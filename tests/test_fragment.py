from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path

from bloodmap.fragment import (
    FragmentError, LevelFragment, apply_fragment_in_place,
    extract_behavior_closed_fragment, extract_fragment,
)
from bloodmap.format import encode_map, parse_map, read_map
from tests.helpers import synthetic_multi_loop_map, synthetic_two_sector_map


MAPS = Path(os.environ.get("BLOODMAP_CORPUS", Path(__file__).resolve().parents[1] / "maps"))


class FragmentTests(unittest.TestCase):
    def setUp(self):
        self.level = synthetic_two_sector_map().to_level_ir()

    def test_boundary_dependencies_are_classified_and_detached(self):
        fragment = extract_fragment(self.level, [0])
        self.assertEqual((len(fragment.sectors), len(fragment.walls), len(fragment.sprites)), (1, 4, 1))
        self.assertEqual(fragment.walls[1]["fields"]["next_wall"], -1)
        self.assertEqual(fragment.walls[1]["fields"]["next_sector"], -1)
        classifications = fragment.dependency_summary()
        self.assertGreaterEqual(classifications["external_geometry"], 1)
        self.assertGreaterEqual(classifications["external_trigger"], 1)
        self.assertGreaterEqual(classifications["external_marker"], 1)
        self.assertGreaterEqual(classifications["external_ownership"], 2)

    def test_complete_selection_localizes_internal_references(self):
        fragment = extract_fragment(self.level, [0, 1])
        self.assertFalse(any(r.classification == "external_geometry" for r in fragment.relationships))
        self.assertTrue(any(r.relation == "portal" and r.classification == "internal_reference" for r in fragment.relationships))
        self.assertTrue(any(r.relation == "trigger" and r.classification == "internal_reference" for r in fragment.relationships))
        self.assertEqual(fragment.walls[1]["fields"]["next_wall"], 7)
        self.assertEqual(fragment.sprites[0]["fields"]["owner"], 1)
        self.assertEqual(fragment.sprites[0]["blood"]["fields"]["target"], 1)

    def test_behavior_closure_follows_gameplay_but_not_geometry(self):
        result = extract_behavior_closed_fragment(self.level, [0])
        self.assertEqual(result.requested_sector_ids, [0])
        self.assertEqual(result.selected_sector_ids, [0, 1])
        self.assertEqual([item["sector_id"] for item in result.additions], [1])
        self.assertFalse(result.unresolved_relationships)
        self.assertFalse(any(
            relationship.classification == "external_geometry"
            for relationship in result.fragment.relationships
        ))

    def test_behavior_closure_preserves_dangling_channels_and_limit(self):
        self.level.sprites[1]["blood"]["fields"]["rx_id"] = 0
        result = self.level.extract_closed([0])
        self.assertEqual(result.selected_sector_ids, [0, 1])
        dangling = [
            relationship for relationship in result.unresolved_relationships
            if relationship.target.get("status") == "no_receiver"
        ]
        self.assertTrue(dangling)
        with self.assertRaisesRegex(FragmentError, "max_sectors"):
            extract_behavior_closed_fragment(self.level, [0], max_sectors=1)

    def test_same_source_reinsertion_is_exact_and_restores_stale_values(self):
        fragment = extract_fragment(self.level, [0])
        restored = apply_fragment_in_place(self.level, fragment)
        self.assertEqual(restored.to_dict(), self.level.to_dict())
        self.assertEqual(restored.sectors[0]["blood"]["fields"]["reference"], 9)
        self.assertEqual(restored.sprites[0]["blood"]["fields"]["reference"], 12)

    def test_fragment_mutation_changes_only_selected_source_geometry(self):
        fragment = extract_fragment(self.level, [0])
        fragment.walls[0]["fields"]["x"] += 256
        restored = apply_fragment_in_place(self.level, fragment)
        self.assertEqual(restored.walls[0]["fields"]["x"], self.level.walls[0]["fields"]["x"] + 256)
        self.assertEqual(restored.walls[4:], self.level.walls[4:])
        self.assertEqual(restored.walls[1]["fields"]["next_wall"], 7)

    def test_fragment_json_roundtrip(self):
        fragment = self.level.extract([0])
        value = json.loads(json.dumps(fragment.to_dict(), sort_keys=True))
        reparsed = LevelFragment.from_dict(value)
        self.assertEqual(reparsed, fragment)
        self.assertEqual(reparsed.apply_to_source(self.level).to_dict(), self.level.to_dict())

    def test_multi_loop_sector_keeps_both_loops(self):
        level = synthetic_multi_loop_map().to_level_ir()
        fragment = extract_fragment(level, [0])
        self.assertEqual(len(fragment.walls), 8)
        self.assertEqual(fragment.walls[3]["fields"]["point2"], 0)
        self.assertEqual(fragment.walls[7]["fields"]["point2"], 4)
        self.assertEqual(apply_fragment_in_place(level, fragment).to_dict(), level.to_dict())

    def test_system_channel_is_source_derived(self):
        self.level.sprites[0]["blood"]["fields"]["tx_id"] = 4
        fragment = extract_fragment(self.level, [0])
        system = [r for r in fragment.relationships if r.classification == "system_global"]
        self.assertTrue(any(r.target.get("name") == "level_exit_normal" for r in system))

    def test_rejects_empty_or_wrong_source(self):
        with self.assertRaises(FragmentError):
            extract_fragment(self.level, [])
        fragment = extract_fragment(self.level, [0])
        wrong = copy.deepcopy(self.level)
        wrong.metadata["source_crc32"] = "deadbeef"
        with self.assertRaises(FragmentError):
            apply_fragment_in_place(wrong, fragment)
        changed = copy.deepcopy(self.level)
        changed.walls[0]["fields"]["x"] += 1
        with self.assertRaisesRegex(FragmentError, "fingerprint"):
            apply_fragment_in_place(changed, fragment)

    def test_original_map_sector_roundtrips_through_fragment_when_available(self):
        path = MAPS / "E1M1.MAP"
        if not path.exists():
            self.skipTest("E1M1.MAP is not present in the local corpus")
        disk = read_map(path)
        level = disk.to_level_ir()
        fragment = extract_fragment(level, [0])
        restored = apply_fragment_in_place(level, fragment)
        self.assertEqual(restored.to_dict(), level.to_dict())
        self.assertEqual(encode_map(restored.to_disk_map()), path.read_bytes())

    def test_every_available_map_reinserts_representative_sectors_exactly(self):
        paths = sorted(MAPS.glob("*.MAP"))
        if not paths:
            self.skipTest("no local Blood MAP corpus; set BLOODMAP_CORPUS to enable")
        for path in paths:
            with self.subTest(path=path.name):
                level = read_map(path).to_level_ir()
                selected = sorted({0, len(level.sectors) // 2, len(level.sectors) - 1})
                fragment = extract_fragment(level, selected)
                restored = apply_fragment_in_place(level, fragment)
                self.assertEqual(restored.to_dict(), level.to_dict())
                self.assertEqual(encode_map(restored.to_disk_map()), path.read_bytes())


if __name__ == "__main__":
    unittest.main()
