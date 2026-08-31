"""Tier-classification rules, from PR #2, converted to the repo's unittest.

A tier is navigation and sampling metadata. It is never an evidence weight and
never ground truth about quality, and there is deliberately no confidence
scalar: the decision is rule-based and its evidence is the rule trace plus the
percentile table.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from bloodmap.tiering import (
    CorpusTieringError,
    _reference_fingerprint,
    compare_tier_manifests,
    _health_failures,
    _summary,
    classify_record,
    measure_map,
    score_record,
)
from tests.helpers import corpus_map


EMPTY_COMPARISON = {"feature_percentiles": {}, "feature_bands": {}, "nearest_canonical": []}


def base(*, sectors: int = 40, enemies: int = 20, mp: int = 0, sp: int = 1) -> dict:
    return {
        "status": "ok",
        "counts": {"playable_sectors": sectors, "validation_errors": 0,
                   "validation_warnings": 0},
        "player_starts": {"single_player": sp, "multiplayer": mp},
        "enemy_count": enemies,
        "progression": {"keys_placed": 0, "locked_objects": 0, "chain_count": 0},
        "mechanism_inventory": {"switch_count": 0, "moving_sector_count": 0,
                                "channel_count": 0},
        "geometry": {"coincident_solid_pairs": 0},
        "water": {"wormholes": 0},
        "lighting": {"wall_flat_sector_fraction": 0.2,
                     "wall_contrast_sector_fraction": 0.6,
                     "surface_shade_range": 60, "adjacent_contrast_fraction": 0.3},
        "materials": {"dominant_wall_share": 0.2, "dominant_floor_share": 0.2,
                      "wall_tiles": 8, "floor_tiles": 5, "ceiling_tiles": 4,
                      "floor_patch_share": 0.7},
        "morphology": {"rectangular_sector_fraction": 0.4, "orientation_diversity": 0.8},
        "shape": {"area_iqr_ratio": 10, "height_iqr_ratio": 2},
        "topology": {"components": 1, "mean_degree": 3.0, "loops_per_100_sectors": 50},
    }


class SummaryTests(unittest.TestCase):
    def test_it_reports_median_and_quartiles_not_a_mean(self):
        """A mean over a corpus with one 4000-sector outlier describes the
        outlier."""
        found = _summary([1, 2, 3, 4, 100])
        self.assertEqual(found["median"], 3)
        self.assertEqual(found["q1"], 2)
        self.assertEqual(found["q3"], 4)
        self.assertNotIn("mean", found)


class ClassificationRuleTests(unittest.TestCase):
    def test_multiplayer_starts_and_no_enemies_are_bloodbath_evidence(self):
        """Structural evidence, not the filename: the corpus is full of
        community maps called BB-something that are not deathmatch maps."""
        found = classify_record(base(sectors=80, enemies=0, mp=8, sp=0),
                                EMPTY_COMPARISON)
        self.assertEqual(found["classification"], "bloodbath")
        self.assertEqual(found["map_type"], "bloodbath")
        self.assertIsNone(found["quality_tier"])
        self.assertTrue(found["reasons"])

    def test_a_small_normal_map_is_capped_at_c(self):
        found = classify_record(base(sectors=6, enemies=20), EMPTY_COMPARISON)
        self.assertEqual(found["classification"], "C")
        self.assertTrue(any("6 playable sectors" in reason
                            for reason in found["reasons"]))

    def test_a_mechanism_demo_needs_several_converging_signals(self):
        record = base(sectors=6, enemies=0, mp=0, sp=1)
        record["mechanism_inventory"] = {"switch_count": 2, "moving_sector_count": 1,
                                         "channel_count": 2,
                                         "generator_or_sound_count": 0}
        found = classify_record(record, EMPTY_COMPARISON)
        self.assertEqual(found["classification"], "mechanism")

    def test_an_empty_map_is_not_a_mechanism_demo(self):
        """Without mechanism signals a small empty map stays ordinary."""
        found = classify_record(base(sectors=6, enemies=0, mp=0, sp=1),
                                EMPTY_COMPARISON)
        self.assertNotEqual(found["classification"], "mechanism")

    def test_a_map_the_sensors_could_not_measure_is_questionable(self):
        record = base()
        record["status"] = "error"
        record["sensor_errors"] = ["boom"]
        found = classify_record(record, EMPTY_COMPARISON)
        self.assertEqual(found["classification"], "questionable")
        self.assertIn("boom", found["reasons"])

    def test_no_decision_carries_an_invented_confidence(self):
        """`0.58 + 0.035 * |strong - weak|` read as a probability and measured
        nothing. The rule trace replaced it."""
        for record in (base(sectors=80, enemies=0, mp=8, sp=0),
                       base(sectors=6, enemies=20),
                       base(sectors=40)):
            found = classify_record(record, EMPTY_COMPARISON)
            self.assertNotIn("confidence", found)

    def test_a_tier_decision_carries_the_trace_that_produced_it(self):
        """The trace replaced the confidence scalar, so it has to track the
        decision rather than merely be present."""
        found = classify_record(base(sectors=40), EMPTY_COMPARISON)
        trace = found["rule_trace"]
        self.assertEqual(trace["playable_sectors"], 40)
        self.assertFalse(trace["severe_geometry_or_validation"])
        self.assertTrue(found["reasons"])

        degraded = base(sectors=40)
        degraded["lighting"] = {"wall_flat_sector_fraction": 0.95,
                                "wall_contrast_sector_fraction": 0.0,
                                "surface_shade_range": 0,
                                "adjacent_contrast_fraction": 0.0}
        degraded["materials"] = {"dominant_wall_share": 0.98,
                                 "dominant_floor_share": 0.98, "wall_tiles": 1,
                                 "floor_tiles": 1, "ceiling_tiles": 1,
                                 "floor_patch_share": 0.0}
        worse = classify_record(degraded, EMPTY_COMPARISON)["rule_trace"]
        self.assertGreater(worse["weak_dimensions"], trace["weak_dimensions"],
                           "a map with flat light and one tile everywhere must "
                           "trace more weak dimensions than a varied one")

    def test_severe_geometry_is_traced_and_forces_questionable(self):
        record = base(sectors=40)
        record["geometry"] = {"coincident_solid_pairs": 3}
        found = classify_record(record, EMPTY_COMPARISON)
        self.assertEqual(found["classification"], "questionable")
        self.assertTrue(found["rule_trace"]["severe_geometry_or_validation"])


class ScoreTests(unittest.TestCase):
    def test_the_score_is_a_declared_rubric_with_its_parts_exposed(self):
        full = score_record(base(sectors=40), EMPTY_COMPARISON)
        tiny = score_record(base(sectors=4), EMPTY_COMPARISON)
        self.assertTrue(0 <= full["score"] <= 100)
        self.assertGreater(full["score"], tiny["score"])
        self.assertEqual(set(full["dimension_scores"]), {
            "structural_validity", "scale_and_extent", "navigation", "lighting",
            "materials", "geometry", "gameplay_population",
            "progression_and_mechanisms"})
        self.assertIn("validation_warnings", full["penalties"])


class HealthGateTests(unittest.TestCase):
    def test_no_report_means_nothing_is_skipped_and_it_says_so(self):
        failed, basis = _health_failures(None)
        self.assertEqual(failed, set())
        self.assertIn("no health report", basis)

    def test_a_missing_report_fails_closed(self):
        with self.assertRaises(CorpusTieringError):
            _health_failures("no/such/report.json")

    def test_failing_maps_are_read_out_of_the_gate_report(self):
        import json
        import tempfile

        path = Path(tempfile.mkdtemp()) / "health.json"
        path.write_text(json.dumps({"results": [
            {"relative": "community/A.MAP", "status": "pass"},
            {"relative": "community/B.MAP", "status": "fail"},
        ]}), encoding="utf-8")
        failed, basis = _health_failures(path)
        self.assertEqual(failed, {"community/B.MAP"})
        self.assertIn("1 maps failed", basis)


class ReferenceFingerprintTests(unittest.TestCase):
    """A tier is a comparison, so two tiers are comparable only if they were
    compared against the same thing. Measured: halving the reference moves
    14.6% of the corpus."""

    LEFT = {
        "reference_view": "reference", "reference_map_count": 102,
        "reference_fingerprint": "aaaa",
        "records": [{"source_relative": "community/A.MAP", "classification": "S"},
                    {"source_relative": "community/B.MAP", "classification": "A"}],
    }

    def test_the_fingerprint_is_over_the_population_not_its_order(self):
        left = [{"source_sha256": "a"}, {"source_sha256": "b"}]
        right = [{"source_sha256": "b"}, {"source_sha256": "a"}]
        self.assertEqual(_reference_fingerprint(left), _reference_fingerprint(right))

    def test_a_different_population_fingerprints_differently(self):
        base = [{"source_sha256": "a"}, {"source_sha256": "b"}]
        wider = base + [{"source_sha256": "c"}]
        self.assertNotEqual(_reference_fingerprint(base), _reference_fingerprint(wider))
        self.assertNotEqual(_reference_fingerprint(base), _reference_fingerprint([]))

    def test_it_refuses_across_different_references(self):
        right = dict(self.LEFT, reference_view="original",
                     reference_map_count=52, reference_fingerprint="bbbb")
        with self.assertRaises(CorpusTieringError) as caught:
            compare_tier_manifests(self.LEFT, right)
        message = str(caught.exception)
        self.assertIn("refusing to compare", message)
        self.assertIn("reference", message)
        self.assertIn("original", message)
        self.assertIn("14.6%", message)

    def test_the_view_name_alone_is_not_enough(self):
        """`reference` means whatever campaign + curated held on the day, and
        the corpus is edited in place."""
        right = dict(self.LEFT, reference_fingerprint="cccc")
        self.assertEqual(right["reference_view"], self.LEFT["reference_view"])
        with self.assertRaises(CorpusTieringError):
            compare_tier_manifests(self.LEFT, right)

    def test_a_manifest_without_a_fingerprint_cannot_be_compared(self):
        old = {k: v for k, v in self.LEFT.items() if k != "reference_fingerprint"}
        with self.assertRaises(CorpusTieringError) as caught:
            compare_tier_manifests(self.LEFT, old)
        self.assertIn("predates reference fingerprinting", str(caught.exception))

    def test_the_same_reference_compares_and_reports_the_moves(self):
        right = {
            **self.LEFT,
            "records": [{"source_relative": "community/A.MAP", "classification": "S"},
                        {"source_relative": "community/B.MAP", "classification": "B"}],
        }
        found = compare_tier_manifests(self.LEFT, right)
        self.assertEqual(found["shared"], 2)
        self.assertEqual(found["agree"], 1)
        self.assertEqual(found["moved"], 1)
        self.assertEqual(found["moves"], {"A->B": 1})

    def test_a_manifest_compared_with_itself_moves_nothing(self):
        found = compare_tier_manifests(self.LEFT, self.LEFT)
        self.assertEqual(found["moved"], 0)
        self.assertEqual(found["agree"], found["shared"])


class DegenerateSectorMeasurementTests(unittest.TestCase):
    """PR #2's own corpus check, repointed at the reorganized layout."""

    def test_e6m7_measures_despite_its_two_walled_sector(self):
        from bloodmap.format import read_map
        from bloodmap.spatial import analyze_spatial

        path = corpus_map("E6M7.MAP")
        if not path.exists():
            self.skipTest("E6M7.MAP is not present in the local corpus")
        spatial = analyze_spatial(read_map(path).to_build_ir())
        self.assertEqual(spatial["ignored_degenerate_sector_ids"], ["sector:144"])
        record = measure_map(path)
        self.assertEqual(record["status"], "ok")
        self.assertIn("source_sha256", record)


class RegistryWiringTests(unittest.TestCase):
    def test_an_unknown_population_fails_closed(self):
        from bloodmap.tiering import tier_corpus

        import tempfile
        with self.assertRaises(Exception):
            tier_corpus(tempfile.mkdtemp(), population="canonical")

    def test_an_empty_population_is_refused_rather_than_tiered(self):
        from bloodmap.patterns import list_corpus_maps
        from bloodmap.tiering import tier_corpus

        import tempfile
        if not list_corpus_maps(population="community"):
            self.skipTest("no local Blood MAP corpus")
        with self.assertRaises(CorpusTieringError):
            tier_corpus(tempfile.mkdtemp(), population="generated")


if __name__ == "__main__":
    unittest.main()
