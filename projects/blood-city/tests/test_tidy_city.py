"""The built city tidied: sectors alike merged, its walls under the limit."""

import unittest
from pathlib import Path

from bloodmap import tidy
from bloodmap.analysis import validate_map
from bloodmap.format import encode_map, parse_map, read_map
from bloodmap.model import record_fields
from bloodmap.sector_geom import sector_walls


def areas(disk):
    out = []
    for index in range(len(disk.sectors)):
        total = 0
        for w in sector_walls(disk, index):
            a = record_fields(disk.walls[w])
            b = record_fields(disk.walls[a["point2"]])
            total += a["x"] * b["y"] - b["x"] * a["y"]
        out.append(total)
    return out


class TidyTests(unittest.TestCase):
    def test_pieces_alike_are_one_and_the_ground_is_the_same(self):
        path = Path("projects/blood-city/level/blood-city-current.MAP")
        if not path.exists():
            self.skipTest("the city is not built here")
        disk = read_map(path)
        total = sum(areas(disk))
        sectors = len(disk.sectors)
        report = tidy.merge_alike(disk, 1000, step=8)
        self.assertGreater(report["sectors_merged"], 0)
        self.assertEqual(len(disk.sectors), sectors - report["sectors_merged"])
        self.assertEqual(sum(areas(disk)), total)
        self.assertEqual(sorted(set(report["into"].values())), list(range(len(disk.sectors))))
        self.assertFalse([d for d in validate_map(parse_map(encode_map(disk))) if d.severity == "error"])

    def test_the_city_is_tidied(self):
        path = Path("projects/blood-city/level/blood-city-current.MAP")
        if not path.exists():
            self.skipTest("the city is not built here")
        self.assertLess(len(read_map(path).walls), 16384)


if __name__ == "__main__":
    unittest.main()
