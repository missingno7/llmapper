"""BB6 pattern reconstruction compiles and keeps all DM starts on the main circuit."""

from __future__ import annotations

import unittest

from experiments.bb6_reconstruction_v1 import make_layout


class BB6PatternReconstructionTests(unittest.TestCase):
    def test_compiles_with_all_dm_starts_in_main(self):
        compiled = make_layout().compile()
        self.assertTrue(compiled.conservation.conserved)
        disk = compiled.level.to_disk_map()
        from bloodmap.geometry_audit import audit_geometry

        gated = {
            compiled.allocations[key].sector_id
            for key, region in compiled.layout.regions.items()
            if region.type in {600, 602} or region.role in {"doorway", "gated_pocket"}
        }
        audit = audit_geometry(disk, gated_sectors=gated)
        self.assertEqual(audit["native_validation_errors"], 0)
        self.assertEqual(audit["traversal"]["dm_starts_total"], 8)
        self.assertEqual(audit["traversal"]["dm_starts_in_main"], 8)


if __name__ == "__main__":
    unittest.main()
