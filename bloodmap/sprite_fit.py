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

    python -m tools.sprite_fit <MAP>                # every fault, a line each
    python -m tools.sprite_fit --rates maps...      # one line per map

A build holds its map to this with `lint(disk)` (`bloodmap.finish`).
"""

from __future__ import annotations

import json
import math
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent

from bloodmap.model import record_extra  # noqa: E402
from bloodmap.player_space import PLAYER_PROFILES  # noqa: E402

BODY = PLAYER_PROFILES["blood"].standing_height
#: share of the sprite's own height under the floor (or over the ceiling)
SUNK = 0.10
WADES = 0.6
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
        if floor == ceiling:
            # goods in a closet nobody has opened: fitted to it as it opens
            moves = record_extra(disk.sectors[sid]) or {}
            if moves.get("on_floor_z") or moves.get("off_floor_z"):
                floor = max(int(moves["on_floor_z"]), int(moves["off_floor_z"]))
                ceiling = min(int(moves["on_ceiling_z"]), int(moves["off_ceiling_z"]))
        sky = bool(int(s["ceiling_stat"]) & 1)
        row = {"sprite": index, "tile": int(f["picnum"]), "sector": sid,
               "align": align, "type": int(f.get("type", 0)),
               "x": int(f["x"]), "y": int(f["y"]),
               "sunk": 0.0, "through": 0.0, "squeezed": None,
               "over_floor": round((floor - bottom) / BODY, 3)}
        if align != "floor":
            row["sunk"] = round(max(0, bottom - floor) / tall, 3)
            # in a liquid that runs (its floor pans) a thing stands to the waist, as far as 0.6 of it, on purpose
            if row["sunk"] <= WADES and (record_extra(disk.sectors[sid]) or {}).get("pan_floor"):
                row["wades"], row["sunk"] = row["sunk"], 0.0
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


#: a plank (68) with nothing on it, and the alphabet
PLAIN_BOARDS, LETTERS = frozenset({68}), range(3808, 3834)


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
            #: written ON a plain board, and drawn in front of it: what a board is for
            if a["tile"] in PLAIN_BOARDS and b["tile"] in LETTERS and b["depth"] - a["depth"] >= 4:
                continue
            if share > covered:
                out.append({"a": a["sprite"], "b": b["sprite"],
                            "tiles": (a["tile"], b["tile"]),
                            "covered": round(share, 2), "sector": a["sector"],
                            "x": a["x"], "y": a["y"]})
    return out


def flat_overlaps(disk, *, covered: float = COVERED) -> list[dict[str, Any]]:
    """Pairs of floor- or ceiling-aligned sprites lying through each other.

    The owner, 2026-11-18: "I also noticed sprite overlapping on some
    floor/ceiling aligned sprites, for example in sewers." A flat sprite is
    a rectangle at its own z; two at one z in one sector whose rectangles
    intersect fight for the same pixels. Each rectangle is the engine's
    own (`bloodmap.flatsprite.footprint`): a flat sprite's width lies a
    quarter turn from its angle, and until 2026-11-19 this ignored
    rotation and took the smaller half extent for a square -- which is
    how a roof of twenty pieces, each lying across its neighbours' gaps
    and over the walls, was reported as no overlap at all.
    """
    from bloodmap import flatsprite

    tiles = art()
    flats = []
    for index, sprite in enumerate(disk.sprites):
        f = sprite.fields
        cstat = int(f["cstat"])
        if cstat & 0x8000 or cstat & 48 != 32 or int(f["picnum"]) <= 0:
            continue
        tile = tiles.get(int(f["picnum"]))
        if tile is None or not tile.width or not tile.height:
            continue
        if not int(f["x_repeat"]) or not int(f["y_repeat"]):
            continue
        x0, y0, x1, y1 = flatsprite.box(
            f, (tile.width, tile.height),
            (int(tile.animation["xofs"]), int(tile.animation["yofs"])))
        flats.append((int(f["z"]), index, int(f["picnum"]), int(f["x"]),
                      int(f["y"]), (x0, y0, x1, y1), int(f["sector"])))
    flats.sort()
    out = []
    for i, a in enumerate(flats):
        for b in flats[i + 1:]:
            if b[0] - a[0] > SAME_PLANE:
                break
            wide = min(a[5][2], b[5][2]) - max(a[5][0], b[5][0])
            deep = min(a[5][3], b[5][3]) - max(a[5][1], b[5][1])
            if wide <= 0 or deep <= 0:
                continue
            smaller = min((a[5][2] - a[5][0]) * (a[5][3] - a[5][1]),
                          (b[5][2] - b[5][0]) * (b[5][3] - b[5][1]))
            if smaller <= 0:
                continue
            share = wide * deep / float(smaller)
            if share > covered:
                out.append({"a": a[1], "b": b[1], "tiles": (a[2], b[2]),
                            "covered": round(share, 2), "sector": a[6],
                            "x": a[3], "y": a[4]})
    return out


#: how near a wall a hung thing must be, and how much of it the wall
#: must stand behind
MOUNT_REACH, BACKED = 96, 0.6


from bloodmap.tile_looks import USAGE, hung_tiles  # noqa: E402


def unbacked(disk, *, backed: float = BACKED) -> list[dict[str, Any]]:
    """Posters, notices and boards with no wall behind them. ADVICE, and
    only about things that are hung (`hung_tiles`): a free-standing wall
    sprite is not looked at.

    The owner, 2026-11-19, in the game: "there are places with posters
    which are hanging mid air." A wall sprite is placed against a line on
    the plan; nothing checked that the line is SOLID where the sprite
    hangs. A doorway cut through that line later, a window, the band of
    a step that stops below the picture -- and the poster hangs over a
    hole. For each wall sprite this finds the walls it lies against and
    measures how much of its drawn height they are solid behind, at its
    middle and towards both ends.
    """
    tiles = art()
    hung = hung_tiles()
    sectors = [s.fields for s in disk.sectors]
    walls = [w.fields for w in disk.walls]
    owner = {}
    for sector_id, s in enumerate(sectors):
        for w in range(int(s["wall_ptr"]),
                       int(s["wall_ptr"]) + int(s["wall_count"])):
            owner[w] = sector_id
    segments = []
    for wall_id, w in enumerate(walls):
        n = walls[int(w["point2"])]
        ax, ay, bx, by = int(w["x"]), int(w["y"]), int(n["x"]), int(n["y"])
        here = sectors[owner[wall_id]]
        bands = []
        other = int(w["next_sector"])
        if other < 0:
            bands.append((int(here["ceiling_z"]), int(here["floor_z"])))
        else:
            there = sectors[other]
            if int(there["ceiling_z"]) > int(here["ceiling_z"]):
                bands.append((int(here["ceiling_z"]),
                              int(there["ceiling_z"])))
            if int(there["floor_z"]) < int(here["floor_z"]):
                bands.append((int(there["floor_z"]), int(here["floor_z"])))
        segments.append((ax, ay, bx, by, bands))
    out = []
    for index, sprite in enumerate(disk.sprites):
        f = sprite.fields
        if not _visible(f) or int(f["cstat"]) & 48 != 16:
            continue
        tile = tiles.get(int(f["picnum"]))
        if tile is None or not tile.height or int(f["picnum"]) not in hung:
            continue
        top, bottom = drawn_extent(tile.height, int(tile.animation["yofs"]),
                                   int(f["y_repeat"]), int(f["cstat"]),
                                   int(f["z"]))
        if bottom <= top:
            continue
        half = tile.width * int(f["x_repeat"]) / 8.0
        turn = (int(f["angle"]) & 2047) * math.pi / 1024
        #: the sprite's own line runs across its facing
        ux, uy = -math.sin(turn), math.cos(turn)
        shares = []
        for along in (-0.7, 0.0, 0.7):
            px = int(f["x"]) + ux * half * along
            py = int(f["y"]) + uy * half * along
            best = 0.0
            for ax, ay, bx, by, bands in segments:
                if (min(ax, bx) - MOUNT_REACH > px or max(ax, bx) + MOUNT_REACH < px
                        or min(ay, by) - MOUNT_REACH > py
                        or max(ay, by) + MOUNT_REACH < py):
                    continue
                length = math.hypot(bx - ax, by - ay)
                if not length:
                    continue
                #: it must lie ALONG the sprite, not across its end
                if abs(((bx - ax) * ux + (by - ay) * uy) / length) < 0.7:
                    continue
                at = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / length ** 2
                if not 0.0 <= at <= 1.0:
                    continue
                if _distance(px, py, ax, ay, bx, by) > MOUNT_REACH:
                    continue
                solid = sum(max(0, min(bottom, low) - max(top, high))
                            for high, low in bands)
                best = max(best, solid / float(bottom - top))
            shares.append(best)
        share = sum(shares) / len(shares)
        if share < backed:
            out.append({"sprite": index, "tile": int(f["picnum"]),
                        "backed": round(share, 2), "sector": int(f["sector"]),
                        "x": int(f["x"]), "y": int(f["y"]), "z": int(f["z"])})
    return out


def on_travelling_floor(disk) -> list[dict[str, Any]]:
    """Decoration left on a floor that carries things away.

    The owner, 2026-11-18: "that pipe entrance decoration on the conveyor
    belt instead on the floor, sometimes we have details like this missed".
    A conveyor is a floor that pans AND drags (`pan_floor` with `drag`):
    a decal on it stays where it was written while the belt runs under it,
    and anything hung over it belongs to the room, not the belt. Water pans
    without dragging and is not counted: the campaign floats things on it.
    """
    out = []
    for index, sprite in enumerate(disk.sprites):
        f = sprite.fields
        if int(f.get("status", 0)) != 0 or int(f.get("type", 0)) != 0:
            continue
        if int(f["cstat"]) & 32768:
            continue
        sid = int(f["sector"])
        if not 0 <= sid < len(disk.sectors):
            continue
        extra = getattr(disk.sectors[sid], "extra", None)
        x = getattr(extra, "fields", None) or {}
        #: only what LIES ON the belt: the campaign hangs lights, grate
        #: decks and posters in its belt and train sectors (E3M5, E1M3),
        #: all of them on a wall or well over the floor
        if (int(f["cstat"]) & 48) == 16:
            continue
        if int(disk.sectors[sid].fields["floor_z"]) - int(f["z"]) > BODY // 4:
            continue
        if int(x.get("pan_floor", 0)) and int(x.get("drag", 0)):
            out.append({"sprite": index, "tile": int(f["picnum"]),
                        "sector": sid, "at": (int(f["x"]), int(f["y"]))})
    return out


def sunk_actors(disk, *, sunk: float = SUNK) -> list[dict[str, Any]]:
    """Actors written with their feet under the floor.

    The game stands a dude on the floor when it spawns, so nobody sees this
    in play (the owner: "enemies even when they are sinked game makes them
    normal, but yes they are sinked in the map"). The editor and every
    renderer that is not the game show the map as written, and the campaign
    writes them standing: all of E3M1's dudes have their drawn bottom on
    their floor.
    """
    tiles = art()
    out = []
    for index, sprite in enumerate(disk.sprites):
        f = sprite.fields
        if not 200 <= int(f.get("type", 0)) <= 260:
            continue
        sid = int(f["sector"])
        tile = tiles.get(int(f["picnum"]))
        if tile is None or not tile.height or not 0 <= sid < len(disk.sectors):
            continue
        s = disk.sectors[sid].fields
        if int(s["floor_heinum"]) and int(s["floor_stat"]) & 2:
            continue
        top, bottom = drawn_extent(tile.height, int(tile.animation["yofs"]),
                                   int(f["y_repeat"]), int(f["cstat"]),
                                   int(f["z"]))
        share = (bottom - int(s["floor_z"])) / max(1, bottom - top)
        if share > sunk:
            out.append({"sprite": index, "tile": int(f["picnum"]),
                        "type": int(f["type"]), "sector": sid,
                        "sunk": round(share, 2)})
    return out


def stood_on_floor() -> dict[int, float]:
    """Each tile's typical height over its floor as a standing (face) sprite
    across the campaign, in bodies (`knowledge/blood/design/tile-usage-v1.json`)."""
    data = json.loads(USAGE.read_text("utf-8"))["tiles"]
    out = {}
    for key, row in data.items():
        face = row.get("roles", {}).get("sprite_face")
        if face and face.get("over_floor_bodies") is not None:
            out[int(key)] = float(face["over_floor_bodies"])
    return out


def lifted(rows, *, lifted_by: float = LIFTED) -> list[dict[str, Any]]:
    """Standing things drawn in the air over their floor.

    The owner, 2026-11-20, of the memorial's statues: "Haven't you spot that
    these statues are floating mid air?" They were 0.83 bodies up: tile 536
    carries an art y-offset of half its height, made to be drawn CENTRED
    (cstat 128), and was written without the bit, so the renderer lifted it
    by that offset. Nothing reported it: `LIFTED` was declared and never
    used. A face sprite is lifted when its drawn bottom stands more than
    `lifted_by` bodies over its own sector's floor AND the campaign stands
    that tile on its floor (its typical height is under half of that) --
    lamps, torches, carcasses and smoke are in the air by nature and the
    campaign says so. Measured over the campaign: no key and no statue 536
    of 95 stands lifted.
    """
    typical = stood_on_floor()
    out = []
    for r in rows:
        if r["align"] != "face" or r["over_floor"] <= lifted_by:
            continue
        usual = typical.get(r["tile"])
        if usual is None or usual > lifted_by / 2:
            continue
        out.append({"sprite": r["sprite"], "tile": r["tile"], "sector": r["sector"],
                    "over_floor": r["over_floor"], "campaign": usual})
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
            "flat_overlaps": flat_overlaps(disk),
            "unbacked": unbacked(disk),
            "sunk_actors": sunk_actors(disk),
            "on_travelling_floor": on_travelling_floor(disk),
            "sunk": found["sunk"], "through": found["through"],
            "squeezed": found["squeezed"], "lifted": lifted(rows)}
