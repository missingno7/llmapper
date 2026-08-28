from __future__ import annotations

import os
import unittest
from collections import Counter
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.differential import compare_e3l1_pair
from bloodmap.duke import read_duke_map
from bloodmap.duke_semantics import classify_se7_groups
from bloodmap.e3l11 import ChannelAllocator, convert_playable_duke_to_blood
from bloodmap.format import encode_map, parse_map


ROOT = Path(__file__).resolve().parents[1]
BLOOD_MAPS = Path(os.environ.get("BLOODMAP_CORPUS", ROOT / "maps" / "blood"))
DUKE_MAPS = Path(os.environ.get("DUKEMAP_CORPUS", ROOT / "maps" / "duke3d"))


class ChannelAllocatorTests(unittest.TestCase):
    def test_small_tags_keep_the_e3l11_offset_encoding(self):
        alloc = ChannelAllocator()
        self.assertEqual(alloc.allocate(58), 158)
        self.assertEqual(alloc.allocate(25), 125)
        self.assertEqual(alloc.allocate(58), 158)

    def test_overflow_tags_take_free_user_channels_and_skip_the_exit(self):
        alloc = ChannelAllocator()
        alloc.allocate(25)
        first = alloc.allocate(3313)
        second = alloc.allocate(8808)
        self.assertTrue(100 <= first <= 1023)
        self.assertNotEqual(first, 4)
        self.assertNotEqual(first, 125)
        self.assertNotEqual(second, first)
        self.assertEqual(alloc.allocate(3313), first)


class E3L3PlayableConversionTests(unittest.TestCase):
    def _paths(self):
        duke = DUKE_MAPS / "E3L3.MAP"
        blood = BLOOD_MAPS / "DNE3L3.map"
        if not duke.exists():
            self.skipTest("E3L3 is not present in the local Duke corpus")
        return duke, blood if blood.exists() else None

    def test_e3l3_dne3l3_is_a_reimagination_not_a_geometry_match(self):
        duke, blood = self._paths()
        if blood is None:
            self.skipTest("DNE3L3 is not present in the local Blood corpus")
        report = compare_e3l1_pair(duke, blood)
        selected = report["normalization"]["xy_scale_duke_to_blood"]["selected"]
        self.assertEqual((selected["numerator"], selected["denominator"]), (3, 2))
        self.assertEqual(report["pair_role"], "reimagination")
        self.assertEqual(report["geometry"]["unique_exact_sector_correspondences"], 0)
        self.assertEqual(report["counts"]["duke"]["sectors"], report["counts"]["blood"]["sectors"])

    def test_playable_conversion_recovers_water_swinging_doors_and_access_switches(self):
        duke_path, _blood = self._paths()
        groups = classify_se7_groups(read_duke_map(duke_path))
        self.assertTrue(all(group["kind"] == "water_link" for group in groups.values()))
        self.assertEqual(len(groups), 25)

        disk, report = convert_playable_duke_to_blood(read_duke_map(duke_path))
        reparsed = parse_map(encode_map(disk))
        self.assertEqual((len(reparsed.sectors), len(reparsed.walls)), (262, 1804))
        self.assertFalse([item for item in validate_map(reparsed) if item.severity == "error"])

        sector_types = Counter(sector.type for sector in reparsed.sectors)
        sprite_types = Counter(sprite.type for sprite in reparsed.sprites)
        self.assertEqual(sprite_types[9], 25)
        self.assertEqual(sprite_types[10], 25)
        self.assertEqual(sector_types[617], 2)
        # E3L3's single SE20 is a stretch bridge, and SE20 is the one Duke
        # moving sector that never calls A_MoveSector: it drags the two walls
        # nearest the effector and leaves the rest of the sector alone. That is
        # Blood's kSectorSlideMarked (614), not the whole-sector slide (616),
        # which would carry the bridge away instead of extending it.
        self.assertEqual(sector_types[614], 1)
        self.assertEqual(sector_types[616], 0)
        self.assertEqual(sprite_types[408], 1)
        self.assertEqual(report["mechanisms"]["counts"]["swinging-door"], 2)
        self.assertEqual(report["mechanisms"]["counts"]["stretch-bridge"], 1)
        self.assertEqual(report["mechanisms"]["counts"]["door-autoclose"], 1)
        self.assertGreaterEqual(report["entities"]["translated_counts"].get("equivalent:access-switch", 0), 6)
        self.assertNotIn(11, report["mechanisms"]["unsupported_sector_effector_lotags"])
        self.assertNotIn(10, report["mechanisms"]["unsupported_sector_effector_lotags"])
        self.assertTrue(report["overall"]["static_progression"]["all_exits_reachable"])
        transmitters = report["mechanisms"]["channel_audit"]["transmitters"]
        self.assertIn(4, transmitters)
        self.assertTrue(all(channel == 4 or 100 <= channel <= 1023 for channel in transmitters))
        exits = [sprite for sprite in reparsed.sprites if sprite.extra and sprite.extra.tx_id == 4]
        self.assertEqual(len(exits), 2)


if __name__ == "__main__":
    unittest.main()
