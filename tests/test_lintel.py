"""The lintel band: finding a painted course and placing it in the world.

`reports/blood-lintel-band.md`. Blood paints its cornices and plinths into the
wall art rather than building them, so the band a shopfront sign appears to sit
on lives at a fixed texture row. `art.course_rows` finds it and
`texture_align.course_z` puts it in the world.

It is recoverable, and it is not what places a sign. Both halves are pinned
here.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from bloodmap.art import ArtTile, COURSE_SIGMA, course_rows, row_luminance
from bloodmap.texture_align import PANNING_PERIOD, course_z, repeat_span


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "blood-lintel-band.json"

#: A greyscale ramp, so palette index n has luminance n. Index 255 is
#: Build's transparency and never reaches the palette, so fixtures stay
#: below it.
GREY = tuple((n, n, n) for n in range(256))
DARK, LIGHT = 40, 200


def tile(rows, *, width=4, number=1):
    """A tile from a list of per-row palette indices. ART is column-major."""
    height = len(rows)
    pixels = bytes(rows[y] for x in range(width) for y in range(height))
    return ArtTile(tile=number, width=width, height=height, pixels=pixels)


class CourseRowTests(unittest.TestCase):
    def test_a_flat_tile_has_no_course(self):
        self.assertEqual(course_rows(tile([DARK] * 32), GREY), [])

    def test_a_banded_tile_reports_the_row_below_the_change(self):
        """A course is the edge between two rows, and belongs to the lower."""
        rows = [LIGHT] * 4 + [DARK] * 28
        self.assertEqual(course_rows(tile(rows), GREY), [4])

    def test_a_cornice_and_a_plinth_are_both_found(self):
        rows = [LIGHT] * 3 + [DARK] * 26 + [LIGHT] * 3
        self.assertEqual(course_rows(tile(rows), GREY), [3, 29])

    def test_row_zero_is_never_a_course(self):
        """There is no row above it for the edge to be between."""
        for rows in ([LIGHT] * 4 + [DARK] * 28, [DARK] * 32, list(range(32))):
            self.assertNotIn(0, course_rows(tile(rows), GREY))

    def test_an_even_gradient_is_not_a_course_on_every_row(self):
        """A ramp changes every row by the same amount, so the edges have no
        spread at all and nothing stands out above them. Without the guard the
        threshold collapses onto the mean and every row reports a band.
        """
        self.assertEqual(course_rows(tile(list(range(0, 64, 2))), GREY), [])

    def test_the_threshold_is_a_named_argument(self):
        """One strong band and a faint one: strict finds the band, loose both."""
        rows = [LIGHT] * 4 + [DARK] * 12 + [DARK + 40] * 16
        strict = course_rows(tile(rows), GREY, sigma=COURSE_SIGMA)
        loose = course_rows(tile(rows), GREY, sigma=0.5)
        self.assertEqual(strict, [4], "only the strong band")
        self.assertEqual(loose, [4, 16], "the faint one as well")

    def test_luminance_is_a_row_average_over_the_whole_width(self):
        profile = row_luminance(tile([0, LIGHT], width=8), GREY)
        self.assertAlmostEqual(profile[0], 0.0, places=3)
        self.assertAlmostEqual(profile[1], float(LIGHT), places=1)

    def test_luminance_is_perceived_brightness_not_one_channel(self):
        """Blood's palettes are not grey. A course between a red row and a
        green row of the same channel value is a real edge to the eye, and
        reading one channel would miss or invent it.
        """
        palette = tuple([(0, 0, 0)] * 256)
        palette = list(palette)
        palette[1], palette[2] = (255, 0, 0), (0, 255, 0)
        palette = tuple(palette)
        red, green = row_luminance(tile([1, 2], width=4), palette)
        self.assertAlmostEqual(red, 76.2, places=0)
        self.assertAlmostEqual(green, 149.7, places=0)
        self.assertGreater(green, red * 1.5)

    def test_a_one_row_tile_has_no_course(self):
        self.assertEqual(course_rows(tile([100]), GREY), [])


class CourseZTests(unittest.TestCase):
    """Blood's z grows downward, so a row measured up has a smaller z."""

    def test_the_anchor_row_is_the_anchor(self):
        self.assertEqual(course_z(-29696, 128, 8, 0), -29696)

    def test_a_row_measured_up_from_the_anchor_has_a_smaller_z(self):
        self.assertLess(course_z(-29696, 128, 8, 13), -29696)

    def test_a_row_measured_down_has_a_larger_z(self):
        self.assertGreater(course_z(-29696, 128, 8, 13, upward=False), -29696)

    def test_a_whole_tile_spans_one_repeat(self):
        self.assertEqual(course_z(0, 128, 8, 128), -repeat_span(128, 8))

    def test_the_e3m2_loading_bay_band(self):
        """The case that raised the question. Tile 80's bottom course is row
        115; hung from that bay's head at -29696 it lands at -33024, and the
        LOADING letters sit at -33792, three texture pixels above it.
        """
        self.assertEqual(course_z(-29696, 128, 8, 128 - 115), -33024)
        self.assertEqual((-33024 - -33792) / (repeat_span(128, 8) / 128), 3.0)

    def test_panning_shifts_the_whole_tile(self):
        """y_panning is one byte covering a whole repeat."""
        span = repeat_span(128, 8)
        shifted = course_z(0, 128, 8, 0, y_panning=PANNING_PERIOD // 2)
        self.assertEqual(shifted, -span // 2)

    def test_a_tile_with_no_span_cannot_move_the_anchor(self):
        self.assertEqual(course_z(-4096, 0, 8, 40), -4096)
        self.assertEqual(course_z(-4096, 128, 0, 40), -4096)

    def test_the_span_has_one_definition(self):
        self.assertEqual(abs(course_z(0, 64, 8, 64)), repeat_span(64, 8))


class EmittedLintelReportTests(unittest.TestCase):
    def setUp(self):
        if not REPORT.exists():
            self.skipTest("the lintel report has not been generated")
        self.doc = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_every_tile_carrying_signage_has_a_course_to_find(self):
        """The recoverability half: the band is really in the art."""
        self.assertTrue(self.doc["tiles"])
        for tile_row in self.doc["tiles"]:
            self.assertTrue(tile_row["course_rows"], tile_row["picnum"])

    def test_the_band_is_refuted_as_the_datum_against_its_own_null(self):
        """Not against zero -- these tiles carry six to eight courses each, so
        a random row is often near one. The comparison has to be the null.
        """
        band = self.doc["band_test"]
        self.assertLessEqual(band["letters_on_a_course"],
                             band["random_rows_on_a_course"])
        self.assertIn("refuted", band["verdict"])

    def test_no_candidate_datum_is_tight_enough_to_be_a_rule(self):
        """The report's conclusion is that there is no datum to miss, so a
        constructor may place a sign by habit and say so.
        """
        for scope in ("blood-campaign", "all"):
            best = min(d["coefficient_of_variation"]
                       for d in self.doc["datums"][scope])
            self.assertGreater(best, 0.25)

    def test_the_street_floor_beats_the_opening_head_as_a_datum(self):
        """Every campaign letter is above its opening's head, but the offset
        from it is looser than the height above the street -- the head is a
        constraint, not a datum.
        """
        by_name = {d["datum"]: d for d in self.doc["datums"]["all"]}
        street = by_name["height above the street floor, player heights"]
        head = by_name["height above its opening's head, player heights"]
        self.assertLess(street["coefficient_of_variation"],
                        head["coefficient_of_variation"])

    def test_curated_is_kept_separate(self):
        self.assertEqual(self.doc["populations"]["community-curated"],
                         "precedent, never convention")


if __name__ == "__main__":
    unittest.main()
