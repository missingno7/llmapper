"""What breaks in Blood breaks in Gravesend: the built city read back."""

from pathlib import Path
import unittest

from bloodmap import breakables
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

CITY = Path("projects/blood-city/level/blood-city-current.MAP")


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
