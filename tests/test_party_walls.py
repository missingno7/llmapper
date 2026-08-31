"""Party walls: where does one building stop? (the Phase 7 follow-up)

`reports/blood-facade-grammar.md` refused a `facade_run()` constructor because
a facade candidate is a plane, not a building. `reports/blood-party-walls.md`
measures that against the interior and mostly withdraws it.

The oracle is not a label: two openings on one frontage are in the same
building when their interiors connect without going back outside.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from bloodmap.anchors import (
    DISCRIMINATOR_FLOOR,
    PARTY_WALL_FEATURES,
    find_facades,
    interior_components,
    party_wall_gaps,
)
from tests.helpers import corpus_map
from tests.test_facade import street_scene


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "blood-party-walls.json"


def _join(build, a, b):
    """Portal two rooms through the side wall they share, if they share one."""
    walls = build.walls

    def wall_ids(sector_id):
        fields = build.sectors[sector_id]["fields"]
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        return range(first, first + count)

    for u in wall_ids(a):
        for v in wall_ids(b):
            ua, ub = walls[u]["fields"], walls[v]["fields"]
            ea = walls[int(ua["point2"])]["fields"]
            eb = walls[int(ub["point2"])]["fields"]
            if ((int(ua["x"]), int(ua["y"])) == (int(eb["x"]), int(eb["y"]))
                    and (int(ea["x"]), int(ea["y"])) == (int(ub["x"]), int(ub["y"]))
                    and int(ua["next_sector"]) < 0 and int(ub["next_sector"]) < 0):
                ua.update(next_wall=v, next_sector=b)
                ub.update(next_wall=u, next_sector=a)
                return True
    return False


def two_shops(*, courtyard=False):
    """A street with three openings: two windows of one shop, then another.

    Bays 1 and 2 are one shop; bay 5, two bays of pier further along, is a
    different one. `courtyard` opens the first shop's second room to the sky,
    which is one of the oracle's two declared failure modes.
    """
    build = street_scene(openings=(1, 2, 5))
    assert _join(build, 1, 2), "bays 1 and 2 share a wall"
    if courtyard:
        build.sectors[2]["fields"]["ceiling_stat"] = 1
    return build


def two_shops_across_a_kerb():
    """The same two shops, with a kerb seam in the pier between them.

    A seam is a two-sided wall, so a pier measured by counting walls rather
    than solid walls would count it.
    """
    build = street_scene(openings=(1, 2, 5), seam_at=(3,))
    assert _join(build, 1, 2)
    return build


def one_shop_three_windows():
    """Three windows in a row, all of one shop -- the back-room-door case.

    Two shops joined behind the scenes are reported as one building. That is
    the oracle's other failure mode, and it is indistinguishable from this.
    """
    build = street_scene(openings=(1, 2, 3))
    assert _join(build, 1, 2) and _join(build, 2, 3)
    return build


class InteriorComponentTests(unittest.TestCase):
    def test_the_street_is_not_a_building(self):
        build = street_scene()
        labels = interior_components(build)
        self.assertEqual(labels[0], -1, "the sky-lit street")
        self.assertTrue(all(labels[s] >= 0 for s in (1, 2, 3)))

    def test_two_rooms_off_one_street_are_not_thereby_one_building(self):
        """The whole point: portals through outdoor space are cut."""
        labels = interior_components(street_scene())
        self.assertEqual(len({labels[1], labels[2], labels[3]}), 3)

    def test_rooms_joined_to_each_other_are_one_building(self):
        labels = interior_components(two_shops())
        self.assertEqual(labels[1], labels[2])
        self.assertNotEqual(labels[1], labels[3])

    def test_a_sky_lit_courtyard_splits_a_building_and_that_is_stated(self):
        """The oracle's declared failure mode, pinned so it stays declared."""
        labels = interior_components(two_shops(courtyard=True))
        self.assertEqual(labels[2], -1)
        self.assertNotEqual(labels[1], labels[3])


class PartyWallGapTests(unittest.TestCase):
    def setUp(self):
        self.build = two_shops()
        self.components = interior_components(self.build)
        self.facade = max(find_facades(self.build),
                          key=lambda f: f.measures["run_length_units"])
        self.gaps = party_wall_gaps(self.build, self.facade, self.components)

    def test_each_consecutive_pair_of_openings_makes_one_gap(self):
        self.assertEqual(len(self.gaps), len(self.facade.openings) - 1)

    def test_two_windows_of_one_shop_are_one_building(self):
        self.assertEqual(self.gaps[0]["verdict"], "one_building")

    def test_the_next_shop_along_is_a_different_building(self):
        self.assertEqual(self.gaps[1]["verdict"], "different_buildings")

    def test_the_pier_between_them_is_measured_in_bays(self):
        self.assertEqual(self.gaps[0]["gap_bays"], 0.0, "adjacent bays")
        self.assertEqual(self.gaps[1]["gap_bays"], 2.0)
        self.assertEqual(self.gaps[1]["solid_walls_between"], 2)

    def test_an_opening_onto_outdoor_space_carries_no_verdict(self):
        """A gate into a courtyard has a header, so it is an opening -- but the
        oracle has nothing to say about it, and says so rather than guessing.
        """
        build = two_shops(courtyard=True)
        gaps = party_wall_gaps(
            build,
            max(find_facades(build), key=lambda f: f.measures["run_length_units"]),
            interior_components(build))
        self.assertIn("unknown", [g["verdict"] for g in gaps])

    def test_rooms_joined_behind_the_facade_are_all_one_building(self):
        """The oracle's other declared failure mode: two shops with a
        back-room door between them are reported as one, and nothing in the
        facade can tell that from three windows of a single shop.
        """
        build = one_shop_three_windows()
        gaps = party_wall_gaps(
            build,
            max(find_facades(build), key=lambda f: f.measures["run_length_units"]),
            interior_components(build))
        self.assertEqual([g["verdict"] for g in gaps],
                         ["one_building", "one_building"])

    def test_a_kerb_seam_inside_the_pier_is_not_counted_as_pier(self):
        """A seam is a two-sided wall, so a pier measured by counting walls
        rather than solid walls would count the kerb as part of the party
        wall. The pier is masonry, not ground.
        """
        build = two_shops_across_a_kerb()
        facade = max(find_facades(build),
                     key=lambda f: f.measures["run_length_units"])
        self.assertEqual(len(facade.seams), 1)
        gaps = party_wall_gaps(build, facade, interior_components(build))
        self.assertEqual(gaps[1]["verdict"], "different_buildings")
        self.assertEqual(gaps[1]["solid_walls_between"], 1)
        self.assertEqual(gaps[1]["gap_bays"], 2.0, "the gap itself is unchanged")

    def test_every_feature_the_report_measures_is_present(self):
        for gap in self.gaps:
            for feature in PARTY_WALL_FEATURES:
                self.assertIn(feature, gap)


class CorpusPartyWallTests(unittest.TestCase):
    def test_e3m2_shopfronts_are_separate_buildings(self):
        from bloodmap.format import read_map
        from bloodmap.reachability import sector_kinds

        path = corpus_map("E3M2.MAP")
        if not path.exists():
            self.skipTest("E3M2.MAP is not present in the local corpus")
        disk = read_map(path)
        build = disk.to_build_ir()
        labels = interior_components(build)
        self.assertGreater(len({v for v in labels.values() if v >= 0}), 10)
        verdicts = [g["verdict"]
                    for f in find_facades(build, disk=disk,
                                          sector_kinds=sector_kinds(disk))
                    for g in party_wall_gaps(build, f, labels)]
        self.assertIn("different_buildings", verdicts)
        self.assertIn("one_building", verdicts)


class EmittedPartyWallReportTests(unittest.TestCase):
    def setUp(self):
        if not REPORT.exists():
            self.skipTest("the party-wall report has not been generated")
        self.doc = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_a_run_is_one_buildings_frontage_far_more_often_than_not(self):
        runs = self.doc["runs"]
        one = runs["buildings_served"]["1"]
        self.assertGreater(one / runs["serving_an_interior"], 0.95)

    def test_the_exceptions_are_long_runs(self):
        bands = self.doc["runs"]["by_run_length"]
        short = bands["under 4 bays"]
        longest = bands["over 16 bays"]
        self.assertLess(short["crossing"] / short["runs"], 0.02)
        self.assertGreater(longest["crossing"] / longest["runs"], 0.1)

    def test_material_is_reported_as_no_signal_at_all(self):
        """Not a weak separator -- it fires on zero pairs of either class, and
        that follows from 98% of these facades using one tile throughout.
        """
        by_name = {s["feature"]: s
                   for s in self.doc["separations"]["separated_by_a_pier"]}
        for feature in ("gap_tile_differs_from_run", "flank_tiles_differ"):
            self.assertEqual(by_name[feature]["positive_share"], 0.0)
            self.assertEqual(by_name[feature]["comparison_share"], 0.0)
            self.assertLess(by_name[feature]["balanced_accuracy"],
                            DISCRIMINATOR_FLOOR)

    def test_the_pier_rule_is_not_credited_on_the_imbalanced_sample(self):
        """`gap_bays` scores 0.877 over every pair only because most
        one-building pairs are two halves of a single hole. On the pairs a
        pier genuinely separates it falls below the floor, and the report has
        to keep both numbers so the first cannot be quoted alone.
        """
        every = {s["feature"]: s for s in self.doc["separations"]["every_judged_pair"]}
        pier = {s["feature"]: s for s in self.doc["separations"]["separated_by_a_pier"]}
        self.assertGreater(every["gap_bays"]["balanced_accuracy"], 0.8)
        self.assertLess(pier["gap_bays"]["balanced_accuracy"], DISCRIMINATOR_FLOOR)

    def test_the_header_line_is_the_only_surviving_signal(self):
        pier = self.doc["separations"]["separated_by_a_pier"]
        above = [s for s in pier
                 if s["balanced_accuracy"] >= DISCRIMINATOR_FLOOR]
        self.assertEqual(pier[0]["feature"], "header_changes")
        self.assertLessEqual(len(above), 2)

    def test_counterexamples_are_kept(self):
        self.assertTrue(self.doc["crossing_runs"])
        for run in self.doc["crossing_runs"]:
            self.assertGreaterEqual(run["buildings_served"], 2)


if __name__ == "__main__":
    unittest.main()
