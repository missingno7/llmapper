"""What breaks in Blood breaks in the city, and the mined table says how."""

from types import SimpleNamespace
import unittest

from bloodmap import breakables


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


if __name__ == "__main__":
    unittest.main()
