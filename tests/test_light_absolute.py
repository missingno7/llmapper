"""The absolute light gate: four numbers read off a compiled map.

Every gate in slice 2d checked the light field's SHAPE -- how many levels, at
what bearing, with what step interval -- and not one of them checked the shade
a sector actually ends up with. That is exactly the hole the 8x texture
regression went through: every relative check green, one absolute number
nobody looked at.

So: a fixture compiled end to end, and four shades read off the built sectors.

    full sun                 base
    one shadow               base + 12
    two overlapping shadows  base + 24
    under a lamp in full sun base minus the lamp's delta

The decided conversion is that a piece at field depth k contributes exactly
`k * 12` to the additive shade channel and the base is the region's own lit
shade from the plan. These tests are what makes that a fact about the built
map rather than an assumption about the code.
"""

import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")
BASE = 8
STEP = 12
LAMP_DELTA = -6


def _resolution():
    import sys

    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))
    try:
        import resolution
    except ImportError as error:                       # pragma: no cover
        raise unittest.SkipTest(str(error))
    return resolution


def _fixture(step=STEP):
    """A plane, two islands, two masses whose shadows overlap, one lamp.

    Compiled end to end through `PlanarLayout`, so the shades asserted are
    read off Build sectors and not off a dictionary in a test.
    """
    from bloodmap.channels import RegionLedger
    from bloodmap.light_field import Mass, build_field
    from bloodmap.lightbomb import apply_shade_channel
    from bloodmap.overlay import ground_plane
    from bloodmap.planar_layout import PlanarLayout

    resolution = _resolution()
    road_z, sky = 10240, 196608
    width, length = 6144, 40960
    a, b = 12288, 12288 + width

    plane = ground_plane([(a, 0, b, length)])
    layout = PlanarLayout(name="light-fixture")

    #: Two masses standing west of the road, close enough in x that their
    #: shadows overlap where they cross it. The sun runs at 84 degrees, so a
    #: shadow drifts about 7100 in x over 67500 in y.
    masses = [Mass("m_south", ((4096, 2048), (10240, 2048),
                               (10240, 6144), (4096, 6144)), 4 * 16960),
              Mass("m_north", ((4096, 8192), (10240, 8192),
                               (10240, 12288), (4096, 12288)), 4 * 16960)]
    field = build_field([plane], masses,
                        bearing_units=resolution.SUN_BEARING)

    ledger = RegionLedger()
    names = []
    for index, piece in enumerate(field["pieces"]):
        name = f"road:{index}"
        layout.add_region(name, piece.rings[0],
                          holes=piece.rings[1:],
                          floor_z=road_z, ceiling_z=road_z - sky,
                          floor_picnum=352, ceiling_picnum=3491,
                          wall_picnum=6, floor_shade=BASE,
                          parallax_ceiling=True, role="street")
        names.append((name, piece.depth))
    #: joins between every pair of pieces that share a wall
    for i, (a_name, _da) in enumerate(names):
        for b_name, _db in names[i + 1:]:
            edge = _shared(layout.regions[a_name].outer,
                           layout.regions[b_name].outer)
            if edge is not None:
                layout.add_connection(f"cut:{a_name}:{b_name}", a_name,
                                      b_name, role="portal",
                                      a1=edge[0], a2=edge[1])
    #: The centroid of the piece, not the road's midpoint: the shadow cuts
    #: are oblique, so a piece is a trapezoid and the middle of the road is
    #: routinely outside whichever piece was picked.
    start_name = next((name for name, depth in names if depth == 0),
                      names[0][0])
    ring = layout.regions[start_name].outer
    spot = (sum(p[0] for p in ring) // len(ring),
            sum(p[1] for p in ring) // len(ring))
    layout.set_player_start(start_name, x=int(spot[0]), y=int(spot[1]),
                            z=road_z, angle=0)
    compiled = layout.compile()
    disk = compiled.level.to_disk_map()

    #: the field's contributions, at the decided conversion
    by_sector = {}
    for name, depth in names:
        sector = compiled.allocations[name].sector_id
        by_sector[sector] = depth
        if depth:
            ledger.write(str(sector), "shade", "sun:field", depth * step,
                         intent="presentation")
    #: one lamp, on a sector in full sun
    lamp_sector = next((s for s, d in by_sector.items() if d == 0), None)
    if lamp_sector is not None:
        ledger.write(str(lamp_sector), "shade", "lamp:0", LAMP_DELTA,
                     intent="presentation")
    apply_shade_channel(disk, ledger)
    return disk, by_sector, lamp_sector, field


def _shared(a, b):
    for index, point in enumerate(a):
        nxt = a[(index + 1) % len(a)]
        for other, start in enumerate(b):
            end = b[(other + 1) % len(b)]
            if {tuple(point), tuple(nxt)} == {tuple(start), tuple(end)}:
                return (tuple(point), tuple(nxt))
    return None


class FourNumbersOffTheBuiltMap(unittest.TestCase):
    def setUp(self):
        self.disk, self.depths, self.lamp, self.field = _fixture()

    def test_the_fixture_really_has_two_overlapping_shadows(self):
        # Without this the other assertions could pass on a map that never
        # reached depth 2, which is the shape of "a gate that cannot fail".
        self.assertIn(2, set(self.depths.values()),
                      f"depths built: {sorted(set(self.depths.values()))}")

    def test_full_sun_is_the_base(self):
        lit = [s for s, d in self.depths.items() if d == 0 and s != self.lamp]
        self.assertTrue(lit, "no sector in full sun without a lamp")
        for sector in lit:
            self.assertEqual(
                int(self.disk.sectors[sector].fields["floor_shade"]), BASE,
                f"s{sector} is in full sun and should read {BASE}")

    def test_one_shadow_is_the_base_plus_twelve(self):
        ones = [s for s, d in self.depths.items() if d == 1]
        self.assertTrue(ones)
        for sector in ones:
            self.assertEqual(
                int(self.disk.sectors[sector].fields["floor_shade"]),
                BASE + STEP, f"s{sector} is one shadow deep")

    def test_two_overlapping_shadows_are_the_base_plus_twentyfour(self):
        twos = [s for s, d in self.depths.items() if d == 2]
        self.assertTrue(twos)
        for sector in twos:
            self.assertEqual(
                int(self.disk.sectors[sector].fields["floor_shade"]),
                BASE + 2 * STEP, f"s{sector} is two shadows deep")

    def test_the_lamp_brightens_the_sector_it_stands_on(self):
        self.assertIsNotNone(self.lamp, "no lit sector to stand a lamp on")
        self.assertEqual(
            int(self.disk.sectors[self.lamp].fields["floor_shade"]),
            BASE + LAMP_DELTA,
            "a lamp in full sun is the base minus its own delta")


class TheGateSpeaksWhenTheConversionBreaks(unittest.TestCase):
    """FAIL-FIRST: break k*12 into k and watch the shape gates stay green."""

    def test_a_broken_conversion_is_caught_by_the_absolute_gate(self):
        disk, depths, _lamp, _field = _fixture(step=1)
        ones = [s for s, d in depths.items() if d == 1]
        self.assertTrue(ones)
        found = int(disk.sectors[ones[0]].fields["floor_shade"])
        self.assertNotEqual(found, BASE + STEP,
                            "the broken fixture should not read correctly")
        self.assertEqual(found, BASE + 1,
                         "k instead of k*12 is the defect being modelled")

    def test_and_every_shape_gate_stays_green_on_the_broken_map(self):
        # The point of the whole exercise. The field's shape is untouched by
        # the conversion, so levels, bearings and the step envelope all pass
        # while the city is one step too dark.
        import math

        from bloodmap.light_field import edges_of, field_faults

        resolution = _resolution()
        _disk, _depths, _lamp, field = _fixture(step=1)
        self.assertEqual(field_faults(field["pieces"], base=BASE), [],
                         "the shape gate should be blind to this")
        for start, end in edges_of(field["pieces"]):
            angle = math.degrees(math.atan2(end[1] - start[1],
                                            end[0] - start[0])) % 180.0
            gap = min(abs(angle - resolution.SUN_BEARING_DEGREES),
                      180.0 - abs(angle - resolution.SUN_BEARING_DEGREES))
            self.assertLessEqual(gap,
                                 resolution.SUN_BEARING_TOLERANCE_DEGREES)


if __name__ == "__main__":
    unittest.main()
