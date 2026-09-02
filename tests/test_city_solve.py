"""The grid solved from the interiors up, not taken from a norm.

Gravesend fixed its block columns from `city-norms.md` and carved rooms into
what that left. The arcade is the bill: `l3_mall.MASS` is 14336 wide, its
envelope with walls and a facade recess is 15872, and the norm gave the whole
column 14336. The solver makes that a number instead of a disappointment.

The absolute check (owner-queue item 17): a relative test -- "the solve is
self-consistent" -- would pass a city built entirely at the wrong scale. So
these assert against E3M1's measured proportions, and against class minima
that are Build units and not ratios.
"""

import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")


def _solve():
    import sys

    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))
    try:
        import city_solve
    except ImportError as error:                       # pragma: no cover
        raise unittest.SkipTest(str(error))
    return city_solve


class AnEnvelopeComesUpFromItsRooms(unittest.TestCase):
    def test_walls_and_a_facade_recess_are_added_to_the_interior(self):
        # The whole of the model in one assertion: a 14336 concourse needs
        # 14336 + two walls + one recess, and a grid that offers 14336 has
        # not offered enough.
        solve = _solve()
        arcade = solve.Envelope("arcade", (14336, 10240), faced=("west",))
        self.assertEqual(arcade.demand("x"), 14336 + 2 * 512 + 512)
        # the unfaced axis pays for walls only
        self.assertEqual(arcade.demand("y"), 10240 + 2 * 512)

    def test_a_building_fronting_two_streets_pays_the_recess_twice(self):
        solve = _solve()
        corner = solve.Envelope("corner", (4096, 4096), faced=("west", "east"))
        self.assertEqual(corner.demand("x"), 4096 + 1024 + 2 * 512)

    def test_the_recess_depth_is_e6m1s(self):
        # P13 measured it: E6M1's s4/s64 are 4096 x 512 display recesses.
        solve = _solve()
        self.assertEqual(solve.FACADE_DEPTH, 512)

    def test_a_cell_is_its_widest_envelope_plus_its_band(self):
        solve = _solve()
        cell = solve.Cell("col", (solve.Envelope("a", (4096, 4096)),
                                  solve.Envelope("b", (8192, 2048))))
        self.assertEqual(cell.demand("x"), 8192 + 1024)
        self.assertEqual(cell.island("x"), 8192 + 1024 + 2 * solve.BAND)


class RoadsAreSpacers(unittest.TestCase):
    """The composition rule: islands are designed, roads push them apart."""

    def test_a_gutter_takes_its_class_minimum(self):
        solve = _solve()
        from resolution import WIDTH_UNITS  # noqa: E402

        for name, width in WIDTH_UNITS.items():
            self.assertEqual(solve.Gutter("g", name).width(WIDTH_UNITS), width)

    def test_a_path_is_e3m1s_512_between_abutting_islands(self):
        # E3M1 s10/s11: where no road runs, the houses are separated by a
        # pavement-only path 512 wide. Not zero, and not a road.
        solve = _solve()
        from resolution import WIDTH_UNITS

        self.assertEqual(solve.Gutter("p", "path").width(WIDTH_UNITS), 512)
        self.assertEqual(solve.PATH_BAND, 512)

    def test_an_unknown_class_is_refused_rather_than_guessed(self):
        solve = _solve()
        from resolution import WIDTH_UNITS

        with self.assertRaises(solve.SolveError):
            solve.Gutter("g", "boulevard").width(WIDTH_UNITS)


class SlackAbsorbsTheResidueAndNothingElseDoes(unittest.TestCase):
    def test_the_residue_goes_to_the_slack_cell(self):
        solve = _solve()
        from resolution import WIDTH_UNITS

        order = [solve.Cell("rigid", (solve.Envelope("v", (4096, 4096)),)),
                 solve.Gutter("street", "street"),
                 solve.Cell("plaza", (), slack=True)]
        loose = solve.solve_axis("x", order, WIDTH_UNITS, target=40000)
        self.assertEqual(loose.total, 40000)
        rigid = loose.span("rigid")
        tight = solve.solve_axis("x", order, WIDTH_UNITS)
        self.assertEqual(rigid, tight.span("rigid"),
                         "an interior must not move when slack is available")
        self.assertGreater(loose.slack_given["plaza"], 0)

    def test_a_target_the_rigid_parts_already_exceed_is_refused(self):
        # Never quietly shrink an interior or a corridor: say the city does
        # not fit.
        solve = _solve()
        from resolution import WIDTH_UNITS

        order = [solve.Cell("rigid", (solve.Envelope("v", (20480, 4096)),)),
                 solve.Cell("plaza", (), slack=True)]
        with self.assertRaises(solve.SolveError):
            solve.solve_axis("x", order, WIDTH_UNITS, target=8192)


class AgainstE3M1(unittest.TestCase):
    """The absolute checks. Rates against the corpus, sizes against Build."""

    #: Measured 2026-09-02 over E3M1's own street surface: 290.5M of road
    #: against 759.4M of pavement.
    E3M1_CORRIDOR_SHARE = 0.27
    #: Its four road strips: 4096, 4096, 5120, 7456 across.
    E3M1_ROAD_WIDTHS = (4096, 4096, 5120, 7456)
    #: Its fourteen pavement sectors: 512 x2, 1024, 2048 x6, 2560.
    E3M1_BANDS = (512, 1024, 2048, 2560)

    def test_every_class_minimum_is_inside_e3m1s_road_widths(self):
        # ABSOLUTE: a class minimum is a number of Build units, and a city
        # whose streets are all 512 or all 40960 would pass every ratio test
        # in this file.
        _solve()
        from resolution import WIDTH_UNITS

        low, high = min(self.E3M1_ROAD_WIDTHS), max(self.E3M1_ROAD_WIDTHS)
        for name in ("street", "row", "avenue"):
            self.assertGreaterEqual(WIDTH_UNITS[name], low // 2, name)
            self.assertLessEqual(WIDTH_UNITS[name], high, name)

    def test_the_band_is_inside_e3m1s_measured_envelope(self):
        solve = _solve()

        self.assertGreaterEqual(solve.BAND, min(self.E3M1_BANDS))
        self.assertLessEqual(solve.BAND, max(self.E3M1_BANDS))
        self.assertIn(solve.BAND, self.E3M1_BANDS,
                      "the band should be one E3M1 actually uses")

    def test_the_solved_city_spends_its_area_the_way_e3m1_does(self):
        # The rate that matters: how much of the ground is corridor. E3M1 is
        # 27%; a solve that came out at 5% would be a city of courtyards and
        # one at 60% a car park, and both would pass every other test here.
        import sys

        if str(LEVEL) not in sys.path:
            sys.path.insert(0, str(LEVEL))
        try:
            import city_plan                       # noqa: F401
        except ImportError as error:               # pragma: no cover
            self.skipTest(str(error))
        solve = _solve()
        from resolution import WIDTH_UNITS

        def env(name):
            spec = dict(city_plan.ENVELOPES[name])
            spec.pop("source", None)
            return solve.Envelope(name, tuple(spec["interior"]),
                                  faced=tuple(spec.get("faced", ("south",))))

        order = [solve.Gutter("lane_west", "lane"),
                 solve.Cell("col_a", (env("aldermack"), env("saloon"))),
                 solve.Gutter("west_street", "street"),
                 solve.Cell("col_b", (env("market_hall"),)),
                 solve.Gutter("avenue", "avenue"),
                 solve.Cell("col_c", (env("church"), env("arcade"))),
                 solve.Gutter("spur", "street")]
        solution = solve.solve_axis("x", order, WIDTH_UNITS)
        stats = solve.compare(solution, [])
        self.assertAlmostEqual(stats["corridor_share"],
                               self.E3M1_CORRIDOR_SHARE, delta=0.12,
                               msg=f"corridor share {stats['corridor_share']} "
                                   f"against E3M1's {self.E3M1_CORRIDOR_SHARE}")

    def test_the_arcade_column_the_old_grid_gave_was_too_small(self):
        # The defect this replaces, as a number: the norm gave col_c 14336
        # Build units and the arcade alone demands more than that.
        import sys

        if str(LEVEL) not in sys.path:
            sys.path.insert(0, str(LEVEL))
        try:
            import city_plan
        except ImportError as error:               # pragma: no cover
            self.skipTest(str(error))
        solve = _solve()
        from resolution import PU

        arcade = solve.Envelope("arcade",
                                tuple(city_plan.ENVELOPES["arcade"]["interior"]),
                                faced=("west",))
        old_column = 14 * PU
        self.assertGreater(arcade.demand("x"), old_column,
                           "if this ever passes, the old grid was fine and "
                           "the solver has nothing to fix")


if __name__ == "__main__":
    unittest.main()
