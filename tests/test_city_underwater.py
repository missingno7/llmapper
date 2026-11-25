"""Read the drowned places from the city's MAP bytes: every surface can be climbed out of, every swim is short, and the branch is only dived to."""

import heapq
from math import dist, hypot
from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.reachability import link_pairs
from bloodmap.sector_geom import outline_and_holes, sector_at, sector_walls, wall_segment
from bloodmap.supplies import Geometry, Walk

LEVEL = Path("projects/blood-city/level")
PU = 1024
#: what a leap out of the water passes (`knowledge/blood/studies/underwater`,
#: "Climbing out"), and plan units in ten seconds at a walk
CLIMB, AIR = 4784, 16


class DrownedPlaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import underwater
        cls.U = underwater
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.level = cls.disk.to_level_ir()
        cls.geo = Geometry(cls.disk)
        cls.sector = [record_fields(s) for s in cls.disk.sectors]
        cls.extra = [record_extra(s) or {} for s in cls.disk.sectors]
        cls.under = {i for i, x in enumerate(cls.extra) if x.get("underwater")}
        #: link id -> (the surface's sector, the water's, their markers)
        cls.pairs = {p["link_id"]: (*p["sectors"], *p["sprites"]) for p in link_pairs(cls.disk)
                     if record_fields(cls.disk.sprites[p["sprites"][0]])["type"] == 9}
        cls.upper = {row[0] for row in cls.pairs.values()}

    def top(self, name):
        return self.pairs[self.U.LINKS[name]][0]

    def below(self, name):
        return self.pairs[self.U.LINKS[name]][1]

    def at(self, x, y, floor):
        found = sector_at(self.level, round(x * PU), round(y * PU), floor_near=floor)
        self.assertEqual(self.sector[found]["floor_z"], floor, (x, y))
        return found

    def doors(self, sector):
        """Every portal of a sector: its wall, where it leads, whether it blocks."""
        for w in sector_walls(self.disk, sector):
            f = record_fields(self.disk.walls[w])
            if f["next_sector"] >= 0:
                both = f["cstat"] | record_fields(self.disk.walls[f["next_wall"]])["cstat"]
                yield w, f["next_sector"], bool(both & 1)

    def rise(self, wall, here, there):
        """How far over the water the neighbour's floor is, at the wall's lower end (a ramp's foot)."""
        return self.sector[here]["floor_z"] - max(self.geo.height(there, *p) for p in wall_segment(self.disk, wall))

    def swim(self, start):
        seen, queue = {start}, [start]
        while queue:
            for _w, there, blocked in self.doors(queue.pop()):
                if not blocked and there in self.under and there not in seen:
                    seen.add(there)
                    queue.append(there)
        return seen

    def test_the_surfaces_are_at_one_translation_over_one_outline(self):
        from shapely.geometry import Polygon
        self.assertEqual(set(self.pairs), set(self.U.LINKS.values()))
        move = tuple(round(v * PU) for v in self.U.OFFSET)
        for link, (top, below, over, beneath) in self.pairs.items():
            a, b = record_fields(self.disk.sprites[over]), record_fields(self.disk.sprites[beneath])
            self.assertEqual((b["x"] - a["x"], b["y"] - a["y"]), move, link)
            self.assertEqual({a["status"], b["status"]}, {0}, "another list's markers are deleted at load")
            self.assertIn(below, self.under)
            self.assertNotIn(top, self.under)
            self.assertEqual(self.sector[top]["floor_picnum"], self.sector[below]["ceiling_picnum"])
            one = Polygon(*outline_and_holes(self.disk, top))
            two = Polygon([(x - move[0], y - move[1]) for x, y in outline_and_holes(self.disk, below)[0]])
            self.assertLess(one.symmetric_difference(two).area, 1, (link, "whoever dives keeps his place in plan"))

    def test_the_drowned_are_beside_the_city_and_over_nothing(self):
        #: (west of everything until the sea was made wider and the streets went on behind their gates, 2026-11-25)
        from shapely import Polygon
        rings = [Polygon(outline_and_holes(self.disk, i)[0]).buffer(0) for i in range(len(self.sector))]
        for i in self.under:
            over = [k for k in range(len(rings)) if k not in self.under and rings[k].intersection(rings[i]).area > 64]
            self.assertEqual(over, [], i)

    def test_every_surface_is_climbed_out_of(self):
        for link, (top, *_rest) in self.pairs.items():
            ways = [w for w, there, blocked in self.doors(top)
                    if not blocked and there not in self.upper and self.rise(w, top, there) <= CLIMB
                    and hypot(*(b - a for a, b in zip(*wall_segment(self.disk, w)))) >= 384]
            self.assertTrue(ways, f"link {link}: nothing within {CLIMB} of the water")

    def test_no_swim_is_longer_than_a_breath(self):
        """From the farthest corner of every drowned sector to the nearest surface, by points a unit apart in the openings."""
        middles = {}
        for s in self.under:
            for w, there, _blocked in self.doors(s):
                (ax, ay), (bx, by) = wall_segment(self.disk, w)
                parts = max(1, round(hypot(bx - ax, by - ay) / PU))
                for k in range(parts):
                    t = (k + 0.5) / parts
                    middles.setdefault(s, []).append((there, (ax + t * (bx - ax), ay + t * (by - ay))))
        surfaced = {row[1] for row in self.pairs.values()}
        #: the least way from a surface to each point of each opening, and so to each sector
        best = {}
        heap = [(0.0, there, point) for s in sorted(surfaced) for there, point in middles[s]]
        while heap:
            far, s, at = heapq.heappop(heap)
            if (s, at) in best or s in surfaced:
                continue
            best[s, at] = far
            for there, point in middles[s]:
                heapq.heappush(heap, (far + dist(at, point), there, point))
        self.assertEqual({s for s, _p in best} | surfaced, self.under, "a drowned sector with no way up")
        for s in self.under - surfaced:
            for corner in outline_and_holes(self.disk, s)[0]:
                way = min(far + dist(corner, at) for (t, at), far in best.items() if t == s)
                self.assertLess(way / PU, AIR / 2, f"sector {s}, {corner}: there and back must be one breath")

    def test_the_reader_swims_to_everything_but_the_pumps_throat(self):
        walk = Walk(self.disk).run()
        missed = {s for s in self.under | self.upper if s not in walk.reached()}
        self.assertEqual(missed, {self.at(*self.U.low(39.4, 7.4), self.U.THROAT_FLOOR)})

    def test_the_sump_goes_through_to_the_junction(self):
        self.assertIn(self.below("junction"), self.swim(self.below("sump")))

    def test_the_branch_is_dived_to_and_its_secret_is_stepped_onto(self):
        bank, water = self.at(45.2, 38.2, self.U.SEWER), self.top("branch")
        x = self.extra[bank]
        self.assertEqual((x["tx_id"], x["command"], x["trigger_enter"], x["trigger_once"]), (2, 64, 1, 1))
        # a link enters no sector: the bank must be walked onto from the water
        self.assertEqual({there for _w, there, blocked in self.doors(bank) if not blocked}, {water})
        sill, = {there for _w, there, _b in self.doors(water)} - {bank}
        mouth = [(w, there, blocked) for w, there, blocked in self.doors(sill) if there != water]
        self.assertTrue(mouth and all(blocked for *_w, blocked in mouth), mouth)
        bars = [record_fields(self.disk.walls[w]) for w, *_rest in mouth]
        self.assertTrue(all(f["over_picnum"] == self.U.LATTICE and f["cstat"] & 16 for f in bars), "seen through")
        self.assertIn(self.below("branch"), self.swim(self.below("cistern")))
        held = {record_fields(s)["type"] for s in self.disk.sprites if record_fields(s)["sector"] == bank}
        self.assertIn(46, held, "the napalm launcher lies on it")

    def test_the_drowned_stand_on_their_chains(self):
        tiles = {row[2] for row in self.U.CHAINED}
        stood = [f for f in map(record_fields, self.disk.sprites)
                 if f["sector"] == self.below("branch") and f["picnum"] in tiles]
        self.assertEqual(len(stood), len(self.U.CHAINED))
        self.assertTrue(all(f["cstat"] & 8 for f in stood), "hung by the feet, turned over")

    def test_nobody_gets_into_the_sea_that_has_no_bottom(self):
        near = self.at(30.0, 60.0, self.U.SEA)
        edge = list(self.doors(near))
        self.assertTrue(any(there == self.top("slip") for _w, there, _b in edge))
        for w, there, blocked in edge:
            if self.sector[there]["floor_z"] <= self.U.SEA and not self.sector[there]["floor_stat"] & 2:
                self.assertTrue(blocked, (w, there))

    def test_the_slip_comes_up_on_the_quay(self):
        slip = self.top("slip")
        ramp = next(there for _w, there, blocked in self.doors(slip)
                    if not blocked and self.sector[there]["floor_stat"] & 2)
        self.assertLessEqual(min(self.rise(w, slip, there) for w, there, _b in self.doors(slip) if there == ramp), 2048)
        head = [there for _w, there, blocked in self.doors(ramp) if not blocked and there != slip
                and self.sector[there]["floor_z"] == self.U.GRADE]
        self.assertTrue(head)

    def test_one_beast_under_the_keel_and_something_on_the_box(self):
        here = [f["type"] for f in map(record_fields, self.disk.sprites) if f["sector"] in self.swim(self.below("slip"))]
        self.assertEqual((here.count(217), here.count(141)), (1, 1))

    def test_an_eel_that_surfaces_dies_so_none_is_out_of_the_water(self):
        for f in map(record_fields, self.disk.sprites):
            if f["type"] == 218:
                self.assertIn(f["sector"], self.under)

    def test_it_is_cheap(self):
        self.assertLess(sum(self.sector[i]["wall_count"] for i in self.under | self.upper), 250)


if __name__ == "__main__":
    unittest.main()
