"""Gallows Steps: the old block west of the well square, opened and raised: a stair out of the dead end alley, a terrace over the crossroads, the parish's gallows on it.

The owner, 2026-11-25: "About that unused building (solid city blocks) it can be
even reshaped to whatever you would like and added something interesting there.
Also we can make the city less flat and have some things in different floors -
similar to what they did in E3M1", and "sometimes negative space can also be
useful". What was there: a brick hulk the streets went round.

The parish is St Gallow's: the gallows stood on the hill over its crossroads
before there was a town round it. The alley that ended in a wall climbs ten
steps to a paved terrace two and a half bodies over the streets, open on two
sides over a knee-high parapet (E3M1's terraces are 1.2 and 3.9 bodies up,
TEDE1M7's 1.2 with a sloped parapet, TEDE1M1's 2.8). On it stands one thing. From
the streets it is a silhouette against the red sky and whoever keeps it shoots
down; from it the whole of the Old Crossing is under you. No sector lies over
another: the terrace is the ground there.
One `bloodmap.arrangement`, joined to the streets along the block's own edge.
"""

from __future__ import annotations

import math

from bloodmap import arrangement as A

PU = 1024
KEY = "region:gravesend/old_crossing/gallows"
GRADE, SKY_Z, SKY = 8192, -188416, 3491
RISER, STEPS = 4096, 10
TOP = GRADE - RISER * STEPS                              # -32768: 2.4 bodies over the street
PARAPET = 5632                                          # a third of a body: seen and shot over, jumped onto
#: plan units
ALLEY = (8.0, 10.0, 29.0)                               # the alley's walls and its end
STAIR_TO = 34.0
BLOCK = (8.0, 24.0, 15.0, 35.0)                         # what is opened of the block: the rest stands
RAIL = 0.25
DAIS, DAIS_R = (12.45, 32.4), (1.7, 1.35)               # the gallows' two steps
POSTS, POST, POST_TALL = (11.45, 13.45), 0.16, 46000    # on the line y = DAIS[1]
HOUSE = (3.75, 30.0, 7.5, 34.5)
DOOR = (7.5, 34.05, 8.0, 34.75)
HOUSE_TOP = 27648
SILL, HEAD = 9216, 22528
WINDOWS = {"w": (3.0, 31.4, 3.75, 32.9), "s": (4.8, 34.5, 6.3, 35.0)}
RUBBLE, PAVING, COPING, STONE, TIMBER, BOARDS, PLASTER, BRICK = 110, 4, 253, 253, 28, 67, 379, 90


def _q(v: float) -> int:
    return round(v * PU)


def _rect(x0, y0, x1, y1):
    return [(_q(x0), _q(y0)), (_q(x1), _q(y0)), (_q(x1), _q(y1)), (_q(x0), _q(y1))]


def _block(layout):
    """The hole the block is in the streets, and the street regions round it."""
    from shapely import Point, Polygon
    inside = Point(_q(12), _q(32))
    for region in layout.regions.values():
        for hole in region.holes:
            shape = Polygon(hole)
            if shape.contains(inside) and shape.area > (8 * PU) ** 2:
                return shape
    raise ValueError("the block the gallows stand in is not a hole in any street")


def plan(shape) -> list:
    """Every cell. `shape` is the block as the streets leave it (its corners are cut)."""
    from shapely import Polygon, box

    def ring(polygon):
        if polygon.geom_type != "Polygon":
            polygon = max((g for g in polygon.geoms if g.geom_type == "Polygon"), key=lambda g: g.area)
        return [(round(x), round(y)) for x, y in polygon.exterior.coords][:-1]

    place = A.Arrangement()
    # the terrace: the corner over the crossroads, and a walk behind the well square
    corner = Polygon(_rect(ALLEY[1], 30.0, 15.5, 35.5)).intersection(shape)
    walk = Polygon(_rect(10.75, 24.0, 13.5, 30.0)).intersection(shape)
    head = Polygon(_rect(8.0, STAIR_TO, ALLEY[1], 35.5)).intersection(shape)
    ground = corner.union(walk).union(head)
    place.add("terrace", ring(ground))
    # the parapet stands inside the edge over the streets and over the stair, not where the stair comes up
    inner = ground.buffer(-_q(RAIL), join_style=2)
    rim = ground.difference(inner).intersection(box(_q(8.0), _q(24.0), _q(16), _q(36)))
    rim = rim.difference(box(_q(7.0), _q(33.0), _q(ALLEY[1]) - 1, _q(35) - _q(RAIL)))      # the head of the stair and the door
    rim = rim.difference(box(_q(10.0), _q(23), _q(11.0), _q(30.0)))                        # the walk's back is a wall
    rim = rim.difference(box(_q(10.5), _q(23), _q(13.5), _q(24.0) + _q(RAIL)))             # and its end
    pieces = [g for g in getattr(rim, "geoms", [rim]) if g.geom_type == "Polygon" and g.area > 30_000]
    for k, piece in enumerate(sorted(pieces, key=lambda g: (g.bounds[0], g.bounds[1]))):
        place.add(f"parapet_{k}", ring(piece))
    for k in range(STEPS):
        y = ALLEY[2] + k * 0.5
        place.add(f"step_{k + 1}", _rect(ALLEY[0], y, ALLEY[1], y + 0.5))
    for k, radius in enumerate(DAIS_R, 1):
        place.add(f"dais_{k}", A.circle((_q(DAIS[0]), _q(DAIS[1])), _q(radius), 8, 1 / 16))
    for k, x in enumerate(POSTS):
        place.add(f"post_{k}", _rect(x - POST / 2, DAIS[1] - POST / 2, x + POST / 2, DAIS[1] + POST / 2))
    # the hangman's house, at the terrace's level: one room, a door, two windows over the streets
    place.add("house", _rect(*HOUSE))
    place.add("door", _rect(*DOOR))
    for name, (x0, y0, x1, y1) in WINDOWS.items():
        place.add(f"window_{name}", ring(Polygon(_rect(x0, y0, x1, y1)).intersection(shape)))
    return place.resolve()


def kind(cell: str) -> str:
    return cell.split("_")[0]


def levels(cell: str) -> tuple[int, int, bool]:
    """Floor, ceiling, under the sky."""
    what, *rest = cell.split("_")
    if what == "step":
        return GRADE - RISER * int(rest[0]), SKY_Z, True
    if what == "parapet":
        return TOP - PARAPET, SKY_Z, True
    if what == "dais":
        return TOP - 3072 * int(rest[0]), SKY_Z, True
    if what == "post":
        return TOP - 6144 - POST_TALL, SKY_Z, True
    if what == "house":
        return TOP, TOP - HOUSE_TOP, False
    if what == "door":
        return TOP, TOP - 21504, False
    if what == "window":
        return TOP - SILL, TOP - HEAD, False
    return TOP, SKY_Z, True


def build(layout) -> dict[str, str]:
    """Open the block: lay the terrace, the stair and the house, and join them to the streets they look over."""
    shape = _block(layout)
    cells = plan(shape)

    def surface(name):
        floor, ceiling, sky = levels(name)
        what = kind(name)
        tiles = {"step": (STONE, RUBBLE), "parapet": (COPING, RUBBLE), "dais": (STONE, STONE), "post": (BOARDS, TIMBER),
                 "house": (BOARDS, PLASTER), "door": (BOARDS, TIMBER), "window": (TIMBER, TIMBER)}.get(what, (PAVING, RUBBLE))
        return dict(floor_z=floor, ceiling_z=ceiling, floor_picnum=tiles[0], wall_picnum=tiles[1],
                    ceiling_picnum=SKY if sky else BOARDS, parallax_ceiling=sky, layer="street",
                    floor_shade=12 if sky else 20, wall_shade=14 if sky else 18, ceiling_shade=0 if sky else 24,
                    role="exterior" if what in ("terrace", "step") else "interior" if what == "house" else "detail",
                    declared_zero_exit=True, intent={"kind": "furnished"})

    def face(seen, beyond, _a, _b):
        there = kind(beyond) if beyond else None
        if there == "post":
            return {"picnum": TIMBER}
        if there in ("dais", "step"):
            return {"picnum": STONE}
        if there == "parapet" or kind(seen) == "parapet":
            return {"picnum": RUBBLE}
        if there in ("window", "door"):
            return {"picnum": PLASTER if kind(seen) == "house" else RUBBLE}
        if there is None and kind(seen) in ("terrace", "step"):
            return {"picnum": BRICK}                       # the rest of the block stands over it, the street's brick
        return {}

    regions = A.lay(layout, KEY, cells, surface, face)
    _join(layout, regions, cells, shape)
    _furnish(layout, regions)
    return regions


def _join(layout, regions, cells, shape) -> None:
    """Every edge of a cell that lies on the block's own edge opens on the street beyond it, but the windows' and the house's sides."""
    from shapely import Point, Polygon
    streets = [(r.region_id, Polygon(r.outer, r.holes), r) for r in layout.regions.values()
               if r.parallax_ceiling and r.floor_z == GRADE and not r.region_id.startswith(KEY)]
    edge = shape.exterior
    for name, a, b in A.rim(cells):
        if kind(name) not in ("terrace", "parapet", "step", "window"):
            continue
        middle = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if edge.distance(Point(middle)) > 2 or edge.distance(Point(a)) > 2 or edge.distance(Point(b)) > 2:
            continue
        length = math.dist(a, b)
        # a cell lies on its edge's right: the street on its left
        out = ((b[1] - a[1]) / length, -(b[0] - a[0]) / length)
        point = Point(middle[0] + out[0] * 40, middle[1] + out[1] * 40)
        street = next((rid for rid, polygon, _r in streets if polygon.contains(point)), None)
        if street is None:
            continue
        layout.add_connection(f"connection:gallows:{name}:{a[0]}:{a[1]}", street, regions[name], a1=b, a2=a,
                              min_width=1, min_opening=0)


def _stand(layout, regions, cell, name, x, y, tile, size, *, tall=None, seat="floor", z=None, **fields):
    import wallplane
    from bloodmap.placement import seated_z
    room = layout.regions[regions[cell]]
    _w, height, _x, offset = wallplane.art()[tile]
    tall, cstat = tall or size, fields.pop("cstat", 128)
    if z is None:
        z = seated_z(seat=seat, floor_z=room.floor_z, ceiling_z=room.ceiling_z, tile_height=height, y_repeat=tall, y_offset=offset,
                     cstat=cstat, clearance=16)
    return layout.add_sprite(f"gallows:{name}", regions[cell], x=_q(x), y=_q(y), z=z, picnum=tile, x_repeat=size, y_repeat=tall,
                             cstat=cstat, **{"shade": 4, **fields})


def _furnish(layout, regions) -> None:
    """The beam and what hangs from it; a lamp at the stair's head; the house's few things."""
    from bloodmap.placement import drawn_extent
    import wallplane
    beam = TOP - 6144 - POST_TALL + 1024                  # the beam's middle, a little under the posts' tops
    long_ = (POSTS[1] - POSTS[0] + POST + 0.9) * PU
    middle = (POSTS[0] + POSTS[1]) / 2
    for side, dy in (("n", -POST / 2 - 0.012), ("s", POST / 2 + 0.012)):
        layout.add_sprite(f"gallows:beam_{side}", regions["dais_2"], x=_q(middle), y=_q(DAIS[1] + dy), z=beam, picnum=BOARDS,
                          x_repeat=round(long_ / 16), y_repeat=9, angle=1536 if side == "n" else 512,
                          cstat=16 | 128, shade=16, sunk=True)
    layout.add_sprite("gallows:beam_top", regions["dais_2"], x=_q(middle), y=_q(DAIS[1]), z=beam - 1152, picnum=BOARDS,
                      x_repeat=round((POST + 0.06) * PU / 16) or 1, y_repeat=round(long_ / 16), angle=0, cstat=32 | 128, shade=10,
                      sunk=True)
    # three on one beam, no two at one height; their chains reach it
    for k, (dx, tile, size, tall) in enumerate(((-0.62, 690, 64, 72), (0.02, 906, 60, 64), (0.66, 924, 60, 76))):
        _w, height, _x, offset = wallplane.art()[tile]
        top, _bottom = drawn_extent(height, offset, tall, 128)
        layout.add_sprite(f"gallows:hanged_{k}", regions["dais_2"], x=_q(middle + dx), y=_q(DAIS[1]), z=beam - top - 200, picnum=tile,
                          x_repeat=size, y_repeat=tall, cstat=128, shade=14, sunk=True)
    layout.add_sprite("gallows:stain", regions["dais_2"], x=_q(middle), y=_q(DAIS[1] + 0.25), z=TOP - 6144 - 16, picnum=956,
                      x_repeat=64, y_repeat=56, angle=512, cstat=32 | 128, shade=24)
    _stand(layout, regions, "terrace", "lamp_head", 10.75, 34.4, 640, 120)
    _stand(layout, regions, "terrace", "lamp_walk", 12.4, 25.0, 640, 120)
    _stand(layout, regions, "house", "candles", 4.3, 33.6, 580, 64, cstat=384, shade=-128)
    _stand(layout, regions, "house", "hung", 5.6, 32.2, 906, 56, tall=44, seat="ceiling", sunk=True)
    _stand(layout, regions, "house", "straw", 4.4, 30.6, 515, 64, shade=16)
