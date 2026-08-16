from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.art import (
    ArtTile, animation_families, decode_picanm, encode_picanm, feature_distance,
    read_art_directory, read_art_file, read_palette, tile_preview_png,
    transparency_stats, write_art_file, write_palette,
)
from bloodmap.doom_fixtures import fixture_basic_room
from bloodmap.format import encode_map, parse_map
from bloodmap.materials import (
    MaterialsError, detect_contradictions, dump_json, empty_ontology,
    export_classification_batch, families_from_evidence, finalize_catalog,
    import_annotations, import_ontology, mine_blood_map, mine_doom_map,
    new_catalog, ontology_aware_match, palette_vocabulary,
    rank_candidates, retrieve_palette, select_authoring_kit, select_representatives,
    similar_palettes, summarize_catalog, usage_prediction_heldout,
)
from tests.helpers import synthetic_two_sector_map


def _palette() -> list[tuple[int, int, int]]:
    colors = [(0, 0, 0)] * 256
    colors[1] = (200, 24, 24)
    colors[2] = (210, 30, 28)
    colors[3] = (20, 40, 200)
    colors[4] = (30, 180, 40)
    colors[5] = (180, 180, 180)
    return colors


def _solid(tile: int, color: int, width: int = 16, height: int = 16, picanm: int = 0) -> ArtTile:
    return ArtTile(tile, width, height, bytes([color]) * (width * height), picanm)


def _masked(tile: int, color: int, width: int = 16, height: int = 32) -> ArtTile:
    pixels = bytearray(width * height)
    for x in range(width):
        for y in range(height):
            pixels[x * height + y] = 255 if y % 2 == 0 else color
    return ArtTile(tile, width, height, bytes(pixels), 0)


def _write_art(directory: Path) -> dict[int, ArtTile]:
    tiles = {
        1: _solid(1, 1),
        2: _solid(2, 2),
        3: _solid(3, 3),
        4: _masked(4, 5),
        10: _solid(10, 4, picanm=encode_picanm(frames=2, type_id=2, speed=3)),
        11: _solid(11, 4),
        12: _solid(12, 4),
        20: _solid(20, 5, width=32, height=32),
        21: _solid(21, 5, width=32, height=16),
    }
    write_art_file(directory / "TILES000.ART", tiles)
    write_palette(directory / "TEST.PAL", _palette())
    return tiles


def _map_with_tiles(*, wall: int, floor: int, ceiling: int, over: int = -1, masked: bool = False) -> object:
    disk = synthetic_two_sector_map()
    for sector in disk.sectors:
        sector.fields["floor_picnum"] = floor
        sector.fields["ceiling_picnum"] = ceiling
    for wall_obj in disk.walls:
        wall_obj.fields["picnum"] = wall
        wall_obj.fields["over_picnum"] = over
        wall_obj.fields["x_repeat"] = 8
        wall_obj.fields["y_repeat"] = 8
    if masked:
        disk.walls[1].fields["cstat"] = 16 | 128
        disk.walls[1].fields["over_picnum"] = over
        disk.walls[7].fields["cstat"] = 16
        disk.walls[7].fields["over_picnum"] = over
    for sprite in disk.sprites:
        sprite.fields["picnum"] = 99
    return parse_map(encode_map(disk))


class ArtIdentityTests(unittest.TestCase):
    def test_picanm_roundtrip_and_transparency(self):
        packed = encode_picanm(frames=3, type_id=1, xofs=-4, yofs=7, speed=5, extra=2)
        info = decode_picanm(packed)
        self.assertEqual(info["frames"], 3)
        self.assertEqual(info["type"], "oscillate")
        self.assertEqual(info["xofs"], -4)
        self.assertEqual(info["yofs"], 7)
        self.assertEqual(info["speed"], 5)
        masked = _masked(4, 5)
        stats = transparency_stats(masked)
        self.assertTrue(stats["has_mask"])
        self.assertGreater(stats["transparent_ratio"], 0.4)
        self.assertFalse(transparency_stats(_solid(1, 1))["has_mask"])

    def test_art_file_roundtrip_preserves_animation_and_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tiles = _write_art(root)
            loaded = read_art_file(root / "TILES000.ART")
            self.assertEqual(loaded[10].picanm, tiles[10].picanm)
            self.assertEqual(loaded[4].pixels, tiles[4].pixels)
            self.assertEqual(read_art_directory(root)[1].width, 16)
            families = animation_families(loaded)
            self.assertEqual(len(families), 1)
            self.assertEqual(families[0]["members"], ["10", "11", "12"])
            self.assertEqual(families[0]["provenance"], "VERIFIED")
            png = tile_preview_png(loaded[1], tuple(_palette()))
            self.assertTrue(png.startswith(b"\x89PNG"))


class UsageMiningTests(unittest.TestCase):
    def test_usage_counts_and_masked_overpic_are_verified(self):
        catalog = new_catalog(games=["blood"])
        mine_blood_map(catalog, _map_with_tiles(wall=1, floor=20, ceiling=21, over=4, masked=True), map_name="A.MAP")
        mine_blood_map(catalog, _map_with_tiles(wall=2, floor=20, ceiling=21), map_name="B.MAP")
        finalize_catalog(catalog)
        wall = catalog["assets"]["blood:tile:1"]
        floor = catalog["assets"]["blood:tile:20"]
        grate = catalog["assets"]["blood:tile:4"]
        self.assertGreater(wall["usage"]["wall"], 0)
        self.assertEqual(wall["usage"]["floor"], 0)
        self.assertGreater(floor["usage"]["floor"], 0)
        self.assertEqual(floor["usage"]["wall"], 0)
        self.assertGreater(grate["usage"]["masked"], 0)
        self.assertGreater(grate["usage"]["overwall"], 0)
        self.assertEqual(wall["usage"]["maps"], 1)
        self.assertEqual(floor["usage"]["maps"], 2)
        self.assertTrue(all(item["kind"] != "exact" or "counts" in item for item in wall["distributions"].values()))
        self.assertLessEqual(len(wall["representatives"]), 8)

    def test_mixed_surface_use_is_measured_from_placement_shares(self):
        catalog = new_catalog(games=["blood"])
        walls = _map_with_tiles(wall=20, floor=20, ceiling=21)
        mine_blood_map(catalog, walls, map_name="MIX.MAP")
        finalize_catalog(catalog)
        tile = catalog["assets"]["blood:tile:20"]
        self.assertGreater(tile["usage"]["wall"], 0)
        self.assertGreater(tile["usage"]["floor"], 0)
        self.assertEqual(tile["status"], "mixed_use")

    def test_representative_sampling_covers_kinds_and_maps_not_every_hit(self):
        occurrences = []
        for index in range(40):
            occurrences.append({
                "map": f"M{index % 3}.MAP",
                "kind": "wall" if index % 5 else "overwall",
                "object": f"wall:{index}",
                "flags": {},
                "geometry": {"x_repeat": 8 if index < 30 else 64},
                "neighbors": [],
                "mechanism": index == 7,
                "moving_sector": False,
                "masked": index == 11,
                "translucent": False,
                "one_sided": False,
                "floor": "blood:tile:20",
                "ceiling": "blood:tile:21",
            })
        picked = select_representatives(occurrences, limit=8)
        self.assertEqual(len(picked), 8)
        self.assertTrue(any(item["masked"] for item in picked))
        self.assertTrue(any(item["mechanism"] for item in picked))
        self.assertGreaterEqual(len({item["map"] for item in picked}), 2)
        self.assertTrue(all(item.get("selected_because") for item in picked))
        self.assertTrue(any("masked" in item["selected_because"] for item in picked))

    def test_doom_named_textures_are_mined_without_numeric_ids_as_semantics(self):
        _semantic, doom, _blood = fixture_basic_room()
        catalog = new_catalog(games=["doom"])
        mine_doom_map(catalog, doom, map_name=doom.name)
        finalize_catalog(catalog)
        self.assertTrue(any(asset["game"] == "doom" for asset in catalog["assets"].values()))
        self.assertTrue(all(":" in ident and ident.split(":")[1] == "texture" for ident in catalog["assets"] if ident.startswith("doom:")))


class ClusterDeterminismTests(unittest.TestCase):
    def _catalog(self, names: list[str]):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tiles = _write_art(root)
            palette = tuple(_palette())
            catalog = new_catalog(games=["blood"])
            from bloodmap.materials import attach_appearance
            attach_appearance(catalog, "blood", tiles, palette, source=str(root))
            maps = {
                "A.MAP": _map_with_tiles(wall=1, floor=20, ceiling=21, over=4, masked=True),
                "B.MAP": _map_with_tiles(wall=2, floor=20, ceiling=21),
            }
            for name in names:
                mine_blood_map(catalog, maps[name], map_name=name)
            return finalize_catalog(catalog)

    def test_visual_and_usage_clusters_are_order_independent(self):
        first = self._catalog(["A.MAP", "B.MAP"])
        second = self._catalog(["B.MAP", "A.MAP"])
        def members(catalog, kind):
            return sorted(
                tuple(cluster["members"])
                for cluster in catalog["clusters"]
                if cluster["kind"] == kind
            )
        self.assertEqual(members(first, "visual"), members(second, "visual"))
        self.assertEqual(members(first, "usage"), members(second, "usage"))
        anim = [cluster for cluster in first["clusters"] if cluster["kind"] == "native_animation"]
        self.assertTrue(anim)
        self.assertEqual(anim[0]["provenance"], "VERIFIED")
        reds = {"blood:tile:1", "blood:tile:2"}
        self.assertTrue(any(reds <= set(cluster["members"]) for cluster in first["clusters"] if cluster["kind"] == "visual"))

    def test_numeric_adjacency_is_not_a_semantic_cluster_kind(self):
        catalog = self._catalog(["A.MAP"])
        self.assertFalse(any(cluster["kind"] == "numeric_adjacency" for cluster in catalog["clusters"]))


class OntologyImportTests(unittest.TestCase):
    def test_empty_ontology_has_no_preset_facets(self):
        ontology = empty_ontology()
        self.assertEqual(ontology["facets"], [])
        self.assertEqual(ontology["status"], "empty")

    def test_schema_version_and_truth_values_are_rejected(self):
        catalog = new_catalog()
        catalog["assets"]["blood:tile:1"] = {
            "id": "blood:tile:1", "game": "blood", "native_kind": "tile", "native_id": "1",
            "usage": {"wall": 4, "floor": 0, "ceiling": 0, "overwall": 0, "masked": 0,
                      "translucent": 0, "one_sided": 0, "two_sided": 0, "mechanism": 0,
                      "moving_sector": 0, "static": 4, "sprite": 0, "maps": 1, "total": 4},
            "status": "unannotated",
        }
        with self.assertRaisesRegex(MaterialsError, "truth value"):
            import_ontology(catalog, {"schema_version": 1, "facets": [{"id": "is_floor", "values": ["true"]}]})
        import_ontology(catalog, {
            "schema_version": 1,
            "facets": [{
                "id": "surface_applicability",
                "values": ["vertical", "horizontal", "unknown"],
                "basis": "usage distributions in the sample",
                "useful_for": ["usage_prediction"],
            }],
        })
        self.assertEqual(catalog["ontology"]["status"], "proposed")
        self.assertEqual(catalog["ontology"]["facets"][0]["provenance"], "INTERPRETED")
        with self.assertRaisesRegex(MaterialsError, "cannot be VERIFIED"):
            import_annotations(catalog, {
                "annotations": [{
                    "asset": "blood:tile:1",
                    "provenance": "VERIFIED",
                    "values": {"surface_applicability": "vertical"},
                }],
            })
        with self.assertRaisesRegex(MaterialsError, "truth values"):
            import_annotations(catalog, {
                "annotations": [{
                    "asset": "blood:tile:1",
                    "provenance": "INTERPRETED",
                    "values": {"player_start_valid": True},
                }],
            })

    def test_unknown_and_contradiction_are_first_class(self):
        catalog = new_catalog()
        catalog["assets"]["blood:tile:3"] = {
            "id": "blood:tile:3", "game": "blood", "native_kind": "tile", "native_id": "3",
            "usage": {"wall": 0, "floor": 6, "ceiling": 0, "overwall": 0, "masked": 0,
                      "translucent": 0, "one_sided": 0, "two_sided": 0, "mechanism": 0,
                      "moving_sector": 0, "static": 6, "sprite": 0, "maps": 1, "total": 6},
            "status": "unannotated",
            "appearance": None,
        }
        import_ontology(catalog, {
            "facets": [{"id": "architectural_role", "values": ["floor_surface", "wall_surface", "unknown"]}],
        })
        import_annotations(catalog, {
            "annotations": [{
                "asset": "blood:tile:3",
                "provenance": "INTERPRETED",
                "status": "annotated",
                "values": {"architectural_role": "wall_surface"},
                "basis": "looked metallic in preview",
            }],
        })
        hits = detect_contradictions(catalog)
        self.assertTrue(any("never used on walls" in item["reason"] for item in hits))
        catalog["assets"]["blood:tile:3"]["status"] = "unknown"
        catalog["annotations"]["blood:tile:3"]["status"] = "unknown"
        catalog["annotations"]["blood:tile:3"]["values"]["architectural_role"]["value"] = "unknown"
        self.assertEqual(catalog["annotations"]["blood:tile:3"]["status"], "unknown")


class RetrievalAndExperimentTests(unittest.TestCase):
    def test_usage_outranks_visual_lookalikes_for_cross_game_selection(self):
        catalog = new_catalog(games=["duke3d", "blood"])
        feature_red = [0.0, 4.0, 0.8, 0.1, 0.1, 0.2] + [0.0] * 24
        feature_red_wall = list(feature_red)
        feature_red_wall[2] = 0.82
        catalog["assets"] = {
            "duke3d:tile:9": {
                "id": "duke3d:tile:9", "game": "duke3d", "native_id": "9", "status": "unannotated",
                "usage": {"wall": 0, "floor": 12, "ceiling": 0, "overwall": 0, "masked": 0,
                          "translucent": 0, "one_sided": 0, "two_sided": 12, "mechanism": 0,
                          "moving_sector": 0, "static": 12, "sprite": 0, "total": 12, "maps": 2},
                "appearance": {"feature": feature_red},
            },
            "blood:tile:100": {
                "id": "blood:tile:100", "game": "blood", "native_id": "100", "status": "unannotated",
                "usage": {"wall": 20, "floor": 0, "ceiling": 0, "overwall": 0, "masked": 0,
                          "translucent": 0, "one_sided": 0, "two_sided": 20, "mechanism": 0,
                          "moving_sector": 0, "static": 20, "sprite": 0, "total": 20, "maps": 3},
                "appearance": {"feature": feature_red_wall},
            },
            "blood:tile:200": {
                "id": "blood:tile:200", "game": "blood", "native_id": "200", "status": "unannotated",
                "usage": {"wall": 0, "floor": 18, "ceiling": 1, "overwall": 0, "masked": 0,
                          "translucent": 0, "one_sided": 0, "two_sided": 19, "mechanism": 0,
                          "moving_sector": 0, "static": 19, "sprite": 0, "total": 19, "maps": 3},
                "appearance": {"feature": [0.1, 4.1, 0.4, 0.4, 0.2, 0.3] + [0.0] * 24},
            },
        }
        ranked = rank_candidates(catalog["assets"]["duke3d:tile:9"], catalog["assets"].values())
        self.assertEqual(ranked[0]["asset"], "blood:tile:200")
        self.assertGreater(ranked[0]["usage_cosine"], ranked[1]["usage_cosine"])
        visual_only = feature_distance(
            tuple(catalog["assets"]["duke3d:tile:9"]["appearance"]["feature"]),
            tuple(catalog["assets"]["blood:tile:100"]["appearance"]["feature"]),
        )
        visual_floor = feature_distance(
            tuple(catalog["assets"]["duke3d:tile:9"]["appearance"]["feature"]),
            tuple(catalog["assets"]["blood:tile:200"]["appearance"]["feature"]),
        )
        self.assertLess(visual_only, visual_floor)

    def test_batch_export_import_and_contact_sheet_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tiles = _write_art(root)
            palette = tuple(_palette())
            catalog = new_catalog(games=["blood"])
            from bloodmap.materials import attach_appearance, contact_sheet_html
            attach_appearance(catalog, "blood", tiles, palette)
            mine_blood_map(catalog, _map_with_tiles(wall=1, floor=20, ceiling=21, over=4, masked=True), map_name="A.MAP")
            finalize_catalog(catalog)
            batch = export_classification_batch(
                catalog, tiles={"blood": tiles}, palettes={"blood": palette}, limit=10,
            )
            self.assertEqual(batch["$schema"], "llmapper.material-classification-batch")
            self.assertTrue(batch["assets"])
            self.assertIn("instruction", batch)
            dump_json(root / "batch.json", batch)
            loaded = json.loads((root / "batch.json").read_text(encoding="utf-8"))
            self.assertEqual(loaded["schema_version"], 1)
            import_ontology(catalog, {
                "facets": [{
                    "id": "rendering_behavior",
                    "values": ["opaque", "masked", "unknown"],
                    "useful_for": ["substitution"],
                }],
            })
            import_annotations(catalog, {
                "annotations": [
                    {
                        "asset": "blood:tile:4",
                        "provenance": "INTERPRETED",
                        "status": "annotated",
                        "values": {"rendering_behavior": "masked"},
                        "basis": "transparent pixels plus masked overwall usage",
                    },
                    {
                        "asset": "blood:tile:1",
                        "provenance": "INTERPRETED",
                        "status": "annotated",
                        "values": {"rendering_behavior": "opaque"},
                    },
                ],
            })
            html = contact_sheet_html(catalog, tiles={"blood": tiles}, palettes={"blood": palette})
            self.assertIn("blood:tile:1", html)
            self.assertIn("cluster:", html)
            prediction = usage_prediction_heldout(catalog)
            self.assertGreaterEqual(prediction["assets"], 1)
            families = families_from_evidence(catalog)
            self.assertTrue(any(item["kind"] == "native_animation" for item in families))
            palettes = retrieve_palette(catalog, like="blood:tile:1")
            self.assertTrue(palettes)
            summary = summarize_catalog(catalog)
            self.assertEqual(summary["ontology_status"], "proposed")
            self.assertIn("rendering_behavior", summary["ontology_facets"])


class CorpusSkipTests(unittest.TestCase):
    def test_local_corpus_mining_is_optional(self):
        maps = Path(__file__).resolve().parents[1] / "maps" / "blood"
        if not list(maps.glob("*.MAP")):
            self.skipTest("no local Blood MAP corpus")
        catalog = new_catalog(games=["blood"])
        from bloodmap.format import read_map
        path = next(iter(sorted(maps.glob("*.MAP"))))
        mine_blood_map(catalog, read_map(path), map_name=path.name)
        finalize_catalog(catalog)
        self.assertGreater(summarize_catalog(catalog)["assets"], 0)
        self.assertGreater(summarize_catalog(catalog)["substantial_usage"], 0)


class OntologyDiscoverySupportTests(unittest.TestCase):
    def test_unused_art_is_appearance_only_not_a_usage_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tiles = _write_art(root)
            catalog = new_catalog(games=["blood"])
            from bloodmap.materials import attach_appearance, query_materials, render_occurrence_context_svg
            attach_appearance(catalog, "blood", tiles, tuple(_palette()))
            mine_blood_map(catalog, _map_with_tiles(wall=1, floor=20, ceiling=21), map_name="A.MAP")
            finalize_catalog(catalog)
            unused = catalog["assets"]["blood:tile:10"]
            self.assertEqual(unused["status"], "appearance_only")
            self.assertEqual(unused["world_scale"]["status"], "appearance_only")
            used = catalog["assets"]["blood:tile:1"]
            self.assertIn("world_scale", used)
            self.assertTrue(used["representatives"][0].get("selected_because"))

    def test_review_sample_is_stratified_and_query_requires_imported_facets(self):
        from bloodmap.materials import attach_appearance, query_materials, select_review_sample
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tiles = _write_art(root)
            catalog = new_catalog(games=["blood"])
            attach_appearance(catalog, "blood", tiles, tuple(_palette()))
            mine_blood_map(catalog, _map_with_tiles(wall=1, floor=20, ceiling=21, over=4, masked=True), map_name="A.MAP")
            mine_blood_map(catalog, _map_with_tiles(wall=1, floor=20, ceiling=21), map_name="B.MAP")
            finalize_catalog(catalog)
            sample = select_review_sample(catalog, limit=20)
            self.assertIn("blood:tile:1", sample)
            self.assertTrue(any(catalog["assets"][ident]["status"] == "appearance_only" for ident in sample))
            import_ontology(catalog, {
                "version": "v1",
                "facets": [{
                    "id": "surface_applicability",
                    "values": ["vertical", "horizontal", "unknown"],
                    "useful_for": ["retrieval"],
                }],
            })
            import_annotations(catalog, {
                "annotations": [{
                    "asset": "blood:tile:1",
                    "provenance": "INTERPRETED",
                    "values": {"surface_applicability": "vertical"},
                }],
            })
            import_ontology(catalog, {
                "version": "v2",
                "status": "refined",
                "facets": [{
                    "id": "surface_applicability",
                    "values": ["vertical", "horizontal", "unknown"],
                    "useful_for": ["retrieval"],
                }],
            })
            self.assertEqual(catalog["ontology"]["version"], "v2")
            self.assertEqual(catalog["ontology_history"][0]["version"], "v1")
            hits = query_materials(catalog, require={"surface_applicability": "vertical"})
            self.assertEqual(hits[0]["asset"], "blood:tile:1")
            with self.assertRaisesRegex(MaterialsError, "not in the imported ontology"):
                query_materials(catalog, require={"made_up_facet": "stone"})

    def test_context_svg_highlights_the_selected_wall(self):
        from bloodmap.materials import render_occurrence_context_svg
        disk = _map_with_tiles(wall=1, floor=20, ceiling=21)
        svg = render_occurrence_context_svg(disk, {
            "map": "A.MAP", "kind": "wall", "object": "wall:1",
        })
        self.assertIn("<svg", svg)
        self.assertIn("wall:1", svg)
        self.assertIn("#ffcc66", svg)

    def test_vertical_label_on_ceiling_only_asset_is_a_contradiction(self):
        catalog = new_catalog()
        catalog["assets"]["blood:tile:9"] = {
            "id": "blood:tile:9", "game": "blood", "native_kind": "tile", "native_id": "9",
            "usage": {"wall": 0, "floor": 0, "ceiling": 12, "overwall": 0, "masked": 0,
                      "translucent": 0, "one_sided": 0, "two_sided": 0, "mechanism": 0,
                      "moving_sector": 0, "static": 12, "sprite": 0, "maps": 2, "total": 12},
            "status": "unannotated",
        }
        catalog["assets"]["blood:tile:10"] = {
            "id": "blood:tile:10", "game": "blood", "native_kind": "tile", "native_id": "10",
            "usage": {"wall": 0, "floor": 0, "ceiling": 0, "overwall": 0, "masked": 0,
                      "translucent": 0, "one_sided": 0, "two_sided": 0, "mechanism": 0,
                      "moving_sector": 0, "static": 0, "sprite": 0, "maps": 0, "total": 0},
            "status": "appearance_only",
        }
        import_annotations(catalog, {
            "facets": [{
                "id": "surface_applicability",
                "values": ["vertical", "horizontal_ceiling", "unknown"],
            }],
            "annotations": [
                {
                    "asset": "blood:tile:9",
                    "provenance": "INTERPRETED",
                    "values": {"surface_applicability": "vertical"},
                    "basis": "looked like a tall wall strip",
                },
                {
                    "asset": "blood:tile:10",
                    "provenance": "INTERPRETED",
                    "status": "annotated",
                    "values": {"surface_applicability": "vertical"},
                    "basis": "unused frame classified from pixels",
                },
            ],
        })
        reasons = [item["reason"] for item in catalog["contradictions"]]
        self.assertTrue(any("never a wall" in reason for reason in reasons))
        self.assertTrue(any("appearance-only" in reason for reason in reasons))

    def test_authoring_kit_and_palette_vocabulary_use_imported_facets(self):
        catalog = new_catalog()
        for ident, native, wall, floor, ceiling in (
            ("blood:tile:1", 1, 10, 0, 0),
            ("blood:tile:2", 2, 0, 8, 0),
            ("blood:tile:3", 3, 1, 1, 6),
        ):
            catalog["assets"][ident] = {
                "id": ident, "game": "blood", "native_kind": "tile", "native_id": str(native),
                "usage": {"wall": wall, "floor": floor, "ceiling": ceiling, "overwall": 0, "masked": 0,
                          "translucent": 0, "one_sided": 0, "two_sided": 0, "mechanism": 0,
                          "moving_sector": 0, "static": wall + floor + ceiling, "sprite": 0,
                          "maps": 1, "total": wall + floor + ceiling},
                "status": "unannotated",
            }
        catalog["palettes"] = [{
            "id": "palette:blood:A.MAP:0", "map": "A.MAP", "sector_count": 3,
            "floor": "blood:tile:2", "ceiling": "blood:tile:3", "walls": ["blood:tile:1"],
        }]
        import_annotations(catalog, {
            "version": "v2",
            "facets": [{
                "id": "surface_applicability",
                "values": ["vertical", "horizontal_floor", "horizontal_ceiling"],
            }],
            "annotations": [
                {"asset": "blood:tile:1", "provenance": "INTERPRETED",
                 "values": {"surface_applicability": "vertical"}},
                {"asset": "blood:tile:2", "provenance": "INTERPRETED",
                 "values": {"surface_applicability": "horizontal_floor"}},
                {"asset": "blood:tile:3", "provenance": "INTERPRETED",
                 "values": {"surface_applicability": "horizontal_ceiling"}},
            ],
        })
        kit = select_authoring_kit(catalog, {
            "wall": {"surface_applicability": "vertical"},
            "floor": {"surface_applicability": "horizontal_floor"},
        })
        self.assertEqual(kit["roles"]["wall"]["chosen_tile"], 1)
        self.assertEqual(kit["roles"]["floor"]["chosen_tile"], 2)
        vocab = palette_vocabulary(catalog, ["blood:tile:1", "blood:tile:2"])
        self.assertEqual(vocab["facet_counts"][0]["facet"], "surface_applicability")
        similar = similar_palettes(catalog, ["blood:tile:1", "blood:tile:2"])
        self.assertEqual(similar[0]["map"], "A.MAP")
        ranked = ontology_aware_match(
            catalog,
            source=catalog["assets"]["blood:tile:1"],
            require={"surface_applicability": "horizontal_ceiling"},
        )
        self.assertEqual(ranked[0]["asset"], "blood:tile:3")

    def test_reviewed_blood_ontology_v2_is_inspectable(self):
        payload = json.loads(
            (Path(__file__).resolve().parents[1] / "knowledge" / "blood" / "ontology-v2.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["version"], "v2")
        self.assertEqual(payload["revision_of"], "v1")
        self.assertEqual(payload["status"], "refined")
        facet_ids = [facet["id"] for facet in payload["facets"]]
        self.assertEqual(facet_ids, [
            "placement_kind", "surface_applicability", "rendering_behavior",
            "architectural_role", "interaction_role", "scale_behavior", "visual_material",
        ])
        self.assertTrue(any(item["id"] == "is_door" for item in payload["rejected_distinctions"]))
        self.assertFalse(any(
            annotation.get("provenance") == "VERIFIED" for annotation in payload["annotations"]
        ))
        sky = next(item for item in payload["annotations"] if item["asset"] == "blood:tile:2500")
        self.assertEqual(sky["values"]["surface_applicability"], "sky_parallax")
        unused = next(item for item in payload["annotations"] if item["asset"] == "blood:tile:1000")
        self.assertEqual(unused["status"], "appearance_only")


if __name__ == "__main__":
    unittest.main()
