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
* does it **displace at rest**? A sector that is not where it was drawn the
  instant the level loads is either authored in the other pose deliberately
  -- Blood's gates are, and say so with `state` -- or is an editor leftover.

The last one is reported rather than failed, because both readings are legal
and only the author knows which was meant. The oracle map is the worked
example: its two planes are drawn in the same physical pose and declare
opposite states, so one of them jumps 1920 units at load.
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
        if abs(value) < MIN_AREA:
            found.problems.append(
                f"step {index}/{steps}: area collapses to {abs(value):.0f}, "
                f"under one player width squared")
            break
    for index, frame in enumerate(frames):
        crossings = self_intersections(frame)
        if crossings:
            found.problems.append(
                f"step {index}/{steps}: {len(crossings)} wall crossing(s) -- "
                f"a degenerate loop the renderer cannot draw")
            break

    displacement = rest_displacement(disk, sector_id, frames)
    if displacement > REST_TOLERANCE:
        found.notes.append(
            f"sits {displacement:.0f} units from its drawn outline at load; "
            f"either it is authored in the other pose on purpose (Blood's "
            f"gates are, and say so with `state`) or the state is a leftover")
    return found


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
