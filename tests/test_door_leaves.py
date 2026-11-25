"""The owner's rules for door leaves, over the city; and what its doorways and its fence are made of (2026-11-25)."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_fields

LEVEL = Path("projects/blood-city/level")


class DoorLeaves(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.sectors = [record_fields(s) for s in cls.disk.sectors]
        cls.walls = [record_fields(w) for w in cls.disk.walls]

    def ring(self, i):
        s = self.sectors[i]
        return range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"])

    def test_no_leaf_moves_as_its_tile_does_not(self):
        from tools.mine_door_leaves import broken_rules
        self.assertEqual(broken_rules(self.disk), [])

    def test_no_doorway_to_the_open_wears_the_room_behind_it(self):
        """A wooden leaf to the street, and everything between it and the street, are of one tile: not carpet, chequers or office ceiling."""
        import apertures
        doorways = 0
        for i, s in enumerate(self.sectors):
            if s["type"] != 600:
                continue
            faces = {self.walls[self.walls[w]["next_wall"]]["picnum"] for w in self.ring(i) if self.walls[w]["next_wall"] >= 0}
            if not faces & apertures.WOODEN_LEAVES:
                continue
            at, came, parts = i, None, [i]
            for side in {self.walls[w]["next_sector"] for w in self.ring(i)} - {-1}:
                at, came, chain = side, i, []
                while not self.sectors[at]["ceiling_stat"] & 1 and len(chain) < 5:
                    on = {self.walls[w]["next_sector"] for w in self.ring(at)} - {-1, came}
                    if not on or (len(on) > 1 and not all(self.sectors[n]["ceiling_stat"] & 1 for n in on)):
                        chain = None
                        break
                    chain.append(at)
                    came, at = at, next(iter(on))
                if chain and self.sectors[at]["ceiling_stat"] & 1:
                    parts += chain
                    doorways += 1
                    tiles = {self.sectors[p][k] for p in parts for k in ("floor_picnum", "ceiling_picnum")}
                    self.assertEqual(len(tiles), 1, (i, tiles))
                    self.assertIn(tiles.pop(), (apertures.WOOD, 110))
        self.assertGreaterEqual(doorways, 8)

    def test_no_door_is_taller_than_the_room_it_opens_into(self):
        """The owner, of the pawn shop's: "taller than the ceiling inside it". And a leaf is 128 thick."""
        from bloodmap.model import record_extra
        looked = 0
        for i, s in enumerate(self.sectors):
            if s["type"] != 600:
                continue
            extra = record_extra(self.disk.sectors[i]) or {}
            faces = {self.walls[self.walls[w]["next_wall"]]["picnum"] for w in self.ring(i) if self.walls[w]["next_wall"] >= 0}
            if not faces & (set(range(22, 28)) | {30, 495}) or extra["on_ceiling_z"] >= s["floor_z"]:
                continue
            looked += 1
            head = extra["on_ceiling_z"]
            xs = [self.walls[w]["x"] for w in self.ring(i)]
            ys = [self.walls[w]["y"] for w in self.ring(i)]
            self.assertLessEqual(abs(min(max(xs) - min(xs), max(ys) - min(ys)) - 128), 2, i)
            for reveal in {self.walls[w]["next_sector"] for w in self.ring(i)} - {-1}:
                for room in {self.walls[w]["next_sector"] for w in self.ring(reveal)} - {-1, i}:
                    if not self.sectors[room]["ceiling_stat"] & 1:
                        self.assertLess(self.sectors[room]["ceiling_z"], head, (i, room))
        self.assertGreaterEqual(looked, 12)

    def test_straw_lies_on_the_floor(self):
        for s in self.disk.sprites:
            f = record_fields(s)
            if f["picnum"] == 515:
                self.assertEqual(f["cstat"] & 48, 32)

    def test_what_is_written_on_the_walls_and_where_the_stand_is(self):
        import writings
        found = [record_fields(s)["picnum"] for s in self.disk.sprites]
        self.assertEqual([found.count(t) for t in (writings.STAY_OUT, writings.SLOTH, writings.MONKS)], [2, 1, 2])
        arrow = [record_fields(s) for s in self.disk.sprites if record_fields(s)["picnum"] == 1042]
        self.assertEqual(len(arrow), 1)
        self.assertEqual((arrow[0]["angle"], arrow[0]["cstat"] & 4), (512, 0))        # read from the south, it points east: to the yard's stair

    def test_nothing_hangs_a_string_in_mid_air(self):
        self.assertFalse([s for s in self.disk.sprites if record_fields(s)["picnum"] == 1907])

    def test_the_promenades_ropes_reach_from_post_to_post(self):
        import l3_market as M
        ropes = [record_fields(s) for s in self.disk.sprites if record_fields(s)["picnum"] == M.ROPE_TILE
                 and record_fields(s)["y"] > 55 * 1024]
        posts = sum(len(xs) for xs in M.FENCE_RUNS)
        spans = sum(len(xs) - 1 for xs in M.FENCE_RUNS) + 4                  # and four on the jetty
        self.assertEqual(len(ropes), spans * len(M.STRANDS))
        stakes = [s for s in self.sectors if s["floor_z"] == M.GRADE - M.FENCE_RISE and s["floor_picnum"] == M.PILE_TILE and s["ceiling_stat"] & 1]
        self.assertEqual(len(stakes), posts)
        for run in M.FENCE_RUNS:
            self.assertFalse(any(a < 14.9 < b for a, b in zip(run, run[1:])), "the gangplank is open")
            self.assertFalse(any(a < 26.0 < b for a, b in zip(run, run[1:])), "the jetty is open")

    def test_the_stations_rail_ends_in_a_newel(self):
        import booking_hall as B
        newels = [s for s in self.sectors if s["floor_z"] == B.TOP - B.NEWEL_RISE and s["floor_picnum"] == B.WOOD]
        self.assertEqual(len(newels), 2)

    def test_the_building_beside_a_mouth_goes_on_past_the_wall(self):
        """Down each side of the street behind a gate, the front that faces the town's side of the corner, to the sky."""
        import street_vistas as V
        for name, (edge, low, high, _wear) in V.ENDS.items():
            line, sign = round(V.EDGES[edge] * V.PU), -1 if edge == "west" else 1
            for y, beyond in ((round(low * V.PU), -1), (round(high * V.PU), 1)):
                fronts = [w for w in self.walls if w["next_sector"] < 0 and w["x"] == self.walls[w["point2"]]["x"] == line
                          and y in (w["y"], self.walls[w["point2"]]["y"]) and (w["y"] + self.walls[w["point2"]]["y"] - 2 * y) * beyond > 0]
                sides = [w for w in self.walls if w["next_sector"] < 0 and w["y"] == self.walls[w["point2"]]["y"] == y
                         and 0 <= sign * (w["x"] - line) <= V.FLANK * V.PU + 1 and sign * (self.walls[w["point2"]]["x"] - line) >= 0]
                self.assertTrue(fronts and sides, (name, y))
                self.assertEqual({w["picnum"] for w in sides}, {fronts[0]["picnum"]}, (name, y))
            # and nothing behind stands as tall as they do
            self.assertLess(max(storeys for _tile, storeys in V.ENDS[name][3].values()), 6)


if __name__ == "__main__":
    unittest.main()
