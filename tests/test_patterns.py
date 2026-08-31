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
                             angle=0, index=index, extra=-1, owner=-1)
        sprite.extra = None
        sprites.append(sprite)
    flush = copy.deepcopy(template)
    flush.fields.update(x=512, y=20, z=floor_z, sector=0, picnum=701,
                        angle=512, index=3, extra=-1, owner=-1)
    flush.extra = None
    sprites.append(flush)
    disk.sprites = sprites
    disk.header["num_sprites"] = len(sprites)
    return parse_map(encode_map(disk))


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
        self.assertIn("relations.context_signature", sample["evidence"])

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
