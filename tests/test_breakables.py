"""What breaks in Blood breaks in the city, and the mined table says how."""

from pathlib import Path
from types import SimpleNamespace
import unittest

from bloodmap import breakables
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

CITY = Path("projects/blood-city/level/blood-city-current.MAP")


def _placed(tile, **more):
    return SimpleNamespace(**{"picnum": tile, "type": 0, "behavior": {}, "cstat": 129, "status": 0, **more})


class BreakablesTests(unittest.TestCase):
    def test_a_tile_breaks_by_the_campaigns_commonest_record(self):
        self.assertEqual(breakables.breaks(925), {"type": 417, "hitscan": True, "data_1": 15, "data_4": 312})
        self.assertIsNone(breakables.breaks(641))         # two lamps on a chain in 452

    def test_only_a_plain_placement_is_made_to_break(self):
        barrel, owned, lamp, step = _placed(925), _placed(925, type=400), _placed(796), _placed(178, cstat=33)
        self.assertEqual(breakables.apply([barrel, owned, lamp, step], leave={796}), {925: 1})
        self.assertEqual((barrel.type, barrel.status, barrel.cstat), (417, 4, 129 | 256))
        self.assertEqual((owned.type, lamp.type, step.type), (400, 0, 0))


class CityBreakablesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not CITY.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(CITY)
        cls.sprites = [(record_fields(s), record_extra(s) or {}) for s in cls.disk.sprites]

    def test_every_barrel_and_cocoon_breaks(self):
        # (117 is a stall's post and holds its roof up: the owner, 2026-11-25, "I wouldn't make them breakable")
        for tile in (925, 1061):
            self.assertEqual({f["type"] in breakables.KINDS for f, _x in self.sprites if f["picnum"] == tile}, {True}, tile)

    def test_every_clock_smashes_and_throws_its_glass(self):
        clocks = [(f, x) for f, x in self.sprites if f["picnum"] in breakables.FACES]
        self.assertGreaterEqual(len(clocks), 8)
        for f, x in clocks:
            self.assertEqual((f["type"], x["trigger_vector"], x["trigger_once"]), (21, 1, 1))
            glass, = ((g, y) for g, y in self.sprites if y.get("rx_id") == x["tx_id"])
            self.assertEqual((glass[0]["type"], glass[0]["cstat"] & 32768), (416, 32768))

    def test_nothing_of_the_engines_is_drawn(self):
        #: the owner, 2026-11-25, of sprite 1303, the secret counter: "probably shouldn't
        #: be visible because it is just a solid wall texture as a sprite"
        self.assertEqual([f["index"] for f, _x in self.sprites
                          if f["picnum"] == 0 and not f["cstat"] & 32768 and not 1 <= f["type"] <= 18], [])


if __name__ == "__main__":
    unittest.main()
