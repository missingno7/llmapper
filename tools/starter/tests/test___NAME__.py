"""__TITLE__ builds, can be finished, and builds the same map twice."""

from __future__ import annotations

import runpy
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


class Builds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = staticmethod(runpy.run_path(str(PROJECT / "level" / "build.py"))["build"])
        cls.made = cls.build(write=False)

    def test_no_gate_refuses_it(self):
        self.assertEqual(self.made.refused, [])
        self.assertEqual([row for row in self.made.manifest["rules"]["open"] if row["severity"] == "error"], [])

    def test_it_can_be_finished(self):
        from bloodmap import completion

        mark = completion.read(self.made.disk)
        self.assertTrue(mark["exits"], "nothing ends the level")
        self.assertTrue(any(e["reached"] for e in mark["exits"]), "the exit is not reached")

    def test_the_same_source_builds_the_same_map(self):
        from bloodmap.format import encode_map

        self.assertEqual(encode_map(self.build(write=False).disk), encode_map(self.made.disk))


if __name__ == "__main__":
    unittest.main()
