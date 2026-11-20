"""L3 for the pilot district: Foundry Ward, dressed.

Attached to the L2 skeleton by names and anchors (design-layers.md): the
works canteen venue (venue-patterns `shop`), the yard's furniture
(street-furniture.md industrial vocabulary), the staged destruction moment
on the grate approach (the district's channel reserve), population and breakables at campaign registers,
and the sewer's E3M3 dressing (animated shade, a wet trunk).

Sprite and door specs are attested: looked up from campaign maps at build
time rather than invented (the blood-physics lesson: transcribe, never
invent).

This module never states a global coordinate: everything derives from the
L1 plan rects and the L2 context passed in.
"""

from __future__ import annotations

import functools

from bloodmap.doors import z_motion_door
from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.levelprog import Frame, RECT_FACES, Style
from bloodmap.prefab import breakable

from resolution import (
    DISTRICT_STYLE, FLOOR_BOARDWALK, FLOOR_GROUND, GRADE, PU, SEWER_CLEAR,
    SKY_TILE, STREET_SKY,
)
from materials import FACADES, INTERIORS, MASONRY

COMPASS = dict(zip(RECT_FACES, range(4)))

#: The campaign's direct-use Z-door family uses tile 22 (64x128); 390 is a
#: masonry surface and made our public leaves read as plain brown wall.
DOOR_FACE_TILE = 22
#: The yard's cage: how deep it is behind its bars, and where they stand.
CAGE_DEEP = 1792
CAGE: dict = {}
#: The canteen's doors were 16,384 high: lower than a body (16,960) and lower
#: than 87% of the campaign's 594 ceiling doors, whose median opens 28,672.
#: The owner, standing in the yard on 2026-11-20: "these low doors ...
#: something what is not finished properly". They take the height every
#: other venue in the city already uses.
CANTEEN_DOOR_H = 31744
#: E1M4's RATDOGS hatch: its grill stands 8,192 above the midway (s167).
#: Its opening there is 16,384 high; here it takes the place of a painted
#: window, and a hatch that stopped at 16,384 left the window's arch
#: standing over it, so it rises to the door's head as the door does.
HATCH_SILL = 8192
HATCH_CLEAR = CANTEEN_DOOR_H - HATCH_SILL
#: The dine-in, north to south: its own 2,560 and the old back room's 2,048.
DINE_DEEP = 4608
#: The kitchen is the strip west of the counter, the hatch's width and more;
#: the pass is the room the counter leaves at its north end for the cook.
KITCHEN_W, COUNTER_PASS = 2048, 1792
#: The freezer: two bays north of the dine-in, less a door's thickness.
FREEZER_DEEP = 1792
JAMB_TILE = 170

#: Lamp sconce, campaign modal form (decoration registry tile 641).
LAMP_TILE = 641
#: ...but 641 is the owner's "lamp hanging on a chain", and in seven town
#: maps all 13 of it hang under a ceiling. The yard has the sky over it:
#: the two there hung from nothing. A yard wall carries the bracket (506).
import props as _props
YARD_LAMP = _props.fields(_props.FLAME)
YARD_LAMP_HEIGHT = _props.height_of(_props.FLAME)
LAMP_FIELDS = {"picnum": 641, "x_repeat": 64, "y_repeat": 64, "cstat": 129,
               "shade": -128, "type": 0}

#: The district's channel allocation starts here (CN 8; city_plan CHANNELS).
#: The staged moment's wire is declared on the build's circuit
#: (`bloodmap.wiring.Circuit`), which numbers it. It used to be channel 30,
#: typed here: that is the engine's kChannelPlayer0, and the grate reported
#: no change of state, so stepping on it sent nothing at all.


@functools.lru_cache(maxsize=None)
def _attested_tile(map_name: str, picnum: int) -> dict:
    """A decoration's fields, copied from the first one a campaign map has."""
    disk = read_map(corpus_map_path(map_name))
    for sprite in disk.sprites:
        if int(sprite.fields["picnum"]) == picnum:
            fields = {k: int(sprite.fields[k]) for k in
                      ("picnum", "x_repeat", "y_repeat", "cstat", "status", "type")}
            return fields
    raise KeyError(f"{map_name} has no sprite wearing tile {picnum}")


@functools.lru_cache(maxsize=None)
def _attested(map_name: str, type_id: int, picnum: int | None = None) -> dict:
    """Sprite fields + behavior for a type, transcribed from a campaign map.

    `picnum` narrows the match: decorations all carry type 0, so a fire is
    identified by the tile the campaign draws it with.
    """
    disk = read_map(corpus_map_path(map_name))
    for sprite in disk.sprites:
        if int(sprite.fields.get("type", 0)) == type_id and (
                picnum is None or int(sprite.fields["picnum"]) == picnum):
            fields = {k: int(sprite.fields[k]) for k in
                      ("picnum", "x_repeat", "y_repeat", "cstat", "status")}
            fields["type"] = type_id
            behavior = {}
            if sprite.extra is not None:
                for key, value in sprite.extra.fields.items():
                    if key.startswith("data_") and value:
                        behavior[key] = int(value)
            return {"fields": fields, "behavior": behavior}
    raise LookupError(f"{map_name} carries no sprite of type {type_id}")


def dress(city, ctx) -> dict:
    """Attach Foundry Ward's L3 content.  Returns what it placed."""
    foundry_st = ctx["foundry_st"]
    yard = ctx["yard_rect_pu"]
    grate_upper = ctx["grate_upper"]
    sewer_rooms = ctx["sewer_rooms"]
    placed = {"sprites": [], "channels": set(), "rooms": []}

    yard_x0, yard_y0, yard_x1, yard_y1 = (int(v * PU) for v in yard)
    fx0, fy0 = ctx["foundry_origin"]

    # ---- the works canteen: RAT DOGS -----------------------------------
    # The owner, 2026-11-20: "canteen should look more like a canteen" and
    # "I would give it some unique style, like rat dogs (similar to E1M4)".
    # It was the VP shop in brick and chequer; it is E1M4's rat-dog stand
    # now, scaled to a works canteen: that stand's kitchen materials, its
    # grill seen through a hatch in the street wall, and its name over the
    # hatch (`knowledge/blood/studies/ratdogs-stand/notes.md`).
    shop = INTERIORS["ratdogs"]
    import citytree
    canteen = city.assembly(
        "canteen",
        # The campaign's median room is one wall-texture repeat tall
        # (33,280); ours were 20,480 and the discriminator saw it.
        # E1M4's kitchen is lit at shade 8 to 16 (s170); rusted metal is
        # dark art, and at the city's interior shades it read as black.
        style=Style(**shop.style_kwargs(floor_shade=8, ceiling_shade=12,
                                        wall_shade=8,
                                        floor_z=GRADE, clear_height=32768)),
        note="the works canteen, RAT DOGS: E1M4's stand, behind a z-motion door",
    )
    citytree.declare_venue(canteen, "works_canteen", "open_front",
                           built_by="l3_foundry")
    # The canteen used to start at yard_x0 - 512, i.e. half a bay off the
    # 1024 grid, so every opening in its face cut the painted windows.  On
    # the grid, its doors can be whole bays with piers between them.
    main_x0, main_y1 = yard_x0 - 1024, yard_y0       # north of the yard
    # THE CANTEEN GREW NORTH (owner, 2026-11-20: "you can even change shape
    # of the building"). The dine-in was 4,096 by 2,560 with a back room
    # behind it, 11.2 M of floor where a destination wants 14.0 M; the back
    # room is now part of it, and the freezer took the place of the rail-
    # yard backdrop box that stood north of the back room, whose window
    # made a cold store look out on a sky.
    main_y0 = main_y1 - 512 - DINE_DEEP
    main = canteen.room(
        "main", [(0, 0), (4096, 0), (4096, DINE_DEEP), (0, DINE_DEEP)],
        role="interior", faces=dict(COMPASS),
        frame=Frame(main_x0, main_y0),
        region_kwargs=shop.region_kwargs(),
        note="main room; counter and display are geometry (VP shop)",
        intent={"venue": "works_canteen", "type": "shop"},
    )
    # THE DINE-IN. The owner, 2026-11-20: "Interior is bit empty, I would
    # add dine in". The main room is E1M2's station buffet, s185: a black
    # and grey marble chequer (290) under brown stucco (140), walls of clay
    # over a dark stone base (150), and round stand-up tables (649) for
    # eating on your feet, which is what a works canteen is. The counter and
    # the hatch keep the stand's iron.
    main.surfaces(wall_picnum=150, floor_picnum=290, ceiling_picnum=140,
                  floor_shade=4, ceiling_shade=12, wall_shade=6)
    # THE FREEZER. "... and maybe freezer to the back." The back room is a
    # walk-in meat store: E1M3's (s305) riveted metal floor (315) under
    # rusted metal (255), grey walls frosted with grime at the foot (345),
    # carcasses on hooks, kept cold and dark (E1M2's locker, s268, stands
    # at shade 46), behind a metal door (495, E3M2's). Its dressing is in
    # `sprinkle`. It has no window.
    back = canteen.room(
        "back", [(0, 0), (4096, 0), (4096, FREEZER_DEEP),
                 (0, FREEZER_DEEP)],
        role="interior", faces=dict(COMPASS),
        frame=Frame(main_x0, main_y0 - 2048),
        region_kwargs=shop.region_kwargs(),
        note="the walk-in freezer, north of the dine-in",
    )
    back.surfaces(wall_picnum=345, floor_picnum=315, ceiling_picnum=255,
                  floor_shade=30, ceiling_shade=34, wall_shade=26)
    freezer_door = canteen.room(
        "freezer_door", [(0, 0), (1024, 0), (1024, 2048 - FREEZER_DEEP),
                         (0, 2048 - FREEZER_DEEP)],
        role="doorway", faces=dict(COMPASS),
        frame=Frame(main_x0 + 2048, main_y0 - (2048 - FREEZER_DEEP)),
        region_kwargs={
            "type": 600, "door_face": 495, "inherit_finish": "both",
            "sector_behavior": z_motion_door(GRADE, GRADE - CANTEEN_DOOR_H),
        },
        note="the freezer's metal door: a push door like the canteen's own",
    )
    freezer_door.surfaces(wall_picnum=200, floor_z=GRADE, clear_height=0)
    canteen.connect(freezer_door.face("north"), back.face("south"),
                    connection_id="connection:freezer_door_in")
    canteen.connect(freezer_door.face("south"), main.face("north"),
                    connection_id="connection:canteen_back")

    # THE COUNTER. It was an iron island a quarter of a body high in the
    # middle of the floor, and the showcase's blind reader said of it, in
    # both rounds: "the low grill reads as a box ... there's no clear place
    # to order or eat" (`reports/showcase/round-2/showcase.md`). It is a
    # serving counter now: Blood's own (`fixtures.BAR`, half a body, wood
    # top 34, plank face 28), one run from the south wall to within a pass
    # of the north, on the door's left as you come in. West of it is the
    # kitchen: the hatch and its grill, the pans and the sign on its wall.
    # East of it the customers stand, on stools along its face.
    import fixtures
    counter_run = fixtures.run_along(
        "canteen_counter", main, axis="y",
        start=main_y0 + COUNTER_PASS, end=main_y0 + DINE_DEEP - 256,
        across0=main_x0 + KITCHEN_W, across1=main_x0 + KITCHEN_W + fixtures.BAR.depth,
        family="bar", material=shop, grade=GRADE, host_clear=32768,
        connector=canteen, whole=True, wall_picnum=fixtures.BAR_FACE)
    counter = counter_run.children[0]
    # The block's own sector runs to the room's ceiling: give it the hall's,
    # or a dark slab of the stand's ceiling hangs over the counter.
    counter.surfaces(ceiling_picnum=140, ceiling_shade=12)
    # THE GRIDDLE. Showcase round 3, with the counter built: "the diner has
    # no visible cooking station to connect the rats and cleaver to what's
    # being served", and with the signs hidden the room was "a bar". The
    # cook's range stands in the kitchen under the pans, a counter's height
    # and E1M4's grill on top (ribbed iron 376 over riveted metal 2453, the
    # stand's own), so the rats are seen cooking from the dine-in.
    griddle = fixtures.place(
        "canteen_griddle", main,
        (main_x0 + 512, main_y0 + DINE_DEEP - 1792,
         main_x0 + 512 + fixtures.BAR.depth, main_y0 + DINE_DEEP - 256),
        shop, family="bar", grade=GRADE, host_clear=32768,
        connector=canteen, wall_picnum=2453)
    griddle.surfaces(floor_picnum=376, ceiling_picnum=140, ceiling_shade=12,
                     floor_shade=4)
    # The kitchen's shelf: a niche let into the west wall beside the pans,
    # Blood's stocked shelf (`fixtures.shelf_niche`, E1M2 s213), holding the
    # cook's jars and jugs (`goods.ROWS`).
    import templates
    fixtures.shelf_niche(main, templates._shelf_id(main), "west", width=2048,
                         at=0.5, sells="kitchen")
    # ...and the cold store's: a shelf let into the freezer's north wall,
    # with the station gallery's body of void behind it, holding the kegs
    # and jars a meat store keeps cold (E1M2's locker s268 keeps its stock
    # on the wall the same way).
    fixtures.shelf_niche(back, templates._shelf_id(back), "north", width=2048,
                         at=0.5, sells="cold")
    placed["rooms"] += [main.region_id, back.region_id]

    # The door: z-motion, push-to-use, marquee flicker on its own sector.
    door = canteen.room(
        "door", [(0, 0), (1024, 0), (1024, 256), (0, 256)],
        role="doorway", faces=dict(COMPASS),
        frame=Frame(main_x0 + 3072, main_y1 - 512),
        # (the porch below occupies the outer 256; see the hall's note)
        region_kwargs={
            "type": 600,
            "door_face": DOOR_FACE_TILE,
            "inherit_finish": "both",
            "sector_behavior": {
                **z_motion_door(GRADE, GRADE - CANTEEN_DOOR_H),
                "amplitude": -24, "shade_frequency": 12, "shade_wave": 0,
            },
        },
        note="canteen door: z-motion push door, marquee-flickered mouth",
    )
    door.surfaces(wall_picnum=JAMB_TILE, floor_z=GRADE, clear_height=0)
    canteen.connect(door.face("north"), main.face("south"),
                    connection_id="connection:canteen_door_in")

    # Mediation, as at the market hall: without a door-height porch the
    # engine draws the whole works facade above the door from the door's
    # own tile -- a six-storey wooden slab.
    porch = canteen.room(
        "porch", [(0, 0), (1024, 0), (1024, 256), (0, 256)],
        role="gateway", faces=dict(COMPASS),
        frame=Frame(main_x0 + 3072, main_y1 - 256),
        note="the canteen's reveal: the facade owns the wall above the door",
    )
    porch.surfaces(wall_picnum=MASONRY.wall, ceiling_picnum=MASONRY.wall,
                   floor_z=GRADE, clear_height=CANTEEN_DOOR_H)
    canteen.connect(porch.face("north"), door.face("south"),
                    connection_id="connection:canteen_porch_door")
    city.connect(porch.face("south"), foundry_st.face("west"),
                 connection_id="connection:canteen_door_street")

    # THE HATCH. The second door on the yard is the stand's serving hatch:
    # E1M4's RATDOGS sells through one, at half a body, its grill on the
    # sill. The grill is that stand's sector 167 transcribed: ribbed iron
    # 376 under rusted metal 255, a kSectorDamage (618) that burns
    # (damage_type 1, data 30), and its shade flickering like a fire. It is
    # the wall's thickness deep and a body high, so the yard sees the grill
    # and the room behind it, and nobody walks through.
    hatch = canteen.room(
        "hatch", [(0, 0), (1024, 0), (1024, 512), (0, 512)],
        role="detail", faces=dict(COMPASS),
        frame=Frame(main_x0 + 1024, main_y1 - 512),
        region_kwargs={
            "type": 618,
            "sector_behavior": {
                "data": 30, "damage_type": 1,
                "amplitude": -3, "shade_frequency": 5, "shade_wave": 6,
                "shade_always": 1, "shade_floor": 1, "shade_ceiling": 1,
                "shade_walls": 1,
            },
        },
        note="the RAT DOGS hatch: E1M4 s167's grill at counter height",
    )
    hatch.surfaces(floor_z=GRADE - HATCH_SILL, clear_height=HATCH_CLEAR,
                   floor_picnum=376, ceiling_picnum=255, wall_picnum=20,
                   floor_shade=16, ceiling_shade=40)
    canteen.connect(hatch.face("north"), main.face("south"),
                    connection_id="connection:canteen_hatch_in")
    city.connect(hatch.face("south"), foundry_st.face("west"),
                 connection_id="connection:canteen_hatch_street")

    # (The rail-yard backdrop box that stood here, seen through the back
    # room's high window, is gone: the freezer stands in its place.)

    # ---- yard furniture: the loading dock (street-furniture.md industrial
    # vocabulary; recessed into the works face so it edges the yard rather
    # than adding a walk-around loop -- the conformance check caught the
    # free-standing version breaching the CN loop ceiling) ------------------
    cart_x0 = yard_x0 - 2048
    cart_y0 = yard_y1 - 2048
    cart = city.room(
        # Two bays tall so the dock's mouth lands between the painted
        # windows like every other opening in the city.
        "yard_dock", [(0, 0), (CAGE_DEEP, 0), (CAGE_DEEP, 2048), (0, 2048)],
        role="detail", faces=dict(COMPASS), frame=Frame(cart_x0, cart_y0),
        note="loading bay, level with the yard, recessed in the works face",
    )
    cart.style = Style(**MASONRY.style_kwargs(
        floor_picnum=FACADES["foundry_ward"].floor, floor_shade=36,
        ceiling_picnum=INTERIORS["service"].ceiling,
        parallax_ceiling=False, clear_height=24576))
    # street-furniture measured cart platforms at +6144, but those are
    # scenery; this one is an alcove the player should be able to step into,
    # and 6144 is above the 4096 max step.  A dock at exactly one max step
    # is what a dock is.  (Found by the reachability check, not by eye.)
    # The owner, playing it: "weird low door". It stood a step up and
    # 16,384 high, lower than a body, so it read as a hole in the wall. It
    # is a bay now: level with the yard and a body and a half high.
    cart.surfaces(floor_z=GRADE)
    # THE BAY IS A CAGE. The owner, walking it on 2026-11-20: "that walk-in
    # bay looks like just a random cutoff in the building. You can put there
    # bars or something to add more meaning to it, maybe it can have bloody
    # stuff behind bars". Bars hang on a wall whose two sides stand at one
    # floor and one ceiling, and the yard has the sky over it, so a reveal
    # of the bay's own height stands in the mouth and the bars cross its
    # inner edge. What hangs behind them is in `sprinkle`.
    reveal = city.room(
        "yard_dock_reveal", [(0, 0), (2048 - CAGE_DEEP, 0),
                             (2048 - CAGE_DEEP, 2048), (0, 2048)],
        role="detail", faces=dict(COMPASS),
        frame=Frame(cart_x0 + CAGE_DEEP, cart_y0),
        note="the cage's reveal: the bars stand at its back",
    )
    reveal.style = cart.style
    reveal.surfaces(floor_z=GRADE)
    city.connect(cart.face("east"), reveal.face("west"),
                 connection_id="connection:dock_cage_bars")
    city.connect(reveal.face("east"), foundry_st.face("east"),
                 connection_id="connection:dock_mouth")
    placed["rooms"].append(reveal.region_id)
    CAGE["bars"] = (cart_x0 + CAGE_DEEP - 16, cart_y0 - 16,
                    cart_x0 + CAGE_DEEP + 16, cart_y0 + 2048 + 16)
    placed["rooms"].append(cart.region_id)

    return {"placed": placed, "canteen_door": door.region_id,
            "hatch": hatch.region_id, "counter": counter.region_id,
            "griddle": griddle.region_id,
            "freezer_world": (main_x0, main_y0 - 2048),
            "main_world": (main_x0, main_y0),
            "cart": cart.region_id, "cart_world": (cart_x0, cart_y0),
            "main": main.region_id,
            "back": back.region_id}


def _transcribed(map_name: str, type_id: int, picnum: int, **change) -> dict:
    """A record copied from the campaign, its behavior folded in, then changed."""
    spec = _attested(map_name, type_id, picnum)
    fields = dict(spec["fields"])
    if spec["behavior"]:
        fields["behavior"] = dict(spec["behavior"])
    fields.update(change)
    return fields


def dress_canteen(layout, dressing) -> list[str]:
    """The dine-in, the kitchen wall and the freezer (owner, 2026-11-20).

    Every thing is a record from the campaign room it was studied in
    (`knowledge/blood/studies/canteen-freezer-dining/notes.md`); what is
    ours is where it stands. Records keep their cstat: the layout's wall
    and ceiling placements read the centring bit (128) themselves.
    """
    out = []
    main, back = dressing["main"], dressing["back"]
    mx0, my0 = dressing["main_world"]
    fx0, fy0 = dressing["freezer_world"]

    # The dine-in: E1M2's buffet tables (649, s185), round, on a pedestal,
    # in the hall north of the counter and east of its pass, clear of the
    # way in from the door (south-east) and of the freezer door (north,
    # middle). E1M2 stands three in 39 M; the customers' side here is about
    # 10 M with the stools along the counter, so four.
    for index, local in enumerate(((0.15, 0.2), (0.38, 0.25), (0.86, 0.2),
                                   (0.84, 0.42))):
        layout.place_on_floor(f"canteen:table_{index}", main, local=local,
                              **_transcribed("E1M2", 417, 649))
        out.append(f"canteen:table_{index}")
    # ...and the dining half gets the kitchen's light too: E1M4's tube
    # laid flat on the ceiling, over the tables.
    layout.place_on_ceiling(
        "canteen:tube_dining", main, local=(0.72, 0.4),
        picnum=796, x_repeat=48, y_repeat=32, cstat=416, shade=-8,
        type=0, status=0)
    out.append("canteen:tube_dining")

    # The kitchen wall, beside the counter, as E1M2's kitchen (s257) hangs
    # it: two frying pans (2304, 2305), EMPLOYEES MUST WASH HANDS (1719),
    # and the fire extinguisher (658) further along. It is the west wall,
    # run from the south end (t 0) to the north; the counter stands at t
    # 0.11 to 0.44.
    west = ((mx0, my0 + DINE_DEEP), (mx0, my0))
    for pid, tile, type_id, t, high in (
            ("pan_0", 2304, 417, 0.16, 1.35), ("pan_1", 2305, 417, 0.27, 1.3),
            ("wash_hands", 1719, 417, 0.39, 1.45)):
        layout.place_on_wall(f"canteen:{pid}", main, a1=west[0], a2=west[1],
                             t=t, height_player_heights=high,
                             offset_player_widths=0.04,
                             **_transcribed("E1M2", type_id, tile))
        out.append(f"canteen:{pid}")
    layout.place_on_wall("canteen:extinguisher", main,
                         a1=west[0], a2=west[1], t=0.82,
                         height_player_heights=1.1, offset_player_widths=0.04,
                         **_transcribed("E1M2", 416, 658))
    out.append("canteen:extinguisher")

    # The customers' side of the counter: the saloon's stools (DWE3M1's,
    # 768 apart), a stool's width off the counter's east face; and on the
    # counter, E1M2's cleaver (2139) where its kitchen counter keeps one.
    import l3_theatre
    from fixtures import BAR
    front = mx0 + KITCHEN_W + BAR.depth + 320
    for index, y in enumerate(range(my0 + COUNTER_PASS + 640,
                                    my0 + DINE_DEEP - 512, l3_theatre.STOOL_PITCH)):
        local = ((front - mx0) / 4096, (y - my0) / DINE_DEEP)
        layout.place_on_floor(f"canteen:stool_{index}", main, local=local,
                              height_player_heights=l3_theatre.STOOL_LIFT / 16960.0,
                              **l3_theatre.STOOL)
        out.append(f"canteen:stool_{index}")
    # E1M2 draws it centred (cstat 128) with its centre 2,304 over the
    # counter top (sprite in s153: z -29952 over a floor at -27648), so the
    # blade stands in the wood; so does ours.
    layout.place_on_floor("canteen:cleaver", dressing["counter"], local=(0.5, 0.5),
                          height_player_heights=2304 / 16960,
                          **_transcribed_tile("E1M2", 2139))
    out.append("canteen:cleaver")

    # The freezer: E1M3's carcasses on hooks (1351, one plucked 1350) over
    # its blood pools (1417, 1413, 732), each with the drip generator E1M3
    # hangs in it (type 702, built running: state 1, every 40 ticks). E1M3
    # wires its drips to a channel; these are not on one, and need none.
    for index, (tile, local) in enumerate((
            (1351, (0.22, 0.35)), (1351, (0.42, 0.62)), (1350, (0.6, 0.3)),
            (1351, (0.78, 0.6)))):
        hung = _transcribed("E1M3", 416, tile)
        # Drawn centred and with no hang point in its art (690's has one,
        # 1351's and 1350's do not), so the ceiling seat puts its centre on
        # the ceiling. E1M3 hangs each half its drawn height down (1351:
        # 133 rows at repeat 40, 21,280 tall, centre 10,560 down); so do we.
        half = (133 if tile == 1351 else 54) * int(hung["y_repeat"]) * 2
        layout.place_on_ceiling(f"freezer:carcass_{index}", back, local=local,
                                height_player_heights=half / 16960, **hung)
        layout.place_on_ceiling(
            f"freezer:drip_{index}", back, local=local, picnum=tile,
            x_repeat=40, y_repeat=40, cstat=32768, shade=-8, type=702,
            status=0, behavior={"state": 1, "busy": 65536, "busy_time": 40,
                                "data_1": 15})
        out += [f"freezer:carcass_{index}", f"freezer:drip_{index}"]
    for index, (tile, local) in enumerate((
            (1417, (0.42, 0.62)), (732, (0.14, 0.22)), (1413, (0.78, 0.55)))):
        layout.place_on_floor(f"freezer:blood_{index}", back, local=local,
                              height_player_heights=0.0,
                              **_transcribed_tile("E1M3", tile))
        out.append(f"freezer:blood_{index}")
    # The butcher's tools on the freezer's west wall, as E3M2 hangs them
    # on its meat room's board (s258): the handsaw, the ice tongs, the axe.
    west = ((fx0, fy0 + FREEZER_DEEP), (fx0, fy0))
    for pid, tile, t in (("saw", 1714, 0.3), ("tongs", 1715, 0.5),
                         ("axe", 1709, 0.7)):
        layout.place_on_wall(f"freezer:{pid}", back, a1=west[0], a2=west[1],
                             t=t, height_player_heights=1.2,
                             offset_player_widths=0.04,
                             **_transcribed_tile("E3M2", tile))
        out.append(f"freezer:{pid}")
    return out


def _transcribed_tile(map_name: str, picnum: int) -> dict:
    """A decoration's record by its tile, with its extension when it has one."""
    disk = read_map(corpus_map_path(map_name))
    for sprite in disk.sprites:
        if int(sprite.fields["picnum"]) == picnum:
            fields = {k: int(sprite.fields[k]) for k in
                      ("picnum", "x_repeat", "y_repeat", "cstat", "type", "shade")}
            fields["status"] = 0
            return fields
    raise KeyError(f"{map_name} has no sprite wearing tile {picnum}")


def sprinkle(layout, ctx, dressing) -> list[str]:
    """Post-program placements: population, breakables, lamps, the staged
    moment's wiring.  Runs on the PlanarLayout, before compile."""
    out = []
    yard = ctx["yard_rect_pu"]
    yard_x0, yard_y0, yard_x1, yard_y1 = (int(v * PU) for v in yard)
    street_region = ctx["foundry_st"].region_id

    def world_sprite(pid, region, x, y, spec, **extra_behavior):
        fields = dict(spec["fields"])
        behavior = dict(spec.get("behavior", {}))
        behavior.update(extra_behavior)
        floor_z = layout.regions[region].floor_z
        if behavior:
            fields["behavior"] = behavior
        layout.add_sprite(pid, region, x=int(x), y=int(y),
                          z=int(floor_z), **fields)
        out.append(pid)

    def room_sprite(pid, region, local, spec, **extra_behavior):
        fields = dict(spec["fields"])
        behavior = dict(spec.get("behavior", {}))
        behavior.update(extra_behavior)
        if behavior:
            fields["behavior"] = behavior
        layout.place_on_floor(pid, region, local=local, **fields)
        out.append(pid)

    cultist = _attested("E3M1", 202)
    zombie = _attested("E3M1", 203)
    rat = _attested("E3M3", 220)
    exploder = _attested("E3M1", 459)
    gen_sound = _attested("E3M1", 708)

    # Population at campaign registers: cultists hold the yard, a zombie in
    # the canteen back, rats in the sewer (E3M3: scavengers, no garrison).
    world_sprite("pop:yard_cultist_a", street_region,
                 (yard_x0 + yard_x1) / 2, yard_y0 + 1024, cultist)
    world_sprite("pop:yard_cultist_b", street_region,
                 yard_x1 - 1024, (yard_y0 + yard_y1) / 2, cultist)
    # The freezer's keeper is a butcher: E3M2 works its meat rooms (s258)
    # with the fat zombie (type 204, tile 1370) where this was an axe one.
    butcher = _attested("E3M2", 204)
    room_sprite("pop:canteen_zombie", dressing["back"], (0.35, 0.5), butcher)
    for index, room_key in enumerate(("trunk", "junction", "cistern")):
        room_sprite(f"pop:sewer_rat_{index}", ctx["sewer_rooms"][room_key],
                    (0.3 + 0.2 * index, 0.5), rat)

    # The staged moment (destruction reserve): stepping onto the grate fires
    # the cart's barrels and a sound cue.  tx: the grate sector itself.
    from bloodmap import wiring

    grate_region = ctx["grate_upper"].region_id
    import wires

    # The staged moment is not staged here any more. The owner: "that
    # staged explosion thing with this weird rectangle hole ... looks
    # weird." Its wire stays in the plan, with no ends, until the moment is
    # rebuilt underground (`knowledge/blood/studies/underpass/notes.md`).
    # What lies on the mouth is the campaign's own sewer grate: tile 502,
    # laid as a floor sprite as Blood lays it (49 times in 9 maps).
    from bloodmap import flatsprite
    import wallplane as _art

    for index, piece in enumerate(flatsprite.cover((0, 0, 1024, 1024),
                                                   _art.art()[502][:2])):
        layout.place_on_floor(
            f"yard:grate_{index}", grate_region,
            local=(piece["x"] / 1024, piece["y"] / 1024),
            height_player_heights=0.0, type=0, picnum=502, cstat=32,
            x_repeat=piece["x_repeat"], y_repeat=piece["y_repeat"],
            angle=piece["angle"], shade=20, status=0)
    cart_x0, cart_y0 = dressing["cart_world"]
    # The grate gained a kerb ring (2048 across, centred 1536 east of the
    # yard's west edge), so the charges sit in the strip between the dock
    # mouth and that ring -- still on the approach the trigger watches.
    mouth_x = yard_x0 + 256
    # `rx_id=0`: the specs are copied from E3M1's own records, channel and
    # all; the wire gives each its channel here.
    for index in range(2):
        fields = breakable("barrel")
        behavior = fields.pop("behavior", {})
        spec = {"fields": fields, "behavior": behavior}
        room_sprite(f"prop:cart_barrel_{index}", dressing["cart"],
                    (0.2 + 0.6 * index, 0.2), spec)
    # What the cage holds: the works' meat store. Corpses on chains hang
    # from the ceiling as Blood hangs them (tiles 690 and 698: 24 and 19 in
    # the campaign, each one a record copied from the map named), over a
    # pool of blood (956, which Blood lays as a floor sprite) and its drips.
    for index, (source, tile, local) in enumerate((
            ("E1M2", 690, (0.3, 0.5)), ("E1M3", 698, (0.55, 0.3)),
            ("E1M2", 690, (0.7, 0.72)))):
        hung = dict(_attested_tile(source, tile))
        # The campaign hangs these at repeat 64 in rooms 33,000 to 42,000
        # high; the cage is 24,576, and at that size the lint read a quarter
        # of each as sunk. Blood also hangs them at 48; these are 40, so
        # chain and body fit under the cage's ceiling.
        hung["x_repeat"] = hung["y_repeat"] = 40
        layout.place_on_ceiling(f"cage:corpse_{index}", dressing["cart"],
                                local=local, **hung)
        out.append(f"cage:corpse_{index}")
    import props as _cage_props
    for index, (tile, local) in enumerate(((956, (0.45, 0.5)), (730, (0.7, 0.7)),
                                           (730, (0.3, 0.35)))):
        layout.place_on_floor(f"cage:blood_{index}", dressing["cart"],
                              local=local, **_cage_props.fields(tile))
        out.append(f"cage:blood_{index}")

    # RAT DOGS on the grill, as E1M4 cooks them (its s167): rats lying on
    # the ribs at repeat 24, one of them flipped, steam rising off each, and
    # extractor fans laid flat on the ceiling over them. Every record is
    # that stand's own; only where it lies is ours, and one bit: E1M4 draws
    # them centred on their z (cstat 128) and lifts each half its height,
    # where `place_on_floor` stands a sprite on its feet, so the bit is
    # dropped and the lift with it (the lint read them 46% sunk).
    rat_on_grill = {"picnum": 1743, "x_repeat": 24, "y_repeat": 24,
                    "cstat": 256, "shade": -8, "type": 0, "status": 0}
    steam = {"picnum": 754, "x_repeat": 32, "y_repeat": 8, "cstat": 2,
             "shade": -8, "type": 0, "status": 0}
    fan = {"picnum": 2548, "x_repeat": 32, "y_repeat": 32, "cstat": 160,
           "shade": 0, "type": 0, "status": 0}
    for place, region, spots in (
            ("grill", dressing["hatch"], (0.2, 0.55, 0.82)),
            ("counter", dressing["counter"], (0.3, 0.7)),
            ("griddle", dressing["griddle"], (0.2, 0.5, 0.8))):
        for index, u in enumerate(spots):
            local = (u, 0.5) if place == "grill" else (0.5, u)
            rat = dict(rat_on_grill, picnum=1744 if index == 1 else 1743,
                       cstat=260 if index % 2 else 256)
            layout.place_on_floor(f"ratdogs:{place}_rat_{index}", region,
                                  local=local, **rat)
            layout.place_on_floor(f"ratdogs:{place}_steam_{index}", region,
                                  local=local, height_player_heights=0.1,
                                  **steam)
            out += [f"ratdogs:{place}_rat_{index}", f"ratdogs:{place}_steam_{index}"]
    for index, u in enumerate((0.25, 0.75)):
        layout.place_on_ceiling(f"ratdogs:fan_{index}", dressing["hatch"],
                                local=(u, 0.5), **fan)
        out.append(f"ratdogs:fan_{index}")
    for index, u in enumerate((0.3, 0.7)):
        layout.place_on_ceiling(f"ratdogs:griddle_fan_{index}", dressing["griddle"],
                                local=(0.5, u), **fan)
        out.append(f"ratdogs:griddle_fan_{index}")
    # The kitchen's light is E1M4's: a fluorescent tube laid flat on the
    # ceiling (796, its s170), over the counter.
    layout.place_on_ceiling(
        "ratdogs:tube", dressing["counter"], local=(0.5, 0.5),
        picnum=796, x_repeat=48, y_repeat=32, cstat=416, shade=-8,
        type=0, status=0)
    out.append("ratdogs:tube")

    out += dress_canteen(layout, dressing)

    # Pickups.  The campaign runs 0.9 per dude; we had none, which the
    # discriminator ranked as one of our worst features.  Types and fields
    # are transcribed from E3M1's own placements, not invented.
    for index, (type_id, region, local) in enumerate((
            (65, dressing["main"], (0.95, 0.1)),    # in the corner past the tables
            (62, dressing["back"], (0.5, 0.5)),
            (67, ctx["sewer_rooms"]["junction"], (0.3, 0.4)),
            (60, ctx["sewer_rooms"]["cistern"], (0.5, 0.5)),
            (63, dressing["stash"], (0.5, 0.5)),
            (109, dressing["stash"], (0.35, 0.6)),
    )):
        try:
            spec = _attested("E3M1", type_id)
        except LookupError:
            continue
        room_sprite(f"item:pickup_{index}", region, local, spec)

    # Lamps.  Tile 641 is a hall torch and the campaign mounts it 57k-64k
    # above the floor (73 instances measured); at head height it rendered
    # as a checkered sliver.  3.38 player heights is the campaign's own.
    top_y0 = ctx["stair_top_y0"]
    layout.place_on_wall(
        "lamp:stair_mouth", street_region,
        a1=(yard_x0, top_y0 + 2048), a2=(yard_x0, top_y0),
        #: over the mouth's head (the mouth is 1.45 bodies), not in it
        t=0.5, height_player_heights=1.9, **YARD_LAMP)
    # Beside the door on the pier between it and the hatch, at the pier's
    # edge: centred on the pier it hung across the painted window there.
    layout.place_on_wall(
        "lamp:canteen_door", street_region,
        a1=(yard_x0 + 1024, yard_y0), a2=(yard_x0 + 2048, yard_y0),
        t=0.93, height_player_heights=YARD_LAMP_HEIGHT, **YARD_LAMP)
    out += ["lamp:stair_mouth", "lamp:canteen_door"]

    # RAT DOGS comes out into the yard. The showcase's reader, of the yard
    # (round 2): "the courtyard has little purpose beyond passage ... add a
    # small Rat Dogs outdoor seating area". Two of the dine-in's stand-up
    # tables stand out on the paving, clear of the way to the hatch and of
    # the works wall (the table is 720 across), where a works hand eats what
    # he bought through it.
    table = _transcribed("E1M2", 417, 649)
    for index, (x, y) in enumerate(((yard_x0 + 448, yard_y0 + 2432),
                                    (yard_x0 + 1664, yard_y0 + 2048))):
        layout.add_sprite(f"ratdogs:yard_table_{index}", street_region, x=x, y=y,
                          z=int(layout.regions[street_region].floor_z), **table)
        out.append(f"ratdogs:yard_table_{index}")
    return out
