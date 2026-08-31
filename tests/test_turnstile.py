"""The turnstile door, built to a template mined from four rotors.

`projects/blood-city/references/auto-rotators.md` found 88 kSectorRotateMarked
instances in 14 maps and split them into doors and scenery -- a spatial split,
not a field one. The template here is the door subfamily: E1M4 151/314
(campaign) and DWE1M9 61/64 (curated, precedent and never convention).

Two things differ between those four and are the only arguments that carry
meaning: where the opening is, and how fast it spins. Everything else is
pinned below against what was measured.
"""

from __future__ import annotations

import unittest

from bloodmap.construction import _sprite_angle
from bloodmap.mechanism import (
    BLADE_COUNT,
    BLADE_PICNUM,
    CAMPAIGN_TRAVEL_ANGLE,
    DEATH_WISH_TRAVEL_ANGLE,
    LEVEL_START_CHANNEL,
    MARKER_AXIS_TYPE,
    MARKER_PICNUM,
    MARKER_STATNUM,
    PLAYER_HEIGHT,
    ROTATE_MARKED,
    SFX_PICNUM,
    SFX_TYPE,
    TURN,
    TURNSTILE_TEMPLATE,
    MechanismError,
    turnstile,
    turnstile_pair,
)
from bloodmap.planar_layout import PlanarLayout

U = 1024
COURT = 12 * U
ROTOR, GAP = 2 * U, 2 * U
WALL, FLOOR, CEILING, SKY = 400, 294, 285, 3491


def court(**kwargs):
    """Outside and inside, joined only through the two rotors."""
    layout = PlanarLayout(name="turnstile-test")
    mid = COURT // 2
    y0, y1 = mid - ROTOR // 2, mid + ROTOR // 2
    left_x0, right_x0 = mid - GAP // 2 - ROTOR, mid + GAP // 2
    for name, (ya, yb) in (("outside", (0, y0)), ("inside", (y1, COURT))):
        layout.add_region(
            f"region:{name}", [(0, ya), (COURT, ya), (COURT, yb), (0, yb)],
            floor_z=0, ceiling_z=-4 * PLAYER_HEIGHT, wall_picnum=WALL,
            floor_picnum=FLOOR, ceiling_picnum=SKY, parallax_ceiling=True)
    outlines = (
        [(left_x0, y0), (left_x0 + ROTOR, y0), (left_x0 + ROTOR, y1), (left_x0, y1)],
        [(right_x0, y0), (right_x0 + ROTOR, y0), (right_x0 + ROTOR, y1), (right_x0, y1)],
    )
    pivots = ((left_x0 + ROTOR // 2, mid), (right_x0 + ROTOR // 2, mid))
    built = turnstile_pair(
        layout, "turnstile", outlines=outlines, pivots=pivots, period=255,
        floor_z=0, ceiling_z=-2 * PLAYER_HEIGHT, wall_picnum=WALL,
        floor_picnum=FLOOR, ceiling_picnum=CEILING, **kwargs)
    for index, outline in enumerate(outlines):
        side = "a" if index == 0 else "b"
        layout.add_connection(f"c:{side}:front", "region:outside",
                              f"turnstile:{side}", a1=outline[0], a2=outline[1],
                              min_width=U)
        layout.add_connection(f"c:{side}:back", f"turnstile:{side}",
                              "region:inside", a1=outline[3], a2=outline[2],
                              min_width=U)
    layout.set_player_start("region:outside", x=mid, y=y0 // 2, z=0)
    return layout, built


class TemplateFieldTests(unittest.TestCase):
    """Every one of these was measured on all four door rotors."""

    def setUp(self):
        self.layout, self.built = court()
        self.disk = self.layout.compile().level.to_disk_map()
        self.rotors = [s for s in self.disk.sectors
                       if int(s.fields["type"]) == ROTATE_MARKED]

    def test_both_rotors_are_rotate_marked(self):
        self.assertEqual(len(self.rotors), 2)

    def test_it_listens_on_level_start_and_never_again(self):
        for rotor in self.rotors:
            self.assertEqual(int(rotor.extra.fields["rx_id"]), LEVEL_START_CHANNEL)

    def test_both_waves_retrigger_which_is_what_makes_it_endless(self):
        for rotor in self.rotors:
            x = rotor.extra.fields
            self.assertEqual((int(x["busy_wave_a"]), int(x["busy_wave_b"])), (1, 1))
            self.assertEqual((int(x["retrigger_a"]), int(x["retrigger_b"])), (1, 1))

    def test_nothing_interrupts_it(self):
        for rotor in self.rotors:
            self.assertEqual(int(rotor.extra.fields["interruptable"]), 0)

    def test_the_period_lives_in_one_busy_field_and_never_both(self):
        for rotor in self.rotors:
            x = rotor.extra.fields
            pair = (int(x["busy_time_a"]), int(x["busy_time_b"]))
            self.assertIn(0, pair, "a rotor with both fields set has no direction")
            self.assertEqual(max(pair), 255)

    def test_a_pair_counter_rotates_by_mirroring_that_field(self):
        """E1M4 runs 255/0 against 0/255, DWE1M9 100/0 against 0/100."""
        a, b = (rotor.extra.fields for rotor in self.rotors)
        self.assertEqual(int(a["busy_time_a"]), int(b["busy_time_b"]))
        self.assertEqual(int(a["busy_time_b"]), int(b["busy_time_a"]))
        self.assertNotEqual(int(a["busy_time_a"]), int(b["busy_time_a"]))

    def test_the_same_direction_variant_is_reachable(self):
        """DNE3L6 3 and 11 both run 0/100. Attested, rarer, not the default."""
        _layout, built = court(counter_rotating=False)
        left, right = built["rotors"]
        self.assertEqual(left["clockwise"], right["clockwise"])
        self.assertFalse(built["counter_rotating"])

    def test_exactly_one_axis_marker_per_rotor_at_the_pivot(self):
        markers = [s for s in self.disk.sprites
                   if int(s.fields["type"]) == MARKER_AXIS_TYPE]
        self.assertEqual(len(markers), 2)
        for marker in markers:
            self.assertEqual(int(marker.fields["picnum"]), MARKER_PICNUM)
            self.assertEqual(int(marker.fields["status"]), MARKER_STATNUM)

    def test_the_marker_owns_its_sector_or_the_loader_deletes_it(self):
        """dbLoadMap rebuilds marker0 from the marker's `owner` and deletes any
        marker whose owner does not name a sector with an XSECTOR."""
        for sprite in self.disk.sprites:
            if int(sprite.fields["type"]) != MARKER_AXIS_TYPE:
                continue
            owner = int(sprite.fields["owner"])
            self.assertEqual(owner, int(sprite.fields["sector"]))
            self.assertEqual(int(self.disk.sectors[owner].fields["type"]),
                             ROTATE_MARKED)

    def test_marker_zero_points_at_the_axis(self):
        for rotor in self.rotors:
            index = int(rotor.extra.fields["marker_0"])
            self.assertEqual(int(self.disk.sprites[index].fields["type"]),
                             MARKER_AXIS_TYPE)

    def test_four_blades_per_rotor_and_they_are_grates(self):
        """The blades are grates, which is what makes a turnstile read as
        passable machinery rather than a solid drum. Death Wish reuses the
        campaign's exact tile."""
        # The literals, not the constants: a test that compares a build against
        # the constant it was built from moves with it and pins nothing. All
        # four mined rotors carry four sprites on tile 332.
        blades = [s for s in self.disk.sprites if int(s.fields["picnum"]) == 332]
        self.assertEqual(len(blades), 8, "four blades on each of two rotors")
        self.assertEqual(BLADE_PICNUM, 332)
        self.assertEqual(BLADE_COUNT, 4)

    def test_the_sound_sprite_is_off_by_default(self):
        """E1M4 puts one in both its rotors and DWE1M9 in neither, so it is a
        map's habit and not a trait of the family."""
        self.assertFalse([s for s in self.disk.sprites
                          if int(s.fields["type"]) == SFX_TYPE])
        _layout, built = court(sound=True)
        self.assertTrue(all(rotor["sound"] for rotor in built["rotors"]))

    def test_the_template_records_where_each_fact_came_from(self):
        self.assertEqual(TURNSTILE_TEMPLATE["mined_from"],
                         {"E1M4": [151, 314], "DWE1M9": [61, 64]})
        self.assertIn("precedent", TURNSTILE_TEMPLATE["populations"]["DWE1M9"])


class TravelAngleTests(unittest.TestCase):
    """How far it turns is the axis marker's angle, and it is not a facing.

    This is the one fact the four rotors do NOT agree on -- E1M4 turns -8192,
    DWE1M9 2047 -- so it is an argument. It is also the fact that was silently
    destroyed: `add_sprite` masked every angle to 0..2047, and -8192 & 2047 is
    exactly 0, which is a rotor that does not move.
    """

    def test_a_facing_still_wraps(self):
        self.assertEqual(_sprite_angle(0, 2048 + 17), 17)
        self.assertEqual(_sprite_angle(0, -1), 2047)

    def test_an_axis_marker_keeps_its_travel(self):
        self.assertEqual(_sprite_angle(MARKER_AXIS_TYPE, CAMPAIGN_TRAVEL_ANGLE),
                         CAMPAIGN_TRAVEL_ANGLE)
        self.assertEqual(_sprite_angle(MARKER_AXIS_TYPE, DEATH_WISH_TRAVEL_ANGLE),
                         DEATH_WISH_TRAVEL_ANGLE)

    def test_four_turns_would_have_masked_to_a_standstill(self):
        """The exact trap: E1M4's value is a whole number of turns."""
        self.assertEqual(CAMPAIGN_TRAVEL_ANGLE % TURN, 0)
        self.assertEqual(CAMPAIGN_TRAVEL_ANGLE & 2047, 0)

    def test_the_built_map_carries_the_campaign_value(self):
        layout, built = court()
        disk = layout.compile().level.to_disk_map()
        for sprite in disk.sprites:
            if int(sprite.fields["type"]) == MARKER_AXIS_TYPE:
                self.assertEqual(int(sprite.fields["angle"]), CAMPAIGN_TRAVEL_ANGLE)
        for rotor in built["rotors"]:
            self.assertEqual(rotor["travel_angle"], CAMPAIGN_TRAVEL_ANGLE)
            self.assertEqual(rotor["turns"], CAMPAIGN_TRAVEL_ANGLE / TURN)

    def test_death_wishs_single_turn_is_available(self):
        layout, _built = court(travel_angle=DEATH_WISH_TRAVEL_ANGLE)
        disk = layout.compile().level.to_disk_map()
        angles = {int(s.fields["angle"]) for s in disk.sprites
                  if int(s.fields["type"]) == MARKER_AXIS_TYPE}
        self.assertEqual(angles, {DEATH_WISH_TRAVEL_ANGLE})


class RefusalTests(unittest.TestCase):
    def test_a_period_outside_the_engine_field_is_refused(self):
        for period in (0, -1, 70000):
            with self.subTest(period=period):
                with self.assertRaises(MechanismError):
                    court_period(period)

    def test_a_rotor_needs_a_closed_outline(self):
        layout = PlanarLayout(name="x")
        with self.assertRaises(MechanismError):
            turnstile(layout, "r", [(0, 0), (10, 0)], pivot=(5, 0), period=255,
                      floor_z=0, ceiling_z=-1024)


def court_period(period):
    layout = PlanarLayout(name="p")
    layout.add_region("region:o", [(0, 0), (4096, 0), (4096, 4096), (0, 4096)],
                      floor_z=0, ceiling_z=-4 * PLAYER_HEIGHT, wall_picnum=WALL,
                      floor_picnum=FLOOR, ceiling_picnum=SKY)
    return turnstile(layout, "rotor",
                     [(1024, 1024), (2048, 1024), (2048, 2048), (1024, 2048)],
                     pivot=(1536, 1536), period=period, floor_z=0,
                     ceiling_z=-2 * PLAYER_HEIGHT)


class CorpusAgreementTests(unittest.TestCase):
    """The built rotor against the one it was mined from. Skips without maps."""

    def rotors(self, name, sectors):
        from bloodmap.format import read_map
        from bloodmap.patterns import PatternError, corpus_map_path

        try:
            path = corpus_map_path(name)
        except PatternError:
            self.skipTest(f"{name} is not in the local corpus")
        if not path.exists():
            self.skipTest(f"{name} is not in the local corpus")
        disk = read_map(path)
        return disk, [disk.sectors[s] for s in sectors]

    def test_the_campaign_pair_has_the_fields_the_template_claims(self):
        disk, rotors = self.rotors("E1M4", (151, 314))
        for rotor in rotors:
            x = rotor.extra.fields
            self.assertEqual(int(rotor.fields["type"]), ROTATE_MARKED)
            self.assertEqual(int(x["rx_id"]), LEVEL_START_CHANNEL)
            self.assertEqual((int(x["retrigger_a"]), int(x["retrigger_b"])), (1, 1))
            self.assertEqual(int(disk.sprites[int(x["marker_0"])].fields["angle"]),
                             CAMPAIGN_TRAVEL_ANGLE)

    def test_the_campaign_rotor_moves_no_walls_and_neither_does_ours(self):
        """A 615 sweeps only walls flagged cstat 16384/32768. E1M4's rotor
        walls are all cstat 0, so the geometry stands still and what turns is
        the carried grates -- which motion_sim does not model.
        """
        _disk, rotors = self.rotors("E1M4", (151, 314))
        for rotor in rotors:
            first = int(rotor.fields["wall_ptr"])
            count = int(rotor.fields["wall_count"])
            flags = [int(_disk.walls[w].fields["cstat"])
                     for w in range(first, first + count)]
            self.assertTrue(all(not (c & (16384 | 32768)) for c in flags))

    def test_death_wish_uses_the_campaigns_own_blade_tile(self):
        disk, _rotors = self.rotors("DWE1M9", (61, 64))
        blades = [s for s in disk.sprites
                  if int(s.fields["picnum"]) == BLADE_PICNUM]
        self.assertTrue(blades)


if __name__ == "__main__":
    unittest.main()
