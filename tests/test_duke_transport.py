"""Directed Duke transports and converter compatibility on synthetic and corpus maps."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from bloodmap.analysis import validate_map
from bloodmap.cli import main
from bloodmap.corpus import list_corpus_maps
from bloodmap.duke import (
    DukeDiskMap, SECTOR_FIELDS, SPRITE_FIELDS, WALL_FIELDS,
    encode_duke_map, read_duke_map,
)
from bloodmap.duke_semantics import classify_se7_groups
from bloodmap.e3l11 import ChannelAllocator, PlayableConversionError, convert_playable_duke_to_blood
from bloodmap.format import encode_map, parse_map
from bloodmap.model import DiskObject


ROOT = Path(__file__).resolve().parents[1]


def board(*effectors: dict[str, int], exit_sector: int | None = 0) -> DukeDiskMap:
    """Four disconnected square rooms, with explicitly authored controllers."""
    sectors, walls, sprites = [], [], []
    for sector_id in range(4):
        fields = {name: 0 for name, _ in SECTOR_FIELDS}
        fields.update(wall_ptr=4 * sector_id, wall_count=4, ceiling_z=-16384,
                      floor_z=16384, extra=-1)
        sectors.append(DiskObject(fields))
        for n, (x, y) in enumerate(((0, 0), (4096, 0), (4096, 4096), (0, 4096))):
            fields = {name: 0 for name, _ in WALL_FIELDS}
            fields.update(x=x + sector_id * 8192, y=y, point2=4 * sector_id + (n + 1) % 4,
                          next_wall=-1, next_sector=-1, x_repeat=8, y_repeat=8, extra=-1)
            walls.append(DiskObject(fields))
    authored = list(effectors)
    if exit_sector is not None:
        authored.append({"picnum": 142, "sector": exit_sector})
    for spec in authored:
        fields = {name: 0 for name, _ in SPRITE_FIELDS}
        fields.update(x=spec.get("sector", 0) * 8192 + 512, y=512, z=16384,
                      picnum=1, lotag=7, hitag=9017, x_repeat=64, y_repeat=64,
                      owner=-1, extra=-1)
        fields.update(spec)
        sprites.append(DiskObject(fields))
    return DukeDiskMap(7, {"version": 7, "start_x": 512, "start_y": 512,
                          "start_z": 0, "start_angle": 0, "start_sector": 0},
                       sectors, walls, sprites)


class DirectedTransportTests(unittest.TestCase):
    def convert(self, duke):
        original = encode_duke_map(duke)
        disk, report = convert_playable_duke_to_blood(duke)
        self.assertEqual(encode_duke_map(duke), original)
        disk = parse_map(encode_map(disk))
        self.assertFalse([d for d in validate_map(disk) if d.severity == "error"])
        json.dumps(report)
        return disk, report

    def routes(self, report):
        return [r for r in report["mechanisms"]["records"] if r["kind"] == "teleporter"]

    def test_se7_to_se23_emits_one_owned_marker_and_no_return_route(self):
        duke = board({"sector": 0}, {"sector": 1, "lotag": 23, "angle": 768}, exit_sector=1)
        disk, report = self.convert(duke)
        self.assertEqual(disk.sectors[0].type, 604)
        self.assertEqual(disk.sectors[1].type, 0)
        pad = disk.sectors[0].extra
        self.assertEqual((pad.trigger_enter, pad.dude_lockout, pad.data), (1, 1, 0))
        marker = disk.sprites[pad.marker_0]
        self.assertEqual((marker.type, marker.status, marker.owner, marker.sector), (8, 10, 0, 1))
        self.assertEqual((marker.x, marker.y, marker.z, marker.angle), (13056, 768, 24576, 768))
        self.assertEqual([(r["source_sprite"], r["destination_sprite"]) for r in self.routes(report)], [(0, 1)])
        self.assertTrue(self.routes(report)[0]["one_way"])
        self.assertTrue(report["overall"]["static_progression"]["all_exits_reachable"])
        self.assertNotIn(23, report["mechanisms"]["unsupported_sector_effector_lotags"])
        inventory = report["mechanisms"]["semantic_inventory"]["effectors"]
        self.assertEqual(inventory[1]["kind"], "teleport_destination")

    def test_progression_does_not_add_a_reverse_edge(self):
        duke = board({"sector": 0}, {"sector": 1, "lotag": 23}, exit_sector=0)
        duke.header.update(start_sector=1, start_x=8704)
        _disk, report = self.convert(duke)
        self.assertEqual(report["overall"]["static_progression"]["reachable_sectors"], 1)
        self.assertFalse(report["overall"]["static_progression"]["all_exits_reachable"])
        self.assertIsNone(report["overall"]["guaranteed_exit_channel"])
        self.assertIn("static-progression-unproven", {d["code"] for d in report["diagnostics"]})

    def test_destination_need_not_be_on_floor(self):
        duke = board({"sector": 0}, {"sector": 1, "lotag": 23, "z": 4096})
        disk, report = self.convert(duke)
        self.assertEqual(disk.sprites[disk.sectors[0].extra.marker_0].z, 6144)
        self.assertEqual(len(self.routes(report)), 1)

    def test_destination_coordinates_are_not_clamped_or_moved_into_the_room(self):
        duke = board({"sector": 0}, {"sector": 1, "lotag": 23, "x": 8000, "z": 65536})
        disk, report = self.convert(duke)
        marker = disk.sprites[disk.sectors[0].extra.marker_0]
        self.assertEqual((marker.x, marker.y, marker.z), (12000, 768, 98304))
        self.assertIn("converted-sprite-outside-volume", {d["code"] for d in report["diagnostics"]})

    def test_first_other_live_endpoint_wins_without_preferring_se23(self):
        cases = [
            ((7, 7, 23), [(0, 1), (1, 0)]),
            ((23, 7, 7), [(1, 0), (2, 0)]),
            ((7, 23, 23), [(0, 1)]),
            ((7, 7, 7), [(0, 1), (1, 0), (2, 0)]),
        ]
        for tags, expected in cases:
            with self.subTest(tags=tags):
                duke = board(*({"sector": i, "lotag": tag} for i, tag in enumerate(tags)))
                _disk, report = self.convert(duke)
                self.assertEqual([(r["source_sprite"], r["destination_sprite"]) for r in self.routes(report)], expected)

    def test_inactive_endpoint_is_not_selected(self):
        duke = board({"sector": 0}, {"sector": 1, "lotag": 23, "status": 1024},
                     {"sector": 2, "lotag": 23})
        groups = classify_se7_groups(duke)
        self.assertEqual(groups[9017]["routes"][0]["destination_sprite"], 2)

    def test_full_signed_hitags_including_zero_are_link_ids(self):
        for hitag in (0, -1, 9017, 32767):
            with self.subTest(hitag=hitag):
                duke = board({"sector": 0, "hitag": hitag},
                             {"sector": 1, "lotag": 23, "hitag": hitag})
                _disk, report = self.convert(duke)
                self.assertEqual(self.routes(report)[0]["link"], hitag)

    def test_regular_two_way_floor_pair_keeps_both_directions(self):
        disk, report = self.convert(board({"sector": 0}, {"sector": 1}))
        self.assertEqual([s.type for s in disk.sectors], [604, 604, 0, 0])
        self.assertEqual([(r["source_sprite"], r["destination_sprite"]) for r in self.routes(report)], [(0, 1), (1, 0)])

    def test_orphan_is_diagnosed_without_blocking_an_independent_valid_route(self):
        duke = board({"sector": 0, "hitag": 99}, {"sector": 1},
                     {"sector": 2, "lotag": 23})
        disk, report = self.convert(duke)
        self.assertEqual([s.type for s in disk.sectors], [0, 604, 0, 0])
        diag = next(d for d in report["diagnostics"] if d["code"] == "duke-transport-unsupported")
        self.assertEqual((diag["hitag"], diag["source_sprite"], diag["source_sector"]), (99, 0, 0))
        self.assertIsNone(diag["destination_sprite"])
        self.assertEqual(diag["endpoints"][0]["position"], [512, 512, 16384])
        self.assertIn("self-owned and inactive", diag["reason"])
        self.assertEqual(report["mechanisms"]["unsupported_sector_effector_lotags"], {7: 1})

    def test_destination_only_group_is_an_inert_controller(self):
        disk, report = self.convert(board({"sector": 0, "lotag": 23}))
        self.assertFalse(self.routes(report))
        self.assertEqual(disk.sectors[0].type, 0)
        self.assertEqual(report["mechanisms"]["semantic_inventory"]["se7_groups"]["9017"]["kind"], "destination_only")

    def test_one_way_silent_and_water_routes_are_explicitly_unsupported(self):
        for mode in ("silent", "water"):
            with self.subTest(mode=mode):
                duke = board({"sector": 0, "z": 0 if mode == "silent" else 16384},
                             {"sector": 1, "lotag": 23})
                if mode == "water":
                    duke.sectors[0].lotag, duke.sectors[1].lotag = 1, 2
                disk, report = self.convert(duke)
                self.assertFalse(self.routes(report))
                self.assertFalse([s for s in disk.sprites if s.type in {6, 7, 8, 9, 10, 11, 12}])
                diag = next(d for d in report["diagnostics"] if d["code"] == "duke-transport-unsupported")
                self.assertEqual(diag["destination_sprite"], 1)
                self.assertIn("reverse route", diag["reason"])

    def test_mixed_floor_and_silent_pair_does_not_become_bidirectional_hatch(self):
        disk, report = self.convert(board({"sector": 0}, {"sector": 1, "z": 0}))
        self.assertEqual([s.type for s in disk.sectors], [604, 0, 0, 0])
        self.assertFalse([s for s in disk.sprites if s.type in {6, 7, 11, 12}])
        self.assertEqual(report["mechanisms"]["unsupported_sector_effector_lotags"], {7: 1})

    def test_reciprocal_water_and_hatch_pairs_still_emit_complete_marker_pairs(self):
        for kind, expected in (("water", {9, 10}), ("hatch", {11, 12})):
            with self.subTest(kind=kind):
                duke = board({"sector": 0, "z": 16384 if kind == "water" else 8192},
                             {"sector": 1, "z": 16384 if kind == "water" else -8192})
                if kind == "water":
                    duke.sectors[0].lotag, duke.sectors[1].lotag = 1, 2
                disk, report = self.convert(duke)
                self.assertEqual({s.type for s in disk.sprites if s.type in expected}, expected)
                self.assertFalse(report["diagnostics"])

    def test_multiple_source_transports_in_one_sector_are_not_overwritten(self):
        duke = board({"sector": 0, "hitag": 2}, {"sector": 1, "lotag": 23, "hitag": 2},
                     {"sector": 0, "hitag": 3}, {"sector": 2, "lotag": 23, "hitag": 3})
        disk, report = self.convert(duke)
        self.assertEqual(disk.sectors[0].type, 0)
        self.assertFalse(self.routes(report))
        self.assertEqual(sum(d["code"] == "duke-transport-unsupported" for d in report["diagnostics"]), 2)

    def test_transport_does_not_replace_sector_motion(self):
        duke = board({"sector": 0}, {"sector": 1, "lotag": 23},
                     {"sector": 0, "lotag": 31, "z": 0})
        disk, report = self.convert(duke)
        self.assertEqual(disk.sectors[0].type, 600)
        self.assertFalse(self.routes(report))
        self.assertIn("No behavior was overwritten", report["diagnostics"][0]["reason"])

    def test_runtime_sector_lotag_is_not_masked_into_a_floor_teleporter(self):
        duke = board({"sector": 0}, {"sector": 1, "lotag": 23})
        duke.sectors[0].lotag = 16384
        disk, report = self.convert(duke)
        self.assertEqual(disk.sectors[0].type, 0)
        self.assertFalse(self.routes(report))

    def test_non_pair_warp_elevators_have_diagnostics(self):
        duke = board(*({"sector": i, "lotag": 17} for i in range(3)))
        disk, report = self.convert(duke)
        self.assertFalse([s for s in disk.sectors if s.type == 604])
        diag = next(d for d in report["diagnostics"] if d["code"] == "duke-warp-elevator-unsupported")
        self.assertEqual(diag["source_sprites"], [0, 1, 2])
        self.assertEqual(report["mechanisms"]["unsupported_sector_effector_lotags"], {17: 3})

    def test_no_exit_is_reported_without_fabricating_one(self):
        disk, report = self.convert(board(exit_sector=None))
        self.assertEqual(report["overall"]["static_progression"]["exit_sectors"], [])
        self.assertIsNone(report["overall"]["guaranteed_exit_channel"])
        self.assertFalse([s for s in disk.sprites if s.extra and s.extra.tx_id == 4])

    def test_outside_motion_marker_is_retained_with_ownership_and_diagnostic(self):
        duke = board({"sector": 0, "lotag": 15, "x": -10000})
        disk, report = self.convert(duke)
        self.assertEqual(disk.sectors[0].type, 616)
        self.assertEqual(disk.sprites[disk.sectors[0].extra.marker_0].owner, 0)
        self.assertTrue(any(d["code"] == "converted-sprite-outside-volume" for d in report["diagnostics"]))

    def test_original_header_start_outside_volume_is_retained_and_reported(self):
        duke = board()
        duke.header["start_z"] = 65536
        disk, report = self.convert(duke)
        marker = next(s for s in disk.sprites if s.type == 1)
        self.assertEqual(marker.z, 98304)
        self.assertEqual(disk.header["start_z"], 98304)
        self.assertIn("converted-sprite-outside-volume", {d["code"] for d in report["diagnostics"]})

    def test_structural_errors_still_abort(self):
        duke = board()
        duke.walls[0].point2 = 9000
        with self.assertRaisesRegex(ValueError, "validation"):
            convert_playable_duke_to_blood(duke)

    def test_channel_capacity_remains_a_real_target_limit(self):
        channels = ChannelAllocator()
        assigned = [channels.allocate(-i) for i in range(1, 925)]
        self.assertEqual((min(assigned), max(assigned), len(set(assigned))), (100, 1023, 924))
        with self.assertRaises(PlayableConversionError):
            channels.allocate(-925)

    def test_hidden_exploder_survives_a_closed_sector_with_no_vertical_volume(self):
        duke = board({"sector": 0, "lotag": 31, "z": -65536},
                     {"sector": 0, "picnum": 1247, "x_repeat": 4})
        disk, report = self.convert(duke)
        self.assertEqual(len([s for s in disk.sprites if s.type == 459]), 1)
        self.assertIn("converted-sprite-outside-volume", {d["code"] for d in report["diagnostics"]})

    def test_invalid_source_sector_still_aborts(self):
        duke = board({"sector": 0})
        duke.sprites[0].sector = 9000
        with self.assertRaises(ValueError):
            convert_playable_duke_to_blood(duke)

    def test_cli_writes_diagnostic_report_and_does_not_modify_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.MAP"
            target = Path(directory) / "target.MAP"
            report_path = Path(directory) / "report.json"
            payload = encode_duke_map(board({"sector": 0}, exit_sector=None))
            source.write_bytes(payload)
            self.assertEqual(main(["convert-playable", str(source), "-o", str(target),
                                   "--report", str(report_path), "--duke-art", directory,
                                   "--blood-art", directory, "--blood-maps", directory]), 0)
            report = json.loads(report_path.read_text())
            self.assertTrue(report["output"]["reparsed"])
            self.assertIn("duke-transport-unsupported", {d["code"] for d in report["diagnostics"]})
            self.assertEqual(source.read_bytes(), payload)
            parse_map(target.read_bytes())


class DukeCorpusCompatibilityTests(unittest.TestCase):
    def test_complete_local_duke_corpus_converts_reparses_and_preserves_sources(self):
        maps = list_corpus_maps(os.environ.get("DUKEMAP_CORPUS", ROOT / "maps" / "duke3d"))
        if not maps:
            self.skipTest("no local Duke corpus")
        for item in maps:
            with self.subTest(map=item.name):
                original = item.path.read_bytes()
                duke = read_duke_map(item.path)
                disk, report = convert_playable_duke_to_blood(duke)
                reparsed = parse_map(encode_map(disk))
                self.assertFalse([d for d in validate_map(reparsed) if d.severity == "error"])
                self.assertEqual(hashlib.sha256(item.path.read_bytes()).digest(), hashlib.sha256(original).digest())
                self.assertEqual(encode_duke_map(duke), original)
                sources = {i for i, s in enumerate(duke.sprites)
                           if s.picnum == 1 and s.lotag == 7 and s.status < 1024}
                lowered = {r["source_sprite"] for r in report["mechanisms"]["records"]
                           if r.get("source_sprite") in sources}
                unsupported = {d["source_sprite"] for d in report["diagnostics"]
                               if d["code"] == "duke-transport-unsupported"}
                self.assertEqual(sources, lowered | unsupported)
                self.assertFalse(lowered & unsupported)
                if item.name == "E4L1.MAP":
                    route = next(r for r in report["mechanisms"]["records"] if r.get("link") == 9017)
                    self.assertEqual((route["source_sprite"], route["destination_sprite"]), (1036, 1039))
                    self.assertEqual((reparsed.sectors[537].type, reparsed.sectors[538].type), (604, 0))


if __name__ == "__main__":
    unittest.main()
