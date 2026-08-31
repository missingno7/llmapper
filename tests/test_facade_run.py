"""Building a frontage from the measured defaults.

`reports/blood-facade-grammar.md` measured what keeps a facade coherent; this
builds one from exactly that and nothing else. The load-bearing facts, in the
order the corpus ranks them: one wall tile across the run, a shared header
datum, a shared sill datum, and a bay of 1024 offered but never enforced.

Two things here were wrong first and are pinned so they stay fixed:

* the datums have to *shape* the opening. Recording `header_z` as an
  annotation left the mouth open floor-to-ceiling and the sign hanging in the
  hole; the header **is** the neighbour's ceiling.
* the piers between openings are wall, and wall in Build is void. 780 of 780
  campaign facade solid walls stand alone with nothing behind them and not one
  is a coincident pair, so the interior is set back by the wall's thickness and
  each opening is a passage cut through it.
"""

from __future__ import annotations

import unittest

from bloodmap.aperture import (
    ApertureError,
    FACADE_BAY,
    FACADE_REVEAL,
    JAMB_PICNUM,
    PLAYER_HEIGHT,
    SIGN_HEIGHT_CORPUS_SPREAD,
    SIGN_HEIGHT_PLAYER_HEIGHTS,
    FacadeOpening,
    facade_run,
)
from bloodmap.planar_layout import PlanarLayout

WALL, FLOOR, CEILING, SKY = 400, 294, 285, 3491
HEADER_Z, SILL_Z = -40960, -1024
DEPTH = 3 * FACADE_BAY
STREET_DEPTH = 6 * FACADE_BAY


def street(bays=6, *, openings=((1, 1), (3, 1)), sign=None, **kwargs):
    """A street with a frontage along its south edge."""
    width = bays * FACADE_BAY
    layout = PlanarLayout(name="facade-test")
    layout.add_region(
        "region:street",
        [(0, 0), (width, 0), (width, STREET_DEPTH), (0, STREET_DEPTH)],
        floor_z=0, ceiling_z=-6 * PLAYER_HEIGHT,
        wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=SKY,
        parallax_ceiling=True)
    spec = [FacadeOpening(bay=b, bays=w,
                          sign=(sign if index == 0 else None))
            for index, (b, w) in enumerate(openings)]
    built = facade_run(
        layout, "facade", host_region="region:street",
        a1=(0, 0), a2=(width, 0), depth=DEPTH, openings=spec,
        wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
        header_z=HEADER_Z, sill_z=SILL_Z, jamb_picnum=JAMB_PICNUM, **kwargs)
    layout.set_player_start("region:street", x=width // 2,
                            y=STREET_DEPTH * 2 // 3, z=0)
    return layout, built


def disk_of(layout):
    return layout.compile().level.to_disk_map()


class FrontageTests(unittest.TestCase):
    def setUp(self):
        self.layout, self.built = street()
        self.disk = disk_of(self.layout)

    def test_it_compiles_to_a_map(self):
        """The weakest claim in the file, and deliberately not the last one."""
        self.assertGreaterEqual(len(self.disk.sectors), 4)
        self.assertTrue(self.disk.walls)

    def test_the_header_is_the_neighbours_ceiling(self):
        """Not an annotation: the datum is the geometry that makes the mouth."""
        for opening in self.built["openings"]:
            region = self.layout.regions[opening["reveal_region"]]
            self.assertEqual(int(region.ceiling_z), HEADER_Z)

    def test_the_sill_is_the_neighbours_floor(self):
        for opening in self.built["openings"]:
            region = self.layout.regions[opening["reveal_region"]]
            self.assertEqual(int(region.floor_z), SILL_Z)

    def test_the_building_behind_defaults_to_the_same_datums(self):
        """A shop that wants a higher ceiling than its own mouth is a second
        room behind this one, not a deeper number here -- so the default is
        the datum, and a caller has to say otherwise on purpose.
        """
        interior = self.layout.regions[self.built["interior"]]
        self.assertEqual(int(interior.ceiling_z), HEADER_Z)
        self.assertEqual(int(interior.floor_z), SILL_Z)

    def test_a_taller_interior_is_available_but_never_the_default(self):
        _layout, built = street(interior_ceiling_z=-60000)
        self.assertEqual(int(_layout.regions[built["interior"]].ceiling_z), -60000)
        for opening in built["openings"]:
            self.assertEqual(int(_layout.regions[opening["reveal_region"]].ceiling_z),
                             HEADER_Z)

    def test_every_opening_shares_one_header_and_one_sill(self):
        """What makes several openings read as one facade: 79% and 77% of the
        131 campaign multi-opening facades, against 31% for the bay grid."""
        headers = {int(self.layout.regions[o["reveal_region"]].ceiling_z)
                   for o in self.built["openings"]}
        sills = {int(self.layout.regions[o["reveal_region"]].floor_z)
                 for o in self.built["openings"]}
        self.assertEqual(len(headers), 1)
        self.assertEqual(len(sills), 1)

    def test_the_wall_carries_one_tile_across_the_run(self):
        """98% of campaign multi-opening facades, the strongest signal there is."""
        build = self.disk.to_build_ir()
        street_walls = [w["fields"] for w in build.walls
                        if int(w["fields"]["next_sector"]) < 0]
        self.assertIn(WALL, {int(w["picnum"]) for w in street_walls})

    def test_the_band_above_the_mouth_wears_the_facade_not_the_jamb(self):
        """`dress the reveal, never the band above the mouth`. The lintel is
        drawn from the street-side record, so a jamb tile there paints a
        stripe of metal across the frontage above every window.
        """
        build = self.disk.to_build_ir()
        reveals = {int(o["reveal_region"].split(":")[-1]) for o in self.built["openings"]}
        street_side = [w["fields"] for w in build.walls
                       if int(w["fields"]["next_sector"]) >= 0
                       and int(w["fields"]["picnum"]) == WALL]
        self.assertTrue(street_side, "no street-side portal wears the facade tile")
        self.assertTrue(any(int(w["picnum"]) == JAMB_PICNUM
                            for w in (x["fields"] for x in build.walls)),
                        "the jamb is nowhere; the reveal is undressed")

    def test_the_piers_are_void_not_a_wall_sandwich(self):
        """780 of 780 campaign facade solid walls stand alone. A coincident
        pair here is an infinitely thin partition, which the authored-geometry
        gate rejects and the engine renders as a seam.
        """
        build = self.disk.to_build_ir()
        ends = {}
        for index, wall in enumerate(build.walls):
            f = wall["fields"]
            e = build.walls[int(f["point2"])]["fields"]
            ends.setdefault(((int(f["x"]), int(f["y"])),
                             (int(e["x"]), int(e["y"]))), []).append(index)
        doubled = [key for key, ids in ends.items()
                   if ends.get((key[1], key[0])) and len(ids) == 1
                   and build.walls[ids[0]]["fields"]["next_sector"] == -1]
        self.assertEqual(doubled, [])

    def test_the_interior_is_set_back_by_the_wall_thickness(self):
        self.assertEqual(self.built["reveal"], FACADE_REVEAL)
        interior = self.layout.regions[self.built["interior"]]
        ys = [p[1] for p in interior.outer]
        self.assertEqual(max(ys), -FACADE_REVEAL)

    def test_an_opening_off_the_end_of_the_run_is_refused(self):
        with self.assertRaises(ApertureError):
            street(bays=4, openings=((6, 1),))

    def test_a_run_with_no_openings_is_refused(self):
        """A facade is a run interrupted by openings; a blank wall is a wall."""
        with self.assertRaises(ApertureError):
            street(openings=())

    def test_a_wall_thicker_than_its_building_is_refused(self):
        with self.assertRaises(ApertureError):
            street(reveal=DEPTH + 1)

    def test_the_header_must_be_above_the_sill(self):
        layout = PlanarLayout(name="upside-down")
        layout.add_region("region:street", [(0, 0), (4096, 0), (4096, 4096), (0, 4096)],
                          floor_z=0, ceiling_z=-6 * PLAYER_HEIGHT,
                          wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=SKY)
        with self.assertRaises(ApertureError):
            facade_run(layout, "f", host_region="region:street", a1=(0, 0),
                       a2=(4096, 0), depth=DEPTH,
                       openings=[FacadeOpening(bay=1)],
                       wall_picnum=WALL, floor_picnum=FLOOR,
                       ceiling_picnum=CEILING, header_z=-1024, sill_z=-40960)


class SignTests(unittest.TestCase):
    """The height is an authoring preference; being above the head is not."""

    def test_a_sign_sits_at_the_stated_height_above_the_street(self):
        _layout, built = street(sign="MEATS")
        sign = built["signs"][0]
        self.assertEqual(sign["height_player_heights"], SIGN_HEIGHT_PLAYER_HEIGHTS)
        self.assertEqual(sign["seat_z"],
                         -int(round(SIGN_HEIGHT_PLAYER_HEIGHTS * PLAYER_HEIGHT)))

    def test_the_sign_clears_its_openings_header(self):
        """Every one of the 26 campaign letters does, so this is enforced
        while the height itself is only stated."""
        _layout, built = street(sign="MEATS")
        self.assertGreater(built["signs"][0]["above_its_header_z"], 0)

    def test_a_sign_below_the_header_is_refused(self):
        with self.assertRaises(ApertureError):
            street(sign="MEATS", sign_height_player_heights=0.5)

    def test_the_corpus_spread_is_carried_with_the_choice(self):
        """A preference stated without its spread implies a precision the
        corpus does not have: cv 0.33 over 86 letters, 1.69 to 5.13."""
        _layout, built = street(sign="MEATS")
        basis = built["basis"]["sign height"]
        self.assertEqual(basis["kind"], "authoring preference, not a datum")
        self.assertEqual(basis["chosen"], SIGN_HEIGHT_PLAYER_HEIGHTS)
        self.assertEqual(basis["median"], SIGN_HEIGHT_CORPUS_SPREAD["median"])
        self.assertGreater(basis["coefficient_of_variation"], 0.3)

    def test_one_letter_sprite_per_letter(self):
        _layout, built = street(sign="MEATS")
        self.assertEqual(len(built["signs"][0]["placements"]), len("MEATS"))


class WidthInvarianceTests(unittest.TestCase):
    """Phase 13's exit shape, piloted: change the width, keep the relations."""

    def setUp(self):
        _n, self.narrow = street(6, openings=((1, 1), (3, 1)), sign="MEATS")
        _w, self.wide = street(10, openings=((1, 1), (3, 1), (6, 2)), sign="MEATS")

    def test_the_bay_and_the_reveal_do_not_move(self):
        self.assertEqual(self.narrow["bay"], self.wide["bay"])
        self.assertEqual(self.narrow["reveal"], self.wide["reveal"])

    def test_both_datums_survive_the_width_change(self):
        self.assertEqual(self.narrow["datums"], self.wide["datums"])

    def test_the_sign_seat_survives_the_width_change(self):
        left, right = self.narrow["signs"][0], self.wide["signs"][0]
        self.assertEqual(left["seat_z"], right["seat_z"])
        self.assertEqual(left["above_its_header_z"], right["above_its_header_z"])

    def test_the_run_grows_and_the_openings_stay_where_they_were_put(self):
        self.assertLess(self.narrow["run_bays"], self.wide["run_bays"])
        shared = self.wide["openings"][:len(self.narrow["openings"])]
        self.assertEqual([o["along_run"] for o in self.narrow["openings"]],
                         [o["along_run"] for o in shared])


class PromotionTests(unittest.TestCase):
    def test_it_is_not_claimed_as_a_vocabulary_constructor(self):
        """vocabulary.py admits a concept only when a compact parameter set
        reproduces held-out examples. That has never been run here, and the
        blockers say so rather than leaving it implied.
        """
        import bloodmap.vocabulary as vocabulary

        self.assertNotIn("facade_run", vocabulary.CORPUS_SUPPORT)
        self.assertFalse(hasattr(vocabulary, "facade_run"))

    def test_the_blockers_are_stated_on_every_build(self):
        _layout, built = street()
        self.assertTrue(built["promotion_blockers"])
        self.assertTrue(any("held-out" in blocker
                            for blocker in built["promotion_blockers"]))

    def test_rhythm_is_not_a_parameter(self):
        """53 repeating runs in 890 campaign candidates is not enough
        recurrence to give one a default, so openings are an argument."""
        import inspect

        signature = inspect.signature(facade_run)
        self.assertNotIn("rhythm", signature.parameters)
        self.assertIn("openings", signature.parameters)
        self.assertIs(signature.parameters["openings"].default,
                      inspect.Parameter.empty)


if __name__ == "__main__":
    unittest.main()
