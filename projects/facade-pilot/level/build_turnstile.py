"""Build a turnstile entrance: two counter-rotating rotors flanking one way in.

Everything except the opening pose and the spin period comes from the template
mined off E1M4 151/314 and DWE1M9 61/64 -- see `bloodmap.mechanism`'s
`TURNSTILE_TEMPLATE` and the docstring on `turnstile`.

The period is E1M4's own 255. Death Wish runs 100; both are in the template
and neither is a default this file invents.

    python projects/facade-pilot/level/build_turnstile.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from bloodmap.format import write_map
from bloodmap.mechanism import PLAYER_HEIGHT, turnstile_pair
from bloodmap.planar_layout import PlanarLayout

U = 1024
#: E1M4's spin period. DWE1M9 runs 100; the template carries both.
PERIOD = 255
WALL, FLOOR, CEILING, SKY = 400, 294, 285, 3491

#: Each rotor is a square drum. The pair flanks a 2-unit gap, which is the
#: passage: two portal walls form the way through, as all four mined rotors do.
ROTOR = 2 * U
GAP = 2 * U
COURT = 12 * U


def build():
    """Outside and inside, joined only through the two rotors.

    All four mined rotors have exactly two portal walls: the rotor *is* the
    passage, not an island standing in one. So the two drums sit in the wall
    between the forecourt and the yard, and everything either side of them is
    wall -- which in Build is void.
    """
    layout = PlanarLayout(name="turnstile")
    mid = COURT // 2
    y0, y1 = mid - ROTOR // 2, mid + ROTOR // 2
    left_x0 = mid - GAP // 2 - ROTOR
    right_x0 = mid + GAP // 2

    for name, (ya, yb), purpose in (
            ("outside", (0, y0), "the forecourt the turnstile is entered from"),
            ("inside", (y1, COURT), "the yard it lets on to")):
        layout.add_region(
            f"region:{name}", [(0, ya), (COURT, ya), (COURT, yb), (0, yb)],
            floor_z=0, ceiling_z=-4 * PLAYER_HEIGHT,
            wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=SKY,
            parallax_ceiling=True, intent={"purpose": purpose})

    outlines = (
        [(left_x0, y0), (left_x0 + ROTOR, y0), (left_x0 + ROTOR, y1), (left_x0, y1)],
        [(right_x0, y0), (right_x0 + ROTOR, y0), (right_x0 + ROTOR, y1), (right_x0, y1)],
    )
    pivots = ((left_x0 + ROTOR // 2, mid), (right_x0 + ROTOR // 2, mid))

    built = turnstile_pair(
        layout, "turnstile", outlines=outlines, pivots=pivots,
        period=PERIOD, floor_z=0, ceiling_z=-2 * PLAYER_HEIGHT,
        wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING)

    for index, outline in enumerate(outlines):
        side = "a" if index == 0 else "b"
        layout.add_connection(
            f"connection:turnstile:{side}:front", "region:outside",
            f"turnstile:{side}", a1=outline[0], a2=outline[1], min_width=U)
        layout.add_connection(
            f"connection:turnstile:{side}:back", f"turnstile:{side}",
            "region:inside", a1=outline[3], a2=outline[2], min_width=U)

    layout.set_player_start("region:outside", x=mid, y=y0 // 2, z=0)
    return layout, built


def main(argv):
    out = pathlib.Path(argv[0]) if argv else pathlib.Path(__file__).resolve().parent
    layout, built = build()
    disk = layout.compile().level.to_disk_map()
    path = out / "turnstile.MAP"
    write_map(disk, path)
    report_dir = pathlib.Path(__file__).resolve().parents[1] / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "turnstile.json").write_text(
        json.dumps({"map": str(path), "sectors": len(disk.sectors),
                    "walls": len(disk.walls), "sprites": len(disk.sprites),
                    **built}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  {len(disk.sectors)} sectors {len(disk.walls)} walls "
          f"{len(disk.sprites)} sprites -> {path}")
    for rotor in built["rotors"]:
        print(f"    {rotor['region']:14} period {rotor['period']:4} "
              f"clockwise {rotor['clockwise']}  busy "
              f"{rotor['behavior']['busy_time_a']}/{rotor['behavior']['busy_time_b']}"
              f"  blades {len(rotor['blades'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
