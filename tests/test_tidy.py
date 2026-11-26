"""Walls joined along a straight run: fewer of them, every sector the size it was, every portal whole."""

import unittest

from bloodmap import corpus, tidy
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
    def test_a_campaign_map_keeps_its_shape_and_its_portals(self):
        class AnyTile(dict):
            def get(self, _tile, _default=None):
                return (64, 64, 0, 0)

        disk = read_map(corpus.corpus_map_path("E1M1"))
        before = areas(disk)
        count = len(disk.walls)
        report = tidy.unsplit(disk, AnyTile())
        self.assertGreater(report["joined"], 0)
        self.assertEqual(len(disk.walls), count - report["joined"])
        self.assertEqual(areas(disk), before)
        again = parse_map(encode_map(disk))
        self.assertFalse([d for d in validate_map(again) if d.severity == "error"])
        for index, wall in enumerate(again.walls):
            f = record_fields(wall)
            if f["next_wall"] >= 0:
                over = record_fields(again.walls[f["next_wall"]])
                self.assertEqual(over["next_wall"], index)
                end = record_fields(again.walls[f["point2"]])
                self.assertEqual((over["x"], over["y"]), (end["x"], end["y"]))


if __name__ == "__main__":
    unittest.main()
