"""How big things are, in Blood, and in a body's own units.

The owner, 2026-11-18: "There is some general issue in feeling size of
things and space, crypt feels tiny, crypt elevator is just for a player
to stand, but there is really no negative space. That hole that get blown
into sewers is just a narrow strip instead of looking like a actual hole.
Similar things are in pump station, it looks quite good, but it feels like
a miniature. We should do something to really have sense of space volume".

Every one of those was laid out in "plan units" of 1,024, and 1,024 is
1.7 metres. A player is 1,060 units tall (16,960 in z) and 384 wide. The
crypt was 2.6 m by 5.6 m under a 2.6 m ceiling; its lift 0.87 m square;
the blown hole 0.87 m wide.

The numbers below are measured over the campaign (`tools.place_character`
holds the rooms; lifts and blast holes are from the same sweep, 434 and
177 of them, which is not kept: the 96 holes kept in
knowledge/blood/findings/probes/sewer-study_breach_shapes.json give a
median (1664, 1.57) and upper quartile (2208, 1.95)). Lay a thing out FROM these, then let the build's character
sheet say whether the place came out cramped.

The convention: state a size in bodies or metres first (`bodies`,
`metres_to_units`), and never pick a width because it is one plan unit.
"""

from __future__ import annotations

BODY_Z = 16960                 # a standing player, in z units
BODY_XY = 1060                 # the same height in plan units
BODY_WIDE = 384                # the player's clip box across
UNITS_PER_METRE = BODY_XY / 1.8

#: lift platforms: (short side, long side) at the median and upper quartile
LIFT_MEDIAN, LIFT_LARGE = (600, 1408), (1536, 2048)
#: blast holes (a shut Z-motion sector opened in a tenth by an explosion):
#: width along the wall, and the opening in bodies. Gravesend's sizes, from a
#: sweep of 177 holes that was not kept; the 96 kept holes give a median
#: (1664, 1.57) and an upper quartile (2208, 1.95)
#: (knowledge/blood/findings/probes/audit2_blast_holes.py). Kept as the city's.
HOLE_MEDIAN, HOLE_LARGE = (1280, 1.45), (1792, 1.81)
#: indoor rooms: height in bodies (median, upper quartile)
ROOM_HEIGHT = (1.93, 3.38)
#: a hall (area 40M and over): short side and height, medians
HALL_SHORT_SIDE, HALL_HEIGHT = 11776, 3.62
#: the least an aisle may be for a body to pass with room either side
AISLE = 1024


def bodies(count: float) -> int:
    """A height, given in bodies, as z units (to the engine's 256 grid)."""
    return int(round(count * BODY_Z / 256.0)) * 256


def metres_to_units(m: float) -> int:
    return int(round(m * UNITS_PER_METRE / 64.0)) * 64


def metres(units: float) -> float:
    return round(units / UNITS_PER_METRE, 1)
