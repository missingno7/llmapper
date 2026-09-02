"""What a mechanism physically does, said neutrally.

A **reading** over what `doors.py`, `assembly.py` and `motion_sim.py` already
record — not a parallel framework and not a catalog of named prefabs. Nothing
here re-derives geometry; every number comes from `observe_motion_sector` or
`assembly_around`.

The reading is factored along five planes, and keeping them apart is the whole
point:

1. **primitive** — what the engine physically does: a surface moves in z, a
   sector translates, a sector turns about an axis. Engine fact, no meaning.
2. **carried** — what rides the motion, and how it is attached.
   `assembly.py`'s domain.
3. **embedding** — where it sits: what the motion does to occupancy and
   reachability. **This is where meaning is born.**
4. **style** — how the thing is made readable: a face unlike its surround, a
   signifier beside it, see-through leaves.
5. **transmission** — what the mechanism DRIVES. Not a property of the sector
   at all: it lives in the pair, and the only field carrying it is `command`.

**The name of a mechanism is assigned from the embedding, never from the
fields.** That is not a preference, it is a measurement: across the 43
campaign maps, 122 sectors whose *floor* moves change what fits through a
portal, and 102 whose *ceiling* moves change nothing at all. A namer reading
the type and the moving surface gets 471 of 1179 wrong -- 40%. The same holds
one family over: 88 instances of the auto-rotating primitive, only 6 are doors
— the rest are a carnival ride, station rotors and fans, decided by space and
never by fields (`projects/blood-city/references/auto-rotators.md`).

So `design_object` below takes the embedding and nothing else, and it is
deliberately impossible to call it with a sector type.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from .doors import (
    PLAYER_HEIGHT, ROTATE_TYPES, SLIDE_TYPES, Z_MOTION_TYPES,
    _wall_owners, observe_motion_sector,
)
from .player_space import PLAYER_PROFILES

SCHEMA = "llmapper.blood-effects"
SCHEMA_VERSION = 1

#: The physical primitives. Deliberately few, deliberately dumb, and named for
#: what the engine does rather than for what a player would call it.
MOVE_FLOOR_Z = "move_floor_z"
MOVE_CEILING_Z = "move_ceiling_z"
TRANSLATE_XY = "translate_xy"
ROTATE_ABOUT_AXIS = "rotate_about_axis"
EFFECTS = (MOVE_FLOOR_Z, MOVE_CEILING_Z, TRANSLATE_XY, ROTATE_ABOUT_AXIS)

#: NBlood's ClipMove step-up limit: the height a walking body climbs without
#: jumping. Two floors further apart than this are two standing levels, and
#: something has to carry a body between them.
STEP_UP = 6656
#: A gap under this admits nothing at all, crouched or otherwise; `doors.py`
#: uses the same figure for "shut".
CLOSED = 512
#: How wide a body is. A gap narrower than this admits nobody however far
#: the leaf travelled.
BODY_WIDTH = PLAYER_PROFILES["blood"].body_width

#: A body on its knees, from the profile the whole repo measures against.
#: Worth a separate question from standing, because the largest single shape
#: in the residue below is a gap that opens to more than this and less than a
#: standing body -- a way through that a body has to duck for.
CROUCH_HEIGHT = PLAYER_PROFILES["blood"].crouch_height or PLAYER_HEIGHT

#: What a marked motion is told to do, and by what.
#:
#: `triggers.cpp:TranslateSector` interpolates the sector between two marker
#: sprites. NOT a rest and a destination -- they are the two STATES.
#: `marker_0` is the position for state OFF and `marker_1` for state ON, and
#: `state` alone decides which one the level starts at; there is no journey
#: and no resting end. A rotate carries one marker and turns about it, and
#: reads it the other way round: `marker_0`'s x/y are the pivot and its angle
#: is the whole turn.
MARKER_OFF, MARKER_ON = "marker_0", "marker_1"
#: The names this pair used to carry. Kept so nothing outside breaks, but the
#: model behind them was wrong: they said a mechanism rests at one end and
#: visits the other.
MARKER_REST, MARKER_MOVED = MARKER_OFF, MARKER_ON

#: **What actually moves, which is not always the sector's own geometry.**
#:
#: `TranslateSector`'s last argument is `bAllWalls`, and the caller passes
#: `type == kSectorSlide` / `type == kSectorRotate` -- so the *unmarked*
#: types 616 and 617 drag every wall they own, while the **Marked** types
#: 614 and 615 drag only walls flagged `cstat & 16384` (with the motion) or
#: `cstat & 32768` (against it).
#:
#: Sprites are dragged on their own flags, `cstat & 8192` and `& 16384`, and
#: they are dragged **whether or not any wall is**. E1M1's sector 65 is the
#: case that proves it: 49 walls, not one of them flagged, and two wall
#: sprites (37 and 38) carrying 8192 and 16384 -- a sliding gate whose whole
#: moving part is two sprites. A reading that only sweeps geometry sees a
#: mechanism that does nothing.
WALL_MOVES_WITH = 16384
WALL_MOVES_AGAINST = 32768
SPRITE_MOVES_WITH = 8192
SPRITE_MOVES_AGAINST = 16384
MOVES_ALL_WALLS_TYPES = frozenset({616, 617})

#: What a motion carries.
PAYLOAD_WALLS = "its own walls"
PAYLOAD_SPRITES = "carried sprites"
PAYLOAD_BOTH = "walls and carried sprites"
PAYLOAD_NOTHING = "nothing that moves"

#: The design objects `design_object` can return. Names, and nothing in the
#: reading depends on them -- they are the output, never an input.
OPENS_A_WAY = "changes what fits through"
CARRIES_BETWEEN_LEVELS = "carries a body between levels"
BOTH = "both"
NEITHER = "neither"
#: The reading declines. Both spatial questions below are asked about a **z**
#: opening, so a sector that only slides or only turns is not "neither" -- it
#: is untested, and the two are not the same claim. Reporting 642 sliding and
#: turning sectors as "neither" is the first thing this experiment did wrong.
UNCLASSIFIED = "not decidable from z alone"


class EffectError(ValueError):
    """A reading was asked for something the record cannot answer."""


def physical_effects(record: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Plane 1: what the engine does, from one `observe_motion_sector` record.

    Magnitudes are signed the way Blood's z is signed -- growing downward --
    because reporting them any other way would be a reading dressed as a
    measurement.
    """
    if record is None:
        raise EffectError("no motion record to read")
    type_id = int(record["type_id"])
    out: list[dict[str, Any]] = []
    floor_travel = int(record["on_floor_z"]) - int(record["off_floor_z"])
    ceiling_travel = int(record["on_ceiling_z"]) - int(record["off_ceiling_z"])
    if type_id in Z_MOTION_TYPES or floor_travel or ceiling_travel:
        if floor_travel:
            out.append({"effect": MOVE_FLOOR_Z, "travel": floor_travel,
                        "from_z": int(record["off_floor_z"]),
                        "to_z": int(record["on_floor_z"])})
        if ceiling_travel:
            out.append({"effect": MOVE_CEILING_Z, "travel": ceiling_travel,
                        "from_z": int(record["off_ceiling_z"]),
                        "to_z": int(record["on_ceiling_z"])})
    if type_id in SLIDE_TYPES:
        out.append({"effect": TRANSLATE_XY, "type_id": type_id})
    if type_id in ROTATE_TYPES:
        out.append({"effect": ROTATE_ABOUT_AXIS, "type_id": type_id})
    return tuple(out)


def openings(record: dict[str, Any]) -> dict[str, int]:
    """The clear gap in each of the two states, and at rest.

    Blood's z grows downward, so a floor is numerically *below* its ceiling
    and the gap is `floor_z - ceiling_z`. Getting that backwards is how a
    reciprocal formula survived in this repo for months.
    """
    off = int(record["off_floor_z"]) - int(record["off_ceiling_z"])
    on = int(record["on_floor_z"]) - int(record["on_ceiling_z"])
    return {"off": off, "on": on,
            "widest": max(off, on), "narrowest": min(off, on),
            "at_rest": int(record["rest_opening"])}


def embedding(record: dict[str, Any],
              neighbour_floor_z: Iterable[int]) -> dict[str, Any]:
    """Plane 3: what the motion does to occupancy and reachability.

    Two questions, both spatial, neither of them a field:

    * does the motion change whether a body fits through? Asked
      **symmetrically** -- a leaf that rests open and shuts changes what fits
      exactly as much as one that rests shut and opens, and deciding which is
      "the" direction is a reading rather than a measurement.
    * does it carry a body between two standing levels? That needs the floor
      to travel further than a body can step, and to arrive at two different
      neighbours' floors.
    """
    gaps = openings(record)
    admits_off = gaps["off"] >= PLAYER_HEIGHT
    admits_on = gaps["on"] >= PLAYER_HEIGHT
    ducked_off = gaps["off"] >= CROUCH_HEIGHT
    ducked_on = gaps["on"] >= CROUCH_HEIGHT
    floor_travel = abs(int(record["on_floor_z"]) - int(record["off_floor_z"]))
    levels = {int(z) for z in neighbour_floor_z}
    served = {z for z in levels
              if any(abs(z - stop) <= STEP_UP for stop in
                     (int(record["off_floor_z"]), int(record["on_floor_z"])))}
    return {
        "changes_what_fits": admits_off != admits_on,
        "admits_a_body": {"off": admits_off, "on": admits_on},
        "admits_a_ducked_body": {"off": ducked_off, "on": ducked_on},
        #: Opens wide enough to duck through and never wide enough to walk
        #: through. A way, and not one the standing body it was measured
        #: against can use.
        "crouch_only": (ducked_off or ducked_on) and not (admits_off or admits_on),
        "carries_between_levels": floor_travel > STEP_UP and len(served) >= 2,
        "floor_travel": floor_travel,
        "ceiling_travel": abs(int(record["on_ceiling_z"])
                              - int(record["off_ceiling_z"])),
        "neighbour_levels": len(levels),
        "levels_served": len(served),
        "shuts_to_nothing": gaps["narrowest"] <= CLOSED,
        "open_throughout": gaps["narrowest"] >= PLAYER_HEIGHT,
        "openings": gaps,
    }


def motion_markers(disk: Any, sector_id: int) -> dict[str, Any]:
    """The marker sprites a marked motion interpolates between.

    Returned as the engine reads them -- position and angle -- with no
    opinion about which is "open". A rotate's `marker_1` is absent, and that
    absence is the difference between turning about a point and travelling
    between two.
    """
    extra = getattr(disk.sectors[sector_id], "extra", None)
    fields = extra.fields if extra is not None and hasattr(extra, "fields") else {}
    out: dict[str, Any] = {}
    for role in (MARKER_OFF, MARKER_ON):
        #: `or -1` would throw away sprite 0, which is a real marker in a
        #: real map -- E1M1's sector 65 references sprite 0 as its own.
        raw = fields.get(role)
        index = -1 if raw is None else int(raw)
        if not 0 <= index < len(disk.sprites):
            continue
        sprite = disk.sprites[index].fields
        out[role] = {
            "sprite": index, "type": int(sprite["type"]),
            "x": int(sprite["x"]), "y": int(sprite["y"]),
            #: A marker's angle is travel, not a facing, so it is never
            #: masked -- E1M4's -8192 is four whole turns and masks to 0.
            "angle": int(sprite["angle"]),
        }
    return out


def _owner_materials(disk: Any, wall_ids: Sequence[int],
                     sprite_ids: Sequence[int]) -> list[dict[str, Any]]:
    """The owner's reading of every tile the moving parts wear.

    `may_name` travels with each one. A weak-binding tile is material and a
    name must not rest on it; carrying the flag beside the label is what
    makes that rule checkable downstream instead of remembered.
    """
    from .owner_anchors import OwnerAnchorError, load_owner_anchors

    try:
        anchors = load_owner_anchors()
    except OwnerAnchorError:
        return []
    seen: dict[int, dict[str, Any]] = {}
    for source, indices in (("wall", wall_ids), ("sprite", sprite_ids)):
        items = disk.walls if source == "wall" else disk.sprites
        for index in indices:
            if not 0 <= index < len(items):
                continue
            picnum = int(items[index].fields["picnum"])
            anchor = anchors.get(picnum)
            if anchor is None or picnum in seen:
                continue
            seen[picnum] = {
                "picnum": picnum, "on": source,
                "label": anchor.describe(),
                "binding": anchor.binding or "untested",
                "may_name": anchor.may_name,
            }
    return [seen[key] for key in sorted(seen)]


#: The payload shapes a Marked slide can have. The first two are named here
#: for the first time; before this the model could list which walls moved and
#: not say what the arrangement MEANT.
SHAPE_BOUNDARY = "boundary re-partition"
SHAPE_RESIZE = "the sector resizes itself"
SHAPE_WHOLE = "the whole sector travels"
SHAPE_PARTIAL = "part of the sector travels"
SHAPE_NONE = "nothing moves"


def payload_shape(disk: Any, sector_id: int, with_walls: list[int],
                  against_walls: list[int]) -> dict[str, Any]:
    """What the arrangement of flagged walls MEANS, not just which they are.

    Two shapes matter and neither was expressible before, which is why two
    whole classes of Blood mechanism could not be read or authored:

    **Boundary re-partition.** Exactly one flagged wall, and it is a portal
    to a neighbour. Its travel moves the line between this sector and that
    one, so plan area passes from one to the other: the hole grows as the
    cover shrinks. E1M1's casket is two of these, and the reason it could
    never be built out of `sliding_gate` is that a gate moves leaves ACROSS a
    threshold and this moves the threshold ITSELF.

    **Self-resize.** Two flagged walls with OPPOSITE flags. One advances
    while the other retreats, so the sector's own extent changes and any
    texture on the faces between them is squashed and stretched by exactly
    that much. E1M1's curtain, s125, is this and nothing else -- the
    deformation IS the animation, which is why reading it as moving sprites
    produced something that behaved like a gate.
    """
    flagged = list(with_walls) + list(against_walls)
    if not flagged:
        return {"shape": SHAPE_NONE, "flagged": 0}
    portals = [w for w in flagged
               if int(disk.walls[w].fields["next_sector"]) >= 0]
    if len(flagged) == 1 and portals:
        neighbour = int(disk.walls[flagged[0]].fields["next_sector"])
        return {
            "shape": SHAPE_BOUNDARY, "flagged": 1,
            "boundary_wall": flagged[0], "re_partitions_with": neighbour,
            "basis": "one flagged wall, and it is the portal to a neighbour: "
                     "its travel moves the line between the two sectors",
        }
    if with_walls and against_walls:
        return {
            "shape": SHAPE_RESIZE, "flagged": len(flagged),
            "advancing": list(with_walls), "retreating": list(against_walls),
            "basis": "flagged walls carry OPPOSITE flags, so the sector's own "
                     "extent changes and the texture between them deforms",
        }
    count = int(disk.sectors[sector_id].fields["wall_count"])
    return {
        "shape": SHAPE_WHOLE if len(flagged) >= count else SHAPE_PARTIAL,
        "flagged": len(flagged), "of": count,
    }


def payload(disk: Any, sector_id: int) -> dict[str, Any]:
    """What the motion drags: the sector's own walls, sprites, or both."""
    sector = disk.sectors[sector_id]
    type_id = int(sector.fields["type"])
    start = int(sector.fields["wall_ptr"])
    count = int(sector.fields["wall_count"])
    all_walls = type_id in MOVES_ALL_WALLS_TYPES
    with_walls, against_walls = [], []
    for wall_id in range(start, start + count):
        cstat = int(disk.walls[wall_id].fields["cstat"])
        if cstat & WALL_MOVES_WITH:
            with_walls.append(wall_id)
        elif cstat & WALL_MOVES_AGAINST:
            against_walls.append(wall_id)
    with_sprites, against_sprites = [], []
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["sector"]) != sector_id:
            continue
        cstat = int(sprite.fields["cstat"])
        if cstat & SPRITE_MOVES_WITH:
            with_sprites.append(index)
        elif cstat & SPRITE_MOVES_AGAINST:
            against_sprites.append(index)
    moves_walls = all_walls or bool(with_walls or against_walls)
    moves_sprites = bool(with_sprites or against_sprites)
    if moves_walls and moves_sprites:
        carries = PAYLOAD_BOTH
    elif moves_walls:
        carries = PAYLOAD_WALLS
    elif moves_sprites:
        carries = PAYLOAD_SPRITES
    else:
        carries = PAYLOAD_NOTHING
    return {
        "carries": carries,
        #: The SHAPE of the payload, which is a different question from what
        #: it is made of and is the one the project could not previously ask.
        "shape": payload_shape(disk, sector_id, with_walls, against_walls),
        #: What the moving parts are *made of*, in the owner's words. A
        #: blade sprite on tile 332 reads "grate/lattice (owner)" in a
        #: report rather than as a bare number, and the label is reproduced
        #: from `owner-anchors-v1.json` rather than retyped here.
        "materials": _owner_materials(disk, with_walls + against_walls,
                                      with_sprites + against_sprites),
        "moves_every_wall": all_walls,
        "walls_with": with_walls, "walls_against": against_walls,
        "sprites_with": with_sprites, "sprites_against": against_sprites,
        "wall_count": count,
        "engine": "triggers.cpp TranslateSector: bAllWalls is set for "
                  "kSectorSlide/kSectorRotate; the Marked types drag only "
                  "walls flagged 16384/32768, and sprites are dragged on "
                  "their own 8192/16384 whatever the walls do",
    }


def swept_motion(disk: Any, sector_id: int, record: dict[str, Any]
                 ) -> dict[str, Any] | None:
    """Plane 1 for a mechanism that travels or turns rather than rising.

    Returns None for a sector that only moves in z -- that one is already
    described by `physical_effects`. What is measured here is the engine's
    own instruction: where the markers are, how far apart, and how much
    turn between them.
    """
    type_id = int(record["type_id"])
    if type_id not in SLIDE_TYPES and type_id not in ROTATE_TYPES:
        return None
    markers = motion_markers(disk, sector_id)
    rest = markers.get(MARKER_OFF)
    moved = markers.get(MARKER_ON)
    kind = TRANSLATE_XY if type_id in SLIDE_TYPES else ROTATE_ABOUT_AXIS
    out: dict[str, Any] = {
        "effect": kind, "type_id": type_id, "markers": markers,
        "payload": payload(disk, sector_id),
        "period": int(record["busy_time_a"]),
    }
    if rest is None:
        #: A marked motion with no OFF marker cannot be interpolated, so
        #: nothing is claimed about where it goes.
        out["travel"] = None
        out["undriven"] = True
        return out
    if kind == ROTATE_ABOUT_AXIS:
        out["pivot"] = {"x": rest["x"], "y": rest["y"]}
        out["turn"] = rest["angle"]
        out["travel"] = abs(rest["angle"])
        return out
    if moved is None:
        out["travel"] = None
        out["undriven"] = True
        return out
    dx, dy = moved["x"] - rest["x"], moved["y"] - rest["y"]
    out["translation"] = {"dx": dx, "dy": dy}
    out["turn"] = moved["angle"] - rest["angle"]
    out["travel"] = int((dx * dx + dy * dy) ** 0.5)
    return out


def _segment_length(disk: Any, wall_id: int) -> float:
    here = disk.walls[wall_id].fields
    there = disk.walls[int(here["point2"])].fields
    dx = int(there["x"]) - int(here["x"])
    dy = int(there["y"]) - int(here["y"])
    return (dx * dx + dy * dy) ** 0.5


def _sprite_width(disk: Any, index: int) -> float:
    """A wall sprite's drawn width: x_repeat * tile_width / 4.

    The tile width is not in the MAP, so 64 is assumed -- the width of every
    blade and panel tile this repo has measured. Where that is wrong the
    number is wrong by a factor, never by a sign.
    """
    return int(disk.sprites[index].fields["x_repeat"]) * 64 / 4


def swept_opening(disk: Any, sector_id: int, motion: dict[str, Any]
                  ) -> dict[str, Any]:
    """How wide a gap the moving payload vacates.

    The swept-area question, answered on the leaf rather than on the room. A
    door leaf of length `L` sliding `d` along its own line leaves an opening
    of `min(d, L)`: travel beyond its own length buys nothing, and a leaf
    longer than its travel is still partly in the way. A leaf hinged at one
    end and swung by `theta` leaves the chord `2 * L * sin(theta / 2)`.

    Then the only question that matters: **is that opening wider than a
    body?** 384 units, from the same profile everything else here measures
    against.

    This is a reading of the leaf, not a polygon sweep of the room. It
    cannot see a leaf that slides into a recess already too small for it, or
    two leaves that foul each other. Those need the real swept polygon, and
    that is still the gap.
    """
    load = motion["payload"]
    lengths = [_segment_length(disk, wall_id)
               for wall_id in load["walls_with"] + load["walls_against"]]
    if load["moves_every_wall"] and not lengths:
        start = int(disk.sectors[sector_id].fields["wall_ptr"])
        count = int(disk.sectors[sector_id].fields["wall_count"])
        lengths = [_segment_length(disk, wall_id)
                   for wall_id in range(start, start + count)]
    lengths.extend(_sprite_width(disk, index)
                   for index in load["sprites_with"] + load["sprites_against"])
    travel = motion.get("travel")
    if not lengths or travel is None:
        return {"leaf_length": None, "opening": 0, "admits_a_body": False,
                "basis": "no moving payload, or a motion with no markers to "
                         "interpolate between"}
    #: The longest moving part is the leaf. A door built of several panels
    #: opens as wide as its widest one, not as wide as their sum.
    leaf = max(lengths)
    if motion["effect"] == ROTATE_ABOUT_AXIS:
        from math import pi, sin

        opening = abs(2 * leaf * sin(pi * (motion.get("turn") or 0) / 2048.0))
        basis = "chord swept by a leaf hinged at one end: 2 L sin(theta/2)"
    else:
        opening = min(float(travel), leaf)
        basis = "a leaf sliding along its own line vacates min(travel, length)"
    return {
        "leaf_length": round(leaf, 1),
        "leaf_parts": len(lengths),
        "opening": int(opening),
        "body_width": BODY_WIDTH,
        "admits_a_body": opening >= BODY_WIDTH,
        "basis": basis,
    }


def leaf_segments(disk: Any, sector_id: int, motion: dict[str, Any]
                  ) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """The solid moving walls: the leaf, as `(start, end, sign)` segments.

    A leaf is a moving wall that is **not** a portal. That is what a door
    leaf is in Build -- E1M1's s4, s63 and s125 all move one-sided walls
    while their portals stay put -- and it is the only part of a moving
    sector that can stand between two sides.

    A sector every one of whose walls is a portal has no leaf, and this
    returns nothing. That is not a failure to find one; there is none, and
    what blocks such a sector is its whole geometry moving, which needs the
    polygon sweep this module does not have.
    """
    load = motion["payload"]
    if load["moves_every_wall"]:
        start = int(disk.sectors[sector_id].fields["wall_ptr"])
        count = int(disk.sectors[sector_id].fields["wall_count"])
        walls = [(wall_id, 1) for wall_id in range(start, start + count)]
    else:
        #: The sign is the engine's: `cstat & 16384` travels with the motion
        #: and `& 32768` against it. A double door is one sector with both,
        #: and translating them the same way leaves half the door still
        #: across the opening -- which is how E1M1's s4 read as never
        #: opening at all.
        walls = ([(wall_id, 1) for wall_id in load["walls_with"]]
                 + [(wall_id, -1) for wall_id in load["walls_against"]])
    out = []
    for wall_id, sign in walls:
        fields = disk.walls[wall_id].fields
        if int(fields["next_sector"]) >= 0:
            continue                      # a portal is a way, not a leaf
        there = disk.walls[int(fields["point2"])].fields
        out.append(((float(fields["x"]), float(fields["y"])),
                    (float(there["x"]), float(there["y"])), sign))
    return out


def _moved(point: tuple[float, float], motion: dict[str, Any], sign: int = 1
           ) -> tuple[float, float]:
    """Where a point of the leaf ends up once the motion has run."""
    from .motion_sim import rotate_about

    if motion["effect"] == ROTATE_ABOUT_AXIS:
        pivot = motion.get("pivot")
        if pivot is None:
            return point
        return rotate_about(point, sign * int(motion.get("turn") or 0),
                            (float(pivot["x"]), float(pivot["y"])))
    shift = motion.get("translation") or {"dx": 0, "dy": 0}
    return (point[0] + sign * shift["dx"], point[1] + sign * shift["dy"])


def leaf_blocks(disk: Any, sector_id: int, motion: dict[str, Any],
                a: tuple[float, float], b: tuple[float, float], *,
                moved: bool) -> bool | None:
    """Does the leaf stand between these two points, in this state?

    The straight line from one portal's midpoint to the other is the way a
    body would take across the sector. If a leaf segment crosses that line,
    the way is shut.

    Returns None when the sector has no leaf, because "no leaf found" and
    "the leaf is not in the way" are different answers and only one of them
    is a measurement.
    """
    from .motion_sim import segments_cross

    segments = leaf_segments(disk, sector_id, motion)
    if not segments:
        return None
    for start, end, sign in segments:
        if moved:
            start = _moved(start, motion, sign)
            end = _moved(end, motion, sign)
        if segments_cross(a, b, start, end):
            return True
    return False


def portal_midpoint(disk: Any, sector_id: int, neighbour: int
                    ) -> tuple[float, float] | None:
    """The middle of the wall this sector shares with that neighbour."""
    start = int(disk.sectors[sector_id].fields["wall_ptr"])
    count = int(disk.sectors[sector_id].fields["wall_count"])
    for wall_id in range(start, start + count):
        fields = disk.walls[wall_id].fields
        if int(fields["next_sector"]) != neighbour:
            continue
        there = disk.walls[int(fields["point2"])].fields
        return ((int(fields["x"]) + int(there["x"])) / 2.0,
                (int(fields["y"]) + int(there["y"])) / 2.0)
    return None


def design_object(spatial: dict[str, Any], *, moves_in_z: bool = True,
                  sweeps: dict[str, Any] | None = None) -> str:
    """Plane 3's conclusion: what the thing *is*, from where it sits.

    Takes the embedding and nothing else. There is deliberately no way to
    hand this function a sector type, because a sector type is what it must
    not consult.

    `moves_in_z` is not an exception to that. It says whether the question
    this function asks even applies -- both clauses are about a vertical
    opening -- and a mechanism that only slides or turns gets `UNCLASSIFIED`
    rather than a confident wrong answer.
    """
    if sweeps is not None:
        #: A swept mechanism is read on the gap its leaf vacates, not on a
        #: vertical opening. This is the branch that unparks slide and
        #: rotate; before it, 657 campaign mechanisms came back undecided.
        return OPENS_A_WAY if sweeps["admits_a_body"] else NEITHER
    if not moves_in_z:
        return UNCLASSIFIED
    opens = bool(spatial["changes_what_fits"])
    carries = bool(spatial["carries_between_levels"])
    if opens and carries:
        return BOTH
    if opens:
        return OPENS_A_WAY
    if carries:
        return CARRIES_BETWEEN_LEVELS
    return NEITHER


def style(record: dict[str, Any]) -> dict[str, Any]:
    """Plane 4: what makes the thing readable as what it is."""
    return {
        "face_unlike_its_surround": bool(record["visually_distinct_from_fill"]),
        "distinct_faces": list(record["distinct_approach_faces"]),
        "signifiers": [item.get("category") for item in record["nearby_sprites"]
                       if item.get("category")][:8],
        "keyed": bool(record["key"]),
        "key_name": record["key_name"],
    }


def carried_parts(assembly: Any) -> dict[str, Any]:
    """Plane 2, from an `assembly.Assembly`: what rides the motion.

    Kept to the shape of the assembly rather than to a list of sprites,
    because what makes two instances comparable is which parts are present in
    what numbers -- which is exactly what `Assembly.shape` already says.
    """
    if assembly is None:
        return {"shape": [], "carried": 0, "operators": 0, "markers": 0}
    shape = dict(assembly.shape())
    return {
        "shape": [list(item) for item in assembly.shape()],
        "carried": sum(count for role, count in shape.items()
                       if role.startswith("carried")),
        "operators": sum(count for role, count in shape.items()
                         if role in ("operator", "switch")),
        "markers": sum(count for role, count in shape.items()
                       if role.startswith("marker")),
    }


# ---------------------------------------------------------------------------
# Plane 5: what the mechanism DRIVES
#
# The four planes above say what one sector does. None of them can say "the
# alcove light follows the curtain", because that fact is not in the curtain
# and not in the light: it is in the pair, and the only field carrying it is
# the sector's `command` -- a number the whole stack could read and no reader
# had ever interpreted as a verb.
#
# Everything here is a transcription. The engine is the authority and each
# clause names the line it came from.
# ---------------------------------------------------------------------------

#: The twelve instruction verbs, `blood_types.COMMANDS` 0..11. Command 12 and
#: up are a counter instruction, the two callback verbs and then the *causes*
#: -- what the engine sends when a body pushes or shoots something -- which
#: are not a transmitter's choice.
#:
#: **Link is the continuous one.** Eleven of the twelve are edge verbs: the
#: sender reports that it changed state and the receiver acts once. `kCmdLink`
#: is sent every tick of the sender's own travel and carries the sender's
#: `busy` with it, so the receiver does not act once -- it TRACKS.
COMMAND_VERBS: dict[int, str] = {
    0: "turn it off", 1: "turn it on", 2: "match my state",
    3: "toggle it", 4: "take my state inverted", 5: "follow me",
    6: "lock it", 7: "unlock it", 8: "toggle its lock",
    9: "stop, then off", 10: "stop, then on", 11: "stop at the next stop",
}
LINK = 5

#: Which busy proc runs a sector, and therefore whether a `command 5` sector
#: sends its Link at all. `OperateSector`'s type switch (triggers.cpp:
#: 1680-1738) picks the BUSYID; `gBusyProc` (:2076-2085) maps it to the
#: function; and each of those functions opens with the same two lines:
#:
#:     if (pXSector->command == kCmdLink && pXSector->txID)
#:         evSend(nSector, 6, pXSector->txID, kCmdLink, causerID);
#:
#: -- VSpriteBusy :1247, VDoorBusy :1346, HDoorBusy :1374, RDoorBusy :1401,
#: StepRotateBusy :1434, GenSectorBusy :1454.
LINK_SENDING_BUSY_PROC: dict[int, str] = {
    600: "VDoorBusy (triggers.cpp:1346)",
    602: "VSpriteBusy (triggers.cpp:1247)",
    613: "StepRotateBusy (triggers.cpp:1434)",
    614: "HDoorBusy (triggers.cpp:1374)",
    615: "RDoorBusy (triggers.cpp:1401)",
    616: "HDoorBusy (triggers.cpp:1374)",
    617: "RDoorBusy (triggers.cpp:1401)",
}

#: The seventh Link send, `VCrushBusy` (triggers.cpp:1198), is NOT reachable
#: in vanilla: `BUSYID_0` is referenced from `nnexts.cpp:4222` alone, which is
#: the NOONE_EXTENSIONS / `gModernMap` path. Cited here so the omission reads
#: as a decision rather than an oversight.
MODERN_ONLY_LINK_SEND = (
    "VCrushBusy (triggers.cpp:1198), reached only from nnexts.cpp:4222 "
    "under gModernMap")

#: Two sector types run no busy proc at all, so a `command 5` on one of them
#: is never sent. `kSectorTeleport` goes to `OperateTeleport` and
#: `kSectorPath` to `OperatePath` (triggers.cpp:1710-1716); `PathBusy`
#: (:1465-1494) is the one busy proc with no Link clause in it.
NO_LINK_SENDER_TYPES: dict[int, str] = {
    604: "OperateTeleport runs no busy proc (triggers.cpp:1711)",
    612: "PathBusy carries no kCmdLink send (triggers.cpp:1465-1494)",
}

#: How a receiver answers, named for what the busy does to it.
FOLLOWS_AS_MOVER = "mirrors the sender's travel"
FOLLOWS_AS_DIMMER = "dims and brightens with the travel"
STATE_ONLY = "flips only when the travel lands on a whole state"
COMBO_DIAL = "reads the sender's data1 as a combination digit"

#: `LinkSector` (triggers.cpp:1781-1794) hands the busy straight to the
#: receiver's own busy proc for exactly these types -- which is why a Link to
#: a second mover is a mirror and not a trigger.
LINK_DRIVEN_MOVER_TYPES: dict[int, str] = {
    600: "VDoorBusy (triggers.cpp:1785)",
    602: "VSpriteBusy (triggers.cpp:1782)",
    614: "HDoorBusy (triggers.cpp:1789)",
    615: "RDoorBusy (triggers.cpp:1793)",
    616: "HDoorBusy (triggers.cpp:1789)",
    617: "RDoorBusy (triggers.cpp:1793)",
}

#: Worth saying the other way round as well: `kSectorRotateStep` (613) SENDS a
#: Link from `StepRotateBusy` but is not in `LinkSector`'s switch, so a Link it
#: RECEIVES reaches only the default branch. A stepped rotator can drive a
#: mirror; it cannot be one.
SENDS_BUT_CANNOT_MIRROR = frozenset({613})

#: Waves this module transcribes exactly. `GetWaveValue` (sectorfx.cpp:75-107)
#: is a pure function of (wave, phase, amplitude); 0..4 are integer arithmetic
#: and are reproduced below. 5 and 11 need Build's `Sin`/`Cos` tables and 6..10
#: index the four flicker tables and the strobe table, none of which is
#: transcribed here -- so those report the shade as unmeasurable rather than
#: guessing at it.
TRANSCRIBED_WAVES = frozenset({0, 1, 2, 3, 4})


def wave_value(wave: int, phase: int, amplitude: int) -> int | None:
    """`GetWaveValue` (sectorfx.cpp:75-107), for the waves transcribed here.

    Returns None for a wave whose table this module does not carry. **Wave 0
    returns the amplitude unchanged** (`:80-81 case 0: return c`), which is
    the whole reason a Link-driven dimmer usually carries no wave at all: the
    shade then IS the scaled amplitude and tracks `busy` linearly.
    """
    phase &= 2047
    amplitude = int(amplitude)
    if wave == 0:
        return amplitude
    if wave == 1:
        return (phase >> 10) * amplitude
    if wave == 2:
        return (abs(128 - (phase >> 3)) * amplitude) >> 7
    if wave == 3:
        return ((phase >> 3) * amplitude) >> 8
    if wave == 4:
        return ((255 - (phase >> 3)) * amplitude) >> 8
    return None


def _mulscale16(a: int, b: int) -> int:
    return (int(a) * int(b)) >> 16


def _clip_shade(value: int) -> int:
    return max(-128, min(127, int(value)))


def _x(item: Any) -> dict[str, Any]:
    extra = getattr(item, "extra", None)
    return dict(extra.fields) if extra is not None else {}


def shade_at(disk: Any, sector_id: int, busy: int) -> dict[str, Any]:
    """What `DoSectorLighting` leaves on this sector's faces at `busy`.

    The gate is `sectorfx.cpp:162` -- `if (pXSector->shadeAlways ||
    pXSector->busy)` -- so with `shade_always` 0 and busy 0 the sector is
    simply its authored shade. At a non-zero busy the amplitude is scaled
    (`:166-168`), the wave is evaluated (`:171`) and the result is added to
    each face the three `shade*` flags select, clipped to -128..127
    (`:171-199`).

    `unmeasurable` is set, and the shade left unchanged, when the wave is one
    this module does not transcribe or when the phase still advances with the
    clock (`freq` non-zero, `:170-171`): the honest answer there is a range
    over the clock, not a number.
    """
    fields = disk.sectors[sector_id].fields
    extra = _x(disk.sectors[sector_id])
    floor = int(fields["floor_shade"])
    ceiling = int(fields["ceiling_shade"])
    out: dict[str, Any] = {
        "busy": int(busy), "floor_shade": floor, "ceiling_shade": ceiling,
        "delta": 0, "unmeasurable": None,
    }
    if not extra:
        return out
    amplitude = int(extra.get("amplitude", 0))
    always = int(extra.get("shade_always", 0))
    #: sectorfx.cpp:363 -- `InitSectorFX` lists a sector for lighting only if
    #: its amplitude is non-zero. With amplitude 0 the sector is never visited
    #: and every other shade field on it is inert.
    if amplitude == 0:
        return out
    if not always and int(busy) == 0:
        return out
    scaled = (_mulscale16(amplitude, int(busy)) if (not always and busy)
              else amplitude)
    wave = int(extra.get("shade_wave", 0))
    freq = int(extra.get("shade_frequency", 0))
    if wave not in TRANSCRIBED_WAVES:
        out["unmeasurable"] = (
            f"wave {wave} needs a table this module does not transcribe "
            "(sectorfx.cpp:90-107)")
        return out
    if freq and wave != 0:
        out["unmeasurable"] = (
            f"shade_frequency {freq} advances the phase with totalclock "
            "(sectorfx.cpp:170-171); the shade is a range, not a value")
        return out
    delta = wave_value(wave, int(extra.get("shade_phase", 0)) * 8, scaled)
    out["delta"] = int(delta)
    if int(extra.get("shade_floor", 0)):
        out["floor_shade"] = _clip_shade(floor + delta)
    if int(extra.get("shade_ceiling", 0)):
        out["ceiling_shade"] = _clip_shade(ceiling + delta)
    #: The walls take the same delta, one at a time (`:191-199`), so the pair
    #: of extremes is the honest summary of a face that is many faces.
    if int(extra.get("shade_walls", 0)):
        start = int(fields["wall_ptr"])
        shades = [int(disk.walls[index].fields["shade"])
                  for index in range(start, start + int(fields["wall_count"]))]
        if shades:
            out["wall_shade"] = [_clip_shade(min(shades) + delta),
                                 _clip_shade(max(shades) + delta)]
    return out


def receiver_index(disk: Any) -> dict[int, list[tuple[str, int]]]:
    """Channel -> everything that listens on it, by kind.

    The mirror of `conditional.transmitters`, and it lives here rather than
    there because `conditional` imports `effects` and that arrow points one
    way only.
    """
    out: dict[int, list[tuple[str, int]]] = {}
    for kind, items in (("sector", disk.sectors), ("wall", disk.walls),
                        ("sprite", disk.sprites)):
        for index, item in enumerate(items):
            channel = int(_x(item).get("rx_id", 0))
            if channel:
                out.setdefault(channel, []).append((kind, index))
    return out


def _sector_receiver(disk: Any, index: int, continuous: bool) -> dict[str, Any]:
    """One sector on the far end of a channel, and what busy does to it."""
    fields = disk.sectors[index].fields
    extra = _x(disk.sectors[index])
    type_id = int(fields["type"])
    amplitude = int(extra.get("amplitude", 0))
    row: dict[str, Any] = {
        "kind": "sector", "id": index, "type_id": type_id,
        "response": None, "engine": None, "follows": False,
        "needs": {}, "faults": [],
    }
    if not continuous:
        row["response"] = STATE_ONLY
        row["engine"] = "OperateSector (triggers.cpp:1680-1738)"
        return row
    #: triggers.cpp:1916 -- `trMessageSector` drops every command but the two
    #: lock verbs on a locked receiver, kCmdLink included.
    if int(extra.get("locked", 0)):
        row["faults"].append(
            "locked: trMessageSector:1916 drops the Link before LinkSector "
            "is reached")
    if type_id in LINK_DRIVEN_MOVER_TYPES:
        row["response"] = FOLLOWS_AS_MOVER
        row["engine"] = LINK_DRIVEN_MOVER_TYPES[type_id]
        row["follows"] = not row["faults"]
        return row
    row["engine"] = "LinkSector default branch (triggers.cpp:1795-1799)"
    if type_id in SENDS_BUT_CANNOT_MIRROR:
        row["faults"].append(
            f"type {type_id} is absent from LinkSector's switch "
            "(triggers.cpp:1780-1800): it can send a Link but not mirror one")
    if amplitude == 0:
        row["response"] = STATE_ONLY
        row["needs"] = {"amplitude": "non-zero, or the sector is never lit"}
        #: Not a fault on its own: a receiver with no amplitude was never
        #: meant to light, and it still takes the state edge at a whole busy.
        #: It becomes a fault when the sector carries shade wiring that now
        #: cannot run.
        if any(int(extra.get(flag, 0)) for flag in
               ("shade_always", "shade_floor", "shade_ceiling", "shade_walls")):
            row["faults"].append(
                "shade wiring with amplitude 0: InitSectorFX:363 never lists "
                "the sector, so DoSectorLighting never visits it")
        return row
    row["response"] = FOLLOWS_AS_DIMMER
    row["needs"] = {
        "amplitude": amplitude,
        "shade_wave": int(extra.get("shade_wave", 0)),
        "shade_frequency": int(extra.get("shade_frequency", 0)),
        "shade_always": int(extra.get("shade_always", 0)),
        "faces": [name for name, flag in
                  (("floor", "shade_floor"), ("ceiling", "shade_ceiling"),
                   ("walls", "shade_walls"))
                  if int(extra.get(flag, 0))],
    }
    if int(extra.get("shade_always", 0)):
        row["faults"].append(
            "shade_always 1: sectorfx.cpp:166 scales the amplitude by busy "
            "only when shade_always is 0, so the wave runs at full swing "
            "whatever the sender does -- the light does not follow")
    if not row["needs"]["faces"] and not int(extra.get("colored_lights", 0)):
        row["faults"].append(
            "amplitude with no shade_floor/ceiling/walls: sectorfx.cpp:"
            "171-199 computes a shade and applies it to nothing")
    row["off"] = shade_at(disk, index, 0)
    row["on"] = shade_at(disk, index, 65536)
    row["follows"] = not row["faults"]
    return row


def _wall_receiver(disk: Any, index: int, continuous: bool) -> dict[str, Any]:
    extra = _x(disk.walls[index])
    row: dict[str, Any] = {
        "kind": "wall", "id": index, "type_id": None,
        "response": STATE_ONLY,
        "engine": ("LinkWall (triggers.cpp:1833-1839): the busy is copied and "
                   "SetWallState runs only at a whole busy"),
        "follows": False, "needs": {}, "faults": [],
    }
    if not continuous:
        row["engine"] = "OperateWall (triggers.cpp:692)"
    elif int(extra.get("locked", 0)):
        row["faults"].append("locked: trMessageWall:1937 drops the Link")
    return row


def _sprite_receiver(disk: Any, index: int, continuous: bool) -> dict[str, Any]:
    fields = disk.sprites[index].fields
    extra = _x(disk.sprites[index])
    type_id = int(fields.get("type", 0))
    row: dict[str, Any] = {
        "kind": "sprite", "id": index, "type_id": type_id,
        "response": STATE_ONLY,
        "engine": ("LinkSprite default (triggers.cpp:1822-1829): the busy is "
                   "copied and SetSpriteState runs only at a whole busy"),
        "follows": False, "needs": {}, "faults": [],
    }
    if not continuous:
        row["engine"] = "OperateSprite (triggers.cpp:1906)"
        return row
    #: kSwitchCombo, the one sprite that reads a Link as DATA rather than as
    #: travel: it copies the sender's data1 and compares it to its own data2.
    if type_id == SWITCH_COMBO:
        row["response"] = COMBO_DIAL
        row["engine"] = "LinkSprite kSwitchCombo (triggers.cpp:1806-1821)"
        row["needs"] = {"data2": int(extra.get("data2", 0))}
    if int(extra.get("locked", 0)):
        row["faults"].append("locked: trMessageSprite:1962 drops the Link")
    return row


#: `kSwitchCombo`, common_game.h:443.
SWITCH_COMBO = 21


def _command_name(command: int) -> str | None:
    from .blood_types import COMMANDS

    entry = COMMANDS.get(int(command))
    return entry["name"] if entry else None


def transmission(disk: Any, sector_id: int, *,
                 receivers: dict[int, list[tuple[str, int]]] | None = None
                 ) -> dict[str, Any] | None:
    """What this sector tells other things to do, and whether they can.

    None when the sector transmits nothing. Otherwise the channel, the verb,
    every listener on that channel by kind, and per listener what the sender's
    `busy` actually does to it -- which for a Link is the difference between a
    light that follows a curtain and a light that ignores it.
    """
    if sector_id >= len(disk.sectors):
        return None
    extra = _x(disk.sectors[sector_id])
    channel = int(extra.get("tx_id", 0)) if extra else 0
    if not channel:
        return None
    command = int(extra.get("command", 0))
    type_id = int(disk.sectors[sector_id].fields["type"])
    continuous = command == LINK
    index = receiver_index(disk) if receivers is None else receivers
    listeners = list(index.get(channel, ()))

    out: dict[str, Any] = {
        "channel": channel,
        "command": command,
        "verb": COMMAND_VERBS.get(command),
        "command_name": _command_name(command),
        "continuous": continuous,
        "sends": None,
        "receivers": [],
        "faults": [],
    }
    if continuous:
        proc = LINK_SENDING_BUSY_PROC.get(type_id)
        if proc is not None:
            out["sends"] = f"kCmdLink every tick of its own travel, from {proc}"
        elif type_id in NO_LINK_SENDER_TYPES:
            out["faults"].append(
                f"command 5 on sector type {type_id}, which runs no Link-"
                f"sending busy proc: {NO_LINK_SENDER_TYPES[type_id]}")
        elif not (int(extra.get("busy_time_a", 0))
                  or int(extra.get("busy_time_b", 0))):
            #: `OperateSector`'s default branch (triggers.cpp:1717-1737)
            #: reaches `GenSectorBusy` only when there is a busy time to run.
            #: With both at zero it calls `SetSectorState` directly, and
            #: :140/:152 refuse to send for a command-5 sector. Such a sector
            #: transmits NOTHING, ever.
            out["faults"].append(
                "command 5 with busy_time_a and busy_time_b both 0: "
                "OperateSector:1718 takes the SetSectorState path and "
                ":140/:152 skip the send for kCmdLink, so nothing is ever "
                "transmitted")
        else:
            out["sends"] = ("kCmdLink every tick of its own travel, from "
                            "GenSectorBusy (triggers.cpp:1454)")
        #: The edge flags are dead weight on a command-5 sector: :140 and :152
        #: test `command != kCmdLink` before consulting them. Recorded rather
        #: than flagged -- it costs nothing, and the campaign is full of it.
        out["edge_flags_ignored"] = bool(int(extra.get("trigger_on", 0))
                                         or int(extra.get("trigger_off", 0)))
    else:
        out["sends"] = ("the verb once, on the state edge its trigger_on / "
                        "trigger_off flags allow (triggers.cpp:140, :152)")
        if not (int(extra.get("trigger_on", 0))
                or int(extra.get("trigger_off", 0))):
            out["faults"].append(
                "neither trigger_on nor trigger_off: SetSectorState:140/:152 "
                "send only inside those flags, so this transmitter is silent")

    for kind, item in listeners:
        if kind == "sector":
            row = _sector_receiver(disk, item, continuous)
        elif kind == "wall":
            row = _wall_receiver(disk, item, continuous)
        else:
            row = _sprite_receiver(disk, item, continuous)
        out["receivers"].append(row)
    if not listeners:
        out["faults"].append(
            f"nothing receives on channel {channel}: the send reaches no one")
    out["drives"] = sorted(row["id"] for row in out["receivers"]
                           if row["kind"] == "sector")
    out["follows"] = sorted(row["id"] for row in out["receivers"]
                            if row["kind"] == "sector" and row["follows"])
    out["cannot_respond"] = [
        {"kind": row["kind"], "id": row["id"], "faults": list(row["faults"])}
        for row in out["receivers"] if row["faults"]]
    return out


def read_mechanism(disk: Any, sector_id: int, *,
                   owners: Sequence[int] | None = None,
                   assembly: Any = None,
                   receivers: dict[int, list[tuple[str, int]]] | None = None
                   ) -> dict[str, Any] | None:
    """All five planes for one moving sector, or None if it does not move."""
    record = observe_motion_sector(
        disk, sector_id,
        owners=list(owners) if owners is not None else None)
    if record is None:
        return None
    neighbours = {int(portal["next_sector"]) for portal in record["portals"]}
    spatial = embedding(
        record,
        (int(disk.sectors[index].fields["floor_z"]) for index in neighbours),
    )
    effects = physical_effects(record)
    motion = swept_motion(disk, sector_id, record)
    sweeps = swept_opening(disk, sector_id, motion) if motion else None
    wiring = transmission(disk, sector_id, receivers=receivers)
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "sector_id": sector_id,
        "primitive": {
            "effects": [dict(item) for item in effects],
            "swept": motion,
            "swept_opening": sweeps,
            "motion": record["motion"],
            "type_id": record["type_id"],
            "period": record["busy_time_a"],
            "interaction": record["interaction"],
            "triggers": list(record["triggers"]),
        },
        "carried": carried_parts(assembly),
        "embedding": spatial,
        "style": style(record),
        #: Plane 5. `drives` is the flat list of sectors on the far end of
        #: this mechanism's channel -- the short answer to "what does it
        #: drive" -- and `transmission` beside it carries the verb, the
        #: receivers of every kind, and what each one does with the busy.
        #: Two keys rather than one because the flat list is what a caller
        #: comparing two readings wants, and burying it inside the facet
        #: would make every such comparison walk a dict.
        "transmission": wiring,
        "drives": list(wiring["drives"]) if wiring else [],
        #: Last, and from the embedding alone.
        "design_object": design_object(
            spatial, sweeps=sweeps,
            moves_in_z=any(item["effect"] in (MOVE_FLOOR_Z, MOVE_CEILING_Z)
                           for item in effects)),
    }


def read_map_mechanisms(disk: Any, *, map_name: str = "") -> dict[str, Any]:
    """Every moving sector of one map, read the same way."""
    owners = _wall_owners(disk)
    #: Once for the map, not once per mechanism: the scan is over every
    #: sector, wall and sprite, and E1M1 alone would repeat it 24 times.
    receivers = receiver_index(disk)
    readings = []
    for sector_id in range(len(disk.sectors)):
        reading = read_mechanism(disk, sector_id, owners=owners,
                                 receivers=receivers)
        if reading is not None:
            readings.append(reading)
    return {
        "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "map": map_name, "count": len(readings), "mechanisms": readings,
    }
