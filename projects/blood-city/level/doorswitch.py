"""A lever, as the campaign carries it, for what is worked from somewhere else.

Levers stood beside five street doors until 2026-11-25, from when a closed leaf
wore plain wall and only a lever said that it opened. The leaves wear planks and
panels now, and the owner found the levers pointless: "it just opens door the same
way you would interact with them". A door that opens by hand gets no lever; a
lever opens something that cannot be opened by hand.

Measured, not chosen:

* **tile 1070** is the lever -- a handle on a rusty plate, 283 sprites over
  the campaign's 43 maps.
* it is **wall-aligned** (cstat 464 = 16 | 64 | 128 | 256) at repeats
  40x40, shade -8.
* **280 of its 283 sprites carry a tx_id**, and the modal command is
  **1 = kCmdOn** (147 of them), with initial state 0.

A switch that reports only its ON sends nothing every second push. `place` writes
the push; whoever wires it says `on=True, off=True` when it is to work both ways.
"""

from __future__ import annotations

from bloodmap.mechanism import CMD_TOGGLE

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


def place(layout, placement_id: str, street_region_id: str, segment,
          channel: int, *, command: int = CMD_TOGGLE) -> str:
    """One lever, wired to a channel.

    Delegates to `bloodmap.switches.pressed_switch`, which is the general
    grammar for this and was sitting unused while this module reinvented
    it -- worse.  The hand-rolled version omitted `trigger_push` and
    `trigger_on`, which 160 and 241 of the campaign's 283 tile-1070 levers
    respectively set: our levers could not be pushed.  It also had to
    rediscover the 0.79 mount height from `switches-v1.json` that
    `pressed_switch` already returns.
    """
    from bloodmap.switches import pressed_switch

    spec = dict(pressed_switch(tile=LEVER_TILE, tx_id=int(channel), command=command))
    # The modal sound pair for pushed tile-1070 toggles (40 of 97).
    spec["behavior"].update(data_1=203, data_2=203)
    height = spec.pop("height_player_heights", LEVER_HEIGHT)
    a1, a2 = segment
    return layout.place_on_wall(
        placement_id, street_region_id, a1=a1, a2=a2, t=0.5,
        height_player_heights=height, offset_player_widths=0.06,
        status=0, **spec)
