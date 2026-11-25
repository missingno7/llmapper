"""How the sewer's secrets are hidden and what opens them: bars and a wheel, a bloody hand on a slab that gives, ivy over a crawl.

The owner, 2026-11-25: "Some secret locations are too visible and easy to access
like that voodoo doll on that place, it should be closed behind bars or something
where you will have wheel as a switch (picnum 982), there are other types of
buttons as well, in some levels there is like a button with bloody hands made as a
sector that goes back a little when pressed." What the campaign does is
`knowledge/blood/studies/secrets/notes.md`: a panel that is its own button differs
from the wall beside it; one worked from elsewhere is the wall's own, and the
button is the tell.

* the stash: seen through bars, which a valve wheel round the corner lifts (both
  halves are E3M3's: the bars of its s254, the wheel of its sprites 107 and 108);
* the Rat King's shrine: its pipe is stopped with the wall's own tiles, and the
  bloody hands on the bleeding floor's wall are a slab that gives (E1M2's s261, of
  its freezer);
* Old Molly's nest: its crawl is behind ivy that stops nobody.
"""

from __future__ import annotations

from bloodmap import mechanism, motion, wiring
from bloodmap.motion import MARKER_OFF, MARKER_ON

import wires

PU = 1024
#: E3M3's portcullis (sprite 198, with E4M6's bit that stops a bullet too), and how far it goes up
GRILLE, GRILLE_CSTAT, LIFT = 1044, 8593, 22528
BARS_DEEP = 256
#: E3M3 sprites 107 and 108, field for field; its next tile is the wheel half a spoke round
WHEEL = {"picnum": 982, "cstat": 464, "x_repeat": 24, "y_repeat": 24, "shade": -8}
HAND, IVY = 904, 17
#: where the brook's vault meets its wall, over the walk: the ivy hangs from there
VAULT_FOOT = 20480
#: the slab: how far it stands back in its frame, how far it gives, its sill over the dock, its height and width
BACK, GIVES, SILL, TALL, WIDE = 32, 64, 6144, 9216, 512
BUTTON = "region:gravesend/sewer/stockyard_floor:hand_button"


def bars_behavior(floor: int, ceiling: int) -> dict:
    """The strip the bars stand in: a kSectorZMotionSprite, which carries its sprite and leaves its floor (triggers.cpp:1209)."""
    return {"rx_id": wires.channel("sewer:stash-bars"), "busy_time_a": 20, "busy_time_b": 20, "off_floor_z": floor,
            "on_floor_z": floor - LIFT, "off_ceiling_z": ceiling, "on_ceiling_z": ceiling}


def hang_bars(layout, strip: str) -> None:
    """The bars across the stash's mouth."""
    region = layout.regions[strip]
    xs, ys = [p[0] for p in region.outer], [p[1] for p in region.outer]
    tall = region.floor_z - region.ceiling_z
    layout.add_sprite("secret:stash_bars", strip, x=(min(xs) + max(xs)) // 2, y=(min(ys) + max(ys)) // 2, z=region.floor_z - tall // 2,
                      picnum=GRILLE, x_repeat=(max(ys) - min(ys)) // 32, y_repeat=tall // 512, angle=0, cstat=GRILLE_CSTAT, shade=-8)
    wires.wire("sewer:stash-bars").then(wiring.region(strip))


def hang_wheel(layout, region: str, a, b, t: float) -> None:
    """The wheel that lifts them."""
    layout.place_on_wall("secret:stash_wheel", region, a1=a, a2=b, t=t, height_player_heights=14336 / 16960,
                         offset_player_widths=0.04, type=20, status=0, behavior={"data_1": 209, "data_2": 209}, **WHEEL)
    wires.wire("sewer:stash-bars").when(wiring.placement("secret:stash_wheel"), "push", command=motion.CMD_ON, on=True, off=True,
                                        dude_lockout=1)


def plug_behavior(floor: int, clear: int) -> dict:
    """What stops the shrine's pipe: a wall that rises and stays up."""
    return {"rx_id": wires.channel("sewer:shrine-hands"), "busy_time_a": 20, "busy_time_b": 20, "off_floor_z": floor, "on_floor_z": floor,
            "off_ceiling_z": floor, "on_ceiling_z": floor - clear}


def hands(layout, host: str, x: int, y: int, *, tile: int, layer: str) -> str:
    """The slab with the hands on it, let into a wall that faces west at `x`, its middle at `y`.

    It is drawn pressed: a marked slide stands at its ON pose in the file and is
    taken to OFF as the level starts. Only its back wall moves; the frame stays.
    """
    floor = layout.regions[host].floor_z - SILL
    y0, y1, back = y - WIDE // 2, y + WIDE // 2, x + BACK + GIVES
    layout.add_region(BUTTON, [(x, y0), (back, y0), (back, y1), (x, y1)], floor_z=floor, ceiling_z=floor - TALL, wall_picnum=tile,
                      floor_picnum=tile, ceiling_picnum=tile, wall_shade=24, floor_shade=24, ceiling_shade=28, layer=layer, role="detail",
                      type=614, declared_zero_exit=True, intent={"kind": "furnished"},
                      sector_behavior={"rx_id": wires.channel("sewer:shrine-hands"), "busy_wave_a": 1, "busy_wave_b": 1, "busy_time_a": 2,
                                       "busy_time_b": 2, "wait_time_a": 20, "retrigger_a": 1})
    layout.add_connection("connection:sewer_hand_button", host, BUTTON, a1=(x, y0), a2=(x, y1), min_width=1, min_opening=0)
    layout.carry_wall(BUTTON, (back, y0), (back, y1), moves="with")
    layout.declare_motion(BUTTON, [])
    for kind, at in ((MARKER_OFF, x + 8), (MARKER_ON, x + 8 + GIVES)):
        layout.add_sprite(f"secret:hand_marker_{kind}", BUTTON, x=at, y=y, z=floor, type=kind, picnum=motion.MARKER_PICNUM,
                          status=motion.MARKER_STATNUM, cstat=motion.MARKER_CSTAT)
    wire = wires.wire("sewer:shrine-hands")
    wire.then(wiring.region(BUTTON))
    for k, (dy, up, flip) in enumerate(((-112, 5200, 4), (104, 4100, 0))):
        hand = f"secret:hand_{k}"
        layout.add_sprite(hand, BUTTON, x=back - 4, y=y + dy, z=floor - up, picnum=HAND, x_repeat=64, y_repeat=64, angle=1024, shade=-23,
                          cstat=mechanism.CARRY_WITH | 256 | 128 | 64 | 16 | flip)
        wire.when(wiring.placement(hand), "push", command=motion.CMD_ON, on=True, off=True, dude_lockout=1)
    return BUTTON


def ivy(layout, region: str, x: int, y: int, wide: int) -> None:
    """What hangs over the crawl: drawn on both its sides and solid on neither."""
    # wider than the mouth and over its head, or its edge is the mouth's
    layout.add_sprite("secret:molly_ivy", region, x=x + 96, y=y, z=layout.regions[region].floor_z - VAULT_FOOT // 2, picnum=IVY,
                      x_repeat=wide * 3 // 2 // 32, y_repeat=VAULT_FOOT // 512, angle=1536, cstat=16 | 128, shade=12, sunk=True)
