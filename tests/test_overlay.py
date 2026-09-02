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
