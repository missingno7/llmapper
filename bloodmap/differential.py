from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from statistics import mean
from typing import Any

from .duke import DukeDiskMap, read_duke_map
from .format import read_map
from .model import DiskMap


SCALE_CANDIDATES = tuple(Fraction(n, d) for n, d in (
    (1, 2), (2, 3), (3, 4), (1, 1), (4, 3), (3, 2), (2, 1),
))


def _scaled(value: int, scale: Fraction) -> int:
    return round(value * scale.numerator / scale.denominator)


def _wall_vectors(disk: Any) -> Counter[tuple[int, int]]:
    result: Counter[tuple[int, int]] = Counter()
    for wall in disk.walls:
        other = disk.walls[wall.point2]
        result[(other.x - wall.x, other.y - wall.y)] += 1
    return result


def infer_xy_scale(duke: DukeDiskMap, blood: DiskMap) -> dict[str, Any]:
    duke_vectors, blood_vectors = _wall_vectors(duke), _wall_vectors(blood)
    candidates = []
    for scale in SCALE_CANDIDATES:
        overlap = sum(
            min(amount, blood_vectors[(_scaled(dx, scale), _scaled(dy, scale))])
            for (dx, dy), amount in duke_vectors.items()
        )
        candidates.append({
            "numerator": scale.numerator,
            "denominator": scale.denominator,
            "value": float(scale),
            "matching_directed_edges": overlap,
        })
    candidates.sort(key=lambda item: (-item["matching_directed_edges"], item["value"]))
    return {"selected": candidates[0], "candidates": candidates}


def _sector_signature(disk: Any, sector: Any, scale: Fraction) -> tuple[tuple[int, int], ...]:
    return tuple(sorted(
        (_scaled(disk.walls[index].x, scale), _scaled(disk.walls[index].y, scale))
        for index in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)
    ))


def _linear_summary(pairs: list[tuple[int, int]]) -> dict[str, Any]:
    ordinary = [(x, y) for x, y in pairs if x > -100]
    if not ordinary:
        return {"samples": 0, "slope": None, "intercept": None, "mean_absolute_error": None}
    mx, my = mean(x for x, _y in ordinary), mean(y for _x, y in ordinary)
    denominator = sum((x - mx) ** 2 for x, _y in ordinary)
    slope = sum((x - mx) * (y - my) for x, y in ordinary) / denominator if denominator else 0.0
    intercept = my - slope * mx
    exact_double = sum(y == 2 * x for x, y in ordinary)
    return {
        "samples": len(ordinary),
        "least_squares_slope": slope,
        "least_squares_intercept": intercept,
        "mean_absolute_error": mean(abs(y - (slope * x + intercept)) for x, y in ordinary),
        "exact_blood_equals_two_times_duke": exact_double,
        "exact_double_fraction": exact_double / len(ordinary),
        "common_residuals_from_double": [
            {"residual": residual, "count": count}
            for residual, count in Counter(y - 2 * x for x, y in ordinary).most_common(12)
        ],
    }


def compare_e3l1_pair(duke_path: str | Path, blood_path: str | Path) -> dict[str, Any]:
    duke_path, blood_path = Path(duke_path), Path(blood_path)
    duke, blood = read_duke_map(duke_path), read_map(blood_path)
    inferred = infer_xy_scale(duke, blood)
    selected = inferred["selected"]
    scale = Fraction(selected["numerator"], selected["denominator"])

    blood_sectors: dict[tuple[tuple[int, int], ...], list[int]] = defaultdict(list)
    for sector_id, sector in enumerate(blood.sectors):
        blood_sectors[_sector_signature(blood, sector, Fraction(1, 1))].append(sector_id)
    sector_pairs: list[tuple[int, int]] = []
    for sector_id, sector in enumerate(duke.sectors):
        candidates = blood_sectors.get(_sector_signature(duke, sector, scale), [])
        if len(candidates) == 1:
            sector_pairs.append((sector_id, candidates[0]))

    blood_walls: dict[tuple[int, int, int, int], list[int]] = defaultdict(list)
    for wall_id, wall in enumerate(blood.walls):
        other = blood.walls[wall.point2]
        blood_walls[(wall.x, wall.y, other.x, other.y)].append(wall_id)
    wall_pairs: list[tuple[int, int]] = []
    for wall_id, wall in enumerate(duke.walls):
        other = duke.walls[wall.point2]
        key = tuple(_scaled(value, scale) for value in (wall.x, wall.y, other.x, other.y))
        candidates = blood_walls.get(key, [])
        if len(candidates) == 1:
            wall_pairs.append((wall_id, candidates[0]))

    z_residuals: Counter[int] = Counter()
    ceiling_shades: list[tuple[int, int]] = []
    floor_shades: list[tuple[int, int]] = []
    material_pairs: Counter[tuple[int, int]] = Counter()
    topology_matches = 0
    for duke_id, blood_id in sector_pairs:
        left, right = duke.sectors[duke_id], blood.sectors[blood_id]
        z_residuals[right.ceiling_z - _scaled(left.ceiling_z, scale)] += 1
        z_residuals[right.floor_z - _scaled(left.floor_z, scale)] += 1
        ceiling_shades.append((left.ceiling_shade, right.ceiling_shade))
        floor_shades.append((left.floor_shade, right.floor_shade))
        material_pairs[(left.ceiling_picnum, right.ceiling_picnum)] += 1
        material_pairs[(left.floor_picnum, right.floor_picnum)] += 1
        left_neighbors = sum(
            duke.walls[index].next_sector >= 0
            for index in range(left.wall_ptr, left.wall_ptr + left.wall_count)
        )
        right_neighbors = sum(
            blood.walls[index].next_sector >= 0
            for index in range(right.wall_ptr, right.wall_ptr + right.wall_count)
        )
        topology_matches += left_neighbors == right_neighbors
    wall_shades = [(duke.walls[left].shade, blood.walls[right].shade) for left, right in wall_pairs]
    for left, right in wall_pairs:
        material_pairs[(duke.walls[left].picnum, blood.walls[right].picnum)] += 1

    mappings: dict[int, Counter[int]] = defaultdict(Counter)
    for (source, target), amount in material_pairs.items():
        mappings[source][target] += amount
    material_evidence = []
    for source, targets in mappings.items():
        total = sum(targets.values())
        target, count = targets.most_common(1)[0]
        material_evidence.append({
            "duke_tile": source, "blood_tile": target, "support": count,
            "observations": total, "confidence": count / total,
            "classification": "exact-known" if target != 0 and count >= 5 and count == total else "context-dependent",
        })
    material_evidence.sort(key=lambda item: (-item["support"], item["duke_tile"]))

    duke_controllers = Counter(
        sprite.picnum for sprite in duke.sprites if sprite.picnum in {1, 2, 4, 8, 10}
    )
    blood_extras = {
        "xsectors": sum(item.extra is not None for item in blood.sectors),
        "xwalls": sum(item.extra is not None for item in blood.walls),
        "xsprites": sum(item.extra is not None for item in blood.sprites),
    }
    coverage = len(sector_pairs) / len(duke.sectors) if duke.sectors else 0.0
    if coverage >= 0.5:
        pair_role = "geometry-matched-hand-conversion"
    elif coverage == 0:
        pair_role = "reimagination"
    else:
        pair_role = "partial-geometry-match"
    limitations = [
        "geometry matching is exact after the selected rational scale and does not force unmatched indices",
        "sprite/entity correspondence is not inferred from proximity alone",
        "material mappings marked context-dependent are not safe global substitutions",
        "mechanisms are inventoried but not translated from tag numbers alone",
    ]
    if pair_role == "reimagination":
        limitations.append(
            "this pair shares an authoring scale but not unique sector shapes; treat Blood as a reimagination, not an index-matched conversion"
        )
    return {
        "$schema": "llmapper.cross-game-differential",
        "schema_version": 1,
        "pair_role": pair_role,
        "sources": {
            "duke": {"path": duke_path.as_posix(), "sha256": hashlib.sha256(duke_path.read_bytes()).hexdigest()},
            "blood": {"path": blood_path.as_posix(), "sha256": hashlib.sha256(blood_path.read_bytes()).hexdigest()},
        },
        "counts": {
            "duke": {"sectors": len(duke.sectors), "walls": len(duke.walls), "sprites": len(duke.sprites)},
            "blood": {"sectors": len(blood.sectors), "walls": len(blood.walls), "sprites": len(blood.sprites)},
        },
        "normalization": {
            "xy_scale_duke_to_blood": inferred,
            "z_scale_used": selected,
            "z_samples": len(sector_pairs) * 2,
            "z_exact_samples": z_residuals[0],
            "z_common_residuals": [{"native_units": value, "count": count} for value, count in z_residuals.most_common(12)],
            "player_start": {
                "duke": dict(x=duke.header["start_x"], y=duke.header["start_y"], z=duke.header["start_z"], angle=duke.header["start_angle"], sector=duke.header["start_sector"]),
                "blood": dict(x=blood.header["start_x"], y=blood.header["start_y"], z=blood.header["start_z"], angle=blood.header["start_angle"], sector=blood.header["start_sector"]),
                "scaled_coordinate_residual": {
                    "x": blood.header["start_x"] - _scaled(duke.header["start_x"], scale),
                    "y": blood.header["start_y"] - _scaled(duke.header["start_y"], scale),
                    "z": blood.header["start_z"] - _scaled(duke.header["start_z"], scale),
                },
            },
        },
        "geometry": {
            "unique_exact_sector_correspondences": len(sector_pairs),
            "duke_sector_coverage": len(sector_pairs) / len(duke.sectors),
            "unique_exact_wall_correspondences": len(wall_pairs),
            "duke_wall_coverage": len(wall_pairs) / len(duke.walls),
            "matched_sector_portal_degree_equal": topology_matches,
            "sector_pairs": [{"duke": left, "blood": right} for left, right in sector_pairs],
        },
        "lighting": {
            "initial_model": "blood_shade = clamp(round(2 * duke_shade), -128, 127); sentinel/context cases reported",
            "ceiling": _linear_summary(ceiling_shades),
            "floor": _linear_summary(floor_shades),
            "walls": _linear_summary(wall_shades),
        },
        "materials": {"candidates": material_evidence},
        "mechanisms": {
            "duke_controller_sprite_counts": [{"picnum": key, "count": value} for key, value in sorted(duke_controllers.items())],
            "blood_extended_record_counts": blood_extras,
            "translation_status": "unresolved-native-features; no low-level tag equivalence inferred",
        },
        "limitations": limitations,
    }


compare_hand_converted_pair = compare_e3l1_pair
