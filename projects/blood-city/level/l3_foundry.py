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
JAMB_TILE = 170

#: Lamp sconce, campaign modal form (decoration registry tile 641).
LAMP_TILE = 641
LAMP_FIELDS = {"picnum": 641, "x_repeat": 64, "y_repeat": 64, "cstat": 129,
               "shade": -128, "type": 0}

#: The district's channel allocation starts here (CN 8; city_plan CHANNELS).
CH_STAGED_MOMENT = 30


@functools.lru_cache(maxsize=None)
def _attested(map_name: str, type_id: int, picnum: int | None = None) -> dict:
    """Sprite fields + behavior for a type, transcribed from a campaign map.

    `picnum` narrows the match: decorations all carry type 0, so a fire is
    identified by the tile the campaign draws it with.
    """
    disk = read_map(f"maps/blood/{map_name}.MAP")
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

    # ---- the works canteen (VP shop, scaled) ------------------------------
    shop = INTERIORS["shop"]
    canteen = city.assembly(
        "canteen",
        # The campaign's median room is one wall-texture repeat tall
        # (33,280); ours were 20,480 and the discriminator saw it.
        style=Style(**shop.style_kwargs(floor_shade=36, floor_z=GRADE,
                                        clear_height=32768)),
        note="the works canteen: VP shop anatomy behind a z-motion door",
    )
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
    # Display pedestal: 512 square at rise 2048 (E6M1 module).
    main.carve([(2816, 1024), (3328, 1024), (3328, 1536), (2816, 1536)])
    pedestal = canteen.room(
        "pedestal", [(0, 0), (512, 0), (512, 512), (0, 512)],
        role="detail", faces=dict(COMPASS),
        frame=Frame(main_x0 + 2816, main_y1 - 512 - 2560 + 1024),
        note="display pedestal, rise 2048 (E6M1)",
    )
    pedestal.surfaces(floor_z=GRADE - 2048, clear_height=30720)
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
                **z_motion_door(GRADE, GRADE - 16384),
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
                   floor_z=GRADE, clear_height=16384)
    canteen.connect(porch.face("north"), door.face("south"),
                    connection_id="connection:canteen_porch_door")
    city.connect(porch.face("south"), foundry_st.face("west"),
                 connection_id="connection:canteen_door_street")

    # A second mouth on the yard: one-door venues are why our dead-end
    # fraction sits at 0.33 against the campaign's 0.16.
    side_door = canteen.room(
        "side_door", [(0, 0), (1024, 0), (1024, 256), (0, 256)],
        role="doorway", faces=dict(COMPASS),
        frame=Frame(main_x0 + 1024, main_y1 - 512),
        region_kwargs={
            "type": 600,
            "door_face": DOOR_FACE_TILE,
            "inherit_finish": "both",
            "sector_behavior": z_motion_door(GRADE, GRADE - 16384),
        },
        note="the canteen's second mouth, west end of the yard face",
    )
    side_door.surfaces(wall_picnum=JAMB_TILE, floor_z=GRADE, clear_height=0)
    canteen.connect(side_door.face("north"), main.face("south"),
                    connection_id="connection:canteen_side_in")
    side_porch = canteen.room(
        "side_porch", [(0, 0), (1024, 0), (1024, 256), (0, 256)],
        role="gateway", faces=dict(COMPASS),
        frame=Frame(main_x0 + 1024, main_y1 - 256),
        note="the second mouth's reveal",
    )
    side_porch.surfaces(wall_picnum=MASONRY.wall, ceiling_picnum=MASONRY.wall,
                        floor_z=GRADE, clear_height=16384)
    canteen.connect(side_porch.face("north"), side_door.face("south"),
                    connection_id="connection:canteen_side_porch")
    city.connect(side_porch.face("south"), foundry_st.face("west"),
                 connection_id="connection:canteen_side_street")

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
        "yard_dock", [(0, 0), (2048, 0), (2048, 2048), (0, 2048)],
        role="detail", faces=dict(COMPASS), frame=Frame(cart_x0, cart_y0),
        note="loading dock, rise 6144, recessed in the works face",
    )
    cart.style = Style(**MASONRY.style_kwargs(
        floor_picnum=FACADES["foundry_ward"].floor, floor_shade=36,
        ceiling_picnum=INTERIORS["service"].ceiling,
        parallax_ceiling=False, clear_height=16384))
    # street-furniture measured cart platforms at +6144, but those are
    # scenery; this one is an alcove the player should be able to step into,
    # and 6144 is above the 4096 max step.  A dock at exactly one max step
    # is what a dock is.  (Found by the reachability check, not by eye.)
    cart.surfaces(floor_z=GRADE - 4096)
    city.connect(cart.face("east"), foundry_st.face("east"),
                 connection_id="connection:dock_mouth")
    placed["rooms"].append(cart.region_id)

    return {"placed": placed, "canteen_door": door.region_id,
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
    grate_region = ctx["grate_upper"].region_id
    layout.regions[grate_region].sector_behavior.update({
        "tx_id": CH_STAGED_MOMENT, "trigger_enter": 1, "trigger_once": 1,
        "command": 1,
    })
    cart_x0, cart_y0 = dressing["cart_world"]
    # The grate gained a kerb ring (2048 across, centred 1536 east of the
    # yard's west edge), so the charges sit in the strip between the dock
    # mouth and that ring -- still on the approach the trigger watches.
    mouth_x = yard_x0 + 256
    world_sprite("moment:exploder_a", street_region,
                 mouth_x, cart_y0 + 256, exploder,
                 **{"rx_id": CH_STAGED_MOMENT})
    world_sprite("moment:exploder_b", street_region,
                 mouth_x, cart_y0 + 1024, exploder,
                 **{"rx_id": CH_STAGED_MOMENT})
    world_sprite("moment:boom_sound", street_region,
                 mouth_x, cart_y0 + 640, gen_sound,
                 **{"rx_id": CH_STAGED_MOMENT})
    for index in range(2):
        fields = breakable("barrel")
        behavior = fields.pop("behavior", {})
        spec = {"fields": fields, "behavior": behavior}
        room_sprite(f"prop:cart_barrel_{index}", dressing["cart"],
                    (0.3 + 0.4 * index, 0.5), spec)

    # Pickups.  The campaign runs 0.9 per dude; we had none, which the
    # discriminator ranked as one of our worst features.  Types and fields
    # are transcribed from E3M1's own placements, not invented.
    for index, (type_id, region, local) in enumerate((
            (65, dressing["main"], (0.75, 0.35)),
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
        t=0.5, height_player_heights=3.38, **LAMP_FIELDS)
    door_region = dressing["canteen_door"]
    layout.place_on_wall(
        "lamp:canteen_door", street_region,
        a1=(yard_x0 + 1536, yard_y0), a2=(yard_x0 + 3072, yard_y0),
        t=0.15, height_player_heights=3.38, **LAMP_FIELDS)
    out += ["lamp:stair_mouth", "lamp:canteen_door"]
    return out
