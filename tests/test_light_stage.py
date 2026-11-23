"""bloodmap.light_stage: a finished map lit as a scene, its lights in rows, the same map every run, and no index moved."""

import copy
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import light_stage as L  # noqa: E402
from bloodmap.analysis import validate_map  # noqa: E402
from bloodmap.format import write_map  # noqa: E402
from bloodmap.planar_layout import PlanarLayout  # noqa: E402


def _f(record):
    return record.fields


def _hall():
    """A long roofed hall, tall enough for recessed panels, off an open yard."""
    layout = PlanarLayout(name="light-stage-probe")
    layout.add_region("town/hall", [(0, 0), (12288, 0), (12288, 6144), (0, 6144)],
                      floor_z=0, ceiling_z=-24576, floor_picnum=4)
    layout.add_region("town/yard", [(12288, 0), (20480, 0), (20480, 6144), (12288, 6144)],
                      floor_z=0, ceiling_z=-65536, parallax_ceiling=True, declared_zero_exit=True)
    layout.add_connection("door", "town/hall", "town/yard", a1=(12288, 0), a2=(12288, 6144),
                          min_width=512)
    layout.set_player_start("town/hall", x=2000, y=3000, z=0)
    compiled = layout.compile()
    disk = compiled.level.to_disk_map()
    region_of = {a.sector_id: rid for rid, a in compiled.allocations.items()}
    return disk, region_of


def _bytes(disk):
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / "x.MAP"
        write_map(disk, path)
        return path.read_bytes()


class LightStageTests(unittest.TestCase):
    def test_a_rooms_shade_bias_follows_its_cut_pieces(self):
        disk, region_of = _hall()
        hall = next(i for i, name in region_of.items() if name == "town/hall")
        yard = next(i for i, name in region_of.items() if name == "town/yard")
        darker = copy.deepcopy(disk)
        baseline = L.Rule("panel", 2290, 3072, 3072)
        offset = L.Rule("panel", 2290, 3072, 3072, shade_bias=(12, 16, 8))
        report = L.run(disk, region_of, lambda name: baseline)
        L.run(darker, region_of, lambda name: offset if name == "town/hall" else baseline)
        pieces = [i for i, parent in report["parent"].items() if parent == hall]
        self.assertTrue(pieces)
        for i in (hall, *pieces):
            original, shaded = _f(disk.sectors[i]), _f(darker.sectors[i])
            self.assertEqual(shaded["floor_shade"] - original["floor_shade"], 12)
            self.assertEqual(shaded["ceiling_shade"] - original["ceiling_shade"], 16)
        self.assertEqual(_f(disk.sectors[yard]), _f(darker.sectors[yard]))

    def test_panels_lie_in_rows_and_sprites_carry_no_wiring(self):
        disk, region_of = _hall()
        hall = next(s for s, r in region_of.items() if r == "town/hall")
        rooms = L.rooms_by_region(disk, region_of)
        self.assertIn("town/hall", rooms)
        laid = L.lay_lights(disk, rooms, lambda r: L.Rule("panel", 2290, 3072, 3072))
        pieces = [int(k) for k, v in laid["cut"]["parent"].items() if int(v) == hall]
        self.assertGreaterEqual(len(pieces), 2)
        # every panel is one tile deep in the ceiling, recessed and lit
        for s in pieces:
            f = _f(disk.sectors[s])
            self.assertEqual(int(f["ceiling_picnum"]), 2290)
            self.assertEqual(int(f["ceiling_shade"]), 0)
            self.assertEqual(int(f["ceiling_z"]), int(_f(disk.sectors[hall])["ceiling_z"]) - L.RECESS)
        # in rows: the centres make a full grid, not a scatter
        def centre(s, key):
            first = int(_f(disk.sectors[s])["wall_ptr"])
            return round(sum(int(_f(disk.walls[w])[key]) for w in range(first, first + 4)) / 4)
        xs = {centre(s, "x") for s in pieces}
        ys = {centre(s, "y") for s in pieces}
        self.assertEqual(len(xs) * len(ys), len(pieces))
        self.assertGreater(len(xs), len(ys))            # more along the hall than across it
        # a room lit by sprites gets clean records: no XSPRITE, no type
        disk2, region_of2 = _hall()
        L.lay_lights(disk2, L.rooms_by_region(disk2, region_of2), lambda r: L.Rule("ceiling", 2290, 3072, 3072))
        added = [s for s in disk2.sprites if int(_f(s)["picnum"]) == 2290]
        self.assertGreater(len(added), 0)
        for s in added:
            self.assertEqual((int(_f(s)["type"]), int(_f(s)["extra"]), s.extra), (0, -1, None))

    def test_the_stage_is_the_same_map_every_run_and_moves_no_index(self):
        disk, region_of = _hall()
        before = copy.deepcopy(disk)
        rule = lambda r: L.Rule("panel", 2290, 3072, 3072)  # noqa: E731
        report = L.run(disk, region_of, rule)
        again = copy.deepcopy(before)
        L.run(again, region_of, rule)
        self.assertEqual(_bytes(disk), _bytes(again))
        # the original sectors keep their indices and their walls' shape
        for i, sector in enumerate(before.sectors):
            for key in ("floor_z", "floor_picnum", "type", "extra"):
                self.assertEqual(_f(disk.sectors[i])[key], _f(sector)[key])
        self.assertEqual(sorted(report["parent"]), list(range(len(before.sectors), len(disk.sectors))))
        # the yard's sky has one shade, and its sprites take the floor's
        yard = next(s for s, r in region_of.items() if r == "town/yard")
        self.assertEqual(int(_f(disk.sectors[yard])["ceiling_shade"]), 0)
        self.assertTrue(int(_f(disk.sectors[yard])["floor_stat"]) & 0x8000)
        self.assertEqual([d for d in validate_map(disk) if d.severity == "error"], [])


class LampReachTests(unittest.TestCase):
    def _floor_light(self, disk, lamp):
        from bloodmap import daylight as D
        from bloodmap.lightbomb import ScanIndex

        p = D.Sample(3000.0, 3000.0, -64.0, 0, (0.0, 0.0, -1.0), indoor=True)
        D.light_point(disk, ScanIndex(disk), p, D._hemisphere(8), D.Sun().vector(), [lamp])
        return p.lamp

    def test_a_lamp_in_the_air_lights_the_floor_below_it(self):
        """Until 2026-11-21 a lamp the ray passed (a candelabrum's flame, a
        street lamp's head) counted as hidden: only one the ray stopped
        beside lit anything."""
        disk, region_of = _hall()
        hall = next(s for s, r in region_of.items() if r == "town/hall")
        self.assertGreater(self._floor_light(disk, (3500.0, 3000.0, -12000.0, hall, 1.0)), 0.3)

    def test_glass_lets_light_into_its_room_and_none_onto_the_street(self):
        from bloodmap import light_kinds as K
        from bloodmap.model import DiskObject

        disk, region_of = _hall()
        hall = next(s for s, r in region_of.items() if r == "town/hall")
        yard = next(s for s, r in region_of.items() if r == "town/yard")

        def glass(x, y, sector, angle):
            f = {"x": x, "y": y, "z": -12000, "cstat": 16 | 64, "picnum": 569, "shade": 8, "pal": 0,
                 "clipdist": 32, "detail": 0, "x_repeat": 48, "y_repeat": 192, "x_offset": 0, "y_offset": 0,
                 "sector": sector, "status": 0, "angle": angle, "owner": -1, "index": len(disk.sprites),
                 "y_velocity": 0, "initial_type": 0, "type": 0, "flags": 0, "extra": -1}
            disk.sprites.append(DiskObject(fields=f))

        glass(6000, 16, hall, 512)          # on the hall's north wall, facing in (south)
        glass(16000, 16, yard, 512)         # on the yard's edge, under the sky
        found = K.sprite_lights(disk)
        self.assertEqual(len(found), 1)
        x, y, z, sector, strength, facing = found[0]
        self.assertEqual(sector, hall)
        self.assertGreater(y, 16)                         # inside the room
        self.assertGreater(facing[1], 0)                  # in ...
        self.assertGreater(facing[2], 0)                  # ... and down

    def test_a_sprite_the_game_never_draws_gives_no_light(self):
        """An exploder (type 459) wears the flame tile, 908; until 2026-11-21
        the three waiting behind the plague pit's seal lit the bricked-up
        room to shade 7."""
        from bloodmap import light_kinds as K
        from bloodmap.model import DiskObject

        disk, region_of = _hall()
        hall = next(s for s, r in region_of.items() if r == "town/hall")

        def flame(type_id):
            f = {"x": 3000, "y": 3000, "z": -64, "cstat": 128, "picnum": 908, "shade": 0, "pal": 0,
                 "clipdist": 32, "detail": 0, "x_repeat": 64, "y_repeat": 64, "x_offset": 0, "y_offset": 0,
                 "sector": hall, "status": 0, "angle": 0, "owner": -1, "index": len(disk.sprites),
                 "y_velocity": 0, "initial_type": 0, "type": type_id, "flags": 0, "extra": -1}
            disk.sprites.append(DiskObject(fields=f))

        before = len(K.sprite_lights(disk))
        flame(0)
        self.assertEqual(len(K.sprite_lights(disk)), before + 1)
        flame(459)
        self.assertEqual(len(K.sprite_lights(disk)), before + 1)


if __name__ == "__main__":
    unittest.main()
