"""Owner-attested constructs, parsed out of the ORIGINAL campaign maps.

Regression armor made of owner knowledge. Each of these is a construct the
owner attested by sector id and this project then modelled; the fixture reads
the real map and asserts the model still produces the reading it was built
from. Any model change that breaks one fails the suite.

The direction is the hard rule and the reason these are separate from the
zoo's conformance sweep: **fixtures parse ORIGINAL maps.** Conformance parses
built maps against templates mined from originals. Never the reverse, and no
generated map is evidence anywhere in this file.

Where today's reading cannot yet produce a facet the blueprint names, the
test asserts what it CAN and marks the rest `expectedFailure` with the
blueprint reference. That keeps the gap visible and countable instead of
quietly absent -- and an expectedFailure that starts passing is itself a
signal, because `unittest` reports an unexpected success.
"""

import unittest
from pathlib import Path


def _campaign(stem):
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [entry for entry in list_corpus_maps(population="blood-campaign")
             if entry.path.stem.upper().startswith(stem)]
    if not found:
        raise unittest.SkipTest(f"{stem} is not in the corpus")
    return read_map(found[0].path)


def _extra(item):
    payload = getattr(item, "extra", None)
    if payload is None:
        return {}
    return payload.fields if hasattr(payload, "fields") else {}


class CasketTest(unittest.TestCase):
    """E1M1 s27-s30: the four-sector planar door.

    Owner-attested, corrected 2026-09-01: two pairs, one above the other.
    Hole sides s28 and s30 are slide-marked and ROR-linked; cover sides s27
    and s29 are plain. Each slide sector moves exactly ONE flagged wall and
    that wall is the hole/cover boundary.
    """

    @classmethod
    def setUpClass(cls):
        cls.disk = _campaign("E1M1")

    def test_both_holes_are_slide_marked(self):
        for sector_id in (28, 30):
            self.assertEqual(int(self.disk.sectors[sector_id].fields["type"]),
                             614, f"s{sector_id}")

    def test_both_covers_are_plain_sectors(self):
        for sector_id in (27, 29):
            self.assertEqual(int(self.disk.sectors[sector_id].fields["type"]),
                             0, f"s{sector_id}")

    def test_each_hole_re_partitions_its_own_boundary(self):
        from bloodmap.effects import payload

        for hole, cover in ((28, 27), (30, 29)):
            shape = payload(self.disk, hole)["shape"]
            self.assertEqual(shape["shape"], "boundary re-partition",
                             f"s{hole}")
            self.assertEqual(shape["flagged"], 1, f"s{hole}")
            self.assertEqual(shape["re_partitions_with"], cover, f"s{hole}")

    def test_both_halves_are_synced_on_one_channel(self):
        for sector_id in (28, 30):
            self.assertEqual(
                int(_extra(self.disk.sectors[sector_id])["rx_id"]), 102,
                f"s{sector_id}")

    def test_the_same_travel_runs_on_both_sides_of_the_plane(self):
        from bloodmap.conformance import measure_planar_pair

        # markers 42->43 and 44->45: -1916 and -1912. If the two halves
        # disagreed the revealed holes would not meet through the link.
        found = measure_planar_pair(self.disk, 28, 30)
        self.assertTrue(found.conforms, found.report())

    def test_the_lower_hole_carries_an_ergonomic_z_assist(self):
        # s30's floor rises 6144 as it opens. The owner's category:
        # ERGONOMIC-ASSIST motion -- present for the body, not for topology.
        # It is the z verb composed on a 614 sector, which is E1M1's own
        # proof that the z states are not a type-600 privilege.
        fields = _extra(self.disk.sectors[30])
        self.assertEqual(int(fields["off_floor_z"]), -20480)
        self.assertEqual(int(fields["on_floor_z"]), -26624)
        self.assertEqual(int(fields["off_ceiling_z"]),
                         int(fields["on_ceiling_z"]))

    def test_the_z_assist_is_not_read_as_gating(self):
        # The reading that would misread the construct: counting the floor
        # rise as part of the door's gating. `embedding` must not claim the
        # lift changes what fits through.
        from bloodmap.doors import _wall_owners
        from bloodmap.effects import read_mechanism

        reading = read_mechanism(self.disk, 30,
                                 owners=_wall_owners(self.disk))
        self.assertFalse(reading["embedding"]["carries_between_levels"])

    def test_the_cover_carries_the_mechanisms_voice(self):
        # s27 breathes light on floor, ceiling and walls while the lid moves.
        fields = _extra(self.disk.sectors[27])
        self.assertEqual(int(fields["amplitude"]), 2)
        self.assertEqual(int(fields["shade_wave"]), 7)
        self.assertTrue(int(fields["shade_always"]))


class CasketRoomOverRoomTest(unittest.TestCase):
    """The half of the casket the model still cannot read."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _campaign("E1M1")

    @unittest.expectedFailure
    def test_the_two_pairs_are_read_as_one_stack_linked_construct(self):
        # Blueprint: roadmap, "Owner-attested E1M1 mechanism reading",
        # casket. s28 and s30 are ROR-linked (link 10, sprites 47/46) and the
        # construct is FOUR sectors. Nothing in the stack composes the two
        # pairs into a single mechanism, so this asserts the shape of the
        # answer rather than pretending to have it.
        from bloodmap.effects import read_mechanism
        from bloodmap.doors import _wall_owners

        reading = read_mechanism(self.disk, 30,
                                 owners=_wall_owners(self.disk))
        self.assertEqual(reading.get("stack_partner"), 28)


class CurtainTest(unittest.TestCase):
    """E1M1 s124/s125: elastic payload, pushed fabric, and a light link."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _campaign("E1M1")

    def test_the_curtain_resizes_itself(self):
        from bloodmap.effects import payload

        shape = payload(self.disk, 125)["shape"]
        self.assertEqual(shape["shape"], "the sector resizes itself")
        # One cap carried with the travel, one against it.
        self.assertEqual(shape["advancing"], [1200])
        self.assertEqual(shape["retreating"], [1210])

    def test_the_fabric_is_the_owners_curtain_tile(self):
        fields = self.disk.sectors[125].fields
        start = int(fields["wall_ptr"])
        picnums = {int(self.disk.walls[i].fields["picnum"])
                   for i in range(start, start + int(fields["wall_count"]))}
        self.assertIn(146, picnums)

    def test_you_push_the_fabric_itself(self):
        # Four of the curtain's own walls carry XWALLs transmitting on the
        # channel the sector receives on, with trigger_push: pushing the
        # curtain tells the curtain to open.
        pushers = []
        fields = self.disk.sectors[125].fields
        start = int(fields["wall_ptr"])
        for index in range(start, start + int(fields["wall_count"])):
            wall = _extra(self.disk.walls[index])
            if wall and int(wall.get("trigger_push", 0)):
                pushers.append((index, int(wall["tx_id"])))
        self.assertEqual([tx for _i, tx in pushers], [125] * 4)
        self.assertEqual(int(_extra(self.disk.sectors[125])["rx_id"]), 125)

    def test_the_curtain_transmits_to_the_alcove_light(self):
        # s125 transmits on 126 with command 5; s124 receives on 126 and
        # answers with a shade wave of amplitude -8. The fabric moves and the
        # light behind it changes.
        curtain = _extra(self.disk.sectors[125])
        alcove = _extra(self.disk.sectors[124])
        self.assertEqual(int(curtain["tx_id"]), 126)
        self.assertEqual(int(curtain["command"]), 5)
        self.assertEqual(int(alcove["rx_id"]), 126)
        self.assertEqual(int(alcove["amplitude"]), -8)

    @unittest.expectedFailure
    def test_the_light_link_is_read_as_a_facet_of_the_mechanism(self):
        # Blueprint: roadmap, curtain s124/s125. The fields above are all
        # readable one at a time; nothing in the stack reports "this
        # mechanism drives that light" as a facet, and command 5 is unread by
        # the whole stack. Queue item: command-verb reading on the bus.
        from bloodmap.doors import _wall_owners
        from bloodmap.effects import read_mechanism

        reading = read_mechanism(self.disk, 125,
                                 owners=_wall_owners(self.disk))
        self.assertEqual(reading.get("drives"), [124])


class DoubleSlideDoorTest(unittest.TestCase):
    """E1M1 s4: one sector, two rigid leaves, worked from its own walls."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _campaign("E1M1")

    def test_it_is_one_slide_marked_sector(self):
        self.assertEqual(int(self.disk.sectors[4].fields["type"]), 614)

    def test_its_two_halves_part(self):
        # The owner's name is "rigid double slide": the leaves do not deform,
        # the SECTOR's extent does, three flagged walls each way.
        from bloodmap.effects import payload

        shape = payload(self.disk, 4)["shape"]
        self.assertEqual(shape["shape"], "the sector resizes itself")
        self.assertEqual(len(shape["advancing"]), 3)
        self.assertEqual(len(shape["retreating"]), 3)

    def test_you_push_the_leaf_and_it_tells_itself_to_open(self):
        fields = self.disk.sectors[4].fields
        start = int(fields["wall_ptr"])
        pushers = []
        for index in range(start, start + int(fields["wall_count"])):
            wall = _extra(self.disk.walls[index])
            if wall and int(wall.get("trigger_push", 0)):
                pushers.append(int(wall["tx_id"]))
        self.assertEqual(pushers, [100] * 4)
        self.assertEqual(int(_extra(self.disk.sectors[4])["rx_id"]), 100)

    @unittest.expectedFailure
    def test_the_wall_level_route_is_read_as_the_interaction(self):
        # Blueprint: roadmap promotion queue, "wall-level interaction route
        # in doors.py". `observe_motion_sector` reports 'remote_rx' -- true
        # of the SECTOR and useless to a player, who is told to find a switch
        # that does not exist. The route runs through the door's own leaf.
        from bloodmap.doors import _wall_owners, observe_motion_sector

        record = observe_motion_sector(self.disk, 4,
                                       owners=_wall_owners(self.disk))
        self.assertEqual(record["interaction"], "wall_push")


class RoomOverRoomGateTest(unittest.TestCase):
    """E1M1 s65/s90: the ROR portal, and a gate whose payload is sprites."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _campaign("E1M1")

    def test_both_halves_are_synced_on_one_channel(self):
        for sector_id in (65, 90):
            self.assertEqual(
                int(_extra(self.disk.sectors[sector_id])["rx_id"]), 101,
                f"s{sector_id}")

    def test_the_gate_moves_only_sprites(self):
        # 49 walls, none flagged, two wall sprites doing the whole job. This
        # is the reuse the visibility budget forces: one big ROR volume made
        # to carry a gate rather than a second volume being spent.
        from bloodmap.effects import payload

        found = payload(self.disk, 65)
        self.assertEqual(found["shape"]["shape"], "nothing moves")
        self.assertEqual(found["walls_with"], [])
        self.assertEqual(found["walls_against"], [])
        self.assertEqual(len(found["sprites_with"])
                         + len(found["sprites_against"]), 2)

    def test_the_leaves_face_across_their_own_travel(self):
        from bloodmap.conformance import measure_sprite_payload

        found = measure_sprite_payload(self.disk, 65)
        self.assertTrue(found.conforms, found.report())


class TurnstilePairTest(unittest.TestCase):
    """E1M4 151/314: the counter-rotating pair at the carnival entry."""

    @classmethod
    def setUpClass(cls):
        cls.disk = _campaign("E1M4")

    def test_both_rotors_conform_to_the_blade_template(self):
        from bloodmap.conformance import measure_turnstile

        for sector_id in (151, 314):
            found = measure_turnstile(self.disk, sector_id)
            self.assertTrue(found.conforms, found.report())

    def test_they_turn_opposite_ways(self):
        # The direction is in WHICH busy field carries the period, not in the
        # angle: s151 puts 255 in busy_time_a and s314 in busy_time_b.
        a = _extra(self.disk.sectors[151])
        b = _extra(self.disk.sectors[314])
        self.assertEqual(int(a["busy_time_a"]), 255)
        self.assertEqual(int(a.get("busy_time_b", 0)), 0)
        self.assertEqual(int(b["busy_time_b"]), 255)
        self.assertEqual(int(b.get("busy_time_a", 0)), 0)

    def test_both_start_with_the_level(self):
        # kChannelLevelStart is 7 and fires before the player moves, so the
        # rotors are already turning when you arrive.
        for sector_id in (151, 314):
            self.assertEqual(
                int(_extra(self.disk.sectors[sector_id])["rx_id"]), 7,
                f"s{sector_id}")


class CasketOracleTest(unittest.TestCase):
    """maps/blood/mechanism/casket.map: the owner's minimal demonstration.

    Owner-authored evidence, mechanism-tutorial population. It may be cited
    and fixtured and must never be edited, so every number here is read off
    it rather than asserted about it.

    Seven sectors demonstrating floor sliding doors uncovering a walkable
    room-over-room stack, and it teaches two dialects E1M1 does not.
    """

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        path = Path("maps/blood/mechanism/casket.map")
        if not path.exists():
            raise unittest.SkipTest("the oracle map is not present")
        cls.disk = read_map(path)

    def test_it_is_two_lid_and_hole_pairs(self):
        # Upper plane s2|s3, lower plane s5|s6. The motors are the LIDS,
        # which is the dialect E1M1 does not use: there the 614 is the hole.
        for motor, hole in ((2, 3), (5, 6)):
            self.assertEqual(int(self.disk.sectors[motor].fields["type"]), 614)
            self.assertEqual(int(self.disk.sectors[hole].fields["type"]), 0)

    def test_each_motor_re_partitions_its_own_boundary(self):
        from bloodmap.effects import payload

        for motor, hole in ((2, 3), (5, 6)):
            shape = payload(self.disk, motor)["shape"]
            self.assertEqual(shape["shape"], "boundary re-partition")
            self.assertEqual(shape["re_partitions_with"], hole)

    def test_both_records_of_the_boundary_carry_the_flag(self):
        # The second dialect: E1M1 flags one side, the oracle flags both.
        for a, b in ((18, 22), (36, 40)):
            for wall in (a, b):
                self.assertTrue(
                    int(self.disk.walls[wall].fields["cstat"]) & 16384,
                    f"wall {wall}")

    def test_the_lid_is_a_step_above_the_hole_it_covers(self):
        # 1024 on the floor above, and mirrored in the ceiling below.
        self.assertEqual(int(self.disk.sectors[3].fields["floor_z"])
                         - int(self.disk.sectors[2].fields["floor_z"]), 1024)
        self.assertEqual(int(self.disk.sectors[5].fields["ceiling_z"])
                         - int(self.disk.sectors[6].fields["ceiling_z"]), 1024)

    def test_one_channel_syncs_both_planes(self):
        for motor in (2, 5):
            self.assertEqual(int(_extra(self.disk.sectors[motor])["rx_id"]),
                             100)

    def test_the_link_markers_sit_at_the_meeting_planes(self):
        # 2332 above at exactly s3's floor, 2331 below at exactly s6's
        # ceiling, data_1-paired, statnum 0.
        upper, lower = self.disk.sprites[5], self.disk.sprites[6]
        self.assertEqual(int(upper.fields["picnum"]), 2332)
        self.assertEqual(int(lower.fields["picnum"]), 2331)
        self.assertEqual(int(upper.fields["z"]),
                         int(self.disk.sectors[3].fields["floor_z"]))
        self.assertEqual(int(lower.fields["z"]),
                         int(self.disk.sectors[6].fields["ceiling_z"]))
        for sprite in (upper, lower):
            self.assertEqual(int(sprite.fields["status"]), 0)
        self.assertEqual(int(_extra(upper)["data_1"]),
                         int(_extra(lower)["data_1"]))

    def test_reachability_pairs_the_link(self):
        from bloodmap.reachability import link_pairs

        pairs = link_pairs(self.disk)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(sorted(pairs[0]["sectors"]), [3, 6])

    def test_the_travel_fully_covers_and_the_receiver_is_sized_for_it(self):
        # The invariant the zoo build violated. Travel 1920 across a 2176
        # footprint leaves 128 on the far side at each end of the motion.
        from bloodmap.conformance import travel_of

        for motor in (2, 5):
            travel = travel_of(self.disk, motor)
            self.assertIsNotNone(travel)
            self.assertEqual(max(abs(travel[0]), abs(travel[1])), 1920)

    def test_both_planes_conform_to_the_planar_door_template(self):
        from bloodmap.conformance import measure_planar_door

        for motor in (2, 5):
            found = measure_planar_door(self.disk, motor)
            self.assertTrue(found.conforms, found.report())
            self.assertEqual(found.measured["dialect_motor"], "lid")
            self.assertEqual(found.measured["dialect_flags"], "both")
            self.assertEqual(found.measured["lid_step"], 1024)

    def test_neither_plane_breaks_its_geometry_across_the_travel(self):
        from bloodmap.swept_state import sweep_sector

        for motor in (2, 5):
            self.assertTrue(sweep_sector(self.disk, motor).sound)

    def test_the_state_mismatch_is_an_editor_leftover(self):
        # The roadmap's open question, settled by replay. Both planes are
        # DRAWN in the same physical pose -- boundary at the on-marker -- but
        # s2 saves state 1 and s5 saves state 0. `trInit` treats the drawn
        # geometry as the pose at busy 1, so a state-0 sector displaces
        # itself by the whole marker separation the moment the level loads.
        #
        # Measured: s2 rests where it was drawn; s5 jumps 1920 units. Two
        # lids on ONE channel, out of step with each other from the first
        # frame. That is not a dialect, it is a leftover.
        from bloodmap.motion_sim import blood_sweep, rest_displacement

        moved = {}
        for motor in (2, 5):
            frames = blood_sweep(self.disk, motor, steps=8)
            moved[motor] = round(rest_displacement(self.disk, motor, frames))
        self.assertEqual(moved[2], 0)
        self.assertEqual(moved[5], 1920)
        self.assertEqual(int(_extra(self.disk.sectors[2])["state"]), 1)
        self.assertEqual(int(_extra(self.disk.sectors[5]).get("state", 0)), 0)

    def test_the_switch_drives_both_planes(self):
        # One switch, pushed, toggling channel 100.
        switch = _extra(self.disk.sprites[2])
        self.assertEqual(int(switch["tx_id"]), 100)
        self.assertEqual(int(switch["command"]), 3)
        self.assertTrue(int(switch["trigger_push"]))


if __name__ == "__main__":
    unittest.main()


class TheCurtainFamilyHasFourDialects(unittest.TestCase):
    """One constructor knew one of them; the originals build four.

    Measured over the 43 campaign maps plus the DOOR-CURTAIN tutorials
    (autosave debris excluded): 39 type-614 sectors wear tile 146/147, of
    which 26 carry one flagged wall, 12 carry two, and one -- E2M1 s95 --
    carries three and is not a dialect anything builds.
    """

    def _dialect(self, path, sector_id):
        from pathlib import Path

        from bloodmap.conformance import curtain_dialect
        from bloodmap.format import read_map

        if not Path(path).exists():
            self.skipTest(f"{path} is not present")
        return curtain_dialect(read_map(path), sector_id)

    def test_one_leaf_void_is_the_tutorial(self):
        # DOOR-CURTAINS s3: three fabric walls, all one-sided, XWALL push on
        # each. The slot is a NOTCH whose interior belongs to nobody.
        found = self._dialect(
            "maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map", 3)
        self.assertEqual(found["leaves"], 1)
        self.assertEqual(found["slot"], "void")
        self.assertEqual((found["fabric_walls"], found["one_sided"]), (3, 3))
        self.assertTrue(found["push"])

    def test_two_leaves_converge_from_both_jambs(self):
        # DOOR-CURTAINSD s2: six fabric walls in two groups of three, tips
        # carrying OPPOSITE flags so the leaves approach each other.
        from bloodmap.format import read_map
        from bloodmap.motion import flagged_walls

        found = self._dialect(
            "maps/blood/mechanism/Vanilla/DOOR-CURTAINSD.map", 2)
        self.assertEqual(found["leaves"], 2)
        self.assertEqual(found["slot"], "void")
        self.assertEqual(found["one_sided"], 6)
        flags = flagged_walls(
            read_map("maps/blood/mechanism/Vanilla/DOOR-CURTAINSD.map"), 2)
        self.assertEqual(sorted(set(flags.values())), [-1, 1],
                         "two leaves that move the same way do not converge")

    def test_the_pocket_dialect_masks_its_fabric(self):
        # DOOR-CURTAINSD s4: the slot is a real sector, so the fabric wall is
        # two-sided -- and a two-sided wall's middle band is only reached
        # when it is masked. Two of its six fabric walls carry cstat 16 with
        # over_picnum 1060, and those two are the only ones you can see.
        from bloodmap.format import read_map

        found = self._dialect(
            "maps/blood/mechanism/Vanilla/DOOR-CURTAINSD.map", 4)
        self.assertEqual((found["leaves"], found["slot"]), (2, "pocket"))
        self.assertEqual(found["one_sided"], 0)
        self.assertEqual(found["masked"], 2)
        disk = read_map("maps/blood/mechanism/Vanilla/DOOR-CURTAINSD.map")
        for wall_id in (28, 32):
            fields = disk.walls[wall_id].fields
            self.assertEqual(int(fields["over_picnum"]), 1060)
            self.assertEqual(int(fields["cstat"]), 81)

    def test_e1m1_carries_a_pelmet_and_drives_a_light(self):
        # The owner-attested one: two one-sided tips, five two-sided walls on
        # a real ceiling step wearing 146 as picnum AND overpicnum -- the
        # valance above the opening -- and a command-5 Link to s124.
        from bloodmap.curriculum import _extra
        from bloodmap.format import read_map

        found = self._dialect("maps/blood/campaign/E1M1.MAP", 125)
        self.assertEqual(found["leaves"], 2)
        self.assertEqual(found["one_sided"], 4)
        self.assertEqual(found["pelmet"], 5)
        self.assertTrue(found["link"])
        disk = read_map("maps/blood/campaign/E1M1.MAP")
        extra = _extra(disk.sectors[125])
        self.assertEqual(int(extra["command"]), 5)
        self.assertEqual(int(extra["tx_id"]), 126)
        self.assertEqual(int(_extra(disk.sectors[124])["rx_id"]), 126)

    def test_every_original_passes_the_conformance(self):
        # The check that matters most about a template: it must not reject
        # the thing it was derived from. An earlier one demanded a texel
        # scale of 2.0 +/- 0.35 and rejected two of these four.
        from pathlib import Path

        from bloodmap.conformance import measure_curtain
        from bloodmap.format import read_map

        for path, sector_id in (
                ("maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map", 3),
                ("maps/blood/mechanism/Vanilla/DOOR-CURTAINSD.map", 2),
                ("maps/blood/mechanism/Vanilla/DOOR-CURTAINSD.map", 4),
                ("maps/blood/campaign/E1M1.MAP", 125)):
            if not Path(path).exists():
                continue
            found = measure_curtain(read_map(path), sector_id)
            self.assertEqual([d.relation for d in found.deviations], [],
                             f"{path} s{sector_id}")


class FabricHasToBeVisible(unittest.TestCase):
    """engine.cpp:4938-4940, which the project had no way to ask about."""

    def test_a_two_sided_unmasked_wall_shows_nothing_in_the_walkable_band(self):
        from bloodmap.conformance import fabric_is_visible
        from bloodmap.format import read_map

        disk = read_map("maps/blood/mechanism/Vanilla/DOOR-CURTAINSD.map")
        #: s4's masked pocket walls are visible; its plain two-sided ones
        #: are not, and the tutorial is content with two of six.
        self.assertTrue(fabric_is_visible(disk, 28, 4))
        self.assertTrue(fabric_is_visible(disk, 32, 4))
        self.assertFalse(fabric_is_visible(disk, 26, 4))
        self.assertFalse(fabric_is_visible(disk, 33, 4))

    def test_a_one_sided_wall_is_always_visible(self):
        from bloodmap.conformance import fabric_is_visible
        from bloodmap.format import read_map

        disk = read_map("maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map")
        for wall_id in (38, 39, 40):
            self.assertTrue(fabric_is_visible(disk, wall_id, 3))
