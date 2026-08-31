from __future__ import annotations

import os
import unittest
from fractions import Fraction
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.conversion import (
    ConversionError, convert_build_ir, convert_shade, native_scale,
)
from bloodmap.differential import compare_e3l1_pair
from bloodmap.duke import encode_duke_map, parse_duke_map, read_duke_map
from bloodmap.format import encode_map, parse_map, read_map
from tests.helpers import corpus_map


ROOT = Path(__file__).resolve().parents[1]
BLOOD_MAPS = Path(os.environ.get("BLOODMAP_CORPUS", ROOT / "maps" / "blood"))
DNE3L1 = corpus_map("DNE3L1.MAP")
DUKE_MAPS = Path(os.environ.get("DUKEMAP_CORPUS", ROOT / "maps" / "duke3d"))


class CrossGameTests(unittest.TestCase):
    def _pair(self) -> tuple[Path, Path]:
        duke, blood = DUKE_MAPS / "E3L1.MAP", DNE3L1
        if not duke.exists() or not blood.exists():
            self.skipTest("E3L1/DNE3L1 pair is not present in the local corpora")
        return duke, blood

    def test_differential_recovers_scale_geometry_shading_and_material_evidence(self):
        duke, blood = self._pair()
        report = compare_e3l1_pair(duke, blood)
        selected = report["normalization"]["xy_scale_duke_to_blood"]["selected"]
        self.assertEqual((selected["numerator"], selected["denominator"]), (3, 2))
        self.assertEqual(report["pair_role"], "geometry-matched-hand-conversion")
        self.assertGreaterEqual(report["geometry"]["unique_exact_sector_correspondences"], 230)
        self.assertGreaterEqual(report["geometry"]["unique_exact_wall_correspondences"], 1600)
        self.assertGreater(report["lighting"]["walls"]["exact_double_fraction"], 0.8)
        exact = {
            (item["duke_tile"], item["blood_tile"])
            for item in report["materials"]["candidates"]
            if item["classification"] == "exact-known"
        }
        self.assertTrue({(89, 2500), (793, 1353)} <= exact)

    def test_profiles_and_shading_are_explicit_and_reversible_where_unsaturated(self):
        self.assertEqual(native_scale("duke3d", "blood"), Fraction(3, 2))
        self.assertEqual(native_scale("blood", "duke3d"), Fraction(2, 3))
        self.assertEqual(convert_shade(17, "duke3d", "blood"), 34)
        self.assertEqual(convert_shade(34, "blood", "duke3d"), 17)
        self.assertEqual(convert_shade(-127, "duke3d", "blood"), 0)

    def test_geometry_only_conversion_both_directions_is_structurally_valid(self):
        duke_path, blood_path = self._pair()

        duke = read_duke_map(duke_path)
        as_blood, duke_report = convert_build_ir(duke.to_build_ir(), "blood", policy="geometry-only")
        reparsed_blood = parse_map(encode_map(as_blood))
        self.assertEqual(len(reparsed_blood.sectors), len(duke.sectors))
        self.assertEqual(len(reparsed_blood.walls), len(duke.walls))
        self.assertEqual(len(reparsed_blood.sprites), 0)
        self.assertFalse([item for item in validate_map(reparsed_blood) if item.severity == "error"])
        self.assertTrue(duke_report["geometry"]["topology_preserved"])
        self.assertEqual(duke_report["overall"]["gameplay_fidelity"], "unsupported")

        blood = read_map(blood_path)
        as_duke, blood_report = convert_build_ir(blood.to_build_ir(), "duke3d", policy="geometry-only")
        reparsed_duke = parse_duke_map(encode_duke_map(as_duke))
        self.assertEqual(len(reparsed_duke.sectors), len(blood.sectors))
        self.assertEqual(len(reparsed_duke.walls), len(blood.walls))
        self.assertEqual(len(reparsed_duke.sprites), 0)
        self.assertFalse([item for item in reparsed_duke.to_build_ir().validate() if item.severity == "error"])
        self.assertTrue(blood_report["geometry"]["slopes_preserved"])

    def test_semantic_policy_is_conservative_and_strict_policy_refuses_guessing(self):
        duke_path, blood_path = self._pair()
        duke = read_duke_map(duke_path).to_build_ir()
        blood = read_map(blood_path).to_build_ir()
        _disk, duke_report = convert_build_ir(duke, "blood", policy="semantic")
        _disk, blood_report = convert_build_ir(blood, "duke3d", policy="semantic")
        self.assertTrue(duke_report["entities"]["translated"])
        self.assertTrue(duke_report["entities"]["omitted"])
        self.assertTrue(blood_report["entities"]["translated"])
        with self.assertRaisesRegex(ConversionError, "strict cross-game conversion"):
            convert_build_ir(duke, "blood", policy="strict")


if __name__ == "__main__":
    unittest.main()
