"""Independent Blood single-player map: progression first, then topology.

Geometry is invented from an abstract SP design contract derived from E2M2
understanding. It does not copy E2M2 vertices. BB3 informs vertical deltas
only (crypt down, gallery up), not deathmatch logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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

U = 384
PH = 0x1600
STEP = PH // 2  # 0.5 player-heights; under Blood max_step 4096
FLOOR = 8192
CEIL_COVERED = FLOOR - 5 * PH
CRYPT_FLOOR = FLOOR + 2 * STEP
CRYPT_STEP_FLOOR = FLOOR + STEP
GALLERY_FLOOR = FLOOR - 4 * STEP
CEIL_GALLERY = GALLERY_FLOOR - 7 * PH
SWITCH_HEIGHT = 2.18
SWITCH_OFFSET = 0.12

DESIGN_PROGRAM = [
    {
        "phase": "A",
        "intent": "covered start; closed exit visible ahead; open side branch",
        "regions": ["start"],
    },
    {
        "phase": "B",
        "intent": "required lower crypt branch yields the skull key",
        "regions": ["crypt_step", "crypt"],
    },
    {
        "phase": "C",
        "intent": "key opens the archive; wall switch raises the stair gate",
        "regions": ["keyed_door", "archive", "stair1", "stair2", "stair3", "stair4"],
    },
    {
        "phase": "D",
        "intent": "taller upper gallery; different palette; overlook-scale height",
        "regions": ["gallery_door", "gallery"],
    },
    {
        "phase": "E",
        "intent": "gallery switch opens the start-side exit; optional secret",
        "regions": ["exit_door", "exit", "secret_door", "secret"],
    },
]

STATE_GRAPH = {
    "S0": {"reachable": ["start", "crypt_step", "crypt"], "action": "take skull key"},
    "S1": {"reachable": ["start", "crypt_step", "crypt"], "action": "unlock keyed door"},
    "S2": {
        "reachable": ["archive", "stair1", "stair2", "stair3", "stair4"],
        "action": "activate archive switch (channel 100)",
    },
    "S3": {"reachable": ["gallery"], "action": "activate gallery switch (channel 101)"},
    "S4": {"reachable": ["exit"], "action": "activate exit switch (channel 4)"},
    "optional": {"action": "activate secret switch (channel 102)", "reachable": ["secret"]},
}


def P(x: float, y: float) -> tuple[int, int]:
    return (int(round(x * U)), int(round(y * U)))


def R(x0: float, y0: float, x1: float, y1: float) -> list[tuple[int, int]]:
    return [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)]


def _closed_door(floor_z: int, open_ceil: int, *, rx: int | None = None, key: int | None = None) -> dict[str, Any]:
    behavior: dict[str, int] = {
        "busy_time_a": 5, "busy_time_b": 5,
        "off_ceiling_z": floor_z, "on_ceiling_z": open_ceil,
        "off_floor_z": floor_z, "on_floor_z": floor_z,
    }
    if rx is not None:
        behavior["rx_id"] = int(rx)
    if key is not None:
        behavior["key"] = int(key)
        behavior["trigger_push"] = 1
    return behavior


def make_layout() -> PlanarLayout:
    layout = PlanarLayout(name="SP-progression-v1", visibility=800)
    start_mat = dict(
        ceiling_z=CEIL_COVERED, floor_z=FLOOR,
        ceiling_picnum=385, floor_picnum=292, wall_picnum=180,
        floor_shade=18, wall_shade=12, ceiling_shade=8,
    )
    crypt_mat = dict(
        ceiling_z=CRYPT_FLOOR - 4 * PH, floor_z=CRYPT_FLOOR,
        ceiling_picnum=416, floor_picnum=270, wall_picnum=110,
        floor_shade=28, wall_shade=24, ceiling_shade=16,
    )
    archive_mat = dict(
        ceiling_z=CEIL_COVERED, floor_z=FLOOR,
        ceiling_picnum=416, floor_picnum=2448, wall_picnum=5,
        floor_shade=16, wall_shade=8, ceiling_shade=6,
    )
    gallery_mat = dict(
        ceiling_z=CEIL_GALLERY, floor_z=GALLERY_FLOOR,
        ceiling_picnum=385, floor_picnum=278, wall_picnum=184,
        floor_shade=8, wall_shade=4, ceiling_shade=0,
    )
    exit_mat = dict(
        ceiling_z=CEIL_COVERED - PH, floor_z=FLOOR,
        ceiling_picnum=385, floor_picnum=294, wall_picnum=181,
        floor_shade=10, wall_shade=6, ceiling_shade=2,
    )
    secret_mat = dict(
        ceiling_z=CEIL_GALLERY + PH, floor_z=GALLERY_FLOOR,
        ceiling_picnum=416, floor_picnum=270, wall_picnum=110,
        floor_shade=32, wall_shade=28, ceiling_shade=20,
    )
    stair_mat = dict(
        ceiling_z=CEIL_GALLERY, ceiling_picnum=385, floor_picnum=2448, wall_picnum=5,
        floor_shade=14, wall_shade=10, ceiling_shade=4, role="stair",
    )

    layout.add_region("region:start", R(4, 0, 24, 16), role="start", **start_mat)
    layout.add_region("region:crypt_step", R(24, 5, 26, 11), role="stair",
                      ceiling_z=CEIL_COVERED, floor_z=CRYPT_STEP_FLOOR,
                      ceiling_picnum=416, floor_picnum=270, wall_picnum=110,
                      floor_shade=24, wall_shade=20, ceiling_shade=12)
    layout.add_region("region:crypt", R(26, 3, 40, 13), role="key_branch", **crypt_mat)
    layout.add_connection("connection:start_step", "region:start", "region:crypt_step", a1=P(24, 5), a2=P(24, 11))
    layout.add_connection("connection:step_crypt", "region:crypt_step", "region:crypt", a1=P(26, 5), a2=P(26, 11))

    layout.add_region(
        "region:keyed_door", R(10, -2, 18, 0),
        ceiling_z=FLOOR, floor_z=FLOOR, type=600, role="doorway",
        ceiling_picnum=104, floor_picnum=104, wall_picnum=104,
        sector_behavior=_closed_door(FLOOR, CEIL_COVERED, key=1),
    )
    layout.add_region("region:archive", R(8, -14, 20, -2), role="machine", **archive_mat)
    layout.add_connection(
        "connection:start_keyed", "region:start", "region:keyed_door",
        role="doorway", gated=True, a1=P(10, 0), a2=P(18, 0),
    )
    layout.add_connection(
        "connection:keyed_archive", "region:keyed_door", "region:archive",
        role="doorway", gated=True, a1=P(10, -2), a2=P(18, -2),
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
        "region:gallery_door", R(10, -24, 18, -22),
        ceiling_z=GALLERY_FLOOR, floor_z=GALLERY_FLOOR, type=600, role="doorway",
        ceiling_picnum=104, floor_picnum=104, wall_picnum=104,
        sector_behavior=_closed_door(GALLERY_FLOOR, CEIL_GALLERY, rx=100),
    )
    layout.add_region("region:gallery", R(4, -38, 22, -24), role="upper", declared_zero_exit=True, **gallery_mat)
    layout.add_connection(
        "connection:stair4_gdoor", "region:stair4", "region:gallery_door",
        role="doorway", gated=True, a1=P(10, -22), a2=P(18, -22),
    )
    layout.add_connection(
        "connection:gdoor_gallery", "region:gallery_door", "region:gallery",
        role="doorway", gated=True, a1=P(10, -24), a2=P(18, -24),
    )

    layout.add_region(
        "region:secret_door", R(22, -34, 24, -28),
        ceiling_z=GALLERY_FLOOR, floor_z=GALLERY_FLOOR, type=600, role="doorway",
        ceiling_picnum=104, floor_picnum=104, wall_picnum=104,
        sector_behavior=_closed_door(GALLERY_FLOOR, CEIL_GALLERY + PH, rx=102),
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
        "region:exit_door", R(12, 16, 20, 18),
        ceiling_z=FLOOR, floor_z=FLOOR, type=600, role="doorway",
        ceiling_picnum=104, floor_picnum=104, wall_picnum=104,
        sector_behavior=_closed_door(FLOOR, CEIL_COVERED - PH, rx=101),
    )
    layout.add_region("region:exit", R(8, 18, 24, 32), role="exit", declared_zero_exit=True, **exit_mat)
    layout.add_connection(
        "connection:start_exitdoor", "region:start", "region:exit_door",
        role="doorway", gated=True, a1=P(12, 16), a2=P(20, 16),
    )
    layout.add_connection(
        "connection:exitdoor_exit", "region:exit_door", "region:exit",
        role="doorway", gated=True, a1=P(12, 18), a2=P(20, 18),
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
    gates = {
        "exit_after_intended": bool(full["exit_reachable"]),
        "exit_without_key": bool(no_key["exit_reachable"]),
        "exit_without_archive_switch": bool(no_100["exit_reachable"]),
        "exit_without_gallery_switch": bool(no_101["exit_reachable"]),
        "exit_without_secret_switch": bool(no_secret["exit_reachable"]),
        "rest_smaller_than_final": full["physical_reachable_at_rest"] < full["final_reachable"],
        "attachments_ok": attachments["ok"],
        "use_poses_ok": poses["ok"],
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
    }


def write_sp_progression_v1(
    map_path: str | Path = "work/SP-progression-v1.MAP",
    report_path: str | Path = "reports/SP-progression-v1-build.json",
) -> CompiledLayout:
    layout = make_layout()
    compiled = layout.compile()
    first = encode_map(compiled.level.to_disk_map())
    second = encode_map(make_layout().compile().level.to_disk_map())
    if first != second:
        raise RuntimeError("SP-progression-v1 is not byte-identical across compiles")
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
    native_ok = audit["native_validation_errors"] == 0
    authored = authored_geometry_report(diagnostics)
    report = {
        "$schema": "llmapper.sp-progression-v1-build",
        "schema_version": 1,
        "map": str(map_path),
        "deterministic": True,
        "bytes": len(first),
        "design_program": DESIGN_PROGRAM,
        "state_graph": STATE_GRAPH,
        "conservation": compiled.conservation.to_dict(),
        "authored": authored,
        "audit_error_conflicts": audit["counts"]["error_conflicts"],
        "native_validation_errors": audit["native_validation_errors"],
        "progression": progression,
        "source_hidden": ["maps/blood/E2M2.MAP", "maps/blood/BB3.MAP"],
        "acceptance": {
            "strict_authored_geometry": authored["errors"] == 0,
            "native_validation": native_ok,
            "progression_ok": progression["gates"]["ok"],
            "object_attachment_violations": len(progression["attachments"]["violations"]),
        },
        "nblood_load": "work/nblood-sp-v1-report.json",
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return compiled


if __name__ == "__main__":
    compiled = write_sp_progression_v1()
    print(
        f"sp-v1: {len(compiled.level.sectors)} sectors, {len(compiled.level.walls)} walls, "
        f"{len(compiled.level.sprites)} sprites, conserved={compiled.conservation.conserved}"
    )
