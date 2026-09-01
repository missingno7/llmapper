"""Functional ownership as a subgraph, and the arbiter that resolves slots.

Two halves of the same idea. A construct owns things across storage
boundaries, so what it owns has to be DECLARED and checked; and the things it
owns are finite, so when two constructs want the same one somebody has to
decide. The owner's rule for the second half is that the answer is never
refusal -- it is a decision, and it gets reported.
"""

import unittest
from pathlib import Path

ORACLE = Path("maps/blood/mechanism/casket.map")


def _oracle():
    from bloodmap.format import read_map

    if not ORACLE.exists():
        raise unittest.SkipTest("the owner's oracle map is not present")
    return read_map(ORACLE)


class MembersCrossStorageBoundaries(unittest.TestCase):
    """A construct is a subgraph over sectors, walls, vertices and sprites."""

    def _curtain(self):
        from bloodmap.construct import Construct

        return (Construct("curtain", kind="curtain", channel=100)
                .claim("sector", 3, "carrier")
                .claim("sector", 3, "payload")
                .claim("wall", 38, "button")
                .claim("wall", 39, "button")
                .claim("wall", 40, "button")
                .claim("sprite", 0, "effect")
                .claim("sector", 2, "frame"))

    def test_one_construct_holds_three_kinds_of_thing(self):
        construct = self._curtain()
        kinds = {member.kind for member in construct.members}
        self.assertEqual(kinds, {"sector", "wall", "sprite"})

    def test_a_role_that_does_not_exist_is_refused(self):
        from bloodmap.construct import Construct, OwnershipError

        with self.assertRaises(OwnershipError):
            Construct("x").claim("sector", 1, "whatever")

    def test_two_payloads_on_one_thing_is_a_conflict(self):
        # The defect neither construct can see alone: two mechanisms moving
        # one vertex tear the map between them.
        from bloodmap.construct import Construct, conflicts

        left = Construct("left").claim("vertex", (512, 512), "payload")
        right = Construct("right").claim("vertex", (512, 512), "payload")
        found = conflicts([left, right])
        self.assertEqual(len(found), 1)
        self.assertIn("payload of 2 constructs", found[0])

    def test_a_payload_that_is_also_someone_elses_frame_is_a_conflict(self):
        from bloodmap.construct import Construct, conflicts

        door = Construct("door").claim("wall", 12, "payload")
        room = Construct("room").claim("wall", 12, "frame")
        found = conflicts([door, room])
        self.assertEqual(len(found), 1)
        self.assertIn("cannot both move and hold still", found[0])

    def test_sharing_a_junction_is_not_a_conflict(self):
        # Sharing is normal. `junction` is the role that says so.
        from bloodmap.construct import Construct, conflicts

        one = Construct("one").claim("wall", 7, "junction")
        two = Construct("two").claim("wall", 7, "junction")
        self.assertEqual(conflicts([one, two]), [])


class DeclaredMotionIsCheckedAgainstTheClosure(unittest.TestCase):
    """The motion-set closure IS the functional ownership of a mover."""

    def test_the_oracle_moves_more_than_its_own_sector(self):
        # Not a defect: the curriculum's normal case. The point is that it
        # must be DECLARED.
        from bloodmap.motion import motion_set

        found = motion_set(_oracle(), 5)
        self.assertGreater(len(found["sectors"]), 1)

    def test_an_undeclared_sector_is_reported(self):
        from bloodmap.construct import Construct, check_declared_motion

        construct = Construct("lid").claim("sector", 5, "carrier")
        problems = check_declared_motion(_oracle(), construct, 5)
        self.assertTrue(problems)
        self.assertIn("never claimed", problems[0])

    def test_declaring_the_whole_closure_is_quiet(self):
        from bloodmap.construct import Construct, check_declared_motion
        from bloodmap.motion import motion_set

        disk = _oracle()
        construct = Construct("lid").claim("sector", 5, "carrier")
        for sector_id in motion_set(disk, 5)["sectors"]:
            construct.claim("sector", sector_id, "payload")
        self.assertEqual(check_declared_motion(disk, construct, 5), [])

    def test_claiming_a_sector_the_flags_do_not_move_is_reported(self):
        from bloodmap.construct import Construct, check_declared_motion
        from bloodmap.motion import motion_set

        disk = _oracle()
        construct = Construct("lid").claim("sector", 5, "carrier")
        for sector_id in motion_set(disk, 5)["sectors"]:
            construct.claim("sector", sector_id, "payload")
        construct.claim("sector", 0, "payload")     # the hall; it does not move
        problems = check_declared_motion(disk, construct, 5)
        self.assertTrue(any("the flags say otherwise" in p for p in problems))


class TheArbiterDecidesRatherThanRefuses(unittest.TestCase):
    """Four moves, three of them demonstrated by the tutorials."""

    def test_a_second_transmitter_relays(self):
        from bloodmap.arbiter import Claim, FUNCTION, PRESENTATION, arbitrate

        decisions, survivors = arbitrate([
            Claim("lift", "s30", "tx", FUNCTION),
            Claim("bell", "s30", "tx", PRESENTATION)])
        self.assertEqual(decisions[0].move, "relay")
        self.assertEqual(decisions[0].kept, "lift")
        #: nothing is dropped -- the bell survives, through the relay
        self.assertEqual(len(survivors), 2)

    def test_a_second_shade_wave_splits_a_carrier(self):
        from bloodmap.arbiter import Claim, MEDIATION, PRESENTATION, arbitrate

        decisions, survivors = arbitrate([
            Claim("door", "s20", "shade wave", MEDIATION),
            Claim("mood", "s20", "shade wave", PRESENTATION)])
        self.assertEqual(decisions[0].move, "split")
        self.assertEqual(len(survivors), 2)

    def test_only_a_state_machine_degrades(self):
        # A sector that is already a mechanism cannot mint a second state
        # machine, so presentation gives way -- and says so out loud.
        from bloodmap.arbiter import Claim, FUNCTION, PRESENTATION, arbitrate

        decisions, survivors = arbitrate([
            Claim("gate", "s40", "state", FUNCTION),
            Claim("flicker", "s40", "state", PRESENTATION)])
        self.assertEqual(decisions[0].move, "degrade")
        self.assertEqual([c.owner for c in survivors], ["gate"])

    def test_the_primary_never_blocks_on_the_secondary(self):
        # The owner's rule, as an invariant: whatever happens, every
        # function-ranked claim survives arbitration.
        from bloodmap.arbiter import (
            Claim, FUNCTION, MEDIATION, PRESENTATION, arbitrate)

        claims = [Claim("door", "s1", "state", FUNCTION),
                  Claim("lamp", "s1", "state", PRESENTATION),
                  Claim("sign", "s1", "state", MEDIATION),
                  Claim("lift", "s2", "tx", FUNCTION),
                  Claim("chime", "s2", "tx", PRESENTATION)]
        _decisions, survivors = arbitrate(claims)
        kept = {claim.owner for claim in survivors}
        for claim in claims:
            if claim.intent == FUNCTION:
                self.assertIn(claim.owner, kept)

    def test_an_uncontested_claim_is_left_alone(self):
        from bloodmap.arbiter import Claim, arbitrate

        decisions, survivors = arbitrate([Claim("door", "s1", "rx")])
        self.assertEqual(decisions, [])
        self.assertEqual(len(survivors), 1)

    def test_every_decision_is_reportable(self):
        from bloodmap.arbiter import Claim, PRESENTATION, arbitrate, report

        decisions, _survivors = arbitrate([
            Claim("a", "s1", "rx"), Claim("b", "s1", "rx", PRESENTATION)])
        payload = report(decisions)
        self.assertEqual(payload["$schema"], "llmapper.arbitration")
        self.assertTrue(payload["lines"][0].startswith("s1 rx:"))


class SlotPressureIsReadableFromAFinishedMap(unittest.TestCase):
    """What the tutorials actually spend."""

    def test_the_lifts_locked_sectors_are_full(self):
        from bloodmap.arbiter import audit_map
        from bloodmap.format import read_map

        path = Path("maps/blood/mechanism/Vanilla/MACHINERY-LIFT.map")
        if not path.exists():
            self.skipTest("tutorial absent")
        found = audit_map(read_map(path))
        self.assertTrue(found)
        self.assertIn("key", found[0])


if __name__ == "__main__":
    unittest.main()
