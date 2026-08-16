"""Evidence-first material/texture knowledge.

This module does not start from a human taxonomy. It measures native identity,
ART appearance, and original-map usage, then forms unlabeled clusters. Semantic
facet names arrive only through an imported, versioned ontology whose labels
are stored as INTERPRETED, never as native facts.
"""

from __future__ import annotations

import base64
import json
from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Iterable

from .art import (
    ArtError, ArtTile, animation_families, art_feature, feature_distance,
    read_art_directory, read_palette, tile_preview_png, transparency_stats,
)
from .doom import ML_TWOSIDED, NO_SIDE, DoomDiskMap, texture_label
from .duke import DukeDiskMap
from .format import read_map
from .model import DiskMap, DiskObject


class MaterialsError(ValueError):
    pass


EVIDENCE_SCHEMA = "llmapper.material-evidence"
ONTOLOGY_SCHEMA = "llmapper.material-ontology"
BATCH_SCHEMA = "llmapper.material-classification-batch"
KNOWLEDGE_SCHEMA = "llmapper.material-knowledge"
SCHEMA_VERSION = 1
PROVENANCE = ("VERIFIED", "DERIVED", "INTERPRETED")
RESERVED_TRUTH_KEYS = frozenset({
    "player_start_valid", "exit_reachable", "is_floor", "is_wall", "is_door",
    "is_metal", "true", "pass",
})
USAGE_KEYS = (
    "wall", "floor", "ceiling", "sprite", "overwall", "masked", "translucent",
    "one_sided", "two_sided", "mechanism", "moving_sector", "static",
)
REPRESENTATIVE_LIMIT = 8
OCCURRENCE_CAP = 24
VISUAL_CLUSTER_THRESHOLD = 0.55
USAGE_CLUSTER_THRESHOLD = 0.18


def asset_id(game: str, native_id: int | str, *, kind: str = "tile") -> str:
    return f"{game}:{kind}:{native_id}"


def parse_asset_id(value: str) -> tuple[str, str, str]:
    game, kind, native = str(value).split(":", 2)
    return game, kind, native


def empty_usage() -> dict[str, int]:
    return {key: 0 for key in USAGE_KEYS} | {"maps": 0, "total": 0}


def _histogram(values: list[int | float]) -> dict[str, Any]:
    if not values:
        return {"kind": "empty", "samples": 0, "provenance": "VERIFIED"}
    counts = Counter(int(value) for value in values)
    ordered = sorted(values)
    n = len(ordered)

    def pct(p: float) -> int | float:
        return ordered[min(n - 1, max(0, int(round((n - 1) * p))))]

    payload: dict[str, Any] = {
        "kind": "exact" if len(counts) <= 24 else "quantiles",
        "samples": n,
        "min": ordered[0],
        "p25": pct(0.25),
        "median": pct(0.5),
        "p75": pct(0.75),
        "max": ordered[-1],
        "provenance": "VERIFIED",
    }
    if payload["kind"] == "exact":
        payload["counts"] = {str(key): count for key, count in sorted(counts.items())}
    return payload


def _top(counter: Counter[str], limit: int = 12) -> dict[str, int]:
    return {key: count for key, count in counter.most_common(limit)}


def _usage_vector(usage: dict[str, int]) -> tuple[float, ...]:
    values = [float(usage.get(key, 0)) for key in USAGE_KEYS]
    norm = sum(values) or 1.0
    return tuple(item / norm for item in values)


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    na = sum(a * a for a in left) ** 0.5
    nb = sum(b * b for b in right) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _union_find(ids: list[str], linked: Iterable[tuple[str, str]]) -> list[list[str]]:
    parent = {item: item for item in ids}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for left, right in linked:
        if left not in parent or right not in parent:
            continue
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)
    groups: dict[str, list[str]] = defaultdict(list)
    for item in ids:
        groups[find(item)].append(item)
    return [groups[key] for key in sorted(groups)]


def _new_asset(game: str, native_id: str, *, kind: str = "tile") -> dict[str, Any]:
    ident = asset_id(game, native_id, kind=kind)
    return {
        "id": ident,
        "game": game,
        "native_kind": kind,
        "native_id": str(native_id),
        "identity": {"provenance": "VERIFIED"},
        "appearance": None,
        "usage": empty_usage(),
        "distributions": {
            "x_repeat": [], "y_repeat": [], "shade": [], "pal": [],
            "world_width": [], "sector_height": [],
        },
        "representatives": [],
        "neighbors": Counter(),
        "floors": Counter(),
        "ceilings": Counter(),
        "maps": set(),
        "status": "unannotated",
    }


def _ensure(catalog: dict[str, Any], game: str, native_id: int | str, *, kind: str = "tile") -> dict[str, Any]:
    ident = asset_id(game, native_id, kind=kind)
    assets = catalog["assets"]
    if ident not in assets:
        assets[ident] = _new_asset(game, native_id, kind=kind)
    return assets[ident]


def new_catalog(*, games: list[str] | None = None) -> dict[str, Any]:
    return {
        "$schema": EVIDENCE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "games": list(games or []),
        "maps_mined": [],
        "art_sources": [],
        "assets": {},
        "clusters": [],
        "relations": [],
        "palettes": [],
        "animation_families": [],
        "ontology": empty_ontology(),
        "annotations": {},
        "contradictions": [],
        "notes": [
            "Clusters and relations are unlabeled evidence groups.",
            "Facet names are INTERPRETED and must be imported, never assumed.",
            "Unknown/ambiguous/mixed_use are valid terminal statuses.",
        ],
    }


def empty_ontology() -> dict[str, Any]:
    return {
        "$schema": ONTOLOGY_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "status": "empty",
        "facets": [],
        "basis": "no facets yet; wait for a classification-batch review",
        "useful_for": [],
        "rejected_distinctions": [],
    }


def attach_appearance(
    catalog: dict[str, Any],
    game: str,
    tiles: dict[int, ArtTile],
    palette: tuple[tuple[int, int, int], ...],
    *,
    source: str | None = None,
) -> None:
    if game not in catalog["games"]:
        catalog["games"].append(game)
    if source:
        catalog["art_sources"].append({"game": game, "path": source, "tiles": len(tiles)})
    catalog["animation_families"].extend(
        {**family, "game": game, "members": [asset_id(game, member) for member in family["members"]]}
        for family in animation_families(tiles)
    )
    for tile_id, tile in tiles.items():
        asset = _ensure(catalog, game, tile_id)
        stats = transparency_stats(tile)
        asset["identity"].update(
            width=tile.width, height=tile.height, animation=tile.animation,
        )
        asset["appearance"] = {
            "provenance": "VERIFIED",
            **stats,
            "feature": [round(value, 6) for value in art_feature(tile, palette)],
        }


def _record_occurrence(
    asset: dict[str, Any],
    *,
    map_name: str,
    kind: str,
    object_ref: str,
    flags: dict[str, Any],
    geometry: dict[str, Any],
    neighbors: list[str],
    floor_id: str | None,
    ceiling_id: str | None,
    mechanism: bool,
    moving: bool,
    masked: bool,
    translucent: bool,
    one_sided: bool,
) -> None:
    usage = asset["usage"]
    usage[kind] = usage.get(kind, 0) + 1
    usage["total"] += 1
    usage["mechanism"] += int(mechanism)
    usage["moving_sector"] += int(moving)
    usage["static"] += int(not mechanism and not moving)
    usage["masked"] += int(masked)
    usage["translucent"] += int(translucent)
    usage["one_sided"] += int(one_sided)
    usage["two_sided"] += int(not one_sided)
    asset["maps"].add(map_name)
    dist = asset["distributions"]
    for key in ("x_repeat", "y_repeat", "shade", "pal", "world_width", "sector_height"):
        if key in geometry and geometry[key] is not None:
            dist[key].append(int(geometry[key]))
    for neighbor in neighbors:
        if neighbor and neighbor != asset["id"]:
            asset["neighbors"][neighbor] += 1
    if floor_id:
        asset["floors"][floor_id] += 1
    if ceiling_id:
        asset["ceilings"][ceiling_id] += 1
    occurrence = {
        "map": map_name,
        "kind": kind,
        "object": object_ref,
        "flags": flags,
        "geometry": {key: geometry[key] for key in geometry if geometry[key] is not None},
        "neighbors": neighbors[:8],
        "mechanism": mechanism,
        "moving_sector": moving,
        "masked": masked,
        "translucent": translucent,
        "one_sided": one_sided,
        "floor": floor_id,
        "ceiling": ceiling_id,
    }
    samples: list[dict[str, Any]] = asset["representatives"]
    key = (
        map_name, kind, int(masked), int(mechanism), int(translucent),
        int(geometry.get("x_repeat") or 0) // 8,
    )
    existing_keys = {
        (
            item["map"], item["kind"], int(item["masked"]), int(item["mechanism"]),
            int(item["translucent"]), int(item["geometry"].get("x_repeat") or 0) // 8,
        )
        for item in samples
    }
    if key not in existing_keys and len(samples) < OCCURRENCE_CAP:
        samples.append(occurrence)
    elif len(samples) < OCCURRENCE_CAP:
        samples.append(occurrence)


def _wall_cstat(cstat: int) -> dict[str, bool]:
    # Ken Build wall cstat: 0 blocking, 4 masked, 5 one-way, 7 translucent, 9 transl. reverse.
    return {
        "blocking": bool(cstat & 1),
        "masked": bool(cstat & 16),
        "one_way": bool(cstat & 32),
        "hitscan_blocking": bool(cstat & 64),
        "translucent": bool(cstat & 128),
        "translucent_reverse": bool(cstat & 512),
    }


def _sprite_cstat(cstat: int) -> dict[str, str | bool]:
    if cstat & 32:
        alignment = "floor"
    elif cstat & 16:
        alignment = "wall"
    else:
        alignment = "face"
    return {
        "blocking": bool(cstat & 1),
        "translucent": bool(cstat & 2),
        "alignment": alignment,
        "one_sided": bool(cstat & 64),
        "hitscan_blocking": bool(cstat & 256),
    }


def _blood_moving(sector: DiskObject) -> bool:
    extra = sector.extra
    if extra is None:
        return False
    fields = extra.fields
    return bool(
        fields.get("off_floor_z") != fields.get("on_floor_z")
        or fields.get("off_ceiling_z") != fields.get("on_ceiling_z")
        or fields.get("busy_time_a")
        or fields.get("bob_speed")
    )


def _blood_mechanism(obj: DiskObject) -> bool:
    extra = obj.extra
    if extra is None:
        return bool(obj.fields.get("type"))
    fields = extra.fields
    return bool(
        fields.get("tx_id") or fields.get("rx_id") or fields.get("trigger_push")
        or fields.get("trigger_vector") or fields.get("trigger_enter")
        or fields.get("key") or obj.fields.get("type")
    )


def mine_blood_map(catalog: dict[str, Any], disk: DiskMap, *, map_name: str) -> None:
    if "blood" not in catalog["games"]:
        catalog["games"].append("blood")
    catalog["maps_mined"].append({"game": "blood", "name": map_name, "sectors": len(disk.sectors)})
    owners = [-1] * len(disk.walls)
    for sector_id, sector in enumerate(disk.sectors):
        for wall_id in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count):
            if 0 <= wall_id < len(disk.walls):
                owners[wall_id] = sector_id
    moving = [_blood_moving(sector) for sector in disk.sectors]
    palettes: dict[tuple, list[int]] = defaultdict(list)

    for sector_id, sector in enumerate(disk.sectors):
        floor_id = asset_id("blood", sector.floor_picnum)
        ceiling_id = asset_id("blood", sector.ceiling_picnum)
        sky = bool(sector.ceiling_stat & 1)
        height = abs(int(sector.floor_z) - int(sector.ceiling_z))
        mechanism = _blood_mechanism(sector)
        floor_asset = _ensure(catalog, "blood", sector.floor_picnum)
        _record_occurrence(
            floor_asset, map_name=map_name, kind="floor", object_ref=f"sector:{sector_id}",
            flags={"sky": False}, geometry={
                "shade": sector.floor_shade, "pal": sector.floor_pal,
                "x_repeat": None, "y_repeat": None, "world_width": None,
                "sector_height": height, "panning": (sector.floor_x_panning, sector.floor_y_panning),
            },
            neighbors=[ceiling_id], floor_id=floor_id, ceiling_id=ceiling_id,
            mechanism=mechanism, moving=moving[sector_id], masked=False, translucent=False,
            one_sided=False,
        )
        ceil_asset = _ensure(catalog, "blood", sector.ceiling_picnum)
        _record_occurrence(
            ceil_asset, map_name=map_name, kind="ceiling", object_ref=f"sector:{sector_id}",
            flags={"sky": sky, "parallax": sky}, geometry={
                "shade": sector.ceiling_shade, "pal": sector.ceiling_pal,
                "x_repeat": None, "y_repeat": None, "world_width": None,
                "sector_height": height, "panning": (sector.ceiling_x_panning, sector.ceiling_y_panning),
            },
            neighbors=[floor_id], floor_id=floor_id, ceiling_id=ceiling_id,
            mechanism=mechanism, moving=moving[sector_id], masked=False, translucent=False,
            one_sided=False,
        )
        wall_ids = [
            asset_id("blood", disk.walls[wid].picnum)
            for wid in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)
            if 0 <= wid < len(disk.walls) and disk.walls[wid].picnum
        ]
        palettes[(floor_id, ceiling_id, tuple(sorted(set(wall_ids))))].append(sector_id)

    for wall_id, wall in enumerate(disk.walls):
        sector_id = owners[wall_id] if wall_id < len(owners) else -1
        sector = disk.sectors[sector_id] if 0 <= sector_id < len(disk.sectors) else None
        point2 = disk.walls[wall.point2] if 0 <= wall.point2 < len(disk.walls) else wall
        width = int(hypot(wall.x - point2.x, wall.y - point2.y))
        height = abs(int(sector.floor_z) - int(sector.ceiling_z)) if sector else None
        floor_id = asset_id("blood", sector.floor_picnum) if sector else None
        ceiling_id = asset_id("blood", sector.ceiling_picnum) if sector else None
        prev_id = wall_id - 1 if sector and wall_id > sector.wall_ptr else (
            sector.wall_ptr + sector.wall_count - 1 if sector else None
        )
        neighbor_ids = []
        if prev_id is not None and 0 <= prev_id < len(disk.walls):
            neighbor_ids.append(asset_id("blood", disk.walls[prev_id].picnum))
        neighbor_ids.append(asset_id("blood", point2.picnum))
        flags = _wall_cstat(wall.cstat)
        one_sided = wall.next_sector < 0 or flags["one_way"]
        mechanism = _blood_mechanism(wall) or (sector is not None and _blood_mechanism(sector))
        moving_flag = bool(0 <= sector_id < len(moving) and moving[sector_id])
        geometry = {
            "x_repeat": wall.x_repeat, "y_repeat": wall.y_repeat, "shade": wall.shade,
            "pal": wall.pal, "world_width": width, "sector_height": height,
            "panning": (wall.x_panning, wall.y_panning),
        }
        if wall.picnum:
            _record_occurrence(
                _ensure(catalog, "blood", wall.picnum), map_name=map_name, kind="wall",
                object_ref=f"wall:{wall_id}", flags=flags, geometry=geometry,
                neighbors=neighbor_ids, floor_id=floor_id, ceiling_id=ceiling_id,
                mechanism=mechanism, moving=moving_flag, masked=flags["masked"],
                translucent=flags["translucent"], one_sided=one_sided,
            )
        if wall.over_picnum and wall.over_picnum > 0:
            over_flags = {**flags, "overpic": True}
            _record_occurrence(
                _ensure(catalog, "blood", wall.over_picnum), map_name=map_name, kind="overwall",
                object_ref=f"wall:{wall_id}", flags=over_flags, geometry=geometry,
                neighbors=[asset_id("blood", wall.picnum), *neighbor_ids],
                floor_id=floor_id, ceiling_id=ceiling_id, mechanism=mechanism,
                moving=moving_flag, masked=True, translucent=flags["translucent"],
                one_sided=one_sided,
            )

    for sprite_id, sprite in enumerate(disk.sprites):
        flags = _sprite_cstat(sprite.cstat)
        sector = disk.sectors[sprite.sector] if 0 <= sprite.sector < len(disk.sectors) else None
        floor_id = asset_id("blood", sector.floor_picnum) if sector else None
        ceiling_id = asset_id("blood", sector.ceiling_picnum) if sector else None
        kind = "decal" if flags["alignment"] == "wall" else "sprite"
        _record_occurrence(
            _ensure(catalog, "blood", sprite.picnum), map_name=map_name, kind=kind,
            object_ref=f"sprite:{sprite_id}", flags={**flags, "type": sprite.type, "status": sprite.status},
            geometry={
                "x_repeat": sprite.x_repeat, "y_repeat": sprite.y_repeat, "shade": sprite.shade,
                "pal": sprite.pal, "world_width": None, "sector_height": None,
            },
            neighbors=[], floor_id=floor_id, ceiling_id=ceiling_id,
            mechanism=_blood_mechanism(sprite), moving=False,
            masked=False, translucent=bool(flags["translucent"]),
            one_sided=bool(flags["one_sided"]),
        )
    _store_palettes(catalog, "blood", map_name, palettes)


def mine_duke_map(catalog: dict[str, Any], disk: DukeDiskMap, *, map_name: str) -> None:
    if "duke3d" not in catalog["games"]:
        catalog["games"].append("duke3d")
    catalog["maps_mined"].append({"game": "duke3d", "name": map_name, "sectors": len(disk.sectors)})
    owners = [-1] * len(disk.walls)
    for sector_id, sector in enumerate(disk.sectors):
        for wall_id in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count):
            if 0 <= wall_id < len(disk.walls):
                owners[wall_id] = sector_id
    palettes: dict[tuple, list[int]] = defaultdict(list)

    for sector_id, sector in enumerate(disk.sectors):
        floor_id = asset_id("duke3d", sector.floor_picnum)
        ceiling_id = asset_id("duke3d", sector.ceiling_picnum)
        sky = bool(sector.ceiling_stat & 1)
        height = abs(int(sector.floor_z) - int(sector.ceiling_z))
        mechanism = bool(sector.lotag)
        moving = bool(sector.lotag)
        _record_occurrence(
            _ensure(catalog, "duke3d", sector.floor_picnum), map_name=map_name, kind="floor",
            object_ref=f"sector:{sector_id}", flags={"lotag": sector.lotag},
            geometry={
                "shade": sector.floor_shade, "pal": sector.floor_pal, "x_repeat": None,
                "y_repeat": None, "world_width": None, "sector_height": height,
            },
            neighbors=[ceiling_id], floor_id=floor_id, ceiling_id=ceiling_id,
            mechanism=mechanism, moving=moving, masked=False, translucent=False, one_sided=False,
        )
        _record_occurrence(
            _ensure(catalog, "duke3d", sector.ceiling_picnum), map_name=map_name, kind="ceiling",
            object_ref=f"sector:{sector_id}", flags={"sky": sky, "lotag": sector.lotag},
            geometry={
                "shade": sector.ceiling_shade, "pal": sector.ceiling_pal, "x_repeat": None,
                "y_repeat": None, "world_width": None, "sector_height": height,
            },
            neighbors=[floor_id], floor_id=floor_id, ceiling_id=ceiling_id,
            mechanism=mechanism, moving=moving, masked=False, translucent=False, one_sided=False,
        )
        wall_ids = [
            asset_id("duke3d", disk.walls[wid].picnum)
            for wid in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)
            if 0 <= wid < len(disk.walls) and disk.walls[wid].picnum
        ]
        palettes[(floor_id, ceiling_id, tuple(sorted(set(wall_ids))))].append(sector_id)

    for wall_id, wall in enumerate(disk.walls):
        sector_id = owners[wall_id] if wall_id < len(owners) else -1
        sector = disk.sectors[sector_id] if 0 <= sector_id < len(disk.sectors) else None
        point2 = disk.walls[wall.point2] if 0 <= wall.point2 < len(disk.walls) else wall
        width = int(hypot(wall.x - point2.x, wall.y - point2.y))
        height = abs(int(sector.floor_z) - int(sector.ceiling_z)) if sector else None
        flags = _wall_cstat(wall.cstat)
        geometry = {
            "x_repeat": wall.x_repeat, "y_repeat": wall.y_repeat, "shade": wall.shade,
            "pal": wall.pal, "world_width": width, "sector_height": height,
        }
        neighbors = [asset_id("duke3d", point2.picnum)]
        floor_id = asset_id("duke3d", sector.floor_picnum) if sector else None
        ceiling_id = asset_id("duke3d", sector.ceiling_picnum) if sector else None
        one_sided = wall.next_sector < 0 or flags["one_way"]
        mechanism = bool(wall.lotag or (sector and sector.lotag))
        if wall.picnum:
            _record_occurrence(
                _ensure(catalog, "duke3d", wall.picnum), map_name=map_name, kind="wall",
                object_ref=f"wall:{wall_id}", flags={**flags, "lotag": wall.lotag},
                geometry=geometry, neighbors=neighbors, floor_id=floor_id, ceiling_id=ceiling_id,
                mechanism=mechanism, moving=bool(sector and sector.lotag),
                masked=flags["masked"], translucent=flags["translucent"], one_sided=one_sided,
            )
        if wall.over_picnum and wall.over_picnum > 0:
            _record_occurrence(
                _ensure(catalog, "duke3d", wall.over_picnum), map_name=map_name, kind="overwall",
                object_ref=f"wall:{wall_id}", flags={**flags, "overpic": True, "lotag": wall.lotag},
                geometry=geometry, neighbors=[asset_id("duke3d", wall.picnum), *neighbors],
                floor_id=floor_id, ceiling_id=ceiling_id, mechanism=mechanism,
                moving=bool(sector and sector.lotag), masked=True,
                translucent=flags["translucent"], one_sided=one_sided,
            )

    for sprite_id, sprite in enumerate(disk.sprites):
        flags = _sprite_cstat(sprite.cstat)
        sector = disk.sectors[sprite.sector] if 0 <= sprite.sector < len(disk.sectors) else None
        _record_occurrence(
            _ensure(catalog, "duke3d", sprite.picnum), map_name=map_name, kind="sprite",
            object_ref=f"sprite:{sprite_id}",
            flags={**flags, "lotag": sprite.lotag, "hitag": sprite.hitag},
            geometry={
                "x_repeat": sprite.x_repeat, "y_repeat": sprite.y_repeat,
                "shade": sprite.shade, "pal": sprite.pal, "world_width": None, "sector_height": None,
            },
            neighbors=[], floor_id=asset_id("duke3d", sector.floor_picnum) if sector else None,
            ceiling_id=asset_id("duke3d", sector.ceiling_picnum) if sector else None,
            mechanism=bool(sprite.lotag), moving=False, masked=False,
            translucent=bool(flags["translucent"]), one_sided=bool(flags["one_sided"]),
        )
    _store_palettes(catalog, "duke3d", map_name, palettes)


def mine_doom_map(catalog: dict[str, Any], level: DoomDiskMap, *, map_name: str) -> None:
    if "doom" not in catalog["games"]:
        catalog["games"].append("doom")
    catalog["maps_mined"].append({"game": "doom", "name": map_name, "sectors": len(level.sectors)})
    palettes: dict[tuple, list[int]] = defaultdict(list)
    for sector_id, sector in enumerate(level.sectors):
        floor_name = texture_label(sector.floor_texture)
        ceil_name = texture_label(sector.ceiling_texture)
        floor_id = asset_id("doom", floor_name, kind="texture") if floor_name else None
        ceiling_id = asset_id("doom", ceil_name, kind="texture") if ceil_name else None
        height = abs(int(sector.floor_height) - int(sector.ceiling_height))
        mechanism = bool(sector.special or sector.tag)
        if floor_id:
            _record_occurrence(
                _ensure(catalog, "doom", floor_name, kind="texture"), map_name=map_name, kind="floor",
                object_ref=f"sector:{sector_id}", flags={"special": sector.special, "tag": sector.tag},
                geometry={
                    "shade": sector.light_level, "pal": None, "x_repeat": None, "y_repeat": None,
                    "world_width": None, "sector_height": height,
                },
                neighbors=[ceiling_id] if ceiling_id else [], floor_id=floor_id, ceiling_id=ceiling_id,
                mechanism=mechanism, moving=bool(sector.special), masked=False, translucent=False,
                one_sided=False,
            )
        if ceiling_id:
            _record_occurrence(
                _ensure(catalog, "doom", ceil_name, kind="texture"), map_name=map_name, kind="ceiling",
                object_ref=f"sector:{sector_id}", flags={"special": sector.special, "tag": sector.tag},
                geometry={
                    "shade": sector.light_level, "pal": None, "x_repeat": None, "y_repeat": None,
                    "world_width": None, "sector_height": height,
                },
                neighbors=[floor_id] if floor_id else [], floor_id=floor_id, ceiling_id=ceiling_id,
                mechanism=mechanism, moving=bool(sector.special), masked=False, translucent=False,
                one_sided=False,
            )

    for line_id, line in enumerate(level.linedefs):
        two_sided = bool(line.flags & ML_TWOSIDED)
        sides = [("front", line.side_front)]
        if line.side_back != NO_SIDE:
            sides.append(("back", line.side_back))
        v1, v2 = level.vertices[line.v1], level.vertices[line.v2]
        width = int(hypot(v1.x - v2.x, v1.y - v2.y))
        mechanism = bool(line.special)
        for side_name, side_index in sides:
            if not 0 <= side_index < len(level.sidedefs):
                continue
            side = level.sidedefs[side_index]
            sector = level.sectors[side.sector] if 0 <= side.sector < len(level.sectors) else None
            height = abs(int(sector.floor_height) - int(sector.ceiling_height)) if sector else None
            floor_id = asset_id("doom", texture_label(sector.floor_texture), kind="texture") if sector else None
            ceiling_id = asset_id("doom", texture_label(sector.ceiling_texture), kind="texture") if sector else None
            for role, raw in (
                ("wall", side.middle_texture),
                ("wall", side.upper_texture),
                ("wall", side.lower_texture),
            ):
                name = texture_label(raw)
                if not name or name == "-":
                    continue
                _record_occurrence(
                    _ensure(catalog, "doom", name, kind="texture"), map_name=map_name, kind=role,
                    object_ref=f"linedef:{line_id}:{side_name}",
                    flags={"special": line.special, "tag": line.tag, "two_sided": two_sided},
                    geometry={
                        "x_repeat": None, "y_repeat": None, "shade": sector.light_level if sector else None,
                        "pal": None, "world_width": width, "sector_height": height,
                        "xofs": side.x_offset, "yofs": side.y_offset,
                    },
                    neighbors=[], floor_id=floor_id, ceiling_id=ceiling_id, mechanism=mechanism,
                    moving=False, masked=False, translucent=False, one_sided=not two_sided,
                )
            if sector:
                walls = []
                for raw in (side.middle_texture, side.upper_texture, side.lower_texture):
                    name = texture_label(raw)
                    if name and name != "-":
                        walls.append(asset_id("doom", name, kind="texture"))
                if floor_id and ceiling_id:
                    palettes[(floor_id, ceiling_id, tuple(sorted(set(walls))))].append(side.sector)
    _store_palettes(catalog, "doom", map_name, palettes)


def _store_palettes(
    catalog: dict[str, Any], game: str, map_name: str, palettes: dict[tuple, list[int]],
) -> None:
    for (floor_id, ceiling_id, walls), sectors in palettes.items():
        catalog["palettes"].append({
            "id": f"palette:{game}:{map_name}:{min(sectors)}",
            "game": game,
            "map": map_name,
            "sectors": [f"sector:{item}" for item in sectors[:12]],
            "sector_count": len(sectors),
            "floor": floor_id,
            "ceiling": ceiling_id,
            "walls": list(walls),
            "provenance": "DERIVED",
            "basis": "per-sector surface set; not a canonical room partition",
        })


def finalize_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    for asset in catalog["assets"].values():
        asset["usage"]["maps"] = len(asset["maps"])
        asset["maps"] = sorted(asset["maps"])
        asset["neighbors"] = _top(asset["neighbors"])
        asset["floors"] = _top(asset["floors"])
        asset["ceilings"] = _top(asset["ceilings"])
        asset["distributions"] = {
            key: _histogram(values) for key, values in asset["distributions"].items()
        }
        asset["representatives"] = select_representatives(asset["representatives"])
        total = asset["usage"]["total"]
        if total == 0 and asset["appearance"] is None:
            asset["status"] = "unknown"
        elif total == 0:
            asset["status"] = "appearance_only"
        else:
            wallish = (asset["usage"]["wall"] + asset["usage"].get("overwall", 0)) / total
            floorish = asset["usage"]["floor"] / total
            ceilish = asset["usage"]["ceiling"] / total
            mixed = sum(value >= 0.2 for value in (wallish, floorish, ceilish)) >= 2
            asset["status"] = "mixed_use" if mixed else "unannotated"
        asset["world_scale"] = _asset_world_scale(asset)
    catalog["clusters"] = discover_clusters(catalog)
    catalog["relations"] = mine_relations(catalog)
    catalog["palettes"] = _compact_palettes(catalog["palettes"])
    catalog["games"] = sorted(set(catalog["games"]))
    return catalog


def _asset_world_scale(asset: dict[str, Any]) -> dict[str, Any] | None:
    if asset["usage"]["total"] <= 0:
        return {
            "status": "appearance_only",
            "provenance": "DERIVED",
            "basis": "no original-map placements; world scale is not claimed",
        }
    try:
        from .player_space import material_player_scale
        payload = material_player_scale(asset, game=asset.get("game"))
    except Exception:
        return None
    payload["provenance"] = "DERIVED"
    return payload


def select_representatives(
    occurrences: list[dict[str, Any]], *, limit: int = REPRESENTATIVE_LIMIT,
) -> list[dict[str, Any]]:
    """Deterministic diverse sample. Each kept occurrence records why it was kept."""
    if not occurrences:
        return []
    indexed: dict[tuple, dict[str, Any]] = {}

    def take(item: dict[str, Any], reason: str) -> None:
        key = (item["map"], item["object"], item["kind"])
        if key in indexed:
            reasons = indexed[key].setdefault("selected_because", [])
            if reason not in reasons:
                reasons.append(reason)
            return
        if len(indexed) >= limit:
            return
        copy = dict(item)
        copy["selected_because"] = [reason]
        indexed[key] = copy

    if len(occurrences) <= limit:
        for item in occurrences:
            take(item, "complete_sample")
        return sorted(indexed.values(), key=lambda item: (item["map"], item["kind"], item["object"]))

    kinds = sorted({item["kind"] for item in occurrences})
    maps = sorted({item["map"] for item in occurrences})
    for kind in kinds:
        match = next((item for item in occurrences if item["kind"] == kind), None)
        if match:
            take(match, f"placement_kind:{kind}")
    for map_name in maps:
        match = next((item for item in occurrences if item["map"] == map_name), None)
        if match:
            take(match, f"map_diversity:{map_name}")
    for name, predicate in (
        ("masked", lambda item: item["masked"]),
        ("translucent", lambda item: item["translucent"]),
        ("mechanism", lambda item: item["mechanism"]),
        ("moving_sector", lambda item: item["moving_sector"]),
        ("one_sided", lambda item: item["one_sided"]),
    ):
        match = next((item for item in occurrences if predicate(item)), None)
        if match:
            take(match, name)
    widths = sorted(int(item["geometry"].get("x_repeat") or 0) for item in occurrences)
    median = widths[len(widths) // 2] if widths else 0
    typical = min(occurrences, key=lambda item: abs(int(item["geometry"].get("x_repeat") or 0) - median))
    take(typical, "typical_repeat")
    rare = max(occurrences, key=lambda item: abs(int(item["geometry"].get("x_repeat") or 0) - median))
    take(rare, "outlier_repeat")
    seen_neighbors: set[tuple] = set()
    for item in occurrences:
        neighbors = tuple(item.get("neighbors") or [])
        if neighbors and neighbors not in seen_neighbors:
            take(item, "different_neighbor_palette")
            seen_neighbors.add(neighbors)
    for item in occurrences:
        take(item, "fill")
    return sorted(indexed.values(), key=lambda item: (item["map"], item["kind"], item["object"]))


def discover_clusters(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    assets = catalog["assets"]
    animated = {
        member
        for family in catalog.get("animation_families") or []
        for member in family.get("members") or []
    }
    active = sorted(
        ident for ident, asset in assets.items()
        if asset["usage"]["total"] > 0 or ident in animated or asset.get("status") in {"unused", "appearance_only"}
    )
    # Full unused ART sets are large; keep visual grouping on used/animated tiles
    # plus unused tiles only when the catalog is still a small fixture.
    visual_ids = active if len(assets) <= 256 else sorted(
        ident for ident in active if assets[ident]["usage"]["total"] > 0 or ident in animated
    )
    usage_ids = sorted(ident for ident in active if assets[ident]["usage"]["total"] > 0)
    visual_links: list[tuple[str, str]] = []
    usage_links: list[tuple[str, str]] = []
    features = {
        ident: tuple(asset["appearance"]["feature"])
        for ident, asset in assets.items()
        if asset.get("appearance") and asset["appearance"].get("feature")
    }
    usage = {ident: _usage_vector(asset["usage"]) for ident, asset in assets.items()}
    for index, left in enumerate(visual_ids):
        for right in visual_ids[index + 1:]:
            if left in features and right in features:
                if feature_distance(features[left], features[right]) <= VISUAL_CLUSTER_THRESHOLD:
                    visual_links.append((left, right))
    for index, left in enumerate(usage_ids):
        for right in usage_ids[index + 1:]:
            if _cosine(usage[left], usage[right]) >= 1.0 - USAGE_CLUSTER_THRESHOLD:
                usage_links.append((left, right))
    clusters = []
    for kind, ids, links, basis in (
        ("visual", visual_ids, visual_links, "ART feature distance; unlabeled"),
        ("usage", usage_ids, usage_links, "cosine of placement-kind usage vectors; unlabeled"),
    ):
        for number, members in enumerate(_union_find(ids, links)):
            if len(members) < 2:
                continue
            clusters.append({
                "id": f"cluster:{kind}:{number:04d}",
                "kind": kind,
                "members": members,
                "provenance": "DERIVED",
                "basis": basis,
            })
    for number, family in enumerate(catalog.get("animation_families") or []):
        members = list(family.get("members") or [])
        if len(members) >= 2:
            clusters.append({
                "id": f"cluster:animation:{number:04d}",
                "kind": "native_animation",
                "members": members,
                "provenance": "VERIFIED",
                "basis": family.get("basis", "ART picanm"),
            })
    return clusters


def mine_relations(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for ident, asset in sorted(catalog["assets"].items()):
        for other, count in asset["neighbors"].items():
            relations.append({
                "source": ident, "target": other, "kind": "observed_adjacent",
                "count": count, "provenance": "DERIVED",
                "basis": "adjacent wall picnums or floor/ceiling pairing in original maps",
            })
        for other, count in asset["floors"].items():
            if other != ident:
                relations.append({
                    "source": ident, "target": other, "kind": "observed_with_floor",
                    "count": count, "provenance": "DERIVED",
                    "basis": "owning sector floor tile when this asset was placed",
                })
        for other, count in asset["ceilings"].items():
            if other != ident:
                relations.append({
                    "source": ident, "target": other, "kind": "observed_with_ceiling",
                    "count": count, "provenance": "DERIVED",
                    "basis": "owning sector ceiling tile when this asset was placed",
                })
    for family in catalog.get("animation_families") or []:
        members = list(family.get("members") or [])
        for left, right in zip(members, members[1:]):
            relations.append({
                "source": left, "target": right, "kind": "native_animation_frame",
                "count": 1, "provenance": "VERIFIED",
                "basis": family.get("basis", "ART picanm"),
            })
    return relations


def _compact_palettes(palettes: list[dict[str, Any]], *, per_map: int = 24) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in palettes:
        grouped[item["map"]].append(item)
    result = []
    for map_name in sorted(grouped):
        ranked = sorted(grouped[map_name], key=lambda item: (-item["sector_count"], item["id"]))
        result.extend(ranked[:per_map])
    return result


def summarize_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    assets = catalog["assets"]
    substantial = [
        asset for asset in assets.values()
        if asset["usage"]["total"] >= 3 or asset["usage"]["maps"] >= 2
    ]
    statuses = Counter(asset["status"] for asset in assets.values())
    by_game = Counter(asset["game"] for asset in assets.values())
    return {
        "schema_version": catalog["schema_version"],
        "games": catalog["games"],
        "maps_mined": len(catalog["maps_mined"]),
        "assets": len(assets),
        "assets_by_game": dict(by_game),
        "substantial_usage": len(substantial),
        "with_appearance": sum(1 for asset in assets.values() if asset.get("appearance")),
        "clusters": len(catalog["clusters"]),
        "relations": len(catalog["relations"]),
        "palettes": len(catalog["palettes"]),
        "animation_families": len(catalog["animation_families"]),
        "statuses": dict(statuses),
        "annotations": len(catalog.get("annotations") or {}),
        "contradictions": len(catalog.get("contradictions") or []),
        "ontology_status": (catalog.get("ontology") or {}).get("status", "empty"),
        "ontology_facets": [facet["id"] for facet in (catalog.get("ontology") or {}).get("facets", [])],
    }


def export_classification_batch(
    catalog: dict[str, Any],
    *,
    tiles: dict[str, dict[int, ArtTile]] | None = None,
    palettes: dict[str, tuple[tuple[int, int, int], ...]] | None = None,
    limit: int = 80,
    include_previews: bool = True,
) -> dict[str, Any]:
    sample_ids = select_review_sample(catalog, limit=limit)
    sample = []
    for ident in sample_ids:
        asset = catalog["assets"][ident]
        entry = {
            "id": asset["id"],
            "game": asset["game"],
            "native_id": asset["native_id"],
            "usage": asset["usage"],
            "status": asset["status"],
            "identity": asset["identity"],
            "review_bucket": asset.get("review_bucket"),
            "world_scale": asset.get("world_scale"),
            "appearance": None if not asset.get("appearance") else {
                key: value for key, value in asset["appearance"].items() if key != "feature"
            },
            "representatives": asset["representatives"],
            "neighbors": asset["neighbors"],
            "floors": asset["floors"],
            "ceilings": asset["ceilings"],
            "clusters": [
                cluster["id"] for cluster in catalog["clusters"]
                if asset["id"] in cluster["members"]
            ],
        }
        if include_previews and tiles and palettes:
            game_tiles = tiles.get(asset["game"])
            palette = palettes.get(asset["game"])
            if game_tiles and palette and asset["native_kind"] == "tile":
                tile = game_tiles.get(int(asset["native_id"]))
                if tile:
                    png = tile_preview_png(tile, palette)
                    entry["asset_preview_png_base64"] = base64.b64encode(png).decode("ascii")
        sample.append(entry)
    return {
        "$schema": BATCH_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "instruction": (
            "Propose independent annotation facets that help describe and predict "
            "how these assets are used. Do not force a single category. Do not treat "
            "numeric tile adjacency as meaning. Unknown is allowed. Return facets first, "
            "then optional per-asset INTERPRETED values. Parameters may name a facet or "
            "threshold; they must not supply truth values such as is_floor=true. "
            "Unused/appearance_only assets may receive visual similarity only; do not "
            "claim how they are normally used."
        ),
        "forbidden_parameter_keys": sorted(RESERVED_TRUTH_KEYS),
        "clusters": catalog["clusters"],
        "animation_families": catalog["animation_families"],
        "assets": sample,
    }


def select_review_sample(catalog: dict[str, Any], *, limit: int = 80) -> list[str]:
    """Stratified review set: usage, mixed, masked, sprites, animation, mechanisms, unused."""
    assets = catalog["assets"]
    animated = {
        member
        for family in catalog.get("animation_families") or []
        for member in family.get("members") or []
    }
    buckets: dict[str, list[str]] = {
        "high_usage": [],
        "mixed_use": [],
        "masked": [],
        "sprite_only": [],
        "animation": [],
        "mechanism": [],
        "ceiling": [],
        "floor": [],
        "appearance_only": [],
        "ambiguous_tall_as_floor": [],
    }
    ranked = sorted(assets.values(), key=lambda asset: (-asset["usage"]["total"], asset["id"]))
    for asset in ranked:
        ident = asset["id"]
        usage = asset["usage"]
        total = usage["total"]
        if total == 0:
            if asset.get("appearance") and len(buckets["appearance_only"]) < max(8, limit // 10):
                buckets["appearance_only"].append(ident)
            continue
        if ident in animated:
            buckets["animation"].append(ident)
        if asset["status"] == "mixed_use":
            buckets["mixed_use"].append(ident)
        if usage["masked"] / total >= 0.4:
            buckets["masked"].append(ident)
        spriteish = (usage.get("sprite", 0) + usage.get("decal", 0)) / total
        if spriteish >= 0.85 and usage["wall"] + usage["floor"] + usage["ceiling"] == 0:
            buckets["sprite_only"].append(ident)
        if usage["mechanism"] / total >= 0.25:
            buckets["mechanism"].append(ident)
        if usage["ceiling"] / total >= 0.7:
            buckets["ceiling"].append(ident)
        if usage["floor"] / total >= 0.7:
            buckets["floor"].append(ident)
        height = (asset.get("identity") or {}).get("height") or 0
        if usage["floor"] / total >= 0.6 and int(height) >= 64:
            buckets["ambiguous_tall_as_floor"].append(ident)
        if usage["wall"] + usage["overwall"] >= usage["floor"] + usage["ceiling"]:
            buckets["high_usage"].append(ident)
    order = (
        "high_usage", "mixed_use", "masked", "sprite_only", "animation",
        "mechanism", "ceiling", "floor", "ambiguous_tall_as_floor", "appearance_only",
    )
    per = max(4, limit // len(order))
    selected: list[str] = []
    seen: set[str] = set()
    for bucket in order:
        for ident in buckets[bucket][:per]:
            if ident in seen:
                continue
            assets[ident]["review_bucket"] = bucket
            selected.append(ident)
            seen.add(ident)
            if len(selected) >= limit:
                return selected
    for asset in ranked:
        if asset["id"] not in seen and asset["usage"]["total"] > 0:
            selected.append(asset["id"])
            seen.add(asset["id"])
            if len(selected) >= limit:
                break
    return selected


def import_ontology(catalog: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") not in {None, SCHEMA_VERSION, 1}:
        raise MaterialsError(f"unsupported ontology schema_version {payload.get('schema_version')}")
    previous = catalog.get("ontology")
    if previous and previous.get("status") not in {None, "empty"}:
        history = catalog.setdefault("ontology_history", [])
        history.append(previous)
    facets = []
    for facet in payload.get("facets") or []:
        ident = str(facet.get("id") or "").strip()
        if not ident:
            raise MaterialsError("ontology facet is missing id")
        if ident.lower() in RESERVED_TRUTH_KEYS:
            raise MaterialsError(f"facet id {ident} looks like a supplied truth value")
        values = []
        for value in facet.get("values") or []:
            if isinstance(value, dict):
                name = str(value.get("id") or value.get("label") or "").strip()
            else:
                name = str(value).strip()
            if not name:
                continue
            if name.lower() in {"true", "false"}:
                raise MaterialsError(f"facet {ident} value {name} is a truth value, not a label")
            values.append(name)
        facets.append({
            "id": ident,
            "label": str(facet.get("label") or ident),
            "values": values,
            "basis": str(facet.get("basis") or "imported proposal"),
            "useful_for": list(facet.get("useful_for") or []),
            "provenance": "INTERPRETED",
        })
    families = []
    for family in payload.get("families") or []:
        ident = str(family.get("id") or "").strip()
        if not ident:
            continue
        families.append({
            "id": ident,
            "kind": str(family.get("kind") or "reviewed"),
            "members": [str(member) for member in (family.get("members") or [])],
            "roles": dict(family.get("roles") or {}),
            "transitions": list(family.get("transitions") or []),
            "basis": str(family.get("basis") or "imported family"),
            "provenance": "INTERPRETED",
        })
    catalog["ontology"] = {
        "$schema": ONTOLOGY_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "status": str(payload.get("status") or ("proposed" if facets else "empty")),
        "version": str(payload.get("version") or "v1"),
        "facets": facets,
        "families": families,
        "basis": str(payload.get("basis") or "imported classification-batch review"),
        "useful_for": list(payload.get("useful_for") or []),
        "rejected_distinctions": list(payload.get("rejected_distinctions") or []),
        "revision_of": payload.get("revision_of"),
        "revision_notes": list(payload.get("revision_notes") or []),
    }
    return catalog["ontology"]


def import_annotations(catalog: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    ontology = catalog.get("ontology") or empty_ontology()
    facet_values = {facet["id"]: set(facet["values"]) for facet in ontology.get("facets") or []}
    if payload.get("ontology"):
        import_ontology(catalog, payload["ontology"])
        ontology = catalog["ontology"]
        facet_values = {facet["id"]: set(facet["values"]) for facet in ontology.get("facets") or []}
    elif payload.get("facets"):
        import_ontology(catalog, payload)
        ontology = catalog["ontology"]
        facet_values = {facet["id"]: set(facet["values"]) for facet in ontology.get("facets") or []}
    annotations = catalog.setdefault("annotations", {})
    for item in payload.get("annotations") or []:
        ident = str(item.get("asset") or item.get("id") or "")
        if ident not in catalog["assets"]:
            raise MaterialsError(f"annotation refers to unknown asset {ident}")
        provenance = str(item.get("provenance") or "INTERPRETED").upper()
        if provenance not in PROVENANCE:
            raise MaterialsError(f"invalid provenance {provenance}")
        if provenance == "VERIFIED":
            raise MaterialsError("imported semantic labels cannot be VERIFIED; use INTERPRETED or DERIVED")
        values = item.get("values") or item.get("facets") or {}
        if any(key in RESERVED_TRUTH_KEYS or str(key).endswith("_valid") for key in values):
            raise MaterialsError("annotation parameters may not supply truth values")
        cleaned: dict[str, Any] = {}
        for facet, value in values.items():
            if facet not in facet_values:
                raise MaterialsError(f"annotation uses unknown facet {facet}")
            label = value if isinstance(value, str) else str(value.get("value") if isinstance(value, dict) else value)
            if facet_values[facet] and label not in facet_values[facet] and label not in {"unknown", "ambiguous", "mixed_use"}:
                raise MaterialsError(f"value {label} is not in facet {facet}")
            cleaned[facet] = {
                "value": label,
                "confidence": float(item.get("confidence") or (value.get("confidence") if isinstance(value, dict) else 0.5) or 0.5),
                "basis": str(item.get("basis") or (value.get("basis") if isinstance(value, dict) else "imported")),
                "supporting": list(item.get("supporting") or []),
                "contradicting": list(item.get("contradicting") or []),
            }
        status = str(item.get("status") or "annotated")
        if status not in {"annotated", "unknown", "ambiguous", "mixed_use", "appearance_only"}:
            status = "annotated"
        annotations[ident] = {
            "asset": ident,
            "provenance": provenance,
            "status": status,
            "values": cleaned,
            "basis": str(item.get("basis") or "imported classification"),
        }
        catalog["assets"][ident]["status"] = status
    catalog["contradictions"] = detect_contradictions(catalog)
    return catalog


def detect_contradictions(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    contradictions = []
    annotations = catalog.get("annotations") or {}
    for ident, note in annotations.items():
        asset = catalog["assets"][ident]
        usage = asset["usage"]
        total = usage["total"] or 1
        values = note.get("values") or {}
        for facet, payload in values.items():
            label = str(payload["value"]).lower()
            if "floor" in label and usage["floor"] == 0 and usage["wall"] + usage["ceiling"] > 0:
                contradictions.append(_contradiction(
                    ident, facet, payload["value"],
                    "classified with a floor-like label but never used on floors",
                    {"floor": usage["floor"], "wall": usage["wall"], "ceiling": usage["ceiling"]},
                ))
            if "wall" in label and usage["wall"] + usage["overwall"] == 0 and usage["floor"] > 0:
                contradictions.append(_contradiction(
                    ident, facet, payload["value"],
                    "classified with a wall-like label but never used on walls",
                    {"wall": usage["wall"], "floor": usage["floor"]},
                ))
            if facet == "surface_applicability" and label == "vertical":
                if usage["wall"] + usage["overwall"] == 0 and usage["ceiling"] + usage["floor"] > 0:
                    contradictions.append(_contradiction(
                        ident, facet, payload["value"],
                        "classified vertical but original-map usage is never a wall",
                        {"wall": usage["wall"], "overwall": usage["overwall"],
                         "floor": usage["floor"], "ceiling": usage["ceiling"]},
                    ))
            if facet == "surface_applicability" and "floor" in label and usage["floor"] == 0 and usage["total"]:
                contradictions.append(_contradiction(
                    ident, facet, payload["value"],
                    "classified as floor-applicable but never used on floors",
                    {"floor": 0, "total": usage["total"]},
                ))
            if facet == "surface_applicability" and (
                "ceiling" in label or "sky" in label
            ) and usage["ceiling"] == 0 and usage["total"]:
                contradictions.append(_contradiction(
                    ident, facet, payload["value"],
                    "classified as ceiling/sky-applicable but never used on ceilings",
                    {"ceiling": 0, "total": usage["total"]},
                ))
            if facet == "placement_kind" and label == "sprite":
                if usage["sprite"] + usage.get("decal", 0) == 0 and usage["wall"] + usage["floor"] + usage["ceiling"] > 0:
                    contradictions.append(_contradiction(
                        ident, facet, payload["value"],
                        "classified as sprite placement but corpus usage is on surfaces",
                        {"sprite": usage["sprite"], "wall": usage["wall"]},
                    ))
            if facet == "placement_kind" and label == "surface":
                if usage["wall"] + usage["overwall"] + usage["floor"] + usage["ceiling"] == 0 and usage["sprite"] > 0:
                    contradictions.append(_contradiction(
                        ident, facet, payload["value"],
                        "classified as a surface but corpus usage is sprite-only",
                        {"sprite": usage["sprite"], "wall": usage["wall"]},
                    ))
            if "opaque" in label and usage["masked"] / total >= 0.5:
                contradictions.append(_contradiction(
                    ident, facet, payload["value"],
                    "classified opaque but majority of placements are masked",
                    {"masked": usage["masked"], "total": usage["total"]},
                ))
            if (
                ( "generic" in label and "wall" in label)
                or (facet == "architectural_role" and label == "structural_fill")
            ) and usage["masked"] / total >= 0.7:
                contradictions.append(_contradiction(
                    ident, facet, payload["value"],
                    "classified as a generic/structural fill but overwhelmingly masked",
                    {"masked": usage["masked"], "total": usage["total"]},
                ))
            if facet == "architectural_role" and "sky" in label:
                if usage["ceiling"] / total < 0.8 and usage["total"]:
                    contradictions.append(_contradiction(
                        ident, facet, payload["value"],
                        "classified as a sky sheet but not ceiling-dominant",
                        {"ceiling": usage["ceiling"], "total": usage["total"]},
                    ))
            if facet == "architectural_role" and "separator" in label and usage["masked"] / total < 0.3 and usage["total"]:
                contradictions.append(_contradiction(
                    ident, facet, payload["value"],
                    "classified as a masked separator but masked share is low",
                    {"masked": usage["masked"], "total": usage["total"]},
                ))
            if "door" in label and usage["mechanism"] == 0 and usage["static"] / total >= 0.9:
                contradictions.append(_contradiction(
                    ident, facet, payload["value"],
                    "classified as door-like but corpus placements are almost all static",
                    {"mechanism": usage["mechanism"], "static": usage["static"]},
                ))
            if usage["total"] == 0 and note.get("status") == "annotated" and any(
                token in label for token in (
                    "wall", "floor", "ceiling", "door", "vertical", "horizontal",
                    "sky", "separator", "fill", "surface",
                )
            ):
                contradictions.append(_contradiction(
                    ident, facet, payload["value"],
                    "confident usage claim on an appearance-only asset with no original-map placements",
                    {"total": 0, "status": asset.get("status")},
                ))
        if note.get("status") == "annotated" and payload_ambiguous(usage):
            contradictions.append(_contradiction(
                ident, "status", note.get("status"),
                "confident annotation on an asset whose usage is mixed across surfaces",
                {key: usage[key] for key in ("wall", "floor", "ceiling", "total")},
            ))
    members_by_cluster = {
        cluster["id"]: cluster["members"] for cluster in catalog.get("clusters") or []
        if cluster["kind"] == "visual"
    }
    for cluster_id, members in members_by_cluster.items():
        vectors = [_usage_vector(catalog["assets"][item]["usage"]) for item in members if catalog["assets"][item]["usage"]["total"]]
        if len(vectors) >= 2:
            worst = min(
                (_cosine(vectors[i], vectors[j]) for i in range(len(vectors)) for j in range(i + 1, len(vectors))),
                default=1.0,
            )
            if worst < 0.35:
                contradictions.append({
                    "asset": members[0],
                    "cluster": cluster_id,
                    "facet": None,
                    "value": None,
                    "reason": "visual cluster members have dissimilar corpus usage",
                    "evidence": {"members": members, "min_usage_cosine": round(worst, 4)},
                    "provenance": "DERIVED",
                })
    return contradictions


def payload_ambiguous(usage: dict[str, int]) -> bool:
    total = usage.get("total") or 1
    wallish = (usage.get("wall", 0) + usage.get("overwall", 0)) / total
    return sum(
        value >= 0.2
        for value in (wallish, usage.get("floor", 0) / total, usage.get("ceiling", 0) / total)
    ) >= 2


def _contradiction(asset: str, facet: str | None, value: Any, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset": asset, "facet": facet, "value": value, "reason": reason,
        "evidence": evidence, "provenance": "DERIVED",
    }


def rank_candidates(
    source: dict[str, Any],
    targets: Iterable[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Rank target assets by usage signature, then appearance, never by raw ID."""
    source_usage = _usage_vector(source["usage"])
    source_feature = tuple(source["appearance"]["feature"]) if source.get("appearance") else None
    ranked = []
    for target in targets:
        if target["id"] == source["id"]:
            continue
        usage_score = _cosine(source_usage, _usage_vector(target["usage"]))
        visual = None
        if source_feature and target.get("appearance"):
            visual = feature_distance(source_feature, tuple(target["appearance"]["feature"]))
        # Usage agreement first: a floor-like source should not prefer a wall-only lookalike.
        score = (1.0 - usage_score) * 4.0 + (visual if visual is not None else 1.5)
        ranked.append({
            "asset": target["id"],
            "game": target["game"],
            "score": round(score, 6),
            "usage_cosine": round(usage_score, 6),
            "visual_distance": None if visual is None else round(visual, 6),
            "status": target["status"],
            "basis": "usage-signature then ART feature; native IDs are not semantics",
        })
    ranked.sort(key=lambda item: (item["score"], item["asset"]))
    return ranked[:limit]


def retrieve_palette(catalog: dict[str, Any], *, like: str | None = None, map_name: str | None = None) -> list[dict[str, Any]]:
    palettes = catalog.get("palettes") or []
    if map_name:
        palettes = [item for item in palettes if item["map"] == map_name]
    if like:
        wanted = {like}
        asset = catalog["assets"].get(like)
        if asset:
            wanted.update(asset.get("neighbors") or {})
        palettes = [
            item for item in palettes
            if like in {item["floor"], item["ceiling"], *item["walls"]} or wanted & set(item["walls"])
        ]
    return sorted(palettes, key=lambda item: (-item["sector_count"], item["id"]))


def palette_vocabulary(catalog: dict[str, Any], asset_ids: Iterable[str]) -> dict[str, Any]:
    """Describe a local asset set using imported facet values only."""
    annotations = catalog.get("annotations") or {}
    counts: Counter[tuple[str, str]] = Counter()
    known = []
    unknown = []
    for ident in asset_ids:
        ident = str(ident)
        note = annotations.get(ident)
        if not note:
            unknown.append(ident)
            continue
        known.append(ident)
        for facet, payload in (note.get("values") or {}).items():
            counts[(facet, str(payload["value"]))] += 1
    return {
        "assets": list(asset_ids),
        "annotated": known,
        "unannotated": unknown,
        "facet_counts": [
            {"facet": facet, "value": value, "count": count}
            for (facet, value), count in counts.most_common()
        ],
        "provenance": "INTERPRETED",
        "basis": "imported facet values over the supplied local assets",
    }


def similar_palettes(
    catalog: dict[str, Any],
    asset_ids: Iterable[str],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Find original-map palettes that overlap a local asset set."""
    wanted = {str(ident) for ident in asset_ids}
    scored = []
    for palette in catalog.get("palettes") or []:
        members = {palette["floor"], palette["ceiling"], *palette["walls"]}
        overlap = wanted & members
        if not overlap:
            continue
        scored.append({
            "id": palette["id"],
            "map": palette["map"],
            "sector_count": palette["sector_count"],
            "overlap": sorted(overlap),
            "overlap_count": len(overlap),
            "floor": palette["floor"],
            "ceiling": palette["ceiling"],
            "walls": palette["walls"],
            "provenance": "DERIVED",
        })
    scored.sort(key=lambda item: (-item["overlap_count"], -item["sector_count"], item["id"]))
    return scored[:limit]


def usage_prediction_heldout(catalog: dict[str, Any]) -> dict[str, Any]:
    """Hide each asset's dominant surface and see whether peers predict it."""
    assets = [asset for asset in catalog["assets"].values() if asset["usage"]["total"] >= 2]
    correct = 0
    total = 0
    for asset in assets:
        observed = max(("wall", "floor", "ceiling"), key=lambda key: asset["usage"][key])
        peers = rank_candidates(asset, assets, limit=3)
        if not peers:
            continue
        votes = Counter()
        for peer in peers:
            other = catalog["assets"][peer["asset"]]
            votes[max(("wall", "floor", "ceiling"), key=lambda key: other["usage"][key])] += 1
        predicted, _count = votes.most_common(1)[0]
        total += 1
        correct += int(predicted == observed)
    return {
        "experiment": "usage_prediction",
        "assets": total,
        "correct": correct,
        "accuracy": None if not total else round(correct / total, 4),
        "basis": "dominant surface of nearest usage/appearance peers",
    }


def contact_sheet_html(
    catalog: dict[str, Any],
    *,
    tiles: dict[str, dict[int, ArtTile]] | None = None,
    palettes: dict[str, tuple[tuple[int, int, int], ...]] | None = None,
    cluster_id: str | None = None,
    title: str = "Material evidence",
) -> str:
    clusters = catalog.get("clusters") or []
    if cluster_id:
        clusters = [item for item in clusters if item["id"] == cluster_id]
    annotations = catalog.get("annotations") or {}
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>",
        _escape(title),
        "</title><style>body{font-family:sans-serif;background:#111;color:#eee}",
        "figure{display:inline-block;margin:8px;width:140px;vertical-align:top}",
        "img{width:128px;height:128px;image-rendering:pixelated;background:#000}",
        "h2{margin-top:2em} .meta{font-size:12px;color:#bbb}</style></head><body>",
        f"<h1>{_escape(title)}</h1>",
        f"<p>schema {catalog.get('schema_version')} · ontology { _escape((catalog.get('ontology') or {}).get('status', 'empty')) }</p>",
    ]
    for cluster in clusters[:40]:
        parts.append(f"<h2>{_escape(cluster['id'])} <span class='meta'>{_escape(cluster['kind'])} · { _escape(cluster['provenance']) }</span></h2>")
        parts.append(f"<p class='meta'>{_escape(cluster.get('basis', ''))}</p>")
        for ident in cluster["members"]:
            asset = catalog["assets"][ident]
            note = annotations.get(ident, {})
            img = ""
            if tiles and palettes and asset["native_kind"] == "tile":
                game_tiles, palette = tiles.get(asset["game"]), palettes.get(asset["game"])
                if game_tiles and palette and int(asset["native_id"]) in game_tiles:
                    png = tile_preview_png(game_tiles[int(asset["native_id"])], palette)
                    img = f"<img src='data:image/png;base64,{base64.b64encode(png).decode('ascii')}' alt='{_escape(ident)}'>"
            values = ", ".join(
                f"{key}={payload['value']}" for key, payload in (note.get("values") or {}).items()
            ) or asset["status"]
            parts.append(
                "<figure>"
                + img
                + f"<figcaption><strong>{_escape(ident)}</strong><br>"
                + f"w{asset['usage']['wall']} f{asset['usage']['floor']} c{asset['usage']['ceiling']} "
                + f"m{asset['usage']['masked']}<br>{_escape(values)}</figcaption></figure>"
            )
    parts.append("</body></html>")
    return "".join(parts)


def _escape(value: Any) -> str:
    return (
        str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def mine_map_directory(
    directory: str | Path,
    *,
    game: str,
    catalog: dict[str, Any] | None = None,
    art_directory: str | Path | None = None,
    palette_path: str | Path | None = None,
) -> dict[str, Any]:
    catalog = catalog or new_catalog(games=[game])
    root = Path(directory)
    paths = sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() == ".map")
    if not paths:
        raise MaterialsError(f"no MAP files in {directory}")
    tiles = None
    palette = None
    if art_directory:
        tiles = read_art_directory(art_directory)
        if not palette_path:
            raise MaterialsError("palette_path is required when ART is supplied")
        palette = read_palette(palette_path)
        attach_appearance(catalog, game, tiles, palette, source=str(art_directory))
    for path in paths:
        if game == "blood":
            mine_blood_map(catalog, read_map(path), map_name=path.name)
        elif game == "duke3d":
            from .duke import read_duke_map
            mine_duke_map(catalog, read_duke_map(path), map_name=path.name)
        else:
            raise MaterialsError(f"map directory mining does not support game {game}")
    return finalize_catalog(catalog)


def mine_doom_wad(
    wad_path: str | Path,
    *,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .doom import read_wad

    catalog = catalog or new_catalog(games=["doom"])
    wad = read_wad(wad_path)
    for level in wad.maps:
        if level.supported:
            mine_doom_map(catalog, level, map_name=level.name)
    return finalize_catalog(catalog)


def default_palette_path(art_directory: str | Path, game: str) -> Path | None:
    root = Path(art_directory)
    names = {
        "blood": root / "xmapedit" / "palettes" / "import" / "BLOOD.PAL",
        "duke3d": root / "xmapedit" / "palettes" / "import" / "DUKE3D.PAL",
    }
    path = names.get(game)
    return path if path and path.exists() else None


def families_from_evidence(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Named families exist only after an imported ontology; otherwise clusters stay unlabeled."""
    annotations = catalog.get("annotations") or {}
    ontology = catalog.get("ontology") or {}
    reviewed = list((ontology.get("families") or []))
    if ontology.get("status") in {None, "empty"} or not annotations:
        return reviewed + [
            {
                "id": cluster["id"],
                "kind": "unlabeled_cluster",
                "members": cluster["members"],
                "provenance": cluster["provenance"],
                "basis": cluster.get("basis"),
            }
            for cluster in catalog.get("clusters") or []
        ]
    grouped: dict[tuple, list[str]] = defaultdict(list)
    for ident, note in annotations.items():
        key = tuple(sorted((facet, payload["value"]) for facet, payload in (note.get("values") or {}).items()))
        if key:
            grouped[key].append(ident)
    families = list(reviewed)
    for number, (key, members) in enumerate(sorted(grouped.items())):
        if len(members) < 2:
            continue
        families.append({
            "id": f"family:{number:04d}",
            "kind": "interpreted_facet_bundle",
            "members": sorted(members),
            "facets": dict(key),
            "provenance": "INTERPRETED",
            "basis": "shared imported facet values; not a native family",
        })
    families.extend(
        {
            "id": family["id"],
            "kind": "native_animation",
            "members": family["members"],
            "provenance": "VERIFIED",
            "basis": family.get("basis"),
            "states": _animation_states(catalog, family["members"]),
        }
        for family in catalog.get("animation_families") or []
    )
    families.extend(_cooccurrence_families(catalog))
    return families


def _animation_states(catalog: dict[str, Any], members: list[str]) -> list[dict[str, Any]]:
    states = []
    for index, ident in enumerate(members):
        asset = catalog["assets"].get(ident)
        if not asset:
            continue
        usage = asset["usage"]
        states.append({
            "asset": ident,
            "index": index,
            "mechanism_share": None if not usage["total"] else round(usage["mechanism"] / usage["total"], 4),
            "provenance": "VERIFIED" if usage["total"] else "DERIVED",
            "basis": "native animation frame order; mechanism share is corpus evidence",
        })
    return states


def _cooccurrence_families(catalog: dict[str, Any], *, min_count: int = 8) -> list[dict[str, Any]]:
    """Small unlabeled families from repeated wall/floor/ceiling adjacency, not visual clusters."""
    pairs: Counter[tuple[str, str, str]] = Counter()
    for ident, asset in catalog["assets"].items():
        for other, count in (asset.get("floors") or {}).items():
            if other != ident and count >= min_count:
                pairs[("with_floor", ident, other)] += int(count)
        for other, count in (asset.get("ceilings") or {}).items():
            if other != ident and count >= min_count:
                pairs[("with_ceiling", ident, other)] += int(count)
    families = []
    for number, ((kind, left, right), count) in enumerate(sorted(pairs.items(), key=lambda item: (-item[1], item[0]))[:40]):
        families.append({
            "id": f"family:cooccur:{number:04d}",
            "kind": "cooccurrence",
            "members": [left, right],
            "relation": kind,
            "count": count,
            "provenance": "DERIVED",
            "basis": "repeated floor/ceiling pairing in original maps; roles are not assigned",
        })
    return families


def query_materials(
    catalog: dict[str, Any],
    *,
    like: str | None = None,
    require: dict[str, str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Ontology-aware retrieval. `require` keys must be facets that were actually imported."""
    ontology = catalog.get("ontology") or {}
    known = {facet["id"] for facet in ontology.get("facets") or []}
    require = require or {}
    unknown = sorted(key for key in require if key not in known)
    if unknown:
        raise MaterialsError(f"query uses facets not in the imported ontology: {unknown}")
    annotations = catalog.get("annotations") or {}
    pool = []
    for ident, asset in catalog["assets"].items():
        if asset["usage"]["total"] <= 0:
            continue
        note = annotations.get(ident) or {}
        values = {facet: payload["value"] for facet, payload in (note.get("values") or {}).items()}
        if any(values.get(facet) != label for facet, label in require.items()):
            continue
        pool.append(asset)
    if like:
        if like not in catalog["assets"]:
            raise MaterialsError(f"unknown asset {like}")
        ranked = rank_candidates(catalog["assets"][like], pool, limit=limit)
        for item in ranked:
            item["required"] = require
        return ranked
    ranked = sorted(pool, key=lambda asset: (-asset["usage"]["total"], asset["id"]))
    return [
        {
            "asset": asset["id"],
            "game": asset["game"],
            "status": asset["status"],
            "usage_total": asset["usage"]["total"],
            "required": require,
            "basis": "ontology facet filter over corpus-backed assets",
        }
        for asset in ranked[:limit]
    ]


def render_occurrence_context_svg(disk: DiskMap, occurrence: dict[str, Any]) -> str:
    """Cropped 2D context for one representative placement. Not a 3D screenshot."""
    kind, _, ident = str(occurrence.get("object") or "sector:0").partition(":")
    index = int(ident or 0)
    owners = [-1] * len(disk.walls)
    for sector_id, sector in enumerate(disk.sectors):
        for wall_id in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count):
            if 0 <= wall_id < len(disk.walls):
                owners[wall_id] = sector_id
    sector_id = None
    wall_id = None
    sprite_id = None
    if kind == "wall":
        wall_id = index
        sector_id = owners[index] if 0 <= index < len(owners) else 0
    elif kind == "sprite":
        sprite_id = index
        if 0 <= index < len(disk.sprites):
            sector_id = disk.sprites[index].sector
    else:
        sector_id = index
    if sector_id is None or not 0 <= sector_id < len(disk.sectors):
        sector_id = 0
    sector = disk.sectors[sector_id]
    xs, ys = [], []
    for wid in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count):
        if 0 <= wid < len(disk.walls):
            xs.append(disk.walls[wid].x)
            ys.append(disk.walls[wid].y)
    if not xs:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240"/>'
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pad = max(64, int(0.25 * max(max_x - min_x, max_y - min_y, 1)))
    min_x, max_x, min_y, max_y = min_x - pad, max_x + pad, min_y - pad, max_y + pad
    width, height, margin = 480, 360, 16
    scale = min((width - 2 * margin) / max(1, max_x - min_x), (height - 2 * margin) / max(1, max_y - min_y))

    def xy(x: int, y: int) -> tuple[float, float]:
        return margin + (x - min_x) * scale, height - margin - (y - min_y) * scale

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#111318"/>',
    ]
    for wid in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count):
        if not 0 <= wid < len(disk.walls):
            continue
        wall = disk.walls[wid]
        if not 0 <= wall.point2 < len(disk.walls):
            continue
        other = disk.walls[wall.point2]
        x1, y1 = xy(wall.x, wall.y)
        x2, y2 = xy(other.x, other.y)
        highlight = wall_id == wid
        color = "#ffcc66" if highlight else ("#43a4db" if wall.next_sector >= 0 else "#d8dde6")
        stroke = 4 if highlight else 1.2
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="{stroke}"/>'
        )
    if sprite_id is not None and 0 <= sprite_id < len(disk.sprites):
        sprite = disk.sprites[sprite_id]
        x, y = xy(sprite.x, sprite.y)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#ff5f5f"/>')
    cx, cy = xy((min_x + max_x) // 2, (min_y + max_y) // 2)
    parts.append(
        f'<text x="{cx:.1f}" y="18" fill="#9aa4b2" font-family="monospace" font-size="11" '
        f'text-anchor="middle">{_escape(occurrence.get("map"))} {_escape(occurrence.get("object"))} '
        f'{_escape(occurrence.get("kind"))}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def write_review_packet(
    catalog: dict[str, Any],
    *,
    maps_directory: str | Path,
    art_tiles: dict[int, ArtTile] | None,
    palette: tuple[tuple[int, int, int], ...] | None,
    output_directory: str | Path,
    asset_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Write isolated previews plus cropped map-context SVGs for a review sample."""
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    chosen = list(asset_ids) if asset_ids is not None else select_review_sample(catalog, limit=48)
    written = []
    for ident in chosen:
        asset = catalog["assets"].get(ident)
        if not asset:
            continue
        folder = root / ident.replace(":", "_")
        folder.mkdir(parents=True, exist_ok=True)
        preview = None
        if art_tiles and palette and asset["native_kind"] == "tile":
            tile = art_tiles.get(int(asset["native_id"]))
            if tile:
                preview = folder / "preview.png"
                preview.write_bytes(tile_preview_png(tile, palette, max_size=96))
        contexts = []
        for number, occurrence in enumerate(asset.get("representatives") or []):
            map_path = Path(maps_directory) / occurrence["map"]
            if not map_path.is_file():
                continue
            svg = render_occurrence_context_svg(read_map(map_path), occurrence)
            svg_path = folder / f"context_{number}_{occurrence['kind']}.svg"
            svg_path.write_text(svg, encoding="utf-8", newline="\n")
            contexts.append({
                "path": str(svg_path),
                "occurrence": {
                    key: occurrence[key]
                    for key in ("map", "kind", "object", "masked", "mechanism", "moving_sector",
                                "translucent", "neighbors", "selected_because")
                    if key in occurrence
                },
            })
        meta = {
            "asset": ident,
            "status": asset["status"],
            "usage": asset["usage"],
            "world_scale": asset.get("world_scale"),
            "preview": None if preview is None else str(preview),
            "contexts": contexts,
            "basis": "isolated ART preview plus cropped 2D map context; not a 3D renderer screenshot",
        }
        (folder / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(ident)
    index = {"assets": written, "directory": str(root)}
    (root / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index


def ontology_aware_match(
    catalog: dict[str, Any],
    *,
    source: dict[str, Any],
    require: dict[str, str] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Separable conversion helper: usage/ontology first, appearance second."""
    if "id" in source and source["id"] in catalog["assets"]:
        return query_materials(catalog, like=source["id"], require=require, limit=limit)
    pool = []
    annotations = catalog.get("annotations") or {}
    known = {facet["id"] for facet in (catalog.get("ontology") or {}).get("facets") or []}
    require = require or {}
    unknown = sorted(key for key in require if key not in known)
    if unknown:
        raise MaterialsError(f"query uses facets not in the imported ontology: {unknown}")
    for ident, asset in catalog["assets"].items():
        if asset["usage"]["total"] <= 0:
            continue
        values = {
            facet: payload["value"]
            for facet, payload in ((annotations.get(ident) or {}).get("values") or {}).items()
        }
        if any(values.get(facet) != label for facet, label in require.items()):
            continue
        pool.append(asset)
    return rank_candidates(source, pool, limit=limit)


def select_authoring_kit(
    catalog: dict[str, Any],
    roles: dict[str, dict[str, str]],
    *,
    limit: int = 3,
) -> dict[str, Any]:
    """Pick corpus-backed assets for named authoring roles using imported facets only."""
    kit = {"provenance": "INTERPRETED", "roles": {}}
    for role, require in roles.items():
        hits = query_materials(catalog, require=require, limit=limit)
        chosen = hits[0] if hits else None
        native = None
        if chosen:
            native = int(str(catalog["assets"][chosen["asset"]]["native_id"]))
        kit["roles"][role] = {
            "require": require,
            "candidates": hits,
            "chosen_asset": None if chosen is None else chosen["asset"],
            "chosen_tile": native,
            "basis": "highest-usage annotated asset matching imported facets",
        }
    return kit
