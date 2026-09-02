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


# ---------------------------------------------------------------------------
# a ground plane is one region, and a junction is a place on it
# ---------------------------------------------------------------------------

def ground_plane(strips: Sequence[Sequence[int]]) -> list[Point]:
    """The outline of a street network: the union boundary of its strips.

    **A junction is not a thing to declare.** It is where two strips of the
    same plane meet, and it has no exits of its own -- which is exactly why
    emitting junction squares as separate regions produced three
    `zero_exit_gameplay_sector` refusals: a square whose every neighbour was a
    road piece at the same z still had nothing the compiler would call a way
    out, because it had been authored as a room rather than as part of the
    floor it is part of.

    So the plane is emitted WHOLE, concave outline and all -- Build sectors
    may be concave and `PlanarLayout` accepts one -- and the pieces come from
    cuts. The kerb is then the boundary between the plane and an island lying
    on it, and the junction is simply the part of the plane no island covers.

    Traced by walking the union's boundary on the grid the strips imply, so
    the result is exact and needs no polygon library.
    """
    if not strips:
        raise OverlayError("a ground plane with no strips is not a plane")
    xs = sorted({int(v) for strip in strips for v in (strip[0], strip[2])})
    ys = sorted({int(v) for strip in strips for v in (strip[1], strip[3])})
    filled = set()
    for column in range(len(xs) - 1):
        for row in range(len(ys) - 1):
            cx = (xs[column] + xs[column + 1]) // 2
            cy = (ys[row] + ys[row + 1]) // 2
            if any(min(s[0], s[2]) <= cx <= max(s[0], s[2])
                   and min(s[1], s[3]) <= cy <= max(s[1], s[3])
                   for s in strips):
                filled.add((column, row))
    if not filled:
        raise OverlayError("the strips cover nothing")
    rings = _trace(filled, xs, ys)
    if len(rings) > 1:
        raise OverlayError(
            f"this plane has {len(rings) - 1} hole(s) -- the blocks its roads "
            f"enclose. Call `ground_plane_rings` for the whole polygon; one "
            f"ring would lose them")
    return rings[0]


def _trace(filled: set, xs, ys) -> list:
    """Walk the boundary of a set of grid cells: EVERY ring, outer first.

    A street lattice does not have one boundary. It has an outer ring and one
    hole per block its roads enclose -- the islands stand in those holes -- so
    returning a single ring loses most of the map, and reporting the extra
    rings as "disconnected" is worse: the first version did exactly that and
    refused Gravesend's own grid, 28 boundary vertices of 64.

    Connectivity is a question about the CELLS, answered by flooding them, and
    not about how many rings the boundary has.
    """
    edges = {}
    for column, row in filled:
        if (column, row - 1) not in filled:
            edges[(column, row)] = (column + 1, row)
        if (column + 1, row) not in filled:
            edges[(column + 1, row)] = (column + 1, row + 1)
        if (column, row + 1) not in filled:
            edges[(column + 1, row + 1)] = (column, row + 1)
        if (column - 1, row) not in filled:
            edges[(column, row + 1)] = (column, row)
    if not edges:
        raise OverlayError("the strips have no boundary")

    seed = next(iter(filled))
    seen = {seed}
    stack = [seed]
    while stack:
        column, row = stack.pop()
        for step in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (column + step[0], row + step[1])
            if nxt in filled and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    if seen != filled:
        raise OverlayError(
            f"the strips do not form one connected plane: {len(seen)} of "
            f"{len(filled)} cells are reachable from the first. Emit one "
            f"ground plane per connected network, as the model says")

    rings = []
    unused = dict(edges)
    while unused:
        first = next(iter(unused))
        ring = [first]
        node = unused.pop(first)
        while node != first:
            if node not in unused:
                raise OverlayError("the boundary walk did not close")
            ring.append(node)
            node = unused.pop(node)
        points = _clean([(xs[column], ys[row]) for column, row in ring])
        if points:
            rings.append(points)
    if not rings:
        raise OverlayError("the strips have no boundary")
    rings.sort(key=lambda r: -abs(signed_area(r)))
    return rings


def ground_plane_rings(strips, holes: Sequence[Sequence[int]] = ()) -> list:
    """The whole plane: its outer ring, then one hole per enclosed block.

    A street grid encloses its blocks, so the plane is a polygon WITH HOLES
    and the islands stand in them. `split_polygon` pairs chords over all rings
    at once, so nothing downstream needs a special case for them.

    `holes` are rectangles the strips cover and the plane does NOT: a plaza
    standing in a street, an end wall blocking a street's mouth, a cemetery
    let into the kerb line. The nine blocks a lattice encloses are holes
    already, by not being covered; these are the ones that have to be said,
    because their street runs through them. Both kinds come out of `_trace`
    identically, which is the point -- an island is an island however it came
    to be one.
    """
    rects = list(strips) + list(holes)
    xs = sorted({int(v) for strip in rects for v in (strip[0], strip[2])})
    ys = sorted({int(v) for strip in rects for v in (strip[1], strip[3])})

    def covers(rect, cx, cy):
        return (min(rect[0], rect[2]) <= cx <= max(rect[0], rect[2])
                and min(rect[1], rect[3]) <= cy <= max(rect[1], rect[3]))

    filled = set()
    for column in range(len(xs) - 1):
        for row in range(len(ys) - 1):
            cx = (xs[column] + xs[column + 1]) // 2
            cy = (ys[row] + ys[row + 1]) // 2
            if any(covers(s, cx, cy) for s in strips) and not any(
                    covers(h, cx, cy) for h in holes):
                filled.add((column, row))
    if not filled:
        raise OverlayError("the strips cover nothing")
    return _trace(filled, xs, ys)


# ---------------------------------------------------------------------------
# what an overlay may touch
# ---------------------------------------------------------------------------

#: A wall that a mechanism drags: cutting the sector it belongs to changes the
#: `DragPoint` closure, which is P3's whole subject.
MOVING_WALL_FLAGS = 0x4000 | 0x8000
#: Sector types 600..619 move. A region carrying one is a mechanism.
MOVING_TYPES = frozenset(range(600, 620))
#: `floor_picnum` 504 marks a stack; a path sector carries markers.
STACK_TILE = 504

#: The surface kinds the sun may fall on: outdoor ground. Interiors are lit by
#: LightBomb from their own declared sources and by their own interior
#: overlays (a window's pool is one), never by the sun.
LIGHT_SURFACES = frozenset({"ground", "island", "plaza", "shore", "roof",
                            "street"})


class DomainError(OverlayError):
    """An overlay asked to cut something it may not."""


@dataclass(frozen=True)
class Domain:
    """Which regions an overlay may cut, and why the rest are excluded.

    Rule 1: every overlay declares this. Rule 2 is folded in and is not
    negotiable per overlay -- a region carrying a sector type, a moving wall,
    a stack marker, a holder role or an insert is excluded from EVERY overlay,
    because cutting a mover changes its `DragPoint` closure, cutting a holder
    breaks the one-record-one-frame law, and cutting a curtain fin changes
    what its motion set is.

    An out-of-domain crossing is **not an error**. The shadow simply does not
    apply there and the manifest says so, because a shadow falling on a house
    is a fact about the world and refusing the build over it would be absurd.
    """

    name: str
    surfaces: frozenset = LIGHT_SURFACES
    #: `None` means "any region"; used by HEIGHT ISLAND, which names its own.
    only: tuple[str, ...] | None = None
    needs_sky: bool = True

    def admits(self, region_id: str, info: dict[str, Any]) -> tuple[bool, str]:
        """May this overlay cut that region? Second value is the reason."""
        if self.only is not None and region_id not in self.only:
            return False, f"{self.name} applies only to {self.only}"
        for flag, why in (
                ("has_sector_type", "it is a mechanism (a sector type)"),
                ("has_moving_wall", "a wall of it moves (cstat 0x4000/0x8000)"),
                ("has_stack_marker", "it carries a stack or path marker"),
                ("is_holder", "it is a holder (one record, one frame)"),
                ("is_insert", "it is an insert")):
            if info.get(flag):
                return False, f"excluded from every overlay: {why}"
        if self.needs_sky and not info.get("under_sky"):
            return False, "it is not under a parallax sky ceiling"
        role = info.get("role")
        if self.surfaces and role is not None and role not in self.surfaces:
            return False, f"its role {role!r} is not a {self.name} surface"
        return True, ""


LIGHT_DOMAIN = Domain("light")


def region_facts(level: Any, sector_id: int,
                 owners: Sequence[int] | None = None) -> dict[str, Any]:
    """What a domain needs to know about one region, read off the map."""
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(level)
    fields = _fields_of(level.sectors[sector_id])
    start = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    moving = False
    insert = False
    for wall in range(start, start + count):
        face = _fields_of(level.walls[wall])
        if int(face["cstat"]) & MOVING_WALL_FLAGS:
            moving = True
        if int(face.get("over_picnum", 0)) and int(face["cstat"]) & 16:
            insert = True
    return {
        "under_sky": bool(int(fields["ceiling_stat"]) & 1),
        "has_sector_type": int(fields["type"]) in MOVING_TYPES,
        "has_moving_wall": moving,
        "has_stack_marker": int(fields["floor_picnum"]) == STACK_TILE
                            or int(fields["ceiling_picnum"]) == STACK_TILE,
        "is_insert": insert,
        "is_holder": False,
        "role": "street",
    }


def _fields_of(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def in_domain(level: Any, domain: Domain, regions: Iterable[int],
              owners: Sequence[int] | None = None
              ) -> tuple[list[int], list[dict[str, Any]]]:
    """Split candidate regions into the ones this overlay may cut and the rest.

    The excluded list is the manifest entry: every region a shadow crossed and
    did not cut, with the reason, so an owner reading the build can see that
    the sun stopped at the front door on purpose.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(level)
    allowed: list[int] = []
    refused: list[dict[str, Any]] = []
    for sector_id in regions:
        facts = region_facts(level, sector_id, owners)
        ok, why = domain.admits(str(sector_id), facts)
        if ok:
            allowed.append(sector_id)
        else:
            refused.append({"region": sector_id, "reason": why})
    return allowed, refused


#: Rule 2's five: the facts that exclude a region from EVERY overlay. A
#: region carrying none of them could never have been refused, so counting it
#: in a refusal statistic is counting the population that was never at risk.
REFUSAL_FLAGS = ("has_sector_type", "has_moving_wall", "has_stack_marker",
                 "is_holder", "is_insert")


def refusal_denominator(level: Any, domain: Domain, regions: Iterable[int],
                        owners: Sequence[int] | None = None) -> dict:
    """How many regions COULD have been refused, beside how many were.

    "The light domain refuses 0" is a green line and an empty one when
    nothing in the map was ever a candidate. A rate needs its denominator:
    a mechanism, an insert or a holder is eligible for refusal, and a plain
    piece of road is not. **Zero refused out of zero eligible is UNTESTED,
    never green** -- the difference between a rule that held and a rule that
    was never asked.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(level)
    eligible: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    admitted = 0
    for sector_id in regions:
        facts = region_facts(level, sector_id, owners)
        why = [flag for flag in REFUSAL_FLAGS if facts.get(flag)]
        if why:
            eligible.append({"region": sector_id, "flags": why})
        ok, reason = domain.admits(str(sector_id), facts)
        if ok:
            admitted += 1
        else:
            refused.append({"region": sector_id, "reason": reason})
    return {
        "domain": domain.name,
        "admitted": admitted,
        "refused": len(refused),
        "eligible": len(eligible),
        "eligible_regions": eligible,
        "refused_regions": refused,
        "verdict": "untested" if not eligible else "tested",
    }


def refusal_line(result: dict) -> str:
    """The manifest line, with the denominator beside the numerator."""
    verdict = ("UNTESTED: nothing in this map is a mechanism, an insert or a "
               "holder, so the rule was never asked"
               if result["verdict"] == "untested" else "tested")
    return (f"{result['domain']} domain: admits {result['admitted']}, "
            f"refuses {result['refused']} of {result['eligible']} eligible "
            f"(mechanisms, inserts, holders) -- {verdict}")


# ---------------------------------------------------------------------------
# the clipper: a half-plane through a polygon with holes
# ---------------------------------------------------------------------------

#: How far apart two points may be and still be the same point after the
#: intersections have been rounded to Build's integer grid.
WELD = 2


def _side(cut: "Cut", point: Point) -> int:
    value = cut.side(point)
    return 0 if abs(value) <= ON_LINE else (1 if value > 0 else -1)


def _param(cut: "Cut", point: Point) -> int:
    """Where a point sits along the cut line. Only the ORDER matters."""
    dx, dy = cut.b[0] - cut.a[0], cut.b[1] - cut.a[1]
    return (point[0] - cut.a[0]) * dx + (point[1] - cut.a[1]) * dy


def _crossing(cut: "Cut", here: Point, nxt: Point) -> Point:
    """Where an edge meets the cut, rounded the same way from either end.

    The endpoints are put in canonical order first. Without that,
    interpolating from `here` and interpolating from `nxt` round to different
    integers on an oblique edge -- and the SAME edge is given in one direction
    by the plane's hole ring and in the other by the island's outer ring, so
    the two would disagree about where they meet and the weld would have
    nothing to match.
    """
    here, nxt = tuple(here), tuple(nxt)
    if (nxt[0], nxt[1]) < (here[0], here[1]):
        here, nxt = nxt, here
    sh, sn = cut.side(here), cut.side(nxt)
    span = sh - sn
    x = here[0] + (nxt[0] - here[0]) * sh / span
    y = here[1] + (nxt[1] - here[1]) * sh / span
    return (int(round(x)), int(round(y)))


def edge_key(a: Point, b: Point) -> tuple:
    """The undirected identity of an edge: the same whichever way it is given.

    The weld's registry key. A plane's hole ring runs one way round a block
    and the island's outer ring runs the other, so the two describe the same
    edges in opposite directions; keyed undirected, a crossing recorded from
    one is found by the other.
    """
    a, b = (int(a[0]), int(a[1])), (int(b[0]), int(b[1]))
    return (a, b) if a <= b else (b, a)


def normalise(rings: Sequence[Sequence[Point]]) -> list[list[Point]]:
    """Outer ring counter-clockwise, holes clockwise."""
    out = []
    for index, ring in enumerate(rings):
        cleaned = _clean(list(ring))
        if not cleaned:
            continue
        want_ccw = index == 0
        if (signed_area(cleaned) > 0) != want_ccw:
            cleaned.reverse()
        out.append(cleaned)
    return out


def split_polygon(rings: Sequence[Sequence[Point]], cut: "Cut",
                  registry: dict | None = None
                  ) -> tuple[list[list[list[Point]]], list[list[list[Point]]]]:
    """Cut a polygon WITH HOLES by a half-plane. Returns (left, right).

    Each side is a list of regions and each region is a list of rings, outer
    first. This is the piece `split_convex` could not be: the ground plane is
    a lattice with the islands as its holes, and refusing to cut it -- which
    `split_convex` does, correctly, rather than guess -- is what stopped
    slice 2b.

    The method is even-odd chord pairing over ALL rings at once. Every ring is
    augmented with its crossings, the edges on one side are kept with their
    original direction, and the gaps are closed by chords along the cut line:
    sort the on-line points by their parameter, pair them consecutively, and
    each pair spans a stretch of the line that lies inside the polygon. Holes
    need no special case, which is the whole reason to pair over all rings
    together rather than ring by ring.
    """
    rings = normalise(rings)
    if not rings:
        return [], []
    #: WHICH POINTS ARE ON THE LINE IS RECORDED, NOT RE-DERIVED.
    #:
    #: A crossing is computed in rationals and rounded to Build's integer
    #: grid, and the rounded point is then routinely more than `ON_LINE` off
    #: the line it was cut on -- the cross product magnifies half a unit of
    #: rounding by the segment's length. Asking `_side` about it afterwards
    #: answers "not on the line", so the chord is never built, the chain
    #: dangles and BOTH sides come back empty. Axis-aligned cuts and a
    #: 45-degree one land exactly on integers, which is why the first round of
    #: tests passed and the sun's 84 degrees did not.
    crossings = set()
    for ring in rings:
        count = len(ring)
        for index in range(count):
            here = tuple(ring[index])
            nxt = tuple(ring[(index + 1) % count])
            if _side(cut, here) and _side(cut, nxt) and                     _side(cut, here) != _side(cut, nxt):
                point = _crossing(cut, here, nxt)
                crossings.add(point)
                if registry is not None:
                    registry.record(here, nxt, point)
                    #: the edge is being cut here, so its two halves descend
                    #: from it -- a later cut recording against a half must
                    #: still reach a neighbour that carries the whole
                    registry.split(here, nxt, point)

    def _on(point):
        return point in crossings or _side(cut, point) == 0

    #: A VERTEX ON THE LINE IS NOT ALWAYS A CROSSING. Where a ring merely
    #: TOUCHES the cut -- both its neighbours on the same side -- the polygon
    #: does not pass through, and pairing it as a chord endpoint makes the
    #: count odd and hands a chord to the wrong partner. That is not a corner
    #: case here: a shell's shadow is cast FROM its own footprint, and the
    #: footprint is the hole it stands in, so every shadow edge begins exactly
    #: on a hole vertex. On five of the city's islands it lost between 14 and
    #: 21 million square units, silently, and the pieces still looked like
    #: pieces.
    touches = set()
    for ring in rings:
        count = len(ring)
        sides = [_side(cut, tuple(point)) for point in ring]
        for index, point in enumerate(ring):
            if sides[index] != 0:
                continue
            before = next((sides[(index - step) % count]
                           for step in range(1, count)
                           if sides[(index - step) % count] != 0), 0)
            after = next((sides[(index + step) % count]
                          for step in range(1, count)
                          if sides[(index + step) % count] != 0), 0)
            if before and after and before == after:
                touches.add(tuple(point))

    out = []
    for want in (1, -1):
        edges = {}
        on_line = set()
        for ring in rings:
            augmented = []
            count = len(ring)
            for index in range(count):
                here = tuple(ring[index])
                nxt = tuple(ring[(index + 1) % count])
                augmented.append(here)
                if _side(cut, here) and _side(cut, nxt) and                         _side(cut, here) != _side(cut, nxt):
                    augmented.append(_crossing(cut, here, nxt))
            total = len(augmented)
            for index in range(total):
                here = augmented[index]
                nxt = augmented[(index + 1) % total]
                if here == nxt:
                    continue
                sh = 0 if _on(here) else _side(cut, here)
                sn = 0 if _on(nxt) else _side(cut, nxt)
                keep = (sh == want or sn == want or (sh == 0 and sn == 0))
                if sh == -want or sn == -want:
                    keep = False
                if not keep:
                    if sh == 0 and here not in touches:
                        on_line.add(here)
                    if sn == 0 and nxt not in touches:
                        on_line.add(nxt)
                    continue
                edges[here] = nxt
                if sh == 0 and here not in touches:
                    on_line.add(here)
                if sn == 0 and nxt not in touches:
                    on_line.add(nxt)
        #: close the gaps along the line
        needs_out = sorted((p for p in on_line if p not in edges),
                           key=lambda p: _param(cut, p))
        incoming = set(edges.values())
        needs_in = sorted((p for p in on_line if p not in incoming),
                          key=lambda p: _param(cut, p))
        ordered = sorted(set(needs_out) | set(needs_in),
                         key=lambda p: _param(cut, p))
        for first, second in zip(ordered[0::2], ordered[1::2]):
            if first in needs_out and second in needs_in:
                edges[first] = second
            elif second in needs_out and first in needs_in:
                edges[second] = first
        out.append(_loops(edges))
    return (_as_regions(out[0]), _as_regions(out[1]))


def _loops(edges: dict[Point, Point]) -> list[list[Point]]:
    """Trace every closed loop in a set of directed edges."""
    out = []
    unused = dict(edges)
    while unused:
        start = next(iter(unused))
        loop = [start]
        node = unused.pop(start)
        guard = 0
        while node != start:
            if node not in unused or guard > 100000:
                loop = []
                break
            loop.append(node)
            node = unused.pop(node)
            guard += 1
        cleaned = _clean(loop) if loop else []
        if cleaned:
            out.append(cleaned)
    return out


def _as_regions(loops: Sequence[Sequence[Point]]) -> list[list[list[Point]]]:
    """Group loops into regions: a positive loop and the loops inside it."""
    outers = [list(loop) for loop in loops if signed_area(loop) > 0]
    holes = [list(loop) for loop in loops if signed_area(loop) < 0]
    if not outers:
        return []
    regions = [[outer] for outer in outers]
    for hole in holes:
        point = hole[0]
        for region in regions:
            if _inside(region[0], point):
                region.append(hole)
                break
    return regions


def _inside(ring: Sequence[Point], point: Point) -> bool:
    inside = False
    count = len(ring)
    for index in range(count):
        a = ring[index]
        b = ring[(index + 1) % count]
        if (a[1] > point[1]) != (b[1] > point[1]):
            x = a[0] + (point[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1] or 1)
            if point[0] < x:
                inside = not inside
    return inside


def region_area(region: Sequence[Sequence[Point]]) -> float:
    """Outer ring less its holes."""
    if not region:
        return 0.0
    return abs(signed_area(region[0])) - sum(
        abs(signed_area(ring)) for ring in region[1:])


def cut_region(rings: Sequence[Sequence[Point]], cut: "Cut", *,
               min_area: int = MIN_PIECE_AREA, registry: dict | None = None
               ) -> tuple[list, list, list[dict[str, Any]]]:
    """One half-plane cut, with slivers absorbed rather than refused.

    A cut that would leave a scrap does not cut: the chord is snapped to the
    nearest vertex, which for a half-plane means the whole polygon stays on
    the side it is mostly on. Deterministic, and REPORTED -- an absorbed
    sliver is a fact the manifest carries, not a silent rounding.

    An oblique shadow clipping the corner off a junction leaves a triangle 43
    units across; emitting it puts a degenerate loop in the map and the
    compiler then finds coincident wall segments nobody declared.
    """
    left, right = split_polygon(rings, cut, registry)
    absorbed: list[dict[str, Any]] = []
    left_area = sum(region_area(region) for region in left)
    right_area = sum(region_area(region) for region in right)
    #: AN EMPTY SIDE IS NOT AN ABSORBED SLIVER. A cut that misses the polygon
    #: entirely leaves one side empty, and the first version reported that as
    #: a sliver of area 0 -- so the counts a build printed were mostly
    #: phantom, and a real absorption could not be seen among them.
    #: ABSORBED MEANS THE NEIGHBOUR KEEPS IT. Returning the CUT piece here
    #: discards the scrap and loses its area -- a 536-unit scrap went missing
    #: that way on a 419-million rectangle, and the partition assertion found
    #: it the moment the weld had removed the overlap that was masking it.
    #: The polygon goes back whole on the side it is mostly on, which is what
    #: "snap the chord to the nearest vertex" means.
    whole = [list(ring) for ring in normalise(rings)]
    if left and right and right_area < min_area:
        absorbed.append({"side": "right", "area": right_area,
                         "why": f"under {min_area}, absorbed into the left"})
        return [whole], [], absorbed
    if right and left and left_area < min_area:
        absorbed.append({"side": "left", "area": left_area,
                         "why": f"under {min_area}, absorbed into the right"})
        return [], [whole], absorbed
    keep_left = [r for r in left if region_area(r) >= min_area]
    keep_right = [r for r in right if region_area(r) >= min_area]
    for dropped, side in ((set(map(id, left)) - set(map(id, keep_left)), "left"),
                          (set(map(id, right)) - set(map(id, keep_right)),
                           "right")):
        for _ in dropped:
            absorbed.append({"side": side, "area": None,
                             "why": f"piece under {min_area}, absorbed"})
    return keep_left, keep_right, absorbed


def cut_by_convex(rings: Sequence[Sequence[Point]],
                  shadow: Sequence[Point], *,
                  min_area: int = MIN_PIECE_AREA, registry: dict | None = None
                  ) -> tuple[list, list, list[dict[str, Any]]]:
    """A convex shadow, as a sequence of half-plane cuts. (inside, outside).

    Applied only to the pieces still overlapping the shadow, never to the
    whole plane, and the OUTSIDE pieces are kept apart so a caller can merge
    them back. A shadow adds exactly its own boundary that way; cutting the
    whole plane with every edge's line would run each shadow line to the map's
    edge and the sector count would explode.
    """
    if len(shadow) < 3:
        raise OverlayError("a shadow needs three corners")
    #: "Inside" is the left of every edge, which is only true of a polygon
    #: wound counter-clockwise. A clockwise shadow gives inside = nothing and
    #: outside = everything -- the cut silently does nothing at all -- so the
    #: orientation is normalised here rather than trusted from the caller.
    shadow = list(shadow)
    if signed_area(shadow) < 0:
        shadow.reverse()
    inside = [list(rings)]
    outside: list = []
    absorbed: list[dict[str, Any]] = []
    count = len(shadow)
    for index in range(count):
        a = tuple(shadow[index])
        b = tuple(shadow[(index + 1) % count])
        if a == b:
            continue
        cut = Cut(a, b)
        nxt = []
        for region in inside:
            keep, drop, notes = cut_region(region, cut, min_area=min_area,
                                           registry=registry)
            absorbed.extend(notes)
            nxt.extend(keep)
            outside.extend(drop)
        inside = nxt
        if not inside:
            break
    return inside, outside, absorbed


# ---------------------------------------------------------------------------
# the assertion the clipper's tests were missing
# ---------------------------------------------------------------------------

def _point_in(rings: Sequence[Sequence[Point]], point: Point) -> bool:
    """Is a point inside a polygon with holes? Even-odd over every ring."""
    inside = False
    for ring in rings:
        count = len(ring)
        for index in range(count):
            a = ring[index]
            b = ring[(index + 1) % count]
            if (a[1] > point[1]) != (b[1] > point[1]):
                span = (b[1] - a[1]) or 1
                x = a[0] + (point[1] - a[1]) * (b[0] - a[0]) / span
                if point[0] < x:
                    inside = not inside
    return inside


def _on_boundary(rings: Sequence[Sequence[Point]], point: Point) -> bool:
    """Does the point lie on any edge of any ring?"""
    px, py = point
    for ring in rings:
        count = len(ring)
        for index in range(count):
            ax, ay = ring[index]
            bx, by = ring[(index + 1) % count]
            if (bx - ax) * (py - ay) - (by - ay) * (px - ax) != 0:
                continue                       # not collinear
            if min(ax, bx) <= px <= max(ax, bx) and                     min(ay, by) <= py <= max(ay, by):
                return True
    return False


def partition_faults(pieces: Sequence[Sequence[Sequence[Point]]],
                     whole: Sequence[Sequence[Point]], *,
                     samples: int = 400, tolerance: float = 1.0
                     ) -> list[str]:
    """Do these pieces partition `whole`? Three questions, not one.

    The clipper's tests asserted area conservation and nothing else, and area
    conservation is **not** partition: ``sum(pieces) == whole`` is satisfied
    by a genuine partition AND by a set that double-counts one region while
    losing another of the same size. That is the same shape of gap as the 8x
    texture regression, one level down, and it is why the whole-graph build
    could fail on overlapping pieces with every clipper test green.

    So: the area, then no two interiors overlapping, then every sampled point
    of the whole claimed exactly once.
    """
    out: list[str] = []
    want = region_area(whole)
    got = sum(region_area(piece) for piece in pieces)
    if abs(got - want) > tolerance:
        out.append(f"area {got} against {want}, off by {got - want}")

    for index, piece in enumerate(pieces):
        for other_index in range(index + 1, len(pieces)):
            other = pieces[other_index]
            for vertex in piece[0]:
                #: STRICTLY inside, which means not on the boundary. Two
                #: pieces of a partition share edges everywhere, and a point
                #: on a shared edge tests as "inside" or "outside" depending
                #: on which way the ray happens to go -- so a boundary test
                #: has to come first or the assertion reports a partition as
                #: an overlap, which is what it did on its first run.
                if _on_boundary(other, vertex):
                    continue
                if _point_in(other, vertex):
                    out.append(
                        f"piece {index} has vertex {vertex} strictly "
                        f"inside piece {other_index}")
                    break

    if want > 0:
        xs = [p[0] for ring in whole for p in ring]
        ys = [p[1] for ring in whole for p in ring]
        import random

        rng = random.Random(20260902)
        checked = claimed_twice = claimed_none = 0
        for _ in range(samples):
            point = (rng.randint(min(xs), max(xs)), rng.randint(min(ys), max(ys)))
            if not _point_in(whole, point):
                continue
            checked += 1
            hits = sum(1 for piece in pieces if _point_in(piece, point))
            if hits > 1:
                claimed_twice += 1
            elif hits == 0:
                claimed_none += 1
        if claimed_twice:
            out.append(f"{claimed_twice} of {checked} sampled points are "
                       f"claimed by more than one piece")
        if claimed_none:
            out.append(f"{claimed_none} of {checked} sampled points are "
                       f"claimed by no piece")
    return out


def assert_partition(pieces, whole, *, what: str = "pieces") -> None:
    """Raise unless `pieces` partition `whole`."""
    faults = partition_faults(pieces, whole)
    if faults:
        raise OverlayError(f"{what} do not partition their input: "
                           + "; ".join(faults))


# ---------------------------------------------------------------------------
# G1: every vertex a surface declared appears in the map, unmoved
# ---------------------------------------------------------------------------

def declared_vertices(surfaces: Iterable[Sequence[Sequence[Point]]]) -> set:
    """Every point the source named, across every ring of every surface."""
    out = set()
    for rings in surfaces:
        for ring in rings:
            for point in ring:
                out.add((int(point[0]), int(point[1])))
    return out


def vertex_faults(level: Any, declared: Iterable[Point]) -> list[str]:
    """Which declared vertices are missing from the built map.

    **G1, vertex fidelity.** A cut may add points -- that is what a cut does --
    but it may never move one the source placed, so the declared set must be a
    subset of the built set. Exact, no radius.

    This is the invariant that decided weld against snap. Snapping crossings to
    a coarser grid fails it by construction: the moment a crossing moves, the
    piece boundaries that meet there move with it, and a vertex the solver
    placed is no longer where the solver placed it. No taste required, and no
    owner question -- the gate chose.
    """
    built = set()
    for wall in level.walls:
        fields = wall["fields"] if isinstance(wall, dict) else wall.fields
        built.add((int(fields["x"]), int(fields["y"])))
    missing = sorted(set(declared) - built)
    return [f"declared vertex {point} is not in the built map"
            for point in missing]


@dataclass
class CutRegistry:
    """Crossings, and the GENEALOGY of the edges they were computed from.

    A crossing is rounded per coordinate, so it can sit up to
    ``0.5 * sqrt(2) = 0.707`` units off the edge it came from -- and a
    containment test with a half-unit tolerance misses every crossing that
    rounded toward the far corner of its unit cell. That bound is why the weld
    is by identity and not by proximity, and it is the invariant that settles
    the question rather than a preference.

    But identity alone is not enough either. When a cut splits edge ``(p, q)``
    at ``r``, the two halves are new edges, and a LATER cut recording a
    crossing against ``(p, r)`` has recorded it against something no
    neighbouring piece carries -- the neighbour still holds ``(p, q)`` whole.
    So each split records its children's parentage, and at weld time a
    crossing reaches any ring carrying its key **or any ancestor of it**.

    No tolerance constant appears anywhere in this module; `test_overlay`
    greps for one.
    """

    points: dict = field(default_factory=dict)
    parent: dict = field(default_factory=dict)

    def record(self, a: Point, b: Point, point: Point) -> None:
        self.points.setdefault(edge_key(a, b), set()).add(tuple(point))

    def split(self, p: Point, q: Point, r: Point) -> None:
        """Edge (p, q) was cut at r: its two halves descend from it."""
        whole = edge_key(p, q)
        for half in (edge_key(p, r), edge_key(r, q)):
            if half != whole:
                self.parent[half] = whole

    def ancestors(self, key: tuple) -> list:
        """The chain from an edge up to the one it was first cut from."""
        out = []
        seen = {key}
        node = self.parent.get(key)
        while node is not None and node not in seen:
            out.append(node)
            seen.add(node)
            node = self.parent.get(node)
        return out

    def descendants(self, key: tuple) -> list:
        """Every edge that came, at any remove, from cutting this one."""
        children: dict = {}
        for child, parent in self.parent.items():
            children.setdefault(parent, []).append(child)
        out: list = []
        stack = list(children.get(key, ()))
        seen = {key}
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            out.append(node)
            stack.extend(children.get(node, ()))
        return out

    def by_edge(self) -> dict:
        """Which points may be inserted into a ring carrying which edge.

        BOTH directions of the chain, and each answers a different failure.

        UPWARD -- a point recorded against a child edge is offered to every
        ancestor, because a neighbour that was never cut still carries the
        whole edge. That is the case slice 2g could not see.

        DOWNWARD -- a point recorded against a whole edge is offered to every
        edge cut out of it, because a plaza's corner is seeded against the
        street's DECLARED edge and the piece that ends up carrying that stretch
        of street is a grandchild of it. Without this the T survives every cut
        and `PlanarLayout` reports it as an unpaired portal candidate.

        `weld` filters both by span, so an ancestor's point that falls outside
        a child's stretch is simply not inserted there.
        """
        out: dict = {}
        for key, found in self.points.items():
            for target in [key] + self.ancestors(key) + self.descendants(key):
                out.setdefault(target, set()).update(found)
        return out


def weld(pieces: Sequence[Sequence[Sequence[Point]]], registry: dict,
         declared: Iterable[Point] = ()) -> tuple[list, int]:
    """Insert every recorded crossing into every ring that still carries its edge.

    **The weld, by identity, with no search radius anywhere.** While cutting,
    each crossing is recorded against the UNDIRECTED key of the edge it was
    computed from; afterwards, any ring that still holds that whole edge gets
    the crossing inserted into it, ordered along the edge.

    That is what makes two pieces share an edge exactly rather than nearly.
    Without it a cut leaves a T-junction: the piece that was cut has a vertex
    where the chord met its boundary, and the neighbour that was not cut does
    not, so the two diverge by the fraction of a unit the rounding introduced
    and `PlanarLayout` reads it as an overlap.

    The registry spans ALL surfaces of one plane on purpose: a plane's hole
    ring and the island standing in it are the same edges given in opposite
    directions, so a crossing recorded from one must be found by the other.
    `edge_key` is what makes that work.

    The walls this adds are not overhead. Build requires a vertex wherever two
    sectors' boundaries meet -- a wall without one is a red wall -- so these
    are walls the format was always going to need.

    `declared` is the second population, and it takes the OTHER exact test.
    A crossing is rounded, so it is found by identity and genealogy and never
    by geometry. A vertex the solver placed is not rounded at all, so exact
    collinearity is the right question to ask of it -- and it has to be asked
    of the CUT edges rather than the declared ones, because a chord that lands
    collinear with a declared edge merges with it and `_clean` drops the
    corner between them. That is a real case: a shadow chord at the cemetery's
    own y swallowed the cemetery's corner and left one plane piece abutting
    two neighbours across a single edge.
    """
    lookup = registry.by_edge() if hasattr(registry, "by_edge") else {
        key: set(value) for key, value in registry.items()}
    declared = {tuple(point) for point in declared}
    added = 0
    out = []
    for rings in pieces:
        welded = []
        for ring in rings:
            grown: list[Point] = []
            count = len(ring)
            for index in range(count):
                here = tuple(ring[index])
                nxt = tuple(ring[(index + 1) % count])
                grown.append(here)
                found = set(lookup.get(edge_key(here, nxt)) or ())
                if declared:
                    #: The second population, asked its own exact question.
                    #: This has to happen BEFORE the empty-set shortcut: the
                    #: edge that swallowed the cemetery's corner had no
                    #: registry entry at all, because no cut ever made it.
                    found |= {point for point in declared
                              if _between(here, nxt, point)}
                if not found:
                    continue
                #: only points strictly between the two ends, in order along
                #: the edge; a piece that already has one keeps it once
                span = (nxt[0] - here[0], nxt[1] - here[1])
                inserted = []
                for point in found:
                    if point in (here, nxt):
                        continue
                    #: A REGISTRY POINT BELONGS TO ITS EDGE BY RECORD, not by
                    #: re-derivation. It was rounded to the integer grid when
                    #: it was computed, so it is routinely NOT exactly
                    #: collinear with the edge it came from -- 668 on the
                    #: cross product for the fixture's own crossing -- and an
                    #: exact collinearity test rejects the very points the
                    #: weld exists to insert. Only the ordering matters here.
                    if not _within_span(here, nxt, point):
                        continue
                    inserted.append(point)
                inserted.sort(key=lambda p: ((p[0] - here[0]) * span[0]
                                             + (p[1] - here[1]) * span[1]))
                for point in inserted:
                    grown.append(point)
                    added += 1
            welded.append(grown)
        out.append(welded)
    return out, added


def _within_span(a: Point, b: Point, point: Point) -> bool:
    """Does the point fall between the two ends, along the edge?

    The bounding box only: a registry point is already known to belong to this
    edge, and asking again in exact integers would reject it for the rounding
    that put it there.
    """
    return (min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= point[1] <= max(a[1], b[1]))


def _between(a: Point, b: Point, point: Point) -> bool:
    """Is `point` on the segment a->b, inclusive of neither end?

    Collinearity is exact; the containment test is the bounding box, which for
    a collinear point is the whole question.
    """
    cross = ((b[0] - a[0]) * (point[1] - a[1])
             - (b[1] - a[1]) * (point[0] - a[0]))
    if cross != 0:
        return False
    return (min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= point[1] <= max(a[1], b[1]))


def seed_coincident_vertices(registry: "CutRegistry",
                             surfaces: Iterable[Sequence[Sequence[Point]]]
                             ) -> int:
    """Record every surface corner that lands inside another surface's edge.

    The weld inserts a crossing into every ring carrying the edge it came
    from. That closes the cuts, and it does not close the DECLARATION: a
    plaza let into a street, an end wall across its mouth or a yard notched
    out of an island all put a corner in the middle of a neighbour's edge,
    and no cut ever made it. Build calls a wall like that a T-junction and
    draws a red line through it.

    So the same registry is seeded, before any field runs, with every vertex
    of one surface that lies strictly within an edge of another. From there
    it is a crossing like any other and the weld does not care which kind it
    was -- which is the point: an island is an island however it came to be
    one, and a T is a T however it came to be one.

    Exact collinearity is the right test HERE, unlike inside the weld: these
    are declared integer coordinates that no rounding has touched.
    """
    rings = [list(ring) for surface in surfaces for ring in surface]
    points = {tuple(point) for ring in rings for point in ring}
    seeded = 0
    for ring in rings:
        for index, here in enumerate(ring):
            nxt = ring[(index + 1) % len(ring)]
            here, nxt = tuple(here), tuple(nxt)
            for point in points:
                if point in (here, nxt):
                    continue
                if _between(here, nxt, point):
                    registry.record(here, nxt, point)
                    seeded += 1
    return seeded
