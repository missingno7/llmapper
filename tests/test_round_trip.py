"""The round trip, and the proof that "0 misreadings" is not vacuous.

A rebuild that writes nothing is byte-identical too. So the first thing these
tests establish is that the tool CAN fail: a claim with a value one away from
the original must come back as a named misreading, with the record, the field,
the reader and both numbers. Only then does a clean run on E3M1 mean anything.

(`verify-the-thing-not-the-call`: a constructor that returns without raising
is not evidence, and neither is a diff that finds nothing because it looked
at nothing.)
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest


def _corpus(name):
    from bloodmap.patterns import corpus_map_path

    try:
        return corpus_map_path(name)
    except Exception as error:  # pragma: no cover - corpus-dependent
        raise unittest.SkipTest(f"{name} is not readable here: {error}")


def _claims(name):
    path = pathlib.Path(f"projects/{name}-decompiled/facts/claims.jsonl")
    if not path.exists():
        raise unittest.SkipTest(f"{name} has no fact store here")
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


class TheDetectorDetects(unittest.TestCase):
    """One wrong claim, one named misreading."""

    def test_a_claim_off_by_one_is_reported_with_both_values(self):
        from bloodmap.format import read_map
        from tools.round_trip import misreadings, rebuild

        path = _corpus("E3M1")
        original = read_map(path)
        working = read_map(path)
        truth = int(original.walls[1].fields["picnum"])
        claim = {"record": "wall:1", "field": "picnum", "value": truth + 1,
                 "_layer": 2, "_reader": "a test", "aspect": "surface:0001"}
        rebuild(working, [claim])
        found = misreadings(original, working, [claim])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["record"], "wall:1")
        self.assertEqual(found[0]["field"], "picnum")
        self.assertEqual(found[0]["original"], truth)
        self.assertEqual(found[0]["rebuilt"], truth + 1)
        self.assertEqual(found[0]["reader"], "a test")

    def test_a_wrong_claim_on_an_extra_is_caught_too(self):
        """`xsector:52.on_floor_z` is a field of the XSECTOR, not the sector,
        and a reader that means one must not be able to write the other."""
        from bloodmap.format import read_map
        from tools.round_trip import misreadings, rebuild

        path = _corpus("E3M1")
        original = read_map(path)
        working = read_map(path)
        extra = original.sectors[52].extra
        self.assertIsNotNone(extra, "sector 52 is E3M1's Z-motion door")
        truth = int(extra.fields["on_floor_z"])
        claim = {"record": "xsector:52", "field": "on_floor_z",
                 "value": truth + 64, "_layer": 5,
                 "_reader": "bloodmap.read_mechanisms", "aspect": "a test"}
        rebuild(working, [claim])
        found = misreadings(original, working, [claim])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["where"], "extra")
        self.assertEqual(found[0]["original"], truth)

    def test_a_claim_naming_a_field_the_map_has_not_is_unwritable(self):
        from bloodmap.format import read_map
        from tools.round_trip import THE_MAP_HAS_NO_FIELD, rebuild

        working = read_map(_corpus("E3M1"))
        done = rebuild(working, [{"record": "sector:0", "field": "vibes",
                                  "value": 1, "_layer": 8,
                                  "_reader": "a test", "aspect": "a test"}])
        self.assertEqual(done["written"], [])
        self.assertEqual(done["unwritable"][0]["because"], THE_MAP_HAS_NO_FIELD)

    def test_a_claim_naming_a_record_the_map_has_not_is_unwritable(self):
        from bloodmap.format import read_map
        from tools.round_trip import NO_SUCH_RECORD, rebuild

        working = read_map(_corpus("E3M1"))
        done = rebuild(working, [{"record": "sector:99999", "field": "floor_z",
                                  "value": 1, "_layer": 1,
                                  "_reader": "a test", "aspect": "a test"}])
        self.assertEqual(done["unwritable"][0]["because"], NO_SUCH_RECORD)


class TheRebuildIsAWholeMap(unittest.TestCase):
    def test_the_rebuilt_map_keeps_every_index(self):
        """The property the owner's walk depends on: sector 118 in the editor
        is sector 118 in both files, so a finding carries an id."""
        from bloodmap.format import read_map
        from tools.round_trip import round_trip

        path = _corpus("E3M1")
        if not pathlib.Path("projects/e3m1-decompiled/facts").exists():
            self.skipTest("E3M1 has no fact store here")
        with tempfile.TemporaryDirectory() as work:
            out = str(pathlib.Path(work) / "E3M1.MAP")
            round_trip(str(path), "projects/e3m1-decompiled/facts", out)
            before, after = read_map(path), read_map(out)
        self.assertEqual(len(before.sectors), len(after.sectors))
        self.assertEqual(len(before.walls), len(after.walls))
        self.assertEqual(len(before.sprites), len(after.sprites))
        for index, (a, b) in enumerate(zip(before.walls, after.walls)):
            self.assertEqual(a.fields["point2"], b.fields["point2"],
                             f"wall {index} changed which wall follows it")
            self.assertEqual(a.fields["next_sector"], b.fields["next_sector"],
                             f"wall {index} changed what is behind it")


class E3M1RoundTripsClean(unittest.TestCase):
    """The gate: every claim's own promise, on the map the model was read from."""

    @classmethod
    def setUpClass(cls):
        from tools.round_trip import round_trip

        path = _corpus("E3M1")
        _claims("e3m1")
        cls.work = tempfile.TemporaryDirectory()
        out = str(pathlib.Path(cls.work.name) / "E3M1.MAP")
        cls.result = round_trip(str(path), "projects/e3m1-decompiled/facts",
                                out)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_every_claim_reproduces_its_field(self):
        self.assertEqual(self.result["misreadings"], [])

    def test_every_claim_could_be_written_back(self):
        self.assertEqual(self.result["rebuild"]["unwritable"], [])

    def test_the_rebuild_writes_all_4298_claims(self):
        """Not vacuous: the count is the store's, and it is not zero."""
        self.assertEqual(self.result["rebuild"]["written"], 4300)
        self.assertEqual(self.result["coverage"]["rebuilt"], 4298)

    def test_the_rebuilt_map_is_byte_identical(self):
        self.assertTrue(self.result["byte_diff"]["identical"])

    def test_and_that_is_3_5_percent_of_the_map(self):
        """The number the round trip exists to make honest: byte-identical
        and 3.5% understood are the same run."""
        self.assertAlmostEqual(self.result["coverage"]["share"], 3.486,
                               places=2)
        self.assertGreater(self.result["coverage"]["copied"], 118000)
