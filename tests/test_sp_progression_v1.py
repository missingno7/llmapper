"""Independent SP progression v1 compiles with anchored switches and gated exit."""

from __future__ import annotations

import unittest

from experiments.sp_progression_v1 import evaluate_progression, make_layout
from bloodmap.geometry_audit import audit_geometry
from bloodmap.placement import validate_attachments, validate_use_poses
from bloodmap.progression import analyze_progression


class SPProgressionV1Tests(unittest.TestCase):
    def test_compiles_with_anchored_switches_and_gated_exit(self):
        compiled = make_layout().compile()
        self.assertTrue(compiled.conservation.conserved)
        disk = compiled.level.to_disk_map()
        gated = {
            compiled.allocations[key].sector_id
            for key, region in compiled.layout.regions.items()
            if region.type in {600, 602} or region.role in {"doorway", "gated_pocket"}
        }
        zero_exit = {
            compiled.allocations[key].sector_id
            for key, region in compiled.layout.regions.items()
            if region.declared_zero_exit
        }
        audit = audit_geometry(disk, gated_sectors=gated, declared_zero_exit=zero_exit)
        self.assertEqual(audit["native_validation_errors"], 0)
        self.assertEqual(audit["counts"]["error_conflicts"], 0)
        self.assertTrue(validate_attachments(disk)["ok"])
        self.assertTrue(validate_use_poses(disk)["ok"])
        full = analyze_progression(disk)
        self.assertTrue(full["exit_reachable"])
        self.assertGreater(full["final_reachable"], full["physical_reachable_at_rest"])
        self.assertIn(1, full["keys_collected"])
        self.assertFalse(analyze_progression(disk, skip_key_ids={1})["exit_reachable"])
        self.assertFalse(analyze_progression(disk, skip_tx_ids={100})["exit_reachable"])
        self.assertFalse(analyze_progression(disk, skip_tx_ids={101})["exit_reachable"])
        self.assertTrue(analyze_progression(disk, skip_tx_ids={102})["exit_reachable"])

    def test_evaluate_gates_pass(self):
        compiled = make_layout().compile()
        report = evaluate_progression(compiled)
        self.assertTrue(report["gates"]["ok"], report["gates"])


if __name__ == "__main__":
    unittest.main()
