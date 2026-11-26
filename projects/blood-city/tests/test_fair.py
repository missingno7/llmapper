"""The fair on the square, what it hides, the difficulties, and where players start: read back from the built map."""

import json
import math
from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.supplies import launched

LEVEL = Path("projects/blood-city/level")


class Fair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.sectors = [record_fields(s) for s in cls.disk.sectors]
        cls.walls = [record_fields(w) for w in cls.disk.walls]
        cls.sprites = [(record_fields(s), record_extra(s) or {}) for s in cls.disk.sprites]

    def _carousel(self):
        import fair
        out = []
        for i, s in enumerate(self.sectors):
            if s["type"] != 617:
                continue
            axis = self.sprites[record_extra(self.disk.sectors[i])["marker_0"]][0]
            if (axis["x"], axis["y"]) == (round(fair.AT[0] * 1024), round(fair.AT[1] * 1024)):
                out.append((i, s, record_extra(self.disk.sectors[i]), axis))
        return out

    def test_the_carousel_is_three_sectors_that_turn_as_one_and_for_ever(self):
        import fair
        turning = self._carousel()
        self.assertEqual(len(turning), 3)
        for _i, _s, x, axis in turning:
            self.assertEqual((x["rx_id"], x["busy_time_a"], x["busy_time_b"], x["retrigger_a"], x["retrigger_b"]), (7, fair.TENTHS, 0, 1, 1))
            self.assertEqual((axis["angle"] % 2048, abs(axis["angle"])), (0, 2048))       # a whole turn: the way back is not seen
        for i, s, _x, axis in turning:
            for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
                far = math.hypot(self.walls[w]["x"] - axis["x"], self.walls[w]["y"] - axis["y"])
                self.assertLess(min(abs(far - r * 1024) for r in (fair.RADIUS, fair.DRUM_R, fair.NECK_R)), 3)
        inside = {i for i, *_rest in turning}
        for f, _x in self.sprites:
            if f["sector"] in inside and f["status"] == 0 and f["picnum"] not in (2521,):
                self.assertTrue(f["cstat"] & fair.CARRIED, f)                             # nothing of it is left behind

    def test_its_drum_wears_whole_faces(self):
        import fair
        drum = next(i for i, s, _x, _a in self._carousel() if s["floor_z"] == fair.GRADE - fair.DRUM)
        faces = [w for w in self.walls if w["picnum"] == fair.CLOWN and w["next_sector"] == drum]
        self.assertEqual(len(faces), 8)
        for w in faces:
            self.assertEqual((w["x_repeat"], w["y_repeat"], w["x_panning"], w["y_panning"]), (16, 13, 0, 0))
        self.assertLess(abs(156 * 2048 / 13 - (fair.DRUM - fair.STEP)), 800)

    def test_every_roof_is_solid_and_so_is_what_one_rides(self):
        import fair
        roofs = [f for f, _x in self.sprites if f["picnum"] == fair.STRIPE and f["cstat"] & 48 == 32]
        self.assertGreater(len(roofs), 130)                        # the fair's four, the carousel's, and the market's two
        mounts = [f for f, _x in self.sprites if f["cstat"] & fair.CARRIED and f["type"] == 0 and f["picnum"] in (fair.POLE, fair.HOUND, fair.RAT)]
        self.assertEqual(len(mounts), 16)
        for f in roofs + mounts:
            self.assertEqual(f["cstat"] & 257, 257, f)

    def test_a_post_does_not_break_and_nothing_breaks_with_thunder(self):
        posts = [f for f, _x in self.sprites if f["picnum"] == 117 and f["cstat"] & 48 == 0]
        self.assertEqual(len(posts), 16)
        self.assertEqual({(f["type"], f["cstat"] & 257) for f in posts}, {(0, 257)})
        self.assertNotIn(308, {x.get("data_4") for f, x in self.sprites if f["type"] in (416, 417)})

    def test_a_stalls_name_is_on_a_board_and_is_read_from_in_front_alone(self):
        import fair
        boards = [f for f, _x in self.sprites if f["picnum"] == fair.PLANK and f["cstat"] & 48 == 16 and f["y_repeat"] == fair.BOARD_TALL]
        self.assertEqual(len(boards), sum(len(name) + 2 for name in ("SHOOTING", "TOFFEE", "FORTUNES")))
        lettered = 0
        for b in boards:
            self.assertFalse(b["cstat"] & 64)                                   # bare wood from behind
            turn = b["angle"] * math.pi / 1024
            for f, _x in self.sprites:
                ahead = (f["x"] - b["x"]) * math.cos(turn) + (f["y"] - b["y"]) * math.sin(turn)
                aside = abs(-(f["x"] - b["x"]) * math.sin(turn) + (f["y"] - b["y"]) * math.cos(turn))
                if 3808 <= f["picnum"] <= 3833 and abs(ahead) < 200 and aside < 24 and abs(f["z"] - b["z"]) < 9000:
                    lettered += 1
                    self.assertEqual((f["angle"], f["z"], f["cstat"] & 64), (b["angle"], b["z"], 64))
                    self.assertTrue(4 <= round(ahead) <= 12, ahead)             # on its front
                    self.assertEqual(b["x_repeat"] * 64 // 4, fair.PITCH)        # a piece to a letter, edge to edge
        self.assertEqual(lettered, len("SHOOTING" + "TOFFEE" + "FORTUNES"))

    def test_nothing_lets_through_what_bloods_does_not(self):
        import json as _json
        from tools import mine_solidity
        self.assertEqual(mine_solidity.faults(self.disk, _json.loads(mine_solidity.DATA.read_text("utf-8"))["tiles"]), [])

    def test_a_stall_is_a_u_of_boards_two_bodies_tall_open_at_the_front(self):
        import fair
        for name, (rect, *_rest) in fair.STALLS.items():
            x0, y0, x1, y1 = (round(v * 1024) for v in rect)
            inside = [s for s in self.sectors if all(x0 <= self.walls[w]["x"] <= x1 and y0 <= self.walls[w]["y"] <= y1
                                                     for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]))
                      and s["ceiling_stat"] & 1]
            rises = sorted({fair.GRADE - s["floor_z"] for s in inside})
            inner = [-fair.WELL, 0, fair.COUNTER_UP, *sorted(fair.TIERS)] if name == "gallery" else [0, fair.COUNTER_UP, fair.SHELF_UP]
            self.assertEqual(rises, [*inner, fair.BACK], name)
            self.assertGreater(fair.BACK, 2 * 16960)

    def test_the_gallery_is_e1m4s(self):
        """Ducks and faces on slabs that run to and fro for ever, bullseyes behind, all counted but the ducks; the last brings up the prize."""
        import fair
        by = {t: [(f, x) for f, x in self.sprites if f["picnum"] == t and f["type"] == 416] for t in fair.TARGETS}
        self.assertEqual([len(by[t]) for t in (fair.DUCK, fair.SMILE, fair.BULLSEYE)], [3, 3, 3])
        channel = {x["tx_id"] for t in (fair.SMILE, fair.BULLSEYE) for _f, x in by[t]}
        self.assertEqual(len(channel), 1)
        self.assertEqual({x["tx_id"] for _f, x in by[fair.DUCK]}, {0})
        tally = [x for f, x in self.sprites if f["type"] == 22 and x["rx_id"] in channel]
        self.assertEqual([x["data_2"] for x in tally], [6])
        well = [(s, record_extra(self.disk.sectors[i])) for i, s in enumerate(self.sectors)
                if (record_extra(self.disk.sectors[i]) or {}).get("rx_id") == tally[0]["tx_id"]]
        self.assertEqual([(s["type"], x["off_floor_z"] - x["on_floor_z"]) for s, x in well], [(600, fair.WELL + fair.COUNTER_UP)])
        self.assertIn(fair.BELL, [x["data_2"] for f, x in self.sprites if f["type"] == 708 and x["rx_id"] == tally[0]["tx_id"]])
        for f, _x in by[fair.DUCK] + by[fair.SMILE]:
            s, x = self.sectors[f["sector"]], record_extra(self.disk.sectors[f["sector"]])
            self.assertEqual((s["type"], x["rx_id"], x["retrigger_a"], x["retrigger_b"]), (616, 7, 1, 1))
            self.assertTrue(f["cstat"] & fair.CARRIED)
            off, on = (self.sprites[x[k]][0] for k in ("marker_0", "marker_1"))
            self.assertEqual(off["x"], on["x"])
            self.assertGreater(abs(off["y"] - on["y"]), 1800)

    def test_hardly_anybody_sees_the_start(self):
        import first_sight
        for skill, at_once, soon in ((0, 0, 4), (2, 0, 4), (4, 1, 8)):
            rows = first_sight.report(self.disk, skill)
            self.assertLessEqual(sum(0 in r["from"] for r in rows), at_once, (skill, rows))
            self.assertLessEqual(len(rows), soon, (skill, rows))
            self.assertTrue(all(r["far"] > 12 for r in rows))

    def test_the_first_frame_is_nobodys_lamp_post(self):
        x, y = self.disk.header["start_x"], self.disk.header["start_y"]
        turn = self.disk.header["start_angle"] * math.pi / 1024
        for f, _x in self.sprites:
            ahead = (f["x"] - x) * math.cos(turn) + (f["y"] - y) * math.sin(turn)
            aside = abs(-(f["x"] - x) * math.sin(turn) + (f["y"] - y) * math.cos(turn))
            if f["picnum"] == 640 and abs(f["z"] - 8192) < 30000:
                self.assertFalse(0 < ahead < 4096 and aside < ahead, f)

    def test_the_difficulties_are_the_campaigns(self):
        import difficulty
        met = [sum(1 for s in self.disk.sprites if (201 <= record_fields(s)["type"] <= 250 or record_fields(s)["type"] == 18)
                   and launched(s, k)) for k in range(5)]
        for k, share in enumerate(difficulty.SHARES):
            self.assertAlmostEqual(met[k] / met[2], share, delta=0.06, msg=str(met))

    def test_eight_start_together_and_eight_apart(self):
        together = {x["data_1"]: f for f, x in self.sprites if f["type"] == 1}
        apart = {x["data_1"]: f for f, x in self.sprites if f["type"] == 2}
        self.assertEqual((set(together), set(apart)), (set(range(8)), set(range(8))))
        one = together[0]
        self.assertEqual((one["x"], one["y"], one["angle"]), tuple(self.disk.header[k] for k in ("start_x", "start_y", "start_angle")))
        for f in (*together.values(), *apart.values()):
            self.assertEqual(f["z"], self.sectors[f["sector"]]["floor_z"])
        spread = [(f["x"], f["y"]) for f in apart.values()]
        self.assertGreater(min(math.dist(a, b) for k, a in enumerate(spread) for b in spread[:k]), 5000)


if __name__ == "__main__":
    unittest.main()
