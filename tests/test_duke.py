from __future__ import annotations

import copy
import os
import struct
import tempfile
import unittest
from pathlib import Path

from bloodmap.build_ir import BuildIR
from bloodmap.cli import main
from bloodmap.duke import DukeMapError, encode_duke_map, parse_duke_map, read_duke_map


MAPS = Path(os.environ.get("DUKEMAP_CORPUS", Path(__file__).resolve().parents[1] / "maps" / "duke3d"))


class DukeFormatTests(unittest.TestCase):
    def test_every_available_duke_map_is_byte_exact_through_disk_and_build_ir(self):
        paths = sorted(MAPS.glob("*.MAP"))
        if not paths:
            self.skipTest("no local Duke3D MAP corpus; set DUKEMAP_CORPUS to enable")
        for path in paths:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                disk = read_duke_map(path)
                self.assertEqual(disk.version, 7)
                self.assertEqual(encode_duke_map(disk), original)
                reparsed = parse_duke_map(encode_duke_map(disk))
                self.assertEqual(reparsed, disk)
                build = disk.to_build_ir()
                self.assertEqual(encode_duke_map(build.to_native_disk_map()), original)
                restored = BuildIR.from_dict(build.to_dict())
                self.assertEqual(encode_duke_map(restored.to_native_disk_map()), original)
                self.assertFalse([item for item in build.validate() if item.severity == "error"])

    def test_duke_writer_is_genuine_and_mutations_reparse(self):
        path = MAPS / "E1L1.MAP"
        if not path.exists():
            self.skipTest("E1L1.MAP is not present in the local Duke corpus")
        original = path.read_bytes()
        disk = read_duke_map(path)
        changed = copy.deepcopy(disk)
        changed.header["start_x"] += 128
        changed.walls[0].fields["shade"] = max(-128, changed.walls[0].shade - 1)
        encoded = encode_duke_map(changed)
        self.assertNotEqual(encoded, original)
        reparsed = parse_duke_map(encoded)
        self.assertEqual(reparsed.header["start_x"], disk.header["start_x"] + 128)
        self.assertEqual(reparsed.walls[0].shade, changed.walls[0].shade)
        self.assertFalse([item for item in reparsed.to_build_ir().validate() if item.severity == "error"])

    def test_build_ir_geometry_transform_reaches_duke_writer(self):
        path = MAPS / "E1L1.MAP"
        if not path.exists():
            self.skipTest("E1L1.MAP is not present in the local Duke corpus")
        disk = read_duke_map(path)
        build = disk.to_build_ir()
        old_start = dict(build.player_start)
        old_wall = dict(build.walls[0]["fields"])
        build.translate(1024, -2048, 4096)
        reparsed = parse_duke_map(encode_duke_map(build.to_native_disk_map()))
        self.assertEqual(reparsed.header["start_x"], old_start["x"] + 1024)
        self.assertEqual(reparsed.header["start_y"], old_start["y"] - 2048)
        self.assertEqual(reparsed.walls[0].x, old_wall["x"] + 1024)
        self.assertEqual(reparsed.walls[0].y, old_wall["y"] - 2048)

    def test_parser_rejects_unsupported_or_truncated_maps_and_preserves_tail(self):
        with self.assertRaisesRegex(DukeMapError, "too short"):
            parse_duke_map(b"\0" * 8)
        with self.assertRaisesRegex(DukeMapError, "unsupported"):
            parse_duke_map(struct.pack("<i", 6) + b"\0" * 22)
        path = MAPS / "E1L1.MAP"
        if not path.exists():
            self.skipTest("E1L1.MAP is not present in the local Duke corpus")
        tailed = path.read_bytes() + b"LLMAPPER-TAIL"
        self.assertEqual(encode_duke_map(parse_duke_map(tailed)), tailed)

    def test_build_ir_cli_dump_and_rebuild_is_byte_exact(self):
        path = MAPS / "E1L1.MAP"
        if not path.exists():
            self.skipTest("E1L1.MAP is not present in the local Duke corpus")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document, rebuilt = root / "E1L1.build.json", root / "E1L1.MAP"
            self.assertEqual(main(["dump-build", str(path), "-o", str(document)]), 0)
            self.assertEqual(main(["build-build", str(document), "-o", str(rebuilt)]), 0)
            self.assertEqual(rebuilt.read_bytes(), path.read_bytes())


if __name__ == "__main__":
    unittest.main()
