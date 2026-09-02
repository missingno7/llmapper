"""Light as a field, and the shadow as one of its iso-lines.

Sources sum; the field is quantised; the cut set is where the level changes.
A lamp inside a shadow then resolves itself -- shadow plus lamp -- with no
pairwise rule for anybody to write.

The quantisation is `base + k * 12`, and 12 is re-measured here rather than
inherited: over the 38 campaign maps with outdoor ground, the 402 same-z
outdoor boundaries where the shade changes have a MEDIAN delta of exactly 12.
It is not a mode -- the distribution is flat, the commonest value takes 9% --
which is why the gate is the interval [8, 16], where half of them lie.
"""

import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")


def _resolution():
    import sys

    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))
    try:
        import resolution
    except ImportError as error:                       # pragma: no cover
        raise unittest.SkipTest(str(error))
    return resolution


def _plane():
    from bloodmap.overlay import ground_plane

    w, length = 5120, 20480
    a, b = length // 2 - w // 2, length // 2 + w // 2
    return ground_plane([(a, 0, b, length), (0, a, length, b)]), length


class TheStepIsMeasuredNotInherited(unittest.TestCase):
    def test_the_constants_are_the_measured_ones(self):
        from bloodmap.light_field import MAX_LEVELS, STEP, STEP_ENVELOPE

        self.assertEqual(STEP, 12)
        self.assertEqual(STEP_ENVELOPE, (8, 16))
        self.assertEqual(MAX_LEVELS, 4)

    def test_the_campaigns_median_outdoor_shade_delta_is_the_step(self):
        # ABSOLUTE, and re-derived from the corpus inside the test so the
        # constant cannot drift away from its evidence.
        import statistics

        from bloodmap.format import read_map
        from bloodmap.light_field import STEP, STEP_ENVELOPE
        from bloodmap.patterns import list_corpus_maps
        from bloodmap.texture_frame import sector_index

        entries = list(list_corpus_maps(population="blood-campaign"))
        if not entries:
            self.skipTest("no campaign corpus")
        deltas = []
        for entry in entries:
            disk = read_map(entry.path)
            owners = sector_index(disk)
            outdoor = {i for i, s in enumerate(disk.sectors)
                       if int(s.fields["ceiling_stat"]) & 1}
            seen = set()
            for index, wall in enumerate(disk.walls):
                nxt = int(wall.fields["next_sector"])
                if nxt < 0:
                    continue
                here = owners[index]
                if here not in outdoor or nxt not in outdoor:
                    continue
                key = (min(here, nxt), max(here, nxt))
                if key in seen:
                    continue
                a, b = disk.sectors[here].fields, disk.sectors[nxt].fields
                if int(a["floor_z"]) != int(b["floor_z"]):
                    continue
                delta = abs(int(a["floor_shade"]) - int(b["floor_shade"]))
                if delta:
                    seen.add(key)
                    deltas.append(delta)
        self.assertGreater(len(deltas), 300)
        self.assertEqual(statistics.median(deltas), STEP)
        inside = sum(1 for d in deltas
                     if STEP_ENVELOPE[0] <= d <= STEP_ENVELOPE[1])
        self.assertGreaterEqual(inside / len(deltas), 0.45,
                                "half the corpus should lie in the envelope")

    def test_the_step_has_no_mode_worth_the_name(self):
        # The claim the decision rested on, checked: 16 appears most and takes
        # only 9% of the boundaries. Recorded as a test because a later reader
        # would otherwise assume "the modal step" was measured that way.
        from collections import Counter

        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps
        from bloodmap.texture_frame import sector_index

        entries = list(list_corpus_maps(population="blood-campaign"))
        if not entries:
            self.skipTest("no campaign corpus")
        deltas = Counter()
        for entry in entries:
            disk = read_map(entry.path)
            owners = sector_index(disk)
            outdoor = {i for i, s in enumerate(disk.sectors)
                       if int(s.fields["ceiling_stat"]) & 1}
            seen = set()
            for index, wall in enumerate(disk.walls):
                nxt = int(wall.fields["next_sector"])
                if nxt < 0:
                    continue
                here = owners[index]
                if here not in outdoor or nxt not in outdoor:
                    continue
                key = (min(here, nxt), max(here, nxt))
                if key in seen:
                    continue
                a, b = disk.sectors[here].fields, disk.sectors[nxt].fields
                if int(a["floor_z"]) != int(b["floor_z"]):
                    continue
                delta = abs(int(a["floor_shade"]) - int(b["floor_shade"]))
                if delta:
                    seen.add(key)
                    deltas[delta] += 1
        top, count = deltas.most_common(1)[0]
        self.assertLess(count / sum(deltas.values()), 0.15,
                        "if a real mode ever appears, the gate should become "
                        "that number instead of the interval")


class TheFieldCutsAPlane(unittest.TestCase):
    def test_two_masses_give_two_levels_and_conserve_the_area(self):
        from bloodmap.light_field import Mass, build_field, shade_for
        from bloodmap.overlay import region_area

        resolution = _resolution()
        plane, _length = _plane()
        whole = region_area([plane])
        masses = [Mass("m1", ((0, 0), (4096, 0), (4096, 3072), (0, 3072)),
                       4 * 16960),
                  Mass("m2", ((14336, 0), (18432, 0), (18432, 3072),
                              (14336, 3072)), 4 * 16960)]
        found = build_field([plane], masses,
                            bearing_units=resolution.SUN_BEARING)
        self.assertEqual(found["levels"], [0, 1])
        self.assertEqual(sum(p.area for p in found["pieces"]), whole)
        shades = sorted({shade_for(8, p.depth) for p in found["pieces"]})
        self.assertEqual(shades, [8, 20], "base and base + one step")

    def test_every_iso_line_runs_at_the_suns_bearing(self):
        import math

        from bloodmap.light_field import Mass, build_field, edges_of

        resolution = _resolution()
        plane, _length = _plane()
        masses = [Mass("m1", ((0, 0), (4096, 0), (4096, 3072), (0, 3072)),
                       4 * 16960)]
        found = build_field([plane], masses,
                            bearing_units=resolution.SUN_BEARING)
        edges = edges_of(found["pieces"])
        self.assertTrue(edges, "the field produced no iso-line")
        for start, end in edges:
            angle = math.degrees(math.atan2(end[1] - start[1],
                                            end[0] - start[0])) % 180.0
            gap = min(abs(angle - resolution.SUN_BEARING_DEGREES),
                      180.0 - abs(angle - resolution.SUN_BEARING_DEGREES))
            self.assertLessEqual(
                gap, resolution.SUN_BEARING_TOLERANCE_DEGREES,
                f"an iso-line at {angle:.1f} is not this sun's")

    def test_the_depth_is_capped_at_the_campaigns_four_levels(self):
        from bloodmap.light_field import MAX_LEVELS, Mass, build_field

        resolution = _resolution()
        plane, _length = _plane()
        masses = [Mass(f"m{i}", ((i * 1024, 0), (i * 1024 + 512, 0),
                                 (i * 1024 + 512, 2048), (i * 1024, 2048)),
                       4 * 16960) for i in range(8)]
        found = build_field([plane], masses,
                            bearing_units=resolution.SUN_BEARING)
        self.assertLessEqual(max(found["levels"]), MAX_LEVELS - 1)

    def test_a_field_with_too_many_levels_is_a_fault(self):
        from bloodmap.light_field import Piece, field_faults

        pieces = [Piece(rings=[[(0, 0), (10, 0), (10, 10)]], depth=k)
                  for k in range(6)]
        found = field_faults(pieces, base=8)
        self.assertTrue(any("light levels" in line for line in found))

    def test_a_step_outside_the_envelope_is_a_fault(self):
        from bloodmap.light_field import Piece, field_faults

        pieces = [Piece(rings=[[(0, 0), (10, 0), (10, 10)]], depth=k)
                  for k in range(2)]
        self.assertTrue(field_faults(pieces, base=8, step=40))
        self.assertEqual(field_faults(pieces, base=8, step=12), [])


class TheObliqueRoundingRegression(unittest.TestCase):
    """The bug the sun found, and the first tests did not.

    A crossing is computed in rationals and rounded to Build's integer grid,
    and the rounded point is then more than `ON_LINE` off the line it was cut
    on -- the cross product magnifies half a unit of rounding by the segment's
    length. Re-deriving "is this on the line" from `_side` afterwards answered
    no, so the chord was never built, the chain dangled and BOTH sides came
    back empty.

    Axis-aligned cuts and a 45-degree one land exactly on integers, which is
    why the clipper's first tests passed and the sun's 84 degrees did not.
    """

    def test_an_oblique_cut_at_the_suns_bearing_splits_the_plane(self):
        from bloodmap.overlay import Cut, region_area, signed_area, split_polygon

        plane, _length = _plane()
        whole = abs(signed_area(plane))
        left, right = split_polygon([plane], Cut((4096, 0), (11160, 67471)))
        self.assertTrue(left, "the left side came back empty")
        self.assertTrue(right, "the right side came back empty")
        total = (sum(region_area(r) for r in left)
                 + sum(region_area(r) for r in right))
        self.assertEqual(total, whole)

    def test_a_cut_whose_crossings_land_off_the_integer_grid(self):
        # A deliberately awkward slope through a plain square.
        from bloodmap.overlay import Cut, region_area, split_polygon

        square = [(0, 0), (10000, 0), (10000, 10000), (0, 10000)]
        left, right = split_polygon([square], Cut((1, 0), (3331, 10000)))
        total = (sum(region_area(r) for r in left)
                 + sum(region_area(r) for r in right))
        self.assertEqual(total, 10000 * 10000)


if __name__ == "__main__":
    unittest.main()
