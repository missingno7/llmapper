"""v3 reconstruction appearance regressions."""

from __future__ import annotations

import unittest

from bloodmap.item_display import WATER_FLOOR_PICNUM, sprite_appearance
from experiments.bb2_reconstruction_v3 import build_bb2_reconstruction_v3


class BB2V3AppearanceTests(unittest.TestCase):
    def test_water_uses_liquid_floor_family_not_tile_90(self):
        compiled = build_bb2_reconstruction_v3()
        pool = compiled.allocations["region:pool"].sector_id
        under = compiled.allocations["region:underwater"].sector_id
        self.assertEqual(compiled.level.sectors[pool]["fields"]["floor_picnum"], WATER_FLOOR_PICNUM)
        self.assertEqual(compiled.level.sectors[under]["fields"]["ceiling_picnum"], WATER_FLOOR_PICNUM)
        self.assertNotEqual(compiled.level.sectors[pool]["fields"]["floor_picnum"], 90)

    def test_pickups_use_campaign_item_tiles(self):
        compiled = build_bb2_reconstruction_v3()
        by_type: dict[int, int] = {}
        for sprite in compiled.level.sprites:
            fields = sprite["fields"]
            type_id = int(fields["type"])
            if type_id in {41, 42, 43, 45, 46, 60, 67, 68, 69, 72, 73, 76, 107, 113, 117, 140, 144, 145, 146}:
                by_type[type_id] = int(fields["picnum"])
                self.assertNotEqual(int(fields["picnum"]), 0, type_id)
        self.assertEqual(by_type[41], sprite_appearance(41)["picnum"])
        self.assertEqual(by_type[117], sprite_appearance(117)["picnum"])
        self.assertEqual(by_type[144], sprite_appearance(144)["picnum"])


if __name__ == "__main__":
    unittest.main()
