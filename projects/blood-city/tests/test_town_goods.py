"""The town is dressed with what Blood's own town maps are dressed with.

The owner, 2026-11-18: "try using more variety of assets, check other blood
city maps like DWE3M1, E3M1 ... Looks like you have quite limited set now."
`tools/mine_city_assets.py` counts it and records how each tile is set down;
`projects/blood-city/level/goods.py` is the plan, by place.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")
CITY = LEVEL / "blood-city-current.MAP"
MANIFEST = LEVEL.parent / "reports" / "build-manifest.json"
E3M1 = Path("maps/blood/campaign/E3M1.MAP")


def _goods():
    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))
    import goods
    return goods


class DecorationCensusTests(unittest.TestCase):
    def test_what_counts_as_decoration(self):
        from tools.mine_city_assets import is_decoration

        base = {"cstat": 0, "type": 0, "picnum": 759}
        self.assertTrue(is_decoration(base))
        self.assertTrue(is_decoration({**base, "type": 416}))     # a "thing"
        self.assertTrue(is_decoration({**base, "type": 32}))      # a candle
        self.assertFalse(is_decoration({**base, "type": 201}))    # a cultist
        self.assertFalse(is_decoration({**base, "type": 41}))     # a pickup
        self.assertFalse(is_decoration({**base, "cstat": 0x8000}))  # invisible
        self.assertFalse(is_decoration({**base, "picnum": 3810}))   # a letter

    @unittest.skipUnless(E3M1.exists(), "no E3M1")
    def test_a_town_map_is_counted_with_how_each_tile_is_set_down(self):
        from tools.mine_city_assets import census, variety

        found = census([str(E3M1)])
        self.assertGreaterEqual(len(found), 50)
        for row in found.values():
            for key in ("count", "maps", "where", "align", "x_repeat",
                        "y_repeat", "cstat", "shade", "pal", "type", "status"):
                self.assertIn(key, row)
            self.assertIn(row["align"], ("face", "wall", "floor", "other"))
        self.assertEqual(variety(E3M1)["decoration_tiles"], len(found))


class GoodsPlanTests(unittest.TestCase):
    def setUp(self):
        self.goods = _goods()

    def _tiles(self):
        g = self.goods
        used = {t for _s, items in g.ON_TOP + g.ON_FLOOR for t, _u, _v in items}
        used |= {t for _s, tiles in g.ROWS for t in tiles}
        used |= {row[2] for row in g.ON_WALL} | {row[2] for row in g.ON_STREET}
        used |= {row[3] for row in g.ON_GROUND}
        return used

    def test_every_tile_is_used_by_two_of_bloods_town_maps(self):
        import json

        anchors = json.loads(Path(
            "knowledge/blood/design/owner-anchors-v1.json").read_text("utf-8"))
        named = {a["picnum"] for a in anchors["anchors"] if "picnum" in a}
        for tile in sorted(self._tiles()):
            self.assertIn(tile, self.goods.ASSETS, tile)
            #: ...or the owner has named it, which outranks a count
            self.assertTrue(len(self.goods.ASSETS[tile]["maps"]) >= 2
                            or tile in named,
                            f"tile {tile} is in one town map only")

    def test_every_tile_has_been_looked_at_and_named(self):
        for tile in sorted(self._tiles()):
            self.assertIn(tile, self.goods.NAMES, tile)

    def test_a_tile_is_set_down_with_the_towns_own_fields(self):
        fields = self.goods.fields(759)
        row = self.goods.ASSETS[759]
        self.assertEqual(fields["picnum"], 759)
        for key in ("x_repeat", "y_repeat", "cstat", "shade", "type", "status"):
            self.assertEqual(fields[key], row[key], key)

    def test_the_plan_is_by_place_and_not_scattered(self):
        g = self.goods
        #: nothing stands on a street's floor: the campaign's own city
        #: street is nearly bare outdoors, and the one thing tried (a bin
        #: at each shop door) read as a bucket of gore
        street_things = {row[3] for row in g.ON_GROUND
                         if row[0] in ("theatre_row", "old_crossing",
                                       "market_slip", "foundry_ward")}
        self.assertEqual(street_things, set())
        #: and a bottle belongs to the saloon, not to the church
        church = {t for s, items in g.ON_TOP + g.ON_FLOOR if "st_gallows" in s
                  for t, _u, _v in items}
        self.assertFalse(church & {759, 605, 606, 574, 521})

    def test_the_tiles_the_owner_has_not_named_are_listed(self):
        unnamed = self.goods.unnamed()
        self.assertTrue(set(unnamed) <= self._tiles())
        self.assertEqual(unnamed, sorted(unnamed))


@unittest.skipUnless(CITY.exists() and MANIFEST.exists(), "the city is not built")
class DressedCityTests(unittest.TestCase):
    def test_the_city_is_dressed_with_more_than_the_campaigns_own_street(self):
        from tools.mine_city_assets import variety

        found = variety(CITY)
        #: 38 before; E3M1 has 61
        self.assertGreaterEqual(found["decoration_tiles"], 75)

    def test_nearly_everything_planned_was_set_down_and_the_rest_is_named(self):
        report = json.loads(MANIFEST.read_text("utf-8"))["goods"]
        planned = report["placed"] + len(report["refused"])
        self.assertGreaterEqual(report["placed"] / planned, 0.85)
        for line in report["refused"]:
            self.assertTrue(line)                      # a reason, not a blank

    def test_a_thing_on_a_counter_stands_on_it(self):
        from bloodmap.format import read_map

        disk = read_map(CITY)
        bottles = [s.fields for s in disk.sprites
                   if int(s.fields["picnum"]) in (759, 605, 606, 574, 521)]
        self.assertGreaterEqual(len(bottles), 8)
        raised = 0
        for f in bottles:
            sector = disk.sectors[int(f["sector"])].fields
            self.assertGreaterEqual(int(f["z"]), int(sector["ceiling_z"]))
            self.assertLessEqual(int(f["z"]), int(sector["floor_z"]))
            raised += int(sector["floor_z"]) < 8192
        #: on a bar, a table or a display, which stand above the room's floor
        self.assertGreaterEqual(raised, 6)


if __name__ == "__main__":
    unittest.main()
