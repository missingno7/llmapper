"""The three properties a level program is supposed to have, at city scale.

`bloodmap` tests each of these on small fixtures.  A 215-sector city with a
six-deep tree is where they are actually load-bearing, and where a tree
that merely *looks* nested can still fail them -- a venue whose rooms are
its siblings passes nothing here.

    python projects/blood-city/level/tree_tests.py

* **Locality.**  Changing one venue changes only that venue's sectors in
  the compiled MAP.  This is the property that makes the tree worth having:
  an agent asked to restyle the saloon can be told what it will touch.
* **Exact frames.**  A parent's frame moves its children without altering a
  number in any child's local outline.  Nesting is only safe if the child's
  source is unchanged by where it is put.
* **Traceable inheritance.**  Every resolved style value names the node that
  stated it, and that node is an ancestor or the room itself.
"""

from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import citytree
from bloodmap.levelprog import Frame


#: The in-progress level carries raw Build records as dicts, so a sector is
#: read through its `fields`, not as an attribute.
_KEYS = ("floor_z", "ceiling_z", "floor_picnum", "ceiling_picnum",
         "floor_shade", "ceiling_shade", "floor_heinum", "ceiling_heinum")


def _sector_key(allocation, level):
    fields = level.sectors[allocation.sector_id]["fields"]
    loop = []
    for index in range(fields["wall_ptr"],
                       fields["wall_ptr"] + fields["wall_count"]):
        wall = level.walls[index]["fields"]
        loop.append((wall["x"], wall["y"]))
    if loop:
        start = loop.index(min(loop))
        loop = loop[start:] + loop[:start]
    return tuple(fields[key] for key in _KEYS) + (tuple(loop),)


def _compiled_sectors(program, gates=()) -> dict:
    layout = program.compile()
    # The cemetery gates are raw connections added after `build()` returns
    # (their two edges are on a notched outline, which has no compass face),
    # so a program compiled without them has unpaired portals.
    for gate_id, region_a, region_b, a1, a2 in gates:
        layout.add_connection(gate_id, region_a, region_b, a1=a1, a2=a2,
                              min_width=1024)
    compiled = layout.compile()
    return {region_id: _sector_key(allocation, compiled.level)
            for region_id, allocation in compiled.allocations.items()}


def test_locality(build, venue: str = "saloon") -> dict:
    """Restyle one venue; nothing outside it may move."""
    program, _stacks, gates, *_rest = build()
    before = _compiled_sectors(program, gates)

    program, _stacks, gates, *_rest = build()
    node = citytree.one(program, venue)
    mine = {room.region_id for room in citytree.rooms_under(node)}
    # `ceiling_shade`, not `floor_picnum`: every room in this city restates
    # its own picnums from its material, so overriding one on the venue is a
    # no-op and the test would pass by measuring nothing.  Shade is the
    # value the rooms genuinely inherit.
    node.style = node.style.override(ceiling_shade=7)
    after = _compiled_sectors(program, gates)

    changed = {region_id for region_id in before
               if after.get(region_id) != before[region_id]}
    stray = changed - mine
    return {
        "check": "locality",
        "venue": node.path(),
        "rooms_in_venue": len(mine),
        "sectors_changed": len(changed),
        "changed_outside_the_venue": sorted(stray)[:8],
        "ok": not stray and bool(changed),
    }


def test_exact_frames(build, node_id: str = "aldermack",
                      delta=(4096, 8192)) -> dict:
    """Move a parent; every child's LOCAL outline must be untouched."""
    program = build()[0]
    node = citytree.one(program, node_id)
    rooms = citytree.rooms_under(node)
    local_before = {room.path(): [tuple(p) for p in room.outline]
                    for room in rooms}
    world_before = {room.path(): [tuple(p) for p in room.world_outline()]
                    for room in rooms}

    node.frame = Frame(node.frame.dx + delta[0], node.frame.dy + delta[1],
                       node.frame.dz, node.frame.turns)

    local_drift = [room.path() for room in rooms
                   if [tuple(p) for p in room.outline]
                   != local_before[room.path()]]
    world_wrong = []
    for room in rooms:
        want = [(x + delta[0], y + delta[1])
                for x, y in world_before[room.path()]]
        if [tuple(p) for p in room.world_outline()] != want:
            world_wrong.append(room.path())
    return {
        "check": "exact_frames",
        "node": node.path(),
        "rooms_moved": len(rooms),
        "local_outlines_altered": local_drift[:8],
        "world_outlines_not_translated_exactly": world_wrong[:8],
        "ok": not local_drift and not world_wrong and bool(rooms),
    }


def test_traceable_inheritance(build) -> dict:
    """Every resolved style value names a node that is an ancestor or self."""
    program = build()[0]
    bad = []
    origins = collections.Counter()
    for room in program.rooms():
        legal = {node.path() for node in (*room.ancestors(), room)}
        effective = room.effective_style()
        for name, spec in room.style_provenance().items():
            origins[spec["from"]] += 1
            if spec["from"] not in legal:
                bad.append(f"{room.path()}.{name} <- {spec['from']}")
            elif effective.get(name) != spec["value"]:
                bad.append(f"{room.path()}.{name} value disagrees with origin")
    return {
        "check": "traceable_inheritance",
        "rooms": len(program.rooms()),
        "values_resolved": sum(origins.values()),
        "distinct_origins": len(origins),
        "deepest_origin_share": (
            origins.most_common(1)[0] if origins else None),
        "unsourced": bad[:8],
        "ok": not bad,
    }


def test_rhythm(build) -> dict:
    """An index is only honest when one note serves every sibling that has it.

    Four modules of a counter run, three targets, four pews: interchangeable
    instances of one rhythm, so they take an index and share a note. A stage,
    three rows of seating and a box office are not, and used to be
    `furniture_0` through `furniture_4`.
    """
    program = build()[0]
    faults = citytree.rhythm_faults(program)
    indexed = sum(1 for node, _d in citytree.walk(program)
                  if node.node_id.rpartition("_")[2].isdigit()
                  and node.node_id.rpartition("_")[1])
    return {"check": "rhythm", "indexed_nodes": indexed,
            "faults": faults[:4], "ok": not faults}


def test_plan_correspondence(build) -> dict:
    """Every L1 venue has exactly one node, and every venue node an L1 slot."""
    import city_plan

    program = build()[0]
    declared = citytree.venues(program)
    slots = {venue["id"]: venue for venue in city_plan.plan()["venues"]}
    missing = sorted(set(slots) - set(declared))
    unplanned = sorted(set(declared) - set(slots))
    doubled = sorted(name for name, nodes in declared.items() if len(nodes) > 1)
    wrong_type = sorted(
        name for name, nodes in declared.items()
        if name in slots
        and getattr(nodes[0], "l1_type", None) != slots[name]["type"])
    planned = [name for name, nodes in declared.items()
               if getattr(nodes[0], "built_by", "") == "(planned)"]
    return {
        "check": "plan_correspondence",
        "l1_venues": len(slots), "declared": len(declared),
        "declared_but_unbuilt": sorted(planned),
        "missing": missing, "unplanned": unplanned,
        "doubled": doubled, "wrong_type": wrong_type,
        "ok": not (missing or unplanned or doubled or wrong_type),
    }


def main() -> int:
    import build_skeleton
    rows = [
        test_traceable_inheritance(build_skeleton.build),
        test_exact_frames(build_skeleton.build),
        test_rhythm(build_skeleton.build),
        test_plan_correspondence(build_skeleton.build),
        test_locality(build_skeleton.build),
    ]
    width = max(len(row["check"]) for row in rows)
    failed = 0
    for row in rows:
        mark = "ok  " if row["ok"] else "FAIL"
        detail = {k: v for k, v in row.items() if k not in ("check", "ok")}
        print(f"{mark} {row['check']:<{width}}  {detail}")
        failed += 0 if row["ok"] else 1
    print(f"{len(rows) - failed}/{len(rows)} tree properties hold")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
