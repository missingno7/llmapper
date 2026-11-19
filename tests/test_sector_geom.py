"""`sector_geom` and the record accessors: one reading of a sector's walls.

Thirteen copies of `wall_owners` and six loop tracers were replaced by these
on 2026-11-19, after a run over the 102 named corpus maps (46,017 sectors,
374,495 walls) found every copy in agreement. These tests hold the behaviour
the copies shared, on maps small enough to check by eye.
"""

from __future__ import annotations

import unittest

from bloodmap.model import record_extra, record_fields
from bloodmap.sector_geom import (
    sector_loops, sector_walls, wall_length, wall_owners, wall_segment,
)
from tests.helpers import (
    synthetic_map, synthetic_multi_loop_map, synthetic_two_sector_map,
)


class RecordAccessTests(unittest.TestCase):
    def test_fields_come_back_the_same_from_either_shape(self):
        disk = synthetic_two_sector_map()
        level = disk.to_level_ir()
        self.assertEqual(dict(record_fields(disk.sectors[1])),
                         dict(record_fields(level.sectors[1])))
        self.assertEqual(record_fields(disk.walls[0])["x"],
                         record_fields(level.walls[0])["x"])

    def test_the_blood_extension_is_found_on_both_shapes(self):
        """`getattr(sector, "extra", None)` is None for every `LevelIR` record:
        that is the reader this replaces, and the bug it had."""
        disk = synthetic_two_sector_map()
        level = disk.to_level_ir()
        on_disk = record_extra(disk.sprites[0])
        in_level = record_extra(level.sprites[0])
        self.assertEqual(on_disk["tx_id"], 100)
        self.assertEqual(in_level["tx_id"], 100)
        self.assertIsNone(getattr(level.sprites[0], "extra", None))

    def test_a_record_without_an_extension_says_none(self):
        disk = synthetic_two_sector_map()
        self.assertIsNone(record_extra(disk.sectors[1]))
        self.assertIsNone(record_extra(disk.to_level_ir().sectors[1]))
        self.assertIsNone(record_extra({"fields": {}}))


class SectorWallTests(unittest.TestCase):
    def test_every_wall_belongs_to_the_sector_whose_run_holds_it(self):
        disk = synthetic_two_sector_map()
        expected = {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 1, 7: 1}
        self.assertEqual(wall_owners(disk), expected)
        self.assertEqual(wall_owners(disk.to_level_ir()), expected)

    def test_a_hole_is_its_own_loop_and_not_part_of_the_outline(self):
        disk = synthetic_multi_loop_map()
        loops = sector_loops(disk, 0)
        self.assertEqual(loops, [
            [(0, 0), (4096, 0), (4096, 4096), (0, 4096)],
            [(1024, 1024), (1024, 3072), (3072, 3072), (3072, 1024)],
        ])
        self.assertEqual(sector_loops(disk.to_level_ir(), 0), loops)

    def test_a_run_that_overshoots_the_wall_list_is_clamped_not_followed(self):
        disk = synthetic_map()
        disk.sectors[0].fields["wall_count"] = 99
        self.assertEqual(list(sector_walls(disk, 0)), [0, 1, 2, 3])
        self.assertEqual(len(sector_loops(disk, 0)), 1)
        self.assertEqual(set(wall_owners(disk)), {0, 1, 2, 3})

    def test_a_loop_of_two_points_is_not_a_loop(self):
        disk = synthetic_map()
        disk.sectors[0].fields["wall_count"] = 2
        disk.walls[1].fields["point2"] = 0
        self.assertEqual(sector_loops(disk, 0), [])

    def test_a_wall_runs_from_its_own_point_to_the_next_walls(self):
        disk = synthetic_map()
        self.assertEqual(wall_segment(disk, 0), ((0, 0), (1024, 0)))
        self.assertEqual(wall_segment(disk, 3), ((0, 1024), (0, 0)))
        self.assertEqual(wall_length(disk, 0), 1024.0)
        self.assertEqual(wall_segment(disk.to_level_ir(), 3), ((0, 1024), (0, 0)))


if __name__ == "__main__":
    unittest.main()
