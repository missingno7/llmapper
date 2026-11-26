"""A lowered SE17 warp elevator is reported as lowered by the conversion's coverage audit."""

from __future__ import annotations

import unittest

from bloodmap.e3l11 import convert_playable_duke_to_blood
from tests.test_duke_transport import board


class WarpElevatorCoverage(unittest.TestCase):
    def test_a_lowered_pair_is_not_counted_unsupported(self):
        # two SE17 cabins sharing a hitag: the converter makes both type 604 warps
        duke = board({"sector": 0, "lotag": 17, "hitag": 5}, {"sector": 1, "lotag": 17, "hitag": 5}, exit_sector=0)
        disk, report = convert_playable_duke_to_blood(duke)
        self.assertEqual(report["mechanisms"]["counts"]["warp-elevator"], 2)
        self.assertNotIn(17, report["mechanisms"]["unsupported_sector_effector_lotags"])

    def test_an_unpaired_cabin_still_is(self):
        duke = board({"sector": 0, "lotag": 17, "hitag": 5}, exit_sector=0)
        _disk, report = convert_playable_duke_to_blood(duke)
        self.assertIn(17, report["mechanisms"]["unsupported_sector_effector_lotags"])


if __name__ == "__main__":
    unittest.main()
