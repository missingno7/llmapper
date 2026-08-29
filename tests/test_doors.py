"""Door interaction, affordance, and approach-face construction."""

from __future__ import annotations

import unittest

from bloodmap.doors import (
    authored_gate_audit,
    door_affordance_report,
    xsector_direct_use,
    xsector_remote_rx,
    z_motion_door,
)
from bloodmap.planar_layout import PlanarLayout
from experiments.sp_progression_v1 import make_layout as make_v1


def _rect(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _direct_door_layout(*, wallpush: bool, key: int | None = 1) -> PlanarLayout:
    layout = PlanarLayout(name="door-fixture")
    layout.add_region("region:hall", _rect(0, 0, 8192, 4096), wall_picnum=180)
    layout.add_region("region:alcove", _rect(2048, 4096, 6144, 6144), wall_picnum=180)
    layout.add_connection("connection:hall_alcove", "region:hall", "region:alcove")
    behavior = {
        "busy_time_a": 5, "busy_time_b": 5,
        "off_ceiling_z": 8192, "on_ceiling_z": -17536,
        "off_floor_z": 8192, "on_floor_z": 8192,
        "trigger_push": 1,
    }
    if wallpush:
        behavior.update(xsector_direct_use(key=key))
    elif key is not None:
        behavior["key"] = int(key)
    layout.add_region(
        "region:door", _rect(8192, 1024, 9216, 3072),
        ceiling_z=8192, floor_z=8192, type=600, role="doorway",
        wall_picnum=219, floor_picnum=219, ceiling_picnum=219,
        sector_behavior=behavior,
        intent={"classification": "MANDATORY", "interaction": "direct_use", "purpose": "test gate"},
    )
    layout.add_region(
        "region:room", _rect(9216, 0, 16384, 4096),
        wall_picnum=110, declared_zero_exit=True,
    )
    layout.add_connection(
        "connection:hall_door", "region:hall", "region:door",
        role="doorway", gated=True, a1=(8192, 1024), a2=(8192, 3072),
        face_picnum=219,
    )
    layout.add_connection(
        "connection:door_room", "region:door", "region:room",
        role="doorway", gated=True, a1=(9216, 1024), a2=(9216, 3072),
        face_picnum=219,
    )
    layout.set_player_start("region:hall", x=4096, y=2048, z=0)
    return layout


class DirectUseDoorTests(unittest.TestCase):
    def test_z_motion_door_has_campaign_speed_and_explicit_dual_use(self):
        fields = z_motion_door(8192, -23552, interaction="both", rx_id=100,
                               key=2)
        self.assertEqual(fields["busy_time_a"], 5)
        self.assertEqual(fields["busy_time_b"], 5)
        self.assertEqual(fields["rx_id"], 100)
        self.assertEqual(fields["key"], 2)
        self.assertEqual(fields["trigger_push"], 1)
        self.assertEqual(fields["trigger_wall_push"], 1)

    def test_z_motion_door_rejects_instant_or_unwired_remote_motion(self):
        with self.assertRaisesRegex(ValueError, "instant"):
            z_motion_door(8192, -23552, open_time=0)
        with self.assertRaisesRegex(ValueError, "rx_id"):
            z_motion_door(8192, -23552, interaction="remote")

    def test_hallway_use_requires_wallpush_not_just_push(self):
        compiled = _direct_door_layout(wallpush=False).compile()
        audit = authored_gate_audit(compiled)
        door = next(item for item in audit["gates"] if item["region_id"] == "region:door")
        self.assertTrue(any("trigger_wall_push" in item for item in door["player_facing_failures"]))
        self.assertFalse(door_affordance_report(compiled)["ok"])

    def test_direct_use_wallpush_and_face_pass_affordance(self):
        compiled = _direct_door_layout(wallpush=True).compile()
        disk = compiled.level.to_disk_map()
        extra = disk.sectors[compiled.allocations["region:door"].sector_id].extra.fields
        self.assertEqual(extra["trigger_push"], 1)
        self.assertEqual(extra["trigger_wall_push"], 1)
        self.assertEqual(extra["key"], 1)
        report = door_affordance_report(compiled)
        self.assertTrue(report["ok"], report)
        faces = [
            int(wall.fields["picnum"])
            for wall in disk.walls
            if int(wall.fields["next_sector"]) >= 0
            and int(wall.fields["picnum"]) == 219
        ]
        self.assertGreaterEqual(len(faces), 2)

    def test_remote_rx_has_no_push_bits(self):
        fields = xsector_remote_rx(100)
        self.assertEqual(fields["rx_id"], 100)
        self.assertEqual(fields["trigger_push"], 0)
        self.assertEqual(fields["trigger_wall_push"], 0)

    def test_sp_v1_keyed_door_fails_wallpush_and_visual(self):
        compiled = make_v1().compile()
        audit = authored_gate_audit(compiled)
        keyed = next(item for item in audit["gates"] if item["region_id"] == "region:keyed_door")
        text = " ".join(keyed["player_facing_failures"])
        self.assertIn("trigger_wall_push", text)
        self.assertFalse(keyed["visual_implementation"]["visually_distinct"])
        self.assertFalse(door_affordance_report(compiled)["ok"])


if __name__ == "__main__":
    unittest.main()
