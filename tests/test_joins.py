"""How two surfaces meet, as a table rather than as four special cases.

Things are one table; joins are the other. A kerb is what road|pavement looks
like, not an object; a holder is what facade|opening requires; a termination
is what road|end wall does. Each was a branch somewhere and each is a ROW
here.

The value is the loud failure. Gravesend's kerbs wore the houses because an
undescribed join fell through to whatever the region happened to carry, and a
table that refuses an unknown pair cannot do that.
"""

import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")


class ARuleIsRequiredNotDefaulted(unittest.TestCase):
    def test_an_undescribed_pair_fails_loudly(self):
        from bloodmap.joins import JoinError, rule

        with self.assertRaises(JoinError) as caught:
            rule("road", "enclosure_backdrop", "b_above")
        self.assertIn("no rule", str(caught.exception))

    def test_the_failure_explains_what_it_is_preventing(self):
        # A gate whose message is "invalid" teaches nobody. This one names the
        # defect it exists to stop.
        from bloodmap.joins import JoinError, rule

        with self.assertRaises(JoinError) as caught:
            rule("road", "chasm", "b_below")
        self.assertIn("kerbs", str(caught.exception))

    def test_a_join_is_symmetric_and_the_sides_swap_with_it(self):
        from bloodmap.joins import PAVEMENT, ROAD, rule

        forward = rule(ROAD, PAVEMENT, "b_above")
        back = rule(PAVEMENT, ROAD, "b_below")
        self.assertEqual(forward.a_shows, back.b_shows)
        self.assertEqual(forward.b_shows, back.a_shows)
        self.assertEqual(forward.frame, back.frame)

    def test_described_names_every_pair_the_table_cannot_answer(self):
        from bloodmap.joins import described

        found = described([("road", "pavement", "b_above"),
                           ("road", "unicorn", "equal")])
        self.assertEqual(len(found), 1)
        self.assertIn("unicorn", found[0])


class TheRowsAreTheMeasuredOnes(unittest.TestCase):
    def test_the_kerb_row_is_e3m1s(self):
        from bloodmap.joins import PAVEMENT, ROAD, rule

        found = rule(ROAD, PAVEMENT, "b_above")
        self.assertIn("kerb", found.a_shows)
        self.assertEqual(found.b_shows, "nothing")
        self.assertEqual(found.frame, "independent")
        self.assertIn("11/11", found.evidence)

    def test_a_road_cut_draws_nothing_and_keeps_its_frame(self):
        # The property the whole overlay model exists to give, as a row.
        from bloodmap.joins import NOTHING, ROAD, rule

        found = rule(ROAD, ROAD, "equal")
        self.assertEqual((found.a_shows, found.b_shows), (NOTHING, NOTHING))
        self.assertEqual(found.frame, "continues")

    def test_the_shopfront_row_requires_a_holder(self):
        # P13's law as a row: a material with its own scale needs a record no
        # other surface uses, and only a sector boundary gives it one.
        from bloodmap.joins import FACADE, OPENING, rule

        found = rule(FACADE, OPENING, "one_sided")
        self.assertTrue(found.holder)
        self.assertEqual(found.frame, "continues")
        self.assertIn("E6M1", found.evidence)

    def test_an_end_wall_blocks_and_ends_the_frame(self):
        from bloodmap.joins import END_WALL, ROAD, rule

        found = rule(ROAD, END_WALL, "b_above")
        self.assertEqual(found.cstat & 1, 1, "you may not walk up a street's end")
        self.assertEqual(found.frame, "boundary")

    def test_the_sea_and_the_horizon_draw_nothing(self):
        from bloodmap.joins import HORIZON, NOTHING, SEA, SHORE, rule

        for a, b in ((SHORE, SEA), (SEA, HORIZON)):
            found = rule(a, b, "equal")
            self.assertEqual((found.a_shows, found.b_shows), (NOTHING, NOTHING))

    def test_the_unlocated_edge_kind_carries_no_row(self):
        # `enclosure_backdrop` is named so the gap is countable and has no
        # row, because no corpus precedent has been found for it. Inventing
        # one would be the guess this table exists to refuse.
        from bloodmap.joins import EDGE_KINDS, ENCLOSURE_BACKDROP, ROWS

        self.assertIn(ENCLOSURE_BACKDROP, EDGE_KINDS)
        self.assertFalse([key for key in ROWS if ENCLOSURE_BACKDROP in key])


class WaterIsAPaletteNotATile(unittest.TestCase):
    """The correction the corpus forced, and it is about reading."""

    def test_2490_is_stone_that_blood_palettises(self):
        # 34 campaign sectors wear it: 25 with palette 10 and panning, 8 with
        # palette 0 and none. Excluding the TILE would throw away eight
        # legitimate stone faces with the twenty-five wet ones.
        from bloodmap.format import read_map
        from bloodmap.joins import is_water
        from bloodmap.patterns import list_corpus_maps

        entries = list(list_corpus_maps(population="blood-campaign"))
        if not entries:
            self.skipTest("no campaign corpus")
        wet = dry = 0
        for entry in entries:
            disk = read_map(entry.path)
            for sector in disk.sectors:
                if int(sector.fields["floor_picnum"]) != 2490:
                    continue
                if is_water(sector):
                    wet += 1
                else:
                    dry += 1
        self.assertGreater(wet, 0, "no 2490 reads as water")
        self.assertGreater(dry, 0,
                           "if every 2490 read as water the tile would be a "
                           "material after all, and this test is the claim")

    def test_a_panning_sector_reads_as_water_whatever_it_wears(self):
        from bloodmap.joins import is_water

        stone = {"fields": {"floor_picnum": 400, "floor_pal": 0}}
        self.assertFalse(is_water(type("S", (), {"fields": stone["fields"],
                                                 "extra": None})()))


class TheBoundaryIsStatedPerSide(unittest.TestCase):
    def _plan(self):
        import sys

        if str(LEVEL) not in sys.path:
            sys.path.insert(0, str(LEVEL))
        try:
            import city_plan
        except ImportError as error:                   # pragma: no cover
            raise unittest.SkipTest(str(error))
        return city_plan

    def test_every_side_of_the_city_says_how_it_ends(self):
        from bloodmap.joins import EDGE_KINDS

        plan = self._plan()
        allowed = set(EDGE_KINDS) | {"building_back", "waterfront", "gate"}
        self.assertEqual(set(plan.BOUNDARY), {"north", "south", "east", "west"})
        for side, chain in plan.BOUNDARY.items():
            self.assertTrue(chain, side)
            for segment in chain:
                self.assertIn(segment["kind"], allowed, side)

    def test_the_south_side_is_the_waterfront(self):
        self.assertEqual([s["kind"] for s in self._plan().BOUNDARY["south"]],
                         ["waterfront"])

    def test_the_perimeter_lane_is_dropped_where_buildings_back_onto_it(self):
        # The one consequence the boundary has for the solve: nothing walks
        # behind a building, so no lane is built there.
        plan = self._plan()
        sides = plan.building_back_sides()
        self.assertIn("north", sides)
        self.assertIn("east", sides)
        self.assertIn("west", sides)
        self.assertNotIn("south", sides, "the quay is walkable")



class TheCompilerAppliesTheTable(unittest.TestCase):
    """Deliverable 1: the table decides every shared record, or refuses."""

    SLICE = Path("projects/blood-city/level/slice1-west-street.MAP")

    def _slice(self):
        from bloodmap.format import read_map

        if not self.SLICE.exists():
            raise unittest.SkipTest(f"{self.SLICE} is not present")
        return read_map(self.SLICE)

    def _kinds(self, disk):
        from bloodmap.joins import PAVEMENT, ROAD

        return {i: (ROAD if int(s.fields["floor_picnum"]) == 352 else PAVEMENT)
                for i, s in enumerate(disk.sectors)}

    def test_the_table_reproduces_the_slice_record_for_record(self):
        # The proof: slice 1's kerbs were painted by hand from HeightIsland.
        # Run the table over the same map and NOTHING may change -- if the
        # table disagreed with the hand-written pass, one of the two is wrong.
        from bloodmap.joins import apply

        disk = self._slice()
        keys = ("picnum", "over_picnum", "cstat", "x_repeat", "y_repeat",
                "x_panning", "y_panning")
        before = [{k: int(w.fields[k]) for k in keys} for w in disk.walls]
        report = apply(disk, self._kinds(disk))
        after = [{k: int(w.fields[k]) for k in keys} for w in disk.walls]
        self.assertGreater(report["records"], 0, "no shared records found")
        self.assertEqual(report["unknown"], [])
        changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        self.assertEqual(changed, [],
                         "the table disagrees with the hand-written pass")

    def test_it_writes_the_kerb_band_on_the_road_side_only(self):
        from bloodmap.joins import apply

        disk = self._slice()
        report = apply(disk, self._kinds(disk))
        kerbs = [row for row in report["applied"]
                 if row["shows"] != "nothing"]
        self.assertTrue(kerbs)
        for row in kerbs:
            self.assertEqual(row["a"], "road",
                             "only the road's record shows a kerb band")
            self.assertIn("kerb", row["shows"])

    def test_a_pair_with_no_row_refuses_loudly_and_names_it(self):
        # FAIL-FIRST: the same map with one sector relabelled a kind the table
        # has no row against. Before the compiler consulted the table this
        # passed silently, because the record simply kept whatever tile its
        # region carried.
        from bloodmap.joins import CHASM, JoinError, apply

        disk = self._slice()
        kinds = self._kinds(disk)
        kinds[next(iter(kinds))] = CHASM
        with self.assertRaises(JoinError) as caught:
            apply(disk, kinds)
        message = str(caught.exception)
        self.assertIn(CHASM, message)
        self.assertIn("no rule", message)

    def test_a_non_strict_run_reports_what_it_could_not_answer(self):
        # For a build that wants the whole list rather than the first refusal.
        from bloodmap.joins import CHASM, apply

        disk = self._slice()
        kinds = self._kinds(disk)
        kinds[next(iter(kinds))] = CHASM
        report = apply(disk, kinds, strict=False)
        self.assertTrue(report["unknown"])
        self.assertTrue(any(CHASM in line for line in report["unknown"]))


if __name__ == "__main__":
    unittest.main()


class TheShoreMeetsTheQuay(unittest.TestCase):
    """The row the waterfront needed, and it is not the one the brief named.

    "The shore at pavement level" would want a PAVEMENT|SHORE row at EQUAL,
    and DWE3M10 does not attest one: every landward record of its shore steps
    UP, seven of them by 35840 (a quay wall) and one by 3072 (a walkable
    step, inside Blood's 4096 autostep). So the row is B_ABOVE and the band
    is on the shore's own side.
    """

    def test_the_row_exists_and_puts_the_band_on_the_shore(self):
        from bloodmap import joins

        found = joins.rule(joins.SHORE, joins.PAVEMENT, joins.B_ABOVE)
        self.assertIn("quay class", found.a_shows)
        self.assertEqual(found.b_shows, joins.NOTHING)
        self.assertIn("DWE3M10", found.evidence)

    def test_it_reads_the_same_from_the_pavement_side(self):
        from bloodmap import joins

        found = joins.rule(joins.PAVEMENT, joins.SHORE, joins.B_BELOW)
        self.assertIn("quay class", found.b_shows)
        self.assertEqual(found.a_shows, joins.NOTHING)

    def test_the_step_is_inside_blood_s_autostep(self):
        from bloodmap import joins
        from bloodmap.player_space import player_profile

        self.assertLessEqual(joins.SHORE_STEP,
                             player_profile("blood").max_step)

    def test_the_shore_at_equal_z_is_still_a_loud_failure(self):
        # The row that was asked for and is not attested. Asking for it must
        # raise rather than fall through to whichever tile a region carried.
        from bloodmap import joins

        with self.assertRaises(joins.JoinError):
            joins.rule(joins.PAVEMENT, joins.SHORE, joins.EQUAL)


class APlazaMayStandInAStreet(unittest.TestCase):
    """`ground_plane_rings` holes: an island whose street runs through it.

    The nine blocks a lattice encloses are holes by not being covered. A
    plaza let into a street is a hole that has to be said, and both kinds
    come out of the tracer identically -- an island is an island however it
    came to be one.
    """

    STRIPS = [(0, 0, 4096, 16384), (0, 0, 16384, 4096),
              (12288, 0, 16384, 16384), (0, 12288, 16384, 16384)]

    def test_without_holes_the_lattice_has_its_one_block(self):
        from bloodmap.overlay import ground_plane_rings

        self.assertEqual([len(r) for r in ground_plane_rings(self.STRIPS)],
                         [4, 4])

    def test_a_hole_in_a_strip_becomes_a_ring_of_its_own(self):
        from bloodmap.overlay import ground_plane_rings

        rings = ground_plane_rings(self.STRIPS,
                                   holes=[(1024, 1024, 3072, 3072)])
        self.assertEqual(len(rings), 3)

    def test_the_hole_s_area_leaves_the_plane(self):
        from bloodmap.overlay import ground_plane_rings, region_area

        whole = region_area(ground_plane_rings(self.STRIPS))
        holed = region_area(ground_plane_rings(
            self.STRIPS, holes=[(1024, 1024, 3072, 3072)]))
        self.assertEqual(whole - holed, 2048 * 2048)

    def test_a_hole_that_severs_the_plane_is_refused(self):
        # Connectivity is a question about the cells, and it is still asked.
        from bloodmap.overlay import OverlayError, ground_plane_rings

        with self.assertRaises(OverlayError) as caught:
            ground_plane_rings(self.STRIPS,
                               holes=[(0, 6144, 4096, 8192),
                                      (12288, 6144, 16384, 8192)])
        self.assertIn("connected", str(caught.exception))

    def test_one_cut_in_a_ring_lattice_does_not_sever_it(self):
        # A ring road survives a single blockage: you go the other way round.
        # The end walls rely on exactly this.
        from bloodmap.overlay import ground_plane_rings

        rings = ground_plane_rings(self.STRIPS,
                                   holes=[(0, 6144, 4096, 8192)])
        self.assertGreaterEqual(len(rings), 1)
