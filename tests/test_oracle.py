from __future__ import annotations

import unittest

from bloodmap.oracle import assess_nblood_output


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


if __name__ == "__main__":
    unittest.main()
