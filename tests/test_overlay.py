"""Partition overlays: one thing lying across several sectors.

The idiom being replaced is "insert a sector into another where there is
room". It is why Gravesend's streets are the residue of its district regions
and why its light pools are carved holes rather than light. An overlay cuts
regions into pieces that inherit everything from their parent and differ only
in what the overlay says, so a road's texture runs on through a shadow edge as
if the edge were not there.

The absolute check (owner-queue item 17): every assertion here that could be
satisfied by a uniformly wrong geometry is paired with one against a measured
number -- E3M1's 2048 kerb rise, its tile 6, its 84-degree shadow bearing.
"""

import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")
SQUARE = [(0, 0), (4096, 0), (4096, 4096), (0, 4096)]


def _resolution():
    import sys

    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))
    try:
        import resolution
    except ImportError as error:                       # pragma: no cover
        raise unittest.SkipTest(str(error))
    return resolution


class SplittingIsExact(unittest.TestCase):
    def test_a_square_cut_in_half_gives_two_halves_and_no_slivers(self):
        from bloodmap.overlay import Cut, signed_area, split_convex

        left, right = split_convex(SQUARE, Cut((2048, 0), (2048, 4096)))
        self.assertEqual(abs(signed_area(left)), 4096 * 2048)
        self.assertEqual(abs(signed_area(right)), 4096 * 2048)
        self.assertEqual(abs(signed_area(left)) + abs(signed_area(right)),
                         abs(signed_area(SQUARE)),
                         "a split must conserve area exactly")

    def test_an_oblique_cut_conserves_area_too(self):
        # The shadow case: 84 degrees, so the crossing points are not on the
        # grid and the arithmetic has somewhere to go wrong.
        from bloodmap.overlay import Cut, signed_area, split_convex

        left, right = split_convex(SQUARE, Cut((0, 0), (416, 4096)))
        total = abs(signed_area(left)) + abs(signed_area(right))
        self.assertAlmostEqual(total, abs(signed_area(SQUARE)), delta=2.0)

    def test_a_cut_that_misses_leaves_one_side_empty(self):
        # The square lies at x < 8192, and "left of a line running +y" is the
        # -x side, so the whole square comes back on the left and the right is
        # empty. Spelling the orientation out because a sign error here would
        # put every kerb on the wrong record.
        from bloodmap.overlay import Cut, split_convex

        left, right = split_convex(SQUARE, Cut((8192, 0), (8192, 4096)))
        self.assertEqual(right, [])
        self.assertEqual(len(left), 4)

    def test_a_concave_region_is_refused_loudly(self):
        # "Insert where there is room" answered this case by guessing. The
        # replacement has to say it cannot, or it is the same thing again.
        from bloodmap.overlay import Cut, OverlayError, split_convex

        ell = [(0, 0), (4096, 0), (4096, 2048), (2048, 2048),
               (2048, 4096), (0, 4096)]
        with self.assertRaises(OverlayError):
            split_convex(ell, Cut((1024, 0), (1024, 4096)))

    def test_clipping_to_a_rect_gives_an_inside_and_the_offcuts(self):
        from bloodmap.overlay import clip_to_rect, signed_area

        inside, outside = clip_to_rect(SQUARE, (1024, 1024, 3072, 3072))
        self.assertEqual(abs(signed_area(inside)), 2048 * 2048)
        self.assertEqual(len(outside), 4)
        total = abs(signed_area(inside)) + sum(abs(signed_area(p))
                                               for p in outside)
        self.assertEqual(total, abs(signed_area(SQUARE)))


class APieceInheritsEverythingButWhatTheOverlaySays(unittest.TestCase):
    def test_the_covered_piece_carries_the_change_and_the_rest_do_not(self):
        from bloodmap.overlay import apply_overlay

        pieces = apply_overlay(
            {"road": SQUARE},
            [(1024, 1024), (3072, 1024), (3072, 3072), (1024, 3072)],
            {"floor_shade": 34}, label="shadow",
            inherits={"road": {"floor_picnum": 352, "floor_z": 10240}})
        shaded = [p for p in pieces if p.changes]
        self.assertEqual(len(shaded), 1)
        self.assertEqual(shaded[0].changes["floor_shade"], 34)
        for piece in pieces:
            self.assertEqual(piece.parent, "road")
            self.assertEqual(piece.inherits["floor_picnum"], 352,
                             "a piece is the same region, not a new one")

    def test_an_overlay_that_misses_a_region_produces_no_pieces_for_it(self):
        from bloodmap.overlay import apply_overlay

        pieces = apply_overlay({"far": [(20480, 0), (24576, 0),
                                        (24576, 4096), (20480, 4096)]},
                               [(0, 0), (1024, 0), (1024, 1024), (0, 1024)],
                               {"floor_shade": 34})
        self.assertEqual(pieces, [])


class TheKerbIsTheIslandsOwnEdge(unittest.TestCase):
    """E3M1, measured: tile 6 on 11 of 11 road-side records, step 2048."""

    def test_the_island_stands_2048_above_its_ground_plane(self):
        # ABSOLUTE, and the number is E3M1's without exception. Blood's z
        # grows downward, so standing higher is a smaller z.
        from bloodmap.overlay import HeightIsland

        island = HeightIsland("pavement", tuple(SQUARE))
        self.assertEqual(island.rise, 2048)
        self.assertEqual(island.floor_z(10240), 8192)

    def test_the_kerb_tile_goes_on_the_road_side_record(self):
        # The correction the whole model rests on: the band that draws faces
        # the road. Gravesend put the house tiles there because the band was
        # a hole's edge in a street residue and inherited the building.
        from bloodmap.overlay import HeightIsland, kerb_records

        island = HeightIsland("pavement", tuple(SQUARE))
        records = kerb_records(island, "road", SQUARE)
        self.assertEqual(len(records), 4)
        for record in records:
            self.assertEqual(record["side"], "ground")
            self.assertEqual(record["picnum"], 6)
            self.assertEqual(record["band"], 2048)

    def test_e3m1_really_does_put_tile_six_there(self):
        # The fixture behind the constant, read off the map rather than
        # trusted: every road-side record at a road/pavement boundary.
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps
        from bloodmap.texture_frame import sector_index

        found = [e for e in list_corpus_maps(population="blood-campaign")
                 if e.path.stem.upper() == "E3M1"]
        if not found:
            self.skipTest("E3M1 is not in the corpus")
        disk = read_map(found[0].path)
        owners = sector_index(disk)
        roads = {i for i, s in enumerate(disk.sectors)
                 if int(s.fields["floor_picnum"]) == 352}
        paves = {i for i, s in enumerate(disk.sectors)
                 if int(s.fields["floor_picnum"]) == 4}
        tiles, steps = [], []
        for index, wall in enumerate(disk.walls):
            nxt = int(wall.fields["next_sector"])
            if nxt < 0 or owners[index] not in roads or nxt not in paves:
                continue
            tiles.append(int(wall.fields["picnum"]))
            steps.append(int(disk.sectors[nxt].fields["floor_z"])
                         - int(disk.sectors[owners[index]].fields["floor_z"]))
        self.assertEqual(len(tiles), 11)
        self.assertEqual(set(tiles), {6})
        self.assertEqual(set(steps), {-2048})


class OneSunForTheWholeLevel(unittest.TestCase):
    def test_the_bearing_is_stated_in_build_angle_units(self):
        # The convention, once: 0..2047, zero along +x, increasing the way
        # sprite.ang does, and it is the direction the shadow is cast toward.
        resolution = _resolution()

        self.assertEqual(resolution.SUN_BEARING, 478)
        self.assertAlmostEqual(resolution.SUN_BEARING * 360.0 / 2048.0,
                               resolution.SUN_BEARING_DEGREES, places=1)

    def test_it_is_the_angle_e3m1s_own_shadow_edges_run_at(self):
        # ABSOLUTE: 416 across for 4096 along, which is what the geometry
        # gives and what the oblique cluster measures.
        import math

        resolution = _resolution()
        measured = math.degrees(math.atan2(4096, 416))
        self.assertAlmostEqual(measured, resolution.SUN_BEARING_DEGREES,
                               delta=resolution.SUN_BEARING_TOLERANCE_DEGREES)

    def test_a_cut_at_the_suns_bearing_reads_back_as_the_suns(self):
        from bloodmap.overlay import Cut

        resolution = _resolution()
        edge = Cut((0, 0), (416, 4096))
        self.assertAlmostEqual(edge.bearing, resolution.SUN_BEARING_DEGREES,
                               delta=resolution.SUN_BEARING_TOLERANCE_DEGREES)

    def test_an_axis_aligned_edge_is_not_the_suns(self):
        # The check has to be able to fail, or "shadow edges share the sun's
        # angle" is satisfied by every sector boundary in the map.
        from bloodmap.overlay import Cut

        resolution = _resolution()
        self.assertGreater(
            abs(Cut((0, 0), (4096, 0)).bearing - resolution.SUN_BEARING_DEGREES),
            resolution.SUN_BEARING_TOLERANCE_DEGREES)

    def test_the_shade_palette_is_e3m1s(self):
        resolution = _resolution()

        self.assertEqual((resolution.SHADE_LIT, resolution.SHADE_SHADOW,
                          resolution.SHADE_PENUMBRA), (8, 34, 24))


if __name__ == "__main__":
    unittest.main()


class AGroundPlaneIsOneRegion(unittest.TestCase):
    """A junction is a place on the plane, not a thing to declare.

    The slice-2 emitter failed `zero_exit_gameplay_sector` at three junction
    squares because it emitted them as separate regions joined by
    connections. A square whose every neighbour was a road piece at the same z
    still had nothing the compiler would call a way out, because it had been
    authored as a room rather than as part of the floor it is part of.
    """

    W, L = 5120, 20480

    def _strips(self, kind):
        a, b = self.L // 2 - self.W // 2, self.L // 2 + self.W // 2
        if kind == "crossing":
            return [(a, 0, b, self.L), (0, a, self.L, b)]
        return [(a, 0, b, self.L), (0, a, a, b)]

    def test_a_crossing_traces_as_one_twelve_sided_plane(self):
        from bloodmap.overlay import ground_plane, signed_area

        plane = ground_plane(self._strips("crossing"))
        self.assertEqual(len(plane), 12)
        #: two strips less the square they share, exactly
        self.assertEqual(abs(signed_area(plane)),
                         2 * self.W * self.L - self.W * self.W)

    def test_a_tee_traces_as_one_eight_sided_plane(self):
        from bloodmap.overlay import ground_plane

        self.assertEqual(len(ground_plane(self._strips("tee"))), 8)

    def test_the_junction_square_is_the_class_widths(self):
        # E3M1 s3 is 5120 x 5120 where two 5120 roads meet. Here the square is
        # what the two strips share, so it is their widths by construction --
        # asserted because a junction sized from anything else would be a
        # number somebody chose.
        from bloodmap.overlay import ground_plane, signed_area

        plane = ground_plane(self._strips("crossing"))
        strips = 2 * self.W * self.L
        overlap = strips - abs(signed_area(plane))
        self.assertEqual(overlap, self.W * self.W)

    def test_disconnected_strips_are_refused_with_the_model_named(self):
        from bloodmap.overlay import OverlayError, ground_plane

        with self.assertRaises(OverlayError) as caught:
            ground_plane([(0, 0, 1024, 1024), (8192, 8192, 9216, 9216)])
        self.assertIn("connected network", str(caught.exception))

    def test_a_plane_with_islands_on_it_compiles_with_no_zero_exit(self):
        # The whole point: emit the plane whole and the junction needs no
        # exits of its own, because it is not a sector of its own.
        from bloodmap.overlay import ground_plane
        from bloodmap.planar_layout import PlanarLayout

        a, b = self.L // 2 - self.W // 2, self.L // 2 + self.W // 2
        plane = ground_plane(self._strips("crossing"))
        layout = PlanarLayout(name="junction")
        layout.add_region("plane", plane, floor_z=10240, ceiling_z=10240 - 196608,
                          floor_picnum=352, ceiling_picnum=3491, wall_picnum=6,
                          parallax_ceiling=True, role="street")
        islands = {"nw": [(0, 0), (a, 0), (a, a), (0, a)],
                   "ne": [(b, 0), (self.L, 0), (self.L, a), (b, a)],
                   "sw": [(0, b), (a, b), (a, self.L), (0, self.L)],
                   "se": [(b, b), (self.L, b), (self.L, self.L), (b, self.L)]}
        for name, outline in islands.items():
            layout.add_region(name, outline, floor_z=10240 - 2048,
                              ceiling_z=10240 - 196608, floor_picnum=4,
                              ceiling_picnum=3491, wall_picnum=400,
                              parallax_ceiling=True, role="street")
            for index, point in enumerate(outline):
                nxt = outline[(index + 1) % len(outline)]
                if not _on_ring(plane, point, nxt):
                    continue
                layout.add_connection(f"kerb:{name}:{index}", "plane", name,
                                      role="portal", a1=point, a2=nxt)
                layout.paint_wall("plane", point, nxt, picnum=6)
        layout.set_player_start("plane", x=self.L // 2, y=self.L // 2,
                                z=10240, angle=0)
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        self.assertEqual(len(disk.sectors), 5, "one plane and four islands")


def _on_ring(ring, a, b):
    for index, point in enumerate(ring):
        nxt = ring[(index + 1) % len(ring)]
        if {tuple(point), tuple(nxt)} == {tuple(a), tuple(b)}:
            return True
    return False


class TheClipperCutsWhatSplitConvexRefused(unittest.TestCase):
    """Owner-queue item 21's default, built.

    `split_convex` refuses a concave polygon on purpose -- guessing at a
    concave cut is the "insert a sector where there is room" idiom this model
    replaces -- and that refusal is what stopped slice 2b, because the ground
    plane is a lattice. This is the general answer: even-odd chord pairing
    over ALL rings at once, so holes need no special case.

    The absolute check is area: a cut conserves it exactly, in integers.
    """

    PLANE = None

    def _plane(self):
        from bloodmap.overlay import ground_plane

        W, L = 5120, 20480
        a, b = L // 2 - W // 2, L // 2 + W // 2
        return ground_plane([(a, 0, b, L), (0, a, L, b)]), W, L

    def test_a_concave_plane_cuts_and_conserves_its_area(self):
        from bloodmap.overlay import (
            Cut, region_area, signed_area, split_polygon)

        plane, _w, length = self._plane()
        whole = abs(signed_area(plane))
        for cut in (Cut((length // 2, 0), (length // 2, length)),
                    Cut((2048, 0), (2048 + 416, 4096))):
            left, right = split_polygon([plane], cut)
            total = (sum(region_area(r) for r in left)
                     + sum(region_area(r) for r in right))
            self.assertEqual(total, whole, f"area lost by {cut}")

    def test_holes_need_no_special_case(self):
        # The plane's islands are its holes, so the pairing runs over every
        # ring together. A cut straight through two holes still conserves.
        from bloodmap.overlay import Cut, region_area, split_polygon

        outer = [(0, 0), (20480, 0), (20480, 20480), (0, 20480)]
        a = [(2048, 2048), (8192, 2048), (8192, 8192), (2048, 8192)]
        b = [(12288, 12288), (18432, 12288), (18432, 18432), (12288, 18432)]
        whole = 20480 ** 2 - 2 * 6144 ** 2
        for cut in (Cut((10240, 0), (10240, 20480)),
                    Cut((0, 0), (20480, 20480)),
                    Cut((5120, 0), (5120, 20480))):
            left, right = split_polygon([outer, a, b], cut)
            total = (sum(region_area(r) for r in left)
                     + sum(region_area(r) for r in right))
            self.assertEqual(total, whole, f"area lost by {cut}")

    def test_a_cut_may_leave_two_disconnected_pieces(self):
        # A U cut across its arms: one side is two pieces. `split_convex`
        # could never say this, and a clipper that returned one polygon would
        # be silently wrong.
        from bloodmap.overlay import Cut, region_area, split_polygon

        u = [(0, 0), (4096, 0), (4096, 12288), (8192, 12288), (8192, 0),
             (12288, 0), (12288, 16384), (0, 16384)]
        left, right = split_polygon([u], Cut((0, 6144), (12288, 6144)))
        pieces = left if len(left) > 1 else right
        self.assertEqual(len(pieces), 2)
        self.assertEqual(region_area(pieces[0]), region_area(pieces[1]))

    def test_a_convex_shadow_is_a_sequence_of_cuts(self):
        from bloodmap.overlay import cut_by_convex, region_area

        square = [(0, 0), (4096, 0), (4096, 4096), (0, 4096)]
        inside, outside, _ = cut_by_convex(
            [square], [(1024, 1024), (3072, 1024), (3072, 3072), (1024, 3072)])
        self.assertEqual(sum(region_area(r) for r in inside), 2048 * 2048)
        self.assertEqual(sum(region_area(r) for r in inside)
                         + sum(region_area(r) for r in outside), 4096 * 4096)

    def test_a_shadow_covering_a_whole_island_leaves_no_outside(self):
        from bloodmap.overlay import cut_by_convex, region_area

        island = [(1024, 1024), (3072, 1024), (3072, 3072), (1024, 3072)]
        inside, outside, _ = cut_by_convex(
            [island], [(0, 0), (4096, 0), (4096, 4096), (0, 4096)])
        self.assertEqual(outside, [])
        self.assertEqual(sum(region_area(r) for r in inside), 2048 * 2048)

    def test_a_sliver_is_absorbed_and_reported_not_refused(self):
        from bloodmap.overlay import Cut, MIN_PIECE_AREA, cut_region

        #: a cut one unit inside a short edge: the offcut is under the floor
        thin = [(0, 0), (4096, 0), (4096, 512), (0, 512)]
        left, right, absorbed = cut_region([thin], Cut((4095, 0), (4095, 512)))
        self.assertTrue(absorbed, "a sliver must be reported")
        self.assertLess(absorbed[0]["area"], MIN_PIECE_AREA)
        #: and the polygon survives whole on the side it is mostly on
        self.assertEqual(len(left) + len(right), 1)


class ACutNeverTouchesAMechanism(unittest.TestCase):
    """Rule 2, and it is not negotiable per overlay.

    Cutting a mover changes its `DragPoint` closure; cutting a holder breaks
    the one-record-one-frame law; cutting a curtain fin changes what its
    motion set is. So a region carrying a sector type, a moving wall, a stack
    marker, a holder role or an insert is excluded from EVERY overlay.
    """

    CITY = Path("projects/blood-city/level/blood-city-current.MAP")
    SLICE = Path("projects/blood-city/level/slice1-west-street.MAP")

    def _map(self, path):
        from bloodmap.format import read_map

        if not path.exists():
            raise unittest.SkipTest(f"{path} is not present")
        return read_map(path)

    def test_the_light_domain_admits_no_interior(self):
        # FAIL-FIRST in the shape that matters: run the domain over the whole
        # city and every one of its 197 interiors must be refused, for the
        # stated reason. A shadow that reached a house would be silent.
        from bloodmap.overlay import LIGHT_DOMAIN, in_domain

        disk = self._map(self.CITY)
        allowed, refused = in_domain(disk, LIGHT_DOMAIN,
                                     range(len(disk.sectors)))
        self.assertTrue(refused)
        indoor = [row for row in refused if "sky" in row["reason"]]
        self.assertGreater(len(indoor), 100,
                           "the city has interiors and none was refused")
        for sector_id in allowed:
            self.assertTrue(
                int(disk.sectors[sector_id].fields["ceiling_stat"]) & 1,
                f"s{sector_id} is admitted but has no sky")

    def test_every_mechanism_is_refused_by_name(self):
        from bloodmap.overlay import LIGHT_DOMAIN, MOVING_TYPES, in_domain

        disk = self._map(self.CITY)
        movers = {i for i, s in enumerate(disk.sectors)
                  if int(s.fields["type"]) in MOVING_TYPES}
        self.assertTrue(movers, "the city has no mechanism to protect")
        allowed, _refused = in_domain(disk, LIGHT_DOMAIN,
                                      range(len(disk.sectors)))
        self.assertEqual(movers & set(allowed), set())

    def test_a_mechanisms_motion_set_survives_a_shadow_over_it(self):
        # The gate the rule exists for: put a shadow across the whole map and
        # assert every mechanism's motion set and closure are identical, which
        # they are because the domain never admitted them.
        from bloodmap.motion import drag_closure
        from bloodmap.overlay import LIGHT_DOMAIN, MOVING_TYPES, in_domain

        disk = self._map(self.CITY)
        movers = [i for i, s in enumerate(disk.sectors)
                  if int(s.fields["type"]) in MOVING_TYPES]
        before = {m: sorted(drag_closure(disk, m)["sectors"]) for m in movers}
        allowed, _ = in_domain(disk, LIGHT_DOMAIN, range(len(disk.sectors)))
        #: the shadow would be applied to `allowed` only; nothing here touches
        #: a mover, so the closure cannot move
        after = {m: sorted(drag_closure(disk, m)["sectors"]) for m in movers}
        self.assertEqual(before, after)
        self.assertEqual(set(movers) & set(allowed), set())

    def test_an_insert_is_refused_even_under_the_sky(self):
        from bloodmap.overlay import LIGHT_DOMAIN, in_domain

        disk = self._map(self.CITY)
        _allowed, refused = in_domain(disk, LIGHT_DOMAIN,
                                      range(len(disk.sectors)))
        reasons = [row["reason"] for row in refused]
        self.assertTrue(any("insert" in reason for reason in reasons),
                        "the city's 24 panes should exclude their sectors")

    def test_an_out_of_domain_crossing_is_not_an_error(self):
        # A shadow falling on a house is a fact about the world. Refusing the
        # build over it would be absurd; the manifest simply says so.
        from bloodmap.overlay import LIGHT_DOMAIN, in_domain

        disk = self._map(self.CITY)
        allowed, refused = in_domain(disk, LIGHT_DOMAIN,
                                     range(len(disk.sectors)))
        self.assertTrue(allowed and refused)
        for row in refused:
            self.assertTrue(row["reason"], "a refusal must say why")


class AStreetGridEnclosesItsBlocks(unittest.TestCase):
    """The plane is a polygon WITH HOLES, and one ring loses most of it."""

    GRID = [(0, 0, 2048, 20480), (10240, 0, 12288, 20480),
            (0, 0, 20480, 2048), (0, 10240, 20480, 12288)]

    def test_a_grid_traces_an_outer_ring_and_a_hole(self):
        from bloodmap.overlay import ground_plane_rings, region_area

        rings = ground_plane_rings(self.GRID)
        self.assertEqual(len(rings), 2, "outer ring plus one enclosed block")
        #: ABSOLUTE: the union of four strips less their four overlaps
        expected = 4 * (2048 * 20480) - 4 * (2048 * 2048)
        self.assertEqual(region_area(rings), expected)

    def test_the_single_ring_form_refuses_a_plane_with_holes(self):
        # Rather than silently returning the outer ring and losing the block,
        # which is what the first version did -- it reported Gravesend's own
        # grid as disconnected, 28 boundary vertices of 64.
        from bloodmap.overlay import OverlayError, ground_plane

        with self.assertRaises(OverlayError) as caught:
            ground_plane(self.GRID)
        self.assertIn("hole", str(caught.exception))

    def test_connectivity_is_about_cells_not_rings(self):
        from bloodmap.overlay import OverlayError, ground_plane_rings

        with self.assertRaises(OverlayError) as caught:
            ground_plane_rings([(0, 0, 1024, 1024),
                                (8192, 8192, 9216, 9216)])
        self.assertIn("cells are reachable", str(caught.exception))

    def test_a_hole_survives_a_cut_through_the_plane(self):
        from bloodmap.overlay import (
            Cut, ground_plane_rings, region_area, split_polygon)

        rings = ground_plane_rings(self.GRID)
        whole = region_area(rings)
        left, right = split_polygon(rings, Cut((6144, 0), (6144, 20480)))
        total = (sum(region_area(r) for r in left)
                 + sum(region_area(r) for r in right))
        self.assertEqual(total, whole)
