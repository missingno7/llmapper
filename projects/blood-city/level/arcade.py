"""The Gravesend Arcade's hall: a gallery at the street's level, broken, over a sunk court with a lantern above it and a dead fountain in it.

Designed in `references/arcade-design.md`, from the study `arcade` (E4M9's
atrium). What was here was one straight hall between six equal shops, and a
blind reader named it "Ornate hallway with library alcove". What is here is one
section: the street comes in on a gallery, the arcade is a storey and a half
below it, and the eye key is in sight from the door, across a gap. The way to
it is down the stopped escalator, through the court, and up the span that fell.

Built of `bloodmap.arrangement`; the street door, the service passage and its
secret are rooms of the tree (`l3_mall`).
"""

from __future__ import annotations

import math

from bloodmap import arrangement as A
from bloodmap import wiring
from bloodmap.doors import z_motion_door
from bloodmap.slope import SlopeSpec

import keysign
import wallplane
import wires
from resolution import GRADE, SKY_TILE

PU = 1024
KEY = "region:gravesend/market_slip/gravesend_arcade/hall"
LAYER = "arcade"
#: levels: the street's, the court's a body and a half under it; the hall's ceiling, the gallery's, the sky over the lantern
DROP = 24576
COURT = GRADE + DROP
HALL, SOFFIT, SKY = -57344, -32768, -77824
#: plan, in plan units
WEST, EDGE, EAST_EDGE, EAST = 39.5, 41.75, 48.5, 50.5       # the street door's wall, the court's two ends, the service door's
NORTH, GALLERY, SOUTH = 43.0, 46.25, 47.75                  # the court's north wall, the gallery's edge and its back
ESCALATOR = (44.0, 45.0)                                    # its foot, and its north side (its south is the gallery's)
RAIL = 44.875
HINGE = 48.0                                                # where the fallen span still holds
LANTERN = (44.75, 43.5, 47.75, 45.5)
BASIN = (46.25, 44.5)
PLINTH = (49.25, 44.75, 49.75, 45.25)
#: the three shops: Pickman's on the gallery (lit, worked in), Miguel's on the gallery (shut), the draper's below (wrecked)
BOOKS = (39.5, 40.75, 41.75, 42.625)
GUNS = (39.75, 48.0, 43.25, 49.375)
SHUTTER = (40.0, SOUTH, 43.0, 48.0)
SHUTTER_OPEN = 24576
DRAPER = (42.25, 40.75, 47.25, 42.25)
FRONT = (42.25, 42.875, 47.25, NORTH)
DOOR = (44.25, 45.25)
WINDOWS = {"win_w": (42.5, 44.0), "win_e": (45.5, 47.0)}    # the west one is broken in

MARBLE, PAVING, ENCAUSTIC, CHEQUER, PARQUET = 43, 44, 304, 290, 372
WALL, PLASTER, RUBBLE, COFFER, SLATE = 1718, 108, 417, 454, 40
FRAME, PILASTER, WOOD, TILED, BOOKCASE = 105, 88, 34, 2294, 2539
STEPS, HANDRAIL, STRINGER, SHIRTS, ROLLER = 376, 195, 255, 2635, 9
WATER, PANEL = 1120, 84

#: cell -> (floor, ceiling, floor tile, ceiling tile, wall tile)
LEVELS = {
    "walk": (GRADE, SOFFIT, ENCAUSTIC, FRAME, PLASTER),
    "court": (COURT, HALL, PAVING, COFFER, WALL),
    "bay": (COURT, SOFFIT, PAVING, FRAME, RUBBLE),
    "span": (GRADE, SOFFIT, ENCAUSTIC, FRAME, RUBBLE),
    "landing": (GRADE, HALL, ENCAUSTIC, COFFER, WALL),
    "escalator": (GRADE, HALL, STEPS, COFFER, WALL),
    "rail": (GRADE - 6144, HALL, HANDRAIL, COFFER, WALL),
    "lantern": (COURT, SKY, PAVING, SKY_TILE, WALL),
    "rim": (COURT - 6144, SKY, MARBLE, SKY_TILE, MARBLE),
    "water": (COURT - 3072, SKY, WATER, SKY_TILE, MARBLE),
    "front": (COURT, -10240, PAVING, FRAME, FRAME),
    "draper": (COURT, COURT - 30720, CHEQUER, SLATE, TILED),
    "counter": (COURT - 8192, COURT - 30720, WOOD, SLATE, TILED),
    "win_w": (COURT - 8192, COURT - 26624, WOOD, FRAME, FRAME),
    "win_e": (COURT - 8192, COURT - 26624, WOOD, FRAME, FRAME),
    "sash_e": (COURT - 8192, COURT - 26624, WOOD, FRAME, PILASTER),
    "books": (GRADE, GRADE - 28672, PARQUET, FRAME, BOOKCASE),
    "desk": (GRADE - 8192, GRADE - 28672, WOOD, FRAME, BOOKCASE),
    "bookwin": (GRADE - 8192, GRADE - 22528, WOOD, FRAME, FRAME),
    "booksash": (GRADE - 8192, GRADE - 22528, WOOD, FRAME, PILASTER),
    "guns": (GRADE, GRADE - 28672, PARQUET, SLATE, PANEL),
    "gun_counter": (GRADE - 8192, GRADE - 28672, WOOD, SLATE, PANEL),
    "shutter": (GRADE, GRADE, ROLLER, ROLLER, ROLLER),
    "closed": (GRADE, GRADE - 24576, PAVING, FRAME, PILASTER),
    "plinth": (GRADE - 9216, HALL, MARBLE, COFFER, MARBLE),
}
WALKED = ("walk", "court", "landing", "draper", "books", "guns")
#: what stands at the street's level, over the sewer at its east end; the rest is the court's
AT_STREET = ("walk", "landing", "plinth", "closed", "books", "desk", "bookwin", "booksash", "guns", "gun_counter", "shutter")
OPEN_TO_SKY = ("lantern", "rim", "water")


def _q(v: float) -> int:
    return round(v * PU)


def _rect(x0, y0, x1, y1):
    return [(_q(x0), _q(y0)), (_q(x1), _q(y0)), (_q(x1), _q(y1)), (_q(x0), _q(y1))]


def _ring(*points):
    return [(_q(x), _q(y)) for x, y in points]


#: marble posts: two at the landing's edge, the service door between them (what there is to stand behind), one under each
#: of the gallery's two edges
POST = 0.25
POSTS = ((EAST_EDGE, 43.9375), (EAST_EDGE, 45.8125), (EDGE - POST, 43.9375), (43.5, GALLERY))
#: the gallery's broken end, and the fallen span's foot
BROKEN = ((44.5, GALLERY), (44.31, 46.6), (44.62, 46.95), (44.36, 47.3), (44.5, SOUTH))
FOOT = ((45.72, GALLERY), (45.52, 46.62), (45.84, 47.0), (45.6, 47.4), (45.7, SOUTH))


def plan() -> list:
    """Every cell of the hall and its shops."""
    place = A.Arrangement()
    place.add("court", _rect(EDGE, NORTH, EAST_EDGE, GALLERY))
    place.add("bay", _rect(44.0, GALLERY, 46.2, SOUTH))
    place.add("walk", _rect(WEST, NORTH, EDGE, SOUTH), _ring((EDGE, GALLERY), *BROKEN, (EDGE, SOUTH)))
    place.add("span", _ring(FOOT[0], (HINGE, GALLERY), (HINGE, SOUTH), *reversed(FOOT[1:])))
    place.add("landing", _rect(EAST_EDGE, NORTH, EAST, SOUTH), _rect(HINGE, GALLERY, EAST_EDGE, SOUTH))
    place.add("escalator", _rect(EDGE, ESCALATOR[1], ESCALATOR[0], GALLERY))
    place.add("rail", _rect(EDGE, RAIL, ESCALATOR[0], ESCALATOR[1]))
    place.add("lantern", _rect(*LANTERN))
    centre = (_q(BASIN[0]), _q(BASIN[1]))
    place.add("rim", A.circle(centre, 960, 8, 1 / 16))
    place.add("water", A.circle(centre, 736, 8, 1 / 16))
    place.add("plinth", _rect(*PLINTH))
    place.add("front", _rect(*FRONT))
    place.add("draper", _rect(*DRAPER), _rect(DOOR[0], DRAPER[3], DOOR[1], FRONT[1]))
    place.add("counter", _rect(42.75, 41.375, 44.0, 41.6875))
    for name, (x0, x1) in WINDOWS.items():
        sash = "sash_" + name[-1]
        deep = FRONT[1] - 0.0625 if sash in LEVELS else FRONT[1]
        place.add(name, _rect(x0, DRAPER[3], x1, deep))
        if sash in LEVELS:
            place.add(sash, _rect(x0, deep, x1, FRONT[1]))
    place.add("books", _rect(*BOOKS), _rect(39.75, BOOKS[3], 40.5, NORTH))
    place.add("desk", _rect(40.5, 41.4375, 41.375, 41.75))
    place.add("bookwin", _rect(40.75, BOOKS[3], 41.5, NORTH - 0.0625))
    place.add("booksash", _rect(40.75, NORTH - 0.0625, 41.5, NORTH))
    place.add("guns", _rect(*GUNS))
    place.add("gun_counter", _rect(40.375, 48.8125, 42.0, 49.0625))
    place.add("shutter", _rect(*SHUTTER))
    place.add("closed", _rect(48.875, NORTH - 0.125, 50.125, NORTH))
    for x, y in POSTS:
        place.solid(_rect(x, y, x + POST, y + POST))
    return place.resolve()


def _post(a, b) -> bool:
    """Is this edge a post's?"""
    return any(_q(x) <= min(a[0], b[0]) and max(a[0], b[0]) <= _q(x + POST) and _q(y) <= min(a[1], b[1])
               and max(a[1], b[1]) <= _q(y + POST) for x, y in POSTS)


def panes() -> list[tuple[int, int, int, int]]:
    """Where the glass hangs (`glass.glaze`): the draper's whole window and the bookseller's."""
    x0, x1 = WINDOWS["win_e"]
    y = _q(FRONT[1] - 0.0625)
    by = _q(NORTH - 0.0625)
    return [(_q(x0), y, _q(x1), y), (_q(40.75), by, _q(41.5), by)]


def _edge(cell, *, x):
    """The edge of a cell that lies on a line of x."""
    ring = cell.outer
    return next((a, b) for a, b in zip(ring, ring[1:] + ring[:1]) if a[0] == b[0] == _q(x))


#: what `_face` painted: (region, a, b, tile); `keep` puts it back
_PAINTED: list[tuple] = []


def _face(seen: str, beyond: str | None, a, b) -> dict:
    """What a cell shows along an edge."""
    if seen == "court":
        if beyond == "span":                                # the wall of the hall over it, the broken slab under
            return {"picnum": WALL, "cstat": 2}
        if beyond == "rail":
            return {"picnum": STRINGER}
        return {}
    if seen == "escalator" and beyond == "rail":
        return {"picnum": HANDRAIL}
    if seen == "span" and beyond == "court":
        return {"picnum": RUBBLE}
    if seen == "lantern" and beyond == "rim" or seen == "water":
        return {"picnum": MARBLE}
    if seen == "landing" and beyond == "plinth":
        return {"picnum": MARBLE}
    if _post(a, b):
        return {"picnum": MARBLE}
    if seen == "draper":
        if beyond == "counter":
            return {"picnum": PANEL}
        if min(a[1], b[1]) >= _q(DRAPER[3]) and a[0] == b[0]:
            return {"picnum": PILASTER}                     # the doorway's cheeks
        # the back wall is the draper's shelves, floor to ceiling
        if beyond is None and a[1] == b[1] == _q(DRAPER[1]):
            return {"picnum": SHIRTS, "x_repeat": (abs(b[0] - a[0])) // 64, "y_repeat": 16, "cstat": 4}
    if seen == "books":
        if beyond == "desk":
            return {"picnum": PANEL}
        if beyond in ("walk", "bookwin"):
            return {"picnum": FRAME}
        if beyond is None and min(a[1], b[1]) >= _q(BOOKS[3]):
            return {"picnum": PILASTER}
    if seen == "walk" and beyond in ("books", "booksash"):
        return {"picnum": FRAME}
    if seen == "walk" and beyond is None and a[1] == b[1] == _q(NORTH) and abs(a[0] - b[0]) < 300:
        return {"picnum": PILASTER}
    if seen == "closed" and beyond is None and a[1] == b[1]:
        return {"picnum": ROLLER}
    if seen == "front" and beyond is None and a[0] == b[0]:
        return {"picnum": PILASTER}
    return {}


def build(layout, tree: dict) -> dict[str, str]:
    """Lay the hall; `tree` is the region ids of the street door and the service door."""
    cells = plan()
    by_name = {c.name: c for c in cells}
    slopes = {
        "escalator": SlopeSpec(hinge=_edge(by_name["escalator"], x=EDGE), rise_z=DROP),
        "rail": SlopeSpec(hinge=_edge(by_name["rail"], x=EDGE), rise_z=DROP),
        "span": SlopeSpec(hinge=_edge(by_name["span"], x=HINGE), rise_z=DROP),
    }

    def surface(name):
        floor, ceiling, floor_tile, roof, wall = LEVELS[name]
        more = {"floor_slope": slopes[name]} if name in slopes else {}
        if name == "shutter":
            more = dict(type=600, door_face=ROLLER, inherit_finish="both", sector_behavior=z_motion_door(
                GRADE, GRADE - SHUTTER_OPEN, interaction="remote", rx_id=wires.channel("key:eye"), open_time=20))
        if name in OPEN_TO_SKY:
            more["parallax_ceiling"] = True
        return dict(floor_z=floor, ceiling_z=ceiling, floor_picnum=floor_tile, ceiling_picnum=roof, wall_picnum=wall,
                    floor_shade=20, wall_shade=20, ceiling_shade=24,
                    layer="street" if name in AT_STREET else LAYER,
                    role="doorway" if name == "shutter" else "interior" if name in WALKED else "detail",
                    declared_zero_exit=name not in WALKED, intent={"kind": "furnished"}, **more)

    _PAINTED.clear()

    def face(seen, beyond, a, b):
        paint = _face(seen, beyond, a, b)
        if "picnum" in paint:
            _PAINTED.append((f"{KEY}:{seen}", a, b, paint["picnum"]))
        return paint

    regions = A.lay(layout, KEY, cells, surface, face,
                    lambda left, right, _a, _b: {"gated": True} if "shutter" in (left, right) else {})
    for name, region, x in (("entry", tree["entry_door"], WEST), ("service", tree["service_door"], EAST)):
        ys = [p[1] for p in layout.regions[region].outer]
        layout.add_connection(f"connection:arcade_{name}_in", region, regions["walk" if name == "entry" else "landing"],
                              a1=(_q(x), max(ys)), a2=(_q(x), min(ys)), min_width=1024)
    wires.wire("key:eye").then(wiring.region(regions["shutter"]))
    _furnish(layout, regions)
    return regions


def keep(disk, compiled) -> int:
    """Put back the fronts, posts and broken edges the city's later passes took for openings and lintels."""
    from bloodmap.model import record_fields
    where = {}
    for region in {r for r, *_rest in _PAINTED}:
        for wall in compiled.allocations[region].wall_ids:
            f = record_fields(disk.walls[wall])
            end = record_fields(disk.walls[int(f["point2"])])
            where[region, (f["x"], f["y"]), (end["x"], end["y"])] = f
    put = 0
    for region, a, b, tile in _PAINTED:
        f = where.get((region, tuple(a), tuple(b))) or where.get((region, tuple(b), tuple(a)))
        if f is not None and f["picnum"] != tile:
            f["picnum"] = tile
            put += 1
    return put


# ---- what stands in it --------------------------------------------------------

def _stand(layout, regions, cell, name, x, y, tile, size, *, tall=None, seat="floor", cstat=128, shade=-8, foot=None,
           **fields) -> str:
    """Seat a sprite on a cell's floor or hang it from its ceiling; `foot`: hung with its foot that far over the floor."""
    from bloodmap.placement import drawn_extent, seated_z
    room = layout.regions[regions[cell]]
    _w, height, _x, offset = wallplane.art()[tile]
    tall = size if tall is None else tall
    if foot is not None:                                    # its chain runs on into the ceiling
        _top, bottom = drawn_extent(height, offset, tall, cstat)
        z = max(room.floor_z - foot - bottom, room.ceiling_z + 16)
        fields.setdefault("sunk", True)
    else:
        z = seated_z(seat=seat, floor_z=room.floor_z, ceiling_z=room.ceiling_z, tile_height=height, y_repeat=tall,
                     y_offset=offset, cstat=cstat, clearance=16)
    return layout.add_sprite(f"arcade:{name}", regions[cell], x=_q(x), y=_q(y), z=z, picnum=tile, x_repeat=size,
                             y_repeat=tall, cstat=cstat, shade=shade, **fields)


def _flat(layout, regions, cell, name, x, y, tile, size, *, shade=8, angle=1536):
    room = layout.regions[regions[cell]]
    layout.add_sprite(f"arcade:{name}", regions[cell], x=_q(x), y=_q(y), z=room.floor_z - 16, picnum=tile, x_repeat=size,
                      y_repeat=size, angle=angle, cstat=160, shade=shade)


def _bill(layout, regions, cell, name, a, b, tile, size, height, *, tall=None, shade=0, **more):
    """A sprite on a wall, `a` to `b` in plan units, its middle that many bodies over the cell's floor."""
    return layout.place_on_wall(
        f"arcade:{name}", regions[cell], a1=(_q(a[0]), _q(a[1])), a2=(_q(b[0]), _q(b[1])), t=0.5,
        height_player_heights=height, offset_player_widths=0.04, spans_opening=True, picnum=tile, x_repeat=size,
        y_repeat=tall or size, cstat=16 | 64 | 128, shade=shade, type=0, status=0, **more)


#: balustrades (588, E2M4's): cell, from, to, and which way the cell lies
BALUSTRADES = (("walk", (EDGE, 43.0), (EDGE, 43.9375), (-16, 0)), ("walk", (EDGE, 44.1875), (EDGE, RAIL), (-16, 0)),
               ("walk", (EDGE, GALLERY), (43.5, GALLERY), (0, 16)), ("walk", (43.75, GALLERY), (44.31, GALLERY), (0, 16)),
               ("landing", (EAST_EDGE, 43.0), (EAST_EDGE, 43.9375), (16, 0)),
               ("landing", (EAST_EDGE, 44.1875), (EAST_EDGE, 45.8125), (16, 0)),
               ("landing", (HINGE, GALLERY), (EAST_EDGE, GALLERY), (0, 16)))
#: 128 texels by 48, at this height: 0.6 of a body
BALUSTRADE_TALL = 52


def _balustrades(layout, regions) -> None:
    from bloodmap.placement import seated_z
    _w, height, _x, offset = wallplane.art()[588]
    for k, (cell, a, b, inward) in enumerate(BALUSTRADES):
        length = _q(math.hypot(b[0] - a[0], b[1] - a[1]))
        parts = max(1, round(length / 1400))
        z = seated_z(seat="floor", floor_z=GRADE, ceiling_z=HALL, tile_height=height, y_repeat=BALUSTRADE_TALL,
                     y_offset=offset, cstat=145, clearance=16)
        for n in range(parts):
            t = (n + 0.5) / parts
            layout.add_sprite(f"arcade:balustrade_{k}_{n}", regions[cell], x=_q(a[0] + t * (b[0] - a[0])) + inward[0],
                              y=_q(a[1] + t * (b[1] - a[1])) + inward[1], z=z, picnum=588,
                              x_repeat=max(8, length // parts // 32), y_repeat=BALUSTRADE_TALL, cstat=145,
                              angle=0 if a[0] == b[0] else 512, shade=8)


#: chain lamps: cell, x, y, how far over the floor the lamp hangs: either side of the clock
LAMPS = (("landing", 49.6, 43.8, 31000), ("landing", 49.6, 46.3, 31000))
#: round glass on the ceilings
GLOBES = (("walk", 40.625, 45.0), ("walk", 42.6, 47.0), ("books", 40.75, 41.2), ("win_e", 46.25, 42.5), ("guns", 41.5, 48.4))
#: mannequins (the owner's 2377): cell, x, y
MANNEQUINS = (("win_e", 45.85, 42.5), ("win_e", 46.65, 42.52), ("win_w", 42.8, 42.6), ("draper", 46.85, 41.1),
              ("draper", 46.3, 41.0))


def _furnish(layout, regions) -> None:
    import l3_mall
    _balustrades(layout, regions)
    for k, (cell, x, y, foot) in enumerate(LAMPS):
        _stand(layout, regions, cell, f"lamp_{k}", x, y, 641, 64, foot=foot, shade=-128)
    for k, (cell, x, y) in enumerate(GLOBES):
        _stand(layout, regions, cell, f"globe_{k}", x, y, 676, 40, seat="ceiling", cstat=168, shade=-128)
    # one gas lamp, by the fallen span's side: the way up
    _stand(layout, regions, "court", "gas_lamp", 48.1, 45.9, 640, 120, shade=-16)

    # the court: a cherub that pours nothing, and the lantern's glazing bars against the sky
    _stand(layout, regions, "water", "statue", *BASIN, 536, 88, shade=0)
    for k in range(3):
        layout.add_sprite(f"arcade:bars_{k}", regions["water" if k == 1 else "lantern"], x=_q(LANTERN[0] + 0.5 + k), y=_q(LANTERN[1] + 1.0),
                          z=HALL - 512, picnum=1060, x_repeat=64, y_repeat=64, cstat=32 | 128, angle=1536, shade=24)
    # the hall's north wall over the draper's, as E4M9 hangs its own
    for k, (tile, x) in enumerate(((847, 43.6), (845, 45.9))):
        _bill(layout, regions, "court", f"banner_{k}", (x - 1, NORTH), (x + 1, NORTH), tile, 64, 3.95, shade=4)
    # the clock over the service door, at the end of the view from the street
    _bill(layout, regions, "landing", "clock", (EAST, NORTH), (EAST, 47.0), 1165, 96, 2.75, shade=-12)
    keysign.placard(layout, "keysign:arcade_service", regions["landing"], ((_q(EAST), _q(45.5)), (_q(EAST), _q(46.25))),
                    l3_mall.SERVICE_KEY)
    keysign.item(layout, "key:arcade_eye", regions["plinth"], l3_mall.SERVICE_KEY)

    # names
    _bill(layout, regions, "walk", "pickmans", (39.6, NORTH), (41.6, NORTH), 740, 64, 2.0, shade=-8)
    _bill(layout, regions, "walk", "miguels", (43.0, SOUTH), (40.0, SOUTH), 2341, 52, 2.14, shade=-8)
    _bill(layout, regions, "landing", "ichabods", (48.75, NORTH), (50.25, NORTH), 2340, 48, 1.95, shade=-4)
    wallplane.text(layout, "arcade:draper", regions["front"], (_q(42.25), _q(FRONT[1])), (_q(47.25), _q(FRONT[1])),
                   words="DRAPER", style="fascia", height_player_heights=2.15, over_steps=True)
    _bill(layout, regions, "walk", "signing", (SOUTH - 4.25, SOUTH), (43.1, SOUTH), 356, 40, 0.9)

    # the draper's: what is in the windows, and what was left
    for k, (cell, x, y) in enumerate(MANNEQUINS):
        _stand(layout, regions, cell, f"mannequin_{k}", x, y, 2377, 40, cstat=384, shade=0)
    _bill(layout, regions, "court", "sale", (47.4, NORTH), (48.4, NORTH), 2357, 40, 0.95)
    broken = layout.regions[regions["win_w"]]
    layout.add_sprite("arcade:smashed", regions["win_w"], x=_q(43.25), y=_q(FRONT[1] - 0.02),
                      z=(broken.floor_z + broken.ceiling_z) // 2, picnum=1099, x_repeat=96,
                      y_repeat=(broken.floor_z - broken.ceiling_z) // 256, angle=512, cstat=16 | 128, shade=4)
    for k, y in enumerate((41.1, 41.75)):
        _bill(layout, regions, "draper", f"hung_{k}", (DRAPER[0], y + 0.25), (DRAPER[0], y - 0.25), 73, 48, 0.8, shade=4)
    _flat(layout, regions, "draper", "cloth", 43.3, 42.0, 1167, 48, angle=300)
    _flat(layout, regions, "court", "paper", 44.4, 43.8, 1167, 48, angle=1900)
    _stand(layout, regions, "counter", "vase", 43.7, 41.53, 739, 40, shade=4)
    # the gunsmith's: what hangs over his counter, and what is left on it
    wallplane.sprite(layout, "arcade:trophy", regions["guns"], (_q(43.0), _q(GUNS[3])), (_q(40.0), _q(GUNS[3])), tile=714,
                     x_repeat=48, y_repeat=48, cstat=16 | 64 | 128, height_player_heights=0.9, status=0)
    _stand(layout, regions, "gun_counter", "box_a", 40.75, 48.94, 683, 40, shade=0)      # (boxes of shells and bullets lay here: what looks like a pickup is one)
    _stand(layout, regions, "gun_counter", "box_b", 41.6, 48.94, 605, 40, shade=0)
    # the bookseller's desk
    _stand(layout, regions, "desk", "ledger", 40.8, 41.6, 518, 36, shade=-16)
    _stand(layout, regions, "desk", "candle", 41.2, 41.58, 938, 40, cstat=384, shade=-128, type=32)
    _stand(layout, regions, "bookwin", "book_a", 41.0, 42.8, 348, 40, shade=-8)
    _stand(layout, regions, "bookwin", "book_b", 41.3, 42.78, 518, 34, shade=-8)
    # what fell with the gallery
    for k, (cell, x, y, tile, size, angle) in enumerate((
            ("bay", 45.2, 47.5, 69, 60, 300), ("bay", 44.95, 46.6, 69, 56, 900), ("court", 45.2, 45.95, 69, 56, 640))):
        _flat(layout, regions, cell, f"plank_{k}", x, y, tile, size, angle=angle, shade=14)
    _stand(layout, regions, "bay", "rubble", 44.75, 47.5, 639, 80, shade=6)
    # plants nobody has watered, at the posts
    for k, (cell, x, y) in enumerate((("landing", 48.95, 43.7), ("landing", 48.95, 46.4), ("walk", 41.45, 43.3))):
        _stand(layout, regions, cell, f"plant_{k}", x, y, 1013, 56, shade=8)


#: who is here: (cell, type, x, y)
FOLK = (("books", 202, 41.1, 41.1), ("draper", 203, 45.4, 41.5), ("court", 203, 48.1, 43.4), ("landing", 202, 49.6, 46.9))
#: what is here
FINDS = (("bay", 65, 45.1, 47.05), ("draper", 62, 42.6, 42.0), ("court", 109, 42.3, 44.4))


def populate(layout, attested) -> dict:
    """The few who are here already, and what lies about; the rest come when the key is taken (`gameplay`)."""
    import ambience
    regions = {cell: f"{KEY}:{cell}" for cell in LEVELS}
    placed = 0
    for k, (cell, kind, x, y) in enumerate(FOLK + FINDS):
        spec = attested(kind)
        if spec is None:
            continue
        xs, ys = zip(*layout.regions[regions[cell]].outer)
        local = ((_q(x) - min(xs)) / (max(xs) - min(xs)), (_q(y) - min(ys)) / (max(ys) - min(ys)))
        layout.place_on_floor(f"mall:{cell}_{kind}_{k}", regions[cell], local=local, **spec["fields"])
        placed += 1
    return {"placed": placed, "ambience": ambience.fill(layout, [
        (regions["walk"], "mall", (0.3, 0.6)), (regions["court"], "mall", (0.4, 0.2)),
        (regions["landing"], "mall", (0.8, 0.3)), (regions["draper"], "mall", (0.5, 0.5))])["placed"]}
