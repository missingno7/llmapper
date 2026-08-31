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
# The shop itself has the E6M1 retail clearance: a full normal-scale crate
# tile is 32,768 z units tall, so the selling floor needs an upper bay above
# it rather than clipping the crate into its ceiling.
MARKET_HALL_HEIGHT = 49152
#: A doorway's clear height: half a texture repeat, ~1.9 player heights.
# Campaign z-motion doors open to a median of 31,744 -- 1.87 player
# heights, measured over 1,269 of them; even their 10th percentile is
# 17,408.  Ours were 16,384, which is 0.97 of a player height: the owner
# called them "short like for midgets" and the census agrees.  Blood has
# no door TEXTURE to lean on (E3M1's own door leaves wear 379 and 449,
# plain wall stone), so an opening reads as a door through its proportion
# and its reveal -- which makes this number the whole fix.
DOOR_HEIGHT = 31744

# The hall occupies most of block A: a broad sales floor, shallow rear stock
# and display galleries on the east and north sides.
SUPERMARKET_WINDOWS = (
    (13824, 41472, 15360, 45056),
    (13824, 48128, 15360, 49152),
    (3584, 40960, 10752, 41472),
)

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

    # ---- the monument: the first thing the player reads -------------------
    # Declared at L1 as a free-standing mass since the plan was written, and
    # never built: the plaza carved its hole and the hole stayed a hole, in
    # the most visible spot in the city.
    import citytree
    import templates as _t
    import city_plan as _plan
    import build_skeleton as _bs
    _rect = next(b["rect"] for b in _plan.BLOCKS if b["id"] == "monument")
    # The very outline the street carved, chamfers and all.
    _outline = _bs.mass_outline(_rect, [])
    monument_node, monument_parts = _t.monument(
        plaza, market_st, _outline,
        # `opening` equal to `wall`, not the jamb tile.  A monument's step is
        # not a doorway: with MASONRY's own opening (28, the boardwalk plank)
        # the plinth's face came out as brown boards under the city's name.
        material=Material(wall=MASONRY.wall, floor=MASONRY.floor,
                          ceiling=MASONRY.ceiling, opening=MASONRY.wall,
                          sky=True, note="the monument's stone"),
        cap_material=Material(wall=MASONRY.wall, floor=MASONRY.floor,
                              ceiling=facade.ceiling, opening=MASONRY.opening,
                              sky=True, note="the pedestal's cap"),
        grade=GRADE, clear_height=STREET_SKY, connector=district)
    citytree.declare_venue(monument_node, "monument", "free_standing",
                           built_by="l3_market")
    built["rooms"] += [r.region_id for r in monument_parts.values()]
    built["street_joined"].append(monument_parts["base"].region_id)
    built["monument"] = {name: room.region_id
                         for name, room in monument_parts.items()}
    #: The rooms themselves, so the dressing pass can ask them for their
    #: faces rather than reconstructing rectangles from region ids.
    built["monument_rooms"] = dict(monument_parts)

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

    # ---- the market hall: a full supermarket inside block A --------------
    # Use most of the block for one readable sales floor, reserve the south
    # strip for staff-only stock, and put shallow display galleries along the
    # north/east sides.
    shop, common = INTERIORS["shop"], INTERIORS["common"]
    import citytree
    hall = district.assembly(
        "market_hall",
        style=Style(**common.style_kwargs(floor_z=GRADE,
                                          clear_height=ROOM_HEIGHT,
                                          floor_shade=32)),
        note="market hall: a large supermarket with windows, aisles and stock")
    citytree.declare_venue(hall, "market_hall", "retail_row",
                           built_by="l3_market")

    def room(name, x0, y0, x1, y1, material, note, **kw):
        clear_height = int(kw.pop("clear_height", ROOM_HEIGHT))
        r = hall.room(
            name, [(0, 0), (int((x1 - x0) * PU), 0),
                   (int((x1 - x0) * PU), int((y1 - y0) * PU)),
                   (0, int((y1 - y0) * PU))],
            role=kw.pop("role", "interior"), faces=dict(COMPASS),
            frame=Frame(int(x0 * PU), int(y0 * PU)),
            region_kwargs={**material.region_kwargs(), **kw.pop("rk", {})},
            note=note)
        r.surfaces(**material.style_kwargs(floor_z=GRADE,
                                           clear_height=clear_height))
        return r

    sales = room("supermarket", 3.5, 40.5, 13.5, 48.0, shop,
                 "the market hall sales floor: tall E6M1 shelf banks and crate bays",
                 clear_height=MARKET_HALL_HEIGHT)
    stock = room("stockroom", 3.5, 48.0, 13.5, 49.5, shop,
                 "staff-only rear stock: separate 452/95 crate bays")
    stock.surfaces(wall_picnum=63)
    # Display galleries are separate shallow sectors, so mannequins and window
    # lighting never occupy a sales aisle.  The east strip is split by the
    # entrance; the north strip makes the building read from the side.
    display_n = room("display_n", 13.5, 40.5, 15.0, 44.0, shop,
                     "east supermarket window: raised display behind glass",
                     role="detail")
    display_s = room("display_s", 13.5, 47.0, 15.0, 48.0, shop,
                     "east supermarket window: lower display behind glass",
                     role="detail")
    display_side = room("display_side", 3.5, 40.0, 10.5, 40.5, shop,
                        "north side display gallery behind glass", role="detail")
    for box in (display_n, display_s, display_side):
        box.surfaces(floor_z=GRADE - 2048, clear_height=ROOM_HEIGHT - 2048)
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
    porch = room("porch", 14.5, 44.5, 15.0, 46.5, common,
                 "the hall's porch: the reveal that owns the wall above",
                 role="gateway")
    porch.surfaces(wall_picnum=facade.opening, ceiling_picnum=facade.opening,
                   clear_height=DOOR_HEIGHT)
    door = room("door", 13.5, 44.5, 14.5, 46.5, common,
                "the hall's door onto the plaza", role="doorway",
                rk={"type": 600, "door_face": 22, "inherit_finish": "both",
                    "sector_behavior": z_motion_door(GRADE, GRADE - 16384)})
    # A doorway's jambs belong to the room that LOOKS at them.  Left on the
    # interior material, the hall's jamb put papered wall (108) on a surface
    # the plaza sees floor-to-sky; it takes the facade's opening tile.
    door.surfaces(wall_picnum=facade.opening, clear_height=0)
    # Anchor partial joins from the smaller room: a connection takes its
    # geometry from the left anchor, preventing a long sales-floor wall from
    # leaving the warehouse opening or windows as coincident fake walls.
    hall.connect(stock.face("north"), sales.face("south"),
                 connection_id="connection:supermarket_stock")
    for tag, box in (("north", display_n), ("south", display_s)):
        hall.connect(box.face("west"), sales.face("east"),
                     connection_id=f"connection:supermarket_window_{tag}_in")
        city.connect(box.face("east"), market_st.face("north"),
                     connection_id=f"connection:supermarket_window_{tag}_street")
    hall.connect(display_side.face("south"), sales.face("north"),
                 connection_id="connection:supermarket_window_side_in")
    city.connect(display_side.face("north"), market_st.face("north"),
                 connection_id="connection:supermarket_window_side_street")
    hall.connect(door.face("west"), sales.face("east", at=0.5,
                                                   width=UNIT_MOUTH),
                 connection_id="connection:hall_door_in")
    hall.connect(porch.face("west"), door.face("east"),
                 connection_id="connection:hall_porch_door")
    city.connect(porch.face("east"), market_st.face("north"),
                 connection_id="connection:hall_porch_plaza")
    # Geometry is intentionally separate from dressing: the template gives
    # the supermarket a usable aisle topology, then the late pass adds its
    # wall clock and electrical detail without creating floor-sprite clashes.
    import templates
    templates.supermarket(sales, material=shop, grade=GRADE,
                          host_clear=MARKET_HALL_HEIGHT)
    templates.stockroom(stock, material=shop, grade=GRADE,
                         host_clear=ROOM_HEIGHT)
    # Rear staff entrance: it reaches the stock strip directly and never turns
    # the public checkout aisle into a through-route.
    staff_door = room("staff_door", 6.0, 49.5, 8.0, 50.0, common,
                      "staff-only rear entrance", role="doorway",
                      rk={"door_face": 22})
    staff_door.surfaces(wall_picnum=facade.opening, clear_height=0)
    hall.connect(staff_door.face("north"), stock.face("south"),
                 connection_id="connection:supermarket_staff_inner")
    city.connect(staff_door.face("south"), market_st.face("north"),
                 connection_id="connection:supermarket_staff_outer")
    built["hall"] = {"supermarket": sales.region_id, "stockroom": stock.region_id,
                      "staff_door": staff_door.region_id}
    built["supermarket_rooms"] = {"sales": sales, "stock": stock,
                                  "display_n": display_n, "display_s": display_s,
                                  "display_side": display_side,
                                  "staff_door": staff_door}
    built["rooms"] += [sales.region_id, stock.region_id]
    built["interiors"] += [sales.region_id, stock.region_id,
                           display_n.region_id, display_s.region_id,
                           display_side.region_id, staff_door.region_id]
    return built


def dress_supermarket(layout, rooms) -> dict:
    """Late, non-blocking retail detail for the supermarket sales room.

    The shelves and counters are sectors, so they must exist before this
    pass.  These are deliberately wall details: an outlet and clock read as
    utility and retail timekeeping without occupying an aisle or intersecting
    a shelf bank.
    """
    import props

    sales, stock = rooms["sales"], rooms["stock"]
    sales_rect = props.room_rect(sales)
    north_a, north_b = props.face_segment(sales_rect, "north", inset=512)
    stock_a, stock_b = props.face_segment(props.room_rect(stock), "west", inset=256)
    layout.place_on_wall(
        "market:super_clock", sales.region_id, a1=north_a, a2=north_b,
        t=0.78, height_player_heights=1.35, offset_player_widths=0.06,
        type=0, picnum=1165, cstat=144, shade=-8,
        x_repeat=48, y_repeat=48, status=0)
    layout.place_on_wall(
        "market:super_outlet", stock.region_id, a1=stock_a, a2=stock_b,
        t=0.25, height_player_heights=0.45, offset_player_widths=0.06,
        type=0, picnum=1050, cstat=144, shade=-4,
        x_repeat=32, y_repeat=32, status=0)
    return {"wall_details": 2, "tiles": [1165, 1050]}


#: The monument's own words, and the register they are written in.
#:
#: Uniform palette, not per-letter.  Only **9 of the corpus's 160 signs**
#: mix palettes at all -- 5.6% -- and every one of them is in an attraction
#: map: E1M4's carnival, DWE1M9's SPOOKY WORLD, DWE3M4 and DWE3M10's ICE.
#: A city's welcome monument is not a fairground, and `fascia` is the style
#: whose own attested word IS `WELCOME` (10 words at size 120, palette 4,
#: shade 0).  The style steps down its own ladder to whatever the plinth's
#: 1,792-unit face will take.
#: Heights are measured from the BASE's floor, and the step above it is
#: 12,288 units -- 0.72 player heights -- of solid masonry.  Both lines sit
#: inside it: at 64 a letter is 2,816 tall, so 0.50 spans 0.42..0.58 and
#: 0.24 spans 0.16..0.32.
MONUMENT_WORDS = (
    ("WELCOME TO", 0.50),
    ("GRAVESEND", 0.24),
)


def _local_of(room, x, y):
    """A world point as a local fraction of a room's bounding box."""
    import props
    x0, y0, x1, y1 = props.room_rect(room)
    return ((x - x0) / max(1, x1 - x0), (y - y0) / max(1, y1 - y0))


def dress_monument(layout, parts, street=None) -> dict:
    """Carve the city's name on the plinth, and light the pedestal.

    The lettering goes on the plinth's SOUTH face because that is the face
    the player is looking at: the spawn is on the quay at (33.5, 53) and the
    monument's centre is (26, 45), eleven plan units north-west of it.

    The apex carries a flame, not a figure.  `monuments-v1.json` finds 421
    tiered outdoor masses and only 77 carry anything at all; what they carry
    is light -- 23 of the statuary sprites are one invisible generator, the
    rest torches and lamps.  Blood has no figure-on-a-plinth idiom, so this
    does not invent one.
    """
    import props
    import wallplane

    report = {"lines": 0, "letters": 0, "lights": 0, "skipped": []}
    plinth = parts.get("plinth")
    pedestal = parts.get("pedestal")
    base = parts.get("base")
    if plinth is None:
        return report

    # The letters belong to the BASE, not the plinth.  The wall between them
    # is a step: from the plinth's side everything above its own floor is
    # open, and the compiler is right to refuse a sprite hung there.  From
    # the base's side the same wall is 12,288 units of solid masonry, which
    # is the surface a monument carries its name on.  The segment is wound
    # backwards for the same reason -- the sprite has to face out of the
    # plinth, not into it.
    rect = props.room_rect(plinth)
    a2, a1 = props.face_segment(rect, "south", inset=64)
    for index, (words, height) in enumerate(MONUMENT_WORDS):
        ids = wallplane.text(
            layout, f"monument:{index}", base.region_id, a1, a2,
            words=words, style="fascia", height_player_heights=height,
            offset_player_widths=0.06, over_steps=True)
        if not ids:
            report["skipped"].append(words)
            continue
        report["lines"] += 1
        report["letters"] += len(ids)

    # The flame on the pedestal: the campaign's own monument statuary, and
    # the plaza's own light.
    if pedestal is not None:
        layout.place_on_floor(
            "monument:flame", pedestal.region_id, local=(0.5, 0.5),
            height_player_heights=props.height_of(2101),
            emits_light=True, light_intensity=3.0,
            light_height_player_heights=0.6,
            **props.fields(2101))
        report["lights"] += 1
    # A lamp at each end of the base's front, the pair E3M1 stands in its
    # streets and `monuments-v1` finds on monuments twice.
    if base is not None:
        # The base is a chamfered octagon with the plinth carved out of its
        # middle, so a hand-chosen local lands on a corner cut or in the
        # hole.  Ask the room where its floor actually is.
        # In the PLAZA, not on the base.  The base ring is only 320 units
        # wide either side of the plinth, so a lamp standing on it stands
        # directly in front of the lettering -- the first render had the G
        # and the D of GRAVESEND behind lamp posts.
        x0, y0, x1, y1 = props.room_rect(base)
        for index, (px, py) in enumerate(((x0 - 1024, y1 + 1024),
                                          (x1 + 1024, y1 + 1024))):
            try:
                layout.place_on_floor(
                    f"monument:lamp_{index}", street.region_id,
                    local=_local_of(street, px, py),
                    height_player_heights=props.height_of(props.STREET_LAMP),
                    **props.fields(props.STREET_LAMP))
                report["lights"] += 1
            except Exception:
                report["skipped"].append(f"lamp_{index}")
    return report
