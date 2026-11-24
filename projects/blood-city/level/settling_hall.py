"""The settling hall: the outfall comes down a flight of falls beside a stair into three vaulted tanks before the Cabal's mouth.

The owner, 2026-11-24: "That room where we previously had cabal circle which is
connecting it to sewers should be redone a bit to have more seamless connection
from sewers." What it was: a box 15 by 7 units with one flat roof, beside the
sewer and not of it; the outfall's corridor ended in a wall, its water went
round a corner into a slot, and the way down was a shut stair in a column.

What it is: the outfall's own section does not stop. Its water crosses the
gallery in one line, drops over five falls, and its east walk goes down beside
the falls as a stair, under the same sloped roof; each tank lies in a vault
whose ridge and springing are the corridor's (its walks' roofs slope 8,192 down
from the crown). So the hall is seen from the outfall, over the falls, before
it is entered, and the Cabal's mouth from the gallery.
Built of `bloodmap.arrangement`, but for the two quays, which are rooms of the
tree because the Toshers' Den and the Cabal's chamber are joined to them.
"""

from __future__ import annotations

from bloodmap import arrangement as A
from bloodmap.slope import SlopeSpec

PU = 1024
KEY = "region:gravesend/sewer/settling_hall/hall"
#: levels: the gallery's channel and walk, the tanks, the walks between them; the vault's crown and its springing
CHANNEL, TOP_WALK, WATER, WALK = 63488, 61440, 106496, 102400
CROWN, SPRING = 32768, 40960
NORTH, WEST, QUAY = 43.0, 21.0, 48.0                    # the gallery's edge, the west quay's, the south quay's
FALLS = (32.5, 33.5)                                    # the outfall's own channel, carried on
STAIR = (33.5, 34.5)
CURB = 32.25                                            # the flume's west wall
FALL, RISER = 8192, 4096
#: the tanks (y0, y1) and the walks between them
TANKS = ((43.0, 44.25), (45.0, 46.25), (47.0, 48.0))
WALKS = ((44.25, 45.0), (46.25, 47.0))
#: where the piers stand along the walks: the mouth's own axis (27.5) is clear
PIERS = (22.6, 25.05, 29.95)
PIER = 0.3125
STONE, BLOCK, FLOOR, VAULT, SEWAGE, TRIM = 492, 488, 568, 255, 1120, 255


def _q(v: float) -> int:
    return round(v * PU)


def _rect(x0, y0, x1, y1):
    return [(_q(x0), _q(y0)), (_q(x1), _q(y0)), (_q(x1), _q(y1)), (_q(x0), _q(y1))]


def plan() -> list:
    """Every cell of the hall between its quays."""
    place = A.Arrangement()
    for k, (y0, y1) in enumerate(TANKS, 1):
        middle = (y0 + y1) / 2
        place.add(f"tank_{k}n", _rect(WEST, y0, CURB, middle))
        place.add(f"tank_{k}s", _rect(WEST, middle, CURB, y1))
    for k, (y0, y1) in enumerate(WALKS, 1):
        place.add(f"walk_{k}", _rect(WEST, y0, CURB, y1))
    for k in range(5):
        y = NORTH + k
        if k < 4:
            place.add(f"curb_{k + 1}", _rect(CURB, y, FALLS[0], y + 1))
        place.add(f"fall_{k + 1}", _rect(CURB if k == 4 else FALLS[0], y, FALLS[1], y + 1))
    for k in range(10):
        y = NORTH + k / 2
        place.add(f"stair_{k + 1}", _rect(STAIR[0], y, STAIR[1], y + 0.5))
    # piers in the water at the walks' edges, and against the gallery's, where they rise past it to the roof
    for x in PIERS:
        for y0, y1 in WALKS:
            place.solid(_rect(x - PIER / 2, y0 - PIER, x + PIER / 2, y0))
            place.solid(_rect(x - PIER / 2, y1, x + PIER / 2, y1 + PIER))
        place.solid(_rect(x - PIER / 2, NORTH, x + PIER / 2, NORTH + 0.25))
    return place.resolve()


def _part(cell: str) -> tuple[str, int]:
    kind, number = cell.split("_")
    return kind, int(number.rstrip("ns"))


def levels(cell: str) -> tuple[int, int]:
    """A cell's floor and ceiling (a vault's at its ridge)."""
    kind, k = _part(cell)
    if kind == "tank":
        return WATER, CROWN
    if kind == "walk":
        return WALK, SPRING
    if kind == "fall":
        return CHANNEL + FALL * k, CROWN
    if kind == "curb":
        return CHANNEL + FALL * k - 2048, CROWN
    return TOP_WALK + RISER * k, CROWN


def _edge_on(cell, *, x=None, y=None):
    """The longest edge of a cell that lies on a line."""
    ring = cell.outer
    on = [(a, b) for a, b in zip(ring, ring[1:] + ring[:1])
          if (x is not None and a[0] == b[0] == x) or (y is not None and a[1] == b[1] == y)]
    return max(on, key=lambda e: abs(e[0][0] - e[1][0]) + abs(e[0][1] - e[1][1]))


def build(layout, gallery: dict, quays: dict) -> dict[str, str]:
    """Lay the hall between the gallery's edge and its two quays.

    `gallery` is {(x0, x1): region id} along the gallery's south edge, `quays`
    the region ids of the west and the south quay.
    """
    from l3_sewer import FLOW, HALL_LAYER, flow_behavior
    cells = plan()
    by_name = {c.name: c for c in cells}

    def surface(name):
        kind, k = _part(name)
        floor, ceiling = levels(name)
        wet = kind in ("tank", "fall")
        more = {}
        if kind == "tank":
            y0, y1 = TANKS[k - 1]
            more["ceiling_slope"] = SlopeSpec(hinge=_edge_on(by_name[name], y=_q((y0 + y1) / 2)), rise_z=SPRING - CROWN)
        if kind == "stair":
            more["ceiling_slope"] = SlopeSpec(hinge=_edge_on(by_name[name], x=_q(STAIR[0])), rise_z=SPRING - CROWN)
        behavior = {}
        if wet:
            flow = FLOW[f"tank_{k}"] if kind == "tank" else (1024, 24, False) if k == 5 else (512, 24, False)
            behavior = {"amplitude": -4, "shade_frequency": 4, **flow_behavior(*flow)}
        return dict(floor_z=floor, ceiling_z=ceiling, floor_picnum=SEWAGE if wet else FLOOR, ceiling_picnum=VAULT,
                    wall_picnum=STONE, floor_shade=38 if wet else 40, wall_shade=24, ceiling_shade=28, layer=HALL_LAYER,
                    role="detail" if kind == "curb" else "interior", declared_zero_exit=True,
                    intent={"kind": "furnished"}, sector_behavior=behavior, **more)

    def face(seen, beyond, a, b):
        here, there = _part(seen)[0], _part(beyond)[0] if beyond else None
        if there is None and here in ("tank", "walk") and math_len(a, b) < 400 and any(
                abs((a[0] + b[0]) / 2 - _q(x)) < 400 for x in PIERS):
            paint = {"picnum": BLOCK}
        elif there in ("stair", "walk"):
            paint = {"picnum": TRIM}
        elif here == "tank":
            paint = {"picnum": STONE}
        else:
            return {}
        _PAINTED.append((regions_of(seen), a, b, paint["picnum"]))
        return paint

    _PAINTED.clear()
    regions = A.lay(layout, KEY, cells, surface, face)
    for name, a, b in A.rim(cells):
        room = None
        if a[0] == b[0] == _q(WEST):
            room = quays["west"]
        elif a[1] == b[1] == _q(QUAY):
            room = quays["south"]
        elif a[1] == b[1] == _q(NORTH):
            middle = (a[0] + b[0]) / 2
            room = next((r for (x0, x1), r in gallery.items() if _q(x0) < middle < _q(x1)), None)
        if room:
            layout.add_connection(f"connection:hall:{name}:{a[0]}:{a[1]}", room, regions[name], a1=b, a2=a,
                                  min_width=1, min_opening=0)
    _water(layout, regions, by_name)
    _furnish(layout, regions)
    return regions


def regions_of(cell: str) -> str:
    return f"{KEY}:{cell}"


#: what `build` painted: (region, a, b, tile); `keep` puts it back
_PAINTED: list[tuple] = []


def keep(disk, compiled) -> int:
    """Put back the piers, gables and risers the city's later passes took for openings and lintels."""
    return put_back(disk, compiled, _PAINTED)


def put_back(disk, compiled, painted: list) -> int:
    """Set each (region, a, b, tile) again on the built walls; a fall's running water is left as it is."""
    from bloodmap.model import record_fields
    where = {}
    for region in {r for r, *_rest in painted}:
        for wall in compiled.allocations[region].wall_ids:
            f = record_fields(disk.walls[wall])
            end = record_fields(disk.walls[int(f["point2"])])
            where[region, (f["x"], f["y"]), (end["x"], end["y"])] = f
    put = 0
    for region, a, b, tile in painted:
        f = where.get((region, tuple(a), tuple(b))) or where.get((region, tuple(b), tuple(a)))
        if f is not None and f["picnum"] != tile and f["picnum"] != SEWAGE:
            f["picnum"] = tile
            put += 1
    return put


def math_len(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _water(layout, regions, cells) -> None:
    """Every fall's face runs (E1M8's wall), foam at its foot, and the sound of it at the head and the foot."""
    from bloodmap.corpus import corpus_map_path
    from bloodmap.format import read_map
    from bloodmap.model import record_extra, record_fields
    from bloodmap.placement import build_angle, inward_normal
    from l3_sewer import POUR_SOURCE
    source = read_map(corpus_map_path(POUR_SOURCE[0])).walls[POUR_SOURCE[1]]
    finish = {key: record_fields(source)[key] for key in
              ("picnum", "type", "x_repeat", "y_repeat", "x_panning", "y_panning")}
    pan = {key: record_extra(source)[key] for key in
           ("pan_always", "pan_x_velocity", "pan_y_velocity", "x_pan_fraction", "y_pan_fraction")}
    runs = [(f"fall_{k}", (FALLS[0], NORTH + k - 1), (FALLS[1], NORTH + k - 1)) for k in range(1, 6)]
    runs += [("tank_3n", (CURB, 47.0), (CURB, 47.5)), ("tank_3s", (CURB, 47.5), (CURB, 48.0))]
    for name, a, b in runs:
        a, b = tuple(map(_q, a)), tuple(map(_q, b))
        ring = cells[name].outer
        a, b = next((p, q) for p, q in zip(ring, ring[1:] + ring[:1]) if {p, q} == {a, b})
        layout.paint_wall(regions[name], a, b, fixed_frame=True, **finish)
        layout.wire_wall(regions[name], a, b, **pan)
        nx, ny = inward_normal(*a, *b)
        layout.add_sprite(f"sewer:hall_foam_{name}", regions[name], picnum=1037,
                          x=round((a[0] + b[0]) / 2 + 32 * nx), y=round((a[1] + b[1]) / 2 + 32 * ny),
                          z=layout.regions[regions[name]].floor_z, angle=build_angle(nx, ny), cstat=210,
                          x_repeat=28 if math_len(a, b) > 800 else 14, y_repeat=32, shade=-33)
    sample = read_map(corpus_map_path(POUR_SOURCE[2]))
    sound = record_fields(sample.sprites[POUR_SOURCE[3]])
    over = record_fields(sample.sectors[POUR_SOURCE[4]])["floor_z"] - sound["z"]
    behavior = {key: record_extra(sample.sprites[POUR_SOURCE[3]])[key] for key in
                ("state", "busy", "data_1", "data_2", "data_3", "data_4")}
    for k in (1, 5):
        floor, _ceiling = levels(f"fall_{k}")
        layout.add_sprite(f"placement:settling_hall:fall_sound_{k}", regions[f"fall_{k}"], x=_q(33.0),
                          y=_q(NORTH + k - 0.5), z=floor - over, behavior=behavior,
                          **{key: sound[key] for key in
                             ("picnum", "type", "cstat", "status", "shade", "x_repeat", "y_repeat")})


#: chain lamps down the walks between the tanks: (cell, x, y)
LAMPS = (("walk_1", 23.8, 44.62), ("walk_1", 27.5, 44.62), ("walk_1", 31.0, 44.62),
         ("walk_2", 23.8, 46.62), ("walk_2", 27.5, 46.62), ("walk_2", 31.0, 46.62))
#: flat lights over the falls, on the crown (the outfall's own tubes stop at the gallery)
FALL_LIGHTS = (1, 3, 5)


def _furnish(layout, regions) -> None:
    import wallplane
    from bloodmap.placement import drawn_extent
    for k, (cell, x, y) in enumerate(LAMPS):
        room = layout.regions[regions[cell]]
        _w, height, _x, offset = wallplane.art()[641]
        _top, bottom = drawn_extent(height, offset, 80, 128)
        layout.add_sprite(f"hall:lamp_{k}", regions[cell], x=_q(x), y=_q(y),
                          z=max(room.floor_z - 26000 - bottom, room.ceiling_z + 16), picnum=641, x_repeat=80, y_repeat=80,
                          cstat=128, shade=-128, sunk=True)
    for k in FALL_LIGHTS:
        room = layout.regions[regions[f"fall_{k}"]]
        layout.add_sprite(f"hall:fall_light_{k}", regions[f"fall_{k}"], x=_q(33.0), y=_q(NORTH + k - 0.5),
                          z=room.ceiling_z + 64, picnum=795, x_repeat=48, y_repeat=48, cstat=32 | 128 | 8, shade=-8)
    # E3M3's moss (793) goes on down the stair's wall
    for k in (3, 6, 9):
        y = NORTH + k / 2
        wallplane.sprite(layout, f"hall:moss_{k}", regions[f"stair_{k}"], (_q(STAIR[1]), _q(y - 0.5)), (_q(STAIR[1]), _q(y)),
                         tile=793, x_repeat=32, y_repeat=32, cstat=208, height_player_heights=1.4, shade=14, required=False)
