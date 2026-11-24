"""A variant of a built map, and the shop surrounds it was first used on.

`tools/whatif.py` answers "what does this feature contribute" by removing it
from the finished map. The tests pin that it changes only what it is told to,
refuses to write a variant that is the map it started from, and never claims
to be a build.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")
CITY = LEVEL / "blood-city-current.MAP"
TAGS = LEVEL / "blood-city-current.tags.json"


def _obj(fields):
    return type("O", (), {"fields": fields})()


def _disk():
    """Two square sectors side by side sharing one wall, and three sprites."""
    disk = type("D", (), {})()
    disk.sectors = [
        _obj({"wall_ptr": 0, "wall_count": 4, "floor_shade": 10,
              "ceiling_shade": 10, "floor_picnum": 4, "ceiling_picnum": 1}),
        _obj({"wall_ptr": 4, "wall_count": 4, "floor_shade": 20,
              "ceiling_shade": 20, "floor_picnum": 352, "ceiling_picnum": 1}),
    ]
    square = [(0, 0), (100, 0), (100, 100), (0, 100)]
    disk.walls = []
    for base, dx in ((0, 0), (4, 100)):
        for index, (x, y) in enumerate(square):
            disk.walls.append(_obj({
                "x": x + dx, "y": y, "point2": base + (index + 1) % 4,
                "next_sector": -1, "picnum": 7, "over_picnum": 0, "shade": 0}))
    disk.walls[1].fields["next_sector"] = 1
    disk.walls[7].fields["next_sector"] = 0
    disk.sprites = [
        _obj({"x": 50, "y": 50, "sector": 0, "picnum": 641}),
        _obj({"x": 150, "y": 50, "sector": 1, "picnum": 641}),
        _obj({"x": 150, "y": 60, "sector": 1, "picnum": 9}),
    ]
    return disk


class EditTests(unittest.TestCase):
    def test_a_sector_is_selected_by_number_and_set(self):
        from tools.whatif import apply

        disk = _disk()
        report = apply(disk, [{"on": "sectors", "where": {"id": [1]},
                               "set": {"floor_shade": 32}}])
        self.assertEqual(report[0]["touched"], 1)
        self.assertEqual(disk.sectors[1].fields["floor_shade"], 32)
        self.assertEqual(disk.sectors[0].fields["floor_shade"], 10)

    def test_walls_are_selected_by_the_sector_that_owns_them(self):
        from tools.whatif import apply

        disk = _disk()
        apply(disk, [{"on": "walls", "where": {"sector": [1]},
                      "set": {"picnum": 99}}])
        self.assertEqual([w.fields["picnum"] for w in disk.walls],
                         [7, 7, 7, 7, 99, 99, 99, 99])

    def test_a_tag_names_sectors_for_any_kind_of_record(self):
        from tools.whatif import apply

        disk = _disk()
        tags = {"shop": [1]}
        apply(disk, [{"on": "sprites", "where": {"intent": "shop",
                                                 "picnum": [641]},
                      "drop": True}], tags=tags)
        self.assertEqual([(s.fields["sector"], s.fields["picnum"])
                          for s in disk.sprites], [(0, 641), (1, 9)])

    def test_add_and_copy(self):
        from tools.whatif import apply

        disk = _disk()
        apply(disk, [{"on": "sectors", "where": {"id": [0]},
                      "set": {"floor_shade": {"add": 5},
                              "ceiling_shade": {"copy": "floor_picnum"}}}])
        self.assertEqual(disk.sectors[0].fields["floor_shade"], 15)
        self.assertEqual(disk.sectors[0].fields["ceiling_shade"], 4)

    def test_a_rectangle_selects_a_wall_by_its_midpoint(self):
        from tools.whatif import apply

        disk = _disk()
        report = apply(disk, [{"on": "walls",
                               "where": {"rect": [40, -5, 60, 5]},
                               "set": {"shade": 9}}])
        self.assertEqual(report[0]["touched"], 1)
        self.assertEqual(disk.walls[0].fields["shade"], 9)

    def test_only_sprites_can_be_dropped(self):
        from tools.whatif import WhatIfError, apply

        with self.assertRaises(WhatIfError):
            apply(_disk(), [{"on": "walls", "where": {"id": [0]},
                             "drop": True}])

    def test_an_unknown_selector_or_field_is_refused(self):
        from tools.whatif import WhatIfError, apply

        with self.assertRaises(WhatIfError):
            apply(_disk(), [{"on": "walls", "where": {"colour": [1]},
                             "set": {"shade": 1}}])
        with self.assertRaises(WhatIfError):
            apply(_disk(), [{"on": "walls", "where": {"id": [0]},
                             "set": {"brightness": 1}}])


@unittest.skipUnless(CITY.exists() and TAGS.exists(), "the city is not built")
class CityVariantTests(unittest.TestCase):
    def test_a_variant_that_changes_nothing_is_refused(self):
        from tools.whatif import WhatIfError, variant

        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(WhatIfError):
                variant(CITY, Path(folder) / "same.MAP",
                        [{"on": "sprites", "where": {"picnum": [-5]},
                          "drop": True}])

    def test_unlighting_the_displays_changes_them_and_nothing_else(self):
        from bloodmap.format import read_map
        from tools.whatif import load_tags, variant

        tags = load_tags(CITY)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "unlit.MAP"
            report = variant(CITY, out, [
                {"on": "sectors", "where": {"intent": "shop_display"},
                 "set": {"floor_shade": 32}}], tags=tags)
            before, after = read_map(CITY), read_map(out)
        self.assertFalse(report["claims"]["is_a_build"])
        self.assertNotEqual(report["source_sha256"], report["target_sha256"])
        displays = set(tags["shop_display"])
        self.assertEqual(report["edits"][0]["touched"], len(displays))
        for index, (a, b) in enumerate(zip(before.sectors, after.sectors)):
            if index in displays:
                self.assertEqual(int(b.fields["floor_shade"]), 32)
            else:
                self.assertEqual(dict(a.fields), dict(b.fields), index)
        self.assertEqual(len(before.walls), len(after.walls))
        self.assertEqual(len(before.sprites), len(after.sprites))


@unittest.skipUnless(CITY.exists() and TAGS.exists(), "the city is not built")
class ShopSurroundTests(unittest.TestCase):
    """A shop is fronted in its own material, named on its fascia, and lit."""

    BODY = 16960

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.disk = read_map(CITY)
        cls.tags = json.loads(TAGS.read_text("utf-8"))

    def _walls(self, sector_id):
        f = self.disk.sectors[sector_id].fields
        return [self.disk.walls[w].fields
                for w in range(int(f["wall_ptr"]),
                               int(f["wall_ptr"]) + int(f["wall_count"]))]

    def test_every_window_has_a_surround_a_display_and_a_lamp(self):
        self.assertEqual(len(self.tags["shopfront"]), 4)
        self.assertEqual(len(self.tags["shop_display"]), 4)
        lamps = [s for s in self.disk.sprites
                 if int(s.fields["picnum"]) == 641
                 and int(s.fields["sector"]) in set(self.tags["shop_display"])]
        self.assertEqual(len(lamps), 4)

    def test_a_surround_stands_on_the_pavement_and_rises_a_fascia(self):
        if str(LEVEL) not in sys.path:
            sys.path.insert(0, str(LEVEL))
        import glass

        for sector_id in self.tags["shopfront"]:
            reveal = self.disk.sectors[sector_id].fields
            self.assertEqual(int(reveal["floor_z"]), 8192, sector_id)
            heads = set()
            for wall in self._walls(sector_id):
                nxt = int(wall["next_sector"])
                if nxt < 0:
                    continue
                there = self.disk.sectors[nxt].fields
                if int(there["ceiling_stat"]) & 1:
                    continue                       # the street or concourse
                if int(there["floor_z"]) < 8192:   # a sash pocket, on a sill
                    heads.add(int(there["ceiling_z"]))
            self.assertEqual(len(heads), 1, sector_id)
            #: z grows downward: the reveal's ceiling is a fascia ABOVE the head
            self.assertEqual(heads.pop() - int(reveal["ceiling_z"]),
                             glass.FASCIA, sector_id)

    def test_the_surround_is_not_the_facade(self):
        facades = {400, 384, 380, 393}
        for sector_id in self.tags["shopfront"]:
            tiles = {int(w["picnum"]) for w in self._walls(sector_id)
                     if int(w["next_sector"]) < 0
                     or not int(self.disk.sectors[int(w["next_sector"])]
                                .fields["ceiling_stat"]) & 1}
            self.assertFalse(tiles & facades, (sector_id, tiles))

    def test_the_street_shops_are_named_on_their_fascias(self):
        letters = set(range(3808, 3834))
        named = {int(s.fields["sector"]) for s in self.disk.sprites
                 if int(s.fields["picnum"]) in letters
                 and int(s.fields["sector"]) in set(self.tags["shopfront"])}
        #: PAWNBROKER, PROVISIONS, MARKET HALL; the market hall's short south
        #: window has no room for one (the arcade's fronts are `arcade`'s own)
        self.assertEqual(len(named), 3)
        for sector_id in named:
            floor = int(self.disk.sectors[sector_id].fields["floor_z"])
            heights = [(floor - int(s.fields["z"])) / self.BODY
                       for s in self.disk.sprites
                       if int(s.fields["sector"]) == sector_id
                       and int(s.fields["picnum"]) in letters]
            #: the campaign's range for a sign over a street: 1.69 to 5.13
            self.assertTrue(all(1.5 <= h <= 2.6 for h in heights), heights)

    def test_rooms_behind_glass_are_brighter_than_the_street(self):
        import statistics

        street = [int(s.fields["floor_shade"]) for s in self.disk.sectors
                  if int(s.fields["ceiling_stat"]) & 1
                  and int(s.fields["floor_z"]) != int(s.fields["ceiling_z"])]
        lit = [int(self.disk.sectors[i].fields["floor_shade"])
               for i in self.tags["shop_display"] + self.tags["lit_shop"]]
        #: DukCity3 holds 13 steps between them and E3M1 holds 8
        self.assertGreaterEqual(
            statistics.median(street) - statistics.median(lit), 8)

    def test_the_glass_rule_still_holds(self):
        owner = {}
        for sector_id, sector in enumerate(self.disk.sectors):
            f = sector.fields
            for w in range(int(f["wall_ptr"]),
                           int(f["wall_ptr"]) + int(f["wall_count"])):
                owner[w] = sector_id
        for index, wall in enumerate(self.disk.walls):
            f = wall.fields
            if int(f.get("over_picnum", 0)) != 266 or not int(f["cstat"]) & 16:
                continue
            a = self.disk.sectors[owner[index]].fields
            b = self.disk.sectors[int(f["next_sector"])].fields
            self.assertEqual(int(a["floor_z"]), int(b["floor_z"]), index)
            self.assertEqual(int(a["ceiling_z"]), int(b["ceiling_z"]), index)


@unittest.skipUnless(CITY.exists() and TAGS.exists(), "the city is not built")
class PledgeRoomTests(unittest.TestCase):
    """The pawnbroker's stock is behind bars."""

    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.disk = read_map(CITY)
        cls.tags = json.loads(TAGS.read_text("utf-8"))
        cls.owner = {}
        for sector_id, sector in enumerate(cls.disk.sectors):
            f = sector.fields
            for w in range(int(f["wall_ptr"]),
                           int(f["wall_ptr"]) + int(f["wall_count"])):
                cls.owner[w] = sector_id

    def test_there_is_one_and_bars_stand_in_front_of_it(self):
        self.assertEqual(len(self.tags["vault"]), 1)
        vault = self.tags["vault"][0]
        bars = [(index, wall.fields) for index, wall in enumerate(self.disk.walls)
                if int(wall.fields.get("over_picnum", 0)) == 463
                and int(wall.fields["cstat"]) & 16
                #: (the city has barred windows too, since 2026-11-18)
                and vault in (self.owner[index],
                              int(wall.fields["next_sector"]))]
        self.assertEqual(len(bars), 2)             # the two sides of one wall
        self.assertIn(vault, {self.owner[i] for i, _f in bars}
                      | {int(f["next_sector"]) for _i, f in bars})
        for index, fields in bars:
            #: blocking: you see the pledges and cannot reach them
            self.assertTrue(int(fields["cstat"]) & 1, index)
            #: and no step band shares the bars' record
            a = self.disk.sectors[self.owner[index]].fields
            b = self.disk.sectors[int(fields["next_sector"])].fields
            self.assertEqual(int(a["floor_z"]), int(b["floor_z"]), index)
            self.assertEqual(int(a["ceiling_z"]), int(b["ceiling_z"]), index)

    def test_it_stands_above_the_shop_under_a_lower_ceiling_and_is_lit(self):
        vault = self.disk.sectors[self.tags["vault"][0]].fields
        self.assertLess(int(vault["floor_z"]), 8192)        # up a step
        self.assertGreater(int(vault["ceiling_z"]), 8192 - 24576)
        street = 32
        self.assertLessEqual(int(vault["floor_shade"]), street - 6)

    def test_something_is_pledged_in_it(self):
        inside = [s for s in self.disk.sprites
                  if int(s.fields["sector"]) == self.tags["vault"][0]]
        self.assertGreaterEqual(len(inside), 3)


class GrilleTests(unittest.TestCase):
    def _level(self, floor_b=0):
        level = type("L", (), {})()
        level.sectors = [
            {"fields": {"wall_ptr": 0, "wall_count": 1, "floor_z": 0,
                        "ceiling_z": -1000}},
            {"fields": {"wall_ptr": 1, "wall_count": 1, "floor_z": floor_b,
                        "ceiling_z": -1000}},
        ]
        level.walls = [
            {"fields": {"x": 0, "y": 0, "point2": 1, "next_sector": 1,
                        "cstat": 0, "over_picnum": 0, "x_repeat": 8,
                        "y_repeat": 8}},
            {"fields": {"x": 100, "y": 0, "point2": 0, "next_sector": 0,
                        "cstat": 0, "over_picnum": 0, "x_repeat": 8,
                        "y_repeat": 8}},
        ]
        return level

    def test_bars_are_masked_blocking_and_not_breakable(self):
        from bloodmap.glass import GRILLE_CSTAT, grille

        level = self._level()
        report = grille(level, [(-10, -10, 110, 10)], tile=463)
        self.assertEqual(report["barred"], [0, 1])
        self.assertEqual(report["refused"], [])
        for wall in level.walls:
            self.assertEqual(wall["fields"]["over_picnum"], 463)
            self.assertEqual(wall["fields"]["cstat"] & GRILLE_CSTAT,
                             GRILLE_CSTAT)
            self.assertNotIn("blood", wall)             # no XWALL: unbreakable

    def test_bars_over_a_step_are_reported(self):
        from bloodmap.glass import grille

        report = grille(self._level(floor_b=-512), [(-10, -10, 110, 10)],
                        tile=463)
        self.assertEqual(report["refused"], [0, 1])


if __name__ == "__main__":
    unittest.main()
