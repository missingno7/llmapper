"""Emitting streets on the ground-plane model: roads, islands, kerbs, ends.

The general emitter behind slices 1 and 2. Given roads (rectangles with a
class), islands (rectangles with a band) and masses (rectangles with a
height), it produces the ground planes, the pavement islands standing 2048 on
them, the kerb records on the ROAD side, the junction squares where roads
cross, the end walls where roads stop, and the shadow cuts of one sun.

The one structural rule, learned the hard way in slice 1: **a cut crosses
everything it crosses, in one pass.** Cutting the road but not the pavement
leaves an island edge spanning two road pieces with nothing to pair against,
and `PlanarLayout.compile` refuses it as an unpaired portal -- which is the
old "insert a sector where there is room" failure at one level up.

A consequence of having ONE sun that is worth stating rather than discovering
twice: at `SUN_BEARING` 478 -- 84 degrees, very nearly due +y -- a **north-south
road is cut lengthwise and an east-west road is cut across**. A shadow on a
north-south street runs along it and reaches the far pavement only after some
125,000 units of run, which is longer than any street in this city. E3M1 has
both kinds (s8 is 7456 x 21504, s45 is 18048 x 4096) and its oblique shade
edges are exactly the ones its east-west roads carry.
"""

from __future__ import annotations

import math
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for path in (str(ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from bloodmap.overlay import (                                    # noqa: E402
    MIN_PIECE_AREA, Cut, HeightIsland, kerb_records, signed_area,
    split_convex)
from bloodmap.player_space import PLAYER_PROFILES                 # noqa: E402
from bloodmap.street import end_wall                              # noqa: E402
from resolution import (                                          # noqa: E402
    GRADE, SHADE_LIT, SHADE_SHADOW, SKY_TILE, STREET_SKY, SUN_BEARING,
    SUN_SHADOW_PER_HEIGHT)

STANDING = PLAYER_PROFILES["blood"].standing_height

ROAD_TILE = 352
PAVE_TILE = 4
KERB_TILE = 6
RISE = 2048
ROAD_Z = GRADE + RISE
#: Where an island's pavement sits: at grade, 2048 above the road.
ISLAND_Z = GRADE


@dataclass
class Road:
    road_id: str
    rect: tuple[int, int, int, int]
    width_class: str = "street"
    facade_tile: int = 400


@dataclass
class Island:
    island_id: str
    rect: tuple[int, int, int, int]
    band: int = 2048


@dataclass
class Mass:
    mass_id: str
    rect: tuple[int, int, int, int]
    height: int = 4 * 16960
    island: str = ""


@dataclass
class StreetBuild:
    """What the emitter produced, so the gates can be asked about it."""

    pieces: list[tuple] = field(default_factory=list)
    kerbs: list[dict] = field(default_factory=list)
    shadow_edges: list[tuple] = field(default_factory=list)
    ends: list[dict] = field(default_factory=list)
    junctions: list[str] = field(default_factory=list)
    lamps: int = 0
    refusals: list[str] = field(default_factory=list)


def rect_points(rect):
    x0, y0, x1, y1 = (int(v) for v in rect)
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def overlaps(a, b) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def intersection(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return (max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1))


def sun_vector(height: int) -> tuple[int, int]:
    """How far and which way a mass of this height throws its shadow."""
    length = int(height * SUN_SHADOW_PER_HEIGHT)
    radians = math.radians(SUN_BEARING * 360.0 / 2048.0)
    return (int(round(length * math.cos(radians))),
            int(round(length * math.sin(radians))))


def shadow_hull(rect, height):
    """The mass's footprint swept along the sun vector, as a convex hull."""
    dx, dy = sun_vector(height)
    base = rect_points(rect)
    points = sorted(set(base + [(x + dx, y + dy) for x, y in base]))

    def half(seq):
        out = []
        for point in seq:
            while len(out) >= 2:
                ax, ay = out[-2]
                bx, by = out[-1]
                if (bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax) > 0:
                    break
                out.pop()
            out.append(point)
        return out

    return half(points)[:-1] + half(list(reversed(points)))[:-1], (dx, dy)


def shadow_cuts(masses: Sequence[Mass], surfaces: dict) -> list[Cut]:
    """One cut per mass whose shadow actually falls across something.

    A shadow boundary nobody can see is not a shadow edge, so a mass whose
    hull crosses no surface contributes no cut rather than a stray sector
    boundary.
    """
    out = []
    for mass in masses:
        hull, vector = shadow_hull(mass.rect, mass.height)
        dx, dy = vector
        perp = (-dy, dx)
        ordered = sorted(hull, key=lambda p: p[0] * perp[0] + p[1] * perp[1])
        for corner in (ordered[0], ordered[-1]):
            cut = Cut(corner, (corner[0] + dx, corner[1] + dy))
            if any(all(split_convex(rect_points(spec[0]), cut))
                   for spec in surfaces.values()):
                out.append(cut)
                break
    return out


def centroid(polygon):
    return (sum(p[0] for p in polygon) // len(polygon),
            sum(p[1] for p in polygon) // len(polygon))


def shared_edge(poly_a, poly_b, *, axis: str, at: int, minimum: int = 512):
    """The stretch of the line `axis = at` that both polygons touch."""
    key = 1 if axis == "x" else 0

    def span(poly):
        values = [p[key] for p in poly
                  if (p[0] if axis == "x" else p[1]) == at]
        return (min(values), max(values)) if len(values) >= 2 else None

    a, b = span(poly_a), span(poly_b)
    if a is None or b is None:
        return None
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    if hi - lo < minimum:
        return None
    if axis == "x":
        return ((at, lo), (at, hi))
    return ((lo, at), (hi, at))


def emit(layout, roads: Sequence[Road], islands: Sequence[Island],
         masses: Sequence[Mass] = (), *, ends: Sequence[dict] = (),
         lamps: bool = True) -> StreetBuild:
    """Ground planes, islands, kerbs, junctions, shadows and end walls.

    Everything is emitted whole and then cut once, by every cut that crosses
    it. The pieces inherit their surface and differ only in shade.
    """
    out = StreetBuild()

    #: --- junctions: where two roads cross, the overlap is a road square ---
    squares = {}
    for index, road_a in enumerate(roads):
        for road_b in roads[index + 1:]:
            if not overlaps(road_a.rect, road_b.rect):
                continue
            box = intersection(road_a.rect, road_b.rect)
            squares[f"junction:{road_a.road_id}:{road_b.road_id}"] = box
            out.junctions.append(f"junction:{road_a.road_id}:{road_b.road_id}")

    #: A road gives its overlap to the junction, so the two never both own it.
    surfaces: dict[str, tuple] = {}
    for road in roads:
        pieces = [road.rect]
        for box in squares.values():
            pieces = [piece for chunk in pieces
                      for piece in _minus(chunk, box)]
        for number, piece in enumerate(pieces):
            name = road.road_id if len(pieces) == 1 else f"{road.road_id}:{number}"
            surfaces[name] = (piece, ROAD_Z, ROAD_TILE, KERB_TILE, "road",
                              road.facade_tile)
    for name, box in squares.items():
        surfaces[name] = (box, ROAD_Z, ROAD_TILE, KERB_TILE, "road", 400)
    for island in islands:
        surfaces[island.island_id] = (island.rect, ISLAND_Z, PAVE_TILE,
                                      PAVE_TILE, "island", 400)

    cuts = shadow_cuts(masses, surfaces)
    out.shadow_edges = [(cut.a, cut.b) for cut in cuts]

    #: --- cut everything, once, by every cut ------------------------------
    by_surface: dict[str, list] = {}
    for surface_id, (rect, floor_z, floor_tile, wall_tile, kind, facade) in \
            sorted(surfaces.items()):
        parts = [(rect_points(rect), SHADE_LIT)]
        for cut in cuts:
            grown = []
            for poly, shade in parts:
                lit, shaded = split_convex(poly, cut)
                #: A CUT THAT WOULD LEAVE A SCRAP DOES NOT CUT. An oblique
                #: shadow clipping the corner off a junction leaves a triangle
                #: 43 units across, and the compiler then finds coincident
                #: wall segments nobody declared. `overlay.MIN_PIECE_AREA` is
                #: the same figure `clip_to_rect` already refuses on: below it
                #: a piece is not a sector anyone can stand on or see.
                if (lit and shaded
                        and abs(signed_area(lit)) >= MIN_PIECE_AREA
                        and abs(signed_area(shaded)) >= MIN_PIECE_AREA):
                    grown.append((lit, shade))
                    grown.append((shaded, SHADE_SHADOW))
                else:
                    #: the shade of the larger half, so a grazed surface takes
                    #: the shade it is mostly in rather than keeping the lit
                    #: default by accident
                    if shaded and (not lit or abs(signed_area(shaded))
                                   > abs(signed_area(lit))):
                        grown.append((poly, SHADE_SHADOW))
                    else:
                        grown.append((poly, shade))
            parts = grown
        halves = []
        for number, (poly, shade) in enumerate(parts):
            name = surface_id if len(parts) == 1 else f"{surface_id}#{number}"
            layout.add_region(
                name, poly, floor_z=floor_z, ceiling_z=floor_z - STREET_SKY,
                floor_picnum=floor_tile, ceiling_picnum=SKY_TILE,
                wall_picnum=wall_tile, floor_shade=shade, wall_shade=shade,
                parallax_ceiling=True, role="street")
            halves.append((name, poly, shade))
            out.pieces.append((name, poly, shade, kind, surface_id))
        by_surface[surface_id] = halves

    #: --- joins: EVERY pair of pieces that shares a wall segment ----------
    #:
    #: Paired by coincident geometry, not by rectangle adjacency. The first
    #: version asked whether the two surfaces' original rectangles touched,
    #: which stops being the question the moment a junction is subtracted out
    #: of a road or a shadow cuts a piece in two -- and `PlanarLayout.compile`
    #: refused nine unpaired portals across the whole graph to say so. Two
    #: pieces are neighbours when a segment of one lies on a segment of the
    #: other, and that is true whatever cut produced them.
    kinds = {name: spec[4] for name, spec in surfaces.items()}
    flat = [(name, poly, surface_id)
            for surface_id, halves in sorted(by_surface.items())
            for name, poly, _shade in halves]
    for index, (a_name, a_poly, a_id) in enumerate(flat):
        for b_name, b_poly, b_id in flat[index + 1:]:
            edge = _coincident(a_poly, b_poly)
            if edge is None:
                continue
            layout.add_connection(f"join:{a_name}:{b_name}", a_name, b_name,
                                  role="portal", a1=edge[0], a2=edge[1])
            pair = (kinds[a_id], kinds[b_id])
            if "island" in pair and "road" in pair:
                road_name = a_name if kinds[a_id] == "road" else b_name
                island_name = b_name if kinds[a_id] == "road" else a_name
                layout.paint_wall(road_name, edge[0], edge[1], picnum=KERB_TILE)
                out.kerbs.append({
                    "road_piece": road_name, "island": island_name,
                    "edge": edge, "picnum": KERB_TILE, "rise": RISE})

    #: --- lamps stand on the pavements ------------------------------------
    if lamps:
        for island in islands:
            for name, poly, _shade in by_surface[island.island_id]:
                spot = centroid(poly)
                layout.add_sprite(f"lamp:{name}", name, x=int(spot[0]),
                                  y=int(spot[1]), z=int(ISLAND_Z), picnum=506,
                                  type=0, status=0, cstat=0, x_repeat=32,
                                  y_repeat=32, angle=0)
                out.lamps += 1

    out.ends = list(ends)
    return out


def _coincident(poly_a, poly_b, minimum: int = 64):
    """The segment two polygons share, if they share one.

    Collinear and overlapping, which covers both the axis-aligned edges the
    grid produces and the oblique ones a shadow cut leaves -- a cut gives both
    pieces the SAME crossing points, so its segments match exactly.
    """
    for a0, a1 in _edges(poly_a):
        for b0, b1 in _edges(poly_b):
            found = _overlap(a0, a1, b0, b1, minimum)
            if found is not None:
                return found
    return None


def _edges(polygon):
    for index, point in enumerate(polygon):
        yield point, polygon[(index + 1) % len(polygon)]


def _overlap(a0, a1, b0, b1, minimum):
    """The shared stretch of two collinear segments, in exact integers.

    Three cases, and the first is the one that matters: a cut gives BOTH
    pieces the same two crossing points, so an oblique shared edge is an
    exact endpoint match. Reconstructing it by projecting onto a float unit
    vector -- which the first version did -- loses the last unit and the
    compiler then reports the pair as unpaired, which is what nine of these
    did across the graph.
    """
    if {tuple(a0), tuple(a1)} == {tuple(b0), tuple(b1)}:
        return (tuple(a0), tuple(a1))
    ax, ay = a1[0] - a0[0], a1[1] - a0[1]
    bx, by = b1[0] - b0[0], b1[1] - b0[1]
    if ax * by - ay * bx != 0:
        return None                                  # not parallel
    if (b0[0] - a0[0]) * ay - (b0[1] - a0[1]) * ax != 0:
        return None                                  # parallel, not collinear
    if ax == 0 and bx == 0 and a0[0] == b0[0]:       # both vertical
        lo = max(min(a0[1], a1[1]), min(b0[1], b1[1]))
        hi = min(max(a0[1], a1[1]), max(b0[1], b1[1]))
        if hi - lo < minimum:
            return None
        return ((a0[0], lo), (a0[0], hi))
    if ay == 0 and by == 0 and a0[1] == b0[1]:       # both horizontal
        lo = max(min(a0[0], a1[0]), min(b0[0], b1[0]))
        hi = min(max(a0[0], a1[0]), max(b0[0], b1[0]))
        if hi - lo < minimum:
            return None
        return ((lo, a0[1]), (hi, a0[1]))
    #: Collinear and oblique but not the same segment. Left unpaired on
    #: purpose: reconstructing a partial oblique overlap needs rational
    #: endpoints Build cannot store, and after the sliver rule no cut
    #: produces one.
    return None


def _minus(rect, box):
    """`rect` with `box` taken out, as up to four rectangles."""
    if not overlaps(rect, box):
        return [rect]
    x0, y0, x1, y1 = rect
    bx0, by0, bx1, by1 = intersection(rect, box)
    out = []
    if y0 < by0:
        out.append((x0, y0, x1, by0))
    if by1 < y1:
        out.append((x0, by1, x1, y1))
    if x0 < bx0:
        out.append((x0, by0, bx0, by1))
    if bx1 < x1:
        out.append((bx1, by0, x1, by1))
    return [piece for piece in out
            if piece[2] - piece[0] >= 512 and piece[3] - piece[1] >= 512]


def _touching(a, b):
    """Which line two rectangles share, if any."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    if ax1 == bx0 and min(ay1, by1) - max(ay0, by0) >= 512:
        return "x", ax1
    if bx1 == ax0 and min(ay1, by1) - max(ay0, by0) >= 512:
        return "x", bx1
    if ay1 == by0 and min(ax1, bx1) - max(ax0, bx0) >= 512:
        return "y", ay1
    if by1 == ay0 and min(ax1, bx1) - max(ax0, bx0) >= 512:
        return "y", by1
    return None, None
