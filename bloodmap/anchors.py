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
from dataclasses import dataclass, replace
from math import hypot
from statistics import mean, pstdev
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .build_ir import BuildIR
from .patterns import list_corpus_maps
from .player_space import player_profile
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


# ---------------------------------------------------------------------------
# Contrast: which relations actually separate two anchored classes
# ---------------------------------------------------------------------------
#
# `03_...md` lists candidate discriminators for confusing pairs -- shelf vs
# crate pile, storefront vs window -- and says to mine the differences instead
# of guessing them. The classes are defined by owner-tagged tiles, so the one
# thing a result here may *not* rest on is the tile: a separator that is really
# texture identity is a finding to report, not a success.

#: Relational features, and the `03_...md` discriminator each stands for.
#: Every one is read from Phase 1 relations or from the sector's own portal
#: measurements. None of them reads a picnum.
CONTRAST_FEATURES: dict[str, str] = {
    "objects_held": "contains_smaller_props: how many *visible* sprites the "
                    "sector carries",
    "wiring_objects_held": "how many non-visible wiring sprites it carries -- "
                           "reported, never counted as furniture",
    "objects_resting": "supports: how many of them sit on one of its planes",
    "objects_against_wall": "against_wall, counted over the sector's own objects",
    "portals": "open_front vs privileged_front: how many ways in",
    "enterable": "requires_access_clearance: some portal a player can walk through",
    "solid_closed_volume": "no portal a player can walk through",
    "max_step_player_heights": "the biggest step up from a neighbour",
    "min_opening_player_heights": "the tightest at-rest opening into it",
    "stands_above_a_neighbour": "above: a volume stacked over another volume. "
                                "Not the same as a raised platform -- a crate "
                                "inside a room sits above that room's floor, "
                                "not above its ceiling.",
    "raised_above_all_neighbours": "the platform reading of stackable_identical_"
                                   "units: this sector's floor is higher than "
                                   "every neighbour's",
    "rise_over_neighbours_player_heights": "how far its floor stands proud of "
                                           "the lowest neighbour",
    "stands_under_a_neighbour": "below: something overhangs it",
    "inside_another_sector": "inside: a volume cut into a bigger one",
    "shares_a_plane": "coplanar_with a neighbour's floor or ceiling",
    "in_a_repeating_run": "repeats_along: its objects form an even row",
    "twin_neighbours": "stackable_identical_units: neighbours of the same "
                       "footprint and clear height",
    "clear_height_player_heights": "standing room, or not a place at all",
    "area_player_areas": "plan size; a bounding-box measure, kept to be rejected",
    "solid_wall_share": "share of its own walls that are one-sided",
}

#: Blood's step limit, from `vocabulary.staircase`. A neighbour higher than
#: this cannot be walked into.
MAX_STEP_PLAYER_HEIGHTS = 4096 / 16960

BOOLEAN_FEATURES = (
    "enterable", "solid_closed_volume", "stands_above_a_neighbour",
    "raised_above_all_neighbours",
    "stands_under_a_neighbour", "inside_another_sector", "shares_a_plane",
    "in_a_repeating_run",
)


def carrier_features(
    build: BuildIR, sector_id: int, document: dict[str, Any],
) -> dict[str, Any]:
    """Relational features of one carrying sector. No picnum is read."""
    from .relations import _id, _polygon_loops, _signed_area

    ref = f"sector:{sector_id}"
    relations = document["relations"]
    #: Visible objects only. Roughly a quarter of every campaign map's sprites
    #: are sector-sound markers, link markers, starts and generators; counting
    #: them made `objects_held` measure the editor's wiring. The wiring stays
    #: in the document and is counted separately below.
    own = {item["subject"] for item in relations
           if item["kind"] == "in_sector" and item["object"] == ref
           and item["measures"].get("visibility") != "wiring"}
    wiring = {item["subject"] for item in relations
              if item["kind"] == "in_sector" and item["object"] == ref
              and item["measures"].get("visibility") == "wiring"}
    portals = [item for item in relations
               if item["kind"] == "adjacent_to" and ref in (item["subject"], item["object"])]
    steps = [item["measures"]["step_player_heights"] for item in portals]
    openings = [item["measures"]["opening_player_heights"] for item in portals]
    enterable = any(
        item["measures"]["opening_player_heights"] >= 1.0
        and item["measures"]["step_player_heights"] <= MAX_STEP_PLAYER_HEIGHTS
        and not item["measures"]["blocking_flag"]
        for item in portals
    )

    fields = build.sectors[sector_id]["fields"]
    clear = (int(fields["floor_z"]) - int(fields["ceiling_z"])) / 16960
    loops = _polygon_loops(build, sector_id)
    area = abs(sum(_signed_area(loop) for loop in loops)) / (384 ** 2)
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    walls = [build.walls[w]["fields"] for w in range(first, first + count)
             if 0 <= w < len(build.walls)]
    solid = sum(1 for w in walls if int(w["next_sector"]) < 0)

    #: Twins: neighbours with the same footprint area and clear height. A crate
    #: in a stack has them; a shelf recess does not.
    twins = 0
    for other in document["neighborhood"]["sectors"]:
        if other == sector_id or not 0 <= other < len(build.sectors):
            continue
        other_fields = build.sectors[other]["fields"]
        other_loops = _polygon_loops(build, other)
        if not other_loops:
            continue
        other_area = abs(sum(_signed_area(loop) for loop in other_loops)) / (384 ** 2)
        other_clear = (int(other_fields["floor_z"]) - int(other_fields["ceiling_z"])) / 16960
        if area > 0 and abs(other_area - area) / area <= 0.05 and abs(other_clear - clear) <= 0.05:
            twins += 1

    #: A raised platform, which `above` does not capture: a crate inside a room
    #: has that room's *floor* below it, not its ceiling. Blood z grows
    #: downward, so a higher floor is a smaller floor_z.
    floor_z = int(fields["floor_z"])
    neighbour_floors = []
    for item in portals:
        other = _id(item["object"] if item["subject"] == ref else item["subject"])
        if 0 <= other < len(build.sectors):
            neighbour_floors.append(int(build.sectors[other]["fields"]["floor_z"]))
    rise = (max(neighbour_floors) - floor_z) / 16960 if neighbour_floors else 0.0

    return {
        "objects_held": len(own),
        "wiring_objects_held": len(wiring),
        "raised_above_all_neighbours": bool(neighbour_floors) and all(
            floor_z < other for other in neighbour_floors),
        "rise_over_neighbours_player_heights": round(rise, 4),
        "objects_resting": sum(1 for item in relations
                               if item["kind"] == "rests_on" and item["subject"] in own),
        "objects_against_wall": sum(1 for item in relations
                                    if item["kind"] == "against_wall" and item["subject"] in own),
        "portals": len(portals),
        "enterable": enterable,
        "solid_closed_volume": not enterable,
        "max_step_player_heights": round(max(steps), 4) if steps else 0.0,
        "min_opening_player_heights": round(min(openings), 4) if openings else 0.0,
        "stands_above_a_neighbour": any(item["kind"] == "above" and item["subject"] == ref
                                        for item in relations),
        "stands_under_a_neighbour": any(item["kind"] == "above" and item["object"] == ref
                                        for item in relations),
        "inside_another_sector": any(item["kind"] == "inside" and item["subject"] == ref
                                     for item in relations),
        "shares_a_plane": any(item["kind"] == "shares_plane" and ref in item.get("members", [])
                              for item in relations),
        "in_a_repeating_run": any(item["kind"] == "repeats_along" and own & set(item.get("members", []))
                                  for item in relations),
        "twin_neighbours": twins,
        "clear_height_player_heights": round(clear, 4),
        "area_player_areas": round(area, 4),
        "solid_wall_share": round(solid / max(1, len(walls)), 4),
    }


def _separation(name: str, positives: list[Any], comparison: list[Any]) -> dict[str, Any]:
    """How well one feature separates two classes, stated honestly.

    Booleans report the share on each side. Numerics report each side's median
    and the single threshold that maximizes balanced accuracy, with the two
    rates kept separate -- on a 28-vs-1250 split a headline accuracy would be
    98% for a rule that never fires.
    """
    if not positives or not comparison:
        return {"feature": name, "verdict": "no data"}
    if isinstance(positives[0], bool):
        share_pos = sum(bool(v) for v in positives) / len(positives)
        share_neg = sum(bool(v) for v in comparison) / len(comparison)
        balanced = (share_pos + (1 - share_neg)) / 2
        return {
            "feature": name, "kind": "boolean",
            "positive_share": round(share_pos, 4),
            "comparison_share": round(share_neg, 4),
            "difference": round(share_pos - share_neg, 4),
            "balanced_accuracy": round(max(balanced, 1 - balanced), 4),
            "direction": "positive" if share_pos >= share_neg else "comparison",
        }
    edges = sorted({float(v) for v in positives} | {float(v) for v in comparison})
    best = None
    for index, edge in enumerate(edges):
        midpoint = edge if index == 0 else (edges[index - 1] + edge) / 2
        for sense in (1, -1):
            hit = sum(1 for v in positives if (v >= midpoint) == (sense > 0))
            miss = sum(1 for v in comparison if (v >= midpoint) == (sense > 0))
            tpr = hit / len(positives)
            tnr = 1 - miss / len(comparison)
            score = (tpr + tnr) / 2
            if best is None or score > best[0]:
                best = (score, midpoint, sense, tpr, tnr)
    score, threshold, sense, tpr, tnr = best
    return {
        "feature": name, "kind": "numeric",
        "positive_median": round(_median_of(positives), 4),
        "comparison_median": round(_median_of(comparison), 4),
        "rule": f"{name} {'>=' if sense > 0 else '<'} {round(threshold, 4)}",
        "positives_matching": round(tpr, 4),
        "comparison_matching": round(1 - tnr, 4),
        "balanced_accuracy": round(score, 4),
    }


def _median_of(values: list[Any]) -> float:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


#: Below this, a feature is reported as rejected rather than discriminating.
#: 0.65 balanced accuracy on a two-class split is barely above the 0.5 a coin
#: gets; anything under it is not a separator, and saying so is the point.
DISCRIMINATOR_FLOOR = 0.65


def contrast_anchor_sets(
    positive: AnchorSpec,
    comparison: AnchorSpec,
    *,
    directory: str | Path | None = None,
    population: str | None = None,
    view: str | None = "reference",
    hops: int = 1,
    examples: int = 8,
) -> dict[str, Any]:
    """Measure which relations separate two tile-anchored classes.

    Sectors carrying tiles from both anchors are **ambiguous**: they are held
    out of the measurement and reported, never assigned to a side.
    """
    from .format import read_map

    selected = list_corpus_maps(directory, population=population, view=view)
    if not selected:
        raise AnchorError(f"no maps for population={population!r} view={view!r}")

    rows: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    maps_with: Counter = Counter()
    for item in selected:
        try:
            build = read_map(item.path).to_build_ir()
        except Exception as exc:
            skipped.append({"map": item.name, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        pos_sectors = {o["sector"] for o in find_occurrences(build, positive.tiles)}
        neg_sectors = {o["sector"] for o in find_occurrences(build, comparison.tiles)}
        if not pos_sectors and not neg_sectors:
            continue
        overlap = pos_sectors & neg_sectors
        if pos_sectors:
            maps_with[positive.name] += 1
        if neg_sectors:
            maps_with[comparison.name] += 1
        failed = 0
        wanted = ([(s, positive.name) for s in sorted(pos_sectors - overlap)]
                  + [(s, comparison.name) for s in sorted(neg_sectors - overlap)])
        for sector_id, label in wanted:
            try:
                document = extract_relations(build, sectors=[sector_id], hops=hops)
            except Exception:
                failed += 1
                continue
            rows.append({
                "map": item.name, "population": item.population, "sector": sector_id,
                "label": label, **carrier_features(build, sector_id, document),
            })
        for sector_id in sorted(overlap):
            ambiguous.append({
                "map": item.name, "sector": sector_id,
                "reason": "carries tiles from both anchors",
            })
        if failed:
            skipped.append({
                "map": item.name, "carriers_unanalysable": failed,
                "reason": "the map failed whole-map wall-ownership validation",
            })

    positives = [row for row in rows if row["label"] == positive.name]
    comparisons = [row for row in rows if row["label"] == comparison.name]
    if not positives or not comparisons:
        raise AnchorError(
            f"contrast needs both sides: {len(positives)} {positive.name}, "
            f"{len(comparisons)} {comparison.name}"
        )
    measured = [
        _separation(name, [row[name] for row in positives],
                    [row[name] for row in comparisons])
        for name in CONTRAST_FEATURES
    ]
    measured.sort(key=lambda item: -item.get("balanced_accuracy", 0))
    discriminating = [m for m in measured
                      if m.get("balanced_accuracy", 0) >= DISCRIMINATOR_FLOOR]
    rejected = [m for m in measured
                if m.get("balanced_accuracy", 0) < DISCRIMINATOR_FLOOR]
    best = discriminating[0] if discriminating else None
    return {
        "$schema": "llmapper.anchor-contrast",
        "schema_version": SCHEMA_VERSION,
        "positive": positive.to_dict(),
        "comparison": comparison.to_dict(),
        "selection": {"population": population, "view": view, "hops": hops,
                      "maps_searched": len(selected)},
        "counts": {
            positive.name: {"sectors": len(positives), "maps": maps_with[positive.name]},
            comparison.name: {"sectors": len(comparisons), "maps": maps_with[comparison.name]},
            "ambiguous_sectors": len(ambiguous),
        },
        "feature_definitions": dict(CONTRAST_FEATURES),
        "discriminator_floor": DISCRIMINATOR_FLOOR,
        "discriminating": discriminating,
        "rejected": rejected,
        "ambiguous": ambiguous[:40],
        "counterexamples": _counterexamples(best, positives, comparisons, examples),
        "map_transfer": _map_transfer(best, positives),
        "skipped": skipped,
        "rows": rows,
        "limitations": [
            "Class membership comes from owner-tagged tiles. Every feature "
            "measured is relational and reads no picnum, so a separator that "
            "is really texture identity cannot hide as one of them.",
            "Balanced accuracy, not accuracy: on an imbalanced split a rule "
            "that never fires scores well on the raw rate.",
            "Thresholds are fitted on the same rows they are scored on. These "
            "are separations observed, not a validated classifier.",
            "Sectors carrying both anchors are held out and reported, never "
            "assigned to a side.",
            "`map_transfer` is the guard against a mapper's habit: a rule whose "
            "per-map share swings from near 0 to near 1 is separating maps.",
        ],
    }


def _map_transfer(
    best: dict[str, Any] | None, positives: list[dict[str, Any]],
) -> dict[str, Any]:
    """Does the best discriminator hold in every map, or only in one?

    The check that caught the first contrast pilot: its winning rule matched
    89% of one map's positives and 0% of another's, so it was separating maps
    rather than concepts. A rule fitted on two maps and tested on a third is
    the cheapest guard against reading a mapper's habit as a convention.
    """
    if best is None:
        return {"rule": None, "note": "no feature reached the discriminator floor"}
    name = best["feature"]
    if best["kind"] == "boolean":
        wanted = best["direction"] == "positive"

        def holds(row: dict[str, Any]) -> bool:
            return bool(row[name]) == wanted
    else:
        parts = best["rule"].split()
        sense, threshold = parts[1], float(parts[2])

        def holds(row: dict[str, Any]) -> bool:
            value = row[name]
            return value >= threshold if sense == ">=" else value < threshold

    maps = sorted({row["map"] for row in positives})
    per_map = {}
    for name_of_map in maps:
        subset = [row for row in positives if row["map"] == name_of_map]
        per_map[name_of_map] = {
            "positives": len(subset),
            "matching": round(sum(1 for row in subset if holds(row)) / len(subset), 4),
        }
    shares = [item["matching"] for item in per_map.values()]
    held_out = {}
    if len(maps) >= 2:
        for name_of_map in maps:
            rest = [row for row in positives if row["map"] != name_of_map]
            subset = [row for row in positives if row["map"] == name_of_map]
            held_out[name_of_map] = {
                "on_the_rest": round(sum(1 for row in rest if holds(row)) / len(rest), 4),
                "on_the_held_out_map": round(
                    sum(1 for row in subset if holds(row)) / len(subset), 4),
            }
    return {
        "rule": best.get("rule") or f"{name} is {best.get('direction') == 'positive'}",
        "maps": len(maps),
        "per_map": per_map,
        "spread": round(max(shares) - min(shares), 4) if shares else None,
        "leave_one_map_out": held_out,
        "reading": "a rule whose per-map share swings from near 0 to near 1 is "
                   "separating maps, not concepts. Spread near 0 means it "
                   "transfers.",
    }


def _counterexamples(
    best: dict[str, Any] | None, positives: list[dict[str, Any]],
    comparisons: list[dict[str, Any]], limit: int,
) -> dict[str, Any]:
    """Members the best discriminator gets wrong. Preserved, never pruned."""
    if best is None:
        return {"rule": None, "note": "no feature reached the discriminator floor"}
    name = best["feature"]
    if best["kind"] == "boolean":
        wanted = best["direction"] == "positive"
        wrong_pos = [row for row in positives if bool(row[name]) != wanted]
        wrong_neg = [row for row in comparisons if bool(row[name]) == wanted]
        rule = f"{name} is {wanted}"
    else:
        parts = best["rule"].split()
        sense, threshold = parts[1], float(parts[2])

        def holds(value: float) -> bool:
            return value >= threshold if sense == ">=" else value < threshold

        wrong_pos = [row for row in positives if not holds(row[name])]
        wrong_neg = [row for row in comparisons if holds(row[name])]
        rule = best["rule"]
    return {
        "rule": rule,
        "positives_it_misses": {
            "count": len(wrong_pos),
            "examples": [{"map": r["map"], "sector": r["sector"], name: r[name]}
                         for r in wrong_pos[:limit]],
        },
        "comparisons_it_wrongly_matches": {
            "count": len(wrong_neg),
            "examples": [{"map": r["map"], "sector": r["sector"], name: r[name]}
                         for r in wrong_neg[:limit]],
        },
    }


#: Features a signature-defined contrast must not be scored on, because the
#: signature fixes them. `objects_resting` *is* the `seated` facet: scoring it
#: would report the class definition back as a discovery.
SIGNATURE_BOUND_FEATURES = {
    "objects_held": "objects",
    "wiring_objects_held": "objects",
    "objects_resting": "seated",
    "objects_against_wall": "wallbound",
    "portals": "portals",
    "inside_another_sector": "enclosed",
    "shares_a_plane": "coplanar",
    "in_a_repeating_run": "run",
    "stands_above_a_neighbour": "stacked",
    "stands_under_a_neighbour": "stacked",
    # `raised_above_all_neighbours` is deliberately NOT bound: the `stacked`
    # facet comes from the `above` relation, which compares a floor with a
    # *ceiling*. Standing proud of a neighbour's floor is a different
    # measurement and the signature does not fix it.
    "area_player_areas": "size",
    "clear_height_player_heights": "clear",
}


def _object_context_rows(
    build: BuildIR, map_name: str, population: str, wanted: set[str], hops: int,
    kinds: dict[int, str] | None = None, reachable_only: bool = True,
) -> tuple[list[dict[str, Any]], int]:
    """Every sprite-carrying sector whose object-context signature is wanted.

    Signatures are computed over *visible* objects, so a class defined by an
    `objects:1` facet now means one object a player can see. Off-map sectors
    are skipped by default rather than silently mixed in.
    """
    from .patterns import PLAYER_HEIGHT, PLAYER_WIDTH, _object_context_signature
    from .relations import (
        _polygon_loops, _signed_area, context_signature, sprite_kind,
    )

    carrying: Counter = Counter()
    for sprite in build.sprites:
        carrying[int(sprite["fields"]["sector"])] += 1
    rows: list[dict[str, Any]] = []
    failed = 0
    for sector_id in sorted(carrying):
        if not 0 <= sector_id < len(build.sectors):
            continue
        if reachable_only and (kinds or {}).get(sector_id, "unknown") not in (
                "reachable", "unknown"):
            continue
        try:
            document = extract_relations(build, sectors=[sector_id], hops=hops,
                                         sector_kinds=kinds)
        except Exception:
            failed += 1
            continue
        fields = build.sectors[sector_id]["fields"]
        loops = _polygon_loops(build, sector_id)
        area = abs(sum(_signed_area(loop) for loop in loops)) / (PLAYER_WIDTH ** 2)
        height = (int(fields["floor_z"]) - int(fields["ceiling_z"])) / PLAYER_HEIGHT
        signature = _object_context_signature({
            "context_signature": context_signature(document, sector_id),
            "scale": {"area_player_areas": round(area, 4),
                      "clear_height_player_heights": round(height, 4)},
        })
        if signature not in wanted:
            continue
        rows.append({
            "map": map_name, "population": population, "sector": sector_id,
            "label": signature, **carrier_features(build, sector_id, document),
            "sector_kind": (kinds or {}).get(sector_id, "unknown"),
            "object_picnums": sorted(
                int(s["fields"]["picnum"]) for sprite_id, s in enumerate(build.sprites)
                if int(s["fields"]["sector"]) == sector_id
                and sprite_kind(build, sprite_id) == "visible"),
            "wiring_picnums": sorted(
                int(s["fields"]["picnum"]) for sprite_id, s in enumerate(build.sprites)
                if int(s["fields"]["sector"]) == sector_id
                and sprite_kind(build, sprite_id) == "wiring"),
        })
    return rows, failed


def _picnum_profile_wiring(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The non-visible sprites in the same sectors. Not objects -- but what
    these sectors are actually for, which is the whole point of labelling."""
    counts: Counter = Counter()
    for row in rows:
        counts.update(row.get("wiring_picnums", ()))
    return {
        "distinct_picnums": len(counts),
        "commonest": [{"picnum": picnum, "count": count}
                      for picnum, count in counts.most_common(8)],
    }


def contrast_signature_classes(
    positive: str,
    comparison: str,
    *,
    positive_name: str = "positive",
    comparison_name: str = "comparison",
    directory: str | Path | None = None,
    population: str | None = "blood-campaign",
    view: str | None = None,
    hops: int = 1,
    examples: int = 8,
) -> dict[str, Any]:
    """Contrast two object-context signature classes found by Phase 3.

    The anchor contrast starts from owner-tagged tiles and asks which relations
    separate them. This starts from two classes that were already found
    *relationally*, differing in exactly one facet, and asks the opposite
    question: does anything else differ? If nothing does, the pair is one
    concept with a variant; if something does, they are two.

    Features the signature itself fixes are excluded and listed, so the class
    definition cannot be reported back as a discovery.
    """
    from .format import read_map
    from .reachability import sector_kinds as reachability_sector_kinds

    selected = list_corpus_maps(directory, population=population, view=view)
    if not selected:
        raise AnchorError(f"no maps for population={population!r} view={view!r}")
    wanted = {positive, comparison}
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for item in selected:
        try:
            build = read_map(item.path).to_build_ir()
        except Exception as exc:
            skipped.append({"map": item.name, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        kinds = reachability_sector_kinds(read_map(item.path))
        found, failed = _object_context_rows(build, item.name, item.population,
                                             wanted, hops, kinds)
        rows.extend(found)
        if failed:
            skipped.append({"map": item.name, "sectors_unanalysable": failed,
                            "reason": "the map failed whole-map wall-ownership validation"})

    positives = [row for row in rows if row["label"] == positive]
    comparisons = [row for row in rows if row["label"] == comparison]
    if not positives or not comparisons:
        raise AnchorError(
            f"contrast needs both classes: {len(positives)} / {len(comparisons)}")

    free = [name for name in CONTRAST_FEATURES if name not in SIGNATURE_BOUND_FEATURES]
    measured = [
        _separation(name, [row[name] for row in positives],
                    [row[name] for row in comparisons])
        for name in free
    ]
    measured.sort(key=lambda item: -item.get("balanced_accuracy", 0))
    discriminating = [m for m in measured
                      if m.get("balanced_accuracy", 0) >= DISCRIMINATOR_FLOOR]
    rejected = [m for m in measured
                if m.get("balanced_accuracy", 0) < DISCRIMINATOR_FLOOR]
    best = discriminating[0] if discriminating else None
    return {
        "$schema": "llmapper.signature-contrast",
        "schema_version": SCHEMA_VERSION,
        "positive": {"name": positive_name, "signature": positive},
        "comparison": {"name": comparison_name, "signature": comparison},
        "differing_facets": sorted(
            key for key, value in signature_facets(positive).items()
            if signature_facets(comparison).get(key) != value),
        "selection": {"population": population, "view": view, "hops": hops,
                      "maps_searched": len(selected)},
        "counts": {
            positive_name: {"sectors": len(positives),
                            "maps": len({r["map"] for r in positives})},
            comparison_name: {"sectors": len(comparisons),
                              "maps": len({r["map"] for r in comparisons})},
        },
        "features_excluded_as_bound_by_the_signature": dict(SIGNATURE_BOUND_FEATURES),
        "features_measured": free,
        "discriminator_floor": DISCRIMINATOR_FLOOR,
        "discriminating": discriminating,
        "rejected": rejected,
        "counterexamples": _counterexamples(best, positives, comparisons, examples),
        "map_transfer": _map_transfer(best, positives),
        "object_description": {
            positive_name: _picnum_profile(positives),
            comparison_name: _picnum_profile(comparisons),
        },
        "wiring_description": {
            "note": "non-visible sprites in the same sectors; reported, never "
                    "counted as objects",
            positive_name: _picnum_profile_wiring(positives),
            comparison_name: _picnum_profile_wiring(comparisons),
        },
        "skipped": skipped,
        "rows": rows,
        "limitations": [
            "The two classes differ by construction in the facets listed under "
            "`differing_facets`; those and every other signature-bound feature "
            "are excluded from scoring.",
            "`object_description` is a description of what sits in each class, "
            "not a discriminator. Separating the classes by picnum would be "
            "separating them by texture, which is a finding, not a success.",
            "Thresholds are fitted on the same rows they are scored on.",
        ],
    }


def _picnum_profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """What actually sits in these sectors. Description, never a separator."""
    counts: Counter = Counter()
    for row in rows:
        counts.update(row.get("object_picnums", ()))
    return {
        "distinct_picnums": len(counts),
        "commonest": [{"picnum": picnum, "count": count}
                      for picnum, count in counts.most_common(8)],
    }


# ---------------------------------------------------------------------------
# Static bundles: several sectors and sprites that are one authored thing
# ---------------------------------------------------------------------------
#
# `assembly.py` groups the parts of a *mechanism* -- things bound by channels
# and state. A counter has neither and is still one object. `04_...md` lists
# the grouping signals: proximity, alignment, consistent orientation, repeated
# spacing, shared wall, common height, contact/support, enclosure. It also says
# proximity alone is insufficient, which is why the rule below leads with
# support and enclosure and never counts sprites in a radius.

#: The player's step limit, from `vocabulary.staircase`. A floor raised by more
#: than this cannot be walked onto, which is what makes a counter a counter
#: rather than a kerb.
STEP_LIMIT = 4096

#: Waist height: raised by more than one step but no more than half a body.
#: Measured, not chosen -- of 958 campaign blocking islands the rise
#: distribution has its largest mass here (38.3%), and E6M1's owner-identified
#: cashwrap sits at 6144, in the middle of it.
WAIST_RISE = (STEP_LIMIT, 8192)

#: An elongated footprint. A square blocking island is a pillar or a crate; a
#: counter is a run you stand along.
COUNTER_MIN_ASPECT = 2.0

BUNDLE_KINDS = {
    "raised-island": "a floor raised out of its host by more than one step, "
                     "with exactly one host, carrying caps or visible props",
}


@dataclass(frozen=True)
class Bundle:
    """Several primitives that are one authored object.

    `core` is the raised sector; `host` is the floor it stands in; `caps` are
    sectors inset into the core's own footprint (E6M1's two register caps);
    `props` are the visible sprites the core carries. Wiring never counts as a
    prop -- `reports/blood-wiring-placement.md` is the reason.
    """

    kind: str
    core: int
    host: int
    caps: tuple[int, ...]
    props: tuple[int, ...]
    measures: dict[str, Any]
    basis: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "core": f"sector:{self.core}",
            "host": f"sector:{self.host}",
            "caps": [f"sector:{value}" for value in self.caps],
            "props": [f"sprite:{value}" for value in self.props],
            "measures": dict(self.measures),
            "basis": list(self.basis),
        }


def _sector_bounds(build: BuildIR, sector_id: int) -> tuple[int, int, int, int] | None:
    fields = build.sectors[sector_id]["fields"]
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    points = [(int(build.walls[w]["fields"]["x"]), int(build.walls[w]["fields"]["y"]))
              for w in range(first, first + count) if 0 <= w < len(build.walls)]
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _sector_neighbours(build: BuildIR, sector_id: int) -> set[int]:
    fields = build.sectors[sector_id]["fields"]
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    out = set()
    for wall_id in range(first, first + count):
        if 0 <= wall_id < len(build.walls):
            other = int(build.walls[wall_id]["fields"]["next_sector"])
            if other >= 0:
                out.add(other)
    return out


def _box_contains(outer: tuple[int, ...], inner: tuple[int, ...]) -> bool:
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and outer[2] >= inner[2] and outer[3] >= inner[3])


def find_bundles(
    build: BuildIR,
    *,
    sector_kinds: dict[int, str] | None = None,
    game: str = "blood",
    waist_only: bool = True,
    require_elongated: bool = True,
    require_carried: bool = True,
) -> list[Bundle]:
    """Every raised-island bundle in a map.

    The rule, in the order the signals are applied -- none of them is proximity:

    1. **enclosure**: the sector has exactly one neighbour that does not sit
       inside its own footprint. That neighbour is the host; the rest are caps.
    2. **common height**: its floor is above the host's.
    3. **contact**: by more than a step, so the host floor and the core are two
       surfaces rather than one.
    4. **support / enclosure again**: it carries a cap or a visible prop.
       A bare raised island is a kerb or a plinth, not a bundle.

    The defaults narrow to the counter-like family measured in
    `reports/blood-assembly-counters.md`; relax them to see the whole
    raised-island population.
    """
    from .relations import sprite_kind

    visible: dict[int, list[int]] = defaultdict(list)
    for sprite_id, sprite in enumerate(build.sprites):
        if sprite_kind(build, sprite_id, game=game) == "visible":
            visible[int(sprite["fields"]["sector"])].append(sprite_id)

    out: list[Bundle] = []
    for core in range(len(build.sectors)):
        if sector_kinds is not None and sector_kinds.get(core, "unknown") not in (
                "reachable", "unknown"):
            continue
        box = _sector_bounds(build, core)
        if box is None:
            continue
        caps, outer = [], []
        for other in _sector_neighbours(build, core):
            other_box = _sector_bounds(build, other)
            (caps if other_box and _box_contains(box, other_box) else outer).append(other)
        if len(outer) != 1:
            continue
        host = outer[0]
        rise = (int(build.sectors[host]["fields"]["floor_z"])
                - int(build.sectors[core]["fields"]["floor_z"]))
        if rise <= STEP_LIMIT:
            continue
        if waist_only and not WAIST_RISE[0] < rise <= WAIST_RISE[1]:
            continue
        width, depth = box[2] - box[0], box[3] - box[1]
        long_side, short_side = max(width, depth), min(width, depth)
        aspect = long_side / short_side if short_side else 0.0
        if require_elongated and aspect < COUNTER_MIN_ASPECT:
            continue
        props = tuple(sorted(visible.get(core, ())))
        if require_carried and not props and not caps:
            continue
        profile = player_profile(game)
        out.append(Bundle(
            kind="raised-island", core=core, host=host,
            caps=tuple(sorted(caps)), props=props,
            measures={
                "rise_units": rise,
                "rise_player_heights": round(rise / profile.standing_height, 4),
                "aspect": round(aspect, 3),
                "long_player_widths": round(long_side / profile.body_width, 3),
                "short_player_widths": round(short_side / profile.body_width, 3),
                "caps": len(caps),
                "visible_props": len(props),
            },
            basis=(
                "one outer neighbour; every other neighbour sits inside its footprint",
                f"floor raised {rise} units over the host, more than the "
                f"{STEP_LIMIT}-unit step limit",
                "carries a cap or a visible prop",
            ),
        ))
    return out


# ---------------------------------------------------------------------------
# The random-prop-scattering detector
# ---------------------------------------------------------------------------
#
# `04_...md`: a common AI failure is to reach the right density by scattering
# props, and a map can match sprite counts and still fail composition. So the
# detector may not count sprites. It looks for the absence of authored
# structure: no support relationship, no grouping, no relation to walls.
#
# The load-bearing signal is **support**. An authored prop sits on something --
# a counter, a shelf, a plinth -- and a scattered one sits on the floor of the
# room it landed in. That is a Phase 1 relation (`rests_on`, plus the raised
# core the bundle already found), not a distance threshold.

#: A room whose props are this concentrated on supports reads as authored.
#: Not tuned on the corpus: it is the midpoint, and the synthetic pair in
#: `tests/test_assembly_bundles.py` sits at 1.0 and 0.0.
AUTHORED_SUPPORT_SHARE = 0.5


def scatter_verdict(
    build: BuildIR,
    host: int,
    *,
    sector_kinds: dict[int, str] | None = None,
    game: str = "blood",
) -> dict[str, Any]:
    """Are this room's props placed on something, or dropped on the floor?

    Returns the measured signals and one of `authored` / `scattered` /
    `ambiguous`. It never reads how *many* props there are: the same props,
    the same count, moved off their support, must flip the verdict, and
    `tests/test_assembly_bundles.py` pins exactly that.
    """
    from .relations import sprite_kind

    bundles = find_bundles(build, sector_kinds=sector_kinds, game=game,
                           require_carried=False)
    cores = {bundle.core: bundle for bundle in bundles if bundle.host == host}

    props, supported, on_core_sectors = [], [], set()
    for sprite_id, sprite in enumerate(build.sprites):
        if sprite_kind(build, sprite_id, game=game) != "visible":
            continue
        sector_id = int(sprite["fields"]["sector"])
        if sector_id == host:
            props.append(sprite_id)
        elif sector_id in cores:
            props.append(sprite_id)
            supported.append(sprite_id)
            on_core_sectors.add(sector_id)

    total = len(props)
    if not total:
        return {
            "host": f"sector:{host}", "verdict": "no props",
            "props": 0, "supports_available": len(cores),
        }
    share = len(supported) / total
    #: The verdict names what was measured, not a judgement about the author.
    #: E6M1's own selling floor scores 0.16 -- three props on the cashwrap and
    #: sixteen on the shop floor, every one of them deliberate. A detector that
    #: called that "scattered" would be wrong about the source material.
    verdict = ("props_on_supports" if share >= AUTHORED_SUPPORT_SHARE
               else "props_off_supports" if not supported and cores
               else "mixed")
    return {
        "host": f"sector:{host}",
        "verdict": verdict,
        "props": total,
        "props_on_a_support": len(supported),
        "support_share": round(share, 4),
        "supports_available": len(cores),
        "supports_used": len(on_core_sectors),
        "signals": {
            "support": "props resting on a raised island rather than on the "
                       "host floor",
            "grouping": "how many of the available supports are actually used",
        },
        "basis": "Phase 1 relations plus the raised-island rule; no sprite "
                 "count enters the verdict",
        "limitations": [
            "A room with no raised support cannot be told apart this way and "
            "says so rather than guessing.",
            "This is a measurement of one room, not a verdict on its author. "
            "A shop floor legitimately carries props on the floor: E6M1's "
            "scores 0.16 and is hand-authored. Use `compare_placements` for "
            "the question the phase actually asks.",
            "Synthetic scenes are validation only and are never evidence.",
        ],
    }


def compare_placements(
    authored: BuildIR, candidate: BuildIR, host: int, *,
    sector_kinds: dict[int, str] | None = None, game: str = "blood",
) -> dict[str, Any]:
    """The Phase 5 question: the same props, placed two ways -- which is which?

    Not "is this room good". Given one arrangement and another of the *same*
    props in the *same* room, say which one is authored. The answer is carried
    by whether the props are on their support, so a scatter that preserves
    count, room and prop identity still loses.
    """
    left = scatter_verdict(authored, host, sector_kinds=sector_kinds, game=game)
    right = scatter_verdict(candidate, host, sector_kinds=sector_kinds, game=game)
    same_props = left.get("props") == right.get("props")
    gap = left.get("support_share", 0) - right.get("support_share", 0)
    return {
        "host": f"sector:{host}",
        "same_prop_count": same_props,
        "authored": left,
        "candidate": right,
        "support_share_gap": round(gap, 4),
        "verdict": ("the first is authored" if gap > 0
                    else "the second is authored" if gap < 0
                    else "indistinguishable by support"),
        "basis": "prop count is identical by construction, so it cannot be "
                 "carrying the answer",
    }


# ---------------------------------------------------------------------------
# Functional region candidates: zones, and the bundles inside them
# ---------------------------------------------------------------------------

#: Two naming hypotheses were tested against the campaign and both failed.
#: They are recorded here because a later pass will think of them again.
REJECTED_ZONE_NAMINGS = (
    {
        "hypothesis": "a counter's wide side is the customer front, because "
                      "that is where the ways out are",
        "measured": "84.1% of a host's ways out are on the wide side, but the "
                    "wide side also carries 83.2% of the host's wall: a lift "
                    "of +0.024, and only 43% of bundles beat their own wall "
                    "share (a coin flip is 50%)",
        "verdict": "rejected: the wide side has the exits because it has the "
                   "wall, not because it is the public side",
    },
    {
        "hypothesis": "merchandise stands on the customer side, so the wide "
                      "side is denser in props",
        "measured": "props on the wide side 0.651 against a floor share of "
                    "0.730 -- a lift of -0.080, and the wide side is the "
                    "denser one in only 40% of bundles",
        "verdict": "rejected, and in the opposite direction to the guess",
    },
)


def region_candidates(
    build: BuildIR,
    sector_ids: Iterable[int],
    *,
    sector_kinds: dict[int, str] | None = None,
    game: str = "blood",
) -> dict[str, Any]:
    """Zones in a group of sectors, with the bundles each one contains.

    Hierarchical containment: complex -> zone -> {sectors, bundles -> {core,
    caps, props}}. Zones are unnamed on purpose. `04_...md` offers a shop
    grammar (`public_floor`, `counter_boundary`, `employee_workspace`) and the
    campaign does not support the naming -- see `REJECTED_ZONE_NAMINGS` and
    `reports/blood-assembly-regions.md`. Structure before naming.
    """
    from .patterns import PLAYER_WIDTH, _area
    from .relations import sprite_kind
    from .spatial import zone_partition

    selected = sorted({int(value) for value in sector_ids})
    zones = zone_partition(build, selected)
    bundles = {b.core: b for b in find_bundles(build, sector_kinds=sector_kinds,
                                               game=game)}

    visible: dict[int, int] = defaultdict(int)
    for sprite_id, sprite in enumerate(build.sprites):
        if sprite_kind(build, sprite_id, game=game) == "visible":
            visible[int(sprite["fields"]["sector"])] += 1

    out = []
    for zone in zones:
        members = zone["sectors"]
        held = [bundles[core].to_dict() for core in members if core in bundles]
        hosted = [bundles[core].to_dict() for core in bundles
                  if bundles[core].host in members]
        out.append({
            **zone,
            "sector_count": len(members),
            "area_player_areas": round(
                sum(_area(build, s) for s in members) / (PLAYER_WIDTH ** 2), 2),
            "visible_props": sum(visible.get(s, 0) for s in members),
            "is_a_bundle_core": held,
            "hosts_bundles": hosted,
            "sector_kinds": sorted({(sector_kinds or {}).get(s, "unknown")
                                    for s in members}),
        })
    return {
        "$schema": "llmapper.functional-regions",
        "schema_version": 1,
        "sectors": selected,
        "zone_count": len(out),
        "zones": out,
        "rejected_namings": [dict(item) for item in REJECTED_ZONE_NAMINGS],
        "limitations": [
            "Zones are unnamed. The partition is by floor plane and floor "
            "tile, which separates a counter from the floor it stands in and "
            "a sunken office from a shop, and does not separate one shop "
            "floor's apparel bay from its display window -- those share a "
            "plane and a tile in E6M1 and differ only in what they hold.",
            "A zone is a candidate, not a room's meaning.",
        ],
    }


# ---------------------------------------------------------------------------
# Facades: the composition that owns its openings
# ---------------------------------------------------------------------------
#
# `06_...md`: the facade owns the openings, the opening does not own the
# facade. So a facade is not found by looking for windows; it is found as a
# coherent run of street-facing wall, and the openings are what interrupt it.
#
# Two measured constants come from `projects/blood-city/level/facade_pass.py`
# and are re-confirmed corpus-wide in `reports/blood-facade-grammar.md`:
# street walls are drawn at 16 world units per tile pixel (73% of 5275
# campaign street-facing walls), so a 64-pixel facade tile spans 1024 units
# and that is the bay.

#: `length / (x_repeat * 8)` for a wall drawn at the facade scale.
FACADE_UNITS_PER_TILE_PIXEL = 16
FACADE_SCALE_TOLERANCE = 0.5
#: One painted window and its pier.
FACADE_BAY = 1024
#: Build's ceiling-alignment bit, which a header wall takes so it continues the
#: wall it hangs from rather than its own opening.
ALIGN_TO_CEILING = 4
#: A run has to be long enough to have a rhythm at all.
FACADE_MIN_BAYS = 2
#: How straight "the same plane" is: the perpendicular offset a wall end may
#: have from the run's line, in world units.
FACADE_COLLINEAR_UNITS = 64

FACADE_RHYTHMS = {
    "single": "one opening; nothing to repeat",
    "repeating": "even spacing, coefficient of variation <= 0.12",
    "alternating": "two spacings alternating",
    "intentionally_broken": "even but for one outlier -- an authored break, "
                            "kept rather than regularized",
    "irregular": "no repeating structure measured",
}


@dataclass(frozen=True)
class Facade:
    """A run of street-facing wall, and everything that hangs off it."""

    host: int
    walls: tuple[int, ...]
    solid: tuple[int, ...]
    openings: tuple[dict[str, Any], ...]
    seams: tuple[int, ...]
    helpers: tuple[int, ...]
    datums: dict[str, Any]
    bays: dict[str, Any]
    rhythm: str
    signage: tuple[dict[str, Any], ...]
    measures: dict[str, Any]
    basis: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": f"sector:{self.host}",
            "walls": [f"wall:{w}" for w in self.walls],
            "solid_walls": len(self.solid),
            "openings": [dict(item) for item in self.openings],
            "seams": [f"wall:{w}" for w in self.seams],
            "helper_sectors": [f"sector:{s}" for s in self.helpers],
            "datums": dict(self.datums),
            "bays": dict(self.bays),
            "rhythm": self.rhythm,
            "signage": [dict(item) for item in self.signage],
            "measures": dict(self.measures),
            "basis": list(self.basis),
        }


def _wall_ends(build: BuildIR, wall_id: int) -> tuple[tuple[int, int], tuple[int, int]]:
    wall = build.walls[wall_id]["fields"]
    end = build.walls[int(wall["point2"])]["fields"]
    return (int(wall["x"]), int(wall["y"])), (int(end["x"]), int(end["y"]))


def _facade_scale(build: BuildIR, wall_id: int) -> bool:
    """Is this wall drawn at the facade scale, 16 world units per tile pixel?"""
    (ax, ay), (bx, by) = _wall_ends(build, wall_id)
    length = hypot(bx - ax, by - ay)
    repeat = int(build.walls[wall_id]["fields"]["x_repeat"])
    if not length or not repeat:
        return False
    return abs(length / (repeat * 8) - FACADE_UNITS_PER_TILE_PIXEL) <= FACADE_SCALE_TOLERANCE


def _collinear_runs(build: BuildIR, wall_ids: Sequence[int]) -> list[list[int]]:
    """Split a wall loop into maximal runs that lie on one line.

    The main plane of a facade, in the `06_...md` sense: a facade turns a
    corner into a different facade of the same building, and a run that
    wandered round a corner would have no plane to measure datums against.
    """
    runs: list[list[int]] = []
    current: list[int] = []
    for wall_id in wall_ids:
        if not current:
            current = [wall_id]
            continue
        (ax, ay), _ = _wall_ends(build, current[0])
        (_, _), (bx, by) = _wall_ends(build, current[-1])
        _, (dx, dy) = _wall_ends(build, wall_id)
        length = hypot(bx - ax, by - ay)
        # Perpendicular distance of the candidate wall's far end from the run's
        # line. It has to be the far end: in a closed loop the near end is the
        # previous wall's end, which lies on the line by construction, so
        # measuring it would never detect a corner.
        offset = (abs((bx - ax) * (dy - ay) - (by - ay) * (dx - ax)) / length
                  if length else 0.0)
        if length and offset <= FACADE_COLLINEAR_UNITS:
            current.append(wall_id)
        else:
            runs.append(current)
            current = [wall_id]
    if current:
        runs.append(current)
    return runs


def _rhythm(offsets: Sequence[float], run_length: float) -> str:
    if len(offsets) <= 1:
        return "single"
    gaps = [b - a for a, b in zip(offsets, offsets[1:])]
    if len(gaps) == 1:
        centred = abs(offsets[0] + (offsets[-1] - offsets[0]) / 2 - run_length / 2)
        return "centered" if centred <= FACADE_BAY / 2 else "irregular"
    spacing = mean(gaps)
    if spacing <= 0:
        return "irregular"
    variation = pstdev(gaps) / spacing
    if variation <= 0.12:
        return "repeating"
    if len(gaps) >= 3:
        odd = gaps[0::2]
        even = gaps[1::2]
        if (len(odd) > 1 and len(even) > 0
                and pstdev(odd) / max(mean(odd), 1) <= 0.12
                and (len(even) < 2 or pstdev(even) / max(mean(even), 1) <= 0.12)
                and abs(mean(odd) - mean(even)) > 0.25 * spacing):
            return "alternating"
        trimmed = sorted(gaps)[:-1]
        if len(trimmed) > 1 and pstdev(trimmed) / max(mean(trimmed), 1) <= 0.12:
            return "intentionally_broken"
    return "irregular"


def find_facades(
    build: BuildIR,
    *,
    disk: Any = None,
    sector_kinds: dict[int, str] | None = None,
    game: str = "blood",
    require_openings: bool = True,
) -> list[Facade]:
    """Facade candidates: coherent runs of street-facing wall.

    A run qualifies when it is a maximal collinear sequence in a sky-lit
    reachable sector, spans at least two bays, and carries at least one
    opening. What makes its openings *belong together* is measured rather
    than assumed: the shared plane, the shared material family, the shared
    sill and header datums, and the bay grid they land on.
    """
    from .lettering import FIRST_LETTER, LAST_LETTER

    out: list[Facade] = []
    for sector_id, sector in enumerate(build.sectors):
        if sector_kinds is not None and sector_kinds.get(sector_id, "unknown") not in (
                "reachable", "unknown"):
            continue
        fields = sector["fields"]
        if not int(fields["ceiling_stat"]) & 1:          # not open to the sky
            continue
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        wall_ids = [w for w in range(first, first + count) if 0 <= w < len(build.walls)]
        floor_z = int(fields["floor_z"])
        candidates = []
        for run in _collinear_runs(build, wall_ids):
            found = _facade_from_run(build, sector_id, run, floor_z, disk,
                                     FIRST_LETTER, LAST_LETTER, require_openings)
            if found is not None:
                candidates.append(found)
        out.extend(_assign_signage(candidates))
    return out


def _assign_signage(candidates: list[Facade]) -> list[Facade]:
    """A letter belongs to one facade: the plane it is nearest to.

    Two collinear runs of the same street sector can both be within a bay of
    the same sign, and counting a word twice would report a shopfront as two
    shopfronts. The nearest plane wins.
    """
    if len(candidates) < 2:
        return candidates
    best: dict[str, tuple[float, int]] = {}
    for index, facade in enumerate(candidates):
        for sign in facade.signage:
            offset = sign["offset_from_plane_units"]
            if sign["sprite"] not in best or offset < best[sign["sprite"]][0]:
                best[sign["sprite"]] = (offset, index)
    return [
        replace(facade, signage=tuple(
            sign for sign in facade.signage
            if best.get(sign["sprite"], (0, index))[1] == index))
        for index, facade in enumerate(candidates)
    ]


def _facade_helper(build: BuildIR, sector_id: int, helpers: list[int]) -> None:
    """A neighbour shallower than half a bay is dressing, not a room.

    Kerb strips and opening frames reach a facade through seams as often as
    through openings, so this is asked of every two-sided neighbour.
    """
    fields = build.sectors[sector_id]["fields"]
    if not abs(int(fields["floor_z"]) - int(fields["ceiling_z"])):
        return
    box = _sector_bounds(build, sector_id)
    if box and min(box[2] - box[0], box[3] - box[1]) <= FACADE_BAY // 2:
        helpers.append(sector_id)


def _facade_from_run(
    build: BuildIR, host: int, run: Sequence[int], floor_z: int, disk: Any,
    first_letter: int, last_letter: int, require_openings: bool,
) -> Facade | None:
    (ox, oy), _ = _wall_ends(build, run[0])
    _, (ex, ey) = _wall_ends(build, run[-1])
    run_length = hypot(ex - ox, ey - oy)
    if run_length < FACADE_MIN_BAYS * FACADE_BAY:
        return None

    def along(x: float, y: float) -> float:
        return hypot(x - ox, y - oy)

    solid, openings, seams, helpers = [], [], [], []
    sills: Counter = Counter()
    headers: Counter = Counter()
    scale_hits = 0
    picnums: Counter = Counter()
    ceiling_z = int(build.sectors[host]["fields"]["ceiling_z"])
    for wall_id in run:
        wall = build.walls[wall_id]["fields"]
        (ax, ay), (bx, by) = _wall_ends(build, wall_id)
        other = int(wall["next_sector"])
        if _facade_scale(build, wall_id):
            scale_hits += 1
        if other < 0:
            solid.append(wall_id)
            picnums[int(wall["picnum"])] += 1
            continue
        neighbour = build.sectors[other]["fields"]
        sill = int(neighbour["floor_z"]) - floor_z
        # Blood z grows downward, so a larger ceiling_z is a lower ceiling. An
        # opening in a facade has a lintel; a two-sided wall that keeps the
        # host's own ceiling is ground, not wall -- a kerb, a step, the seam
        # between two sectors of one street. 3187 of the 4331 two-sided walls
        # on campaign facade runs are that, and counting them as openings is
        # what the first version of this did.
        if int(neighbour["ceiling_z"]) <= ceiling_z:
            seams.append(wall_id)
            _facade_helper(build, other, helpers)
            continue
        sills[sill] += 1
        headers[int(neighbour["ceiling_z"])] += 1
        width = hypot(bx - ax, by - ay)
        openings.append({
            "wall": f"wall:{wall_id}",
            "leads_to": f"sector:{other}",
            "along_run": round(along((ax + bx) / 2, (ay + by) / 2), 1),
            "width_units": round(width, 1),
            "width_bays": round(width / FACADE_BAY, 3),
            "whole_bay": abs(width / FACADE_BAY - round(width / FACADE_BAY)) < 0.02
                         and width >= FACADE_BAY * 0.5,
            "sill_above_street": sill,
            "header_ceiling_z": int(neighbour["ceiling_z"]),
            "header_aligned_to_ceiling": bool(int(wall["cstat"]) & ALIGN_TO_CEILING),
        })
        _facade_helper(build, other, helpers)
    if require_openings and not openings:
        return None

    offsets = sorted(item["along_run"] for item in openings)
    signage = _facade_signage(build, disk, host, run, (ox, oy), run_length,
                             first_letter, last_letter, floor_z)
    dominant = picnums.most_common(1)[0] if picnums else (None, 0)
    return Facade(
        host=host, walls=tuple(run), solid=tuple(solid),
        openings=tuple(openings), seams=tuple(seams),
        helpers=tuple(sorted(set(helpers))),
        datums={
            "sill_above_street": {str(k): v for k, v in sorted(sills.items())},
            "repeated_sill": max(sills.values()) if sills else 0,
            "header_ceiling_z": {str(k): v for k, v in sorted(headers.items())},
            "repeated_header": max(headers.values()) if headers else 0,
            "cornice": None,
            "cornice_note": "not recoverable from geometry: a street sector's "
                            "ceiling is the sky, so the top of a facade is "
                            "painted rather than built",
        },
        bays={
            "run_bays": round(run_length / FACADE_BAY, 3),
            "whole_bay_openings": sum(1 for item in openings if item["whole_bay"]),
            "openings": len(openings),
        },
        rhythm=_rhythm(offsets, run_length),
        signage=tuple(signage),
        measures={
            "run_length_units": round(run_length, 1),
            "walls": len(run),
            "solid_walls": len(solid),
            "seams": len(seams),
            "at_facade_scale": scale_hits,
            "facade_scale_share": round(scale_hits / len(run), 3),
            "distinct_wall_tiles": len(picnums),
            "dominant_tile": dominant[0],
            "dominant_tile_share": round(dominant[1] / max(1, len(solid)), 3),
            "helper_sectors": len(set(helpers)),
        },
        basis=(
            "maximal collinear run of one sky-lit sector's wall loop",
            f"at least {FACADE_MIN_BAYS} bays of {FACADE_BAY} units",
            "openings are the two-sided walls interrupting the run",
        ),
    )


def _facade_signage(
    build: BuildIR, disk: Any, host: int, run: Sequence[int],
    origin: tuple[int, int], run_length: float, first_letter: int, last_letter: int,
    floor_z: int,
) -> list[dict[str, Any]]:
    """Letter sprites standing on this facade, placed against its own grid.

    Signage is a member of the hierarchy, not decoration: where a sign sits is
    measured in bays along the run and in player heights above the street, so
    two facades in different maps can be compared.
    """
    from .player_space import player_profile

    profile = player_profile("blood")
    letters = [
        (index, sprite) for index, sprite in enumerate(build.sprites)
        if first_letter <= int(sprite["fields"]["picnum"]) <= last_letter
        and int(sprite["fields"]["sector"]) == host
    ]
    if not letters:
        return []
    ox, oy = origin
    (ax, ay), _ = _wall_ends(build, run[0])
    _, (bx, by) = _wall_ends(build, run[-1])
    ux, uy = bx - ax, by - ay
    length = hypot(ux, uy) or 1.0
    ux, uy = ux / length, uy / length

    out = []
    for index, sprite in letters:
        fields = sprite["fields"]
        px, py = int(fields["x"]) - ox, int(fields["y"]) - oy
        along = px * ux + py * uy
        offset = abs(px * -uy + py * ux)
        if not (-FACADE_BAY <= along <= run_length + FACADE_BAY):
            continue
        if offset > FACADE_BAY:                          # not on this plane
            continue
        out.append({
            "sprite": f"sprite:{index}",
            "picnum": int(fields["picnum"]),
            "along_run_units": round(along, 1),
            "along_run_bays": round(along / FACADE_BAY, 3),
            "offset_from_plane_units": round(offset, 1),
            "height_above_street_player_heights": round(
                (floor_z - int(fields["z"])) / profile.standing_height, 3),
            "wall_aligned": bool(int(fields["cstat"]) & 16),
            "x_repeat": int(fields["x_repeat"]),
            "pal": int(fields["pal"]),
        })
    return out

# A facade candidate is a plane, not a building. `reports/blood-facade-grammar.md`
# named that as the one thing blocking a `facade_run()` constructor: 47 campaign
# runs are longer than 30 bays, and nothing in the run itself says where one
# frontage stops and the next begins.
#
# The oracle for that is not a label, it is the interior. Two openings on one
# frontage are in the same building when you can walk from one interior to the
# other without stepping back outside.

#: What a street and an alley have in common, and what a shop interior does not.
def _outdoor(build: BuildIR, sector_id: int) -> bool:
    return bool(int(build.sectors[sector_id]["fields"]["ceiling_stat"]) & 1)


def interior_components(build: BuildIR) -> dict[int, int]:
    """Label every sector by the interior it belongs to; outdoor space is -1.

    Portals through outdoor sectors are cut, so two shops that share a street
    are not thereby one building. A whole-map fact, computed once per map, as
    `docs/architecture.md` asks.
    """
    inside = [s for s in range(len(build.sectors)) if not _outdoor(build, s)]
    graph: dict[int, set[int]] = {s: set() for s in inside}
    for owner in inside:
        fields = build.sectors[owner]["fields"]
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        for wall_id in range(first, min(first + count, len(build.walls))):
            other = int(build.walls[wall_id]["fields"]["next_sector"])
            if other in graph:
                graph[owner].add(other)
                graph[other].add(owner)
    labels = {s: -1 for s in range(len(build.sectors))}
    seen: set[int] = set()
    index = 0
    for start in inside:
        if start in seen:
            continue
        stack, group = [start], []
        seen.add(start)
        while stack:
            node = stack.pop()
            group.append(node)
            for neighbour in graph[node]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        for node in group:
            labels[node] = index
        index += 1
    return labels


#: What is measured on the solid stretch between two openings on one frontage.
PARTY_WALL_FEATURES = (
    "gap_bays",
    "solid_walls_between",
    "header_changes",
    "sill_changes",
    "gap_tile_differs_from_run",
    "flank_tiles_differ",
    "gap_shade_differs_from_run",
    "masked_wall_in_gap",
    "interior_depth_changes",
)


def _modal(values: list[int]) -> int | None:
    return Counter(values).most_common(1)[0][0] if values else None


def party_wall_gaps(
    build: BuildIR, facade: Facade, components: Mapping[int, int],
) -> list[dict[str, Any]]:
    """Each consecutive pair of openings on one run, and what lies between.

    The oracle is `different_buildings`, taken from the interior rather than
    from the street: the two openings lead into interiors that are not
    connected to each other except by going back outside. A pair where either
    side opens onto more outdoor space carries no verdict and is excluded
    rather than guessed.
    """
    run = list(facade.walls)
    position = {wall_id: index for index, wall_id in enumerate(run)}
    ordered = sorted(
        ((int(item["wall"].split(":")[1]), item) for item in facade.openings),
        key=lambda pair: position[pair[0]])
    dominant = facade.measures["dominant_tile"]
    shades = [int(build.walls[w]["fields"]["shade"]) for w in facade.solid]
    run_shade = _modal(shades)

    out: list[dict[str, Any]] = []
    for (left_id, left), (right_id, right) in zip(ordered, ordered[1:]):
        low, high = position[left_id], position[right_id]
        between = [w for w in run[low + 1:high]
                   if int(build.walls[w]["fields"]["next_sector"]) < 0]
        gap = ((right["along_run"] - right["width_units"] / 2)
               - (left["along_run"] + left["width_units"] / 2))
        left_interior = int(left["leads_to"].split(":")[1])
        right_interior = int(right["leads_to"].split(":")[1])
        left_label, right_label = components.get(left_interior, -1), components.get(right_interior, -1)
        picnums = [int(build.walls[w]["fields"]["picnum"]) for w in between]
        gap_shades = [int(build.walls[w]["fields"]["shade"]) for w in between]
        before = run[low - 1] if low > 0 else None
        after = run[high + 1] if high + 1 < len(run) else None

        def depth(sector_id: int) -> float:
            box = _sector_bounds(build, sector_id)
            return min(box[2] - box[0], box[3] - box[1]) if box else 0.0

        out.append({
            "left": left["wall"], "right": right["wall"],
            "left_interior": left["leads_to"], "right_interior": right["leads_to"],
            "verdict": ("unknown" if left_label < 0 or right_label < 0 else
                        "different_buildings" if left_label != right_label else
                        "one_building"),
            "gap_units": round(gap, 1),
            "gap_bays": round(gap / FACADE_BAY, 3),
            "solid_walls_between": len(between),
            "header_changes": left["header_ceiling_z"] != right["header_ceiling_z"],
            "sill_changes": left["sill_above_street"] != right["sill_above_street"],
            "gap_tile_differs_from_run": (_modal(picnums) is not None
                                          and _modal(picnums) != dominant),
            "flank_tiles_differ": (
                before is not None and after is not None
                and int(build.walls[before]["fields"]["picnum"])
                != int(build.walls[after]["fields"]["picnum"])),
            "gap_shade_differs_from_run": (_modal(gap_shades) is not None
                                           and _modal(gap_shades) != run_shade),
            "masked_wall_in_gap": any(
                int(build.walls[w]["fields"]["over_picnum"]) > 0 for w in between),
            "interior_depth_changes": round(
                abs(depth(left_interior) - depth(right_interior)) / FACADE_BAY, 3),
        })
    return out
