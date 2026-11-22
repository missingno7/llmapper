"""Surface overlays: patches on a region's floor, cut into the finished map after everything else has run.

EXPERIMENTAL (owner, 2026-11-20): not used by the city's build by default
(`build_skeleton.GROUND_SHADOWS`); its open questions are written there.

The owner, 2026-11-20, of shadows on the street: "try to come up with some
general handling of shadows that won't break geometry ... this splitting
sectors, it can be used to like some sort of like decoration, like
different textures and stuff like that. But it is almost like a separate
layer about what is existing".

It is a separate layer. A region is a SPACE: where a body can go, its floor
and its ceiling, and how it joins its neighbours. A shadow on the pavement,
a worn patch of paving, a puddle, a rug, a painted line are not spaces; they
are what the floor looks like over part of it. In Build a floor has one
shade and one tile per sector, so showing one means cutting the sector.

WHERE the cut happens is the whole design. The first version cut regions at
compile, and the city's own passes broke at once: the facade pass reads a
street sector's hole loops as its buildings and its largest loop as the
district's edge, the station's dress finds the carriage by its one sector --
dozens of passes ask for a region's sector after compile, and each would
have had to learn about pieces. So an overlay is:

* DECLARED on the layout (`PlanarLayout.add_overlay`): a polygon, a shade
  offset and/or floor fields, and a name. It is source, kept beside the
  region it lies on; the region is not touched.
* LAID on the finished map (`lay`) as its last change, after every pass has
  seen whole regions and after the lamps have lit them. Each overlaid
  sector is cut into pieces; every other sector keeps its index, the pieces
  are appended, the walls are laid out again with each twin re-paired, a
  wall split by a cut keeps its texture's phase, and every sprite (and the
  player start) moves to the piece it stands in.

(`bloodmap.overlay`, singular, is the street-model pipeline's exact
half-plane cutter; it cuts while building, which is what this one learned
not to do for a layout whose passes read regions after compile.)

A cut crosses a sector's boundary only where that boundary runs along an
axis, so a crossing rounded to whole units is still on the neighbour's wall;
it keeps `SLIVER` clear of a slanted wall, of a wall carrying an XWALL, and
of a wall facing a sector with a type or an XSECTOR, so no door, lift or
switch gains a vertex. A sector with a slope, or an XSECTOR that does more
than animate its shade, is not cut, though a patch over its whole floor is
laid (that changes only its look); a shade-only XSECTOR goes with every
piece. A
part of a patch thinner than `SLIVER` is not laid, and a thin scrap of what
is left goes to the piece beside it.
"""

from __future__ import annotations

import copy
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .model import DiskObject, record_fields as _f

#: thinner than this (map units) a piece is a sliver
SLIVER = 128
#: overlays may set these on the pieces they make: what the floor and the
#: ceiling look like, and -- for a light panel -- how far its ceiling is
#: recessed (the campaign's panels stand 1024 above the room's ceiling,
#: `bloodmap.light_kinds`)
SURFACE_FIELDS = ("floor_picnum", "floor_stat", "floor_shade", "floor_pal",
                  "floor_x_panning", "floor_y_panning",
                  "ceiling_picnum", "ceiling_stat", "ceiling_shade", "ceiling_pal",
                  "ceiling_x_panning", "ceiling_y_panning", "ceiling_z")


@dataclass
class OverlaySpec:
    overlay_id: str
    region_id: str
    #: one or more polygons, each (outer ring, [hole rings])
    shapes: tuple
    floor_shade_offset: int = 0
    surface: dict = field(default_factory=dict)
    note: str = ""


class OverlayError(ValueError):
    """An overlay the layer will not lay."""


# --- what may be cut -------------------------------------------------------

def uncuttable(layout) -> dict[str, str]:
    """Regions of a layout not worth declaring an overlay on, each with the reason.

    The cut on the finished map refuses what it must anyway (`cut_sectors`);
    saying it on the layout lets a caster skip these without building
    anything. Each is named by something that expects it whole: a
    mechanism, a partition, a stacked or special pair, an XSECTOR, a slope,
    or a shaft (one footprint in two layers, as a grate's mouth over the
    sewer's riser).
    """
    out: dict[str, str] = {}
    for rid, _edge in layout.carried:
        out.setdefault(rid, "a mechanism carries its walls")
    for driven, payload in layout.declared_motion.items():
        for rid in (driven, *payload):
            out.setdefault(rid, "a mechanism moves it")
    for a, b, kind in layout.special_pairs:
        for rid in (a, b):
            out.setdefault(rid, f"a special pair ({kind})")
    for partition in layout.partitions.values():
        for rid in (partition.region_a, partition.region_b):
            if rid:
                out.setdefault(rid, "a partition")
    footprints: dict[frozenset, list] = {}
    for region in layout.regions.values():
        if region.stack_pair:
            out.setdefault(region.region_id, "a stack")
            out.setdefault(region.stack_pair, "a stack")
        if region.sector_behavior:
            out.setdefault(region.region_id, "an XSECTOR")
        if region.floor_slope is not None or region.ceiling_slope is not None:
            out.setdefault(region.region_id, "a slope")
        footprints.setdefault(frozenset(region.outer), []).append(region)
    for group in footprints.values():
        if len({region.layer for region in group}) > 1:
            for region in group:
                out.setdefault(region.region_id, "a shaft: one footprint in two layers")
    return out


# --- geometry --------------------------------------------------------------

def _polygons(geometry) -> list:
    from shapely.geometry import GeometryCollection, MultiPolygon, Polygon

    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, (MultiPolygon, GeometryCollection)):
        return [g for part in geometry.geoms for g in _polygons(part)]
    return []


def _thin(polygon) -> bool:
    return polygon.buffer(-SLIVER / 2).is_empty


def _signed(points) -> float:
    return sum(points[i][0] * points[(i + 1) % len(points)][1]
               - points[(i + 1) % len(points)][0] * points[i][1]
               for i in range(len(points)))


def _ring(coords, *, positive: bool) -> list:
    points = []
    for x, y in list(coords)[:-1]:
        p = (int(round(x)), int(round(y)))
        if not points or points[-1] != p:
            points.append(p)
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    # rounding to whole units can leave a spike: a run out to a point and
    # straight back. Two walls would then lie on one segment.
    changed = True
    while changed and len(points) > 3:
        changed = False
        for i in range(len(points)):
            a, b, c = points[i - 1], points[i], points[(i + 1) % len(points)]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            back = (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1])
            if a == b or (cross == 0 and back <= 0):
                points.pop(i)
                changed = True
                break
    if (_signed(points) > 0) != positive:
        points.reverse()
    return points


def _shape(spec_shapes) -> Any:
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    return unary_union([Polygon(outer, holes) for outer, holes in spec_shapes])


def pieces(base, keep_clear, specs, report) -> list:
    """Cut a floor polygon by its overlays: [(polygon, spec or None)].

    `keep_clear` is a shape no patch may enter (the band along walls a cut
    must not cross). The last declared overlay lies on top.
    """
    from shapely import set_precision
    from shapely.ops import unary_union

    remaining = base
    laid = []
    for spec in reversed(specs):
        shape = _shape(spec.shapes)
        if keep_clear is not None:
            shape = shape.difference(keep_clear)
        shape = set_precision(shape.intersection(remaining), 1.0)
        kept = []
        for polygon in _polygons(shape):
            if _thin(polygon):
                report["slivers_dropped"] += 1
            else:
                kept.append(polygon)
        if not kept:
            continue
        remaining = set_precision(remaining.difference(unary_union(kept)), 1.0)
        laid.append((spec, kept))
    laid.reverse()
    made = [(polygon, spec) for spec, polys in laid for polygon in polys]
    made += [(polygon, None) for polygon in _polygons(remaining)]
    merged = True
    while merged:
        merged = False
        for index, (polygon, _spec) in enumerate(made):
            if not _thin(polygon) and polygon.area >= SLIVER * SLIVER * 4:
                continue
            best, length = None, 0.0
            for other_index, (other, _s) in enumerate(made):
                if other_index == index:
                    continue
                shared = polygon.boundary.intersection(other.boundary).length
                if shared > length:
                    best, length = other_index, shared
            if best is None:
                continue
            joined = _polygons(set_precision(unary_union([made[best][0], polygon]), 1.0))
            if len(joined) != 1:
                continue
            made[best] = (joined[0], made[best][1])
            made.pop(index)
            report["slivers_merged"] += 1
            merged = True
            break
    return made


def _on(a, b, p) -> bool:
    """p lies exactly on segment a-b, strictly between its ends."""
    cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    if cross != 0 or p == a or p == b:
        return False
    dot = (p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])
    return 0 < dot < (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2


#: piece corners closer than this (plan units) are one corner
SNAP = 8


def _snap_corners(made, fixed: set) -> list:
    """Merge piece corners that rounding left a few units apart into one.

    Where several band edges meet, rounding to whole units can leave three or
    four pieces with corners 1-3 units apart instead of one point, and the
    walls between them double back on each other. Every corner within `SNAP`
    of an earlier one (the sector's own corners first, so the outline never
    moves) is moved onto it; a piece that collapses is dropped.
    """
    from shapely.geometry import Polygon

    reps = list(fixed)
    grid: dict = {}

    def key(p):
        return (p[0] // SNAP, p[1] // SNAP)

    for p in reps:
        grid.setdefault(key(p), []).append(p)

    def snap(p):
        p = (int(round(p[0])), int(round(p[1])))
        kx, ky = key(p)
        best, dist = None, None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for q in grid.get((kx + dx, ky + dy), ()):
                    d = (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2
                    if d <= SNAP * SNAP and (dist is None or d < dist):
                        best, dist = q, d
        if best is None:
            grid.setdefault((kx, ky), []).append(p)
            return p
        return best

    out = []
    for polygon, spec in made:
        rings = [[snap(c) for c in ring.coords[:-1]] for ring in (polygon.exterior, *polygon.interiors)]
        cleaned = []
        for ring in rings:
            dedup = [p for i, p in enumerate(ring) if p != ring[i - 1]]
            if len(dedup) >= 3:
                cleaned.append(dedup)
        if not cleaned:
            continue
        snapped = Polygon(cleaned[0], cleaned[1:])
        if not snapped.is_valid:
            snapped = snapped.buffer(0)
        for part in _polygons(snapped):
            if part.area > 1:
                out.append((part, spec))
    return out


def _near_on(a, b, p, tolerance: float = 1.0) -> bool:
    """p lies within `tolerance` of segment a-b, strictly between its ends."""
    if p == a or p == b:
        return False
    dx, dy = b[0] - a[0], b[1] - a[1]
    span = dx * dx + dy * dy
    if not span:
        return False
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / span
    if not 0 < t < 1:
        return False
    return math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1]) <= tolerance


def _covers(a, b, p, q) -> bool:
    """Segment p-q lies on segment a-b (ends included)."""
    return all(point in (a, b) or _on(a, b, point) for point in (p, q))


def _distance(a, b, p) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    span = dx * dx + dy * dy
    t = 0.0 if not span else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / span))
    return math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1])


def _vertices(polygon) -> list:
    out = []
    for ring in (polygon.exterior, *polygon.interiors):
        out += [(int(round(x)), int(round(y))) for x, y in list(ring.coords)[:-1]]
    return out


# --- the finished map ------------------------------------------------------

class _Snapshot:
    """The map's walls as they were before anything was moved."""

    def __init__(self, disk):
        self.pos = [(int(_f(w)["x"]), int(_f(w)["y"])) for w in disk.walls]
        self.point2 = [int(_f(w)["point2"]) for w in disk.walls]
        self.next_wall = [int(_f(w)["next_wall"]) for w in disk.walls]
        self.fields = [dict(_f(w)) for w in disk.walls]
        self.loops = []
        for sector in disk.sectors:
            f = _f(sector)
            start, count = int(f["wall_ptr"]), int(f["wall_count"])
            seen, loops = set(), []
            for first in range(start, start + count):
                if first in seen:
                    continue
                loop, wall = [], first
                while wall not in seen:
                    seen.add(wall)
                    loop.append(wall)
                    wall = self.point2[wall]
                loops.append(loop)
            self.loops.append(loops)

    def segment(self, wall):
        return self.pos[wall], self.pos[self.point2[wall]]


def lay(disk: Any, compiled: Any) -> dict[str, Any]:
    """Cut every overlay declared on the compiled layout into the finished map."""
    jobs: dict[int, list] = defaultdict(list)
    for spec in compiled.layout.overlays.values():
        allocation = compiled.allocations.get(spec.region_id)
        if allocation is None:
            raise OverlayError(f"overlay {spec.overlay_id}: {spec.region_id} built no sector")
        jobs[allocation.sector_id].append(spec)
    return cut_sectors(disk, dict(jobs))


def cut_sectors(disk: Any, jobs: dict[int, list],
                wall_points: dict[int, list] | None = None,
                slopes_across: bool = False) -> dict[str, Any]:
    """Cut each sector by its overlays; every other sector keeps its index.

    Returns a report with `parent` (new sector -> the sector it was cut from)
    and `refused` (sector -> why it was left whole).

    A sloped sector is refused unless `slopes_across`, and then cut only
    ACROSS its slope: Build hinges a slope on a sector's first wall
    (`bloodmap.slope`), so a piece whose first wall lies on the original
    hinge line, with the same heinum and the same z on that line, is the same
    plane. Every new edge must be perpendicular to the hinge and every piece
    must keep a stretch of it, or the sector is left whole. (The owner,
    2026-11-21: "be careful about slopes, I think we still can split it
    perpendicularly to not break it".)
    """
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union

    report: dict[str, Any] = {"sectors": 0, "pieces": 0, "slivers_merged": 0,
                              "slivers_dropped": 0, "walls_split": 0, "seams": 0,
                              "refused": {}, "parent": {}}
    snap = _Snapshot(disk)

    def busy(sector: int) -> bool:
        f = _f(disk.sectors[sector])
        return int(f["type"]) != 0 or not shade_only(disk.sectors[sector])

    plans: dict[int, list] = {}
    inserts: dict[int, set] = defaultdict(set)
    original: dict[int, dict] = {}
    hinge_of: dict[int, tuple] = {}
    for sector, specs in sorted(jobs.items()):
        sf = _f(disk.sectors[sector])
        loops = snap.loops[sector]
        rings = [[snap.pos[w] for w in loop] for loop in loops]
        outer = max(range(len(rings)), key=lambda i: abs(_signed(rings[i])))
        base = Polygon(rings[outer], [r for i, r in enumerate(rings) if i != outer])
        # A patch over the whole floor changes how it looks and nothing else:
        # it needs no cut, any sector may take it, and it hides every patch
        # declared before it. The patches declared after it are cut in on
        # top, each relative to the floor as it was (the sun brightens the
        # street; the shadow on it is the street's own shade, darker).
        top_whole = max((i for i, spec in enumerate(specs)
                         if base.is_valid and base.difference(_shape(spec.shapes)).area < 1),
                        default=None)
        original[sector] = dict(sf)
        partial = specs if top_whole is None else specs[top_whole + 1:]
        if top_whole is not None:
            _apply(disk.sectors[sector], specs[top_whole])
            report["whole"] = report.get("whole", 0) + 1
        if not partial:
            continue
        if int(sf["extra"]) > 0 and not shade_only(disk.sectors[sector]):
            report["refused"][sector] = "an XSECTOR"
            continue
        sloped = bool((int(sf["floor_stat"]) | int(sf["ceiling_stat"])) & 2)
        if sloped and not slopes_across:
            report["refused"][sector] = "a slope"
            continue
        if not base.is_valid:
            report["refused"][sector] = "an invalid outline"
            continue
        specs = partial
        walls = [w for loop in loops for w in loop]
        clear = []
        for wall in walls:
            a, b = snap.segment(wall)
            wf = snap.fields[wall]
            other, twin = int(wf["next_sector"]), snap.next_wall[wall]
            if ((a[0] != b[0] and a[1] != b[1]) or int(wf["extra"]) > 0
                    or (other >= 0 and busy(other))
                    or (twin >= 0 and int(snap.fields[twin]["extra"]) > 0)):
                clear.append(LineString([a, b]).buffer(SLIVER, quad_segs=2))
        keep_clear = unary_union(clear) if clear else None
        made = pieces(base, keep_clear, specs, report)
        made = _snap_corners(made, {p for ring in rings for p in ring})
        if len(made) == 1 and made[0][1] is not None:
            # one patch over the whole floor: no cut, only its look
            _apply(disk.sectors[sector], made[0][1])
            report["whole"] = report.get("whole", 0) + 1
            continue
        if len(made) <= 1:
            continue
        if sloped:
            # across the slope only: every new edge perpendicular to the
            # hinge (the sector's first wall), every piece holding a stretch
            # of the hinge line to be its own first wall
            hp, hq = snap.segment(loops[0][0])
            hx, hy = hq[0] - hp[0], hq[1] - hp[1]
            hlen = (hx * hx + hy * hy) ** 0.5
            outline = [snap.segment(w) for w in walls]

            def on_hinge_line(a, b):
                return all(abs(hx * (v[1] - hp[1]) - hy * (v[0] - hp[0])) <= hlen for v in (a, b))

            fine = True
            for polygon, _spec in made:
                ring = list(polygon.exterior.coords)[:-1]
                edges = list(zip(ring, ring[1:] + ring[:1]))
                if not any(on_hinge_line(a, b) for a, b in edges):
                    fine = False
                for a, b in edges:
                    a, b = tuple(map(int, a)), tuple(map(int, b))
                    if any(_covers(p, q, a, b) for p, q in outline):
                        continue
                    ex, ey = b[0] - a[0], b[1] - a[1]
                    if abs(ex * hx + ey * hy) > 0.01 * hlen * (ex * ex + ey * ey) ** 0.5:
                        fine = False
            if not fine:
                report["refused"][sector] = "a slope not cut across it"
                continue
            hinge_of[sector] = (hp, hq)
        # every vertex a piece puts on this sector's boundary is exactly on
        # a wall (it is then added to that wall and its twin), or the sector
        # is left whole: the piece would leave the neighbour's line
        local: dict[int, set] = defaultdict(set)
        ok = True
        for polygon, _spec in made:
            for p in _vertices(polygon):
                for wall in walls:
                    a, b = snap.segment(wall)
                    if _on(a, b, p):
                        local[wall].add(p)
                        if snap.next_wall[wall] >= 0:
                            local[snap.next_wall[wall]].add(p)
                    elif p not in (a, b) and _distance(a, b, p) < 1.0:
                        ok = False
        if not ok:
            report["refused"][sector] = "a cut would leave a wall's line"
            continue
        for wall, points in local.items():
            inserts[wall] |= points
        plans[sector] = made

    # walls split along their length on their own (a light band edge on a long
    # wall): each point goes on the wall and on its twin, and is refused where
    # it would not lie exactly on the line, or where the wall or its twin
    # carries an XWALL or faces a sector a mechanism moves
    for wall, points in (wall_points or {}).items():
        a, b = snap.segment(wall)
        twin = snap.next_wall[wall]
        if int(snap.fields[wall]["extra"]) > 0 or (twin >= 0 and int(snap.fields[twin]["extra"]) > 0):
            report["walls_refused"] = report.get("walls_refused", 0) + 1
            continue
        other = int(snap.fields[wall]["next_sector"])
        if other >= 0 and busy(other):
            report["walls_refused"] = report.get("walls_refused", 0) + 1
            continue
        good = {tuple(map(int, p)) for p in points if _on(a, b, tuple(map(int, p)))}
        if not good:
            continue
        inserts[wall] |= good
        if twin >= 0:
            inserts[twin] |= good
        report["walls_cut"] = report.get("walls_cut", 0) + 1
    if not plans and not inserts:
        return report

    # --- the sectors' loops, as segments with the wall each came from -------
    new_sectors = list(disk.sectors)
    next_extra = [max([int(_f(s)["extra"]) for s in disk.sectors] + [0])]
    layout_loops: dict[int, list] = {}
    shapes_of: dict[int, list] = {}
    for sector, made in plans.items():
        loops = snap.loops[sector]
        walls = [w for loop in loops for w in loop]
        rings = [[snap.pos[w] for w in loop] for loop in loops]
        outer = max(range(len(rings)), key=lambda i: abs(_signed(rings[i])))
        outer_positive = _signed(rings[outer]) > 0
        segments = [(*snap.segment(w), w) for w in walls]
        vertices = {p for ring in rings for p in ring}
        for polygon, _spec in made:
            vertices |= set(_vertices(polygon))
        uncovered = [i for i, (_p, spec) in enumerate(made) if spec is None]
        keeper = max(uncovered or range(len(made)), key=lambda i: made[i][0].area)
        order = [keeper] + [i for i in range(len(made)) if i != keeper]
        shapes_of[sector] = []
        for rank, index in enumerate(order):
            polygon, spec = made[index]
            if rank == 0:
                target, obj = sector, disk.sectors[sector]
            else:
                target = len(new_sectors)
                source = disk.sectors[sector]
                # a shade-only XSECTOR goes with every piece: each animates
                # around its own shade, in the same phase as the rest
                obj = DiskObject(fields=dict(_f(source)),
                                 extra=copy.deepcopy(source.extra) if shade_only(source) else None)
                if obj.extra is None:
                    obj.fields["extra"] = -1
                else:
                    # its own XSECTOR: a fresh index, and a reference to itself
                    next_extra[0] += 1
                    obj.fields["extra"] = next_extra[0]
                    if "reference" in obj.extra.fields:
                        obj.extra.fields["reference"] = target
                new_sectors.append(obj)
                report["parent"][target] = sector
            if spec is not None:
                for key in SURFACE_FIELDS:
                    _f(obj)[key] = original[sector][key]
                _apply(obj, spec)
            shapes_of[sector].append((target, polygon))
            loops_out = []
            for k, ring in enumerate((polygon.exterior, *polygon.interiors)):
                points = _ring(ring.coords,
                               positive=outer_positive if k == 0 else not outer_positive)
                loop = []
                for i, a in enumerate(points):
                    b = points[(i + 1) % len(points)]
                    template = next((w for p, q, w in segments if _covers(p, q, a, b)), None)
                    if template is None:
                        # a seam between pieces: a neighbour's corner rounded half a
                        # unit off this edge still splits it, or the two sides of the
                        # seam would not meet wall for wall (a kink nobody sees)
                        cuts = {v for v in vertices if _near_on(a, b, v)}
                    else:
                        cuts = {v for v in vertices if _on(a, b, v)}
                    if template is not None:
                        cuts |= {v for v in inserts.get(template, ()) if _on(a, b, v)}
                    chain = [a, *sorted(cuts, key=lambda v: (v[0] - a[0]) ** 2
                                        + (v[1] - a[1]) ** 2), b]
                    loop += [(s, t, template, sector) for s, t in zip(chain, chain[1:])]
                if k == 0 and sector in hinge_of:
                    # the piece's first wall on the hinge line, running the
                    # hinge's way: the slope is then the parent's plane
                    hp, hq = hinge_of[sector]
                    hx, hy = hq[0] - hp[0], hq[1] - hp[1]
                    hlen = (hx * hx + hy * hy) ** 0.5
                    start = next(i for i, (s, t, _tp, _g) in enumerate(loop)
                                 if all(abs(hx * (v[1] - hp[1]) - hy * (v[0] - hp[0])) <= hlen
                                        for v in (s, t))
                                 and (t[0] - s[0]) * hx + (t[1] - s[1]) * hy > 0)
                    loop = loop[start:] + loop[:start]
                loops_out.append(loop)
            layout_loops[target] = loops_out
        report["sectors"] += 1
        report["pieces"] += len(made)

    # --- the walls, laid out again ------------------------------------------
    new_walls: list = []
    by_template: dict = {}
    seams: dict = {}
    owner_of: dict[int, int] = {}
    pending: list = []
    for index, obj in enumerate(new_sectors):
        if index in layout_loops:
            loops = layout_loops[index]
        else:
            loops = []
            for loop in snap.loops[index]:
                out = []
                for wall in loop:
                    a, b = snap.segment(wall)
                    cuts = sorted((v for v in inserts.get(wall, ()) if _on(a, b, v)),
                                  key=lambda v: (v[0] - a[0]) ** 2 + (v[1] - a[1]) ** 2)
                    chain = [a, *cuts, b]
                    out += [(s, t, wall, None) for s, t in zip(chain, chain[1:])]
                loops.append(out)
        f = _f(obj)
        f["wall_ptr"] = len(new_walls)
        count = 0
        for loop in loops:
            first = len(new_walls)
            for i, (a, b, template, group) in enumerate(loop):
                if template is not None:
                    whole = (a, b) == snap.segment(template)
                    if whole:
                        wall = disk.walls[template]
                    else:
                        if disk.walls[template].extra is not None:
                            raise OverlayError(f"wall {template} carries an XWALL and would be split")
                        wall = DiskObject(fields=dict(snap.fields[template]), extra=None)
                        _f(wall)["extra"] = -1
                        _split_texture(_f(wall), snap.fields[template], *snap.segment(template), a, b)
                        report["walls_split"] += 1
                    by_template[(template, a, b)] = len(new_walls)
                else:
                    seed = snap.fields[snap.loops[group][0][0]]
                    wall = DiskObject(fields=dict(seed), extra=None)
                    # never drawn (one floor and ceiling both sides); a repeat
                    # of 32 is 256 texels, a whole number of any tile, so each
                    # seam's texture runs on into the next (`texture_frame.
                    # join_continues`) and the joins' statistics stay honest
                    _f(wall).update(cstat=0, extra=-1, over_picnum=0, type=0, hitag=0,
                                    x_panning=0, y_panning=0, y_repeat=8, x_repeat=32)
                    seams[(group, a, b)] = len(new_walls)
                    report["seams"] += 1
                wf = _f(wall)
                wf["x"], wf["y"] = a
                wf["point2"] = first + (i + 1) % len(loop)
                owner_of[len(new_walls)] = index
                pending.append((len(new_walls), template, a, b, group))
                new_walls.append(wall)
            _chain_texture(new_walls, first, loop, snap)
            count += len(loop)
        f["wall_count"] = count

    for wall_index, template, a, b, group in pending:
        wf = _f(new_walls[wall_index])
        if template is None:
            twin = seams.get((group, b, a))
            if twin is None:
                raise OverlayError(f"a seam of sector {group} from {a} to {b} has no twin")
        else:
            old_twin = snap.next_wall[template]
            if old_twin < 0:
                wf["next_wall"], wf["next_sector"] = -1, -1
                continue
            twin = by_template.get((old_twin, b, a))
            if twin is None:
                raise OverlayError(
                    f"wall {template} from {a} to {b} lost its twin (wall {old_twin})")
        wf["next_wall"], wf["next_sector"] = twin, owner_of[twin]

    disk.walls[:] = new_walls
    disk.sectors[:] = new_sectors

    # sprites, and the player, stand in the piece under them
    for sprite in disk.sprites:
        sf = _f(sprite)
        if int(sf["sector"]) in shapes_of:
            sf["sector"] = _piece_at(shapes_of[int(sf["sector"])], int(sf["x"]), int(sf["y"]))
    header = disk.header
    if int(header.get("start_sector", -1)) in shapes_of:
        header["start_sector"] = _piece_at(shapes_of[int(header["start_sector"])],
                                           int(header["start_x"]), int(header["start_y"]))
    report["refused"] = {str(k): v for k, v in report["refused"].items()}
    report["parent"] = {str(k): v for k, v in report["parent"].items()}
    return report


def _apply(sector, spec) -> None:
    fields = _f(sector)
    for key, value in spec.surface.items():
        fields[key] = int(value)
    if spec.floor_shade_offset:
        fields["floor_shade"] = max(-128, min(63, int(fields["floor_shade"])
                                              + int(spec.floor_shade_offset)))


#: XSECTOR fields that only animate a sector's shade: no channel, no motion,
#: no trigger. A sector carrying nothing else may be cut, and every piece
#: carries the same animation (`cut_sectors`).
SHADE_ANIMATION = frozenset({
    "amplitude", "shade_frequency", "shade_phase", "shade_wave", "shade_always",
    "shade_floor", "shade_ceiling", "shade_walls", "shade_pal",
    "reference", "marker_0", "marker_1", "state",
    # a surface's current and its water: per sector, nothing moves, and each
    # piece copies them exactly (E3M3's channels pan and drag; the sewer's
    # walks stood beside them uncut because a panning neighbour counted as busy)
    "pan_floor", "pan_ceiling", "pan_always", "pan_velocity", "pan_angle", "drag", "depth",
})


def shade_only(sector) -> bool:
    """A sector whose XSECTOR (if any) does nothing but animate its surface: its shade, its current, its water's depth."""
    from .model import record_extra

    if int(_f(sector)["extra"]) <= 0:
        return True
    extra = record_extra(sector) or {}
    return all(not value or key in SHADE_ANIMATION for key, value in extra.items())


def _piece_at(shapes, x: int, y: int) -> int:
    from shapely.geometry import Point

    point = Point(x, y)
    for target, polygon in shapes:
        if polygon.covers(point):
            return target
    return min(shapes, key=lambda item: item[1].distance(point))[0]


def _chain_texture(new_walls, first: int, loop, snap) -> None:
    """The parts of one split wall continue its texture exactly, end to end.

    Rounding each part's repeat on its own drifts its end a texel or so off
    the next part's start (`texture_frame.join_continues` reads that as a
    broken material, and a city with hundreds of split walls fails the
    campaign's continuity floor). So each part starts where the one before it
    ends, and the last takes what repeat is left: the run ends where the whole
    wall did, and its join to the next wall is untouched.
    """
    k = 0
    while k < len(loop):
        a, b, template, _group = loop[k]
        if template is None or (a, b) == snap.segment(template):
            k += 1
            continue
        run = [k]
        while (k + len(run) < len(loop) and loop[k + len(run)][2] == template):
            run.append(k + len(run))
        if len(run) > 1:
            source = snap.fields[template]
            total = int(source["x_repeat"])
            ta, tb = snap.segment(template)
            whole = math.hypot(tb[0] - ta[0], tb[1] - ta[1]) or 1.0
            starts_at_origin = loop[run[0]][0] == ta
            pan = int(_f(new_walls[first + run[0]])["x_panning"])
            used = 0
            for j, idx in enumerate(run):
                wf = _f(new_walls[first + idx])
                pa, pb = loop[idx][0], loop[idx][1]
                if j == len(run) - 1 and starts_at_origin and loop[run[-1]][1] == tb:
                    rep = max(1, total - used)
                else:
                    rep = max(1, int(round(total * math.hypot(pb[0] - pa[0], pb[1] - pa[1]) / whole)))
                wf["x_repeat"] = min(255, rep)
                wf["x_panning"] = pan % _tile_width(int(wf["picnum"]))
                pan += rep * 8
                used += rep
        k += len(run)


def _split_texture(wf, source, ta, tb, a, b) -> None:
    """A part of a wall keeps the texture where it was on the whole wall."""
    length = math.hypot(tb[0] - ta[0], tb[1] - ta[1])
    if length <= 0:
        return
    d0 = math.hypot(a[0] - ta[0], a[1] - ta[1])
    d1 = math.hypot(b[0] - ta[0], b[1] - ta[1])
    if int(source["cstat"]) & 8:                  # x-flipped: u runs from the far end
        d0, d1 = length - d1, length - d0
    repeat = int(source["x_repeat"])
    wf["x_repeat"] = max(1, min(255, int(round(repeat * (d1 - d0) / length))))
    wf["x_panning"] = ((int(source["x_panning"]) + int(round(repeat * 8 * d0 / length)))
                       % _tile_width(int(source["picnum"])))


def _tile_width(picnum: int) -> int:
    """A tile's width in texels, the period of its x panning (256 when unknown).

    The engine wraps panning at the tile's width, and `texture_frame.
    join_continues` compares panning modulo it: a part stored as 200 on a
    64-wide tile is drawn where 8 is, but reads as a broken join."""
    try:
        from .shade_table import _art

        tile = _art().get(int(picnum))
        if tile is not None and tile.width:
            return int(tile.width)
    except Exception:
        pass
    return 256
