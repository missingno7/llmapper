"""Surfaces recovered from a map, and the residue that is the measurement.

The reader's claim is narrow and testable: group wall records into the
surfaces one projected material would have produced, and replay each recovered
frame through the WRITER (`texture_frame.resolve_run`). What comes back field
for field is explained; what does not is residue, named.

Two things these tests exist to stop:

* a reader that joins everything (residue would go to zero and mean nothing);
* a reader that joins nothing (every record becomes its own surface, which
  reproduces itself, and the map would read as fully understood for free).

So there is a fixture for each direction, and a corpus check against a reader
that already existed (`texture_frame.continuity_rows`) so the two cannot
quietly disagree.
"""

from __future__ import annotations

import os
import unittest
from copy import deepcopy

SIZES = {1: (64, 64), 2: (128, 64)}


def _square_level():
    """One 1024 square, one material, projected once around all four walls."""
    from tests.helpers import synthetic_map

    level = synthetic_map().to_level_ir()
    for index, wall in enumerate(level.walls):
        wall["fields"].update(picnum=1, x_repeat=8, y_repeat=8,
                              x_panning=0, y_panning=0, cstat=0)
    return level


def _art():
    from bloodmap.texture_align import wall_art_sizes

    sizes = wall_art_sizes(os.environ.get("BLOODMAP_ART", "reference/blood"))
    if not sizes:
        raise unittest.SkipTest("no Blood ART; set BLOODMAP_ART")
    return sizes


def _e3m1():
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [item for item in list_corpus_maps(population="blood-campaign")
             if item.path.stem.upper() == "E3M1"]
    if not found:
        raise unittest.SkipTest("E3M1 is not in the corpus")
    return read_map(found[0].path).to_level_ir()


class OneProjectionIsOneSurface(unittest.TestCase):
    def test_a_square_of_one_material_is_one_surface(self):
        from bloodmap.read_surfaces import read_surfaces

        result = read_surfaces(_square_level(), art_sizes=SIZES)
        self.assertEqual(len(result["surfaces"]), 1)
        surface = result["surfaces"][0]
        self.assertEqual(len(surface.records), 4)
        self.assertEqual(len(surface.exact), 4, surface.mismatches)
        self.assertEqual(result["residue_records"], [])

    def test_a_broken_panning_splits_the_surface_and_says_why(self):
        from bloodmap.read_surfaces import read_surfaces

        level = _square_level()
        level.walls[2]["fields"]["x_panning"] = 17      # a restarted run
        result = read_surfaces(level, art_sizes=SIZES)
        self.assertGreater(len(result["surfaces"]), 1)
        self.assertIn("u does not continue across the vertex",
                      result["census"]["breaks"])
        self.assertTrue(result["residue_broken"],
                        "a record that broke off its neighbour is residue")

    def test_a_second_scale_breaks_the_surface(self):
        from bloodmap.read_surfaces import read_surfaces

        level = _square_level()
        level.walls[2]["fields"]["x_repeat"] = 16
        result = read_surfaces(level, art_sizes=SIZES)
        self.assertIn("a different scale", result["census"]["breaks"])

    def test_a_lone_record_is_residue_not_understanding(self):
        """The asymmetry the whole ledger rests on.

        A frame fitted to one record reproduces that record. If such a record
        counted as explained, a map of 2481 unrelated walls would read as
        100% understood, which is the failure mode this test names.
        """
        from bloodmap.read_surfaces import read_surfaces

        level = _square_level()
        for index, wall in enumerate(level.walls):
            wall["fields"]["picnum"] = 1 + (index % 2)   # nothing continues
            wall["fields"]["x_repeat"] = 8 if index % 2 == 0 else 16
        result = read_surfaces(level, art_sizes=SIZES)
        self.assertEqual(result["records_explained"], [])
        self.assertEqual(len(result["residue_records"]), 4)


class TheFrameIsFittedNotAssumed(unittest.TestCase):
    def test_v0_is_solved_from_the_records_own_y_panning(self):
        """`v0` is a world z, and the records state it. Taking the first
        record's own peg forces its `y_panning` to zero, and E3M1's is not."""
        from bloodmap.read_surfaces import read_surfaces

        level = _square_level()
        for wall in level.walls:
            wall["fields"]["y_panning"] = 40
        result = read_surfaces(level, art_sizes=SIZES)
        surface = result["surfaces"][0]
        self.assertEqual(len(surface.exact), 4, surface.mismatches)
        self.assertNotEqual(surface.frame.v0, None)

    def test_a_panning_at_or_above_the_tile_width_is_not_a_mismatch(self):
        """96 on a 64-wide tile is 32: the same texel, a different spelling."""
        from bloodmap.read_surfaces import read_surfaces

        level = _square_level()
        for wall in level.walls:
            wall["fields"]["x_panning"] = 64        # == 0 modulo the width
        result = read_surfaces(level, art_sizes=SIZES)
        self.assertEqual(len(result["records_mismatched"]), 0)
        self.assertTrue(result["records_normalised"])


class E3M1(unittest.TestCase):
    """Absolute numbers off the original map, not shape checks."""

    def setUp(self):
        self.level = _e3m1()
        self.sizes = _art()

    def test_the_reader_agrees_with_the_reader_that_already_existed(self):
        """`continuity_rows` measures u continuity over same-tile `point2`
        joins and predates this module. If the surface partition joined
        materially more or fewer records than that, one of them is wrong."""
        from bloodmap.read_surfaces import read_surfaces
        from bloodmap.texture_frame import continuity_rows

        rows = continuity_rows(self.level, self.sizes)
        joins = sum(row["n"] for row in rows.values())
        continued = sum(row["x"] for row in rows.values())
        self.assertGreater(joins, 1000)
        rate = continued / joins
        result = read_surfaces(self.level, art_sizes=self.sizes)
        explained = len(result["records_explained"]) / result["records"]
        self.assertAlmostEqual(rate, explained, delta=0.10,
                               msg=f"{rate:.3f} vs {explained:.3f}")

    def test_most_of_e3m1_is_not_one_projection(self):
        """The finding, asserted so a change to the reader has to face it:
        E3M1 restarts its materials at corners. Only about a third of its
        records sit in a shared projection, and a reader that suddenly
        explained 90% of them has loosened the law, not learned something."""
        from bloodmap.read_surfaces import read_surfaces

        result = read_surfaces(self.level, art_sizes=self.sizes)
        self.assertEqual(result["records"], 2481)
        explained = len(result["records_explained"])
        self.assertGreater(explained, 600)
        self.assertLess(explained, 1000)
        self.assertEqual(len(result["records_unmeasurable"]), 0)

    def test_the_partition_covers_every_record_exactly_once(self):
        from bloodmap.read_surfaces import read_surfaces

        result = read_surfaces(self.level, art_sizes=self.sizes)
        seen = [index for item in result["surfaces"] for index in item.records]
        self.assertEqual(sorted(seen), list(range(len(self.level.walls))))
        self.assertEqual(len(seen), len(set(seen)))

    def test_reading_does_not_write(self):
        from bloodmap.read_surfaces import read_surfaces

        before = deepcopy(self.level.to_dict())
        read_surfaces(self.level, art_sizes=self.sizes)
        self.assertEqual(self.level.to_dict(), before,
                         "a reader that repairs its input measures its own repair")


if __name__ == "__main__":
    unittest.main()
