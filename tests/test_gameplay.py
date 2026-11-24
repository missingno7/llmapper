"""Read the city's play from its MAP bytes: six keys in any order, the station they open, what they wake, the guns."""

from collections import Counter
from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

LEVEL = Path("projects/blood-city/level")


class GameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import gameplay
        import wires
        cls.G, cls.wires = gameplay, wires
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.sprites = [(i, record_fields(s), record_extra(s) or {}) for i, s in enumerate(cls.disk.sprites)]

    def on(self, name):
        channel = self.wires.channel(name)
        return [(i, f, x) for i, f, x in self.sprites if x.get("rx_id") == channel]

    def test_every_key_is_in_the_level_once(self):
        kinds = Counter(f["type"] for _i, f, _x in self.sprites if 100 <= f["type"] <= 105)
        self.assertEqual(kinds, {100 + k: 1 for k in range(6)})

    def test_six_keyed_switches_into_one_count_raise_every_gate(self):
        """DWE1M9 1399-1407: each switch wants its key and turns once; the counter sends at the sixth."""
        channel = self.wires.channel("station:keys")
        turned = [x for _i, f, x in self.sprites if x.get("tx_id") == channel]
        self.assertEqual(sorted(x["key"] for x in turned), [1, 2, 3, 4, 5, 6])
        for x in turned:
            self.assertTrue(x["trigger_push"] and x["trigger_once"])
        (_i, tally, x), = self.on("station:keys")
        self.assertEqual((tally["type"], x["data_2"], x["tx_id"]), (22, 6, self.wires.channel("station:unlock")))
        gates = [s for s in self.disk.sectors if (record_extra(s) or {}).get("rx_id") == self.wires.channel("station:unlock")]
        self.assertGreaterEqual(len(gates), 3)
        for s in gates:
            f, x = record_fields(s), record_extra(s)
            self.assertEqual(f["ceiling_z"], f["floor_z"])                     # shut
            self.assertLess(x["on_ceiling_z"], f["floor_z"] - 16960)           # a body clears it when it is up

    def test_the_station_cannot_be_entered_before_and_can_after(self):
        from bloodmap.sector_geom import sector_at
        from tests.test_cabal_rite import reach
        level = self.disk.to_level_ir()
        start = int(self.disk.header["start_sector"])
        hall = sector_at(level, 35 * 1024, -6 * 1024 + 300, floor_near=8192)
        before = reach(self.disk, start)
        self.assertNotIn(hall, before)
        for s in self.disk.sectors:
            x = record_extra(s)
            if x and x["rx_id"] == self.wires.channel("station:unlock"):
                record_fields(s)["ceiling_z"] = x["on_ceiling_z"]
        try:
            self.assertIn(hall, reach(self.disk, start))
        finally:
            for s in self.disk.sectors:
                x = record_extra(s)
                if x and x["rx_id"] == self.wires.channel("station:unlock"):
                    record_fields(s)["ceiling_z"] = x["off_ceiling_z"]

    def test_what_each_key_wakes(self):
        for name, row in self.G.KEYS.items():
            if not row[4]:
                continue
            (x,) = [x for _i, f, x in self.sprites if 100 <= f["type"] <= 105 and x.get("tx_id") == self.wires.channel(f"key:{name}")]
            self.assertTrue(x["trigger_pickup"] and x["trigger_once"])
            woken = [x["data_1"] for _i, f, x in self.on(f"key:{name}") if f["type"] == 18]
            self.assertEqual(sorted(woken), sorted(w for w, _x, _y in row[4]))

    def test_the_dagger_lies_behind_the_rose(self):
        import cabal_rite as R
        key = next(f for _i, f, _x in self.sprites if f["type"] == 103)
        self.assertGreater(key["y"], R.GULLET)
        self.assertLess(key["y"], R.HEART[1] - R.COLUMN)

    def test_one_of_each_big_gun_and_the_best_of_them_hidden(self):
        kinds = Counter(f["type"] for _i, f, _x in self.sprites)
        for gun in (41, 42, 43, 45, 46, 50, 70):
            self.assertEqual(kinds[gun], 1, gun)
        # the sawed-off is in reach of the first frame
        start = self.disk.header
        gun = next(f for _i, f, _x in self.sprites if f["type"] == 41)
        self.assertLess(abs(gun["x"] - start["start_x"]) + abs(gun["y"] - start["start_y"]), 8000)

    def test_every_supply_row_is_in_the_map(self):
        want = Counter(t for types, *_rest in self.G.SUPPLIES for t in types)
        have = Counter(f["type"] for _i, f, _x in self.sprites)
        for kind, n in want.items():
            self.assertGreaterEqual(have[kind], n, kind)

    def test_a_foe_in_six_carries_something(self):
        fighters = [x for _i, f, x in self.sprites if f["type"] in (201, 202, 203, 248)]
        carrying = sum(1 for x in fighters if x.get("drop_item"))
        self.assertAlmostEqual(carrying / len(fighters), 1 / 6, delta=0.06)


if __name__ == "__main__":
    unittest.main()
