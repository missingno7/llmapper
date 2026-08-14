from __future__ import annotations

import unittest

import tempfile
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.format import read_map
from bloodmap.oracle import (
    assess_behavior_equivalence, assess_nblood_output, build_zmotion_behavior_scenario,
)


class OracleAssessmentTests(unittest.TestCase):
    def test_healthy_bounded_run_passes(self):
        log = """NBlood r14378-fbc5e1186
BLOODMAP_ORACLE_BOOTSTRAPPED
Waiting for network players!
Modern types erased: 0.
"""
        result = assess_nblood_output(log, "", stayed_alive=True)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["engine_revision"], "r14378-fbc5e1186")
        self.assertTrue(all(result["markers"].values()))

    def test_early_exit_missing_marker_or_fatal_signal_fails(self):
        healthy = "BLOODMAP_ORACLE_BOOTSTRAPPED\nWaiting for network players!\nModern types erased: 0."
        self.assertEqual(assess_nblood_output(healthy, "", stayed_alive=False)["status"], "fail")
        self.assertEqual(
            assess_nblood_output("BLOODMAP_ORACLE_BOOTSTRAPPED", "", stayed_alive=True)["status"],
            "fail",
        )
        crashed = assess_nblood_output(healthy, "Caught signal: SIGSEGV", stayed_alive=True)
        self.assertEqual(crashed["status"], "fail")
        self.assertEqual(crashed["fatal_indicators"], ["Caught signal"])

    def test_public_behavior_scenario_is_valid_and_composed(self):
        with tempfile.TemporaryDirectory() as directory:
            scenario = build_zmotion_behavior_scenario(directory)
            baseline = read_map(scenario["baseline"])
            candidate = read_map(scenario["candidate"])
            self.assertFalse([item for item in validate_map(baseline) if item.severity == "error"])
            self.assertFalse([item for item in validate_map(candidate) if item.severity == "error"])
            self.assertEqual((len(baseline.sectors), len(baseline.walls)), (1, 4))
            self.assertEqual((len(candidate.sectors), len(candidate.walls)), (2, 8))
            self.assertEqual(candidate.sectors[1].extra.fields["rx_id"], 100)
            self.assertEqual(candidate.walls[5].extra.fields["tx_id"], 100)
            self.assertEqual(scenario["composition"]["unresolved_relationships"], [])

    def test_behavior_equivalence_requires_stable_changed_matching_views(self):
        probe = {
            "status": "pass", "stable_views": True, "idle_control_unchanged": True,
            "visible_state_changed": True,
            "before_view": {"unique_sha256": ["before"]},
            "idle_control_view": {"unique_sha256": ["before"]},
            "after_view": {"unique_sha256": ["after"]},
        }
        self.assertEqual(assess_behavior_equivalence(probe, probe)["status"], "pass")
        changed = dict(probe)
        changed["after_view"] = {"unique_sha256": ["different"]}
        self.assertEqual(assess_behavior_equivalence(probe, changed)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
