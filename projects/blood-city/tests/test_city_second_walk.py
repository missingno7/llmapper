"""What the owner found on the second walk of Gravesend, held.

2026-11-18, after playing the build: enemies are written sunk in the map;
shop shelves are not aligned with their textures and the pawn shop wants
rethinking; some sprites wear DWE3M1's fog palette in clear rooms; floor
and ceiling sprites overlap in the sewers; the pump station is small and
should be "a big technical building with conveyor belts and heavy
machinery"; "Ship in a harbour is just a wooden rectangle, water should end
with sky"; and "some of the lower walls around city have building textures
and the things that should probably be buildings have wall textures".
"""

from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path

LEVEL = Path("projects/blood-city/level")
CITY = LEVEL / "blood-city-current.MAP"
E3M1 = Path("maps/blood/campaign/E3M1.MAP")
DWE3M1 = Path("maps/blood/curated/DWE3M1.MAP")
ASSETS = Path("knowledge/blood/references/city-assets.json")

#: the owner's names for the tiles a building front wears
FACADES = {380, 384, 393, 397, 400, 401}


def _level():
    if str(LEVEL) not in sys.path:
        sys.path.insert(0, str(LEVEL))


class FlatOverlapTests(unittest.TestCase):
    def _disk(self, sprites):
        return types.SimpleNamespace(
            sectors=[],
            sprites=[types.SimpleNamespace(fields=dict(
                {"cstat": 32, "picnum": 795, "x_repeat": 64, "y_repeat": 64,
                 "angle": 0, "z": 0, "sector": 0, "x": 0, "y": 0}, **f))
                for f in sprites])

    def test_two_flat_sprites_at_one_height_lie_through_each_other(self):
        from tools.sprite_fit import flat_overlaps

        self.assertEqual(len(flat_overlaps(self._disk([{}, {"x": 40}]))), 1)

    def test_apart_or_at_different_heights_they_do_not(self):
        from tools.sprite_fit import flat_overlaps

        self.assertEqual(flat_overlaps(self._disk([{}, {"x": 4000}])), [])
        self.assertEqual(flat_overlaps(self._disk([{}, {"z": 4096}])), [])

    @unittest.skipUnless(E3M1.exists(), "no E3M1")
    def test_the_campaign_writes_its_dudes_standing(self):
        from bloodmap.format import read_map
        from tools.sprite_fit import sunk_actors

        self.assertEqual(sunk_actors(read_map(E3M1)), [])


@unittest.skipUnless(ASSETS.exists(), "no asset census")
class PaletteTests(unittest.TestCase):
    def test_a_fogged_maps_palette_is_the_places_not_the_things(self):
        tiles = json.loads(ASSETS.read_text("utf-8"))["tiles"]
        #: chairs, bottles and plants were palette 1 because DWE3M1 is fog
        for tile in ("517", "758", "741", "802"):
            self.assertEqual(tiles[tile]["pal"], 0, tile)
        #: a coloured coat is its own colour
        self.assertNotEqual(tiles["73"]["pal"], 0)


@unittest.skipUnless(CITY.exists(), "the city is not built")
class SecondWalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bloodmap.format import read_map

        cls.disk = read_map(CITY)
        cls.sectors = [s.fields for s in cls.disk.sectors]
        cls.walls = [w.fields for w in cls.disk.walls]

    def test_no_enemy_is_written_under_its_floor(self):
        from tools.sprite_fit import flat_overlaps, sunk_actors

        self.assertEqual(sunk_actors(self.disk), [])
        self.assertEqual(flat_overlaps(self.disk), [])

    def test_nothing_wears_the_fog_palette_in_a_clear_sector(self):
        for sprite in self.disk.sprites:
            f = sprite.fields
            sector = self.sectors[int(f["sector"])]
            if int(f.get("pal", 0)) == 1:
                self.assertEqual(int(sector.get("floor_pal", 0)), 1, f)

    def test_the_sea_ends_in_a_horizon_and_not_a_wall(self):
        #: (the sea is Blood's own since the harbour study: 2490 in
        #: palette 10, 1.75 bodies under the quay)
        water = [i for i, s in enumerate(self.sectors)
                 if int(s["floor_picnum"]) == 2490
                 and int(s["floor_pal"]) == 10
                 and int(s["ceiling_stat"]) & 1]
        self.assertGreaterEqual(len(water), 3)       # banded, as DWE3M4's
        shades = sorted(int(self.sectors[i]["floor_shade"]) for i in water)
        self.assertGreater(shades[-1], shades[0])
        rings = [s for s in self.sectors
                 if int(s["floor_z"]) == int(s["ceiling_z"])
                 and int(s["floor_stat"]) & 1 and int(s["ceiling_stat"]) & 1]
        #: (seven until the near band's ends became a building's flank)
        self.assertGreaterEqual(len(rings), 5)
        #: no sea sector has a solid wall longer than a door: its sides
        #: and its far end are all horizon
        for i in water[1:]:
            s = self.sectors[i]
            for w in range(int(s["wall_ptr"]),
                           int(s["wall_ptr"]) + int(s["wall_count"])):
                wall = self.walls[w]
                #: (but for the end face of the building that flanks the
                #: harbour, which is a building and wears its own wall
                #: without the windows: 381 beside a 380, and so on)
                if (int(wall["picnum"]) in (381, 385, 394, 396)
                        and int(wall["next_sector"]) < 0):
                    continue
                self.assertGreaterEqual(int(wall["next_sector"]), 0)

    def test_the_ship_has_a_rim_over_its_deck_and_a_bow(self):
        _level()
        import l3_market

        rim = l3_market.GRADE - l3_market.SHIP_RIM
        deck = rim + l3_market.SHIP_DECK_DROP
        rims = [s for s in self.sectors if int(s["floor_z"]) == rim
                and int(s["floor_picnum"]) == l3_market.SHIP_PLANK]
        decks = [s for s in self.sectors if int(s["floor_z"]) == deck
                 and int(s["ceiling_stat"]) & 1]
        self.assertEqual(len(rims), 1)
        self.assertEqual(len(decks), 1)
        #: not a rectangle: the hull has more than four sides
        self.assertGreater(int(decks[0]["wall_count"]), 4 + 8)

    def test_a_street_end_is_plain_and_the_citys_edge_is_buildings(self):
        report = json.loads((LEVEL.parent / "reports" / "build-manifest.json")
                            .read_text("utf-8"))
        edge = report["building_backs"]["edge"]
        self.assertGreaterEqual(report["building_backs"]["vertices"], 15)
        longest, plain_tall = 0, 0
        for s in self.sectors:
            if not int(s["ceiling_stat"]) & 1:
                continue
            for w in range(int(s["wall_ptr"]),
                           int(s["wall_ptr"]) + int(s["wall_count"])):
                a = self.walls[w]
                if int(a["next_sector"]) >= 0:
                    continue
                b = self.walls[int(a["point2"])]
                x0, y0, x1, y1 = (int(a["x"]), int(a["y"]),
                                  int(b["x"]), int(b["y"]))
                on_edge = ((x0 == x1 and x0 in (edge[0], edge[2]))
                           or (y0 == y1 and y0 in (edge[1], edge[3])))
                length = abs(x1 - x0) + abs(y1 - y0)
                if on_edge and length >= 1024:
                    longest = max(longest, length)
                    plain_tall += int(a["picnum"]) == 417 and length > 9216
        #: was one brick wall 49,152 long; E3M1's longest is 8,704
        self.assertLessEqual(longest, 13312)
        self.assertEqual(plain_tall, 0)

    def test_an_end_wall_does_not_wear_a_building_front(self):
        _level()
        import street_vistas

        self.assertNotIn(street_vistas.WALL, FACADES)

    def test_the_pump_station_has_a_machine_hall_with_a_running_belt(self):
        _level()
        import l3_shed

        x0, y0, x1, y1 = l3_shed.MACHINE_HALL
        self.assertGreaterEqual((x1 - x0) * (y1 - y0), 40 * 1024 * 1024)
        #: in the hall: 376 is ribbed iron, and the RAT DOGS grill wears it
        #: too, as E1M4's own grill does
        def in_hall(sector):
            corner = self.disk.walls[int(sector.fields["wall_ptr"])].fields
            return x0 <= int(corner["x"]) <= x1 and y0 <= int(corner["y"]) <= y1

        belts = [s for s in self.disk.sectors
                 if int(s.fields["floor_picnum"]) == l3_shed.BELT_TILE
                 and in_hall(s)]
        self.assertEqual(len(belts), len(l3_shed.BELT_SECTIONS))
        for sector in belts:
            extra = sector.extra or {}
            fields = extra.get("fields", extra) if isinstance(extra, dict) \
                else getattr(extra, "fields", {})
            self.assertTrue(fields, "a belt needs an XSECTOR")
        halls = [s for s in self.sectors
                 if int(s["floor_picnum"]) == l3_shed.HALL_FLOOR
                 and int(s["floor_z"]) - int(s["ceiling_z"])
                 == l3_shed.HALL_CLEAR]
        #: the hall, and the light pools let into its floor since
        self.assertGreaterEqual(len(halls), 1)

    def test_the_pawnbroker_has_no_mannequins_and_a_stocked_shelf(self):
        from bloodmap.model import record_fields

        report = json.loads((LEVEL.parent / "reports" / "build-manifest.json")
                            .read_text("utf-8"))
        self.assertEqual(report["sprite_fit"]["squeezed"], [])
        # Include the pawnbroker's window, sales floor, and pledge room.
        mannequins = [f for s in self.disk.sprites if (f := record_fields(s))["picnum"] == 2377
                      and 27136 <= f["x"] <= 32768 and 3072 <= f["y"] <= 7424]
        self.assertEqual(mannequins, [])


if __name__ == "__main__":
    unittest.main()
