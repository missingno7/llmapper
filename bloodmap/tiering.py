"""Heuristic tiering of the bulk community corpus.

This module is deliberately a consumer of llmapper's existing sensors.  It
does not try to infer a room taxonomy or replace the map understanding layer:
it combines verified inventories with the independent derived measurements
from ``level_profile``, ``morphology``, ``design``, ``spatial`` and
``progression``.  The final classification is a small, explainable rule
system whose evidence is retained in the manifest.

**What a tier is.**  A tier is navigation and sampling metadata, never an
evidence weight and never ground truth about quality -- ``07_...md`` is
explicit about this, and so is ``maps/blood/README.md``.  The reference
population is the named view ``reference`` (campaign + curated) from the
corpus registry in ``patterns.py``; the candidates are the ``community``
population.  A percentile against that reference describes **unusualness, not
goodness**: absolute scale is reported and never used as a quality penalty,
and a map far from the reference may be far in a good direction.

Exact duplicate hashes are collapsed for reference statistics; geometry and
topology family keys are reported separately so related revisions can be
reviewed without deleting or silently merging their files.

**`quality_score` stays, and is navigation only** (owner decision,
2026-08-31).  It is a declared rubric with every component and penalty
exposed, which is what separates it from the confidence scalar that was
removed: it does not pretend to be a probability, and a reader can see what
produced it.  It exists to *order* a sampling queue -- look at these before
those -- and it must **never gate acceptance**.  A critic is forbidden a
single quality number, because a number that can reject a map has to be
right about quality and this one is not; a sampling aid only has to be
useful.  Anything that consumes `quality_score` to pass or fail a map is
misusing it.

There is deliberately **no confidence scalar**.  The tier decision is
rule-based and its evidence is the rule trace plus the percentile table, both
of which are in the manifest; a number like ``0.58 + 0.035 * |strong - weak|``
would read as a probability while measuring nothing.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from concurrent.futures import ProcessPoolExecutor
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .contents import explain_mechanisms, inventory_map
from .design import design_fingerprint
from .format import BloodMapError, read_map
from .level_profile import flatten, level_profile
from .morphology import MorphologyError, analyze_morphology
from .progression import analyze_progression
from .reachability import analyze_reachability, design_sectors, link_pairs, teleport_pairs


SCHEMA = "llmapper.blood-corpus-classification"
SCHEMA_VERSION = 1
CLASSIFICATIONS = ("S", "A", "B", "C", "mechanism", "bloodbath", "questionable")
QUALITY_DIMENSIONS = (
    "structural_validity", "scale_and_extent", "navigation", "lighting",
    "materials", "geometry", "gameplay_population", "progression_and_mechanisms",
)
DIMENSION_POINTS = {"strong": 100.0, "adequate": 65.0, "weak": 25.0}


def _percentile(values: Iterable[float], fraction: float) -> float | None:
    ordered = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _summary(values: Iterable[float]) -> dict[str, float | int | None]:
    ordered = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    return {
        "count": len(ordered),
        "min": _percentile(ordered, 0.0),
        "p10": _percentile(ordered, 0.10),
        "q1": _percentile(ordered, 0.25),
        "median": _percentile(ordered, 0.50),
        "q3": _percentile(ordered, 0.75),
        "p90": _percentile(ordered, 0.90),
        "max": _percentile(ordered, 1.0),
    }


def _value(item: Any) -> Any:
    if isinstance(item, dict) and "value" in item and set(item) <= {"value", "basis", "confidence"}:
        return item["value"]
    return item


def _nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return _value(current)


def _safe_ratio(numerator: float, denominator: float) -> float:
    return round(float(numerator) / max(1.0, float(denominator)), 6)


def _shade_quantiles(values: list[int]) -> dict[str, Any]:
    return {key: None if value is None else round(value, 3) for key, value in _summary(values).items()}


def lighting_metrics(disk: Any, playable: set[int]) -> dict[str, Any]:
    """Measure shade distributions and their within-space relationships.

    The existing lighting sensor is primarily an authoring pass.  Curation
    needs the observation side: whether a map has contrast, whether walls
    vary within sectors, and whether adjacent spaces make lighting decisions.
    """
    wall_shades: list[int] = []
    floor_shades: list[int] = []
    ceiling_shades: list[int] = []
    spreads: list[int] = []
    floor_by_sector: dict[int, int] = {}
    ceiling_by_sector: dict[int, int] = {}
    for sector_id in sorted(playable):
        sector = disk.sectors[sector_id].fields
        floor = int(sector["floor_shade"])
        ceiling = int(sector["ceiling_shade"])
        floor_shades.append(floor)
        ceiling_shades.append(ceiling)
        floor_by_sector[sector_id] = floor
        ceiling_by_sector[sector_id] = ceiling
        shades: list[int] = []
        first = int(sector["wall_ptr"])
        count = int(sector["wall_count"])
        for wall_id in range(first, first + count):
            if 0 <= wall_id < len(disk.walls):
                shade = int(disk.walls[wall_id].fields["shade"])
                wall_shades.append(shade)
                shades.append(shade)
        if shades:
            spreads.append(max(shades) - min(shades))

    adjacent_diffs: list[int] = []
    seen_edges: set[tuple[int, int]] = set()
    for sector_id in playable:
        first = int(disk.sectors[sector_id].fields["wall_ptr"])
        count = int(disk.sectors[sector_id].fields["wall_count"])
        for wall_id in range(first, first + count):
            if not 0 <= wall_id < len(disk.walls):
                continue
            other = int(disk.walls[wall_id].fields["next_sector"])
            edge = tuple(sorted((sector_id, other)))
            if other not in playable or edge in seen_edges:
                continue
            seen_edges.add(edge)
            adjacent_diffs.append(abs(floor_by_sector[sector_id] - floor_by_sector[other]))

    surface = wall_shades + floor_shades + ceiling_shades
    bins = Counter(int(value // 8) for value in surface)
    total = len(surface) or 1
    entropy = -sum((n / total) * math.log(n / total, 2) for n in bins.values())
    return {
        "wall_shade": _shade_quantiles(wall_shades),
        "floor_shade": _shade_quantiles(floor_shades),
        "ceiling_shade": _shade_quantiles(ceiling_shades),
        "surface_shade_range": (max(surface) - min(surface)) if surface else 0,
        "surface_shade_unique": len(set(surface)),
        "surface_shade_entropy_8unit_bins": round(entropy, 4),
        "wall_within_sector_spread": _shade_quantiles(spreads),
        "wall_flat_sector_fraction": round(sum(value <= 2 for value in spreads) / max(1, len(spreads)), 4),
        "wall_contrast_sector_fraction": round(sum(value >= 8 for value in spreads) / max(1, len(spreads)), 4),
        "adjacent_floor_shade_difference": _shade_quantiles(adjacent_diffs),
        "adjacent_contrast_fraction": round(sum(value >= 8 for value in adjacent_diffs) / max(1, len(adjacent_diffs)), 4),
    }


def _mechanism_inventory(disk: Any, contents: dict[str, Any], progression: dict[str, Any]) -> dict[str, Any]:
    explanation = explain_mechanisms(disk)
    sectors = explanation.get("sectors", [])
    walls = explanation.get("walls", [])
    sprites = explanation.get("sprites", [])
    by_kind = Counter()
    by_command = Counter()
    trigger_flags = Counter()
    for record in sectors + walls + sprites:
        kind = record.get("type_name") or record.get("category") or "unknown"
        by_kind[str(kind)] += 1
        for field in (record.get("xsector") or {}, record.get("xwall") or {}, record.get("xsprite") or {}):
            command = field.get("command_name")
            if command:
                by_command[str(command)] += 1
            for trigger in field.get("triggers") or []:
                trigger_flags[str(trigger)] += 1
    moving = Counter(str(int(sector.fields["type"])) for sector in disk.sectors if 600 <= int(sector.fields["type"]) <= 619)
    switch_count = sum(1 for sprite in disk.sprites if 20 <= int(sprite.fields["type"]) <= 23)
    generator_count = sum(1 for sprite in disk.sprites if 700 <= int(sprite.fields["type"]) <= 711)
    return {
        "object_count": len(sectors) + len(walls) + len(sprites),
        "sector_records": len(sectors),
        "wall_records": len(walls),
        "sprite_records": len(sprites),
        "switch_count": switch_count,
        "generator_or_sound_count": generator_count,
        "moving_sector_count": sum(moving.values()),
        "moving_sector_types": dict(sorted(moving.items())),
        "by_type": dict(sorted(by_kind.items())),
        "by_command": dict(sorted(by_command.items())),
        "trigger_flags": dict(sorted(trigger_flags.items())),
        "channel_count": len(contents.get("channels") or []),
        "progression_transmitter_count": progression.get("transmitter_count", 0),
        "progression_motion_receiver_count": sum(len(v) for v in (progression.get("motion_receivers") or {}).values()),
        "unresolved_count": len(explanation.get("unresolved") or []),
        "evidence_refs": [item.get("ref") for item in (sectors + walls + sprites)[:128] if item.get("ref")],
    }


def _coarse_geometry_signature(disk: Any, playable: set[int]) -> str:
    """Translation/order-insensitive geometry/topology family fingerprint."""
    areas: list[int] = []
    heights: list[int] = []
    degrees: Counter[int] = Counter()
    wall_counts: list[int] = []
    for sector_id in playable:
        sector = disk.sectors[sector_id].fields
        first, count = int(sector["wall_ptr"]), int(sector["wall_count"])
        twice_area = 0
        for wall_id in range(first, first + count):
            wall = disk.walls[wall_id].fields
            other = disk.walls[int(wall["point2"])].fields
            twice_area += int(wall["x"]) * int(other["y"]) - int(other["x"]) * int(wall["y"])
        areas.append(int(round(abs(twice_area) / 2.0 / 4096.0)))
        heights.append(int(round(abs(int(sector["floor_z"]) - int(sector["ceiling_z"])) / 256.0)))
        wall_counts.append(count)
        degrees[sum(1 for wall_id in range(first, first + count) if int(disk.walls[wall_id].fields["next_sector"]) >= 0)] += 1
    payload = {
        "sectors": len(playable),
        "areas": sorted(areas),
        "heights": sorted(heights),
        "wall_counts": sorted(wall_counts),
        "degrees": sorted(degrees.items()),
    }
    return hashlib.sha1(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def _geometry_signature(disk: Any, playable: set[int]) -> str:
    """Stronger translation-normalized geometry signature for revisions."""
    points = [
        (int(wall.fields["x"]), int(wall.fields["y"]))
        for wall in disk.walls
    ]
    min_x = min((point[0] for point in points), default=0)
    min_y = min((point[1] for point in points), default=0)
    sectors = []
    for sector_id in sorted(playable):
        sector = disk.sectors[sector_id].fields
        first, count = int(sector["wall_ptr"]), int(sector["wall_count"])
        walls = []
        for wall_id in range(first, first + count):
            wall = disk.walls[wall_id].fields
            walls.append((
                (int(wall["x"]) - min_x) // 64,
                (int(wall["y"]) - min_y) // 64,
                int(wall["point2"]) - first,
                int(wall["next_sector"]),
            ))
        sectors.append({
            "walls": walls,
            "floor_z": int(sector["floor_z"]) // 128,
            "ceiling_z": int(sector["ceiling_z"]) // 128,
        })
    return hashlib.sha1(json.dumps(sectors, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def _compact_morphology(report: dict[str, Any]) -> dict[str, Any]:
    walls, corners, sectors = report["walls"], report["corners"], report["sectors"]
    vertices = sectors.get("outer_vertex_counts") or {}
    return {
        "wall_counted": walls.get("counted", 0),
        "orthogonal_length_fraction": walls.get("orthogonal_length_fraction"),
        "diagonal_length_fraction": walls.get("diagonal_length_fraction"),
        "orientation_5deg_bins_occupied": walls.get("orientation_5deg_bins_occupied"),
        "orientation_diversity": walls.get("orientation_diversity"),
        "median_wall_length_player_widths": (walls.get("length_player_widths") or {}).get("median"),
        "corner_orthogonal_fraction": corners.get("orthogonal_fraction"),
        "chamfer_fraction": corners.get("chamfer_fraction"),
        "segmented_arc_chain_count": corners.get("segmented_arc_chain_count"),
        "rectangular_sector_fraction": sectors.get("rectangular_fraction"),
        "convex_sector_fraction": sectors.get("convex_fraction"),
        "median_outer_vertex_count": vertices.get("median"),
        "aabb_fill_median": (sectors.get("aabb_fill") or {}).get("median"),
    }


def measure_map(path: str | Path) -> dict[str, Any]:
    """Read one map and return a provenance-rich, JSON-native measurement."""
    source = Path(path)
    raw = source.read_bytes()
    record: dict[str, Any] = {
        "source_absolute": str(source.resolve()),
        "source_relative": source.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_bytes": len(raw),
        "status": "ok",
        "sensors": {},
        "sensor_errors": [],
        "family": {},
        "counts": {
            "sectors": None, "playable_sectors": None, "walls": None, "sprites": None,
            "xsectors": None, "xwalls": None, "xsprites": None,
            "validation_errors": None, "validation_warnings": None,
        },
        "player_starts": {
            "single_player": None, "multiplayer": None,
            "single_player_refs": [], "multiplayer_refs": [],
        },
        "enemy_count": None,
    }
    try:
        try:
            disk = read_map(source)
        except Exception as strict_error:
            # Preserve and classify maps whose CRC is stale, while still using
            # the parser's structural validation on their decoded records.
            disk = read_map(source, verify_crc=False)
            record["crc_read_warning"] = f"{type(strict_error).__name__}: {strict_error}"
        contents = inventory_map(disk)
        enemies = [item for item in disk.sprites if 201 <= int(item.fields["type"]) <= 253]
        record.update({
            "counts": {
                "sectors": len(disk.sectors), "playable_sectors": None,
                "walls": len(disk.walls), "sprites": len(disk.sprites),
                "xsectors": sum(obj.extra is not None for obj in disk.sectors),
                "xwalls": sum(obj.extra is not None for obj in disk.walls),
                "xsprites": sum(obj.extra is not None for obj in disk.sprites),
                "validation_errors": contents["validation"]["errors"],
                "validation_warnings": contents["validation"]["warnings"],
            },
            "player_starts": {
                "single_player": len(contents["starts"]["single_player"]),
                "multiplayer": len(contents["starts"]["multiplayer"]),
                "single_player_refs": [item["ref"] for item in contents["starts"]["single_player"]],
                "multiplayer_refs": [item["ref"] for item in contents["starts"]["multiplayer"]],
            },
            "enemy_count": len(enemies),
        })
        playable = set(design_sectors(disk))
        profile = level_profile(disk, name=source.name)
        progression = analyze_progression(disk, include_pacing=False)
        build = disk.to_build_ir()
        morphology = analyze_morphology(build)
        fingerprint = design_fingerprint(build)
        reach = analyze_reachability(disk)
        mechanisms = _mechanism_inventory(disk, contents, progression)
        starts = contents["starts"]
        record.update({
            "map_type_candidate": "singleplayer",
            "counts": {
                "sectors": len(disk.sectors),
                "playable_sectors": len(playable),
                "walls": len(disk.walls),
                "sprites": len(disk.sprites),
                "xsectors": sum(obj.extra is not None for obj in disk.sectors),
                "xwalls": sum(obj.extra is not None for obj in disk.walls),
                "xsprites": sum(obj.extra is not None for obj in disk.sprites),
                "validation_errors": contents["validation"]["errors"],
                "validation_warnings": contents["validation"]["warnings"],
            },
            "player_starts": {
                "single_player": len(starts["single_player"]),
                "multiplayer": len(starts["multiplayer"]),
                "single_player_refs": [item["ref"] for item in starts["single_player"]],
                "multiplayer_refs": [item["ref"] for item in starts["multiplayer"]],
            },
            "enemy_count": len(enemies),
            "family": {
                "coarse_geometry_topology_signature": _coarse_geometry_signature(disk, playable),
                "geometry_signature": _geometry_signature(disk, playable),
            },
            "mechanism_inventory": mechanisms,
            "topology": profile["topology"],
            "progression": {**profile["progression"], **{
                "physical_reachable_at_rest": progression["physical_reachable_at_rest"],
                "final_reachable": progression["final_reachable"],
                "final_reachable_fraction": _safe_ratio(progression["final_reachable"], len(disk.sectors)),
                "exit_reachable": progression["exit_reachable"],
                "transmitter_count": progression["transmitter_count"],
                "activated_channel_count": len(progression["channels_activated"]),
                "witness_event_count": len(progression["witness"]),
                "chain_count": len(progression["chains"]),
            }},
            "lighting": lighting_metrics(disk, playable),
            "materials": profile["materials"],
            "shape": profile["shape"],
            "geometry": profile["geometry"],
            "population": profile["population"],
            "water": profile["water"],
            "mechanisms": profile["mechanisms"],
            "morphology": _compact_morphology(morphology),
            "design_fingerprint_metrics": fingerprint["metrics"],
            "spatial_summary": {
                "used_by": "analyze_progression -> analyze_spatial",
                "physical_reachable_at_rest": progression["physical_reachable_at_rest"],
                "final_reachable": progression["final_reachable"],
                "state_dependent_portal_count": len(progression.get("motion_receivers", {})),
            },
            "sensors": {
                "contents": {
                    "counts": contents["counts"],
                    "type_counts": contents["type_counts"],
                    "pickup_categories": dict(Counter(item["category"] for item in contents["pickups"])),
                    "channels": contents["channels"],
                    "unsupported": contents["unsupported"],
                },
                "level_profile": profile,
                "morphology": _compact_morphology(morphology),
                "design_fingerprint_metrics": fingerprint["metrics"],
                "progression": {
                    "physical_reachable_at_rest": progression["physical_reachable_at_rest"],
                    "final_reachable": progression["final_reachable"],
                    "exit_reachable": progression["exit_reachable"],
                    "keys_collected": progression["keys_collected"],
                    "channels_activated": progression["channels_activated"],
                    "transmitter_count": progression["transmitter_count"],
                    "chain_count": len(progression["chains"]),
                    "witness_event_count": len(progression["witness"]),
                },
                "reachability": {
                    "start": reach.start,
                    "reached": len(reach.reached),
                    "offmap": len(reach.offmap),
                    "offmap_fraction": round(reach.offmap_fraction, 4),
                    "links": len(reach.links),
                    "teleports": len(reach.teleports),
                },
                "link_pairs": link_pairs(disk),
                "teleport_pairs": teleport_pairs(disk),
            },
        })
    except Exception as error:
        record["status"] = "sensor_error"
        record["map_type_candidate"] = "questionable/other"
        record["sensor_errors"].append(f"{type(error).__name__}: {error}")
        # The parser and contents inventory are intentionally independent of
        # the more demanding spatial/design sensors.  Keep those verified
        # facts even when a malformed wall loop or unsupported construction
        # prevents a complete derived profile.
        try:
            disk = locals().get("disk")
            if disk is None:
                disk = read_map(source, verify_crc=False)
            contents = locals().get("contents") or inventory_map(disk)
            record.setdefault("counts", {}).update({
                "sectors": len(disk.sectors), "walls": len(disk.walls), "sprites": len(disk.sprites),
                "xsectors": sum(obj.extra is not None for obj in disk.sectors),
                "xwalls": sum(obj.extra is not None for obj in disk.walls),
                "xsprites": sum(obj.extra is not None for obj in disk.sprites),
                "validation_errors": contents["validation"]["errors"],
                "validation_warnings": contents["validation"]["warnings"],
            })
            record.setdefault("player_starts", {
                "single_player": len(contents["starts"]["single_player"]),
                "multiplayer": len(contents["starts"]["multiplayer"]),
                "single_player_refs": [item["ref"] for item in contents["starts"]["single_player"]],
                "multiplayer_refs": [item["ref"] for item in contents["starts"]["multiplayer"]],
            })
            record.setdefault("enemy_count", sum(201 <= int(item.fields["type"]) <= 253 for item in disk.sprites))
        except Exception:
            record.setdefault("counts", {
                "sectors": None, "playable_sectors": None, "walls": None, "sprites": None,
                "xsectors": None, "xwalls": None, "xsprites": None,
                "validation_errors": None, "validation_warnings": None,
            })
    return record


REFERENCE_FEATURES = (
    "topology.components", "topology.loops_per_100_sectors", "topology.dead_end_fraction",
    "topology.mean_degree", "materials.dominant_wall_share", "materials.dominant_floor_share",
    "materials.floor_patch_share", "materials.ceiling_patch_share", "lighting.wall_flat_sector_fraction",
    "lighting.wall_contrast_sector_fraction", "lighting.surface_shade_range", "lighting.adjacent_contrast_fraction",
    "shape.walls_per_sector", "shape.area_iqr_ratio", "shape.height_iqr_ratio",
    "shape.distinct_floor_levels", "shape.sky_fraction", "geometry.blocking_two_sided_walls",
    "population.dudes_per_100_sectors", "population.pickups_per_100_sectors",
    "population.occupied_sector_fraction", "progression.distinct_keys", "progression.locked_objects",
    "progression.secret_marks", "mechanisms.moving_per_100_sectors", "morphology.orientation_diversity",
    "morphology.rectangular_sector_fraction", "morphology.convex_sector_fraction",
    "morphology.chamfer_fraction", "morphology.median_outer_vertex_count",
)


def _feature_value(record: dict[str, Any], key: str) -> float | None:
    parts = key.split(".")
    current: Any = record
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    if isinstance(current, dict) and "median" in current and len(current) > 1:
        current = current["median"]
    if isinstance(current, bool) or not isinstance(current, (int, float)):
        return None
    return float(current)


def _family_groups(records: list[dict[str, Any]], key: str) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        value = record.get("family", {}).get(key)
        if value:
            groups[str(value)].append(index)
    return {value: indexes for value, indexes in groups.items() if len(indexes) > 1}


def _reference_population(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    usable = [record for record in records if record.get("status") == "ok"]
    exact: dict[str, dict[str, Any]] = {}
    for record in usable:
        exact.setdefault(record["source_sha256"], record)
    independent = list(exact.values())
    distributions = {}
    for feature in REFERENCE_FEATURES:
        distributions[feature] = _summary(
            value for record in independent
            if (value := _feature_value(record, feature)) is not None
        )
    return independent, {
        "maps_read": len(records),
        "maps_usable": len(usable),
        "exact_duplicate_groups": len({
            sha for sha, group in _group_by(records, "source_sha256").items() if len(group) > 1
        }),
        "independent_exact_hashes": len(independent),
        "feature_distributions": distributions,
        "notes": [
            "Canonical reference distributions use medians and percentiles, not means.",
            "Absolute sector/wall/area scale is excluded from quality comparisons.",
            "A percentile describes unusualness relative to canonical maps, not goodness by itself.",
        ],
    }


def _group_by(records: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        value = record.get(key)
        if value:
            groups[str(value)].append(record)
    return groups


def _canonical_score_report(
    records: list[dict[str, Any]],
    independent: list[dict[str, Any]],
    distributions: dict[str, Any],
    canonical_root: Path,
) -> dict[str, Any]:
    """Build a ranked, explainable score table for every canonical MAP."""
    entries: list[dict[str, Any]] = []
    for record in records:
        relative = _relative(Path(record["source_absolute"]), canonical_root)
        if record.get("status") == "ok":
            comparison = canonical_comparison(record, independent, distributions)
            judgement = classify_record(record, comparison)
            quality_score = score_record(record, comparison)
        else:
            comparison = {"feature_percentiles": {}, "feature_bands": {}, "nearest_canonical": []}
            judgement = {"classification": "questionable", "quality_tier": None}
            quality_score = score_record(record, comparison)
        entries.append({
            "map": relative,
            "map": record.get("source_relative") or Path(record["source_absolute"]).name,
            "source_sha256": record["source_sha256"],
            "classification": judgement.get("classification"),
            "quality_tier": judgement.get("quality_tier"),
            "score": quality_score,
            "canonical_comparison": {
                "nearest_canonical": comparison.get("nearest_canonical", []),
                "feature_percentiles": comparison.get("feature_percentiles", {}),
            },
        })

    ranked = sorted(
        entries,
        key=lambda item: (
            item["score"]["score"] is None,
            -(float(item["score"]["score"]) if item["score"]["score"] is not None else 0.0),
            item["map"].lower(),
        ),
    )
    for index, item in enumerate(ranked, start=1):
        item["overall_rank"] = index if item["score"]["score"] is not None else None

    general = [item for item in ranked if item["classification"] in {"S", "A", "B", "C"} and item["score"]["score"] is not None]
    for index, item in enumerate(general, start=1):
        item["general_map_rank"] = index
    for item in ranked:
        item.setdefault("general_map_rank", None)

    scored = [float(item["score"]["score"]) for item in ranked if item["score"]["score"] is not None]
    return {
        "score_definition": {
            "range": [0, 100],
            "higher_is_better": True,
            "dimensions": {name: {"strong": 100, "adequate": 65, "weak": 25} for name in QUALITY_DIMENSIONS},
            "dimension_average_weight": round(100.0 / len(QUALITY_DIMENSIONS), 4),
            "penalties": {
                "validation_warnings": "0.25 points each, capped at 12",
                "unresolved_mechanisms": "0.5 points each, capped at 10",
                "water_wormhole_candidates": "2 points each, capped at 10",
            },
            "scale_policy": "scale_and_extent is included to keep tiny maps lower-weight; size above 8 playable sectors is not rewarded or penalized",
            "interpretation": "a transparent corpus-ranking heuristic, not an objective aesthetic judgement",
        },
        "map_count": len(entries),
        "scored_map_count": len(scored),
        "score_summary": _summary(scored),
        "ranked_maps": ranked,
    }


def canonical_comparison(record: dict[str, Any], canonical: list[dict[str, Any]], distributions: dict[str, Any]) -> dict[str, Any]:
    percentiles: dict[str, float | None] = {}
    bands: dict[str, str] = {}
    for feature in REFERENCE_FEATURES:
        value = _feature_value(record, feature)
        summary = distributions.get(feature) or {}
        if value is None or not summary.get("count"):
            percentiles[feature] = None
            bands[feature] = "unknown"
            continue
        p10, q1, q3, p90 = summary.get("p10"), summary.get("q1"), summary.get("q3"), summary.get("p90")
        if p10 is None or p90 is None:
            percentiles[feature], bands[feature] = None, "unknown"
            continue
        # Empirical percentile rank against the actual independent population.
        samples = [_feature_value(item, feature) for item in canonical]
        samples = [item for item in samples if item is not None]
        rank = sum(1 for item in samples if item <= value) / max(1, len(samples))
        percentiles[feature] = round(rank * 100.0, 2)
        if value < p10 or value > p90:
            bands[feature] = "outside_p10_p90"
        elif q1 is not None and q3 is not None and q1 <= value <= q3:
            bands[feature] = "central_IQR"
        else:
            bands[feature] = "outer_IQR"

    nearest: list[dict[str, Any]] = []
    distances = []
    for candidate in canonical:
        terms: list[float] = []
        for feature in REFERENCE_FEATURES:
            left = _feature_value(record, feature)
            right = _feature_value(candidate, feature)
            summary = distributions.get(feature) or {}
            scale = max(1e-6, float((summary.get("q3") or 0) - (summary.get("q1") or 0)))
            if left is not None and right is not None:
                terms.append(min(4.0, abs(left - right) / scale))
        if terms:
            distances.append((sum(terms) / len(terms), candidate))
    for distance, candidate in sorted(distances, key=lambda item: (item[0], item[1]["source_sha256"]))[:5]:
        nearest.append({
            "map": candidate.get("source_relative") or Path(candidate["source_absolute"]).name,
            "sha256": candidate["source_sha256"],
            "robust_feature_distance": round(distance, 4),
        })
    return {
        "feature_percentiles": percentiles,
        "feature_bands": bands,
        "nearest_canonical": nearest,
        "scale_is_not_a_quality_penalty": True,
        "comparison_features": list(REFERENCE_FEATURES),
    }


def _dimension_judgement(record: dict[str, Any], comparison: dict[str, Any]) -> tuple[dict[str, str], list[str], list[str]]:
    """Return dimension states, reasons, and unusual/outlier observations."""
    p = comparison["feature_percentiles"]
    profile = record
    dimensions: dict[str, str] = {}
    reasons: list[str] = []
    unusual: list[str] = []
    errors = int((record.get("counts") or {}).get("validation_errors") or 0)
    sectors = int((record.get("counts") or {}).get("playable_sectors") or 0)
    enemies = int(record.get("enemy_count") or 0)
    pickups = int((record.get("population") or {}).get("pickups") or 0)
    progression = record.get("progression") or {}
    mechanisms = record.get("mechanism_inventory") or {}
    lighting = record.get("lighting") or {}
    materials = record.get("materials") or {}
    morphology = record.get("morphology") or {}
    topology = record.get("topology") or {}

    if errors:
        dimensions["structural_validity"] = "weak"
        reasons.append(f"{errors} structural validation error(s)")
    else:
        dimensions["structural_validity"] = "strong"
    if sectors <= 3:
        dimensions["scale_and_extent"] = "weak"
        reasons.append(f"only {sectors} playable sectors")
    elif sectors <= 8:
        dimensions["scale_and_extent"] = "adequate"
    else:
        dimensions["scale_and_extent"] = "strong"
    if topology.get("components", 1) > 1:
        dimensions["navigation"] = "weak"
        reasons.append(f"playable topology has {topology['components']} components")
    elif ((p.get("topology.mean_degree") is not None and 20 <= p["topology.mean_degree"] <= 85) or
          (p.get("topology.loops_per_100_sectors") is not None and 15 <= p["topology.loops_per_100_sectors"] <= 90)):
        dimensions["navigation"] = "strong"
    else:
        dimensions["navigation"] = "adequate"
    flat = float(lighting.get("wall_flat_sector_fraction") or 0)
    contrast = float(lighting.get("wall_contrast_sector_fraction") or 0)
    shade_range = float(lighting.get("surface_shade_range") or 0)
    if flat >= 0.9 and contrast < 0.05 and shade_range <= 4:
        dimensions["lighting"] = "weak"
        reasons.append("shading is almost uniform with little within-map contrast")
    elif ((p.get("lighting.wall_flat_sector_fraction") is not None and p["lighting.wall_flat_sector_fraction"] <= 75 and
          p.get("lighting.wall_contrast_sector_fraction") is not None and p["lighting.wall_contrast_sector_fraction"] >= 25) or
          (p.get("lighting.adjacent_contrast_fraction") is not None and p["lighting.adjacent_contrast_fraction"] >= 25)):
        dimensions["lighting"] = "strong"
    else:
        dimensions["lighting"] = "adequate"
    dominant_wall = float(materials.get("dominant_wall_share") or 0)
    dominant_floor = float(materials.get("dominant_floor_share") or 0)
    material_types = int(materials.get("wall_tiles") or 0) + int(materials.get("floor_tiles") or 0) + int(materials.get("ceiling_tiles") or 0)
    if material_types <= 3 or (dominant_wall >= 0.95 and dominant_floor >= 0.95):
        dimensions["materials"] = "weak"
        reasons.append("material treatment is extremely concentrated")
    elif ((p.get("materials.dominant_wall_share") is not None and p["materials.dominant_wall_share"] <= 65 and
          p.get("materials.dominant_floor_share") is not None and p["materials.dominant_floor_share"] <= 65) or
          (p.get("materials.floor_patch_share") is not None and 25 <= p["materials.floor_patch_share"] <= 90 and material_types >= 8)):
        dimensions["materials"] = "strong"
    else:
        dimensions["materials"] = "adequate"
    rect = float(morphology.get("rectangular_sector_fraction") or 0)
    orient = float(morphology.get("orientation_diversity") or 0)
    area_iqr = float((record.get("shape") or {}).get("area_iqr_ratio") or 1)
    height_iqr = float((record.get("shape") or {}).get("height_iqr_ratio") or 1)
    if ((rect >= 0.9 and orient < 0.35 and area_iqr <= 1.4 and height_iqr <= 1.25 and sectors >= 8) or
            (p.get("morphology.rectangular_sector_fraction") is not None and p["morphology.rectangular_sector_fraction"] >= 95 and
             p.get("shape.area_iqr_ratio") is not None and p["shape.area_iqr_ratio"] <= 20)):
        dimensions["geometry"] = "weak"
        reasons.append("geometry is highly repetitive rectangular construction")
    elif ((p.get("morphology.rectangular_sector_fraction") is not None and p["morphology.rectangular_sector_fraction"] <= 75) or
          (p.get("shape.area_iqr_ratio") is not None and p["shape.area_iqr_ratio"] >= 25) or
          (p.get("shape.height_iqr_ratio") is not None and p["shape.height_iqr_ratio"] >= 25)):
        dimensions["geometry"] = "strong"
    else:
        dimensions["geometry"] = "adequate"
    enemy_rank = p.get("population.dudes_per_100_sectors")
    pickup_rank = p.get("population.pickups_per_100_sectors")
    if enemies and pickups and ((enemy_rank is not None and enemy_rank >= 20) or (pickup_rank is not None and pickup_rank >= 20)):
        dimensions["gameplay_population"] = "strong"
    elif enemies or pickups or progression.get("keys_placed") or progression.get("locked_objects"):
        dimensions["gameplay_population"] = "adequate"
    else:
        dimensions["gameplay_population"] = "weak"
        reasons.append("no enemies, pickups, or key/lock population detected")
    meaningful_progression = (
        (progression.get("distinct_keys") and progression.get("locked_objects")) or
        (progression.get("exit_reachable") and progression.get("final_reachable", 0) > progression.get("physical_reachable_at_rest", 0)) or
        progression.get("chain_count", 0) >= 2
    )
    if meaningful_progression:
        dimensions["progression_and_mechanisms"] = "strong"
    elif (progression.get("distinct_keys") or progression.get("locked_objects") or progression.get("chain_count") or
          progression.get("activated_channel_count") or mechanisms.get("moving_sector_count")):
        dimensions["progression_and_mechanisms"] = "adequate"
    else:
        dimensions["progression_and_mechanisms"] = "adequate"

    for feature, rank in p.items():
        if rank is not None and (rank <= 5 or rank >= 95):
            unusual.append(f"{feature} is at approximately the {rank:g}th canonical percentile")
    if record.get("water", {}).get("wormholes"):
        unusual.append(f"{record['water']['wormholes']} water wormhole candidate(s)")
    if record.get("geometry", {}).get("coincident_solid_pairs"):
        unusual.append(f"{record['geometry']['coincident_solid_pairs']} coincident solid wall pair(s)")
    if mechanisms.get("unresolved_count"):
        unusual.append(f"{mechanisms['unresolved_count']} unresolved mechanism object(s)")
    if record.get("counts", {}).get("validation_warnings"):
        unusual.append(f"{record['counts']['validation_warnings']} validation warning(s)")
    return dimensions, reasons, unusual


def classify_record(record: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    starts = record.get("player_starts") or {}
    mp = int(starts.get("multiplayer") or 0)
    sp = int(starts.get("single_player") or 0)
    enemies = int(record.get("enemy_count") or 0)
    sectors = int((record.get("counts") or {}).get("playable_sectors") or 0)
    progression = record.get("progression") or {}
    mechanisms = record.get("mechanism_inventory") or {}
    reasons: list[str] = []
    unusual: list[str] = []

    # Structural multiplayer evidence is intentionally stronger than names.
    bloodbath_evidence = []
    if mp >= 2:
        bloodbath_evidence.append(f"{mp} multiplayer starts")
    if mp >= 4:
        bloodbath_evidence.append("four or more distinct multiplayer spawn points")
    if enemies == 0:
        bloodbath_evidence.append("no normal single-player enemy population")
    if sp == 0:
        bloodbath_evidence.append("no single-player start")
    if not progression.get("keys_placed") and not progression.get("locked_objects") and not progression.get("chain_count"):
        bloodbath_evidence.append("no detected single-player progression structure")
    if mp >= 2 and len(bloodbath_evidence) >= 3 and (enemies == 0 or sp == 0):
        return {
            "classification": "bloodbath", "map_type": "bloodbath", "quality_tier": None,
            "dimension_judgements": {}, "reasons": bloodbath_evidence,
            "unusual_features": unusual, "special_purpose_evidence": bloodbath_evidence,
        }

    if record.get("status") != "ok":
        return {
            "classification": "questionable", "map_type": "questionable/other", "quality_tier": None,
            "dimension_judgements": {},
            "reasons": ["map could not be measured by the llmapper sensor bundle", *record.get("sensor_errors", [])],
            "unusual_features": list(record.get("sensor_errors", [])),
        }

    # A demonstration map needs several converging signals.  Empty maps with
    # no mechanism evidence remain normal/questionable rather than becoming demos.
    demo_evidence = []
    if sp == 1 and mp == 0:
        demo_evidence.append("one single-player start and no multiplayer starts")
    if enemies == 0:
        demo_evidence.append("no enemies")
    if mechanisms.get("switch_count", 0):
        demo_evidence.append(f"{mechanisms['switch_count']} switches")
    if mechanisms.get("moving_sector_count", 0):
        demo_evidence.append(f"{mechanisms['moving_sector_count']} moving sectors")
    if mechanisms.get("generator_or_sound_count", 0):
        demo_evidence.append(f"{mechanisms['generator_or_sound_count']} generators/sound objects")
    if mechanisms.get("channel_count", 0):
        demo_evidence.append(f"{mechanisms['channel_count']} mechanism channels")
    if sectors <= 24:
        demo_evidence.append(f"small/artificial scale ({sectors} playable sectors)")
    if sp == 1 and mp == 0 and enemies == 0 and len(demo_evidence) >= 4 and (
            mechanisms.get("moving_sector_count", 0) or mechanisms.get("switch_count", 0) or mechanisms.get("channel_count", 0)):
        return {
            "classification": "mechanism", "map_type": "mechanism", "quality_tier": None,
            "dimension_judgements": {},
            "reasons": demo_evidence,
            "unusual_features": unusual,
            "special_purpose_evidence": demo_evidence,
            "demonstrated_mechanisms": mechanisms.get("by_type", {}),
        }

    dimensions, quality_reasons, dimension_unusual = _dimension_judgement(record, comparison)
    reasons.extend(quality_reasons)
    unusual.extend(dimension_unusual)
    quality_dimension_names = tuple(name for name in dimensions if name != "scale_and_extent")
    strong = sum(dimensions[name] == "strong" for name in quality_dimension_names)
    weak = sum(dimensions[name] == "weak" for name in quality_dimension_names)
    severe = bool(record.get("geometry", {}).get("coincident_solid_pairs")) or bool((record.get("counts") or {}).get("validation_errors"))
    empty_unmotivated = enemies == 0 and not progression.get("keys_placed") and not progression.get("locked_objects") and not mechanisms.get("moving_sector_count") and not mechanisms.get("switch_count")
    if severe or (empty_unmotivated and sectors <= 3):
        classification = "questionable"
        map_type = "questionable/other"
        tier = None
        reasons.append("pathological or insufficient evidence for a normal reference tier")
    elif sectors <= 8:
        # A tiny playable footprint can be an excellent local mechanism
        # reference, but it is not enough evidence for a general visual/layout
        # authority.  BloodBath/mechanism branches have already returned above.
        classification = tier = "C"
        map_type = "singleplayer"
        reasons.append(f"only {sectors} playable sectors; retained as a low-weight small-map reference")
    elif strong >= 6 and weak <= 1:
        classification = tier = "S"
        map_type = "singleplayer"
        reasons.append(f"strong evidence across {strong} independent design dimensions")
    elif strong >= 5 and weak <= 2:
        classification = tier = "A"
        map_type = "singleplayer"
        reasons.append(f"strong evidence across {strong} independent design dimensions")
    elif weak >= 4 or (empty_unmotivated and sectors <= 8):
        classification = tier = "C"
        map_type = "singleplayer"
        reasons.append(f"{weak} independent design dimensions are weak")
    elif strong >= 2 and weak <= 3:
        classification = tier = "B"
        map_type = "singleplayer"
        reasons.append(f"competent evidence across {strong} strong and {weak} weak dimensions")
    else:
        classification = tier = "C"
        map_type = "singleplayer"
        reasons.append("evidence is mixed or underdeveloped")
    return {
        "classification": classification, "map_type": map_type, "quality_tier": tier,
        "dimension_judgements": dimensions,
        "rule_trace": {
            "strong_dimensions": strong,
            "weak_dimensions": weak,
            "severe_geometry_or_validation": bool(severe),
            "empty_and_unmotivated": bool(empty_unmotivated),
            "playable_sectors": sectors,
        },
        "reasons": reasons,
        "unusual_features": unusual,
    }


def score_record(record: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    """Return an explainable 0-100 general-map quality score.

    This is deliberately a rubric score, not a claim that a map's aesthetic
    quality can be reduced to one number.  It mirrors the classification
    dimensions, includes scale so tiny maps do not outrank full levels, and
    exposes every component and penalty for review.
    """
    if record.get("status") != "ok":
        return {
            "score": None,
            "raw_dimension_score": None,
            "dimension_scores": {},
            "penalties": {},
            "score_status": "unavailable",
            "score_notes": ["one or more required sensors failed"],
        }
    dimensions, _reasons, _unusual = _dimension_judgement(record, comparison)
    dimension_scores = {
        name: DIMENSION_POINTS.get(dimensions.get(name), 0.0)
        for name in QUALITY_DIMENSIONS
    }
    raw = sum(dimension_scores.values()) / len(QUALITY_DIMENSIONS)
    counts = record.get("counts") or {}
    mechanisms = record.get("mechanism_inventory") or {}
    water = record.get("water") or {}
    penalties = {
        "validation_warnings": round(min(12.0, float(counts.get("validation_warnings") or 0) * 0.25), 2),
        "unresolved_mechanisms": round(min(10.0, float(mechanisms.get("unresolved_count") or 0) * 0.5), 2),
        "water_wormhole_candidates": round(min(10.0, float(water.get("wormholes") or 0) * 2.0), 2),
    }
    total_penalty = sum(penalties.values())
    score = max(0.0, min(100.0, raw - total_penalty))
    notes = [
        "Higher is better within this corpus rubric; it is not an objective aesthetic rating.",
        "Scale is included so very small maps remain lower-weight general-map references.",
        "Absolute size above the small-map threshold is not rewarded or penalized.",
    ]
    if total_penalty:
        notes.append(f"quality findings reduced the raw score by {total_penalty:g} points")
    return {
        "score": round(score, 2),
        "raw_dimension_score": round(raw, 2),
        "dimension_scores": dimension_scores,
        "dimension_judgements": dimensions,
        "penalties": penalties,
        "score_status": "scored",
        "score_notes": notes,
    }


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _tier_destination(record: dict[str, Any], output_root: Path) -> str:
    """Where a map's tier copy goes, as a path relative to the tier root.

    The source's shape below its population directory is preserved:
    `community/chronicles1/CRYPT.MAP` becomes `S/chronicles1/CRYPT.MAP`. The
    old tier tree flattened to the filename, which is why 120 names ended up in
    more than one tier directory and why a hash join was needed to read it
    back. Two maps that share a name are two maps.
    """
    parts = Path(record["source_relative"]).parts
    relative = Path(*parts[1:]) if len(parts) > 1 else Path(parts[-1])
    destination = output_root / record["classification"] / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = Path(record["source_absolute"])
    if destination.resolve() != source.resolve():
        if destination.exists():
            # copy2 carries the source's mode bits, and a good part of this
            # corpus is read-only 0444 from a 2004 archive. Re-running the
            # tiering must not need a chmod -R first.
            destination.chmod(0o666)
            destination.unlink()
        shutil.copy2(source, destination)
    return (Path(record["classification"]) / relative).as_posix()


def _summary_report(records: list[dict[str, Any]], reference: dict[str, Any], canonical_scores: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(record.get("classification", "questionable") for record in records)
    independent: dict[str, dict[str, Any]] = {}
    for record in records:
        independent.setdefault(record["source_sha256"], record)
    independent_counts = Counter(record.get("classification", "questionable") for record in independent.values())
    tiered = {key: [record for record in records if record.get("classification") == key] for key in CLASSIFICATIONS}
    feature_by_class: dict[str, Any] = {}
    for key, members in tiered.items():
        feature_by_class[key] = {
            feature: _summary(value for record in members if (value := _feature_value(record, feature)) is not None)
            for feature in REFERENCE_FEATURES
        }
    reason_counts = Counter()
    for record in records:
        reason_counts.update(record.get("reasons") or [])
    samples = {}
    for key, members in tiered.items():
        samples[key] = [
            {"source_relative": item["source_relative"], "classification": item["classification"], "reasons": item["reasons"][:4]}
            for item in sorted(members, key=lambda value: value["source_relative"])[:8]
        ]
    return {
        "$schema": "llmapper.blood-corpus-summary",
        "schema_version": 1,
        "map_count": len(records),
        "classification_counts": dict(counts),
        "exact_hash_deduplicated_classification_counts": dict(independent_counts),
        "exact_hash_deduplicated_map_count": len(independent),
        "feature_distributions_by_class": feature_by_class,
        "strongest_classification_reasons": [{"reason": reason, "count": count} for reason, count in reason_counts.most_common(30)],
        "representative_samples": samples,
        "reference_population": reference,
        "canonical_scores": canonical_scores,
        "validation_notes": [
            "Review S/A boundaries with the nearest-canonical evidence and raw sensors; the tier decision remains rule-based.",
            "Canonical scores reuse the same global quality dimensions as tiering; higher is better, but the number is not an objective aesthetic judgement.",
            "Scale and ambitious geometry are reported but are not automatic quality penalties.",
            "Mechanism maps are separated before quality tiering so sophisticated mechanisms do not promote tutorials.",
            "Empty maps are not mechanism demos unless multiple mechanism signals converge.",
            "Normal maps with 8 or fewer playable sectors are capped at C; maps with 3 or fewer may be questionable when their evidence is insufficient.",
        ],
    }


def _measure_paths(paths: list[Path], workers: int) -> list[dict[str, Any]]:
    if workers <= 1:
        return [measure_map(path) for path in paths]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(measure_map, paths))


def _health_failures(report_path: str | Path | None) -> tuple[set[str], str]:
    """Relatives the native losslessness gate rejected, and where that came from.

    Fail-closed: a map the gate could not vouch for is not tiered.  A heuristic
    that scores a file the parser could not round-trip is scoring its own
    parse errors.
    """
    if report_path is None:
        return set(), "no health report supplied; every candidate was tiered"
    path = Path(report_path)
    if not path.exists():
        raise CorpusTieringError(f"health report {path} does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    failed = {
        str(item.get("relative") or item.get("filename"))
        for item in payload.get("results", [])
        if item.get("status") != "pass"
    }
    return failed, f"{path.as_posix()} ({len(failed)} maps failed the gate)"


class CorpusTieringError(ValueError):
    pass


def _reference_fingerprint(records: list[dict[str, Any]]) -> str:
    """One digest over the reference population's content hashes.

    A tier is a comparison, so two tiers are only comparable if they were
    compared against the same thing. The view *name* is not enough: `reference`
    means whatever `campaign + curated` held on the day, and the corpus is
    edited in place.
    """
    digest = hashlib.sha256()
    for value in sorted(record["source_sha256"] for record in records):
        digest.update(value.encode("ascii"))
    return digest.hexdigest()


def compare_tier_manifests(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Agreements and moves between two tier manifests, or a refusal.

    Measured: halving the reference population from the 102-map `reference`
    view to the 52-map `original` view moved **14.6%** of community maps
    (213 of 1461), all of it inside S/A/B. `C`, `bloodbath`, `mechanism` and
    `questionable` never moved, because those rules read absolute evidence -
    sector counts, player starts, mechanism counts, sensor status - rather than
    the reference distribution.

    So comparing tiers scored against different references measures the
    reference, not the maps, and this refuses to do it.
    """
    for side, payload in (("left", left), ("right", right)):
        if "reference_fingerprint" not in payload:
            raise CorpusTieringError(
                f"{side} manifest predates reference fingerprinting and cannot "
                "be compared; regenerate it with corpus-tier"
            )
    if left["reference_fingerprint"] != right["reference_fingerprint"]:
        raise CorpusTieringError(
            "refusing to compare tier manifests scored against different "
            f"reference populations: {left['reference_view']} "
            f"({left['reference_map_count']} maps, "
            f"{left['reference_fingerprint'][:12]}) against "
            f"{right['reference_view']} ({right['reference_map_count']} maps, "
            f"{right['reference_fingerprint'][:12]}). Measured churn between "
            "the reference and original views is 14.6%, so the difference "
            "would be the reference and not the maps."
        )
    a = {record["source_relative"]: record["classification"] for record in left["records"]}
    b = {record["source_relative"]: record["classification"] for record in right["records"]}
    shared = sorted(set(a) & set(b))
    moved = [name for name in shared if a[name] != b[name]]
    return {
        "reference_view": left["reference_view"],
        "reference_fingerprint": left["reference_fingerprint"],
        "shared": len(shared),
        "agree": len(shared) - len(moved),
        "moved": len(moved),
        "only_in_left": sorted(set(a) - set(b)),
        "only_in_right": sorted(set(b) - set(a)),
        "moves": dict(Counter(f"{a[name]}->{b[name]}" for name in moved)),
    }


def tier_corpus(
    output_directory: str | Path,
    *,
    directory: str | Path | None = None,
    population: str = "community",
    reference_view: str = "reference",
    health_report: str | Path | None = None,
    workers: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Tier one population against a named reference view.

    Both sets come from the Phase 0a corpus registry, so provenance is the
    directory a map lives in and nothing here globs a folder.  Paths in the
    manifest are relative to the corpus root: an absolute path from one
    checkout is meaningless in another, which is exactly what went wrong with
    the manifest this replaces.
    """
    from .patterns import corpus_root, list_corpus_maps

    root = corpus_root(directory)
    output_root = Path(output_directory)
    candidates = list_corpus_maps(root, population=population)
    reference_maps = list_corpus_maps(root, view=reference_view)
    if not candidates:
        raise CorpusTieringError(f"no maps in population {population!r} under {root}")
    if not reference_maps:
        raise CorpusTieringError(f"no maps in view {reference_view!r} under {root}")

    failed, health_basis = _health_failures(health_report)
    gated = [item for item in candidates if item.relative not in failed]
    skipped = [
        {"relative": item.relative, "reason": "failed the native losslessness gate"}
        for item in candidates if item.relative in failed
    ]

    source_records = _measure_paths([item.path for item in gated], workers)
    reference_records = _measure_paths([item.path for item in reference_maps], workers)
    relative_of = {str(Path(item.path).resolve()): item.relative
                   for item in gated + reference_maps}

    for record in source_records + reference_records:
        record["source_relative"] = relative_of.get(
            str(Path(record["source_absolute"]).resolve()),
            Path(record["source_absolute"]).name)

    independent_reference, reference = _reference_population(reference_records)
    distributions = reference["feature_distributions"]
    reference_scores = _canonical_score_report(
        reference_records, independent_reference, distributions, root)
    reference_families = _family_groups(
        reference_records, "coarse_geometry_topology_signature")

    exact_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    coarse_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in source_records:
        exact_groups[record["source_sha256"]].append(record)
        key = record.get("family", {}).get("coarse_geometry_topology_signature")
        if key:
            coarse_groups[key].append(record)

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_records = []
    for record in source_records:
        comparison = (
            canonical_comparison(record, independent_reference, distributions)
            if record.get("status") == "ok"
            else {"feature_percentiles": {}, "feature_bands": {}, "nearest_canonical": []}
        )
        judgement = classify_record(record, comparison)
        if record.get("status") != "ok":
            for key in ("topology", "progression", "lighting", "materials", "shape",
                        "geometry", "population", "water", "mechanisms", "morphology",
                        "design_fingerprint_metrics", "spatial_summary"):
                record.setdefault(key, None)
            record.setdefault("mechanism_inventory", {
                "status": "unavailable",
                "reason": "sensor bundle stopped before mechanism inventory completed",
            })
            record["measurement_completeness"] = "partial"
        else:
            record["measurement_completeness"] = "complete"
        record.update(judgement)
        record["quality_score"] = score_record(record, comparison)
        record["reference_comparison"] = comparison
        signature = record.get("family", {}).get("coarse_geometry_topology_signature")
        record["family"].update({
            "exact_duplicate_group_size": len(exact_groups[record["source_sha256"]]),
            "exact_duplicate_representative": min(
                item["source_relative"] for item in exact_groups[record["source_sha256"]]),
            "coarse_geometry_topology_family_size": len(coarse_groups.get(signature, [])),
            "coarse_geometry_topology_family_confidence":
                "medium" if len(coarse_groups.get(signature, [])) > 1 else "none",
            "reference_same_coarse_family_count": len(reference_families.get(signature, [])),
        })
        record["destination"] = _tier_destination(record, output_root)
        record.pop("source_absolute", None)      # never leaves this function
        manifest_records.append(record)

    manifest = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "corpus_root": root.as_posix(),
        "population": population,
        "reference_view": reference_view,
        "reference_map_count": len(reference_maps),
        "reference_fingerprint": _reference_fingerprint(reference_records),
        "output_directory": output_root.as_posix(),
        "paths_are": "relative to the corpus root; sha256 is the identity",
        "health_gate": {"basis": health_basis, "skipped": skipped},
        "classification_order": ["bloodbath", "mechanism", "S", "A", "B", "C", "questionable"],
        "tier_doctrine": (
            "navigation and sampling metadata, never an evidence weight and "
            "never ground truth about quality; a percentile describes "
            "unusualness, not goodness"
        ),
        "reference_population": reference,
        "reference_scores": reference_scores,
        "duplicate_handling": {
            "exact_duplicate_definition": "identical source SHA-256 bytes",
            "family_definition": "translation-normalized geometry plus coarse "
                                 "sector-area/height/topology signature",
            "statistics_policy": "exact duplicate hashes are collapsed in the "
                                 "reference population; source files are all retained",
        },
        "records": manifest_records,
    }
    summary = _summary_report(manifest_records, reference, reference_scores)
    summary["health_gate"] = manifest["health_gate"]
    return manifest, summary


def write_tiered_corpus(
    output_directory: str | Path,
    manifest_path: str | Path,
    summary_path: str | Path,
    **kwargs: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest, summary = tier_corpus(output_directory, **kwargs)
    for path, payload in ((manifest_path, manifest), (summary_path, summary)):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8", newline="\n")
    return manifest, summary
