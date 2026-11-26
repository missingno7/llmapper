"""The Toshers' Den: the low timbered room off the settling hall's west quay where the sewer's scavengers slept, and the hoard under one of their beds.

From the study `toshers-den` (E6M7:195's shoring and firelight, DWE2M5:292's hay
and lantern, E3M3:265's beds). It stands where the hall's service lift was (the
owner, 2026-11-25: "that elevator I would probably rework or remove"). Built of
`bloodmap.arrangement`, joined to the quay through a short adit on the line of
the walk between two tanks, so that its light is seen from across the water.

THE TOSHERS' CACHE: E3M3's own secret (sector 264): a bed of straw on boxes that
sinks when it is pushed, and a crawl behind it where its boxes stood.
"""

from __future__ import annotations

from bloodmap import arrangement as A

PU = 1024
KEY = "region:gravesend/sewer/toshers_den/den"
FLOOR = 102400                                            # the quay's
CEILING, BEAM = FLOOR - 26624, FLOOR - 24576              # low: a body and a half
ADIT_TOP = FLOOR - 19456
LOW_BED, BED, BED_TOP = FLOOR - 6144, FLOOR - 10240, FLOOR - 21504   # one box high, and two: that bed is the wrong one
STOVE, HOOD = FLOOR - 8192, FLOOR - 17408
CACHE_FLOOR, CACHE_TOP = FLOOR + 4096, FLOOR - 16384      # a step down, and a crouching body (13,376) under the bed's own height
ADIT = (18.75, 46.0, 20.0, 47.25)                         # on the line of the walk between tanks 2 and 3
ROOM = [(12.75, 43.0), (18.0, 43.0), (18.75, 43.75), (18.75, 48.0), (12.75, 48.0)]
BEAMS = (14.125, 16.6875)
BEAM_WIDE = 0.375
BEDS = {"bed_1": (12.0, 43.125, 12.75, 44.5), "bed_2": (12.0, 44.8125, 12.75, 46.1875), "bed_3": (12.0, 46.5, 12.75, 47.875)}
SECRET = "bed_2"
STOVE_AT = (15.0625, 42.375, 16.0625, 43.0)
CRAWL = (10.875, 45.0, 12.0, 46.0)
CACHE = [(8.75, 44.5), (10.25, 44.0), (10.875, 44.75), (10.875, 46.25), (10.0, 47.0), (8.75, 46.5)]

SHORING, PLANKS, ROOF, OAK, STRAW, BOXES, BOARDED = 172, 178, 21, 169, 514, 562, 170
IRON, OVEN, BRICK = 376, 261, 91
RUBBLE, EARTH, STONE = 110, 270, 253


def _q(v: float) -> int:
    return round(v * PU)


def _rect(x0, y0, x1, y1):
    return [(_q(x0), _q(y0)), (_q(x1), _q(y0)), (_q(x1), _q(y1)), (_q(x0), _q(y1))]


def _ring(points):
    return [(_q(x), _q(y)) for x, y in points]


def plan() -> list:
    place = A.Arrangement()
    place.add("room", _ring(ROOM))
    for k, x in enumerate(BEAMS, 1):
        place.add(f"beam{k}", _rect(x, 43.0, x + BEAM_WIDE, 48.0))
    place.add("adit", _rect(*ADIT))
    for name, rect in BEDS.items():
        place.add(name, _rect(*rect))
    place.add("stove", _rect(*STOVE_AT))
    place.add("crawl", _rect(*CRAWL))
    place.add("cache", _ring(CACHE))
    return place.resolve()


def _kind(cell: str) -> str:
    return cell.rstrip("0123456789").rstrip("_")


def surface(cell: str) -> dict:
    """What a cell is made of."""
    from l3_sewer import HALL_LAYER
    kind = _kind(cell)
    floor, ceiling = {"room": (FLOOR, CEILING), "beam": (FLOOR, BEAM), "adit": (FLOOR, ADIT_TOP), "bed": (BED if cell == SECRET else LOW_BED, BED_TOP),
                      "stove": (STOVE, HOOD), "crawl": (CACHE_FLOOR, BED), "cache": (CACHE_FLOOR, CACHE_TOP)}[kind]
    wall, under, over = {"bed": (SHORING, STRAW, OAK), "stove": (IRON, IRON, IRON), "crawl": (RUBBLE, EARTH, STONE),
                         "cache": (RUBBLE, EARTH, STONE), "beam": (SHORING, PLANKS, OAK)}.get(kind, (SHORING, PLANKS, ROOF))
    more = {}
    if cell == SECRET:
        # E3M3:264, pushed at its boxes; but once, and for good (its own comes back up after four seconds)
        more = {"type": 600, "sector_behavior": {
            "off_floor_z": BED, "on_floor_z": CACHE_FLOOR, "off_ceiling_z": BED_TOP, "on_ceiling_z": BED_TOP,
            "busy_time_a": 12, "busy_time_b": 12, "trigger_wall_push": 1, "trigger_push": 1, "trigger_once": 1,
            "dude_lockout": 1}}
    elif kind in ("crawl", "cache"):
        more = {"secret": kind == "cache", "sector_behavior": {"amplitude": -8, "shade_frequency": 7}}
    return dict(floor_z=floor, ceiling_z=ceiling, wall_picnum=wall, floor_picnum=under, ceiling_picnum=over,
                floor_shade=40, wall_shade=28, ceiling_shade=32, layer=HALL_LAYER, declared_zero_exit=True,
                role="platform" if kind == "bed" else "secret" if kind == "cache" else "interior",
                intent={"kind": "furnished"}, **more)


def face(seen: str, beyond: str | None, a, b) -> dict:
    """The boxes the beds stand on, the stove's door and its chimney, the beams' sides."""
    here, there = _kind(seen), _kind(beyond) if beyond else None
    if there == "bed" and here == "room":
        return {"picnum": OAK, "cstat": 2}               # the lintel is a beam; under the straw the other record's boxes show
    if here == "bed" and there == "crawl":
        return {"picnum": BOARDED}                       # the wrong bed's back is boarded up
    if here in ("bed", "crawl") and there in ("room", "bed"):
        return {"picnum": BOXES}
    if here == "room" and there == "stove":
        return {"picnum": BRICK, "cstat": 2}             # the band under the hood shows the other record's tile: the oven door
    if here == "stove" and there == "room":
        return {"picnum": OVEN}
    if there == "beam" or there == "adit" and here == "room":
        return {"picnum": OAK}
    return {}


def build(layout, quay: str) -> dict[str, str]:
    """Lay the den, joined to the hall's west quay."""
    import l3_sewer
    cells = plan()
    _PAINTED.clear()

    def painted(seen, beyond, a, b):
        paint = face(seen, beyond, a, b)
        if paint:
            _PAINTED.append((f"{KEY}:{seen}", a, b, paint["picnum"]))
        return paint

    regions = A.lay(layout, KEY, cells, surface, painted)
    for name, a, b in A.rim(cells):
        if a[0] == b[0] == _q(ADIT[2]):
            layout.add_connection(f"connection:den:{name}", quay, regions[name], a1=b, a2=a, min_width=1, min_opening=0)
    # the city's door pass would frame a bed that sinks as a door
    l3_sewer.LATE_TYPES[regions[SECRET]] = 600
    layout.regions[regions[SECRET]].type = 0
    _furnish(layout, regions)
    return regions


#: what `build` painted: (region, a, b, tile); `keep` puts it back after the lintel pass
_PAINTED: list[tuple] = []


def keep(disk, compiled) -> int:
    import settling_hall
    return settling_hall.put_back(disk, compiled, _PAINTED)


#: what lies about: (cell, tile, x, y, repeats, cstat, shade, type)
GEAR = (
    ("bed_1", 515, 12.4, 43.6, (44, 44), 32 | 128, 6, 0), ("bed_3", 515, 12.4, 47.2, (48, 44), 32 | 128, 6, 0),
    ("room_0", 515, 13.4, 44.2, (52, 52), 32 | 128, 12, 0),
    ("bed_3", 2333, 12.4, 47.0, (34, 34), 128, 10, 0),                # one of them stayed
    ("room_1", 925, 15.1, 47.6, (48, 48), 128 | 1, 4, 417), ("room_1", 925, 14.75, 47.2, (40, 40), 128 | 1, 8, 417),
)
#: leaned on a wall: (cell, tile, a, b, share along, repeats)
LEANED = (("room_2", 1713, (18.75, 43.75), (18.75, 46.0), 0.42, (40, 44)), ("room_2", 1712, (18.75, 43.75), (18.75, 46.0), 0.62, (44, 44)),
          ("room_1", 1710, (16.6875, 48.0), (14.5, 48.0), 0.7, (44, 44)))
#: brass lanterns: under each beam and, for whoever comes along the quay, in the adit's mouth; the fire in the stove
LANTERNS = (("beam1", 14.3125, 45.5, 52), ("beam2", 16.875, 46.4, 52), ("adit", 19.6, 46.62, 44))
FIRE = ("stove", 15.5625, 42.62)


def _furnish(layout, regions) -> None:
    from bloodmap import wallplane
    from bloodmap.placement import drawn_extent
    from bloodmap.shade_table import _art
    from l3_foundry import _attested
    art = _art()
    breaks = {925: dict(_attested("E1M2", 417, picnum=925)["behavior"])}

    def put(name, cell, tile, x, y, repeats, cstat, shade, *, z=None, **more):
        room = layout.regions[regions[cell]]
        if z is None:
            _top, bottom = drawn_extent(art[tile].height, art[tile].animation["yofs"], repeats[1], cstat)
            z = room.floor_z - 16 if cstat & 32 else room.floor_z - 8 - bottom
        return layout.add_sprite(f"den:{name}", regions[cell], x=_q(x), y=_q(y), z=z, picnum=tile, x_repeat=repeats[0],
                                 y_repeat=repeats[1], cstat=cstat, shade=shade, **more)

    for k, (cell, tile, x, y, repeats, cstat, shade, kind) in enumerate(GEAR):
        more = {"type": kind, "status": 4, "behavior": breaks[tile]} if kind else {}
        put(f"gear_{k}", cell, tile, x, y, repeats, cstat, shade, **more)
    for k, (cell, tile, a, b, t, repeats) in enumerate(LEANED):
        wallplane.sprite(layout, f"den:leaned_{k}", regions[cell], (_q(a[0]), _q(a[1])), (_q(b[0]), _q(b[1])), tile=tile,
                         x_repeat=repeats[0], y_repeat=repeats[1], cstat=208, t=t,
                         height_player_heights=art[tile].height * repeats[1] * 4 / 2 / 16960, shade=8, required=False)
    for k, (cell, x, y, size) in enumerate(LANTERNS):
        top, _bottom = drawn_extent(art[693].height, art[693].animation["yofs"], size, 128)
        put(f"lantern_{k}", cell, 693, x, y, (size, size), 128, -128, z=layout.regions[regions[cell]].ceiling_z + 32 - top)
    cell, x, y = FIRE
    put("fire", cell, 2101, x, y, (48, 40), 128, -128)
