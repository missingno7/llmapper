from __future__ import annotations

import unittest
from pathlib import Path

from bloodmap.duke import read_duke_map
from bloodmap.duke_semantics import analyze_duke_mechanisms


ROOT = Path(__file__).resolve().parents[1]


class DukeSemanticInventoryTests(unittest.TestCase):
    def test_e3l11_crack_explosion_and_lighting_groups_are_semantic_not_raw_tags(self):
        source = ROOT / "maps" / "duke3d" / "E3L11.MAP"
        if not source.exists():
            self.skipTest("E3L11 is not present in the local Duke corpus")
        inventory = analyze_duke_mechanisms(read_duke_map(source))
        self.assertEqual(inventory["counts_by_effector_lotag"][12], 32)
        self.assertEqual(inventory["counts_by_effector_lotag"][13], 11)
        self.assertEqual(len(inventory["destructible_walls"]), 6)
        self.assertTrue(all(item["kind"] == "destructible_wall" for item in inventory["destructible_walls"]))
        self.assertTrue(all(item["linked_effect"] == "linked_explosion" for item in inventory["destructible_walls"]))
        self.assertIn("switchable_lighting", {item["kind"] for item in inventory["effectors"]})


if __name__ == "__main__":
    unittest.main()
