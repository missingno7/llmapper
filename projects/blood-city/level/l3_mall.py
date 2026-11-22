"""The Gravesend Arcade: a shopping mall, from E4M9's own proportions.

Owner: add a shopping mall; E4M9 is the campaign's, and E6M1 has the shop.

What E4M9 actually is, measured rather than remembered: a **tall concourse**
with units opening straight onto it.  Its concourse sectors run **3.86 to
4.35 player heights** where its retail units run 1.8 to 2.9 — the height
difference *is* the mall.  Units sit at the concourse's own floor level
(step +0) with a few raised half a player (-8192), and unit areas cluster
between 0.4M and 6M square units.

The shopfronts are E6M1's, which this project already built once for the
pawn shop: a shallow display box between the shop and the public space,
floor raised as a plinth, glazed on the public side with a masked
translucent wall and an XWALL that lets it be shot out (see `glass.py`).

Three lessons from elsewhere land here:

* **Name the uses.**  DukCity spells its businesses on the wall — SHOPPING
  CENTER, PHARMACY, TOYS US, BOOKS, NEWS — roughly ten named uses a map,
  where Gravesend had five venues in the whole city.  Each unit here is
  named, in `signage.py`.
* **A key placard means a keyed door.**  The service corridor behind the
  arcade is locked, carries `XSECTOR.key`, and the eye emblem hangs beside
  it because that is what the emblem is for.  The key itself is in a unit,
  reachable.
* **Ambience.**  Sound 65 is E4M9's own, and E4M9 is its heaviest user in
  the corpus (5 of its 11 instances).
"""

from __future__ import annotations

import wires
from bloodmap import wiring

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.slope import SlopeSpec

import keysign
import setpieces
import templates
from materials import FACADES, INTERIORS, MASONRY, Material
from resolution import GRADE, PU

COMPASS = dict(zip(RECT_FACES, range(4)))

#: market_block_c, the biggest unbuilt block in the city.
MASS = (39 * PU, 40 * PU, 53 * PU, 50 * PU)

DOOR_D = PORCH_D = 256
DOOR_H = 31744            # the campaign's median door opening
CONCOURSE_H = 65536       # 3.86 player heights: E4M9's concourse
UNIT_H = 28672            # 1.69: E4M9's retail units
SERVICE_H = 24576
# A concourse is a hall, not an extra-wide room.  This shallow clerestory-like
# pitch supplies the missing interior volume while leaving every shop front
# and portal at its existing clear height.
CONCOURSE_PITCH = 8192

#: The concourse's pools of light (fractions of its length), their size,
#: and the shades: lit floor against the hall's (`place_character`'s light
#: layer wants a spread of 12)
POOL_AT, POOL_W, POOL_INSET = (1 / 6, 1 / 2, 5 / 6), 1536, 768
POOL_SHADE, CONCOURSE_FLOOR_SHADE = 6, 30
#: The arcade's clock: the landmark the round-2 reader asked for, at the
#: far (east) end, high, where the whole concourse sees it
CLOCK_TILE, CLOCK_REPEAT = 1165, 96

#: The key the service corridor needs.  2 is the eye; its placard is 2541
#: and its item is sprite type 101.
SERVICE_KEY = 2

#: The concourse, which is the only thing here stated as a rectangle: it is
#: the site, and everything else is derived from it.
CONCOURSE = (40448, 44544, 51712, 47616)

NECK_D = 512
#: The band each range's openings live in.
NORTH_BAND = (CONCOURSE[1] - NECK_D, CONCOURSE[1])
SOUTH_BAND = (CONCOURSE[3], CONCOURSE[3] + NECK_D)
UNIT_D = 2048
#: How deep a display box stands in front of its shop.
WINDOW_PLINTH = 4096

#: **The ranges are generated, not drawn.**  They used to be six literal
#: rectangles on a fixed 3x2 grid at absolute coordinates, so the arcade
#: could not answer the only question a retail row is ever asked: how many
#: shops fit here?  `templates.retail_row` answers it from the frontage,
#: at E4M9's own measured rhythm -- a 2,560-unit unit (its median across 51
#: units) opening on 1,536 (its median across 85 shared walls).  Hand it a
#: longer concourse and it builds more shops.
import templates as _templates

#: One unit per range is glazed, because a mall whose every unit is behind
#: glass has no way in and a mall with none is a corridor of doors.
GLAZED = (0,)

RANGES = {
    "north": _templates.retail_row(
        start=CONCOURSE[0], end=CONCOURSE[2], band=NORTH_BAND[0],
        side="north", depth=UNIT_D, glaze=GLAZED),
    "south": _templates.retail_row(
        start=CONCOURSE[0], end=CONCOURSE[2], band=SOUTH_BAND[1],
        side="south", depth=UNIT_D, glaze=GLAZED),
}
#: Unit names stay a, b, c ... so signage and the key placard keep working.
_LETTERS = "abcdefghijklmnop"


def _unit_name(side, index):
    return "unit_" + _LETTERS[index + (0 if side == "north" else
                                       len(RANGES["north"]))]


ROOMS = [
    ("concourse", *CONCOURSE, "common", CONCOURSE_H,
     "the arcade concourse: E4M9's height, which is what makes it a mall"),
] + [
    (_unit_name(side, unit.index), *unit.rect, "shop", UNIT_H,
     f"a retail unit ({side} range, {unit.index})")
    for side, units in RANGES.items() for unit in units
] + [
    ("service", 51968, 44544, 53760, 47616, "service", SERVICE_H,
     "the service corridor, behind the keyed door"),
]

#: Necks: each unit reaches the concourse through its own opening, so the
#: rest of its frontage can be glass.  (unit, x0, x1, side)
NECKS = [
    (_unit_name(side, unit.index), unit.opening[0], unit.opening[1], side)
    for side, units in RANGES.items() for unit in units
]

#: What the two glazed units are, lettered small on their fascias.  A blind
#: reviewer on the first build: "the mall units sell nothing ... no set has
#: a sign".  The four that open by a neck are named on their inside walls
#: (`signage.SIGNS`); these two had no name anywhere.
#: What each unit sells: its lettering says so, and its shelf is stocked by it.
SELLS = {"unit_a": "draper", "unit_b": "apothecary", "unit_c": "ironmonger",
         "unit_d": "clocks", "unit_e": "books", "unit_f": "tobacco"}
WINDOW_NAMES = {"unit_a": "DRAPER", "unit_d": "CLOCKS"}

#: Glazed display boxes, the E6M1 shopfront: (unit, x0, x1, side, plinth).
#: One per range, because a mall whose every unit is behind glass has no way
#: in and a mall with none is a corridor of doors.  The pane takes the
#: frontage left over beside the unit's own opening, so it never overlaps it.
WINDOWS = [
    (_unit_name(side, unit.index), unit.window[0], unit.window[1],
     side, WINDOW_PLINTH)
    for side, units in RANGES.items() for unit in units
    if unit.window is not None
]


def build(city, market_st):
    """The arcade, its units, its glazing and its locked service door."""
    facade = FACADES["market_slip"]
    arcade = city.assembly(
        "gravesend_arcade",
        style=Style(**INTERIORS["common"].style_kwargs(
            floor_z=GRADE, clear_height=CONCOURSE_H)),
        note="the Gravesend Arcade: E4M9's concourse, E6M1's shopfronts",
    )
    import citytree
    citytree.declare_venue(arcade, "arcade", "retail_row", built_by="l3_mall")
    rooms: dict = {}

    def make(name, x0, y0, x1, y1, key, clear, note, *, role="interior",
             floor_z=GRADE, rk=None):
        material = INTERIORS[key]
        made = arcade.room(
            name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
            role=role, faces=dict(COMPASS), frame=Frame(int(x0), int(y0)),
            region_kwargs={**material.region_kwargs(), **(rk or {})},
            note=note)
        made.surfaces(**material.style_kwargs(floor_z=floor_z,
                                              clear_height=clear))
        rooms[name] = made
        return made

    for name, x0, y0, x1, y1, key, clear, note in ROOMS:
        # The service corridor's only exit is the keyed door, which is shut
        # at rest -- which is what "locked" means.  The geometry audit
        # rightly flags a room with no walkable-at-rest exit unless it is
        # DECLARED as gated, so declare it rather than weaken the lock.
        rk = {"declared_zero_exit": True} if name == "service" else {}
        if name == "concourse":
            # Hinge on the long west edge so the roof pitch reads along the
            # public route, not across individual shop fronts.
            rk["ceiling_slope"] = SlopeSpec(
                hinge=((x0, y1), (x0, y0)), rise_z=-CONCOURSE_PITCH)
        make(name, x0, y0, x1, y1, key, clear, note, rk=rk)

    # LIGHT DOWN THE CONCOURSE. The build reports the arcade "lacks light"
    # (floor shades spread under 12 across it), and the showcase's blind
    # reader: "dim lighting ... the continuous dark brickwork". Three pools
    # of lit floor down the hall's axis, each under a hanging lamp
    # (`dress`), give it light and a rhythm. Each pool's ceiling keeps the
    # concourse's pitch: in Build a slope pivots on the sector's first wall,
    # so a pool hinged on its own west edge, at the roof's height there and
    # rising at the same rate, lies flush with it.
    cx0, cy0, cx1, cy1 = CONCOURSE
    span = cx1 - cx0
    for index, frac in enumerate(POOL_AT):
        px0 = int(cx0 + frac * span - POOL_W / 2)
        px1, py0, py1 = px0 + POOL_W, cy0 + POOL_INSET, cy1 - POOL_INSET
        pool = setpieces.raised_solid(
            arcade, f"concourse_pool_{index}", rooms["concourse"],
            (px0, py0, px1, py1), INTERIORS["common"], grade=GRADE, rise=0,
            host_clear=CONCOURSE_H, connector=arcade,
            note="light on the concourse floor under a hanging lamp")
        lift = CONCOURSE_PITCH * (px0 - cx0) / span
        pool.surfaces(clear_height=int(round(CONCOURSE_H + lift)), floor_shade=POOL_SHADE)
        pool.region_kwargs["ceiling_slope"] = SlopeSpec(
            hinge=((px0, py1), (px0, py0)),
            rise_z=-CONCOURSE_PITCH * (px1 - px0) / span)
        rooms[f"concourse_pool_{index}"] = pool
    rooms["concourse"].surfaces(floor_shade=CONCOURSE_FLOOR_SHADE)

    # Each unit reaches the concourse through its own neck, so the frontage
    # beside it is free for glass.
    for unit, nx0, nx1, side in NECKS:
        y0, y1 = NORTH_BAND if side == "north" else SOUTH_BAND
        neck = make(f"{unit}_neck", nx0, y0, nx1, y1, "shop", UNIT_H,
                    f"{unit}'s opening onto the concourse", role="gateway")
        # A north-range unit sits north of the concourse, so its opening
        # joins the unit on its north face and the concourse on its south.
        inner, outer = ("north", "south") if side == "north" else ("south", "north")
        arcade.connect(neck.face(inner), rooms[unit].face(outer),
                       connection_id=f"connection:{unit}_neck_shop")
        arcade.connect(neck.face(outer), rooms["concourse"].face(side),
                       connection_id=f"connection:{unit}_neck_concourse")

    # Glazed display boxes: shop on one side, concourse on the other, which
    # is the two-sided wall breakable glass needs.
    import glass
    for unit, wx0, wx1, side, plinth in WINDOWS:
        y0, y1 = NORTH_BAND if side == "north" else SOUTH_BAND
        inner, outer = ("north", "south") if side == "north" else ("south", "north")
        front = glass.shopfront((wx0, y0, wx1, y1), outer)

        def part(name, rect, note, _plinth=plinth):
            return make(name, *rect, "shop", UNIT_H - _plinth, note,
                        role="detail", floor_z=GRADE - _plinth)

        box = part(f"{unit}_window", front["box"], f"{unit}'s display window")
        reveal = part(f"{unit}_window_reveal", front["reveal"],
                      f"{unit}'s window surround: riser and fascia")
        glass.surround(front, name=f"{unit}_window", kind="arcade",
                       reveal=reveal, box=box, shop=rooms[unit], grade=GRADE,
                       sill=plinth, box_clear=UNIT_H - plinth,
                       words=WINDOW_NAMES.get(unit))
        for index, rect in enumerate(front["sashes"]):
            sash = part(f"{unit}_window_sash_{index}", rect,
                        "a sash pocket: the pane hangs at its back")
            sash.surfaces(wall_picnum=glass.JAMB_TILE)
            arcade.connect(sash.face(outer), reveal.face(inner),
                           connection_id=f"connection:{unit}_window_sash_{index}_reveal")
            arcade.connect(sash.face(inner), box.face(outer),
                           connection_id=f"connection:{unit}_window_sash_{index}_box")
        arcade.connect(box.face(inner), rooms[unit].face(outer),
                       connection_id=f"connection:{unit}_window_shop")
        arcade.connect(reveal.face(outer), rooms["concourse"].face(side),
                       connection_id=f"connection:{unit}_window_concourse")

    # **The units are furnished by a template, not left empty.**  Six retail
    # units with nothing in them is what "the buildings are still empty"
    # meant; `templates.shop` fits each one out from its own rect -- a shelf
    # run of pedestals down its long side, a counter across its front --
    # and each of those runs is itself a parametric fixture family.  This is
    # the composition chain: retail_row -> shop -> run -> fixture.
    fitted = []
    for _side, _units in RANGES.items():
        for _unit in _units:
            _name = _unit_name(_side, _unit.index)
            #: A unit's back wall is the one away from the concourse, and
            #: it has void behind it: the stock goes in a shelf there.
            fitted.append(templates.shop(
                rooms[_name], material=INTERIORS["shop"], grade=GRADE,
                host_clear=UNIT_H, margin=384,
                back="north" if _side == "north" else "south",
                sells=SELLS.get(_name, "")))
    rooms["_fitted"] = fitted

    # The street entrance: concourse -> door -> porch -> the market street.
    entry_y0, entry_y1 = 45568, 46592
    door = make("entry_door", 40192, entry_y0, 40448, entry_y1, "common", 0,
                "the arcade entrance", role="doorway",
                rk={"type": 600, "door_face": 22, "inherit_finish": "both",
                    "sector_behavior": z_motion_door(GRADE, GRADE - DOOR_H)})
    door.surfaces(wall_picnum=facade.opening, floor_z=GRADE, clear_height=0)
    porch = make("entry_porch", 39936, entry_y0, 40192, entry_y1, "common",
                 DOOR_H, "the arcade reveal", role="gateway")
    porch.surfaces(wall_picnum=facade.opening, ceiling_picnum=facade.opening,
                   floor_z=GRADE, clear_height=DOOR_H)
    arcade.connect(door.face("east"), rooms["concourse"].face("west"),
                   connection_id="connection:arcade_entry_in")
    arcade.connect(porch.face("east"), door.face("west"),
                   connection_id="connection:arcade_entry_porch")
    city.connect(porch.face("west"), market_st.face("north"),
                 connection_id="connection:arcade_entry_street")

    # The keyed service door.  A placard is only ever emitted beside a door
    # that really carries the key -- see keysign.py.
    key_door = make("service_door", 51712, entry_y0, 51968, entry_y1,
                    "service", 0, "the service door: needs the eye key",
                    role="doorway",
                    rk={"type": 600, "door_face": 22,
                        "inherit_finish": "both",
                        "sector_behavior": z_motion_door(
                            GRADE, GRADE - DOOR_H, key=SERVICE_KEY)})
    key_door.surfaces(wall_picnum=MASONRY.wall, floor_z=GRADE, clear_height=0)
    arcade.connect(key_door.face("west"), rooms["concourse"].face("east"),
                   connection_id="connection:arcade_service_in")
    arcade.connect(key_door.face("east"), rooms["service"].face("west"),
                   connection_id="connection:arcade_service_out")

    # The extinguisher and what is behind it. The owner, 2026-11-18: "fire
    # extinguisher ... is usually thing that will explode and reveal hole
    # in the wall behind it, it is something that can possibly reveal
    # secret room for example in staff only part of arcades".
    #
    # Transcribed from E3M4 sprite 331 and E1M2 sprite 489 (the one whose
    # hole is a counted secret): the extinguisher is a kThingObjectGib that
    # a bullet breaks, its death sends its channel (actor.cpp:3513 ->
    # triggers.cpp:103), a closed Z-motion sector in the wall behind it
    # opens in a tenth of a second, and exploders on the same channel go
    # off staggered. None of the campaign's nine uses a gib WALL.
    cache = make("service_cache", *SECRET_CACHE, "service", SERVICE_H,
                 "the cache behind the service corridor's wall: a secret",
                 role="secret",
                 rk={"secret": True, "declared_zero_exit": True})
    # the hole the blast leaves: ragged, the way Blood's are (the owner,
    # 2026-11-22: "Blown out holes are usually using sloped floor and
    # ceiling and usually aren't regular"), blown from the corridor
    # (its near side, the north wall at y 44,544) through to the cache
    from bloodmap import breach
    x0, y0, x1, y1 = SECRET_SEAL
    wall = INTERIORS["service"]
    material = Material(wall=wall.wall, floor=wall.wall, ceiling=wall.wall, opening=wall.wall,
                        note="the blown wall: its own plaster and brick")
    for index, piece in enumerate(breach.lay(
            arcade, "service_seal", secret_pieces(), origin=(x1, y1), along=(-1, 0), through=(0, -1),
            near_floor=GRADE, region_kwargs=material.region_kwargs(), rx_id=SECRET_CHANNEL,
            note="the wall behind the extinguisher: blown open, once",
            surfaces=material.style_kwargs(floor_z=GRADE, clear_height=0))):
        rooms[piece.node_id] = piece
        wires.wire("arcade:cache").then(wiring.region(piece.region_id))
        LATE_TYPES[piece.region_id] = 600
        arcade.connect(piece.face("near"), rooms["service"].face("north"),
                       connection_id=f"connection:arcade_cache_blast_{index}")
        arcade.connect(piece.face("far"), cache.face("south"),
                       connection_id=f"connection:arcade_cache_in_{index}")

    # The four hand-placed counters that used to sit here are gone: they
    # were four of six units furnished, each a literal rect derived from
    # its host's own origin.  `templates.shop` furnishes all six, from the
    # same counter family, at whatever size the unit turns out to be.
    return rooms


#: The extinguisher's channel, the blast hole and the cache behind it.
SECRET_CHANNEL = wires.channel("arcade:cache")
#: the blown wall: 1,280 wide, the campaign's median blast hole (E3M4's
#: wall 2361 was 640, too narrow to leave a ragged hole a body walks
#: through), the cache's whole width, in four pieces
SECRET_SEAL = (52224, 44032, 53504, 44544)
SECRET_CACHE = (52224, 43008, 53504, 44032)
SECRET_HOLE = 20480                              # E3M4 s320: 18,432-26,624
#: its sills over the corridor's floor, and its ragged top under the
#: corridor's ceiling, or that ceiling's edge is all that shows of it
SECRET_SILL, SECRET_TOP = (256, 1536), SERVICE_H - 512
#: region id -> sector type, set by the build once the doors are framed
LATE_TYPES: dict = {}


def secret_pieces() -> list:
    """The blown wall's pieces, in its own frame (`bloodmap.breach.ragged`)."""
    from bloodmap import breach
    x0, y0, x1, y1 = SECRET_SEAL
    return breach.ragged(x1 - x0, y1 - y0, seed="arcade:service_seal", pieces=4,
                         sill=SECRET_SILL, top=SECRET_TOP)
#: E3M4 sprite 331, field for field
EXTINGUISHER = {"type": 416, "picnum": 658, "cstat": 464, "x_repeat": 40,
                "y_repeat": 40, "status": 4,
                "behavior": {"tx_id": SECRET_CHANNEL, "command": 1,
                             "trigger_on": 1, "trigger_off": 1,
                             "trigger_once": 1, "trigger_vector": 1,
                             "data_1": 5, "data_4": 314}}
#: E3M4 sprites 332-334: (local in the corridor, tenths of a second)
EXPLODERS = (((0.40, 0.06), 1), ((0.52, 0.10), 4), ((0.46, 0.14), 3))


def extinguisher_secret(layout, rooms) -> dict:
    """Hang the extinguisher on the seal and arm the charges behind it."""
    service = rooms["service"]
    x0, y0, x1, _y1 = 51968, 44544, 53760, 47616
    centre = (SECRET_SEAL[0] + SECRET_SEAL[2]) // 2
    layout.place_on_wall(
        "mall:service_extinguisher", service.region_id,
        a1=(x0, y0), a2=(x1, y0), t=(centre - x0) / (x1 - x0),
        height_player_heights=0.87, offset_player_widths=0.06,
        #: it hangs on the wall that opens, and goes with it
        spans_opening=True, **EXTINGUISHER)
    wires.wire("arcade:cache").when(
        wiring.placement("mall:service_extinguisher"), "vector", command=1,
        on=True, off=True, once=True)
    for index, (local, wait) in enumerate(EXPLODERS):
        layout.place_on_floor(
            f"mall:service_charge_{index}", service.region_id, local=local,
            type=459, picnum=908, cstat=128, x_repeat=4, y_repeat=64,
            status=11, behavior={"rx_id": SECRET_CHANNEL, "wait_time": wait})
        wires.wire("arcade:cache").then(
            wiring.placement(f"mall:service_charge_{index}"))
    return {"channel": SECRET_CHANNEL, "charges": len(EXPLODERS)}


#: Where the placard hangs, and where the key it names can be found.
def dress(layout, rooms, attested) -> dict:
    import ambience
    import props

    report = {}
    report["extinguisher_secret"] = extinguisher_secret(layout, rooms)
    for index, (type_id, local) in enumerate(((62, (0.3, 0.4)),
                                              (65, (0.7, 0.4)),
                                              (109, (0.5, 0.7)))):
        spec = attested(type_id)
        if spec is not None:
            layout.place_on_floor(f"mall:cache_{type_id}_{index}",
                                  rooms["service_cache"].region_id,
                                  local=local, **spec["fields"])
    # The placard, on the concourse wall beside the service door.
    concourse = rooms["concourse"]
    keysign.placard(layout, "keysign:arcade_service", concourse.region_id,
                    ((51712, 46592), (51712, 47360)), SERVICE_KEY)
    # And the key itself, in a unit, so the lock is not a wall.
    keysign.item(layout, "key:arcade_eye", rooms["unit_f"].region_id,
                 SERVICE_KEY, local=(0.2, 0.3))    # the customer's side
    report["keyed_door"] = "eye"

    # E4M9's own ambience, in the concourse and the two ranges.
    # Through `ambience.fill`, which tests containment: a furnished unit is
    # a unit with holes in it, and the centre of one is now its counter.
    spots = [(concourse.region_id, "mall", (0.25, 0.5)),
             (concourse.region_id, "mall", (0.75, 0.5)),
             (rooms["unit_b"].region_id, "mall", (0.5, 0.5)),
             (rooms["unit_e"].region_id, "mall", (0.5, 0.5))]
    report["ambience"] = ambience.fill(layout, spots)["placed"]

    # Population and finds, attested as everywhere else.
    for index, (name, type_id, local) in enumerate(
            [("concourse", 202, (0.2, 0.4)), ("concourse", 203, (0.8, 0.6)),
             ("unit_a", 202, (0.5, 0.4)), ("unit_e", 203, (0.5, 0.3)),
             ("service", 202, (0.5, 0.5)),
             #: (the customer's side of each counter: behind a hip-high one
             #: a find is out of reach)
             ("unit_c", 65, (0.4, 0.2)), ("unit_d", 62, (0.5, 0.3)),
             ("service", 109, (0.3, 0.6))]):
        spec = attested(type_id)
        if spec is None or name not in rooms:
            continue
        # The units are furnished by a template now, so where the fixtures
        # are depends on how big the unit came out.  A hand-written local
        # that used to be "clear of the counter" cannot know that any more;
        # asking the room is the only version that stays true.
        region_id = rooms[name].region_id
        free = props.free_local(layout.regions[region_id], local)
        if free is None:
            continue
        layout.place_on_floor(f"mall:{name}_{type_id}_{index}",
                              region_id, local=free, **spec["fields"])
    # A brazier at each end of the concourse: it is the city's longest room.
    for index, (face, t) in enumerate((("north", 0.08), ("south", 0.92))):
        props.mount_on_wall(layout, f"mall:brazier_{index}", concourse, face,
                            t=t)
    # A brass lamp hung over each pool (945, "brass hanging lamp, lit shade",
    # as E1M2, E2M4 and E3M2 hang it), seated half its drawn height under
    # the roof, and a source at it.
    report["lamps"] = 0
    for index in range(len(POOL_AT)):
        pool = rooms[f"concourse_pool_{index}"]
        region = layout.regions[pool.region_id]
        layout.place_on_ceiling(
            f"mall:pool_lamp_{index}", pool.region_id, local=(0.5, 0.5),
            height_player_heights=(30 * 64 * 2) / 16960, picnum=945, cstat=0,
            x_repeat=64, y_repeat=64, shade=-16, pal=0, type=0, status=0)
        xs = [p[0] for p in region.outer]
        ys = [p[1] for p in region.outer]
        layout.add_light_source(
            f"light:mall_pool_{index}", pool.region_id,
            x=(min(xs) + max(xs)) // 2, y=(min(ys) + max(ys)) // 2,
            z=int(region.floor_z - 2.2 * 16960), intensity=2.0)
        report["lamps"] += 1
    # THE CLOCK. Round 2's reader: "the arcade lacks a landmark ... build a
    # tall, illuminated clock into the far bay". The owner's "wall clock"
    # (1165), large and high on the concourse's east end wall, over the
    # keyed door, facing the whole hall; a lamp under it.
    cx0, cy0, cx1, cy1 = CONCOURSE
    # Over the door's head, which is where an arcade hangs its clock: the
    # wall either side of the door is 1,024 and the clock 1,536, so
    # `wallplane.sprite` (one free stretch of wall) has no slot for it; the
    # wall over the opening is solid from the door's head up.
    layout.place_on_wall(
        "mall:clock", concourse.region_id, a1=(cx1, cy0), a2=(cx1, cy1), t=0.5,
        height_player_heights=2.9, offset_player_widths=0.04,
        picnum=CLOCK_TILE, x_repeat=CLOCK_REPEAT, y_repeat=CLOCK_REPEAT,
        cstat=16 | 64 | 128, shade=-12, type=0, status=0)
    report["clock"] = True
    return report
