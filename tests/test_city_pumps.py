"""The pump station's filter and its two pumps, read back from the built map."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

LEVEL = Path("projects/blood-city/level")


class Pumps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.sectors = [(record_fields(s), record_extra(s) or {}) for s in cls.disk.sectors]

    def test_the_filter_hangs_over_the_basin_and_leaves_it_to_be_dived_into(self):
        import pump_engine as P
        tank = [f for f, _x in self.sectors if f["ceiling_picnum"] == P.MESH and f["floor_picnum"] == 1120]
        self.assertEqual(len(tank), 1)
        self.assertEqual(tank[0]["ceiling_z"], P.GRADE - P.UNDER)
        self.assertGreater(tank[0]["floor_z"] - tank[0]["ceiling_z"], 16960)
        faces = [record_fields(w) for w in self.disk.walls if record_fields(w)["picnum"] == P.DRUM and record_fields(w)["next_sector"] >= 0]
        self.assertGreaterEqual(len(faces), 10)

    def test_two_rods_go_up_and_down_for_ever_and_nothing_is_under_them(self):
        import pump_engine as P
        rods = [(f, x) for f, x in self.sectors if f["type"] == 600 and x["rx_id"] == 7 and x["off_floor_z"] == P.GRADE - P.LOW]
        self.assertEqual(len(rods), len(P.PUMPS))
        for f, x in rods:
            self.assertEqual((x["on_floor_z"], x["retrigger_a"], x["retrigger_b"], x["tx_id"]), (P.GRADE - P.HIGH, 1, 1, 0))
            self.assertEqual(x["off_ceiling_z"], x["on_ceiling_z"])                # its floor alone moves: there is no press in it
        self.assertEqual(len({x["busy_time_a"] for _f, x in rods}), len(rods))

    def test_no_wall_trap_is_a_lamp(self):
        for s in self.disk.sprites:
            f = record_fields(s)
            self.assertFalse(f["picnum"] == 2183 and f["type"] != 452 and not f["cstat"] & 32768, f)


if __name__ == "__main__":
    unittest.main()
