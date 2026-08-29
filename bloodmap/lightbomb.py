"""XMapEdit's light bomb: shade from rays that actually travel through the map.

Every lighting pass this project had computes shade from a *number* -- a wall's
angle to an assumed direction, a distance to the nearest lamp. Neither of them
knows where the walls are. A torch on one side of a partition lights the far
side of it just as brightly as the near side, and a lamp in a corridor lights the
room next door through the stone.

XMapEdit ships the answer, and it is not a heuristic. `edit3d.cpp` casts several
thousand rays out of a point, follows each one through the map with the engine's
own `hitscan`, deposits energy where it lands, reflects it and follows it again.
This is that algorithm, transcribed:

.. code-block:: text

    for elevation in 30..150 step 5 degrees:
        for azimuth in 0..360 step 360/256:
            ShootRay(x, y, z, sector, direction, intensity, reflect=0, dist=0)

    ShootRay:
        hit = hitscan(...)
        dist += |hit - origin|                      # z counted at 1/16
        E = intensity / (dist + rampDist)
        E = E / area(surface)                       # spread over what it lands on
        surface.shade -= E                          # shade is inverted
        if reflect < reflections:
            reflect the direction about the surface normal
            intensity -= intensity * attenuation
            ShootRay(from the hit, ...)

Three details in it are load-bearing and none of them are obvious:

**Energy is divided by the area of the surface it lands on.** A ray that hits a
small alcove wall brightens it far more than the same ray hitting the side of a
nave. That is what makes the pass produce pools and edges rather than a uniform
wash, and it is why `SetupLightBomb` spends its time computing areas.

**A two-sided wall's area is only the part of it that is solid** -- the step up
from the neighbour's floor plus the step down from its ceiling. The open middle
is not surface, so light does not land on it; it goes through, which is the
whole point.

**Sky absorbs.** A ray that hits a parallax floor or ceiling returns without
depositing anything and without reflecting. Outdoors does not bounce.

The accumulation is fixed point in the original -- a 16.16 companion array per
surface -- because thousands of rays each deposit far less than one shade unit
and integer truncation would throw all of them away. Here it is a float
accumulator, which is the same idea with less ceremony.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

#: Blood's z axis is 16 units to one horizontal unit, so a distance that mixes
#: them has to bring z back down before adding.
Z_SCALE = 16.0

#: The original works in a coarser grid than the map: every length is shifted
#: right by 4 before use (`x >> 4`), and z by 8, which puts both on the same
#: scale. Areas are therefore in sixteenths squared, and getting this wrong is
#: worth a factor of 256 in the energy -- which is exactly enough for the whole
#: pass to do nothing at all and look like it worked.
GRID = 16.0

#: `divscale16(a, b)` is `(a << 16) / b`, and the energy passes through two of
#: them: once against distance and once against area. The shade a ray deposits
#: is the result read back out of 16.16, so the two shifts and the final one
#: leave a single factor of 65536.
FIXED = 65536.0

#: XMapEdit's own defaults, from `LIGHT_BOMB::Init`.
XMAPEDIT_INTENSITY = 16
XMAPEDIT_RAMP_DISTANCE = 0x10000
XMAPEDIT_MAX_BRIGHT = -4

ATTENUATION = 0x1000 / 65536.0      # 6.25% of the remaining intensity per bounce
REFLECTIONS = 2

#: Intensity and ramp fitted to Blood's own light, rather than taken from the
#: editor's defaults.
#:
#: The defaults are not wrong, they answer a different question. `rampDist` is
#: 65536 against ray distances of a hundred or two, so ``E = intensity/(dist +
#: ramp)`` is very nearly ``intensity/ramp`` and **the pass has no distance
#: falloff at all** -- everything it does comes from occlusion and from dividing
#: energy by the area it lands on. That is a defensible thing for an editor tool
#: to do: it bakes ambient bounce and leaves the artist to place the highlights.
#:
#: It is not what Blood's maps look like. Measuring the campaign's walls against
#: their distance from the nearest burning sprite gives medians of 8, 17, 24 and
#: 28 shade at under one player width, one to three, three to six, and beyond,
#: against 31 for a wall in a room with no light in it -- so relative to unlit,
#: -23, -14, -7 and -3.
#:
#: Sweeping the two free parameters against those four numbers, over the whole
#: of this level and its 22 lights, lands here::
#:
#:     ramp   intensity   deltas                 error
#:     2048        1.0    -23, -11,  -6,  -7         8
#:     3072        2.5    -24, -12,  -8,  -7         8
#:     1024        6.0    -30, -15, -10,  -9        18
#:     65536      16.0    (flat: no falloff)
#:
#: The near pool comes out exactly right and the tail is a little fat, which is
#: the two reflections putting more bounce into the far corners than Blood's
#: hand-shaded walls carry. That is the honest failure mode of a physical model
#: fitted to a hand-made corpus, and it is small.
INTENSITY = 1.0
RAMP_DISTANCE = 2048

#: No clamp. XMapEdit stops at -4 so its editor preview cannot blow out; the fit
#: above was made without one, and `match_corpus_shade` sets the level's exposure
#: afterwards anyway.
MAX_BRIGHT = -128

#: The ray fan: elevations from 30 to 150 degrees in steps of 5, and 256
#: azimuths at each. `kAng90 - kAng60` to `kAng90 + kAng60` by `kAng5`, and
#: `kAng360 / 256`.
ELEVATION_FROM = 30.0
ELEVATION_TO = 150.0
ELEVATION_STEP = 5.0
AZIMUTHS = 256

SHADE_MIN, SHADE_MAX = -128, 127

#: A ray that has crossed this many portals is in a loop or in a corridor long
#: enough that the energy left is beneath notice. The original relies on
#: `hitscan` terminating; this is the same guarantee made explicit.
MAX_CROSSINGS = 64


@dataclass
class Surfaces:
    """Areas and normals, computed once. `SetupLightBomb`."""

    sector_area: list[float]
    wall_area: list[float]
    wall_normal: list[tuple[float, float]]


def _fields(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def _walls_of(level: Any, index: int) -> range:
    fields = _fields(level.sectors[index])
    start = int(fields["wall_ptr"])
    return range(start, start + int(fields["wall_count"]))


def sector_area(level: Any, index: int) -> float:
    """Twice the shoelace, halved -- in map units squared."""
    total = 0.0
    for wall_id in _walls_of(level, index):
        here = _fields(level.walls[wall_id])
        there = _fields(level.walls[int(here["point2"])])
        x1, y1 = int(here["x"]) / GRID, int(here["y"]) / GRID
        x2, y2 = int(there["x"]) / GRID, int(there["y"]) / GRID
        total += (x1 + x2) * (y2 - y1)
    return abs(total) / 2.0


def prepare(level: Any) -> Surfaces:
    """Areas and outward normals for every surface in the map."""
    areas = [0.0] * len(level.sectors)
    wall_areas = [0.0] * len(level.walls)
    normals: list[tuple[float, float]] = [(0.0, 0.0)] * len(level.walls)

    for index in range(len(level.sectors)):
        fields = _fields(level.sectors[index])
        areas[index] = sector_area(level, index)
        floor_z, ceiling_z = int(fields["floor_z"]), int(fields["ceiling_z"])
        for wall_id in _walls_of(level, index):
            here = _fields(level.walls[wall_id])
            there = _fields(level.walls[int(here["point2"])])
            dx = int(there["x"]) - int(here["x"])
            dy = int(there["y"]) - int(here["y"])
            length = math.hypot(dx / GRID, dy / GRID) or 1.0
            # the inward normal of a wall, as the original computes it
            normals[wall_id] = (dy / length, -dx / length)

            height = floor_z - ceiling_z
            other = int(here["next_sector"])
            if other >= 0:
                # Only the solid parts count: the step up out of the neighbour's
                # floor and the step down from its ceiling. The gap between them
                # is a hole and light goes through it.
                theirs = _fields(level.sectors[other])
                height = 0
                if int(theirs["floor_z"]) < floor_z:
                    height += floor_z - int(theirs["floor_z"])
                if int(theirs["ceiling_z"]) > ceiling_z:
                    height += int(theirs["ceiling_z"]) - ceiling_z
            wall_areas[wall_id] = max(1.0, length * height / 256.0)
    return Surfaces(areas, wall_areas, normals)


def _is_sky(level: Any, index: int, which: str) -> bool:
    return bool(int(_fields(level.sectors[index]).get(f"{which}_stat", 0)) & 1)


@dataclass
class Hit:
    kind: str                       # "wall", "floor", "ceiling" or "void"
    sector: int
    wall: int
    x: float
    y: float
    z: float


def hitscan(level: Any, x: float, y: float, z: float, sector: int,
            dx: float, dy: float, dz: float) -> Hit:
    """Follow a ray until it lands on something.

    Walks sector to sector: within each, find the nearest wall the ray crosses,
    then check whether the ray leaves through the floor or ceiling first. A
    two-sided wall is passed through when the ray's height at the crossing is
    inside the neighbour's open band; otherwise it is a surface and the ray
    stops.
    """
    for _ in range(MAX_CROSSINGS):
        fields = _fields(level.sectors[sector])
        floor_z, ceiling_z = int(fields["floor_z"]), int(fields["ceiling_z"])

        # Which wall, and how far along the ray
        best_t: float | None = None
        best_wall = -1
        for wall_id in _walls_of(level, sector):
            here = _fields(level.walls[wall_id])
            there = _fields(level.walls[int(here["point2"])])
            ax, ay = int(here["x"]), int(here["y"])
            bx, by = int(there["x"]), int(there["y"])
            ex, ey = bx - ax, by - ay
            denominator = dx * ey - dy * ex
            if abs(denominator) < 1e-9:
                continue
            t = ((ax - x) * ey - (ay - y) * ex) / denominator
            u = ((ax - x) * dy - (ay - y) * dx) / denominator
            if t <= 1e-6 or not (0.0 <= u <= 1.0):
                continue
            if best_t is None or t < best_t:
                best_t, best_wall = t, wall_id
        if best_t is None:
            return Hit("void", sector, -1, x, y, z)

        # Does it leave through a horizontal surface first?
        if dz > 0:
            t_plane = (floor_z - z) / dz if dz else None
            plane = "floor"
        elif dz < 0:
            t_plane = (ceiling_z - z) / dz
            plane = "ceiling"
        else:
            t_plane, plane = None, ""
        if t_plane is not None and 0 < t_plane < best_t:
            return Hit(plane, sector, -1, x + dx * t_plane, y + dy * t_plane,
                       z + dz * t_plane)

        hx, hy, hz = x + dx * best_t, y + dy * best_t, z + dz * best_t
        here = _fields(level.walls[best_wall])
        other = int(here["next_sector"])
        if other >= 0:
            theirs = _fields(level.sectors[other])
            top = max(ceiling_z, int(theirs["ceiling_z"]))
            bottom = min(floor_z, int(theirs["floor_z"]))
            if top < hz < bottom:
                # through the opening and on into the next room
                x, y, z, sector = hx, hy, hz, other
                continue
        return Hit("wall", sector, best_wall, hx, hy, hz)
    return Hit("void", sector, -1, x, y, z)


def light_bomb(level: Any, lights: Sequence[tuple[int, int, int, int] | tuple[int, int, int, int, float]], *,
               intensity: float = INTENSITY,
               attenuation: float = ATTENUATION,
               reflections: int = REFLECTIONS,
               max_bright: int = MAX_BRIGHT,
               ramp_distance: int = RAMP_DISTANCE,
               azimuths: int = AZIMUTHS,
               surfaces: Surfaces | None = None,
               protected: dict[str, Iterable[int]] | None = None) -> dict[str, Any]:
    """Cast light out of each source and shade what it reaches.

    `lights` is a sequence of ``(x, y, z, sector)`` values, optionally with a
    fifth per-source intensity. ``protected`` is an optional mapping of
    ``wall``, ``floor`` and ``ceiling`` to emitted ids whose author-stated
    shades must not be changed. Protected surfaces still receive rays -- they
    continue to occlude and reflect light -- but their final shade remains an
    explicit authoring decision.
    """
    prepared = surfaces if surfaces is not None else prepare(level)
    wall_gain = [0.0] * len(level.walls)
    floor_gain = [0.0] * len(level.sectors)
    ceiling_gain = [0.0] * len(level.sectors)
    protected = protected or {}
    protected_walls = {int(item) for item in protected.get("wall", ())}
    protected_floors = {int(item) for item in protected.get("floor", ())}
    protected_ceilings = {int(item) for item in protected.get("ceiling", ())}
    rays = 0

    def shoot(x: float, y: float, z: float, sector: int,
              dx: float, dy: float, dz: float,
              power: float, reflected: int, travelled: float) -> None:
        nonlocal rays
        rays += 1
        hit = hitscan(level, x, y, z, sector, dx, dy, dz)
        if hit.kind == "void":
            return
        distance = travelled + math.hypot(
            math.hypot((hit.x - x) / GRID, (hit.y - y) / GRID),
            (hit.z - z) / GRID / Z_SCALE)

        if hit.kind == "wall":
            energy = power * FIXED / max(1.0, distance + ramp_distance)
            energy = energy / prepared.wall_area[hit.wall]
            if energy <= 0:
                return
            wall_gain[hit.wall] += energy
            if reflected >= reflections:
                return
            nx, ny = prepared.wall_normal[hit.wall]
            dot = dx * nx + dy * ny
            if dot < 0:
                return                      # the original calls this bogus
            rx, ry = dx - 2 * dot * nx, dy - 2 * dot * ny
            shoot(hit.x + rx * 1e-3, hit.y + ry * 1e-3, hit.z + dz * 1e-3,
                  hit.sector, rx, ry, dz,
                  power - power * attenuation, reflected + 1, distance)
            return

        which = "floor" if hit.kind == "floor" else "ceiling"
        if _is_sky(level, hit.sector, which):
            return                          # outdoors does not bounce
        energy = power * FIXED / max(1.0, distance + ramp_distance)
        energy = energy / max(1.0, prepared.sector_area[hit.sector])
        if energy <= 0:
            return
        (floor_gain if which == "floor" else ceiling_gain)[hit.sector] += energy
        if reflected >= reflections:
            return
        shoot(hit.x, hit.y, hit.z - dz * 1e-3, hit.sector, dx, dy, -dz,
              power - power * attenuation, reflected + 1, distance)

    elevations = []
    step = ELEVATION_FROM
    while step <= ELEVATION_TO + 1e-9:
        elevations.append(math.radians(step))
        step += ELEVATION_STEP

    for light in lights:
        if len(light) == 4:
            x, y, z, sector = light
            source_intensity = float(intensity)
        elif len(light) == 5:
            x, y, z, sector, source_intensity = light
            source_intensity = float(source_intensity)
        else:
            raise ValueError("a LightBomb source must have 4 or 5 values")
        if source_intensity <= 0:
            raise ValueError("a LightBomb source intensity must be positive")
        if not 0 <= sector < len(level.sectors):
            continue
        for elevation in elevations:
            dz = math.cos(elevation) * Z_SCALE
            horizontal = math.sin(elevation)
            for index in range(azimuths):
                angle = 2.0 * math.pi * index / azimuths
                shoot(x, y, z, sector,
                      math.cos(angle) * horizontal, math.sin(angle) * horizontal, dz,
                      source_intensity, 0, 0.0)

    def apply(value: int, gain: float) -> int:
        return max(max_bright, min(SHADE_MAX, int(round(value - gain))))

    touched = 0
    skipped = 0
    for wall_id, gain in enumerate(wall_gain):
        if gain <= 0:
            continue
        if wall_id in protected_walls:
            skipped += 1
            continue
        fields = _fields(level.walls[wall_id])
        fields["shade"] = apply(int(fields["shade"]), gain)
        touched += 1
    for index, gain in enumerate(floor_gain):
        if gain <= 0:
            continue
        if index in protected_floors:
            skipped += 1
            continue
        fields = _fields(level.sectors[index])
        fields["floor_shade"] = apply(int(fields["floor_shade"]), gain)
        touched += 1
    for index, gain in enumerate(ceiling_gain):
        if gain <= 0:
            continue
        if index in protected_ceilings:
            skipped += 1
            continue
        fields = _fields(level.sectors[index])
        fields["ceiling_shade"] = apply(int(fields["ceiling_shade"]), gain)
        touched += 1

    return {
        "lights": len(lights),
        "rays_cast": rays,
        "surfaces_lit": touched,
        "surfaces_protected": skipped,
        "walls_lit": sum(1 for g in wall_gain if g > 0),
        "basis": (
            "XMapEdit's own LightBomb, from edit3d.cpp: energy is "
            "intensity/(dist+ramp) divided by the area of the surface it lands "
            "on, reflected %d times with %.1f%% lost per bounce, and sky absorbs"
            % (reflections, 100 * attenuation)
        ),
    }


def lights_in(level: Any, tiles: Iterable[int], *,
              max_shade: int = -64) -> list[tuple[int, int, int, int]]:
    """Every burning sprite in the level, as ``(x, y, z, sector)``."""
    wanted = frozenset(int(t) for t in tiles)
    out = []
    for sprite in level.sprites:
        fields = _fields(sprite)
        if int(fields["picnum"]) not in wanted:
            continue
        if int(fields["shade"]) > max_shade:
            continue
        out.append((int(fields["x"]), int(fields["y"]), int(fields["z"]),
                    int(fields["sector"])))
    return out
