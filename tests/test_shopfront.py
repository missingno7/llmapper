"""A pane sits in a frame, a road crosses a seam, and a facade is a wall.

Three things the owner found walking Gravesend on 2026-11-17:

* "the glass should sit in an aperture/frame so glass texture scaling won't
  be colliding with facade texture" -- the pane was glazed on the facade's
  own record;
* "there were roads and sidewalk attempts but it looks poor" -- eight of the
  city's main runs were refused because they straddle a district seam;
* "these ceiling crates doesn't feel right" -- the lintel pass took a
  sector's commonest wall RECORD for its facade.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")
CITY = LEVEL / "blood-city-current.MAP"


def _level_path():
    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))


def _wall_level(length: int):
    level = type("L", (), {})()
    level.walls = [
        {"fields": {"x": 0, "y": 0, "point2": 1, "next_sector": 2,
                    "cstat": 0, "x_repeat": 8, "y_repeat": 8,
                    "over_picnum": 0, "extra": 0}},
        {"fields": {"x": length, "y": 0, "point2": 0, "next_sector": -1,
                    "cstat": 0, "x_repeat": 8, "y_repeat": 8,
                    "over_picnum": 0, "extra": 0}},
    ]
    return level


class ShopfrontGeometryTests(unittest.TestCase):
    def setUp(self):
        _level_path()
        import glass
        self.glass = glass

    def test_layers_tile_the_window_from_street_to_shop(self):
        for rect, outward in (((27648, 3072, 31744, 3584), "north"),
                              ((13824, 41472, 15360, 45056), "east"),
                              ((41984, 44032, 42880, 44544), "south"),
                              ((0, 0, 512, 4096), "west")):
            front = self.glass.shopfront(rect, outward)
            along_x = outward in ("north", "south")
            lo, hi = (1, 3) if along_x else (0, 2)
            reveal, box = front["reveal"], front["box"]
            depth = rect[hi] - rect[lo]
            self.assertEqual(reveal[hi] - reveal[lo], self.glass.REVEAL_DEPTH)
            self.assertEqual(
                box[hi] - box[lo],
                depth - self.glass.REVEAL_DEPTH - self.glass.SASH_DEPTH)
            #: the reveal is on the street side, the box on the shop side
            street_edge = rect[lo] if outward in ("north", "west") else rect[hi]
            self.assertIn(street_edge, (reveal[lo], reveal[hi]))
            self.assertNotIn(street_edge, (box[lo], box[hi]))

    def test_a_long_window_is_divided_and_a_short_one_is_not(self):
        long = self.glass.shopfront((3584, 40960, 10752, 41472), "north")
        short = self.glass.shopfront((41984, 44032, 42880, 44544), "south")
        self.assertEqual(len(long["sashes"]), 3)
        self.assertEqual(len(short["sashes"]), 1)
        widths = {s[2] - s[0] for s in long["sashes"]}
        self.assertEqual(len(widths), 1, "bays of one window are equal")
        self.assertLessEqual(widths.pop(), self.glass.BAY_WIDEST)
        #: and there is a mullion's width of solid between two bays
        first, second = long["sashes"][0], long["sashes"][1]
        self.assertEqual(second[0] - first[2], self.glass.MULLION)

    def test_a_pane_span_holds_only_the_back_of_its_sash(self):
        front = self.glass.shopfront((27648, 3072, 31744, 3584), "north")
        plane = 3072 + self.glass.REVEAL_DEPTH + self.glass.SASH_DEPTH
        for (x0, y0, x1, y1), sash in zip(front["panes"], front["sashes"]):
            self.assertLess(y0, plane)
            self.assertGreater(y1, plane)
            #: neither the facade line nor the box's back wall is inside it
            self.assertGreater(y0, 3072 + self.glass.REVEAL_DEPTH)
            self.assertLess(y1, 3584)
            self.assertGreaterEqual(x0, sash[0])
            self.assertLessEqual(x1, sash[2])

    def test_a_window_too_shallow_for_a_frame_is_refused(self):
        with self.assertRaises(self.glass.GlassError):
            self.glass.shopfront((0, 0, 4096, 256), "north")


class GlassDensityTests(unittest.TestCase):
    def test_fit_keeps_e6m1s_density_not_its_number(self):
        from bloodmap.glass import glaze

        for length, want in ((4096, 32), (2048, 16), (896, 7), (7168, 56)):
            level = _wall_level(length)
            glaze(level, [(-10, -10, length + 10, 10)], fit=True)
            self.assertEqual(level.walls[0]["fields"]["x_repeat"], want, length)

    def test_without_fit_the_number_is_e6m1s(self):
        from bloodmap.glass import glaze

        level = _wall_level(896)
        glaze(level, [(-10, -10, 906, 10)])
        self.assertEqual(level.walls[0]["fields"]["x_repeat"], 32)


@unittest.skipUnless(CITY.exists(), "the city is not built")
class CityGlassTests(unittest.TestCase):
    """The owner's sentence, as three things a reader can count."""

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map
        from bloodmap.glass import GLASS_TILE

        cls.disk = read_map(CITY)
        cls.owner = {}
        for sector_id, sector in enumerate(cls.disk.sectors):
            f = sector.fields
            for wall in range(int(f["wall_ptr"]),
                              int(f["wall_ptr"]) + int(f["wall_count"])):
                cls.owner[wall] = sector_id
        cls.panes = [index for index, wall in enumerate(cls.disk.walls)
                     if int(wall.fields.get("over_picnum", 0)) == GLASS_TILE
                     and int(wall.fields["cstat"]) & 16]

    def _sides(self, wall):
        here = self.disk.sectors[self.owner[wall]].fields
        there = self.disk.sectors[
            int(self.disk.walls[wall].fields["next_sector"])].fields
        return here, there

    def test_the_city_has_glass(self):
        self.assertGreaterEqual(len(self.panes), 12)

    def test_no_pane_shares_its_record_with_a_step_band(self):
        for wall in self.panes:
            here, there = self._sides(wall)
            self.assertEqual(int(here["floor_z"]), int(there["floor_z"]), wall)
            self.assertEqual(int(here["ceiling_z"]), int(there["ceiling_z"]),
                             wall)

    def test_no_pane_is_on_a_facade_record(self):
        for wall in self.panes:
            for side in self._sides(wall):
                self.assertFalse(int(side["ceiling_stat"]) & 1,
                                 f"wall {wall} is glazed on a street's record")

    def test_every_pane_is_held_by_a_frame_with_a_sill(self):
        from bloodmap.glass import panes_without_a_recess

        self.assertEqual(panes_without_a_recess(self.disk), [])


@unittest.skipUnless(CITY.exists(), "the city is not built")
class CityStreetTests(unittest.TestCase):
    """A street has a pavement, a carriageway and a kerb between them."""

    FACADES = {400, 384, 380, 393}
    BODY = 16960

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.disk = read_map(CITY)
        cls.owner = {}
        for sector_id, sector in enumerate(cls.disk.sectors):
            f = sector.fields
            for wall in range(int(f["wall_ptr"]),
                              int(f["wall_ptr"]) + int(f["wall_count"])):
                cls.owner[wall] = sector_id

    def _open_pairs(self):
        """(wall fields, this sector, the neighbour) under open sky."""
        for index, wall in enumerate(self.disk.walls):
            nxt = int(wall.fields["next_sector"])
            if nxt < 0:
                continue
            here = self.disk.sectors[self.owner[index]].fields
            there = self.disk.sectors[nxt].fields
            if int(here["ceiling_stat"]) & 1 and int(there["ceiling_stat"]) & 1:
                yield wall.fields, here, there

    def test_a_road_on_a_seam_is_one_road_with_no_strip_in_it(self):
        # A carriageway that lies on a district seam is laid by both
        # districts, as a notch in each street's outline, and the two parts
        # meet ON the seam: no pavement between them.
        import json

        manifest = json.loads(
            (LEVEL.parent / "reports" / "build-manifest.json").read_text())
        by_piece: dict[tuple, list] = {}
        for row in manifest["streets"]["laid"]:
            if row.get("half"):
                by_piece.setdefault((row["run"], row["piece"]), []).append(
                    row["rect"])
        self.assertGreaterEqual(len(by_piece), 6)
        for key, rects in by_piece.items():
            self.assertGreaterEqual(len(rects), 2, key)
            x0 = min(r[0] for r in rects); y0 = min(r[1] for r in rects)
            x1 = max(r[2] for r in rects); y1 = max(r[3] for r in rects)
            area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects)
            #: the parts tile one rectangle exactly
            self.assertEqual(area, (x1 - x0) * (y1 - y0), key)

    def test_the_avenue_has_a_pavement_on_both_sides(self):
        import json

        manifest = json.loads(
            (LEVEL.parent / "reports" / "build-manifest.json").read_text())
        rows = [r for r in manifest["streets"]["laid"]
                if r["run"] == "the_avenue_mid"]
        self.assertTrue(rows)
        x0 = min(r["rect"][0] for r in rows)
        x1 = max(r["rect"][2] for r in rows)
        #: the avenue is 7168 wide from x 32768; its seam is at 36352
        self.assertLess(x0, 36352)
        self.assertGreater(x1, 36352)
        self.assertGreaterEqual(x0 - 32768, 1024)
        self.assertGreaterEqual(32768 + 7168 - x1, 1024)

    def test_the_main_streets_have_carriageways(self):
        import json

        manifest = json.loads(
            (LEVEL.parent / "reports" / "build-manifest.json").read_text())
        laid = manifest["streets"]["laid"]
        self.assertGreaterEqual(len(laid), 9)
        runs = {row["run"] for row in laid}
        for name in ("the_avenue_north", "the_avenue_mid",
                     "Theatre_Row_street_east", "market_street_mid"):
            self.assertIn(name, runs)

    def test_a_kerb_wears_the_kerb_tile_between_paving_and_cobble(self):
        kerbs = 0
        for wall, here, there in self._open_pairs():
            #: the road's own record, looking up a kerb at the pavement
            if (int(here["floor_picnum"]) == 352
                    and int(there["floor_picnum"]) == 4
                    and int(here["floor_z"]) - int(there["floor_z"]) == 2048):
                kerbs += 1
                self.assertEqual(int(wall["picnum"]), 6)
        self.assertGreaterEqual(kerbs, 36)

    def test_nothing_standing_in_a_street_wears_a_slice_of_facade(self):
        offenders = []
        for wall, here, there in self._open_pairs():
            rise = int(here["floor_z"]) - int(there["floor_z"])
            if 0 < rise < self.BODY and int(wall["picnum"]) in self.FACADES:
                offenders.append((int(wall["x"]), int(wall["y"]),
                                  int(wall["picnum"]), rise))
        self.assertEqual(offenders, [])


@unittest.skipUnless(CITY.exists(), "the city is not built")
class CityStreetEndTests(unittest.TestCase):
    """A main street ends in a low wall with the sky behind it (E3M1)."""

    BODY = 16960

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.disk = read_map(CITY)

    def _walls(self, sector_id):
        f = self.disk.sectors[sector_id].fields
        return [self.disk.walls[w].fields
                for w in range(int(f["wall_ptr"]),
                               int(f["wall_ptr"]) + int(f["wall_count"]))]

    def test_three_streets_end_in_six_backed_masses(self):
        from bloodmap import skyline

        #: (the sea's horizon pieces are backings too, with the sky on their
        #: FLOOR as well: `l3_market`, DWE3M4 s648. These are the streets'.)
        #: The avenue ended in one until 2026-11-20; the station fronts it
        #: now (`l3_station.avenue_front`): a forecourt whose sky is the
        #: front's top, which needs no backing.
        backings = [b for b in skyline.sky_backings(self.disk)
                    if not int(self.disk.sectors[b].fields["floor_stat"]) & 1]
        self.assertEqual(len(backings), 6)
        for backing in backings:
            masses = {int(w["next_sector"]) for w in self._walls(backing)
                      if int(w["next_sector"]) >= 0
                      and not skyline.is_sky_backing(self.disk,
                                                     int(w["next_sector"]))}
            self.assertEqual(len(masses), 1, backing)
            mass = self.disk.sectors[masses.pop()].fields
            #: the mass is open to the sky and stands E3M1's 5.8 bodies up
            self.assertTrue(int(mass["ceiling_stat"]) & 1)
            rise = (8192 - int(mass["floor_z"])) / self.BODY
            self.assertTrue(3.86 - 0.01 <= rise <= 5.80 + 0.01, rise)

    def test_a_backing_is_not_reported_as_a_lowered_sky(self):
        from bloodmap import skyline

        lowered = {row["sector"] for row in skyline.lowered_skies(self.disk)}
        self.assertFalse(lowered & set(skyline.sky_backings(self.disk)))

    def test_the_rule_about_skies_does_not_fire_on_a_backing(self):
        from bloodmap import rules_blood

        finding = rules_blood._open_neighbours_share_a_sky(self.disk)
        self.assertEqual(finding.violations, ())


class SeamClipTests(unittest.TestCase):
    def setUp(self):
        _level_path()
        import streets
        self.streets = streets

    def test_a_seam_side_keeps_half_a_strip_and_a_city_edge_a_pavement(self):
        city = (0, 0, 20000, 10000)
        west = (0, 0, 10000, 10000)             # its east side is a seam
        road = (7000, 0, 13000, 10000)
        got = self.streets._clip_seams(road, west, city, seam=128, edge=1024)
        self.assertEqual(got, (7000, 1024, 9872, 8976))

    def test_a_seam_crossed_end_on_leaves_a_crossing_not_a_line(self):
        city = (0, 0, 20000, 10000)
        road = (7000, 4000, 13000, 6000)          # runs along x, across a seam
        kw = dict(seam=self.streets.CENTRE_STRIP // 2, edge=1024,
                  end=self.streets.CROSSING // 2, along=0)
        west = self.streets._clip_seams(road, (0, 0, 10000, 10000), city, **kw)
        east = self.streets._clip_seams(road, (10000, 0, 20000, 10000), city,
                                        **kw)
        self.assertEqual(east[0] - west[2], self.streets.CROSSING)
        #: and it is not narrowed: the seam is not along its side
        self.assertEqual((west[1], west[3]), (4000, 6000))

    def test_a_seam_run_along_keeps_only_a_kerb_line(self):
        city = (0, 0, 20000, 10000)
        road = (7000, 2000, 13000, 8000)          # runs along y, on the seam
        west = self.streets._clip_seams(
            road, (0, 0, 10000, 10000), city,
            seam=self.streets.CENTRE_STRIP // 2, edge=1024,
            end=self.streets.CROSSING // 2, along=1)
        self.assertEqual(west[2], 10000 - self.streets.CENTRE_STRIP // 2)

    def test_the_clear_stretch_beyond_an_obstacle_is_found(self):
        # A guillotine tiling loses it: the tower stands in one side of the
        # avenue and the full-width road beyond it is in no tile.
        road = (0, 0, 3000, 20000)
        tower = (0, 8000, 1000, 10000)
        got = self.streets._clear_rects(road, [tower], along=1,
                                        min_across=2000, min_along=4000)
        #: the longest first: past the tower, narrower, the whole way
        self.assertEqual(got[0], (1000, 0, 3000, 20000))
        #: and the full-width stretches either side of it are offered too
        self.assertIn((0, 10000, 3000, 20000), got)
        self.assertIn((0, 0, 3000, 8000), got)

    def test_a_blocked_street_offers_nothing(self):
        got = self.streets._clear_rects((0, 0, 3000, 20000),
                                        [(500, 0, 2500, 20000)], along=1,
                                        min_across=2000, min_along=4000)
        self.assertEqual(got, [])

    def test_a_sliver_is_no_road(self):
        city = (0, 0, 20000, 10000)
        got = self.streets._clip_seams((9500, 0, 13000, 10000),
                                       (0, 0, 10000, 10000), city,
                                       seam=128, edge=1024)
        self.assertIsNone(got)


class FacadeIsAWallTests(unittest.TestCase):
    """`dominant_wall_tile`: solid wall by length, not records by count."""

    def _disk(self, walls):
        #: (x, y, picnum, next_sector) in loop order
        obj = lambda fields: type("O", (), {"fields": fields})()
        disk = type("D", (), {})()
        disk.sectors = [obj({"wall_ptr": 0, "wall_count": len(walls)})]
        disk.walls = [obj({"x": x, "y": y, "picnum": tile, "next_sector": nxt,
                           "point2": (index + 1) % len(walls)})
                      for index, (x, y, tile, nxt) in enumerate(walls)]
        return disk

    def test_many_short_crate_rims_do_not_outvote_one_long_wall(self):
        from bloodmap.aperture import dominant_wall_tile

        disk = self._disk([
            (0, 0, 2294, -1),            # 8192 of plaster
            (8192, 0, 452, 5), (8192, 512, 452, 5), (8192, 1024, 452, 5),
            (8192, 1536, 452, 5),        # four crate rims, two-sided
            (8192, 2048, 2294, -1), (0, 2048, 452, 6),
        ])
        self.assertEqual(dominant_wall_tile(disk, 0), 2294)

    def test_length_decides_between_two_solid_tiles(self):
        from bloodmap.aperture import dominant_wall_tile

        disk = self._disk([(0, 0, 10, -1), (100, 0, 20, -1),
                           (100, 4000, 10, -1), (0, 4000, 20, -1)])
        self.assertEqual(dominant_wall_tile(disk, 0), 20)

    def test_a_sector_with_no_solid_wall_falls_back_to_what_it_has(self):
        from bloodmap.aperture import dominant_wall_tile

        disk = self._disk([(0, 0, 7, 1), (100, 0, 7, 1), (100, 100, 9, 1)])
        self.assertEqual(dominant_wall_tile(disk, 0), 7)

    @unittest.skipUnless(CITY.exists(), "the city is not built")
    def test_the_market_hall_wears_no_crates_over_its_openings(self):
        from bloodmap.format import read_map

        disk = read_map(CITY)
        crates = {95, 452, 462}
        offenders = []
        for sector_id, sector in enumerate(disk.sectors):
            f = sector.fields
            my_ceiling = int(f["ceiling_z"])
            for wall in range(int(f["wall_ptr"]),
                              int(f["wall_ptr"]) + int(f["wall_count"])):
                w = disk.walls[wall].fields
                nxt = int(w["next_sector"])
                if nxt < 0 or int(w["picnum"]) not in crates:
                    continue
                there = disk.sectors[nxt].fields
                #: a band ABOVE the mouth (z grows downward) in crate, where
                #: the neighbour is not itself a crate standing on the floor
                if (int(there["ceiling_z"]) > my_ceiling
                        and int(there["floor_picnum"]) not in crates):
                    offenders.append((sector_id, wall))
        self.assertEqual(offenders, [])


class MaterialStandsOnItsFloorTests(unittest.TestCase):
    """`frame_map(v_anchor="floor")`: the owner's "meaningful alignment"."""

    TILE, SIZE = 2294, (32, 256)           # plaster over a tiled dado
    FLOOR, CEILING = 8192, -40960          # the market hall: 192 texels tall

    def _hall(self, order):
        """A square hall whose loop starts at `order`'s first wall."""
        points = [(0, 0), (4096, 0), (4096, 4096), (0, 4096)]
        points = points[order:] + points[:order]
        walls = [{"fields": {
            "x": x, "y": y, "point2": (index + 1) % 4,
            "next_wall": -1, "next_sector": -1, "cstat": 0,
            "picnum": self.TILE, "over_picnum": 0,
            "x_repeat": 16, "y_repeat": 8, "x_panning": 0,
            "y_panning": 37 * (index + 1) % 256, "shade": 0, "extra": -1}}
            for index, (x, y) in enumerate(points)]
        level = type("L", (), {})()
        level.walls = walls
        level.sectors = [{"fields": {
            "wall_ptr": 0, "wall_count": 4, "floor_z": self.FLOOR,
            "ceiling_z": self.CEILING, "type": 0,
            "floor_picnum": 1, "ceiling_picnum": 1,
            "floor_stat": 0, "ceiling_stat": 0}}]
        return level

    def _row_at_floor(self, level, wall):
        """Which texel row of the tile lands on the floor."""
        fields = level.walls[wall]["fields"]
        texel_z = 2048 // int(fields["y_repeat"])
        #: a one-sided wall hangs from its ceiling, panned by y_panning rows
        #: of a 256-row tile
        rows = (self.FLOOR - self.CEILING) // texel_z
        return (int(fields["y_panning"]) * self.SIZE[1] // 256 + rows)             % self.SIZE[1]

    def test_the_tiles_bottom_row_lands_on_the_floor(self):
        from bloodmap.texture_frame import frame_map

        level = self._hall(0)
        frame_map(level, art_sizes={self.TILE: self.SIZE}, v_anchor="floor")
        for wall in range(4):
            self.assertEqual(self._row_at_floor(level, wall), 0, wall)

    def test_it_does_not_depend_on_where_the_run_starts(self):
        from bloodmap.texture_frame import frame_map

        seen = set()
        for order in range(4):
            level = self._hall(order)
            frame_map(level, art_sizes={self.TILE: self.SIZE},
                      v_anchor="floor")
            seen.add(int(level.walls[0]["fields"]["y_panning"]))
        self.assertEqual(len(seen), 1)

    def test_the_editors_anchor_is_still_the_default(self):
        from bloodmap.texture_frame import frame_map

        level = self._hall(0)
        frame_map(level, art_sizes={self.TILE: self.SIZE})
        #: the first wall's peg is the origin, so it pans by nothing
        self.assertEqual(int(level.walls[0]["fields"]["y_panning"]), 0)

    def test_an_unknown_anchor_is_refused(self):
        from bloodmap.texture_frame import FrameError, frame_map

        with self.assertRaises(FrameError):
            frame_map(self._hall(0), art_sizes={self.TILE: self.SIZE},
                      v_anchor="ceiling")

    def test_a_run_stands_on_the_floor_most_of_it_stands_on(self):
        from bloodmap.texture_frame import run_floor

        level = self._hall(0)
        level.sectors.append({"fields": dict(level.sectors[0]["fields"],
                                             floor_z=4096)})
        #: three walls on the hall's floor, one on a raised one
        self.assertEqual(run_floor(level, [0, 1, 2, 3], [0, 0, 0, 1]),
                         self.FLOOR)


if __name__ == "__main__":
    unittest.main()
