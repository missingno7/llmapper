from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.cli import main
from bloodmap.format import write_map
from bloodmap.semantics import ObservationError
from tests.helpers import synthetic_map, synthetic_two_sector_map


class LevelIRSemanticTests(unittest.TestCase):
    def test_global_observation_indexes_level_types_tiles_channels_and_sectors(self):
        level = synthetic_two_sector_map().to_level_ir()
        observation = level.observe()

        self.assertEqual(observation["$schema"], "bloodmap.level-observation")
        self.assertEqual(
            observation["level"]["counts"],
            {"sectors": 2, "walls": 8, "sprites": 2},
        )
        self.assertEqual(len(observation["sector_index"]), 2)
        self.assertEqual(observation["sector_index"][0]["ref"], "sector:0")
        self.assertEqual(observation["channels"][0]["channel"], 100)
        self.assertEqual(observation["channels"][0]["transmitters"][0]["ref"], "sprite:0")
        self.assertEqual(observation["channels"][0]["receivers"], ["sprite:1"])
        self.assertIsNone(observation["selection"])

    def test_selected_observation_explains_contents_connectors_and_dependencies(self):
        level = synthetic_two_sector_map().to_level_ir()
        observation = level.observe([0])
        selection = observation["selection"]

        self.assertEqual(selection["sector_ids"], [0])
        self.assertEqual(observation["level"]["observation_scope"], "selection")
        self.assertNotIn("tile_inventory", observation["level"])
        self.assertEqual(len(observation["sector_index"]), 1)
        self.assertEqual(observation["channels"][0]["channel"], 100)
        self.assertGreaterEqual(selection["dependency_summary"]["external_geometry"], 1)
        self.assertTrue(any(
            connector["ref"] == "wall:1" and connector["kind"] == "external_portal"
            for connector in selection["connectors"]
        ))
        self.assertEqual(selection["sprites"][0]["ref"], "sprite:0")
        self.assertTrue(any(
            item["ref"] == "sprite:0" and item["blood"]["tx_id"] == 100
            for item in selection["interactive_objects"]
        ))
        self.assertNotIn("opaque_tail_hex", json.dumps(observation))

    def test_observation_rejects_invalid_selection(self):
        level = synthetic_map().to_level_ir()
        with self.assertRaisesRegex(ObservationError, "empty"):
            level.observe([])
        with self.assertRaisesRegex(ObservationError, "out of range"):
            level.observe([99])

    def test_attachment_is_a_first_class_level_ir_operation(self):
        destination = synthetic_map().to_level_ir()
        room = synthetic_map().to_level_ir().extract([0])
        result = destination.attach(room, destination_wall=1, fragment_wall=3)

        self.assertEqual(result.level.walls[1]["fields"]["next_wall"], 7)
        self.assertEqual(result.level.walls[7]["fields"]["next_wall"], 1)

    def test_observe_cli_writes_json_from_level_ir(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "level.MAP"
            output_path = root / "observation.json"
            write_map(synthetic_two_sector_map(), map_path)

            status = main([
                "observe", str(map_path), "--sectors", "0", "-o", str(output_path),
            ])

            self.assertEqual(status, 0)
            observation = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(observation["selection"]["sector_ids"], [0])
            self.assertEqual(observation["level"]["counts"]["sectors"], 2)


if __name__ == "__main__":
    unittest.main()
