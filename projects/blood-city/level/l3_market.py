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
from bloodmap.slope import SlopeSpec

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
#: The side of each the street is on.
SUPERMARKET_WINDOW_FACES = ("east", "east", "north")

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
#: THE SEA, from the harbour study (`knowledge/blood/studies/harbour`).
#: Two blind reviews read the water as grass, and the study says why: it
#: was 1120, the owner's "green dirty water", still, bright, and 0.12 of a
#: body under the boards -- a lawn. Every Blood sea (DWE3M4 s636/528/527,
#: E2M1 s125, E2M9 s49) is tile 2490 or 2448 in PALETTE 10, shade 38 to 44
#: darkening outward, its floor panning, depth 0, and it lies 1.75 bodies
#: below its quay (DWE3M4: boardwalk -8,192 over sea 21,504).
#: (2490 is the owner's "light marble": water is a use he has not named.)
SEA_TILE, SEA_PAL = 2490, 10
SEA_DROP = 29696
SEA_PAN = {"pan_floor": 1, "pan_always": 1, "pan_velocity": 10,
           "pan_angle": 900, "depth": 0}
BULKHEAD = 20                  # the quay's face to the water: dark planks

#: The sea, band by band going out: (depth in plan units, floor shade).
#: DWE3M4 darkens its sea 3 a band (35, 38, 41, 44); ours starts where the
#: old river was lit.
SEA_BANDS = ((8, 38), (6, 41), (6, 44))
HORIZON_DEPTH = 1024
#: region ids of the horizon's pieces, for the build to check
HORIZON: list = []
#: The ship. Rim over the quay: DWE3M4's "Phantom" stands 11,264 over its
#: pier; deck under the rim: 4,096 (s671 under s625).
SHIP_RIM = 11264
SHIP_DECK_DROP = 4096
SHIP_CABIN = 16384
SHIP_MAST = 73728
#: Owner anchors: 67 "dark horizontal planks" is the hull DWE2M4's rowboat
#: shows the water; 15 planks cap the rim; 28 is the wooden wall; 20 is the
#: tile DWE2M6's three masts wear.
SHIP_HULL, SHIP_PLANK, SHIP_CABIN_WALL, SHIP_MAST_TILE = 67, 15, 28, 20
#: region id -> the tile its raised sides wear (`skyline.dress_steps`)
SHIP_FACES: dict = {}
#: the owner's "smaller crate"; and E2M1 sprites 156/157, the black flag
CRATE = 452
FLAG = {"type": 0, "picnum": 3558, "cstat": 144, "x_repeat": 64,
        "y_repeat": 64, "shade": 8, "status": 0}
SHIP_FLAG: list = []


def fly_flag(layout) -> int:
    """Hang the flag on the mast's west face, 2.3 bodies over the deck."""
    for spec in SHIP_FLAG:
        layout.place_on_wall(
            "ship:flag", spec["region_id"], a1=spec["a1"], a2=spec["a2"],
            t=0.5, height_player_heights=2.3, offset_player_widths=0.02,
            **FLAG)
    return len(SHIP_FLAG)

#: What stands between the sea and the town. The owner, 2026-11-18: "Edges
#: of that sea looks bad because they connect straight to buildings, it
#: should have something to visually divide it, places where player can't
#: reach, but will see." The water ran from a building's back corner
#: straight to the horizon ring.
#:
#: Measured: DWE2M6 rings its bay in rock (s931-940: floor 273, faces 458,
#: 2.3 to 3.6 bodies over the water); DWE3M5's ring STOPS at the tips of
#: rock headlands with jagged edges of several segments; DWE2M6 stands
#: wooden piles in the water (s621-626: 512 square, 2.05 bodies, tile 20,
#: 2,560 apart); DWE3M4 blocks every wall into its outermost band, so the
#: far sea is seen and never reached.
#:
#: Plan units, in the near band's own frame: a headland at each end,
#: between the quay's corner and the ring, and its crest.
HEAD_WEST = ((0, 0), (3.5, 0), (3, 2), (1.5, 3.5), (1, 5.5), (0, 6.5))
HEAD_EAST = ((44.25, 0), (48, 0), (48, 6), (47, 5), (46.5, 3), (45, 1.75))
CREST_WEST = ((0.5, 0.5), (2.5, 0.5), (2, 1.75), (0.75, 3), (0.5, 4))
CREST_EAST = ((45.5, 0.5), (47.5, 0.5), (47.5, 3.5), (46.75, 2.5), (46, 1.25))
#: the flank of the building at each end of the quay: the owner's "brick
#: facade with shuttered window", darker than the street's own fronts
#: (until `flank_follow` has looked at the building each one belongs to)
FLANK_TILE, FLANK_SHADE = 385, 12
FLANKS: list = []
FLANK_END = 2048               # how thick the flank building is at its end
#: over the SEA, which now lies 1.75 bodies under the quay: the tops stand
#: where they stood, 2.5 and 4 bodies over the street (DWE3M5: 2.7 to 6)
HEAD_RISE = 44096 + 27648
CREST_RISE = 71232 + 27648
ROCK_FLOOR, ROCK_FACE = 273, 458   # the owner's "rock/cliff" and "rock"
PILE, PILE_RISE, PILE_PITCH = 512, 34768, 2560
#: the jetty: (x0, x1, length) in plan units, in the near band's frame --
#: beside the ship's bow, five and a half out. TWO units wide: at one,
#: with a 256 post 64 in from each edge, 384 was left between the posts and
#: a body is wider than that (the owner, in the game: "Pier is very narrow,
#: you can't walk on it"). Now 1,408 clear.
JETTY = (21, 23, 5.5)
POST_RISE = 16960              # a body over the deck
PILE_TILE = 20
#: a skerry in the second band: out of reach, in view from the whole quay
SKERRY = ((36, 9.5), (38.5, 9), (39.5, 10.5), (38.5, 12), (36.5, 12.5),
          (35.5, 11))
SKERRY_RISE = 25440            # a body and a half
#: region ids: the band the player can wade, and the ones he cannot
SEA: dict = {}
#: region ids of everything made of rock, for the scale pass
ROCKS: list = []


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


def close_outer_sea(level, compiled) -> dict:
    """Block every wall from the near water into the bands beyond it.

    DWE3M4 does exactly this (every wall between s527 and s856 carries the
    blocking bit): the far sea, its skerry and the ring are seen and never
    reached, so nobody wades to the horizon and finds its edge.
    """
    def f(item):
        return item.get("fields", item) if isinstance(item, dict) else item.fields

    near = compiled.allocations[SEA["near"]].sector_id
    far = {compiled.allocations[r].sector_id for r in SEA["far"]}
    #: palette 10 is what makes 2490 water; and nobody steps off the quay
    #: into a sea 1.75 bodies down that he could not climb out of: every
    #: wall between the water and anything at the quay's level blocks.
    walk = {compiled.allocations[r].sector_id for r in SEA.get("walk", ())
            if r in compiled.allocations}
    edge = 0
    for index in [near, *far]:
        s = f(level.sectors[index])
        s["floor_pal"] = SEA_PAL
        s["floor_stat"] = int(s["floor_stat"]) | 4
    for index, sector in enumerate(level.sectors):
        s = f(sector)
        for w in range(int(s["wall_ptr"]),
                       int(s["wall_ptr"]) + int(s["wall_count"])):
            wall = f(level.walls[w])
            other = int(wall["next_sector"])
            if (index == near and other in walk) or (index in walk
                                                     and other == near):
                wall["cstat"] = int(wall["cstat"]) | 1
                edge += 1
    shut = 0
    for index, sector in enumerate(level.sectors):
        s = f(sector)
        for w in range(int(s["wall_ptr"]),
                       int(s["wall_ptr"]) + int(s["wall_count"])):
            wall = f(level.walls[w])
            other = int(wall["next_sector"])
            if (index == near and other in far) or (index in far
                                                    and other == near):
                wall["cstat"] = int(wall["cstat"]) | 1
                shut += 1
    # Rock at the scale it is drawn everywhere else. The same reviewer:
    # "a free-standing block of cracked grey rock ... its texture is badly
    # stretched". The faces took whatever repeat their wall had as water's
    # edge; a rock face is 16 units a texel both ways, begun at its own end.
    rocks = {compiled.allocations[r].sector_id for r in ROCKS
             if r in compiled.allocations}
    scaled = 0
    for wall in level.walls:
        w = f(wall)
        if int(w["next_sector"]) in rocks and int(w["picnum"]) == ROCK_FACE:
            n = f(level.walls[int(w["point2"])])
            length = (abs(int(n["x"]) - int(w["x"]))
                      + abs(int(n["y"]) - int(w["y"])))
            w["x_repeat"] = max(1, min(255, round(length / 128)))
            w["y_repeat"], w["x_panning"], w["y_panning"] = 8, 0, 0
            scaled += 1
    return {"walls": shut, "rock_faces": scaled, "quay_edge": edge}


def _flank_specs(side):
    import detailing
    return [spec for spec in detailing.PANELS
            if spec["note"].startswith(f"harbour flank {side}")]


def flank_follow(level, compiled, street_region_id, quay_y, x_ends) -> dict:
    """Each flank wears its own building's wall, without the windows.

    The owner, in the game, 2026-11-19: "These building walls which reach
    sea shouldn't probably have windows if there is that big rock. Also
    they should have texture that follows up -- for example 380 is building
    facade with windows and 381 is the same thing just without windows."
    Both flanks were 384 whatever stood on the quay beside them. Now the
    front that ends at each corner is read, and the flank takes its blank
    companion (`facade_pass.BLANK_OF`); a front with no companion (the
    tall 400 and 401) is made the district's 380, which has one.

    Before `detailing.paint`, which then paints what this decided.
    """
    import facade_pass

    def f(item):
        return item.get("fields", item) if isinstance(item, dict) else item.fields

    street = f(level.sectors[compiled.allocations[street_region_id].sector_id])
    out = {}
    for side, x in zip(("west", "east"), x_ends):
        front = None
        for w in range(int(street["wall_ptr"]),
                       int(street["wall_ptr"]) + int(street["wall_count"])):
            wall = f(level.walls[w])
            nxt = f(level.walls[int(wall["point2"])])
            if (int(wall["next_sector"]) >= 0 or int(wall["y"]) != quay_y
                    or int(nxt["y"]) != quay_y):
                continue
            xs = (int(wall["x"]), int(nxt["x"]))
            beyond = min(xs) < x if side == "west" else max(xs) > x
            if x in xs and beyond:
                front = wall
        if front is None:
            out[side] = None
            continue
        if int(front["picnum"]) not in facade_pass.BLANK_OF:
            front["picnum"] = 380
        blank = facade_pass.BLANK_OF[int(front["picnum"])]
        for spec in _flank_specs(side):
            spec["tile"] = blank
        out[side] = [int(front["picnum"]), blank]
    return out


def flank_align(level, grade, art_sizes) -> int:
    """After the frames: the flank's courses are the front's courses.

    The front stands on the quay (`frame_map`, v_anchor floor); a flank's
    own floor is a rock or the sea, 1.75 bodies and more below. So the
    flank is hung from the sky they share, panned to put the tile's bottom
    row at the QUAY's level -- the cornice and the brick base come round
    the corner at the height they left it.
    """
    from bloodmap.texture_frame import c_div, sector_index

    def f(item):
        return item.get("fields", item) if isinstance(item, dict) else item.fields

    owners = sector_index(level)
    done = 0
    for side in ("west", "east"):
        for spec in _flank_specs(side):
            size = art_sizes.get(int(spec["tile"]))
            if not size:
                continue
            for index in spec.get("records", ()):
                wall = f(level.walls[index])
                ceiling = int(f(level.sectors[owners[index]])["ceiling_z"])
                origin = grade - int(size[1]) * 2048 // 8
                wall["cstat"] = int(wall["cstat"]) & ~4
                wall["y_repeat"] = 8
                wall["y_panning"] = c_div((ceiling - origin) * 8,
                                          int(size[1]) << 3) % 256
                done += 1
    return done


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

    # ---- the sea: it ends in sky, not in a wall --------------------------
    # The owner, walking the build of 2026-11-18: "Ship in a harbour is just
    # a wooden rectangle, water should end with sky (check DWE3M4 for
    # promenades, sea, etc.)". This was one water sector 16 units deep
    # walled in brick 11.7 bodies high on three sides: a tank.
    #
    # DWE3M4, measured: the sea runs flat to a HORIZON RING, sector 648 --
    # zero height at the water's own z, the sky on floor AND ceiling with
    # the parallax bit on both. The wall between two parallax ceilings is
    # never drawn, so the sky comes down to the waterline. The sea is cut
    # into bands only to step its shade outward: 35, 38, 41, 44.
    river_y0 = int(city_d_pu * PU)
    river_x0, river_x1 = int(4 * PU), int(52 * PU)
    sea_z = GRADE + SEA_DROP
    sky = facade.ceiling

    # The near band's ends are the headlands' shores: north, the east
    # head's four edges, east, south, west, the west head's four.
    jx0, jx1, jlen = JETTY
    near_outline = ([HEAD_WEST[1], (jx0, 0), (jx0, jlen), (jx1, jlen),
                     (jx1, 0), HEAD_EAST[0]]
                    + list(reversed(HEAD_EAST[2:]))
                    + [(48, SEA_BANDS[0][0]), (0, SEA_BANDS[0][0])]
                    + list(reversed(HEAD_WEST[2:])))
    near_outline = [(int(x * PU), int(y * PU)) for x, y in near_outline]
    #: north, the jetty's three sides, north again, then as before
    near_faces = {"north": 0, "jw": 1, "js": 2, "je": 3, "north_b": 4,
                  "east": 9, "south": 10, "west": 11}
    near_faces.update({f"he{k}": 5 + k for k in range(4)})
    near_faces.update({f"hw{k}": 12 + k for k in range(4)})

    #: The bands beyond the near one are WIDER than it by `FLANK_END` at
    #: each side. A blind reviewer on the build that first had flanks:
    #: "the brick wall ends flat against the sky, a cut-off edge with no
    #: visible side or thickness". The step in the sea's outline is that
    #: side: the flank building's END FACE, turning its far corner.
    far_x0, far_x1 = river_x0 - FLANK_END, river_x1 + FLANK_END

    def water_band(name, y0, depth, shade, note, outline=None):
        wide = outline is None
        x0, x1 = (far_x0, far_x1) if wide else (river_x0, river_x1)
        band = quay.room(
            name, outline or [(0, 0), (x1 - x0, 0), (x1 - x0, depth),
                              (0, depth)],
            role="exterior",
            faces=dict(near_faces) if outline else dict(COMPASS),
            frame=Frame(x0, y0),
            region_kwargs={"sector_behavior": dict(SEA_PAN)},
            note=note)
        band.style = Style(floor_picnum=SEA_TILE, wall_picnum=BULKHEAD,
                           ceiling_picnum=sky, parallax_ceiling=True,
                           layer="sea",
                           floor_z=sea_z, clear_height=STREET_SKY + SEA_DROP,
                           floor_shade=shade)
        built["rooms"].append(band.region_id)
        built["street_joined"].append(band.region_id)
        return band

    def horizon(name, x0, y0, x1, y1):
        piece = quay.room(
            name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
            role="exterior", faces=dict(COMPASS), frame=Frame(x0, y0),
            region_kwargs={"declared_zero_exit": True},
            intent={"kind": "horizon"},
            note="the horizon: no height, sky above and below (DWE3M4 s648)")
        piece.style = Style(floor_picnum=sky, wall_picnum=MASONRY.wall,
                            ceiling_picnum=sky, parallax_ceiling=True,
                            layer="sea",
                            floor_stat=1, floor_z=sea_z, clear_height=0)
        HORIZON.append(piece.region_id)
        return piece

    bands, rings = [], []
    y = river_y0
    for index, (depth, shade) in enumerate(SEA_BANDS):
        band = water_band(
            "river" if index == 0 else f"sea_{index}", y, depth * PU, shade,
            "the water at the quay" if index == 0
            else "the sea, a band further out and a step darker",
            outline=near_outline if index == 0 else None)
        if bands:
            city.connect(bands[-1].face("south"), band.face("north"),
                         connection_id=f"connection:sea_{index}")
        if index == 0:
            # The owner, 2026-11-18: "the sea connection to city looks
            # poor, there is a wall that directly ends into sky". The quay
            # street runs a little past the water at each end, and the
            # facade on its seaward side stopped dead where the ring began:
            # a building with a front and no flank, its end against the sky.
            # So the near band has NO ring at its ends. Its end walls, and
            # the headlands', are solid: the flank of that same building,
            # standing in the water behind the rock (`FLANKS`, painted by
            # `detailing`). The ring begins one band further out, at the
            # building's far corner.
            for x in (river_x0, river_x1):
                FLANKS.append(((x, y), (x, y + depth * PU)))
            rings.append(None)
            bands.append(band)
            y += depth * PU
            continue
        west = horizon(f"horizon_w{index}", far_x0 - HORIZON_DEPTH, y,
                       far_x0, y + depth * PU)
        east = horizon(f"horizon_e{index}", far_x1, y,
                       far_x1 + HORIZON_DEPTH, y + depth * PU)
        if index == 1:
            import detailing as _detailing
            for a, b in (((far_x0, y), (river_x0, y)),
                         ((river_x1, y), (far_x1, y))):
                side = "west" if a[0] < river_x0 else "east"
                _detailing.panel(band.region_id, a, b, FLANK_TILE,
                                 peg="ceiling", shade=FLANK_SHADE + 4,
                                 note=f"harbour flank {side} end face")
        city.connect(band.face("west"), west.face("east"),
                     connection_id=f"connection:horizon_w{index}")
        city.connect(band.face("east"), east.face("west"),
                     connection_id=f"connection:horizon_e{index}")
        #: every coincident edge is a declared portal
        for side, piece in (("w", west), ("e", east)):
            if rings[-1]:
                city.connect(rings[-1][side].face("south"), piece.face("north"),
                             connection_id=f"connection:horizon_{side}{index}_up")
        rings.append({"w": west, "e": east})
        bands.append(band)
        y += depth * PU
    south = horizon("horizon_s", far_x0, y, far_x1, y + HORIZON_DEPTH)
    city.connect(bands[-1].face("south"), south.face("north"),
                 connection_id="connection:horizon_s")
    river = bands[0]
    SEA["near"] = river.region_id
    SEA["walk"] = [market_st.region_id]
    SEA["far"] = [band.region_id for band in bands[1:]]

    def rock(name, outline, rise, shade, note, tile=ROCK_FLOOR,
             face=ROCK_FACE, origin_y=river_y0, fall=0):
        """`fall` tips the top: z gained going away from its first edge.

        The study: Blood's rock is facets, "each with its own slope and
        its own shade" (DWE3M5 s46-60: heinum 512 to 1,280, shade 25 to
        37); ours was "two stacked rectangles with flat tops".
        """
        points = [(int(x * PU), int(y * PU)) for x, y in outline]
        x0 = min(x for x, _y in points)
        y0 = min(y for _x, y in points)
        room = quay.room(
            name, [(x - x0, y - y0) for x, y in points], role="detail",
            faces={f"e{i}": i for i in range(len(points))},
            frame=Frame(river_x0 + x0, origin_y + y0),
            region_kwargs={"declared_zero_exit": True, **(
                {"floor_slope": SlopeSpec(
                    hinge=((river_x0 + points[0][0], origin_y + points[0][1]),
                           (river_x0 + points[1][0], origin_y + points[1][1])),
                    rise_z=fall)} if fall else {})},
            intent={"kind": "sea_rock"}, note=note)
        room.style = Style(floor_picnum=tile, wall_picnum=face,
                           ceiling_picnum=sky, parallax_ceiling=True,
                           floor_z=sea_z - rise,
                           clear_height=STREET_SKY + SEA_DROP - rise,
                           floor_shade=shade)
        SHIP_FACES[room.region_id] = face
        if face == ROCK_FACE:
            ROCKS.append(room.region_id)
        return room, points, (x0, y0)

    import detailing
    for side, outline, crest in (("west", HEAD_WEST, CREST_WEST),
                                 ("east", HEAD_EAST, CREST_EAST)):
        head, points, origin = rock(
            f"headland_{side}", outline, HEAD_RISE,
            31 if side == "west" else 35,
            "a rock headland: the sea ends against it, not against a house",
            fall=20480)                 # highest at the land, down to sea
        top, crest_points, _o = rock(
            f"headland_{side}_crest", crest, CREST_RISE,
            25 if side == "west" else 28, "the headland's crest",
            fall=-9216 if side == "west" else 12288)
        head.carve([(x - origin[0], y - origin[1]) for x, y in crest_points])
        for name in list(top.faces):
            city.connect(top.face(name), head.face("e0"),
                         connection_id=f"connection:crest_{side}_{name}")
        city.connect(head.face("e0"), market_st.face("south"),
                     connection_id=f"connection:headland_{side}_quay")
        #: west: edges 1-4 are the shore and 5 the ring; east: 1 is the
        #: ring and 2-5 the shore
        shore = range(1, 5) if side == "west" else range(2, 6)
        for k in shore:
            city.connect(head.face(f"e{k}"), river.face("north"),
                         connection_id=f"connection:headland_{side}_shore{k}")
        x = river_x0 if side == "west" else river_x1
        for region in (head, river):
            #: hung from the sky both regions share, so the window rows
            #: run straight across the rock and the water
            detailing.panel(region.region_id, (x, river_y0),
                            (x, river_y0 + SEA_BANDS[0][0] * PU), FLANK_TILE,
                            peg="ceiling", shade=FLANK_SHADE,
                            note=f"harbour flank {side}")
    built["headlands"] = 2

    # The jetty, and the posts that are ITS posts. A blind reviewer on
    # the first build with piles in the water: "the posts are scattered at
    # random and fence nothing". A pile has a job when it holds something
    # up: so a plank jetty runs out from the quay beside the ship's bow,
    # and the piles stand along its two edges, a body over the deck
    # (DWE2M6 s621-626: 512 square, 2.05 bodies over the water).
    city.connect(river.face("north_b"), market_st.face("south"),
                 connection_id="connection:quay_river_b")
    jw = int((jx1 - jx0) * PU)
    jetty = quay.room(
        "jetty", [(0, 0), (jw, 0), (jw, int(jlen * PU)), (0, int(jlen * PU))],
        role="exterior", faces=dict(COMPASS),
        frame=Frame(river_x0 + int(jx0 * PU), river_y0),
        intent={"kind": "jetty"}, note="the jetty: planks out over the water")
    jetty.style = Style(floor_picnum=BOARDWALK, wall_picnum=PILE_TILE,
                        ceiling_picnum=sky, parallax_ceiling=True,
                        floor_z=GRADE, clear_height=STREET_SKY,
                        floor_shade=26)
    SHIP_FACES[jetty.region_id] = PILE_TILE
    SEA["walk"].append(jetty.region_id)
    built["rooms"].append(jetty.region_id)
    built["street_joined"].append(jetty.region_id)
    city.connect(jetty.face("north"), market_st.face("south"),
                 connection_id="connection:jetty_quay")
    for face in ("east", "south", "west"):
        city.connect(jetty.face(face), river.face("north"),
                     connection_id=f"connection:jetty_{face}")
    piles = 0
    post, inset = 256, 64
    for side, px in enumerate((inset, jw - inset - post)):
        for k in range(4):
            py = 512 + k * 1408
            box_ = [(px, py), (px + post, py), (px + post, py + post),
                    (px, py + post)]
            jetty.carve(box_)
            pile = quay.room(
                f"pile_{side}_{k}", [(0, 0), (post, 0), (post, post),
                                     (0, post)],
                role="detail", faces=dict(COMPASS),
                frame=Frame(river_x0 + int(jx0 * PU) + px, river_y0 + py),
                region_kwargs={"declared_zero_exit": True},
                intent={"kind": "sea_rock"}, note="a jetty post")
            pile.style = Style(floor_picnum=PILE_TILE, wall_picnum=PILE_TILE,
                               ceiling_picnum=sky, parallax_ceiling=True,
                               floor_z=GRADE - POST_RISE,
                               clear_height=STREET_SKY - POST_RISE,
                               floor_shade=28)
            SHIP_FACES[pile.region_id] = PILE_TILE
            for name in list(pile.faces):
                city.connect(pile.face(name), jetty.face("north"),
                             connection_id=f"connection:pile_{side}_{k}_{name}")
            piles += 1
    built["piles"] = piles

    # The skerry: a rock in the band nobody can wade to.
    far = bands[1]
    far_y0 = river_y0 + SEA_BANDS[0][0] * PU
    far.carve([(int(x * PU) + FLANK_END, int(y * PU) - SEA_BANDS[0][0] * PU)
               for x, y in SKERRY])
    skerry, _p, _o = rock("skerry", SKERRY, SKERRY_RISE + 27648, 33,
                          "a skerry: in view from the quay, out of reach",
                          fall=14336)
    for name in list(skerry.faces):
        city.connect(skerry.face(name), far.face("north"),
                     connection_id=f"connection:skerry_{name}")
    city.connect(river.face("north"), market_st.face("south"),
                 connection_id="connection:quay_river")

    # ---- the ship: a hull, not a deck ------------------------------------
    # It was a 4 x 2 rectangle of boards a step over the water. Every hull
    # in the corpus that reads as a boat (DWE3M4's "Phantom", DWE2M6's ghost
    # ship, DWE2M4's rowboat) has the same three things: a pointed or
    # tapered end, a thin RIM that is the highest thing with the deck lower
    # inside it, and a hull tile that is not the deck's. This is the
    # Phantom's plan at three quarters: 9,984 by 3,072, bow to the east, the
    # rim 0.66 body over the quay as the Phantom's is over its pier, the
    # deck 4,096 under the rim.
    ship_x0 = river_x0 + 10 * PU
    ship_y0 = river_y0 + 1 * PU
    hull = [(0, 0), (7680, 0), (9216, 768), (9984, 1536), (9216, 2304),
            (7680, 3072), (0, 3072)]
    inside = [(256, 256), (7616, 256), (8960, 928), (9472, 1536),
              (8960, 2144), (7616, 2816), (256, 2816)]
    cabin_box = (1024, 768, 3072, 2304)
    mast_box = (5120, 1408, 5376, 1664)
    rim_z = GRADE - SHIP_RIM
    deck_z = rim_z + SHIP_DECK_DROP

    def edges(points):
        return {f"e{i}": i for i in range(len(points))}

    def box(b):
        return [(0, 0), (b[2] - b[0], 0), (b[2] - b[0], b[3] - b[1]),
                (0, b[3] - b[1])]

    def part(name, outline, origin, floor_z, floor_tile, wall_tile, shade,
             note):
        room = quay.room(name, outline, role="detail", faces=edges(outline),
                         frame=Frame(ship_x0 + origin[0], ship_y0 + origin[1]),
                         region_kwargs={"declared_zero_exit": True},
                         intent={"kind": "ship"}, note=note)
        room.style = Style(floor_picnum=floor_tile, wall_picnum=wall_tile,
                           ceiling_picnum=sky, parallax_ceiling=True,
                           floor_z=floor_z,
                           clear_height=STREET_SKY - (GRADE - floor_z),
                           floor_shade=shade)
        SHIP_FACES[room.region_id] = wall_tile
        return room

    def join(room, other, tag):
        for name in list(room.faces):
            if name.startswith("e"):
                city.connect(room.face(name), other.face(next(iter(other.faces))),
                             connection_id=f"connection:ship_{tag}_{name}")

    river.carve([(ship_x0 - river_x0 + x, ship_y0 - river_y0 + y)
                 for x, y in hull])
    rim = part("ship_rim", hull, (0, 0), rim_z, SHIP_PLANK, SHIP_HULL, 24,
               "the gunwale: the highest thing on the hull")
    rim.carve(inside)
    deck = part("ship_deck", inside, (0, 0), deck_z, BOARDWALK, SHIP_HULL, 28,
                "the deck, a step under the gunwale")
    deck.carve([(x, y) for x, y in box(cabin_box)]
               if False else [(cabin_box[0], cabin_box[1]),
                              (cabin_box[2], cabin_box[1]),
                              (cabin_box[2], cabin_box[3]),
                              (cabin_box[0], cabin_box[3])])
    deck.carve([(mast_box[0], mast_box[1]), (mast_box[2], mast_box[1]),
                (mast_box[2], mast_box[3]), (mast_box[0], mast_box[3])])
    cabin = part("ship_cabin", box(cabin_box), cabin_box[:2],
                 deck_z - SHIP_CABIN, SHIP_PLANK, SHIP_CABIN_WALL, 26,
                 "the deckhouse: a body high, shut")
    mast = part("ship_mast", box(mast_box), mast_box[:2], deck_z - SHIP_MAST,
                SHIP_PLANK, SHIP_MAST_TILE, 30, "the mast")
    join(rim, river, "hull")
    join(deck, rim, "deck")
    join(cabin, deck, "cabin")
    join(mast, deck, "mast")
    deck.light_source("ship_lamp", local=(0.7, 0.5), height_player_heights=1.0)
    # What is ON the deck is what makes a hull a ship (the study, after
    # DWE3M4's "Phantom" and E2M1): crates, and the black flag at the mast.
    #: A WHOLE tile to a face. They were 768 square and 12,288 high, and
    #: tile 452 is 64 texels: a face showed three quarters of the picture
    #: each way (the owner: "crates at ship has misaligned textures"). The
    #: small crate's module is 1,024 by 16,384 (`templates.SMALL_CRATE`).
    for index, (bx, by) in enumerate(((6144, 512), (6400, 1664))):
        crate_box = (bx, by, bx + 1024, by + 1024)
        deck.carve([(crate_box[0], crate_box[1]), (crate_box[2], crate_box[1]),
                    (crate_box[2], crate_box[3]), (crate_box[0], crate_box[3])])
        crate = part(f"ship_crate_{index}", box(crate_box), crate_box[:2],
                     deck_z - 16384, CRATE, CRATE, 24, "a crate on the deck")
        join(crate, deck, f"crate_{index}")
    SHIP_FLAG.append({
        "region_id": deck.region_id,
        "a1": (ship_x0 + mast_box[0], ship_y0 + mast_box[1]),
        "a2": (ship_x0 + mast_box[0], ship_y0 + mast_box[3])})
    built["ship"] = [rim.region_id, deck.region_id, cabin.region_id,
                     mast.region_id]

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
    # Each window is a pane in a frame -- reveal, sash pockets, box -- and
    # none of it is glazed on the facade line; see `glass.shopfront`.
    import glass
    window_parts = []
    fronts = []

    def window(name, rect_pu, outward, note, words=None):
        front = glass.shopfront([int(v * PU) for v in rect_pu], outward)

        def part(part_name, rect, part_note):
            made = room(part_name, *(v / PU for v in rect), shop, part_note,
                        role="detail")
            made.surfaces(floor_z=GRADE - glass.SILL,
                          clear_height=ROOM_HEIGHT - glass.SILL)
            window_parts.append(made)
            return made

        box = part(name, front["box"], note)
        reveal = part(f"{name}_reveal", front["reveal"],
                      "the window's surround: riser, fascia and the name")
        fronts.append((front, name, reveal, box, words))
        out, into = front["outward"], front["inward"]
        for index, rect in enumerate(front["sashes"]):
            sash = part(f"{name}_sash_{index}", rect,
                        "a sash pocket: the pane hangs at its back")
            sash.surfaces(wall_picnum=glass.JAMB_TILE)
            hall.connect(sash.face(out), reveal.face(into),
                         connection_id=f"connection:{name}_sash_{index}_reveal")
            hall.connect(sash.face(into), box.face(out),
                         connection_id=f"connection:{name}_sash_{index}_box")
        return box, reveal

    display_n, reveal_n = window(
        "display_n", (13.5, 40.5, 15.0, 44.0), "east",
        "east supermarket window: raised display behind glass",
        words="PROVISIONS")
    display_s, reveal_s = window(
        "display_s", (13.5, 47.0, 15.0, 48.0), "east",
        "east supermarket window: lower display behind glass")
    display_side, reveal_side = window(
        "display_side", (3.5, 40.0, 10.5, 40.5), "north",
        "north side display gallery behind glass", words="MARKET HALL")
    for front, front_name, reveal, box, words in fronts:
        glass.surround(front, name=front_name, kind="hall", reveal=reveal,
                       box=box, shop=sales, grade=GRADE, sill=glass.SILL,
                       box_clear=ROOM_HEIGHT - glass.SILL, words=words)
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
    for tag, box, reveal in (("north", display_n, reveal_n),
                             ("south", display_s, reveal_s)):
        hall.connect(box.face("west"), sales.face("east"),
                     connection_id=f"connection:supermarket_window_{tag}_in")
        city.connect(reveal.face("east"), market_st.face("north"),
                     connection_id=f"connection:supermarket_window_{tag}_street")
    hall.connect(display_side.face("south"), sales.face("north"),
                 connection_id="connection:supermarket_window_side_in")
    city.connect(reveal_side.face("north"), market_st.face("north"),
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
    #: A DOOR, in a frame. It was a sector of no height and no type: it
    #: never opened, and with nothing between its planks and the street
    #: they were drawn from the pavement to the sky (the owner:
    #: "Provisions backdoor aren't set in a frame and their texture goes up
    #: to the sky"). As a type-600 door it gets what the front door has:
    #: a thin leaf with a reveal each side, the outer one a recess at door
    #: height that gives the wall above back to the facade.
    staff_door = room("staff_door", 6.0, 49.5, 8.0, 50.0, common,
                      "staff-only rear entrance", role="doorway",
                      rk={"type": 600, "door_face": 22,
                          "inherit_finish": "both",
                          "sector_behavior": z_motion_door(
                              GRADE, GRADE - 16384)})
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
                           staff_door.region_id]
    built["interiors"] += [made.region_id for made in window_parts]
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
