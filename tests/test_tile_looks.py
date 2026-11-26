"""A floor whose tile runs one way is laid along its sector: E1M2's tracks are, and turned a quarter they are not."""

from __future__ import annotations

import unittest

from bloodmap.tile_looks import directional_floor_faults, tile_looks


def _e1m2():
    from bloodmap.corpus import corpus_map_path
    from bloodmap.format import read_map

    path = corpus_map_path("E1M2")
    if not path.exists():
        raise unittest.SkipTest("the corpus is not here")
    return read_map(path)


class FloorsLaidAcross(unittest.TestCase):
    def test_the_campaigns_tracks_run_along_their_beds_and_turned_they_do_not(self):
        disk = _e1m2()
        runs = {tile for tile, row in tile_looks().items() if row.get("runs")}
        self.assertIn(1129, runs)                       # the owner's rails: their tile runs along its x
        self.assertEqual(directional_floor_faults(disk), [])
        tracks = [s for s in disk.sectors if int(s.fields["floor_picnum"]) in runs]
        self.assertTrue(tracks)
        for sector in tracks:
            sector.fields["floor_stat"] = int(sector.fields["floor_stat"]) ^ 4      # swap the tile's x and y
        faults = directional_floor_faults(disk)
        self.assertTrue(faults)
        self.assertTrue(all(f["runs_along"] != f["sector_runs"] for f in faults))

    def test_a_relative_floor_says_nothing(self):
        disk = _e1m2()
        for sector in disk.sectors:
            sector.fields["floor_stat"] = (int(sector.fields["floor_stat"]) ^ 4) | 64
        self.assertEqual(directional_floor_faults(disk), [])


if __name__ == "__main__":
    unittest.main()
