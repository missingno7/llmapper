"""Bounded 2D geometric sightlines over Build walls.

Portal adjacency is not line of sight. This sensor casts XY rays against
occluding wall segments and reports whether a query pair is blocked.

It is intentionally limited:

- 2D only; floor/ceiling height, slopes, and eye height are not tested
- sprites, voxels, and masked mid-textures are not occluders
- lighting, fog, and sky are ignored
- masked walls (cstat bit 4 / 16) are treated as see-through even if they block
  movement, because that is how Blood windows and fences typically render

The result is a derived probe, not a renderer.
"""

from __future__ import annotations

from math import cos, hypot, pi, sin
from typing import Any, Iterable

from .build_ir import BuildIR
from .design import _ref


SCHEMA = "llmapper.sightline"
SCHEMA_VERSION = 1

CSTAT_WALL_BLOCK = 1
CSTAT_WALL_MASKED = 16
CSTAT_WALL_BLOCK_HITSCAN = 64
_EPS = 1.0


class SightError(ValueError):
    pass


def _orientation(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> int:
    value = (by - ay) * (cx - bx) - (bx - ax) * (cy - by)
    if abs(value) < 1e-9:
        return 0
    return 1 if value > 0 else 2


def _on_segment(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
    return (
        min(ax, bx) - _EPS <= cx <= max(ax, bx) + _EPS
        and min(ay, by) - _EPS <= cy <= max(ay, by) + _EPS
    )


def _segments_intersect(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float],
) -> bool:
    o1 = _orientation(*a, *b, *c)
    o2 = _orientation(*a, *b, *d)
    o3 = _orientation(*c, *d, *a)
    o4 = _orientation(*c, *d, *b)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(*a, *b, *c):
        return True
    if o2 == 0 and _on_segment(*a, *b, *d):
        return True
    if o3 == 0 and _on_segment(*c, *d, *a):
        return True
    if o4 == 0 and _on_segment(*c, *d, *b):
        return True
    return False


def _intersection_point(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float],
) -> tuple[float, float] | None:
    x1, y1 = a
    x2, y2 = b
    x3, y3 = c
    x4, y4 = d
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-12:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
    return px, py


def _point_near_segment(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> bool:
    ax, ay = a
    bx, by = b
    length = hypot(bx - ax, by - ay)
    if length < _EPS:
        return hypot(px - ax, py - ay) < _EPS
    t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / (length * length)
    if t < 0.0 or t > 1.0:
        return False
    qx = ax + t * (bx - ax)
    qy = ay + t * (by - ay)
    return hypot(px - qx, py - qy) < _EPS


def wall_occludes_sight(fields: dict[str, int]) -> bool:
    """Return whether this wall should block a 2D sight ray.

    Masked mid-textures are see-through. One-sided walls always occlude.
    Two-sided walls occlude only when they block movement or hitscan and are
    not masked.
    """
    cstat = int(fields["cstat"])
    if cstat & CSTAT_WALL_MASKED:
        return False
    if int(fields["next_sector"]) < 0:
        return True
    return bool(cstat & (CSTAT_WALL_BLOCK | CSTAT_WALL_BLOCK_HITSCAN))


def occluding_segments(build: BuildIR) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for wall_id, wall in enumerate(build.walls):
        fields = wall["fields"]
        if not wall_occludes_sight(fields):
            continue
        point2 = int(fields["point2"])
        if not 0 <= point2 < len(build.walls):
            continue
        end = build.walls[point2]["fields"]
        start = (float(fields["x"]), float(fields["y"]))
        finish = (float(end["x"]), float(end["y"]))
        if hypot(finish[0] - start[0], finish[1] - start[1]) < _EPS:
            continue
        segments.append({
            "wall": _ref("wall", wall_id),
            "wall_id": wall_id,
            "start": start,
            "end": finish,
            "one_sided": int(fields["next_sector"]) < 0,
        })
    return segments


def _first_hit(
    origin: tuple[float, float],
    target: tuple[float, float],
    segments: list[dict[str, Any]],
) -> dict[str, Any] | None:
    span = hypot(target[0] - origin[0], target[1] - origin[1])
    if span < _EPS:
        return None
    best: dict[str, Any] | None = None
    best_distance = span
    for segment in segments:
        a = segment["start"]
        b = segment["end"]
        if _point_near_segment(*origin, a, b) or _point_near_segment(*target, a, b):
            continue
        if not _segments_intersect(origin, target, a, b):
            continue
        hit = _intersection_point(origin, target, a, b)
        if hit is None:
            continue
        distance = hypot(hit[0] - origin[0], hit[1] - origin[1])
        if distance < _EPS or distance >= best_distance - 1e-6:
            continue
        best_distance = distance
        best = {
            "wall": segment["wall"],
            "wall_id": segment["wall_id"],
            "distance": round(distance, 3),
            "point": {"x": round(hit[0], 3), "y": round(hit[1], 3)},
        }
    return best


def line_of_sight(
    build: BuildIR,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    segments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Report whether an XY ray from (x1,y1) to (x2,y2) is blocked by walls."""
    origin = (float(x1), float(y1))
    target = (float(x2), float(y2))
    walls = segments if segments is not None else occluding_segments(build)
    hit = _first_hit(origin, target, walls)
    distance = hypot(target[0] - origin[0], target[1] - origin[1])
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "model": "2d-xy-ray-vs-occluding-walls",
        "basis": (
            "one-sided walls and unmasked blocking/hitscan walls occlude; "
            "masked walls and open portals do not; height/slopes/sprites ignored"
        ),
        "from": {"x": origin[0], "y": origin[1]},
        "to": {"x": target[0], "y": target[1]},
        "distance": round(distance, 3),
        "clear": hit is None,
        "occluder": hit,
        "kind": "derived",
        "confidence": "high" if hit is None or hit["wall_id"] is not None else "medium",
    }


def depth_samples(
    build: BuildIR,
    x: float,
    y: float,
    *,
    rays: int = 32,
    max_distance: float | None = None,
    segments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Cast equally spaced XY rays and report nearest occluder distances."""
    if rays < 4:
        raise SightError("depth sampling requires at least 4 rays")
    walls = segments if segments is not None else occluding_segments(build)
    if max_distance is None:
        xs = [int(wall["fields"]["x"]) for wall in build.walls]
        ys = [int(wall["fields"]["y"]) for wall in build.walls]
        max_distance = hypot(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    origin = (float(x), float(y))
    samples = []
    for index in range(rays):
        angle = (2.0 * pi * index) / rays
        target = (origin[0] + max_distance * cos(angle), origin[1] + max_distance * sin(angle))
        hit = _first_hit(origin, target, walls)
        samples.append({
            "index": index,
            "angle_radians": round(angle, 4),
            "clear_to_max": hit is None,
            "distance": None if hit is None else hit["distance"],
            "occluder": None if hit is None else hit["wall"],
        })
    finite = [item["distance"] for item in samples if item["distance"] is not None]
    finite.sort()
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "model": "2d-xy-depth-rose",
        "origin": {"x": origin[0], "y": origin[1]},
        "rays": rays,
        "max_distance": round(float(max_distance), 3),
        "open_ray_count": sum(1 for item in samples if item["clear_to_max"] or (item["distance"] or 0) > max_distance * 0.5),
        "median_occluder_distance": None if not finite else finite[len(finite) // 2],
        "min_occluder_distance": None if not finite else finite[0],
        "max_occluder_distance": None if not finite else finite[-1],
        "samples": samples,
        "kind": "derived",
    }


def sight_to_targets(
    build: BuildIR,
    origin: tuple[float, float],
    targets: Iterable[dict[str, Any]],
    *,
    segments: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    walls = segments if segments is not None else occluding_segments(build)
    results = []
    for target in targets:
        probe = line_of_sight(
            build, origin[0], origin[1], float(target["x"]), float(target["y"]), segments=walls,
        )
        results.append({
            "target": target.get("id"),
            "clear": probe["clear"],
            "distance": probe["distance"],
            "occluder": probe["occluder"],
        })
    return results


def sprite_targets(build: BuildIR, *, lotags: set[int] | None = None) -> list[dict[str, Any]]:
    targets = []
    wanted = lotags
    for sprite_id, sprite in enumerate(build.sprites):
        fields = sprite["fields"]
        lotag = int(fields["lotag"])
        if wanted is not None and lotag not in wanted:
            continue
        targets.append({
            "id": _ref("sprite", sprite_id),
            "sprite_id": sprite_id,
            "lotag": lotag,
            "sector": int(fields["sector"]),
            "x": float(fields["x"]),
            "y": float(fields["y"]),
        })
    return targets


def spawn_sight_report(build: BuildIR, *, include_sp_start: bool = True) -> dict[str, Any]:
    """Pairwise 2D sight among player-start sprites, plus a depth rose per start."""
    lotags = {1, 2} if include_sp_start else {2}
    starts = sprite_targets(build, lotags=lotags)
    if not starts:
        header = build.player_start
        starts = [{
            "id": "player_start_header",
            "sprite_id": None,
            "lotag": None,
            "sector": int(header["sector"]),
            "x": float(header["x"]),
            "y": float(header["y"]),
        }]
    walls = occluding_segments(build)
    pairs = []
    for index, left in enumerate(starts):
        for right in starts[index + 1:]:
            probe = line_of_sight(build, left["x"], left["y"], right["x"], right["y"], segments=walls)
            pairs.append({
                "a": left["id"],
                "b": right["id"],
                "clear": probe["clear"],
                "distance": probe["distance"],
                "occluder": probe["occluder"],
            })
    roses = []
    for start in starts:
        rose = depth_samples(build, start["x"], start["y"], segments=walls)
        roses.append({
            "origin": start["id"],
            "open_ray_count": rose["open_ray_count"],
            "median_occluder_distance": rose["median_occluder_distance"],
            "min_occluder_distance": rose["min_occluder_distance"],
            "max_occluder_distance": rose["max_occluder_distance"],
        })
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "model": "spawn-pairwise-2d-sight",
        "starts": starts,
        "pairs": pairs,
        "depth_summaries": roses,
        "occluding_wall_count": len(walls),
        "kind": "derived",
        "limitations": [
            "2D XY only",
            "ignores height, slopes, sprites, lighting",
            "masked walls are treated as see-through",
        ],
    }
