"""Read Gravesend's Phantom carriage, departure sequence, lights and exits from MAP bytes."""

from collections import Counter, deque
from math import hypot
import sys
import unittest
from pathlib import Path

from shapely.geometry import Point, Polygon

from bloodmap import mechanism, motion, posed, swept_state, wiring
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.motion_sim import body_health, rigid_bodies
from bloodmap.placement import drawn_extent
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.sector_geom import outline_and_holes, sector_at, sector_walls, wall_segment

LEVEL = Path("projects/blood-city/level")
BODY = PLAYER_PROFILES["blood"]


def walking_sectors(disk, start):
    """Follow standing, unblocked portals with steps a player can climb."""
    reached, frontier = {start}, deque([start])
    while frontier:
        current = frontier.popleft()
        here = record_fields(disk.sectors[current])
        for w in sector_walls(disk, current):
            edge = record_fields(disk.walls[w])
            target = edge["next_sector"]
            if target < 0 or target in reached:
                continue
            back = record_fields(disk.walls[edge["next_wall"]])
            if (edge["cstat"] | back["cstat"]) & 1:
                continue
            a, b = wall_segment(disk, w)
            if hypot(b[0] - a[0], b[1] - a[1]) < BODY.body_width:
                continue
            there = record_fields(disk.sectors[target])
            clear = min(here["floor_z"], there["floor_z"]) - max(here["ceiling_z"], there["ceiling_z"])
            if clear < BODY.standing_height or here["floor_z"] - there["floor_z"] > BODY.max_step:
                continue
            reached.add(target)
            frontier.append(target)
    return reached


class PhantomTerminusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(LEVEL) not in sys.path:
            sys.path.insert(0, str(LEVEL))
        import carriage
        import phantom_terminus as terminus
        import wallplane
        import wires

        cls.carriage, cls.design = carriage, terminus
        cls.art = wallplane.art()
        cls.destination_tiles = [wallplane.tile_for(letter) for letter in "PHANTOM"]
        cls.disk = read_map(LEVEL / "blood-city-current.MAP")
        cls.wires = {name: wires.channel(name)
                     for name in (terminus.DEPART, terminus.RUN, terminus.PRIZE, terminus.ARM,
                                  terminus.COACH_STATE, terminus.CAR_LIGHT, terminus.PLATFORM_ENTRY)}
        cls.nodes = wiring.nodes(cls.disk)
        cls.aisle = cls.sector(cls, *terminus.COACH(35, 25), terminus.DECK)
        cls.body, = [b for b in rigid_bodies(cls.disk) if cls.aisle in b.members]
        cls.prize, = [node["index"] for node in cls.nodes
                      if node["type"] == 50 and node["tx"] == cls.wires[terminus.PRIZE]]
        cls.departure = posed.chain_of(wiring.chains(cls.disk), f"sprite {cls.prize}")

    def sector(self, x, y, floor):
        return sector_at(self.disk, x, y, floor_near=floor)

    def test_the_carriage_is_one_body_of_sectors_inside_one_host(self):
        self.assertGreater(len(self.body.members), 50)
        health = body_health(self.disk, self.body, steps=64)
        self.assertEqual((health["problems"], health["notes"]), ([], []))
        host = health["host"]
        self.assertEqual(swept_state.hosts(self.disk)[host] & set(self.body.members),
                         swept_state.hosts(self.disk)[host])
        self.assertEqual(list(self.body.displacement), [-self.design.TRAVEL, 0])
        self.assertEqual(self.body.rx, self.wires[self.design.RUN])
        roles = Counter()
        for index in self.body.members:
            f, x = record_fields(self.disk.sectors[index]), record_extra(self.disk.sectors[index])
            self.assertTrue(x["drag"] and x["state"])
            if f["floor_z"] == f["ceiling_z"]:
                roles["solid"] += 1
                continue
            # the owner: "The ceiling of the train if it is part of the train it should move"
            self.assertTrue(f["floor_stat"] & f["ceiling_stat"] & 64, index)
            roles["seat" if f["floor_z"] == self.design.SEAT_Z else "open"] += 1
        self.assertGreaterEqual(roles["solid"], 14)
        self.assertEqual(roles["seat"], 9)
        panes = [w for s in self.body.members for w in sector_walls(self.disk, s)
                 if record_fields(self.disk.walls[w])["over_picnum"] in
                 (self.carriage.GLASS, self.carriage.BROKEN)
                 and record_fields(self.disk.walls[w])["cstat"] & 16]
        self.assertEqual(len(panes) % 2, 0)
        self.assertGreaterEqual(len(panes) // 2, 12)
        for pane in panes:
            wall = record_fields(self.disk.walls[pane])
            here = next(s for s in self.body.members if pane in sector_walls(self.disk, s))
            a, b = (record_fields(self.disk.sectors[s]) for s in (here, wall["next_sector"]))
            self.assertIn(wall["next_sector"], self.body.members)
            self.assertEqual((a["floor_z"], a["ceiling_z"]), (b["floor_z"], b["ceiling_z"]))
            self.assertTrue(wall["cstat"] & 1)

    def test_everything_aboard_rides_and_the_dead_sit_on_the_benches(self):
        fittings = [f for s in self.disk.sprites if (f := record_fields(s))["sector"] in self.body.members
                    and f["status"] not in {10, 16}]
        self.assertTrue(fittings)
        self.assertTrue(all(f["cstat"] & mechanism.CARRY_WITH for f in fittings))
        seated = [f for f in fittings if f["picnum"] in self.design.SEATED]
        self.assertGreaterEqual(len(seated), 8)
        for f in (*seated, record_fields(self.disk.sprites[self.prize])):
            self.assertEqual(record_fields(self.disk.sectors[f["sector"]])["floor_z"], self.design.SEAT_Z)
            # whoever sits there is drawn standing up from it, and from no flat cut-out
            self.assertEqual(f["cstat"] & 48, 0)
            _, height, _, offset = self.art[f["picnum"]]
            _, bottom = drawn_extent(height, offset, f["y_repeat"], f["cstat"])
            self.assertEqual(f["z"] + bottom, self.design.SEAT_Z - 16)
        # the wheels hang in the host's space and ride because it moves as the car does (E1M2 s34)
        host = body_health(self.disk, self.body)["host"]
        fields, extra = record_fields(self.disk.sectors[host]), record_extra(self.disk.sectors[host])
        self.assertEqual((fields["type"], extra["rx_id"]), (614, self.wires[self.design.RUN]))
        self.assertFalse(any(record_fields(self.disk.walls[w])["cstat"] & motion.CARRY
                             for w in sector_walls(self.disk, host)))
        wheels = [f for s in self.disk.sprites if (f := record_fields(s))["sector"] == host
                  and f["picnum"] == 2320]
        self.assertEqual(len(wheels), 8)
        self.assertTrue(all(f["cstat"] & mechanism.CARRY_WITH for f in wheels))
        voice = [s for s in self.disk.sprites if record_fields(s)["type"] == 709
                 and record_fields(s)["sector"] in self.body.members]
        self.assertEqual(len(voice), 1)
        self.assertEqual(tuple(record_extra(voice[0])[f"data_{i}"] for i in range(1, 5)), (115, 277, 115, 277))
        fascia = sorted((f for f in fittings if f["picnum"] in self.destination_tiles
                         and f["cstat"] & 48 == 16), key=lambda f: f["x"])
        self.assertEqual([f["picnum"] for f in fascia], self.destination_tiles)

    def test_the_whole_travel_leaves_a_lane_and_a_way_out_at_both_berths(self):
        host = body_health(self.disk, self.body)["host"]
        bay = Polygon(outline_and_holes(self.disk, host)[0])
        west, north, east, south = self.design.CAR
        for shift in (0, self.design.TRAVEL // 2, self.design.TRAVEL):
            car = Polygon([(west + shift, north), (east + shift, north), (east + shift, south), (west + shift, south)])
            self.assertTrue(bay.contains(car))
        self.assertGreaterEqual(north - bay.bounds[1], 2 * BODY.body_width)
        # at the door the gap is one a body cannot fall through
        edge = self.sector(sum(self.design.DOOR) // 2, self.design.SOUTH_EDGE + 64, self.design.DECK)
        self.assertLess(self.design.SOUTH_EDGE - south, BODY.body_radius)
        self.assertEqual(record_fields(self.disk.sectors[edge])["floor_z"], self.design.DECK)

        fired, _ = posed.posed(self.disk, self.departure)
        for pose in (self.disk, fired):
            home = sector_at(pose, 48448, -8192, floor_near=self.design.GHOST_FLOOR)
            stop = sector_at(pose, 68160, -9824, floor_near=self.design.GHOST_FLOOR + 2048)
            pit = sector_at(pose, 47616, -16640, floor_near=self.design.TRACK_FLOOR)
            for start in (self.aisle, stop, pit):
                self.assertIn(home, walking_sectors(pose, start))
            self.assertIn(stop, walking_sectors(pose, home))

    def test_prize_runs_the_show_and_buttons_recall_the_car(self):
        self.assertIn(record_fields(self.disk.sprites[self.prize])["sector"], self.body.members)
        self.assertEqual(self.departure["cause"], ["pickup"])
        self.assertTrue(self.departure["once"])
        sent = [(step["to"], step["command"]) for step in self.departure["steps"]]
        for member in self.body.members:
            self.assertIn((f"sector {member}", motion.CMD_OFF), sent)
        effects = [self.disk.sprites[int(step["to"].split()[1])] for step in self.departure["steps"]
                   if step["to"].startswith("sprite ")]
        for kind, value in ((711, 276), (711, 3034), (18, 210), (19, 1200)):
            self.assertIn((kind, value), [(record_fields(s)["type"], record_extra(s)["data_1"])
                                         for s in effects])
        coach = record_extra(self.disk.sectors[self.aisle])
        self.assertEqual((coach["command"], coach["tx_id"]),
                         (motion.CMD_STATE, self.wires[self.design.COACH_STATE]))
        calls = [n for n in self.nodes if n["kind"] == "sprite"
                 and n["tx"] == self.wires[self.design.RUN] and "push" in n["causes"]]
        self.assertEqual(len(calls), 3)
        aboard = [n for n in calls if record_fields(self.disk.sprites[n["index"]])["sector"] in self.body.members]
        handle, = aboard
        self.assertEqual(record_extra(self.disk.sprites[handle["index"]])["command"], motion.CMD_TOGGLE)
        via_pickup, _ = posed.posed(self.disk, self.departure)
        via_handle, _ = posed.posed(
            self.disk, posed.chain_of(wiring.chains(self.disk), f'sprite {handle["index"]}'))
        for member in self.body.members:
            self.assertEqual(outline_and_holes(via_pickup, member), outline_and_holes(via_handle, member))
            a, b = (record_fields(d.walls[sector_walls(d, member)[0]]) for d in (self.disk, via_pickup))
            self.assertEqual((b["x"] - a["x"], b["y"] - a["y"]), (self.design.TRAVEL, 0))

    def lit_by(self, **wanted):
        return [(i, record_fields(s), x) for i, s in enumerate(self.disk.sectors)
                if (x := record_extra(s)) and all(x.get(k) == v for k, v in wanted.items()) and x["amplitude"]]

    def test_a_lamp_that_switches_takes_its_light_with_it(self):
        entry, depart, link = (self.wires[n] for n in (self.design.PLATFORM_ENTRY, self.design.DEPART,
                                                       self.design.CAR_LIGHT))
        for channel in (entry, depart):
            rows = self.lit_by(rx_id=channel)
            self.assertTrue(rows)
            # lit until the wire turns it on: saved bright, OFF, with a wave that darkens
            self.assertTrue(all(x["amplitude"] > 0 and not x["state"] and not x["shade_always"] for *_, x in rows))
        driver, = [x for s in self.disk.sectors if (x := record_extra(s))
                   and x["tx_id"] == link and x["command"] == motion.CMD_LINK]
        self.assertEqual(driver["rx_id"], self.wires[self.design.RUN])
        fallen = self.lit_by(rx_id=link, state=1)
        self.assertTrue(fallen)
        self.assertTrue(all(x["busy"] == 65536 for *_, x in fallen))
        inside = [x for i, _, x in self.lit_by(shade_always=1) if i in self.body.members]
        self.assertGreater(len(inside), 20)
        self.assertEqual(len({(x["shade_wave"], x["shade_frequency"], x["shade_phase"]) for x in inside}), 1)
        # the reapers' niches: each flickers on a beat of its own, its mouth with it
        beats = set()
        for x0 in self.design.WATCHERS:
            niche = self.sector(x0 + 576, -18016, self.design.WATCH_FLOOR)
            light = record_extra(self.disk.sectors[niche])
            self.assertTrue(light and light["shade_always"] and light["amplitude"] < 0)
            beats.add((light["shade_wave"], light["shade_frequency"], light["shade_phase"]))
            self.assertTrue(any(record_extra(self.disk.sectors[n])
                                and record_extra(self.disk.sectors[n])["shade_phase"] == light["shade_phase"]
                                and record_extra(self.disk.sectors[n])["shade_always"]
                                for w in sector_walls(self.disk, niche)
                                if (n := record_fields(self.disk.walls[w])["next_sector"]) >= 0))
        self.assertEqual(len(beats), len(self.design.WATCHERS))

    def test_the_station_keeps_its_secret_and_its_first_step(self):
        secret = self.sector(48448, -8192, self.design.GHOST_FLOOR)
        credit = record_extra(self.disk.sectors[secret])
        self.assertEqual(credit["tx_id"], motion.CHANNEL_SECRET_FOUND)
        self.assertFalse(credit["rx_id"])
        self.assertTrue(credit["trigger_once"] and credit["trigger_enter"])
        # as many as the level says it has
        declared, = [x["command"] - motion.CMD_NUMERIC_BASE for x in map(record_extra, self.disk.sprites)
                     if x and x["tx_id"] == motion.CHANNEL_SET_TOTAL_SECRETS]
        self.assertEqual(sum((record_extra(s) or {}).get("tx_id") == motion.CHANNEL_SECRET_FOUND
                             for s in self.disk.sectors), declared)
        channel = self.wires[self.design.PLATFORM_ENTRY]
        throat = record_extra(self.disk.sectors[self.sector(49984, -10240, self.design.GHOST_FLOOR)])
        self.assertEqual((throat["tx_id"], throat["command"]), (channel, motion.CMD_TOGGLE))
        self.assertTrue(throat["trigger_enter"] and throat["trigger_once"])
        whistle, = [record_extra(s) for s in self.disk.sprites if (record_extra(s) or {}).get("rx_id") == channel]
        self.assertEqual((whistle["data_2"], whistle["busy_time"]), (276, 0))

    def test_tiles_the_owner_ruled_on(self):
        # 1717 is a wall of morgue drawers and 51, 52 are a wall's broken plaster
        self.assertFalse([i for i, s in enumerate(self.disk.sectors)
                          if 1717 in (record_fields(s)["floor_picnum"], record_fields(s)["ceiling_picnum"])])
        self.assertFalse([i for i, s in enumerate(self.disk.sprites)
                          if record_fields(s)["picnum"] in (51, 52) and record_fields(s)["cstat"] & 48 != 16])

    def test_the_drowned_carriage_stands_free(self):
        plan, axes = self.design.WRECK_PLAN, self.design.WRECK
        outline = Polygon([axes(u, v) for u, v in ((0, 0), (plan.length, 0), (plan.length, self.carriage.WIDTH),
                                                   (0, self.carriage.WIDTH))])
        cavern = Polygon(self.design.CAVERN)
        self.assertTrue(cavern.contains(outline.buffer(2 * BODY.body_width)))
        for x, y in outline.buffer(BODY.body_radius + 64).exterior.coords[::4]:
            around = self.sector(int(x), int(y), self.design.WATER_FLOOR)
            f = record_fields(self.disk.sectors[around])
            self.assertGreaterEqual(f["floor_z"] - f["ceiling_z"], BODY.standing_height)
        self.assertTrue(outline.contains(Point(*axes(35, 25))))


if __name__ == "__main__":
    unittest.main()
