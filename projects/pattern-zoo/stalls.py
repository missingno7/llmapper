"""What goes inside each stall.

One function per exhibit. Each is handed the layout, the stall's region id, the
stall rectangle, and a **back** rectangle lying beyond the stall's far wall.
Sub-rooms are built in the back, never inside the stall: a region wholly inside
another is a containment the planar layout refuses, and rightly.

Everything is added through the existing authoring stack -- `mechanism`,
`doors`, `aperture`, `lettering`. Where no constructor exists the registry
carries an EMPTY stall and says what is missing.

Tiles come from the owner's anchors by number, and the numbers are the ones
the owner named. A build once shipped tile 459 -- a moss-grown rock -- as a
crate; `owner_anchors` is why that cannot happen quietly again.
"""

from __future__ import annotations

from bloodmap.doors import xsector_direct_use, xsector_remote_rx, z_motion_endpoints
from bloodmap.mechanism import PLAYER_HEIGHT, sliding_gate, turnstile
from bloodmap.owner_anchors import load_owner_anchors

U = 1024

#: The zoo's own shell. Plain, so the exhibits are what the eye goes to.
WALL, FLOOR, CEILING = 400, 294, 285

#: Owner anchors, by the owner's number, so a reader can check them against
#: `owner-anchors-v1.json` without leaving the file.
CRATE_SMALL, CRATE_BROKEN, CRATE_LARGE = 452, 462, 95
BLADE = 332
JAMB_RAIL, THRESHOLD = 195, 200
GRASS, DIRT = 361, 270
SHELF = 2026
MANNEQUIN = 2377
SEWER_PIPE, SEWER_DOOR = 496, 500

#: Channels the zoo wires itself with. Well above the reserved band -- nothing
#: below 100 gates anything in the campaign either.
CH_SWITCHED_DOOR = 300
CH_CRACK = 301
CH_ROTATE_A = 302
CH_ROTATE_B = 303
CH_SHELF = 304
CH_GATE = 305
CH_DOUBLE_SLIDE = 306
CH_CURTAIN = 307

#: A switch as the campaign builds one.
SWITCH = dict(type=20, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, shade=-8)
#: kThingWallCrack, shot open, transmits once.
CRACK = dict(type=408, picnum=1127, x_repeat=32, y_repeat=32, cstat=128, status=4)

#: A blade tile is 512 tall and must meet both surfaces, so a rotor's clear
#: height is a whole number of them. 32768 is 64 tiles.
ROTOR_CLEAR = 32768


def _rect(box):
    x0, y0, x1, y1 = box
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _outward(back, box=None):
    """+1 when the back room lies to +x of the stall, -1 when to -x.

    Compared against the stall rather than against the origin: a heuristic on
    the sign of a coordinate happens to work for this gallery and would stop
    working the moment a stall crossed x=0.
    """
    if box is not None:
        return 1 if back[0] >= box[2] else -1
    return 1 if back[0] >= 0 else -1


def _shared(stall_box, back):
    """The wall the stall and its back room share, as (a1, a2).

    Ordered so that "into the region" points back into the stall, because
    `place_on_wall` offsets a sprite that way and the direction comes from
    the span. Reversed, the letters and the crack sprite land outside the
    sector they belong to.
    """
    sx0, sy0, sx1, sy1 = stall_box
    if _outward(back, stall_box) > 0:
        return (sx1, sy0), (sx1, sy1)
    return (sx0, sy1), (sx0, sy0)


def _span(stall_box, back):
    """The same wall as `_shared`, in plain low-to-high order.

    Geometry wants the span; only `place_on_wall` cares which way it runs,
    and giving both jobs one ordering put the sliding gate's leaves outside
    their own sector.
    """
    sx0, sy0, sx1, sy1 = stall_box
    x = sx1 if _outward(back, stall_box) > 0 else sx0
    return (x, sy0), (x, sy1)


def _slice(back, at, depth):
    """A strip of the back room, `depth` deep, `at` units out from the stall."""
    bx0, by0, bx1, by1 = back
    if _outward(back) > 0:
        return (bx0 + at, by0, bx0 + at + depth, by1)
    return (bx1 - at - depth, by0, bx1 - at, by1)


def _far_edge(strip, back):
    """The strip's face away from the stall, as (a1, a2)."""
    x0, y0, x1, y1 = strip
    x = x1 if _outward(back) > 0 else x0
    return (x, y0), (x, y1)


# ---------------------------------------------------------------------------
# the z-motion door family
# ---------------------------------------------------------------------------

def _door_behind(layout, stall, box, back, name, *, behavior,
                 floor_z, ceiling_z, shut=True):
    """A door leaf against the stall's back wall, with a room beyond it."""
    leaf = _slice(back, 0, 512)
    room = _slice(back, 512, 2 * U)
    layout.add_region(f"{name}:leaf", _rect(leaf),
                      floor_z=floor_z,
                      ceiling_z=floor_z if shut else ceiling_z,
                      wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
                      sector_behavior=behavior,
                      #: Shut at rest, so at-rest reachability is right to
                      #: say nothing walks through it. Declared rather than
                      #: opened, the way l3_mall declares its locked
                      #: service corridor.
                      declared_zero_exit=True,
                      intent={"purpose": f"{name}: the door leaf"})
    layout.add_region(f"{name}:room", _rect(room),
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
                      declared_zero_exit=True,
                      intent={"purpose": f"{name}: what the door hides"})
    a1, a2 = _span(box, back)
    layout.add_connection(f"{name}:c0", stall, f"{name}:leaf",
                          a1=a1, a2=a2, min_width=U // 2)
    b1, b2 = _far_edge(leaf, back)
    layout.add_connection(f"{name}:c1", f"{name}:leaf", f"{name}:room",
                          a1=b1, a2=b2, min_width=U // 2)


def push_door(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    _door_behind(layout, stall, box, back, "push_door",
                 behavior={**z_motion_endpoints(floor_z, ceiling_z),
                           **xsector_direct_use(),
                           "busy_time_a": 10, "busy_time_b": 10},
                 floor_z=floor_z, ceiling_z=ceiling_z)


def switched_door(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    _door_behind(layout, stall, box, back, "switched_door",
                 behavior={**z_motion_endpoints(floor_z, ceiling_z),
                           **xsector_remote_rx(CH_SWITCHED_DOOR),
                           "busy_time_a": 10, "busy_time_b": 10},
                 floor_z=floor_z, ceiling_z=ceiling_z)
    x0, y0, x1, _y1 = box
    layout.place_on_wall("switched_door:switch", stall,
                         a1=(x0, y0), a2=(x1, y0), t=0.3,
                         height_player_heights=0.55,
                         behavior={"tx_id": CH_SWITCHED_DOOR, "command": 1,
                                   "trigger_push": 1},
                         **SWITCH)


def keyed_door(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    #: Key 6 is the moon, which is what E1M4 sector 295 wears.
    _door_behind(layout, stall, box, back, "keyed_door",
                 behavior={**z_motion_endpoints(floor_z, ceiling_z),
                           **xsector_direct_use(key=6),
                           "busy_time_a": 10, "busy_time_b": 10},
                 floor_z=floor_z, ceiling_z=ceiling_z)
    layout.place_on_floor("keyed_door:key", stall, local=(0.3, 0.35),
                          type=105, picnum=2552, x_repeat=40, y_repeat=40,
                          cstat=128, status=3, shade=-8)


def lift(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    platform = _slice(back, 0, 2 * U)
    landing = _slice(back, 2 * U, 2 * U)
    top = floor_z - 4 * PLAYER_HEIGHT // 3
    layout.add_region("lift:platform", _rect(platform),
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
                      sector_behavior={"off_floor_z": floor_z, "on_floor_z": top,
                                       "off_ceiling_z": ceiling_z,
                                       "on_ceiling_z": ceiling_z,
                                       "busy_time_a": 20, "busy_time_b": 20,
                                       "trigger_push": 1, "trigger_wall_push": 1},
                      intent={"purpose": "lift: carries a body between levels"})
    layout.add_region("lift:landing", _rect(landing),
                      floor_z=top, ceiling_z=ceiling_z,
                      wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
                      declared_zero_exit=True,
                      intent={"purpose": "lift: the upper landing"})
    a1, a2 = _span(box, back)
    layout.add_connection("lift:c0", stall, "lift:platform",
                          a1=a1, a2=a2, min_width=U // 2)
    b1, b2 = _far_edge(platform, back)
    layout.add_connection("lift:c1", "lift:platform", "lift:landing",
                          a1=b1, a2=b2, min_width=U // 2)


def crack_barrier(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    #: Flush at rest -- ceiling equal to floor -- as E1M4's 276 and 277 are.
    _door_behind(layout, stall, box, back, "crack",
                 behavior={"rx_id": CH_CRACK, "command": 1,
                           "busy_time_a": 1, "trigger_once": 1,
                           "off_floor_z": floor_z, "on_floor_z": floor_z,
                           "off_ceiling_z": floor_z, "on_ceiling_z": ceiling_z},
                 floor_z=floor_z, ceiling_z=ceiling_z)
    a1, a2 = _shared(box, back)
    layout.place_on_wall("crack:sprite", stall, a1=a1, a2=a2, t=0.5,
                         height_player_heights=0.7,
                         behavior={"tx_id": CH_CRACK, "command": 1},
                         **CRACK)


# ---------------------------------------------------------------------------
# the rotating family
# ---------------------------------------------------------------------------

def _rotors(layout, stall, box, back, name, *, floor_z, period, pair,
            same_way=False, vanes=4):
    """One or two rotors in the back room, each opening off the stall."""
    drum = 2 * U
    bx0, by0, bx1, by1 = back
    mid = (by0 + by1) // 2
    near = bx0 if _outward(back) > 0 else bx1 - drum
    if pair:
        spans = [(near, mid - drum - U // 4, True),
                 (near, mid + U // 4, True if same_way else False)]
    else:
        spans = [(near, mid - drum // 2, True)]
    for index, (rx, ry, spin) in enumerate(spans):
        outline = [(rx, ry), (rx + drum, ry), (rx + drum, ry + drum), (rx, ry + drum)]
        turnstile(layout, f"{name}:rotor{index}", outline,
                  pivot=(rx + drum // 2, ry + drum // 2), period=period,
                  floor_z=floor_z, ceiling_z=floor_z - ROTOR_CLEAR,
                  clockwise=spin, vanes=vanes, blade_picnum=BLADE,
                  wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING)
        face = rx if _outward(back) > 0 else rx + drum
        layout.add_connection(f"{name}:c{index}", stall, f"{name}:rotor{index}",
                              a1=(face, ry), a2=(face, ry + drum),
                              min_width=U // 2)


def turnstile_pair_stall(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    _rotors(layout, stall, box, back, "turnstile_pair",
            floor_z=floor_z, period=255, pair=True)


def turnstile_same_way(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    _rotors(layout, stall, box, back, "turnstile_same",
            floor_z=floor_z, period=255, pair=True, same_way=True)


def double_rotate_door(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    """Two rotating leaves chained by channel, as E1M1's 50 and 51 are."""
    _rotors(layout, stall, box, back, "double_rotate",
            floor_z=floor_z, period=8, pair=True, vanes=1)
    #: The chain is the exhibit: leaf 0 listens on one channel and transmits
    #: on the next, which is E1M1's 105 -> 106 wiring.
    for index in (0, 1):
        spec = layout.regions[f"double_rotate:rotor{index}"]
        wiring = {"rx_id": CH_ROTATE_A if index == 0 else CH_ROTATE_B}
        if index == 0:
            wiring.update({"tx_id": CH_ROTATE_B, "command": 5})
        spec.sector_behavior = {**spec.sector_behavior, **wiring}
    x0, y0, x1, _y1 = box
    layout.place_on_wall("double_rotate:switch", stall,
                         a1=(x0, y0), a2=(x1, y0), t=0.3,
                         height_player_heights=0.55,
                         behavior={"tx_id": CH_ROTATE_A, "command": 1,
                                   "trigger_push": 1},
                         **SWITCH)


def _gate(layout, stall, box, back, name, *, floor_z, ceiling_z, channel,
          busy_time, depth=U, pushable=True):
    strip = _slice(back, 0, depth)
    a1, a2 = _span(box, back)
    #: The threshold runs through the middle of the gate sector, not along
    #: its edge: a leaf sprite placed exactly on a sector boundary belongs to
    #: neither side of it.
    sx0, sy0, sx1, sy1 = strip
    middle = (sx0 + sx1) // 2
    #: The leaves retract **into the jambs**, past the ends of the opening,
    #: so the gate sector has to be wider than its own threshold or a
    #: retracted leaf ends up outside the sector that carries it. Half the
    #: strip is opening and a quarter is jamb at each end.
    span = (sy1 - sy0) // 2
    centre_y = (sy0 + sy1) // 2
    threshold = ((middle, centre_y - span // 2), (middle, centre_y + span // 2))
    sliding_gate(layout, f"{name}:gate", _rect(strip),
                 threshold=threshold, travel=span // 2,
                 channel=channel, busy_time=busy_time, pushable=pushable,
                 floor_z=floor_z, ceiling_z=ceiling_z,
                 wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING)
    layout.add_connection(f"{name}:c0", stall, f"{name}:gate",
                          a1=a1, a2=a2, min_width=U // 2)
    return strip


def sliding_gate_stall(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    _gate(layout, stall, box, back, "sliding_gate",
          floor_z=floor_z, ceiling_z=ceiling_z, channel=CH_GATE, busy_time=20)


def double_slide_door(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    """One sector carrying both leaves -- E1M1 sector 4's shape."""
    _gate(layout, stall, box, back, "double_slide",
          floor_z=floor_z, ceiling_z=ceiling_z, channel=CH_DOUBLE_SLIDE,
          busy_time=10)


def curtain(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    """A slide as furnishing: nothing behind it was closed off."""
    _gate(layout, stall, box, back, "curtain",
          floor_z=floor_z, ceiling_z=ceiling_z, channel=CH_CURTAIN,
          busy_time=40, depth=768)


def shelf_secret(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    """A shelf that slides aside; a secret waits behind it."""
    strip = _gate(layout, stall, box, back, "shelf_secret",
                  floor_z=floor_z, ceiling_z=ceiling_z, channel=CH_SHELF,
                  busy_time=20, depth=640, pushable=False)
    secret = _slice(back, 640, 2 * U)
    layout.add_region("shelf_secret:secret", _rect(secret),
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
                      declared_zero_exit=True,
                      #: Channel 2 is kChannelSecretFound: entering scores it.
                      sector_behavior={"tx_id": 2, "command": 1,
                                       "trigger_enter": 1, "trigger_once": 1},
                      intent={"purpose": "shelf secret: the secret itself"})
    b1, b2 = _far_edge(strip, back)
    layout.add_connection("shelf_secret:c1", "shelf_secret:gate",
                          "shelf_secret:secret", a1=b1, a2=b2, min_width=U // 2)
    x0, y0, x1, _y1 = box
    layout.place_on_wall("shelf_secret:switch", stall,
                         a1=(x0, y0), a2=(x1, y0), t=0.3,
                         height_player_heights=0.55,
                         behavior={"tx_id": CH_SHELF, "command": 1,
                                   "trigger_push": 1},
                         **SWITCH)


def casket(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    """E1M1's opening, as far as one constructor reaches.

    The full casket is slide, stack link and z at once. What stands here is
    its z half -- a lid that lifts -- and the label says which part is real.
    """
    lid = _slice(back, 0, 2 * U)
    layout.add_region("casket:box", _rect(lid),
                      floor_z=floor_z, ceiling_z=floor_z - PLAYER_HEIGHT,
                      wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
                      sector_behavior={"off_ceiling_z": floor_z - PLAYER_HEIGHT,
                                       "on_ceiling_z": ceiling_z,
                                       "off_floor_z": floor_z,
                                       "on_floor_z": floor_z,
                                       "busy_time_a": 40, "busy_time_b": 40,
                                       "trigger_push": 1, "trigger_wall_push": 1},
                      intent={"purpose": "casket: the lid, as a z motion"})
    a1, a2 = _span(box, back)
    layout.add_connection("casket:c0", stall, "casket:box",
                          a1=a1, a2=a2, min_width=U // 2)


# ---------------------------------------------------------------------------
# apertures and dressing
# ---------------------------------------------------------------------------

def _frontage(layout, stall, box, back, name, *, floor_z, ceiling_z, face):
    room = _slice(back, 0, 2 * U)
    layout.add_region(f"{name}:interior", _rect(room),
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
                      declared_zero_exit=True,
                      intent={"purpose": f"{name}: behind the frontage"})
    a1, a2 = _span(box, back)
    layout.add_connection(f"{name}:mouth", stall, f"{name}:interior",
                          a1=a1, a2=a2, min_width=U // 2, face_picnum=face)


def facade_narrow(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    _frontage(layout, stall, box, back, "facade_narrow",
              floor_z=floor_z, ceiling_z=ceiling_z, face=WALL)


def facade_wide(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    _frontage(layout, stall, box, back, "facade_wide",
              floor_z=floor_z, ceiling_z=ceiling_z, face=WALL)


def dressed_doorway(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    """A doorway wearing the owner's jamb rail (195) and threshold (200)."""
    room = _slice(back, 0, 2 * U)
    layout.add_region("dressed:behind", _rect(room),
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=WALL, floor_picnum=THRESHOLD,
                      ceiling_picnum=CEILING, declared_zero_exit=True,
                      intent={"purpose": "dressed doorway: the reveal"})
    a1, a2 = _span(box, back)
    layout.add_connection("dressed:mouth", stall, "dressed:behind",
                          a1=a1, a2=a2, min_width=U // 2, face_picnum=JAMB_RAIL)


# ---------------------------------------------------------------------------
# assemblies and materials
# ---------------------------------------------------------------------------

def counter(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    top = _slice(back, 0, 512)
    behind = _slice(back, 512, 2 * U)
    layout.add_region("counter:top", _rect(top),
                      floor_z=floor_z - PLAYER_HEIGHT // 2, ceiling_z=ceiling_z,
                      wall_picnum=SHELF, floor_picnum=FLOOR,
                      ceiling_picnum=CEILING,
                      intent={"purpose": "counter: the top"})
    layout.add_region("counter:behind", _rect(behind),
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
                      declared_zero_exit=True,
                      intent={"purpose": "counter: the working clearance"})
    a1, a2 = _span(box, back)
    layout.add_connection("counter:c0", stall, "counter:top",
                          a1=a1, a2=a2, min_width=U // 2)
    b1, b2 = _far_edge(top, back)
    layout.add_connection("counter:c1", "counter:top", "counter:behind",
                          a1=b1, a2=b2, min_width=U // 2)


def crate_stack(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    """Crates from the owner's tiles: intact 452, broken 462, large 95."""
    for index, picnum in enumerate((CRATE_SMALL, CRATE_BROKEN, CRATE_LARGE)):
        layout.place_on_floor(f"crate:{index}", stall,
                              local=(0.3 + 0.2 * index, 0.6),
                              type=0, picnum=picnum, x_repeat=48, y_repeat=48,
                              cstat=1, shade=-4)


def shelf_run(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    a1, a2 = _shared(box, back)
    layout.place_on_wall("shelf_run:face", stall, a1=a1, a2=a2, t=0.5,
                         height_player_heights=0.9,
                         type=0, picnum=SHELF, cstat=16, x_repeat=64,
                         y_repeat=64, shade=-4)


def mannequin_row(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    for index, offset in enumerate((0.3, 0.5, 0.7)):
        layout.place_on_floor(f"mannequin:{index}", stall, local=(offset, 0.6),
                              type=0, picnum=MANNEQUIN, x_repeat=48,
                              y_repeat=48, cstat=0, shade=-8)


def park_corner(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    grass = _slice(back, 0, 2 * U)
    dirt = _slice(back, 2 * U, U)
    layout.add_region("park:grass", _rect(grass),
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=WALL, floor_picnum=GRASS,
                      ceiling_picnum=CEILING,
                      intent={"purpose": "park corner: grass"})
    layout.add_region("park:dirt", _rect(dirt),
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=WALL, floor_picnum=DIRT,
                      ceiling_picnum=CEILING, declared_zero_exit=True,
                      intent={"purpose": "park corner: the dirt patch"})
    a1, a2 = _span(box, back)
    layout.add_connection("park:c0", stall, "park:grass",
                          a1=a1, a2=a2, min_width=U // 2)
    b1, b2 = _far_edge(grass, back)
    layout.add_connection("park:c1", "park:grass", "park:dirt",
                          a1=b1, a2=b2, min_width=U // 2)


def sewer_wall(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    room = _slice(back, 0, 2 * U)
    layout.add_region("sewer:run", _rect(room),
                      floor_z=floor_z, ceiling_z=ceiling_z,
                      wall_picnum=SEWER_PIPE, floor_picnum=FLOOR,
                      ceiling_picnum=CEILING, declared_zero_exit=True,
                      intent={"purpose": "sewer wall: the pipe run"})
    a1, a2 = _span(box, back)
    layout.add_connection("sewer:c0", stall, "sewer:run",
                          a1=a1, a2=a2, min_width=U // 2, face_picnum=SEWER_DOOR)


def tile_museum(layout, stall, box, back, *, floor_z, ceiling_z, **_):
    """The owner's strong-binding tiles, on the stall's back wall."""
    anchors = load_owner_anchors()
    strong = sorted(anchors.by_binding("strong"), key=lambda item: item.picnum)
    shown = strong[:8]
    a1, a2 = _shared(box, back)
    for index, item in enumerate(shown):
        layout.place_on_wall(
            f"museum:{item.picnum}", stall, a1=a1, a2=a2,
            t=(index + 0.5) / max(1, len(shown)),
            height_player_heights=0.9,
            type=0, picnum=item.picnum, cstat=16,
            x_repeat=24, y_repeat=24, shade=-8)
