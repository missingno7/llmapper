"""The three censuses, and the properties that keep them honest.

Each census answers a question one map cannot: E3M1's 414 is one level's
choice, its 50.6% bend continuity is one level's habit, its 1122 indoor pairs
are one level's plan. So the tests check the corpus numbers where the corpus
is available, and the per-map function's own invariants always.

The one rule that matters most: **nothing here adds a row to `joins.ROWS`.**
The outdoor table can be trusted because a pair with no row is a loud failure;
a census that quietly grew it would end that.
"""

from __future__ import annotations

import unittest


def _map(stem: str):
    from bloodmap.format import read_map
    from bloodmap.patterns import corpus_map_path

    path = corpus_map_path(stem, missing_ok=True)
    if not path.exists():
        raise unittest.SkipTest(f"{stem} is not in the corpus")
    return read_map(path).to_level_ir()


def _art():
    import os

    from bloodmap.texture_align import wall_art_sizes

    sizes = wall_art_sizes(os.environ.get("BLOODMAP_ART", "reference/blood"))
    if not sizes:
        raise unittest.SkipTest("no Blood ART; set BLOODMAP_ART")
    return sizes


class TheCensusAddsNoRow(unittest.TestCase):
    def test_the_writers_table_is_the_same_size_after_a_census(self):
        from bloodmap import joins
        from bloodmap.read_census import census, proposed_indoor_rows

        before = len(joins.ROWS)
        summary = census([_map("E3M1")], names=["E3M1"], art_sizes=_art())
        proposed_indoor_rows(summary)
        self.assertEqual(len(joins.ROWS), before)

    def test_a_proposed_row_says_it_is_proposed(self):
        from bloodmap.read_census import census, proposed_indoor_rows

        summary = census([_map("E3M1")], names=["E3M1"], art_sizes=_art())
        for row in proposed_indoor_rows(summary, floor_share=0.0):
            self.assertIn("proposed_row", row)
            self.assertIn("records", row)
            self.assertIn("maps", row)

    def test_a_class_one_map_has_is_not_a_proposal(self):
        """One map's habit is not a row."""
        from bloodmap.read_census import census, proposed_indoor_rows

        summary = census([_map("E3M1")], names=["E3M1"], art_sizes=_art())
        self.assertEqual(proposed_indoor_rows(summary), [],
                         "a single map cannot justify an indoor row")


class OnE3M1(unittest.TestCase):
    """The per-map functions reproduce what layer 3 already found."""

    def setUp(self):
        self.level = _map("E3M1")
        self.sizes = _art()

    def test_the_end_wall_census_finds_layer_threes_records(self):
        from bloodmap.read_census import end_wall_tiles

        rows = end_wall_tiles(self.level)
        self.assertEqual(rows["tiles"]["road|end_wall"], {414: 3})
        self.assertEqual(rows["blocking"]["road|end_wall"], {1: 3})
        #: 9, not the 13 of the first reading: item 28c moved E3M1's two
        #: moving masses out of `end_wall`, so the four records facing them
        #: are no longer end-wall joins. The census population moved with the
        #: kind, which is why it is re-run whenever a kind changes.
        self.assertEqual(sum(rows["tiles"]["pavement|end_wall"].values()), 9)

    def test_the_continuity_census_agrees_with_continuity_rows(self):
        """`texture_frame.continuity_rows` predates this module and measures
        the same x continuity. If the two ever disagree, one is wrong."""
        from bloodmap.read_census import u_continuity
        from bloodmap.texture_frame import continuity_rows

        mine = u_continuity(self.level, self.sizes)
        theirs = continuity_rows(self.level, self.sizes)
        for name, row in theirs.items():
            self.assertEqual(mine["by_class"][name]["n"], row["n"], name)
            self.assertEqual(mine["by_class"][name]["u_continues"], row["x"], name)

    def test_the_interior_census_covers_layer_threes_undescribed_pairs(self):
        from bloodmap.read_census import interior_pairs
        from bloodmap.read_joins import read_joins

        pairs = interior_pairs(self.level)
        census_total = pairs["records"]
        joins = read_joins(self.level)["census"]["undescribed"]
        undescribed = sum(count for key, count in joins.items()
                          if key.startswith("interior|interior"))
        self.assertEqual(census_total, undescribed)

    def test_a_class_carries_the_angle_it_was_measured_at(self):
        """A bend of 12 degrees and one of 89 are the same class and not the
        same decision, so the class carries its own spread."""
        from bloodmap.read_census import u_continuity

        rows = u_continuity(self.level, self.sizes)["by_class"]
        for row in rows.values():
            self.assertIn("turn_degrees", row)
            self.assertGreater(row["turn_degrees"]["n"], 0)


class TheShadeStepEnvelope(unittest.TestCase):
    def test_the_network_definition_is_named_in_the_answer(self):
        """The gate must say which network it means, because the answer moves
        with it. A function that returned a bare number could not."""
        from bloodmap.read_light import shade_step_envelope

        rows = shade_step_envelope([_map("E3M1")], names=["E3M1"],
                                   network="all_parallax")
        self.assertEqual(rows["network"], "all_parallax")
        self.assertIn("envelope", rows)
        self.assertIn("current_gate", rows)

    def test_an_unknown_network_is_refused(self):
        from bloodmap.light_field import FieldError
        from bloodmap.read_light import shade_step_envelope

        with self.assertRaises(FieldError):
            shade_step_envelope([], network="whatever the caller meant")

    def test_e3m1s_own_step_is_outside_the_gate_under_both_definitions(self):
        from bloodmap.light_field import STEP_ENVELOPE
        from bloodmap.read_light import NETWORKS, shade_step_envelope

        low, high = STEP_ENVELOPE
        for network in NETWORKS:
            rows = shade_step_envelope([_map("E3M1")], names=["E3M1"],
                                       network=network)
            median = rows["envelope"]["median"]
            self.assertFalse(low <= median <= high,
                             f"{network}: median {median} is inside the gate")


if __name__ == "__main__":
    unittest.main()
