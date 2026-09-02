"""Rule 2, with a denominator: an overlay may not cut a mechanism.

Slice 2i's manifest said the light domain refused 0, and nothing in that map
was a mechanism, so the rule had never been asked. With nine curtains standing
in the city's shells it has a population at last, and this is the gate it was
written for: a mechanism's `DragPoint` closure must be exactly what it was
before any overlay ran.

The fail-first lays a shadow over a curtain -- literally cuts the sector the
mechanism lives in -- and reads the closure change off the built map.
"""

from __future__ import annotations

import unittest

from bloodmap.overlay import (
    LIGHT_DOMAIN, refusal_denominator, region_facts)
from bloodmap.planar_layout import PlanarLayout

SKY = 3491
CURTAIN_TYPE = 614
#: cstat 0x4000 / 0x8000: the bits that say a wall is dragged.
DRAG_FORWARD, DRAG_BACK = 0x4000, 0x8000


def _curtain(*, cut: bool):
    """A curtain in a doorway, optionally cut in two by a shadow."""
    layout = PlanarLayout(name="rule-two-fixture")
    layout.add_region("room", [(0, 0), (8192, 0), (8192, 4096), (0, 4096)],
                      floor_z=8192, ceiling_z=8192 - 3 * 16960,
                      floor_picnum=4, ceiling_picnum=379, wall_picnum=401,
                      role="interior")
    if cut:
        #: THE SHADOW, laid over the mechanism. Two sectors where the
        #: mechanism declared one.
        layout.add_region("door_a", [(2048, 4096), (4096, 4096),
                                     (4096, 5120), (2048, 5120)],
                          floor_z=8192, ceiling_z=8192 - 2 * 16960,
                          floor_picnum=4, ceiling_picnum=379,
                          wall_picnum=401, type=CURTAIN_TYPE, role="opening")
        layout.add_region("door_b", [(4096, 4096), (6144, 4096),
                                     (6144, 5120), (4096, 5120)],
                          floor_z=8192, ceiling_z=8192 - 2 * 16960,
                          floor_picnum=4, ceiling_picnum=379,
                          wall_picnum=401, type=CURTAIN_TYPE, role="opening")
        layout.add_connection("shadow", "door_a", "door_b", role="portal",
                              a1=(4096, 4096), a2=(4096, 5120))
        layout.add_connection("mouth_a", "room", "door_a", role="portal",
                              a1=(2048, 4096), a2=(4096, 4096))
        layout.add_connection("mouth_b", "room", "door_b", role="portal",
                              a1=(4096, 4096), a2=(6144, 4096))
    else:
        layout.add_region("door", [(2048, 4096), (6144, 4096),
                                   (6144, 5120), (2048, 5120)],
                          floor_z=8192, ceiling_z=8192 - 2 * 16960,
                          floor_picnum=4, ceiling_picnum=379,
                          wall_picnum=401, type=CURTAIN_TYPE, role="opening")
        layout.add_connection("mouth", "room", "door", role="portal",
                              a1=(2048, 4096), a2=(6144, 4096))
    layout.set_player_start("room", x=4096, y=2048, z=8192, angle=0)
    disk = layout.compile().level.to_disk_map()
    #: flag the mechanism's own walls as dragged, as a curtain's are
    for sector in disk.sectors:
        if int(sector.fields["type"]) != CURTAIN_TYPE:
            continue
        start = int(sector.fields["wall_ptr"])
        for wall_id in range(start, start + int(sector.fields["wall_count"])):
            disk.walls[wall_id].fields["cstat"] = (
                int(disk.walls[wall_id].fields["cstat"]) | DRAG_FORWARD)
    return disk


def _closures(disk):
    from bloodmap.motion import drag_closure

    out = {}
    for index, sector in enumerate(disk.sectors):
        if int(sector.fields["type"]) != CURTAIN_TYPE:
            continue
        found = drag_closure(disk, index)
        out[index] = sorted((int(disk.walls[w].fields["x"]),
                             int(disk.walls[w].fields["y"]))
                            for w in found["walls"])
    return out


class AnOverlayMayNotCutAMechanism(unittest.TestCase):

    def test_a_mechanism_is_eligible_for_refusal_and_a_road_is_not(self):
        disk = _curtain(cut=False)
        result = refusal_denominator(disk, LIGHT_DOMAIN,
                                     range(len(disk.sectors)))
        self.assertEqual(result["eligible"], 1)
        self.assertEqual(result["verdict"], "tested")

    def test_the_domain_names_the_sector_type_as_the_reason(self):
        disk = _curtain(cut=False)
        for index, sector in enumerate(disk.sectors):
            if int(sector.fields["type"]) != CURTAIN_TYPE:
                continue
            ok, why = LIGHT_DOMAIN.admits(str(index),
                                          region_facts(disk, index))
            self.assertFalse(ok)
            self.assertIn("mechanism", why)

    def test_laying_a_shadow_over_a_curtain_changes_its_closure(self):
        # THE FAIL-FIRST, read off the built map: one curtain with a closure
        # of N becomes two, and neither has the closure the sentence declared.
        whole = _closures(_curtain(cut=False))
        halves = _closures(_curtain(cut=True))
        self.assertEqual(len(whole), 1)
        self.assertEqual(len(halves), 2)
        only = next(iter(whole.values()))
        self.assertTrue(all(sorted(part) != sorted(only)
                            for part in halves.values()),
                        "a cut mechanism must not report the closure it had")

    def test_an_uncut_curtain_keeps_the_closure_it_had(self):
        self.assertEqual(_closures(_curtain(cut=False)),
                         _closures(_curtain(cut=False)))


class AMechanismDeformsWhatItSaysItDeforms(unittest.TestCase):
    """A Z-motion door moves a PLANE. Nothing in the map travels.

    Slice 4 flagged its mouth 0x4000 -- the bit that says a wall is dragged --
    on a mechanism that drags nothing, and `DragPoint` believed it: the walk
    left the door through the vertex the weld made it share with the pavement
    and reported six walls in three sectors. That was the read-back's one
    remaining difference, and the weld was not its cause.
    """

    Z_MOTION = 600

    @staticmethod
    def _shutter(*, flag_the_leaf: bool):
        from bloodmap.doors import z_motion_door
        from bloodmap.planar_layout import PlanarLayout

        layout = PlanarLayout(name="payload-fixture")
        layout.add_region("street", [(0, 0), (16384, 0), (16384, 4096),
                                     (0, 4096)],
                          floor_z=8192, ceiling_z=8192 - 6 * 32768,
                          floor_picnum=4, ceiling_picnum=SKY, wall_picnum=401,
                          parallax_ceiling=True, role="street")
        layout.add_region("door", [(6144, 4096), (10240, 4096),
                                   (10240, 5120), (6144, 5120)],
                          #: built OPEN, as the city builds one: the shut
                          #: state is the XSECTOR's off_ceiling_z, not the
                          #: height the sector is written at.
                          floor_z=8192, ceiling_z=8192 - 2 * 16960,
                          floor_picnum=4, ceiling_picnum=379,
                          wall_picnum=401, role="opening",
                          type=AMechanismDeformsWhatItSaysItDeforms.Z_MOTION,
                          sector_behavior=z_motion_door(
                              8192, 8192 - 2 * 16960, interaction="direct"))
        layout.add_region("room", [(4096, 5120), (12288, 5120),
                                   (12288, 12288), (4096, 12288)],
                          floor_z=8192, ceiling_z=8192 - 3 * 16960,
                          floor_picnum=4, ceiling_picnum=379,
                          wall_picnum=401, role="interior")
        layout.add_connection("mouth", "street", "door", role="portal",
                              a1=(6144, 4096), a2=(10240, 4096))
        layout.add_connection("inner", "door", "room", role="portal",
                              a1=(6144, 5120), a2=(10240, 5120))
        layout.set_player_start("street", x=2048, y=2048, z=8192, angle=0)
        disk = layout.compile().level.to_disk_map()
        if flag_the_leaf:
            for index, sector in enumerate(disk.sectors):
                if int(sector.fields["type"]) != 600:
                    continue
                start = int(sector.fields["wall_ptr"])
                disk.walls[start].fields["cstat"] = (
                    int(disk.walls[start].fields["cstat"]) | DRAG_FORWARD)
        return disk

    def _closure(self, disk):
        from bloodmap.motion import drag_closure

        for index, sector in enumerate(disk.sectors):
            if int(sector.fields["type"]) == self.Z_MOTION:
                return drag_closure(disk, index)
        raise AssertionError("no Z-motion sector in the fixture")

    def test_a_flagged_leaf_makes_a_shutter_drag_its_neighbours(self):
        # THE FAIL-FIRST, and the absolute reading is that the walk LEAVES the
        # mechanism: more than one sector comes back.
        found = self._closure(self._shutter(flag_the_leaf=True))
        self.assertTrue(found["walls"])
        self.assertGreater(len(found["sectors"]), 1)

    def test_an_unflagged_shutter_deforms_nothing(self):
        found = self._closure(self._shutter(flag_the_leaf=False))
        self.assertEqual(found["walls"], [])

    def test_the_constructor_does_not_flag_a_z_motion_leaf(self):
        from bloodmap import city

        self.assertFalse(city._leaf_for(city.Z_MOTION)["flags"]
                         & city.DRAG_FORWARD)
        self.assertTrue(city._leaf_for(city.Z_MOTION)["flags"] & city.MASKED)

    def test_it_still_flags_one_that_does_slide(self):
        from bloodmap import city

        self.assertTrue(city._leaf_for(614)["flags"] & city.DRAG_FORWARD)


if __name__ == "__main__":
    unittest.main()
