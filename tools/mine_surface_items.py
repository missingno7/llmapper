"""What stands on a counter, and how it is arranged.

The fixture layer stops at the furniture: `fixtures.py` builds a counter, a
pedestal, a booth. The next scale down is what sits *on* it -- glasses on a
bar, bottles behind it, tools on a bench, stock on a shelf -- and the
project has nothing for it at all.

A *surface* here is a small sector standing proud of a bigger neighbour --
the same object `mine_fixtures.py` calls a fixture -- and a *surface item*
is a sprite standing inside its footprint at about its own floor height.
That is the whole detection: no tile list, no guessing, just what is
physically on top of something.

What the answer has to cover, because a run type needs all of it:

* which tiles, and are they floor-aligned planes or face sprites;
* how many per unit of surface, and how that scales with the surface;
* the spacing along the long axis, in map units and in item widths;
* whether they arrive in runs or scattered.

Derived: every count, tile, spacing and density. Interpreted: nothing.

    python tools/mine_surface_items.py -o knowledge/blood/design/surface-items-v1.json
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bloodmap.art import read_art_directory
from bloodmap.format import read_map

#: The maps the project already mines for fixtures, plus the two richest
#: interiors in the corpus.
SOURCES = ("DWE3M1", "DWE3M10", "E6M1", "E4M9", "E1M4", "E1M1", "E3M2",
           "E2M1", "E1M5", "E3M1")

HOST_AREA = 4_000_000
ALIGN_MASK = 0x30
ALIGN_FLOOR = 0x20
ALIGN_WALL = 0x10

#: How far above a surface's own floor a sprite may sit and still be ON it,
#: in map units. A body is 16,960 tall; a glass is a fraction of that, and
#: anything more than about a third of a player is hanging over the counter
#: rather than standing on it.
SIT_TOLERANCE = 5_600


def _outline(m, s):
    return [(m.walls[w].x, m.walls[w].y)
            for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]


def _area(points) -> float:
    total = 0.0
    for index, (ax, ay) in enumerate(points):
        bx, by = points[(index + 1) % len(points)]
        total += ax * by - bx * ay
    return abs(total) / 2


def _inside(points, x, y) -> bool:
    hit = False
    count = len(points)
    for index in range(count):
        ax, ay = points[index]
        bx, by = points[(index + 1) % count]
        if (ay > y) != (by > y):
            cross = ax + (y - ay) * (bx - ax) / (by - ay)
            if cross > x:
                hit = not hit
    return hit


def surfaces(m):
    """Every small sector standing proud of a bigger neighbour."""
    out = []
    for index, sector in enumerate(m.sectors):
        if sector.wall_count < 4:
            continue
        points = _outline(m, sector)
        if _area(points) > HOST_AREA:
            continue
        neighbours = [m.walls[w].next_sector
                      for w in range(sector.wall_ptr,
                                     sector.wall_ptr + sector.wall_count)]
        neighbours = [n for n in neighbours if n >= 0]
        if not neighbours:
            continue
        host = max(neighbours,
                   key=lambda n: _area(_outline(m, m.sectors[n])))
        rise = m.sectors[host].floor_z - sector.floor_z
        if rise <= 0:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        out.append({
            "sector": index, "points": points, "rise": rise,
            "floor_z": sector.floor_z, "tile": sector.floor_picnum,
            "width": max(xs) - min(xs), "depth": max(ys) - min(ys),
            "area": _area(points),
        })
    return out


def survey(name: str, art) -> dict:
    m = read_map(f"maps/blood/{name}.MAP")
    found = surfaces(m)
    by_sector = collections.defaultdict(list)
    for sprite in m.sprites:
        if sprite.status != 0 or sprite.type != 0:
            continue
        by_sector[sprite.sector].append(sprite)

    carried = 0
    items = collections.Counter()
    alignment = collections.Counter()
    per_surface = []
    gaps_units = []
    gaps_widths = []
    density = []
    heights = []
    for surface in found:
        standing = []
        for sprite in by_sector.get(surface["sector"], ()):
            if not _inside(surface["points"], sprite.x, sprite.y):
                continue
            # z is the sprite's centre; a floor-aligned plane sits at its own
            # z, a face sprite reaches down to its bottom.
            above = surface["floor_z"] - sprite.z
            if -256 <= above <= SIT_TOLERANCE:
                standing.append(sprite)
        per_surface.append(len(standing))
        if not standing:
            continue
        carried += 1
        for sprite in standing:
            items[sprite.picnum] += 1
            bits = sprite.cstat & ALIGN_MASK
            alignment["floor" if bits == ALIGN_FLOOR
                      else "wall" if bits == ALIGN_WALL else "face"] += 1
            heights.append(surface["floor_z"] - sprite.z)
        # Spacing along the surface's long axis.
        horizontal = surface["width"] >= surface["depth"]
        along = sorted((sprite.x if horizontal else sprite.y)
                       for sprite in standing)
        for a, b in zip(along, along[1:]):
            if b > a:
                gaps_units.append(b - a)
                size = art.get(int(standing[0].picnum))
                if size and size[0]:
                    gaps_widths.append((b - a)
                                       / max(1, size[0] * standing[0].x_repeat / 4))
        run = max(surface["width"], surface["depth"])
        if run:
            density.append(len(standing) / (run / 1024.0))

    def spread(values):
        values = sorted(values)
        if not values:
            return {"n": 0}
        return {"n": len(values), "median": round(statistics.median(values), 3),
                "q1": round(values[len(values) // 4], 3),
                "q3": round(values[3 * len(values) // 4], 3),
                "min": round(values[0], 3), "max": round(values[-1], 3)}

    return {
        "map": name,
        "surfaces": len(found),
        "surfaces_carrying_something": carried,
        "carry_share": round(carried / max(1, len(found)), 3),
        "items": sum(items.values()),
        "items_per_surface": spread(per_surface),
        "items_per_plan_unit_of_run": spread(density),
        "gap_units": spread(gaps_units),
        "gap_item_widths": spread(gaps_widths),
        "height_above_surface": spread(heights),
        "alignment": dict(alignment),
        "top_tiles": items.most_common(20),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--output")
    parser.add_argument("--reference", default="reference/blood")
    args = parser.parse_args(argv)

    tiles = read_art_directory(args.reference)
    art = {tile: (item.width, item.height) for tile, item in tiles.items()}

    rows = [survey(name, art) for name in SOURCES]
    total = collections.Counter()
    carried = surfaces_total = 0
    for row in rows:
        for tile, count in row["top_tiles"]:
            total[tile] += count
        carried += row["surfaces_carrying_something"]
        surfaces_total += row["surfaces"]
        print(f"  {row['map']:9s} surfaces {row['surfaces']:4d} "
              f"carrying {row['surfaces_carrying_something']:3d} "
              f"({row['carry_share']:.2f})  items {row['items']:4d}  "
              f"gap {row['gap_units'].get('median', 0)}")
    report = {
        "$schema": "llmapper.blood-surface-items",
        "schema_version": 1,
        "note": ("Derived: every count, tile, spacing and density. A surface "
                 "is a small sector standing proud of a bigger neighbour; an "
                 "item is a sprite inside its footprint at about its floor."),
        "sources": list(SOURCES),
        "maps": rows,
        "corpus": {
            "surfaces": surfaces_total,
            "carrying_something": carried,
            "carry_share": round(carried / max(1, surfaces_total), 3),
            "top_tiles": total.most_common(24),
        },
    }
    if args.output:
        pathlib.Path(args.output).write_text(json.dumps(report, indent=1),
                                             encoding="utf-8")
        print(f"wrote {args.output}")
    print(f"  corpus: {carried}/{surfaces_total} surfaces carry something "
          f"({100.0 * carried / max(1, surfaces_total):.1f}%)")
    print(f"  commonest: {total.most_common(12)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
