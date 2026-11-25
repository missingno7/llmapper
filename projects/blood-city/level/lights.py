"""The city's lights: which kind of light each place is lit by, and how far apart. A place not named here is lit by `DEFAULT`, and the build names it.

The owner, 2026-11-20: "you should be using different types of light sources,
check existing levels ... Torches should be used only where it makes sense",
and of the tiles: "501, 2290, 2288, 796 can be used as textures ... rest of
them would be sprite only" (`bloodmap.light_kinds`). Then: "it looks like you
are just scattering stuff on the ceiling" -- so a room is lit in rows along
its long axis, one kind per room (`bloodmap.light_stage.lay_lights`).

To light a new place, add a line: the first key that is a part of the
place's region path wins, so a narrower place goes above the place it is in.
Nothing else is needed; the stage lights the finished map from scratch on
every build.

    form      "none"    the room's own lights only
              "panel"   a recessed ceiling sector of the tile, in whole tiles
              "ceiling" a flat sprite on the ceiling
              "hanging" a sprite on a chain (a round glass lamp where the
                        room is too low for it)
              "pairs"   standing lights in matching pairs along the long walls
    along     spacing along the room's long axis (plan units)
    across    spacing across it (0: one row)
"""

from __future__ import annotations

from bloodmap.light_stage import Rule

#: (part of a region path, its rule). The first match wins.
RULES: tuple[tuple[str, Rule], ...] = (
    # the station's portico: a lamp on its chain in each bay (`l3_station.furnish`)
    ("station_portico", Rule("none", 0, 0, cut=False)),
    ("station_column_", Rule("none", 0, 0, cut=False)),
    ("station_lip", Rule("none", 0, 0, cut=False, shade_bias=(0, 0, -6))),
    # the drowned places' surfaces: a linked sector is never cut
    ("pump_station/tank_0", Rule("none", 0, 0, cut=False)),
    ("trunk/well_", Rule("none", 0, 0, cut=False)),
    # the loading shutter sweeps over it, in plan, two levels up: a cut under the sweep reads as one in its way
    ("trunk/duct_cistern", Rule("ceiling", 796, 7168, 7168, cut=False)),
    ("chambers/flooded_", Rule("none", 0, 0, cut=False)),
    # Graves Brook is older than the ring: lamps hung on chains far apart,
    # not the ring's tubes (`references/sewer-design.md`: "almost none")
    ("graves_brook", Rule("hanging", 641, 8192)),
    ("old_crossing/gallows:dais", Rule("none", 0, 0, cut=False)),    # two shallow steps: a shadow's edge on them reads as a crack
    ("theatre_row/bill_column", Rule("none", 0, 0, cut=False)),
    ("old_crossing/gallows", Rule("none", 0, 0)),         # two lamps, and a candelabrum in the house
    # the Cabal keeps its own fires
    ("settling_hall/rite:tier", Rule("none", 0, 0, cut=False, shade_bias=(14, 26, 12))),
    ("settling_hall/rite:gallery", Rule("none", 0, 0, cut=False, shade_bias=(14, 26, 12))),
    ("settling_hall/rite:sign", Rule("none", 0, 0, cut=False, shade_bias=(14, 26, 12))),
    ("settling_hall/rite:floor", Rule("none", 0, 0, cut=False, shade_bias=(14, 26, 12))),
    ("settling_hall/rite:niche", Rule("none", 0, 0, cut=False, shade_bias=(10, 12, 12))),
    ("settling_hall/rite:gullet", Rule("none", 0, 0)),
    ("settling_hall/rite:heart", Rule("none", 0, 0)),
    ("settling_hall/rite", Rule("none", 0, 0, shade_bias=(14, 26, 12))),
    # the settling hall: chain lamps over the tanks, their chains in the roof
    ("settling_hall", Rule("none", 0, 0)),                # its own (`settling_hall.LAMPS`, `FALL_LIGHTS`)
    # the sewer's secret rooms: nobody keeps a lamp in a hermit's lair or a
    # bricked-up plague pit; the sewer's own dark, and the shade's flicker
    ("sewer/secrets/", Rule("none", 0, 0)),
    # the Weaver's Cellars: nobody lights a spiders' nest; the brook's lamps
    # through the passage, and the dark
    ("sewer/lair/", Rule("none", 0, 0)),
    ("stockyard_drain", Rule("panel", 501, 5632)),
    ("stockyard_head", Rule("panel", 501, 5632)),
    ("stockyard_floor", Rule("panel", 501, 2560)),
    # the Toshers' Den: its own lantern and stove
    ("toshers_den", Rule("none", 0, 0)),
    ("rat_king_", Rule("none", 0, 0)),
    ("track_coach:", Rule("none", 0, 0)),
    ("fallen_roof_wreck:", Rule("none", 0, 0)),
    ("ghost_station/watch_", Rule("none", 0, 0)),
    ("ghost_station/drowned", Rule("none", 0, 0, shade_bias=(3, 2, 2))),
    ("ghost_station/fallen_roof", Rule("none", 0, 0, shade_bias=(3, 2, 2))),
    ("ghost_station/siding", Rule("none", 0, 0, shade_bias=(6, 5, 5))),
    ("ghost_station", Rule("none", 0, 0, shade_bias=(15, 14, 12))),             # its own lamps, and what switches them (`phantom_terminus.light_groups`)
    ("ghost_service_stair", Rule("none", 0, 0)),
    ("sewer/", Rule("panel", 796, 7168, 7168)),          # pools with darkness between
    # its own: the hood's strip over the key, the consoles' strip, the lever's lamp
    ("pump_station/machine_hall", Rule("none", 0, 0)),
    ("pump_station/deck", Rule("none", 0, 0)),
    ("pump_station", Rule("panel", 501, 3072, 3072)),
    ("works_stair/underpass", Rule("none", 0, 0, cut=False)),          # its own tubes (`underpass.TUBES`), a bay to a light
    ("works_stair", Rule("none", 0, 0)),
    ("yard_dock", Rule("panel", 501, 3072, 3072)),
    ("gravesend_station/tunnel_1", Rule("none", 0, 0)),
    ("gravesend_station/tunnel", Rule("panel", 796, 4096, 4096)),
    # its own lamps and its glass roof (`booking_hall.LAMPS`, `GLOBES`)
    ("gravesend_station/booking_hall", Rule("none", 0, 0, cut=False)),
    ("gravesend_station/hearth", Rule("none", 0, 0)),
    ("gravesend_station/signal_box", Rule("ceiling", 795, 2560, 2560)),
    ("gravesend_station", Rule("panel", 2290, 3072, 3072)),
    ("market_hall/cold_store", Rule("ceiling", 796, 4096, 4096)),
    ("market_hall", Rule("panel", 2290, 3072, 3072)),
    ("gravesend_arcade/hall:rim", Rule("none", 0, 0, shade_bias=(-10, 0, -8))),
    ("gravesend_arcade/hall:water", Rule("none", 0, 0, shade_bias=(-10, 0, -8))),
    ("gravesend_arcade/hall:lantern", Rule("none", 0, 0, shade_bias=(-10, 0, -8))),
    ("gravesend_arcade/hall", Rule("none", 0, 0)),        # the moon through its lantern, its shops' own lamps (`arcade.LAMPS`)
    ("gravesend_arcade", Rule("panel", 2290, 3072, 3072)),
    ("station_arch", Rule("ceiling", 795, 2560, 2560)),
    ("pawn_shop", Rule("panel", 2290, 3072, 3072)),
    ("canteen", Rule("ceiling", 795, 2560, 2560)),
    ("aldermack/backstage", Rule("none", 0, 0)),
    ("aldermack/dressing", Rule("none", 0, 0)),
    ("aldermack/fire_", Rule("none", 0, 0)),
    ("theatre_row/saloon", Rule("hanging", 641, 3072, 3072)),
    ("theatre_row/aldermack/foyer", Rule("none", 0, 0)),
    ("theatre_row/aldermack/front_", Rule("none", 0, 0)),
    ("theatre_row/aldermack/lobby", Rule("none", 0, 0)),
    ("theatre_row/aldermack/porch", Rule("none", 0, 0)),
    # Keep the chandelier and sconce pools against the dark red and black house.
    ("aldermack/house/", Rule("none", 0, 0, shade_bias=(19, 18, 15))),
    ("theatre_row", Rule("ceiling", 676, 2560, 2560)),
    # its own two candelabra and its stained glass (`light_kinds`: glass on a
    # roofed wall lets daylight in); the pairs the stage stood along the nave
    # blocked the views (the owner, 2026-11-21)
    ("st_gallows", Rule("none", 0, 0)),
)
#: places whose light their own module sets, from a study: the stage leaves
#: them as they are (not cut, not lit in rows, their shades not written). The
#: harbour: its water is dark (38 and more) because two blind readers took it
#: for grass, and its deck, jetty and crates are one sector each. Remove a line
#: to have the stage light the place like any other. (St Gallow's was here
#: until the owner, 2026-11-21: "We can make it lit by model, the stained
#: glass should be giving some light in".)
OWN_LIGHT: tuple[str, ...] = (
    # full of water: what little light each has is its own (`underwater`)
    "gravesend/drowned/",
    # The lit case at the underpass's end: a light in itself.
    "works_stair/underpass:lightbox",
    # The dark the line goes into, past the station's tunnel gate.
    "gravesend_station/tunnel_1",
    # The narrow sash and box carry the poster pane and its measured contrast.
    "theatre_row/aldermack/bill_",
    "market_slip/quay",
    # Hand-painted pools at the work lights and mirrors, and in the swept bay.
    "aldermack/backstage",
    "aldermack/dressing",
    "aldermack/fire_",
    # Preserve the frame, the shade wave and the fin's untouched bay.
    "aldermack/house/stage",
    "aldermack/house/backcloth",
    "aldermack/house/main_curtain",
    "aldermack/house/box_curtain",
    "aldermack/house/light_slit",
    "aldermack/house/terrace",
    "aldermack/house/west_aisle_step",
    "aldermack/house/east_aisle_step",
    "aldermack/house/pelmet",
    "aldermack/house/apron",
    "aldermack/house/west_drape",
    "aldermack/house/east_drape",
    # The deck's hole moves through the rail bed. Keep its lighting in
    # the authored sectors so the band cutter leaves the sweep clear.
    "sewer/sampling/trolley_track",
    # the key's stone, full in the shaft's light
    "lair/pit:stone",
    # E1M1's crypt, field for field (`l3_church`): dark (floor 34, ceiling
    # 28) and flickering; lit by the model its two torches made it shade 0
    "st_gallows/crypt",
)
#: how strong a place's lamps are, against the model's 1 (the first match
#: wins). The owner, 2026-11-21, of St Gallow's lit by the model: "it looks
#: little bit too much light for the church".
LAMP_SCALE: tuple[tuple[str, float], ...] = (
    ("toshers_den", 2.2),
    ("lair/pit:stone", 3.0),
    # a few tubes in a long passage: at full strength every bay was as light as the next
    ("works_stair/underpass:end", 1.0),
    ("works_stair/underpass", 0.5),
    ("pump_station/belt", 2.4),
    ("pump_station/consoles", 1.8),
    ("pump_station/machine_hall", 1.6),
    # six fires in one round room at full strength lit all of it alike, and
    # their death changed nothing (round 1's readers: "floodlit")
    ("settling_hall/rite:gullet", 1.0),
    ("settling_hall/rite:heart", 1.0),
    ("settling_hall/rite", 0.5),
    ("settling_hall", 1.4),
    # the one thing that glows in a station struck off the line
    ("track_coach:", 1.5),
    ("fallen_roof_wreck:", 1.6),
    ("ghost_station/watch_", 1.6),
    ("ghost_station/", 0.7),
    ("theatre_row/aldermack/foyer", 0.55),
    ("theatre_row/aldermack/front_", 0.55),
    ("theatre_row/aldermack/lobby", 0.55),
    ("st_gallows", 0.5),
    ("market_hall/cold_store", 0.4),
    ("market_hall/supermarket", 0.7),
    ("aldermack/backstage", 0.45),
    ("aldermack/dressing", 0.35),
    ("aldermack/house/", 0.42),
    # the lair's two torches at full strength over the sewer's dark: their
    # light falls off steeply enough for the light stage to cut pools in
    # the hall's floor; at 0.35 there was no change to cut and the hall
    # was one even grey (round 5: "the torches throw no pools")
)
#: a room no rule names: a round light flat on the ceiling
DEFAULT = Rule("ceiling", 795, 2560, 2560)


def rule_for(region: str) -> Rule:
    return next((rule for key, rule in RULES if key in region), DEFAULT)


def room_key(region: str) -> str:
    """The room a region is lit as: a sewer corridor's walks, fords and channel are one room."""
    import l3_sewer
    # the settling hall's tanks, walks and quays are one hall
    marker = "/" + l3_sewer.HALL_LAYER + "/"
    if marker in region:
        # the Cabal's chamber behind it is lit by its own fires
        if "/settling_hall/rite:" in region:
            return region[: region.index("rite:") + 4]
        return region[: region.index(marker) + len(marker) - 1]
    tail = region.rsplit("/", 1)[-1]
    for hall in ("stockyard_floor:", "toshers_den/den:"):          # one room, of many cells
        if hall in region:
            return region[: region.index(hall) + len(hall) - 1]
    corridor = _CORRIDOR_OF.get(tail)
    if corridor is None:
        _CORRIDOR_OF.update({e["name"]: e["corridor"] for e in l3_sewer.plan() if e.get("corridor")})
        corridor = _CORRIDOR_OF.get(tail)
    return region[: -len(tail)] + corridor if corridor else region


_CORRIDOR_OF: dict[str, str] = {}


def lamp_scale(region: str) -> float:
    return next((value for key, value in LAMP_SCALE if key in region), 1.0)


def own_light(region: str) -> bool:
    return any(key in region for key in OWN_LIGHT)


def unnamed(rooms) -> list[str]:
    """The rooms lit by DEFAULT because no rule names them."""
    return sorted(r for r in rooms if not any(key in r for key, _ in RULES))
