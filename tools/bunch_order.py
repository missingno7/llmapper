"""Build geometry and visibility primitives.

What the overlap validator needs from the engine, and nothing else:

  Map                     a .MAP as sector edges, walls and portal neighbours
  broad_phase_occluded    which sectors the render flood reaches from a point,
                          as angular interval sets clipped by white walls
  wallfront               engine.cpp:2227 -- can two walls be ordered front to
                          back?  -1 collinear, -2 mutual straddle, and a -2 is
                          what leaves bunchfront with no answer

This file used to hold a second, point-sampling validator of its own.  That
one missed bad_1 on the calibration set and is gone; tools/vector_report.py is
the validator.  Its history is in the commit that removed it, along with the
predicates that were tried and what each scored.
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bloodmap.format import read_map

TAU = 2.0 * math.pi


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
