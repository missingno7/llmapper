"""Design-pattern observation and retrieval regressions."""

from __future__ import annotations

import unittest

from bloodmap.patterns import (
    classify_map_population,
    cluster_samples,
    observe_spawn_neighborhoods,
    query_catalog,
)
from tests.test_exposure import field_and_closet_map


class PatternPopulationTests(unittest.TestCase):
    def test_filename_provenance_is_not_mixed(self):
        self.assertEqual(classify_map_population("maps/blood/BB6.MAP"), "blood-bloodbath")
        self.assertEqual(classify_map_population("maps/blood/E1M1.MAP"), "blood-campaign")
        self.assertEqual(classify_map_population("maps/blood/DWE1M1.MAP"), "conversion")
        self.assertEqual(classify_map_population("work/BB2-semantic-reconstruction-v3.MAP"), "generated")
        self.assertEqual(classify_map_population("work/BB6-pattern-reconstruction-v1.MAP"), "generated")
        self.assertEqual(classify_map_population("work/E1M1-BLOOD.MAP"), "conversion")


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
