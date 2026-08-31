from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.blood_types import classify
from bloodmap.cli import main
from bloodmap.contents import explain_mechanisms, inventory_map, multiplayer_layout
from bloodmap.format import write_map
from bloodmap.sight import line_of_sight, spawn_sight_report, wall_occludes_sight
from tests.helpers import (
    synthetic_masked_portal_map,
    synthetic_separated_rooms_map,
    synthetic_two_sector_map,
)


class BloodTypeCatalogTests(unittest.TestCase):
    def test_known_types_are_source_backed_and_unknowns_stay_unknown(self):
        start = classify("sprite", 2)
        self.assertTrue(start["known"])
        self.assertEqual(start["name"], "kMarkerMPStart")
        self.assertEqual(start["category"], "start")
        self.assertIn("common_game.h", start["provenance"])

        ambient = classify("sprite", 710)
        self.assertTrue(ambient["known"])
        self.assertEqual(ambient["name"], "Ambient SFX")
        self.assertEqual(ambient["category"], "sound")
        self.assertIn("asound.cpp", ambient["provenance"])

        motion = classify("sector", 600)
        self.assertEqual(motion["name"], "kSectorZMotion")
        gib = classify("wall", 511)
        self.assertEqual(gib["name"], "kWallGib")
        match = classify("channel", 8)
        self.assertEqual(match["name"], "kChannelLevelStartMatch")
        user = classify("channel", 100)
        self.assertEqual(user["category"], "user")

        unknown = classify("sprite", 9999)
        self.assertFalse(unknown["known"])
        self.assertIsNone(unknown["name"])
        self.assertEqual(unknown["category"], "unknown")


class SightlineTests(unittest.TestCase):
    def test_open_portal_is_not_an_occluder_and_solid_wall_is(self):
        open_build = synthetic_two_sector_map().to_build_ir()
        blocked_build = synthetic_separated_rooms_map().to_build_ir()
        masked_build = synthetic_masked_portal_map().to_build_ir()

        open_sight = line_of_sight(open_build, 512, 512, 1536, 512)
        blocked_sight = line_of_sight(blocked_build, 512, 512, 1536, 512)
        masked_sight = line_of_sight(masked_build, 512, 512, 1536, 512)
        interior = line_of_sight(open_build, 256, 256, 768, 768)

        self.assertTrue(open_sight["clear"])
        self.assertFalse(blocked_sight["clear"])
        self.assertIsNotNone(blocked_sight["occluder"])
        self.assertTrue(masked_sight["clear"])
        self.assertTrue(interior["clear"])
        self.assertFalse(wall_occludes_sight(masked_build.walls[1]["fields"]))

    def test_cli_and_spawn_report_work_on_synthetic_and_optional_second_map(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rooms.MAP"
            write_map(synthetic_separated_rooms_map(), path)
            out = Path(directory) / "sight.json"
            self.assertEqual(main([
                "sightline", str(path),
                "--from-x", "512", "--from-y", "512",
                "--to-x", "1536", "--to-y", "512",
                "-o", str(out),
            ]), 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(payload["clear"])

        report = spawn_sight_report(synthetic_two_sector_map().to_build_ir())
        self.assertGreaterEqual(len(report["starts"]), 1)
        other = Path("maps/blood/campaign/multiplayer/BB1.MAP")
        if other.exists():
            from bloodmap.format import read_map
            extra = spawn_sight_report(read_map(other).to_build_ir())
            self.assertGreaterEqual(len(extra["starts"]), 1)
            self.assertIn("pairs", extra)


class ContentsTests(unittest.TestCase):
    def test_inventory_classifies_the_synthetic_start_sprite(self):
        disk = synthetic_two_sector_map()
        inventory = inventory_map(disk)
        self.assertEqual(inventory["$schema"], "llmapper.map-contents")
        self.assertEqual(len(inventory["starts"]["single_player"]), 2)
        self.assertEqual(inventory["starts"]["single_player"][0]["type_name"], "kMarkerSPStart")
        mechanisms = explain_mechanisms(disk)
        self.assertTrue(any(item["xsector"]["tx_id"] or item.get("ref") for item in mechanisms["sectors"]))
        layout = multiplayer_layout(disk)
        self.assertIn("spawn_sight", layout)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.MAP"
            write_map(disk, path)
            out = Path(directory) / "contents.json"
            self.assertEqual(main(["contents", str(path), "--mechanisms", "-o", str(out)]), 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["counts"]["sprites"], 2)
