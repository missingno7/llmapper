"""Incremental map patches preserve unrelated manual edits and refuse conflicting ones."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from bloodmap.construction import LevelBuilder
from bloodmap.format import encode_map, read_map
from bloodmap.model import record_fields

SCRIPT = Path(__file__).resolve().parents[1] / "edit_map.py"
spec = importlib.util.spec_from_file_location("e4l1_edit", SCRIPT)
editor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(editor)


class IncrementalMapEditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.map = self.root / "current.MAP"
        builder = LevelBuilder()
        builder.add_sector([(0, 0), (4096, 0), (4096, 4096), (0, 4096)],
                           ceiling_z=-32768, floor_z=0)
        builder.set_player_start(sector=0, x=512, y=512, z=-8192, angle=0)
        record_fields(builder.level.walls[0])["shade"] = 0
        self.original = encode_map(builder.level.to_disk_map())
        self.map.write_bytes(self.original)
        self.patch = self.root / "pass.json"
        self.plan = {"id": "test-pass", "edits": [{"kind": "wall", "index": 0,
                     "identity": {"x": 0, "y": 0}, "fields": {"shade": [0, 20]}}],
                     "sprites": [{"name": "lamp", "fields": {"sector": 0, "x": 1024,
                       "y": 1024, "z": -8192, "type": 0, "picnum": 501,
                       "status": 0, "cstat": 128, "x_repeat": 16, "y_repeat": 16,
                       "shade": -16, "angle": 0}, "extra": {}}]}
        self.patch.write_text(json.dumps(self.plan))

    def test_apply_creates_exact_backup_and_is_byte_idempotent(self):
        report = editor.apply_patch(self.map, self.patch)
        self.assertEqual((self.root / report["backup"]).read_bytes(), self.original)
        changed = self.map.read_bytes()
        self.assertNotEqual(changed, self.original)
        self.assertTrue(editor.apply_patch(self.map, self.patch)["unchanged"])
        self.assertEqual(self.map.read_bytes(), changed)
        self.assertEqual(len(read_map(self.map).sprites), 1)

    def test_unrelated_manual_field_survives(self):
        disk = read_map(self.map)
        record_fields(disk.walls[1])["shade"] = 13
        self.map.write_bytes(encode_map(disk))
        editor.apply_patch(self.map, self.patch)
        self.assertEqual(record_fields(read_map(self.map).walls[1])["shade"], 13)

    def test_conflicting_manual_field_aborts_without_a_write(self):
        disk = read_map(self.map)
        record_fields(disk.walls[0])["shade"] = 17
        self.map.write_bytes(encode_map(disk))
        changed = self.map.read_bytes()
        with self.assertRaises(editor.EditConflict):
            editor.apply_patch(self.map, self.patch)
        self.assertEqual(self.map.read_bytes(), changed)
        self.assertFalse((self.root / "snapshots").exists())

    def test_dry_run_does_not_write_a_map_or_backup(self):
        report = editor.apply_patch(self.map, self.patch, dry_run=True)
        self.assertTrue(report["dry_run"])
        self.assertEqual(self.map.read_bytes(), self.original)
        self.assertFalse((self.root / "snapshots").exists())

    def test_appended_manual_change_is_not_duplicated_or_overwritten(self):
        editor.apply_patch(self.map, self.patch)
        disk = read_map(self.map)
        record_fields(disk.sprites[0])["x"] += 64
        self.map.write_bytes(encode_map(disk))
        saved = self.map.read_bytes()
        with self.assertRaises(editor.EditConflict):
            editor.apply_patch(self.map, self.patch)
        self.assertEqual(self.map.read_bytes(), saved)

    def test_interrupted_report_write_recovers_without_duplicate_sprites(self):
        editor.apply_patch(self.map, self.patch)
        (self.root / "reports/test-pass-applied.json").unlink()
        saved = self.map.read_bytes()
        editor.apply_patch(self.map, self.patch)
        self.assertEqual(self.map.read_bytes(), saved)
        self.assertEqual(len(read_map(self.map).sprites), 1)

    def test_baseline_is_never_an_edit_target(self):
        baseline = self.root / "E4L1-baseline.MAP"
        baseline.write_bytes(self.original)
        with self.assertRaises(editor.EditConflict):
            editor.apply_patch(baseline, self.patch)
        self.assertEqual(baseline.read_bytes(), self.original)

    def test_native_sky_panorama_is_a_guarded_incremental_edit(self):
        self.plan["edits"] = [{"kind": "sky", "index": 0, "fields": {
            "bits": [0, 2], "offsets": [[0], [0, 1, 2, 3]]}}]
        self.patch.write_text(json.dumps(self.plan))
        editor.apply_patch(self.map, self.patch)
        disk = read_map(self.map)
        self.assertEqual(disk.header["sky_bits"], 2)
        self.assertEqual(disk.sky_offsets, [0, 1, 2, 3])
