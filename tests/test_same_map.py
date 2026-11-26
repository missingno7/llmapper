"""Two maps are the same level whatever order their records are in, and not when one thing differs."""

from __future__ import annotations

import copy
import unittest

from bloodmap import same_map
from bloodmap.model import record_fields

from tests.test_finish import quiet, two_rooms
from bloodmap import finish


class SameMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.disk = finish.finish(*two_rooms()[:1], circuit=two_rooms()[1], say=quiet).disk

    def test_a_map_is_itself_and_its_rebuild(self):
        again = finish.finish(*two_rooms()[:1], circuit=two_rooms()[1], say=quiet).disk
        self.assertTrue(same_map.same(self.disk, again))

    def test_sprites_in_another_order_are_the_same_level(self):
        other = copy.deepcopy(self.disk)
        other.sprites.reverse()
        self.assertTrue(same_map.same(self.disk, other))

    def test_one_tile_changed_is_not(self):
        other = copy.deepcopy(self.disk)
        record_fields(other.walls[0])["picnum"] += 1
        found = same_map.difference(self.disk, other)
        self.assertEqual(found["walls"], {"only_before": 1, "only_after": 1})
        self.assertEqual(found["sectors"], {"only_before": 0, "only_after": 0})
        self.assertFalse(same_map.same(self.disk, other))


if __name__ == "__main__":
    unittest.main()
