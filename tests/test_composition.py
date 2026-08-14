from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.cli import main
from bloodmap.composition import (
    CompositionError, attach_fragment, connect_portals, connect_with_pathway, insert_fragment,
)
from bloodmap.format import encode_map, parse_map, read_map, write_map
from bloodmap.recipe import build_composition_recipe
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

    def test_pathway_connects_separated_rooms_with_generated_sector(self):
        other = synthetic_map().to_level_ir().extract([0])
        separated = insert_fragment(self.destination, other, dx=4096).level
        result = connect_with_pathway(separated, 1, 7)
        self.assertEqual(result.sector_ids, [2])
        self.assertEqual(result.portal_pairs, [(1, 8), (7, 10)])
        self.assertEqual(result.level.walls[1]["fields"]["next_wall"], 8)
        self.assertEqual(result.level.walls[7]["fields"]["next_wall"], 10)
        self.assertEqual(result.layout_conflicts, [])
        self.assertTrue(all(opening >= 8192 for opening in result.portal_openings))
        self.assertFalse([
            diagnostic for diagnostic in validate_map(result.level.to_disk_map())
            if diagnostic.severity == "error"
        ])

    def test_pathway_generates_bounded_stairs_for_height_difference(self):
        other = synthetic_map().to_level_ir().extract([0])
        separated = insert_fragment(self.destination, other, dx=8192, dz=6144).level
        result = separated.connect_pathway(1, 7, max_step_height=2048)
        self.assertEqual(len(result.sector_ids), 4)
        self.assertEqual(result.floor_z, [8192, 10240, 12288, 14336])
        self.assertTrue(all(step <= 2048 for step in result.step_heights))
        self.assertEqual(len(result.portal_pairs), 5)

    def test_pathway_supports_unequal_widths_and_routed_centerline(self):
        other = synthetic_map().to_level_ir().extract([0])
        separated = insert_fragment(self.destination, other, dx=8192).level
        separated.walls[6]["fields"]["y"] = 2048
        separated.walls[7]["fields"]["y"] = 2048
        result = connect_with_pathway(
            separated, 1, 7, via=[(4096, 512), (6144, 1024)], sectors=3,
        )
        self.assertEqual(len(result.sector_ids), 3)
        self.assertEqual(result.level.walls[result.wall_ids[-2]]["fields"]["next_wall"], 7)
        self.assertFalse(result.layout_conflicts)

    def test_composition_recipe_resolves_fragment_wall_allocations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_map(self.destination.to_disk_map(), root / "base.MAP")
            write_map(synthetic_map(), root / "room.MAP")
            recipe = {
                "$schema": "bloodmap.composition-recipe",
                "schema_version": 1,
                "base": "base.MAP",
                "operations": [
                    {
                        "op": "insert", "id": "room", "source": "room.MAP",
                        "sectors": [0], "dx": 4096,
                    },
                    {
                        "op": "pathway", "id": "hall",
                        "wall_a": {"absolute": 1},
                        "wall_b": {"operation": "room", "fragment_wall": 3},
                    },
                ],
            }
            result = build_composition_recipe(recipe, root)
            self.assertEqual(len(result.operations), 2)
            self.assertEqual((len(result.level.sectors), len(result.level.walls)), (3, 12))
            self.assertEqual(result.operations[1]["result"]["layout_check"]["status"], "pass")

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

    def test_attach_fragment_aligns_translates_and_connects_room(self):
        fragment = synthetic_map().to_level_ir().extract([0])
        result = attach_fragment(
            self.destination, fragment, destination_wall=1, fragment_wall=3,
        )
        self.assertEqual((result.quarter_turns, result.dx, result.dy), (0, 1024, 0))
        self.assertEqual(result.attached_wall, 7)
        self.assertEqual(result.level.walls[1]["fields"]["next_wall"], 7)
        self.assertEqual(result.level.walls[7]["fields"]["next_wall"], 1)
        self.assertEqual(result.level.walls[1]["fields"]["next_sector"], 1)
        self.assertEqual(result.level.walls[7]["fields"]["next_sector"], 0)
        self.assertEqual(result.report()["connection"]["passable_at_rest"], True)
        self.assertFalse([
            item for item in validate_map(result.level.to_disk_map())
            if item.severity == "error"
        ])

    def test_attach_fragment_chooses_quarter_turn_and_rotates_contents(self):
        fragment = synthetic_map().to_level_ir().extract([0])
        result = attach_fragment(
            self.destination, fragment, destination_wall=1, fragment_wall=0,
        )
        self.assertEqual((result.quarter_turns, result.dx, result.dy), (3, 1024, 1024))
        self.assertEqual(
            (result.level.sprites[1]["fields"]["x"], result.level.sprites[1]["fields"]["y"]),
            (1536, 512),
        )
        self.assertEqual(result.level.sprites[1]["fields"]["angle"], 1536)

    def test_attach_fragment_can_copy_rooms_and_remap_each_channel_namespace(self):
        first = attach_fragment(
            self.destination, self.fragment, destination_wall=1, fragment_wall=3,
        )
        second = attach_fragment(
            first.level, self.fragment, destination_wall=5, fragment_wall=3,
            channel_policy="remap",
        )
        self.assertEqual((len(second.level.sectors), len(second.level.walls)), (3, 12))
        self.assertEqual(second.composition.channel_map, {100: 101})
        self.assertEqual(second.level.sprites[2]["blood"]["fields"]["tx_id"], 101)
        self.assertEqual(second.level.walls[5]["fields"]["next_wall"], 11)

    def test_attach_fragment_rejects_new_geometry_overlapping_destination(self):
        fragment = synthetic_map().to_level_ir().extract([0])
        # Keep wall 3 as the doorway but fold the opposite edge through the
        # destination room after placement.
        fragment.walls[1]["fields"]["x"] = -512
        fragment.walls[2]["fields"]["x"] = -512
        with self.assertRaisesRegex(CompositionError, "overlaps existing layout"):
            attach_fragment(
                self.destination, fragment, destination_wall=1, fragment_wall=3,
            )
        allowed = attach_fragment(
            self.destination, fragment, destination_wall=1, fragment_wall=3,
            allow_overlap=True,
        )
        self.assertTrue(allowed.layout_conflicts)
        self.assertEqual(allowed.report()["layout_check"]["status"], "fail")

    def test_attach_fragment_resolves_selected_external_portal_dependency(self):
        result = attach_fragment(
            self.destination, self.fragment, destination_wall=1, fragment_wall=1,
        )
        self.assertEqual(result.quarter_turns, 2)
        self.assertTrue(result.resolved_relationships)
        self.assertTrue(all(
            item.classification == "external_geometry"
            and item.source.get("id") == 1
            for item in result.resolved_relationships
        ))
        self.assertFalse(any(
            item.classification == "external_geometry" and item.source.get("id") == 1
            for item in result.composition.unresolved_relationships
        ))

    def test_attach_fragment_fails_closed_on_unsafe_connections(self):
        fragment = synthetic_map().to_level_ir().extract([0])
        with self.assertRaisesRegex(CompositionError, "quarter-turn"):
            attach_fragment(
                self.destination, fragment, destination_wall=1, fragment_wall=3,
                quarter_turns=1,
            )

        unequal = copy.deepcopy(fragment)
        unequal.walls[0]["fields"]["x"] = 2048
        with self.assertRaisesRegex(CompositionError, "equal length"):
            attach_fragment(self.destination, unequal, destination_wall=1, fragment_wall=3)

        blocked = copy.deepcopy(self.destination)
        blocked.walls[1]["fields"]["cstat"] |= 1
        with self.assertRaisesRegex(CompositionError, "blocks movement"):
            attach_fragment(blocked, fragment, destination_wall=1, fragment_wall=3)
        cleared = attach_fragment(
            blocked, fragment, destination_wall=1, fragment_wall=3, clear_blocking=True,
        )
        self.assertTrue(cleared.blocking_cleared)
        self.assertEqual(cleared.level.walls[1]["fields"]["cstat"] & 1, 0)

        with self.assertRaisesRegex(CompositionError, "no vertical opening"):
            attach_fragment(
                self.destination, fragment, destination_wall=1, fragment_wall=3,
                dz=50000,
            )
        intentionally_closed = attach_fragment(
            self.destination, fragment, destination_wall=1, fragment_wall=3,
            dz=50000, allow_blocked=True,
        )
        self.assertFalse(intentionally_closed.report()["connection"]["passable_at_rest"])
        self.assertTrue(intentionally_closed.composition.warnings)

        sloped = copy.deepcopy(fragment)
        sloped.sectors[0]["fields"]["ceiling_stat"] |= 2
        sloped.sectors[0]["fields"]["ceiling_heinum"] = 4096
        with self.assertRaisesRegex(CompositionError, "no vertical opening"):
            attach_fragment(self.destination, sloped, destination_wall=1, fragment_wall=3)

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

    def test_attach_cli_writes_connected_map_and_placement_report(self):
        fragment = synthetic_map().to_level_ir().extract([0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination_path = root / "destination.MAP"
            fragment_path = root / "room.json"
            output_path = root / "attached.MAP"
            report_path = root / "attachment.json"
            write_map(self.destination.to_disk_map(), destination_path)
            fragment_path.write_text(json.dumps(fragment.to_dict()), encoding="utf-8")

            status = main([
                "attach", str(destination_path), str(fragment_path),
                "--destination-wall", "1", "--fragment-wall", "0",
                "--report", str(report_path), "-o", str(output_path),
            ])

            self.assertEqual(status, 0)
            attached = read_map(output_path)
            self.assertEqual(attached.walls[1].next_wall, 4)
            self.assertEqual(attached.walls[4].next_wall, 1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["placement"]["quarter_turns"], 3)
            self.assertTrue(report["connection"]["passable_at_rest"])


if __name__ == "__main__":
    unittest.main()
