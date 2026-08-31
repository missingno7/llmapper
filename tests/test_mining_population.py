"""A mined file has to say which population it was mined from.

Five miners describe themselves as measuring "the campaign" and were in fact
reading the `reference` view -- campaign, BloodBath and the curated community
sets -- because they globbed a flat directory that happened to hold it.
Nothing in their output said so, and the protocol's rule that community maps
are precedent and never campaign convention cannot be checked against a file
that does not name its own evidence.

`reports/blood-mining-population.md` measures what the two readings cost.
"""

from __future__ import annotations

import io
import json
import pathlib
import sys
import tempfile
import unittest

from bloodmap.patterns import CORPUS_VIEWS, list_corpus_maps


#: Every miner that used to glob the flat corpus, and the artifact it wrote.
MINERS = {
    "mine_run_rhythm": "knowledge/blood/design/run-rhythm-v1.json",
    "mine_set_pieces": "knowledge/blood/design/set-pieces-v1.json",
    "mine_monuments": "knowledge/blood/design/monuments-v1.json",
    "mine_prop_catalogue": "projects/blood-city/references/prop-catalogue.json",
    "mine_style_combinations":
        "projects/blood-city/references/style-combinations.json",
}

ROOT = pathlib.Path(__file__).resolve().parents[1]


def have_corpus() -> bool:
    try:
        return bool(list_corpus_maps(population="blood-campaign"))
    except Exception:
        return False


def mine(module_name: str, *args) -> dict:
    """Run one miner into a temporary file and return what it wrote."""
    import importlib

    module = importlib.import_module(f"tools.{module_name}")
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "out.json"
        stdout, sys.stdout = sys.stdout, io.StringIO()
        try:
            module.main([*args, "-o", str(out)])
        finally:
            sys.stdout = stdout
        return json.loads(out.read_text(encoding="utf-8"))


class ViewArgumentTests(unittest.TestCase):
    """The population is a named choice, not a free-text field."""

    def refuse(self, module_name, view):
        import importlib

        module = importlib.import_module(f"tools.{module_name}")
        stderr, sys.stderr = sys.stderr, io.StringIO()
        try:
            with self.assertRaises(SystemExit):
                module.main(["--view", view, "-o", "unused"])
        finally:
            sys.stderr = stderr

    def test_every_miner_refuses_a_view_the_registry_does_not_define(self):
        for module_name in MINERS:
            with self.subTest(miner=module_name):
                self.refuse(module_name, "the-flat-directory")

    def test_the_offered_views_are_the_registry_own(self):
        """`reference` and `original` come from bloodmap.patterns, so a miner
        cannot drift into a private idea of which maps count.
        """
        self.assertIn("reference", CORPUS_VIEWS)
        self.assertIn("original", CORPUS_VIEWS)
        self.assertNotIn("community", CORPUS_VIEWS["reference"])


class PopulationStampTests(unittest.TestCase):
    """The cheapest of the five, run at both readings."""

    @classmethod
    def setUpClass(cls):
        if not have_corpus():
            raise unittest.SkipTest("the Blood corpus is not present")

    def test_the_default_is_the_population_the_published_file_was_mined_from(self):
        stamped = mine("mine_run_rhythm")["population"]
        self.assertEqual(stamped["view"], "reference")
        self.assertEqual(stamped["populations"], list(CORPUS_VIEWS["reference"]))

    def test_asking_for_the_campaign_only_is_recorded_as_such(self):
        stamped = mine("mine_run_rhythm", "--view", "original")["population"]
        self.assertEqual(stamped["view"], "original")
        self.assertNotIn("community-curated", stamped["populations"])

    def test_the_narrower_reading_really_is_narrower(self):
        """If the two views gave the same numbers the label would not matter."""
        wide = mine("mine_run_rhythm")
        narrow = mine("mine_run_rhythm", "--view", "original")
        self.assertGreater(wide["runs_examined"], 4 * narrow["runs_examined"])
        self.assertNotEqual(wide["gap_plan_units"]["median"],
                            narrow["gap_plan_units"]["median"])

    def test_the_default_still_reproduces_what_was_published(self):
        """The distribution, not the counts: the curated set has grown since
        2026-08-28, so there are more runs, but the shape is the same file.
        """
        published = json.loads(
            (ROOT / MINERS["mine_run_rhythm"]).read_text(encoding="utf-8"))
        fresh = mine("mine_run_rhythm")
        for stat in ("median", "q3"):
            self.assertEqual(fresh["gap_plan_units"][stat],
                             published["gap_plan_units"][stat], stat)
        self.assertAlmostEqual(fresh["gap_plan_units"]["q1"],
                               published["gap_plan_units"]["q1"], delta=0.02)


class PublishedArtifactTests(unittest.TestCase):
    """What the five files say about themselves today."""

    def test_the_published_files_predate_the_stamp_and_are_unlabelled(self):
        """Recorded rather than asserted-away: these were mined before the
        population was stamped, so none of them names its evidence. Re-mining
        them is the owner's call, and this fails once they are re-mined --
        which is the point, because then the claim below is stale.
        """
        unlabelled = []
        for artifact in MINERS.values():
            path = ROOT / artifact
            if not path.exists():
                continue
            if "population" not in json.loads(path.read_text(encoding="utf-8")):
                unlabelled.append(artifact)
        self.assertEqual(len(unlabelled), len(MINERS),
                         "a file gained a population stamp; re-check the report")


if __name__ == "__main__":
    unittest.main()
