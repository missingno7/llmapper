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

from bloodmap.aperture import (
    FacadeOpening, facade_run, framed_door, maskwall_panel,
)
from bloodmap.doors import z_motion_door
from bloodmap.lettering import write_on_wall
from bloodmap.furniture import furnish, mounting_for, place as furnish_into
from bloodmap import keys, motion
from bloodmap.mechanism import (
    PLAYER_HEIGHT, curtain as mechanism_curtain,
    lift as mechanism_lift, planar_door,
    sliding_gate, turnstile_pair,
)
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

#: E1M1 s125 is 128 units deep. A curtain is thin -- that is what lets its
#: length change read as the fabric gathering.
#: The doorway the fabric hangs in. DOOR-CURTAINS s3 is 256 thick.
CURTAIN_DOORWAY = 256
CURTAIN_DEPTH = 128

#: The oracle's lid: 2048 of a 2176 footprint at rest, 128 when open.
CASKET_LID = 2048
#: The ergonomic assist, E1M1 s30's category: it boosts the body out.
CASKET_ASSIST = 6144

#: The sky, which may only appear with the parallax bit and is the only
#: thing that may. bloodmap/usage_kinds.py carries the law.
SKY = 2500

#: `norms-v1.json` shape.median_height: one campaign storey.
MEDIAN_CLEAR = 33280
#: kChannelSecretFound: entering a sector that transmits on it scores a secret.
CH_SECRET = 2

#: A switch as the campaign builds one.
#: The canonical switch, from `#TYPE600.MAP` and `#MSGBUT.MAP`: type 21 on
#: picnum 1046. Its wiring comes from `motion.transmitter`, which sets the
#: `trigger_on` the engine gates evSend on -- without it a switch flips its
#: own state and sends nothing, which is what every switch in this zoo did.
SWITCH = dict(type=motion.SWITCH_TYPE, picnum=motion.SWITCH_PICNUM,
              cstat=464, x_repeat=40, y_repeat=40, shade=-8)
#: kThingWallCrack: shot open, transmits once.
#: The full native record, from `maps/blood/mechanism/#SPR408.MAP` spr0 --
#: statnum and cstat included, because a thing left on a default statnum is
#: a thing the engine's damage path never reaches.
CRACK = motion.crack_thing()

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
#: Rooms beyond a door. Chosen from what the campaign builds with, not from
#: what reads well in a thumbnail: 400 is a multi-storey facade BACKDROP with
#: 48 wall slots in 43 maps, and using it as a room material is the single
#: largest tile error the corpus audit found.
CHAPEL = (281, 294, 285)     # irregular grey masonry, 1012 campaign slots
STORE = (91, 294, 285)       # brick with a base course, 3126
VAULT = (491, 294, 285)      # metal plating (owner anchor, weak), 200


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
                         behavior=motion.transmitter(
                             channel=CH_SWITCHED_DOOR),
                         **SWITCH)


#: The moon. The lock, the placard and the pickup all read from this one
#: number, so there is nothing to keep in step by hand.
KEYED_DOOR_KEY = 6


def keyed_door(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    # `_` carries section_box; the key stands in this bay, not in the hall.
    #: Key 6 is the moon, which is what E1M4 sector 295 wears.
    """A locked way into a vault: what a key is for."""
    _z_door(layout, stall, box, back, "keyed_door",
            floor_z=floor_z, ceiling_z=ceiling_z, skin=skin,
            beyond="the vault the moon key opens", beyond_skin=VAULT,
            interaction="direct", key=KEYED_DOOR_KEY, open_time=8)
    #: A key lies on the floor at hip height, and `place_on_floor` seats it
    #: from the tile's own extent -- which is exactly what v1 skipped for
    #: the tiles it placed by hand.
    #: Type AND art derived together from the key, so they cannot drift.
    #: This exhibit granted the moon key while wearing the skull key's tile:
    #: the lock opened, and the thing on the floor was a different key.
    layout.place_on_floor("keyed_door:key", stall,
                          local=_local(layout, _.get("section_box") or box, box,
                                       0.35, 0.3, back),
                          **keys.pickup(KEYED_DOOR_KEY))


def lift(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A shaft with two real storeys, and an upper room worth arriving at.

    The owner's habitat rule: a lift that rises into a bare box demonstrates
    nothing, because nothing up there says the ride had a point. So the
    platform sits at the bottom of a two-storey shaft and the landing opens
    into a lit upper room dressed as somewhere to be -- which is how the
    campaign's lifts sit, serving a floor rather than a ceiling.

    The mechanism is `mechanism.lift` now, promoted out of this file and
    built to `Vanilla/MACHINERY-LIFT.map`. It carries no markers: the
    vertical keeps its state pair in the XSECTOR -- `off_floor_z`/
    `on_floor_z`, and the ceiling's own pair -- chosen by the same `state`
    that chooses between markers in the horizontal.
    """
    wall, floor, ceiling = skin
    #: A shaft is two campaign-median storeys, and it rises ABOVE the
    #: gallery's own ceiling -- which is what a lift shaft does. Deriving the
    #: storey from the room it opens off gave a landing half a body high.
    storey = MEDIAN_CLEAR
    ceiling_z = floor_z - 2 * storey
    platform = _slice(back, box, 0, 2 * U)
    landing = _slice(back, box, 2 * U, 3 * U)
    mechanism_lift(
        layout, "lift", footprint=platform, region="lift:platform",
        low_z=floor_z, high_z=floor_z - storey, ceiling_z=ceiling_z,
        busy_up=20, busy_down=20, route="wall_push",
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
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
    #: A THING, not a switch. It fires when it is destroyed, so the trigger
    #: is `trigger_impact` -- damage landing -- and not `trigger_vector`,
    #: which is a hitscan crossing. That one field is why it did nothing.
    layout.place_on_wall("crack:sprite", stall, a1=f1, a2=f2, t=0.5,
                         height_player_heights=0.7,
                         behavior=motion.thing_transmitter(channel=CH_CRACK),
                         **CRACK)
    #: And the cascade the zoo omitted entirely: three exploders on the
    #: crack's own channel, staggered, so the breach BLOWS instead of
    #: silently vanishing. Without them the wall just stops existing.
    for index, (wait, along) in enumerate(zip(motion.EXPLODER_WAITS,
                                              (0.35, 0.5, 0.65))):
        puff = motion.exploder(channel=CH_CRACK, wait=wait)
        behavior = puff.pop("behavior")
        layout.place_on_wall(f"crack:blast{index}", stall, a1=f1, a2=f2,
                             t=along, height_player_heights=0.7,
                             behavior=behavior, **puff)


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


#: Owner anchors: tiles 31, 32 and 33 are all "bookcase front". The leaf
#: wears one and the recess around it wears another, so the moving section
#: reads as one bay of a run of shelving rather than as a panel.
BOOKCASE_LEAF, BOOKCASE_SURROUND = 31, 33

#: This exhibit is the level's only secret, and it is secret index 0.
SECRET_INDEX = 0


def shelf_secret(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A BOOKSHELF that slides aside, per the E1M1 s70 blueprint.

    Rebuilt after the owner walked it and could not tell what it was: it had
    been a generic two-leaf sliding gate standing in a plain recess with
    unrelated props beside it, which reads as a gate, because that is what it
    was.

    Three things make it a bookshelf instead. It is ONE leaf, not two parting
    ones -- a bookcase slides aside, it does not open like gates. The leaf
    wears an owner-anchored bookcase front and the recess around it wears
    another, so it sits in a run of shelving and the moving bay is one of
    them. And the space behind is credited as a SECRET, which is what a
    bookcase that moves is always hiding.

    E1M1's own is sector 70: a slide whose whole sector travels, dressed with
    wall sprites for the books, resting at state 1 with a shade wave. Ours
    keeps the shape and the dressing; the shade wave is the campaign's
    flourish and is left out.
    """
    wall, floor, ceiling = skin
    nook = (BOOKCASE_SURROUND, floor, ceiling)
    #: Framed and shelved: the recess is the library nook, and the shelf is
    #: the bay of it that moves.
    strip = _gate(layout, stall, box, back, "shelf_secret",
                  floor_z=floor_z, ceiling_z=ceiling_z, skin=nook,
                  channel=CH_SHELF, busy_time=20, depth=768, pushable=False,
                  frame=3 * U, leaves=1,
                  leaf=dict(leaf_picnum=BOOKCASE_LEAF),
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
        #: The tutorial's own record. It sent command 1 before, which is
        #: kCmdOn -- a verb, where the counter wants a NUMBER.
        sector_behavior=motion.secret_credit(SECRET_INDEX),
        intent={"purpose": "shelf secret: the secret behind the bookcase"})
    b1, b2 = _far(strip, back, box)
    layout.add_connection("shelf_secret:c1", "shelf_secret:gate",
                          "shelf_secret:secret", a1=b1, a2=b2, min_width=U // 2)
    #: On the section's own back wall in this bay, clear of the shelf. A
    #: bay's side edges are interior lines, not walls.
    a1, a2 = _facing(box, back)
    layout.place_on_wall("shelf_secret:switch", stall,
                         a1=a1, a2=a2, t=0.12,
                         height_player_heights=0.55,
                         behavior=motion.transmitter(channel=CH_SHELF),
                         **SWITCH)


def casket(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A lid in the floor above and its mirror in the ceiling below.

    Built to `maps/blood/mechanism/casket.map`, and it takes FOUR sectors in
    TWO planes, which is the part this project kept dropping:

        upper   s2 lid (614, floor 33792, tile 97) | s3 hole (floor 34816,
                floor tile 504 -- you look DOWN through it)
        lower   s5 lid (614, ceiling -33792)       | s6 hole (ceiling -34816,
                ceiling tile 504 -- you look UP through it)

    Both lids are on ONE channel with the same travel, so the two openings
    appear together and the ceiling below mimics the floor above. Building
    only the upper plane, as this did, leaves a hole in the floor with an
    unbroken ceiling under it: the link warps you into a room whose roof
    never opened.

    The switch is the canonical one -- `#TYPE600.MAP`'s type 21 on picnum
    1046 -- and its wiring comes from `motion.transmitter`, which sets the
    `trigger_on` that `triggers.cpp` gates evSend on. Without that flag a
    switch flips its own state and sends nothing, which is why this exhibit
    "did nothing" when pushed.
    """
    wall, floor, ceiling = skin
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    mid = (by0 + by1) // 2
    width = 2 * U
    low, high = mid - width // 2, mid + width // 2
    near = box[2] if out > 0 else box[0]
    span, travel = 2176, 1920
    far = near + out * span
    fx0, fx1 = min(near, far), max(near, far)
    rest = fx0 + CASKET_LID if out > 0 else fx1 - CASKET_LID
    signed = -travel if out > 0 else travel

    #: The upper plane: a lid in the floor you stand on.
    built = planar_door(
        layout, "casket",
        footprint=(fx0, low, fx1, high), axis="x", split=rest,
        travel=signed, channel=CH_CASKET,
        lid_region="casket:lid", hole_region="casket:hole",
        floor_z=floor_z, ceiling_z=ceiling_z, plane="floor",
        motor="hole", flags="both", route="remote",
        lift_out=CASKET_ASSIST, transmits=CH_CASKET + 1,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        hole_kwargs={"declared_zero_exit": True})
    layout.declare_motion("casket:hole", ["casket:lid"])
    layout.add_connection("casket:c0", stall, "casket:lid",
                          a1=(near, low), a2=(near, high), min_width=U // 2)

    #: The lower plane, the same footprint one storey down and mirrored into
    #: the ceiling, on the SAME channel so the two move together.
    shift = out * (span + 512)
    gx0, gx1 = fx0 + shift, fx1 + shift
    lower_floor = floor_z + MEDIAN_CLEAR
    below = planar_door(
        layout, "casket:below",
        footprint=(min(gx0, gx1), low, max(gx0, gx1), high), axis="x",
        split=rest + shift, travel=signed, channel=CH_CASKET,
        lid_region="casket:under", hole_region="casket:grave",
        floor_z=lower_floor, ceiling_z=floor_z, plane="ceiling",
        motor="hole", flags="both", route="remote",
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        lid_kwargs={"declared_zero_exit": True},
        hole_kwargs={"declared_zero_exit": True})
    layout.declare_motion("casket:grave", ["casket:under"])

    #: The link joins the two HOLES, at the plane they meet on: the upper
    #: hole's floor and the lower hole's ceiling, both wearing 504.
    anchor = built["link_anchor"]
    motion.build_stack_link(
        layout, 10, upper_region="casket:hole", lower_region="casket:grave",
        upper_at=anchor, lower_at=(anchor[0] + shift, anchor[1]),
        upper_z=floor_z, lower_z=floor_z, see_through=True)

    x0, y0, x1, _y1 = box
    layout.place_on_wall("casket:switch", stall, a1=(x0, y0), a2=(x1, y0),
                         t=0.5, height_player_heights=0.55,
                         behavior=motion.transmitter(
                             channel=CH_CASKET, receiver_state=1),
                         **SWITCH)
    return built

def curtain(layout, stall, box, back, *, floor_z, ceiling_z, skin, **_):
    """A curtain, to `Vanilla/DOOR-CURTAINS.map`.

    The fabric is an internal FIN in the doorway's own outline: a narrow tab
    hanging from one edge, whose free end is the single flagged wall. Drawing
    it across stretches the tab's two sides, and because every moved vertex
    is interior to this sector nothing outside it can deform -- which is why
    the tutorial's curtains never disturb their rooms and the zoo's did.

    It rests CLOSED. Markers are state-anchored -- type 3 is the OFF
    position, type 4 the ON position, and the geometry is drawn at ON -- so
    with state 0 the fabric snaps across the doorway at load. The zoo had
    that pair backwards and its curtains ran the wrong way.
    """
    wall, floor, ceiling = skin
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    mid = (by0 + by1) // 2
    width = 3 * U
    low, high = mid - width // 2, mid + width // 2
    near = box[2] if out > 0 else box[0]
    far = near + out * CURTAIN_DOORWAY
    x0, x1 = min(near, far), max(near, far)

    #: The doorway: thin in the direction you walk through it, wide across.
    #: The fabric draws along y, so the fin hangs from the high edge.
    built = mechanism_curtain(
        layout, "curtain", opening=(x0, low, x1, high), axis="y",
        channel=CH_CURTAIN, leaf_region="curtain:leaf",
        floor_z=floor_z, ceiling_z=ceiling_z, anchored="high",
        frame_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        declared_zero_exit=True)
    layout.declare_motion("curtain:leaf", [])
    layout.add_connection("curtain:c0", stall, "curtain:leaf",
                          a1=(near, low), a2=(near, high), min_width=384)

    #: What a curtain is drawn across.
    stage = _slice(back, box, CURTAIN_DOORWAY, 2 * U)
    stage = (stage[0], low, stage[2], high)
    layout.add_region(
        "curtain:stage", _rect(stage),
        floor_z=floor_z - PLAYER_HEIGHT // 4, ceiling_z=ceiling_z,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        declared_zero_exit=True,
        intent={"purpose": "curtain: the alcove it is drawn across"})
    layout.add_connection("curtain:c1", "curtain:leaf", "curtain:stage",
                          a1=(far, low), a2=(far, high), min_width=384)
    layout.place_on_floor("curtain:statue", "curtain:stage", local=(0.5, 0.5),
                          **furnish("statue"))
    #: A switch as well as the fabric itself, since this is an exhibit.
    f1, f2 = _facing(box, back)
    layout.place_on_wall("curtain:switch", stall, a1=f1, a2=f2, t=0.2,
                         height_player_heights=0.55,
                         behavior=motion.transmitter(channel=CH_CURTAIN),
                         **SWITCH)
    return built

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

def _volume(layout, name, box, *, tile, floor_z, rise, ceiling_z,
            ceiling_picnum=285, top_picnum=None):
    """A solid block of geometry wearing one tile on the faces that show.

    This is what a crate is. v1 made them sprites, which is a picture of a
    crate rather than a crate.

    Walls and top only. The campaign attests 452 and 95 on walls and floors
    -- a crate lid IS a floor you can stand on -- and never on a ceiling, so
    the underside keeps the room's own. The zoo wore the crate tile on all
    six faces, which put it in a slot the corpus does not attest.
    """
    layout.add_region(
        name, _rect(box),
        floor_z=floor_z - rise, ceiling_z=ceiling_z,
        wall_picnum=tile,
        floor_picnum=tile if top_picnum is None else top_picnum,
        ceiling_picnum=ceiling_picnum,
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
        wall_picnum=SHELF, floor_picnum=floor, ceiling_picnum=ceiling,
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
    #: Shelf faces on the sides, an ordinary floor on the top: 2026 is a
    #: wall tile and the campaign never lays it flat.
    layout.add_region(
        "counter:top", _rect(top),
        floor_z=floor_z - COUNTER_RISE, ceiling_z=ceiling_z,
        wall_picnum=SHELF, floor_picnum=floor, ceiling_picnum=ceiling,
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
        #: The grate, in the only slot the campaign ever puts one: the
        #: over_picnum of a masked two-sided wall. It carries the mask colour,
        #: so a floor or a plain wall is closed to it by the transparency law
        #: -- 502 appears as an over_picnum 27 times and on a plain wall never.
        if index == 1:
            maskwall_panel(layout, f"sewer:grate{index}", previous, name,
                           a1=(face, lo), a2=(face, hi),
                           picnum=SEWER_GRATE, shade=-8, blocking=False)
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
    """A niche per owner tile -- each showing that tile WHERE IT BELONGS.

    v3's museum was the worst violator of the very rule it exists to teach.
    It painted every anchor on a wall panel regardless of what kind of tile
    it was, so a translucent curtain (147), a candelabrum (580), a smoke
    plume (672) and three kinds of blood (713/731/732) were all rendered as
    masonry. Six of them carry the mask colour, which the campaign never puts
    on a one-sided wall in 52422 slots, so the museum shipped eighteen
    violations of the transparency law while claiming to teach it.

    So each panel now asks the usage-kind table where the campaign actually
    puts this tile, and shows it there: a wall tile on the niche's walls, a
    surface tile on its floor, a sprite tile as a sprite standing in it.
    Strong binding first, because that is the executable half of the owner's
    rule -- a strong tile MAY name what it depicts, and a weak or untested
    one never may.
    """
    from bloodmap.usage_kinds import slots_for, tile_size
    from bloodmap.placement import repeat_to_fit

    wall, floor, ceiling = skin
    anchors = load_owner_anchors()
    strong = sorted(anchors.by_binding("strong"), key=lambda item: item.picnum)
    out = _outward(back, box)
    bx0, by0, bx1, by1 = back
    depth = 512
    near = bx0 if out > 0 else bx1 - depth
    #: A niche is chest-high and headed, not a full-height slot, so the
    #: exhibit's own label has solid wall to sit on above it.
    header = floor_z - 5 * PLAYER_HEIGHT // 4
    sill = floor_z - PLAYER_HEIGHT // 3
    shown = strong[:8]
    pitch = (by1 - by0 - 512) // max(1, len(shown))
    face = near if out > 0 else near + depth
    for index, item in enumerate(shown):
        low = by0 + 256 + index * pitch
        high = low + pitch - 256
        slots = slots_for(item.picnum)
        best = max(slots, key=slots.get) if slots else "wall_one_sided"
        name = f"museum:{item.picnum}"
        #: A tile attested only on TWO-SIDED walls, or as the masked overlay
        #: of one, cannot go on the niche's walls: three of the four are
        #: one-sided and painting them breaks the very law this exhibit
        #: teaches. The owner's 2026-09-01 ruling put tile 142 -- the skull
        #: fireplace maskwall, whose two-sided uses are the legitimate
        #: see-through mouth -- into the strong-binding set, and the museum
        #: promptly shipped three violations of its own rule. Such a tile
        #: belongs on the niche's OPENING, as a masked panel, which is the
        #: only two-sided wall it has.
        as_overlay = best in ("wall_two_sided", "over_picnum")
        on_wall = (item.picnum if best.startswith("wall") and not as_overlay
                   else wall)
        on_floor = item.picnum if best in ("floor", "ceiling") else floor
        layout.add_region(
            name, _rect((near, low, near + depth, high)),
            floor_z=sill, ceiling_z=header,
            wall_picnum=on_wall, floor_picnum=on_floor,
            ceiling_picnum=ceiling, declared_zero_exit=True,
            intent={"purpose": f"tile museum: tile {item.picnum}, "
                               f"{item.label_en} -- owner, binding strong; "
                               f"shown in slot {best}, its commonest in the "
                               f"campaign"})
        layout.add_connection(
            f"museum:c{index}", stall, name,
            a1=(face, low), a2=(face, high), min_width=384)
        if as_overlay:
            maskwall_panel(layout, f"museum:{item.picnum}:panel",
                           stall, name,
                           a1=(face, low), a2=(face, high),
                           picnum=item.picnum, blocking=False)
        if best.startswith("sprite"):
            size = tile_size(item.picnum) or (64, 64)
            #: A sprite tile is shown as a sprite. Which alignment it takes
            #: is the tile's own business, from the same table.
            cstat = {"sprite_wall": 16, "sprite_floor": 32}.get(best, 0)
            #: Sized to the niche rather than to a fixed repeat: these are
            #: whatever the owner graded strong, and a curtain tile is four
            #: times a candle's height.
            fit = repeat_to_fit(sill, header, size[1],
                                fraction=0.8)
            layout.place_on_floor(
                f"museum:{item.picnum}:sprite", name, local=(0.5, 0.5),
                type=0, picnum=item.picnum, cstat=cstat | 128,
                x_repeat=fit, y_repeat=fit, shade=-8)
        label = _sayable(item.label_en, high - low, 48)
        if label:
            a1 = (face, low) if out > 0 else (face, high)
            a2 = (face, high) if out > 0 else (face, low)
            write_on_wall(layout, f"museum:name:{item.picnum}", stall,
                          a1=a1, a2=a2, text=label,
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


def _local(layout, section_box, box, u, v, back=None):
    """A point at (u, v) of the BAY, as a fraction of the SECTION.

    Three transforms in one, each of which was a bug once.

    `place_on_floor` takes `local` relative to the region it places into, and
    an exhibit places into the section it stands in -- so a bay-relative
    fraction handed straight to it lands somewhere else entirely. The
    graveyard turned up in the light fittings' bay that way.

    With `back` given, `u` is measured **from the section wall the bay backs
    onto**, which is the only direction an exhibit can reason in: bays sit on
    both long walls of a branch, so the bay's own x0 is the wall on one side
    and the open room on the other. Measuring from x0 put a row of mannequins
    in the camera's face on half the bays.

    And the builder's frame is not the world's. `layout` is a `frame.Framed`
    wrapping the real layout, so the local point goes through its transform
    before it is turned into a fraction of the section's WORLD rectangle --
    otherwise the fraction is computed on swapped axes and every floor-placed
    thing lands in another branch.
    """
    x = (box[2] - u * (box[2] - box[0])) if (
        back is not None and _outward(back, box) > 0) else (
        box[0] + u * (box[2] - box[0]))
    y = box[1] + v * (box[3] - box[1])
    point = layout.point((x, y)) if hasattr(layout, "point") else (x, y)
    sx0, sy0, sx1, sy1 = section_box
    return ((point[0] - sx0) / max(1, sx1 - sx0),
            (point[1] - sy0) / max(1, sy1 - sy0))


def _bay_wall(box, back):
    """The section's back wall across this bay, ordered to offset inward."""
    return _facing(box, back)


def _shallow(layout, name, rect, *, tile, floor_z, ceiling_z, purpose,
             floor_picnum=None, ceiling_picnum=None):
    """A shallow sector wearing one tile: how a shelf or a panel is built.

    The representation rule the owner named: a shelf is a WALL TEXTURE on a
    shallow sector, not a sprite thrown at a wall. v1 shipped the sprite.
    """
    #: The tile goes on the WALLS and nowhere else. A shelf tile laid on the
    #: floor of its own recess is the representation error one level down
    #: from the one this helper exists to prevent: the campaign attests 2026
    #: and 2635 on walls only, and the usage-kind check now says so.
    layout.add_region(
        name, _rect(rect),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=tile,
        floor_picnum=floor_picnum if floor_picnum is not None else 294,
        ceiling_picnum=ceiling_picnum if ceiling_picnum is not None else 285,
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
                     local=_local(layout, section_box, box, across, t, back))


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
                     local=_local(layout, section_box or box, box,
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
                 local=_local(layout, section_box or box, box, 0.4, 0.5, back))


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
        #: The shelf tile on the sides, the room's own floor on the top. A
        #: table top wearing 2026 puts a wall-only tile on a floor, which the
        #: campaign never does in 26383 surface slots.
        _volume(layout, f"tables:{index}:top", (x0, low, x1, high),
                tile=SHELF_TILES[0], floor_z=floor_z, rise=TABLE_RISE,
                ceiling_z=ceiling_z, top_picnum=floor, ceiling_picnum=ceiling)
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
                 ceiling_z=ceiling_z, floor_picnum=floor,
                 ceiling_picnum=ceiling,
                 purpose=f"shelf runs: a shallow sector wearing tile {tile}, "
                         f"owner anchor, binding strong")
        face = near if out > 0 else near + depth
        #: The niche's mouth is a two-sided wall and 2635 is attested only on
        #: one-sided ones, so the opening wears the room's material.
        layout.add_connection(
            f"shelf_runs:c{index}", stall, f"shelf_runs:{index}",
            a1=(face, low), a2=(face, high), min_width=384,
            face_picnum=wall)


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
        wall_picnum=GRASS, floor_picnum=GRASS, ceiling_picnum=SKY,
        parallax_ceiling=True,
        intent={"purpose": "ground: grass, owner anchor 361, binding strong"})
    layout.add_region(
        "ground:dirt", _rect(dirt),
        floor_z=floor_z, ceiling_z=ceiling_z,
        wall_picnum=DIRT, floor_picnum=DIRT, ceiling_picnum=SKY,
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
                     local=_local(layout, section_box or box, box,
                                  0.25 + 0.25 * (index % 2),
                                  0.15 + 0.23 * index, back))


def straw(layout, stall, box, back, *, floor_z, ceiling_z, skin,
          section_box=None, **_):
    """A heap of straw at the height the campaign draws it."""
    _row_on_floor(layout, stall, ("straw",) * 2, box,
                  section_box or box, back, prefix="straw",
                  across=0.35)
