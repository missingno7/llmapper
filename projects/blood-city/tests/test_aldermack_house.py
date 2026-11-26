"""Read the Aldermack's playable house and show back from the built map."""

import json
import sys
import unittest
from pathlib import Path

from bloodmap.conformance import measure_curtain
from bloodmap.format import read_map
from bloodmap.light_kinds import sprite_lights
from bloodmap.model import record_extra, record_fields
from bloodmap.motion_sim import blood_poses
from bloodmap.player_space import player_profile
from bloodmap.sector_geom import outline_and_holes, sector_walls


LEVEL = Path("projects/blood-city/level")
MAP = LEVEL / "blood-city-current.MAP"
TAGS = MAP.with_suffix(".tags.json")


@unittest.skipUnless(MAP.exists() and TAGS.exists(), "the city is not built")
class AldermackHouseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        try:
            import aldermack_house
            import wires
        finally:
            sys.path.pop(0)
        cls.house = aldermack_house
        cls.channel = staticmethod(wires.channel)
        cls.disk = read_map(MAP)
        cls.tags = json.loads(TAGS.read_text("utf-8"))

    def sector(self, tag):
        return self.tags["aldermack_" + tag][0]

    def fields(self, tag):
        return record_fields(self.disk.sectors[self.sector(tag)])

    def test_rising_house_curtain_and_the_sliding_box_curtain(self):
        house = self.house
        stage = self.fields("stage")
        self.assertEqual(stage["floor_picnum"], 15)
        self.assertEqual(stage["floor_z"], house.GRADE - 11520)
        self.assertEqual(stage["ceiling_z"], house.GRADE - 115712)
        main = self.disk.sectors[self.sector("main_curtain")]
        fields, extra = record_fields(main), record_extra(main)
        self.assertEqual(fields["type"], 600)
        self.assertEqual(fields["ceiling_picnum"], 159)
        self.assertEqual(fields["floor_z"], stage["floor_z"])
        self.assertEqual(fields["ceiling_z"], fields["floor_z"])
        self.assertEqual(extra["off_ceiling_z"], fields["floor_z"])
        self.assertEqual(extra["on_ceiling_z"], fields["floor_z"] - 61056)
        self.assertEqual(extra["rx_id"], self.channel("theatre:curtain"))
        self.assertEqual(extra["state"], 0)
        self.assertLessEqual(house.OPENING[2] - house.OPENING[0], 4608)

        (fin,) = self.tags["curtain"]
        curtain = self.disk.sectors[fin]
        self.assertEqual(record_extra(curtain)["state"], 0)
        self.assertEqual(record_extra(curtain)["rx_id"], self.channel("theatre:box-curtain"))
        self.assertEqual(measure_curtain(self.disk, fin, declared=[fin]).deviations, [])
        off, on = blood_poses(self.disk, fin)
        walls = list(sector_walls(self.disk, fin))

        def fabric_span(outline):
            points = dict(zip(walls, outline))
            spans = []
            for wall, a in points.items():
                f = record_fields(self.disk.walls[wall])
                b = points[f["point2"]]
                if f["picnum"] == 146 and f["next_sector"] == -1 and a[0] == b[0]:
                    spans.append(abs(a[1] - b[1]))
            return sorted(spans)

        self.assertEqual(fabric_span(off), [1408, 1408])
        self.assertEqual(fabric_span(on), [128, 128])
        for side in ("west", "east"):
            a = self.sector(side + "_drape_front")
            b = self.sector(side + "_drape_back")
            (mask,) = [record_fields(self.disk.walls[w]) for w in sector_walls(self.disk, a)
                       if record_fields(self.disk.walls[w])["next_sector"] == b]
            self.assertTrue(mask["cstat"] & 16)
            self.assertEqual(mask["over_picnum"], 159)
            self.assertEqual(self.fields(side + "_drape_front")["ceiling_z"],
                             self.fields(side + "_drape_back")["ceiling_z"])
            self.assertEqual(self.fields(side + "_drape_front")["floor_z"],
                             self.fields(side + "_drape_back")["floor_z"])

    def test_dwe_benches_terraces_and_lit_side_stairs(self):
        h = self.house
        profile = player_profile("blood")
        for i in (1, 2, 3):
            front = self.fields(f"terrace_{i}")
            rear = self.fields(f"terrace_tier_{i}")
            self.assertEqual((front["floor_picnum"], front["ceiling_picnum"]), (306, 28))
            self.assertEqual(h.GRADE - front["floor_z"], 3072 + (i - 1) * 6144)
            self.assertEqual(front["floor_z"] - rear["floor_z"], 3072)
        for tag, tile in (("bench_seat", 42), ("bench_back", 68)):
            for sector in self.tags["aldermack_" + tag]:
                outline, _ = outline_and_holes(self.disk, sector)
                ys = [p[1] for p in outline]
                self.assertEqual(max(ys) - min(ys), 256)
                self.assertEqual(record_fields(self.disk.sectors[sector])["floor_picnum"], tile)

        routes = [
            ["auditorium", *[f"{side}_apron_step_{i}" for i in range(1, 4)], "apron"]
            for side in ("west", "east")
        ]
        routes.append(["vomitory", *[f"circle_step_{i}" for i in range(1, 10)],
                       "circle_east_landing", "circle_front"])
        for side in ("west", "east"):
            steps = [f"{side}_aisle_step_{i}" for i in range(1, 7)]
            routes.append(["auditorium", *steps])
            for step in steps:
                sparks = [record_fields(s) for s in self.disk.sprites
                          if record_fields(s)["sector"] == self.sector(step)
                          and record_fields(s)["picnum"] == 624]
                self.assertEqual(sorted((f["cstat"], f["x_repeat"], f["shade"], f["pal"])
                                        for f in sparks),
                                 [(8320, 4, -30, 8)] * 2 + [(8322, 8, -30, 8)] * 2)
        for route in routes:
            for start, end in zip(route, route[1:]):
                self.assertTrue(self.adjacent(self.sector(start), self.sector(end)), (start, end))
                self.assertLessEqual(self.fields(start)["floor_z"] - self.fields(end)["floor_z"],
                                     profile.max_step)

    def adjacent(self, a, b):
        return any(record_fields(self.disk.walls[w])["next_sector"] == b
                   for w in sector_walls(self.disk, a))

    def test_the_moon_key_drops_cloth_and_opens_four_wings_with_a_bypass(self):
        prize_channel = self.channel("theatre:prize")
        main_channel = self.channel("theatre:curtain")
        sprites = [(record_fields(s), record_extra(s) or {}) for s in self.disk.sprites]
        (key,) = [(f, x) for f, x in sprites if x.get("tx_id") == prize_channel]
        self.assertEqual((key[0]["type"], key[0]["picnum"]), (105, 2557))
        self.assertTrue(key[1]["trigger_pickup"] and key[1]["trigger_once"])
        (drop,) = [x for _f, x in sprites if x.get("tx_id") == main_channel
                   and x.get("rx_id") == prize_channel]
        self.assertEqual(drop["command"], 0)
        reopeners = [(f, x) for f, x in sprites if f["picnum"] == 1070
                     and x.get("tx_id") == main_channel]
        self.assertEqual(len(reopeners), 2)
        self.assertTrue(all(x["command"] == 1 and x["trigger_on"] and x["trigger_off"]
                            for _f, x in reopeners))
        for i in range(4):
            door = self.disk.sectors[self.sector(f"stage_wing_door_{i}")]
            self.assertEqual(record_fields(door)["type"], 600)
            extra = record_extra(door)
            self.assertEqual(extra["rx_id"], prize_channel)
            self.assertEqual(extra["state"], 0)
            self.assertLess(extra["on_ceiling_z"], extra["off_ceiling_z"])
        self.assertEqual(sum(f["picnum"] == 3129 and x.get("rx_id") == prize_channel
                             for f, x in sprites), 2)
        path = ["stage", "west_wing_step_3", "west_wing_step_2", "west_wing_step_1"]
        for start, end in zip(path, path[1:]):
            self.assertTrue(self.adjacent(self.sector(start), self.sector(end)))
            self.assertEqual(self.fields(end)["type"], 0)
        exit_step = self.sector(path[-1])
        self.assertTrue(any(record_fields(self.disk.walls[w])["next_sector"] >= 0
                            and record_fields(self.disk.walls[w])["x"] == 19328
                            and record_fields(self.disk.walls[
                                record_fields(self.disk.walls[w])["point2"]])["x"] == 19328
                            for w in sector_walls(self.disk, exit_step)))

    def test_one_show_and_a_separate_piano(self):
        show = self.channel("theatre:show")
        latch = self.channel("theatre:show-latch")
        light = self.channel("theatre:stage-light")
        stage = record_extra(self.disk.sectors[self.sector("stage")])
        self.assertEqual((stage["rx_id"], stage["tx_id"], stage["command"], stage["trigger_on"]),
                         (light, latch, 1, 1))
        listeners = [(record_fields(s), record_extra(s)) for s in self.disk.sprites
                     if (record_extra(s) or {}).get("rx_id") == show]
        self.assertEqual(sorted(f["type"] for f, _x in listeners), [18] * 2 + [416] * 2 + [711])
        self.assertEqual({x["data_1"] for f, x in listeners if f["type"] == 18}, {203})
        self.assertEqual({x["data_1"] for f, x in listeners if f["type"] == 711}, {3101})
        (relay,) = [record_extra(s) for s in self.disk.sprites
                    if (record_extra(s) or {}).get("tx_id") == show]
        self.assertEqual((relay["rx_id"], relay["trigger_on"], relay["trigger_off"],
                          relay["rest_state"], relay["wait_time"]), (latch, 1, 0, 0, 0))
        (piano,) = [record_extra(s) for s in self.disk.sprites
                    if (record_extra(s) or {}).get("rx_id") == self.channel("theatre:pit-piano")]
        self.assertEqual(piano["data_2"], 279)

    def test_dome_chandelier_and_stage_back_have_no_window(self):
        ceiling = self.fields("auditorium")["ceiling_z"]
        rim = self.fields("dome_rim")["ceiling_z"]
        crown = self.fields("dome_crown")["ceiling_z"]
        self.assertLess(crown, rim)
        self.assertLess(rim, ceiling)
        self.assertIn(self.sector("dome_crown"), {light[3] for light in sprite_lights(self.disk)})
        cloth = self.sector("backcloth")
        windows = set(self.tags["window"])
        self.assertFalse(windows & {record_fields(self.disk.walls[w])["next_sector"]
                                    for w in sector_walls(self.disk, cloth)})
