"""The four primitives, each on its own fixture.

Factored the way the owner's grammar is factored, and tested that way: if the
constructor and the understanding are built from the same four pieces, then
the system can read and build combinations nobody has named, which is the
whole point of having a grammar rather than a catalogue of prefabs.
"""

import unittest
from pathlib import Path

ORACLE = Path("maps/blood/mechanism/casket.map")


def _oracle():
    from bloodmap.format import read_map

    if not ORACLE.exists():
        raise unittest.SkipTest("the oracle map is not present")
    return read_map(ORACLE)


def _campaign(stem):
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps

    found = [entry for entry in list_corpus_maps(population="blood-campaign")
             if entry.path.stem.upper().startswith(stem)]
    if not found:
        raise unittest.SkipTest(f"{stem} is not in the corpus")
    return read_map(found[0].path)


# ---------------------------------------------------------------------------
# 1. MARKED-WALL MOTION
# ---------------------------------------------------------------------------

class MarkedWallMotionTest(unittest.TestCase):
    def test_a_flag_moves_a_whole_edge(self):
        # triggers.cpp:897 drags the flagged wall's point2 as well, unless
        # that wall is flagged too. So one flag is one EDGE, not one vertex.
        from bloodmap.motion import moved_points

        points = moved_points(_oracle(), 2)
        self.assertEqual(len(points), 2)
        self.assertEqual({sign for sign in points.values()}, {1})

    def test_two_opposite_flags_keep_their_own_signs(self):
        # The stop condition is what lets a curtain's caps close toward each
        # other rather than travelling together.
        from bloodmap.motion import moved_points

        points = moved_points(_campaign("E1M1"), 125)
        self.assertEqual(sorted(set(points.values())), [-1, 1])

    def test_the_motion_set_is_the_vertex_closure_not_the_flag_set(self):
        # The owner's deepest payload rule. E1M1's curtain flags two of its
        # OWN walls and the motion reaches a second sector -- the alcove --
        # because `dragpoint` walks every wall around a moved vertex.
        from bloodmap.motion import flagged_walls, motion_set

        disk = _campaign("E1M1")
        self.assertEqual(len(flagged_walls(disk, 125)), 2)
        found = motion_set(disk, 125)
        self.assertEqual(found["sectors"], [124, 125])

    def test_a_caskets_motion_reaches_the_rooms_around_it(self):
        # Measured, not assumed, and it corrects an assumption: E1M1's casket
        # is NOT isolated. Each hole's boundary shares its end vertices with
        # the rooms beside it -- s28 drags one wall each of sectors 1 and 2,
        # s30 one each of 67 and 68 -- because a floor boundary sliding
        # across a room necessarily meets that room's walls at its ends.
        #
        # So the isolation discipline is not universal. A CURTAIN needs it,
        # because the deformation runs along a face the player is looking at;
        # a floor lid can drag a wall's end vertex without anyone seeing it.
        # The gate therefore checks a construct against what it DECLARED,
        # rather than against a blanket rule.
        from bloodmap.motion import motion_set

        disk = _campaign("E1M1")
        self.assertEqual(motion_set(disk, 28)["sectors"], [1, 2, 27, 28])
        self.assertEqual(motion_set(disk, 30)["sectors"], [29, 30, 67, 68])
        # One wall each in the outsiders, both halves in the construct.
        walls = motion_set(disk, 28)["walls"]
        self.assertEqual(len(walls[1]), 1)
        self.assertEqual(len(walls[2]), 1)

    def test_an_undeclared_member_is_named_with_the_vertex(self):
        from bloodmap.motion import check_motion_set

        disk = _campaign("E1M1")
        found = check_motion_set(disk, 125, [])
        self.assertFalse(found.clean)
        self.assertEqual({item["sector"] for item in found.undeclared}, {124})
        self.assertIn("shares the moved vertex", found.undeclared[0]["why"])

    def test_the_three_payload_shapes(self):
        from bloodmap.motion import payload_shape

        disk = _campaign("E1M1")
        self.assertEqual(payload_shape(disk, 28)["shape"],
                         "boundary re-partition")
        self.assertEqual(payload_shape(disk, 125)["shape"],
                         "the sector resizes itself")
        self.assertEqual(payload_shape(disk, 65)["shape"], "nothing moves")


# ---------------------------------------------------------------------------
# 2. MOTION MARKERS
# ---------------------------------------------------------------------------

class MotionMarkerTest(unittest.TestCase):
    def test_the_pair_parameterizes_the_travel(self):
        from bloodmap.motion import marker_pair

        found = marker_pair(_oracle(), 2)
        self.assertEqual(found["travel"], (0, -1920))
        self.assertEqual(found["turn"], 0)

    def test_state_says_which_marker_the_sector_is_at(self):
        # Corrected: the two marker positions ARE the two states, so `state`
        # names one of them. It is not "where it rests on a journey".
        from bloodmap.motion import drawn_pose, marker_pair

        disk = _oracle()
        self.assertEqual(marker_pair(disk, 2)["at"], "on")
        self.assertEqual(marker_pair(disk, 5)["at"], "off")
        # And both are DRAWN at their ON pose, which is the law.
        self.assertEqual(drawn_pose(disk, 2), "on")
        self.assertEqual(drawn_pose(disk, 5), "on")

    def test_a_marker_may_stand_where_it_does_not_belong(self):
        # `owner` is the sector a marker CONTROLS. E1M1's casket puts its
        # "on" marker inside the COVER, which has no XSECTOR at all, and
        # `dbLoadMap` deletes any marker whose owner names none.
        disk = _campaign("E1M1")
        self.assertEqual(int(disk.sprites[43].fields["sector"]), 29)
        self.assertEqual(int(disk.sprites[43].fields["owner"]), 30)


# ---------------------------------------------------------------------------
# 3. CONTROL WIRING
# ---------------------------------------------------------------------------

class ControlWiringTest(unittest.TestCase):
    def test_on_to_a_thing_already_on_is_a_no_op(self):
        # The owner's state+verb rule, and the zoo casket's exact defect.
        from bloodmap.motion import CMD_OFF, CMD_ON, CMD_TOGGLE, verb_fits_state

        self.assertFalse(verb_fits_state(CMD_ON, 1))
        self.assertTrue(verb_fits_state(CMD_ON, 0))
        self.assertFalse(verb_fits_state(CMD_OFF, 0))
        self.assertTrue(verb_fits_state(CMD_TOGGLE, 1))
        self.assertTrue(verb_fits_state(CMD_TOGGLE, 0))

    def test_a_no_op_wiring_is_refused_at_construction(self):
        from bloodmap.motion import CMD_ON, WiringError, wiring

        with self.assertRaises(WiringError):
            wiring(route="remote", channel=100, command=CMD_ON,
                   receiver_state=1)

    def test_the_routes_are_orthogonal_and_parameterized(self):
        from bloodmap.motion import wiring

        self.assertEqual(wiring(route="push")["trigger_push"], 1)
        self.assertEqual(wiring(route="wall_push")["trigger_wall_push"], 1)
        self.assertEqual(wiring(route="remote", channel=42)["rx_id"], 42)
        self.assertEqual(wiring(route="level_start")["rx_id"], 7)
        self.assertEqual(wiring(route="remote", channel=1, key=6)["key"], 6)

    def test_a_whole_map_can_be_swept_for_no_ops(self):
        from bloodmap.motion import no_op_wirings

        # The campaign does not do this to itself.
        self.assertEqual(no_op_wirings(_oracle()), [])


# ---------------------------------------------------------------------------
# 4. ROR STACK
# ---------------------------------------------------------------------------

class RorStackTest(unittest.TestCase):
    def test_the_pair_is_matched_on_data_1(self):
        from bloodmap.motion import stack_pairs

        found = stack_pairs(_oracle())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["upper"], 3)
        self.assertEqual(found[0]["lower"], 6)

    def test_the_markers_sit_at_the_meeting_planes(self):
        disk = _oracle()
        upper, lower = disk.sprites[5], disk.sprites[6]
        self.assertEqual(int(upper.fields["z"]),
                         int(disk.sectors[3].fields["floor_z"]))
        self.assertEqual(int(lower.fields["z"]),
                         int(disk.sectors[6].fields["ceiling_z"]))
        for sprite in (upper, lower):
            self.assertEqual(int(sprite.fields["status"]), 0)

    def test_seeing_through_is_a_separate_property_from_the_warp(self):
        # `mirrors.cpp` IsRorSector: floor picnum 504, or floorstat & 0x180.
        # A link without it warps you through a floor that looks solid --
        # which is what the pattern zoo shipped.
        from bloodmap.motion import is_see_through, stack_pairs

        disk = _campaign("E1M1")
        for row in stack_pairs(disk):
            self.assertTrue(row["see_through"], row)
        self.assertTrue(is_see_through(disk, 28))

    def test_a_link_is_a_translation_at_a_plane(self):
        # The two halves need not overlap in plan; the marker pair carries
        # the offset applied when a body crosses.
        from bloodmap.motion import stack_pairs

        found = stack_pairs(_oracle())[0]
        self.assertNotEqual(found["offset"], (0, 0))


# ---------------------------------------------------------------------------
# the compositions add only composition facts
# ---------------------------------------------------------------------------

class CompositionTest(unittest.TestCase):
    def _layout(self):
        from bloodmap.planar_layout import PlanarLayout

        layout = PlanarLayout(name="probe")
        layout.add_region("room", [(0, 0), (4096, 0), (4096, 3072), (0, 3072)],
                          floor_z=0, ceiling_z=-33280)
        layout.set_player_start("room", x=1024, y=1024, z=0, angle=0)
        return layout

    def _curtain(self, layout, **overrides):
        from bloodmap.mechanism import curtain

        kwargs = dict(opening=(0, 3072, 2048, 4096), axis="x", channel=200,
                      leaf_region="leaf", floor_z=0, ceiling_z=-33280,
                      declared_zero_exit=True)
        kwargs.update(overrides)
        return curtain(layout, "cur", **kwargs)

    def test_a_curtain_rests_closed(self):
        # Markers are state-anchored and the geometry is drawn at ON, so a
        # state-0 curtain comes up with its fabric drawn across. The
        # tutorial's twenty-five exemplars all do this.
        layout = self._layout()
        built = self._curtain(layout)
        self.assertEqual(built["rests"], "closed")
        self.assertEqual(layout.regions["leaf"].sector_behavior["state"], 0)

    def test_a_curtain_declares_only_its_own_fabric(self):
        # The fin's moved vertices are interior to its own outline, so the
        # seam is part of the sector and nothing else can be dragged.
        layout = self._layout()
        built = self._curtain(layout)
        self.assertEqual(built["declared_motion"], ["leaf"])

    def test_a_fin_with_nothing_to_draw_over_is_refused(self):
        from bloodmap.mechanism import MechanismError

        layout = self._layout()
        with self.assertRaises(MechanismError):
            self._curtain(layout, retracted=8192)

    def test_a_fin_too_fat_for_its_doorway_is_refused(self):
        from bloodmap.mechanism import MechanismError

        layout = self._layout()
        with self.assertRaises(MechanismError):
            self._curtain(layout, fin_width=4096)

    def test_a_planar_door_rests_covered_and_toggles(self):
        from bloodmap.mechanism import planar_door

        layout = self._layout()
        built = planar_door(layout, "door",
                            footprint=(0, 3072, 2048, 3072 + 2176), axis="y",
                            split=3072 + 2048, travel=-1920, channel=100,
                            lid_region="lid", hole_region="hole",
                            floor_z=0, ceiling_z=-33280,
                            hole_kwargs={"declared_zero_exit": True})
        self.assertEqual(built["rests"], "covered")
        behavior = layout.regions["lid"].sector_behavior
        self.assertEqual(behavior["state"], 1)
        self.assertEqual(sorted(built["declared_motion"]), ["hole", "lid"])


if __name__ == "__main__":
    unittest.main()
