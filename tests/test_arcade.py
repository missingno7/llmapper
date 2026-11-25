"""Read the Gravesend Arcade from the city's MAP bytes: two levels, a broken gallery, the way to the key, what its taking opens."""

from collections import deque
from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.sector_geom import sector_at, sector_walls
from bloodmap.slope import SLOPE_DIVISOR

LEVEL = Path("projects/blood-city/level")
PU = 1024
BODY = PLAYER_PROFILES["blood"]


def floor_at(disk, sector, x, y):
    """A floor's height at a point, its slope and all (`getflorzofslope`)."""
    f = record_fields(disk.sectors[sector])
    if not f["floor_stat"] & 2:
        return f["floor_z"]
    a = record_fields(disk.walls[f["wall_ptr"]])
    b = record_fields(disk.walls[a["point2"]])
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    length = (dx * dx + dy * dy) ** 0.5
    return f["floor_z"] + f["floor_heinum"] * (dx * (y - a["y"]) - dy * (x - a["x"])) / length / SLOPE_DIVISOR


def walk(disk, start, *, shut=()):
    """Every sector a standing body walks to, by the floor's height at each opening; sloped floors count as they are."""
    seen, queue = {start}, deque([start])
    while queue:
        here = queue.popleft()
        for w in sector_walls(disk, here):
            edge = record_fields(disk.walls[w])
            there = edge["next_sector"]
            if there < 0 or there in seen or there in shut or (edge["cstat"] & 1):
                continue
            end = record_fields(disk.walls[edge["point2"]])
            wide = ((end["x"] - edge["x"]) ** 2 + (end["y"] - edge["y"]) ** 2) ** 0.5
            if wide < BODY.body_width:
                continue
            for t in (0.15, 0.5, 0.85):
                x, y = edge["x"] + t * (end["x"] - edge["x"]), edge["y"] + t * (end["y"] - edge["y"])
                a, b = floor_at(disk, here, x, y), floor_at(disk, there, x, y)
                top = max(record_fields(disk.sectors[s])["ceiling_z"] for s in (here, there))
                if a - b <= BODY.max_step and min(a, b) - top >= BODY.standing_height:
                    seen.add(there)
                    queue.append(there)
                    break
    return seen


class ArcadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import arcade
        import l3_mall
        import wires
        cls.A, cls.M, cls.wires = arcade, l3_mall, wires
        path = LEVEL / "blood-city-current.MAP"
        if not path.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.disk = read_map(path)
        cls.level = cls.disk.to_level_ir()

    def at(self, x, y, floor):
        sector = sector_at(self.level, round(x * PU), round(y * PU), floor_near=floor)
        self.assertEqual(record_fields(self.disk.sectors[sector])["floor_z"], floor, (x, y))
        return sector

    def test_the_key_is_walked_to_from_the_street_door_and_back(self):
        gallery = self.at(40.0, 45.0, self.A.GRADE)
        landing = self.at(49.0, 45.0, self.A.GRADE)
        court = self.at(44.4, 44.0, self.A.COURT)
        for a, b in ((gallery, court), (court, landing), (landing, court), (court, gallery)):
            self.assertIn(b, walk(self.disk, a))

    def test_the_gallery_is_broken_so_the_court_must_be_crossed(self):
        gallery, landing = self.at(40.0, 45.0, self.A.GRADE), self.at(49.0, 45.0, self.A.GRADE)
        court = {i for i, s in enumerate(self.disk.sectors) if record_fields(s)["floor_z"] == self.A.COURT}
        self.assertNotIn(landing, walk(self.disk, gallery, shut=court))

    def test_the_key_stands_on_its_plinth_before_the_door_it_opens(self):
        keys = [record_fields(s) for s in self.disk.sprites if record_fields(s)["type"] == 101]
        self.assertEqual(len(keys), 1)
        floor = record_fields(self.disk.sectors[keys[0]["sector"]])["floor_z"]
        self.assertEqual(floor, self.A.LEVELS["plinth"][0])
        locked = [record_extra(s) for s in self.disk.sectors if (record_extra(s) or {}).get("key") == self.M.SERVICE_KEY]
        self.assertTrue(locked)

    def test_taking_it_raises_the_gun_shops_shutter(self):
        channel = self.wires.channel("key:eye")
        shutters = [s for s in self.disk.sectors if (record_extra(s) or {}).get("rx_id") == channel]
        self.assertEqual(len(shutters), 1)
        f, x = record_fields(shutters[0]), record_extra(shutters[0])
        self.assertEqual((f["type"], f["ceiling_z"]), (600, f["floor_z"]))
        self.assertLessEqual(x["on_ceiling_z"], f["floor_z"] - BODY.standing_height)
        guns = self.at(41.0, 48.4, self.A.GRADE)
        self.assertNotIn(guns, walk(self.disk, self.at(40.0, 45.0, self.A.GRADE)))

    def test_everything_and_everybody_in_it_can_be_got_at(self):
        """Once the shutter is up; the first arcade's counters shut its key and a zombie behind them."""
        start = self.at(40.0, 45.0, self.A.GRADE)
        channel = self.wires.channel("key:eye")
        (shutter,) = [s for s in self.disk.sectors if (record_extra(s) or {}).get("rx_id") == channel]
        record_fields(shutter)["ceiling_z"] = record_extra(shutter)["on_ceiling_z"]
        try:
            reached = walk(self.disk, start)
        finally:
            record_fields(shutter)["ceiling_z"] = record_extra(shutter)["off_ceiling_z"]
        plinth = self.at(49.5, 45.0, self.A.LEVELS["plinth"][0])
        seen = 0
        for s in self.disk.sprites:
            f = record_fields(s)
            here = self.A.WEST < f["x"] / PU < self.A.EAST and 40.7 < f["y"] / PU < 49.4 and f["z"] < 40000
            if here and (40 <= f["type"] < 150 or 200 <= f["type"] < 260 or f["type"] == 18):
                seen += 1
                self.assertIn(f["sector"], reached | {plinth}, (f["type"], f["x"], f["y"]))
        self.assertGreaterEqual(seen, 12)

    def test_the_court_lies_over_nothing(self):
        for i, s in enumerate(self.disk.sectors):
            f = record_fields(s)
            if f["floor_z"] <= self.A.COURT or f["ceiling_stat"] & 1:
                continue
            for w in sector_walls(self.disk, i):
                g = record_fields(self.disk.walls[w])
                inside = (self.A.EDGE < g["x"] / PU < self.A.EAST_EDGE and 40.75 < g["y"] / PU < self.A.SOUTH)
                self.assertFalse(inside and f["floor_z"] > 40000, i)

    def test_the_lantern_is_open_to_the_sky_and_barred(self):
        roof = record_fields(self.disk.sectors[self.at(45.0, 43.7, self.A.COURT)])
        self.assertTrue(roof["ceiling_stat"] & 1)
        bars = [s for s in self.disk.sprites if record_fields(s)["picnum"] == 1060 and record_fields(s)["cstat"] & 32
                and record_fields(s)["y"] > 0]            # (the station's glass roof has its own)
        self.assertEqual(len(bars), 3)


if __name__ == "__main__":
    unittest.main()
