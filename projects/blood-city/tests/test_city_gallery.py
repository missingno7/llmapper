"""The Gravesend Gallery, the memorial's obelisk and the church's name, read back from the built map."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

LEVEL = Path("projects/blood-city/level")


class Gallery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.sectors = [record_fields(s) for s in cls.disk.sectors]
        cls.sprites = [(record_fields(s), record_extra(s) or {}) for s in cls.disk.sprites]
        cls.inside = [(f, x) for f, x in cls.sprites if 11 * 1024 <= f["x"] <= 16 * 1024 and 6 * 1024 <= f["y"] <= 13 * 1024
                      and -30000 < f["z"] < 10000 and not f["cstat"] & 32768]

    def test_the_pictures_hang_and_nothing_is_lettered_shooting(self):
        import gallery
        hung = [f for f, _x in self.inside if f["cstat"] & 48 == 16]
        self.assertGreaterEqual(len(hung), len(gallery.HUNG) + len(gallery.ON_PIERS))
        self.assertTrue(all(f["cstat"] & 64 for f in hung))
        self.assertFalse([f for f in hung if 3808 <= f["picnum"] <= 3833])
        self.assertEqual({f["picnum"] for f in hung} & {716, 717, 718, 719}, {716, 717, 718, 719})

    def test_each_lit_picture_has_a_lamp_and_a_brighter_half_round(self):
        import gallery
        lamps = [f for f, _x in self.inside if f["picnum"] == gallery.LAMP and f["cstat"] & 48 == 32]
        lit = sum(row[-1] for row in gallery.HUNG)
        self.assertEqual(len(lamps), lit + len(gallery.LAMPS))
        pools = {f["sector"] for f in lamps if f["x_repeat"] == 36}
        self.assertEqual(len(pools), lit)
        room = max(self.sectors[f["sector"]]["floor_shade"] for f in lamps if f["x_repeat"] == 24)
        for sector in pools:
            self.assertLess(self.sectors[sector]["floor_shade"] + 6, room)

    def test_the_beast_gets_down_when_what_lies_before_it_is_taken(self):
        beast = [(f, x) for f, x in self.inside if f["type"] == 208]
        self.assertEqual(len(beast), 1)
        prize = [x for f, x in self.inside if f["type"] == 141]
        self.assertEqual(len(prize), 1)
        self.assertTrue(prize[0]["trigger_pickup"] and prize[0]["tx_id"] and prize[0]["tx_id"] == beast[0][1]["rx_id"])

    def test_the_memorial_has_an_obelisk_with_the_flame_on_its_point(self):
        import l3_market as M
        flame = [f for f, _x in self.sprites if f["picnum"] == 2101 and abs(f["x"] - 26.5 * 1024) < 600 and 41 * 1024 < f["y"] < 44 * 1024]
        self.assertEqual(len(flame), 1)
        under = self.sectors[flame[0]["sector"]]
        self.assertEqual(under["floor_z"], 8192 - M.PARAPET_RISE - M.BACKDROP_RISE - sum(row[3] for row in M.OBELISK))

    def test_the_church_says_its_name_on_the_avenue(self):
        import l3_church as C
        letters = [f for f, _x in self.sprites if 3808 <= f["picnum"] <= 3833 and abs(f["x"] - C.MASS[2] - 10) < 4
                   and abs(f["y"] - C.NAME_AT[0]) < 1200 and f["z"] == 8192 - C.NAME_AT[1]]
        self.assertEqual("".join(chr(65 + f["picnum"] - 3808) for f in sorted(letters, key=lambda f: -f["y"])), C.NAME.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
