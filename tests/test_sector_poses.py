"""A reference sector is looked at from where it can be seen: a room from inside, a step or a door from beside it."""

from __future__ import annotations

import unittest

from bloodmap.viewplan import SMALL_SECTOR, sector_poses


def _e3m1():
    from bloodmap.corpus import corpus_map_path
    from bloodmap.format import read_map

    path = corpus_map_path("E3M1")
    if not path.exists():
        raise unittest.SkipTest("the corpus is not here")
    return read_map(path).to_level_ir()


class SectorPoses(unittest.TestCase):
    def test_a_room_is_seen_from_inside_and_a_step_from_its_widest_neighbour(self):
        level = _e3m1()
        room, step = sector_poses(level, [12, 79])
        self.assertEqual((room.sector, room.view_id), (12, "sector_12"))
        #: s79 is a tread of E3M1's long flight, narrower than SMALL_SECTOR: from inside it the view is a wall
        self.assertNotEqual(step.sector, 79)
        self.assertEqual(step.view_id, "sector_79")
        self.assertIn("seen from sector", step.note)

    def test_what_is_not_there_is_named(self):
        refused = []
        self.assertEqual(sector_poses(_e3m1(), [999999], refused=refused), [])
        self.assertTrue(refused and "not in the map" in refused[0])
        self.assertGreater(SMALL_SECTOR, 384)


if __name__ == "__main__":
    unittest.main()
