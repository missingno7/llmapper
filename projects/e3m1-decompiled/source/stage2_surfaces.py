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

from _common import art_sizes, level, write

from bloodmap.read_surfaces import read_surfaces, summary
from bloodmap.texture_frame import sector_index, wall_visible


def main() -> int:
    world = level()
    sizes = art_sizes()
    result = read_surfaces(world, art_sizes=sizes)
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
    print(f"  u continues        : {continued} of {joins} same-tile joins "
          f"({100.0 * continued / joins:.1f}%)")
    for name, row in by_class.items():
        print(f"    {name:26s} {row['u_continues']:4d}/{row['joins']:4d} "
              f"{row['percent']:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
