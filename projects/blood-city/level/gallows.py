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
RISER, STEPS = 4096, 10                                 # ten risers: nine treads, and the terrace
TOP = GRADE - RISER * STEPS                              # -32768: 2.4 bodies over the street
PARAPET = 5632                                          # a third of a body: seen and shot over, jumped onto
#: plan units
ALLEY = (8.0, 10.0, 27.0)                               # the alley's walls and its end
STAIR_TO = 31.5                                         # (34 until the owner, 2026-11-25: "move the whole stairs little bit to make more room for door")
BLOCK = (8.0, 24.0, 15.0, 35.0)                         # what is opened of the block: the rest stands
RAIL = 0.25
DAIS, DAIS_R = (12.45, 32.4), (1.7, 1.35)               # the gallows' two steps
POSTS, POST, POST_TALL = (11.45, 13.45), 0.16, 46000    # on the line y = DAIS[1]
HOUSE = (3.75, 30.0, 7.5, 34.5)
#: the house's doorway: a frame of wood set in the wall, and the way in through it, clear of the house's corner on both sides
FRAME, DOOR = (7.875, 32.9, 8.0, 33.8), (7.5, 33.0, 7.875, 33.7)
#: (as tall as the town's other doors: 24,576 of doorway. The owner: "the enterance felt bit lower than usual".)
FRAME_TOP, DOOR_TOP = 26624, 24576
#: what is left of its door. (The owner: "it is just plain hole in the wall ... you can maybe make it like destroyed wooden
#: door", and "for the broken door I would but the door on the floor made out of sector with jagged line".) It lies where it
#: was kicked to, broken across: two slabs a hand thick whose broken ends match, the farther one thrown askew; a splinter of
#: it still stands on the hinges.
BREAK = ((0.0, 0.02), (0.13, -0.09), (0.24, 0.03), (0.36, -0.07), (0.47, 0.06), (0.57, -0.05), (0.66, 0.01))
SLAB = (7.36, 6.5, 33.02)                               # its end at the doorway, its break, its side
THROWN = (-0.2, 0.1, 0.16, 0.42)                        # the farther piece: moved by, turned by (radians), and its length
SLAB_THICK, LEAF_TILE = 1536, 22
STUMP, LEAF_THICK, STUMP_TALL = ((7.42, 33.74), (7.24, 33.86)), 0.07, 13312
HOUSE_TOP = 27648
FRONT = 384                                             # what the block wears to the streets (`facade_pass`): two windows of it are cut in each wall
WINDOWS: dict = {}
#: the shade of the walls beside the stair, from its foot (the alley's own walls are 35) to its head. The owner: "they seem to
#: be much brighter than walls, how is that?" A tread sees the whole strip of sky over the alley and came out at 2 to 19; a
#: wall across two units from another sees next to none, and came out at 43.
SIDE_SHADE = (35, 27)
#: the stair: a tread is worn stone, a riser one course of blocks with a dark joint under its edge
TREAD, RISER_STONE, SILL_BOARD = 4, 429, 20             # the treads are the alley's paving and the terrace's: 253 is 45% lighter than the brick
FLAGS = 281                                             # the house's floor: on boards, a door lying down is one more board
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


def _riser(step: int) -> dict:
    """The face of one step, every one of them alike: a course of blocks at the scale stone is drawn at everywhere, its joints never over the last one's."""
    return {"picnum": RISER_STONE, "x_repeat": 16, "y_repeat": 8, "x_panning": (step * 27) % 64, "y_panning": 0, "cstat": 0}


def _windows(shape) -> dict:
    """The two windows of each of the house's outer walls, where the front is painted with one: {name: (x0, y0, x1, y1) in units}."""
    from facade_bays import windows_on
    ring = [(round(x), round(y)) for x, y in shape.exterior.coords][:-1]
    found = {}
    for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1]):
        if ax == bx == _q(3.0):
            lo, hi = sorted((ay, by))                        # from the north: the left hand as the street faces it
            spans = [(lo + a, lo + b) for a, b in windows_on(hi - lo, FRONT)]
            spans = [s for s in spans if s[0] > _q(HOUSE[1]) + 256 and s[1] < _q(HOUSE[3]) - 256][-2:]
            found.update({f"w{k}": (_q(3.0), a, _q(HOUSE[0]), b) for k, (a, b) in enumerate(spans)})
        if ay == by == _q(35.0) and min(ax, bx) < _q(5.0):
            lo, hi = min(ax, bx), _q(8.0)                    # the front ends where the stair's head opens on the street
            spans = [(lo + a, lo + b) for a, b in windows_on(hi - lo, FRONT)]
            spans = [s for s in spans if s[0] > _q(HOUSE[0]) + 256 and s[1] < _q(HOUSE[2]) - 256][:2]
            found.update({f"s{k}": (a, _q(HOUSE[3]), b, _q(35.0)) for k, (a, b) in enumerate(spans)})
    return found


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
    rim = rim.difference(box(_q(7.0), _q(STAIR_TO) - 1024, _q(ALLEY[1]), _q(35) - _q(RAIL)))      # the head of the stair and the door
    rim = rim.difference(box(_q(10.0), _q(23), _q(11.0), _q(30.0)))                        # the walk's back is a wall
    rim = rim.difference(box(_q(10.5), _q(23), _q(13.5), _q(24.0) + _q(RAIL)))             # and its end
    pieces = [g for g in getattr(rim, "geoms", [rim]) if g.geom_type == "Polygon" and g.area > 30_000]
    for k, piece in enumerate(sorted(pieces, key=lambda g: (g.bounds[0], g.bounds[1]))):
        place.add(f"parapet_{k}", ring(piece))
    for k in range(STEPS - 1):
        y = ALLEY[2] + k * 0.5
        place.add(f"step_{k + 1}", _rect(ALLEY[0], y, ALLEY[1], y + 0.5))
    for k, radius in enumerate(DAIS_R, 1):
        place.add(f"dais_{k}", A.circle((_q(DAIS[0]), _q(DAIS[1])), _q(radius), 8, 1 / 16))
    for k, x in enumerate(POSTS):
        place.add(f"post_{k}", _rect(x - POST / 2, DAIS[1] - POST / 2, x + POST / 2, DAIS[1] + POST / 2))
    # the hangman's house, at the terrace's level: one room, a door, two windows over the streets
    place.add("house", _rect(*HOUSE))
    place.add("frame", _rect(*FRAME))
    place.add("door", _rect(*DOOR))
    place.add("leaf_0", A.band((_q(STUMP[0][0]), _q(STUMP[0][1])), (_q(STUMP[1][0]), _q(STUMP[1][1])), LEAF_THICK * PU))
    end, at, side = SLAB
    wide = BREAK[-1][0]
    place.add("slab_0", [(_q(end), _q(side)), (_q(end), _q(side + wide))] + [(_q(at + x), _q(side + y)) for y, x in reversed(BREAK)])
    dx, dy, turn, long_ = THROWN
    far = [(x, y) for y, x in BREAK] + [(-long_, wide), (-long_, 0.0)]
    place.add("slab_1", [(_q(at + dx + x * math.cos(turn) - (y - wide / 2) * math.sin(turn)),
                          _q(side + dy + wide / 2 + x * math.sin(turn) + (y - wide / 2) * math.cos(turn))) for x, y in far])
    WINDOWS.clear()
    WINDOWS.update(_windows(shape))
    for name, (x0, y0, x1, y1) in WINDOWS.items():
        place.add(f"window_{name}", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
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
    if what == "frame":
        return TOP, TOP - FRAME_TOP, False
    if what == "door":
        return TOP, TOP - DOOR_TOP, False
    if what == "leaf":
        return TOP - STUMP_TALL, TOP - HOUSE_TOP, False
    if what == "slab":
        return TOP - SLAB_THICK, TOP - HOUSE_TOP, False
    if what == "window":
        from facade_bays import rises
        sill, head = rises(FRONT)                           # of the front's second storey, 32,768 over the street
        return GRADE - 32768 - sill, GRADE - 32768 - head, False
    return TOP, SKY_Z, True


def build(layout) -> dict[str, str]:
    """Open the block: lay the terrace, the stair and the house, and join them to the streets they look over."""
    shape = _block(layout)
    cells = plan(shape)

    def surface(name):
        floor, ceiling, sky = levels(name)
        what = kind(name)
        tiles = {"step": (TREAD, RUBBLE), "parapet": (COPING, RUBBLE), "dais": (STONE, STONE), "post": (BOARDS, TIMBER),
                 "house": (FLAGS, PLASTER), "door": (SILL_BOARD, SILL_BOARD), "frame": (SILL_BOARD, SILL_BOARD), "leaf": (SILL_BOARD, SILL_BOARD),
                 "slab": (LEAF_TILE, SILL_BOARD),
                 "window": (TIMBER, TIMBER)}.get(what, (PAVING, RUBBLE))
        return dict(floor_z=floor, ceiling_z=ceiling, floor_picnum=tiles[0], wall_picnum=tiles[1],
                    ceiling_picnum=SKY if sky else BOARDS, parallax_ceiling=sky, layer="street",
                    floor_shade=12 if sky else 20, wall_shade=14 if sky else 18, ceiling_shade=0 if sky else 24,
                    role="exterior" if what in ("terrace", "step") else "interior" if what == "house" else "detail",
                    declared_zero_exit=True, intent={"kind": "furnished"})

    def face(seen, beyond, _a, _b):
        there = kind(beyond) if beyond else None
        if there == "post":
            return {"picnum": TIMBER}
        if there == "step" or (kind(seen) == "step" and there == "terrace"):
            # one course to a riser, and no riser's joints over the next one's
            return _riser(int(beyond.split("_")[1]) if there == "step" else STEPS)
        if there == "leaf":
            return {"picnum": LEAF_TILE, "x_repeat": 1, "y_repeat": 10, "x_panning": 0, "y_panning": 96, "cstat": 0}
        if there == "slab":
            return {"picnum": SILL_BOARD}
        if {kind(seen), there} == {"frame", "door"}:
            return {"picnum": SILL_BOARD}
        if there == "dais":
            return {"picnum": STONE}
        if there == "parapet" or kind(seen) == "parapet":
            return {"picnum": RUBBLE}
        if there in ("window", "door", "frame"):
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
        if name == "step_1":
            layout.paint_wall(street, b, a, fixed_frame=True, **_riser(1))   # the street's own record: the first riser


def _stand(layout, regions, cell, name, x, y, tile, size, *, tall=None, seat="floor", z=None, **fields):
    from bloodmap import wallplane
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
    from bloodmap import wallplane
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
    # boards that were nailed across it, and what came down with the door
    for k, (dy, up, long_) in enumerate(((0.0, 19400, 60), (0.11, 15600, 34))):
        layout.add_sprite(f"gallows:board_{k}", regions["frame"], x=_q(7.89), y=_q((DOOR[1] + DOOR[3]) / 2 + (0.24 if k else dy)), z=TOP - up, picnum=68,
                          x_repeat=long_ * 3 // 4, y_repeat=26, angle=0, cstat=16 | 128, shade=14, spans_opening=True)
    _stand(layout, regions, "house", "candles", 4.3, 33.6, 580, 64, cstat=384, shade=-128)
    _stand(layout, regions, "house", "hung", 5.6, 32.2, 906, 56, tall=44, seat="ceiling", sunk=True)
    # straw lies (all 41 of the campaign's are floor sprites, 14 of them with these bits, at the floor itself)
    layout.add_sprite("gallows:straw", regions["house"], x=_q(4.5), y=_q(30.7), z=TOP, picnum=515, x_repeat=64, y_repeat=64, angle=320,
                      cstat=32 | 64 | 128, shade=16)


def even(disk, compiled) -> dict:
    """After the light stage: the stair goes from the alley's shade to the terrace's by even steps, each riser as much darker than its tread.

    The owner, twice: "Gallows stairs shading looks flat", "Gallows stairs
    still have weird shading". Ten narrow sectors are lit by a sample apiece:
    nine came out at 0 between an alley at 21 and paving at 20, and one riser
    at 36 where a chimney's shadow crossed its middle. (225 outdoor steps of
    the campaign: a riser is 12 darker than its tread, and no tread differs
    from the next.)
    """
    from bloodmap.model import record_fields
    from bloodmap.sector_geom import sector_at
    level = disk.to_level_ir()

    def shade(x, y, floor):
        return int(record_fields(disk.sectors[sector_at(level, _q(x), _q(y), floor_near=floor)])["floor_shade"])

    foot, head = shade(9.0, ALLEY[2] - 0.2, GRADE), shade(9.0, STAIR_TO + 0.4, TOP)
    ids = [compiled.allocations[f"{KEY}:step_{k}"].sector_id for k in range(1, STEPS)]
    # it stays in the alley's shade until it comes up into the open; and the walls beside it are the alley's walls, not 8 darker
    treads = [round(foot + (head - foot) * (k / STEPS) ** 2.5) for k in range(1, STEPS)]
    beside = [round(SIDE_SHADE[0] + (SIDE_SHADE[1] - SIDE_SHADE[0]) * k / STEPS) for k in range(1, STEPS)]
    shades = dict(zip(ids, treads))
    top = {i for i, s in enumerate(disk.sectors) if int(record_fields(s)["floor_z"]) == TOP}
    for i, value in shades.items():
        record_fields(disk.sectors[i])["floor_shade"] = value
    for i, s in enumerate(disk.sectors):
        f = record_fields(s)
        for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            wall = record_fields(disk.walls[w])
            there = int(wall["next_sector"])
            up = there in shades and int(record_fields(disk.sectors[there])["floor_z"]) < int(f["floor_z"])
            last = i in shades and there in top
            if i in shades and int(wall["picnum"]) in (BRICK, RUBBLE):
                wall["shade"] = beside[ids.index(i)]
            if up or last:
                wall["shade"] = min(60, (shades[there] if up else treads[-1]) + 12)
                wall.update(_riser(STEPS if last else ids.index(there) + 1))
    return {"foot": foot, "head": head, "treads": treads}


def finish(level, compiled) -> int:
    """No two treads show the same piece of their tile. The owner: "move the textures on each step a bit to make it look less repetitive"."""
    done = 0
    for k in range(1, STEPS):
        allocation = compiled.allocations.get(f"{KEY}:step_{k}")
        if allocation is None:
            continue
        sector = level.sectors[allocation.sector_id]
        f = sector.get("fields", sector) if isinstance(sector, dict) else sector.fields
        f["floor_x_panning"], f["floor_y_panning"] = (k * 89) % 256, (k * 151) % 256
        done += 1
    # the door lies along the house: its tile's length along x, its first band a third of the way in from the doorway
    for k in (0, 1):
        allocation = compiled.allocations.get(f"{KEY}:slab_{k}")
        if allocation is not None:
            sector = level.sectors[allocation.sector_id]
            f = sector.get("fields", sector) if isinstance(sector, dict) else sector.fields
            f["floor_stat"] = int(f["floor_stat"]) | 4
            f["floor_x_panning"], f["floor_y_panning"] = 16 + 96 * k, round(-SLAB[2] * 64) % 256
    # the brick over and beside the doorway is one wall: hung from the sky, drawn from one corner
    from bloodmap import wallplane
    wide = wallplane.art()[BRICK][0]
    face = []
    for wall in level.walls:
        f = wall.get("fields", wall) if isinstance(wall, dict) else wall.fields
        n = level.walls[int(f["point2"])]
        n = n.get("fields", n) if isinstance(n, dict) else n.fields
        if int(f["x"]) == int(n["x"]) == _q(8.0) and int(f["picnum"]) == BRICK and _q(ALLEY[2]) <= min(int(f["y"]), int(n["y"])) \
                and max(int(f["y"]), int(n["y"])) <= _q(35.5) and int(f["y"]) > int(n["y"]):
            face.append((f, n))
    for f, n in face:
        f["x_repeat"] = max(1, round((int(f["y"]) - int(n["y"])) / 128))
        f["x_panning"] = ((_q(35.5) - int(f["y"])) // 16) % wide
        f["y_repeat"], f["y_panning"] = 8, 0
        f["cstat"] = int(f["cstat"]) | 4 if int(f["next_sector"]) >= 0 else int(f["cstat"]) & ~4
    return done
