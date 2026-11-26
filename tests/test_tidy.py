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

class MergeAlike(unittest.TestCase):
    """Pieces that came out alike are one sector again: the ground they cover is the same, and the map stays valid."""

    def test_e3m1s_alike_neighbours_are_joined_and_the_ground_is_kept(self):
        path = corpus.corpus_map_path("E3M1")
        if not path.exists():
            self.skipTest("the corpus is not here")
        disk = read_map(path)
        total, sectors = sum(areas(disk)), len(disk.sectors)
        report = tidy.merge_alike(disk, 0, step=8)
        self.assertGreater(report["sectors_merged"], 0)
        self.assertEqual(len(disk.sectors), sectors - report["sectors_merged"])
        self.assertEqual(sum(areas(disk)), total)
        self.assertEqual(sorted(set(report["into"].values())), list(range(len(disk.sectors))))
        self.assertFalse([d for d in validate_map(parse_map(encode_map(disk))) if d.severity == "error"])

    def test_only_sectors_from_the_first_given_are_candidates(self):
        path = corpus.corpus_map_path("E3M1")
        if not path.exists():
            self.skipTest("the corpus is not here")
        disk = read_map(path)
        self.assertEqual(tidy.merge_alike(disk, len(disk.sectors), step=8)["sectors_merged"], 0)

if __name__ == "__main__":
    unittest.main()
