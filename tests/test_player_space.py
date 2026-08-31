from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.cli import main
from bloodmap.doom import DoomSector, DoomThing, _tex8
from bloodmap.doom_fixtures import assemble_doom, fixture_basic_room
from bloodmap.format import write_map
from bloodmap.player_space import (
    PLAYER_PROFILES, comparable_openings, compare_transition, conversion_player_scale_report,
    focus_observation, inspect_connection, inspect_doom_space, inspect_space,
    material_player_scale, material_world_scale, mine_build_spatial_corpus,
    mine_doom_spatial_corpus, player_profile, present_space, sprite_height_above_floor,
    traversal_affordances,
)
from bloodmap.spatial import analyze_spatial
from tests.helpers import synthetic_two_sector_map


def _pair(
    points: list[tuple[int, int]] | None = None,
    *,
    floor0: int = 8192,
    ceil0: int = -8192,
    floor1: int = 8192,
    ceil1: int = -8192,
    ceil_stat0: int = 0,
    ceil_stat1: int = 0,
    x_repeat: int = 8,
):
    disk = synthetic_two_sector_map()
    disk.sectors[0].fields.update(floor_z=floor0, ceiling_z=ceil0, ceiling_stat=ceil_stat0)
    disk.sectors[1].fields.update(floor_z=floor1, ceiling_z=ceil1, ceiling_stat=ceil_stat1)
    if points is not None:
        for index, (x, y) in enumerate(points):
            disk.walls[index].fields["x"] = x
            disk.walls[index].fields["y"] = y
    for wall in disk.walls:
        wall.fields["x_repeat"] = x_repeat
        wall.fields["picnum"] = 12
    return disk.to_build_ir()


def _corridor_into_hall():
    # Sector 0: 4096 x 384 corridor. Sector 1: 16384 x 4096 hall. Shared portal 384.
    return _pair([
        (0, 0), (4096, 0), (4096, 384), (0, 384),
        (4096, 0), (20480, 0), (20480, 4096), (4096, 4096),
    ])


class PlayerProfileTests(unittest.TestCase):
    def test_profiles_are_source_backed_and_keep_collision_separate_from_view(self):
        blood = player_profile("blood")
        duke = player_profile("duke")
        doom = player_profile("doom")

        self.assertEqual(blood.body_radius, 192)
        self.assertEqual(blood.body_width, 384)
        # The body is the drawn figure. 0x1600 is `eyeAboveZ`, an offset from
        # the sprite's centre, and it lives on its own field now -- calling it a
        # standing height put this project's camera at chest level for months.
        self.assertEqual(blood.standing_height, 16960)
        self.assertEqual(blood.crouch_height, 13376)
        self.assertEqual(blood.eye_above_centre, 0x1600)
        self.assertEqual(blood.eye_height, 14112)
        self.assertIn("GetSpriteExtents", blood.evidence["standing_height"])
        self.assertTrue(blood.jump)
        self.assertTrue(blood.crouch)
        self.assertIn("clipdist=0x30", blood.evidence["body_radius"])

        self.assertEqual(duke.body_radius, 164)
        self.assertEqual(duke.standing_height, 38 << 8)
        self.assertEqual(duke.max_step, 20 << 8)
        self.assertIsNone(duke.crouch_height)
        self.assertTrue(duke.crouch)

        self.assertEqual(doom.body_width, 32)
        self.assertEqual(doom.standing_height, 56)
        self.assertEqual(doom.eye_height, 41)
        self.assertNotEqual(doom.standing_height, doom.eye_height)
        self.assertFalse(doom.jump)
        self.assertFalse(doom.crouch)
        self.assertEqual(PLAYER_PROFILES["blood"].id, "player-profile:blood")
        self.assertEqual(blood.to_dict()["optional_meters"]["role"].startswith("optional"), True)

    def test_player_relative_opening_keeps_native_raw_value(self):
        build = synthetic_two_sector_map().to_build_ir()
        payload = inspect_connection(build, wall_id=1)
        self.assertEqual(payload["width"]["raw"], 1024)
        self.assertEqual(payload["width"]["player_widths"], round(1024 / 384, 4))
        self.assertEqual(payload["width"]["native_unit"], "build")
        self.assertEqual(payload["width"]["profile"], "player-profile:blood")
        self.assertIsNone(payload["width"]["corpus_percentile"])
        compact = present_space(payload)
        self.assertEqual(compact["width_player_widths"], payload["width"]["player_widths"])
        self.assertIn("raw", payload["width"])


class TraversalAffordanceTests(unittest.TestCase):
    def test_physical_fit_is_independent_of_existing_spatial_width_threshold(self):
        profile = player_profile("blood")
        spatial = analyze_spatial(synthetic_two_sector_map().to_build_ir())
        self.assertEqual(spatial["views"]["traversability"]["walkable_at_rest"][0]["width"], 1024)

        fits = traversal_affordances(
            width=400, opening=20480, floor_delta=0, blocking=False, profile=profile,
        )
        blocked = traversal_affordances(
            width=256, opening=20480, floor_delta=0, blocking=False, profile=profile,
        )
        self.assertTrue(fits["can_fit"])
        self.assertTrue(fits["can_walk_through"])
        self.assertFalse(blocked["can_fit"])
        self.assertTrue(blocked["cannot_traverse"])
        self.assertEqual(fits["physical"]["width_player_widths"], round(400 / 384, 4))

    def test_step_crouch_and_jump_follow_the_player_profile(self):
        profile = player_profile("blood")
        step = traversal_affordances(
            width=1024, opening=20480, floor_delta=5000, blocking=False, profile=profile,
        )
        self.assertFalse(step["can_step_up"])
        self.assertTrue(step["requires_jump"])
        self.assertFalse(step["can_walk_through"])

        crouch = traversal_affordances(
            width=1024, opening=14336, floor_delta=0, blocking=False, profile=profile,
        )
        self.assertTrue(crouch["requires_crouch"])
        self.assertFalse(crouch["can_walk_through"])

        too_low = traversal_affordances(
            width=1024, opening=12288, floor_delta=0, blocking=False, profile=profile,
        )
        self.assertTrue(too_low["cannot_traverse"])

        doom = traversal_affordances(
            width=64, opening=128, floor_delta=32, blocking=False, profile=player_profile("doom"),
        )
        self.assertFalse(doom["can_step_up"])
        self.assertFalse(doom["requires_jump"])
        self.assertTrue(doom["cannot_traverse"])

    def test_inspect_connection_reports_cannot_fit_on_a_sub_body_portal(self):
        build = _pair([
            (0, 0), (1024, 0), (1024, 256), (0, 256),
            (1024, 0), (2048, 0), (2048, 256), (1024, 256),
        ])
        payload = inspect_connection(build, left=0, right=1)
        self.assertEqual(payload["width"]["raw"], 256)
        self.assertLess(payload["width"]["player_widths"], 1.0)
        self.assertFalse(payload["movement"]["can_fit"])
        self.assertTrue(payload["movement"]["cannot_traverse"])


class CorpusPercentileTests(unittest.TestCase):
    def test_percentiles_come_from_observed_player_relative_samples(self):
        maps = [("wide", synthetic_two_sector_map().to_build_ir()) for _ in range(8)]
        maps.append(("tight", _pair([
            (0, 0), (1024, 0), (1024, 256), (0, 256),
            (1024, 0), (2048, 0), (2048, 256), (1024, 256),
        ])))
        corpus = mine_build_spatial_corpus(maps)
        self.assertGreaterEqual(len(corpus["opening_width_player_widths"]), 2)
        tight = inspect_connection(maps[-1][1], wall_id=1, corpus=corpus)
        wide = inspect_connection(maps[0][1], wall_id=1, corpus=corpus)
        self.assertLess(tight["width"]["corpus_percentile"], wide["width"]["corpus_percentile"])
        self.assertIn("traversable_opening_width_player_widths", corpus)
        self.assertGreaterEqual(len(corpus["opening_width_player_widths"]), len(corpus["traversable_opening_width_player_widths"]))
        self.assertEqual(tight["width"]["interpretation"]["confidence"], "heuristic")
        self.assertIn("narrow", tight["width"]["interpretation"]["value"])
        self.assertIn("clusters", corpus)

    def test_corpus_does_not_mix_games(self):
        with self.assertRaises(Exception):
            mine_build_spatial_corpus([])


class TransitionAndEnclosureTests(unittest.TestCase):
    def test_narrow_approach_into_a_wider_taller_destination(self):
        build = _corridor_into_hall()
        build.sectors[1]["fields"]["ceiling_z"] = -16384
        payload = compare_transition(build, [0], [1])
        self.assertGreaterEqual(payload["width_ratio"], 4.0)
        self.assertGreater(payload["navigable_area_ratio"], 3.0)
        self.assertGreater(payload["clear_height_ratio"], 1.0)
        self.assertEqual(payload["interpretation"]["value"], "strong spatial expansion")
        self.assertEqual(payload["interpretation"]["confidence"], "heuristic")
        compact = present_space(payload)
        self.assertEqual(compact["kind"], "transition")
        self.assertNotIn("source", compact)

    def test_enclosure_is_faceted_not_binary_indoor_outdoor(self):
        indoor = inspect_space(synthetic_two_sector_map().to_build_ir(), [0])
        sky = inspect_space(_pair(ceil_stat1=1), [1])
        self.assertIn("sky_exposure", indoor["enclosure"])
        self.assertIn("lateral_enclosure", indoor["enclosure"])
        self.assertIn("vertical_enclosure", indoor["enclosure"])
        self.assertNotIn("indoor", indoor["enclosure"])
        self.assertEqual(indoor["enclosure"]["sky_exposure"], 0.0)
        self.assertEqual(sky["enclosure"]["sky_exposure"], 1.0)
        self.assertGreater(indoor["enclosure"]["vertical_enclosure"], sky["enclosure"]["vertical_enclosure"])
        self.assertGreater(indoor["enclosure"]["lateral_enclosure"], 0.5)

    def test_question_oriented_focus_does_not_dump_the_full_payload(self):
        payload = inspect_space(synthetic_two_sector_map().to_build_ir(), [0])
        focused = focus_observation(payload, "enclosure")
        self.assertEqual(set(focused), {"kind", "enclosure"})
        self.assertIn("sky_exposure", focused["enclosure"])


class CrossGameAndMaterialTests(unittest.TestCase):
    def test_player_relative_openings_are_comparable_across_native_units(self):
        comparison = comparable_openings(("doom", 64), ("duke3d", 656), ("blood", 768))
        widths = [item["player_widths"] for item in comparison["openings"]]
        self.assertTrue(all(1.9 <= value <= 2.1 for value in widths))
        self.assertTrue(comparison["approximately_comparable"])
        report = conversion_player_scale_report()
        self.assertAlmostEqual(report["after_existing_xy_scale"]["duke_over_blood"], 1.2812, places=3)
        self.assertAlmostEqual(report["after_existing_xy_scale"]["doom_over_blood"], 512 / 384, places=4)
        self.assertIn("not a replacement", report["conclusion"])

    def test_texture_world_scale_is_player_relative(self):
        profile = player_profile("blood")
        scale = material_world_scale(
            world_widths=[128, 128, 160],
            x_repeats=[8, 8, 8],
            tile_width=128,
            profile=profile,
        )
        self.assertEqual(scale["typical_x_repeat"], 8)
        self.assertEqual(scale["player_widths_per_repeat"]["median"], round(128 / 384, 4))
        self.assertTrue(scale["rarely_tiled_horizontally"])
        tiled = material_world_scale(
            world_widths=[1024, 1024, 2048],
            x_repeats=[8, 8, 16],
            tile_width=128,
            profile=profile,
        )
        self.assertFalse(tiled["rarely_tiled_horizontally"])
        asset = {
            "game": "blood",
            "appearance": {"width": 128, "height": 64},
            "distributions": {
                "world_width": {"kind": "exact", "counts": {"1024": 3}, "samples": 3},
                "x_repeat": {"kind": "exact", "counts": {"8": 3}, "samples": 3},
            },
        }
        from_asset = material_player_scale(asset)
        self.assertEqual(from_asset["typical_x_repeat"], 8)

    def test_sprite_height_keeps_raw_and_player_heights(self):
        build = synthetic_two_sector_map().to_build_ir()
        payload = sprite_height_above_floor(build, 0)
        self.assertEqual(payload["raw"], 8192)
        self.assertEqual(payload["player_heights"], round(8192 / 16960, 4))

    def test_doom_space_uses_the_doom_player_profile(self):
        vertices = [
            (0, 0), (128, 0), (128, 32), (0, 32),
            (512, 0), (512, 32),
        ]
        doom = assemble_doom(
            "MAP01",
            vertices,
            [
                (0, 3, 0, None), (3, 2, 0, None), (2, 1, 0, 1), (1, 0, 0, None),
                (4, 1, 1, None), (2, 5, 1, None), (5, 4, 1, None),
            ],
            [
                DoomSector(0, 72, _tex8("FLOOR0_1"), _tex8("CEIL1_1"), 160, 0, 0),
                DoomSector(0, 192, _tex8("FLOOR0_1"), _tex8("F_SKY1"), 160, 0, 0),
            ],
            [DoomThing(64, 16, 0, 1, 7)],
        )
        approach = inspect_doom_space(doom, [0])
        dest = inspect_doom_space(doom, [1])
        self.assertEqual(approach["profile"]["id"], "player-profile:doom")
        self.assertEqual(approach["scale"]["aabb_width"]["player_widths"], round(128 / 32, 4))
        self.assertEqual(dest["enclosure"]["sky_exposure"], 1.0)
        self.assertEqual(approach["enclosure"]["sky_exposure"], 0.0)
        self.assertTrue(approach["movement"]["affordances"]["can_fit"])
        corpus = mine_doom_spatial_corpus([doom, fixture_basic_room()[1]])
        self.assertGreater(len(corpus["opening_width_player_widths"]), 0)
        self.assertEqual(corpus["game"], "doom")


class CompactPresentationTests(unittest.TestCase):
    def test_compact_view_omits_engine_coordinate_dumps(self):
        payload = inspect_space(_corridor_into_hall(), [1])
        compact = present_space(payload)
        dumped = json.dumps(compact)
        self.assertNotIn("16384", dumped)
        self.assertIn("player_widths", dumped)
        self.assertIn("sky_exposure", dumped)
        self.assertEqual(payload["scale"]["aabb_width"]["raw"], 16384)

    def test_cli_inspect_space_defaults_to_the_compact_view(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "pair.MAP"
            out_path = root / "space.json"
            write_map(synthetic_two_sector_map(), map_path)
            self.assertEqual(main(["inspect-space", str(map_path), "--sectors", "0", "-o", str(out_path)]), 0)
            compact = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(compact["kind"], "space")
            self.assertIn("movement", compact)
            self.assertNotIn("profile", compact)
            self.assertEqual(main(["inspect-space", str(map_path), "--sectors", "0", "--full", "-o", str(out_path)]), 0)
            full = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(full["width"] if False else full["scale"]["aabb_width"]["raw"], 1024)
            self.assertEqual(main(["player-profile", "--game", "blood", "-o", str(out_path)]), 0)
            profile = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(profile["body_width"], 384)
            self.assertEqual(main(["compare-space", str(map_path), "--from", "0", "--to", "1", "-o", str(out_path)]), 0)
            transition = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(transition["kind"], "transition")
            self.assertEqual(main(["inspect-connection", str(map_path), "--wall", "1", "-o", str(out_path)]), 0)
            opening = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertAlmostEqual(opening["width_player_widths"], 1024 / 384, places=3)

    def test_existing_spatial_sensor_thresholds_are_unchanged(self):
        analysis = analyze_spatial(synthetic_two_sector_map().to_build_ir())
        edge = analysis["views"]["traversability"]["walkable_at_rest"][0]
        self.assertGreaterEqual(edge["width"], 512)
        self.assertGreaterEqual(edge["at_rest_opening"], 4096)


class OriginalMapAuditTests(unittest.TestCase):
    def test_original_maps_yield_player_relative_descriptions_when_present(self):
        blood = Path("maps/blood/campaign/E1M1.MAP")
        duke = Path("maps/duke3d/E1L1.MAP")
        wad = Path("maps/doom/doom.wad")
        if not blood.is_file():
            self.skipTest("original Blood maps are not in this checkout")
        from bloodmap.format import read_map
        from bloodmap.duke import read_duke_map
        from bloodmap.doom import read_wad, wad_map

        build = read_map(blood).to_build_ir()
        analysis = analyze_spatial(build)
        openings = analysis["views"]["geometry"]["portals"]
        self.assertTrue(openings)
        narrow = min(openings, key=lambda item: item["width"])
        left, right = (int(ref.split(":", 1)[1]) for ref in narrow["sectors"])
        connection = inspect_connection(build, left=left, right=right)
        self.assertGreater(connection["width"]["player_widths"], 0)
        self.assertEqual(connection["width"]["raw"], narrow["width"])

        largest = max(analysis["views"]["geometry"]["sectors"], key=lambda item: item["area"])
        space = inspect_space(build, [int(largest["ref"].split(":", 1)[1])])
        self.assertGreater(space["scale"]["footprint"]["player_areas"], 0)
        self.assertIn("sky_exposure", space["enclosure"])

        if duke.is_file():
            duke_build = read_duke_map(duke).to_build_ir()
            duke_space = inspect_space(duke_build, [0])
            self.assertEqual(duke_space["profile"]["id"], "player-profile:duke3d")
            comparison = comparable_openings(
                ("blood", connection["width"]["raw"]),
                ("duke3d", duke_space["scale"]["aabb_width"]["raw"]),
            )
            self.assertEqual(len(comparison["openings"]), 2)

        if wad.is_file():
            doom = inspect_doom_space(wad_map(read_wad(wad), "E1M1"), [0])
            self.assertEqual(doom["profile"]["id"], "player-profile:doom")
            self.assertGreater(doom["scale"]["aabb_width"]["player_widths"], 0)
