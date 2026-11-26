"""The critic bench is kept as it was run: its answers parse and its key names nothing."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "experiments" / "critics" / "critic_bench.py"


def _critic_bench():
    spec = importlib.util.spec_from_file_location("critic_bench", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CriticBenchTests(unittest.TestCase):
    """The owner: "which model is best critic ... how to do objective test"."""

    def test_an_answer_with_a_fault_is_parsed(self):
        critic_bench = _critic_bench()

        row = critic_bench.parse("NAME: Railway track\nSURE: 4\n"
                                 "FAULT: Yes\nWHAT: rails run across\n")
        self.assertTrue(row["ok"] and row["fault"])
        self.assertFalse(critic_bench.parse("NAME: x\n")["ok"])

    def test_every_fault_has_a_clean_twin_and_the_key_names_nothing(self):
        critic_bench = _critic_bench()

        path = critic_bench.BENCH / "key.json"
        if not path.exists():
            self.skipTest("no benchmark built")
        key = critic_bench.json.loads(path.read_text("utf-8"))
        kinds = [row["kind"] for row in key.values()]
        self.assertEqual(kinds.count("fault"), len(critic_bench.FAULTS))
        self.assertGreaterEqual(kinds.count("clean") + kinds.count("naming"),
                                2 * kinds.count("fault"))
        twins = {row["truth"].split(": ")[1] for row in key.values()
                 if row["kind"] == "clean"}
        self.assertEqual(twins, {pose for pose, _ in
                                 critic_bench.FAULTS.values()})
        for q in key:
            self.assertRegex(q, r"^b_\d\d$")


if __name__ == "__main__":
    unittest.main()
