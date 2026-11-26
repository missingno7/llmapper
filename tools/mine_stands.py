"""What the goods in Blood's town maps stand ON.

A blind reviewer of Gravesend, 2026-11-18: "Shops have no fixtures ...
shelves and racks with stock on them", and "the goods are tiny lumps
scattered on the floor rather than on shelves."

`tools/mine_city_assets.py` says which things Blood's towns are dressed
with. This asks the next question of the same maps: for every small thing
that stands indoors, what is under it? The answer is read off the sector the
sprite is in and off that sector's neighbours, so it is a measurement of
geometry and not a reading of a picture:

``floor``    the sector is level with the lowest floor it touches
``island``   it stands above that floor and every side is open
             (a counter, a table, a crate)
``ledge``    it stands above that floor against a solid wall, and its
             ceiling is its neighbours' (a back bar, a shelf run)
``niche``    as a ledge, with its own lowered head (a shelf let into a wall)
``floating`` the sprite's FOOT is well above the floor of its sector: it
             hangs, or stands on a shelf that is only a picture

.. code-block:: bash

    python -m tools.mine_stands                 # the town maps
    python -m tools.mine_stands --json out.json maps...
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import statistics
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.mine_city_assets import TOWN_MAPS, is_decoration, map_path  # noqa: E402
from bloodmap.player_space import PLAYER_PROFILES

BODY = PLAYER_PROFILES["blood"].standing_height
#: a player's width, the unit plan sizes are stated in
WIDTH = 1024
#: a sprite this far over its sector's floor is not standing on it
FLOATING = 0.35
LEVEL = 0.03
CLASSES = ("floor", "island", "ledge", "niche", "floating")


def _loop(disk, sector) -> list[int]:
    start = int(sector["wall_ptr"])
    return list(range(start, start + int(sector["wall_count"])))


def describe(disk, index: int) -> dict[str, Any]:
    """One sector as a thing something could stand on."""
    sectors = disk.sectors
    walls = disk.walls
    s = sectors[index].fields
    area2 = 0.0
    solid = perimeter = 0.0
    floors, ceilings = [], []
    solid_tiles: collections.Counter = collections.Counter()
    face_tiles: collections.Counter = collections.Counter()
    xs, ys = [], []
    for w in _loop(disk, s):
        a = walls[w].fields
        b = walls[int(a["point2"])].fields
        length = math.hypot(int(b["x"]) - int(a["x"]), int(b["y"]) - int(a["y"]))
        area2 += int(a["x"]) * int(b["y"]) - int(b["x"]) * int(a["y"])
        perimeter += length
        xs.append(int(a["x"]))
        ys.append(int(a["y"]))
        other = int(a["next_sector"])
        if other < 0:
            solid += length
            solid_tiles[int(a["picnum"])] += length
            continue
        o = sectors[other].fields
        floors.append(int(o["floor_z"]))
        ceilings.append(int(o["ceiling_z"]))
        if int(o["floor_z"]) > int(s["floor_z"]) and int(a["next_wall"]) >= 0:
            #: the riser is drawn from the lower side's record
            face_tiles[int(walls[int(a["next_wall"])].fields["picnum"])] += length
    rise = (max(floors) - int(s["floor_z"])) / BODY if floors else 0.0
    drop = (int(s["ceiling_z"]) - min(ceilings)) / BODY if ceilings else 0.0
    share = solid / perimeter if perimeter else 0.0
    if rise < LEVEL:
        kind = "floor"
    elif share < 0.1:
        kind = "island"
    elif drop > 0.05:
        kind = "niche"
    else:
        kind = "ledge"
    box = sorted((max(xs) - min(xs), max(ys) - min(ys))) if xs else [0, 0]
    return {
        "kind": kind, "rise": round(rise, 3), "drop": round(drop, 3),
        "solid_share": round(share, 2),
        "clear": round((int(s["floor_z"]) - int(s["ceiling_z"])) / BODY, 3),
        "area": round(abs(area2) / 2 / WIDTH / WIDTH, 2),
        "short": round(box[0] / WIDTH, 2), "long": round(box[1] / WIDTH, 2),
        "top_tile": int(s["floor_picnum"]),
        "face_tile": face_tiles.most_common(1)[0][0] if face_tiles else None,
        "back_tile": solid_tiles.most_common(1)[0][0] if solid_tiles else None,
    }


def is_goods(fields) -> bool:
    """A small thing that stands: face-aligned decoration, indoors or out."""
    return is_decoration(fields) and int(fields["cstat"]) & 48 == 0


def stands(paths) -> list[dict[str, Any]]:
    """One row per standing thing: what it is and what is under it."""
    from bloodmap import art
    from bloodmap.format import read_map
    from bloodmap.placement import sprite_extent

    tiles = art.read_art_directory(str(ROOT / "reference" / "blood"))
    rows = []
    for text in paths:
        path = map_path(str(text))
        disk = read_map(path)
        seen: dict[int, dict] = {}
        for sprite in disk.sprites:
            f = sprite.fields
            index = int(f["sector"])
            if not is_goods(f) or not 0 <= index < len(disk.sectors):
                continue
            sector = disk.sectors[index].fields
            if int(sector["ceiling_stat"]) & 1:
                continue                                  # outdoors
            under = seen.setdefault(index, describe(disk, index))
            size = tiles.get(int(f["picnum"]))
            below = 0
            if size is not None and size.height:
                #: a sprite's z is not its foot: the foot is this far below
                below = sprite_extent(size.height, int(f["y_repeat"]),
                                      int(f["cstat"]),
                                      y_offset=int(size.animation["yofs"]))[1]
            over = (int(sector["floor_z"]) - int(f["z"]) - below) / BODY
            row = dict(under, map=path.stem, sector=index,
                       tile=int(f["picnum"]), over=round(over, 3))
            if over > FLOATING:
                row["kind"] = "floating"
            rows.append(row)
    return rows


def summary(rows) -> dict[str, Any]:
    """Per class: how many things, on how many fixtures, of what size."""
    out: dict[str, Any] = {}
    for kind in CLASSES:
        mine = [r for r in rows if r["kind"] == kind]
        fixtures = {(r["map"], r["sector"]): r for r in mine}
        entry: dict[str, Any] = {"things": len(mine), "fixtures": len(fixtures)}
        if fixtures and kind in ("island", "ledge", "niche"):
            pieces = list(fixtures.values())
            for key in ("rise", "drop", "clear", "short", "long"):
                entry[key] = round(statistics.median(p[key] for p in pieces), 2)
            for key in ("top_tile", "face_tile", "back_tile"):
                entry[key] = collections.Counter(
                    p[key] for p in pieces if p[key] is not None).most_common(4)
            per = collections.Counter((r["map"], r["sector"]) for r in mine)
            entry["things_per_fixture"] = round(statistics.median(per.values()), 1)
        out[kind] = entry
    return out


def table(by_map: dict[str, dict]) -> str:
    lines = ["| map | things | " + " | ".join(CLASSES) + " |",
             "|---|---|" + "---|" * len(CLASSES)]
    for name, found in by_map.items():
        total = sum(found[k]["things"] for k in CLASSES)
        cells = [f"{found[k]['things']} ({found[k]['things'] / total:.0%})"
                 if total else "0" for k in CLASSES]
        lines.append(f"| {name} | {total} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("maps", nargs="*", default=list(TOWN_MAPS))
    parser.add_argument("--json")
    args = parser.parse_args(argv)
    rows = stands(args.maps)
    by_map = {}
    for name in dict.fromkeys(r["map"] for r in rows):
        by_map[name] = summary([r for r in rows if r["map"] == name])
    print(table(by_map))
    whole = summary(rows)
    for kind in ("island", "ledge", "niche"):
        print(kind, json.dumps(whole[kind]))
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"maps": list(args.maps), "by_map": by_map, "all": whole,
             "rows": rows}, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
