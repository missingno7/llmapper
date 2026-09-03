"""The city's vocabulary: the constructors, named where a reader can find them.

A constructor here is one word of the language the project is trying to
speak, and P15's readers of E3M1 have to recognise the same words coming the
other way. So they live in `bloodmap` and not in the project: a project may
choose its numbers, and it may not own its nouns.

    street(...)      the ground plane: one region per connected network
    island(...)      a pavement standing on it, kerb being its exposed edge
    end_wall(...)    where a street reaches the boundary and stops
    waterfront(...)  quay walk, shore, sea, horizon -- DWE3M10's dialect
    shell(...)       a building: facade, opening, insert, room
    facade(...)      the wall of a shell, cut open at its openings
    opening(...)     a void in a facade
    insert(...)      what fills an opening, in a sector of its own

Each returns `pipeline.SurfaceSpec`s and, where it has a mechanism, the
declaration that goes with them. Nothing here compiles, cuts or writes: the
compiler owns the pipeline and a constructor only says what a thing is.

The numbers are the corpus's
============================

* the kerb steps 2048 and its face wears tile 6, on 11 of E3M1's 11 records;
* a step's face is shaded its floor's shade **+6**, median over those same 11;
* the facade family is E3M1's one-sided outdoor records weighted by LENGTH --
  401 at 27.6%, 417 at 21.5%, 181 at 11.6%, 400 at 8.7% -- all at y_repeat 8;
* a roof wears 379;
* the shore stands one walkable step (3072) below the quay, the sea meets it
  at equal z under palette 10 with pan_floor, pan_always and drag, and the
  horizon is a zero-height sector wearing the SAME sky as the space it ends,
  because 271 of 271 campaign outdoor regions wear exactly one.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

from . import joins
from .pipeline import SurfaceSpec

Point = tuple[int, int]

#: The ground's own materials, and E3M1's numbers for them.
ROAD_TILE = 352
PAVEMENT_TILE = 4
KERB_TILE = joins.TILE_CLASSES["kerb class"]
ROAD_WALL_TILE = 400
PAVEMENT_WALL_TILE = 401
FACADE_FAMILY = joins.FACADE_FAMILY
ROOF_TILE = joins.ROOF_TILE
#: THE FLOOR AND CEILING CLASSES, from `materials.INTERIORS["common"]`, which
#: is E3M1's own interior: a papered wall over a coffered ceiling. They are
#: named here because a wall-class tile on a horizontal surface is a fault --
#: the owner found 401, the facade family's window, on an interior floor.
INTERIOR_FLOOR = 304
INTERIOR_CEILING = 454
#: A pavement stands this far above the road it borders.
KERB_RISE = 2048


def _rect(x0: int, y0: int, x1: int, y1: int) -> list:
    return [(int(x0), int(y0)), (int(x1), int(y0)),
            (int(x1), int(y1)), (int(x0), int(y1))]


def street(surface_id: str, rings: Sequence[Sequence[Point]], *,
           floor_z: int, sky_z: int, sky_tile: int,
           wall_tile: int = ROAD_WALL_TILE,
           floor_tile: int = ROAD_TILE) -> SurfaceSpec:
    """The ground plane: ONE region per connected street network.

    A junction is not a thing to declare -- it is the part of the plane no
    island covers -- and the kerb is not an object either: it is what the join
    road|pavement looks like. The wall material is NOT the kerb tile, because
    a kerb exists only where a road meets a pavement; making it the plane's
    default put a kerb face on every shadow cut and every map edge.
    """
    return SurfaceSpec(
        surface_id=surface_id, rings=tuple(list(ring) for ring in rings),
        floor_z=int(floor_z), ceiling_z=int(sky_z), floor_tile=int(floor_tile),
        ceiling_tile=int(sky_tile), wall_tile=int(wall_tile),
        kind=joins.ROAD)


def island(surface_id: str, rings: Sequence[Sequence[Point]], *,
           floor_z: int, sky_z: int, sky_tile: int,
           wall_tile: int = PAVEMENT_WALL_TILE,
           floor_tile: int = PAVEMENT_TILE) -> SurfaceSpec:
    """A pavement standing on the plane. Its exposed edge IS the kerb."""
    return SurfaceSpec(
        surface_id=surface_id, rings=tuple(list(ring) for ring in rings),
        floor_z=int(floor_z), ceiling_z=int(sky_z), floor_tile=int(floor_tile),
        ceiling_tile=int(sky_tile), wall_tile=int(wall_tile),
        kind=joins.PAVEMENT)


def end_wall(surface_id: str, rect: Sequence[int], *, road_floor_z: int,
             standing_height: int, sky_tile: int,
             facade_tile: int = joins.TILE_CLASSES["facade stone"]
             ) -> SurfaceSpec:
    """Where a street reaches the boundary and stops, in E3M1's dialect.

    The numbers come from `street.end_wall`, which measured s0, s339 and s343:
    3.86 to 5.80 player heights up, 5.80 to 7.73 of sky above that, floor 379,
    and blocking faces in the district's own stone.
    """
    from .street import end_wall as _record

    found = _record(_rect(*rect), road_floor_z=int(road_floor_z),
                    standing_height=int(standing_height),
                    facade_tile=int(facade_tile), sky_tile=int(sky_tile),
                    name=surface_id)
    return SurfaceSpec(
        surface_id=surface_id, rings=(found["outline"],),
        floor_z=found["floor_z"], ceiling_z=found["ceiling_z"],
        floor_tile=found["floor_picnum"],
        ceiling_tile=found["ceiling_picnum"], wall_tile=int(facade_tile),
        kind=joins.END_WALL, lit=False)


def waterfront(prefix: str, *, x0: int, x1: int, y: int, walk_depth: int,
               shore_depth: int, sea_depth: int, horizon_depth: int,
               pavement_z: int, sky_z_of, sky_tile: int) -> list:
    """Quay walk, shore, sea and horizon, in DWE3M10's dialect.

    Four surfaces and three joins. The shore stands one WALKABLE step below
    the walk -- 3072, inside Blood's 4096 autostep, which is DWE3M10's gentle
    case; its other seven landward records step 35840, and that is a quay wall
    rather than a shore. The sea meets the shore at equal z. The horizon is a
    zero-height sector at the sea's own z with the sky on BOTH surfaces and
    the parallax bit on both -- and the sky is the CITY's, because one
    connected outdoor space wears one sky.
    """
    shore_z = int(pavement_z) + joins.SHORE_STEP
    walk = _rect(x0, y - walk_depth, x1, y)
    shore = _rect(x0, y, x1, y + shore_depth)
    sea = _rect(x0, y + shore_depth, x1, y + shore_depth + sea_depth)
    horizon = _rect(x0, y + shore_depth + sea_depth,
                    x1, y + shore_depth + sea_depth + horizon_depth)
    return [
        island(f"{prefix}walk", (walk,), floor_z=int(pavement_z),
               sky_z=sky_z_of(int(pavement_z)), sky_tile=int(sky_tile)),
        SurfaceSpec(surface_id=f"{prefix}shore", rings=(shore,),
                    floor_z=shore_z, ceiling_z=sky_z_of(shore_z),
                    floor_tile=joins.SHORE_TILES[0], ceiling_tile=int(sky_tile),
                    wall_tile=joins.TILE_CLASSES["quay class"],
                    kind=joins.SHORE),
        SurfaceSpec(surface_id=f"{prefix}sea", rings=(sea,), floor_z=shore_z,
                    ceiling_z=sky_z_of(shore_z), floor_tile=joins.SEA_TILE,
                    ceiling_tile=int(sky_tile),
                    wall_tile=joins.TILE_CLASSES["quay class"],
                    kind=joins.SEA,
                    finish={"floor_pal": joins.SEA_PALETTE},
                    behavior={"pan_floor": 1, "pan_always": 1, "drag": 1,
                              "pan_velocity": joins.SEA_PAN_VELOCITY,
                              "pan_angle": joins.SEA_PAN_ANGLE}),
        SurfaceSpec(surface_id=f"{prefix}horizon", rings=(horizon,),
                    floor_z=shore_z, ceiling_z=shore_z,
                    floor_tile=int(sky_tile), ceiling_tile=int(sky_tile),
                    wall_tile=int(sky_tile), kind=joins.HORIZON,
                    floor_stat=1, lit=False, declared_zero_exit=True),
    ]


def facade(surface_id: str, rect: Sequence[int], inner: Sequence[int],
           door: Sequence[int], *, roof_z: int, sky_z: int, sky_tile: int,
           wall_tile: int) -> SurfaceSpec:
    """A shell's wall, as ONE simple polygon cut open at its door.

    Not a rectangle with a hole: the doorway reaches the outside, so the room
    is not enclosed by the wall and a hole would TOUCH the outer ring at the
    mouth. That shape is degenerate, and `PlanarLayout` says so.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    ix0, iy0, ix1, iy1 = (int(v) for v in inner)
    dx0, dx1 = int(door[0]), int(door[2])
    ring = [(x0, y0), (x1, y0), (x1, y1), (dx1, y1), (dx1, iy1),
            (ix1, iy1), (ix1, iy0), (ix0, iy0), (ix0, iy1),
            (dx0, iy1), (dx0, y1), (x0, y1)]
    return SurfaceSpec(
        surface_id=surface_id, rings=(ring,), floor_z=int(roof_z),
        ceiling_z=int(sky_z), floor_tile=ROOF_TILE, ceiling_tile=int(sky_tile),
        wall_tile=int(wall_tile), kind=joins.FACADE, lit=False)


def opening(surface_id: str, rect: Sequence[int], *, floor_z: int,
            head_z: int, wall_tile: int, floor_tile: int = PAVEMENT_TILE,
            ceiling_tile: int = INTERIOR_CEILING, sector_type: int = 0,
            lod: int = 2, behavior: dict | None = None,
            role: str = "opening") -> SurfaceSpec:
    """A void in a facade, as a sector of its own.

    P13's law, and the reason this is a sector rather than a wall band: a
    material with its own scale needs a record no other surface uses. The
    facade's run crosses the mouth above it; nothing of the facade's frame
    touches these records.
    """
    return SurfaceSpec(
        surface_id=surface_id, rings=(_rect(*rect),), floor_z=int(floor_z),
        ceiling_z=int(head_z), floor_tile=int(floor_tile),
        ceiling_tile=int(ceiling_tile), wall_tile=int(wall_tile),
        kind=joins.OPENING, role=str(role), parallax_ceiling=False,
        lit=False, lod=int(lod), sector_type=int(sector_type),
        behavior=dict(behavior or {}))


def room(surface_id: str, rect: Sequence[int], *, floor_z: int,
         ceiling_z: int, wall_tile: int, floor_tile: int = INTERIOR_FLOOR,
         ceiling_tile: int = INTERIOR_CEILING, lod: int = 1,
         role: str = "gated_pocket") -> SurfaceSpec:
    """The space behind a facade. Not ground: the sun does not reach it.

    Its ROLE is `gated_pocket`, which is the truth about a room behind a shut
    door: its only way in is a mechanism, so it has no walkable-at-rest portal
    and the geometry audit is told that rather than being silenced.

    The floor and the ceiling wear FLOOR and CEILING classes. E3M1's own
    interior is `materials.INTERIORS["common"]` -- floor 304, ceiling 454 --
    and a wall tile on a horizontal surface is a fault by sector, which is
    what the owner found on one of them.
    """
    return SurfaceSpec(
        surface_id=surface_id, rings=(_rect(*rect),), floor_z=int(floor_z),
        ceiling_z=int(ceiling_z), floor_tile=int(floor_tile),
        ceiling_tile=int(ceiling_tile), wall_tile=int(wall_tile),
        kind=joins.INTERIOR, role=str(role), parallax_ceiling=False,
        lit=False, lod=int(lod))


#: A curtain's leaf: `conformance.CURTAIN`'s own numbers. One flagged tip or
#: two carrying opposite flags, and the deformation is only visible on the
#: fabric, so the leaf wears 146 and not the wall it hangs in.
CURTAIN_FABRIC = 146
DRAG_FORWARD = 0x4000
#: MASKED. `engine.cpp:4938-4940` draws a two-sided wall's middle band only
#: when it is masked or one-way; unmasked, the fabric shows on the step bands
#: and nowhere a body walks -- which is what `conformance.measure_curtain`
#: says when it counts 0 visible fabric walls.
MASKED = 16


def insert(surface: str, *, holder: str, room_id: str, void: Sequence,
           kind: str = "curtain", sector_type: int = 0, lod: int = 2,
           wiring: Iterable[dict] = (), key: int | None = None,
           key_realised: bool = False, key_why: str = "",
           leaf: dict | None = None) -> dict:
    """What fills an opening: the declaration, not the geometry.

    Two facts come out of this and they are two different claims. `void` says
    the facade has a hole here and names the holder it belongs to; `fill` says
    what is in it. A link whose tx nobody carries is written with
    `realised: false` rather than being quietly absent.
    """
    return {"kind": str(kind), "surface": str(surface), "holder": str(holder),
            "room": str(room_id), "void": [list(point) for point in void],
            "sector_type": int(sector_type), "lod": int(lod),
            "wiring": [dict(row) for row in wiring],
            "key": key, "key_realised": bool(key_realised),
            "key_why": str(key_why),
            "leaf": dict(leaf) if leaf else None}


#: THE SWITCH, measured. Of the campaign's 20/21 switch sprites the commonest
#: wall-aligned tile is 1070 -- 104 as kSwitchToggle and 78 as kSwitchOneWay
#: -- and they hang a median 5120 above their floor, which is 0.30 of a body.
SWITCH_TILE = 1070
SWITCH_TYPE = 20
SWITCH_HEIGHT = 5120
#: THE KEYS. Blood's five key pickups are types 100..104 wearing 2552..2556,
#: and its sixth is 105/2557; the campaign uses them 29, 11, 19, 10 and 8
#: times. Key n is type 99 + n.
KEY_TYPE_BASE = 99
KEY_TILE_BASE = 2551
#: A MARKED SLIDE NAMES ITS TWO POSITIONS BY SPRITE INDEX, and a sprite has
#: no index until the layout has compiled -- but the sweep validator runs
#: DURING that compile and refuses a 614 with no marker0. `kSectorSlideMarked`
#: therefore needs a first-class constructor that declares its markers as part
#: of the layout, which this pipeline does not yet have.
#:
#: A street door that RISES needs no markers: type 600, kSectorZMotion, with
#: its two ceiling heights. So a shopfront's door is a shutter, and the
#: construct changes name honestly rather than the mechanism being faked.
#: `doors.z_motion_door` is the campaign-backed behaviour, five tenths of a
#: second each way.
Z_MOTION = 600


def _leaf_for(sector_type: int) -> dict:
    """What the mouth's own record wears, and whether anything drags it.

    A Z-MOTION DOOR DEFORMS NOTHING. It moves its ceiling from one z to
    another and no point in the map travels, so a wall flagged 0x4000 on one
    is a claim the mechanism never makes -- and `DragPoint` believes it: the
    flag walked the ring out of the door, through the vertex the weld made it
    share with the pavement, and reported a motion set of six walls in three
    sectors for a thing that moves a plane.

    That was slice 4's one remaining read-back difference, and its cause was
    not the weld. The leaf stays MASKED and wearing the fabric, because
    `engine.cpp:4938-4940` draws a two-sided wall's middle band only when it
    is masked or one-way; it is simply not dragged.
    """
    flags = MASKED if int(sector_type) == Z_MOTION else MASKED | DRAG_FORWARD
    return {"tile": CURTAIN_FABRIC, "flags": flags,
            "over_picnum": CURTAIN_FABRIC, "faces": joins.PAVEMENT,
            "drags": bool(flags & DRAG_FORWARD)}


def switch(prop_id: str, point: Point, *, tx_id: int, height: int = SWITCH_HEIGHT
           ) -> dict:
    """A wall switch, on the facade beside the thing it works.

    It carries the tx; the mechanism carries the matching rx. Until both
    exist the link is a declaration and says so.
    """
    #: `triggers.cpp:102-104` gates every message on the send-when bit of the
    #: state being ENTERED. Without `trigger_on` a tx is a number nobody ever
    #: transmits, and nine of this city's switches carried exactly that.
    return {"prop_id": str(prop_id), "point": (int(point[0]), int(point[1])),
            "tile": SWITCH_TILE, "sprite_type": SWITCH_TYPE, "cstat": MASKED,
            "shade": -8, "height": int(height), "mount": "wall",
            "solid_only": True,
            "xsprite": {"tx_id": int(tx_id), "trigger_push": 1,
                        "trigger_on": 1, "command": 1, "state": 0}}


def key_pickup(prop_id: str, point: Point, *, key: int,
               height: int = 0) -> dict:
    """One of Blood's five keys, on the floor where the circuit passes."""
    if not 1 <= int(key) <= 6:
        raise ValueError(f"Blood has six keys; {key} is not one of them")
    return {"prop_id": str(prop_id), "point": (int(point[0]), int(point[1])),
            "tile": KEY_TILE_BASE + int(key),
            "sprite_type": KEY_TYPE_BASE + int(key), "cstat": 0,
            "shade": -8, "height": int(height), "mount": "free",
            "statnum": 3, "xsprite": {"key": int(key)}}


def shell(key: str, rect: Sequence[int], *, wall_thickness: int,
          door_width: int, roof_z: int, floor_z: int, interior_z: int,
          head_z: int, sky_z: int, sky_tile: int, wall_tile: int,
          sector_type: int = 0, wiring: Iterable[dict] = (),
          gate_key: int | None = None, key_why: str = "") -> tuple:
    """A building: facade, opening, insert and room, from one rectangle.

    The mouth is on the SOUTH face, which is the one the sun lights and the
    street sees, and which `city_plan.ENVELOPES` faces its venues towards.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    inner = (x0 + wall_thickness, y0 + wall_thickness,
             x1 - wall_thickness, y1 - wall_thickness)
    mid = (x0 + x1) // 2
    door = (mid - door_width // 2, inner[3], mid + door_width // 2, y1)
    #: THE DOOR CARRIES THE RX. A mechanism that answers a channel says so in
    #: its own XSECTOR; without that the switch's tx reaches nobody, and the
    #: link is a sentence about two things that have never met.
    channel = next((int(row.get("rx_id") or row.get("channel") or 0)
                    for row in wiring), 0)
    from .doors import z_motion_door

    behavior = {}
    if sector_type == Z_MOTION:
        behavior = z_motion_door(
            int(floor_z), int(head_z),
            interaction="both" if channel else "direct",
            rx_id=channel or None, key=gate_key)
    elif channel:
        behavior = {"rx_id": channel}
        if gate_key:
            behavior["key"] = int(gate_key)
    surfaces = [
        facade(f"shell:{key}", (x0, y0, x1, y1), inner, door, roof_z=roof_z,
               sky_z=sky_z, sky_tile=sky_tile, wall_tile=wall_tile),
        room(f"interior:{key}", inner, floor_z=floor_z, ceiling_z=interior_z,
             wall_tile=wall_tile),
        opening(f"door:{key}", door, floor_z=floor_z, head_z=head_z,
                wall_tile=wall_tile, sector_type=sector_type,
                behavior=behavior),
    ]
    #: THE LEAF. A sector type alone is not a curtain: `drag_closure` finds
    #: nothing to drag and `conformance.measure_curtain` says so in two
    #: sentences -- "found 0 leaves" and "fabric: wanted 146". The leaf is the
    #: record at the mouth, flagged and wearing the fabric.
    declaration = insert(f"door:{key}", holder=f"shell:{key}",
                         kind="z_motion_door" if sector_type == Z_MOTION
                         else "curtain",
                         room_id=f"interior:{key}", void=_rect(*door),
                         sector_type=sector_type, wiring=wiring,
                         key=gate_key, key_why=key_why,
                         leaf=_leaf_for(sector_type))
    #: THE SWITCH, on the facade beside the mouth -- half a door's width
    #: clear of the jamb, on the pavement the door opens onto.
    props = []
    if channel:
        props.append(switch(f"switch:{key}",
                            (door[2] + door_width // 2, y1 - 1),
                            tx_id=channel))
    #: THE KEY, out on the circuit rather than beside the lock. A key at its
    #: own door is a formality; the point of a gate is that the key is
    #: somewhere else.
    if gate_key:
        props.append(key_pickup(f"key:{key}",
                                ((x0 + x1) // 2, y1 + 3 * 1024),
                                key=int(gate_key)))
    if props:
        declaration["props"] = props
    return surfaces, declaration


# ---------------------------------------------------------------------------
# dressing: props stand on something, and the something is anchored to a record
# ---------------------------------------------------------------------------

#: A PLINTH IS WAIST-HIGH AND ELONGATED, and both numbers are the reader's.
#: `anchors.find_bundles` recovers a raised island only when its rise is more
#: than the 4096 step limit and no more than half a body (8192) -- of 958
#: campaign blocking islands that band holds the largest mass, 38.3% -- and
#: only when its footprint is at least twice as long as it is deep, because a
#: square blocking island is a pillar and a counter is a run you stand along.
#: 6144 is E6M1's owner-identified cashwrap, in the middle of the band.
PLINTH_RISE = 6144
PLINTH_DEPTH = 2048
PLINTH_MIN_ASPECT = 2.0
#: What a plinth wears. E3M1's facade family again: a counter in a Blood room
#: is built of the room's own stone.
PLINTH_TILE = 401


def _screen_area(ring: Sequence) -> float:
    """Twice the signed area in Build's screen space (+Y down).

    `planar_geom.validate_loop` is exact about the sign: an outer loop is
    POSITIVE and a hole NEGATIVE, and it refuses either the wrong way round.
    """
    total = 0.0
    for index, here in enumerate(ring):
        nxt = ring[(index + 1) % len(ring)]
        total += here[0] * nxt[1] - nxt[0] * here[1]
    return total


class DressingError(ValueError):
    """A bundle that would not come back as one."""


def dressing(anchor: Sequence, props: Sequence[dict], *, inward: Point,
             floor_z: int, ceiling_z: int, surface_id: str,
             spread: float = 0.6, facing: str = "out",
             depth: int = PLINTH_DEPTH, rise: int = PLINTH_RISE,
             tile: int = PLINTH_TILE, lod: int = 3) -> dict:
    """A bundle of unwired sprites, placed against an ANCHOR RECORD.

    Never by absolute coordinate. `anchor` is an edge of the host surface --
    two points the solver placed -- and everything here is an offset from it:
    the plinth is centred on that edge, `spread` of its length, `depth` into
    the room, and the props stand along the plinth's top.

    That is what makes it come back. `anchors.find_bundles` recovers a bundle
    from geometry and never from proximity: one outer neighbour, a floor
    raised out of the host by more than a step, an elongated footprint, and at
    least one visible prop. A handful of sprites dropped at coordinates has
    none of those and comes back as nothing -- which is the whole difference
    between dressing a room and scattering in one.

    Returns the plinth's surface, the hole its host must carry, and the props.
    """
    (ax, ay), (bx, by) = (tuple(anchor[0]), tuple(anchor[1]))
    length = math.hypot(bx - ax, by - ay)
    if not length:
        raise DressingError(f"{surface_id}: an anchor record of zero length")
    run = max(int(round(length * float(spread))), 1)
    if run < depth * PLINTH_MIN_ASPECT:
        raise DressingError(
            f"{surface_id}: a plinth {run} long and {depth} deep has aspect "
            f"{run / depth:.2f}; `anchors.find_bundles` wants at least "
            f"{PLINTH_MIN_ASPECT}, because a square blocking island is a "
            f"pillar and a counter is a run you stand along")
    if not 4096 < rise <= 8192:
        raise DressingError(
            f"{surface_id}: a rise of {rise} is not waist height; a bundle is "
            f"recovered between 4096 and 8192 and nowhere else")

    #: the unit vectors of the record and of the room behind it
    ux, uy = (bx - ax) / length, (by - ay) / length
    span = math.hypot(inward[0], inward[1]) or 1.0
    nx, ny = inward[0] / span, inward[1] / span
    #: THE PLINTH IS OFF THE WALL BY ITS OWN DEPTH, so its only neighbour is
    #: the host: flush against the record it would share that record's far
    #: side too, and `find_bundles` counts two outer neighbours and refuses.
    mid = ((ax + bx) / 2.0, (ay + by) / 2.0)
    base = (mid[0] + nx * depth, mid[1] + ny * depth)
    half = run / 2.0
    corners = []
    for along, out in ((-half, 0), (half, 0), (half, depth), (-half, depth)):
        corners.append((int(round(base[0] + ux * along + nx * out)),
                        int(round(base[1] + uy * along + ny * out))))

    #: BOTH WINDINGS ARE THE VALIDATOR'S, and it refuses either the wrong way
    #: round: an outer loop is POSITIVE in Build's screen space and a hole
    #: NEGATIVE. The plinth's ring is built in the anchor record's own
    #: direction, which may be either, so both are normalised rather than
    #: assumed.
    if _screen_area(corners) < 0:
        corners.reverse()
    top = int(floor_z) - int(rise)
    surface = SurfaceSpec(
        surface_id=surface_id, rings=(corners,), floor_z=top,
        ceiling_z=int(ceiling_z), floor_tile=INTERIOR_FLOOR,
        ceiling_tile=INTERIOR_CEILING, wall_tile=int(tile),
        kind=joins.INTERIOR, role="gated_pocket", parallax_ceiling=False,
        lit=False, lod=int(lod))

    #: the props, spread along the plinth's own centre line
    angle = int(round(math.atan2(-ux, uy) * 2048 / (2 * math.pi))) % 2048
    if facing == "in":
        angle = (angle + 1024) % 2048
    placed = []
    count = max(1, len(props))
    for index, prop in enumerate(props):
        share = (index + 0.5) / count - 0.5
        point = (int(round(base[0] + ux * run * share + nx * depth / 2)),
                 int(round(base[1] + uy * run * share + ny * depth / 2)))
        placed.append({**prop, "point": point, "angle": angle,
                       "prop_id": f"{surface_id}:{prop.get('name', index)}",
                       "mount": "free", "height": 0})
    #: THE HOLE'S WINDING IS THE HOST'S PROBLEM, and `PlanarLayout` is exact
    #: about it: a hole loop must run counter-clockwise in Build's screen
    #: space. The plinth's own ring is built in the anchor's direction, which
    #: may be either way round, so the hole is normalised rather than assumed.
    hole = list(reversed(corners))
    return {"surface": surface, "hole": hole,
            "props": placed, "anchor": (tuple(anchor[0]), tuple(anchor[1])),
            "rise": int(rise), "aspect": run / depth}


def prop(name: str, *, shade: int = -8, statnum: int = 0) -> dict:
    """One named prop, by the campaign's own word for its tile.

    `read_intent.named_props` counts a sprite only when `furniture.FURNITURE`
    has a name for its tile and `blood_types.sprite_visibility` calls it
    visible -- a tile nobody has named contributes nothing, and about a
    quarter of a campaign map's sprites are wiring nobody sees.
    """
    from .furniture import FURNITURE

    item = FURNITURE.get(name)
    if item is None:
        raise DressingError(
            f"{name!r} is not a name the campaign uses. `furniture.FURNITURE` "
            f"supplies the word, and a tile nobody has named cannot be read "
            f"back")
    return {"name": str(name), "tile": int(item.picnum), "cstat": 0,
            "shade": int(shade), "sprite_type": 0, "statnum": int(statnum)}


def shell_of_rooms(key: str, rect: Sequence[int], rooms: Sequence[dict], *,
                   wall_thickness: int, door_width: int, roof_z: int,
                   floor_z: int, head_z: int, sky_z: int, sky_tile: int,
                   wall_tile: int, entry: str, sector_type: int = 0,
                   wiring: Iterable[dict] = (), gate_key: int | None = None,
                   key_why: str = "") -> tuple:
    """A building whose interior is ROOMS CUT OUT OF SOLID STONE.

    `shell` gives a building one room, and one room is a box. A building with
    eight is not eight boxes in a row: it is a mass with rooms taken out of
    it, and the stone that is left between them is the thing that makes a
    nave read as a nave and a vestry as a vestry.

    So the facade is not a ring around one rectangle any more. It is the
    shell's footprint MINUS the rooms and minus the door, traced by
    `overlay.ground_plane_rings`, which already does exactly this for the
    street plane and its blocks -- a mass with holes in it is a plane with
    blocks on it, one level up and inside out.

    `rooms` are dicts of `{name, rect, clear, tile, rise}` in coordinates
    relative to the shell's INNER origin, so a floor plan survives being moved
    and being re-solved. `entry` names the room the street door reaches; the
    door notch runs from the shell's south face to that room's south edge,
    through whatever stone is between.
    """
    from .overlay import ground_plane_rings

    x0, y0, x1, y1 = (int(v) for v in rect)
    inner = (x0 + wall_thickness, y0 + wall_thickness,
             x1 - wall_thickness, y1 - wall_thickness)
    plan = {row["name"]: [int(v) for v in row["rect"]] for row in rooms}
    if entry not in plan:
        raise DressingError(f"{key}: the entry room {entry!r} is not in the "
                            f"plan")
    span_x = max(r[2] for r in plan.values()) - min(r[0] for r in plan.values())
    span_y = max(r[3] for r in plan.values()) - min(r[1] for r in plan.values())
    if span_x > inner[2] - inner[0] or span_y > inner[3] - inner[1]:
        raise DressingError(
            f"{key}: a plan {span_x}x{span_y} does not fit an interior "
            f"{inner[2] - inner[0]}x{inner[3] - inner[1]}")
    low_x = min(r[0] for r in plan.values())
    low_y = min(r[1] for r in plan.values())
    #: THE ENTRY ROOM IS CENTRED ON THE MOUTH, and the plan's south edge sits
    #: on the interior's, so a door in the middle of the street face reaches
    #: the room that is meant to receive it.
    mid = (x0 + x1) // 2
    entry_mid = (plan[entry][0] + plan[entry][2]) // 2 - low_x
    offset_x = mid - inner[0] - entry_mid
    offset_x = max(0, min(offset_x, (inner[2] - inner[0]) - span_x))
    offset_y = (inner[3] - inner[1]) - span_y

    def place(box):
        return (inner[0] + offset_x + box[0] - low_x,
                inner[1] + offset_y + box[1] - low_y,
                inner[0] + offset_x + box[2] - low_x,
                inner[1] + offset_y + box[3] - low_y)

    placed = {name: place(box) for name, box in plan.items()}
    #: THE MOUTH IS WHERE THE ROOM IT SERVES IS. Centring it on the shell
    #: instead put the notch through the nave whenever the plan had to be
    #: clamped to fit, and a door that opens into the wrong room is worse
    #: than one that is off centre.
    door_mid = (placed[entry][0] + placed[entry][2]) // 2
    #: AND IT IS NO WIDER THAN THE ROOM IT SERVES. A 4096 mouth on a 1536
    #: narthex spills over the nave beside it, and the compiler reads that
    #: as two regions overlapping -- correctly, because they do.
    width = min(int(door_width), placed[entry][2] - placed[entry][0])
    door = (door_mid - width // 2, placed[entry][3],
            door_mid + width // 2, y1)

    rings = ground_plane_rings([[x0, y0, x1, y1]],
                               holes=list(placed.values()) + [list(door)])
    channel = next((int(row.get("rx_id") or row.get("channel") or 0)
                    for row in wiring), 0)
    from .doors import z_motion_door

    behavior = {}
    if sector_type == Z_MOTION:
        behavior = z_motion_door(
            int(floor_z), int(head_z),
            interaction="both" if channel else "direct",
            rx_id=channel or None, key=gate_key)
    elif channel:
        behavior = {"rx_id": channel}

    surfaces = [SurfaceSpec(
        surface_id=f"shell:{key}", rings=tuple(rings), floor_z=int(roof_z),
        ceiling_z=int(sky_z), floor_tile=ROOF_TILE,
        ceiling_tile=int(sky_tile), wall_tile=int(wall_tile),
        kind=joins.FACADE, lit=False)]
    for row in rooms:
        box = placed[row["name"]]
        rise = int(row.get("rise", 0))
        surfaces.append(room(
            f"room:{key}:{row['name']}", box, floor_z=int(floor_z) - rise,
            ceiling_z=int(floor_z) - rise - int(row["clear"]),
            wall_tile=int(row.get("tile", wall_tile))))
    surfaces.append(opening(
        f"door:{key}", door, floor_z=int(floor_z), head_z=int(head_z),
        wall_tile=int(wall_tile), sector_type=int(sector_type),
        behavior=behavior))
    declaration = insert(
        f"door:{key}", kind="z_motion_door" if sector_type == Z_MOTION
        else "curtain", holder=f"shell:{key}",
        room_id=f"room:{key}:{entry}", void=_rect(*door),
        sector_type=int(sector_type), wiring=wiring, key=gate_key,
        key_why=key_why, leaf=_leaf_for(sector_type))
    if channel:
        declaration["props"] = [switch(
            f"switch:{key}", (door[2] + door_width // 2, y1 - 1),
            tx_id=channel)]
        if gate_key:
            declaration["props"].append(key_pickup(
                f"key:{key}", (door_mid, y1 + 3 * 1024), key=int(gate_key)))
    return surfaces, declaration, placed


#: The campaign's door width, across the middle half of 1231 type-600
#: sectors in 43 maps.
DOOR_WIDTH_ENVELOPE = (768, 2048)

#: A STEPPED RUN IS THREE RISES OR MORE. `structures._detect_stepped_runs`
#: takes a maximal monotone climb in the sub-step rise graph and wants at
#: least three of them; two steps are a threshold and a kerb, not a stair.
MIN_RISES = 3


def stair(from_: Sequence, to: Sequence, *, treads: int, width: int,
          clear_height: int, surface_id: str, tile: int = PLINTH_TILE,
          floor_tile: int = 304, lod: int = 1) -> dict:
    """A stepped run between two landings, and ONE surface owns its flank.

    `from_` and `to` are `(edge, floor_z)`: two parallel records the solver
    placed, the foot and the head. The treads divide the gap between them
    evenly and the rise divides the drop evenly, so a stair is stated as its
    two ends and its count -- never as a list of boxes, which is what makes
    it survive a landing moving.

    THE FLANK IS ONE SURFACE. Every tread's side records wear one material
    and carry one projection across the whole run, which is what
    `read_surfaces` means by explained: a record whose u-origin fits no
    neighbour's frame is residue, and a run that restarts its panning at every
    tread is the commonest way to make some.
    """
    if int(treads) < MIN_RISES:
        raise DressingError(
            f"{surface_id}: {treads} treads is not a stepped run; "
            f"`structures` wants at least {MIN_RISES} rises, because two "
            f"steps are a threshold and a kerb")
    (ax, ay), (bx, by) = tuple(from_[0][0]), tuple(from_[0][1])
    (cx, cy), (dx, dy) = tuple(to[0][0]), tuple(to[0][1])
    foot_z, head_z = int(from_[1]), int(to[1])
    surfaces = []
    count = int(treads)
    for index in range(count):
        low, high = index / count, (index + 1) / count
        ring = [
            (int(round(ax + (cx - ax) * low)), int(round(ay + (cy - ay) * low))),
            (int(round(bx + (dx - bx) * low)), int(round(by + (dy - by) * low))),
            (int(round(bx + (dx - bx) * high)), int(round(by + (dy - by) * high))),
            (int(round(ax + (cx - ax) * high)), int(round(ay + (cy - ay) * high))),
        ]
        if _screen_area(ring) < 0:
            ring.reverse()
        floor_z = foot_z + int(round((head_z - foot_z) * (index + 0.5) / count))
        surfaces.append(SurfaceSpec(
            surface_id=f"{surface_id}:{index:02d}", rings=(ring,),
            floor_z=floor_z, ceiling_z=floor_z - int(clear_height),
            floor_tile=int(floor_tile), ceiling_tile=INTERIOR_CEILING,
            wall_tile=int(tile), kind=joins.INTERIOR, role="gated_pocket",
            parallax_ceiling=False, lit=False, lod=int(lod)))
    rise = abs(head_z - foot_z) // count
    return {"surfaces": surfaces, "rises": count, "rise": rise,
            "width": int(width), "flank_tile": int(tile),
            "foot_z": foot_z, "head_z": head_z}


# ---------------------------------------------------------------------------
# a building is a VOID in the pavement, not a sector standing on it
# ---------------------------------------------------------------------------

#: THE CAMPAIGN'S Z-MOTION DOOR, over 1231 type-600 sectors in 43 maps: the
#: long side runs 768 to 2048 across the middle half, median 1024, and the
#: short side is 256 on 339 of them, the commonest by a distance. E3M1's own
#: six are 256 to 1024 long, 256 thick but for s114's 128, and CLOSED AT REST
#: -- ceiling on floor, all six -- with no masked record between them.
DOOR_WIDTH = 1024
DOOR_THICKNESS = 256
#: What one opens to: the LINTEL, never the roof. E3M1's four that move travel
#: 16384, 17408, 18432 and 22528; the campaign's quartiles are 16384 and
#: 30720, and `l3_church` measured a median open height of 31744 over 1269 of
#: them. 30720 is the campaign's own q3 and 1.81 player heights.
DOOR_TRAVEL = 30720
#: How deep the reveal is: whatever is left of the wall once the door has its
#: 256. E6M1's shopfront recess is 512 deep, so a 1024 wall gives 768 and a
#: 512 wall gives 256, both inside that dialect.


def building(key: str, rect: Sequence[int], rooms: Sequence[dict], *,
             wall_thickness: int, floor_z: int, sky_tile: int,
             facade_tile: int, entry: str, door_width: int = DOOR_WIDTH,
             door_thickness: int = DOOR_THICKNESS,
             travel: int = DOOR_TRAVEL, sector_type: int = 0,
             wiring: Iterable[dict] = (), gate_key: int | None = None,
             key_why: str = "") -> tuple:
    """A building: a VOID in the pavement with rooms inside it.

    THE MODEL CHANGED HERE, and the engine is why. A shell built as a SECTOR
    has a real ceiling, and `engine.cpp:4688` says an upper wall clips the
    view -- raises `umost` to the far ceiling line -- whenever one of the two
    ceilings is not parallaxed. So a roof-height slab beside the street cuts
    off everything above it behind, which is what the owner saw at every
    doorway. Sky against sky never clips, whatever the step: E3M1 has 13
    differing sky|sky pairs and no visible cut.

    E3M1's buildings are not sectors. Its facades ARE the one-sided records of
    its outdoor sectors -- 122 of them -- and the stone between its rooms is
    simply absent from the map. So a building here is a HOLE in the island,
    with the rooms as sectors inside it, the wall as the space between them
    that no sector fills, and the facade as the island's own hole-ring
    records, which are one-sided because there is nothing on the other side.

    The mouth follows E3M1's envelope: a `door_width` opening in the facade,
    a reveal taking the rest of the wall's depth, and the door itself
    `door_thickness` deep against the room, CLOSED at rest with its ceiling on
    its floor, opening to its lintel.

    Returns `(hole_ring, surfaces, declaration, placed)`.
    """
    from .doors import z_motion_door
    from .overlay import ground_plane_rings

    x0, y0, x1, y1 = (int(v) for v in rect)
    inner = (x0 + wall_thickness, y0 + wall_thickness,
             x1 - wall_thickness, y1 - wall_thickness)
    plan = {row["name"]: [int(v) for v in row["rect"]] for row in rooms}
    if entry not in plan:
        raise DressingError(f"{key}: the entry room {entry!r} is not in the "
                            f"plan")
    low_x = min(r[0] for r in plan.values())
    low_y = min(r[1] for r in plan.values())
    span_x = max(r[2] for r in plan.values()) - low_x
    span_y = max(r[3] for r in plan.values()) - low_y
    if span_x > inner[2] - inner[0] or span_y > inner[3] - inner[1]:
        raise DressingError(
            f"{key}: a plan {span_x}x{span_y} does not fit an interior "
            f"{inner[2] - inner[0]}x{inner[3] - inner[1]}")
    offset_x = max(0, min((inner[2] - inner[0]) - span_x,
                          (x0 + x1) // 2 - inner[0]
                          - ((plan[entry][0] + plan[entry][2]) // 2 - low_x)))
    offset_y = (inner[3] - inner[1]) - span_y

    def place(box):
        return (inner[0] + offset_x + box[0] - low_x,
                inner[1] + offset_y + box[1] - low_y,
                inner[0] + offset_x + box[2] - low_x,
                inner[1] + offset_y + box[3] - low_y)

    placed = {name: place(box) for name, box in plan.items()}
    room_box = placed[entry]
    width = min(int(door_width), room_box[2] - room_box[0])
    if width < DOOR_WIDTH_ENVELOPE[0]:
        raise DressingError(
            f"{key}: a mouth {width} across is narrower than any door the "
            f"campaign builds ({DOOR_WIDTH_ENVELOPE[0]} at the first "
            f"quartile of 1231)")
    mid = (room_box[0] + room_box[2]) // 2
    #: THE DOOR IS AGAINST THE ROOM and the reveal takes the rest of the wall.
    door = (mid - width // 2, room_box[3],
            mid + width // 2, room_box[3] + int(door_thickness))
    reveal = (door[0], door[3], door[2], y1)
    if reveal[1] >= reveal[3]:
        raise DressingError(f"{key}: the wall is thinner than its own door")

    #: The island's hole is the footprint; the reveal's mouth lies on its
    #: south edge and becomes the one two-sided record in it.
    hole = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
    if _screen_area(hole) > 0:
        hole.reverse()

    channel = next((int(row.get("rx_id") or row.get("channel") or 0)
                    for row in wiring), 0)
    shut = int(floor_z)
    open_to = int(floor_z) - int(travel)
    behavior = {}
    if sector_type == Z_MOTION:
        behavior = z_motion_door(shut, open_to,
                                 interaction="both" if channel else "direct",
                                 rx_id=channel or None, key=gate_key)
    elif channel:
        behavior = {"rx_id": channel}

    surfaces = []
    for row in rooms:
        box = placed[row["name"]]
        rise = int(row.get("rise", 0))
        surfaces.append(room(
            f"room:{key}:{row['name']}", box, floor_z=int(floor_z) - rise,
            ceiling_z=int(floor_z) - rise - int(row["clear"]),
            wall_tile=int(row.get("tile", facade_tile))))
    #: The reveal is the head of the opening, at the lintel.
    #: THE REVEAL IS PART OF THE MOUTH, not a room: it is the depth of the
    #: opening between the street and the leaf, which is what E6M1's 512-deep
    #: shopfront recess is.
    surfaces.append(opening(
        f"reveal:{key}", reveal, floor_z=int(floor_z), head_z=open_to,
        wall_tile=int(facade_tile), floor_tile=PAVEMENT_TILE,
        ceiling_tile=INTERIOR_CEILING, lod=2, role="doorway"))
    #: THE DOOR, SHUT: its ceiling is on its floor and it opens to the lintel.
    surfaces.append(opening(
        f"door:{key}", door, floor_z=int(floor_z), head_z=int(floor_z),
        wall_tile=int(facade_tile), sector_type=int(sector_type),
        behavior=behavior))

    declaration = insert(
        f"door:{key}", kind="z_motion_door" if sector_type == Z_MOTION
        else "curtain", holder=f"island:{key}",
        room_id=f"room:{key}:{entry}", void=_rect(*door),
        sector_type=int(sector_type), wiring=wiring, key=gate_key,
        key_why=key_why, leaf=None)
    if channel:
        #: THE SWITCH IS IN THE PAVEMENT, beside the mouth, on the facade's
        #: own one-sided record -- `triggers.cpp:102-104` needs the send-when
        #: bit and a body needs to be standing somewhere to press it.
        declaration["props"] = [switch(
            f"switch:{key}", (door[2] + width, y1 + 512), tx_id=channel)]
        if gate_key:
            declaration["props"].append(key_pickup(
                f"key:{key}", (mid, y1 + 3 * 1024), key=int(gate_key)))
    return hole, surfaces, declaration, placed
