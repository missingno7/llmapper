"""L3 for Market Slip: the river gate the player starts in.

Built on the three stages the Foundry pilot proved (role-named materials,
per-building facade variety, light pools), so this module only adds what is
particular to the district:

* the **quay** as an actual boardwalk (the plank floor 352, kept back in
  materials.py for "the thing it actually is" rather than a district's
  roadway) with the river beyond it -- DWE3M10's promenade is single-sided
  frontage against water built as real sectors with boats as geometry;
* the **fountain**, a sunken basin at the depth DWE3M1 builds its basins
  (-4096, water floor), which is also exactly one max-step, so the basin
  stays inside the street's walkable component and adds no walk-around
  loop -- the loop census is at its contract ceiling of 9;
* a **stall run** of three platforms at +3072, TEDE1M2's market module.

Everything is placed from the L1 plan's own `furnish` slots for the area.
"""

from __future__ import annotations

from bloodmap.levelprog import Frame, RECT_FACES, Style

from bloodmap.doors import z_motion_door

from materials import Material, BOARDWALK, FACADES, INTERIORS, MASONRY
from resolution import GRADE, PU, STREET_SKY

#: E4M9's concourse rhythm: unit mouths 1536 wide, one every ~1840 of
#: frontage.  A retail row is that module repeated, not one big shop.
UNIT_MOUTH = 1536
#: The campaign's median room is one wall-texture repeat tall.
ROOM_HEIGHT = 32768
#: A doorway's clear height: half a texture repeat, ~1.9 player heights.
# Campaign z-motion doors open to a median of 31,744 -- 1.87 player
# heights, measured over 1,269 of them; even their 10th percentile is
# 17,408.  Ours were 16,384, which is 0.97 of a player height: the owner
# called them "short like for midgets" and the census agrees.  Blood has
# no door TEXTURE to lean on (E3M1's own door leaves wear 379 and 449,
# plain wall stone), so an opening reads as a door through its proportion
# and its reveal -- which makes this number the whole fix.
DOOR_HEIGHT = 31744

COMPASS = dict(zip(RECT_FACES, range(4)))

#: DWE3M1's basins sit 4096 below their court; that is also the player's
#: max step, so the basin is walkable and costs no loop.
BASIN_DROP = 4096
#: TEDE1M2's market platforms: +3072, one to two plan units across.
STALL_RISE = 3072
#: A river slip shallow enough to climb out of (one max step).
SLIP_DROP = 2048
#: Water, third attempt and this one measured against the right thing.
#: 404 (DWE3M1 basins) and 433 (DWE3M10, whose wet sectors are *underwater*
#: volumes needing a water-link pair) both rendered as dirt at the surface.
#: E3M3's *shallow* water -- the wading kind, which is what a slip and a
#: basin are -- is tile 1120 at xsector `depth` 7, in 16 sectors; that is
#: also the form that made our own sewer trunk read wet.
WATER = 1120
WATER_DEPTH = 7


def _island(place, district, street_room, name, *, x0, y0, x1, y1, floor_z,
            style, note, region_kwargs=None):
    """A sector cut into the street floor, joined on all four faces.

    Every coincident edge has to be a declared portal, so the four faces
    are connected explicitly -- the lesson that recurs in this project.

    `place` is what the island is part of -- the plaza, the quay -- and
    `district` is the node that declares its portals, because the street is
    the other side of every one of them.  Each of these used to be its own
    single-room assembly at the top of the city: `market_stall_0` holding
    `stall_0`, three times over.
    """
    frame = street_room.world_frame()
    street_room.carve([(x0 - frame.dx, y0 - frame.dy), (x1 - frame.dx, y0 - frame.dy),
                       (x1 - frame.dx, y1 - frame.dy), (x0 - frame.dx, y1 - frame.dy)])
    room = place.room(
        name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
        role="detail", faces=dict(COMPASS), frame=Frame(int(x0), int(y0)),
        region_kwargs=region_kwargs or {}, note=note)
    room.style = style
    for face in ("north", "east", "south", "west"):
        district.connect(room.face(face), street_room.face("north"),
                         connection_id=f"connection:market_{name}_{face}")
    return room


def dress(district, market_st, plaza_rect_pu, quay_y_pu, city_d_pu) -> dict:
    """Furnish Market Slip's public space.  Returns what it built."""
    city = district
    facade = FACADES["market_slip"]
    # The two public places of the district, and what stands in each.
    plaza = district.assembly(
        "plaza", note="the market plaza: its fountain and its stalls")
    quay = district.assembly(
        "quay", note="the river gate: boardwalk, water, a moored lighter")
    px0, py0, px1, py1 = (int(v * PU) for v in plaza_rect_pu)
    # `street_joined` are the pieces within one max step of the street,
    # so they enter its walkable component and must be declared to the
    # conformance check; `interiors` do not.
    built = {"rooms": [], "street_joined": [], "interiors": []}

    # ---- the fountain: L1 says centre-offset-west -------------------------
    basin_w = 3 * PU
    cx = px0 + (px1 - px0) // 3
    cy = (py0 + py1) // 2
    # Built through the set-piece constructor, from the mined basin class
    # (36 pieces / 25 maps): concentric tiers descending in even steps to
    # water, standing inside a raised rim.  The hand-built version was one
    # sunk square -- a hole in the plaza, not a fountain.
    import setpieces
    fountain_assembly = plaza.assembly(
        "fountain",
        style=Style(floor_picnum=MASONRY.floor, wall_picnum=MASONRY.wall,
                    ceiling_picnum=facade.ceiling, parallax_ceiling=True,
                    floor_z=GRADE, clear_height=STREET_SKY, floor_shade=24),
        note="the plaza fountain, modelled from the mined basin class")
    water = Material(wall=MASONRY.wall, floor=WATER,
                     ceiling=facade.ceiling, opening=MASONRY.opening, sky=True,
                     note="E3M3's shallow water")
    parts = setpieces.basin(
        fountain_assembly, "fountain", market_st,
        (cx - basin_w // 2, cy - basin_w // 2,
         cx + basin_w // 2, cy + basin_w // 2),
        MASONRY, water, grade=GRADE, host_clear=STREET_SKY,
        tiers=2, wall_thickness=512, connector=city,
        note="the plaza fountain")
    basin = parts["rim"]
    built["rooms"].append(parts["well"].region_id)
    built["rooms"].append(basin.region_id)
    built["street_joined"].append(basin.region_id)

    # ---- the stall run: three platforms along the plaza's west edge -------
    stall_w, stall_d = int(1.5 * PU), 2 * PU
    for index in range(3):
        sy = py0 + int((index * 3 + 1.5) * PU)
        stall = _island(
            plaza, district, market_st, f"stall_{index}",
            x0=px0 + PU, y0=sy, x1=px0 + PU + stall_w, y1=sy + stall_d,
            floor_z=GRADE - STALL_RISE,
            style=Style(floor_picnum=BOARDWALK, wall_picnum=MASONRY.wall,
                        ceiling_picnum=facade.ceiling, parallax_ceiling=True,
                        floor_z=GRADE - STALL_RISE,
                        clear_height=STREET_SKY - STALL_RISE, floor_shade=30),
            note="market stall platform (TEDE1M2 module)")
        built["rooms"].append(stall.region_id)
        built["street_joined"].append(stall.region_id)

    # ---- the quay: boards along the water edge ----------------------------
    quay_y = int(quay_y_pu * PU)
    board_y0 = quay_y + int(3.5 * PU)
    board_y1 = quay_y + int(5.5 * PU)
    boards = _island(
        quay, district, market_st, "boardwalk",
        x0=int(4 * PU), y0=board_y0, x1=int(52 * PU), y1=board_y1,
        floor_z=GRADE,
        style=Style(floor_picnum=BOARDWALK, wall_picnum=facade.wall,
                    ceiling_picnum=facade.ceiling, parallax_ceiling=True,
                    floor_z=GRADE, clear_height=STREET_SKY, floor_shade=30),
        note="the quay's boards: promenade-patterns, single-sided frontage")
    built["rooms"].append(boards.region_id)
    built["street_joined"].append(boards.region_id)
    built["boardwalk"] = boards

    # ---- the river: DWE3M10 builds its water as real sectors with boats
    # as geometry, not as a painted edge.  A slip one max-step deep, so the
    # player can step down to the water and back out.
    river_y0 = int(city_d_pu * PU)
    river_x0, river_x1 = int(4 * PU), int(52 * PU)
    # Deep enough that the far bank falls into the engine's own fog rather
    # than reading as the wall of a tank (visibility 800, E3M1's own).
    river_depth = 16 * PU
    river = quay.room(
        "river", [(0, 0), (river_x1 - river_x0, 0),
                  (river_x1 - river_x0, river_depth), (0, river_depth)],
        role="exterior", faces=dict(COMPASS),
        frame=Frame(river_x0, river_y0),
        region_kwargs={"sector_behavior": {"depth": WATER_DEPTH}},
        note="the river beyond the quay (promenade-patterns)")
    river.style = Style(floor_picnum=WATER, wall_picnum=MASONRY.wall,
                        ceiling_picnum=facade.ceiling, parallax_ceiling=True,
                        floor_z=GRADE + SLIP_DROP,
                        clear_height=STREET_SKY + SLIP_DROP, floor_shade=26)
    city.connect(river.face("north"), market_st.face("south"),
                 connection_id="connection:quay_river")
    built["rooms"].append(river.region_id)
    built["street_joined"].append(river.region_id)

    # A moored boat: a deck standing in the water, geometry not sprite.
    boat_w, boat_d = 4 * PU, 2 * PU
    boat_x0 = river_x0 + 12 * PU
    boat_y0 = river_y0 + 4 * PU
    river.carve([(boat_x0 - river_x0, boat_y0 - river_y0),
                 (boat_x0 - river_x0 + boat_w, boat_y0 - river_y0),
                 (boat_x0 - river_x0 + boat_w, boat_y0 - river_y0 + boat_d),
                 (boat_x0 - river_x0, boat_y0 - river_y0 + boat_d)])
    boat = quay.room(
        "boat", [(0, 0), (boat_w, 0), (boat_w, boat_d), (0, boat_d)],
        role="detail", faces=dict(COMPASS), frame=Frame(boat_x0, boat_y0),
        note="a moored lighter: deck boards over the water")
    boat.style = Style(floor_picnum=BOARDWALK, wall_picnum=BOARDWALK,
                       ceiling_picnum=facade.ceiling, parallax_ceiling=True,
                       floor_z=GRADE - 1024, clear_height=STREET_SKY - 1024,
                       floor_shade=28)
    for face in ("north", "east", "south", "west"):
        city.connect(boat.face(face), river.face("north"),
                     connection_id=f"connection:boat_{face}")
    built["rooms"].append(boat.region_id)
    built["street_joined"].append(boat.region_id)

    # ---- the market hall: E4M9's retail row, inside block A --------------
    # The block is a hole in the district's street region, so its inside is
    # void: interiors are placed in it directly, no carving needed.
    shop, common = INTERIORS["shop"], INTERIORS["common"]
    import citytree
    hall = district.assembly(
        "market_hall",
        style=Style(**common.style_kwargs(floor_z=GRADE,
                                          clear_height=ROOM_HEIGHT,
                                          floor_shade=32)),
        note="market hall: concourse plus two units (E4M9 grammar)")
    citytree.declare_venue(hall, "market_hall", "retail_row",
                           built_by="l3_market")

    def room(name, x0, y0, x1, y1, material, note, **kw):
        r = hall.room(
            name, [(0, 0), (int((x1 - x0) * PU), 0),
                   (int((x1 - x0) * PU), int((y1 - y0) * PU)),
                   (0, int((y1 - y0) * PU))],
            role=kw.pop("role", "interior"), faces=dict(COMPASS),
            frame=Frame(int(x0 * PU), int(y0 * PU)),
            region_kwargs={**material.region_kwargs(), **kw.pop("rk", {})},
            note=note)
        r.surfaces(**material.style_kwargs(floor_z=GRADE,
                                           clear_height=ROOM_HEIGHT))
        return r

    concourse = room("concourse", 10.5, 42.5, 13.5, 48.5, common,
                     "the hall's concourse; units open off its west side")
    # Each unit meets the concourse through a mouth-sized neck.  Two rooms
    # sharing only part of an edge leave the remainder coincident and
    # unpaired; a neck whose whole face is the mouth avoids that, and it is
    # what a storefront reveal is anyway.
    unit_a = room("unit_a", 7.5, 43.0, 10.0, 45.5, shop,
                  "retail unit: the chandlery's neighbour")
    unit_b = room("unit_b", 7.5, 45.8, 10.0, 48.3, shop,
                  "retail unit: differentiated by its stock, not its plan")
    neck_a = room("neck_a", 10.0, 43.75, 10.5, 44.75, shop,
                  "unit A's storefront reveal")
    neck_b = room("neck_b", 10.0, 46.55, 10.5, 47.55, shop,
                  "unit B's storefront reveal")
    # Two bays wide (2048) with both edges on the 1024 bay grid, so the
    # opening replaces whole painted bays instead of slicing windows in
    # half.  E3M1's modal street opening is one bay; a public hall takes
    # two.
    #
    # A door in a six-storey facade needs MEDIATION, not just a leaf.  With
    # the door opening straight onto the street, Build draws the whole wall
    # above it from the door's own tile -- a brown slab of "door" rising six
    # storeys, which is what the stall frame showed.  A porch with a
    # door-height ceiling gives the facade back the wall above the opening
    # (the project's aperture grammar: a leaf plus its mediation).
    porch = room("porch", 14.0, 45.0, 15.0, 47.0, common,
                 "the hall's porch: the reveal that owns the wall above",
                 role="gateway")
    porch.surfaces(wall_picnum=facade.opening, ceiling_picnum=facade.opening,
                   clear_height=DOOR_HEIGHT)
    door = room("door", 13.5, 45.0, 14.0, 47.0, common,
                "the hall's door onto the plaza", role="doorway",
                rk={"type": 600, "door_face": 22, "inherit_finish": "both",
                    "sector_behavior": z_motion_door(GRADE, GRADE - 16384)})
    # A doorway's jambs belong to the room that LOOKS at them.  Left on the
    # interior material, the hall's jamb put papered wall (108) on a surface
    # the plaza sees floor-to-sky; it takes the facade's opening tile.
    door.surfaces(wall_picnum=facade.opening, clear_height=0)
    # Anchor a partial join from the SMALLER face: a connection takes its
    # geometry from the left anchor, so anchoring on the long concourse
    # wall leaves the unit's own edge unpaired (the recurring lesson).
    for tag, unit, neck in (("a", unit_a, neck_a), ("b", unit_b, neck_b)):
        hall.connect(neck.face("west"), unit.face("east"),
                     connection_id=f"connection:hall_unit_{tag}_in")
        hall.connect(neck.face("east"), concourse.face("west"),
                     connection_id=f"connection:hall_unit_{tag}_out")
    hall.connect(door.face("west"), concourse.face("east", at=0.5,
                                                   width=UNIT_MOUTH),
                 connection_id="connection:hall_door_in")
    hall.connect(porch.face("west"), door.face("east"),
                 connection_id="connection:hall_porch_door")
    city.connect(porch.face("east"), market_st.face("north"),
                 connection_id="connection:hall_porch_plaza")
    built["hall"] = {"concourse": concourse.region_id,
                     "unit_a": unit_a.region_id, "unit_b": unit_b.region_id}
    built["rooms"] += [concourse.region_id, unit_a.region_id, unit_b.region_id]
    built["interiors"] += [concourse.region_id, unit_a.region_id,
                           unit_b.region_id, neck_a.region_id,
                           neck_b.region_id]
    return built
