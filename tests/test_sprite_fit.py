"""A sprite fits where it was put, as the engine draws it.

The owner, walking Gravesend on 2026-11-18: "sometimes you are placing
sprites partially under ground or into space where they don't fit, also
sometimes you are using statues on weird places. Lamps are also placed
little bit weirdly around the town", and then: "On some walls you have
overlapping sprites, usually letters with other sprites, maybe we can have
something like map linting script".

`tools/sprite_fit.py` is that script. Its thresholds are where Blood's own
town maps stop, because Blood sinks and overlaps a few things on purpose.
"""

from __future__ import annotations

import unittest
from pathlib import Path

CITY = Path("projects/blood-city/level/blood-city-current.MAP")
E3M1 = Path("maps/blood/campaign/E3M1.MAP")
DWE3M1 = Path("maps/blood/curated/DWE3M1.MAP")


class DrawnExtentTests(unittest.TestCase):
    def test_bit_128_draws_a_sprite_about_its_z(self):
        from bloodmap.placement import drawn_extent

        #: 48 texels at repeat 40: 7,680 tall
        self.assertEqual(drawn_extent(48, 0, 40, 128, 0), (-3840, 3840))

    def test_without_it_the_sprite_stands_on_its_z(self):
        from bloodmap.placement import drawn_extent

        self.assertEqual(drawn_extent(48, 0, 40, 0, 0), (-7680, 0))

    def test_the_tiles_own_offset_moves_it(self):
        from bloodmap.placement import drawn_extent, drawn_lift

        #: tile 536, the statue: 110 texels with a y offset of 55 -- its art
        #: is offset so that a centred sprite stands on its z
        self.assertEqual(drawn_extent(110, 55, 40, 128, 0), (-17600, 0))
        self.assertEqual(drawn_lift(110, 55, 40, 128), 0)
        #: tile 739, the urn: no offset, so its z goes half its height up
        self.assertEqual(drawn_lift(48, 0, 40, 128), 3840)

    def test_a_floor_sprite_is_a_plane(self):
        from bloodmap.placement import drawn_extent

        self.assertEqual(drawn_extent(64, 0, 64, 32, 500), (500, 500))


@unittest.skipUnless(E3M1.exists() and DWE3M1.exists(), "no town maps")
class TownMapsAreTheThresholdTests(unittest.TestCase):
    def test_the_campaign_buries_a_little_and_no_more(self):
        from bloodmap.format import read_map
        from tools.sprite_fit import audit, rates

        for path in (E3M1, DWE3M1):
            found = rates(audit(read_map(path)))
            self.assertGreater(found["sprites"], 200)
            self.assertLessEqual(found["sunk"], 0.03, path)
            self.assertLessEqual(found["squeezed"], 0.07, path)

    def test_the_town_maps_seat_a_standing_thing_on_its_drawn_bottom(self):
        """Not on its z: the census's height over the floor IS the lift."""
        import json

        from bloodmap.placement import drawn_lift
        from tools.sprite_fit import art

        assets = json.loads(Path(
            "projects/blood-city/references/city-assets.json").read_text(
                "utf-8"))["tiles"]
        for tile in (712, 739, 1009, 1013, 3540):
            row = assets[str(tile)]
            picture = art()[tile]
            lift = drawn_lift(picture.height, picture.animation["yofs"],
                              row["y_repeat"], row["cstat"])
            self.assertAlmostEqual(row["over_floor_bodies"], lift / 16960,
                                   delta=0.02, msg=tile)


class OverlapTests(unittest.TestCase):
    def _disk(self, sprites):
        import types

        return types.SimpleNamespace(sprites=[
            types.SimpleNamespace(fields=dict(
                {"cstat": 80, "picnum": 3808, "x_repeat": 64, "y_repeat": 64,
                 "angle": 0, "z": 0, "sector": 0}, **fields))
            for fields in sprites])

    def test_two_wall_sprites_on_one_plane_cover_each_other(self):
        from tools.sprite_fit import overlaps

        found = overlaps(self._disk([{"x": 100, "y": 0},
                                     {"x": 108, "y": 40}]))
        self.assertEqual(len(found), 1)
        self.assertGreater(found[0]["covered"], 0.5)

    def test_a_bucket_edge_does_not_hide_one_from_the_other(self):
        """8 units apart in depth is one wall: the fault that let six signs
        be written through pictures."""
        import sys

        sys.path.insert(0, "projects/blood-city/level")
        import wallplane

        a = wallplane._plane_key((0, 27174), (1.0, 0.0))
        b = wallplane._plane_key((0, 27182), (1.0, 0.0))
        self.assertNotEqual(a, b)              # the edge is real ...
        self.assertLessEqual(abs(a[2] - b[2]), 1)   # ... and one bucket wide

    def test_side_by_side_or_on_different_walls_they_do_not(self):
        from tools.sprite_fit import overlaps

        self.assertEqual(overlaps(self._disk([{"x": 100, "y": 0},
                                              {"x": 100, "y": 4000}])), [])
        self.assertEqual(overlaps(self._disk([{"x": 100, "y": 0},
                                              {"x": 900, "y": 0}])), [])


class LampSlotTests(unittest.TestCase):
    def test_staggered_lamps_alternate_pavements(self):
        from bloodmap.street import Run, lamp_slots

        run = Run("r", (0, 0), (36 * 1024, 0), 4096)
        paired = lamp_slots(run)
        staggered = lamp_slots(run, stagger=True)
        self.assertEqual(len(staggered) * 2, len(paired))
        self.assertEqual([s.side for s in staggered[:4]],
                         ["low", "high", "low", "high"])


@unittest.skipUnless(CITY.exists(), "the city is not built")
class CityFitsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map
        from tools.sprite_fit import lint

        cls.disk = read_map(CITY)
        cls.lint = lint(cls.disk)

    def test_nothing_is_sunk_or_squeezed_past_what_the_town_maps_do(self):
        rates = self.lint["rates"]
        #: was 5.2% sunk; the town maps run 0% to 2.1%
        self.assertLessEqual(rates["sunk"], 0.021)
        self.assertLessEqual(rates["through"], 0.013)
        self.assertLessEqual(rates["squeezed"], 0.056)

    def test_no_sign_is_written_through_a_picture(self):
        #: was 16 pairs; the two pledged coats on one rail are the one left
        self.assertLessEqual(len(self.lint["overlaps"]), 1)
        for pair in self.lint["overlaps"]:
            self.assertFalse(any(3808 <= t <= 3833 for t in pair["tiles"]))

    def test_a_statue_stands_on_a_floor(self):
        from tools.mine_stands import stands

        statues = [r for r in stands([str(CITY)]) if r["tile"] == 536]
        self.assertTrue(statues)
        for row in statues:
            #: on a floor (E3M1, twice), or raised with a body of air over
            #: its head (E1M2): never on a counter or in a shop's shelf
            tall = 17600 / 16960
            self.assertTrue(row["kind"] == "floor"
                            or (row["kind"] == "niche"
                                and row["clear"] >= tall + 0.9), row)

    def test_a_street_lamp_is_a_post_and_a_chain_lamp_has_a_ceiling(self):
        lamps = [s.fields for s in self.disk.sprites
                 if int(s.fields["picnum"]) == 640]
        self.assertGreaterEqual(len(lamps), 10)
        for f in lamps:
            self.assertEqual(int(f["y_repeat"]), 120)
        for sprite in self.disk.sprites:
            f = sprite.fields
            if int(f["picnum"]) == 641:
                sector = self.disk.sectors[int(f["sector"])].fields
                self.assertFalse(int(sector["ceiling_stat"]) & 1,
                                 "a lamp on a chain hangs under the sky")


if __name__ == "__main__":
    unittest.main()
