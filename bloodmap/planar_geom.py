"""Exact integer planar predicates for authored Build geometry.

These helpers are shared by geometry audit, authored validation, and the planar
layout compiler. They do not mutate maps. Intersection tests use integer
orientation; point-in-polygon uses exact rationals. Floating-point is not used
to decide incidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence

Point = tuple[int, int]
Segment = tuple[Point, Point]


class PlanarGeomError(ValueError):
    pass


def orientation(a: Point, b: Point, c: Point) -> int:
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (value > 0) - (value < 0)


def area2(points: Sequence[Point]) -> int:
    total = 0
    count = len(points)
    for index, (x, y) in enumerate(points):
        nx, ny = points[(index + 1) % count]
        total += x * ny - nx * y
    return total


def is_clockwise(points: Sequence[Point]) -> bool:
    return area2(points) > 0


def on_segment_inclusive(a: Point, b: Point, point: Point) -> bool:
    if orientation(a, b, point) != 0:
        return False
    return (
        min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])
    )


def on_segment_strict(a: Point, b: Point, point: Point) -> bool:
    return on_segment_inclusive(a, b, point) and point != a and point != b


def undirected_key(a: Point, b: Point) -> tuple[Point, Point]:
    return (a, b) if a <= b else (b, a)


def directed_key(a: Point, b: Point) -> tuple[Point, Point]:
    return (a, b)


def segment_length_sq(a: Point, b: Point) -> int:
    dx, dy = b[0] - a[0], b[1] - a[1]
    return dx * dx + dy * dy


def midpoint_toward(a: Point, b: Point) -> Point:
    """Integer point strictly between a and b when the segment is long enough."""
    return ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)


def proper_crossing(a: Point, b: Point, c: Point, d: Point) -> bool:
    """True when segment interiors intersect at a single non-collinear point."""
    oa, ob = orientation(a, b, c), orientation(a, b, d)
    oc, od = orientation(c, d, a), orientation(c, d, b)
    return oa * ob < 0 and oc * od < 0


def _axis_interval(a: Point, b: Point, axis: int) -> tuple[int, int]:
    left, right = a[axis], b[axis]
    return (left, right) if left <= right else (right, left)


def collinear(a: Point, b: Point, c: Point, d: Point) -> bool:
    return orientation(a, b, c) == 0 and orientation(a, b, d) == 0


def collinear_overlap_interval(
    a: Point, b: Point, c: Point, d: Point,
) -> tuple[Point, Point] | None:
    """Return the closed overlap endpoints if collinear segments share positive length."""
    if not collinear(a, b, c, d):
        return None
    if (a, b) == (c, d) or (a, b) == (d, c):
        return undirected_key(a, b)
    axis = 0 if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else 1
    left = max(min(a[axis], b[axis]), min(c[axis], d[axis]))
    right = min(max(a[axis], b[axis]), max(c[axis], d[axis]))
    if right <= left:
        return None
    points = [a, b, c, d]
    start = min((point for point in points if point[axis] == left), key=lambda item: item)
    end = min((point for point in points if point[axis] == right), key=lambda item: item)
    if start == end:
        return None
    return (start, end)


def same_direction(a: Point, b: Point, c: Point, d: Point) -> bool:
    return (b[0] - a[0]) * (d[0] - c[0]) + (b[1] - a[1]) * (d[1] - c[1]) > 0


def exact_reversed(a: Point, b: Point, c: Point, d: Point) -> bool:
    return (a, b) == (d, c)


def exact_same_direction(a: Point, b: Point, c: Point, d: Point) -> bool:
    return (a, b) == (c, d)


def t_junction_point(a: Point, b: Point, c: Point, d: Point) -> Point | None:
    """Return the endpoint that lies strictly on the other segment, if any."""
    for point, start, end in ((a, c, d), (b, c, d), (c, a, b), (d, a, b)):
        if on_segment_strict(start, end, point):
            return point
    return None


def classify_segment_pair(a: Point, b: Point, c: Point, d: Point) -> dict[str, object] | None:
    """Classify two directed segments. Endpoint-only contact is not a conflict."""
    if a == b or c == d:
        return {
            "kind": "zero_length",
            "a": [a, b],
            "b": [c, d],
        }
    if proper_crossing(a, b, c, d):
        return {
            "kind": "proper_crossing",
            "a": [a, b],
            "b": [c, d],
            "integer_intersection": integer_intersection(a, b, c, d),
        }
    overlap = collinear_overlap_interval(a, b, c, d)
    if overlap is not None:
        left, right = overlap
        reversed_exact = exact_reversed(a, b, c, d)
        same_exact = exact_same_direction(a, b, c, d)
        kind = "partial_collinear_overlap"
        if reversed_exact:
            kind = "exact_reversed_coincident"
        elif same_exact:
            kind = "exact_same_direction_coincident"
        elif undirected_key(a, b) == undirected_key(c, d):
            kind = "exact_same_direction_coincident" if same_direction(a, b, c, d) else "exact_reversed_coincident"
        return {
            "kind": kind,
            "a": [a, b],
            "b": [c, d],
            "overlap": [left, right],
            "same_direction": same_direction(a, b, c, d),
            "covers_a": undirected_key(a, b) == undirected_key(left, right),
            "covers_b": undirected_key(c, d) == undirected_key(left, right),
        }
    junction = t_junction_point(a, b, c, d)
    if junction is not None:
        return {
            "kind": "t_junction",
            "a": [a, b],
            "b": [c, d],
            "point": junction,
        }
    return None


def integer_intersection(a: Point, b: Point, c: Point, d: Point) -> Point | None:
    """Return the intersection if it is an integer lattice point; otherwise None."""
    x1, y1 = a
    x2, y2 = b
    x3, y3 = c
    x4, y4 = d
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denom == 0:
        return None
    px_num = (x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)
    py_num = (x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)
    if px_num % denom or py_num % denom:
        return None
    return (px_num // denom, py_num // denom)


def split_points_along(a: Point, b: Point, points: Iterable[Point]) -> list[Point]:
    """Return unique lattice points on AB, ordered from A to B, including A and B."""
    ordered = {a, b}
    for point in points:
        if on_segment_inclusive(a, b, point):
            ordered.add(point)
    dx, dy = b[0] - a[0], b[1] - a[1]

    def parameter(point: Point) -> int:
        return (point[0] - a[0]) * dx + (point[1] - a[1]) * dy

    return sorted(ordered, key=parameter)


def atomic_subsegments(a: Point, b: Point, points: Iterable[Point]) -> list[Segment]:
    chain = split_points_along(a, b, points)
    return [(chain[index], chain[index + 1]) for index in range(len(chain) - 1) if chain[index] != chain[index + 1]]


def point_on_loop_boundary(point: Point, loop: Sequence[Point]) -> bool:
    count = len(loop)
    for index in range(count):
        if on_segment_inclusive(loop[index], loop[(index + 1) % count], point):
            return True
    return False

def point_in_loop(point: Point, loop: Sequence[Point]) -> int:
    """Return 1 inside, 0 outside, -1 on boundary. Even-odd with exact rationals."""
    if point_on_loop_boundary(point, loop):
        return -1
    x, y = point
    inside = False
    count = len(loop)
    for index in range(count):
        x1, y1 = loop[index]
        x2, y2 = loop[(index + 1) % count]
        if (y1 > y) != (y2 > y):
            crossing_x = Fraction(x1) + Fraction((y - y1) * (x2 - x1), y2 - y1)
            if crossing_x > x:
                inside = not inside
    return int(inside)


def point_in_loops(point: Point, loops: Sequence[Sequence[Point]]) -> int:
    """Even-odd across every loop of a sector, including holes."""
    on_boundary = False
    inside = False
    for loop in loops:
        state = point_in_loop(point, loop)
        if state < 0:
            on_boundary = True
        elif state == 1:
            inside = not inside
    if on_boundary:
        return -1
    return int(inside)


def validate_loop(points: Sequence[Point], *, role: str = "outer") -> list[str]:
    errors: list[str] = []
    polygon = [(int(x), int(y)) for x, y in points]
    if len(polygon) < 3:
        errors.append("loop needs at least three points")
        return errors
    if any(polygon[index] == polygon[(index + 1) % len(polygon)] for index in range(len(polygon))):
        errors.append("zero-length edge")
    if len(set(polygon)) != len(polygon):
        if any(polygon[index] == polygon[(index + 1) % len(polygon)] for index in range(len(polygon))):
            errors.append("duplicate consecutive vertices")
        else:
            errors.append("duplicate non-consecutive vertices")
    signed = area2(polygon)
    if signed == 0:
        errors.append("zero-area loop")
    elif role == "outer" and signed < 0:
        errors.append("invalid winding: outer loop must be clockwise in Build screen-space")
    elif role == "hole" and signed > 0:
        errors.append("invalid winding: hole loop must be counterclockwise in Build screen-space")
    segments = [(polygon[index], polygon[(index + 1) % len(polygon)]) for index in range(len(polygon))]
    for left in range(len(segments)):
        for right in range(left + 1, len(segments)):
            adjacent = right in {left + 1, (left - 1) % len(segments)} or (
                left == 0 and right == len(segments) - 1
            )
            if adjacent:
                continue
            relation = classify_segment_pair(*segments[left], *segments[right])
            if relation is not None and relation["kind"] in {"proper_crossing", "partial_collinear_overlap"}:
                errors.append(f"self-intersection ({relation['kind']})")
                return errors
    return errors


def sample_strict_interior(loops: Sequence[Sequence[Point]]) -> Point | None:
    """Pick a lattice point strictly inside the polygon if one is obvious."""
    if not loops:
        return None
    outer = loops[0]
    signed = area2(outer)
    if signed == 0:
        return None
    cx = sum(x for x, _ in outer) / len(outer)
    cy = sum(y for _, y in outer) / len(outer)
    candidates = [
        (round(cx), round(cy)),
        (int(cx), int(cy)),
        (int(cx) + 1, int(cy)),
        (int(cx), int(cy) + 1),
    ]
    for index in range(len(outer)):
        a, b = outer[index], outer[(index + 1) % len(outer)]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        nx, ny = b[1] - a[1], a[0] - b[0]
        if signed > 0:
            nx, ny = -nx, -ny
        length = max(1.0, (nx * nx + ny * ny) ** 0.5)
        candidates.append((round(mx + 8 * nx / length), round(my + 8 * ny / length)))
    seen: set[Point] = set()
    for candidate in candidates:
        point = (int(candidate[0]), int(candidate[1]))
        if point in seen:
            continue
        seen.add(point)
        if point_in_loops(point, loops) == 1:
            return point
    return None


def z_interval(ceiling_z: int, floor_z: int) -> tuple[int, int]:
    lo, hi = int(ceiling_z), int(floor_z)
    return (lo, hi) if lo <= hi else (hi, lo)


def z_relation(left: tuple[int, int], right: tuple[int, int]) -> str:
    if left[1] < right[0] or right[1] < left[0]:
        return "vertically_disjoint"
    if left[1] == right[0] or right[1] == left[0]:
        return "vertically_touching"
    return "overlapping_vertical_volumes"


def polygon_relation(
    loops_a: Sequence[Sequence[Point]],
    loops_b: Sequence[Sequence[Point]],
) -> dict[str, object]:
    """Classify XY footprint relationship using actual polygon tests, not AABBs."""
    edges_a = _loop_edges(loops_a)
    edges_b = _loop_edges(loops_b)
    crossings = []
    collinear_hits = []
    junctions = []
    shared_full = []
    for a1, a2 in edges_a:
        for b1, b2 in edges_b:
            relation = classify_segment_pair(a1, a2, b1, b2)
            if relation is None:
                continue
            kind = str(relation["kind"])
            if kind == "proper_crossing":
                crossings.append(relation)
            elif kind == "t_junction":
                junctions.append(relation)
            elif kind in {
                "partial_collinear_overlap",
                "exact_reversed_coincident",
                "exact_same_direction_coincident",
            }:
                collinear_hits.append(relation)
                if kind in {"exact_reversed_coincident", "exact_same_direction_coincident"}:
                    shared_full.append(relation)
    a_inside_b = _strict_vertex_inside(loops_a, loops_b)
    b_inside_a = _strict_vertex_inside(loops_b, loops_a)
    a_all_in_b = _all_vertices_in_or_on(loops_a, loops_b)
    b_all_in_a = _all_vertices_in_or_on(loops_b, loops_a)
    if crossings or (a_inside_b and b_inside_a):
        kind = "partial_area_overlap"
    elif a_all_in_b and a_inside_b and not b_inside_a:
        kind = "full_containment_a_in_b"
    elif b_all_in_a and b_inside_a and not a_inside_b:
        kind = "full_containment_b_in_a"
    elif shared_full and not a_inside_b and not b_inside_a and not crossings:
        kind = "exactly_shared_boundary"
    elif (collinear_hits or junctions) and not a_inside_b and not b_inside_a:
        kind = "boundary_touching"
    else:
        kind = "disjoint"
    hole = False
    if kind in {"full_containment_a_in_b", "boundary_touching", "exactly_shared_boundary"}:
        hole = _matches_hole(loops_a, loops_b)
    if kind in {"full_containment_b_in_a", "boundary_touching", "exactly_shared_boundary"}:
        hole = hole or _matches_hole(loops_b, loops_a)
    if hole and kind.startswith("full_containment"):
        kind = "hole_containment"
    return {
        "kind": kind,
        "proper_crossings": crossings,
        "collinear": collinear_hits,
        "t_junctions": junctions,
        "a_strict_interior_vertex_in_b": a_inside_b,
        "b_strict_interior_vertex_in_a": b_inside_a,
        "hole_relationship": hole,
    }


def _loop_edges(loops: Sequence[Sequence[Point]]) -> list[Segment]:
    edges: list[Segment] = []
    for loop in loops:
        count = len(loop)
        for index in range(count):
            edges.append((loop[index], loop[(index + 1) % count]))
    return edges


def _strict_vertex_inside(subject: Sequence[Sequence[Point]], host: Sequence[Sequence[Point]]) -> bool:
    for loop in subject:
        for point in loop:
            if point_in_loops(point, host) == 1:
                return True
    return False


def _all_vertices_in_or_on(subject: Sequence[Sequence[Point]], host: Sequence[Sequence[Point]]) -> bool:
    for loop in subject:
        for point in loop:
            if point_in_loops(point, host) == 0:
                return False
    return True


def _matches_hole(inner: Sequence[Sequence[Point]], outer: Sequence[Sequence[Point]]) -> bool:
    if len(inner) < 1 or len(outer) < 2:
        return False
    inner_cycle = _cycle_key(inner[0])
    for hole in outer[1:]:
        if _cycle_key(hole) == inner_cycle or _cycle_key(list(reversed(hole))) == inner_cycle:
            return True
    return False


def loops_equivalent(left: Sequence[Point], right: Sequence[Point]) -> bool:
    return _cycle_key(left) == _cycle_key(right) or _cycle_key(left) == _cycle_key(list(reversed(right)))


def _cycle_key(points: Sequence[Point]) -> tuple[Point, ...]:
    if not points:
        return ()
    start = min(range(len(points)), key=lambda index: points[index])
    rotated = list(points[start:]) + list(points[:start])
    return tuple(rotated)


@dataclass(frozen=True)
class LoopView:
    points: tuple[Point, ...]
    kind: str

    def edges(self) -> list[Segment]:
        count = len(self.points)
        return [(self.points[index], self.points[(index + 1) % count]) for index in range(count)]

def canonical_ring(loop: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    """A loop's corners, with vertices that only subdivide an edge removed.

    Two sectors on one footprint rarely have the same vertex list: each has its
    own doorways splitting its own walls, so a storey and the storey over it are
    the same rectangle with different points along the edges. Comparing raw
    vertex lists calls them different shapes, which is how the commonest overlap
    in Blood -- one room directly over another -- went undetected.
    """
    points = list(loop)
    if len(points) > 2 and points[0] == points[-1]:
        points.pop()
    out: list[tuple[int, int]] = []
    count = len(points)
    for index in range(count):
        prev = points[index - 1]
        here = points[index]
        nxt = points[(index + 1) % count]
        cross = ((here[0] - prev[0]) * (nxt[1] - here[1])
                 - (here[1] - prev[1]) * (nxt[0] - here[0]))
        if cross != 0:
            out.append((int(here[0]), int(here[1])))
    return tuple(out)


def same_ground(loop_a: list[tuple[int, int]], loop_b: list[tuple[int, int]]) -> bool:
    """Do these two outlines enclose the same ground, however they are cut up?

    Corner-for-corner, in either winding, from any starting vertex. This is a
    stricter question than `polygon_relation`'s `exactly_shared_boundary`, which
    a sector filling a *hole* in another also satisfies -- and that is not shared
    ground at all, it is a cut-out.
    """
    a = canonical_ring(loop_a)
    b = canonical_ring(loop_b)
    if len(a) != len(b) or not a:
        return False
    for flip in (b, tuple(reversed(b))):
        for start in range(len(flip)):
            if a == flip[start:] + flip[:start]:
                return True
    return False

