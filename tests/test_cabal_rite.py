"""Read the Cabal's chamber, its sign, its people and the rite's one chain from the city's MAP bytes."""

from collections import Counter, deque
from math import atan2, hypot, pi
from pathlib import Path
import sys
import unittest

from bloodmap import blasts, compositions, posed, wiring
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.sector_geom import sector_at, sector_walls, wall_segment

LEVEL = Path("projects/blood-city/level")
BODY = PLAYER_PROFILES["blood"]


def reach(disk, start, *, through_glass=False):
    """Every sector a standing body can walk to: no jump, no crouch, no blocked portal."""
    seen, queue = {start}, deque([start])
    while queue:
        here = queue.popleft()
        f = record_fields(disk.sectors[here])
        for w in sector_walls(disk, here):
            edge = record_fields(disk.walls[w])
            there = edge["next_sector"]
            if there < 0 or there in seen:
                continue
            g = record_fields(disk.sectors[there])
            blocked = (edge["cstat"] | record_fields(disk.walls[edge["next_wall"]])["cstat"]) & 1
            if blocked and not (through_glass and edge["type"] == 511):
                continue
            (ax, ay), (bx, by) = wall_segment(disk, w)
            if hypot(bx - ax, by - ay) < BODY.body_width:
                continue
            if min(f["floor_z"], g["floor_z"]) - max(f["ceiling_z"], g["ceiling_z"]) < BODY.standing_height:
                continue
            if f["floor_z"] - g["floor_z"] > BODY.max_step:
                continue
            seen.add(there)
            queue.append(there)
    return seen


class CabalRiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import cabal_rite
        import wires
        cls.R, cls.wires = cabal_rite, wires
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.level = cls.disk.to_level_ir()

    def at(self, x, y, floor):
        sector = sector_at(self.level, int(x), int(y), floor_near=floor)
        self.assertIsNotNone(sector)
        self.assertEqual(record_fields(self.disk.sectors[sector])["floor_z"], floor)
        return sector

    def chamber(self):
        """Sprites within the chamber and behind its window."""
        cx, cy = self.R.CENTRE
        for index, sprite in enumerate(self.disk.sprites):
            f = record_fields(sprite)
            if hypot(f["x"] - cx, f["y"] - cy) < 13000 and 40000 < f["z"] < 170000 and f["y"] > self.R.QUAY_FACE - 2200:
                yield index, f, record_extra(sprite) or {}

    def on(self, name, kinds=None):
        channel = self.wires.channel(name)
        return [(i, f, x) for i, f, x in self.chamber()
                if x.get("rx_id") == channel and (kinds is None or f["type"] in kinds)]

    def test_the_whole_chamber_is_walked_from_the_quay_and_the_gullet_only_when_the_rose_has_burst(self):
        R = self.R
        quay = self.at(R.CENTRE[0], R.QUAY_FACE - 900, R.QUAY)
        gallery = self.at(R.CENTRE[0] - 6000, R.CENTRE[1] + 900, R.QUAY)
        floor = self.at(R.CENTRE[0] + 3700, R.CENTRE[1] - 300, R.FLOOR)
        dais = self.at(R.CENTRE[0] - 1200, 64800, R.DAIS)
        apse = self.at(R.CENTRE[0], R.SOUTH + 400, R.APSE_FLOOR)
        heart = self.at(R.HEART[0] + 1200, R.HEART[1], R.HEART_FLOOR)
        before = reach(self.disk, quay)
        for place in (gallery, floor, dais, apse):
            self.assertIn(place, before)
        self.assertNotIn(heart, before)
        self.assertIn(heart, reach(self.disk, quay, through_glass=True))
        self.assertIn(quay, reach(self.disk, heart, through_glass=True))

    def test_nobody_gets_into_the_well(self):
        well = self.at(*self.R.CENTRE, self.R.BRIM)
        self.assertNotIn(well, reach(self.disk, self.at(self.R.CENTRE[0] + 3700, self.R.CENTRE[1] - 300, self.R.FLOOR)))
        for w in sector_walls(self.disk, well):
            edge = record_fields(self.disk.walls[w])
            beyond = record_fields(self.disk.sectors[edge["next_sector"]])
            if not beyond["floor_stat"] & 2:              # a tooth is sloped; the rest is the rim
                self.assertTrue(edge["cstat"] & 1)

    def test_the_sign_is_blood_cut_in_the_floor(self):
        lines = [s for s in self.disk.sectors if record_fields(s)["floor_picnum"] == self.R.BLOOD
                 and record_fields(s)["floor_z"] == self.R.FLOOR + 512]
        self.assertGreaterEqual(len(lines), 2)
        # it fills the floor, and burns until the second pair of fires dies, all of it alike (the owner, 2026-11-24)
        self.assertGreater(self.R.STAR / self.R.ARENA, 0.85)
        channel = self.wires.channel("cabal:fires-2")
        for s in lines:
            x = record_extra(s)
            self.assertEqual((x["rx_id"], x["state"], x["busy"], x["shade_floor"]), (channel, 1, 65536, 1))
            self.assertEqual(record_fields(s)["floor_shade"], self.R.SIGN_DEAD)
            self.assertEqual(record_fields(s)["floor_shade"] + x["amplitude"], self.R.SIGN_LIT)

    def test_the_celebrants_face_the_well_and_are_deaf(self):
        cx, cy = self.R.CENTRE
        seen = 0
        for _i, f, x in self.chamber():
            if f["type"] in (201, 202) and hypot(f["x"] - cx, f["y"] - cy) < self.R.STAR:
                seen += 1
                want = round(atan2(cy - f["y"], cx - f["x"]) * 1024 / pi)
                self.assertLess(abs((f["angle"] - want + 1024) % 2048 - 1024), 24)
                self.assertTrue(x["dude_deaf"])
        self.assertEqual(seen, len(self.R.CELEBRANTS))

    def test_the_composition_reader_finds_what_was_meant(self):
        """The same reader that found E2M9's circle finds this one: a round room, rings in it, people at a focus."""
        cx, cy = self.R.CENTRE
        rows = [r for r in compositions.observe_compositions(self.disk)
                if hypot(r["centre"][0] - cx, r["centre"][1] - cy) < 400]
        kinds = Counter(r["kind"] for r in rows)
        self.assertTrue(kinds["nest"] or kinds["round"], kinds)

    def test_the_stone_beasts_death_is_one_chain_that_does_the_whole_rite(self):
        beast = next(i for i, f, _x in self.chamber() if f["type"] == 207)
        chain = posed.chain_of(wiring.chains(self.disk), f"sprite {beast}")
        after, report = posed.posed(self.disk, chain)
        well = self.at(*self.R.CENTRE, self.R.BRIM)
        self.assertEqual(record_fields(after.sectors[well])["floor_z"], self.R.SUNK)
        fires = [i for k in (1, 2, 3) for i, _f, _x in self.on(f"cabal:fires-{k}", {30})]
        self.assertEqual(len(fires), 6)
        for i in fires:
            self.assertEqual(record_extra(self.disk.sprites[i])["state"], 1)
            self.assertEqual(record_extra(after.sprites[i])["state"], 0)
        # the horned thing bursts: a gib object of stone, locked so that no blast but its own wire breaks it
        horned, _f, x = next(row for row in self.chamber() if row[1]["picnum"] == 1840)
        self.assertEqual((record_fields(self.disk.sprites[horned])["type"], x["rx_id"], x["state"], x["locked"], x["data_1"]),
                         (417, self.wires.channel("cabal:burst"), 1, 1, 20))
        panes = [w for w, wall in enumerate(self.disk.walls) if record_fields(wall)["over_picnum"] == self.R.ROSE]
        self.assertEqual(len(panes), 2)
        for w in panes:
            self.assertTrue(record_fields(self.disk.walls[w])["cstat"] & 1)
            self.assertFalse(record_fields(after.walls[w])["cstat"] & 1)
        self.assertEqual(len(self.on("cabal:broken", {244})), len(self.R.RISERS))
        self.assertEqual(len(self.on("cabal:window", {208})), 2)
        self.assertEqual({x["data_1"] for _i, _f, x in self.on("cabal:window", {18})}, {206})
        said = [x["data_1"] for _i, _f, x in self.on("cabal:says", {711})]
        self.assertEqual(said, [3056])                                        # "Rest in pieces."

    def test_the_stone_beast_is_the_enemy_and_turns_when_the_mouth_shuts(self):
        _i, f, x = next(row for row in self.chamber() if row[1]["type"] == 207)
        self.assertEqual((f["picnum"], f["pal"], x["rx_id"], x["tx_id"]),
                         (1470, 5, self.wires.channel("cabal:shut"), self.wires.channel("cabal:broken")))
        self.assertTrue(x["trigger_off"] and x["decoupled"] and not x["trigger_on"])  # its death says it, its waking does not

    def test_the_fire_climbs_and_hurts_nobody_below(self):
        """Death Wish's chain: one wire, each blast its own wait; none of them reaches a body on the floor, the steps or the gallery."""
        chain = next(c for c in blasts.chains(self.disk) if c.channel == self.wires.channel("cabal:broken"))
        self.assertGreaterEqual(len(chain.steps), 12)
        up = [b for b in chain.blasts if b.z < self.R.FLOOR and b.wait < 30]
        self.assertGreater(up[0].z - up[-1].z, BODY.standing_height)
        self.assertEqual([b.wait for b in up], sorted(b.wait for b in up))
        cx, cy = self.R.CENTRE
        bodies = []
        for s in self.disk.sectors:
            f = record_fields(s)
            first = record_fields(self.disk.walls[f["wall_ptr"]])
            if f["floor_z"] in (self.R.FLOOR, self.R.FLOOR + 512, self.R.DAIS, self.R.QUAY) and hypot(first["x"] - cx, first["y"] - cy) < 7200:
                for w in range(f["wall_ptr"], f["wall_ptr"] + f["wall_count"]):
                    q = record_fields(self.disk.walls[w])
                    bodies.append((q["x"], q["y"], f["floor_z"] - 9000))
        self.assertGreater(len(bodies), 60)
        # the well's own lie on the blood and have gone down with it when they go off
        well = self.R.SUNK - 900
        at = [(b.x, b.y, well if b.z > self.R.FLOOR else b.z) for b in chain.blasts]
        self.assertTrue(blasts.harmless(at, bodies))

    def test_the_congregation_looks_at_the_well(self):
        """The owner, 2026-11-24: "they should be all looking into the center"; it is only their angle."""
        cx, cy = self.R.CENTRE
        rows = [f for _i, f, _x in self.chamber() if f["picnum"] == 2870]
        self.assertEqual(len(rows), len(self.R.CONGREGATION))
        for f in rows:
            want = round(atan2(cy - f["y"], cx - f["x"]) * 1024 / pi)
            self.assertLess(abs((f["angle"] - want + 1024) % 2048 - 1024), 24)

    def test_nothing_here_is_shown_by_the_editor_as_something_else(self):
        """XMapEdit draws a switched zap (456) as lightning (1156), whatever its tile: the owner saw lightning where the statue is."""
        self.assertFalse([i for i, f, _x in self.chamber() if f["type"] in (455, 456)])

    def test_the_fires_take_their_light_with_them(self):
        """Every sector the fires light is authored dark, lit while its state is on, and an OFF is what comes."""
        channel = self.wires.channel("cabal:fires-2")
        lit = [x for s in self.disk.sectors if (x := record_extra(s)) and x["rx_id"] == channel and x["amplitude"]]
        self.assertGreaterEqual(len(lit), 30)
        for x in lit:
            self.assertEqual((x["state"], x["amplitude"] < 0, x["shade_ceiling"]), (1, True, 0))
        for k in (1, 2, 3):
            channel = self.wires.channel(f"cabal:fires-{k}")
            senders = [x for s in self.disk.sprites if (x := record_extra(s)) and x["tx_id"] == channel]
            self.assertEqual({x["command"] for x in senders}, {0})

    def test_the_mouth_shuts_behind_whoever_steps_over_the_ring_and_opens_again(self):
        channel = self.wires.channel("cabal:shut")
        gates = [(s, record_extra(s)) for s in self.disk.sectors if (record_extra(s) or {}).get("rx_id") == channel]
        self.assertTrue(gates)
        for sector, x in gates:
            f = record_fields(sector)
            self.assertEqual((x["off_ceiling_z"], x["on_ceiling_z"]), (f["ceiling_z"], f["floor_z"]))
            self.assertTrue(x["wait_time_a"] and x["retrigger_a"])            # it lets go by itself
        senders = Counter((x["command"], bool(x["trigger_enter"])) for s in self.disk.sectors
                          if (x := record_extra(s)) and x["tx_id"] == channel)
        self.assertTrue(senders[1, True])
        relays = [x for s in self.disk.sprites if (x := record_extra(s)) and x["tx_id"] == channel]
        self.assertEqual([x["command"] for x in relays], [0])                 # and the bursting window opens it

    def test_the_stone_beast_stands_in_the_rose_over_the_horned_thing(self):
        """Seen from the mouth: the line from a standing eye to its head passes over the thing's horns."""
        priest = next(f for _i, f, _x in self.chamber() if f["type"] == 207)
        horned = next(f for _i, f, _x in self.chamber() if f["picnum"] == 1840)
        self.assertLess(abs(priest["x"] - self.R.CENTRE[0]), 64)
        self.assertEqual((priest["angle"], horned["angle"]), (512, 1536))       # it faces the rose, the thing in the well the door
        eye_y, eye_z = self.R.NORTH, self.R.QUAY - BODY.standing_height
        head_z = priest["z"] - priest["y_repeat"] * 4 * 115 // 2
        along = (self.R.CENTRE[1] - eye_y) / (priest["y"] - eye_y)
        horns = horned["z"] - horned["y_repeat"] * 4 * 163 // 2
        self.assertLess(eye_z + (head_z - eye_z) * along, horns)

    def test_once_it_is_dead_the_kerb_shuts_nothing(self):
        disarm, shut = self.wires.channel("cabal:disarm"), self.wires.channel("cabal:shut")
        rings = [x for s in self.disk.sectors if (x := record_extra(s)) and x["tx_id"] == shut]
        self.assertTrue(rings)
        self.assertEqual({x["rx_id"] for x in rings}, {disarm})
        senders = [x for s in self.disk.sprites if (x := record_extra(s)) and x["tx_id"] == disarm]
        self.assertEqual([(x["command"], x["rx_id"]) for x in senders], [(6, self.wires.channel("cabal:broken"))])

    def test_the_teeth_draw_back_with_the_well(self):
        channel = self.wires.channel("cabal:broken")
        teeth = [s for s in self.disk.sectors if (record_extra(s) or {}).get("rx_id") == channel
                 and record_fields(s)["floor_stat"] & 2]
        self.assertEqual(len(teeth), 10)
        for s in teeth:
            self.assertGreater(record_extra(s)["on_floor_z"], record_extra(s)["off_floor_z"])

    def test_the_hung_have_something_in_their_pockets(self):
        kinds = {f["type"] for _i, f, _x in self.chamber()}
        for _face, what, *_rest in self.R.POCKETS:
            self.assertIn(what, kinds)

    def test_a_shot_rose_does_not_break(self):
        """It is the rite's to break: no pane takes a bullet's trigger."""
        for wall in self.disk.walls:
            if record_fields(wall)["over_picnum"] == self.R.ROSE:
                extra = record_extra(wall)
                self.assertFalse(extra and extra["trigger_vector"])

    def test_the_heart_opens_the_flesh_and_stops(self):
        eyes = [w for w, wall in enumerate(self.disk.walls) if record_fields(wall)["picnum"] == self.R.EYE
                and hypot(record_fields(wall)["x"] - self.R.HEART[0], record_fields(wall)["y"] - self.R.HEART[1]) < 800]
        self.assertEqual(len(eyes), 1)
        answer = record_extra(self.disk.walls[eyes[0]])
        self.assertTrue(answer["trigger_vector"] and answer["trigger_push"] and answer["trigger_once"])
        chain = posed.chain_of(wiring.chains(self.disk), f"wall {eyes[0]}")
        after, _report = posed.posed(self.disk, chain)
        opened = [s for s, sector in enumerate(self.disk.sectors)
                  if (record_extra(sector) or {}).get("rx_id") == self.wires.channel("cabal:heart")]
        self.assertEqual(len(opened), 2)
        for s in opened:
            self.assertEqual(record_fields(self.disk.sectors[s])["ceiling_z"], record_fields(self.disk.sectors[s])["floor_z"])
            f = record_fields(after.sectors[s])
            self.assertGreaterEqual(f["floor_z"] - f["ceiling_z"], BODY.standing_height)


if __name__ == "__main__":
    unittest.main()
