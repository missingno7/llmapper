"""What goes with what: the JOINT distribution of surfaces and props.

Every earlier pass in this project mined marginals -- how high tile 506
sits, which facade tile is commonest.  Marginals cannot tell you that a
brazier belongs in a stone hall and a crate belongs in a warehouse, so
surfaces were chosen by role and props by a ceiling-tile lookup, and the
two never met.  This mines the joint distribution instead:

* which (wall, floor, ceiling) triples actually recur -- a room STYLE;
* which props associate with each style far above chance (PMI with a
  support floor), which is what a prop MEANS;
* which props co-occur with each other, so a room can be dressed as a set
  rather than as independent draws from a palette.

Usage:  python tools/mine_style_combinations.py [-o out.json]
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bloodmap.format import read_map
from bloodmap.patterns import CORPUS_VIEWS, list_corpus_maps

PLAYER = 16960
#: Sprites that are furniture/props rather than actors, pickups or markers.
def is_prop(sp) -> bool:
    return sp.status == 0 and sp.type == 0 and sp.picnum > 0


def _area(m, sector) -> float:
    """Shoelace over the sector's first loop -- enough to reject fragments."""
    pts = [(m.walls[w].x, m.walls[w].y)
           for w in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)]
    total = 0.0
    for i, (ax, ay) in enumerate(pts):
        bx, by = pts[(i + 1) % len(pts)]
        total += ax * by - bx * ay
    return abs(total) / 2


def dominant_wall(m, sector) -> int:
    """The tile the room is mostly MADE of, weighted by wall length."""
    by_len = collections.Counter()
    for w in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count):
        wl = m.walls[w]
        nxt = m.walls[wl.point2]
        length = int(((wl.x - nxt.x) ** 2 + (wl.y - nxt.y) ** 2) ** 0.5)
        by_len[wl.picnum] += length
    return by_len.most_common(1)[0][0] if by_len else 0


def height_band(units: int) -> str:
    h = units / PLAYER
    if h <= 0: return "flat"
    if h < 1.2: return "crawl"
    if h < 2.2: return "room"
    if h < 4.0: return "hall"
    return "vault"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--view", default="reference",
                    choices=sorted(CORPUS_VIEWS),
                    help="corpus view to mine (default: reference)")
    ap.add_argument("--support", type=int, default=6,
                    help="minimum co-occurrences before an association counts")
    args = ap.parse_args(argv)

    style_count = collections.Counter()          # (wall, floor, ceil) -> n
    style_props = collections.defaultdict(collections.Counter)
    style_height = collections.defaultdict(collections.Counter)
    style_maps = collections.defaultdict(set)
    prop_count = collections.Counter()
    prop_pairs = collections.Counter()
    surface_prop = collections.Counter()         # (surface_key, prop) -> n
    surface_count = collections.Counter()
    total_rooms = 0

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
        in_sector = collections.defaultdict(set)
        for sp in m.sprites:
            if is_prop(sp):
                in_sector[sp.sector].add(sp.picnum)
        for index, sector in enumerate(m.sectors):
            if sector.wall_count < 3:
                continue
            # A ROOM, not a fragment.  The unfiltered pass was dominated by
            # monochrome sectors -- 449/449/449, 379/379/379, 20/20/20 --
            # which are doors, steps and lift shafts inheriting one
            # material from their neighbour.  They are most of the sector
            # count and none of the style.
            if sector.type in (600, 602, 604, 614, 616, 618):
                continue
            clear = sector.floor_z - sector.ceiling_z
            if clear < 1.2 * PLAYER:
                continue
            if _area(m, sector) < 1_000_000:   # ~1 plan unit square, a small room
                continue
            wall = dominant_wall(m, sector)
            style = (wall, sector.floor_picnum, sector.ceiling_picnum)
            props = in_sector.get(index, set())
            total_rooms += 1
            style_count[style] += 1
            style_maps[style].add(name)
            style_height[style][height_band(sector.floor_z - sector.ceiling_z)] += 1
            for surface_key in (f"wall:{wall}", f"floor:{sector.floor_picnum}",
                                f"ceiling:{sector.ceiling_picnum}"):
                surface_count[surface_key] += 1
                for p in props:
                    surface_prop[(surface_key, p)] += 1
            for p in props:
                prop_count[p] += 1
                style_props[style][p] += 1
            ordered = sorted(props)
            for i, a in enumerate(ordered):
                for b in ordered[i + 1:]:
                    prop_pairs[(a, b)] += 1

    # --- prop -> surface association, by PMI over a support floor --------
    associations = collections.defaultdict(list)
    for (surface_key, prop), n in surface_prop.items():
        if n < args.support:
            continue
        p_joint = n / total_rooms
        p_surface = surface_count[surface_key] / total_rooms
        p_prop = prop_count[prop] / total_rooms
        if p_surface <= 0 or p_prop <= 0:
            continue
        pmi = math.log(p_joint / (p_surface * p_prop), 2)
        associations[prop].append({"surface": surface_key, "n": n,
                                   "pmi": round(pmi, 2)})
    for prop in associations:
        associations[prop].sort(key=lambda r: -r["pmi"])

    styles = []
    for style, n in style_count.most_common(40):
        wall, floor, ceiling = style
        props = style_props[style]
        styles.append({
            "wall": wall, "floor": floor, "ceiling": ceiling,
            "rooms": n, "maps": sorted(style_maps[style]),
            "height": style_height[style].most_common(2),
            "props": props.most_common(8),
        })

    report = {
        "rooms_examined": total_rooms,
        "distinct_styles": len(style_count),
        "styles": styles,
        "prop_associations": {str(k): v[:6] for k, v in associations.items()},
        "prop_pairs": [{"a": a, "b": b, "n": n}
                       for (a, b), n in prop_pairs.most_common(40)],
    }
    text = json.dumps(report, indent=2)
    if args.output:
        pathlib.Path(args.output).write_text(text, encoding="utf-8")
        print("wrote", args.output)
    print(f"{total_rooms} rooms, {len(style_count)} distinct (wall,floor,ceiling) styles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
