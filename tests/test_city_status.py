"""The city's status is data the build writes, and it is never out of date.

Two pages used to say where the city stood. One gave September's 215
sectors and a 7,000-wall budget; the other called the full city "the older
artifact" while every later session worked on it. What each place's critique
had found lived in one agent's private notes. `status.py` generates the
answer from the build manifest and the critique rounds, and these tests fail
while what it wrote and what it would write differ.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVEL = ROOT / "projects" / "blood-city" / "level"
REPORTS = LEVEL.parent / "reports"


def _status():
    """Load the project's status module without leaving its folder on the path."""
    added = str(LEVEL) not in sys.path
    if added:
        sys.path.insert(0, str(LEVEL))
    try:
        spec = importlib.util.spec_from_file_location("blood_city_status",
                                                      LEVEL / "status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, module.gather()
    finally:
        if added:
            sys.path.remove(str(LEVEL))


@unittest.skipUnless((REPORTS / "build-manifest.json").exists()
                     and (LEVEL / "blood-city-current.MAP").exists(),
                     "the city has not been built")
class CityStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.status = _status()

    def test_the_two_files_are_what_the_sources_give_today(self):
        data, page = self.module.render(self.status)
        for name, text in (("status.json", data), ("STATUS.md", page)):
            with self.subTest(file=name):
                path = REPORTS / name
                self.assertTrue(path.exists(), "run projects/blood-city/level/status.py")
                current = path.read_text(encoding="utf-8").replace("\r\n", "\n")
                self.assertTrue(
                    current == text,
                    f"{name} is stale: run python projects/blood-city/level/status.py")

    def test_it_counts_the_map_that_is_on_disk(self):
        from bloodmap.format import read_map

        disk = read_map(LEVEL / "blood-city-current.MAP")
        build = self.status["build"]
        self.assertEqual((build["sectors"], build["walls"], build["sprites"]),
                         (len(disk.sectors), len(disk.walls), len(disk.sprites)))

    def test_every_place_on_the_character_sheet_is_reported(self):
        manifest = json.loads((REPORTS / "build-manifest.json").read_text("utf-8"))
        self.assertEqual([place["name"] for place in self.status["places"]],
                         list(manifest["character"]["places"]))

    def test_an_open_item_says_what_where_who_and_how_to_see_it(self):
        self.assertTrue(self.status["open"])
        for row in self.status["open"]:
            with self.subTest(kind=row["kind"]):
                self.assertTrue(row["says"])
                self.assertTrue(row["owner"])
                self.assertTrue(row["see"])
        counted = sum(self.status["open_by_kind"].values())
        self.assertEqual(counted, len(self.status["open"]))

    def test_an_owner_that_names_a_file_names_one_that_exists(self):
        checked = 0
        for row in self.status["open"]:
            owner = row["owner"].split(":")[0].split(" ")[0]
            if "/" not in owner:
                continue
            checked += 1
            self.assertTrue((ROOT / owner).exists(), row["owner"])
        self.assertGreater(checked, 10)

    def test_a_place_that_failed_its_critique_carries_what_the_readers_said(self):
        failed = [place for place in self.status["places"]
                  if place["critique"] and not place["critique"]["passes"]]
        for place in failed:
            said = [row for row in self.status["open"]
                    if row["place"] == place["name"] and row["kind"] == "critique"]
            self.assertEqual(len(said),
                             len(place["critique"]["blocking"])
                             + len(place["critique"]["readers_missing"]),
                             place["name"])

    def test_the_brief_is_short_and_says_what_is_not_verified(self):
        _data, page = self.module.render(self.status)
        self.assertLess(len(page.splitlines()), 70)
        self.assertIn("## Not verified", page)
        self.assertIn("Do not edit", page)


if __name__ == "__main__":
    unittest.main()
