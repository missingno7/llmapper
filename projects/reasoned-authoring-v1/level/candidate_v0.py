"""Cliffside monastery, iteration 0: blockout.

Written against the brief in ../design/brief.md and the precedents frozen in
../references/precedent-packet.json.  This iteration deliberately commits only
to hierarchy, containment, connectivity, scale, and the start/exit spine.  It
uses two coarse material sets (exterior / interior) and the minimum sprites the
progression needs, because deciding surface treatment before knowing how the
space actually reads would be guessing.

Precedents applied here:
  * precedent:open-parent-containing-structure -> the courtyard is ONE region
    with holes carved for the chapel shell and the garden bed.
  * precedent:release-opening -> a 2-unit-wide, 2-player-height gate tunnel
    opens onto the courtyard.
  * precedent:stair-run -> the crypt stair uses the 2048-unit step rise
    measured on E2M6 sector:52..63.
  * precedent:dark-low-interior -> the crypt is low, small, dark, monomaterial.
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

# --- units -----------------------------------------------------------------
U = 384          # one player body width
PH = 0x1600      # 5632, one player standing height

def P(x: float, y: float) -> tuple[int, int]:
    return (int(round(x * U)), int(round(y * U)))

def R(x0: float, y0: float, x1: float, y1: float) -> list[tuple[int, int]]:
    return [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)]

# --- vertical plan ---------------------------------------------------------
COURT = 8192                       # courtyard datum
SKY = COURT - 16 * PH              # open cliffside sky
LEDGE_CEIL = COURT - 4 * PH
TUNNEL_CEIL = COURT - 2 * PH       # constrained approach
BED_FLOOR = COURT + 2048           # sunken planter, one step down
NAVE_CEIL = COURT - 7 * PH         # tall chapel interior
CRYPT_STEP = 2048                  # E2M6 sector:52..63 step rise
CRYPT_FLOOR = COURT + 6 * CRYPT_STEP
CRYPT_CEIL = CRYPT_FLOOR - 12288   # 2.18 player heights, matches E6M3 range
NICHE_CEIL = CRYPT_FLOOR - 2 * PH
GAL_STEP = 3072
GALLERY_FLOOR = COURT - 5 * GAL_STEP
GALLERY_CEIL = GALLERY_FLOOR - 6 * PH
EXIT_CEIL = GALLERY_FLOOR - 4 * PH

SWITCH_HEIGHT = 2.18
SWITCH_OFFSET = 0.12

# --- blockout materials ----------------------------------------------------
# Two sets only.  Corpus-backed (E2M6 exterior vocabulary; tile 5 / 294 / 416
# are high-usage interior tiles) but intentionally undifferentiated per
# assembly until the spatial reading is settled.
EXT = dict(wall_picnum=2490, floor_picnum=2448, ceiling_picnum=2500,
           wall_shade=16, floor_shade=16, ceiling_shade=0)
INT = dict(wall_picnum=5, floor_picnum=294, ceiling_picnum=416,
           wall_shade=20, floor_shade=20, ceiling_shade=16)
CRYPT_MAT = dict(wall_picnum=1097, floor_picnum=1097, ceiling_picnum=1097,
                 wall_shade=44, floor_shade=44, ceiling_shade=44)

DOOR_FACE = 22        # campaign wall_push Z-ceiling approach face
KEYED_FACE = 495      # E3M3/E3M4 skull-key direct-use face
REMOTE_FACE = 200     # modal closed remote Z-ceiling approach

CH_CRYPT_GATE = 100
CH_SECRET = 102
CH_EXIT = 4           # kChannelLevelExitNormal


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
    layout = PlanarLayout(name="monastery-v0", visibility=800)

    # ---- arrival -----------------------------------------------------------
    layout.add_region(
        "region:ledge", R(-6, 18, 2, 26), role="start",
        ceiling_z=LEDGE_CEIL, floor_z=COURT, **EXT,
        intent={"purpose": "cliffside arrival ledge", "classification": "MANDATORY"},
    )
    layout.add_region(
        "region:gate_tunnel", R(2, 21, 10, 23), role="gateway",
        ceiling_z=TUNNEL_CEIL, floor_z=COURT, **EXT,
        intent={"purpose": "constrained gate tunnel", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:ledge_tunnel", "region:ledge", "region:gate_tunnel",
                          a1=P(2, 21), a2=P(2, 23), min_width=768)
    layout.add_connection("connection:tunnel_courtyard", "region:gate_tunnel", "region:courtyard",
                          a1=P(10, 21), a2=P(10, 23), min_width=768)

    # ---- courtyard: one region, holes carved for the masses it contains ----
    layout.add_region(
        "region:courtyard", R(10, 4, 52, 40), role="exterior",
        ceiling_z=SKY, floor_z=COURT, parallax_ceiling=True, **EXT,
        intent={"purpose": "arrival garden courtyard", "classification": "MANDATORY"},
    )
    layout.carve_hole("region:courtyard", R(24, 12, 44, 34))   # chapel shell
    layout.carve_hole("region:courtyard", R(13, 8, 20, 16))    # garden bed

    layout.add_region(
        "region:garden_bed", R(13, 8, 20, 16), role="detail",
        ceiling_z=SKY, floor_z=BED_FLOOR, parallax_ceiling=True,
        wall_picnum=2490, floor_picnum=270, ceiling_picnum=2500,
        wall_shade=16, floor_shade=20, ceiling_shade=0,
        intent={"purpose": "sunken planter inside the courtyard", "classification": "OPTIONAL"},
    )
    for name, a1, a2 in (
        ("south", P(13, 8), P(20, 8)), ("east", P(20, 8), P(20, 16)),
        ("north", P(13, 16), P(20, 16)), ("west", P(13, 8), P(13, 16)),
    ):
        layout.add_connection(f"connection:bed_{name}", "region:courtyard", "region:garden_bed",
                              a1=a1, a2=a2, min_width=512)

    # ---- chapel: embedded building inside the courtyard hole ---------------
    layout.add_region(
        "region:chapel_door", R(24, 21, 26, 25), role="doorway", type=600,
        ceiling_z=COURT, floor_z=COURT,
        wall_picnum=DOOR_FACE, floor_picnum=DOOR_FACE, ceiling_picnum=DOOR_FACE,
        wall_shade=16, floor_shade=16, ceiling_shade=16,
        sector_behavior=_z_door(COURT, COURT - 6 * PH, interaction="direct"),
        intent={"purpose": "chapel west door", "classification": "MANDATORY",
                "interaction": "direct_use"},
    )
    layout.add_region(
        "region:chapel_nave", R(26, 14, 42, 32), role="interior",
        # Reached only through the chapel door, so it has no walkable-at-rest portal.
        declared_zero_exit=True,
        ceiling_z=NAVE_CEIL, floor_z=COURT, **INT,
        intent={"purpose": "chapel nave", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:courtyard_chapeldoor", "region:courtyard", "region:chapel_door",
                          role="doorway", gated=True, a1=P(24, 21), a2=P(24, 25),
                          face_picnum=DOOR_FACE, min_width=1536)
    layout.add_connection("connection:chapeldoor_nave", "region:chapel_door", "region:chapel_nave",
                          role="doorway", gated=True, a1=P(26, 21), a2=P(26, 25),
                          face_picnum=DOOR_FACE, min_width=1536)

    # ---- crypt: remote-gated stair down from the courtyard's north wall ----
    layout.add_region(
        "region:crypt_gate", R(30, 40, 34, 42), role="doorway", type=600,
        ceiling_z=COURT, floor_z=COURT,
        wall_picnum=REMOTE_FACE, floor_picnum=REMOTE_FACE, ceiling_picnum=REMOTE_FACE,
        wall_shade=16, floor_shade=16, ceiling_shade=16,
        sector_behavior=_z_door(COURT, COURT - 3 * PH, interaction="remote", rx=CH_CRYPT_GATE),
        intent={"purpose": "crypt gate opened from the chapel", "classification": "MANDATORY",
                "interaction": "remote_switch"},
    )
    layout.add_connection("connection:courtyard_cryptgate", "region:courtyard", "region:crypt_gate",
                          role="doorway", gated=True, a1=P(30, 40), a2=P(34, 40),
                          face_picnum=REMOTE_FACE, min_width=1536)

    previous = "region:crypt_gate"
    previous_edge = P(30, 42), P(34, 42)
    for step in range(1, 7):
        region = f"region:crypt_stair_{step}"
        y0, y1 = 40 + 2 * step, 42 + 2 * step
        layout.add_region(
            region, R(30, y0, 34, y1), role="stair",
            ceiling_z=COURT + step * CRYPT_STEP - 3 * PH, floor_z=COURT + step * CRYPT_STEP,
            **CRYPT_MAT,
            intent={"purpose": f"crypt stair step {step}", "classification": "MANDATORY"},
        )
        layout.add_connection(f"connection:crypt_step_{step}", previous, region,
                              a1=previous_edge[0], a2=previous_edge[1], min_width=1536)
        previous, previous_edge = region, (P(30, y1), P(34, y1))

    layout.add_region(
        "region:crypt_hall", R(24, 54, 40, 62), role="interior",
        ceiling_z=CRYPT_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_MAT,
        intent={"purpose": "crypt hall", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:cryptstair_hall", previous, "region:crypt_hall",
                          a1=P(30, 54), a2=P(34, 54), min_width=1536)

    layout.add_region(
        "region:crypt_key_niche", R(18, 56, 24, 60), role="key_branch",
        ceiling_z=NICHE_CEIL, floor_z=CRYPT_FLOOR, **CRYPT_MAT,
        intent={"purpose": "reliquary niche holding the skull key", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:crypthall_keyniche", "region:crypt_hall", "region:crypt_key_niche",
                          a1=P(24, 56), a2=P(24, 60), min_width=1536)

    layout.add_region(
        "region:crypt_secret_door", R(40, 56, 42, 60), role="doorway", type=600,
        ceiling_z=CRYPT_FLOOR, floor_z=CRYPT_FLOOR,
        wall_picnum=1097, floor_picnum=1097, ceiling_picnum=1097,
        wall_shade=44, floor_shade=44, ceiling_shade=44,
        sector_behavior=_z_door(CRYPT_FLOOR, NICHE_CEIL, interaction="remote", rx=CH_SECRET),
        intent={"purpose": "hidden ossuary panel", "classification": "OPTIONAL", "hidden": True},
    )
    layout.add_region(
        "region:crypt_secret_niche", R(42, 54, 50, 62), role="secret",
        ceiling_z=NICHE_CEIL, floor_z=CRYPT_FLOOR, declared_zero_exit=True, **CRYPT_MAT,
        intent={"purpose": "optional ossuary", "classification": "OPTIONAL"},
    )
    layout.add_connection("connection:crypthall_secretdoor", "region:crypt_hall", "region:crypt_secret_door",
                          role="doorway", gated=True, a1=P(40, 56), a2=P(40, 60), min_width=1536)
    layout.add_connection("connection:secretdoor_niche", "region:crypt_secret_door", "region:crypt_secret_niche",
                          role="doorway", gated=True, a1=P(42, 56), a2=P(42, 60), min_width=1536)

    # ---- gallery: stair up from the courtyard's east wall ------------------
    previous = "region:courtyard"
    previous_edge = P(52, 20), P(52, 24)
    for step in range(1, 6):
        region = f"region:gallery_stair_{step}"
        x0, x1 = 50 + 2 * step, 52 + 2 * step
        layout.add_region(
            region, R(x0, 20, x1, 24), role="stair",
            ceiling_z=COURT - step * GAL_STEP - 4 * PH, floor_z=COURT - step * GAL_STEP,
            **EXT,
            intent={"purpose": f"gallery stair step {step}", "classification": "MANDATORY"},
        )
        layout.add_connection(f"connection:gallery_step_{step}", previous, region,
                              a1=previous_edge[0], a2=previous_edge[1], min_width=1536)
        previous, previous_edge = region, (P(x1, 20), P(x1, 24))

    layout.add_region(
        "region:gallery", R(62, 10, 76, 38), role="upper", **INT,
        ceiling_z=GALLERY_CEIL, floor_z=GALLERY_FLOOR,
        intent={"purpose": "upper service gallery", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:gallerystair_gallery", previous, "region:gallery",
                          a1=P(62, 20), a2=P(62, 24), min_width=1536)

    # ---- loop: gallery back down to the courtyard's north-east corner ------
    previous = "region:gallery"
    previous_edge = P(62, 34), P(62, 38)
    for step in range(1, 6):
        region = f"region:loop_stair_{step}"
        x0, x1 = 62 - 2 * step, 64 - 2 * step
        layout.add_region(
            region, R(x0, 34, x1, 38), role="stair",
            ceiling_z=GALLERY_FLOOR + step * GAL_STEP - 4 * PH,
            floor_z=GALLERY_FLOOR + step * GAL_STEP, **EXT,
            intent={"purpose": f"loop stair step {step}", "classification": "MANDATORY"},
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
        wall_picnum=KEYED_FACE, floor_picnum=KEYED_FACE, ceiling_picnum=KEYED_FACE,
        wall_shade=16, floor_shade=16, ceiling_shade=16,
        sector_behavior=_z_door(GALLERY_FLOOR, EXIT_CEIL, interaction="direct", key=1),
        intent={"purpose": "skull-keyed exit gate", "classification": "MANDATORY",
                "interaction": "direct_use"},
    )
    layout.add_region(
        "region:exit_hall", R(78, 18, 88, 30), role="exit", declared_zero_exit=True, **INT,
        ceiling_z=EXIT_CEIL, floor_z=GALLERY_FLOOR,
        intent={"purpose": "exit chamber", "classification": "MANDATORY"},
    )
    layout.add_connection("connection:gallery_exitdoor", "region:gallery", "region:exit_door",
                          role="doorway", gated=True, a1=P(76, 22), a2=P(76, 26),
                          face_picnum=KEYED_FACE, min_width=1536)
    layout.add_connection("connection:exitdoor_hall", "region:exit_door", "region:exit_hall",
                          role="doorway", gated=True, a1=P(78, 22), a2=P(78, 26),
                          face_picnum=KEYED_FACE, min_width=1536)

    # ---- the minimum population a blockout needs ---------------------------
    start = P(-2, 22)
    layout.set_player_start("region:ledge", x=start[0], y=start[1], z=COURT - 1024, angle=0)
    layout.add_sprite("sp_start", "region:ledge", x=start[0], y=start[1], z=COURT - 1024,
                      **sprite_appearance(1, angle=0), behavior={"state": 1})

    layout.place_on_wall(
        "sw_crypt_gate", "region:chapel_nave", a1=P(42, 14), a2=P(42, 32), t=0.5,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET, **SWITCH,
        behavior={"tx_id": CH_CRYPT_GATE, "command": 1, "trigger_on": 1,
                  "trigger_push": 1, "data_1": 203},
    )
    layout.place_on_wall(
        # Wall direction follows the region loop: the y=62 edge runs east to west.
        "sw_secret", "region:crypt_hall", a1=P(40, 62), a2=P(24, 62), t=0.15,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET, **SWITCH,
        behavior={"tx_id": CH_SECRET, "command": 1, "trigger_on": 1,
                  "trigger_push": 1, "data_1": 203},
    )
    layout.place_on_wall(
        "sw_exit", "region:exit_hall", a1=P(88, 18), a2=P(88, 30), t=0.5,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET, **SWITCH,
        behavior={"tx_id": CH_EXIT, "command": 1, "trigger_on": 1, "trigger_push": 1},
    )
    layout.place_on_floor("key_skull", "region:crypt_key_niche", local=(0.5, 0.5),
                          **sprite_appearance(100), behavior={"state": 1})
    return layout


# ---------------------------------------------------------------------------
# Declared intent.  Everything below is what the author MEANT; the evaluation
# packet keeps it strictly out of its observation sections.
# ---------------------------------------------------------------------------

CRYPT_STAIRS = tuple(f"region:crypt_stair_{n}" for n in range(1, 7))
GALLERY_STAIRS = tuple(f"region:gallery_stair_{n}" for n in range(1, 6))
LOOP_STAIRS = tuple(f"region:loop_stair_{n}" for n in range(1, 6))

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
                "a covered ledge and a tight gate tunnel that withhold the courtyard",
                ("region:ledge", "region:gate_tunnel"),
                material_vocabulary={"wall": 2490, "floor": 2448, "ceiling": 2500},
            ),
            AuthoredAssembly(
                "assembly:courtyard", "arrival courtyard", "exterior_parent",
                "the large open cliffside courtyard that contains the chapel and the garden bed",
                ("region:courtyard", "region:garden_bed"),
                material_vocabulary={"wall": 2490, "floor": 2448, "ceiling": 2500},
                landmarks=("the chapel mass standing in the middle of the courtyard",),
            ),
            AuthoredAssembly(
                "assembly:chapel", "chapel", "embedded_building",
                "a tall brick chapel embedded in the courtyard, holding the crypt-gate switch",
                ("region:chapel_door", "region:chapel_nave"),
                parent_assembly="assembly:courtyard",
                material_vocabulary={"wall": 5, "floor": 294, "ceiling": 416},
            ),
            AuthoredAssembly(
                "assembly:crypt", "lower crypt", "lower_interior",
                "a low, dark, monomaterial crypt reached by a long descending stair",
                ("region:crypt_gate", *CRYPT_STAIRS, "region:crypt_hall", "region:crypt_key_niche"),
                material_vocabulary={"wall": 1097, "floor": 1097, "ceiling": 1097},
            ),
            AuthoredAssembly(
                "assembly:ossuary", "optional ossuary", "optional_side_space",
                "an optional room behind a hidden panel in the crypt",
                ("region:crypt_secret_door", "region:crypt_secret_niche"),
                parent_assembly="assembly:crypt", optional=True, mandatory=False,
            ),
            AuthoredAssembly(
                "assembly:gallery", "upper gallery", "upper_interior",
                "an elevated service gallery reached from the courtyard and looping back to it",
                ("region:gallery", *GALLERY_STAIRS, *LOOP_STAIRS),
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
                "transition:reveal", "gate tunnel into the courtyard",
                "region:gate_tunnel", "region:courtyard", "constrained_to_open",
                "the tight low tunnel should release into the tall open courtyard",
                connection_id="connection:tunnel_courtyard",
                expectation={"area_ratio_at_least": 8, "clear_height_gain_at_least": 10 * PH},
            ),
            AuthoredTransition(
                "transition:descent", "courtyard down into the crypt",
                "region:courtyard", "region:crypt_hall", "vertical_descent",
                "a long stair down into a low dark space",
                connection_id="connection:courtyard_cryptgate",
                expectation={"floor_gain_at_least": 6 * CRYPT_STEP},
            ),
            AuthoredTransition(
                "transition:ascent", "courtyard up into the gallery",
                "region:courtyard", "region:gallery", "vertical_ascent",
                "a stair up to an elevated interior that overlooks the approach",
                connection_id="connection:gallery_step_1",
                expectation={"floor_gain_at_least": 5 * GAL_STEP},
            ),
            AuthoredTransition(
                "transition:chapel_entry", "courtyard into the chapel",
                "region:courtyard", "region:chapel_nave", "enclosure",
                "stepping from open sky into a tall enclosed interior",
                connection_id="connection:courtyard_chapeldoor",
            ),
        ),
        progression=(
            {"step": 1, "action": "arrive on the ledge and pass the gate tunnel"},
            {"step": 2, "action": "cross the courtyard and enter the chapel"},
            {"step": 3, "action": "use the nave switch to open the crypt gate",
             "channel": CH_CRYPT_GATE},
            {"step": 4, "action": "descend the crypt stair and take the skull key"},
            {"step": 5, "action": "climb the gallery stair from the courtyard"},
            {"step": 6, "action": "unlock the keyed exit gate and use the exit switch",
             "channel": CH_EXIT},
            {"step": "optional", "action": "open the ossuary panel", "channel": CH_SECRET},
        ),
        landmarks=(
            {"landmark": "chapel mass", "regions": ["region:chapel_nave"],
             "claim": "the chapel should be the visual centre of the courtyard"},
        ),
        optional_regions=("region:crypt_secret_door", "region:crypt_secret_niche",
                          "region:garden_bed"),
        loops=(
            {"loop": "courtyard -> gallery stair -> gallery -> loop stair -> courtyard",
             "claim": "the gallery returns the player to the courtyard by a second route"},
        ),
        material_vocabulary={
            "note": "blockout uses two coarse sets plus the crypt monomaterial",
            "exterior": EXT, "interior": INT, "crypt": CRYPT_MAT,
        },
    )


ALL_CONNECTIONS = (
    "connection:ledge_tunnel", "connection:tunnel_courtyard",
    "connection:bed_south", "connection:bed_east", "connection:bed_north", "connection:bed_west",
    "connection:courtyard_chapeldoor", "connection:chapeldoor_nave",
    "connection:courtyard_cryptgate",
    *(f"connection:crypt_step_{n}" for n in range(1, 7)),
    "connection:cryptstair_hall", "connection:crypthall_keyniche",
    "connection:crypthall_secretdoor", "connection:secretdoor_niche",
    *(f"connection:gallery_step_{n}" for n in range(1, 6)),
    "connection:gallerystair_gallery",
    *(f"connection:loop_step_{n}" for n in range(1, 6)),
    "connection:loop_courtyard",
    "connection:gallery_exitdoor", "connection:exitdoor_hall",
)

# Everything except the ossuary panel and its room.
OPEN_EXCEPT_SECRET = tuple(
    name for name in ALL_CONNECTIONS
    if name not in {"connection:crypthall_secretdoor", "connection:secretdoor_niche"}
)


def probes() -> tuple[ProbeRequest, ...]:
    return (
        ProbeRequest(
            "probe:reach_chapel", "access",
            "can the chapel nave be reached from the start?",
            "the chapel is mandatory and holds the crypt-gate switch",
            target_region="region:chapel_nave",
            opened_connections=("connection:courtyard_chapeldoor", "connection:chapeldoor_nave"),
        ),
        ProbeRequest(
            "probe:reach_crypt", "access",
            "can the crypt hall be reached once the crypt gate is open?",
            "the crypt holds the key the exit needs",
            target_region="region:crypt_hall",
            opened_connections=("connection:courtyard_cryptgate",),
        ),
        ProbeRequest(
            "probe:route_start_to_exit", "route",
            "what route runs from the start to the exit chamber?",
            "the brief needs a coherent start-to-exit spine",
            target_region="region:exit_hall",
            opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:route_through_hierarchy", "visibility",
            "where along the start-to-exit route does the chapel first become adjacent?",
            "the chapel should be met early, not stumbled on at the end",
            target_region="region:chapel_nave",
            opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:reveal_contrast", "transition",
            "does the gate tunnel to courtyard step produce measurable spatial release?",
            "the brief asks for one composed constrained-to-open transition",
            source_region="region:gate_tunnel", destination_region="region:courtyard",
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
            "probe:ossuary_optional", "access",
            "is the ossuary unreachable while its panel stays shut?",
            "optional means gated, not accidentally disconnected",
            target_region="region:crypt_secret_niche",
            opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:gallery_choices", "escape",
            "how many onward routes leave the gallery?",
            (
                "the brief asks for one real spatial loop; two independent downward "
                "routes out of the gallery is the observable part of that claim"
            ),
            start_region="region:gallery",
            opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:revisit_after_crypt_gate", "revisit",
            "what does the nave switch actually open?",
            "the gate must add the crypt and nothing else",
            target_region="region:crypt_hall",
            opened_connections=("connection:courtyard_chapeldoor", "connection:chapeldoor_nave"),
            alt_opened_connections=(
                "connection:courtyard_chapeldoor", "connection:chapeldoor_nave",
                "connection:courtyard_cryptgate",
            ),
        ),
        ProbeRequest(
            "probe:courtyard_choices", "escape",
            "how many onward choices does the courtyard offer?",
            "a hub parent space should branch, not funnel",
            start_region="region:courtyard",
            opened_connections=OPEN_EXCEPT_SECRET,
        ),
        ProbeRequest(
            "probe:tunnel_choices", "escape",
            "how many onward choices does the gate tunnel offer?",
            "the approach should be the narrowest decision point of the level",
            start_region="region:gate_tunnel",
            opened_connections=OPEN_EXCEPT_SECRET,
        ),
    )


def viewpoints() -> tuple[ViewpointSpec, ...]:
    return (
        ViewpointSpec("view:start", "player_start", "region:ledge",
                      *P(-2, 22), COURT - 1024, 0,
                      note="the arrival pose the player actually spawns in"),
        ViewpointSpec("view:gate_approach", "transition_approach", "region:gate_tunnel",
                      *P(5, 22), COURT - 1024, 0,
                      note="inside the constrained tunnel, facing the courtyard"),
        ViewpointSpec("view:courtyard_center", "assembly_center", "region:courtyard",
                      *P(17, 22), COURT - 1024, 0,
                      note="standing in the west courtyard, facing the chapel mass"),
        ViewpointSpec("view:chapel_interior", "assembly_center", "region:chapel_nave",
                      *P(30, 23), COURT - 1024, 0,
                      note="just inside the chapel, facing the switch wall"),
        ViewpointSpec("view:crypt_hall", "assembly_center", "region:crypt_hall",
                      *P(32, 58), CRYPT_FLOOR - 1024, 1536,
                      note="the crypt hall, facing the reliquary niche"),
        ViewpointSpec("view:gallery", "assembly_center", "region:gallery",
                      *P(68, 24), GALLERY_FLOOR - 1024, 1024,
                      note="the upper gallery, facing back down the stair"),
        ViewpointSpec("view:courtyard_from_stair", "vertical_relationship", "region:gallery_stair_3",
                      *P(57, 22), COURT - 3 * GAL_STEP - 1024, 1024,
                      note="mid-ascent, showing the courtyard below and behind"),
        ViewpointSpec("view:chapel_reverse", "reverse_view", "region:courtyard",
                      *P(46, 23), COURT - 1024, 1024,
                      note="east of the chapel, looking back across the courtyard"),
    )


def candidate() -> Candidate:
    return Candidate(
        iteration_id="v0",
        module="projects/reasoned-authoring-v1/level/candidate_v0.py",
        factory=make_layout,
        intent=intent(),
        probes=probes(),
        viewpoints=viewpoints(),
        parent=None,
        declared_changes=("initial blockout: hierarchy, containment, connectivity, scale, spine",),
    )
