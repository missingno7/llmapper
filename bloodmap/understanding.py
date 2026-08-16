"""Bundled map-understanding sensors for independent reading.

This is a reading packet, not a prose generator and not a similarity score.
Callers freeze this packet from one map before comparing it to another.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .analysis import validate_map
from .contents import explain_mechanisms, inventory_map, multiplayer_layout
from .exposure import route_exposure_report, spawn_neighborhood_report
from .model import DiskMap
from .morphology import analyze_morphology
from .player_space import compare_transition, inspect_space
from .sight import spawn_sight_report
from .spatial import analyze_spatial


SCHEMA = "llmapper.map-understanding"
SCHEMA_VERSION = 1


def _compact_scale(space: dict[str, Any]) -> dict[str, Any]:
    scale = space["scale"]
    return {
        "sector_count": space["shape"]["sector_count"],
        "footprint_player_areas": scale["footprint"].get("player_areas"),
        "aabb_width_player_widths": scale["aabb_width"].get("player_widths"),
        "clear_height_player_heights": scale["clear_height"].get("player_heights"),
        "clear_height_range": scale["clear_height_range"],
        "opening_width_range": scale["opening_width_range"],
        "enclosure": space["enclosure"],
        "surfaces": space["surfaces"],
    }


def _sky_ids(disk: DiskMap) -> list[int]:
    return [index for index, sector in enumerate(disk.sectors) if int(sector.fields["ceiling_stat"]) & 1]


def understand_map(disk: DiskMap, *, include_sp_start: bool = False) -> dict[str, Any]:
    """Deterministic sensor packet used by independent map-understanding reports."""
    build = disk.to_build_ir()
    inventory = inventory_map(disk)
    mechanisms = explain_mechanisms(disk)
    spatial = analyze_spatial(build)
    sky = _sky_ids(disk)
    covered = [index for index in range(len(disk.sectors)) if index not in set(sky)]
    sky_space = inspect_space(build, sky) if sky else None
    covered_space = inspect_space(build, covered) if covered else None
    whole = inspect_space(build)
    mp_starts = inventory["starts"]["multiplayer"]
    indoor = [item["sector"] for item in mp_starts if item["sector"] in set(covered)]
    outdoor = [item["sector"] for item in mp_starts if item["sector"] in set(sky)]
    transition = None
    if indoor and outdoor:
        transition = compare_transition(build, indoor, outdoor)
    sight = spawn_sight_report(build, include_sp_start=include_sp_start)
    neighborhoods = spawn_neighborhood_report(build, include_sp_start=include_sp_start)
    routes = route_exposure_report(build, include_sp_start=include_sp_start)
    morph = analyze_morphology(build)
    morph = {key: value for key, value in morph.items() if key != "loops"}
    layout = multiplayer_layout(disk, build)
    errors = [item for item in validate_map(disk) if item.severity == "error"]
    xs = [int(wall.fields["x"]) for wall in disk.walls]
    ys = [int(wall.fields["y"]) for wall in disk.walls]
    width = 384
    picnums = {
        "floor": dict(Counter(int(sector.fields["floor_picnum"]) for sector in disk.sectors)),
        "ceiling": dict(Counter(int(sector.fields["ceiling_picnum"]) for sector in disk.sectors)),
        "wall": dict(Counter(int(wall.fields["picnum"]) for wall in disk.walls)),
    }
    floor_z = {
        "sky": sorted({int(disk.sectors[index].fields["floor_z"]) for index in sky}),
        "covered": sorted({int(disk.sectors[index].fields["floor_z"]) for index in covered}),
    }
    ceil_z = {
        "sky": sorted({int(disk.sectors[index].fields["ceiling_z"]) for index in sky}),
        "covered": sorted({int(disk.sectors[index].fields["ceiling_z"]) for index in covered}),
    }
    underwater = [
        index for index, sector in enumerate(disk.sectors)
        if sector.extra and sector.extra.fields.get("underwater")
    ]
    routes_compact = []
    for route in routes["routes"]:
        routes_compact.append({key: value for key, value in route.items() if key != "samples"})
    prog = spatial["views"]["progression"]
    trav = spatial["views"]["traversability"]
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "model": "bundled independent sensors; not a room model and not a similarity score",
        "parse": {
            "version": f"0x{disk.version:04x}",
            "validation_errors": len(errors),
            "sectors": len(disk.sectors),
            "walls": len(disk.walls),
            "sprites": len(disk.sprites),
            "xsectors": sum(1 for sector in disk.sectors if sector.extra),
            "xwalls": sum(1 for wall in disk.walls if wall.extra),
            "xsprites": sum(1 for sprite in disk.sprites if sprite.extra),
            "parallax_ceilings": len(sky),
            "masked_walls": inventory["counts"]["masked_walls"],
            "blocking_walls": inventory["counts"]["blocking_walls"],
        },
        "header": {
            "visibility": disk.header.get("visibility"),
            "sky_type": disk.header.get("sky_type"),
            "sky_bits": disk.header.get("sky_bits"),
        },
        "aabb_player_widths": [
            round((max(xs) - min(xs)) / width, 4) if xs else 0.0,
            round((max(ys) - min(ys)) / width, 4) if ys else 0.0,
        ],
        "starts": inventory["starts"],
        "indoor_multiplayer_starts": len(indoor),
        "outdoor_multiplayer_starts": len(outdoor),
        "pickups": [
            {
                "ref": item["ref"],
                "type_id": item["type_id"],
                "type_name": item["type_name"],
                "category": item["category"],
                "sector": item["sector"],
                "sky_ceiling": item["sector"] in set(sky),
                "underwater": item["sector"] in set(underwater),
            }
            for item in inventory["pickups"]
        ],
        "pickup_categories": dict(Counter(item["category"] for item in inventory["pickups"])),
        "unknown_sprites": inventory["unknown_sprites"],
        "picnums": picnums,
        "floor_z": floor_z,
        "ceiling_z": ceil_z,
        "underwater_sectors": underwater,
        "space": {
            "whole": _compact_scale(whole),
            "sky": None if sky_space is None else _compact_scale(sky_space),
            "covered": None if covered_space is None else _compact_scale(covered_space),
        },
        "transition_indoor_starts_to_outdoor_starts": None if transition is None else {
            "sky_exposure": transition["sky_exposure"],
            "clear_height_ratio": transition["clear_height_ratio"],
            "navigable_area_ratio": transition["navigable_area_ratio"],
        },
        "sight": {
            "pairs": len(sight["pairs"]),
            "clear": sum(1 for pair in sight["pairs"] if pair["clear"]),
            "roses": sight.get("depth_summaries") or [],
        },
        "neighborhoods": neighborhoods,
        "routes": {
            "target_sector": routes.get("target_sector"),
            "summaries": routes_compact,
        },
        "morphology": morph,
        "spatial": {
            "reachable": len(prog["reachable_sectors"]),
            "unreachable": len(prog["unreachable_sectors"]),
            "walkable_at_rest": len(trav["walkable_at_rest"]),
            "blocked_or_state_dependent": len(trav["blocked_or_state_dependent"]),
            "nonportal": trav["known_non_portal_transitions"],
            "hypothesis_counts": dict(Counter(item["kind"] for item in spatial["hypotheses"])),
        },
        "mechanisms": {
            "sectors": mechanisms["sectors"],
            "walls": mechanisms["walls"],
            "notes": mechanisms["notes"],
        },
        "switches": inventory.get("switches") or [],
        "markers": inventory.get("markers") or [],
        "sounds": inventory.get("sounds") or [],
        "nearest_resources": layout["nearest_resources"],
        "limitations": [
            "2D sight ignores height, sprites, and lighting",
            "prose interpretation is not generated here",
            "this packet must be frozen before reading a target description",
        ],
    }
