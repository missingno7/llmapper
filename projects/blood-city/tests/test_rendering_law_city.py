"""The rendering law on the built city: the rebuilt curtain's fabric is drawn."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CITY = ROOT / "projects" / "blood-city" / "level" / "blood-city-current.MAP"


class FailFirstTest(unittest.TestCase):
    def setUp(self):
        import bloodmap.rules_blood                       # noqa: F401
        from bloodmap.rules import RULES

        self.rules = RULES

    def test_the_rebuilt_city_curtain_passes_the_same_gate(self):
        # And the fix is visible to the same gate: P1's one-sided fin puts
        # 146 in a one_sided_middle, so the map no longer loses the tile.
        # Five OTHER tiles are still lost -- the districts' `opening`
        # materials on flush doorway thresholds -- which is the finding this
        # rule was built to make and is in the owner review queue.
        if not CITY.exists():
            self.skipTest("no city build")
        from bloodmap.format import read_map

        found = self.rules["wall-tile-is-drawn-somewhere"].check(read_map(CITY))
        self.assertNotIn("tile[146]", [v.location for v in found.violations])


if __name__ == "__main__":
    unittest.main()
