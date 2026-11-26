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


class Probes(unittest.TestCase):
    """A probe is evidence another agent runs again: from the repository root, and from nothing that is not kept."""

    def test_every_probe_says_what_it_counts_and_leans_on_nothing_outside_the_repository(self):
        import ast

        probes = sorted((F.HOME / "probes").glob("*.py"))
        self.assertGreater(len(probes), 30)
        for path in probes:
            with self.subTest(probe=path.name):
                text = path.read_text(encoding="utf-8")
                tree = ast.parse(text)
                self.assertTrue(ast.get_docstring(tree), "open with a sentence saying what it counts")
                scratch = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)
                           and isinstance(node.value, str) and node.value is not ast.get_docstring(tree, clean=False)
                           and (node.value.startswith("work/") or "work/consolidation" in node.value)]
                self.assertEqual(scratch, [], "a probe reads and writes nothing under work/")
                if "bloodmap" in text or "from tools" in text:
                    self.assertIn("sys.path", text, "put the repository root on the path: it is run as a file")

    def test_a_probe_that_is_cited_must_be_kept(self):
        row = {**GOOD, "learned": {"in": "some-level", "date": "2026-11-26"},
               "evidence": ["E3M1 s79; recounted by knowledge/blood/findings/probes/no_such_probe.py"]}
        row.pop("learned_in"), row.pop("date")
        self.assertIn("not kept", " ".join(F.problems(row)))


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

    def test_a_mark_is_of_the_finding_as_it_stood_and_a_rewritten_one_is_unchecked_again(self):
        F.record(**GOOD, home=self.home)
        self.assertEqual([row["id"] for row in F.unchecked(self.home)], [GOOD["id"]])
        self.assertIn("unchecked", F.line(F.read(self.home)[0]))
        with self.assertRaises(F.FindingError):
            F.mark(GOOD["id"], "looked", home=self.home)             # what was opened, and what was read there
        F.mark(GOOD["id"], "E3M1 sector 79 read: its walls carry one course on from step to step", home=self.home)
        self.assertEqual(F.unchecked(self.home), [])
        self.assertIn("CHECKED", F.show(F.read(self.home)[0]))
        # a word of use is not what was checked; the claim is
        F.amend(GOOD["id"], home=self.home, claim=GOOD["claim"] + " Always.")
        self.assertEqual(len(F.unchecked(self.home)), 1)
        row = F.amend(GOOD["id"], "E3M1 sector 79 read again: one flight of one map, so not always", home=self.home,
                      claim=GOOD["claim"], use="Carry the courses on.")
        self.assertTrue(F.is_checked(row))
        path = self.home / f"{GOOD['id']}.json"
        path.write_text(path.read_text("utf-8").replace("carries", "never carries"), "utf-8")      # edited by hand
        self.assertEqual(len(F.unchecked(self.home)), 1)
        self.assertIn("rewritten since", F.show(F.read(self.home)[0]))
        F.record(**GOOD, home=self.home, replace=True)
        self.assertNotIn("checked", F.read(self.home)[0])

    def test_a_hypothesis_is_owed_no_check_and_carries_no_mark(self):
        F.record(**{**GOOD, "standing": "hypothesis", "evidence": []}, home=self.home)
        self.assertEqual(F.unchecked(self.home), [])
        with self.assertRaises(F.FindingError):
            F.mark(GOOD["id"], "E3M1 sector 79 read: it is so after all, in this one flight", home=self.home)
        with self.assertRaises(F.FindingError):
            F.amend(GOOD["id"], home=self.home, colour="red")


if __name__ == "__main__":
    unittest.main()
