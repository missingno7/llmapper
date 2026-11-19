"""The local map corpus: where a map came from, and how to enumerate it.

This is the one place that knows the corpus layout. Provenance is resolved
from the directory (`maps/blood/{campaign,curated,conversions,community,
tiered,mechanism}`, each with an optional `multiplayer/` mode subdirectory);
filename prefixes are only a sanity cross-check. Authoritative statements
about "what original Blood does" may cite `blood-campaign` and
`blood-bloodbath` only, and populations are never mixed while mining.

Enumerate through this module, never by globbing a directory:

* :func:`campaign_maps` -- the original single-player campaign, one path per
  map. Every miner that measures "what the campaign does" starts here.
* :func:`named_maps` -- every map a bare filename names: the pre-reorganization
  flat corpus, and what a conversion draws its Blood vocabulary from.
* :func:`list_corpus_maps` -- any population or named view, with provenance.
* :func:`corpus_map_path` -- one named map, wherever the layout puts it.

It lived inside `bloodmap.patterns` until 2026-11-19. A registry inside a
sensor module meant every tool that only wanted a list of maps imported the
whole sensor stack, and seventeen miners globbed `maps/blood/*.MAP` instead
-- which matched nothing once the corpus was reorganized, so a re-run would
have written an empty knowledge file without complaint.
"""

from __future__ import annotations

import hashlib
import re
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Sequence

from .format import read_map


class CorpusError(ValueError):
    """The corpus cannot answer: an unknown population, a map that is absent."""


#: Source populations. Never mixed while mining. The legacy names
#: `blood-campaign` / `blood-bloodbath` stay valid: they are the original
#: Monolith provenance filtered by game mode.
POPULATIONS = {
    "blood-campaign": "original Blood single-player episode maps (campaign/)",
    "blood-bloodbath": "original BloodBath deathmatch maps (campaign/multiplayer/)",
    "community-curated": "owner hand-picked community source maps (curated/)",
    "own-conversion": "the owner's manual Duke3D->Blood conversions (conversions/)",
    "community": "bulk community maps (community/, tier from tiered/ as metadata)",
    "mechanism-tutorial": "mechanism tutorials and showcases (mechanism/)",
    "generated": "scratch-authored, reconstructed, or tool-converted maps",
    "other": "unclassified Blood MAPs",
}


# ---------------------------------------------------------------------------
# Corpus registry: provenance comes from the directory, not the filename
# ---------------------------------------------------------------------------
#
# The local Blood corpus was reorganized (owner, 2026-08-31) from one flat
# directory into provenance directories, each with an optional `multiplayer/`
# mode subdirectory. Directory membership is authoritative; filename prefixes
# survive only as a sanity cross-check, because the ~1500 bulk community maps
# have arbitrary names -- there are community files literally called `BB3.MAP`
# and `E1M1.MAP` that are not the Monolith maps.

CORPUS_ROOT_ENV = "BLOODMAP_CORPUS"

#: Top-level corpus directory -> population.
CORPUS_DIRECTORIES: dict[str, str] = {
    "campaign": "blood-campaign",
    "curated": "community-curated",
    "conversions": "own-conversion",
    "community": "community",
    "tiered": "community",
    "mechanism": "mechanism-tutorial",
}

#: `community/` and `tiered/` hold the same maps. Enumeration walks the flat
#: `community/` copy and attaches the tier from `tiered/` as metadata, so one
#: map is never counted as two independent pieces of evidence.
COMMUNITY_TIER_DIRECTORY = "tiered"

#: Tier directory names under `tiered/`. These are the classifier's own
#: classification labels (`tiering.CLASSIFICATIONS`). `multiplayer` is the name
#: the first tier tree used for what the classifier calls `bloodbath`; it stays
#: readable so an older tree still resolves.
TIERS = ("S", "A", "B", "C", "questionable", "bloodbath", "mechanism", "multiplayer")

MODE_SUBDIRECTORY = "multiplayer"

#: Directories that actually express the mode axis with a `multiplayer/`
#: subdirectory. Elsewhere the directory says nothing about mode and the
#: honest answer is `unknown` -- cross-check it with :func:`observed_mode`,
#: never with the filename.
MODE_BEARING_DIRECTORIES = frozenset({"campaign", "curated", "tiered"})

#: Populations whose naming convention is exactly known, so a filename that
#: disagrees with the directory is a contaminant rather than an arbitrary name.
#: Authoritative statements about original Blood may cite only these two, so
#: admission is fail-closed here: a file in `campaign/` that is not an `E*M*`
#: or `BB*` map -- an editor autosave, a work copy -- is quarantined and
#: reported by :func:`unadmitted_corpus_maps`, never mined as convention.
#: Everywhere else filenames are arbitrary and the directory alone decides.
STRICT_NAME_POPULATIONS = frozenset({"blood-campaign", "blood-bloodbath"})

#: Named views over populations. `reference` is the quality yardstick the tier
#: classifier scored against: the `campaign/` and `curated/` directories whole,
#: both modes included. "Canonical" is no longer a directory; this is the view
#: that replaced it.
CORPUS_VIEWS: dict[str, tuple[str, ...]] = {
    "reference": ("blood-campaign", "blood-bloodbath", "community-curated"),
    "original": ("blood-campaign", "blood-bloodbath"),
}


@dataclass(frozen=True)
class CorpusMap:
    """One enumerated corpus file with resolved provenance and metadata."""

    path: Path
    relative: str
    population: str
    mode: str
    provenance_directory: str
    tier: str | None = None
    filename_hint: str | None = None

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def hint_conflict(self) -> bool:
        """True when the filename prefix disagrees with directory provenance.

        Informational only: the directory wins. Bulk community filenames are
        arbitrary, so conflicts inside `community/` are expected, not errors.
        """
        return bool(self.filename_hint) and self.filename_hint != self.population

    def to_dict(self) -> dict[str, Any]:
        item: dict[str, Any] = {
            "filename": self.path.name,
            "relative": self.relative,
            "population": self.population,
            "mode": self.mode,
            "provenance_directory": self.provenance_directory,
        }
        if self.tier:
            item["tier"] = self.tier
        if self.filename_hint:
            item["filename_hint"] = self.filename_hint
            item["filename_hint_conflict"] = self.hint_conflict
        return item


def corpus_root(directory: str | Path | None = None) -> Path:
    """Resolve the corpus root: explicit argument, then `BLOODMAP_CORPUS`."""
    if directory is not None:
        return Path(directory)
    override = os.environ.get(CORPUS_ROOT_ENV)
    if override:
        return Path(override)
    return Path("maps") / "blood"


def is_structured_corpus(directory: str | Path) -> bool:
    """True when `directory` is a reorganized corpus root, not a flat folder."""
    root = Path(directory)
    return any((root / name).is_dir() for name in CORPUS_DIRECTORIES)


def filename_population_hint(path: str | Path) -> str | None:
    """Population suggested by the filename prefix. A cross-check, not truth.

    Owner correction (2026-08-31): `DWE*` (Death Wish) and `TEDE*` are
    hand-picked community source maps, **not** conversions; `DNE*` are the
    owner's own manual Duke3D->Blood conversions.
    """
    stem = Path(path).stem.upper()
    name = Path(path).name.upper()
    if "RECONSTRUCTION" in name or name.endswith("-BLOOD.MAP"):
        return "generated"
    if stem.startswith("DNE"):
        return "own-conversion"
    if stem.startswith(("DWE", "DWBB", "TEDE", "SS")):
        return "community-curated"
    if stem.startswith("DM") and stem[2:].isdigit():
        return "community-curated"
    if stem.startswith("BB") and stem[2:].isdigit():
        return "blood-bloodbath"
    if len(stem) >= 4 and stem[0] == "E" and stem[1].isdigit() and "M" in stem:
        return "blood-campaign"
    return None


def classify_map_population(path: str | Path) -> str:
    """Fail-closed population label for a *loose* path, from the filename.

    Prefer :func:`resolve_corpus_map`, which reads provenance from the corpus
    directory layout. This filename classifier only covers the naming
    conventions of the campaign, BloodBath, curated and conversion sets; bulk
    community maps have arbitrary names and fall through to ``"other"``.
    """
    return filename_population_hint(path) or "other"


def _mode_for_parts(top: str, parts: tuple[str, ...]) -> str:
    if any(p.lower() == MODE_SUBDIRECTORY for p in parts):
        return "multiplayer"
    return "sp" if top in MODE_BEARING_DIRECTORIES else "unknown"


def observed_mode(path: str | Path) -> str:
    """Mode read from the map's player starts. The cross-check for the axis.

    A Blood map with multiplayer starts and no single-player start is a
    multiplayer map; one with a single-player start and no multiplayer starts
    is single-player. Maps carrying both are `ambiguous`, which is common:
    plenty of community SP maps also place BloodBath starts.
    """
    from .contents import inventory_map

    starts = inventory_map(read_map(path))["starts"]
    single = bool(starts["single_player"])
    multi = bool(starts["multiplayer"])
    if single and multi:
        return "ambiguous"
    if multi:
        return "multiplayer"
    if single:
        return "sp"
    return "unknown"


def resolve_corpus_map(path: str | Path, *, root: str | Path | None = None) -> CorpusMap:
    """Resolve one corpus file's population, mode and tier from its directory."""
    root_path = corpus_root(root)
    file_path = Path(path)
    try:
        relative = file_path.resolve().relative_to(root_path.resolve())
    except (ValueError, OSError) as exc:
        raise CorpusError(f"{file_path} is not inside corpus root {root_path}") from exc
    parts = relative.parts
    if len(parts) < 2:
        raise CorpusError(
            f"{relative.as_posix()} sits at the corpus root; provenance is only "
            "resolved from a population directory"
        )
    top = parts[0]
    population = CORPUS_DIRECTORIES.get(top)
    if population is None:
        raise CorpusError(f"unknown corpus directory {top!r} for {relative.as_posix()}")
    mode = _mode_for_parts(top, parts[1:])
    if population == "blood-campaign" and mode == "multiplayer":
        population = "blood-bloodbath"
    tier = None
    if top == COMMUNITY_TIER_DIRECTORY and len(parts) >= 3 and parts[1] in TIERS:
        tier = parts[1]
    return CorpusMap(
        path=file_path,
        relative=relative.as_posix(),
        population=population,
        mode=mode,
        provenance_directory=top,
        tier=tier,
        filename_hint=filename_population_hint(file_path),
    )


#: XMapEdit writes `ASAVE<n>.map` (+ `.bak`) into whatever directory it was
#: opened from, so an autosave lands in the corpus every time the owner opens
#: the editor (owner, 2026-09-02: "ignore them"). The name check already
#: quarantines it out of every authoritative population; this predicate lets
#: the hygiene gates tell expected editor debris from a real stray file.
_EDITOR_AUTOSAVE = re.compile(r"^ASAVE\d*\.(map|bak)$", re.IGNORECASE)


def is_editor_autosave(path: str | Path) -> bool:
    """True for an XMapEdit autosave file (`ASAVE1.map`, `ASAVE1.bak`)."""
    return bool(_EDITOR_AUTOSAVE.match(Path(path).name))


def _map_paths_under(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        (p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() == ".map"),
        key=lambda p: p.as_posix().upper(),
    )


_TIER_INDEX_CACHE: dict[str, dict[str, str]] = {}


def clear_corpus_cache() -> None:
    """Drop the cached `tiered/` content-hash index (tests, moved corpora)."""
    _TIER_INDEX_CACHE.clear()


def tier_index(root: str | Path | None = None) -> dict[str, str]:
    """sha256 -> tier, read from the `tiered/` copy of the community maps.

    Tier is metadata from a heuristic classifier -- a navigation and sampling
    aid, never an evidence weight. The join is by content hash because 120
    filenames occur under more than one tier directory, so a name-keyed join
    would silently mislabel them; hashes that land in two tiers are dropped
    rather than guessed.
    """
    root_path = corpus_root(root)
    key = str(root_path.resolve())
    cached = _TIER_INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    index: dict[str, str] = {}
    ambiguous: set[str] = set()
    tier_root = root_path / COMMUNITY_TIER_DIRECTORY
    for path in _map_paths_under(tier_root):
        parts = path.relative_to(tier_root).parts
        if len(parts) < 2 or parts[0] not in TIERS:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if index.setdefault(digest, parts[0]) != parts[0]:
            ambiguous.add(digest)
    for digest in ambiguous:
        index.pop(digest, None)
    _TIER_INDEX_CACHE[key] = index
    return index


def _admitted(item: CorpusMap) -> bool:
    """Fail-closed admission for the two authoritative original populations.

    An XMapEdit autosave is never admitted anywhere: the editor drops
    `ASAVE<n>.map` into whichever corpus directory it was opened from, and
    `curated/` and `community/` accept arbitrary names, so without this an
    autosave in `curated/` counted as a curated map (2026-09-02: 47 for 46).
    """
    if is_editor_autosave(item.path):
        return False
    if item.population not in STRICT_NAME_POPULATIONS:
        return True
    return item.filename_hint == item.population


def unadmitted_corpus_maps(directory: str | Path | None = None) -> list[CorpusMap]:
    """Files quarantined out of an authoritative population by the name check.

    In practice these are working artifacts that landed in a provenance
    directory -- an editor autosave, a rebuilt copy. They are reported so the
    corpus can be cleaned, never silently mined as original convention.
    """
    return [
        item for item in list_corpus_maps(directory, strict=False)
        if not _admitted(item)
    ]


def _directory_can_yield(top: str, wanted: set[str]) -> bool:
    if CORPUS_DIRECTORIES[top] in wanted:
        return True
    # campaign/ also yields blood-bloodbath, through campaign/multiplayer/.
    return top == "campaign" and "blood-bloodbath" in wanted


def _list_flat_corpus(
    root: Path, *, wanted: set[str] | None, mode: str | None, tier: str | None,
) -> list[CorpusMap]:
    """A legacy flat directory (or a flat `BLOODMAP_CORPUS`): filenames only."""
    if tier is not None:
        return []
    results = []
    for path in _map_paths_under(root):
        population = classify_map_population(path)
        if wanted is not None and population not in wanted:
            continue
        item = CorpusMap(
            path=path,
            relative=path.relative_to(root).as_posix(),
            population=population,
            mode="multiplayer" if population == "blood-bloodbath" else "sp",
            provenance_directory="",
            filename_hint=filename_population_hint(path),
        )
        if mode is not None and item.mode != mode:
            continue
        results.append(item)
    return results


def list_corpus_maps(
    directory: str | Path | None = None,
    *,
    population: str | None = None,
    view: str | None = None,
    mode: str | None = None,
    tier: str | None = None,
    attach_tiers: bool = True,
    strict: bool = True,
) -> list[CorpusMap]:
    """Enumerate the corpus recursively with directory-resolved provenance.

    `community` resolves to the flat `community/` copy with `tier` attached
    from `tiered/`: the two directories are one population, never two.

    With `strict` (the default), a file whose filename contradicts a
    :data:`STRICT_NAME_POPULATIONS` directory is not admitted; list those with
    :func:`unadmitted_corpus_maps`.
    """
    root = corpus_root(directory)
    if population is not None and population not in POPULATIONS:
        raise CorpusError(f"unknown population {population!r}")
    if view is not None and view not in CORPUS_VIEWS:
        raise CorpusError(f"unknown corpus view {view!r}")
    if tier is not None and tier not in TIERS:
        raise CorpusError(f"unknown tier {tier!r}")
    wanted: set[str] | None = set(CORPUS_VIEWS[view]) if view is not None else None
    if population is not None:
        wanted = {population} if wanted is None else wanted & {population}
    if not root.is_dir():
        return []
    if not is_structured_corpus(root):
        return _list_flat_corpus(root, wanted=wanted, mode=mode, tier=tier)

    results: list[CorpusMap] = []
    for top in CORPUS_DIRECTORIES:
        if top == COMMUNITY_TIER_DIRECTORY:
            continue                                  # the community/ copy wins
        if wanted is not None and not _directory_can_yield(top, wanted):
            continue
        results.extend(resolve_corpus_map(path, root=root) for path in _map_paths_under(root / top))
    if strict:
        results = [item for item in results if _admitted(item)]
    if wanted is not None:
        results = [item for item in results if item.population in wanted]
    if attach_tiers and any(item.population == "community" for item in results):
        index = tier_index(root)
        if index:
            results = [
                replace(item, tier=index.get(hashlib.sha256(item.path.read_bytes()).hexdigest()))
                if item.population == "community" else item
                for item in results
            ]
    if mode is not None:
        results = [item for item in results if item.mode == mode]
    if tier is not None:
        results = [item for item in results if item.tier == tier]
    return results


def list_original_maps(
    directory: str | Path | None = None, *, population: str,
) -> list[Path]:
    """Every path for one population, resolved from the corpus layout."""
    if population not in POPULATIONS:
        raise CorpusError(f"unknown population {population!r}")
    return [item.path for item in list_corpus_maps(directory, population=population)]


#: Populations a bare filename may name unambiguously. The bulk `community/`
#: set is excluded on purpose: its filenames are arbitrary and collide with
#: campaign names, so a name lookup across it would silently hand back
#: somebody else's E1M1.
NAMED_POPULATIONS: tuple[str, ...] = (
    "blood-campaign", "blood-bloodbath", "community-curated", "own-conversion",
)


def _named_map_index(
    root: Path, populations: tuple[str, ...],
) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for population in populations:
        for item in list_corpus_maps(root, population=population, attach_tiers=False):
            index.setdefault(item.name.upper(), item.path)
    return index


def corpus_map_path(
    name: str,
    *,
    root: str | Path | None = None,
    populations: Sequence[str] = NAMED_POPULATIONS,
    missing_ok: bool = False,
) -> Path:
    """Where a named map lives, whatever directory the corpus puts it in.

    `name` may be given with or without its extension and in any case, so
    ``"E3M1"``, ``"e3m1.map"`` and ``"E3M1.MAP"`` all resolve.

    The corpus was reorganized into provenance directories, so
    ``maps/blood/E3M1.MAP`` stopped existing and every caller that spelled
    that path by hand stopped working -- silently, at whatever depth it first
    read a map. This is the one place that knows the layout. Enumerate
    through it, never by globbing a directory.

    Raises `CorpusError` when the map is absent, so a miner fails at the
    lookup rather than deep inside. Pass ``missing_ok=True`` to get the path
    it *would* have back instead, which is what a test's `exists()` skip
    guard wants.
    """
    root_path = corpus_root(root)
    wanted = Path(str(name)).name.upper()
    if not wanted.endswith(".MAP"):
        wanted += ".MAP"
    index = _named_map_index(root_path, tuple(populations))
    found = index.get(wanted)
    if found is not None:
        return found
    if missing_ok:
        return root_path / wanted
    raise CorpusError(
        f"{wanted} is not in the corpus at {root_path}; "
        f"searched {', '.join(populations)}"
    )


CORPUS_MANIFEST_SCHEMA = "llmapper.blood-corpus-manifest"
CORPUS_MANIFEST_VERSION = 1

#: Owner-stated provenance, 2026-08-31. These override older docs and code.
CORPUS_PROVENANCE_NOTES = [
    "Provenance comes from the directory a map lives in; filename prefixes are "
    "only a sanity cross-check.",
    "DWE* (Death Wish) and TEDE* are hand-picked community source maps, NOT "
    "conversions; older docs and classify_map_population labelled them wrongly.",
    "DNE* are the owner's own manual Duke3D->Blood conversions: cross-game "
    "correspondence evidence only, never Blood design convention.",
    "campaign/multiplayer/BB1-BB9 is the only original BloodBath set; "
    "curated/multiplayer/ (DWBB1-3, DM1-3, SSFACE) is owner-picked community MP.",
    "community/ and tiered/ hold the same maps. Tier is metadata from a "
    "heuristic classifier: a sampling aid, never an evidence weight.",
    "tiered/manifest.json carries absolute paths from another checkout; trust "
    "its sha256/filenames, not its paths.",
    "'Canonical' is no longer a directory. It survives as the named view "
    "reference = campaign + curated.",
    "Community maps have not passed the native losslessness gate. The gate is "
    "fail-closed: a failing map is skipped and reported, never normalized.",
]


MODES = ("sp", "multiplayer", "unknown")


def cross_check_modes(maps: Iterable[CorpusMap]) -> dict[str, Any]:
    """Compare the directory-declared mode with the map's own player starts.

    Only maps whose directory actually declares a mode are checked. `ambiguous`
    (both start kinds present) is not a disagreement; a map that declares `sp`
    and carries multiplayer starts only, is.
    """
    checked = 0
    agreements: Counter[str] = Counter()
    disagreements: list[dict[str, str]] = []
    for item in maps:
        if item.mode == "unknown":
            continue
        checked += 1
        try:
            observed = observed_mode(item.path)
        except Exception as exc:                          # unparsable: reported, not guessed
            disagreements.append({
                "relative": item.relative, "declared": item.mode,
                "observed": "unreadable", "detail": f"{type(exc).__name__}: {exc}",
            })
            continue
        agreements[observed] += 1
        if observed not in (item.mode, "ambiguous"):
            disagreements.append({
                "relative": item.relative, "declared": item.mode, "observed": observed,
            })
    return {
        "maps_checked": checked,
        "observed_start_kinds": dict(sorted(agreements.items())),
        "disagreements": disagreements,
        "basis": "sprite type 1 = single-player start, type 2 = multiplayer start",
    }


def build_corpus_manifest(directory: str | Path | None = None) -> dict[str, Any]:
    """Inventory the corpus: layout, populations, modes, tiers, duplicates.

    Records content hashes so that later runs can detect the same map appearing
    in two directories, which would otherwise be double-counted as evidence.
    """
    root = corpus_root(directory)
    maps = list_corpus_maps(root)
    if not maps:
        raise CorpusError(f"no maps found under corpus root {root}")

    by_digest: dict[str, list[CorpusMap]] = defaultdict(list)
    entries: list[dict[str, Any]] = []
    for item in maps:
        data = item.path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        by_digest[digest].append(item)
        entry = item.to_dict()
        entry.update(sha256=digest, bytes=len(data))
        entries.append(entry)

    populations = Counter(item.population for item in maps)
    modes = Counter(f"{item.population}|{item.mode}" for item in maps)
    tiers = Counter(item.tier or "untiered" for item in maps if item.population == "community")
    cross_population_duplicates = [
        {
            "sha256": digest,
            "files": sorted(item.relative for item in group),
            "populations": sorted({item.population for item in group}),
        }
        for digest, group in sorted(by_digest.items())
        if len({item.population for item in group}) > 1
    ]
    views = {
        name: {
            "populations": list(members),
            "map_count": sum(populations[p] for p in members),
        }
        for name, members in CORPUS_VIEWS.items()
    }
    return {
        "$schema": CORPUS_MANIFEST_SCHEMA,
        "schema_version": CORPUS_MANIFEST_VERSION,
        "corpus_root": root.as_posix(),
        "map_count": len(maps),
        "distinct_sha256": len(by_digest),
        "populations": {
            name: {"description": POPULATIONS[name], "map_count": populations.get(name, 0)}
            for name in POPULATIONS
            if populations.get(name)
        },
        "population_directories": dict(CORPUS_DIRECTORIES),
        "modes": {key: count for key, count in sorted(modes.items())},
        "tiers": {key: count for key, count in sorted(tiers.items())},
        "views": views,
        "mode_axis": {
            "declared_from": "the multiplayer/ subdirectory of campaign/, curated/ and tiered/",
            "unknown_where": "community/, conversions/ and mechanism/ do not express the axis",
            "cross_check": cross_check_modes(maps),
        },
        "cross_population_duplicates": cross_population_duplicates,
        "filename_hint_conflicts": [
            {"relative": item.relative, "population": item.population,
             "filename_hint": item.filename_hint}
            for item in maps
            if item.hint_conflict and item.population != "community"
        ],
        "unadmitted": [
            {"relative": item.relative, "would_be_population": item.population,
             "filename_hint": item.filename_hint,
             "reason": "filename contradicts an authoritative population directory"}
            for item in unadmitted_corpus_maps(root)
        ],
        "provenance_notes": CORPUS_PROVENANCE_NOTES,
        "limitations": [
            "Mode for community/ maps is unknown from the directory alone; the "
            "tier 'multiplayer' is the classifier's guess, not a player-start count.",
            "Tier is absent where a map is not in tiered/ or where its hash lands "
            "in two tier directories; that is recorded as untiered, never guessed.",
        ],
        "maps": entries,
    }

def named_maps(directory: str | Path | None = None) -> list[Path]:
    """Every map a bare filename names unambiguously, one path per name.

    The campaign, BloodBath, the curated community maps and the owner's
    conversions (:data:`NAMED_POPULATIONS`): what the corpus was while it was
    one flat directory, and the set the native losslessness gate is expected
    to hold for. The bulk `community/` population is excluded on purpose --
    its maps have not passed that gate and its filenames collide with campaign
    names. A flat directory that is not a corpus yields every map in it.
    Editor autosaves are never included.
    """
    root = corpus_root(directory)
    if is_structured_corpus(root):
        items = [item for population in NAMED_POPULATIONS
                 for item in list_corpus_maps(
                     root, population=population, attach_tiers=False)]
    else:
        items = list_corpus_maps(root, attach_tiers=False)
    found: dict[str, Path] = {}
    for item in items:
        if not is_editor_autosave(item.path):
            found.setdefault(item.name.upper(), item.path)
    return sorted(found.values())


# ---------------------------------------------------------------------------
# The campaign
# ---------------------------------------------------------------------------

#: A campaign map's name: episodes 1-4 and 6 (the Plasma Pak), maps 1-9.
#: Episode 5 is Cryptic Passage, which ships its maps under other names.
CAMPAIGN_NAME = re.compile(r"^E[1-46]M[1-9]$")


def campaign_maps(
    directory: str | Path | None = None, *, required: bool = False,
) -> list[Path]:
    """The original single-player campaign, one path per map, sorted by name.

    `directory` is a corpus root or a flat directory of maps; `None` is the
    local corpus (`BLOODMAP_CORPUS`, else `maps/blood`). A miner whose output
    is a knowledge file passes ``required=True``: an empty corpus is then an
    error at the first line rather than an empty document written over a
    measured one.
    """
    found: dict[str, Path] = {}
    for item in list_corpus_maps(
            directory, population="blood-campaign", attach_tiers=False):
        name = item.path.stem.upper()
        if CAMPAIGN_NAME.match(name):
            found.setdefault(name, item.path)
    if required and not found:
        raise CorpusError(
            f"no campaign maps under {corpus_root(directory)}; "
            f"set {CORPUS_ROOT_ENV} or pass the corpus directory")
    return [found[name] for name in sorted(found)]
