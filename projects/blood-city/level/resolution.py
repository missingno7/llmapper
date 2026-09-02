"""L2 resolution facts: how the schematic plan's classes become Build units.

This is the only place the mapping lives. L1 (city_plan.py) speaks in width
classes and plan units; the skeleton generator and the contract checker both
read this table, so the plan and its verification cannot disagree about what
a class means. Every value cites its contract (CN = city-norms.md,
SP = sewer-patterns.md).
"""

from bloodmap.player_space import PLAYER_PROFILES

PROFILE = PLAYER_PROFILES["blood"]
STANDING = PROFILE.standing_height          # 16960 z (the corrected body)
EYE = PROFILE.eye_height                    # 14112 z above the floor

#: Plotting and generation convention: one plan unit.
PU = 1024

#: Width classes -> Build units (CN 1: DukCity street median 5120, Blood
#: town mains 6144..7552, alleys p10 1024..2048, lanes read as minor streets).
WIDTH_UNITS = {
    "alley": 2048,
    "lane": 3072,
    "street": 5120,
    "row": 6144,
    "avenue": 7168,
}

#: One 128px wall tile at y_repeat 8: the vertical grid Blood builds on.
TEXTURE_REPEAT = 32768

GRADE = 8192
#: Street sky at six repeats: avenue canyon (196608/16)/7168 = 1.71 (CN 1).
STREET_SKY = 6 * TEXTURE_REPEAT

#: Sewer, under-city form: the network shares Foundry Ward's XY footprint
#: and sits 53248 z below grade = 3.13 standing (SP band 2.5..4).  The yard
#: grate and the old works pit retain their ROR links, while the pump station
#: provides the ordinary walkable route with a physical spiral stair.
CELLAR_DROP = 11 * 4096                     # 45056: the walkable flights
CELLAR_FLOOR = GRADE + CELLAR_DROP          # 53248, also the pit link plane
SEWER_FLOOR = CELLAR_FLOOR + 8192           # 61440
#: Tunnel headroom, and a correction from E3M3 itself.  20,480 everywhere
#: was 1.2 player heights of flat ceiling over every run and chamber, and
#: the frames show what that costs: the sewer's sectors are the level's
#: worst on `visual.composition.ceiling` at 0.35-0.40 of the frame, against
#: a campaign median of 0.025 and E3M3's own 0.042.
#:
#: E3M3's sector heights: median **28,672**, q1 16,384, q3 32,768.  So the
#: number was low, and -- just as telling -- it was a single number, where
#: Blood's own sewer varies its headroom by a factor of two.
SEWER_CLEAR = 24576         # the runs: between E3M3's q1 and its median
SEWER_CHAMBER_CLEAR = 32768  # the rooms: E3M3's q3
# The pump-station cellar starts its real spiral descent at this plane.
STATION_STACK_PLANE = GRADE + 8 * 4096     # 40,960
STATION_STACK_LANDING_DEPTH = SEWER_FLOOR - STATION_STACK_PLANE  # 20,480
#: Stack-link mouths: the pit's landing floor sits deep enough that a
#: standing body's centre stays below the link plane (no warp ping-pong:
#: centre is 8480 above the feet), and shallow enough to jump back out.
PIT_LANDING_DEPTH = 10240
#: Stack mouths are aligned vertically: their source sectors share XY.
#: Kept as a named vector because `build_stack_link` accepts arbitrary links.
SEWER_CITY_D = (0, 0)

#: Materials now live in level/materials.py, named by role.  This module
#: keeps only the compatibility aliases the older call sites use.
from materials import (  # noqa: E402
    BACKDROP, FACADES, HOARDING, INTERIORS, MASONRY, ROADWAY, SEWER,
    SEWER_WET, SKY, BOARDWALK,
)

SKY_TILE = SKY
FLOOR_BOARDWALK = BOARDWALK
FLOOR_GROUND = ROADWAY

#: District style, derived from the facade materials (one place, one rule).
DISTRICT_STYLE = {
    name: {"floor_picnum": mat.floor, "wall_picnum": mat.wall,
           "floor_shade": shade}
    for (name, mat), shade in zip(FACADES.items(), (30, 34, 32, 36))
}


# --- the sun: one direction for the whole level ---------------------------
#
# THE CONVENTION, stated once because the owner asked for it once.
#
# `SUN_BEARING` is a BUILD ANGLE: 0..2047, zero along +x, increasing the way
# `sprite.ang` does. It is the direction a shadow is cast TOWARDS -- the
# direction light travels in plan -- so a mass at (x, y) throws its shadow to
# (x + L*cos, y + L*sin).
#
# The number is measured, not chosen. E3M1's road is cut at its shadow edges,
# and those edges run along the sun's azimuth: of its 112 shade boundaries
# inside the street surface, 60 are axis-aligned (sector edges) and 20 are
# oblique, and the oblique ones cluster hard -- 52.1, 71.1, 78.7, 82.9, 83.8,
# 84.2 degrees, median 84.0. The 84.2 cluster is the largest and is the
# brief's "416 over 4096" read off the geometry: atan2(4096, 416) = 84.2.
#
# 84.0 degrees in Build units is 84.0 * 2048 / 360 = 478.
SUN_BEARING = 478
SUN_BEARING_DEGREES = 84.0
#: How far a shadow edge may sit from the sun's bearing and still be this
#: sun's. E3M1's own oblique edges spread 52..84, so the tolerance is what
#: separates "cast by the sun" from "a sector boundary that happens to be
#: diagonal", and it is generous on purpose.
SUN_BEARING_TOLERANCE_DEGREES = 6.0

#: How long a shadow is, per unit of mass height. Blood has no real sun
#: elevation; what E3M1 has is shadows about as long as its masses are tall,
#: so the elevation convention is 45 degrees and the shadow length equals the
#: height above the ground plane. Stated as a ratio so it is one number to
#: change if the corpus ever says otherwise.
SUN_SHADOW_PER_HEIGHT = 1.0

#: The shade palette, measured over E3M1's 68 street sectors: 8 on nine of
#: them (lit), 34 on seventeen and 32 on three (shadow), 24 on seven
#: (penumbra). 44 appears on thirteen, which is the quay and the far bank --
#: outside the lit street, and not part of this palette.
SHADE_LIT = 8
SHADE_SHADOW = 34
SHADE_PENUMBRA = 24
