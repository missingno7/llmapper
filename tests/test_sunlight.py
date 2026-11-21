"""bloodmap.sunlight: outdoor walls shaded by which way they face one sun."""

import pathlib
import sys
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import sunlight  # noqa: E402


def _record(**fields):
    return SimpleNamespace(fields=dict(fields))


def _yard():
    """One open-sky square sector, walls wound with the inside on the right."""
    pts = [(0, 0), (4096, 0), (4096, 4096), (0, 4096)]
    walls = [_record(x=x, y=y, point2=(i + 1) % 4, next_sector=-1, shade=10)
             for i, (x, y) in enumerate(pts)]
    sector = _record(wall_ptr=0, wall_count=4, ceiling_stat=1, floor_shade=30,
                     floor_z=8192, ceiling_z=-188416)
    return SimpleNamespace(sectors=[sector], walls=walls)


class SunlightTests(unittest.TestCase):
    def test_each_wall_faces_into_its_open_sector(self):
        faces = dict(sunlight.outdoor_faces(_yard()))
        # the north wall (0,0)->(4096,0) faces south, into the yard
        self.assertEqual(sunlight._quarter(faces[0]), "S")
        self.assertEqual(sunlight._quarter(faces[3]), "E")

    def test_a_flat_yard_measures_flat(self):
        m = sunlight.measure(_yard())
        self.assertEqual(m["facing_step"], 0)
        self.assertEqual(m["ground_median"], 30)

    def test_the_light_steps_the_faces_by_which_way_they_turn(self):
        disk = _yard()
        report = sunlight.apply(disk, azimuth=270.0, tone=0, reach=False)
        by = report["after"]["by_facing"]
        # light from the north, as E3M1's corners have it: the north face is
        # the brightest, the south the darkest, east and west between
        self.assertLess(by["N"], by["E"])
        self.assertEqual(by["E"], by["W"])
        self.assertLess(by["E"], by["S"])
        self.assertEqual(report["after"]["facing_step"], 2 * sunlight.STEP)
        # and every corner shows two planes
        self.assertEqual(report["after"]["corner_equal"], 0.0)

    def test_a_face_the_light_cannot_reach_is_not_brightened(self):
        # the yard is 4096 across and its sky stands 196608 up: from a point
        # on the south wall (facing north) a ray toward a low northern sun
        # meets the north wall before it meets the sky; a steep sun clears it
        low = sunlight.sun_reach(_yard(), sunlight.outdoor_faces(_yard()),
                                 azimuth=270.0, elevation=20.0)
        high = sunlight.sun_reach(_yard(), sunlight.outdoor_faces(_yard()),
                                  azimuth=270.0, elevation=89.0)
        # wall 2 runs (4096,4096)->(0,4096): the south wall, facing north
        self.assertEqual(low[2], 0.0)
        self.assertEqual(high[2], 1.0)
        # a face turned away from the light is not traced at all
        self.assertEqual(low[0], 0.0)

    def test_a_building_keeps_its_tone_from_build_to_build(self):
        one, two = _yard(), _yard()
        sunlight.apply(one, reach=False)
        sunlight.apply(two, reach=False)
        self.assertEqual([w.fields["shade"] for w in one.walls],
                         [w.fields["shade"] for w in two.walls])

    def test_interiors_are_not_touched(self):
        disk = _yard()
        disk.sectors[0].fields["ceiling_stat"] = 0
        self.assertEqual(sunlight.apply(disk)["walls"], 0)
        self.assertTrue(all(w.fields["shade"] == 10 for w in disk.walls))


class ShadowTests(unittest.TestCase):
    def _street(self):
        from bloodmap.planar_layout import PlanarLayout

        layout = PlanarLayout(name="shadow-probe")
        # an open square with a building (a hole: nothing open there) in its middle
        layout.add_region("street", [(0, 0), (16384, 0), (16384, 16384), (0, 16384)],
                          holes=[[(6144, 6144), (6144, 10240), (10240, 10240), (10240, 6144)]],
                          floor_z=8192, ceiling_z=-188416, parallax_ceiling=True)
        # and a lane one walks in from (ground no one can reach is a roof)
        layout.add_region("lane", [(16384, 2048), (18432, 2048), (18432, 4096), (16384, 4096)],
                          floor_z=8192, ceiling_z=-188416, parallax_ceiling=True)
        layout.add_connection("street-lane", "street", "lane",
                              a1=(16384, 2048), a2=(16384, 4096), min_width=512)
        layout.set_player_start("street", x=1024, y=15000, z=8192)
        return layout

    def test_a_building_throws_its_shadow_away_from_the_sun(self):
        from shapely.geometry import Point, Polygon

        layout = self._street()
        report = sunlight.cast_shadows(layout, azimuth=45.0)
        self.assertIn("shadow:street", layout.overlays)
        spec = layout.overlays["shadow:street"]
        from shapely.ops import unary_union

        shadow = unary_union([Polygon(outer, holes) for outer, holes in spec.shapes])
        # the sun stands south-east (+x, +y), so the shadow falls north-west
        self.assertTrue(shadow.covers(Point(5000, 5000)))
        self.assertFalse(shadow.covers(Point(11000, 11000)))
        self.assertGreater(spec.floor_shade_offset, 0)
        # and the city's edge, all the world beyond it a mass, shades the
        # ground along its sunward walls
        self.assertTrue(shadow.covers(Point(15000, 8000)))

    def test_a_roof_no_one_walks_on_is_not_shadowed(self):
        layout = self._street()
        layout.add_region("roof", [(18432, 2048), (22528, 2048), (22528, 4096), (18432, 4096)],
                          floor_z=8192 - 5 * 16960, ceiling_z=-188416, parallax_ceiling=True)
        layout.add_connection("lane-roof", "lane", "roof",
                              a1=(18432, 2048), a2=(18432, 4096), min_width=512)
        report = sunlight.cast_shadows(layout, azimuth=45.0)
        self.assertIn("roof", report["skipped"])
        self.assertNotIn("shadow:roof", layout.overlays)

    def test_the_sunlit_side_is_laid_whole(self):
        layout = self._street()
        sunlight.cast_shadows(layout, azimuth=45.0, shade=12, sunlit=-14)
        sun = layout.overlays["sun:street"]
        self.assertEqual(sun.floor_shade_offset, -14)
        # declared first, so the shadow lies on top of it
        self.assertEqual(list(layout.overlays)[:2], ["sun:street", "shadow:street"])


if __name__ == "__main__":
    unittest.main()
