"""The campaign marks our readers: a shipped map can be finished, so a reading must get there.

The owner, 2026-11-19: "we should use corpus maps also to test our tools ...
if they can be used ... to be able to correctly understand them." Nothing here
was labelled by anyone. A campaign map can be finished, its keys can be picked
up, and it declares its own secret count; `bloodmap.completion` says what our
readers found of that, and `tools/reading_check.py` keeps the score. On the
day this was written the traversal reader reached the exit in 26 of 43 maps
and no map was read to its end. The score is held as a ratchet: it may only
be rewritten, never drift.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.helpers import campaign_maps, corpus_disk

ROOT = Path(__file__).resolve().parent.parent
SCORECARD = ROOT / "knowledge" / "blood" / "design" / "reading-scorecard-v1.json"


class MissedTests(unittest.TestCase):
    def _mark(self, **changed):
        mark = {"exits": [{"reached": True}], "exit_reached": True,
                "keys": [{"name": "kItemKeySkull", "reached": True}],
                "unreached": [], "space": 10, "locked": [{"key": 1}],
                "secrets": {"declared": 3, "credited_normal": 3, "credited_super": 1}}
        mark.update(changed)
        return mark

    def test_a_map_read_to_its_end_misses_nothing(self):
        from bloodmap import completion

        self.assertEqual(completion.missed(self._mark()), [])

    def test_each_shortfall_is_named(self):
        from bloodmap import completion

        said = completion.missed(self._mark(
            exit_reached=False, exits=[{"reached": False}],
            keys=[{"name": "kItemKeySkull", "reached": False}],
            unreached=[4, 5],
            secrets={"declared": 3, "credited_normal": 2, "credited_super": 0}))
        self.assertEqual(len(said), 4)
        self.assertIn("the exit is never reached", said)
        self.assertTrue(any("kItemKeySkull" in line for line in said))
        self.assertEqual(completion.missed(self._mark(exits=[], exit_reached=False))[0],
                         "no chain ends at the level's exit")

    def test_a_key_no_lock_wants_is_said(self):
        from bloodmap import completion

        mark = self._mark(locked=[])
        self.assertTrue(any("opens nothing" in line for line in completion.missed(mark)))
        mark = self._mark(locked=[{"key": 1}])
        self.assertEqual(completion.missed(mark), [])

    def test_a_super_secret_is_not_counted_against_the_total(self):
        """The number on channel 2 is a type: 0 normal, more super
        (endgame.cpp:240). E1M1 declares 11 and credits 11 and one super."""
        from bloodmap import completion

        self.assertEqual(completion.missed(self._mark(
            secrets={"declared": 3, "credited_normal": 3, "credited_super": 2})), [])


@unittest.skipUnless(campaign_maps(), "no campaign corpus")
class E1M1Tests(unittest.TestCase):
    """What E1M1 is, read off its own records, and what our readers make of it."""

    @classmethod
    def setUpClass(cls):
        from bloodmap import completion

        cls.mark = completion.read(corpus_disk("E1M1"), "E1M1")

    def test_the_player_starts_in_the_casket_and_the_newer_reader_gets_him_out(self):
        self.assertEqual(self.mark["start_sector"], 30)
        self.assertTrue(self.mark["exit_reached"])
        # the older reader never leaves the coffin: the lid opens on the
        # level-start channel, which it does not model
        self.assertEqual(self.mark["older_reader"]["final_reachable"], 2)
        self.assertFalse(self.mark["older_reader"]["exit_reachable"])

    def test_its_two_keys_and_what_each_works(self):
        # each key is there twice: lying as an item, and carried by a
        # cultist who drops it when killed (actor.cpp:3053)
        self.assertEqual(sorted(row["name"] for row in self.mark["keys"]),
                         ["dagger key, dropped by kDudeCultistShotgun",
                          "kItemKeyDagger", "kItemKeySkull",
                          "skull key, dropped by kDudeCultistShotgun"])
        self.assertTrue(all(row["reached"] for row in self.mark["keys"]))
        locked = {row["key_name"]: row for row in self.mark["locked"]}
        self.assertEqual(set(locked), {"skull", "dagger"})
        # the skull key works the chained rotating doors, s50 and s51
        self.assertIn("sector 50", locked["skull"]["answers"])
        self.assertIn("sector 51", locked["skull"]["answers"])
        self.assertEqual(locked["dagger"]["answers"], ["sector 94"])

    def test_it_ends_at_a_pushed_switch_and_counts_eleven_secrets(self):
        (way_out,) = self.mark["exits"]
        self.assertEqual((way_out["cause"], way_out["to"]),
                         ("push", "kChannelLevelExitNormal"))
        self.assertEqual(self.mark["secrets"],
                         {"declared": 11, "credited_normal": 11, "credited_super": 1})

    def test_it_is_read_as_the_areas_each_act_opens(self):
        """A gated area is the unit a map is played in, and the engine
        decides where it ends. A "room" is a guess with thresholds."""
        areas = self.mark["gated_areas"]
        self.assertEqual(areas[0]["opened_by"], ["nothing: open from the start"])
        self.assertGreater(len(areas), 3)
        self.assertEqual(sum(area["sectors"] for area in areas),
                         len(set(range(10**6)) & set(self._reached())))
        self.assertTrue(all(area["sectors"] > 0 for area in areas))

    def _reached(self):
        from bloodmap import bundle, completion

        views = bundle.build_bundle(corpus_disk("E1M1"), map_name="E1M1")["views"]
        return completion.reached_sectors(views["progression"])

    def test_the_whole_map_reading_names_all_of_it(self):
        from tools import catalog

        said = catalog.map_reading("E1M1")
        for heading in ("SAYS OF ITSELF", "ROOMS", "HOW IT IS FINISHED", "WIRING",
                        "MATERIALS", "HOW FAR OUR READERS GET"):
            self.assertIn(heading, said)
        self.assertIn("MORNINGSIDE", said)            # the cemetery's own gate
        self.assertIn("wants the skull key", said)
        self.assertIn("never reached", said)          # and it says where it fails


@unittest.skipUnless(campaign_maps() and SCORECARD.exists(), "no campaign corpus")
class ScorecardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools import reading_check

        cls.tool = reading_check
        cls.fresh = reading_check.gather()
        cls.committed = json.loads(SCORECARD.read_text(encoding="utf-8"))

    def test_the_score_is_the_one_the_readers_get_today(self):
        self.assertTrue(self.committed == self.fresh,
                        "run python -m tools.reading_check")

    def test_the_secret_reader_agrees_with_what_most_maps_declare(self):
        total = self.committed["total"]
        self.assertGreaterEqual(total["secret_counts_agree"], 39)

    def test_the_shortfall_is_stated_and_not_hidden(self):
        """The readers do not finish the campaign. The file says so."""
        total = self.committed["total"]
        self.assertEqual(total["maps"], len(campaign_maps()))
        short = [row for row in self.committed["maps"] if row["missed"]]
        self.assertEqual(len(short), total["maps"] - total["read_to_the_end"])
        for row in short:
            self.assertTrue(all(isinstance(line, str) and line for line in row["missed"]))


if __name__ == "__main__":
    unittest.main()
