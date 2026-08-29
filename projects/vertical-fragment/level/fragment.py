"""The Malt Cross: a brewery yard with a cellar under it and lofts over it.

A vertical fragment, built to force the toolkit to stack space rather than to be
a good level on its own -- though it has to be worth walking through, because a
technically perfect fragment nobody wants to walk through has not proved the
thing it exists to prove.

Three walkable levels inside one plan:

    upper       -32768   the malt loft, the kiln loft, the store roof
    street        8192   the yard, three ground floors
    undercroft   49152   the malt cellar, under the yard

Bands, slab and floor-to-floor are BB4's, unchanged: 32,768 z of clear height
per layer (1.93 standing bodies), 8,192 of slab between them (0.48), 40,960
floor to floor (2.41). BB4 is 71 sectors carrying 68 plan overlaps and not one
z-clash, which is the map this one is trying to be. See
``projects/vertical-fragment/design/layer-conditions.md`` and
``knowledge/blood/design/layers-v1.json``.

All three of Build's ways round one-floor-per-sector appear, each where it is
the only one that works:

* **plan overlap** wherever a storey stands over a storey, because both are
  enclosed and the slab between them is real masonry.
* **room-over-room** for the hatch in the yard down into the cellar, because the
  player has to *see* the cellar through the yard floor before they drop into
  it, and a mirror-tiled link is the only thing that draws the other side.
* **a blocking floor-aligned sprite deck** for the gantry across the yard,
  because a sector built out over the yard would share ground with an open
  volume that reaches from the cobbles to the sky, and nothing in z could
  separate them. This is not a stylistic choice. It is why the campaign puts a
  sprite deck on 86% of its maps.

Walls are 512 units thick, the campaign's own commonest value by a factor of
three (``knowledge/blood/design/wall-thickness-v1.json``: 31,593 of 48,019
probes; median 544). Thickness is not decoration here -- two same-layer rooms
that merely share an edge must be joined or the level is refused, so a wall with
depth is what lets a building have an outside.

Every literal coordinate below is recorded in
``../reports/literal-coordinates.md``. That list is the specification for the
intent resolver this pilot deliberately did not build.
"""

from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from bloodmap import layers, surfaces
from bloodmap.levelprog import LevelProgram, Style
from bloodmap.prefab import sprite_bridge
from bloodmap.roomoverroom import room_over_room
from bloodmap.spiral import CLEAR_HEIGHT as TOWER_CLEAR, spiral_stair
from bloodmap.surfaces import MATERIALS

# ---------------------------------------------------------------------------
# the units, and the numbers derived from them
# ---------------------------------------------------------------------------

#: One body width, and one standing Blood human.
U = 384
PH = layers.STANDING_HEIGHT

#: BB4's vertical grammar, taken whole.
CLEAR = 32768                 # 1.93 bodies of headroom per layer
SLAB = 8192                   # 0.48 bodies of masonry between layers
STOREY = CLEAR + SLAB         # 40960, 2.41 bodies floor to floor

STREET_FLOOR = 8192
UPPER_FLOOR = STREET_FLOOR - STOREY          # -32768
UNDERCROFT_FLOOR = STREET_FLOOR + STOREY     # 49152

#: The sky stands a storey above the highest roof, so the buildings read as
#: buildings rather than as walls that stop.
SKY_Z = UPPER_FLOOR - STOREY - CLEAR         # -106496

BANDS = {
    "upper": (UPPER_FLOOR - CLEAR, UPPER_FLOOR),
    "street": (STREET_FLOOR - CLEAR, STREET_FLOOR),
    "undercroft": (UNDERCROFT_FLOOR - CLEAR, UNDERCROFT_FLOOR),
}

#: The campaign's commonest wall thickness.
WALL = 512

#: A stair carries one storey in equal steps of 4096 -- the player's maximum
#: step, and the corpus's commonest rise by two to one. Everything about the
#: stairwell follows from that rather than being drawn.
STEP_RISE = 4096
STEP_COUNT = STOREY // STEP_RISE             # 10
#: A slightly steep tread, and deliberately so: the run has to fit beside an
#: upper storey that is *inset* from the one below it, and a body width per tread
#: does not leave the room.
TREAD = 320
STAIR_RUN = STEP_COUNT * TREAD               # 3200
STAIR_WIDTH = 1024                           # 2.67 bodies across
#: The head landing has to be as deep as the doorway that reaches it across the
#: inset, so it is not the same size as the foot landing.
LANDING = 768
LANDING_FOOT = 640

#: How far an upper storey is set in from the one under it.
#:
#: Not decoration. Two storeys with one outline give every wall of the lower a
#: twin in the upper, and `wallfront` (build/src/engine.cpp:2227) is a 2D test:
#: for two walls on one line it returns -1 and the bunch sort at engine.cpp:9739
#: answers that with `continue`, so the pair is never ordered and which is drawn
#: first is an artifact of wall order. From most of the yard only one is on
#: screen; from the south-west, in through both openings of one facade, the frame
#: tears. The inset removes the thing that cannot be ordered.
INSET = 256

#: A stairwell is the run plus a landing at each end, in a shaft its own width.
#: The head landing starts at the inset, because that is where the loft's own
#: wall now is.
WELL_DEPTH = INSET + LANDING + STAIR_RUN + LANDING_FOOT   # 4864

#: The brewhouse's main room and the shaft beside it, stated here because the
#: plan below is written in terms of them.
MAIN_W, MAIN_H = 3072, WELL_DEPTH
MAIN_X, MAIN_Y = WALL, WALL
WELL_X = MAIN_X + MAIN_W + WALL              # 4096


def rect(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


#: Which two corners of a rectangle a compass side runs between.
SIDES = {"north": (0, 1), "east": (1, 2), "south": (2, 3), "west": (3, 0)}


def side_of(plan: list[tuple[int, int]], name: str) -> tuple[tuple[int, int], int]:
    """The midpoint and length of one side of a rectangular plan."""
    first, second = SIDES[name]
    a, b = plan[first], plan[second]
    return (((a[0] + b[0]) // 2, (a[1] + b[1]) // 2),
            int(round(math.hypot(b[0] - a[0], b[1] - a[1]))))


def against(room, name: str, plan: list[tuple[int, int]], side: str):
    """The part of `room`'s named face that the given doorway stands against.

    `Room.face` takes a fraction along the wall, which is the right thing when
    the author means "in the middle" and the wrong thing when they mean "where
    the door is". A doorway already knows where it is -- it is a rectangle in
    the wall -- so this converts the one into the other rather than making the
    author write 0.20512820512 and hope. The midpoint is used rather than a
    corner because a face runs whichever way its outline winds, and which corner
    comes first is not something the author should have to know.

    Finding #2: naming a stretch of a wall by where it stands, rather than by a
    fraction of the wall's length, is something the level program cannot say.
    """
    centre, width = side_of(plan, side)
    a, b = room.local_edge(name)
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    offset = math.hypot(centre[0] - a[0], centre[1] - a[1])
    return room.face(name, at=offset / length, width=width)


def style_of(name: str, **overrides) -> Style:
    """A named material as an inheritable style.

    `surfaces.material` returns region keywords; this keeps the four that are
    style fields, so a whole assembly wears one material and a room under it can
    override a single surface without restating the other three.
    """
    fields = surfaces.material(name, **overrides)
    return Style(
        wall_picnum=fields["wall_picnum"],
        floor_picnum=fields["floor_picnum"],
        ceiling_picnum=fields["ceiling_picnum"],
        parallax_ceiling=fields["parallax_ceiling"] or None,
    )


def jamb(name: str) -> dict:
    """The tile this material dresses its own openings in.

    Of the 8,320 campaign rooms with more than one wall tile, 74% put a
    different one on their two-sided walls than on their solid ones.
    """
    return {"portal_wall_picnum": MATERIALS[name].opening}


# ---------------------------------------------------------------------------
# the plan
# ---------------------------------------------------------------------------
#
# Three blocks round an open yard, with the cellar under the yard. Interiors are
# inset WALL from their block, so every building has an outside. The lofts leave
# through the covered alley between the two, from the side of each upper room,
# so the yard's north facade never opens into a storey that shares ground with a
# room it already opens into -- which is the thing `wallfront` cannot order.
#
#    -1024     0                    5632 6656              9984  11008
#      0       +---------------------+--+ +----------------+
#              | BREWHOUSE           |AL| | KILN           |
#              | mash/loft | well    |ley| | floor/loft|well|
#   3200 porch |                     |    |                | well
#   5888 ------+---------------------+--+ +----------------+------ porch
#              |              gantry (E-W)                     |
#              |               Y A R D                         |
#              |        (malt cellar underneath)               |
#  10240       +-----------------------------------------------+
#              |               S T O R E                       |
#  13312       +-----------------------------------------------+

BREWHOUSE_X, BREWHOUSE_Y = 0, 0
#: The alley is as wide as the stair that goes in it, and sits hard against both
#: buildings' outside walls, so the doorways through those walls are the alley's
#: own east and west sides.
GAP_LEFT = WELL_X + STAIR_WIDTH + WALL          # 5632
KILN_X, KILN_Y = GAP_LEFT + STAIR_WIDTH, 0      # 6656

#: A full wall separates the street volume from the upper-level facade.  The
#: buildings themselves end at y=5888; starting the yard one wall farther south
#: keeps window recesses and the balcony return from becoming zero-thickness
#: solid walls against the open yard.
YARD_TOP, YARD_BOTTOM = 6400, 10240
YARD_LEFT, YARD_RIGHT = 0, 9984

STORE_TOP, STORE_BOTTOM = 10240, 13824
STORE_LEFT, STORE_RIGHT = 768, 9216

#: The yard's corners are cut, because a yard is not a rectangle and because a
#: chamfer stops every wall in the fragment running on one of two bearings.
YARD = [
    (YARD_LEFT, YARD_TOP), (YARD_RIGHT, YARD_TOP),
    (YARD_RIGHT, YARD_BOTTOM - 1024), (YARD_RIGHT - 1024, YARD_BOTTOM),
    (YARD_LEFT + 1024, YARD_BOTTOM), (YARD_LEFT, YARD_BOTTOM - 1024),
]

#: The hatch, and directly beneath it the cellar sector it looks into.
HATCH = rect(4096, 7168, 5632, 8448)

#: The cellar sits well inside the yard's edges, so nothing of it reaches a wall
#: the yard also owns.
CELLAR = rect(1536, 6656, 8448, 9216)

#: The gantry's line. It runs at the lofts' level *across* the yard, porch to
#: porch, because a sector built out over the cobbles would share ground with a
#: volume that reaches the sky.  Its 704-unit panels fit in the 768-unit strip
#: between the new facade and the hatch: 32 units of real cobbles remain on both
#: sides, so a floor sprite cannot touch either wall.  East-west, not
#: north-south: that is how the two second-floor rooms meet without either of
#: them opening on the yard's north facade, which already has the street doors.
GANTRY_Y = YARD_TOP + 384
#: The way in from the yard at street level, through the store's north wall.
STORE_DOOR = rect(4352, YARD_BOTTOM, 5376, STORE_TOP + WALL)

# ---------------------------------------------------------------------------
# the malt tower: a second way up, and the only one that arrives facing the gantry
# ---------------------------------------------------------------------------
#
# A helix costs 6.7 x 6.7 body widths for the whole climb, which is the cheapest
# vertical connector in the campaign. E3M1's is the precedent, measured in
# `bloodmap.spiral`: 22.5 degrees a step, the ceiling tracking the floor, a solid
# newel, and the safety falling out of the arithmetic rather than out of anyone
# thinking about it.
#
# Entry and exit both face north, side by side, because the top landing closes on
# the radial edge the bottom one opens from. That is what a stair tower is: one
# face, two levels.
TOWER_AXIS = (3400, 15200)
TOWER_RADIUS = 1375
#: Undercroft floor to upper floor, in one structure.
TOWER_RISE = UPPER_FLOOR - UNDERCROFT_FLOOR

#: The cellar's way in, meeting the bottom landing's outer chord.  Its north
#: face is a full 1024-unit threshold: this is the entrance to a circulation
#: route, not a crack beside the stair.
TOWER_FOOT = [(3400, 13825), (3926, 13930), (4352, 13312),
              (3328, 13312)]
#: The way out onto the store roof, meeting the top landing's outer chord.
TOWER_HEAD = [(2874, 13930), (3400, 13825), (3400, 13056), (2874, 13056)]

#: The way back out of the cellar. A stair from one level to another has to run
#: in plan area that *neither* level's floor plate covers, so the store's floor
#: stops at the stairwell and the shaft below it is the cellar's.
#: The cellar route carries the player from the vault to the main stair, so it
#: takes the campaign's median aperture width (1024 / 2.67 body widths) rather
#: than the old 512-unit squeeze.  Its eastern edge stays fixed: the stair it
#: meets remains aligned with the store above.
CELLAR_PASSAGE = rect(3328, 9216, 4352, 12288)
CELLAR_LANDING = rect(3328, 12288, 4352, 13312)
STAIRHEAD = rect(4352 + STAIR_RUN, 12288, 4352 + STAIR_RUN + 512, 13312)
#: The store's floor and its stairwell are two rooms at one height, so the wall
#: between them is a wall: 512 of stone with a doorway cut through it. The first
#: version butted them together and `wall-between-rooms-is-not-paper` said so.
STAIR_DOOR = rect(4352 + STAIR_RUN, 11776, 4352 + STAIR_RUN + 512, 12288)

#: A building's outside wall is 512 thick, so the way in through it is a sector
#: of its own: the reveal a door has when the wall it is in has depth.
BREW_DOOR = rect(2560, 5376, 3584, YARD_TOP)
#: Street doors stay on the south facade. The lofts do not: a second opening on
#: the same yard wall is exactly the vantage `layer-stacked-and-seen-together`
#: refuses -- the yard looking into both halves of a storey. The kiln's street
#: door is therefore the only hole in its south wall.
KILN_YARD_DOOR = rect(KILN_X + WALL, MAIN_Y + MAIN_H,
                     KILN_X + WALL + 768, YARD_TOP)


def build() -> LevelProgram:
    """The whole fragment as one tree. Read top down; edit in place."""
    level = LevelProgram(
        "malt_cross",
        name="MALTX",
        visibility=1024,
        style=Style(wall_shade=14, floor_shade=16, ceiling_shade=18),
        note="a brewery yard at night, three levels deep in one footprint",
    )
    for layer_id, (ceiling_z, floor_z) in BANDS.items():
        level.declare_layer(layer_id, ceiling_z=ceiling_z, floor_z=floor_z,
                            note="1.93 bodies of clear height; BB4's band")

    yard = _yard(level)
    brewhouse = _brewhouse(level)
    kiln = _kiln(level)
    alley = _alley(level)
    porches = _porches(level)
    store = _store(level)
    cellar = _cellar(level)

    _join(level, yard, brewhouse, kiln, alley, porches, store, cellar)
    _hatch_link(yard, cellar)
    _gantry(yard)
    level.set_start(yard["cobbles"], local=(0.5, 0.88), angle=1536)
    return level


# ---------------------------------------------------------------------------
# street: the yard everything else is arranged around
# ---------------------------------------------------------------------------

def _yard(level: LevelProgram) -> dict:
    place = level.assembly(
        "yard",
        style=style_of("street_masonry").override(
            layer="street", floor_z=STREET_FLOOR,
            # The yard's ceiling is the sky, which stands above the highest roof
            # rather than at the top of the street band. `layers.permitted_band`
            # allows exactly that for an open sector, and for nothing else.
            clear_height=STREET_FLOOR - SKY_Z,
            floor_shade=18, wall_shade=16),
        note="the brewery yard: cobbles, open to the night",
    )
    cobbles = place.room("cobbles", YARD, note="the yard proper")
    cobbles.light_source("moon", local=(0.5, 0.45), height_player_heights=6.0)

    # A patch of floor in the middle of a yard is a hole with something in it:
    # two regions of one layer may not share ground.
    cobbles.carve(HATCH)
    hatch = place.room(
        "hatch", HATCH,
        style=Style(clear_height=CLEAR, parallax_ceiling=False,
                    ceiling_picnum=MATERIALS["city_crypt"].ceiling,
                    floor_shade=22),
        note="the malt hatch: the floor you can see the cellar through")
    return {"place": place, "cobbles": cobbles, "hatch": hatch}


# ---------------------------------------------------------------------------
# the brewhouse: two storeys and the stairwell between them
# ---------------------------------------------------------------------------
#
#   x:  512      3584 4096      5120
#      +----------+   +----------+
#      |          |   | landing  |     y 512 .. 1024
#      |   mash   |   |  stair   |     y 1024 .. 4864
#      |   loft   |   | stairfoot|     y 4864 .. 5376
#      +----------+   +----------+
#
# The stairwell is a separate shaft with WALL between it and the main room,
# reached through one doorway on each level. That separation is not tidiness:
# two same-layer regions that merely share an edge must be joined, and the loft
# must not open onto the middle of a stair.


MAIN = rect(MAIN_X, MAIN_Y, MAIN_X + MAIN_W, MAIN_Y + MAIN_H)

#: The loft, on the mash's own outline.
#:
#: It used to be inset 256 on every side, on the theory that two storeys with one
#: outline give every wall of the lower a twin in the upper and `wallfront`
#: cannot order a pair on one line. That theory is measurably wrong: 91% of the
#: campaign's 7,533 overlapping sector pairs have exactly such a wall pair,
#: because putting one sector directly over another on the same outline is how
#: Blood builds stacked space at all.
#:
#: The inset was worse than useless -- it *caused* the tear. Set in, every wall
#: of the loft stands **strictly inside the mash's plan**, and Build's sort is
#: 2D: a one-sided wall standing inside another sector's footprint retires its
#: screen columns whole once drawn (engine.c:3216) no matter that the two are
#: 40,960 apart in z, and `scansector` then never recurses past it
#: (engine.c:3156). Looking in from the yard through the street door and the
#: loading door at once, the loft's inset wall stood in the middle of the mash
#: and the mash's wall stood in the middle of the loading door, and whichever
#: drew first took the columns.
#:
#: Flush, no wall of one is inside the other, and the pair is the ordinary
#: stacked storey the campaign builds everywhere.
LOFT = rect(MAIN_X, MAIN_Y, MAIN_X + MAIN_W, MAIN_Y + MAIN_H)

_HEAD_Y = MAIN_Y + INSET
_FOOT_Y = _HEAD_Y + LANDING + STAIR_RUN
WELL_TOP = rect(WELL_X, _HEAD_Y, WELL_X + STAIR_WIDTH, _HEAD_Y + LANDING)
WELL_FOOT = rect(WELL_X, _FOOT_Y, WELL_X + STAIR_WIDTH, MAIN_Y + MAIN_H)
#: Doorways are inset from the landing's north edge so two rooms in a row do
#: not put their north walls on one line -- that is what `wallfront` cannot
#: rank, and it is the pair the sweep actually named (7x8, 3x4), not the stack.
DOOR_JOG = 128
DOOR_UP = rect(MAIN_X + MAIN_W, _HEAD_Y + DOOR_JOG, WELL_X, _HEAD_Y + LANDING)
DOOR_DOWN = rect(MAIN_X + MAIN_W, _FOOT_Y + DOOR_JOG, WELL_X, MAIN_Y + MAIN_H)

#: The covered alley between the buildings. Same shaft grammar as a stairwell
#: inside a building: a landing at the top, a foot at the bottom, the run
#: between them. The yard meets it only at street height, through the south
#: door; the lofts meet it only from the side, through the east and west doors.
#: Those two facts together are the whole point -- the space you enter the
#: mash from never opens into the loft, and the space you leave the loft into
#: never opens into the mash.
ALLEY_LANDING = rect(GAP_LEFT, _HEAD_Y, GAP_LEFT + STAIR_WIDTH, _HEAD_Y + LANDING)
ALLEY_FOOT = rect(GAP_LEFT, _FOOT_Y, GAP_LEFT + STAIR_WIDTH, MAIN_Y + MAIN_H)
ALLEY_YARD_DOOR = rect(GAP_LEFT, MAIN_Y + MAIN_H, GAP_LEFT + STAIR_WIDTH, YARD_TOP)
BREW_ALLEY_DOOR = rect(WELL_X + STAIR_WIDTH, _HEAD_Y, GAP_LEFT, _HEAD_Y + LANDING)


def _brewhouse(level: LevelProgram) -> dict:
    place = level.assembly(
        "brewhouse",
        style=style_of("city_service").override(wall_shade=20, ceiling_shade=24),
        note="the working building: mash floor below, malt loft above",
    )

    ground = place.assembly(
        "ground",
        style=Style(layer="street", floor_z=STREET_FLOOR, clear_height=CLEAR),
        note="the mash floor, and the foot of the stair")
    mash = ground.room("mash", MAIN, note="coppers and a drain; the loudest room here")
    mash.light_source("copper_fire", local=(0.3, 0.65), height_player_heights=0.9)
    stairfoot = ground.room(
        "stairfoot", WELL_FOOT,
        style=style_of("city_service").override(floor_shade=22),
        note="where the stair down from the loft arrives")
    mash_door = ground.room(
        "mash_door", DOOR_DOWN, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="through the stairwell wall, at the bottom")
    yard_door = ground.room(
        "yard_door", BREW_DOOR, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="out to the yard, through 512 units of outside wall")

    first = place.assembly(
        "first",
        style=Style(layer="upper", floor_z=UPPER_FLOOR, clear_height=CLEAR),
        note="the malt loft; the alley between the buildings is the way off")
    loft = first.room(
        "loft", LOFT,
        style=style_of("city_saloon").override(floor_shade=20),
        note="boarded floor and sacks; the way off is east, through the stair landing")
    loft.light_source("loft_lamp", local=(0.35, 0.4), height_player_heights=1.6)
    landing = first.room("landing", WELL_TOP, note="the head of the stair")
    loft_door = first.room(
        "loft_door", DOOR_UP, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="through the stairwell wall, at the top")

    # The descent from inside a building into the level below. Ten equal steps
    # carrying the whole 40,960, growing south out of the landing.
    landing.staircase(
        "malt_stair", "south", at=0.5, width=STAIR_WIDTH,
        total_rise=STOREY, step_rise=STEP_RISE, tread=TREAD,
        clear_height=CLEAR, shade_ramp=(24, 16),
        arrive_at=stairfoot.region_id,
        **surfaces.material("city_service"),
    )
    return {"place": place, "ground": ground, "mash": mash, "stairfoot": stairfoot,
            "mash_door": mash_door, "yard_door": yard_door, "first": first, "loft": loft,
            "landing": landing, "loft_door": loft_door}


# ---------------------------------------------------------------------------
# the kiln: the same building grammar, mirrored, with its own stair
# ---------------------------------------------------------------------------

KILN_MAIN_W = 2048
KILN_MAIN = rect(KILN_X + WALL, KILN_Y + WALL,
                 KILN_X + WALL + KILN_MAIN_W, KILN_Y + WALL + WELL_DEPTH)
#: The kiln loft, on the drying floor's outline, for the reason the malt loft is
#: on the mash's.
KILN_LOFT = rect(KILN_X + WALL, KILN_Y + WALL,
                 KILN_X + WALL + KILN_MAIN_W,
                 KILN_Y + WALL + WELL_DEPTH)
KILN_WELL_X = KILN_X + WALL + KILN_MAIN_W + WALL
_KILN_HEAD_Y = KILN_Y + WALL + INSET
_KILN_FOOT_Y = _KILN_HEAD_Y + LANDING + STAIR_RUN
KILN_WELL_TOP = rect(KILN_WELL_X, _KILN_HEAD_Y,
                     KILN_WELL_X + STAIR_WIDTH, _KILN_HEAD_Y + LANDING)
KILN_WELL_FOOT = rect(KILN_WELL_X, _KILN_FOOT_Y,
                      KILN_WELL_X + STAIR_WIDTH, KILN_Y + WALL + WELL_DEPTH)
KILN_DOOR_UP = rect(KILN_X + WALL + KILN_MAIN_W, _KILN_HEAD_Y + DOOR_JOG,
                    KILN_WELL_X, _KILN_HEAD_Y + LANDING)
KILN_DOOR_DOWN = rect(KILN_X + WALL + KILN_MAIN_W, _KILN_FOOT_Y + DOOR_JOG,
                      KILN_WELL_X, KILN_Y + WALL + WELL_DEPTH)
#: Out of the kiln loft through its west wall -- the side of the room, not the
#: south facade the street door already occupies.
KILN_ALLEY_DOOR = rect(KILN_X, _HEAD_Y, KILN_X + WALL, _HEAD_Y + LANDING)

# ---------------------------------------------------------------------------
# side porches: the BB4 pattern -- both storeys open to the yard, not on one line
# ---------------------------------------------------------------------------
#
# Sector 9 (kiln floor) and sector 13 (kiln loft) share a footprint. Opening
# both to the yard on the *north* facade (wall 6) is one vertical sightline and
# the frame tears. Opening the loft through the yard's *east* wall (wall 7) is
# a different line, which is how BB4 stacks three floors on one space.
#
# The brewhouse gets the same treatment on the west, so the gantry has two
# ends and the second floor is a circuit, not two cul-de-sacs.

PORCH_W = 1024
PORCH_ALONG = 1024
SIDE_Y0 = 3200
SIDE_Y1 = SIDE_Y0 + LANDING

WEST_SIDE_DOOR = rect(0, SIDE_Y0, WALL, SIDE_Y1)
WEST_PORCH = rect(-PORCH_W, SIDE_Y0, 0, YARD_TOP + PORCH_ALONG)
WEST_YARD_OPEN = rect(-PORCH_W, YARD_TOP, 0, YARD_TOP + PORCH_ALONG)

#: The kiln's east wall is the stairwell. The loft therefore leaves through its
#: south wall, east of the street door, onto a balcony that does *not* open to
#: the yard -- that would be the north facade again. The balcony runs east past
#: the yard's north-east corner and the porch turns onto the yard's east wall.
KILN_LOFT_EAST = KILN_X + WALL + KILN_MAIN_W
#: Window reveals stop at the inside face of the facade.  The remaining WALL is
#: real masonry before the open yard begins, not a zero-thickness wall line.
#: The loft's way onto the yard is the side porch, turned 90 degrees, which is
#: what BB4's stacked rooms do.
WINDOW_STOP = YARD_TOP - WALL
BREW_WINDOW = rect(1024, MAIN_Y + MAIN_H, 2048, WINDOW_STOP)
KILN_WINDOW = rect(KILN_LOFT_EAST - 1024, MAIN_Y + MAIN_H, KILN_LOFT_EAST, WINDOW_STOP)
EAST_RUN = rect(KILN_LOFT_EAST, MAIN_Y + MAIN_H, YARD_RIGHT, WINDOW_STOP)
EAST_PORCH = rect(YARD_RIGHT, MAIN_Y + MAIN_H, YARD_RIGHT + PORCH_W,
                 YARD_TOP + PORCH_ALONG)
EAST_YARD_OPEN = rect(YARD_RIGHT, YARD_TOP, YARD_RIGHT + PORCH_W,
                     YARD_TOP + PORCH_ALONG)


def _kiln(level: LevelProgram) -> dict:
    place = level.assembly(
        "kiln",
        style=style_of("city_parlor").override(wall_shade=18),
        note="where the malt is dried: warmer and dirtier than the brewhouse")

    ground = place.assembly(
        "ground",
        style=Style(layer="street", floor_z=STREET_FLOOR, clear_height=CLEAR),
        note="the drying floor and the foot of its stair")
    floor = ground.room("floor", KILN_MAIN,
                        style=Style(floor_shade=22, ceiling_shade=26),
                        note="perforated, hot, and the way in from the yard")
    floor.light_source("kiln_mouth", local=(0.5, 0.8), height_player_heights=0.5)
    kiln_foot = ground.room("stairfoot", KILN_WELL_FOOT,
                            style=style_of("city_service"),
                            note="the foot of the kiln stair")
    kiln_door_down = ground.room(
        "door", KILN_DOOR_DOWN, role="doorway",
        style=style_of("city_service").override(clear_height=CLEAR),
        region_kwargs=jamb("city_service"), note="into the stairwell")
    kiln_yard_door = ground.room(
        "yard_door", KILN_YARD_DOOR, role="doorway",
        style=style_of("city_service").override(clear_height=CLEAR),
        region_kwargs=jamb("city_service"),
        note="out to the yard, through 512 units of outside wall")

    first = place.assembly(
        "first",
        style=style_of("city_service").override(
            layer="upper", floor_z=UPPER_FLOOR, clear_height=CLEAR),
        note="the kiln loft, reached from its own stair")
    kiln_loft = first.room("loft", KILN_LOFT,
                           note="one long room over the drying floor; the alley is west")
    kiln_loft.light_source("cowl", local=(0.5, 0.5), height_player_heights=1.8)
    kiln_landing = first.room("landing", KILN_WELL_TOP, note="the head of the stair")
    kiln_door_up = first.room(
        "door", KILN_DOOR_UP, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="out of the stairwell onto the loft")

    kiln_landing.staircase(
        "kiln_stair", "south", at=0.5, width=STAIR_WIDTH,
        total_rise=STOREY, step_rise=STEP_RISE, tread=TREAD,
        clear_height=CLEAR, shade_ramp=(26, 20),
        arrive_at=kiln_foot.region_id,
        **surfaces.material("city_service"),
    )
    return {"place": place, "ground": ground, "floor": floor,
            "stairfoot": kiln_foot, "door_down": kiln_door_down,
            "yard_door": kiln_yard_door,
            "first": first, "loft": kiln_loft, "landing": kiln_landing,
            "door_up": kiln_door_up}


# ---------------------------------------------------------------------------
# the alley: both lofts leave from the side, and only then down to the yard
# ---------------------------------------------------------------------------

def _alley(level: LevelProgram) -> dict:
    place = level.assembly(
        "alley",
        style=style_of("city_service").override(wall_shade=22, ceiling_shade=26),
        note="the covered close between the buildings: both lofts, then the yard")

    ground = place.assembly(
        "ground",
        style=Style(layer="street", floor_z=STREET_FLOOR, clear_height=CLEAR),
        note="the foot of the alley stair, and the door onto the cobbles")
    stairfoot = ground.room(
        "stairfoot", ALLEY_FOOT,
        style=style_of("city_service").override(floor_shade=22),
        note="where the alley stair arrives at street height")
    yard_door = ground.room(
        "yard_door", ALLEY_YARD_DOOR, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="out to the yard, between the two street doors, not above either")

    first = place.assembly(
        "first",
        style=Style(layer="upper", floor_z=UPPER_FLOOR, clear_height=CLEAR),
        note="the head of the alley, fed from both lofts through their side walls")
    landing = first.room(
        "landing", ALLEY_LANDING,
        note="the alley landing: east from the malt loft, west from the kiln loft")
    landing.light_source("alley_lamp", local=(0.5, 0.5), height_player_heights=1.5)
    brew_door = first.room(
        "brew_door", BREW_ALLEY_DOOR, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="through the brewhouse's east wall, off the malt-stair landing")
    kiln_door = first.room(
        "kiln_door", KILN_ALLEY_DOOR, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="through the kiln's west wall, the side of the loft")

    landing.staircase(
        "alley_stair", "south", at=0.5, width=STAIR_WIDTH,
        total_rise=STOREY, step_rise=STEP_RISE, tread=TREAD,
        clear_height=CLEAR, shade_ramp=(26, 18),
        arrive_at=stairfoot.region_id,
        **surfaces.material("city_service"),
    )
    return {"place": place, "ground": ground, "stairfoot": stairfoot,
            "yard_door": yard_door, "first": first, "landing": landing,
            "brew_door": brew_door, "kiln_door": kiln_door}


# ---------------------------------------------------------------------------
# porches and windows: the second floor meets the yard from the side
# ---------------------------------------------------------------------------

def _porches(level: LevelProgram) -> dict:
    place = level.assembly(
        "porches",
        style=style_of("city_service").override(
            layer="upper", floor_z=UPPER_FLOOR, clear_height=CLEAR,
            wall_shade=18, floor_shade=16),
        note="side porches onto the yard, and the windows that look out over it")

    west_door = place.room(
        "west_door", WEST_SIDE_DOOR, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="out of the malt loft through its west wall")
    west = place.room(
        "west", WEST_PORCH,
        style=style_of("leads").override(
            clear_height=UPPER_FLOOR - SKY_Z, floor_shade=14, wall_shade=12),
        note="the west porch: along the yard's west wall, onto the gantry")
    west.light_source("west_lamp", local=(0.5, 0.85), height_player_heights=1.4)

    east_door = place.room(
        "east_door", KILN_WINDOW, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="French doors out of the kiln loft, east of the street door, onto the balcony")
    east_run = place.room(
        "east_run", EAST_RUN, role="doorway",
        style=style_of("leads").override(
            clear_height=UPPER_FLOOR - SKY_Z, floor_shade=14, wall_shade=12),
        note="the balcony along the kiln's south wall; it does not open to the yard")
    east = place.room(
        "east", EAST_PORCH,
        style=style_of("leads").override(
            clear_height=UPPER_FLOOR - SKY_Z, floor_shade=14, wall_shade=12),
        note="the east porch: into the yard through its east wall, not its north")
    east.light_source("east_lamp", local=(0.5, 0.85), height_player_heights=1.4)

    brew_window = place.room(
        "brew_window", BREW_WINDOW, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_saloon"),
        note="a window in the malt loft's south wall, west of the street door")
    return {"place": place, "west_door": west_door, "west": west,
            "east_door": east_door, "east_run": east_run, "east": east,
            "brew_window": brew_window}


# ---------------------------------------------------------------------------
# the store: one storey whose roof is the upper level's floor
# ---------------------------------------------------------------------------

STORE_INSIDE = rect(STORE_LEFT + WALL, STORE_TOP + WALL,
                    STORE_RIGHT - WALL, STORE_BOTTOM - WALL)

#: The roof, inset from the store on every side.
#:
#: It used to run out to the yard's own edge and stand open along it, and that
#: is what tore the frame. Two things it did, both fatal and neither fixable
#: after the fact:
#:
#: * it put a wall of the roof on the same line as the store's own north wall,
#:   and the roof and the store's interior share ground. `wallfront`
#:   (engine.cpp:2227) is the predicate the whole draw-order sort rests on, and
#:   for two segments on one line it returns -1, which the sort answers with
#:   `continue` (engine.cpp:9736 -- "Almost works, but not quite :(").
#: * it put a large sector, floor 40,960 above the yard's eye, into the yard's
#:   own flood. Its far wall is one-sided, so drawing it sets
#:   `umost[x] = dmost[x]+1` and retires those columns whole after painting the
#:   handful of rows its geometry reaches; and `scansector` recurses only while
#:   a column is still open (engine.c:3156). The store's interior behind it was
#:   therefore never scanned at all, and its columns stayed at whatever the
#:   frame was cleared to.
#:
#: Inset on all four sides, no wall of the roof lies on a line with any wall of
#: the store, and the yard's flood does not reach it. The way up is the stair
#: inside, which is what a roof usually has.
LEADS = rect(STORE_LEFT + WALL + INSET, STORE_TOP + WALL + INSET,
             STORE_RIGHT - WALL - INSET, STORE_BOTTOM - WALL - INSET)
#: The store's own floor is the north strip only; the rest of its footprint is
#: the stairwell the cellar comes up in, and the roof over both.
SHED = rect(STORE_LEFT + WALL, STORE_TOP + WALL, STORE_RIGHT - WALL, 11776)


def _store(level: LevelProgram) -> dict:
    place = level.assembly(
        "store",
        style=style_of("city_service"),
        note="a low range along the south of the yard; its roof is walked on")

    inside = place.assembly(
        "inside",
        style=Style(layer="street", floor_z=STREET_FLOOR, clear_height=CLEAR),
        note="the store itself")
    shed = inside.room("shed", SHED,
                       style=Style(floor_shade=26, ceiling_shade=28),
                       note="barrels, and the way through to the yard")
    shed.light_source("store_lamp", local=(0.7, 0.5), height_player_heights=1.5)
    stairhead = inside.room(
        "stairhead", STAIRHEAD,
        style=Style(floor_shade=24),
        note="the head of the cellar stair, walled off from the store floor")
    stair_door = inside.room(
        "stair_door", STAIR_DOOR, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="through the store's south wall, to the stairhead")
    shed_door = inside.room(
        "door", STORE_DOOR, role="doorway",
        style=Style(clear_height=CLEAR), region_kwargs=jamb("city_service"),
        note="in from the yard, through the store's north wall")

    roof = place.assembly(
        "roof",
        style=style_of("leads").override(
            layer="upper", floor_z=UPPER_FLOOR,
            # The same sky as the yard it looks over. 94% of the campaign's
            # adjacent open-to-open sector pairs hold their sky at one z, and
            # two different ones draw as a band of wall hanging in the air.
            clear_height=UPPER_FLOOR - SKY_Z,
            floor_shade=14, wall_shade=12),
        note="the store roof: level with both lofts, and where the gantry lands")
    leads = roof.room("leads", LEADS,
                      note="walked over the store, open to the sky, reached by "
                           "the stair inside it")
    tower_head = roof.room(
        "tower_head", TOWER_HEAD, role="doorway",
        style=style_of("city_service").override(
            clear_height=TOWER_CLEAR, parallax_ceiling=False,
            ceiling_picnum=MATERIALS["city_service"].ceiling, floor_shade=16),
        note="off the malt tower onto the store roof, facing the gantry")
    return {"place": place, "inside": inside, "shed": shed, "shed_door": shed_door,
            "stairhead": stairhead, "stair_door": stair_door, "roof": roof,
            "leads": leads, "tower_head": tower_head}


# ---------------------------------------------------------------------------
# the undercroft: the malt cellar under the yard
# ---------------------------------------------------------------------------

def _cellar(level: LevelProgram) -> dict:
    place = level.assembly(
        "cellar",
        style=style_of("city_crypt").override(
            layer="undercroft", floor_z=UNDERCROFT_FLOOR, clear_height=CLEAR,
            wall_shade=28, floor_shade=30, ceiling_shade=30),
        note="the malt cellar: the whole reason the yard has a hatch in it")

    vault = place.room("vault", CELLAR, note="one long vault, under the yard")
    vault.light_source("cellar_lamp", local=(0.3, 0.5), height_player_heights=1.4)

    # The lower half of the room-over-room pair: the same footprint as the hatch
    # above, so what the player sees through the yard floor is where they land.
    vault.carve(HATCH)
    under_hatch = place.room("under_hatch", HATCH,
                             note="what the hatch looks down into")

    # The way back out. Without it the hatch is a trap: `layers.drop_between`
    # says the fall in costs nothing, and nothing is not the same as nowhere.
    passage = place.room(
        "passage", CELLAR_PASSAGE, role="doorway",
        style=style_of("city_sewer").override(floor_shade=30),
        note="a low run south under the yard, toward the store")
    cellar_landing = place.room(
        "landing", CELLAR_LANDING,
        style=style_of("city_service").override(floor_shade=28),
        note="the foot of the stair up into the store")
    tower_foot = place.room(
        "tower_foot", TOWER_FOOT, role="doorway",
        # No taller than the stair itself. A door in a tower's outer wall stands
        # where every turn passes, so a doorway with the room's clear height
        # rather than the stair's has the turn above it poking through -- which
        # is exactly what the geometry audit caught here.
        style=style_of("city_service").override(clear_height=TOWER_CLEAR,
                                                floor_shade=28),
        note="out of the cellar into the foot of the malt tower")
    return {"place": place, "vault": vault, "under_hatch": under_hatch,
            "passage": passage, "landing": cellar_landing,
            "tower_foot": tower_foot}


# ---------------------------------------------------------------------------
# how the parts meet
# ---------------------------------------------------------------------------

def _join(level: LevelProgram, yard: dict, brewhouse: dict, kiln: dict,
          alley: dict, porches: dict, store: dict, cellar: dict) -> None:
    """Every opening in the fragment."""
    # The cellar stair. It belongs to the cellar rather than to the store,
    # because a connector's steps take the layer of the room that grew them and
    # this run has to be allowed to climb out of the undercroft band.
    cellar["landing"].staircase(
        "cellar_stair", "east", at=0.5, width=STAIR_WIDTH,
        total_rise=-STOREY, step_rise=STEP_RISE, tread=TREAD,
        clear_height=CLEAR, shade_ramp=(30, 24),
        arrive_at=store["stairhead"].region_id,
        **surfaces.material("city_service"),
    )
    # The malt tower. One line of intent: climb from the cellar to the lofts,
    # and come out facing north onto the store roof, where the gantry is. The
    # turns, the step count, the step rise, the landings and the overlaps between
    # turns are all derived -- see `bloodmap.spiral`.
    def raise_the_tower(layout, _room):
        tower = spiral_stair(
            layout, "malt_tower", axis=TOWER_AXIS, base_floor_z=UNDERCROFT_FLOOR,
            rise=TOWER_RISE, exit_angle=0.0, entry_angle=270.0,
            radius=TOWER_RADIUS, layer="undercroft",
            **surfaces.material("city_service"))
        # Both ends join on the chord at the outer wall, which is the only edge
        # of a wedge that faces outward at all. The bottom landing opens from the
        # 270-degree radial edge and the top one closes on it, so the two doors
        # end up side by side on one face -- which is what a stair tower is.
        entry, way_out = tower.flanks
        layout.add_connection(
            "tower_in", cellar["tower_foot"].region_id, entry.region_id,
            a1=entry.a, a2=entry.b, min_width=512)
        layout.add_connection(
            "tower_out", way_out.region_id, store["tower_head"].region_id,
            a1=way_out.a, a2=way_out.b, min_width=512)

        # A door in a tower's outer wall stands on a chord every turn crosses.
        # The doorway is a portal to the one step it serves and shares that same
        # line with the step a turn above and the one a turn below, which is not
        # a mistake and has to be said so. Their bands are the stair's own slab
        # apart, by the arithmetic `plan_spiral` already refused to break.
        per_turn = int(round(360.0 / tower.provenance["step_angle"]))
        for offset, door in ((0, cellar["tower_foot"]),
                             (len(tower.regions) - 1, store["tower_head"])):
            for index, region_id in enumerate(tower.regions):
                if index != offset and (index - offset) % per_turn == 0:
                    layout.declare_special(door.region_id, region_id, "tower_door")
        return tower

    cellar["landing"].raw(
        "spiral: the malt tower, cellar to the store roof", raise_the_tower)
    level.connect(cellar["landing"].face("south"),
                  against(cellar["tower_foot"], "north",
                          rect(3328, 13312, 4352, 13930), "north"),
                  connection_id="cellar_to_tower_foot")
    level.connect(store["tower_head"].face("north"),
                  against(store["leads"], "south",
                          [(2874, 13056), (3400, 13056), (3400, 13930), (2874, 13930)],
                          "north"),
                  connection_id="tower_head_to_leads")

    level.connect(against(cellar["vault"], "south", CELLAR_PASSAGE, "north"),
                  cellar["passage"].face("north"),
                  connection_id="vault_to_passage")
    store["inside"].connect(against(store["shed"], "south", STAIR_DOOR, "north"),
                            store["stair_door"].face("north"),
                            connection_id="shed_to_stair_door")
    store["inside"].connect(store["stair_door"].face("south"),
                            store["stairhead"].face("north"),
                            connection_id="stair_door_to_stairhead")
    level.connect(cellar["passage"].face("south"),
                  cellar["landing"].face("north"),
                  connection_id="passage_to_landing")
    # Both halves of the hatch fill a hole in the floor they are set into, so
    # every side is a way on -- above and below alike.
    for side in ("north", "east", "south", "west"):
        level.connect(yard["cobbles"].hole_face(0, side), yard["hatch"].face(side),
                      connection_id="cobbles_to_hatch_" + side)
        level.connect(cellar["vault"].hole_face(0, side),
                      cellar["under_hatch"].face(side),
                      connection_id="vault_to_under_hatch_" + side)

    # Inside the brewhouse: one doorway through the stairwell wall per level.
    brewhouse["ground"].connect(against(brewhouse["mash"], "east", DOOR_DOWN, "west"),
                                brewhouse["mash_door"].face("west"),
                                connection_id="mash_to_door")
    brewhouse["ground"].connect(brewhouse["mash_door"].face("east"),
                                brewhouse["stairfoot"].face("west"),
                                connection_id="door_to_stairfoot")
    brewhouse["first"].connect(against(brewhouse["loft"], "east", DOOR_UP, "west"),
                               brewhouse["loft_door"].face("west"),
                               connection_id="loft_to_door")
    brewhouse["first"].connect(brewhouse["loft_door"].face("east"),
                               brewhouse["landing"].face("west"),
                               connection_id="door_to_landing")

    # Inside the kiln: the same pattern.
    kiln["ground"].connect(kiln["floor"].face("east", at=1.0, width=LANDING),
                           kiln["door_down"].face("west"),
                           connection_id="kiln_floor_to_door")
    kiln["ground"].connect(kiln["door_down"].face("east"),
                           kiln["stairfoot"].face("west"),
                           connection_id="kiln_door_to_stairfoot")
    kiln["first"].connect(against(kiln["loft"], "east", KILN_DOOR_UP, "west"),
                          kiln["door_up"].face("west"),
                          connection_id="kiln_loft_to_door")
    kiln["first"].connect(kiln["door_up"].face("east"),
                          kiln["landing"].face("west"),
                          connection_id="kiln_door_to_landing")

    # Out of the yard at street level, into the store.
    level.connect(against(yard["cobbles"], "south", STORE_DOOR, "north"),
                  store["shed_door"].face("north"),
                  connection_id="yard_to_store_door")
    level.connect(store["shed_door"].face("south"), store["shed"].face("north"),
                  connection_id="store_door_to_shed")
    for name, door, inside_room, plan in (
        ("brewhouse", brewhouse["yard_door"], brewhouse["mash"], BREW_DOOR),
        ("kiln", kiln["yard_door"], kiln["floor"], KILN_YARD_DOOR),
    ):
        level.connect(against(inside_room, "south", plan, "north"),
                      door.face("north"),
                      connection_id="{}_to_yard_door".format(name))
        level.connect(door.face("south"),
                      against(yard["cobbles"], "north", plan, "south"),
                      connection_id="yard_door_to_yard_{}".format(name))

    # The alley: both lofts from the side, then down, then the yard. The yard
    # opening is a street door between the two buildings, so one flood never
    # holds a storey and the storey over it.
    level.connect(brewhouse["landing"].face("east"),
                  alley["brew_door"].face("west"),
                  connection_id="landing_to_alley_door")
    level.connect(alley["brew_door"].face("east"),
                  alley["landing"].face("west"),
                  connection_id="alley_door_to_landing")
    level.connect(against(kiln["loft"], "west", KILN_ALLEY_DOOR, "east"),
                  alley["kiln_door"].face("east"),
                  connection_id="kiln_loft_to_alley_door")
    level.connect(alley["kiln_door"].face("west"),
                  alley["landing"].face("east"),
                  connection_id="kiln_alley_door_to_landing")
    alley["ground"].connect(alley["stairfoot"].face("south"),
                            alley["yard_door"].face("north"),
                            connection_id="alley_foot_to_yard_door")
    level.connect(alley["yard_door"].face("south"),
                  against(yard["cobbles"], "north", ALLEY_YARD_DOOR, "south"),
                  connection_id="alley_door_to_yard")

    # Side porches. The kiln loft (the room over the drying floor) meets the
    # yard through the yard's east wall -- wall 7 of sector 0 -- so a look into
    # the loft is not a look into the drying floor along the same line.
    level.connect(against(brewhouse["loft"], "west", WEST_SIDE_DOOR, "east"),
                  porches["west_door"].face("east"),
                  connection_id="loft_to_west_door")
    level.connect(porches["west_door"].face("west"),
                  against(porches["west"], "east", WEST_SIDE_DOOR, "west"),
                  connection_id="west_door_to_porch")
    level.connect(against(porches["west"], "east", WEST_YARD_OPEN, "east"),
                  against(yard["cobbles"], "west", WEST_YARD_OPEN, "east"),
                  connection_id="west_porch_to_yard")

    level.connect(against(kiln["loft"], "south", KILN_WINDOW, "north"),
                  porches["east_door"].face("north"),
                  connection_id="loft_to_east_door", min_width=256)
    level.connect(porches["east_door"].face("east"),
                  porches["east_run"].face("west"),
                  connection_id="east_door_to_run", min_width=256)
    level.connect(porches["east_run"].face("east"),
                  against(porches["east"], "west", EAST_RUN, "east"),
                  connection_id="east_run_to_porch", min_width=256)
    level.connect(against(porches["east"], "west", EAST_YARD_OPEN, "west"),
                  against(yard["cobbles"], "east", EAST_YARD_OPEN, "west"),
                  connection_id="east_porch_to_yard")

    # Look-outs from the malt window and from the kiln balcony. Ordinary
    # portals: a one-way or blocking flag here was a draw-order guess that the
    # sweep did not support. The openings stay until the plan is rebuilt with
    # jogs so these walls no longer share a line with the street doors.
    level.connect(against(brewhouse["loft"], "south", BREW_WINDOW, "north"),
                  porches["brew_window"].face("north"),
                  connection_id="brew_loft_to_window", min_width=256)
    # The alcoves stop in the wall. Opening them to the yard on the same line
    # as the street doors is the north-facade pair the detector names; the
    # sweep never blamed that pair, but it is still an overlapping pair with
    # two openings on one line, and one-way flags are not how it is resolved.



# ---------------------------------------------------------------------------
# the two things a sector cannot do
# ---------------------------------------------------------------------------

def _hatch_link(yard: dict, cellar: dict) -> None:
    """Open the yard floor onto the cellar with a room-over-room stack.

    Not decoration and not a shortcut. `GetZRange` (blood/src/gameutil.cpp:726)
    replaces a sector's floor with the *linked* sector's floor whenever
    `gUpperLink` is set, so the hatch floor stops being solid and the player
    falls through it into the room below and lands on that room's floor. The
    mirror tile on both surfaces is what makes the cellar visible from the yard
    before they step on it -- without it `CheckLink` still moves them and they
    cross blind.

    The drop is one storey, 40,960 z. `layers.fall_cost` says Blood forgives
    anything under 62,564, so it costs nothing to take.
    """
    yard["hatch"].raw(
        "room-over-room: the yard floor opens onto the malt cellar",
        lambda layout, room: room_over_room(
            layout, "malt_hatch", room.region_id,
            cellar["under_hatch"].region_id,
            link_id=1, at=(4864, 7808), family="stack"),
    )


def _gantry(yard: dict) -> None:
    """Cross the yard on a deck of blocking floor-aligned sprites.

    A sector built out over the yard would share ground with an open volume
    reaching from the cobbles to the sky, and nothing in z could separate them --
    exactly the case `bloodmap.layers` refuses. The campaign's answer, on 86% of
    its maps, is to build the walkway out of sprites: a blocking floor-aligned
    sprite is a surface with no sector behind it, so it stands in the yard's air
    without being a second floor of the yard.

    East-west between the two side porches, so the second floor is a crossing
    rather than a bridge that leads nowhere.
    """
    yard["cobbles"].raw(
        "sprite deck: the gantry from the west porch to the east porch",
        lambda layout, room: sprite_bridge(
            layout, "gantry", room.region_id,
            start=(WALL, GANTRY_Y), end=(YARD_RIGHT - WALL, GANTRY_Y),
            z=UPPER_FLOOR, repeat=23, shade_from=18, shade_to=24),
    )


# ---------------------------------------------------------------------------
# building it
# ---------------------------------------------------------------------------

def make_layout():
    """The planar source this fragment lowers to."""
    return build().compile()


if __name__ == "__main__":
    program = build()
    print(program.tree())
    compiled = program.compile().compile()
    print("")
    print("{} sectors, {} walls, {} sprites".format(
        len(compiled.level.sectors), len(compiled.level.walls),
        len(compiled.level.sprites)))
