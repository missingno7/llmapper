"""bloodmap.shade_table: Blood's own palette and shade table, read from BLOOD.RFF."""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import shade_table as T  # noqa: E402

HAVE = (ROOT / "reference" / "blood" / "BLOOD.RFF").exists()


@unittest.skipUnless(HAVE, "the game's BLOOD.RFF is supplied locally")
class ShadeTableTests(unittest.TestCase):
    def test_shade_zero_is_the_identity_and_the_last_row_is_black(self):
        t = T.tables()
        self.assertTrue(all(t["plu"][i] == i for i in range(255)))
        last = [T.luminance(t["palette"][t["plu"][63 * 256 + i]]) for i in range(255)]
        self.assertLess(max(last), 5)

    def test_each_shade_takes_about_a_sixty_fourth(self):
        # measured: the palette's mean falls 100, 88, 75, 63, 50, 38, 25% at
        # shades 0, 8, 16, 24, 32, 40, 48 -- linear, which is why a step of 8
        # is an eighth of a texture's full brightness wherever it is taken
        t = T.tables()
        mean = [sum(T.luminance(t["palette"][t["plu"][s * 256 + i]]) for i in range(256)) / 256
                for s in (0, 32)]
        self.assertAlmostEqual(mean[1] / mean[0], 0.5, delta=0.03)

    def test_below_zero_is_drawn_as_zero(self):
        self.assertEqual(T.clamp_shade(-8), 0)
        self.assertEqual(T.brightness(417, -8), T.brightness(417, 0))


if __name__ == "__main__":
    unittest.main()
