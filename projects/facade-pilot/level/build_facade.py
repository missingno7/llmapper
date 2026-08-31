"""Build the facade_run pilot: one street frontage, at two widths.

The first crossing from reading to authoring. Everything dimensional here is
a measurement someone else made:

    one wall tile across the run        98% of 131 campaign multi-opening facades
    a shared header datum               79%
    a shared sill datum                 77%
    a thin helper sector (the kerb)     71%
    openings on whole bays              31% -- so they are given, not snapped
    bay                                 1024 units, from 16 units per tile pixel
    wall thickness (the reveal)         256, the commonest depth behind an opening
    sign height                         2.5 player heights: a preference, cv 0.33

    python projects/facade-pilot/level/build_facade.py

Nothing here invents a fact. The material family, the datums, the bay and the
sign height all come from `reports/blood-facade-grammar.md`; the openings are
given, because 53 repeating runs in 890 campaign candidates is not enough
recurrence to invent a rhythm.

    python work/_facade_pilot.py <out-dir>
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from bloodmap.aperture import (
    FACADE_BAY, JAMB_PICNUM, PLAYER_HEIGHT, THRESHOLD_PICNUM,
    FacadeOpening, facade_run,
)
from bloodmap.format import write_map
from bloodmap.planar_layout import PlanarLayout

#: E3M1's grey ashlar street family, from facade_pass.TILE_SETS["theatre_row"].
WALL = 400
FLOOR, CEILING = 294, 285
#: E3M1's night sky: all 45 of its parallax sectors name this.
SKY = 3491

STREET_DEPTH = 6 * FACADE_BAY
KERB = FACADE_BAY // 4
#: One shared header and one shared sill, which is what makes several openings
#: read as one facade. Blood z grows downward.
HEADER_Z = -40960
SILL_Z = -1024


def build(name: str, bays: int, openings, *, sign_on: int, text: str):
    """One street with a frontage along its south edge."""
    width = bays * FACADE_BAY
    layout = PlanarLayout(name=name)
    # The kerb: the thin helper sector 71% of multi-opening campaign facades
    # carry. facade_run leaves it to composition because it reshapes the
    # street, not the frontage -- so the street stops a strip short and this
    # fills the band.
    layout.add_region(
        "region:kerb",
        [(0, 0), (width, 0), (width, KERB), (0, KERB)],
        floor_z=0, ceiling_z=-6 * PLAYER_HEIGHT,
        wall_picnum=WALL, floor_picnum=THRESHOLD_PICNUM, ceiling_picnum=SKY,
        parallax_ceiling=True,
        intent={"purpose": f"{name}: kerb strip along the frontage"})
    layout.add_connection("connection:kerb", "region:kerb", "region:street",
                          a1=(0, KERB), a2=(width, KERB), min_width=width)
    layout.add_region(
        "region:street",
        [(0, KERB), (width, KERB), (width, STREET_DEPTH), (0, STREET_DEPTH)],
        floor_z=0, ceiling_z=-6 * PLAYER_HEIGHT,
        wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=SKY,
        parallax_ceiling=True,
        intent={"purpose": f"{name}: the street the frontage is seen from"})

    spec = [FacadeOpening(bay=b, bays=w, sign=(text if i == sign_on else None))
            for i, (b, w) in enumerate(openings)]
    built = facade_run(
        layout, f"facade_{name}",
        host_region="region:kerb",
        a1=(0, 0), a2=(width, 0),
        depth=3 * FACADE_BAY,
        openings=spec,
        wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
        header_z=HEADER_Z, sill_z=SILL_Z,
        jamb_picnum=JAMB_PICNUM)

    layout.set_player_start("region:street", x=width // 2,
                            y=STREET_DEPTH * 2 // 3, z=0)
    return layout, built


CASES = {
    # Same relationships, two widths: the bays, the datums and the sign seat
    # must survive the change. That is Phase 13's exit shape, piloted early.
    "narrow": dict(bays=6, openings=[(1, 1), (3, 1)], sign_on=0, text="MEATS"),
    "wide": dict(bays=10, openings=[(1, 1), (3, 1), (6, 2)], sign_on=0,
                 text="MEATS"),
}


def main(argv):
    out = (pathlib.Path(argv[0]) if argv else
           pathlib.Path(__file__).resolve().parents[1] / "level")
    out.mkdir(parents=True, exist_ok=True)
    report = {"$schema": "llmapper.facade-pilot", "schema_version": 1,
              "cases": {}}
    for name, case in CASES.items():
        layout, built = build(name, **case)
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        path = out / f"facade-{name}.MAP"
        write_map(disk, path)
        report["cases"][name] = {
            "map": str(path),
            "sectors": len(disk.sectors), "walls": len(disk.walls),
            "sprites": len(disk.sprites),
            **built,
        }
        print(f"  {name:8} {len(disk.sectors)} sectors {len(disk.walls)} walls "
              f"{len(disk.sprites)} sprites -> {path}")
    report_dir = pathlib.Path(__file__).resolve().parents[1] / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "facade-pilot.json").write_text(json.dumps(report, indent=2) + "\n",
                                           encoding="utf-8", newline="\n")
    print(f"\nwrote {out / 'facade-pilot.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
