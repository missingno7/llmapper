"""Contrastive-concept regressions (Phase 4).

Covers the contrast surface of `bloodmap/anchors.py`: the relational features,
the separation arithmetic, and the two guards that decide whether a measured
separation means anything -- the discriminator floor and the map-transfer
check. The map-transfer check exists because the shelf-vs-crate pilot's best
rule matched 89% of one map's positives and 0% of another's, so it was
separating maps rather than concepts.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from bloodmap.anchors import (
    CONTRAST_FEATURES,
    DISCRIMINATOR_FLOOR,
    MAX_STEP_PLAYER_HEIGHTS,
    SIGNATURE_BOUND_FEATURES,
    AnchorError,
    _counterexamples,
    _map_transfer,
    _separation,
    anchor_from_tiles,
    carrier_features,
    contrast_anchor_sets,
    contrast_signature_classes,
)
from bloodmap.relations import extract_relations
from tests.test_relations import (
    furnished_map, notched_map, stacked_map, wired_map,
)


ROOT = Path(__file__).resolve().parents[1]
SHELF_REPORT = ROOT / "reports" / "blood-contrast-shelf-vs-crate.json"
NICHE_REPORT = ROOT / "reports" / "blood-contrast-niche-pair.json"


def _features(build, sector_id, hops=1):
    return carrier_features(build, sector_id,
                            extract_relations(build, sectors=[sector_id], hops=hops))


class CarrierFeatureTests(unittest.TestCase):
    """Every feature is relational and reads no picnum."""

    def setUp(self):
        self.build = furnished_map()
        self.found = _features(self.build, 0)

    def test_it_counts_what_the_sector_holds_and_what_holds_it_up(self):
        self.assertEqual(self.found["objects_held"], 4)
        self.assertEqual(self.found["objects_resting"], 4)
        self.assertEqual(self.found["objects_against_wall"], 1)

    def test_it_counts_the_ways_in(self):
        self.assertEqual(self.found["portals"], 1)
        self.assertEqual(self.found["solid_wall_share"], 0.75)

    def test_a_room_under_one_body_tall_is_not_enterable(self):
        """The synthetic room is 0.966 player heights clear, so no portal
        into it clears a standing player -- which is what `enterable` means."""
        self.assertFalse(self.found["enterable"])
        self.assertTrue(self.found["solid_closed_volume"])

    def test_raising_the_ceiling_makes_it_enterable(self):
        build = furnished_map()
        for sector in build.sectors:
            sector["fields"]["ceiling_z"] = -40000
        self.assertTrue(_features(build, 0)["enterable"])

    def test_a_step_over_blood_s_limit_closes_the_way_in(self):
        build = furnished_map()
        for sector in build.sectors:
            sector["fields"]["ceiling_z"] = -40000
        build.sectors[0]["fields"]["floor_z"] = (
            int(build.sectors[1]["fields"]["floor_z"]) - 8192)      # a big step up
        found = _features(build, 0)
        self.assertGreater(found["max_step_player_heights"], MAX_STEP_PLAYER_HEIGHTS)
        self.assertFalse(found["enterable"])

    def test_identical_neighbours_are_counted_as_twins(self):
        """`stackable_identical_units`: the two synthetic sectors have the same
        footprint and clear height."""
        self.assertEqual(self.found["twin_neighbours"], 1)

    def test_a_differently_sized_neighbour_is_not_a_twin(self):
        build = furnished_map()
        build.sectors[1]["fields"]["floor_z"] = 30000
        self.assertEqual(_features(build, 0)["twin_neighbours"], 0)

    def test_stacking_and_nesting_come_from_the_relations(self):
        """`above` and `inside` need both sectors in the document. The stacked
        fixture's two sectors are not portal-linked, so a one-hop neighborhood
        around either would not see the other -- which is exactly why a crate
        built as an unlinked overlapping sector is invisible to this feature."""
        build = stacked_map()
        document = extract_relations(build, sectors=[0, 1], hops=0)
        stacked = carrier_features(build, 1, document)
        self.assertTrue(stacked["stands_above_a_neighbour"])
        self.assertTrue(stacked["inside_another_sector"])

        build = notched_map()
        document = extract_relations(build, sectors=[0, 1, 2], hops=0)
        nested = carrier_features(build, 1, document)
        self.assertTrue(nested["inside_another_sector"])
        self.assertFalse(nested["stands_above_a_neighbour"])

    def test_a_raised_platform_is_not_the_same_as_a_stacked_volume(self):
        """A crate inside a room stands above that room's *floor*, not above
        its ceiling. `above` misses it; `raised_above_all_neighbours` is the
        feature that carries the platform reading."""
        build = furnished_map()
        build.sectors[0]["fields"]["floor_z"] = (
            int(build.sectors[1]["fields"]["floor_z"]) - 8192)
        found = _features(build, 0)
        self.assertTrue(found["raised_above_all_neighbours"])
        self.assertGreater(found["rise_over_neighbours_player_heights"], 0)
        self.assertFalse(found["stands_above_a_neighbour"])
        level = _features(furnished_map(), 0)
        self.assertFalse(level["raised_above_all_neighbours"])
        self.assertEqual(level["rise_over_neighbours_player_heights"], 0.0)

    def test_every_declared_feature_is_produced(self):
        self.assertEqual(set(self.found), set(CONTRAST_FEATURES))

    def test_no_feature_reads_which_tile(self):
        """Class membership comes from tiles; a feature that moved when the
        tiles were renamed would be measuring texture identity. Relabelling is
        injective -- every tile gets a new number, none are merged."""
        build = furnished_map()
        before = _features(build, 0)
        for sprite in build.sprites:
            sprite["fields"]["picnum"] = int(sprite["fields"]["picnum"]) + 5000
        for wall in build.walls:
            wall["fields"]["picnum"] = int(wall["fields"]["picnum"]) + 5000
        self.assertEqual(_features(build, 0), before)

    def test_one_feature_does_read_tile_equality_and_says_so(self):
        """`in_a_repeating_run` groups objects by identical picnum. That is
        tile *equality* among neighbours -- a relation -- not a lookup of which
        tile it is. Merging every object onto one tile therefore changes it,
        and a reader of the contrast should know that."""
        build = furnished_map()
        self.assertTrue(_features(build, 0)["in_a_repeating_run"])
        build = furnished_map()
        for index, sprite in enumerate(build.sprites):
            sprite["fields"]["picnum"] = 900 + index      # all distinct: no run
        self.assertFalse(_features(build, 0)["in_a_repeating_run"])


class WiringIsNotFurnitureTests(unittest.TestCase):
    """Phase 4 counted sound markers as objects; picnum 2520 was 83% of both
    sides of the niche contrast and is `kSoundSector`'s editor icon."""

    def test_objects_held_counts_only_what_a_player_sees(self):
        build = wired_map()
        document = extract_relations(build, sectors=[0, 1], hops=0)
        closet = carrier_features(build, 1, document)
        self.assertEqual(closet["objects_held"], 0)
        self.assertEqual(closet["wiring_objects_held"], 4)
        room = carrier_features(build, 0, document)
        self.assertEqual(room["objects_held"], 2)
        self.assertEqual(room["wiring_objects_held"], 0)

    def test_relations_about_wiring_are_not_counted_as_supported_objects(self):
        build = wired_map()
        document = extract_relations(build, sectors=[1], hops=0)
        found = carrier_features(build, 1, document)
        self.assertEqual(found["objects_resting"], 0)
        self.assertEqual(found["objects_against_wall"], 0)

    def test_the_wiring_count_is_a_declared_feature_bound_by_the_signature(self):
        self.assertIn("wiring_objects_held", CONTRAST_FEATURES)
        self.assertEqual(SIGNATURE_BOUND_FEATURES["wiring_objects_held"], "objects")


class SeparationTests(unittest.TestCase):
    def test_a_boolean_feature_reports_both_shares(self):
        found = _separation("f", [True] * 8 + [False] * 2, [False] * 20)
        self.assertEqual(found["kind"], "boolean")
        self.assertEqual(found["positive_share"], 0.8)
        self.assertEqual(found["comparison_share"], 0.0)
        self.assertEqual(found["balanced_accuracy"], 0.9)
        self.assertEqual(found["direction"], "positive")

    def test_a_feature_that_says_nothing_scores_a_half(self):
        found = _separation("f", [True, False], [True, False])
        self.assertEqual(found["balanced_accuracy"], 0.5)
        self.assertLess(found["balanced_accuracy"], DISCRIMINATOR_FLOOR)

    def test_a_feature_pointing_the_other_way_still_scores(self):
        """A separator that is inverted is still a separator; the direction is
        reported rather than the score being thrown away."""
        found = _separation("f", [False] * 10, [True] * 10)
        self.assertEqual(found["balanced_accuracy"], 1.0)
        self.assertEqual(found["direction"], "comparison")

    def test_a_numeric_feature_finds_a_threshold_and_keeps_both_rates(self):
        found = _separation("f", [10, 11, 12], [1, 2, 3])
        self.assertEqual(found["kind"], "numeric")
        self.assertEqual(found["positive_median"], 11)
        self.assertEqual(found["comparison_median"], 2)
        self.assertEqual(found["balanced_accuracy"], 1.0)
        self.assertEqual(found["positives_matching"], 1.0)
        self.assertEqual(found["comparison_matching"], 0.0)
        self.assertTrue(found["rule"].startswith("f >="))

    def test_balanced_accuracy_does_not_reward_a_rule_that_never_fires(self):
        """The reason the measure is balanced: on 5-vs-500 a rule matching
        nothing is 99% accurate and useless."""
        found = _separation("f", [1] * 5, [1] * 500)
        self.assertLessEqual(found["balanced_accuracy"], 0.51)

    def test_an_empty_side_reports_no_data(self):
        self.assertEqual(_separation("f", [], [1])["verdict"], "no data")


class MapTransferTests(unittest.TestCase):
    """The guard that caught pilot 1."""

    ROWS = ([{"map": "A.MAP", "f": True} for _ in range(9)]
            + [{"map": "B.MAP", "f": False} for _ in range(7)])
    BEST = {"feature": "f", "kind": "boolean", "direction": "positive"}

    def test_a_rule_true_in_one_map_and_false_in_another_shows_full_spread(self):
        found = _map_transfer(self.BEST, self.ROWS)
        self.assertEqual(found["maps"], 2)
        self.assertEqual(found["per_map"]["A.MAP"]["matching"], 1.0)
        self.assertEqual(found["per_map"]["B.MAP"]["matching"], 0.0)
        self.assertEqual(found["spread"], 1.0)

    def test_leave_one_map_out_shows_it_does_not_transfer(self):
        found = _map_transfer(self.BEST, self.ROWS)["leave_one_map_out"]
        self.assertEqual(found["A.MAP"]["on_the_rest"], 0.0)
        self.assertEqual(found["A.MAP"]["on_the_held_out_map"], 1.0)

    def test_a_rule_that_holds_everywhere_has_no_spread(self):
        rows = [{"map": "A.MAP", "f": True}, {"map": "B.MAP", "f": True}]
        self.assertEqual(_map_transfer(self.BEST, rows)["spread"], 0.0)

    def test_no_discriminator_means_nothing_to_transfer(self):
        self.assertIsNone(_map_transfer(None, self.ROWS)["rule"])


class CounterexampleTests(unittest.TestCase):
    def test_boolean_misses_and_false_matches_are_both_kept(self):
        positives = [{"map": "A", "sector": i, "f": i < 3} for i in range(5)]
        comparisons = [{"map": "B", "sector": i, "f": i < 2} for i in range(6)]
        found = _counterexamples(
            {"feature": "f", "kind": "boolean", "direction": "positive"},
            positives, comparisons, 8)
        self.assertEqual(found["positives_it_misses"]["count"], 2)
        self.assertEqual(found["comparisons_it_wrongly_matches"]["count"], 2)

    def test_numeric_rules_are_read_back_from_the_rule_string(self):
        positives = [{"map": "A", "sector": i, "f": v} for i, v in enumerate([9, 9, 1])]
        comparisons = [{"map": "B", "sector": i, "f": v} for i, v in enumerate([1, 9])]
        found = _counterexamples(
            {"feature": "f", "kind": "numeric", "rule": "f >= 5.0"},
            positives, comparisons, 8)
        self.assertEqual(found["rule"], "f >= 5.0")
        self.assertEqual(found["positives_it_misses"]["count"], 1)
        self.assertEqual(found["comparisons_it_wrongly_matches"]["count"], 1)

    def test_nothing_reaching_the_floor_is_said_plainly(self):
        self.assertIsNone(_counterexamples(None, [], [], 8)["rule"])


class SignatureBoundFeatureTests(unittest.TestCase):
    def test_the_defining_facet_is_never_scored(self):
        """`objects_resting` *is* the `seated` facet. Scoring it would report
        the class definition back as a discovery."""
        self.assertEqual(SIGNATURE_BOUND_FEATURES["objects_resting"], "seated")
        free = [n for n in CONTRAST_FEATURES if n not in SIGNATURE_BOUND_FEATURES]
        self.assertNotIn("objects_resting", free)
        self.assertIn("min_opening_player_heights", free)
        self.assertTrue(free)

    def test_every_bound_feature_is_a_real_feature(self):
        for name in SIGNATURE_BOUND_FEATURES:
            self.assertIn(name, CONTRAST_FEATURES)


class FailClosedTests(unittest.TestCase):
    def test_a_contrast_with_an_empty_side_refuses(self):
        from bloodmap.patterns import list_corpus_maps

        if not list_corpus_maps(population="blood-campaign"):
            self.skipTest("no local Blood campaign maps")
        with self.assertRaises(AnchorError):
            contrast_anchor_sets(
                anchor_from_tiles("nothing", (65500,)),
                anchor_from_tiles("also_nothing", (65501,)),
                directory=None, population="blood-bloodbath", view=None)


class EmittedReportTests(unittest.TestCase):
    """The pilots' findings, pinned. These fail if a threshold change flips a
    conclusion the reports state in prose."""

    def test_the_shelf_pilot_records_a_map_artifact_not_a_concept(self):
        if not SHELF_REPORT.exists():
            self.skipTest("the shelf-vs-crate contrast report has not been generated")
        doc = json.loads(SHELF_REPORT.read_text(encoding="utf-8"))
        self.assertGreater(doc["map_transfer"]["spread"], 0.5,
                           "the report's verdict is that the best rule is map-confounded")
        self.assertLessEqual(doc["counts"]["shelf"]["maps"], 3)
        rejected = {item["feature"] for item in doc["rejected"]}
        for predicted in ("twin_neighbours", "solid_closed_volume", "enterable",
                          "stands_above_a_neighbour"):
            self.assertIn(predicted, rejected,
                          f"{predicted} is reported as a rejected 03_...md discriminator")
        self.assertGreater(doc["counts"]["ambiguous_sectors"], 0)
        self.assertTrue(doc["limitations"])

    def test_the_niche_pilot_finds_one_concept_with_two_variants(self):
        if not NICHE_REPORT.exists():
            self.skipTest("the niche-pair contrast report has not been generated")
        doc = json.loads(NICHE_REPORT.read_text(encoding="utf-8"))
        self.assertEqual(doc["differing_facets"], ["seated"])
        self.assertEqual(doc["discriminating"], [],
                         "the report's verdict is that nothing else separates them")
        positive = doc["object_description"]["wall_fixture_niche"]["commonest"][0]
        comparison = doc["object_description"]["floor_object_niche"]["commonest"][0]
        self.assertEqual(positive["picnum"], comparison["picnum"],
                         "both variants must be dominated by the same object, "
                         "or the split would be texture after all")
        for side in ("wall_fixture_niche", "floor_object_niche"):
            self.assertGreaterEqual(doc["counts"][side]["maps"], 20)
        for name in doc["features_measured"]:
            self.assertNotIn(name, SIGNATURE_BOUND_FEATURES)


class VisibleOnlyRerunTests(unittest.TestCase):
    """The Phase 4 re-run after the mining-hygiene fix. Pins the finding that
    the family mostly dissolved, so a regression that quietly re-admits wiring
    shows up here."""

    REPORT = ROOT / "reports" / "blood-contrast-niche-pair-visible-only.json"

    def setUp(self):
        if not (self.REPORT.exists() and NICHE_REPORT.exists()):
            self.skipTest("the niche-pair contrast reports have not been generated")
        self.before = json.loads(NICHE_REPORT.read_text(encoding="utf-8"))
        self.after = json.loads(self.REPORT.read_text(encoding="utf-8"))

    def test_the_family_shrank_once_wiring_stopped_counting(self):
        for side in ("wall_fixture_niche", "floor_object_niche"):
            self.assertLess(self.after["counts"][side]["sectors"],
                            self.before["counts"][side]["sectors"] / 2,
                            f"{side} should lose most of its members")

    def test_the_sound_marker_tile_is_gone_from_both_sides(self):
        """picnum 2520 was 83% of both classes; it is a kSoundSector icon."""
        for side in ("wall_fixture_niche", "floor_object_niche"):
            picnums = {item["picnum"]
                       for item in self.after["object_description"][side]["commonest"]}
            self.assertNotIn(2520, picnums)

    def test_the_wiring_is_reported_rather_than_discarded(self):
        self.assertIn("wiring_description", self.after)
        self.assertTrue(self.after["wiring_description"]["note"])

    def test_the_one_surviving_discriminator_is_map_confounded(self):
        """With 13 positives across 10 maps there is not enough evidence for a
        claim, and the transfer check says so rather than the prose."""
        if not self.after["discriminating"]:
            return
        self.assertGreater(self.after["map_transfer"]["spread"], 0.5)


class LiveContrastTests(unittest.TestCase):
    """One end-to-end run on real maps, on the smallest population."""

    def setUp(self):
        from bloodmap.patterns import list_corpus_maps

        if not list_corpus_maps(population="blood-bloodbath"):
            self.skipTest("no local Blood BloodBath maps")

    def test_a_signature_contrast_never_scores_the_facets_that_define_it(self):
        """Runs the real path, not the stored report: a change inside
        `contrast_signature_classes` cannot hide behind an artifact written
        before it."""
        base = ("portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|"
                "seated:some|wallbound:some|run:no|size:hall|clear:{}")
        payload = contrast_signature_classes(
            base.format("lofty"), base.format("standing"),
            directory=None, population="blood-bloodbath", hops=1)
        self.assertEqual(payload["differing_facets"], ["clear"])
        self.assertTrue(payload["features_measured"])
        for name in payload["features_measured"]:
            self.assertNotIn(name, SIGNATURE_BOUND_FEATURES)
        scored = {item["feature"]
                  for item in payload["discriminating"] + payload["rejected"]}
        self.assertEqual(scored, set(payload["features_measured"]))

    def test_a_contrast_runs_and_reports_every_required_part(self):
        payload = contrast_anchor_sets(
            anchor_from_tiles("crate", (95, 452, 462, 456)),
            anchor_from_tiles("pipe", (496, 497, 498, 499)),
            directory=None, population="blood-bloodbath", view=None)
        for key in ("counts", "discriminating", "rejected", "ambiguous",
                    "counterexamples", "map_transfer", "skipped", "limitations"):
            self.assertIn(key, payload)
        self.assertTrue(payload["rows"])
        for row in payload["rows"]:
            self.assertIn(row["label"], {"crate", "pipe"})
            self.assertEqual(row["population"], "blood-bloodbath")
        scored = {item["feature"] for item in payload["discriminating"] + payload["rejected"]}
        self.assertEqual(scored, set(CONTRAST_FEATURES))


if __name__ == "__main__":
    unittest.main()
