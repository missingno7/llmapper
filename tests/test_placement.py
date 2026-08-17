"""Anchored sprite placement and corpus attachment signatures."""

from __future__ import annotations

import unittest

from bloodmap.construction import LevelBuilder
from bloodmap.placement import observe_sprite_attachment, validate_attachments
from bloodmap.planar_layout import PlanarLayout


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


class AnchorConstructionTests(unittest.TestCase):
    def test_wall_switch_is_not_free_floating(self):
        layout = PlanarLayout(name="anchor")
        layout.add_region("region:room", _rect(0, 0, 8192, 8192), ceiling_z=-24576, floor_z=8192)
        layout.add_region("region:east", _rect(8192, 2048, 12288, 6144), ceiling_z=-24576, floor_z=8192)
        layout.add_connection("connection:re", "region:room", "region:east")
        layout.place_on_wall(
            "sw", "region:room",
            a1=(8192, 0), a2=(8192, 2048),
            t=0.5, height_player_heights=0.65, offset_player_widths=0.08,
            type=21, picnum=1070, cstat=464, x_repeat=40, y_repeat=40,
            behavior={"tx_id": 100, "command": 1, "trigger_on": 1, "trigger_push": 1},
        )
        layout.set_player_start("region:room", x=4096, y=4096, z=0)
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        sample = observe_sprite_attachment(disk, 0)
        self.assertIn(sample["sit"], {"wall_flush", "wall_offset"})
        self.assertTrue(sample["faces_inward"])
        report = validate_attachments(disk)
        self.assertTrue(report["ok"], report["violations"])
        from bloodmap.placement import validate_use_poses
        poses = validate_use_poses(disk)
        self.assertTrue(poses["ok"], poses["violations"])


class FreeSwitchTests(unittest.TestCase):
    def test_centered_switch_is_a_violation(self):
        builder = LevelBuilder()
        room = builder.add_sector(_rect(0, 0, 8192, 8192))
        builder.add_sprite(sector=room.sector_id, x=4096, y=4096, z=0, type=21, picnum=1070)
        builder.set_player_start(sector=room.sector_id, x=2048, y=2048, z=0, angle=0)
        disk = builder.build().to_disk_map()
        report = validate_attachments(disk)
        self.assertFalse(report["ok"])
        self.assertEqual(report["violations"][0]["code"], "floating_switch")


if __name__ == "__main__":
    unittest.main()
