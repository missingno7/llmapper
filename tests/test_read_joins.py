"""Surface kinds read off geometry, and the join table counted against them.

The reader must not be able to flatter the table. Two properties keep it
honest and both are asserted here:

* it adds no row -- a pair `joins.ROWS` does not hold is reported, never
  defaulted;
* it reads kinds from what a body can do, not from a tile. `joins.py` states
  that surface kind is not readable from a tile, so a test that recovered
  `road` by looking for 352 would be testing our own habit.
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


class TheReaderAddsNoRow(unittest.TestCase):
    def test_every_pair_it_reports_as_described_is_in_the_table(self):
        from bloodmap import joins
        from bloodmap.read_joins import read_joins

        result = read_joins(_e3m1())
        for key in result["census"]["described"]:
            a, b, height = key.split("|")
            joins.rule(a, b, height)          # raises if it is not a row

    def test_every_undescribed_pair_really_has_no_row(self):
        from bloodmap import joins
        from bloodmap.read_joins import read_joins

        result = read_joins(_e3m1())
        for key in result["census"]["undescribed"]:
            a, b, height = key.split("|")
            with self.assertRaises(joins.JoinError):
                joins.rule(a, b, height)


class E3M1sStreet(unittest.TestCase):
    """Absolute numbers, read off the map, against the owner's own reading."""

    def setUp(self):
        from bloodmap.read_joins import read_joins

        self.result = read_joins(_e3m1())
        self.kinds = self.result["kinds"]
        self.census = self.result["census"]

    def test_the_rise_is_measured_as_2048_on_eleven_steps(self):
        """`HeightIsland.rise` defaults to 2048 because E3M1 does. The reader
        counts the steps rather than agreeing with the default."""
        self.assertEqual(self.kinds["measured_rise"], 2048)
        self.assertEqual(self.kinds["steps_in_the_network"][2048], 11)

    def test_eleven_of_eleven_kerb_records_wear_tile_6(self):
        """The measured fact the whole street model rests on, recovered."""
        row = "road|pavement|b_above"
        self.assertEqual(self.census["described"][row], 11)
        self.assertEqual(self.census["band_tiles"][row], {6: 11})
        self.assertEqual(self.census["table_tile_matches"][row], [11, 11])
        self.assertEqual(self.census["band_blocking"][row], {0: 11})

    def test_the_road_is_the_base_plane_and_is_found_without_a_tile(self):
        kinds = self.kinds["kinds"]
        road = sorted(key for key, value in kinds.items() if value == "road")
        self.assertEqual(road, [3, 7, 8, 45])
        self.assertEqual(self.kinds["base_plane_z"], 10240)

    def test_exactly_three_end_walls_are_met_by_a_road(self):
        """The owner's reading: "the T of the main street ends in three end
        walls (0, 339, 343)". The reader finds ten wall-top masses and three
        of them are what a ROAD runs into -- which is the same statement.

        Still three, and now under two names. Item 32c split `facade` off
        `end_wall`, and 343 is part of E3M1's one building: the four-sector
        mass 118/165/166/343, whose top wears 379 and whose room is ceilinged
        379. The T still ends in three masses; one of them has rooms in it,
        and the test reads both rows rather than the one that used to hold
        all three.
        """
        level = _e3m1()
        records = (self.census["described_records"]["road|end_wall|b_above"]
                   + self.census["described_records"]["road|facade|b_above"])
        met = sorted({int(level.walls[record]["fields"]["next_sector"])
                      for record in records})
        self.assertEqual(met, [0, 339, 343])
        terminations = sorted(
            {int(level.walls[record]["fields"]["next_sector"])
             for record in self.census["described_records"]["road|end_wall|b_above"]})
        self.assertEqual(terminations, [0, 339])

    def test_s10_and_s11_are_solid_masses_not_a_pavement_path(self):
        """`joins.py`'s pavement|pavement row cites them as "a pavement-only
        path". Both have floor_z == ceiling_z: nothing draws inside and no
        body stands in either. The row survives on other records; its cited
        evidence does not."""
        level = _e3m1()
        for sector in (10, 11):
            fields = level.sectors[sector]["fields"]
            self.assertEqual(int(fields["floor_z"]), int(fields["ceiling_z"]))
            self.assertEqual(self.kinds["kinds"][sector], "solid")
        self.assertGreater(self.census["described"]["pavement|pavement|equal"], 0)

    def test_the_table_describes_the_building_now_as_well(self):
        """It used to describe 66 of 1386 and the building was the residue.

        Two items landed on it within a day and both raised the number.

        Item 37e landed the indoor law -- ONE row keyed on the height
        relation, because the campaign's 25 mirrored interior|interior classes
        say one thing and it is `wallVisible`: the record whose neighbour
        stands above is the one that draws. The 1122 interior|interior records
        that were residue are described by three rows.

        Item 32c then split `facade` and `opening` off `end_wall` and
        `interior`. E3M1 has one building -- the four-sector mass
        118/165/166/343, whose top wears 379 and whose room is ceilinged 379
        -- and one shopfront, sector 206. Both reach rows the writer's table
        has carried since the grammar was written and no reader could produce.

        1188 after the indoor law, 1190 after the two kinds: E3M1's shopfront
        stopped being an interior, so the two records between it and room 208
        are `interior|opening` and `opening|interior`, which the table
        describes. 196 remain, and they are what the grammar still has no row
        for -- a mass meeting a solid, a mechanism at rest meeting anything,
        a facade meeting a facade.
        """
        from bloodmap.read_joins import summary

        stats = summary(self.result)
        self.assertEqual(stats["two_sided_records"], 1386)
        self.assertEqual(stats["records_described"], 1190)
        interior = sum(count for key, count in self.census["undescribed"].items()
                       if key.startswith("interior|interior"))
        self.assertEqual(interior, 0)

    def test_a_raised_mass_that_moves_is_not_an_end_wall(self):
        """Item 28c, and it is what the blocking clause was tripping over.

        Five band records used not to block, and four of them faced sectors
        172 and 174, which carry type 600. Those two are now
        `mechanism_at_rest` and their records are not end-wall joins at all,
        so one disagreement remains -- wall 1529, facing the raised ledge
        s237, which really does not block and really is not a mechanism.
        """
        kinds = self.kinds["kinds"]
        self.assertEqual(kinds[172], "mechanism_at_rest")
        self.assertEqual(kinds[174], "mechanism_at_rest")
        #: AND THE LAST DISAGREEMENT IS GONE, because item 37c took the
        #: clause out rather than the record: 269 of the campaign's 285
        #: road-side end-wall band records do not block, so wall 1529 was
        #: never the exception -- the row was.
        self.assertEqual(self.census["cstat_disagreements"], [])


if __name__ == "__main__":
    unittest.main()
