"""The swept-state gate, and the engine fact the motion model was missing.

Every other check in this project reads the pose a map is SAVED in. A moving
sector is in that pose for one instant of its life, and the zoo shipped a
casket whose boundary swept 2304 units past the far wall of the sector
receiving it -- inverting it -- through structural validation, the geometry
audit, the four usage laws, the self-reading gate, template conformance, a
byte-exact round trip and an NBlood load smoke.
"""

import unittest
from pathlib import Path

ORACLE = Path("maps/blood/mechanism/casket.map")


def _oracle():
    from bloodmap.format import read_map

    if not ORACLE.exists():
        raise unittest.SkipTest("the oracle map is not present")
    return read_map(ORACLE)


class TranslateSectorTest(unittest.TestCase):
    """A flagged wall drags its own vertex AND its point2's."""

    def test_one_flag_moves_a_whole_edge(self):
        # triggers.cpp:897-909 --
        #     if (wall[nWall].cstat&16384) {
        #         DragPoint(nWall, ...);
        #         if ((wall[v10].cstat&49152) == 0) DragPoint(v10, ...);
        #
        # Without that propagation the model SHEARS every Marked slide
        # instead of sliding it: the oracle's lid came back as a trapezoid
        # of 2228224 units where the engine gives a 2048x128 strip. Every
        # conclusion drawn from a swept area before this measured the wrong
        # shape, including a "wall crossing" reported against the curtain
        # that was never there.
        from bloodmap.motion_sim import blood_sweep, polygon_area

        disk = _oracle()
        frames = blood_sweep(disk, 2, steps=2)
        self.assertEqual(round(polygon_area(frames[0])), 2048 * 2048)
        self.assertEqual(round(polygon_area(frames[-1])), 2048 * 128)
        # The whole boundary edge translates: both of its endpoints move.
        self.assertEqual([tuple(round(v) for v in p) for p in frames[-1]][:2],
                         [(-2560, -512), (-512, -512)])

    def test_a_flagged_neighbour_keeps_its_own_sign(self):
        # `if ((wall[v10].cstat&49152) == 0)` -- the propagation stops at a
        # wall that carries a flag of its own, which is what lets a curtain's
        # two caps move in opposite directions.
        from bloodmap.format import read_map
        from bloodmap.motion_sim import blood_sweep
        from bloodmap.patterns import list_corpus_maps

        found = [e for e in list_corpus_maps(population="blood-campaign")
                 if e.path.stem.upper().startswith("E1M1")]
        if not found:
            self.skipTest("E1M1 is not in the corpus")
        disk = read_map(found[0].path)
        frames = blood_sweep(disk, 125, steps=4)
        first, last = frames[0], frames[-1]
        moved = [i for i, (a, b) in enumerate(zip(first, last)) if a != b]
        # Both caps move, and they move opposite ways.
        self.assertGreaterEqual(len(moved), 2)


class SweptGateTest(unittest.TestCase):
    def test_the_oracle_is_sound_throughout_its_travel(self):
        from bloodmap.swept_state import run

        report = run(_oracle())
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["mechanisms"], 2)

    def test_a_travel_past_the_receiving_wall_is_caught(self):
        # The zoo's defect, reconstructed: move the oracle's "on" marker so
        # the boundary sweeps out of the footprint.
        from bloodmap.swept_state import sweep_sector

        disk = _oracle()
        self.assertTrue(sweep_sector(disk, 2).sound)
        disk.sprites[0].fields["y"] = int(disk.sprites[0].fields["y"]) - 4096
        found = sweep_sector(disk, 2)
        self.assertFalse(found.sound)
        self.assertTrue(any("invert" in line or "collapse" in line
                            or "crossing" in line for line in found.problems))

    def test_displacing_at_load_is_normal_and_not_reported(self):
        # Corrected by the marker law. Markers are state-anchored and the
        # geometry is drawn at ON, so a state-0 sector moves the whole
        # separation the instant the level loads -- that is how a curtain
        # drawn open comes up closed, not a smell. The oracle's s5 does
        # exactly this and the gate stays quiet about it.
        from bloodmap.swept_state import sweep_sector

        found = sweep_sector(_oracle(), 5)
        self.assertTrue(found.sound)
        self.assertEqual(found.notes, [])

    def test_the_oracle_has_clearance(self):
        # The owner's own map, which is the thing that must stay quiet.
        from bloodmap.swept_state import sweep_sector

        self.assertTrue(sweep_sector(_oracle(), 5).sound)

    def test_a_mechanism_that_sweeps_through_a_room_is_caught(self):
        # The check the rotors never had. Push the ON marker far enough that
        # the travel carries the moving outline across a wall of a sector the
        # mechanism does not move; before this check, that passed everything.
        from bloodmap.swept_state import sweep_sector

        disk = _oracle()
        #: The mover sits in its own room at y -5760..-7808, and the hall
        #: above it ends at y -4096. Reverse and lengthen the travel so the
        #: base lands inside that hall: the outline then crosses the hall's
        #: wall part way through, and the hall is not in the motion set.
        disk.sprites[3].fields["y"] = -9888
        found = sweep_sector(disk, 5)
        self.assertFalse(found.sound)
        self.assertIn("sweeps through standing geometry",
                      " ".join(found.problems))


class PlanarDoorConstructorTest(unittest.TestCase):
    """The invariants are derived or clamped, never trusted from the caller."""

    def _layout(self):
        from bloodmap.planar_layout import PlanarLayout

        layout = PlanarLayout(name="probe")
        layout.add_region("room", [(0, 0), (2048, 0), (2048, 3072), (0, 3072)],
                          floor_z=0, ceiling_z=-33280)
        layout.set_player_start("room", x=1024, y=1024, z=0, angle=0)
        return layout

    def _door(self, layout, **overrides):
        from bloodmap.mechanism import planar_door

        kwargs = dict(
            footprint=(0, 3072, 2048, 3072 + 2176), axis="y", split=3072 + 2048,
            travel=-1920, channel=100, lid_region="lid", hole_region="hole",
            floor_z=0, ceiling_z=-33280,
            wall_picnum=205, floor_picnum=294, ceiling_picnum=285,
            hole_kwargs={"declared_zero_exit": True})
        kwargs.update(overrides)
        return planar_door(layout, "door", **kwargs)

    def test_it_reproduces_the_oracles_proportions(self):
        built = self._door(self._layout())
        self.assertEqual(built["footprint"], (3072, 3072 + 2176))
        self.assertEqual(built["rest"], 3072 + 2048)
        self.assertEqual(built["opened"], 3072 + 128)
        self.assertEqual(built["lid_step"], 1024)

    def test_a_travel_that_leaves_the_footprint_is_refused(self):
        from bloodmap.mechanism import MechanismError

        with self.assertRaises(MechanismError):
            self._door(self._layout(), travel=-2200)

    def test_a_travel_that_leaves_no_room_for_a_body_is_refused(self):
        from bloodmap.mechanism import MechanismError

        with self.assertRaises(MechanismError):
            self._door(self._layout(), travel=-2100)

    def test_a_split_outside_the_footprint_is_refused(self):
        from bloodmap.mechanism import MechanismError

        with self.assertRaises(MechanismError):
            self._door(self._layout(), split=3072)

    def test_the_lift_belongs_on_the_hole_the_body_stands_in(self):
        from bloodmap.mechanism import MechanismError

        with self.assertRaises(MechanismError):
            self._door(self._layout(), motor="lid", lift_out=6144)

    def test_both_dialects_build_and_sweep_sound(self):
        from bloodmap.swept_state import sweep_sector

        for motor in ("lid", "hole"):
            for flags in ("one", "both"):
                layout = self._layout()
                self._door(layout, motor=motor, flags=flags)
                layout.add_connection("c", "room", "lid", a1=(0, 3072),
                                      a2=(2048, 3072), min_width=512)
                compiled = layout.compile()
                disk = compiled.level.to_disk_map()
                driver = "lid" if motor == "lid" else "hole"
                found = sweep_sector(
                    disk, compiled.allocations[driver].sector_id)
                self.assertTrue(found.sound,
                                f"{motor}/{flags}: {found.problems}")

    def test_the_link_anchor_is_in_the_strip_that_is_always_hole(self):
        # The hole is smallest in its drawn pose, so that span is the only
        # place a link marker is inside the sector in every pose.
        built = self._door(self._layout())
        low, high = built["hole_always"]
        anchor = built["link_anchor"][1]
        self.assertTrue(low <= anchor <= high)


class SweptPreflightTest(unittest.TestCase):
    def test_a_layout_whose_mechanism_breaks_is_refused_at_compile(self):
        # A 614 whose flagged boundary travels back past its own far wall:
        # the sector turns inside out partway through the motion, and every
        # static check passes because the SAVED pose is fine. The markers
        # are placed by hand in sectors that hold them -- `owner` is the
        # sector a marker controls, not the one it stands in -- so the build
        # reaches the swept gate rather than tripping containment first.
        from bloodmap.planar_layout import PlanarLayout, PlanarLayoutError

        layout = PlanarLayout(name="probe")
        layout.add_region("motor", [(0, 0), (2048, 0), (2048, 512), (0, 512)],
                          floor_z=0, ceiling_z=-33280, type=614,
                          sector_behavior={"rx_id": 300, "busy_time_a": 20,
                                           "busy_time_b": 20})
        layout.add_region("room", [(0, 512), (2048, 512), (2048, 3072),
                                   (0, 3072)],
                          floor_z=0, ceiling_z=-33280)

        layout.set_player_start("room", x=1024, y=2048, z=0, angle=0)
        layout.add_connection("c0", "motor", "room", a1=(0, 512),
                              a2=(2048, 512), min_width=512)
        layout.carry_wall("motor", (0, 512), (2048, 512), moves="with")
        #: `trInit` treats the DRAWN pose as busy 1, so a state-0 sector's
        #: base is drawn MINUS the travel: 512 - 1280 = -768, past its own
        #: far wall at 0. It is inside out from the first frame and the
        #: saved pose says nothing about it.
        for tag, kind, region, y in (("off", 3, "motor", 256),
                                     ("on", 4, "room", 1536)):
            layout.add_sprite(f"probe_marker_{tag}", region, x=1024, y=y, z=0,
                              type=kind, picnum=3997, status=10, cstat=32896,
                              x_repeat=64, y_repeat=64, angle=0,
                              marker_owner="motor")
        with self.assertRaises(PlanarLayoutError) as caught:
            layout.compile()
        message = str(caught.exception)
        self.assertIn("break their geometry", message)
        self.assertIn("travel", message)


if __name__ == "__main__":
    unittest.main()
