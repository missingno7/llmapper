"""The sewer's oldest rooms are refitted, not boxes, and everything that was joined to them still is."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

LEVEL = Path("projects/blood-city/level")
MAP = LEVEL / "blood-city-current.MAP"


class SewerRooms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MAP.exists():
            raise unittest.SkipTest("the city is not built here")
        sys.path.insert(0, str(LEVEL))
        cls.disk = read_map(MAP)
        cls.sectors = [record_fields(s) for s in cls.disk.sectors]
        cls.walls = [record_fields(w) for w in cls.disk.walls]

    def inside(self, x0, y0, x1, y1):
        out = []
        for i, s in enumerate(self.sectors):
            pts = [(self.walls[w]["x"] / 1024, self.walls[w]["y"] / 1024) for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"])]
            if 30000 < s["floor_z"] < 70000 and all(x0 - 0.01 <= x <= x1 + 0.01 and y0 - 0.01 <= y <= y1 + 0.01 for x, y in pts):
                out.append(i)
        return out

    def test_no_room_is_a_box_any_more(self):
        for name, rect in (("trunk", (39.25, 20.5, 50.0, 22.5)), ("junction", (39.25, 9.0, 44.25, 15.0)),
                           ("cistern", (43.0, 27.0, 49.0, 31.0)), ("pumps", (27.0, 12.0, 32.0, 18.0)),
                           ("annex", (53.0, 14.0, 57.0, 20.0)), ("silt", (45.5, 2.0, 50.0, 6.0)),
                           ("riser", (39.25, 15.0, 40.75, 20.5)), ("fall", (45.25, 22.5, 46.75, 27.0)),
                           ("adit", (34.0, 11.0, 39.25, 13.0))):
            here = self.inside(*rect)
            self.assertGreaterEqual(len(here), 3, name)
            self.assertTrue(any(self.sectors[i]["ceiling_stat"] & 2 or self.sectors[i]["floor_stat"] & 2
                                or len({(self.sectors[j]["ceiling_z"], self.sectors[j]["floor_z"]) for j in here}) > 2 for i in here), name)

    def test_one_pump_still_goes(self):
        rods = [i for i in self.inside(27.0, 12.0, 32.0, 18.0) if self.sectors[i]["type"] == 600]
        self.assertEqual(len(rods), 1)
        extra = record_extra(self.disk.sectors[rods[0]])
        self.assertEqual(extra["rx_id"], 7)                      # kChannelLevelStart: `wires`, "pump:engine"
        self.assertNotEqual(extra["off_floor_z"], extra["on_floor_z"])

    def test_the_trunk_runs_east_in_its_channel(self):
        water = [i for i in self.inside(39.25, 20.5, 50.0, 22.5) if self.sectors[i]["floor_picnum"] == 1120]
        self.assertGreaterEqual(len(water), 4)
        for i in water:
            extra = record_extra(self.disk.sectors[i])
            self.assertTrue(extra.get("pan_floor") and extra.get("pan_angle") == 0, i)


if __name__ == "__main__":
    unittest.main()
