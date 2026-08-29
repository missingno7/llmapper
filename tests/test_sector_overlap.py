"""The overlap validator against the hand-built calibration set.

Two sectors may share ground in XY, and the engine will draw both -- the far
one's floor landing on the near one wherever the bunch sort has no answer.
`tools.vector_report` decides, per map, from which camera positions that can
happen.

The maps in tests/data/sector_overlap were built by hand in XMapEdit and
checked in the engine, one at a time, each after a verdict here disagreed with
what the game did.  They are the only ground truth this validator has, which is
why they live in the tree rather than beside the commercial corpora.

Every good map here was once believed good and turned out not to be: good_3,
good_4 and good_6 were renamed to bad_7, bad_9 and bad_8 after the owner stood
where the validator pointed and saw the glitch.  So a bad map failing this test
is a regression; a good map failing it is a question, not necessarily a bug.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build2d_core import Build2DModel
from tools.vector_report import solve_map

DATA = Path(__file__).resolve().parent / "data" / "sector_overlap"


def _verdict(path):
    found = solve_map(Build2DModel.load(path))
    return [r for r in found if "wkt" in r]


class CalibrationSetTests(unittest.TestCase):
    def test_every_bad_map_is_flagged(self):
        maps = sorted(DATA.glob("bad_*.map"))
        self.assertEqual(len(maps), 7, "the bad half of the set went missing")
        for path in maps:
            with self.subTest(map=path.stem):
                regions = _verdict(path)
                self.assertTrue(
                    regions,
                    f"{path.stem} glitches in the engine and must be flagged",
                )

    def test_every_good_map_is_clean(self):
        maps = sorted(DATA.glob("good_*.map"))
        self.assertEqual(len(maps), 3, "the good half of the set went missing")
        for path in maps:
            with self.subTest(map=path.stem):
                regions = _verdict(path)
                self.assertFalse(
                    regions,
                    "%s does not glitch in the engine; flagged %s"
                    % (path.stem, [r["overlap"] for r in regions]),
                )

    def test_the_verdict_does_not_move_between_runs(self):
        """The transparent cluster once iterated a set, so the domain -- and
        the verdict with it -- followed Python's per-process string hashing."""
        path = DATA / "bad_3.map"
        first = [(r["overlap"], r["root"], round(r["area"], 3))
                 for r in _verdict(path)]
        second = [(r["overlap"], r["root"], round(r["area"], 3))
                  for r in _verdict(path)]
        self.assertEqual(first, second)
        self.assertTrue(first)


if __name__ == "__main__":
    unittest.main()
