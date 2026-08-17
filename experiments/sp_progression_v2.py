"""Persistent SP test level v2: native door interaction and visual language.

Continues work/SP-progression-v1.MAP. Geometry stays invented; door realizations
are chosen from campaign precedents (not a make_door prefab).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bloodmap.doors import (
    authored_gate_audit,
    door_affordance_report,
    gate_audit_markdown,
    xsector_direct_use,
    xsector_remote_rx,
    z_motion_endpoints,
)
from bloodmap.format import encode_map, write_map
from bloodmap.geometry_audit import (
    audit_geometry,
    authored_geometry_report,
    validate_authored_level,
)
from bloodmap.item_display import sprite_appearance
from bloodmap.placement import validate_attachments, validate_use_poses
from bloodmap.planar_layout import CompiledLayout, PlanarLayout
from bloodmap.progression import analyze_progression
from experiments.sp_progression_v1 import (
    CEIL_COVERED,
    CEIL_GALLERY,
    CRYPT_FLOOR,
    CRYPT_STEP_FLOOR,
    FLOOR,
    GALLERY_FLOOR,
    PH,
    STEP,
    SWITCH_HEIGHT,
    SWITCH_OFFSET,
    U,
    P,
    R,
)

# Campaign-mined approach faces (blood-door-families.json).
FACE_ORDINARY = 22    # common closed wall_push Z-ceiling face (E3M1 and others)
FACE_KEYED = 495      # E3M3/E3M4 skull-key direct-use doors
FACE_REMOTE = 200     # modal closed remote Z-ceiling approach
FACE_EXIT = 345       # second closed remote Z-ceiling approach
# Wall-aligned type-0 decoration; 20/21 keyed skull occurrences across 15 maps.
SKULL_EMBLEM = dict(type=0, picnum=2540, cstat=464, x_repeat=32, y_repeat=32, shade=-4)

DESIGN_PROGRAM = [
    {
        "phase": "A",
        "intent": "covered start; closed exit door visible ahead; crypt mouth is a usable door",
        "regions": ["start"],
    },
    {
        "phase": "B",
        "intent": "direct-use crypt door; key in the lower crypt; scenic courtyard visible, not reachable",
        "regions": ["crypt_door", "crypt_step", "crypt", "crypt_view"],
    },
    {
        "phase": "C",
        "intent": "skull-keyed direct-use archive gate with emblem; archive switch raises gallery door",
        "regions": ["keyed_door", "archive", "stair1", "stair2", "stair3", "stair4"],
    },
    {
        "phase": "D",
        "intent": "remote gallery door; taller upper gallery",
        "regions": ["gallery_door", "gallery"],
    },
    {
        "phase": "E",
        "intent": "remote exit door; optional hidden secret panel",
        "regions": ["exit_door", "exit", "secret_door", "secret"],
    },
]

STATE_GRAPH = {
    "S0": {"reachable": ["start"], "action": "use crypt mouth door"},
    "S1": {"reachable": ["start", "crypt_step", "crypt"], "action": "take skull key"},
    "S2": {"reachable": ["start", "crypt_step", "crypt"], "action": "use keyed archive door"},
    "S3": {
        "reachable": ["archive", "stair1", "stair2", "stair3", "stair4"],
        "action": "activate archive switch (channel 100)",
    },
    "S4": {"reachable": ["gallery"], "action": "activate gallery switch (channel 101)"},
    "S5": {"reachable": ["exit"], "action": "activate exit switch (channel 4)"},
    "optional": {"action": "activate secret switch (channel 102)", "reachable": ["secret"]},
    "scenic": {"reachable": [], "note": "crypt_view is INTENTIONALLY_UNREACHABLE"},
}


def _z_door(floor_z: int, open_ceil: int, *, interaction: str, rx: int | None = None, key: int | None = None) -> dict[str, int]:
    behavior = {"busy_time_a": 5, "busy_time_b": 5, **z_motion_endpoints(floor_z, open_ceil)}
    if interaction == "direct":
        behavior.update(xsector_direct_use(key=key))
    elif interaction == "remote":
        if rx is None:
            raise ValueError("remote door requires rx")
        behavior.update(xsector_remote_rx(rx))
    else:
        raise ValueError(interaction)
    return behavior


def make_layout() -> PlanarLayout:
    layout = PlanarLayout(name="SP-progression-v2", visibility=800)
    start_mat = dict(
        ceiling_z=CEIL_COVERED, floor_z=FLOOR,
        ceiling_picnum=385, floor_picnum=292, wall_picnum=180,
        floor_shade=18, wall_shade=12, ceiling_shade=8,
        intent={"purpose": "start hall", "classification": "MANDATORY", "player_reachable": True},
    )
    crypt_mat = dict(
        ceiling_z=CRYPT_FLOOR - 4 * PH, floor_z=CRYPT_FLOOR,
        ceiling_picnum=416, floor_picnum=270, wall_picnum=110,
        floor_shade=28, wall_shade=24, ceiling_shade=16,
        intent={"purpose": "key chamber", "classification": "STATE_DEPENDENT", "player_reachable_after": "crypt_door"},
    )
    archive_mat = dict(
        ceiling_z=CEIL_COVERED, floor_z=FLOOR,
        ceiling_picnum=416, floor_picnum=2448, wall_picnum=5,
        floor_shade=16, wall_shade=8, ceiling_shade=6,
        intent={"purpose": "machine room", "classification": "STATE_DEPENDENT", "player_reachable_after": "keyed_door"},
    )
    gallery_mat = dict(
        ceiling_z=CEIL_GALLERY, floor_z=GALLERY_FLOOR,
        ceiling_picnum=385, floor_picnum=278, wall_picnum=184,
        floor_shade=8, wall_shade=4, ceiling_shade=0,
        intent={"purpose": "upper gallery", "classification": "STATE_DEPENDENT", "player_reachable_after": "switch:archive"},
    )
    exit_mat = dict(
        ceiling_z=CEIL_COVERED - PH, floor_z=FLOOR,
        ceiling_picnum=385, floor_picnum=294, wall_picnum=181,
        floor_shade=10, wall_shade=6, ceiling_shade=2,
        intent={"purpose": "exit chamber", "classification": "STATE_DEPENDENT", "player_reachable_after": "switch:gallery"},
    )
    secret_mat = dict(
        ceiling_z=CEIL_GALLERY + PH, floor_z=GALLERY_FLOOR,
        ceiling_picnum=416, floor_picnum=270, wall_picnum=110,
        floor_shade=32, wall_shade=28, ceiling_shade=20,
        intent={"purpose": "optional secret", "classification": "OPTIONAL", "player_reachable_after": "switch:secret"},
    )
    stair_mat = dict(
        ceiling_z=CEIL_GALLERY, ceiling_picnum=385, floor_picnum=2448, wall_picnum=5,
        floor_shade=14, wall_shade=10, ceiling_shade=4, role="stair",
        intent={"purpose": "stair run", "classification": "STATE_DEPENDENT"},
    )

    layout.add_region("region:start", R(4, 0, 24, 16), role="start", **start_mat)

    layout.add_region("region:crypt_step", R(24, 5, 26, 11), role="stair",
                      ceiling_z=CEIL_COVERED, floor_z=CRYPT_STEP_FLOOR,
                      ceiling_picnum=416, floor_picnum=270, wall_picnum=110,
                      floor_shade=24, wall_shade=20, ceiling_shade=12,
                      intent={"purpose": "crypt stair", "classification": "MANDATORY"})
    layout.add_region(
        "region:crypt_door", R(26, 7, 28, 9),
        ceiling_z=CRYPT_STEP_FLOOR, floor_z=CRYPT_STEP_FLOOR, type=600, role="doorway",
        ceiling_picnum=FACE_ORDINARY, floor_picnum=FACE_ORDINARY, wall_picnum=FACE_ORDINARY,
        sector_behavior=_z_door(CRYPT_STEP_FLOOR, CRYPT_FLOOR - 4 * PH, interaction="direct"),
        intent={
            "purpose": "crypt mouth",
            "classification": "MANDATORY",
            "interaction": "direct_use",
            "realization": "campaign wall_push Z-ceiling, face 22",
        },
    )
    layout.add_region("region:crypt", R(28, 3, 42, 13), role="key_branch", declared_zero_exit=True, **crypt_mat)
    layout.add_connection("connection:start_step", "region:start", "region:crypt_step", a1=P(24, 5), a2=P(24, 11))
    layout.add_connection(
        "connection:step_cryptdoor", "region:crypt_step", "region:crypt_door",
        role="doorway", gated=True, a1=P(26, 7), a2=P(26, 9), face_picnum=FACE_ORDINARY,
    )
    layout.add_connection(
        "connection:cryptdoor_crypt", "region:crypt_door", "region:crypt",
        role="doorway", gated=True, a1=P(28, 7), a2=P(28, 9), face_picnum=FACE_ORDINARY,
    )

    layout.add_region(
        "region:crypt_view", R(42, 4, 54, 12),
        ceiling_z=CRYPT_FLOOR - 6 * PH, floor_z=CRYPT_FLOOR + PH,
        ceiling_picnum=385, floor_picnum=294, wall_picnum=181,
        floor_shade=40, wall_shade=32, ceiling_shade=8,
        declared_zero_exit=True, role="scenery",
        intent={
            "purpose": "scenic courtyard seen from crypt",
            "classification": "INTENTIONALLY_UNREACHABLE",
            "player_reachable": False,
            "visible_from": "crypt",
        },
    )
    layout.add_connection(
        "connection:crypt_window", "region:crypt", "region:crypt_view",
        role="window", a1=P(42, 4), a2=P(42, 12), face_cstat=1,
    )

    layout.add_region(
        "region:keyed_door", R(14, -2, 16, 0),
        ceiling_z=FLOOR, floor_z=FLOOR, type=600, role="doorway",
        ceiling_picnum=FACE_KEYED, floor_picnum=FACE_KEYED, wall_picnum=FACE_KEYED,
        sector_behavior=_z_door(FLOOR, CEIL_COVERED, interaction="direct", key=1),
        intent={
            "purpose": "skull-keyed archive gate",
            "classification": "MANDATORY",
            "interaction": "direct_use",
            "realization": "E3M3-style wall_push Z-ceiling, face 495, emblem 2540",
        },
    )
    layout.add_region("region:archive", R(8, -14, 20, -2), role="machine", **archive_mat)
    layout.add_connection(
        "connection:start_keyed", "region:start", "region:keyed_door",
        role="doorway", gated=True, a1=P(14, 0), a2=P(16, 0), face_picnum=FACE_KEYED,
    )
    layout.add_connection(
        "connection:keyed_archive", "region:keyed_door", "region:archive",
        role="doorway", gated=True, a1=P(14, -2), a2=P(16, -2), face_picnum=FACE_KEYED,
    )

    prev = "region:archive"
    ys = [(-16, -14), (-18, -16), (-20, -18), (-22, -20)]
    for index, (y0, y1) in enumerate(ys, start=1):
        rid = f"region:stair{index}"
        layout.add_region(rid, R(10, y0, 18, y1), floor_z=FLOOR - index * STEP, **stair_mat)
        if index == 1:
            layout.add_connection("connection:archive_stair1", prev, rid, a1=P(10, -14), a2=P(18, -14))
        else:
            layout.add_connection(
                f"connection:stair{index-1}_{index}", prev, rid, a1=P(10, y1), a2=P(18, y1),
            )
        prev = rid

    layout.add_region(
        "region:gallery_door", R(13, -24, 15, -22),
        ceiling_z=GALLERY_FLOOR, floor_z=GALLERY_FLOOR, type=600, role="doorway",
        ceiling_picnum=FACE_REMOTE, floor_picnum=FACE_REMOTE, wall_picnum=FACE_REMOTE,
        sector_behavior=_z_door(GALLERY_FLOOR, CEIL_GALLERY, interaction="remote", rx=100),
        intent={
            "purpose": "remote stair-to-gallery door",
            "classification": "MANDATORY",
            "interaction": "remote_switch",
            "realization": "RX 100, no Push/Wallpush, face 200",
        },
    )
    layout.add_region("region:gallery", R(4, -38, 22, -24), role="upper", declared_zero_exit=True, **gallery_mat)
    layout.add_connection(
        "connection:stair4_gdoor", "region:stair4", "region:gallery_door",
        role="doorway", gated=True, a1=P(13, -22), a2=P(15, -22), face_picnum=FACE_REMOTE,
    )
    layout.add_connection(
        "connection:gdoor_gallery", "region:gallery_door", "region:gallery",
        role="doorway", gated=True, a1=P(13, -24), a2=P(15, -24), face_picnum=FACE_REMOTE,
    )

    layout.add_region(
        "region:secret_door", R(22, -34, 24, -28),
        ceiling_z=GALLERY_FLOOR, floor_z=GALLERY_FLOOR, type=600, role="doorway",
        ceiling_picnum=184, floor_picnum=184, wall_picnum=184,
        sector_behavior=_z_door(GALLERY_FLOOR, CEIL_GALLERY + PH, interaction="remote", rx=102),
        intent={
            "purpose": "hidden secret panel",
            "classification": "OPTIONAL",
            "hidden": True,
            "interaction": "remote_switch",
            "realization": "same face as gallery fill; not a visible door",
        },
    )
    layout.add_region("region:secret", R(24, -36, 36, -26), role="secret", declared_zero_exit=True, **secret_mat)
    layout.add_connection(
        "connection:gallery_sdoor", "region:gallery", "region:secret_door",
        role="doorway", gated=True, a1=P(22, -34), a2=P(22, -28),
    )
    layout.add_connection(
        "connection:sdoor_secret", "region:secret_door", "region:secret",
        role="doorway", gated=True, a1=P(24, -34), a2=P(24, -28),
    )

    layout.add_region(
        "region:exit_door", R(14, 16, 16, 18),
        ceiling_z=FLOOR, floor_z=FLOOR, type=600, role="doorway",
        ceiling_picnum=FACE_EXIT, floor_picnum=FACE_EXIT, wall_picnum=FACE_EXIT,
        sector_behavior=_z_door(FLOOR, CEIL_COVERED - PH, interaction="remote", rx=101),
        intent={
            "purpose": "remote exit door",
            "classification": "MANDATORY",
            "interaction": "remote_switch",
            "realization": "RX 101, face 345",
        },
    )
    layout.add_region("region:exit", R(8, 18, 24, 32), role="exit", declared_zero_exit=True, **exit_mat)
    layout.add_connection(
        "connection:start_exitdoor", "region:start", "region:exit_door",
        role="doorway", gated=True, a1=P(14, 16), a2=P(16, 16), face_picnum=FACE_EXIT,
    )
    layout.add_connection(
        "connection:exitdoor_exit", "region:exit_door", "region:exit",
        role="doorway", gated=True, a1=P(14, 18), a2=P(16, 18), face_picnum=FACE_EXIT,
    )

    layout.set_player_start("region:start", x=P(16, 12)[0], y=P(16, 12)[1], z=FLOOR - 1024, angle=512)
    layout.add_sprite(
        "sp_start", "region:start",
        x=P(16, 12)[0], y=P(16, 12)[1], z=FLOOR - 1024,
        **sprite_appearance(1, angle=512),
        behavior={"state": 1},
    )

    switch_kw = dict(type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40, shade=-8)
    layout.place_on_wall(
        "sw_archive", "region:archive",
        a1=P(8, -2), a2=P(8, -14), t=0.55,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
        **switch_kw,
        behavior={"tx_id": 100, "command": 1, "trigger_on": 1, "trigger_push": 1, "data_1": 203},
    )
    layout.place_on_wall(
        "sw_gallery", "region:gallery",
        a1=P(4, -24), a2=P(4, -38), t=0.45,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
        **switch_kw,
        behavior={"tx_id": 101, "command": 1, "trigger_on": 1, "trigger_push": 1, "data_1": 203},
    )
    layout.place_on_wall(
        "sw_secret", "region:gallery",
        a1=P(4, -38), a2=P(22, -38), t=0.88,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
        **switch_kw,
        behavior={"tx_id": 102, "command": 1, "trigger_on": 1, "trigger_push": 1, "data_1": 203},
    )
    layout.place_on_wall(
        "sw_exit", "region:exit",
        a1=P(24, 32), a2=P(8, 32), t=0.5,
        height_player_heights=SWITCH_HEIGHT, offset_player_widths=SWITCH_OFFSET,
        **switch_kw,
        behavior={"tx_id": 4, "command": 1, "trigger_on": 1, "trigger_push": 1},
    )
    layout.place_on_wall(
        "torch_start", "region:start",
        a1=P(4, 16), a2=P(4, 0), t=0.35,
        height_player_heights=0.9, offset_player_widths=0.08,
        **sprite_appearance(30, shade=-8),
    )
    layout.place_on_wall(
        "skull_emblem", "region:start",
        a1=P(4, 0), a2=P(24, 0), t=0.42,
        height_player_heights=2.55, offset_player_widths=0.10,
        **SKULL_EMBLEM,
    )
    layout.place_on_floor("key_skull", "region:crypt", local=(0.55, 0.5), **sprite_appearance(100), behavior={"state": 1})
    layout.place_on_floor("shotgun", "region:start", local=(0.25, 0.35), **sprite_appearance(41), behavior={"state": 1})
    layout.place_on_floor("health_secret", "region:secret", local=(0.5, 0.5), **sprite_appearance(107), behavior={"state": 1})
    layout.place_on_floor("cultist_crypt", "region:crypt", local=(0.35, 0.35), **sprite_appearance(201, angle=1024), behavior={"state": 1})
    layout.place_on_floor("cultist_archive", "region:archive", local=(0.7, 0.55), **sprite_appearance(201, angle=512), behavior={"state": 1})
    return layout


def _gated(compiled: CompiledLayout) -> set[int]:
    return {
        compiled.allocations[key].sector_id
        for key, region in compiled.layout.regions.items()
        if region.type in {600, 602} or region.role in {"doorway", "gated_pocket"}
    }


def evaluate_progression(compiled: CompiledLayout) -> dict[str, Any]:
    disk = compiled.level.to_disk_map()
    full = analyze_progression(disk)
    no_key = analyze_progression(disk, skip_key_ids={1})
    no_100 = analyze_progression(disk, skip_tx_ids={100})
    no_101 = analyze_progression(disk, skip_tx_ids={101})
    no_secret = analyze_progression(disk, skip_tx_ids={102})
    attachments = validate_attachments(disk)
    poses = validate_use_poses(disk)
    affordance = door_affordance_report(compiled)
    gates = {
        "exit_after_intended": bool(full["exit_reachable"]),
        "exit_without_key": bool(no_key["exit_reachable"]),
        "exit_without_archive_switch": bool(no_100["exit_reachable"]),
        "exit_without_gallery_switch": bool(no_101["exit_reachable"]),
        "exit_without_secret_switch": bool(no_secret["exit_reachable"]),
        "rest_smaller_than_final": full["physical_reachable_at_rest"] < full["final_reachable"],
        "attachments_ok": attachments["ok"],
        "use_poses_ok": poses["ok"],
        "door_affordance_ok": affordance["ok"],
    }
    gates["ok"] = (
        gates["exit_after_intended"]
        and not gates["exit_without_key"]
        and not gates["exit_without_archive_switch"]
        and not gates["exit_without_gallery_switch"]
        and gates["exit_without_secret_switch"]
        and gates["rest_smaller_than_final"]
        and gates["attachments_ok"]
        and gates["use_poses_ok"]
        and gates["door_affordance_ok"]
    )
    return {
        "gates": gates,
        "full": {
            "rest": full["physical_reachable_at_rest"],
            "final": full["final_reachable"],
            "exit": full["exit_reachable"],
            "keys": full["keys_collected"],
            "channels": full["channels_activated"],
            "witness": full["witness"],
        },
        "attachments": attachments,
        "use_poses": {"ok": poses["ok"], "violations": poses["violations"], "probe_count": len(poses["probes"])},
        "affordance": affordance,
    }


def write_action_fixture(kind: str, map_path: str | Path) -> CompiledLayout:
    """Pose the player in Use range of one gate. Does not walk or give inventory."""
    layout = make_layout()
    if kind == "ordinary-crypt":
        layout.set_player_start("region:crypt_step", x=P(25, 8)[0], y=P(25, 8)[1], z=CRYPT_STEP_FLOOR - 1024, angle=0)
    elif kind == "keyed-locked":
        layout.set_player_start("region:start", x=P(15, 1)[0], y=P(15, 1)[1], z=FLOOR - 1024, angle=1536)
    elif kind == "archive-switch":
        layout.set_player_start("region:archive", x=P(10, -8)[0], y=P(10, -8)[1], z=FLOOR - 1024, angle=1024)
    else:
        raise ValueError(kind)
    compiled = layout.compile()
    path = Path(map_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_map(compiled.level.to_disk_map(), path)
    return compiled


def write_sp_progression_v2(
    map_path: str | Path = "work/SP-progression-v2.MAP",
    report_path: str | Path = "reports/SP-v2-build.json",
) -> CompiledLayout:
    layout = make_layout()
    compiled = layout.compile()
    first = encode_map(compiled.level.to_disk_map())
    second = encode_map(make_layout().compile().level.to_disk_map())
    if first != second:
        raise RuntimeError("SP-progression-v2 is not byte-identical across compiles")
    map_path = Path(map_path)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    write_map(compiled.level.to_disk_map(), map_path)
    gated = _gated(compiled)
    zero_exit = {
        compiled.allocations[key].sector_id
        for key, region in compiled.layout.regions.items()
        if region.declared_zero_exit
    }
    diagnostics = validate_authored_level(
        compiled.level,
        intended_adjacency=[(item.region_a, item.region_b) for item in compiled.layout.connections.values()],
        gated_sectors=gated,
        declared_zero_exit=zero_exit,
        declared_specials=compiled.declared_specials,
        allocations={key: value.sector_id for key, value in compiled.allocations.items()},
        connection_report=compiled.connection_report,
    )
    audit = audit_geometry(
        compiled.level,
        declared_specials=compiled.declared_specials,
        gated_sectors=gated,
        declared_zero_exit=zero_exit,
    )
    progression = evaluate_progression(compiled)
    gate_audit = authored_gate_audit(compiled)
    native_ok = audit["native_validation_errors"] == 0
    authored = authored_geometry_report(diagnostics)
    report = {
        "$schema": "llmapper.sp-progression-v2-build",
        "schema_version": 1,
        "map": str(map_path),
        "parent": "work/SP-progression-v1.MAP",
        "deterministic": True,
        "bytes": len(first),
        "design_program": DESIGN_PROGRAM,
        "state_graph": STATE_GRAPH,
        "door_choices": {
            "crypt_door": "direct wall_push Z-ceiling, face 22",
            "keyed_door": "direct wall_push skull key, face 495, emblem 2540",
            "gallery_door": "remote RX 100, face 200",
            "exit_door": "remote RX 101, face 345",
            "secret_door": "remote RX 102, hidden same-as-fill",
            "crypt_view": "blocking window, INTENTIONALLY_UNREACHABLE",
        },
        "conservation": compiled.conservation.to_dict(),
        "authored": authored,
        "audit_error_conflicts": audit["counts"]["error_conflicts"],
        "native_validation_errors": audit["native_validation_errors"],
        "progression": progression,
        "gate_audit": gate_audit,
        "source_hidden": ["maps/blood/E2M2.MAP", "maps/blood/BB3.MAP"],
        "acceptance": {
            "strict_authored_geometry": authored["errors"] == 0,
            "native_validation": native_ok,
            "progression_ok": progression["gates"]["ok"],
            "door_affordance": progression["gates"]["door_affordance_ok"],
            "object_attachment_violations": len(progression["attachments"]["violations"]),
        },
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    Path("reports/SP-v2-door-affordance.json").write_text(
        json.dumps(progression["affordance"], indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n",
    )
    Path("reports/SP-v2-door-audit.md").write_text(
        gate_audit_markdown(gate_audit), encoding="utf-8", newline="\n",
    )
    return compiled


if __name__ == "__main__":
    compiled = write_sp_progression_v2()
    print(
        f"sp-v2: {len(compiled.level.sectors)} sectors, {len(compiled.level.walls)} walls, "
        f"{len(compiled.level.sprites)} sprites, conserved={compiled.conservation.conserved}"
    )
    print(gate_audit_markdown(authored_gate_audit(compiled)))
