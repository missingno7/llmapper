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
    # Graves Brook is older than the ring: lamps hung on chains far apart,
    # not the ring's tubes (`references/sewer-design.md`: "almost none")
    ("graves_brook", Rule("hanging", 641, 8192)),
    # the settling hall: chain lamps over the tanks, their chains in the roof
    ("settling_hall", Rule("hanging", 641, 4096, 4096)),
    # the sewer's secret rooms: nobody keeps a lamp in a hermit's lair or a
    # bricked-up plague pit; the sewer's own dark, and the shade's flicker
    ("sewer/secrets/", Rule("none", 0, 0)),
    # the Weaver's Cellars: nobody lights a spiders' nest; the brook's lamps
    # through the passage, and the dark
    ("sewer/lair/", Rule("none", 0, 0)),
    ("stockyard_drain", Rule("panel", 501, 5632)),
    ("stockyard_rack", Rule("panel", 501, 4096)),
    ("rat_king_", Rule("none", 0, 0)),
    ("sewer/", Rule("panel", 796, 7168, 7168)),          # pools with darkness between
    ("pump_station", Rule("panel", 501, 3072, 3072)),
    ("works_stair", Rule("ceiling", 795, 2560, 2560)),
    ("yard_dock", Rule("panel", 501, 3072, 3072)),
    ("gravesend_station/tunnel", Rule("panel", 796, 4096, 4096)),
    ("gravesend_station/goods_store", Rule("panel", 501, 3072, 3072)),
    ("gravesend_station/signal_box", Rule("ceiling", 795, 2560, 2560)),
    ("gravesend_station", Rule("panel", 2290, 3072, 3072)),
    ("market_hall", Rule("panel", 2290, 3072, 3072)),
    ("gravesend_arcade", Rule("panel", 2290, 3072, 3072)),
    ("station_arch", Rule("ceiling", 795, 2560, 2560)),
    ("pawn_shop", Rule("panel", 2290, 3072, 3072)),
    ("canteen", Rule("ceiling", 795, 2560, 2560)),
    ("theatre_row/saloon", Rule("hanging", 641, 3072, 3072)),
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
    "market_slip/quay",
    # E1M1's crypt, field for field (`l3_church`): dark (floor 34, ceiling
    # 28) and flickering; lit by the model its two torches made it shade 0
    "st_gallows/crypt",
)
#: how strong a place's lamps are, against the model's 1 (the first match
#: wins). The owner, 2026-11-21, of St Gallow's lit by the model: "it looks
#: little bit too much light for the church".
LAMP_SCALE: tuple[tuple[str, float], ...] = (
    ("st_gallows", 0.5),
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
        return region[: region.index(marker) + len(marker) - 1]
    tail = region.rsplit("/", 1)[-1]
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
