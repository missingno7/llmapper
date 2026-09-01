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
    blood_sweep, polygon_area, rest_displacement, self_intersections,
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

    found.problems.extend(_clearance(disk, sector_id, frames))
    return found


def _segments(points: list[Any]) -> list[tuple[Any, Any]]:
    return [(points[i], points[(i + 1) % len(points)])
            for i in range(len(points))]


def _crosses(a1, a2, b1, b2) -> bool:
    """Do two segments properly cross? Touching at an endpoint does not."""
    def side(p, q, r):
        value = ((q[0] - p[0]) * (r[1] - p[1])
                 - (q[1] - p[1]) * (r[0] - p[0]))
        return (value > 1e-9) - (value < -1e-9)

    d1, d2 = side(a1, a2, b1), side(a1, a2, b2)
    d3, d4 = side(b1, b2, a1), side(b1, b2, a2)
    return d1 * d2 < 0 and d3 * d4 < 0


def _clearance(disk: Any, sector_id: int, frames: list[Any]) -> list[str]:
    """Does the swept outline cut through geometry it does not move?

    The check the rotors never had. A mechanism may deform the sectors it
    declares -- that is the normal case in the tutorials -- but a wall
    belonging to a sector OUTSIDE its motion set is static, and an outline
    that crosses one is a mechanism travelling through a room.

    Only proper crossings count: a moving wall sharing an endpoint with a
    static one is a hinge, which is how most of these are built.
    """
    from .motion import motion_set, sector_walls

    try:
        moving = set(motion_set(disk, sector_id)["sectors"])
    except Exception:
        moving = {sector_id}
    static = []
    for other in range(len(disk.sectors)):
        if other in moving:
            continue
        for wall_id in sector_walls(disk, other):
            fields = disk.walls[wall_id].fields
            end = disk.walls[int(fields["point2"])].fields
            static.append(((int(fields["x"]), int(fields["y"])),
                           (int(end["x"]), int(end["y"])), other, wall_id))
    if not static:
        return []
    for index, frame in enumerate(frames):
        for a1, a2 in _segments(list(frame)):
            for b1, b2, other, wall_id in static:
                if _crosses(a1, a2, b1, b2):
                    return [
                        f"step {index}/{len(frames) - 1}: the outline cuts "
                        f"through wall {wall_id} of sector {other}, which "
                        f"this mechanism does not move -- it sweeps through "
                        f"standing geometry"]
    return []


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
        "per_sector": [
            {"sector": item.sector, "type": item.type_id,
             "areas": item.areas, "problems": item.problems,
             "notes": item.notes}
            for item in findings],
        "passed": not problems,
    }
