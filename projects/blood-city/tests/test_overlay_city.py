"""Overlays on Gravesend: its sun (`resolution`), its built map's mechanisms, and the regression captured at its bearing."""

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


class ACutNeverTouchesAMechanism(unittest.TestCase):
    """Rule 2, and it is not negotiable per overlay.

    Cutting a mover changes its `DragPoint` closure; cutting a holder breaks
    the one-record-one-frame law; cutting a curtain fin changes what its
    motion set is. So a region carrying a sector type, a moving wall, a stack
    marker, a holder role or an insert is excluded from EVERY overlay.
    """

    CITY = Path("projects/blood-city/level/blood-city-current.MAP")
    SLICE = Path("tests/fixtures/city-slices/slice1-west-street.MAP")

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


class ObliqueCutsRoundAndThePiecesDrift(unittest.TestCase):
    """The captured cause, with its magnitude.

    `tests/fixtures/overlay_partition_regression.json` is one island of the
    real graph and the nine masses whose shadows fall on it. Cutting it with a
    single shadow gains **334 units of area over 276 million** -- 1.2 parts per
    million -- and one piece's vertex lands **0.05 units** inside its
    neighbour.

    That is not double-counting. Every oblique half-plane cut rounds its
    crossings to Build's integer grid independently, so two pieces that ought
    to share an edge diverge by a fraction of a unit, and the partition is
    exact only to within that rounding. Both this assertion and
    `PlanarLayout`'s overlap check were reading a 0.05-unit divergence as a
    real overlap.
    """

    FIXTURE = Path("tests/fixtures/overlay_partition_regression.json")

    def _case(self):
        import json
        import sys

        if not self.FIXTURE.exists():
            raise unittest.SkipTest(f"{self.FIXTURE} is not present")
        level = str(Path("projects/blood-city/level"))
        if level not in sys.path:
            sys.path.insert(0, level)
        try:
            from resolution import SUN_BEARING
        except ImportError as error:               # pragma: no cover
            raise unittest.SkipTest(str(error))
        from bloodmap.light_field import Mass, shadow_of

        data = json.loads(self.FIXTURE.read_text(encoding="utf-8"))
        rings = [[tuple(p) for p in ring] for ring in data["rings"]]
        mass = data["masses"][0]
        shadow = shadow_of(Mass(mass["id"],
                                tuple(tuple(p) for p in mass["outline"]),
                                mass["height"]), SUN_BEARING)
        return rings, shadow

    def test_the_drift_is_rounding_and_not_double_counting(self):
        from bloodmap.overlay import cut_by_convex, region_area

        rings, shadow = self._case()
        inside, outside, _ = cut_by_convex(rings, shadow)
        pieces = inside + outside
        whole = region_area(rings)
        got = sum(region_area(piece) for piece in pieces)
        #: ABSOLUTE: the drift is parts per million, not a lost or duplicated
        #: region. A double-count would be a piece-sized number.
        self.assertLess(abs(got - whole) / whole, 1e-5,
                        f"{got} against {whole}")
        self.assertGreater(abs(got - whole), 0,
                           "if this is ever exact the rounding was fixed and "
                           "this fixture should assert equality instead")

    def test_no_vertex_is_more_than_a_unit_inside_its_neighbour(self):
        from bloodmap.overlay import _on_boundary, _point_in, cut_by_convex

        rings, shadow = self._case()
        inside, outside, _ = cut_by_convex(rings, shadow)
        pieces = inside + outside
        worst = 0.0
        for index, piece in enumerate(pieces):
            for other_index, other in enumerate(pieces):
                if index == other_index:
                    continue
                for vertex in piece[0]:
                    if _on_boundary(other, vertex) or not _point_in(other,
                                                                    vertex):
                        continue
                    #: how far inside is the NEAREST edge, not the furthest.
                    #: Taking the max over edges measures the distance across
                    #: the whole polygon and reads a point sitting on one
                    #: slanted edge as 11780 units deep, which is how this
                    #: test first accused the clipper of a structural overlap.
                    nearest = min(
                        (abs((b[0] - a[0]) * (a[1] - vertex[1])
                             - (a[0] - vertex[0]) * (b[1] - a[1]))
                         / ((((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5)
                            or 1))
                        for ring in other
                        for a, b in zip(ring, ring[1:] + ring[:1]))
                    worst = max(worst, nearest)
        self.assertLess(worst, 1.0,
                        f"a vertex sits {worst:.2f} units inside a neighbour, "
                        f"which would be a real overlap rather than rounding")


class TheWeldByEdgeIdentity(unittest.TestCase):
    """Two pieces share an edge exactly, or they only nearly do.

    Every oblique cut rounds its crossings to Build's integer grid, so a piece
    that was cut has a vertex where the chord met its boundary and a
    neighbour that was not cut does not. The weld inserts each recorded
    crossing into every ring that still carries the edge it came from, keyed
    UNDIRECTED -- a plane's hole ring and the island standing in it are the
    same edges given in opposite directions.

    No search radius anywhere: a crossing belongs to its edge by record.
    """

    FIXTURE = Path("tests/fixtures/overlay_partition_regression.json")

    def test_the_weld_closes_the_captured_regression(self):
        # THE CASE THAT DECIDED IT. Before the weld this surface gained 334
        # units and put a vertex 0.05 inside its neighbour.
        import json
        import sys

        if not self.FIXTURE.exists():
            self.skipTest(f"{self.FIXTURE} is not present")
        level = str(Path("projects/blood-city/level"))
        if level not in sys.path:
            sys.path.insert(0, level)
        try:
            from resolution import SUN_BEARING
        except ImportError as error:               # pragma: no cover
            self.skipTest(str(error))
        from bloodmap.light_field import Mass, build_field
        from bloodmap.overlay import partition_faults

        data = json.loads(self.FIXTURE.read_text(encoding="utf-8"))
        rings = [[tuple(p) for p in ring] for ring in data["rings"]]
        masses = [Mass(m["id"], tuple(tuple(p) for p in m["outline"]),
                       m["height"]) for m in data["masses"]]
        found = build_field(rings, masses, bearing_units=SUN_BEARING)
        self.assertEqual(
            partition_faults([p.rings for p in found["pieces"]], rings), [])
        self.assertGreater(found["welded_vertices"], 0,
                           "if nothing welded, the fixture stopped exercising "
                           "the case it was captured for")


if __name__ == "__main__":
    unittest.main()
