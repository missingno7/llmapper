"""Duke's hardcoded moving sectors, and the Blood types that match them.

Every expectation here is a transcription of EDuke32 or NBlood, not a fitted
number, so a failure means the transcription is wrong rather than that a
heuristic drifted.  The corpus cases skip themselves without the Duke maps.
"""

from __future__ import annotations

import glob
import unittest
from pathlib import Path

from bloodmap.duke import read_duke_map
from bloodmap.duke_motion import (
    DEFAULT_SECTOR_EXTRA,
    SWING_ANGLE,
    busy_time,
    nearest_walls,
    rotate_rise_bridge,
    sector_extra,
    sepldist,
    sliding_door,
    stretch_bridge,
    swinging_door,
)

ROOT = Path(__file__).resolve().parent.parent


def duke_maps() -> list[Path]:
    return [Path(p) for p in sorted(glob.glob(str(ROOT / "maps" / "duke3d" / "*.MAP")))]


HAVE_CORPUS = bool(duke_maps())
E3L11 = ROOT / "maps" / "duke3d" / "E3L11.MAP"


class DistanceTests(unittest.TestCase):
    def test_build_distance_is_not_euclidean(self):
        """SE20 chooses the walls it drags with this, so it has to be Ken's."""
        self.assertEqual(sepldist(100, 0), 100)      # exact along an axis
        self.assertEqual(sepldist(0, 100), 100)
        self.assertEqual(sepldist(3, 4), 5)          # agrees here by luck
        # ...but it is an octagonal approximation, so it does not agree in
        # general, and the disagreement is what can pick a different wall.
        self.assertNotEqual(sepldist(1000, 1000), 1414)
        self.assertLess(abs(sepldist(1000, 1000) - 1414), 60)

    def test_busy_time_converts_thirty_hertz_ticks_to_tenths_of_a_second(self):
        self.assertEqual(busy_time(30), 10)   # one second
        self.assertEqual(busy_time(64), 21)   # every ST30 bridge
        self.assertEqual(busy_time(0), 1)     # never zero


@unittest.skipUnless(E3L11.exists(), "no Duke3D corpus")
class E3L11MotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.duke = read_duke_map(E3L11)

    def test_sector_extra_defaults_and_is_overridden_by_gpspeed(self):
        """The map file never carries the motion speed on the effector."""
        slider = next(s for s in self.duke.sprites if s.picnum == 1 and s.lotag == 15)
        self.assertEqual(slider.y_velocity, 0)
        self.assertEqual(sector_extra(self.duke, slider.sector), 450)

    def test_a_sliding_door_travels_far_further_than_its_sprite_repeat(self):
        """The regression this module exists for.

        Reading the extent off the effector's texture repeat gave 128 units;
        the engine runs 16 units for (extra >> 3) ticks, which here is 896.
        """
        slider = next(s for s in self.duke.sprites if s.picnum == 1 and s.lotag == 15)
        motion = sliding_door(self.duke, slider)
        self.assertEqual(motion["ticks"], 450 >> 3)
        self.assertEqual(motion["distance"], 16 * (450 >> 3))
        self.assertEqual(motion["distance"], 896)
        self.assertNotEqual(motion["distance"], max(128, slider.x_repeat * 2))

    def test_rotate_bridges_do_not_all_turn_by_the_same_angle(self):
        """ST30's turn is 2 * sector.extra, so a GPSPEED changes the geometry.

        E3L11 carries both cases, which is why a hardcoded 256 was wrong on one
        of the five bridges and right on the other four by accident.
        """
        pivots = {s.hitag: s for s in self.duke.sprites if s.picnum == 1 and s.lotag == 1}
        angles = {}
        for sprite in self.duke.sprites:
            if sprite.picnum != 1 or sprite.lotag != 0:
                continue
            if (self.duke.sectors[sprite.sector].lotag & 0x3FFF) != 30:
                continue
            motion = rotate_rise_bridge(self.duke, sprite, pivots[sprite.hitag])
            angles[sprite.sector] = motion["angle"]
            self.assertEqual(motion["ticks"], 64)
            self.assertEqual(abs(motion["angle"]), 2 * motion["sector_extra"])
        self.assertEqual(angles[162], -512)                       # a quarter turn
        self.assertEqual({angles[s] for s in (220, 221, 222, 223)}, {-256})

    def test_a_bridge_whose_effector_sits_on_the_floor_does_not_rise(self):
        """The Z half is real, but E3L11 authors zero displacement for it."""
        pivots = {s.hitag: s for s in self.duke.sprites if s.picnum == 1 and s.lotag == 1}
        for sprite in self.duke.sprites:
            if sprite.picnum != 1 or sprite.lotag != 0:
                continue
            if (self.duke.sectors[sprite.sector].lotag & 0x3FFF) != 30:
                continue
            motion = rotate_rise_bridge(self.duke, sprite, pivots[sprite.hitag])
            self.assertEqual(motion["floor_z"], self.duke.sectors[sprite.sector].floor_z)


@unittest.skipUnless(HAVE_CORPUS, "no Duke3D corpus")
class CorpusMotionTests(unittest.TestCase):
    """What the 52 classic boards actually author for these effectors."""

    @classmethod
    def setUpClass(cls):
        seen: dict[str, object] = {}
        for path in duke_maps():
            name = path.stem.upper()
            if name in seen:
                continue
            try:
                seen[name] = read_duke_map(path)
            except ValueError:
                continue
        cls.maps = seen

    def _effectors(self, lotag):
        for name, duke in self.maps.items():
            for sprite in duke.sprites:
                if sprite.picnum == 1 and sprite.lotag == lotag:
                    yield name, duke, sprite

    def test_no_moving_effector_carries_its_speed_on_the_sprite(self):
        """Which is why SP(i) has to be read as sector.extra instead."""
        for lotag in (0, 11, 15, 20):
            for name, _duke, sprite in self._effectors(lotag):
                with self.subTest(map=name, lotag=lotag):
                    self.assertEqual(sprite.y_velocity, 0)

    def test_a_swinging_door_is_always_a_quarter_turn(self):
        """Unlike ST30, actors.cpp bounds the swing with a constant."""
        seen = 0
        for name, duke, sprite in self._effectors(11):
            motion = swinging_door(duke, sprite)
            with self.subTest(map=name):
                self.assertEqual(abs(motion["angle"]), SWING_ANGLE)
            seen += 1
        self.assertGreater(seen, 100)

    def test_swing_direction_follows_the_effector_angle(self):
        """Spawn sets T4 = (ang > 1024) ? +2 : -2 -- above 1024 turns positive."""
        for name, duke, sprite in self._effectors(11):
            with self.subTest(map=name, ang=sprite.angle):
                expected = 1 if sprite.angle > 1024 else -1
                self.assertEqual(swinging_door(duke, sprite)["direction"], expected)

    def test_slide_extents_vary_with_gpspeed_rather_than_being_constant(self):
        extents = {sliding_door(d, s)["distance"] for _n, d, s in self._effectors(15)}
        self.assertGreater(len(extents), 5)
        self.assertIn(16 * (DEFAULT_SECTOR_EXTRA >> 3), extents)

    def test_a_stretch_bridge_names_exactly_the_two_walls_it_drags(self):
        """SE20 is the effector that does not move its whole sector."""
        seen = 0
        for name, duke, sprite in self._effectors(20):
            motion = stretch_bridge(duke, sprite)
            sector = duke.sectors[sprite.sector]
            span = range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)
            with self.subTest(map=name):
                self.assertEqual(len(motion["walls"]), 2)
                self.assertEqual(len(set(motion["walls"])), 2)
                for wall_id in motion["walls"]:
                    self.assertIn(wall_id, span)
            seen += 1
        self.assertGreater(seen, 20)

    def test_nearest_walls_breaks_ties_toward_the_lower_index(self):
        """game.cpp keeps a strictly smaller distance, so the first one wins."""
        for name, duke, sprite in self._effectors(20):
            walls = nearest_walls(duke, sprite, count=2)
            with self.subTest(map=name):
                self.assertEqual(walls, sorted(walls, key=lambda w: (
                    sepldist(sprite.x - duke.walls[w].x, sprite.y - duke.walls[w].y), w)))


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(E3L11.exists(), "no Duke3D corpus")
class DifferentialMotionTests(unittest.TestCase):
    """Replaying the travel in both engines is the check that catches real bugs.

    Each of these pins a mistake that passed structural validation and loaded in
    NBlood, and that only a swept comparison against Duke could see.
    """

    @classmethod
    def setUpClass(cls):
        from bloodmap.e3l11 import convert_playable_duke_to_blood
        from bloodmap.format import encode_map, parse_map

        cls.duke = read_duke_map(E3L11)
        disk, cls.report = convert_playable_duke_to_blood(cls.duke)
        cls.level = parse_map(encode_map(disk))
        cls.moving = [
            r for r in cls.report["mechanisms"]["records"]
            if r.get("kind") in {"sliding-door", "rotate-bridge", "swinging-door", "stretch-bridge"}
        ]

    def _sweeps(self, record, steps=16):
        from bloodmap.motion_sim import blood_sweep, duke_sweep

        return (duke_sweep(self.duke, int(record["source_effector"]), steps=steps),
                blood_sweep(self.level, int(record["source_sector"]), steps=steps))

    def test_every_moving_sector_follows_its_duke_original(self):
        """Within 3:2 rounding, over the whole travel rather than at the ends."""
        from bloodmap.motion_sim import compare_sweeps

        self.assertTrue(self.moving)
        for record in self.moving:
            with self.subTest(sector=record["source_sector"], kind=record["kind"]):
                comparison = compare_sweeps(*self._sweeps(record))
                self.assertLess(comparison["max_deviation"], 8.0)
                self.assertGreater(comparison["duke_travel"], 100.0)

    def test_no_moving_sector_folds_through_itself(self):
        from bloodmap.motion_sim import self_intersections

        for record in self.moving:
            _duke_frames, blood_frames = self._sweeps(record, steps=32)
            for step, frame in enumerate(blood_frames):
                with self.subTest(sector=record["source_sector"], step=step):
                    self.assertEqual(self_intersections(frame), [])

    def test_a_masked_marker_angle_would_swing_the_long_way_round(self):
        """The bug that made a 45 degree bridge sweep 315 degrees.

        Blood interpolates the turn linearly from 0 to the marker angle, so
        -256 and 1792 reach the same pose by opposite paths. Reducing the angle
        mod 2048 keeps the endpoint and destroys the motion, which is invisible
        to any check that only looks at the final position.
        """
        from bloodmap.motion_sim import compare_sweeps

        bridge = next(r for r in self.moving if r["kind"] == "rotate-bridge")
        sector_id = int(bridge["source_sector"])
        marker = int(self.level.sectors[sector_id].extra.fields["marker_0"])
        authored = int(self.level.sprites[marker].fields["angle"])
        self.assertNotEqual(authored, 0)

        honest = compare_sweeps(*self._sweeps(bridge))
        self.assertLess(honest["max_deviation"], 8.0)

        # A negative sweep and its masked equivalent finish in the same pose and
        # take opposite paths there, so only a swept comparison can tell them
        # apart. Drive the marker negative and mask it to show the difference.
        self.level.sprites[marker].fields["angle"] = -abs(authored)
        try:
            signed = compare_sweeps(*self._sweeps(bridge))["max_deviation"]
            self.level.sprites[marker].fields["angle"] = (-abs(authored)) & 2047
            masked = compare_sweeps(*self._sweeps(bridge))["max_deviation"]
        finally:
            self.level.sprites[marker].fields["angle"] = authored
        # Hundreds of units apart, against a match that is within rounding.
        self.assertGreater(abs(masked - signed), 500.0)

    def test_equal_slide_marker_angles_would_rotate_the_leaf(self):
        """interpolate(a, a, t) is a, so a shared non-zero angle never reaches 0.

        A sliding door whose markers both carry the Duke slide direction is
        rotated by that angle for its entire travel, at rest included.
        """
        from bloodmap.motion_sim import compare_sweeps

        slider = next(r for r in self.moving if r["kind"] == "sliding-door")
        sector_id = int(slider["source_sector"])
        extra = self.level.sectors[sector_id].extra.fields
        m0, m1 = int(extra["marker_0"]), int(extra["marker_1"])
        self.assertEqual(int(self.level.sprites[m0].fields["angle"]), 0)
        self.assertEqual(int(self.level.sprites[m1].fields["angle"]), 0)

        # compare_sweeps measures each sweep against its own first frame, so a
        # constant rotation cancels out of it entirely and it reports a perfect
        # match. The displacement at rest is what exposes this one.
        from bloodmap.motion_sim import blood_sweep, rest_displacement

        honest = rest_displacement(self.level, sector_id, blood_sweep(self.level, sector_id))
        self.assertAlmostEqual(honest, 0.0, places=6)

        for marker in (m0, m1):
            self.level.sprites[marker].fields["angle"] = 1024
        try:
            frames = blood_sweep(self.level, sector_id)
            turned = rest_displacement(self.level, sector_id, frames)
            relative = compare_sweeps(*self._sweeps(slider))
        finally:
            for marker in (m0, m1):
                self.level.sprites[marker].fields["angle"] = 0
        self.assertGreater(turned, 100.0)
        self.assertLess(relative["max_deviation"], 8.0)  # invisible to the relative check

    def test_a_converted_map_names_its_spawn_the_way_blood_does(self):
        """warpInit reads a kMarkerSPStart with data1 == 0, not the header."""
        from bloodmap.reachability import player_start

        start = player_start(self.level)
        self.assertEqual(start["source"], "kMarkerSPStart with data1 == 0")
        self.assertIsNotNone(start["sprite"])


@unittest.skipUnless(E3L11.exists(), "no Duke3D corpus")
class TriggerWiringTests(unittest.TestCase):
    """The activation graph, which a geometry check cannot see at all.

    Each of these pins a way a converted map could load, validate and match
    Duke's motion exactly while nothing in it could actually be set off.
    """

    @classmethod
    def setUpClass(cls):
        from bloodmap.e3l11 import convert_playable_duke_to_blood
        from bloodmap.format import encode_map, parse_map

        cls.duke = read_duke_map(E3L11)
        disk, cls.report = convert_playable_duke_to_blood(cls.duke)
        cls.level = parse_map(encode_map(disk))

    def _sector_extra(self, sector_id):
        return self.level.sectors[sector_id].extra.fields

    def test_a_touchplate_sector_actually_transmits(self):
        """trTriggerSector only reaches evSend through SetSectorState.

        An untyped sector falls through OperateSector to
        SetSectorState(state ^ 1), and that sends the channel only when
        `triggerOn && state` (or triggerOff and not state). Without those bits
        the sector flips its own state and tells nobody. 878 of the 885
        Enter-plus-TX sectors in the Blood corpus set triggerOn.
        """
        plates = [
            sprite.sector for sprite in self.duke.sprites
            if sprite.picnum == 3 and sprite.lotag
        ]
        # A plate that shares its sector with an SE12 light pulse inherits that
        # sector's busyTime, which sends OperateSector down OperateDoor rather
        # than straight to SetSectorState. The channel still goes out, at the
        # end of the busy rather than on the step, so it is a delay and not a
        # failure -- E3L11's sector 196 is the one that does it.
        delayed = [s for s in plates if int(self._sector_extra(s)["busy_time_a"])]
        self.assertLessEqual(len(delayed), 1)
        self.assertTrue(plates)
        for sector_id in plates:
            extra = self._sector_extra(sector_id)
            with self.subTest(sector=sector_id):
                self.assertTrue(int(extra["trigger_enter"]))
                self.assertGreater(int(extra["tx_id"]), 0)
                self.assertTrue(int(extra["trigger_on"]) or int(extra["trigger_off"]))

    def test_walking_into_sector_225_reaches_the_whole_set_piece(self):
        """The freeway collapse: one plate, five bridges, nineteen explosives."""
        channel = int(self._sector_extra(225)["tx_id"])
        self.assertGreater(channel, 0)
        sectors = [
            index for index, sector in enumerate(self.level.sectors)
            if sector.extra and int(sector.extra.fields.get("rx_id", 0)) == channel
        ]
        traps = [
            sprite for sprite in self.level.sprites
            if sprite.extra and int(sprite.extra.fields.get("rx_id", 0)) == channel
            and int(sprite.fields["type"]) == 459
        ]
        self.assertEqual(sorted(sectors), [162, 220, 221, 222, 223])
        self.assertEqual(len(traps), 19)

    def test_an_explosive_group_listens_to_whatever_arms_it(self):
        """A MasterSwitch arms the explosives in its own sector, not its hitag.

        E3L11's group 50 is armed by the MasterSwitch on channel 49 that also
        turns the bridges, so keying it to its own hitag of 50 would leave ten
        explosives waiting on a channel nothing sends.
        """
        armed = {
            int(record["channel"])
            for record in self.report["mechanisms"]["records"]
            if record.get("kind") == "chain-exploder" and record["channel"]
        }
        transmitters = set(self.report["mechanisms"]["channel_audit"]["transmitters"])
        for channel in armed:
            with self.subTest(channel=channel):
                self.assertIn(str(channel), {str(t) for t in transmitters})

    def test_nothing_receives_a_channel_no_one_sends(self):
        audit = self.report["mechanisms"]["channel_audit"]
        self.assertEqual(audit["dangling_user_receive_channels"], [])

    def test_a_masterswitch_makes_its_own_sector_a_receiver(self):
        """It calls G_OperateSectors on its sector, exactly as an ACTIVATOR does.

        168 MasterSwitches in the corpus sit in an operable sector with no
        ACTIVATOR beside them, so treating only ACTIVATORs as receivers leaves
        those sectors deaf.
        """
        for sprite in self.duke.sprites:
            if sprite.picnum != 8 or not sprite.lotag:
                continue
            sector = self.level.sectors[sprite.sector]
            if sector.extra is None or int(sector.fields["type"]) == 0:
                continue  # an untagged sector has nothing to operate
            with self.subTest(sector=sprite.sector):
                self.assertGreater(int(sector.extra.fields["rx_id"]), 0)

    def test_a_touchplate_does_not_disturb_a_mover_it_shares_a_sector_with(self):
        """E1L3 puts a touchplate inside two of its rotate bridges."""
        from bloodmap.e3l11 import convert_playable_duke_to_blood
        from bloodmap.format import encode_map, parse_map
        from bloodmap.motion_sim import blood_sweep, rest_displacement

        path = ROOT / "maps" / "duke3d" / "E1L3.MAP"
        if not path.exists():
            self.skipTest("E1L3 not present")
        disk, _report = convert_playable_duke_to_blood(read_duke_map(path))
        level = parse_map(encode_map(disk))
        for sector_id in (450, 184):
            with self.subTest(sector=sector_id):
                frames = blood_sweep(level, sector_id, steps=8)
                self.assertLess(rest_displacement(level, sector_id, frames), 8.0)
