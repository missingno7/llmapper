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
from typing import Any, Iterable, Sequence

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


def blood_sweep(level: Any, sector_id: int, *, steps: int = 16) -> list[Polygon]:
    """Wall positions across a Blood moving sector's whole travel.

    Transcribes ``TranslateSector`` for the four moving types, including the
    ``bAllWalls`` split: 616/617 move every wall, 614/615 move only walls
    flagged ``cstat & 16384`` (forward) or ``& 32768`` (reverse).
    """
    sector = level.sectors[sector_id]
    kind = int(sector.fields["type"])
    if kind not in (614, 615, 616, 617):
        raise ValueError(f"sector {sector_id} has type {kind}, which does not move horizontally")
    if sector.extra is None:
        raise ValueError(f"sector {sector_id} has no XSECTOR")
    extra = sector.extra.fields
    walls = blood_sector_walls(level, sector_id)
    start = int(sector.fields["wall_ptr"])
    all_walls = kind in (616, 617)

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

    #: A flagged wall drags its OWN vertex and its `point2`'s -- unless that
    #: next wall is itself flagged, in which case it moves under its own
    #: sign. `triggers.cpp:902` and `:917`:
    #:
    #:     if (wall[nWall].cstat&16384) {
    #:         DragPoint(nWall, ...);
    #:         if ((wall[v10].cstat&49152) == 0) DragPoint(v10, ...);
    #:
    #: That propagation is how flagging ONE wall translates a whole EDGE,
    #: and without it the model shears every Marked slide instead of sliding
    #: it: the oracle's lid came back as a trapezoid of 2228224 units where
    #: the engine gives a 2048x128 strip. Every conclusion drawn from a swept
    #: area before this was measuring the wrong shape.
    CARRY = 16384 | 32768

    def _signs() -> list[float]:
        out: list[float | None] = [None] * len(walls)
        for index in range(len(walls)):
            cstat = int(level.walls[start + index].fields["cstat"])
            if all_walls:
                out[index] = 1.0
                continue
            if cstat & 16384:
                out[index] = 1.0
            elif cstat & 32768:
                out[index] = -1.0
        if not all_walls:
            for index in range(len(walls)):
                cstat = int(level.walls[start + index].fields["cstat"])
                if not cstat & CARRY:
                    continue
                sign = 1.0 if cstat & 16384 else -1.0
                nxt = int(level.walls[start + index].fields["point2"]) - start
                if not 0 <= nxt < len(walls):
                    continue
                if int(level.walls[start + nxt].fields["cstat"]) & CARRY:
                    continue
                out[nxt] = sign
        return [0.0 if value is None else value for value in out]

    signs = _signs()

    def place(source: Polygon, busy: float) -> Polygon:
        vc = a6 + (a9 - a6) * busy
        v8 = a7 + (a10 - a7) * busy
        vbp = a8 + (a11 - a8) * busy
        frame: Polygon = []
        for index, point in enumerate(source):
            sign = signs[index]
            if not sign:
                frame.append(point)
                continue
            moved = point
            if vbp:
                moved = rotate_about(point, round(sign * vbp), (a4, a5))
            frame.append((moved[0] + sign * (vc - a4), moved[1] + sign * (v8 - a5)))
        return frame

    # trInit does not treat the authored geometry as the resting pose. It runs
    # TranslateSector once at busy = -65536 -- a full travel *backwards* --
    # calls setBaseWallSect to make that the reference, and only then moves to
    # the sector's real busy. So the coordinates in the MAP are the pose at
    # busy = 1, and a sector left at state 0 displaces itself by the whole
    # marker separation the moment the level loads.
    base = place(walls, -1.0)
    rest = 1.0 if int(extra.get("state", 0)) else 0.0
    target = 1.0 - rest
    return [place(base, rest + (target - rest) * (i / steps)) for i in range(steps + 1)]


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


def sweep_health(frames: Sequence[Polygon], *, static: Iterable[Polygon] = ()) -> dict[str, Any]:
    """Geometric problems a moving sector develops over its travel.

    ``static`` is the set of outlines the mover must not run through -- in
    practice the sectors around it that do not move with it.
    """
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
