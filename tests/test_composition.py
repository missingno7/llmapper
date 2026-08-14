from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.cli import main
from bloodmap.composition import CompositionError, connect_portals, insert_fragment
from bloodmap.format import encode_map, parse_map, read_map, write_map
from tests.helpers import synthetic_map, synthetic_two_sector_map


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.destination = synthetic_map().to_level_ir()
        self.fragment = synthetic_two_sector_map().to_level_ir().extract([0])

    def test_insert_allocates_objects_extras_and_remaps_references(self):
        result = insert_fragment(self.destination, self.fragment, dx=4096, dy=2048, dz=256)
        level = result.level
        self.assertEqual((len(level.sectors), len(level.walls), len(level.sprites)), (2, 8, 2))
        self.assertEqual(result.allocations["sector"].fragment_to_destination, {0: 1})
        self.assertEqual(result.allocations["wall"].fragment_to_destination, {0: 4, 1: 5, 2: 6, 3: 7})
        self.assertEqual(result.allocations["sprite"].fragment_to_destination, {0: 1})
        self.assertEqual(level.sectors[1]["fields"]["wall_ptr"], 4)
        self.assertEqual(level.walls[4]["fields"]["point2"], 5)
        self.assertEqual(level.sprites[1]["fields"]["sector"], 1)
        self.assertEqual(level.sprites[1]["fields"]["extra"], 2)
        self.assertEqual(level.sprites[1]["blood"]["fields"]["reference"], 1)
        self.assertEqual(level.sprites[1]["fields"]["x"], 4608)
        self.assertEqual(level.sprites[1]["fields"]["z"], 256)
        self.assertTrue(result.unresolved_relationships)
        rebuilt = parse_map(encode_map(level.to_disk_map()))
        self.assertFalse([d for d in validate_map(rebuilt) if d.severity == "error"])

    def test_channel_collision_errors_or_remaps_deterministically(self):
        self.destination.sprites[0]["blood"]["fields"]["rx_id"] = 100
        with self.assertRaisesRegex(CompositionError, "collides"):
            insert_fragment(self.destination, self.fragment)
        result = insert_fragment(self.destination, self.fragment, channel_policy="remap")
        self.assertEqual(result.channel_map, {100: 101})
        self.assertEqual(result.level.sprites[1]["blood"]["fields"]["tx_id"], 101)

    def test_repeated_insertions_use_collision_free_indices_and_channels(self):
        first = insert_fragment(self.destination, self.fragment)
        second = insert_fragment(first.level, self.fragment, dx=4096, channel_policy="remap")
        self.assertEqual(first.level.sprites[1]["fields"]["extra"], 2)
        self.assertEqual(second.level.sprites[2]["fields"]["extra"], 3)
        self.assertEqual(second.channel_map, {100: 101})
        self.assertEqual(second.level.sprites[2]["blood"]["fields"]["tx_id"], 101)

    def test_system_channels_are_shared_and_reserved_unknowns_fail_closed(self):
        system = copy.deepcopy(self.fragment)
        system.sprites[0]["blood"]["fields"]["tx_id"] = 4
        self.destination.sprites[0]["blood"]["fields"]["rx_id"] = 4
        result = insert_fragment(self.destination, system, channel_policy="remap")
        self.assertEqual(result.channel_map[4], 4)

        unknown = copy.deepcopy(self.fragment)
        unknown.sprites[0]["blood"]["fields"]["tx_id"] = 42
        self.destination.sprites[0]["blood"]["fields"]["rx_id"] = 42
        with self.assertRaisesRegex(CompositionError, "cannot be safely remapped"):
            insert_fragment(self.destination, unknown, channel_policy="remap")

    def test_malformed_fragment_identity_and_channels_fail_closed(self):
        malformed = copy.deepcopy(self.fragment)
        malformed.walls[0]["id"] = 3
        with self.assertRaisesRegex(CompositionError, "dense and ordered"):
            insert_fragment(self.destination, malformed)

        malformed = copy.deepcopy(self.fragment)
        malformed.sprites[0]["blood"]["fields"]["tx_id"] = 1024
        with self.assertRaisesRegex(CompositionError, "outside the Blood field range"):
            insert_fragment(self.destination, malformed)

    def test_explicit_portal_connection_requires_reversed_coincident_walls(self):
        fragment = synthetic_map().to_level_ir().extract([0])
        inserted = insert_fragment(self.destination, fragment, dx=1024).level
        connected = connect_portals(inserted, 1, 7)
        self.assertEqual(connected.walls[1]["fields"]["next_wall"], 7)
        self.assertEqual(connected.walls[1]["fields"]["next_sector"], 1)
        self.assertEqual(connected.walls[7]["fields"]["next_wall"], 1)
        self.assertEqual(connected.walls[7]["fields"]["next_sector"], 0)
        self.assertFalse([d for d in validate_map(connected.to_disk_map()) if d.severity == "error"])
        with self.assertRaises(CompositionError):
            connect_portals(inserted, 0, 4)

    def test_quarter_turn_placement_transforms_geometry_and_angles(self):
        fragment = synthetic_map().to_level_ir().extract([0])
        result = insert_fragment(
            self.destination, fragment, dx=3000, dy=4000, quarter_turns=1,
            pivot_x=0, pivot_y=0,
        )
        # Local wall (1024, 0) rotates to (0, 1024), then translates.
        self.assertEqual(
            (result.level.walls[5]["fields"]["x"], result.level.walls[5]["fields"]["y"]),
            (3000, 5024),
        )
        self.assertEqual(result.level.sprites[1]["fields"]["angle"], 512)

    def test_report_is_machine_readable(self):
        result = insert_fragment(self.destination, self.fragment)
        report = result.report()
        self.assertEqual(report["result_counts"], {"sectors": 2, "walls": 8, "sprites": 2})
        self.assertIn("allocations", report)
        self.assertIn("unresolved_relationships", report)

    def test_compose_cli_writes_reparseable_map_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination_path = root / "destination.MAP"
            fragment_path = root / "fragment.json"
            output_path = root / "composed.MAP"
            report_path = root / "report.json"
            write_map(self.destination.to_disk_map(), destination_path)
            fragment_path.write_text(json.dumps(self.fragment.to_dict()), encoding="utf-8")

            status = main([
                "compose", str(destination_path), str(fragment_path),
                "--x", "4096", "--channel-policy", "remap",
                "--report", str(report_path), "-o", str(output_path),
            ])

            self.assertEqual(status, 0)
            self.assertEqual(len(read_map(output_path).sectors), 2)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["result_counts"]["walls"], 8)

    def test_connect_cli_writes_reciprocal_portal(self):
        adjacent = insert_fragment(
            self.destination, synthetic_map().to_level_ir().extract([0]), dx=1024,
        ).level
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "adjacent.MAP"
            output_path = root / "connected.MAP"
            write_map(adjacent.to_disk_map(), input_path)

            status = main([
                "connect", str(input_path), "--wall-a", "1", "--wall-b", "7",
                "-o", str(output_path),
            ])

            self.assertEqual(status, 0)
            connected = read_map(output_path)
            self.assertEqual(connected.walls[1].next_wall, 7)
            self.assertEqual(connected.walls[7].next_wall, 1)


if __name__ == "__main__":
    unittest.main()
