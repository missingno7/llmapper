"""Breakable glass, against E6M1's own shopfront.

The recipe was read off E6M1 years ago and has been glazing blood-city since;
these are the tests it never had while it lived inside a level. They check the
campaign source, the two ways a pane can be silently dead, and that the zoo's
exhibit is really glazed.
"""

import unittest
from pathlib import Path

E6M1 = Path("maps/blood/campaign/E6M1.MAP")
ZOO = Path("projects/pattern-zoo/level/pattern-zoo.MAP")


def _map(path):
    from bloodmap.format import read_map

    if not path.exists():
        raise unittest.SkipTest(f"{path} is not present")
    return read_map(path)


class TheRecipeIsE6M1s(unittest.TestCase):
    """The campaign's own glazed shopfront."""

    def test_the_campaign_glazes_two_sided_walls_with_an_overlay(self):
        from bloodmap.glass import GLASS_TILE

        disk = _map(E6M1)
        glazed = [i for i, w in enumerate(disk.walls)
                  if int(w.fields.get("over_picnum", 0)) == GLASS_TILE]
        self.assertTrue(glazed, "E6M1 has no glass at all")
        for wall_id in glazed:
            fields = disk.walls[wall_id].fields
            #: the overlay only exists on a two-sided wall -- there has to be
            #: something behind it to see
            self.assertGreaterEqual(int(fields["next_sector"]), 0, wall_id)

    def test_the_glass_cstat_carries_the_masked_bit(self):
        from bloodmap.glass import GLASS_CSTAT

        #: 0xd5 = blocking | align | masked | hitscan | translucent. The
        #: masked bit is the one that makes the overlay draw at all.
        self.assertTrue(GLASS_CSTAT & 16)
        self.assertTrue(GLASS_CSTAT & 64)
        self.assertTrue(GLASS_CSTAT & 1)

    def test_breaking_clears_blocking_hitscan_and_masked(self):
        # `trTriggerWall` clears exactly these three on both sides, which is
        # why kWallGib is the one mechanism that REOPENS a route.
        from bloodmap.glass import GLASS_CSTAT, breaks_to

        after = breaks_to(GLASS_CSTAT)
        self.assertFalse(after & 1)
        self.assertFalse(after & 16)
        self.assertFalse(after & 64)
        #: and it keeps what is not about blocking or drawing the overlay
        self.assertTrue(after & 128)


class APaneNeedsTwoSides(unittest.TestCase):
    """The HOLDER mediation: a window is a relationship, not a property."""

    def test_a_holder_names_both_rooms(self):
        from bloodmap.glass import holder

        found = holder("shop", "street", (0, 0, 64, 512))
        self.assertEqual(found["role"], "holder")
        self.assertEqual((found["inside"], found["outside"]),
                         ("shop", "street"))

    def test_one_room_cannot_hold_a_pane(self):
        from bloodmap.glass import GlassError, holder

        with self.assertRaises(GlassError):
            holder("shop", "shop", (0, 0, 64, 512))


class TheWaysAPaneDiesSilently(unittest.TestCase):
    """Both are invisible to every other reading."""

    def _zoo(self):
        return _map(ZOO)

    def test_the_zoo_pane_is_sound(self):
        from bloodmap.glass import pane_faults

        self.assertEqual(pane_faults(self._zoo()), [])

    def test_glass_without_an_xwall_is_a_permanent_pane(self):
        # NBlood needs `wall.extra > 0` before it will even look at
        # `triggerVector`. Every field is individually legal and the window
        # simply never breaks.
        from bloodmap.glass import GLASS_TILE, pane_faults

        disk = self._zoo()
        for wall in disk.walls:
            if int(wall.fields.get("over_picnum", 0)) == GLASS_TILE:
                wall.extra.fields["trigger_vector"] = 0
        faults = pane_faults(disk)
        self.assertTrue(faults)
        self.assertIn("permanent", faults[0])

    def test_glass_on_a_one_sided_wall_is_caught(self):
        from bloodmap.glass import GLASS_TILE, pane_faults

        disk = self._zoo()
        for wall in disk.walls:
            if int(wall.fields.get("over_picnum", 0)) == GLASS_TILE:
                wall.fields["next_sector"] = -1
                break
        self.assertTrue(any("ONE-SIDED" in f for f in pane_faults(disk)))


class TheZooExhibitIsReallyGlazed(unittest.TestCase):
    def test_both_sides_of_the_pair_are_glass(self):
        # `trTriggerWall` clears the bits on pWall2 as well, so a pane glazed
        # on one side only half-breaks.
        from bloodmap.glass import GLASS_TILE

        disk = _map(ZOO)
        glazed = [i for i, w in enumerate(disk.walls)
                  if int(w.fields.get("over_picnum", 0)) == GLASS_TILE]
        self.assertEqual(len(glazed), 2, "a pane is a PAIR of walls")
        first, second = (disk.walls[i].fields for i in glazed)
        self.assertEqual(int(first["next_sector"]) >= 0, True)
        self.assertEqual(int(second["next_sector"]) >= 0, True)

    def test_a_solid_wall_in_the_span_stays_a_pier(self):
        # A window needs something to see through to; `glaze` reports what it
        # refused rather than quietly doing nothing.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "_zoo_build", Path("projects/pattern-zoo/build_zoo.py"))
        if not Path("projects/pattern-zoo/build_zoo.py").exists():
            self.skipTest("zoo absent")
        #: the build prints its report; here we just assert the constructor
        #: has the behaviour, on a hand-made level
        from bloodmap.glass import glaze

        level = type("L", (), {})()
        level.walls = [
            {"fields": {"x": 0, "y": 0, "point2": 1, "next_sector": -1,
                        "cstat": 0, "x_repeat": 8, "y_repeat": 8,
                        "over_picnum": 0, "extra": 0}},
            {"fields": {"x": 100, "y": 0, "point2": 0, "next_sector": 2,
                        "cstat": 0, "x_repeat": 8, "y_repeat": 8,
                        "over_picnum": 0, "extra": 0}},
        ]
        report = glaze(level, [(-10, -10, 200, 200)])
        self.assertEqual(report["skipped_solid"], 1)
        self.assertEqual(report["panes"], 1)


if __name__ == "__main__":
    unittest.main()
