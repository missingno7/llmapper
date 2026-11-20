"""bloodmap.tile_contexts: what a tile is used as, where, on whose evidence."""

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import tile_contexts as tc  # noqa: E402


class _Isolated(unittest.TestCase):
    """Point the catalogue at an empty folder for the test, then put it back."""

    def setUp(self):
        self._home, self._readings = tc.HOME, tc.READINGS
        self._dir = tempfile.TemporaryDirectory()
        tc.HOME = pathlib.Path(self._dir.name)
        tc.READINGS = tc.HOME / "readings.jsonl"
        tc.clear_cache()

    def tearDown(self):
        tc.HOME, tc.READINGS = self._home, self._readings
        tc.clear_cache()
        self._dir.cleanup()


class ReadingTests(_Isolated):
    def test_a_reading_must_say_what_it_was_read_from(self):
        with self.assertRaises(tc.TileContextError):
            tc.record(364, slot="two_sided_lower", is_="a drum's face", evidence="")

    def test_a_reading_is_the_weakest_evidence_and_attests_its_slot(self):
        tc.record(99999, slot="two_sided_lower", place="outdoors",
                  is_="a drum's face", evidence="a frame")
        rows = tc.contexts(99999)
        self.assertEqual(rows[-1]["source"], "agent")
        self.assertEqual(tc.attestation(99999, "two_sided_lower")["source"], "agent")
        self.assertIsNone(tc.attestation(99999, "floor"))

    def test_a_misfit_is_a_warning_never_permission(self):
        tc.record(99998, slot="sprite_wall", place="outdoors", fits=False,
                  is_="reads as eyes at street distance", evidence="a blind reader")
        self.assertIsNone(tc.attestation(99998, "sprite_wall", "outdoors"))
        self.assertFalse(tc.contexts(99998)[-1]["fits"])


@unittest.skipUnless((ROOT / "maps" / "blood" / "campaign" / "E1M1.MAP").exists(),
                     "no campaign")
class MiningTests(_Isolated):
    def test_mining_a_map_counts_its_uses_by_slot_and_place(self):
        from bloodmap.corpus import corpus_map_path
        from bloodmap.format import read_map

        disk = read_map(corpus_map_path("E1M1"))
        table = tc.mine([("E1M1", disk, {})])
        self.assertEqual(table["maps"], 1)
        slots = {key.split("|")[0] for rows in table["tiles"].values() for key in rows}
        self.assertTrue({"floor", "one_sided_middle", "sprite_face"} <= slots)
        tc.save_mined("blood-campaign", table, maps=["E1M1"])
        tc.clear_cache()
        tile, rows = next(iter(table["tiles"].items()))
        key = next(iter(rows))
        slot, place = key.split("|")
        best = tc.attestation(int(tile), slot, place)
        self.assertEqual(best["source"], "blood-campaign")

    def test_the_owners_name_attests_no_slot(self):
        # 2476: the owner names it and notes its dual role; neither says where
        # it may go, so with nothing mined nothing is attested
        self.assertTrue(any(r["source"] == "owner" for r in tc.contexts(2476)))
        self.assertIsNone(tc.attestation(2476, "floor"))


if __name__ == "__main__":
    unittest.main()
