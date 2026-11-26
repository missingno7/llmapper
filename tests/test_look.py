"""The shared look hides words on sprites and walls, and names a pose set by a hash that moves when a camera does."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap import project as P
from bloodmap.construction import LevelBuilder
from bloodmap.format import read_map, write_map
from bloodmap.model import record_fields
from bloodmap.tile_looks import word_tiles
from tools.look import hide_words, pose_hash


class HideWords(unittest.TestCase):
    def test_a_word_sprite_is_hidden_and_a_word_wall_blanked(self):
        word = min(word_tiles())
        builder = LevelBuilder()
        builder.add_sector([(0, 0), (4096, 0), (4096, 4096), (0, 4096)], floor_z=0, ceiling_z=-32768)
        builder.set_player_start(sector=0, x=512, y=512, z=-8192, angle=0)
        sign = builder.add_sprite(sector=0, x=1024, y=1024, z=-8192, type=0, status=0, picnum=word, cstat=16)
        plain = builder.add_sprite(sector=0, x=2048, y=1024, z=-8192, type=0, status=0, picnum=0, cstat=0)
        record_fields(builder.level.walls[0])["picnum"] = word
        record_fields(builder.level.walls[1])["over_picnum"] = word
        record_fields(builder.level.walls[1])["cstat"] = 16
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "x.MAP"
            write_map(builder.level.to_disk_map(), path)
            self.assertEqual(hide_words(path), 3)
            disk = read_map(path)
        self.assertTrue(record_fields(disk.sprites[sign])["cstat"] & 32768)
        self.assertFalse(record_fields(disk.sprites[plain])["cstat"] & 32768)
        self.assertEqual(record_fields(disk.walls[0])["picnum"], 255)
        self.assertFalse(record_fields(disk.walls[1])["cstat"] & 16)


class PoseHash(unittest.TestCase):
    def test_a_moved_camera_is_a_different_look(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "project.json").write_text(json.dumps({"$schema": P.SCHEMA, "kind": "level", "map": "x.MAP",
                                                           "poses": "poses.json"}), encoding="utf-8")
            poses = {"a": [{"id": "v", "x": 0, "y": 0, "angle": 0, "sector": 0}], "b": []}
            (root / "poses.json").write_text(json.dumps(poses), encoding="utf-8")
            project = P.read(root)
            first = pose_hash(project, ["a"])
            self.assertEqual(first, pose_hash(project, ["a"]))
            poses["b"] = [{"id": "w", "x": 9, "y": 9, "angle": 0, "sector": 0}]
            (root / "poses.json").write_text(json.dumps(poses), encoding="utf-8")
            self.assertEqual(first, pose_hash(project, ["a"]), "another set's camera is not this look's")
            poses["a"][0]["angle"] = 512
            (root / "poses.json").write_text(json.dumps(poses), encoding="utf-8")
            self.assertNotEqual(first, pose_hash(project, ["a"]))


if __name__ == "__main__":
    unittest.main()
