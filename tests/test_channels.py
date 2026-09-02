"""Two kinds of channel, and the order the passes run in.

A lamp under a shadow gives less light; a thing cannot open and close at once.
Those are the only two behaviours, so there are two kinds of channel and no
priority scheme between them.

The fail-firsts here are the three the model names, and each is a defect this
project has already shipped once in another form: two writers on one exclusive
channel (P13's `glaze` against `frame_map`, where pass order decided per
record), a mechanism asked to do two things at once, and four shade writers on
one sector where the last one used to win.
"""

import unittest


class TheTableHasTwoKinds(unittest.TestCase):
    def test_light_is_additive_and_the_structural_ones_are_exclusive(self):
        from bloodmap.channels import ADDITIVE, CHANNELS, EXCLUSIVE

        self.assertEqual(CHANNELS["shade"], ADDITIVE)
        for name in ("floor_z", "sector_type", "mechanism_state", "frame",
                     "holder_role"):
            self.assertEqual(CHANNELS[name], EXCLUSIVE, name)

    def test_a_channel_nobody_declared_is_refused(self):
        from bloodmap.channels import ChannelError, RegionLedger

        with self.assertRaises(ChannelError) as caught:
            RegionLedger().write("s1", "vibes", "somebody", 1)
        self.assertIn("not a channel", str(caught.exception))


class ShadeSumsRatherThanOverwrites(unittest.TestCase):
    """FAIL-FIRST: four writers on one sector, and the last used to win."""

    def test_the_four_shade_writers_sum(self):
        # The sun field, a lamp, a flicker wave and a Link-driven wave. Before
        # the channel table each of these wrote `floor_shade` directly and
        # whichever pass ran last decided the sector -- which is how P13 found
        # fifteen panes keeping one number and nine getting another.
        from bloodmap.channels import RegionLedger

        ledger = RegionLedger()
        for owner, delta in (("sun:field", 12), ("lamp:0", -6),
                             ("flicker:s24", 3), ("link:s37->s24", -4)):
            ledger.write("s24", "shade", owner, delta, intent="presentation")
        self.assertEqual(ledger.total("s24", "shade"), 5)
        self.assertEqual(len(ledger.contributors("s24", "shade")), 4)
        self.assertEqual(ledger.dropped, [],
                         "an additive channel has nothing to arbitrate")

    def test_an_additive_channel_never_drops_a_link_wave(self):
        # The reason shade is additive: P8 counted 146 Link-driven lights in
        # the campaign, and an exclusive shade with the sun as owner would
        # drop every one of them.
        from bloodmap.channels import RegionLedger

        ledger = RegionLedger()
        ledger.write("s24", "shade", "sun:field", 12, intent="function")
        ledger.write("s24", "shade", "link:s37->s24", -8,
                     intent="presentation")
        self.assertEqual(ledger.dropped_facets(), [])
        self.assertEqual(ledger.total("s24", "shade"), 4)


class AnExclusiveChannelHasOneOwner(unittest.TestCase):
    def test_two_overlays_writing_floor_z_is_refused_by_name(self):
        # FAIL-FIRST, and the message must name both writers and the channel:
        # a refusal that says "conflict" teaches nobody which two passes to
        # look at.
        from bloodmap.channels import ChannelError, RegionLedger

        ledger = RegionLedger()
        ledger.write("island:col_a", "floor_z", "height:island", 8192)
        with self.assertRaises(ChannelError) as caught:
            ledger.write("island:col_a", "floor_z", "setpiece:basin", 11264)
        message = str(caught.exception)
        self.assertIn("height:island", message)
        self.assertIn("setpiece:basin", message)
        self.assertIn("floor_z", message)

    def test_a_mechanism_asked_to_open_and_close_at_once_is_refused(self):
        from bloodmap.channels import ChannelError, RegionLedger

        ledger = RegionLedger()
        ledger.write("s37", "mechanism_state", "curtain:open", 1)
        with self.assertRaises(ChannelError) as caught:
            ledger.write("s37", "mechanism_state", "curtain:close", 0)
        self.assertIn("nothing to resolve", str(caught.exception))

    def test_a_presentation_claim_yields_and_is_listed(self):
        # Not an error, and not silent: the manifest carries it by name with
        # its reason so the review sheet can list it and an owner can promote
        # it to FUNCTION when it matters.
        from bloodmap.channels import RegionLedger

        ledger = RegionLedger()
        ledger.write("s24", "frame", "surface:facade", "world-anchored",
                     intent="function")
        ledger.write("s24", "frame", "pool:lamp_0", "local",
                     intent="presentation", detail="a lamp's own pool frame")
        self.assertEqual(ledger.owner_of("s24", "frame"), "surface:facade")
        facets = ledger.dropped_facets()
        self.assertEqual(len(facets), 1)
        self.assertIn("pool:lamp_0", facets[0])
        self.assertIn("yields", facets[0])

    def test_the_weaker_claim_yields_whichever_arrives_first(self):
        from bloodmap.channels import RegionLedger

        first = RegionLedger()
        first.write("s1", "frame", "pool", "local", intent="presentation")
        first.write("s1", "frame", "facade", "world", intent="function")
        self.assertEqual(first.owner_of("s1", "frame"), "facade")

        second = RegionLedger()
        second.write("s1", "frame", "facade", "world", intent="function")
        second.write("s1", "frame", "pool", "local", intent="presentation")
        self.assertEqual(second.owner_of("s1", "frame"), "facade")
        self.assertEqual(len(first.dropped), len(second.dropped), 1)

    def test_two_function_claims_are_an_error_not_a_yield(self):
        from bloodmap.channels import ChannelError, RegionLedger

        ledger = RegionLedger()
        ledger.write("s1", "sector_type", "curtain", 614, intent="function")
        with self.assertRaises(ChannelError):
            ledger.write("s1", "sector_type", "lift", 600, intent="function")


class TheOrderIsAssertedNotDocumented(unittest.TestCase):
    """Every ordering bug this project has had was invisible for one reason.

    The passes simply ran and the last one won: `glaze` against `frame_map`,
    the facade pass against the run carry, the sun against a mover. An order
    that raises cannot do that.
    """

    def test_the_passes_in_order_complete(self):
        from bloodmap.channels import PASSES, Compilation

        run = Compilation()
        for name in PASSES:
            run.enter(name)
        self.assertTrue(run.complete)

    def test_the_light_field_may_not_run_before_mechanisms_are_declared(self):
        # FAIL-FIRST with the reason, because this is the one that matters:
        # a field running first would cut a curtain that nothing had yet
        # marked uncuttable.
        from bloodmap.channels import Compilation, OrderError

        run = Compilation()
        run.enter("planes")
        with self.assertRaises(OrderError) as caught:
            run.enter("light")
        self.assertIn("declare", str(caught.exception))
        self.assertIn("curtain", str(caught.exception))

    def test_joins_may_not_run_before_the_field_that_makes_their_edges(self):
        from bloodmap.channels import Compilation, OrderError

        run = Compilation()
        run.enter("planes")
        run.enter("declare")
        with self.assertRaises(OrderError) as caught:
            run.enter("joins")
        self.assertIn("pieces", str(caught.exception))

    def test_a_pass_may_not_run_twice(self):
        from bloodmap.channels import Compilation, OrderError

        run = Compilation()
        run.enter("planes")
        with self.assertRaises(OrderError):
            run.enter("planes")

    def test_an_unknown_pass_is_refused(self):
        from bloodmap.channels import Compilation, OrderError

        with self.assertRaises(OrderError):
            Compilation().enter("vibes")


if __name__ == "__main__":
    unittest.main()


class LightBombIsTheSingleSummingOwner(unittest.TestCase):
    """Nothing writes `floor_shade` directly any more."""

    SLICE = "projects/blood-city/level/slice1-west-street.MAP"

    def _map(self):
        from pathlib import Path

        from bloodmap.format import read_map

        path = Path(self.SLICE)
        if not path.exists():
            raise unittest.SkipTest(f"{path} is not present")
        return read_map(path)

    def test_four_contributions_land_as_one_sum(self):
        from bloodmap.channels import RegionLedger
        from bloodmap.lightbomb import apply_shade_channel

        disk = self._map()
        before = [int(s.fields["floor_shade"]) for s in disk.sectors]
        ledger = RegionLedger()
        for owner, delta in (("sun:field", 12), ("lamp:0", -6),
                             ("flicker", 3), ("link:s1", -4)):
            ledger.write("0", "shade", owner, delta, intent="presentation")
        report = apply_shade_channel(disk, ledger)
        after = [int(s.fields["floor_shade"]) for s in disk.sectors]
        self.assertEqual(report["contributions"], 4)
        self.assertEqual(after[0], before[0] + 5, "the deltas must sum")
        self.assertEqual(before[1:], after[1:],
                         "a region nobody wrote to must not move")

    def test_a_region_with_no_contribution_is_left_alone(self):
        from bloodmap.channels import RegionLedger
        from bloodmap.lightbomb import apply_shade_channel

        disk = self._map()
        before = [int(s.fields["floor_shade"]) for s in disk.sectors]
        report = apply_shade_channel(disk, RegionLedger())
        after = [int(s.fields["floor_shade"]) for s in disk.sectors]
        self.assertEqual(report["sectors_written"], 0)
        self.assertEqual(before, after)

    def test_the_sum_is_clipped_to_builds_shade_range(self):
        # ABSOLUTE: Blood stores shade in a signed byte, so a field that
        # summed past it would wrap and a lit street would come out black.
        from bloodmap.channels import RegionLedger
        from bloodmap.lightbomb import apply_shade_channel

        disk = self._map()
        ledger = RegionLedger()
        ledger.write("0", "shade", "runaway", 4000, intent="presentation")
        apply_shade_channel(disk, ledger)
        self.assertLessEqual(int(disk.sectors[0].fields["floor_shade"]), 127)
