"""A map lit as the 3D scene it is: sky, sun and lamps traced with the engine's hitscan, giving every floor and wall a mean shade and a spread.

The owner, 2026-11-20: "We should be able to map the light like it is 3D
thing with real shadows and when some big area will have too big contrast -
conflicting light levels it can be decided to be divided". Build keeps one
shade per floor and per wall; light does not. So the light is computed at
sample points over every surface, as light, and only then collapsed to
Build's rule: a surface's MEAN is its shade, and its SPREAD (p90 - p10 of
its samples, in shades) is how much the collapse threw away -- the measure
of where a split would show something.

The scene. Every sector is a prism: a floor plane, a ceiling plane, and
vertical walls; an opening is open only between its two sectors' heights.
`lightbomb.hitscan` walks it exactly so (through an opening at the height it
is open, stopped by the first solid surface, out through a parallax sky),
so a ray toward the sun from a point either reaches the sky or it does not.
Masked walls (glass, bars) are open to it; sprites do not occlude.

The light at a sample point, facing `n`:

* SKY -- the share of the sky the point sees, cosine-weighted over a fixed
  set of `SKY_RAYS` directions on the upper hemisphere: an open floor sees
  1, an open wall 0.5 (half the sky), the inside of a doorway a little, the
  back of a room none.
* SUN -- `max(0, n . s)` where a ray toward the sun reaches the sky.
* LAMPS -- every light sprite within `LAMP_REACH`, by inverse square past a
  core radius, times `max(0, n . l)`, where the lamp is in sight.

`L = SKY + sun_weight * SUN + lamp_weight * LAMPS`, and the shade is linear in
it, as the game's own table is linear in brightness (`shade_table`):
`shade = dark - (dark - bright) * L / reference`, clamped to 0..63.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any

from .lightbomb import Z_SCALE, ScanIndex, hitscan
from .model import record_fields as _f

#: a standing player, in z
BODY = 16960
#: sample spacing on a floor (plan units), and at most this many per sector
FLOOR_SPACING = 512
FLOOR_MAX = 36
#: sample spacing along a wall, at most this many along it
WALL_SPACING = 512
WALL_MAX = 8
#: sky directions over the upper hemisphere
SKY_RAYS = 24
#: lamps further than this (plan units) light nothing
LAMP_REACH = 8192
#: inside this radius a lamp's light stops growing (plan units). 1024 was
#: LightBomb's fit to the campaign's walls beside burning sprites; a light on
#: a ceiling is a body and a half over the floor, and at 1024 it gave that
#: floor about 7 shades -- under a band step, and the owner saw lights that
#: "do not behave like light sources". The campaign's panels make the floor
#: under them 12 to 20 lighter (`tools/light_sources.py`): 1600, with the lamp
#: weight 1.3, gives about 16.
LAMP_CORE = 1600
#: a ray that stops this close to a lamp (plan units) has reached it: the
#: wall or ceiling it hangs from
LAMP_SURFACE = 256
#: the sprites that are lights: these tiles, or anything drawn this bright
LIGHT_TILES = frozenset({506, 641, 1701})
LIGHT_SHADE = -64


@dataclass
class Sun:
    azimuth: float = 264.0          # map degrees the light comes FROM (0 east, 90 south)
    elevation: float = 45.0

    def vector(self) -> tuple[float, float, float]:
        """Unit vector toward the sun, in plan units (z up is negative in Build)."""
        a, e = math.radians(self.azimuth), math.radians(self.elevation)
        return (math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), -math.sin(e))


@dataclass
class Weights:
    sun: float = 1.0
    lamp: float = 1.0
    dark: float = 44.0              # the shade of a surface no light reaches
    bright: float = 4.0             # the shade at `reference` light
    reference: float = 2.0          # open ground in full sun: sky 1 + sun ~0.7
    bounce: float = 0.0             # how much one bounce adds (a reflectance)
    #: the base light of a roofed space before any lamp. Blood shades a room
    #: from a stated level and puts lamp pools on top (E3M1's unlit rooms sit at
    #: 34); a lamp at the campaign's falloff lights a pool ~1,500 units across,
    #: so physics alone leaves every room at `dark`.
    indoor_ambient: float = 0.0
    #: a place's own base light, by sector, where it differs: a sewer is near
    #: darkness between its lights (the owner: "sewers have potential to have
    #: more light vs shadow parts")
    ambient_by_sector: dict = field(default_factory=dict)

    def total(self, p: "Sample") -> float:
        ambient = self.ambient_by_sector.get(p.sector, self.indoor_ambient) if p.indoor else 0.0
        return p.sky + self.sun * p.sun + self.lamp * p.lamp + self.bounce * p.bounce + ambient

    def shade(self, light: float) -> float:
        value = self.dark - (self.dark - self.bright) * light / self.reference
        return max(0.0, min(63.0, value))


@dataclass
class Sample:
    x: float
    y: float
    z: float
    sector: int
    normal: tuple[float, float, float]
    sky: float = 0.0
    sun: float = 0.0
    lamp: float = 0.0
    bounce: float = 0.0
    indoor: bool = False


@dataclass
class Surface:
    kind: str                        # "floor", "ceiling" or "wall"
    index: int                       # sector or wall id
    sector: int
    samples: list = field(default_factory=list)


def _hemisphere(n: int) -> list[tuple[float, float, float]]:
    """`n` directions spread evenly over the upper hemisphere (unit vectors, up = -z)."""
    out = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        up = (i + 0.5) / n                         # cos of the angle from the zenith
        r = math.sqrt(1 - up * up)
        a = golden * i
        out.append((r * math.cos(a), r * math.sin(a), -up))
    return out


def _sky_hit(disk, hit) -> bool:
    return hit.kind == "ceiling" and bool(int(_f(disk.sectors[hit.sector])["ceiling_stat"]) & 1)


def _trace(disk, scan, sample: Sample, d: tuple[float, float, float]):
    """Cast from a sample along a plan-unit direction (z scaled for hitscan)."""
    return hitscan(disk, sample.x, sample.y, sample.z, sample.sector,
                   d[0], d[1], d[2] * Z_SCALE, index=scan)


def lights_of(disk) -> list[tuple[float, float, float, int, float]]:
    """Every light in the map, at its light point, with its strength (`light_kinds`).

    The first version took any sprite drawn at shade -64 or brighter: it
    counted the signs' fullbright letters as lamps, missed the city's street
    lamps (their light is in the head of the post, not at its foot), and knew
    nothing of panels.
    """
    from .light_kinds import lights

    return lights(disk)


def surfaces(disk, *, sectors=None) -> list[Surface]:
    """Sample points over every floor and every visible wall face."""
    from shapely.geometry import Point, Polygon

    from .sector_geom import outline_and_holes

    wanted = None if sectors is None else set(sectors)
    out: list[Surface] = []
    owners = {}
    polys = {}
    for index, sector in enumerate(disk.sectors):
        f = _f(sector)
        for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            owners[w] = index
        try:
            o, h = outline_and_holes(disk, index)
            polys[index] = Polygon(o, h)
        except Exception:
            continue
    for index, poly in polys.items():
        if wanted is not None and index not in wanted:
            continue
        f = _f(disk.sectors[index])
        if int(f["floor_z"]) - int(f["ceiling_z"]) < 256 or not poly.is_valid or poly.area < 4096:
            continue
        surface = Surface("floor", index, index)
        minx, miny, maxx, maxy = poly.bounds
        step = max(FLOOR_SPACING, math.sqrt(poly.area / FLOOR_MAX))
        inner = poly.buffer(-32)
        y = miny + step / 2
        while y < maxy:
            x = minx + step / 2
            while x < maxx:
                if inner.contains(Point(x, y)):
                    surface.samples.append(Sample(x, y, int(f["floor_z"]) - 64, index, (0.0, 0.0, -1.0)))
                x += step
            y += step
        if not surface.samples:
            p = poly.representative_point()
            surface.samples.append(Sample(p.x, p.y, int(f["floor_z"]) - 64, index, (0.0, 0.0, -1.0)))
        out.append(surface)
        for q in surface.samples:
            q.indoor = not int(f["ceiling_stat"]) & 1
        # a roofed ceiling is a surface too: it faces down, and its light is
        # what the lamps and the floor below send up to it
        if not int(f["ceiling_stat"]) & 1:
            ceiling = Surface("ceiling", index, index)
            ceiling.samples = [Sample(q.x, q.y, int(f["ceiling_z"]) + 64, index, (0.0, 0.0, 1.0), indoor=True)
                               for q in surface.samples]
            out.append(ceiling)
    for w, wall in enumerate(disk.walls):
        sector = owners.get(w)
        if sector is None or sector not in polys or (wanted is not None and sector not in wanted):
            continue
        f = _f(wall)
        n = _f(disk.walls[int(f["point2"])])
        ax, ay, bx, by = int(f["x"]), int(f["y"]), int(n["x"]), int(n["y"])
        length = math.hypot(bx - ax, by - ay)
        if length < 64:
            continue
        mine = _f(disk.sectors[sector])
        floor, ceil = int(mine["floor_z"]), int(mine["ceiling_z"])
        bands = []
        other = int(f["next_sector"])
        if other < 0:
            top = ceil if not int(mine["ceiling_stat"]) & 1 else max(ceil, floor - 4 * BODY)
            bands.append((top, floor))
        else:
            theirs = _f(disk.sectors[other])
            if int(theirs["floor_z"]) < floor:
                bands.append((max(int(theirs["floor_z"]), ceil), floor))
            if (int(theirs["ceiling_z"]) > ceil
                    and not (int(theirs["ceiling_stat"]) & 1 and int(mine["ceiling_stat"]) & 1)):
                bands.append((ceil if not int(mine["ceiling_stat"]) & 1
                              else max(ceil, int(theirs["ceiling_z"]) - 4 * BODY),
                              min(int(theirs["ceiling_z"]), floor)))
        bands = [(t, b) for t, b in bands if b - t > 512]
        if not bands:
            continue
        nx, ny = -(by - ay) / length, (bx - ax) / length
        mx, my = (ax + bx) / 2, (ay + by) / 2
        if not polys[sector].covers(Point(mx + nx * 16, my + ny * 16)):
            nx, ny = -nx, -ny
        surface = Surface("wall", w, sector)
        along = max(1, min(WALL_MAX, int(length // WALL_SPACING)))
        for k in range(along):
            t = (k + 0.5) / along
            px, py = ax + (bx - ax) * t + nx * 16, ay + (by - ay) * t + ny * 16
            for top, bottom in bands:
                for frac in (0.25, 0.75) if bottom - top > 2 * BODY else (0.5,):
                    z = bottom - (bottom - top) * frac
                    surface.samples.append(Sample(px, py, z, sector, (nx, ny, 0.0),
                                                  indoor=not int(mine["ceiling_stat"]) & 1))
        out.append(surface)
    return out


def light_point(disk, scan, p: Sample, dome, sun_vector, lamps) -> int:
    """Trace sky, sun and lamps for one point; fills it in. Returns rays cast."""
    rays = 0
    nx, ny, nz = p.normal
    # sky: cosine-weighted share of the dome that is open sky
    total = seen = 0.0
    for d in dome:
        c = nx * d[0] + ny * d[1] + nz * d[2]
        if c <= 0:
            continue
        total += c
        rays += 1
        if _sky_hit(disk, _trace(disk, scan, p, d)):
            seen += c
    # an unobstructed floor sees 1; a wall sees half the dome
    p.sky = seen / total * (1.0 if nz < -0.5 else 0.5) if total else 0.0
    s = sun_vector
    c = nx * s[0] + ny * s[1] + nz * s[2]
    p.sun = 0.0
    if c > 0:
        rays += 1
        if _sky_hit(disk, _trace(disk, scan, p, s)):
            p.sun = c
    p.lamp = 0.0
    for lamp in lamps:
        lx, ly, lz = lamp[0], lamp[1], lamp[2]
        strength = lamp[4] if len(lamp) > 4 else 1.0
        dx, dy, dz = lx - p.x, ly - p.y, (lz - p.z) / Z_SCALE
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist > LAMP_REACH or dist < 1:
            continue
        c = (nx * dx + ny * dy + nz * dz) / dist
        if c <= 0:
            continue
        rays += 1
        hit = hitscan(disk, p.x, p.y, p.z, p.sector, dx / dist, dy / dist,
                      dz / dist * Z_SCALE, index=scan)
        if hit.kind != "void":
            # a lamp hangs on a wall or under a ceiling: the ray meets that
            # surface a hand's width short of it, and that is reaching it
            gap = math.sqrt((hit.x - lx) ** 2 + (hit.y - ly) ** 2 + ((hit.z - lz) / Z_SCALE) ** 2)
            if gap > LAMP_SURFACE:
                continue
        p.lamp += strength * c / (1.0 + (dist / LAMP_CORE) ** 2)
    return rays


def light(disk, found: list[Surface], *, sun: Sun = Sun(), lamps=None,
          sky_rays: int = SKY_RAYS) -> dict[str, Any]:
    """Trace sky, sun and lamps for every sample. Fills the samples in place."""
    scan = ScanIndex(disk)
    dome = _hemisphere(sky_rays)
    s = sun.vector()
    lamps = lights_of(disk) if lamps is None else lamps
    rays = 0
    for surface in found:
        for p in surface.samples:
            rays += light_point(disk, scan, p, dome, s, lamps)
    return {"surfaces": len(found), "samples": sum(len(s.samples) for s in found),
            "rays": rays, "lamps": len(lamps)}


def collapse(found: list[Surface], weights: Weights = Weights()) -> list[dict[str, Any]]:
    """Each surface's shade (the mean of its samples) and its spread (p90 - p10)."""
    out = []
    for surface in found:
        shades = sorted(weights.shade(weights.total(p)) for p in surface.samples)
        if not shades:
            continue
        lo = shades[int(0.1 * (len(shades) - 1))]
        hi = shades[int(0.9 * (len(shades) - 1))]
        out.append({"kind": surface.kind, "index": surface.index, "sector": surface.sector,
                    "shade": round(statistics.fmean(shades)), "spread": round(hi - lo, 1),
                    "samples": len(shades)})
    return out


#: The one shade of the open sky. The first version set each open sector's
#: sky 16 brighter than its floor (the campaign's median habit), so that the
#: sprites standing there would follow the ground -- and the owner saw the
#: sky drawn in bands, one per sector. Blood has the better tool: floorstat
#: bit 0x8000 makes a sprite under an open sky take the FLOOR's shade
#: (NBlood `view.cpp:2875`, the only place the bit is read), so the sky can
#: be one shade everywhere and the sprites still follow the ground.
SKY_SHADE = 0
SPRITES_TAKE_FLOOR = 0x8000


def apply(disk, rows: list[dict[str, Any]], *, sky_shade: int | None = SKY_SHADE) -> int:
    """Write each surface's computed shade into the map.

    Every open sector then takes the one sky shade and the floor flag, so the
    sky is drawn evenly and its sprites take the light of the ground they
    stand on; None leaves the skies as they are.
    """
    for row in rows:
        if row["kind"] == "floor":
            _f(disk.sectors[row["index"]])["floor_shade"] = int(row["shade"])
        elif row["kind"] == "ceiling":
            _f(disk.sectors[row["index"]])["ceiling_shade"] = int(row["shade"])
        else:
            _f(disk.walls[row["index"]])["shade"] = int(row["shade"])
    if sky_shade is not None:
        unify_sky(disk, sky_shade)
    return len(rows)


def unify_sky(disk, shade: int = SKY_SHADE) -> int:
    """One sky shade for every open sector; its sprites take the floor's."""
    count = 0
    for sector in disk.sectors:
        f = _f(sector)
        if int(f["ceiling_stat"]) & 1:
            f["ceiling_shade"] = int(shade)
            f["floor_stat"] = int(f["floor_stat"]) | SPRITES_TAKE_FLOOR
            count += 1
    return count


def normalise(disk, rows: list[dict[str, Any]], *, strength: float = 0.5,
              reference: float | None = None) -> dict[str, Any]:
    """Correct each surface's shade part of the way for how light its tile is.

    The engine draws texel x shade-brightness, so under one light a dark
    brick wall and a pale stone wall differ by their art, and Blood's tiles
    differ a lot (the city's facades average 39 to 67 of 255 at shade 0,
    `shade_table`). The owner: "we might need to normalise light based on
    the texture lightness". A surface's drawn brightness is moved `strength`
    of the way (on a log scale) toward what a tile of `reference` lightness
    would show at its shade. Shade 0 is the brightest anything is drawn, so
    a dark tile can be lifted only so far; a light one is calmed.
    """
    from . import shade_table as T

    lightness: dict[int, float] = {}

    def tile_of(row):
        if row["kind"] == "floor":
            return int(_f(disk.sectors[row["index"]])["floor_picnum"])
        return int(_f(disk.walls[row["index"]])["picnum"])

    for row in rows:
        tile = tile_of(row)
        if tile not in lightness:
            lightness[tile] = T.brightness(tile, 0)
    known = sorted(v for v in lightness.values() if v > 0)
    ref = reference if reference is not None else known[len(known) // 2]
    moved = 0
    for row in rows:
        a = lightness.get(tile_of(row)) or ref
        factor = (ref / a) ** strength
        target = 64.0 - 64.0 * factor * (1.0 - row["shade"] / 64.0)
        new = int(round(max(0.0, min(63.0, target))))
        if new != row["shade"]:
            moved += 1
        row["shade"] = new
    return {"reference_lightness": round(ref, 1), "strength": strength, "moved": moved,
            "tiles": len(lightness)}


# --- one bounce ---------------------------------------------------------------
#
# Sky and sun alone leave everything the sun misses one flat dark tone, and a
# room behind an open door as dark as its back wall: in the world most of the
# light on a shaded facade or inside a room has bounced off something lit.
# One bounce, gathered: each surface is first lit directly (its samples are the
# cache); a point then looks over the half-sphere it faces, and every ray that
# lands on a floor or a wall brings back that surface's direct light at the
# nearest sample, cosine-weighted, times a reflectance.

#: directions over the whole sphere for gathering bounce light
GATHER_RAYS = 24
#: how much of the light on a surface it throws back (Blood's tiles average
#: about a quarter of full brightness; the look is a judgement, not physics)
REFLECTANCE = 0.5


def _sphere(n: int) -> list[tuple[float, float, float]]:
    out = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        out.append((r * math.cos(golden * i), r * math.sin(golden * i), z))
    return out


class BounceCache:
    """Each surface's directly lit samples, looked up by the surface a ray lands on."""

    def __init__(self, found: list[Surface], weights: Weights):
        self.points: dict[tuple, list] = {}
        for surface in found:
            key = (surface.kind, surface.index)
            self.points[key] = [(p.x, p.y, p.z, p.sky + weights.sun * p.sun + weights.lamp * p.lamp)
                                for p in surface.samples]

    def direct(self, hit) -> float:
        key = (("floor", hit.sector) if hit.kind == "floor" else ("wall", hit.wall) if hit.kind == "wall"
               else ("ceiling", hit.sector) if hit.kind == "ceiling" else None)
        points = self.points.get(key) if key else None
        if not points:
            return 0.0
        best = min(points, key=lambda q: (q[0] - hit.x) ** 2 + (q[1] - hit.y) ** 2
                   + ((q[2] - hit.z) / Z_SCALE) ** 2)
        return best[3]


def bounce_point(disk, scan, p: Sample, sphere, cache: BounceCache) -> float:
    """The light reaching a point after one bounce off lit floors and walls."""
    nx, ny, nz = p.normal
    total = got = 0.0
    for d in sphere:
        c = nx * d[0] + ny * d[1] + nz * d[2]
        if c <= 0:
            continue
        total += c
        hit = _trace(disk, scan, p, d)
        if hit.kind in ("floor", "wall", "ceiling"):
            got += c * cache.direct(hit)
    return got / total if total else 0.0


def light_with_bounce(disk, found: list[Surface], *, sun: Sun = Sun(), weights: Weights,
                      lamps=None, gather: int = GATHER_RAYS) -> dict[str, Any]:
    """Direct light for every sample, then one bounce gathered from it."""
    report = light(disk, found, sun=sun, lamps=lamps)
    cache = BounceCache(found, Weights(sun=weights.sun, lamp=weights.lamp))
    scan = ScanIndex(disk)
    sphere = _sphere(gather)
    for surface in found:
        for p in surface.samples:
            p.bounce = bounce_point(disk, scan, p, sphere, cache)
    report["gather_rays"] = gather
    return report
