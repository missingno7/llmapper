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
#: A body on its knees, from the profile the whole repo measures against.
#: Worth a separate question from standing, because the largest single shape
#: in the residue below is a gap that opens to more than this and less than a
#: standing body -- a way through that a body has to duck for.
CROUCH_HEIGHT = PLAYER_PROFILES["blood"].crouch_height or PLAYER_HEIGHT

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


def design_object(spatial: dict[str, Any], *, moves_in_z: bool = True) -> str:
    """Plane 3's conclusion: what the thing *is*, from where it sits.

    Takes the embedding and nothing else. There is deliberately no way to
    hand this function a sector type, because a sector type is what it must
    not consult.

    `moves_in_z` is not an exception to that. It says whether the question
    this function asks even applies -- both clauses are about a vertical
    opening -- and a mechanism that only slides or turns gets `UNCLASSIFIED`
    rather than a confident wrong answer.
    """
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
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "sector_id": sector_id,
        "primitive": {
            "effects": [dict(item) for item in effects],
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
            spatial,
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
