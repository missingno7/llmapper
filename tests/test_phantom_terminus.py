"""Read Gravesend's Phantom carriage, departure sequence and exits from MAP bytes."""

from collections import deque
from math import hypot
import sys
import unittest
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon

from bloodmap import flatsprite, mechanism, motion, posed, swept_state, wiring
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.motion_sim import blood_sweep
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
        import phantom_terminus as terminus
        import wallplane
        import wires

        cls.design = terminus
        cls.art = wallplane.art()
        cls.destination_tiles = [wallplane.tile_for(letter) for letter in "PHANTOM"]
        cls.disk = read_map(LEVEL / "blood-city-current.MAP")
        cls.wires = {name: wires.channel(name)
                     for name in (terminus.DEPART, terminus.RUN, terminus.PRIZE,
                                  terminus.ARM, terminus.COACH, terminus.BOARDING,
                                  terminus.LAMP_PULSE, terminus.PLATFORM_ENTRY,
                                  terminus.SPILL_OFF, "caleb:ghost-tunnel")}
        cls.nodes = wiring.nodes(cls.disk)
        cls.car, = [node["index"] for node in cls.nodes
                    if node["kind"] == "sector" and node["rx"] == cls.wires[terminus.RUN]]
        cls.prize, = [node["index"] for node in cls.nodes
                      if node["type"] == 42 and node["tx"] == cls.wires[terminus.PRIZE]]
        cls.departure = posed.chain_of(wiring.chains(cls.disk), f"sprite {cls.prize}")

    def test_carried_interior_and_equilevel_window_masks(self):
        fields = record_fields(self.disk.sectors[self.car])
        behavior = record_extra(self.disk.sectors[self.car])
        self.assertEqual(fields["type"], 616)
        self.assertTrue(fields["floor_stat"] & 64)
        self.assertEqual((fields["floor_pal"], fields["ceiling_pal"]), (self.design.GREEN,) * 2)
        self.assertLessEqual(max(fields["floor_shade"], fields["ceiling_shade"]), 4)
        self.assertGreaterEqual(fields["floor_z"] - fields["ceiling_z"], 24576)
        self.assertTrue(behavior["state"] and behavior["drag"])
        self.assertFalse(behavior["crush"])
        hosts = swept_state.hosts(self.disk)
        track, = [host for host, movers in hosts.items() if self.car in movers]
        self.assertEqual(hosts[track], {self.car})
        track_fields = record_fields(self.disk.sectors[track])
        self.assertEqual((fields["floor_z"], fields["ceiling_z"]),
                         (track_fields["floor_z"], track_fields["ceiling_z"]))
        windows, doors = 0, []
        for index in sector_walls(self.disk, self.car):
            wall = record_fields(self.disk.walls[index])
            other = record_fields(self.disk.walls[wall["next_wall"]])
            self.assertEqual((wall["next_sector"], other["next_sector"]), (track, self.car))
            if not wall["cstat"] & 1:
                doors.append(wall_segment(self.disk, index))
            if wall["over_picnum"] == self.design.WINDOW_MASK:
                self.assertEqual(wall["cstat"] & 0xD1, 0x51)
                self.assertEqual(other["over_picnum"], self.design.WINDOW_MASK)
                self.assertEqual(wall["pal"], self.design.GREEN)
                windows += 1
        self.assertEqual(windows, 8)
        door, = doors
        self.assertGreaterEqual(abs(door[1][0] - door[0][0]), BODY.body_width * 2)
        fittings = [s for s in self.disk.sprites
                    if (f := record_fields(s))["sector"] == self.car and f["status"] not in {10, 16}]
        self.assertTrue(fittings)
        self.assertTrue(all(record_fields(s)["cstat"] & mechanism.CARRY_WITH for s in fittings))
        seated = [record_fields(s) for s in fittings if record_fields(s)["picnum"] in self.design.SEATED]
        self.assertGreaterEqual(len(seated), 8)
        self.assertLessEqual(len(seated), 12)
        self.assertTrue(all((body["angle"], body["pal"]) == (512, 0) for body in seated))
        tops = [f for s in fittings if (f := record_fields(s))["picnum"] == 67
                and f["cstat"] & 48 == 32 and f["z"] == self.design.SEAT_Z]
        seats = [Polygon(flatsprite.footprint(top, self.art[67][:2], self.art[67][2:]))
                 for top in tops]
        for passenger in (*seated, record_fields(self.disk.sprites[self.prize])):
            with self.subTest(tile=passenger["picnum"], x=passenger["x"]):
                _, height, _, offset = self.art[passenger["picnum"]]
                _, bottom = drawn_extent(height, offset, passenger["y_repeat"], passenger["cstat"])
                self.assertEqual(passenger["z"] + bottom, self.design.SEAT_Z - 16)
                self.assertTrue(any(seat.contains(Point(passenger["x"], passenger["y"])) for seat in seats))
        sound, = [record_extra(s) for s in fittings if record_fields(s)["type"] == 709]
        self.assertEqual(tuple(sound[f"data_{i}"] for i in range(1, 5)), (115, 277, 115, 277))

    def test_entire_sweep_leaves_a_walk_on_both_sides_and_an_exit_at_both_berths(self):
        self.assertTrue(swept_state.sweep_sector(self.disk, self.car, steps=64).sound)
        track, = [host for host, movers in swept_state.hosts(self.disk).items() if self.car in movers]
        outer, holes = outline_and_holes(self.disk, track)
        self.assertEqual(len(holes), 1)
        bay = Polygon(outer)
        stroke = blood_sweep(self.disk, self.car, steps=64)
        west, north, east, south = bay.bounds
        radius = BODY.body_radius
        lanes = [LineString([(west + 512, y), (east - 512, y)])
                 for y in (north + 384, south - 384)]
        for loop in stroke:
            outline = Polygon(loop)
            self.assertTrue(bay.contains(outline.buffer(radius)))
            self.assertTrue(all(outline.distance(lane) >= radius for lane in lanes))
        self.assertEqual(motion.marker_pair(self.disk, self.car)["travel"],
                         (-self.design.TRAVEL, 0))

        fired, _ = posed.posed(self.disk, self.departure)
        for pose in (self.disk, fired):
            home = sector_at(pose, 48448, -8192, floor_near=self.design.GHOST_FLOOR)
            stop = sector_at(pose, 68160, -9824, floor_near=self.design.GHOST_FLOOR + 2048)
            self.assertIn(home, walking_sectors(pose, self.car))
            self.assertIn(home, walking_sectors(pose, stop))
            self.assertIn(stop, walking_sectors(pose, home))

    def test_prize_runs_the_show_and_buttons_recall_the_car(self):
        prize = self.disk.sprites[self.prize]
        self.assertEqual(record_fields(prize)["sector"], self.car)
        self.assertEqual(self.departure["cause"], ["pickup"])
        self.assertTrue(self.departure["once"])
        self.assertIn((f"sector {self.car}", motion.CMD_OFF),
                      [(step["to"], step["command"]) for step in self.departure["steps"]])
        affected = [step["to"] for step in self.departure["steps"]]
        effects = [self.disk.sprites[int(ref.split()[1])] for ref in affected
                   if ref.startswith("sprite ")]
        for kind, value in ((711, 276), (711, 3034), (18, 210), (19, 1200)):
            self.assertIn((kind, value), [(record_fields(s)["type"], record_extra(s)["data_1"])
                                         for s in effects])
        ghosts = [record_fields(s) for s in effects if record_fields(s)["type"] == 18]
        self.assertEqual([ghost["angle"] for ghost in ghosts], [1024, 1024])
        car = record_extra(self.disk.sectors[self.car])
        self.assertEqual(car["command"], motion.CMD_STATE)
        self.assertEqual(car["tx_id"], self.wires[self.design.COACH])
        self.assertTrue(car["trigger_on"] and car["trigger_off"])
        calls = [n for n in self.nodes if n["kind"] == "sprite"
                 and n["tx"] == self.wires[self.design.RUN] and "push" in n["causes"]]
        self.assertEqual(len(calls), 3)
        for call in calls:
            fields = record_fields(self.disk.sprites[call["index"]])
            trigger = record_extra(self.disk.sprites[call["index"]])
            self.assertEqual(fields["type"], 20)
            if fields["sector"] == self.car:
                self.assertEqual(trigger["command"], motion.CMD_TOGGLE)
                self.assertTrue(trigger["trigger_on"] and trigger["trigger_off"])
                self.assertTrue(fields["cstat"] & mechanism.CARRY_WITH)
                chain = posed.chain_of(wiring.chains(self.disk), f'sprite {call["index"]}')
                self.assertIn((f"sector {self.car}", motion.CMD_TOGGLE),
                              [(step["to"], step["command"]) for step in chain["steps"]])
            else:
                self.assertEqual(trigger["command"], motion.CMD_ON)
        handle, = [n for n in calls
                   if record_fields(self.disk.sprites[n["index"]])["sector"] == self.car]
        handle_chain = posed.chain_of(wiring.chains(self.disk), f'sprite {handle["index"]}')
        via_pickup, _ = posed.posed(self.disk, self.departure)
        via_handle, _ = posed.posed(self.disk, handle_chain)
        self.assertEqual(outline_and_holes(via_pickup, self.car), outline_and_holes(via_handle, self.car))
        self.assertNotEqual(outline_and_holes(self.disk, self.car), outline_and_holes(via_handle, self.car))

    def test_station_lighting_does_not_share_the_secret_trigger(self):
        secret = sector_at(self.disk, 48448, -8192, floor_near=self.design.GHOST_FLOOR)
        self.assertEqual(sector_at(self.disk, 48448, -8400, floor_near=self.design.GHOST_FLOOR),
                         secret)
        credit = record_extra(self.disk.sectors[secret])
        self.assertEqual(credit["tx_id"], motion.CHANNEL_SECRET_FOUND)
        self.assertFalse(credit["rx_id"] or credit["amplitude"])
        self.assertTrue(credit["trigger_once"] and credit["trigger_enter"])
        self.assertEqual(sum((record_extra(s) or {}).get("tx_id") == motion.CHANNEL_SECRET_FOUND
                             for s in self.disk.sectors), 7)
        station_entry = self.wires[self.design.PLATFORM_ENTRY]
        entry, = [record_extra(s) for s in self.disk.sectors
                  if (record_extra(s) or {}).get("tx_id") == station_entry]
        self.assertTrue(entry["trigger_enter"] and entry["trigger_once"])
        self.assertEqual(entry["command"], motion.CMD_TOGGLE)
        threshold = sector_at(self.disk, 49984, -10240, floor_near=self.design.GHOST_FLOOR)
        self.assertEqual(record_extra(self.disk.sectors[threshold])["tx_id"], station_entry)
        entry_props = [s for s in self.disk.sprites if (record_extra(s) or {}).get("rx_id") == station_entry]
        self.assertCountEqual([record_fields(s)["type"] for s in entry_props], (456, 708))
        whistle, = [record_extra(s) for s in entry_props if record_fields(s)["type"] == 708]
        self.assertEqual((whistle["data_2"], whistle["busy_time"]), (276, 0))

        car = record_extra(self.disk.sectors[self.car])
        self.assertTrue(car["trigger_enter"] and car["trigger_once"] and car["decoupled"])
        board, = [record_extra(s) for s in self.disk.sprites
                  if (record_extra(s) or {}).get("tx_id") == self.wires[self.design.BOARDING]]
        self.assertEqual((board["wait_time"], board["trigger_on"], board["trigger_off"]), (0, 1, 0))
        pulse, = [record_extra(s) for s in self.disk.sprites
                  if (record_extra(s) or {}).get("tx_id") == self.wires[self.design.LAMP_PULSE]]
        self.assertEqual((pulse["rx_id"], pulse["command"], pulse["wait_time"]),
                         (self.wires[self.design.BOARDING], motion.CMD_NOT_STATE, 2))
        self.assertTrue(pulse["trigger_on"] and pulse["trigger_off"])
        lamps = [record_fields(s) for s in self.disk.sprites
                 if (record_extra(s) or {}).get("rx_id") == self.wires[self.design.LAMP_PULSE]]
        self.assertEqual(len(lamps), 4)
        self.assertTrue(all(lamp["type"] == 456 and lamp["sector"] == self.car and
                            lamp["cstat"] & mechanism.CARRY_WITH for lamp in lamps))

        home_spill = self.wires[self.design.DEPART]
        far_spill = self.wires[self.design.COACH]
        for channel, count, state in ((home_spill, 7, 0), (far_spill, 4, 1)):
            strips = [(record_fields(s), record_extra(s)) for s in self.disk.sectors
                      if (record_extra(s) or {}).get("rx_id") == channel
                      and record_fields(s)["floor_pal"] == self.design.GREEN]
            self.assertEqual(len(strips), count)
            for fields, light in strips:
                self.assertLessEqual(fields["floor_shade"], 6)
                self.assertTrue(light["amplitude"] >= 48 and light["shade_floor"])
                self.assertEqual((light["state"], light["shade_always"]), (state, 0))
        track_spill = [s for s in self.disk.sprites if (record_extra(s) or {}).get("rx_id")
                       == self.wires[self.design.SPILL_OFF]]
        self.assertEqual(len(track_spill), 4)
        self.assertTrue(all(record_fields(s)["type"] == 405 and record_extra(s)["state"]
                            and record_fields(s)["pal"] == self.design.GREEN
                            and not (record_fields(s)["cstat"] & 1) for s in track_spill))
        clerk = sector_at(self.disk, 45312, -9000, floor_near=self.design.GHOST_FLOOR)
        flicker = record_extra(self.disk.sectors[clerk])
        self.assertEqual((flicker["shade_always"], flicker["shade_wave"]), (1, 6))
        signs = [s for s in self.disk.sprites if record_fields(s)["picnum"] == 1667
                 and record_fields(s)["z"] > self.design.GHOST_FLOOR - 32768]
        self.assertEqual(len(signs), 2)
        x0, x1 = self.design.DOOR
        fascia = [f for s in self.disk.sprites if (f := record_fields(s))["sector"] == self.car
                  and x0 < f["x"] < x1 and f["y"] == self.design.CAR[3] - 32
                  and f["z"] == self.design.TRACK_ROOF + 2992]
        self.assertEqual([f["picnum"] for f in sorted(fascia, key=lambda f: f["x"])],
                         self.destination_tiles)


if __name__ == "__main__":
    unittest.main()
