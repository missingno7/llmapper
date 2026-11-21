"""tools.wiki_levels: a level page's wikitext becomes facts (counts, keys in route order, rewards, words)."""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import wiki_levels  # noqa: E402

#: written for the test in the wiki's markup, not copied from it
PAGE = """{{B1E3}}
[[File:Example.png|thumb|a caption]]
{{level_stats|designer=[[Some Designer|A. Designer]] & [[Other]]|song=1 - [[Tune]] (CD-Audio)|1=10|2=12|3=20'|4=30|5=31|secrets=3 + 1 [[Super Secret]]}}

== Walkthrough  ==

{{quote|quotation="Wade through the sewage to a valve. Turning it drains the pool. Take the [[Moon Key|moon key]] by the bridge, then the Skull Key at the lift, and the moon key again at the end."|attributedTo=[[Someone]]}}

== Enemies Present ==
*[[Cultist]]
*[[Bone Eel]]

== Weapons Available ==
*[[Flare Gun]]

== Secrets ==
*Behind a crate near the start. ''Reward: Doctor's Bag''
*Swim under the waterfall. ''Reward: [[Life Seed]]''
*A switch behind a plant.

== Trivia ==
*Something about pipes.
"""


class WikiLevelTests(unittest.TestCase):
    def test_a_page_becomes_facts(self):
        row = wiki_levels.parse("E3M3", PAGE)
        self.assertEqual(row["designer"], "A. Designer & Other")
        self.assertEqual(row["enemies_by_difficulty"], ["10", "12", "20'", "30", "31"])
        self.assertEqual((row["secrets_declared"], row["super_secrets"]), (3, 1))
        # the walkthrough is inside a quote template; keys counted once, in order
        self.assertEqual(row["keys_in_route_order"], ["moon", "skull"])
        self.assertEqual(row["enemies"], ["Cultist", "Bone Eel"])
        self.assertEqual(row["weapons"], ["Flare Gun"])
        self.assertEqual([s["reward"] for s in row["secrets"]], ["Doctor's Bag", "Life Seed", ""])
        self.assertIn("waterfall", row["secrets"][1]["words"])
        for word in ("sewage", "valve", "pool", "bridge", "lift"):
            self.assertIn(word, row["words"]["walkthrough"])
        self.assertIn("pipe", row["words"]["trivia"])

    def test_every_campaign_map_has_a_page(self):
        from bloodmap.corpus import campaign_maps

        try:
            names = {path.stem.upper() for path in campaign_maps()}
        except Exception:
            self.skipTest("no corpus")
        self.assertEqual(names - set(wiki_levels.TITLES), set())


if __name__ == "__main__":
    unittest.main()
