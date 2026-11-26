"""The findings shelf holds only well-made findings, and each kind of knowing must cite what it is made of."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bloodmap import findings as F

GOOD = dict(id="a-test-finding-about-stairs", topic="texture", standing="precedent",
            claim="Down a long flight Blood carries the wall's courses on from step to step.",
            evidence=["E3M1 s79: the courses continue"], learned_in="some-level", date="2026-11-26")


class Shelf(unittest.TestCase):
    def test_everything_on_file_is_well_made_and_names_code_that_is_there(self):
        self.assertEqual(F.check(), [])

    def test_the_shelf_is_not_empty_and_keeps_its_kinds_apart(self):
        rows = F.read()
        self.assertGreater(len(rows), 100)
        kinds = {row["standing"] for row in rows}
        self.assertLessEqual(kinds, set(F.STANDINGS))
        for needed in ("engine", "ruling", "precedent", "tendency", "practice"):
            self.assertIn(needed, kinds)


class Filing(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())

    def test_a_finding_is_filed_found_and_not_filed_twice(self):
        F.record(**GOOD, home=self.home, words=["Staircase"])
        self.assertEqual([row["id"] for row in F.find(["stair"], home=self.home)], [GOOD["id"]])
        self.assertEqual([row["id"] for row in F.find(["staircase", "courses"], home=self.home)], [GOOD["id"]])
        self.assertEqual(F.find(["lamp"], home=self.home), [])
        with self.assertRaises(F.FindingError):
            F.record(**GOOD, home=self.home)
        F.record(**{**GOOD, "claim": GOOD["claim"] + " And the roof comes down in one slope."}, home=self.home, replace=True)
        self.assertIn("one slope", F.read(self.home)[0]["claim"])

    def test_each_kind_of_knowing_must_cite_what_it_is_made_of(self):
        for standing, evidence, wrong in (
                ("engine", ["we saw it happen"], "source file"),
                ("precedent", ["Blood does this a lot"], "map"),
                ("tendency", ["most maps"], "count"),
                ("ruling", ["the owner said so"], "day"),
                ("practice", [], "evidence is missing")):
            with self.subTest(standing=standing):
                with self.assertRaises(F.FindingError) as caught:
                    F.record(**{**GOOD, "standing": standing, "evidence": evidence}, home=self.home)
                self.assertIn(wrong, str(caught.exception))
        F.record(**{**GOOD, "id": "an-engine-fact", "standing": "engine", "evidence": ["NBlood/source/blood/src/actor.cpp:2710"]},
                 home=self.home)
        F.record(**{**GOOD, "id": "a-guess", "standing": "hypothesis", "evidence": []}, home=self.home)

    def test_a_refuted_finding_says_what_is_true_instead(self):
        with self.assertRaises(F.FindingError):
            F.record(**{**GOOD, "standing": "refuted"}, home=self.home)
        F.record(**{**GOOD, "standing": "refuted"}, instead="The courses restart only at a landing.", home=self.home)

    def test_code_that_is_named_must_be_there(self):
        self.assertTrue(F.resolves("bloodmap.findings.record"))
        self.assertTrue(F.resolves("bloodmap.wiring.Circuit.drop_idle"))
        self.assertTrue(F.resolves("bloodmap/findings.py"))
        self.assertFalse(F.resolves("bloodmap.findings.no_such_thing"))
        with self.assertRaises(F.FindingError):
            F.record(**GOOD, code=["bloodmap.no_such_module.f"], home=self.home)

    def test_the_firmest_is_found_first(self):
        F.record(**{**GOOD, "id": "ours", "standing": "practice", "evidence": ["it held in one level"]}, home=self.home)
        F.record(**GOOD, home=self.home)
        self.assertEqual([row["standing"] for row in F.find(["flight"], home=self.home)], ["precedent", "practice"])

    def test_a_project_scope_is_said_as_such(self):
        row = F.record(**GOOD, scope="project:some-level", home=self.home)
        self.assertIn("(project:some-level)", F.line(row))
        with self.assertRaises(F.FindingError):
            F.record(**{**GOOD, "id": "another"}, scope="everywhere", home=self.home)


if __name__ == "__main__":
    unittest.main()
