"""The passage oracle: does a body get through a moving aperture?

The engine half needs Windows, NBlood and Blood's game data, so what is
covered here is the half that decides what a run *meant*: parsing the
engine's trajectory, and the two-clause verdict over it. That is where the
earlier attempts at this went wrong -- one read a spawn inside the exit
sector as passage -- so it is the half worth pinning down.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from bloodmap.oracle import (
    OracleError, _read_trajectory, passage_verdict, run_nblood_passage_oracle,
)


def probe(sectors, **kwargs):
    """A probe result carrying a made-up trajectory through `sectors`."""
    return {
        "trajectory": [{"tick": index, "game_time": index // 30,
                        "sector": sector, "x": 0, "y": 0, "z": 0}
                       for index, sector in enumerate(sectors)],
        **kwargs,
    }


class PassageVerdictTest(unittest.TestCase):
    def test_a_body_that_reaches_the_far_sector_passes(self):
        verdict = passage_verdict(probe([0, 0, 2, 2, 1, 1]), [1])
        self.assertTrue(verdict["passed"])
        self.assertTrue(verdict["crossed"])
        self.assertEqual(verdict["sectors_visited"], [0, 2, 1])
        self.assertEqual(verdict["arrived_tick"], 4)

    def test_a_body_that_never_leaves_the_near_room_fails(self):
        verdict = passage_verdict(probe([0, 0, 0, 0]), [1])
        self.assertFalse(verdict["passed"])
        self.assertFalse(verdict["crossed"])
        self.assertIsNone(verdict["arrived_tick"])

    def test_reaching_the_aperture_but_not_the_far_side_fails(self):
        # Standing inside the rotor is not getting through it.
        verdict = passage_verdict(probe([0, 2, 2, 0]), [1])
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["sectors_visited"], [0, 2])

    def test_spawning_beyond_the_aperture_is_not_passage(self):
        # The clause that matters. An earlier attempt at this oracle spawned
        # the body in the exit sector and read the result back as passage.
        verdict = passage_verdict(probe([1, 1, 1]), [1])
        self.assertFalse(verdict["passed"])
        self.assertTrue(verdict["crossed"])
        self.assertTrue(verdict["began_beyond_the_aperture"])

    def test_a_run_that_produced_no_ticks_is_not_a_pass(self):
        # What every rotor probe actually did: the driver refused the map and
        # wrote nothing. Silence is not evidence of blocking, and it is
        # certainly not evidence of passage.
        verdict = passage_verdict(probe([]), [1])
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["ticks"], 0)
        self.assertEqual(verdict["start_sector"], -1)

    def test_any_of_several_far_sectors_counts(self):
        verdict = passage_verdict(probe([0, 0, 5]), [1, 5])
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["far_sectors"], [1, 5])

    def test_the_first_arrival_is_the_one_reported(self):
        verdict = passage_verdict(probe([0, 1, 0, 1]), [1])
        self.assertEqual(verdict["arrived_tick"], 1)


class TrajectoryReadingTest(unittest.TestCase):
    def test_missing_file_reads_as_no_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(_read_trajectory(Path(directory) / "nope"), [])

    def test_a_partial_final_line_does_not_lose_the_rest(self):
        # A run killed on the wall clock leaves the last line half-written.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trajectory.ndjson"
            path.write_text(
                json.dumps({"tick": 0, "sector": 0}) + "\n"
                + json.dumps({"tick": 1, "sector": 1}) + "\n"
                + '{"tick":2,"sec',
                encoding="utf-8")
            samples = _read_trajectory(path)
        self.assertEqual([item["sector"] for item in samples], [0, 1])

    def test_a_torn_line_in_the_middle_does_not_end_the_reading(self):
        # Interleaved writes tear a line anywhere, not only at the end. A
        # reader that stops at the first bad one silently shortens the run,
        # and a shortened run is one that never reached the far side.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trajectory.ndjson"
            path.write_text(
                json.dumps({"tick": 0, "sector": 0}) + "\n"
                + '{"tick":1,"sec' + "\n"
                + json.dumps({"tick": 2, "sector": 1}) + "\n",
                encoding="utf-8")
            samples = _read_trajectory(path)
        self.assertEqual([item["sector"] for item in samples], [0, 1])

    def test_blank_lines_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trajectory.ndjson"
            path.write_text('\n{"tick":0,"sector":4}\n\n', encoding="utf-8")
            self.assertEqual(len(_read_trajectory(path)), 1)


class PassageArgumentTest(unittest.TestCase):
    """The oracle refuses to run rather than reporting on nothing."""

    def setUp(self):
        if os.name != "nt":
            self.skipTest("the passage oracle currently requires Windows")
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.map = self.root / "probe.MAP"
        self.map.write_bytes(b"not really a map")
        self.nblood = self.root / "nblood.exe"
        self.nblood.write_bytes(b"")
        self.addCleanup(self.directory.cleanup)

    def call(self, **overrides):
        arguments = {"map_path": self.map, "far_sectors": [1],
                     "nblood": self.nblood, "game_dir": self.root}
        arguments.update(overrides)
        return run_nblood_passage_oracle(**arguments)

    def test_a_missing_map_is_refused(self):
        with self.assertRaises(OracleError):
            self.call(map_path=self.root / "absent.MAP")

    def test_a_missing_executable_is_refused(self):
        with self.assertRaises(OracleError):
            self.call(nblood=self.root / "absent.exe")

    def test_a_missing_game_directory_is_refused(self):
        with self.assertRaises(OracleError):
            self.call(game_dir=self.root / "absent")

    def test_no_far_sector_is_refused(self):
        # Without one the question has no answer, and "passed" would mean
        # nothing at all.
        with self.assertRaises(OracleError):
            self.call(far_sectors=[])

    def test_an_absurd_time_limit_is_refused(self):
        with self.assertRaises(OracleError):
            self.call(game_seconds=0)
        with self.assertRaises(OracleError):
            self.call(game_seconds=100000)


if __name__ == "__main__":
    unittest.main()
