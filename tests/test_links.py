"""The two ways down that are links: the crypt's slab (E4M4 s159) and the pump station's ramp (E2M1 s20), as built."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.reachability import link_pairs
from bloodmap.roomoverroom import MIRROR_TILE
from bloodmap.sector_geom import outline_and_holes

LEVEL = Path("projects/blood-city/level")


class Links(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import l3_church
        import l3_shed
        cls.C, cls.P = l3_church, l3_shed
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.pairs = {row["link_id"]: row["sectors"] for row in link_pairs(cls.disk)}

    def sector(self, i):
        return record_fields(self.disk.sectors[i])

    def walls(self, i):
        s = self.sector(i)
        return [(record_fields(self.disk.walls[w]), record_fields(self.disk.walls[record_fields(self.disk.walls[w])["point2"]]))
                for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"])]

    def test_each_half_is_one_sector_of_one_plan_with_the_plane_between(self):
        for link, rect in ((self.C.SLAB_LINK, self.C.CRYPT_LIFT), (self.P.RAMP_LINK, self.P.RAMP)):
            upper, lower = self.pairs[link]
            a, b = self.sector(upper), self.sector(lower)
            self.assertEqual((a["floor_picnum"], b["ceiling_picnum"]), (MIRROR_TILE, MIRROR_TILE))
            self.assertEqual((a["floor_z"], b["ceiling_z"]), (8192, 8192))
            x0, y0, x1, y1 = rect
            for i in (upper, lower):
                outline, holes = outline_and_holes(self.disk, i)
                self.assertEqual((sorted(outline), holes), (sorted([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), []))
            # nobody sees the plane from anywhere it is cut: no other sector has a mirror floor at that plan
            others = [i for i, s in enumerate(self.disk.sectors) if record_fields(s)["floor_picnum"] == MIRROR_TILE and i != upper
                      and any(x0 <= w["x"] <= x1 and y0 <= w["y"] <= y1 for w, _n in self.walls(i))]
            self.assertEqual(others, [])
            for k, s in ((upper, 11), (lower, 12)):
                markers = [record_fields(sp) for sp in self.disk.sprites if record_fields(sp)["sector"] == k and record_fields(sp)["type"] == s]
                self.assertEqual([(m["z"], m["status"]) for m in markers], [(8192, 0)])

    def test_the_slab_stops_a_step_under_the_floor(self):
        lower = self.pairs[self.C.SLAB_LINK][1]
        extra = record_extra(self.disk.sectors[lower])
        self.assertEqual(self.sector(lower)["type"], 600)
        self.assertEqual((extra["off_floor_z"] - 8192, extra["on_floor_z"]), (4096, self.C.CRYPT_FLOOR))
        self.assertEqual((extra["off_ceiling_z"], extra["on_ceiling_z"]), (8192, 8192))

    def test_the_ramp_runs_from_a_hand_under_the_plane_to_a_step_over_the_cellar(self):
        upper, lower = self.pairs[self.P.RAMP_LINK]
        s = self.sector(lower)
        x0, _y0, x1, _y1 = self.P.RAMP
        first = self.walls(lower)[0]
        self.assertEqual(first[0]["x"], x0)                       # its first wall is its foot: the hinge
        slope = s.get("floor_heinum", s.get("floor_slope"))
        head = s["floor_z"] + slope * (x1 - x0) * 16 // 4096
        self.assertTrue(512 <= head - 8192 <= 2048, head)
        self.assertEqual(self.P.CELLAR_FLOOR_Z - s["floor_z"], 1024)
        self.assertLess(abs(slope), 2753)                         # E2M1's own is 2,752
        out = [record_fields(self.disk.sectors[w["next_sector"]])["floor_z"] for w, _n in self.walls(lower) if w["next_sector"] >= 0]
        self.assertEqual(out, [self.P.CELLAR_FLOOR_Z])
        into = [(w["x"], n["x"]) for w, n in self.walls(upper) if w["next_sector"] >= 0]
        self.assertEqual(into, [(x1, x1)])                        # over its high end and nowhere else

    def test_nothing_but_the_links_joins_the_deep_layer_to_the_city(self):
        """What `references/sewers-outside.md` needs before the shift: the only portals left are the cellar's."""
        deep = {i for i, s in enumerate(self.disk.sectors) if record_fields(s)["floor_z"] >= 40000}
        deep.add(self.pairs[self.C.SLAB_LINK][1])
        deep.add(self.pairs[self.P.RAMP_LINK][1])
        out = {(i, w["next_sector"]) for i in deep for w, _n in self.walls(i) if w["next_sector"] >= 0 and w["next_sector"] not in deep}
        self.assertEqual(out, set())


if __name__ == "__main__":
    unittest.main()
