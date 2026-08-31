"""Focused tests for evidence-driven corpus classification rules."""

from __future__ import annotations

from pathlib import Path

from bloodmap.corpus import _summary, classify_record, measure_map, score_record
from bloodmap.format import read_map
from bloodmap.spatial import analyze_spatial


def _base(*, sectors: int = 40, enemies: int = 20, mp: int = 0, sp: int = 1) -> dict:
    return {
        "status": "ok",
        "counts": {"playable_sectors": sectors, "validation_errors": 0, "validation_warnings": 0},
        "player_starts": {"single_player": sp, "multiplayer": mp},
        "enemy_count": enemies,
        "progression": {"keys_placed": 0, "locked_objects": 0, "chain_count": 0},
        "mechanism_inventory": {"switch_count": 0, "moving_sector_count": 0, "channel_count": 0},
        "geometry": {"coincident_solid_pairs": 0},
        "water": {"wormholes": 0},
        "lighting": {"wall_flat_sector_fraction": 0.2, "wall_contrast_sector_fraction": 0.6, "surface_shade_range": 60, "adjacent_contrast_fraction": 0.3},
        "materials": {"dominant_wall_share": 0.2, "dominant_floor_share": 0.2, "wall_tiles": 8, "floor_tiles": 5, "ceiling_tiles": 4, "floor_patch_share": 0.7},
        "morphology": {"rectangular_sector_fraction": 0.4, "orientation_diversity": 0.8},
        "shape": {"area_iqr_ratio": 10, "height_iqr_ratio": 2},
        "topology": {"components": 1, "mean_degree": 3.0, "loops_per_100_sectors": 50},
    }


def test_summary_uses_median_and_iqr_fields() -> None:
    result = _summary([1, 2, 3, 4, 100])
    assert result["median"] == 3
    assert result["q1"] == 2
    assert result["q3"] == 4
    assert "mean" not in result


def test_multiple_mp_starts_and_empty_population_are_bloodbath_evidence() -> None:
    record = _base(sectors=80, enemies=0, mp=8, sp=0)
    result = classify_record(record, {"feature_percentiles": {}, "feature_bands": {}, "nearest_canonical": []})
    assert result["classification"] == "bloodbath"
    assert result["map_type"] == "bloodbath"


def test_small_normal_map_is_capped_at_c() -> None:
    record = _base(sectors=6, enemies=20)
    result = classify_record(record, {"feature_percentiles": {}, "feature_bands": {}, "nearest_canonical": []})
    assert result["classification"] == "C"
    assert any("6 playable sectors" in reason for reason in result["reasons"])


def test_mechanism_demo_requires_converging_signals() -> None:
    record = _base(sectors=6, enemies=0, mp=0, sp=1)
    record["mechanism_inventory"] = {"switch_count": 2, "moving_sector_count": 1, "channel_count": 2, "generator_or_sound_count": 0}
    result = classify_record(record, {"feature_percentiles": {}, "feature_bands": {}, "nearest_canonical": []})
    assert result["classification"] == "mechanism"
    assert result["map_type"] == "mechanism"


def test_quality_score_is_explainable_and_small_maps_score_lower() -> None:
    comparison = {"feature_percentiles": {}, "feature_bands": {}, "nearest_canonical": []}
    full = score_record(_base(sectors=40), comparison)
    tiny = score_record(_base(sectors=4), comparison)
    assert 0 <= full["score"] <= 100
    assert full["score"] > tiny["score"]
    assert set(full["dimension_scores"]) == {
        "structural_validity", "scale_and_extent", "navigation", "lighting",
        "materials", "geometry", "gameplay_population", "progression_and_mechanisms",
    }
    assert "validation_warnings" in full["penalties"]


def test_canonical_e6m7_degenerate_sector_isolated_without_sensor_failure() -> None:
    path = Path("maps/canonical/E6M7.MAP")
    if not path.is_file():
        return
    spatial = analyze_spatial(read_map(path).to_build_ir())
    assert spatial["ignored_degenerate_sector_ids"] == ["sector:144"]
    assert len(spatial["sector_ids"]) == 471
    record = measure_map(path)
    assert record["status"] == "ok"
    assert record["counts"]["validation_warnings"] == 1
