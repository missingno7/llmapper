"""A building is as tall as the sky of the ground in front of it.

These pin the one engine fact `bloodmap.skyline` rests on, as it comes out of
the compiler: a mass face that borders an apron is a wall of the apron's
sector, so it is drawn to the apron's ceiling and not the street's.
"""

import unittest

from bloodmap import skyline
from bloodmap.levelprog import Frame, LevelProgram, LevelProgramError, Style
from bloodmap.slope import SlopeSpec

STREET_SKY = 196608
EAVES = 65536
SKY, STONE, PAVING = 3491, 406, 352


def _street_and_court(court_sky, *, lip=False):
    """A street, and a court off its north side between two buildings."""
    level = LevelProgram("town", style=Style(wall_picnum=384, floor_picnum=PAVING, ceiling_picnum=SKY, parallax_ceiling=True,
                                             floor_z=8192, clear_height=STREET_SKY))
    faces = {"north": 0, "east": 1, "south": 2, "west": 3}

    def room(name, x0, y0, x1, y1, **style):
        made = level.room(name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)], role="exterior", faces=faces, frame=Frame(x0, y0))
        made.surfaces(**style)
        return made

    street = room("street", 0, 0, 16384, 4096)
    court = room("court", 6144, -3072, 10240, 0, clear_height=court_sky)
    level.connect(court.face("south"), street.face("north"), connection_id="connection:mouth")
    if lip:
        strip = room("lip", 6144, -3200, 10240, -3072, clear_height=EAVES)
        level.connect(strip.face("south"), court.face("north"), connection_id="connection:lip")
    level.set_start(street, local=(0.1, 0.5))
    return level.compile().compile().level


class ThinFrontTests(unittest.TestCase):
    def test_a_court_under_a_lower_sky_leaves_its_neighbours_a_blade(self):
        found = skyline.thin_fronts(_street_and_court(EAVES))
        self.assertEqual({(f["x"], f["y"]) for f in found}, {(6144, 0), (10240, 0)})
        self.assertEqual({f["bare"] for f in found}, {STREET_SKY - EAVES})

    def test_the_streets_sky_and_a_lip_are_a_low_front_between_two_solid_buildings(self):
        self.assertEqual(skyline.thin_fronts(_street_and_court(STREET_SKY, lip=True)), [])


def _street_with_a_mass(*, apron_height=EAVES, slope=None):
    """A square street round a square mass, with an apron on its east face."""
    level = LevelProgram(
        "town", style=Style(wall_picnum=384, floor_picnum=PAVING,
                            ceiling_picnum=SKY, parallax_ceiling=True,
                            floor_z=8192, clear_height=STREET_SKY))
    faces = {"north": 0, "east": 1, "south": 2, "west": 3}
    street = level.room("street", [(0, 0), (16384, 0), (16384, 16384),
                                   (0, 16384)], role="exterior", faces=faces,
                        frame=Frame(0, 0))
    # The street gives up the mass AND the strip in front of it, as one hole.
    street.carve([(6144, 6144), (10752, 6144), (10752, 10240), (6144, 10240)])
    strip = skyline.apron(
        level, "eaves", [(10240, 6144), (10752, 6144), (10752, 10240),
                         (10240, 10240)],
        wall_height=apron_height, floor_z=8192, sky_picnum=SKY,
        wall_picnum=STONE, floor_picnum=PAVING, ceiling_slope=slope)
    for name in ("e0", "e1", "e2"):
        level.connect(strip.face(name), street.face("north"),
                      connection_id=f"connection:eaves_{name}")
    level.set_start(street, local=(0.1, 0.1))
    return level, strip


class ApronTests(unittest.TestCase):
    def test_the_face_behind_an_apron_is_drawn_to_the_aprons_sky(self):
        level, strip = _street_with_a_mass()
        compiled = level.compile().compile()
        disk = compiled.level

        rows = skyline.street_wall_heights(disk)
        by_height = {}
        for row in rows:
            by_height.setdefault(row["height"], []).append(row)

        self.assertEqual(sorted(by_height), [EAVES, STREET_SKY])
        # exactly one wall is low: the mass's east face, in the apron's stone
        (low,) = by_height[EAVES]
        fields = disk.walls[low["wall"]]["fields"]
        after = disk.walls[int(fields["point2"])]["fields"]
        self.assertEqual({int(fields["x"]), int(after["x"])}, {10240})
        self.assertEqual(int(fields["picnum"]), STONE)
        sector = disk.sectors[low["sector"]]["fields"]
        self.assertTrue(int(sector["ceiling_stat"]) & 1)

    def test_the_profile_counts_distinct_heights(self):
        level, _strip = _street_with_a_mass()
        profile = skyline.profile(level.compile().compile().level)

        self.assertEqual(profile["distinct_heights"], 2)
        self.assertEqual(profile["tallest"], STREET_SKY)

    def test_a_sky_within_reach_is_refused(self):
        with self.assertRaises(LevelProgramError) as caught:
            _street_with_a_mass(apron_height=skyline.REACH - 1)

        self.assertIn("invisible ceiling", str(caught.exception))

    def test_an_apron_remembers_what_it_is_for(self):
        _level, strip = _street_with_a_mass()

        self.assertEqual(strip.intent["kind"], "sky_apron")
        self.assertEqual(strip.intent["wall_height"], EAVES)

    def test_a_sloped_sky_compiles_to_a_sloped_parallax_ceiling(self):
        hinge = ((10240, 6144), (10752, 6144))
        level, _strip = _street_with_a_mass(
            slope=SlopeSpec(hinge=hinge, rise_z=16384))
        disk = level.compile().compile().level

        sloped = [s["fields"] for s in disk.sectors
                  if int(s["fields"]["ceiling_stat"]) & 1
                  and int(s["fields"]["ceiling_heinum"])]
        self.assertEqual(len(sloped), 1)
        self.assertTrue(int(sloped[0]["ceiling_stat"]) & 2)


class ApertureAuditTests(unittest.TestCase):
    def test_a_step_between_two_skies_is_not_a_lintel(self):
        from bloodmap.aperture import observe_openings

        level, _strip = _street_with_a_mass()
        disk = level.compile().compile().level.to_disk_map()

        rows = observe_openings("fixture", disk)
        self.assertTrue(rows)
        self.assertNotIn("lintel", {row["kind"] for row in rows})
        self.assertEqual({row["lintel_player_heights"] for row in rows}, {0.0})


def _street_with_a_roofed_mass(*, top=EAVES):
    """The same mass, but as a roof: a sector whose floor is its top."""
    level = LevelProgram(
        "town", style=Style(wall_picnum=384, floor_picnum=PAVING,
                            ceiling_picnum=SKY, parallax_ceiling=True,
                            floor_z=8192, clear_height=STREET_SKY))
    faces = {"north": 0, "east": 1, "south": 2, "west": 3}
    street = level.room("street", [(0, 0), (16384, 0), (16384, 16384),
                                   (0, 16384)], role="exterior", faces=faces,
                        frame=Frame(0, 0))
    block = [(6144, 6144), (10240, 6144), (10240, 10240), (6144, 10240)]
    street.carve(block)
    top_room = skyline.roof(
        level, "block", block, top_height=top, sky_height=STREET_SKY,
        grade_z=8192, sky_picnum=SKY, wall_picnum=STONE, top_picnum=PAVING)
    for name in ("e0", "e1", "e2", "e3"):
        level.connect(top_room.face(name), street.face("north"),
                      connection_id=f"connection:block_{name}")
    level.set_start(street, local=(0.1, 0.1))
    return level, top_room


class RoofTests(unittest.TestCase):
    def test_a_roof_keeps_the_common_sky_and_raises_its_floor(self):
        level, _room = _street_with_a_roofed_mass()
        disk = level.compile().compile().level

        skies = {int(s["fields"]["ceiling_z"]) for s in disk.sectors
                 if int(s["fields"]["ceiling_stat"]) & 1}
        self.assertEqual(skies, {8192 - STREET_SKY})   # nothing was lowered
        floors = sorted({int(s["fields"]["floor_z"]) for s in disk.sectors})
        self.assertEqual(floors, [8192 - EAVES, 8192])
        self.assertEqual(skyline.lowered_skies(disk), [])

    def test_an_apron_is_reported_as_a_lowered_sky(self):
        level, _strip = _street_with_a_mass()
        disk = level.compile().compile().level

        lowered = skyline.lowered_skies(disk)
        self.assertEqual(len(lowered), 1)
        self.assertEqual(lowered[0]["below_common_sky"], STREET_SKY - EAVES)

    def test_the_face_of_a_roof_is_painted_from_the_side_that_sees_it(self):
        level, room = _street_with_a_roofed_mass()
        compiled = level.compile().compile()
        disk = compiled.level
        sector_id = compiled.allocations[room.region_id].sector_id

        report = skyline.dress_steps(disk, {sector_id: STONE})

        self.assertEqual(report["step_walls_painted"], 4)
        looking_up = [w["fields"] for w in disk.walls
                      if int(w["fields"]["next_sector"]) == sector_id]
        self.assertEqual({int(w["picnum"]) for w in looking_up}, {STONE})

    def test_only_from_limits_which_records_are_painted(self):
        level, room = _street_with_a_roofed_mass()
        compiled = level.compile().compile()
        disk = compiled.level
        sector_id = compiled.allocations[room.region_id].sector_id

        nowhere = skyline.dress_steps(disk, {sector_id: STONE},
                                      only_from={sector_id})
        self.assertEqual(nowhere["step_walls_painted"], 0)
        street = {index for index in range(len(disk.sectors))
                  if index != sector_id}
        there = skyline.dress_steps(disk, {sector_id: STONE},
                                    only_from=street)
        self.assertEqual(there["step_walls_painted"], 4)

    def test_a_roof_needs_a_sky_over_it(self):
        with self.assertRaises(LevelProgramError):
            _street_with_a_roofed_mass(top=STREET_SKY)


class _Region:
    def __init__(self, sky, kind=None):
        self.parallax_ceiling = sky
        self.intent = {"kind": kind} if kind else {}


class _Overlap:
    def __init__(self, left, right):
        self.left, self.right = left, right


class _Layout:
    """Just enough of a layout to ask the question of."""

    def __init__(self, regions, joins):
        self.regions = regions
        self._joins = joins

    def declared_joins(self):
        return [frozenset(pair) for pair in self._joins]


class LeakTests(unittest.TestCase):
    REGIONS = {
        "street": _Region(True), "roof": _Region(True, "roof"),
        "porch": _Region(False), "hall": _Region(False),
        "tower_room": _Region(False), "ring": _Region(True, "sky_apron"),
    }
    STACK = [_Overlap("roof", "porch"), _Overlap("hall", "roof")]

    def test_a_porch_under_a_roof_that_opens_on_the_street_is_a_leak(self):
        layout = _Layout(self.REGIONS, [("street", "roof"), ("street", "porch"),
                                        ("porch", "hall")])

        found = skyline.leaks_under_roofs(layout, overlaps=self.STACK)

        self.assertEqual(found, [{"roof": "roof", "room": "porch",
                                  "opens_onto": "street"}])

    def test_a_way_in_through_a_tower_is_not(self):
        # street -> the tower's ring of raised sky -> a room in the tower,
        # which nothing is over -> the hall under the roof
        layout = _Layout(self.REGIONS, [("street", "roof"), ("street", "ring"),
                                        ("ring", "tower_room"),
                                        ("tower_room", "hall")])

        self.assertEqual(
            skyline.leaks_under_roofs(layout, overlaps=self.STACK), [])


class SkyRuleTests(unittest.TestCase):
    def test_a_step_out_of_reach_is_a_skyline_and_not_a_fault(self):
        from bloodmap import rules_blood

        level, _strip = _street_with_a_mass()
        disk = level.compile().compile().level.to_disk_map()

        finding = rules_blood._open_neighbours_share_a_sky(disk)
        self.assertGreaterEqual(finding.population, 1)
        self.assertEqual(finding.violations, ())

    def test_a_step_within_reach_is_still_reported(self):
        from bloodmap import rules_blood

        level, _strip = _street_with_a_mass()
        disk = level.compile().compile().level.to_disk_map()
        low = next(s.fields for s in disk.sectors
                   if int(s.fields["floor_z"]) - int(s.fields["ceiling_z"]) == EAVES)
        low["ceiling_z"] = int(low["floor_z"]) - 2 * 16960

        finding = rules_blood._open_neighbours_share_a_sky(disk)
        self.assertEqual(len(finding.violations), 1)


if __name__ == "__main__":
    unittest.main()
