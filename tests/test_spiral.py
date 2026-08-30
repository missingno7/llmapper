"""The spiral prefab, tested across its parameter space rather than at one point.

Building one instance and looking at it is the classic procedural failure, and
this project already has two scars from it. So this sweeps the range -- a
quarter turn, a half turn, three turns, the tightest radius that still yields a
walkable tread, the largest rise that stays a stair -- and for each asks the
four questions that decide whether it is a stair at all:

* is every step inside the player's 4,096 limit;
* is the outer tread wider than a body;
* do the bands of consecutive turns stay disjoint;
* does `overlap_visibility` stay silent.
"""

from __future__ import annotations

import math
import unittest

from bloodmap import overlap_visibility as ov
from bloodmap import spiral
from bloodmap.planar_layout import PlanarLayout

AXIS = (8192, 8192)
BODY = spiral.PLAYER_WIDTH
PH = spiral.PLAYER_HEIGHT


def build(**kwargs) -> tuple[PlanarLayout, object]:
    layout = PlanarLayout(name="spiral")
    options = dict(axis=AXIS, base_floor_z=0, rise=-47104, exit_angle=180.0)
    options.update(kwargs)
    structure = spiral.spiral_stair(layout, "helix", **options)
    return layout, structure


def stand_on(layout, region_id: str) -> None:
    """Put the start inside a step rather than on the angle it begins at.

    A wedge's own entry angle is a boundary, not a place to stand.
    """
    region = layout.regions[region_id]
    xs = [p[0] for p in region.outer]
    ys = [p[1] for p in region.outer]
    layout.set_player_start(region_id, x=sum(xs) // len(xs),
                            y=sum(ys) // len(ys), z=int(region.floor_z))


class DerivationTests(unittest.TestCase):
    """The author states a rise and a way out; the turns are a consequence."""

    def test_e3m1s_own_climb_comes_back_as_e3m1s_own_stair(self):
        # 23 steps of 2048 is 47,104, and 23 * 22.5 is 517.5 degrees -- one turn
        # plus 157.5. Asked for that rise and that exit, the plan should land on
        # the same stair rather than on some other stair with the same endpoints.
        # 23 steps plus a landing at each end is 25 slots of 22.5 degrees --
        # 562.5, which is one turn plus 202.5. The exit angle is where the top
        # landing's far edge sits, not where the last step does.
        plan = spiral.plan_spiral(rise=-47104, exit_angle=202.5)
        self.assertEqual(plan.steps, 23)
        self.assertEqual(plan.step_rise, -2048)
        self.assertAlmostEqual(plan.swept_degrees, 562.5)

    def test_every_extra_turn_lands_the_same_way_out(self):
        """That is the whole reason `k` is free and the exit angle is not."""
        for extra in range(3):
            plan = spiral.plan_spiral(rise=-47104 - extra * 32768,
                                      exit_angle=180.0)
            self.assertAlmostEqual(plan.swept_degrees % 360, 180.0, places=3)

    def test_it_derives_against_the_corpus_rise_not_the_player_limit(self):
        plan = spiral.plan_spiral(rise=-81920, exit_angle=180.0)
        # A ladder would be legal: 81,920 over 540 degrees is 24 steps of 3,413,
        # inside the 4,096 limit. The corpus target pulls it to a real stair.
        self.assertLessEqual(abs(plan.step_rise), spiral.MAX_STEP)
        self.assertLess(abs(abs(plan.step_rise) - spiral.TARGET_STEP_RISE),
                        abs(spiral.MAX_STEP - spiral.TARGET_STEP_RISE))
        self.assertIn("refusal threshold rather than the target", plan.why)

    def test_a_rise_no_number_of_turns_can_carry_is_refused_by_name(self):
        with self.assertRaises(spiral.SpiralError) as caught:
            spiral.plan_spiral(rise=-4_000_000, exit_angle=90.0)
        self.assertIn("no whole number of extra turns", str(caught.exception))


class TreadTests(unittest.TestCase):
    def test_the_minimum_radius_comes_from_the_step_angle(self):
        smallest = spiral.minimum_radius()
        self.assertEqual(smallest, math.ceil(BODY / math.radians(22.5)))
        self.assertGreaterEqual(smallest * math.radians(22.5), BODY)

    def test_too_tight_a_radius_names_the_parameters_that_conflict(self):
        with self.assertRaises(spiral.SpiralError) as caught:
            spiral.plan_spiral(rise=-47104, exit_angle=180.0, radius=400)
        message = str(caught.exception)
        self.assertIn("tread", message)
        self.assertIn("radius", message)
        self.assertIn("step angle", message)

    def test_e3m1_walks_the_outside(self):
        """97 units at the newel, 540 at the wall, against a 384 body."""
        plan = spiral.plan_spiral(rise=-47104, exit_angle=202.5)
        self.assertLess(plan.inner_tread, BODY)
        self.assertGreater(plan.outer_tread, BODY)

    def test_room_portals_use_the_long_radial_side_not_a_tread_chord(self):
        """A room must meet a usable flight width, not a 22.5-degree slit."""
        _layout, structure = build(radius=1000)
        entry, exit = structure.flanks
        self.assertGreaterEqual(entry.width, 1000 - spiral.INNER_RADIUS - 1)
        self.assertGreaterEqual(exit.width, 1000 - spiral.INNER_RADIUS - 1)
        self.assertGreater(entry.width,
                           1000 * math.radians(spiral.STEP_ANGLE))

    def test_three_quarter_turn_matches_the_station_descent(self):
        """A 20,480-unit station drop needs ten normal 2,048-unit treads."""
        plan = spiral.plan_spiral(rise=20480, exit_angle=270.0, radius=1000)
        self.assertEqual(plan.steps, 10)
        self.assertEqual(plan.step_rise, 2048)
        self.assertAlmostEqual(plan.swept_degrees, 270.0)

    def test_ports_name_the_two_corridor_directions(self):
        """A connector continues tangentially, not into the spiral's annulus."""
        layout, structure = build(rise=20480, exit_angle=270.0, radius=1000)
        ports = structure.provenance["ports"]
        self.assertEqual(ports["entry"]["corridor_angle"], 270.0)
        self.assertEqual(ports["exit"]["corridor_angle"], 0.0)
        entry = structure.flanks[0]
        outline = spiral.port_corridor_outline(entry, angle=270.0, depth=1024)
        self.assertIn(entry.a, outline)
        self.assertIn(entry.b, outline)
        self.assertEqual(min(y for _x, y in outline), AXIS[1] - 1024)


class SweepTests(unittest.TestCase):
    """The range, not one point in it."""

    #: Chosen to span the range, and each one buildable. A quarter turn cannot
    #: carry much: four slots is two steps, so the rise it can take is 8,192 and
    #: no more -- adding turns to spread it makes the pitch too shallow for the
    #: turns to clear each other, which is the law above. That refusal is tested
    #: separately rather than smuggled in here as a case that quietly fails.
    CASES = {
        "quarter_turn": dict(rise=-4096, exit_angle=90.0),
        "half_turn": dict(rise=-12288, exit_angle=180.0),
        "three_turns": dict(rise=-94208, exit_angle=0.0),
        "e3m1s_own": dict(rise=-47104, exit_angle=202.5),
        "tightest_radius": dict(rise=-47104, exit_angle=202.5,
                                radius=spiral.minimum_radius()),
        "largest_rise": dict(rise=-172032, exit_angle=270.0),
    }

    def test_a_quarter_turn_cannot_carry_a_storey(self):
        """Steepness is decided by the endpoints, and sometimes they refuse.

        Two steps is all a quarter turn has, so 16,384 needs 8,192 a step --
        twice the player's limit -- and every extra turn that would spread it
        makes the pitch too shallow for the turns to clear each other.
        """
        with self.assertRaises(spiral.SpiralError) as caught:
            spiral.plan_spiral(rise=-16384, exit_angle=90.0)
        self.assertIn("turn would sit inside the one above it",
                      str(caught.exception))

    def test_every_case_is_a_stair_a_body_can_walk(self):
        for name, options in self.CASES.items():
            with self.subTest(case=name):
                plan = spiral.plan_spiral(**options)
                self.assertLessEqual(abs(plan.step_rise), spiral.MAX_STEP,
                                     f"{name}: step taller than the player")
                self.assertGreaterEqual(plan.outer_tread, BODY,
                                        f"{name}: outer tread narrower than a body")
                self.assertGreaterEqual(plan.steps, 2)

    def test_consecutive_turns_stay_apart_in_z(self):
        """The arithmetic that makes a helix safe, checked at every size."""
        for name, options in self.CASES.items():
            with self.subTest(case=name):
                plan = spiral.plan_spiral(**options)
                per_turn = abs(plan.step_rise) * (360.0 / plan.step_angle)
                if plan.swept_degrees <= 360.0:
                    continue          # nothing is a turn apart yet
                self.assertGreater(
                    per_turn, plan.clear_height,
                    f"{name}: a turn rises {per_turn:.0f} but the stair is "
                    f"{plan.clear_height} tall, so the bands would intersect")

    def test_every_case_compiles_and_the_checker_stays_silent(self):
        for name, options in self.CASES.items():
            with self.subTest(case=name):
                layout, structure = build(**options)
                self.assertEqual(len(structure.regions),
                                 spiral.plan_spiral(**options).steps + 2)
                self.assertGreaterEqual(len(structure.regions), 4)
                stand_on(layout, structure.regions[0])
                compiled = layout.compile()
                disk = compiled.level.to_disk_map()
                verdicts = ov.audit(disk)
                # A helix overlaps itself across turns and nowhere else, and
                # every one of those is resolved by the band separation.
                self.assertEqual([v for v in verdicts if not v.safe], [],
                                 f"{name}: the checker found an uncut overlap")

    def test_a_helix_overlaps_only_across_turns(self):
        """Adjacent steps never share ground; steps a turn apart always do."""
        layout, structure = build(rise=-98304, exit_angle=0.0)
        stand_on(layout, structure.regions[0])
        disk = layout.compile().level.to_disk_map()
        pairs = ov.overlapping_pairs(disk)
        self.assertTrue(pairs, "three turns should overlap themselves")
        per_turn = int(360 / spiral.STEP_ANGLE)
        for left, right, _kind in pairs:
            self.assertGreater(abs(right - left), 1,
                               "adjacent steps must never overlap")
            self.assertGreaterEqual(abs(right - left), per_turn - 2)


class HandednessTests(unittest.TestCase):
    def test_handedness_reverses_the_sweep(self):
        right, _ = build(handed="right")
        left, _ = build(handed="left")

        def first_step_angle(layout):
            outline = layout.regions["region:helix:step_01"].outer
            return math.degrees(math.atan2(outline[0][1] - AXIS[1],
                                           outline[0][0] - AXIS[0]))

        self.assertNotAlmostEqual(first_step_angle(right), first_step_angle(left))


if __name__ == "__main__":
    unittest.main()
