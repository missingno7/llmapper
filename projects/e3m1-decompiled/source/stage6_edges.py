"""Stage 6 -- the edge chain: how E3M1's ground meets its termination.

`bloodmap.read_edges` walks the boundary of the GROUND -- not of the outdoor
network, which contains the end walls and would swallow them -- and gives each
record an edge kind read off what is on its far side, never off a tile. The
chain is then the runs of consecutive records of one kind, in Build's own
`point2` order, so a segment is a stretch a body walking the edge would call
one thing.

    PYTHONPATH=. python projects/e3m1-decompiled/source/stage6_edges.py
"""

from __future__ import annotations

from _common import level, write
from _review import Tree, answers, write_pack

from bloodmap.read_edges import read_edges, summary
from bloodmap.read_joins import surface_kinds
from bloodmap.texture_frame import sector_index


def _far_sectors(world, result, kind: str) -> list[int]:
    return sorted({int(world.walls[int(record)]["fields"]["next_sector"])
                   for record, value in result["kinds"].items()
                   if value == kind
                   and int(world.walls[int(record)]["fields"]["next_sector"]) >= 0})


def _claims(world, result) -> list[dict]:
    """What the edge model reproduces, field by field.

    Three predictions, each of which could have come back wrong:

    * a BACKING mass has no interior, so its `ceiling_z` is its `floor_z`;
    * a BUILDING BACK is one-sided against the void, so it takes no facade run
      and no masked band: its `over_picnum` is unused;
    * nothing else. The chain says which kind each record is; it does not say
      what any of them wears, and claiming a tile here would be borrowing
      layer 2's answer.
    """
    rows = []
    for sector in _far_sectors(world, result, "backing"):
        fields = world.sectors[sector]["fields"]
        rows.append({
            "kind": "sector", "index": sector, "field": "ceiling_z",
            "owner": "edge:backing", "value": int(fields["ceiling_z"]),
            "why": ("a backing mass has no interior, so its ceiling is its "
                    "floor: nothing is drawn inside it and no body stands "
                    "in it")})
    for record, value in result["kinds"].items():
        if value != "building_back":
            continue
        rows.append({
            "kind": "wall", "index": int(record), "field": "over_picnum",
            "owner": "edge:building_back",
            "value": int(world.walls[int(record)]["fields"]["over_picnum"]),
            "why": ("a one-sided wall against the void carries no facade run "
                    "and no masked band, so its overlay tile is unused")})
    return rows


def _review(world, result, kinds) -> dict:
    tree = Tree(len(world.sectors), "E3M1 -- the edge chain")
    ground = result["ground_sectors"]
    tree.add("ground", "ground", f"the ground the chain bounds "
             f"({len(ground)} sectors)", tree.root.id, ground)
    for kind in sorted(result["counts"]):
        far = _far_sectors(world, result, kind)
        segments = [row for row in result["segments"] if row["kind"] == kind]
        tree.add(f"edge:{kind}", "edge_kind",
                 f"{kind}: {result['counts'][kind]} records in "
                 f"{len(segments)} segments", tree.root.id, far)
    offmap = result["offmap"].get("offmap_sectors") or []
    if offmap:
        tree.add("offmap", "offmap",
                 f"unreachable beyond the skin ({len(offmap)} sectors, "
                 f"{result['offmap'].get('by_kind')})", tree.root.id, offmap)
    questions = [
        {"node": "edge:building_back",
         "question": (f"{result['counts'].get('building_back', 0)} of "
                      f"{len(result['boundary_records'])} boundary records are "
                      f"one-sided walls against the void -- section 15b's "
                      f"'a building may be a link in the chain'. E3M1 spends "
                      f"no sector behind any of them. Is `building_back` an "
                      f"edge KIND, or just the absence of one?"),
         "recommended_default": ("a kind: it is what the plan states for a "
                                 "side that needs no street behind it, and "
                                 "the solver drops the perimeter lane there. "
                                 "The reader counts it as one and the census "
                                 "says how much of E3M1's edge it is"),
         "evidence": "references/edge-chain.json: counts"},
        {"node": "offmap",
         "question": ("Section 14 records `reachability.classify_offmap` as "
                      "raising TypeError on every map, which is why the "
                      "enclosure-with-backdrop member has no reader. It does "
                      "not raise: on E3M1 it returns 374 reached, 8 off-map, "
                      "2 logic closets and 6 bare. Should the backdrop hunt "
                      "be reopened?"),
         "recommended_default": ("yes, but not here: E3M1 has no enclosure, so "
                                 "its off-map geometry is closets and scraps. "
                                 "The hunt belongs on the curated community "
                                 "population, as precedent"),
         "evidence": "references/edge-chain.json: offmap"},
        {"node": "edge:interior_doorway",
         "question": (f"{result['counts'].get('interior_doorway', 0)} boundary "
                      f"records open into an interior. A way IN is not a "
                      f"termination, so the chain is not closed by "
                      f"terminations alone. Should a doorway be a member of "
                      f"the edge family, or a hole in the chain?"),
         "recommended_default": ("a member, named `gate` in `joins.py`'s "
                                 "vocabulary: section 14 already says a road "
                                 "may end at a junction, a gate or an edge "
                                 "kind, and a doorway is the building-scale "
                                 "gate"),
         "evidence": "references/edge-chain.json: segments"},
    ]
    return write_pack(6, tree, "E3M1 layer 6: the edge chain", questions)


def main() -> int:
    world = level()
    owners = sector_index(world)
    kinds = surface_kinds(world, owners=owners)["kinds"]
    result = read_edges(world, kinds, owners=owners)
    stats = summary(result)

    #: A residue of zero here is honest but easy: `building_back` catches
    #: every one-sided record and `interior_doorway` every way in, so almost
    #: nothing can fall through. The number that says how much of E3M1's edge
    #: is a TERMINATION is the family's own share, and it is reported beside
    #: the residue so the zero cannot be read as "understood".
    family = sum(count for kind, count in result["counts"].items()
                 if kind in ("end_wall", "chasm", "horizon",
                             "enclosure_backdrop", "waterfront"))
    payload = {
        "reader": "bloodmap.read_edges (new; reuses "
                  "reachability.classify_offmap for the backdrop hunt)",
        "summary": stats,
        "records_in_the_edge_family_proper": family,
        "records_that_are_the_void_behind_a_building": (
            result["counts"].get("building_back", 0)
            + result["counts"].get("backing", 0)),
        "records_that_are_a_way_in": result["counts"].get("interior_doorway", 0),
        "ground_sectors": result["ground_sectors"],
        "boundary_records": result["boundary_records"],
        "kinds": result["kinds"],
        "why": result["why"],
        "counts": result["counts"],
        "segments": result["segments"],
        "segment_counts": result["segment_counts"],
        "residue_records": result["residue_records"],
        "offmap": result["offmap"],
        "disagreements_with_the_measured_facts": _disagreements(result),
        "ledger": {
            "reader": "bloodmap.read_edges (new)",
            "gate": ("every record of the ground's own outline given an edge "
                     "kind from what is on its far side, then chained into "
                     "segments in Build's point2 order"),
            "population": f"{len(result['boundary_records'])} boundary records",
            "explained": (len(result["boundary_records"])
                          - len(result["residue_records"])),
            "residue": len(result["residue_records"]),
            "residue_percent": stats["residue_percent"],
            "residue_is": ("boundary records in no edge class. Zero here is "
                           "honest but easy: only "
                           f"{family} of {len(result['boundary_records'])} "
                           "records are a member of the edge FAMILY proper; "
                           f"{result['counts'].get('building_back', 0) + result['counts'].get('backing', 0)} "
                           "are the void behind a building and "
                           f"{result['counts'].get('interior_doorway', 0)} "
                           "are a way in"),
            "disagreements": _disagreements(result),
        },
    }
    payload["review"] = _review(world, result, kinds)
    payload["owner_marks_read_back"] = answers(6)
    write("edge-chain.json", payload)

    print(f"E3M1 edge chain: {len(result['ground_sectors'])} ground sectors, "
          f"{len(result['boundary_records'])} boundary records in "
          f"{len(result['segments'])} segments")
    for kind, count in sorted(result["counts"].items(), key=lambda row: -row[1]):
        print(f"    {kind:20s} {count:4d} records in "
              f"{result['segment_counts'].get(kind, 0)} segments")
    print(f"  the edge family    : {family} records; "
          f"{result['counts'].get('building_back', 0) + result['counts'].get('backing', 0)} "
          f"are the void behind a building, "
          f"{result['counts'].get('interior_doorway', 0)} are a way in")
    print(f"  off-map            : {result['offmap'].get('by_kind')} "
          f"({result['offmap'].get('reached')} of {len(world.sectors)} reached)")
    print(f"  RESIDUE            : {len(result['residue_records'])} records "
          f"({stats['residue_percent']}%)")
    return 0


def _disagreements(result) -> list[dict]:
    out = [{
        "claim": "reachability.classify_offmap raises TypeError on every map, "
                 "so the enclosure-with-backdrop member has no reader "
                 "(decisions section 14)",
        "the_reader_finds": (
            f"it returns a classification: "
            f"{result['offmap'].get('reached')} sectors reached, "
            f"{len(result['offmap'].get('offmap_sectors') or [])} off-map, "
            f"{result['offmap'].get('by_kind')}"),
        "reconciled": "the reader works; what is missing is a corpus precedent "
                      "for an enclosure, and E3M1 is not one",
    }]
    if "chasm" not in result["counts"] and "horizon" not in result["counts"]:
        out.append({
            "claim": "the map edge is a family of five",
            "the_reader_finds": (
                f"E3M1 uses {sorted(result['counts'])}: no chasm, no horizon, "
                f"no waterfront and no enclosure anywhere on its boundary"),
            "reconciled": "the family is right and E3M1 exercises three of it; "
                          "the other members are attested on DWE3M1 and "
                          "DWE3M10, as the decisions say",
        })
    return out


if __name__ == "__main__":
    raise SystemExit(main())
