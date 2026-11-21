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

    form      "panel"   a recessed ceiling sector of the tile, in whole tiles
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
)
#: places whose light their own module sets, from a study: the stage leaves
#: them as they are (not cut, not lit in rows, their shades not written). The
#: harbour: its water is dark (38 and more) because two blind readers took it
#: for grass, and its deck, jetty and crates are one sector each. St Gallow's:
#: lit from the floor toward the altar, by its own two candelabra, after the
#: church study found every surface at shade 32. Remove a line to have the
#: stage light the place like any other.
OWN_LIGHT: tuple[str, ...] = (
    "market_slip/quay",
    "st_gallows",
)
#: a room no rule names: a round light flat on the ceiling
DEFAULT = Rule("ceiling", 795, 2560, 2560)


def rule_for(region: str) -> Rule:
    return next((rule for key, rule in RULES if key in region), DEFAULT)


def own_light(region: str) -> bool:
    return any(key in region for key in OWN_LIGHT)


def unnamed(rooms) -> list[str]:
    """The rooms lit by DEFAULT because no rule names them."""
    return sorted(r for r in rooms if not any(key in r for key, _ in RULES))
