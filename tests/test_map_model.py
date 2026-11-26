"""The cut-away model of a whole map: what tools.map_model builds before anything is drawn."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import corpus_map

from tools import map_model as mm


class E3M1Section(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = corpus_map("E3M1.MAP")
        if not path.exists():
            raise unittest.SkipTest("the Blood corpus is not here")
        cls.path = path
        played = mm.as_played(path, tempfile.mkdtemp(), empty=True)
        m0 = mm.build(played, keep=lambda i, q, s: False)
        cls.ok = mm.reachable(m0, mm.start_sector(path))
        cls.cut = 1.6 * mm.BODY
        cls.m = mm.build(played, keep=lambda i, q, s: i in cls.ok, cut=cls.cut)
        cls.caps, cls.bounds, cls.base, cls.top, cls.low = mm.section_caps(cls.m)

    def test_the_start_reaches_most_of_the_map(self):
        self.assertIn(mm.start_sector(self.path), self.ok)
        self.assertGreater(len(self.m["ok"]), 300)

    def test_no_room_has_a_ceiling(self):
        self.assertFalse([k for k in self.m["tris"] if k[0] != "bill" and k[2] == "ceil"])

    def test_nothing_is_drawn_over_its_sector_cut(self):
        """Walls end at the cut over their own floor, so nothing stands over the highest cut, and E3M1's sky walls (11.5 high) are cut down."""
        for k, v in self.m["tris"].items():
            if k[0] == "bill" or not len(v):
                continue
            self.assertLessEqual(float(v[:, 1].max()), self.top + 1e-3, k)
        flat_highest = -min(self.m["sectors"][i]["floor_z"] for i in self.m["ok"]) / mm.ZU
        # a sloped floor rises over its stored height, but not to the sky
        self.assertGreaterEqual(self.top, flat_highest + self.cut / mm.ZU - 1e-3)
        self.assertLess(self.top, 11.5)

    def test_rooms_go_on_up_to_the_cut_where_their_ceiling_is_lower(self):
        wells = self.m["tris"].get((-1, 0, "well"))
        self.assertIsNotNone(wells)
        self.assertGreater(len(wells), 0)

    def test_the_solid_is_capped_and_the_model_stands_on_its_base(self):
        caps, sides, _ = self.caps
        self.assertGreater(len(caps), 0)
        self.assertGreater(len(sides), 0)
        self.assertAlmostEqual(float(sides[:, 1].min()), self.base, places=4)
        self.assertLessEqual(float(caps[:, 1].max()), self.top + 1e-3)
        self.assertLess(self.base, self.low)

    def test_the_camera_frames_the_outline(self):
        eye, at = mm.fit_camera(self.caps[1][:, :3], 20, 42, 32, 4 / 3)
        self.assertGreater(eye[1], at[1])


class Resolve(unittest.TestCase):
    def test_a_path_and_a_corpus_name(self):
        here = Path(mm.__file__)
        self.assertEqual(mm.resolve(str(here)), here)
        if corpus_map("E3M1.MAP").exists():
            self.assertEqual(mm.resolve("E3M1").name.upper(), "E3M1.MAP")


if __name__ == "__main__":
    unittest.main()
