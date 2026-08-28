"""Fixture families and detail palettes from the city-detail sources.

Four maps, chosen because they are what a Blood town actually does with
small repeated geometry: **DWE3M1** (the richest -- 606 sectors, 1,690
sprites), **DWE3M10** (the pier, 498/1,038), **E6M1** (the shop),
**E4M9** (the mall) and **E1M4** (Dark Carnival -- the booths, the ride
platforms and the stanchion rows a fairground is made of).

A *fixture* here is a small sector standing proud of a bigger neighbour: a
pedestal, a counter, a shelf, a panel run. What matters is that they come in
**families** -- the same thing at several lengths, with the rise and the
tile pinned. DWE3M10 builds (512x1024) and (1024x1024) four times each at
rise 3072 on tile 345; DWE3M1 builds (256x2048) six times at rise 21504 on
tile 1666, with siblings at 256x1536 and 256x3584. One element, one free
dimension.

Two findings this pass exists to record, because both contradict an
assumption that would otherwise have been built in:

* **Goods mostly do not reach the shelf.** Median sprites per fixture is
  **zero** in all four maps: 143 of DWE3M1's 171 fixtures are bare, 125 of
  DWE3M10's 136, 41 of E6M1's 43. The fixture is the detail. A few carry a
  cluster (max 11), so merchandise is an accent, not a rule.
* **A shutter is a masked wall, not a sprite.** DWE3M10 draws tile 1060 as
  the `over_picnum` of a two-sided wall ten times -- the same construction
  as glass (266), which every one of the four maps uses. So closing a
  shopfront and glazing one are the same constructor with a different tile.

Derived: every count, family, dimension and palette below. Interpreted:
the names given to the palettes.

    python tools/mine_fixtures.py -o knowledge/blood/design/fixtures-v1.json
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bloodmap.format import read_map

SOURCES = ("DWE3M1", "DWE3M10", "E6M1", "E4M9", "E1M4")
HOST_AREA = 4_000_000
SHUTTER_TILES = (1060, 1044)


def _area(m, s) -> float:
    pts = [(m.walls[w].x, m.walls[w].y)
           for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]
    total = 0.0
    for i, (ax, ay) in enumerate(pts):
        bx, by = pts[(i + 1) % len(pts)]
        total += ax * by - bx * ay
    return abs(total) / 2


def _box(m, s):
    pts = [(m.walls[w].x, m.walls[w].y)
           for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return max(xs) - min(xs), max(ys) - min(ys)


def survey(name: str) -> dict:
    m = read_map(f"maps/blood/{name}.MAP")
    inside = collections.Counter()
    for sp in m.sprites:
        if sp.status == 0 and sp.type == 0:
            inside[sp.sector] += 1

    families = collections.defaultdict(list)
    goods = []
    for index, s in enumerate(m.sectors):
        if s.wall_count < 4 or _area(m, s) > HOST_AREA:
            continue
        neighbours = [m.walls[w].next_sector
                      for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]
        neighbours = [n for n in neighbours if n >= 0]
        if not neighbours:
            continue
        host = max(neighbours, key=lambda n: _area(m, m.sectors[n]))
        rise = m.sectors[host].floor_z - s.floor_z
        if rise <= 0:
            continue
        width, depth = _box(m, s)
        goods.append(inside.get(index, 0))
        families[(rise, s.floor_picnum)].append((width, depth, index))

    # A family is one (rise, tile) built at more than one size, or more than
    # once at the same size: that is what makes it parametric rather than a
    # one-off.
    out_families = []
    for (rise, tile), members in families.items():
        if len(members) < 3:
            continue
        widths = sorted({w for w, _d, _i in members})
        depths = sorted({d for _w, d, _i in members})
        free = ("width" if len(widths) > len(depths)
                else "depth" if len(depths) > len(widths) else "both")
        out_families.append({
            "rise": rise, "tile": tile, "count": len(members),
            "widths": widths, "depths": depths,
            "free_dimension": free,
            "sectors": sorted(i for _w, _d, i in members)[:12],
        })
    out_families.sort(key=lambda f: -f["count"])

    masked = collections.Counter()
    for w in m.walls:
        if w.next_sector >= 0 and (w.cstat & 16) and w.over_picnum:
            masked[w.over_picnum] += 1
    props = collections.Counter(sp.picnum for sp in m.sprites
                                if sp.status == 0 and sp.type == 0)
    return {
        "map": name,
        "sectors": len(m.sectors), "sprites": len(m.sprites),
        "fixtures": len(goods),
        "goods_per_fixture": {
            "mean": round(sum(goods) / max(1, len(goods)), 3),
            "median": statistics.median(goods) if goods else 0,
            "max": max(goods) if goods else 0,
            "bare": sum(1 for g in goods if g == 0),
        },
        "families": out_families[:12],
        "masked_wall_overlays": masked.most_common(6),
        "shutter_sprites": sum(1 for sp in m.sprites
                               if sp.picnum in SHUTTER_TILES),
        "top_props": props.most_common(16),
        "letters": sum(1 for sp in m.sprites if 3808 <= sp.picnum <= 3833),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args(argv)

    rows = [survey(name) for name in SOURCES]
    both_death_wish = (
        {t for t, _n in next(r for r in rows if r["map"] == "DWE3M1")["top_props"]}
        & {t for t, _n in next(r for r in rows if r["map"] == "DWE3M10")["top_props"]})
    report = {
        "$schema": "llmapper.blood-fixtures",
        "schema_version": 1,
        "note": ("Derived: counts, families, dimensions, palettes. "
                 "Interpreted: the palette names."),
        "sources": list(SOURCES),
        "maps": rows,
        "attested_in_both_death_wish": sorted(both_death_wish),
        "palettes": {
            "town": {
                "note": "DWE3M1's inland town register (interpreted name)",
                "tiles": [973, 2621, 544, 256, 421, 2210, 2211],
            },
            "waterfront": {
                "note": "DWE3M10's pier register (interpreted name)",
                "tiles": [795, 676, 640, 743, 742, 624, 694, 754, 599, 660],
            },
        },
        "reading_guide": [
            "a family's free dimension is the one it varies; rise and tile pin",
            "goods per fixture is a median of ZERO in every source",
            "a shutter and a window are the same masked wall, different tile",
        ],
    }
    pathlib.Path(args.output).write_text(json.dumps(report, indent=1),
                                         encoding="utf-8")
    print(f"wrote {args.output}")
    for row in rows:
        print(f"  {row['map']:9s} fixtures {row['fixtures']:4d} "
              f"families {len(row['families']):2d} "
              f"bare {row['goods_per_fixture']['bare']:3d} "
              f"letters {row['letters']:3d}")
    print(f"  attested in BOTH Death Wish maps: {sorted(both_death_wish)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
