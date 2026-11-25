"""Read back the two Aldermack entrances, their fixtures and clear routes."""

import unittest
from pathlib import Path

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.sector_geom import outline_and_holes, wall_segment


MAP = Path("projects/blood-city/level/blood-city-current.MAP")
BODY = PLAYER_PROFILES["blood"]


@unittest.skipUnless(MAP.exists(), "the city has not been built")
class AldermackFrontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.disk = read_map(MAP)
        cls.sectors = [record_fields(s) for s in cls.disk.sectors]
        cls.walls = [record_fields(w) for w in cls.disk.walls]
        cls.sprites = [record_fields(s) for s in cls.disk.sprites]

    def test_the_street_doors_are_pushed_and_no_lever_stands_by_them(self):
        #: the owner, 2026-11-26: "some of the shops have lever next to it, but it just
        #: opens door the same way you would interact with them"
        levers = [s for s in self.sprites if s["picnum"] == 1070 and abs(s["z"]) < 16384
                  and (10900 <= s["y"] <= 17000 or 32256 <= s["x"] <= 34000 and 3000 <= s["y"])]
        self.assertEqual([s for s in levers if s["y"] < 17000 and s["x"] < 34000], [])

        def corners(s):
            return [(w.fields["x"], w.fields["y"]) for w in self.disk.walls[s["wall_ptr"]:s["wall_ptr"] + s["wall_count"]]]

        avenue, = (record_extra(self.disk.sectors[i]) for i, s in enumerate(self.sectors)
                   if s["type"] == 600 and s["floor_z"] == s["ceiling_z"]
                   and all(32256 <= x <= 32512 and 8192 <= y <= 10240 for x, y in corners(s)))
        self.assertTrue(avenue["trigger_wall_push"])
        self.assertGreaterEqual(avenue["on_floor_z"] - avenue["on_ceiling_z"], 24576)

    def test_the_front_doors_are_mirrored_wings(self):
        #: the owner: "Shouldn't the front door be like mirror wings to each
        #: other? You already had door like this before ... and also they are
        #: slightly cropped, these previous two wing doors you had were what
        #: I would expect" -- so both pairs are one drawing
        leaves = [s for s in self.sectors if s["type"] == 617]
        self.assertEqual(len(leaves), 4)
        for s in leaves:
            walls = [self.walls[w] for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"])]
            faces = [self.walls[w["next_wall"]] for w in walls]
            broad = [f for f in faces if f["picnum"] == 30]
            self.assertEqual(len(broad), 2)
            self.assertEqual(sorted(f["cstat"] & 8 for f in broad), [0, 8])
            self.assertEqual({(f["x_repeat"], f["y_repeat"]) for f in broad}, {(8, 10)})
            host = self.sectors[walls[0]["next_sector"]]
            self.assertEqual(host["floor_z"] - s["floor_z"], 24576)

    def test_ticket_box_and_foyer_apertures(self):
        portals = [wall_segment(self.disk, i) for i, w in enumerate(self.walls)
                   if w["next_sector"] >= 0]
        for y, x in [(6656, 28096), (6656, 29408), (11264, 28448)]:
            with self.subTest(x=x, y=y):
                self.assertTrue(any(
                    ay == by == y and min(ax, bx) <= x <= max(ax, bx)
                    for (ax, ay), (bx, by) in portals))
        # The future vomitory lies on the existing foyer's west boundary.
        outlines = [outline_and_holes(self.disk, i)[0]
                    for i, s in enumerate(self.sectors)
                    if s["floor_z"] - s["ceiling_z"] == 40960
                    and (26624, 6656) in outline_and_holes(self.disk, i)[0]]
        self.assertTrue(outlines)
        self.assertTrue(any(
            x0 == x1 == 26624 and min(y0, y1) < 10240 and max(y0, y1) > 8704
            for outline in outlines
            for ((x0, y0), (x1, y1)) in zip(outline, outline[1:]+outline[:1])))

    def test_glazed_bills_have_their_own_wall_records(self):
        from bloodmap.glass import recess_faults

        cases = set()
        for i, w in enumerate(self.walls):
            if w["over_picnum"] != 266 or not w["cstat"] & 16:
                continue
            (ax, ay), (bx, by) = wall_segment(self.disk, i)
            if ay != 11136 or by != 11136 or not 26624 < min(ax, bx) < 30720:
                continue
            self.assertGreaterEqual(w["next_sector"], 0)
            self.assertEqual(w["type"], 511)
            self.assertTrue((record_extra(self.disk.walls[i]) or {})["trigger_vector"])
            opposite = self.walls[w["next_wall"]]
            # Fixed glazing is carried on a boundary with no step band.
            source, destination = (self.sectors[index] for index in
                                   (opposite["next_sector"], w["next_sector"]))
            for surface in ("floor_z", "ceiling_z"):
                self.assertEqual(source[surface], destination[surface])
            self.assertTrue(any(not recess_faults(self.disk, index) for index in
                                (opposite["next_sector"], w["next_sector"])))
            cases.add(min(i, w["next_wall"]))
        self.assertEqual(len(cases), 2)

    def test_the_theatre_blade_reads_aldermack_from_both_sides(self):
        for angle in (0, 1024):
            glyphs = sorted(
                (s for s in self.sprites
                 if s["angle"] == angle and 4225 <= s["picnum"] <= 4250
                 and 29520 <= s["x"] <= 29584 and 11472 <= s["y"] <= 11568),
                key=lambda sprite: sprite["z"])
            self.assertEqual("".join(chr(ord("A") + s["picnum"] - 4225)
                                     for s in glyphs), "ALDERMACK")

    def test_foyer_fixtures_read_back(self):
        tiles = {s["picnum"] for s in self.sprites
                 if 26624 < s["x"] < 30720 and 6656 < s["y"] < 10752}
        self.assertTrue({596, 710, 711, 73, 1009, 1013, 2334, 1417, 588} <= tiles)
        rail, = (s for s in self.sprites if s["picnum"] == 588
                 and 26624 < s["x"] < 30720 and 6656 < s["y"] < 10752)
        self.assertTrue(rail["cstat"] & 1)
        self.assertFalse(rail["cstat"] & 64)
        self.assertFalse(any(
            s["picnum"] in {534, 588, 1009, 1013}
            and 26624 < s["x"] < 26624 + BODY.body_width
            and 8704 <= s["y"] <= 10240 for s in self.sprites))
