"""Doom → Build geometry lowering.

This translates Doom sector ownership (sidedefs pointing at sectors) into
Build sector-owned wall loops with reciprocal portals. It is a geometric
translation step, not a claim that a Doom linedef *is* a Build wall.

Unusual topology is reported rather than silently repaired.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from math import hypot
from typing import Any

from .doom import ML_TWOSIDED, NO_SIDE, DoomDiskMap
from .format import SECTOR_FIELDS, WALL_FIELDS
from .model import LevelIR


class DoomGeometryError(ValueError):
    pass


# NBlood wad2map.cpp (Ken Silverman): wall xy `((v-c)<<4)`, sector z `-(z<<8)`,
# vertex Y negated at load. TEDE1M9 (Blood recreation of Doom E1M1) selects the
# same ratios by wall-vector overlap (*16 Y-flip) and Z-hit count (*256).
XY_SCALE = 16
Z_SCALE = 256
XY_SCALE_EVIDENCE = (
    "NBlood source/tools/src/wad2map.cpp wall xy ((v-c)<<4); "
    "TEDE1M9 vs Doom E1M1 wall-vector overlap peaks at *16 with Y-flip"
)
Z_SCALE_EVIDENCE = (
    "NBlood wad2map.cpp sector z = -(doom_z<<8); "
    "TEDE1M9 floor/ceiling values match Doom heights * 256"
)


def scale_xy(value: int) -> int:
    return int(value) * XY_SCALE


def scale_z(value: int) -> int:
    return -int(value) * Z_SCALE


def scale_angle(doom_degrees: int) -> int:
    """Doom 0=east, CCW; Build 0=+X, Y-down, so negate after conversion."""
    return (2048 - (int(doom_degrees) % 360) * 2048 // 360) & 2047


def _empty(schema) -> dict[str, int]:
    return {name: 0 for name, _kind in schema}


def _area2(points: list[tuple[int, int]]) -> int:
    total = 0
    for index, (x, y) in enumerate(points):
        nx, ny = points[(index + 1) % len(points)]
        total += x * ny - nx * y
    return total


def _point_in_loop(point: tuple[int, int], loop: list[tuple[int, int]]) -> bool:
    x, y = point
    inside = False
    for index, (x1, y1) in enumerate(loop):
        x2, y2 = loop[(index + 1) % len(loop)]
        if (y1 > y) != (y2 > y) and x < x1 + (x2 - x1) * (y - y1) / (y2 - y1):
            inside = not inside
    return inside


@dataclass
class LoopEdge:
    x1: int
    y1: int
    x2: int
    y2: int
    linedef: int
    side: int


@dataclass
class SectorLoops:
    sector_id: int
    outer: list[LoopEdge]
    holes: list[list[LoopEdge]]
    warnings: list[str] = field(default_factory=list)


def _sector_edges(level: DoomDiskMap, sector_id: int) -> tuple[list[LoopEdge], list[str]]:
    edges: list[LoopEdge] = []
    warnings: list[str] = []
    self_refs = 0
    for line_id, line in enumerate(level.linedefs):
        sides = []
        for side_id, reverse in ((line.side_front, False), (line.side_back, True)):
            if side_id == NO_SIDE or not 0 <= side_id < len(level.sidedefs):
                continue
            if int(level.sidedefs[side_id].sector) != sector_id:
                continue
            a = level.vertices[line.v1]
            b = level.vertices[line.v2]
            if reverse:
                edges.append(LoopEdge(b.x, b.y, a.x, a.y, line_id, 1))
            else:
                edges.append(LoopEdge(a.x, a.y, b.x, b.y, line_id, 0))
            sides.append(side_id)
        if len(sides) == 2:
            self_refs += 1
    if self_refs:
        warnings.append(f"sector:{sector_id} has {self_refs} self-referencing linedef(s)")
    return edges, warnings


def _trace_loops(edges: list[LoopEdge]) -> tuple[list[list[int]], list[str]]:
    outgoing: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, edge in enumerate(edges):
        outgoing[(edge.x1, edge.y1)].append(index)
    used = [False] * len(edges)
    loops: list[list[int]] = []
    warnings: list[str] = []
    for start in range(len(edges)):
        if used[start]:
            continue
        loop: list[int] = []
        current = start
        guard = 0
        while not used[current]:
            used[current] = True
            loop.append(current)
            edge = edges[current]
            candidates = [index for index in outgoing[(edge.x2, edge.y2)] if not used[index]]
            if not candidates:
                break
            if len(candidates) > 1:
                warnings.append("vertex has multiple unused outgoing edges; first successor used")
            current = candidates[0]
            guard += 1
            if guard > len(edges) + 2:
                warnings.append("loop tracing exceeded edge count")
                break
        first, last = edges[loop[0]], edges[loop[-1]]
        if (last.x2, last.y2) != (first.x1, first.y1):
            warnings.append("open chain; sector boundary did not close")
        loops.append(loop)
    leftover = used.count(False)
    if leftover:
        warnings.append(f"{leftover} unused boundary edges remain")
    return loops, warnings


def _points(edges: list[LoopEdge], indices: list[int]) -> list[tuple[int, int]]:
    return [(edges[index].x1, edges[index].y1) for index in indices]


def extract_sector_loops(level: DoomDiskMap, sector_id: int) -> SectorLoops:
    edges, warnings = _sector_edges(level, sector_id)
    if len(edges) < 3:
        raise DoomGeometryError(f"sector:{sector_id} has fewer than 3 boundary edges")
    loops, loop_warnings = _trace_loops(edges)
    warnings.extend(loop_warnings)
    ranked: list[tuple[int, list[int], list[tuple[int, int]]]] = []
    for indices in loops:
        points = _points(edges, indices)
        ranked.append((abs(_area2(points)), indices, points))
    if not ranked:
        raise DoomGeometryError(f"sector:{sector_id} produced no loops")
    ranked.sort(key=lambda item: item[0], reverse=True)
    outer_indices = ranked[0][1]
    outer_points = ranked[0][2]
    holes: list[list[LoopEdge]] = []
    extra_outers = 0
    for _area, indices, points in ranked[1:]:
        sample = points[0]
        if _area2(points) == 0:
            warnings.append("degenerate zero-area loop rejected")
            continue
        if _point_in_loop(sample, outer_points):
            holes.append([edges[index] for index in indices])
        else:
            extra_outers += 1
            warnings.append("disconnected extra outer loop rejected")
    if extra_outers:
        warnings.append(f"sector:{sector_id} has {extra_outers} disconnected outer loop(s)")
    return SectorLoops(
        sector_id=sector_id,
        outer=[edges[index] for index in outer_indices],
        holes=holes,
        warnings=warnings,
    )


def _to_build_loop(edges: list[LoopEdge]) -> list[tuple[int, int, LoopEdge]]:
    """Y-flip, scale, and reverse so Build outer loops are clockwise.

    Each Build vertex keeps the Doom linedef/side whose physical segment
    leaves that vertex after the reverse walk.
    """
    n = len(edges)
    points = [(scale_xy(edge.x1), scale_xy(-edge.y1)) for edge in edges]
    return [
        (points[(n - 1 - index) % n][0], points[(n - 1 - index) % n][1], edges[(n - 2 - index) % n])
        for index in range(n)
    ]


def _reverse_build_loop(loop: list[tuple[int, int, LoopEdge]]) -> list[tuple[int, int, LoopEdge]]:
    """Reverse a Build loop while keeping each edge on the segment it describes."""
    if len(loop) < 2:
        return list(reversed(loop))
    points = [(x, y) for x, y, _ in loop]
    edges = [edge for _, _, edge in loop]
    points.reverse()
    edges.reverse()
    edges = edges[1:] + edges[:1]
    return [(points[index][0], points[index][1], edges[index]) for index in range(len(loop))]


def lower_doom_geometry(level: DoomDiskMap, *, ir: LevelIR) -> dict[str, Any]:
    """Append Build sectors/walls for every Doom sector. Does not assign player start."""
    warnings: list[dict[str, str]] = []
    edge_to_wall: dict[tuple[int, int], int] = {}
    sector_map: list[int] = []
    for doom_sector_id, sector in enumerate(level.sectors):
        try:
            loops = extract_sector_loops(level, doom_sector_id)
        except DoomGeometryError as exc:
            warnings.append({"severity": "error", "sector": f"sector:{doom_sector_id}", "message": str(exc)})
            sector_map.append(-1)
            continue
        for message in loops.warnings:
            warnings.append({"severity": "warning", "sector": f"sector:{doom_sector_id}", "message": message})
        build_loops = [_to_build_loop(loops.outer)]
        for hole in loops.holes:
            build_loops.append(_to_build_loop(hole))
        # Outer must be clockwise; holes counterclockwise.
        if _area2([(x, y) for x, y, _ in build_loops[0]]) < 0:
            build_loops[0] = _reverse_build_loop(build_loops[0])
        for index, hole in enumerate(build_loops[1:], start=1):
            if _area2([(x, y) for x, y, _ in hole]) > 0:
                build_loops[index] = _reverse_build_loop(hole)
        wall_base = len(ir.walls)
        wall_count = sum(len(item) for item in build_loops)
        fields = _empty(SECTOR_FIELDS)
        fields.update(
            wall_ptr=wall_base,
            wall_count=wall_count,
            ceiling_z=scale_z(sector.ceiling_height),
            floor_z=scale_z(sector.floor_height),
            extra=-1,
        )
        build_sector_id = len(ir.sectors)
        ir.sectors.append({"id": build_sector_id, "fields": fields, "blood": None})
        sector_map.append(build_sector_id)
        wall_id = wall_base
        for loop in build_loops:
            loop_start = wall_id
            for index, (x, y, edge) in enumerate(loop):
                next_id = loop_start if index == len(loop) - 1 else wall_id + 1
                nx, ny, _next_edge = loop[(index + 1) % len(loop)]
                wall = _empty(WALL_FIELDS)
                wall.update(
                    x=x, y=y, point2=next_id, next_wall=-1, next_sector=-1,
                    extra=-1,
                    x_repeat=max(1, min(255, round(hypot(nx - x, ny - y) / 128))),
                    y_repeat=8,
                )
                ir.walls.append({"id": wall_id, "fields": wall, "blood": None})
                edge_to_wall[(edge.linedef, edge.side)] = wall_id
                wall_id += 1

    portals = 0
    for line_id, line in enumerate(level.linedefs):
        if line.side_back == NO_SIDE or not (line.flags & ML_TWOSIDED):
            continue
        left = edge_to_wall.get((line_id, 0))
        right = edge_to_wall.get((line_id, 1))
        if left is None or right is None:
            warnings.append({
                "severity": "warning", "linedef": f"linedef:{line_id}",
                "message": "two-sided linedef missing a Build wall",
            })
            continue
        owner_left = _wall_owner(ir, left)
        owner_right = _wall_owner(ir, right)
        a, b = ir.walls[left]["fields"], ir.walls[right]["fields"]
        a_end, b_end = ir.walls[int(a["point2"])]["fields"], ir.walls[int(b["point2"])]["fields"]
        if (a["x"], a["y"], a_end["x"], a_end["y"]) != (b_end["x"], b_end["y"], b["x"], b["y"]):
            warnings.append({
                "severity": "warning", "linedef": f"linedef:{line_id}",
                "message": "two-sided linedef did not produce reversed coincident Build walls",
            })
            continue
        a.update(next_wall=right, next_sector=owner_right)
        b.update(next_wall=left, next_sector=owner_left)
        portals += 1

    return {
        "sector_map": sector_map,
        "edge_to_wall": {f"{line}:{side}": wall for (line, side), wall in sorted(edge_to_wall.items())},
        "portals": portals,
        "warnings": warnings,
        "xy_scale": XY_SCALE,
        "z_scale": Z_SCALE,
        "xy_scale_evidence": XY_SCALE_EVIDENCE,
        "z_scale_evidence": Z_SCALE_EVIDENCE,
    }


def _wall_owner(ir: LevelIR, wall_id: int) -> int:
    for sector_id, sector in enumerate(ir.sectors):
        first = int(sector["fields"]["wall_ptr"])
        count = int(sector["fields"]["wall_count"])
        if first <= wall_id < first + count:
            return sector_id
    raise DoomGeometryError(f"wall:{wall_id} has no sector owner")
