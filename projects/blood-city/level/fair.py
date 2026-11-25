"""Jo-Jo's fair on the market square: a carousel at the avenue's foot and four stalls, and nobody sees the quay past them.

The owner, 2026-11-25: "right now you just get attacked by a lot of enemies around you
immediatelly ... we can like add some objects or something like near the player start,
sonething meaningful that would like cover the view of the enemies ... Maybe we can add
more stands, a differend ones or a circus with carousel ... Stands should probably be partly
made of sectors combined with flat sprites." The town's bills have named the show since the
first of them was pasted up ("JO-JO, the idiot circus boy"); this is where it stopped.

What hides what (`first_sight.py` measures it; ten of them saw the start): the carousel's
drum the avenue, from its foot to the station; the gallery's back the square's west end; the
toffee stall's back the quay to the east; the ticket booth the corner by the churchyard. A
sprite stops no line, so every back is a sector: boards two bodies tall.

A stall is one hole in the street with a U of boards in it, a counter across the mouth and a
shelf along the back; its roof, its valance and what it sells are sprites, as the market's two
stalls have them (`meat_market`, after DWE3M10). Nothing over it but sky: the roof is flat
sprites, so the street's own sky is seen past it.

The carousel is three sectors that turn as one: a platform of sixteen sides, the drum on it,
the neck on that (type 617, one axis, one time, so a point they share is put at the same place
on every tick: `mechanism.rigid_body` says why), and every sprite in them is carried (cstat
8192). E1M4's nine sectors (321 to 329) are driven so: on at the level's start, `retrigger` at
both ends, and no time at all for the way back, which is a whole turn and so is not seen.
The host is a ring of the street's own (`APRON`), and a circle turns in its own hole. What stands on it is iron: hounds
and rats in grey (palette 5), so that nothing alive is taken for them.
"""

from __future__ import annotations

import math

from bloodmap import arrangement as A, motion, wiring

PU = 1024
KEY = "region:gravesend/market_slip/fair"
GRADE, SKY_Z, SKY = 8192, -188416, 3491
BODY = 16960
#: the carousel: its middle, the platform's, the drum's and the neck's radii, and how far over the street each stands
AT, RADIUS, DRUM_R, NECK_R = (35.6, 46.4), 2.6, 1.55, 0.6
STEP, DRUM, ROOF = 2560, 27648, 42496
#: a ring of the street that stays, round the one that turns: what a mover stands in is not cut up by light and shadow, and the square must be
APRON = 0.22
SIDES, TURN, TENTHS = 16, 2048, 200                              # one turn in twenty seconds
CARRIED = 8192
#: the clown on the drum: one whole face to a side (128 by 156 texels), its crown at the drum's top
FACE = {"x_repeat": 16, "y_repeat": 13, "x_panning": 0, "y_panning": 0}
CLOWN, STRIPE, BULBS, PLATES, POLE = 1096, 1004, 77, 438, 213
HOUND, RAT, GREY, COLD = 1270, 1745, 5, 10
#: the calliope: "Happy Alarm Clock Song", twelve and a half seconds of it, heard all over the square
TUNE, NEAR, FAR, LOUD = 65, 80, 420, 45
BOARDS, TOP_WOOD, COUNTER, FLOOR, DRAPE = 170, 34, 84, 28, 1004
BACK, COUNTER_UP, SHELF_UP, CANOPY = 34560, 8192, 12288, 35328
THICK, DEEP, SHELF = 0.16, 0.42, 0.34
#: name -> (x0, y0, x1, y1), which way it faces, its boards outside, what is written over it, the shelf's things, the counter's
STALLS = {
    "gallery": ((27.2, 49.9, 29.7, 52.7), "east", STRIPE, "SHOOTING", (), ()),
    "toffee": ((41.2, 50.7, 43.4, 53.1), "west", STRIPE, "TOFFEE", (834, 802, 834, 802, 834), (604, 616, 604)),
    "tickets": ((31.0, 42.9, 32.5, 44.4), "south", STRIPE, "", (), ()),
    "fortunes": ((20.6, 50.2, 23.4, 52.7), "south", DRAPE, "FORTUNES", (), (760,)),
}
#: the shooting gallery is E1M4's (its sectors 26 to 43): tiers one over another, and let into each of them slabs no bigger than a hand
#: that slide from end to end for ever (616, `retrigger` at both ends), a rubber duck (852) or a smiling face (853) standing on each;
#: bullseyes (967, its sprite 999) on the boards behind. Faces and bullseyes are counted (a combination switch, 22), and the last rings a
#: bell (270) and brings the prize up through a well in the counter (its sectors 64 and 174). (The owner, of the figures first stood
#: there: "That dummy used in shootings isn't game asset that is normally used, look at how shooting is done in E1M4 ... You can even
#: have the moving targets smiley faces and ducks ... and you have bullseye sprites as well".)
TIER, TIERS = 0.3, (22528, 17408, 12288)                         # the back one first
DUCK, SMILE, BULLSEYE = 852, 853, 967
TARGETS = {DUCK: (40, {"data_1": 8, "data_4": 2203}), SMILE: (64, {"data_1": 1, "data_4": 301}), BULLSEYE: (44, {"data_1": 5, "data_4": 312})}
#: each slab: (tier, what stands on it, how far off the tier's middle line, tenths of a second there and back, which end it starts at)
SLABS = ((0, SMILE, -80, 26, 30, 0), (0, DUCK, 80, 34, 34, 1), (1, SMILE, 80, 22, 22, 1), (1, DUCK, -80, 30, 26, 0),
         (2, SMILE, -80, 30, 36, 1), (2, DUCK, 80, 24, 28, 0))
SLAB, ENDS = 64, 150
PRIZE, PRIZE_PICTURE, BELL, WELL, WELL_WIDE = 68, (812, 48), 270, 7168, 0.62
#: what is pasted on a stall's outside: (stall, side, how far along it, tile, repeat, bodies up)
BILLS = (("gallery", "south", 0.5, 981, 40, 1.15), ("gallery", "west", 0.28, 440, 44, 1.1), ("gallery", "west", 0.72, 335, 36, 1.2),
         ("gallery", "north", 0.5, 335, 36, 1.15), ("toffee", "east", 0.5, 981, 40, 1.15), ("toffee", "south", 0.5, 440, 44, 1.1),
         ("tickets", "west", 0.5, 440, 40, 1.1), ("tickets", "east", 0.5, 981, 32, 1.2), ("tickets", "north", 0.5, 335, 32, 1.15),
         ("fortunes", "west", 0.5, 440, 44, 1.1), ("fortunes", "north", 0.5, 981, 44, 1.15))
#: balloons: the plan's point, the palette
BALLOONS = ((30.0, 49.8, 2), (30.05, 52.8, 10), (40.9, 50.8, 10), (40.9, 53.0, 2), (30.8, 44.6, 2), (32.7, 44.65, 10), (20.4, 52.9, 2))
#: the run of cobbles where the carousel stands: `streets.lay` leaves it out
NO_ROAD = ("the_avenue_south", "market_slip")
_PAINTED: list[tuple[str, tuple, tuple, dict]] = []
_REGIONS: dict[str, dict[str, str]] = {}
_HOST: dict[str, str] = {}


def _q(v: float) -> int:
    return round(v * PU)


def _rect(x0, y0, x1, y1):
    return [(_q(x0), _q(y0)), (_q(x1), _q(y0)), (_q(x1), _q(y1)), (_q(x0), _q(y1))]


def _facing(side: str):
    """Out of a stall's front, as the engine turns: (dx, dy), and the angle a sprite there faces."""
    return {"east": ((1, 0), 0), "south": ((0, 1), 512), "west": ((-1, 0), 1024), "north": ((0, -1), 1536)}[side]


def _street(layout, x: float, y: float):
    from shapely import Point, Polygon
    return next(r for r in layout.regions.values() if r.parallax_ceiling and r.floor_z == GRADE and r.role != "detail"
                and Polygon(r.outer, r.holes).contains(Point(_q(x), _q(y))))


def _strip(rect, side: str, deep: float, off: float = 0.0, inset: float = 0.0):
    """A strip of a rectangle along one side of it."""
    x0, y0, x1, y1 = rect
    return {"east": _rect(x1 - off - deep, y0 + inset, x1 - off, y1 - inset), "west": _rect(x0 + off, y0 + inset, x0 + off + deep, y1 - inset),
            "south": _rect(x0 + inset, y1 - off - deep, x1 - inset, y1 - off),
            "north": _rect(x0 + inset, y0 + off, x1 - inset, y0 + off + deep)}[side]


OPPOSITE = {"east": "west", "west": "east", "north": "south", "south": "north"}
BESIDE = {"east": ("north", "south"), "west": ("north", "south"), "north": ("west", "east"), "south": ("west", "east")}


def _lay(layout, name, cells, heights, floors, walls, host, extra=None):
    """Cells in one hole of the street: their regions, their joins, what their walls wear."""
    def surface(cell):
        return dict(floor_z=GRADE - heights[cell], ceiling_z=SKY_Z, floor_picnum=floors[cell], wall_picnum=walls(cell, None),
                    ceiling_picnum=SKY, parallax_ceiling=True, layer="street", floor_shade=14, wall_shade=14, ceiling_shade=0,
                    role="detail", declared_zero_exit=True, intent={"kind": "furnished"}, **((extra or {}).get(cell) or {}))

    def face(seen, beyond, a, b):
        paint = {"picnum": walls(beyond, seen)} if beyond is not None and heights[beyond] > heights[seen] else {}
        if paint:
            if paint["picnum"] == CLOWN:
                paint.update(FACE)
            _PAINTED.append((f"{KEY}/{name}:{seen}", a, b, paint))
        return paint

    from shapely import Polygon, unary_union
    whole = unary_union([Polygon(c.outer) for c in cells])
    layout.carve_hole(host.region_id, [(int(x), int(y)) for x, y in list(whole.exterior.coords)[:-1]])
    regions = A.lay(layout, f"{KEY}/{name}", cells, surface, face)
    for cell, a, b in A.rim(cells):
        layout.add_connection(f"connection:fair_{name}:{a[0]}:{a[1]}", host.region_id, regions[cell], a1=b, a2=a, min_width=1, min_opening=0)
        paint = {"picnum": walls(cell, "street")}
        layout.paint_wall(host.region_id, b, a, **paint)
        _PAINTED.append((host.region_id, b, a, paint))
    _REGIONS[name], _HOST[name] = regions, host.region_id
    return regions


def build(layout) -> dict:
    """The holes, the boards and the carousel's three sectors."""
    _PAINTED.clear()
    _REGIONS.clear()
    _HOST.clear()
    for name, (rect, side, outside, *_rest) in STALLS.items():
        place = A.Arrangement()
        place.add("inside", _rect(*rect))
        for k, end in enumerate(BESIDE[side]):
            place.add(f"end_{k}", _strip(rect, end, THICK))
        place.add("back", _strip(rect, OPPOSITE[side], THICK))
        extra = None
        if name == "gallery":
            extra = _ranges(place, rect)
        else:
            place.add("shelf", _strip(rect, OPPOSITE[side], SHELF, THICK, THICK))
        place.add("counter", _strip(rect, side, DEEP, 0.0, THICK))
        if name == "gallery":
            middle = (rect[1] + rect[3]) / 2
            place.add("well", _rect(rect[2] - DEEP + 0.06, middle - WELL_WIDE / 2, rect[2] - 0.06, middle + WELL_WIDE / 2))
        cells = place.resolve()
        rises = {"inside": 0, "end": BACK, "back": BACK, "shelf": SHELF_UP, "counter": COUNTER_UP, "well": -WELL}
        kind = {c.name: c.name.split("_")[0] for c in cells}
        _lay(layout, name, cells, {n: TIERS[int(n.split("_")[1])] if k in ("tier", "target") else rises[k] for n, k in kind.items()},
             {n: FLOOR if k == "inside" else TOP_WOOD for n, k in kind.items()},
             lambda cell, seen, kind=kind, outside=outside: (
                 COUNTER if kind[cell] in ("counter", "shelf", "well", "tier", "target") else outside if seen == "street" else BOARDS),
             _street(layout, (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2), extra)
    centre = (_q(AT[0]), _q(AT[1]))
    street = _street(layout, *AT)
    place = A.Arrangement()
    place.add("apron", A.circle(centre, _q(RADIUS + APRON), SIDES))
    place.add("platform", A.circle(centre, _q(RADIUS), SIDES))
    place.add("drum", A.circle(centre, _q(DRUM_R), 8, 1 / 16))
    place.add("neck", A.circle(centre, _q(NECK_R), 8, 1 / 16))
    behavior = {"busy_time_a": TENTHS, "busy_wave_a": 1, "busy_wave_b": 1, "retrigger_a": 1, "retrigger_b": 1, "drag": 1}
    regions = _lay(layout, "carousel", place.resolve(), {"apron": 0, "platform": STEP, "drum": DRUM, "neck": ROOF},
                   {"apron": street.floor_picnum, "platform": PLATES, "drum": TOP_WOOD, "neck": TOP_WOOD},
                   lambda cell, _seen: {"apron": street.wall_picnum, "platform": COUNTER, "drum": CLOWN, "neck": STRIPE}[cell], street,
                   {cell: {"type": 617, "relative_alignment": "floor", "sector_behavior": dict(behavior)} for cell in ("platform", "drum", "neck")})
    import wires
    started = wires.wire("fair:carousel")
    for cell, region in regions.items():
        if cell == "apron":
            continue
        layout.add_sprite(f"fair:axis_{cell}", regions["neck"], x=centre[0], y=centre[1], z=GRADE - ROOF,
                          type=motion.MARKER_AXIS, picnum=motion.MARKER_PICNUM, status=motion.MARKER_STATNUM, cstat=motion.MARKER_CSTAT,
                          x_repeat=64, y_repeat=64, angle=TURN, marker_owner=region)
        started.then(wiring.region(region))
    return {"stalls": len(STALLS), "turning": len(regions) - 1}


def _slab(rect, row) -> tuple[int, int, int, int]:
    """A slab's line in x, its middle at either end of its run, and which of the two it is drawn at (its ON)."""
    tier, _what, aside, _there, _back, end = row
    x = _q(rect[0] + THICK + TIER * (tier + 0.5)) + aside
    low, high = _q(rect[1] + THICK) + ENDS, _q(rect[3] - THICK) - ENDS
    return (x, low, high, high if end else low)


def _ranges(place, rect) -> dict:
    """The tiers and the slabs in them."""
    for k in range(len(TIERS)):
        x = rect[0] + THICK + TIER * k
        place.add(f"tier_{k}", _rect(x, rect[1] + THICK, x + TIER, rect[3] - THICK))
    extra = {"well": {"type": 600, "sector_behavior": {"busy_time_a": 10, "off_floor_z": GRADE + WELL, "on_floor_z": GRADE - COUNTER_UP,
                                                       "off_ceiling_z": SKY_Z, "on_ceiling_z": SKY_Z, "dude_lockout": 1}}}
    for n, row in enumerate(SLABS):
        x, _low, _high, at = _slab(rect, row)
        half = SLAB // 2
        place.add(f"target_{row[0]}_{n}", [(x - half, at - half), (x + half, at - half), (x + half, at + half), (x - half, at + half)])
        extra[f"target_{row[0]}_{n}"] = {"type": 616, "sector_behavior": {
            "busy_time_a": row[3], "busy_time_b": row[4], "wait_time_a": 2, "wait_time_b": 2, "retrigger_a": 1, "retrigger_b": 1}}
    return extra


def movers() -> frozenset[str]:
    """What rises and is no door: the gallery's well."""
    return frozenset({_REGIONS["gallery"]["well"]})


def _gallery(layout) -> int:
    """What stands on the slabs, the bullseyes, the count, the bell, and what comes up."""
    import wires
    from bloodmap.breakables import THING_STATUS
    from bloodmap.placement import seated_z
    regions = _REGIONS["gallery"]
    rect = STALLS["gallery"][0]
    x0, y0, x1, y1 = rect
    hits, won, started = wires.wire("fair:hits"), wires.wire("fair:prize"), wires.wire("fair:targets")
    counted = 0

    def target(name, region, x, y, z, tile, **fields):
        size, record = TARGETS[tile]
        layout.add_sprite(name, region, x=x, y=y, z=z, picnum=tile, x_repeat=size, y_repeat=size, type=416, status=THING_STATUS,
                          shade=-16, behavior=dict(record), **fields)
        if tile != DUCK:
            hits.when(wiring.placement(name), "destroyed", command=motion.CMD_ON, on=True, off=True, once=True)

    for n, row in enumerate(SLABS):
        tier, what = row[0], row[1]
        x, low, high, at = _slab(rect, row)
        slab, host = regions[f"target_{tier}_{n}"], regions[f"tier_{tier}"]
        motion.place_markers(layout, f"fair:target_{n}", driven_region=slab, off_at=(x, low + high - at), on_at=(x, at), off_region=host,
                             z=GRADE - TIERS[tier])
        layout.declare_motion(slab, [host])
        started.then(wiring.region(slab))
        size = TARGETS[what][0]
        z = seated_z(seat="floor", floor_z=GRADE - TIERS[tier], ceiling_z=SKY_Z, tile_height=_art(what)[1], y_repeat=size,
                     y_offset=_art(what)[3], cstat=128, clearance=0)
        target(f"fair:target_{n}", slab, x, at, z, what, cstat=CARRIED | 385 | (4 if row[5] else 0), angle=0)
        counted += what != DUCK
    for k in range(3):
        target(f"fair:bullseye_{k}", regions["tier_0"], _q(x0 + THICK) + 6, _q(y0 + (y1 - y0) * (k + 0.5 + 0.12 * (1 - k)) / 3),
               GRADE - 29200, BULLSEYE, cstat=16 | 64 | 128 | 256, angle=0)
        counted += 1
    inside = regions["inside"]
    at = (_q(x1 - DEEP - 0.3), _q(y0 + THICK + 0.3))
    tally = layout.add_sprite("fair:count", inside, x=at[0], y=at[1], z=GRADE - 4096, type=22, picnum=0, shade=-128, cstat=32896, status=0,
                              behavior={"data_2": counted})
    hits.then(wiring.placement(tally))
    won.when(wiring.placement(tally), wiring.RELAY, command=motion.CMD_ON, once=True)
    won.then(wiring.region(regions["well"]))
    won.then(wiring.placement(layout.add_sprite("fair:bell", inside, x=at[0] + 96, y=at[1], z=GRADE - 20000, type=708, picnum=2519, shade=-128,
                                                cstat=32896, status=0, behavior={"data_2": BELL})))
    tile, size = PRIZE_PICTURE
    well = layout.regions[regions["well"]]
    layout.add_sprite("fair:prize", regions["well"], x=_q(x1 - DEEP / 2), y=_q((y0 + y1) / 2), z=seated_z(
        seat="floor", floor_z=well.floor_z, ceiling_z=well.ceiling_z, tile_height=_art(tile)[1], y_repeat=size, y_offset=_art(tile)[3],
        cstat=128, clearance=16), picnum=tile, x_repeat=size, y_repeat=size, type=PRIZE, status=3, cstat=128 | CARRIED, shade=-8)
    return len(SLABS) + 7


def _art(tile: int):
    import wallplane
    return wallplane.art()[tile]


def _write(layout, name, text, region, middle, angle, z, size=28, pal=0) -> int:
    """A word along a wall, read from in front of it: tile 3808 is A."""
    step = _art(3808)[0] * size // 4 + 10
    right = ((angle + 1536) & 2047) * math.pi / 1024
    for k, letter in enumerate(text):
        off = (k - (len(text) - 1) / 2) * step
        layout.add_sprite(f"fair:{name}_letter_{k}", region, x=round(middle[0] + math.cos(right) * off), y=round(middle[1] + math.sin(right) * off),
                          z=z, picnum=3808 + ord(letter) - ord("A"), x_repeat=size, y_repeat=size, angle=angle, cstat=16 | 64 | 128,
                          shade=-20, pal=pal)
    return len(text)


def _dress_stall(layout, name) -> int:
    from bloodmap import flatsprite
    from bloodmap.placement import seated_z
    from shapely import Point, Polygon
    rect, side, _outside, sign, shelf, counter = STALLS[name]
    regions, street = _REGIONS[name], _HOST[name]
    (dx, dy), angle = _facing(side)
    x0, y0, x1, y1 = rect
    shapes = [(r, Polygon(layout.regions[r].outer, layout.regions[r].holes)) for r in regions.values()]
    put = 0

    def region_at(x, y):
        return next((r for r, shape in shapes if shape.covers(Point(x, y))), street)

    def add(tag, x, y, z, **fields):
        nonlocal put
        put += 1
        layout.add_sprite(f"stall:fair_{name}_{tag}", region_at(x, y), x=round(x), y=round(y), z=round(z),
                          **{"type": 0, "status": 0, "shade": 8, "cstat": 128, **fields})
    # the roof, half a unit out over the front
    out, lip = 0.45, 0.12
    rx0, ry0 = x0 - (out if dx < 0 else lip), y0 - (out if dy < 0 else lip)
    rx1, ry1 = x1 + (out if dx > 0 else lip), y1 + (out if dy > 0 else lip)
    rx0, ry0, rx1, ry1 = (round(v * 16) / 16 for v in (rx0, ry0, rx1, ry1))      # whole repeats of the cloth
    roof = GRADE - CANOPY
    for k, p in enumerate(flatsprite.cover((_q(rx0), _q(ry0), _q(rx1), _q(ry1)), _art(STRIPE)[:2])):
        add(f"roof_{k}", p["x"], p["y"], roof, picnum=STRIPE, angle=p["angle"], x_repeat=p["x_repeat"], y_repeat=p["y_repeat"],
            cstat=32 | 128 | 256, shade=22)
    # the valance: bulbs along the front, cloth round the rest
    for face, (ax, ay), (bx, by) in (("east", (rx1, ry0), (rx1, ry1)), ("west", (rx0, ry0), (rx0, ry1)),
                                     ("south", (rx0, ry1), (rx1, ry1)), ("north", (rx0, ry0), (rx1, ry0))):
        length = math.hypot(_q(bx - ax), _q(by - ay))
        tile, wide, tall = (BULBS, 1024, 40) if face == side else (STRIPE, 512, 20)
        count = max(1, round(length / wide))
        size = round(length / count * 4 / _art(tile)[0])
        half = _art(tile)[1] * tall * 2
        for k in range(count):
            t = (k + 0.5) / count
            add(f"valance_{face}_{k}", _q(ax + (bx - ax) * t), _q(ay + (by - ay) * t), roof + half, picnum=tile, angle=_facing(face)[1],
                x_repeat=size, y_repeat=tall, cstat=16 | 128 | 256, shade=-12 if tile == BULBS else 12)
    # a post at each front corner
    front = {"east": ((rx1, y0), (rx1, y1)), "west": ((rx0, y0), (rx0, y1)), "south": ((x0, ry1), (x1, ry1)), "north": ((x0, ry0), (x1, ry0))}[side]
    for k, (px, py) in enumerate(front):
        add(f"post_{k}", _q(px) - dx * 60, _q(py) - dy * 60, GRADE - CANOPY // 2, picnum=117, x_repeat=28, y_repeat=CANOPY // 512,
            cstat=128 | 256 | 1, shade=16)
    middle = (_q((x0 + x1) / 2), _q((y0 + y1) / 2))
    edge = {"east": _q(rx1), "west": _q(rx0), "south": _q(ry1), "north": _q(ry0)}[side]
    if sign:
        at = (edge + dx * 14, middle[1]) if dx else (middle[0], edge + dy * 14)
        _write(layout, name, sign, region_at(*at), at, angle, roof + 8200, size=40, pal=2)
    # what stands on the shelf and the counter
    import goods
    for cell, row in (("shelf", shelf), ("counter", counter)):
        for k, tile in enumerate(row):
            u = (k + 0.5) / len(row)
            fields = goods.fields(tile) if tile in goods.ASSETS else {"picnum": tile, "cstat": 0, "x_repeat": 40, "y_repeat": 40, "shade": -20,
                                                                      "pal": 0, "type": 0, "status": 0}
            at = f"stall:fair_{name}_{cell}_{k}"
            layout.place_on_floor(at, regions[cell], local=(0.5, u) if dx else (u, 0.5), **fields)
            if _art(tile)[3]:                                      # (drawn about its middle: set down by the box the renderer draws)
                spec = next(p for p in layout.placements if p.placement_id == at)
                spec.cstat, host = 128, layout.regions[regions[cell]]
                spec.z = seated_z(seat="floor", floor_z=host.floor_z, ceiling_z=host.ceiling_z, tile_height=_art(tile)[1],
                                  y_repeat=spec.y_repeat, y_offset=_art(tile)[3], cstat=128, clearance=16)
            put += 1
    # a lamp under the roof's front; the fortune teller sits in the dark
    if name == "fortunes":
        return put
    across = _q(0.5 * ((y1 - y0) if dx else (x1 - x0)) - 0.3)
    add("lamp", middle[0] + (dx * _q((x1 - x0) / 2 + 0.15) if dx else across), middle[1] + (dy * _q((y1 - y0) / 2 + 0.15) if dy else across),
        GRADE - 22500, picnum=693, x_repeat=36, y_repeat=36, shade=-128)
    return put


def _carousel(layout) -> int:
    from bloodmap import flatsprite
    regions = _REGIONS["carousel"]
    cx, cy = _q(AT[0]), _q(AT[1])
    put = 0

    def add(tag, x, y, z, **fields):
        nonlocal put
        put += 1
        far = math.hypot(x - cx, y - cy) / PU
        cell = "neck" if far < NECK_R * 0.9 else "drum" if far < DRUM_R * 0.92 else "platform"
        fields = {"type": 0, "status": 0, "shade": 4, "cstat": 128, **fields}
        layout.add_sprite(f"fair:carousel_{tag}", regions[cell], x=round(x), y=round(y), z=round(z), **{**fields, "cstat": fields["cstat"] | CARRIED})
    roof = GRADE - ROOF - 128
    # the roof: a square and four wings, flat
    half, reach = 1.75, 2.5625
    for tag, box in (("mid", (-half, -half, half, half)), ("n", (-1.125, -reach, 1.125, -half)), ("s", (-1.125, half, 1.125, reach)),
                     ("w", (-reach, -1.125, -half, 1.125)), ("e", (half, -1.125, reach, 1.125))):
        x0, y0, x1, y1 = (_q(AT[k % 2] + v) for k, v in enumerate(box))
        for k, p in enumerate(flatsprite.cover((x0, y0, x1, y1), _art(STRIPE)[:2])):
            add(f"roof_{tag}_{k}", p["x"], p["y"], roof, picnum=STRIPE, angle=p["angle"], x_repeat=p["x_repeat"], y_repeat=p["y_repeat"],
                cstat=32 | 128, shade=20)
    # the rim: bulbs, and cloth under them
    wide = 2 * RADIUS * math.sin(math.pi / SIDES) * PU
    apothem = RADIUS * math.cos(math.pi / SIDES) * PU - 10
    for k in range(SIDES):
        turn = 2 * math.pi * (k + 0.5) / SIDES
        x, y, angle = cx + apothem * math.cos(turn), cy + apothem * math.sin(turn), round(turn * 1024 / math.pi) & 2047
        add(f"bulbs_{k}", x, y, roof + 32 * 36 * 2, picnum=BULBS, angle=angle, x_repeat=round(wide * 4 / 128) + 1, y_repeat=36, cstat=16 | 128,
            shade=-24)
        add(f"cloth_{k}", x, y, roof + 32 * 36 * 4 + 64 * 14 * 2, picnum=STRIPE, angle=angle, x_repeat=round(wide * 4 / 32) + 1, y_repeat=14,
            cstat=16 | 128, shade=2)
    tall = ROOF - STEP
    for k in range(8):
        turn = 2 * math.pi * (k + 0.5) / 8
        x, y = cx + 2.1 * PU * math.cos(turn), cy + 2.1 * PU * math.sin(turn)
        add(f"pole_{k}", x, y, GRADE - STEP - tall // 2, picnum=POLE, x_repeat=20, y_repeat=tall // 512, cstat=128)
        tile, size, pal = ((HOUND, 40, GREY), (RAT, 60, COLD))[k % 2]
        add(f"mount_{k}", x + 6 * math.cos(turn), y + 6 * math.sin(turn), GRADE - STEP - (11000 if k % 2 else 12400), picnum=tile, x_repeat=size,
            y_repeat=size, pal=pal, cstat=128, angle=round((turn + math.pi / 2) * 1024 / math.pi) & 2047)
    for k in range(4):
        turn = 2 * math.pi * k / 4
        x, y = cx + 2.0 * PU * math.cos(turn), cy + 2.0 * PU * math.sin(turn)
        add(f"lantern_{k}", x, y, roof + 37 * 32 * 2 + 600, picnum=693, x_repeat=32, y_repeat=32, shade=-128)
    layout.add_sprite("fair:tune", regions["neck"], x=cx, y=cy, z=GRADE - ROOF - 4096, type=710, picnum=2521, status=12, cstat=32896,
                      behavior={"state": 1, "data_1": NEAR, "data_2": FAR, "data_3": TUNE, "data_4": LOUD})
    return put


def dress(layout) -> dict:
    """Roofs, valances, words, goods, bills, balloons; the mounts on their poles; the calliope."""
    from shapely import Point, Polygon
    report = {"sprites": 0}
    for name in STALLS:
        report["sprites"] += _dress_stall(layout, name)
    report["sprites"] += _carousel(layout) + _gallery(layout)
    for k, (stall, side, t, tile, size, up) in enumerate(BILLS):
        x0, y0, x1, y1 = STALLS[stall][0]
        (dx, dy), angle = _facing(side)
        x = {"east": x1, "west": x0}.get(side, x0 + (x1 - x0) * t)
        y = {"south": y1, "north": y0}.get(side, y0 + (y1 - y0) * t)
        layout.add_sprite(f"fair:bill_{k}", _HOST[stall], x=_q(x) + dx * 8, y=_q(y) + dy * 8, z=GRADE - round(up * BODY), picnum=tile,
                          x_repeat=size, y_repeat=size, angle=angle, cstat=16 | 64 | 128, shade=10)
    # the booth: a clerk, its board and its prices
    x0, y0, x1, y1 = STALLS["tickets"][0]
    layout.add_sprite("fair:tickets_sign", _REGIONS["tickets"]["shelf"], x=_q((x0 + x1) / 2) - 130, y=_q(y0 + THICK) + 8, z=GRADE - 26500, picnum=943,
                      x_repeat=52, y_repeat=52, angle=512, cstat=16 | 64 | 128, shade=-24)
    layout.add_sprite("fair:tickets_prices", _HOST["tickets"], x=_q((x0 + x1) / 2), y=_q(y1) + 8, z=GRADE - 4300, picnum=905, x_repeat=44,
                      y_repeat=44, angle=512, cstat=16 | 64 | 128, shade=0)
    layout.place_on_floor("fair:clerk", _REGIONS["tickets"]["inside"], local=(0.5, 0.5), type=0, picnum=2400, cstat=0, x_repeat=40, y_repeat=40,
                          shade=0, angle=512, status=0)
    for k, (x, y, pal) in enumerate(BALLOONS):
        region = next(r for r in layout.regions.values() if r.parallax_ceiling and r.floor_z == GRADE
                      and Polygon(r.outer, r.holes).contains(Point(_q(x), _q(y))))
        layout.add_sprite(f"fair:balloon_{k}", region.region_id, x=_q(x), y=_q(y), z=GRADE - 21000, picnum=1115, x_repeat=40, y_repeat=40,
                          pal=pal, cstat=128, shade=-8)
    return report


def keep(level, compiled) -> int:
    """Put back the boards the city's later passes took for a facade."""
    from bloodmap.model import record_fields
    where = {}
    for region in {r for r, *_rest in _PAINTED}:
        for wall in compiled.allocations[region].wall_ids:
            f = record_fields(level.walls[wall])
            end = record_fields(level.walls[int(f["point2"])])
            where[region, (f["x"], f["y"]), (end["x"], end["y"])] = f
    put = 0
    for region, a, b, paint in _PAINTED:
        f = where.get((region, tuple(a), tuple(b))) or where.get((region, tuple(b), tuple(a)))
        if f is not None and any(f[k] != v for k, v in paint.items()):
            f.update(paint)
            put += 1
    return put
