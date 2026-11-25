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
static set is exactly the walls whose endpoints do not move. A rigid body's
members share one sweep for the loops they drag and for clearance, as the
nine slides of MACHINERY-1WAYVEHICLE s2–10 need.

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

from .model import record_extra, record_fields
from .motion_sim import (
    _body_timing_notes, blood_sweep, body_health, closure_health, rigid_bodies,
    sector_loops, self_intersections,
    driven_walls,
)
from .player_space import PLAYER_PROFILES

#: The four horizontally-moving Blood sector types.
MOVING_TYPES = (614, 615, 616, 617)

#: A sector this small has no usable inside. One player width squared.
MIN_AREA = float(PLAYER_PROFILES["blood"].body_width ** 2)

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


def hosts(disk: Any) -> dict[int, set[int]]:
    """The sectors each moving sector's dragged walls border: {host: {movers}}.

    A mover sweeps through these. Cutting one along the sweep would put a
    wall in the way of a moving one, so a pass that splits sectors leaves
    them whole (`light_stage`).
    """
    from .motion import moved_points
    from .sector_geom import sector_walls

    out: dict[int, set[int]] = {}
    for mover in moving_sectors(disk):
        moved = set(moved_points(disk, mover))
        for wall in sector_walls(disk, mover):
            f = disk.walls[wall].fields
            end = disk.walls[int(f["point2"])].fields
            other = int(f["next_sector"])
            if other >= 0 and {(int(f["x"]), int(f["y"])), (int(end["x"]), int(end["y"]))} & moved:
                out.setdefault(other, set()).add(mover)
    return out


def escape(disk: Any, sector_id: int, frames: Any) -> str | None:
    """Why an island's sweep leaves the one sector it stands in, or None.

    The rule of the engine (the owner, 2026-11-23): "moving or rotating
    sector can never leave it's parent sector". It is asked of a mover whose
    every wall borders the same sector; one set between several rooms moves
    its boundary with them, and the closure check answers for that.
    """
    from shapely.geometry import Polygon

    from .sector_geom import outline_and_holes, sector_walls

    around = {int(record_fields(disk.walls[w])["next_sector"])
              for w in sector_walls(disk, sector_id)}
    if len(around) != 1 or -1 in around:
        return None
    host = around.pop()
    room = Polygon(outline_and_holes(disk, host)[0]).buffer(1)
    for step, frame in enumerate(frames):
        left = Polygon(frame).buffer(0).difference(room).area
        if left > 1:
            return f"step {step}: it leaves sector {host}, the one it stands in, by {left:.0f} square units"
    return None


def moving_sectors(disk: Any) -> list[int]:
    return [index for index, sector in enumerate(disk.sectors)
            if int(record_fields(sector)["type"]) in MOVING_TYPES
            and record_extra(sector) is not None]


def sweep_sector(disk: Any, sector_id: int, *, steps: int = 16,
                 in_body: bool = False, driven: Any = None) -> SweptFinding:
    """Step one mechanism through its travel and check the geometry."""
    type_id = int(record_fields(disk.sectors[sector_id])["type"])
    found = SweptFinding(sector=sector_id, type_id=type_id, steps=steps)
    try:
        frames = blood_sweep(disk, sector_id, steps=steps)
    except Exception as exc:
        found.problems.append(f"cannot be swept at all: {exc}")
        return found

    own = [frames]
    if in_body:
        # The standalone reader's historic wall-order polygon includes jumps
        # between loops. A rigid member can have holes (e.g. E2M1 s87).
        first = int(record_fields(disk.sectors[sector_id])["wall_ptr"])
        own = [[[frame[w - first] for w in loop] for frame in frames]
               for loop in sector_loops(disk, sector_id)]
        own.sort(key=lambda loop: abs(polygon_area_signed(loop[-1])), reverse=True)
    for loop in own:
        _check_own_frames(found, loop, steps)
    if not in_body:
        left = escape(disk, sector_id, frames)
        if left:
            found.problems.append(left)
    found.problems.extend(_closure(disk, sector_id, found, steps=steps, in_body=in_body, driven=driven))
    return found


def _check_own_frames(found: SweptFinding, frames: Any, steps: int) -> None:
    signed = [polygon_area_signed(frame) for frame in frames]
    if not found.areas:
        found.areas = [round(abs(value), 1) for value in signed]
    first = signed[0]
    for index, value in enumerate(signed):
        where = f"step {index}/{steps}"
        if first and value and (first > 0) != (value > 0):
            found.problems.append(
                f"{where}: the sector inverts -- its outline winds the other "
                f"way, so it is inside out from here on")
            break
    largest = max(abs(v) for v in signed)
    if largest < MIN_AREA:
        # never a place a body stood: E1M2 s261, the freezer's bloody button, is
        # 64 by 512 pressed and nothing at all at rest
        found.notes.append(f"a button: {largest:.0f} of area at most")
    for index, value in enumerate(signed if largest >= MIN_AREA else ()):
        # Collapse is losing area. A leaf turned or slid whole keeps its own,
        # however thin it is drawn: the campaign hangs its wooden doors 64
        # thick and 1,024 long (E2M5 569), under this threshold at every pose.
        if abs(value) >= MIN_AREA or abs(value) >= 0.9 * largest:
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


def _closure(disk: Any, sector_id: int, found: SweptFinding,
             *, steps: int, in_body: bool, driven: Any = None) -> list[str]:
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
        health = closure_health(disk, sector_id, steps=steps, in_body=in_body, driven=driven)
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
    """Sweep each mechanism's own geometry and each rigid body's shared geometry."""
    bodies = rigid_bodies(disk)
    members = {sector for body in bodies for sector in body.members}
    driven = driven_walls(disk)
    findings = [sweep_sector(disk, sector_id, steps=steps,
                             in_body=sector_id in members, driven=driven)
                for sector_id in moving_sectors(disk)]
    body_reports = [body_health(disk, body, steps=steps) for body in bodies]
    problems = [f"sector {item.sector} (type {item.type_id}): {line}"
                for item in findings for line in item.problems]
    notes = [f"sector {item.sector} (type {item.type_id}): {line}"
             for item in findings for line in item.notes]
    for body in body_reports:
        problems.extend(f"body {body['members']}: {line}" for line in body["problems"])
        notes.extend(f"body {body['members']}: {line}" for line in body["notes"])
    notes.extend(note for pair, note in _body_timing_notes(disk).items()
                 if members.isdisjoint(pair))
    return {
        "$schema": "llmapper.swept-state", "schema_version": 1,
        "mechanisms": len(findings),
        "sound": sum(1 for item in findings if item.sound),
        "steps": steps,
        "bodies": body_reports,
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
