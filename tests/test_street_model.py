"""The kerb, once it is a record somebody declared.

P14's first run could not calibrate this gate and said so. Guessing from a
finished map which two-sided steps are kerbs picks up harbour walls, ledges
and rooftops; the campaign's outdoor kerb tiles are diverse (2490, 67, 110,
2499, 6... the top eight sharing 43% of 1046 records); and the narrower clause
"never the material above it" scored the campaign at 16% against the city's
0%, so the city was already better by it.

`overlay.HeightIsland` changes the question. A kerb is now a record the model
DECLARES, so the rule is about a stated population rather than an inferred
one, it needs no corpus threshold, and it is exact -- the same shape as P13's
record-ownership ledger. That closes owner-queue item 18.

The absolute check beside it (item 17): the rise is 2048, E3M1's on 11 of 11,
asserted as a number and not as "consistent with its neighbours".
"""

import unittest
from pathlib import Path

CITY = Path("projects/blood-city/level/blood-city-current.MAP")
SLICE = Path("projects/blood-city/level/slice1-west-street.MAP")


def _map(path):
    from bloodmap.format import read_map

    if not path.exists():
        raise unittest.SkipTest(f"{path} is not present")
    return read_map(path)


def _road_pieces(disk):
    return [i for i, s in enumerate(disk.sectors)
            if int(s.fields["floor_picnum"]) == 352]


class TheKerbIsWhatABodyOnTheRoadSees(unittest.TestCase):
    """The owner's acceptance test, as a reading."""

    def test_the_committed_city_shows_a_body_the_house(self):
        # FAIL-FIRST, and it is not close: of the 74 faces standing up around
        # blood-city's outdoor sectors, none wears a kerb tile. They wear 380,
        # 417, 384, 28, 393 and 400 -- facade stone, because the band was a
        # hole's edge in a street residue and inherited the building.
        from bloodmap.street_model import sees_the_kerb
        from bloodmap.texture_frame import sector_index

        disk = _map(CITY)
        owners = sector_index(disk)
        outdoor = [i for i, s in enumerate(disk.sectors)
                   if int(s.fields["ceiling_stat"]) & 1]
        tiles = set()
        faces = 0
        for sector_id in outdoor:
            view = sees_the_kerb(disk, sector_id, owners)
            faces += len(view["faces"])
            tiles.update(view["kerb_tiles"])
        self.assertGreater(faces, 50, "nothing to look at")
        self.assertNotIn(6, tiles,
                         "if this ever fails the city has been rebuilt and "
                         "this fixture should become the positive one")

    def test_the_slice_shows_a_body_the_kerb(self):
        from bloodmap.street_model import sees_the_kerb
        from bloodmap.texture_frame import sector_index

        disk = _map(SLICE)
        owners = sector_index(disk)
        roads = _road_pieces(disk)
        self.assertTrue(roads, "the slice has no road")
        for sector_id in roads:
            view = sees_the_kerb(disk, sector_id, owners)
            self.assertEqual(view["kerb_tiles"], [6], f"road s{sector_id}")
            self.assertEqual(view["materials_above"], [4],
                             "and what stands above the kerb is pavement")


class TheDeclaredKerbRule(unittest.TestCase):
    def _declared(self, disk):
        """Every road/pavement boundary in the slice, as the build declares."""
        from bloodmap.texture_frame import sector_index

        owners = sector_index(disk)
        out = []
        for wall_id, wall in enumerate(disk.walls):
            nxt = int(wall.fields["next_sector"])
            if nxt < 0:
                continue
            here = owners[wall_id]
            if int(disk.sectors[here].fields["floor_picnum"]) != 352:
                continue
            if int(disk.sectors[nxt].fields["floor_picnum"]) != 4:
                continue
            face = wall.fields
            after = disk.walls[int(face["point2"])].fields
            out.append({
                "island": f"s{nxt}", "road_piece": f"s{here}",
                "edge": ((int(face["x"]), int(face["y"])),
                         (int(after["x"]), int(after["y"]))),
                "picnum": 6, "rise": 2048})
        return out, owners

    def test_the_slices_declared_kerbs_all_pass(self):
        from bloodmap.street_model import kerb_faults

        disk = _map(SLICE)
        declared, owners = self._declared(disk)
        self.assertTrue(declared, "the slice declares no kerb")
        self.assertEqual(kerb_faults(disk, declared, owners=owners), [])

    def test_a_kerb_wearing_the_pavement_is_a_fault(self):
        # The owner's middle clause: a kerb is not the pavement folded down.
        from bloodmap.street_model import kerb_faults

        disk = _map(SLICE)
        declared, owners = self._declared(disk)
        target = declared[0]
        for wall in disk.walls:
            face = wall.fields
            after = disk.walls[int(face["point2"])].fields
            if ((int(face["x"]), int(face["y"])),
                    (int(after["x"]), int(after["y"]))) == target["edge"]:
                face["picnum"] = 4
        found = kerb_faults(disk, declared, owners=owners)
        self.assertTrue(found)
        self.assertTrue(any("standing above it" in line for line in found),
                        found)

    def test_the_rise_is_checked_absolutely(self):
        # ABSOLUTE: 2048, E3M1's on 11 of 11 kerbs. A kerb consistent with its
        # neighbours at 512 would pass any relative form of this.
        from bloodmap.street_model import KERB_RISE, kerb_faults

        self.assertEqual(KERB_RISE, 2048)
        disk = _map(SLICE)
        declared, owners = self._declared(disk)
        for sector in disk.sectors:
            if int(sector.fields["floor_picnum"]) == 4:
                sector.fields["floor_z"] = int(sector.fields["floor_z"]) + 1536
        found = kerb_faults(disk, declared, owners=owners)
        self.assertTrue(any("steps" in line for line in found), found)


class TheShadowRunsAtTheLevelsSun(unittest.TestCase):
    def test_an_edge_at_the_bearing_passes_and_an_axis_edge_does_not(self):
        from bloodmap.street_model import shadow_edge_faults

        import sys
        level = str(Path("projects/blood-city/level"))
        if level not in sys.path:
            sys.path.insert(0, level)
        try:
            from resolution import (SUN_BEARING_DEGREES,
                                    SUN_BEARING_TOLERANCE_DEGREES)
        except ImportError as error:                   # pragma: no cover
            self.skipTest(str(error))
        disk = _map(SLICE)
        good = [((0, 0), (416, 4096))]
        bad = [((0, 0), (4096, 0))]
        self.assertEqual(shadow_edge_faults(disk, good, SUN_BEARING_DEGREES,
                                            SUN_BEARING_TOLERANCE_DEGREES), [])
        self.assertTrue(shadow_edge_faults(disk, bad, SUN_BEARING_DEGREES,
                                           SUN_BEARING_TOLERANCE_DEGREES))


class TheFrameSurvivesTheCuts(unittest.TestCase):
    """The property the whole overlay model exists to give."""

    def test_the_editor_would_change_nothing_after_a_kerb_and_shadow_cut(self):
        from bloodmap.texture_align import wall_art_sizes
        from bloodmap.texture_frame import (
            auto_align_walls, run_partition, sector_index)

        art = wall_art_sizes()
        if not art:
            self.skipTest("no ART in reference/blood")
        disk = _map(SLICE)
        owners = sector_index(disk)
        keys = ("x_repeat", "x_panning", "y_repeat", "y_panning", "cstat")
        moved = 0
        for run in run_partition(disk, art_sizes=art, owners=owners):
            before = {w: {k: int(disk.walls[w].fields[k]) for k in keys}
                      for w in run}
            auto_align_walls(disk, run[0], flags=0x01, art_sizes=art,
                             owners=owners)
            moved += sum(1 for w in run
                         if any(int(disk.walls[w].fields[k]) != before[w][k]
                                for k in keys))
        self.assertEqual(moved, 0,
                         "a road cut by a kerb and a shadow must still be a "
                         "fixed point of the editor's own align")

    def test_the_road_is_drawn_at_the_campaigns_size(self):
        # ABSOLUTE, and the check P13 added after shipping an 8x map: texels
        # per sixteen world units, median 1.00 over the campaign.
        from bloodmap import rules_blood                       # noqa: F401
        from bloodmap.rules import RULES
        from bloodmap.texture_align import wall_art_sizes

        if not wall_art_sizes():
            self.skipTest("no ART in reference/blood")
        finding = RULES["material-is-drawn-at-campaign-size"].check(_map(SLICE))
        self.assertEqual(finding.violations, ())


if __name__ == "__main__":
    unittest.main()


class ARoadHasAnEnd(unittest.TestCase):
    """E3M1's terminations, measured on s0, s339 and s343.

    A road does not end at a building and it does not end at a kerb. E3M1
    ends its streets against a raised mass whose floor IS the top of the wall:
    a stone face across the road with a strip of sky above it.
    """

    def test_the_dialect_is_e3m1s(self):
        from bloodmap.street import (
            END_WALL_CSTAT_BLOCKING, END_WALL_FLOOR_TILE, END_WALL_Y_REPEAT,
            end_wall)

        found = end_wall([(0, 0), (1024, 0), (1024, 4096), (0, 4096)],
                         road_floor_z=10240, standing_height=16960,
                         facade_tile=400)
        self.assertEqual(found["floor_picnum"], END_WALL_FLOOR_TILE)
        self.assertEqual(found["ceiling_picnum"], 3491)
        self.assertTrue(found["parallax_ceiling"])
        self.assertEqual(found["face_cstat"], END_WALL_CSTAT_BLOCKING)
        self.assertEqual(found["face_y_repeat"], END_WALL_Y_REPEAT)
        self.assertEqual(found["face_picnum"], 400)

    def test_e3m1s_three_terminations_read_as_the_dialect(self):
        # ABSOLUTE, off the map: floor 379, sky ceiling 3491 parallaxed, and
        # blocking faces. Read rather than trusted.
        from bloodmap.format import read_map
        from bloodmap.patterns import list_corpus_maps
        from bloodmap.street import END_WALL_FLOOR_TILE

        found = [e for e in list_corpus_maps(population="blood-campaign")
                 if e.path.stem.upper() == "E3M1"]
        if not found:
            self.skipTest("E3M1 is not in the corpus")
        disk = read_map(found[0].path)
        for sector_id in (0, 339, 343):
            fields = disk.sectors[sector_id].fields
            self.assertEqual(int(fields["floor_picnum"]),
                             END_WALL_FLOOR_TILE, sector_id)
            self.assertEqual(int(fields["ceiling_picnum"]), 3491, sector_id)
            self.assertTrue(int(fields["ceiling_stat"]) & 1, sector_id)

    def test_a_termination_outside_e3m1s_band_is_a_fault(self):
        # It can fail: a wall a body could step over is not the end of a
        # street. E3M1's three stand 3.86 to 5.80 player heights up.
        from bloodmap.street import end_wall, termination_faults

        low = end_wall([(0, 0), (1024, 0), (1024, 4096), (0, 4096)],
                       road_floor_z=10240, standing_height=16960,
                       facade_tile=400, rise_bodies=0.5)
        found = termination_faults(None, [low], standing_height=16960)
        self.assertTrue(found)
        self.assertIn("above the road", found[0])

    def test_a_termination_you_could_walk_up_is_a_fault(self):
        from bloodmap.street import end_wall, termination_faults

        found = end_wall([(0, 0), (1024, 0), (1024, 4096), (0, 4096)],
                         road_floor_z=10240, standing_height=16960,
                         facade_tile=400)
        found["face_cstat"] = 0
        faults = termination_faults(None, [found], standing_height=16960)
        self.assertTrue(any("may not walk up" in line for line in faults))


class TheSkyIsAMaterial(unittest.TestCase):
    def test_the_slice_wears_a_sky_tile_on_every_parallax_ceiling(self):
        # The defect slice 1 shipped: every parallaxed ceiling wore its own
        # floor's tile, and `parallax-wears-a-sky-tile` reported all five.
        # The law was there; the slice had never been run through the gates
        # the city build runs.
        from bloodmap import rules_blood                       # noqa: F401
        from bloodmap.rules import RULES

        disk = _map(SLICE)
        for rule_id in ("parallax-wears-a-sky-tile",
                        "tile-sits-in-an-attested-slot"):
            finding = RULES[rule_id].check(disk)
            self.assertEqual(finding.violations, (), rule_id)


class TheReaderSideOfTheGroundModel(unittest.TestCase):
    """Every writer has a reader, and the reader says what it cannot recover.

    A value only the emitter knows is a claim nobody can check, so `read_city`
    reports its blind spots by name beside the numbers it does recover.
    """

    @staticmethod
    def _city():
        """A road split by one shadow, and two islands joined by a path."""
        from bloodmap.planar_layout import PlanarLayout

        layout = PlanarLayout(name="reader-fixture")
        sky = 3491
        # two road pieces, one lit and one in shadow, meeting on an OBLIQUE
        # edge at the sun's bearing (atan2(4096, 416) = 84.2 degrees)
        layout.add_region("road_lit", [(0, 0), (8608, 0), (8192, 4096),
                                       (0, 4096)],
                          floor_z=10240, ceiling_z=10240 - 6 * 32768,
                          floor_picnum=352, ceiling_picnum=sky,
                          wall_picnum=6, floor_shade=8,
                          parallax_ceiling=True, role="street")
        layout.add_region("road_dark", [(8608, 0), (16384, 0), (16384, 4096),
                                        (8192, 4096)],
                          floor_z=10240, ceiling_z=10240 - 6 * 32768,
                          floor_picnum=352, ceiling_picnum=sky,
                          wall_picnum=6, floor_shade=20,
                          parallax_ceiling=True, role="street")
        for name, x0, x1 in (("island_a", 0, 8192), ("island_b", 8192, 16384)):
            layout.add_region(name, [(x0, 4096), (x1, 4096), (x1, 12288),
                                     (x0, 12288)],
                              floor_z=8192, ceiling_z=8192 - 6 * 32768,
                              floor_picnum=4, ceiling_picnum=sky,
                              wall_picnum=4, floor_shade=8,
                              parallax_ceiling=True, role="street")
        layout.add_connection("shadow", "road_lit", "road_dark", role="portal",
                              a1=(8608, 0), a2=(8192, 4096))
        layout.add_connection("path", "island_a", "island_b", role="portal",
                              a1=(8192, 4096), a2=(8192, 12288))
        layout.add_connection("kerb_a", "road_lit", "island_a", role="portal",
                              a1=(0, 4096), a2=(8192, 4096))
        layout.add_connection("kerb_b", "road_dark", "island_b", role="portal",
                              a1=(8192, 4096), a2=(16384, 4096))
        layout.set_player_start("road_lit", x=2048, y=2048, z=10240, angle=0)
        return layout.compile().level.to_disk_map()

    def test_it_recovers_one_plane_and_the_shade_levels(self):
        from bloodmap.street_model import read_city

        found = read_city(self._city())
        self.assertEqual(found["planes"], 1)
        self.assertEqual(found["road_sectors"], 2)
        self.assertEqual(found["shade_levels"], [8, 20])

    def test_it_recovers_the_sun_bearing_from_the_iso_line(self):
        from bloodmap.street_model import read_city

        found = read_city(self._city())
        self.assertEqual(found["oblique_iso_lines"], 2)
        self.assertAlmostEqual(found["sun_bearing_degrees"], 84.2, places=1)

    def test_two_islands_on_a_path_read_back_as_one(self):
        # THE NAMED GAP, and it is a real asymmetry rather than a defect: the
        # map records a connected pavement network and not the surfaces the
        # emitter declared.
        from bloodmap.street_model import read_city

        found = read_city(self._city())
        self.assertEqual(found["pavement_sectors"], 2)
        self.assertEqual(found["islands"], 1)
        self.assertTrue(any("surface identity" in gap
                            for gap in found["symmetry_gaps"]))

    def test_the_gaps_are_reported_rather_than_implied(self):
        from bloodmap.street_model import read_city

        found = read_city(self._city())
        self.assertEqual(len(found["symmetry_gaps"]), 3)
        for gap in found["symmetry_gaps"]:
            self.assertIn(":", gap, "each gap is named, then explained")


class TheCircuitIsASequenceOfSurfaces(unittest.TestCase):
    """A leg is the surfaces a body passes through, never a coordinate.

    The plan's legs were points in a 58x56 grid and the envelope solve makes
    72x60, so no leg could be checked against a built map -- and a coordinate
    would not survive the next re-solve either.
    """

    CIRCUIT = (
        {"leg": "start on the quay", "surfaces": ("walk",), "built": True},
        {"leg": "the plaza", "surfaces": ("plane", "plaza"), "built": True},
        {"leg": "the sewer", "surfaces": ("trunk",), "built": False,
         "why": "no sewer is emitted"},
    )
    SURFACES = {"walk": [0], "plane": [1], "plaza": [2]}

    def test_a_circuit_whose_legs_are_all_reachable_is_silent(self):
        from bloodmap.street_model import circuit_faults

        self.assertEqual(
            circuit_faults(None, self.CIRCUIT, self.SURFACES,
                           reachable={0, 1, 2}), [])

    def test_a_leg_that_is_built_and_unreachable_is_named(self):
        # THE FAIL-FIRST: one leg's surface drops out of the reachable set.
        from bloodmap.street_model import circuit_faults

        faults = circuit_faults(None, self.CIRCUIT, self.SURFACES,
                                reachable={0, 1})
        self.assertEqual(len(faults), 1)
        self.assertIn("'the plaza'", faults[0])
        self.assertIn("not reachable at rest", faults[0])

    def test_a_leg_naming_a_surface_the_level_lacks_is_named(self):
        from bloodmap.street_model import circuit_faults

        faults = circuit_faults(None, self.CIRCUIT,
                                {"walk": [0], "plane": [1]},
                                reachable={0, 1})
        self.assertEqual(len(faults), 1)
        self.assertIn("does not have", faults[0])

    def test_an_unbuilt_leg_is_skipped_and_not_a_fault(self):
        from bloodmap.street_model import circuit_faults

        self.assertEqual(
            circuit_faults(None, self.CIRCUIT, self.SURFACES,
                           reachable={0, 1, 2}), [],
            "the sewer leg is declared unbuilt, with its reason")

    def test_the_plan_s_own_circuit_names_surfaces(self):
        import sys
        from pathlib import Path

        level_dir = Path("projects/blood-city/level")
        if not (level_dir / "city_plan.py").exists():  # pragma: no cover
            self.skipTest("the project is not present")
        sys.path.insert(0, str(level_dir))
        try:
            import city_plan
        finally:
            sys.path.remove(str(level_dir))
        self.assertTrue(all("surfaces" in leg for leg in city_plan.CIRCUIT))
        self.assertEqual(sum(1 for leg in city_plan.CIRCUIT
                             if not leg.get("built", True)), 4)
        for leg in city_plan.CIRCUIT:
            if not leg.get("built", True):
                self.assertTrue(leg.get("why"), leg["leg"])
