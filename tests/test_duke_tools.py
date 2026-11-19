"""Looking at a Duke map, and asking it a question Blood can use.

`tools/duke_view.py` builds what the Blood observer needs to stand in a Duke
level; `tools/city_profile.py` asks one list of structural questions of any
Build map and answers in bodies. Neither is a conversion, and the tests pin
exactly that: nothing is scaled, nothing is renumbered, and the numbers that
cross between the games are ratios.
"""

from __future__ import annotations

import unittest
from pathlib import Path

DUKCITY1 = Path("maps/duke3d/DukCity1.map")
E3M1 = Path("maps/blood/campaign/E3M1.MAP")
CITY = Path("projects/blood-city/level/blood-city-current.MAP")
GRP = Path("reference/duke3d/duke3d.grp")


class PaletteBridgeTests(unittest.TestCase):
    """The observer reads a palette from one archive format; Duke's goes in it.

    The first version moved Duke's ART into Blood's palette instead, and the
    owner's verdict on the frames was "Duke palette is off".
    """

    def test_a_shade_row_is_dukes_row_at_half_the_index(self):
        from tools.duke_view import RFF_SHADES, shade_table_64

        #: four Duke levels; level n is 256 bytes of n
        table = b"".join(bytes([level]) * 256 for level in range(4))
        made = shade_table_64(table, 4)
        self.assertEqual(len(made), RFF_SHADES * 256)
        #: the viewing copy doubles a shade, so row 2n is Duke's row n
        for duke_level in range(4):
            self.assertEqual(made[(2 * duke_level) * 256], duke_level)
            self.assertEqual(made[(2 * duke_level + 1) * 256], duke_level)
        #: past Duke's last level it stays at the last
        self.assertEqual(made[63 * 256], 3)

    def test_a_palette_swap_is_applied_before_the_shade(self):
        from tools.duke_view import shade_table_64

        table = bytes(range(256))                     # one level: identity
        remap = bytes((i + 1) % 256 for i in range(256))
        made = shade_table_64(table, 1, remap)
        self.assertEqual(made[10], 11)
        self.assertEqual(made[255], 0)

    def test_the_archive_is_laid_out_as_the_observer_reads_it(self):
        import struct
        import tempfile

        from tools.duke_view import write_rff

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "BLOOD.RFF"
            write_rff(path, [("PAL", 0, "DUKE", b"p" * 768),
                             ("PLU", 7, "SWAP7", b"s" * 16384)])
            data = path.read_bytes()
        self.assertEqual(data[:3], b"RFF")
        self.assertEqual(data[3], 0x1A)
        #: not version 3: the observer would decrypt its directory
        self.assertNotEqual(struct.unpack_from("<H", data, 4)[0] & 0xFF00, 0x300)
        dir_off, count = struct.unpack_from("<ii", data, 8)
        self.assertEqual(count, 2)
        second = data[dir_off + 48:dir_off + 96]
        offset, size = struct.unpack_from("<ii", second, 16)
        self.assertEqual(second[32], 0)                    # nothing encrypted
        self.assertEqual(second[33:36], b"PLU")
        self.assertEqual(struct.unpack_from("<i", second, 44)[0], 7)
        self.assertEqual(data[offset:offset + size], b"s" * 16384)

    @unittest.skipUnless(GRP.exists(), "no duke3d.grp")
    def test_dukes_tables_come_out_of_the_grp_whole(self):
        from tools.duke_view import duke_tables, read_grp

        tables = duke_tables(read_grp(GRP))
        self.assertEqual(len(tables["palette"]), 768)
        self.assertEqual(tables["shades"], 32)
        self.assertEqual(len(tables["shade_table"]), 32 * 256)
        #: shade 0 is the identity, a colour at full light being itself --
        #: all but one index, which Duke's own table sends to its twin
        same = sum(1 for i in range(255) if tables["shade_table"][i] == i)
        self.assertGreaterEqual(same, 253)
        self.assertEqual(len(tables["transluc"]), 65536)
        self.assertGreater(len(tables["swaps"]), 10)

    def test_an_art_file_keeps_a_picanm_whose_top_bit_is_set(self):
        # Every Duke ART file has one; `write_art_file` packed the field
        # signed and refused them.
        import tempfile

        from bloodmap import art

        tile = art.ArtTile(7, 2, 2, bytes([1, 2, 3, 4]), 0x80000001)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "TILES000.ART"
            art.write_art_file(path, {7: tile}, first=7)
            back = art.read_art_file(path)
        self.assertEqual(back[7].picanm, 0x80000001)
        self.assertEqual(back[7].pixels, tile.pixels)


@unittest.skipUnless(DUKCITY1.exists(), "no DukCity1")
class ViewingCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bloodmap.duke import read_duke_map
        from tools.duke_view import viewing_copy

        cls.duke = read_duke_map(DUKCITY1)
        cls.disk, cls.counts = viewing_copy(cls.duke)

    def test_geometry_and_tiles_are_dukes_unscaled(self):
        self.assertEqual(len(self.disk.sectors), len(self.duke.sectors))
        self.assertEqual(len(self.disk.walls), len(self.duke.walls))
        for index in (0, 17, len(self.duke.walls) - 1):
            a, b = self.duke.walls[index].fields, self.disk.walls[index].fields
            for key in ("x", "y", "point2", "next_wall", "next_sector",
                        "picnum", "x_repeat", "y_repeat"):
                self.assertEqual(int(a[key]), int(b[key]), (index, key))
        for index in (0, 5, len(self.duke.sectors) - 1):
            a, b = self.duke.sectors[index].fields, self.disk.sectors[index].fields
            for key in ("floor_z", "ceiling_z", "floor_picnum",
                        "ceiling_picnum", "wall_ptr", "wall_count"):
                self.assertEqual(int(a[key]), int(b[key]), (index, key))

    def test_palette_swaps_are_kept(self):
        swapped = [i for i, w in enumerate(self.duke.walls)
                   if int(w.fields["pal"])]
        self.assertTrue(swapped)
        for index in swapped[:20]:
            self.assertEqual(int(self.disk.walls[index].fields["pal"]),
                             int(self.duke.walls[index].fields["pal"]))

    def test_shade_is_moved_to_bloods_table(self):
        from bloodmap.conversion import convert_shade

        for index in range(0, len(self.duke.walls), 97):
            want = convert_shade(int(self.duke.walls[index].fields["shade"]),
                                 "duke3d", "blood")
            self.assertEqual(int(self.disk.walls[index].fields["shade"]), want)

    def test_marker_sprites_are_dropped_and_the_rest_keep_their_tile(self):
        from tools.duke_view import DUKE_MARKER_TILES

        tiles = {int(s.fields["picnum"]) for s in self.disk.sprites}
        self.assertFalse(tiles & DUKE_MARKER_TILES)
        self.assertEqual(self.counts["sprites_kept"], len(self.disk.sprites))
        self.assertEqual(self.counts["sprites_kept"]
                         + self.counts["sprites_dropped"],
                         len(self.duke.sprites))
        self.assertGreater(self.counts["sprites_dropped"], 0)

    def test_a_pose_stands_at_dukes_eye_height_in_the_right_sector(self):
        from tools.duke_view import DUKE_EYE, pose

        h = self.duke.header
        made = pose(self.duke, "start", h["start_x"], h["start_y"],
                    h["start_x"] + 1000, h["start_y"])
        self.assertEqual(made.sector, int(h["start_sector"]))
        floor = int(self.duke.sectors[made.sector].fields["floor_z"])
        self.assertEqual(made.z, floor - DUKE_EYE)
        self.assertEqual(made.angle, 0)


class CityProfileTests(unittest.TestCase):
    """One question, three maps, one unit."""

    @classmethod
    def setUpClass(cls):
        from tools.city_profile import load, profile

        cls.profiles = {}
        for name, path in (("duke", DUKCITY1), ("e3m1", E3M1), ("city", CITY)):
            if path.exists():
                game, disk = load(path)
                cls.profiles[name] = profile(disk, game)

    def _need(self, *names):
        for name in names:
            if name not in self.profiles:
                self.skipTest(f"{name} is not present")
        return [self.profiles[name] for name in names]

    def test_the_game_is_told_from_the_file(self):
        duke, e3m1 = self._need("duke", "e3m1")
        self.assertEqual(duke["game"], "duke3d")
        self.assertEqual(e3m1["game"], "blood")
        #: Blood is built at 3:2 of Duke
        self.assertAlmostEqual(e3m1["body_z"] * 2, duke["body_z"] * 3)

    def test_a_kerb_is_a_tenth_of_a_body_in_either_game(self):
        duke, e3m1 = self._need("duke", "e3m1")
        self.assertAlmostEqual(
            duke["derived"]["ground"]["kerb"]["rise_bodies_median"], 0.091, 2)
        #: 2048 over 16960: E3M1's kerb, 22 of 22 walls
        self.assertAlmostEqual(
            e3m1["derived"]["ground"]["kerb"]["rise_bodies_median"], 0.121, 2)

    def test_blood_ends_streets_in_sky_and_duke_does_not(self):
        duke, e3m1 = self._need("duke", "e3m1")
        self.assertEqual(duke["native"]["sky_backings"], 0)
        self.assertGreaterEqual(e3m1["native"]["sky_backings"], 2)

    def test_dukes_city_is_one_height_and_bloods_is_not(self):
        duke, e3m1 = self._need("duke", "e3m1")
        self.assertGreater(
            duke["derived"]["street_wall"]["share_at_modal_height"], 0.8)
        self.assertLess(
            e3m1["derived"]["street_wall"]["share_at_modal_height"], 0.5)

    def test_duke_almost_never_glazes_a_streets_own_wall(self):
        (duke,) = self._need("duke")
        glass = duke["derived"]["glass"]
        self.assertGreater(glass["masked_two_sided_walls"], 50)
        self.assertLess(glass["on_a_street_record_share"], 0.05)

    def test_the_city_glazes_none_and_has_its_street_ends(self):
        (city,) = self._need("city")
        self.assertEqual(
            city["derived"]["glass"]["on_a_street_record_share"], 0.0)
        self.assertEqual(
            city["derived"]["glass"]["sharing_a_record_with_a_step_band_share"],
            0.0)
        #: eight behind the street ends, and the sea's five horizon pieces
        #: (a horizon is the same thing with the sky on its floor as well;
        #: seven until the near band's ends became a building's flank)
        self.assertEqual(city["native"]["sky_backings"], 13)

    def test_bloods_city_is_deeper_indoors_than_ours(self):
        # The measure behind "more complex interiors": E3M1's median interior
        # holds many floor heights over about three bodies and a wide spread
        # of light. This pins the reference, not the city, which is the
        # thing being changed.
        from tools.city_profile import interiors, load

        if not E3M1.exists():
            self.skipTest("no E3M1")
        game, disk = load(E3M1)
        found = interiors(disk, game)
        self.assertGreaterEqual(found["interiors"], 5)
        self.assertGreaterEqual(found["floor_heights"], 10)
        self.assertGreaterEqual(found["floor_range_bodies"], 2.0)
        self.assertGreaterEqual(found["floor_shade_spread"], 20)

    def test_the_interior_table_has_a_row_for_each_measure(self):
        from tools.city_profile import INTERIOR_ROWS, interior_table

        text = interior_table({"a": {key: 1 for _label, key in INTERIOR_ROWS}})
        self.assertEqual(len(text.splitlines()), len(INTERIOR_ROWS) + 2)

    def test_the_table_has_a_column_for_each_map(self):
        from tools.city_profile import ROWS, table

        if not self.profiles:
            self.skipTest("no maps")
        text = table(self.profiles)
        lines = text.splitlines()
        self.assertEqual(len(lines), len(ROWS) + 2)
        self.assertEqual(lines[0].count("|"), len(self.profiles) + 2)


if __name__ == "__main__":
    unittest.main()
