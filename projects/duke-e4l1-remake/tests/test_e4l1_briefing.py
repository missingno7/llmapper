"""The briefing device reaches its delayed explosion and collapse receivers after native encoding."""

import importlib.util
from pathlib import Path
import unittest

from bloodmap.construction import LevelBuilder
from bloodmap.format import encode_map, parse_map
from bloodmap.model import record_fields, record_extra
from bloodmap.posed import chain_of, posed
from bloodmap.wiring import chains

SCRIPT = Path(__file__).resolve().parents[1] / "briefing.py"
SPEC = importlib.util.spec_from_file_location("remake_briefing", SCRIPT)
briefing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(briefing)


class BriefingCircuitTests(unittest.TestCase):
    def fixture(self):
        builder = LevelBuilder()
        for i in range(4):
            x = i * 8192
            builder.add_sector([(x, 0), (x + 4096, 0), (x + 4096, 4096), (x, 4096)],
                               floor_z=0, ceiling_z=-32768)
            if i:
                record_fields(builder.level.sectors[i])["type"] = 600
                builder.set_behavior("sector", i, off_floor_z=0, on_floor_z=4096 * i,
                                     off_ceiling_z=-32768, on_ceiling_z=-32768,
                                     busy_time_a=8, busy_time_b=8)
        builder.set_player_start(sector=0, x=512, y=512, z=-8192, angle=0)
        for i, fuse in enumerate((8, 6, 3)):
            trap = builder.add_sprite(sector=0, x=1024 + 256*i, y=1024, z=0,
                                      type=459, status=11, picnum=908, cstat=32896)
            builder.set_behavior("sprite", trap, wait_time=fuse)
        disk = builder.level.to_disk_map()
        circuit, layout = briefing.declare(disk, wall_id=0, moving=(1, 2, 3), exploders=(0, 1, 2))
        for key, spec in layout.regions.items():
            if spec.sector_behavior:
                builder.set_behavior("sector", int(key), **spec.sector_behavior)
        for i in range(3):
            spec = next(p for p in layout.placements if p.placement_id == f"existing-{i}")
            builder.set_behavior("sprite", i, **spec.behavior)
        added = {}
        for name in ("briefing-arm-delay", "briefing-collapse-delay"):
            added[name] = builder.add_sprite(sector=0, x=512, y=512, z=-16000,
                                             type=0, status=0, picnum=0, cstat=32896)
            spec = next(p for p in layout.placements if p.placement_id == name)
            builder.set_behavior("sprite", added[name], **spec.behavior)
        builder.set_behavior("wall", 0, **layout.wired_walls[0])
        return parse_map(encode_map(builder.level.to_disk_map())), circuit, added

    def test_use_reaches_all_retained_receivers_and_has_no_dead_relay(self):
        disk, circuit, added = self.fixture()
        report = circuit.read_back(briefing.compiled(disk, added), disk)
        self.assertTrue(report["agrees"], report)
        chain = chain_of(chains(disk), "wall 0")
        self.assertFalse(chain["dead_relays"])
        reached = {s["to"] for s in chain["steps"]}
        self.assertTrue({"sprite 0", "sprite 1", "sprite 2", "sector 1", "sector 2", "sector 3"} <= reached)
        self.assertEqual([record_extra(disk.sprites[i])["wait_time"] for i in range(3)], [8, 6, 3])
        self.assertEqual(record_extra(disk.walls[0])["trigger_once"], 1)

    def test_posed_endpoints_follow_the_return_edge_of_both_delay_relays(self):
        disk, _, added = self.fixture()
        result, report = posed(disk, chain_of(chains(disk), "wall 0"))
        self.assertEqual([record_fields(result.sectors[i])["floor_z"] for i in (1, 2, 3)],
                         [4096, 8192, 12288])
        for name, wait in (("briefing-arm-delay", 27), ("briefing-collapse-delay", 30)):
            extra = record_extra(disk.sprites[added[name]])
            self.assertEqual((extra["trigger_on"], extra["trigger_off"], extra["wait_time"]),
                             (0, 1, wait))
        self.assertTrue(any("after 3 s" in row.get("arrives", "") for row in report["objects"]))

    def test_mixed_receiver_channels_are_refused(self):
        disk, circuit, _ = self.fixture()
        builder = LevelBuilder(disk.to_level_ir())
        builder.set_behavior("sprite", 0, rx_id=circuit.wires[0].channel)
        with self.assertRaisesRegex(ValueError, "receivers disagree"):
            briefing.declare(builder.level.to_disk_map(), wall_id=0,
                              moving=(1, 2, 3), exploders=(0, 1, 2))


if __name__ == "__main__":
    unittest.main()
