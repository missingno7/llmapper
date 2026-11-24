"""A place drawn as shapes laid over one another, resolved into regions that meet edge to edge.

A rotunda is a circle, with a smaller circle on it, with a star on that, with a
pit in the middle of the star. Written as regions it is forty outlines whose
corners must all agree: where a line of the star crosses a ring, the ring, the
line and whatever lies inside both need a vertex on the same whole unit, and
each pair of neighbours a connection along the edge they share. Writing that by
hand is why the city's round places were one octagon with sprites in it.

Here the author says only what lies over what. Each `add` lays a named shape on
top of everything before it; `solid` lays a piece of rock. `resolve` cuts the
lot into cells whose corners are whole units and whose edges are shared exactly
(GEOS's snap-rounding noder does the arithmetic, so a crossing that falls
between two units is moved once, for everybody), and `lay` writes them to a
`PlanarLayout` with every joint connected and painted.

The compositions this is for, and how often Blood builds them, are the
catalogue's (`python -m tools.mine_compositions find nest`).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

Point = tuple[int, int]
#: a cell smaller than this, in square units, is what rounding left and goes to its longest neighbour
CRUMB = 4096
SOLID = None


# ---- shapes -----------------------------------------------------------------

def spoke(centre: Point, radius: float, turn: float) -> Point:
    """The point at a radius and a turn (0 is north, up the page; a whole circle is 1; clockwise)."""
    angle = 2 * math.pi * turn
    return round(centre[0] + radius * math.sin(angle)), round(centre[1] - radius * math.cos(angle))


def circle(centre: Point, radius: float, sides: int, turn: float = 0.0) -> list[Point]:
    """A regular polygon with a corner at `turn`, clockwise on the page as Build winds an outline."""
    return [spoke(centre, radius, turn + k / sides) for k in range(sides)]


def arc(centre: Point, inner: float, outer: float, first: int, last: int, sides: int,
        turn: float = 0.0) -> list[Point]:
    """A stretch of the ring between two circles, from corner `first` to corner `last` of `sides`."""
    if last <= first:
        last += sides
    far = [spoke(centre, outer, turn + k / sides) for k in range(first, last + 1)]
    near = [spoke(centre, inner, turn + k / sides) for k in range(last, first - 1, -1)]
    return far + near


def band(a: Point, b: Point, width: float) -> list[Point]:
    """A straight strip of a width from one point to another, square at its ends."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1
    ox, oy = -dy / length * width / 2, dx / length * width / 2
    return [(round(a[0] - ox), round(a[1] - oy)), (round(b[0] - ox), round(b[1] - oy)),
            (round(b[0] + ox), round(b[1] + oy)), (round(a[0] + ox), round(a[1] + oy))]


def star(centre: Point, radius: float, points: int, step: int, width: float, turn: float = 0.0) -> list[list[Point]]:
    """The strips of a star polygon: {5, 2} is the pentagram, {6, 2} the hexagram."""
    corners = circle(centre, radius, points, turn)
    return [band(corners[k], corners[(k + step) % points], width) for k in range(points)]


# ---- the arrangement --------------------------------------------------------

@dataclass(frozen=True)
class Cell:
    """One region's outline: clockwise on the page, its holes the other way."""
    name: str
    outer: tuple[Point, ...]
    holes: tuple[tuple[Point, ...], ...] = ()


@dataclass(frozen=True)
class Joint:
    """A straight edge two cells share, as the first of them walks it."""
    left: str
    right: str
    a: Point
    b: Point


@dataclass
class Arrangement:
    """Shapes in the order they are laid; a later one covers what is under it."""

    shapes: list[tuple[str | None, Any]] = field(default_factory=list)

    def add(self, name: str, *rings: Sequence[Point], holes: Iterable[Sequence[Point]] = ()) -> "Arrangement":
        """Lay one shape, the union of its rings less its holes."""
        from shapely import Polygon, unary_union
        shape = unary_union([Polygon(r).buffer(0) for r in rings])
        for hole in holes:
            shape = shape.difference(Polygon(hole))
        self.shapes.append((name, shape))
        return self

    def solid(self, *rings: Sequence[Point]) -> "Arrangement":
        """Lay rock: no region, and walls round it."""
        self.add("", *rings)
        self.shapes[-1] = (SOLID, self.shapes[-1][1])
        return self

    def resolve(self) -> list[Cell]:
        """The cells, on whole units, meeting exactly. One name laid in two places gives name_0, name_1."""
        from shapely import Point as GeosPoint, polygonize, get_parts, unary_union

        outlines = []
        for _name, shape in self.shapes:
            for part in get_parts(shape):
                outlines += [part.exterior, *part.interiors]
        noded = unary_union(outlines, grid_size=1)
        faces = [f for f in get_parts(polygonize([line for line in get_parts(noded)]))]

        def owner(face):
            at = face.representative_point()
            for name, shape in reversed(self.shapes):
                if shape.covers(GeosPoint(at)):
                    return name, True
            return None, False

        owned: dict[str, list] = defaultdict(list)
        crumbs = []
        for face in faces:
            name, inside = owner(face)
            if not inside or name is SOLID:
                continue
            (crumbs if face.area < CRUMB else owned[name]).append(face)
        for crumb in crumbs:
            near = max(((face.boundary.intersection(crumb.boundary).length, name, k)
                        for name, group in owned.items() for k, face in enumerate(group)), default=None)
            if near and near[0] > 0:
                owned[near[1]].append(crumb)

        cells: list[Cell] = []
        for name, group in owned.items():
            parts = sorted(get_parts(unary_union(group, grid_size=1)), key=lambda p: p.bounds)
            for k, part in enumerate(parts):
                label = name if len(parts) == 1 else f"{name}_{k}"
                cells.append(Cell(label, _ring(part.exterior.coords, True),
                                  tuple(_ring(h.coords, False) for h in part.interiors)))
        return _straighten(cells)


def _ring(coords, clockwise: bool) -> tuple[Point, ...]:
    ring = [(round(x), round(y)) for x, y in coords][:-1]
    area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(ring, ring[1:] + ring[:1]))
    if (area > 0) != clockwise:
        ring.reverse()
    start = ring.index(min(ring))
    return tuple(ring[start:] + ring[:start])


def _straighten(cells: list[Cell]) -> list[Cell]:
    """Drop a corner that is on a straight edge in every ring that has it, and where no third edge meets."""
    ends = defaultdict(set)
    for cell in cells:
        for ring in (cell.outer, *cell.holes):
            for p, q in zip(ring, ring[1:] + ring[:1]):
                ends[p].add(q)
                ends[q].add(p)
    idle = set()
    for p, others in ends.items():
        if len(others) == 2:
            (ax, ay), (bx, by) = others
            if (ax - p[0]) * (by - p[1]) == (ay - p[1]) * (bx - p[0]):
                idle.add(p)
    keep = lambda ring: tuple(p for p in ring if p not in idle)
    return [Cell(c.name, keep(c.outer), tuple(keep(h) for h in c.holes)) for c in cells]


def joints(cells: list[Cell]) -> list[Joint]:
    """Every edge two cells share."""
    walked = {}
    for cell in cells:
        for ring in (cell.outer, *cell.holes):
            for p, q in zip(ring, ring[1:] + ring[:1]):
                walked[p, q] = cell.name
    return [Joint(name, walked[q, p], p, q) for (p, q), name in walked.items()
            if (q, p) in walked and (walked[q, p], q, p) > (name, p, q)]


def rim(cells: list[Cell]) -> list[tuple[str, Point, Point]]:
    """Every edge with a cell on one side only: the place's walls, as (cell, a, b)."""
    walked = {}
    for cell in cells:
        for ring in (cell.outer, *cell.holes):
            for p, q in zip(ring, ring[1:] + ring[:1]):
                walked[p, q] = cell.name
    return [(name, p, q) for (p, q), name in walked.items() if (q, p) not in walked]


def lay(layout, key: str, cells: list[Cell], surface: Callable[[str], dict[str, Any]],
        face: Callable[[str, str | None, Point, Point], dict[str, Any]] = lambda *_: {},
        joint: Callable[[str, str, Point, Point], dict[str, Any]] = lambda *_: {}) -> dict[str, str]:
    """Write the cells to a layout and return {cell name: region id}.

    `surface(cell)` is what `add_region` is given for it. `face(seen, beyond,
    a, b)` is the paint of one wall record: what a cell shows along an edge,
    with rock beyond (None) or another cell. `joint(left, right, a, b)` adds
    to the connection (a role, a gate).
    """
    regions = {}
    for cell in cells:
        regions[cell.name] = layout.add_region(f"{key}:{cell.name}", cell.outer, holes=cell.holes, **surface(cell.name))
    for index, j in enumerate(sorted(joints(cells), key=lambda j: (j.left, j.right, j.a))):
        layout.add_connection(f"{regions[j.left]}|{regions[j.right]}:{index}", regions[j.left], regions[j.right],
                              a1=j.a, a2=j.b, **{"min_width": 1, "min_opening": 0, **joint(j.left, j.right, j.a, j.b)})
        for seen, beyond in ((j.left, j.right), (j.right, j.left)):
            paint = face(seen, beyond, j.a, j.b)
            if paint:
                layout.paint_wall(regions[seen], j.a, j.b, fixed_frame="x_repeat" in paint, **paint)
    for name, a, b in rim(cells):
        paint = face(name, None, a, b)
        if paint:
            layout.paint_wall(regions[name], a, b, fixed_frame="x_repeat" in paint, **paint)
    return regions
