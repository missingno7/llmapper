"""What a mechanism physically does, said neutrally.

A **reading** over what `doors.py`, `assembly.py` and `motion_sim.py` already
record — not a parallel framework and not a catalog of named prefabs. Nothing
here re-derives geometry; every number comes from `observe_motion_sector` or
`assembly_around`.

The reading is factored along four planes, and keeping them apart is the whole
point:

1. **primitive** — what the engine physically does: a surface moves in z, a
   sector translates, a sector turns about an axis. Engine fact, no meaning.
2. **carried** — what rides the motion, and how it is attached.
   `assembly.py`'s domain.
3. **embedding** — where it sits: what the motion does to occupancy and
   reachability. **This is where meaning is born.**
4. **style** — how the thing is made readable: a face unlike its surround, a
   signifier beside it, see-through leaves.

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
#: sprites: `marker_0` gives the rest position and angle, `marker_1` the
#: moved one. A rotate carries one marker and turns about it; a slide
#: carries two and travels between them.
MARKER_REST, MARKER_MOVED = "marker_0", "marker_1"

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
    for role in (MARKER_REST, MARKER_MOVED):
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
    rest = markers.get(MARKER_REST)
    moved = markers.get(MARKER_MOVED)
    kind = TRANSLATE_XY if type_id in SLIDE_TYPES else ROTATE_ABOUT_AXIS
    out: dict[str, Any] = {
        "effect": kind, "type_id": type_id, "markers": markers,
        "payload": payload(disk, sector_id),
        "period": int(record["busy_time_a"]),
    }
    if rest is None:
        #: A marked motion with no rest marker cannot be interpolated, so
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


def read_mechanism(disk: Any, sector_id: int, *,
                   owners: Sequence[int] | None = None,
                   assembly: Any = None) -> dict[str, Any] | None:
    """All four planes for one moving sector, or None if it does not move."""
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
        #: Last, and from the embedding alone.
        "design_object": design_object(
            spatial, sweeps=sweeps,
            moves_in_z=any(item["effect"] in (MOVE_FLOOR_Z, MOVE_CEILING_Z)
                           for item in effects)),
    }


def read_map_mechanisms(disk: Any, *, map_name: str = "") -> dict[str, Any]:
    """Every moving sector of one map, read the same way."""
    owners = _wall_owners(disk)
    readings = []
    for sector_id in range(len(disk.sectors)):
        reading = read_mechanism(disk, sector_id, owners=owners)
        if reading is not None:
            readings.append(reading)
    return {
        "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "map": map_name, "count": len(readings), "mechanisms": readings,
    }
