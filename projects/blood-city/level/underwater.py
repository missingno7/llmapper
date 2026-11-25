"""The drowned places: the pumps' sump under the settling basin, the flooded branch that is dived to, and the slip under the Demeter's keel.

The owner, 2026-11-25: "There are no underwater places, I would add few like
that tank in pump station", and "Some secret locations are too visible and easy
to access". One idea each, and not much else in the water:

* THE SUMP: the basin is the top of a well four bodies deep. At its foot the
  pumps' own wheel stands behind a screen, the one light down there, coming and
  going with their beat, and against the screen lies what they drew in. A pipe
  goes on south, under the ring, and comes up in the junction.
* THE FLOODED BRANCH, a secret: its mouth on the ring's south walk is barred,
  and what lies on the bank at its back can be seen through the bars. The way in
  is from the cistern's tank, by a crawl broken through under the south channel,
  into a hall where the drowned stand on their chains.
* THE SLIP: the water between the quay, the Demeter and the jetty is open, and
  a ramp comes up out of it onto the quay. Below, the hull hangs in the light
  like a whale's, and under its keel lies the ship's boat with one of her boxes.

The drowned half of a place is not under it: it is `OFFSET` away on the sheet,
all of it, so a swim goes the way the streets over it go
(`bloodmap.roomoverroom.water_link`). Every swim is under ten seconds at a walk;
air lasts ten (player.cpp: 1,200 tics of 120).

Study: `knowledge/blood/studies/underwater`.
"""

from __future__ import annotations

import math

from bloodmap import arrangement as A
from bloodmap.roomoverroom import water_link
from bloodmap.slope import SlopeSpec

PU = 1024
#: the lower sector of every pair, less its upper one (plan units)
OFFSET = (-60, 0)
LAYER = "drowned"
GRADE = 8192
BODY = 16960
#: the surfaces: the pump hall's basin (`l3_shed.BASIN_WATER`), the sewers' water, the sea
SEWER, RUN = 61440, 63488
SEA = GRADE + 29696
KEY = "region:gravesend/drowned"
#: link ids: the manholes have 10 to 13
LINKS = {"sump": 30, "junction": 31, "cistern": 32, "branch": 33, "slip": 34}

TANK = "region:gravesend/foundry_ward/pump_station/tank_0"
JUNCTION = "region:gravesend/sewer/trunk/junction"
CISTERN = "region:gravesend/sewer/trunk/cistern"
BRANCH = "region:gravesend/sewer/chambers/flooded"
WALK = "region:gravesend/sewer/ring/s_walk"
QUAY = "region:gravesend/market_slip/quay"
RIVER, SLIP, RAMP, JETTY = f"{QUAY}/river", f"{QUAY}/slip", f"{QUAY}/slip_ramp", f"{QUAY}/jetty"

SEWAGE, SILT, STONE, BRICK, PIPE, PLATE, RUBBLE, VAULT = 1120, 568, 568, 492, 255, 510, 110, 253
SCREEN, WHEEL, MAIN, LATTICE, RIM = 191, 483, 211, 502, 200
SEA_TILE, SEA_PAL, HULL, PLANK, EARTH, BED, ROCK, QUAYSIDE, PILE = 2490, 10, 67, 15, 270, 358, 458, 411, 20

#: --- the sump -------------------------------------------------------------------
SUMP_TOP, SUMP_FLOOR, SUMP_PIT = 34816, 104448, 110592
GALLERY_TOP = SUMP_FLOOR - 38912
GALLERY = [(40.6, 5.5), (43.8, 5.5), (44.4, 6.1), (44.4, 8.6), (43.7, 9.2), (40.8, 9.2), (40.1, 8.5), (40.1, 6.2)]
#: the two mains that go up out of the gallery's roof to the pumps
MAINS, MAIN_R = ((41.75, 8.15), (43.35, 7.45)), 0.27
#: the screen's throat, square as the wheel's tile is (1,408 units, 21,845 z)
THROAT = (38.5, 6.7, 39.85, 8.075)
#: bars hang where both sides stand at one level (`tools.city_profile`): a length of the throat before its screen
REVEAL = 40.1
THROAT_FLOOR, THROAT_TOP = SUMP_FLOOR - 4096, SUMP_FLOOR - 4096 - 21888
CULVERT = (42.0, 42.35, 43.05, 43.4)                      # the pipe's four lines across, north to south
PIPE_FLOOR, PIPE_TOP, PIPE_ROUND = SUMP_FLOOR - 2048, SUMP_FLOOR - 2048 - 23552, 7168
WELL = (42.0, 11.25, 43.4, 12.85)
KERB, KERB_WIDE = 1024, 0.2
#: --- the flooded branch ----------------------------------------------------------
TANK_POOL = (43.3, 28.0, 44.9, 30.4)
TANK_FLOOR = RUN + 38912
CRAWL = [(43.6, 30.4), (44.5, 30.4), (44.5, 33.4), (43.45, 33.4), (43.45, 34.5), (42.55, 34.5), (42.55, 32.5), (43.6, 32.5)]
CRAWL_CLEAR = 20480
MOUTH = (42.25, 34.0, 43.75, 34.5)
BARS = 34.25                                             # across the mouth, half way in: one level on both sides
MOUTH_CLEAR = 17408
BANK = [(46.0, 36.7), (44.1, 37.25), (42.2, 36.8), (40.0, 37.4)]
BRANCH_FLOOR = RUN + 42112
#: the drowned on their chains, (x, y, tile, repeat across, repeat up): hung by the feet, so turned over they stand
CHAINED = ((41.0, 35.7, 697, 60, 60), (42.5, 36.35, 924, 56, 66), (43.9, 35.4, 688, 56, 56), (45.2, 36.1, 697, 56, 68),
           (44.5, 36.75, 924, 60, 48))
#: --- the slip --------------------------------------------------------------------
SLIP_RING = [(15.25, 56.0), (21.75, 56.0), (21.75, 56.75), (25.0, 56.75), (25.0, 59.0), (24.0, 59.0), (23.0, 58.0), (21.0, 57.0), (15.25, 57.0)]
RAMP_RECT = (21.75, 56.0, 25.0, 56.75)
RAMP_FOOT = SEA - 1024
BED_Z = SEA + 58368
KEEL, BILGE, SCOUR = SEA + 26624, SEA + 8192, BED_Z + 4096
KEEL_FLAT = [(15.25, 58.0), (23.0, 58.0), (24.0, 59.0), (23.0, 60.0), (15.25, 60.0)]
PORT = [(15.25, 57.0), (21.0, 57.0), (23.0, 58.0), (15.25, 58.0)]
STARBOARD = [(15.25, 60.0), (23.0, 60.0), (21.0, 61.0), (15.25, 61.0)]
BOAT = [(17.4, 59.0), (17.9, 58.5), (19.9, 58.45), (21.0, 59.0), (19.9, 59.55), (17.9, 59.5)]
BOAT_IN = [(17.65, 59.0), (18.0, 58.65), (19.85, 58.6), (20.65, 59.0), (19.85, 59.4), (18.0, 59.35)]
GUNWALE, BILGES = SCOUR - 8192, SCOUR - 2048
BOX = [(18.35, 58.8), (19.35, 58.8), (19.35, 59.2), (18.35, 59.2)]
BOX_LOST = [(21.4, 59.35), (22.2, 59.75), (22.0, 60.1 - 0.15), (21.25, 59.65)]
BOX_TALL = 7168


def _q(v: float) -> int:
    return round(v * PU)


def _ring(points) -> list:
    return [(_q(x), _q(y)) for x, y in points]


def _rect(x0, y0, x1, y1) -> list:
    return _ring(((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def _low(ring) -> list:
    """A ring of the sheet's own units, moved to where the water is kept."""
    return [(x + _q(OFFSET[0]), y + _q(OFFSET[1])) for x, y in ring]


def low(x: float, y: float) -> tuple[float, float]:
    return x + OFFSET[0], y + OFFSET[1]


def _edge(ring, *, x=None, y=None):
    """The longest edge of a ring that lies on a line."""
    on = [(a, b) for a, b in zip(ring, ring[1:] + ring[:1])
          if (x is not None and a[0] == b[0] == x) or (y is not None and a[1] == b[1] == y)]
    return max(on, key=lambda e: abs(e[0][0] - e[1][0]) + abs(e[0][1] - e[1][1]))


#: the campaign's underwater floors are a median 26 and its ceilings 30 (quartiles 16 to 35): drawn as first
#: written, at the dark end of that, the sump and the junction's well were black in their frames
LIFT = 8


def _drowned(floor, ceiling, under, over, wall, shade=(34, 30, 34), **more) -> dict:
    """A sector full of water: E3M3's (shades 28 to 40), its shimmer, nobody's light but what its place has."""
    behavior = {"underwater": 1, **more.pop("sector_behavior", {})}
    return dict(floor_z=floor, ceiling_z=ceiling, floor_picnum=under, ceiling_picnum=over, wall_picnum=wall,
                floor_shade=shade[0] - LIFT, ceiling_shade=shade[1] - LIFT, wall_shade=shade[2] - LIFT, layer=LAYER, role="detail",
                declared_zero_exit=True, intent={"kind": "furnished"}, sector_behavior=behavior, **more)


#: E3M3's surface: a faint wave of light over water, floor and walls (sector 63, and 34 over it)
SHIMMER = {"amplitude": -4, "shade_frequency": 4, "shade_wave": 7, "shade_always": 1, "shade_floor": 1,
           "shade_ceiling": 1, "shade_walls": 1}


def _join(layout, name, left, right, a, b, **more) -> None:
    layout.add_connection(f"connection:drowned:{name}", left, right, a1=a, a2=b, **{"min_width": 1, "min_opening": 0, **more})


def _drop_connections(layout, *between) -> None:
    for key in [k for k, c in layout.connections.items() if {c.region_a, c.region_b} == set(between)]:
        del layout.connections[key]


# ---- the surfaces --------------------------------------------------------------

def _pool(layout, name: str, host: str, rect, *, tile=SEWAGE) -> str:
    """A kerbed pool cut into a room's floor: its water's level is the sewers', a step under the floor."""
    base = host.rsplit("/", 1)[0] + f"/well_{name}"
    outer = _rect(rect[0] - KERB_WIDE, rect[1] - KERB_WIDE, rect[2] + KERB_WIDE, rect[3] + KERB_WIDE)
    inner = _rect(*rect)
    room = layout.regions[host]
    layout.carve_hole(host, outer)
    common = dict(ceiling_z=room.ceiling_z, ceiling_picnum=room.ceiling_picnum, layer=room.layer, declared_zero_exit=True,
                  role="detail", intent={"kind": "furnished"})
    kerb = layout.add_region(f"{base}_kerb", outer, holes=[inner[::-1]], floor_z=room.floor_z - KERB, floor_picnum=PIPE,
                             wall_picnum=RIM, floor_shade=28, wall_shade=24, **common)
    pool = layout.add_region(base, inner, floor_z=RUN, floor_picnum=tile, wall_picnum=BRICK, floor_shade=34, wall_shade=26,
                             sector_behavior=dict(SHIMMER), **common)
    for ring, inside, outside, kind in ((outer, kerb, host, "kerb"), (inner, pool, kerb, "water")):
        for k, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
            _join(layout, f"{name}_{kind}_{k}", inside, outside, a, b)
    return pool


# ---- the sump ------------------------------------------------------------------

def _sump(layout) -> dict[str, str]:
    tank = layout.regions[TANK]
    drum = _low(list(tank.outer))
    # its north wall lies on the drum's own two corners, east and west: a wall that crossed the drum's between two
    # corners would move the crossing to a whole unit, and the drum would no longer be the basin's outline
    east = max(drum)
    corner = max(p[1] for p in drum if abs(p[0] - east[0]) <= 1)
    top = min(y for _x, y in GALLERY)
    gallery = [(x, corner if py == top else y) for (_px, py), (x, y) in zip(GALLERY, _low(_ring(GALLERY)))]
    place = A.Arrangement()
    place.add("gallery", gallery)
    place.add("drum", drum)
    place.add("throat", _low(_rect(*THROAT)))
    place.add("reveal", _low(_rect(THROAT[2], THROAT[1], REVEAL, THROAT[3])))
    y0, y1 = GALLERY[4][1], WELL[1]
    for k, part in enumerate(("west", "middle", "east")):
        place.add(f"pipe_{part}", _low(_rect(CULVERT[k], y0, CULVERT[k + 1], y1)))
    place.add("well", _low(_rect(*WELL)))
    for x, y in MAINS:
        place.solid(_low(A.circle((_q(x), _q(y)), _q(MAIN_R), 6, 1 / 12)))
    cells = place.resolve()
    by_name = {c.name: c for c in cells}

    def surface(name):
        if name == "drum":
            return _drowned(SUMP_PIT, SUMP_TOP, SILT, SEWAGE, PLATE, (38, 30, 34), sector_behavior=dict(SHIMMER))
        if name == "well":
            return _drowned(SUMP_FLOOR, RUN, SILT, SEWAGE, BRICK, (32, 26, 30), sector_behavior=dict(SHIMMER))
        if name == "reveal":
            return _drowned(THROAT_FLOOR, THROAT_TOP, PIPE, PIPE, PIPE, (20, 24, 20))
        if name == "throat":
            # the pumps' beat: the wheel's light comes and goes, as E3M3's generator's does
            return _drowned(THROAT_FLOOR, THROAT_TOP, PIPE, PIPE, PIPE, (6, 10, 8), sector_behavior={
                "shade_wave": 5, "amplitude": 18, "shade_frequency": 9, "shade_always": 1, "shade_floor": 1,
                "shade_ceiling": 1, "shade_walls": 1})
        if name.startswith("pipe"):
            more = {}
            if name != "pipe_middle":
                hinge = _edge(by_name[name].outer, x=_low(_rect(CULVERT[1 if name == "pipe_west" else 2], 0, 0, 0))[0][0])
                more = {"floor_slope": SlopeSpec(hinge=hinge, rise_z=-PIPE_ROUND),
                        "ceiling_slope": SlopeSpec(hinge=hinge, rise_z=PIPE_ROUND)}
            return _drowned(PIPE_FLOOR, PIPE_TOP, PIPE, PIPE, PIPE, (38, 38, 36), **more)
        return _drowned(SUMP_FLOOR, GALLERY_TOP, SILT, VAULT, BRICK, (34, 38, 32))

    def face(seen, beyond, a, b):
        if seen == "gallery" and beyond is None and math.dist(a, b) < 0.4 * PU:
            return {"picnum": MAIN, "x_repeat": 4, "y_repeat": 8}                # the mains' sides: one tile of twin pipes each
        if {seen, beyond} == {"reveal", "throat"}:
            return {"picnum": PIPE, "over_picnum": SCREEN, "cstat": 1 | 16 | 64 | 4,
                    "x_repeat": 16, "y_repeat": 12, "y_panning": 0}
        if seen == "gallery" and beyond is None and a[0] == b[0] == _low([(_q(REVEAL), 0)])[0][0]:
            return {"shade": 18}                                                 # either side of the screen, in the wheel's light
        if seen == "gallery" and beyond == "drum" or seen == "drum" and beyond:
            return {"picnum": PLATE}
        return {}

    regions = A.lay(layout, f"{KEY}/sump", cells, surface, face)
    _link(layout, "sump", TANK, regions["drum"], SEWAGE)
    pool = _pool(layout, "junction", JUNCTION, WELL)
    _link(layout, "junction", pool, regions["well"], SEWAGE)
    return regions


# ---- the flooded branch ----------------------------------------------------------

def _branch(layout) -> dict[str, str]:
    room = layout.regions[BRANCH]
    (x0, y0), (x1, y1) = map(min, zip(*room.outer)), map(max, zip(*room.outer))
    x0, x1 = min(p[0] for p in room.outer), max(p[0] for p in room.outer)
    y0, y1 = min(p[1] for p in room.outer), max(p[1] for p in room.outer)
    edge = _ring(BANK)
    _drop_connections(layout, BRANCH, WALK)
    mouth_y = _q(MOUTH[3])
    water = [(x0, mouth_y), (_q(MOUTH[0]), mouth_y), (_q(MOUTH[2]), mouth_y), (x1, mouth_y), *edge]
    # what was the whole branch is the bank at its back, dry: the secret is stepping onto it (a link tells no sector
    # that it was entered, actor.cpp:4555 before :4644)
    room.outer = tuple([*edge[::-1], (x1, y1), (x0, y1)])
    room.floor_z = SEWER
    room.floor_picnum = EARTH
    for key in ("depth",):
        room.sector_behavior.pop(key, None)
    style = dict(ceiling_z=room.ceiling_z, ceiling_picnum=room.ceiling_picnum, wall_picnum=room.wall_picnum, layer=room.layer,
                 declared_zero_exit=True, intent={"kind": "furnished"})
    pool = layout.add_region(f"{BRANCH}_water", water, floor_z=RUN, floor_picnum=SEWAGE, role="interior", floor_shade=34,
                             wall_shade=30, ceiling_shade=32, sector_behavior=dict(SHIMMER), **style)
    parts = {}
    for name, south, north in (("mouth", BARS, MOUTH[1]), ("sill", MOUTH[3], BARS)):
        parts[name] = layout.add_region(
            f"{BRANCH}_{name}", _rect(MOUTH[0], north, MOUTH[2], south), floor_z=SEWER, floor_picnum=STONE, role="gateway",
            floor_shade=36, wall_shade=28, ceiling_shade=34,
            **{**style, "ceiling_z": SEWER - MOUTH_CLEAR, "ceiling_picnum": PIPE, "wall_picnum": PIPE})
    across = [(left, right, (_q(MOUTH[0]), _q(y)), (_q(MOUTH[2]), _q(y))) for left, right, y in (
        (parts["mouth"], WALK, MOUTH[1]), (parts["mouth"], parts["sill"], BARS), (parts["sill"], pool, MOUTH[3]))]
    for k, (left, right, a, b) in enumerate(across):
        _join(layout, f"branch_mouth_{k}", left, right, a, b)
    for k, (a, b) in enumerate(zip(edge, edge[1:])):
        _join(layout, f"branch_bank_{k}", pool, BRANCH, a, b)
    bars = {"over_picnum": LATTICE, "cstat": 1 | 16 | 64, "x_repeat": 16, "y_repeat": 8}
    for seen in parts.values():
        layout.paint_wall(seen, *across[1][2:], fixed_frame=True, picnum=PIPE, **bars)

    place = A.Arrangement()
    place.add("tank", _low(_rect(*TANK_POOL)))
    place.add("crawl", _low(_ring(CRAWL)))
    place.add("hall", _low(water))
    cells = place.resolve()

    def surface(name):
        if name == "tank":
            return _drowned(TANK_FLOOR, RUN, SILT, SEWAGE, BRICK, (32, 26, 30), sector_behavior=dict(SHIMMER))
        if name == "hall":
            return _drowned(BRANCH_FLOOR, RUN, SILT, SEWAGE, BRICK, (36, 28, 34), sector_behavior=dict(SHIMMER))
        return _drowned(TANK_FLOOR, TANK_FLOOR - CRAWL_CLEAR, EARTH, VAULT, RUBBLE, (40, 40, 38))

    def face(seen, beyond, a, b):
        return {"picnum": RUBBLE} if beyond == "crawl" else {}

    regions = A.lay(layout, f"{KEY}/branch", cells, surface, face)
    tank = _pool(layout, "cistern", CISTERN, TANK_POOL)
    _link(layout, "cistern", tank, regions["tank"], SEWAGE)
    _link(layout, "branch", pool, regions["hall"], SEWAGE)
    return regions


# ---- the slip -------------------------------------------------------------------

def _slip(layout) -> dict[str, str]:
    """Cut the slip and its ramp out of the near sea, and give each of its edges back to whoever it was joined to."""
    from shapely.geometry import LineString, Polygon
    import l3_market
    river = layout.regions[RIVER]
    pool_ring, ramp_ring = _ring(SLIP_RING), _rect(*RAMP_RECT)
    rest = Polygon(river.outer, river.holes).difference(Polygon(pool_ring).union(Polygon(ramp_ring)))
    if rest.geom_type != "Polygon" or rest.interiors:
        raise ValueError(f"the slip cuts the near sea in pieces: {rest.geom_type}")
    ring = [(round(x), round(y)) for x, y in rest.exterior.coords][:-1]
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1])) < 0:
        ring.reverse()
    river.outer = tuple(ring)
    sky = dict(ceiling_z=river.ceiling_z, ceiling_picnum=river.ceiling_picnum, parallax_ceiling=True, layer=river.layer,
               declared_zero_exit=True, intent={"kind": "furnished"})
    layout.add_region(SLIP, pool_ring, floor_z=river.floor_z, floor_picnum=SEA_TILE, wall_picnum=l3_market.BULKHEAD, role="exterior",
                      floor_shade=river.floor_shade, sector_behavior=dict(l3_market.SEA_PAN), **sky)
    x1, y0 = _q(RAMP_RECT[2]), _q(RAMP_RECT[1])
    layout.add_region(RAMP, ramp_ring, floor_z=GRADE, floor_picnum=l3_market.BOARDWALK, wall_picnum=PILE, role="exterior",
                      floor_shade=28, floor_slope=SlopeSpec(hinge=((x1, y0), (x1, _q(RAMP_RECT[3]))), rise_z=RAMP_FOOT - GRADE),
                      relative_alignment="floor", **sky)
    l3_market.SHIP_FACES[RAMP] = PILE
    parts = {RIVER: Polygon(ring), SLIP: Polygon(pool_ring), RAMP: Polygon(ramp_ring)}
    old = [c for c in layout.connections.values() if RIVER in (c.region_a, c.region_b)]
    for c in old:
        line = LineString([c.a1, c.a2])
        other = c.region_b if c.region_a == RIVER else c.region_a
        pieces = [(part, line.intersection(shape.exterior)) for part, shape in parts.items()]
        pieces = [(part, g) for part, g in pieces if g.length > 8]
        if len(pieces) == 1 and pieces[0][0] == RIVER:
            continue
        del layout.connections[c.connection_id]
        for part, g in pieces:
            for k, run in enumerate(_runs(g)):
                _join(layout, f"slip:{c.connection_id.rsplit(':', 1)[-1]}:{part.rsplit('/', 1)[-1]}:{k}", other, part, *run)
    for k, (a, b) in enumerate(zip(pool_ring, pool_ring[1:] + pool_ring[:1])):
        for part in (RAMP, RIVER):
            shared = LineString([a, b]).intersection(parts[part].exterior)
            if shared.length > 8:
                _join(layout, f"slip_{part.rsplit('/', 1)[-1]}_{k}", SLIP, part, a, b)
    # the boom: nobody swims out to the sea that has no bottom
    a, b = (_q(25.0), _q(59.0)), (_q(24.0), _q(59.0))
    for seen in (SLIP, RIVER):
        layout.paint_wall(seen, a, b, cstat=1)

    place = A.Arrangement()
    place.add("bed", _low(pool_ring))
    for name, points in (("keel", KEEL_FLAT), ("port", PORT), ("starboard", STARBOARD), ("boat", BOAT), ("bilge", BOAT_IN),
                         ("box", BOX), ("lost", BOX_LOST)):
        place.add(name, _low(_ring(points)))
    cells = place.resolve()
    by_name = {c.name: c for c in cells}

    def surface(name):
        if name == "bed":
            return _drowned(BED_Z, SEA, BED, SEA_TILE, QUAYSIDE, (26, 34, 28), sector_behavior={
                "pan_ceiling": 1, "pan_always": 1, "pan_velocity": 10, "pan_angle": 900})
        if name in ("port", "starboard"):
            hinge = _edge(by_name[name].outer, y=_q(58.0 if name == "port" else 60.0))
            return _drowned(SCOUR, KEEL, BED, HULL, ROCK, (38, 34, 46),
                            ceiling_slope=SlopeSpec(hinge=hinge, rise_z=BILGE - KEEL))
        floor, tile, wall, shade = {"keel": (SCOUR, BED, ROCK, (40, 36, 46)), "boat": (GUNWALE, PLANK, HULL, (26, 36, 22)),
                                    "bilge": (BILGES, 21, HULL, (32, 36, 26)), "box": (BILGES - BOX_TALL, EARTH, 178, (14, 36, 16)),
                                    "lost": (SCOUR - BOX_TALL + 2048, 178, 178, (30, 36, 26))}[name]
        return _drowned(floor, KEEL, tile, HULL, wall, shade)

    def face(seen, beyond, a, b):
        if beyond == "boat" or seen == "boat":
            return {"picnum": HULL}
        if beyond in ("box", "lost"):
            return {"picnum": 178}
        if seen == "bed" and beyond in ("keel", "port", "starboard"):
            return {"picnum": HULL, "shade": 22}                             # her side, in what light there is
        return {}

    regions = A.lay(layout, f"{KEY}/slip", cells, surface, face)
    _link(layout, "slip", SLIP, regions["bed"], SEA_TILE)
    return regions


def _runs(geometry) -> list:
    """A line or lines as ((x, y), (x, y)) pairs of whole units, each as long as it goes."""
    from shapely.ops import linemerge
    if geometry.geom_type == "LineString":
        lines = [geometry]
    else:
        merged = linemerge([g for g in geometry.geoms if g.geom_type == "LineString"])
        lines = getattr(merged, "geoms", [merged])
    return [tuple((round(x), round(y)) for x, y in (line.coords[0], line.coords[-1])) for line in lines]


def _link(layout, name: str, upper: str, under: str, tile: int) -> None:
    water_link(layout, f"drowned:{name}", upper, under, link_id=LINKS[name],
               offset=(_q(OFFSET[0]), _q(OFFSET[1])), tile=tile)


# ---- building and dressing -------------------------------------------------------

ROOMS: dict[str, dict[str, str]] = {}


def build(layout) -> dict:
    """Lay all three, after the program has become a layout: they are cut into rooms that other modules made."""
    layout.declare_layer(LAYER, ceiling_z=SUMP_TOP, floor_z=SUMP_PIT + 2048,
                         note="what is full of water, kept beside the city: the sump, the flooded branch, the slip")
    ROOMS.clear()
    ROOMS.update(sump=_sump(layout), branch=_branch(layout), slip=_slip(layout))
    _dress(layout)
    return {name: len(rooms) for name, rooms in ROOMS.items()}


def _put(layout, name, region, x, y, tile, repeats, *, cstat=128, up=0, z=None, **fields) -> str:
    import wallplane
    from bloodmap.placement import drawn_extent
    room = layout.regions[region]
    width_repeat, tall = repeats
    _w, height, _x, offset = wallplane.art()[tile]
    _top, bottom = drawn_extent(height, offset, tall, cstat)
    if z is None:
        z = room.floor_z - 16 if cstat & 32 else room.floor_z - 8 - bottom - up
    return layout.add_sprite(f"drowned:{name}", region, x=_q(x), y=_q(y), z=round(z), picnum=tile, x_repeat=width_repeat,
                             y_repeat=tall, cstat=cstat, **{"shade": 8, **fields})


#: a bubbling weed (E1M4 sprite 339: the weed is the generator): busy time, how many
BUBBLES = {"state": 1, "busy_time": 50, "data_1": 10}


def _dress(layout) -> None:
    import ambience
    sump, branch, slip = ROOMS["sump"], ROOMS["branch"], ROOMS["slip"]

    def put(name, region, x, y, *rest, **fields):
        return _put(layout, name, region, *low(x, y), *rest, **fields)

    def weed(name, region, x, y, tile=660, size=64, bubbles=False, shade=8, **fields):
        more = {"type": 706, "behavior": dict(BUBBLES)} if bubbles else {}
        return put(name, region, x, y, tile, (size, size), shade=shade, **more, **fields)

    def sound(name, region, x, y, context, under=True):
        (put if under else lambda *a, **k: _put(layout, *a, **k))
        px, py = low(x, y) if under else (x, y)
        room = layout.regions[region]
        fields = ambience.fields(context)
        layout.add_sprite(f"drowned:sound_{name}", region, x=_q(px), y=_q(py), z=room.floor_z - 8192, **fields)

    # the sump: what the pumps drew in lies against the screen, in the wheel's light
    tx, ty = REVEAL, (THROAT[1] + THROAT[3]) / 2
    put("sump_light", sump["throat"], THROAT[0] + 0.6, ty, 795, (40, 40), cstat=32 | 128 | 8,
        z=layout.regions[sump["throat"]].ceiling_z + 64, shade=-16)
    # (483 is a mask: it hangs, it is no wall's own tile)
    put("sump_wheel", sump["throat"], THROAT[0] + 0.02, ty, WHEEL, (44, 42), cstat=16 | 128, angle=0, shade=-16,
        z=(THROAT_TOP + THROAT_FLOOR) // 2)
    put("drawn_body", sump["gallery"], tx + 0.22, ty - 0.2, 2333, (48, 48), shade=2)
    put("drawn_body_2", sump["gallery"], tx + 0.62, ty + 0.52, 2333, (44, 44), shade=12, cstat=128 | 4)
    put("drawn_barrel", sump["gallery"], tx + 0.3, ty + 0.5, 925, (56, 56), shade=4)
    put("drawn_barrel_2", sump["gallery"], tx + 0.25, ty - 0.68, 925, (48, 48), shade=8)
    for k, (dy, size) in enumerate(((-0.42, 60), (0.15, 72), (0.6, 56))):
        weed(f"drawn_weed_{k}", sump["gallery"], tx + 0.08, ty + dy, 664, size, bubbles=k == 1, shade=6)
    weed("sump_weed_0", sump["drum"], 42.6, 4.5, 668, 64)
    weed("sump_weed_1", sump["gallery"], 44.0, 6.5, 660, 56)
    weed("well_weed", sump["well"], 43.1, 12.5, 660, 56, bubbles=True)
    sound("sump", sump["gallery"], 42.4, 7.2, "drowned")
    sound("sump_wheel", sump["throat"], THROAT[0] + 0.4, ty, "wheel")
    sound("junction", f"{JUNCTION.rsplit('/', 1)[0]}/well_junction", 42.7, 12.0, "lapping", under=False)

    # the branch: the drowned, weighted, standing up out of the silt on their chains
    for k, (x, y, tile, wide, tall) in enumerate(CHAINED):
        put(f"chained_{k}", branch["hall"], x, y, tile, (wide, tall), cstat=128 | 8, shade=2 * k - 4)
    weed("hall_weed_0", branch["hall"], 40.6, 36.6, 664, 60)
    weed("hall_weed_1", branch["hall"], 45.6, 35.1, 660, 64, bubbles=True)
    weed("tank_weed", branch["tank"], 44.6, 28.4, 660, 60)
    weed("tank_bubbles", branch["tank"], 43.75, 30.1, 668, 56)
    weed("crawl_bubbles", branch["crawl"], 43.8, 33.0, 668, 44)
    sound("hall", branch["hall"], 43.0, 35.8, "drowned")
    sound("tank", branch["tank"], 44.0, 29.2, "drowned")
    sound("cistern", f"{CISTERN.rsplit('/', 1)[0]}/well_cistern", 44.1, 29.2, "lapping", under=False)
    sound("branch", f"{BRANCH}_water", 43.0, 35.8, "lapping", under=False)

    # the slip: one lit thing on the bed of the harbour, the lantern that went down with the boat
    put("boat_lantern", slip["bilge"], 20.2, 59.0, 693, (44, 44), shade=-128)
    for k, (x, y, tile, size, bubbles) in enumerate(((16.6, 56.4, 664, 72, False), (19.0, 56.7, 660, 64, True),
                                                     (22.6, 57.35, 664, 64, False), (24.4, 57.2, 660, 72, False),
                                                     (24.1, 58.5, 664, 56, False))):
        weed(f"bed_weed_{k}", slip["bed"], x, y, tile, size, bubbles)
    weed("keel_weed_0", slip["port"], 17.0, 57.5, 660, 64)
    weed("keel_weed_1", slip["starboard"], 21.4, 60.5, 660, 56)
    weed("boat_bubbles", slip["bilge"], 18.1, 59.25, 668, 48)
    sound("bed", slip["bed"], 23.0, 57.4, "drowned")
    sound("keel", slip["keel"], 16.4, 59.3, "drowned")
    sound("slip", SLIP, 20.0, 56.5, "lapping", under=False)
    # the net that closes the slip, from the bow to the jetty (112, the ship's own rope net)
    width, height = 64, 64
    layout.add_sprite("drowned:boom", SLIP, x=_q(24.5), y=_q(59.0) - 4, z=SEA - 8192, picnum=112, cstat=16 | 128, angle=1536,
                      x_repeat=64, y_repeat=32, shade=14, spans_opening=True)


def finish(level, compiled) -> dict:
    """What a region cannot say: the sea's palette on both sides of the slip, and water that is not seen far through."""
    def f(item):
        return item.get("fields", item) if isinstance(item, dict) else item.fields

    def sector(region):
        return f(level.sectors[compiled.allocations[region].sector_id])

    for name, rooms in ROOMS.items():
        for region in rooms.values():
            sector(region)["visibility"] = 16                                # E6M4's 25
    top, bed = sector(SLIP), sector(ROOMS["slip"]["bed"])
    top["floor_pal"] = bed["ceiling_pal"] = SEA_PAL
    top["floor_stat"] = int(top["floor_stat"]) | 4
    bed["ceiling_stat"] = int(bed["ceiling_stat"]) | 4
    return {name: len(rooms) for name, rooms in ROOMS.items()}
