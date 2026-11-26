"""Gravesend measured as a town by the profile that measures Duke's city and E3M1 (`tools.city_profile`)."""

from __future__ import annotations

import unittest
from pathlib import Path

CITY = Path("projects/blood-city/level/blood-city-current.MAP")


class CityProfile(unittest.TestCase):
    def test_the_city_glazes_none_and_has_its_street_ends(self):
        from tools.city_profile import load, profile

        game, disk = load(CITY)
        city = profile(disk, game)
        self.assertEqual(
            city["derived"]["glass"]["on_a_street_record_share"], 0.0)
        self.assertEqual(
            city["derived"]["glass"]["sharing_a_record_with_a_step_band_share"],
            0.0)
        #: three behind the streets that go on (`street_vistas`) and the
        #: sea's twenty-two horizon pieces (a horizon is the same thing with
        #: the sky on its floor as well; `l3_market.SEA_STEP`); the
        #: station's avenue front stands in a forecourt and needs none
        self.assertEqual(city["native"]["sky_backings"], 25)


if __name__ == "__main__":
    unittest.main()
