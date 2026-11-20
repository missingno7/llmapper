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

    def test_the_sun_lights_the_faces_turned_to_it(self):
        disk = _yard()
        report = sunlight.apply(disk, azimuth=45.0, base=10)
        by = report["after"]["by_facing"]
        # a sun in the south-east lights walls facing south and east, darkens
        # those facing north and west
        self.assertLess(by["S"], by["N"])
        self.assertLess(by["E"], by["W"])
        self.assertGreaterEqual(report["after"]["facing_step"], 8)

    def test_interiors_are_not_touched(self):
        disk = _yard()
        disk.sectors[0].fields["ceiling_stat"] = 0
        self.assertEqual(sunlight.apply(disk)["walls"], 0)
        self.assertTrue(all(w.fields["shade"] == 10 for w in disk.walls))


if __name__ == "__main__":
    unittest.main()
