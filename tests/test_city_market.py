"""The market district as built: the stalls, the meat market's act, the Demeter that can be boarded."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVEL = ROOT / "projects" / "blood-city" / "level"
CITY = LEVEL / "blood-city-current.MAP"
PU = 1024


@unittest.skipUnless(CITY.exists(), "the city is not built")
class MarketTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if str(LEVEL) not in sys.path:
            sys.path.insert(0, str(LEVEL))
        from bloodmap.format import read_map
        from bloodmap.model import record_extra, record_fields
        cls.disk = read_map(CITY)
        cls.sectors = [record_fields(s) for s in cls.disk.sectors]
        cls.walls = [record_fields(w) for w in cls.disk.walls]
        cls.sprites = [record_fields(s) for s in cls.disk.sprites]
        cls.extra = [record_extra(s) or {} for s in cls.disk.sprites]
        cls.sector_extra = [record_extra(s) or {} for s in cls.disk.sectors]

    def ring(self, sector):
        s = self.sectors[sector]
        return [self.walls[w] for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"])]

    def at(self, x, y, near):
        from bloodmap.sector_geom import sector_at
        return sector_at(self.disk.to_level_ir(), int(x * PU), int(y * PU), floor_near=near)

    def test_no_bare_platform_stands_before_the_hall(self):
        import meat_market
        for name, x, y, *_rest in meat_market.STALLS:
            s = self.sectors[self.at(x + 1, y - 0.3, 0)]
            self.assertEqual(8192 - s["floor_z"], meat_market.COUNTER_RISE, name)
            roof = [p for p in self.sprites if p["picnum"] == meat_market.STRIPE and p["cstat"] & 48 == 32
                    and abs(p["x"] - (x + 1) * PU) < 1400 and abs(p["y"] - y * PU) < 1400]
            self.assertTrue(roof, name)
            #: a body walks under it
            self.assertTrue(all(8192 - p["z"] > 1.5 * 16960 for p in roof), name)
        #: what was there: three platforms of boardwalk, 3,072 high
        left = [i for i, s in enumerate(self.sectors) if s["floor_z"] == 8192 - 3072 and s["ceiling_stat"] & 1
                and all(40 * PU <= w["y"] <= 50 * PU for w in self.ring(i))]
        self.assertEqual(left, [])

    def test_the_lever_in_the_gallery_raises_the_cold_store_s_door(self):
        import meat_market as m
        door = self.at((m.DOOR[0] + m.DOOR[2]) / 2, 45.5, 4096)
        self.assertEqual(self.sectors[door]["type"], 600)
        channel = self.sector_extra[door]["rx_id"]
        senders = [i for i, e in enumerate(self.extra) if e.get("tx_id") == channel]
        self.assertEqual(len(senders), 1)
        lever = self.sprites[senders[0]]
        self.assertEqual(self.sectors[lever["sector"]]["floor_z"], 8192 - m.GALLERY_RISE)
        self.assertTrue(self.extra[senders[0]]["trigger_push"])
        self.assertFalse(self.sector_extra[door]["trigger_wall_push"])     # by the lever alone
        #: every step of the stair up to it can be stepped
        floors = [8192] + [self.sectors[self.at(m.LOBBY[2] + (k + 0.5) * m.TREAD, 48.7, 8192 - 4096 * (k + 1))]["floor_z"]
                           for k in range(m.TREADS)] + [8192 - m.GALLERY_RISE]
        self.assertTrue(all(a - b == 4096 for a, b in zip(floors, floors[1:])), floors)

    def test_the_armor_is_behind_the_steel_door_and_wakes_something(self):
        armor = [i for i, p in enumerate(self.sprites) if p["type"] == 140 and 3.5 * PU < p["x"] < 6 * PU
                 and 42.5 * PU < p["y"] < 47.75 * PU]
        self.assertEqual(len(armor), 1)
        channel = self.extra[armor[0]]["tx_id"]
        woken = [i for i, e in enumerate(self.extra) if e.get("rx_id") == channel and self.sprites[i]["type"] == 18]
        self.assertEqual(len(woken), 3)

    def test_the_meat_hangs_from_the_ceiling_to_head_height(self):
        import meat_market as m
        from bloodmap.placement import drawn_extent
        import wallplane
        _w, height, _x, offset = wallplane.art()[m.CARCASS]
        meat = [p for p in self.sprites if p["picnum"] == m.CARCASS and p["type"] == 416
                and 6.5 * PU < p["x"] < 13.5 * PU and 40 * PU < p["y"] < 48 * PU]
        self.assertEqual(len(meat), len(m.FILES) * len(m.HOOKS))
        for p in meat:
            top, bottom = drawn_extent(height, offset, p["y_repeat"], p["cstat"], p["z"])
            self.assertLess(abs(top - (8192 - m.HALL_CLEAR)), 64)
            self.assertTrue(8192 - 16960 < bottom < 8192 - 4096, bottom)
            self.assertFalse(p["cstat"] & 1)                    # a body walks through the meat

    def test_the_demeter_can_be_boarded_and_left_and_not_fallen_from(self):
        import harbour_ship as ship
        import l3_market
        deck_z = 8192 - l3_market.SHIP_RIM + l3_market.SHIP_DECK_DROP
        gang = self.at(sum(ship.GANG) / 2, 56.5, 8192)
        self.assertEqual(self.sectors[gang]["floor_z"], 8192)
        self.assertNotEqual(self.sectors[gang]["floor_heinum"], 0)
        from bloodmap.render_slots import surface_z
        top = surface_z(self.disk, gang, int(sum(ship.GANG) / 2 * PU), int(57.25 * PU) - 2)[1]
        self.assertLess(abs(top - deck_z), 256)                 # it ends on the deck
        beyond = {w["next_sector"] for w in self.ring(gang)}
        deck = self.at(16.5, 58.0, deck_z)
        quay = self.at(14.9, 55.8, 8192)
        self.assertTrue({deck, quay} <= beyond)
        #: every edge between anything walked on and the water blocks
        water = [i for i, s in enumerate(self.sectors) if s["floor_picnum"] == l3_market.SEA_TILE and s["ceiling_stat"] & 1]
        for i in water:
            for w in self.ring(i):
                if w["next_sector"] >= 0 and self.sectors[w["next_sector"]]["floor_z"] in (8192, deck_z - l3_market.SHIP_DECK_DROP):
                    self.assertTrue(w["cstat"] & 1)

    def test_the_hold_is_a_step_at_a_time_and_its_locker_is_a_secret_behind_a_panel(self):
        import harbour_ship as ship
        import l3_market
        from bloodmap import motion
        deck_z = 8192 - l3_market.SHIP_RIM + l3_market.SHIP_DECK_DROP
        y = sum(ship.DOORWAY) / 2
        floors = [self.sectors[self.at(x, y, near)]["floor_z"] for x, near in (
            (14.75, deck_z), (14.375, deck_z + 4096), (14.0, deck_z + 8192), (13.0, deck_z + 12288))]
        self.assertEqual(floors, [deck_z + 4096 * k for k in range(4)])
        panel = self.at(sum(ship.PARTITION) / 2, sum(ship.PANEL) / 2, deck_z - ship.HOUSE)
        self.assertEqual(self.sectors[panel]["type"], 600)
        x = self.sector_extra[panel]
        self.assertEqual(x["on_floor_z"], floors[-1])
        self.assertTrue(x["trigger_wall_push"] or x["trigger_push"])
        locker = self.at(11.6, 59.0, floors[-1])
        self.assertEqual(self.sector_extra[locker]["tx_id"], motion.secret_credit()["tx_id"])

    def test_the_district_costs_no_more_than_it_did(self):
        stage = json.loads((LEVEL.parent / "reports" / "build-manifest.json").read_text("utf-8"))["light_stage"]
        self.assertLess(stage["walls"], 16384)


if __name__ == "__main__":
    unittest.main()
