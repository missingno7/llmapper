"""The edge chain: how the playable city meets its real termination.

Decisions section 15b: the ground's boundary is a CLOSED CHAIN whose segments
each have an edge kind, and adjacent segments join by the join grammar. This
reads that chain off an original map -- one segment per run of consecutive
boundary records of the same kind -- and names the records no kind claims.

The family (`joins.EDGE_KINDS` plus the two that are not edge kinds but do
bound a city) is classified from what is on the FAR side of each record,
never from a tile:

* **end_wall** -- the far side is an outdoor mass no body can step onto
  (`read_joins`'s own criterion).
* **horizon** -- the far side has parallax on floor and ceiling both.
* **waterfront** -- the far side reads as water (palette or panning).
* **chasm** -- the far side's floor is far BELOW this one, in the open.
* **building_back** -- the record is one-sided: a flat wall against the void,
  with nothing behind it and no sector spent. Section 15b's "a building may be
  a link in the chain".
* **backing** -- the far side is a zero-height sector: a mass with no interior
  standing behind an end wall. E3M1's outermost skin is made of these, and
  they are the thing section 14 calls "the backing nobody sees".
* **enclosure_backdrop** -- walls ringing the city with unreachable fake
  masses beyond. `reachability.classify_offmap` is the reader for the masses,
  and it works (section 14 records it as raising `TypeError` on every map;
  that is no longer true -- it returns a classification for E3M1).

A record whose far side is ordinary reachable ground is not a boundary at all
and is not counted: the chain is the boundary of the ground, so the population
is the ground's own outline.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Sequence

from .joins import CHASM_TILES
from .read_joins import (
    AUTOSTEP, INTERIOR, MECHANISM_AT_REST, SOLID, adjacency, reads_as_water,
    street_network, surface_kinds,
)
from .texture_frame import sector_index

END_WALL = "end_wall"
HORIZON = "horizon"
WATERFRONT = "waterfront"
CHASM = "chasm"
BUILDING_BACK = "building_back"
BACKING = "backing"
#: `joins.GATE`, which section 14 already names as a member of the family: a
#: way through, rather than a termination. A boundary record whose far side is
#: a MECHANISM AT REST is one -- the mass is a wall only until it is told to
#: move -- and E3M1's four such records were unclassified until 28c named the
#: movers apart from the end walls.
GATE = "gate"
ENCLOSURE_BACKDROP = "enclosure_backdrop"
INTERIOR_DOORWAY = "interior_doorway"
UNCLASSIFIED = "unclassified"


def _face(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


#: The kinds that ARE ground: what a body stands on. An end wall is inside
#: the outdoor network (it is outdoor and it has clear height) and is not
#: ground, so a boundary defined as "the network's outline" would swallow
#: every end wall and report a city with no terminations at all -- which is
#: what the first run of this reader did on a map whose T ends in three.
GROUND = frozenset({"road", "pavement", "outdoor_ground", "shore"})


def ground_of(network: set[int], kinds: dict[int, str]) -> set[int]:
    return {index for index in network if kinds.get(index) in GROUND}


def boundary_records(level: Any, network: set[int], owners: Sequence[int]
                     ) -> list[int]:
    """Every record of the ground whose other side is not the ground."""
    out = []
    for index in sorted(network):
        fields = _face(level.sectors[index])
        start = int(fields["wall_ptr"])
        for wall_id in range(start, start + int(fields["wall_count"])):
            other = int(_face(level.walls[wall_id])["next_sector"])
            if other < 0 or other not in network:
                out.append(wall_id)
    return out


def classify(level: Any, wall_id: int, here: int, kinds: dict[int, str]
             ) -> tuple[str, str]:
    """This boundary record's edge kind, and the measurement behind it."""
    face = _face(level.walls[wall_id])
    other = int(face["next_sector"])
    if other < 0:
        return (BUILDING_BACK,
                "one-sided: a flat wall against the void, no sector spent "
                "behind it")
    there = _face(level.sectors[other])
    if int(there["floor_stat"]) & 1 and int(there["ceiling_stat"]) & 1:
        return HORIZON, "the far side has parallax on floor and ceiling both"
    if reads_as_water(level.sectors[other]):
        return WATERFRONT, "the far side reads as water: a palette, or panning"
    kind = kinds.get(other)
    if kind == MECHANISM_AT_REST:
        return (GATE,
                f"the far side is sector {other}, a raised outdoor mass that "
                f"carries a sector type: a way through when it is told to "
                f"move, and a wall until then")
    if kind == END_WALL:
        return (END_WALL,
                f"the far side is sector {other}, an outdoor mass standing "
                f"more than the {AUTOSTEP} autostep above every neighbour")
    if kind == SOLID:
        return (BACKING,
                f"the far side is sector {other}, floor_z == ceiling_z: a mass "
                f"with no interior, the backing nobody sees")
    drop = int(there["floor_z"]) - int(_face(level.sectors[here])["floor_z"])
    if drop > AUTOSTEP and int(there["ceiling_stat"]) & 1:
        rock = int(there["floor_picnum"]) in CHASM_TILES
        return (CHASM,
                f"the far side is {drop} below, in the open"
                + (f", wearing rock {int(there['floor_picnum'])}" if rock else
                   f", wearing {int(there['floor_picnum'])} (not a rock tile)"))
    if kind == INTERIOR:
        return (INTERIOR_DOORWAY,
                f"the far side is sector {other}, an interior: this is a way "
                f"in, not a termination")
    return UNCLASSIFIED, f"the far side is sector {other}, kind {kind!r}"


def chain(level: Any, records: Sequence[int], labels: dict[int, str]
          ) -> list[dict[str, Any]]:
    """The boundary as SEGMENTS: runs of consecutive records of one kind.

    Consecutive in Build's own `point2` order, so a segment is what a body
    walking the edge would call one stretch of it, rather than a set of
    records that happen to share a label.
    """
    order = {record: int(_face(level.walls[record])["point2"])
             for record in records}
    members = set(records)
    starts = [record for record in records
              if not any(order.get(other) == record for other in members)]
    segments: list[dict[str, Any]] = []
    seen: set[int] = set()
    for start in sorted(starts) + sorted(members):
        if start in seen:
            continue
        run, current = [], start
        while current in members and current not in seen:
            if run and labels[current] != labels[run[0]]:
                break
            seen.add(current)
            run.append(current)
            current = order.get(current, -1)
        if run:
            segments.append({"kind": labels[run[0]], "records": run,
                             "length": len(run)})
    return segments


def read_edges(level: Any, kinds: dict[int, str] | None = None, *,
               owners: Sequence[int] | None = None) -> dict[str, Any]:
    owners = list(owners) if owners is not None else sector_index(level)
    graph = adjacency(level, owners)
    network, _ = street_network(level, graph)
    if kinds is None:
        kinds = surface_kinds(level, owners=owners)["kinds"]
    ground = ground_of(network, kinds)
    records = boundary_records(level, ground, owners)
    labels: dict[int, str] = {}
    why: dict[int, str] = {}
    for record in records:
        kind, reason = classify(level, record, owners[record], kinds)
        labels[record], why[record] = kind, reason
    segments = chain(level, records, labels)
    unclassified = sorted(record for record in records
                          if labels[record] == UNCLASSIFIED)
    return {
        "ground_sectors": sorted(ground),
        "boundary_records": records,
        "kinds": {str(record): labels[record] for record in records},
        "why": {str(record): why[record] for record in records},
        "counts": dict(Counter(labels.values())),
        "segments": segments,
        "segment_counts": dict(Counter(row["kind"] for row in segments)),
        "residue_records": unclassified,
        "offmap": _offmap(level),
    }


def _offmap(level: Any) -> dict[str, Any]:
    """Unreachable geometry beyond the skin: the backdrop reader.

    Section 14 records `reachability.classify_offmap` as raising `TypeError`
    on every map. It does not any more, and the correction matters because it
    is the only reader that could find an enclosure's backdrop masses.
    """
    from .reachability import classify_offmap

    try:
        found = classify_offmap(level.to_disk_map())
    except Exception as error:                 # keep the old symptom visible
        return {"reader": "reachability.classify_offmap", "raised": repr(error)}
    return {
        "reader": "reachability.classify_offmap",
        "reached": found["reachability"]["reached"],
        "offmap_sectors": found["reachability"]["offmap"],
        "by_kind": found["sectors_by_kind"],
        "components": found["components"],
    }


def summary(result: dict[str, Any]) -> dict[str, Any]:
    total = len(result["boundary_records"])
    residue = len(result["residue_records"])
    return {
        "boundary_records": total,
        "by_kind": result["counts"],
        "segments": len(result["segments"]),
        "segments_by_kind": result["segment_counts"],
        "residue_records": residue,
        "residue_percent": round(100.0 * residue / total, 2) if total else 0.0,
    }
