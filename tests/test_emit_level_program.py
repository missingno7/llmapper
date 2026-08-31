"""Turning a Blood map into level-program source it can be rebuilt from.

The cases here are about the *representation*: a shape Build accepts that a
planar subdivision does not, and what the emitter has to do about it.
"""

from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

from bloodmap.format import read_map
from bloodmap.model import LevelIR
from bloodmap.planar_geom import area2
from tools.emit_level_program import (
    _on_segment,
    _sector_loops,
    _sector_loops_split,
    _splice_flush_hole,
)

ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")
E2M3 = ROOT / "maps" / "blood" / "campaign" / "E2M3.MAP"


def campaign_maps() -> list[Path]:
    seen: set[str] = set()
    result = []
    for path in sorted(glob.glob(str(ROOT / "maps" / "blood" / "campaign" / "*.MAP"))):
        name = Path(path).stem.upper()
        if name in seen or not CAMPAIGN.match(name):
            continue
        seen.add(name)
        result.append(Path(path))
    return result


class SegmentTests(unittest.TestCase):
    def test_on_segment_is_exact(self):
        self.assertTrue(_on_segment((5, 0), (0, 0), (10, 0)))
        self.assertTrue(_on_segment((0, 0), (0, 0), (10, 0)))    # endpoints count
        self.assertFalse(_on_segment((11, 0), (0, 0), (10, 0)))  # past the end
        self.assertFalse(_on_segment((5, 1), (0, 0), (10, 0)))   # off the line


class FlushHoleTests(unittest.TestCase):
    """A hole sitting against the outer boundary is a notch drawn the other way."""

    def test_a_flush_hole_becomes_an_indentation(self):
        outer = [(0, 0), (100, 0), (100, 100), (0, 100)]
        hole = [(40, 0), (40, 20), (60, 20), (60, 0)]

        spliced = _splice_flush_hole(outer, hole)

        self.assertIsNotNone(spliced)
        self.assertIn((40, 20), spliced)
        self.assertIn((60, 20), spliced)
        # The notch removes area rather than adding it, and the outline stays
        # simple and positively wound.
        self.assertGreater(area2(tuple(spliced)), 0)
        self.assertLess(area2(tuple(spliced)), area2(tuple(outer)))
        self.assertEqual(len(set(spliced)), len(spliced))

    def test_a_strictly_interior_hole_stays_a_hole(self):
        outer = [(0, 0), (100, 0), (100, 100), (0, 100)]
        hole = [(40, 40), (40, 60), (60, 60), (60, 40)]

        self.assertIsNone(_splice_flush_hole(outer, hole))

    def test_the_seam_does_not_repeat_a_vertex_the_outline_already_had(self):
        """The common case: the hole's corners are outer vertices already."""
        outer = [(0, 0), (40, 0), (60, 0), (100, 0), (100, 100), (0, 100)]
        hole = [(40, 0), (40, 20), (60, 20), (60, 0)]

        spliced = _splice_flush_hole(outer, hole)

        self.assertIsNotNone(spliced)
        self.assertEqual(len(set(spliced)), len(spliced))


@unittest.skipUnless(E2M3.exists(), "no Blood campaign maps")
class E2M3Tests(unittest.TestCase):
    def test_sector_212_carries_a_hole_flush_with_its_own_outer_edge(self):
        """The shape that stopped the round trip, and why it is legal in Build.

        Sector 212 has four inner loops; the one that sector 326 fills has its
        bottom edge lying exactly on 212's outer boundary. The renderer walks
        loops rather than a subdivision, so Build does not care -- but two
        regions then draw the same piece of line in the same direction, which a
        planar layout cannot pair.
        """
        level = LevelIR.from_disk_map(read_map(E2M3))
        loops = _sector_loops(level, 212)
        self.assertEqual(len(loops), 5)

        outer, holes = _sector_loops_split(level, 212)

        self.assertEqual(len(holes), 3)          # one of the four was folded in
        self.assertIn((54720, 37376), outer)     # the notch is in the outline now
        self.assertIn((54784, 37376), outer)
        self.assertEqual(len(set(outer)), len(outer))
        self.assertGreater(area2(tuple(outer)), 0)


@unittest.skipUnless(campaign_maps(), "no Blood campaign maps")
class CorpusSafetyTests(unittest.TestCase):
    """Splicing must not create a shape that was fine before."""

    def test_splicing_introduces_no_new_degenerate_outline(self):
        def split(level, sector_id, use_splice):
            loops = _sector_loops(level, sector_id)
            outer_loop = max(loops, key=lambda loop: abs(area2(tuple(loop))))
            outer = [(int(x), int(y)) for x, y in outer_loop]
            if area2(tuple(outer)) < 0:
                outer.reverse()
            for loop in loops:
                if loop is outer_loop:
                    continue
                hole = [(int(x), int(y)) for x, y in loop]
                if area2(tuple(hole)) > 0:
                    hole.reverse()
                if use_splice:
                    spliced = _splice_flush_hole(outer, hole)
                    if spliced is not None:
                        outer = spliced
            return outer

        def degenerate(outline):
            return area2(tuple(outline)) <= 0 or len(set(outline)) != len(outline)

        folded = 0
        for path in campaign_maps():
            level = LevelIR.from_disk_map(read_map(path))
            for sector_id in range(len(level.sectors)):
                try:
                    loops = _sector_loops(level, sector_id)
                except Exception:
                    continue
                if len(loops) < 2:
                    continue
                plain = split(level, sector_id, False)
                joined = split(level, sector_id, True)
                if len(joined) != len(plain):
                    folded += 1
                with self.subTest(map=path.stem, sector=sector_id):
                    if not degenerate(plain):
                        self.assertFalse(degenerate(joined))
        # The fix has to actually apply somewhere, or it is untested cover.
        self.assertGreater(folded, 20)


if __name__ == "__main__":
    unittest.main()
