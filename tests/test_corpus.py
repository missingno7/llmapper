from __future__ import annotations

import unittest
import os
from pathlib import Path

from bloodmap.analysis import channel_graph, geometry_view, validate_map
from bloodmap.format import encode_map, parse_map, read_map


MAPS = Path(os.environ.get("BLOODMAP_CORPUS", Path(__file__).resolve().parents[1] / "maps"))


class CorpusTests(unittest.TestCase):
    def test_every_available_map_is_v7_and_byte_exact_through_both_models(self):
        paths = sorted(MAPS.glob("*.MAP"))
        if not paths:
            self.skipTest("no local Blood MAP corpus; set BLOODMAP_CORPUS to enable")
        for path in paths:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                disk = read_map(path)
                self.assertEqual(disk.version, 0x0700)
                self.assertEqual(encode_map(disk), original)
                self.assertEqual(encode_map(disk.to_level_ir().to_disk_map()), original)
                reparsed = parse_map(encode_map(disk))
                self.assertEqual(reparsed, disk)
                self.assertFalse([d for d in validate_map(disk) if d.severity == "error"])

    def test_derived_views_cover_objects(self):
        path = MAPS / "E1M1.MAP"
        if not path.exists():
            self.skipTest("E1M1.MAP is not present in the local corpus")
        disk = read_map(path)
        geometry = geometry_view(disk)
        self.assertEqual(len(geometry), len(disk.sectors))
        self.assertEqual(sum(len(item["sprites"]) for item in geometry), len(disk.sprites))
        graph = channel_graph(disk)
        self.assertTrue(graph["channels"])


if __name__ == "__main__":
    unittest.main()
