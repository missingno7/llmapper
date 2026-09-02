"""The city's vocabulary lives in `bloodmap`, because a project may choose
its numbers and may not own its nouns.

P15's readers of E3M1 have to recognise the same words coming the other way,
so each constructor is checked against the corpus number it stands on rather
than against itself.
"""

from __future__ import annotations

import unittest

from bloodmap import city, joins

SKY = 3491
GRADE = 8192
ROAD_Z = GRADE + 2048
STANDING = 16960


def _sky_of(floor_z):
    return floor_z - 6 * 32768


class TheGround(unittest.TestCase):

    def test_a_street_does_not_wear_the_kerb_tile(self):
        # W1's rule, in the constructor rather than in a project: a kerb
        # exists only where a road meets a pavement.
        made = city.street("plane", [[(0, 0), (8192, 0), (8192, 8192)]],
                           floor_z=ROAD_Z, sky_z=_sky_of(ROAD_Z),
                           sky_tile=SKY)
        self.assertNotEqual(made.wall_tile, city.KERB_TILE)
        self.assertEqual(made.kind, joins.ROAD)

    def test_an_island_stands_a_kerb_above_the_road(self):
        road = city.street("plane", [[(0, 0), (1, 0), (1, 1)]],
                           floor_z=ROAD_Z, sky_z=_sky_of(ROAD_Z), sky_tile=SKY)
        pavement = city.island("i", [[(0, 0), (1, 0), (1, 1)]],
                               floor_z=GRADE, sky_z=_sky_of(GRADE),
                               sky_tile=SKY)
        self.assertEqual(road.floor_z - pavement.floor_z, city.KERB_RISE)
        self.assertEqual(
            joins.height_relation(road.floor_z, pavement.floor_z),
            joins.B_ABOVE)

    def test_an_end_wall_stands_in_e3m1_s_band(self):
        from bloodmap.street import END_WALL_RISE_BODIES

        made = city.end_wall("end_wall:avenue", (0, 0, 7168, 2048),
                             road_floor_z=ROAD_Z, standing_height=STANDING,
                             sky_tile=SKY)
        rise = (ROAD_Z - made.floor_z) / STANDING
        low, high = END_WALL_RISE_BODIES
        self.assertGreaterEqual(rise, low - 0.5)
        self.assertLessEqual(rise, high + 0.5)
        self.assertEqual(made.kind, joins.END_WALL)


class TheWater(unittest.TestCase):

    def test_the_shore_steps_down_by_blood_s_own_autostep_or_less(self):
        from bloodmap.player_space import player_profile

        made = city.waterfront("", x0=0, x1=8192, y=0, walk_depth=2048,
                               shore_depth=2048, sea_depth=8192,
                               horizon_depth=2048, pavement_z=GRADE,
                               sky_z_of=_sky_of, sky_tile=SKY)
        walk, shore = made[0], made[1]
        self.assertEqual(shore.floor_z - walk.floor_z, joins.SHORE_STEP)
        self.assertLessEqual(joins.SHORE_STEP,
                             player_profile("blood").max_step)

    def test_the_sea_pans_and_drags_under_palette_ten(self):
        sea = city.waterfront("", x0=0, x1=1, y=0, walk_depth=1,
                              shore_depth=1, sea_depth=1, horizon_depth=1,
                              pavement_z=GRADE, sky_z_of=_sky_of,
                              sky_tile=SKY)[2]
        self.assertEqual(sea.floor_tile, joins.SEA_TILE)
        self.assertEqual(sea.finish["floor_pal"], joins.SEA_PALETTE)
        for name in ("pan_floor", "pan_always", "drag"):
            self.assertTrue(sea.behavior[name], name)

    def test_the_horizon_is_zero_height_and_wears_the_city_s_own_sky(self):
        # W4: one connected outdoor space wears one sky, 271 of 271 campaign
        # regions. The horizon's trick is the zero height and the parallax
        # bit on both, not DWE3M10's particular tile.
        horizon = city.waterfront("", x0=0, x1=1, y=0, walk_depth=1,
                                  shore_depth=1, sea_depth=1, horizon_depth=1,
                                  pavement_z=GRADE, sky_z_of=_sky_of,
                                  sky_tile=SKY)[3]
        self.assertEqual(horizon.floor_z, horizon.ceiling_z)
        self.assertEqual(horizon.floor_tile, SKY)
        self.assertEqual(horizon.ceiling_tile, SKY)
        self.assertTrue(horizon.floor_stat & 1)
        self.assertTrue(horizon.parallax_ceiling)


class TheShell(unittest.TestCase):

    def _shell(self):
        return city.shell("block", (0, 0, 16384, 16384), wall_thickness=1024,
                          door_width=4096, roof_z=GRADE - 4 * STANDING,
                          floor_z=GRADE, interior_z=GRADE - 3 * STANDING,
                          head_z=GRADE - 2 * STANDING,
                          sky_z=_sky_of(GRADE - 4 * STANDING), sky_tile=SKY,
                          wall_tile=joins.FACADE_FAMILY[0],
                          sector_type=614)

    def test_a_shell_is_a_facade_a_room_and_an_opening(self):
        surfaces, _declared = self._shell()
        self.assertEqual([s.kind for s in surfaces],
                         [joins.FACADE, joins.INTERIOR, joins.OPENING])

    def test_the_facade_is_one_simple_ring_cut_open_at_the_door(self):
        # Not a rectangle with a hole: the doorway reaches the outside, so a
        # hole would TOUCH the outer ring at the mouth, which is degenerate.
        surfaces, _declared = self._shell()
        self.assertEqual(len(surfaces[0].rings), 1)
        self.assertEqual(len(surfaces[0].rings[0]), 12)

    def test_the_insert_carries_the_sector_type_and_the_facade_does_not(self):
        surfaces, declared = self._shell()
        self.assertEqual(surfaces[2].sector_type, 614)
        self.assertEqual(surfaces[0].sector_type, 0)
        self.assertEqual(declared["sector_type"], 614)

    def test_the_roof_wears_e3m1_s_own_tile(self):
        surfaces, _declared = self._shell()
        self.assertEqual(surfaces[0].floor_tile, joins.ROOF_TILE)

    def test_an_unrealised_link_says_so_rather_than_being_absent(self):
        made = city.insert("door:x", holder="shell:x", room_id="interior:x",
                           void=[(0, 0)], wiring=[{"channel": 400,
                                                   "realised": False,
                                                   "why": "no tx yet"}])
        self.assertFalse(made["wiring"][0]["realised"])
        self.assertIn("no tx", made["wiring"][0]["why"])


class ASectorTypeAloneIsNotAMechanism(unittest.TestCase):
    """The question slice 4 was set: does a construct declared against a
    room's records survive the compiler's passes?

    It does -- Rule 2 finds 0 of 9 closures moved -- and it was not a curtain
    to begin with. A sector type with no flagged wall drags nothing, and the
    read-back said so in two sentences before anything else was asked.
    """

    def _shell(self, **overrides):
        spec = dict(wall_thickness=1024, door_width=4096,
                    roof_z=GRADE - 4 * STANDING, floor_z=GRADE,
                    interior_z=GRADE - 3 * STANDING,
                    head_z=GRADE - 2 * STANDING,
                    sky_z=_sky_of(GRADE - 4 * STANDING), sky_tile=SKY,
                    wall_tile=joins.FACADE_FAMILY[0], sector_type=614)
        spec.update(overrides)
        return city.shell("block", (0, 0, 16384, 16384), **spec)

    def test_the_declaration_carries_a_leaf(self):
        _surfaces, declared = self._shell()
        leaf = declared["leaf"]
        self.assertEqual(leaf["tile"], city.CURTAIN_FABRIC)
        self.assertTrue(leaf["flags"] & city.DRAG_FORWARD)
        self.assertEqual(leaf["faces"], joins.PAVEMENT)

    def test_the_leaf_is_masked_or_the_fabric_is_drawn_nowhere(self):
        # engine.cpp:4938-4940 draws a two-sided wall's middle band only when
        # it is masked or one-way. Unmasked, conformance counts 0 visible
        # fabric walls -- "the fabric shows on the step bands and nowhere a
        # body walks".
        _surfaces, declared = self._shell()
        self.assertTrue(declared["leaf"]["flags"] & city.MASKED)
        self.assertEqual(declared["leaf"]["over_picnum"], city.CURTAIN_FABRIC)

    def test_the_fabric_is_the_conformance_template_s_own_tile(self):
        from bloodmap.conformance import CURTAIN_TEMPLATE

        self.assertEqual(city.CURTAIN_FABRIC,
                         CURTAIN_TEMPLATE["picnum"])


if __name__ == "__main__":
    unittest.main()
