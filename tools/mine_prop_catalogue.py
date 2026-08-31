"""A measured catalogue of every prop the campaign uses more than rarely.

`props.py` began as a hand-copied table, which does not scale and goes
stale the moment a new tile is adopted.  This emits the same facts
mechanically: for each decoration tile, how it is ALIGNED (its cstat says
whether it is wall-aligned, floor-aligned, or a free face sprite), how high
above the floor its centre sits, how often it is found hard against a solid
wall, and the repeats and shade the campaign gives it.

The alignment bits are the ground truth for mounting:
  0x10 (16) wall-aligned  -> it lies flat ON a wall (a painting, a poster)
  0x20 (32) floor-aligned -> it lies flat on the floor (a decal, a grate)
  neither                 -> a free-standing face sprite, and then the
                             wall-hug fraction says whether it is meant to
                             stand against one (a brazier at 92%) or out in
                             the open (a tree at 5%).
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
from bloodmap.format import read_map
from bloodmap.patterns import CORPUS_VIEWS, list_corpus_maps

PLAYER = 16960


def seg_dist(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--view", default="reference",
                    choices=sorted(CORPUS_VIEWS),
                    help="corpus view to mine (default: reference)")
    ap.add_argument("--min-instances", type=int, default=12)
    args = ap.parse_args(argv)

    acc = collections.defaultdict(lambda: {
        "n": 0, "height": [], "dist": [], "cstat": collections.Counter(),
        "rep": collections.Counter(), "shade": [], "maps": set(),
        "sky": 0, "wet": 0})

    # This used to glob a flat maps/blood, which after the corpus became
    # provenance directories matched nothing at all. The population it
    # was really reading is the `reference` view -- campaign, BloodBath
    # and the curated community sets -- and that is what the committed
    # knowledge file was mined from, so it stays the default rather than
    # silently moving numbers nobody asked to move. Note that the prose
    # above says "the campaign" and the evidence is wider than that;
    # `--view original` is the honest campaign-only run.
    for path in sorted(str(item.path) for item in
                       list_corpus_maps(view=args.view)):
        name = pathlib.Path(path).stem
        try:
            m = read_map(path)
        except Exception:
            continue
        for sp in m.sprites:
            if sp.status != 0 or sp.type != 0 or sp.picnum <= 0:
                continue
            sec = m.sectors[sp.sector]
            a = acc[sp.picnum]
            a["n"] += 1
            a["maps"].add(name)
            a["height"].append((sec.floor_z - sp.z) / PLAYER)
            a["cstat"][sp.cstat] += 1
            a["rep"][(sp.x_repeat, sp.y_repeat)] += 1
            a["shade"].append(sp.shade)
            if sec.ceiling_stat & 1:
                a["sky"] += 1
            best = 1e18
            for w in range(sec.wall_ptr, sec.wall_ptr + sec.wall_count):
                wl = m.walls[w]
                if wl.next_sector >= 0:
                    continue
                nx = m.walls[wl.point2]
                best = min(best, seg_dist(sp.x, sp.y, wl.x, wl.y, nx.x, nx.y))
            if best < 1e17:
                a["dist"].append(best)

    catalogue = {}
    for tile, a in acc.items():
        if a["n"] < args.min_instances:
            continue
        cstat = a["cstat"].most_common(1)[0][0]
        rep = a["rep"].most_common(1)[0][0]
        hug = (sum(1 for d in a["dist"] if d <= 512) / len(a["dist"])
               if a["dist"] else 0.0)
        height = statistics.median(a["height"])
        if cstat & 0x20:
            kind = "decal"
        elif cstat & 0x10:
            kind = "wall_aligned"
        elif hug >= 0.70 and height >= 0.40:
            kind = "bracket"
        else:
            kind = "floor"
        catalogue[str(tile)] = {
            "kind": kind,
            "height": round(height, 2),
            "wall_hug": round(hug, 2),
            "cstat": cstat,
            "x_repeat": rep[0], "y_repeat": rep[1],
            "shade": collections.Counter(a["shade"]).most_common(1)[0][0],
            "n": a["n"], "maps": len(a["maps"]),
            "sky_share": round(a["sky"] / a["n"], 2),
        }
    # The document is the tile map, so the population goes beside it under
    # a reserved non-numeric key: every real key here is a picnum, and a
    # reader that walks digits is unaffected.
    document = {"population": {"view": args.view,
                               "populations": list(CORPUS_VIEWS[args.view])},
                **catalogue}
    pathlib.Path(args.output).write_text(
        json.dumps(document, indent=1, sort_keys=True), encoding="utf-8")
    kinds = collections.Counter(v["kind"] for v in catalogue.values())
    print(f"wrote {args.output}: {len(catalogue)} props, {dict(kinds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
