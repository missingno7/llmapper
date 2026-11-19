"""`AGENTS.md` is the first page every agent session reads, so it is tested.

An agent trusts what it reads first. A command there that no longer exists
costs a session; a page that grows until it is skimmed costs every session.
These hold the page to the code: every module it tells an agent to run
exists, every file it links to is there, every catalogue key it uses as an
example resolves, and it stays short enough to be read whole.
"""

from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEF = ROOT / "AGENTS.md"
INDEX = ROOT / "knowledge" / "blood" / "design" / "mechanism-examples-v1.json"


class AgentsBriefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = BRIEF.read_text(encoding="utf-8")

    def test_claude_code_is_sent_to_the_same_page(self):
        self.assertEqual((ROOT / "CLAUDE.md").read_text(encoding="utf-8").strip(),
                         "@AGENTS.md")

    def test_it_is_short_enough_to_be_read_whole(self):
        self.assertLessEqual(len(self.text.splitlines()), 130,
                             "move detail into the page it belongs to and link it")

    def test_every_module_it_says_to_run_exists(self):
        named = set(re.findall(r"python -m ((?:tools|bloodmap|experiments)[\w.]*)", self.text))
        self.assertGreaterEqual(len(named), 5)
        for module in sorted(named):
            with self.subTest(module=module):
                self.assertIsNotNone(importlib.util.find_spec(module), module)

    def test_every_script_and_link_it_names_is_there(self):
        paths = set(re.findall(r"\]\(([^)#]+)\)", self.text))
        paths |= set(re.findall(r"python (projects/[\w./-]+\.py)", self.text))
        self.assertGreaterEqual(len(paths), 5)
        for path in sorted(paths):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists(), path)

    def test_every_library_name_it_cites_resolves(self):
        for dotted in ("bloodmap.corpus.campaign_maps", "bloodmap.corpus.named_maps",
                       "bloodmap.corpus.corpus_map_path", "bloodmap.model.record_fields",
                       "bloodmap.model.record_extra", "bloodmap.sector_geom.outline_and_holes",
                       "bloodmap.player_space.PLAYER_PROFILES",
                       "bloodmap.visual.run_observation"):
            module, _dot, name = dotted.rpartition(".")
            with self.subTest(name=dotted):
                self.assertTrue(name in self.text, f"the page does not name {name}")
                loaded = importlib.import_module(module)
                self.assertTrue(hasattr(loaded, name), dotted)

    def test_the_numbers_it_states_are_the_codes(self):
        from bloodmap.build_ir import BUILD_LIMITS, VANILLA_LIMITS
        from bloodmap.player_space import PLAYER_PROFILES

        blood = PLAYER_PROFILES["blood"]
        for value in (blood.standing_height, blood.body_width,
                      *BUILD_LIMITS.values(), *VANILLA_LIMITS.values()):
            self.assertTrue(str(value) in self.text, f"the page does not state {value}")

    @unittest.skipUnless(INDEX.exists(), "the mechanism index is not built")
    def test_the_catalogue_keys_it_uses_as_examples_resolve(self):
        from bloodmap import examples

        index = json.loads(INDEX.read_text(encoding="utf-8"))
        for said in ("conveyor", "sector:614", "kSwitchToggle", "channel:4",
                     "lesson:DOOR-SLIDING"):
            with self.subTest(said=said):
                self.assertTrue(said in self.text, f"the page does not use {said}")
                self.assertIsNotNone(examples.resolve(index, said), said)


if __name__ == "__main__":
    unittest.main()
