"""Classic Build bunch-order conflict validator.

Searches a map for camera states in which geometry from two XY-overlapping
sectors becomes co-resident in the renderer pending bunch set and Build cannot
establish a valid front-to-back ordering between the resulting bunches.

Staged, cheap to expensive:

    XY overlap pairs -> topological prefilter -> XY samples
    -> 360 degree broad phase (angular intervals through portals)
    -> FOV compatibility -> Z admission -> exact bunch-order oracle

FAIL is a counterexample with a witness camera. PASS means no conflict was
found at the tested sampling density, never a proof.

    python -m tools.bunch_order MAP.MAP [--xy-step 512] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bloodmap.format import read_map

TAU = 2.0 * math.pi
FOV = math.radians(90.0)
EYE_ABOVE_FLOOR = 15264
CROUCH_ABOVE_FLOOR = 8192


def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (b[0] - o[0]) * (a[1] - o[1])


class Map:
    def __init__(self, path):
        d = read_map(path)
        self.disk = d
        self.n = len(d.sectors)
        self.edges = {}
        self.walls = {}
        self.nbr = defaultdict(set)
        for si, s in enumerate(d.sectors):
            f = s.fields
            p, c = int(f["wall_ptr"]), int(f["wall_count"])
            E, W = [], []
            for w in range(p, p + c):
                wf = d.walls[w].fields
                p2 = int(wf["point2"])
                nf = d.walls[p2].fields
                a = (int(wf["x"]), int(wf["y"]))
                b = (int(nf["x"]), int(nf["y"]))
                nxt = int(wf["next_sector"])
                E.append((a, b))
                W.append((w, a, b, nxt, int(wf["cstat"]), p2))
                if nxt >= 0:
                    self.nbr[si].add(nxt)
                    self.nbr[nxt].add(si)
            self.edges[si] = E
            self.walls[si] = W
        self.floor = [int(s.fields["floor_z"]) for s in d.sectors]
        self.ceil = [int(s.fields["ceiling_z"]) for s in d.sectors]

    def inside(self, si, x, y):
        hit = False
        for (x1, y1), (x2, y2) in self.edges[si]:
            if (y1 > y) != (y2 > y):
                if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                    hit = not hit
        return hit

    def bbox(self, si):
        xs = [q[0] for e in self.edges[si] for q in e]
        ys = [q[1] for e in self.edges[si] for q in e]
        return min(xs), min(ys), max(xs), max(ys)


def overlap_pairs(m, cell=128):
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
    out = []
    for a in range(m.n):
        A = bb[a]
        for b in range(a + 1, m.n):
            B = bb[b]
            if A[2] <= B[0] or B[2] <= A[0] or A[3] <= B[1] or B[3] <= A[1]:
                continue
            if mask[a] & mask[b]:
                out.append((a, b))
    return out


def component_of(m):
    comp = [-1] * m.n
    c = 0
    for s in range(m.n):
        if comp[s] >= 0:
            continue
        q = deque([s])
        comp[s] = c
        while q:
            u = q.popleft()
            for v in m.nbr[u]:
                if comp[v] < 0:
                    comp[v] = c
                    q.append(v)
        c += 1
    return comp


def prefilter(m, pairs):
    comp = component_of(m)
    return [(a, b) for a, b in pairs if comp[a] == comp[b]]


def norm(a):
    while a <= -math.pi:
        a += TAU
    while a > math.pi:
        a -= TAU
    return a


def subtend(p, a, b):
    a1 = math.atan2(a[1] - p[1], a[0] - p[0])
    a2 = math.atan2(b[1] - p[1], b[0] - p[0])
    span = norm(a2 - a1)
    if abs(span) < 1e-9:
        return None
    return (a1, a1 + span) if span > 0 else (a1 + span, a1)


def meet(c1, c2):
    if c1 is None:
        return c2
    if c2 is None:
        return c1
    l1, h1 = c1
    l2, h2 = c2
    k = round((l1 - l2) / TAU)
    l2 += k * TAU
    h2 += k * TAU
    for dl in (0.0, TAU, -TAU):
        lo, hi = max(l1, l2 + dl), min(h1, h2 + dl)
        if hi - lo > 1e-9:
            return (lo, hi)
    return False


def contains(outer, inner):
    """Is the inner angular interval already covered by the outer one?"""
    if outer is None:
        return True
    if inner is None:
        return False
    lo, hi = outer
    l, h = inner
    k = round(((l + h) / 2 - (lo + hi) / 2) / TAU)
    l -= k * TAU
    h -= k * TAU
    return lo - 1e-9 <= l and h <= hi + 1e-9


MAX_CONES = 8


def broad_phase(m, start, p):
    """Sectors the renderer could collect, with the widest cone found for each.

    A sector may be reached by several portal chains with different angular
    support, and the first chain found is not necessarily the widest.  Keeping
    only the first under-approximates reachability, which for a validator is a
    false negative -- the one error it must not make.  So a sector is expanded
    again whenever a cone arrives that no cone already recorded for it covers.
    """
    cones = defaultdict(list)
    reach = {start: (None, (start,))}
    cones[start].append(None)
    stack = [(start, None, (start,))]
    while stack:
        cur, cone, path = stack.pop()
        for (_w, a, b, nxt, cstat, _p2) in m.walls[cur]:
            if nxt < 0 or (cstat & 32):
                continue
            wg = subtend(p, a, b)
            if wg is None:
                continue
            c2 = meet(cone, wg)
            if c2 is False:
                continue
            if any(contains(old, c2) for old in cones[nxt]):
                continue
            if len(cones[nxt]) >= MAX_CONES:
                continue
            cones[nxt].append(c2)
            prev = reach.get(nxt)
            if prev is None or contains(c2, prev[0]):
                reach[nxt] = (c2, path + (nxt,))
            stack.append((nxt, c2, path + (nxt,)))
    return reach



# --------------------------------------------------------------------------
# cones as interval sets, so a white wall can split one
# --------------------------------------------------------------------------

def iv_norm(iv):
    """Bring an interval into [-pi, pi), splitting it if it wraps."""
    lo, hi = iv
    if hi - lo >= TAU - 1e-9:
        return [(-math.pi, math.pi)]
    lo = norm(lo)
    hi = lo + (iv[1] - iv[0])
    if hi > math.pi:
        return [(lo, math.pi), (-math.pi, hi - TAU)]
    return [(lo, hi)]


def iv_meet(A, B):
    out = []
    for (l1, h1) in A:
        for (l2, h2) in B:
            lo, hi = max(l1, l2), min(h1, h2)
            if hi - lo > 1e-9:
                out.append((lo, hi))
    return out


def iv_sub(A, B):
    """A minus B."""
    out = list(A)
    for (l2, h2) in B:
        nxt = []
        for (l1, h1) in out:
            if h2 <= l1 or h1 <= l2:
                nxt.append((l1, h1))
                continue
            if l1 < l2 - 1e-9:
                nxt.append((l1, min(h1, l2)))
            if h2 + 1e-9 < h1:
                nxt.append((max(l1, h2), h1))
        out = nxt
    return [(l, h) for (l, h) in out if h - l > 1e-9]


def iv_span(A):
    if not A:
        return 0.0
    return sum(h - l for (l, h) in A)


def seg_dist(p, a, b):
    """Distance from p to the nearest point of segment a-b."""
    vx, vy = b[0] - a[0], b[1] - a[1]
    wx, wy = p[0] - a[0], p[1] - a[1]
    d2 = vx * vx + vy * vy
    t = 0.0 if d2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / d2))
    dx, dy = a[0] + t * vx - p[0], a[1] + t * vy - p[1]
    return math.hypot(dx, dy)


def clipped_cone(m, p, cur, cone, wall):
    """The sub-cone that survives a portal, minus nearer white walls of `cur`.

    Standing outside a sector, its own solid walls occlude part of what its
    portals would otherwise show.  This is the clipping the owner describes --
    the white wall of one sector cutting the view of what lies beyond another.
    """
    (_w, a, b, _n, _c, _p2) = wall
    wg = subtend(p, a, b)
    if wg is None:
        return []
    sub = iv_meet(cone, iv_norm(wg))
    if not sub:
        return []
    dw = seg_dist(p, a, b)
    for (_w2, a2, b2, nxt2, _c2, _p22) in m.walls[cur]:
        if nxt2 >= 0:
            continue
        if seg_dist(p, a2, b2) >= dw:
            continue
        og = subtend(p, a2, b2)
        if og is None:
            continue
        sub = iv_sub(sub, iv_norm(og))
        if not sub:
            return []
    return sub


def broad_phase_occluded(m, start, p):
    """Cone propagation with white-wall clipping, cones as interval sets."""
    full = [(-math.pi, math.pi)]
    best = {start: (full, (start,))}
    stack = [(start, full, (start,))]
    while stack:
        cur, cone, path = stack.pop()
        for wall in m.walls[cur]:
            nxt, cstat = wall[3], wall[4]
            if nxt < 0 or (cstat & 32):
                continue
            sub = clipped_cone(m, p, cur, cone, wall)
            if not sub:
                continue
            prev = best.get(nxt)
            if prev is not None and iv_span(iv_sub(sub, prev[0])) < 1e-6:
                continue
            merged = sub if prev is None else prev[0] + sub
            best[nxt] = (merged, path + (nxt,))
            stack.append((nxt, sub, path + (nxt,)))
    return best


def fov_compatible(c1, c2):
    """Heading interval whose 90 degree viewport can hold both, or None."""
    if c1 is None or c2 is None:
        return (-math.pi, math.pi)
    l1, h1 = c1
    l2, h2 = c2
    k = round(((l1 + h1) / 2 - (l2 + h2) / 2) / TAU)
    l2 += k * TAU
    h2 += k * TAU
    lo, hi = min(l1, l2), max(h1, h2)
    if hi - lo > FOV:
        return None
    return (hi - FOV / 2, lo + FOV / 2)


def white_walls(m):
    """Every one-sided wall: the only geometry that ends the render flood."""
    out = []
    for si in range(m.n):
        for (_w, a, b, nxt, _cstat, _p2) in m.walls[si]:
            if nxt < 0:
                out.append((a, b))
    return out


def _seg_hit(p, q, a, b):
    """Does segment p-q cross segment a-b strictly between the endpoints?"""
    d1 = cross(a, b, p)
    d2 = cross(a, b, q)
    if (d1 > 0) == (d2 > 0):
        return False
    d3 = cross(p, q, a)
    d4 = cross(p, q, b)
    return (d3 > 0) != (d4 > 0)


def sees(p, target, walls):
    """An unobstructed straight line from p to target, ignoring portals."""
    for (a, b) in walls:
        if _seg_hit(p, target, a, b):
            return False
    return True


def probes_of(m, si, limit=9):
    """A few interior-ish points of a sector to aim occlusion rays at."""
    pts = []
    for (_w, a, b, _n, _c, _p2) in m.walls[si][:limit]:
        pts.append(((a[0] + b[0]) // 2, (a[1] + b[1]) // 2))
    xs = [q[0] for e in m.edges[si] for q in e]
    ys = [q[1] for e in m.edges[si] for q in e]
    pts.append((sum(xs) // len(xs), sum(ys) // len(ys)))
    return pts


def reachable_by_sight(m, p, si, walls):
    """A straight unobstructed line from p into this sector.

    NOT a correct model of the render flood, and kept only as a note: the
    renderer reaches a sector through a *chain of portals*, which may bend
    round corners, so demanding a straight line rejects sectors the renderer
    genuinely collects.  Measured on overlap1: sectors 1 and 5 are co-drawn in
    97 of 4,848 observer views, and this test prunes them.  White-wall
    occlusion has to be applied inside the cone propagation, where it can clip
    part of a cone, not as a final straight-line test.
    """
    return any(sees(p, t, walls) for t in probes_of(m, si))



# --------------------------------------------------------------------------
# the condition that actually matters: is the OVERLAPPING PART visible twice?
# --------------------------------------------------------------------------

def overlap_cells(m, a, b, cell=128):
    """Sample points inside both sectors: the region their geometry shares."""
    x0 = max(m.bbox(a)[0], m.bbox(b)[0])
    y0 = max(m.bbox(a)[1], m.bbox(b)[1])
    x1 = min(m.bbox(a)[2], m.bbox(b)[2])
    y1 = min(m.bbox(a)[3], m.bbox(b)[3])
    out = []
    for cx in range(x0 // cell, x1 // cell + 1):
        for cy in range(y0 // cell, y1 // cell + 1):
            qx, qy = cx * cell + cell // 2, cy * cell + cell // 2
            if m.inside(a, qx, qy) and m.inside(b, qx, qy):
                out.append((qx, qy))
    return out


def in_cone(cone, ang):
    """Is a direction inside an interval-set cone?"""
    for (lo, hi) in cone:
        t = ang
        k = round(((lo + hi) / 2 - t) / TAU)
        t += k * TAU
        if lo - 1e-9 <= t <= hi + 1e-9:
            return True
    return False


def shared_part_visible(m, p, cones, a, b, cells, solid):
    """A point of the shared region admitted by BOTH portal chains, or None.

    Not "are both sectors drawn" -- Blood draws overlapping sectors together
    all the time and is fine.  The fault is the *overlapping part* arriving
    down two chains at once, because that is where two sets of geometry claim
    the same screen columns.
    """
    ca, cb = cones.get(a), cones.get(b)
    if ca is None or cb is None:
        return None
    for q in cells:
        ang = math.atan2(q[1] - p[1], q[0] - p[0])
        if not (in_cone(ca, ang) and in_cone(cb, ang)):
            continue
        if sees(p, q, solid):
            return q
    return None


def z_samples(m, si):
    f, c = m.floor[si], m.ceil[si]
    out = []
    for above in (EYE_ABOVE_FLOOR, CROUCH_ABOVE_FLOOR):
        z = f - above
        if c < z < f:
            out.append(z)
    if not out:
        out.append((f + c) // 2)
    return out


def vertically_open(m, path):
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        if min(m.floor[a], m.floor[b]) - max(m.ceil[a], m.ceil[b]) <= 0:
            return False
    return True


def wallfront(w1, w2, pos):
    """engine.cpp:2227 -- 1/0 ordered, -1 collinear, -2 mutually crossing."""
    (a1, b1), (a2, b2) = w1, w2
    t1 = cross(a1, b1, a2)
    t2 = cross(a1, b1, b2)
    if t1 == 0 and t2 == 0:
        return -1
    if t1 == 0:
        t1 = t2
    if t2 == 0:
        t2 = t1
    if (t1 >= 0) == (t2 >= 0):
        tp = cross(a1, b1, pos)
        return 1 if ((tp >= 0) == (t1 >= 0)) else 0
    s1 = cross(a2, b2, a1)
    s2 = cross(a2, b2, b1)
    if s1 == 0 and s2 == 0:
        return -1
    if s1 == 0:
        s1 = s2
    if s2 == 0:
        s2 = s1
    if (s1 >= 0) == (s2 >= 0):
        sp = cross(a2, b2, pos)
        return 0 if ((sp >= 0) == (s1 >= 0)) else 1
    return -2


def build_bunches(m, sectors, pos, heading):
    """Maximal runs of consecutive front-facing walls per sector, within view."""
    half = FOV / 2 + 0.35
    out = []
    for si in sorted(sectors):
        W = m.walls[si]
        by_id = {w[0]: k for k, w in enumerate(W)}
        run = []
        prev_p2 = None
        for (wid, a, b, nxt, cstat, p2) in W:
            facing = cross(a, b, pos) > 0
            angs = [norm(math.atan2(q[1] - pos[1], q[0] - pos[0]) - heading)
                    for q in (a, b)]
            in_view = any(-half <= t <= half for t in angs)
            if facing and in_view:
                if run and prev_p2 == wid:
                    run.append((wid, a, b))
                else:
                    if run:
                        out.append((si, run))
                    run = [(wid, a, b)]
                prev_p2 = p2
            else:
                if run:
                    out.append((si, run))
                run = []
                prev_p2 = None
        if run:
            out.append((si, run))
    return out


def order_graph(bunches, pos):
    edges = set()
    skips = []
    for i in range(len(bunches)):
        si, wi = bunches[i]
        for j in range(i + 1, len(bunches)):
            sj, wj = bunches[j]
            if si == sj:
                continue
            verdict = None
            for (_wa, a1, b1) in wi:
                for (_wb, a2, b2) in wj:
                    v = wallfront((a1, b1), (a2, b2), pos)
                    if v < 0:
                        verdict = v
                        break
                    if verdict is None:
                        verdict = v
                if verdict is not None and verdict < 0:
                    break
            if verdict is None:
                continue
            if verdict < 0:
                skips.append((si, sj, verdict))
            elif verdict == 1:
                edges.add((i, j))
            else:
                edges.add((j, i))
    return edges, skips


def has_cycle(count, edges):
    g = defaultdict(list)
    for u, v in edges:
        g[u].append(v)
    colour = {}

    def dfs(u):
        colour[u] = 1
        for v in g[u]:
            c = colour.get(v, 0)
            if c == 1:
                return True
            if c == 0 and dfs(v):
                return True
        colour[u] = 2
        return False

    return any(colour.get(u, 0) == 0 and dfs(u) for u in range(count))


def validate_any(path, xy_step=512, first=False):
    """Drop the XY-overlap prefilter: check every co-resident bunch pair.

    The overlap prefilter is what makes the staged search cheap, but it also
    scopes the validator to faults *between overlapping sectors*.  A map whose
    unorderable pairs are ordinary same-height neighbours is invisible to it,
    so this mode asks the order graph directly at each sample.
    """
    m = Map(path)
    stats = dict(sectors=m.n, overlap_pairs=-1, samples=0, broad_candidates=0,
                 fov_survivors=0, z_tested=0, conflicts=0)
    conflicts = {}
    overlapping = set(prefilter(m, overlap_pairs(m)))
    for s in range(m.n):
        x0, y0, x1, y1 = m.bbox(s)
        for x in range(x0 + xy_step // 2, x1, xy_step):
            for y in range(y0 + xy_step // 2, y1, xy_step):
                if not m.inside(s, x, y):
                    continue
                stats["samples"] += 1
                p = (x, y)
                reach = broad_phase(m, s, p)
                for z in z_samples(m, s):
                    stats["z_tested"] += 1
                    for heading in (0.0, math.pi / 2, math.pi, -math.pi / 2):
                        bunches = build_bunches(m, set(reach), p, heading)
                        edges, skips = order_graph(bunches, p)
                        cyc = has_cycle(len(bunches), edges)
                        for (si, sj, v) in skips:
                            key = tuple(sorted((si, sj)))
                            if key in conflicts:
                                continue
                            conflicts[key] = dict(
                                sectors=list(key), start_sector=s, x=x, y=y, z=z,
                                heading_deg=[round(math.degrees(heading), 1)] * 2,
                                path_a=list(reach.get(si, (None, ()))[1]),
                                path_b=list(reach.get(sj, (None, ()))[1]),
                                reason=("unorderable bunch pair"
                                        + (" (XY-overlapping)" if key in overlapping
                                           else " (not XY-overlapping)")),
                                verdict=v)
                            stats["conflicts"] += 1
                            if first:
                                return stats, conflicts
                        if cyc:
                            key = ("cycle", s, x, y)
                            if key not in conflicts:
                                conflicts[key] = dict(
                                    sectors=[], start_sector=s, x=x, y=y, z=z,
                                    heading_deg=[round(math.degrees(heading), 1)] * 2,
                                    path_a=[], path_b=[],
                                    reason="ordering cycle", verdict=None)
                                stats["conflicts"] += 1
    return stats, conflicts


def validate(path, xy_step=512, first=False):
    m = Map(path)
    pairs = prefilter(m, overlap_pairs(m))
    stats = dict(sectors=m.n, overlap_pairs=len(pairs), samples=0,
                 broad_candidates=0, fov_survivors=0, sight_survivors=0,
                 z_tested=0, conflicts=0)
    conflicts = {}
    if not pairs:
        return stats, conflicts
    solid = white_walls(m)
    for s in range(m.n):
        x0, y0, x1, y1 = m.bbox(s)
        for x in range(x0 + xy_step // 2, x1, xy_step):
            for y in range(y0 + xy_step // 2, y1, xy_step):
                if not m.inside(s, x, y):
                    continue
                stats["samples"] += 1
                p = (x, y)
                reach = broad_phase(m, s, p)
                cand = [(a, b) for (a, b) in pairs if a in reach and b in reach]
                if not cand:
                    continue
                stats["broad_candidates"] += len(cand)
                for (a, b) in cand:
                    if (a, b) in conflicts:
                        continue
                    ca, pa = reach[a]
                    cb, pb = reach[b]
                    head = fov_compatible(ca, cb)
                    if head is None:
                        continue
                    stats["fov_survivors"] += 1
                    for z in z_samples(m, s):
                        if not (vertically_open(m, pa) and vertically_open(m, pb)):
                            continue
                        stats["z_tested"] += 1
                        heading = (head[0] + head[1]) / 2
                        sectors = set(pa) | set(pb)
                        bunches = build_bunches(m, sectors, p, heading)
                        edges, skips = order_graph(bunches, p)
                        hit = [(si, sj, v) for (si, sj, v) in skips
                               if {si, sj} == {a, b}]
                        cyc = has_cycle(len(bunches), edges)
                        if hit or cyc:
                            conflicts[(a, b)] = dict(
                                sectors=[a, b], start_sector=s, x=x, y=y, z=z,
                                heading_deg=[round(math.degrees(head[0]), 1),
                                             round(math.degrees(head[1]), 1)],
                                path_a=list(pa), path_b=list(pb),
                                reason=("unorderable bunch pair" if hit
                                        else "ordering cycle"),
                                verdict=(hit[0][2] if hit else None))
                            stats["conflicts"] += 1
                            if first:
                                return stats, conflicts
                            break
    return stats, conflicts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("map")
    ap.add_argument("--xy-step", type=int, default=512)
    ap.add_argument("--first", action="store_true")
    ap.add_argument("--all-pairs", action="store_true",
                    help="drop the XY-overlap prefilter")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    fn = validate_any if a.all_pairs else validate
    stats, conflicts = fn(a.map, xy_step=a.xy_step, first=a.first)
    name = Path(a.map).name
    if conflicts:
        print("BUNCH-ORDER CONFLICT  " + name)
        for c in list(conflicts.values())[:8]:
            who = ("{}/{}".format(*c["sectors"]) if len(c["sectors"]) == 2
                   else "(cycle)")
            print("  sectors {}  [{}]".format(who, c["reason"]))
            print("    witness: sector {} at ({}, {}, {})  heading {}..{} deg".format(
                c["start_sector"], c["x"], c["y"], c["z"],
                c["heading_deg"][0], c["heading_deg"][1]))
            print("    path A {}   path B {}".format(c["path_a"], c["path_b"]))
    else:
        print("PASS  {} -- no bunch-order conflict at xy-step {}".format(
            name, a.xy_step))
    print("  sectors {}, overlap pairs {}, samples {}, broad {}, fov {}, "
          "sight {}, z {}, conflicts {}".format(
              stats["sectors"], stats["overlap_pairs"], stats["samples"],
              stats["broad_candidates"], stats["fov_survivors"],
              stats.get("sight_survivors", -1),
              stats["z_tested"], stats["conflicts"]))
    if a.json:
        Path(a.json).write_text(json.dumps(
            {"map": a.map, "stats": stats,
             "conflicts": list(conflicts.values())}, indent=1))
    return 1 if conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
