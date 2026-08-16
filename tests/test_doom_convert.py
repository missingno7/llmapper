from __future__ import annotations

import json
import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.doom import encode_wad, new_wad, read_wad, wad_map
from bloodmap.doom_convert import convert_doom_to_blood
from bloodmap.doom_fixtures import ALL_FIXTURES, fixture_basic_room, fixture_keyed_door
from bloodmap.doom_geometry import XY_SCALE, Z_SCALE
from bloodmap.doom_semantics import doom_to_semantic_level
from bloodmap.format import encode_map, parse_map, read_map
from bloodmap.mechanisms import solve_progression
from bloodmap.semantics import blood_to_semantic_level


DOOM_WAD = Path(os.environ.get("DOOM_IWAD", Path(__file__).resolve().parents[1] / "maps" / "doom" / "doom.wad"))
DOOM2_WAD = Path(os.environ.get("DOOM2_IWAD", Path(__file__).resolve().parents[1] / "maps" / "doom" / "DOOM2.WAD"))
if not DOOM2_WAD.exists():
    DOOM2_WAD = DOOM2_WAD.with_name("doom2.wad")


class DoomConvertTests(unittest.TestCase):
    def test_basic_room_converts_to_valid_blood(self):
        _semantic, doom, _blood = fixture_basic_room()
        level, report = convert_doom_to_blood(doom)
        disk = parse_map(encode_map(level.to_disk_map()))
        self.assertFalse([item for item in validate_map(disk) if item.severity == "error"])
        self.assertGreaterEqual(len(disk.sectors), 3)
        self.assertEqual(report["source_counts"]["sectors"], 3)
        self.assertEqual(disk.header["start_sector"], level.player_start["sector"])

    def test_keyed_door_survives_lowering(self):
        semantic, doom, _blood = fixture_keyed_door()
        level, report = convert_doom_to_blood(doom)
        self.assertTrue(any(item["kind"] == "key_gate" for item in report["mechanism_records"]))
        self.assertTrue(any(sprite["fields"]["type"] == 100 for sprite in level.sprites))
        doors = [sector for sector in level.sectors if sector["fields"]["type"] == 600]
        self.assertTrue(doors)
        self.assertTrue(any(int(sector.get("blood", {}).get("fields", {}).get("key", 0)) == 1 for sector in doors if sector.get("blood")))
        doom_solution = solve_progression(semantic)
        self.assertTrue(doom_solution["exit_reachable"])

    def test_original_e1m1_converts_and_reparses(self):
        if not DOOM_WAD.exists():
            self.skipTest("DOOM.WAD is not present")
        doom = wad_map(read_wad(DOOM_WAD), "E1M1")
        level, report = convert_doom_to_blood(doom)
        rebuilt = parse_map(encode_map(level.to_disk_map()))
        self.assertFalse([item for item in validate_map(rebuilt) if item.severity == "error"])
        self.assertGreater(report["mechanisms_translated"], 0)
        self.assertGreater(len(level.sectors), 50)
        self.assertEqual(rebuilt.header["start_sector"], level.player_start["sector"])
        work = Path(__file__).resolve().parents[1] / "work"
        work.mkdir(exist_ok=True)
        (work / "E1M1-BLOOD.MAP").write_bytes(encode_map(level.to_disk_map()))
        (work / "E1M1-BLOOD.report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )

    def test_e1m1_scale_matches_wad2map_and_tede1m9(self):
        self.assertEqual(XY_SCALE, 16)
        self.assertEqual(Z_SCALE, 256)
        if not DOOM_WAD.exists():
            self.skipTest("DOOM.WAD is not present")
        tede = Path(__file__).resolve().parents[1] / "maps" / "blood" / "TEDE1M9.MAP"
        if not tede.exists():
            self.skipTest("TEDE1M9.MAP is not present")
        doom = wad_map(read_wad(DOOM_WAD), "E1M1")
        blood = read_map(tede)
        doom_vecs = Counter()
        for line in doom.linedefs:
            a, b = doom.vertices[line.v1], doom.vertices[line.v2]
            doom_vecs[(b.x - a.x, b.y - a.y)] += 1
        blood_vecs = Counter()
        for wall in blood.walls:
            other = blood.walls[wall.point2]
            blood_vecs[(other.x - wall.x, other.y - wall.y)] += 1

        def overlap(scale: int) -> int:
            return sum(
                min(count, blood_vecs[(dx * scale, -dy * scale)])
                for (dx, dy), count in doom_vecs.items()
            )

        self.assertGreater(overlap(16), overlap(32))
        blood_z = Counter(sector.floor_z for sector in blood.sectors)
        blood_z.update(sector.ceiling_z for sector in blood.sectors)
        doom_h = [sector.floor_height for sector in doom.sectors]
        doom_h.extend(sector.ceiling_height for sector in doom.sectors)
        hits = {k: sum(blood_z[-h * k] for h in doom_h) for k in (137, 256)}
        self.assertGreater(hits[256], hits[137])
        converted, report = convert_doom_to_blood(doom)
        self.assertEqual(len(converted.sectors), len(doom.sectors))
        self.assertEqual(report["scale"]["xy"], 16)
        self.assertEqual(report["scale"]["z"], 256)
        self.assertGreater(len(blood.sectors), len(doom.sectors))

    def test_representative_original_maps_convert(self):
        work = Path(__file__).resolve().parents[1] / "work"
        work.mkdir(exist_ok=True)
        cases = []
        if DOOM_WAD.exists():
            cases.extend([(DOOM_WAD, name) for name in ("E1M1", "E1M3", "E2M1")])
        if DOOM2_WAD.exists():
            cases.append((DOOM2_WAD, "MAP01"))
        if not cases:
            self.skipTest("Doom IWADs are not present")
        converted = 0
        for wad_path, name in cases:
            with self.subTest(map=name):
                doom = wad_map(read_wad(wad_path), name)
                level, report = convert_doom_to_blood(doom)
                rebuilt = parse_map(encode_map(level.to_disk_map()))
                self.assertFalse([item for item in validate_map(rebuilt) if item.severity == "error"])
                self.assertGreater(report["mechanisms_translated"], 0)
                (work / f"{name}-BLOOD.MAP").write_bytes(encode_map(level.to_disk_map()))
                (work / f"{name}-BLOOD.report.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
                )
                converted += 1
        self.assertGreaterEqual(converted, 1)


class CrossEngineFixtureTests(unittest.TestCase):
    def test_shared_semantic_progression_matches_across_fixtures(self):
        for name, factory in ALL_FIXTURES.items():
            with self.subTest(fixture=name):
                semantic, doom, blood = factory()
                authored = solve_progression(semantic)
                from_doom = solve_progression(doom_to_semantic_level(doom))
                from_blood = solve_progression(blood_to_semantic_level(blood))
                self.assertTrue(authored["exit_reachable"], msg=name)
                self.assertTrue(from_doom["exit_reachable"], msg=name)
                self.assertTrue(from_blood["exit_reachable"], msg=name)
                converted, _report = convert_doom_to_blood(doom)
                from_converted = solve_progression(blood_to_semantic_level(converted))
                self.assertTrue(from_converted["exit_reachable"], msg=name)
                self.assertFalse([item for item in validate_map(converted.to_disk_map()) if item.severity == "error"])
                self.assertGreaterEqual(blood.player_start["sector"], 0)

    def test_fixture_wads_roundtrip(self):
        _semantic, doom, _blood = fixture_basic_room()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.wad"
            path.write_bytes(encode_wad(new_wad(maps=[doom])))
            again = wad_map(read_wad(path), "MAP01")
            self.assertEqual(len(again.sectors), len(doom.sectors))


if __name__ == "__main__":
    unittest.main()
