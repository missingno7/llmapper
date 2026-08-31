"""Anchor queries: from a sparse label to the structure around it.

`tools/mine_e6m1_shop.py` and `tools/mine_sewer_kit.py` are two hand-written
miners that do the same four things -- resolve a role to tiles, find every
occurrence, collect the carrying sectors, widen by one portal hop -- and then
stop at "here is the tile and its neighbours". Writing a third by hand would
copy that code a third time, so this module is the general form of the two,
and it goes one step further than either.

The step is the one `03_...md` asks for. An anchor is a sparse
high-confidence label, not a concept; it seeds a corpus query. So after
collecting occurrences this module reduces each carrying sector's Phase 1
relation neighborhood to a **discrete context signature**, clusters the
occurrences by it, and then asks the two questions a tile lookup cannot:

- which occurrences do *not* fit the dominant context (counterexamples), and
- which sectors have the dominant context but **none of the anchor tiles**
  (anchor-free analogues -- 03's "structurally equivalent examples using
  different art").

What it does not do is decide that an analogue *is* the anchored thing. A
matching signature is a candidate and is labelled one. Naming happens later,
by review, and never here.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .build_ir import BuildIR
from .patterns import list_corpus_maps
from .relations import (
    CONTEXT_FACETS, OBJECT_FACETS, context_signature, extract_relations,
    signature_facets,
)


SCHEMA = "llmapper.anchor-query"
SCHEMA_VERSION = 1

#: Where a tile can be used. The three surfaces both hand-written miners
#: search, kept as one implementation instead of two near-copies.
OCCURRENCE_FIELDS = {
    "wall": ("picnum", "over_picnum"),
    "surface": ("floor_picnum", "ceiling_picnum"),
    "sprite": ("picnum",),
}


class AnchorError(ValueError):
    pass


@dataclass(frozen=True)
class AnchorSpec:
    """A sparse label: a role name and the tiles that stand for it."""

    name: str
    tiles: tuple[int, ...]
    #: How the tiles were obtained, carried into the report so a reader can
    #: tell an owner's hand-tagged list from a material's declared surfaces.
    origin: str = "explicit tiles"

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "tiles": list(self.tiles), "origin": self.origin}


def anchor_from_tiles(name: str, tiles: Iterable[int]) -> AnchorSpec:
    values = tuple(sorted({int(value) for value in tiles}))
    if not values:
        raise AnchorError(f"anchor {name!r} has no tiles")
    return AnchorSpec(name=name, tiles=values)


def anchor_from_material(name: str) -> AnchorSpec:
    """The declared surfaces of a named `surfaces.Material`."""
    from .surfaces import MATERIALS, SurfaceError

    try:
        found = MATERIALS[name]
    except KeyError as exc:
        raise AnchorError(
            f"no material named {name!r}; known: {', '.join(sorted(MATERIALS))}"
        ) from exc
    tiles = {found.wall, found.floor}
    if not found.sky:
        tiles.add(found.ceiling)
    if found.opening is not None:
        tiles.add(found.opening)
    return AnchorSpec(name=f"material:{name}", tiles=tuple(sorted(tiles)),
                      origin=f"surfaces.MATERIALS[{name!r}] declared surfaces")


def anchor_from_regions(
    build: BuildIR, sector_ids: Iterable[int], *, name: str, source: str = "",
) -> AnchorSpec:
    """Every tile the given example sectors actually use.

    This is the `03_...md` "these source maps/regions are examples" input: the
    owner points at a place instead of at a tile list.
    """
    tiles: set[int] = set()
    selected = [int(value) for value in sector_ids]
    for sector_id in selected:
        if not 0 <= sector_id < len(build.sectors):
            raise AnchorError(f"sector:{sector_id} is out of range")
        fields = build.sectors[sector_id]["fields"]
        tiles.add(int(fields["floor_picnum"]))
        tiles.add(int(fields["ceiling_picnum"]))
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        for wall_id in range(first, first + count):
            if 0 <= wall_id < len(build.walls):
                tiles.add(int(build.walls[wall_id]["fields"]["picnum"]))
    for sprite in build.sprites:
        if int(sprite["fields"]["sector"]) in set(selected):
            tiles.add(int(sprite["fields"]["picnum"]))
    origin = f"tiles used by sectors {sorted(selected)}"
    return AnchorSpec(name=name, tiles=tuple(sorted(tiles)),
                      origin=f"{origin} of {source}" if source else origin)


def _wall_owners(build: BuildIR) -> list[int]:
    owners = [-1] * len(build.walls)
    for sector_id, sector in enumerate(build.sectors):
        first = int(sector["fields"]["wall_ptr"])
        count = int(sector["fields"]["wall_count"])
        for wall_id in range(first, first + count):
            if 0 <= wall_id < len(owners):
                owners[wall_id] = sector_id
    return owners


def find_occurrences(build: BuildIR, tiles: Iterable[int]) -> list[dict[str, Any]]:
    """Every use of the anchor tiles, as wall, surface or sprite.

    One `over_picnum` and one `picnum` on the same wall are two uses, and a
    floor and a ceiling of the same tile are two uses. That is the counting
    both hand-written miners already do, kept identical so their reports stay
    reproducible through this path.
    """
    wanted = {int(value) for value in tiles}
    owners = _wall_owners(build)
    found: list[dict[str, Any]] = []
    for wall_id, wall in enumerate(build.walls):
        for field in OCCURRENCE_FIELDS["wall"]:
            if int(wall["fields"][field]) in wanted:
                found.append({
                    "kind": "wall", "ref": f"wall:{wall_id}", "sector": owners[wall_id],
                    "field": field, "picnum": int(wall["fields"][field]),
                })
    for sector_id, sector in enumerate(build.sectors):
        for field in OCCURRENCE_FIELDS["surface"]:
            if int(sector["fields"][field]) in wanted:
                found.append({
                    "kind": "surface", "ref": f"sector:{sector_id}", "sector": sector_id,
                    "field": field, "picnum": int(sector["fields"][field]),
                })
    for sprite_id, sprite in enumerate(build.sprites):
        if int(sprite["fields"]["picnum"]) in wanted:
            found.append({
                "kind": "sprite", "ref": f"sprite:{sprite_id}",
                "sector": int(sprite["fields"]["sector"]),
                "field": "picnum", "picnum": int(sprite["fields"]["picnum"]),
            })
    return found


def _map_signatures(
    build: BuildIR, sector_ids: Sequence[int], *, hops: int,
) -> tuple[dict[int, dict[str, str]], list[dict[str, Any]]]:
    """Signature per sector at two scales, plus whatever refused to compute.

    Scale 1 is the sector's own contents; scale 2 is one hop out. Scales 3+ are
    a perceptual space and an architectural context, which `decompiler.py`
    already recovers; this module does not compute them a second time.

    Failures are returned, never swallowed. `spatial.analyze_spatial` validates
    wall ownership across the **whole map** before analysing any selection, so
    one malformed sector anywhere makes every local query on that map fail --
    which is a fact about the map worth reporting, not a reason to guess.
    """
    out: dict[int, dict[str, str]] = {}
    failures: list[dict[str, Any]] = []
    for sector_id in sector_ids:
        try:
            local = extract_relations(build, sectors=[sector_id], hops=0)
            wider = extract_relations(build, sectors=[sector_id], hops=hops)
        except Exception as exc:
            failures.append({"sector": sector_id, "error": f"{type(exc).__name__}: {exc}"})
            continue
        out[sector_id] = {
            "scale_1": context_signature(local, sector_id, facets=OBJECT_FACETS),
            "scale_2": context_signature(wider, sector_id),
        }
    return out, failures


def mine_anchor(
    spec: AnchorSpec,
    *,
    directory: str | Path | None = None,
    population: str | None = "blood-campaign",
    view: str | None = None,
    top_maps: int = 3,
    hops: int = 1,
    analogues: bool = True,
    analogue_limit: int = 25,
) -> dict[str, Any]:
    """Run one anchor query over a population.

    Occurrences are counted across every map in the population -- that is cheap
    and it is what the two hand-written miners report. Signatures, clusters,
    counterexamples and analogues are computed only for the `top_maps` densest
    maps, because they need a relation neighborhood per sector and the report
    should say plainly which maps it looked at.
    """
    from .format import read_map

    selected = list_corpus_maps(directory, population=population, view=view)
    if not selected:
        raise AnchorError(f"no maps for population={population!r} view={view!r}")

    per_map: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for item in selected:
        try:
            build = read_map(item.path).to_build_ir()
        except Exception as exc:
            errors.append({"map": item.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        found = find_occurrences(build, spec.tiles)
        if not found:
            continue
        per_map.append({
            "map": item.name,
            "population": item.population,
            "relative": item.relative,
            "uses": len(found),
            "uses_by_kind": dict(Counter(item_["kind"] for item_ in found)),
            "tile_counts": {str(tile): count for tile, count
                            in sorted(Counter(item_["picnum"] for item_ in found).items())},
            "carrying_sectors": sorted({item_["sector"] for item_ in found}),
        })
    per_map.sort(key=lambda entry: (-entry["uses"], entry["map"]))

    studied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    analogue_rows: list[dict[str, Any]] = []
    # Densest first, but a map that cannot be analysed must not consume a study
    # slot -- and must be named. `spatial.analyze_spatial` validates the whole
    # map's wall ownership before any selection, so one malformed sector costs
    # the entire map.
    for entry in per_map:
        if len(studied) >= top_maps:
            break
        path = next(item.path for item in selected if item.name == entry["map"])
        build = read_map(path).to_build_ir()
        carrying = entry["carrying_sectors"]
        signatures, failures = _map_signatures(build, carrying, hops=hops)
        if not signatures:
            skipped.append({
                "map": entry["map"], "uses": entry["uses"],
                "carrying_sectors": len(carrying),
                "reason": failures[0]["error"] if failures else "no signatures computed",
            })
            continue
        for sector_id in carrying:
            if sector_id not in signatures:
                continue
            occurrences.append({
                "map": entry["map"], "population": entry["population"],
                "sector": sector_id, **signatures[sector_id],
            })
        studied.append({
            "map": entry["map"], "uses": entry["uses"],
            "carrying_sectors": len(carrying),
            "signatures_computed": len(signatures),
            "sectors_that_would_not_compute": len(failures),
        })
        if analogues:
            anchored = set(carrying)
            others = [sector_id for sector_id in range(len(build.sectors))
                      if sector_id not in anchored]
            found_rows, _ignored = _map_signatures(build, others, hops=hops)
            for sector_id, found in found_rows.items():
                analogue_rows.append({
                    "map": entry["map"], "sector": sector_id, **found,
                })

    clusters = _cluster(occurrences)
    dominant = clusters[0]["signature"] if clusters else None
    counterexamples = [
        item for item in occurrences
        if dominant is not None and item["scale_2"] != dominant
    ]
    rare = {cluster["signature"] for cluster in clusters if cluster["count"] <= 2}
    enrichment = _enrichment(dominant, occurrences, analogue_rows)
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "anchor": spec.to_dict(),
        "selection": {"population": population, "view": view,
                      "maps_searched": len(selected), "hops": hops,
                      "top_maps_studied": top_maps},
        "maps_with_use": len(per_map),
        "total_uses": sum(entry["uses"] for entry in per_map),
        "per_map": per_map,
        "studied": studied,
        "skipped_maps": skipped,
        "context_clusters": clusters,
        "dominant_context": enrichment,
        "counterexamples": {
            "count": len(counterexamples),
            "note": "occurrences of the anchor whose one-hop context differs from "
                    "the dominant one. These are where a tile-only reading breaks.",
            "in_rare_contexts": [item for item in counterexamples
                                 if item["scale_2"] in rare][:20],
        },
        "anchor_free_analogues": _analogues(analogue_rows, dominant, analogue_limit),
        "errors": errors,
        "limitations": [
            "An analogue shares the anchor's dominant context signature and "
            "carries none of its tiles. That makes it a candidate, not the same "
            "thing: this module never decides an analogue IS the anchored object.",
            "Signatures describe a sector's role among its neighbours -- portals, "
            "enclosure, stacking, coplanarity, and what its objects do. They do "
            "not describe shape, so two differently shaped rooms can key alike.",
            "Occurrence counts span the whole population; signatures, clusters "
            "and analogues cover only the densest maps named in `studied`. Maps "
            "that could not be analysed are named in `skipped_maps` with the "
            "reason, and did not consume a study slot.",
            "Every row is an OBSERVATION. Role names come from the anchor spec "
            "and are the owner's, never inferred here.",
        ],
    }


def _enrichment(
    dominant: str | None,
    occurrences: Sequence[dict[str, Any]],
    others: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Is the dominant context actually associated with the anchor?

    The question a tile lookup never asks. A context that half the map shares
    says nothing about the anchor no matter how often the anchor sits in it, so
    the number that matters is how much *more* common it is where the anchor is
    than where it is not. Enrichment near 1 means the signature is describing
    the map, not the anchor -- and the tool should say so about itself.
    """
    if dominant is None:
        return {"signature": None, "note": "no occurrence produced a signature"}
    anchored_hits = sum(1 for item in occurrences if item["scale_2"] == dominant)
    other_hits = sum(1 for item in others if item["scale_2"] == dominant)
    anchored_share = anchored_hits / len(occurrences) if occurrences else None
    other_share = other_hits / len(others) if others else None
    ratio = (round(anchored_share / other_share, 2)
             if anchored_share and other_share else None)
    return {
        "signature": dominant,
        "facets": signature_facets(dominant),
        "anchored": {"hits": anchored_hits, "of": len(occurrences),
                     "share": round(anchored_share, 4) if anchored_share is not None else None},
        "unanchored": {"hits": other_hits, "of": len(others),
                       "share": round(other_share, 4) if other_share is not None else None},
        "enrichment": ratio,
        "reading": (
            "how much more often the anchor's sectors carry this context than "
            "sectors without any anchor tile, in the same maps. 1.0 would mean "
            "the context says nothing about the anchor."
        ),
    }


def _cluster(occurrences: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in occurrences:
        grouped[item["scale_2"]].append(item)
    clusters = [
        {
            "signature": signature,
            "facets": signature_facets(signature),
            "count": len(members),
            "maps": sorted({item["map"] for item in members}),
            "examples": [{"map": item["map"], "sector": item["sector"]}
                         for item in members[:6]],
        }
        for signature, members in grouped.items()
    ]
    clusters.sort(key=lambda cluster: (-cluster["count"], cluster["signature"]))
    return clusters


def _analogues(
    rows: Sequence[dict[str, Any]], dominant: str | None, limit: int,
) -> dict[str, Any]:
    if dominant is None:
        return {"dominant_context": None, "count": 0, "examples": []}
    matches = [item for item in rows if item["scale_2"] == dominant]
    return {
        "dominant_context": dominant,
        "sectors_searched": len(rows),
        "count": len(matches),
        "share_of_searched": round(len(matches) / len(rows), 4) if rows else None,
        "examples": [{"map": item["map"], "sector": item["sector"]}
                     for item in matches[:limit]],
        "note": "sectors carrying none of the anchor tiles whose one-hop context "
                "matches the anchor's dominant context. Candidates for the same "
                "structure built from different art -- not a claim that they are.",
    }


def load_kit(path: str | Path) -> list[AnchorSpec]:
    """Read a role->tiles table, including from a report that already has one.

    Both hand-written miners write their `role_assets` table into their report,
    so an existing reference report can drive this tool directly -- which is how
    the two of them are reproduced through the general path rather than
    re-typed into it.
    """
    import json

    document = json.loads(Path(path).read_text(encoding="utf-8"))
    table = document.get("role_assets", document) if isinstance(document, dict) else None
    if not isinstance(table, dict) or not table:
        raise AnchorError(f"{path} has no role_assets table")
    specs = []
    for name, tiles in table.items():
        if not isinstance(tiles, (list, tuple)) or not all(
            isinstance(tile, int) and not isinstance(tile, bool) for tile in tiles
        ):
            raise AnchorError(
                f"{path}: role {name!r} must map to a list of tile numbers, got {tiles!r}"
            )
        specs.append(anchor_from_tiles(str(name), tiles))
    return specs


def mine_kit(specs: Sequence[AnchorSpec], **kwargs: Any) -> dict[str, Any]:
    """Run one anchor query per role and collect them under one report."""
    if not specs:
        raise AnchorError("a kit needs at least one anchor")
    roles = {spec.name: mine_anchor(spec, **kwargs) for spec in specs}
    return {
        "$schema": "llmapper.anchor-kit",
        "schema_version": SCHEMA_VERSION,
        "role_assets": {spec.name: list(spec.tiles) for spec in specs},
        "selection": next(iter(roles.values()))["selection"],
        "roles": roles,
    }
