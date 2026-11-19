"""The mapper's own tools for learning: a tile lookup and a study.

The owner, 2026-11-18: "If you want to check on textures, you should be
able yourself to obtain it how it is used in other levels in which context
... But still you should understand what it looks like"; and "It should be
something like, I would like to build this, I am checking these levels how
they did it, etc. to get inspiration and really think stuff through. This
should allow you to learn by yourself".
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

E1M1 = Path("maps/blood/campaign/E1M1.MAP")
ART = Path("reference/blood")
CRYPT = Path("knowledge/blood/studies/crypt")
MANIFEST = Path("projects/blood-city/reports/build-manifest.json")


@unittest.skipUnless(E1M1.exists() and ART.exists(), "no corpus or no ART")
class TileUsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools import tile_usage

        cls.tool = tile_usage
        cls.seen = tile_usage.scan([E1M1], only={346, 504, 128})

    def test_346_is_a_tomb_top_and_a_door_leaf(self):
        #: the owner: "346 can be used for multiple things, it can even be
        #: a door texture"
        roles = self.seen[346].summary()["roles"]
        self.assertIn("top", roles)
        self.assertEqual((roles["top"]["short_side"],
                          roles["top"]["long_side"]), (1024, 2048))
        self.assertIn("leaf", roles)

    def test_the_picture_says_what_a_tile_is(self):
        with tempfile.TemporaryDirectory() as folder:
            slab = self.tool.picture(346, Path(folder))
            lattice = self.tool.picture(144, Path(folder))
            self.assertTrue(Path(slab["picture"]).exists())
        self.assertEqual(slab["pixels"], [64, 128])
        self.assertFalse(slab["is_mask"])
        #: the tile that drew magenta on a solid wall
        self.assertTrue(lattice["is_mask"])

    def test_the_owner_s_name_heads_the_report(self):
        name = self.tool.owner_name(504)
        #: the lookup that would have kept 504 off a coffin lid
        self.assertIn("never a material choice", name)


class StudyTests(unittest.TestCase):
    def test_an_empty_study_owes_every_heading(self):
        from tools import study

        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(study.notes_written(Path(folder)),
                             list(study.HEADINGS))
            Path(folder, "notes.md").write_text(
                "\n".join(f"## {h}\n\n{study.UNWRITTEN}\n"
                          for h in study.HEADINGS), "utf-8")
            self.assertEqual(len(study.notes_written(Path(folder))),
                             len(study.HEADINGS))

    @unittest.skipUnless(CRYPT.exists(), "no crypt study")
    def test_the_crypt_was_studied_and_the_notes_are_written(self):
        from tools import study

        self.assertEqual(study.notes_written(CRYPT), [])
        data = json.loads((CRYPT / "study.json").read_text("utf-8"))
        seeds = {s["seed"]: s for s in data["seeds"]}
        e1m1 = seeds["E1M1:150!"]
        #: what the study measured, and the crypt was then built from
        self.assertEqual(e1m1["floor"][0], 270)
        self.assertEqual(e1m1["walls"][0][0], 110)
        self.assertTrue(any(row["tile"] == 128 for row in e1m1["sprites"]))
        index = json.loads((CRYPT.parent / "index.json").read_text("utf-8"))
        self.assertIn("crypt", index["studies"])

    @unittest.skipUnless(MANIFEST.exists(), "the city is not built")
    def test_the_build_names_the_places_built_without_a_study(self):
        sheet = json.loads(MANIFEST.read_text("utf-8"))["character"]
        self.assertNotIn("St Gallow's crypt", sheet["unstudied"])
        self.assertEqual(sheet["places"]["St Gallow's crypt"]["study"],
                         "crypt")
        #: honest about the rest: the others were built before the rule
        self.assertIn("arcade concourse", sheet["unstudied"])
        #: the four studied the same day name their study
        for name, slug in (("harbour", "harbour"), ("saloon", "saloon"),
                           ("St Gallow's nave", "church"),
                           ("Aldermack auditorium", "theatre")):
            self.assertEqual(sheet["places"][name]["study"], slug)
            self.assertNotIn(name, sheet["unstudied"])


if __name__ == "__main__":
    unittest.main()
