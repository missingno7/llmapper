"""Read the underpass, the machine hall's deck and the works yard from the city's MAP bytes."""

from pathlib import Path
import sys
import unittest

from bloodmap import sight
from bloodmap.format import read_map
from bloodmap.mechanism import CARRY_WITH
from bloodmap.model import record_extra, record_fields
from bloodmap.motion import marker_pair
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.sector_geom import outline_and_holes, sector_at, sector_walls

LEVEL = Path("projects/blood-city/level")
BODY = PLAYER_PROFILES["blood"]
PU = 1024
#: a standing player's eye over his floor: `bloodmap.viewplan.eye_z`'s
EYE = 15264


class FoundryWardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import gameplay
        import l3_foundry
        import l3_shed
        import underpass
        import wires
        cls.U, cls.S, cls.F, cls.G, cls.wires = underpass, l3_shed, l3_foundry, gameplay, wires
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.level = cls.disk.to_level_ir()

    def at(self, x, y, floor):
        sector = sector_at(self.level, int(x * PU), int(y * PU), floor_near=floor)
        self.assertIsNotNone(sector, (x, y))
        return sector

    def floor(self, sector):
        return record_fields(self.disk.sectors[sector])["floor_z"]

    def path_of(self, points, floor):
        """The floors met walking a line of plan points."""
        return [self.floor(self.at(x, y, floor)) for x, y in points]

    # -- the underpass ----------------------------------------------------

    def test_one_walks_from_the_yard_to_the_avenue(self):
        U = self.U
        here = None
        walk = [(x / 8, 19.0 - 0.4) for x in range(int(U.YARD_FACE * 8) + 4, int(44 * 8), -1)]
        walk += [(44.0, y / 4) for y in range(19 * 4, 32 * 4)]
        walk += [(x / 8, 32.4) for x in range(44 * 8, int(U.AVENUE_FACE * 8) - 4, -1)]
        for x, y in walk:
            near = here if here is not None else U.GRADE
            floor = self.floor(self.at(x, y, near))
            if here is not None:
                self.assertLessEqual(abs(floor - here), BODY.max_step, (x, y))
            here = floor
        self.assertEqual(here, U.GRADE)

    def test_the_passage_is_long_and_no_street_is_seen_through_it(self):
        U = self.U
        self.assertGreaterEqual(U.AVENUE_MOUTH[1] - U.YARD_MOUTH[0], 13)
        sector = self.at(48.75, 19.0, U.GRADE)
        eye = (48.75 * PU, 19.0 * PU, U.GRADE - EYE)
        self.assertFalse(sight.sees(self.level, sector, eye, (40.0 * PU, 32.0 * PU, U.GRADE - EYE)))

    def test_every_bay_is_one_sector_and_the_tubes_are_few(self):
        U = self.U
        for cell, x, y, lit in U.TUBES:
            sector = self.at(x, y, U.FLOOR)
            tile = U.TUBE if lit else U.DEAD_TUBE
            found = [s for s in self.disk.sprites if record_fields(s)["sector"] == sector and record_fields(s)["picnum"] == tile]
            self.assertEqual(len(found), 1, cell)
            if cell.startswith("bay"):
                ring, _holes = outline_and_holes(self.disk, sector)
                xs = [p[0] for p in ring]
                self.assertEqual((min(xs), max(xs)), (U._q(U.WEST), U._q(U.EAST)), cell)
        self.assertGreaterEqual(sum(1 for *_c, lit in U.TUBES if not lit), 2)

    def test_the_failing_tube_takes_its_light_with_it(self):
        U = self.U
        x, y = next((x, y) for cell, x, y, _lit in U.TUBES if cell == U.LOOSE)
        extra = record_extra(self.disk.sectors[self.at(x, y, U.FLOOR)])
        self.assertTrue(extra["shade_always"])
        self.assertLess(extra["amplitude"], 0)

    def test_leaving_the_ticket_hall_is_what_moves_the_pram(self):
        U = self.U
        channel = self.wires.channel(U.WIRE)
        senders = [i for i, s in enumerate(self.disk.sectors) if (record_extra(s) or {}).get("tx_id") == channel]
        hall = self.at(46.0, 27.5, U.FLOOR)
        self.assertEqual(senders, [hall])
        extra = record_extra(self.disk.sectors[hall])
        self.assertTrue(extra["trigger_exit"] and extra["trigger_once"] and extra["trigger_on"] and extra["dude_lockout"])
        plate = self.at((U.PLATE[0] + U.PLATE[2]) / 2, (U.PLATE[1] + U.PLATE[3]) / 2, U.FLOOR)
        hears = {i for i, s in enumerate(self.disk.sectors) if (record_extra(s) or {}).get("rx_id") == channel}
        self.assertIn(plate, hears)
        # the bulb's light is on the same wire: the bed, the end and the plate, lit while ON
        self.assertEqual(len(hears), 3)
        for sector in hears:
            x = record_extra(self.disk.sectors[sector])
            self.assertEqual(x["state"], 1)
            self.assertLess(x["amplitude"], 0)
        prams = [record_fields(s) for s in self.disk.sprites if record_fields(s)["picnum"] == U.PRAM]
        self.assertEqual(len(prams), 1)
        self.assertEqual(prams[0]["sector"], plate)
        self.assertTrue(prams[0]["cstat"] & CARRY_WITH)

    def test_the_pram_stays_in_the_bed_and_comes_to_the_gate(self):
        U = self.U
        plate = self.at((U.PLATE[0] + U.PLATE[2]) / 2, (U.PLATE[1] + U.PLATE[3]) / 2, U.FLOOR)
        pair = marker_pair(self.disk, plate)
        self.assertIsNotNone(pair)
        self.assertGreater(U.PLATE[0] - U.COMES, U.BARS)
        self.assertLess(U.PLATE[0] - U.COMES - U.BARS, 1.0)
        self.assertLess(U.PLATE[2], U.BED)

    def test_the_gate_is_a_gate_and_one_sees_through_it(self):
        U = self.U
        gates = [w for w in self.disk.walls if record_fields(w)["over_picnum"] == U.GATE
                 and record_fields(w)["x"] == U._q(U.BARS) and record_fields(w)["cstat"] & 16]
        self.assertEqual(len(gates), 2)
        hall = self.at(46.0, 26.5, U.FLOOR)
        eye = (46.0 * PU, 26.5 * PU, U.FLOOR - EYE)
        self.assertTrue(sight.sees(self.level, hall, eye, (50.5 * PU, 26.5 * PU, U.FLOOR - 4096)))

    def test_nobody_is_in_it(self):
        U = self.U
        for s in self.disk.sprites:
            f = record_fields(s)
            if f["status"] == 6 and f["sector"] >= 0:
                inside = U._q(U.AVENUE_FACE) < f["x"] < U._q(U.YARD_FACE) and U._q(18) < f["y"] < U._q(33)
                self.assertFalse(inside and self.floor(f["sector"]) == U.FLOOR, f["type"])

    # -- the machine hall ---------------------------------------------------

    def test_the_gallery_climbs_to_a_deck_and_the_deck_goes_down(self):
        S = self.S
        deck = S.GRADE - S.DECK_RISE
        up = self.path_of([(51.0, 6.2), (50.25, 6.2), (49.75, 6.2), (49.25, 6.2), (48.0, 6.2), (46.5, 6.2)], deck)
        down = self.path_of([(46.5, 6.2), (45.25, 6.2), (44.75, 6.2), (44.25, 6.2), (43.6, 7.4)], deck)
        for floors in (up, down):
            for a, b in zip(floors, floors[1:]):
                self.assertLessEqual(abs(a - b), BODY.max_step)
        self.assertEqual((up[0], up[-1], down[-1]), (S.GRADE, deck, S.GRADE))

    def test_the_key_and_the_lever_are_seen_from_the_deck(self):
        S = self.S
        deck = S.GRADE - S.DECK_RISE
        key = next(record_fields(s) for s in self.disk.sprites if record_fields(s)["type"] == 102)
        self.assertEqual((key["x"], key["y"]), (round(self.G.KEYS["flame"][1] * PU), round(self.G.KEYS["flame"][2] * PU)))
        spots = [(x / 4, y / 4) for x in range(183, 190) for y in range(22, 28)]
        seen = [p for p in spots if sight.sees(self.level, self.at(*p, deck), (p[0] * PU, p[1] * PU, deck - EYE),
                                               (key["x"], key["y"], S.GRADE - S.BELT_RISE - 6000))]
        self.assertTrue(seen, "the key is seen from nowhere on the deck")
        lever = next(record_fields(s) for s in self.disk.sprites
                     if (record_extra(s) or {}).get("tx_id") == S.BELT_CHANNEL)
        eye = (46.5 * PU, 6.2 * PU, deck - EYE)
        self.assertTrue(sight.sees(self.level, self.at(46.5, 6.2, deck), eye, (lever["x"] + 64, lever["y"], lever["z"])))

    def test_the_hood_over_the_key_is_a_light(self):
        S = self.S
        belt = self.at(43.75, 9.5, S.GRADE)
        f = record_fields(self.disk.sectors[belt])
        self.assertEqual(f["ceiling_picnum"], S.STRIP_LIGHT)
        self.assertEqual(f["floor_z"] - f["ceiling_z"], S.HOOD_CLEAR)
        self.assertGreaterEqual(S.HOOD_CLEAR, 2 * BODY.standing_height)

    def test_what_taking_the_key_wakes_stands_somewhere(self):
        _n, x, y, _f, wakes = self.G.KEYS["flame"]
        channel = self.wires.channel("key:flame")
        spawns = [record_fields(s) for s in self.disk.sprites if (record_extra(s) or {}).get("rx_id") == channel]
        self.assertEqual(len(spawns), len(wakes))
        self.assertTrue(any(record_fields(self.disk.sectors[s["sector"]])["floor_picnum"] == self.S.SEWAGE for s in spawns))
        self.assertTrue(any(self.floor(s["sector"]) == self.S.GRADE - self.S.DECK_RISE for s in spawns))

    # -- the yard -----------------------------------------------------------

    def test_the_yard_is_one_paving_with_a_grate_laid_on_it(self):
        here = self.at(50.5, 21.5, 8192)
        ring, _holes = outline_and_holes(self.disk, here)
        self.assertNotIn((50 * PU, 21 * PU), ring)            # neither the shaft's square ...
        self.assertNotIn((int(49.5 * PU), int(20.5 * PU)), ring)      # ... nor the ring round it
        grates = [s for s in self.disk.sprites if record_fields(s)["picnum"] == 502
                  and abs(record_fields(s)["x"] - 50.5 * PU) < 1024 and abs(record_fields(s)["y"] - 21.5 * PU) < 1024]
        self.assertTrue(grates)

    def test_the_chimney_is_brick_all_round(self):
        x0, y0, x1, y1 = self.F.CHIMNEY
        walls = [record_fields(w) for w in self.disk.walls]
        faces = [f for f in walls if f["next_sector"] < 0 and all(
            x0 <= p["x"] <= x1 and y0 <= p["y"] <= y1 for p in (f, walls[f["point2"]]))]
        self.assertGreaterEqual(len(faces), 8)
        self.assertEqual({f["picnum"] for f in faces}, {self.F.CHIMNEY_BRICK})


if __name__ == "__main__":
    unittest.main()
