from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from bloodmap import ConstructionError, LevelBuilder, build_first_puzzle_room, portal_profiles
from bloodmap.analysis import validate_map
from bloodmap.cli import main
from bloodmap.format import encode_map, parse_map


class ConstructionTests(unittest.TestCase):
    def test_builder_rejects_inverted_and_self_intersecting_polygons(self):
        with self.assertRaisesRegex(ConstructionError, "winding"):
            LevelBuilder().add_sector([(0, 0), (0, 1024), (1024, 1024), (1024, 0)])
        with self.assertRaisesRegex(ConstructionError, "zero area|self-intersects"):
            LevelBuilder().add_sector([(0, 0), (1024, 1024), (0, 1024), (1024, 0)])

    def test_first_room_cli_writes_map_and_machine_readable_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, report = root / "room.MAP", root / "report.json"
            self.assertEqual(main(["design-first-room", "-o", str(output), "--report", str(report)]), 0)
            self.assertTrue(output.is_file())
            value = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(value["name"], "first-puzzle-room")
            self.assertEqual(value["counts"], {"sectors": 5, "walls": 28, "sprites": 7})

    def test_first_puzzle_room_is_deterministic_and_functionally_wired(self):
        first = build_first_puzzle_room()
        second = build_first_puzzle_room()
        first_bytes = encode_map(first.level.to_disk_map())
        self.assertEqual(first_bytes, encode_map(second.level.to_disk_map()))
        reparsed = parse_map(first_bytes)
        self.assertFalse([item for item in validate_map(reparsed) if item.severity == "error"])
        self.assertEqual((len(first.level.sectors), len(first.level.walls), len(first.level.sprites)), (5, 28, 7))
        self.assertEqual(first.level.player_start["sector"], 0)
        self.assertEqual(
            (first.level.player_start["x"], first.level.player_start["y"], first.level.player_start["z"]),
            (15488, 3072, 0),
        )

        profiles = first.report["portal_profiles"]
        self.assertEqual(len(profiles), 4)
        self.assertTrue(all(profile["width"] >= 3072 for profile in profiles))
        self.assertTrue(all(not profile["walkable_at_rest"] for profile in profiles))
        self.assertTrue(all(profile["walkable_when_open"] for profile in profiles))

        graph = {
            item["channel"]: item for item in first.report["channel_graph"]["channels"]
        }
        for channel in (100, 101):
            self.assertEqual(len(graph[channel]["transmitters"]), 1)
            self.assertEqual(len(graph[channel]["receivers"]), 1)
        for sprite_id, channel in ((0, 100), (1, 101)):
            sprite = first.level.sprites[sprite_id]
            self.assertEqual(sprite["fields"]["type"], 21)
            self.assertEqual(sprite["blood"]["fields"]["tx_id"], channel)
            self.assertEqual(sprite["blood"]["fields"]["trigger_push"], 1)

    def test_builder_creates_reparseable_level_with_portal_and_behavior(self):
        builder = LevelBuilder()
        room = builder.add_sector([(0, 0), (8192, 0), (8192, 4096), (0, 4096)])
        hall = builder.add_sector([(8192, 0), (12288, 0), (12288, 4096), (8192, 4096)])
        builder.connect(room.wall_ids[1], hall.wall_ids[3])
        builder.set_behavior(
            "sector", hall.sector_id, rx_id=100, busy_time_a=5, busy_time_b=5,
            interruptable=1, off_ceiling_z=-24576, on_ceiling_z=-16384,
            off_floor_z=8192, on_floor_z=8192,
        )
        switch = builder.add_sprite(
            sector=room.sector_id, x=0, y=2048, z=0, type=21, picnum=1070,
            cstat=464, x_repeat=40, y_repeat=40,
        )
        builder.set_behavior(
            "sprite", switch, tx_id=100, command=1, trigger_on=1,
            trigger_push=1, data_1=203,
        )
        builder.set_player_start(sector=room.sector_id, x=4096, y=2048, z=0, angle=1024)
        level = builder.build()
        self.assertEqual(level.walls[0]["fields"]["x_repeat"], 64)
        reparsed = parse_map(encode_map(level.to_disk_map()))
        self.assertFalse([item for item in validate_map(reparsed) if item.severity == "error"])
        self.assertEqual(reparsed.header["num_sectors"], 2)
        self.assertEqual(reparsed.header["num_sprites"], 1)
        self.assertEqual(reparsed.sprites[0].extra.tx_id, 100)

    def test_portal_profiles_reject_narrow_connections_and_understand_open_doors(self):
        builder = LevelBuilder()
        room = builder.add_sector([(0, 0), (8192, 0), (8192, 1024), (0, 1024)])
        door = builder.add_sector(
            [(8192, 0), (10240, 0), (10240, 1024), (8192, 1024)],
            ceiling_z=8192, floor_z=8193, type=600,
        )
        builder.connect(room.wall_ids[1], door.wall_ids[3])
        builder.set_behavior(
            "sector", door.sector_id, rx_id=100,
            off_ceiling_z=8192, on_ceiling_z=-24576,
            off_floor_z=8193, on_floor_z=8193,
        )
        builder.set_player_start(sector=room.sector_id, x=4096, y=512, z=0, angle=0)
        level = builder.build()
        profile = portal_profiles(level, min_width=2048)[0]
        self.assertFalse(profile["wide_enough"])
        self.assertFalse(profile["walkable_at_rest"])
        self.assertFalse(profile["walkable_when_open"])

        profile = portal_profiles(level, min_width=1024)[0]
        self.assertTrue(profile["wide_enough"])
        self.assertFalse(profile["walkable_at_rest"])
        self.assertTrue(profile["walkable_when_open"])


if __name__ == "__main__":
    unittest.main()
