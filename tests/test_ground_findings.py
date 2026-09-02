"""The owner's four findings from the walk of 2026-09-02, as readers.

Each is a rule the corpus states and the built city broke, so each gate is
written to fail on the map as it was and to read an absolute value off the
map as it is. They run on originals too: that is the reader side, and a
non-empty answer on a campaign map is a finding about that map.
"""

from __future__ import annotations

import unittest

from bloodmap.planar_layout import PlanarLayout
from bloodmap.street_model import (
    kerb_tile_faults, lamp_faults, sky_faults, step_shade_faults)

SKY = 3491
OTHER_SKY = 3678
ROAD, PAVE, KERB = 352, 4, 6


def _street(*, kerb_everywhere: bool, kerb_shade: int, sky_b: int = SKY):
    """A road cut in two by a shadow, with a pavement beside it.

    `kerb_everywhere` puts the kerb tile on the road|road cut as well, which
    is what a surface whose default material IS the kerb tile produces.
    """
    layout = PlanarLayout(name="findings-fixture")
    for name, x0, x1, shade in (("road_lit", 0, 8192, 8),
                                ("road_dark", 8192, 16384, 32)):
        layout.add_region(name, [(x0, 0), (x1, 0), (x1, 4096), (x0, 4096)],
                          floor_z=10240, ceiling_z=10240 - 6 * 32768,
                          floor_picnum=ROAD, ceiling_picnum=SKY,
                          wall_picnum=KERB if kerb_everywhere else 400,
                          floor_shade=shade, parallax_ceiling=True,
                          role="street")
    layout.add_region("island", [(0, 4096), (16384, 4096), (16384, 12288),
                                 (0, 12288)],
                      floor_z=8192, ceiling_z=8192 - 6 * 32768,
                      floor_picnum=PAVE, ceiling_picnum=sky_b,
                      wall_picnum=401, floor_shade=8, parallax_ceiling=True,
                      role="street")
    layout.add_connection("cut", "road_lit", "road_dark", role="portal",
                          a1=(8192, 0), a2=(8192, 4096))
    layout.add_connection("kerb_a", "road_lit", "island", role="portal",
                          a1=(0, 4096), a2=(8192, 4096))
    layout.add_connection("kerb_b", "road_dark", "island", role="portal",
                          a1=(8192, 4096), a2=(16384, 4096))
    layout.set_player_start("road_lit", x=2048, y=2048, z=10240, angle=0)
    disk = layout.compile().level.to_disk_map()
    from bloodmap.texture_frame import sector_index

    owners = sector_index(disk)
    for wall_id, wall in enumerate(disk.walls):
        there = int(wall.fields["next_sector"])
        if there < 0:
            continue
        here = owners[wall_id]
        pair = {int(disk.sectors[here].fields["floor_picnum"]),
                int(disk.sectors[there].fields["floor_picnum"])}
        if pair == {ROAD, PAVE} and \
                int(disk.sectors[here].fields["floor_picnum"]) == ROAD:
            wall.fields["picnum"] = KERB
            wall.fields["shade"] = kerb_shade
    return disk


class W1AKerbIsOnlyWhereRoadMeetsPavement(unittest.TestCase):
    """E3M1 says it twice: its eleven tile-6 records all step road->pavement,
    and its road|road records wear the facade family instead."""

    def test_the_kerb_tile_as_a_default_material_is_a_fault(self):
        # THE FAIL-FIRST: the built city had 111 of these, on shadow cuts, on
        # map edges and on the faces of its end walls.
        faults = kerb_tile_faults(_street(kerb_everywhere=True, kerb_shade=14))
        self.assertTrue(faults)
        self.assertIn("not road|pavement", faults[0])

    def test_a_kerb_only_where_the_road_steps_up_is_silent(self):
        self.assertEqual(
            kerb_tile_faults(_street(kerb_everywhere=False, kerb_shade=14)), [])


class W2AStepFaceFollowsTheField(unittest.TestCase):
    """E3M1's eleven kerb records, measured: the six standing on road at floor
    shade 32 read a median 38, the five on road at 8 read 8. Median delta +6.
    """

    def test_a_face_left_at_the_base_while_its_floor_darkens_is_a_fault(self):
        disk = _street(kerb_everywhere=False, kerb_shade=14)
        faults = step_shade_faults(disk)
        # the lit road's kerb is right at 8 + 6; the shadowed one is not
        self.assertEqual(len(faults), 1)
        self.assertIn("reads 14, not 38", faults[0])

    def test_the_absolute_reading_is_e3m1_s_own(self):
        # A kerb standing on a floor at shade 32 -- one depth-2 piece of the
        # city -- reads 38, which is exactly what E3M1's shadowed kerbs read.
        from bloodmap.joins import KERB_SHADE_OFFSET

        self.assertEqual(32 + KERB_SHADE_OFFSET, 38)

    def test_both_kerbs_following_their_floors_is_silent(self):
        disk = _street(kerb_everywhere=False, kerb_shade=14)
        from bloodmap.texture_frame import sector_index

        owners = sector_index(disk)
        for wall_id, wall in enumerate(disk.walls):
            if int(wall.fields["picnum"]) != KERB:
                continue
            wall.fields["shade"] = int(
                disk.sectors[owners[wall_id]].fields["floor_shade"]) + 6
        self.assertEqual(step_shade_faults(disk), [])


class W3ALampHangsFromSomething(unittest.TestCase):
    """641 is a ceiling lantern on a chain. Under an open sky it hangs from
    nothing."""

    @staticmethod
    def _with_sprite(disk, *, cstat, x, y, sector):
        from bloodmap.format import SPRITE_FIELDS
        from bloodmap.model import DiskObject

        fields = {name: 0 for name, _code in SPRITE_FIELDS}
        fields.update({"x": x, "y": y, "z": 0, "sector": sector,
                       "picnum": 641, "shade": -128, "cstat": cstat,
                       "x_repeat": 64, "y_repeat": 64, "owner": -1,
                       "extra": -1})
        disk.sprites.append(DiskObject(fields=fields))
        return disk

    def test_a_lantern_under_the_sky_is_a_fault_by_sprite_index(self):
        disk = self._with_sprite(_street(kerb_everywhere=False, kerb_shade=14),
                                 cstat=128, x=4096, y=2048, sector=0)
        faults = lamp_faults(disk)
        self.assertEqual(len(faults), 1)
        self.assertIn("hangs under an open sky", faults[0])

    def test_wall_aligned_but_on_no_wall_is_still_a_fault(self):
        disk = self._with_sprite(_street(kerb_everywhere=False, kerb_shade=14),
                                 cstat=208, x=4096, y=2048, sector=0)
        faults = lamp_faults(disk)
        self.assertEqual(len(faults), 1)
        self.assertIn("stands on no wall", faults[0])

    def test_wall_aligned_and_on_a_wall_is_silent(self):
        disk = self._with_sprite(_street(kerb_everywhere=False, kerb_shade=14),
                                 cstat=208, x=4096, y=0, sector=0)
        self.assertEqual(lamp_faults(disk), [])


class W4OneOutdoorSpaceWearsOneSky(unittest.TestCase):
    """271 of 271 connected outdoor regions in the campaign carry exactly one
    sky picnum, at every size, with no exception."""

    def test_two_skies_side_by_side_is_a_fault(self):
        faults = sky_faults(_street(kerb_everywhere=False, kerb_shade=14,
                                    sky_b=OTHER_SKY))
        self.assertEqual(len(faults), 1)
        self.assertIn("wears 2 skies", faults[0])
        self.assertIn("271 of 271", faults[0])

    def test_one_sky_is_silent(self):
        self.assertEqual(
            sky_faults(_street(kerb_everywhere=False, kerb_shade=14)), [])

    def test_the_campaign_itself_passes_its_own_law(self):
        # The reader side, on originals: E3M1 has one sky over its streets.
        from bloodmap.patterns import corpus_map_path, read_map

        try:
            disk = read_map(corpus_map_path("E3M1"))
        except Exception:  # pragma: no cover - corpus absent
            self.skipTest("corpus not present")
        self.assertEqual(sky_faults(disk), [])


if __name__ == "__main__":
    unittest.main()
