"""Build maps as the 2D model the vector overlap solver expects.

Provides `Build2DModel` with shapely sector polygons (holes included), walls
tagged solid/portal, a portal graph, computed overlaps, and the point oracle
the arrangement classifies its cells with.

The oracle is the design predicate, three independent existential conditions:

    (exists r_A: A admitted) and (exists r_B: B admitted)
    and (exists r_O: the shared region exposed)

never one shared beam, and never "the region seen through A and through B" --
that stronger reading loses the maps where a branch is admitted in a direction
other than the one the region is exposed from.
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bloodmap.format import read_map
from tools.bunch_order import wallfront as _wallfront
from tools.bunch_order import Map as _BunchMap, broad_phase_occluded

Vec2 = Tuple[float, float]
FOV = math.radians(90.0)


def _norm(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def _span(geom, p):
    """The angular interval the footprint subtends from p."""
    pts = list(geom.exterior.coords)[:-1]
    angs = [math.atan2(q[1] - p[1], q[0] - p[0]) for q in pts]
    base = angs[0]
    rel = sorted(((a - base + math.pi) % (2 * math.pi)) - math.pi
                 for a in angs)
    return base + rel[0], base + rel[-1]


EPS = 1e-9


@dataclass
class Wall:
    a: Vec2
    b: Vec2
    kind: str                 # "solid" | "portal"
    neighbor: Optional[str]


@dataclass
class Sector:
    id: str
    polygon: Polygon
    walls: List[Wall] = field(default_factory=list)


@dataclass
class Overlap:
    id: str
    sector_a: str
    sector_b: str
    geometry: Polygon


def _loops(disk, si):
    """Split a sector's walls into closed loops through point2."""
    f = disk.sectors[si].fields
    p, c = int(f["wall_ptr"]), int(f["wall_count"])
    nxt = {}
    for w in range(p, p + c):
        nxt[w] = int(disk.walls[w].fields["point2"])
    seen, loops = set(), []
    for w in range(p, p + c):
        if w in seen:
            continue
        ring, cur = [], w
        while cur not in seen:
            seen.add(cur)
            wf = disk.walls[cur].fields
            ring.append((float(wf["x"]), float(wf["y"])))
            cur = nxt[cur]
        if len(ring) >= 3:
            loops.append(ring)
    return loops


def _signed_area(ring):
    s = 0.0
    for i, p in enumerate(ring):
        q = ring[(i + 1) % len(ring)]
        s += p[0] * q[1] - q[0] * p[1]
    return s / 2.0


class Build2DModel:
    """A Build map as sector polygons, walls, a portal graph and overlaps."""

    def __init__(self, path):
        disk = read_map(str(path))
        self.disk = disk
        self.path = str(path)
        self.sectors: Dict[str, Sector] = {}
        self.portal_graph: Dict[str, Set[str]] = defaultdict(set)
        self._index: Dict[str, int] = {}

        for si in range(len(disk.sectors)):
            sid = "s%d" % si
            self._index[sid] = si
            rings = _loops(disk, si)
            if not rings:
                continue
            rings.sort(key=lambda r: abs(_signed_area(r)), reverse=True)
            shell, holes = rings[0], rings[1:]
            poly = Polygon(shell, holes)
            if not poly.is_valid:
                poly = poly.buffer(0)
            self.sectors[sid] = Sector(sid, poly)

        for si in range(len(disk.sectors)):
            sid = "s%d" % si
            if sid not in self.sectors:
                continue
            f = disk.sectors[si].fields
            p, c = int(f["wall_ptr"]), int(f["wall_count"])
            for w in range(p, p + c):
                wf = disk.walls[w].fields
                nf = disk.walls[int(wf["point2"])].fields
                a = (float(wf["x"]), float(wf["y"]))
                b = (float(nf["x"]), float(nf["y"]))
                ns = int(wf["next_sector"])
                one_way = bool(int(wf["cstat"]) & 32)
                if ns >= 0 and not one_way:
                    nid = "s%d" % ns
                    self.sectors[sid].walls.append(Wall(a, b, "portal", nid))
                    self.portal_graph[sid].add(nid)
                    self.portal_graph[nid].add(sid)
                else:
                    self.sectors[sid].walls.append(Wall(a, b, "solid", None))

        self.overlaps: List[Overlap] = []
        ids = sorted(self.sectors, key=lambda s: self._index[s])
        for i, a in enumerate(ids):
            pa = self.sectors[a].polygon
            for b in ids[i + 1:]:
                pb = self.sectors[b].polygon
                if not pa.intersects(pb):
                    continue
                inter = pa.intersection(pb)
                for geom in getattr(inter, "geoms", [inter]):
                    if geom.geom_type != "Polygon" or geom.area <= 1.0:
                        continue
                    self.overlaps.append(
                        Overlap("%s__%s" % (a, b), a, b, geom))
        self.overlap_by_id = {o.id: o for o in self.overlaps}

    # -- oracle -----------------------------------------------------------

    def _ray_hit(self, p, d, a, b):
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = d[0] * ey - d[1] * ex
        if abs(den) < EPS:
            return None
        wx, wy = a[0] - p[0], a[1] - p[1]
        t = (wx * ey - wy * ex) / den
        u = (d[0] * wy - d[1] * wx) / -den
        if t <= 1e-7 or u < -1e-9 or u > 1.0 + 1e-9:
            return None
        return t

    def trace(self, start, p, d, limit=64):
        segments = self.trace_segments(start, p, d, limit)
        admitted = [s for s, _a, _b in segments]
        end = segments[-1][2] if segments else 0.0
        return admitted, end

    def trace_segments(self, start, p, d, limit=64):
        """The ray's walk as (sector, t_enter, t_exit) spans.

        Knowing *which* sector the ray occupies over each span is what lets the
        oracle ask whether the footprint is painted by a particular parent,
        rather than merely reached by some sector or other.
        """
        sector = start
        out = []
        t0 = 0.0
        for _ in range(limit):
            best_t, best_next = None, None
            for w in self.sectors[sector].walls:
                t = self._ray_hit(p, d, w.a, w.b)
                if t is None or t <= t0 + 1e-6:
                    continue
                if best_t is None or t < best_t:
                    best_t = t
                    best_next = w.neighbor if w.kind == "portal" else None
            if best_t is None:
                # The ray leaked out through a vertex: the walk is unusable
                # past here, so it ends rather than flying through solid space.
                out.append((sector, t0, float("inf")))
                return out
            out.append((sector, t0, best_t))
            if best_next is None:
                return out
            sector = best_next
            t0 = best_t
        return out

    def _bmap(self):
        m = getattr(self, "_bunch_map", None)
        if m is None:
            m = self._bunch_map = _BunchMap(self.path)
        return m

    def admitted_sectors(self, start, p):
        """Which sectors the render flood can reach from p.

        Cone propagation with white-wall clipping, not a ray fan: it answers
        the same question in one pass over the portal graph instead of one
        trace per direction, and admission is all the sort clause needs.
        """
        si = int(start[1:])
        reach = broad_phase_occluded(self._bmap(), si, p)
        return {"s%d" % k for k in reach}

    def _window_walls(self, p, lo, hi):
        """Walls whose silhouette can fall inside the footprint's window.

        Everything else in the map contributes directions that no ray toward
        the footprint will ever take, and scanning all of them per point is
        what made BB4 unusable.
        """
        out = []
        width = (hi - lo) % (2 * math.pi)
        for sec in self.sectors.values():
            for w in sec.walls:
                for q in (w.a, w.b):
                    t = math.atan2(q[1] - p[1], q[0] - p[0])
                    if (t - lo) % (2 * math.pi) <= width + 1e-9:
                        out.append(t)
                        break
        return out

    def _fan(self, p, overlap):
        """Critical directions, restricted to the footprint's angular window.

        Both clauses ask about rays that cross the footprint, so a direction
        outside the window cannot change either answer.
        """
        lo, hi = _span(overlap.geometry, p)
        if (hi - lo) > math.pi:
            return []
        pad = 1e-4
        lo, hi = lo - pad, hi + pad
        angs = set(self._window_walls(p, lo, hi))
        o = overlap.geometry
        pts = list(o.exterior.coords)[:-1]
        for ring in o.interiors:
            pts.extend(list(ring.coords)[:-1])
        for q in pts:
            angs.add(math.atan2(q[1] - p[1], q[0] - p[0]))
        angs.add(lo)
        angs.add(hi)
        s = sorted(a for a in angs
                   if (a - lo) % (2 * math.pi) <= (hi - lo) % (2 * math.pi))
        out = list(s)
        for i in range(len(s) - 1):
            out.append((s[i] + s[i + 1]) / 2.0)
        return out

    def _bunches(self, sectors, p, heading, half=None):
        """Front-facing wall runs per sector, within the view cone.

        A bunch is what carries a sector's floor and ceiling across screen
        columns, so this is the unit the draw order is decided between.
        """
        if half is None:
            half = FOV / 2 + 0.35
        out = []
        for sid in sorted(sectors):
            W = self.sectors[sid].walls
            run = []
            prev_b = None
            for w in W:
                cr = ((w.a[0] - p[0]) * (w.b[1] - p[1])
                      - (w.b[0] - p[0]) * (w.a[1] - p[1]))
                angs = [_norm(math.atan2(q[1] - p[1], q[0] - p[0]) - heading)
                        for q in (w.a, w.b)]
                if cr > 0 and any(-half <= t <= half for t in angs):
                    if run and prev_b == w.a:
                        run.append(w)
                    else:
                        if run:
                            out.append((sid, run))
                        run = [w]
                    prev_b = w.b
                else:
                    if run:
                        out.append((sid, run))
                    run = []
                    prev_b = None
            if run:
                out.append((sid, run))
        return out

    def _sort_conflict(self, admitted, p, overlap, nhead=12):
        """Is the draw order between the two parents ever undecidable?

        wallfront's -2 verdict is a mutual straddle: neither wall is wholly in
        front of the other, so the engine has no answer and the floor of the
        far sector can land on top of the near one.
        """
        A, B = overlap.sector_a, overlap.sector_b
        if A not in admitted or B not in admitted:
            return False
        lo, hi = _span(overlap.geometry, p)
        if (hi - lo) > math.pi:
            return False
        for k in range(nhead):
            heading = lo + (hi - lo) * k / max(1, nhead - 1)
            bun = self._bunches(admitted, p, heading)
            for i, (si, wi) in enumerate(bun):
                if si != A and si != B:
                    continue
                for j, (sj, wj) in enumerate(bun):
                    if j <= i or {si, sj} != {A, B}:
                        continue
                    for u in wi:
                        for v in wj:
                            if _wallfront((u.a, u.b), (v.a, v.b), p) == -2:
                                return True
        return False

    def classify_point(self, start_sector, p, overlap):
        """True when this camera position can glitch the overlap.

        Two failure modes, measured separately on the calibration set:

          1. the footprint is reachable down BOTH branches, so the same ground
             is drawn twice at two depths.  True in bad_1 and bad_2 only.
          2. the two parents' walls mutually straddle while both are drawn, so
             bunchfront has no answer and the far floor paints over the near
             one.  This is what bad_3, bad_4, bad_7, bad_8 and bad_9 do.

        The floors and ceilings are what the player sees break, but they carry
        no depth of their own -- they inherit the order of the bunch they hang
        on, which is why both clauses are stated over walls.

        Rejected readings, so none is retried: "A admitted and B admitted and
        the footprint exposed" flags good_2, which does not glitch in the
        engine; "both parents have a front-facing wall in a footprint column"
        flags all three goods, because the far wall beyond the footprint is
        front-facing from almost anywhere.
        """
        A, B = overlap.sector_a, overlap.sector_b
        geom = overlap.geometry
        # Admission first.  Reversing this to run the ray fan first was tried
        # and is slower: the fan looked cheap only because admission was short
        # -circuiting 98% of cells before it ever ran.  Measured on BB4, the
        # fan-first order pushed a 5m46s pass past 10 minutes.
        admitted = self.admitted_sectors(start_sector, p)
        if A not in admitted or B not in admitted:
            return False, None, None
        thru_a = thru_b = False
        for ang in self._fan(p, overlap):
            d = (math.cos(ang), math.sin(ang))
            for sector, t0, t1 in self.trace_segments(start_sector, p, d):
                if t1 == float("inf") or (sector != A and sector != B):
                    continue
                span = LineString([(p[0] + d[0] * t0, p[1] + d[1] * t0),
                                   (p[0] + d[0] * t1, p[1] + d[1] * t1)])
                if not span.intersects(geom):
                    continue
                if sector == A:
                    thru_a = True
                elif sector == B:
                    thru_b = True
        if thru_a and thru_b:
            return True, None, None
        return self._sort_conflict(admitted, p, overlap), None, None

    @classmethod
    def load(cls, path):
        return cls(path)
