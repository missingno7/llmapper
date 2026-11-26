"""A remake status must distinguish stale evidence and changed native mechanisms."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from bloodmap import project as P

from bloodmap.construction import LevelBuilder
from bloodmap.format import encode_map, parse_map
from bloodmap.model import record_fields

SCRIPT = Path(__file__).resolve().parents[1] / "status.py"
spec = importlib.util.spec_from_file_location("e4l1_status", SCRIPT)
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


class EvidenceIdentityTests(unittest.TestCase):
    def test_map_save_invalidates_old_evidence(self):
        manifest = {"source_sha256": "old", "poses_sha256": "poses"}
        self.assertEqual(status.evidence_state(manifest, "new", "poses"), "historical map")

    def test_camera_edit_invalidates_evidence_even_with_same_map(self):
        manifest = {"source_sha256": "map", "poses_sha256": "old"}
        self.assertEqual(status.evidence_state(manifest, "map", "new"), "historical poses")
        self.assertEqual(status.evidence_state(manifest, "map", "old"), "current")
        self.assertEqual(status.evidence_state(None, "map", "old"), "missing")

    def test_native_mechanism_change_is_reported_separately_from_material(self):
        builder = LevelBuilder()
        builder.add_sector([(0, 0), (4096, 0), (4096, 4096), (0, 4096)],
                           floor_z=0, ceiling_z=-32768)
        builder.set_player_start(sector=0, x=512, y=512, z=-8192, angle=0)
        builder.set_behavior("sector", 0, busy_time_a=8)
        before = parse_map(encode_map(builder.level.to_disk_map()))
        record_fields(builder.level.walls[0])["picnum"] = 181
        builder.set_behavior("sector", 0, busy_time_a=12)
        after = builder.level.to_disk_map()
        result = status.preservation(before, after)
        self.assertEqual(result["geometry_changes"], [])
        self.assertEqual(result["existing_extension_changes"], ["sector 0"])
        record_fields(after.walls[0])["x"] = 64
        self.assertIn("wall 0 x", status.preservation(before, after)["geometry_changes"])
        record_fields(after.sectors[0])["floor_stat"] ^= 2
        self.assertIn("sector 0 floor_stat slope flag",
                      status.preservation(before, after)["geometry_changes"])


class PlaceEvidenceTests(unittest.TestCase):
    """A place's evidence is its last critique round, judged by the hashes its packet names."""

    def project(self, folder):
        root = Path(folder)
        (root / "project.json").write_text(json.dumps({"$schema": P.SCHEMA, "kind": "level", "map": "x.MAP",
                                                       "poses": "poses.json", "critique": "reports/critique"}))
        return P.read(root)

    def test_no_round_is_missing_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            found = status.place_evidence(self.project(folder), "hall", "map", "poses")
        self.assertEqual((found["evidence"], found["round"]), ("missing", None))

    def test_an_unanswered_round_is_current_but_unread_until_a_frame_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            project = self.project(folder)
            packet = project.rounds("hall") / "round-1"
            (packet / "ours" / "frames").mkdir(parents=True)
            frame = packet / "ours" / "frames" / "view_01.png"
            frame.write_bytes(b"frame")
            (packet / "packet.json").write_text(json.dumps({
                "round": 1, "kind": "hall", "readers": ["recognition", "comparison", "use", "sense"],
                "source_sha256": "map", "poses_sha256": "poses",
                "frames": {"ours/frames/view_01.png": hashlib.sha256(b"frame").hexdigest()}}))
            found = status.place_evidence(project, "hall", "map", "poses")
            self.assertEqual((found["evidence"], found["review"]), ("current", "prepared, no reader has answered"))
            self.assertEqual(status.place_evidence(project, "hall", "saved", "poses")["evidence"], "historical map")
            frame.write_bytes(b"another")
            self.assertEqual(status.place_evidence(project, "hall", "map", "poses")["evidence"], "frames changed")


if __name__ == "__main__":
    unittest.main()
