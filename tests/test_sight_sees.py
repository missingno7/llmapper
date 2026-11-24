"""A sight line walked through portals knows the heights of what it passes."""

import unittest

from bloodmap.planar_layout import PlanarLayout
from bloodmap.sight import near_sectors, sees


def three_rooms(middle_floor=0, middle_ceiling=-32768):
    """Three rooms in a row, the middle one with its own floor and ceiling."""
    layout = PlanarLayout()
    for k, (floor, ceiling) in enumerate(((0, -32768), (middle_floor, middle_ceiling), (0, -32768))):
        x = 1024 * k
        layout.add_region(f"r{k}", [(x, 0), (x + 1024, 0), (x + 1024, 1024), (x, 1024)], floor_z=floor, ceiling_z=ceiling,
                          floor_picnum=0, ceiling_picnum=0, wall_picnum=0, floor_shade=0, wall_shade=0, ceiling_shade=0,
                          role="interior", declared_zero_exit=True)
    for k in (0, 1):
        x = 1024 * (k + 1)
        layout.add_connection(f"c{k}", f"r{k}", f"r{k + 1}", a1=(x, 0), a2=(x, 1024), min_width=1, min_opening=0)
    layout.set_player_start("r0", x=512, y=512, z=-1000)
    compiled = layout.compile()
    return compiled.level.to_disk_map().to_level_ir(), [compiled.allocations[f"r{k}"].sector_id for k in range(3)]


class SeesTests(unittest.TestCase):
    EYE, AT = (200, 512, -15000), (2900, 512, -15000)

    def test_through_two_open_portals(self):
        level, ids = three_rooms()
        self.assertTrue(sees(level, ids[0], self.EYE, self.AT))

    def test_a_raised_floor_between_hides_it(self):
        level, ids = three_rooms(middle_floor=-20000)
        self.assertFalse(sees(level, ids[0], self.EYE, self.AT))

    def test_a_low_ceiling_between_hides_it(self):
        level, ids = three_rooms(middle_ceiling=-10000)
        self.assertFalse(sees(level, ids[0], self.EYE, self.AT))
        self.assertTrue(sees(level, ids[0], (200, 512, -5000), (2900, 512, -5000)))

    def test_a_wall_hides_it(self):
        level, ids = three_rooms()
        self.assertFalse(sees(level, ids[0], self.EYE, (2900, 5000, -15000)))

    def test_near_sectors_stop_at_the_reach(self):
        level, ids = three_rooms()
        self.assertEqual(near_sectors(level, ids[0], 100, 512, 1200), ids[:2])


if __name__ == "__main__":
    unittest.main()
