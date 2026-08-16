"""Inventory of Blood map contents, starts, pickups, and static mechanisms.

This is a reading aid over DiskMap plus the Blood type catalog. It does not
simulate runtime, invent rooms, or replace channel_graph / spatial analysis.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from typing import Any

from .analysis import channel_graph, validate_map
from .blood_types import classify, command_name
from .build_ir import BuildIR
from .design import _ref
from .model import DiskMap, DiskObject
from .player_space import PLAYER_PROFILES
from .sight import line_of_sight, occluding_segments, spawn_sight_report


SCHEMA = "llmapper.map-contents"
SCHEMA_VERSION = 1

_TRIGGER_FLAGS = (
    "trigger_push", "trigger_vector", "trigger_impact", "trigger_pickup",
    "trigger_touch", "trigger_sight", "trigger_proximity", "trigger_enter",
    "trigger_exit", "trigger_wall_push", "trigger_on", "trigger_off",
    "trigger_once", "decoupled",
)

_PICKUP_CATEGORIES = {"weapon", "ammo", "health", "armor", "powerup", "key", "flag"}


def _active_flags(fields: dict[str, Any], names: tuple[str, ...]) -> list[str]:
    return [name for name in names if fields.get(name)]


def _extra_fields(obj: DiskObject) -> dict[str, Any] | None:
    return None if obj.extra is None else dict(obj.extra.fields)


def _sprite_record(index: int, sprite: DiskObject) -> dict[str, Any]:
    typed = classify("sprite", int(sprite.fields["type"]))
    extra = _extra_fields(sprite)
    record = {
        "ref": _ref("sprite", index),
        "type_id": int(sprite.fields["type"]),
        "type_name": typed["name"],
        "category": typed["category"],
        "known": typed["known"],
        "picnum": int(sprite.fields["picnum"]),
        "sector": int(sprite.fields["sector"]),
        "x": int(sprite.fields["x"]),
        "y": int(sprite.fields["y"]),
        "z": int(sprite.fields["z"]),
        "angle": int(sprite.fields["angle"]),
        "status": int(sprite.fields["status"]),
    }
    if extra is not None:
        record["xsprite"] = {
            "state": extra["state"],
            "tx_id": extra["tx_id"],
            "rx_id": extra["rx_id"],
            "command": extra["command"],
            "command_name": command_name(extra["command"]),
            "busy_time": extra["busy_time"],
            "wait_time": extra["wait_time"],
            "data_1": extra["data_1"],
            "data_2": extra["data_2"],
            "data_3": extra["data_3"],
            "data_4": extra["data_4"],
            "triggers": _active_flags(extra, _TRIGGER_FLAGS),
        }
        if typed["type_id"] == 710 or typed["category"] == "sound":
            record["xsprite"]["notes"] = typed.get("notes")
    return record


def _sector_mechanism(index: int, sector: DiskObject) -> dict[str, Any] | None:
    extra = _extra_fields(sector)
    type_id = int(sector.fields["type"])
    typed = classify("sector", type_id)
    if extra is None and type_id == 0:
        return None
    ceiling_stat = int(sector.fields["ceiling_stat"])
    floor_stat = int(sector.fields["floor_stat"])
    record: dict[str, Any] = {
        "ref": _ref("sector", index),
        "type_id": type_id,
        "type_name": typed["name"],
        "category": typed["category"],
        "known": typed["known"],
        "floor_z": int(sector.fields["floor_z"]),
        "ceiling_z": int(sector.fields["ceiling_z"]),
        "floor_picnum": int(sector.fields["floor_picnum"]),
        "ceiling_picnum": int(sector.fields["ceiling_picnum"]),
        "parallax_ceiling": bool(ceiling_stat & 1),
        "parallax_floor": bool(floor_stat & 1),
    }
    if extra is None:
        return record
    off_floor, on_floor = extra["off_floor_z"], extra["on_floor_z"]
    off_ceil, on_ceil = extra["off_ceiling_z"], extra["on_ceiling_z"]
    record["xsector"] = {
        "state": extra["state"],
        "busy": extra["busy"],
        "tx_id": extra["tx_id"],
        "rx_id": extra["rx_id"],
        "command": extra["command"],
        "command_name": command_name(extra["command"]),
        "key": extra["key"],
        "locked": extra["locked"],
        "underwater": extra["underwater"],
        "depth": extra["depth"],
        "wind_always": extra["wind_always"],
        "wind_velocity": extra["wind_velocity"],
        "bob_always": extra["bob_always"],
        "bob_z_range": extra["bob_z_range"],
        "crush": extra["crush"],
        "damage_type": extra["damage_type"],
        "marker_0": extra["marker_0"],
        "marker_1": extra["marker_1"],
        "off_floor_z": off_floor,
        "on_floor_z": on_floor,
        "off_ceiling_z": off_ceil,
        "on_ceiling_z": on_ceil,
        "floor_z_delta": on_floor - off_floor,
        "ceiling_z_delta": on_ceil - off_ceil,
        "busy_time_a": extra["busy_time_a"],
        "wait_time_a": extra["wait_time_a"],
        "busy_time_b": extra["busy_time_b"],
        "wait_time_b": extra["wait_time_b"],
        "triggers": _active_flags(extra, _TRIGGER_FLAGS),
    }
    return record


def _wall_mechanism(index: int, wall: DiskObject) -> dict[str, Any] | None:
    extra = _extra_fields(wall)
    type_id = int(wall.fields["type"])
    typed = classify("wall", type_id)
    if extra is None and type_id == 0:
        return None
    cstat = int(wall.fields["cstat"])
    record: dict[str, Any] = {
        "ref": _ref("wall", index),
        "type_id": type_id,
        "type_name": typed["name"],
        "category": typed["category"],
        "known": typed["known"],
        "picnum": int(wall.fields["picnum"]),
        "over_picnum": int(wall.fields["over_picnum"]),
        "next_sector": int(wall.fields["next_sector"]),
        "cstat": cstat,
        "blocking": bool(cstat & 1),
        "masked": bool(cstat & 16),
        "hitscan_blocking": bool(cstat & 64),
    }
    if extra is None:
        return record
    record["xwall"] = {
        "state": extra["state"],
        "data": extra["data"],
        "tx_id": extra["tx_id"],
        "rx_id": extra["rx_id"],
        "command": extra["command"],
        "command_name": command_name(extra["command"]),
        "key": extra["key"],
        "locked": extra["locked"],
        "busy_time": extra["busy_time"],
        "wait_time": extra["wait_time"],
        "triggers": _active_flags(extra, _TRIGGER_FLAGS),
    }
    return record


def _channel_roles(graph: dict[str, Any]) -> list[dict[str, Any]]:
    roles = []
    for item in graph["channels"]:
        channel = int(item["channel"])
        typed = classify("channel", channel)
        roles.append({
            "channel": channel,
            "name": typed["name"],
            "category": typed["category"],
            "transmitters": item["transmitters"],
            "receivers": item["receivers"],
        })
    return roles


def inventory_map(disk: DiskMap) -> dict[str, Any]:
    """Classify every Blood object that matters for reading a map."""
    diagnostics = validate_map(disk)
    sprites = [_sprite_record(index, sprite) for index, sprite in enumerate(disk.sprites)]
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unknown = []
    for record in sprites:
        by_category[record["category"]].append(record)
        if not record["known"]:
            unknown.append(record)
    type_counts = Counter(int(sprite.fields["type"]) for sprite in disk.sprites)
    sector_type_counts = Counter(int(sector.fields["type"]) for sector in disk.sectors)
    wall_type_counts = Counter(int(wall.fields["type"]) for wall in disk.walls)
    parallax_ceil = sum(1 for sector in disk.sectors if int(sector.fields["ceiling_stat"]) & 1)
    parallax_floor = sum(1 for sector in disk.sectors if int(sector.fields["floor_stat"]) & 1)
    masked = sum(1 for wall in disk.walls if int(wall.fields["cstat"]) & 16)
    blocking = sum(1 for wall in disk.walls if int(wall.fields["cstat"]) & 1)
    portals = sum(1 for wall in disk.walls if int(wall.fields["next_sector"]) >= 0)
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "facts+derived",
        "version": f"0x{disk.version:04x}",
        "player_start_header": {
            "x": disk.header["start_x"],
            "y": disk.header["start_y"],
            "z": disk.header["start_z"],
            "angle": disk.header["start_angle"],
            "sector": disk.header["start_sector"],
        },
        "sky": {
            "sky_bits": disk.header["sky_bits"],
            "sky_type": disk.header["sky_type"],
            "visibility": disk.header["visibility"],
            "sky_offset_count": len(disk.sky_offsets),
        },
        "counts": {
            "sectors": len(disk.sectors),
            "walls": len(disk.walls),
            "sprites": len(disk.sprites),
            "xsectors": sum(obj.extra is not None for obj in disk.sectors),
            "xwalls": sum(obj.extra is not None for obj in disk.walls),
            "xsprites": sum(obj.extra is not None for obj in disk.sprites),
            "portals": portals,
            "masked_walls": masked,
            "blocking_walls": blocking,
            "parallax_ceilings": parallax_ceil,
            "parallax_floors": parallax_floor,
        },
        "validation": {
            "errors": sum(1 for item in diagnostics if item.severity == "error"),
            "warnings": sum(1 for item in diagnostics if item.severity == "warning"),
        },
        "type_counts": {
            "sprites": [
                {**classify("sprite", type_id), "count": count}
                for type_id, count in sorted(type_counts.items())
            ],
            "sectors": [
                {**classify("sector", type_id), "count": count}
                for type_id, count in sorted(sector_type_counts.items())
            ],
            "walls": [
                {**classify("wall", type_id), "count": count}
                for type_id, count in sorted(wall_type_counts.items())
            ],
        },
        "starts": {
            "single_player": [item for item in by_category.get("start", []) if item["type_id"] == 1],
            "multiplayer": [item for item in by_category.get("start", []) if item["type_id"] == 2],
        },
        "pickups": [
            item for item in sprites if item["category"] in _PICKUP_CATEGORIES
        ],
        "switches": by_category.get("switch", []),
        "markers": by_category.get("marker", []),
        "sounds": by_category.get("sound", []),
        "generators": by_category.get("generator", []),
        "things": by_category.get("thing", []),
        "decorations": by_category.get("decoration", []),
        "unknown_sprites": unknown,
        "channels": _channel_roles(channel_graph(disk)),
        "unsupported": {
            "unknown_sprite_types": sorted({item["type_id"] for item in unknown}),
            "unknown_sector_types": [
                type_id for type_id, _ in sector_type_counts.items()
                if not classify("sector", type_id)["known"]
            ],
            "unknown_wall_types": [
                type_id for type_id, _ in wall_type_counts.items()
                if not classify("wall", type_id)["known"]
            ],
        },
    }


def explain_mechanisms(disk: DiskMap) -> dict[str, Any]:
    """Enumerate every extended/special object with static activation evidence.

    Runtime interpolation is not executed. Z off/on values and trigger flags
    are reported so a later description can state what should happen.
    """
    sectors = [
        record for index, sector in enumerate(disk.sectors)
        if (record := _sector_mechanism(index, sector)) is not None
    ]
    walls = [
        record for index, wall in enumerate(disk.walls)
        if (record := _wall_mechanism(index, wall)) is not None
    ]
    interesting_sprites = []
    for index, sprite in enumerate(disk.sprites):
        record = _sprite_record(index, sprite)
        extra = record.get("xsprite")
        category = record["category"]
        if category in {"start", "weapon", "ammo", "health", "armor", "powerup", "key", "flag", "decoration"}:
            if extra and (extra["tx_id"] or extra["rx_id"] or extra["triggers"]):
                interesting_sprites.append(record)
            continue
        interesting_sprites.append(record)

    unexplained = []
    for record in sectors:
        if not record["known"] and record["type_id"]:
            unexplained.append(record["ref"])
        extra = record.get("xsector") or {}
        if extra.get("underwater") or extra.get("wind_velocity") or extra.get("bob_z_range") or extra.get("damage_type"):
            continue
        if record["type_id"] == 0 and extra and not extra.get("tx_id") and not extra.get("rx_id") and not extra.get("triggers"):
            # shade/panning-only extras are still listed; not unexplained
            continue
    for record in interesting_sprites:
        if not record["known"]:
            unexplained.append(record["ref"])

    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "facts+derived",
        "sectors": sectors,
        "walls": walls,
        "sprites": interesting_sprites,
        "channels": _channel_roles(channel_graph(disk)),
        "unresolved": unexplained,
        "notes": [
            "kSectorZMotion interpolates floor/ceiling between off_*_z and on_*_z",
            "kSectorSlideMarked / kSectorRotate use marker sprites 3/4/5",
            "Ambient SFX (type 710) is processed by asound.cpp on kStatAmbience",
            "This listing does not execute busy-time motion",
        ],
    }


def multiplayer_layout(disk: DiskMap, build: BuildIR | None = None) -> dict[str, Any]:
    """Spawn/resource geometry with optional 2D sight. No balance claims."""
    inventory = inventory_map(disk)
    starts = inventory["starts"]["multiplayer"] or inventory["starts"]["single_player"]
    pickups = inventory["pickups"]
    profile = PLAYER_PROFILES["blood"]
    ir = build if build is not None else disk.to_build_ir()
    walls = occluding_segments(ir)
    sight = spawn_sight_report(ir, include_sp_start=False) if inventory["starts"]["multiplayer"] else spawn_sight_report(ir)
    nearest = []
    for start in starts:
        ranked = []
        for pickup in pickups:
            distance = hypot(pickup["x"] - start["x"], pickup["y"] - start["y"])
            probe = line_of_sight(ir, start["x"], start["y"], pickup["x"], pickup["y"], segments=walls)
            ranked.append({
                "pickup": pickup["ref"],
                "type_name": pickup["type_name"],
                "category": pickup["category"],
                "distance": round(distance, 3),
                "distance_player_widths": round(distance / profile.body_width, 3),
                "sight_clear": probe["clear"],
            })
        ranked.sort(key=lambda item: item["distance"])
        nearest.append({
            "start": start["ref"],
            "sector": start["sector"],
            "nearest_pickups": ranked[:8],
        })
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "player_body_width": profile.body_width,
        "starts": starts,
        "pickup_count": len(pickups),
        "pickup_categories": dict(Counter(item["category"] for item in pickups)),
        "spawn_sight": sight,
        "nearest_resources": nearest,
        "not_inferred": [
            "competitive balance",
            "likely player paths as intent",
            "high-control positions as design quality",
        ],
    }
