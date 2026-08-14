from __future__ import annotations

import copy
import json
import os
import struct
import unittest
import zlib
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.format import (
    BloodMapError, MAIN_STRUCT, SECTOR_STRUCT, SPRITE_STRUCT, WALL_STRUCT,
    XSECTOR_SCHEMA, XSPRITE_SCHEMA, XWALL_SCHEMA, _pack_bits, _unpack_bits,
    crypt, encode_map, parse_map, read_map,
)
from bloodmap.model import LevelIR
from tests.helpers import synthetic_map


MAPS = Path(os.environ.get("BLOODMAP_CORPUS", Path(__file__).resolve().parents[1] / "maps"))


class PrimitiveTests(unittest.TestCase):
    def test_fixed_record_sizes(self):
        self.assertEqual(MAIN_STRUCT.size, 37)
        self.assertEqual(SECTOR_STRUCT.size, 40)
        self.assertEqual(WALL_STRUCT.size, 32)
        self.assertEqual(SPRITE_STRUCT.size, 44)

    def test_crypt_is_involution(self):
        data = bytes(range(256))
        for key in (0, 1, 0x7474614D, 4597 * 44):
            self.assertEqual(crypt(crypt(data, key), key), data)

    def test_packed_bitfields_roundtrip_boundaries(self):
        for kind, schema, size in (
            ("XSECTOR", XSECTOR_SCHEMA, 60),
            ("XWALL", XWALL_SCHEMA, 24),
            ("XSPRITE", XSPRITE_SCHEMA, 56),
        ):
            values = {}
            for name, width, signed in schema:
                values[name] = -(1 << (width - 1)) if signed else (1 << width) - 1
            known_size = sum(bits for _, bits, _ in schema) // 8
            raw = bytes((i * 37) & 0xFF for i in range(size))
            extra = _unpack_bits(raw, schema, kind)
            extra.fields.update(values)
            rebuilt = _pack_bits(extra, schema, size)
            reparsed = _unpack_bits(rebuilt, schema, kind)
            self.assertEqual(reparsed.fields, values)
            self.assertEqual(reparsed.opaque_tail, raw[known_size:])

    def test_crc_rejection(self):
        damaged = bytearray(encode_map(synthetic_map()))
        damaged[200] ^= 1
        with self.assertRaisesRegex(BloodMapError, "CRC mismatch"):
            parse_map(bytes(damaged))

    def test_validator_detects_broken_point2(self):
        disk = synthetic_map()
        disk.walls[0].point2 = len(disk.walls)
        errors = [d for d in validate_map(disk) if d.severity == "error"]
        self.assertTrue(any(d.code == "point2" for d in errors))


class MutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = MAPS / "E1M1.MAP"
        if cls.path.exists():
            cls.original = read_map(cls.path)
            cls.original_bytes = cls.path.read_bytes()
        else:
            cls.original = synthetic_map()
            cls.original_bytes = encode_map(cls.original)

    def _mutate_and_reparse(self, mutate):
        changed = copy.deepcopy(self.original)
        mutate(changed)
        rebuilt = encode_map(changed)
        self.assertNotEqual(rebuilt, self.original_bytes)
        reparsed = parse_map(rebuilt)
        self.assertEqual(reparsed.header, changed.header)
        self.assertEqual(reparsed.sky_offsets, changed.sky_offsets)
        self.assertEqual(reparsed.sectors, changed.sectors)
        self.assertEqual(reparsed.walls, changed.walls)
        self.assertEqual(reparsed.sprites, changed.sprites)
        self.assertFalse([d for d in validate_map(reparsed) if d.severity == "error"])
        return reparsed

    def test_wall_texture_mutation(self):
        old = self.original.walls[0].picnum
        result = self._mutate_and_reparse(lambda d: setattr(d.walls[0], "picnum", old + 1))
        self.assertEqual(result.walls[0].picnum, old + 1)

    def test_sprite_move_mutation(self):
        old = self.original.sprites[0].x
        result = self._mutate_and_reparse(lambda d: setattr(d.sprites[0], "x", old + 64))
        self.assertEqual(result.sprites[0].x, old + 64)

    def test_player_start_mutation(self):
        old = self.original.header["start_x"]
        result = self._mutate_and_reparse(lambda d: d.header.__setitem__("start_x", old + 128))
        self.assertEqual(result.header["start_x"], old + 128)

    def test_sector_shade_mutation(self):
        old = self.original.sectors[0].floor_shade
        new = old + 1 if old < 127 else old - 1
        result = self._mutate_and_reparse(lambda d: setattr(d.sectors[0], "floor_shade", new))
        self.assertEqual(result.sectors[0].floor_shade, new)

    def test_extended_field_mutation(self):
        index = next(i for i, value in enumerate(self.original.sprites) if value.extra is not None)
        old = self.original.sprites[index].extra.fields["data_1"]
        new = old + 1 if old < 32767 else old - 1
        result = self._mutate_and_reparse(lambda d: d.sprites[index].extra.fields.__setitem__("data_1", new))
        self.assertEqual(result.sprites[index].extra.fields["data_1"], new)

    def test_ir_json_roundtrip_and_mutation(self):
        ir = self.original.to_level_ir()
        text = json.dumps(ir.to_dict(), sort_keys=True)
        rebuilt_ir = LevelIR.from_dict(json.loads(text))
        self.assertEqual(encode_map(rebuilt_ir.to_disk_map()), self.original_bytes)
        rebuilt_ir.walls[0]["fields"]["picnum"] += 1
        parsed = parse_map(encode_map(rebuilt_ir.to_disk_map()))
        self.assertEqual(parsed.walls[0].picnum, self.original.walls[0].picnum + 1)

    def test_safe_transformations(self):
        ir = self.original.to_level_ir()
        x, y = ir.player_start["x"], ir.player_start["y"]
        ir.translate(4096, -2048, 256)
        ir.rotate_quarter_turns(1, 100, -200)
        parsed = parse_map(encode_map(ir.to_disk_map()))
        self.assertEqual((parsed.header["start_x"], parsed.header["start_y"]),
                         (-(y - 2048 + 200) + 100, (x + 4096 - 100) - 200))
        self.assertFalse([d for d in validate_map(parsed) if d.severity == "error"])


if __name__ == "__main__":
    unittest.main()
