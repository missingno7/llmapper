"""One light over a map's open sky: outdoor faces shaded as the campaign shades them, the sun's reach traced with the engine's hitscan, and the measure of it.

The owner, 2026-11-20: "Overall it feels like there is no real direction of
natural light and shadows in the city exterior ... Looks like this might be
a systematic problem." It was: every facade of the city took one flat shade.

WHAT THE CAMPAIGN DOES (`measure`; `python -m tools.light_profile`). The
first version of this pass assumed one sun shading every outdoor wall by its
facing, and a blind reader preferred it in 4 and 8 of 23 street views. The
assumption was wrong. Fitted over a whole map, one sun explains 0 to 19% of
the outdoor wall shade, and its best direction differs from map to map,
because each building carries its own tone. Measured WITHIN buildings it is
there:

=====  ===========================  ==================  ===============
map    darker face at a corner,     corner step,        faces of one
       share by facing N/E/S/W      p25 / p50 / p75     tile, sd
=====  ===========================  ==================  ===============
E3M1   0.05 / 0.26 / 0.46 / 0.23    7 / 10 / 15         6.9
E2M1   0.11 / 0.34 / 0.18 / 0.38    8 / 14 / 18.5       7.8
E6M1   0.11 / 0.40 / 0.05 / 0.44    8 / 16 / 16         7.5
E1M4   0.24 / 0.26 / 0.27 / 0.23    6 / 11 / 16         9.0
city   (72% of corners equal)       0                   1.5
=====  ===========================  ==================  ===============

In E3M1 the same face of a corner is the darker one 11 of 12 to 14 of 17
times for each pair of facings: the light comes from the north (map -y; a
sun fitted with a base per building points to 265-270), north faces are
the brightest, south the darkest, east and west between. So a face's shade
is its BUILDING'S TONE plus a STEP BY FACING, and every corner of a building
shows two planes. The first version also put its sun at 45 degrees, where a
south face and an east face are lit alike, and gave most corners no step.

THE SUN'S REACH (owner: "How that light bomb works, can't we use it?").
`lightbomb.hitscan` follows a ray through the map as the engine draws it:
through an opening where it is open at that height, stopped by the first
solid surface, and out through a parallax sky. A face turned to the light
is brightened only as far as the light reaches it: from points on it a ray
is cast TOWARD the sun, and the share that reach the sky is the share lit.
A north face looking into a narrow alley is shadowed by the building
across it, which no facing angle can know.

THE SCALE (measured, `bloodmap.shade_table`; owner: "our scaling might be
wrong, you should check the overall brightness of actual texture"). A
shade takes 1/64 of a texture's full brightness, linearly; below 0 is
drawn as 0 up close and only holds off the distance term (about 1.2 shade
per 1024 units at visibility 800). The city's facade tiles are dark (mean
39-67 of 255 at shade 0) and busy (texel spread 12-34): a step must be
10-20 shades to equal half the texture's own contrast. The version with a
step of 8 on facades at shade 9 changed 8 per channel where it changed
anything, and a blind reader called the pair "nearly identical" -- the
light was invisible, not wrong. Hence `FACADE_LEVEL` and `STEP` below.

`apply`: the outdoor faces are moved, together, so their median stands at
`FACADE_LEVEL` (what the lamps added and what the passes stated stays, as
an offset); then each takes its building's tone (`TONE` either way, from a
hash of where the building stands, so a rebuild gives the same city) and a
step by facing: turned away from the light, up to `STEP` darker; turned to
it and reached, up to `STEP` brighter; turned to it and not reached, as
dark as turned away. Interiors are not touched.
"""

from __future__ import annotations

import math
import statistics
import zlib
from collections import defaultdict
from typing import Any

from .model import record_fields as _fields

#: Where the light comes from, as a map direction (degrees: 0 is +x, east;
#: 90 is +y, south, Build's y running down; 270 is north). E3M1 and E2M1,
#: fitted with a base per building, put it at 265-270 and 260. Turned 30
#: degrees off north so east and west faces differ too: from due north both
#: facades of a north-south street are side on, and the avenue never changed.
SUN_AZIMUTH = 300.0
#: how high the sun stands, degrees above the horizon: a street a building's
#: height wide is half in shade
SUN_ELEVATION = 45.0
#: shades a face turned squarely to the light is brightened, and one turned
#: squarely away darkened. 16: about half the texel spread of the city's
#: commonest facade tiles (10-14 shades, `shade_table`), so a corner reads
#: through the texture; E3M1's own corner step is 10, at the edge of that
STEP = 16
#: each building's tone, either way: faces of one tile spread about 7 in the
#: campaign, 1.5 in the city
TONE = 5
#: where the outdoor faces' median is put before the light is laid: room
#: for STEP both ways inside the owner's usable 0..40 (below 0 looks the
#: same as 0 up close). The derived default had them at 9, with no room to
#: brighten.
FACADE_LEVEL = 20
#: kept from the first version: the facades' level against the ground's
BASE_UNDER_GROUND = 4
#: walls shorter than this are corners and chamfers, not faces
MIN_FACE = 256
#: points sampled along a face, at most, and the heights above its foot (in
#: standing bodies) they are sampled at
SAMPLES_ALONG = 4
SAMPLE_HEIGHTS = (0.5, 1.5)
BODY = 16960
SHADE_RANGE = (-128, 63)


def _owners(disk: Any) -> dict[int, int]:
    out = {}
    for index, sector in enumerate(disk.sectors):
        f = _fields(sector)
        for wall in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            out[wall] = index
    return out


def _open(disk: Any, sector: int) -> bool:
    return bool(int(_fields(disk.sectors[sector])["ceiling_stat"]) & 1)


def outdoor_faces(disk: Any) -> list[tuple[int, float]]:
    """(wall, facing in degrees) for every wall seen from an open-sky sector.

    Build winds a sector's outer loop so its inside is on the right of each
    wall, so the wall faces (-dy, dx) of its run: into the sector it is seen
    from. A two-sided wall counts when the neighbour stands up as a step or
    hangs down as a lintel, i.e. when the street sees some of it.
    """
    owners = _owners(disk)
    out = []
    for index, wall in enumerate(disk.walls):
        f = _fields(wall)
        here = owners.get(index)
        if here is None or not _open(disk, here):
            continue
        other = int(f["next_sector"])
        if other >= 0:
            mine, theirs = _fields(disk.sectors[here]), _fields(disk.sectors[other])
            step = int(theirs["floor_z"]) < int(mine["floor_z"])
            lintel = (not int(theirs["ceiling_stat"]) & 1
                      and int(theirs["ceiling_z"]) > int(mine["ceiling_z"]))
            if not (step or lintel):
                continue
        n = _fields(disk.walls[int(f["point2"])])
        dx, dy = int(n["x"]) - int(f["x"]), int(n["y"]) - int(f["y"])
        if math.hypot(dx, dy) < MIN_FACE:
            continue
        out.append((index, math.degrees(math.atan2(dx, -dy)) % 360))
    return out


def _quarter(angle: float) -> str:
    return "ESWN"[int(((angle + 45) % 360) // 90)]


def _loops(disk: Any) -> dict[int, int]:
    """wall -> the first wall of the loop it lies on."""
    out: dict[int, int] = {}
    for start in range(len(disk.walls)):
        if start in out:
            continue
        wall = start
        while wall not in out:
            out[wall] = start
            wall = int(_fields(disk.walls[wall])["point2"])
    return out


def _buildings(disk: Any, faces) -> dict[int, tuple]:
    """face -> its building: the loop it lies on and the tile it wears.

    A street's hole loop is one building's footprint; the street's outer loop
    runs along many, and the city gives each building its own facade tile.
    The key is the loop's lowest vertex, not a wall index, so it survives a
    rebuild that renumbers walls.
    """
    loop_of = _loops(disk)
    corner: dict[int, tuple] = {}
    for wall, start in loop_of.items():
        f = _fields(disk.walls[wall])
        point = (int(f["x"]), int(f["y"]))
        if start not in corner or point < corner[start]:
            corner[start] = point
    return {wall: (corner[loop_of[wall]], int(_fields(disk.walls[wall]).get("picnum", 0)))
            for wall, _ in faces}


def sun_reach(disk: Any, faces, *, azimuth: float = SUN_AZIMUTH,
              elevation: float = SUN_ELEVATION) -> dict[int, float]:
    """face -> the share of points on it from which a ray toward the sun reaches the sky.

    Only faces turned toward the light are traced; the rest get 0. Each point
    stands a little in front of the face, in the open sector it is seen
    from, at `SAMPLE_HEIGHTS` above the face's foot (the higher of its own
    floor and, for a step, the neighbour's).
    """
    from .lightbomb import Z_SCALE, ScanIndex, hitscan

    owners = _owners(disk)
    scan = ScanIndex(disk)
    sun = math.radians(azimuth)
    rise = math.radians(elevation)
    dx, dy = math.cos(sun) * math.cos(rise), math.sin(sun) * math.cos(rise)
    dz = -math.sin(rise) * Z_SCALE              # up is -z
    out: dict[int, float] = {}
    for wall, angle in faces:
        if math.cos(math.radians(angle) - sun) <= 0:
            out[wall] = 0.0
            continue
        f = _fields(disk.walls[wall])
        n = _fields(disk.walls[int(f["point2"])])
        ax, ay, bx, by = int(f["x"]), int(f["y"]), int(n["x"]), int(n["y"])
        length = math.hypot(bx - ax, by - ay)
        nx, ny = -(by - ay) / length, (bx - ax) / length     # into the sector
        sector = owners[wall]
        floor = int(_fields(disk.sectors[sector])["floor_z"])
        other = int(f["next_sector"])
        foot = floor
        if other >= 0:
            foot = min(floor, int(_fields(disk.sectors[other])["floor_z"]))
        ceiling = int(_fields(disk.sectors[sector])["ceiling_z"])
        along = max(1, min(SAMPLES_ALONG, int(length // 512)))
        hits = total = 0
        for k in range(along):
            t = (k + 0.5) / along
            px, py = ax + (bx - ax) * t + nx * 8, ay + (by - ay) * t + ny * 8
            for height in SAMPLE_HEIGHTS:
                pz = foot - height * BODY
                if pz <= ceiling:
                    continue
                total += 1
                hit = hitscan(disk, px, py, pz, sector, dx, dy, dz, index=scan)
                if hit.kind == "ceiling" and _open(disk, hit.sector):
                    hits += 1
        out[wall] = hits / total if total else 1.0
    return out


def measure(disk: Any) -> dict[str, Any]:
    """The outdoor light of a map, in the campaign's terms."""
    faces = outdoor_faces(disk)
    shades = {index: int(_fields(disk.walls[index])["shade"]) for index, _ in faces}
    angles = dict(faces)
    by = {q: [] for q in "NESW"}
    for index, angle in faces:
        by[_quarter(angle)].append(shades[index])
    grounds = [int(_fields(s)["floor_shade"]) for i, s in enumerate(disk.sectors)
               if _open(disk, i)]
    medians = {q: (statistics.median(v) if v else None) for q, v in by.items()}
    known = [m for m in medians.values() if m is not None]
    values = list(shades.values())
    # corners: a face and the next along its loop, turned 60-120 degrees
    steps, equal = [], 0
    darker = {q: 0 for q in "NESW"}
    for index, angle in faces:
        other = int(_fields(disk.walls[index])["point2"])
        if other not in angles:
            continue
        turn = abs((angles[other] - angle + 180) % 360 - 180)
        if not 60 <= turn <= 120:
            continue
        a, b = shades[index], shades[other]
        if a == b:
            equal += 1
            continue
        steps.append(abs(a - b))
        darker[_quarter(angle if a > b else angles[other])] += 1
    corners = len(steps) + equal
    # within a building: each face against its building's mean, by facing
    building = _buildings(disk, faces)
    groups: dict[tuple, list] = defaultdict(list)
    for index, angle in faces:
        groups[building[index]].append((angle, shades[index]))
    within = {q: [] for q in "NESW"}
    for items in groups.values():
        if len({_quarter(a) for a, _ in items}) < 2:
            continue
        mean = statistics.fmean(s for _, s in items)
        for angle, shade in items:
            within[_quarter(angle)].append(shade - mean)
    tiles: dict[int, list] = defaultdict(list)
    for index, _ in faces:
        tiles[int(_fields(disk.walls[index]).get("picnum", 0))].append(shades[index])
    tile_sd = [statistics.pstdev(v) for v in tiles.values() if len(v) >= 4]
    unequal = sum(darker.values()) or 1
    return {
        "walls": len(values),
        "wall_sd": round(statistics.pstdev(values), 1) if len(values) > 1 else 0.0,
        "wall_median": statistics.median(values) if values else None,
        "by_facing": medians,
        "facing_step": (max(known) - min(known)) if known else 0,
        "ground_median": statistics.median(grounds) if grounds else None,
        "ground_sd": round(statistics.pstdev(grounds), 1) if len(grounds) > 1 else 0.0,
        "corners": corners,
        "corner_equal": round(equal / corners, 2) if corners else None,
        "corner_step": statistics.median(steps) if steps else 0,
        "corner_darker": {q: round(darker[q] / unequal, 2) for q in "NESW"},
        "within_building": {q: (round(statistics.median(v), 1) if v else None)
                            for q, v in within.items()},
        "tile_sd": round(statistics.fmean(tile_sd), 1) if tile_sd else None,
    }


def _tone(key: tuple, spread: int) -> int:
    """A building's own tone, the same on every build."""
    if not spread:
        return 0
    value = zlib.crc32(repr(key).encode("utf-8")) % (2 * spread + 1)
    return int(value) - spread


def apply(disk: Any, *, azimuth: float = SUN_AZIMUTH, elevation: float = SUN_ELEVATION,
          step: int = STEP, tone: int = TONE, reach: bool = True,
          base: int | None = FACADE_LEVEL) -> dict[str, Any]:
    """Shade every outdoor face: its building's tone, and a step by facing and reach.

    A face turned away from the light by an angle gets `step * cos` darker; a
    face turned to it is brightened by `step * cos` where the light reaches
    it (`sun_reach`, unless `reach` is False) and darkened as much where it
    does not. `base` is where the outdoor faces' median is moved first (what
    the lamps added stays, as an offset); None leaves the level as it is.
    Returns the light before and after.
    """
    before = measure(disk)
    faces = outdoor_faces(disk)
    if not faces:
        return {"before": before, "after": before, "walls": 0}
    shift = 0 if base is None else int(round(base - before["wall_median"]))
    building = _buildings(disk, faces)
    lit = (sun_reach(disk, faces, azimuth=azimuth, elevation=elevation) if reach
           else {wall: 1.0 for wall, _ in faces})
    sun = math.radians(azimuth)
    turned = reached = 0
    for index, angle in faces:
        f = _fields(disk.walls[index])
        facing = math.cos(math.radians(angle) - sun)
        if facing > 0:
            turned += 1
            share = lit[index]
            reached += share
            offset = step * facing * (1 - 2 * share)
        else:
            offset = -step * facing
        offset += _tone(building[index], tone)
        value = int(f["shade"]) + shift + int(round(offset))
        f["shade"] = max(SHADE_RANGE[0], min(SHADE_RANGE[1], value))
    return {"before": before, "after": measure(disk), "walls": len(faces),
            "azimuth": azimuth, "elevation": elevation, "step": step, "tone": tone,
            "shift": shift, "faces_turned_to_light": turned,
            "reached_share": round(reached / turned, 2) if turned else None}


# --- shadows on the ground -------------------------------------------------
#
# The owner, 2026-11-20: "Eventually we should have the real shadows on the
# ground ... some general handling of shadows that won't break geometry."
# Build shades a floor per sector, so a shadow is a cut in the ground. It is
# declared as an overlay (`bloodmap.overlays`): the street stays one space in
# the source and is cut only when the map is emitted.

#: how far a shadow reaches per unit of height above the ground it falls on,
#: in plan units per plan unit (a sun about 50 degrees up). Build's z is 16
#: times finer than its plan, so a wall of h z-units throws h/16 * this.
SHADOW_REACH = 0.8
#: no shadow reaches further than this (plan units), however tall the wall
SHADOW_MAX = 4096
#: shadows are measured in steps of this, so neighbouring walls of nearly one
#: height throw one straight edge, not a staircase
SHADOW_STEP = 256
#: shades a shadow is darker than the lit ground beside it
SHADOW_SHADE = 12
#: a shadow smaller than this side squared is not laid
SAMPLE = 512
#: a ground region smaller than this (plan units squared) is not shadowed
MIN_GROUND = 1024 * 1024
#: an open region lower than a standing body (z) is a sky backing or a
#: ledge, not ground anyone walks on (`player_space.PLAYER_PROFILES`)
PLAYER_STANDING = 16960
#: the highest step a body climbs (z); ground with no neighbour within it is
#: the top of a mass, a roof or a wall, which no one walks on
MAX_STEP = 4096


def _ground_regions(layout: Any, skipped: dict | None = None) -> list[Any]:
    from .overlays import uncuttable

    refused = uncuttable(layout)
    out = []
    for region in layout.regions.values():
        if not region.parallax_ceiling:
            continue
        why = refused.get(region.region_id) or (region.special and f"special {region.special}")
        if why:
            if skipped is not None:
                skipped[region.region_id] = why
            continue
        out.append(region)
    return out


def tops(layout: Any) -> set[str]:
    """Regions that stand above everything around them: masses, roofs, crates, piles.

    Regions joined within a step are one floor a body walks; a floor whose
    every way out drops by more than a step is the top of something -- a
    street-end mass, a yard wall, a roof, a crate on a deck -- open to the
    sky but not ground anyone walks. (Walking from the player start was
    tried first; it missed the station, whose platforms are reached through
    constructs the plain connection graph does not carry.)
    """
    joined: dict[str, set] = {}
    for connection in layout.connections.values():
        if connection.region_a in layout.regions and connection.region_b in layout.regions:
            joined.setdefault(connection.region_a, set()).add(connection.region_b)
            joined.setdefault(connection.region_b, set()).add(connection.region_a)

    def floor(rid: str) -> int:
        return int(layout.regions[rid].floor_z)

    seen: set[str] = set()
    out: set[str] = set()
    for rid in layout.regions:
        if rid in seen:
            continue
        group, frontier = {rid}, [rid]
        while frontier:
            here = frontier.pop()
            for other in joined.get(here, ()):
                if other not in group and abs(floor(here) - floor(other)) <= MAX_STEP:
                    group.add(other)
                    frontier.append(other)
        seen |= group
        exits = [(here, other) for here in group for other in joined.get(here, ())
                 if other not in group]
        # Build's z runs down: every way out a drop of more than a step
        if exits and all(floor(other) - floor(here) > MAX_STEP for here, other in exits):
            out |= group
    return out


def _sweep(polygon: Any, dx: float, dy: float) -> Any:
    """The ground a polygon's shadow covers: the polygon dragged along (dx, dy)."""
    from shapely.affinity import translate
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    parts = [polygon, translate(polygon, dx, dy)]
    for part in getattr(polygon, "geoms", [polygon]):
        for ring in (part.exterior, *part.interiors):
            coords = list(ring.coords)
            for a, b in zip(coords, coords[1:]):
                quad = Polygon([a, b, (b[0] + dx, b[1] + dy), (a[0] + dx, a[1] + dy)])
                if quad.area > 0:
                    parts.append(quad)
    return unary_union(parts)


def cast_shadows(layout: Any, *, azimuth: float = SUN_AZIMUTH,
                 reach: float = SHADOW_REACH, shade: int = SHADOW_SHADE,
                 sunlit: int = 0, longest: int = SHADOW_MAX,
                 regions: Any = None) -> dict[str, Any]:
    """Declare the sun's shadow on every open-sky ground region, as overlays.

    Shadows are cast by MASSES, not by the edges of the ground they fall on:
    a road is bordered by its pavement, a kerb high, and the building beyond
    the pavement is what darkens the road. Everything in plan that is not
    open sky -- a building, a roofed room, the world beyond its edge -- is a
    mass as tall as the sky (Build draws the wall above a roofed neighbour up
    to the street's own sky); an open floor standing higher than the ground
    is a mass as tall as its rise. Each throws its footprint away from the
    sun for `reach` times its height (at most `longest`). The union, clipped
    to a region where a body can stand, is laid on it as one overlay of
    `shade` darker; with `sunlit` (negative: brighter) the rest of that
    ground is laid as well, so the step between sun and shadow is
    `shade - sunlit` and both sides of it move.
    """
    from shapely import STRtree, set_precision
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union

    sun = math.radians(azimuth)
    sx, sy = math.cos(sun), math.sin(sun)
    polys = {}
    for rid, region in layout.regions.items():
        polygon = Polygon(region.outer, region.holes)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        polys[rid] = polygon
    open_ids = [rid for rid, r in layout.regions.items() if r.parallax_ceiling]
    open_union = unary_union([polys[rid] for rid in open_ids])
    minx, miny, maxx, maxy = open_union.bounds
    world = box(minx - 2 * longest, miny - 2 * longest, maxx + 2 * longest, maxy + 2 * longest)
    masses = world.difference(open_union)
    tall = _sweep(masses, -sx * longest, -sy * longest).buffer(0)
    tree = STRtree([polys[rid] for rid in open_ids])
    raised = tops(layout)
    wanted = None if regions is None else set(regions)
    report = {"regions": 0, "area": 0.0, "ground_area": 0.0, "skipped": {}, "shadowed": {}}
    # ground the shadows do not cut (a lamp's pool, a sloped headland) still
    # stands in the sun, or a pool would read darker than the street round it
    ground_regions = _ground_regions(layout, report["skipped"])
    if sunlit:
        for rid, why in report["skipped"].items():
            region = layout.regions[rid]
            if int(region.floor_z) - int(region.ceiling_z) < PLAYER_STANDING:
                continue
            layout.add_overlay(f"sun:{rid}", rid, [(list(region.outer),
                                                    [list(h) for h in region.holes])],
                               floor_shade_offset=sunlit,
                               note=f"the sun on open ground ({why}: not cut)")
    for region in ground_regions:
        rid = region.region_id
        if wanted is not None and rid not in wanted:
            continue
        ground = polys[rid]
        if int(region.floor_z) - int(region.ceiling_z) < PLAYER_STANDING:
            report["skipped"][rid] = "no one stands there (lower than a body)"
            continue
        if rid in raised:
            report["skipped"][rid] = "a top: every way off it drops more than a step"
            continue
        if ground.area < MIN_GROUND:
            continue
        casts = [tall.intersection(ground)]
        near = ground.buffer(longest)
        for index in tree.query(near):
            other_id = open_ids[int(index)]
            other = layout.regions[other_id]
            if other_id == rid:
                continue
            rise = int(region.floor_z) - int(other.floor_z)
            if rise <= 0:
                continue
            run = min(longest, rise / 16.0 * reach)
            run = SHADOW_STEP * round(run / SHADOW_STEP)
            if run < SHADOW_STEP:
                continue
            casts.append(_sweep(polys[other_id], -sx * run, -sy * run).intersection(ground))
        shadow = unary_union(casts).intersection(ground)
        shadow = set_precision(shadow.simplify(32), 1.0)
        if sunlit:
            layout.add_overlay(f"sun:{rid}", rid, [(list(region.outer),
                                                    [list(h) for h in region.holes])],
                               floor_shade_offset=sunlit,
                               note=f"the sun on open ground, azimuth {azimuth}")
        if shadow.is_empty or shadow.area < SAMPLE * SAMPLE:
            continue
        shapes = []
        for part in getattr(shadow, "geoms", [shadow]):
            if part.geom_type != "Polygon" or part.area < SAMPLE * SAMPLE / 2:
                continue
            shapes.append(([tuple(c) for c in part.exterior.coords[:-1]],
                           [[tuple(c) for c in h.coords[:-1]] for h in part.interiors]))
        if not shapes:
            continue
        layout.add_overlay(f"shadow:{rid}", rid, shapes, floor_shade_offset=shade,
                           note=f"the sun's shadow, azimuth {azimuth}")
        report["regions"] += 1
        report["shadowed"][rid] = round(shadow.area / ground.area, 2)
        report["area"] += shadow.area
        report["ground_area"] += ground.area
    report["share"] = round(report["area"] / report["ground_area"], 3) if report["ground_area"] else 0.0
    report["area"] = int(report["area"])
    report["ground_area"] = int(report["ground_area"])
    return report
