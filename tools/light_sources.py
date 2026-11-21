"""How Blood's maps show things that give light: tiles drawn brighter than the room around them, as sprites or surfaces, and how the room is shaded around them.

The owner, 2026-11-20: "you are using torches almost everywhere ... you
should be using different types of light sources, check existing levels
what can be light source like fluorescent tubes ... Light source can be a
sector with texture". Blood shades by hand, but a mapper still marks what
gives light by drawing it bright. So a use of a tile is BRIGHT when:

* a surface (wall, floor, ceiling) is shaded at least `SELF_BRIGHT` below
  its own sector's floor -- the panel is lighter than the room;
* a sprite carries an own shade at or below `SPRITE_BRIGHT` (Blood ADDS the
  sector's shade to a sprite, `visual.sprite_shades_as_drawn`, so a lamp
  that stays bright carries a negative shade of its own).

Per tile it reports how often it is used, in how many maps, how it is used
(ceiling panel, wall, floor-aligned sprite on a ceiling, wall sprite...),
how often it is drawn bright, and what the sector it lights does: the floor
shade of sectors holding it against their neighbours.

.. code-block:: bash

    python -m tools.light_sources                  # the campaign's light tiles, ranked
    python -m tools.light_sources --tiles 501 795  # those tiles only
    python -m tools.light_sources --json knowledge/blood/light-sources.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: a surface this many shades lighter than its own sector's floor is drawn as a light
SELF_BRIGHT = 12
#: a sprite with an own shade at or below this stays bright wherever it is
SPRITE_BRIGHT = -16
#: a tile is a light when at least this share of its uses are bright
BRIGHT_SHARE = 0.5
MIN_USES, MIN_MAPS = 12, 3


def _use_of_sprite(f, sector) -> str:
    cstat = int(f["cstat"])
    align = cstat & 48
    if align == 32:
        on_ceiling = abs(int(f["z"]) - int(sector["ceiling_z"])) < abs(int(f["z"]) - int(sector["floor_z"]))
        return "flat sprite on a ceiling" if on_ceiling else "flat sprite on a floor"
    if align == 16:
        return "wall sprite"
    return "standing sprite"


def mine(paths) -> dict:
    from bloodmap.format import read_map
    from bloodmap.model import record_fields as F

    tiles: dict[int, dict] = defaultdict(lambda: {"uses": 0, "bright": 0, "maps": set(),
                                                  "as": Counter(), "bright_as": Counter(),
                                                  "shade": [], "room": []})
    rooms_lit, rooms_unlit = [], []
    panels: dict[int, list] = defaultdict(list)
    for path in paths:
        try:
            d = read_map(path)
        except Exception as exc:                          # a map that will not read is named, not fatal
            print(f"  ! {path}: {exc}", file=sys.stderr)
            continue
        name = pathlib.Path(path).stem
        sectors = [F(s) for s in d.sectors]
        owner = {}
        for i, s in enumerate(sectors):
            for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"])):
                owner[w] = i
        lit = set()

        def note(tile, use, bright, shade, room, sector):
            row = tiles[tile]
            row["uses"] += 1
            row["maps"].add(name)
            row["as"][use] += 1
            row["shade"].append(shade)
            row["room"].append(room)
            if bright:
                row["bright"] += 1
                row["bright_as"][use] += 1
                lit.add(sector)

        def neighbours(i):
            s = sectors[i]
            return [n for n in {int(F(d.walls[w])["next_sector"]) for w in
                                range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))} if n >= 0]

        for i, s in enumerate(sectors):
            room = int(s["floor_shade"])
            if not int(s["ceiling_stat"]) & 1:
                # a ceiling is a light when it is lighter than the ceilings around
                # it: a panel's own floor is lit too, so its floor is no measure
                c = int(s["ceiling_shade"])
                roofed = [sectors[n] for n in neighbours(i) if not int(sectors[n]["ceiling_stat"]) & 1]
                around = statistics.median(int(n["ceiling_shade"]) for n in roofed) if roofed else room
                bright = around - c >= SELF_BRIGHT
                note(int(s["ceiling_picnum"]), "ceiling panel", bright, c, room, i)
                if bright and roofed:
                    panels[int(s["ceiling_picnum"])].append({
                        "recess": statistics.median(int(n["ceiling_z"]) for n in roofed) - int(s["ceiling_z"]),
                        "pool": statistics.median(int(n["floor_shade"]) for n in roofed) - room,
                        "walls": int(s["wall_count"])})
            note(int(s["floor_picnum"]), "floor", False, room, room, i)
        for i, s in enumerate(sectors):
            # a wall is a light when it is lighter than the other walls of its room
            walls = range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))
            shades = sorted(int(F(d.walls[w])["shade"]) for w in walls)
            median = shades[len(shades) // 2]
            for w in walls:
                f = F(d.walls[w])
                note(int(f["picnum"]), "wall", median - int(f["shade"]) >= SELF_BRIGHT, int(f["shade"]),
                     int(s["floor_shade"]), i)
        for sprite in d.sprites:
            f = F(sprite)
            sec = int(f["sector"])
            if not 0 <= sec < len(sectors) or int(f["cstat"]) & 0x8000 or int(f["status"]) == 10:
                continue
            if int(f.get("type", 0)):
                continue                  # keys, pickups and enemies are drawn bright to be seen, not to give light
            use = _use_of_sprite(f, sectors[sec])
            note(int(f["picnum"]), use, int(f["shade"]) <= SPRITE_BRIGHT, int(f["shade"]),
                 int(sectors[sec]["floor_shade"]), sec)
        # what a lit sector's floor does against its unlit neighbours
        for i in lit:
            s = sectors[i]
            neighbours = {int(F(d.walls[w])["next_sector"]) for w in range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))}
            others = [int(sectors[n]["floor_shade"]) for n in neighbours if n >= 0 and n not in lit]
            if others:
                rooms_lit.append(int(s["floor_shade"]) - statistics.median(others))
    return {"tiles": tiles, "pool": rooms_lit, "panels": panels}


def ranked(found, wanted=None) -> list[dict]:
    from tools.catalog import tile_name

    out = []
    for tile, row in found["tiles"].items():
        if wanted is not None and tile not in wanted:
            continue
        share = row["bright"] / row["uses"] if row["uses"] else 0.0
        if wanted is None and (row["uses"] < MIN_USES or len(row["maps"]) < MIN_MAPS or share < BRIGHT_SHARE
                               or row["bright"] < MIN_USES):
            continue
        try:
            name = tile_name(tile) or ""
            if isinstance(name, tuple):
                name = " ".join(str(x) for x in name if x)
        except Exception:
            name = ""
        panel = found["panels"].get(tile, [])
        out.append({"tile": tile, "name": name, "uses": row["uses"], "maps": len(row["maps"]),
                    "panel": ({"n": len(panel), "recess": statistics.median(p["recess"] for p in panel),
                               "pool_under": statistics.median(p["pool"] for p in panel),
                               "walls": statistics.median(p["walls"] for p in panel)} if panel else None),
                    "bright_share": round(share, 2),
                    "bright_as": dict(row["bright_as"].most_common(4)),
                    "shade_median": statistics.median(row["shade"]),
                    "room_median": statistics.median(row["room"])})
    out.sort(key=lambda r: -r["uses"] * r["bright_share"])
    return out


def main(argv=None) -> int:
    from bloodmap.corpus import campaign_maps

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tiles", nargs="*", type=int)
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)
    found = mine(list(campaign_maps()))
    rows = ranked(found, set(args.tiles) if args.tiles else None)
    pool = found["pool"]
    print(f"{len(rows)} tiles the campaign draws as light (bright in {BRIGHT_SHARE:.0%}+ of {MIN_USES}+ uses, {MIN_MAPS}+ maps)")
    print(f"a sector holding a light: its floor against its unlit neighbours, median {statistics.median(pool):+.0f} "
          f"(p25 {statistics.quantiles(pool, n=4)[0]:+.0f}, p75 {statistics.quantiles(pool, n=4)[2]:+.0f}; negative is lighter)")
    for r in rows:
        print(f"  {r['tile']:5d} {r['name'][:34]:34s} uses {r['uses']:4d} in {r['maps']:2d} maps  bright {r['bright_share']:4.0%}"
              f"  shade {r['shade_median']:5.0f} in rooms at {r['room_median']:3.0f}  as {r['bright_as']}")
        if r["panel"]:
            pn = r["panel"]
            print(f"        as a ceiling panel ({pn['n']}): recessed {pn['recess']:.0f} z, {pn['walls']:.0f} walls, "
                  f"floor under it {pn['pool_under']:+.0f} lighter than around")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps({"tiles": rows, "pool": {
            "median": statistics.median(pool), "n": len(pool)}}, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
