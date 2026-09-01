"""The rendering law: which tile the engine draws on which band of a wall.

Hand-built minimal maps, one per case the engine's wall pass distinguishes,
so a change to `bloodmap.render_slots` that stops agreeing with
`engine.cpp:4685-4940` and `:7217-7231` fails here by name. The corpus
fixtures at the end are the two curtains the reader was written against.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from bloodmap.format import SECTOR_FIELDS, SPRITE_FIELDS, WALL_FIELDS
from bloodmap.model import DiskMap, DiskObject
from bloodmap.render_slots import (
    CSTAT_MASKED, CSTAT_ONE_WAY, CSTAT_SWAP_BOTTOM, MASKED_MIDDLE,
    MIRROR_TILE, ONE_SIDED_MIDDLE, ONEWAY_MIDDLE, TWO_SIDED_LOWER,
    TWO_SIDED_UPPER, bands_showing_picnum, bands_sourced_from,
    draws_in_walkable_band, draws_on_a_step, render_slots, surface_z,
    undrawn_walls,
)

ROOT = Path(__file__).resolve().parents[1]

CEILING = -16384          # one standing body, roughly
FLOOR = 0


def _record(fields, **values):
    record = {name: 0 for name, _ in fields}
    record.update(values)
    return DiskObject(fields=record)


def _map(sectors, walls):
    return DiskMap(version=7, header={}, extra_header=None, sky_offsets=[],
                   sectors=sectors, walls=walls, sprites=[],
                   source_crc32=0, source_size=0)


def _box(points, wall_ptr, picnum, **sector):
    """A rectangular sector's walls, one-sided, and its sector record."""
    walls = []
    count = len(points)
    for i, (x, y) in enumerate(points):
        walls.append(_record(WALL_FIELDS, x=x, y=y,
                             point2=wall_ptr + (i + 1) % count,
                             next_wall=-1, next_sector=-1, picnum=picnum,
                             x_repeat=8, y_repeat=8))
    values = dict(wall_ptr=wall_ptr, wall_count=count,
                  ceiling_z=CEILING, floor_z=FLOOR)
    values.update(sector)
    record = _record(SECTOR_FIELDS, **values)
    return record, walls


def _pair(left_picnum=10, right_picnum=20, *, left=None, right=None,
          shared_cstat=0, shared_over=0, right_shared_cstat=None):
    """Two boxes sharing the wall x=1024: left wall 1, right wall 7.

    Left box (sector 0) is (0,0)-(1024,1024), right (sector 1) is
    (1024,0)-(2048,1024). The shared wall is left's wall 1 (1024,0)->(1024,
    1024) and right's wall 7 (1024,1024)->(1024,0).
    """
    s0, w0 = _box([(0, 0), (1024, 0), (1024, 1024), (0, 1024)], 0,
                  left_picnum, **(left or {}))
    s1, w1 = _box([(1024, 0), (2048, 0), (2048, 1024), (1024, 1024)], 4,
                  right_picnum, **(right or {}))
    w0[1].fields.update(next_wall=7, next_sector=1, cstat=shared_cstat,
                        over_picnum=shared_over)
    w1[3].fields.update(next_wall=1, next_sector=0,
                        cstat=(shared_cstat if right_shared_cstat is None
                               else right_shared_cstat),
                        over_picnum=shared_over)
    return _map([s0, s1], w0 + w1)


def _bands(disk, wall):
    return [(b.band, b.tile) for b in render_slots(disk)[wall].bands]


class OneSidedTest(unittest.TestCase):
    def test_a_white_wall_draws_picnum_ceiling_to_floor(self):
        s, w = _box([(0, 0), (1024, 0), (1024, 1024), (0, 1024)], 0, 77)
        disk = _map([s], w)
        for index in range(4):
            self.assertEqual(_bands(disk, index), [(ONE_SIDED_MIDDLE, 77)])
        band = render_slots(disk)[0].bands[0]
        self.assertEqual(band.top, (CEILING, CEILING))
        self.assertEqual(band.bottom, (FLOOR, FLOOR))
        self.assertEqual(band.height, FLOOR - CEILING)

    def test_a_zero_height_sector_draws_nothing(self):
        s, w = _box([(0, 0), (1024, 0), (1024, 1024), (0, 1024)], 0, 77,
                    ceiling_z=0, floor_z=0)
        disk = _map([s], w)
        self.assertEqual(_bands(disk, 0), [])
        self.assertIn("zero-height", render_slots(disk)[0].skipped[0])


class TwoSidedTest(unittest.TestCase):
    def test_a_flush_red_wall_draws_nothing_from_either_side(self):
        # Same ceiling, same floor, not masked: engine.cpp:4690 and :4801
        # skip both steps and :4685/:4938 never read the middle.
        disk = _pair()
        self.assertEqual(_bands(disk, 1), [])
        self.assertEqual(_bands(disk, 7), [])
        found = render_slots(disk)
        self.assertEqual(bands_showing_picnum(found, 1), [])
        self.assertEqual(bands_sourced_from(found, 1), [])

    def test_a_ceiling_step_draws_picnum_on_the_higher_side_only(self):
        # The right room's ceiling is lower: from the LEFT the neighbour's
        # ceiling is lower, so the left wall draws its picnum on the upper
        # step (engine.cpp:4720); from the right nothing steps.
        disk = _pair(left={"ceiling_z": -32768})
        self.assertEqual(_bands(disk, 1), [(TWO_SIDED_UPPER, 10)])
        self.assertEqual(_bands(disk, 7), [])
        band = render_slots(disk)[1].bands[0]
        self.assertEqual((band.top, band.bottom),
                         ((-32768, -32768), (CEILING, CEILING)))

    def test_a_floor_step_draws_picnum_on_the_lower_side_only(self):
        # The right room's floor is higher: from the left the neighbour's
        # floor is higher, so the left wall draws its lower step.
        disk = _pair(right={"floor_z": -4096})
        self.assertEqual(_bands(disk, 1), [(TWO_SIDED_LOWER, 10)])
        self.assertEqual(_bands(disk, 7), [])

    def test_cstat_2_swaps_the_partners_picnum_onto_the_lower_step(self):
        # engine.cpp:4832-4833: the lower step reads wall[nextwall].picnum.
        disk = _pair(right={"floor_z": -4096}, shared_cstat=CSTAT_SWAP_BOTTOM,
                     right_shared_cstat=0)
        found = render_slots(disk)
        self.assertEqual(_bands(disk, 1), [(TWO_SIDED_LOWER, 20)])
        self.assertEqual(found[1].bands[0].source_wall, 7)
        # The partner's picnum is what is on screen; it is sourced from the
        # partner even though the left wall's own field is 10.
        self.assertEqual([b.tile for b in bands_sourced_from(found, 7)], [20])
        self.assertEqual(bands_sourced_from(found, 1), [])
        self.assertFalse(found[1].draws_picnum)

    def test_both_steps_when_the_neighbour_is_a_shallower_room(self):
        disk = _pair(left={"ceiling_z": -32768, "floor_z": 8192})
        self.assertEqual(_bands(disk, 1),
                         [(TWO_SIDED_UPPER, 10), (TWO_SIDED_LOWER, 10)])

    def test_a_step_at_one_end_only_still_draws(self):
        # engine.cpp:4690 skips only when BOTH ends fail to step: a sloped
        # neighbour whose ceiling dips below ours at one end draws the step.
        disk = _pair(right={"ceiling_stat": 2, "ceiling_heinum": 4096})
        found = render_slots(disk)
        self.assertTrue(found[1].sloped)
        self.assertEqual(_bands(disk, 1), [(TWO_SIDED_UPPER, 10)])

    def test_both_ceilings_parallaxed_skip_the_upper_step(self):
        # engine.cpp:4688 -- the sky is drawn instead, whatever the heights.
        disk = _pair(left={"ceiling_z": -32768, "ceiling_stat": 1},
                     right={"ceiling_stat": 1})
        self.assertEqual(_bands(disk, 1), [])
        self.assertIn("parallaxed", render_slots(disk)[1].skipped[0])

    def test_one_parallaxed_ceiling_still_steps(self):
        disk = _pair(left={"ceiling_z": -32768, "ceiling_stat": 1})
        self.assertEqual(_bands(disk, 1), [(TWO_SIDED_UPPER, 10)])


class MaskedAndOneWayTest(unittest.TestCase):
    def test_a_masked_wall_draws_over_picnum_in_the_middle(self):
        disk = _pair(shared_cstat=CSTAT_MASKED, shared_over=502)
        found = render_slots(disk)
        self.assertEqual(_bands(disk, 1), [(MASKED_MIDDLE, 502)])
        self.assertEqual(_bands(disk, 7), [(MASKED_MIDDLE, 502)])
        band = found[1].bands[0]
        self.assertEqual(band.field, "over_picnum")
        # engine.cpp:7217-7218: lower ceiling to higher floor.
        self.assertEqual((band.top, band.bottom),
                         ((CEILING, CEILING), (FLOOR, FLOOR)))
        # The picnum is still authored and still on screen nowhere.
        self.assertEqual(bands_showing_picnum(found, 1), [])

    def test_the_masked_middle_is_the_opening_not_the_wall(self):
        # A doorway with a lower ceiling and a raised floor: the mask spans
        # the opening between the steps.
        disk = _pair(left={"ceiling_z": -32768, "floor_z": 8192},
                     shared_cstat=CSTAT_MASKED, shared_over=502)
        bands = {b.band: b for b in render_slots(disk)[1].bands}
        self.assertEqual(set(bands), {TWO_SIDED_UPPER, TWO_SIDED_LOWER,
                                      MASKED_MIDDLE})
        self.assertEqual((bands[MASKED_MIDDLE].top, bands[MASKED_MIDDLE].bottom),
                         ((CEILING, CEILING), (FLOOR, FLOOR)))

    def test_a_closed_opening_draws_no_mask(self):
        # The neighbour's floor meets our ceiling: nothing to mask.
        disk = _pair(right={"floor_z": CEILING, "ceiling_z": CEILING - 4096},
                     shared_cstat=CSTAT_MASKED, shared_over=502)
        self.assertEqual(_bands(disk, 1), [(TWO_SIDED_LOWER, 10)])
        self.assertIn("no height", " ".join(render_slots(disk)[1].skipped))

    def test_a_one_way_wall_draws_over_picnum_opaque(self):
        disk = _pair(shared_cstat=CSTAT_ONE_WAY, shared_over=504,
                     right_shared_cstat=0)
        self.assertEqual(_bands(disk, 1), [(ONEWAY_MIDDLE, 504)])
        self.assertEqual(_bands(disk, 7), [])

    def test_one_way_beats_masked(self):
        # engine.cpp:4685-4686 `(cstat&48) == 16` -- a wall with both bits is
        # drawn as one-way in the solid pass, never deferred as a mask.
        disk = _pair(shared_cstat=CSTAT_ONE_WAY | CSTAT_MASKED, shared_over=502)
        self.assertEqual(_bands(disk, 1), [(ONEWAY_MIDDLE, 502)])


class SlopeTest(unittest.TestCase):
    def test_a_flat_sector_reports_its_own_z(self):
        s, w = _box([(0, 0), (1024, 0), (1024, 1024), (0, 1024)], 0, 1)
        disk = _map([s], w)
        self.assertEqual(surface_z(disk, 0, 512, 512), (CEILING, FLOOR))

    def test_a_slope_rises_away_from_the_first_wall(self):
        # getzsofslopeptr: heinum 4096 is 45 degrees, so at 1024 plan units
        # from the first wall the floor moves by 1024 plan units, which is
        # 16384 in z -- Build's z is 16 times finer than x/y. The sign
        # follows the wall's winding.
        s, w = _box([(0, 0), (1024, 0), (1024, 1024), (0, 1024)], 0, 1,
                    floor_stat=2, floor_heinum=4096)
        disk = _map([s], w)
        self.assertEqual(surface_z(disk, 0, 0, 0)[1], FLOOR)
        far = surface_z(disk, 0, 0, 1024)[1]
        self.assertEqual(abs(far - FLOOR), 1024 * 16)
        # Halfway along, half the rise: the slope is linear in distance.
        self.assertEqual(abs(surface_z(disk, 0, 512, 512)[1] - FLOOR), 512 * 16)


class UndrawnWallsTest(unittest.TestCase):
    def test_fabric_on_a_flush_unmasked_red_wall_is_undrawn(self):
        # The city's stage curtain, reduced: fabric 146 on a two-sided wall
        # whose neighbour's ceiling is HIGHER and whose floors are flush.
        # Nothing steps on the fabric's side; the partner draws the
        # auditorium's own tile on the step above. 146 is on screen nowhere.
        disk = _pair(left_picnum=146, right_picnum=119,
                     right={"ceiling_z": -40960})
        found = undrawn_walls(disk)
        self.assertEqual([f["wall"] for f in found], [1])
        self.assertEqual(found[0]["picnum"], 146)
        self.assertEqual(found[0]["partner_picnum"], 119)
        self.assertEqual(found[0]["pair_draws"], [(TWO_SIDED_UPPER, 119)])

    def test_the_same_fabric_on_the_stepping_side_is_drawn(self):
        disk = _pair(left_picnum=146, right_picnum=119,
                     left={"ceiling_z": -40960})
        found = undrawn_walls(disk)
        self.assertNotIn(1, [f["wall"] for f in found])
        # The partner's 119 is now the undrawn one: the campaign does this
        # on a quarter of its walls, which is why the per-wall rule is a
        # note and the per-map rule is the gate.
        self.assertEqual([(f["wall"], f["picnum"]) for f in found], [(7, 119)])

    def test_the_partner_wearing_the_same_tile_counts_as_shown(self):
        # The pelmet idiom: both sides wear the tile, one side draws it.
        disk = _pair(left_picnum=146, right_picnum=146,
                     right={"ceiling_z": -40960})
        self.assertEqual(undrawn_walls(disk), [])

    def test_sky_mirror_and_blank_are_exempt(self):
        for tile in (2500, 504, 0):
            disk = _pair(left_picnum=tile, right_picnum=tile)
            self.assertEqual(undrawn_walls(disk), [], tile)


class CorpusCurtainsTest(unittest.TestCase):
    """The two curtains the reader was written against."""

    def _campaign(self, stem):
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps

        found = [e for e in list_corpus_maps(population="blood-campaign")
                 if e.path.stem.upper() == stem]
        if not found:
            self.skipTest(f"{stem} is not in the corpus")
        return read_map(found[0].path)

    def test_e1m1_pelmet_is_the_auditoriums_tile_not_the_fabric(self):
        # Walls 1203-1207 (s125, ceiling -10240) face s122 whose ceiling is
        # -75776: from the curtain's side nothing steps, so their 146 is on
        # screen nowhere. The 65536-unit pelmet is drawn by the partners
        # 1102-1106 with THEIR picnum, 109; their over_picnum 146 is never
        # read (cstat 0x6: swap and align, no mask).
        disk = self._campaign("E1M1")
        found = render_slots(disk)
        for wall in range(1203, 1208):
            self.assertEqual(found[wall].picnum, 146)
            self.assertEqual(found[wall].bands, ())
            self.assertEqual(bands_showing_picnum(found, wall), [])
        for wall in range(1102, 1107):
            self.assertEqual([(b.band, b.tile, b.height) for b in found[wall].bands],
                             [(TWO_SIDED_UPPER, 109, 65536)])
            self.assertEqual(found[wall].over_picnum, 146)
            self.assertFalse(found[wall].draws_over_picnum)

    def test_the_pocket_curtain_shows_its_overlay_and_hides_its_picnum(self):
        # DOOR-CURTAINSD s4: the pocket-side walls are masked (0x51) with
        # over_picnum 1060, so 1060 draws in the middle band, full height;
        # the 146 on their picnum is never on screen.
        from bloodmap.format import read_map
        from bloodmap.patterns import corpus_root

        path = corpus_root() / "mechanism" / "Vanilla" / "DOOR-CURTAINSD.map"
        if not path.exists():
            self.skipTest("DOOR-CURTAINSD is not in the corpus")
        found = render_slots(read_map(path))
        for wall in (28, 32, 37, 41):
            self.assertEqual([(b.band, b.tile, b.height) for b in found[wall].bands],
                             [(MASKED_MIDDLE, 1060, 24576)])
            self.assertEqual(found[wall].picnum, 146)
            self.assertEqual(bands_showing_picnum(found, wall), [])


class WalkableBandTest(unittest.TestCase):
    """The relation `conformance.fabric_is_visible` asks, owned here.

    One reader for the rendering law: conformance used to decide it from the
    cstat bits alone, which cannot see a masked wall between two sectors that
    leave no opening, nor a white wall in a sector with no height.
    """

    def test_a_white_wall_is_walkable_and_is_not_a_step(self):
        s, w = _box([(0, 0), (1024, 0), (1024, 1024), (0, 1024)], 0, 146)
        disk = _map([s], w)
        self.assertTrue(draws_in_walkable_band(disk, 0))
        self.assertFalse(draws_on_a_step(disk, 0))

    def test_a_flush_unmasked_red_wall_is_not_walkable(self):
        disk = _pair(left_picnum=146)
        self.assertFalse(draws_in_walkable_band(disk, 1))

    def test_a_masked_wall_is_walkable_and_a_one_way_one_too(self):
        for cstat in (CSTAT_MASKED, CSTAT_ONE_WAY):
            disk = _pair(shared_cstat=cstat, shared_over=146)
            self.assertTrue(draws_in_walkable_band(disk, 1), cstat)

    def test_a_masked_wall_across_no_opening_is_not_walkable(self):
        # The case a cstat test cannot see: the neighbour's floor is at our
        # ceiling, so `z2 - z1` is zero and renderDrawMaskedWall has nothing
        # to scan (engine.cpp:7217-7218).
        disk = _pair(right={"floor_z": CEILING, "ceiling_z": CEILING - 4096},
                     shared_cstat=CSTAT_MASKED, shared_over=146)
        self.assertFalse(draws_in_walkable_band(disk, 1))

    def test_a_step_is_a_step_on_one_side_and_a_portal_step_on_both(self):
        # E1M1 s125 in miniature: the step exists, and the side that draws
        # it is the one whose own ceiling is the lower.
        disk = _pair(left={"ceiling_z": -32768})
        self.assertTrue(draws_on_a_step(disk, 1))
        self.assertFalse(draws_on_a_step(disk, 7))
        self.assertTrue(draws_on_a_step(disk, 7, either_side=True))
        self.assertFalse(draws_in_walkable_band(disk, 1))


class MirrorTest(unittest.TestCase):
    """mirrors.cpp:466-469 edits the wall before anything is drawn."""

    def test_a_red_mirror_wall_draws_a_one_way_middle(self):
        # The file says cstat 0, no over_picnum; the running level says
        # one-way with over_picnum 504. Without the transform this wall
        # would read as "draws nothing" -- and the campaign has exactly one
        # of them.
        disk = _pair(left_picnum=MIRROR_TILE)
        found = render_slots(disk)
        self.assertEqual(_bands(disk, 1), [(ONEWAY_MIDDLE, MIRROR_TILE)])
        self.assertEqual(found[1].cstat, CSTAT_ONE_WAY)
        self.assertEqual(found[1].over_picnum, MIRROR_TILE)
        self.assertEqual(_bands(disk, 7), [])

    def test_a_white_mirror_wall_still_draws_its_picnum(self):
        # nextsectnum < 0 wins the ternary at :4940 whatever the bit says.
        s, w = _box([(0, 0), (1024, 0), (1024, 1024), (0, 1024)], 0,
                    MIRROR_TILE)
        disk = _map([s], w)
        self.assertEqual(_bands(disk, 0), [(ONE_SIDED_MIDDLE, MIRROR_TILE)])


if __name__ == "__main__":
    unittest.main()
