"""`sector_geom` and the record accessors: one reading of a sector's walls.

Thirteen copies of `wall_owners` and six loop tracers were replaced by these
on 2026-11-19, after a run over the 102 named corpus maps (46,017 sectors,
374,495 walls) found every copy in agreement. These tests hold the behaviour
the copies shared, on maps small enough to check by eye.
"""

from __future__ import annotations

import unittest

from bloodmap.model import record_extra, record_fields
from bloodmap.format import WALL_FIELDS, encode_map, parse_map
from bloodmap.model import DiskObject
from bloodmap.sector_geom import (
    outline_and_holes, sector_at, sector_contains, sector_loops, sector_walls,
    wall_length, wall_owners, wall_segment,
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


def _hole_first_map():
    """One sector whose wall run traces its hole before its outline.

    Build allows it and the campaign does it: BB4 sector 41, twenty-five
    sectors of E1M2. A reader that takes the first loop for the outline
    accepts points that stand in solid space.
    """
    disk = synthetic_map()
    disk.sectors[0].fields["wall_count"] = 8
    points = [
        (1024, 1024), (1024, 3072), (3072, 3072), (3072, 1024),      # the hole
        (0, 0), (4096, 0), (4096, 4096), (0, 4096),                  # the outline
    ]
    walls = []
    for index, (x, y) in enumerate(points):
        wall = {name: 0 for name, _codec in WALL_FIELDS}
        point2 = (index + 1) if index not in (3, 7) else (0 if index == 3 else 4)
        wall.update(x=x, y=y, point2=point2, next_wall=-1, next_sector=-1,
                    picnum=1, over_picnum=-1, extra=-1)
        walls.append(DiskObject(wall))
    disk.walls = walls
    disk.header["num_walls"] = 8
    return parse_map(encode_map(disk))


class ContainmentTests(unittest.TestCase):
    def test_the_outline_is_the_largest_loop_wherever_it_comes_in_the_run(self):
        disk = _hole_first_map()
        self.assertEqual(sector_loops(disk, 0)[0][0], (1024, 1024))   # hole first
        outline, holes = outline_and_holes(disk, 0)
        self.assertEqual(outline[0], (0, 0))
        self.assertEqual(len(holes), 1)

    def test_a_point_in_the_hole_is_not_in_the_sector(self):
        for disk in (_hole_first_map(), synthetic_multi_loop_map()):
            with self.subTest(first=sector_loops(disk, 0)[0][0]):
                self.assertTrue(sector_contains(disk, 0, 512, 512))
                self.assertFalse(sector_contains(disk, 0, 2048, 2048))
                self.assertTrue(sector_contains(disk, 0, 1024, 2048))   # on the hole's edge
                self.assertFalse(sector_contains(disk, 0, 5000, 5000))
                self.assertIsNone(sector_at(disk, 2048, 2048))
                self.assertEqual(sector_at(disk, 512, 512), 0)

    def test_where_space_is_stacked_the_floor_named_decides(self):
        disk = synthetic_two_sector_map()
        # put the second sector on top of the first, a storey up
        for wall, (x, y) in zip(disk.walls[4:], [(0, 0), (1024, 0), (1024, 1024), (0, 1024)]):
            wall.fields.update(x=x, y=y)
        for wall in (disk.walls[1], disk.walls[7]):
            wall.fields.update(next_wall=-1, next_sector=-1)
        disk.sectors[0].fields.update(floor_z=8192, ceiling_z=-8192)
        disk.sectors[1].fields.update(floor_z=-40000, ceiling_z=-60000)
        self.assertEqual(sector_at(disk, 512, 512), 0)                  # map order
        self.assertEqual(sector_at(disk, 512, 512, floor_near=8192), 0)
        self.assertEqual(sector_at(disk, 512, 512, floor_near=-41000), 1)
        self.assertEqual(sector_at(disk.to_level_ir(), 512, 512, floor_near=-41000), 1)


if __name__ == "__main__":
    unittest.main()
