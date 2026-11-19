"""Cliffside monastery, iteration 1: spatial revision.

Every change below answers a specific piece of v0 evidence, recorded in
../design/reviews/v0.json.

1. v0's independent decompilation put the arrival, the courtyard, and the whole
   gallery into ONE derived perceptual space (space:001, 15 sectors).  The
   intended three identities did not exist in the result, because the only thing
   separating them was height, and height does not create a boundary.
   -> A covered GATEHOUSE now stands between the tunnel and the courtyard, and a
      low dark ARCH stands at each of the gallery's two openings.  These are real
      monastery architecture; their darkness follows from being covered, and it
      is that darkness rather than the height that makes the boundary.

2. v0 was 16 stair sectors and 10 rooms: three rooms and a lot of walking.
   -> The gallery drops to about two player heights, its ascent and its loop
      descent go from five steps to three each, and the crypt stair goes from six
      to four.  Ten stair sectors, fifteen rooms.

3. v0's crypt was one room at the end of a stair (derived space:005 was six
   stair sectors out of eight), and its chapel was a single empty rectangle.
   -> The crypt gains a reliquary and a cistern chamber off a larger hall.  The
      chapel gains two side aisles and a raised, brighter apse that now holds the
      crypt-gate switch instead of a blank wall.

4. v0's declared intent claimed the open exterior stairs for the gallery.  The
   evidence disagreed, and on reflection the evidence is right: an open stair
   rising out of a courtyard reads as part of the courtyard until you pass
   through something.  The stairs are declared as courtyard circulation here, and
   the gallery assembly begins at its arch.

Surface treatment is deliberately still the v0 blockout vocabulary.  The visual
weaknesses v0's rendered frames exposed are iteration 2's subject, and mixing
them in here would make it impossible to tell which change moved which evidence.
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


# --- vertical plan ---------------------------------------------------------
COURT = 8192
SKY = COURT - 16 * PH
LEDGE_CEIL = COURT - 4 * PH
TUNNEL_CEIL = COURT - 2 * PH
GATEHOUSE_CEIL = COURT - 3 * PH
BED_FLOOR = COURT + 2048
NAVE_CEIL = COURT - 7 * PH
AISLE_CEIL = COURT - 4 * PH
APSE_FLOOR = COURT - 2048            # a raised chancel step, under max_step
APSE_CEIL = COURT - 6 * PH

CRYPT_STEP = 3072
CRYPT_FLOOR = COURT + 4 * CRYPT_STEP  # 20480
CRYPT_CEIL = CRYPT_FLOOR - 12288      # 2.18 player heights, the E6M3 range
CHAMBER_CEIL = CRYPT_FLOOR - 2 * PH
CISTERN_FLOOR = CRYPT_FLOOR + 2048

GAL_STEP = 3840                       # three steps, still under max_step 4096
GALLERY_FLOOR = COURT - 3 * GAL_STEP  # -3328, about two player heights up
ARCH_CEIL = GALLERY_FLOOR - 2 * PH
GALLERY_CEIL = GALLERY_FLOOR - 6 * PH
EXIT_CEIL = GALLERY_FLOOR - 4 * PH

SWITCH_HEIGHT = 2.18
SWITCH_OFFSET = 0.12

# --- blockout materials (unchanged from v0 on purpose) ---------------------
EXT_TILES = dict(wall_picnum=2490, floor_picnum=2448, ceiling_picnum=2500)
INT_TILES = dict(wall_picnum=5, floor_picnum=294, ceiling_picnum=416)
CRYPT_TILES = dict(wall_picnum=1097, floor_picnum=1097, ceiling_picnum=1097)

DOOR_FACE = 22
KEYED_FACE = 495
REMOTE_FACE = 200

CH_CRYPT_GATE = 100
CH_SECRET = 102
CH_EXIT = 4


def shades(value: int) -> dict[str, int]:
    """Uniform sector shade; the grouping tolerance reads the floor/ceiling mean."""
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


def make_layout() -> PlanarLayout:
    layout = PlanarLayout(name="monastery-v1", visibility=800)

    # ---- arrival: ledge, tunnel, and the new covered gatehouse -------------
    layout.add_region(
        "region:ledge", R(-10, 18, -2, 26), role="start",
        ceiling_z=LEDGE_CEIL, floor_z=COURT, **EXT_TILES, **shades(34),
        intent={"purpose": "cliffside arrival ledge", "classification": "MANDATORY"},
    )
    layout.add_region(
        "region:gate_tunnel", R(-2, 21, 6, 23), role="gateway",
        ceiling_z=TUNNEL_CEIL, floor_z=COURT, **EXT_TILES, **shades(36),
        intent={"purpose": "constrained gate tunnel", "classification": "MANDATORY"},
    )
    layout.add_region(
        "region:gatehouse", R(6, 19, 10, 25), role="gateway",
        ceiling_z=GATEHOUSE_CEIL, floor_z=COURT, **EXT_TILES, **shades(32),
        intent={
            "purpose": "covered gatehouse; the threshold the courtyard is entered through",
            "classification": "MANDATORY",
            "answers": "v0 evidence that arrival and courtyard were one perceptual space",
        },
    )
    layout.add_connection("connection:ledge_tunnel", "region:ledge", "region:gate_tunnel",
                          a1=P(-2, 21), a2=P(-2, 23), min_width=768)
    layout.add_connection("connection:tunnel_gatehouse", "region:gate_tunnel", "region:gatehouse",
                          a1=P(6, 21), a2=P(6, 23), min_width=768)
    layout.add_connection("connection:gatehouse_courtyard", "region:gatehouse", "region:courtyard",
                          a1=P(10, 19), a2=P(10, 25), min_width=1536)

    # ---- courtyard: one region with its masses carved out ------------------
    layout.add_region(
        "region:courtyard", R(10, 4, 52, 40), role="exterior",
        ceiling_z=SKY, floor_z=COURT, parallax_ceiling=True,
        **EXT_TILES, **sky_shades(16),
        intent={"purpose": "arrival garden courtyard", "classification": "MANDATORY"},
    )
    layout.carve_hole("region:courtyard", R(24, 12, 44, 34))   # chapel shell
    layout.carve_hole("region:courtyard", R(13, 8, 20, 16))    # garden bed

    layout.add_region(
        "region:garden_bed", R(13, 8, 20, 16), role="detail",
        ceiling_z=SKY, floor_z=BED_FLOOR, parallax_ceiling=True,
        wall_picnum=2490, floor_picnum=270, ceiling_picnum=2500, **sky_shades(20),
        intent={"purpose": "sunken planter inside the courtyard", "classification": "OPTIONAL"},
    )
    for name, a1, a2 in (
        ("south", P(13, 8), P(20, 8)), ("east", P(20, 8), P(20, 16)),
        ("north", P(13, 16), P(20, 16)), ("west", P(13, 8), P(13, 16)),
    ):
        layout.add_connection(f"connection:bed_{name}", "region:courtyard", "region:garden_bed",
                              a1=a1, a2=a2, min_width=512)

    # ---- chapel: nave, two aisles, and a raised apse -----------------------
    layout.add_region(
        "region:chapel_door", R(24, 21, 26, 25), role="doorway", type=600,
        ceiling_z=COURT, floor_z=COURT,
        wall_picnum=DOOR_FACE, floor_picnum=DOOR_FACE, ceiling_picnum=DOOR_FACE, **shades(16),
        sector_behavior=_z_door(COURT, COURT - 6 * PH, interaction="direct"),
        intent={"purpose": "chapel west door", "classification": "MANDATORY",
                "interaction": "direct_use"},
    )
    layout.add_region(
        "region:chapel_nave", R(26, 18, 38, 28), role="interior",
        ceiling_z=NAVE_CEIL, floor_z=COURT, **INT_TILES, **shades(20),
        intent={"purpose": "chapel nave", "classification": "MANDATORY"},
    )
    layout.add_region(
        "region:chapel_aisle_south", R(26, 14, 38, 18), role="interior",
        ceiling_z=AISLE_CEIL, floor_z=COURT, **INT_TILES, **shades(26),
        intent={"purpose": "south side aisle, lower than the nave", "classification": "OPTIONAL"},
    )
    layout.add_region(
        "region:chapel_aisle_north", R(26, 28, 38, 32), role="interior",
        ceiling_z=AISLE_CEIL, floor_z=COURT, **INT_TILES, **shades(26),
        intent={"purpose": "north side aisle, lower than the nave", "classification": "OPTIONAL"},
    )
    layout.add_region(
        "region:chapel_apse", R(38, 20, 42, 26), role="interior",
        ceiling_z=APSE_CEIL, floor_z=APSE_FLOOR, **INT_TILES, **shades(8),
        intent={"purpose": "raised, brighter apse holding the crypt-gate switch",
                "classification": "MANDATORY"},
    )
    layout.add_connection("connection:courtyard_chapeldoor", "region:courtyard", "region:chapel_door",
                          role="doorway", gated=True, a1=P(24, 21), a2=P(24, 25),
                          face_picnum=DOOR_FACE, min_width=1536)
    layout.add_connection("connection:chapeldoor_nave", "region:chapel_door", "region:chapel_nave",
                          role="doorway", gated=True, a1=P(26, 21), a2=P(26, 25),
                          face_picnum=DOOR_FACE, min_width=1536)
    layout.add_connection("connection:nave_aisle_south", "region:chapel_nave", "region:chapel_aisle_south",
                          a1=P(26, 18), a2=P(38, 18), min_width=1536)
    layout.add_connection("connection:nave_aisle_north", "region:chapel_nave", "region:chapel_aisle_north",
                          a1=P(26, 28), a2=P(38, 28), min_width=1536)
    layout.add_connection("connection:nave_apse", "region:chapel_nave", "region:chapel_apse",
                          a1=P(38, 20), a2=P(38, 26), min_width=1536)

    # ---- crypt: a shorter stair into a hall with two chambers --------------
    layout.add_region(
        "region:crypt_gate", R(30, 40, 34, 42), role="doorway", type=600,
        ceiling_z=COURT, floor_z=COURT,
        wall_picnum=REMOTE_FACE, floor_picnum=REMOTE_FACE, ceiling_picnum=REMOTE_FACE, **shades(16),
        sector_behavior=_z_door(COURT, COURT - 3 * PH, interaction="remote", rx=CH_CRYPT_GATE),
        intent={"purpose": "crypt gate opened from the chapel apse", "classification": "MANDATORY",
                "interaction": "remote_switch"},
    )
    layout.add_connection("connection:courtyard_cryptgate", "region:courtyard", "region:crypt_gate",
                          role="doorway", gated=True, a1=P(30, 40), a2=P(34, 40),
                          face_picnum=REMOTE_FACE, min_width=1536)

    # Darkening rather than brightening along the run: the destination is the
    # crypt, and the light the player walks toward is in the hall below, not on
    # the stair.  This inverts the E2M6 ramp on purpose.
    previous, previous_edge = "region:crypt_gate", (P(30, 42), P(34, 42))
    for step, shade in enumerate((28, 34, 40, 46), start=1):
        region = f"region:crypt_stair_{step}"
        y0, y1 = 40 + 2 * step, 42 + 2 * step
        layout.add_region(
            region, R(30, y0, 34, y1), role="stair",
            ceiling_z=COURT + step * CRYPT_STEP - 3 * PH,
            floor_z=COURT + step * CRYPT_STEP, **CRYPT_TILES, **shades(shade),
            intent={"purpose": f"crypt stair step {step}", "classification": "MANDATORY"},
        )
        layout.add_connection(f"connection:crypt_step_{step}", previous, region,
                              a1=previous_edge[0], a2=previous_edge[1], min_width=1536)
        previous, previous_edge = region, (P(30, y1), P(34, y1))

    layout.add_region(
        "region:crypt_hall", R(22, 50, 42, 60), role="interior",
        ceiling_z=CRYPT_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_TILES, **shades(32),
        intent={"purpose": "crypt hall; the lit destination the dark stair descends to",
                "classification": "MANDATORY"},
    )
    layout.add_connection("connection:cryptstair_hall", previous, "region:crypt_hall",
                          a1=P(30, 50), a2=P(34, 50), min_width=1536)

    layout.add_region(
        "region:crypt_reliquary", R(16, 52, 22, 58), role="key_branch",
        ceiling_z=CHAMBER_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_TILES, **shades(36),
        intent={"purpose": "reliquary chamber holding the skull key", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:crypthall_reliquary", "region:crypt_hall", "region:crypt_reliquary",
                          a1=P(22, 52), a2=P(22, 58), min_width=1536)

    layout.add_region(
        "region:crypt_cistern", R(26, 60, 34, 66), role="interior",
        ceiling_z=CHAMBER_CEIL, floor_z=CISTERN_FLOOR, **CRYPT_TILES, **shades(40),
        intent={"purpose": "sunken cistern chamber holding the ossuary switch",
                "classification": "MANDATORY"},
    )
    layout.add_connection("connection:crypthall_cistern", "region:crypt_hall", "region:crypt_cistern",
                          a1=P(26, 60), a2=P(34, 60), min_width=1536)

    # ---- optional ossuary behind a hidden panel ----------------------------
    layout.add_region(
        "region:ossuary_door", R(42, 52, 44, 56), role="doorway", type=600,
        ceiling_z=CRYPT_FLOOR, floor_z=CRYPT_FLOOR, **CRYPT_TILES, **shades(40),
        sector_behavior=_z_door(CRYPT_FLOOR, CHAMBER_CEIL, interaction="remote", rx=CH_SECRET),
        intent={"purpose": "hidden ossuary panel", "classification": "OPTIONAL", "hidden": True},
    )
    layout.add_region(
        "region:ossuary", R(44, 50, 52, 60), role="secret",
        ceiling_z=CHAMBER_CEIL, floor_z=CRYPT_FLOOR, declared_zero_exit=True,
        **CRYPT_TILES, **shades(44),
        intent={"purpose": "optional ossuary", "classification": "OPTIONAL"},
    )
    layout.add_connection("connection:crypthall_ossuarydoor", "region:crypt_hall", "region:ossuary_door",
                          role="doorway", gated=True, a1=P(42, 52), a2=P(42, 56), min_width=1536)
    layout.add_connection("connection:ossuarydoor_ossuary", "region:ossuary_door", "region:ossuary",
                          role="doorway", gated=True, a1=P(44, 52), a2=P(44, 56), min_width=1536)

    # ---- ascent: three open courtyard steps, then the gallery arch ---------
    previous, previous_edge = "region:courtyard", (P(52, 20), P(52, 24))
    for step, shade in enumerate((14, 20, 26), start=1):
        region = f"region:gallery_stair_{step}"
        x0, x1 = 50 + 2 * step, 52 + 2 * step
        layout.add_region(
            region, R(x0, 20, x1, 24), role="stair",
            ceiling_z=COURT - step * GAL_STEP - 4 * PH,
            floor_z=COURT - step * GAL_STEP, **EXT_TILES, **shades(shade),
            intent={"purpose": f"open courtyard stair step {step}", "classification": "MANDATORY"},
        )
        layout.add_connection(f"connection:gallery_step_{step}", previous, region,
                              a1=previous_edge[0], a2=previous_edge[1], min_width=1536)
        previous, previous_edge = region, (P(x1, 20), P(x1, 24))

    layout.add_region(
        "region:gallery_arch", R(58, 20, 62, 24), role="gateway",
        ceiling_z=ARCH_CEIL, floor_z=GALLERY_FLOOR, **EXT_TILES, **shades(42),
        intent={"purpose": "low covered arch; the threshold the gallery begins at",
                "classification": "MANDATORY",
                "answers": "v0 evidence that the gallery was absorbed into the courtyard"},
    )
    layout.add_connection("connection:gallerystair_arch", previous, "region:gallery_arch",
                          a1=P(58, 20), a2=P(58, 24), min_width=1536)

    layout.add_region(
        "region:gallery", R(62, 10, 76, 38), role="upper",
        ceiling_z=GALLERY_CEIL, floor_z=GALLERY_FLOOR, **INT_TILES, **shades(12),
        intent={"purpose": "upper service gallery", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:arch_gallery", "region:gallery_arch", "region:gallery",
                          a1=P(62, 20), a2=P(62, 24), min_width=1536)

    # ---- loop: a second arch and three steps back down to the courtyard ----
    layout.add_region(
        "region:loop_arch", R(58, 34, 62, 38), role="gateway",
        ceiling_z=ARCH_CEIL, floor_z=GALLERY_FLOOR, **EXT_TILES, **shades(42),
        intent={"purpose": "second gallery arch onto the return stair", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:gallery_looparch", "region:gallery", "region:loop_arch",
                          a1=P(62, 34), a2=P(62, 38), min_width=1536)

    previous, previous_edge = "region:loop_arch", (P(58, 34), P(58, 38))
    for step, shade in enumerate((26, 20, 14), start=1):
        region = f"region:loop_stair_{step}"
        x0, x1 = 58 - 2 * step, 60 - 2 * step
        layout.add_region(
            region, R(x0, 34, x1, 38), role="stair",
            ceiling_z=GALLERY_FLOOR + step * GAL_STEP - 4 * PH,
            floor_z=GALLERY_FLOOR + step * GAL_STEP, **EXT_TILES, **shades(shade),
            intent={"purpose": f"return stair step {step}", "classification": "MANDATORY"},
        )
        layout.add_connection(f"connection:loop_step_{step}", previous, region,
                              a1=previous_edge[0], a2=previous_edge[1], min_width=1536)
        previous, previous_edge = region, (P(x0, 34), P(x0, 38))
    layout.add_connection("connection:loop_courtyard", previous, "region:courtyard",
                          a1=P(52, 34), a2=P(52, 38), min_width=1536)

    # ---- exit --------------------------------------------------------------
    layout.add_region(
        "region:exit_door", R(76, 22, 78, 26), role="doorway", type=600,
        ceiling_z=GALLERY_FLOOR, floor_z=GALLERY_FLOOR,
        wall_picnum=KEYED_FACE, floor_picnum=KEYED_FACE, ceiling_picnum=KEYED_FACE, **shades(16),
        sector_behavior=_z_door(GALLERY_FLOOR, EXIT_CEIL, interaction="direct", key=1),
        intent={"purpose": "skull-keyed exit gate", "classification": "MANDATORY",
                "interaction": "direct_use"},
    )
    layout.add_region(
        "region:exit_hall", R(78, 18, 88, 30), role="exit", declared_zero_exit=True,
        ceiling_z=EXIT_CEIL, floor_z=GALLERY_FLOOR, **INT_TILES, **shades(18),
        intent={"purpose": "exit chamber", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:gallery_exitdoor", "region:gallery", "region:exit_door",
                          role="doorway", gated=True, a1=P(76, 22), a2=P(76, 26),
                          face_picnum=KEYED_FACE, min_width=1536)
    layout.add_connection("connection:exitdoor_hall", "region:exit_door", "region:exit_hall",
                          role="doorway", gated=True, a1=P(78, 22), a2=P(78, 26),
                          face_picnum=KEYED_FACE, min_width=1536)

    # ---- population: still only what the progression needs -----------------
    start = P(-6, 22)
    layout.set_player_start("region:ledge", x=start[0], y=start[1], z=COURT - 1024, angle=0)
    layout.add_sprite("sp_start", "region:ledge", x=start[0], y=start[1], z=COURT - 1024,
                      **sprite_appearance(1, angle=0), behavior={"state": 1})

    layout.place_on_wall(
        "sw_crypt_gate", "region:chapel_apse", a1=P(42, 20), a2=P(42, 26), t=0.5,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET, **SWITCH,
        behavior={"tx_id": CH_CRYPT_GATE, "command": 1, "trigger_on": 1,
                  "trigger_push": 1, "data_1": 203},
    )
    layout.place_on_wall(
        "sw_ossuary", "region:crypt_cistern", a1=P(34, 66), a2=P(26, 66), t=0.5,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET, **SWITCH,
        behavior={"tx_id": CH_SECRET, "command": 1, "trigger_on": 1,
                  "trigger_push": 1, "data_1": 203},
    )
    layout.place_on_wall(
        "sw_exit", "region:exit_hall", a1=P(88, 18), a2=P(88, 30), t=0.5,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET, **SWITCH,
        behavior={"tx_id": CH_EXIT, "command": 1, "trigger_on": 1, "trigger_push": 1},
    )
    layout.place_on_floor("key_skull", "region:crypt_reliquary", local=(0.5, 0.5),
                          **sprite_appearance(100), behavior={"state": 1})
    return layout


# ---------------------------------------------------------------------------
# Declared intent
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
                "a covered ledge, a tight tunnel, and a gatehouse that withhold the courtyard",
                ("region:ledge", "region:gate_tunnel", "region:gatehouse"),
                material_vocabulary={"wall": 2490, "floor": 2448, "ceiling": 2500},
            ),
            AuthoredAssembly(
                "assembly:courtyard", "arrival courtyard", "exterior_parent",
                (
                    "the large open cliffside courtyard that contains the chapel and the "
                    "garden bed, together with the open stairs that climb out of it. v0 "
                    "evidence showed those stairs read as courtyard, and I now agree."
                ),
                ("region:courtyard", "region:garden_bed", *GALLERY_STAIRS, *LOOP_STAIRS),
                material_vocabulary={"wall": 2490, "floor": 2448, "ceiling": 2500},
                landmarks=("the chapel mass standing in the middle of the courtyard",),
            ),
            AuthoredAssembly(
                "assembly:chapel", "chapel", "embedded_building",
                "a tall brick chapel embedded in the courtyard: nave, two aisles, raised apse",
                ("region:chapel_door", "region:chapel_nave", "region:chapel_aisle_south",
                 "region:chapel_aisle_north", "region:chapel_apse"),
                parent_assembly="assembly:courtyard",
                material_vocabulary={"wall": 5, "floor": 294, "ceiling": 416},
                landmarks=("the raised apse at the east end",),
            ),
            AuthoredAssembly(
                "assembly:crypt", "lower crypt", "lower_interior",
                "a low dark hall with a reliquary and a cistern chamber, under a dark stair",
                ("region:crypt_gate", *CRYPT_STAIRS, "region:crypt_hall",
                 "region:crypt_reliquary", "region:crypt_cistern"),
                material_vocabulary={"wall": 1097, "floor": 1097, "ceiling": 1097},
            ),
            AuthoredAssembly(
                "assembly:ossuary", "optional ossuary", "optional_side_space",
                "an optional room behind a hidden panel in the crypt hall",
                ("region:ossuary_door", "region:ossuary"),
                parent_assembly="assembly:crypt", optional=True, mandatory=False,
            ),
            AuthoredAssembly(
                "assembly:gallery", "upper gallery", "upper_interior",
                "an elevated gallery entered through one arch and left through another",
                ("region:gallery_arch", "region:gallery", "region:loop_arch"),
                material_vocabulary={"wall": 5, "floor": 294, "ceiling": 416},
            ),
            AuthoredAssembly(
                "assembly:exit", "exit chamber", "terminal",
                "a keyed chamber that ends the level",
                ("region:exit_door", "region:exit_hall"),
            ),
        ),
        transitions=(
            AuthoredTransition(
                "transition:reveal", "gatehouse into the courtyard",
                "region:gatehouse", "region:courtyard", "constrained_to_open",
                "the low covered gatehouse should release into the tall open courtyard",
                connection_id="connection:gatehouse_courtyard",
                expectation={"area_ratio_at_least": 8, "clear_height_gain_at_least": 10 * PH},
            ),
            AuthoredTransition(
                "transition:descent", "courtyard down into the crypt",
                "region:courtyard", "region:crypt_hall", "vertical_descent",
                "a darkening stair down into a low lit hall",
                connection_id="connection:courtyard_cryptgate",
                expectation={"floor_gain_at_least": 4 * CRYPT_STEP},
            ),
            AuthoredTransition(
                "transition:ascent", "courtyard up through the arch into the gallery",
                "region:gallery_arch", "region:gallery", "vertical_ascent",
                "a low dark arch opening onto the elevated gallery",
                connection_id="connection:arch_gallery",
                expectation={"area_ratio_at_least": 8},
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
            {"step": 3, "action": "use the apse switch to open the crypt gate",
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
            {"landmark": "raised apse", "regions": ["region:chapel_apse"],
             "claim": "the apse should be the brightest point inside the chapel"},
        ),
        optional_regions=("region:ossuary_door", "region:ossuary", "region:garden_bed",
                          "region:chapel_aisle_south", "region:chapel_aisle_north"),
        loops=(
            {"loop": "courtyard -> ascent stair -> gallery arch -> gallery -> loop arch "
                     "-> return stair -> courtyard",
             "claim": "the gallery returns the player to the courtyard by a second route"},
        ),
        material_vocabulary={
            "note": "unchanged from v0 on purpose; surface treatment is iteration 2's subject",
            "exterior": EXT_TILES, "interior": INT_TILES, "crypt": CRYPT_TILES,
        },
    )


ALL_CONNECTIONS = (
    "connection:ledge_tunnel", "connection:tunnel_gatehouse", "connection:gatehouse_courtyard",
    "connection:bed_south", "connection:bed_east", "connection:bed_north", "connection:bed_west",
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

# A closed Blood Z-door blocks BOTH of its portals, so opening a gate means
# naming the connection on each side of it.  v0's probe named only one.
CRYPT_GATE_BOTH = ("connection:courtyard_cryptgate", "connection:crypt_step_1")
CHAPEL_DOOR_BOTH = ("connection:courtyard_chapeldoor", "connection:chapeldoor_nave")


def probes() -> tuple[ProbeRequest, ...]:
    return (
        ProbeRequest(
            "probe:reach_chapel", "access",
            "can the chapel nave be reached from the start?",
            "the chapel is mandatory and holds the crypt-gate switch",
            target_region="region:chapel_nave", opened_connections=CHAPEL_DOOR_BOTH,
        ),
        ProbeRequest(
            "probe:reach_apse", "access",
            "can the raised apse be reached once the chapel is open?",
            "the apse holds the switch the whole crypt branch depends on",
            target_region="region:chapel_apse", opened_connections=CHAPEL_DOOR_BOTH,
        ),
        ProbeRequest(
            "probe:reach_crypt", "access",
            "can the crypt hall be reached once the crypt gate is open?",
            "the crypt holds the key the exit needs; v0's version of this probe opened only one side of the gate",
            target_region="region:crypt_hall", opened_connections=CRYPT_GATE_BOTH,
        ),
        ProbeRequest(
            "probe:route_start_to_exit", "route",
            "what route runs from the start to the exit chamber?",
            "the brief needs a coherent start-to-exit spine",
            target_region="region:exit_hall", opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:gallery_seen_late", "visibility",
            "how far along the start-to-exit route does the gallery first become adjacent?",
            "the gallery is the last major identity; it should be met late, not early",
            target_region="region:gallery", opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:reveal_contrast", "transition",
            "does the gatehouse to courtyard step produce measurable spatial release?",
            "the brief asks for one composed constrained-to-open transition",
            source_region="region:gatehouse", destination_region="region:courtyard",
        ),
        ProbeRequest(
            "probe:arch_contrast", "transition",
            "does the gallery arch to gallery step produce release on the upper level too?",
            "the arch is the new threshold the gallery's identity depends on",
            source_region="region:gallery_arch", destination_region="region:gallery",
        ),
        ProbeRequest(
            "probe:crypt_contrast", "transition",
            "does arriving in the crypt hall read as a contraction?",
            "the crypt must feel unlike the courtyard it descends from",
            source_region="region:courtyard", destination_region="region:crypt_hall",
        ),
        ProbeRequest(
            "probe:gallery_contrast", "transition",
            "does the gallery read as different from the courtyard it rises out of?",
            "the gallery is a separate intended identity",
            source_region="region:courtyard", destination_region="region:gallery",
        ),
        ProbeRequest(
            "probe:ossuary_reachable_while_shut", "access",
            "is the ossuary reachable while its panel stays shut? (fail is the intended answer)",
            "optional means gated, not accidentally disconnected",
            target_region="region:ossuary", opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:gallery_choices", "escape",
            "how many onward routes leave the gallery?",
            (
                "the brief asks for one real spatial loop; two independent descents out of "
                "the gallery is the observable part of that claim"
            ),
            start_region="region:gallery", opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:revisit_after_crypt_gate", "revisit",
            "what does the apse switch actually open?",
            "the gate must add the crypt branch and nothing else",
            target_region="region:crypt_hall", opened_connections=CHAPEL_DOOR_BOTH,
            alt_opened_connections=CHAPEL_DOOR_BOTH + CRYPT_GATE_BOTH,
        ),
        ProbeRequest(
            "probe:courtyard_choices", "escape",
            "how many onward choices does the courtyard offer?",
            "a hub parent space should branch, not funnel",
            start_region="region:courtyard", opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:gatehouse_choices", "escape",
            "how many onward choices does the gatehouse offer?",
            "the approach should be the narrowest decision point of the level",
            start_region="region:gatehouse", opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:chapel_choices", "escape",
            "how many onward choices does the chapel nave offer?",
            "the chapel should have parts, not be a single terminus",
            start_region="region:chapel_nave", opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:crypt_choices", "escape",
            "how many onward choices does the crypt hall offer?",
            "the crypt should be a hall with chambers, not one room",
            start_region="region:crypt_hall", opened_connections=OPEN_EXCEPT_SECRET,
        ),
    )


def viewpoints() -> tuple[ViewpointSpec, ...]:
    return (
        ViewpointSpec("view:start", "player_start", "region:ledge",
                      *P(-6, 22), COURT - 1024, 0,
                      note="the arrival pose the player actually spawns in"),
        ViewpointSpec("view:gate_approach", "transition_approach", "region:gate_tunnel",
                      *P(2, 22), COURT - 1024, 0,
                      note="inside the constrained tunnel, facing the gatehouse"),
        ViewpointSpec("view:gatehouse", "transition_approach", "region:gatehouse",
                      *P(8, 22), COURT - 1024, 0,
                      note="under the new gatehouse, facing the courtyard release"),
        ViewpointSpec("view:courtyard_center", "assembly_center", "region:courtyard",
                      *P(17, 22), COURT - 1024, 0,
                      note="standing in the west courtyard, facing the chapel mass"),
        ViewpointSpec("view:chapel_interior", "assembly_center", "region:chapel_nave",
                      *P(29, 23), COURT - 1024, 0,
                      note="just inside the chapel, facing the raised apse"),
        ViewpointSpec("view:chapel_apse", "landmark", "region:chapel_apse",
                      *P(40, 23), APSE_FLOOR - 1024, 1024,
                      note="on the apse step, facing back down the nave"),
        ViewpointSpec("view:crypt_hall", "assembly_center", "region:crypt_hall",
                      *P(32, 55), CRYPT_FLOOR - 1024, 1024,
                      note="the crypt hall, facing the reliquary"),
        ViewpointSpec("view:gallery_arch", "transition_approach", "region:gallery_arch",
                      *P(60, 22), GALLERY_FLOOR - 1024, 0,
                      note="under the new arch, facing into the gallery"),
        ViewpointSpec("view:gallery", "assembly_center", "region:gallery",
                      *P(68, 24), GALLERY_FLOOR - 1024, 1024,
                      note="the upper gallery, facing back at the arch"),
        ViewpointSpec("view:courtyard_from_stair", "vertical_relationship", "region:gallery_stair_2",
                      *P(55, 22), COURT - 2 * GAL_STEP - 1024, 1024,
                      note="mid-ascent, showing the courtyard below and behind"),
        ViewpointSpec("view:chapel_reverse", "reverse_view", "region:courtyard",
                      *P(47, 23), COURT - 1024, 1024,
                      note="east of the chapel, looking back across the courtyard"),
    )


def candidate() -> Candidate:
    return Candidate(
        iteration_id="v1",
        module="projects/reasoned-authoring-v1/level/candidate_v1.py",
        factory=make_layout,
        intent=intent(),
        probes=probes(),
        viewpoints=viewpoints(),
        parent="v0",
        declared_changes=(
            "added a covered gatehouse and two gallery arches as real thresholds, each "
            "darker than its neighbours, to answer the collapsed perceptual space",
            "cut stair sectors from 16 to 10 and raised room sectors from 10 to 15",
            "lowered the gallery from about 2.7 to about 2.0 player heights",
            "gave the chapel two side aisles and a raised, brighter apse holding the switch",
            "gave the crypt a larger hall plus a reliquary and a cistern chamber",
            "declared the open exterior stairs as courtyard circulation instead of gallery",
            "fixed probe:reach_crypt to open both sides of the crypt gate and reworded "
            "the ossuary probe so its intended answer is not phrased as a failure",
            "surface treatment deliberately unchanged; that is iteration 2",
        ),
    )
