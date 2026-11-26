"""The sewer's secrets as built: bars and a wheel, the bloody hands and the pipe they open, ivy over a crawl."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.motion import marker_pair
from bloodmap.sector_geom import outline_and_holes, sector_walls

LEVEL = Path("projects/blood-city/level")
STANDING = 16960


class SecretPlacesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import secret_places
        import wires
        cls.S, cls.wires = secret_places, wires
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.sprites = [(record_fields(s), record_extra(s) or {}) for s in cls.disk.sprites]
        cls.sectors = [(record_fields(s), record_extra(s) or {}) for s in cls.disk.sectors]

    def hears(self, name):
        channel = self.wires.channel(name)
        return [(i, f, x) for i, (f, x) in enumerate(self.sectors) if x.get("rx_id") == channel]

    def sends(self, name):
        channel = self.wires.channel(name)
        return [(f, x) for f, x in self.sprites if x.get("tx_id") == channel]

    def test_the_stash_is_behind_bars_that_a_wheel_lifts(self):
        (strip, fields, extra), = self.hears("sewer:stash-bars")
        self.assertEqual(fields["type"], 602)
        self.assertGreater(extra["off_floor_z"] - extra["on_floor_z"], STANDING)
        bars, = (f for f, _x in self.sprites if f["sector"] == strip and f["picnum"] == self.S.GRILLE)
        self.assertEqual(bars["cstat"] & (8192 | 256 | 16 | 1), 8192 | 256 | 16 | 1)
        points, _holes = outline_and_holes(self.disk, strip)
        ys = [p[1] for p in points]
        self.assertGreaterEqual(bars["x_repeat"] * 128 // 4, max(ys) - min(ys) - 64)       # no way round them
        (wheel, push), = self.sends("sewer:stash-bars")
        self.assertEqual((wheel["picnum"], wheel["type"], push["trigger_push"], push["command"]), (982, 20, 1, 1))
        self.assertTrue(push["trigger_on"] and push["trigger_off"])
        self.assertEqual([f["index"] for f, _x in self.sprites if f["picnum"] in (982, 983)], [wheel["index"]])   # the only one

    def test_the_hands_press_their_slab_and_open_the_pipe(self):
        heard = {f["type"]: (i, x) for i, f, x in self.hears("sewer:shrine-hands")}
        self.assertEqual(set(heard), {600, 614})
        button, behaviour = heard[614]
        self.assertEqual(marker_pair(self.disk, button)["travel"], (self.S.GIVES, 0))
        self.assertTrue(behaviour["retrigger_a"] and behaviour["wait_time_a"])
        hands = self.sends("sewer:shrine-hands")
        self.assertEqual([f["picnum"] for f, _x in hands], [self.S.HAND] * 2)
        for f, x in hands:
            self.assertTrue(f["cstat"] & 8192 and f["cstat"] & 256 and x["trigger_push"])
            self.assertEqual(f["sector"], button)
        plug, extra = heard[600]
        self.assertEqual(extra["off_ceiling_z"], extra["off_floor_z"])
        self.assertGreater(extra["on_floor_z"] - extra["on_ceiling_z"], STANDING)
        # shut, it wears what the wall beside it wears
        for w in sector_walls(self.disk, plug):
            other = record_fields(self.disk.walls[w])["next_wall"]
            if other < 0:
                continue
            face = record_fields(self.disk.walls[other])
            host = next(i for i, (f, _x) in enumerate(self.sectors) if f["wall_ptr"] <= other < f["wall_ptr"] + f["wall_count"])
            if self.sectors[host][0]["floor_picnum"] == 291:
                solid = {record_fields(self.disk.walls[v])["picnum"] for v in sector_walls(self.disk, host)
                         if record_fields(self.disk.walls[v])["next_sector"] < 0}
                self.assertIn(face["picnum"], solid)

    def test_the_ivy_stops_nobody(self):
        ivy, = (f for f, _x in self.sprites if f["picnum"] == self.S.IVY)
        self.assertFalse(ivy["cstat"] & (1 | 256 | 64))


if __name__ == "__main__":
    unittest.main()
