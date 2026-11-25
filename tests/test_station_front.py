"""Gravesend Station's front as built: the buildings beside it have sides, and its portico has columns."""

from pathlib import Path
import sys
import unittest

from bloodmap import skyline
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.sector_geom import sector_at, sector_walls

LEVEL = Path("projects/blood-city/level")


class StationFrontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import gameplay
        import l3_station
        cls.T, cls.G = l3_station, gameplay
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.level = cls.disk.to_level_ir()

    def at(self, x, y):
        return sector_at(self.level, x, y, floor_near=8192)

    def test_no_building_in_the_city_is_a_front_with_no_side(self):
        #: the owner, 2026-11-25: "makes buildings next to it to look like paper thin because of the sky"
        self.assertEqual(skyline.thin_fronts(self.disk), [])

    def test_the_forecourt_has_the_streets_sky_and_the_neighbours_own_walls(self):
        T = self.T
        x0, x1 = T.FORECOURT[0][0], T.FORECOURT[-1][1]
        court, street = self.at((x0 + x1) // 2, -1000), self.at((x0 + x1) // 2, 600)
        sky = [record_fields(self.disk.sectors[s])["ceiling_z"] for s in (court, street)]
        self.assertEqual(sky[0], sky[1])
        sides = {x: set() for x in (x0, x1)}
        for wall in self.disk.walls:
            f, p = record_fields(wall), record_fields(self.disk.walls[record_fields(wall)["point2"]])
            if f["next_sector"] < 0 and f["x"] == p["x"] in sides and -2432 <= min(f["y"], p["y"]) and max(f["y"], p["y"]) <= 0:
                sides[f["x"]].add(f["picnum"])
        self.assertEqual(sides, {x0: {T.SIDES["west"]}, x1: {T.SIDES["east"]}})

    def test_four_columns_stand_under_one_roof(self):
        T = self.T
        portico = self.at(sum(T.FRONT_PIER) // 2, -T.FORECOURT_D + 200)
        self.assertFalse(record_fields(self.disk.sectors[portico])["ceiling_stat"] & 1)
        for cx in T.COLUMNS_X:
            ring = self.at(cx, -T.FORECOURT_D + T.PORTICO_D - T.COLUMN_BACK + T.PLINTH_HALF - 20)
            shaft = [w for w in sector_walls(self.disk, ring) if record_fields(self.disk.walls[w])["next_sector"] < 0]
            self.assertEqual(len(shaft), T.SHAFT_SIDES)
            self.assertEqual({record_fields(self.disk.walls[w])["picnum"] for w in shaft}, {T.SHAFT_STONE})

    def test_the_six_locks_hang_on_the_pier_between_the_middle_columns(self):
        T = self.T
        locks = [record_fields(s) for s in self.disk.sprites if (record_extra(s) or {}).get("key") and record_fields(s)["picnum"] == 1048]
        self.assertEqual(len(locks), 6)
        for f in locks:
            self.assertTrue(T.COLUMNS_X[1] < f["x"] < T.COLUMNS_X[2])
            self.assertLess(abs(f["y"] - self.G.PIER_Y), 64)


if __name__ == "__main__":
    unittest.main()
