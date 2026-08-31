"""Anchor-query regressions.

Two things are pinned. First, that the general path counts occurrences exactly
the way the two hand-written miners it replaces do -- otherwise "reproducible
through the new path" is a claim, not a fact. Second, that a map which cannot
be analysed is *reported*, never silently dropped: the first run of this tool
lost its two densest maps to a swallowed exception and said `0` without saying
why.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from bloodmap.anchors import (
    CONTEXT_FACETS,
    OBJECT_FACETS,
    AnchorError,
    anchor_from_material,
    anchor_from_regions,
    anchor_from_tiles,
    _enrichment,
    context_signature,
    find_occurrences,
    load_kit,
    mine_anchor,
    _map_signatures,
)
from bloodmap.format import encode_map, parse_map
from bloodmap.relations import extract_relations
from tests.helpers import corpus_map, synthetic_two_sector_map
from tests.test_relations import furnished_map


ROOT = Path(__file__).resolve().parents[1]
E6M1_REFERENCE = ROOT / "projects" / "blood-city" / "references" / "e6m1-shop.json"
SEWER_REFERENCE = ROOT / "projects" / "blood-city" / "references" / "sewer-kit.json"


def tiled_map():
    """A map using one tile as a wall, an over-wall, a floor, and a sprite."""
    disk = synthetic_two_sector_map()
    disk.walls[0].fields.update(picnum=900, over_picnum=900)   # two uses on one wall
    disk.walls[5].fields.update(picnum=900)
    disk.sectors[1].fields.update(floor_picnum=900, ceiling_picnum=900)
    disk.sprites[0].fields.update(picnum=900)
    return parse_map(encode_map(disk)).to_build_ir()


class OccurrenceTests(unittest.TestCase):
    def test_every_surface_a_tile_can_sit_on_is_searched(self):
        found = find_occurrences(tiled_map(), (900,))
        kinds = [(item["kind"], item["ref"], item["field"]) for item in found]
        self.assertIn(("wall", "wall:0", "picnum"), kinds)
        self.assertIn(("wall", "wall:0", "over_picnum"), kinds)
        self.assertIn(("wall", "wall:5", "picnum"), kinds)
        self.assertIn(("surface", "sector:1", "floor_picnum"), kinds)
        self.assertIn(("surface", "sector:1", "ceiling_picnum"), kinds)
        self.assertIn(("sprite", "sprite:0", "picnum"), kinds)

    def test_one_wall_carrying_the_tile_twice_is_two_uses(self):
        """The counting both hand-written miners do. If this changes, their
        reports stop being reproducible through this path."""
        found = find_occurrences(tiled_map(), (900,))
        self.assertEqual(sum(1 for item in found if item["ref"] == "wall:0"), 2)

    def test_carrying_sectors_are_recorded_for_every_kind(self):
        found = find_occurrences(tiled_map(), (900,))
        self.assertEqual({item["sector"] for item in found}, {0, 1})

    def test_an_absent_tile_finds_nothing(self):
        self.assertEqual(find_occurrences(tiled_map(), (4321,)), [])


class HandWrittenMinerEquivalenceTests(unittest.TestCase):
    """The general path must count exactly as the two scripts it replaces."""

    def test_it_agrees_with_the_sewer_kit_miner(self):
        from tools.mine_sewer_kit import sectors_for

        disk = parse_map(encode_map(_tiled_disk()))
        sectors, uses = sectors_for(disk, (900,))
        found = find_occurrences(disk.to_build_ir(), (900,))
        self.assertEqual(len(found), len(uses))
        self.assertEqual({item["sector"] for item in found}, sectors)

    def test_it_agrees_with_the_shop_miner(self):
        from tools.mine_e6m1_shop import _asset_occurrences, _wall_owner

        disk = parse_map(encode_map(_tiled_disk()))
        theirs = _asset_occurrences(disk, _wall_owner(disk), (900,))
        found = find_occurrences(disk.to_build_ir(), (900,))
        mine = {
            "sprites": sum(1 for item in found if item["kind"] == "sprite"),
            "walls": sum(1 for item in found if item["kind"] == "wall"),
            "surfaces": sum(1 for item in found if item["kind"] == "surface"),
        }
        self.assertEqual(mine, {key: len(value) for key, value in theirs.items()})


def _tiled_disk():
    disk = synthetic_two_sector_map()
    disk.walls[0].fields.update(picnum=900, over_picnum=900)
    disk.walls[5].fields.update(picnum=900)
    disk.sectors[1].fields.update(floor_picnum=900, ceiling_picnum=900)
    disk.sprites[0].fields.update(picnum=900)
    return disk


class AnchorSpecTests(unittest.TestCase):
    def test_tiles_are_deduplicated_and_sorted(self):
        spec = anchor_from_tiles("role", [7, 3, 7])
        self.assertEqual(spec.tiles, (3, 7))
        self.assertEqual(spec.origin, "explicit tiles")

    def test_an_empty_anchor_fails_closed(self):
        with self.assertRaises(AnchorError):
            anchor_from_tiles("role", [])

    def test_a_material_resolves_to_its_declared_surfaces(self):
        from bloodmap.surfaces import MATERIALS

        name = "nave"
        spec = anchor_from_material(name)
        found = MATERIALS[name]
        self.assertEqual(spec.name, f"material:{name}")
        self.assertIn(found.wall, spec.tiles)
        self.assertIn(found.floor, spec.tiles)
        self.assertIn("MATERIALS", spec.origin)

    def test_an_unknown_material_fails_closed_and_names_the_known_ones(self):
        with self.assertRaises(AnchorError) as caught:
            anchor_from_material("no-such-material")
        self.assertIn("nave", str(caught.exception))

    def test_example_regions_yield_the_tiles_those_regions_use(self):
        build = tiled_map()
        spec = anchor_from_regions(build, [1], name="example", source="synthetic")
        self.assertIn(900, spec.tiles)
        self.assertIn("sectors [1]", spec.origin)
        with self.assertRaises(AnchorError):
            anchor_from_regions(build, [99], name="oops")


class SignatureTests(unittest.TestCase):
    def setUp(self):
        self.build = furnished_map()

    def test_a_scale_one_signature_omits_facets_a_lone_sector_cannot_have(self):
        """A hops=0 neighborhood is one sector, so every neighbour relation is
        absent by construction. Reporting `portals:0` there would state an
        artefact of the selection as a fact about the map."""
        local = extract_relations(self.build, sectors=[0], hops=0)
        signature = context_signature(local, 0, facets=OBJECT_FACETS)
        for facet in CONTEXT_FACETS:
            self.assertNotIn(f"{facet}:", signature)
        for facet in OBJECT_FACETS:
            self.assertIn(f"{facet}:", signature)

    def test_a_full_signature_carries_every_facet(self):
        wider = extract_relations(self.build, sectors=[0], hops=1)
        signature = context_signature(wider, 0)
        for facet in CONTEXT_FACETS + OBJECT_FACETS:
            self.assertIn(f"{facet}:", signature)

    def test_the_signature_reads_the_neighbourhood_it_is_given(self):
        wider = extract_relations(self.build, sectors=[0], hops=1)
        facets = dict(part.split(":", 1) for part in context_signature(wider, 0).split("|"))
        self.assertEqual(facets["portals"], "1")
        self.assertEqual(facets["objects"], "3+")      # the row of three plus the flush one
        self.assertEqual(facets["run"], "yes")
        self.assertEqual(facets["wallbound"], "some")

    def test_an_unknown_facet_fails_closed(self):
        from bloodmap.relations import RelationError

        wider = extract_relations(self.build, sectors=[0], hops=1)
        with self.assertRaises(RelationError):
            context_signature(wider, 0, facets=("colour",))

    def test_a_signature_survives_translation_and_rotation(self):
        """Inherited from the Phase 1 relations, and worth pinning here: a
        signature that moved with the world frame would cluster by map."""
        wider = extract_relations(self.build, sectors=[0], hops=1)
        reference = context_signature(wider, 0)
        for turns in (1, 2, 3):
            with self.subTest(turns=turns):
                moved = copy.deepcopy(self.build)
                moved.rotate_quarter_turns(turns)
                moved.translate(8192, -4096)
                document = extract_relations(moved, sectors=[0], hops=1)
                self.assertEqual(context_signature(document, 0), reference)


class FailClosedTests(unittest.TestCase):
    def test_a_sector_that_will_not_compute_is_reported_with_its_reason(self):
        """`spatial.analyze_spatial` validates the whole map's wall ownership
        before any selection, so one malformed sector costs every local query on
        that map. That is a fact to report, not an exception to swallow."""
        build = furnished_map()
        build.sectors[1]["fields"]["wall_ptr"] = 9999
        signatures, failures = _map_signatures(build, [0], hops=1)
        self.assertEqual(signatures, {})
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["sector"], 0)
        self.assertTrue(failures[0]["error"])

    def test_a_healthy_map_reports_no_failures(self):
        signatures, failures = _map_signatures(furnished_map(), [0, 1], hops=1)
        self.assertEqual(failures, [])
        self.assertEqual(set(signatures), {0, 1})


class EnrichmentTests(unittest.TestCase):
    """The number that stops the tool believing its own dominant context."""

    def test_enrichment_is_the_ratio_of_the_two_shares(self):
        anchored = [{"scale_2": "A"}] * 3 + [{"scale_2": "B"}]
        others = [{"scale_2": "A"}] * 2 + [{"scale_2": "B"}] * 18
        found = _enrichment("A", anchored, others)
        self.assertEqual(found["anchored"], {"hits": 3, "of": 4, "share": 0.75})
        self.assertEqual(found["unanchored"], {"hits": 2, "of": 20, "share": 0.1})
        self.assertEqual(found["enrichment"], 7.5)

    def test_a_context_shared_with_everything_scores_about_one(self):
        anchored = [{"scale_2": "A"}] * 5
        others = [{"scale_2": "A"}] * 40
        self.assertEqual(_enrichment("A", anchored, others)["enrichment"], 1.0)

    def test_a_context_rarer_around_the_anchor_scores_below_one(self):
        anchored = [{"scale_2": "A"}, {"scale_2": "B"}, {"scale_2": "C"}, {"scale_2": "D"}]
        others = [{"scale_2": "A"}] * 10
        self.assertLess(_enrichment("A", anchored, others)["enrichment"], 1.0)

    def test_no_dominant_context_reports_no_signature(self):
        self.assertIsNone(_enrichment(None, [], [])["signature"])


class KitTests(unittest.TestCase):
    def test_a_report_with_a_role_table_can_drive_the_tool(self):
        import tempfile

        path = Path(tempfile.mkdtemp()) / "kit.json"
        path.write_text(json.dumps({"role_assets": {"thing": [900, 901]}}), encoding="utf-8")
        specs = load_kit(path)
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].name, "thing")
        self.assertEqual(specs[0].tiles, (900, 901))

    def test_a_file_without_a_role_table_fails_closed(self):
        import tempfile

        path = Path(tempfile.mkdtemp()) / "empty.json"
        path.write_text(json.dumps({"nothing": "here"}), encoding="utf-8")
        with self.assertRaises(AnchorError):
            load_kit(path)


class ReferenceReproductionTests(unittest.TestCase):
    """The Phase 2 exit criterion: the two reference reports as outputs."""

    def test_the_e6m1_shop_asset_counts_reproduce_exactly(self):
        path = corpus_map("E6M1.MAP")
        if not path.exists() or not E6M1_REFERENCE.exists():
            self.skipTest("E6M1.MAP or the e6m1-shop reference report is absent")
        from bloodmap.format import read_map

        reference = json.loads(E6M1_REFERENCE.read_text(encoding="utf-8"))
        build = read_map(path).to_build_ir()
        for role, tiles in reference["role_assets"].items():
            with self.subTest(role=role):
                found = find_occurrences(build, tiles)
                self.assertEqual(
                    {
                        "sprites": sum(1 for i in found if i["kind"] == "sprite"),
                        "walls": sum(1 for i in found if i["kind"] == "wall"),
                        "surfaces": sum(1 for i in found if i["kind"] == "surface"),
                    },
                    reference["asset_counts"][role],
                )

    def test_the_sewer_kit_densest_maps_reproduce_exactly(self):
        if not SEWER_REFERENCE.exists():
            self.skipTest("the sewer-kit reference report is absent")
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps

        maps = list_corpus_maps(population=None, view="reference")
        maps += list_corpus_maps(population="own-conversion")
        if not maps:
            self.skipTest("no local Blood corpus")
        reference = json.loads(SEWER_REFERENCE.read_text(encoding="utf-8"))
        loaded = [(item.name, read_map(item.path).to_build_ir()) for item in maps]
        for role, tiles in reference["role_assets"].items():
            rows = []
            for name, build in loaded:
                found = find_occurrences(build, tiles)
                if found:
                    rows.append((len(found), name, sorted({i["sector"] for i in found})))
            rows.sort(key=lambda row: (-row[0], row[1]))
            for index, example in enumerate(reference["roles"][role]["examples"][:3]):
                with self.subTest(role=role, rank=index):
                    self.assertEqual(rows[index][1], example["map"])
                    self.assertEqual(rows[index][0], example["uses"])
                    self.assertEqual(rows[index][2], example["affected_sectors"])

    def test_the_only_map_the_registry_withholds_is_a_working_file(self):
        """The hand-written miner globs `maps/blood/campaign/*.MAP` raw and so
        counts an editor autosave as a campaign map. The registry quarantines
        it, which is why `maps_with_use` differs by one for two sewer roles."""
        from bloodmap.patterns import list_corpus_maps, unadmitted_corpus_maps

        maps = list_corpus_maps(population=None, view="reference")
        if not maps:
            self.skipTest("no local Blood corpus")
        admitted = {item.name for item in maps}
        for item in unadmitted_corpus_maps():
            self.assertNotIn(item.name, admitted)


class AnchorMiningTests(unittest.TestCase):
    def test_an_anchor_query_reports_provenance_enrichment_and_skips(self):
        from bloodmap.patterns import list_corpus_maps

        if not list_corpus_maps(population="blood-campaign"):
            self.skipTest("no local Blood campaign maps")
        payload = mine_anchor(
            anchor_from_tiles("grate", (502,)),
            population=None, view="reference", top_maps=2, analogues=True,
        )
        self.assertGreater(payload["maps_with_use"], 0)
        self.assertLessEqual(len(payload["studied"]), 2)
        self.assertTrue(payload["dominant_context"]["signature"])
        self.assertIn("enrichment", payload["dominant_context"])
        for entry in payload["studied"]:
            self.assertGreater(entry["signatures_computed"], 0)
        for entry in payload["skipped_maps"]:
            self.assertTrue(entry["reason"], "a skipped map must say why")
        self.assertTrue(payload["limitations"])

    def test_an_anchor_nothing_uses_fails_closed(self):
        from bloodmap.patterns import list_corpus_maps

        if not list_corpus_maps(population="blood-campaign"):
            self.skipTest("no local Blood campaign maps")
        payload = mine_anchor(anchor_from_tiles("nothing", (65500,)),
                              population="blood-campaign", top_maps=1, analogues=False)
        self.assertEqual(payload["maps_with_use"], 0)
        self.assertIsNone(payload["dominant_context"]["signature"])
        self.assertEqual(payload["anchor_free_analogues"]["count"], 0)

    def test_an_unknown_population_fails_closed(self):
        with self.assertRaises(Exception):
            mine_anchor(anchor_from_tiles("x", (1,)), population="canonical")


if __name__ == "__main__":
    unittest.main()
