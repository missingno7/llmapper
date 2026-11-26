"""Read the Aldermack's backstage joins, clearances and door sweep from the city MAP."""

import sys
import unittest
from pathlib import Path

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from bloodmap import wiring
from bloodmap.format import read_map
from bloodmap.model import record_fields
from bloodmap.sector_geom import outline_and_holes, sector_walls, wall_segment
from bloodmap.swept_state import hosts, sweep_sector


LEVEL = Path(__file__).resolve().parents[3] / "projects" / "blood-city" / "level"
CITY = LEVEL / "blood-city-current.MAP"


@unittest.skipUnless(CITY.exists(), "the city is not built")
class AldermackBackstageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(LEVEL) not in sys.path:
            sys.path.insert(0, str(LEVEL))
        import aldermack_backstage
        import l3_theatre
        from resolution import GRADE

        cls.plan = aldermack_backstage
        cls.theatre = l3_theatre
        cls.grade = GRADE
        cls.disk = read_map(CITY)
        cls.sectors = [record_fields(s) for s in cls.disk.sectors]
        cls.sprites = [record_fields(s) for s in cls.disk.sprites]

    def test_service_route_has_two_body_widths(self):
        # The original parlor passage has 20,480 headroom. The new hallway
        # and dressing-room route have at least 24,576.
        shell = box(self.plan.WEST - 1024, 3584, 19456, 14912)
        parts = [
            Polygon(*outline_and_holes(self.disk, i)).intersection(shell)
            for i, s in enumerate(self.sectors)
            if self.grade - self.plan.PLAYER.max_step <= s["floor_z"] <= self.grade
            and s["floor_z"] - s["ceiling_z"] >= self.plan.DRESSING_CLEAR
        ]
        floor = unary_union(parts)
        route = LineString([(18400, 4352), (18400, 7680), (17920, 8240),
                            (17920, 10640), (18464, 11680), (18464, 14464)])
        self.assertTrue(floor.buffer(-self.plan.AISLE / 2).covers(route))

        y0, y1 = self.plan.PARLOR
        approach = box(self.plan.WEST - 1024, y0, self.plan.WEST, y1)
        for i, s in enumerate(self.sectors):
            if (s["floor_z"] == self.grade
                    and s["floor_z"] - s["ceiling_z"] >= self.plan.PLAYER.standing_height):
                parts.append(Polygon(*outline_and_holes(self.disk, i)).intersection(approach))
        walk = unary_union(parts).buffer(-self.plan.AISLE / 2)
        self.assertTrue(walk.covers(LineString([(16900, 7680), (18400, 7680)])))

    def test_future_stair_and_parlor_passage_keep_their_spans(self):
        def coverage(x, span, *, portal=None):
            intervals = []
            for i, w in enumerate(self.disk.walls):
                f = record_fields(w)
                (ax, ay), (bx, by) = wall_segment(self.disk, i)
                if ax == bx == x and min(ay, by) >= span[0] and max(ay, by) <= span[1]:
                    if portal is None or (f["next_sector"] >= 0) == portal:
                        intervals.append(LineString([(x, ay), (x, by)]))
            return unary_union(intervals).length

        self.assertEqual(coverage(self.plan.WEST, self.plan.PARLOR, portal=True), 1024)
        self.assertEqual(coverage(self.plan.EAST, self.plan.STAIR), 1024)
        t = self.theatre
        pair = t.FIRE_DOORS
        frame = (pair.middle[1] - pair.half, pair.middle[1] + pair.half)
        self.assertEqual(coverage(t.FIRE_EAST, frame, portal=True), 2 * pair.half)
        self.assertFalse(any(self.plan.EAST - 384 < s["x"] < self.plan.EAST
                             and self.plan.STAIR[0] < s["y"] < self.plan.STAIR[1]
                             and s["cstat"] & 1 for s in self.sprites))

    def test_fire_doors_share_their_original_empty_bay(self):
        import wing_doors
        import wires

        t = self.theatre
        channel = wires.channel(t.FIRE_WIRE)
        nodes = wiring.nodes(self.disk)
        receivers = {n["index"] for n in nodes if n["rx"] == channel and n["kind"] == "sector"}
        self.assertEqual(len(receivers), 2)
        self.assertEqual({self.sectors[i]["type"] for i in receivers}, {617})
        bay, = [host for host, movers in hosts(self.disk).items() if movers == receivers]
        outline, holes = outline_and_holes(self.disk, bay)
        expected = box(*t.FIRE_DOORS.bay())
        self.assertTrue(Polygon(outline).equals(expected))
        self.assertEqual(len(holes), 2)
        self.assertFalse(any(s["sector"] == bay for s in self.sprites))
        self.assertEqual(len([n for n in nodes if n["tx"] == channel and n["kind"] == "wall"
                              and "push" in n["causes"]]), 8)
        for leaf in receivers:
            with self.subTest(leaf=leaf):
                self.assertTrue(sweep_sector(self.disk, leaf).sound)
                self.assertEqual(Polygon(outline_and_holes(self.disk, leaf)[0]).area,
                                 t.FIRE_DOORS.hinge * wing_doors.THICKNESS)
                self.assertEqual({record_fields(self.disk.walls[w])["next_sector"]
                                  for w in sector_walls(self.disk, leaf)}, {bay})

    def test_two_dressing_places_and_the_original_pickup(self):
        sprites = [s for s in self.sprites if self.plan.WEST < s["x"] < 19456
                   and 11520 < s["y"] < 14912 and s["z"] <= self.grade]
        self.assertEqual(sorted(s["picnum"] for s in sprites if s["picnum"] in (710, 711)),
                         [710, 711])
        self.assertEqual(len([s for s in sprites if s["type"] == 109]), 1)
        bulbs = [s for s in sprites if s["picnum"] == 77]
        self.assertEqual(len(bulbs), 2)
        self.assertTrue(all(s["shade"] < -40 for s in bulbs))
