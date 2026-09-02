"""Partition overlays: one thing lying across several sectors.

Build has no way to say "a shadow falls across this road and that pavement".
It has sectors, and a sector has one floor shade. So every element that spans
a boundary has to be cut into pieces, and this project's compiler could only
ever *insert* a region into another where there was room -- which is why
Gravesend's streets are the residue of its districts and its light pools are
carved holes rather than light.

Level design is made of overlapping relationships. An island lies on a street;
a shadow lies across both; a building stands on the island; a facade run
passes a recess. The pieces are an artefact of the file format, not of the
design, so the compiler should produce them rather than the author.

An **overlay** is a set of polygons that splits existing regions into pieces
**without changing ownership, surfaces, frames or behaviour**. Each piece
inherits everything from its parent and differs only in what the overlay says
-- a floor z for a height island, a shade for a shadow. That inheritance is
the contract: a surface keeps its frame across the pieces, so the road's
texture runs on through a shadow edge exactly as if the edge were not there,
which is the property `texture_frame`'s world u-origin was built to give.

Two kinds are implemented here:

* **HEIGHT ISLAND** -- a region standing 2048 above the ground plane it lies
  on. The kerb is not a thing anyone draws: it is the island's edge showing
  above the road, and the exposed band wears the kerb tile on the ROAD-side
  record. Measured on E3M1: tile 6 on 11 of 11 road-side records at a
  road/pavement boundary, with the step exactly 2048 every time.
* **LIGHT** -- a shadow polygon carrying a floor and wall shade. E3M1 cuts
  its road at shadow edges, not at junctions only.

The geometry is exact and deliberately narrow. A cut is a HALF-PLANE, and
splitting a convex polygon by a half-plane gives exactly two convex polygons
with no tolerance anywhere. A rectangle is four cuts. Anything this cannot
resolve -- a concave region, a cut that would leave a sliver -- is refused
loudly, because "insert a sector where there is room" is the idiom being
replaced and silently declining to cut is the same failure wearing a hat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

Point = tuple[int, int]

#: Below this an offcut is not a sector anyone can stand on or see, and
#: emitting it would put a degenerate wall loop in the map. A cut that would
#: produce one is refused rather than rounded away.
MIN_PIECE_AREA = 4096
#: How far off a vertex may be from a cut line and still count as on it.
ON_LINE = 1


class OverlayError(ValueError):
    """An overlay the compiler cannot resolve, said out loud."""


def _cross(o: Point, a: Point, b: Point) -> int:
    return ((a[0] - o[0]) * (b[1] - o[1])) - ((a[1] - o[1]) * (b[0] - o[0]))


def signed_area(polygon: Sequence[Point]) -> float:
    """Twice the signed area; positive is counter-clockwise."""
    total = 0
    for index, point in enumerate(polygon):
        nxt = polygon[(index + 1) % len(polygon)]
        total += point[0] * nxt[1] - nxt[0] * point[1]
    return total / 2.0


def is_convex(polygon: Sequence[Point]) -> bool:
    """Every turn the same way, ignoring collinear vertices."""
    if len(polygon) < 3:
        return False
    seen = 0
    for index in range(len(polygon)):
        a = polygon[index]
        b = polygon[(index + 1) % len(polygon)]
        c = polygon[(index + 2) % len(polygon)]
        turn = _cross(a, b, c)
        if turn == 0:
            continue
        sign = 1 if turn > 0 else -1
        if seen and sign != seen:
            return False
        seen = sign
    return True


@dataclass(frozen=True)
class Cut:
    """A half-plane, as a line through two points.

    `side(point)` is positive to the left of a->b, negative to the right and
    zero on the line, which is the same orientation convention the rest of
    this package uses for wall winding.
    """

    a: Point
    b: Point

    def __post_init__(self) -> None:
        if self.a == self.b:
            raise OverlayError("a cut needs two distinct points")

    def side(self, point: Point) -> int:
        return _cross(self.a, self.b, point)

    @property
    def bearing(self) -> float:
        """Degrees from +x, 0..180. What a shadow edge's angle is measured as."""
        import math

        dx = self.b[0] - self.a[0]
        dy = self.b[1] - self.a[1]
        return math.degrees(math.atan2(dy, dx)) % 180.0


def split_convex(polygon: Sequence[Point], cut: Cut
                 ) -> tuple[list[Point], list[Point]]:
    """Split a convex polygon by a half-plane. Returns (left, right).

    Exact: the intersection of an edge with the cut is computed in rationals
    and rounded once, and a vertex within `ON_LINE` of the line joins both
    pieces rather than being duplicated near it. Either side may come back
    empty, which is how "the cut misses this polygon" is said.
    """
    if not is_convex(polygon):
        raise OverlayError(
            f"split_convex needs a convex polygon; {list(polygon)} turns both "
            f"ways. Split the region first, or state the overlay as several "
            f"convex pieces -- guessing at a concave cut is how the old "
            f"'insert where there is room' idiom got its answers")
    left: list[Point] = []
    right: list[Point] = []
    count = len(polygon)
    for index in range(count):
        here = tuple(polygon[index])
        nxt = tuple(polygon[(index + 1) % count])
        side_here = cut.side(here)
        side_next = cut.side(nxt)
        if abs(side_here) <= ON_LINE:
            left.append(here)
            right.append(here)
        elif side_here > 0:
            left.append(here)
        else:
            right.append(here)
        if abs(side_here) <= ON_LINE or abs(side_next) <= ON_LINE:
            continue
        if (side_here > 0) != (side_next > 0):
            span = side_here - side_next
            x = here[0] + (nxt[0] - here[0]) * side_here / span
            y = here[1] + (nxt[1] - here[1]) * side_here / span
            crossing = (int(round(x)), int(round(y)))
            left.append(crossing)
            right.append(crossing)
    return (_clean(left), _clean(right))


def _clean(polygon: Sequence[Point]) -> list[Point]:
    """Drop repeats and collinear vertices; empty if it has no area."""
    out: list[Point] = []
    for point in polygon:
        if not out or out[-1] != point:
            out.append(tuple(point))
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    if len(out) < 3:
        return []
    kept: list[Point] = []
    for index in range(len(out)):
        a = out[index - 1]
        b = out[index]
        c = out[(index + 1) % len(out)]
        if _cross(a, b, c) != 0:
            kept.append(b)
    if len(kept) < 3:
        return []
    return kept


def clip_to_rect(polygon: Sequence[Point], rect: Sequence[int]
                 ) -> tuple[list[Point], list[list[Point]]]:
    """The part of `polygon` inside `rect`, and the parts outside it.

    Four half-plane cuts in sequence. The inside is one convex piece; the
    outside is up to four, one per cut, and each is convex because a convex
    polygon cut by a line gives two convex pieces.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    #: counter-clockwise, so "inside" is consistently the left side
    edges = (Cut((x0, y0), (x1, y0)), Cut((x1, y0), (x1, y1)),
             Cut((x1, y1), (x0, y1)), Cut((x0, y1), (x0, y0)))
    inside = list(polygon)
    outside: list[list[Point]] = []
    for cut in edges:
        if not inside:
            break
        keep, drop = split_convex(inside, cut)
        inside = keep
        if drop and abs(signed_area(drop)) >= MIN_PIECE_AREA:
            outside.append(drop)
    return inside, outside


@dataclass(frozen=True)
class HeightIsland:
    """A pavement standing on a road, and the kerb that is its own edge.

    `rise` is how far the island stands above the ground plane it lies on --
    2048 on E3M1, every one of its eleven kerbs, without exception. Blood's z
    grows downward, so the island's floor z is the ground's MINUS the rise.

    `kerb_tile` goes on the ROAD-side record of the boundary, which is the
    correction this model is built on: the band that draws is the one facing
    the road, and Gravesend gave it the building's material because the band
    was a hole's edge in a street residue and inherited the house.
    """

    island_id: str
    outline: tuple[Point, ...]
    rise: int = 2048
    kerb_tile: int = 6
    floor_picnum: int = 4

    def floor_z(self, ground_z: int) -> int:
        return int(ground_z) - int(self.rise)


@dataclass(frozen=True)
class ShadowPolygon:
    """One mass's shadow on the ground, as a convex polygon and a shade."""

    shadow_id: str
    outline: tuple[Point, ...]
    floor_shade: int
    wall_shade: int | None = None


@dataclass
class Piece:
    """One offcut: whose it is, what it inherited, what the overlay changed."""

    parent: str
    outline: list[Point]
    inherits: dict[str, Any] = field(default_factory=dict)
    changes: dict[str, Any] = field(default_factory=dict)
    label: str = ""

    @property
    def area(self) -> float:
        return abs(signed_area(self.outline))


def apply_overlay(regions: dict[str, Sequence[Point]],
                  overlay: Sequence[Point], changes: dict[str, Any], *,
                  label: str = "overlay",
                  inherits: dict[str, dict[str, Any]] | None = None
                  ) -> list[Piece]:
    """Cut every region the overlay crosses, and say what each piece is.

    The pieces inside the overlay carry `changes`; the pieces outside carry
    nothing new. Both inherit their parent's everything, which is the part
    that makes this safe: a piece is not a new region, it is the same region
    in two halves, and its surface keeps its frame.
    """
    inherits = inherits or {}
    rect = _bounds(overlay)
    out: list[Piece] = []
    for region_id, outline in sorted(regions.items()):
        parent_inherits = dict(inherits.get(region_id, {}))
        inside, outside = clip_to_rect(outline, rect)
        if not inside:
            continue                      # the overlay misses this region
        if not outside:
            #: wholly covered: one piece, no cut needed
            out.append(Piece(region_id, list(outline), parent_inherits,
                             dict(changes), label))
            continue
        out.append(Piece(region_id, inside, parent_inherits, dict(changes),
                         label))
        for piece in outside:
            out.append(Piece(region_id, piece, parent_inherits, {}, ""))
    return out


def _bounds(polygon: Sequence[Point]) -> tuple[int, int, int, int]:
    xs = [int(p[0]) for p in polygon]
    ys = [int(p[1]) for p in polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def kerb_records(island: HeightIsland, ground_id: str,
                 ground_outline: Sequence[Point]) -> list[dict[str, Any]]:
    """Which records carry the kerb band, and what goes on them.

    One entry per edge of the island that faces the ground plane. The tile
    goes on the ground's side, and the peg is the default -- E3M1's kerb
    records carry no `kWallOrgBottom`, so the band hangs from the ceiling the
    way every other two-sided wall does.
    """
    out = []
    outline = list(island.outline)
    for index, here in enumerate(outline):
        there = outline[(index + 1) % len(outline)]
        out.append({
            "island": island.island_id,
            "ground": ground_id,
            "edge": (tuple(here), tuple(there)),
            "side": "ground",
            "picnum": int(island.kerb_tile),
            "band": int(island.rise),
            "why": ("E3M1: tile 6 on 11 of 11 road-side records at a "
                    "road/pavement boundary, step 2048 every time"),
        })
    return out
