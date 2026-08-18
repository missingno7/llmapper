"""Top-down SVG diagnostics for Build/Blood sectors.

This is deliberately a view over :class:`~bloodmap.model.DiskMap`, not another
MAP reader or a second geometry representation.  The disk map remains the
authority for sector/wall indices and coordinates.
"""

from __future__ import annotations

import html
import json
from math import hypot
from pathlib import Path
from typing import Iterable

from .model import DiskMap
from .planar_geom import area2, point_in_loops


Point = tuple[int, int]


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def _loops_for_sector(disk: DiskMap, sector_index: int) -> list[list[Point]]:
    """Follow the sector's authoritative point2 links into closed wall loops."""
    sector = disk.sectors[sector_index]
    first = max(0, sector.wall_ptr)
    last = min(len(disk.walls), first + max(0, sector.wall_count))
    owned = set(range(first, last))
    loops: list[list[Point]] = []
    while owned:
        start = min(owned)
        current = start
        points: list[Point] = []
        local: set[int] = set()
        while current in owned and current not in local:
            local.add(current)
            owned.discard(current)
            wall = disk.walls[current]
            points.append((wall.x, wall.y))
            if wall.point2 == start:
                break
            current = wall.point2
        if len(points) >= 2:
            loops.append(points)
    return loops


def _polygon_centroid(points: list[Point]) -> tuple[float, float] | None:
    twice = area2(points)
    if not twice:
        return None
    x = sum((points[i][0] + points[(i + 1) % len(points)][0]) *
            (points[i][0] * points[(i + 1) % len(points)][1] -
             points[(i + 1) % len(points)][0] * points[i][1])
            for i in range(len(points)))
    y = sum((points[i][1] + points[(i + 1) % len(points)][1]) *
            (points[i][0] * points[(i + 1) % len(points)][1] -
             points[(i + 1) % len(points)][0] * points[i][1])
            for i in range(len(points)))
    return x / (3 * twice), y / (3 * twice)


def _distance_to_boundary(point: tuple[float, float], loops: list[list[Point]]) -> float:
    px, py = point
    best = float("inf")
    for loop in loops:
        for index, (ax, ay) in enumerate(loop):
            bx, by = loop[(index + 1) % len(loop)]
            dx, dy = bx - ax, by - ay
            length_sq = dx * dx + dy * dy
            if length_sq:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
                qx, qy = ax + t * dx, ay + t * dy
            else:
                qx, qy = ax, ay
            best = min(best, hypot(px - qx, py - qy))
    return best


def _representative_point(loops: list[list[Point]]) -> tuple[float, float] | None:
    """Choose an interior point, favoring clearance from concave boundaries."""
    if not loops:
        return None
    points = [point for loop in loops for point in loop]
    min_x, max_x = min(x for x, _ in points), max(x for x, _ in points)
    min_y, max_y = min(y for _, y in points), max(y for _, y in points)
    candidates: list[tuple[float, float]] = []
    largest = max(loops, key=lambda loop: abs(area2(loop)))
    centroid = _polygon_centroid(largest)
    if centroid is not None:
        candidates.append(centroid)
    candidates.extend([
        (sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points)),
        ((min_x + max_x) / 2, (min_y + max_y) / 2),
    ])

    # A small deterministic clearance search handles concave sectors and holes.
    # It is a label-placement heuristic only; it never changes map geometry.
    for row in range(1, 18):
        y = min_y + (max_y - min_y) * row / 18
        for column in range(1, 18):
            x = min_x + (max_x - min_x) * column / 18
            candidates.append((x, y))
    inside = [candidate for candidate in candidates if point_in_loops(
        (round(candidate[0]), round(candidate[1])), loops) == 1
    ]
    if inside:
        return max(inside, key=lambda candidate: _distance_to_boundary(candidate, loops))
    # Degenerate/very thin sectors still receive a label rather than silently
    # disappearing from the debugging view.
    return centroid or candidates[0]


def _path_for_loops(loops: list[list[Point]], xy) -> str:
    commands: list[str] = []
    for loop in loops:
        if not loop:
            continue
        points = [xy(x, y) for x, y in loop]
        commands.append("M " + " L ".join(f"{_fmt(x)} {_fmt(y)}" for x, y in points) + " Z")
    return " ".join(commands)


def _trajectory_points(path: str | Path | None) -> list[tuple[int, int]]:
    if not path:
        return []
    points: list[tuple[int, int]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
            if "x" in value and "y" in value:
                points.append((int(value["x"]), int(value["y"])))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return points


def render_sector_map(
    disk: DiskMap,
    *,
    highlight_sectors: Iterable[int] = (),
    highlight_walls: Iterable[int] = (),
    trajectory: str | Path | None = None,
    width: int = 2400,
    height: int = 1800,
) -> str:
    """Render all Build geometry and real sector IDs as a zoomable SVG."""
    wall_points = [(wall.x, wall.y) for wall in disk.walls]
    if not wall_points:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"/>'
    selected_sectors = {int(value) for value in highlight_sectors}
    selected_walls = {int(value) for value in highlight_walls}
    min_x = min(x for x, _ in wall_points)
    max_x = max(x for x, _ in wall_points)
    min_y = min(y for _, y in wall_points)
    max_y = max(y for _, y in wall_points)
    margin = 70
    scale = min(
        (width - 2 * margin) / max(1, max_x - min_x),
        (height - 2 * margin) / max(1, max_y - min_y),
    )

    def xy(x: float, y: float) -> tuple[float, float]:
        # Match bloodmap.analysis.render_svg: Build +Y is displayed upward.
        return margin + (x - min_x) * scale, height - margin - (y - min_y) * scale

    sector_loops = [_loops_for_sector(disk, index) for index in range(len(disk.sectors))]
    labels = [_representative_point(loops) for loops in sector_loops]
    path_data = [_path_for_loops(loops, xy) for loops in sector_loops]
    trajectory_points = _trajectory_points(trajectory)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<title>Build/Blood sector map</title>',
        '<desc>Authoritative MAP XY geometry with actual sector and highlighted wall indices.</desc>',
        '<rect width="100%" height="100%" fill="#111318"/>',
        '<g id="sectors" fill-rule="evenodd" stroke-linejoin="round">',
    ]
    palette = ("#244b5c", "#3b4e37", "#4f3d58", "#55452d")
    for index, path_data_item in enumerate(path_data):
        if not path_data_item:
            continue
        highlighted = index in selected_sectors
        fill = "#d98935" if highlighted else palette[index % len(palette)]
        opacity = "0.62" if highlighted else "0.28"
        parts.append(
            f'<path data-sector="{index}" d="{path_data_item}" fill="{fill}" '
            f'fill-opacity="{opacity}" stroke="none"/>'
        )
    parts.append('</g><g id="walls" fill="none" stroke-linecap="round">')
    for wall_index, wall in enumerate(disk.walls):
        if not 0 <= wall.point2 < len(disk.walls):
            continue
        end = disk.walls[wall.point2]
        x1, y1 = xy(wall.x, wall.y)
        x2, y2 = xy(end.x, end.y)
        highlighted = wall_index in selected_walls
        color = "#ff4f70" if highlighted else ("#58b7dd" if wall.next_sector >= 0 else "#aeb7c4")
        stroke = 5.5 if highlighted else (1.8 if wall.next_sector >= 0 else 1.1)
        parts.append(
            f'<line data-wall="{wall_index}" x1="{_fmt(x1)}" y1="{_fmt(y1)}" '
            f'x2="{_fmt(x2)}" y2="{_fmt(y2)}" stroke="{color}" stroke-width="{stroke}"/>'
        )
        if highlighted:
            parts.append(
                f'<text x="{_fmt((x1 + x2) / 2)}" y="{_fmt((y1 + y2) / 2 - 8)}" '
                'fill="#ff8098" font-family="monospace" font-size="22" '
                'text-anchor="middle" paint-order="stroke" stroke="#111318" stroke-width="5">'
                f'W{wall_index}</text>'
            )
    parts.append('</g>')
    if trajectory_points:
        projected = [xy(x, y) for x, y in trajectory_points]
        point_text = " ".join(
            ("M" if index == 0 else "L") + f" {_fmt(x)} {_fmt(y)}"
            for index, (x, y) in enumerate(projected)
        )
        parts.extend([
            '<g id="trajectory">',
            f'<path d="{point_text}" fill="none" stroke="#ffe66d" stroke-width="4" '
            'stroke-opacity="0.9" stroke-linecap="round" stroke-linejoin="round"/>',
            f'<circle cx="{_fmt(projected[0][0])}" cy="{_fmt(projected[0][1])}" r="7" fill="#fff3a3"/>',
            f'<circle cx="{_fmt(projected[-1][0])}" cy="{_fmt(projected[-1][1])}" r="9" fill="#ff6b6b"/>',
            '</g>',
        ])
    parts.append('<g id="sector-label-leaders" fill="none" stroke="#f1f4f7" stroke-width="1.5" stroke-dasharray="4 3">')
    for index, point in enumerate(labels):
        if point is None:
            continue
        loops = sector_loops[index]
        inside = point_in_loops((round(point[0]), round(point[1])), loops) == 1
        if not inside:
            x, y = xy(*point)
            parts.append(f'<path d="M {_fmt(x)} {_fmt(y)} L {_fmt(x)} {_fmt(y - 22)}"/>')
    parts.append('</g><g id="sector-labels" font-family="monospace" font-size="22" text-anchor="middle">')
    for index, point in enumerate(labels):
        if point is None:
            continue
        x, y = xy(*point)
        if point_in_loops((round(point[0]), round(point[1])), sector_loops[index]) != 1:
            y -= 22
        color = "#ffe08a" if index in selected_sectors else "#f1f4f7"
        parts.append(
            f'<text data-sector-label="{index}" x="{_fmt(x)}" y="{_fmt(y)}" fill="{color}" '
            'font-weight="bold" paint-order="stroke" stroke="#111318" stroke-width="6">'
            f'S{index}</text>'
        )
    parts.append('</g>')
    start_x, start_y = xy(disk.header["start_x"], disk.header["start_y"])
    parts.append(
        f'<g id="player-start" stroke="#ffd866" stroke-width="3"><path d="M {_fmt(start_x - 9)} '
        f'{_fmt(start_y)} H {_fmt(start_x + 9)} M {_fmt(start_x)} {_fmt(start_y - 9)} '
        f'V {_fmt(start_y + 9)}"/></g>'
    )
    description = (
        f"sectors={len(disk.sectors)} walls={len(disk.walls)} "
        f"highlights=S{','.join(map(str, sorted(selected_sectors))) or 'none'} "
        f"W{','.join(map(str, sorted(selected_walls))) or 'none'}"
    )
    parts.append(
        f'<text x="{width - margin}" y="{height - 24}" fill="#aeb7c4" '
        f'font-family="monospace" font-size="18" text-anchor="end">'
        f'{html.escape(description)}</text>'
    )
    parts.append('</svg>')
    return "\n".join(parts)
