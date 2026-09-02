"""Islands and the light field, recovered from E3M1 and replayed through the
writer.

The two readers here answer questions the project has so far answered by
declaration: `HeightIsland.rise` is 2048 "because E3M1 is", the sun's bearing
is 478 "because the oblique edges cluster at 84 degrees", the field is
`base + k*12` "because the campaign's median delta is 12". Each of those is
now a measurement with a number that can come back wrong, and two of them do.
"""

from __future__ import annotations

import unittest


def _e3m1():
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [item for item in list_corpus_maps(population="blood-campaign")
             if item.path.stem.upper() == "E3M1"]
    if not found:
        raise unittest.SkipTest("E3M1 is not in the corpus")
    return read_map(found[0].path).to_level_ir()


class Islands(unittest.TestCase):
    def setUp(self):
        from bloodmap.read_islands import read_islands

        self.level = _e3m1()
        self.result = read_islands(self.level)

    def test_three_islands_at_a_measured_rise_of_2048(self):
        self.assertEqual(len(self.result["islands"]), 3)
        self.assertEqual(self.result["rise"], 2048)
        self.assertEqual(sorted(self.result["island_sectors"]),
                         [1, 2, 4, 5, 6, 9, 159, 175, 235])

    def test_every_kerb_record_the_map_makes_wears_tile_6(self):
        self.assertEqual(self.result["kerb_tiles_seen"], {6: 11})
        self.assertEqual(self.result["kerb_records_the_map_makes"], 11)

    def test_kerb_records_now_claims_exactly_what_the_map_makes(self):
        """The writer replayed over what the reader recovered.

        This test used to assert the DEFECT. `overlay.kerb_records` iterated
        the island's outline and never read its `ground_outline` argument, so
        it asked for a kerb on the edges facing a building, an interior and
        the void as well: **81 claims against the map's 11**, the 70 extra
        facing 56 edges of void, 18 of interior and 13 of end wall.

        Two things had to change for the numbers to meet. The writer emits one
        record per GROUND edge the island's boundary shares a stretch with,
        because the band goes on the ground's side and the two sides are not
        split alike -- E3M1's islands present 7 outline edges to the road and
        the road answers with 11 records. And the reader replays EVERY loop of
        an island: island:001 has two, and all four of its road-facing edges
        are on the shorter one.
        """
        self.assertEqual(self.result["kerb_records_the_writer_claims"], 11)
        self.assertEqual(self.result["kerb_records_the_writer_claims"],
                         self.result["kerb_records_the_map_makes"])
        self.assertEqual(self.result["islands_the_writer_over_claims"], [])

    def test_a_step_that_is_not_the_rise_is_residue(self):
        steps = self.result["steps_that_are_not_islands"]
        self.assertNotIn(2048, steps)
        self.assertEqual(sum(steps.values()), 15)


class TheSun(unittest.TestCase):
    def setUp(self):
        from bloodmap.read_light import read_light

        self.level = _e3m1()
        self.result = read_light(self.level)

    def test_the_bearing_comes_back_within_one_build_unit_of_478(self):
        """The project cites SUN_BEARING 478. The reader recovers the axis
        from the oblique boundaries and the sign from the perpendicular ones,
        and gets 479 -- 0.18 degrees apart, with nothing typed in."""
        self.assertEqual(self.result["axis"]["axis_degrees"], 84.2)
        self.assertEqual(self.result["sign"]["throw_bearing_units"], 479)
        self.assertTrue(self.result["sign"]["decided"])
        self.assertEqual(self.result["sign"]["votes"],
                         {"along the axis": 6, "against it": 0})

    def test_the_sign_is_decided_by_the_shadows_far_ends(self):
        """A boundary perpendicular to the axis is a shadow's far end and the
        shadow is up-sun of it. Without that, the field fixes the bearing only
        modulo 180."""
        self.assertGreater(self.result["sign"]["far_end_boundaries"], 0)
        for ballot in self.result["sign"]["ballots"]:
            self.assertEqual(ballot["vote"], "+")

    def test_two_oblique_edges_are_not_at_the_bearing(self):
        axis = self.result["axis"]
        self.assertEqual(axis["oblique_edges"], 16)
        self.assertEqual(axis["cluster_records"], 14)
        self.assertEqual(axis["residue_edges_off_the_bearing"], [643, 857])
        self.assertEqual(axis["residue_axes"], [71.08])

    def test_e3m1s_own_step_is_not_the_campaigns_and_fails_the_envelope(self):
        """The finding. `light_field.STEP` is 12 with an envelope of [8, 16],
        and E3M1 -- the map the street language was read from -- has deltas of
        24 and 26 on 20 of its 22 boundary records."""
        from bloodmap.light_field import STEP, STEP_ENVELOPE

        step = self.result["step"]
        self.assertEqual(step["deltas"], {12: 2, 24: 6, 26: 14})
        self.assertEqual(step["median"], 26)
        self.assertNotEqual(step["median"], STEP)
        low, high = STEP_ENVELOPE
        self.assertEqual(step["outside_it"], 20)
        self.assertFalse(low <= step["median"] <= high)

    def test_the_base_and_the_level_count_do_hold(self):
        """The half of the decision that survives: the lit base is the
        network's own (8, as cited) and the field has 2-4 significant
        levels."""
        from bloodmap.light_field import MAX_LEVELS

        field = self.result["field"]
        self.assertEqual(field["lit_base"], 8)
        self.assertGreaterEqual(field["significant_count"], 2)
        self.assertLessEqual(field["significant_count"], MAX_LEVELS)

    def test_the_casters_are_not_recovered_and_the_reader_says_so(self):
        """8 up-sun against 8 down-sun is a tie. A reader that reported a
        caster anyway would be naming one the geometry does not choose."""
        cast = self.result["casters"]
        self.assertEqual(cast["up_sun_end_is_a_mass_corner"],
                         cast["down_sun_end_is_a_mass_corner"])

    def test_sectors_that_drive_their_own_shade_are_excluded_first(self):
        """A sector whose XSECTOR carries `amplitude` or `shade_always` drives
        its shade at run time, so its `floor_shade` is a phase of a wave and
        not a sample of the sun. E3M1 has 61 such sectors; ONE of them (s174)
        is in the street network, and it lies on no same-z shade boundary, so
        excluding them removes 0 of the 22 shade-edge records and one sector
        from the field's levels. A true zero, measured rather than assumed.
        """
        self.assertEqual(
            len(self.result["sectors_driving_their_own_shade_in_the_whole_map"]),
            61)
        self.assertEqual(self.result["sectors_driving_their_own_shade"], [174])
        self.assertEqual(
            self.result["shade_edge_records_the_wave_exclusion_removes"], 0)
        self.assertNotIn(174, self.result["field"]["levels"])

    def test_the_extras_are_read_through_the_key_a_levelir_uses(self):
        """The accessor bug this test exists to keep fixed. A `LevelIR` carries
        a record's Blood extra under `"blood"`, not under an `extra`
        attribute; reading it the other way reports a map with 133 XSECTORs as
        having none, which is what an earlier pass of this reader did."""
        with_extras = sum(1 for sector in self.level.sectors
                          if sector.get("blood"))
        self.assertEqual(with_extras, 133)
        self.assertEqual(sum(1 for wall in self.level.walls
                             if wall.get("blood")), 41)
        self.assertEqual(sum(1 for sprite in self.level.sprites
                             if sprite.get("blood")), 716)

    def test_the_lamps_are_fullbright_sprites(self):
        self.assertEqual(self.result["lamps"]["fullbright_sprites"], 46)


if __name__ == "__main__":
    unittest.main()
