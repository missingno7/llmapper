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
        self.assertEqual(sector_types[600], 10)  # doors, elevator, SE31/SE32 motions
        self.assertEqual(sector_types[604], 4)   # two bidirectional Duke teleporter pairs
        self.assertEqual(sector_types[616], 1)
        self.assertEqual(sector_types[617], 5)

        sprite_types = Counter(sprite.type for sprite in reparsed.sprites)
        self.assertEqual(sprite_types[9], 20)
        self.assertEqual(sprite_types[10], 20)
        self.assertEqual(sprite_types[8], 4)
        self.assertEqual(sprite_types[459], 6)  # hidden exploders linked to CRACK1..4 groups
        self.assertEqual(sprite_types[41], 2)
        self.assertGreater(sprite_types[201] + sprite_types[202], 40)
        exits = [sprite for sprite in reparsed.sprites if sprite.extra and sprite.extra.tx_id == 4]
        self.assertEqual(len(exits), 1)

        self.assertEqual(reparsed.sectors[84].extra.rx_id, 158)
        self.assertEqual(reparsed.sectors[111].extra.rx_id, 125)
        self.assertEqual(reparsed.sectors[159].extra.rx_id, 141)
        for sector_id in (162, 220, 221, 222, 223):
            self.assertEqual(reparsed.sectors[sector_id].extra.rx_id, 149)
            self.assertEqual(reparsed.sectors[sector_id].extra.trigger_push, 0)
        self.assertTrue(all(count == 2 for count in report["mechanisms"]["water_link_ids"].values()))
        self.assertNotIn(31, report["mechanisms"]["unsupported_sector_effector_lotags"])
        self.assertNotIn(32, report["mechanisms"]["unsupported_sector_effector_lotags"])
        self.assertEqual(report["mechanisms"]["counts"]["destructible-wall"], 6)
        self.assertEqual(report["mechanisms"]["counts"]["linked-explosion"], 6)
        self.assertEqual(report["mechanisms"]["counts"]["switchable-light-pulse"], 32)
        self.assertEqual(report["mechanisms"]["channel_audit"]["dangling_user_transmit_channels"], [139, 159, 160, 161])
        gib_walls = [wall for wall in reparsed.walls if wall.type == 511]
        self.assertEqual(len(gib_walls), 6)
        self.assertTrue(all(wall.extra and wall.extra.trigger_vector for wall in gib_walls))


if __name__ == "__main__":
    unittest.main()
