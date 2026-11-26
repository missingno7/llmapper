"""A whole Blood map rendered from outside as a cut-away model: every room cut at a height over its own floor, solid parts capped, lit offscreen.

The level is built into triangles by Build's own rules (slopes by heinum,
wall and step texture origins, floor panning, sprite alignment, palookups),
drawn by a hidden OpenGL 4.3 context with deferred light: a sun with a
shadow, ambient occlusion, the lamps the map carries, bloom. Nothing of the
game is started.

What is drawn is what can be walked to from the first player start through
portals (``--all`` for every sector). Each sector is cut at ``--cut`` player
heights over its own floor, so a map whose floors climb a hill is cut along
the hill; the walls of a room go on up to the cut in a flat colour where its
ceiling is lower, and what is solid between the rooms is capped at the cut
heights of the walls round it. Ceilings are not drawn, so every room is open
from above.

.. code-block:: bash

    python -m tools.map_model E3M1 -o work/map_model/E3M1.png
    python -m tools.map_model E3M1 --az 200 --el 50 --cut 1.2 --light day
    python -m tools.map_model blood-city --light day --ss 3

A render of a campaign map is a render of commercial data: keep it under
``work/``. The ModDB logo of Gravesend (``projects/blood-city/renders/moddb``)
is this renderer with its own caps and scene.
"""

from __future__ import annotations

import argparse
import math
import pathlib
import sys
import tempfile
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import bloodmap.art as art
from bloodmap import shade_table
from bloodmap.flatsprite import footprint
from bloodmap.format import read_map
from bloodmap.model import record_fields as F
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.visual import as_played

RES = str(ROOT / 'reference' / 'blood')
PU = 1024.
ZU = 16 * 1024.
BODY = PLAYER_PROFILES['blood'].standing_height
LAMPS = {640: (1.0, .62, .26, 1.0, .86), 641: (1.0, .6, .25, .8, .5), 506: (1.0, .45, .12, .9, .5), 908: (1.0, .45, .12, .9, .5),
         569: (.9, .5, .9, .0, .5)}
CONTROL = (0, 2519, 2520, 2521, 2330, 2331, 2332, 2333, 2334, 3997)


def V(x, y, z):
    """Map units to the renderer's: plan units, y up."""
    return (x / PU, -z / ZU, y / PU)


def br(sh):
    return max(0., min(1.8, 1 - sh / 64))


def p2(n):
    return 1 << max(0, math.ceil(math.log2(max(1, n))))


def _geoms(g):
    return list(g.geoms) if hasattr(g, 'geoms') else [g]


def played(path, empty=True):
    """The map as the game shows it: control sprites hidden, and with ``empty`` no enemies or pickups."""
    return as_played(pathlib.Path(path), tempfile.mkdtemp(), empty=empty)


def build(mapfile, keep=None, uncut=None, cut=None):
    """Triangles of a MAP by texture, sprites as billboards.

    ``keep(i, polygon, sector)`` chooses the sectors. ``uncut(sprite)`` names
    the wall sprites a section plane leaves whole. ``cut`` (Build z units)
    cuts every kept sector that far over its own floor: walls end there,
    one-sided walls rise to it, a room's walls go on above its ceiling as
    ``well`` (a flat colour) and sprites standing above it are dropped.
    """
    d = read_map(mapfile)
    SE = [F(s) for s in d.sectors]
    WA = [F(w) for w in d.walls]
    T = art.read_art_directory(RES)
    out = defaultdict(list)

    def tri(key, pts, uvs, n, b):
        for i in range(1, len(pts) - 1):
            for k in (0, i, i + 1):
                out[key].append((*pts[k], *uvs[k], *n, b))

    def loops(i):
        s = SE[i]
        a, b = s['wall_ptr'], s['wall_ptr'] + s['wall_count']
        seen, L = set(), []
        for w in range(a, b):
            if w in seen:
                continue
            l, k = [], w
            while k not in seen and a <= k < b:
                seen.add(k)
                l.append((WA[k]['x'], WA[k]['y']))
                k = WA[k]['point2']
            if len(l) >= 3:
                L.append(l)
        return L

    polys = {}
    for i in range(len(SE)):
        L = sorted(loops(i), key=lambda l: -Polygon(l).area)
        if not L:
            continue
        p = Polygon(L[0], L[1:])
        polys[i] = p if p.is_valid else p.buffer(0)

    def slope(i, which):
        s = SE[i]
        z = s[which + '_z']
        h = s[which + '_heinum'] if s[which + '_stat'] & 2 else 0
        if not h:
            return lambda x, y: z
        w = WA[s['wall_ptr']]
        w2 = WA[w['point2']]
        dx, dy = w2['x'] - w['x'], w2['y'] - w['y']
        n = math.hypot(dx, dy) or 1
        return lambda x, y: z + h * (dx * (y - w['y']) - dy * (x - w['x'])) / n / 256

    FZ = [slope(i, 'floor') for i in range(len(SE))]
    CZ = [slope(i, 'ceiling') for i in range(len(SE))]
    sky = [bool(s['ceiling_stat'] & 1) for s in SE]
    kept = [not keep or keep(i, polys.get(i), SE[i]) for i in range(len(SE))]

    # the section: each sector's cut, and the height a one-sided wall rises to at each of its ends
    SC = [(lambda f: (lambda x, y: f(x, y) - cut))(FZ[i]) for i in range(len(SE))] if cut is not None else None
    VH = {}
    segs = []
    if cut is not None:
        for i, s in enumerate(SE):
            if not kept[i]:
                continue
            for wi in range(s['wall_ptr'], s['wall_ptr'] + s['wall_count']):
                w = WA[wi]
                if w['next_sector'] >= 0 and kept[w['next_sector']]:
                    continue
                w2 = WA[w['point2']]
                for p in ((w['x'], w['y']), (w2['x'], w2['y'])):
                    VH[p] = min(VH.get(p, math.inf), SC[i](*p))
        for i, s in enumerate(SE):
            if not kept[i]:
                continue
            for wi in range(s['wall_ptr'], s['wall_ptr'] + s['wall_count']):
                w = WA[wi]
                if w['next_sector'] >= 0 and kept[w['next_sector']]:
                    continue
                w2 = WA[w['point2']]
                segs.append((w['x'], w['y'], w2['x'], w2['y'], VH[(w['x'], w['y'])], VH[(w2['x'], w2['y'])]))

    def flat(i, which):
        s = SE[i]
        st = s[which + '_stat']
        if st & 1 or i not in polys:
            return
        pic = s[which + '_picnum']
        t = T.get(pic)
        if not t or not t.width:
            return
        zf = (FZ if which == 'floor' else CZ)[i]
        b_ = br(s[which + '_shade'])
        w = WA[s['wall_ptr']]
        w2 = WA[w['point2']]
        ang = math.atan2(w2['y'] - w['y'], w2['x'] - w['x'])
        sc = 8 if st & 8 else 16

        def uv(x, y):
            if st & 64:
                rx, ry = x - w['x'], y - w['y']
                x, y = rx * math.cos(ang) + ry * math.sin(ang), -rx * math.sin(ang) + ry * math.cos(ang)
            u, v = x / sc, -y / sc
            if st & 4:
                u, v = v, u
            if st & 16:
                u = -u
            if st & 32:
                v = -v
            return (u / t.width + s[which + '_x_panning'] / 256, v / t.height + s[which + '_y_panning'] / 256)

        for q in shapely.constrained_delaunay_triangles(polys[i]).geoms:
            c = list(q.exterior.coords)[:3]
            kind = 'solid' if which == 'floor' else 'ceil'
            tri((pic, s[which + '_pal'], kind), [V(x, y, zf(x, y)) for x, y in c], [uv(x, y) for x, y in c],
                (0, 1 if which == 'floor' else -1, 0), b_)

    def quad(pic, pal, kind, x0, y0, x1, y1, za0, za1, zb0, zb1, anchor, shade, cst, xr, yr, xp, yp):
        if zb0 <= za0 and zb1 <= za1:
            return
        t = T.get(pic)
        if not t or not t.width:
            return
        u0 = xp / t.width
        U = xr * 8 / t.width
        ul, ur = (u0, u0 + U) if not cst & 8 else (u0 + U, u0)

        def vf(z):
            return (((z - anchor) * yr / 2048) / t.height + yp * p2(t.height) / 256 / t.height) * (-1 if cst & 256 else 1)
        n = (-(y1 - y0), 0, (x1 - x0))
        l = math.hypot(n[0], n[2]) or 1
        n = (n[0] / l, 0, n[2] / l)
        zb0, zb1 = max(zb0, za0), max(zb1, za1)
        tri((pic, pal, kind), [V(x0, y0, za0), V(x1, y1, za1), V(x1, y1, zb1), V(x0, y0, zb0)],
            [(ul, vf(za0)), (ur, vf(za1)), (ur, vf(zb1)), (ul, vf(zb0))], n, br(shade))

    def well(x0, y0, x1, y1, za0, za1, zb0, zb1):
        if zb0 <= za0 and zb1 <= za1:
            return
        n = (-(y1 - y0), 0, (x1 - x0))
        l = math.hypot(n[0], n[2]) or 1
        zb0, zb1 = max(zb0, za0), max(zb1, za1)
        tri((-1, 0, 'well'), [V(x0, y0, za0), V(x1, y1, za1), V(x1, y1, zb1), V(x0, y0, zb0)], [(0, 0)] * 4, (n[0] / l, 0, n[2] / l), .6)

    for i, s in enumerate(SE):
        if not kept[i]:
            continue
        flat(i, 'floor')
        if cut is None or sky[i]:
            flat(i, 'ceiling')
        for wi in range(s['wall_ptr'], s['wall_ptr'] + s['wall_count']):
            w = WA[wi]
            w2 = WA[w['point2']]
            x0, y0, x1, y1 = w['x'], w['y'], w2['x'], w2['y']
            f0, f1, c0, c1 = FZ[i](x0, y0), FZ[i](x1, y1), CZ[i](x0, y0), CZ[i](x1, y1)
            n, cs = w['next_sector'], w['cstat']
            tx = (w['x_repeat'], w['y_repeat'], w['x_panning'], w['y_panning'])
            outer = ('spire' if s['ceiling_stat'] & 2 and s['ceiling_heinum'] > 9000 else 'wall') if sky[i] else 'room'
            if n < 0 or (cut is not None and not kept[n]):
                anchor = s['floor_z'] if cs & 4 else s['ceiling_z']
                if cut is None:
                    quad(w['picnum'], w['pal'], outer, x0, y0, x1, y1, c0, c1, f0, f1, anchor, w['shade'], cs, *tx)
                    continue
                t0, t1 = VH[(x0, y0)], VH[(x1, y1)]
                if sky[i]:
                    quad(w['picnum'], w['pal'], outer, x0, y0, x1, y1, t0, t1, f0, f1, anchor, w['shade'], cs, *tx)
                else:
                    quad(w['picnum'], w['pal'], outer, x0, y0, x1, y1, max(c0, t0), max(c1, t1), f0, f1, anchor, w['shade'], cs, *tx)
                    well(x0, y0, x1, y1, t0, t1, min(c0, f0), min(c1, f1))
                continue
            g0, g1, h0, h1 = FZ[n](x0, y0), FZ[n](x1, y1), CZ[n](x0, y0), CZ[n](x1, y1)
            T0 = T1 = -math.inf
            if cut is not None:
                T0, T1 = min(SC[i](x0, y0), SC[n](x0, y0)), min(SC[i](x1, y1), SC[n](x1, y1))
            if not (sky[i] and sky[n]):
                quad(w['picnum'], w['pal'], outer, x0, y0, x1, y1, max(c0, T0), max(c1, T1), min(h0, f0), min(h1, f1),
                     s['ceiling_z'] if cs & 4 else SE[n]['ceiling_z'], w['shade'], cs, *tx)
            lw = WA[w['next_wall']] if cs & 2 and w['next_wall'] >= 0 else w
            ta, tb = (g0, g1) if sky[i] else (max(g0, c0), max(g1, c1))
            quad(lw['picnum'], lw['pal'], 'step', x0, y0, x1, y1, max(ta, T0), max(tb, T1), f0, f1,
                 s['ceiling_z'] if cs & 4 else SE[n]['floor_z'], lw['shade'], cs,
                 w['x_repeat'], w['y_repeat'], lw['x_panning'], lw['y_panning'])
            if cs & 48 and (cs & 32 or wi < w['next_wall']):
                A = max(SE[i]['ceiling_z'], SE[n]['ceiling_z']) if not cs & 4 else min(s['floor_z'], SE[n]['floor_z'])
                quad(w['over_picnum'], w['pal'], 'mask', x0, y0, x1, y1, max(c0, h0, T0), max(c1, h1, T1), min(f0, g0), min(f1, g1),
                     A, w['shade'], cs, *tx)
    sprites = []
    for sp in d.sprites:
        f = F(sp)
        if f['cstat'] & 32768 or f['status'] == 10 or f['x_repeat'] == 0:
            continue
        if f['picnum'] in CONTROL or 2522 <= f['picnum'] <= 2529:
            continue
        i = f['sector']
        if not 0 <= i < len(SE) or not kept[i]:
            continue
        t = T.get(f['picnum'])
        if t and t.width:
            sprites.append(dict(f))
    for f in sprites:
        t = T[f['picnum']]
        al = f['cstat'] & 48
        an = t.animation
        xo, yo = int(an['xofs']) + f['x_offset'], int(an['yofs']) + f['y_offset']
        bb = br(f['shade'])
        key = (f['picnum'], f['pal'], 'mask')
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if f['cstat'] & 4:
            uvs = [(1 - u, v) for u, v in uvs]
        if f['cstat'] & 8:
            uvs = [(u, 1 - v) for u, v in uvs]
        top = SC[f['sector']](f['x'], f['y']) if cut is not None else -math.inf
        if al == 32:
            if f['z'] - 60 < top:
                continue
            tri(key, [V(x, y, f['z'] - 60) for x, y in footprint(f, (t.width, t.height), (xo, yo))], uvs, (0, 1, 0), bb)
            continue
        w = t.width * f['x_repeat'] / 4
        h = t.height * f['y_repeat'] * 4
        bottom = f['z'] + (h / 2 if f['cstat'] & 128 else 0) - yo * f['y_repeat'] * 4
        if bottom < top:
            continue
        if al == 16:
            a = f['angle'] * math.pi / 1024
            dx, dy, nx, ny = -math.sin(a), math.cos(a), math.cos(a), math.sin(a)
            x, y = f['x'] + nx * 8, f['y'] + ny * 8
            e0, e1 = (x + dx * w / 2, y + dy * w / 2), (x - dx * w / 2, y - dy * w / 2)
            if not (uncut and uncut(f)):
                key = (*key[:2], 'sign')
            tri(key, [V(*e0, bottom - h), V(*e1, bottom - h), V(*e1, bottom), V(*e0, bottom)], uvs, (nx, 0, ny), bb)
        else:
            out[('bill', f['picnum'], f['pal'])].append(
                (f['x'] / PU, -bottom / ZU, f['y'] / PU, .8 * w / PU, h / ZU, bb, 1. if f['cstat'] & 4 else 0., f['type']))
    return dict(tris={k: np.array(v, 'f4') for k, v in out.items()}, sectors=SE, walls=WA, polys=polys,
                sprites=sprites, sky=sky, tiles=T, ok={i for i in range(len(SE)) if kept[i] and i in polys},
                segs=segs, sprite_records=[F(s) for s in d.sprites])


def reachable(m, start):
    """The sectors joined to ``start`` by portals."""
    SE, WA = m['sectors'], m['walls']
    seen, st = {start}, [start]
    while st:
        i = st.pop()
        for w in range(SE[i]['wall_ptr'], SE[i]['wall_ptr'] + SE[i]['wall_count']):
            n = WA[w]['next_sector']
            if n >= 0 and n not in seen:
                seen.add(n)
                st.append(n)
    return seen


def start_sector(mapfile):
    """The sector of the first player start (type 1), or the largest sector."""
    d = read_map(mapfile)
    starts = sorted((F(s) for s in d.sprites if F(s)['type'] == 1), key=lambda f: f.get('data1', 0))
    if starts:
        return starts[0]['sector']
    m = build(mapfile, keep=lambda i, q, s: False)
    return max(m['polys'], key=lambda i: m['polys'][i].area)


def section_caps(m, margin=1600):
    """What is solid between the kept sectors, capped at the cut heights of the walls round it, and the model's sides down to its base.

    Returns (caps, sides, base, top) with base and top in render units (y up).
    """
    allp = unary_union([m['polys'][i].buffer(.5) for i in m['ok']])
    roi = allp.buffer(margin + 3600, join_style=2).buffer(-3600, join_style=2)
    roi = unary_union([Polygon(g.exterior) for g in _geoms(roi)])
    solid = roi.difference(allp)
    segs = m['segs']
    lines = [LineString([(a, b), (c, d)]) for a, b, c, d, _, _ in segs]
    tree = shapely.STRtree(lines)

    def heights(pts):
        P = shapely.points(np.asarray(pts, float))
        idx = tree.nearest(P)
        out = []
        for p, k in zip(P, idx):
            a, b, c, d, t0, t1 = segs[k]
            u = lines[k].project(p, normalized=True)
            out.append(t0 + (t1 - t0) * u)
        return np.array(out)
    floor_low = max(m['sectors'][i]['floor_z'] for i in m['ok'])
    base = -floor_low / ZU - 1.0
    tris = []
    for g in _geoms(solid):
        if g.area < 200 or g.geom_type != 'Polygon':
            continue
        for q in shapely.constrained_delaunay_triangles(g.segmentize(2048)).geoms:
            c = list(q.exterior.coords)[:3]
            hz = heights(c)
            for (x, y), z in zip(c, hz):
                tris.append((x / PU, -z / ZU, y / PU, x / PU, y / PU, 0, 1, 0, 1.))
    skirt = []
    for g in _geoms(roi):
        g = shapely.geometry.polygon.orient(g, 1.0)
        c = list(g.segmentize(1024).exterior.coords)
        hz = heights(c)
        for k in range(len(c) - 1):
            (xa, ya), (xb, yb) = c[k], c[k + 1]
            n = (yb - ya, -(xb - xa))
            l = math.hypot(*n) or 1
            n = (n[0] / l, 0, n[1] / l)
            P = [(xa / PU, -hz[k] / ZU, ya / PU), (xb / PU, -hz[k + 1] / ZU, yb / PU), (xb / PU, base, yb / PU), (xa / PU, base, ya / PU)]
            for j in (0, 1, 2, 0, 2, 3):
                skirt.append((*P[j], (P[j][0] + P[j][2]) / 6, -P[j][1] / 6, *n, .9))
    top = -min(min(s[4], s[5]) for s in segs) / ZU
    return (np.array(tris, 'f4').reshape(-1, 9), np.array(skirt, 'f4').reshape(-1, 9), np.zeros((0, 9), 'f4')), roi.bounds, base, top, -floor_low / ZU


VS = '''#version 430
in vec3 p; in vec2 uv; in vec3 n; in float b; uniform mat4 M; out vec3 wp; out vec2 t; out vec3 nn; out float br;
void main(){ wp=p; t=uv; nn=n; br=b; gl_Position=M*vec4(p,1); }'''
FS = '''#version 430
in vec3 wp; in vec2 t; in vec3 nn; in float br; uniform sampler2D tex; uniform int kind; uniform vec3 flat_; uniform vec4 plane; uniform vec4 boxx; uniform float emis; uniform vec3 tint; uniform float gain;
layout(location=0) out vec4 A; layout(location=1) out vec4 N; layout(location=2) out vec4 E;
void main(){
 if(wp.x<boxx.x||wp.x>boxx.y||wp.z<boxx.z||wp.z>boxx.w) discard;
 float pl=plane.x+plane.y*wp.z+plane.z*wp.x;
 if((kind&1)!=0 && wp.y>pl) discard;
 vec4 c=(kind&2)!=0?vec4(flat_,1):texture(tex,t);
 if((kind&4)!=0 && c.a<.5) discard;
 vec3 a=pow(c.rgb,vec3(2.2));
 vec3 nr=dot(nn,nn)>.01?normalize(nn):vec3(0,1,0);
 A=vec4(a*tint, br*gain); N=vec4(nr,1); E=vec4(a*emis,1);
}'''
QVS = '''#version 430
out vec2 q; void main(){ vec2 v=vec2((gl_VertexID<<1)&2,gl_VertexID&2); q=v; gl_Position=vec4(v*2-1,0,1);} '''
LFS = '''#version 430
in vec2 q; out vec4 o; uniform sampler2D A,N,E,D; uniform mat4 IM,MV; uniform vec3 eye; uniform int nl; uniform sampler2D L; uniform vec2 res;
uniform vec3 amb,sun,sund; uniform mat4 SM; uniform sampler2DShadow SD; uniform float ao_r; uniform vec3 bg0,bg1; uniform float fogy; uniform float lampk,floork,sidek; uniform vec3 grade;
vec3 pos(vec2 u){ float d=texture(D,u).r; vec4 h=IM*vec4(u*2-1,d*2-1,1); return h.xyz/h.w; }
float hash(vec2 p){ return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453); }
void main(){
 float d=texture(D,q).r;
 if(d>=1.){ o=vec4(0,0,0,0); return; }
 vec4 a=texture(A,q); vec3 n=normalize(texture(N,q).xyz+1e-6); vec3 e=texture(E,q).rgb; vec3 p=pos(q);
 vec3 v=normalize(eye-p); if(dot(n,v)<0.) n=-n;
 // occlusion, in world units
 float occ=0.; const int K=40; float rot=hash(q*res)*6.2831;
 for(int i=0;i<K;i++){ float f=(i+.5)/K; float r=ao_r*sqrt(f); float th=rot+2.39996*i;
   vec3 t1=normalize(abs(n.y)<.9?cross(n,vec3(0,1,0)):cross(n,vec3(1,0,0))), t2=cross(n,t1);
   vec3 sp=p+ (t1*cos(th)+t2*sin(th))*r*.8 + n*r*(.15+.6*fract(i*.618));
   vec4 c=MV*vec4(sp,1); vec2 u=c.xy/c.w*.5+.5; if(u.x<0.||u.x>1.||u.y<0.||u.y>1.) continue;
   vec3 o2=pos(u); float ds=dot(normalize(sp-eye),sp-eye)-dot(normalize(sp-eye),o2-eye);
   if(ds>.02 && ds<ao_r*2.5) occ+=1.; }
 float ao=pow(1.-occ/K,1.6);
 float bake=max(a.w,0.);
 vec4 s=SM*vec4(p+n*.06,1); vec3 sc=s.xyz*.5+.5; float sh=0.;
 for(int i=-2;i<=2;i++)for(int j=-2;j<=2;j++) sh+=texture(SD,vec3(sc.xy+vec2(i,j)/8192.*1.6,sc.z-.0006)); sh/=25.;
 float gr=p.y<grade.x?floork:p.y<grade.z?mix(sidek,1.,smoothstep(grade.y,grade.z,p.y)):1.;
 if(sc.x<0.||sc.x>1.||sc.y<0.||sc.y>1.) sh=1.;
 vec3 li=amb*ao*(.35+.65*bake)*(.6+.4*n.y) + sun*max(dot(n,-sund),0.)*sh*(.5+.5*bake); li*=gr;
 for(int i=0;i<nl;i++){ vec4 l0=texelFetch(L,ivec2(0,i),0), l1=texelFetch(L,ivec2(1,i),0); vec3 dl=l0.xyz-p; float dd=length(dl); if(dd>l0.w) continue;
   float at=pow(1.-dd/l0.w,2.)/(1.+dd*dd*1.1); li+=l1.rgb*at*(.25+.75*max(dot(n,dl/dd),0.))*mix(1.,ao,.6)*lampk; }
 vec3 c=a.rgb*li+e;
 o=vec4(c,1);
}'''


def look_at(eye, at, up=(0, 1, 0)):
    eye, at, up = map(lambda v: np.array(v, float), (eye, at, up))
    f = at - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    M = np.eye(4)
    M[0, :3], M[1, :3], M[2, :3] = s, u, -f
    M[:3, 3] = -M[:3, :3] @ eye
    return M


def persp(fov, asp, n, f):
    t = 1 / math.tan(math.radians(fov) / 2)
    P = np.zeros((4, 4))
    P[0, 0], P[1, 1], P[2, 2], P[2, 3], P[3, 2] = t / asp, t, (f + n) / (n - f), 2 * f * n / (n - f), -1
    return P


def ortho(w, h, n, f):
    P = np.eye(4)
    P[0, 0], P[1, 1], P[2, 2], P[2, 3] = 2 / w, 2 / h, -2 / (f - n), -(f + n) / (f - n)
    return P


class Renderer:
    """One map's triangles on a hidden GL context; ``shot`` draws a view of them.

    ``caps(m, plane)`` gives the solid's caps, the sides and the wells as
    vertex arrays; ``grade`` is (base, side foot, side top) for darkening the
    base and the sides; ``shadow`` the sun shadow's centre and width.
    """

    def __init__(self, m, caps, W=1600, H=1200, ss=2, bounds=(-999, 999, -999, 999), grade=(-9.95, -6., -2.6), shadow=((29, 0, 15), 110)):
        import moderngl
        self.gl = moderngl
        self.ctx = c = moderngl.create_standalone_context(require=430)
        self.W, self.H, self.ss = W, H, ss
        self.m, self.caps, self.bounds, self.grade, self.shadow = m, caps, bounds, grade, shadow
        self.prog = c.program(vertex_shader=VS, fragment_shader=FS)
        self.lp = c.program(vertex_shader=QVS, fragment_shader=LFS)
        self.tex = {}
        t = shade_table.tables(RES)
        self.pal = np.array(t['palette'], 'u1')
        ent = shade_table.read_rff(pathlib.Path(RES) / 'BLOOD.RFF')
        self.plu = {i: np.frombuffer(v[:256], 'u1') for (k, i, _), v in ent.items() if k == 'PLU'}
        self.vao = {}
        for k, v in self.m['tris'].items():
            if k[0] == 'bill':
                continue
            b = c.buffer(v.tobytes())
            self.vao[k] = (c.vertex_array(self.prog, [(b, '3f 2f 3f 1f', 'p', 'uv', 'n', 'b')]), len(v))

    def texture(self, pic, pal):
        key = (pic, pal)
        if key not in self.tex:
            t = self.m['tiles'][pic]
            ix = np.frombuffer(bytes(t.pixels), 'u1').reshape(t.width, t.height).T
            jx = self.plu[pal][ix] if pal in self.plu else ix
            rgb = self.pal[jx]
            a = np.where(ix == 255, 0, 255).astype('u1')
            if (a == 0).any() and (a > 0).any():
                # what lies under the holes is the nearest of what is drawn, so no fringe is mixed into the smaller mips
                from scipy.ndimage import distance_transform_edt as edt
                _, (iy, ix_) = edt(a == 0, return_indices=True)
                rgb = rgb[iy, ix_]
            tx = self.ctx.texture((t.width, t.height), 4, np.dstack([rgb, a]).tobytes())
            tx.build_mipmaps()
            tx.filter = (self.gl.LINEAR_MIPMAP_LINEAR, self.gl.NEAREST)
            tx.anisotropy = 16
            self.tex[key] = tx
        return self.tex[key]

    def shot(self, eye, at, fov=30, plane=(99, 0, 0), bounds=None, open_rooms=True, orth=None, amb=(.55, .30, .28), sun=(1.6, .5, .35),
             sund=(-.45, -.75, -.5), lampk=6., capcol=(.30, .25, .23), bloom=.9, roomgain=1.5, exposure=1.3, ao_r=1.1, bake=1.0, hide=(), streetgain=1.0,
             extra=None, roomtint=(1.25, .98, .72), watertint=(.10, .12, .15), decals=(), discs=(), candles=(), lights=(), floork=.05, sidek=.25, sidetile=110, sidetint=(.55, .5, .48), rooftile=6, rooftint=(.5, .45, .45)):
        """Linear light of one view, its coverage and the view matrix."""
        moderngl = self.gl
        bounds = bounds or self.bounds
        c, ss = self.ctx, self.ss
        W, H = self.W * ss, self.H * ss
        VM = look_at(eye, at)
        dist = np.linalg.norm(np.array(eye) - np.array(at))
        P = ortho(orth * W / H, orth, 1, dist * 3) if orth else persp(fov, W / H, max(1, dist * .1), dist * 4)
        M = P @ VM
        ga, gn, ge = (c.texture((W, H), 4, dtype='f2') for _ in range(3))
        dt = c.depth_texture((W, H))
        fb = c.framebuffer([ga, gn, ge], dt)
        pf = lambda x, y: plane[0] + plane[1] * y + plane[2] * x
        tr, sk, we = self.caps(self.m, pf)
        cap_v = [c.vertex_array(self.prog, [(c.buffer(v.tobytes()), '3f 2f 3f 1f', 'p', 'uv', 'n', 'b')]) if len(v) else None for v in (tr, sk, we)]
        right = VM[0, :3]
        bills = []
        glow = []
        for k, v in self.m['tris'].items():
            if k[0] != 'bill' or k[1] in hide:
                continue
            for x, y, z, w, h, b, fl, ty in v:
                r = right * w / 2
                r = np.array([r[0], 0, r[2]])
                r *= (w / 2) / (np.linalg.norm(r) or 1)
                q = [((x - r[0], y + h, z - r[2]), (fl, 0)), ((x + r[0], y + h, z + r[2]), (1 - fl, 0)), ((x + r[0], y, z + r[2]), (1 - fl, 1)), ((x - r[0], y, z - r[2]), (fl, 1))]
                bills.append((k, np.array([(*q[j][0], *q[j][1], 0, 1, 0, b) for j in (0, 1, 2, 0, 2, 3)], 'f4')))
                if k[1] in LAMPS:
                    L = LAMPS[k[1]]
                    if L[3]:
                        glow.append((x, y + h * L[4], z, 7.0, *[L[0] * L[3], L[1] * L[3], L[2] * L[3]], 0))
        for f in self.m['sprites']:
            if f['picnum'] == 795:
                glow.append((f['x'] / 1024, -f['z'] / ZU - .15, f['y'] / 1024, 5.0, .9, .72, .42, 0))
        for x, y, z, h in candles:
            w = h * 9 / 28
            bills.append((('bill', 938, 0), (x, y, z, w, h)))
            glow.append((x, y + h * .9, z, 16.0, 1.0 * h * .5, .5 * h * .5, .16 * h * .5, 0))
        glow += list(lights)
        bills = [(k, v) if not isinstance(v, tuple) else (k, np.array([(*q_, *uv_, 0, 1, 0, 1) for q_, uv_ in [(((v[0] + sx * right[0] * v[3] / 2), v[1] + sy * v[4], v[2] + sx * right[2] * v[3] / 2), ((sx + 1) / 2, 1 - sy)) for sx, sy in ((-1, 1), (1, 1), (1, 0), (-1, 1), (1, 0), (-1, 0))]], 'f4')) for k, v in bills]
        byk = {}
        for k, v in bills:
            byk.setdefault(k, []).append(v)

        def draw(MM, color):
            self.prog['M'].write(MM.T.astype('f4').tobytes())
            U = self.prog
            for n, v in (('plane', (*plane, 0)), ('boxx', bounds), ('flat_', capcol), ('emis', 0.), ('tint', (1, 1, 1)), ('gain', 1.)):
                if n in U:
                    U[n].value = v
            for k, (va, n) in self.vao.items():
                pic, pal, kind = k
                if kind == 'ceil' and open_rooms or pic in hide:
                    continue
                if kind != 'well':
                    self.texture(pic, pal).use(0)
                kd = {'spire': 0, 'wall': 1, 'room': 1, 'step': 0, 'solid': 0, 'ceil': 1, 'mask': 4, 'sign': 5, 'well': 3}[kind]
                if kind in ('room',):
                    c.enable(moderngl.CULL_FACE)
                if 'kind' in U:
                    U['kind'].value = kd
                if 'tint' in U:
                    U['tint'].value = roomtint if kind == 'room' else watertint if pal == 10 else (1, 1, 1)
                if 'gain' in U:
                    U['gain'].value = roomgain if kind in ('room',) else streetgain
                if kind in ('wall', 'room', 'step', 'spire', 'well'):
                    c.enable(moderngl.CULL_FACE)
                    c.front_face = 'cw'
                    c.cull_face = 'back'
                else:
                    c.disable(moderngl.CULL_FACE)
                va.render(moderngl.TRIANGLES)
            c.disable(moderngl.CULL_FACE)
            for k, vs in byk.items():
                self.texture(k[1], k[2]).use(0)
                U['kind'].value = 5
                U['emis'].value = 0. if not color else 5. if k[1] in LAMPS else 1.6 if k[1] == 938 and k[0] == 'bill' else 0.
                U['boxx'].value = (-999, 999, -999, 999) if k[1] == 938 else bounds
                U['plane'].value = (999, 0, 0, 0) if k[1] == 938 else (*plane, 0)
                b = c.buffer(np.concatenate(vs).tobytes())
                c.vertex_array(self.prog, [(b, '3f 2f 3f 1f', 'p', 'uv', 'n', 'b')]).render(moderngl.TRIANGLES)
            U['plane'].value = (*plane, 0)
            U['boxx'].value = bounds
            U['emis'].value = 0.
            U['gain'].value = 1.
            U['kind'].value = 0
            U['tint'].value = rooftint
            U['gain'].value = 1.0
            self.texture(rooftile, 0).use(0)
            if cap_v[0]:
                cap_v[0].render(moderngl.TRIANGLES)
            U['tint'].value = (1, 1, 1)
            U['kind'].value = 0
            U['tint'].value = sidetint
            self.texture(sidetile, 0).use(0)
            if cap_v[1]:
                cap_v[1].render(moderngl.TRIANGLES)
            U['tint'].value = (1, 1, 1)
            U['kind'].value = 2
            if open_rooms and cap_v[2]:
                U['kind'].value = 3
                c.enable(moderngl.CULL_FACE)
                c.front_face = 'cw'
                c.cull_face = 'back'
                cap_v[2].render(moderngl.TRIANGLES)
                c.disable(moderngl.CULL_FACE)
        rt, upv = VM[0, :3], VM[1, :3]

        def draw_extra():
            U = self.prog
            U['boxx'].value = (-999, 999, -999, 999)
            U['tint'].value = (1, 1, 1)
            for dec in decals:
                if len(dec) == 5:
                    verts, pic, tint_, em, gn_ = dec
                    U['kind'].value = 0 if pic >= 0 else 4
                    U['tint'].value = tint_
                    U['emis'].value = em
                    U['gain'].value = gn_
                    self.texture(pic, 0).use(0)
                    b = c.buffer(np.array(verts, 'f4').tobytes())
                    c.vertex_array(U, [(b, '3f 2f 3f 1f', 'p', 'uv', 'n', 'b')]).render(moderngl.TRIANGLES)
                    U['tint'].value = (1, 1, 1)
                    continue
                verts, col = dec
                U['kind'].value = 2
                U['flat_'].value = col
                U['emis'].value = 1.
                U['gain'].value = 0.
                b = c.buffer(np.array(verts, 'f4').tobytes())
                c.vertex_array(U, [(b, '3f 2f 3f 1f', 'p', 'uv', 'n', 'b')]).render(moderngl.TRIANGLES)
            for pic, pos, sz, em in discs:
                U['kind'].value = 4
                U['emis'].value = em
                U['gain'].value = 0.
                self.texture(pic, 0).use(0)
                pos = np.array(pos)
                q = [(pos + (-rt + upv) * sz, (0, 0)), (pos + (rt + upv) * sz, (1, 0)), (pos + (rt - upv) * sz, (1, 1)), (pos + (-rt - upv) * sz, (0, 1))]
                b = c.buffer(np.array([(*q[j][0], *q[j][1], 0, 1, 0, 1) for j in (0, 1, 2, 0, 2, 3)], 'f4').tobytes())
                c.vertex_array(U, [(b, '3f 2f 3f 1f', 'p', 'uv', 'n', 'b')]).render(moderngl.TRIANGLES)
        # the sky's light, with a shadow
        SZ = 8192
        sdt = c.depth_texture((SZ, SZ))
        sfb = c.framebuffer([], sdt)
        sd = np.array(sund) / np.linalg.norm(sund)
        ctr, span = np.array(self.shadow[0]), self.shadow[1]
        SMx = ortho(span, span, 1, 300 * span / 110) @ look_at(ctr - sd * 120 * span / 110, ctr)
        c.enable(moderngl.DEPTH_TEST)
        sfb.use()
        sfb.clear(depth=1.)
        draw(SMx, False)
        sdt.compare_func = '<='
        fb.use()
        fb.clear(0, 0, 0, 0, depth=1.)
        draw(M, True)
        draw_extra()
        c.disable(moderngl.DEPTH_TEST)
        hdr = c.texture((W, H), 4, dtype='f2')
        hfb = c.framebuffer([hdr])
        hfb.use()
        hfb.clear()
        dt.compare_func = ''
        for j, (n, t_) in enumerate((('A', ga), ('N', gn), ('E', ge), ('D', dt))):
            t_.use(j)
            if n in self.lp:
                self.lp[n].value = j
        gl = np.array(glow, 'f4').reshape(-1, 2, 4)
        lt = c.texture((2, max(1, len(gl))), 4, gl.tobytes(), dtype='f4')
        lt.filter = (moderngl.NEAREST, moderngl.NEAREST)
        lt.use(4)
        sdt.use(5)
        vals = dict(L=4, SD=5, nl=len(gl), res=(W, H), eye=tuple(eye), amb=amb, sun=sun, sund=tuple(sd), ao_r=ao_r, lampk=lampk, floork=floork, sidek=sidek,
                    grade=tuple(self.grade))
        for k, v in vals.items():
            if k in self.lp:
                self.lp[k].value = v
        self.lp['IM'].write(np.linalg.inv(M).T.astype('f4').tobytes())
        self.lp['MV'].write(M.T.astype('f4').tobytes())
        self.lp['SM'].write(SMx.T.astype('f4').tobytes())
        va = c.vertex_array(self.lp, [])
        va.render(moderngl.TRIANGLES, vertices=3)
        x = np.frombuffer(hdr.read(), 'f2').reshape(H, W, 4)[::-1].astype('f4')
        x = np.nan_to_num(x, nan=0., posinf=0., neginf=0.)
        x = np.clip(x, 0, 40)
        x = x.reshape(H // ss, ss, W // ss, ss, 4).mean((1, 3))
        for r_ in (ga, gn, ge, dt, fb, hdr, hfb, sdt, sfb, lt):
            r_.release()
        self.M = M
        rgb, alpha = x[..., :3], x[..., 3:]
        return rgb * exposure, alpha, M


def tonemap(rgb, bloom=.9, th=.9):
    import cv2
    l = rgb.max(2, keepdims=True)
    br_ = rgb * np.clip((l - th) / th, 0, 1)
    b = sum(cv2.GaussianBlur(br_, (0, 0), s) * w for s, w in ((3, .5), (10, .35), (30, .3)))
    x = rgb + b * bloom
    x = x * (2.51 * x + .03) / (x * (2.43 * x + .59) + .14)
    return np.clip(x, 0, 1) ** (1 / 2.2)


def save(rgb, path):
    from PIL import Image
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype('u1')).save(path)


def fit_camera(points, az, el, fov, aspect, fill=.92):
    """An eye and a target that frame ``points`` (render units, n x 3) seen from azimuth ``az`` (0: from the map's +y) and elevation ``el``."""
    pts = np.asarray(points, float)
    at = (pts.min(0) + pts.max(0)) / 2
    a, e = math.radians(az), math.radians(el)
    d = np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)])
    corners = np.c_[pts, np.ones(len(pts))]
    P = persp(fov, aspect, .1, 1e5)
    lo, hi = 1., 1e4
    for _ in range(60):
        r = (lo + hi) / 2
        q = (P @ look_at(at + d * r, at) @ corners.T).T
        ndc = q[:, :2] / q[:, 3:4]
        if (q[:, 3] > 0).all() and np.abs(ndc).max() <= fill:
            hi = r
        else:
            lo = r
    q = (P @ look_at(at + d * hi, at) @ corners.T).T
    ndc = q[:, :2] / q[:, 3:4]
    # centre what is seen, not the box's middle
    inv = np.linalg.inv(P @ look_at(at + d * hi, at))
    shift = (ndc.max(0) + ndc.min(0)) / 2
    VMr = look_at(at + d * hi, at)
    at2 = at + VMr[0, :3] * shift[0] * hi * math.tan(math.radians(fov) / 2) * aspect + VMr[1, :3] * shift[1] * hi * math.tan(math.radians(fov) / 2)
    return tuple(at2 + d * hi), tuple(at2)


LIGHT = {
    'dusk': dict(amb=(.95, .78, .80), sun=(2.0, .95, .68), lampk=10., roomgain=2.2, exposure=1.45, floork=.10, sidek=.35),
    'day': dict(amb=(1.0, .97, .95), sun=(2.4, 2.15, 1.85), lampk=5., roomgain=2.0, exposure=1.25, floork=.10, sidek=.35,
                roomtint=(1.15, 1.0, .85), rooftint=(.45, .43, .42)),
}


def model(mapfile, cut_bodies=1.6, everything=False, empty=True, W=1600, H=1200, ss=2):
    """A Renderer of a whole map cut ``cut_bodies`` player heights over each floor, its box and its sides' points (render units)."""
    p = played(mapfile, empty)
    keep = None
    if not everything:
        m0 = build(p, keep=lambda i, q, s: False)
        ok = reachable(m0, start_sector(mapfile))
        keep = lambda i, q, s: i in ok
    m = build(p, keep=keep, cut=cut_bodies * BODY)
    caps, (bx0, by0, bx1, by1), base, top, low = section_caps(m)
    R = Renderer(m, lambda m_, pf: caps, W, H, ss, bounds=(-999, 999, -999, 999), grade=(base - .5, base, low),
                 shadow=(((bx0 + bx1) / 2 / PU, (base + top) / 2, (by0 + by1) / 2 / PU), 1.25 * max(bx1 - bx0, by1 - by0) / PU))
    return R, ((bx0 / PU, bx1 / PU), (base, top), (by0 / PU, by1 / PU)), caps[1][:, :3]


def ground(box3, tile=253, tint=(.22, .19, .19)):
    """A floor under the model, to take its shadow."""
    (x0, x1), (y0, _), (z0, z1) = box3
    cx, cz, r = (x0 + x1) / 2, (z0 + z1) / 2, 8 * max(x1 - x0, z1 - z0)
    q = [(cx - r, cz - r), (cx + r, cz - r), (cx + r, cz + r), (cx - r, cz + r)]
    return (([(x, y0 - .03, z, x / 18, z / 18, 0, 1, 0, 1) for j in (0, 1, 2, 0, 2, 3) for x, z in [q[j]]]), tile, tint, 0., .8)


def finish(rgb, vignette=True):
    import cv2
    x = tonemap(rgb, bloom=.5, th=1.0)
    l = x.mean(2, keepdims=True)
    x = np.clip(l + (x - l) * 1.08, 0, 1)
    x = np.clip(x + .35 * (x - cv2.GaussianBlur(x.astype('f4'), (0, 0), 1.0)), 0, 1)
    if vignette:
        H, W = x.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W]
        v = 1 - .5 * np.clip(((xx - W / 2) / (W * .6)) ** 2 + ((yy - H * .52) / (H * .62)) ** 2 - .55, 0, 1)
        x = x * v[..., None]
    return x


def resolve(name):
    """A MAP path, a corpus map's name (E3M1) or a project's name (blood-city: the map it plays)."""
    p = pathlib.Path(name)
    if p.is_file():
        return p
    from bloodmap.corpus import corpus_map_path
    found = corpus_map_path(name, missing_ok=True)
    if found and (ROOT / found).is_file():
        return ROOT / found
    from bloodmap.project import named
    pr = named(name)
    return pr.path('played') or pr.map()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('map', help='a corpus name (E3M1), a project (blood-city) or a MAP path')
    ap.add_argument('-o', '--out', help='PNG to write (default work/map_model/<name>.png)')
    ap.add_argument('--az', type=float, default=20., help='degrees round from the map\'s +y side (the bottom of the editor), clockwise seen from above')
    ap.add_argument('--el', type=float, default=42., help='degrees above the horizon')
    ap.add_argument('--fov', type=float, default=32.)
    ap.add_argument('--cut', type=float, default=1.6, help='player heights over each floor where the rooms are cut')
    ap.add_argument('--light', choices=sorted(LIGHT), default='dusk')
    ap.add_argument('--size', default='1600x1200')
    ap.add_argument('--ss', type=int, default=2, help='supersampling')
    ap.add_argument('--all', action='store_true', help='every sector, not only those reachable from the start')
    ap.add_argument('--full', action='store_true', help='keep enemies and pickups')
    a = ap.parse_args(argv)
    path = resolve(a.map)
    W, H = map(int, a.size.lower().split('x'))
    R, box3, outline = model(path, a.cut, a.all, not a.full, W, H, a.ss)
    eye, at = fit_camera(outline, a.az, a.el, a.fov, W / H)
    light = dict(LIGHT[a.light])
    rgb, alpha, _ = R.shot(eye=eye, at=at, fov=a.fov, decals=[ground(box3)], **light)
    out = pathlib.Path(a.out) if a.out else ROOT / 'work' / 'map_model' / f'{path.stem}.png'
    save(finish(rgb), out)
    print(f'{path.name}: {len(R.m["ok"])} sectors drawn, cut at {a.cut} bodies -> {out}')


if __name__ == '__main__':
    main()
