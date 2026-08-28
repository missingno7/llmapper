"""Cliffside monastery, iteration 3: scale and shape.

This iteration exists because the project owner said the map was still mostly
rectangular and its ceilings too low, and because adding the two missing
measurements to the packet proved both points exactly.  Against 42 campaign maps
v2 was at the 100th percentile for orthogonal wall length and rectangular
sectors, the 0th for diagonals, orientation variety and chamfers, and had five
spaces below the 5th percentile of corpus clear height for their footprint.

1. SCALE.  Every ceiling is now set from what original Blood maps do at that
   footprint, not from a round multiple of the player's height.  The corpus
   median for sectors of at least 20 player areas is 8.73 player heights and for
   at least 200 it is 11.64; v2 had a 200 player-area crypt hall at 2.18 and a
   440 player-area gallery at 6.
     nave 7 -> 10, aisles 4 -> 6, apse 6 -> 8, gallery 6 -> 12, exit 4 -> 8,
     ledge 4 -> 6, gatehouse 3 -> 5, crypt hall 2.18 -> 5, arches 2 -> 4.
   The crypt CHAMBERS stay deliberately low at about 3 player heights: the E6M3
   precedent measures real crypt cells at 1.45 to 2.91, and at 30 to 55 player
   areas these are that size of space.  That is now an argued exception instead
   of an unexamined default.

2. SHAPE.  The level stops being a grid.  The courtyard, the chapel mass it
   contains, the crypt hall, the gallery, the exit hall, the ledge and the crypt
   chambers all get 45-degree chamfered corners; the gatehouse is splayed so it
   opens toward the courtyard; the apse becomes a six-sided chancel; the garden
   bed becomes an octagonal planter.  Stairs, doors and the two arches stay
   rectangular, which is normal for original maps too.

3. SPRITE SCALE.  v2 shipped 18 decorations taller than three quarters of the
   space they stood in, several clipping through floor and ceiling at over 250
   percent, because repeats were copied from the campaign mode without asking
   what room they were going into.  Repeats are now derived from each tile's real
   pixel dimensions and a stated target size in player heights.

4. The loop arch gets the emblem its twin already had.

Geometry, heights and sprite sizes change here.  Material choices and the shade
structure that carries the perceptual thresholds are inherited from v2 unchanged.
"""

from __future__ import annotations

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
BED_FLOOR = COURT + 2048
NAVE_CEIL = COURT - 10 * PH
AISLE_CEIL = COURT - 6 * PH
APSE_FLOOR = COURT - 2048
APSE_CEIL = APSE_FLOOR - 8 * PH

CRYPT_STEP = 3072
CRYPT_FLOOR = COURT + 4 * CRYPT_STEP
CRYPT_CEIL = CRYPT_FLOOR - 5 * PH        # a vaulted hall, not a crawlspace
CHAMBER_CEIL = CRYPT_FLOOR - 3 * PH      # cells, kept low on the E6M3 precedent
CISTERN_FLOOR = CRYPT_FLOOR + 2048

GAL_STEP = 3840
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
CRYPT_TILES = dict(wall_picnum=1097, floor_picnum=1097, ceiling_picnum=1097)
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
COURTYARD = poly((14, 4), (46, 4), (52, 7), (52, 38), (50, 40), (15, 40), (10, 37), (10, 8))
CHAPEL_SHELL = poly((26, 12), (42, 12), (44, 14), (44, 32), (42, 34), (26, 34), (24, 32), (24, 14))
GARDEN_BED = poly((15, 8), (18, 8), (20, 10), (20, 14), (18, 16), (15, 16), (13, 14), (13, 10))
NAVE = poly((28, 18), (36, 18), (38, 20), (38, 26), (36, 28), (28, 28), (26, 26), (26, 20))
AISLE_SOUTH = poly((30, 14), (34, 14), (36, 16), (36, 18), (28, 18), (28, 16))
AISLE_NORTH = poly((28, 28), (36, 28), (36, 30), (34, 32), (30, 32), (28, 30))
APSE = poly((38, 20), (40, 20), (42, 21), (43, 22), (43, 24), (42, 25), (40, 26), (38, 26))
CRYPT_HALL = poly((24, 50), (39, 50), (42, 52), (42, 58), (40, 60), (25, 60), (22, 58), (22, 52))
RELIQUARY = poly((18, 52), (22, 52), (22, 58), (18, 58), (16, 56), (16, 54))
CISTERN = poly((26, 60), (34, 60), (34, 64), (32, 66), (28, 66), (26, 64))
OSSUARY = poly((44, 50), (50, 50), (52, 52), (52, 58), (50, 60), (44, 60))
GALLERY = poly((64, 10), (73, 10), (76, 12), (76, 39), (74, 42), (64, 42), (62, 40), (62, 12))
EXIT_HALL = poly((78, 18), (86, 18), (88, 20), (88, 28), (86, 30), (78, 30))

BED_EDGES = (
    ("s", (15, 8), (18, 8)), ("se", (18, 8), (20, 10)), ("e", (20, 10), (20, 14)),
    ("ne", (20, 14), (18, 16)), ("n", (18, 16), (15, 16)), ("nw", (15, 16), (13, 14)),
    ("w", (13, 14), (13, 10)), ("sw", (13, 10), (15, 8)),
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
                              a1=P(*a1), a2=P(*a2), min_width=512)

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
                      intent={"purpose": "raised six-sided chancel holding the crypt-gate switch",
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
    layout.add_connection("connection:nave_apse", "region:chapel_nave", "region:chapel_apse",
                          a1=P(38, 20), a2=P(38, 26), min_width=1536)

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

    previous, previous_edge = "region:crypt_gate", (P(30, 42), P(34, 42))
    for step, shade in enumerate((28, 34, 40, 46), start=1):
        region = f"region:crypt_stair_{step}"
        y0, y1 = 40 + 2 * step, 42 + 2 * step
        layout.add_region(region, R(30, y0, 34, y1), role="stair",
                          ceiling_z=COURT + step * CRYPT_STEP - 4 * PH,
                          floor_z=COURT + step * CRYPT_STEP, **CRYPT_TILES, **shades(shade),
                          intent={"purpose": f"crypt stair step {step}", "classification": "MANDATORY"})
        layout.add_connection(f"connection:crypt_step_{step}", previous, region,
                              a1=previous_edge[0], a2=previous_edge[1], min_width=1536)
        previous, previous_edge = region, (P(30, y1), P(34, y1))

    layout.add_region("region:crypt_hall", CRYPT_HALL, role="interior",
                      ceiling_z=CRYPT_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_TILES, **shades(32),
                      intent={"purpose": "vaulted crypt hall with cut corners",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:cryptstair_hall", previous, "region:crypt_hall",
                          a1=P(30, 50), a2=P(34, 50), min_width=1536)
    layout.add_region("region:crypt_reliquary", RELIQUARY, role="key_branch",
                      ceiling_z=CHAMBER_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_TILES, **shades(36),
                      intent={"purpose": "reliquary cell holding the skull key; kept low on the "
                                         "E6M3 precedent for crypt cells of this size",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:crypthall_reliquary", "region:crypt_hall", "region:crypt_reliquary",
                          a1=P(22, 52), a2=P(22, 58), min_width=1536)
    layout.add_region("region:crypt_cistern", CISTERN, role="interior",
                      ceiling_z=CHAMBER_CEIL, floor_z=CISTERN_FLOOR, **CRYPT_TILES, **shades(40),
                      intent={"purpose": "sunken cistern cell holding the ossuary switch",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:crypthall_cistern", "region:crypt_hall", "region:crypt_cistern",
                          a1=P(26, 60), a2=P(34, 60), min_width=1536)

    layout.add_region("region:ossuary_door", R(42, 52, 44, 56), role="doorway", type=600,
                      ceiling_z=CRYPT_FLOOR, floor_z=CRYPT_FLOOR, **CRYPT_TILES, **shades(40),
                      sector_behavior=_z_door(CRYPT_FLOOR, CHAMBER_CEIL, interaction="remote",
                                              rx=CH_SECRET),
                      intent={"purpose": "hidden ossuary panel", "classification": "OPTIONAL",
                              "hidden": True})
    layout.add_region("region:ossuary", OSSUARY, role="secret",
                      ceiling_z=CHAMBER_CEIL, floor_z=CRYPT_FLOOR, declared_zero_exit=True,
                      **CRYPT_TILES, **shades(44),
                      intent={"purpose": "optional ossuary", "classification": "OPTIONAL"})
    layout.add_connection("connection:crypthall_ossuarydoor", "region:crypt_hall", "region:ossuary_door",
                          role="doorway", gated=True, a1=P(42, 52), a2=P(42, 56), min_width=1536)
    layout.add_connection("connection:ossuarydoor_ossuary", "region:ossuary_door", "region:ossuary",
                          role="doorway", gated=True, a1=P(44, 52), a2=P(44, 56), min_width=1536)

    # ---- ascent, gallery, and the loop back down ---------------------------
    previous, previous_edge = "region:courtyard", (P(52, 20), P(52, 24))
    for step, shade in enumerate((14, 20, 26), start=1):
        region = f"region:gallery_stair_{step}"
        x0, x1 = 50 + 2 * step, 52 + 2 * step
        layout.add_region(region, R(x0, 20, x1, 24), role="stair",
                          ceiling_z=COURT - step * GAL_STEP - 5 * PH,
                          floor_z=COURT - step * GAL_STEP, **COURT_TILES, **shades(shade),
                          intent={"purpose": f"open courtyard stair step {step}",
                                  "classification": "MANDATORY"})
        layout.add_connection(f"connection:gallery_step_{step}", previous, region,
                              a1=previous_edge[0], a2=previous_edge[1], min_width=1536)
        previous, previous_edge = region, (P(x1, 20), P(x1, 24))

    layout.add_region("region:gallery_arch", R(58, 20, 62, 24), role="gateway",
                      ceiling_z=ARCH_CEIL, floor_z=GALLERY_FLOOR, **ARCH_TILES, **shades(42),
                      intent={"purpose": "low covered arch; the threshold the gallery begins at",
                              "classification": "MANDATORY"})
    layout.add_connection("connection:gallerystair_arch", previous, "region:gallery_arch",
                          a1=P(58, 20), a2=P(58, 24), min_width=1536)
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

    previous, previous_edge = "region:loop_arch", (P(58, 34), P(58, 38))
    for step, shade in enumerate((26, 20, 14), start=1):
        region = f"region:loop_stair_{step}"
        x0, x1 = 58 - 2 * step, 60 - 2 * step
        layout.add_region(region, R(x0, 34, x1, 38), role="stair",
                          ceiling_z=GALLERY_FLOOR + step * GAL_STEP - 5 * PH,
                          floor_z=GALLERY_FLOOR + step * GAL_STEP, **COURT_TILES, **shades(shade),
                          intent={"purpose": f"return stair step {step}", "classification": "MANDATORY"})
        layout.add_connection(f"connection:loop_step_{step}", previous, region,
                              a1=previous_edge[0], a2=previous_edge[1], min_width=1536)
        previous, previous_edge = region, (P(x0, 34), P(x0, 38))
    layout.add_connection("connection:loop_courtyard", previous, "region:courtyard",
                          a1=P(52, 34), a2=P(52, 38), min_width=1536)

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
    layout.place_on_wall("sw_crypt_gate", "region:chapel_apse", a1=P(43, 22), a2=P(43, 24), t=0.5,
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
    # A grille set in the arch: this wall is the opening, and filling it is the
    # whole point of a grille. `spans_opening` says so; the check arrived at v5.
    layout.place_on_wall("dec_nave_grille_s", "region:chapel_nave", a1=P(28, 18), a2=P(36, 18),
                         t=0.5, height_player_heights=3.2, offset_player_widths=0.12,
                         spans_opening=True, **grille(1.8))
    for name, t_value in (("south", 0.25), ("north", 0.75)):
        layout.place_on_wall(f"dec_apse_sconce_{name}", "region:chapel_apse",
                             a1=P(42, 21), a2=P(43, 22), t=t_value,
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
    # Moved off the opening. The check that found this arrived at v5; the fault
    # is the same one and it has been here since this iteration.
    layout.place_on_wall("dec_crypt_emblem", "region:crypt_hall", a1=P(40, 60), a2=P(25, 60),
                         t=0.2, height_player_heights=2.2, offset_player_widths=0.12,
                         **emblem(2545, 1.0))
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
                         t=0.12, height_player_heights=1.6, offset_player_widths=0.10,
                         spans_opening=True, **plank(0.6))
    for name, local in (("west", (0.25, 0.5)), ("east", (0.75, 0.5))):
        layout.place_on_ceiling(f"dec_gallery_lamp_{name}", "region:gallery",
                                local=local, height_player_heights=0.9, **lamp(2.2))
    layout.place_on_wall("dec_gallery_grille", "region:gallery", a1=P(73, 10), a2=P(76, 12),
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

CRYPT_STAIRS = tuple(f"region:crypt_stair_{n}" for n in range(1, 5))
GALLERY_STAIRS = tuple(f"region:gallery_stair_{n}" for n in range(1, 4))
LOOP_STAIRS = tuple(f"region:loop_stair_{n}" for n in range(1, 4))

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
                 "region:chapel_aisle_north", "region:chapel_apse"),
                parent_assembly="assembly:courtyard",
                material_vocabulary=dict(NAVE_TILES),
                landmarks=("the raised chancel at the east end",),
            ),
            AuthoredAssembly(
                "assembly:crypt", "lower crypt", "lower_interior",
                "a vaulted hall with a reliquary and a cistern cell, under a darkening stair",
                ("region:crypt_gate", *CRYPT_STAIRS, "region:crypt_hall",
                 "region:crypt_reliquary", "region:crypt_cistern"),
                material_vocabulary=dict(CRYPT_TILES),
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
                ("region:gallery_arch", "region:gallery", "region:loop_arch"),
                material_vocabulary=dict(GALLERY_TILES),
            ),
            AuthoredAssembly(
                "assembly:exit", "exit chamber", "terminal",
                "a keyed chamber that ends the level",
                ("region:exit_door", "region:exit_hall"),
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
                          "region:chapel_aisle_south", "region:chapel_aisle_north"),
        loops=(
            {"loop": "courtyard -> ascent stair -> gallery arch -> gallery -> loop arch "
                     "-> return stair -> courtyard",
             "claim": "the gallery returns the player to the courtyard by a second route"},
        ),
        material_vocabulary={
            "note": "inherited from v2 unchanged; this iteration changes scale and shape",
            "approach": APPROACH_TILES, "courtyard": COURT_TILES, "garden_bed": BED_TILES,
            "chapel_nave": NAVE_TILES, "chapel_aisles": AISLE_TILES, "chapel_apse": APSE_TILES,
            "crypt": CRYPT_TILES, "arches": ARCH_TILES, "gallery": GALLERY_TILES,
            "exit": EXIT_TILES,
        },
    )


ALL_CONNECTIONS = (
    "connection:ledge_tunnel", "connection:tunnel_gatehouse", "connection:gatehouse_courtyard",
    *(f"connection:bed_{name}" for name, _a, _b in BED_EDGES),
    "connection:courtyard_chapeldoor", "connection:chapeldoor_nave",
    "connection:nave_aisle_south", "connection:nave_aisle_north", "connection:nave_apse",
    "connection:courtyard_cryptgate",
    *(f"connection:crypt_step_{n}" for n in range(1, 5)),
    "connection:cryptstair_hall", "connection:crypthall_reliquary", "connection:crypthall_cistern",
    "connection:crypthall_ossuarydoor", "connection:ossuarydoor_ossuary",
    *(f"connection:gallery_step_{n}" for n in range(1, 4)),
    "connection:gallerystair_arch", "connection:arch_gallery", "connection:gallery_looparch",
    *(f"connection:loop_step_{n}" for n in range(1, 4)),
    "connection:loop_courtyard",
    "connection:gallery_exitdoor", "connection:exitdoor_hall",
)

OPEN_EXCEPT_SECRET = tuple(
    name for name in ALL_CONNECTIONS
    if name not in {"connection:crypthall_ossuarydoor", "connection:ossuarydoor_ossuary"}
)
CRYPT_GATE_BOTH = ("connection:courtyard_cryptgate", "connection:crypt_step_1")
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
        ViewpointSpec("view:courtyard_corner", "assembly_center", "region:courtyard",
                      *P(16, 8), COURT - 1024, 256,
                      note="the chamfered south-west corner and the octagonal planter"),
        ViewpointSpec("view:chapel_interior", "assembly_center", "region:chapel_nave",
                      *P(29, 23), COURT - 1024, 0, note="inside the chapel, facing the chancel"),
        ViewpointSpec("view:chapel_apse", "landmark", "region:chapel_apse",
                      *P(40, 23), APSE_FLOOR - 1024, 1024, note="on the chancel, facing the nave"),
        ViewpointSpec("view:crypt_hall", "assembly_center", "region:crypt_hall",
                      *P(32, 55), CRYPT_FLOOR - 1024, 1024, note="the vaulted crypt hall"),
        ViewpointSpec("view:gallery_arch", "transition_approach", "region:gallery_arch",
                      *P(60, 22), GALLERY_FLOOR - 1024, 0, note="under the arch, facing the gallery"),
        ViewpointSpec("view:gallery", "assembly_center", "region:gallery",
                      *P(68, 24), GALLERY_FLOOR - 1024, 1024, note="the gallery, facing the arch"),
        ViewpointSpec("view:courtyard_from_stair", "vertical_relationship", "region:gallery_stair_2",
                      *P(55, 22), COURT - 2 * GAL_STEP - 1024, 1024, note="mid-ascent, looking back"),
        ViewpointSpec("view:chapel_reverse", "reverse_view", "region:courtyard",
                      *P(47, 23), COURT - 1024, 1024, note="east of the chapel, looking back"),
    )


def candidate() -> Candidate:
    return Candidate(
        iteration_id="v3",
        module="projects/reasoned-authoring-v1/level/candidate_v3.py",
        factory=make_layout,
        intent=intent(),
        probes=probes(),
        viewpoints=viewpoints(),
        parent="v2",
        declared_changes=(
            "ceilings set from corpus percentiles for each space's footprint rather than from "
            "round multiples of player height: nave 7->10, aisles 4->6, apse 6->8, gallery 6->12, "
            "exit 4->8, ledge 4->6, gatehouse 3->5, crypt hall 2.18->5, arches 2->4",
            "crypt cells deliberately kept near 3 player heights on the E6M3 precedent, as an "
            "argued exception rather than an unexamined default",
            "chamfers and shallower non-45-degree facets on the courtyard, chapel mass, crypt "
            "hall, gallery, exit hall, ledge and crypt cells; the gatehouse splayed at 37 degrees; "
            "the apse made an eight-sided radial chancel; the garden bed made an octagonal planter",
            "sprite repeats derived from each tile's pixel size and a stated target height in "
            "player heights, instead of copied from the campaign mode",
            "the loop arch given the emblem its twin already had",
        ),
    )
