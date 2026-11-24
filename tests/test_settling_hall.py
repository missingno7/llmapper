"""Read the settling hall from the city's MAP bytes: the outfall's line runs on, down the falls and the stair, to the Cabal's quay."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.sector_geom import sector_at, sector_walls
from tests.test_cabal_rite import reach

LEVEL = Path("projects/blood-city/level")
PU = 1024


class SettlingHallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import settling_hall
        cls.H = settling_hall
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.level = cls.disk.to_level_ir()

    def at(self, x, y, floor):
        sector = sector_at(self.level, round(x * PU), round(y * PU), floor_near=floor)
        self.assertEqual(record_fields(self.disk.sectors[sector])["floor_z"], floor, (x, y))
        return sector

    def test_the_way_down_is_walked_from_the_outfall_and_back(self):
        outfall = self.at(33.75, 38.0, 61440)
        quay = self.at(33.0, 49.0, self.H.WALK)
        self.assertIn(quay, reach(self.disk, outfall))
        self.assertIn(outfall, reach(self.disk, quay))
        self.assertIn(self.at(27.5, 44.6, self.H.WALK), reach(self.disk, quay))

    def test_the_water_comes_down_in_one_line_and_every_drop_of_it_runs(self):
        here = self.at(33.0, 42.75, self.H.CHANNEL)
        for k in range(1, 6):
            there = self.at(33.0, 42.5 + k, self.H.CHANNEL + self.H.FALL * k)
            faces = [w for w in sector_walls(self.disk, there)
                     if record_fields(self.disk.walls[w])["next_sector"] == here
                     and record_fields(self.disk.walls[w])["picnum"] == self.H.SEWAGE]
            self.assertTrue(faces, k)
            for w in faces:
                self.assertTrue(record_extra(self.disk.walls[w])["pan_always"])
            self.assertEqual(record_fields(self.disk.sectors[there])["floor_picnum"], self.H.SEWAGE)
            here = there

    def test_every_tank_lies_in_a_vault_of_the_corridors_rise(self):
        for y0, y1 in self.H.TANKS:
            for y in (y0 + 0.2, y1 - 0.2):
                f = record_fields(self.disk.sectors[self.at(26.4, y, self.H.WATER)])
                self.assertTrue(f["ceiling_stat"] & 2)
                self.assertNotEqual(f["ceiling_heinum"], 0)
        self.assertEqual(self.H.SPRING - self.H.CROWN, 8192)


if __name__ == "__main__":
    unittest.main()
