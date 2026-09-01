"""What stands in each bay, built by the code that owns the concept.

v3. Every builder takes `(layout, section, bay, back, *, floor_z, ceiling_z,
skin)`: the section region it stands in, the strip of section floor in front
of its stretch of the section's back wall, and the box beyond that wall where
its own sub-rooms go. Sub-rooms go in the back box because a region wholly
inside another is a containment the planar layout refuses -- correctly, since
neither side of that boundary can be a portal.


v2. Every function here either calls an owning constructor or does not exist;
where a concept has no constructor the registry carries an EMPTY stall
instead. That rule is the whole rebuild: v1 hand-assembled XSECTOR dicts and
never set the sector *type*, so the map had zero type-600 sectors and not one
door worked, while renders and load smoke passed.

Three representation fixes the owner named, and where each concept lives:

* a **door** is `doors.z_motion_door` **plus `type=600`** -- the behaviour
  dict alone does nothing on a type-0 sector;
* a **crate** is a sector volume wearing a `templates` crate module, not a
  sprite;
* a **shelf** is a shallow sector wearing the shelf texture, not a sprite on
  a wall; and anything that stands on the floor goes through
  `furniture.furnish`, which knows each tile's campaign height.

Each builder is handed the layout, the stall's region id, the stall rectangle,
and a **back** rectangle beyond the stall's far wall. Sub-rooms go in the
back: a region wholly inside another is a containment the planar layout
refuses, and rightly.
"""

from __future__ import annotations

from bloodmap.aperture import FacadeOpening, facade_run, framed_door
from bloodmap.doors import z_motion_door
from bloodmap.lettering import write_on_wall
from bloodmap.furniture import furnish, mounting_for, place as furnish_into
from bloodmap.mechanism import PLAYER_HEIGHT, sliding_gate, turnstile_pair
from bloodmap.owner_anchors import load_owner_anchors

U = 1024

#: Blood's own sector types, so a reader can see which is which.
Z_MOTION = 600

#: The crate and table modules come from the file that owns them --
#: `projects/blood-city/level/templates.py` -- rather than being transcribed
#: here. Transcribed numbers go stale silently; imported ones cannot. That
#: file sits on the levelprog stack and imports its neighbours by bare name,
#: so its directory goes on the path before it is loaded.
def _templates():
    import pathlib
    import sys

    here = (pathlib.Path(__file__).resolve().parents[2]
            / "projects" / "blood-city" / "level")
    if str(here) not in sys.path:
        sys.path.append(str(here))
    import templates

    return templates


_TEMPLATES = _templates()
#: 452 is not 459 -- 459 is a moss-grown rock, and a market hall of rock faces
#: was what confusing them produced once. `templates.py` carries that warning
#: beside the module, which is the other reason to read it from there.
CRATE_SMALL_TILE = _TEMPLATES.SMALL_CRATE.tile
CRATE_SMALL_SIDE = _TEMPLATES.SMALL_CRATE.side
CRATE_SMALL_RISE = _TEMPLATES.SMALL_CRATE.rise
CRATE_LARGE_TILE = _TEMPLATES.LARGE_CRATE.tile
CRATE_LARGE_SIDE = _TEMPLATES.LARGE_CRATE.side
CRATE_LARGE_RISE = _TEMPLATES.LARGE_CRATE.rise
CRATE_BROKEN_TILE = 462

#: Owner anchors, by the owner's number.
#: 146 is the curtain texture (strong binding), 32x128 -- a narrow vertical
#: strip, which is why it needs its own repeat rather than the fence's.
CURTAIN_TILE, CURTAIN_TILE_W, CURTAIN_TILE_H = 146, 32, 128
BLADE = 332
JAMB_RAIL, THRESHOLD = 195, 200
GRASS, DIRT = 361, 270
SHELF = 2026
#: The sewer kit, from `reports/anchor-sewer-kit.json`: four pipe wall tiles,
#: a technical door, a grate and the light that lit it in the maps it was
#: mined from.
SEWER_PIPE = (496, 497, 498, 499)
SEWER_DOOR, SEWER_LIGHT, SEWER_GRATE = 500, 501, 502
SEWER_MACHINERY = (2462, 2463, 2476, 2477)

#: `reports/blood-assembly-counters.json`, the campaign's own counter rule:
#: a rise in the waist band 4096-8192, an elongated footprint of aspect >= 2,
#: props on the top, and an access front that is not the working side. E1M1's
#: sector 80 rises the full 8192 and carries seven props.
COUNTER_RISE = 8192
COUNTER_MIN_ASPECT = 2.0

#: Channels the zoo wires itself with, all well above the reserved band.
CH_SWITCHED_DOOR = 300
CH_CRACK = 301
CH_GATE = 302
CH_CURTAIN = 303
CH_SHELF = 304
CH_DOUBLE_SLIDE = 307
CH_PLAIN_SLIDE = 308
CH_CASKET = 309

#: `norms-v1.json` shape.median_height: one campaign storey.
MEDIAN_CLEAR = 33280
#: kChannelSecretFound: entering a sector that transmits on it scores a secret.
CH_SECRET = 2

#: A switch as the campaign builds one.
SWITCH = dict(type=20, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, shade=-8)
#: kThingWallCrack: shot open, transmits once.
CRACK = dict(type=408, picnum=1127, x_repeat=32, y_repeat=32, cstat=128, status=4)

#: A blade tile is 512 tall and has to meet both surfaces, so a rotor's clear
#: height is a whole number of them.
ROTOR_CLEAR = 32768

#: How far back a leaf sits in its frame, and how thick the leaf is. The
#: reveal is `aperture.FACADE_REVEAL`, the depth the campaign sets an
#: opening's interior back by.
REVEAL = 256
LEAF_DEPTH = 512


def _rect(box):
    x0, y0, x1, y1 = box
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _outward(back, box):
    """+1 when the back room lies to +x of the stall, -1 when to -x."""
    return 1 if back[0] >= box[2] else -1


def _span(box, back):
    """The wall the stall and its back room share, low to high."""
    sx0, sy0, sx1, sy1 = box
    x = sx1 if _outward(back, box) > 0 else sx0
    return (x, sy0), (x, sy1)


def _facing(box, back):
    """The same wall, ordered so `place_on_wall` offsets into the stall."""
    sx0, sy0, sx1, sy1 = box
    if _outward(back, box) > 0:
        return (sx1, sy0), (sx1, sy1)
    return (sx0, sy1), (sx0, sy0)


def _slice(back, box, at, depth):
    """A strip of the back room, `depth` deep, `at` units out from the stall."""
    bx0, by0, bx1, by1 = back
    if _outward(back, box) > 0:
        return (bx0 + at, by0, bx0 + at + depth, by1)
    return (bx1 - at - depth, by0, bx1 - at, by1)


def _far(strip, back, box):
    x0, y0, x1, y1 = strip
    x = x1 if _outward(back, box) > 0 else x0
    return (x, y0), (x, y1)


def _alcove(layout, stall, box, back, name, *, low, high, depth, skin,
            floor_z, ceiling_z):
    """A short neck from the stall's back wall to a feature set back from it.

    A feature that touches the stall wall over only part of its length leaves
    the rest coincident and unpaired, which the planar compiler refuses --
    correctly, since neither side of that stretch can be a portal. The neck is
    the same move the corridor makes onto each room.
    """
    wall, floor, ceiling = skin
    out = _outward(back, box)
    near = box[2] if out > 0 else box[0]
    far = near + out * depth
    x0, x1 = (near, far) if out > 0 else (far, near)
    layout.add_region(
        f"{name}:alcove", _rect((x0, low, x1, high)),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        intent={"purpose": f"{name}: the way to the exhibit"})
    layout.add_connection(f"{name}:alcove:c", stall, f"{name}:alcove",
                          a1=(near, low), a2=(near, high), min_width=384)
    return (x0, low, x1, high), far


def _framed_opening(layout, stall, box, back, name, *, width, skin,
                    floor_z, ceiling_z, header_z=None,
                    jamb=None, threshold=None):
    """A doorway cut in a wall: jambs either side, a reveal, a threshold.

    The owner's rule, and `aperture.py`'s grammar: a door is an *opening in a
    wall*, not a leaf spanning the room. The wall either side of this stays
    solid; the reveal is the short depth the leaf sits back in; the metal
    family wears jamb rail 195 and riveted threshold 200.

    Returns the reveal's box and the x its far face sits at, for whatever the
    exhibit hangs behind it.
    """
    wall, floor, ceiling = skin
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    mid = (by0 + by1) // 2
    low, high = mid - width // 2, mid + width // 2
    near = box[2] if out > 0 else box[0]
    far = near + out * REVEAL
    x0, x1 = (near, far) if out > 0 else (far, near)
    layout.add_region(
        f"{name}:reveal", _rect((x0, low, x1, high)),
        floor_z=floor_z,
        ceiling_z=header_z if header_z is not None else ceiling_z,
        wall_picnum=jamb or wall,
        floor_picnum=threshold or floor,
        ceiling_picnum=ceiling,
        intent={"purpose": f"{name}: the reveal -- jamb, header and threshold"})
    layout.add_connection(
        f"{name}:reveal:c", stall, f"{name}:reveal",
        a1=(near, low), a2=(near, high), min_width=U // 2,
        face_picnum=jamb or wall)
    return (x0, low, x1, high), far, low, high


def _narrow(strip, margin):
    """A strip pulled in along y, so a leaf has jambs to retract into."""
    x0, y0, x1, y1 = strip
    return (x0, y0 + margin, x1, y1 - margin)


# ---------------------------------------------------------------------------
# the z-motion door family -- doors.py owns these
# ---------------------------------------------------------------------------

def _z_door(layout, stall, box, back, name, *, floor_z, ceiling_z, skin,
            width=2048, jamb=JAMB_RAIL, threshold=THRESHOLD, beyond="a room",
            beyond_skin=None, **door):
    """A framed doorway with a working leaf, and something worth opening it for.

    Two things v1 got wrong and one the owner named afterwards. `type=Z_MOTION`
    is the line that makes the XSECTOR mean anything. `z_motion_door` supplies
    the busy times that endpoints alone leave at zero. And the leaf is
    **2048 wide in a wall that stays solid either side** -- a leaf spanning the
    room is not a door, it is a moving wall.
    """
    wall, floor, ceiling = skin
    header = floor_z - 3 * PLAYER_HEIGHT // 2
    reveal, after, low, high = _framed_opening(
        layout, stall, box, back, name, width=width, skin=skin,
        floor_z=floor_z, ceiling_z=ceiling_z, header_z=header,
        jamb=jamb, threshold=threshold)
    out = _outward(back, box)
    leaf_x0 = min(after, after + out * LEAF_DEPTH)
    leaf_x1 = max(after, after + out * LEAF_DEPTH)
    layout.add_region(
        f"{name}:leaf", _rect((leaf_x0, low, leaf_x1, high)),
        type=Z_MOTION,
        floor_z=floor_z, ceiling_z=floor_z,
        wall_picnum=jamb or wall, floor_picnum=threshold or floor,
        ceiling_picnum=ceiling,
        sector_behavior=z_motion_door(floor_z, header, **door),
        declared_zero_exit=True,
        intent={"purpose": f"{name}: the leaf, a type-600 sector in its frame"})
    layout.add_connection(f"{name}:c0", f"{name}:reveal", f"{name}:leaf",
                          a1=(after, low), a2=(after, high), min_width=U // 2)
    beyond_x = after + out * LEAF_DEPTH
    room_far = beyond_x + out * (2 * U + 512)
    rx0, rx1 = min(beyond_x, room_far), max(beyond_x, room_far)
    bwall, bfloor, bceiling = beyond_skin or skin
    layout.add_region(
        f"{name}:room", _rect((rx0, by_low(back), rx1, by_high(back))),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=bwall, floor_picnum=bfloor, ceiling_picnum=bceiling,
        declared_zero_exit=True,
        intent={"purpose": f"{name}: {beyond}, which is why you open it"})
    layout.add_connection(f"{name}:c1", f"{name}:leaf", f"{name}:room",
                          a1=(beyond_x, low), a2=(beyond_x, high),
                          min_width=U // 2)


def by_low(back):
    return back[1]


def by_high(back):
    return back[3]


#: Habitats. A room beyond a door is what makes opening it worth doing, and
#: its material says what kind of place the door serves.
CHAPEL = (400, 294, 285)
STORE = (452, 294, 285)
VAULT = (491, 294, 285)


def push_door(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A stone doorway into a chapel-like room: the campaign's commonest door."""
    _z_door(layout, stall, box, back, "push_door",
            floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
            beyond="a lit room on the far side", beyond_skin=CHAPEL,
            interaction="direct", open_time=8)


def switched_door(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A brick service door worked from a switch across the room."""
    _z_door(layout, stall, box, back, "switched_door",
            floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
            beyond="the store the switch serves", beyond_skin=STORE,
            interaction="remote", rx_id=CH_SWITCHED_DOOR, open_time=8)
    #: On the section's back wall, in this bay, beside the door. A bay's
    #: side edges are interior lines, not walls, so nothing can hang on them.
    a1, a2 = _facing(box, back)
    layout.place_on_wall("switched_door:switch", stall,
                         a1=a1, a2=a2, t=0.15,
                         height_player_heights=0.55,
                         behavior={"tx_id": CH_SWITCHED_DOOR, "command": 1,
                                   "trigger_push": 1},
                         **SWITCH)


def keyed_door(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    # `_` carries section_box; the key stands in this bay, not in the hall.
    #: Key 6 is the moon, which is what E1M4 sector 295 wears.
    """A locked way into a vault: what a key is for."""
    _z_door(layout, stall, box, back, "keyed_door",
            floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
            beyond="the vault the moon key opens", beyond_skin=VAULT,
            interaction="direct", key=6, open_time=8)
    #: A key lies on the floor at hip height, and `place_on_floor` seats it
    #: from the tile's own extent -- which is exactly what v1 skipped for
    #: the tiles it placed by hand.
    layout.place_on_floor("keyed_door:key", stall,
                          local=_local(_.get("section_box") or box, box,
                                       0.35, 0.3, back),
                          type=105, picnum=2552, x_repeat=40, y_repeat=40,
                          cstat=128, status=3, shade=-8)


def lift(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A shaft with two real storeys, and an upper room worth arriving at.

    The owner's habitat rule: a lift that rises into a bare box demonstrates
    nothing, because nothing up there says the ride had a point. So the
    platform sits at the bottom of a two-storey shaft and the landing opens
    into a lit upper room dressed as somewhere to be -- which is how the
    campaign's lifts sit, serving a floor rather than a ceiling.

    The mechanism itself is **hand-composed**: `doors.z_motion_door` writes
    ceiling endpoints, and a lift travels its *floor*. See the completion
    report's promotion candidates.
    """
    wall, floor, ceiling = skin
    #: A shaft is two campaign-median storeys, and it rises ABOVE the
    #: gallery's own ceiling -- which is what a lift shaft does. Deriving the
    #: storey from the room it opens off gave a landing half a body high.
    storey = MEDIAN_CLEAR
    ceiling_z = floor_z - 2 * storey
    platform = _slice(back, box, 0, 2 * U)
    landing = _slice(back, box, 2 * U, 3 * U)
    layout.add_region(
        "lift:platform", _rect(platform),
        type=Z_MOTION,
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        sector_behavior={
            "busy_time_a": 20, "busy_time_b": 20,
            #: A *floor* z-motion: the two endpoints differ on floor_z and
            #: agree on ceiling_z, the mirror of a door's.
            "off_floor_z": floor_z, "on_floor_z": floor_z - storey,
            "off_ceiling_z": ceiling_z, "on_ceiling_z": ceiling_z,
            "trigger_push": 1, "trigger_wall_push": 1,
        },
        intent={"purpose": "lift: its floor travels a whole storey"})
    #: The upper room, a storey up: its own material, its own light, and
    #: something standing in it. This is the half that makes the ride read.
    layout.add_region(
        "lift:landing", _rect(landing),
        floor_z=floor_z - storey, ceiling_z=ceiling_z,
        wall_picnum=CHAPEL[0], floor_picnum=CHAPEL[1], ceiling_picnum=ceiling,
        declared_zero_exit=True,
        intent={"purpose": "lift: the upper room, and why the ride is worth "
                           "taking"})
    a1, a2 = _span(box, back)
    layout.add_connection("lift:c0", stall, "lift:platform",
                          a1=a1, a2=a2, min_width=U // 2)
    b1, b2 = _far(platform, back, box)
    layout.add_connection("lift:c1", "lift:platform", "lift:landing",
                          a1=b1, a2=b2, min_width=U // 2)
    layout.place_on_floor("lift:urn", "lift:landing", local=(0.35, 0.5),
                          **furnish("urn"))
    layout.place_on_floor("lift:statue", "lift:landing", local=(0.65, 0.5),
                          **furnish("statue"))
    lx0, ly0, lx1, ly1 = landing
    layout.place_on_wall("lift:lantern", "lift:landing",
                         a1=(lx1, ly1), a2=(lx0, ly1), t=0.5,
                         height_player_heights=1.1, **furnish("lantern"))


def crack_barrier(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A breach in a load-bearing brick wall, opened once by shooting.

    Flush at rest -- ceiling on the floor -- which is how E1M4's 276 and 277
    are built. The breach is narrow and the wall either side stays solid, so
    what the shot opens reads as damage rather than as a door.
    """
    wall, floor, ceiling = skin
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    mid = (by0 + by1) // 2
    width = 1536
    low, high = mid - width // 2, mid + width // 2
    near = box[2] if out > 0 else box[0]
    leaf_far = near + out * 768
    lx0, lx1 = min(near, leaf_far), max(near, leaf_far)
    layout.add_region(
        "crack:leaf", _rect((lx0, low, lx1, high)),
        type=Z_MOTION,
        floor_z=floor_z, ceiling_z=floor_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        sector_behavior={
            "rx_id": CH_CRACK, "command": 1, "trigger_once": 1,
            "busy_time_a": 4, "busy_time_b": 4,
            "off_floor_z": floor_z, "on_floor_z": floor_z,
            "off_ceiling_z": floor_z, "on_ceiling_z": ceiling_z,
        },
        declared_zero_exit=True,
        intent={"purpose": "crack barrier: the breach, flush at rest"})
    room_far = leaf_far + out * (2 * U)
    rx0, rx1 = min(leaf_far, room_far), max(leaf_far, room_far)
    layout.add_region(
        "crack:room", _rect((rx0, by0, rx1, by1)),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        declared_zero_exit=True,
        intent={"purpose": "crack barrier: the space the breach reveals"})
    layout.add_connection("crack:c0", stall, "crack:leaf",
                          a1=(near, low), a2=(near, high), min_width=U // 2)
    layout.add_connection("crack:c1", "crack:leaf", "crack:room",
                          a1=(leaf_far, low), a2=(leaf_far, high),
                          min_width=U // 2)
    f1, f2 = _facing(box, back)
    layout.place_on_wall("crack:sprite", stall, a1=f1, a2=f2, t=0.5,
                         height_player_heights=0.7,
                         behavior={"tx_id": CH_CRACK, "command": 1},
                         **CRACK)


# ---------------------------------------------------------------------------
# the rotating family -- mechanism.py owns these
# ---------------------------------------------------------------------------

def _rotor_pair(layout, stall, box, back, name, *, floor_z, ceiling_z, skin,
                counter_rotating, concourse=True):
    """Two rotor drums flanking a gap, built by mechanism.turnstile_pair.

    Each drum reaches the room through its own short alcove, because a drum
    set straight against the stall wall covers only part of it and leaves the
    rest coincident and unpaired.
    """
    wall, floor, ceiling = skin
    drum = 2 * U
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    mid = (by0 + by1) // 2
    lows = (mid - drum - U // 2, mid + U // 2)
    for index, low in enumerate(lows):
        _alcove(layout, stall, box, back, f"{name}:{index}",
                low=low, high=low + drum, depth=512, skin=skin,
                floor_z=floor_z, ceiling_z=ceiling_z)
    near = (box[2] if out > 0 else box[0]) + out * 512
    outlines, pivots = [], []
    for low in lows:
        x0 = min(near, near + out * drum)
        x1 = max(near, near + out * drum)
        outlines.append([(x0, low), (x1, low), (x1, low + drum), (x0, low + drum)])
        pivots.append(((x0 + x1) // 2, low + drum // 2))
    built = turnstile_pair(
        layout, name, outlines=(outlines[0], outlines[1]),
        pivots=(pivots[0], pivots[1]), period=255,
        floor_z=floor_z, ceiling_z=floor_z - ROTOR_CLEAR,
        counter_rotating=counter_rotating, blade_picnum=BLADE,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling)
    for index, low in enumerate(lows):
        face = near
        layout.add_connection(
            f"{name}:c{index}", f"{name}:{index}:alcove",
            f"{name}:{'ab'[index]}",
            a1=(face, low), a2=(face, low + drum), min_width=U // 2)

    if not concourse:
        return built

    #: The habitat. E1M4's carnival entry is what turnstiles are *for*: they
    #: flank the way into somewhere public, and the concourse beyond is the
    #: reason anyone pushes through one. Two drums in two alcoves with
    #: nothing behind them are a pair of machines, not an entrance.
    far_face = near + out * drum
    cx0 = min(far_face, far_face + out * 2 * U)
    cx1 = max(far_face, far_face + out * 2 * U)
    layout.add_region(
        f"{name}:concourse", _rect((cx0, lows[0], cx1, lows[1] + drum)),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        declared_zero_exit=True,
        intent={"purpose": f"{name}: the public space the turnstiles admit "
                           f"you to, as E1M4's carnival entry does"})
    for index, low in enumerate(lows):
        layout.add_connection(
            f"{name}:out{index}", f"{name}:{'ab'[index]}",
            f"{name}:concourse",
            a1=(far_face, low), a2=(far_face, low + drum), min_width=U // 2)
    return built


def turnstile_pair_stall(layout, stall, box, back, *, floor_z, ceiling_z,
                         skin, **_):
    _rotor_pair(layout, stall, box, back, "turnstile_pair", floor_z=floor_z,
                ceiling_z=ceiling_z, skin=skin, counter_rotating=True)


def turnstile_same_way(layout, stall, box, back, *, floor_z, ceiling_z,
                       skin, **_):
    _rotor_pair(layout, stall, box, back, "turnstile_same", floor_z=floor_z,
                ceiling_z=ceiling_z, skin=skin, counter_rotating=False)


def _gate(layout, stall, box, back, name, *, floor_z, ceiling_z, skin,
          channel, busy_time, depth=U, pushable=True,
          frame=None, header_z=None, leaf=None, leaves=2):
    """A sliding gate in the back strip, built by mechanism.sliding_gate.

    `frame` cuts a proscenium first -- a narrower opening with jambs and a
    header, the gate hanging inside it. The owner's rule: a curtain hangs in
    a doorway, not on open masonry, and a gate that spans a whole room wall
    is a moving wall.
    """
    wall, floor, ceiling = skin
    at = 0
    if frame is not None:
        _reveal, _after, low, high = _framed_opening(
            layout, stall, box, back, name, width=frame, skin=skin,
            floor_z=floor_z, ceiling_z=ceiling_z, header_z=header_z,
            jamb=JAMB_RAIL, threshold=THRESHOLD)
        at = REVEAL
    strip = _slice(back, box, at, depth)
    if frame is not None:
        #: The gate is exactly as wide as the opening it hangs in. A gate
        #: sector wider than its reveal would meet the stall's back wall
        #: over the rest of its length, which is neither a portal nor solid.
        strip = (strip[0], low, strip[2], high)
    sx0, sy0, sx1, sy1 = strip
    middle = (sx0 + sx1) // 2
    #: The leaves retract into the jambs, past the ends of the opening, so
    #: the gate sector has to be wider than its own threshold.
    span = (sy1 - sy0) // 2
    centre = (sy0 + sy1) // 2
    threshold = ((middle, centre - span // 2), (middle, centre + span // 2))
    sliding_gate(layout, f"{name}:gate", _rect(strip),
                 threshold=threshold, travel=span // 2,
                 **(leaf or {}),
                 channel=channel, busy_time=busy_time, pushable=pushable,
                 leaves=leaves,
                 floor_z=floor_z, ceiling_z=ceiling_z,
                 wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling)
    if frame is None:
        a1, a2 = _span(box, back)
        layout.add_connection(f"{name}:c0", stall, f"{name}:gate",
                              a1=a1, a2=a2, min_width=U // 2)
    else:
        #: Through the proscenium rather than through the whole wall. The
        #: reveal is as wide as the frame, so the gate sector meets it over
        #: only that width and the masonry either side stays solid.
        near = _slice(back, box, 0, REVEAL)
        f1, f2 = _far((near[0], low, near[2], high), back, box)
        layout.add_connection(f"{name}:c0", f"{name}:reveal", f"{name}:gate",
                              a1=f1, a2=f2, min_width=U // 2)
    return strip


def sliding_gate_stall(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    _gate(layout, stall, box, back, "sliding_gate",
          floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
          channel=CH_GATE, busy_time=20)


def curtain(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A curtain hung in a timber proscenium, with a stage behind it.

    The owner's rule: a curtain hangs in a doorway or a proscenium, never on
    open masonry. So the opening is framed and narrower than the wall, and
    what it hides is a small lit stage -- the thing a curtain is drawn across.
    """
    wall, floor, ceiling = skin
    header = floor_z - 3 * PLAYER_HEIGHT // 2
    strip = _gate(layout, stall, box, back, "curtain",
                  floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
                  channel=CH_CURTAIN, busy_time=40, depth=768,
                  frame=3 * U, header_z=header,
                  leaf={"leaf_picnum": CURTAIN_TILE,
                        "tile_width": CURTAIN_TILE_W,
                        "tile_height": CURTAIN_TILE_H})
    stage = _slice(back, box, REVEAL + 768, 2 * U)
    layout.add_region(
        "curtain:stage", _rect(stage),
        floor_z=floor_z - PLAYER_HEIGHT // 4, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        declared_zero_exit=True,
        intent={"purpose": "curtain: the stage it is drawn across"})
    b1, b2 = _far(strip, back, box)
    layout.add_connection("curtain:c1", "curtain:gate", "curtain:stage",
                          a1=b1, a2=b2, min_width=U // 2)
    layout.place_on_floor("curtain:statue", "curtain:stage", local=(0.5, 0.5),
                          **furnish("statue"))
    sx0, sy0, sx1, sy1 = stage
    for index, t in enumerate((0.25, 0.75)):
        layout.place_on_wall(f"curtain:sconce:{index}", "curtain:stage",
                             a1=(sx1, sy1), a2=(sx0, sy1), t=t,
                             height_player_heights=1.2, **furnish("sconce"))


def shelf_secret(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    wall, floor, ceiling = skin
    #: Framed, so the shelf is narrower than the wall it sits in -- which is
    #: what makes it read as a shelf rather than as a moving wall, and leaves
    #: solid masonry for the switch that opens it.
    strip = _gate(layout, stall, box, back, "shelf_secret",
                  floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
                  channel=CH_SHELF, busy_time=20, depth=768, pushable=False,
                  frame=3 * U,
                  header_z=floor_z - 3 * PLAYER_HEIGHT // 2)
    #: As wide as the gate it hides behind, not as wide as the bay: a room
    #: wider than its own doorway meets the wall either side over stretches
    #: that are neither portal nor solid, which the compiler refuses.
    secret = _slice(back, box, REVEAL + 768, 2 * U)
    secret = (secret[0], strip[1], secret[2], strip[3])
    layout.add_region(
        "shelf_secret:secret", _rect(secret),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        declared_zero_exit=True,
        sector_behavior={"tx_id": CH_SECRET, "command": 1,
                         "trigger_enter": 1, "trigger_once": 1},
        intent={"purpose": "shelf secret: the secret the shelf hides"})
    b1, b2 = _far(strip, back, box)
    layout.add_connection("shelf_secret:c1", "shelf_secret:gate",
                          "shelf_secret:secret", a1=b1, a2=b2, min_width=U // 2)
    #: On the section's own back wall in this bay, clear of the shelf. A
    #: bay's side edges are interior lines, not walls.
    a1, a2 = _facing(box, back)
    layout.place_on_wall("shelf_secret:switch", stall,
                         a1=a1, a2=a2, t=0.12,
                         height_player_heights=0.55,
                         behavior={"tx_id": CH_SHELF, "command": 1,
                                   "trigger_push": 1},
                         **SWITCH)


def casket(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """E1M1's opening: a slide and a z travel conjugated on ONE sector.

    The owner's correction is the exhibit. The casket is not a z door: it is
    four sectors in two pairs, and the sector the player wakes in (s30) is
    **kSectorSlideMarked AND carries z endpoints** -- which is the attested
    proof that the two XSECTOR z states are not a type-600 privilege. A verb
    for the XY motion comes from the type; the z verb is orthogonal and
    composes on the same sector.

    So this builds the slide through `mechanism.sliding_gate` and then merges
    z endpoints onto that same sector, exactly as s30 does.

    Two things it is NOT, both lettered in the registry as hand-composed:
    the ROR link (PlanarLayout has no stack link at all), and the
    boundary-wall area re-partition that is how the real lid works.
    """
    wall, floor, ceiling = skin
    header = floor_z - 3 * PLAYER_HEIGHT // 2
    strip = _gate(layout, stall, box, back, "casket",
                  floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
                  channel=CH_CASKET, busy_time=40, depth=768,
                  frame=2 * U, header_z=header)
    #: The second verb on the same sector: s30's floor lifts the player so
    #: they can climb out. The owner calls this ERGONOMIC-ASSIST motion --
    #: present for the body, not for topology -- so it is not a gating claim.
    layout.regions["casket:gate"].sector_behavior.update({
        "off_floor_z": floor_z, "on_floor_z": floor_z - PLAYER_HEIGHT // 2,
        "off_ceiling_z": ceiling_z, "on_ceiling_z": ceiling_z,
    })
    hole = _slice(back, box, REVEAL + 768, 2 * U)
    hole = (hole[0], strip[1], hole[2], strip[3])
    layout.add_region(
        "casket:hole", _rect(hole),
        floor_z=floor_z - PLAYER_HEIGHT // 2, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        declared_zero_exit=True,
        intent={"purpose": "casket: the hole the lid slides off, one storey "
                           "down from the cover"})
    b1, b2 = _far(strip, back, box)
    layout.add_connection("casket:c1", "casket:gate", "casket:hole",
                          a1=b1, a2=b2, min_width=U // 2)


# ---------------------------------------------------------------------------
# apertures -- aperture.py owns these
# ---------------------------------------------------------------------------

def facade(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A street frontage, built by the facade constructor itself."""
    wall, floor, ceiling = skin
    a1, a2 = _span(box, back)
    depth = abs(back[2] - back[0]) - 512
    header = floor_z - 3 * PLAYER_HEIGHT // 2
    facade_run(
        layout, "facade", host_region=stall, a1=a1, a2=a2, depth=depth,
        openings=(FacadeOpening(bay=2, bays=2, sign="SHOP"),),
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        header_z=header, sill_z=floor_z, jamb_picnum=JAMB_RAIL)


def dressed_doorway(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A door split into frame / leaf / frame by the constructor that owns it.

    `framed_door` exists because a shut Z-motion door has zero height, so the
    room's wall paints one unbroken band from its own ceiling down -- eleven
    stacked copies of a door tile, measured on the monastery. The fix is the
    reveal: the leaf sits back between two jambs. v1 painted a bare metal
    sector and called it dressed.
    """
    wall, floor, ceiling = skin
    door = _slice(back, box, 0, 1536)
    room = _slice(back, box, 1536, 2 * U)
    layout.add_region(
        "dressed:door", _rect(door),
        type=Z_MOTION,
        floor_z=floor_z, ceiling_z=floor_z,
        wall_picnum=THRESHOLD, floor_picnum=THRESHOLD, ceiling_picnum=ceiling,
        sector_behavior=z_motion_door(floor_z, ceiling_z,
                                      interaction="direct", open_time=8),
        declared_zero_exit=True,
        intent={"purpose": "dressed doorway: the leaf, set back in its frame"})
    layout.add_region(
        "dressed:behind", _rect(room),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        declared_zero_exit=True,
        intent={"purpose": "dressed doorway: the reveal behind the frame"})
    a1, a2 = _span(box, back)
    layout.add_connection("dressed:c0", stall, "dressed:door",
                          a1=a1, a2=a2, min_width=U // 2, face_picnum=JAMB_RAIL)
    b1, b2 = _far(door, back, box)
    layout.add_connection("dressed:c1", "dressed:door", "dressed:behind",
                          a1=b1, a2=b2, min_width=U // 2, face_picnum=JAMB_RAIL)
    framed_door(layout, "dressed:door",
                near_edge=(a1, a2), far_edge=(b1, b2),
                leaf_height_z=floor_z - 3 * PLAYER_HEIGHT // 2,
                face_picnum=THRESHOLD, face_tile_height=64,
                jamb_picnum=JAMB_RAIL)


# ---------------------------------------------------------------------------
# assemblies -- volumes and textures, never sprites
# ---------------------------------------------------------------------------

def _volume(layout, name, box, *, tile, floor_z, rise, ceiling_z):
    """A solid block of geometry wearing one tile on every face.

    This is what a crate is. v1 made them sprites, which is a picture of a
    crate rather than a crate.
    """
    layout.add_region(
        name, _rect(box),
        floor_z=floor_z - rise, ceiling_z=ceiling_z,
        wall_picnum=tile, floor_picnum=tile, ceiling_picnum=tile,
        declared_zero_exit=True,
        intent={"purpose": f"{name}: a texture-grid volume"})


def crate_stack(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """Crates at their own module sizes, each a volume you can walk round."""
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    at = 512
    for index, (tile, side, rise) in enumerate((
            (CRATE_SMALL_TILE, CRATE_SMALL_SIDE, CRATE_SMALL_RISE),
            (CRATE_BROKEN_TILE, CRATE_SMALL_SIDE, CRATE_SMALL_RISE),
            (CRATE_LARGE_TILE, CRATE_LARGE_SIDE, CRATE_LARGE_RISE))):
        low = by0 + at
        high = low + side
        if high > by1 - 256:
            break
        _alcove(layout, stall, box, back, f"crate:{index}",
                low=low, high=high, depth=512, skin=skin,
                floor_z=floor_z, ceiling_z=ceiling_z)
        near = (box[2] if out > 0 else box[0]) + out * 512
        x0 = min(near, near + out * side)
        x1 = max(near, near + out * side)
        _volume(layout, f"crate:{index}:block", (x0, low, x1, high),
                tile=tile, floor_z=floor_z, rise=rise, ceiling_z=ceiling_z)
        layout.add_connection(
            f"crate:{index}:face", f"crate:{index}:alcove",
            f"crate:{index}:block",
            a1=(near, low), a2=(near, high), min_width=384)
        at += side + 512


def shelf_run(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A shelf as shallow sectors wearing the shelf texture, not a sprite."""
    wall, floor, ceiling = skin
    bx0, by0, bx1, by1 = back
    depth = 512
    near = bx0 if _outward(back, box) > 0 else bx1 - depth
    strip = (near, by0 + 512, near + depth, by1 - 512)
    layout.add_region(
        "shelf:run", _rect(strip),
        floor_z=floor_z - PLAYER_HEIGHT // 2, ceiling_z=ceiling_z,
        wall_picnum=SHELF, floor_picnum=SHELF, ceiling_picnum=ceiling,
        declared_zero_exit=True,
        intent={"purpose": "shelf run: a shallow sector wearing tile 2026"})
    a1, a2 = _span(box, back)
    layout.add_connection("shelf:c0", stall, "shelf:run",
                          a1=a1, a2=a2, min_width=U // 2)


def park_corner(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """Grass and dirt, with trees placed through furniture.py."""
    wall, floor, ceiling = skin
    grass = _slice(back, box, 0, 2 * U)
    dirt = _slice(back, box, 2 * U, U)
    layout.add_region(
        "park:grass", _rect(grass),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=GRASS, ceiling_picnum=ceiling,
        parallax_ceiling=True,
        intent={"purpose": "park corner: grass, owner anchor 361"})
    layout.add_region(
        "park:dirt", _rect(dirt),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=DIRT, ceiling_picnum=ceiling,
        parallax_ceiling=True, declared_zero_exit=True,
        intent={"purpose": "park corner: the dirt patch, owner anchor 270"})
    a1, a2 = _span(box, back)
    layout.add_connection("park:c0", stall, "park:grass",
                          a1=a1, a2=a2, min_width=U // 2)
    b1, b2 = _far(grass, back, box)
    layout.add_connection("park:c1", "park:grass", "park:dirt",
                          a1=b1, a2=b2, min_width=U // 2)
    #: `furnish` carries each tile's campaign height, so a tree meets the
    #: ground instead of hanging over it. v1 placed sprites by hand and the
    #: owner found them floating.
    for index, (name, local) in enumerate((("pine", (0.3, 0.4)),
                                           ("oak", (0.7, 0.5)),
                                           ("bush", (0.5, 0.7)))):
        layout.place_on_floor(f"park:{name}:{index}", "park:grass",
                              local=local, **furnish(name))


def counter(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A shop counter, to the campaign's own rule for one.

    `reports/blood-assembly-counters.json` mined 384 of these and states the
    rule in five clauses: a rise in the waist band 4096-8192, an elongated
    footprint of aspect at least 2, props on the top, exactly one neighbour
    it does not sit inside, and an access front that is not the working side.
    E1M1's sector 80 takes the full 8192 and carries seven props.

    The owner's habitat rule puts it in a shop: shelves behind the server,
    goods on the top, and the working clearance you cannot walk into from
    the front.
    """
    wall, floor, ceiling = skin
    top = _slice(back, box, 0, U)
    behind = _slice(back, box, U, 2 * U)
    tx0, ty0, tx1, ty1 = top
    long_side, short_side = (ty1 - ty0), (tx1 - tx0)
    if long_side < COUNTER_MIN_ASPECT * short_side:
        raise ValueError(
            f"counter: footprint {long_side}x{short_side} is not elongated "
            f"enough; the campaign rule wants aspect >= {COUNTER_MIN_ASPECT}")
    layout.add_region(
        "counter:top", _rect(top),
        floor_z=floor_z - COUNTER_RISE, ceiling_z=ceiling_z,
        wall_picnum=SHELF, floor_picnum=SHELF, ceiling_picnum=ceiling,
        intent={"purpose": "counter: the top, raised the campaign's 8192 -- "
                           "waist band, aspect 2, props on it"})
    layout.add_region(
        "counter:behind", _rect(behind),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=SHELF, floor_picnum=floor, ceiling_picnum=ceiling,
        declared_zero_exit=True,
        intent={"purpose": "counter: the working clearance the server stands "
                           "in, which the front does not reach into"})
    a1, a2 = _span(box, back)
    layout.add_connection("counter:c0", stall, "counter:top",
                          a1=a1, a2=a2, min_width=U // 2)
    b1, b2 = _far(top, back, box)
    layout.add_connection("counter:c1", "counter:top", "counter:behind",
                          a1=b1, a2=b2, min_width=U // 2)
    #: The props the campaign rule asks for, placed through `furniture.place`
    #: so each is seated the way that thing is mounted. Short props only: the
    #: counter top is a waist-high shelf with the room's ceiling still over
    #: it, so what stands on it has to fit in what is left -- and no wall
    #: fitting, because a plaque laid flat on a counter drew a gore splatter
    #: across the shelves the one time this placed one by hand.
    for index, local in enumerate(((0.5, 0.2), (0.5, 0.5), (0.5, 0.8))):
        furnish_into(layout, f"counter:prop:{index}", "counter:top", "urn",
                     local=local)


def sewer_wall(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A wet service passage: pipe walls, a grate underfoot, a technical door.

    The kit is `reports/anchor-sewer-kit.json`, mined by role: pipe walls
    496-499, technical door 500, light 501, grate 502, machinery 2462/2463.
    The habitat is what those roles were mined *from* -- a passage you duck
    along, not a hall. So the clear height is one and a bit player heights
    and the run is long and narrow, and the four pipe tiles alternate down it
    the way a real run of pipe does.
    """
    wall, floor, ceiling = skin
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    #: A service passage is ducked along. One and a quarter player heights is
    #: below the campaign median on purpose: that is the point of it.
    low_ceiling = floor_z - 5 * PLAYER_HEIGHT // 4
    mid = (by0 + by1) // 2
    width = 2 * U
    lo, hi = mid - width // 2, mid + width // 2
    _alcove_box, after = _alcove(
        layout, stall, box, back, "sewer", low=lo, high=hi, depth=512,
        skin=(SEWER_PIPE[0], floor, ceiling),
        floor_z=floor_z, ceiling_z=low_ceiling)
    at = 512
    previous = "sewer:alcove"
    face = after
    for index, pipe in enumerate(SEWER_PIPE):
        run = _slice(back, box, at, U + U // 2)
        run = (run[0], lo, run[2], hi)
        name = f"sewer:run{index}"
        layout.add_region(
            name, _rect(run),
            floor_z=floor_z, ceiling_z=low_ceiling,
            wall_picnum=pipe,
            #: NOT the grate: 502 carries mask pixels, and the measured law
            #: is that no such tile appears on any campaign floor or ceiling.
            #: A grate is a maskwall panel, and nothing here owns one.
            floor_picnum=floor,
            ceiling_picnum=ceiling,
            declared_zero_exit=index == len(SEWER_PIPE) - 1,
            intent={"purpose": f"sewer wall: pipe run {index}, tile {pipe} "
                               f"(anchor-sewer-kit role pipe_walls)"})
        layout.add_connection(
            f"sewer:c{index}", previous, name,
            a1=(face, lo), a2=(face, hi), min_width=384,
            #: The technical door face where the passage begins, which is the
            #: seam the exhibit asks you to look for.
            **({"face_picnum": SEWER_DOOR} if index == 0 else {}))
        at += U + U // 2
        face = face + out * (U + U // 2)
        previous = name
        #: What makes it read as *wet*: `furniture.wet_only()` is the set of
        #: tiles that belong under water and nowhere else, and two of them
        #: standing in the run say more than any floor tile we have graded --
        #: no owner anchor names a wet floor at any binding.
        if index % 2 == 0:
            layout.place_on_floor(f"sewer:weed:{index}", name,
                                  local=(0.5, 0.25), **furnish("waterweed"))
        #: On the run's *side* wall. Its far wall is the portal to the next
        #: run, and a sprite hung across an opening is a sprite hung in a
        #: doorway -- which the layout refuses, correctly.
        layout.place_on_wall(
            f"sewer:light:{index}", name,
            a1=(run[0], lo), a2=(run[2], lo),
            t=0.5, height_player_heights=0.95,
            type=0, picnum=SEWER_LIGHT, cstat=16, x_repeat=32, y_repeat=32,
            shade=-32)


def _sayable(text, width, size):
    """The owner's name for a tile, in the alphabet the sign font has.

    A-Z and space only, and short enough for the panel it goes under. The
    owner's labels carry slashes, commas and Czech, none of which the
    campaign's letter tiles can draw, so this keeps whole words and stops.
    """
    from bloodmap.lettering import drawn_width, text_width

    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ ")
    cleaned = "".join(c if c in allowed else " " for c in text.upper())
    words = cleaned.split()
    out = ""
    for word in words:
        trial = (out + " " + word).strip()
        if text_width(trial, size) + drawn_width(size) > width:
            break
        out = trial
    return out


def tile_museum(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A niche per owner tile, each lettered with the owner's own name.

    Strong binding first, because that is the executable half of the rule:
    a strong tile MAY name what it depicts, and a weak or untested one never
    may. The names under these panels are therefore the owner's, quoted, not
    ours -- which is exactly what makes them correctable on the walk.

    The niches carry a header so the exhibit's own label can be written on
    the solid band above them; a panel opened to the ceiling leaves nowhere
    for the sign, which is how this first failed to build.
    """
    wall, floor, ceiling = skin
    anchors = load_owner_anchors()
    strong = sorted(anchors.by_binding("strong"), key=lambda item: item.picnum)
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    depth = 512
    near = bx0 if out > 0 else bx1 - depth
    #: A niche is chest-high and headed, not a full-height slot.
    header = floor_z - 5 * PLAYER_HEIGHT // 4
    sill = floor_z - PLAYER_HEIGHT // 3
    shown = strong[:8]
    pitch = (by1 - by0 - 512) // max(1, len(shown))
    face = near if out > 0 else near + depth
    for index, item in enumerate(shown):
        low = by0 + 256 + index * pitch
        high = low + pitch - 256
        layout.add_region(
            f"museum:{item.picnum}", _rect((near, low, near + depth, high)),
            floor_z=sill, ceiling_z=header,
            wall_picnum=item.picnum, floor_picnum=floor,
            ceiling_picnum=ceiling, declared_zero_exit=True,
            intent={"purpose": f"tile museum: tile {item.picnum}, "
                               f"{item.label_en} -- owner, binding strong"})
        layout.add_connection(
            f"museum:c{index}", stall, f"museum:{item.picnum}",
            a1=(face, low), a2=(face, high), min_width=384)
        name = _sayable(item.label_en, high - low, 48)
        if name:
            a1 = (face, low) if out > 0 else (face, high)
            a2 = (face, high) if out > 0 else (face, low)
            write_on_wall(layout, f"museum:name:{item.picnum}", stall,
                          a1=a1, a2=a2, text=name,
                          height_player_heights=1.45, size=48)


# ---------------------------------------------------------------------------
# v3 builders: the sections
# ---------------------------------------------------------------------------

#: The shop kit, owner anchors. 2026 and 2635 are both graded STRONG for
#: "shelf", so both may be named; 202 is a weak-binding worn facade texture
#: and is used as material only.
SHELF_TILES = (2026, 2635)
SHOP_WORN = 202

#: Channels the v3 exhibits add.
CH_ROTOR_CHAIN = 305
CH_SEWER_DOOR = 306

#: Read from `templates.py` too: 0.30 player heights on a 1024 side.
TABLE_RISE = _TEMPLATES.TABLE_RISE
TABLE_SIDE = _TEMPLATES.TABLE_SIDE


def _local(section_box, box, u, v, back=None):
    """A point at (u, v) of the BAY, as a fraction of the SECTION.

    `place_on_floor` takes `local` relative to the region it is placing in,
    and an exhibit places into the section it stands in -- so a bay-relative
    fraction handed straight to it lands somewhere else entirely. The
    graveyard turned up in the light fittings' bay exactly this way.

    With `back` given, `u` is measured **from the section's back wall**,
    which is the only direction an exhibit can reason in: sections alternate
    sides of the spine, so the bay's own x0 is the back wall on one side and
    the front wall on the other. Measuring from x0 put a row of mannequins
    in the camera's face on half the sections.
    """
    sx0, sy0, sx1, sy1 = section_box
    if back is not None and _outward(back, box) > 0:
        x = box[2] - u * (box[2] - box[0])
    else:
        x = box[0] + u * (box[2] - box[0])
    y = box[1] + v * (box[3] - box[1])
    return ((x - sx0) / max(1, sx1 - sx0), (y - sy0) / max(1, sy1 - sy0))


def _bay_wall(box, back):
    """The section's back wall across this bay, ordered to offset inward."""
    return _facing(box, back)


def _shallow(layout, name, rect, *, tile, floor_z, ceiling_z, purpose,
             floor_picnum=None, ceiling_picnum=None):
    """A shallow sector wearing one tile: how a shelf or a panel is built.

    The representation rule the owner named: a shelf is a WALL TEXTURE on a
    shallow sector, not a sprite thrown at a wall. v1 shipped the sprite.
    """
    layout.add_region(
        name, _rect(rect),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=tile,
        floor_picnum=floor_picnum if floor_picnum is not None else tile,
        ceiling_picnum=ceiling_picnum if ceiling_picnum is not None else tile,
        declared_zero_exit=True,
        intent={"purpose": purpose})


# -- the doors gallery ------------------------------------------------------

def double_slide_door(layout, stall, box, back, *, floor_z, ceiling_z, skin,
                      **_):
    """E1M1 s4: one sector, two leaves parting along their own line."""
    _gate(layout, stall, box, back, "double_slide",
          floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
          channel=CH_DOUBLE_SLIDE, busy_time=20)


def plain_slide_door(layout, stall, box, back, *, floor_z, ceiling_z, skin,
                     **_):
    """E1M1 s63: a single leaf, the load-bearing kind, in a framed opening.

    The owner's reading calls this one *more* load-bearing than the double
    rotating door built as the way on, which is why it is not dressed up.
    """
    header = floor_z - 3 * PLAYER_HEIGHT // 2
    _gate(layout, stall, box, back, "plain_slide",
          floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
          channel=CH_PLAIN_SLIDE, busy_time=20, depth=768,
          frame=2 * U, header_z=header, leaves=1)


def double_rotating_door(layout, stall, box, back, *, floor_z, ceiling_z,
                         skin, **_):
    """E1M1 s50 and s51: two rotating leaves chained on one channel.

    The chain is the point. s50 transmits to s51, so working one leaf makes
    the other answer -- a sentence in the control-bus grammar rather than two
    doors that happen to sit together.
    """
    built = _rotor_pair(layout, stall, box, back, "rotating_door",
                        floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
                        counter_rotating=True, concourse=False)
    #: The chain: the first leaf transmits on the channel the second hears.
    layout.regions["rotating_door:a"].sector_behavior.update(
        {"tx_id": CH_ROTOR_CHAIN, "command": 1})
    layout.regions["rotating_door:b"].sector_behavior.update(
        {"rx_id": CH_ROTOR_CHAIN})
    return built


# -- the furniture hall -----------------------------------------------------

def _row_on_floor(layout, region, names, box, section_box, back, *, prefix,
                  across=0.35):
    """A row of floor-standing things across a bay, each at its own height.

    `across` is the fraction of the bay's depth measured FROM THE BACK WALL,
    so the row stands against the back of its own bay rather than out in the
    aisle where a visitor walks into it.
    """
    for index, name in enumerate(names):
        t = (index + 0.5) / len(names)
        furnish_into(layout, f"{prefix}:{name}:{index}", region, name,
                     local=_local(section_box, box, across, t, back))


def light_fittings(layout, stall, box, back, *, floor_z, ceiling_z, skin,
                   section_box=None, **_):
    """The four light kinds, each on the surface that thing hangs from."""
    a1, a2 = _bay_wall(box, back)
    for index, name in enumerate(("torch", "sconce")):
        furnish_into(layout, f"lights:{name}", stall, name,
                     a1=a1, a2=a2, t=0.25 + 0.5 * index,
                     height_player_heights=1.1)
    for index, name in enumerate(("chandelier", "lantern")):
        furnish_into(layout, f"lights:{name}", stall, name,
                     local=_local(section_box or box, box,
                                  0.35, 0.3 + 0.4 * index, back))


def wall_fittings(layout, stall, box, back, *, floor_z, ceiling_z, skin,
                  section_box=None, **_):
    """Mounted things that are not lights, each in its own alignment state."""
    a1, a2 = _bay_wall(box, back)
    for index, name in enumerate(("plaque", "plank")):
        furnish_into(layout, f"fittings:{name}", stall, name,
                     a1=a1, a2=a2, t=0.3 + 0.4 * index,
                     height_player_heights=0.9)
    #: Floor-aligned: it lies flat on the ceiling and cannot hang on a wall.
    #: `furniture.place` is what enforces that, from the tile's own cstat.
    furnish_into(layout, "fittings:ceiling_plate", stall, "ceiling_plate",
                 local=_local(section_box or box, box, 0.4, 0.5, back))


def tables(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """Tables as raised volumes at the campaign rise, not as sprites."""
    wall, floor, ceiling = skin
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    at = 512
    for index in range(2):
        low = by0 + at
        high = low + TABLE_SIDE
        if high > by1 - 256:
            break
        _alcove(layout, stall, box, back, f"tables:{index}",
                low=low, high=high, depth=512, skin=skin,
                floor_z=floor_z, ceiling_z=ceiling_z)
        near = (box[2] if out > 0 else box[0]) + out * 512
        x0 = min(near, near + out * TABLE_SIDE)
        x1 = max(near, near + out * TABLE_SIDE)
        _volume(layout, f"tables:{index}:top", (x0, low, x1, high),
                tile=SHELF_TILES[0], floor_z=floor_z, rise=TABLE_RISE,
                ceiling_z=ceiling_z)
        layout.add_connection(
            f"tables:{index}:face", f"tables:{index}:alcove",
            f"tables:{index}:top",
            a1=(near, low), a2=(near, high), min_width=384)
        at += TABLE_SIDE + 1024


def graveyard(layout, stall, box, back, *, floor_z, ceiling_z, skin,
              section_box=None, **_):
    """The headstone set, each seated on its own mined campaign height."""
    _row_on_floor(layout, stall,
                  ("headstone_rip", "headstone_cross", "headstone_flame",
                   "tomb"), box, section_box or box, back,
                  prefix="graveyard")


# -- the shop ---------------------------------------------------------------

def register(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A shop counter, to the campaign's own five-clause rule for one."""
    counter(layout, stall, box, back, floor_z=floor_z, ceiling_z=ceiling_z,
            skin=skin)


def shelf_runs(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """Two shelf runs, each a shallow sector wearing a shelf tile.

    Both tiles are owner anchors graded STRONG for "shelf", so both may be
    named. They are worn as wall texture; v1 threw one at a wall as a sprite.
    """
    wall, floor, ceiling = skin
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    depth = 512
    near = bx0 if out > 0 else bx1 - depth
    span = (by1 - by0 - 1536) // len(SHELF_TILES)
    for index, tile in enumerate(SHELF_TILES):
        low = by0 + 512 + index * (span + 256)
        high = low + span
        if high > by1 - 256:
            break
        _shallow(layout, f"shelf_runs:{index}", (near, low, near + depth, high),
                 tile=tile, floor_z=floor_z - PLAYER_HEIGHT // 2,
                 ceiling_z=ceiling_z, ceiling_picnum=ceiling,
                 purpose=f"shelf runs: a shallow sector wearing tile {tile}, "
                         f"owner anchor, binding strong")
        face = near if out > 0 else near + depth
        layout.add_connection(
            f"shelf_runs:c{index}", stall, f"shelf_runs:{index}",
            a1=(face, low), a2=(face, high), min_width=384)


def display_row(layout, stall, box, back, *, floor_z, ceiling_z, skin,
                section_box=None, **_):
    """Three mannequins, standing on the floor they are seated to."""
    _row_on_floor(layout, stall, ("mannequin",) * 3, box,
                  section_box or box, back, prefix="display",
                  across=0.3)


# -- the street -------------------------------------------------------------

def _facade(layout, stall, box, back, name, *, floor_z, ceiling_z, skin,
            bays, openings, sign):
    """One frontage through aperture.facade_run, at a given width."""
    wall, floor, ceiling = skin
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    edge = box[2] if out > 0 else box[0]
    run = bays * U
    low = (by0 + by1) // 2 - run // 2
    a1, a2 = ((edge, low), (edge, low + run))
    if out < 0:
        a1, a2 = a2, a1
    return facade_run(
        layout, name, host_region=stall, a1=a1, a2=a2, depth=4 * U,
        openings=[FacadeOpening(bay=b, bays=n,
                                sign=sign if index == 0 else None)
                  for index, (b, n) in enumerate(openings)],
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        header_z=floor_z - 40960, sill_z=floor_z - 1024,
        jamb_picnum=JAMB_RAIL)


def facade_narrow(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """The six-bay frontage: two openings, one sign."""
    _facade(layout, stall, box, back, "facade_narrow",
            floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
            bays=6, openings=((1, 1), (3, 1)), sign="SHOP")


def facade_wide(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """The same frontage at ten bays: three openings, the datums unchanged."""
    _facade(layout, stall, box, back, "facade_wide",
            floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
            bays=10, openings=((1, 1), (3, 1), (6, 2)), sign="WIDE")


# -- the sewer --------------------------------------------------------------

def pipe_run(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A wet service passage you duck along, four pipe tiles down it."""
    sewer_wall(layout, stall, box, back, floor_z=floor_z,
               ceiling_z=ceiling_z, skin=skin)


def sewer_door(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """The technical door face on a working z-motion door."""
    _z_door(layout, stall, box, back, "sewer_door",
            floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
            jamb=SEWER_DOOR, threshold=THRESHOLD,
            beyond="the plant room the passage serves",
            beyond_skin=(SEWER_PIPE[2], 294, 285),
            interaction="direct", open_time=8)


# -- the park ---------------------------------------------------------------

def ground(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """Grass and dirt: the two-tile ground vocabulary, with a seam."""
    wall, floor, ceiling = skin
    grass = _slice(back, box, 0, 2 * U)
    dirt = _slice(back, box, 2 * U, U + U // 2)
    layout.add_region(
        "ground:grass", _rect(grass),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=GRASS, floor_picnum=GRASS, ceiling_picnum=ceiling,
        parallax_ceiling=True,
        intent={"purpose": "ground: grass, owner anchor 361, binding strong"})
    layout.add_region(
        "ground:dirt", _rect(dirt),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=DIRT, floor_picnum=DIRT, ceiling_picnum=ceiling,
        parallax_ceiling=True, declared_zero_exit=True,
        intent={"purpose": "ground: the dirt patch, owner anchor 270"})
    a1, a2 = _span(box, back)
    layout.add_connection("ground:c0", stall, "ground:grass",
                          a1=a1, a2=a2, min_width=U // 2)
    b1, b2 = _far(grass, back, box)
    layout.add_connection("ground:c1", "ground:grass", "ground:dirt",
                          a1=b1, a2=b2, min_width=U // 2)


def trees(layout, stall, box, back, *, floor_z, ceiling_z, skin,
          section_box=None, **_):
    """The four tree kinds, each at its own mined campaign height."""
    for index, name in enumerate(("oak", "elm", "pine", "deadwood")):
        furnish_into(layout, f"trees:{name}", stall, name,
                     local=_local(section_box or box, box,
                                  0.25 + 0.25 * (index % 2),
                                  0.15 + 0.23 * index, back))


def straw(layout, stall, box, back, *, floor_z, ceiling_z, skin,
          section_box=None, **_):
    """A heap of straw at the height the campaign draws it."""
    _row_on_floor(layout, stall, ("straw",) * 2, box,
                  section_box or box, back, prefix="straw",
                  across=0.35)
