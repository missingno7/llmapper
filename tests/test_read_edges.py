"""The edge chain read off E3M1, and the definition that had to be corrected.

The first version of this reader took the boundary of the outdoor NETWORK and
found no end wall on a map whose main street ends in three. An end wall is
outdoor and has clear height, so it is inside the network; the chain bounds
the GROUND, and end walls are what the ground meets. That correction is the
first test here, because it is the kind of mistake that looks like a clean
result.
"""

from __future__ import annotations

import unittest


def _e3m1():
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [item for item in list_corpus_maps(population="blood-campaign")
             if item.path.stem.upper() == "E3M1"]
    if not found:
        raise unittest.SkipTest("E3M1 is not in the corpus")
    return read_map(found[0].path).to_level_ir()


class TheChain(unittest.TestCase):
    def setUp(self):
        from bloodmap.read_edges import read_edges

        self.level = _e3m1()
        self.result = read_edges(self.level)

    def test_the_chain_bounds_the_ground_not_the_outdoor_network(self):
        """The correction. An end wall is outdoor with clear height, so a
        boundary defined as the network's outline swallows it."""
        from bloodmap.read_edges import GROUND

        self.assertEqual(self.result["ground_sectors"],
                         [1, 2, 3, 4, 5, 6, 7, 8, 9, 45, 65, 159, 175, 235])
        self.assertNotIn("end_wall", GROUND)
        self.assertGreater(self.result["counts"].get("end_wall", 0), 0)

    def test_every_boundary_record_gets_a_kind(self):
        self.assertEqual(self.result["residue_records"], [])
        self.assertEqual(len(self.result["boundary_records"]), 100)

    def test_a_zero_residue_here_is_easy_and_the_family_share_says_so(self):
        """`building_back` catches every one-sided record, so almost nothing
        can fall through. The number that measures the EDGE FAMILY is its own
        share: 16 of 100 records are a termination; 65 are the void behind a
        building and 19 are a way in."""
        counts = self.result["counts"]
        family = sum(counts.get(kind, 0) for kind in
                     ("end_wall", "chasm", "horizon", "waterfront",
                      "enclosure_backdrop", "gate"))
        #: Still 16, but split now: 12 end walls and 4 GATES, because item
        #: 28c named the two moving masses apart and a boundary record whose
        #: far side moves is a way through rather than a termination.
        self.assertEqual(family, 16)
        self.assertEqual(counts.get("end_wall"), 12)
        self.assertEqual(counts.get("gate"), 4)
        self.assertEqual(counts.get("building_back", 0)
                         + counts.get("backing", 0), 65)
        self.assertEqual(counts.get("interior_doorway", 0), 19)

    def test_e3m1_uses_three_of_the_family_and_not_the_other_two(self):
        """No chasm, no horizon, no waterfront. The family is right and this
        map exercises part of it; DWE3M1 and DWE3M10 attest the rest."""
        for absent in ("chasm", "horizon", "waterfront", "enclosure_backdrop"):
            self.assertNotIn(absent, self.result["counts"])

    def test_every_backing_mass_has_no_interior(self):
        """The claim this layer makes: a backing sector's ceiling is its
        floor. Six of them, and if one had an interior the claim would be
        wrong rather than merely unproven."""
        far = {int(self.level.walls[int(record)]["fields"]["next_sector"])
               for record, kind in self.result["kinds"].items()
               if kind == "backing"}
        self.assertEqual(sorted(far), [10, 11, 58, 59, 60, 283])
        for sector in far:
            fields = self.level.sectors[sector]["fields"]
            self.assertEqual(int(fields["floor_z"]), int(fields["ceiling_z"]))

    def test_classify_offmap_does_not_raise_any_more(self):
        """Decisions section 14 records it as raising `TypeError` on every
        map, which is why the enclosure member has no reader. It returns."""
        offmap = self.result["offmap"]
        self.assertNotIn("raised", offmap)
        self.assertEqual(offmap["reached"], 374)
        self.assertEqual(offmap["by_kind"], {"bare": 6, "logic_closet": 2})

    def test_a_segment_is_a_run_in_builds_own_order(self):
        """Not a set of records that share a label: the chain has to be
        walkable, so a segment's records follow one another by `point2`."""
        for segment in self.result["segments"]:
            records = segment["records"]
            for index in range(len(records) - 1):
                self.assertEqual(
                    int(self.level.walls[records[index]]["fields"]["point2"]),
                    records[index + 1])


if __name__ == "__main__":
    unittest.main()
