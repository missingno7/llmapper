"""The map that is played is the plan's map with what is under the city moved, and nothing else."""

import math
from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.reachability import link_pairs
from bloodmap.sector_geom import outline_and_holes, sector_at

LEVEL = Path("projects/blood-city/level")


class Release(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import release
        cls.R = release
        if not release.PLAN.exists() or not release.RELEASE.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.plan, cls.played = read_map(release.PLAN), read_map(release.RELEASE)
        cls.moved = release.under(cls.plan)

    def test_only_where_it_is_has_changed(self):
        dx, dy = self.R.SHIFT
        for part in ("sectors", "walls", "sprites"):
            self.assertEqual(len(getattr(self.plan, part)), len(getattr(self.played, part)))
        owner = {}
        for i, (a, b) in enumerate(zip(self.plan.sectors, self.played.sectors)):
            self.assertEqual((record_fields(a), record_extra(a)), (record_fields(b), record_extra(b)), i)
            s = record_fields(a)
            for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
                owner[w] = i
        for part, sector in (("walls", owner.__getitem__), ("sprites", lambda k: record_fields(self.plan.sprites[k])["sector"])):
            for k, (a, b) in enumerate(zip(getattr(self.plan, part), getattr(self.played, part))):
                f, g = dict(record_fields(a)), dict(record_fields(b))
                if sector(k) in self.moved:
                    f["x"] += dx
                    f["y"] += dy
                self.assertEqual(f, g, (part, k))
                self.assertEqual(record_extra(a), record_extra(b), (part, k))
        self.assertEqual(self.plan.header, self.played.header)

    def test_every_sprite_is_still_in_its_sector(self):
        """A sprite that is in its sector in the plan's map is in it in the played one, markers and all."""
        for k, (a, b) in enumerate(zip(self.plan.sprites, self.played.sprites)):
            f, g = record_fields(a), record_fields(b)
            if f["status"] in (10, 16) and 0 <= f["owner"] < len(self.plan.sectors):
                self.assertEqual(f["owner"] in self.moved, f["sector"] in self.moved, k)          # a mover and its markers go together
            self.assertEqual(g["x"] - f["x"], self.R.SHIFT[0] if f["sector"] in self.moved else 0, k)

    def test_nothing_lies_over_anything_it_did_not_already(self):
        """In plan, nothing that was moved lies over or under anything that was not."""
        from shapely import Polygon, unary_union
        rings = [Polygon(outline_and_holes(self.played, i)[0]).buffer(0) for i in range(len(self.played.sectors))]
        below = unary_union([rings[i] for i in self.moved])
        above = unary_union([rings[i] for i in range(len(rings)) if i not in self.moved])
        self.assertLess(below.intersection(above).area, 1)
        # and the nearest of it is farther from the streets than any ambience reaches (a sixteenth of a unit to one of the engine's)
        streets = unary_union([rings[i] for i in range(len(rings)) if i not in self.moved
                               and record_fields(self.played.sectors[i])["floor_z"] <= 16384 and rings[i].bounds[0] >= 0])
        reach = max(record_extra(s)["data_2"] for s in self.played.sprites if record_fields(s)["type"] == 710)
        self.assertGreater(below.distance(streets) / 16, 2 * reach)

    def test_no_sound_of_the_sewers_reaches_a_street(self):
        ambiences = [(record_fields(s), record_extra(s)["data_2"]) for s in self.played.sprites if record_fields(s)["type"] == 710]
        deep = [(f, reach) for f, reach in ambiences if f["sector"] in self.moved]
        self.assertGreater(len(deep), 40)
        for x in range(0, 58 * 1024, 1024):
            for y in range(-18 * 1024, 56 * 1024, 1024):
                for f, reach in deep:
                    self.assertGreater(math.dist((f["x"], f["y"]), (x, y)) / 16, reach)

    def test_the_links_are_the_same_links(self):
        pairs = {r["link_id"]: r["sectors"] for r in link_pairs(self.played)}
        self.assertEqual(pairs, {r["link_id"]: r["sectors"] for r in link_pairs(self.plan)})
        for link, (upper, lower) in pairs.items():
            a, _h = outline_and_holes(self.played, upper)
            b, _h = outline_and_holes(self.played, lower)
            marks = {}
            for s in self.played.sprites:
                f = record_fields(s)
                if f["type"] in (9, 10, 11, 12) and record_extra(s)["data_1"] == link:
                    marks[f["type"] % 2] = (f["x"], f["y"])
            dx, dy = marks[0][0] - marks[1][0], marks[0][1] - marks[1][1]
            # a link is a translation, and it lays one half exactly on the other
            from shapely import Polygon
            over = Polygon([(x + dx, y + dy) for x, y in a]).buffer(0).symmetric_difference(Polygon(b).buffer(0)).area
            was = {}
            for s in self.plan.sprites:
                f = record_fields(s)
                if f["type"] in (9, 10, 11, 12) and record_extra(s)["data_1"] == link:
                    was[f["type"] % 2] = (f["x"], f["y"])
            px, py = was[0][0] - was[1][0], was[0][1] - was[1][1]
            c, _h = outline_and_holes(self.plan, upper)
            d, _h = outline_and_holes(self.plan, lower)
            before = Polygon([(x + px, y + py) for x, y in c]).buffer(0).symmetric_difference(Polygon(d).buffer(0)).area
            self.assertAlmostEqual(over, before, delta=1, msg=link)

    def test_it_is_inside_builds_map_and_the_way_through_it_is_the_same(self):
        for w in self.played.walls:
            f = record_fields(w)
            self.assertLess(max(abs(f["x"]), abs(f["y"])), self.R.EXTENT)
        # a point in the sewers, found where it now is
        x, y = 23 * 1024 + self.R.SHIFT[0], 20 * 1024 + self.R.SHIFT[1]
        self.assertEqual(sector_at(self.played.to_level_ir(), x, y, floor_near=61440),
                         sector_at(self.plan.to_level_ir(), 23 * 1024, 20 * 1024, floor_near=61440))


if __name__ == "__main__":
    unittest.main()
