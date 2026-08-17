"""State-dependent progression witness on the scratch puzzle room."""

from __future__ import annotations

import unittest

from bloodmap.designs import build_first_puzzle_room
from bloodmap.progression import analyze_progression, classify_mechanisms, completion_witness


class ProgressionTests(unittest.TestCase):
    def test_first_puzzle_room_grows_reachability_through_two_switches(self):
        designed = build_first_puzzle_room()
        report = analyze_progression(designed.level.to_disk_map())
        activates = [item for item in report["witness"] if item.get("kind") == "activate"]
        self.assertGreaterEqual(len(activates), 2)
        self.assertGreater(report["final_reachable"], report["physical_reachable_at_rest"])
        roles = classify_mechanisms(report)
        self.assertTrue(any(item["role"] == "opens_space" for item in roles["required"]))
        witness = completion_witness(report)
        self.assertGreaterEqual(len(witness["events"]), 3)


if __name__ == "__main__":
    unittest.main()
