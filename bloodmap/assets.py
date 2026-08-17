"""Contextual sprite and decorative-tile knowledge.

Facets stay independent. A sprite may be wall-mounted, decorative, a key
signifier, and non-blocking at once. Labels that imply purpose are INTERPRETED
and require corpus repetition plus optional review packets.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .blood_types import classify
from .doors import (
    KEY_TYPES,
    MARKER_TYPES,
    mine_map,
    SIGNIFIER_RADIUS_PW,
)
from .format import read_map
from .patterns import classify_map_population, list_original_maps
from .placement import PlacementError, observe_sprite_attachment
from .player_space import PLAYER_PROFILES


SCHEMA = "llmapper.blood-sprite-context"
SCHEMA_VERSION = 1
PLAYER = PLAYER_PROFILES["blood"]
EXAMPLE_CAP = 8


class AssetError(ValueError):
    pass


def _pic_key(picnum: int, type_id: int) -> str:
    return f"blood:sprite:{picnum}:type{type_id}"


def observe_sprite_context(disk, sprite_id: int, *, near_motion: bool, near_key: int) -> dict[str, Any]:
    sprite = disk.sprites[sprite_id]
    fields = sprite.fields
    typed = classify("sprite", int(fields["type"]))
    extra = None if sprite.extra is None else dict(sprite.extra.fields)
    try:
        sit = observe_sprite_attachment(disk, sprite_id)
        sit_kind = sit.get("sit")
        height_ph = sit.get("height_from_floor_player_heights")
        wall_pw = sit.get("wall_distance_player_widths")
    except PlacementError:
        sit_kind, height_ph, wall_pw = "unknown", None, None
    cstat = int(fields["cstat"])
    return {
        "sprite_id": sprite_id,
        "picnum": int(fields["picnum"]),
        "type_id": int(fields["type"]),
        "type_name": typed["name"],
        "category": typed["category"],
        "cstat": cstat,
        "wall_aligned": bool(cstat & 16),
        "floor_aligned": bool(cstat & 32),
        "blocking": bool(cstat & 1),
        "hitscan_blocking": bool(cstat & 64),
        "translucent": bool(cstat & 2) or bool(cstat & 512),
        "x_repeat": int(fields["x_repeat"]),
        "y_repeat": int(fields["y_repeat"]),
        "pal": int(fields["pal"]),
        "shade": int(fields["shade"]),
        "sit": sit_kind,
        "height_ph": height_ph,
        "wall_distance_pw": wall_pw,
        "near_motion": near_motion,
        "near_keyed_motion": near_key,
        "tx_id": 0 if extra is None else int(extra.get("tx_id") or 0),
        "rx_id": 0 if extra is None else int(extra.get("rx_id") or 0),
        "key": 0 if extra is None else int(extra.get("key") or 0),
        "interactive": bool(extra and (
            extra.get("trigger_push") or extra.get("tx_id") or extra.get("rx_id")
        )),
    }


def mine_sprite_context(directory: str | Path, *, population: str = "blood-campaign") -> dict[str, Any]:
    files = list_original_maps(directory, population=population)
    if not files:
        raise AssetError(f"no {population} maps in {directory}")
    families: dict[str, dict[str, Any]] = {}
    for path in files:
        disk = read_map(path)
        mined = mine_map(path)
        motion_sectors = {item["sector_id"] for item in mined["occurrences"]}
        keyed_near: dict[int, int] = defaultdict(int)
        for item in mined["occurrences"]:
            if not item.get("key"):
                continue
            for sprite in item.get("nearby_sprites") or []:
                keyed_near[sprite["sprite_id"]] = int(item["key"])
        near_motion_ids = {
            sprite["sprite_id"]
            for item in mined["occurrences"]
            for sprite in item.get("nearby_sprites") or []
        }
        for sprite_id, sprite in enumerate(disk.sprites):
            type_id = int(sprite.fields["type"])
            if type_id in KEY_TYPES or type_id in MARKER_TYPES:
                continue
            category = classify("sprite", type_id)["category"]
            if category == "dude":
                continue
            near = sprite_id in near_motion_ids or int(sprite.fields["sector"]) in motion_sectors
            wall_aligned = bool(int(sprite.fields["cstat"]) & 16)
            extra = None if sprite.extra is None else sprite.extra.fields
            interactive = bool(extra and (extra.get("trigger_push") or extra.get("tx_id")))
            if not (near or wall_aligned or interactive):
                continue
            record = observe_sprite_context(
                disk, sprite_id,
                near_motion=near,
                near_key=keyed_near.get(sprite_id, 0),
            )
            record["map"] = path.name
            key = _pic_key(record["picnum"], record["type_id"])
            family = families.setdefault(key, {
                "id": key,
                "picnum": record["picnum"],
                "type_id": record["type_id"],
                "type_name": record["type_name"],
                "category": record["category"],
                "maps": set(),
                "count": 0,
                "near_motion": 0,
                "near_keyed": 0,
                "interactive": 0,
                "wall_aligned": 0,
                "floor_aligned": 0,
                "blocking": 0,
                "sits": Counter(),
                "pals": Counter(),
                "x_repeats": [],
                "height_ph": [],
                "examples": [],
            })
            family["maps"].add(path.name)
            family["count"] += 1
            family["near_motion"] += int(record["near_motion"])
            family["near_keyed"] += int(bool(record["near_keyed_motion"]))
            family["interactive"] += int(record["interactive"])
            family["wall_aligned"] += int(record["wall_aligned"])
            family["floor_aligned"] += int(record["floor_aligned"])
            family["blocking"] += int(record["blocking"])
            family["sits"][record["sit"] or "unknown"] += 1
            family["pals"][record["pal"]] += 1
            family["x_repeats"].append(record["x_repeat"])
            if record["height_ph"] is not None:
                family["height_ph"].append(record["height_ph"])
            if len(family["examples"]) < EXAMPLE_CAP:
                family["examples"].append({
                    "map": path.name,
                    "sprite_id": sprite_id,
                    "sit": record["sit"],
                    "height_ph": record["height_ph"],
                    "wall_distance_pw": record["wall_distance_pw"],
                    "near_motion": record["near_motion"],
                    "near_keyed_motion": record["near_keyed_motion"],
                    "cstat": record["cstat"],
                    "x_repeat": record["x_repeat"],
                    "y_repeat": record["y_repeat"],
                })

    rows = []
    for family in families.values():
        n = max(1, family["count"])
        heights = sorted(family["height_ph"])
        repeats = sorted(family["x_repeats"])
        rows.append({
            "id": family["id"],
            "picnum": family["picnum"],
            "type_id": family["type_id"],
            "type_name": family["type_name"],
            "category": family["category"],
            "count": family["count"],
            "maps": len(family["maps"]),
            "near_motion_share": round(family["near_motion"] / n, 3),
            "near_keyed_share": round(family["near_keyed"] / n, 3),
            "interactive_share": round(family["interactive"] / n, 3),
            "wall_aligned_share": round(family["wall_aligned"] / n, 3),
            "floor_aligned_share": round(family["floor_aligned"] / n, 3),
            "blocking_share": round(family["blocking"] / n, 3),
            "sits": dict(family["sits"]),
            "pals": dict(family["pals"].most_common(6)),
            "median_x_repeat": repeats[len(repeats) // 2] if repeats else None,
            "median_height_ph": heights[len(heights) // 2] if heights else None,
            "examples": family["examples"],
        })
    rows.sort(key=lambda item: (-item["near_keyed_share"], -item["near_motion_share"], -item["count"]))
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "population": population,
        "maps": len(files),
        "family_count": len(rows),
        "families": rows,
        "signifier_radius_pw": SIGNIFIER_RADIUS_PW,
        "notes": [
            "facets are independent counts, not a single category",
            "near_motion is co-occurrence, not purpose",
            "INTERPRETED purpose requires review packets plus mapper judgment",
        ],
    }


def query_sprite_families(
    catalog: dict[str, Any],
    *,
    wall_aligned: bool | None = None,
    near_keyed: bool | None = None,
    interactive: bool | None = None,
    min_maps: int = 2,
    limit: int = 12,
) -> list[dict[str, Any]]:
    hits = []
    for family in catalog.get("families") or []:
        if family.get("maps", 0) < min_maps:
            continue
        share = family.get("wall_aligned_share") or 0
        if wall_aligned is True and share < 0.5:
            continue
        if wall_aligned is False and share >= 0.5:
            continue
        if near_keyed and (family.get("near_keyed_share") or 0) < 0.15:
            continue
        if interactive is not None:
            share = family.get("interactive_share") or 0
            if interactive and share < 0.3:
                continue
            if not interactive and share >= 0.3:
                continue
        hits.append(family)
        if len(hits) >= limit:
            break
    return hits
