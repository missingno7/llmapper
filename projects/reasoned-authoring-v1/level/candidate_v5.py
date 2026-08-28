"""Cliffside monastery, iteration 5: curvature and surface.

Three findings drove this iteration, and one of them turned out to be a bug in
the compiler rather than anything about the level.

1. THE SKY WAS NEVER THE LEVEL'S FAULT.  Four iterations recorded "the sky
   renders very dark" as an unexplained unknown.  Captured against an original
   under identical conditions it was obvious: E2M3's outdoor ground shows moving
   cloud, ours showed flat black, with byte-identical ceiling configuration.  The
   difference was in the MAP header.  All 38 campaign maps that contain a
   parallax sector declare a sixteen-panel sky; ``new_level`` hardcoded a single
   panel, which maps the whole 360 degrees onto one 64-pixel column of the sky
   tile.  ``PlanarLayout`` now emits the corpus panorama, so this is fixed for
   every level the project generates, not only this one.

2. THE CRYPT WAS UNREADABLE.  Tile 1097 was on the floor, the walls and the
   ceiling of all eleven crypt sectors, and the rendered frame shows one
   continuous pattern with no visible edge between any two surfaces.  The corpus
   does use 1097 that way -- 26 of its 31 occurrences are single-surface -- but
   at a median of 8 player areas and 2.91 player heights.  Our crypt hall is 174
   player areas.  The tile is a cell finish and we stretched it over a hall.
   The hall, its stair and the tomb block take E6M3's own crypt treatment
   (wall 194 over floor 568 under ceiling 67 and 255), the reliquary keeps 1097
   at cell scale where the corpus supports it, and the two larger chambers take
   E6M3's second treatment.

3. THE LEVEL WAS STILL A GRID.  Orientation variety was 5 of 36 bins at the 0th
   percentile while chamfer fraction sat above the corpus maximum, because every
   cut corner was a 45-degree chamfer.  ``bloodmap.vocabulary.arc`` now exists
   with parameters mined from 1473 segmented-arc chains across 41 of 42 campaign
   maps: 7-8 segments, 15-30 degrees a segment, segments about one player width.
   The planter, the chancel, two courtyard corners, two crypt-hall corners and
   two gallery corners are arcs at those parameters instead of chamfers.

Four viewpoints now declare an upward pitch.  A camera locked level cannot
review a ceiling, which is how a pilot that spent a whole iteration on ceiling
heights never actually looked at one.
"""

from __future__ import annotations

from math import cos, radians, sin

from bloodmap.authoring_loop import (
    AuthoredAssembly,
    AuthoredIntent,
    AuthoredTransition,
    Candidate,
    ProbeRequest,
)
from bloodmap.doors import xsector_direct_use, xsector_remote_rx, z_motion_endpoints
from bloodmap.decoration import DECORATION, height_range, is_confident_size
from bloodmap.mechanism import sliding_gate
from bloodmap.placement import leaf_repeat, repeat_to_fit
from bloodmap.prefab import alcove_run, breakable
from bloodmap.texture_align import (
    align_wall_runs, align_wall_textures, sprite_tile_extents, wall_art_sizes)
from bloodmap.item_display import sprite_appearance
from bloodmap.lightbomb import light_bomb, lights_in
from bloodmap.lighting import (
    LIGHT_TILES, flicker_lit_sectors, match_corpus_shade,
    ripple_underwater_sectors, shade_walls_directionally)
from math import hypot

from bloodmap.planar_layout import PlanarLayout
from bloodmap.slope import SlopeSpec
from bloodmap.viewpoints import ViewpointSpec
from bloodmap.vocabulary import Anchor, arc_through, outline, recess, staircase

U = 384          # one player body width
PH = 0x1600      # 5632, one player standing height


def P(x: float, y: float) -> tuple[int, int]:
    return (int(round(x * U)), int(round(y * U)))


def R(x0: float, y0: float, x1: float, y1: float) -> list[tuple[int, int]]:
    return [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)]


def poly(*points: tuple[float, float]) -> list[tuple[int, int]]:
    """Free-form outline; must wind the same way R does."""
    return [P(x, y) for x, y in points]


# --- vertical plan, set from corpus percentiles for each footprint ---------
#
# Heights are stated in player heights and then snapped to the texture grid.
#
# A player height is 0x1600 = 5632 z units, which is 1024 x 5.5, so every odd
# multiple of it lands halfway between texture rows. This level used to state
# every ceiling as a whole number of player heights, and the result was that 68%
# of its walls could not tile: the seam had nowhere to go but across the middle.
#
# Blood does not size rooms in player heights. Its wall tiles are 128 pixels and
# it leaves y_repeat at 8 on 98% of one-sided walls, so one texture repeat is
# 32768 z units -- and the campaign's first quartile room height is exactly
# 32768, with a median of 33280. A typical Blood room is one wall texture tall.
# 95% of its sector heights are multiples of 1024 and 60% of 4096, against 53%
# and 16% here.
#
# So the author still says "six player heights", which is the readable unit, and
# `tex` puts it on the grid Blood builds on. The largest correction is 2048, a
# third of a player height, and several values were already exact.
TEXTURE_REPEAT = 32768          # a 128px wall tile at y_repeat 8
TEXTURE_GRID = TEXTURE_REPEAT // 8   # 4096, which is also the player step


def tex(player_heights: float) -> int:
    """A clear height in player heights, snapped to the wall-texture grid."""
    return max(TEXTURE_GRID, round(player_heights * PH / TEXTURE_GRID) * TEXTURE_GRID)


COURT = 8192
SKY = COURT - tex(16)              # 1100 player areas at p59 of comparable corpus sectors
LEDGE_CEIL = COURT - tex(6)
TUNNEL_CEIL = COURT - tex(3)       # deliberately tight; only 16 player areas
GATEHOUSE_CEIL = COURT - tex(5)
BED_FLOOR = COURT - 6144            # a raised planter; 1.1 player heights above the courtyard
NAVE_CEIL = COURT - tex(10)
AISLE_CEIL = COURT - tex(6)
APSE_FLOOR = COURT - 6144           # raised out of step range, reached by its own stair
APSE_CEIL = APSE_FLOOR - tex(8)

CRYPT_STEP = 3072
CRYPT_FLOOR = COURT + 4 * CRYPT_STEP
CRYPT_CEIL = CRYPT_FLOOR - tex(5)        # a vaulted hall, not a crawlspace
CHAMBER_CEIL = CRYPT_FLOOR - tex(3)      # cells, kept low on the E6M3 precedent
# The ossuary and the panel that hides it stand clear of the cells, because a
# rotating grille has to fit in the opening it turns in. Blood draws its fence
# tile between 3.64 and 12.36 player heights and never below; at the cells' 2.91
# the grille had to be shrunk to a size the game never uses, and it filled the
# doorway top to bottom with no jamb left over. tex(4) is 4.36, which is where
# the campaign draws that fence three times.
OSSUARY_CEIL = CRYPT_FLOOR - tex(4)
CISTERN_FLOOR = CRYPT_FLOOR + 2048

GAL_STEP = 4096                     # the corpus rise, and the player step exactly
GALLERY_FLOOR = COURT - 3 * GAL_STEP
ARCH_CEIL = GALLERY_FLOOR - tex(4)       # still a third of what it opens onto
GALLERY_CEIL = GALLERY_FLOOR - tex(12)
EXIT_CEIL = GALLERY_FLOOR - tex(8)

SWITCH_HEIGHT = 2.18
SWITCH_OFFSET = 0.12

# --- material vocabulary (inherited from v2) -------------------------------
APPROACH_TILES = dict(wall_picnum=427, floor_picnum=270, ceiling_picnum=285)
#: The first of the sixteen panels Blood wraps around a parallax sky. Every
#: outdoor sector in the level uses this one, because a run that is not sixteen
#: sky tiles renders whatever art happens to follow.
SKY_PANEL = 2500

COURT_TILES = dict(wall_picnum=110, floor_picnum=2448, ceiling_picnum=SKY_PANEL)
BED_TILES = dict(wall_picnum=110, floor_picnum=270, ceiling_picnum=2500)
NAVE_TILES = dict(wall_picnum=5, floor_picnum=294, ceiling_picnum=454)
AISLE_TILES = dict(wall_picnum=80, floor_picnum=294, ceiling_picnum=285)
APSE_TILES = dict(wall_picnum=5, floor_picnum=44, ceiling_picnum=4)
# E6M3 finishes its crypt-scale interiors with wall 194 over floor 568 under
# ceiling 67 (12 sectors, median 42 player areas) and ceiling 255 (24 sectors,
# median 19).  Tile 1097 is a cell finish: 26 of its 31 corpus occurrences put
# it on all three surfaces, at a median of 8 player areas and 2.91 player
# heights, so it stays on the one chamber that is actually that size.
CRYPT_HALL_TILES = dict(wall_picnum=194, floor_picnum=568, ceiling_picnum=67)
CRYPT_STAIR_TILES = dict(wall_picnum=194, floor_picnum=568, ceiling_picnum=255)
CRYPT_CELL_TILES = dict(wall_picnum=1097, floor_picnum=1097, ceiling_picnum=255)
CRYPT_CHAMBER_TILES = dict(wall_picnum=194, floor_picnum=255, ceiling_picnum=255)
PLINTH_TILES = dict(wall_picnum=194, floor_picnum=452, ceiling_picnum=67)
CRYPT_TILES = CRYPT_HALL_TILES
ARCH_TILES = dict(wall_picnum=427, floor_picnum=2448, ceiling_picnum=285)
GALLERY_TILES = dict(wall_picnum=91, floor_picnum=44, ceiling_picnum=455)
EXIT_TILES = dict(wall_picnum=194, floor_picnum=290, ceiling_picnum=296)

# A door face belongs to the door sector, not to the wall facing it. A Z-door is
# a slab: when it is shut its sector has no height, so the whole wall from the
# doorway up to the room's ceiling is one band. Painting that band with the door
# tile stacks the door two or three times up the wall -- which is what this level
# used to do, most visibly over the exit and the chapel door.
#
# Blood does not. On walls facing a type-600 door with a band of more than two
# repeats, the wall wears the *room's* tile 77% of the time and the door's only
# 35%. The door regions below still paint their own walls with these tiles, so
# the doorway still reads as a door from inside it.
#: How far each leaf of the crypt gate slides, and therefore how wide a leaf may
#: be: a gate leaf that travels less than its own width leaves the rest of itself
#: across the opening. Two units is half the four-unit doorway, so the two leaves
#: meet in the middle when shut and stand clear of it when open.
#: How many rooms in this level are wired as secrets. Kept in one place because
#: the count is declared to the engine separately from the rooms themselves, and
#: the two drifting apart is a level that says "1 of 3" forever.
SECRETS = 3

GATE_TRAVEL = 2 * 384

DOOR_FACE = 22
#: What the inside of a door frame is made of. The door itself is `door_face`,
#: which the compiler puts on the portals; these are the two solid cheeks.
JAMB_TILE = 449

#: A window is a two-sided wall drawn as a masked middle section: cstat
#: block(1) + masked(16) + hitscan(64), with the surface on `over_picnum`. 523
#: campaign walls carry the masked bit.
WINDOW_CSTAT = 1 | 16 | 64

#: Tile 266 is the campaign's commonest by a factor of four -- 232 of 523 -- and
#: it is *frosted glass*: 0% of its pixels are transparent. Perfect for a window
#: in a wall you are not meant to see through, and useless for one you are. The
#: belfry got it first and looked at a grey pane.
#:
#: 330 is 78% transparent, 58 is 55%, 502 is 41%. A bar grate you can see the
#: sky through wants one of those.
WINDOW_GLASS = 266
#: 463: vertical bars, 40% transparent, 54 campaign uses. 330 is 78%
#: transparent but reads as a thicket rather than a grate at this size.
WINDOW_GRATE = 463
KEYED_FACE = 495
REMOTE_FACE = 200
#: The screen tile; kWallGib walls in the campaign carry 2453, 179, 20 and 1665.
GIB_FACE = 2453

CH_CRYPT_GATE = 100
CH_SECRET = 102
CH_BREACH = 103        # the cracked crypt wall and the charges behind it
CH_CLOISTER = 104      # the cloister gate, pushed from either side

# --- water --------------------------------------------------------------
# Blood joins a pool to the volume under it with a marker pair: kMarkerUpWater
# in the pool and kMarkerLowWater in the sunk sector, matched on XSPRITE.data1.
# 191 such pairs across 24 of the 43 maps, and 152 of them pair sectors that are
# *congruent but somewhere else entirely* -- the underwater room is a copy of the
# pool's footprint parked in free map space, which is how Blood gets a dive
# without stacking geometry. The lower sector carries Underwater; the upper one
# does not. Their volumes run a median 8.7 player heights deep.
WATER_LINK_WELL = 1
WATER_LINK_CRYPT = 2
WELL_SURFACE = COURT + 2048     # the water line, a little below the courtyard

# The volume runs a median 8.7 player heights deep in the campaign, and its
# ceiling is the underside of the surface you dived through.
SUNK_CEIL = WELL_SURFACE
SUNK_FLOOR = SUNK_CEIL + tex(9)

# Water tiles are a convention this level had wrong. 2915 is the campaign's
# water surface: it is the *floor* of 96 pool sectors and the *ceiling* of 99
# underwater ones, because it is the same surface seen from each side. 1120 is
# the same idea (52 and 65). The bottom is ordinary ground -- 358 is its
# commonest floor -- and the walls are rock, 2490 and 449 leading.
WATER_SURFACE_TILE = 2915
SUNK_TILES = dict(wall_picnum=449, floor_picnum=358, ceiling_picnum=67)
SUNK_UNDER_POOL = dict(wall_picnum=449, floor_picnum=358,
                       ceiling_picnum=WATER_SURFACE_TILE)

# Every pool in this level dives into the same underwater place, so every pool
# uses the same translation to get there. That is what makes the geography hold:
# two mouths 33 player widths apart on the surface come out 33 player widths
# apart below, and the swim between them is a real distance rather than a hop
# between two shafts parked side by side.
#
# The campaign is looser than this -- of its 34 underwater regions serving more
# than one pool, 11 keep a single translation and 23 do not -- but the ones that
# do are the ones that read as a place, and the rule makes the swim come out at
# the right length by construction instead of by measurement. E1M6 does it at
# roughly (0, 0); E3M3 shares (81, 0) across 16 of its 36 links.
SUNK_TRANSLATION = (0, 56 * 384)


def dive(points):
    """The same mouth, moved into the flooded space by the level's translation."""
    return [(x + SUNK_TRANSLATION[0], y + SUNK_TRANSLATION[1]) for x, y in points]


# Mouths are not square holes. A well head is round and a crack in a floor is
# not anything in particular; the campaign's pools are whatever shape the room
# wanted. The sunk copy is generated from the same outline, so the two cannot
# drift apart.
WELL_MOUTH = poly((15, 20), (17, 20), (18, 21), (18, 23), (17, 24), (15, 24),
                  (14, 23), (14, 21))
CRYPT_MOUTH = poly((24, 53), (25, 52), (27, 52), (28, 54), (27, 56), (25, 55.5),
                   (24.5, 54.5))
CH_EXIT = 4

# --- decoration, sized from the campaign rather than from a wish ------------
# Build draws a sprite at tile pixels * repeat * 4 world units, so a height in
# player heights does determine a repeat. The mistake this file used to make was
# supposing the height was the author's to choose.
#
# It is not. Across the 3,159 visible decorations in the campaign, 60% are drawn
# at y_repeat 64 -- the tile's natural size -- and most tiles are never resized
# at all: tile 641 is 5.82 player heights in every one of its 71 uses, and 1044
# is never below 5.09. Every decoration in this level used to sit below the
# smallest size Blood ever draws it at, several of them by a factor of five,
# and the same tile appeared at four or five different sizes in one level.
#
# So the canonical size wins wherever the campaign is settled on one, and where
# it genuinely varies the requested height is clamped into the range the game
# actually uses. `player_heights` survives as a preference, not a decision.
ART_SIZE = {
    506: (12, 43), 2542: (58, 58), 2540: (58, 58), 2545: (58, 58),
    1044: (128, 128), 641: (15, 128), 660: (22, 32), 664: (11, 126),
    68: (64, 16), 1701: (30, 119), 795: (32, 32),
    915: (50, 88), 510: (8, 32),
    # the garden: a bush, four trees, a statue and an urn
    599: (63, 53), 541: (158, 199), 542: (96, 183), 543: (105, 162),
    547: (76, 159), 536: (36, 110), 537: (24, 50),
    # under water: bubbles, seaweed, and the gill beast
    668: (20, 128), 546: (61, 47), 641: (15, 128), 1570: (63, 96),
}


def _repeat(picnum: int, player_heights: float, *, aspect: float = 1.0) -> dict[str, int]:
    """Repeats for this tile at a height the campaign would recognise."""
    if is_confident_size(picnum):
        y_repeat = DECORATION[picnum]["y_repeat"]
    else:
        span = height_range(picnum)
        if span is not None:
            player_heights = max(span[0], min(span[1], player_heights))
        _width, height = ART_SIZE[picnum]
        y_repeat = max(4, min(255, round(player_heights * PH / (height * 4))))
    return {"y_repeat": y_repeat, "x_repeat": max(4, min(255, round(y_repeat * aspect)))}


def decor(picnum: int, cstat: int, player_heights: float, *, aspect: float = 1.0,
          shade: int = -8) -> dict[str, int]:
    return {"type": 0, "picnum": picnum, "cstat": cstat, "shade": shade,
            **_repeat(picnum, player_heights, aspect=aspect)}


# `shades` and `sky_shades` are gone. There were fifty-nine of the first and
# fourteen of the second, each a hand-picked number saying how dark one room
# should be relative to the others -- seventy-three judgements, none checkable,
# and every one of them something the author had to hold in their head while
# describing a building.
#
# They are now derived. `bloodmap.lighting.derived_shade` reads them off what
# the region already declares -- open to the sky or not, and how big its floor
# is -- because that is what accounts for the variation in the campaign's own
# 13,649 playable sectors: roofed 32, open 16, a hall seven brighter than a
# room. The remaining difference, a room with a flame in it against one without,
# is not an authoring decision at all: `bloodmap.lightbomb` derives it by
# casting the light out of the flame and seeing where it lands.
#
# A number can still be passed where one is genuinely a decision -- a stair's
# shade ramp is one -- and an explicit value is never overwritten.


def _z_door(floor_z: int, open_ceiling_z: int, *, interaction: str,
            rx: int | None = None, key: int | None = None) -> dict[str, int]:
    behavior = {"busy_time_a": 5, "busy_time_b": 5,
                **z_motion_endpoints(floor_z, open_ceiling_z)}
    if interaction == "direct":
        behavior.update(xsector_direct_use(key=key))
    elif interaction == "remote":
        behavior.update(xsector_remote_rx(int(rx)))
    else:
        raise ValueError(interaction)
    return behavior


SWITCH = dict(type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, shade=-8)

# --- population and ambience, at the campaign's own forms --------------------
# Every field below is the modal authored value for that type across the 43
# campaign maps, so a cultist here is drawn and stated exactly as a cultist in
# E2M2 is. Nothing is invented; the only judgement is which type goes where.
DUDE = {
    201: dict(type=201, picnum=2820, cstat=384, x_repeat=40, y_repeat=40, status=6, shade=-8),
    202: dict(type=202, picnum=2825, cstat=384, x_repeat=40, y_repeat=40, status=6, shade=-8),
    203: dict(type=203, picnum=1170, cstat=384, x_repeat=40, y_repeat=40, status=6, shade=-8),
    206: dict(type=206, picnum=1470, cstat=384, x_repeat=40, y_repeat=40, status=6, shade=-8),
    211: dict(type=211, picnum=1270, cstat=384, x_repeat=40, y_repeat=40, status=6, shade=-8),
    # The Gill Beast, which is the campaign's underwater dude: 101 of its 101
    # sprites stand in water. Note the repeat -- 48, where every other dude here
    # is 40.
    217: dict(type=217, picnum=1570, cstat=384, x_repeat=48, y_repeat=48, status=6, shade=-8),
}
PICKUP = {
    109: dict(type=109, picnum=2169, cstat=128, x_repeat=40, y_repeat=40, status=3),
    68: dict(type=68, picnum=812, cstat=128, x_repeat=48, y_repeat=48, status=3),
    76: dict(type=76, picnum=816, cstat=128, x_repeat=48, y_repeat=48, status=3),
    72: dict(type=72, picnum=817, cstat=128, x_repeat=48, y_repeat=48, status=3),
    63: dict(type=63, picnum=809, cstat=384, x_repeat=48, y_repeat=48, status=3),
    41: dict(type=41, picnum=559, cstat=128, x_repeat=48, y_repeat=48, status=3),
    42: dict(type=42, picnum=558, cstat=128, x_repeat=48, y_repeat=48, status=3),
    107: dict(type=107, picnum=519, cstat=128, x_repeat=48, y_repeat=48, status=3),
}

# Ambient SFX: 1,778 of them across 41 of the 43 maps, and this level had none.
# ambProcess fades the sound between data1 and data2 by distance, plays the
# resource named by data3 at volume data4, and does nothing at all unless state
# is set. ambInit assigns the channel, so owner stays -1 as the corpus leaves it.
def ambience(sound: int, *, near: int = 75, far: int = 150, volume: int = 50) -> dict:
    return dict(type=710, picnum=2521, cstat=32896, status=12,
                x_repeat=64, y_repeat=64, shade=-128,
                behavior={"state": 1, "data_1": near, "data_2": far,
                          "data_3": sound, "data_4": volume})


def sector_sfx(sound: int) -> dict:
    """Sector SFX (709): 1,247 in 42 maps, resting at state 0 on statnum 0."""
    return dict(type=709, picnum=2520, cstat=32896, status=0,
                x_repeat=64, y_repeat=64, shade=-128,
                behavior={"state": 0, "data_1": sound, "data_3": sound})

# Outlines.  Every 45-degree cut below is a real chamfer, which is what puts
# diagonal wall length and orientation variety into the level.
LEDGE = poly((-8, 18), (-2, 18), (-2, 26), (-8, 26), (-10, 24), (-10, 20))
GATEHOUSE = poly((6, 20), (10, 17), (10, 27), (6, 24))
# Two of the courtyard's four cut corners become segmented arcs at the corpus
# parameters; the other two stay chamfers, because originals mix them.
COURTYARD = outline(
    [P(14, 4), P(46, 4)],
    arc_through(P(46, 4), P(52, 7), bulge=1.2 * U, segments=6),
    [P(52, 38), P(50, 40), P(15, 40)],
    arc_through(P(15, 40), P(10, 37), bulge=1.2 * U, segments=6),
    [P(10, 8)],
)
CHAPEL_SHELL = poly((26, 12), (42, 12), (44, 14), (44, 32), (42, 34), (26, 34), (24, 32), (24, 14))
# A round planter rather than an octagonal one: sixteen segments of 22.5
# degrees, which is the corpus median turn, and a chord of 0.68 player widths.
GARDEN_BED = [
    (int(round(16.5 * U + 3.5 * U * cos(radians(-90 + 22.5 * index)))),
     int(round(12.0 * U + 3.5 * U * sin(radians(-90 + 22.5 * index)))))
    for index in range(16)
]
NAVE = poly((28, 18), (36, 18), (38, 20), (38, 26), (36, 28), (28, 28), (26, 26), (26, 20))
AISLE_SOUTH = poly((30, 14), (34, 14), (36, 16), (36, 18), (28, 18), (28, 16))
AISLE_NORTH = poly((28, 28), (36, 28), (36, 30), (34, 32), (30, 32), (28, 30))
# The chancel keeps its radial east end and gains a west wing beside the
# three-tread chancel stair, so half the nave/chancel edge stays a direct
# opening: that opening is the level's first overlook inside a building.
APSE_ARC = arc_through(P(41, 20), P(41, 26), bulge=1.6 * U, segments=8)
APSE = outline(APSE_ARC, [P(38, 26), P(38, 23), P(41, 23)])
CRYPT_HALL = outline(
    [P(24, 50), P(39, 50)],
    arc_through(P(39, 50), P(42, 52), bulge=0.8 * U, segments=5),
    [P(42, 58), P(40, 60), P(25, 60)],
    arc_through(P(25, 60), P(22, 58), bulge=0.8 * U, segments=5),
    [P(22, 52)],
)
RELIQUARY = poly((18, 52), (22, 52), (22, 58), (18, 58), (16, 56), (16, 54))
CISTERN = poly((26, 60), (34, 60), (34, 64), (32, 66), (28, 66), (26, 64))
OSSUARY = poly((44, 50), (50, 50), (52, 52), (52, 58), (50, 60), (44, 60))
# An ambulatory running behind the crypt's south-west corner, from the reliquary
# down and back east into the cistern. It is the shape a crypt of this plan
# already implies -- a walk around the tomb rather than a walk up to it.
AMBULATORY = poly((18, 58), (22, 58), (22, 61), (26, 61), (26, 64), (18, 64))
GALLERY = outline(
    [P(64, 10), P(73, 10)],
    arc_through(P(73, 10), P(76, 12), bulge=0.8 * U, segments=5),
    [P(76, 39)],
    arc_through(P(76, 39), P(74, 42), bulge=0.8 * U, segments=5),
    [P(64, 42), P(62, 40), P(62, 12)],
)
EXIT_HALL = poly((78, 18), (86, 18), (88, 20), (88, 28), (86, 30), (78, 30))
# The graveyard: seen from the belfry window and never walked in. Cut corners so
# it does not read as a box from above.
#: The tower's vertical plan, and the graveyard's with it.
#:
#: `max_step` for Blood is 4096, so 24 steps of it climbs 17.5 player heights --
#: near the campaign's longest run of 25.
#:
#: The graveyard's ceiling is set by the belfry window, and setting it wrong
#: closes the window. Build shows a masked portal only between the lower of the
#: two ceilings and the higher of the two floors, so tex(1) of clearance over
#: the belfry floor left the view from the tower a 4096 letterbox at ankle
#: height. tex(4) opens it to 2.9 player heights, which is a window.
#:
#: That puts the graveyard at 20.4 player heights, past the campaign's outdoor
#: q3 of 17.1 and well inside its p95 of 31.2. Tall, and it should be: it is a
#: walled yard at the foot of a bell tower, and the tower is why the wall is
#: that high.
TOWER_STEP = 4096
TOWER_STEPS = 24
TOWER_RISE = TOWER_STEP * TOWER_STEPS
BELFRY_FLOOR = COURT - TOWER_RISE
GRAVEYARD_SKY = BELFRY_FLOOR - tex(4)

#: South edge at -57, not -56. The belfry's north wall is at -56, and while the
#: graveyard came up to the same line the tower had no thickness at its window:
#: the two sectors were neighbours along the whole wall, and the stone either
#: side of the opening had to be two masked walls standing in for masonry. A
#: unit of clearance makes the tower wall 384 of solid stone and turns the
#: window into an embrasure with a reveal, which is what a window in a wall that
#: thick looks like.
GRAVEYARD = poly((22, -80), (50, -80), (52, -78), (52, -59), (50, -57),
                 (22, -57), (20, -59), (20, -78))

PLINTH = R(34, 53, 38, 57)
PLINTH_EDGES = (
    ("s", (34, 53), (38, 53)), ("e", (38, 53), (38, 57)),
    ("n", (38, 57), (34, 57)), ("w", (34, 57), (34, 53)),
)

# One connection per arc segment: the planter's edges are now generated from
# its own outline rather than restated by hand, so they cannot drift apart.
BED_EDGES = tuple(
    (f"seg{index:02d}", GARDEN_BED[index], GARDEN_BED[(index + 1) % len(GARDEN_BED)])
    for index in range(len(GARDEN_BED))
)


_ALIGNMENT: dict = {}
_LIGHTING: dict = {}
_MARKERS: dict = {}


# =====================================================================
# The water garden
# =====================================================================
#
# A monastery's hortus conclusus: an enclosed garden, walked to from the chapter
# house along a covered passage, dropping into a sunken lawn with a hedge maze, a
# stepped shrine at its head, and a cascade falling off the rock shelf that
# closes the north end. Behind the falling water there is a grotto.
#
# It is here to be the level's one large open space. Everything before it is
# rooms, and this is somewhere to stand and look, which the map did not have.
#
# Three things in it were not previously buildable, and each is a corpus fact
# rather than a flourish:
#
# *Slopes.* Every one of the 43 campaign maps slopes sectors -- the thinnest 5,
# the median 59 -- and this level had none in 112. The porch here carries a real
# pitched roof: two sectors meeting along a ridge, which is not a stylistic
# choice but the only way to build one. A slope hinges on its sector's first
# wall, and a sector has exactly one of those.
#
# *Scrolling water.* An XWALL with pan_y_velocity set and pan_always on. The
# campaign's waterfalls are tile 1005 at -80 in E2M7 and -75 elsewhere, and the
# falling sheet is a masked two-sided wall, so it can be walked through.
#
# *Foliage.* Tiles 541, 542, 543, 547 and 599 -- four trees and a bush. The first
# search for these turned up 2519 to 2529, which appear in twenty maps apiece and
# looked like strong evidence until they were rendered: they are the editor's own
# gizmos, the word "sound" and the numbers one to eight. That is the third time a
# tile has been chosen from usage counts and turned out to be a label, so these
# were looked at before they were placed.

GARDEN_LAWN = COURT + 8192              # two steps down from the cloister level
GARDEN_POOL = GARDEN_LAWN + 6144        # wading depth in the basin
GARDEN_SHELF = GARDEN_LAWN - tex(5)     # the rock the cascade falls from
# Not tex(28). That was 29 player heights of blank stone standing round a lawn,
# and it made everything in the lawn look like a model of itself: a three-player
# tree against a twenty-nine-player wall is a shrub. Every measurement said the
# garden was fine -- its area is ordinary for the campaign, its sprite density
# sits on the campaign median, its height-over-root-area was *below* the
# campaign median -- because all of them are ratios, and the thing the eye was
# reading is the absolute number. The campaign's outdoor sectors run 9.5 to 17.1
# player heights between quartiles; 29 is its 93rd percentile.
GARDEN_SKY = COURT - tex(12)
HEDGE_LIFT = 6144                       # over a 4096 step, so a hedge is a wall
CASCADE_TILE = 1005                     # the campaign's falling water
WATER_TILE = 2915                       # nine frames of rippling blue
GARDEN_GROUND = 270                     # the campaign's commonest outdoor ground
HEDGE_SOIL = 568

#: Falling water: masked so it draws as a sheet and not blocking so you can step
#: through it. `pan_always` is the part that matters -- without it the pan runs
#: only while the wall's XWALL is busy, and a wall nothing ever triggers is never
#: busy, so the fall would hang perfectly still.
CASCADE_CSTAT = 16
CASCADE_PAN = {"pan_x_velocity": 0, "pan_y_velocity": -80, "pan_always": 1}


#: Bushes along the crown, spaced by their own width so the run closes up.
HEDGE_BUSH_STRIDE = U * 1.4


def _hedge(layout, tag, outline):
    """One length of hedge: a planter too tall to step onto, grown over.

    A hedge cannot be sprites alone. A bush sprite blocks where it stands and
    nowhere else, so a row of them is a row of posts with gaps between: the
    player walks the maze by squeezing past the shrubs and the whole thing
    collapses. The wall has to be the floor. This lifts a sector 6144, which is
    over the 4096 the player can step, and stands the foliage on top of it.

    ``outline`` is a polygon, not a rectangle, and that is the point. The maze
    was thirteen separate boxes, because two boxes that meet along an edge give
    the compiler two coincident same-direction segments it cannot pair -- so
    each was inset by 48 and the maze had a gap at every junction you could see
    daylight through. A hedge that turns a corner is *one* sector with a corner
    in it. Thirteen boxes became five runs, the gaps closed, and thirteen
    dead-end sectors became five.
    """
    rid = "region:hedge_%s" % tag
    layout.carve_hole("region:garden_court", outline)
    layout.add_region(rid, outline, role="detail",
                      ceiling_z=GARDEN_SKY, floor_z=GARDEN_LAWN - HEDGE_LIFT,
                      parallax_ceiling=True, wall_picnum=HEDGE_SOIL,
                      floor_picnum=HEDGE_SOIL, ceiling_picnum=SKY_PANEL,
                      intent={"purpose": "hedge %s of the garden maze" % tag,
                              "classification": "OPTIONAL"})
    count = len(outline)
    for index in range(count):
        a, b = outline[index], outline[(index + 1) % count]
        layout.add_connection("connection:hedge_%s_%02d" % (tag, index),
                              "region:garden_court", rid, a1=a, a2=b, min_width=256)
    # Foliage along every edge, so a run that turns a corner is planted round it.
    placed = 0
    for index in range(count):
        (ax, ay), (bx, by) = outline[index], outline[(index + 1) % count]
        span = hypot(bx - ax, by - ay)
        steps = max(1, int(round(span / HEDGE_BUSH_STRIDE)))
        for step in range(steps):
            t = (step + 0.5) / steps
            layout.add_sprite(
                "hedge_%s_bush_%02d" % (tag, placed), rid,
                x=int(ax + (bx - ax) * t), y=int(ay + (by - ay) * t),
                z=GARDEN_LAWN - HEDGE_LIFT, seat="floor",
                **decor(599, 1 | 128 | 256, 2.4, shade=6))
            placed += 1


#: The maze, as five runs of hedge rather than thirteen boxes. A grid of four
#: cells by four over x 56..72, y -60..-44, with one way in at the south and one
#: out at the north, a winding route between them and three dead ends.
#:
#: Each run is a single rectilinear polygon: the two outer C-shapes, the S that
#: divides the west half, the L that divides the east, and one free-standing
#: stub. They are drawn so that no two of them touch, which is what lets each be
#: a sector in its own right.
GARDEN_MAZE = (
    # the west outer wall, turning east at both ends; the gap is the entrance
    ("west", poly((56, -60), (64, -60), (64, -59), (57, -59), (57, -45),
                  (62, -45), (62, -44), (56, -44))),
    # the east outer wall, likewise; the gap at the north is the way out
    ("east", poly((68, -60), (72, -60), (72, -44), (66, -44), (66, -45),
                  (71, -45), (71, -59), (68, -59))),
    # the S that makes the route double back rather than spiral
    # Stops at -45.5 rather than -45: the west run's south arm is at -45, and two
    # hedges that meet along a line are two holes in the lawn sharing an edge,
    # which the compiler cannot pair. Half a unit is 192, and the player is 384.
    ("inner_w", poly((65, -59), (66, -59), (66, -55), (60, -55), (60, -45.5),
                     (59, -45.5), (59, -56), (65, -56))),
    # the L that closes the east half off from the exit
    ("inner_e", poly((62, -52), (69, -52), (69, -47), (68, -47), (68, -51),
                     (62, -51))),
    # and the stub that makes the last cell a dead end rather than a through way
    ("stub", R(62, -48, 66, -47)),
)


def water_garden(layout):
    """Build the garden and tie it to the chapter house."""

    # -- the way in -----------------------------------------------------------
    #
    # The passage climbs nothing and turns nowhere. It is there so the garden is
    # arrived at rather than merely adjacent to the chapter house, and so the
    # sky arrives with it.
    # x 52..56, not 54..58. The chapter house is chamfered at its north-east
    # corner -- (56,-14) then (58,-12) -- so its north wall stops at 56, and a
    # doorway declared out to 58 had its eastern half standing over nothing.
    # The compiler said so: four units asked for, two realized.
    layout.add_region("region:garden_passage", R(52, -26, 56, -14), role="gateway",
                      ceiling_z=COURT - tex(4), floor_z=COURT,
                      wall_picnum=110, floor_picnum=538, ceiling_picnum=416,
                      intent={"purpose": "covered passage from the chapter house "
                                         "out to the garden",
                              "classification": "REQUIRED"})
    # `all_atomic` because the chapter house's north wall already carries a
    # vertex at x=56, so the doorway lands on two atomic segments rather than
    # one and the default policy would pair only the first -- a four-unit
    # opening realized two units wide, with the other half left as blank stone.
    layout.add_connection("connection:chapter_garden", "region:chapter_house",
                          "region:garden_passage",
                          a1=P(52, -14), a2=P(56, -14), min_width=1536,
                          attach_policy="all_atomic")

    # The porch roof. One sector cannot pitch two ways: a slope hinges on
    # wall[wallptr] and there is exactly one of those, so a ridge is where two
    # sectors meet. Each half hinges on its own outer edge and rises by the same
    # amount over the same depth, which is what makes the join a ridge rather
    # than a step in the roof.
    PORCH_EAVE = COURT - tex(4)
    PORCH_RISE = -tex(3)                 # z points down, so a lift is negative
    for tag, box, hinge in (
        ("w", R(52, -32, 57, -26), (P(52, -26), P(52, -32))),
        ("e", R(57, -32, 62, -26), (P(62, -32), P(62, -26))),
    ):
        layout.add_region("region:garden_porch_%s" % tag, box, role="gateway",
                          ceiling_z=PORCH_EAVE, floor_z=COURT,
                          ceiling_slope=SlopeSpec(hinge=hinge, rise_z=PORCH_RISE),
                          wall_picnum=110, floor_picnum=538, ceiling_picnum=416,
                          intent={"purpose": "%s half of the garden porch, pitched "
                                             "to a ridge" % tag,
                                  "classification": "REQUIRED"})
    layout.add_connection("connection:porch_ridge", "region:garden_porch_w",
                          "region:garden_porch_e",
                          a1=P(57, -32), a2=P(57, -26), min_width=1536)
    layout.add_connection("connection:passage_porch", "region:garden_passage",
                          "region:garden_porch_w", a1=P(52, -26), a2=P(56, -26),
                          min_width=1536)

    # -- the lawn -------------------------------------------------------------
    # Notched along its north edge rather than holed, because the basin reaches
    # that edge and a carved hole has to be strictly inside the region it is cut
    # from. The notch is the basin's footprint.
    # West edge at 52, not 50: the graveyard reaches x=52 at these latitudes and
    # two regions may not share ground without saying why.
    # West edge at 54, not 52. The graveyard's east wall is at 52, and while the
    # lawn came up to the same line the two grounds met along it -- so the wall
    # dividing them had no thickness at all, and everything about it had to be
    # faked with masked two-sided walls. Standing them two units apart leaves
    # 768 of solid masonry, which is what the precinct wall of a monastery is,
    # and every face of it is then an ordinary one-sided wall with stone behind.
    LAWN = poly((54, -68), (68, -68), (68, -62), (82, -62), (82, -68),
                (88, -68), (88, -36), (54, -36))
    layout.add_region("region:garden_court", LAWN, role="exterior",
                      ceiling_z=GARDEN_SKY, floor_z=GARDEN_LAWN,
                      parallax_ceiling=True,
                      wall_picnum=110, floor_picnum=GARDEN_GROUND,
                      ceiling_picnum=SKY_PANEL,
                      intent={"purpose": "the sunken garden lawn, the level's one "
                                         "large open space",
                              "classification": "REQUIRED"})

    # Down into it. Two steps, because the lawn is two steps below the cloister
    # level and a garden you walk down into is enclosed in a way a flat one is not.
    garden_steps = staircase(
        layout, "stairs:garden",
        parallax_ceiling=True,   # outdoors: the sky tile means the sky
        # From x=54, because the lawn now starts there: the stair used to run
        # from 52 and its western two units came down onto the wall.
        base=Anchor("region:garden_porch_w", P(54, -32), P(57, -32)),
        total_rise=GARDEN_LAWN - COURT, step_rise=4096, tread=2 * U,
        clear_height=tex(12), base_floor_z=COURT,
        wall_picnum=110, floor_picnum=538, ceiling_picnum=SKY_PANEL,
        intent={"purpose": "steps from the porch down into the sunken lawn",
                "classification": "REQUIRED"})
    garden_steps.arrive_at("region:garden_court")

    # -- the maze -------------------------------------------------------------
    for tag, outline in GARDEN_MAZE:
        _hedge(layout, tag, outline)

    # -- the shrine ----------------------------------------------------------
    #
    # Three concentric steps with a statue on the top one. Built from sectors
    # rather than laid on the ground as a sprite, because a stepped mound is the
    # one thing in a garden the player can climb, and because E1M1's graveyard
    # taught the same lesson: the plot has to be raised or it reads as a marker
    # dropped on a field.
    SHRINE = (
        ("1", R(74, -56, 86, -44), 2048),
        ("2", R(76, -54, 84, -46), 4096),
        ("3", R(78, -52, 82, -48), 6144),
    )
    previous = "region:garden_court"
    for tag, box, lift in SHRINE:
        rid = "region:shrine_%s" % tag
        layout.carve_hole(previous, box)
        layout.add_region(rid, box, role="detail",
                          ceiling_z=GARDEN_SKY, floor_z=GARDEN_LAWN - lift,
                          parallax_ceiling=True,
                          wall_picnum=538, floor_picnum=538,
                          ceiling_picnum=SKY_PANEL,
                          intent={"purpose": "step %s of the garden shrine" % tag,
                                  "classification": "OPTIONAL"})
        for name, index in (("s", 0), ("e", 1), ("n", 2), ("w", 3)):
            layout.add_connection("connection:shrine_%s_%s" % (tag, name),
                                  previous, rid,
                                  a1=box[index], a2=box[(index + 1) % 4],
                                  min_width=384)
        previous = rid

    layout.add_sprite("shrine_statue", "region:shrine_3",
                      x=P(80, -50)[0], y=P(80, -50)[1],
                      z=GARDEN_LAWN - 6144, seat="floor", angle=1536,
                      **decor(536, 1 | 128 | 256, 3.75, shade=4))
    for tag, x, y in (("sw", 76.5, -53.5), ("se", 83.5, -53.5),
                      ("nw", 76.5, -46.5), ("ne", 83.5, -46.5)):
        layout.add_sprite("shrine_urn_%s" % tag, "region:shrine_2",
                          x=P(x, y)[0], y=P(x, y)[1], z=GARDEN_LAWN - 4096,
                          seat="floor", **decor(537, 1 | 128 | 256, 2.27, shade=8))

    # -- the cascade ---------------------------------------------------------
    #
    # A rock shelf five player heights above the lawn, a basin at its foot, and
    # the water falling between them on the two-sided wall that separates them.
    # A U, not a rectangle with a hole in it: the grotto opens south onto the
    # basin, so it takes a bite out of the shelf's edge rather than sitting
    # inside it.
    #
    # The bite is a unit wider than the grotto on all three rock sides. When the
    # two were flush the shelf and the grotto were neighbours along every one of
    # those edges, and six masked walls had to stand in for the rock between
    # them -- a plane with the shelf's tile on one face and the grotto's on the
    # other, and nothing in between. Standing them 384 apart leaves real stone
    # there, and every face of it is a one-sided wall.
    # The notch opens the full width of the basin, so the shelf meets only the
    # lawn along its foot and never overhangs the water. What is left between the
    # notch and the grotto -- two units either side, one at the back -- is
    # unclaimed solid rock, which is the point.
    SHELF = poly((66, -78), (84, -78), (84, -68), (82, -68), (82, -75),
                 (68, -75), (68, -68), (66, -68))
    layout.add_region("region:cascade_shelf", SHELF, role="exterior",
                      ceiling_z=GARDEN_SKY, floor_z=GARDEN_SHELF,
                      parallax_ceiling=True,
                      wall_picnum=110, floor_picnum=568, ceiling_picnum=SKY_PANEL, declared_zero_exit=True,
                      intent={"purpose": "the rock shelf the cascade falls from; "
                                         "seen, never stood on",
                              "classification": "OPTIONAL"})

    POOL = R(68, -68, 82, -62)
    layout.add_region("region:garden_pool", POOL, role="interior",
                      ceiling_z=GARDEN_SKY, floor_z=GARDEN_POOL,
                      parallax_ceiling=True,
                      wall_picnum=568, floor_picnum=WATER_TILE,
                      ceiling_picnum=SKY_PANEL,
                      intent={"purpose": "the basin the cascade falls into",
                              "classification": "OPTIONAL"})
    # Three sides onto the lawn; the fourth is the cascade.
    for name, a1, a2 in (("s", P(68, -62), P(82, -62)),
                         ("w", P(68, -68), P(68, -62)),
                         ("e", P(82, -62), P(82, -68))):
        layout.add_connection("connection:pool_%s" % name, "region:garden_court",
                              "region:garden_pool", a1=a1, a2=a2, min_width=768)

    # The grotto is a bite taken out of the shelf at basin level, so the cascade
    # falls across its mouth. Its ceiling is the shelf's floor: you are standing
    # inside the rock, under five player heights of it.
    GROTTO = R(70, -74, 80, -68)
    layout.add_region("region:cascade_grotto", GROTTO, role="secret", secret=True,
                      ceiling_z=GARDEN_SHELF, floor_z=GARDEN_POOL,
                      wall_picnum=568, floor_picnum=568, ceiling_picnum=568,
                      intent={"purpose": "a grotto behind the falling water",
                              "classification": "OPTIONAL"})

    # The sheet itself. A connection rather than a partition: `wall_behavior`
    # reaches an XWALL only through a connection, which is also right -- the
    # player walks through this wall.
    layout.add_connection("connection:cascade", "region:garden_pool",
                          "region:cascade_grotto",
                          a1=P(70, -68), a2=P(80, -68), min_width=1024,
                          face_cstat=CASCADE_CSTAT, face_picnum=CASCADE_TILE,
                          face_over_picnum=CASCADE_TILE, face_shade=-16,
                          wall_behavior=dict(CASCADE_PAN))

    # Rock. Every one of these is two regions that share ground and are not a way
    # through, and the compiler is right to demand each be named: an undeclared
    # coincident edge is how a wall goes missing. `opaque` is what makes them
    # stone rather than an invisible barrier -- Blood's solid two-sided wall is
    # the masked one, block plus masked plus hitscan, and without it the shelf
    # would be a five-storey drop the player could see straight through.
    # The graveyard used to be scenery: a walled field looked down on from the
    # belfry window and never entered. The garden's west wall is its east wall,
    # so a breach in it is the whole of what that takes, and it turns the tower
    # window from a view into a promise -- the better use of a window.
    #
    # A hole is not a breach. Deleting the wall for four units gave a doorway
    # with no doorway around it: two grounds meeting along a line, which is what
    # a *missing* wall looks like and not what a fallen one does. It was also
    # impassable in the direction that mattered. The lawn sits 8192 above the
    # graveyard and the player steps 4096, so the clean gap was a one-way drop --
    # fall into the graveyard, never climb out.
    #
    # Both faults have one answer. The wall did not vanish, it came down, and
    # what came down is still lying there: a bank of fallen masonry halfway
    # between the two floors, one step from either side. You climb the rubble to
    # get out. Blood has no rubble *sprite* -- its falling-rock and object-gib
    # tiles are corpses, barrels and icicles, not one of them stone -- so the
    # heap is built the way the graveyard's own plots are, out of sectors, with
    # the wall's tile lying on the floor of it.
    BREACH_FLOOR = COURT + 4096
    layout.add_region("region:garden_breach", R(52, -64, 54, -60), role="gateway",
                      ceiling_z=GRAVEYARD_SKY, floor_z=BREACH_FLOOR,
                      parallax_ceiling=True,
                      wall_picnum=110, floor_picnum=110, ceiling_picnum=SKY_PANEL,
                      intent={"purpose": "the fallen stretch of the graveyard wall, "
                                         "climbed over to reach the garden",
                              "classification": "OPTIONAL"})
    # Both mouths of the passage. Everything either side of them is now solid:
    # the wall's faces are one-sided walls with stone behind, so the collapse has
    # a jamb you walk between and a soffit you walk under, and none of it is a
    # masked wall pretending to be thick.
    layout.add_connection("connection:breach_graveyard", "region:garden_breach",
                          "region:graveyard", a1=P(52, -64), a2=P(52, -60),
                          min_width=1024)
    layout.add_connection("connection:breach_garden", "region:garden_breach",
                          "region:garden_court", a1=P(54, -60), a2=P(54, -64),
                          min_width=1024)
    # What came off the wall lies on both sides of it, because a wall falls
    # outward. These are the spill: mounds half a step high, standing clear of
    # the passage so neither of them narrows it.
    for tag, host, box, ground in (
        ("grave", "region:graveyard", R(49.5, -63.5, 51.5, -60.5), COURT),
        ("garden", "region:garden_court", R(54.5, -63.5, 56.5, -60.5), GARDEN_LAWN),
    ):
        rid = "region:breach_spill_%s" % tag
        layout.carve_hole(host, box)
        layout.add_region(rid, box, role="detail",
                          ceiling_z=GRAVEYARD_SKY, floor_z=ground - 2048,
                          parallax_ceiling=True,
                          wall_picnum=110, floor_picnum=110, ceiling_picnum=SKY_PANEL,
                          intent={"purpose": "masonry spilled from the fallen wall",
                                  "classification": "OPTIONAL"})
        for name, index in (("s", 0), ("e", 1), ("n", 2), ("w", 3)):
            layout.add_connection("connection:breach_spill_%s_%s" % (tag, name),
                                  host, rid,
                                  a1=box[index], a2=box[(index + 1) % 4], min_width=512)
    # Growing through it, because a wall that fell last week is a hole and a wall
    # that fell a century ago has a garden in it.
    for tag, x, y in (("a", 52.3, -60.5), ("b", 53.7, -63.5)):
        layout.add_sprite("breach_bush_%s" % tag, "region:garden_breach",
                          x=P(x, y)[0], y=P(x, y)[1], z=BREACH_FLOOR, seat="floor",
                          **decor(599, 1 | 128 | 256, 2.0, shade=6))
    # No graveyard entry here any more: with the lawn held back to x=54 the two
    # regions do not touch, and the wall between them is masonry rather than a
    # declaration about a shared line.
    # Where the shelf meets the garden it is a cliff, and a cliff is a portal.
    #
    # These were four masked walls apiece, which is what you build when you have
    # decided in advance that the answer to "these two must not connect" is a
    # wall. It is not: the shelf stands five player heights over the lawn and
    # the player climbs four thousand and ninety-six, so an open portal is
    # already impassable, and it shows what a wall cannot -- the rock face, the
    # lip of the shelf, and sky above it. The campaign masks 0.53% of its walls;
    # this level was masking 4%, nearly all of it copying a wall's own picnum
    # onto its over_picnum to fake solidity, which the campaign does 14 times in
    # 600.
    for tag, region_b, a1, a2 in (
        ("shelf_lawn_w", "region:garden_court", P(66, -68), P(68, -68)),
        ("shelf_lawn_e", "region:garden_court", P(82, -68), P(84, -68)),
    ):
        layout.add_connection("connection:garden_%s" % tag, "region:cascade_shelf",
                              region_b, a1=a1, a2=a2, min_width=768)

    # -- planting ------------------------------------------------------------
    #
    # Trees around the rim, where they frame the lawn without standing in it,
    # and never two of the same next to each other.
    # Heights are the campaign's own, not a guess at what a tree "should" be.
    # These were first authored at 2.8 to 3.4 player heights, on the reasoning
    # that a tree is about three times a person -- and every one of them read as
    # a sapling. Blood draws its trees at seven to nine: 541 median 8.48 over 8
    # sprites, 542 8.32 over 19, 543 7.36 over 12, 547 7.23 over 46.
    #
    # Nothing caught it, because `DECORATION` has no entry for any of these
    # tiles: it catalogues what the corpus files as decoration, and the campaign
    # files its trees elsewhere. A tile the table does not know is a tile with no
    # size discipline at all, so `_repeat` took the invented number whole.
    TREES = ((541, 8.5), (542, 8.3), (543, 7.4), (547, 7.2))
    RIM = (
        # x=55.5, not 53.5: 52 to 54 is the wall between garden and graveyard
        (55.5, -38.0), (55.5, -46.0), (55.5, -54.0), (55.5, -58.0),
        (56.0, -66.0), (62.0, -66.5), (86.0, -66.0),
        (86.5, -58.0), (86.5, -40.0), (74.0, -38.0), (64.0, -38.0),
    )
    for index, (x, y) in enumerate(RIM):
        picnum, height = TREES[index % len(TREES)]
        layout.add_sprite("garden_tree_%02d" % index, "region:garden_court",
                          x=P(x, y)[0], y=P(x, y)[1], z=GARDEN_LAWN, seat="floor",
                          **decor(picnum, 1 | 128 | 256, height, shade=10))


def make_layout() -> PlanarLayout:
    layout = PlanarLayout(name="monastery-v3", visibility=800,
                          tile_extents=sprite_tile_extents())
    # Every tile that might land on a floor or a ceiling, so the compiler can
    # hold them to Build's power-of-two rule.
    layout.flat_tile_sizes = wall_art_sizes()

    # ---- arrival -----------------------------------------------------------
    layout.add_region("region:ledge", LEDGE, role="start",
                      ceiling_z=LEDGE_CEIL, floor_z=COURT, **APPROACH_TILES,
                      intent={"purpose": "cliffside arrival ledge", "classification": "MANDATORY"})
    layout.add_region("region:gate_tunnel", R(-2, 21, 6, 23), role="gateway",
                      inherit_finish="both",
                      ceiling_z=TUNNEL_CEIL, floor_z=COURT, **APPROACH_TILES,
                      intent={"purpose": "constrained gate tunnel", "classification": "MANDATORY"})
    layout.add_region("region:gatehouse", GATEHOUSE, role="gateway",
                      ceiling_z=GATEHOUSE_CEIL, floor_z=COURT, **APPROACH_TILES,
                      intent={"purpose": "splayed covered gatehouse opening toward the courtyard",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:ledge_tunnel", "region:ledge", "region:gate_tunnel",
                          a1=P(-2, 21), a2=P(-2, 23), min_width=768)
    layout.add_connection("connection:tunnel_gatehouse", "region:gate_tunnel", "region:gatehouse",
                          a1=P(6, 21), a2=P(6, 23), min_width=768)
    layout.add_connection("connection:gatehouse_courtyard", "region:gatehouse", "region:courtyard",
                          a1=P(10, 17), a2=P(10, 27), min_width=1536)

    # ---- courtyard ---------------------------------------------------------
    layout.add_region("region:courtyard", COURTYARD, role="exterior",
                      ceiling_z=SKY, floor_z=COURT, parallax_ceiling=True,
                      **COURT_TILES,
                      intent={"purpose": "arrival garden courtyard", "classification": "MANDATORY"})
    layout.carve_hole("region:courtyard", CHAPEL_SHELL)
    layout.carve_hole("region:courtyard", GARDEN_BED)

    layout.add_region("region:garden_bed", GARDEN_BED, role="detail",
                      ceiling_z=SKY, floor_z=BED_FLOOR, parallax_ceiling=True,
                      **BED_TILES,
                      intent={"purpose": "octagonal sunken planter", "classification": "OPTIONAL"})
    for name, a1, a2 in BED_EDGES:
        layout.add_connection(f"connection:bed_{name}", "region:courtyard", "region:garden_bed",
                              a1=a1, a2=a2, min_width=256)

    # ---- chapel ------------------------------------------------------------
    layout.add_region("region:chapel_door", R(24, 21, 26, 25), role="doorway", type=600,
                      inherit_finish="both",
                      ceiling_z=COURT, floor_z=COURT,
                      # `door_face` rather than `wall_picnum`. A door sector's
                      # own walls face inward, and for a sector the player never
                      # stands in those are the only surfaces they never see:
                      # the door tile ended up on the inside of the frame while
                      # the rooms either side showed their own masonry. What is
                      # actually seen approaching a shut Z-door is the top
                      # section of the wall on the room side, which Build draws
                      # from that wall's own picnum. door_face puts it there, on
                      # both faces of every portal, and leaves the jambs to
                      # wall_picnum.
                      door_face=DOOR_FACE,
                      wall_picnum=JAMB_TILE, floor_picnum=DOOR_FACE, ceiling_picnum=DOOR_FACE,
                      sector_behavior=_z_door(COURT, COURT - tex(8), interaction="direct"),
                      intent={"purpose": "chapel west door", "classification": "MANDATORY",
                              "interaction": "direct_use"})
    layout.add_region("region:chapel_nave", NAVE, role="interior",
                      ceiling_z=NAVE_CEIL, floor_z=COURT, **NAVE_TILES,
                      intent={"purpose": "chapel nave", "classification": "MANDATORY"})
    layout.add_region("region:chapel_aisle_south", AISLE_SOUTH, role="interior",
                      ceiling_z=AISLE_CEIL, floor_z=COURT, **AISLE_TILES,
                      intent={"purpose": "south side aisle", "classification": "OPTIONAL"})
    layout.add_region("region:chapel_aisle_north", AISLE_NORTH, role="interior",
                      ceiling_z=AISLE_CEIL, floor_z=COURT, **AISLE_TILES,
                      intent={"purpose": "north side aisle", "classification": "OPTIONAL"})
    layout.add_region("region:chapel_apse", APSE, role="interior",
                      ceiling_z=APSE_CEIL, floor_z=APSE_FLOOR, **APSE_TILES,
                      intent={"purpose": "chancel raised 6144 above the nave, holding the "
                                         "crypt-gate switch",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:courtyard_chapeldoor", "region:courtyard", "region:chapel_door",
                          role="doorway", gated=True, a1=P(24, 21), a2=P(24, 25),
                          min_width=1536)
    layout.add_connection("connection:chapeldoor_nave", "region:chapel_door", "region:chapel_nave",
                          role="doorway", gated=True, a1=P(26, 21), a2=P(26, 25),
                          min_width=1536)
    layout.add_connection("connection:nave_aisle_south", "region:chapel_nave", "region:chapel_aisle_south",
                          a1=P(28, 18), a2=P(36, 18), min_width=1536)
    # Half the nave/aisle edge is a way through and half is a screen you shoot
    # out. kWallGib is 218 walls across the campaign and 98% of them are
    # two-sided: a window between two rooms rather than a hole in an outside
    # wall, always with trigger_vector set and resting at state 0. Both halves
    # join the same pair, so the aisle stays reachable whether or not the screen
    # is broken; breaking it only widens the way in.
    layout.add_connection("connection:nave_aisle_north", "region:chapel_nave", "region:chapel_aisle_north",
                          a1=P(28, 28), a2=P(32, 28), min_width=1536)
    layout.add_connection("connection:nave_screen", "region:chapel_nave", "region:chapel_aisle_north",
                          role="window", a1=P(32, 28), a2=P(36, 28), min_width=1536,
                          face_picnum=GIB_FACE,
                          wall_behavior={"trigger_vector": 1, "state": 0, "data": 12})
    # Both aisles were pockets hanging off the nave, which is not what an aisle
    # is: an aisle exists to be a way along the nave, and a chapel of this plan
    # has a porch on each flank. Giving each one its own way out to the
    # courtyard turns two dead ends into the level's two shortest loops --
    # courtyard, porch, aisle, nave -- and lets the nave be entered or left from
    # three sides instead of one, which is the difference between a room you
    # clear and a room you can be flanked in.
    #
    # They are deliberately not a matched pair. The campaign builds its two
    # approaches to a place differently far more often than it mirrors them, and
    # a chapel that has stood long enough to have a crypt full of bones has not
    # kept both its doors.
    layout.add_region("region:chapel_porch_south", R(30, 12, 34, 14), role="doorway", type=600,
                      inherit_finish="both",
                      ceiling_z=COURT, floor_z=COURT,
                      # `door_face` rather than `wall_picnum`. A door sector's
                      # own walls face inward, and for a sector the player never
                      # stands in those are the only surfaces they never see:
                      # the door tile ended up on the inside of the frame while
                      # the rooms either side showed their own masonry. What is
                      # actually seen approaching a shut Z-door is the top
                      # section of the wall on the room side, which Build draws
                      # from that wall's own picnum. door_face puts it there, on
                      # both faces of every portal, and leaves the jambs to
                      # wall_picnum.
                      door_face=DOOR_FACE,
                      wall_picnum=JAMB_TILE, floor_picnum=DOOR_FACE, ceiling_picnum=DOOR_FACE,
                      sector_behavior=_z_door(COURT, COURT - tex(6), interaction="direct"),
                      intent={"purpose": "chapel south porch, a working door onto the courtyard",
                              "classification": "OPTIONAL", "interaction": "direct_use"})
    layout.add_connection("connection:courtyard_porchsouth", "region:courtyard",
                          "region:chapel_porch_south", role="doorway", gated=True,
                          a1=P(30, 12), a2=P(34, 12), min_width=1536)
    layout.add_connection("connection:porchsouth_aisle", "region:chapel_porch_south",
                          "region:chapel_aisle_south", role="doorway", gated=True,
                          a1=P(30, 14), a2=P(34, 14), min_width=1536)

    # The north one has lost its door and stands open at the aisle's own ceiling
    # height, so it reads as a breach rather than a second porch and is the way
    # in that never needs opening.
    layout.add_region("region:chapel_breach_north", R(30, 32, 34, 34), role="gateway",
                      inherit_finish="both",
                      ceiling_z=AISLE_CEIL, floor_z=COURT, **ARCH_TILES,
                      intent={"purpose": "fallen north porch, standing open onto the courtyard",
                              "classification": "OPTIONAL"})
    layout.add_connection("connection:aisle_breachnorth", "region:chapel_aisle_north",
                          "region:chapel_breach_north", a1=P(30, 32), a2=P(34, 32),
                          min_width=1536)
    layout.add_connection("connection:breachnorth_courtyard", "region:chapel_breach_north",
                          "region:courtyard", a1=P(30, 34), a2=P(34, 34), min_width=1536)

    # The south half of the nave/chancel edge carries the stair; the north half
    # stays open at the full 6144 drop, which is what makes it an overlook.
    chancel = staircase(
        layout, "stairs:chancel",
        base=Anchor("region:chapel_nave", P(38, 20), P(38, 23)),
        total_rise=APSE_FLOOR - COURT, step_rise=-2048, tread=U, clear_height=tex(8),
        base_floor_z=COURT, shade_ramp=(18, 12), **APSE_TILES,
        intent={"classification": "MANDATORY"},
    )
    chancel.arrive_at("region:chapel_apse")
    # These three were blocked portals, to stop the player stepping sideways onto
    # the chancel instead of climbing the stair and turning. They were also
    # invisible: cstat 1 and nothing else, so you saw a 2048 kerb, read it as the
    # step it plainly is, and walked into a wall.
    #
    # Blood does block two-sided walls -- 2,272 of them -- but not here. The
    # floor difference across a blocked wall in the campaign has a median of
    # **4.00 player heights** and a q1 of 1.09; only a fifth of them sit at a
    # steppable kerb under 0.4, and a fifth of all of them are masked so you can
    # see what stopped you. A 0.36 kerb with nothing drawn on it is neither.
    #
    # So the rails are gone and the geometry means what it says: the chancel is
    # three shallow steps and you may climb it from the side.
    for step in range(1, 4):
        layout.add_connection(
            f"connection:chancel_side_{step:02d}", "region:chapel_apse",
            f"region:stairs:chancel:step_{step:02d}",
            a1=P(37 + step, 23), a2=P(38 + step, 23), min_width=384,
        )
    layout.add_connection("connection:nave_apse", "region:chapel_nave", "region:chapel_apse",
                          a1=P(38, 23), a2=P(38, 26), min_width=1152)


    # ---- cloister ----------------------------------------------------------
    #
    # The room a monastery is organised around, and the one this level did not
    # have: a covered walk on four sides of an open garth, with the working
    # rooms opening off it.
    #
    # It is also the answer to the level's most stubborn measurement. The
    # monastery ran 16 loops per 100 sectors against a campaign 38, and its
    # rendered `depth` was 3 sectors in frame against 5, which are two ways of
    # saying the same thing: it was a tree of rooms. A cloister is a cycle by
    # construction -- four walks meeting at the corners -- and every room that
    # opens onto two of them closes another.
    WALK_CEIL = COURT - tex(5)
    GARTH_FLOOR = COURT + 1024          # the garth sits a step below the walk
    CLOISTER_TILES = dict(wall_picnum=110, floor_picnum=2448, ceiling_picnum=285)
    # 2500, not 504. A parallax ceiling names the *first of sixteen* panels, and
    # the run from 504 is not sky at all -- it contains torches and trim, tiles
    # that are 10 to 89% transparent, which the renderer paints as raw magenta.
    # The courtyard has used 2500 since the first version; the garth was given
    # 504 when the cloister was built and has had a broken sky ever since.
    GARTH_TILES = dict(wall_picnum=110, floor_picnum=270, ceiling_picnum=SKY_PANEL)

    for tag, box, purpose in (
        ("south", R(14, -2, 46, 2), "cloister walk, south range"),
        ("north", R(14, -20, 46, -14), "cloister walk, north range"),
        ("west", R(14, -14, 20, -2), "cloister walk, west range"),
        ("east", R(40, -14, 46, -2), "cloister walk, east range"),
    ):
        layout.add_region(f"region:walk_{tag}", box, role="interior",
                          ceiling_z=WALK_CEIL, floor_z=COURT,
                          **CLOISTER_TILES,
                          intent={"purpose": purpose, "classification": "OPTIONAL"})

    layout.add_region("region:garth", R(20, -14, 40, -2), role="exterior",
                      ceiling_z=SKY, floor_z=GARTH_FLOOR, parallax_ceiling=True,
                      **GARTH_TILES,
                      intent={"purpose": "open garth at the centre of the cloister",
                              "classification": "OPTIONAL"})

    # The four corners of the walk. These are what make the cloister a ring
    # rather than four dead ends.
    for tag, a, b, x, y in (
        ("sw", "south", "west", (14, -2), (20, -2)),
        ("se", "south", "east", (40, -2), (46, -2)),
        ("nw", "north", "west", (14, -14), (20, -14)),
        ("ne", "north", "east", (40, -14), (46, -14)),
    ):
        layout.add_connection(f"connection:walk_{tag}", f"region:walk_{a}",
                              f"region:walk_{b}", a1=P(*x), a2=P(*y), min_width=1536)

    # The arcade: the walk looks into the garth on all four sides, which is what
    # a cloister is for and what puts four more independent loops in the graph.
    for tag, a1, a2 in (
        ("south", (20, -2), (40, -2)),
        ("north", (20, -14), (40, -14)),
        ("west", (20, -14), (20, -2)),
        ("east", (40, -2), (40, -14)),
    ):
        layout.add_connection(f"connection:arcade_{tag}", f"region:walk_{tag}",
                              "region:garth", a1=P(*a1), a2=P(*a2), min_width=1536)

    # A second sliding gate, built by the same one call as the crypt gate.
    CLOISTER_GATE = sliding_gate(
        layout, "region:cloister_gate",
        poly((26, 2), (30, 2), (30, 2.25), (32, 2.25), (32, 2.75),
             (30, 2.75), (30, 4), (26, 4), (26, 2.75), (24, 2.75),
             (24, 2.25), (26, 2.25)),
        threshold=(P(26, 2.5), P(30, 2.5)),
        travel=GATE_TRAVEL, channel=CH_CLOISTER,
        floor_z=COURT, ceiling_z=COURT - tex(4),
        **APPROACH_TILES,
        intent={"purpose": "the cloister gate, pushed open from either side",
                "classification": "OPTIONAL", "interaction": "direct_use"})
    layout.add_connection("connection:courtyard_cloistergate", "region:courtyard",
                          "region:cloister_gate", role="doorway", gated=True,
                          a1=P(26, 4), a2=P(30, 4), min_width=1536)
    layout.add_connection("connection:cloistergate_walk", "region:cloister_gate",
                          "region:walk_south", role="doorway", gated=True,
                          a1=P(26, 2), a2=P(30, 2), min_width=1536)

    # The working rooms. Each opens onto two walks, so each is a route rather
    # than a pocket -- the fault the chapel aisles had before their porches.
    # The pier between the two doors is set back to x 48, so the room meets the
    # walk only where it opens onto it. Declaring two doors along one shared
    # edge instead leaves the span between them paired with nothing, which the
    # compiler refuses -- rightly: a solid boundary on a shared edge emits two
    # coincident one-sided walls, and the campaign has none in 113,261.
    layout.add_region("region:chapter_house",
                      poly((46, -14), (56, -14), (58, -12), (58, -4), (56, -2),
                           (46, -2), (46, -6), (48, -6), (48, -10), (46, -10)),
                      role="interior", ceiling_z=COURT - tex(8), floor_z=COURT,
                      wall_picnum=91, floor_picnum=568, ceiling_picnum=255,
                      intent={"purpose": "chapter house off the east walk",
                              "classification": "OPTIONAL"})
    # The north opening is barred rather than open: you see the chapter house
    # from the walk before you reach it, and go round by the south door. Each of
    # these rooms was reached through two identical holes, which is a corridor
    # with a room attached rather than a room.
    layout.add_connection("connection:eastwalk_chapter_n", "region:walk_east",
                          "region:chapter_house", a1=P(46, -14), a2=P(46, -10),
                          min_width=1536,
                          face_cstat=WINDOW_CSTAT, face_over_picnum=WINDOW_GLASS)
    layout.add_connection("connection:eastwalk_chapter_s", "region:walk_east",
                          "region:chapter_house", a1=P(46, -6), a2=P(46, -2),
                          min_width=1536)

    layout.add_region("region:refectory",
                      poly((4, -14), (14, -14), (14, -10), (12, -10), (12, -6),
                           (14, -6), (14, -2), (6, -2), (4, -4)),
                      role="interior", ceiling_z=COURT - tex(7), floor_z=COURT,
                      wall_picnum=194, floor_picnum=294, ceiling_picnum=255,
                      intent={"purpose": "refectory off the west walk",
                              "classification": "OPTIONAL"})
    layout.add_connection("connection:westwalk_refectory_n", "region:walk_west",
                          "region:refectory", a1=P(14, -14), a2=P(14, -10),
                          min_width=1536,
                          face_cstat=WINDOW_CSTAT, face_over_picnum=WINDOW_GLASS)
    layout.add_connection("connection:westwalk_refectory_s", "region:walk_west",
                          "region:refectory", a1=P(14, -6), a2=P(14, -2),
                          min_width=1536)

    # A third secret: the campaign runs a median of 3 per map and a q3 of 5.
    layout.add_region("region:cloister_cell", R(24, -26, 30, -20), role="secret",
                      secret=True, declared_zero_exit=True,
                      ceiling_z=COURT - tex(4), floor_z=COURT,
                      wall_picnum=194, floor_picnum=294, ceiling_picnum=255,
                      intent={"purpose": "a walled-up cell behind the north walk",
                              "classification": "OPTIONAL", "hidden": True})
    layout.add_connection("connection:northwalk_cell", "region:walk_north",
                          "region:cloister_cell", a1=P(24, -20), a2=P(30, -20),
                          min_width=1536)

    # ---- crypt -------------------------------------------------------------
    # A sliding fence gate rather than a fourth slab. E1M1's gate is a type-614
    # sector with 49 walls and *none of them marked*: no geometry moves at all.
    # TranslateSector runs its sprite loop whatever the walls do, so the two
    # fence sprites -- one carrying cstat 8192 and one 16384 -- part in opposite
    # directions and the sector stands still. That is why it cannot distort the
    # courtyard it shares a wall with, which a whole-sector slide would.
    # One call. Everything below the threshold and the travel comes from the
    # template mined off the campaign's 308 gates: the resting pose, both marker
    # tiles and angles and cstats, each leaf's angle relative to the threshold,
    # its width relative to the travel, its seat on the floor, the two carry
    # bits, and the push wiring. Twelve facts that were previously twelve
    # decisions, seven of which were wrong at some point.
    # The sector is wider than the opening it closes, because a sliding gate
    # needs somewhere to slide *into*. E1M1's gate sector is 49 walls for the
    # same reason.
    #
    # It is not, however, a rectangle. It was, and then the two units either side
    # of the opening ran flush against the courtyard, so eight walls of this gate
    # were "blocked portals" -- masked two-sided walls with the wall's own picnum
    # copied onto its over_picnum to fake solidity. The campaign does that in 14
    # walls out of 600 masked; this level was doing it in 32 of 38, and from
    # inside they read as exactly what they are, invisible barriers standing in
    # for stone.
    #
    # The shape is the answer. The gate only ever needs to be wide *on the line
    # the leaves travel along*: a slot half a unit deep at the threshold, with a
    # neck at either end the width of the doorway. Then the sector touches its
    # neighbours only where it opens onto them, everything else is a one-sided
    # wall with rock behind it, and the leaves still have their two units to
    # retract into. The slot is 192 across, so nothing walks into it either --
    # the player is 384.
    CRYPT_GATE = sliding_gate(
        layout, "region:crypt_gate",
        poly((30, 40), (34, 40), (34, 40.25), (36, 40.25), (36, 40.75),
             (34, 40.75), (34, 42), (30, 42), (30, 40.75), (28, 40.75),
             (28, 40.25), (30, 40.25)),
        threshold=(P(30, 40.5), P(34, 40.5)),
        travel=GATE_TRAVEL, channel=CH_CRYPT_GATE,
        floor_z=COURT, ceiling_z=COURT - tex(4),
        **APPROACH_TILES,
        intent={"purpose": "iron fence gate onto the crypt stair; the leaves part "
                           "rather than the gate lifting",
                "classification": "MANDATORY", "interaction": "remote_switch"})

    layout.add_connection("connection:courtyard_cryptgate", "region:courtyard", "region:crypt_gate",
                          role="doorway", gated=True, a1=P(30, 40), a2=P(34, 40),
                          min_width=1536)

    # Four rises of 3072, which is the third rise the corpus actually uses.  The
    # whole run, its shade ramp and its five portals are one call; v0-v3 wrote
    # this as a loop that tracked its own previous edge by hand.
    descent = staircase(
        layout, "stairs:crypt",
        base=Anchor("region:crypt_gate", P(34, 42), P(30, 42)),
        total_rise=4 * CRYPT_STEP, step_rise=CRYPT_STEP, tread=2 * U,
        clear_height=tex(4), base_floor_z=COURT, shade_ramp=(28, 46), **CRYPT_STAIR_TILES,
        intent={"classification": "MANDATORY"},
    )
    layout.add_region("region:crypt_hall", CRYPT_HALL, role="interior",
                      ceiling_z=CRYPT_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_TILES,
                      intent={"purpose": "vaulted crypt hall with cut corners",
                              "classification": "MANDATORY"})
    descent.arrive_at("region:crypt_hall")
    # A raised tomb block the player walks around and never stands on: the crypt
    # hall's own vertical relationship, and something for a 200 player-area room
    # to be about.
    layout.carve_hole("region:crypt_hall", PLINTH)
    layout.add_region("region:crypt_plinth", PLINTH, role="detail",
                      ceiling_z=CRYPT_CEIL, floor_z=CRYPT_FLOOR - 6144,
                      **PLINTH_TILES,
                      intent={"purpose": "raised tomb block in the crypt hall",
                              "classification": "OPTIONAL"})
    for name, a1, a2 in PLINTH_EDGES:
        layout.add_connection(f"connection:plinth_{name}", "region:crypt_hall",
                              "region:crypt_plinth", a1=P(*a1), a2=P(*a2), min_width=512)
    layout.add_region("region:crypt_reliquary", RELIQUARY, role="key_branch",
                      ceiling_z=CHAMBER_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_CELL_TILES,
                      intent={"purpose": "reliquary cell holding the skull key; kept low on the "
                                         "E6M3 precedent for crypt cells of this size",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:crypthall_reliquary", "region:crypt_hall", "region:crypt_reliquary",
                          a1=P(22, 52), a2=P(22, 58), min_width=1536)
    # The cistern is sludge, not a dry cell. kSectorDamage is 77 sectors across
    # the campaign and E1M3 builds its flowing ones exactly this way: damage_type
    # 3 with the floor panned and Drag set, so the surface moves and carries the
    # player with it. `data` is the damage, clipped to 0..1000, and 0 means
    # instant death -- so it has to be stated. E1M2 uses 35, E1M4 uses 30.
    # The floor has to look like what it does. This sector has hurt the player
    # and dragged them since it was built, and it was wearing tile 255 -- plain
    # dark stone -- so nothing about it said so: you walked into a room that
    # damaged you for no visible reason, and the only clue was that the floor was
    # sliding. 1120 is the campaign's commonest panned floor tile by a distance
    # (128 sectors) and is six frames of green sludge, which is what a cistern
    # under a monastery holds.
    #
    # The damage type stays at 3. `kDamageExplode` reads oddly for sludge, and it
    # is what Blood uses: 27 of the 28 campaign damage sectors that set Drag pick
    # it, against one that picks Burn.
    layout.add_region("region:crypt_cistern", CISTERN, role="interior", type=618,
                      ceiling_z=CHAMBER_CEIL, floor_z=CISTERN_FLOOR,
                      **dict(CRYPT_CHAMBER_TILES, floor_picnum=1120),
                      # 27 of the campaign's 28 sludge sectors that set Drag use
                      # pan_velocity 255 with pan_angle 512, and nothing uses 96.
                      # The field is eight bits and drives both the surface pan
                      # and the shove (`speed = panVel << 9`), so 96 was drifting
                      # at 38% of the only speed Blood ever gives sludge.
                      sector_behavior={"damage_type": 3, "data": 30,
                                       "pan_always": 1, "pan_floor": 1, "drag": 1,
                                       "pan_velocity": 255, "pan_angle": 512,
                                       "underwater": 0},
                      intent={"purpose": "sludge cistern holding the ossuary switch; the floor "
                                         "hurts and drifts, which is what makes the switch cost "
                                         "something to reach",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:crypthall_cistern", "region:crypt_hall", "region:crypt_cistern",
                          a1=P(26, 60), a2=P(34, 60), min_width=1536)

    # The crypt hall was the level's worst funnel: seven spokes, and cutting it
    # broke the map into seven pieces. Every one of those spokes was reached and
    # left through the same door, which is what a star looks like and not what a
    # crypt looks like. The ambulatory closes the south-west of it into a
    # circuit, so the reliquary -- the room the player leaves carrying the key,
    # and therefore the room worth ambushing -- has a second way out that is not
    # back through whatever followed them in.
    #
    # It is deliberately the meanest space in the crypt: a head-height crawl
    # rather than a vaulted walk, so the circuit costs something to use and the
    # hall keeps its scale by comparison.
    layout.add_region("region:crypt_ambulatory", AMBULATORY, role="interior",
                      ceiling_z=CRYPT_FLOOR - tex(4), floor_z=CRYPT_FLOOR,
                      **CRYPT_CELL_TILES,
                      intent={"purpose": "low bone-lined ambulatory closing the crypt's "
                                         "south-west into a circuit",
                              "classification": "OPTIONAL"})
    layout.add_connection("connection:reliquary_ambulatory", "region:crypt_reliquary",
                          "region:crypt_ambulatory", a1=P(18, 58), a2=P(22, 58),
                          min_width=1536)
    layout.add_connection("connection:ambulatory_cistern", "region:crypt_ambulatory",
                          "region:crypt_cistern", a1=P(26, 61), a2=P(26, 64),
                          min_width=1024)

    # A rotating panel rather than a fourth slab that drops out of the ceiling.
    # The campaign runs 211 type-617 sectors and 168 of them turn exactly a
    # quarter (marker angle +/-512), so that is the sweep. It rests at state 1
    # because trInit treats the authored geometry as the busy == 1 pose: it
    # translates a rotating sector a full turn backwards, takes that as its base
    # and only then moves to its busy, so a panel left at state 0 swings itself
    # open the moment the level loads.
    #
    # The axis is the panel's north-east corner and the sweep is negative, which
    # takes it into the ossuary. `tools/verify_motion` is what says it does not
    # cross anything on the way; nothing about the declaration guarantees that.
    layout.add_region("region:ossuary_door", R(42, 52, 44, 56), role="doorway", type=617,
                      inherit_finish="both",
                      ceiling_z=OSSUARY_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_CHAMBER_TILES,
                      # Drawn shut, so it rests at busy 65536 -- see the crypt
                      # gate for why (state, busy) has to be a matched pair.
                      sector_behavior={"state": 1, "busy": 65536,
                                       "busy_time_a": 10, "busy_time_b": 10,
                                       "rx_id": CH_SECRET, "trigger_push": 0,
                                       "trigger_wall_push": 0},
                      intent={"purpose": "hidden ossuary panel, a quarter turn on its own hinge",
                              "classification": "OPTIONAL", "hidden": True})
    # cstat 32896: all 211 campaign rotate pivots carry it, and none the bare
    # invisible bit. The same slip as the slide markers, found the same way.
    layout.add_sprite("axis_ossuary", "region:ossuary_door",
                      x=P(44, 52)[0] - 64, y=P(44, 52)[1] + 64, z=CRYPT_FLOOR,
                      type=5, picnum=3997, status=10, cstat=32896,
                      x_repeat=64, y_repeat=64, angle=-512)
    # The panel itself is a grille that turns with its sector. TranslateSector
    # moves a sprite with the sector only if it carries cstat 8192 (with it) or
    # 16384 (against it); without one of those bits the sector turns and the
    # thing standing in it stays put. E1M8 builds its rotating fences exactly
    # this way: tile 1064 at cstat 8337, which is 8192 plus blocking,
    # wall-aligned and centred.
    # `seat="floor"` rather than z=CRYPT_FLOOR. Blood centres a sprite on its
    # own z, so the obvious spelling buried exactly half the grille; 43 of the
    # campaign's 65 fence sprites sit with their bottom exactly on the floor.
    # The repeat comes from the opening rather than from E1M8: E1M8's fence is
    # 32768 tall in a 65536 room, and copying its repeat into a 16384 doorway
    # made a grille twice the height of the hole it fills.
    # Tile 1044 rather than E1M8's 1064: the cstat is what E1M8 teaches and that
    # is kept, but 1064 appears twice in the whole campaign, both times at 5.82
    # player heights, so there is no evidence for it at any other size. 1044 is
    # the fence Blood actually uses -- 63 placements from 3.64 up.
    layout.add_sprite("fence_ossuary", "region:ossuary_door",
                      x=P(43, 54)[0], y=P(43, 54)[1], z=CRYPT_FLOOR,
                      seat="floor",
                      type=0, picnum=1044, status=0, cstat=8192 | 1 | 16 | 128,
                      x_repeat=64, y_repeat=repeat_to_fit(CRYPT_FLOOR, OSSUARY_CEIL, 128),
                      # The ossuary door opens along x, so its panel faces along
                      # x too -- a quarter turn from the wall it lies on, like
                      # the gate leaves. It was at 512, edge-on in its own
                      # doorway.
                      #
                      # It is deliberately *not* pushable, unlike the gate. The
                      # campaign leaves 44 of its 65 fences with no XSprite at
                      # all, and this one is the far side of a secret whose
                      # price is the switch out in the sludge. A panel that
                      # opens to a shove would refund that.
                      shade=-8, angle=1024)
    layout.add_region("region:ossuary", OSSUARY, role="secret", secret=True,
                      ceiling_z=OSSUARY_CEIL, floor_z=CRYPT_FLOOR, declared_zero_exit=True,
                      **CRYPT_CHAMBER_TILES,
                      intent={"purpose": "optional ossuary", "classification": "OPTIONAL"})
    layout.add_connection("connection:crypthall_ossuarydoor", "region:crypt_hall", "region:ossuary_door",
                          role="doorway", gated=True, a1=P(42, 52), a2=P(42, 56), min_width=1536)
    layout.add_connection("connection:ossuarydoor_ossuary", "region:ossuary_door", "region:ossuary",
                          role="doorway", gated=True, a1=P(44, 52), a2=P(44, 56), min_width=1536)

    # ---- the cracked wall --------------------------------------------------
    #
    # 108 of these across 27 of the 43 campaign maps, always tile 1127, and they
    # transmit to two things: a hidden kTrapExploder (347 receivers across the
    # campaign) and a type-600 sector that opens the hole (194). The crack is the
    # shootable part; the charges behind it do the damage and the collapsed
    # sector is the hole itself.
    layout.add_region("region:crypt_breach", R(25, 49, 29, 50), role="doorway", type=600,
                      inherit_finish="both",
                      door_face=DOOR_FACE,
                      ceiling_z=CRYPT_FLOOR, floor_z=CRYPT_FLOOR, **CRYPT_HALL_TILES,
                      sector_behavior=_z_door(CRYPT_FLOOR, CHAMBER_CEIL, interaction="remote",
                                              rx=CH_BREACH),
                      intent={"purpose": "the hole the charge opens; collapsed until then",
                              "classification": "OPTIONAL", "hidden": True})
    layout.add_region("region:crypt_charnel", R(25, 45, 29, 49), role="secret", secret=True,
                      ceiling_z=CHAMBER_CEIL, floor_z=CRYPT_FLOOR, declared_zero_exit=True,
                      **CRYPT_CELL_TILES,
                      intent={"purpose": "charnel niche behind the cracked wall",
                              "classification": "OPTIONAL"})
    layout.add_connection("connection:crypthall_breach", "region:crypt_hall", "region:crypt_breach",
                          role="doorway", gated=True, a1=P(25, 50), a2=P(29, 50), min_width=1536)
    layout.add_connection("connection:breach_charnel", "region:crypt_breach", "region:crypt_charnel",
                          role="doorway", gated=True, a1=P(25, 49), a2=P(29, 49), min_width=1536)

    # ---- ascent, gallery, and the loop back down ---------------------------
    ascent = staircase(
        layout, "stairs:ascent",
        parallax_ceiling=True,   # outdoors: the sky tile means the sky
        base=Anchor("region:courtyard", P(52, 20), P(52, 24)),
        total_rise=-3 * GAL_STEP, step_rise=-GAL_STEP, tread=2 * U,
        clear_height=tex(5), base_floor_z=COURT, shade_ramp=(14, 26), **COURT_TILES,
        intent={"classification": "MANDATORY"},
    )
    layout.add_region("region:gallery_arch", R(58, 20, 62, 24), role="gateway",
                      inherit_finish="both",
                      ceiling_z=ARCH_CEIL, floor_z=GALLERY_FLOOR, **ARCH_TILES,
                      intent={"purpose": "low covered arch; the threshold the gallery begins at",
                              "classification": "MANDATORY"})
    ascent.arrive_at("region:gallery_arch")
    layout.add_region("region:gallery", GALLERY, role="upper",
                      ceiling_z=GALLERY_CEIL, floor_z=GALLERY_FLOOR, **GALLERY_TILES,
                      intent={"purpose": "tall upper service gallery with cut corners",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:arch_gallery", "region:gallery_arch", "region:gallery",
                          a1=P(62, 20), a2=P(62, 24), min_width=1536)

    # ---- bell tower --------------------------------------------------------
    #
    # The level was flat: 11.3 player heights from its lowest floor to its
    # highest, against a campaign median of 32.4 (E1M1 is 13.1, so it is low
    # too, but the campaign q1 is 20.4 and this was under half of it). Its
    # longest stair was four steps where the campaign's runs reach twenty-five.
    #
    # A tower fixes both at once, and it is what a monastery is missing when it
    # has a cloister and no bell.
    #
    # The step is 4096, not the 8192 this first tried. The campaign uses 8192
    # between small sectors 1,025 times, which looked like licence -- but
    # `max_step` for Blood is 4096, so those are ledges and drops, not treads.
    # The vocabulary said so: "that is an overlook, not a stair". Twenty-four
    # steps is near the campaign's longest run of twenty-five, and climbs 17.5
    # player heights.
    # TOWER_STEP, TOWER_STEPS, TOWER_RISE, BELFRY_FLOOR and GRAVEYARD_SKY are
    # module-level: the garden is built pages before the tower and shares the
    # graveyard's wall with it.
    TOWER_TILES = dict(wall_picnum=91, floor_picnum=568, ceiling_picnum=255)

    layout.add_region("region:tower_foot", R(33, -24, 39, -20), role="gateway",
                      ceiling_z=COURT - tex(6), floor_z=COURT,
                      **TOWER_TILES,
                      intent={"purpose": "foot of the bell tower, off the north walk",
                              "classification": "OPTIONAL"})
    layout.add_connection("connection:northwalk_tower", "region:walk_north",
                          "region:tower_foot", a1=P(33, -20), a2=P(39, -20),
                          min_width=1536)

    # A tall shaft to climb inside: the clear height stays generous the whole
    # way up, so the tower reads as one space rather than as twenty boxes.
    tower = staircase(
        layout, "stairs:tower",
        base=Anchor("region:tower_foot", P(33, -24), P(39, -24)),
        total_rise=-TOWER_RISE, step_rise=-TOWER_STEP, tread=U,
        clear_height=tex(7), base_floor_z=COURT, shade_ramp=(30, 10),
        **TOWER_TILES,
        intent={"classification": "OPTIONAL"},
    )
    layout.add_region("region:belfry", R(31, -56, 41, -48), role="upper",
                      ceiling_z=BELFRY_FLOOR - tex(9), floor_z=BELFRY_FLOOR,
                      **TOWER_TILES,
                      intent={"purpose": "the belfry at the head of the tower stair",
                              "classification": "OPTIONAL"})
    tower.arrive_at("region:belfry")

    # What the tower is for. A belfry with no view is a staircase with a room on
    # top, so the north wall is barred and the ground beyond it is a graveyard
    # twenty-four player heights below -- open to the sky, full of markers, and
    # unreachable. Blood builds scenery you can see and not enter all through
    # the campaign; the window is the same masked wall as the cloister's, and
    # what makes the ground unreachable is simply that it blocks.
    # Its sky has to be higher than the tower, or there is nothing to see: a
    # window shows the neighbour's *middle* band, and if the neighbour's ceiling
    # is below this floor there is no middle band at all. The first version put
    # the graveyard under the ordinary courtyard sky, which is eight player
    # heights below the belfry floor, and the window looked at nothing.
    layout.add_region("region:graveyard", GRAVEYARD, role="exterior",
                      ceiling_z=GRAVEYARD_SKY, floor_z=COURT,
                      parallax_ceiling=True,
                      wall_picnum=110, floor_picnum=270, ceiling_picnum=SKY_PANEL,
                      intent={"purpose": "walled graveyard below the belfry, seen "
                                         "from the tower window and reached from "
                                         "the garden",
                              "classification": "OPTIONAL"})
    # The embrasure: the opening carried through the thickness of the wall. Its
    # ceiling is lower than the belfry's, which is what gives the window a head
    # rather than letting it run to the roof, and the grille sits on its outer
    # face where a grille belongs. The stone either side of it is now stone --
    # the belfry's own north wall, one-sided, with nothing behind it.
    layout.add_region("region:belfry_window", R(33, -57, 39, -56), role="gateway",
                      ceiling_z=BELFRY_FLOOR - tex(3), floor_z=BELFRY_FLOOR,
                      wall_picnum=91, floor_picnum=91, ceiling_picnum=91,
                      intent={"purpose": "the belfry window carried through the "
                                         "thickness of the tower wall",
                              "classification": "OPTIONAL"})
    layout.add_connection("connection:belfry_window", "region:belfry",
                          "region:belfry_window", a1=P(33, -56), a2=P(39, -56),
                          min_width=1536)
    layout.add_connection("connection:belfry_graveyard", "region:belfry_window",
                          "region:graveyard", a1=P(33, -57), a2=P(39, -57),
                          min_width=1536,
                          face_cstat=WINDOW_CSTAT, face_over_picnum=WINDOW_GRATE)

    # Graves. E1M1's cemetery is built from raised plots -- small sectors lifted
    # 1024 for a kerb or 6144 for a tomb -- with a headstone standing on each,
    # and that is what makes it read as a graveyard rather than as a field with
    # markers scattered on it. Its outdoor tiles are 700, 701, 703, 704 and 706,
    # all roughly 45x60.
    #
    # This took two wrong tiles before it was the wrong *kind* of thing: first
    # the iron fence shrunk below any size Blood draws it at, then a key sign,
    # and both times the ground stayed flat.
    #
    # The repeat is 64 because that is what all five of these tiles use in the
    # campaign, every time. It was 48, which is not a size Blood ever draws a
    # headstone at -- one number picked for five tiles of four different heights,
    # so at best it was right for one of them.
    GRAVE_KERB = 1024
    GRAVE_TOMB = 6144
    for tag, box, lift, stone in (
        ("a", R(24, -66, 30, -60), GRAVE_KERB, 704),
        ("b", R(32, -66, 38, -60), GRAVE_TOMB, 706),
        ("c", R(24, -76, 30, -70), GRAVE_TOMB, 701),
        ("d", R(32, -76, 38, -70), GRAVE_KERB, 703),
    ):
        rid = f"region:grave_{tag}"
        layout.carve_hole("region:graveyard", box)
        layout.add_region(rid, box, role="detail",
                          ceiling_z=GRAVEYARD_SKY, floor_z=COURT - lift,
                          parallax_ceiling=True,
                          wall_picnum=110, floor_picnum=568, ceiling_picnum=SKY_PANEL,
                          intent={"purpose": f"raised grave plot {tag}",
                                  "classification": "OPTIONAL"})
        for name, index in (("s", 0), ("e", 1), ("n", 2), ("w", 3)):
            layout.add_connection(f"connection:grave_{tag}_{name}", "region:graveyard",
                                  rid, a1=box[index], a2=box[(index + 1) % 4],
                                  min_width=256)
        cx = (box[0][0] + box[2][0]) // 2
        cy = (box[0][1] + box[2][1]) // 2
        layout.add_sprite(f"grave_stone_{tag}", rid, x=cx, y=cy, z=COURT - lift,
                          seat="floor", type=0, picnum=stone, status=0,
                          cstat=1 | 128 | 256, x_repeat=64, y_repeat=64,
                          shade=8, angle=512)

    for tag, x, y in (("a", 24, -66), ("b", 42, -70), ("c", 33, -78)):
        layout.add_sprite(f"grave_bush_{tag}", "region:graveyard",
                          x=P(x, y)[0], y=P(x, y)[1], z=COURT, seat="floor",
                          **decor(599, 1 | 128 | 256, 2.4, shade=6))

    # The garden, off the chapter house. Everything up to here is rooms; this is
    # the one place in the level with a horizon in it.
    water_garden(layout)

    # -- the flooded run, dressed ------------------------------------------
    #
    # Five sectors of water with two sprites in them between them, lit flat and
    # dark. Blood's own underwater sectors are not like that: 41 of them carry a
    # rising column of bubbles (668), and seaweed (546), weed (660) and kelp
    # (664) grow in them; a Gill Beast (type 217, tile 1570) is in 101 of them.
    #
    # A lantern goes in the vault because the campaign puts one under water five
    # times and because it is the only way this run gets a light of its own --
    # 641 is in `LIGHT_TILES`, so the pooling pass then works out the walls
    # around it, and the room acquires a middle as well as a floor and a ceiling.
    SUNK_LIGHT = 641
    layout.add_sprite("sunk_lantern", "region:sunk_vault",
                      x=P(21, 103)[0], y=P(21, 103)[1], z=SUNK_CEIL,
                      seat="ceiling", **decor(SUNK_LIGHT, 128, 5.8, shade=-128))
    # Bubbles. Floor-seated and tall -- the campaign draws 668 at a median of
    # 5.82 player heights, which is most of the height of the water.
    for tag, region, x, y in (
        ("well", "region:sunk_well", 15.5, 78.5),
        ("descent_a", "region:sunk_descent", 15.0, 86.0),
        ("descent_b", "region:sunk_descent", 17.0, 95.0),
        ("vault_a", "region:sunk_vault", 17.0, 102.0),
        ("vault_b", "region:sunk_vault", 25.0, 104.0),
        ("crypt", "region:sunk_crypt", 25.6, 110.0),
    ):
        layout.add_sprite("sunk_bubbles_%s" % tag, region,
                          x=P(x, y)[0], y=P(x, y)[1], z=SUNK_FLOOR, seat="floor",
                          **decor(668, 128, 5.8, shade=-24))
    # Weed on the bottom. 546 is the campaign's own seaweed and is sometimes a
    # breakable thing (type 417) rather than scenery; here it is scenery.
    for tag, region, x, y, tile, height in (
        ("a", "region:sunk_vault", 15.5, 101.0, 546, 3.5),
        ("b", "region:sunk_vault", 26.5, 105.0, 546, 3.5),
        ("c", "region:sunk_descent", 14.6, 90.0, 660, 1.45),
        ("d", "region:sunk_descent", 17.4, 82.0, 660, 1.45),
        ("e", "region:sunk_vault", 20.0, 105.5, 664, 5.7),
        ("f", "region:sunk_vault", 23.0, 100.6, 664, 5.7),
    ):
        layout.add_sprite("sunk_weed_%s" % tag, region,
                          x=P(x, y)[0], y=P(x, y)[1], z=SUNK_FLOOR, seat="floor",
                          **decor(tile, 1 | 128 | 256, height, shade=10))

    # The long way round. The chapter house backs onto the ground the gallery
    # stands over, and a stair up its east side ties the new wing to the far end
    # of the level: courtyard, cloister, chapter house, gallery, back down the
    # ascent to the courtyard. One loop, but the largest one in the map -- and
    # the reason to walk the cloister rather than glance into it.
    layout.add_region("region:chapter_landing", R(58, -12, 62, -4), role="interior",
                      ceiling_z=COURT - tex(5), floor_z=COURT,
                      wall_picnum=91, floor_picnum=568, ceiling_picnum=255,
                      intent={"purpose": "landing at the foot of the dorter stair",
                              "classification": "OPTIONAL"})
    layout.add_connection("connection:chapter_landing", "region:chapter_house",
                          "region:chapter_landing", a1=P(58, -12), a2=P(58, -4),
                          min_width=1536)
    dorter = staircase(
        layout, "stairs:dorter",
        base=Anchor("region:chapter_landing", P(62, -4), P(58, -4)),
        total_rise=-3 * GAL_STEP, step_rise=-GAL_STEP, tread=2 * U,
        # A roofed ceiling, not the courtyard's sky: this stair runs between the
        # chapter landing and the gallery approach and never sees daylight.
        clear_height=tex(5), base_floor_z=COURT, shade_ramp=(26, 14),
        wall_picnum=110, floor_picnum=2448, ceiling_picnum=285,
        intent={"classification": "OPTIONAL"},
    )
    layout.add_region("region:gallery_approach", R(58, 2, 62, 16), role="interior",
                      ceiling_z=GALLERY_FLOOR - tex(5), floor_z=GALLERY_FLOOR,
                      **GALLERY_TILES,
                      intent={"purpose": "upper walk from the dorter stair to the gallery",
                              "classification": "OPTIONAL"})
    dorter.arrive_at("region:gallery_approach")
    layout.add_connection("connection:approach_gallery", "region:gallery_approach",
                          "region:gallery", a1=P(62, 12), a2=P(62, 16), min_width=1536)

    layout.add_region("region:loop_arch", R(58, 34, 62, 38), role="gateway",
                      inherit_finish="both",
                      ceiling_z=ARCH_CEIL, floor_z=GALLERY_FLOOR, **ARCH_TILES,
                      intent={"purpose": "second gallery arch onto the return stair",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:gallery_looparch", "region:gallery", "region:loop_arch",
                          a1=P(62, 34), a2=P(62, 38), min_width=1536)

    descent_home = staircase(
        layout, "stairs:return",
        parallax_ceiling=True,   # outdoors: the sky tile means the sky
        base=Anchor("region:loop_arch", P(58, 38), P(58, 34)),
        total_rise=3 * GAL_STEP, step_rise=GAL_STEP, tread=2 * U,
        clear_height=tex(5), base_floor_z=GALLERY_FLOOR, shade_ramp=(26, 14), **COURT_TILES,
        intent={"classification": "MANDATORY"},
    )
    descent_home.arrive_at("region:courtyard")

    # ---- exit --------------------------------------------------------------
    layout.add_region("region:exit_door", R(76, 22, 78, 26), role="doorway", type=600,
                      inherit_finish="both",
                      # The keyed face is the whole point of this door, so it is
                      # what the gallery sees; the jambs are ordinary masonry.
                      door_face=KEYED_FACE,
                      ceiling_z=GALLERY_FLOOR, floor_z=GALLERY_FLOOR,
                      wall_picnum=JAMB_TILE, floor_picnum=KEYED_FACE, ceiling_picnum=KEYED_FACE,
                      sector_behavior=_z_door(GALLERY_FLOOR, EXIT_CEIL, interaction="direct", key=1),
                      intent={"purpose": "skull-keyed exit gate", "classification": "MANDATORY",
                              "interaction": "direct_use"})
    layout.add_region("region:exit_hall", EXIT_HALL, role="exit", declared_zero_exit=True,
                      ceiling_z=EXIT_CEIL, floor_z=GALLERY_FLOOR, **EXIT_TILES,
                      intent={"purpose": "exit chamber", "classification": "MANDATORY"})
    layout.add_connection("connection:gallery_exitdoor", "region:gallery", "region:exit_door",
                          role="doorway", gated=True, a1=P(76, 22), a2=P(76, 26),
                          min_width=1536)
    layout.add_connection("connection:exitdoor_hall", "region:exit_door", "region:exit_hall",
                          role="doorway", gated=True, a1=P(78, 22), a2=P(78, 26),
                          min_width=1536)

    # ---- gameplay population -----------------------------------------------
    start = P(-6, 22)
    # Blood counts secrets over its own channels: each secret room transmits 64
    # on channel 2 when entered, and one sprite declares the total as 64 + n on
    # channel 1. This level had two hidden rooms and neither told the player
    # anything on finding it, because "secret" was a role name here and nothing
    # in the map. The campaign runs a median of 3 per map (q1 2, q3 5).
    layout.add_sprite("secret_total", "region:ledge",
                      x=start[0], y=start[1], z=COURT - 1024,
                      type=0, picnum=0, status=0, cstat=32768,
                      x_repeat=64, y_repeat=64, angle=0,
                      behavior={"tx_id": 1, "command": 64 + SECRETS})

    layout.set_player_start("region:ledge", x=start[0], y=start[1], z=COURT - 1024, angle=0)
    # An explicit zero rather than no behaviour at all: the dict is what makes
    # the compiler allocate the XSprite, and all 345 campaign player starts carry
    # one, at state 0. This used to say 1, which is a state no campaign start is
    # ever in.
    layout.add_sprite("sp_start", "region:ledge", x=start[0], y=start[1], z=COURT - 1024,
                      **sprite_appearance(1, angle=0), behavior={"state": 0})
    layout.place_on_wall("sw_crypt_gate", "region:chapel_apse",
                         a1=APSE_ARC[4], a2=APSE_ARC[5], t=0.5,
                         height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
                         **SWITCH,
                         # kCmdToggle (3), not kCmdOn (1). The gate rests at
                         # state 1, and `SetSectorState` returns 0 when the
                         # sector is already in the state it is being sent to,
                         # so kCmdOn to an already-on sector is a switch that
                         # visibly does nothing. The campaign bears this out:
                         # across 659 slide and rotate sectors, a state-1 sector
                         # is sent toggle 42 times and off 34, and kCmdOn
                         # not once.
                         behavior={"tx_id": CH_CRYPT_GATE, "command": 3, "trigger_on": 1,
                                   "trigger_push": 1, "data_1": 203})
    # The crack itself: hung on the crypt-hall side of the collapsed breach, at
    # the tile and mounting the campaign gives all 108 of its cracks. Vector and
    # Impact are what let a shot and a nearby blast reach it; NBlood's
    # actFireVector only issues kCmdSpriteImpact when Vector is set, and
    # thingInfo gives type 408 no bullet damage, so without it a hitscan does
    # nothing. It rests at state 0 -- SetSpriteState returns early when the state
    # already equals the one asked for, so a crack authored at 1 never transmits.
    # Statnum 4, kStatThing. This was on statnum 0, and that alone is why the
    # charges never went off: `actDamageSprite` runs the health-and-trigger path
    # under `case kStatThing` only, and `actInit` hands out `startHealth` on the
    # same list. Off it, a crack is scenery -- it cannot be hurt, so it never
    # reaches zero health, never calls `trTriggerSprite`, and never transmits.
    #
    # cstat 209 is the campaign's, blocking and wall-aligned and one-sided. The
    # 256 bit this used to carry was there to let a bullet reach it, which
    # cannot work: `thingInfo` for kThingWallCrack is dmgControl
    # {0, 0, 0, 256, 0, 0, 0}, and index 3 is kDamageExplode -- every other
    # damage type, kDamageBullet included, is multiplied by zero. A crack is
    # opened by a blast and by nothing else, which is why `trigger_vector` goes
    # too. The TNT in the courtyard is the key to this door.
    layout.place_on_wall("crack_crypt", "region:crypt_hall", a1=P(25, 50), a2=P(29, 50), t=0.5,
                         height_player_heights=1.6, offset_player_widths=0.06,
                         type=408, picnum=1127, status=4, cstat=209,
                         x_repeat=64, y_repeat=64, shade=-8,
                         # (decoupled 0, state 0, trigger_off 1, trigger_on 1)
                         # is what 105 of the campaign's 108 cracks carry.
                         behavior={"tx_id": CH_BREACH, "command": 1, "state": 0,
                                   "trigger_on": 1, "trigger_off": 1})
    # The charges. trInit clamps an exploder's waitTime to at least 1 and only
    # arms them on kStatTraps, and OperateSprite explodes one on any command that
    # is not kCmdOn -- so an RX channel plus a waitTime is the whole fuse. Two of
    # them, staggered, which is the median the campaign wires to one crack.
    for index, (x, y, fuse) in enumerate(((26, 48, 1), (28, 47, 3)), start=1):
        layout.add_sprite(f"charge_crypt_{index:02d}", "region:crypt_charnel",
                          x=P(x, y)[0], y=P(x, y)[1], z=CRYPT_FLOOR,
                          type=459, picnum=908, status=11, cstat=32896,
                          x_repeat=4, y_repeat=4, shade=-8,
                          behavior={"rx_id": CH_BREACH, "wait_time": fuse})

    # ---- the well, and the swim under it ------------------------------------
    #
    # A dive that skips the crypt gate: down the courtyard well, along a flooded
    # undercroft, and up into the crypt hall.
    #
    # Both mouths dive by the same translation, so the flooded space is the dry
    # level's geography carried whole rather than two shafts parked next to each
    # other. The well head and the crypt pool sit 33 player widths apart above
    # and 33 apart below, which is what makes the swim between them a distance
    # the player could actually have covered.
    layout.carve_hole("region:courtyard", WELL_MOUTH)
    layout.add_region("region:well", WELL_MOUTH, role="interior",
                      ceiling_z=COURT - tex(3), floor_z=WELL_SURFACE,
                      wall_picnum=449, floor_picnum=WATER_SURFACE_TILE,
                      ceiling_picnum=67,
                      intent={"purpose": "round well head; its floor is the water surface you "
                                         "dive through, which is why it carries the water tile",
                              "classification": "OPTIONAL"})
    # A rim, not a passage: the player drops in over whichever segment they walk
    # into, so the declared width is one player rather than a doorway, and the
    # shaped mouth's shortest chamfer (429) has to clear it rather than a square
    # mouth's uniform edge.
    for index in range(len(WELL_MOUTH)):
        layout.add_connection(
            f"connection:well_{index:02d}", "region:courtyard", "region:well",
            a1=WELL_MOUTH[index], a2=WELL_MOUTH[(index + 1) % len(WELL_MOUTH)],
            min_width=384)

    layout.carve_hole("region:crypt_hall", CRYPT_MOUTH)
    layout.add_region("region:crypt_pool", CRYPT_MOUTH, role="interior",
                      ceiling_z=CRYPT_CEIL, floor_z=CRYPT_FLOOR + 2048,
                      wall_picnum=449, floor_picnum=WATER_SURFACE_TILE,
                      ceiling_picnum=67,
                      intent={"purpose": "a crack in the crypt floor the undercroft surfaces "
                                         "into", "classification": "OPTIONAL"})
    for index in range(len(CRYPT_MOUTH)):
        layout.add_connection(
            f"connection:cryptpool_{index:02d}", "region:crypt_hall", "region:crypt_pool",
            a1=CRYPT_MOUTH[index], a2=CRYPT_MOUTH[(index + 1) % len(CRYPT_MOUTH)],
            min_width=384)

    # The sunk rooms share no wall with the dry level: the marker pair is the
    # only way in, which is how 152 of the campaign's 191 pairs are built. The
    # two shafts are the mouths themselves, carried down; the passages between
    # them are the distance.
    def sunk(name, points, purpose, *, under_pool=False):
        layout.add_region(name, points, role="interior",
                          ceiling_z=SUNK_CEIL, floor_z=SUNK_FLOOR,
                          **(SUNK_UNDER_POOL if under_pool else SUNK_TILES),
                          # 18, not 44. The campaign's 618 underwater sectors sit
                          # at a median floor shade of 26 and ceiling of 30; this
                          # run was emitting 52 and 57, dark enough that the only
                          # thing you could tell about it was that you were in it.
                          # 18 is what lands on 26 once `match_corpus_shade` has
                          # applied the level's exposure offset.
                          sector_behavior={"underwater": 1},
                          intent={"purpose": purpose, "classification": "OPTIONAL"})

    sunk("region:sunk_well", dive(WELL_MOUTH),
         "the flooded shaft under the well head", under_pool=True)
    sunk("region:sunk_crypt", dive(CRYPT_MOUTH),
         "the flooded shaft under the crypt crack", under_pool=True)
    sunk("region:sunk_descent", R(14, 24 + 56, 18, 44 + 56), "flooded passage running south")
    sunk("region:sunk_vault", R(14, 44 + 56, 28, 50 + 56),
         "flooded vault at the bottom of the run")
    # The rise meets the crypt mouth on the mouth's own top edge, which runs
    # x 25..27 rather than the full width: the shaft is a crack, not a box.
    sunk("region:sunk_rise", R(25, 50 + 56, 27, 52 + 56), "flooded passage running back north")
    # Three of these are the width of the shaft they belong to rather than of a
    # corridor: once the mouths stopped being squares, the well's flat bottom is
    # two units across and the crypt crack is two units across, so the joins that
    # meet them are too. They are declared at what the shape gives, because a
    # declaration copied from the square-mouth version is a claim about geometry
    # that no longer exists -- the gate caught exactly that.
    for tag, a, b, a1, a2, width in (
        ("well_descent", "region:sunk_well", "region:sunk_descent",
         (15, 24 + 56), (17, 24 + 56), 768),
        ("descent_vault", "region:sunk_descent", "region:sunk_vault",
         (14, 44 + 56), (18, 44 + 56), 1536),
        ("vault_rise", "region:sunk_vault", "region:sunk_rise",
         (25, 50 + 56), (27, 50 + 56), 768),
        ("rise_crypt", "region:sunk_rise", "region:sunk_crypt",
         (25, 52 + 56), (27, 52 + 56), 768),
    ):
        layout.add_connection(f"connection:sunk_{tag}", a, b,
                              a1=P(*a1), a2=P(*a2), min_width=width)

    # The markers. Up sits between the pool's floor and ceiling -- 187 of the
    # campaign's 191 put it there -- and low sits on the sunk sector's ceiling,
    # which 169 of them do. Tiles 2332 and 2331, statnum 0, cstat 128. The low
    # marker is the up marker carried by the level's translation, like the room.
    for tag, pool, sunk_id, link, up_at, up_z in (
        ("well", "region:well", "region:sunk_well", WATER_LINK_WELL,
         (16, 22), WELL_SURFACE - 1024),
        ("crypt", "region:crypt_pool", "region:sunk_crypt", WATER_LINK_CRYPT,
         (26, 54), CRYPT_FLOOR + 1024),
    ):
        up_point = P(*up_at)
        layout.add_sprite(f"water_up_{tag}", pool,
                          x=up_point[0], y=up_point[1], z=up_z,
                          type=9, picnum=2332, cstat=128, status=0,
                          x_repeat=64, y_repeat=64, angle=0,
                          behavior={"data_1": link})
        low_point = dive([up_point])[0]
        layout.add_sprite(f"water_low_{tag}", sunk_id,
                          x=low_point[0], y=low_point[1], z=SUNK_CEIL,
                          type=10, picnum=2331, cstat=128, status=0,
                          x_repeat=64, y_repeat=64, angle=0,
                          behavior={"data_1": link})

    # ---- population -------------------------------------------------------
    #
    # The campaign puts 32.5 dudes and 29.3 pickups per 100 playable sectors,
    # leaves 89% of its sectors empty, keeps the nearest enemy a median 3 hops
    # from the spawn, and lands close to one pickup per dude. At 40 sectors that
    # is about thirteen and twelve, concentrated in a handful of rooms rather
    # than sprinkled -- which is the part a density alone would get wrong.
    for tag, region, kind, x, y, z in (
        ("court_a", "region:courtyard", 202, 20, 12, COURT),
        ("court_b", "region:courtyard", 202, 44, 30, COURT),
        ("court_c", "region:courtyard", 201, 46, 12, COURT),
        ("nave_a", "region:chapel_nave", 201, 32, 22, COURT),
        ("nave_b", "region:chapel_nave", 203, 34, 26, COURT),
        ("aisle", "region:chapel_aisle_north", 203, 32, 30, COURT),
        ("crypt_a", "region:crypt_hall", 203, 28, 55, CRYPT_FLOOR),
        ("crypt_b", "region:crypt_hall", 203, 38, 52, CRYPT_FLOOR),
        ("crypt_c", "region:crypt_hall", 211, 32, 57, CRYPT_FLOOR),
        ("gallery_a", "region:gallery", 206, 70, 14, GALLERY_FLOOR),
        ("gallery_b", "region:gallery", 206, 72, 22, GALLERY_FLOOR),
        ("gallery_c", "region:gallery", 201, 70, 30, GALLERY_FLOOR),
        ("ossuary", "region:ossuary", 203, 49, 55, CRYPT_FLOOR),
        # the cloister wing
        ("walk_n", "region:walk_north", 201, 38, -17, COURT),
        ("garth", "region:garth", 203, 30, -8, GARTH_FLOOR),
        ("chapter_a", "region:chapter_house", 202, 52, -11, COURT),
        ("refectory", "region:refectory", 201, 8, -8, COURT),
        # The flooded run. A Gill Beast is a thing you meet under water and
        # nowhere else, and the whole point of a dive is that it costs something.
        ("sunk_a", "region:sunk_vault", 217, 18, 103, SUNK_FLOOR),
        ("sunk_b", "region:sunk_descent", 217, 16, 92, SUNK_FLOOR),
        # The garden, which had nothing in it at all. 12.1 dudes per 100 playable
        # sectors against a campaign median of 32.5 is not an atmosphere, it is
        # an empty building -- and the new wing was the emptiest part of it.
        ("garden_a", "region:garden_court", 201, 58, -38, GARDEN_LAWN),
        ("garden_b", "region:garden_court", 203, 78, -60, GARDEN_LAWN),
        ("garden_c", "region:garden_court", 201, 62, -50, GARDEN_LAWN),
        ("shrine", "region:shrine_1", 202, 75, -45, GARDEN_LAWN - 2048),
        ("grotto", "region:cascade_grotto", 206, 75, -71, GARDEN_POOL),
        ("graveyard_a", "region:graveyard", 203, 41, -63, COURT),
        ("graveyard_b", "region:graveyard", 201, 44, -73, COURT),
        ("porch", "region:garden_porch_e", 202, 59, -29, COURT),
        ("passage", "region:garden_passage", 201, 55, -20, COURT),
        ("belfry", "region:belfry", 211, 36, -51, BELFRY_FLOOR),
    ):
        layout.add_sprite(f"dude_{tag}", region, x=P(x, y)[0], y=P(x, y)[1], z=z,
                          angle=1024, **DUDE[kind])
    for tag, region, kind, x, y, z in (
        ("ledge", "region:ledge", 41, -6, 22, COURT),
        ("court_shells", "region:courtyard", 68, 18, 30, COURT),
        ("court_med", "region:courtyard", 109, 48, 24, COURT),
        ("gatehouse", "region:gatehouse", 76, 8, 22, COURT),
        ("walk_shells", "region:walk_north", 68, 18, -17, COURT),
        ("garth_med", "region:garth", 109, 26, -8, GARTH_FLOOR),
        ("chapter_ammo", "region:chapter_house", 72, 55, -8, COURT),
        ("refectory_med", "region:refectory", 109, 8, -12, COURT),
        ("cell_armor", "region:cloister_cell", 63, 27, -23, COURT),
        ("approach_ammo", "region:gallery_approach", 76, 60, 8, GALLERY_FLOOR),
        ("nave_tommy", "region:chapel_nave", 42, 30, 24, COURT),
        ("aisle_drum", "region:chapel_aisle_south", 72, 32, 16, COURT),
        ("apse_med", "region:chapel_apse", 107, 40, 23, APSE_FLOOR),
        ("crypt_tnt", "region:crypt_hall", 63, 34, 52, CRYPT_FLOOR),
        ("crypt_med", "region:crypt_hall", 109, 26, 57, CRYPT_FLOOR),
        ("charnel", "region:crypt_charnel", 109, 27, 47, CRYPT_FLOOR),
        ("ossuary_flare", "region:ossuary", 76, 47, 55, CRYPT_FLOOR),
        ("gallery_shells", "region:gallery", 68, 72, 26, GALLERY_FLOOR),
        # Likewise items: 13.6 per 100 sectors against a campaign median of 29.3.
        ("grotto_armor", "region:cascade_grotto", 63, 76, -70, GARDEN_POOL),
        ("garden_med", "region:garden_court", 109, 55, -66, GARDEN_LAWN),
        ("garden_shells", "region:garden_court", 68, 84, -40, GARDEN_LAWN),
        ("shrine_flare", "region:shrine_3", 76, 80, -50, GARDEN_LAWN - 6144),
        ("graveyard_med", "region:graveyard", 109, 31, -68, COURT),
        ("graveyard_tnt", "region:graveyard", 63, 26, -58, COURT),
        ("breach_ammo", "region:garden_breach", 72, 53, -62, COURT + 4096),
        ("sunk_med", "region:sunk_vault", 109, 24, 102, SUNK_FLOOR),
        ("belfry_ammo", "region:belfry", 76, 33, -50, BELFRY_FLOOR),
        ("porch_shells", "region:garden_porch_w", 68, 54, -29, COURT),
    ):
        layout.add_sprite(f"item_{tag}", region, x=P(x, y)[0], y=P(x, y)[1], z=z,
                          angle=0, **PICKUP[kind])

    # Breakable props. The largest single difference between this level and E1M1
    # was not its rooms: E1M1 carries 183 kThingObjectGib/Explode against this
    # level's 3, and the campaign runs a median of 33 per 100 playable sectors.
    # They are what makes a room look occupied and give the player something to
    # shoot that is not a cultist.
    for tag, region, kind, x, y, z in (
        ("court_a", "region:courtyard", "crate", 18, 8, COURT),
        ("court_b", "region:courtyard", "crate", 20, 9, COURT),
        ("court_c", "region:courtyard", "barrel", 48, 34, COURT),
        ("court_d", "region:courtyard", "urn", 46, 36, COURT),
        ("gate_a", "region:gatehouse", "urn", 8, 19, COURT),
        ("nave_a", "region:chapel_nave", "urn", 30, 20, COURT),
        ("nave_b", "region:chapel_nave", "urn", 34, 20, COURT),
        ("aisle_a", "region:chapel_aisle_south", "crate", 31, 16, COURT),
        ("aisle_b", "region:chapel_aisle_north", "crate", 33, 30, COURT),
        ("apse_a", "region:chapel_apse", "urn", 39, 24, APSE_FLOOR),
        ("crypt_a", "region:crypt_hall", "urn", 27, 52, CRYPT_FLOOR),
        ("crypt_b", "region:crypt_hall", "urn", 36, 58, CRYPT_FLOOR),
        ("crypt_c", "region:crypt_hall", "barrel", 30, 57, CRYPT_FLOOR),
        ("relic_a", "region:crypt_reliquary", "urn", 19, 54, CRYPT_FLOOR),
        ("relic_b", "region:crypt_reliquary", "crate", 20, 56, CRYPT_FLOOR),
        ("ossuary_a", "region:ossuary", "urn", 47, 53, CRYPT_FLOOR),
        ("ossuary_b", "region:ossuary", "urn", 49, 57, CRYPT_FLOOR),
        ("charnel_a", "region:crypt_charnel", "urn", 27, 47, CRYPT_FLOOR),
        ("gallery_a", "region:gallery", "barrel", 68, 16, GALLERY_FLOOR),
        ("gallery_b", "region:gallery", "crate", 70, 18, GALLERY_FLOOR),
        ("gallery_c", "region:gallery", "crate", 71, 19, GALLERY_FLOOR),
        ("gallery_d", "region:gallery", "urn", 74, 36, GALLERY_FLOOR),
        ("exit_a", "region:exit_hall", "barrel", 84, 27, GALLERY_FLOOR),
        ("walk_a", "region:walk_north", "urn", 20, -17, COURT),
        ("walk_b", "region:walk_north", "crate", 42, -17, COURT),
        ("walk_c", "region:walk_south", "urn", 20, 0, COURT),
        ("walk_d", "region:walk_east", "barrel", 43, -5, COURT),
        ("garth_a", "region:garth", "urn", 22, -12, GARTH_FLOOR),
        ("chapter_a", "region:chapter_house", "crate", 54, -12, COURT),
        ("chapter_b", "region:chapter_house", "crate", 55, -11, COURT),
        ("refect_a", "region:refectory", "barrel", 7, -11, COURT),
        ("refect_b", "region:refectory", "urn", 9, -5, COURT),
    ):
        layout.add_sprite(f"prop_{tag}", region, x=P(x, y)[0], y=P(x, y)[1], z=z,
                          seat="floor", angle=0, **breakable(kind))

    # ---- ambience ----------------------------------------------------------
    # Sound ids are the campaign's own most-used: 27 is its commonest ambience
    # by a wide margin, then 39, 40 and 32.
    #
    # The two radii come from a short list of round numbers rather than from
    # arithmetic on the room: across 1,778 campaign ambiences `data1` is 75, 100,
    # 150, 200, 300 or 500 and `data2` is 150, 200, 300, 400, 500 or 1000. Four
    # of the six below were tuned to the room instead and landed on values --
    # 60, 90, 140, 160, 180, 240 -- that the game never uses.
    for tag, region, sound, x, y, z, near, far in (
        ("court", "region:courtyard", 27, 20, 34, COURT, 100, 300),
        ("gate", "region:gatehouse", 32, 8, 22, COURT, 75, 150),
        ("nave", "region:chapel_nave", 39, 32, 24, COURT, 75, 150),
        ("crypt", "region:crypt_hall", 40, 32, 55, CRYPT_FLOOR, 75, 200),
        ("cistern", "region:crypt_cistern", 12, 30, 62, CISTERN_FLOOR, 75, 150),
        ("gallery", "region:gallery", 13, 72, 26, GALLERY_FLOOR, 100, 200),
        ("garth", "region:garth", 27, 30, -8, GARTH_FLOOR, 100, 300),
        ("chapter", "region:chapter_house", 39, 52, -8, COURT, 75, 150),
    ):
        layout.add_sprite(f"amb_{tag}", region, x=P(x, y)[0], y=P(x, y)[1], z=z,
                          angle=0, **ambience(sound, near=near, far=far))
    layout.add_sprite("sfx_crypt", "region:crypt_hall",
                      x=P(30, 53)[0], y=P(30, 53)[1], z=CRYPT_FLOOR,
                      angle=0, **sector_sfx(106))

    layout.place_on_wall("sw_ossuary", "region:crypt_cistern", a1=P(32, 66), a2=P(28, 66), t=0.5,
                         height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
                         **SWITCH,
                         # Toggle, for the same reason as the crypt gate.
                         behavior={"tx_id": CH_SECRET, "command": 3, "trigger_on": 1,
                                   "trigger_push": 1, "data_1": 203})
    layout.place_on_wall("sw_exit", "region:exit_hall", a1=P(88, 20), a2=P(88, 28), t=0.5,
                         height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
                         **SWITCH,
                         behavior={"tx_id": CH_EXIT, "command": 1, "trigger_on": 1, "trigger_push": 1})
    # No behaviour needed now: a key is statnum 3, and the compiler gives every
    # sprite on that list an XSprite whether or not one is asked for. All 29
    # campaign keys rest at state 0.
    layout.place_on_floor("key_skull", "region:crypt_reliquary", local=(0.5, 0.5),
                          **sprite_appearance(100))

    # ---- niches, on the corpus recess profile -------------------------------
    # 792 recesses across all 42 campaign maps: floor flush with the host in
    # roughly three quarters of them, a lowered ceiling in a third, and a
    # footprint of a few percent of the host.  These are the first in the level
    # that were not really side rooms wearing a niche's name.
    recess(layout, "recess:crypt_niche",
           anchor=Anchor("region:crypt_hall", P(38, 60), P(36, 60)),
           depth=int(1.5 * U), ceiling_drop=tex(2), **CRYPT_CELL_TILES,
           intent={"purpose": "wall niche in the crypt hall", "classification": "OPTIONAL"})
    recess(layout, "recess:gallery_niche",
           anchor=Anchor("region:gallery", P(62, 30), P(62, 26)),
           depth=int(1.5 * U), ceiling_drop=tex(6), **GALLERY_TILES,
           intent={"purpose": "wall niche in the gallery", "classification": "OPTIONAL"})
    recess(layout, "recess:exit_niche",
           anchor=Anchor("region:exit_hall", P(84, 30), P(82, 30)),
           depth=int(1.5 * U), ceiling_drop=tex(4), **EXIT_TILES,
           intent={"purpose": "wall niche in the exit chamber", "classification": "OPTIONAL"})

    _decorate(layout)

    # ---- detail ------------------------------------------------------------
    #
    # A Blood level is mostly small sectors: 68% of E1M1's are under 20 player
    # widths squared, and its alcoves alone number 32. This level had five,
    # because `recess` builds one niche per call and nobody writes thirty-nine
    # calls. `alcove_run` takes a wall instead, which is the unit these are
    # actually authored in.
    for tag, region, a, b, drop in (
        # split around the cloister gate, which stands in the middle of this wall
        ("nich_walk_sw", "region:walk_south", P(26, 2), P(14, 2), 2048),
        ("nich_walk_se", "region:walk_south", P(46, 2), P(30, 2), 2048),
        ("nich_chapter", "region:chapter_house", P(56, -14), P(58, -12), 0),
        ("nich_refect", "region:refectory", P(4, -14), P(14, -14), 2048),
        # split around the cloister cell and the tower foot, both of which
        # open north through this same wall
        ("nich_walk_nw", "region:walk_north", P(14, -20), P(23, -20), 2048),
        ("nich_walk_ne", "region:walk_north", P(41, -20), P(46, -20), 2048),
        ("nich_walk_e", "region:walk_east", P(46, -2), P(46, -14), 2048),
        ("nich_walk_w", "region:walk_west", P(14, -14), P(14, -2), 2048),
        ("nich_crypt_n", "region:crypt_hall", P(24, 50), P(39, 50), 2048),
        ("nich_gallery_w", "region:gallery", P(62, 12), P(62, 40), 3072),
        ("nich_gallery_e", "region:gallery", P(76, 39), P(76, 12), 3072),
        ("nich_exit", "region:exit_hall", P(88, 20), P(88, 28), 2048),
    ):
        alcove_run(layout, tag, region_id=region, a=a, b=b, ceiling_drop=drop)

    # Anchor wall textures the way the campaign does. Nothing above this line
    # chooses a y_panning, and a level that pans nothing leaves every seam on an
    # unevenly-tiling wall across the middle of it; Blood pans 46% of exactly
    # those walls. It runs after compile because it needs each wall's picnum and
    # its sector's heights, and only touches walls no one has panned already.
    # A rotate sector names its axis by sprite index, which only exists once the
    # level is emitted, so the binding is a post-compile step like the alignment.
    # Marker binding is no longer a hook here -- `PlanarLayout.compile` does it
    # for every layout, before the structure is validated.
    layout.post_compile.append(_bind_rotation_axis)
    layout.post_compile.append(
        lambda level: _ALIGNMENT.update(align_wall_textures(level, wall_art_sizes())))
    # And the horizontal axis, which nothing here had ever set. Every wall began
    # its texture at panning zero, so the pattern restarted at every vertex --
    # including the ones that are not corners, where a long wall was only split
    # to hang a doorway off it. 3% of this level's same-tile joins continued
    # against a campaign median of 48%.
    layout.post_compile.append(
        lambda level: _ALIGNMENT.update(align_wall_runs(level, wall_art_sizes())))
    # Every room here had exactly one wall shade, so nothing in it lit anything
    # and the level read flat. Wall facing explains 81% of the campaign's
    # within-room shade variation -- more than texture's 52%, and far more than
    # the lamps, which are too rare to account for much -- and it carries no
    # global bias, so each room has its own implied direction. Here that is the
    # room's lamp where it has one and its widest opening where it does not.
    # Water moves. 112 of the campaign's 618 underwater sectors animate their
    # shade, 69 of them on wave 7 at amplitude -4 -- not a flame guttering but
    # the surface overhead breaking the light up.
    layout.post_compile.append(
        lambda level: _LIGHTING.update(ripple=ripple_underwater_sectors(level)))
    # Then light that knows where the walls are.
    #
    # `shade_walls_by_light`, which this replaces, brightened a wall by its
    # distance to the nearest lamp -- and distance is not what light does. A
    # torch on the far side of a partition lit the near side exactly as much as
    # the far, and a lamp in the crypt hall lit the cistern through the stone,
    # because nothing in the calculation had ever heard of the stone.
    #
    # XMapEdit ships the answer and it is not a heuristic: several thousand rays
    # out of each flame, followed through the map with a hitscan, depositing
    # energy where they land and reflecting twice. See `bloodmap.lightbomb` --
    # including why its two free parameters are fitted to the campaign's own
    # measured falloff rather than left at the editor's defaults.
    layout.post_compile.append(
        lambda level: _LIGHTING.update(bomb=light_bomb(
            level, lights_in(level, LIGHT_TILES))))
    # And the room-scale gradient on top, for the four rooms in five that have no
    # flame in them at all and so receive no rays.
    layout.post_compile.append(
        lambda level: _LIGHTING.update(shade_walls_directionally(level)))
    # And a moving offset on top of that base. Blood animates the shade of one
    # playable sector in five, and 65% of the ones with a lamp in them; this
    # level animated none, so its torches were painted light rather than light.
    # Dress the openings. Every room in this level was painted in a single wall
    # tile -- 90% of them, against a campaign 37% -- and that one fact carries
    # three of the level's four worst deviations at once: `visual.contrast` 18
    # against 48, `composition.wall` 0.665 against 0.501, `tile_variety` 4
    # against 6. A room with one material has nothing in it for the eye to
    # measure the room by.
    #
    # The pairs are the campaign's own, taken from which tiles actually share a
    # room with which: 91 with 90 in 25% of the rooms 91 appears in, 180 with
    # 110 in 38%, 427 with 556 in 21%. 110 -- this level's commonest wall by
    # far -- goes with 5, attested both directions, and it is also the right
    # answer for the building: 110 is rubble and 5 is dressed ashlar, which is
    # where the stone goes that has to hold an opening up.
    OPENING_DRESS = {110: 5, 91: 90, 180: 110, 427: 556, 568: 108}
    for region in layout.regions.values():
        if region.role in ("stair", "doorway"):
            continue          # a stair has no openings to dress and a door is a door
        dress = OPENING_DRESS.get(int(region.wall_picnum))
        if dress is not None and region.door_face is None:
            region.portal_wall_picnum = dress

    # Exposure last, after every relative decision has been made: the pools, the
    # directions and the author's own choices are all differences, and this moves
    # only where the whole set sits.
    layout.post_compile.append(
        lambda level: _LIGHTING.update(exposure=match_corpus_shade(level)))
    layout.post_compile.append(
        lambda level: _LIGHTING.update(flicker=flicker_lit_sectors(level)))
    return layout


#: The sweep of each rotating door, by the region that owns it. Kept out of the
#: sprite because `add_sprite` reduces an angle mod 2048 -- correct for a facing
#: direction and wrong for this. Blood interpolates the turn from 0 to the
#: marker angle, so the sign is the direction: -512 is a quarter turn one way
#: and 1536 is three quarters the other, reaching the same pose by sweeping the
#: panel through everything beside it.
ROTATION_SWEEP = {"region:ossuary_door": -512}


def _bind_rotation_axis(level) -> None:
    """Write each rotate pivot's sweep angle raw.

    The binding this used to do -- pointing the sector's `marker_0` at the pivot
    -- moved to `mechanism.bind_markers`, which does it through the field the
    engine actually reads. What is left is the angle, which cannot go through
    `add_sprite` because that reduces it mod 2048: correct for a facing
    direction, wrong for a signed sweep.
    """
    for index, sprite in enumerate(level.sprites):
        fields = sprite["fields"]
        if int(fields["type"]) != 5:
            continue
        sector = level.sectors[int(fields["sector"])]
        if int(sector["fields"]["type"]) != 617:
            continue
        fields["angle"] = ROTATION_SWEEP.get("region:ossuary_door", -512)

    # A shootable screen is a wall *type*, which is not an XWALL field, so the
    # connection cannot state it and the hook does. Two-sided only: a gib wall
    # with nothing behind it is a hole in the outside of the level.
    for wall in level.walls:
        fields = wall["fields"]
        if int(fields["picnum"]) == GIB_FACE and int(fields["next_sector"]) >= 0:
            fields["type"] = 511

    # A slide names two markers, kMarkerOff and kMarkerOn, the same way.
    for index, sprite in enumerate(level.sprites):
        fields = sprite["fields"]
        if int(fields["type"]) not in (3, 4):
            continue
        sector = level.sectors[int(fields["sector"])]
        if int(sector["fields"]["type"]) not in (614, 615, 616, 617):
            continue
        blood = sector.get("blood")
        if blood is None:
            continue
        blood["fields"]["marker_0" if int(fields["type"]) == 3 else "marker_1"] = index


def _decorate(layout: PlanarLayout) -> None:
    """Decoration attached to architectural roles, sized to the room it stands in."""
    # Square repeats, everywhere but the grille.
    #
    # `aspect` was a mistake with a plausible-sounding reason behind it: these
    # tiles are tall and narrow, so their repeats were made tall and narrow to
    # match. But `x_repeat` scales the tile's *own* width, and the tile is
    # already 12 pixels across -- so squashing it again drew a torch a third of
    # its proper width and a column of bubbles at 0.16, which is what "extremely
    # thin" was. 16,746 of the campaign's 18,858 sprites use x_repeat ==
    # y_repeat, and the ratio's q1, median and q3 are all exactly 1.00.
    #
    # The exception is 1044, and it earns it: a fence leaf is sized to the
    # opening it has to fill, and the campaign's own modal repeat for it is
    # x64 y88, a ratio of 0.73.
    torch = lambda ph: decor(506, 128, ph, shade=-128)                      # noqa: E731
    # Tiles 2540-2545 are gone from this level. They are six identical 58x58
    # icons -- Blood's key placards, the signs that mark a keyed door -- and
    # using them as wall furniture hung a key symbol on the chapter house, the
    # reliquary, the ossuary and every 'emblem' in the map. A level that
    # signposts eight keyed doors and has one key is lying to the player.
    #
    # 795 was the first replacement and the wrong one. It is the campaign's
    # commonest decoration, 159 uses -- but its canonical cstat is 224, which is
    # *floor* alignment: it is a grate laid on the ground. Hung on a wall by
    # `place_on_wall` it became eleven flat discs floating edge-on in mid-air.
    # The mounting is part of the tile, and a table of canonical cstats is a
    # table of mountings, not of appearances.
    #
    # 915 is wall-aligned (cstat 208), 56 uses, drawn between 1.5 and 4.5 player
    # heights -- a plaque, which is what these places want.
    sconce = lambda ph: decor(510, 208, ph)                                 # noqa: E731
    emblem = lambda pic, ph: decor(915, 208, ph)                            # noqa: E731
    # The corpus gives four of these tiles a vertical habit, and the rest none.
    # Tile 1044 puts its bottom on the floor in 63% of 63 uses, 660 in 91% of
    # 86 and 664 in 94% of 68; 1701 puts its top against the ceiling in 81% of
    # 53. Those four say where they go, so they are seated rather than hung at
    # a height chosen here. The torches, sconces, emblems, planks and discs have
    # no such habit -- they sit wherever the wall wants them -- and are left to
    # the wall anchor, which now keeps the whole sprite inside the room.
    #
    # 1044 also gains its blocking bit: 412 is 413 without it, so every grille
    # in the level was scenery the player walked through.
    grille = lambda ph: dict(decor(1044, 413, ph, aspect=0.73), seat="floor")  # noqa: E731
    chain = lambda ph: decor(641, 128, ph, shade=-128)                      # noqa: E731
    # 660 and 664 are aquatic, and were being used all over the dry level as a
    # creeper and a pot plant. The campaign places 664 in 82 sectors and every
    # single one is under water; 660 in 142, likewise. Blood simply has no dry
    # climbing plant -- the tiles that look like candidates when you sort by
    # usage turn out to be a wooden pedestal, a candelabra and a stone column.
    #
    # So overgrowth on land is 599, its bush: 35 dry uses, none wet, drawn at a
    # median of 2.41 player heights. The two green strands now appear only in
    # the flooded run, which is the one place in this level they belong.
    shrub = lambda ph=2.4: decor(599, 1 | 128 | 256, ph, shade=6)           # noqa: E731
    plank = lambda ph: decor(68, 464, ph)                                   # noqa: E731
    lamp = lambda ph: decor(1701, 384, ph, shade=-128)                      # noqa: E731
    # Floor-aligned (cstat 232 & 0x30 == 0x20): a flat plate, not a facing
    # sprite. That makes it a ceiling light and nothing else -- it was also on a
    # cistern wall, where it hung edge-on in the air.
    disc = lambda ph: decor(795, 232, ph)                                   # noqa: E731

    # -- approach (ledge 6 PH, tunnel 3 PH, gatehouse 5 PH) -------------------
    layout.place_on_wall("dec_ledge_torch", "region:ledge", a1=P(-10, 24), a2=P(-10, 20),
                         t=0.5, height_player_heights=1.9, offset_player_widths=0.10, **torch(1.5))
    layout.place_on_wall("dec_tunnel_torch", "region:gate_tunnel", a1=P(-2, 21), a2=P(6, 21),
                         t=0.7, height_player_heights=1.5, offset_player_widths=0.10, **torch(1.0))
    layout.place_on_wall("dec_gate_emblem", "region:gatehouse", a1=P(10, 27), a2=P(6, 24),
                         t=0.5, height_player_heights=2.6, offset_player_widths=0.12, **emblem(2540, 1.0))
    layout.place_on_wall("dec_gate_grille", "region:gatehouse", a1=P(6, 20), a2=P(10, 17),
                         t=0.5, height_player_heights=1.9, offset_player_widths=0.12, **grille(1.6))

    # -- courtyard: the chapel mass is the courtyard's own hole boundary ------
    for name, t_value in (("south", 0.30), ("north", 0.70)):
        layout.place_on_wall(f"dec_chapel_torch_{name}", "region:courtyard",
                             a1=P(24, 14), a2=P(24, 32), t=t_value,
                             height_player_heights=1.9, offset_player_widths=0.10, **torch(1.5))
    for name, t_value in (("south", 0.06), ("north", 0.94)):
        layout.place_on_wall(f"dec_chapel_vine_{name}", "region:courtyard",
                             a1=P(24, 14), a2=P(24, 32), t=t_value,
                             height_player_heights=0.05, offset_player_widths=0.12, **shrub())
    layout.place_on_wall("dec_court_emblem", "region:courtyard", a1=P(44, 32), a2=P(44, 14),
                         t=0.5, height_player_heights=2.6, offset_player_widths=0.12, **emblem(2545, 1.2))

    for name, local in (("nw", (0.28, 0.3)), ("ne", (0.72, 0.3)),
                        ("sw", (0.3, 0.7)), ("se", (0.7, 0.7))):
        layout.place_on_floor(f"dec_bed_plant_{name}", "region:garden_bed", local=local, **shrub(1.2))
    layout.place_on_floor("dec_bed_vine_c", "region:garden_bed", local=(0.5, 0.5), **shrub(1.8))

    # -- chapel (nave 10 PH, aisles 6 PH, apse 8 PH) --------------------------
    for name, local in (("west", (0.32, 0.5)), ("east", (0.68, 0.5))):
        layout.place_on_ceiling(f"dec_nave_lamp_{name}", "region:chapel_nave",
                                local=local, height_player_heights=0.8, **lamp(1.3))
    for name, t_value in (("south", 0.16), ("north", 0.84)):
        layout.place_on_wall(f"dec_nave_sconce_{name}", "region:chapel_nave",
                             a1=P(26, 26), a2=P(26, 20), t=t_value,
                             height_player_heights=2.3, offset_player_widths=0.12, **sconce(0.9))
    # A grille set in the arch, not hung beside it: this wall *is* the opening
    # onto the south aisle, and filling it is the whole point of a grille.
    layout.place_on_wall("dec_nave_grille_s", "region:chapel_nave", a1=P(28, 18), a2=P(36, 18),
                         t=0.5, height_player_heights=3.2, offset_player_widths=0.12,
                         spans_opening=True, **grille(1.8))
    for name, t_value in (("south", 0.25), ("north", 0.75)):
        layout.place_on_wall(f"dec_apse_sconce_{name}", "region:chapel_apse",
                             a1=APSE_ARC[1], a2=APSE_ARC[2], t=t_value,
                             height_player_heights=2.1, offset_player_widths=0.12, **sconce(0.9))
    layout.place_on_ceiling("dec_apse_light", "region:chapel_apse", local=(0.5, 0.5),
                            height_player_heights=0.35, **disc(0.7))
    layout.place_on_wall("dec_aisle_s_plank", "region:chapel_aisle_south",
                         a1=P(30, 14), a2=P(34, 14), t=0.5,
                         height_player_heights=1.6, offset_player_widths=0.10, **plank(0.5))
    # The chain is a fixed-size tile -- 5.82 player heights in all 71 of its
    # campaign uses -- and the aisle is 5.8 exactly, so it hangs flush. Any drop
    # at all pushes its foot through the floor, which is what the 0.5 here did.
    layout.place_on_ceiling("dec_aisle_s_chain", "region:chapel_aisle_south",
                            local=(0.7, 0.5), **chain(2.4))
    layout.place_on_wall("dec_aisle_n_plank", "region:chapel_aisle_north",
                         a1=P(34, 32), a2=P(30, 32), t=0.5,
                         height_player_heights=1.6, offset_player_widths=0.10,
                         spans_opening=True, **plank(0.5))
    layout.place_on_ceiling("dec_aisle_n_chain", "region:chapel_aisle_north",
                            local=(0.3, 0.5), **chain(2.4))

    # -- crypt (hall 5 PH, cells 3 PH) ----------------------------------------
    for name, t_value in (("west", 0.15), ("east", 0.85)):
        layout.place_on_wall(f"dec_crypt_grille_{name}", "region:crypt_hall",
                             a1=P(24, 50), a2=P(39, 50), t=t_value,
                             height_player_heights=1.9, offset_player_widths=0.12, **grille(1.5))
    # The crypt hall is 5.1 player heights and the chain is 5.8, so a chain
    # cannot hang here at all -- it was passing through the floor by 0.5 of a
    # player. The hanging lamp is 4.1 and fits with room to spare, which is the
    # decoration this ceiling can actually carry.
    # (The west one sits south to clear the pool cut into the hall floor.)
    for name, local in (("west", (0.2, 0.85)), ("east", (0.8, 0.5))):
        layout.place_on_ceiling(f"dec_crypt_lamp_{name}", "region:crypt_hall",
                                local=local, **lamp(4.1))
    # The crypt hall's north wall is mostly not wall: the cistern opens off it at
    # x 26 to 34 and a niche at 36 to 38, which leaves a strip at 34 to 36 and
    # the ends. t=0.33 puts the emblem on the strip.
    layout.place_on_wall("dec_crypt_emblem", "region:crypt_hall", a1=P(40, 60), a2=P(25, 60),
                         t=0.33, height_player_heights=2.2, offset_player_widths=0.12,
                         **emblem(2545, 1.0))
    layout.place_on_ceiling("dec_crypt_lamp", "region:crypt_hall", local=(0.5, 0.45),
                            **lamp(4.1))
    layout.place_on_wall("dec_reliquary_emblem", "region:crypt_reliquary",
                         a1=P(18, 58), a2=P(16, 56), t=0.5,
                         height_player_heights=1.6, offset_player_widths=0.12, **emblem(2545, 0.8))
    # The reliquary is 2.9 player heights. The campaign's smallest hanging lamp
    # is 4.1 and its chain is 5.8, so this cell takes a wall sconce instead --
    # 1.32, which is what a low stone cell is lit by.
    layout.place_on_wall("dec_reliquary_sconce", "region:crypt_reliquary",
                         a1=P(16, 56), a2=P(16, 54), t=0.5,
                         height_player_heights=1.5, offset_player_widths=0.12, **sconce(1.3))
    layout.place_on_wall("dec_cistern_sconce", "region:crypt_cistern",
                         a1=P(28, 66), a2=P(26, 64), t=0.5,
                         height_player_heights=1.5, offset_player_widths=0.12, **sconce(1.3))
    # 3.3 player heights against a grille that is never drawn below 5.1.
    layout.place_on_wall("dec_cistern_disc", "region:crypt_cistern", a1=P(34, 60), a2=P(34, 64),
                         t=0.5, height_player_heights=1.6, offset_player_widths=0.12, **emblem(915, 1.4))
    layout.place_on_wall("dec_ossuary_emblem", "region:ossuary", a1=P(52, 52), a2=P(52, 58),
                         t=0.5, height_player_heights=1.6, offset_player_widths=0.12, **emblem(2545, 0.8))
    layout.place_on_wall("dec_ossuary_sconce", "region:ossuary", a1=P(50, 60), a2=P(44, 60),
                         t=0.5, height_player_heights=1.5, offset_player_widths=0.12, **sconce(1.3))

    # -- cloister (walks 5 PH, garth open, chapter house 8 PH) ----------------
    # Torches on the walk piers, which is what gives the arcade its rhythm and
    # what the directional lighting pass then has a direction to work from.
    # north_b is at 0.85 rather than 0.7 because the tower foot opens off the
    # north walk at x 33 to 39, and 0.7 put a torch in the middle of it.
    for tag, a1, a2, t in (("south_a", (46, 2), (14, 2), 0.25),
                           ("south_b", (46, 2), (14, 2), 0.75),
                           ("north_a", (14, -20), (46, -20), 0.3),
                           ("north_b", (14, -20), (46, -20), 0.85)):
        layout.place_on_wall(f"dec_walk_torch_{tag}", f"region:walk_{tag.split('_')[0]}",
                             a1=P(*a1), a2=P(*a2), t=t,
                             height_player_heights=1.9, offset_player_widths=0.10,
                             **torch(1.5))
    for tag, local in (("a", (0.25, 0.3)), ("b", (0.75, 0.3)), ("c", (0.5, 0.75))):
        layout.place_on_floor(f"dec_garth_plant_{tag}", "region:garth", local=local,
                              **shrub(1.2))
    layout.place_on_floor("dec_garth_vine", "region:garth", local=(0.5, 0.45), **shrub(1.8))
    # The chapter house's east wall is the landing stair, its whole length --
    # there was no masonry anywhere on it to hang this from. The north wall has
    # some: x 46 to 52, west of the garden passage.
    layout.place_on_wall("dec_chapter_emblem", "region:chapter_house",
                         a1=P(46, -14), a2=P(52, -14), t=0.5,
                         height_player_heights=2.6, offset_player_widths=0.12,
                         **emblem(2540, 1.2))
    layout.place_on_ceiling("dec_chapter_lamp", "region:chapter_house",
                            local=(0.5, 0.5), **lamp(4.1))
    layout.place_on_wall("dec_refectory_plank", "region:refectory",
                         a1=P(4, -14), a2=P(14, -14), t=0.5,
                         height_player_heights=1.6, offset_player_widths=0.10, **plank(0.5))
    layout.place_on_wall("dec_cell_sconce", "region:cloister_cell",
                         a1=P(24, -26), a2=P(30, -26), t=0.5,
                         height_player_heights=1.5, offset_player_widths=0.12, **sconce(1.3))

    # -- gallery (12 PH) ------------------------------------------------------
    for name, t_value in (("a", 0.25), ("b", 0.6), ("c", 0.9)):
        layout.place_on_wall(f"dec_gallery_vine_{name}", "region:gallery",
                             a1=P(64, 10), a2=P(73, 10), t=t_value,
                             height_player_heights=0.05, offset_player_widths=0.12, **shrub())
    for name, t_value in (("d", 0.3), ("e", 0.7)):
        layout.place_on_wall(f"dec_gallery_vine_{name}", "region:gallery",
                             a1=P(74, 42), a2=P(64, 42), t=t_value,
                             height_player_heights=0.05, offset_player_widths=0.12, **shrub())
    for name, t_value in (("north", 0.3), ("south", 0.7)):
        layout.place_on_wall(f"dec_gallery_torch_{name}", "region:gallery",
                             a1=P(76, 12), a2=P(76, 39), t=t_value,
                             height_player_heights=2.2, offset_player_widths=0.10, **torch(1.6))
    layout.place_on_wall("dec_gallery_plank", "region:gallery", a1=P(62, 40), a2=P(62, 12),
                         t=0.12, height_player_heights=1.6, offset_player_widths=0.10,
                         spans_opening=True, **plank(0.6))
    for name, local in (("west", (0.25, 0.5)), ("east", (0.75, 0.5))):
        layout.place_on_ceiling(f"dec_gallery_lamp_{name}", "region:gallery",
                                local=local, height_player_heights=0.9, **lamp(2.2))
    layout.place_on_wall("dec_gallery_grille", "region:gallery", a1=P(64, 10), a2=P(73, 10),
                         t=0.5, height_player_heights=3.5, offset_player_widths=0.12, **grille(2.4))
    layout.place_on_wall("dec_arch_emblem", "region:gallery_arch", a1=P(58, 20), a2=P(62, 20),
                         t=0.5, height_player_heights=2.0, offset_player_widths=0.12, **emblem(2540, 0.9))
    # v2 gave the entry arch an emblem and forgot its twin.
    layout.place_on_wall("dec_looparch_emblem", "region:loop_arch", a1=P(58, 34), a2=P(62, 34),
                         t=0.5, height_player_heights=2.0, offset_player_widths=0.12, **emblem(2540, 0.9))

    # -- exit (8 PH) ----------------------------------------------------------
    for name, t_value in (("north", 0.25), ("south", 0.75)):
        layout.place_on_wall(f"dec_exit_sconce_{name}", "region:exit_hall",
                             a1=P(88, 20), a2=P(88, 28), t=t_value,
                             height_player_heights=2.2, offset_player_widths=0.12, **sconce(0.9))
    layout.place_on_ceiling("dec_exit_light", "region:exit_hall", local=(0.5, 0.5),
                            height_player_heights=0.5, **disc(0.7))
    layout.place_on_wall("dec_exit_chain", "region:exit_hall", a1=P(78, 18), a2=P(86, 18),
                         t=0.5, height_player_heights=2.6, offset_player_widths=0.12, **chain(2.6))


# ---------------------------------------------------------------------------
# Declared intent (unchanged in structure from v1/v2)
# ---------------------------------------------------------------------------

# Region and connection ids are now the vocabulary's, not hand-written ones.
CRYPT_STAIRS = tuple(f"region:stairs:crypt:step_{n:02d}" for n in range(1, 5))
GALLERY_STAIRS = tuple(f"region:stairs:ascent:step_{n:02d}" for n in range(1, 4))
LOOP_STAIRS = tuple(f"region:stairs:return:step_{n:02d}" for n in range(1, 4))
CHANCEL_STAIRS = tuple(f"region:stairs:chancel:step_{n:02d}" for n in range(1, 4))
NICHES = ("region:recess:crypt_niche", "region:recess:gallery_niche",
          "region:recess:exit_niche")

BRIEF = (
    "An abandoned cliffside monastery: an arrival garden courtyard, an embedded "
    "chapel, a lower crypt, and an upper service gallery, forming one coherent "
    "explorable place with distinct spatial and visual identities."
)


def intent() -> AuthoredIntent:
    return AuthoredIntent(
        brief=BRIEF,
        start_region="region:ledge",
        exit_region="region:exit_hall",
        assemblies=(
            AuthoredAssembly(
                "assembly:arrival", "arrival approach", "constrained_approach",
                "a covered ledge, a tight tunnel, and a splayed gatehouse that withhold the courtyard",
                ("region:ledge", "region:gate_tunnel", "region:gatehouse"),
                material_vocabulary=dict(APPROACH_TILES),
            ),
            AuthoredAssembly(
                "assembly:courtyard", "arrival courtyard", "exterior_parent",
                "the large open cliffside courtyard that contains the chapel and the octagonal "
                "garden bed, together with the open stairs that climb out of it",
                ("region:courtyard", "region:garden_bed", *GALLERY_STAIRS, *LOOP_STAIRS),
                material_vocabulary=dict(COURT_TILES),
                landmarks=("the chapel mass standing in the middle of the courtyard",),
            ),
            AuthoredAssembly(
                "assembly:chapel", "chapel", "embedded_building",
                "a tall brick chapel embedded in the courtyard: nave, two aisles, six-sided apse",
                ("region:chapel_door", "region:chapel_nave", "region:chapel_aisle_south",
                 "region:chapel_aisle_north", *CHANCEL_STAIRS, "region:chapel_apse"),
                parent_assembly="assembly:courtyard",
                material_vocabulary=dict(NAVE_TILES),
                landmarks=("the raised chancel at the east end",),
            ),
            AuthoredAssembly(
                "assembly:crypt", "lower crypt", "lower_interior",
                "a vaulted hall with a reliquary and a cistern cell, under a darkening stair",
                ("region:crypt_gate", *CRYPT_STAIRS, "region:crypt_hall",
                 "region:crypt_reliquary", "region:crypt_cistern",
                 "region:crypt_plinth", "region:recess:crypt_niche"),
                material_vocabulary=dict(CRYPT_HALL_TILES),
            ),
            AuthoredAssembly(
                "assembly:ossuary", "optional ossuary", "optional_side_space",
                "an optional room behind a hidden panel in the crypt hall",
                ("region:ossuary_door", "region:ossuary"),
                parent_assembly="assembly:crypt", optional=True, mandatory=False,
            ),
            AuthoredAssembly(
                "assembly:gallery", "upper gallery", "upper_interior",
                "a tall elevated gallery entered through one arch and left through another",
                ("region:gallery_arch", "region:gallery", "region:loop_arch",
                 "region:recess:gallery_niche"),
                material_vocabulary=dict(GALLERY_TILES),
            ),
            AuthoredAssembly(
                "assembly:exit", "exit chamber", "terminal",
                "a keyed chamber that ends the level",
                ("region:exit_door", "region:exit_hall", "region:recess:exit_niche"),
                material_vocabulary=dict(EXIT_TILES),
            ),
        ),
        transitions=(
            AuthoredTransition(
                "transition:reveal", "gatehouse into the courtyard",
                "region:gatehouse", "region:courtyard", "constrained_to_open",
                "the low covered gatehouse should release into the tall open courtyard",
                connection_id="connection:gatehouse_courtyard",
                expectation={"area_ratio_at_least": 8, "clear_height_gain_at_least": 8 * PH},
            ),
            AuthoredTransition(
                "transition:descent", "courtyard down into the crypt",
                "region:courtyard", "region:crypt_hall", "vertical_descent",
                "a darkening stair down into a vaulted hall",
                connection_id="connection:courtyard_cryptgate",
                expectation={"floor_gain_at_least": 4 * CRYPT_STEP},
            ),
            AuthoredTransition(
                "transition:ascent", "arch into the gallery",
                "region:gallery_arch", "region:gallery", "vertical_ascent",
                "a low dark arch opening onto a tall elevated gallery",
                connection_id="connection:arch_gallery",
                expectation={"area_ratio_at_least": 8, "clear_height_gain_at_least": 6 * PH},
            ),
            AuthoredTransition(
                "transition:chapel_entry", "courtyard into the chapel",
                "region:courtyard", "region:chapel_nave", "enclosure",
                "stepping from open sky into a tall enclosed interior",
                connection_id="connection:courtyard_chapeldoor",
            ),
        ),
        progression=(
            {"step": 1, "action": "arrive on the ledge, pass the tunnel and the gatehouse"},
            {"step": 2, "action": "cross the courtyard and enter the chapel"},
            {"step": 3, "action": "use the chancel switch to open the crypt gate",
             "channel": CH_CRYPT_GATE},
            {"step": 4, "action": "descend the crypt stair and take the skull key"},
            {"step": 5, "action": "climb the courtyard stair and pass the gallery arch"},
            {"step": 6, "action": "unlock the keyed exit gate and use the exit switch",
             "channel": CH_EXIT},
            {"step": "optional", "action": "open the ossuary panel from the cistern",
             "channel": CH_SECRET},
        ),
        landmarks=(
            {"landmark": "chapel mass", "regions": ["region:chapel_nave"],
             "claim": "the chapel should be the visual centre of the courtyard"},
            {"landmark": "raised chancel", "regions": ["region:chapel_apse"],
             "claim": "the chancel should be the brightest point inside the chapel"},
        ),
        optional_regions=("region:ossuary_door", "region:ossuary", "region:garden_bed",
                          "region:chapel_aisle_south", "region:chapel_aisle_north",
                          "region:crypt_plinth", *NICHES),
        loops=(
            {"loop": "courtyard -> ascent stair -> gallery arch -> gallery -> loop arch "
                     "-> return stair -> courtyard",
             "claim": "the gallery returns the player to the courtyard by a second route"},
        ),
        material_vocabulary={
            "note": "inherited from v2 unchanged; this iteration changes scale and shape",
            "approach": APPROACH_TILES, "courtyard": COURT_TILES, "garden_bed": BED_TILES,
            "chapel_nave": NAVE_TILES, "chapel_aisles": AISLE_TILES, "chapel_apse": APSE_TILES,
            "crypt_hall": CRYPT_HALL_TILES, "crypt_stair": CRYPT_STAIR_TILES,
            "crypt_cell": CRYPT_CELL_TILES, "crypt_chamber": CRYPT_CHAMBER_TILES,
            "crypt_plinth": PLINTH_TILES,
            "arches": ARCH_TILES, "gallery": GALLERY_TILES,
            "exit": EXIT_TILES,
        },
    )


ALL_CONNECTIONS = (
    "connection:ledge_tunnel", "connection:tunnel_gatehouse", "connection:gatehouse_courtyard",
    *(f"connection:bed_{name}" for name, _a, _b in BED_EDGES),
    "connection:courtyard_chapeldoor", "connection:chapeldoor_nave",
    "connection:nave_aisle_south", "connection:nave_aisle_north", "connection:nave_apse",
    *(f"connection:stairs:chancel:step_{n:02d}" for n in range(1, 4)),
    "connection:stairs:chancel:arrive",
    "connection:courtyard_cryptgate",
    *(f"connection:stairs:crypt:step_{n:02d}" for n in range(1, 5)),
    "connection:stairs:crypt:arrive",
    "connection:crypthall_reliquary", "connection:crypthall_cistern",
    *(f"connection:plinth_{name}" for name, _a, _b in PLINTH_EDGES),
    "connection:recess:crypt_niche:mouth",
    "connection:crypthall_ossuarydoor", "connection:ossuarydoor_ossuary",
    *(f"connection:stairs:ascent:step_{n:02d}" for n in range(1, 4)),
    "connection:stairs:ascent:arrive", "connection:arch_gallery",
    "connection:recess:gallery_niche:mouth",
    "connection:gallery_looparch",
    *(f"connection:stairs:return:step_{n:02d}" for n in range(1, 4)),
    "connection:stairs:return:arrive",
    "connection:gallery_exitdoor", "connection:exitdoor_hall",
    "connection:recess:exit_niche:mouth",
)

OPEN_EXCEPT_SECRET = tuple(
    name for name in ALL_CONNECTIONS
    if name not in {"connection:crypthall_ossuarydoor", "connection:ossuarydoor_ossuary"}
)
CRYPT_GATE_BOTH = ("connection:courtyard_cryptgate", "connection:stairs:crypt:step_01")
CHAPEL_DOOR_BOTH = ("connection:courtyard_chapeldoor", "connection:chapeldoor_nave")


def probes() -> tuple[ProbeRequest, ...]:
    return (
        ProbeRequest("probe:reach_chapel", "access",
                     "can the chapel nave be reached from the start?",
                     "the chapel is mandatory and holds the crypt-gate switch",
                     target_region="region:chapel_nave", opened_connections=CHAPEL_DOOR_BOTH),
        ProbeRequest("probe:reach_apse", "access",
                     "can the raised chancel be reached once the chapel is open?",
                     "the chancel holds the switch the whole crypt branch depends on",
                     target_region="region:chapel_apse", opened_connections=CHAPEL_DOOR_BOTH),
        ProbeRequest("probe:reach_crypt", "access",
                     "can the crypt hall be reached once the crypt gate is open?",
                     "the crypt holds the key the exit needs",
                     target_region="region:crypt_hall", opened_connections=CRYPT_GATE_BOTH),
        ProbeRequest("probe:route_start_to_exit", "route",
                     "what route runs from the start to the exit chamber?",
                     "the brief needs a coherent start-to-exit spine",
                     target_region="region:exit_hall", opened_connections=OPEN_EXCEPT_SECRET),
        ProbeRequest("probe:gallery_seen_late", "visibility",
                     "how far along the start-to-exit route does the gallery first become adjacent?",
                     "the gallery is the last major identity; it should be met late",
                     target_region="region:gallery", opened_connections=OPEN_EXCEPT_SECRET),
        ProbeRequest("probe:reveal_contrast", "transition",
                     "does the gatehouse to courtyard step produce measurable spatial release?",
                     "the brief asks for one composed constrained-to-open transition",
                     source_region="region:gatehouse", destination_region="region:courtyard"),
        ProbeRequest("probe:arch_contrast", "transition",
                     "does the gallery arch to gallery step produce release on the upper level?",
                     "the arch is the threshold the gallery's identity depends on",
                     source_region="region:gallery_arch", destination_region="region:gallery"),
        ProbeRequest("probe:crypt_contrast", "transition",
                     "does arriving in the crypt hall read as a contraction?",
                     "the crypt must feel unlike the courtyard it descends from",
                     source_region="region:courtyard", destination_region="region:crypt_hall"),
        ProbeRequest("probe:gallery_contrast", "transition",
                     "does the gallery read as different from the courtyard it rises out of?",
                     "the gallery is a separate intended identity",
                     source_region="region:courtyard", destination_region="region:gallery"),
        ProbeRequest("probe:ossuary_reachable_while_shut", "access",
                     "is the ossuary reachable while its panel stays shut? (fail is intended)",
                     "optional means gated, not accidentally disconnected",
                     target_region="region:ossuary", opened_connections=OPEN_EXCEPT_SECRET),
        ProbeRequest("probe:gallery_choices", "escape",
                     "how many onward routes leave the gallery?",
                     "two independent descents is the observable part of the loop claim",
                     start_region="region:gallery", opened_connections=OPEN_EXCEPT_SECRET),
        ProbeRequest("probe:revisit_after_crypt_gate", "revisit",
                     "what does the chancel switch actually open?",
                     "the gate must add the crypt branch and nothing else",
                     target_region="region:crypt_hall", opened_connections=CHAPEL_DOOR_BOTH,
                     alt_opened_connections=CHAPEL_DOOR_BOTH + CRYPT_GATE_BOTH),
        ProbeRequest("probe:courtyard_choices", "escape",
                     "how many onward choices does the courtyard offer?",
                     "a hub parent space should branch, not funnel",
                     start_region="region:courtyard", opened_connections=OPEN_EXCEPT_SECRET),
        ProbeRequest("probe:gatehouse_choices", "escape",
                     "how many onward choices does the gatehouse offer?",
                     "the approach should be the narrowest decision point",
                     start_region="region:gatehouse", opened_connections=OPEN_EXCEPT_SECRET),
        ProbeRequest("probe:chapel_choices", "escape",
                     "how many onward choices does the chapel nave offer?",
                     "the chapel should have parts, not be a single terminus",
                     start_region="region:chapel_nave", opened_connections=OPEN_EXCEPT_SECRET),
        ProbeRequest("probe:crypt_choices", "escape",
                     "how many onward choices does the crypt hall offer?",
                     "the crypt should be a hall with cells, not one room",
                     start_region="region:crypt_hall", opened_connections=OPEN_EXCEPT_SECRET),
    )


def viewpoints() -> tuple[ViewpointSpec, ...]:
    return (
        ViewpointSpec("view:start", "player_start", "region:ledge",
                      *P(-6, 22), COURT - 1024, 0, note="the arrival pose"),
        ViewpointSpec("view:gate_approach", "transition_approach", "region:gate_tunnel",
                      *P(2, 22), COURT - 1024, 0, note="inside the tunnel, facing the gatehouse"),
        ViewpointSpec("view:gatehouse", "transition_approach", "region:gatehouse",
                      *P(8, 22), COURT - 1024, 0, note="under the splayed gatehouse"),
        ViewpointSpec("view:courtyard_center", "assembly_center", "region:courtyard",
                      *P(17, 22), COURT - 1024, 0, note="west courtyard, facing the chapel mass"),
        ViewpointSpec("view:courtyard_sky", "assembly_center", "region:courtyard",
                      *P(22, 12), COURT - 1024, 512, pitch=16,
                      note="the courtyard looking up, which no earlier iteration ever did"),
        ViewpointSpec("view:nave_vault", "assembly_center", "region:chapel_nave",
                      *P(31, 23), COURT - 1024, 0, pitch=14,
                      note="the ten player-height nave ceiling, looked at for the first time"),
        ViewpointSpec("view:crypt_vault", "assembly_center", "region:crypt_hall",
                      *P(28, 55), CRYPT_FLOOR - 1024, 512, pitch=12,
                      note="the crypt vault after the surface change"),
        ViewpointSpec("view:gallery_vault", "assembly_center", "region:gallery",
                      *P(68, 30), GALLERY_FLOOR - 1024, 1024, pitch=14,
                      note="the twelve player-height gallery ceiling"),
        ViewpointSpec("view:courtyard_corner", "assembly_center", "region:courtyard",
                      *P(16, 8), COURT - 1024, 256,
                      note="the chamfered south-west corner and the octagonal planter"),
        ViewpointSpec("view:chapel_interior", "assembly_center", "region:chapel_nave",
                      *P(29, 23), COURT - 1024, 0, note="inside the chapel, facing the chancel"),
        ViewpointSpec("view:chapel_apse", "landmark", "region:chapel_apse",
                      *P(40, 24), APSE_FLOOR - 1024, 1024,
                      note="on the raised chancel, looking back down over the nave"),
        ViewpointSpec("view:chancel_stair", "vertical_relationship", "region:chapel_nave",
                      *P(35, 22), COURT - 1024, 0,
                      note="in the nave, facing the chancel stair and the 6144 opening beside it"),
        ViewpointSpec("view:planter", "vertical_relationship", "region:courtyard",
                      *P(22, 12), COURT - 1024, 512,
                      note="beside the raised planter, which now stands over the courtyard"),
        ViewpointSpec("view:crypt_hall", "assembly_center", "region:crypt_hall",
                      *P(32, 55), CRYPT_FLOOR - 1024, 1024, note="the vaulted crypt hall"),
        ViewpointSpec("view:gallery_arch", "transition_approach", "region:gallery_arch",
                      *P(60, 22), GALLERY_FLOOR - 1024, 0, note="under the arch, facing the gallery"),
        ViewpointSpec("view:gallery", "assembly_center", "region:gallery",
                      *P(68, 24), GALLERY_FLOOR - 1024, 1024, note="the gallery, facing the arch"),
        ViewpointSpec("view:courtyard_from_stair", "vertical_relationship",
                      "region:stairs:ascent:step_02",
                      *P(55, 22), COURT - 2 * GAL_STEP - 1024, 1024, note="mid-ascent, looking back"),
        ViewpointSpec("view:chapel_reverse", "reverse_view", "region:courtyard",
                      *P(47, 23), COURT - 1024, 1024, note="east of the chapel, looking back"),
    )


def candidate() -> Candidate:
    return Candidate(
        iteration_id="v5",
        module="projects/reasoned-authoring-v1/level/candidate_v5.py",
        factory=make_layout,
        intent=intent(),
        probes=probes(),
        viewpoints=viewpoints(),
        parent="v4",
        declared_changes=(
            "both chapel aisles gain their own way out to the courtyard -- a working "
            "porch south, a fallen one standing open north -- so the two pockets "
            "hanging off the nave become aisles, and the nave can be entered or left "
            "from three sides instead of one",
            "a low ambulatory closes the crypt's south-west into a circuit, giving the "
            "reliquary a second way out; the crypt hall was a seven-spoke star whose "
            "removal broke the map into seven pieces, and the level's dead-end fraction "
            "falls from 0.255 to 0.160, inside the campaign's 0.119..0.19",
            "the two water mouths dive by one translation, because the campaign pins "
            "the translation exactly when both mouths are also reachable on foot "
            "(630 agree, 4 disagree) and leaves it free when they are not (8 vs 100)",
            "the sunk joins are declared at the width the shaped mouths actually give "
            "rather than the width the square ones did; the portals_realized gate "
            "caught the stale declaration",
            "the crypt stops being one tile: the hall, its stair and the tomb block take "
            "E6M3's crypt treatments, tile 1097 stays only on the reliquary where the "
            "corpus supports it, and the two larger chambers take a third set",
            "segmented arcs at the mined corpus parameters replace chamfers on the planter, "
            "the chancel, two courtyard corners, two crypt-hall corners and two gallery corners",
            "the planter's eight hand-written connection edges are generated from its own "
            "outline, so its sixteen segments cannot drift out of step with its connections",
            "four viewpoints declare an upward pitch, so the level's ceilings and its sky "
            "are looked at for the first time in five iterations",
            "the sky panorama itself was a compiler fix rather than a source change: "
            "PlanarLayout now emits the sixteen-panel sky every campaign map with a "
            "parallax sector declares, instead of the single panel new_level hardcoded",
        ),
    )
