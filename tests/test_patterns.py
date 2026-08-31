"""Design-pattern observation and retrieval regressions."""

from __future__ import annotations

import unittest

import copy

from bloodmap.patterns import (
    OBJECT_AREA_BANDS,
    OBJECT_HEIGHT_BANDS,
    _object_context_signature,
    classify_map_population,
    cluster_samples,
    observe_object_context,
    observe_spawn_neighborhoods,
    query_catalog,
)
from bloodmap.format import encode_map, parse_map
from tests.helpers import synthetic_two_sector_map
from tests.test_exposure import field_and_closet_map


def furnished_disk():
    """One sector holding three floor objects and one wall-bound one; the
    other sector empty. The empty sector must not be sampled."""
    disk = synthetic_two_sector_map()
    template = copy.deepcopy(disk.sprites[0])
    floor_z = int(disk.sectors[0].fields["floor_z"])
    sprites = []
    for index, x in enumerate((400, 512, 624)):
        sprite = copy.deepcopy(template)
        sprite.fields.update(x=x, y=512, z=floor_z, sector=0, picnum=700,
                             type=0, cstat=0, angle=0, index=index, extra=-1,
                             owner=-1)
        sprite.extra = None
        sprites.append(sprite)
    flush = copy.deepcopy(template)
    flush.fields.update(x=512, y=20, z=floor_z, sector=0, picnum=701,
                        type=0, cstat=0, angle=512, index=3, extra=-1, owner=-1)
    flush.extra = None
    sprites.append(flush)
    disk.sprites = sprites
    disk.header["num_sprites"] = len(sprites)
    return parse_map(encode_map(disk))


def wired_disk():
    """A furnished room, plus an unreachable closet holding only sound markers.

    Sector 1 is sealed (its portal is unlinked) and every sprite in it is a
    `kSoundSector` marker. Both exclusion reasons in one fixture.
    """
    disk = synthetic_two_sector_map()
    disk.walls[1].fields.update(next_wall=-1, next_sector=-1)
    disk.walls[7].fields.update(next_wall=-1, next_sector=-1)
    template = copy.deepcopy(disk.sprites[0])
    floor_z = int(disk.sectors[0].fields["floor_z"])
    sprites = []
    for index, x in enumerate((400, 512, 624)):
        sprite = copy.deepcopy(template)
        sprite.fields.update(x=x, y=512, z=floor_z, sector=0, picnum=700,
                             type=0, cstat=0, angle=0, index=index, extra=-1, owner=-1)
        sprite.extra = None
        sprites.append(sprite)
    for index in range(2):
        sprite = copy.deepcopy(template)
        sprite.fields.update(x=1400 + 128 * index, y=512, z=floor_z, sector=1,
                             picnum=2520, type=709, cstat=32896, angle=0,
                             index=3 + index, extra=-1, owner=-1)
        sprite.extra = None
        sprites.append(sprite)
    disk.sprites = sprites
    disk.header["num_sprites"] = len(sprites)
    return parse_map(encode_map(disk))


class ObjectContextHygieneTests(unittest.TestCase):
    """Off-map geometry and wiring are labelled and excluded by default."""

    def setUp(self):
        self.samples = observe_object_context(
            wired_disk(), map_id="wired.MAP", population="blood-campaign")
        self.by_sector = {item["focus"]["sector"]: item for item in self.samples}

    def test_both_sectors_are_still_sampled(self):
        """Labelling, not dropping: the wiring closet keeps its sample."""
        self.assertEqual(sorted(self.by_sector), [0, 1])

    def test_the_furnished_room_is_in_the_default_scope(self):
        room = self.by_sector[0]
        self.assertEqual(room["scope"], "default")
        self.assertEqual(room["excluded_because"], [])
        self.assertEqual(room["scale"]["objects"], 3)
        self.assertEqual(room["scale"]["objects_wiring"], 0)

    def test_the_wiring_closet_is_excluded_and_says_why(self):
        closet = self.by_sector[1]
        self.assertEqual(closet["scope"], "excluded")
        self.assertEqual(closet["scale"]["objects"], 0)
        self.assertEqual(closet["scale"]["objects_all"], 2)
        self.assertEqual(closet["scale"]["objects_wiring"], 2)
        self.assertTrue(closet["excluded_because"])
        self.assertTrue(any("wiring" in reason for reason in closet["excluded_because"]))

    def test_every_sample_carries_its_reachability_kind(self):
        for sample in self.samples:
            self.assertIn(sample["sector_kind"],
                          ("reachable", "logic_closet", "signature", "helper",
                           "bare", "sealed", "unknown"))
        self.assertEqual(self.by_sector[0]["sector_kind"], "reachable")
        self.assertNotEqual(self.by_sector[1]["sector_kind"], "reachable")

    def test_the_signature_counts_visible_objects_only(self):
        self.assertIn("objects:3+", _object_context_signature(self.by_sector[0]))
        self.assertIn("objects:0", _object_context_signature(self.by_sector[1]))

    def test_clustering_keeps_the_excluded_under_their_own_heading(self):
        clustered = cluster_samples(self.samples)
        default = [c for c in clustered["candidates"] if c["subject"] == "object-context"]
        self.assertEqual(len(default), 1)
        self.assertEqual(default[0]["occurrence_count"], 1)
        self.assertEqual(clustered["scope"]["default_samples"], 1)
        self.assertEqual(clustered["scope"]["excluded_samples"], 1)
        self.assertEqual(len(clustered["excluded_candidates"]), 1)
        excluded = clustered["excluded_candidates"][0]
        self.assertEqual(excluded["status"], "excluded-from-default-statistics")
        self.assertTrue(excluded["reasons"])
        self.assertTrue(excluded["sector_kinds"])

    def test_an_excluded_sample_is_keyed_on_what_it_does_hold(self):
        """Keyed on the visible objects it lacks, every sound-marker pocket in
        the campaign files under one meaningless `objects:0` bucket."""
        closet = self.by_sector[1]
        self.assertIn("wiring_signature", closet)
        self.assertIn("objects:0", closet["context_signature"])
        self.assertNotIn("objects:0", closet["wiring_signature"])
        self.assertEqual(closet["wiring_categories"], {"sound": 2})

    def test_a_default_sample_has_no_wiring_signature(self):
        self.assertNotIn("wiring_signature", self.by_sector[0])
        self.assertNotIn("wiring_categories", self.by_sector[0])

    def test_excluded_clusters_report_what_they_hold_and_how_they_were_keyed(self):
        clustered = cluster_samples(self.samples)
        excluded = clustered["excluded_candidates"][0]
        self.assertEqual(excluded["keyed_on"], "wiring")
        self.assertEqual(excluded["wiring_categories"], {"sound": 2})
        self.assertNotIn("objects:0", excluded["signature"])

    def test_two_wiring_pockets_with_the_same_shape_cluster_together(self):
        """The point of keying on the wiring: recurrence becomes visible."""
        first = observe_object_context(wired_disk(), map_id="a.MAP",
                                       population="blood-campaign")
        second = observe_object_context(wired_disk(), map_id="b.MAP",
                                        population="blood-campaign")
        clustered = cluster_samples(first + second)
        excluded = clustered["excluded_candidates"]
        self.assertEqual(len(excluded), 1, "the two pockets must be one candidate")
        self.assertEqual(excluded[0]["occurrence_count"], 2)
        self.assertEqual(excluded[0]["map_count"], 2)

    def test_reachability_is_computed_once_per_map(self):
        """A whole-map flood fill per sample would cost more than every
        relation extraction put together."""
        import bloodmap.reachability as reachability

        calls = []
        original = reachability.analyze_reachability
        reachability.analyze_reachability = lambda disk: calls.append(1) or original(disk)
        try:
            observe_object_context(wired_disk(), map_id="wired.MAP",
                                   population="blood-campaign")
        finally:
            reachability.analyze_reachability = original
        self.assertEqual(len(calls), 1, f"analyze_reachability ran {len(calls)} times")


class ObjectContextFamilyTests(unittest.TestCase):
    """The Phase 3 object-scale family, in the existing pipeline's idiom."""

    def setUp(self):
        self.samples = observe_object_context(
            furnished_disk(), map_id="synthetic.MAP", population="blood-campaign")

    def test_only_sectors_that_hold_objects_are_sampled(self):
        self.assertEqual([item["focus"]["sector"] for item in self.samples], [0])

    def test_a_sample_carries_its_subject_provenance_and_evidence(self):
        sample = self.samples[0]
        self.assertEqual(sample["subject"], "object-context")
        self.assertEqual(sample["population"], "blood-campaign")
        self.assertEqual(sample["map"], "synthetic.MAP")
        self.assertEqual(sample["scale"]["objects"], 4)
        self.assertTrue(sample["evidence"])
        self.assertIn("relations.context_signature (visible objects only)",
                      sample["evidence"])
        self.assertIn("reachability.sector_kinds", sample["evidence"])
        self.assertEqual(sample["sector_kind"], "reachable")
        self.assertEqual(sample["scope"], "default")

    def test_the_signature_is_the_relation_context_plus_two_scale_bands(self):
        signature = _object_context_signature(self.samples[0])
        self.assertTrue(signature.startswith(self.samples[0]["context_signature"]))
        facets = dict(part.split(":", 1) for part in signature.split("|"))
        self.assertIn(facets["size"], {label for _edge, label in OBJECT_AREA_BANDS})
        self.assertIn(facets["clear"], {label for _edge, label in OBJECT_HEIGHT_BANDS})
        self.assertEqual(facets["run"], "yes")        # the evenly spaced row of three

    def test_every_band_label_is_reachable(self):
        """Bands calibrated to corpus quartiles. A band nothing can land in
        would silently collapse the family; the first guessed height bands put
        nearly every campaign sector in one bucket."""
        sample = copy.deepcopy(self.samples[0])
        seen_size, seen_clear = set(), set()
        for area in (1.0, 8.0, 30.0, 500.0):
            for height in (1.0, 1.8, 3.0, 9.0):
                sample["scale"]["area_player_areas"] = area
                sample["scale"]["clear_height_player_heights"] = height
                facets = dict(p.split(":", 1) for p in _object_context_signature(sample).split("|"))
                seen_size.add(facets["size"])
                seen_clear.add(facets["clear"])
        self.assertEqual(seen_size, {label for _edge, label in OBJECT_AREA_BANDS})
        self.assertEqual(seen_clear, {label for _edge, label in OBJECT_HEIGHT_BANDS})

    def test_the_family_clusters_through_the_existing_pipeline(self):
        clustered = cluster_samples(self.samples)
        found = [c for c in clustered["candidates"] if c["subject"] == "object-context"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["occurrence_count"], 1)
        self.assertEqual(found[0]["status"], "unsigned")
        self.assertTrue(found[0]["candidate_id"].startswith("candidate:object-context:"))

    def test_the_family_reaches_observe_map(self):
        """The integration point: `pattern-mine` only sees this family because
        `observe_map` calls it."""
        import tempfile
        from pathlib import Path

        from bloodmap.format import write_map
        from bloodmap.patterns import observe_map

        path = Path(tempfile.mkdtemp()) / "FURNISHED.MAP"
        write_map(furnished_disk(), path)
        subjects = {item["subject"] for item in observe_map(path, population="blood-campaign")}
        self.assertIn("object-context", subjects)

    def test_the_signature_does_not_move_with_the_world_frame(self):
        reference = _object_context_signature(self.samples[0])
        disk = furnished_disk()
        build = disk.to_build_ir()
        for turns in (1, 2, 3):
            with self.subTest(turns=turns):
                moved = copy.deepcopy(build)
                moved.rotate_quarter_turns(turns)
                moved.translate(8192, -4096)
                samples = observe_object_context(
                    moved.to_native_disk_map(), map_id="moved.MAP",
                    population="blood-campaign")
                self.assertEqual(_object_context_signature(samples[0]), reference)


class PatternPopulationTests(unittest.TestCase):
    def test_filename_provenance_is_not_mixed(self):
        """Loose paths still classify by filename. Directory-resolved corpus
        provenance is pinned in `tests/test_corpus_registry.py`."""
        self.assertEqual(classify_map_population("maps/blood/campaign/multiplayer/BB6.MAP"), "blood-bloodbath")
        self.assertEqual(classify_map_population("maps/blood/campaign/E1M1.MAP"), "blood-campaign")
        # Owner correction 2026-08-31: Death Wish is a hand-picked community
        # source set, not a conversion. Only DNE* are conversions.
        self.assertEqual(classify_map_population("maps/blood/curated/DWE1M1.MAP"), "community-curated")
        self.assertEqual(classify_map_population("maps/blood/curated/TEDE1M9.MAP"), "community-curated")
        self.assertEqual(classify_map_population("maps/blood/conversions/DNE3L1.MAP"), "own-conversion")
        self.assertEqual(classify_map_population("work/BB2-semantic-reconstruction-v3.MAP"), "generated")
        self.assertEqual(classify_map_population("work/BB6-pattern-reconstruction-v1.MAP"), "generated")
        self.assertEqual(classify_map_population("work/E1M1-BLOOD.MAP"), "generated")


class PatternObservationTests(unittest.TestCase):
    def test_field_and_closet_spawns_get_different_signatures(self):
        samples = observe_spawn_neighborhoods(
            field_and_closet_map(), map_id="synthetic.MAP", population="blood-bloodbath",
        )
        self.assertEqual(len(samples), 2)
        clustered = cluster_samples(samples)
        spawn = [item for item in clustered["candidates"] if item["subject"] == "spawn-neighborhood"]
        self.assertGreaterEqual(len(spawn), 2)
        signatures = {item["signature"] for item in spawn}
        self.assertGreaterEqual(len(signatures), 2)

    def test_query_returns_multiple_hits(self):
        catalog = {
            "patterns": [
                {
                    "id": "pattern:spawn:test-a",
                    "subject": "spawn-neighborhood",
                    "population": "blood-bloodbath",
                    "signature": "sky:1|hops:0|exits:3+",
                    "tags": ["open-field"],
                    "interpretation": {"label": "open field spawn"},
                    "occurrences": [
                        {"map": "BB1.MAP", "focus": {"sector": 1}},
                        {"map": "BB6.MAP", "focus": {"sector": 4}},
                    ],
                }
            ]
        }
        hits = query_catalog(catalog, view="spawn-neighborhood", require={"hops": "0"}, limit=8)
        self.assertEqual(len(hits), 2)
        catalog["patterns"].append({
            "id": "pattern:spawn:test-b",
            "subject": "spawn-neighborhood",
            "match": {"hops": "0", "sky": "0"},
            "interpretation": {"label": "covered zero hops"},
            "occurrences": [{"map": "BB2.MAP", "focus": {"sector": 2}}],
        })
        mixed = query_catalog(catalog, view="spawn-neighborhood", require={"hops": "0"}, limit=3)
        self.assertEqual({item["pattern_id"] for item in mixed}, {"pattern:spawn:test-a", "pattern:spawn:test-b"})

    def test_one_sample_can_match_overlapping_hypotheses(self):
        samples = observe_spawn_neighborhoods(
            field_and_closet_map(), map_id="synthetic.MAP", population="blood-bloodbath",
        )
        clustered = cluster_samples(samples)
        catalog = {
            "medians": clustered["medians"],
            "patterns": [
                {
                    "id": "pattern:spawn:sky-or-field",
                    "subject": "spawn-neighborhood",
                    "population": "blood-bloodbath",
                    "match": {"sky": "1"},
                    "interpretation": {"label": "sky spawn"},
                },
                {
                    "id": "pattern:spawn:zero-hops",
                    "subject": "spawn-neighborhood",
                    "population": "blood-bloodbath",
                    "match": {"hops": "0"},
                    "interpretation": {"label": "already in sky component"},
                },
            ],
        }
        from bloodmap.patterns import match_samples_to_catalog
        matches = match_samples_to_catalog(samples, catalog)
        by_sample = {}
        for item in matches:
            by_sample.setdefault(item["focus"]["origin"], []).append(item["pattern_id"])
        overlapping = [ids for ids in by_sample.values() if len(ids) >= 2]
        self.assertTrue(overlapping)


if __name__ == "__main__":
    unittest.main()
