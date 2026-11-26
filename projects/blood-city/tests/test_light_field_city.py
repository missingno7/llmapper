"""The light field cut at the city's own sun bearing (`resolution.SUN_BEARING`)."""

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


if __name__ == "__main__":
    unittest.main()
