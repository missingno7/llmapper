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
from bloodmap.item_display import sprite_appearance
from bloodmap.planar_layout import PlanarLayout
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
COURT = 8192
SKY = COURT - 16 * PH              # 1100 player areas at p59 of comparable corpus sectors
LEDGE_CEIL = COURT - 6 * PH
TUNNEL_CEIL = COURT - 3 * PH       # deliberately tight; only 16 player areas
GATEHOUSE_CEIL = COURT - 5 * PH
BED_FLOOR = COURT - 6144            # a raised planter; 1.1 player heights above the courtyard
NAVE_CEIL = COURT - 10 * PH
AISLE_CEIL = COURT - 6 * PH
APSE_FLOOR = COURT - 6144           # raised out of step range, reached by its own stair
APSE_CEIL = APSE_FLOOR - 8 * PH

CRYPT_STEP = 3072
CRYPT_FLOOR = COURT + 4 * CRYPT_STEP
CRYPT_CEIL = CRYPT_FLOOR - 5 * PH        # a vaulted hall, not a crawlspace
CHAMBER_CEIL = CRYPT_FLOOR - 3 * PH      # cells, kept low on the E6M3 precedent
CISTERN_FLOOR = CRYPT_FLOOR + 2048

GAL_STEP = 4096                     # the corpus rise, and the player step exactly
GALLERY_FLOOR = COURT - 3 * GAL_STEP
ARCH_CEIL = GALLERY_FLOOR - 4 * PH       # still a third of what it opens onto
GALLERY_CEIL = GALLERY_FLOOR - 12 * PH
EXIT_CEIL = GALLERY_FLOOR - 8 * PH

SWITCH_HEIGHT = 2.18
SWITCH_OFFSET = 0.12

# --- material vocabulary (inherited from v2) -------------------------------
APPROACH_TILES = dict(wall_picnum=427, floor_picnum=270, ceiling_picnum=285)
COURT_TILES = dict(wall_picnum=110, floor_picnum=2448, ceiling_picnum=2500)
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

DOOR_FACE = 22
KEYED_FACE = 495
REMOTE_FACE = 200

CH_CRYPT_GATE = 100
CH_SECRET = 102
CH_EXIT = 4

# --- decoration, sized from tile pixels rather than copied repeats ---------
# Build draws a sprite at tile pixels * repeat * 4 world units, so a repeat is
# chosen from the height the decoration should actually be in this room.
ART_SIZE = {
    506: (12, 43), 2542: (58, 58), 2540: (58, 58), 2545: (58, 58),
    1044: (128, 128), 641: (15, 128), 660: (22, 32), 664: (11, 126),
    68: (64, 16), 1701: (30, 119), 795: (32, 32),
}


def _repeat(picnum: int, player_heights: float, *, aspect: float = 1.0) -> dict[str, int]:
    """Repeats that make this tile the stated number of player heights tall."""
    _width, height = ART_SIZE[picnum]
    y_repeat = max(4, min(255, round(player_heights * PH / (height * 4))))
    return {"y_repeat": y_repeat, "x_repeat": max(4, min(255, round(y_repeat * aspect)))}


def decor(picnum: int, cstat: int, player_heights: float, *, aspect: float = 1.0,
          shade: int = -8) -> dict[str, int]:
    return {"type": 0, "picnum": picnum, "cstat": cstat, "shade": shade,
            **_repeat(picnum, player_heights, aspect=aspect)}


def shades(value: int) -> dict[str, int]:
    return dict(floor_shade=value, ceiling_shade=value, wall_shade=max(-128, value - 2))


def sky_shades(floor: int) -> dict[str, int]:
    return dict(floor_shade=floor, ceiling_shade=0, wall_shade=floor - 2)


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
GALLERY = outline(
    [P(64, 10), P(73, 10)],
    arc_through(P(73, 10), P(76, 12), bulge=0.8 * U, segments=5),
    [P(76, 39)],
    arc_through(P(76, 39), P(74, 42), bulge=0.8 * U, segments=5),
    [P(64, 42), P(62, 40), P(62, 12)],
)
EXIT_HALL = poly((78, 18), (86, 18), (88, 20), (88, 28), (86, 30), (78, 30))

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


def make_layout() -> PlanarLayout:
    layout = PlanarLayout(name="monastery-v3", visibility=800)

    # ---- arrival -----------------------------------------------------------
    layout.add_region("region:ledge", LEDGE, role="start",
                      ceiling_z=LEDGE_CEIL, floor_z=COURT, **APPROACH_TILES, **shades(34),
                      intent={"purpose": "cliffside arrival ledge", "classification": "MANDATORY"})
    layout.add_region("region:gate_tunnel", R(-2, 21, 6, 23), role="gateway",
                      ceiling_z=TUNNEL_CEIL, floor_z=COURT, **APPROACH_TILES, **shades(36),
                      intent={"purpose": "constrained gate tunnel", "classification": "MANDATORY"})
    layout.add_region("region:gatehouse", GATEHOUSE, role="gateway",
                      ceiling_z=GATEHOUSE_CEIL, floor_z=COURT, **APPROACH_TILES, **shades(32),
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
                      **COURT_TILES, **sky_shades(16),
                      intent={"purpose": "arrival garden courtyard", "classification": "MANDATORY"})
    layout.carve_hole("region:courtyard", CHAPEL_SHELL)
    layout.carve_hole("region:courtyard", GARDEN_BED)

    layout.add_region("region:garden_bed", GARDEN_BED, role="detail",
                      ceiling_z=SKY, floor_z=BED_FLOOR, parallax_ceiling=True,
                      **BED_TILES, **sky_shades(20),
                      intent={"purpose": "octagonal sunken planter", "classification": "OPTIONAL"})
    for name, a1, a2 in BED_EDGES:
        layout.add_connection(f"connection:bed_{name}", "region:courtyard", "region:garden_bed",
                              a1=a1, a2=a2, min_width=256)

    # ---- chapel ------------------------------------------------------------
    layout.add_region("region:chapel_door", R(24, 21, 26, 25), role="doorway", type=600,
                      ceiling_z=COURT, floor_z=COURT,
                      wall_picnum=DOOR_FACE, floor_picnum=DOOR_FACE, ceiling_picnum=DOOR_FACE,
                      **shades(16),
                      sector_behavior=_z_door(COURT, COURT - 8 * PH, interaction="direct"),
                      intent={"purpose": "chapel west door", "classification": "MANDATORY",
                              "interaction": "direct_use"})
    layout.add_region("region:chapel_nave", NAVE, role="interior",
                      ceiling_z=NAVE_CEIL, floor_z=COURT, **NAVE_TILES, **shades(20),
                      intent={"purpose": "chapel nave", "classification": "MANDATORY"})
    layout.add_region("region:chapel_aisle_south", AISLE_SOUTH, role="interior",
                      ceiling_z=AISLE_CEIL, floor_z=COURT, **AISLE_TILES, **shades(26),
                      intent={"purpose": "south side aisle", "classification": "OPTIONAL"})
    layout.add_region("region:chapel_aisle_north", AISLE_NORTH, role="interior",
                      ceiling_z=AISLE_CEIL, floor_z=COURT, **AISLE_TILES, **shades(26),
                      intent={"purpose": "north side aisle", "classification": "OPTIONAL"})
    layout.add_region("region:chapel_apse", APSE, role="interior",
                      ceiling_z=APSE_CEIL, floor_z=APSE_FLOOR, **APSE_TILES, **shades(8),
                      intent={"purpose": "chancel raised 6144 above the nave, holding the "
                                         "crypt-gate switch",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:courtyard_chapeldoor", "region:courtyard", "region:chapel_door",
                          role="doorway", gated=True, a1=P(24, 21), a2=P(24, 25),
                          face_picnum=DOOR_FACE, min_width=1536)
    layout.add_connection("connection:chapeldoor_nave", "region:chapel_door", "region:chapel_nave",
                          role="doorway", gated=True, a1=P(26, 21), a2=P(26, 25),
                          face_picnum=DOOR_FACE, min_width=1536)
    layout.add_connection("connection:nave_aisle_south", "region:chapel_nave", "region:chapel_aisle_south",
                          a1=P(28, 18), a2=P(36, 18), min_width=1536)
    layout.add_connection("connection:nave_aisle_north", "region:chapel_nave", "region:chapel_aisle_north",
                          a1=P(28, 28), a2=P(36, 28), min_width=1536)
    # The south half of the nave/chancel edge carries the stair; the north half
    # stays open at the full 6144 drop, which is what makes it an overlook.
    chancel = staircase(
        layout, "stairs:chancel",
        base=Anchor("region:chapel_nave", P(38, 20), P(38, 23)),
        total_rise=APSE_FLOOR - COURT, step_rise=-2048, tread=U, clear_height=8 * PH,
        base_floor_z=COURT, shade_ramp=(18, 12), **APSE_TILES,
        intent={"classification": "MANDATORY"},
    )
    chancel.arrive_at("region:chapel_apse")
    # The chancel platform runs alongside the stair as well as behind it, so the
    # three tread/platform boundaries are walls, not openings: you climb east and
    # turn north onto the chancel rather than stepping sideways up 2048 at a time.
    for step in range(1, 4):
        layout.add_partition(
            f"partition:chancel_rail_{step:02d}", "region:chapel_apse",
            f"region:stairs:chancel:step_{step:02d}", role="solid_boundary",
            a1=P(37 + step, 23), a2=P(38 + step, 23),
        )
    layout.add_connection("connection:nave_apse", "region:chapel_nave", "region:chapel_apse",
                          a1=P(38, 23), a2=P(38, 26), min_width=1152)

    # ---- crypt -------------------------------------------------------------
    layout.add_region("region:crypt_gate", R(30, 40, 34, 42), role="doorway", type=600,
                      ceiling_z=COURT, floor_z=COURT,
                      wall_picnum=REMOTE_FACE, floor_picnum=REMOTE_FACE, ceiling_picnum=REMOTE_FACE,
                      **shades(16),
                      sector_behavior=_z_door(COURT, COURT - 4 * PH, interaction="remote",
                                              rx=CH_CRYPT_GATE),
                      intent={"purpose": "crypt gate opened from the chapel apse",
                              "classification": "MANDATORY", "interaction": "remote_switch"})
    layout.add_connection("connection:courtyard_cryptgate", "region:courtyard", "region:crypt_gate",
                          role="doorway", gated=True, a1=P(30, 40), a2=P(34, 40),
                          face_picnum=REMOTE_FACE, min_width=1536)

    # Four rises of 3072, which is the third rise the corpus actually uses.  The
    # whole run, its shade ramp and its five portals are one call; v0-v3 wrote
    # this as a loop that tracked its own previous edge by hand.
    descent = staircase(
        layout, "stairs:crypt",
        base=Anchor("region:crypt_gate", P(34, 42), P(30, 42)),
        total_rise=4 * CRYPT_STEP, step_rise=CRYPT_STEP, tread=2 * U,
        clear_height=4 * PH, base_floor_z=COURT, shade_ramp=(28, 46), **CRYPT_STAIR_TILES,
        intent={"classification": "MANDATORY"},
    )
    layout.add_region("region:crypt_hall", CRYPT_HALL, role="interior",
                      ceiling_z=CRYPT_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_TILES, **shades(32),
                      intent={"purpose": "vaulted crypt hall with cut corners",
                              "classification": "MANDATORY"})
    descent.arrive_at("region:crypt_hall")
    # A raised tomb block the player walks around and never stands on: the crypt
    # hall's own vertical relationship, and something for a 200 player-area room
    # to be about.
    layout.carve_hole("region:crypt_hall", PLINTH)
    layout.add_region("region:crypt_plinth", PLINTH, role="detail",
                      ceiling_z=CRYPT_CEIL, floor_z=CRYPT_FLOOR - 6144,
                      **PLINTH_TILES, **shades(24),
                      intent={"purpose": "raised tomb block in the crypt hall",
                              "classification": "OPTIONAL"})
    for name, a1, a2 in PLINTH_EDGES:
        layout.add_connection(f"connection:plinth_{name}", "region:crypt_hall",
                              "region:crypt_plinth", a1=P(*a1), a2=P(*a2), min_width=512)
    layout.add_region("region:crypt_reliquary", RELIQUARY, role="key_branch",
                      ceiling_z=CHAMBER_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_CELL_TILES,
                      **shades(36),
                      intent={"purpose": "reliquary cell holding the skull key; kept low on the "
                                         "E6M3 precedent for crypt cells of this size",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:crypthall_reliquary", "region:crypt_hall", "region:crypt_reliquary",
                          a1=P(22, 52), a2=P(22, 58), min_width=1536)
    layout.add_region("region:crypt_cistern", CISTERN, role="interior",
                      ceiling_z=CHAMBER_CEIL, floor_z=CISTERN_FLOOR, **CRYPT_CHAMBER_TILES,
                      **shades(40),
                      intent={"purpose": "sunken cistern cell holding the ossuary switch",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:crypthall_cistern", "region:crypt_hall", "region:crypt_cistern",
                          a1=P(26, 60), a2=P(34, 60), min_width=1536)

    layout.add_region("region:ossuary_door", R(42, 52, 44, 56), role="doorway", type=600,
                      ceiling_z=CRYPT_FLOOR, floor_z=CRYPT_FLOOR, **CRYPT_CHAMBER_TILES,
                      **shades(40),
                      sector_behavior=_z_door(CRYPT_FLOOR, CHAMBER_CEIL, interaction="remote",
                                              rx=CH_SECRET),
                      intent={"purpose": "hidden ossuary panel", "classification": "OPTIONAL",
                              "hidden": True})
    layout.add_region("region:ossuary", OSSUARY, role="secret",
                      ceiling_z=CHAMBER_CEIL, floor_z=CRYPT_FLOOR, declared_zero_exit=True,
                      **CRYPT_CHAMBER_TILES, **shades(44),
                      intent={"purpose": "optional ossuary", "classification": "OPTIONAL"})
    layout.add_connection("connection:crypthall_ossuarydoor", "region:crypt_hall", "region:ossuary_door",
                          role="doorway", gated=True, a1=P(42, 52), a2=P(42, 56), min_width=1536)
    layout.add_connection("connection:ossuarydoor_ossuary", "region:ossuary_door", "region:ossuary",
                          role="doorway", gated=True, a1=P(44, 52), a2=P(44, 56), min_width=1536)

    # ---- ascent, gallery, and the loop back down ---------------------------
    ascent = staircase(
        layout, "stairs:ascent",
        base=Anchor("region:courtyard", P(52, 20), P(52, 24)),
        total_rise=-3 * GAL_STEP, step_rise=-GAL_STEP, tread=2 * U,
        clear_height=5 * PH, base_floor_z=COURT, shade_ramp=(14, 26), **COURT_TILES,
        intent={"classification": "MANDATORY"},
    )
    layout.add_region("region:gallery_arch", R(58, 20, 62, 24), role="gateway",
                      ceiling_z=ARCH_CEIL, floor_z=GALLERY_FLOOR, **ARCH_TILES, **shades(42),
                      intent={"purpose": "low covered arch; the threshold the gallery begins at",
                              "classification": "MANDATORY"})
    ascent.arrive_at("region:gallery_arch")
    layout.add_region("region:gallery", GALLERY, role="upper",
                      ceiling_z=GALLERY_CEIL, floor_z=GALLERY_FLOOR, **GALLERY_TILES, **shades(12),
                      intent={"purpose": "tall upper service gallery with cut corners",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:arch_gallery", "region:gallery_arch", "region:gallery",
                          a1=P(62, 20), a2=P(62, 24), min_width=1536)

    layout.add_region("region:loop_arch", R(58, 34, 62, 38), role="gateway",
                      ceiling_z=ARCH_CEIL, floor_z=GALLERY_FLOOR, **ARCH_TILES, **shades(42),
                      intent={"purpose": "second gallery arch onto the return stair",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:gallery_looparch", "region:gallery", "region:loop_arch",
                          a1=P(62, 34), a2=P(62, 38), min_width=1536)

    descent_home = staircase(
        layout, "stairs:return",
        base=Anchor("region:loop_arch", P(58, 38), P(58, 34)),
        total_rise=3 * GAL_STEP, step_rise=GAL_STEP, tread=2 * U,
        clear_height=5 * PH, base_floor_z=GALLERY_FLOOR, shade_ramp=(26, 14), **COURT_TILES,
        intent={"classification": "MANDATORY"},
    )
    descent_home.arrive_at("region:courtyard")

    # ---- exit --------------------------------------------------------------
    layout.add_region("region:exit_door", R(76, 22, 78, 26), role="doorway", type=600,
                      ceiling_z=GALLERY_FLOOR, floor_z=GALLERY_FLOOR,
                      wall_picnum=KEYED_FACE, floor_picnum=KEYED_FACE, ceiling_picnum=KEYED_FACE,
                      **shades(16),
                      sector_behavior=_z_door(GALLERY_FLOOR, EXIT_CEIL, interaction="direct", key=1),
                      intent={"purpose": "skull-keyed exit gate", "classification": "MANDATORY",
                              "interaction": "direct_use"})
    layout.add_region("region:exit_hall", EXIT_HALL, role="exit", declared_zero_exit=True,
                      ceiling_z=EXIT_CEIL, floor_z=GALLERY_FLOOR, **EXIT_TILES, **shades(18),
                      intent={"purpose": "exit chamber", "classification": "MANDATORY"})
    layout.add_connection("connection:gallery_exitdoor", "region:gallery", "region:exit_door",
                          role="doorway", gated=True, a1=P(76, 22), a2=P(76, 26),
                          face_picnum=KEYED_FACE, min_width=1536)
    layout.add_connection("connection:exitdoor_hall", "region:exit_door", "region:exit_hall",
                          role="doorway", gated=True, a1=P(78, 22), a2=P(78, 26),
                          face_picnum=KEYED_FACE, min_width=1536)

    # ---- gameplay population -----------------------------------------------
    start = P(-6, 22)
    layout.set_player_start("region:ledge", x=start[0], y=start[1], z=COURT - 1024, angle=0)
    layout.add_sprite("sp_start", "region:ledge", x=start[0], y=start[1], z=COURT - 1024,
                      **sprite_appearance(1, angle=0), behavior={"state": 1})
    layout.place_on_wall("sw_crypt_gate", "region:chapel_apse",
                         a1=APSE_ARC[4], a2=APSE_ARC[5], t=0.5,
                         height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
                         **SWITCH,
                         behavior={"tx_id": CH_CRYPT_GATE, "command": 1, "trigger_on": 1,
                                   "trigger_push": 1, "data_1": 203})
    layout.place_on_wall("sw_ossuary", "region:crypt_cistern", a1=P(32, 66), a2=P(28, 66), t=0.5,
                         height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
                         **SWITCH,
                         behavior={"tx_id": CH_SECRET, "command": 1, "trigger_on": 1,
                                   "trigger_push": 1, "data_1": 203})
    layout.place_on_wall("sw_exit", "region:exit_hall", a1=P(88, 20), a2=P(88, 28), t=0.5,
                         height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
                         **SWITCH,
                         behavior={"tx_id": CH_EXIT, "command": 1, "trigger_on": 1, "trigger_push": 1})
    layout.place_on_floor("key_skull", "region:crypt_reliquary", local=(0.5, 0.5),
                          **sprite_appearance(100), behavior={"state": 1})

    # ---- niches, on the corpus recess profile -------------------------------
    # 792 recesses across all 42 campaign maps: floor flush with the host in
    # roughly three quarters of them, a lowered ceiling in a third, and a
    # footprint of a few percent of the host.  These are the first in the level
    # that were not really side rooms wearing a niche's name.
    recess(layout, "recess:crypt_niche",
           anchor=Anchor("region:crypt_hall", P(38, 60), P(36, 60)),
           depth=int(1.5 * U), ceiling_drop=2 * PH, **CRYPT_CELL_TILES, **shades(36),
           intent={"purpose": "wall niche in the crypt hall", "classification": "OPTIONAL"})
    recess(layout, "recess:gallery_niche",
           anchor=Anchor("region:gallery", P(62, 30), P(62, 26)),
           depth=int(1.5 * U), ceiling_drop=6 * PH, **GALLERY_TILES, **shades(16),
           intent={"purpose": "wall niche in the gallery", "classification": "OPTIONAL"})
    recess(layout, "recess:exit_niche",
           anchor=Anchor("region:exit_hall", P(84, 30), P(82, 30)),
           depth=int(1.5 * U), ceiling_drop=4 * PH, **EXIT_TILES, **shades(22),
           intent={"purpose": "wall niche in the exit chamber", "classification": "OPTIONAL"})

    _decorate(layout)
    return layout


def _decorate(layout: PlanarLayout) -> None:
    """Decoration attached to architectural roles, sized to the room it stands in."""
    torch = lambda ph: decor(506, 128, ph, aspect=1.0, shade=-128)          # noqa: E731
    sconce = lambda ph: decor(2542, 464, ph)                                # noqa: E731
    emblem = lambda pic, ph: decor(pic, 464, ph)                            # noqa: E731
    grille = lambda ph: decor(1044, 412, ph, aspect=0.45)                   # noqa: E731
    chain = lambda ph: decor(641, 128, ph, aspect=0.35, shade=-128)         # noqa: E731
    plant = lambda ph: decor(660, 128, ph, aspect=0.5)                      # noqa: E731
    vine = lambda ph: decor(664, 128, ph, aspect=0.35)                      # noqa: E731
    plank = lambda ph: decor(68, 464, ph, aspect=2.0)                       # noqa: E731
    lamp = lambda ph: decor(1701, 384, ph, aspect=0.55, shade=-128)         # noqa: E731
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
                             height_player_heights=0.05, offset_player_widths=0.12, **vine(3.4))
    layout.place_on_wall("dec_court_emblem", "region:courtyard", a1=P(44, 32), a2=P(44, 14),
                         t=0.5, height_player_heights=2.6, offset_player_widths=0.12, **emblem(2545, 1.2))

    for name, local in (("nw", (0.28, 0.3)), ("ne", (0.72, 0.3)),
                        ("sw", (0.3, 0.7)), ("se", (0.7, 0.7))):
        layout.place_on_floor(f"dec_bed_plant_{name}", "region:garden_bed", local=local, **plant(0.8))
    layout.place_on_floor("dec_bed_vine_c", "region:garden_bed", local=(0.5, 0.5), **vine(2.2))

    # -- chapel (nave 10 PH, aisles 6 PH, apse 8 PH) --------------------------
    for name, local in (("west", (0.32, 0.5)), ("east", (0.68, 0.5))):
        layout.place_on_ceiling(f"dec_nave_lamp_{name}", "region:chapel_nave",
                                local=local, height_player_heights=0.8, **lamp(1.3))
    for name, t_value in (("south", 0.16), ("north", 0.84)):
        layout.place_on_wall(f"dec_nave_sconce_{name}", "region:chapel_nave",
                             a1=P(26, 26), a2=P(26, 20), t=t_value,
                             height_player_heights=2.3, offset_player_widths=0.12, **sconce(0.9))
    layout.place_on_wall("dec_nave_grille_s", "region:chapel_nave", a1=P(28, 18), a2=P(36, 18),
                         t=0.5, height_player_heights=3.2, offset_player_widths=0.12, **grille(1.8))
    for name, t_value in (("south", 0.25), ("north", 0.75)):
        layout.place_on_wall(f"dec_apse_sconce_{name}", "region:chapel_apse",
                             a1=APSE_ARC[1], a2=APSE_ARC[2], t=t_value,
                             height_player_heights=2.1, offset_player_widths=0.12, **sconce(0.9))
    layout.place_on_ceiling("dec_apse_light", "region:chapel_apse", local=(0.5, 0.5),
                            height_player_heights=0.35, **disc(0.7))
    layout.place_on_wall("dec_aisle_s_plank", "region:chapel_aisle_south",
                         a1=P(30, 14), a2=P(34, 14), t=0.5,
                         height_player_heights=1.6, offset_player_widths=0.10, **plank(0.5))
    layout.place_on_ceiling("dec_aisle_s_chain", "region:chapel_aisle_south",
                            local=(0.7, 0.5), height_player_heights=0.5, **chain(2.4))
    layout.place_on_wall("dec_aisle_n_plank", "region:chapel_aisle_north",
                         a1=P(34, 32), a2=P(30, 32), t=0.5,
                         height_player_heights=1.6, offset_player_widths=0.10, **plank(0.5))
    layout.place_on_ceiling("dec_aisle_n_chain", "region:chapel_aisle_north",
                            local=(0.3, 0.5), height_player_heights=0.5, **chain(2.4))

    # -- crypt (hall 5 PH, cells 3 PH) ----------------------------------------
    for name, t_value in (("west", 0.15), ("east", 0.85)):
        layout.place_on_wall(f"dec_crypt_grille_{name}", "region:crypt_hall",
                             a1=P(24, 50), a2=P(39, 50), t=t_value,
                             height_player_heights=1.9, offset_player_widths=0.12, **grille(1.5))
    for name, local in (("west", (0.2, 0.5)), ("east", (0.8, 0.5))):
        layout.place_on_ceiling(f"dec_crypt_chain_{name}", "region:crypt_hall",
                                local=local, height_player_heights=0.5, **chain(2.0))
    layout.place_on_wall("dec_crypt_emblem", "region:crypt_hall", a1=P(40, 60), a2=P(25, 60),
                         t=0.5, height_player_heights=2.2, offset_player_widths=0.12, **emblem(2545, 1.0))
    layout.place_on_ceiling("dec_crypt_lamp", "region:crypt_hall", local=(0.5, 0.45),
                            height_player_heights=0.6, **lamp(1.2))
    layout.place_on_wall("dec_reliquary_emblem", "region:crypt_reliquary",
                         a1=P(18, 58), a2=P(16, 56), t=0.5,
                         height_player_heights=1.6, offset_player_widths=0.12, **emblem(2545, 0.8))
    layout.place_on_ceiling("dec_reliquary_lamp", "region:crypt_reliquary", local=(0.5, 0.5),
                            height_player_heights=0.4, **lamp(0.9))
    layout.place_on_ceiling("dec_cistern_chain", "region:crypt_cistern", local=(0.35, 0.5),
                            height_player_heights=0.4, **chain(1.3))
    layout.place_on_wall("dec_cistern_grille", "region:crypt_cistern", a1=P(34, 60), a2=P(34, 64),
                         t=0.5, height_player_heights=1.4, offset_player_widths=0.12, **grille(1.0))
    layout.place_on_wall("dec_ossuary_emblem", "region:ossuary", a1=P(52, 52), a2=P(52, 58),
                         t=0.5, height_player_heights=1.6, offset_player_widths=0.12, **emblem(2545, 0.8))
    layout.place_on_ceiling("dec_ossuary_chain", "region:ossuary", local=(0.4, 0.5),
                            height_player_heights=0.4, **chain(1.3))

    # -- gallery (12 PH) ------------------------------------------------------
    for name, t_value in (("a", 0.25), ("b", 0.6), ("c", 0.9)):
        layout.place_on_wall(f"dec_gallery_vine_{name}", "region:gallery",
                             a1=P(64, 10), a2=P(73, 10), t=t_value,
                             height_player_heights=0.05, offset_player_widths=0.12, **vine(4.0))
    for name, t_value in (("d", 0.3), ("e", 0.7)):
        layout.place_on_wall(f"dec_gallery_vine_{name}", "region:gallery",
                             a1=P(74, 42), a2=P(64, 42), t=t_value,
                             height_player_heights=0.05, offset_player_widths=0.12, **vine(4.0))
    for name, t_value in (("north", 0.3), ("south", 0.7)):
        layout.place_on_wall(f"dec_gallery_torch_{name}", "region:gallery",
                             a1=P(76, 12), a2=P(76, 39), t=t_value,
                             height_player_heights=2.2, offset_player_widths=0.10, **torch(1.6))
    layout.place_on_wall("dec_gallery_plank", "region:gallery", a1=P(62, 40), a2=P(62, 12),
                         t=0.12, height_player_heights=1.6, offset_player_widths=0.10, **plank(0.6))
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
