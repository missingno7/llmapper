"""Monuments: what Blood stands in the open, and how it is stacked.

Gravesend's plaza carves a hole for a monument and the hole stays a hole.
Before building one, two questions the campaign can answer and guesswork
cannot:

* **How is a stepped base built?** How many tiers, what each one rises, and
  how the top tier relates to what stands on it.
* **How is a figure stood?** A sprite, a sector mass, or both.

A *monument* here is detected, not listed: a chain of raised sectors under
an open sky, each tier's footprint strictly inside the one below it. That
catches a stepped base and rejects a staircase (which does not nest), a
building (which is not raised out of its host) and a counter (which is
indoors).

Statuary is whatever stands ON the innermost tier -- the same test
`mine_surface_items` uses, at the top tier's floor.

Derived: every count, footprint, rise and tile. Interpreted: nothing.

    python tools/mine_monuments.py -o knowledge/blood/design/monuments-v1.json
"""

from __future__ import annotations

import argparse
import collections
from glob import glob
import json
import os
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bloodmap.format import read_map
from bloodmap.patterns import CORPUS_VIEWS, list_corpus_maps

PLAYER = 16960
PLAN = 1024
#: A tier is smaller than this; above it the thing is a building.
TIER_AREA = 9_000_000
#: An outdoor host is at least this big and wears a parallax ceiling.
HOST_AREA = 4_000_000
PARALLAX = 1
ALIGN_MASK = 0x30
ALIGN_FLOOR = 0x20


def _loop(m, s):
    return [(m.walls[w].x, m.walls[w].y)
            for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]


def _area(points) -> float:
    total = 0.0
    for index, (ax, ay) in enumerate(points):
        bx, by = points[(index + 1) % len(points)]
        total += ax * by - bx * ay
    return abs(total) / 2


def _box(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _inside(outer, inner) -> bool:
    """Is `inner`'s box strictly inside `outer`'s, and smaller?"""
    ax0, ay0, ax1, ay1 = outer
    bx0, by0, bx1, by1 = inner
    return (ax0 <= bx0 and ay0 <= by0 and bx1 <= ax1 and by1 <= ay1
            and (bx1 - bx0) * (by1 - by0) < (ax1 - ax0) * (ay1 - ay0))


def _contains_point(points, x, y) -> bool:
    hit = False
    count = len(points)
    for index in range(count):
        ax, ay = points[index]
        bx, by = points[(index + 1) % count]
        if (ay > y) != (by > y):
            if ax + (y - ay) * (bx - ax) / (by - ay) > x:
                hit = not hit
    return hit


def survey(path) -> dict:
    m = read_map(path)
    name = pathlib.Path(path).stem
    loops = [_loop(m, s) for s in m.sectors]
    areas = [_area(p) if p else 0.0 for p in loops]
    boxes = [_box(p) if p else (0, 0, 0, 0) for p in loops]

    outdoor = {i for i, s in enumerate(m.sectors)
               if (s.ceiling_stat & PARALLAX) and areas[i] >= HOST_AREA}
    if not outdoor:
        return {"map": name, "monuments": []}

    # A tier: small, raised, and touching the open air (directly or through
    # another tier).
    tiers = []
    for index, s in enumerate(m.sectors):
        if s.wall_count < 3 or areas[index] > TIER_AREA or index in outdoor:
            continue
        neighbours = [m.walls[w].next_sector
                      for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]
        neighbours = [n for n in neighbours if n >= 0]
        if not neighbours:
            continue
        host = max(neighbours, key=lambda n: areas[n])
        if m.sectors[host].floor_z - s.floor_z <= 0:
            continue                       # not raised
        if not (host in outdoor or areas[host] <= TIER_AREA):
            continue
        tiers.append(index)

    # Chains: each tier strictly inside the one below it.
    inside_of = collections.defaultdict(list)
    for a in tiers:
        for b in tiers:
            if a != b and _inside(boxes[a], boxes[b]):
                inside_of[a].append(b)

    chains = []
    used = set()
    for base in sorted(tiers, key=lambda i: -areas[i]):
        if base in used or not inside_of.get(base):
            continue
        chain = [base]
        current = base
        while inside_of.get(current):
            nxt = max((c for c in inside_of[current] if c not in chain),
                      key=lambda i: areas[i], default=None)
            if nxt is None:
                break
            chain.append(nxt)
            current = nxt
        if len(chain) < 2:
            continue
        used.update(chain)
        chains.append(chain)

    # Anything standing on the innermost tier.
    by_sector = collections.defaultdict(list)
    for sprite in m.sprites:
        by_sector[sprite.sector].append(sprite)

    out = []
    for chain in chains:
        base = chain[0]
        top = chain[-1]
        x0, y0, x1, y1 = boxes[base]
        rises = []
        previous_floor = m.sectors[
            max((m.walls[w].next_sector
                 for w in range(m.sectors[base].wall_ptr,
                                m.sectors[base].wall_ptr
                                + m.sectors[base].wall_count)
                 if m.walls[w].next_sector >= 0),
                key=lambda n: areas[n])].floor_z
        for tier in chain:
            rises.append(previous_floor - m.sectors[tier].floor_z)
            previous_floor = m.sectors[tier].floor_z
        statuary = []
        for sprite in by_sector.get(top, ()):
            if sprite.status != 0:
                continue
            above = m.sectors[top].floor_z - sprite.z
            if -512 <= above <= 3 * PLAYER:
                statuary.append({
                    "picnum": int(sprite.picnum), "type": int(sprite.type),
                    "cstat": int(sprite.cstat),
                    "align": ("floor" if sprite.cstat & ALIGN_MASK == ALIGN_FLOOR
                              else "wall" if sprite.cstat & ALIGN_MASK == 0x10
                              else "face"),
                    "height_player_heights": round(above / PLAYER, 2),
                    "x_repeat": int(sprite.x_repeat),
                    "y_repeat": int(sprite.y_repeat),
                })
        out.append({
            "map": name,
            "sectors": chain,
            "tiers": len(chain),
            "base_plan": [round((x1 - x0) / PLAN, 2), round((y1 - y0) / PLAN, 2)],
            "top_plan": [round((boxes[top][2] - boxes[top][0]) / PLAN, 2),
                         round((boxes[top][3] - boxes[top][1]) / PLAN, 2)],
            "rises": rises,
            "rises_player_heights": [round(r / PLAYER, 2) for r in rises],
            "total_rise_player_heights": round(sum(rises) / PLAYER, 2),
            "tiles": [int(m.sectors[t].floor_picnum) for t in chain],
            "wall_tiles": [int(m.walls[m.sectors[t].wall_ptr].picnum)
                           for t in chain],
            "statuary": statuary,
        })
    return {"map": name, "monuments": out}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--output")
    parser.add_argument("--maps", default=None,
                        help="explicit glob of maps; overrides --view")
    parser.add_argument("--view", default="reference",
                        choices=sorted(CORPUS_VIEWS),
                        help="corpus view to mine (default: reference)")
    args = parser.parse_args(argv)

    found = []
    # Default to the view the flat glob was really reading -- campaign,
    # BloodBath and the curated sets -- rather than a directory the corpus
    # no longer has. `--view original` is the campaign-only run.
    paths = (sorted(glob(args.maps)) if args.maps else
             sorted(str(item.path) for item in
                    list_corpus_maps(view=args.view)))
    for path in paths:
        try:
            found += survey(path)["monuments"]
        except Exception:
            continue

    tiers = collections.Counter(row["tiers"] for row in found)
    rises = [r for row in found for r in row["rises_player_heights"] if r > 0]
    bases = [max(row["base_plan"]) for row in found]
    tops = [max(row["top_plan"]) for row in found]
    statues = collections.Counter(
        item["picnum"] for row in found for item in row["statuary"])
    aligns = collections.Counter(
        item["align"] for row in found for item in row["statuary"])
    with_statue = sum(1 for row in found if row["statuary"])

    def spread(values):
        values = sorted(values)
        if not values:
            return {"n": 0}
        return {"n": len(values), "median": round(statistics.median(values), 3),
                "q1": values[len(values) // 4],
                "q3": values[3 * len(values) // 4],
                "min": values[0], "max": values[-1]}

    report = {
        "$schema": "llmapper.blood-monuments",
        # What was actually measured. These files described themselves as
        # campaign evidence while being mined over campaign plus curated
        # community maps, and nothing in them said so. Stating the view
        # makes the population a fact of the artifact rather than of
        # whichever directory happened to be on disk.
        "population": {"view": args.view,
                       "populations": list(CORPUS_VIEWS[args.view])},
        "schema_version": 1,
        "note": ("Derived: every tier, rise, footprint and tile. A monument "
                 "is a chain of raised sectors under open sky, each tier's "
                 "footprint strictly inside the one below."),
        "monuments": len(found),
        "maps_with_one": len({row["map"] for row in found}),
        "tier_counts": dict(sorted(tiers.items())),
        "tier_rise_player_heights": spread(rises),
        "base_plan_units": spread(bases),
        "top_plan_units": spread(tops),
        "carrying_statuary": with_statue,
        "statuary_alignment": dict(aligns),
        "statuary_tiles": statues.most_common(16),
        "examples": sorted(found, key=lambda r: -r["tiers"])[:14],
    }
    if args.output:
        pathlib.Path(args.output).write_text(json.dumps(report, indent=1),
                                             encoding="utf-8")
        print(f"wrote {args.output}")
    print(f"  {len(found)} monuments in {report['maps_with_one']} maps; "
          f"tiers {report['tier_counts']}")
    print(f"  tier rise (player heights): {report['tier_rise_player_heights']}")
    print(f"  base plan units: {report['base_plan_units']}")
    print(f"  top  plan units: {report['top_plan_units']}")
    print(f"  {with_statue} carry statuary; alignment {dict(aligns)}")
    print(f"  statuary tiles: {statues.most_common(10)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
