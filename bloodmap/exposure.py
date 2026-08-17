"""Spawn-neighborhood and route exposure over 2D sight plus traversal.

Pairwise spawn sight does not distinguish a hunting-ground alcove from a
closet. These probes measure local footprint, hops into the largest sky
region, and sight along deterministic circulation samples.
"""

from __future__ import annotations

from collections import defaultdict, deque
from math import hypot
from typing import Any

from .build_ir import BuildIR
from .design import _polygon_loops, _ref, _signed_area
from .player_space import PLAYER_PROFILES
from .sight import depth_samples, occluding_segments, sprite_targets
from .spatial import analyze_spatial


SCHEMA = "llmapper.exposure"
SCHEMA_VERSION = 1
LOCAL_RADIUS_WIDTHS = 16.0
MAJOR_SKY_AREA_FRACTION = 0.25
ROUTE_SAMPLE_WIDTHS = 4.0


class ExposureError(ValueError):
    pass


def _id(ref: str) -> int:
    return int(ref.split(":", 1)[1])


def _sky(build: BuildIR, sector_id: int) -> bool:
    return bool(int(build.sectors[sector_id]["fields"]["ceiling_stat"]) & 1)


def _area(build: BuildIR, sector_id: int) -> float:
    return abs(sum(_signed_area(loop) for loop in _polygon_loops(build, sector_id)))


def _centroid(build: BuildIR, sector_id: int) -> tuple[float, float]:
    points = [point for loop in _polygon_loops(build, sector_id) for point in loop]
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def _point_in_loop(x: float, y: float, points: list[tuple[int, int]]) -> bool:
    inside = False
    n = len(points)
    for index in range(n):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % n]
        if (y1 > y) != (y2 > y):
            at_x = (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1
            if x < at_x:
                inside = not inside
    return inside


def _sectors_containing(build: BuildIR, x: float, y: float) -> list[int]:
    hits = []
    for sector_id in range(len(build.sectors)):
        loops = _polygon_loops(build, sector_id)
        outer = max(loops, key=lambda loop: abs(_signed_area(loop)))
        if not _point_in_loop(x, y, outer):
            continue
        hole = False
        for loop in loops:
            if loop is outer:
                continue
            if _point_in_loop(x, y, loop):
                hole = True
                break
        if not hole:
            hits.append(sector_id)
    return hits


def _traversal(build: BuildIR) -> dict[int, set[int]]:
    views = analyze_spatial(build)["views"]
    graph: dict[int, set[int]] = defaultdict(set)
    for edge in views["traversability"]["walkable_at_rest"]:
        left, right = _id(edge["sectors"][0]), _id(edge["sectors"][1])
        graph[left].add(right)
        graph[right].add(left)
    for edge in views["traversability"]["known_non_portal_transitions"]:
        left, right = _id(edge["sectors"][0]), _id(edge["sectors"][1])
        graph[left].add(right)
        graph[right].add(left)
    return graph


def _hops(graph: dict[int, set[int]], start: int, goals: set[int]) -> int | None:
    if start in goals:
        return 0
    pending = deque([(start, 0)])
    seen = {start}
    while pending:
        current, dist = pending.popleft()
        for neighbor in graph.get(current, ()):
            if neighbor in seen:
                continue
            if neighbor in goals:
                return dist + 1
            seen.add(neighbor)
            pending.append((neighbor, dist + 1))
    return None


def _path(graph: dict[int, set[int]], start: int, goal: int) -> list[int] | None:
    if start == goal:
        return [start]
    pending = deque([start])
    parent: dict[int, int | None] = {start: None}
    while pending:
        current = pending.popleft()
        for neighbor in sorted(graph.get(current, ())):
            if neighbor in parent:
                continue
            parent[neighbor] = current
            if neighbor == goal:
                result = [goal]
                while parent[result[-1]] is not None:
                    result.append(parent[result[-1]])  # type: ignore[arg-type]
                return list(reversed(result))
            pending.append(neighbor)
    return None


def _largest_sky_region(build: BuildIR, graph: dict[int, set[int]]) -> set[int]:
    sky = {index for index in range(len(build.sectors)) if _sky(build, index)}
    if not sky:
        return set()
    unseen = set(sky)
    best: set[int] = set()
    best_area = -1.0
    while unseen:
        root = min(unseen)
        pending = [root]
        component = {root}
        unseen.remove(root)
        while pending:
            current = pending.pop()
            for neighbor in unseen.intersection(graph.get(current, ())):
                unseen.remove(neighbor)
                component.add(neighbor)
                pending.append(neighbor)
        area = sum(_area(build, sector_id) for sector_id in component)
        if area > best_area:
            best, best_area = component, area
    return best


def _local_area(build: BuildIR, graph: dict[int, set[int]], start: int, origin: tuple[float, float], radius: float) -> float:
    pending = deque([start])
    seen = {start}
    total = 0.0
    while pending:
        current = pending.popleft()
        cx, cy = _centroid(build, current)
        if hypot(cx - origin[0], cy - origin[1]) > radius and current != start:
            continue
        total += _area(build, current)
        for neighbor in graph.get(current, ()):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return total


def _ray_reaches_region(
    build: BuildIR,
    origin: tuple[float, float],
    angle_index: int,
    rays: int,
    max_distance: float,
    region: set[int],
    hit_distance: float | None,
) -> bool:
    from math import cos, pi, sin
    span = max_distance if hit_distance is None else min(max_distance, hit_distance)
    if span < 32:
        return bool(_sectors_containing(build, origin[0], origin[1]) and set(_sectors_containing(build, origin[0], origin[1])) & region)
    angle = (2.0 * pi * angle_index) / rays
    steps = max(4, int(span / (PLAYER_PROFILES["blood"].body_width)))
    for step in range(1, steps + 1):
        t = (step / steps) * span
        x = origin[0] + t * cos(angle)
        y = origin[1] + t * sin(angle)
        if set(_sectors_containing(build, x, y)) & region:
            return True
    return False


def spawn_neighborhood_report(build: BuildIR, *, include_sp_start: bool = False) -> dict[str, Any]:
    """Local footprint and field access for each player-start sprite."""
    profile = PLAYER_PROFILES.get(build.source_game) or PLAYER_PROFILES["blood"]
    lotags = {1, 2} if include_sp_start else {2}
    starts = sprite_targets(build, lotags=lotags)
    if not starts:
        raise ExposureError("no player-start sprites found")
    graph = _traversal(build)
    sky_region = _largest_sky_region(build, graph)
    sky_area = sum(_area(build, sector_id) for sector_id in sky_region) or 1.0
    walls = occluding_segments(build)
    radius = LOCAL_RADIUS_WIDTHS * profile.body_width
    neighborhoods = []
    for start in starts:
        sector = int(start["sector"])
        origin = (float(start["x"]), float(start["y"]))
        rose = depth_samples(build, origin[0], origin[1], segments=walls)
        hops = _hops(graph, sector, sky_region) if sky_region else None
        reaches = 0
        for sample in rose["samples"]:
            if _ray_reaches_region(
                build, origin, sample["index"], rose["rays"], rose["max_distance"],
                sky_region, sample["distance"],
            ):
                reaches += 1
        local = _local_area(build, graph, sector, origin, radius)
        neighborhoods.append({
            "origin": start["id"],
            "sprite_id": start["sprite_id"],
            "sector": _ref("sector", sector),
            "sky_ceiling": _sky(build, sector),
            "spawn_sector_area_player_areas": round(_area(build, sector) / (profile.body_width ** 2), 4),
            "local_reachable_area_player_areas": round(local / (profile.body_width ** 2), 4),
            "immediate_portal_choices": len(graph.get(sector, ())),
            "hops_to_largest_sky_region": hops,
            "max_2d_sight_player_widths": None if rose["max_occluder_distance"] is None else round(
                rose["max_occluder_distance"] / profile.body_width, 4
            ),
            "median_2d_sight_player_widths": None if rose["median_occluder_distance"] is None else round(
                rose["median_occluder_distance"] / profile.body_width, 4
            ),
            "rays_reaching_largest_sky_region": reaches,
            "ray_count": rose["rays"],
            "sky_region_ray_fraction": round(reaches / max(1, rose["rays"]), 4),
        })
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "model": "spawn-neighborhood: local traversal footprint plus 2D sight into the largest sky component",
        "player_body_width": profile.body_width,
        "local_radius_player_widths": LOCAL_RADIUS_WIDTHS,
        "largest_sky_region_sectors": len(sky_region),
        "largest_sky_region_player_areas": round(sky_area / (profile.body_width ** 2), 4),
        "neighborhoods": neighborhoods,
        "limitations": [
            "2D sight; height and sprites ignored",
            "local area uses sector centroids versus Euclidean radius",
            "labels such as closet/field are not assigned",
        ],
    }


def route_exposure_report(build: BuildIR, *, include_sp_start: bool = False) -> dict[str, Any]:
    """Sight and sky/cover samples along shortest paths from starts to the main sky region."""
    profile = PLAYER_PROFILES.get(build.source_game) or PLAYER_PROFILES["blood"]
    lotags = {1, 2} if include_sp_start else {2}
    starts = sprite_targets(build, lotags=lotags)
    if not starts:
        raise ExposureError("no player-start sprites found")
    graph = _traversal(build)
    sky_region = _largest_sky_region(build, graph)
    if not sky_region:
        return {
            "$schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "kind": "derived",
            "model": "shortest at-rest path from each start to the largest sky sector; 2D sight at sector samples",
            "target_sector": None,
            "routes": [],
            "limitations": [
                "not a player simulation",
                "this map has no sky-parallax sector, so there is no field target",
            ],
        }
    target = max(sky_region, key=lambda sector_id: _area(build, sector_id))
    walls = occluding_segments(build)
    step = ROUTE_SAMPLE_WIDTHS * profile.body_width
    routes = []
    for start in starts:
        path = _path(graph, int(start["sector"]), target)
        if not path:
            routes.append({"origin": start["id"], "reachable": False, "samples": []})
            continue
        samples = []
        sky_samples = 0
        transitions = 0
        prev_sky = None
        for index, sector_id in enumerate(path):
            cx, cy = _centroid(build, sector_id)
            if index == 0:
                cx, cy = float(start["x"]), float(start["y"])
            rose = depth_samples(build, cx, cy, rays=16, segments=walls)
            is_sky = _sky(build, sector_id)
            if prev_sky is not None and is_sky != prev_sky:
                transitions += 1
            prev_sky = is_sky
            if is_sky:
                sky_samples += 1
            samples.append({
                "sector": _ref("sector", sector_id),
                "sky_ceiling": is_sky,
                "max_2d_sight_player_widths": None if rose["max_occluder_distance"] is None else round(
                    rose["max_occluder_distance"] / profile.body_width, 4
                ),
                "median_2d_sight_player_widths": None if rose["median_occluder_distance"] is None else round(
                    rose["median_occluder_distance"] / profile.body_width, 4
                ),
                "immediate_portal_choices": len(graph.get(sector_id, ())),
            })
        max_sights = [item["max_2d_sight_player_widths"] for item in samples if item["max_2d_sight_player_widths"] is not None]
        routes.append({
            "origin": start["id"],
            "reachable": True,
            "hops": len(path) - 1,
            "sky_sample_fraction": round(sky_samples / max(1, len(samples)), 4),
            "cover_sky_transitions": transitions,
            "mean_max_sight_player_widths": None if not max_sights else round(sum(max_sights) / len(max_sights), 4),
            "min_max_sight_player_widths": None if not max_sights else round(min(max_sights), 4),
            "samples": samples,
        })
        _ = step  # reserved for denser interpolation
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "model": "shortest at-rest path from each start to the largest sky sector; 2D sight at sector samples",
        "target_sector": _ref("sector", target),
        "routes": routes,
        "limitations": [
            "not a player simulation",
            "samples are sector centroids except the spawn origin",
            "closed movers are not opened",
        ],
    }
