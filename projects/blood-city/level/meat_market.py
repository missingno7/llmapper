"""The market hall, a meat market: an aisle of hung carcasses from the street door to a shut cold store, the clerk's gallery over it; and the street stalls.

The owner, 2026-11-25, of the pavement in front of it: "some random wooden
blocks which probably supposed to represent something but it doesn't look like
anything". They were three bare platforms; two stalls stand there now, each a
counter under a striped canopy, as DWE3M10's promenade stands them (sectors
286 and 287: a half-body counter, a roof of sprites).

The hall was a supermarket of two shelf banks with armor in it and nobody. It
is played so: the meat hangs in two files from the door to the steel door of
the cold store; the butcher is behind his counter, the clerk shoots from the
gallery over the shelves. The stair to the gallery starts in the porters'
lobby, the lever up there raises the steel door, and what was shut in with the
meat comes out. At the back of it lies the armor, and taking that brings two
of the hung down off their hooks.

Study: `knowledge/blood/studies/meat-market`. Design: `references/market-design.md`.
"""

from __future__ import annotations

from bloodmap import wiring
from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Style

import wires

PU = 1024
BODY = 16960
GRADE = 8192
HALL_CLEAR = 49152
#: E1M3 s305, the freezer: its floor, its ceiling, its walls; E3M2's steel door
COLD = {"floor_picnum": 315, "ceiling_picnum": 255, "wall_picnum": 345,
        "floor_shade": 34, "ceiling_shade": 40, "wall_shade": 30}
COLD_STEP, COLD_CLEAR, COLD_DOOR, COLD_OPEN = 4096, 32768, 495, 28672
#: plan units: the hall, the nook behind the north window (a rectangle of its own: `windows.cut_through` wants one,
#: and cuts the west lane's window in it), the cold store, its door, the porters' lobby
HALL = (6.5, 40.5, 13.5, 48.0)
NOOK = (3.5, 40.5, 6.5, 42.5)
COLD_STORE = (3.5, 42.75, 6.0, 47.75)
DOOR = (6.0, 44.5, 6.5, 46.5)
LOBBY = (3.5, 48.0, 8.0, 49.5)
#: the stair up from the lobby: five treads, and the gallery is the sixth riser; three rows of 2027's shelf stand under it
TREADS, TREAD, RISER = 5, 0.3125, 4096
GALLERY = (8.0 + TREADS * TREAD, 48.0, 13.5, 49.5)
GALLERY_RISE = 24576
SHELVES = 2027
#: the butcher's counter; behind it he has the window at his back
COUNTER = (8.5, 42.0, 11.5, 42.75)
#: the two files of carcasses, either side of the way from the street door to the steel one
FILES = (44.15, 46.85)
HOOKS = (7.75, 8.95, 10.15, 11.35, 12.55)
#: E3M2 hangs 1351 at 104 by 88 in a room of four bodies; E1M3 at 40 in one of one and a half; the hall is 2.9
CARCASS, PLUCKED, HANGED = 1351, 1350, 895
BREAKS = {"data_1": 8, "data_4": 2205}                  # E3M2's carcasses, field for field
POOLS = (1417, 1413, 732)
ROOMS: dict = {}


def _q(v: float) -> int:
    return round(v * PU)


def build(hall, *, shop, room) -> dict:
    """The hall's own floor, the cold store, the lobby, the stair and the gallery. `room` is l3_market's room maker."""
    import citytree
    import fixtures
    ROOMS.clear()
    sales = room("supermarket", *HALL, shop, "the market hall: an aisle of hung meat from the street door to the cold store's",
                 clear_height=HALL_CLEAR)
    sales.surfaces(floor_shade=34, ceiling_shade=38)
    nook = room("nook", *NOOK, shop, "the nook behind the hall's north window", clear_height=HALL_CLEAR)
    nook.surfaces(floor_shade=34, ceiling_shade=38)
    hall.connect(nook.face("east"), sales.face("west"), connection_id="connection:nook_hall")
    cold = room("cold_store", *COLD_STORE, shop, "the cold store: a step up, dark, its meat hung at head height")
    cold.surfaces(**COLD, floor_z=GRADE - COLD_STEP, clear_height=COLD_CLEAR)
    door = room("cold_door", *DOOR, shop, "the cold store's steel door: the gallery's lever raises it", role="doorway",
                rk={"type": 600, "door_face": COLD_DOOR, "inherit_finish": "both",
                    "sector_behavior": z_motion_door(
                        GRADE - COLD_STEP, GRADE - COLD_STEP - COLD_OPEN, interaction="remote",
                        rx_id=wires.channel("market:cold-store"), open_time=18)})
    door.surfaces(wall_picnum=COLD_DOOR, floor_picnum=COLD["floor_picnum"], floor_z=GRADE - COLD_STEP, clear_height=0)
    wires.wire("market:cold-store").then(wiring.region(door.region_id))
    hall.connect(door.face("west"), cold.face("east"), connection_id="connection:cold_door_in")
    hall.connect(door.face("east"), sales.face("west"), connection_id="connection:cold_door_out")
    lobby = room("stockroom", *LOBBY, shop, "the porters' lobby: the back door's, and the foot of the gallery's stair")
    lobby.surfaces(wall_picnum=63, clear_height=HALL_CLEAR)    # the hall's roof: no band of it over the mouth
    west = HALL[0]
    hall.connect(sales.face("south", at=(13.5 - (west + LOBBY[2]) / 2) / (13.5 - west), width=_q(LOBBY[2] - west)),
                 lobby.face("north"), connection_id="connection:lobby_hall")
    before = lobby
    for k in range(TREADS):
        left = LOBBY[2] + k * TREAD
        tread = room(f"stair_{k + 1}", left, 48.0, left + TREAD, 49.5, shop, "the stair to the clerk's gallery", role="detail")
        tread.surfaces(floor_picnum=34, floor_z=GRADE - RISER * (k + 1), clear_height=HALL_CLEAR - RISER * (k + 1))
        hall.connect(tread.face("west"), before.face("east"), connection_id=f"connection:gallery_stair_{k}", face_picnum=28)
        hall.connect(tread.face("north"), sales.face("south"), connection_id=f"connection:gallery_stair_side_{k}",
                     face_picnum=28)
        before = tread
    gallery = room("gallery", *GALLERY, shop, "the clerk's gallery over the hall: the lever of the cold store's door")
    gallery.surfaces(floor_picnum=34, floor_z=GRADE - GALLERY_RISE, clear_height=HALL_CLEAR - GALLERY_RISE)
    hall.connect(gallery.face("west"), before.face("east"), connection_id="connection:gallery_stair_top", face_picnum=28)
    hall.connect(gallery.face("north"), sales.face("south"), connection_id="connection:gallery_front", face_picnum=SHELVES)
    fittings = citytree.sub(sales, "meat_fittings", note="the butcher's counter")
    counter = fixtures.place("meat_counter", sales, tuple(_q(v) for v in COUNTER), shop, family="bar", grade=GRADE,
                             host_clear=HALL_CLEAR, connector=hall, into=fittings, wall_picnum=fixtures.BAR_FACE)
    counter.surfaces(floor_shade=0)
    ROOMS.update(sales=sales, nook=nook, cold=cold, door=door, lobby=lobby, gallery=gallery, counter=counter)
    return ROOMS


# ---- what hangs, stands and lies in it ------------------------------------------

def _art(tile: int):
    import wallplane
    return wallplane.art()[tile]


def _hung(layout, name, region, x, y, tile, size, tall, **fields):
    """A thing on a hook: its art's top at the ceiling."""
    from bloodmap.placement import drawn_extent
    _w, height, _x, offset = _art(tile)
    fields = {"cstat": 384, "shade": 4, "type": 416, "status": 4, "behavior": dict(BREAKS), **fields}
    top, _bottom = drawn_extent(height, offset, tall, fields["cstat"])
    return layout.add_sprite(name, region, x=_q(x), y=_q(y), z=layout.regions[region].ceiling_z - top + 16,
                             picnum=tile, x_repeat=size, y_repeat=tall, **fields)


def _flat(layout, name, region, x, y, tile, size=64, **fields):
    return layout.add_sprite(name, region, x=_q(x), y=_q(y), z=layout.regions[region].floor_z - 16, picnum=tile,
                             cstat=32 | 128 | 256, x_repeat=size, y_repeat=size, **{"shade": 8, "type": 0, "status": 0, **fields})


def _stand(layout, name, region, x, y, tile, size, **fields):
    from bloodmap.placement import seated_z
    _w, height, _x, offset = _art(tile)
    r = layout.regions[region]
    fields = {"cstat": 385, "shade": 8, "type": 0, "status": 0, **fields}
    z = seated_z(seat="floor", floor_z=r.floor_z, ceiling_z=r.ceiling_z, tile_height=height, y_repeat=size, y_offset=offset,
                 cstat=fields["cstat"], clearance=0)
    return layout.add_sprite(name, region, x=_q(x), y=_q(y), z=z, picnum=tile, x_repeat=size, y_repeat=size, **fields)


def spawn(layout, name, what, region, x, y):
    """A marker that puts a foe there when its wire fires (type 18)."""
    return layout.add_sprite(name, region, x=_q(x), y=_q(y), z=layout.regions[region].floor_z - 4096, type=18, picnum=2077,
                             shade=-128, cstat=32896, status=0, behavior={"data_1": what, "trigger_once": 1})


def dress(layout, street: str) -> dict:
    """The meat, the blood under it, the counter, the gallery and its lever, the cold store and what wakes in it; the stalls."""
    import doorswitch
    import wallplane
    from bloodmap import motion
    sales, cold, gallery, lobby, counter = (ROOMS[k].region_id for k in ("sales", "cold", "gallery", "lobby", "counter"))
    put = 0
    for f, y in enumerate(FILES):
        for h, x in enumerate(HOOKS):
            turned = (f + h) % 2
            _hung(layout, f"market:file_{f}_{h}", sales, x, y, CARCASS, 84, 68 + 2 * turned, cstat=384 | 4 * turned)
            put += 1
            if (f * 5 + h) % 2 == 0:
                _flat(layout, f"market:pool_{f}_{h}", sales, x, y, POOLS[(f + h // 2) % 3], angle=(h * 300) % 2048)
    for k, u in enumerate((0.15, 0.5, 0.85)):
        _hung(layout, f"market:bird_{k}", counter, COUNTER[0] + u * (COUNTER[2] - COUNTER[0]), 42.35, PLUCKED, 56, 56)
    for k, (u, tile) in enumerate(((0.1, 2073), (0.32, 2074), (0.68, 2075), (0.9, 2073))):
        layout.place_on_floor(f"market:cut_{k}", counter, local=(u, 0.45), picnum=tile, cstat=1, x_repeat=48, y_repeat=48,
                              shade=-8, pal=2, type=416, status=0)
    # E3M2's plank board of tools, on the wall by the steel door; the clock over the window
    wall = (_q(6.5), _q(48.0)), (_q(6.5), _q(42.5))
    for name, tile, size, t, tall in (("saw", 1714, 64, 0.06, 1.2), ("tongs", 1715, 64, 0.15, 1.15), ("axe", 1709, 48, 0.23, 1.2)):
        wallplane.sprite(layout, f"market:tool_{name}", sales, *wall, tile=tile, x_repeat=size, y_repeat=size,
                         cstat=16 | 64 | 128, t=t, height_player_heights=tall, shade=4)
    for k, (x, y) in enumerate(((3.95, 48.5), (4.5, 48.45), (4.0, 49.1))):
        _stand(layout, f"market:barrel_{k}", lobby, x, y, 925, 64)
    # the gallery: a rail along its edge, and the lever at its far end
    a, b = _q(GALLERY[0]) + 256, _q(GALLERY[2])
    for k in range(3):
        wide = (b - a) / 3
        layout.add_sprite(f"market:rail_{k}", gallery, x=round(a + wide * (k + 0.5)), y=_q(48.0) + 24, picnum=588,
                          z=layout.regions[gallery].floor_z - (48 * 2 - 22 * 4) * 40, cstat=16 | 128 | 1, angle=512,
                          x_repeat=round(wide / 32), y_repeat=40, shade=8, type=0, status=0, spans_opening=True)
    wallplane.sprite(layout, "market:manager", gallery, (_q(12.6), _q(49.5)), (_q(10.2), _q(49.5)), tile=751, x_repeat=64,
                     y_repeat=64, cstat=16 | 64 | 128, t=0.5, height_player_heights=1.05, shade=-4)
    lever = doorswitch.place(layout, "market:cold_lever", gallery,
                             ((_q(GALLERY[2]), _q(48.25)), (_q(GALLERY[2]), _q(49.25))),
                             wires.channel("market:cold-store"), command=motion.CMD_ON)
    wires.wire("market:cold-store").when(wiring.placement(lever), "push", command=motion.CMD_ON, on=True, off=True, once=True)
    put += _cold_store(layout, cold, sales)
    return {"hung": put, "stalls": _dress_stalls(layout, street)}


def _cold_store(layout, cold, sales) -> int:
    from bloodmap import motion
    put = 0
    sizes = {CARCASS: (64, 44), HANGED: (40, 40), PLUCKED: (52, 52)}
    for k, (x, y, tile) in enumerate(((4.2, 43.2, CARCASS), (5.3, 43.4, CARCASS), (4.2, 44.5, HANGED), (5.35, 44.4, CARCASS),
                                      (4.1, 45.9, CARCASS), (5.4, 46.6, HANGED), (4.75, 47.2, PLUCKED))):
        fields = {"type": 0, "status": 0, "behavior": {}, "shade": 10} if tile == HANGED else {}
        _hung(layout, f"market:cold_{k}", cold, x, y, tile, *sizes[tile], **fields)
        put += 1
        if k in (0, 2, 4):
            _flat(layout, f"market:cold_pool_{k}", cold, x, y, POOLS[k // 2])
        if k in (1, 3, 4):
            # E1M3 drips its freezer's blood (type 702); built running, on no wire
            layout.add_sprite(f"market:drip_{k}", cold, x=_q(x), y=_q(y), z=layout.regions[cold].ceiling_z + 24000, type=702,
                              picnum=0, cstat=32896, shade=-8, status=0,
                              behavior={"state": 1, "busy_time": 20, "wait_time": 7, "data_1": 5})
    armor = _stand(layout, "market:armor", cold, 4.2, 46.9, 2628, 64, cstat=128, shade=-8, type=140, status=3)
    taken = wires.wire("market:armor")
    taken.when(wiring.placement(armor), "pickup", command=motion.CMD_ON, once=True)
    for k, (what, region, x, y) in enumerate(((203, cold, 4.2, 44.6), (203, cold, 5.4, 46.5), (204, sales, 8.0, 45.5))):
        taken.then(wiring.placement(spawn(layout, f"market:wakes_{k}", what, region, x, y)))
    return put


# ---- the street stalls ----------------------------------------------------------

#: (name, the counter's west end and its front edge in plan units, what lies on it, what hangs over it, barrels beside it)
STALLS = (
    ("butcher", 17.0, 49.0, ((2073, 0.15), (2074, 0.4), (2139, 0.62), (2075, 0.85)), (PLUCKED, PLUCKED, PLUCKED),
     ((19.75, 48.7),)),
    ("grocer", 17.0, 42.0, ((616, 0.1), (604, 0.28), (834, 0.46), (802, 0.64), (605, 0.82)), (),
     ((16.4, 41.3), (16.3, 41.75), (19.7, 41.6))),
)
COUNTER_WIDE, COUNTER_DEEP, COUNTER_RISE = 2048, 640, 8192
#: the canopy over it: wider and deeper than the counter, two bodies up
CANOPY_WIDE, CANOPY_DEEP, CANOPY_UP = 2560, 1536, 33792
STRIPE, POLE, BOARDS = 1004, 117, 170
#: a flat roof stops a body and a bullet, as 251 of Blood's 312 do (the owner: "roofs of stands aren't solid/blocking even they should be")
SOLID = 1 | 256
STALL_ROOMS: dict = {}


def build_stalls(plaza, district, market_st, island, sky_tile, sky_clear: int) -> list:
    """The stalls' counters, cut into the plaza. `island` is l3_market's."""
    STALL_ROOMS.clear()
    for name, x, y, *_rest in STALLS:
        x1, y1 = _q(x), _q(y)
        STALL_ROOMS[name] = island(
            plaza, district, market_st, f"stall_{name}", x0=x1, y0=y1 - COUNTER_DEEP, x1=x1 + COUNTER_WIDE, y1=y1,
            floor_z=GRADE - COUNTER_RISE,
            style=Style(floor_picnum=34, wall_picnum=84, ceiling_picnum=sky_tile, parallax_ceiling=True,
                        floor_z=GRADE - COUNTER_RISE, clear_height=sky_clear - COUNTER_RISE, floor_shade=20),
            note=f"a street stall: the {name}'s counter, half a body high")
    return list(STALL_ROOMS.values())


def _dress_stalls(layout, street: str) -> int:
    """Poles, the striped canopy with its valance, the boards at the back, and what is sold."""
    import goods
    from bloodmap import flatsprite
    put = 0
    for name, wx, wy, sold, hung, barrels in STALLS:
        counter = STALL_ROOMS[name].region_id
        middle, front = _q(wx) + COUNTER_WIDE // 2, _q(wy) + 256
        x0, x1, y0, y1 = middle - CANOPY_WIDE // 2, middle + CANOPY_WIDE // 2, front - CANOPY_DEEP, front
        roof = GRADE - CANOPY_UP
        cx0, cx1, cy0, cy1 = _q(wx), _q(wx) + COUNTER_WIDE, _q(wy) - COUNTER_DEEP, _q(wy)

        def add(tag, x, y, z, **fields):
            fields = {"type": 0, "status": 0, "shade": 12, "cstat": 128, **fields}
            at = counter if cx0 <= x <= cx1 and cy0 <= y <= cy1 else street
            layout.add_sprite(f"stall:{name}_{tag}", at, x=round(x), y=round(y), z=round(z), **fields)
            return 1

        for k, piece in enumerate(flatsprite.cover((x0, y0, x1, y1), _art(STRIPE)[:2])):
            put += add(f"roof_{k}", piece["x"], piece["y"], roof, picnum=STRIPE, angle=piece["angle"], x_repeat=piece["x_repeat"],
                       y_repeat=piece["y_repeat"], cstat=32 | 128 | SOLID, shade=26)
        # the valance, hung from the roof's edge on every side
        for side, (ax, ay), (dx, dy), angle, length in (
                ("south", (x0, y1), (1, 0), 512, CANOPY_WIDE), ("north", (x0, y0), (1, 0), 1536, CANOPY_WIDE),
                ("west", (x0, y0), (0, 1), 1024, CANOPY_DEEP), ("east", (x1, y0), (0, 1), 0, CANOPY_DEEP)):
            count = length // 512
            for k in range(count):
                along = (k + 0.5) * length / count
                put += add(f"valance_{side}_{k}", ax + dx * along, ay + dy * along, roof + 64 * 20 * 2, picnum=STRIPE, angle=angle,
                           x_repeat=64, y_repeat=20, cstat=16 | 128 | 256)
        for k, (px, py) in enumerate(((x0 + 64, y0 + 64), (x1 - 64, y0 + 64), (x0 + 64, y1 - 64), (x1 - 64, y1 - 64))):
            put += add(f"pole_{k}", px, py, GRADE - CANOPY_UP // 2, picnum=POLE, x_repeat=32, y_repeat=CANOPY_UP // 512,
                       cstat=128 | 256 | 1, shade=20)
        # DWE3M10 boards the back of its stand (170)
        put += add("boards", middle, y0 + 96, GRADE - 128 * 40 * 2, picnum=BOARDS, angle=512, x_repeat=64, y_repeat=40,
                   cstat=16 | 128 | 256 | 1, shade=24)
        for k, (tile, u) in enumerate(sold):
            if tile in goods.ASSETS and tile != 2139:
                fields = goods.fields(tile)
            else:
                fields = {"picnum": tile, "cstat": 0, "x_repeat": 44, "y_repeat": 44, "shade": -4,
                          "pal": 2 if 2073 <= tile <= 2076 else 0, "type": 0, "status": 0}
            layout.place_on_floor(f"stall:{name}_sold_{k}", counter, local=(u, 0.5), **fields)
            put += 1
        for k, tile in enumerate(hung):
            put += add(f"hung_{k}", x0 + 640 + k * 640, y1 - 320, roof + _art(tile)[1] * 44 * 2, picnum=tile, x_repeat=44,
                       y_repeat=44, cstat=384, type=416, status=4, behavior=dict(BREAKS), shade=4)
        for k, (bx, by) in enumerate(barrels):
            _stand(layout, f"stall:{name}_barrel_{k}", street, bx, by, 925, 60)
        put += add("lamp", x1 - 64, y1 - 40, GRADE - 21000, picnum=693, x_repeat=36, y_repeat=36, shade=-128)
    return put
