"""Fixtures over the mechanism tutorials, and the laws mined from them.

`maps/blood/mechanism/` is owner-supplied mechanism-tutorial population: cited
and fixtured, never edited. These are the Tier-1 maps the rework is built on,
plus the negative fixture -- STACKS3DSPACES-BADROR, which the manual points at
to show what a broken room-over-room looks like, and which a reading must
therefore REJECT rather than wave through.
"""

import unittest
from pathlib import Path

VANILLA = Path("maps/blood/mechanism/Vanilla")


def _map(name: str):
    from bloodmap.format import read_map

    path = VANILLA / name
    if not path.exists():
        raise unittest.SkipTest(f"{name} is not present")
    return read_map(path)


def _mine(name: str):
    from bloodmap.curriculum import mine_map

    path = VANILLA / name
    if not path.exists():
        raise unittest.SkipTest(f"{name} is not present")
    return mine_map(path)


class TheEngineDecidesThePose(unittest.TestCase):
    """`trInit` rebases by the whole marker delta before recording the base."""

    def test_the_off_pose_is_the_drawn_outline_minus_the_delta(self):
        # DOOR-CURTAINS s3 to the unit: the fin is saved at y -1152, the
        # markers are 896 apart, and the base lands on -2048 -- which is
        # exactly where the type-3 marker sits. The engine never reads that
        # marker's position; it arrives there by subtraction.
        from bloodmap.motion import marker_pair, off_pose

        disk = _map("DOOR-CURTAINS.map")
        pair = marker_pair(disk, 3)
        self.assertEqual(pair["travel"], (0, 896))
        moved = {point for point in off_pose(disk, 3)}
        self.assertIn((-2208, -2048), moved)
        self.assertIn((-2144, -2048), moved)
        self.assertEqual(pair["off"]["y"], -2048)

    def test_marker_absolutes_are_free_for_a_slide(self):
        # `TranslateSector` moves each base point by
        # `interpolate(m1, m2, busy) - m1`, so only the difference is read.
        # Both authoring conventions are in the corpus, and this map uses the
        # one where the pair sits at the two poses.
        from bloodmap.motion import marker_convention

        self.assertEqual(marker_convention(_map("DOOR-CURTAINS.map"), 3),
                         "at the poses")

    def test_a_parked_pair_drives_the_sector_identically(self):
        # The proof that the absolutes are free: shift BOTH markers by the
        # same offset and the swept geometry does not change at all.
        from bloodmap.motion_sim import blood_sweep

        disk = _map("DOOR-CURTAINS.map")
        before = blood_sweep(disk, 3, steps=4)
        for sprite in disk.sprites:
            if int(sprite.fields["type"]) in (3, 4) \
                    and int(sprite.fields["sector"]) == 3:
                sprite.fields["x"] = int(sprite.fields["x"]) + 4096
                sprite.fields["y"] = int(sprite.fields["y"]) - 2048
        self.assertEqual(blood_sweep(disk, 3, steps=4), before)


class TheButtonIsTheSurface(unittest.TestCase):
    """The tutorials wire a shove as an XWALL, not as a sector flag."""

    def test_the_curtain_receives_and_its_faces_transmit(self):
        # manual p.239. s3's whole XSECTOR is rx 100, two busy times and the
        # marker pair -- there is no `trigger_wall_push` on it anywhere.
        from bloodmap.curriculum import _extra

        disk = _map("DOOR-CURTAINS.map")
        sector = _extra(disk.sectors[3])
        self.assertEqual(int(sector["rx_id"]), 100)
        self.assertNotIn("trigger_wall_push", sector)
        self.assertNotIn("trigger_push", sector)
        for wall_id in (38, 39, 40):
            wall = _extra(disk.walls[wall_id])
            self.assertEqual(int(wall["tx_id"]), 100)
            self.assertEqual(int(wall["command"]), 3)
            self.assertTrue(int(wall["trigger_push"]))

    def test_our_constructor_wires_it_the_same_way(self):
        from bloodmap.curriculum import _extra
        from bloodmap.motion import sector_walls

        from tests.test_door_curtains import ConstructorMatchesTutorialTest

        layout, _built = ConstructorMatchesTutorialTest(
            "test_it_builds_the_eight_wall_fin")._built()
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        sector_id = compiled.allocations["cur"].sector_id
        sector = _extra(disk.sectors[sector_id])
        self.assertNotIn("trigger_wall_push", sector)
        buttons = [wall for wall in sector_walls(disk, sector_id)
                   if _extra(disk.walls[wall]).get("tx_id")]
        self.assertEqual(len(buttons), 3)


class ZMotionIsStateAnchoredToo(unittest.TestCase):
    """The vertical has the same shape as the horizontal."""

    def test_a_lift_is_a_floor_pair(self):
        from bloodmap.curriculum import z_pair, _extra

        disk = _map("MACHINERY-LIFT.map")
        pair = z_pair(_extra(disk.sectors[2]))
        self.assertEqual(pair["off_floor_z"], 8192)
        self.assertEqual(pair["on_floor_z"], -24576)
        # and the ceiling of that one does not travel
        self.assertEqual(pair["off_ceiling_z"], pair["on_ceiling_z"])

    def test_both_planes_may_travel_at_once(self):
        from bloodmap.curriculum import z_pair, _extra

        pair = z_pair(_extra(_map("MACHINERY-LIFT.map").sectors[6]))
        self.assertNotEqual(pair["off_floor_z"], pair["on_floor_z"])
        self.assertNotEqual(pair["off_ceiling_z"], pair["on_ceiling_z"])


class TheRelayIsASprite(unittest.TestCase):
    """kGenTrigger, the move that gets a second transmitter out of a sector."""

    def test_the_lift_relays_through_a_generator(self):
        from bloodmap.curriculum import SPRITE_ROLES, _extra

        sprite = _map("MACHINERY-LIFT.map").sprites[127]
        self.assertEqual(int(sprite.fields["type"]), 700)
        self.assertEqual(SPRITE_ROLES[700], "generator: trigger (a relay)")
        extra = _extra(sprite)
        self.assertEqual(int(extra["rx_id"]), 106)
        self.assertEqual(int(extra["tx_id"]), 115)

    def test_a_relay_is_allowed_to_carry_no_edge(self):
        # Our `transmitter` used to refuse this, which would have refused the
        # tutorial's own relay. The edge rule binds SWITCHES.
        from bloodmap.motion import transmitter

        fields = transmitter(channel=115, command=1, on=False, off=False,
                             relay=True)
        self.assertEqual(int(fields["tx_id"]), 115)
        self.assertNotIn("trigger_on", fields)

    def test_a_switch_with_no_edge_is_still_refused(self):
        from bloodmap.motion import WiringError, transmitter

        with self.assertRaises(WiringError):
            transmitter(channel=115, command=3, on=False, off=False)


class CombinationSwitchesSendOutsideTheGuards(unittest.TestCase):
    """The exception the source predicts and the corpus confirms."""

    def test_the_six_edgeless_switches_are_all_command_five(self):
        # triggers.cpp:491 -- kSwitchCombo sends
        # `if (command == kCmdLink && txID > 0)`, outside triggerOn/triggerOff.
        from bloodmap.curriculum import _extra

        disk = _map("SPRITE-OTHERSP.map")
        for sprite_id in (66, 67, 68, 69, 70, 72):
            extra = _extra(disk.sprites[sprite_id])
            self.assertEqual(int(disk.sprites[sprite_id].fields["type"]), 22)
            self.assertEqual(int(extra["command"]), 5)
            self.assertNotIn("trigger_on", extra)
            self.assertNotIn("trigger_off", extra)


class BadRorIsRejected(unittest.TestCase):
    """The negative fixture. A reading that passes it is wrong."""

    def test_the_broken_link_is_faulted(self):
        reading = _mine("STACKS3DSPACES-BADROR.map")
        self.assertEqual(len(reading.stacks), 1)
        faults = reading.stacks[0]["faults"]
        self.assertTrue(faults, "BADROR must not read as sound")
        self.assertIn("concave", " ".join(faults))

    def test_the_working_links_are_not_faulted(self):
        for name in ("STACKS3DSPACES-ROR1.map", "STACKS3DSPACES-ROR2.map"):
            reading = _mine(name)
            self.assertTrue(reading.stacks, name)
            for pair in reading.stacks:
                self.assertEqual(pair["faults"], [], f"{name} {pair}")

    def test_the_halves_of_a_working_link_are_congruent(self):
        # The rule the manual states, holding on every working link.
        from bloodmap.curriculum import _bbox

        disk = _map("STACKS3DSPACES-ROR2.map")
        reading = _mine("STACKS3DSPACES-ROR2.map")
        for pair in reading.stacks:
            upper, lower = _bbox(disk, pair["upper"]), _bbox(disk, pair["lower"])
            self.assertEqual((upper[2] - upper[0], upper[3] - upper[1]),
                             (lower[2] - lower[0], lower[3] - lower[1]))


class TheCurriculumIsMineable(unittest.TestCase):
    """The mine itself, over the whole Tier-1 set."""

    def test_every_tier_one_map_reads(self):
        from bloodmap.curriculum import TIER1

        missing = [name for name in TIER1 if not (VANILLA / name).exists()]
        self.assertEqual(missing, [], "tier-1 maps absent from the corpus")

    def test_every_law_that_measures_finds_something(self):
        from bloodmap.curriculum import mine_folder
        from bloodmap.curriculum_laws import evaluate, unsupported

        readings = mine_folder(VANILLA)
        self.assertGreater(len(readings), 90)
        self.assertEqual(unsupported(evaluate(readings)), [])

    def test_motion_crossing_a_boundary_is_the_normal_case(self):
        # The correction that matters most for the construct model: we
        # treated this as pathology, and it is the majority behaviour.
        from bloodmap.curriculum import mine_folder
        from bloodmap.curriculum_laws import _motion_crosses_storage

        readings = mine_folder(VANILLA)
        self.assertGreater(len(_motion_crosses_storage(readings)), 50)


if __name__ == "__main__":
    unittest.main()
