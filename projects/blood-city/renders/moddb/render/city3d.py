"""The whole city from outside: a hidden GL context, the level's own walls, floors, sprites and baked shades."""
import math, sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[5]))
import numpy as np, moderngl, shapely
from shapely.geometry import box, Polygon, LineString
from shapely.ops import unary_union
from PIL import Image
import tools.map_model as mesh
from tools.map_model import Renderer, LAMPS, look_at, persp, ortho, tonemap, save

S = pathlib.Path(__file__).parent
MAP = S.parents[2] / 'release' / 'GRAVESEND.MAP'

GRADE = -8192 / mesh.ZU          # street level, in plan units up
X0, X1, Y0, Y1 = -3.0, 61.0, -31.0, 64.7
WATER = -37888 / mesh.ZU
BASE = -10.0


def surface(m):
    """The sectors joined to the streets (sector 0) by portals."""
    return mesh.reachable(m, 0)


def SIGNS_WHOLE(f):
    """The wall sprites the section plane leaves whole: the station's, and those north of the city."""
    return 24 < f['x'] / 1024 < 35 and 20 < f['y'] / 1024 < 36 or f['y'] < 0


def load(empty=True, shift=None):
    p = mesh.played(MAP, empty)
    m0 = mesh.build(p, keep=lambda i, q, s: False)
    up = surface(m0)
    B = box(X0 * 1024, Y0 * 1024, X1 * 1024, 130 * 1024)
    ok = {i for i in up if i in m0['polys'] and m0['polys'][i].intersects(B) and m0['sectors'][i]['floor_z'] - 0 >= -70000 or (i in up and i in m0['polys'] and m0['polys'][i].intersects(box(X0*1024,Y0*1024,X1*1024,56*1024)))}
    sea = {i for i in up if i in m0['polys'] and m0['sectors'][i]['floor_z'] == 37888}
    ok = {i for i in ok if not (m0['sectors'][i]['floor_z'] == 37888 == m0['sectors'][i]['ceiling_z'])}
    m = mesh.build(p, keep=lambda i, q, s: i in ok, uncut=SIGNS_WHOLE)
    m['ok'] = ok
    return m


def caps(m, plane, under=None):
    """What is solid between the rooms and the streets, shut at the section plane; the island's sides."""
    B = box(X0 * 1024, Y0 * 1024, X1 * 1024, 64 * 1024)
    allp = unary_union([m['polys'][i].buffer(.5) for i in m['ok']]).intersection(B)
    roi = allp.buffer(5200, join_style=2).buffer(-3600, join_style=2).intersection(B)
    roi = unary_union([Polygon(g.exterior) for g in (roi.geoms if hasattr(roi, 'geoms') else [roi])])
    solid = roi.difference(allp)
    tris = []
    for g in (solid.geoms if hasattr(solid, 'geoms') else [solid]):
        if g.area < 200 or g.geom_type != 'Polygon':
            continue
        for q in shapely.constrained_delaunay_triangles(g.segmentize(4096)).geoms:
            for x, y in list(q.exterior.coords)[:3]:
                tris.append((x / 1024, plane(x / 1024, y / 1024), y / 1024, x / 1024, y / 1024, 0, 1, 0, 1.))
    skirt = []
    for g in (roi.geoms if hasattr(roi, 'geoms') else [roi]):
        c = list(g.segmentize(1024).exterior.coords)
        for (xa, ya), (xb, yb) in zip(c, c[1:]):
            mid = shapely.geometry.Point((xa + xb) / 2, (ya + yb) / 2)
            ta = tb = GRADE if (ya + yb) / 2 < 56 * 1024 - 8 else WATER
            if mid.y > 63.9 * 1024 and not solid.buffer(40).contains(mid): continue
            if solid.buffer(40).contains(mid):
                ta, tb = plane(xa / 1024, ya / 1024), plane(xb / 1024, yb / 1024)
            n = (yb - ya, -(xb - xa))
            l = math.hypot(*n) or 1
            n = (n[0] / l, 0, n[1] / l)
            P = [(xa / 1024, ta, ya / 1024), (xb / 1024, tb, yb / 1024), (xb / 1024, BASE, yb / 1024), (xa / 1024, BASE, ya / 1024)]
            for k in (0, 1, 2, 0, 2, 3):
                skirt.append((*P[k], (P[k][0] + P[k][2]) / 6, -P[k][1] / 6, *n, .9))
    for (xa, ya), (xb, yb) in (((X0, 64), (X0, Y1)), ((X0, Y1), (X1, Y1)), ((X1, Y1), (X1, 64))):
        P = [(xa, WATER, ya), (xb, WATER, yb), (xb, BASE, yb), (xa, BASE, ya)]
        for k in (0, 1, 2, 0, 2, 3):
            skirt.append((*P[k], (P[k][0] + P[k][2]) / 6, -P[k][1] / 6, *((0, 0, 1) if ya == yb else (-1 if xa < 9 else 1, 0, 0)), .9))
    # over the rooms' ceilings their walls go on up to the plane
    well = []
    SE, WA = m['sectors'], m['walls']
    for i in m['ok']:
        if m['sky'][i]:
            continue
        s = SE[i]
        for wi in range(s['wall_ptr'], s['wall_ptr'] + s['wall_count']):
            w = WA[wi]
            n = w['next_sector']
            if n >= 0 and not m['sky'][n]:
                continue
            w2 = WA[w['point2']]
            a, b = (w['x'] / 1024, w['y'] / 1024), (w2['x'] / 1024, w2['y'] / 1024)
            lo = -s['ceiling_z'] / mesh.ZU
            nn = (-(b[1] - a[1]), b[0] - a[0])
            l = math.hypot(*nn) or 1
            P = [(a[0], 40, a[1]), (b[0], 40, b[1]), (b[0], lo, b[1]), (a[0], lo, a[1])]
            for k in (0, 1, 2, 0, 2, 3):
                well.append((*P[k], 0, 0, nn[0] / l, 0, nn[1] / l, .6))
    return np.array(tris, 'f4'), np.array(skirt, 'f4'), np.array(well, 'f4').reshape(-1, 9)

class City(Renderer):
    """Gravesend's surface on the renderer of tools.map_model, with its own caps and island."""

    def __init__(self, W=1600, H=1200, ss=2, empty=True, m=None):
        super().__init__(m or load(empty), caps, W, H, ss, bounds=(X0, X1, Y0, Y1), grade=(-9.95, -6., -2.6), shadow=((29, 0, 15), 110))
