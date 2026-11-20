"""L3 for the pilot district: Foundry Ward, dressed.

Attached to the L2 skeleton by names and anchors (design-layers.md): the
works canteen venue (venue-patterns `shop`), the yard's furniture
(street-furniture.md industrial vocabulary), the staged destruction moment
on the grate approach (the district's channel reserve), a backdrop window
(backdrop-and-weave.md), population and breakables at campaign registers,
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
from materials import BACKDROP, FACADES, INTERIORS, MASONRY

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
    main = canteen.room(
        "main", [(0, 0), (4096, 0), (4096, 2560), (0, 2560)],
        role="interior", faces=dict(COMPASS),
        frame=Frame(main_x0, main_y1 - 512 - 2560),
        region_kwargs=shop.region_kwargs(),
        note="main room; counter and display are geometry (VP shop)",
        intent={"venue": "works_canteen", "type": "shop"},
    )
    back = canteen.room(
        "back", [(0, 0), (3072, 0), (3072, 2048), (0, 2048)],
        role="interior", faces=dict(COMPASS),
        frame=Frame(main_x0 + 512, main_y1 - 512 - 2560 - 2048),
        region_kwargs=shop.region_kwargs(),
        note="the back room; its high window is the backdrop frame",
    )
    canteen.connect(back.face("south"), main.face("north"),
                    connection_id="connection:canteen_back")

    # Counter: geometry at rise 4096 (VP), an island in the main room.
    main.carve([(512, 512), (1536, 512), (1536, 2048), (512, 2048)])
    counter = canteen.room(
        "counter", [(0, 0), (1024, 0), (1024, 1536), (0, 1536)],
        role="detail", faces=dict(COMPASS),
        frame=Frame(main_x0 + 512, main_y1 - 512 - 2560 + 512),
        note="the counter, rise 4096 (VP shop)",
    )
    counter.surfaces(floor_z=GRADE - 4096, clear_height=28672)
    for face in ("north", "east", "south", "west"):
        canteen.connect(counter.face(face), main.face("north"),
                        connection_id=f"connection:counter_rim_{face}")
    # The serving counter is the cook's: its top is the grill's ribbed iron.
    counter.surfaces(floor_picnum=376, wall_picnum=2453)
    # A table to eat at, where the display pedestal stood: a wooden block
    # at table height, a body's width across and two long.
    main.carve([(2816, 768), (3328, 768), (3328, 1792), (2816, 1792)])
    pedestal = canteen.room(
        "pedestal", [(0, 0), (512, 0), (512, 1024), (0, 1024)],
        role="detail", faces=dict(COMPASS),
        frame=Frame(main_x0 + 2816, main_y1 - 512 - 2560 + 768),
        note="the canteen's table, rise 7168, a wooden top",
    )
    pedestal.surfaces(floor_z=GRADE - 7168, clear_height=25600,
                      floor_picnum=20, wall_picnum=20)
    for face in ("north", "east", "south", "west"):
        canteen.connect(pedestal.face(face), main.face("north"),
                        connection_id=f"connection:pedestal_rim_{face}")
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

    # ---- backdrop window: the rail yard behind the works ------------------
    box = city.room(
        "railyard_scene", [(0, 0), (4096, 0), (4096, 2048), (0, 2048)],
        role="detail", faces=dict(COMPASS),
        frame=Frame(main_x0 + 256, main_y1 - 512 - 2560 - 2048 - 2048),
        note="backdrop-and-weave.md: 12-wall depth behind the canteen "
             "window; sill 8192 keeps it scenery",
    )
    box.style = Style(**BACKDROP.style_kwargs(floor_shade=44,
                                              floor_z=GRADE - 8192,
                                              clear_height=STREET_SKY))
    box.carve([(1024, 512), (2560, 512), (2560, 1024), (1024, 1024)])
    city.connect(back.face("north"), box.face("south"),
                 connection_id="connection:backdrop_window")
    placed["rooms"].append(box.region_id)

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
            "table": pedestal.region_id,
            "cart": cart.region_id, "cart_world": (cart_x0, cart_y0),
            "main": main.region_id,
            "back": back.region_id, "box": box.region_id}


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
    room_sprite("pop:canteen_zombie", dressing["back"], (0.35, 0.5), zombie)
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
            ("counter", dressing["counter"], (0.3, 0.7))):
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
    # The kitchen's light is E1M4's: a fluorescent tube laid flat on the
    # ceiling (796, its s170), over the counter.
    layout.place_on_ceiling(
        "ratdogs:tube", dressing["counter"], local=(0.5, 0.5),
        picnum=796, x_repeat=48, y_repeat=32, cstat=416, shade=-8,
        type=0, status=0)
    out.append("ratdogs:tube")

    # Pickups.  The campaign runs 0.9 per dude; we had none, which the
    # discriminator ranked as one of our worst features.  Types and fields
    # are transcribed from E3M1's own placements, not invented.
    for index, (type_id, region, local) in enumerate((
            (65, dressing["main"], (0.9, 0.3)),     # beside the table
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
    return out
