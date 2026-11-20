"""A plan of one area of a map, drawn as the editor draws it, with each sector's id and floor.

Planning a change to a built map ("put the station at the head of the
avenue") needs the ground: which sectors are there, how high their floors
are, where the walls run and what is open sky. `bloodmap.analysis.render_svg`
draws a whole map with +Y up; XMapEdit draws +Y down, and a plan that does
not match the editor gets read backwards. This draws a box of the map, +Y
down, in plan units (1,024), one colour per floor height, sky sectors
hatched, and each sector's id and floor z at its centre.

.. code-block:: bash

    python -m tools.plan_view projects/blood-city/level/blood-city-current.MAP \\
        --box 0 -25 45 20 -o work/plan-north.png
    python -m tools.plan_view MAP --box ... --floor-near 61440    # the sewer level
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bloodmap.format import read_map
from bloodmap.sector_geom import outline_and_holes

PU = 1024


def plan(map_path, box, out, *, floor_near=None, band=16384, scale=24):
    from PIL import Image, ImageDraw

    level = read_map(map_path).to_level_ir()
    x0, y0, x1, y1 = (v * PU for v in box)
    W, H = int((x1 - x0) / PU * scale), int((y1 - y0) / PU * scale)
    img = Image.new("RGB", (W + 1, H + 1), (24, 24, 24))
    draw = ImageDraw.Draw(img)

    def to(p):
        return ((p[0] - x0) / PU * scale, (p[1] - y0) / PU * scale)

    rows = []
    for s, sector in enumerate(level.sectors):
        f = sector["fields"]
        z = int(f["floor_z"])
        if floor_near is not None and abs(z - floor_near) > band:
            continue
        outer, holes = outline_and_holes(level, s)
        if not outer:
            continue
        xs = [p[0] for p in outer]
        ys = [p[1] for p in outer]
        if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1:
            continue
        rows.append((abs(min(xs) - max(xs)) * abs(min(ys) - max(ys)), s, outer, holes, z,
                     bool(int(f["ceiling_stat"]) & 1)))
    zs = sorted({r[4] for r in rows})

    def colour(z):
        t = zs.index(z) / max(1, len(zs) - 1)
        return (int(60 + 150 * t), int(90 + 60 * (1 - t)), int(200 - 140 * t))

    for _area, s, outer, holes, z, sky in sorted(rows, key=lambda r: -r[0]):
        draw.polygon([to(p) for p in outer], fill=colour(z), outline=(10, 10, 10))
        # a hole is not this sector's floor: a building stands in a street
        # as a hole in it, and its own sectors (smaller) are drawn after
        for hole in holes:
            if len(hole) >= 3:
                draw.polygon([to(p) for p in hole], fill=(24, 24, 24), outline=(10, 10, 10))
        if sky:
            pts = [to(p) for p in outer]
            bx0, by0 = min(p[0] for p in pts), min(p[1] for p in pts)
            bx1, by1 = max(p[0] for p in pts), max(p[1] for p in pts)
            for k in range(int(bx0), int(bx1), 12):
                draw.line((k, by0, k, by0 + 3), fill=(230, 230, 230))
    for _area, s, outer, holes, z, sky in rows:
        cx = sum(p[0] for p in outer) / len(outer)
        cy = sum(p[1] for p in outer) / len(outer)
        px, py = to((cx, cy))
        draw.text((px - 10, py - 6), f"{s}\n{z // 1024}", fill=(255, 255, 255))
    for k in range(int(box[0]), int(box[2]) + 1):
        if k % 5 == 0:
            draw.line((to((k * PU, y0))[0], 0, to((k * PU, y0))[0], H), fill=(70, 70, 70))
            draw.text((to((k * PU, y0))[0] + 2, 2), str(k), fill=(255, 255, 0))
    for k in range(int(box[1]), int(box[3]) + 1):
        if k % 5 == 0:
            draw.line((0, to((x0, k * PU))[1], W, to((x0, k * PU))[1]), fill=(70, 70, 70))
            draw.text((2, to((x0, k * PU))[1] + 2), str(k), fill=(255, 255, 0))
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out, len(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--box", nargs=4, type=float, required=True,
                        metavar=("X0", "Y0", "X1", "Y1"), help="plan units")
    parser.add_argument("--floor-near", type=int, default=None)
    parser.add_argument("--band", type=int, default=16384)
    parser.add_argument("--scale", type=int, default=24, help="pixels per plan unit")
    parser.add_argument("-o", "--out", default="work/plan.png")
    args = parser.parse_args(argv)
    out, n = plan(args.map, args.box, args.out, floor_near=args.floor_near,
                  band=args.band, scale=args.scale)
    print(f"{n} sectors -> {out} (labels: sector id, floor z / 1024; +Y down, as the editor)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
