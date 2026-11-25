"""Gravesend Station's booking hall: what is inside the avenue's portico, from the street's level up a flight to the trains.

The owner, 2026-11-25: "That station side entry probably doesn't make sense any more, it
was the original entry before we made that main one, I would also rework the station
itself a bit ... You can look for stations references like E1M2 for example."

The station had grown back to front. Its tickets, its fare gate and its benches were at
the west end of the platform, behind a roll-up door in a lane; the front on the avenue,
built later, opened on a bare stone box, a bare stair and a bare brick box.

What E1M2's hall (s92) does: 7.7 bodies high and a marble checker floor (294) under it;
two long double benches down its middle (s82 to s87: seats 0.24 bodies up either side of
a back 0.54 up); the business along its sides under a lower roof; a sign over every
way out; red brick and grey. Ours takes those and its own plan:

* on the axis of the portico, the benches and a flight of stairs into the waiting hall
  (`l3_station.HALL`), which is as wide as this one, open to it across the whole end a
  body up, and open on its far side to the platform: one sees the train from the door;
* the roof is an iron one: it rises from the side walls to a strip of glass, on two
  rows of riveted columns;
* west, three barred ticket windows and the office behind them; east, a refreshment
  room's counter and two telephones. Nothing else.

The waiting room off the waiting hall is laid here too, for the sake of its longcase
clock and its hearth. The owner, 2026-11-25: "grandfather clock and telephone booth
shouldn't be just sprite but a made out of sector". Blood's are blocks that stand against
a wall and wear the tile: the clock 512 wide and 24,576 high (E3M2 s193, E2M4 s476), a
telephone 1,024 by 32,768 (E1M2 s181).

Laid by `bloodmap.arrangement`; the arches' gates and the way to the platform are rooms
of the tree (`l3_station`). Design: `references/station-design.md`.
"""

from __future__ import annotations

from bloodmap import arrangement as A
from bloodmap.slope import SlopeSpec
from materials import FACADES
from resolution import GRADE, PU

KEY = "region:gravesend/gravesend_station/booking_hall"
BODY = 16960
#: the platform's level, over the street's
UP = 20480
TOP = GRADE - UP
WEST, EAST, EDGE, SOUTH = 30.5, 40.5, -13.0, -4.5
NAVE = (33.0, 38.0)
GLASS = (33.5, -10.75, 37.5, -5.75)
#: the iron roof: at the side walls, at the glass, and the sky over it; and the waiting hall's flat one
SPRING, CROWN, SKY_Z, HALL_ROOF = GRADE - 81920, GRADE - 110592, GRADE - 122880, TOP - 50176
STAIR, TREADS, TREAD = (34.0, 37.0), 4, 0.4
#: (the owner, 2026-11-25: "On train station I noticed picnum 588 railing ending mid air, we should add some wooden sector there")
NEWEL, NEWEL_RISE = 0.25, 11264
RISER = UP // (TREADS + 1)
#: either side of the middle aisle: seat, back, seat
BENCHES = {"w": (33.9, 34.3, 34.45, 34.85), "e": (36.15, 36.55, 36.7, 37.1)}
BENCH_Y = (-10.0, -6.75)
SEAT, BACK = 4096, 9216
#: before each arch's gate: a doorway a step deep, so that the roll-up gate shows in it and stone over it
PORCH, PORCH_H = 0.25, 40960
COLUMN_X, COLUMN_Y, COLUMN_R = (33.25, 37.75), (-6.0, -8.25, -10.5), 0.16
#: the booking office, its three windows and its way in
OFFICE = (27.75, -10.25, 30.25, -4.75)
WINDOWS = ((-9.9, -9.0), (-8.4, -7.5), (-6.9, -6.0))
WAY = (-5.6, -4.9)
#: the clerks' desk, under the windows
DESK = (29.75, -10.25, 30.25, -5.9)
SILL, WINDOW_H, OFFICE_H = 9216, 17408, 36864
#: the refreshment room: its counter, what is behind it, and the shelf in its back wall
COUNTER, KIOSK, SHELF = (40.5, -10.25, 40.875, -6.25), (40.875, -10.75, 42.5, -5.75), (42.5, -9.75, 42.75, -6.75)
BAR, BAR_HEAD, KIOSK_H, SHELF_UP, SHELF_H = 9216, 28672, 32768, 9216, 12288

#: the arches' gates across its south wall (`l3_station.ARCHES`)
ARCHES = ((32.5, 34.5), (36.5, 38.5))

#: telephones: (x0, y0, x1, y1), a thousand and twenty-four of face to each
PHONES = ((40.0625, -12.75, 40.5, -10.75), (40.0625, -5.75, 40.5, -4.75))
PHONE_H = 32768
#: the waiting room, off the waiting hall: its door, itself, benches along two walls, a table, the clock and the hearth
WDOOR, WAITING = (EAST, -17.0, 40.75, -16.0), (40.75, -18.0, 44.25, -15.0)
WBENCHES, WTABLE = ((41.25, -18.0, 43.75, -17.6), (41.25, -15.4, 43.75, -15.0)), (42.0, -16.75, 42.75, -16.25)
LONGCASE, MOUTH, HEARTH = (44.0625, -17.5, 44.25, -17.0), (44.25, -16.5, 44.375, -15.0), (44.375, -16.5, 45.0, -15.0)
WAIT_H, CLOCK_H, HEARTH_H = 36864, 24576, 26112
RISER_EDGE = 429
CARPET, PLASTER, RUBBLE, LONGCASE_TILE, HEARTH_TILE, FIRE, CHAIR = 300, 109, 414, 720, 142, 3566, 758

CHECK, SLAB, WOOD, PLANK, BOARDS, BRICK, STONE, MEANDER, IRON, RIVETS, ROOF, SOFFIT, LINING = (
    294, 281, 34, 28, 67, 90, 427, 409, 115, 470, 255, 253, 109)
BARS, RAIL, GLOBE, LAMP, CLOCK, TICKETS, ARRIVALS, PHONE = 58, 588, 676, 641, 1165, 943, 431, 645


def _q(v: float) -> int:
    return round(v * PU)


def _rect(x0, y0, x1, y1):
    return [(_q(x0), _q(y0)), (_q(x1), _q(y0)), (_q(x1), _q(y1)), (_q(x0), _q(y1))]


def plan() -> list:
    place = A.Arrangement()
    place.add("aisle_w", _rect(WEST, EDGE, NAVE[0], SOUTH))
    place.add("aisle_e", _rect(NAVE[1], EDGE, EAST, SOUTH))
    place.add("nave", _rect(NAVE[0], EDGE, NAVE[1], SOUTH))
    for k, (x0, x1) in enumerate(ARCHES):
        place.add(f"porch_{k}", _rect(x0, SOUTH - PORCH, x1, SOUTH))
    for k in range(1, TREADS + 1):
        south = EDGE + TREAD * (TREADS - k + 1)
        place.add(f"stair_{k}", _rect(STAIR[0], south - TREAD, STAIR[1], south))
    # a newel each side of the flight: the rail along the edge over it ends in something
    for k, x in enumerate((STAIR[0] - NEWEL, STAIR[1])):
        place.add(f"newel_{k}", _rect(x, EDGE, x + NEWEL, EDGE + NEWEL))
    place.add("glass", _rect(*GLASS))
    for side, (a, b, c, d) in BENCHES.items():
        place.add(f"seat_{side}1", _rect(a, BENCH_Y[0], b, BENCH_Y[1]))
        place.add(f"back_{side}", _rect(b, BENCH_Y[0], c, BENCH_Y[1]))
        place.add(f"seat_{side}2", _rect(c, BENCH_Y[0], d, BENCH_Y[1]))
    place.add("office", _rect(*OFFICE))
    place.add("desk", _rect(*DESK))
    for k, (y0, y1) in enumerate(WINDOWS):
        place.add(f"window_{k}", _rect(OFFICE[2], y0, WEST, y1))
    place.add("way", _rect(OFFICE[2], WAY[0], WEST, WAY[1]))
    place.add("counter", _rect(*COUNTER))
    place.add("kiosk", _rect(*KIOSK))
    place.add("shelf", _rect(*SHELF))
    for k, rect in enumerate(PHONES):
        place.add(f"phone_{k}", _rect(*rect))
    place.add("wdoor", _rect(*WDOOR))
    place.add("waiting", _rect(*WAITING))
    for k, rect in enumerate(WBENCHES):
        place.add(f"wbench_{k}", _rect(*rect))
    place.add("wtable", _rect(*WTABLE))
    place.add("longcase", _rect(*LONGCASE))
    place.add("mouth", _rect(*MOUTH))
    place.add("hearth", _rect(*HEARTH))
    for x in COLUMN_X:
        for y in COLUMN_Y:
            place.solid(A.circle((_q(x), _q(y)), COLUMN_R * PU, 8, 1 / 16))
    return place.resolve()


def _kind(cell: str) -> str:
    return cell.split("_")[0]


#: what each kind of cell is: floor, ceiling, floor tile, ceiling tile, wall tile
LEVELS = {
    "aisle": (GRADE, CROWN, SLAB, ROOF, BRICK), "nave": (GRADE, CROWN, CHECK, RIVETS, STONE),
    "newel": (TOP - NEWEL_RISE, CROWN, WOOD, RIVETS, WOOD),
    "phone": (GRADE - PHONE_H, CROWN, WOOD, ROOF, BRICK),
    "wdoor": (TOP, TOP - 28672, WOOD, WOOD, WOOD), "waiting": (TOP, TOP - WAIT_H, CARPET, BOARDS, PLASTER),
    "wbench": (TOP - 4608, TOP - WAIT_H, WOOD, BOARDS, PLASTER), "wtable": (TOP - 7168, TOP - WAIT_H, WOOD, BOARDS, PLASTER),
    "longcase": (TOP - CLOCK_H, TOP - WAIT_H, WOOD, BOARDS, PLASTER),
    "mouth": (TOP, TOP - HEARTH_H, RUBBLE, RUBBLE, RUBBLE), "hearth": (TOP, TOP - HEARTH_H, RUBBLE, RUBBLE, RUBBLE),
    "glass": (GRADE, SKY_Z, CHECK, None, RIVETS),
    "seat": (GRADE - SEAT, SKY_Z, WOOD, None, RIVETS), "back": (GRADE - BACK, SKY_Z, WOOD, None, RIVETS),
    "office": (GRADE, GRADE - OFFICE_H, WOOD, BOARDS, LINING),
    "window": (GRADE - SILL, GRADE - SILL - WINDOW_H, WOOD, WOOD, WOOD), "way": (GRADE, GRADE - 30720, WOOD, WOOD, WOOD),
    "porch": (GRADE, GRADE - PORCH_H, SLAB, SOFFIT, STONE),
    "desk": (GRADE - SILL, GRADE - OFFICE_H, WOOD, BOARDS, LINING),
    "counter": (GRADE - BAR, GRADE - BAR_HEAD, WOOD, WOOD, WOOD), "kiosk": (GRADE, GRADE - KIOSK_H, WOOD, BOARDS, LINING),
    "shelf": (GRADE - SHELF_UP, GRADE - SHELF_UP - SHELF_H, WOOD, WOOD, WOOD),
}
OPEN_TO_SKY = ("glass", "seat", "back")
WALKED = ("wdoor", "waiting", "porch", "aisle", "nave", "stair", "glass", "office", "way", "kiosk")


def _column(a, b) -> bool:
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    return any(abs(mx - _q(x)) < 200 and abs(my - _q(y)) < 200 for x in COLUMN_X for y in COLUMN_Y)


def _facet(a, b) -> dict:
    """One length of riveted iron to a facet, whatever side it faces."""
    return {"picnum": IRON, "x_repeat": 2, "y_repeat": 8, "x_panning": 0, "y_panning": 0, "cstat": 0}


_PAINTED: list[tuple] = []
_HALL: list[str] = []


def _face(seen: str, beyond: str | None, a, b) -> dict:
    here, there = _kind(seen), _kind(beyond) if beyond else None
    if beyond is None:
        if _column(a, b):
            return _facet(a, b)
        if here in ("nave", "stair", "aisle") and a[1] == b[1] == _q(EDGE):
            return {"picnum": MEANDER if here != "aisle" else STONE}    # over the waiting hall, and the wall it stands on
        return {}
    along = round((abs(a[0] - b[0]) + abs(a[1] - b[1])) / 128)
    if there == "phone":
        if a[1] == b[1]:
            return {"picnum": PLANK, "cstat": 4}
        if a[0] == b[0]:
            # pegged to the aisle's roof, as a wall drawn in two bands is (its roof meets the aisle's exactly, but is another
            # record), and panned so that the tile starts at the block's top
            rows = (GRADE - PHONE_H - CROWN) // 256
            return {"picnum": PHONE, "x_repeat": along, "y_repeat": 8, "x_panning": 0, "y_panning": -rows * 2 % 256, "cstat": 4}
    if there == "longcase":
        if a[0] == b[0]:
            return {"picnum": LONGCASE_TILE, "x_repeat": along, "y_repeat": 8, "x_panning": 0, "y_panning": 0, "cstat": 0}
        return {"picnum": PLANK}
    if there in ("wbench", "wtable", "desk", "newel"):
        return {"picnum": PLANK}
    if {here, there} == {"mouth", "hearth"}:
        return {"over_picnum": HEARTH_TILE, "x_repeat": 16, "y_repeat": 10, "x_panning": 0, "y_panning": 0, "cstat": 16 | 1 | 64,
                "picnum": RUBBLE}
    if there == "porch":
        return {"picnum": STONE}
    if there in ("seat", "back"):
        return {"picnum": PLANK}
    if there == "stair" or here == "stair":
        return {"picnum": RISER_EDGE if a[1] == b[1] else STONE}
    if there in ("window", "way"):
        return {"picnum": BRICK if here == "aisle" else LINING}
    if there == "counter":
        return {"picnum": BRICK if here == "aisle" else LINING}
    if there == "shelf":
        return {"picnum": LINING}
    if there == "glass" or here == "glass":
        return {"picnum": RIVETS}
    return {}


def build(layout, gates: list[str], waiting_hall: str) -> dict[str, str]:
    """Lay the hall between the arches' gates and the waiting hall, and the waiting room off that."""
    cells = plan()
    by_name = {c.name: c for c in cells}
    sky = FACADES["theatre_row"].ceiling

    def inner(name, x):
        ring = by_name[name].outer
        on = [(a, b) for a, b in zip(ring, ring[1:] + ring[:1]) if a[0] == b[0] == _q(x)]
        return max(on, key=lambda e: abs(e[0][1] - e[1][1]))

    slopes = {"aisle_w": SlopeSpec(hinge=inner("aisle_w", NAVE[0]), rise_z=SPRING - CROWN),
              "aisle_e": SlopeSpec(hinge=inner("aisle_e", NAVE[1]), rise_z=SPRING - CROWN)}
    # a telephone stands against the wall under the aisle's slope: its own roof is the aisle's there
    share = (PHONES[0][0] - NAVE[1]) / (EAST - NAVE[1])
    phone_roof = round(CROWN + (SPRING - CROWN) * share)

    def surface(name):
        kind = _kind(name)
        if kind == "stair":
            floor, ceiling, under, over, wall = GRADE - RISER * int(name[-1]), CROWN, SLAB, RIVETS, STONE
        else:
            floor, ceiling, under, over, wall = LEVELS[kind]
        more = {"ceiling_slope": slopes[name]} if name in slopes else {}
        if kind == "phone":
            ceiling = phone_roof
            more = {"ceiling_slope": SlopeSpec(hinge=inner(name, PHONES[0][0]), rise_z=SPRING - phone_roof)}
        if kind in OPEN_TO_SKY:
            over, more = sky, {"parallax_ceiling": True}
        return dict(floor_z=floor, ceiling_z=ceiling, floor_picnum=under, ceiling_picnum=over, wall_picnum=wall,
                    floor_shade=14, ceiling_shade=20, wall_shade=14, layer="street",
                    role="interior" if kind in WALKED else "detail", declared_zero_exit=True, intent={"kind": "furnished"}, **more)

    _PAINTED.clear()

    def face(seen, beyond, a, b):
        paint = _face(seen, beyond, a, b)
        if paint:
            _PAINTED.append((f"{KEY}:{seen}", a, b, dict(paint)))
        return paint

    regions = A.lay(layout, KEY, cells, surface, face)
    for k, gate in enumerate(gates):
        xs = [p[0] for p in layout.regions[gate].outer]
        for name, a, b in A.rim(cells):
            if a[1] == b[1] == _q(SOUTH):
                x0, x1 = max(min(a[0], b[0]), min(xs)), min(max(a[0], b[0]), max(xs))
                if x1 - x0 > 64:
                    layout.add_connection(f"connection:booking_gate_{k}_{name}", gate, regions[name], a1=(x0, _q(SOUTH)),
                                          a2=(x1, _q(SOUTH)), min_width=1, min_opening=0, gated=True)
    for name, a, b in A.rim(cells):
        if a[1] == b[1] == _q(EDGE) or (_kind(name) == "wdoor" and a[0] == b[0] == _q(EAST)):
            layout.add_connection(f"connection:booking_{name}_{a[0]}", waiting_hall, regions[name], a1=b, a2=a, min_width=1, min_opening=0)
        if _kind(name) == "newel" and a[1] == b[1] == _q(EDGE):
            layout.paint_wall(waiting_hall, b, a, picnum=PLANK)
    _HALL.append(waiting_hall)
    _furnish(layout, regions)
    return regions


def keep(level, compiled) -> int:
    """Put back the risers, bands and columns the city's later passes took for openings."""
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


#: chain lamps between the columns: x, y, how far over the floor
LAMPS = tuple((x, y, 48000) for x in COLUMN_X for y in (-7.12, -9.38))
#: and under the aisles' roofs, before the windows and the counter: smaller, lower
SIDE_LAMPS = tuple((cell, x, y, 37000) for cell, x in (("aisle_w", 31.35), ("aisle_e", 39.65)) for y in (-6.1, -8.2, -10.6))
#: round glass on the flat roofs: cell, x, y
GLOBES = (("office", 29.0, -7.5), ("kiosk", 41.7, -8.25))


def _furnish(layout, regions) -> None:
    import wallplane
    from bloodmap import flatsprite
    from bloodmap.placement import drawn_extent, seated_z
    from shapely.geometry import Point, Polygon

    art = wallplane.art()

    def put(name, cell, x, y, tile, size, *, seat="floor", up=0, cstat=128, **fields):
        room = layout.regions[regions[cell]]
        _w, tall, _x, offset = art[tile]
        xr, yr = size if isinstance(size, tuple) else (size, size)
        z = seated_z(seat=seat, floor_z=room.floor_z, ceiling_z=room.ceiling_z, tile_height=tall, y_repeat=yr, y_offset=offset,
                     cstat=cstat, clearance=16) - up
        return layout.add_sprite(f"station:{name}", regions[cell], x=_q(x), y=_q(y), z=z, picnum=tile, x_repeat=xr, y_repeat=yr,
                                 cstat=cstat, **{"type": 0, "status": 0, "shade": 4, **fields})

    def bill(name, cell, a, b, tile, size, high, *, t=0.5, shade=4, **more):
        return wallplane.sprite(layout, f"station:{name}", regions[cell], (_q(a[0]), _q(a[1])), (_q(b[0]), _q(b[1])), tile=tile,
                                x_repeat=size, y_repeat=size, cstat=16 | 64 | 128, t=t, height_player_heights=high,
                                offset_player_widths=0.04, shade=shade, **more)

    def over(name, cell, a, b, tile, size, z, *, t=0.5, shade=-8):
        """A thing hung over an opening: where its middle is, in the world's z."""
        room = layout.regions[regions[cell]]
        layout.place_on_wall(f"station:{name}", regions[cell], a1=(_q(a[0]), _q(a[1])), a2=(_q(b[0]), _q(b[1])), t=t,
                             height_player_heights=(room.floor_z - z) / BODY, offset_player_widths=0.04, picnum=tile, x_repeat=size,
                             y_repeat=size, cstat=16 | 64 | 128, type=0, status=0, shade=shade, spans_opening=True)

    # over the stair: the clock, under it the name
    top = TREADS
    over("hall_clock", f"stair_{top}", (STAIR[0], EDGE), (STAIR[1], EDGE), CLOCK, 100, HALL_ROOF - 23000, shade=-64)
    # when the trains go, either side of the flight, on the wall the gallery stands on
    for side, x0, x1 in (("w", NAVE[0] - 2.0, NAVE[0]), ("e", NAVE[1], NAVE[1] + 2.0)):
        bill(f"hall_board_{side}", f"aisle_{side}", (x0, EDGE), (x1, EDGE), ARRIVALS, 80, 0.72, shade=-4, spans_opening=True)
    # the ticket windows: the board over the middle one, bars in each
    over("tickets", "aisle_w", (WEST, WINDOWS[1][1]), (WEST, WINDOWS[1][0]), TICKETS, 64, GRADE - SILL - WINDOW_H - 6200)
    for k, (y0, y1) in enumerate(WINDOWS):
        layout.add_sprite(f"station:ticket_bars_{k}", regions[f"window_{k}"], x=_q((OFFICE[2] + WEST) / 2), y=_q((y0 + y1) / 2),
                          z=GRADE - SILL - WINDOW_H // 2, picnum=BARS, x_repeat=round((y1 - y0) * PU / 16), y_repeat=WINDOW_H // 256,
                          angle=0, cstat=16 | 128 | 1, shade=6)
    put("office_lantern", "office", 28.1, -9.6, 693, 40, shade=-128)
    put("office_clerk", "office", 29.2, -7.95, 2333, 44, cstat=128)
    for k, (tile, y, size) in enumerate(((1167, -9.45, 36), (1167, -7.7, 40), (743, -6.6, 36), (606, -8.8, 36))):
        put(f"desk_{k}", "desk", 30.0, y, tile, size, cstat=128 | 32 if tile != 606 else 385)
    put("office_sack_0", "office", 28.2, -5.4, 822, 44, cstat=385)
    put("office_sack_1", "office", 28.6, -5.2, 822, 40, cstat=385)
    # refreshments
    wallplane.text(layout, "sign:station_refreshments", regions["aisle_e"], (_q(EAST), _q(COUNTER[1])), (_q(EAST), _q(COUNTER[3])),
                   words="REFRESHMENTS", style=wallplane.style("fascia", size=84, palette=5, shade=-60),
                   height_player_heights=(BAR_HEAD + 7000) / BODY, over_steps=True, required=True)
    for k, (tile, y) in enumerate(((759, -9.4), (606, -9.0), (605, -8.6), (759, -8.1), (606, -7.6), (605, -7.2))):
        put(f"bar_bottle_{k}", "shelf", 42.62, y, tile, 40, cstat=385)
    for k, (tile, y) in enumerate(((606, -9.7), (759, -7.0))):
        put(f"bar_glass_{k}", "counter", 40.68, y, tile, 40, cstat=385)
    put("barman", "kiosk", 41.5, -7.0, 2334, 44, cstat=128)
    # the bills
    for k, (tile, y) in enumerate(((440, -11.6), (981, -10.75))):
        bill(f"hall_bill_{k}", "aisle_w", (WEST, y + 0.5), (WEST, y - 0.5), tile, 44, 1.25)
    # the rail along the waiting hall's edge, either side of the flight (588, solid and seen from both sides)
    for side, x0, x1 in (("w", WEST, STAIR[0]), ("e", STAIR[1], EAST)):
        for k in range(2):
            x = x0 + (x1 - x0) * (k + 0.5) / 2
            layout.add_sprite(f"station:hall_rail_{side}{k}", _HALL[-1], x=_q(x), y=_q(EDGE) - 24, z=TOP - 5200, picnum=RAIL,
                              x_repeat=round((x1 - x0) / 2 * PU / 32), y_repeat=44, angle=512, cstat=16 | 128 | 1, shade=8)
    for k, (x, y, up) in enumerate(LAMPS):
        _w, tall, _x, offset = art[LAMP]
        _top, bottom = drawn_extent(tall, offset, 124, 0)
        layout.add_sprite(f"station:hall_lamp_{k}", regions["nave"], x=_q(x), y=_q(y), z=GRADE - up - bottom, picnum=LAMP, x_repeat=112,
                          y_repeat=124, cstat=0, shade=-128, sunk=True)
    for k, (cell, x, y, up) in enumerate(SIDE_LAMPS):
        _w, tall, _x, offset = art[LAMP]
        _top, bottom = drawn_extent(tall, offset, 96, 0)
        layout.add_sprite(f"station:side_lamp_{k}", regions[cell], x=_q(x), y=_q(y), z=GRADE - up - bottom, picnum=LAMP, x_repeat=72,
                          y_repeat=96, cstat=0, shade=-128, sunk=True)
    for k, (cell, x, y) in enumerate(GLOBES):
        put(f"hall_globe_{k}", cell, x, y, GLOBE, 40, seat="ceiling", cstat=168, shade=-128)
    # the glazing bars against the sky (the arcade's lantern)
    for k, piece in enumerate(flatsprite.cover((_q(GLASS[0]), _q(GLASS[1]), _q(GLASS[2]), _q(GLASS[3])), art[1060][:2])):
        under = next(r for c, r in regions.items() if _kind(c) in OPEN_TO_SKY
                     and Polygon(layout.regions[r].outer, layout.regions[r].holes).contains(Point(piece["x"], piece["y"])))
        layout.add_sprite(f"station:glazing_{k}", under, x=piece["x"], y=piece["y"], z=CROWN - 512, picnum=1060,
                          x_repeat=piece["x_repeat"], y_repeat=piece["y_repeat"], cstat=32 | 128, angle=piece["angle"], shade=24)
    # the waiting room: what burns in its hearth, a lamp on its chain, two chairs at the table
    layout.add_sprite("station:hearth_fire", regions["hearth"], x=_q((HEARTH[0] + HEARTH[2]) / 2), y=_q((HEARTH[1] + HEARTH[3]) / 2),
                      z=seated_z(seat="floor", floor_z=TOP, ceiling_z=TOP - HEARTH_H, tile_height=art[FIRE][1], y_repeat=36,
                                 y_offset=art[FIRE][3], cstat=128, clearance=16),
                      picnum=FIRE, x_repeat=48, y_repeat=36, cstat=128, shade=-128, type=0, status=0)
    layout.add_sprite("station:wait_lamp", regions["waiting"], x=_q(41.4), y=_q(-16.5), z=TOP - 28500, picnum=LAMP, x_repeat=48,
                      y_repeat=48, cstat=0, shade=-128, type=0, status=0, sunk=True)
    import props
    for k, (local, angle) in enumerate((((0.22, 0.5), 0), ((0.68, 0.5), 1024))):
        props.stand_on_floor(layout, f"station:wait_chair_{k}", regions["waiting"], local=local, tile=CHAIR, angle=angle)
    put("wait_bottle", "wtable", 42.4, -16.5, 759, 40, cstat=385)
    # somebody's bag, and somebody
    put("hall_dead", "nave", 35.6, -5.6, 2333, 48, cstat=128)
    import ambience
    layout.add_sprite("station:hall_hum", regions["nave"], x=_q(35.5), y=_q(-11.0), z=GRADE - 20000, **ambience.fields("interior"))
