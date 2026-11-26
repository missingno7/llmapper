"""The city's build names the places it built without a study."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

MANIFEST = Path("projects/blood-city/reports/build-manifest.json")


class StudyTests(unittest.TestCase):
    @unittest.skipUnless(MANIFEST.exists(), "the city is not built")
    def test_the_build_names_the_places_built_without_a_study(self):
        sheet = json.loads(MANIFEST.read_text("utf-8"))["character"]
        self.assertNotIn("St Gallow's crypt", sheet["unstudied"])
        self.assertEqual(sheet["places"]["St Gallow's crypt"]["study"],
                         "crypt")
        #: the last one built before the rule was studied on 2026-11-25
        self.assertEqual(sheet["unstudied"], [])
        #: the four studied the same day name their study
        for name, slug in (("harbour", "harbour"), ("saloon", "saloon"), ("arcade concourse", "arcade"),
                           ("St Gallow's nave", "church"),
                           ("Aldermack auditorium", "aldermack-rebuild")):
            self.assertEqual(sheet["places"][name]["study"], slug)
            self.assertNotIn(name, sheet["unstudied"])


if __name__ == "__main__":
    unittest.main()
