"""Goods stand on fixtures, and the fixtures are the town maps' own.

A blind reviewer of Gravesend, 2026-11-18: "Shops have no fixtures ...
shelves and racks with stock on them." `tools/mine_stands.py` reads what
is under every standing thing in Blood's town maps; `fixtures.BAR` and
`fixtures.shelf_niche` are what it found; `goods.ROWS` stocks them.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")
CITY = LEVEL / "blood-city-current.MAP"
E3M1 = Path("maps/blood/campaign/E3M1.MAP")
E1M2 = Path("maps/blood/campaign/E1M2.MAP")


def _level_module(name):
    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))
    return __import__(name)


@unittest.skipUnless(E1M2.exists() and E3M1.exists(), "no campaign maps")
class WhatIsUnderAThingTests(unittest.TestCase):
    def test_e1m2s_liquor_shelf_is_a_niche_with_a_row_on_it(self):
        from tools.mine_stands import stands

        rows = [r for r in stands([str(E1M2)]) if r["sector"] == 213]
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertEqual(row["kind"], "niche")
            self.assertAlmostEqual(row["rise"], 0.483, places=2)
            self.assertAlmostEqual(row["clear"], 0.725, places=2)
            self.assertEqual(row["top_tile"], 34)

    def test_e3m1s_bar_is_a_ledge_half_a_body_high(self):
        from tools.mine_stands import stands

        rows = [r for r in stands([str(E3M1)]) if r["sector"] == 167]
        self.assertEqual({r["kind"] for r in rows}, {"ledge"})
        self.assertAlmostEqual(rows[0]["rise"], 0.483, places=2)
        self.assertEqual((rows[0]["top_tile"], rows[0]["face_tile"]), (34, 28))

    def test_a_centred_sprite_on_the_floor_is_not_floating(self):
        """A sprite's z is not its foot. Read raw, half of every town map's
        chairs and plants hung in the air."""
        from tools.mine_stands import stands, summary

        found = summary(stands([str(E1M2)]))
        things = sum(found[k]["things"] for k in found)
        self.assertLess(found["floating"]["things"] / things, 0.2)

    def test_every_class_is_reported_whether_or_not_anything_is_in_it(self):
        from tools.mine_stands import CLASSES, summary

        self.assertEqual(set(summary([])), set(CLASSES))


class FixtureFamilyTests(unittest.TestCase):
    def test_the_bar_is_the_measured_height_in_the_owners_wood(self):
        import json

        fixtures = _level_module("fixtures")
        self.assertAlmostEqual(fixtures.BAR.rise / 16960, 0.483, places=3)
        anchors = json.loads(Path(
            "knowledge/blood/design/owner-anchors-v1.json").read_text("utf-8"))
        named = {a["picnum"] for a in anchors["anchors"] if "picnum" in a}
        for tile in (fixtures.BAR.tile, fixtures.BAR_FACE, fixtures.SHELF_BACK):
            self.assertIn(tile, named)

    def test_a_shelf_leaves_the_wall_over_its_head(self):
        fixtures = _level_module("fixtures")
        head = fixtures.SHELF_RISE + fixtures.SHELF_CLEAR
        #: an arcade unit is 28,672 clear; its name is lettered over the shelf
        self.assertLessEqual(head, 28672 - 6144)

    def test_a_shelf_too_short_for_a_row_is_refused(self):
        fixtures = _level_module("fixtures")
        with self.assertRaises(fixtures.FixtureError):
            fixtures.shelf_niche(None, "x", "north", width=512)


@unittest.skipUnless(CITY.exists(), "the city is not built")
class StockedCityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.mine_stands import stands, summary

        tags = json.loads(CITY.with_suffix(".tags.json").read_text("utf-8"))
        auditorium = {sector for kind, sectors in tags.items()
                      if kind.startswith("aldermack_") for sector in sectors}
        # Theatre, underground railway and ritual scenery stand outside the shop sample.
        scenery = auditorium | set(tags["phantom_terminus"]) | set(tags["cabal_rite"])
        cls.rows = [row for row in stands([str(CITY)]) if row["sector"] not in scenery]
        cls.found = summary(cls.rows)

    def test_the_citys_fixtures_stand_as_high_as_the_towns(self):
        pieces = {(r["sector"]): r["rise"] for r in self.rows
                  if r["kind"] in ("island", "ledge", "niche")}
        rises = sorted(pieces.values())
        self.assertGreaterEqual(rises[len(rises) // 2], 0.40)

    def test_a_third_of_what_stands_indoors_stands_on_a_shelf(self):
        things = sum(self.found[k]["things"] for k in self.found)
        shelved = self.found["ledge"]["things"] + self.found["niche"]["things"]
        #: 15% before; E3M1 27%, E1M2 31%, E1M4 39%
        self.assertGreaterEqual(shelved / things, 0.35)

    def test_each_shelf_holds_a_row_and_not_one_thing(self):
        from bloodmap.format import read_map
        import json

        tags = json.loads(CITY.with_suffix(".tags.json").read_text("utf-8"))
        shelves = tags.get("shelf_niche", [])
        #: seven, the pawnbroker's behind his counter, and RAT DOGS'
        #: kitchen shelf beside its pans and its freezer's cold shelf
        self.assertEqual(len(shelves), 10)
        disk = read_map(CITY)
        rows = 0
        for sector in shelves:
            held = [s for s in disk.sprites
                    if int(s.fields["sector"]) == sector]
            #: (the bookseller's is the exception: its back IS the books,
            #: the owner's "bookcase front", and it holds two candles)
            self.assertGreaterEqual(len(held), 2, sector)
            rows += len(held) >= 4
            fields = disk.sectors[sector].fields
            self.assertEqual(int(fields["floor_picnum"]), 34)
            #: (9,216 in the pawn shop, whose room is 4,096 lower)
            self.assertIn(int(fields["floor_z"]) - int(fields["ceiling_z"]),
                          (12288, 9216))
        self.assertGreaterEqual(rows, 6)


def _level_floor(disk, start):
    """A sector and every sector joined to it at the same floor, ceiling and floor tile."""
    def key(s):
        f = disk.sectors[s].fields
        return int(f["floor_z"]), int(f["ceiling_z"]), int(f["floor_picnum"])

    seen, todo = {start}, [start]
    while todo:
        f = disk.sectors[todo.pop()].fields
        for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            other = int(disk.walls[w].fields["next_sector"])
            if other >= 0 and other not in seen and key(other) == key(start):
                seen.add(other)
                todo.append(other)
    return sorted(seen)


@unittest.skipUnless(CITY.exists(), "the city is not built")
class NothingIsShutBehindACounterTests(unittest.TestCase):
    def test_every_find_and_actor_in_the_arcade_units_stands_on_the_floor(self):
        """A hip-high counter cannot be stepped over. Run wall to wall, the
        first ones shut the arcade's key, a pickup and a zombie behind them;
        a blind reviewer saw "a bald scalp" over the bookseller's counter."""
        from bloodmap.format import read_map
        from tools.mine_stands import describe

        disk = read_map(CITY)
        seen = 0
        for sprite in disk.sprites:
            f = sprite.fields
            x, y, kind = int(f["x"]), int(f["y"]), int(f["type"])
            in_units = 41728 <= x <= 50432 and (41600 <= y <= 44032
                                                or 48128 <= y <= 50560)
            if not in_units or kind == 0 or 400 <= kind <= 433                     or kind in (30, 32):
                continue
            seen += 1
            under = describe(disk, int(f["sector"]))
            self.assertEqual(under["kind"], "floor", (kind, x, y))
            #: the unit's own floor, joined to its mouth round the counter;
            #: the light stage cuts a floor into lit pieces level with each
            #: other, so the floor is the piece and every piece level with it
            area = sum(describe(disk, s)["area"] for s in _level_floor(disk, int(f["sector"])))
            self.assertGreater(area, 3.0, (kind, x, y))
        self.assertGreaterEqual(seen, 5)

    def test_a_counter_leaves_a_way_round_it(self):
        templates = _level_module("templates")
        self.assertGreaterEqual(templates.COUNTER_PASS, 1024)


class SignOverAnOpeningTests(unittest.TestCase):
    def test_sloped_composition_reserves_what_the_compiler_draws(self):
        from unittest.mock import patch
        from bloodmap.lettering import tile_for
        from bloodmap.placement import drawn_extent
        from bloodmap.planar_layout import PlanarLayout
        from bloodmap.render_slots import surface_z
        from bloodmap.slope import SlopeSpec

        wallplane = _level_module("wallplane")
        art = {847: (64, 64, 5, -96), tile_for("A"): (8, 11, 0, -2),
               tile_for("B"): (10, 11, 1, 2)}
        layout = PlanarLayout(tile_extents={tile: (h, y) for tile, (_, h, _, y) in art.items()})
        hinge = ((0, 1024), (0, 0))
        layout.add_region("walk", [(0, 0), (8192, 0), (8192, 1024), (0, 1024)],
                          ceiling_z=-16384, floor_z=16384, declared_zero_exit=True,
                          ceiling_slope=SlopeSpec(hinge=hinge, heinum=512),
                          floor_slope=SlopeSpec(hinge=hinge, heinum=64))
        layout.set_player_start("walk", x=4096, y=512, z=4000)
        with patch.object(wallplane, "art", return_value=art):
            made = wallplane.composition(
                layout, "sloped", "walk", (8192, 1024), (0, 1024), t=0.503,
                top_player_heights=2.5,
                blocks=(wallplane.painting(847, x_repeat=32, y_repeat=32),
                        wallplane.caption("AB", size=(40, 48))))
            self.assertEqual(made["skipped"], [])
            self.assertIsNone(wallplane.sprite(
                layout, "too-tall", "walk", (8192, 1024), (0, 1024),
                tile=847, x_repeat=32, y_repeat=200, cstat=16))
            reserved = wallplane.occupancy(layout)

        disk = layout.compile().level.to_disk_map()
        rendered = []
        for sprite in disk.sprites:
            width, height, x_offset, y_offset = art[sprite.picnum]
            top, bottom = drawn_extent(height, y_offset, sprite.y_repeat, sprite.cstat, sprite.z)
            centre = width // 2 + x_offset
            left = sprite.x - sprite.x_repeat * centre // 4
            right = sprite.x + sprite.x_repeat * (width - centre) // 4
            rendered.append(wallplane.Rect(left, right, top, bottom))
            for x in (left, right):
                ceiling, floor = surface_z(disk, sprite.sector, x, sprite.y)
                self.assertLessEqual(ceiling, top)
                self.assertLessEqual(bottom, floor)
        banner, *caption = rendered
        self.assertEqual(len(caption), 2)
        self.assertGreaterEqual(min(glyph.z0 for glyph in caption) - banner.z1, 1696)
        point = (disk.sprites[0].x, disk.sprites[0].y)
        self.assertEqual(reserved[wallplane._plane_key(point, (1.0, 0.0))].taken, rendered)

    def test_wall_slot_search_lowers_a_drip_under_the_sewer_vault(self):
        from unittest.mock import patch
        from bloodmap.planar_layout import PlanarLayout
        from bloodmap.slope import SlopeSpec

        wallplane = _level_module("wallplane")
        layout = PlanarLayout()
        layout.add_region("walk", [(0, 0), (4096, 0), (4096, 512), (0, 512)],
                          ceiling_z=0, floor_z=28672,
                          ceiling_slope=SlopeSpec(hinge=((0, 0), (4096, 0)), rise_z=8192))
        with patch.object(wallplane, "art", return_value={54: (128, 64, 0, 0)}):
            got = wallplane.sprite(layout, "drip", "walk", (4096, 512), (0, 512),
                                   tile=54, x_repeat=32, y_repeat=40, cstat=150,
                                   height_player_heights=1.21, required=True)
        self.assertEqual(got, "drip")
        self.assertLess(layout.placements[0].anchor["height_player_heights"], 1.21)

    def test_an_opening_blocks_a_sprite_only_where_it_is_open(self):
        """A sign over a shelf's head has wall behind it."""
        import types

        wallplane = _level_module("wallplane")
        room = types.SimpleNamespace(floor_z=0, ceiling_z=-28672)
        shelf = types.SimpleNamespace(floor_z=-8192, ceiling_z=-20480)
        link = types.SimpleNamespace(region_a="room", region_b="shelf",
                                     a1=(512, 0), a2=(2048, 0))
        layout = types.SimpleNamespace(
            regions={"room": room, "shelf": shelf}, connections={"c": link},
            placements={})
        spans = wallplane.portal_spans(layout, "room", (0, 0), (2560, 0))
        self.assertEqual(spans, [(512, 2048, -20480, -8192)])


if __name__ == "__main__":
    unittest.main()
