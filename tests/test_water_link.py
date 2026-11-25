"""A pool's surface is a pair of markers over two copies of one outline, as the campaign's 191 are."""

import unittest

from bloodmap.planar_layout import PlanarLayout
from bloodmap.roomoverroom import MARKER_STATNUM, StackError, water_link

POOL = [(0, 0), (2048, 0), (2048, 2048), (0, 2048)]
AWAY = (-8192, 0)


def layout(lower=None):
    made = PlanarLayout(name="pool")
    made.add_region("region:pool", POOL, ceiling_z=-32768, floor_z=0, declared_zero_exit=True)
    made.add_region("region:water", lower or [(x + AWAY[0], y + AWAY[1]) for x, y in POOL], ceiling_z=8192, floor_z=40960,
                    declared_zero_exit=True)
    made.set_player_start("region:pool", x=1024, y=1024, z=0, angle=0)
    return made


class WaterLinkTests(unittest.TestCase):
    def test_both_surfaces_wear_the_water_and_the_one_below_is_under_it(self):
        made = layout()
        water_link(made, "pool", "region:pool", "region:water", link_id=7, offset=AWAY, tile=2915)
        top, below = made.regions["region:pool"], made.regions["region:water"]
        self.assertEqual((top.floor_picnum, below.ceiling_picnum), (2915, 2915))
        self.assertEqual(below.sector_behavior["underwater"], 1)
        self.assertEqual((top.floor_z, below.ceiling_z), (0, 8192), "141 of 191 pairs do not meet at one z")
        self.assertIn(("region:pool", "region:water", "water"), made.special_pairs)

    def test_the_markers_are_the_translation(self):
        made = layout()
        water_link(made, "pool", "region:pool", "region:water", link_id=7, offset=AWAY)
        upper, lower = made.placements[-2:]
        self.assertEqual((upper.type, lower.type), (9, 10))
        self.assertEqual((lower.x - upper.x, lower.y - upper.y), AWAY)
        self.assertEqual({p.behavior["data_1"] for p in (upper, lower)}, {7})
        self.assertEqual({p.status for p in (upper, lower)}, {MARKER_STATNUM})

    def test_the_built_map_pairs_them(self):
        from bloodmap.reachability import link_pairs
        made = layout()
        water_link(made, "pool", "region:pool", "region:water", link_id=7, offset=AWAY)
        compiled = made.compile()
        pairs = link_pairs(compiled.level.to_disk_map())
        self.assertEqual([p["link_id"] for p in pairs], [7])

    def test_a_copy_of_another_shape_is_refused(self):
        made = layout(lower=[(-8192, 0), (-6144, 0), (-6144, 2049), (-8192, 2049)])
        with self.assertRaises(StackError):
            water_link(made, "pool", "region:pool", "region:water", link_id=7, offset=AWAY)

    def test_a_tile_no_water_wears_is_refused(self):
        with self.assertRaises(StackError):
            water_link(layout(), "pool", "region:pool", "region:water", link_id=7, offset=AWAY, tile=568)


class LinkedSectorTests(unittest.TestCase):
    def test_the_light_stage_leaves_a_linked_sector_whole(self):
        from bloodmap.light_stage import linked

        class Sprite:
            def __init__(self, kind, sector):
                self.fields = {"type": kind, "sector": sector}

        class Disk:
            sprites = [Sprite(9, 4), Sprite(10, 9), Sprite(0, 3), Sprite(218, 5)]

        self.assertEqual(linked(Disk()), {4, 9})


if __name__ == "__main__":
    unittest.main()
