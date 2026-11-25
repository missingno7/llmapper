"""Painted fronts are whole windows, as the built city shows them; and what else the owner listed on 2026-11-25 before a release."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_fields
from bloodmap.sector_geom import sector_at

LEVEL = Path("projects/blood-city/level")


class FacadeBays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import facade_bays
        cls.B = facade_bays
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.level = cls.disk.to_level_ir()

    def test_a_stretch_holds_whole_windows(self):
        for tile in self.B.PAINTED:
            for length in range(1024, 12 * 1024, 333):
                u0, repeats, _cost = self.B.fit(length, tile)
                self.assertFalse(self.B._cuts(tile, u0) or self.B._cuts(tile, u0 + repeats * 8), (tile, length))
                self.assertLess(abs(repeats * 128 / length - 1), 0.2, (tile, length))

    def test_no_corner_or_doorway_of_the_city_cuts_a_window(self):
        cut = []
        for key, front in self.B._fronts(self.level, frozenset()):
            for kind, pieces in self.B._stretches(front):
                if any(p[2] == "window" for p in pieces) or sum(p[1] for p in pieces) < 600:
                    continue
                first, last = (record_fields(self.disk.walls[p[3]]) for p in (pieces[0], pieces[-1]))
                if self.B._cuts(key[0], first["x_panning"]) or self.B._cuts(key[0], last["x_panning"] + last["x_repeat"] * 8):
                    cut.append((key, kind, pieces[0][3]))
        self.assertEqual(cut, [])

    def test_a_window_one_looks_through_takes_a_painted_ones_place(self):
        found = 0
        for (tile, *_), front in self.B._fronts(self.level, frozenset()):
            lo, hi, *_rest = self.B.OPENING[tile]
            for _along, length, kind, w in front:
                f = record_fields(self.disk.walls[w])
                if kind == "window" and abs(length - (hi - lo) * 16) <= 24:
                    self.assertEqual((f["x_panning"], f["x_repeat"]), (lo, (hi - lo) // 8), w)
                    found += 1
        self.assertGreaterEqual(found, 6)

    def test_the_rails_run_on_under_the_tunnels_gate(self):
        import l3_station as T
        track = [record_fields(s) for s in self.disk.sectors
                 if record_fields(s)["floor_picnum"] == T.TRACK and record_fields(s)["floor_z"] == T.BED_Z]
        self.assertGreater(len(track), 8)
        self.assertEqual({(f["floor_x_panning"], f["floor_y_panning"], f["floor_stat"] & 4) for f in track}, {(0, T.TRACK_PAN, 0)})

    def test_the_stairs_to_the_gallows_leave_the_door_room_and_repeat_nothing(self):
        import gallows as G
        self.assertGreaterEqual(G.DOOR[1] - G.STAIR_TO, 0.75)
        self.assertGreater(G.HOUSE[3] - G.DOOR[3], 0.5)
        self.assertGreater(G.DOOR[1] - G.HOUSE[1], 0.5)
        treads = []
        for k in range(1, G.STEPS):
            i = sector_at(self.level, 9 * 1024, round((G.ALLEY[2] + (k - 0.5) * 0.5) * 1024), floor_near=G.GRADE - G.RISER * k)
            f = record_fields(self.disk.sectors[i])
            self.assertEqual(f["floor_z"], G.GRADE - G.RISER * k)
            treads.append((f["floor_x_panning"], f["floor_y_panning"]))
        self.assertEqual(len(set(treads)), G.STEPS - 1)

    def test_no_wall_of_the_sea_is_longer_than_the_renderer_sorts(self):
        import l3_market as M
        for s in self.disk.sectors:
            f = record_fields(s)
            if f["floor_picnum"] != M.SEA_TILE or not f["ceiling_stat"] & 1:
                continue
            for w in range(f["wall_ptr"], f["wall_ptr"] + f["wall_count"]):
                a = record_fields(self.disk.walls[w]); b = record_fields(self.disk.walls[a["point2"]])
                self.assertLessEqual(abs(a["x"] - b["x"]) + abs(a["y"] - b["y"]), 50 * 1024)

    def test_the_ships_stays_are_one_rope(self):
        """Each piece of tile 513 begins inside the end of the one above: no gap between them, and less than a fifth shared."""
        from collections import defaultdict
        ropes = defaultdict(list)
        for s in self.disk.sprites:
            f = record_fields(s)
            if f["picnum"] == 513 and abs(f["y"] - 59 * 1024) < 64 and f["cstat"] & 16:
                ropes[f["cstat"] & 4].append(f)
        self.assertEqual(sorted(len(pieces) for pieces in ropes.values()), [2, 3])
        for pieces in ropes.values():
            pieces.sort(key=lambda f: f["x"])
            for a, b in zip(pieces, pieces[1:]):
                wide = a["x_repeat"] * 38 / 4
                step = abs(b["x"] - a["x"])
                self.assertLess(step, wide * 33 / 38 + 8)
                self.assertGreater(step, wide * 0.8)


if __name__ == "__main__":
    unittest.main()
