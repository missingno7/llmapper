"""Light a finished map as the 3D scene it is: lights set in rows where its rooms want them, the light traced, and floors and walls cut where it changes.

The owner, 2026-11-20 and 21, over one evening of walking the city: the
light must come from a sun and from lamps ("we should be able to map the
light like it is 3D thing with real shadows"), a big floor whose light
conflicts is cut where it changes, along the light's own contour and not in
blocks; rooms are lit by lights of the kind that fits them, in regular rows
("it looks like you are just scattering stuff on the ceiling"); sewers keep
"more light vs shadow"; long walls fade along their length. And, of putting
it into the build: "Lighting shouldn't make modifying and extending map
harder."

So this is a STAGE on a finished map, never a part of its source. It reads
the map and which room each sector belongs to; it adds light sprites and
panel sectors, cuts pieces off floors and walls, and writes every shade. It
changes no sector's index (pieces are appended, `report["parent"]` names
each one's original), cuts no sector that carries anything but its shade
(`overlays.shade_only`), and is the same map every time it runs on the same
input (the rays are fixed directions, every loop is in index order). A
level that changes is lit again from scratch; nothing here is kept.

The steps, each its own function:

0. `cut_shadows` -- an open floor the sun half lights is cut along its
   shadow's edge, one straight edge (cut by bands alone, a sharp edge
   becomes a stack of strips).
1. `lay_lights` -- per room, a `Rule` (its kind of light and the spacing);
   points in rows along the room's long axis; a panel is a recessed sector
   of a whole tile, a sprite is a clean record (`SPRITES`).
2. `band_floors` -- a floor whose traced light spans `FLOOR_SPREAD` shades
   is traced on a grid, smoothed, and cut along the filled contours of every
   `FLOOR_BAND` shades, simplified to straight runs.
3. `band_walls` -- a straight wall at least `WALL_LONG` long is traced
   every `WALL_STEP` along and split where its light crosses a
   `WALL_BAND`-shade band.
4. `shade` -- the whole map traced once more and every floor, ceiling and
   wall given its light; the sky takes one shade and its sprites the floor's.
5. `switch_lamps` -- a lamp that blinks or is put out takes its light with it:
   the map is traced without it, and every sector that changes moves with it.

The model's terms and their calibration are `daylight`'s.
"""

from __future__ import annotations

import math
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from . import daylight as D
from . import light_kinds as K
from . import overlays as O
from .model import DiskObject, record_fields as _f

# --- the model -----------------------------------------------------------------


@dataclass
class Model:
    """The light the city is drawn in: one sun, its lamps, a bounce, and the dark underground."""

    #: due west, 45 degrees up: the one azimuth that predicts the campaign's
    #: road shade cuts (10 of 11 in E3M1; no other above 7)
    sun: D.Sun = field(default_factory=lambda: D.Sun(270, 45))
    #: lamp 2.4 at `daylight.LAMP_POWER` 4 with a base light indoors of 0.10:
    #: tight pools, bright under a light and dark between (the owner,
    #: 2026-11-21: "make like the lighting like more visible", and of the
    #: frames: "it looks good"). Each view's light-to-dark spread grew (the
    #: concourse 54 to 62, the chancel 47 to 62) with the rooms about as
    #: bright, and the streets as they were. (History: 1.3 with only lamps on
    #: walls and ceilings lighting; 0.8 once every lamp lit, at power 2 and
    #: base light 0.30.)
    weights: D.Weights = field(default_factory=lambda: D.Weights(
        sun=2.0, lamp=2.4, dark=39.0, bright=8.0, reference=1.3, bounce=1.0,
        indoor_ambient=0.10))
    #: a roofed sector with its floor this deep is under the street (the sewer,
    #: the crypt): near dark between its lights, its lamps a little stronger,
    #: so the light lies in pools with darkness between
    underground_z: int = 40000
    underground_ambient: float = 0.05
    underground_lamp: float = 1.2
    #: how strong the lamps of a sector are, where a place asks for other
    #: than 1 (a church is dimmer than a shop); filled by `run`
    lamp_scale_by_sector: dict = field(default_factory=dict)

    def underground(self, disk, sector: int) -> bool:
        f = _f(disk.sectors[sector])
        return int(f["floor_z"]) >= self.underground_z and not int(f["ceiling_stat"]) & 1

    def lamps(self, disk) -> list:
        return [(x, y, z, sector, strength * (self.underground_lamp if self.underground(disk, sector) else 1.0)
                 * self.lamp_scale_by_sector.get(sector, 1.0), *rest)
                for x, y, z, sector, strength, *rest in D.lights_of(disk)]

    def prepare(self, disk) -> None:
        self.weights.ambient_by_sector = {i: self.underground_ambient
                                          for i in range(len(disk.sectors)) if self.underground(disk, i)}

    def trace(self, disk, *, wall_spacing: int = D.WALL_SPACING, wall_max: int = D.WALL_MAX) -> list:
        """Every surface's samples, lit by sky, sun, lamps and one bounce.

        The same numbers as `daylight.light_with_bounce`, traced by
        `WORKERS` processes: the direct light first, then the bounce
        gathered from it.
        """
        self.prepare(disk)
        saved = D.WALL_SPACING, D.WALL_MAX
        D.WALL_SPACING, D.WALL_MAX = wall_spacing, wall_max
        try:
            found = D.surfaces(disk)
        finally:
            D.WALL_SPACING, D.WALL_MAX = saved
        samples = [p for s in found for p in s.samples]
        sun, lamps = self.sun.vector(), self.lamps(disk)
        for p, (sky, sunlit, lamp) in zip(samples, _parallel(disk, sun, lamps, None, _direct_job, samples)):
            p.sky, p.sun, p.lamp = sky, sunlit, lamp
        cache = D.BounceCache(found, D.Weights(sun=self.weights.sun, lamp=self.weights.lamp))
        for p, bounce in zip(samples, _parallel(disk, sun, lamps, cache.points, _bounce_job, samples)):
            p.bounce = bounce
        return found


# --- tracing in parallel --------------------------------------------------------
#
# Each worker reads the map once and keeps its own hitscan index; a job is a
# run of samples, and the answers come back in order, so the result is the
# same whatever the number of workers. A small map is traced in this process.

#: processes tracing at once
WORKERS = max(1, min(24, (os.cpu_count() or 1) - 2))
#: below this many samples the pool costs more than it saves
PARALLEL_FROM = 4000
#: samples per job
CHUNK = 64

_STATE: dict[str, Any] = {}
#: `daylight`'s settings a worker must share with this process: a worker
#: imports the module afresh, and a value set here would not reach it
TUNABLES = ("LAMP_CORE", "LAMP_POWER", "LAMP_PIVOT", "LAMP_SURFACE", "LAMP_REACH", "SKY_RAYS", "GATHER_RAYS", "REFLECTANCE")


def _start(disk_or_path, sun, lamps, cache_points, tunables=None) -> None:
    from .lightbomb import ScanIndex

    for name, value in (tunables or {}).items():
        setattr(D, name, value)

    if isinstance(disk_or_path, str):
        from .format import read_map
        disk = read_map(disk_or_path)
    else:
        disk = disk_or_path
    cache = None
    if cache_points is not None:
        cache = D.BounceCache([], D.Weights())
        cache.points = cache_points
    _STATE.clear()
    _STATE.update(disk=disk, scan=ScanIndex(disk), dome=D._hemisphere(D.SKY_RAYS),
                  sphere=D._sphere(D.GATHER_RAYS), sun=sun, lamps=lamps, cache=cache)


def _direct_job(samples: list) -> list:
    s = _STATE
    out = []
    for p in samples:
        D.light_point(s["disk"], s["scan"], p, s["dome"], s["sun"], s["lamps"])
        out.append((p.sky, p.sun, p.lamp))
    return out


def _bounce_job(samples: list) -> list:
    s = _STATE
    return [D.bounce_point(s["disk"], s["scan"], p, s["sphere"], s["cache"]) for p in samples]


def _full_job(samples: list) -> list:
    """Direct light and bounce for points that no surface's cache holds (a floor's grid)."""
    s = _STATE
    out = []
    for p in samples:
        D.light_point(s["disk"], s["scan"], p, s["dome"], s["sun"], s["lamps"])
        p.bounce = D.bounce_point(s["disk"], s["scan"], p, s["sphere"], s["cache"])
        out.append((p.sky, p.sun, p.lamp, p.bounce))
    return out


def _parallel(disk, sun, lamps, cache_points, job, samples: list) -> list:
    chunks = [samples[i:i + CHUNK] for i in range(0, len(samples), CHUNK)]
    if WORKERS <= 1 or len(samples) < PARALLEL_FROM:
        _start(disk, sun, lamps, cache_points)
        try:
            return [r for chunk in chunks for r in job(chunk)]
        finally:
            _STATE.clear()
    import tempfile
    from concurrent.futures import ProcessPoolExecutor

    from .format import write_map

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "trace.MAP")
        write_map(disk, path)
        tunables = {name: getattr(D, name) for name in TUNABLES}
        with ProcessPoolExecutor(WORKERS, initializer=_start,
                                 initargs=(path, sun, lamps, cache_points, tunables)) as pool:
            return [r for part in pool.map(job, chunks) for r in part]


# --- 1. the lights --------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    """How a room is lit: the form, its tile, and the spacing along and across the room."""

    form: str            # "panel", "ceiling", "hanging", "pairs" (standing, along the two long walls),
    #                      or "none" (the room's own lights only)
    tile: int
    along: int
    across: int = 0
    shade_bias: tuple[int, int, int] = (0, 0, 0)  # floor, ceiling, wall
    #: whether its floors and walls may be cut where the light changes. A place
    #: already authored in pieces (a ring of steps in arcs) is lit piece by piece
    #: without: the cuts of the Cabal's three round tiers cost 600 walls.
    cut: bool = True


#: a light sprite as the campaign sets it down (its first use, E1M1/E1M2/E1M4),
#: without what that use was wired to: (cstat, shade, x_repeat, y_repeat).
#: The first version copied those sprites whole, and 19 panels in the city
#: became toggle switches sending on the campaign's channel 114.
SPRITES: dict[int, tuple[int, int, int, int]] = {
    795: (160, -8, 48, 48),
    676: (160, -128, 40, 40),
    641: (129, 0, 64, 64),
    560: (385, -128, 64, 64),
    580: (384, -128, 64, 64),
    2290: (160, -8, 64, 64),
    796: (160, -128, 64, 48),
}
#: no light nearer a wall than this (plan units)
MARGIN = 768
#: a panel is recessed this far above its room's ceiling (the campaign: 1024)
RECESS = 1024
#: a room is a roofed space at least this high somewhere, and this large
ROOM_HEIGHT = 12000
ROOM_AREA = 0.5e6
#: the lowest a roofed sector may be to count toward a room at all
LOW = 4096


def rooms_by_region(disk, region_of: dict[int, str], skip: frozenset = frozenset(),
                    room_key: Callable[[str], str] | None = None) -> dict[str, list[int]]:
    """Roofed sectors grouped into rooms: a region and the regions named under it that are its furniture.

    A light hangs above a pew: a region under another (`a/b` under `a`) is
    folded into it when `a` has the height of a room.
    """
    by_region: dict[str, list[int]] = defaultdict(list)
    for i, sector in enumerate(disk.sectors):
        f = _f(sector)
        if i in skip or int(f["ceiling_stat"]) & 1 or int(f["floor_z"]) - int(f["ceiling_z"]) < LOW:
            continue
        region = region_of.get(i, "")
        by_region[room_key(region) if room_key else region].append(i)

    def tall(secs):
        return any(int(_f(disk.sectors[i])["floor_z"]) - int(_f(disk.sectors[i])["ceiling_z"]) >= ROOM_HEIGHT
                   for i in secs)

    keys = sorted(by_region, key=lambda k: (len(k), k))
    rooms: dict[str, list[int]] = defaultdict(list)
    for region in keys:
        home = next((k for k in keys if k != region and region.startswith(k + "/") and tall(by_region[k])), region)
        rooms[home].extend(by_region[region])
    return {k: sorted(v) for k, v in sorted(rooms.items())}


def _grid(poly, along: int, across: int, margin: int):
    """Points in rows along the polygon's long axis, evenly spaced and centred."""
    minx, miny, maxx, maxy = poly.bounds
    long_x = (maxx - minx) >= (maxy - miny)
    length = (maxx - minx) if long_x else (maxy - miny)
    width = (maxy - miny) if long_x else (maxx - minx)
    n = max(1, int(round((length - 2 * margin) / along)) + 1) if length > 2 * margin else 1
    m = max(1, int(round((width - 2 * margin) / across)) + 1) if across and width > 2 * margin + across else 1
    pts = []
    for i in range(n):
        t = (i + 0.5) / n
        for j in range(m):
            u = (j + 0.5) / m
            x = minx + (t * (maxx - minx) if long_x else u * (maxx - minx))
            y = miny + (u * (maxy - miny) if long_x else t * (maxy - miny))
            pts.append((x, y))
    return pts, long_x


def _add_sprite(disk, art, tile: int, x: float, y: float, sector: int, form: str) -> bool:
    from .placement import drawn_extent

    cstat, shade, xr, yr = SPRITES[tile]
    sec = _f(disk.sectors[sector])
    f = {"x": int(x), "y": int(y), "z": 0, "cstat": cstat, "picnum": tile, "shade": shade, "pal": 0,
         "clipdist": 32, "detail": 0, "x_repeat": xr, "y_repeat": yr, "x_offset": 0, "y_offset": 0,
         "sector": int(sector), "status": 0, "angle": 0, "owner": -1, "index": len(disk.sprites),
         "y_velocity": 0, "initial_type": 0, "type": 0, "flags": 0, "extra": -1}
    if form == "ceiling":
        f["cstat"] = 160                                  # flat on the ceiling, centred
        f["z"] = int(sec["ceiling_z"]) + 64
        f["shade"] = min(shade, -16)
    else:
        a = art[tile]
        top, bottom = drawn_extent(a.height, int(a.animation["yofs"]), yr, cstat, 0)
        if form == "hanging":
            # hung from the ceiling; if the chain is longer than the room
            # allows, lifted so its foot clears the floor and its chain runs
            # up into the ceiling (the owner, 2026-11-21: "lanterns on chain,
            # you can simply let it sink into ceiling and it looks good") --
            # as long as the lamp itself is below the ceiling
            f["z"] = min(int(sec["ceiling_z"]) - top, int(sec["floor_z"]) - LOW - bottom)
            head = f["z"] + top + (bottom - top) * K.KINDS[tile].point
            if head < int(sec["ceiling_z"]) + 512:
                return False
        else:                                             # standing on the floor
            f["z"] = int(sec["floor_z"]) - bottom
            if f["z"] + top < int(sec["ceiling_z"]) + 512:
                return False
    disk.sprites.append(DiskObject(fields=f))
    return True


def lay_lights(disk, rooms: dict[str, list[int]], rule_for: Callable[[str], Rule], art=None,
               whole: frozenset = frozenset()) -> dict[str, Any]:
    """Light every room by its rule; a room that has the map's own lights keeps them and is filled up to its count; a panel is never let into a sector of `whole`."""
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union

    from .sector_geom import outline_and_holes

    if art is None:
        from .shade_table import _art
        art = _art()
    S = [_f(s) for s in disk.sectors]

    def height(i):
        return int(S[i]["floor_z"]) - int(S[i]["ceiling_z"])

    room_of = {i: name for name, secs in rooms.items() for i in secs}
    existing: dict[str, int] = defaultdict(int)
    for sp in disk.sprites:
        f = _f(sp)
        if K.is_lamp(int(f["picnum"])) and not int(f["cstat"]) & 0x8000 and int(f["sector"]) in room_of:
            existing[room_of[int(f["sector"])]] += 1
    polys = {}
    for secs in rooms.values():
        for i in secs:
            try:
                o, h = outline_and_holes(disk, i)
                polys[i] = Polygon(o, h).buffer(0)
            except Exception:
                pass

    placed: dict[str, dict[str, int]] = {}
    panels: dict[int, list] = defaultdict(list)
    for name, secs in sorted(rooms.items()):
        room = unary_union([polys[i] for i in secs if i in polys])
        if room.is_empty or room.area < ROOM_AREA or not any(height(i) >= ROOM_HEIGHT for i in secs):
            continue
        rule = rule_for(name)
        if rule.form == "none":
            placed[name] = {"its own lights": existing[name]}
            continue
        inner = room.buffer(-MARGIN, join_style=2)
        if inner.is_empty:
            continue
        got: dict[str, int] = defaultdict(int)
        if rule.form == "pairs":                         # along the two long walls, in matching pairs
            minx, miny, maxx, maxy = room.bounds
            pts, long_x = _grid(room, rule.along, 0, MARGIN)
            for x, y in pts:
                for side in (0, 1):
                    px, py = ((x, miny + 512 if side == 0 else maxy - 512) if long_x
                              else (minx + 512 if side == 0 else maxx - 512, y))
                    sec = next((i for i in secs if i in polys and polys[i].buffer(-64).contains(Point(px, py))), None)
                    if sec is not None and _add_sprite(disk, art, rule.tile, px, py, sec, "standing"):
                        got[f"{rule.tile} pair"] += 1
            placed[name] = dict(got)
            continue
        pts, long_x = _grid(room, rule.along, rule.across, MARGIN)
        if len(pts) <= existing[name]:
            placed[name] = {"kept the map's own": existing[name]}
            continue
        tall = [i for i in secs if i in polys and height(i) >= ROOM_HEIGHT]
        spots = []
        for x, y in pts:
            p = Point(x, y)
            if not inner.contains(p):
                continue
            sec = next((i for i in tall if polys[i].contains(p)), None)
            if sec is None:                               # over furniture: from the nearest ceiling of the room
                sec = min(tall, key=lambda i: (polys[i].distance(p), i), default=None)
                if sec is not None and polys[sec].distance(p) > 256:
                    sec = None
            if sec is not None:
                spots.append((x, y, sec))
        if rule.form == "panel":
            # one kind per room: panels only if every spot takes a whole panel
            w, l = K.KINDS[rule.tile].panel
            wx, wy = (l, w) if long_x else (w, l)        # along the room's long axis
            rects = []
            for x, y, sec in spots:
                x0 = round((x - wx / 2) / wx) * wx         # whole tiles on the texture grid
                y0 = round((y - wy / 2) / wy) * wy
                rect = box(x0, y0, x0 + wx, y0 + wy)
                ok = (polys[sec].buffer(-256, join_style=2).contains(rect) and O.shade_only(disk.sectors[sec])
                      and not (int(S[sec]["floor_stat"]) | int(S[sec]["ceiling_stat"])) & 2
                      and sec not in whole and height(sec) >= 16960 + RECESS)
                rects.append((rect, sec) if ok else None)
            if rects and all(rects):
                for rect, sec in rects:
                    panels[sec].append((rect, rule.tile, long_x))
                    got[f"panel {rule.tile}"] += 1
                placed[name] = dict(got)
                continue
            tile = rule.tile if rule.tile in SPRITES else 795
            for x, y, sec in spots:
                if _add_sprite(disk, art, tile, x, y, sec, "ceiling"):
                    got[f"ceiling {tile}"] += 1
        elif rule.form == "hanging":
            # one kind per room: chain lamps only if every spot has the height
            cstat, _, _, yr = SPRITES[rule.tile]
            a = art[rule.tile]
            from .placement import drawn_extent
            top, bottom = drawn_extent(a.height, int(a.animation["yofs"]), yr, cstat, 0)
            # a chain may run up into the ceiling; the lamp must hang below it
            point = K.KINDS[rule.tile].point

            def head(sec):
                z = min(int(S[sec]["ceiling_z"]) - top, int(S[sec]["floor_z"]) - LOW - bottom)
                return z + top + (bottom - top) * point

            fits = all(head(sec) >= int(S[sec]["ceiling_z"]) + 512 for _, _, sec in spots)
            tile, form = (rule.tile, "hanging") if fits else (676, "ceiling")
            for x, y, sec in spots:
                if _add_sprite(disk, art, tile, x, y, sec, form):
                    got[f"{form} {tile}"] += 1
        else:
            for x, y, sec in spots:
                if _add_sprite(disk, art, rule.tile, x, y, sec, "ceiling"):
                    got[f"ceiling {rule.tile}"] += 1
        placed[name] = dict(got)

    jobs = {}
    for sec, items in sorted(panels.items()):
        specs = []
        for k, (rect, tile, swapped) in enumerate(items):
            stat = int(S[sec]["ceiling_stat"]) & ~(64 | 4)
            if swapped:
                stat |= 4
            specs.append(O.OverlaySpec(
                overlay_id=f"panel{k}:{sec}", region_id=str(sec),
                shapes=((tuple(map(tuple, rect.exterior.coords[:-1])), ()),),
                surface={"ceiling_picnum": tile, "ceiling_shade": 0, "ceiling_pal": 0, "ceiling_stat": stat,
                         "ceiling_x_panning": 0, "ceiling_y_panning": 0,
                         "ceiling_z": int(S[sec]["ceiling_z"]) - RECESS}))
        jobs[sec] = specs
    cut = _cut(disk, jobs)
    return {"rooms": placed, "cut": cut}


# --- 0. the sun's shadows -------------------------------------------------------

#: an open floor is cut along the sun's shadow where its light spans this many shades
SHADOW_SPREAD = 16
#: whether the sun reaches is looked at on a grid this fine (plan units)
SHADOW_CELL = 128
#: no shadow piece smaller than this (plan units squared)
SHADOW_PIECE = 512 * 512


def _sun_job(points: list) -> list:
    s = _STATE
    return [D._sky_hit(s["disk"], D._trace(s["disk"], s["scan"], p, s["sun"])) for p in points]


def cut_shadows(disk, model: Model, keep: frozenset = frozenset()) -> dict[str, Any]:
    """Cut every open floor the sun half lights along the edge of its shadow: one straight edge, before any band.

    A shadow's edge is sharp; cut by light bands alone it becomes a stack of
    thin strips. With the sun due west the edges run along the axes, so the
    shadowed cells are joined and closed square.
    """
    from shapely import set_precision
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union

    from .sector_geom import outline_and_holes

    found = model.trace(disk)
    rows = {(r["kind"], r["index"]): r for r in D.collapse(found, model.weights)}
    grids = []
    for s in found:
        if s.kind != "floor" or s.index in keep:
            continue
        f = _f(disk.sectors[s.index])
        if (not int(f["ceiling_stat"]) & 1
                or rows.get(("floor", s.index), {}).get("spread", 0) < SHADOW_SPREAD
                or not O.shade_only(disk.sectors[s.index]) or (int(f["floor_stat"]) | int(f["ceiling_stat"])) & 2):
            continue
        o, h = outline_and_holes(disk, s.index)
        poly = Polygon(o, h)
        if poly.area < FLOOR_MIN_AREA:
            continue
        minx, miny, maxx, maxy = poly.bounds
        pts = []
        y = miny + SHADOW_CELL / 2
        while y < maxy:
            x = minx + SHADOW_CELL / 2
            while x < maxx:
                if poly.contains(Point(x, y)):
                    pts.append(D.Sample(x, y, int(f["floor_z"]) - 64, s.index, (0.0, 0.0, -1.0)))
                x += SHADOW_CELL
            y += SHADOW_CELL
        grids.append((s.index, poly, pts))
    flat = [p for _, _, pts in grids for p in pts]
    lit = iter(_parallel(disk, model.sun.vector(), [], None, _sun_job, flat))
    jobs = {}
    for sector, poly, pts in grids:
        reached = [next(lit) for _ in pts]
        cells = [box(p.x - SHADOW_CELL / 2, p.y - SHADOW_CELL / 2, p.x + SHADOW_CELL / 2, p.y + SHADOW_CELL / 2)
                 for p, r in zip(pts, reached) if not r]
        if not cells or all(not r for r in reached):
            continue
        shadow = unary_union(cells)
        # close small gaps and open small notches, keeping corners square
        shadow = shadow.buffer(SHADOW_CELL, join_style=2).buffer(-2 * SHADOW_CELL, join_style=2) \
            .buffer(SHADOW_CELL, join_style=2)
        shadow = set_precision(shadow.intersection(poly), 1.0)
        parts = [g for g in getattr(shadow, "geoms", [shadow]) if g.geom_type == "Polygon" and g.area > SHADOW_PIECE]
        if parts:
            jobs[sector] = [O.OverlaySpec(
                overlay_id=f"shadow:{sector}", region_id=str(sector),
                shapes=tuple((tuple(map(tuple, g.exterior.coords[:-1])),
                              tuple(tuple(map(tuple, r.coords[:-1])) for r in g.interiors)) for g in parts))]
    cut = _cut(disk, jobs)
    cut["looked_at"] = len(grids)
    return cut


# --- 2. floors ------------------------------------------------------------------

#: a floor is cut where its light spans at least this many shades ...
FLOOR_SPREAD = 12
#: ... into bands this many shades apart: the campaign's own step between
#: two floors cut only for light is 10 to 14 (E1M4 10, E3M1 12, E3M2 14,
#: E3M5 14.5; `work/lightstage/budget.py`); at 6 the city cut three times as
#: often for steps nobody sees
FLOOR_BAND = 12
#: a band piece is kept only if its light differs from the piece around it by
#: at least this many shades, and it is at least `FLOOR_PIECE` in area: a cut
#: must show (409 of the fine cut's 3,291 seams ended within a shade)
FLOOR_SHOW = 6
#: traced on a grid this fine (plan units)
FLOOR_CELL = 128
#: the field smoothed by this many cells: a few dozen rays a point are noisy
FLOOR_SMOOTH = 1.0
#: a band's edge simplified to straight runs within this (plan units); the
#: owner of the first, cell-joined version: "unnecessary blocky where it can
#: be connected with 1 line"
FLOOR_SIMPLIFY = 256
#: a band piece smaller than this is not cut (plan units squared)
FLOOR_PIECE = 512 * 512
#: a floor smaller than this is one light, cut neither by bands nor by a
#: shadow: a shop unit of three square metres shows nothing by being cut, and
#: what stands on it would stand on a sliver of it
FLOOR_MIN_AREA = 2048 * 2048


def raised(disk, sector: int) -> bool:
    """A roofed floor that rises above a floor it opens onto and under none: furniture (a display, a shelf, a counter, a pew), never cut.

    Furniture is often a run of level pieces (a display of three sectors), so
    it is what has a floor below it beside it and none above.

    A light band across a shop's display left the goods on it standing on a
    sliver the shelf miner (`tools.mine_stands`) no longer reads as a shelf.
    """
    f = _f(disk.sectors[sector])
    z = int(f["floor_z"])
    others = [int(_f(disk.walls[w])["next_sector"])
              for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"]))]
    levels = [int(_f(disk.sectors[o])["floor_z"]) for o in others if o >= 0]
    return (not int(f["ceiling_stat"]) & 1 and any(level > z for level in levels)
            and not any(level < z for level in levels))


def band_floors(disk, model: Model, found: list | None = None, keep: frozenset = frozenset()) -> dict[str, Any]:
    """Cut every floor whose light spans many shades along the contours of that light."""
    import contourpy
    import numpy as np
    from scipy import ndimage
    from shapely import set_precision
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union

    from .sector_geom import outline_and_holes

    if found is None:
        found = model.trace(disk)
    W = model.weights
    rows = {(r["kind"], r["index"]): r for r in D.collapse(found, W)}
    cache = D.BounceCache(found, D.Weights(sun=W.sun, lamp=W.lamp))
    grids = []
    for s in found:
        if (s.kind != "floor" or s.index in keep
                or rows.get(("floor", s.index), {}).get("spread", 0) < FLOOR_SPREAD):
            continue
        f = _f(disk.sectors[s.index])
        if (not O.shade_only(disk.sectors[s.index]) or (int(f["floor_stat"]) | int(f["ceiling_stat"])) & 2
                or raised(disk, s.index)):
            continue                                  # the cutter would refuse it, or it is furniture
        o, h = outline_and_holes(disk, s.index)
        poly = Polygon(o, h)
        if poly.area < FLOOR_MIN_AREA:
            continue
        minx, miny, maxx, maxy = poly.bounds
        xs = np.arange(minx + FLOOR_CELL / 2, maxx, FLOOR_CELL)
        ys = np.arange(miny + FLOOR_CELL / 2, maxy, FLOOR_CELL)
        if len(xs) < 2 or len(ys) < 2:
            continue
        indoor = not int(f["ceiling_stat"]) & 1
        cells = [(j, i, D.Sample(float(x), float(y), int(f["floor_z"]) - 64, s.index, (0.0, 0.0, -1.0),
                                 indoor=indoor))
                 for j, y in enumerate(ys) for i, x in enumerate(xs) if poly.contains(Point(x, y))]
        grids.append((s.index, poly, xs, ys, cells))
    flat = [p for *_, cells in grids for _, _, p in cells]
    traced = iter(_parallel(disk, model.sun.vector(), model.lamps(disk), cache.points, _full_job, flat))
    jobs: dict[int, list] = {}
    for sector, poly, xs, ys, cells in grids:
        z = np.full((len(ys), len(xs)), np.nan)
        for j, i, p in cells:
            p.sky, p.sun, p.lamp, p.bounce = next(traced)
            z[j, i] = W.shade(W.total(p))
        traced_cells = [(p.x, p.y, float(z[j, i])) for j, i, p in cells]
        inside = ~np.isnan(z)
        if inside.sum() < 4:
            continue
        # outside the floor, the nearest value inside: the contours do not bend to the walls
        _, (jj, ii) = ndimage.distance_transform_edt(~inside, return_indices=True)
        z = ndimage.gaussian_filter(z[jj, ii], FLOOR_SMOOTH)
        lo, hi = int(np.floor(z.min() / FLOOR_BAND)), int(np.ceil(z.max() / FLOOR_BAND))
        thresholds = [t for t in (b * FLOOR_BAND + FLOOR_BAND / 2 for b in range(lo, hi))
                      if float(z.min()) < t < float(z.max())]
        gen = contourpy.contour_generator(xs, ys, z, fill_type=contourpy.FillType.OuterOffset)
        levels = []
        for t in sorted(thresholds, reverse=True):     # darkest threshold (largest region) first
            points, offsets = gen.filled(float(z.min()) - 1.0, t)
            polys = []
            for pts, offs in zip(points, offsets):
                rings = [pts[offs[k]:offs[k + 1]] for k in range(len(offs) - 1)]
                if rings:
                    g = Polygon(rings[0], rings[1:])
                    if g.is_valid and g.area > 0:
                        polys.append(g)
            if not polys:
                continue
            region = set_precision(unary_union(polys).simplify(FLOOR_SIMPLIFY, preserve_topology=True)
                                   .intersection(poly), 1.0)
            parts = [g for g in getattr(region, "geoms", [region])
                     if g.geom_type == "Polygon" and g.area > FLOOR_PIECE]
            if parts and sum(g.area for g in parts) < poly.area * 0.97:
                levels.append((t, parts))
        specs = [O.OverlaySpec(
            overlay_id=f"band{t:.0f}:{sector}", region_id=str(sector),
            shapes=tuple((tuple(map(tuple, g.exterior.coords[:-1])),
                          tuple(tuple(map(tuple, r.coords[:-1])) for r in g.interiors)) for g in parts))
            for t, parts in _showing(poly, levels, traced_cells)]
        if specs:
            jobs[sector] = specs
    cut = _cut(disk, jobs)
    cut["looked_at"] = len(grids)
    return cut


def _showing(poly, levels: list, cells: list) -> list:
    """The band levels whose piece would show: as large as `FLOOR_PIECE`, and `FLOOR_SHOW` shades from the piece around it.

    `levels` run from the largest region (the darkest threshold) inward; each
    level's piece is its region less the next one's. A level that would not
    show is dropped, its piece joining the one around it, until all show.
    """
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from shapely.prepared import prep

    levels = [(t, parts, unary_union(parts)) for t, parts in levels]
    points = [(Point(x, y), shade) for x, y, shade in cells]

    def piece(k):
        outer = poly if k < 0 else levels[k][2]
        return outer.difference(levels[k + 1][2]) if k + 1 < len(levels) else outer

    def mean(region):
        test = prep(region)
        values = [shade for point, shade in points if test.contains(point)]
        return sum(values) / len(values) if values else None

    changed = True
    while changed and levels:
        changed = False
        for k in range(len(levels)):
            inner, outer = piece(k), piece(k - 1)
            a, b = mean(inner), mean(outer)
            if (inner.area < FLOOR_PIECE or outer.area < FLOOR_PIECE or a is None or b is None
                    or abs(a - b) < FLOOR_SHOW):
                del levels[k]
                changed = True
                break
    return [(t, parts) for t, parts, _ in levels]


# --- 2b. sloped floors ------------------------------------------------------------

#: light is traced along a sloped floor this often (plan units)
SLOPE_STEP = 256
#: and no piece of it shorter than this along its slope's hinge
SLOPE_MIN_PIECE = 1024


def band_slopes(disk, model: Model, keep: frozenset = frozenset()) -> dict[str, Any]:
    """Cut every sloped floor whose light changes along it, straight ACROSS its slope.

    A sewer's walk has its ceiling sloped down to the wall (E3M3's vault), so
    it cannot be cut along a contour: a piece is the same plane only if its
    first wall lies on the slope's hinge line (`overlays.cut_sectors`,
    `slopes_across`). Its light is traced every `SLOPE_STEP` along the hinge,
    cut where it crosses a `FLOOR_BAND` band and kept only where each piece
    is `SLOPE_MIN_PIECE` long and `FLOOR_SHOW` shades from its neighbour.
    """
    import numpy as np
    from shapely import set_precision
    from shapely.geometry import Point, Polygon

    from .sector_geom import outline_and_holes

    found = model.trace(disk)
    W = model.weights
    rows = {(r["kind"], r["index"]): r for r in D.collapse(found, W)}
    cache = D.BounceCache(found, D.Weights(sun=W.sun, lamp=W.lamp))
    lines = []
    for s in found:
        if s.kind != "floor" or s.index in keep:
            continue
        f = _f(disk.sectors[s.index])
        if not (int(f["floor_stat"]) | int(f["ceiling_stat"])) & 2 or not O.shade_only(disk.sectors[s.index]):
            continue
        if rows.get(("floor", s.index), {}).get("spread", 0) < FLOOR_BAND / 2:
            continue
        a = _f(disk.walls[int(f["wall_ptr"])])
        b = _f(disk.walls[int(a["point2"])])
        hp = (int(a["x"]), int(a["y"]))
        ux, uy = int(b["x"]) - hp[0], int(b["y"]) - hp[1]
        ulen = (ux * ux + uy * uy) ** 0.5
        if ulen < 1:
            continue
        ux, uy = ux / ulen, uy / ulen
        poly = Polygon(*outline_and_holes(disk, s.index))
        ring = list(poly.exterior.coords)
        along = [(x - hp[0]) * ux + (y - hp[1]) * uy for x, y in ring]
        across = [-(x - hp[0]) * uy + (y - hp[1]) * ux for x, y in ring]
        t0, t1 = min(along), max(along)
        if t1 - t0 < 2 * SLOPE_MIN_PIECE:
            continue
        mid = (min(across) + max(across)) / 2
        indoor = not int(f["ceiling_stat"]) & 1
        points = []
        for t in np.arange(t0 + SLOPE_STEP / 2, t1, SLOPE_STEP):
            x, y = hp[0] + ux * t - uy * mid, hp[1] + uy * t + ux * mid
            if poly.contains(Point(x, y)):
                points.append((float(t), D.Sample(float(x), float(y), int(f["floor_z"]) - 64, s.index,
                                                   (0.0, 0.0, -1.0), indoor=indoor)))
        if len(points) >= 4:
            lines.append((s.index, poly, hp, (ux, uy), (min(across), max(across)), points))
    flat = [p for *_, pts in lines for _, p in pts]
    traced = iter(_parallel(disk, model.sun.vector(), model.lamps(disk), cache.points, _full_job, flat))
    jobs: dict[int, list] = {}
    for sector, poly, hp, (ux, uy), (a0, a1), points in lines:
        ts, shades = [], []
        for t, p in points:
            p.sky, p.sun, p.lamp, p.bounce = next(traced)
            ts.append(t)
            shades.append(W.shade(W.total(p)))
        shades = np.array(shades)
        if len(shades) >= 3:
            shades = np.convolve(np.pad(shades, 1, mode="edge"), np.ones(3) / 3, mode="valid")
        bands = np.round(shades / FLOOR_BAND).astype(int)
        cuts = [ts[0] - SLOPE_STEP / 2]
        for k in range(1, len(ts)):
            if bands[k] != bands[k - 1]:
                cuts.append((ts[k - 1] + ts[k]) / 2)
        cuts.append(ts[-1] + SLOPE_STEP / 2)
        # a piece must be long enough and show: merge until both hold
        segments = [[cuts[i], cuts[i + 1]] for i in range(len(cuts) - 1)]

        def mean(seg):
            values = [v for t, v in zip(ts, shades) if seg[0] <= t < seg[1]]
            return sum(values) / len(values) if values else 0.0

        merged = True
        while merged and len(segments) > 1:
            merged = False
            for i in range(len(segments) - 1):
                left, right = segments[i], segments[i + 1]
                if (left[1] - left[0] < SLOPE_MIN_PIECE or right[1] - right[0] < SLOPE_MIN_PIECE
                        or abs(mean(left) - mean(right)) < FLOOR_SHOW):
                    segments[i:i + 2] = [[left[0], right[1]]]
                    merged = True
                    break
        if len(segments) < 2:
            continue
        specs = []
        pad = 4096
        for k, (lo, hi) in enumerate(segments[1:], start=1):
            corners = [(lo, a0 - pad), (hi, a0 - pad), (hi, a1 + pad), (lo, a1 + pad)]
            strip = Polygon([(hp[0] + ux * t - uy * c, hp[1] + uy * t + ux * c) for t, c in corners])
            piece = set_precision(strip.intersection(poly), 1.0)
            parts = [g for g in getattr(piece, "geoms", [piece]) if g.geom_type == "Polygon" and g.area > 0]
            if parts:
                specs.append(O.OverlaySpec(
                    overlay_id=f"slope{k}:{sector}", region_id=str(sector),
                    shapes=tuple((tuple(map(tuple, g.exterior.coords[:-1])), ()) for g in parts)))
        if specs:
            jobs[sector] = specs
    cut = _cut(disk, jobs, slopes_across=True)
    cut["looked_at"] = len(lines)
    return cut


# --- 3. walls -------------------------------------------------------------------

#: a straight, axis-aligned wall at least this long is traced along its length
WALL_LONG = 1024
#: every this far (plan units)
WALL_STEP = 256
#: and split where its light crosses a band this many shades wide (on a
#: textured wall a step under ~10 does not show: `shade_table`)
WALL_BAND = 10
#: no piece shorter than this
WALL_MIN_PART = 384


def band_walls(disk, model: Model, keep: frozenset = frozenset()) -> dict[str, Any]:
    """Split long walls where their light changes along them."""
    import numpy as np

    found = model.trace(disk, wall_spacing=WALL_STEP, wall_max=256)
    W = model.weights
    points: dict[int, list] = {}
    looked = 0
    for s in found:
        if s.kind != "wall" or not s.samples or s.sector in keep:
            continue
        f = _f(disk.walls[s.index])
        if int(f["next_sector"]) in keep:
            continue
        n = _f(disk.walls[int(f["point2"])])
        ax, ay, bx, by = int(f["x"]), int(f["y"]), int(n["x"]), int(n["y"])
        length = math.hypot(bx - ax, by - ay)
        if length < WALL_LONG or (ax != bx and ay != by):
            continue
        looked += 1
        along: dict[float, list] = defaultdict(list)       # the light at each position, heights averaged
        for p in s.samples:
            t = ((p.x - ax) * (bx - ax) + (p.y - ay) * (by - ay)) / (length * length)
            along[round(t, 4)].append(W.shade(W.total(p)))
        ts = sorted(along)
        shades = np.array([np.mean(along[t]) for t in ts])
        if len(shades) >= 3:
            shades = np.convolve(np.pad(shades, 1, mode="edge"), np.ones(3) / 3, mode="valid")
        bands = np.round(shades / WALL_BAND).astype(int)
        cuts: list[float] = []
        for k in range(1, len(ts)):
            if bands[k] != bands[k - 1]:
                d = (ts[k - 1] + ts[k]) / 2 * length
                if d < WALL_MIN_PART or length - d < WALL_MIN_PART or (cuts and d - cuts[-1] < WALL_MIN_PART):
                    continue
                cuts.append(d)
        if cuts:
            points[s.index] = [((ax, int(round(ay + (by - ay) * d / length))) if ax == bx
                                else (int(round(ax + (bx - ax) * d / length)), ay)) for d in cuts]
    cut = _cut(disk, {}, points)
    cut["looked_at"] = looked
    return cut


# --- 4. the shades --------------------------------------------------------------


#: how bright glass that lets daylight in is drawn (Blood draws a sprite
#: indoors at its own shade plus the floor's): the owner, 2026-11-21, "That
#: stained glass itself should be lighter"
WINDOW_DRAWN = 0


def glow_windows(disk, keep: frozenset = frozenset()) -> int:
    """Set the shade of glass on a roofed wall so it draws at `WINDOW_DRAWN` over its floor."""
    count = 0
    for sprite in disk.sprites:
        f = _f(sprite)
        kind = K.KINDS.get(int(f["picnum"]))
        sector = int(f["sector"])
        if kind is None or kind.form != "window" or not 0 <= sector < len(disk.sectors) or sector in keep:
            continue
        s = _f(disk.sectors[sector])
        if int(s["ceiling_stat"]) & 1:
            continue
        f["shade"] = max(-128, min(127, WINDOW_DRAWN - int(s["floor_shade"])))
        count += 1
    return count


def shade(disk, model: Model, keep: frozenset = frozenset(), *,
          bias: dict[int, tuple[int, int, int]] | None = None) -> dict[str, Any]:
    """Trace the map and write every floor, ceiling and wall its light (but those of `keep`'s sectors); one sky shade; glass glows."""
    found = model.trace(disk)
    rows = [r for r in D.collapse(found, model.weights) if r["sector"] not in keep]
    if bias:
        surface_index = {"floor": 0, "ceiling": 1, "wall": 2}
        for row in rows:
            offset = bias.get(row["sector"])
            if offset:
                value = row["shade"] + offset[surface_index[row["kind"]]]
                row["shade"] = max(-128, min(127, value))
    D.apply(disk, rows)
    glowing = glow_windows(disk, keep)
    return {"surfaces": len(rows), "windows": glowing,
            "spread_12": sum(1 for r in rows if r["kind"] == "floor" and r["spread"] >= 12)}


@dataclass(frozen=True)
class LampGroup:
    """Lamps that go on, off or flicker as one, and how.

    The owner, 2026-11-24: "when you made light blinking it should also
    affect neighbouring sectors that are lit by that light". So a group names
    its lamps and the trace says what they light.

    mode        what the engine does with it (sectorfx.cpp:162-206: a wave is
                added while the sector's `busy` is up, scaled by it, or always)
      always    it flickers for ever; needs no wire
      on        lit while the sector is ON (saved ON), by `rx`
      out       lit until `rx` turns the sector ON (saved OFF)
    wave, frequency, phase   the shade wave; the same in every sector it
                lights, so they move together
    within      which sectors (by region) may be given it
    floor_pal   the palette a floor and its walls take while the light is on
                (XSECTOR `colored_lights`), where the light has a colour
    moved       the map with the lamps where they will be, made from the one it
                is given, for light that falls in another place once a lamp
                has travelled
    """

    name: str
    lamps: frozenset
    mode: str = "always"
    wave: int = 0
    frequency: int = 0
    phase: int = 0
    rx: int = 0
    within: Callable[[str], bool] = lambda region: True
    floor_pal: int | None = None
    moved: Any = None


#: a sector that a group changes by fewer shades than this does not show it
SWITCH_STEP = 4


def _lamp_steps(disk, model: Model, lamps: frozenset, sectors: list[int]) -> dict[int, dict[str, int]]:
    """By how many shades these lamps light each sector's floor, ceiling and walls."""
    sun = model.sun.vector()
    model.prepare(disk)

    def traced(hide: frozenset):
        saved = {i: int(_f(disk.sprites[i])["cstat"]) for i in hide}
        for i in hide:
            _f(disk.sprites[i])["cstat"] = saved[i] | 0x8000
        try:
            lit = model.lamps(disk)
        finally:
            for i, cstat in saved.items():
                _f(disk.sprites[i])["cstat"] = cstat
        found = D.surfaces(disk, sectors=sectors)
        samples = [p for surface in found for p in surface.samples]
        for p, got in zip(samples, _parallel(disk, sun, lit, None, _direct_job, samples)):
            p.sky, p.sun, p.lamp = got
        cache = D.BounceCache(found, D.Weights(sun=model.weights.sun, lamp=model.weights.lamp))
        for p, bounce in zip(samples, _parallel(disk, sun, lit, cache.points, _bounce_job, samples)):
            p.bounce = bounce
        return {(r["kind"], r["index"]): r for r in D.collapse(found, model.weights)}

    on, off = traced(frozenset()), traced(lamps)
    steps: dict[int, dict[str, Any]] = defaultdict(lambda: {"floor": 0, "ceiling": 0, "walls": []})
    for key, row in on.items():
        step = int(round(off[key]["shade"] - row["shade"])) if key in off else 0
        if row["kind"] == "wall":
            steps[row["sector"]]["walls"].append(step)
        else:
            steps[row["sector"]][row["kind"]] = step
    return {sector: {"floor": v["floor"], "ceiling": v["ceiling"],
                     "walls": max(v["walls"], default=0)} for sector, v in steps.items()}


def _xsector(disk, sector: int, used: set[int]) -> dict[str, int]:
    from .construction import _empty_fields
    from .format import XSECTOR_SCHEMA
    from .model import PackedExtra

    item = disk.sectors[sector]
    if item.extra is None:
        number = next(n for n in range(1, len(disk.sectors) + 2) if n not in used)
        used.add(number)
        fields = _empty_fields(XSECTOR_SCHEMA)
        fields.update(reference=sector, marker_0=-1, marker_1=-1)
        item.extra = PackedExtra("XSECTOR", fields)
        item.fields["extra"] = number
    return item.extra.fields


def switch_lamps(disk, model: Model, groups: list[LampGroup], region_of: dict[int, str],
                 keep: frozenset = frozenset()) -> dict[str, Any]:
    """Give every sector a switched lamp lights the same switch, by as much as that lamp lights it.

    The sector's shades are those with every lamp lit. The engine adds
    `amplitude` (times the wave, times `busy`), so a light that is lit while
    the wave is up is authored dark with a negative amplitude, and one that
    is put out is authored lit with a positive one. A sector has one wave and
    one receiver: it goes to the group that lights it most, and one already
    wired to something else keeps that and is named in the report.
    """
    claims: dict[int, list] = defaultdict(list)
    for group in groups:
        scene = disk if group.moved is None else group.moved(disk)
        spots = [_f(scene.sprites[i]) for i in group.lamps]
        near = []
        for i, sector in enumerate(scene.sectors):
            f = _f(sector)
            if i in keep or int(f["floor_z"]) == int(f["ceiling_z"]) or not group.within(region_of.get(i, "")):
                continue
            a = _f(scene.walls[int(f["wall_ptr"])])
            if any(abs(int(a["x"]) - int(p["x"])) < 2 * D.LAMP_REACH
                   and abs(int(a["y"]) - int(p["y"])) < 2 * D.LAMP_REACH for p in spots):
                near.append(i)
        for sector, step in _lamp_steps(scene, model, group.lamps, near).items():
            size = max(step.values())
            if size >= SWITCH_STEP:
                claims[sector].append((size, group, step))
    used = {int(_f(s)["extra"]) for s in disk.sectors if int(_f(s)["extra"]) > 0}
    report: dict[str, Any] = {"groups": {g.name: 0 for g in groups}, "held_by_another_wire": []}

    def brighten(sector: int, flags: dict[str, int], by: int) -> None:
        f = _f(disk.sectors[sector])
        for flag, key in (("floor", "floor_shade"), ("ceiling", "ceiling_shade")):
            if flags[flag]:
                f[key] = max(-32, min(63, int(f[key]) - by))
        if flags["walls"]:
            for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
                wall = _f(disk.walls[w])
                wall["shade"] = max(-32, min(63, int(wall["shade"]) - by))

    for sector, found in sorted(claims.items()):
        for size, group, step in sorted(found, key=lambda row: (-row[0], row[1].name)):
            held = getattr(disk.sectors[sector].extra, "fields", None) or {}
            # a receiver that also sends would send when the lamp goes: the light
            # of a room that credits a secret once gave the secret away
            if held.get("amplitude") or (group.rx and (held.get("rx_id", 0) not in (0, group.rx)
                                                       or held.get("tx_id"))):
                report["held_by_another_wire"].append((sector, group.name))
                continue
            x = _xsector(disk, sector, used)
            flags = {k: int(step[k] >= SWITCH_STEP) for k in ("floor", "ceiling", "walls")}
            amount = step["floor"] if flags["floor"] else size
            later = group.moved is not None                # lit when the lamp gets here: by ON it is away
            dark = group.mode != "out" and not later
            x.update(shade_wave=group.wave, shade_frequency=group.frequency, shade_phase=group.phase,
                     shade_floor=flags["floor"], shade_ceiling=flags["ceiling"], shade_walls=flags["walls"],
                     shade_always=int(group.mode == "always"), amplitude=-amount if dark else amount)
            if dark:
                brighten(sector, flags, -amount)
            elif later:
                brighten(sector, flags, amount)
            if group.rx:
                x["rx_id"] = group.rx
            if group.mode == "on":
                x.update(state=1, busy=65536)
            if group.floor_pal is not None and flags["floor"] and dark:
                x.update(colored_lights=1, floor_pal_2=group.floor_pal,
                         ceiling_pal_2=int(_f(disk.sectors[sector])["ceiling_pal"]))
            report["groups"][group.name] += 1
            break
    return report


def even_movers(disk, keep: frozenset = frozenset()) -> int:
    """Give the faces of each sector that moves whole (616, 617) one shade: the mean of theirs, by length.

    The trace sees the pose the map is saved in. A door leaf drawn open is
    lit on one side, and shut it would carry that light into the other
    leaf's shade; its faces turn through every direction, so none keeps one.
    """
    from .sector_geom import sector_walls, wall_length

    evened = 0
    for index, sector in enumerate(disk.sectors):
        if int(_f(sector)["type"]) not in (616, 617):
            continue
        faces = [int(_f(disk.walls[w])["next_wall"]) for w in sector_walls(disk, index)]
        faces = [w for w in faces if w >= 0]
        if not faces or any(int(_f(disk.walls[w])["next_sector"]) in keep for w in sector_walls(disk, index)):
            continue
        total = sum(wall_length(disk, w) for w in faces)
        mean = round(sum(int(_f(disk.walls[w])["shade"]) * wall_length(disk, w) for w in faces) / total)
        for w in faces:
            _f(disk.walls[w])["shade"] = mean
        evened += 1
    return evened


# --- cutting, whole or not at all ----------------------------------------------


def _unpaired(disk) -> set[int]:
    """Sectors with a two-sided wall whose twin does not point back along the same edge."""
    walls = disk.walls
    owner = {}
    for index, sector in enumerate(disk.sectors):
        f = _f(sector)
        for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            owner[w] = index
    bad: set[int] = set()
    for w, wall in enumerate(walls):
        f = _f(wall)
        twin = int(f["next_wall"])
        if twin < 0:
            continue
        ok = 0 <= twin < len(walls)
        if ok:
            t = _f(walls[twin])
            a2 = _f(walls[int(f["point2"])])
            b2 = _f(walls[int(t["point2"])])
            ok = (int(t["next_wall"]) == w and int(f["next_sector"]) == owner.get(twin)
                  and (int(f["x"]), int(f["y"])) == (int(b2["x"]), int(b2["y"]))
                  and (int(t["x"]), int(t["y"])) == (int(a2["x"]), int(a2["y"])))
        if not ok:
            bad.add(owner.get(w, -1))
            if int(f["next_sector"]) >= 0:
                bad.add(int(f["next_sector"]))
    bad.discard(-1)
    return bad


def _cut(disk, jobs: dict, wall_points: dict | None = None, slopes_across: bool = False) -> dict[str, Any]:
    """`overlays.cut_sectors` on a copy; where the cutter cannot pair an edge, those sectors stay whole.

    The cutter raises when a cut would leave a wall without its twin (a
    corner case at the edge of a piece). One such edge must not stop a
    build: the sectors and walls the error names are left out, reported in
    `refused`, and the rest is cut again. The map is only ever replaced by a
    cut that completed.
    """
    import copy
    import re

    jobs, wall_points = dict(jobs), dict(wall_points or {})
    owner = {}
    for index, sector in enumerate(disk.sectors):
        f = _f(sector)
        for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            owner[w] = index
    left_whole: dict[int, str] = {}
    for _ in range(len(jobs) + len(wall_points) + 1):
        trial = copy.deepcopy(disk)
        try:
            report = O.cut_sectors(trial, jobs, wall_points=wall_points or None,
                                   slopes_across=slopes_across)
        except O.OverlayError as error:
            walls = [int(n) for n in re.findall(r"wall (\d+)", str(error))]
            sectors = {int(n) for n in re.findall(r"sector (\d+)", str(error))}
            sectors |= {owner[w] for w in walls if w in owner}
            twins = {int(_f(disk.walls[w])["next_wall"]) for w in walls if w < len(disk.walls)}
            dropped = [s for s in sectors if s in jobs] + [w for w in set(walls) | twins if w in wall_points]
            if not dropped:
                raise
            for s in sectors:
                if jobs.pop(s, None) is not None:
                    left_whole[s] = str(error)
            for w in set(walls) | twins:
                if wall_points.pop(w, None) is not None:
                    left_whole[-1 - w] = str(error)
            continue
        bad = _unpaired(trial)
        if bad:
            parent = {int(k): int(v) for k, v in report.get("parent", {}).items()}
            sectors = {parent.get(s, s) for s in bad}
            dropped = [s for s in sectors if s in jobs]
            walls = [w for w in wall_points if owner.get(w) in sectors
                     or int(_f(disk.walls[w])["next_sector"]) in sectors]
            if not dropped and not walls:
                raise O.OverlayError(f"the cut left walls without their twins in sectors {sorted(sectors)}")
            for s in dropped:
                jobs.pop(s)
                left_whole[s] = "a wall of the cut had no twin"
            for w in walls:
                wall_points.pop(w)
                left_whole[-1 - w] = "a wall of the cut had no twin"
            continue
        vars(disk).update(vars(trial))
        report["left_whole"] = {str(k): v for k, v in sorted(left_whole.items())}
        return report
    raise O.OverlayError("the cut could not be completed")


# --- the stage ------------------------------------------------------------------


def _chain(parent: dict, cut: dict, scale: dict | None = None) -> None:
    for piece, source in cut.get("parent", {}).items():
        source = int(source)
        parent[int(piece)] = parent.get(source, source)
        if scale is not None and source in scale:
            scale[int(piece)] = scale[source]


def run(disk, region_of: dict[int, str], rule_for: Callable[[str], Rule], model: Model | None = None,
        *, keep: Callable[[str], bool] = lambda region: False,
        lamp_scale: Callable[[str], float] = lambda region: 1.0,
        room_key: Callable[[str], str] | None = None, art=None,
        groups: list[LampGroup] = ()) -> dict[str, Any]:
    """Light a finished map: the sun's shadows, its lights, its floor bands, its wall bands, then every shade.

    A sector whose region `keep` names keeps the light its own module gave
    it: it is not cut, not lit in rows, and its shades are not written. It
    still stands in the scene, and its lamps still light the rest.
    A sector a moving sector sweeps through (`swept_state.hosts`) is lit but
    never cut: a cut across the sweep would be a wall in the mover's way.
    `lamp_scale` says how strong a place's lamps are (1 is the model's).
    `room_key` names the room a region belongs to, where several regions are
    one room to be lit (a corridor's walks and its channel).
    A rule's shade bias sets the base darkness while keeping the traced pools.
    """
    model = model or Model()
    kept = frozenset(i for i, region in region_of.items() if keep(region))
    scale = model.lamp_scale_by_sector = {i: lamp_scale(r) for i, r in region_of.items() if lamp_scale(r) != 1.0}
    report: dict[str, Any] = {"sectors_before": len(disk.sectors), "walls_before": len(disk.walls),
                              "sprites_before": len(disk.sprites)}
    parent: dict[int, int] = {}
    from .swept_state import hosts
    whole = kept | frozenset(hosts(disk))
    report["mover_hosts"] = sorted(whole - kept)
    whole |= frozenset(i for i, region in region_of.items() if not rule_for(region).cut)
    shadows = cut_shadows(disk, model, whole)
    _chain(parent, shadows, scale)
    report["shadow_cut"] = {k: v for k, v in shadows.items() if k != "parent"}
    # the pieces of a room are still that room
    region_of = dict(region_of)
    for piece, source in parent.items():
        region_of[piece] = region_of.get(source, "")
    rooms = rooms_by_region(disk, region_of, kept, room_key)
    laid = lay_lights(disk, rooms, rule_for, art, whole)
    _chain(parent, laid["cut"], scale)
    report["rooms"] = laid["rooms"]
    report["panel_cut"] = {k: v for k, v in laid["cut"].items() if k != "parent"}
    floors = band_floors(disk, model, keep=whole)
    _chain(parent, floors, scale)
    report["floor_cut"] = {k: v for k, v in floors.items() if k != "parent"}
    slopes = band_slopes(disk, model, whole)
    _chain(parent, slopes, scale)
    report["slope_cut"] = {k: v for k, v in slopes.items() if k != "parent"}
    walls = band_walls(disk, model, whole)
    report["wall_cut"] = {k: v for k, v in walls.items() if k != "parent"}
    bias = {}
    for i, region in region_of.items():
        offset = rule_for(region).shade_bias
        if any(offset):
            bias[i] = offset
    for piece, source in parent.items():
        if source in bias:
            bias[piece] = bias[source]
    report["shades"] = shade(disk, model, kept, bias=bias)
    report["shades"]["movers_evened"] = even_movers(disk, kept)
    if groups:
        for piece, source in parent.items():
            region_of.setdefault(piece, region_of.get(source, ""))
        report["switched"] = switch_lamps(disk, model, list(groups), region_of, kept)
    report["kept"] = len(kept)
    report["parent"] = dict(sorted(parent.items()))
    report.update(sectors=len(disk.sectors), walls=len(disk.walls), sprites=len(disk.sprites))
    return report
