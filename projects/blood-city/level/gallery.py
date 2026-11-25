"""The Gravesend Gallery: pictures in pools of light, between the saloon and the Aldermack, and at the end a beast of stone that is none.

The owner, 2026-11-25, of the shooting parlor that was here: "I would flag the hall between
that whiskey and aldemarck dressing room. That room which says shooting on the wall, it is
quite underwhelming"; "Maybe it can be just a galery, there was galery in E3M1 for example?";
and, of the maps called museum, "These museum maps actually looks bad ... Maybe just look at
art gallery in E3M1 it would be better".

E3M1's (sectors 178 to 209) wears what the parlor wore already (wall 100, checks 294, under
coffers 454); what makes it a gallery is how it is laid. Piers stand in the room with their
corners off and a picture on each face. Each picture on a wall has its own lamp (795) over it
and its own light under it: half rounds in floor and ceiling, 12 and 24 in a room at 38. There
are statues on the floor (536), vases and dried flowers on stands in the corners (642), and
what hangs can be shot to pieces (417).

Ours is an enfilade: from the street's door between two piers to the end wall, where the light
is on a low round platform, and on it what looks like one more statue (208, 1530, as the
rite's niches have them). What lies at its feet is taken, and it gets down. The painted
mother and child hangs four times along the door's own wall, each further gone (716 to 719):
they are seen last, going out.

The shooting is at the fair now, where there is something to shoot at (`fair.py`).
"""

from __future__ import annotations

import math

from bloodmap import arrangement as A, motion, wiring

PU = 1024
HALL, BACK = "region:gravesend/theatre_row/parlor/gallery", "region:gravesend/theatre_row/parlor/range"
GRADE = 8192
RISE, STONE = 2560, 84
SOLID = 1 | 256
#: the piers, (x0, y0, x1, y1), their corners cut off by CUT: holes from floor to ceiling
PIERS = ((11.95, 10.1, 12.85, 11.9), (14.15, 10.1, 15.05, 11.9))
CUT = 0.2
#: the platform at the end: its middle and its reach
PLATFORM, REACH = (13.5, 7.15), 0.8
LAMP, SPOT, OFF = 795, 0.5, 0.06
#: on the walls: (room, wall, how far along, tile, repeat, the middle over the floor in bodies, whether it has a light of its own)
HUNG = (
    (HALL, "south", 15.35, 716, 48, 0.98, False), (HALL, "south", 14.5, 717, 48, 0.98, False),
    (HALL, "south", 12.5, 718, 48, 0.98, False), (HALL, "south", 11.65, 719, 48, 0.98, False),
    (HALL, "west", 11.0, 610, 44, 1.08, True), (HALL, "east", 11.0, 613, 48, 1.08, True),
    (BACK, "west", 8.35, 612, 52, 1.08, True), (BACK, "east", 8.46, 611, 48, 1.08, True),
    (BACK, "north", 11.85, 163, 60, 1.08, True), (BACK, "north", 13.5, 614, 56, 1.12, False), (BACK, "north", 15.15, 617, 64, 1.05, True),
)
#: on the piers: (pier, face, tile, repeat, bodies)
ON_PIERS = ((0, "south", 268, 32, 1.08), (1, "south", 268, 32, 1.08), (0, "north", 99, 32, 1.08), (1, "north", 99, 32, 1.08),
            (0, "west", 621, 56, 1.0), (1, "east", 269, 40, 1.05), (0, "east", 617, 52, 1.0), (1, "west", 163, 44, 1.02))
#: on the floor: (room, x, y, tile, repeat, type)
STANDING = ((BACK, 12.2, 8.75, 536, 40, 417, {"data_1": 20, "data_4": 301}), (BACK, 14.8, 8.75, 536, 40, 417, {"data_1": 20, "data_4": 301}),
            (HALL, 11.3, 12.65, 642, 64, 416, {"data_1": 5, "data_4": 301}), (HALL, 15.7, 12.65, 642, 64, 416, {"data_1": 5, "data_4": 301}),
            (BACK, 11.3, 6.25, 642, 64, 416, {"data_1": 5, "data_4": 301}), (BACK, 15.7, 6.25, 642, 64, 416, {"data_1": 5, "data_4": 301}))
#: lamps that are no wall's: over the platform, between the piers, and one before each of their ends
LAMPS = ((BACK, 13.5, 7.15, 40), (HALL, 13.5, 11.0, 24), (HALL, 12.4, 9.6, 24), (HALL, 14.6, 9.6, 24), (HALL, 12.4, 12.35, 24),
         (HALL, 14.6, 12.35, 24))
BEAST, PRIZE = (13.5, 6.95), (141, 2586, 13.5, 7.65)           # (64, as all 58 of Blood's body armours are)
FACING = {"south": 1536, "north": 512, "west": 0, "east": 1024}
OUT = {"south": 512, "north": 1536, "west": 1024, "east": 0}             # a pier's face looks out of it
_MADE: dict[str, str] = {}
_PAINTED: list[tuple[str, tuple, tuple, dict]] = []


def _q(v: float) -> int:
    return round(v * PU)


def _cut(x0, y0, x1, y1, c):
    return [(_q(x), _q(y)) for x, y in ((x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c),
                                        (x0, y0 + c))]


def _box(layout, room):
    ring = layout.regions[room].outer
    return tuple(f(p[a] for p in ring) for f, a in ((min, 0), (min, 1), (max, 0), (max, 1)))


def _spot(layout, room, wall, along):
    """The half round of floor before a picture: its ring, and where its lamp is."""
    x0, y0, x1, y1 = _box(layout, room)
    ring = []
    for k in range(6):
        turn = math.pi * k / 5
        side, out = SPOT * math.cos(turn), OFF + SPOT * math.sin(turn)
        ring.append({"north": (_q(along + side), y0 + _q(out)), "south": (_q(along + side), y1 - _q(out)), "west": (x0 + _q(out), _q(along + side)),
                     "east": (x1 - _q(out), _q(along + side))}[wall])
    lamp = {"north": (_q(along), y0 + _q(0.3)), "south": (_q(along), y1 - _q(0.3)), "west": (x0 + _q(0.3), _q(along)), "east": (x1 - _q(0.3), _q(along))}
    return ring, lamp[wall]


def _island(layout, name, host, ring, **fields):
    """A piece of a room's floor of its own."""
    room = layout.regions[host]
    place = A.Arrangement()
    place.add("it", ring)
    cells = place.resolve()
    layout.carve_hole(host, list(cells[0].outer))
    made = A.lay(layout, f"{host}/{name}", cells, lambda _cell: {**dict(
        floor_z=GRADE, ceiling_z=room.ceiling_z, floor_picnum=room.floor_picnum, wall_picnum=room.wall_picnum, ceiling_picnum=room.ceiling_picnum,
        layer=room.layer, floor_shade=room.floor_shade, wall_shade=room.wall_shade, ceiling_shade=room.ceiling_shade, role="detail",
        declared_zero_exit=True, intent={"kind": "furnished"}), **fields})
    for _cell, a, b in A.rim(cells):
        layout.add_connection(f"connection:gallery_{name}:{a[0]}:{a[1]}", host, made["it"], a1=b, a2=a, min_width=1, min_opening=0)
    _MADE[name] = made["it"]
    return cells


def build(layout) -> dict:
    """The piers, the platform, and the lit half rounds."""
    _MADE.clear()
    _PAINTED.clear()
    for pier in PIERS:
        layout.carve_hole(HALL, _cut(*pier, CUT))
    centre = (_q(PLATFORM[0]), _q(PLATFORM[1]))
    for _cell, a, b in A.rim(_island(layout, "platform", BACK, A.circle(centre, _q(REACH), 12), floor_z=GRADE - RISE)):
        layout.paint_wall(BACK, b, a, picnum=STONE)
        _PAINTED.append((BACK, b, a, {"picnum": STONE}))
    spots = 0
    for k, (room, wall, along, *_rest, lit) in enumerate(HUNG):
        if lit:
            _island(layout, f"spot_{k}", room, _spot(layout, room, wall, along)[0])
            spots += 1
    return {"piers": len(PIERS), "spots": spots}


def _art(tile: int):
    import wallplane
    return wallplane.art()[tile]


def _set(layout, name, region, x, y, tile, size, **fields) -> None:
    """A thing on the floor, by the box the renderer draws."""
    from bloodmap.placement import seated_z
    host = layout.regions[region]
    layout.add_sprite(name, region, x=_q(x), y=_q(y), z=seated_z(
        seat="floor", floor_z=host.floor_z, ceiling_z=host.ceiling_z, tile_height=_art(tile)[1], y_repeat=size, y_offset=_art(tile)[3],
        cstat=128, clearance=0), picnum=tile, x_repeat=size, y_repeat=size, **{"type": 0, "status": 0, "cstat": 128 | SOLID, "shade": -8, **fields})


def _lamp(layout, name, region, x, y, size) -> None:
    layout.add_sprite(name, region, x=x, y=y, z=int(layout.regions[region].ceiling_z) + 64, picnum=LAMP, x_repeat=size, y_repeat=size,
                      cstat=32 | 64 | 128 | 8, shade=-64, sunk=True)


def dress(layout) -> dict:
    """What hangs, what lights it, what stands, and what is not stone."""
    import wires

    def hang(name, room, x, y, tile, size, up, angle):
        layout.add_sprite(name, room, x=x, y=y, z=GRADE - round(up * 16960) + _art(tile)[3] * size * 4, picnum=tile, x_repeat=size, y_repeat=size,
                          angle=angle, cstat=16 | 64 | 128, shade=-8)
    for k, (room, wall, along, tile, size, up, lit) in enumerate(HUNG):
        x0, y0, x1, y1 = _box(layout, room)
        x, y = {"south": (_q(along), y1 - 5), "north": (_q(along), y0 + 5), "west": (x0 + 5, _q(along)), "east": (x1 - 5, _q(along))}[wall]
        hang(f"gallery:hung_{k}", room, x, y, tile, size, up, FACING[wall])
        if lit:
            _lamp(layout, f"gallery:lamp_{k}", _MADE[f"spot_{k}"], *_spot(layout, room, wall, along)[1], 36)
    for k, (pier, face, tile, size, up) in enumerate(ON_PIERS):
        x0, y0, x1, y1 = PIERS[pier]
        x, y = {"south": (_q((x0 + x1) / 2), _q(y1) + 5), "north": (_q((x0 + x1) / 2), _q(y0) - 5), "west": (_q(x0) - 5, _q((y0 + y1) / 2)),
                "east": (_q(x1) + 5, _q((y0 + y1) / 2))}[face]
        hang(f"gallery:pier_{k}", HALL, x, y, tile, size, up, OUT[face])
    for k, (room, x, y, size) in enumerate(LAMPS):
        _lamp(layout, f"gallery:lamp_over_{k}", _MADE["platform"] if (x, y) == PLATFORM else room, _q(x), _q(y), size)
    for k, (room, x, y, tile, size, kind, record) in enumerate(STANDING):
        _set(layout, f"gallery:standing_{k}", room, x, y, tile, size, type=kind, status=4, behavior=dict(record))
    stage = _MADE["platform"]
    _set(layout, "gallery:beast", stage, *BEAST, 1530, 40, type=208, status=6, cstat=384, shade=0, angle=512)
    kind, tile, x, y = PRIZE
    _set(layout, "gallery:prize", stage, x, y, tile, 64, type=kind, status=3, cstat=128, shade=-8)
    taken = wires.wire("gallery:beast")
    taken.when(wiring.placement("gallery:prize"), "pickup", command=motion.CMD_ON, once=True)
    taken.then(wiring.placement("gallery:beast"))
    return {"hung": len(HUNG) + len(ON_PIERS), "standing": len(STANDING), "lamps": len(LAMPS) + sum(row[-1] for row in HUNG)}


def keep(level, compiled) -> int:
    """The platform's edge, put back."""
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
