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


if __name__ == "__main__":
    unittest.main()
