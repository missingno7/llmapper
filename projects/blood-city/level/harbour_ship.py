"""The Demeter, moored at the quay: a hull that can be boarded, a deck, a hold under the deckhouse, and a smuggler's locker behind a panel.

The harbour is the first thing the level shows, and the ship in it was looked
at and never reached: a hull a unit off the quay, its deckhouse shut. It is the
size of DWE3M4's "Phantom" now (13,312 by 4,096), and a gangplank lies from the
quay to a gap in the gunwale before the deckhouse.

One plan, resolved by `bloodmap.arrangement`: the gunwale is the highest thing
on the hull but for the deckhouse's walls, which stand on it at the stern. The
hold is the inside of those walls, three steps down from the deck, under a roof
of flat plank sprites (as DWE3M10 and E6M1 roof their stands): every ceiling
aboard is the sky's, because a ceiling under a sky as tall as this one draws a
wall from itself to the top of it.

In the hold are the crew, the flare pistol, and at the back a panel of other
planks that sinks when it is pushed: the locker is a secret, dynamite, which is
also the way through a manhole. Taking the pistol brings what is under the
keel aboard.

Study: `knowledge/blood/studies/harbour`. Design: `references/market-design.md`.
"""

from __future__ import annotations

import re

from bloodmap import arrangement as A
from bloodmap import motion, wiring
from bloodmap.doors import xsector_direct_use
from bloodmap.levelprog import Frame, Style
from bloodmap.slope import SlopeSpec

import wires

PU = 1024
GRADE = 8192
#: plan units. The hull's outline, stern first; its inside, a gunwale's width in
HULL = ((11.0, 57.0), (21.0, 57.0), (23.0, 58.0), (24.0, 59.0), (23.0, 60.0), (21.0, 61.0), (11.0, 61.0))
INSIDE = ((11.25, 57.25), (20.9375, 57.25), (22.75, 58.15625), (23.5, 59.0), (22.75, 59.84375), (20.9375, 60.75), (11.25, 60.75))
#: the deckhouse: its front wall, its doorway, the partition before the locker, the panel in it
FRONT = (14.25, 14.5)
DOORWAY = (58.5, 59.5)
PARTITION = (12.0, 12.25)
PANEL = (59.75, 60.75)
#: the gangplank: from the quay's edge to the deck, through the gap it fills in the gunwale
GANG = (14.5, 15.25)
QUAY = 56.0
MAST = (18.0, 58.875, 18.25, 59.125)
CRATES = ((19.5, 57.5), (19.75, 59.25))
#: levels, down from the gunwale's top (which is 11,264 over the quay)
HOUSE, STEP = 16384, 4096
LETTERED = "DEMETER"
#: tile 513: its columns and rows, and how far across and down the rope itself goes (a texel short, so two pieces meet)
ROPE = (38, 52, 32, 49)
#: region id -> a type the door pass must not see (it takes a 600 for a leaf whose ceiling rises)
LATE_TYPES: dict = {}
ROOMS: dict = {}
CELLS: list = []


def _q(v: float) -> int:
    return round(v * PU)


def _ring(points):
    return [(_q(x), _q(y)) for x, y in points]


def _rect(x0, y0, x1, y1):
    return _ring(((x0, y0), (x1, y0), (x1, y1), (x0, y1)))


def plan() -> list:
    place = A.Arrangement()
    place.add("rim", _ring(HULL))
    place.add("shell", _rect(11.0, 57.0, FRONT[1], 61.0))
    place.add("deck", [p for p in _ring(INSIDE)])
    place.add("shell", _rect(11.0, 57.25, FRONT[0], 60.75))
    place.add("bulkhead", _rect(FRONT[0], 57.25, FRONT[1], 60.75))
    place.add("hold", _rect(PARTITION[1], 57.25, FRONT[0], 60.75))
    place.add("locker", _rect(11.25, 57.25, PARTITION[0], 60.75))
    place.add("panel", _rect(PARTITION[0], PANEL[0], PARTITION[1], PANEL[1]))
    place.add("sill", _rect(FRONT[0], DOORWAY[0], FRONT[1], DOORWAY[1]))
    place.add("stair", _rect(FRONT[0] - 0.5, DOORWAY[0], FRONT[0], DOORWAY[1]))
    place.add("gang", _rect(GANG[0], QUAY, GANG[1], 57.25))
    place.add("mast", _rect(*MAST))
    for k, (x, y) in enumerate(CRATES):
        place.add(f"crate_{k}", _rect(x, y, x + 1, y + 1))
    return place.resolve()


def river_edges() -> list[tuple[float, float]]:
    """The way round the hull and its gangplank as the water walks it, from the quay to the quay, in plan units."""
    round_hull = [HULL[0], *reversed(HULL[1:])]          # the stern's north corner, then the stern, the south side, the bow
    return [(GANG[0], QUAY), (GANG[0], 57.0), *round_hull, (GANG[1], 57.0), (GANG[1], QUAY)]


def build(quay, city, river, market_st, *, sky: int, sky_clear: int, market) -> dict:
    """Every piece of the ship, joined to each other, to the water and to the quay. `market` is l3_market, for its tiles."""
    rim = GRADE - market.SHIP_RIM
    deck = rim + market.SHIP_DECK_DROP
    top, hold = deck - HOUSE, deck + 3 * STEP
    plank, hull, board = market.SHIP_PLANK, market.SHIP_HULL, market.SHIP_CABIN_WALL
    #: cell -> floor, its floor's tile, the tile its raised sides wear, its floor's shade
    levels = {"rim": (rim, plank, hull, 24), "shell": (top, plank, hull, 24), "bulkhead": (top, plank, board, 24),
              "deck": (deck, market.BOARDWALK, hull, 28), "hold": (hold, market.BOARDWALK, hull, 30),
              "locker": (hold, market.BOARDWALK, hull, 36), "panel": (top, board, board, 30),
              "sill": (deck + STEP, plank, board, 30), "stair": (deck + 2 * STEP, plank, board, 30),
              "gang": (GRADE, market.BOARDWALK, market.PILE_TILE, 24),
              "mast": (deck - market.SHIP_MAST, plank, market.SHIP_MAST_TILE, 30)}
    CELLS[:] = plan()
    ROOMS.clear()
    for cell in CELLS:
        #: a front wall with a doorway in it is two cells
        floor, tile, side, shade = levels.get(re.sub(r"_\d$", "", cell.name), (deck - 16384, market.CRATE, market.CRATE, 24))
        kwargs = {"declared_zero_exit": True}
        if cell.name == "gang":
            kwargs["floor_slope"] = SlopeSpec(hinge=((_q(GANG[0]), _q(QUAY)), (_q(GANG[1]), _q(QUAY))), rise_z=deck - GRADE)
        if cell.name == "locker":
            kwargs["secret"] = True
        if cell.name == "panel":
            kwargs["sector_behavior"] = {**xsector_direct_use(), "off_floor_z": top, "on_floor_z": hold,
                                         "off_ceiling_z": GRADE - sky_clear, "on_ceiling_z": GRADE - sky_clear,
                                         "busy_time_a": 20, "busy_time_b": 20}
        made = quay.room(f"ship_{cell.name}", cell.outer, frame=Frame(0, 0),
                         role={"locker": "secret", "panel": "doorway"}.get(cell.name, "detail"),
                         faces={f"e{i}": i for i in range(len(cell.outer))}, region_kwargs=kwargs,
                         intent={"kind": "ship"}, note=NOTES.get(cell.name, "a crate on the deck"))
        made.style = Style(floor_picnum=tile, wall_picnum=side, ceiling_picnum=sky, parallax_ceiling=True, floor_z=floor,
                           clear_height=sky_clear - (GRADE - floor), floor_shade=shade,
                           ceiling_shade=14 if cell.name in ("hold", "locker", "stair", "sill") else None)
        for hole in cell.holes:
            made.carve(hole)
        market.SHIP_FACES[made.region_id] = side
        ROOMS[cell.name] = made
    LATE_TYPES.clear()
    LATE_TYPES[ROOMS["panel"].region_id] = 600
    edges = {(a, b): (cell.name, f"e{i}") for cell in CELLS
             for i, (a, b) in enumerate(zip(cell.outer, cell.outer[1:] + cell.outer[:1]))}
    for index, j in enumerate(A.joints(CELLS)):
        a, b = (j.a, j.b) if (j.a, j.b) in edges else (j.b, j.a)
        name, face = edges[a, b]
        other = j.right if name == j.left else j.left
        city.connect(ROOMS[name].face(face), ROOMS[other].face("e0"), connection_id=f"connection:ship_{index}_{name}_{other}")
    for index, (name, a, b) in enumerate(A.rim(CELLS)):
        beyond = market_st if a[1] == b[1] == _q(QUAY) else river
        face = "south" if beyond is market_st else "north"
        city.connect(ROOMS[name].face(edges[a, b][1]), beyond.face(face), connection_id=f"connection:ship_hull_{index}_{name}")
    #: nobody steps off her into a sea 1.75 bodies down
    market.SEA["walk"] += [ROOMS[n].region_id for n in ("rim", "shell", "gang")]
    return ROOMS


NOTES = {"rim": "the gunwale: the highest thing on the hull but the deckhouse", "shell": "the deckhouse's walls, on the hull's own",
         "bulkhead": "the deckhouse's front", "deck": "the deck, a step under the gunwale",
         "hold": "the hold, three steps down under the deckhouse", "locker": "the smuggler's locker: a secret",
         "panel": "a panel of other planks: pushed, it sinks", "sill": "the doorway into the hold", "stair": "a step down into it",
         "gang": "the gangplank, from the quay through the gunwale", "mast": "the mast"}


def _region_at(x: int, y: int):
    from shapely import Point, Polygon
    at = Point(x, y)
    return next(ROOMS[c.name].region_id for c in CELLS if Polygon(c.outer, c.holes).buffer(1).covers(at))


def _art(tile: int):
    import wallplane
    return wallplane.art()[tile]


def _rig(layout) -> int:
    """The yard and its stays, the rope nets up to them, and the lintel over the hold's doorway: wall sprites, seen from both sides."""
    from bloodmap.placement import drawn_extent
    deck, rim = (layout.regions[ROOMS[n].region_id] for n in ("deck", "rim"))
    head = deck.floor_z - 68000
    done = 0

    def hang(name, x, y, top, tile, wide, tall, angle, *, flip=False, **fields):
        """A wall sprite `wide` units by `tall` z, its top at `top`, its middle at (x, y)."""
        nonlocal done
        width, height, _x, offset = _art(tile)
        x_repeat, y_repeat = round(4 * wide / width), round(tall / (4 * height))
        up, _down = drawn_extent(height, offset, y_repeat, 128)
        layout.add_sprite(f"ship:{name}", _region_at(_q(x), _q(y)), x=_q(x), y=_q(y), z=round(top - up), picnum=tile,
                          cstat=16 | 128 | 256 | (4 if flip else 0), angle=angle, x_repeat=x_repeat, y_repeat=y_repeat,
                          **{"shade": 8, "type": 0, "status": 0, "spans_opening": True, **fields})
        done += 1

    def stay(name, x0, z0, x1, z1, y, pieces):
        """A rope from (x0, z0) to (x1, z1): tile 513 laid end over end, each piece begun inside the last one's end.

        The owner, 2026-11-25: "diagonal ropes would need to have little bit of overlapping because how the texture
        is done, right now it has visible gaps even the sprites itself are aligned correctly". The art: the rope
        leaves the tile's first corner and ends at 33 of its 38 columns and 50 of its 52 rows; what is past that is a
        loose tuft. So a piece reaches 38/32 and 52/49 of its share, and the next covers the tuft.
        """
        share_x, share_z = (x1 - x0) / pieces, (z1 - z0) / pieces
        wide, tall = abs(share_x) * PU * ROPE[0] / ROPE[2], abs(share_z) * ROPE[1] / ROPE[3]
        for k in range(pieces):
            left = x0 + k * share_x
            right = left + (wide / PU if share_x > 0 else -wide / PU)
            hang(f"{name}_{k}", (left + right) / 2, y, z0 + k * share_z, 513, wide, tall, 1536, flip=share_x > 0)

    mx, my = (MAST[0] + MAST[2]) / 2, (MAST[1] + MAST[3]) / 2
    hang("yard", mx, MAST[1] - 0.06, head + 18000, 68, 2560, 4096, 1536)
    # the stays: from the mast's head forward to the bow, and aft to the deckhouse's roof (513, "diagonal rope")
    stay("forestay", mx, head, 23.2, rim.floor_z, my, 3)
    stay("backstay", mx, head, FRONT[1], layout.regions[ROOMS["shell"].region_id].floor_z, my, 2)
    # the rope nets (112, E2M1's) stand on the gunwale abreast of the mast
    for side, y in (("port", 57.12), ("starboard", 60.88)):
        for k in range(2):
            hang(f"shroud_{side}_{k}", mx, y, rim.floor_z - 16384 * (k + 1), 112, 1024, 16384, 1536 if side == "port" else 512)
    hang("lintel", FRONT[1] + 0.02, sum(DOORWAY) / 2, layout.regions[ROOMS["shell"].region_id].floor_z, 68, 1280, 4096, 0, shade=-8)
    return done


def dress(layout, river: str) -> dict:
    """The deckhouse's roof, its lantern, her name, what lies in the hold and the locker, and what comes aboard."""
    import wallplane
    from bloodmap import flatsprite
    from bloodmap.placement import seated_z
    from meat_market import spawn
    house = layout.regions[ROOMS["shell"].region_id].floor_z
    # each piece a texel over its neighbours, and every other one a hair lower: laid edge to edge the sky showed
    # through the joints
    roof = flatsprite.cover((_q(11.0), _q(57.0), _q(FRONT[1]), _q(61.0)), _art(178)[:2])
    for k, piece in enumerate(roof):
        layout.add_sprite(f"ship:roof_{k}", _region_at(piece["x"], piece["y"]), x=piece["x"], y=piece["y"],
                          z=house - 128 - 64 * ((piece["x"] // 896 + piece["y"] // 1024) % 2), picnum=178,
                          cstat=32 | 1 | 128 | 256, angle=piece["angle"], x_repeat=piece["x_repeat"] + 2,
                          y_repeat=piece["y_repeat"] + 2, shade=2, type=0, status=0)
    rigging = _rig(layout)

    def add(name, cell, x, y, tile, size, *, up=None, **fields):
        region = layout.regions[ROOMS[cell].region_id]
        _w, height, _x, offset = _art(tile)
        fields = {"cstat": 128, "shade": 4, "type": 0, "status": 0, **fields}
        z = seated_z(seat="floor", floor_z=region.floor_z, ceiling_z=region.ceiling_z, tile_height=height, y_repeat=size,
                     y_offset=offset, cstat=fields["cstat"], clearance=16) - (up or 0)
        return layout.add_sprite(name, region.region_id, x=_q(x), y=_q(y), z=z, picnum=tile, x_repeat=size, y_repeat=size, **fields)

    # a lantern by the doorway and one on a barrel below
    add("ship:lantern_deck", "deck", 14.65, 58.2, 693, 40, up=10000, shade=-128)
    add("ship:barrel_0", "hold", 12.55, 57.6, 925, 60, cstat=385, shade=18)
    add("ship:lantern_hold", "hold", 12.55, 57.62, 693, 36, up=45 * 60 * 4 - 200, shade=-128)
    add("ship:barrel_1", "hold", 13.1, 57.55, 925, 60, cstat=385, shade=18)
    add("ship:barrel_2", "hold", 13.95, 60.4, 925, 60, cstat=385, shade=22)
    pistol = add("harbour:flare_pistol", "hold", 13.2, 60.1, 524, 48, shade=-8, type=43, status=3)
    for k in range(2):
        add(f"harbour:flares_{k}", "hold", 12.75 + 0.2 * k, 60.35, 816, 48, shade=-8, type=76, status=3)
    for k, (kind, tile, size, y) in enumerate(((62, 589, 48, 57.7), (62, 589, 48, 58.1), (63, 809, 48, 58.6), (62, 589, 48, 59.0),
                                               (107, 519, 48, 59.5))):
        add(f"harbour:cache_{k}", "locker", 11.6, y, tile, size, shade=-8, type=kind, status=3)
    add("ship:lantern_locker", "locker", 11.45, 57.45, 693, 32, shade=-128)
    boarded = wires.wire("harbour:boarded")
    boarded.when(wiring.placement(pistol), "pickup", command=motion.CMD_ON, once=True)
    for k, (cell, x, y) in enumerate((("deck", 16.5, 60.2), ("deck", 21.5, 58.6), ("deck", 16.6, 58.1))):
        boarded.then(wiring.placement(spawn(layout, f"harbour:aboard_{k}", 217, ROOMS[cell].region_id, x, y)))
    # her name on the side the quay sees, over the water she lies in
    named = wallplane.text(layout, "ship:name", river, (_q(20.8), _q(57.0)), (_q(15.6), _q(57.0)), words=LETTERED,
                           style=wallplane.style("plain", size=120, palette=5, shade=-40), height_player_heights=(layout.regions[river].floor_z - GRADE + 4600) / 16960,
                           offset_player_widths=0.06, over_steps=True)
    return {"roof": len(roof), "rigging": rigging, "name": len(named or ())}
