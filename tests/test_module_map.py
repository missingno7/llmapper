"""The module map is a true map: every module is on it, and it is current.

`docs/module-map.md` is what an agent reads to find out whether something
already exists. A page like that is worth exactly as much as it is complete,
so its completeness is tested: a new module has to be placed in a layer, has
to say what it is in its own docstring, and the page has to be regenerated.
"""

from __future__ import annotations

import unittest

from tools import module_map


class ModuleMapTests(unittest.TestCase):
    def test_every_module_and_tool_is_placed_and_says_what_it_is(self):
        self.assertEqual(module_map.problems(), [])

    def test_the_page_is_what_the_generator_writes_today(self):
        self.assertTrue(module_map.OUTPUT.exists(),
                        "run python -m tools.module_map")
        self.assertEqual(
            module_map.OUTPUT.read_text(encoding="utf-8"), module_map.render(),
            "docs/module-map.md is out of date; run python -m tools.module_map")

    def test_a_sentence_is_one_line_and_ends_where_the_sentence_does(self):
        path = module_map.module_path("bloodmap", "corpus")
        said = module_map.first_sentence(path)
        self.assertNotIn("\n", said)
        self.assertTrue(said.startswith("The local map corpus"), said)
        self.assertTrue(said.endswith("."), said)


if __name__ == "__main__":
    unittest.main()
