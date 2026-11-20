"""The city's names for its goods agree with what each tile is (the owner's word first).

goods.NAMES stocked a grocer's window with tile 2937 as "roast"; the owner's
name for 2937 is "dead cultist". Nothing compared the two. Each name here
must share a word with the owner's name for the tile, or, where the owner
has not named it, with the library's reading.
"""

import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "projects" / "blood-city" / "level"))

STOP = {"the", "and", "with", "bill", "sign", "a", "of", "in", "on"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 3 and w not in STOP}


class GoodsNamesTest(unittest.TestCase):
    def test_every_name_agrees_with_the_tile(self):
        import goods
        from tools import catalog

        wrong = []
        for tile, name in sorted(goods.NAMES.items()):
            source, truth = catalog.tile_name(tile)
            if not truth:
                continue
            if not (_words(name) & _words(truth)) and not any(
                    w in truth.lower() for w in _words(name)):
                wrong.append(f"{tile}: goods says {name!r}, {source} says {truth!r}")
        self.assertEqual(wrong, [])

    def test_tile_is_follows_the_owner(self):
        from tools import catalog
        self.assertFalse(catalog.tile_is(2937, "roast", "meat"))
        self.assertTrue(catalog.tile_is(2026, "shelf"))
        self.assertFalse(catalog.tile_is(202, "shelf"))


if __name__ == "__main__":
    unittest.main()
