"""Read rings, concentric floors, round rooms and common facings from Blood map geometry."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import atan2, cos, hypot, pi, radians, sin, sqrt, tan, tau
from statistics import mean, median
from typing import Iterable, Mapping, Sequence

from .blood_types import hidden_in_single_player, sprite_visibility
from .model import DiskMap, record_extra, record_fields
from .planar_geom import area2, orientation, point_in_loop, proper_crossing
from .player_space import PLAYER_PROFILES
from .reachability import ReachabilityError, sector_kinds
from .render_slots import surface_z
from .sector_geom import outline_and_holes, sector_walls
from .sight import wall_occludes_sight

BODY = PLAYER_PROFILES["blood"]
# Same convention as the catalogue's place profiles: 16 z units per plan unit,
# with the standing player represented as 1.8 metres.
PLAN_UNITS_PER_METRE = BODY.standing_height / 16 / 1.8

RING_MIN_RADIUS = BODY.body_width / 4
RING_HEIGHT_SPREAD = BODY.max_step // 2
RING_RADIUS_ERROR = 0.055
RING_SLOT_ERROR = 0.13  # fraction of one nominal angular interval
LARGE_COMPLETE_RING_SLOT_ERROR = 0.24
FOUR_MEMBER_RING_SLOT_ERROR = 0.085
RING_MAX_MISSING = 2
RING_SEED_NEIGHBOURS = 8
SQUARE_ANGLE_ERROR = 0.075
RECTANGLE_OPPOSITE_ERROR = radians(5)
GRID_POSITION_ERROR = 0.14
GRID_ORTHOGONAL_ERROR = 0.17  # absolute cosine between lattice axes
GRID_INDEX_ERROR = 0.21       # nearest lattice index, in grid steps
GRID_NEIGHBOURS = 24
CENTRE_CONTENTS_RADIUS = 0.4

NEST_CENTRE_ERROR = 0.175  # relative to the smaller level's radius
NEST_MIN_GROWTH = 1.045
ROUND_MIN_RADIUS = BODY.body_width * 2
ROUND_MIN_SIDES = 8
ROUND_RADIUS_ERROR = 0.115
ROUND_MAX_GAP = radians(60)
ROUND_EDGE_RADIUS = 0.79
PILLAR_MAX_AREA = 0.12  # of the host outline
PILLAR_MAX_RADIUS = 0.38  # of the circle traced by the pillar centres
PILLAR_SLOT_ERROR = 0.16

FOCUS_ANGLE_ERROR = radians(8)
FOCUS_SLOPE_ERROR = tan(FOCUS_ANGLE_ERROR)
FOCUS_MIN_CROSSING = sin(radians(16))
FOCUS_MIN_DISTANCE = BODY.body_width / 4
GROUP_CENTRE_ERROR = 0.20
GROUP_SHARED_SPRITES = 0.75

Point = tuple[int, int]
XY = tuple[float, float]
Member = tuple[str, int]


def _distance(a: XY, b: XY) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


def _gaps(points: Sequence[XY], centre: XY) -> list[float]:
    angles = sorted(atan2(y - centre[1], x - centre[0]) for x, y in points)
    return [b - a for a, b in zip(angles, angles[1:] + [angles[0] + tau])]


@dataclass(frozen=True)
class _Shape:
    centre: XY
    radius: float
    area: float
    points: tuple[Point, ...]
    bounds: tuple[int, int, int, int]

    @classmethod
    def of(cls, loop: Sequence[Point]) -> _Shape | None:
        # Drop subdivided straight walls before measuring how many sides the
        # builder drew. Keep their native wall ids separately for topology.
        loop = [p for a, p in zip(loop[-1:] + loop[:-1], loop) if a != p]
        points = tuple(p for a, p, b in zip(loop[-1:] + loop[:-1], loop, loop[1:] + loop[:1])
                       if orientation(a, p, b))
        area = area2(points)
        if not area:
            return None
        edges = zip(points, points[1:] + points[:1])
        x0, y0 = points[0]
        sx = sy = 0
        for (x, y), (nx, ny) in edges:
            x, y, nx, ny = x - x0, y - y0, nx - x0, ny - y0
            cross = x * ny - nx * y
            sx += (x + nx) * cross
            sy += (y + ny) * cross
        centre = x0 + sx / (3 * area), y0 + sy / (3 * area)
        radius = mean(_distance(p, centre) for p in points)
        xs, ys = zip(*points)
        return cls(centre, radius, abs(area) / 2, points,
                   (min(xs), min(ys), max(xs), max(ys)))

    def contains(self, xy: XY) -> bool:
        x, y = xy
        a, b, c, d = self.bounds
        return a <= x <= c and b <= y <= d and point_in_loop(xy, self.points) != 0

    def circularity(self) -> float | None:
        if len(self.points) < ROUND_MIN_SIDES or not self.contains(self.centre):
            return None
        error = max(abs(_distance(p, self.centre) / self.radius - 1) for p in self.points)
        if error > ROUND_RADIUS_ERROR or max(_gaps(self.points, self.centre)) > ROUND_MAX_GAP:
            return None
        # A long chord may have vertices at the right distance. Measure
        # the nearest point on the actual segment, including short jambs.
        x, y = self.centre
        for (ax, ay), (bx, by) in zip(self.points, self.points[1:] + self.points[:1]):
            dx, dy = bx - ax, by - ay
            if not dx and not dy:                          # a community map may repeat a corner
                continue
            along = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            distance = hypot(ax + along * dx - x, ay + along * dy - y)
            if distance < self.radius * ROUND_EDGE_RADIUS:
                return None
        return 1 - error


@dataclass(frozen=True)
class _Site:
    member: Member
    xy: XY
    z: int
    size: float = 0  # equivalent radius of a pillar footprint


@dataclass(frozen=True)
class _Circle:
    centre: XY
    radius: float
    sites: tuple[_Site, ...]
    missing: int
    regularity: float


@dataclass(frozen=True)
class _Level:
    sectors: tuple[int, ...]
    shape: _Shape
    outer: frozenset[int]
    holes: tuple[frozenset[int], ...]


class _Geometry:
    def __init__(self, disk: DiskMap):
        self.disk = disk
        self.sectors = [record_fields(s) for s in disk.sectors]
        self.walls = [record_fields(w) for w in disk.walls]
        self.sprites = [record_fields(s) for s in disk.sprites]
        self.xy = [(w["x"], w["y"]) for w in self.walls]
        self.runs = [tuple(sector_walls(disk, i)) for i in range(len(self.sectors))]
        self.owners = {w: s for s, run in enumerate(self.runs) for w in run}
        self.portals = {w: int(self.walls[w]["next_wall"]) for w in self.owners
                        if self._paired(w)}
        self.levels: dict[tuple[int, ...], _Level | None] = {}
        self.holes: dict[int, list[list[Point]]] = {}
        self.shapes: dict[int, _Shape] = {}
        self.open_neighbours: dict[int, set[int]] = defaultdict(set)
        try:
            self.offstage = {s for s, kind in sector_kinds(disk).items()
                             if kind in ("logic_closet", "signature")}
        except ReachabilityError:
            # A malformed start does not invalidate unrelated geometry.
            self.offstage = set()
        for i, run in enumerate(self.runs):
            outline, holes = outline_and_holes(disk, i)
            shape = _Shape.of(outline)
            if shape is None:
                continue
            self.shapes[i] = shape
            self.holes[i] = holes
            # Index actual directed edges, retaining the ids even on a cut
            # wall that is collinear with the following segment.
            edges = {self._edge(w): w for w in run if w in self.owners
                     and self.walls[w]["point2"] in self.owners}
            boundaries = tuple(frozenset(edges[a, b] for a, b in zip(loop, loop[1:] + loop[:1])
                                         if (a, b) in edges) for loop in [outline, *holes])
            self.levels[i,] = _Level((i,), shape, boundaries[0], boundaries[1:])
            for w in run:
                if w not in self.portals:
                    continue
                other = self.owners[self.portals[w]]
                a, b = self.sectors[i], self.sectors[other]
                if (min(a["floor_z"], b["floor_z"]) > max(a["ceiling_z"], b["ceiling_z"])
                        and not wall_occludes_sight(self.walls[w])):
                    self.open_neighbours[i].add(other)
        self.by_sector: dict[int, list[int]] = defaultdict(list)
        self.dudes: set[int] = set()
        for i, (sprite, raw) in enumerate(zip(self.sprites, disk.sprites)):
            extra = record_extra(raw) or {}
            kind = sprite["type"]
            visibility = sprite_visibility(kind, sprite["cstat"])
            if (sprite["sector"] not in self.shapes or sprite["sector"] in self.offstage
                    or visibility["kind"] != "visible" or sprite["picnum"] < 0
                    or hidden_in_single_player(kind, sprite["status"], extra.get("launch_single", 0))
                    or not (sprite.get("x_repeat", 1) and sprite.get("y_repeat", 1))):
                continue
            self.by_sector[sprite["sector"]].append(i)
            if visibility["category"] == "dude":
                self.dudes.add(i)

    def _edge(self, wall: int) -> tuple[Point, Point]:
        return self.xy[wall], self.xy[self.walls[wall]["point2"]]

    def _paired(self, wall: int) -> bool:
        a = self.walls[wall]
        other = a["next_wall"]
        return (other in self.owners and self.owners[other] == a["next_sector"]
                and self.walls[other]["next_wall"] == wall
                and self.walls[other]["next_sector"] == self.owners[wall]
                and a["point2"] in self.owners and self.walls[other]["point2"] in self.owners
                and self._edge(wall) == self._edge(other)[::-1])

    def site(self, sprite: int) -> _Site:
        fields = self.sprites[sprite]
        return _Site(("sprite", sprite), (fields["x"], fields["y"]), fields["z"])

    def level(self, sectors: Iterable[int]) -> _Level | None:
        ids = tuple(sorted(sectors))
        if ids not in self.levels:
            self.levels[ids] = self._union(ids) if len(ids) > 1 else None
        return self.levels[ids]

    def _union(self, sectors: tuple[int, ...]) -> _Level | None:
        """Trace boundary wall successors, crossing each internal portal at its vertex."""
        walls = {w for s in sectors for w in self.runs[s]}
        boundary = {w for w in walls if self.portals.get(w) not in walls}
        left = boundary.copy()
        loops = []
        while left:
            start = min(left)
            loop, current = [], start
            while current in left:
                left.remove(current)
                loop.append(current)
                current = self.walls[current]["point2"]
                crossed = set()
                while current in walls and current not in boundary and current not in crossed:
                    crossed.add(current)
                    current = self.walls[self.portals[current]]["point2"]
            if current != start or len(loop) < 3:
                return None
            loops.append(loop)
        if not loops:
            return None
        loops.sort(key=lambda loop: abs(area2([self.xy[w] for w in loop])), reverse=True)
        shape = _Shape.of([self.xy[w] for w in loops[0]])
        # Multiple disjoint outer boundaries are not one enclosing level.
        if shape is None or any(not shape.contains(self.xy[w]) for loop in loops[1:] for w in loop):
            return None
        return _Level(sectors, shape, frozenset(loops[0]), tuple(map(frozenset, loops[1:])))

    def primary(self, level: _Level) -> int:
        return max(level.sectors, key=lambda s: (self.shapes[s].area, -s))

    def floor(self, sector: int) -> dict:
        s = self.sectors[sector]
        return {"floor_tile": s["floor_picnum"], "floor_shade": s["floor_shade"],
                "floor_z": s["floor_z"], "type": s["type"], "sloped": bool(s["floor_stat"] & 2)}

    def at(self, xy: XY, z: int, scope: set[int]) -> int | None:
        # Prefer the same stack even when a remote layer overlaps it in plan.
        hits = [s for s in scope if s in self.shapes and self.shapes[s].contains(xy)
                and not any(point_in_loop(xy, h) == 1 for h in self.holes[s])]
        return min(hits, key=lambda s: (max(self.sectors[s]["ceiling_z"] - z, 0,
                                            z - self.sectors[s]["floor_z"]),
                                       abs(self.sectors[s]["floor_z"] - z), s), default=None)

    def wall_faces(self, walls: Iterable[int]) -> set[int]:
        return {self.owners[self.portals[w]] for w in walls if w in self.portals}

    def wires(self, members: Iterable[Member]) -> list[dict]:
        records = {"sector": self.disk.sectors, "sprite": self.disk.sprites, "wall": self.disk.walls}
        result = []
        for kind, index in sorted(set(members)):
            extra = record_extra(records[kind][index]) or {}
            tx, rx = extra.get("tx_id", 0), extra.get("rx_id", 0)
            if tx or rx:
                result.append({"kind": kind, "id": index, "tx_id": tx, "rx_id": rx})
        return result


def _circumcircle(a: XY, b: XY, c: XY) -> tuple[XY, float] | None:
    bx, by, cx, cy = b[0] - a[0], b[1] - a[1], c[0] - a[0], c[1] - a[1]
    d = 2 * (bx * cy - by * cx)
    if not d:
        return None
    bb, cc = bx * bx + by * by, cx * cx + cy * cy
    x, y = (cy * bb - by * cc) / d, (bx * cc - cx * bb) / d
    return (a[0] + x, a[1] + y), hypot(x, y)


def _fit_circle(sites: Sequence[_Site]) -> tuple[XY, float] | None:
    """Least-squares circle, shifting coordinates before forming the moments."""
    x, y = map(mean, zip(*(s.xy for s in sites)))
    xx = xy = yy = xr = yr = 0.0
    for site in sites:
        dx, dy = site.xy[0] - x, site.xy[1] - y
        rr = dx * dx + dy * dy
        xx += dx * dx
        yy += dy * dy
        xy += dx * dy
        xr += dx * rr / 2
        yr += dy * rr / 2
    det = xx * yy - xy * xy
    if det <= 0:
        return None
    centre = x + (xr * yy - yr * xy) / det, y + (yr * xx - xr * xy) / det
    return centre, mean(_distance(s.xy, centre) for s in sites)


def _circle_spacing(sites: Sequence[_Site], centre: XY, radius: float, *,
                    slot_error: float) -> tuple[int, float] | None:
    points = [s.xy for s in sites]
    radial_error = max(abs(_distance(p, centre) / radius - 1) for p in points)
    if radial_error > RING_RADIUS_ERROR:
        return None
    gaps = _gaps(points, centre)
    counts = range(len(points), len(points) + RING_MAX_MISSING + 1)
    if len(points) == 4:
        a, b, c, d = gaps
        if max(abs(a + b - pi), abs(b + c - pi), abs(c + d - pi)) <= RECTANGLE_OPPOSITE_ERROR:
            error = max(abs(g / (pi / 2) - 1) for g in gaps)
            return (0, 1 - max(error, radial_error)) if error <= SQUARE_ANGLE_ERROR else None
        counts = range(5, 5 + RING_MAX_MISSING)
    for count in counts:
        gaps_in_slots = [g * count / tau for g in gaps]
        slots = [round(g) for g in gaps_in_slots]
        error = max(abs(g - n) for g, n in zip(gaps_in_slots, slots))
        missing = count - len(points)
        tolerance = slot_error
        if missing and len(points) == 4:
            tolerance = FOUR_MEMBER_RING_SLOT_ERROR
        elif not missing and count >= 8:
            tolerance = max(tolerance, LARGE_COMPLETE_RING_SLOT_ERROR)
        if min(slots) >= 1 and sum(slots) == count and error <= tolerance:
            return missing, 1 - max(radial_error, error)
    return None


def _grid_square(circle: _Circle, sites: Sequence[_Site]) -> bool:
    """A four-corner cell with another pair extending either axis belongs to a grid."""
    if len(circle.sites) != 4 or circle.missing:
        return False
    x, y = circle.centre
    points = sorted((s.xy for s in circle.sites), key=lambda p: atan2(p[1] - y, p[0] - x))
    height = median(s.z for s in circle.sites)
    others = [s.xy for s in sites if s not in circle.sites and abs(s.z - height) <= RING_HEIGHT_SPREAD]
    for index, a in enumerate(points):
        b, d = points[(index + 1) % 4], points[(index + 3) % 4]
        dx, dy = d[0] - a[0], d[1] - a[1]
        targets = [(b[0] - dx, b[1] - dy), (a[0] - dx, a[1] - dy)]
        if all(any(_distance(p, t) <= circle.radius * GRID_POSITION_ERROR for p in others)
               for t in targets):
            return True
    return False


def _grid_members(sites: Sequence[_Site]) -> set[_Site]:
    """Find sites on near-complete 3 by 3 patches of an orthogonal lattice."""
    marked = set()
    for origin in sites:
        neighbours = sorted((s for s in sites if s.xy != origin.xy
                             and abs(s.z - origin.z) <= RING_HEIGHT_SPREAD),
                            key=lambda s: _distance(s.xy, origin.xy))[:GRID_NEIGHBOURS]
        if len(neighbours) < 7:
            continue
        x, y = origin.xy
        offsets = [(s.xy[0] - x, s.xy[1] - y, s) for s in neighbours]
        for (ax, ay, _), (bx, by, _) in combinations(offsets[:RING_SEED_NEIGHBOURS], 2):
            if abs(ax * bx + ay * by) > GRID_ORTHOGONAL_ERROR * hypot(ax, ay) * hypot(bx, by):
                continue
            det = ax * by - ay * bx
            cells = {(0, 0): origin}
            for dx, dy, site in offsets:
                u, v = (dx * by - dy * bx) / det, (ax * dy - ay * dx) / det
                i, j = round(u), round(v)
                if max(abs(i), abs(j)) <= 1 and max(abs(i - u), abs(j - v)) <= GRID_INDEX_ERROR:
                    cells.setdefault((i, j), site)
            if len(cells) >= 8:
                marked.update(cells.values())
                break
    return marked


def _circles(sites: Sequence[_Site], *, pillars: bool = False) -> list[_Circle]:
    """Seed from local triples, fit all sites in each radial band, then keep disjoint rings."""
    if len(sites) < 4:
        return []
    span = hypot(max(s.xy[0] for s in sites) - min(s.xy[0] for s in sites),
                 max(s.xy[1] for s in sites) - min(s.xy[1] for s in sites))
    checked, refined = set(), set()
    candidates = []
    for anchor in sites:
        near = sorted((s for s in sites if s.xy != anchor.xy
                       and abs(s.z - anchor.z) <= RING_HEIGHT_SPREAD),
                      key=lambda s: _distance(s.xy, anchor.xy))[:RING_SEED_NEIGHBOURS]
        for b, c in combinations(near, 2):
            fit = _circumcircle(anchor.xy, b.xy, c.xy)
            if fit is None:
                continue
            centre, radius = fit
            if not RING_MIN_RADIUS <= radius <= span:
                continue
            z = median((anchor.z, b.z, c.z))
            key = (*[round(v / 4) for v in centre], round(radius / 4), z)
            if key in checked:
                continue
            checked.add(key)
            cohort = tuple(s for s in sites if abs(s.z - z) <= RING_HEIGHT_SPREAD
                           and abs(_distance(s.xy, centre) / radius - 1) <= RING_RADIUS_ERROR * 1.4)
            if len(cohort) < 4 or cohort in refined:
                continue
            refined.add(cohort)
            fit = _fit_circle(cohort)
            if fit is None:
                continue
            centre, radius = fit
            if radius < RING_MIN_RADIUS or max(s.z for s in cohort) - min(s.z for s in cohort) > RING_HEIGHT_SPREAD:
                continue
            spacing = _circle_spacing(cohort, centre, radius,
                                      slot_error=PILLAR_SLOT_ERROR if pillars else RING_SLOT_ERROR)
            if spacing is None or (pillars and (spacing[0] or max(s.size for s in cohort)
                                                > PILLAR_MAX_RADIUS * radius)):
                continue
            circle = _Circle(centre, radius, cohort, *spacing)
            if not _grid_square(circle, sites):
                candidates.append(circle)
    if candidates and len(sites) >= 8:
        lattice = _grid_members(sites)
        candidates = [circle for circle in candidates
                      if len(lattice.intersection(circle.sites)) < 0.75 * len(circle.sites)]
    selected, used = [], set()
    for circle in sorted(candidates, key=lambda c: (-len(c.sites), c.missing, -c.regularity, c.radius)):
        if used.intersection(circle.sites):
            continue
        concentric = {s for other in candidates
                      if other.radius < circle.radius * (1 - 2 * RING_RADIUS_ERROR)
                      and _distance(other.centre, circle.centre) <= GROUP_CENTRE_ERROR * other.radius
                      for s in other.sites}
        height = median(s.z for s in circle.sites)
        # Repeated fixtures between the centre and circumference are evidence
        # for a filled pattern. A separately fitted inner ring explains them.
        interior = [s for s in sites if s not in circle.sites and s not in concentric
                    and abs(s.z - height) <= RING_HEIGHT_SPREAD
                    and CENTRE_CONTENTS_RADIUS * circle.radius < _distance(s.xy, circle.centre)
                    < (1 - RING_RADIUS_ERROR) * circle.radius]
        # A sparse four-member fit needs a clean annulus. In the campaign
        # these are otherwise likely to be four actors picked out of a crowd.
        allowed = 0 if len(circle.sites) == 4 and circle.missing else 1
        if len(interior) <= allowed:
            selected.append(circle)
            used.update(circle.sites)
    return selected


def _nests(geom: _Geometry) -> list[tuple[_Level, ...]]:
    """Grow from the centre across complete portal rims, keeping maximal chains."""
    chains = set()
    for sector in geom.shapes:
        if sector in geom.offstage:
            continue
        inner = geom.level((sector,))
        chain = [inner]
        while inner.outer and all(w in geom.portals for w in inner.outer):
            rim = frozenset(geom.portals[w] for w in inner.outer)
            outside = geom.wall_faces(inner.outer)
            if outside & geom.offstage or outside.intersection(s for level in chain for s in level.sectors):
                break
            if len({geom.sectors[s]["floor_z"] for s in outside}) != 1:
                break
            outer = geom.level(outside)
            if outer is None or rim not in outer.holes:
                break
            a, b = inner.shape, outer.shape
            if (b.area < NEST_MIN_GROWTH * a.area
                    or _distance(chain[0].shape.centre, b.centre) > NEST_CENTRE_ERROR * a.radius
                    or not b.contains(chain[0].shape.centre)):
                break
            chain.append(outer)
            inner = outer
        if len(chain) > 1:
            chains.add(tuple(reversed(chain)))
    # An intermediate regular annulus also seeds a chain. Count its steps
    # once, on the longest reading that reaches its innermost floor.
    longest = []
    prefixes = set()
    for chain in sorted(chains, key=lambda c: (-len(c), tuple(level.sectors for level in c))):
        if chain not in prefixes:
            longest.append(chain)
            prefixes.update(chain[:i] for i in range(1, len(chain)))
    return longest


def _nest_data(geom: _Geometry, chain: Sequence[_Level], host: int) -> tuple[str, list[dict]] | None:
    levels, steps, surfaces = [], [], set()
    previous = geom.sectors[host]["floor_z"]
    for level in chain:
        representative = geom.primary(level)
        floor = geom.floor(representative)
        step = previous - floor["floor_z"]
        previous = floor["floor_z"]
        steps.append(step)
        row = {"sector": representative, "sectors": list(level.sectors),
               "sides": len(level.shape.points), "radius": round(level.shape.radius, 1),
               "floor_step": step, **floor}
        variants = []
        for sector in level.sectors:
            other = geom.floor(sector)
            surfaces.add((other["floor_tile"], other["floor_shade"]))
            if other != floor:
                variants.append({"sector": sector, **other})
        if variants:
            row["surface_variants"] = variants
        levels.append(row)
    signs = {(step > 0) - (step < 0) for step in steps if step}
    if not signs and len(surfaces) < 2:
        return None
    name = {(): "flat", (-1,): "pit", (1,): "dais", (-1, 1): "mixed"}[tuple(sorted(signs))]
    return name, levels


def _pillar_sites(geom: _Geometry, host: int) -> list[_Site]:
    level = geom.level((host,))
    floor = geom.sectors[host]["floor_z"]
    sites = []
    for loop, walls in zip(geom.holes[host], level.holes):
        shape = _Shape.of(loop)
        if shape is None or not walls or shape.area > PILLAR_MAX_AREA * level.shape.area:
            continue
        islands = geom.wall_faces(walls)
        if all(geom.walls[w]["next_sector"] < 0 for w in walls):
            member = ("wall", min(walls))
        elif len(islands) == 1 and all(w in geom.portals for w in walls):
            island = next(iter(islands))
            if (geom.wall_faces(w for w in geom.runs[island] if w in geom.portals) != {host}
                    or geom.sectors[island]["floor_z"] == floor):
                continue
            member = ("sector", island)
        else:
            continue
        z = geom.sectors[member[1]]["floor_z"] if member[0] == "sector" else floor
        sites.append(_Site(member, shape.centre, z, sqrt(shape.area / pi)))
    return sites


def _room_windows(geom: _Geometry, nests: Sequence[Sequence[_Level]]) -> dict[frozenset[int], int]:
    """A local room comprises its floor, openings to neighbours and enclosed bands."""
    windows = {}
    for host in sorted(geom.shapes.keys() - geom.offstage, key=lambda s: (-geom.shapes[s].area, s)):
        scope = frozenset({host, *geom.open_neighbours[host]})
        windows.setdefault(scope, host)
    for chain in nests:
        scope = frozenset(s for level in chain for s in level.sectors)
        host = geom.primary(chain[0])
        windows.setdefault(scope | frozenset(geom.open_neighbours[host]), host)
    return windows


def _sprite_rings(geom: _Geometry, windows: Mapping[frozenset[int], int]) -> Iterable[dict]:
    cohorts = {}
    for scope, host in windows.items():
        families = defaultdict(list)
        for sector in sorted(scope):
            for i in geom.by_sector[sector]:
                sprite = geom.sprites[i]
                families["picnum", sprite["picnum"]].append(i)
                if i in geom.dudes:
                    families["dude_type", sprite["type"]].append(i)
        for (by, _), ids in families.items():
            if len(ids) >= 4:
                cohorts.setdefault((by, tuple(sorted(ids))), []).append((scope, host))
    found = {}
    for (by, ids), rooms in cohorts.items():
        for circle in _circles([geom.site(i) for i in ids]):
            members = tuple(s.member for s in circle.sites)
            z = round(median(s.z for s in circle.sites))
            kind = "square" if len(members) == 4 and circle.missing == 0 else "ring"
            fallback = None
            for scope, host in rooms:
                if geom.at(circle.centre, z, scope) is not None:
                    break
                # The first window may miss an inset floor that a nest's
                # window includes. A genuine solid island is still a centre.
                if fallback is None and any(geom.shapes[s].contains(circle.centre) for s in scope):
                    fallback = scope, host
            else:
                if fallback is None:
                    continue
                scope, host = fallback
            row = _record(geom, kind, circle.centre, z, host, set(scope), members,
                          circle.radius, circle.regularity, by=by,
                          missing=circle.missing, expected_count=len(members) + circle.missing)
            found.setdefault(members, row)
    # Different room windows can see a subset of the same ring; a dude type
    # can also recover a ring whose frames have different tiles.
    present = set()
    for members, row in sorted(found.items(), key=lambda item: (-item[1]["count"],
                              -item[1]["regularity"], item[0])):
        if len(present.intersection(members)) <= 1:
            present.update(members)
            yield row


@dataclass(frozen=True)
class _Ray:
    site: _Site
    direction: XY

    def aims_at(self, centre: XY) -> bool:
        x, y = centre[0] - self.site.xy[0], centre[1] - self.site.xy[1]
        dx, dy = self.direction
        forward = x * dx + y * dy
        return (forward > 0 and x * x + y * y >= FOCUS_MIN_DISTANCE ** 2
                and abs(x * dy - y * dx) <= forward * FOCUS_SLOPE_ERROR)

    def error(self, centre: XY) -> float:
        x, y = centre[0] - self.site.xy[0], centre[1] - self.site.xy[1]
        dx, dy = self.direction
        return abs(atan2(x * dy - y * dx, x * dx + y * dy))


def _ray_intersection(rays: Sequence[_Ray]) -> XY | None:
    # Minimize squared perpendicular distance to the focus lines. For two
    # rays this is their intersection, for more it averages mapping jitter.
    x, y = rays[0].site.xy
    xx = xy = yy = xr = yr = 0.0
    for ray in rays:
        dx, dy = ray.direction
        nx, ny = -dy, dx
        dot = (ray.site.xy[0] - x) * nx + (ray.site.xy[1] - y) * ny
        xx += nx * nx
        xy += nx * ny
        yy += ny * ny
        xr += nx * dot
        yr += ny * dot
    det = xx * yy - xy * xy
    if det <= FOCUS_MIN_CROSSING ** 2:
        return None
    return x + (xr * yy - yr * xy) / det, y + (yr * xx - xr * xy) / det


def _room_boundaries(geom: _Geometry, scope: frozenset[int]) -> list[tuple[Point, Point]]:
    return [geom._edge(w) for sector in sorted(scope) for w in geom.runs[sector]
            if geom.walls[w]["point2"] in geom.owners
            and (w not in geom.portals or geom.owners[geom.portals[w]] not in scope
                 or geom.owners[geom.portals[w]] not in geom.open_neighbours[sector]
                 or wall_occludes_sight(geom.walls[w]))]


def _clear_ray(a: XY, b: XY, boundary: Sequence[tuple[Point, Point]]) -> bool:
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return not any(not (max(p[0], q[0]) < x0 or min(p[0], q[0]) > x1
                        or max(p[1], q[1]) < y0 or min(p[1], q[1]) > y1)
                   and proper_crossing(a, b, p, q) for p, q in boundary)


def _focuses(geom: _Geometry, windows: Mapping[frozenset[int], int],
             directional_tiles: Iterable[int]) -> Iterable[dict]:
    directional = set(directional_tiles)
    rays = {}
    for ids in geom.by_sector.values():
        for i in ids:
            sprite = geom.sprites[i]
            if i in geom.dudes or sprite["cstat"] & 48 == 16 or sprite["picnum"] in directional:
                angle = sprite["angle"] * tau / 2048
                rays[i] = _Ray(geom.site(i), (cos(angle), sin(angle)))
    found = {}
    for scope, host in windows.items():
        nearby = [rays[i] for s in sorted(scope) for i in geom.by_sector[s] if i in rays]
        if len(nearby) < 4:
            continue
        boundary = _room_boundaries(geom, scope)
        room = set(scope)
        seen, checked = set(), set()
        for a, b in combinations(nearby, 2):
            point = _ray_intersection((a, b))
            if point is None or not (a.aims_at(point) and b.aims_at(point)):
                continue
            key = tuple(round(v / 16) for v in point)
            if key in checked:
                continue
            checked.add(key)
            aimed = tuple(r for r in nearby if r.aims_at(point))
            if len(aimed) < 4 or aimed in seen:
                continue
            seen.add(aimed)
            point = _ray_intersection(aimed)
            if point is None:
                continue
            visible = tuple(r for r in aimed if r.aims_at(point) and _clear_ray(r.site.xy, point, boundary))
            if visible != aimed:
                if len(visible) < 4:
                    continue
                aimed = visible
                point = _ray_intersection(aimed)
                if point is None or not all(r.aims_at(point) and _clear_ray(r.site.xy, point, boundary)
                                            for r in aimed):
                    continue
            zs = [r.site.z for r in aimed]
            z = round(median(zs))
            if max(zs) - min(zs) > BODY.standing_height or geom.at(point, z, room) is None:
                continue
            error = max(r.error(point) for r in aimed)
            members = tuple(sorted(r.site.member for r in aimed))
            radius = mean(_distance(r.site.xy, point) for r in aimed)
            row = _record(geom, "focus", point, z, host, room, members, radius,
                          1 - error / (pi / 2), by="facing")
            if members not in found or row["regularity"] > found[members]["regularity"]:
                found[members] = row
    present = set()
    for members, row in sorted(found.items(), key=lambda item: (-item[1]["count"],
                              -item[1]["regularity"], item[0])):
        if len(present.intersection(members)) <= 1:
            present.update(members)
            yield row


def _family(geom: _Geometry, members: Iterable[Member], by: str) -> dict:
    fields = {"sector": geom.sectors, "sprite": geom.sprites, "wall": geom.walls}
    tiles, types = set(), set()
    for kind, index in members:
        f = fields[kind][index]
        tiles.add(f["floor_picnum"] if kind == "sector" else f["picnum"])
        types.add(f["type"])
    return {"by": by, "picnums": sorted(tiles), "types": sorted(types)}


def _record(geom: _Geometry, kind: str, centre: XY, z: int, host: int, scope: set[int],
            members: Iterable[Member], radius: float, regularity: float, *,
            by: str = "geometry", count: int | None = None, **details) -> dict:
    members = tuple(sorted(set(members)))
    centre_sector = geom.at(centre, z, scope)
    floor, contrast = None, None
    centre_members = []
    if centre_sector is not None:
        floor = geom.floor(centre_sector)
        near_host, near_centre = geom.floor(host), floor
        # The first wall is the slope's reference even when the disk happens
        # to trace a hole first. The plane step is evaluated at the shared XY.
        x, y = map(round, centre)
        floor_zs = [surface_z(geom.disk, s, x, y)[1]
                    if geom.runs[s] and geom.walls[geom.runs[s][0]]["point2"] in geom.owners
                    else geom.sectors[s]["floor_z"] for s in (host, centre_sector)]
        floor["floor_step"] = floor_zs[0] - floor_zs[1]
        contrast = near_centre["floor_shade"] - near_host["floor_shade"]
        centre_members.append(("sector", centre_sector))
    base_z = floor["floor_z"] if floor else z
    host_z = geom.sectors[host]["floor_z"]
    contents = []
    for sector in sorted(scope):
        for sprite_id in geom.by_sector[sector]:
            sprite = geom.sprites[sprite_id]
            if ("sprite", sprite_id) in members:
                continue
            distance = _distance((sprite["x"], sprite["y"]), centre)
            if (distance <= CENTRE_CONTENTS_RADIUS * radius
                    and min(z, base_z, host_z) - BODY.standing_height <= sprite["z"]
                    <= max(z, base_z, host_z) + BODY.max_step):
                contents.append({"id": sprite_id, "picnum": sprite["picnum"],
                                 "type": sprite["type"], "distance": round(distance, 1)})
                centre_members.append(("sprite", sprite_id))
    contents.sort(key=lambda s: (s["distance"], s["id"]))
    wiring = geom.wires((*members, *centre_members))
    count = len(members) if count is None else count
    return {"kind": kind, "centre": [round(v, 1) for v in centre], "z": z,
            "centre_sector": centre_sector, "host_sector": host,
            "count": count, "radius": round(radius, 1),
            "radius_m": round(radius / PLAN_UNITS_PER_METRE, 2),
            "members": [{"kind": k, "id": i} for k, i in members],
            "family": _family(geom, members, by), "regularity": round(regularity, 4),
            "centre_contents": contents, "centre_floor": floor, "light_contrast": contrast,
            "wired": bool(wiring), "wiring": wiring,
            "score": _score(1, regularity, count), **details}


def _score(layers: int, regularity: float, count: int) -> float:
    return round(layers + 0.8 * regularity + 0.01 * min(count, 19), 4)


def _boundary_host(geom: _Geometry, level: _Level) -> int:
    exterior = [geom.owners[geom.portals[w]] for w in level.outer if w in geom.portals]
    if exterior and len(exterior) == len(level.outer) and len(set(exterior)) == 1:
        return exterior[0]
    return geom.primary(level)


def _sector_patterns(geom: _Geometry, nests: Sequence[Sequence[_Level]]) -> Iterable[dict]:
    rounds = {}
    inner_sectors = set()
    for chain in nests:
        outer, inner = chain[0], chain[-1]
        host = _boundary_host(geom, outer)
        data = _nest_data(geom, chain, host)
        if data is None:
            continue
        form, levels = data
        centre = inner.shape.centre
        sectors = {s for level in chain for s in level.sectors}
        scope = {host, *sectors, *geom.open_neighbours[host]}
        z = geom.sectors[geom.primary(inner)]["floor_z"]
        error = max(_distance(centre, level.shape.centre) / level.shape.radius for level in chain)
        yield _record(geom, "nest", centre, z, host, scope, (("sector", s) for s in sectors),
                      outer.shape.radius, 1 - error, count=len(levels), form=form, levels=levels)
        rounds[outer.sectors] = outer, scope, host
        inner_sectors.update(s for level in chain[1:] for s in level.sectors)
        if len(outer.sectors) > 1:
            inner_sectors.update(outer.sectors)
    for host in sorted(geom.shapes.keys() - inner_sectors - geom.offstage):
        level = geom.level((host,))
        rounds.setdefault((host,), (level, {host, *geom.open_neighbours[host]}, host))
    for level, scope, host in rounds.values():
        shape = level.shape
        regularity = shape.circularity()
        floor = geom.sectors[geom.primary(level)]
        if (regularity is not None and shape.radius >= ROUND_MIN_RADIUS
                and floor["floor_z"] - floor["ceiling_z"] >= BODY.crouch_height):
            yield _record(geom, "round", shape.centre, floor["floor_z"], host, scope,
                          (("sector", s) for s in level.sectors), shape.radius, regularity,
                          count=len(shape.points), sides=len(shape.points))
    for host in geom.shapes:
        if host in geom.offstage or len(geom.holes[host]) < 4:
            continue
        sites = _pillar_sites(geom, host)
        for circle in _circles(sites, pillars=True):
            members = tuple(s.member for s in circle.sites)
            z = geom.sectors[host]["floor_z"]
            scope = {host, *geom.open_neighbours[host]}
            row = _record(geom, "pillars", circle.centre, z, host, scope, members,
                          circle.radius, circle.regularity)
            # A solid pillar is a whole hole loop. Its first wall identifies
            # the member; a switch on another wall of the loop still counts.
            ids = {i for k, i in members if k == "wall"}
            walls = (("wall", w) for loop in geom.level((host,)).holes
                     if loop and min(loop) in ids for w in loop)
            for wire in geom.wires(walls):
                if wire not in row["wiring"]:
                    row["wiring"].append(wire)
            row["wired"] = bool(row["wiring"])
            yield row


def _groups(geom: _Geometry, records: Sequence[dict]) -> Iterable[dict]:
    """Compare every layer to the smallest one, preventing chains of drifting centres."""
    available = sorted(records, key=lambda r: (r["radius"], r["id"]))
    while available:
        anchor = available.pop(0)
        other_layers = []
        independent = [anchor]
        footprints = [_sprite_footprint(anchor)]
        for layer in available:
            if _distance(anchor["centre"], layer["centre"]) > GROUP_CENTRE_ERROR * anchor["radius"]:
                continue
            same_centre = (anchor["centre_sector"] is not None
                           and anchor["centre_sector"] == layer["centre_sector"])
            host, other = anchor["host_sector"], layer["host_sector"]
            if not (same_centre or host == other or other in geom.open_neighbours[host]):
                continue
            if not same_centre and abs(anchor["z"] - layer["z"]) > BODY.standing_height:
                continue
            other_layers.append(layer)
            footprint = _sprite_footprint(layer)
            if not footprint or not any(other and len(footprint & other)
                                        >= GROUP_SHARED_SPRITES * min(len(footprint), len(other))
                                        for other in footprints):
                footprints.append(footprint)
                independent.append(layer)
        if len(independent) < 2:
            continue
        layers = [anchor, *other_layers]
        used = {layer["id"] for layer in layers}
        available = [r for r in available if r["id"] not in used]
        # The smallest pattern localizes the centre. The largest supplies the
        # room footprint and radius, and the centre floor is read once there.
        outer = layers[-1]
        host = outer["host_sector"]
        members = {(m["kind"], m["id"]) for layer in layers for m in layer["members"]}
        scope = {host, *geom.open_neighbours[host],
                 *(layer["host_sector"] for layer in layers),
                 *(layer["centre_sector"] for layer in layers if layer["centre_sector"] is not None),
                 *(i for k, i in members if k == "sector"),
                 *(geom.sprites[i]["sector"] for k, i in members if k == "sprite")}
        quality = mean(layer["regularity"] for layer in independent)
        count = len(independent)
        group = _record(geom, "group", tuple(anchor["centre"]), anchor["z"], host, scope,
                        members, outer["radius"], quality, by="layers", count=count,
                        layers=[{key: layer[key] for key in ("id", "kind", "count", "family", "radius")}
                                | ({"form": layer["form"]} if "form" in layer else {})
                                for layer in layers])
        for layer in layers:
            for wire in layer["wiring"]:
                if wire not in group["wiring"]:
                    group["wiring"].append(wire)
        group["wired"] = bool(group["wiring"])
        group["score"] = _score(count, quality, sum(layer["count"] for layer in independent))
        yield group


def _sprite_footprint(row: dict) -> frozenset[int]:
    return frozenset(m["id"] for m in row["members"] if m["kind"] == "sprite")


def observe_compositions(disk: DiskMap, *, directional_tiles: Iterable[int] = ()) -> list[dict]:
    """Return deterministic, JSON-ready records for a disk map at single-player load.

    Pass tile ids with five- or eight-view ART when available. Dudes and
    wall-aligned sprites carry usable angles without ART. Native z increases
    downwards; a positive floor step in a record is a rise. Group scores are
    the count of agreeing layers plus a fractional regularity and size bonus.
    """
    geom = _Geometry(disk)
    nests = _nests(geom)
    windows = _room_windows(geom, nests)
    records = [*_sector_patterns(geom, nests), *_sprite_rings(geom, windows),
               *_focuses(geom, windows, directional_tiles)]
    records.sort(key=lambda r: (r["host_sector"], r["kind"], r["centre"],
                                r["radius"], [(m["kind"], m["id"]) for m in r["members"]]))
    for index, row in enumerate(records):
        row["id"] = index
    for group in _groups(geom, records[:]):
        group["id"] = len(records)
        records.append(group)
    return records
