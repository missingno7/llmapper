"""Levers beside doors, so a door reads as a door.

Owner: "building doors look like a solid wall, they should have a lever
next to it to open them."  Correct, and it follows from something this
project established earlier: Blood has no door texture -- E3M1's own door
leaves wear 379 and 449, plain wall stone -- so a closed door in a masonry
facade is, visually, masonry.  Height and a reveal got it part of the way.
A lever finishes the job, because it is the only thing on a Blood facade
that says "this opens".

Measured, not chosen:

* **tile 1070** is the lever -- a handle on a rusty plate, 356 instances,
  more than twice the next switch tile.
* it is **wall-aligned** (cstat 464 = 16 | 64 | 128 | 256) at repeats
  40x40, shade -8.
* it mounts at **0.48 player heights**, which is hand height.
* **351 of its 356 instances carry a tx_id**, and the modal command is
  **1 = kCmdOn** (183 of them), with initial state 0 (350 of them).

The door keeps `xsector_direct_use` as well, so pushing the door itself
still works; the lever adds `rx_id` on the same channel.  Two ways in is
not redundancy here -- it is the difference between a player who finds the
door and a player who walks past a wall.
"""

from __future__ import annotations

#: The lever, exactly as the campaign carries it.
LEVER_TILE = 1070
LEVER_TYPE = 20            # kSwitchToggle
LEVER_CSTAT = 464          # wall-aligned | one-sided | centred | blocking2
LEVER_REPEAT = 40
LEVER_SHADE = -8
#: `knowledge/blood/design/switches-v1.json` splits switches by how they
#: are operated, which the raw per-tile median does not: tile 1070 spans
#: q1 0.18 / median 0.48 / q3 0.78 across all its instances, but the
#: **pushed** population -- the ones a player walks up to and uses -- sits
#: at median **0.79**, just under the campaign's 0.832 eye height.  A door
#: lever is a pushed switch, so it takes the pushed height, not the
#: all-instances one.
LEVER_HEIGHT = 0.79
LEVER_COMMAND = 1          # kCmdOn, the campaign's modal
LEVER_OFFSET = 512         # how far to the side of the opening it sits

#: Channels reserved for door levers.  L1's channel budget owns the rest;
#: these are taken from the top of the range so they cannot collide with
#: the destruction and secret channels already allocated.
FIRST_CHANNEL = 200


def channel_for(index: int) -> int:
    return FIRST_CHANNEL + index


def lever_segment(face: str, x0: int, y0: int, x1: int, y1: int,
                  offset: int = LEVER_OFFSET):
    """The wall segment beside an opening, on the mass face.

    Wound the way `props.face_segment` winds a room's north face, which is
    the relationship a street has to a building it fronts: the open side
    lies beyond the segment as you walk along it.
    """
    # Wound so the STREET lies on the segment's inward side, which is the
    # relationship `place_on_wall` resolves against.  A room's north face
    # winds +x with the room at +y, so a wall whose street is at +y winds
    # +x; a wall whose street is at +x takes the mirror of the east-face
    # winding, -y.  Getting this backwards puts the lever inside the
    # building, which is where the lobby's first one went.
    if face == "south":                      # street at +y
        return ((x1, y1), (x1 + offset, y1))
    if face == "north":                      # street at -y
        return ((x0, y0), (x0 - offset, y0))
    if face == "east":                       # street at +x
        return ((x1, y1 + offset), (x1, y1))
    if face == "west":                       # street at -x
        return ((x0, y0 - offset), (x0, y0))
    raise ValueError(f"no lever segment for face {face!r}")


def place(layout, placement_id: str, street_region_id: str, segment,
          channel: int) -> str:
    """One lever, wired to a channel.

    Delegates to `bloodmap.switches.pressed_switch`, which is the general
    grammar for this and was sitting unused while this module reinvented
    it -- worse.  The hand-rolled version omitted `trigger_push` and
    `trigger_on`, which 230 and 316 of the campaign's 356 tile-1070 levers
    respectively set: our levers could not be pushed.  It also had to
    rediscover the 0.79 mount height from `switches-v1.json` that
    `pressed_switch` already returns.
    """
    from bloodmap.switches import pressed_switch

    spec = dict(pressed_switch(tile=LEVER_TILE, tx_id=int(channel)))
    height = spec.pop("height_player_heights", LEVER_HEIGHT)
    a1, a2 = segment
    return layout.place_on_wall(
        placement_id, street_region_id, a1=a1, a2=a2, t=0.5,
        height_player_heights=height, offset_player_widths=0.06,
        status=0, **spec)
