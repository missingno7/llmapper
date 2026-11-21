"""bloodmap.visual.sprite_shades_as_drawn: sprites lit by their sector, as Blood's viewProcessSprites does."""

import pathlib
import sys
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap.visual import sprite_shades_as_drawn  # noqa: E402


def _rec(**f):
    return SimpleNamespace(fields=dict(f))


class SpriteShadeTests(unittest.TestCase):
    def test_under_the_sky_a_sprite_takes_the_ceiling_and_indoors_the_floor(self):
        disk = SimpleNamespace(
            sectors=[_rec(ceiling_stat=1, floor_stat=0, ceiling_shade=12, floor_shade=30),
                     _rec(ceiling_stat=0, floor_stat=0, ceiling_shade=40, floor_shade=20),
                     _rec(ceiling_stat=1, floor_stat=0x8000, ceiling_shade=12, floor_shade=30)],
            sprites=[_rec(sector=0, shade=-4), _rec(sector=1, shade=0), _rec(sector=2, shade=2)])
        self.assertEqual(sprite_shades_as_drawn(disk), 3)
        self.assertEqual([s.fields["shade"] for s in disk.sprites], [8, 20, 32])


if __name__ == "__main__":
    unittest.main()
