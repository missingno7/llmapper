"""Read the Gallows Steps from the city's MAP bytes: the alley climbs to a terrace over the streets, and nothing lies over anything."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_fields
from bloodmap.sector_geom import sector_at, sector_walls
from tests.test_cabal_rite import BODY, reach

LEVEL = Path("projects/blood-city/level")
PU = 1024


class GallowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import gallows
        cls.G = gallows
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.level = cls.disk.to_level_ir()

    def at(self, x, y, floor):
        sector = sector_at(self.level, round(x * PU), round(y * PU), floor_near=floor)
        self.assertEqual(record_fields(self.disk.sectors[sector])["floor_z"], floor, (x, y))
        return sector

    def test_the_alley_is_walked_up_to_the_terrace_and_the_house(self):
        alley = self.at(9.0, 22.0, self.G.GRADE)
        seen = reach(self.disk, alley)
        self.assertIn(self.at(11.0, 31.0, self.G.TOP), seen)
        self.assertIn(self.at(5.5, 32.0, self.G.TOP), seen)
        self.assertIn(alley, reach(self.disk, self.at(11.0, 31.0, self.G.TOP)))

    def test_it_stands_over_the_streets_and_opens_on_them(self):
        self.assertGreater(self.G.GRADE - self.G.TOP, 2 * BODY.standing_height)
        over = set()
        for x, y in ((14.9, 32.0), (12.0, 34.9), (12.9, 27.0)):
            parapet = self.at(x, y, self.G.TOP - self.G.PARAPET)
            for w in sector_walls(self.disk, parapet):
                n = record_fields(self.disk.walls[w])["next_sector"]
                if n >= 0 and record_fields(self.disk.sectors[n])["floor_z"] >= self.G.GRADE:
                    over.add((x, y))
        self.assertEqual(len(over), 3)

    def test_there_is_no_floor_under_the_terrace(self):
        """Where the terrace is, the ground is the terrace: nothing of the street's layer lies below it."""
        for x, y in ((11.0, 31.0), (14.0, 33.0), (11.8, 27.0), (9.0, 34.4)):
            sector = sector_at(self.level, round(x * PU), round(y * PU), floor_near=self.G.GRADE)
            f = record_fields(self.disk.sectors[sector])
            self.assertTrue(f["floor_z"] < 0 or f["ceiling_z"] > 16384, (x, y, f["floor_z"]))


if __name__ == "__main__":
    unittest.main()
