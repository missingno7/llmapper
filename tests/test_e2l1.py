from __future__ import annotations

import os
import unittest
from collections import Counter
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.differential import compare_e3l1_pair
from bloodmap.duke import read_duke_map
from bloodmap.duke_semantics import analyze_duke_mechanisms
from bloodmap.e3l11 import convert_playable_duke_to_blood
from bloodmap.format import encode_map, parse_map, read_map
from bloodmap.style import extract_visual_style, load_visual_style
from tests.helpers import corpus_map


ROOT = Path(__file__).resolve().parents[1]
BLOOD_MAPS = Path(os.environ.get("BLOODMAP_CORPUS", ROOT / "maps" / "blood"))
DUKE_MAPS = Path(os.environ.get("DUKEMAP_CORPUS", ROOT / "maps" / "duke3d"))
DUKE_ART = ROOT / "reference" / "duke3d"
BLOOD_ART = ROOT / "reference" / "blood"


class E2L1StyleReferenceTests(unittest.TestCase):
    def _paths(self):
        duke = DUKE_MAPS / "E2L1.MAP"
        blood = corpus_map("DWE2M3.MAP")
        if not duke.exists():
            self.skipTest("E2L1 is not present in the local Duke corpus")
        if not blood.exists():
            self.skipTest("DWE2M3 is not present in the local Blood corpus")
        return duke, blood

    def test_e2l1_dwe2m3_is_a_style_pair_not_a_geometry_match(self):
        duke, blood = self._paths()
        report = compare_e3l1_pair(duke, blood)
        self.assertEqual(report["pair_role"], "reimagination")
        self.assertEqual(report["geometry"]["unique_exact_sector_correspondences"], 0)
        self.assertNotEqual(report["counts"]["duke"]["sectors"], report["counts"]["blood"]["sectors"])

    def test_dwe2m3_style_is_dark_indoor_tech_with_header_fog(self):
        _duke, blood = self._paths()
        style = load_visual_style(str(blood))
        self.assertEqual(style["header"]["visibility"], 208)
        self.assertEqual(style["header"]["sky_bits"], 4)
        self.assertEqual(style["parallax_ceilings"], 0)
        self.assertGreater(style["shades"]["wall"]["mean"], 30)
        self.assertIn("1012", style["surface"]["wall"])
        self.assertGreater(style["candidates"]["wall"][1012], 500)


class E2L1PlayableConversionTests(unittest.TestCase):
    def _paths(self):
        duke = DUKE_MAPS / "E2L1.MAP"
        style = corpus_map("DWE2M3.MAP")
        if not duke.exists():
            self.skipTest("E2L1 is not present in the local Duke corpus")
        if not style.exists():
            self.skipTest("DWE2M3 is not present in the local Blood corpus")
        return duke, style

    def _convert(self, with_art: bool = False):
        duke, style = self._paths()
        kwargs: dict = {"style_map": style}
        if with_art:
            if not (DUKE_ART / "TILES000.ART").exists() or not list(BLOOD_ART.glob("[Tt][Ii][Ll][Ee][Ss]*.[Aa][Rr][Tt]")):
                self.skipTest("local ART sets are not present")
            kwargs.update(duke_art=DUKE_ART, blood_art=BLOOD_ART, blood_maps=BLOOD_MAPS)
        return convert_playable_duke_to_blood(read_duke_map(duke), **kwargs)

    def test_playable_conversion_lowers_warp_elevators_platforms_and_splitting_doors(self):
        duke, _style = self._paths()
        inventory = analyze_duke_mechanisms(read_duke_map(duke))
        self.assertEqual(inventory["counts_by_effector_lotag"][17], 2)
        self.assertEqual(inventory["counts_by_effector_lotag"][6], 1)

        disk, report = self._convert(with_art=False)
        reparsed = parse_map(encode_map(disk))
        self.assertEqual((len(reparsed.sectors), len(reparsed.walls)), (357, 2397))
        self.assertFalse([item for item in validate_map(reparsed) if item.severity == "error"])

        sector_types = Counter(sector.type for sector in reparsed.sectors)
        sprite_types = Counter(sprite.type for sprite in reparsed.sprites)
        self.assertEqual(sector_types[604], 6)
        self.assertGreaterEqual(sector_types[600], 21)
        self.assertEqual(report["mechanisms"]["counts"]["warp-elevator"], 2)
        self.assertEqual(report["mechanisms"]["counts"]["splitting-door"], 3)
        self.assertEqual(report["mechanisms"]["counts"]["platform"], 3)
        self.assertEqual(sprite_types[9], 2)
        self.assertEqual(sprite_types[10], 2)
        # E2L1 carries both kinds of Duke explosive: 4 authored at xrepeat 40
        # and 3 at xrepeat 4. Duke spawns anything at 8 or less invisible and
        # zero-sized, so only the visible 4 get a TNT barrel to shoot, while all
        # 7 become chain exploders on their hitag channel.
        self.assertEqual(sprite_types[400], 4)
        self.assertEqual(report["mechanisms"]["counts"]["chain-exploder"], 7)
        self.assertEqual(report["mechanisms"]["counts"]["visible-explosive"], 4)
        self.assertGreaterEqual(
            report["entities"]["translated_counts"].get("approximation:Liztroop ducking->Tommy cultist", 0),
            7,
        )
        self.assertNotIn(17, report["mechanisms"]["unsupported_sector_effector_lotags"])
        self.assertIn(6, report["mechanisms"]["unsupported_sector_effector_lotags"])
        self.assertTrue(report["overall"]["static_progression"]["all_exits_reachable"])
        self.assertEqual(reparsed.header["visibility"], 208)
        self.assertEqual(reparsed.header["sky_bits"], 4)
        exits = [sprite for sprite in reparsed.sprites if sprite.extra and sprite.extra.tx_id == 4]
        self.assertEqual(len(exits), 1)

        push_motion = [
            sector for sector in reparsed.sectors
            if sector.type == 600 and sector.extra and not sector.extra.rx_id
        ]
        rx_motion = [
            sector for sector in reparsed.sectors
            if sector.type == 600 and sector.extra and sector.extra.rx_id
        ]
        self.assertTrue(push_motion)
        self.assertTrue(all(
            sector.extra.trigger_push and sector.extra.trigger_wall_push
            for sector in push_motion
        ))
        self.assertTrue(all(
            not sector.extra.trigger_push and not sector.extra.trigger_wall_push
            for sector in rx_motion
        ))
        teleporters = [sector for sector in reparsed.sectors if sector.type == 604]
        self.assertEqual(len(teleporters), 6)
        self.assertTrue(all(
            sector.extra and sector.extra.trigger_enter and sector.extra.dude_lockout
            and sector.extra.data == 0
            for sector in teleporters
        ))
        autoclose = [
            record for record in report["mechanisms"]["records"]
            if record["kind"] == "door-autoclose"
        ]
        self.assertEqual(len(autoclose), 9)
        for record in autoclose:
            extra = reparsed.sectors[record["source_sector"]].extra
            self.assertEqual(extra.wait_time_a, record["wait_time"])
            self.assertEqual(extra.retrigger_a, 1)
            self.assertEqual(extra.wait_time_b, 0)
        # ST20 sector 115 neighbors ST2; ST20 sector 42 only neighbors ST1 (surface).
        self.assertEqual(reparsed.sectors[115].type, 600)
        self.assertTrue(reparsed.sectors[115].extra.underwater)
        self.assertEqual(reparsed.sectors[42].type, 600)
        self.assertFalse(reparsed.sectors[42].extra.underwater)

    def test_style_map_constrains_indoor_tiles_to_dwe2m3_vocabulary(self):
        disk, report = self._convert(with_art=True)
        style = extract_visual_style(read_map(self._paths()[1]))
        wall_vocab = set(style["candidates"]["wall"])
        ceiling_vocab = set(style["candidates"]["ceiling"])
        floor_vocab = set(style["candidates"]["floor"])
        converted_walls = {wall.picnum for wall in disk.walls if wall.picnum}
        converted_floors = {sector.floor_picnum for sector in disk.sectors if sector.floor_picnum != 2915}
        indoor_ceilings = {
            sector.ceiling_picnum for sector in disk.sectors
            if sector.ceiling_picnum
            and not (sector.ceiling_stat & 1)
            and sector.ceiling_picnum != 2915
        }
        self.assertTrue(converted_walls <= wall_vocab)
        self.assertTrue(converted_floors <= floor_vocab)
        self.assertTrue(indoor_ceilings <= ceiling_vocab)
        self.assertIn("style+visual-match", report["materials"]["decisions"])
        self.assertEqual(report["style"]["visibility"], 208)
