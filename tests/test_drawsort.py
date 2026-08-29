"""Build's draw-order predicate, and what it does and does not predict.

`bloodmap.drawsort.wallfront` is a transcription of engine.cpp:2227 rather than
a model of it, so the tests here are of two kinds: that the transcription is
faithful, and that the thing it detects is reported at the severity the campaign
actually assigns it.

The second kind matters more than it looks. A predicate can be exact and still
be the wrong gate, and this one is: 91.1% of the campaign's overlapping sector
pairs have a wall pair it refuses to rank, because putting one sector directly
over another with the same outline is how Blood builds stacked space at all.
"""

from __future__ import annotations

import unittest

from bloodmap import drawsort as ds


class PredicateTests(unittest.TestCase):
    def test_two_segments_on_one_line_are_refused(self):
        self.assertEqual(ds.wallfront(((0, 0), (1024, 0)), ((2048, 0), (3072, 0))),
                         ds.COLLINEAR)

    def test_collinear_holds_however_far_apart_they_are(self):
        """The predicate is about the two lines, not the two spans.

        `t1 == 0 && t2 == 0` says the second segment's endpoints are both on the
        first's *infinite* line. Nothing in it asks whether the spans meet.
        """
        self.assertEqual(ds.wallfront(((0, 0), (16, 0)), ((30000, 0), (30016, 0))),
                         ds.COLLINEAR)

    def test_properly_crossing_segments_are_refused(self):
        self.assertEqual(ds.wallfront(((0, 0), (1024, 1024)), ((0, 1024), (1024, 0))),
                         ds.CROSSING)

    def test_touching_at_a_shared_corner_is_not_a_crossing(self):
        """Two walls of one room meet end to end; that must stay orderable."""
        verdict = ds.wallfront(((0, 0), (1024, 0)), ((1024, 0), (1024, 1024)),
                               viewer=(512, -2048))
        self.assertGreaterEqual(verdict, 0)

    def test_the_answer_names_the_nearer_wall_the_callers_way(self):
        """`if (j == 0) closest = i`, engine.cpp:9736 -- 0 means l1 is in front."""
        near = ((0, 0), (1024, 0))
        far = ((0, 512), (1024, 512))
        self.assertEqual(ds.wallfront(near, far, viewer=(512, -512)), 0)
        self.assertEqual(ds.wallfront(far, near, viewer=(512, -512)), 1)

    def test_the_shift_is_part_of_the_predicate(self):
        """`dmulscale2` floors by 2 bits, so a cross product of 3 reads as zero.

        Emulating that is the difference between reproducing the engine and
        approximating it: these two segments are *not* collinear, and the engine
        still calls them collinear.
        """
        self.assertEqual(ds.dmulscale2(3, 1, 0, 0), 0)
        self.assertEqual(ds.dmulscale2(4, 1, 0, 0), 1)
        near_miss = ds.wallfront(((0, 0), (3, 0)), ((0, -1), (3, -1)))
        self.assertEqual(near_miss, ds.COLLINEAR,
                         "a sub-4 cross product must read as on-the-line, "
                         "because that is what the engine does with it")

    def test_a_verdict_is_independent_of_where_the_viewer_stands(self):
        a, b = ((0, 0), (1024, 0)), ((2048, 0), (3072, 0))
        for viewer in [(0, 0), (5000, 5000), (-9000, 300), None]:
            self.assertEqual(ds.wallfront(a, b, viewer=viewer), ds.COLLINEAR)


class StackedFootprintTests(unittest.TestCase):
    """Why this is a note and not a gate."""

    @staticmethod
    def _rect(x0, y0, x1, y1):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return [(pts[i], pts[(i + 1) % 4]) for i in range(4)]

    def test_one_room_over_another_on_the_same_outline_is_all_refusals(self):
        """The campaign's own way of stacking space, and it fails every pair."""
        same = self._rect(0, 0, 4096, 4096)
        hits = ds.segments_unorderable(same, same)
        self.assertEqual(len(hits), 4, "each wall lies on exactly its own twin")
        self.assertTrue(all(v == ds.COLLINEAR for _i, _j, v in hits))

    def test_setting_the_upper_room_in_clears_every_one_of_them(self):
        """Inset on all four sides and no wall of one is on a line with the other.

        This is the whole architectural instruction, and it is cheap: 256 units,
        one foot of floor.
        """
        lower = self._rect(0, 0, 4096, 4096)
        upper = self._rect(256, 256, 3840, 3840)
        self.assertEqual(ds.segments_unorderable(lower, upper), [])

    def test_a_jog_clears_it_where_an_inset_cannot(self):
        """Rooms that go different ways before they overlap satisfy it for free."""
        lower = self._rect(0, 0, 4096, 4096)
        turned = [((512, 1024), (3000, 1500)), ((3000, 1500), (2500, 3000)),
                  ((2500, 3000), (512, 1024))]
        self.assertEqual(ds.segments_unorderable(lower, turned), [])


if __name__ == "__main__":
    unittest.main()
