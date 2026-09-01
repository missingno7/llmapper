"""Validate a map's geometry through the WHOLE of every motion, not at rest.

The gap that let the zoo ship a casket whose cover inverted. `validate_map`,
the geometry audit, the usage laws and the self-reading gate all inspect the
pose the map is SAVED in. A moving sector is only in that pose for one
instant of its life, and everything wrong with the zoo's casket happened
somewhere else in the travel: a boundary sweeping 2288 units past the far
wall of the sector receiving it, turning that sector inside out.

So this steps each mechanism through its own travel with
`bloodmap.motion_sim` -- which transcribes `TranslateSector`, including the
`trInit` base displacement that makes a state-0 sector jump the moment the
level loads -- and asks at every step:

* does the moving outline **self-intersect**? A sector whose walls cross is a
  degenerate loop the renderer cannot draw and the clipper cannot solve.
* has it **inverted**? Signed area changing sign means the loop wound the
  other way: the sector turned inside out.
* has it **collapsed**? Area at or near zero is a sector with no inside.
* does it **have clearance**? A mechanism that sweeps through the wall of a
  room it does not move is the fault the rotors were always suspected of and
  nothing ever checked.

What it sweeps is the `DragPoint` CLOSURE, not the mover's polygon. The
engine never moves a polygon: `TranslateSector` drags vertices, and
`DragPoint` (triggers.cpp:817-854) sets each one for every wall that shares
it across `nextwall` -- so a flagged wall shared with a neighbour deforms the
neighbour, and the curriculum says that is the normal case. The first
version of this gate swept only the mover and called every neighbour static;
it passed a strip whose thin neighbour was inside out from the moment the
level loaded (`tests/test_swept_state.py::DragClosureGateTest`). Now every
loop with a moved vertex is checked for inversion and self-crossing, and the
static set is exactly the walls whose endpoints do not move.

A check this file used to make and no longer does: whether the sector sits
away from its drawn outline at rest. That is not measurable. `trInit` derives
the base FROM the markers -- base = drawn minus delta -- so a state-0 sector
displaces by the marker separation by construction, and the two can never
disagree. The test that was supposed to catch a disagreement had to move a
marker to provoke one, which moved the separation with it. A check that
cannot fail proves nothing, so it is gone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .motion_sim import (
    blood_sweep, closure_health, polygon_area, rest_displacement,
    self_intersections,
)

#: The four horizontally-moving Blood sector types.
MOVING_TYPES = (614, 615, 616, 617)

#: A sector this small has no usable inside. One player width squared.
MIN_AREA = 384.0 * 384.0

#: How far a sector may sit from its drawn outline at load before it is worth
#: telling the author about. Half a player width.
REST_TOLERANCE = 192.0


@dataclass
class SweptFinding:
    """What one mechanism did across its whole travel."""

    sector: int
    type_id: int
    steps: int
    areas: list[float] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    #: The DragPoint closure: which sectors the motion deforms besides the
    #: mover, the loops it touched, and where nextwall and coordinates
    #: disagree about who shares a vertex.
    closure: dict[str, Any] = field(default_factory=dict)

    @property
    def sound(self) -> bool:
        return not self.problems


def moving_sectors(disk: Any) -> list[int]:
    return [index for index, sector in enumerate(disk.sectors)
            if int(sector.fields["type"]) in MOVING_TYPES
            and sector.extra is not None]


def sweep_sector(disk: Any, sector_id: int, *, steps: int = 16) -> SweptFinding:
    """Step one mechanism through its travel and check the geometry."""
    type_id = int(disk.sectors[sector_id].fields["type"])
    found = SweptFinding(sector=sector_id, type_id=type_id, steps=steps)
    try:
        frames = blood_sweep(disk, sector_id, steps=steps)
    except Exception as exc:
        found.problems.append(f"cannot be swept at all: {exc}")
        return found

    signed = [polygon_area_signed(frame) for frame in frames]
    found.areas = [round(abs(value), 1) for value in signed]
    first = signed[0]
    for index, value in enumerate(signed):
        where = f"step {index}/{steps}"
        if first and value and (first > 0) != (value > 0):
            found.problems.append(
                f"{where}: the sector inverts -- its outline winds the other "
                f"way, so it is inside out from here on")
            break
    for index, value in enumerate(signed):
        if abs(value) >= MIN_AREA:
            continue
        #: A curtain drawn fully across has no interior left, and
        #: DOOR-CURTAINS s24 does exactly that at its OFF pose. That is a
        #: closed door, not a broken sector -- so a collapse is only a fault
        #: when it happens PART WAY through, where nothing is meant to be
        #: shut.
        if index in (0, steps):
            found.notes.append(
                f"step {index}/{steps}: closes to {abs(value):.0f} of area, "
                f"which is a mechanism that shuts completely")
            continue
        found.problems.append(
            f"step {index}/{steps}: area collapses to {abs(value):.0f} part "
            f"way through the travel, under one player width squared")
        break
    for index, frame in enumerate(frames):
        crossings = self_intersections(frame)
        if crossings:
            found.problems.append(
                f"step {index}/{steps}: {len(crossings)} wall crossing(s) -- "
                f"a degenerate loop the renderer cannot draw")
            break

    found.problems.extend(_closure(disk, sector_id, found, steps=steps))
    return found


def _closure(disk: Any, sector_id: int, found: SweptFinding,
             *, steps: int) -> list[str]:
    """Everything the motion drags, swept: neighbours, and the static set.

    `closure_health` walks `nextwall` as `DragPoint` does, so the loops it
    returns are the ones the engine actually deforms. Three kinds of problem
    come back: a dragged loop (the mover's own or a neighbour's) that inverts
    against its DRAWN winding, one that crosses itself, and a moving wall
    that properly crosses a wall whose endpoints do not move -- the check
    the rotors never had. The mover's own inversion and self-crossing are
    already reported above against its first frame, so only its neighbours'
    are added here.

    A vertex that coincides with the moved one but is not chained to it is
    not a problem for the gate -- the engine simply leaves it behind -- but it
    is a map defect, and it is recorded as a note.
    """
    try:
        health = closure_health(disk, sector_id, steps=steps)
    except Exception as exc:                        # pragma: no cover
        return [f"cannot sweep the drag closure: {exc}"]
    found.closure = {
        "sectors": health["sectors"],
        "neighbours": health["neighbours"],
        "coincidence_sectors": health["coincidence_sectors"],
        "co_movers": health["co_movers"],
        "isolated": health["isolated"],
        "moved_walls": health["moved_walls"],
        "loops": [(row["sector"], row["loop"]) for row in health["loops"]],
        "disagreements": health["disagreements"],
    }
    found.notes.extend(health["notes"])
    for item in health["disagreements"]:
        found.notes.append(
            f"vertex ({item['vertex'][0]}, {item['vertex'][1]}) is "
            f"{item['kind']}: {item['why']}")
    problems: list[str] = []
    for line in health["problems"]:
        own = (f"loop 0 of sector {sector_id} " in line
               and "drags through" not in line)
        if own and ("inverts" in line or "crosses itself" in line):
            continue
        problems.append(line)
    return problems


def polygon_area_signed(polygon: Iterable[Any]) -> float:
    """Twice the signed area, halved: sign is the winding."""
    points = list(polygon)
    total = 0.0
    for index, (x, y) in enumerate(points):
        nx, ny = points[(index + 1) % len(points)]
        total += x * ny - nx * y
    return total / 2.0


def run(disk: Any, *, steps: int = 16) -> dict[str, Any]:
    """Every mechanism in the map, swept."""
    findings = [sweep_sector(disk, sector_id, steps=steps)
                for sector_id in moving_sectors(disk)]
    problems = [f"sector {item.sector} (type {item.type_id}): {line}"
                for item in findings for line in item.problems]
    notes = [f"sector {item.sector} (type {item.type_id}): {line}"
             for item in findings for line in item.notes]
    return {
        "$schema": "llmapper.swept-state", "schema_version": 1,
        "mechanisms": len(findings),
        "sound": sum(1 for item in findings if item.sound),
        "steps": steps,
        "problems": problems,
        "notes": notes,
        "deforming_neighbours": sum(
            1 for item in findings if item.closure.get("neighbours")),
        "per_sector": [
            {"sector": item.sector, "type": item.type_id,
             "areas": item.areas, "problems": item.problems,
             "notes": item.notes, "closure": item.closure}
            for item in findings],
        "passed": not problems,
    }
