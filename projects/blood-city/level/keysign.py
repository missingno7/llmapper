"""Key placards, used the way Blood uses them.

`knowledge/blood/design/keys-v1.json`, mined by the authoring-loop agent
across 43 maps, is unambiguous about what these six tiles are:

    2540 skull   2541 eye   2542 flame
    2543 dagger  2544 spider  2545 moon

They are **placards**: a plate hung beside a door that needs that key.  The
campaign has 265 keyed things and **213 of them carry one** — 80%. "The
emblem is the message; the frame is the same on all six."

Gravesend had been using the eye and the flame as wall ornaments, in a city
with no keyed door anywhere: a sign promising a lock that does not exist.
This module is the correct use, and it refuses the incorrect one — a
placard is only ever emitted together with the door it describes.

The three parts of a working keyed door, all measured:

* the door sector carries `XSECTOR.key = N` (campaign keyed sectors run
  N = 1..6; key 1 is the commonest at 34 of 89);
* the placard is tile **2539 + N**, wall-aligned, hung at **0.845 player
  heights** (campaign q1 0.785, q3 0.966), repeats 32x32, palette 0;
* the key item is sprite type **99 + N** with tile **2551 + N** — key 1 is
  kItemKeySkull, type 100, tile 2552 — and it has to be somewhere the
  player can reach, or the door is just a wall.
"""

from __future__ import annotations

#: key id -> (placard tile, item sprite type, item tile, name)
KEYS = {
    1: (2540, 100, 2552, "skull"),
    2: (2541, 101, 2553, "eye"),
    3: (2542, 102, 2554, "flame"),
    4: (2543, 103, 2555, "dagger"),
    5: (2544, 104, 2556, "spider"),
    6: (2545, 105, 2557, "moon"),
}

PLACARD_HEIGHT = 0.845     # player heights; campaign q1 0.785, q3 0.966
PLACARD_CSTAT = 464        # wall-aligned | one-sided | centred | blocking2
PLACARD_REPEAT = 32        # 149 of 200 campaign placards
PLACARD_SHADE = -8


class KeyError_(ValueError):
    """A key used in a way the campaign never uses one."""


def door_fields(key: int) -> dict:
    """The XSECTOR field that actually locks a door."""
    if key not in KEYS:
        raise KeyError_(f"Blood has keys 1..6; {key} is not one")
    return {"key": int(key)}


def placard(layout, placement_id: str, region_id: str, segment, key: int,
            *, t: float = 0.5) -> str:
    """Hang the emblem for this key beside its door."""
    tile, _type, _item, _name = KEYS[key]
    a1, a2 = segment
    return layout.place_on_wall(
        placement_id, region_id, a1=a1, a2=a2, t=t,
        height_player_heights=PLACARD_HEIGHT,
        offset_player_widths=0.06,
        type=0, picnum=tile, cstat=PLACARD_CSTAT, shade=PLACARD_SHADE,
        x_repeat=PLACARD_REPEAT, y_repeat=PLACARD_REPEAT, status=0)


def item(layout, placement_id: str, region_id: str, key: int,
         local=(0.5, 0.5)) -> str:
    """Put the key itself somewhere, because a lock without one is a wall."""
    _tile, type_id, item_tile, _name = KEYS[key]
    return layout.place_on_floor(
        placement_id, region_id, local=local, height_player_heights=0.0,
        type=type_id, picnum=item_tile, cstat=0, shade=-8,
        x_repeat=32, y_repeat=32, status=3)
