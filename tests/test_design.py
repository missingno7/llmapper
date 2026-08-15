from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.cli import main
from bloodmap.design import design_fingerprint
from bloodmap.format import write_map
from tests.helpers import synthetic_two_sector_map


class DesignUnderstandingTests(unittest.TestCase):
    def test_fingerprint_keeps_measurements_interpretations_and_evidence_separate(self):
        fingerprint = design_fingerprint(synthetic_two_sector_map().to_build_ir())

        self.assertEqual(fingerprint["$schema"], "bloodmap.design-fingerprint")
        self.assertEqual(fingerprint["scope"], "level")
        self.assertEqual(fingerprint["metrics"]["topology"]["sector_count"]["value"], 2)
        self.assertEqual(fingerprint["metrics"]["topology"]["portal_edge_count"]["value"], 1)
        self.assertIn("sector:0", fingerprint["evidence"]["sectors"])
        self.assertIn("wall:1", fingerprint["evidence"]["walls"])
        for group in fingerprint["metrics"].values():
            for metric in group.values():
                self.assertIn(metric["basis"], {"verified selection", "derived", "not inferred from tile IDs"})
                self.assertIn("confidence", metric)
        self.assertTrue(all(item["confidence"] == "heuristic" for item in fingerprint["interpretations"]))
        self.assertIn("not_inferred", fingerprint["provenance"])

    def test_selected_region_reports_external_portal_without_whole_level_boundary_noise(self):
        build = synthetic_two_sector_map().to_build_ir()
        whole = design_fingerprint(build)
        region = design_fingerprint(build, [0])

        self.assertIsNone(whole["metrics"]["space"]["connector_width_mean"]["value"])
        self.assertEqual(region["metrics"]["topology"]["portal_edge_count"]["value"], 0)
        self.assertEqual(region["metrics"]["space"]["connector_width_mean"]["value"], 1024.0)
        self.assertIn("wall:1", region["evidence"]["connectors"])

    def test_cli_indexes_and_retrieves_a_grounded_motif(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "synthetic.MAP"
            index_path = root / "index.json"
            result_path = root / "result.json"
            write_map(synthetic_two_sector_map(), map_path)

            self.assertEqual(main(["design-index", str(root), "-o", str(index_path)]), 0)
            index = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(index["$schema"], "bloodmap.design-index")
            self.assertEqual(index["entries"][0]["status"], "ok")

            self.assertEqual(main([
                "design-search", str(index_path), "--motif", "repeated-bays",
                "--limit", "1", "-o", str(result_path),
            ]), 0)
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["query"]["motif"], "repeated-bays")
            self.assertEqual(result["results"][0]["motif"], "repeated-bays")
            self.assertIn("repeated_shape_ratio", result["results"][0]["match_basis"])

            similarity_path = root / "similarity.json"
            self.assertEqual(main([
                "design-search", str(index_path), "--like", str(map_path),
                "--limit", "1", "-o", str(similarity_path),
            ]), 0)
            similarity = json.loads(similarity_path.read_text(encoding="utf-8"))
            self.assertEqual(similarity["results"][0]["map"], "synthetic.MAP")
            self.assertEqual(similarity["results"][0]["distance"], 0.0)


if __name__ == "__main__":
    unittest.main()
