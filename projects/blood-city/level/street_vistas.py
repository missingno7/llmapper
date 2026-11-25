"""Where a main street stops: the old town wall, its gate shut, and the street going on behind it under the roofs of a town nobody can walk to.

The owner, 2026-11-25: "These walls on the city borders should have hint of continuing
behind even it is unreachable, but it should make it to look better, now it is just
cutoff by sky." Each of the three ends was one plain mass 5.8 bodies tall with sky
straight behind it.

E3M1 shows what lies past its edge in two places (sectors 333-337 and 366-368): a court
out of reach, its outline broken, every wall of it another building's tile (384, 401,
181, 418, 414; 397, 393, 417, 381), a sector of no height where the sky comes down. So:
a wall of 2.9 bodies, that the roofs behind stand over, and a barred gate in it through
which the paving and the lamps go on to where the street turns. The buildings are raised
floors of whole storeys (a lower sky would be a lid on everything, `bloodmap.skyline`),
none of one height, with the sky's own backing behind them.

One `bloodmap.arrangement` to each end, written in the street's own frame: `s` along the
mouth, `d` out of the town.
"""

from __future__ import annotations

import math

from bloodmap import arrangement as A

PU = 1024
KEY = "region:gravesend/vistas"
GRADE, SKY_Z, SKY = 8192, -188416, 3491
ROAD = 10240
STOREY = 32768
#: the wall over the paving, and the posts of its gate (a man is 16,960)
WALL_RISE, POST_RISE = 49152, 59392
WALL, POST, COPING, PAVING, COBBLE, KERB, ROOF, STACK = 110, 427, 253, 4, 352, 6, 379, 90
THICK, GATE_W, POST_W = 0.5, 2.0, 0.5
#: E1M2's iron gates as the station hangs them: spear heads up, 2,048 wide and 32,768 tall, seen through and shot through
GATE = {"type": 0, "picnum": 1044, "cstat": 8413 & ~64 & ~256, "x_repeat": 64, "y_repeat": 64, "shade": 8, "status": 0}
#: an end: the edge it is in, and its mouth's two ends along it, in plan units; what each building behind wears and how many
#: storeys it has. `left` and `right` as they stand along the edge, low end first.
ENDS = {
    "row": ("west", 15.0, 21.0, {"left": (400, 4), "bend": (393, 3), "right": (384, 3), "corner": (380, 5), "far": (397, 4)}),
    "market_west": ("west", 35.0, 40.0, {"left": (384, 3), "bend": (380, 4), "right": (393, 4), "corner": (400, 4), "far": (384, 3)}),
    "market_east": ("east", 35.0, 40.0, {"left": (397, 4), "bend": (384, 3), "right": (380, 3), "corner": (393, 5), "far": (400, 4)}),
}
EDGES = {"west": 0.0, "east": 58.0}


def _frame(edge, low):
    """(s, d) in plan units to the map."""
    line, out = EDGES[edge], -1 if edge == "west" else 1
    return lambda s, d: (round((line + out * d) * PU), round((low + s) * PU))


def plan(name: str) -> list:
    """Every cell of one end."""
    from shapely import Polygon, box, unary_union
    edge, low, high, _wear = ENDS[name]
    m, at = high - low, _frame(edge, low)

    def ring(points):
        return [at(s, d) for s, d in points]

    def rect(s0, d0, s1, d1):
        return [(s0, d0), (s1, d0), (s1, d1), (s0, d1)]

    t = THICK
    street = [(0, t), (m, t), (m, 4.5), (m + .5, 4.5), (m + .5, 7.5), (m + 3, 10.5), (m + 3, 13), (m + .25, 13), (.75, 9.5), (.75, 6.5), (0, 6.5)]
    middle = m / 2
    road = [(middle - 1, t), (middle + 1, t), (middle + 1, 6.6), (m + 2.3, 11.2), (m + 2.3, 12.4), (m + .9, 12.4), (middle - 1, 8)]
    masses = {
        "left": rect(-2, t, 0, 6.5),
        "bend": [(-1.5, 6.5), (.75, 6.5), (.75, 9.5), (m + .25, 13), (m - 1, 14.5), (-1.5, 10.5)],
        "right": rect(m, t, m + 2, 4.5),
        "corner": [(m + .5, 4.5), (m + 2.5, 4.5), (m + 2.5, 7), (m + 5, 9.5), (m + 3, 10.5), (m + .5, 7.5)],
        "far": [(m - 1, 13), (m + 3, 13), (m + 3, 10.5), (m + 5, 9.5), (m + 5, 14.5), (m - 1, 14.5)],
    }
    place = A.Arrangement()
    # the sky comes down behind it all: never nearer the town than the wall's back
    town = unary_union([Polygon(p) for p in masses.values()] + [Polygon(street)])
    sky = town.buffer(0.5, join_style=2).intersection(box(-10, t, m + 10, 20))
    place.add("sky", ring(list(sky.exterior.coords)[:-1]))
    for part, points in masses.items():
        place.add(part, ring(points))
    for part, (s0, d0, s1, d1) in {"left": (-1.5, 2, -.75, 2.75), "bend": (0, 8, .5, 8.75), "right": (m + .75, 2.5, m + 1.5, 3.25),
                                   "corner": (m + 1.5, 6, m + 2, 6.75), "far": (m + 3.75, 12, m + 4.5, 12.5)}.items():
        place.add(f"stack_{part}", ring(rect(s0, d0, s1, d1)))
    place.add("pave", ring(street))
    place.add("road", ring(road))
    g0, g1 = middle - GATE_W / 2, middle + GATE_W / 2
    place.add("wall_a", ring(rect(0, 0, g0 - POST_W, t)))
    place.add("post_a", ring(rect(g0 - POST_W, 0, g0, t)))
    place.add("gate_out", ring(rect(g0, 0, g1, t / 2)))
    place.add("gate_in", ring(rect(g0, t / 2, g1, t)))
    place.add("post_b", ring(rect(g1, 0, g1 + POST_W, t)))
    place.add("wall_b", ring(rect(g1 + POST_W, 0, m, t)))
    return place.resolve()


def build(layout) -> dict[str, int]:
    """Lay each end beyond the town's edge and join it to the streets along the mouth."""
    out = {}
    for name, (edge, low, high, wear) in ENDS.items():
        cells = plan(name)
        key = f"{KEY}/{name}"

        def base(cell):
            return cell.split("_")[0]

        def levels(cell):
            what, *rest = cell.split("_")
            if what == "sky":
                return GRADE, GRADE
            if what == "stack":
                return GRADE - wear[rest[0]][1] * STOREY - 14336, SKY_Z
            if what in wear:
                return GRADE - wear[what][1] * STOREY, SKY_Z
            return {"wall": GRADE - WALL_RISE, "post": GRADE - POST_RISE, "road": ROAD}.get(what, GRADE), SKY_Z

        def surface(cell):
            what = base(cell)
            floor, ceiling = levels(cell)
            tiles = {"sky": (PAVING, WALL), "stack": (STACK, STACK), "wall": (COPING, WALL), "post": (COPING, POST), "road": (COBBLE, PAVING),
                     "gate": (PAVING, POST), "pave": (PAVING, PAVING)}.get(what) or (ROOF, wear[what][0])
            return dict(floor_z=floor, ceiling_z=ceiling, floor_picnum=tiles[0], wall_picnum=tiles[1], ceiling_picnum=SKY, parallax_ceiling=True,
                        layer="street", floor_shade=14, wall_shade=14, ceiling_shade=0, role="detail", declared_zero_exit=True,
                        intent={"kind": {"wall": "end_wall", "post": "end_wall", "gate": "end_wall", "sky": "sky_backing"}.get(what, "vista"),
                                "street": name})

        def worn(cell):
            """What a raised cell shows to whoever is under it."""
            what, *rest = cell.split("_")
            return {"wall": WALL, "post": POST, "stack": STACK}.get(what) or (wear[what][0] if what in wear else PAVING)

        def face(seen, beyond, _a, _b):
            if beyond is None:
                return {"picnum": wear["left"][0]} if base(seen) in ("pave", "road") else {}
            if base(seen) == "road" and base(beyond) in ("pave", "gate"):
                return {"picnum": KERB}
            if levels(beyond)[0] < levels(seen)[0]:
                return {"picnum": worn(beyond)}
            return {}

        regions = A.lay(layout, key, cells, surface, face)
        out[name] = len(regions)
        _join(layout, name, regions, cells, worn)
        _furnish(layout, name, regions, cells)
    return out


def _join(layout, name, regions, cells, worn) -> None:
    """The wall and the gate open on whichever streets come to the mouth."""
    from shapely import LineString, Polygon
    edge, _low, _high, _wear = ENDS[name]
    line = round(EDGES[edge] * PU)
    streets = [(r.region_id, Polygon(r.outer).exterior) for r in layout.regions.values()
               if r.parallax_ceiling and r.floor_z == GRADE and not r.region_id.startswith(KEY)
               and any(x == line for x, _y in r.outer)]
    for cell, a, b in A.rim(cells):
        if not a[0] == b[0] == line:
            continue
        for street, border in streets:
            shared = LineString((a, b)).intersection(border.buffer(1))
            if shared.is_empty or shared.length < 64:
                continue
            ys = sorted(round(y) for _x, y in shared.coords)
            lo, hi = max(min(a[1], b[1]), ys[0]), min(max(a[1], b[1]), ys[-1])
            # the ends of what is shared, on the streets' own corners where they have one there
            own = [y for x, y in next(r for r in layout.regions.values() if r.region_id == street).outer if x == line]
            lo = next((y for y in own if abs(y - lo) <= 2), lo)
            hi = next((y for y in own if abs(y - hi) <= 2), hi)
            p, q = ((line, lo), (line, hi)) if a[1] < b[1] else ((line, hi), (line, lo))
            layout.add_connection(f"connection:vista:{name}:{cell}:{street.split('/')[-2]}", street, regions[cell], a1=q, a2=p,
                                  min_width=1, min_opening=0)
            if not cell.startswith("gate"):
                layout.paint_wall(street, q, p, picnum=worn(cell))


def _furnish(layout, name, regions, cells) -> None:
    """The gate's two leaves' iron, and a lamp either side of the street behind it."""
    import wallplane
    from bloodmap.placement import seated_z
    edge, low, high, _wear = ENDS[name]
    m, at = high - low, _frame(edge, low)
    g0, g1 = m / 2 - GATE_W / 2, m / 2 + GATE_W / 2
    a, b = at(g0, THICK / 2), at(g1, THICK / 2)
    # from the street one faces it: its wall runs from the left hand to the right
    a1, a2 = (b, a) if edge == "west" else (a, b)
    _w, height, _x, offset = wallplane.art()[GATE["picnum"]]
    layout.add_sprite(f"vista:{name}:gate", regions["gate_out"], x=(a[0] + b[0]) // 2 + (16 if edge == "west" else -16), y=(a[1] + b[1]) // 2,
                      z=seated_z(seat="floor", floor_z=GRADE, ceiling_z=SKY_Z, tile_height=height, y_repeat=GATE["y_repeat"],
                                 y_offset=offset, cstat=GATE["cstat"], clearance=16),
                      angle=0 if edge == "west" else 1024, spans_opening=True, **GATE)
    _w, height, _x, offset = wallplane.art()[640]
    for k, (s, d) in enumerate(((0.5, 2.5), (m - 0.5, 6.5), (m + 2.5, 12.0))):
        cell = next(c for c in cells if c.name.startswith("pave") and _inside(c, at(s, d)))
        x, y = at(s, d)
        layout.add_sprite(f"vista:{name}:lamp_{k}", regions[cell.name], x=x, y=y,
                          z=seated_z(seat="floor", floor_z=GRADE, ceiling_z=SKY_Z, tile_height=height, y_repeat=120, y_offset=offset,
                                     cstat=128, clearance=16),
                          picnum=640, x_repeat=120, y_repeat=120, cstat=128, shade=4)


def _inside(cell, point) -> bool:
    from shapely import Point, Polygon
    return Polygon(cell.outer, cell.holes).buffer(-64).contains(Point(point))
