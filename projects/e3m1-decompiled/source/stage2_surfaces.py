"""Stage 2 -- surfaces and frames: "one record, one frame", read backwards.

`bloodmap.read_surfaces` groups E3M1's wall records into the surfaces one
material, projected once from one origin at one scale, would have produced,
fits that frame, and replays it through the WRITER (`resolve_run`) to see
which records come back field for field.

The gate is the replay, and it is asymmetric on purpose. A frame fitted to a
single record always reproduces it, so a record only counts as explained when
it sits in a surface of two or more that ONE frame reproduces exactly.

    PYTHONPATH=. python projects/e3m1-decompiled/source/stage2_surfaces.py
"""

from __future__ import annotations

from collections import Counter

from _common import art_sizes, emit_claims, level, write
from _review import Tree, answers, write_pack

from bloodmap.read_stairs import read_stairs
from bloodmap.read_surfaces import read_surfaces, summary
from bloodmap.texture_frame import sector_index, wall_visible


def _review(level_ir, result, owners, stairs) -> dict:
    """The pack: one node per surface that spans more than one record.

    A surface owns wall records, and the pack colours sectors, so a surface
    node holds the sectors its records belong to. A sector no multi-record
    surface touches is unowned -- which is this layer's residue drawn on the
    map: the parts of E3M1 where every wall carries its own projection.
    """
    tree = Tree(len(level_ir.sectors), "E3M1 -- surfaces of more than one record")
    by_tile: dict[int, list] = {}
    for item in result["surfaces"]:
        if len(item.records) > 1:
            by_tile.setdefault(item.tile, []).append(item)
    for tile in sorted(by_tile):
        group = by_tile[tile]
        sectors = {owners[record] for item in group for record in item.records}
        tree.add(f"tile:{tile}", "material", f"tile {tile} "
                 f"({len(group)} surfaces)", tree.root.id, sectors)
        for item in group:
            tree.add(item.surface_id, "surface",
                     f"{item.surface_id} x{len(item.records)} "
                     f"{'exact' if item.understood else 'partial'}",
                     f"tile:{tile}",
                     {owners[record] for record in item.records})
    #: Stairs are STRUCTURES, not mechanisms: E3M1's helix carries no sector
    #: type on 19 of its 25 sectors and nothing about it moves.
    tree.add("stairs", "structure",
             f"stepped runs ({len(stairs['runs'])}, "
             f"{stairs['runs_with_a_constant_rise']} of constant rise)",
             tree.root.id, stairs["sectors_in_a_run"])
    for run in stairs["runs"]:
        tree.add(run["id"], "stepped_run",
                 f"{run['id']} x{len(run['sectors'])} rise "
                 f"{run['fit']['rise']}"
                 f"{'' if run['fit']['constant_rise'] else ' (not constant)'}",
                 "stairs", run["sectors"])
    biggest = max((item for group in by_tile.values() for item in group),
                  key=lambda item: len(item.records))
    questions = [
        {"node": biggest.surface_id,
         "question": ("E3M1's largest recovered surface spans "
                      f"{len(biggest.records)} records of tile {biggest.tile}. "
                      "Only 31% of the map's records sit in a shared "
                      "projection at all. Should the writer keep projecting "
                      "one frame per RUN, or per FLAT FACE, which is what "
                      "E3M1 does (88% of collinear joins continue, 15-51% of "
                      "bends, 13% of reflex corners)?"),
         "recommended_default": ("keep the run, and add nothing: "
                                 "RUN_BREAK_DEGREES already stops at 100 "
                                 "degrees, and the reader's census is the "
                                 "evidence for whether a bend break belongs "
                                 "in the writer too. Decide it on the whole "
                                 "campaign, not on E3M1"),
         "evidence": "references/surfaces.json: u_continuity_by_join_class"},
        {"node": "level",
         "question": ("2481 records, 1075 of them with no same-material "
                      "neighbour at all. Is a lone record a SURFACE of one, "
                      "or is it evidence that our surface model does not fit "
                      "how Blood was authored?"),
         "recommended_default": ("count it as residue, as here: a frame "
                                 "fitted to one record reproduces it for "
                                 "free, and calling that understanding is how "
                                 "a coverage report reaches 100%"),
         "evidence": "references/surfaces.json: residue_solitary_records"},
    ]
    return write_pack(2, tree, "E3M1 layer 2: surfaces and frames", questions)


FRAME_FIELDS = ("picnum", "x_repeat", "x_panning", "y_repeat", "y_panning")


def _claims(world, result, owners, stairs) -> list[dict]:
    """What this layer reproduces, field by field.

    Only records inside a surface of MORE THAN ONE record: a frame fitted to a
    single record reproduces it for free, and a ledger that counted that would
    hand the map back to itself and call it understood.
    """
    rows = []
    for surface in result["surfaces"]:
        if len(surface.records) < 2:
            continue
        for record in surface.exact:
            face = world.walls[record]["fields"]
            for name in FRAME_FIELDS:
                rows.append({
                    "kind": "wall", "index": record, "field": name,
                    "owner": surface.surface_id, "value": int(face[name]),
                    "why": (f"one WallRunFrame (tile {surface.frame.tile}, "
                            f"u0 {surface.frame.u0}, v0 {surface.frame.v0}) "
                            f"over {len(surface.records)} records replays "
                            f"through texture_frame.resolve_run to this value")})
    for run in stairs["runs"]:
        fit = run["fit"]
        for index in fit["reproduces"]:
            rows.append({
                "kind": "sector", "index": index, "field": "floor_z",
                "owner": run["id"],
                "value": int(world.sectors[index]["fields"]["floor_z"]),
                "why": (f"a stepped run of rise {fit['rise']} from "
                        f"{fit['origin']}: this floor lands on the fitted "
                        f"progression")})
    return rows


def main() -> int:
    world = level()
    sizes = art_sizes()
    result = read_surfaces(world, art_sizes=sizes)
    stairs = read_stairs(world)
    stats = summary(result)
    owners = sector_index(world)

    surfaces = [item.to_dict() for item in result["surfaces"]
                if len(item.records) > 1]
    biggest = sorted(surfaces, key=lambda row: -len(row["records"]))[:20]
    continuity = result["census"]["continuity_by_join_class"]
    joins = sum(row["n"] for row in continuity.values())
    continued = sum(row["x"] for row in continuity.values())

    #: The corner rule, read off E3M1 rather than assumed: where does a
    #: material actually stop? Split by the join's own class.
    by_class = {
        name: {"joins": row["n"], "u_continues": row["x"],
               "percent": round(100.0 * row["x"] / row["n"], 1) if row["n"] else 0.0}
        for name, row in sorted(continuity.items())}

    visible = sum(1 for index in range(len(world.walls))
                  if wall_visible(world, index, owners))
    payload = {
        "reader": "bloodmap.read_surfaces (new; replays through "
                  "texture_frame.resolve_run, the writer)",
        "summary": stats,
        "records_visible": visible,
        "surfaces_of_more_than_one_record": biggest,
        "surface_count_by_size": dict(sorted(Counter(
            len(item.records) for item in result["surfaces"]).items())),
        "u_continuity_by_join_class": by_class,
        "u_continuity_overall": {
            "same_tile_joins": joins, "u_continues": continued,
            "percent": round(100.0 * continued / joins, 1) if joins else 0.0},
        "break_reasons": dict(result["census"]["breaks"]),
        "residue_broken_records": result["residue_broken"],
        "residue_solitary_records": result["residue_solitary"],
        "records_mismatched": result["records_mismatched"],
        "ledger": {
            "reader": "bloodmap.read_surfaces (new)",
            "gate": ("replay each recovered frame through "
                     "texture_frame.resolve_run and diff picnum, x_repeat, "
                     "x_panning, y_repeat and y_panning per record"),
            "population": f"{stats['records']} wall records",
            "explained": stats["records_explained"],
            "residue": stats["residue_records"],
            "residue_percent": stats["residue_percent"],
            "residue_is": ("records broken off a same-material neighbour "
                           f"({stats['residue_broken']}), records with no "
                           f"same-material neighbour at all "
                           f"({stats['residue_solitary']}), and records one "
                           f"frame does not reproduce "
                           f"({stats['records_mismatched']})"),
            "disagreements": [],
        },
    }
    payload["stairs"] = stairs
    payload["claims"] = emit_claims(2, _claims(world, result, owners, stairs),
                                    note=("the five texture fields of every "
                                          "record a shared projection "
                                          "reproduces exactly, and the floor z "
                                          "of every stair sector its fitted "
                                          "rise reproduces"))
    payload["review"] = _review(world, result, owners, stairs)
    payload["owner_marks_read_back"] = answers(2)
    write("surfaces.json", payload)

    print(f"E3M1 surfaces: {stats['surfaces']} recovered, "
          f"{stats['surfaces_of_more_than_one_record']} of more than one record")
    print(f"  explained          : {stats['records_explained']} of "
          f"{stats['records']} records ({100 - stats['residue_percent']:.2f}%)")
    print(f"  RESIDUE            : {stats['residue_records']} records "
          f"({stats['residue_percent']}%) = {stats['residue_broken']} broken + "
          f"{stats['residue_solitary']} solitary + "
          f"{stats['records_mismatched']} mismatched")
    print(f"  breaks             : {stats['breaks']}")
    print(f"  stepped runs       : {len(stairs['runs'])}, "
          f"{stairs['runs_with_a_constant_rise']} of constant rise; "
          f"{len(stairs['sectors_the_fit_reproduces'])} of "
          f"{len(stairs['sectors_in_a_run'])} sectors reproduced, residual "
          f"{stairs['sectors_in_the_residual']}")
    print(f"  u continues        : {continued} of {joins} same-tile joins "
          f"({100.0 * continued / joins:.1f}%)")
    for name, row in by_class.items():
        print(f"    {name:26s} {row['u_continues']:4d}/{row['joins']:4d} "
              f"{row['percent']:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
