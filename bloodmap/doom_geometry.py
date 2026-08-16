"""Doom → Build geometry lowering.

This translates Doom sector ownership (sidedefs pointing at sectors) into
Build sector-owned wall loops with reciprocal portals. It is a geometric
translation step, not a claim that a Doom linedef *is* a Build wall.

Boundary tracing follows the wad2map continuation rule: collect every directed
sidedef edge of a sector, then choose a successor at ambiguous vertices by
geometric orientation. Input order is not a geometric tie-breaker.

Unusual topology fails closed. Successful lowering reports zero dropped and
zero duplicated source edges.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from math import atan2, hypot
from typing import Any, Iterable

from .doom import ML_TWOSIDED, NO_SIDE, DoomDiskMap
from .format import SECTOR_FIELDS, WALL_FIELDS
from .model import LevelIR


class DoomGeometryError(ValueError):
    """Non-representable or malformed Doom sector boundary."""

    def __init__(
        self,
        reason: str,
        *,
        map_name: str = "",
        sector_id: int | None = None,
        linedefs: Iterable[int] | None = None,
    ) -> None:
        self.reason = reason
        self.map_name = map_name
        self.sector_id = sector_id
        self.linedefs = sorted({int(item) for item in (linedefs or [])})
        parts: list[str] = []
        if map_name:
            parts.append(str(map_name))
        if sector_id is not None:
            parts.append(f"sector:{sector_id}")
        if self.linedefs:
            joined = ",".join(f"linedef:{item}" for item in self.linedefs)
            parts.append(f"linedefs:[{joined}]")
        parts.append(reason)
        super().__init__(" ".join(parts))


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


def _centroid(points: list[tuple[int, int]]) -> tuple[float, float]:
    if not points:
        return 0.0, 0.0
    return sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points)


@dataclass(frozen=True)
class DirectedBoundaryEdge:
    x1: int
    y1: int
    x2: int
    y2: int
    linedef: int
    side: int

    @property
    def start(self) -> tuple[int, int]:
        return (self.x1, self.y1)

    @property
    def end(self) -> tuple[int, int]:
        return (self.x2, self.y2)

    @property
    def key(self) -> tuple[int, int, int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2, self.linedef, self.side)

    def native_ref(self) -> str:
        return f"linedef:{self.linedef}"


# Compatibility alias used by tests and older call sites.
LoopEdge = DirectedBoundaryEdge


@dataclass
class BoundaryLoop:
    edges: list[DirectedBoundaryEdge]
    kind: str  # "outer" | "hole"

    def points(self) -> list[tuple[int, int]]:
        return [(edge.x1, edge.y1) for edge in self.edges]


@dataclass
class BoundaryComponent:
    outer: BoundaryLoop
    holes: list[BoundaryLoop] = field(default_factory=list)

    def all_edges(self) -> list[DirectedBoundaryEdge]:
        edges = list(self.outer.edges)
        for hole in self.holes:
            edges.extend(hole.edges)
        return edges


@dataclass
class GeometryConservationReport:
    source_directed_edges: int
    emitted_directed_edges: int
    dropped_source_edges: list[tuple[int, int, int, int, int, int]]
    duplicated_source_edges: list[tuple[int, int, int, int, int, int]]
    boundary_component_count: int
    ambiguous_vertices: list[tuple[int, int]]
    unpaired_portal_candidates: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_directed_edges": self.source_directed_edges,
            "emitted_directed_edges": self.emitted_directed_edges,
            "dropped_source_edges": [list(item) for item in self.dropped_source_edges],
            "duplicated_source_edges": [list(item) for item in self.duplicated_source_edges],
            "boundary_component_count": self.boundary_component_count,
            "ambiguous_vertices": [list(item) for item in self.ambiguous_vertices],
            "unpaired_portal_candidates": list(self.unpaired_portal_candidates),
        }

    @property
    def conserved(self) -> bool:
        return not self.dropped_source_edges and not self.duplicated_source_edges


@dataclass
class SectorBoundary:
    sector_id: int
    map_name: str
    components: list[BoundaryComponent]
    conservation: GeometryConservationReport
    ambiguous_vertices: list[tuple[int, int]] = field(default_factory=list)

    @property
    def outer(self) -> list[DirectedBoundaryEdge]:
        return list(self.components[0].outer.edges) if self.components else []

    @property
    def holes(self) -> list[list[DirectedBoundaryEdge]]:
        return [list(hole.edges) for component in self.components for hole in component.holes]

    @property
    def extra_outers(self) -> list[list[DirectedBoundaryEdge]]:
        return [list(component.outer.edges) for component in self.components[1:]]

    @property
    def warnings(self) -> list[str]:
        return [f"ambiguous vertex {x},{y}" for x, y in self.ambiguous_vertices]


# Compatibility name used by existing tests.
SectorLoops = SectorBoundary


def _sector_edges(
    level: DoomDiskMap, sector_id: int,
) -> list[DirectedBoundaryEdge]:
    edges: list[DirectedBoundaryEdge] = []
    for line_id, line in enumerate(level.linedefs):
        for side, reverse in ((0, False), (1, True)):
            side_id = line.side_front if side == 0 else line.side_back
            if side_id == NO_SIDE or not 0 <= side_id < len(level.sidedefs):
                continue
            if int(level.sidedefs[side_id].sector) != sector_id:
                continue
            a = level.vertices[line.v1]
            b = level.vertices[line.v2]
            if reverse:
                edges.append(DirectedBoundaryEdge(b.x, b.y, a.x, a.y, line_id, side))
            else:
                edges.append(DirectedBoundaryEdge(a.x, a.y, b.x, b.y, line_id, side))
    return edges


def _successor_rank(incoming: DirectedBoundaryEdge, outgoing: DirectedBoundaryEdge) -> tuple:
    """Rank outgoing edges: most clockwise interior-on-right turn first.

    wad2map.cpp compares 2D cross products at the shared vertex and rejects a
    collinear continuation when a turning candidate exists. Linedef/side break
    remaining ties; input order does not.
    """
    in_dx = incoming.x2 - incoming.x1
    in_dy = incoming.y2 - incoming.y1
    out_dx = outgoing.x2 - outgoing.x1
    out_dy = outgoing.y2 - outgoing.y1
    cross = in_dx * out_dy - in_dy * out_dx
    dot = in_dx * out_dx + in_dy * out_dy
    collinear = 0 if cross else 1
    return (collinear, atan2(cross, dot), outgoing.linedef, outgoing.side)


def _choose_successor(
    incoming: DirectedBoundaryEdge,
    candidates: list[DirectedBoundaryEdge],
) -> DirectedBoundaryEdge:
    if not candidates:
        raise DoomGeometryError("no successor")
    return min(candidates, key=lambda item: _successor_rank(incoming, item))


def _trace_loops(
    edges: list[DirectedBoundaryEdge],
    *,
    map_name: str,
    sector_id: int,
) -> tuple[list[list[DirectedBoundaryEdge]], list[tuple[int, int]]]:
    by_start: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, edge in enumerate(edges):
        if (edge.x1, edge.y1) == (edge.x2, edge.y2):
            raise DoomGeometryError(
                "zero-length boundary edge",
                map_name=map_name, sector_id=sector_id, linedefs=[edge.linedef],
            )
        by_start[edge.start].append(index)
    ambiguous = sorted(vertex for vertex, items in by_start.items() if len(items) > 1)
    unused = set(range(len(edges)))
    loops: list[list[DirectedBoundaryEdge]] = []
    starts = sorted(unused, key=lambda index: (edges[index].linedef, edges[index].side, index))
    for start_index in starts:
        if start_index not in unused:
            continue
        loop_indices: list[int] = []
        current = start_index
        guard = 0
        while current in unused:
            unused.remove(current)
            loop_indices.append(current)
            edge = edges[current]
            first = edges[loop_indices[0]]
            if edge.end == first.start and len(loop_indices) >= 2:
                break
            remaining = [index for index in by_start[edge.end] if index in unused]
            if not remaining:
                raise DoomGeometryError(
                    "open chain; sector boundary did not close",
                    map_name=map_name, sector_id=sector_id,
                    linedefs=[edges[index].linedef for index in loop_indices],
                )
            chosen = _choose_successor(edge, [edges[index] for index in remaining])
            current = next(
                index for index in remaining
                if edges[index].key == chosen.key
            )
            guard += 1
            if guard > len(edges) + 2:
                raise DoomGeometryError(
                    "loop tracing exceeded edge count",
                    map_name=map_name, sector_id=sector_id,
                    linedefs=[edges[index].linedef for index in loop_indices],
                )
        first, last = edges[loop_indices[0]], edges[loop_indices[-1]]
        if last.end != first.start:
            raise DoomGeometryError(
                "open chain; sector boundary did not close",
                map_name=map_name, sector_id=sector_id,
                linedefs=[edges[index].linedef for index in loop_indices],
            )
        loops.append([edges[index] for index in loop_indices])
    if unused:
        raise DoomGeometryError(
            f"{len(unused)} unused boundary edges remain",
            map_name=map_name, sector_id=sector_id,
            linedefs=[edges[index].linedef for index in sorted(unused)],
        )
    return loops, ambiguous


def _conservation(
    source: list[DirectedBoundaryEdge],
    emitted: list[DirectedBoundaryEdge],
    *,
    component_count: int,
    ambiguous: list[tuple[int, int]],
    unpaired: list[str] | None = None,
) -> GeometryConservationReport:
    source_keys = [edge.key for edge in source]
    emitted_keys = [edge.key for edge in emitted]
    source_counts = Counter(source_keys)
    emitted_counts = Counter(emitted_keys)
    dropped = [key for key, count in source_counts.items() if emitted_counts[key] < count for _ in range(count - emitted_counts[key])]
    duplicated = []
    for key, count in emitted_counts.items():
        extra = count - source_counts[key]
        if extra > 0:
            duplicated.extend([key] * extra)
    return GeometryConservationReport(
        source_directed_edges=len(source),
        emitted_directed_edges=len(emitted),
        dropped_source_edges=dropped,
        duplicated_source_edges=duplicated,
        boundary_component_count=component_count,
        ambiguous_vertices=list(ambiguous),
        unpaired_portal_candidates=list(unpaired or []),
    )


def _require_conserved(report: GeometryConservationReport, *, map_name: str, sector_id: int) -> None:
    if report.conserved:
        return
    linedefs = sorted({
        key[4] for key in report.dropped_source_edges + report.duplicated_source_edges
    })
    raise DoomGeometryError(
        "geometry conservation failed "
        f"dropped={len(report.dropped_source_edges)} duplicated={len(report.duplicated_source_edges)}",
        map_name=map_name, sector_id=sector_id, linedefs=linedefs,
    )


def _classify_components(
    loops: list[list[DirectedBoundaryEdge]],
    *,
    map_name: str,
    sector_id: int,
) -> list[BoundaryComponent]:
    ranked: list[tuple[int, int, list[DirectedBoundaryEdge], list[tuple[int, int]]]] = []
    for loop in loops:
        points = [(edge.x1, edge.y1) for edge in loop]
        area = _area2(points)
        if area == 0 or len(loop) < 3:
            raise DoomGeometryError(
                "degenerate zero-area or self-referencing boundary loop",
                map_name=map_name, sector_id=sector_id,
                linedefs=[edge.linedef for edge in loop],
            )
        ranked.append((abs(area), area, loop, points))
    ranked.sort(key=lambda item: (-item[0], item[3][0][0], item[3][0][1], item[2][0].linedef))
    assigned = [False] * len(ranked)
    components: list[BoundaryComponent] = []
    for outer_index, (_abs_area, outer_area, outer_loop, outer_points) in enumerate(ranked):
        if assigned[outer_index]:
            continue
        holes: list[BoundaryLoop] = []
        for inner_index in range(outer_index + 1, len(ranked)):
            if assigned[inner_index]:
                continue
            _inner_abs, inner_area, inner_loop, inner_points = ranked[inner_index]
            sample = _centroid(inner_points)
            if not _point_in_loop((sample[0], sample[1]), outer_points):
                continue
            if (inner_area > 0) == (outer_area > 0):
                raise DoomGeometryError(
                    "nested same-winding loop is not representable as a Build hole",
                    map_name=map_name, sector_id=sector_id,
                    linedefs=[edge.linedef for edge in inner_loop],
                )
            assigned[inner_index] = True
            holes.append(BoundaryLoop(edges=list(inner_loop), kind="hole"))
        assigned[outer_index] = True
        holes.sort(key=lambda item: (item.points()[0], item.edges[0].linedef, item.edges[0].side))
        components.append(BoundaryComponent(
            outer=BoundaryLoop(edges=list(outer_loop), kind="outer"),
            holes=holes,
        ))
    components.sort(key=lambda item: (item.outer.points()[0], item.outer.edges[0].linedef))
    return components


def extract_sector_loops(level: DoomDiskMap, sector_id: int) -> SectorBoundary:
    edges = _sector_edges(level, sector_id)
    map_name = getattr(level, "name", "") or ""
    if len(edges) < 3:
        raise DoomGeometryError(
            "sector has fewer than 3 boundary edges",
            map_name=map_name, sector_id=sector_id,
            linedefs=[edge.linedef for edge in edges],
        )
    loops, ambiguous = _trace_loops(edges, map_name=map_name, sector_id=sector_id)
    components = _classify_components(loops, map_name=map_name, sector_id=sector_id)
    emitted = [edge for component in components for edge in component.all_edges()]
    conservation = _conservation(
        edges, emitted, component_count=len(components), ambiguous=ambiguous,
    )
    _require_conserved(conservation, map_name=map_name, sector_id=sector_id)
    return SectorBoundary(
        sector_id=sector_id,
        map_name=map_name,
        components=components,
        conservation=conservation,
        ambiguous_vertices=ambiguous,
    )


def _to_build_loop(edges: list[DirectedBoundaryEdge]) -> list[tuple[int, int, DirectedBoundaryEdge]]:
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


def _reverse_build_loop(
    loop: list[tuple[int, int, DirectedBoundaryEdge]],
) -> list[tuple[int, int, DirectedBoundaryEdge]]:
    """Reverse a Build loop while keeping each edge on the segment it describes."""
    if len(loop) < 2:
        return list(reversed(loop))
    points = [(x, y) for x, y, _ in loop]
    edges = [edge for _, _, edge in loop]
    points.reverse()
    edges.reverse()
    edges = edges[1:] + edges[:1]
    return [(points[index][0], points[index][1], edges[index]) for index in range(len(loop))]


def _emit_component_loops(component: BoundaryComponent) -> list[list[tuple[int, int, DirectedBoundaryEdge]]]:
    build_loops = [_to_build_loop(component.outer.edges)]
    for hole in component.holes:
        build_loops.append(_to_build_loop(hole.edges))
    if _area2([(x, y) for x, y, _ in build_loops[0]]) < 0:
        build_loops[0] = _reverse_build_loop(build_loops[0])
    for index, hole in enumerate(build_loops[1:], start=1):
        if _area2([(x, y) for x, y, _ in hole]) > 0:
            build_loops[index] = _reverse_build_loop(hole)
    return build_loops


def _rotate_tuple(values: tuple) -> tuple:
    if not values:
        return values
    start = min(range(len(values)), key=lambda index: values[index])
    return values[start:] + values[:start]


def canonical_topology(ir: LevelIR) -> dict[str, Any]:
    """Index-normalized topology used only for comparison and tests."""
    components = []
    portals = []
    ownership = []
    seen_portals: set[tuple[int, int]] = set()
    for sector_id, sector in enumerate(ir.sectors):
        first = int(sector["fields"]["wall_ptr"])
        count = int(sector["fields"]["wall_count"])
        used = [False] * count
        loops = []
        for offset in range(count):
            if used[offset]:
                continue
            loop = []
            current = offset
            for _ in range(count + 1):
                if used[current]:
                    break
                used[current] = True
                wall_id = first + current
                wall = ir.walls[wall_id]["fields"]
                nxt = int(wall["point2"])
                end = ir.walls[nxt]["fields"]
                next_sector = int(wall["next_sector"])
                loop.append((
                    int(wall["x"]), int(wall["y"]), int(end["x"]), int(end["y"]),
                    next_sector >= 0,
                ))
                current = nxt - first
            loops.append(_rotate_tuple(tuple(loop)))
        loops.sort()
        components.append({"sector": sector_id, "loops": loops, "wall_count": count})
        ownership.append((sector_id, count))
        for wall_id in range(first, first + count):
            nxt = int(ir.walls[wall_id]["fields"]["next_wall"])
            if nxt < 0:
                continue
            pair = tuple(sorted((wall_id, nxt)))
            if pair in seen_portals:
                continue
            seen_portals.add(pair)
            a, b = ir.walls[wall_id]["fields"], ir.walls[nxt]["fields"]
            a_end, b_end = ir.walls[int(a["point2"])]["fields"], ir.walls[int(b["point2"])]["fields"]
            geom = tuple(sorted((
                (int(a["x"]), int(a["y"]), int(a_end["x"]), int(a_end["y"])),
                (int(b["x"]), int(b["y"]), int(b_end["x"]), int(b_end["y"])),
            )))
            owners = tuple(sorted((
                int(ir.walls[wall_id]["fields"]["next_sector"]),
                int(ir.walls[nxt]["fields"]["next_sector"]),
            )))
            portals.append({"segment": geom, "sectors": owners})
    directed = [
        edge[:4]
        for item in components
        for loop in item["loops"]
        for edge in loop
    ]
    return {
        "directed_edge_multiset": sorted(directed),
        "boundary_components": components,
        "portal_pairings": sorted(portals, key=lambda item: (item["segment"], item["sectors"])),
        "sector_ownership": ownership,
        "wall_count": len(ir.walls),
        "sector_count": len(ir.sectors),
    }


def lower_doom_geometry(level: DoomDiskMap, *, ir: LevelIR) -> dict[str, Any]:
    """Append Build sectors/walls for every Doom sector. Does not assign player start."""
    warnings: list[dict[str, str]] = []
    edge_to_wall: dict[tuple[int, int], int] = {}
    sector_map: list[int] = []
    conservation_reports: list[dict[str, Any]] = []
    map_name = getattr(level, "name", "") or ""
    for doom_sector_id, sector in enumerate(level.sectors):
        boundary = extract_sector_loops(level, doom_sector_id)
        conservation_reports.append({"sector": doom_sector_id, **boundary.conservation.to_dict()})
        build_loops: list[list[tuple[int, int, DirectedBoundaryEdge]]] = []
        for component in boundary.components:
            build_loops.extend(_emit_component_loops(component))
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
                previous = edge_to_wall.get((edge.linedef, edge.side))
                if previous is not None:
                    raise DoomGeometryError(
                        "duplicated source edge in Build lowering",
                        map_name=map_name, sector_id=doom_sector_id,
                        linedefs=[edge.linedef],
                    )
                edge_to_wall[(edge.linedef, edge.side)] = wall_id
                wall_id += 1

    portals = 0
    unpaired: list[str] = []
    for line_id, line in enumerate(level.linedefs):
        if line.side_back == NO_SIDE or not (line.flags & ML_TWOSIDED):
            continue
        left = edge_to_wall.get((line_id, 0))
        right = edge_to_wall.get((line_id, 1))
        if left is None or right is None:
            unpaired.append(f"linedef:{line_id}")
            raise DoomGeometryError(
                "two-sided linedef missing a Build wall",
                map_name=map_name, sector_id=None, linedefs=[line_id],
            )
        owner_left = _wall_owner(ir, left)
        owner_right = _wall_owner(ir, right)
        a, b = ir.walls[left]["fields"], ir.walls[right]["fields"]
        a_end, b_end = ir.walls[int(a["point2"])]["fields"], ir.walls[int(b["point2"])]["fields"]
        if (a["x"], a["y"], a_end["x"], a_end["y"]) != (b_end["x"], b_end["y"], b["x"], b["y"]):
            raise DoomGeometryError(
                "two-sided linedef did not produce reversed coincident Build walls",
                map_name=map_name, sector_id=None, linedefs=[line_id],
            )
        a.update(next_wall=right, next_sector=owner_right)
        b.update(next_wall=left, next_sector=owner_left)
        portals += 1

    total_source = sum(item["source_directed_edges"] for item in conservation_reports)
    total_emitted = sum(item["emitted_directed_edges"] for item in conservation_reports)
    dropped = [edge for item in conservation_reports for edge in item["dropped_source_edges"]]
    duplicated = [edge for item in conservation_reports for edge in item["duplicated_source_edges"]]
    conservation = GeometryConservationReport(
        source_directed_edges=total_source,
        emitted_directed_edges=total_emitted,
        dropped_source_edges=[tuple(item) for item in dropped],
        duplicated_source_edges=[tuple(item) for item in duplicated],
        boundary_component_count=sum(item["boundary_component_count"] for item in conservation_reports),
        ambiguous_vertices=[
            tuple(vertex)
            for item in conservation_reports
            for vertex in item["ambiguous_vertices"]
        ],
        unpaired_portal_candidates=unpaired,
    )
    _require_conserved(conservation, map_name=map_name, sector_id=None)

    return {
        "sector_map": sector_map,
        "edge_to_wall": {f"{line}:{side}": wall for (line, side), wall in sorted(edge_to_wall.items())},
        "portals": portals,
        "warnings": warnings,
        "conservation": conservation.to_dict(),
        "conservation_by_sector": conservation_reports,
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
