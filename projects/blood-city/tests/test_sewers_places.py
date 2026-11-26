"""Read the sewers' three remade places from the city's MAP bytes: the Toshers' Den and its bed, the Weaver's pit and shaft, the bleeding floor."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.sector_geom import sector_at, sector_walls
from test_cabal_rite import reach

LEVEL = Path("projects/blood-city/level")
PU = 1024
BODY = PLAYER_PROFILES["blood"]
CROUCHING = 13376


class SewersPlacesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import gameplay
        import l3_sewer
        import stockyard_floor
        import toshers_den
        import wires
        cls.G, cls.S, cls.Y, cls.D, cls.wires = gameplay, l3_sewer, stockyard_floor, toshers_den, wires
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.level = cls.disk.to_level_ir()

    def at(self, x, y, floor):
        sector = sector_at(self.level, round(x * PU), round(y * PU), floor_near=floor)
        self.assertEqual(record_fields(self.disk.sectors[sector])["floor_z"], floor, (x, y))
        return sector

    def sector(self, index):
        return record_fields(self.disk.sectors[index])

    def things(self, sector, type_id):
        return [s for s in self.disk.sprites if record_fields(s)["sector"] == sector and record_fields(s)["type"] == type_id]

    # ---- the lift that was, and the den

    def test_the_service_lift_is_gone_and_its_wire_with_it(self):
        self.assertFalse(any("lift" in name for name, _says in self.wires.PLAN if name.startswith("sewer:")))
        self.assertIsNone(sector_at(self.level, round(18.25 * PU), round(42.0 * PU), floor_near=61440)
                          if self._deep(18.25, 42.0) else None)

    def _deep(self, x, y):
        index = sector_at(self.level, round(x * PU), round(y * PU), floor_near=80000)
        return index is not None and self.sector(index)["floor_z"] > 40000

    def test_the_den_is_walked_into_from_the_quay_and_out_again(self):
        quay, den = self.at(20.5, 46.6, self.D.FLOOR), self.at(15.5, 45.5, self.D.FLOOR)
        self.assertIn(den, reach(self.disk, quay))
        self.assertIn(quay, reach(self.disk, den))

    def test_the_bed_hides_the_crawl_until_it_is_pushed_and_then_a_crouching_body_fits(self):
        x0, y0, x1, y1 = self.D.BEDS[self.D.SECRET]
        bed = self.at((x0 + x1) / 2, (y0 + y1) / 2, self.D.BED)
        f, x = self.sector(bed), record_extra(self.disk.sectors[bed])
        self.assertEqual((f["type"], x["trigger_wall_push"], x["trigger_once"]), (600, 1, 1))
        self.assertEqual((x["off_floor_z"], x["on_floor_z"]), (self.D.BED, self.D.CACHE_FLOOR))
        crawl = self.sector(self.at(11.4, 45.5, self.D.CACHE_FLOOR))
        self.assertGreaterEqual(crawl["ceiling_z"], f["floor_z"])                 # shut at rest
        self.assertGreater(x["on_floor_z"] - crawl["ceiling_z"], CROUCHING)       # and open after
        self.assertLessEqual(x["on_floor_z"] - self.D.FLOOR, BODY.max_step)       # and climbed out of
        cache = self.at(9.7, 45.4, self.D.CACHE_FLOOR)
        extra = record_extra(self.disk.sectors[cache])
        self.assertEqual((extra["tx_id"], extra["command"]), (2, 64))
        self.assertTrue(self.things(cache, 110))                                  # worth it

    def test_its_neighbours_are_lower_so_that_it_is_the_wrong_one(self):
        for name, (x0, y0, x1, y1) in self.D.BEDS.items():
            if name != self.D.SECRET:
                self.at((x0 + x1) / 2, (y0 + y1) / 2, self.D.LOW_BED)

    # ---- the lair

    def test_the_lair_goes_down_in_steps_to_a_pit_under_the_mother(self):
        F = self.S.SEWER_FLOOR
        hall, lip = self.at(9.5, 16.0, F), self.at(10.8, 13.9, F + 4096)
        pit = self.at(12.2, 14.0, F + 8192)
        self.assertIn(pit, reach(self.disk, hall))
        self.assertIn(hall, reach(self.disk, pit))
        self.assertGreater(self.sector(pit)["floor_z"] - self.sector(pit)["ceiling_z"], 3 * BODY.standing_height)
        self.assertEqual(len(self.things(pit, 216)), 1)
        self.assertLess(self.sector(lip)["ceiling_z"], self.sector(hall)["ceiling_z"])

    def test_the_key_lies_in_the_shafts_light_behind_a_web_that_breaks(self):
        _n, x, y, floor, _wakes = self.G.KEYS["spider"]
        stone = self.at(x, y, floor)
        self.assertTrue(any(record_fields(s)["sector"] == stone and 100 <= record_fields(s)["type"] <= 106 for s in self.disk.sprites))
        hall = self.at(9.5, 16.0, self.S.SEWER_FLOOR)
        self.assertLess(self.sector(stone)["floor_shade"] + 16, self.sector(hall)["floor_shade"])
        webs = [record_fields(s) for s in self.disk.sprites if record_fields(s)["type"] == 410]
        self.assertTrue(any(abs(w["y"] - 11 * PU) < 200 and abs(w["x"] - 12 * PU) < 400 for w in webs))

    # ---- the bleeding floor

    def test_the_drain_runs_through_the_bleeding_floor_and_is_blood_after_it(self):
        Y = self.Y
        head, hall = self.at(49.0, 37.0, Y.FLOOR), self.at(52.0, 40.5, Y.FLOOR)
        down = self.at(49.0, 47.0, Y.FLOOR)
        self.assertIn(hall, reach(self.disk, head))
        self.assertIn(down, reach(self.disk, head))
        self.assertIn(head, reach(self.disk, down))
        self.assertIn(self.at(54.6, 43.0, Y.DOCK_Z), reach(self.disk, hall))
        self.assertEqual(self.sector(self.at(49.75, 37.0, Y.WATER))["floor_pal"], 0)
        for x, y, floor in ((52.0, 42.0, Y.GUTTER_Z), (50.1, 44.2, Y.WATER), (49.75, 47.5, Y.WATER), (49.75, 51.4, Y.WATER)):
            self.assertEqual(self.sector(self.at(x, y, floor))["floor_pal"], 7, (x, y))

    def test_it_has_air_and_a_fight(self):
        race = self.sector(self.at(49.5, 40.0, self.Y.WATER))
        self.assertGreater(race["floor_z"] - race["ceiling_z"], 2.5 * BODY.standing_height)
        x0, x1, y0, y1 = (v * PU for v in (self.Y.X0, self.Y.X1, self.Y.Y0, self.Y.Y1))
        foes = [f for f in map(record_fields, self.disk.sprites)
                if 201 <= f["type"] <= 220 and x0 < f["x"] < x1 and y0 < f["y"] < y1 and f["z"] > 30000]
        self.assertGreaterEqual(len(foes), 4)

    def test_taking_the_armor_across_the_blood_wakes_something(self):
        for name, what, _x, comes in self.G.WAKES:
            channel = self.wires.channel(name)
            senders = [s for s in self.disk.sprites if (record_extra(s) or {}).get("tx_id") == channel]
            self.assertEqual([record_fields(s)["type"] for s in senders], [what])
            answers = [s for s in self.disk.sprites if (record_extra(s) or {}).get("rx_id") == channel]
            self.assertEqual(sorted(record_extra(s)["data_1"] for s in answers), sorted(c[0] for c in comes))


if __name__ == "__main__":
    unittest.main()
