"""The multi-view bundle, and its contract.

The contract is the thing worth testing: no view canonical, relations
explicit, and disagreements listed rather than reconciled. A bundle whose
views all agree has either been reconciled by hand or is running one view
twice, so the tests check that the disagreement machinery can actually fire.

The gathering half needs the corpus and skips cleanly without it.
"""

import unittest

from bloodmap.bundle import SCHEMA, VIEWS, disagreements

try:
    from bloodmap.patterns import list_corpus_maps
    CORPUS = bool(list_corpus_maps(population="blood-campaign"))
except Exception:
    CORPUS = False


def bundle(**views):
    return {"$schema": SCHEMA, "views": views}


class DisagreementTest(unittest.TestCase):
    """Each disagreement fires on a difference and stays quiet without one."""

    def progression(self, mine, theirs):
        return {"finally_reachable": mine, "at_rest_reachable": 0,
                "sp_understand": {"final_reachable": theirs}}

    def test_two_reachability_answers_that_differ_are_reported(self):
        found = disagreements(bundle(progression=self.progression(357, 278)))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["difference"], 79)
        self.assertEqual(found[0]["between"],
                         ["conditional_topology", "sp_understand"])

    def test_two_reachability_answers_that_agree_are_not_reported(self):
        self.assertEqual(disagreements(bundle(progression=self.progression(300, 300))), [])

    def test_the_difference_is_unsigned_so_neither_view_reads_as_a_deficit(self):
        # Which of two independent readings is the larger is not a fact about
        # correctness, and a signed difference invites reading one as the
        # shortfall of the other.
        one = disagreements(bundle(progression=self.progression(357, 278)))[0]
        other = disagreements(bundle(progression=self.progression(278, 357)))[0]
        self.assertEqual(one["difference"], other["difference"])
        self.assertEqual(one["difference"], 79)

    def test_a_disagreement_says_why_the_two_can_differ(self):
        # An entry that only states two numbers invites the reader to treat
        # one as a defect. Each has to carry what the two were looking at.
        found = disagreements(bundle(progression=self.progression(357, 278)))
        self.assertIn("why_they_can_differ", found[0])
        self.assertGreater(len(found[0]["why_they_can_differ"]), 80)

    def test_nothing_is_reconciled_away(self):
        # Both numbers survive into the entry. A disagreement that reports
        # only a winner is a reconciliation wearing the word.
        found = disagreements(bundle(progression=self.progression(357, 278)))[0]
        self.assertEqual(found["conditional_topology"], 357)
        self.assertEqual(found["sp_understand"], 278)

    def test_undecided_mechanisms_are_reported_by_both_counts(self):
        found = disagreements(bundle(
            effects={"by_design_object": {"not decidable from z alone": 29}},
            conditional_topology={"summary": {"scoped_out_rotate_slide": 29}}))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["effects_undecided"], 29)
        self.assertEqual(found[0]["conditional_scoped_out"], 29)

    def test_a_map_with_nothing_undecided_reports_nothing(self):
        self.assertEqual(disagreements(bundle(
            effects={"by_design_object": {"changes what fits through": 4}},
            conditional_topology={"summary": {"scoped_out_rotate_slide": 0}})), [])

    def test_a_sector_that_is_both_frontage_and_structure_is_reported(self):
        found = disagreements(bundle(
            facades={"hosts": [10, 11, 12]},
            functional_regions={"records": [{"sectors": ["sector:11", "sector:99"]}]}))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["sectors"], [11])

    def test_sector_refs_and_bare_ints_are_both_understood(self):
        found = disagreements(bundle(
            facades={"hosts": [7]},
            functional_regions={"records": [{"sectors": [7]}]}))
        self.assertEqual(found[0]["sectors"], [7])

    def test_player_space_the_traversal_cannot_enter_is_reported(self):
        found = disagreements(bundle(
            geometry={"sector_kinds": {"reachable": 387}},
            progression=self.progression(357, 357)))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["difference"], 30)

    def test_reaching_everything_the_geometry_offers_reports_nothing(self):
        found = disagreements(bundle(
            geometry={"sector_kinds": {"reachable": 300}},
            progression=self.progression(300, 300)))
        self.assertEqual(found, [])

    def test_a_refused_viewpoint_is_reported_as_a_view_conflict(self):
        found = disagreements(bundle(
            visual={"refused": [{"sector": 276, "reason": "no clearance"}]}))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["between"], ["visual", "conditional_topology"])

    def test_a_render_that_refused_nothing_reports_nothing(self):
        self.assertEqual(disagreements(bundle(visual={"refused": []})), [])

    def test_an_empty_bundle_has_no_disagreements_rather_than_failing(self):
        self.assertEqual(disagreements(bundle()), [])


class AbridgementTest(unittest.TestCase):
    def test_a_list_inside_the_limit_is_left_alone_and_not_announced(self):
        # Saying a view was abridged when it was not is a lie about the data,
        # and the cheapest kind to tell.
        from bloodmap.bundle import _abridge

        built = {"views": {"facades": {"records": [1, 2, 3]}}}
        note = _abridge(built, 400)
        self.assertEqual(note, {"limit": 400})
        self.assertEqual(built["views"]["facades"]["records"], [1, 2, 3])
        self.assertNotIn("records_note", built["views"]["facades"])

    def test_a_list_over_the_limit_is_trimmed_and_says_so(self):
        from bloodmap.bundle import _abridge

        built = {"views": {"facades": {"records": list(range(10))}}}
        note = _abridge(built, 4)
        self.assertEqual(note["trimmed"]["facades"], {"kept": 4, "of": 10})
        self.assertEqual(built["views"]["facades"]["records"], [0, 1, 2, 3])
        self.assertIn("records_note", built["views"]["facades"])


@unittest.skipUnless(CORPUS, "the Blood corpus is not present")
class GatherTest(unittest.TestCase):
    def test_one_campaign_map_gathers_every_view_but_the_rendered_one(self):
        from bloodmap.bundle import build_bundle
        from bloodmap.format import read_map

        entry = [item for item in list_corpus_maps(population="blood-campaign")
                 if item.path.stem == "E1M4"][0]
        built = build_bundle(read_map(entry.path), map_name="E1M4")
        #: Everything but `visual`, which needs the renderer and is passed in.
        self.assertEqual(built["views_missing"], ["visual"])
        for name in built["views_gathered"]:
            view = built["views"][name]
            self.assertIn("produced_by", view, name)
            self.assertIn("assumes", view, name)
        self.assertTrue(built["disagreements"])
        self.assertEqual(len(built["contract"]), 3)

    def test_the_bundle_abridges_honestly_or_not_at_all(self):
        from bloodmap.bundle import build_bundle
        from bloodmap.format import read_map

        entry = [item for item in list_corpus_maps(population="blood-campaign")
                 if item.path.stem == "E1M4"][0]
        built = build_bundle(read_map(entry.path), map_name="E1M4", abridge=5)
        self.assertTrue(built["abridged"]["trimmed"])
        for name, note in built["abridged"]["trimmed"].items():
            self.assertEqual(len(built["views"][name]["records"]), note["kept"])
            self.assertIn("records_note", built["views"][name])
            self.assertGreater(note["of"], note["kept"])


if __name__ == "__main__":
    unittest.main()
