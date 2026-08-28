from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.duke import read_duke_map
from bloodmap.e3l11 import convert_e3l11_to_blood
from bloodmap.format import encode_map, parse_map


ROOT = Path(__file__).resolve().parents[1]


class E3L11PlayableConversionTests(unittest.TestCase):
    def _convert(self):
        source = ROOT / "maps" / "duke3d" / "E3L11.MAP"
        if not source.exists():
            self.skipTest("E3L11 is not present in the local Duke corpus")
        return convert_e3l11_to_blood(read_duke_map(source))

    def test_core_geometry_mechanisms_and_population_are_native_blood_records(self):
        disk, report = self._convert()
        reparsed = parse_map(encode_map(disk))
        self.assertEqual((len(reparsed.sectors), len(reparsed.walls)), (253, 1600))
        self.assertFalse([item for item in validate_map(reparsed) if item.severity == "error"])

        sector_types = Counter(sector.type for sector in reparsed.sectors)
        self.assertEqual(sector_types[600], 21)  # doors, elevator, SE31/SE32, plus 11 SE13 holes
        self.assertEqual(sector_types[604], 0)   # E3L11 has no floor-standing SE7 teleporters
        self.assertEqual(sector_types[616], 1)
        self.assertEqual(sector_types[617], 5)

        sprite_types = Counter(sprite.type for sprite in reparsed.sprites)
        self.assertEqual(sprite_types[9], 20)
        self.assertEqual(sprite_types[10], 20)
        self.assertEqual(sprite_types[8], 0)
        self.assertEqual(sprite_types[11], 2)  # congruent air-hatch up-stacks
        self.assertEqual(sprite_types[12], 2)
        self.assertEqual(sprite_types[408], 6)  # shootable Blood wall cracks
        # 6 SE13 hole exploders plus the 61 SEENINE chain nodes. Every one of
        # E3L11's SEENINEs is authored at xrepeat 4, which Duke spawns invisible
        # and zero-sized, so none of them becomes a visible TNT barrel.
        self.assertEqual(sprite_types[459], 67)
        self.assertEqual(sprite_types[400], 0)
        self.assertEqual(sprite_types[18], 4)   # RESPAWN -> kMarkerDudeSpawn
        self.assertEqual(sprite_types[1], 1)    # exactly one kMarkerSPStart
        # No dead combination switches: a kSwitchCombo with data1/2/3 all zero
        # can never satisfy data1 == data2 and never fires its channel.
        self.assertEqual(sprite_types[22], 0)
        self.assertEqual(sprite_types[41], 2)
        self.assertGreater(sprite_types[201] + sprite_types[202], 40)
        exits = [sprite for sprite in reparsed.sprites if sprite.extra and sprite.extra.tx_id == 4]
        self.assertEqual(len(exits), 1)

        self.assertEqual(reparsed.sectors[84].extra.rx_id, 158)
        self.assertEqual(reparsed.sectors[111].extra.rx_id, 125)
        self.assertEqual(reparsed.sectors[159].extra.rx_id, 141)
        self.assertEqual(reparsed.sectors[83].extra.busy_time_a, 5)   # GPSPEED 1024
        # Sliding doors and rotate bridges now take their duration from the
        # engine rather than from a fitted curve. The SE15 leaf in sector 159
        # runs sector.extra >> 3 == 56 ticks at 30 Hz, which is 19 tenths of a
        # second; every ST30 bridge runs actors.cpp's fixed 64, which is 21.
        self.assertEqual(reparsed.sectors[159].extra.busy_time_a, 19)  # GPSPEED 450
        self.assertEqual(reparsed.sectors[220].extra.busy_time_a, 21)  # GPSPEED 128
        for sector_id in (162, 220, 221, 222, 223):
            self.assertEqual(reparsed.sectors[sector_id].extra.rx_id, 149)
            self.assertEqual(reparsed.sectors[sector_id].extra.trigger_push, 0)
            self.assertEqual(reparsed.sectors[sector_id].extra.trigger_wall_push, 0)
        push_motion = [
            sector for sector in reparsed.sectors
            if sector.type == 600 and sector.extra and not sector.extra.rx_id
        ]
        self.assertTrue(push_motion)
        self.assertTrue(all(
            sector.extra.trigger_push and sector.extra.trigger_wall_push
            for sector in push_motion
        ))
        self.assertTrue(all(count == 2 for count in report["mechanisms"]["water_link_ids"].values()))
        self.assertEqual(report["mechanisms"]["hatch_link_ids"], {1: 2, 19: 2})
        self.assertNotIn(31, report["mechanisms"]["unsupported_sector_effector_lotags"])
        self.assertNotIn(32, report["mechanisms"]["unsupported_sector_effector_lotags"])
        self.assertEqual(report["mechanisms"]["counts"]["destructible-wall"], 6)
        self.assertEqual(report["mechanisms"]["counts"]["linked-explosion"], 6)
        self.assertEqual(report["mechanisms"]["counts"]["explosive-z-sector"], 11)
        self.assertEqual(report["mechanisms"]["counts"]["hatch-marker"], 4)
        self.assertEqual(report["mechanisms"]["counts"]["switchable-light-pulse"], 32)
        # 139 now reaches the SEENINE cascade and 160/161 reach dude-spawn
        # markers. 159 stays: it is a lone Duke touchplate wired to nothing in
        # E3L11 itself, so a converted map that dropped it would be inventing a
        # receiver the original never had.
        self.assertEqual(report["mechanisms"]["channel_audit"]["dangling_user_transmit_channels"], [159])
        self.assertEqual(report["mechanisms"]["counts"]["chain-exploder"], 61)
        self.assertEqual(report["mechanisms"]["counts"]["dude-spawn"], 4)
        self.assertFalse([wall for wall in reparsed.walls if wall.type == 511])
        exploders = [sprite for sprite in reparsed.sprites if sprite.type == 459]
        self.assertTrue(all(sprite.status == 11 for sprite in exploders))
        self.assertTrue(all(sprite.extra and sprite.extra.wait_time >= 1 for sprite in exploders))
        cracks = [sprite for sprite in reparsed.sprites if sprite.type == 408]
        self.assertTrue(all(sprite.picnum == 1127 and sprite.status == 4 for sprite in cracks))
        self.assertTrue(all(sprite.cstat & 256 for sprite in cracks))
        self.assertTrue(all(
            sprite.extra and sprite.extra.tx_id and sprite.extra.command == 1
            and sprite.extra.trigger_vector and sprite.extra.trigger_impact
            for sprite in cracks
        ))
        # DNE3L11 marks every Duke ST2 underwater, including SE13 holes 140/141.
        self.assertEqual(report["mechanisms"]["counts"]["underwater-sector"], 22)
        self.assertTrue(reparsed.sectors[140].extra.underwater)
        self.assertTrue(reparsed.sectors[141].extra.underwater)
        self.assertEqual(reparsed.sectors[140].type, 600)
        self.assertEqual(reparsed.sectors[141].type, 600)

        # SE13 ang 512 in sector 201 snaps only the floor to the effector Z.
        self.assertEqual(reparsed.sectors[201].type, 600)
        self.assertLess(reparsed.sectors[201].floor_z, reparsed.sectors[201].extra.on_floor_z)
        self.assertEqual(reparsed.sectors[201].ceiling_z, reparsed.sectors[201].extra.on_ceiling_z)
        # Dual-surface SE13 starts as a collapsed slit.
        self.assertEqual(reparsed.sectors[214].ceiling_z, reparsed.sectors[214].floor_z)

        hatch_pairs = {}
        for sprite in reparsed.sprites:
            if sprite.type in {11, 12} and sprite.extra:
                hatch_pairs.setdefault(sprite.extra.data_1, set()).add(sprite.type)
        self.assertEqual(hatch_pairs, {1: {11, 12}, 19: {11, 12}})


class DNE3L11PartialConversionTests(unittest.TestCase):
    def test_dne3l11_is_a_partial_3_2_water_pass_of_e3l11(self):
        duke = ROOT / "maps" / "duke3d" / "E3L11.MAP"
        blood = ROOT / "maps" / "blood" / "DNE3L11.map"
        if not duke.exists() or not blood.exists():
            self.skipTest("E3L11/DNE3L11 pair is not present")
        from bloodmap.differential import compare_e3l1_pair, infer_xy_scale
        from bloodmap.duke import read_duke_map
        from bloodmap.format import read_map

        duke_map, blood_map = read_duke_map(duke), read_map(blood)
        scale = infer_xy_scale(duke_map, blood_map)["selected"]
        self.assertEqual((scale["numerator"], scale["denominator"]), (3, 2))
        report = compare_e3l1_pair(duke, blood)
        self.assertEqual(report["pair_role"], "reimagination")
        st2 = [index for index, sector in enumerate(duke_map.sectors) if (sector.lotag & 0x3FFF) == 2]
        underwater = [index for index, sector in enumerate(blood_map.sectors) if sector.extra and sector.extra.underwater]
        self.assertEqual(underwater, st2)
        self.assertEqual(len(underwater), 22)
        self.assertTrue(all(blood_map.sectors[index].type == 0 for index in underwater))
        self.assertEqual(sum(sprite.type == 408 for sprite in blood_map.sprites), 0)


if __name__ == "__main__":
    unittest.main()
