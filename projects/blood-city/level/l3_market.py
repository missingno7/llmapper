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
* two **street stalls** and the **meat market** behind them (`meat_market`),
  and the **Demeter** at her moorings (`harbour_ship`).

Everything is placed from the L1 plan's own `furnish` slots for the area.
"""

from __future__ import annotations

import math
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.slope import SlopeSpec

from bloodmap.doors import z_motion_door

from materials import Material, BOARDWALK, FACADES, INTERIORS, MASONRY
from resolution import GRADE, PU, STREET_SKY

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

# The hall occupies most of block A (`meat_market`), with display galleries on
# its east and north sides.
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
#: The owner, 2026-11-25: "I would make the ocean bigger to the side and also
#: to distance it would make it to look better". It was 48 units wide and 20
#: deep: from the quay its edge stood 6 degrees under the eye and its sides
#: were the quay's own. DWE3M4's and DWE3M10's outer band is 95 by 173 units
#: (`SEA_WIDE` each side of ours, and 68 out), and nothing on it is cut finer.
SEA_BANDS = ((8, 38), (10, 40), (14, 42), (16, 43), (20, 44))
#: how far the light of each carries (a sector's `visibility`: 0 is the usual fall, 240 none). At the usual fall everything
#: past 25 units was black, and the sea read as a dark field before the sky.
SEA_CARRY = (0, 252, 248, 245, 243)
#: how far the bands beyond the near one run, west and east, in plan units
SEA_WIDE = (-60, 116)
#: ...and no wall of it is longer than this: the classic renderer sorts walls by products of their coordinates in 32 bits
#: (`wallfront`, xmapedit/src/engine.c), and with bands one wall wide everything past 38 units was drawn under the water.
#: The longest in DWE3M4 is 71,943.
SEA_STEP = 22
HORIZON_DEPTH = 1024
#: region ids of the horizon's pieces, for the build to check
HORIZON: list = []
#: The ship. Rim over the quay: DWE3M4's "Phantom" stands 11,264 over its
#: pier; deck under the rim: 4,096 (s671 under s625).
SHIP_RIM = 11264
SHIP_DECK_DROP = 4096
SHIP_MAST = 73728
#: The hull wore 67, "dark horizontal planks", DWE2M4's rowboat's: three
#: courses of it. Ten courses of its staggered butt joints were a brick wall.
#: 68, the single plank the campaign puts on 1,927 steps, runs in strakes.
#: 15 planks cap the rim; 28 is the wooden wall; 20 is the tile DWE2M6's
#: three masts wear.
SHIP_HULL, SHIP_PLANK, SHIP_CABIN_WALL, SHIP_MAST_TILE = 68, 15, 28, 20
#: region id -> the tile its raised sides wear (`skyline.dress_steps`)
SHIP_FACES: dict = {}
#: the owner's "smaller crate"; and E2M1 sprites 156/157, the black flag
CRATE = 452
FLAG = {"type": 0, "picnum": 3558, "cstat": 144, "x_repeat": 64,
        "y_repeat": 64, "shade": 8, "status": 0}
SHIP_FLAG: list = []


#: The promenade's fence. The owner, 2026-11-25: "we should add some fencing around the promenade, it might be combination of
#: rope sprites and wooden sectors", and of 258: the rope "used by fencing". Posts of the jetty's wood on the quay's edge, plan
#: units along it, open at the gangplank, at the boards the water is left by, and at the jetty; two strands between two posts
#: that are neighbours, as TEDE1M7 s284 hangs its one (9,216 up) and E2M7 s72 its own.
FENCE_RUNS = ((7.75, 9.85, 11.95, 14.05), (15.6, 17.5, 19.4, 21.3), (27.35, 29.4, 31.45, 33.5, 35.55, 37.6, 39.65, 41.7, 43.75, 45.8, 47.85))
FENCE_Y, FENCE_POST, FENCE_RISE, STRANDS, ROPE_TILE = 55.72, 256, 10240, (8704, 4864), 258
#: ropes: (region id, the two posts' facing sides in units, the floor they hang over)
ROPES: list = []


def rope(layout, name, region_id, a, b, floor_z) -> int:
    """Two sagging strands from a to b, as wall sprites seen from both sides."""
    import wallplane
    wide, tall, _x, offset = wallplane.art()[ROPE_TILE]
    length = math.dist(a, b)
    angle = round(math.atan2(b[1] - a[1], b[0] - a[0]) * 1024 / math.pi + 512) % 2048
    for k, up in enumerate(STRANDS):
        layout.add_sprite(f"fence:{name}:{k}", region_id, x=round((a[0] + b[0]) / 2), y=round((a[1] + b[1]) / 2), z=floor_z - up,
                          picnum=ROPE_TILE, x_repeat=min(255, round((length + 40) * 4 / wide)), y_repeat=64, angle=angle,
                          cstat=16 | 128, shade=10, type=0, status=0, spans_opening=True)
    return len(STRANDS)


def fly_flag(layout) -> int:
    """Hang the flag on the mast's west face, 2.3 bodies over the deck."""
    for spec in SHIP_FLAG:
        layout.place_on_wall(
            "ship:flag", spec["region_id"], a1=spec["a1"], a2=spec["a2"],
            t=0.5, height_player_heights=2.3, offset_player_widths=0.02,
            **FLAG)
    # the light out in the bay: a fire in the open on the tower's head
    import wallplane
    from bloodmap.placement import seated_z
    for region_id in LIGHT_ROOM:
        region = layout.regions[region_id]
        _w, tall, _x, offset = wallplane.art()[FIRE]
        layout.add_sprite("harbour:light", region_id, x=round(LIGHT_AT[0] * PU), y=round(LIGHT_AT[1] * PU),
                          z=seated_z(seat="floor", floor_z=region.floor_z, ceiling_z=region.ceiling_z, tile_height=tall,
                                     y_repeat=255, y_offset=offset, cstat=128, clearance=16),
                          picnum=FIRE, x_repeat=255, y_repeat=255, cstat=128, shade=-128, type=0, status=0)
    for k, (region_id, a, b, floor_z) in enumerate(ROPES):
        rope(layout, k, region_id, a, b, floor_z)
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
#: What stands out there, in plan units: (the band it lies in, name, its tiers). A tier is (outline, its top over the
#: water, floor shade, floor tile, the tile of its sides, how far its top tips). The far points of the bay close it on both
#: sides; between them one thing: the light. (Houses in whole storeys of their facades: 32,768.)
FAR_THINGS = (
    (2, "west_point", (
        (((-26, 79), (-17, 76.5), (-10, 77), (-5, 78.5), (-1, 81.5), (-6, 83.5), (-13, 86), (-24, 85)), 22000, 34, 273, 458, 6000),
        (((-23, 79.5), (-16, 78), (-11, 78.5), (-8, 80.5), (-12, 83.5), (-21, 83.5)), 52000, 36, 273, 458, -8000),
        (((-19, 80), (-16, 80), (-16, 82.5), (-19, 82.5)), 52000 + 65536, 30, 379, 384, 0),
        (((-14.5, 80.25), (-12.5, 80.25), (-12.5, 82), (-14.5, 82)), 52000 + 32768, 30, 379, 393, 0))),
    (2, "east_point", (
        (((58, 81), (62, 78), (70, 76), (80, 77.5), (84, 81), (79, 85.5), (68, 86.5), (61, 84.5)), 26000, 34, 273, 458, 5000),
        (((63, 80.5), (70, 78), (78, 79), (80, 81.5), (75, 84), (66, 84)), 64000, 36, 273, 458, -9000),
        (((67, 79.75), (71, 79.75), (71, 82.5), (67, 82.5)), 64000 + 32768, 30, 379, 385, 0),
        (((68, 80.25), (69, 80.25), (69, 81.25), (68, 81.25)), 64000 + 98304, 30, 379, 385, 0))),
    (3, "light_rock", (
        (((26, 95), (27.5, 92.5), (31, 91.5), (34, 92.5), (35, 95), (33.5, 97.5), (29.5, 98.5), (27, 97)), 12000, 33, 273, 458, 5000),
        (((28, 95), (29, 93.25), (31.5, 93), (33, 94.5), (32.5, 96.5), (30, 97)), 22000, 34, 273, 458, -3000))),
    # the skerry: out of reach, in view from the whole quay (a flat-topped stump until 2026-11-25)
    (1, "skerry", (
        (((39, 67), (40, 65.25), (42.5, 64.75), (44.5, 66), (44.25, 68), (42, 69.25), (40, 69)), 10000, 34, 273, 458, 5000),
        (((39.75, 67), (40.75, 65.75), (42.5, 65.5), (43.25, 67), (42, 68.5), (40.25, 68.25)), 30000, 32, 273, 458, 9000),
        (((40.5, 67), (41.25, 66.25), (42.25, 66.5), (42, 67.75), (41, 67.75)), 52000, 30, 273, 458, -9000))),
    (1, "reef_west", (
        (((-9, 68), (-7, 66.5), (-4.5, 67), (-4, 69), (-6.5, 70.5), (-8.5, 70)), 15000, 34, 273, 458, 6000),)),
    (2, "reef_mid", (
        (((45, 79), (47, 77.5), (50, 78), (50.5, 80), (48, 81.5), (46, 81)), 13000, 35, 273, 458, 5000),
        (((47, 79), (48.5, 78.5), (49, 79.75), (47.75, 80.25)), 22000, 34, 273, 458, 3000))),
    (3, "reef_far", (
        (((6, 100), (9, 98), (13, 98.5), (14, 101), (11, 102.5), (7, 102)), 14000, 35, 273, 458, 5000),)),
    (3, "reef_east", (
        (((68, 93), (71, 91.5), (74, 93), (73.5, 95.5), (70, 96)), 17000, 35, 273, 458, 6000),)),
)
#: the lighthouse on `light_rock`: its middle, the radius of its foot and its shaft, their tops over the water
LIGHT_AT, LIGHT_TIERS = (30.6, 95.0), ((1.5, 34000, 253, 253), (1.1, 34000 + 98304, 253, 253), (0.7, 34000 + 98304 + 9000, 253, 253))
LIGHT_ROOM: list = []
#: region ids of all of it, and the band each stands in: it is lit as its water is
FAR_REGIONS: dict = {}
FIRE = 2101                            # the owner's "flame (small fire)"
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
    for index, carry in zip([near, *(compiled.allocations[r].sector_id for r in SEA["far"])], SEA_CARRY):
        f(level.sectors[index])["visibility"] = carry
    for region_id, at in FAR_REGIONS.items():
        f(level.sectors[compiled.allocations[region_id].sector_id])["visibility"] = SEA_CARRY[at]
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
            length = math.hypot(int(n["x"]) - int(w["x"]),
                                int(n["y"]) - int(w["y"]))
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
    monument_node, monument_parts = memorial(
        plaza, market_st, _outline, grade=GRADE, clear_height=STREET_SKY,
        sky_tile=facade.ceiling, connector=district)
    citytree.declare_venue(monument_node, "monument", "free_standing",
                           built_by="l3_market")
    built["rooms"] += [r.region_id for r in monument_parts.values()]
    built["street_joined"].append(monument_parts["base"].region_id)
    built["monument"] = {name: room.region_id
                         for name, room in monument_parts.items()}
    #: The rooms themselves, so the dressing pass can ask them for their
    #: faces rather than reconstructing rectangles from region ids.
    built["monument_rooms"] = dict(monument_parts)

    # ---- the fountain: the memorial is it now (`memorial`) ----------------
    # L1 asked for a fountain centre-offset-west beside the monument; the
    # owner asked for one memorial with water, so the two are one.
    built["rooms"].append(monument_parts["pool"].region_id)

    # ---- two street stalls, where three bare platforms stood --------------
    import meat_market
    for stall in meat_market.build_stalls(plaza, district, market_st, _island,
                                          facade.ceiling, STREET_SKY):
        # half a body high: a counter is not walked onto
        built["rooms"].append(stall.region_id)

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

    # The near band's ends are the headlands' shores: north (broken by the
    # gangplank, the ship it leads to, and the jetty), the east head's four
    # edges, east, south, west, the west head's four.
    import harbour_ship
    jx0, jx1, jlen = JETTY
    round_ship = harbour_ship.river_edges()
    walk = ([("north", HEAD_WEST[1])]
            # the last of them is on the quay again: the quay's edge goes on
            + [("north_c" if k == len(round_ship) - 1 else f"hull{k}",
                (x - 4, y - city_d_pu)) for k, (x, y) in enumerate(round_ship)]
            + [("jw", (jx0, 0)), ("js", (jx0, jlen)), ("je", (jx1, jlen)),
               ("north_b", (jx1, 0)), ("he0", HEAD_EAST[0])]
            + [(f"he{k + 1}" if k < 3 else "east", point)
               for k, point in enumerate(reversed(HEAD_EAST[2:]))]
            + [("south", (48, SEA_BANDS[0][0])), ("west", (0, SEA_BANDS[0][0]))]
            + [(f"hw{k}", point)
               for k, point in enumerate(reversed(HEAD_WEST[2:]))])
    near_outline = [(int(x * PU), int(y * PU)) for _name, (x, y) in walk]
    near_faces = {name: index for index, (name, _point) in enumerate(walk)}

    #: The bands beyond the near one are WIDER than it by `FLANK_END` at
    #: each side. A blind reviewer on the build that first had flanks:
    #: "the brick wall ends flat against the sky, a cut-off edge with no
    #: visible side or thickness". The step in the sea's outline is that
    #: side: the flank building's END FACE, turning its far corner.
    far_x0, far_x1 = river_x0 - FLANK_END, river_x1 + FLANK_END
    wide_x0, wide_x1 = (int(v * PU) for v in SEA_WIDE)

    sea_cuts = [x * PU for x in range(SEA_WIDE[0], SEA_WIDE[1] + 1, SEA_STEP)]
    first_far = river_y0 + SEA_BANDS[0][0] * PU
    first_cuts = sorted({v for v in sea_cuts if v < far_x0 or v > far_x1} | {far_x0, river_x0, river_x1, far_x1})

    def water_band(name, y0, depth, shade, note, outline=None):
        wide = outline is None
        x0, x1 = (wide_x0, wide_x1) if wide else (river_x0, river_x1)
        if wide:
            north = [v - x0 for v in (first_cuts if y0 == first_far else sea_cuts)]
            south = [v - x0 for v in sea_cuts]
            points = [(v, 0) for v in north] + [(v, depth) for v in reversed(south)]
            sides = {f"n{k}": k for k in range(len(north) - 1)}
            sides["east"] = len(north) - 1
            sides.update({f"s{k}": len(points) - 2 - k for k in range(len(south) - 1)})
            sides["west"] = len(points) - 1
        band = quay.room(
            name, outline or points,
            role="exterior",
            faces=dict(near_faces) if outline else sides,
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
        if index == 1:
            at = first_cuts.index(river_x0)
            city.connect(bands[-1].face("south"), band.face(f"n{at}"),
                         connection_id=f"connection:sea_{index}")
        elif bands:
            for k in range(len(sea_cuts) - 1):
                city.connect(bands[-1].face(f"s{k}"), band.face(f"n{k}"),
                             connection_id=f"connection:sea_{index}_{k}")
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
        west = horizon(f"horizon_w{index}", wide_x0 - HORIZON_DEPTH, y,
                       wide_x0, y + depth * PU)
        east = horizon(f"horizon_e{index}", wide_x1, y,
                       wide_x1 + HORIZON_DEPTH, y + depth * PU)
        if index == 1:
            # past the harbour's two buildings the sea has a north side too
            before = None
            for k, (x0, x1) in enumerate(zip(first_cuts, first_cuts[1:])):
                if far_x0 <= x0 < far_x1:
                    before = None
                    continue
                shore = horizon(f"horizon_n{k}", x0, y - HORIZON_DEPTH, x1, y)
                city.connect(band.face(f"n{k}"), shore.face("south"),
                             connection_id=f"connection:horizon_n{k}")
                if before is not None:
                    city.connect(before.face("east"), shore.face("west"),
                                 connection_id=f"connection:horizon_n{k}_on")
                before = shore
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
    before = None
    for k, (x0, x1) in enumerate(zip(sea_cuts, sea_cuts[1:])):
        south = horizon(f"horizon_s{k}", x0, y, x1, y + HORIZON_DEPTH)
        city.connect(bands[-1].face(f"s{k}"), south.face("north"),
                     connection_id=f"connection:horizon_s{k}")
        if before is not None:
            city.connect(before.face("east"), south.face("west"),
                         connection_id=f"connection:horizon_s{k}_on")
        before = south
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
        #: three to a side (2,112 apart): DWE2M6's stand 2,560 apart
        for k in range(3):
            py = 512 + k * 2112
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
    # the jetty's own posts carry the same rope
    ROPES.clear()
    for px in (inset, jw - inset - post):
        for k in range(2):
            x = river_x0 + int(jx0 * PU) + px + post // 2
            y0, y1 = (river_y0 + 512 + j * 2112 + (post if j == k else 0) for j in (k, k + 1))
            ROPES.append((jetty.region_id, (x, y0), (x, y1), GRADE))
    # and the quay's edge, from headland to headland
    for run, xs in enumerate(FENCE_RUNS):
        for k, x in enumerate(xs):
            x0, y0 = int(x * PU) - FENCE_POST // 2, int(FENCE_Y * PU) - FENCE_POST // 2
            stake = _island(quay, city, market_st, f"fence_{run}_{k}", x0=x0, y0=y0, x1=x0 + FENCE_POST, y1=y0 + FENCE_POST,
                            floor_z=GRADE - FENCE_RISE, note="a post of the promenade's fence",
                            style=Style(floor_picnum=PILE_TILE, wall_picnum=PILE_TILE, ceiling_picnum=sky, parallax_ceiling=True,
                                        floor_z=GRADE - FENCE_RISE, clear_height=STREET_SKY - FENCE_RISE, floor_shade=26),
                            region_kwargs={"declared_zero_exit": True})
            SHIP_FACES[stake.region_id] = PILE_TILE
            if k:
                y = int(FENCE_Y * PU)
                ROPES.append((market_st.region_id, (int(xs[k - 1] * PU) + FENCE_POST // 2, y), (x0, y), GRADE))
    built["fence"] = sum(len(xs) for xs in FENCE_RUNS)

    # Out in the bay: its two points, reefs, and the light.
    tops = [river_y0 + sum(d for d, _s in SEA_BANDS[:k]) * PU for k in range(len(SEA_BANDS))]
    things = [(b, n, t) for b, n, t in FAR_THINGS]
    for at, (radius, rise, floor, side) in enumerate(LIGHT_TIERS):
        ring = tuple((LIGHT_AT[0] + radius * math.sin(math.pi * (k + 0.5) / 4), LIGHT_AT[1] - radius * math.cos(math.pi * (k + 0.5) / 4))
                     for k in range(8))
        things = [(b, n, (*t, (ring, rise, 26 - 6 * at, floor, side, 0))) if n == "light_rock" else (b, n, t) for b, n, t in things]
    for at, name, tiers in things:
        under, corner = bands[at], (wide_x0, tops[at])
        placed = []
        for k, (outline, rise, shade, floor, side, fall) in enumerate(tiers):
            points = [(round(x * PU) - river_x0, round(y * PU) - river_y0) for x, y in outline]
            made, _points, origin = rock(f"{name}_{k}", [(x / PU, y / PU) for x, y in points], rise, shade,
                                         "out in the bay: seen and never reached", tile=floor, face=side, fall=fall)
            made.intent = {"kind": "sea_rock"}
            # it stands in the tier it lies inside of, or in the water
            from shapely import Polygon
            here = Polygon(outline)
            host, host_corner = under, corner
            for other, shape, other_corner in placed:
                if shape.contains(here):
                    host, host_corner = other, other_corner
            mine = (river_x0 + origin[0], river_y0 + origin[1])
            host.carve([(x + river_x0 - host_corner[0], y + river_y0 - host_corner[1]) for x, y in points])
            for face in list(made.faces):
                city.connect(made.face(face), host.face("n0" if host is under else "e0"),
                             connection_id=f"connection:{name}_{k}_{face}")
            placed.append((made, here, mine))
            FAR_REGIONS[made.region_id] = at
            if name == "light_rock":
                LIGHT_ROOM[:] = [made.region_id]
    city.connect(river.face("north"), market_st.face("south"),
                 connection_id="connection:quay_river")

    # every stretch of the quay's edge is the same water's
    city.connect(river.face("north_c"), market_st.face("south"),
                 connection_id="connection:quay_river_c")

    # ---- the ship: a hull that can be boarded (`harbour_ship`) -------------
    # It was a 4 x 2 rectangle of boards a step over the water, and then a
    # hull a unit off the quay with its deckhouse shut. Every hull in the
    # corpus that reads as a boat (DWE3M4's "Phantom", DWE2M6's ghost ship,
    # DWE2M4's rowboat) has a pointed or tapered end, a thin RIM that is the
    # highest thing with the deck lower inside it, and a hull tile that is
    # not the deck's. This is the Phantom's plan: 13,312 by 4,096, bow to the
    # east, the rim 0.66 body over the quay as the Phantom's is over its
    # pier, the deck 4,096 under the rim.
    import sys as _sys
    parts = harbour_ship.build(quay, city, river, market_st, sky=sky,
                               sky_clear=STREET_SKY,
                               market=_sys.modules[__name__])
    deck = parts["deck"]
    deck.light_source("ship_lamp", local=(0.04, 0.3), height_player_heights=1.0)
    mx0, my0, _mx1, my1 = (int(v * PU) for v in harbour_ship.MAST)
    SHIP_FLAG.append({"region_id": deck.region_id,
                      "a1": (mx0, my0), "a2": (mx0, my1)})
    # what a body reaches from the quay in steps
    built["street_joined"] += [parts[n].region_id for n in (
        "gang", "deck", "rim", "sill", "stair", "hold")]
    built["rooms"] += [room.region_id for room in parts.values()]
    built["ship"] = [room.region_id for room in parts.values()]

    # ---- the market hall: a meat market inside block A (`meat_market`) ----
    shop, common = INTERIORS["shop"], INTERIORS["common"]
    import citytree
    hall = district.assembly(
        "market_hall",
        style=Style(**common.style_kwargs(floor_z=GRADE,
                                          clear_height=ROOM_HEIGHT,
                                          floor_shade=32)),
        note="market hall: a meat market, its cold store and its clerk's gallery")
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

    parts = meat_market.build(hall, shop=shop, room=room)
    sales, stock = parts["sales"], parts["lobby"]
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
    # leaving the windows as coincident fake walls.
    for tag, box, reveal in (("north", display_n, reveal_n),
                             ("south", display_s, reveal_s)):
        hall.connect(box.face("west"), sales.face("east"),
                     connection_id=f"connection:supermarket_window_{tag}_in")
        city.connect(reveal.face("east"), market_st.face("north"),
                     connection_id=f"connection:supermarket_window_{tag}_street")
    # the north gallery lies along the nook and the hall's west end
    hall.connect(parts["nook"].face("north"), display_side.face("south"),
                 connection_id="connection:supermarket_window_side_nook")
    shown = 10.5 - meat_market.HALL[0]
    wide = meat_market.HALL[2] - meat_market.HALL[0]
    hall.connect(sales.face("north", at=shown / 2 / wide, width=int(shown * PU)),
                 display_side.face("south"),
                 connection_id="connection:supermarket_window_side_in")
    city.connect(reveal_side.face("north"), market_st.face("north"),
                 connection_id="connection:supermarket_window_side_street")
    hall.connect(door.face("west"), sales.face("east"),
                 connection_id="connection:hall_door_in")
    hall.connect(porch.face("west"), door.face("east"),
                 connection_id="connection:hall_porch_door")
    city.connect(porch.face("east"), market_st.face("north"),
                 connection_id="connection:hall_porch_plaza")
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
                                  "street": market_st, "river": river,
                                  "display_n": display_n, "display_s": display_s,
                                  "display_side": display_side,
                                  "staff_door": staff_door}
    built["rooms"] += [sales.region_id, stock.region_id]
    built["interiors"] += [sales.region_id, stock.region_id,
                           parts["nook"].region_id,
                           staff_door.region_id]
    built["interiors"] += [made.region_id for made in window_parts]
    return built


def dress_supermarket(layout, rooms) -> dict:
    """The hall's clock and outlet, then what the hall, the stalls and the ship hold (`meat_market`, `harbour_ship`)."""
    import harbour_ship
    import meat_market
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
    return {"wall_details": 2, "tiles": [1165, 1050],
            **meat_market.dress(layout, rooms["street"].region_id),
            "ship": harbour_ship.dress(layout, __import__("underwater").SLIP)}


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
#: (On the memorial's backdrop, over the box the water falls from: the box
#: stands 1.6 bodies over the plaza, the rim 0.24, so the lines start above
#: it, measured from the rim; the emblem stands over them.)
MONUMENT_WORDS = (
    ("WELCOME TO", 2.15),
    ("GRAVESEND", 1.8),
)


#: THE MEMORIAL (owner, 2026-11-20: "I would also rework that welcome to
#: gravesend we can do some bigger memorial with water or something more
#: eye catching"). The first rework was water everywhere -- a block whose
#: four faces were waterfalls -- and the owner: "That one you created looks
#: quite bad now, there should be that combination of stone and water, to
#: give it some shape", pointing at his own street memorial in RABIDN09
#: (sectors 153-158, 190-198, 346-354; not copied, read for its ideas):
#: the STONE is the shape and the water fills what the stone leaves. A low
#: rim of light dressed stone (253) round a pool (2915); a tall dark backdrop
#: of grey brick (421) with an emblem high on it (his ram skull, 1348); in
#: front of it a dark box rising out of the water with ONE narrow fall down
#: its middle (1005, moving as E3M6's wall 450 moves) and foam at its foot
#: (1037); either side, a drum of ornamented stone (409) standing in the
#: water with a carved panel top (360) and a crouching statue (536).
#: Heights in Build z, up from the plaza.
PARAPET_RISE = 4096                 # the rim: a step up off the plaza
#: an obelisk on the backdrop: its step, its shaft and its point, (half across, half deep, how far over the one below). The square's
#: own landmark: blind readers of it found "no memorial with a recognizable silhouette" (showcase round 14)
OBELISK = (("step", 1216, 512, 6144), ("shaft", 448, 352, 40960), ("point", 224, 176, 9216))
BACKDROP_RISE = 59392               # 3.5 bodies over the rim
BOX_RISE, FALL_RISE = 27136, 25088  # over the water; the fall's lip a little under the box's top
DRUM_RISE = 16384                   # over the water: a body over the rim
BAND = 2560                         # the rim's north band, which the backdrop stands on
POOL_INSET = 768                    # the rim's width elsewhere
RIM_STONE, DARK_STONE, MEMORIAL_WATER, FALLING = 253, 421, 2915, 1005
#: (the owner's drums wear 364, an ogee lattice; the campaign never puts it
#: on a step face, so ours wear his named meander-ornament stone, 409, the
#: station pier's)
DRUM_FACE, DRUM_TOP = 409, 360
FALLS = {"pan_always": 1, "pan_y_velocity": -75, "y_pan_fraction": 32}


def memorial(parent, street, outline, *, grade: int, clear_height: int,
             sky_tile: int, connector) -> tuple:
    """The plaza memorial, filling the hole the street cuts for it.

    Concentric, as `templates.monument` and `setpieces.basin` are: the rim
    fills the street's (chamfered) hole; the pool is carved out of the rim
    and the backdrop stands on the rim's north band; the box, the fall and
    the drums stand in the pool, none touching another, so every coincident
    edge is a declared portal.
    """
    import citytree
    import setpieces
    from bloodmap.levelprog import Frame, _compass_edges

    def mat(wall, floor, note):
        return Material(wall=wall, floor=floor, ceiling=sky_tile, opening=wall,
                        sky=True, note=note)

    rim_m = mat(RIM_STONE, RIM_STONE, "the memorial's rim")
    dark = mat(DARK_STONE, RIM_STONE, "the memorial's dark stone")
    water = mat(RIM_STONE, MEMORIAL_WATER, "the memorial's water")
    falls = mat(FALLING, MEMORIAL_WATER, "the falling water")
    drum_m = mat(DRUM_FACE, DRUM_TOP, "a statue's drum")
    node = parent.assembly("monument", note="the Gravesend memorial: stone and water")
    points = [(int(px), int(py)) for px, py in outline]
    ox, oy = min(p[0] for p in points), min(p[1] for p in points)
    local = [(px - ox, py - oy) for px, py in points]
    rim = citytree.make_room(
        node, "parapet", local, role="detail", frame=Frame(ox, oy),
        faces={f"edge{index}": index for index in range(len(points))},
        region_kwargs=rim_m.region_kwargs(),
        note="the rim round the pool: one low step off the plaza")
    rim.surfaces(**rim_m.style_kwargs(floor_z=grade - PARAPET_RISE,
                                      clear_height=clear_height - PARAPET_RISE))
    rim.faces.update(_compass_edges(local))
    for index in range(len(points)):
        connector.connect(rim.face(f"edge{index}"), street.face("north"),
                          connection_id=f"connection:memorial_rim_{index}")
    x0, y0 = ox, oy
    x1, y1 = max(p[0] for p in points), max(p[1] for p in points)
    cx = (x0 + x1) // 2
    made = {"rim": rim}
    # the backdrop, on the rim's north band
    made["backdrop"] = setpieces.raised_solid(
        node, "backdrop", rim, (x0 + 1536, y0 + 512, x1 - 1536, y0 + BAND - 512),
        dark, grade=grade - PARAPET_RISE, rise=BACKDROP_RISE,
        host_clear=clear_height - PARAPET_RISE, connector=connector,
        face_picnum=DARK_STONE, shade=12,
        note="the backdrop: the city's name and the emblem over the water")
    host, top, deep = made["backdrop"], grade - PARAPET_RISE - BACKDROP_RISE, y0 + BAND // 2
    for label, across, half, over in OBELISK:
        made[f"obelisk_{label}"] = setpieces.raised_solid(
            node, f"obelisk_{label}", host, (cx - across, deep - half, cx + across, deep + half), dark, grade=top, rise=over,
            host_clear=clear_height - (grade - top), connector=connector, face_picnum=RIM_STONE if label != "shaft" else DARK_STONE, shade=10,
            note=f"the memorial's obelisk: its {label}")
        host, top = made[f"obelisk_{label}"], top - over
        host.region_kwargs["declared_zero_exit"] = True                 # nobody is up there
    # the pool, the rest of the rim's middle
    px0, py0, px1, py1 = x0 + POOL_INSET, y0 + BAND, x1 - POOL_INSET, y1 - POOL_INSET
    setpieces._carve_into(rim, (px0, py0, px1, py1))
    pool = setpieces._rect_room(node, "pool", (px0, py0, px1, py1), water,
                                floor_z=grade, clear=clear_height,
                                behavior={"depth": setpieces.WATER_DEPTH},
                                note="the memorial's pool")
    setpieces._rim(connector, pool, rim, "memorial_pool")
    made["pool"] = pool
    box = (cx - 1536, py0 + 256, cx + 1536, py0 + 1536)
    # a sheet of water, not a block: a quarter of a body proud of the box
    fall = (cx - 512, box[3] + 64, cx + 512, box[3] + 320)
    for label, rect, material, rise, face, behavior, shade in (
            ("box", box, dark, BOX_RISE, DARK_STONE, None, 14),
            ("fall", fall, falls, FALL_RISE, FALLING, FALLS, 24),
            ("drum_0", (px0 + 384, py0 + 640, px0 + 1664, py0 + 1920), drum_m,
             DRUM_RISE, DRUM_FACE, None, 10),
            ("drum_1", (px1 - 1664, py0 + 640, px1 - 384, py0 + 1920), drum_m,
             DRUM_RISE, DRUM_FACE, None, 10)):
        made[label] = setpieces.raised_solid(
            node, label, pool, rect, material, grade=grade, rise=rise,
            host_clear=clear_height, connector=connector, face_picnum=face,
            wall_behavior=behavior, shade=shade,
            note={"box": "the dark box the water falls from",
                  "fall": "the one narrow fall, its lip under the box's top",
                  "drum_0": "a statue's drum in the water",
                  "drum_1": "a statue's drum in the water"}[label])
    # `dress_monument` letters the backdrop from the rim it stands on and
    # sets the flame on its top
    made.update(base=rim, plinth=made["backdrop"], pedestal=made["obelisk_point"])
    return node, made


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

    # THE MEMORIAL'S FIGURES, as the owner's RABIDN09 memorial sets them
    # (its sprites, read for their records): a crouching statue (536, repeat
    # 64) on each drum, the foam (1037, repeat 32, cstat 144) where the fall
    # meets the pool, and the emblem high on the backdrop (his ram skull,
    # 1348, repeat 152, cstat 208).
    for index in (0, 1):
        drum = parts.get(f"drum_{index}")
        if drum is not None:
            layout.place_on_floor(
                # his cstat, 385: centred (128), as all five of the
                # campaign's 536 are -- the art is offset by half its height
                # to be drawn so, and written without the bit it stood 0.83
                # bodies in the air
                f"monument:statue_{index}", drum.region_id, local=(0.5, 0.5),
                picnum=536, cstat=385, x_repeat=64, y_repeat=64, shade=8, pal=0,
                type=0, status=0)
            report["statues"] = report.get("statues", 0) + 1
    fall = parts.get("fall")
    if fall is not None:
        fx0, fy0, fx1, fy1 = props.room_rect(fall)
        pool = parts["pool"]
        layout.add_sprite("monument:foam", pool.region_id, x=(fx0 + fx1) // 2,
                          y=fy1 + 32, z=int(layout.regions[pool.region_id].floor_z),
                          picnum=1037, cstat=144, x_repeat=32, y_repeat=32,
                          angle=512, shade=0, pal=0, type=0, status=0)
    backdrop = parts.get("backdrop")
    if backdrop is not None:
        b2, b1 = props.face_segment(props.room_rect(backdrop), "south", inset=64)
        got = wallplane.sprite(
            # (his is at 152, 4,180 wide: on a backdrop five units wide that
            # is the lettering's room; at 64 it stands over the letters)
            layout, "monument:emblem", base.region_id, b1, b2, tile=1348,
            x_repeat=64, y_repeat=64, cstat=16 | 64 | 128, t=0.5,
            height_player_heights=3.05, offset_player_widths=0.06, shade=0,
            over_steps=True)
        report["emblem"] = bool(got)

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
        # (off the memorial's parapet: its "base", which carries the name,
        # stands in the middle of the pool)
        x0, y0, x1, y1 = props.room_rect(parts.get("rim", base))
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
