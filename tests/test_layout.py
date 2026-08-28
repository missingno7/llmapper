"""Sizing, quarter-turns, and the one-time stamp.

Three pieces of the layout half of the representation, each targeting a fault
that the previous representation made easy:

* **thin walls**, because nothing owned the space between two parts, so extending
  a corridor silently ate the mass beyond it;
* **rotation**, because `Frame` refused all of it on an argument that is only
  true of arbitrary angles;
* **texture and slope direction under rotation**, because a sector's slope and
  its first-wall-relative alignment reference the first wall while sprite angles
  are absolute, so half of a rotated room follows and half does not.
"""

from __future__ import annotations

import unittest


class RunTests(unittest.TestCase):

    def _cloister(self, chapel: int | None = None):
        """A walk between two fixed ends, optionally with a chapel inserted."""
        from bloodmap.layout import Fixed, Flex, Wall, run

        parts = [
            Fixed(name="porch", extent=1024),
            Wall(name="porch_wall", extent=256),
            Flex(name="walk", low=1152),
        ]
        if chapel is not None:
            parts += [Wall(name="chapel_wall", extent=256),
                      Fixed(name="chapel", extent=chapel)]
        parts += [Wall(name="chancel_wall", extent=256),
                  Fixed(name="chancel", extent=1536)]
        return run("run:cloister", *parts, total=8192)

    def test_a_run_resolves_to_offsets_that_tile_the_span(self):
        placed = self._cloister().resolve()
        self.assertEqual(placed[0].offset, 0)
        self.assertEqual(placed[-1].end, 8192)
        for earlier, later in zip(placed, placed[1:]):
            self.assertEqual(earlier.end, later.offset, "parts must not overlap")

    def test_inserting_a_part_changes_only_the_flexible_one(self):
        """The whole feature: one number moves, and it is the one whose job is
        to move."""
        before = {p.name: p.extent for p in self._cloister().resolve()}
        after = {p.name: p.extent for p in self._cloister(chapel=1024).resolve()}

        for name in ("porch", "porch_wall", "chancel_wall", "chancel"):
            self.assertEqual(before[name], after[name],
                             "%s should not have moved" % name)
        self.assertEqual(before["walk"] - after["walk"], 1024 + 256)

    def test_squeezing_the_flexible_part_too_far_names_what_does_not_fit(self):
        from bloodmap.layout import LayoutError

        with self.assertRaises(LayoutError) as caught:
            self._cloister(chapel=4096).resolve()
        message = str(caught.exception)
        self.assertIn("short", message)
        self.assertIn("walk>=1152", message)
        self.assertIn("chapel=4096", message)

    def test_a_run_with_nothing_flexible_must_add_up(self):
        from bloodmap.layout import Fixed, LayoutError, run

        with self.assertRaises(LayoutError) as caught:
            run("run:rigid", Fixed(name="a", extent=1024),
                Fixed(name="b", extent=1024), total=4096).resolve()
        self.assertIn("nothing to absorb", str(caught.exception))

    def test_two_flexible_parts_share_the_residual_by_weight(self):
        from bloodmap.layout import Fixed, Flex, run

        placed = {p.name: p.extent for p in run(
            "run:two", Fixed(name="end", extent=1024),
            Flex(name="wide", low=384, weight=3.0),
            Flex(name="narrow", low=384, weight=1.0),
            total=1024 + 384 + 384 + 800).resolve()}
        self.assertEqual(placed["wide"] + placed["narrow"], 384 * 2 + 800)
        self.assertEqual(placed["wide"] - 384, 600)
        self.assertEqual(placed["narrow"] - 384, 200)

    def test_the_run_total_is_exact_even_when_the_weights_do_not_divide(self):
        from bloodmap.layout import Fixed, Flex, run

        placed = run("run:odd", Fixed(name="end", extent=100),
                     Flex(name="a", low=10, weight=1.0),
                     Flex(name="b", low=10, weight=1.0),
                     Flex(name="c", low=10, weight=1.0),
                     total=100 + 30 + 100).resolve()
        self.assertEqual(placed[-1].end, 230)


class WallThicknessTests(unittest.TestCase):

    def test_the_minimum_comes_from_the_campaign(self):
        from bloodmap.layout import MIN_WALL

        self.assertEqual(MIN_WALL, 128)

    def test_a_wall_thinner_than_the_minimum_is_refused(self):
        from bloodmap.layout import LayoutError, Wall

        with self.assertRaises(LayoutError) as caught:
            Wall(name="squeeze", extent=16)
        message = str(caught.exception)
        self.assertIn("thin_because", message)
        self.assertIn("Flex", message, "the message should name the real fix")

    def test_a_thin_wall_that_says_why_is_allowed(self):
        """Blood builds these -- 2.64% of its room pairs -- and always means it."""
        from bloodmap.layout import Wall

        self.assertEqual(Wall(name="panel", extent=16,
                              thin_because="fake_wall").extent, 16)

    def test_a_reason_has_to_be_one_of_the_known_ones(self):
        from bloodmap.layout import LayoutError, Wall

        with self.assertRaises(LayoutError):
            Wall(name="panel", extent=16, thin_because="because I said so")

    def test_the_registry_grades_it_as_a_habit_not_a_law(self):
        from bloodmap.rules import load_grades

        grades = load_grades()
        grade = grades.get("wall-between-rooms-is-not-paper")
        if grade is None:
            self.skipTest("rules not graded")
        self.assertEqual(grade.severity, "warning")
        self.assertLess(grade.rate, 0.05)


class QuarterTurnTests(unittest.TestCase):
    """k x 90 is exact on the integer grid; that is the whole argument."""

    def test_a_quarter_turn_is_exact(self):
        from bloodmap.levelprog import Frame

        square = [(0, 0), (1024, 0), (1024, 512), (0, 512)]
        turned = Frame(turns=1)
        for point in square:
            x, y = turned.apply(point)
            self.assertEqual((x, y), (-point[1], point[0]))

    def test_four_turns_are_the_identity_with_no_residual(self):
        from bloodmap.levelprog import Frame

        point = (12345, -6789)
        current = point
        for _ in range(4):
            current = Frame(turns=1).apply(current)
        self.assertEqual(current, point)

    def test_turns_compose_exactly(self):
        from bloodmap.levelprog import Frame

        point = (700, 300)
        once = Frame(turns=1).compose(Frame(turns=1))
        self.assertEqual(once.turns, 2)
        self.assertEqual(once.apply(point), Frame(turns=2).apply(point))

    def test_composition_turns_the_childs_offset_into_the_parents_space(self):
        """The bug a naive implementation has: a child 1024 east of its parent
        is 1024 *north* once the parent is quarter-turned."""
        from bloodmap.levelprog import Frame

        parent = Frame(turns=1)
        child = Frame(dx=1024, dy=0)
        self.assertEqual(parent.compose(child).apply((0, 0)),
                         parent.apply(child.apply((0, 0))))
        self.assertEqual(parent.compose(child).apply((0, 0)), (0, 1024))

    def test_unturn_undoes_turn(self):
        from bloodmap.levelprog import Frame

        for turns in range(4):
            frame = Frame(turns=turns)
            self.assertEqual(frame.unturn(frame.turn((913, -457))), (913, -457))

    def test_a_quarter_turn_preserves_winding(self):
        """Determinant +1. If it did not, every rotated room would compile with
        its outer loop inside out."""
        from bloodmap.planar_geom import area2
        from bloodmap.levelprog import Frame

        square = [(0, 0), (1024, 0), (1024, 512), (0, 512)]
        for turns in range(4):
            turned = [Frame(turns=turns).apply(p) for p in square]
            self.assertEqual(area2(square) > 0, area2(turned) > 0)

    def test_a_sprite_angle_turns_with_the_frame(self):
        from bloodmap.levelprog import Frame

        self.assertEqual(Frame(turns=1).apply_angle(0), 512)
        self.assertEqual(Frame(turns=3).apply_angle(1536), 1024)
        self.assertEqual(Frame(turns=0).apply_angle(300), 300)


class StampTests(unittest.TestCase):
    """Arbitrary angles: composed in floats, rounded once, never nested."""

    def test_a_stamp_rotates_an_outline(self):
        from bloodmap.vocabulary import stamp

        turned = stamp([(0, 0), (1000, 0), (1000, 1000), (0, 1000)], 90)
        self.assertEqual(turned, [(0, 0), (0, 1000), (-1000, 1000), (-1000, 0)])

    def test_rounding_residual_is_bounded_at_half_a_unit(self):
        from math import cos, radians, sin
        from bloodmap.vocabulary import stamp

        outline = [(0, 0), (1024, 0), (1024, 768), (0, 768)]
        theta = radians(37.0)
        exact = [(x * cos(theta) - y * sin(theta), x * sin(theta) + y * cos(theta))
                 for x, y in outline]
        for (ex, ey), (gx, gy) in zip(exact, stamp(outline, 37.0)):
            self.assertLessEqual(abs(ex - gx), 0.5 + 1e-9)
            self.assertLessEqual(abs(ey - gy), 0.5 + 1e-9)

    def test_a_shared_edge_comes_out_of_the_stamp_identical_on_both_sides(self):
        """The reason a one-time stamp is safe and a nested one is not: both
        rooms' copies of the shared edge are rounded from the same floats, so
        they land on the same integers and the planar overlay sees one edge."""
        from bloodmap.vocabulary import stamp

        shared = [(1024, 0), (1024, 768)]
        left = stamp([(0, 0), *shared, (0, 768)], 23.5, offset=(4096, 4096))
        right = stamp([*shared, (2048, 768), (2048, 0)], 23.5, offset=(4096, 4096))
        self.assertEqual(left[1], right[0])
        self.assertEqual(left[2], right[1])

    def test_about_turns_around_a_named_local_point(self):
        from bloodmap.vocabulary import stamp

        outline = [(0, 0), (1024, 0), (1024, 512), (0, 512)]
        self.assertEqual(stamp(outline, 90, about=(0, 0))[0], (0, 0))
        turned = stamp(outline, 180, about=(512, 256))
        self.assertEqual(turned[0], (1024, 512))

    def test_an_outline_too_small_to_survive_rounding_is_refused(self):
        from bloodmap.vocabulary import VocabularyError, stamp

        with self.assertRaises(VocabularyError):
            stamp([(0, 0), (1, 0), (1, 1), (0, 1)], 45)

    def test_a_stamped_sprite_keeps_pointing_the_same_way_in_the_world(self):
        from bloodmap.vocabulary import stamp_angle

        self.assertEqual(stamp_angle(0, 90), 512)
        self.assertEqual(stamp_angle(0, 45), 256)
        self.assertEqual(stamp_angle(1024, -90), 512)


class AlignmentUnderRotationTests(unittest.TestCase):
    """The half of rotation that is not geometry.

    Blood's own habit, from 13,649 playable sectors: 14.0% align the floor to
    the first wall overall, but split by cause it is 43.2% for sloped floors
    against 11.0% for flat ones, and only 17.6% for angled rooms against 12.2%
    for cardinal ones. Slope is the signal; rotation barely is.
    """

    def test_a_flat_angled_floor_stays_world_aligned(self):
        from bloodmap.vocabulary import stamp_alignment

        self.assertEqual(stamp_alignment(0, sloped=False, directional=False), 0)

    def test_a_sloped_floor_takes_relative_alignment(self):
        from bloodmap.vocabulary import RELATIVE_ALIGNMENT, stamp_alignment

        self.assertEqual(stamp_alignment(0, sloped=True, directional=False),
                         RELATIVE_ALIGNMENT)

    def test_a_directional_flat_takes_it_too(self):
        from bloodmap.vocabulary import RELATIVE_ALIGNMENT, stamp_alignment

        self.assertEqual(stamp_alignment(0, sloped=False, directional=True),
                         RELATIVE_ALIGNMENT)

    def test_existing_bits_survive(self):
        from bloodmap.vocabulary import RELATIVE_ALIGNMENT, stamp_alignment

        self.assertEqual(stamp_alignment(1, sloped=True, directional=False),
                         1 | RELATIVE_ALIGNMENT)

    def test_the_bit_is_the_one_the_engine_reads(self):
        """buildtypes.h:24 -- 'bit 6: 1 = Align texture to first wall'."""
        from bloodmap.vocabulary import RELATIVE_ALIGNMENT

        self.assertEqual(RELATIVE_ALIGNMENT, 1 << 6)
