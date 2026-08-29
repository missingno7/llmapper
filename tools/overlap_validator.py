"""Build overlap glitch validator -- the owner's 2D pipeline.

    map -> OverlapCells -> portal reachability -> CandidateOriginSectors
        -> TransparentVisibilityDomains -> conflict oracle per point
        -> ConflictRegion -> sector attribution -> report

The rule, from the design:

    a conflict exists at camera P when the render branches to BOTH parents of
    an XY overlap are admitted from P, and the overlap itself is exposed --
    reachable through an open aperture.

Red portals are not ignored globally: they carry sector identity and admission
in the topological phases, and only dissolve as *geometric* boundaries inside
a chosen origin domain, where they genuinely do not occlude.

Deliberately 2D.  No z, no slopes, no camera angle: the angle is existential,
resolved by the critical-angle ray fan rather than sampled.

    python -m tools.overlap_validator MAP.MAP [--step 512] [--json out.json]

Exit code 0 = no conflict found at this sampling, 1 = conflict, 2 = bad map.

The ConflictRegion is reported as a set of grid cells rather than a vector
polygon: this tree has no polygon-boolean library, and an adaptive grid is the
design's own sanctioned fallback (section 8.2) rather than a hand-rolled
arrangement nobody can trust.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.bunch_order import Map, cross, broad_phase_occluded

EPS = 1e-9


# --------------------------------------------------------------------------
# phase 1: OverlapCells
# --------------------------------------------------------------------------

def overlap_cells(m, cell=128):
    """Every pair of sectors sharing interior area, with the shared samples.

    Interior is even-odd over real wall edges, so a sector filling another's
    hole shares no ground and is not an overlap -- the mistake that made an
    earlier detector report Blood's ordinary construction as a fault.
    """
    bb = {s: m.bbox(s) for s in range(m.n)}
    mask = {}
    for s in range(m.n):
        x0, y0, x1, y1 = bb[s]
        cells = set()
        for cx in range(x0 // cell, x1 // cell + 1):
            for cy in range(y0 // cell, y1 // cell + 1):
                if m.inside(s, cx * cell + cell // 2, cy * cell + cell // 2):
                    cells.add((cx, cy))
        mask[s] = cells
    out = {}
    for a in range(m.n):
        A = bb[a]
        for b in range(a + 1, m.n):
            B = bb[b]
            if A[2] <= B[0] or B[2] <= A[0] or A[3] <= B[1] or B[3] <= A[1]:
                continue
            shared = mask[a] & mask[b]
            if shared:
                out[(a, b)] = sorted(
                    (cx * cell + cell // 2, cy * cell + cell // 2)
                    for (cx, cy) in shared)
    return out


# --------------------------------------------------------------------------
# phase 2: portal reachability and candidate origins
# --------------------------------------------------------------------------

def reach_from(m, start):
    seen = {start}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in m.nbr[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    return seen


def candidate_origins(m, a, b, reach):
    return [s for s in range(m.n) if a in reach[s] and b in reach[s]]


# --------------------------------------------------------------------------
# phase 3: TransparentVisibilityDomains
# --------------------------------------------------------------------------

def transparent_domains(m, origins, parents):
    """Group candidate origins into clusters joined by portals.

    Internal red boundaries inside a cluster do not occlude, so the cluster is
    one visibility space for the shape phase while every sector keeps its
    identity for admission and for attributing the result back.
    """
    pool = set(origins)
    out = []
    while pool:
        root = pool.pop()
        cluster = {root}
        q = deque([root])
        while q:
            s = q.popleft()
            for n in m.nbr[s]:
                if n in parents or n in cluster or n not in pool:
                    continue
                cluster.add(n)
                pool.discard(n)
                q.append(n)
        out.append(sorted(cluster))
    return out


# --------------------------------------------------------------------------
# phase 6: the conflict oracle -- ray traversal on critical angles
# --------------------------------------------------------------------------

def ray_wall_hit(p, d, a, b):
    """Parameter t>0 where ray p+t*d crosses segment a-b, or None."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    den = d[0] * ey - d[1] * ex
    if abs(den) < EPS:
        return None
    wx, wy = a[0] - p[0], a[1] - p[1]
    t = (wx * ey - wy * ex) / den
    u = (wx * d[1] - wy * d[0]) / -den if abs(den) > EPS else -1.0
    u = (d[0] * wy - d[1] * wx) / -den
    if t <= EPS or u < -EPS or u > 1.0 + EPS:
        return None
    return t


def trace(m, start, p, d, limit=64):
    """Sectors a ray enters, how far it travels, and whose wall stopped it.

    The renderer own walk: a portal changes sector identity and does not stop
    the ray, a solid wall ends it.  The terminating sector is what is painted
    in that direction, which the narrow phase needs.
    """
    sector = start
    admitted = [start]
    t0 = 0.0
    for _ in range(limit):
        best_t, best_next = None, None
        for (_w, a, b, nxt, cstat, _p2) in m.walls[sector]:
            t = ray_wall_hit(p, d, a, b)
            if t is None or t <= t0 + 1e-6:
                continue
            if best_t is None or t < best_t:
                best_t, best_next = t, (-1 if (nxt < 0 or (cstat & 32)) else nxt)
        if best_t is None:
            return admitted, float("inf"), sector
        if best_next < 0:
            return admitted, best_t, sector
        sector = best_next
        admitted.append(sector)
        t0 = best_t
    return admitted, float("inf"), sector


def critical_angles(m, p, cells, focus):
    """Directions worth firing: every relevant vertex, plus a mid-ray between.

    The camera angle is existential, so it is not sampled uniformly.  Between
    two adjacent critical directions the ray combinatorics do not change, so
    one ray per interval decides the interval.
    """
    angs = set()
    for si in focus:
        for (_w, a, b, _n, _c, _p2) in m.walls[si]:
            for q in (a, b):
                angs.add(math.atan2(q[1] - p[1], q[0] - p[0]))
    for q in cells:
        angs.add(math.atan2(q[1] - p[1], q[0] - p[0]))
    if not angs:
        return []
    s = sorted(angs)
    out = []
    for i, t in enumerate(s):
        u = s[(i + 1) % len(s)]
        mid = t + ((u - t) if u > t else (u + 2 * math.pi - t)) / 2.0
        out.append(mid)
        out.append(t + 1e-5)
    return out


def target_local_angles(m, p, cells, domain, parents):
    """Only the geometry that can change the answer, per the design.

    Overlap vertices, endpoints of portals leading out of the domain, solid
    blocker vertices, and the branch sectors own vertices -- not every vertex
    of every sector in the focus, which is what made the first version
    unusable on a real map.
    """
    angs = set()
    for q in cells:
        angs.add(math.atan2(q[1] - p[1], q[0] - p[0]))
    for si in domain:
        for (_w, a, b, nxt, _c, _p2) in m.walls[si]:
            if nxt < 0 or nxt in parents:      # blocker, or an exit aperture
                for q in (a, b):
                    angs.add(math.atan2(q[1] - p[1], q[0] - p[0]))
    for si in parents:
        for (_w, a, b, nxt, _c, _p2) in m.walls[si]:
            if nxt < 0:                        # the branch own solid silhouette
                for q in (a, b):
                    angs.add(math.atan2(q[1] - p[1], q[0] - p[0]))
    if not angs:
        return []
    s = sorted(angs)
    out = []
    for k, t in enumerate(s):
        u = s[(k + 1) % len(s)]
        out.append(t + ((u - t) if u > t else (u + 2 * math.pi - t)) / 2.0)
    return out + s


def exposed_at(m, p, start, cells, angles):
    """Does any ray reach the shared region before a solid wall stops it?

    Independent of which branch was admitted: the design correction.  Rays are
    aimed at the region rather than swept over the whole circle.
    """
    for q in cells:
        ang = math.atan2(q[1] - p[1], q[0] - p[0])
        d = (math.cos(ang), math.sin(ang))
        _seen, dist, _term = trace(m, start, p, d)
        if math.hypot(q[0] - p[0], q[1] - p[1]) <= dist + 1e-6:
            return True
    for ang in angles:
        d = (math.cos(ang), math.sin(ang))
        _seen, dist, _term = trace(m, start, p, d)
        for q in cells:
            dx, dy = q[0] - p[0], q[1] - p[1]
            t = dx * d[0] + dy * d[1]
            if 0 < t <= dist and abs(dx * d[1] - dy * d[0]) <= 64:
                return True
    return False


def conflict_at(m, p, start, pair, cells, focus, domain=(), parents=()):
    """Two stages, from the design: a loose necessary test, then a strict one.

    BROAD -- the three independent existential conditions:
        (exists r_A: A admitted) and (exists r_B: B admitted)
        and (exists r_O: the shared region exposed)
    Never one shared beam, and never "the region seen through A and through B";
    bad_3 is the regression test for that mistake.  This is sound -- it catches
    every bad map -- and loose: on its own it flags every good one too.

    NARROW -- what the broad phase cannot see: a branch being admitted says
    nothing about *where it paints*.  The fault is both parents painting into
    the columns the shared region subtends, which is where two sets of geometry
    claim the same pixels.  So each direction is attributed to the sector whose
    wall terminated it, and both parents must own a direction inside the shared
    region window.
    """
    a, b = pair
    if not cells:
        return False
    angles = target_local_angles(m, p, cells, domain or (start,), parents or (a, b))
    saw_a = saw_b = exposed = False
    win = []
    for q in cells:
        win.append(math.atan2(q[1] - p[1], q[0] - p[0]))
    lo, hi = min(win), max(win)
    wrap = (hi - lo) > math.pi
    if wrap:
        sh = [t if t >= 0 else t + 2 * math.pi for t in win]
        lo, hi = min(sh), max(sh)
    paints_a = paints_b = False
    for ang in angles:
        d = (math.cos(ang), math.sin(ang))
        seen, dist, term = trace(m, start, p, d)
        if a in seen:
            saw_a = True
        if b in seen:
            saw_b = True
        if not exposed:
            for q in cells:
                dx, dy = q[0] - p[0], q[1] - p[1]
                t = dx * d[0] + dy * d[1]
                if 0 < t <= dist and abs(dx * d[1] - dy * d[0]) <= 64:
                    exposed = True
                    break
        t = ang + 2 * math.pi if (wrap and ang < 0) else ang
        if lo - 1e-6 <= t <= hi + 1e-6:
            if term == a:
                paints_a = True
            elif term == b:
                paints_b = True
    if not (saw_a and saw_b and exposed):
        return False
    return paints_a and paints_b


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def validate(path, step=512, first=False):
    m = Map(path)
    stats = dict(sectors=m.n, overlaps=0, with_origins=0, domains=0,
                 points=0, conflicts=0)
    overlaps = overlap_cells(m)
    stats["overlaps"] = len(overlaps)
    if not overlaps:
        return stats, []
    reach = {s: reach_from(m, s) for s in range(m.n)}
    results = []
    for (a, b), cells in overlaps.items():
        origins = candidate_origins(m, a, b, reach)
        if not origins:
            continue
        stats["with_origins"] += 1
        for domain in transparent_domains(m, origins, {a, b}):
            stats["domains"] += 1
            focus = set(domain) | {a, b}
            hits = []
            for s in domain:
                x0, y0, x1, y1 = m.bbox(s)
                for x in range(x0 + step // 2, x1, step):
                    for y in range(y0 + step // 2, y1, step):
                        if not m.inside(s, x, y):
                            continue
                        stats["points"] += 1
                        if conflict_at(m, (x, y), s, (a, b), cells, focus,
                                       domain=domain, parents=(a, b)):
                            hits.append({"sector": s, "x": x, "y": y})
                            if first:
                                break
                    if first and hits:
                        break
                if first and hits:
                    break
            if not hits:
                continue
            stats["conflicts"] += 1
            per_sector = defaultdict(int)
            for h in hits:
                per_sector[h["sector"]] += 1
            results.append({
                "region_cells": [(h["x"], h["y"]) for h in hits],
                "overlap": {"parent_a": a, "parent_b": b,
                            "shared_samples": len(cells)},
                "transparent_domain": {"sectors": domain},
                "conflict_region": {"cells": len(hits), "step": step,
                                    "area_units": len(hits) * step * step},
                "sector_attribution": dict(per_sector),
                "witnesses": hits[:8],
            })
            if first:
                return stats, results
    return stats, results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("map")
    ap.add_argument("--step", type=int, default=512)
    ap.add_argument("--first", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    try:
        stats, results = validate(a.map, step=a.step, first=a.first)
    except Exception as exc:
        print("UNSUPPORTED {}: {}".format(Path(a.map).name, exc))
        return 2
    name = Path(a.map).name
    if results:
        print("OVERLAP CONFLICT  " + name)
        for r in results[:6]:
            o = r["overlap"]
            w = r["witnesses"][0]
            print("  sectors {}/{}  domain {}".format(
                o["parent_a"], o["parent_b"], r["transparent_domain"]["sectors"]))
            print("    region {} cell(s) at step {}; witness sector {} at ({}, {})".format(
                r["conflict_region"]["cells"], r["conflict_region"]["step"],
                w["sector"], w["x"], w["y"]))
    else:
        print("PASS  {} -- no conflict found at step {}".format(name, a.step))
    print("  sectors {}, overlaps {}, with origins {}, domains {}, "
          "points {}, conflicting pairs {}".format(
              stats["sectors"], stats["overlaps"], stats["with_origins"],
              stats["domains"], stats["points"], stats["conflicts"]))
    if a.json:
        Path(a.json).write_text(json.dumps(
            {"map": a.map, "stats": stats, "conflicts": results}, indent=1))
    return 1 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())
