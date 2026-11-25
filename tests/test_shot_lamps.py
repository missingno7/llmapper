"""Lamps that are shot out take their light with them; and the station's rail meets its newels in the middle."""

import json
import math
from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

LEVEL = Path("projects/blood-city/level")


class ShotLamps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.manifest = json.loads((LEVEL.parent / "reports" / "build-manifest.json").read_text("utf-8"))
        cls.channels = cls.manifest["shot_lamps"]

    def test_each_is_hit_by_a_bullet_and_puts_out_what_it_lights(self):
        self.assertGreaterEqual(len(self.channels), 15)
        for name, channel in self.channels.items():
            senders = [(record_fields(s), record_extra(s)) for s in self.disk.sprites if (record_extra(s) or {}).get("tx_id") == channel]
            self.assertTrue(senders, name)
            for f, x in senders:
                self.assertTrue(f["cstat"] & 256, name)                          # a bullet stops at it
                self.assertIn(f["type"], (21, 416), name)
                self.assertEqual((x["command"], x["trigger_once"]), (1, 1), name)
            lit = [(record_fields(s), record_extra(s)) for s in self.disk.sectors if (record_extra(s) or {}).get("rx_id") == channel]
            self.assertTrue(lit, f"{name} lights nothing")
            for f, x in lit:
                self.assertEqual((x["state"], x["tx_id"]), (0, 0), name)         # lit until the ON, and it sends nothing on
                self.assertGreater(x["amplitude"], 0, name)                      # (a light is a shade less: ON makes it more)
                self.assertLess(f["floor_shade"], 60, name)

    def test_a_row_of_panels_is_one_circuit(self):
        import shot_lamps
        for name, panels in shot_lamps.CIRCUITS.items():
            channel = self.channels[name]
            rows = [(record_fields(s), record_extra(s)) for s in self.disk.sprites
                    if record_fields(s)["picnum"] == shot_lamps.PANEL and (record_extra(s) or {}).get("rx_id") == channel]
            self.assertEqual(len(rows), len(panels), name)
            self.assertEqual({x["tx_id"] for _f, x in rows}, {channel})

    def test_there_are_channels_to_spare(self):
        used = {v for part in (self.disk.sectors, self.disk.walls, self.disk.sprites) for o in part
                for k, v in (record_extra(o) or {}).items() if k in ("tx_id", "rx_id") and v >= 100}
        self.assertLess(len(used), 145)                                          # the most a campaign map has
        self.assertLess(max(used), 1024)

    def test_the_rail_meets_the_middle_of_its_newels(self):
        import booking_hall as B
        rails = [record_fields(s) for s in self.disk.sprites if record_fields(s)["picnum"] == B.RAIL
                 and abs(record_fields(s)["y"] - B._q(B.EDGE)) < 64]
        self.assertEqual(len(rails), 4)
        ends = sorted(x for f in rails for x in (f["x"] - f["x_repeat"] * 16, f["x"] + f["x_repeat"] * 16))
        middles = [B._q(B.STAIR[0] - B.NEWEL), B._q(B.STAIR[1] + B.NEWEL)]
        self.assertTrue(abs(ends[3] - middles[0]) <= 4 and abs(ends[4] - middles[1]) <= 4, (ends, middles))
        self.assertTrue(abs(ends[0] - B._q(B.WEST)) <= 4 and abs(ends[-1] - B._q(B.EAST)) <= 4)
        newels = [s for s in self.disk.sectors if record_fields(s)["floor_z"] == B.TOP - B.NEWEL_RISE and record_fields(s)["floor_picnum"] == B.WOOD]
        self.assertEqual(len(newels), 2)
        for s in newels:
            f = record_fields(s)
            ys = [record_fields(self.disk.walls[w])["y"] for w in range(f["wall_ptr"], f["wall_ptr"] + f["wall_count"])]
            self.assertTrue(all(abs((min(ys) + max(ys)) / 2 - r["y"]) <= 2 for r in rails))     # astride the rail's own line


if __name__ == "__main__":
    unittest.main()
