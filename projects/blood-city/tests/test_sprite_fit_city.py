"""Sprite fit on the built city, and the city's wall-plane buckets."""

from __future__ import annotations

import unittest
from pathlib import Path

CITY = Path("projects/blood-city/level/blood-city-current.MAP")
E3M1 = Path("maps/blood/campaign/E3M1.MAP")
DWE3M1 = Path("maps/blood/curated/DWE3M1.MAP")


class OverlapTests(unittest.TestCase):
    def test_a_bucket_edge_does_not_hide_one_from_the_other(self):
        """8 units apart in depth is one wall: the fault that let six signs
        be written through pictures."""
        import sys

        sys.path.insert(0, "projects/blood-city/level")
        from bloodmap import wallplane

        a = wallplane._plane_key((0, 27174), (1.0, 0.0))
        b = wallplane._plane_key((0, 27182), (1.0, 0.0))
        self.assertNotEqual(a, b)              # the edge is real ...
        self.assertLessEqual(abs(a[2] - b[2]), 1)   # ... and one bucket wide


@unittest.skipUnless(CITY.exists(), "the city is not built")
class CityFitsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map
        from tools.sprite_fit import lint

        cls.disk = read_map(CITY)
        cls.lint = lint(cls.disk)

    def test_nothing_is_sunk_or_squeezed_past_what_the_town_maps_do(self):
        rates = self.lint["rates"]
        #: was 5.2% sunk; the town maps run 0% to 2.1%
        self.assertLessEqual(rates["sunk"], 0.021)
        self.assertLessEqual(rates["through"], 0.013)
        self.assertLessEqual(rates["squeezed"], 0.056)

    def test_no_sign_is_written_through_a_picture(self):
        #: was 16 pairs; the two pledged coats on one rail are the one left
        self.assertLessEqual(len(self.lint["overlaps"]), 1)
        for pair in self.lint["overlaps"]:
            self.assertFalse(any(3808 <= t <= 3833 for t in pair["tiles"]))

    def test_a_statue_stands_on_a_floor(self):
        from tools.mine_stands import stands

        statues = [r for r in stands([str(CITY)]) if r["tile"] == 536]
        self.assertTrue(statues)
        for row in statues:
            #: on a floor (E3M1, twice), or raised with a body of air over
            #: its head (E1M2): never on a counter or in a shop's shelf
            tall = 17600 / 16960
            self.assertTrue(row["kind"] == "floor"
                            or (row["kind"] == "niche"
                                and row["clear"] >= tall + 0.9), row)

    def test_a_street_lamp_is_a_post_and_a_chain_lamp_has_a_ceiling(self):
        lamps = [s.fields for s in self.disk.sprites
                 if int(s.fields["picnum"]) == 640]
        self.assertGreaterEqual(len(lamps), 10)
        for f in lamps:
            self.assertEqual(int(f["y_repeat"]), 120)
        for sprite in self.disk.sprites:
            f = sprite.fields
            if int(f["picnum"]) == 641:
                sector = self.disk.sectors[int(f["sector"])].fields
                self.assertFalse(int(sector["ceiling_stat"]) & 1,
                                 "a lamp on a chain hangs under the sky")


if __name__ == "__main__":
    unittest.main()
