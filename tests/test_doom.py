from __future__ import annotations

import copy
import os
import unittest
from pathlib import Path

from bloodmap.doom import (
    DoomError, doom_corpus_report, encode_doom_map_lumps, encode_wad, new_wad,
    parse_wad, read_wad, validate_doom_map, wad_map,
)
from bloodmap.doom_fixtures import fixture_basic_room


DOOM_WAD = Path(os.environ.get("DOOM_IWAD", Path(__file__).resolve().parents[1] / "maps" / "doom" / "doom.wad"))
DOOM2_WAD = Path(os.environ.get("DOOM2_IWAD", Path(__file__).resolve().parents[1] / "maps" / "doom" / "DOOM2.WAD"))
if not DOOM2_WAD.exists():
    DOOM2_WAD = DOOM2_WAD.with_name("doom2.wad")


def _load(path: Path):
    if not path.exists():
        return None
    return read_wad(path)


class DoomNativeTests(unittest.TestCase):
    def test_synthetic_map_lumps_roundtrip_and_mutation_rebuilds_from_fields(self):
        _semantic, doom, _blood = fixture_basic_room()
        wad = new_wad(maps=[doom])
        original = encode_wad(wad)
        reparsed = parse_wad(original)
        level = wad_map(reparsed, "MAP01")
        self.assertEqual(level.format, "doom")
        self.assertEqual(len(level.sectors), 3)
        self.assertEqual(encode_doom_map_lumps(level)["THINGS"], encode_doom_map_lumps(doom)["THINGS"])
        self.assertFalse([item for item in validate_doom_map(level) if item["severity"] == "error"])

        mutated = copy.deepcopy(level)
        mutated.vertices[0].x += 8
        mutated.things[0].angle = 90
        rebuilt = encode_wad(new_wad(maps=[mutated]))
        self.assertNotEqual(rebuilt, original)
        again = wad_map(parse_wad(rebuilt), "MAP01")
        self.assertEqual(again.vertices[0].x, doom.vertices[0].x + 8)
        self.assertEqual(again.things[0].angle, 90)
        # Writer reconstructed VERTEXES from fields, not from stashed bytes.
        self.assertNotEqual(encode_doom_map_lumps(again)["VERTEXES"], encode_doom_map_lumps(doom)["VERTEXES"])

    def test_parser_rejects_truncated_and_unknown_headers(self):
        with self.assertRaisesRegex(DoomError, "too short"):
            parse_wad(b"PWAD")
        with self.assertRaisesRegex(DoomError, "unsupported WAD"):
            parse_wad(b"NOPE" + b"\0" * 12)

    def _assert_iwad(self, path: Path, expected_maps: int):
        wad = _load(path)
        if wad is None:
            self.skipTest(f"{path.name} is not present")
        self.assertEqual(wad.kind, "IWAD")
        self.assertEqual(len(wad.maps), expected_maps)
        supported = [level for level in wad.maps if level.supported]
        self.assertEqual(len(supported), expected_maps)
        original = path.read_bytes()
        rebuilt = encode_wad(wad)
        self.assertEqual(rebuilt, original)
        for level in supported:
            with self.subTest(map=level.name):
                lumps = encode_doom_map_lumps(level)
                self.assertEqual(len(lumps["VERTEXES"]) % 4, 0)
                self.assertFalse([item for item in validate_doom_map(level) if item["severity"] == "error"])
                mutated = copy.deepcopy(level)
                mutated.linedefs[0].tag = (mutated.linedefs[0].tag + 1) & 0x7FFF
                self.assertNotEqual(encode_doom_map_lumps(mutated)["LINEDEFS"], lumps["LINEDEFS"])

    def test_doom_wad_parses_and_roundtrips(self):
        # Ultimate Doom retail has 36 maps (E1–E4); registered has 27; shareware 9.
        wad = _load(DOOM_WAD)
        if wad is None:
            self.skipTest("doom.wad is not present")
        self.assertIn(len(wad.maps), {9, 27, 36})
        self._assert_iwad(DOOM_WAD, len(wad.maps))

    def test_doom2_wad_parses_and_roundtrips(self):
        self._assert_iwad(DOOM2_WAD, 32)

    def test_unsigned_linedef_special_roundtrips(self):
        wad = _load(DOOM_WAD)
        if wad is None:
            self.skipTest("doom.wad is not present")
        level = wad_map(wad, "E2M7")
        self.assertTrue(any(line.special == 0xFFFF for line in level.linedefs))
        lumps = encode_doom_map_lumps(level)
        from bloodmap.doom import parse_doom_map
        again = parse_doom_map("E2M7", lumps)
        self.assertTrue(any(line.special == 0xFFFF for line in again.linedefs))
        report = doom_corpus_report(wad, path=DOOM_WAD)
        self.assertEqual(report["parse_count"], 36)
        self.assertEqual(report["supported_count"], 36)
        self.assertEqual(report["roundtrip_count"], 36)
        self.assertEqual(report["validation_count"], 36)
        self.assertEqual(report["format_classification"], ["doom"])


if __name__ == "__main__":
    unittest.main()
