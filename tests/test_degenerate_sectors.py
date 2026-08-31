"""Degenerate sectors do not have to cost a whole map.

Build accepts a sector with fewer than three walls. It cannot form a polygon,
but before this the first one in a file made every spatial view of that map
raise, and three maps in the local corpus have exactly one each -- E6M7 sector
144, TEDE1M4 sector 332, TEDE1M5 sector 0, all `wall_count == 2`. Those three
were being skipped whole by the Phase 1/2/3 miners.

The sensors now isolate such sectors, report them by id, and analyse the rest.
"""

from __future__ import annotations

import unittest

from bloodmap.design import DesignUnderstandingError, design_fingerprint
from bloodmap.morphology import MorphologyError, analyze_morphology
from bloodmap.spatial import SpatialAnalysisError, analyze_spatial
from tests.helpers import corpus_map, synthetic_two_sector_map


def map_with_a_degenerate_sector():
    """The two-sector fixture, with a third sector owning two walls.

    The two extra walls are real entries the sector points at, which is what
    Build allows and what the corpus actually contains.
    """
    from bloodmap.format import WALL_FIELDS, encode_map, parse_map
    from bloodmap.model import DiskObject

    disk = synthetic_two_sector_map()
    first = len(disk.walls)
    for offset, (x, y) in enumerate(((4096, 4096), (4096, 5120))):
        fields = {name: 0 for name, _codec in WALL_FIELDS}
        fields.update(x=x, y=y, point2=first + (offset + 1) % 2, next_wall=-1,
                      next_sector=-1, picnum=1, over_picnum=-1, extra=-1)
        disk.walls.append(DiskObject(fields))
    stub = DiskObject({name: 0 for name, _codec in
                       __import__("bloodmap.format", fromlist=["SECTOR_FIELDS"]).SECTOR_FIELDS})
    stub.fields.update(wall_ptr=first, wall_count=2, ceiling_z=-8192,
                       floor_z=8192, extra=-1)
    disk.sectors.append(stub)
    disk.header.update(num_sectors=len(disk.sectors), num_walls=len(disk.walls))
    return parse_map(encode_map(disk)).to_build_ir()


class DegenerateSectorTests(unittest.TestCase):
    def setUp(self):
        self.build = map_with_a_degenerate_sector()

    def test_spatial_analysis_survives_and_names_the_sector(self):
        found = analyze_spatial(self.build)
        self.assertEqual(found["ignored_degenerate_sector_ids"], ["sector:2"])
        self.assertNotIn("sector:2", found["sector_ids"])
        self.assertTrue(found["diagnostics"])
        self.assertIn("2 wall(s)", found["diagnostics"][0])

    def test_the_rest_of_the_map_is_still_analysed(self):
        found = analyze_spatial(self.build)
        self.assertEqual(found["sector_ids"], ["sector:0", "sector:1"])
        self.assertTrue(found["views"]["geometry"]["portals"])

    def test_morphology_reports_the_sector_and_counts_only_the_valid_ones(self):
        found = analyze_morphology(self.build)
        self.assertEqual(found["ignored_degenerate_sector_ids"], [2])
        self.assertEqual(found["sectors"]["count"], 2,
                         "fractions must not be diluted by a sector with no polygon")

    def test_the_design_fingerprint_reports_it_too(self):
        found = design_fingerprint(self.build)
        self.assertEqual(found["ignored_degenerate_sector_ids"], [2])
        self.assertEqual(found["sector_ids"], [0, 1])

    def test_a_selection_of_only_degenerate_sectors_fails_closed(self):
        """Nothing is guessed when there is no geometry left to measure."""
        with self.assertRaises(SpatialAnalysisError):
            analyze_spatial(self.build, [2])
        with self.assertRaises(MorphologyError):
            analyze_morphology(self.build, {2})
        with self.assertRaises(DesignUnderstandingError):
            design_fingerprint(self.build, [2])

    def test_genuinely_broken_wall_ownership_still_raises(self):
        """The fix is for `wall_count < 3`, not for a sector pointing outside
        the wall array."""
        build = map_with_a_degenerate_sector()
        build.sectors[2]["fields"]["wall_ptr"] = 9999
        with self.assertRaises(SpatialAnalysisError):
            analyze_spatial(build)

    def test_morphology_accepts_a_sector_selection(self):
        found = analyze_morphology(self.build, {0})
        self.assertEqual(found["sectors"]["count"], 1)
        with self.assertRaises(MorphologyError):
            analyze_morphology(self.build, {99})


class CorpusDegenerateSectorTests(unittest.TestCase):
    """The three maps this unblocks. Skips cleanly without the corpus."""

    CASES = (("E6M7.MAP", 144), ("TEDE1M4.MAP", 332), ("TEDE1M5.MAP", 0))

    def test_the_maps_that_one_two_walled_sector_used_to_cost(self):
        from bloodmap.format import read_map

        checked = 0
        for name, sector_id in self.CASES:
            path = corpus_map(name)
            if not path.exists():
                continue
            with self.subTest(map=name):
                build = read_map(path).to_build_ir()
                self.assertLess(int(build.sectors[sector_id]["fields"]["wall_count"]), 3)
                found = analyze_spatial(build)
                self.assertIn(f"sector:{sector_id}",
                              found["ignored_degenerate_sector_ids"])
                self.assertGreater(len(found["sector_ids"]), 100)
                checked += 1
        if not checked:
            self.skipTest("no local Blood MAP corpus")


if __name__ == "__main__":
    unittest.main()
