"""Corpus-grounded design-pattern observation, clustering, and retrieval.

This layer sits between sensors and interpretation. It does not name rooms.
It records measurable spawn, route, morphology, and vertical relationships,
clusters them by independent discrete signatures, and retrieves precedents.

Populations are never mixed. Provenance is resolved from the corpus directory
layout (`maps/blood/{campaign,curated,conversions,community,tiered,mechanism}`,
each with an optional `multiplayer/` mode subdirectory); filename prefixes are
only a sanity cross-check. Authoritative statements about "what original Blood
does" may cite `blood-campaign` and `blood-bloodbath` only.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from math import atan2, degrees, hypot
from pathlib import Path
from typing import Any, Iterable, Sequence

from .build_ir import BuildIR
from .design import _polygon_loops, _signed_area
from .exposure import (
    ExposureError,
    route_exposure_report,
    spawn_neighborhood_report,
)
from .format import read_map
from .model import DiskMap
from .morphology import _loop_metrics
from .player_space import PLAYER_PROFILES
from .sight import spawn_sight_report
from .spatial import analyze_spatial


SCHEMA = "llmapper.design-patterns"
SCHEMA_VERSION = 1
PLAYER_WIDTH = 384
#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

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


class PatternError(ValueError):
    pass


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
        raise PatternError(f"{file_path} is not inside corpus root {root_path}") from exc
    parts = relative.parts
    if len(parts) < 2:
        raise PatternError(
            f"{relative.as_posix()} sits at the corpus root; provenance is only "
            "resolved from a population directory"
        )
    top = parts[0]
    population = CORPUS_DIRECTORIES.get(top)
    if population is None:
        raise PatternError(f"unknown corpus directory {top!r} for {relative.as_posix()}")
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
    """Fail-closed admission for the two authoritative original populations."""
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
        raise PatternError(f"unknown population {population!r}")
    if view is not None and view not in CORPUS_VIEWS:
        raise PatternError(f"unknown corpus view {view!r}")
    if tier is not None and tier not in TIERS:
        raise PatternError(f"unknown tier {tier!r}")
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
        raise PatternError(f"unknown population {population!r}")
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

    Raises `PatternError` when the map is absent, so a miner fails at the
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
    raise PatternError(
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
        raise PatternError(f"no maps found under corpus root {root}")

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


def _id(ref: str) -> int:
    return int(str(ref).split(":", 1)[1])


def _sky(build: BuildIR, sector_id: int) -> bool:
    return bool(int(build.sectors[sector_id]["fields"]["ceiling_stat"]) & 1)


def _area(build: BuildIR, sector_id: int) -> float:
    return abs(sum(_signed_area(loop) for loop in _polygon_loops(build, sector_id)))


def _shade(build: BuildIR, sector_id: int) -> dict[str, int]:
    fields = build.sectors[sector_id]["fields"]
    first = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    walls = [int(build.walls[wid]["fields"].get("shade") or 0) for wid in range(first, first + count)]
    return {
        "floor": int(fields.get("floor_shade") or 0),
        "ceiling": int(fields.get("ceiling_shade") or 0),
        "wall_mean": int(round(sum(walls) / max(1, len(walls)))),
    }


def _materials(build: BuildIR, sector_id: int) -> dict[str, int]:
    fields = build.sectors[sector_id]["fields"]
    first = int(fields["wall_ptr"])
    wall_pic = int(build.walls[first]["fields"]["picnum"]) if 0 <= first < len(build.walls) else 0
    return {
        "floor_picnum": int(fields["floor_picnum"]),
        "ceiling_picnum": int(fields["ceiling_picnum"]),
        "wall_picnum": wall_pic,
    }


def _bin_relative(value: float | None, median: float, *, low: float = 0.5, high: float = 2.0) -> str:
    if value is None or median <= 0:
        return "unknown"
    if value < low * median:
        return "small"
    if value > high * median:
        return "large"
    return "medium"


def _bin_hops(value: int | None) -> str:
    if value is None:
        return "none"
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    return "2+"


def _bin_exits(value: int) -> str:
    if value <= 1:
        return "1"
    if value == 2:
        return "2"
    return "3+"


def _bin_frac(value: float | None, *, low: float = 0.25, high: float = 0.75) -> str:
    if value is None:
        return "unknown"
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "mid"


def _bin_sight(widths: float | None) -> str:
    if widths is None:
        return "unknown"
    if widths < 8:
        return "low"
    if widths < 24:
        return "mid"
    return "high"


def _bin_step(player_heights: float) -> str:
    mag = abs(player_heights)
    if mag < 0.25:
        return "flat"
    if mag < 1.5:
        return "step"
    return "storey"


def observe_spawn_neighborhoods(
    disk: DiskMap, *, map_id: str, population: str, force: bool = False,
) -> list[dict[str, Any]]:
    """One observation sample per multiplayer start.

    Mining keeps this BloodBath-only so campaign maps are not silently mixed.
    Pattern-aware reading may pass force=True to score a generated candidate.
    """
    if population != "blood-bloodbath" and not force:
        return []
    build = disk.to_build_ir()
    try:
        neighborhoods = spawn_neighborhood_report(build, include_sp_start=False)
        sight = spawn_sight_report(build, include_sp_start=False)
    except ExposureError:
        return []
    clear_by_origin: dict[str, list[bool]] = defaultdict(list)
    for pair in sight.get("pairs") or []:
        clear_by_origin[str(pair["a"])].append(bool(pair["clear"]))
        clear_by_origin[str(pair["b"])].append(bool(pair["clear"]))
    samples = []
    for item in neighborhoods["neighborhoods"]:
        sector_id = _id(item["sector"])
        origin = str(item["origin"])
        clears = clear_by_origin.get(origin) or []
        samples.append({
            "subject": "spawn-neighborhood",
            "population": population,
            "map": map_id,
            "focus": {"sprite": int(item["sprite_id"]), "sector": sector_id, "origin": origin},
            "geometry": {
                "sky_ceiling": item["sky_ceiling"],
                "vertices": _loop_metrics(max(_polygon_loops(build, sector_id), key=lambda loop: abs(_signed_area(loop))))["vertices"],
            },
            "scale": {
                "spawn_sector_area_player_areas": item["spawn_sector_area_player_areas"],
                "local_reachable_area_player_areas": item["local_reachable_area_player_areas"],
            },
            "visibility": {
                "max_2d_sight_player_widths": item["max_2d_sight_player_widths"],
                "sky_region_ray_fraction": item["sky_region_ray_fraction"],
                "spawn_pair_clear_fraction": None if not clears else round(sum(clears) / len(clears), 4),
            },
            "routes": {
                "immediate_portal_choices": item["immediate_portal_choices"],
                "hops_to_largest_sky_region": item["hops_to_largest_sky_region"],
            },
            "materials": _materials(build, sector_id),
            "lighting": _shade(build, sector_id),
            "evidence": ["spawn_neighborhood_report", "spawn_sight_report"],
        })
    return samples


def observe_routes(disk: DiskMap, *, map_id: str, population: str, include_sp_start: bool) -> list[dict[str, Any]]:
    build = disk.to_build_ir()
    try:
        report = route_exposure_report(build, include_sp_start=include_sp_start)
    except ExposureError:
        return []
    samples = []
    for route in report["routes"]:
        if not route.get("reachable"):
            continue
        seq = []
        heights = []
        shades = []
        for sample in route.get("samples") or []:
            sector_id = _id(sample["sector"])
            seq.append("S" if sample["sky_ceiling"] else "C")
            fields = build.sectors[sector_id]["fields"]
            heights.append(int(fields["floor_z"]))
            shades.append(_shade(build, sector_id)["wall_mean"])
        compressed = []
        for token in seq:
            if not compressed or compressed[-1] != token:
                compressed.append(token)
        first_h, last_h = (heights[0], heights[-1]) if heights else (0, 0)
        first_s, last_s = (shades[0], shades[-1]) if shades else (0, 0)
        samples.append({
            "subject": "route-exposure",
            "population": population,
            "map": map_id,
            "focus": {"origin": route["origin"], "hops": route["hops"]},
            "geometry": {"cover_sequence": "".join(compressed), "hops": route["hops"]},
            "scale": {
                "sky_sample_fraction": route["sky_sample_fraction"],
                "mean_max_sight_player_widths": route["mean_max_sight_player_widths"],
                "min_max_sight_player_widths": route["min_max_sight_player_widths"],
            },
            "visibility": {
                "cover_sky_transitions": route["cover_sky_transitions"],
            },
            "routes": {
                "floor_delta_player_heights": round((last_h - first_h) / PLAYER_HEIGHT, 4),
                "shade_delta": last_s - first_s,
            },
            "lighting": {"origin_wall_shade": first_s, "destination_wall_shade": last_s},
            "evidence": ["route_exposure_report"],
        })
    return samples


def observe_morphology(disk: DiskMap, *, map_id: str, population: str) -> list[dict[str, Any]]:
    build = disk.to_build_ir()
    samples = []
    for sector_id in range(len(build.sectors)):
        area = _area(build, sector_id) / (PLAYER_WIDTH ** 2)
        if area < 1.0:
            continue
        loops = _polygon_loops(build, sector_id)
        outer = max(loops, key=lambda loop: abs(_signed_area(loop)))
        metrics = _loop_metrics(outer)
        if metrics["vertices"] < 3:
            continue
        turns = []
        lengths = []
        n = len(outer)
        for index in range(n):
            ax, ay = outer[index]
            bx, by = outer[(index + 1) % n]
            lengths.append(hypot(bx - ax, by - ay))
            cx, cy = outer[(index + 2) % n]
            ux, uy = bx - ax, by - ay
            vx, vy = cx - bx, cy - by
            lu, lv = hypot(ux, uy), hypot(vx, vy)
            if lu < 1 or lv < 1:
                continue
            turns.append(round(degrees(atan2(ux * vy - uy * vx, ux * vx + uy * vy)) / 15.0) * 15)
        perimeter = sum(lengths) or 1.0
        rel = [round(value / perimeter, 3) for value in lengths]
        samples.append({
            "subject": "local-morphology",
            "population": population,
            "map": map_id,
            "focus": {"sector": sector_id},
            "geometry": {
                "vertices": metrics["vertices"],
                "rectangular": metrics["rectangular"],
                "convex": metrics["convex"],
                "chamfer_corners": metrics["chamfer_corners"],
                "curved_chains": metrics["curved_chains"],
                "aabb_fill": metrics["aabb_fill"],
                "turn_sequence_deg": turns,
                "relative_lengths": rel,
            },
            "scale": {"area_player_areas": round(area, 4)},
            "materials": _materials(build, sector_id),
            "lighting": _shade(build, sector_id),
            "context": {"sky_ceiling": _sky(build, sector_id), "hole_count": max(0, len(loops) - 1)},
            "evidence": ["analyze_morphology loop metrics"],
        })
    return samples


def observe_vertical(disk: DiskMap, *, map_id: str, population: str) -> list[dict[str, Any]]:
    build = disk.to_build_ir()
    spatial = analyze_spatial(build)
    samples = []
    for edge in spatial["views"]["traversability"]["walkable_at_rest"]:
        left, right = _id(edge["sectors"][0]), _id(edge["sectors"][1])
        lf = int(build.sectors[left]["fields"]["floor_z"])
        rf = int(build.sectors[right]["fields"]["floor_z"])
        delta = (rf - lf) / PLAYER_HEIGHT
        if abs(delta) < 0.2:
            continue
        ls, rs = _sky(build, left), _sky(build, right)
        if ls == rs:
            sky_rel = "same"
        elif (not ls) and rs:
            sky_rel = "cover_to_open"
        else:
            sky_rel = "open_to_cover"
        shade_delta = _shade(build, right)["wall_mean"] - _shade(build, left)["wall_mean"]
        samples.append({
            "subject": "vertical-transition",
            "population": population,
            "map": map_id,
            "focus": {"sectors": [left, right], "wall": edge.get("wall")},
            "geometry": {
                "floor_delta_player_heights": round(delta, 4),
                "sky_relationship": sky_rel,
            },
            "scale": {
                "left_area_player_areas": round(_area(build, left) / (PLAYER_WIDTH ** 2), 4),
                "right_area_player_areas": round(_area(build, right) / (PLAYER_WIDTH ** 2), 4),
            },
            "visibility": {"sky_relationship": sky_rel},
            "lighting": {
                "shade_delta": shade_delta,
                "left": _shade(build, left),
                "right": _shade(build, right),
            },
            "materials": {"left": _materials(build, left), "right": _materials(build, right)},
            "evidence": ["spatial.traversability.walkable_at_rest"],
        })
    return samples


def observe_object_context(
    disk: DiskMap, *, map_id: str, population: str, hops: int = 1,
) -> list[dict[str, Any]]:
    """One sample per sector that holds objects, keyed by its relations.

    The three families above measure a sector's *shape*, its *route*, or its
    *edges*. This one measures what the sector is for at object scale: what it
    holds, what holds those objects up, and how it sits among its neighbours.
    Features are Phase 1 relations, so the signature is frame-independent --
    two furnished corners in different maps at different orientations key the
    same, which is the whole point of mining them together.

    Only sectors carrying at least one sprite are sampled. An empty sector has
    no object-scale content, and including 600 of them per map would bury the
    families that do.

    Every sample is labelled twice and nothing is dropped: `sector_kind` from
    `reachability.sector_kinds` (a switch closet is not a furnished room) and
    the visible/wiring split of what it holds. A sample is in `scope`
    `"default"` when it sits in reachable geometry and holds at least one
    object a player can see; everything else is `"excluded"` and is clustered
    under its own heading, because a sound-marker pocket is evidence about
    wiring rather than about furniture.

    Reachability is computed **once per map** here, never per sample.
    """
    from .blood_types import sprite_visibility
    from .reachability import sector_kinds as reachability_sector_kinds
    from .relations import context_signature, extract_relations, sprite_kind

    build = disk.to_build_ir()
    kinds = reachability_sector_kinds(disk)
    carrying: dict[int, int] = defaultdict(int)
    visible: dict[int, int] = defaultdict(int)
    wiring_categories: dict[int, Counter] = defaultdict(Counter)
    for sprite_id, sprite in enumerate(build.sprites):
        fields = sprite["fields"]
        sector_id = int(fields["sector"])
        carrying[sector_id] += 1
        if sprite_kind(build, sprite_id) == "visible":
            visible[sector_id] += 1
        else:
            found = sprite_visibility(int(fields["lotag"]), int(fields["cstat"]))
            wiring_categories[sector_id][
                found["category"] if found["non_visible_category"] else "hidden-" + found["category"]
            ] += 1

    samples = []
    for sector_id in sorted(carrying):
        if not 0 <= sector_id < len(build.sectors):
            continue
        document = extract_relations(build, sectors=[sector_id], hops=hops,
                                     sector_kinds=kinds)
        area = _area(build, sector_id) / (PLAYER_WIDTH ** 2)
        fields = build.sectors[sector_id]["fields"]
        height = (int(fields["floor_z"]) - int(fields["ceiling_z"])) / PLAYER_HEIGHT
        kind = kinds.get(sector_id, "unknown")
        seen = visible[sector_id]
        excluded_because = []
        if kind not in ("reachable", "unknown"):
            excluded_because.append(f"off-map: {kind}")
        if seen == 0:
            excluded_because.append(
                f"all {carrying[sector_id]} objects are wiring or markers")
        sample = {
            "subject": "object-context",
            "population": population,
            "map": map_id,
            "focus": {"sector": sector_id},
            "sector_kind": kind,
            "scope": "excluded" if excluded_because else "default",
            "excluded_because": excluded_because,
            "context_signature": context_signature(document, sector_id),
            "scale": {
                "area_player_areas": round(area, 4),
                "clear_height_player_heights": round(height, 4),
                "objects": seen,
                "objects_all": carrying[sector_id],
                "objects_wiring": carrying[sector_id] - seen,
            },
            "relation_counts": dict(document["counts"]),
            "materials": _materials(build, sector_id),
            "evidence": ["relations.extract_relations one-hop neighborhood",
                         "relations.context_signature (visible objects only)",
                         "reachability.sector_kinds"],
        }
        if wiring_categories[sector_id]:
            # Keyed on the wiring instead. Without this an excluded sample
            # reads `objects:0` and says nothing about what it actually holds,
            # which makes the excluded heading a bin rather than a finding.
            sample["wiring_signature"] = context_signature(
                document, sector_id, visible_only=False)
            sample["wiring_categories"] = dict(sorted(wiring_categories[sector_id].items()))
        samples.append(sample)
    return samples


def observe_map(path: str | Path, *, population: str | None = None) -> list[dict[str, Any]]:
    path = Path(path)
    pop = population or classify_map_population(path)
    disk = read_map(path)
    map_id = path.name
    samples: list[dict[str, Any]] = []
    samples.extend(observe_spawn_neighborhoods(disk, map_id=map_id, population=pop))
    samples.extend(observe_routes(
        disk, map_id=map_id, population=pop,
        include_sp_start=pop == "blood-campaign",
    ))
    samples.extend(observe_morphology(disk, map_id=map_id, population=pop))
    samples.extend(observe_vertical(disk, map_id=map_id, population=pop))
    samples.extend(observe_object_context(disk, map_id=map_id, population=pop))
    return samples


def _spawn_signature(sample: dict[str, Any], medians: dict[str, float]) -> str:
    vis = sample["visibility"]
    routes = sample["routes"]
    scale = sample["scale"]
    return "|".join((
        f"sky:{int(sample['geometry']['sky_ceiling'])}",
        f"hops:{_bin_hops(routes['hops_to_largest_sky_region'])}",
        f"exits:{_bin_exits(int(routes['immediate_portal_choices']))}",
        f"area:{_bin_relative(scale['spawn_sector_area_player_areas'], medians.get('spawn_area', 1))}",
        f"local:{_bin_relative(scale['local_reachable_area_player_areas'], medians.get('local_area', 1))}",
        f"field:{_bin_frac(vis['sky_region_ray_fraction'])}",
        f"sight:{_bin_sight(vis['max_2d_sight_player_widths'])}",
        f"peek:{_bin_frac(vis['spawn_pair_clear_fraction'], low=0.1, high=0.4)}",
    ))


def _route_signature(sample: dict[str, Any]) -> str:
    geo = sample["geometry"]
    routes = sample["routes"]
    return "|".join((
        f"seq:{geo['cover_sequence'] or '?'}",
        f"hops:{_bin_hops(geo['hops'])}",
        f"skyfrac:{_bin_frac(sample['scale']['sky_sample_fraction'])}",
        f"z:{_bin_step(float(routes['floor_delta_player_heights']))}",
        f"shade:{'darker' if routes['shade_delta'] > 4 else 'brighter' if routes['shade_delta'] < -4 else 'flat'}",
    ))


def _morph_signature(sample: dict[str, Any]) -> str:
    geo = sample["geometry"]
    verts = int(geo["vertices"])
    if verts <= 4:
        vbin = "4"
    elif verts <= 8:
        vbin = "5-8"
    else:
        vbin = "9+"
    fill = geo.get("aabb_fill") or 0
    return "|".join((
        f"rect:{int(bool(geo['rectangular']))}",
        f"convex:{int(bool(geo['convex']))}",
        f"verts:{vbin}",
        f"chamfer:{'1+' if geo['chamfer_corners'] else '0'}",
        f"curve:{'1+' if geo['curved_chains'] else '0'}",
        f"fill:{'boxy' if fill >= 0.75 else 'loose'}",
        f"sky:{int(bool(sample['context']['sky_ceiling']))}",
        f"holes:{'1+' if sample['context']['hole_count'] else '0'}",
    ))


def _vertical_signature(sample: dict[str, Any]) -> str:
    geo = sample["geometry"]
    shade = sample["lighting"]["shade_delta"]
    return "|".join((
        f"step:{_bin_step(float(geo['floor_delta_player_heights']))}",
        f"sky:{geo['sky_relationship']}",
        f"shade:{'darker' if shade > 4 else 'brighter' if shade < -4 else 'flat'}",
        f"into:{_bin_relative(sample['scale']['right_area_player_areas'], sample['scale']['left_area_player_areas'] or 1)}",
    ))


#: Quartile boundaries of the 2837 sprite-carrying sectors in the first 15
#: campaign maps, measured rather than chosen: area p25/p50/p75 = 3.7/14.2/56.7
#: player areas, clear height p25/p50/p75 = 1.57/1.93/3.50 player heights.
#: Quartiles because a band that holds nine tenths of the corpus separates
#: nothing -- the first guess here was 1.0/2.0/4.0 on height and put nearly
#: every campaign sector in one bucket.
OBJECT_AREA_BANDS = ((4.0, "tiny"), (14.0, "small"), (57.0, "room"), (None, "hall"))
OBJECT_HEIGHT_BANDS = ((1.5, "tight"), (2.0, "standing"), (3.5, "open"), (None, "lofty"))


def _band(value: float, bands: tuple[tuple[float | None, str], ...]) -> str:
    for edge, label in bands:
        if edge is None or value < edge:
            return label
    return bands[-1][1]


def _object_context_signature(sample: dict[str, Any]) -> str:
    """The relation context, plus the two scale bands that separate a shelf
    recess from a furnished hall holding the same relations."""
    scale = sample["scale"]
    return "|".join((
        sample["context_signature"],
        f"size:{_band(float(scale['area_player_areas']), OBJECT_AREA_BANDS)}",
        f"clear:{_band(float(scale['clear_height_player_heights']), OBJECT_HEIGHT_BANDS)}",
    ))


_SIGNATURES = {
    "spawn-neighborhood": _spawn_signature,
    "route-exposure": _route_signature,
    "local-morphology": _morph_signature,
    "vertical-transition": _vertical_signature,
    "object-context": _object_context_signature,
}


def _median(values: list[float]) -> float:
    if not values:
        return 1.0
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def cluster_samples(samples: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Group samples by independent discrete signatures. No room names.

    A sample may carry `scope`. Anything marked `"excluded"` -- off-map
    geometry, or a sector whose every object is wiring -- is clustered
    separately into `excluded_candidates` rather than mixed into the default
    statistics or thrown away. It is evidence about how a level is wired.
    """
    samples = list(samples)
    excluded = [item for item in samples if item.get("scope") == "excluded"]
    samples = [item for item in samples if item.get("scope") != "excluded"]
    by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        by_subject[str(sample["subject"])].append(sample)
    medians = {
        "spawn_area": _median([
            item["scale"]["spawn_sector_area_player_areas"]
            for item in by_subject.get("spawn-neighborhood", [])
        ]),
        "local_area": _median([
            item["scale"]["local_reachable_area_player_areas"]
            for item in by_subject.get("spawn-neighborhood", [])
        ]),
    }
    candidates = []
    for subject, items in sorted(by_subject.items()):
        signer = _SIGNATURES[subject]
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            if subject == "spawn-neighborhood":
                key = signer(item, medians)
            else:
                key = signer(item)
            item = dict(item)
            item["signature"] = key
            buckets[key].append(item)
        for signature, members in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            maps = sorted({item["map"] for item in members})
            candidates.append({
                "candidate_id": f"candidate:{subject}:{signature}",
                "subject": subject,
                "signature": signature,
                "occurrence_count": len(members),
                "map_count": len(maps),
                "maps": maps,
                "occurrences": [
                    {"map": item["map"], "focus": item["focus"], "population": item["population"]}
                    for item in members
                ],
                "common_properties": _common_properties(subject, signature, members),
                "status": "unsigned",
            })
    excluded_candidates = _cluster_excluded(excluded)
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "default_samples": len(samples),
            "excluded_samples": len(excluded),
            "excluded_reasons": dict(sorted(Counter(
                reason for item in excluded
                for reason in item.get("excluded_because", ())
                or ("unstated",)).items())),
            "note": "default statistics cover reachable geometry and visible "
                    "objects; the excluded remainder is wiring evidence, "
                    "clustered under excluded_candidates",
        },
        "excluded_candidates": excluded_candidates,
        "kind": "derived",
        "model": "discrete independent-view signatures; names are not assigned here",
        "sample_count": sum(len(items) for items in by_subject.values()),
        "candidates": candidates,
        "medians": medians,
        "limitations": [
            "signatures are quantized; nearby geometry may split across bins",
            "2D sight ignores height and sprites",
            "campaign and bloodbath populations must be mined separately",
        ],
    }


def _common_properties(subject: str, signature: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    parts = dict(item.split(":", 1) for item in signature.split("|") if ":" in item)
    return {
        "signature_parts": parts,
        "count": len(members),
        "maps": sorted({item["map"] for item in members}),
    }


def _cluster_excluded(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The same clustering, over what the default scope holds back."""
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in samples:
        subject = str(item["subject"])
        signer = _SIGNATURES.get(subject)
        if signer is None or subject == "spawn-neighborhood":
            continue
        #: An excluded sample is keyed on what it *does* hold. Keying it on the
        #: visible objects it does not have would file every sound-marker
        #: pocket in the campaign under one meaningless `objects:0` bucket.
        if "wiring_signature" in item:
            keyed = dict(item)
            keyed["context_signature"] = item["wiring_signature"]
            buckets[(subject, signer(keyed))].append(item)
        else:
            buckets[(subject, signer(item))].append(item)
    out = []
    for (subject, signature), members in sorted(
            buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        maps = sorted({item["map"] for item in members})
        out.append({
            "candidate_id": f"excluded:{subject}:{signature}",
            "subject": subject,
            "signature": signature,
            "occurrence_count": len(members),
            "map_count": len(maps),
            "maps": maps,
            "reasons": dict(sorted(Counter(
                reason for item in members
                for reason in item.get("excluded_because", ())).items())),
            "sector_kinds": dict(sorted(Counter(
                item.get("sector_kind", "unknown") for item in members).items())),
            "wiring_categories": dict(sorted(Counter(
                category for item in members
                for category, count in item.get("wiring_categories", {}).items()
                for _ in range(count)).items())),
            "keyed_on": "wiring" if any("wiring_signature" in item for item in members)
                        else "visible objects",
            "occurrences": [
                {"map": item["map"], "focus": item["focus"],
                 "population": item["population"]}
                for item in members
            ],
            "status": "excluded-from-default-statistics",
        })
    return out


def mine_directory(
    directory: str | Path | None = None, *, population: str,
    tier: str | None = None, limit: int | None = None,
) -> dict[str, Any]:
    """Mine one population, optionally one tier of it, optionally a prefix.

    `limit` takes the first `limit` maps in enumeration order -- a bounded
    sample, not a random one, so a rerun mines the same maps. The report says
    how many were available so a reader can see it was a sample.
    """
    import sys

    selected = list_corpus_maps(directory, population=population, tier=tier)
    available = len(selected)
    paths = [item.path for item in (selected[:limit] if limit else selected)]
    if not paths:
        raise PatternError(
            f"no maps for population {population}"
            + (f" tier {tier}" if tier else "")
            + f" in {corpus_root(directory)}"
        )
    samples: list[dict[str, Any]] = []
    errors = []
    for index, path in enumerate(paths, start=1):
        print(f"[{index}/{len(paths)}] {path.name}", file=sys.stderr, flush=True)
        try:
            samples.extend(observe_map(path, population=population))
        except Exception as exc:
            errors.append({"map": path.name, "error": str(exc)})
    clustered = cluster_samples(samples)
    clustered["population"] = population
    clustered["tier"] = tier
    clustered["maps_mined"] = [path.name for path in paths]
    clustered["maps_available"] = available
    clustered["sampled"] = len(paths) < available
    clustered["observe_errors"] = errors
    return clustered


def signature_parts(signature: str | dict[str, Any] | None) -> dict[str, str]:
    if signature is None:
        return {}
    if isinstance(signature, dict):
        return {str(key): str(value) for key, value in signature.items()}
    return dict(item.split(":", 1) for item in str(signature).split("|") if ":" in item)


def parts_satisfy(parts: dict[str, str], require: dict[str, Any] | None) -> bool:
    """True when every required key equals the quantized signature part."""
    if not require:
        return True
    for key, value in require.items():
        if key in {"tag", "status", "scale", "id", "population"}:
            continue
        if str(parts.get(key)) != str(value):
            return False
    return True


def sample_signature(sample: dict[str, Any], medians: dict[str, float] | None = None) -> str:
    subject = sample["subject"]
    medians = medians or {"spawn_area": 1.0, "local_area": 1.0}
    if subject == "spawn-neighborhood":
        return _spawn_signature(sample, medians)
    if subject == "route-exposure":
        return _route_signature(sample)
    if subject == "local-morphology":
        return _morph_signature(sample)
    if subject == "vertical-transition":
        return _vertical_signature(sample)
    raise PatternError(f"unknown subject {subject!r}")


def pattern_matches_signature(pattern: dict[str, Any], signature: str) -> bool:
    """A sample may match several patterns; exact string equality is not required."""
    parts = signature_parts(signature)
    match = pattern.get("match") or {}
    if match:
        return parts_satisfy(parts, match)
    listed = pattern.get("signatures") or []
    if listed:
        return signature in listed or any(parts_satisfy(parts, signature_parts(item)) for item in listed)
    stored = pattern.get("signature")
    if isinstance(stored, dict) and stored:
        return parts_satisfy(parts, stored)
    if isinstance(stored, str) and "|" in stored:
        return signature == stored or parts_satisfy(parts, signature_parts(stored))
    return False


def load_catalog(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def query_catalog(
    catalog: dict[str, Any],
    *,
    view: str | None = None,
    require: dict[str, Any] | None = None,
    map_name: str | None = None,
    population: str | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return multiple matching pattern occurrences, never a single best match."""
    require = require or {}
    buckets: list[list[dict[str, Any]]] = []
    for pattern in catalog.get("patterns") or []:
        if view and view not in {
            pattern.get("view"), pattern.get("scale"), pattern.get("subject"),
        }:
            continue
        if population and pattern.get("population") != population:
            continue
        tags = [str(item) for item in (pattern.get("tags") or [])]
        parts = signature_parts(pattern.get("match") or pattern.get("signature"))
        ok = True
        for key, value in require.items():
            expected = str(value)
            if key == "tag":
                ok = expected in tags
            elif key in parts:
                ok = str(parts.get(key)) == expected
            elif key in {"status", "scale", "subject", "population"}:
                ok = str(pattern.get(key)) == expected
            elif expected in tags:
                ok = True
            else:
                ok = False
            if not ok:
                break
        if not ok:
            continue
        bucket = []
        for occurrence in pattern.get("occurrences") or []:
            if map_name and occurrence.get("map") != map_name:
                continue
            bucket.append({
                "pattern_id": pattern["id"],
                "status": pattern.get("status"),
                "subject": pattern.get("subject"),
                "signature": pattern.get("signature") or pattern.get("match"),
                "occurrence": occurrence,
                "interpretation": (pattern.get("interpretation") or {}).get("label"),
            })
        if bucket:
            buckets.append(bucket)
    hits = []
    while buckets and len(hits) < limit:
        remaining = []
        for bucket in buckets:
            hits.append(bucket.pop(0))
            if bucket:
                remaining.append(bucket)
            if len(hits) >= limit:
                break
        buckets = remaining
    return hits


def inspect_pattern(catalog: dict[str, Any], pattern_id: str) -> dict[str, Any]:
    for pattern in catalog.get("patterns") or []:
        if pattern.get("id") == pattern_id:
            return pattern
    raise PatternError(f"unknown pattern {pattern_id!r}")


def match_samples_to_catalog(samples: list[dict[str, Any]], catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach every matching catalog hypothesis to a sample. Overlap is allowed."""
    medians = catalog.get("medians") or {"spawn_area": 40.0, "local_area": 200.0}
    matches = []
    for sample in samples:
        subject = sample["subject"]
        if subject not in _SIGNATURES:
            continue
        signature = sample_signature(sample, medians)
        for pattern in catalog.get("patterns") or []:
            if pattern.get("subject") != subject:
                continue
            if not pattern_matches_signature(pattern, signature):
                continue
            matches.append({
                "pattern_id": pattern["id"],
                "status": pattern.get("status"),
                "subject": subject,
                "signature": signature,
                "focus": sample["focus"],
                "interpretation": (pattern.get("interpretation") or {}).get("label"),
                "confidence": pattern.get("confidence"),
            })
    return matches


def attach_corpus_occurrences(
    catalog: dict[str, Any],
    unsigned: dict[str, Any],
    *,
    max_occurrences: int = 32,
) -> dict[str, Any]:
    """Fill pattern occurrence lists from an unsigned mine of one population."""
    if catalog.get("medians") is None and unsigned.get("medians"):
        catalog["medians"] = unsigned["medians"]
    rows: list[dict[str, Any]] = []
    for candidate in unsigned.get("candidates") or []:
        for occurrence in candidate.get("occurrences") or []:
            rows.append({
                "subject": candidate["subject"],
                "signature": candidate["signature"],
                "map": occurrence["map"],
                "focus": occurrence.get("focus"),
                "population": occurrence.get("population") or unsigned.get("population"),
            })
    for pattern in catalog.get("patterns") or []:
        if pattern.get("population") and unsigned.get("population"):
            if pattern["population"] != unsigned["population"]:
                continue
        hits = [
            item for item in rows
            if item["subject"] == pattern.get("subject")
            and pattern_matches_signature(pattern, item["signature"])
        ]
        maps = sorted({item["map"] for item in hits})
        pattern["occurrence_count"] = len(hits)
        pattern["map_count"] = len(maps)
        pattern["maps"] = maps
        pattern["occurrences"] = [
            {
                "map": item["map"],
                "focus": item["focus"],
                "population": item["population"],
                "signature": item["signature"],
            }
            for item in hits[:max_occurrences]
        ]
        pattern["occurrences_truncated"] = len(hits) > max_occurrences
    return catalog


def pattern_aware_understanding(
    disk: DiskMap, catalog: dict[str, Any], *, map_id: str, population: str,
    include_sp_start: bool | None = None,
) -> dict[str, Any]:
    from .understanding import understand_map
    if include_sp_start is None:
        include_sp_start = population == "blood-campaign"
    packet = understand_map(disk, include_sp_start=include_sp_start)
    samples = []
    samples.extend(observe_spawn_neighborhoods(
        disk, map_id=map_id, population=population, force=True,
    ))
    samples.extend(observe_routes(
        disk, map_id=map_id, population=population,
        include_sp_start=population == "blood-campaign",
    ))
    samples.extend(observe_morphology(disk, map_id=map_id, population=population))
    samples.extend(observe_vertical(disk, map_id=map_id, population=population))
    matches = match_samples_to_catalog(samples, catalog)
    sky = packet.get("space") or {}
    sky_space = (sky.get("sky") or {}).get("footprint_player_areas") or 0
    cov_space = (sky.get("covered") or {}).get("footprint_player_areas") or 0
    sky_sectors = (sky.get("sky") or {}).get("sector_count") or 0
    cov_sectors = (sky.get("covered") or {}).get("sector_count") or 0
    total_area = sky_space + cov_space
    total_sectors = sky_sectors + cov_sectors
    packet["patterns"] = {
        "catalog": catalog.get("id"),
        "match_count": len(matches),
        "by_pattern": dict(Counter(item["pattern_id"] for item in matches)),
        "matches": matches,
        "area_vs_sector": {
            "sky_area_fraction": None if not total_area else round(sky_space / total_area, 4),
            "sky_sector_fraction": None if not total_sectors else round(sky_sectors / total_sectors, 4),
            "note": "sector count and footprint can disagree; both are evidence",
        },
        "limitations": [
            "matches are hypotheses over quantized signatures",
            "absence of a match is not evidence the relation is absent",
            "2D spawn sight ignores height",
        ],
    }
    return packet
