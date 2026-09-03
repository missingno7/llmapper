"""The owner's second walk (2026-09-03), as readers that fail first.

Eight findings, each with an absolute reading off a built map. The fixtures
below are the faults themselves, built deliberately, so every gate is shown
catching the thing it was written for before it is shown passing.
"""

from __future__ import annotations

import unittest

from bloodmap import city, joins
from bloodmap import street_model as sm
from bloodmap.format import SPRITE_FIELDS
from bloodmap.model import DiskObject, PackedExtra
from bloodmap.planar_layout import PlanarLayout

SKY = 3491
GRADE = 8192
ROAD_Z = GRADE + 2048
FAMILY = set(joins.FACADE_FAMILY)


def _street(**region):
    """One pavement piece under the sky, with whatever is asked of it."""
    layout = PlanarLayout(name="second-walk-fixture")
    spec = dict(floor_z=GRADE, ceiling_z=GRADE - 6 * 32768, floor_picnum=4,
                ceiling_picnum=SKY, wall_picnum=401, floor_shade=32,
                parallax_ceiling=True, role="street")
    spec.update(region)
    layout.add_region("pavement", [(0, 0), (16384, 0), (16384, 16384),
                                   (0, 16384)], declared_zero_exit=True,
                      **spec)
    layout.set_player_start("pavement", x=8192, y=8192, z=GRADE, angle=0)
    return layout.compile().level.to_disk_map()


def _sprite(disk, *, tile, sector, x, y, z=None, cstat=0, xsprite=None,
            sprite_type=0):
    fields = {name: 0 for name, _code in SPRITE_FIELDS}
    fields.update({
        "x": x, "y": y,
        "z": int(disk.sectors[sector].fields["floor_z"]) if z is None else z,
        "sector": sector, "picnum": tile, "cstat": cstat, "shade": -8,
        "type": sprite_type, "initial_type": sprite_type,
        "x_repeat": 64, "y_repeat": 64, "owner": -1, "extra": -1,
        "clipdist": 32,
    })
    extra = None
    if xsprite:
        from bloodmap.format import XSPRITE_SCHEMA

        packed = {name: 0 for name, _bits, _signed in XSPRITE_SCHEMA}
        packed.update(reference=len(disk.sprites), target=-1, burn_source=-1)
        packed.update({k: int(v) for k, v in xsprite.items()})
        fields["extra"] = len(disk.sprites) + 1
        extra = PackedExtra(kind="XSPRITE", fields=packed, opaque_tail=b"")
    disk.sprites.append(DiskObject(fields=fields, extra=extra))
    return len(disk.sprites) - 1


class W5ADoorIsDoorSizedAndShut(unittest.TestCase):
    """E3M1's six Z-motion doors are 256 to 1024 long, 256 thick and CLOSED
    at rest, ceiling on floor, all six. The city's nine were 4096 x 1024 with
    33920 of clear -- the whole facade lifting."""

    def _door(self, *, long_side, thickness, clear, travel):
        layout = PlanarLayout(name="door-fixture")
        layout.add_region("room", [(0, 0), (8192, 0), (8192, 8192), (0, 8192)],
                          floor_z=GRADE, ceiling_z=GRADE - 3 * 16960,
                          floor_picnum=304, ceiling_picnum=454,
                          wall_picnum=401, role="gated_pocket")
        layout.add_region("door", [(0, 8192), (long_side, 8192),
                                   (long_side, 8192 + thickness),
                                   (0, 8192 + thickness)],
                          floor_z=GRADE, ceiling_z=GRADE - clear,
                          floor_picnum=4, ceiling_picnum=454,
                          wall_picnum=401, role="doorway", type=600,
                          sector_behavior={"off_ceiling_z": GRADE,
                                           "on_ceiling_z": GRADE - travel,
                                           "busy_time_a": 5})
        layout.add_connection("mouth", "room", "door", role="portal",
                              a1=(0, 8192), a2=(long_side, 8192))
        layout.set_player_start("room", x=4096, y=4096, z=GRADE, angle=0)
        return layout.compile().level.to_disk_map()

    def test_a_facade_wide_door_standing_open_is_caught(self):
        faults = sm.door_envelope_faults(
            self._door(long_side=4096, thickness=1024, clear=33920,
                       travel=33920))
        text = " ".join(faults)
        self.assertIn("4096 across is outside", text)
        self.assertIn("1024 thick", text)
        self.assertIn("standing open at rest", text)

    def test_e3m1_s_own_envelope_is_silent(self):
        self.assertEqual(
            sm.door_envelope_faults(
                self._door(long_side=1024, thickness=256, clear=0,
                           travel=city.DOOR_TRAVEL)), [])

    def test_the_constructor_builds_inside_that_envelope(self):
        self.assertEqual(city.DOOR_THICKNESS, 256)
        low, high = city.DOOR_WIDTH_ENVELOPE
        self.assertTrue(low <= city.DOOR_WIDTH <= high)


class W6ASwitchThatCannotSend(unittest.TestCase):
    """`triggers.cpp:102-104` gates every message on the send-when bit of the
    state being entered. Nine switches carried a tx and neither bit."""

    def test_a_tx_with_no_send_when_bit_is_caught(self):
        disk = _street()
        _sprite(disk, tile=city.SWITCH_TILE, sector=0, x=64, y=8192,
                cstat=16, sprite_type=20, xsprite={"tx_id": 400})
        faults = sm.switch_faults(disk)
        self.assertEqual(len(faults), 1)
        self.assertIn("triggers.cpp:102-104", faults[0])

    def test_trigger_on_is_enough(self):
        disk = _street()
        _sprite(disk, tile=city.SWITCH_TILE, sector=0, x=64, y=8192,
                cstat=16, sprite_type=20,
                xsprite={"tx_id": 400, "trigger_on": 1})
        self.assertEqual(sm.switch_faults(disk), [])

    def test_the_constructor_sets_it(self):
        made = city.switch("s", (0, 0), tx_id=400)
        self.assertEqual(made["xsprite"]["trigger_on"], 1)
        self.assertTrue(made["solid_only"])


class W7APropHasARole(unittest.TestCase):
    """A tile's role comes from `bloodmap.owner_anchors`, which names 224
    tiles, and never from a census or a table typed here.

    Tile 510 was chosen for being drawn bright and eleven of eighteen hung on
    red walls between street pieces. The owner names 510 a `wall` -- "metal
    plate" -- so it was never a prop at all, and the local table that gave it
    a role was the guess dressed up as the answer.
    """

    def test_the_owner_calls_510_a_wall_and_that_settles_it(self):
        from bloodmap.owner_anchors import load_owner_anchors

        anchor = load_owner_anchors().get(510)
        self.assertIsNotNone(anchor)
        self.assertEqual(anchor.kind, "wall")
        disk = _street()
        _sprite(disk, tile=510, sector=0, x=8192, y=8192)
        self.assertTrue(any("as a sprite" in row and "names it a wall" in row
                            for row in sm.prop_role_faults(disk)))

    def test_a_lantern_hanging_under_the_sky_is_caught(self):
        disk = _street()
        _sprite(disk, tile=641, sector=0, x=8192, y=8192,
                z=GRADE - 3 * 16960)
        self.assertTrue(any("the sector's ceiling is the sky" in row
                            for row in sm.prop_role_faults(disk)))

    def test_a_wall_aligned_sprite_on_a_portal_is_caught(self):
        disk = _street()
        _sprite(disk, tile=641, sector=0, x=8192, y=8192, cstat=16)
        self.assertTrue(any("portal, not a wall" in row
                            for row in sm.prop_role_faults(disk)))

    def test_a_tile_the_owner_has_not_named_goes_on_the_sheet(self):
        # NOT a fault, and not a guess either: 224 tiles are named and this is
        # not one of them, so it is a question for the next sheet.
        disk = _street()
        _sprite(disk, tile=99999, sector=0, x=8192, y=8192)
        found = sm.anchor_role_faults(disk)
        self.assertNotIn(99999, [int(row.split()[3])
                                 for row in found["faults"] if row.split()[3].isdigit()])
        self.assertIn(99999, [row["picnum"] for row in found["unanchored"]])


class W8ASpriteIsWhereItSaysItIs(unittest.TestCase):

    def test_a_sprite_naming_the_wrong_sector_is_caught(self):
        disk = _street()
        _sprite(disk, tile=536, sector=0, x=100000, y=100000)
        faults = sm.sprite_home_faults(disk)
        self.assertEqual(len(faults), 1)
        self.assertIn("is in no sector at all", faults[0])

    def test_a_sprite_in_its_own_sector_is_silent(self):
        disk = _street()
        _sprite(disk, tile=536, sector=0, x=8192, y=8192)
        self.assertEqual(sm.sprite_home_faults(disk), [])


class W9AWallTileOnAFloor(unittest.TestCase):
    """The role comes from the anchors. The first version of this gate carried
    its own list of wall tiles and passed 379 on three roofs and 2490 on
    twenty-three sea floors, because neither was in it."""

    def test_the_facade_s_window_on_a_floor_is_caught(self):
        faults = sm.horizontal_tile_faults(_street(floor_picnum=401))
        self.assertTrue(any("401 as a floor" in row for row in faults))
        self.assertTrue(any("names it a wall" in row for row in faults))

    def test_a_surface_anchor_on_a_floor_is_silent(self):
        self.assertEqual(
            sm.horizontal_tile_faults(_street(floor_picnum=city.INTERIOR_FLOOR)),
            [])

    def test_an_acknowledged_conflict_is_reported_and_is_not_a_fault(self):
        # 379 is a `wall` to the owner and a floor to E3M1's three end walls.
        # A conflict the project has taken to the owner is on the sheet; an
        # unacknowledged one fails.
        disk = _street(floor_picnum=379)
        self.assertTrue(sm.horizontal_tile_faults(disk))
        found = sm.anchor_role_faults(disk, acknowledged=[("floor", 379)])
        self.assertEqual([row for row in found["faults"]
                          if " as a floor;" in row], [])
        self.assertEqual([row["picnum"] for row in found["acknowledged"]],
                         [379])


class W10AMaskHasAPartner(unittest.TestCase):

    def _pair(self, *, both: bool):
        layout = PlanarLayout(name="mask-fixture")
        for index, y0 in enumerate((0, 8192)):
            layout.add_region(f"room{index}",
                              [(0, y0), (8192, y0), (8192, y0 + 8192),
                               (0, y0 + 8192)],
                              floor_z=GRADE, ceiling_z=GRADE - 3 * 16960,
                              floor_picnum=304, ceiling_picnum=454,
                              wall_picnum=401, role="interior")
        layout.add_connection("between", "room0", "room1", role="portal",
                              a1=(0, 8192), a2=(8192, 8192))
        layout.set_player_start("room0", x=4096, y=4096, z=GRADE, angle=0)
        disk = layout.compile().level.to_disk_map()
        marked = 0
        for wall in disk.walls:
            if int(wall.fields["next_sector"]) < 0:
                continue
            if marked and not both:
                break
            wall.fields["cstat"] = int(wall.fields["cstat"]) | 16
            wall.fields["over_picnum"] = 146
            marked += 1
        return disk

    def test_a_mask_on_one_side_only_is_caught(self):
        faults = sm.mask_partner_faults(self._pair(both=False))
        self.assertTrue(faults)
        self.assertIn("is not", faults[0])

    def test_a_mask_on_both_is_silent(self):
        self.assertEqual(sm.mask_partner_faults(self._pair(both=True)), [])


class W11AFacadeTakesTheField(unittest.TestCase):
    """Over the campaign's 5320 one-sided outdoor records the median delta
    from the floor shade of the piece they stand on is +6 -- the same offset
    the kerb census gave, which makes it one law and not two."""

    def test_a_facade_left_at_its_own_shade_is_caught(self):
        disk = _street()
        for wall in disk.walls:
            wall.fields["shade"] = 9
        faults = sm.facade_shade_faults(disk)
        self.assertTrue(faults)
        self.assertIn("reads 9, not 38", faults[0])

    def test_the_measured_relation_is_silent(self):
        disk = _street()
        for wall in disk.walls:
            wall.fields["shade"] = 32 + sm.FACADE_SHADE_OFFSET
        self.assertEqual(sm.facade_shade_faults(disk), [])

    def test_it_is_the_same_offset_the_kerb_takes(self):
        self.assertEqual(sm.FACADE_SHADE_OFFSET, joins.KERB_SHADE_OFFSET)


class W12ARealCeilingBesideTheSky(unittest.TestCase):
    """`engine.cpp:4688`: an upper wall raises `umost` to the far ceiling line
    only when one of the two ceilings is not parallaxed. Sky against sky never
    clips; a roof-height slab beside the street cuts off everything behind."""

    def _pair(self, *, clear):
        layout = PlanarLayout(name="sky-fixture")
        layout.add_region("street", [(0, 0), (16384, 0), (16384, 8192),
                                     (0, 8192)],
                          floor_z=GRADE, ceiling_z=GRADE - 6 * 32768,
                          floor_picnum=4, ceiling_picnum=SKY,
                          wall_picnum=401, parallax_ceiling=True,
                          role="street")
        layout.add_region("under", [(0, 8192), (16384, 8192),
                                    (16384, 12288), (0, 12288)],
                          floor_z=GRADE, ceiling_z=GRADE - clear,
                          floor_picnum=4, ceiling_picnum=454,
                          wall_picnum=401, role="doorway")
        layout.add_connection("mouth", "street", "under", role="portal",
                              a1=(0, 8192), a2=(16384, 8192))
        layout.set_player_start("street", x=8192, y=4096, z=GRADE, angle=0)
        return layout.compile().level.to_disk_map()

    def test_a_roof_height_slab_beside_the_sky_is_caught(self):
        faults = sm.sky_clip_faults(self._pair(clear=4 * 16960),
                                    lintel_height=city.DOOR_TRAVEL)
        self.assertTrue(faults)
        self.assertIn("clips everything above its line", faults[0])

    def test_a_lintel_at_its_declared_height_is_silent(self):
        self.assertEqual(
            sm.sky_clip_faults(self._pair(clear=city.DOOR_TRAVEL),
                               lintel_height=city.DOOR_TRAVEL), [])

    def test_sky_against_sky_never_clips_whatever_the_step(self):
        # E3M1 has 13 differing sky|sky pairs and no visible cut.
        layout = PlanarLayout(name="sky-sky")
        for index, y0 in enumerate((0, 8192)):
            layout.add_region(f"piece{index}",
                              [(0, y0), (16384, y0), (16384, y0 + 8192),
                               (0, y0 + 8192)],
                              floor_z=GRADE,
                              ceiling_z=GRADE - (6 if index else 4) * 32768,
                              floor_picnum=4, ceiling_picnum=SKY,
                              wall_picnum=401, parallax_ceiling=True,
                              role="street")
        layout.add_connection("seam", "piece0", "piece1", role="portal",
                              a1=(0, 8192), a2=(16384, 8192))
        layout.set_player_start("piece0", x=8192, y=4096, z=GRADE, angle=0)
        disk = layout.compile().level.to_disk_map()
        self.assertEqual(sm.sky_clip_faults(disk), [])


class TheShadowFitsTheBuilding(unittest.TestCase):

    def test_a_mass_casting_from_nowhere_is_caught(self):
        from bloodmap.light_field import Mass

        disk = _street()
        away = Mass("mass:elsewhere", ((-9999, -9999), (-9998, -9999),
                                       (-9998, -9998), (-9999, -9998)), 67840)
        faults = sm.shadow_fits_faults(disk, [away])
        self.assertEqual(len(faults), 4)
        self.assertIn("does not start at the building", faults[0])

    def test_a_mass_on_the_map_s_own_vertices_is_silent(self):
        from bloodmap.light_field import Mass

        disk = _street()
        here = Mass("mass:here", ((0, 0), (16384, 0), (16384, 16384),
                                  (0, 16384)), 67840)
        self.assertEqual(sm.shadow_fits_faults(disk, [here]), [])


if __name__ == "__main__":
    unittest.main()
