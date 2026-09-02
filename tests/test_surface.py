"""Facades with holes, inserts with holders, one owner per record.

The law is a fact about the file format: a Build wall record has ONE set of
texture fields, and `picnum` and `over_picnum` share them (`AlignWalls`,
xmapedit/src_blood/xmpmaped.cpp:3024-3050). So a pane fitted to its opening
and a facade continuing past it cannot both be right on the same record, and
the only way to give an insert a record of its own is a holder sector.

The defect these fixtures exist for is not hypothetical. blood-city shipped 24
panes on the facade line where `glass.glaze` wrote `x_repeat` 32 and
`texture_frame.frame_map` then re-derived the facade run over the same
records: fifteen kept the pane's number, nine got the facade's, and which nine
was decided by the order the two passes ran in.
"""

import unittest
from pathlib import Path


def _campaign(stem):
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [entry for entry in list_corpus_maps(population="blood-campaign")
             if entry.path.stem.upper() == stem]
    if not found:
        raise unittest.SkipTest(f"{stem} is not in the corpus")
    return read_map(found[0].path)


class TheLedgerRefusesAtTheWrite(unittest.TestCase):
    """Not a convention anybody has to remember: a second claim raises."""

    def test_two_owners_of_one_record_is_an_error(self):
        from bloodmap.surface import OwnershipError, RecordOwner

        records = RecordOwner()
        records.claim(7, "surface:facade")
        records.claim(7, "surface:facade")          # idempotent for one owner
        with self.assertRaises(OwnershipError):
            records.claim(7, "insert:pane")

    def test_an_unclaimed_record_is_writable_by_anyone(self):
        # A build that has not adopted the ledger everywhere still works, and
        # the report says how much is unclaimed rather than pretending the
        # question was asked.
        from bloodmap.surface import RecordOwner

        records = RecordOwner()
        self.assertTrue(records.may_write(3, "anyone"))
        records.claim(3, "surface")
        self.assertFalse(records.may_write(3, "insert"))
        self.assertTrue(records.may_write(3, "surface"))

    def test_standing_aside_is_recorded_rather_than_silent(self):
        from bloodmap.surface import RecordOwner

        records = RecordOwner()
        records.claim(1, "surface")
        records.concede(1, "insert")
        self.assertEqual(records.report()["records_conceded"], 1)


class AnInsertNeedsSomewhereToPutItsMaterial(unittest.TestCase):
    def test_an_insert_with_no_holder_is_a_fault(self):
        from bloodmap.surface import Insert, insert_faults

        homeless = Insert("shop:0", "opening:0", "shopfront")
        held = Insert("shop:1", "opening:1", "shopfront",
                      holder_regions=("recess:1",))
        self.assertFalse(homeless.lawful)
        self.assertTrue(held.lawful)
        found = insert_faults([homeless, held])
        self.assertEqual(len(found), 1)
        self.assertIn("no holder region", found[0])

    def test_a_surface_knows_which_opening_a_point_falls_in(self):
        from bloodmap.surface import Opening, Surface
        from bloodmap.texture_frame import WallRunFrame

        facade = Surface("building:a:street", "building:a",
                         WallRunFrame(tile=400),
                         openings=(Opening("door", (1024, 0, 2048, 0), "door"),
                                   Opening("shop", (3072, 0, 5120, 0),
                                           "shopfront")))
        self.assertEqual(facade.opening_at(1500, 0).opening_id, "door")
        self.assertEqual(facade.opening_at(4000, 0).opening_id, "shop")
        self.assertIsNone(facade.opening_at(2560, 0))

    def test_an_unknown_kind_is_refused(self):
        from bloodmap.surface import Insert, SurfaceError

        with self.assertRaises(SurfaceError):
            Insert("x", "o", "skylight")


class GlazeOnlyScalesRecordsItOwns(unittest.TestCase):
    """The binding, in the one function that had it."""

    def _pair(self):
        """Two rooms sharing a wall, so `glaze` has something to glaze."""
        walls = [
            {"fields": {"x": 0, "y": 0, "point2": 1, "next_wall": 2,
                        "next_sector": 1, "cstat": 0, "picnum": 400,
                        "over_picnum": 0, "x_repeat": 8, "y_repeat": 8,
                        "x_panning": 0, "y_panning": 0, "extra": -1}},
            {"fields": {"x": 1024, "y": 0, "point2": 0, "next_wall": -1,
                        "next_sector": -1, "cstat": 0, "picnum": 400,
                        "over_picnum": 0, "x_repeat": 8, "y_repeat": 8,
                        "x_panning": 0, "y_panning": 0, "extra": -1}},
            {"fields": {"x": 1024, "y": 0, "point2": 3, "next_wall": 0,
                        "next_sector": 0, "cstat": 0, "picnum": 400,
                        "over_picnum": 0, "x_repeat": 8, "y_repeat": 8,
                        "x_panning": 0, "y_panning": 0, "extra": -1}},
            {"fields": {"x": 0, "y": 0, "point2": 2, "next_wall": -1,
                        "next_sector": -1, "cstat": 0, "picnum": 400,
                        "over_picnum": 0, "x_repeat": 8, "y_repeat": 8,
                        "x_panning": 0, "y_panning": 0, "extra": -1}},
        ]
        level = type("L", (), {})()
        level.walls = walls
        level.sectors = []
        level.xwalls = []
        return level

    def test_with_no_ledger_it_writes_the_scale_as_it_always_did(self):
        from bloodmap.glass import GLASS_REPEATS, glaze

        level = self._pair()
        glaze(level, [(-1, -1, 2048, 1)])
        self.assertEqual(int(level.walls[0]["fields"]["x_repeat"]),
                         GLASS_REPEATS[0])

    def test_it_will_not_scale_a_record_a_surface_owns(self):
        # THE FAIL-FIRST CASE. The facade claims the record first; the pane
        # still goes on -- `over_picnum` and cstat are the insert's own fields
        # and no run reads them -- but the scale is left alone and reported.
        from bloodmap.glass import GLASS_TILE, glaze
        from bloodmap.surface import RecordOwner

        level = self._pair()
        records = RecordOwner()
        records.claim(0, "surface:facade")
        report = glaze(level, [(-1, -1, 2048, 1)], owner="insert:pane",
                       records=records)
        self.assertIn(0, report["borrowed"])
        self.assertEqual(int(level.walls[0]["fields"]["x_repeat"]), 8,
                         "the facade's scale must survive")
        self.assertEqual(int(level.walls[0]["fields"]["over_picnum"]),
                         GLASS_TILE, "the pane itself must still be there")

    def test_a_record_the_pane_claims_first_is_not_re_derived(self):
        # The other direction, which is what blood-city actually did: the
        # pane claims, and `frame_map` then leaves it alone instead of
        # overwriting nine of twenty-four by accident.
        from bloodmap.glass import GLASS_REPEATS, glaze
        from bloodmap.surface import OwnershipError, RecordOwner

        level = self._pair()
        records = RecordOwner()
        glaze(level, [(-1, -1, 2048, 1)], owner="insert:pane", records=records)
        self.assertEqual(records.owner_of(0), "insert:pane")
        self.assertFalse(records.may_write(0, "surface:facade"))
        with self.assertRaises(OwnershipError):
            records.claim(0, "surface:facade")
        self.assertEqual(int(level.walls[0]["fields"]["x_repeat"]),
                         GLASS_REPEATS[0])


class TheCampaignShareRecordsButNeverFarApart(unittest.TestCase):
    """The clause the corpus corrected.

    The brief's law was "a wall record with a masked overlay whose picnum
    continues a surface run is a violation". The campaign does exactly that
    **34 times across 14 of its 43 maps**, so it is a practice, not an error:
    a grate set into a wall whose material carries on past it, at a scale near
    enough that one record can serve both. What the campaign never does is let
    the two diverge -- 1.11x to 2.33x, with one outlier at 11.11x.
    """

    def test_the_threshold_is_the_campaigns_own_ceiling(self):
        from bloodmap.rules_blood import FRAME_DISAGREEMENT

        self.assertGreater(FRAME_DISAGREEMENT, 2.33)
        self.assertLess(FRAME_DISAGREEMENT, 11.11)

    def test_only_the_one_outlier_is_flagged(self):
        from bloodmap import rules_blood                       # noqa: F401
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps
        from bloodmap.rules import RULES
        from bloodmap.texture_align import wall_art_sizes

        if not wall_art_sizes():
            self.skipTest("no ART in reference/blood")
        entries = list(list_corpus_maps(population="blood-campaign"))
        if not entries:
            self.skipTest("no campaign corpus")
        rule = RULES["no-record-carries-two-frames"]
        flagged = {entry.path.stem.upper(): [v.location for v
                                             in rule.check(read_map(entry.path)).violations]
                   for entry in entries}
        flagged = {name: where for name, where in flagged.items() if where}
        self.assertEqual(flagged, {"E3M3": ["wall[1447]"]},
                         "the only campaign record with two frames far apart")

    def test_it_fires_on_a_pane_drawn_at_a_wildly_different_scale(self):
        from bloodmap import rules_blood                       # noqa: F401
        from bloodmap.rules import RULES
        from bloodmap.texture_align import wall_art_sizes
        from bloodmap.texture_frame import WALL_MASKED

        if not wall_art_sizes():
            self.skipTest("no ART in reference/blood")
        disk = _campaign("E1M1")
        rule = RULES["no-record-carries-two-frames"]
        before = len(rule.check(disk).violations)
        #: turn every masked insert into an 8x one, which is what a pane that
        #: kept its own repeat on a facade record looks like
        for wall in disk.walls:
            fields = wall.fields
            if int(fields.get("over_picnum", 0)) and int(fields["cstat"]) & WALL_MASKED:
                fields["x_repeat"] = min(255, int(fields["x_repeat"]) * 8)
        after = len(rule.check(disk).violations)
        self.assertGreater(after, before,
                           "an insert eight times off its run must be a "
                           "finding")


if __name__ == "__main__":
    unittest.main()
