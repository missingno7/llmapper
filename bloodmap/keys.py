"""Telling the player which key a door wants.

A keyed door in Blood keeps its requirement in the XSECTOR's ``key`` field --
which the engine reads and the player cannot. What the player reads is a
*placard*: a 58x58 emblem in a spiked iron frame, hung beside the door, one
tile per key.

The six emblems and what they are, from rendering them rather than recalling
them: 2540 a skull, 2541 an eye, 2542 a flame, 2543 a dagger, 2544 a spider,
2545 a crescent moon. They share a frame and nothing else, and the difference is
the entire message.

What the campaign does
----------------------

``knowledge/blood/design/keys-v1.json``, all 43 maps: 200 placards against 265
keyed sectors, sprites and walls, with **80.4% of keyed things carrying a
placard within 3072 units**. The key-to-emblem mapping below is not a table
anybody remembered -- it is derived by pairing each placard with the nearest
keyed thing, and it comes out near-unanimous::

    key 1  skull   67 votes to 2
    key 2  eye     26 to 1
    key 3  flame   27 to 1
    key 4  dagger  20, unanimous
    key 5  spider  10, unanimous
    key 6  moon    26, unanimous

Hung a median **0.845 standing humans** above the floor (q1 0.785, q3 0.966),
at ``x_repeat == y_repeat == 32`` in 149 of 200 cases, palette 0 in all 200.
Two cstats account for every one: 464 and 208, which differ only in whether the
placard stops a hitscan -- both are wall-aligned, one-sided and centred.

Why this module exists rather than a tile constant
--------------------------------------------------

The level these emblems came out of had used them as ordinary wall furniture --
a key symbol on the chapter house, the reliquary, the ossuary and every
"emblem" in the map -- so it signposted eight keyed doors while holding one key.
The fix at the time was to delete all six tiles, which stopped the lying and
left the one genuinely keyed door with nothing on it at all.

So a placard here is not something you can hang. It is something a *keyed door*
gets, derived from the key it actually demands, and `check` refuses a level
whose placards and locks disagree.
"""

from __future__ import annotations

import math
from typing import Any

from .player_space import PLAYER_PROFILES

PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

#: key value -> emblem tile, derived from co-location across the campaign.
KEY_EMBLEM = {1: 2540, 2: 2541, 3: 2542, 4: 2543, 5: 2544, 6: 2545}

#: What each emblem is, for error messages a person can act on.
EMBLEM_NAME = {2540: "skull", 2541: "eye", 2542: "flame",
               2543: "dagger", 2544: "spider", 2545: "moon"}

#: The key *item* the player picks up, by key value. Blood's pickup types run
#: from kItemKey1 at 100.
KEY_ITEM_TYPE = {key: 99 + key for key in KEY_EMBLEM}

#: The tile a key PICKUP wears where it lies in the world, which is not the
#: placard emblem and not a free choice. Mined over the 43 campaign maps: 95
#: key pickups, six item types, and every single one wears `2452 + type` --
#: no map ever dresses a key as another key. So the world art is DERIVED from
#: the item type rather than passed in beside it, which is how the zoo came
#: to grant the moon key (type 105) while showing the skull key's tile
#: (2552): the lock opened, and the thing on the floor was the wrong key.
WORLD_TILE_BASE = 2452
WORLD_TILE = {key: WORLD_TILE_BASE + kind
              for key, kind in KEY_ITEM_TYPE.items()}


def world_picnum(key: int) -> int:
    """The tile the pickup for `key` wears on the floor."""
    if key not in WORLD_TILE:
        raise KeyError(f"key {key} is not one of {sorted(WORLD_TILE)}")
    return WORLD_TILE[key]


def pickup(key: int, **overrides: int) -> dict[str, int]:
    """The full sprite record for a key lying in the world.

    Type and picnum are derived together from the key, so they cannot drift
    apart. A caller that wants different art has to say so explicitly, and a
    reader can then tell intent from accident.
    """
    record = {"type": KEY_ITEM_TYPE[key], "picnum": world_picnum(key),
              "x_repeat": 40, "y_repeat": 40, "cstat": 128, "status": 3,
              "shade": -8}
    record.update(overrides)
    return record


def pickup_art_faults(disk: Any) -> list[str]:
    """Key pickups whose art does not match the key they grant.

    Readability, not correctness: the lock still opens, so nothing static
    catches it and nothing crashes. The player picks up a skull key, walks to
    a door that wants the moon, and cannot tell why it opens.
    """
    by_type = {kind: key for key, kind in KEY_ITEM_TYPE.items()}
    out = []
    for index, sprite in enumerate(disk.sprites):
        kind = int(sprite.fields["type"])
        key = by_type.get(kind)
        if key is None:
            continue
        found = int(sprite.fields["picnum"])
        want = world_picnum(key)
        if found != want:
            out.append(
                f"sprite {index} grants key {key} (item type {kind}) but "
                f"wears tile {found}, which is the pickup art for key "
                f"{by_type.get(found - WORLD_TILE_BASE, '?')}; it should be "
                f"{want}")
    return out

#: Wall-aligned (16), one-sided (64), centred (128), stops a hitscan (256).
#: 125 of the campaign's 200 placards; the other 75 drop the hitscan bit.
PLACARD_CSTAT = 464

#: 149 of 200. The tile is 58 square, so this draws it 464 units across.
PLACARD_REPEAT = 32

#: Median height above the floor, in standing humans.
PLACARD_HEIGHT = 0.845

#: How far from its door a placard can hang and still be read as belonging to
#: it. The campaign's own pairing radius.
PLACARD_REACH = 3072

#: A wall shorter than the placard is drawn across cannot carry one.
PLACARD_WIDTH = PLACARD_REPEAT * 58 // 4


class KeyError_(ValueError):
    """A key marking the level cannot mean."""


def emblem_for(key: int) -> int:
    if int(key) not in KEY_EMBLEM:
        raise KeyError_(
            "there is no emblem for key %r; Blood has six, %s"
            % (key, ", ".join("%d=%s" % (k, EMBLEM_NAME[v])
                              for k, v in sorted(KEY_EMBLEM.items()))))
    return KEY_EMBLEM[int(key)]


def _edges(outline: Any) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    points = [tuple(p) for p in outline]
    return [(points[i], points[(i + 1) % len(points)]) for i in range(len(points))]


def approach_wall(layout: Any, keyed_region: str, room: str
                  ) -> tuple[tuple[int, int], tuple[int, int], float] | None:
    """Where on `room`'s boundary a placard for this door can hang.

    Returns the edge and a fraction along it, because a room's outline edge is
    not the same thing as a wall. The gallery's east side is one 10,368-unit
    edge in the level program, which the compiler splits into half a dozen
    walls around the niches and the door cut into it. Accepting or rejecting
    the whole edge -- the first version -- threw away 10,000 units of perfectly
    good masonry because one niche sat on it, and put the level's only placard
    in the room *behind* the locked door where nobody can read it before they
    need it.

    So the edge is measured as an interval, the spans other regions and mounted
    sprites occupy are subtracted, and the placard goes in the free stretch
    nearest the door.
    """
    from .prefab import _along, _on_segment, _wall_mounted_points

    door = layout.regions.get(keyed_region)
    host = layout.regions.get(room)
    if door is None or host is None:
        return None
    points = [tuple(p) for p in door.outer]
    centre = (sum(p[0] for p in points) / len(points),
              sum(p[1] for p in points) / len(points))
    mounted = _wall_mounted_points(layout, room)

    best = None
    for a, b in _edges(host.outer):
        run = math.hypot(b[0] - a[0], b[1] - a[1])
        if run < PLACARD_WIDTH:
            continue

        taken: list[tuple[float, float]] = []
        for other, region in layout.regions.items():
            if other == room:
                continue
            for c, e in _edges(region.outer):
                if (_on_segment(a, b, c, tolerance=16)
                        and _on_segment(a, b, e, tolerance=16) and c != e):
                    # `_along` gives a FRACTION of the edge, not a distance.
                    # Treating it as units put every span at 0..1 out of 10368,
                    # so nothing was ever subtracted and the placard went
                    # straight onto the doorway.
                    lo, hi = sorted((_along(a, b, c) * run, _along(a, b, e) * run))
                    taken.append((lo, hi))
        for point in mounted:
            if _on_segment(a, b, point, tolerance=64):
                at = _along(a, b, point) * run
                taken.append((at - PLACARD_WIDTH, at + PLACARD_WIDTH))

        taken.sort()
        free: list[tuple[float, float]] = []
        cursor = 0.0
        for lo, hi in taken:
            if lo > cursor:
                free.append((cursor, min(lo, run)))
            cursor = max(cursor, hi)
        if cursor < run:
            free.append((cursor, run))

        for lo, hi in free:
            if hi - lo < PLACARD_WIDTH:
                continue
            # Slide along the free stretch to the point nearest the door.
            ux, uy = (b[0] - a[0]) / run, (b[1] - a[1]) / run
            best_at = None
            steps = max(2, int((hi - lo) // 128))
            for step in range(steps + 1):
                at = lo + PLACARD_WIDTH / 2 + (hi - lo - PLACARD_WIDTH) * step / steps
                px, py = a[0] + ux * at, a[1] + uy * at
                distance = math.hypot(px - centre[0], py - centre[1])
                if best_at is None or distance < best_at[0]:
                    best_at = (distance, at)
            if best_at is None or best_at[0] > PLACARD_REACH:
                continue
            if best is None or best_at[0] < best[0]:
                best = (best_at[0], a, b, best_at[1] / run)
    if best is None:
        return None
    return best[1], best[2], best[3]


def _neighbours(layout: Any, region: str) -> list[str]:
    out = []
    for connection in layout.connections.values():
        if connection.region_a == region:
            out.append(connection.region_b)
        elif connection.region_b == region:
            out.append(connection.region_a)
    return out


def _rooms_you_see_it_from(layout: Any, keyed_region: str) -> list[str]:
    """The rooms a player actually approaches this door from.

    Not simply its neighbours. A framed door touches nothing but its own two
    frames, whose jambs are a couple of hundred units wide -- the exit gate's
    are 261 against a placard 464 across -- so a placard has to be hung in the
    room beyond. This steps through anything that is itself a doorway.
    """
    rooms: list[str] = []
    for first in dict.fromkeys(_neighbours(layout, keyed_region)):
        region = layout.regions.get(first)
        if region is not None and getattr(region, "role", None) == "doorway":
            for second in _neighbours(layout, first):
                if second != keyed_region:
                    rooms.append(second)
        else:
            rooms.append(first)
    return list(dict.fromkeys(rooms))


def key_placard(layout: Any, placard_id: str, *, room: str, key: int,
                a1: tuple[int, int], a2: tuple[int, int], t: float = 0.5,
                shade: int = -8) -> str:
    """Hang the emblem for `key` on one wall of `room`."""
    picnum = emblem_for(key)
    return layout.place_on_wall(
        placard_id, room, a1=a1, a2=a2, t=t,
        height_player_heights=PLACARD_HEIGHT,
        picnum=picnum, cstat=PLACARD_CSTAT,
        x_repeat=PLACARD_REPEAT, y_repeat=PLACARD_REPEAT,
        shade=shade, pal=0, type=0,
    )


def sign_the_locks(layout: Any) -> list[dict[str, Any]]:
    """Give every keyed region in the layout the placard its key calls for.

    Returns what was signed and what could not be, because a lock nobody can
    read is worth reporting rather than swallowing.
    """
    signed = []
    for name, region in list(layout.regions.items()):
        key = int(dict(getattr(region, "sector_behavior", {}) or {}).get("key", 0) or 0)
        if not key:
            continue
        rooms = _rooms_you_see_it_from(layout, name)
        placed = 0
        for index, room in enumerate(dict.fromkeys(rooms)):
            wall = approach_wall(layout, name, room)
            if wall is None:
                continue
            key_placard(layout, "placard_%s_%d" % (name.split(":", 1)[-1], index),
                        room=room, key=key, a1=wall[0], a2=wall[1], t=wall[2])
            placed += 1
        signed.append({"region": name, "key": key,
                       "emblem": EMBLEM_NAME[emblem_for(key)],
                       "placards": placed,
                       "rooms": list(dict.fromkeys(rooms))})
    return signed


def check(disk: Any) -> list[str]:
    """Do this map's placards and its locks agree?

    Three ways they can disagree, and this level has committed the first two:

    * a placard for a key no lock in the map demands -- signposting a door that
      is not there;
    * a keyed door with no placard within reach -- a lock the player cannot read;
    * a placard whose emblem is not the emblem of the nearest lock's key.
    """
    from tools.mine_keys import key_of

    complaints: list[str] = []
    locks = []
    for index, sector in enumerate(disk.sectors):
        key = key_of(sector)
        if not key:
            continue
        fields = sector.fields
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        xs = [int(disk.walls[w].fields["x"]) for w in range(start, start + count)]
        ys = [int(disk.walls[w].fields["y"]) for w in range(start, start + count)]
        locks.append((key, sum(xs) // len(xs), sum(ys) // len(ys)))

    placards = [(int(s.fields["picnum"]), int(s.fields["x"]), int(s.fields["y"]))
                for s in disk.sprites
                if int(s.fields["picnum"]) in EMBLEM_NAME
                and not int(s.fields["cstat"]) & 0x8000]

    held = {int(s.fields["type"]) for s in disk.sprites}

    for picnum, x, y in placards:
        near = [(math.hypot(lx - x, ly - y), key)
                for key, lx, ly in locks]
        near.sort()
        if not near or near[0][0] > PLACARD_REACH:
            complaints.append(
                "placard %s at (%d,%d) is not within %d units of any keyed door"
                % (EMBLEM_NAME[picnum], x, y, PLACARD_REACH))
        elif emblem_for(near[0][1]) != picnum:
            complaints.append(
                "placard %s at (%d,%d) sits by a door that wants %s"
                % (EMBLEM_NAME[picnum], x, y,
                   EMBLEM_NAME[emblem_for(near[0][1])]))

    for key, x, y in locks:
        if not any(math.hypot(px - x, py - y) <= PLACARD_REACH
                   and pic == emblem_for(key)
                   for pic, px, py in placards):
            complaints.append(
                "the door at (%d,%d) wants the %s key and nothing says so"
                % (x, y, EMBLEM_NAME[emblem_for(key)]))
        if KEY_ITEM_TYPE[key] not in held:
            complaints.append(
                "the door at (%d,%d) wants the %s key and the level does not "
                "contain one" % (x, y, EMBLEM_NAME[emblem_for(key)]))
    return complaints
