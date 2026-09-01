"""Replay a moving sector in both engines and compare where the walls end up.

A converted door can pass structural validation, load in NBlood and still be
wrong: it can open a quarter of the way, turn the wrong direction, sweep through
the wall beside it, or rotate while it is supposed to slide.  None of that shows
up in a sector count.  The only check that actually answers "is this the same
motion" is to run both engines' geometry over the whole travel and compare the
wall positions.

Both routines are transcribed here rather than approximated:

``A_MoveSector`` (EDuke32 ``actors.cpp``) puts wall *w* at
``effector.xy + rotatevec(origin[w], T3)``, where ``origin[w]`` was captured at
spawn as ``wall[w].xy - effector.xy``.

``TranslateSector`` (NBlood ``triggers.cpp``) puts wall *w* at
``RotatePoint(baseWall[w], vbp, a4, a5) + (vc - a4, v8 - a5)``, where the three
interpolants run between the marker sprites as ``busy`` goes 0 -> 65536.

The two rotations are the same rotation: Build's ``rotatevec`` uses
``cos = sintable[(a+2560)&2047]``, ``sin = sintable[(a+2048)&2047]`` and Blood's
``RotatePoint`` uses ``Cos(a)``/``Sin(a)`` with the same signs, so a positive
Duke ``T3`` and a positive Blood marker angle turn the same way.  That is what
makes the comparison meaningful instead of a sign convention argument.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .duke import DukeDiskMap
from .duke_motion import rotate_rise_bridge, sliding_door, stretch_bridge, swinging_door

Point = tuple[float, float]
Polygon = list[Point]

#: Build's ``sintable`` is a 2048-entry sine scaled by 16384.
SINE_SCALE = 16384


def build_sin(angle: int) -> float:
    return math.sin((angle & 2047) * math.pi / 1024.0) * SINE_SCALE


def rotatevec(x: float, y: float, angle: int) -> Point:
    """Build's ``rotatevec``, in floating point.

    Kept in floats deliberately: this is a comparison tool, and reproducing the
    engines' integer truncation would add a unit of noise to a measurement whose
    whole point is to detect deviations far larger than a unit.
    """
    cos = build_sin(angle + 512)
    sin = build_sin(angle)
    return ((x * cos - y * sin) / SINE_SCALE, (y * cos + x * sin) / SINE_SCALE)


def rotate_about(point: Point, angle: int, origin: Point) -> Point:
    dx, dy = point[0] - origin[0], point[1] - origin[1]
    rx, ry = rotatevec(dx, dy, angle)
    return (origin[0] + rx, origin[1] + ry)


def duke_sector_walls(duke: DukeDiskMap, sector_id: int) -> Polygon:
    sector = duke.sectors[sector_id]
    start = int(sector.wall_ptr)
    return [
        (float(duke.walls[w].x), float(duke.walls[w].y))
        for w in range(start, start + int(sector.wall_count))
    ]


def blood_sector_walls(level: Any, sector_id: int) -> Polygon:
    fields = level.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    return [
        (float(level.walls[w].fields["x"]), float(level.walls[w].fields["y"]))
        for w in range(start, start + int(fields["wall_count"]))
    ]


def duke_sweep(duke: DukeDiskMap, effector_index: int, *, steps: int = 16) -> list[Polygon]:
    """Wall positions across a Duke moving sector's whole travel.

    Returns ``steps + 1`` polygons, the first being the authored geometry.
    Raises ``ValueError`` for an effector whose motion this does not model.
    """
    sprite = duke.sprites[effector_index]
    if sprite.picnum != 1:
        raise ValueError(f"sprite {effector_index} is not a sector effector")
    sector_id = sprite.sector
    walls = duke_sector_walls(duke, sector_id)
    lotag = sprite.lotag
    sector_tag = duke.sectors[sector_id].lotag & 0x3FFF

    if lotag == 11:
        motion = swinging_door(duke, sprite)
        centre = (float(sprite.x), float(sprite.y))
        return [
            [rotate_about(p, round(motion["angle"] * i / steps), centre) for p in walls]
            for i in range(steps + 1)
        ]

    if lotag == 15:
        motion = sliding_door(duke, sprite)
        radians = motion["angle"] * math.pi / 1024.0
        dx, dy = math.cos(radians), math.sin(radians)
        return [
            [(p[0] + motion["distance"] * dx * i / steps,
              p[1] + motion["distance"] * dy * i / steps) for p in walls]
            for i in range(steps + 1)
        ]

    if lotag == 20:
        motion = stretch_bridge(duke, sprite)
        radians = motion["angle"] * math.pi / 1024.0
        dx, dy = math.cos(radians), math.sin(radians)
        first = int(duke.sectors[sector_id].wall_ptr)
        moved = {w - first for w in motion["walls"]}
        frames = []
        for i in range(steps + 1):
            step_x = motion["distance"] * dx * i / steps
            step_y = motion["distance"] * dy * i / steps
            frames.append([
                (p[0] + step_x, p[1] + step_y) if index in moved else p
                for index, p in enumerate(walls)
            ])
        return frames

    if lotag == 0 and sector_tag == 30:
        pivot = next(
            (s for s in duke.sprites if s.picnum == 1 and s.lotag == 1 and s.hitag == sprite.hitag),
            None,
        )
        if pivot is None:
            raise ValueError(f"SE0 sprite {effector_index} has no SE1 pivot")
        motion = rotate_rise_bridge(duke, sprite, pivot)
        centre = (float(motion["centre_x"]), float(motion["centre_y"]))
        return [
            [rotate_about(p, round(motion["angle"] * i / steps), centre) for p in walls]
            for i in range(steps + 1)
        ]

    raise ValueError(f"SE{lotag} in ST{sector_tag} is not a modelled moving sector")


@dataclass
class Travel:
    """`TranslateSector`'s eight marker arguments plus where the sector rests.

    ``(a4, a5)`` is the pivot, ``(a6, a7, a8)`` the OFF position and angle,
    ``(a9, a10, a11)`` the ON position and angle; ``rest`` is the busy the
    sector sits at when the level loads (``xsector.state``), and the travel
    runs from ``rest`` to ``1 - rest``.
    """

    a4: float
    a5: float
    a6: float
    a7: float
    a8: float
    a9: float
    a10: float
    a11: float
    rest: float

    def place(self, point: Point, sign: float, busy: float) -> Point:
        """One base point, moved as `TranslateSector` moves it at `busy`."""
        vc = self.a6 + (self.a9 - self.a6) * busy
        v8 = self.a7 + (self.a10 - self.a7) * busy
        vbp = self.a8 + (self.a11 - self.a8) * busy
        moved = point
        if vbp:
            moved = rotate_about(point, round(sign * vbp), (self.a4, self.a5))
        return (moved[0] + sign * (vc - self.a4), moved[1] + sign * (v8 - self.a5))

    def busies(self, steps: int) -> list[float]:
        target = 1.0 - self.rest
        return [self.rest + (target - self.rest) * (i / steps) for i in range(steps + 1)]


def blood_travel(level: Any, sector_id: int) -> Travel:
    """Read a moving sector's markers into the arguments `trInit` passes.

    Raises ``ValueError`` for a sector that does not move horizontally or has
    no markers, exactly as `blood_sweep` always has.
    """
    sector = level.sectors[sector_id]
    kind = int(sector.fields["type"])
    if kind not in (614, 615, 616, 617):
        raise ValueError(f"sector {sector_id} has type {kind}, which does not move horizontally")
    if sector.extra is None:
        raise ValueError(f"sector {sector_id} has no XSECTOR")
    extra = sector.extra.fields

    # Sprite 0 is a real sprite, so an unset marker is -1 rather than 0. Marker
    # angles are read raw: Blood interpolates 0 -> ang linearly, so the sign is
    # the direction of travel and a magnitude past 2048 is more than one turn.
    marker0 = int(extra.get("marker_0", -1))
    if marker0 < 0:
        raise ValueError(f"sector {sector_id} has no marker0")
    m0 = level.sprites[marker0].fields
    if kind in (617, 615):
        a4, a5 = float(m0["x"]), float(m0["y"])
        a6, a7, a8 = a4, a5, 0.0
        a9, a10, a11 = a4, a5, float(int(m0["angle"]))
    else:
        marker1 = int(extra.get("marker_1", -1))
        if marker1 < 0:
            raise ValueError(f"sector {sector_id} has no marker1")
        m1 = level.sprites[marker1].fields
        a4, a5 = float(m0["x"]), float(m0["y"])
        a6, a7, a8 = a4, a5, float(int(m0["angle"]))
        a9, a10, a11 = float(m1["x"]), float(m1["y"]), float(int(m1["angle"]))
    rest = 1.0 if int(extra.get("state", 0)) else 0.0
    return Travel(a4, a5, a6, a7, a8, a9, a10, a11, rest)


def blood_sweep(level: Any, sector_id: int, *, steps: int = 16,
                by_loop: bool = False) -> list[Polygon] | dict[tuple[int, int], list[Polygon]]:
    """Wall positions across a Blood moving sector's whole travel.

    Transcribes ``TranslateSector`` for the four moving types, including the
    ``bAllWalls`` split: 616/617 move every wall, 614/615 move only walls
    flagged ``cstat & 16384`` (forward) or ``& 32768`` (reverse).

    The default return is ``steps + 1`` polygons of the mover's OWN walls in
    sector order, which is what every existing caller reads. With
    ``by_loop=True`` it returns frames for EVERY loop the motion touches,
    keyed ``(sector, loop_index)`` -- the mover's loops and every neighbour
    loop `DragPoint` deforms -- because the engine moves vertices, not the
    mover's polygon, and a neighbour can invert while the mover stays sound.
    Both come from one simulation (`closure_sweep`), so they cannot disagree.

    A flagged wall drags its OWN vertex and its `point2`'s -- unless that
    next wall is itself flagged, in which case it moves under its own
    sign. `triggers.cpp:902` and `:917`:

        if (wall[nWall].cstat&16384) {
            DragPoint(nWall, ...);
            if ((wall[v10].cstat&49152) == 0) DragPoint(v10, ...);

    That propagation is how flagging ONE wall translates a whole EDGE,
    and without it the model shears every Marked slide instead of sliding
    it: the oracle's lid came back as a trapezoid of 2228224 units where
    the engine gives a 2048x128 strip. Every conclusion drawn from a swept
    area before this was measuring the wrong shape.

    trInit does not treat the authored geometry as the resting pose. It runs
    TranslateSector once at busy = -65536 -- a full travel *backwards* --
    calls setBaseWallSect to make that the reference, and only then moves to
    the sector's real busy. So the coordinates in the MAP are the pose at
    busy = 1, and a sector left at state 0 displaces itself by the whole
    marker separation the moment the level loads.
    """
    swept = closure_sweep(level, sector_id, steps=steps)
    if by_loop:
        return swept.loops
    fields = level.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    own = range(start, start + int(fields["wall_count"]))
    return [[swept.position(step, wall) for wall in own] for step in range(steps + 1)]


def blood_poses(level: Any, sector_id: int) -> tuple[Polygon, Polygon]:
    """The OFF outline and the ON outline, in that order, whatever it rests at.

    `blood_sweep` runs from the sector's REST pose outwards, because that is
    the order a player sees. So its first frame is busy 0 for a state-0
    sector and busy 65536 for a state-1 one, and anything that reads
    `frames[0]` as "OFF" mislabels every mechanism authored to start open.
    The zoo's two casket lids are exactly that, and their state pair was
    printed backwards until this existed.
    """
    frames = blood_sweep(level, sector_id, steps=1)
    extra = level.sectors[sector_id].extra
    rests_on = bool(int(extra.fields.get("state", 0))) if extra else False
    return (frames[-1], frames[0]) if rests_on else (frames[0], frames[-1])


def rest_displacement(level: Any, sector_id: int, frames: Sequence[Polygon]) -> float:
    """How far the sector sits from its authored outline before anything moves.

    ``compare_sweeps`` deliberately measures each sweep relative to its own
    first frame, so it cannot see a mechanism that is displaced *at rest* -- and
    a sector that is already rotated or shifted when the level loads is a real
    defect that looks perfect to a relative comparison.  This is the missing
    half: it should be zero.

    The case it catches is a slide whose two markers carry the same non-zero
    angle.  ``TranslateSector`` computes the rotation as
    ``interpolate(marker0.ang, marker1.ang, busy)`` and ``interpolate(a, a, t)``
    is ``a`` for every ``t``, so the sector is turned by that angle for the whole
    travel, at rest included, and never reaches zero.
    """
    authored = blood_sector_walls(level, sector_id)
    return max(
        math.hypot(a[0] - b[0], a[1] - b[1])
        for a, b in zip(authored, frames[0])
    )


def polygon_area(polygon: Sequence[Point]) -> float:
    total = 0.0
    for i, (x1, y1) in enumerate(polygon):
        x2, y2 = polygon[(i + 1) % len(polygon)]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _segments(polygon: Sequence[Point]) -> list[tuple[Point, Point]]:
    return [(polygon[i], polygon[(i + 1) % len(polygon)]) for i in range(len(polygon))]


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segments_cross(p1: Point, p2: Point, p3: Point, p4: Point, *, eps: float = 1e-9) -> bool:
    """Proper crossing only: touching endpoints do not count.

    Adjacent walls of a sector share an endpoint by construction, so counting
    contact would report every polygon as self-intersecting.
    """
    d1, d2 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    d3, d4 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    if abs(d1) < eps or abs(d2) < eps or abs(d3) < eps or abs(d4) < eps:
        return False
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def self_intersections(polygon: Sequence[Point]) -> list[tuple[int, int]]:
    """Non-adjacent wall pairs of one sector that cross.

    A sector whose own outline crosses itself is not a sector any more: Build's
    renderer and clipper both assume a simple loop.  A door that folds through
    itself partway through its travel will do visible and physical damage even
    though the map file validates.
    """
    segments = _segments(polygon)
    count = len(segments)
    found: list[tuple[int, int]] = []
    for i in range(count):
        for j in range(i + 1, count):
            if j == i or (j + 1) % count == i or (i + 1) % count == j:
                continue
            if segments_cross(*segments[i], *segments[j]):
                found.append((i, j))
    return found


def polygons_overlap(a: Sequence[Point], b: Sequence[Point]) -> bool:
    """Whether two sector outlines cross edges or one contains the other."""
    for s1 in _segments(a):
        for s2 in _segments(b):
            if segments_cross(*s1, *s2):
                return True
    return point_in_polygon(a[0], b) or point_in_polygon(b[0], a)


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in _segments(polygon):
        if (y1 > y) != (y2 > y):
            t = (y - y1) / (y2 - y1) if y2 != y1 else 0.0
            if x < x1 + t * (x2 - x1):
                inside = not inside
    return inside


def sweep_health(frames: Sequence[Polygon] | Mapping[tuple[int, int], Sequence[Polygon]],
                 *, static: Iterable[Polygon] = ()) -> dict[str, Any]:
    """Geometric problems a moving sector develops over its travel.

    ``static`` is the set of outlines the mover must not run through -- in
    practice the sectors around it that do not move with it.

    Given the by-loop mapping `blood_sweep(..., by_loop=True)` returns, every
    loop is evaluated and the report carries a ``loops`` list keyed by
    ``(sector, loop)`` with ``healthy`` false if ANY of them folds, inverts
    against its first frame, or collides. `closure_health` is the fuller
    check: it knows the drawn winding and the exact static set.
    """
    if isinstance(frames, Mapping):
        per_loop = []
        for key, loop_frames in frames.items():
            one = sweep_health(loop_frames, static=static)
            signed = [polygon_area(frame) for frame in loop_frames]
            one["inverted_steps"] = [
                step for step, value in enumerate(signed)
                if signed[0] and value and (value > 0) != (signed[0] > 0)]
            one["healthy"] = one["healthy"] and not one["inverted_steps"]
            one["sector"], one["loop"] = key
            per_loop.append(one)
        return {
            "loops": per_loop,
            "healthy": all(one["healthy"] for one in per_loop),
        }
    static_list = list(static)
    folds: list[int] = []
    collisions: list[dict[str, int]] = []
    areas: list[float] = []
    for step, frame in enumerate(frames):
        areas.append(abs(polygon_area(frame)))
        if self_intersections(frame):
            folds.append(step)
        for index, other in enumerate(static_list):
            if polygons_overlap(frame, other):
                collisions.append({"step": step, "static_index": index})
    first, last = areas[0], areas[-1]
    return {
        "steps": len(frames),
        "self_intersecting_steps": folds,
        "collisions": collisions,
        "area_first": round(first, 1),
        "area_last": round(last, 1),
        "area_ratio": round(last / first, 4) if first else None,
        "healthy": not folds and not collisions,
    }


def compare_sweeps(duke_frames: Sequence[Polygon], blood_frames: Sequence[Polygon],
                   *, scale_num: int = 3, scale_den: int = 2) -> dict[str, Any]:
    """Vertex-by-vertex deviation between the two engines' travel.

    The Duke frames are scaled by the measured 3:2 authoring ratio first, and
    both sweeps are re-expressed relative to their own first frame, so this
    measures *the motion* rather than any constant placement offset introduced
    by rounding the level into Blood coordinates.
    """
    if len(duke_frames) != len(blood_frames):
        raise ValueError("sweeps have different step counts")
    if len(duke_frames[0]) != len(blood_frames[0]):
        raise ValueError(
            f"sweeps have different wall counts: {len(duke_frames[0])} and {len(blood_frames[0])}"
        )
    ratio = scale_num / scale_den
    deviations: list[float] = []
    worst = {"step": 0, "wall": 0, "distance": 0.0}
    for step, (duke_frame, blood_frame) in enumerate(zip(duke_frames, blood_frames)):
        for wall, (dp, bp) in enumerate(zip(duke_frame, blood_frame)):
            dx = (dp[0] - duke_frames[0][wall][0]) * ratio
            dy = (dp[1] - duke_frames[0][wall][1]) * ratio
            bx = bp[0] - blood_frames[0][wall][0]
            by = bp[1] - blood_frames[0][wall][1]
            distance = math.hypot(dx - bx, dy - by)
            deviations.append(distance)
            if distance > worst["distance"]:
                worst = {"step": step, "wall": wall, "distance": round(distance, 2)}
    travel = max(
        math.hypot((p[0] - duke_frames[0][i][0]) * ratio, (p[1] - duke_frames[0][i][1]) * ratio)
        for i, p in enumerate(duke_frames[-1])
    )
    peak = max(deviations)
    return {
        "max_deviation": round(peak, 2),
        "mean_deviation": round(sum(deviations) / len(deviations), 2),
        "duke_travel": round(travel, 2),
        "relative_error": round(peak / travel, 4) if travel else None,
        "worst": worst,
        "samples": len(deviations),
    }


# ---------------------------------------------------------------------------
# The DragPoint closure: what a motion moves besides the mover's own polygon
# ---------------------------------------------------------------------------
#
# `TranslateSector` never moves a polygon. It calls `DragPoint` per VERTEX,
# and `DragPoint` (triggers.cpp:817-854) sets that vertex for every wall that
# shares it, found by walking `nextwall` -- forward through each neighbour's
# `point2`, and if that walk hits a one-sided wall, backward again from the
# start through `lastwall().nextwall` (engine.cpp:13227). So a flagged wall
# shared with a neighbour deforms the neighbour, and the curriculum says that
# is the NORMAL case (motion-crosses-storage-boundaries-by-default). A gate
# that sweeps only the mover cannot see a neighbour turning inside out.
#
# None of this sits under NOONE_EXTENSIONS: the only `gModernMap` branch in
# `TranslateSector` (triggers.cpp:874-878, `sprDy`) concerns reverse-flagged
# SPRITES, not walls, and is left alone here.

#: `TranslateSector`'s wall payload flags (triggers.cpp:897 and :912).
MOVES_WITH = 16384
MOVES_AGAINST = 32768
CARRY_FLAGS = MOVES_WITH | MOVES_AGAINST

#: `bAllWalls` is set for exactly these (triggers.cpp:1371, :1398).
ALL_WALL_TYPES = (616, 617)


def _wall_field(level: Any, wall_id: int, key: str) -> int:
    return int(level.walls[wall_id].fields[key])


def wall_owners(level: Any) -> dict[int, int]:
    """Which sector owns each wall."""
    owners: dict[int, int] = {}
    for sector_id, sector in enumerate(level.sectors):
        start = int(sector.fields["wall_ptr"])
        for wall_id in range(start, start + int(sector.fields["wall_count"])):
            owners[wall_id] = sector_id
    return owners


def sector_loops(level: Any, sector_id: int) -> list[list[int]]:
    """Each loop of a sector as its wall ids in `point2` order, first loop first.

    Build's convention (and this project's `construction.py:124`) is that the
    first loop is the outer boundary and the rest are holes.
    """
    fields = level.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    end = start + int(fields["wall_count"])
    seen: set[int] = set()
    loops: list[list[int]] = []
    for wall_id in range(start, end):
        if wall_id in seen:
            continue
        loop: list[int] = []
        current = wall_id
        while current not in seen and start <= current < end:
            seen.add(current)
            loop.append(current)
            current = _wall_field(level, current, "point2")
        loops.append(loop)
    return loops


def last_wall(level: Any, wall_id: int) -> int:
    """Build's `lastwall` (engine.cpp:13227-13248): the wall whose point2 is this.

    Tries the wall just before first, then walks `point2` around the loop;
    returns the argument unchanged if nothing closes on it (the engine does).
    """
    if wall_id > 0 and _wall_field(level, wall_id - 1, "point2") == wall_id:
        return wall_id - 1
    current = wall_id
    for _ in range(len(level.walls)):
        following = _wall_field(level, current, "point2")
        if following == wall_id:
            return current
        current = following
    return wall_id


def drag_chain(level: Any, wall_id: int) -> list[int]:
    """The walls whose vertex `DragPoint(wall_id, x, y)` sets, in engine order.

    A transcription of triggers.cpp:817-854, `vsi` guard included:

        wall[nWall] = (x, y)
        vb = nWall
        do {
            if (wall[vb].nextwall >= 0) {            // forward around the vertex
                vb = wall[wall[vb].nextwall].point2; wall[vb] = (x, y)
            } else {                                 // hit a one-sided wall:
                vb = nWall;                          // go the other way round
                do {
                    if (wall[lastwall(vb)].nextwall >= 0) {
                        vb = wall[lastwall(vb)].nextwall; wall[vb] = (x, y)
                    } else break;
                } while (vb != nWall && --vsi > 0);
                break;
            }
        } while (vb != nWall && --vsi > 0);

    The walk is over `nextwall`, never over coordinates: a wall that merely
    sits on the same point but is not paired to the fan is NOT moved, which
    is what `drag_closure` reports as a disagreement.
    """
    def nextwall(w: int) -> int:
        return _wall_field(level, w, "next_wall")

    chain = [wall_id]
    vsi = len(level.walls)
    vb = wall_id
    while True:
        if nextwall(vb) >= 0:
            vb = _wall_field(level, nextwall(vb), "point2")
            chain.append(vb)
        else:
            vb = wall_id
            while True:
                before = last_wall(level, vb)
                if nextwall(before) >= 0:
                    vb = nextwall(before)
                    chain.append(vb)
                else:
                    break
                vsi -= 1
                if vb == wall_id or vsi <= 0:
                    break
            break
        vsi -= 1
        if vb == wall_id or vsi <= 0:
            break
    ordered: list[int] = []
    for item in chain:
        if item not in ordered:
            ordered.append(item)
    return ordered


def drag_drivers(level: Any, sector_id: int) -> list[tuple[int, float, str]]:
    """``(wall, sign, why)`` for every `DragPoint` call, in the order made.

    616/617 (`bAllWalls`, triggers.cpp:881-888) drag every wall forward.
    614/615 (:892-927) drag a 16384 wall forward and a 32768 wall backward,
    and each also drags its `point2` under the same sign when that wall
    carries no flag of its own (:902, :917). A wall with both flags takes the
    16384 branch, as the engine's `continue` makes it.
    """
    fields = level.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    every = int(fields["type"]) in ALL_WALL_TYPES
    out: list[tuple[int, float, str]] = []
    for wall_id in range(start, start + int(fields["wall_count"])):
        if every:
            out.append((wall_id, 1.0, "bAllWalls"))
            continue
        cstat = _wall_field(level, wall_id, "cstat")
        if cstat & MOVES_WITH:
            sign, why = 1.0, "cstat 16384"
        elif cstat & MOVES_AGAINST:
            sign, why = -1.0, "cstat 32768"
        else:
            continue
        out.append((wall_id, sign, why))
        following = _wall_field(level, wall_id, "point2")
        if not _wall_field(level, following, "cstat") & CARRY_FLAGS:
            out.append((following, sign, f"point2 of {wall_id}"))
    return out


def drag_closure(level: Any, sector_id: int) -> dict[str, Any]:
    """Every (wall, vertex) `DragPoint` would move for this sector's motion.

    ``drivers`` are the `DragPoint` calls in engine order, each with the walls
    its `nextwall` walk reaches (``chain``) and, beside it, the walls that
    merely share the vertex's coordinates (``coincident``). Where the two
    differ the map is defective in one of two ways, and both are reported in
    ``disagreements``:

    * ``coincident but not chained`` -- a wall sits on the moved point but is
      not paired into the fan, so the engine leaves it behind and the motion
      tears the map open at that vertex (an unwelded vertex);
    * ``chained but not coincident`` -- `nextwall` pairs a wall that does not
      actually start at the vertex, so the drag snaps it there (a broken
      pairing).

    ``moved`` is the union in last-writer-wins order, ``loops`` the
    ``(sector, loop_index)`` keys of every loop with a moved vertex.
    """
    owners = wall_owners(level)
    by_vertex: dict[tuple[int, int], list[int]] = {}
    for wall_id, wall in enumerate(level.walls):
        key = (int(wall.fields["x"]), int(wall.fields["y"]))
        by_vertex.setdefault(key, []).append(wall_id)

    drivers: list[dict[str, Any]] = []
    moved: dict[int, dict[str, Any]] = {}
    disagreements: list[dict[str, Any]] = []
    for wall_id, sign, why in drag_drivers(level, sector_id):
        vertex = (_wall_field(level, wall_id, "x"), _wall_field(level, wall_id, "y"))
        chain = drag_chain(level, wall_id)
        coincident = sorted(by_vertex.get(vertex, []))
        unchained = sorted(set(coincident) - set(chain))
        apart = [w for w in chain
                 if (_wall_field(level, w, "x"), _wall_field(level, w, "y")) != vertex]
        row = {
            "wall": wall_id, "sign": sign, "why": why,
            "vertex": [vertex[0], vertex[1]],
            "chain": chain,
            "chain_sectors": sorted({owners.get(w, -1) for w in chain}),
            "coincident": coincident,
            "coincident_sectors": sorted({owners.get(w, -1) for w in coincident}),
            "unchained_coincident": unchained,
            "chained_apart": apart,
        }
        drivers.append(row)
        for member in chain:
            moved[member] = {"driver": wall_id, "sign": sign}
        if unchained:
            disagreements.append({
                "kind": "coincident but not chained", "driver": wall_id,
                "vertex": [vertex[0], vertex[1]], "walls": unchained,
                "sectors": sorted({owners.get(w, -1) for w in unchained}),
                "why": f"wall(s) {unchained} sit on ({vertex[0]}, {vertex[1]}) "
                       f"but no nextwall pairing reaches them from wall "
                       f"{wall_id}, so the engine leaves them behind",
            })
        if apart:
            disagreements.append({
                "kind": "chained but not coincident", "driver": wall_id,
                "vertex": [vertex[0], vertex[1]], "walls": apart,
                "sectors": sorted({owners.get(w, -1) for w in apart}),
                "why": f"nextwall pairing reaches wall(s) {apart} from wall "
                       f"{wall_id} although they do not start at "
                       f"({vertex[0]}, {vertex[1]}); DragPoint snaps them there",
            })

    sectors = sorted({owners.get(w, -1) for w in moved})
    loops: list[tuple[int, int]] = []
    loop_walls: dict[tuple[int, int], list[int]] = {}
    for sector in sectors:
        if sector < 0:
            continue
        for index, walls in enumerate(sector_loops(level, sector)):
            if any(w in moved for w in walls):
                loops.append((sector, index))
                loop_walls[(sector, index)] = walls
    coincidence_sectors = sorted({s for row in drivers for s in row["coincident_sectors"]})
    return {
        "sector": sector_id,
        "type": int(level.sectors[sector_id].fields["type"]),
        "all_walls": int(level.sectors[sector_id].fields["type"]) in ALL_WALL_TYPES,
        "drivers": drivers,
        "moved": moved,
        "walls": sorted(moved),
        "sectors": sectors,
        "coincidence_sectors": coincidence_sectors,
        "loops": loops,
        "loop_walls": loop_walls,
        "disagreements": disagreements,
        "basis": "triggers.cpp:817-854 DragPoint walks nextwall both ways; "
                 ":897-910 a 16384 wall drags its point2 when that wall is "
                 "unflagged; :912-926 a 32768 wall does the same in reverse",
    }


@dataclass
class ClosureSweep:
    """One mechanism's travel, applied to every vertex `DragPoint` moves."""

    sector: int
    steps: int
    busy: list[float]
    closure: dict[str, Any]
    #: Per step, moved wall -> where its vertex is.
    positions: list[dict[int, Point]]
    #: Every loop with a moved vertex, keyed (sector, loop_index).
    loops: dict[tuple[int, int], list[Polygon]]
    loop_walls: dict[tuple[int, int], list[int]]
    drawn: dict[int, Point]

    def position(self, step: int, wall_id: int) -> Point:
        return self.positions[step].get(wall_id, self.drawn[wall_id])


def closure_sweep(level: Any, sector_id: int, *, steps: int = 16) -> ClosureSweep:
    """Step a mechanism through its travel and move everything it drags.

    Each driver's base is its drawn vertex run backwards a full travel --
    the `trInit` rebase -- and at every step each chained wall is set to its
    driver's position, exactly as `DragPoint` assigns absolute coordinates
    rather than offsets. `setBaseWallSect` (triggers.cpp:2144-2151) records
    the base for the MOVER's walls only, so a neighbour has no base of its
    own: it is wherever the vertex it shares was last put.
    """
    travel = blood_travel(level, sector_id)
    closure = drag_closure(level, sector_id)
    drawn: dict[int, Point] = {
        wall_id: (float(wall.fields["x"]), float(wall.fields["y"]))
        for wall_id, wall in enumerate(level.walls)
    }
    drivers = [(row["wall"], row["sign"], row["chain"]) for row in closure["drivers"]]
    base = {wall_id: travel.place(drawn[wall_id], sign, -1.0) for wall_id, sign, _ in drivers}
    busies = travel.busies(steps)
    positions: list[dict[int, Point]] = []
    for busy in busies:
        frame: dict[int, Point] = {}
        for wall_id, sign, chain in drivers:
            point = travel.place(base[wall_id], sign, busy)
            for member in chain:
                frame[member] = point
        positions.append(frame)
    loops = {
        key: [[positions[step].get(w, drawn[w]) for w in walls] for step in range(steps + 1)]
        for key, walls in closure["loop_walls"].items()
    }
    return ClosureSweep(sector=sector_id, steps=steps, busy=busies, closure=closure,
                        positions=positions, loops=loops,
                        loop_walls=dict(closure["loop_walls"]), drawn=drawn)


def _bbox(points: Iterable[Point]) -> tuple[float, float, float, float]:
    xs, ys = zip(*points)
    return (min(xs), min(ys), max(xs), max(ys))


def _boxes_touch(a: tuple[float, float, float, float],
                 b: tuple[float, float, float, float]) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def closure_crossings(level: Any, swept: ClosureSweep,
                      *, owners: dict[int, int] | None = None) -> list[dict[str, Any]]:
    """Moving walls that properly cross walls the motion does not move.

    A wall MOVES if either of its endpoints does (its own vertex or its
    `point2`'s). Everything else is static, at its drawn coordinates -- and
    that is now exact, where the mover-only gate had to guess the static set
    by whole sectors. Touching at an endpoint is a hinge and does not count.
    """
    owners = owners if owners is not None else wall_owners(level)
    moved = set(swept.closure["walls"])
    moving = sorted({w for w in moved} | {
        w for w in range(len(level.walls))
        if _wall_field(level, w, "point2") in moved
    })
    if not moving:
        return []
    swept_points = [swept.position(step, w) for w in moving for step in range(swept.steps + 1)]
    swept_points += [swept.position(step, _wall_field(level, w, "point2"))
                     for w in moving for step in range(swept.steps + 1)]
    window = _bbox(swept_points)
    moving_set = set(moving)
    static: list[tuple[int, Point, Point]] = []
    for wall_id in range(len(level.walls)):
        if wall_id in moving_set:
            continue
        end_id = _wall_field(level, wall_id, "point2")
        a, b = swept.drawn[wall_id], swept.drawn[end_id]
        if _boxes_touch(window, _bbox((a, b))):
            static.append((wall_id, a, b))
    #: Baseline: pairs that already cross in the DRAWN pose are the map's
    #: own hairline overlaps (E1M1 s55 has one at its door notch), not
    #: something the motion did. Only crossings the travel CREATES count.
    already: set[tuple[int, int]] = set()
    for wall_id in moving:
        a = swept.drawn[wall_id]
        b = swept.drawn[_wall_field(level, wall_id, "point2")]
        for other, c, d in static:
            if segments_cross(a, b, c, d):
                already.add((wall_id, other))
    found: list[dict[str, Any]] = []
    for step in range(swept.steps + 1):
        for wall_id in moving:
            a = swept.position(step, wall_id)
            b = swept.position(step, _wall_field(level, wall_id, "point2"))
            for other, c, d in static:
                if (wall_id, other) in already:
                    continue
                if segments_cross(a, b, c, d):
                    found.append({
                        "step": step, "wall": wall_id,
                        "sector": owners.get(wall_id, -1),
                        "static_wall": other,
                        "static_sector": owners.get(other, -1),
                    })
                    break
    return found


def closure_health(level: Any, sector_id: int, *, steps: int = 16) -> dict[str, Any]:
    """Geometric problems ANYTHING the motion drags develops over the travel.

    For every loop with a moved vertex -- the mover's own and every
    neighbour's -- the signed area at each step is compared with the DRAWN
    pose's winding (the pose the map was validated in), and the loop is
    checked for self-intersection; and every moving wall is checked against
    every static one for a proper crossing. ``problems`` is the list a gate
    should refuse on; ``disagreements`` are the closure's own map defects.
    """
    swept = closure_sweep(level, sector_id, steps=steps)
    owners = wall_owners(level)
    loops: list[dict[str, Any]] = []
    problems: list[str] = []
    notes: list[str] = []
    moved = swept.closure["moved"]
    #: A neighbour that is itself a horizontal mover is a CO-MOVER: the
    #: engine drags its shared vertices here and then its own
    #: `TranslateSector` re-places them from its own base, so where they end
    #: up depends on both mechanisms' busy. One mechanism at a time cannot
    #: judge it (E1M4's eight-sector wheel, E3M2's boat), so its loops are
    #: reported but never counted as problems.
    co_movers = sorted(
        s for s in swept.closure["sectors"]
        if s != sector_id
        and int(level.sectors[s].fields["type"]) in (614, 615, 616, 617)
        and level.sectors[s].extra is not None)
    for key, frames in swept.loops.items():
        sector, index = key
        walls = swept.loop_walls[key]
        drawn_poly = [swept.drawn[w] for w in walls]
        drawn_area = polygon_area(drawn_poly)
        #: Baseline against the DRAWN loop: an original may already cross
        #: itself by a hair (E1M1 s55's door notch does), and that is the
        #: map's property, not the motion's.
        drawn_folds = set(self_intersections(drawn_poly))
        signed = [polygon_area(frame) for frame in frames]
        inverted = [step for step, value in enumerate(signed)
                    if drawn_area and value and (value > 0) != (drawn_area > 0)]
        folds = [step for step, frame in enumerate(frames)
                 if set(self_intersections(frame)) - drawn_folds]
        dragged_through = sorted({moved[w]["driver"] for w in walls if w in moved})
        row = {
            "sector": sector, "loop": index, "own": sector == sector_id,
            "co_mover": sector in co_movers,
            "walls": len(walls),
            "moved_walls": sum(1 for w in walls if w in moved),
            "dragged_by_walls": dragged_through,
            "area_drawn": round(drawn_area, 1),
            "drawn_self_intersecting": bool(drawn_folds),
            "areas": [round(value, 1) for value in signed],
            "inverted_steps": inverted,
            "self_intersecting_steps": folds,
        }
        loops.append(row)
        where = (f"loop {index} of sector {sector}"
                 + ("" if sector == sector_id
                    else f", which this mechanism drags through wall(s) {dragged_through}"))
        if sector in co_movers:
            if inverted or folds:
                notes.append(
                    f"{where} is itself a mover (type "
                    f"{int(level.sectors[sector].fields['type'])}); swept alone it "
                    f"would invert at {inverted[:3]} / fold at {folds[:3]}, but "
                    f"its own travel re-places those vertices -- not judged")
            continue
        if inverted:
            problems.append(
                f"step {inverted[0]}/{steps}: {where} inverts -- its outline "
                f"winds the other way, so it is inside out at that pose")
        if folds:
            fresh = set(self_intersections(frames[folds[0]])) - drawn_folds
            problems.append(
                f"step {folds[0]}/{steps}: {where} crosses itself "
                f"({len(fresh)} new wall pair(s))")
    crossings = [hit for hit in closure_crossings(level, swept, owners=owners)
                 if hit["static_sector"] not in co_movers]
    for hit in crossings[:8]:
        problems.append(
            f"step {hit['step']}/{steps}: wall {hit['wall']} of sector "
            f"{hit['sector']} cuts through wall {hit['static_wall']} of sector "
            f"{hit['static_sector']}, which this mechanism does not move -- it "
            f"sweeps through standing geometry")
    return {
        "sector": sector_id,
        "type": swept.closure["type"],
        "steps": steps,
        "moved_walls": len(swept.closure["walls"]),
        "sectors": swept.closure["sectors"],
        "coincidence_sectors": swept.closure["coincidence_sectors"],
        "neighbours": [s for s in swept.closure["sectors"] if s != sector_id],
        "co_movers": co_movers,
        "isolated": swept.closure["sectors"] == [sector_id],
        "loops": loops,
        "crossings": crossings,
        "disagreements": swept.closure["disagreements"],
        "problems": problems,
        "notes": notes,
        "healthy": not problems,
    }
