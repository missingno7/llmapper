"""Does every sprite fit where it was put? As the engine DRAWS it.

The owner, walking Gravesend on 2026-11-18: "sometimes you are placing
sprites partially under ground or into space where they don't fit".

Nothing in the build could have said so. Sprites were seated by
`bloodmap.placement.sprite_extent`, which is Blood's PHYSICS box
(`GetSpriteExtents`, db.h): half above z and half below, whatever the cstat.
The renderer does not use it. `engine.cpp` `setup_globals_sprite1`::

    z2 = z - ((yoff * yrepeat) << 2);            // the bottom
    if (cstat & 128) z2 += (yspan * yrepeat) << 1;
    z1 = z2 - ((yspan * yrepeat) << 2);           // the top

So a sprite with bit 128 is drawn about its z, and one WITHOUT it stands on
its z. The two boxes agree only when bit 128 is set. `drawn_extent` is the
renderer's.

Per sprite, against the flat sector it is in:

``sunk``      how far its drawn bottom is under the floor
``through``   how far its drawn top is over a real (not parallax) ceiling
``squeezed``  a face sprite wider than the room it has: the nearest wall
              that would cut it (a solid wall, or a step it does not clear)
              is closer than a share of its half width
``overlap``   two wall sprites on one plane whose rectangles intersect

Every number is reported for the campaign's own maps too, by the same code:
Blood buries some sprites on purpose (a gravestone, a body), so a threshold
is where the campaign stops, not zero.

.. code-block:: bash

    python -m tools.sprite_fit projects/blood-city/level/blood-city-current.MAP
    python -m tools.sprite_fit --rates maps...      # one line per map
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BODY = 16960
#: share of the sprite's own height under the floor (or over the ceiling)
SUNK = 0.10
#: nearest cutting wall closer than this share of the half width
SQUEEZED = 0.5
#: a standing thing this far over the floor, in bodies, stands on nothing
LIFTED = 0.12

#: a face sprite this narrow, this close to a wall, is a wall bracket
MOUNTED_HALF = 128
MOUNTED_ROOM = 64

_ART = None


def art() -> dict:
    global _ART
    if _ART is None:
        from bloodmap.art import read_art_directory

        _ART = read_art_directory(str(ROOT / "reference" / "blood"))
    return _ART


from bloodmap.placement import drawn_extent, drawn_lift  # noqa: E402,F401


def _visible(f) -> bool:
    if int(f["cstat"]) & 0x8000 or int(f["picnum"]) <= 0:
        return False
    if int(f["x_repeat"]) == 0 or int(f["y_repeat"]) == 0:
        return False
    kind = int(f.get("type", 0))
    #: markers, actors (the engine seats them), sounds and generators
    return kind == 0 or 30 <= kind <= 199 or 400 <= kind <= 433


def _distance(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if not length2:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def audit(disk) -> list[dict[str, Any]]:
    """One row per visible sprite in a flat sector."""
    tiles = art()
    sectors = [s.fields for s in disk.sectors]
    walls = [w.fields for w in disk.walls]
    rows = []
    for index, sprite in enumerate(disk.sprites):
        f = sprite.fields
        sid = int(f["sector"])
        if not _visible(f) or not 0 <= sid < len(sectors):
            continue
        tile = tiles.get(int(f["picnum"]))
        if tile is None or not tile.height or not tile.width:
            continue
        s = sectors[sid]
        if int(s["floor_heinum"]) and int(s["floor_stat"]) & 2 \
                or int(s["ceiling_heinum"]) and int(s["ceiling_stat"]) & 2:
            continue
        cstat = int(f["cstat"])
        align = {0: "face", 16: "wall", 32: "floor"}.get(cstat & 48, "other")
        top, bottom = drawn_extent(tile.height, int(tile.animation["yofs"]),
                                   int(f["y_repeat"]), cstat, int(f["z"]))
        tall = max(1, bottom - top)
        floor, ceiling = int(s["floor_z"]), int(s["ceiling_z"])
        sky = bool(int(s["ceiling_stat"]) & 1)
        row = {"sprite": index, "tile": int(f["picnum"]), "sector": sid,
               "align": align, "type": int(f.get("type", 0)),
               "x": int(f["x"]), "y": int(f["y"]),
               "sunk": 0.0, "through": 0.0, "squeezed": None,
               "over_floor": round((floor - bottom) / BODY, 3)}
        if align != "floor":
            row["sunk"] = round(max(0, bottom - floor) / tall, 3)
            if not sky:
                row["through"] = round(max(0, ceiling - top) / tall, 3)
        else:
            row["sunk"] = 1.0 if int(f["z"]) > floor else 0.0
        if align == "face":
            half = tile.width * int(f["x_repeat"]) / 8.0
            nearest = None
            for w in range(int(s["wall_ptr"]),
                           int(s["wall_ptr"]) + int(s["wall_count"])):
                a = walls[w]
                b = walls[int(a["point2"])]
                other = int(a["next_sector"])
                if other >= 0:
                    o = sectors[other]
                    #: open over the whole sprite: nothing is cut
                    if int(o["floor_z"]) >= bottom - 256 and (
                            int(o["ceiling_stat"]) & 1
                            or int(o["ceiling_z"]) <= top + 256):
                        continue
                d = _distance(int(f["x"]), int(f["y"]), int(a["x"]),
                              int(a["y"]), int(b["x"]), int(b["y"]))
                nearest = d if nearest is None else min(nearest, d)
            if nearest is not None and half > 0:
                row["squeezed"] = round(nearest / half, 2)
                row["half_width"] = int(half)
                row["room"] = int(nearest)
        rows.append(row)
    return rows


#: two wall sprites on one plane cover each other when this share of the
#: smaller one is under the other
COVERED = 0.15
#: sprites this close in depth are on the same plane: there is no depth
#: buffer between them, and which one wins changes with the view
SAME_PLANE = 24.0


def overlaps(disk, *, covered: float = COVERED) -> list[dict[str, Any]]:
    """Pairs of wall sprites that cover each other on one wall.

    The owner, 2026-11-18: "On some walls you have overlapping sprites,
    usually letters with other sprites." A wall-aligned sprite is a rectangle
    on a plane; two on the same plane, facing the same way, whose rectangles
    intersect are drawn through each other.
    """
    tiles = art()
    rects = []
    for index, sprite in enumerate(disk.sprites):
        f = sprite.fields
        cstat = int(f["cstat"])
        if cstat & 0x8000 or cstat & 48 != 16 or int(f["picnum"]) <= 0:
            continue
        tile = tiles.get(int(f["picnum"]))
        if tile is None or not tile.width or not tile.height:
            continue
        angle = (int(f["angle"]) & 2047) * math.pi / 1024.0
        normal = (math.cos(angle), math.sin(angle))
        along = (-normal[1], normal[0])
        s = int(f["x"]) * along[0] + int(f["y"]) * along[1]
        depth = int(f["x"]) * normal[0] + int(f["y"]) * normal[1]
        half = tile.width * int(f["x_repeat"]) / 8.0
        top, bottom = drawn_extent(tile.height, int(tile.animation["yofs"]),
                                   int(f["y_repeat"]), cstat, int(f["z"]))
        if half <= 0 or bottom <= top:
            continue
        rects.append({"sprite": index, "tile": int(f["picnum"]),
                      "facing": (int(f["angle"]) & 2047),
                      "s": s, "depth": depth, "half": half, "top": top,
                      "bottom": bottom, "x": int(f["x"]), "y": int(f["y"]),
                      "sector": int(f["sector"])})
    out = []
    rects.sort(key=lambda r: (r["facing"], r["depth"]))
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            if b["facing"] != a["facing"] or b["depth"] - a["depth"] > SAME_PLANE:
                break
            wide = min(a["s"] + a["half"], b["s"] + b["half"])                 - max(a["s"] - a["half"], b["s"] - b["half"])
            tall = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
            if wide <= 0 or tall <= 0:
                continue
            smaller = min(2 * a["half"] * (a["bottom"] - a["top"]),
                          2 * b["half"] * (b["bottom"] - b["top"]))
            share = wide * tall / smaller
            if share > covered:
                out.append({"a": a["sprite"], "b": b["sprite"],
                            "tiles": (a["tile"], b["tile"]),
                            "covered": round(share, 2), "sector": a["sector"],
                            "x": a["x"], "y": a["y"]})
    return out


def faults(rows, *, sunk: float = SUNK, squeezed: float = SQUEEZED) -> dict:
    return {
        "sunk": [r for r in rows if r["sunk"] > sunk],
        "through": [r for r in rows if r["through"] > sunk],
        #: (a narrow thing hard against a wall is MOUNTED on it: a bracket)
        "squeezed": [r for r in rows if r["squeezed"] is not None
                     and r["squeezed"] < squeezed
                     and not (r.get("half_width", 0) <= MOUNTED_HALF
                              and r.get("room", 0) <= MOUNTED_ROOM)],
    }


def rates(rows) -> dict[str, float]:
    found = faults(rows)
    total = max(1, len(rows))
    face = max(1, sum(1 for r in rows if r["align"] == "face"))
    return {"sprites": len(rows),
            "sunk": round(len(found["sunk"]) / total, 3),
            "through": round(len(found["through"]) / total, 3),
            "squeezed": round(len(found["squeezed"]) / face, 3)}


def lint(disk) -> dict[str, Any]:
    """Everything, for a build to print and a test to hold."""
    rows = audit(disk)
    found = faults(rows)
    return {"rates": rates(rows), "overlaps": overlaps(disk),
            "sunk": found["sunk"], "through": found["through"],
            "squeezed": found["squeezed"]}


def main(argv=None) -> int:
    from bloodmap.format import read_map

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("maps", nargs="+")
    parser.add_argument("--rates", action="store_true")
    parser.add_argument("--json")
    args = parser.parse_args(argv)
    out = {}
    for text in args.maps:
        path = pathlib.Path(text)
        if not path.is_absolute() and not path.exists():
            path = ROOT / text
        disk = read_map(path)
        rows = audit(disk)
        covering = overlaps(disk)
        out[path.stem] = {"rates": rates(rows), "faults": faults(rows),
                          "overlaps": covering}
        print(path.stem, rates(rows), "overlapping wall sprite pairs:",
              len(covering))
        if args.rates:
            continue
        for pair in covering:
            print(f"  overlap   sprites {pair['a']} and {pair['b']} tiles "
                  f"{pair['tiles']} sector {pair['sector']} at "
                  f"({pair['x']}, {pair['y']}): {pair['covered']:.0%} of the "
                  "smaller is covered")
        for kind, found in faults(rows).items():
            for r in sorted(found, key=lambda r: (r["tile"], r["sprite"])):
                detail = (f"room {r.get('room')} for half width "
                          f"{r.get('half_width')}" if kind == "squeezed"
                          else f"{r[kind]:.0%} of its height")
                print(f"  {kind:9s} sprite {r['sprite']:4d} tile {r['tile']:5d} "
                      f"{r['align']:5s} type {r['type']:3d} sector "
                      f"{r['sector']:4d} at ({r['x']}, {r['y']}): {detail}")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(out, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
