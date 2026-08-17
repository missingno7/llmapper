"""SP-v2 compiles with distinct native door realizations and affordance gates."""

from __future__ import annotations

import unittest

from bloodmap.doors import authored_gate_audit, door_affordance_report
from experiments.sp_progression_v2 import evaluate_progression, make_layout


class SPProgressionV2Tests(unittest.TestCase):
    def test_compiles_with_distinct_door_realizations(self):
        compiled = make_layout().compile()
        self.assertTrue(compiled.conservation.conserved)
        disk = compiled.level.to_disk_map()
        keyed = disk.sectors[compiled.allocations["region:keyed_door"].sector_id].extra.fields
        crypt = disk.sectors[compiled.allocations["region:crypt_door"].sector_id].extra.fields
        gallery = disk.sectors[compiled.allocations["region:gallery_door"].sector_id].extra.fields
        secret = disk.sectors[compiled.allocations["region:secret_door"].sector_id].extra.fields
        self.assertEqual(crypt["trigger_wall_push"], 1)
        self.assertEqual(crypt["key"], 0)
        self.assertEqual(keyed["trigger_wall_push"], 1)
        self.assertEqual(keyed["key"], 1)
        self.assertEqual(gallery["rx_id"], 100)
        self.assertEqual(gallery["trigger_wall_push"], 0)
        self.assertEqual(secret["rx_id"], 102)
        faces = {}
        for region_id, picnum in (
            ("region:crypt_door", 22),
            ("region:keyed_door", 495),
            ("region:gallery_door", 200),
            ("region:exit_door", 345),
        ):
            sector_id = compiled.allocations[region_id].sector_id
            faces[region_id] = picnum
            extra_walls = [
                int(wall.fields["picnum"])
                for wall in disk.walls
                if int(wall.fields["next_sector"]) == sector_id
            ]
            self.assertTrue(extra_walls)
            self.assertTrue(any(item == picnum for item in extra_walls), extra_walls)
        emblem = next(
            spr for spr in disk.sprites if int(spr.fields["picnum"]) == 2540
        )
        self.assertEqual(int(emblem.fields["cstat"]) & 16, 16)
        report = evaluate_progression(compiled)
        self.assertTrue(report["gates"]["ok"], report["gates"])
        self.assertTrue(door_affordance_report(compiled)["ok"])

    def test_secret_may_match_wall_fill(self):
        compiled = make_layout().compile()
        audit = authored_gate_audit(compiled)
        secret = next(item for item in audit["gates"] if item["region_id"] == "region:secret_door")
        self.assertTrue(secret["semantic_intent"].get("hidden"))
        self.assertEqual(secret["classification"], "OPTIONAL")

    def test_crypt_view_is_intentionally_unreachable(self):
        compiled = make_layout().compile()
        region = compiled.layout.regions["region:crypt_view"]
        self.assertEqual(region.intent["classification"], "INTENTIONALLY_UNREACHABLE")
        self.assertFalse(region.intent["player_reachable"])


if __name__ == "__main__":
    unittest.main()
