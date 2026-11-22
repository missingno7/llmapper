"""bloodmap.overlays: a patch on a region's floor is cut into the finished map, and nothing else changes."""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import overlays  # noqa: E402
from bloodmap.planar_layout import PlanarLayout, PlanarLayoutError  # noqa: E402
from bloodmap.analysis import validate_map  # noqa: E402


def _f(record):
    return record.fields


def _yard():
    """A yard with a house standing in it (a hole) and a lane off its east side."""
    layout = PlanarLayout(name="overlay-probe")
    layout.add_region(
        "yard", [(0, 0), (8192, 0), (8192, 8192), (0, 8192)],
        holes=[[(2048, 2048), (2048, 4096), (4096, 4096), (4096, 2048)]],
        floor_z=0, ceiling_z=-65536, floor_picnum=4, floor_shade=20)
    layout.add_region("lane", [(8192, 2048), (10240, 2048), (10240, 6144), (8192, 6144)],
                      floor_z=0, ceiling_z=-65536, declared_zero_exit=True)
    layout.add_connection("yard-lane", "yard", "lane", a1=(8192, 2048), a2=(8192, 6144),
                          min_width=512)
    layout.set_player_start("yard", x=6000, y=6000, z=0)
    return layout


def _laid(layout):
    compiled = layout.compile()
    disk = compiled.level.to_disk_map()
    report = overlays.lay(disk, compiled)
    return compiled, disk, report


def _walls_of(disk, sector):
    f = _f(disk.sectors[sector])
    return range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"]))


class SlopedCutTests(unittest.TestCase):
    """A sloped sector is cut only across its slope, and each piece is the same plane."""

    def _walk(self):
        from bloodmap.slope import SlopeSpec

        layout = PlanarLayout(name="sloped-walk")
        # a walk 512 wide and 8192 long, its ceiling falling to the east wall
        layout.add_region("walk", [(0, 0), (512, 0), (512, 8192), (0, 8192)],
                          floor_z=0, ceiling_z=-28672,
                          ceiling_slope=SlopeSpec(hinge=((0, 8192), (0, 0)), rise_z=8192),
                          declared_zero_exit=True)
        layout.set_player_start("walk", x=256, y=1000, z=0)
        compiled = layout.compile()
        return compiled.level.to_disk_map()

    @staticmethod
    def _ceiling_at(disk, sector, x, y):
        from bloodmap.slope import rise_at, signed_distance
        f = _f(disk.sectors[sector])
        first = int(f["wall_ptr"])
        a = _f(disk.walls[first])
        b = _f(disk.walls[int(a["point2"])])
        hinge = ((int(a["x"]), int(a["y"])), (int(b["x"]), int(b["y"])))
        heinum = int(f["ceiling_heinum"]) if int(f["ceiling_stat"]) & 2 else 0
        return int(f["ceiling_z"]) + rise_at(heinum, signed_distance((x, y), hinge))

    def test_a_cut_across_the_slope_keeps_each_piece_on_the_plane(self):
        disk = self._walk()
        before = [self._ceiling_at(disk, 0, x, y) for x, y in ((100, 1000), (400, 1000), (400, 6000))]
        spec = overlays.OverlaySpec(overlay_id="band", region_id="0",
                                    shapes=((((0, 4096), (512, 4096), (512, 8192), (0, 8192)), ()),),
                                    surface={})
        report = overlays.cut_sectors(disk, {0: [spec]}, slopes_across=True)
        self.assertEqual(report["refused"], {})
        self.assertEqual(len(disk.sectors), 2)
        piece = next(int(k) for k in report["parent"])
        after = [self._ceiling_at(disk, 0, 100, 1000), self._ceiling_at(disk, 0, 400, 1000),
                 self._ceiling_at(disk, piece, 400, 6000)]
        for was, now in zip(before, after):
            self.assertAlmostEqual(was, now, delta=16)
        self.assertEqual([d for d in validate_map(disk) if d.severity == "error"], [])

    def test_a_cut_along_the_slope_is_refused(self):
        disk = self._walk()
        spec = overlays.OverlaySpec(overlay_id="band", region_id="0",
                                    shapes=((((256, 0), (512, 0), (512, 8192), (256, 8192)), ()),),
                                    surface={})
        report = overlays.cut_sectors(disk, {0: [spec]}, slopes_across=True)
        self.assertIn(0, report["refused"])
        self.assertEqual(len(disk.sectors), 1)
        # and without leave, any cut of a slope is refused
        disk = self._walk()
        spec = overlays.OverlaySpec(overlay_id="band", region_id="0",
                                    shapes=((((0, 4096), (512, 4096), (512, 8192), (0, 8192)), ()),),
                                    surface={})
        self.assertIn(0, overlays.cut_sectors(disk, {0: [spec]})["refused"])


class OverlayTests(unittest.TestCase):
    def test_a_shadow_cuts_the_floor_and_only_the_floor(self):
        layout = _yard()
        # the house's shadow, cast north-west; and a worn patch running out to
        # the lane's opening, so the yard's wall there is split as well
        layout.add_overlay("shadow", "yard",
                           [(1024, 1024), (4096, 1024), (4096, 2048), (2048, 2048),
                            (2048, 4096), (1024, 4096)],
                           floor_shade_offset=12)
        layout.add_overlay("worn", "yard", [(7168, 1536), (9000, 1536), (9000, 4096), (7168, 4096)],
                           floor_picnum=9)
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        sectors_before = len(disk.sectors)
        lane = compiled.allocations["lane"].sector_id
        lane_fields = dict(_f(disk.sectors[lane]))
        report = overlays.lay(disk, compiled)
        yard = compiled.allocations["yard"].sector_id
        pieces = [yard] + [int(k) for k, v in report["parent"].items() if v == yard]
        self.assertEqual(len(pieces), 3)
        self.assertEqual(len(disk.sectors), sectors_before + 2)
        shades = sorted(int(_f(disk.sectors[s])["floor_shade"]) for s in pieces)
        self.assertEqual(shades[0], int(_f(disk.sectors[yard])["floor_shade"]))
        self.assertEqual(shades[-1] - shades[0], 12)
        tiles = {int(_f(disk.sectors[s])["floor_picnum"]) for s in pieces}
        self.assertEqual(tiles, {4, 9})
        # the lane is the same sector, joined now to two pieces of the yard
        for key in ("floor_z", "ceiling_z", "floor_picnum", "floor_shade"):
            self.assertEqual(_f(disk.sectors[lane])[key], lane_fields[key])
        reached = {int(_f(disk.walls[w])["next_sector"]) for w in _walls_of(disk, lane)}
        self.assertGreaterEqual(len(reached & set(pieces)), 2)
        self.assertGreater(report["walls_split"], 0)
        # and the map is a map
        errors = [d for d in validate_map(disk) if d.severity == "error"]
        self.assertEqual(errors, [])
        for wall, record in enumerate(disk.walls):
            twin = int(_f(record)["next_wall"])
            if twin >= 0:
                self.assertEqual(int(_f(disk.walls[twin])["next_wall"]), wall)

    def test_a_sprite_stands_in_the_piece_under_it(self):
        layout = _yard()
        layout.add_overlay("shadow", "yard", [(0, 6144), (2048, 6144), (2048, 8192), (0, 8192)],
                           floor_shade_offset=10)
        layout.add_sprite("barrel", "yard", x=1024, y=7168, z=0, picnum=907)
        compiled, disk, report = _laid(layout)
        sprite = compiled.placement_sprites["barrel"]
        sector = int(_f(disk.sprites[sprite])["sector"])
        self.assertIn(str(sector), report["parent"])
        yard = compiled.allocations["yard"].sector_id
        self.assertEqual(int(_f(disk.sectors[sector])["floor_shade"]),
                         int(_f(disk.sectors[yard])["floor_shade"]) + 10)

    def test_a_patch_may_not_set_anything_but_the_floor(self):
        layout = _yard()
        with self.assertRaises(PlanarLayoutError):
            layout.add_overlay("hole", "yard", [(0, 0), (512, 0), (512, 512), (0, 512)],
                               floor_z=4096)

    def test_a_sliver_is_not_laid(self):
        layout = _yard()
        layout.add_overlay("thin", "yard", [(5000, 0), (5040, 0), (5040, 8192), (5000, 8192)],
                           floor_shade_offset=8)
        _compiled, _disk, report = _laid(layout)
        self.assertEqual(report["pieces"], 0)
        self.assertEqual(report["slivers_dropped"], 1)

    def test_a_whole_patch_shifts_the_floor_and_the_shadow_stays_relative(self):
        layout = _yard()
        layout.add_overlay("sun", "yard", [((0, 0), (8192, 0), (8192, 8192), (0, 8192))],
                           floor_shade_offset=-10)
        layout.add_overlay("shadow", "yard", [(0, 6144), (2048, 6144), (2048, 8192), (0, 8192)],
                           floor_shade_offset=8)
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        yard = compiled.allocations["yard"].sector_id
        was = int(_f(disk.sectors[yard])["floor_shade"])
        report = overlays.lay(disk, compiled)
        pieces = [yard] + [int(k) for k in report["parent"]]
        # two pieces, not a third rim of untouched floor along the walls
        self.assertEqual(len(pieces), 2)
        shades = sorted(int(_f(disk.sectors[s])["floor_shade"]) for s in pieces)
        self.assertEqual(shades, [was - 10, was + 8])

    def test_a_long_wall_is_split_along_its_length_and_keeps_its_texture(self):
        layout = _yard()
        compiled = layout.compile()
        disk = compiled.level.to_disk_map()
        yard = compiled.allocations["yard"].sector_id
        walls_before = len(disk.walls)
        f = _f(disk.sectors[yard])
        # the lane's opening wall (two-sided) and an outer wall (one-sided)
        target = {}
        for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            a = _f(disk.walls[w]); b = _f(disk.walls[int(a["point2"])])
            if (a["x"], a["y"], b["x"], b["y"]) in ((0, 0, 8192, 0), (8192, 0, 0, 0)):
                target[w] = [(2048, 0), (6144, 0)]
        report = overlays.cut_sectors(disk, {}, wall_points=target)
        self.assertEqual(report.get("walls_cut"), 1)
        self.assertEqual(len(disk.walls), walls_before + 2)
        errors = [d for d in validate_map(disk) if d.severity == "error"]
        self.assertEqual(errors, [])
        parts = []
        for w, rec in enumerate(disk.walls):
            a = _f(rec); b = _f(disk.walls[int(a["point2"])])
            if a["y"] == 0 and b["y"] == 0 and a["x"] < b["x"]:
                parts.append((a["x"], int(a["x_repeat"]), int(a["x_panning"]), int(a["picnum"])))
        parts.sort()
        self.assertEqual([p[0] for p in parts], [0, 2048, 6144])
        # each part's texture starts where the one before it ended, modulo the
        # tile's width (where the engine wraps it, and `join_continues` reads it)
        for (_, rep, pan, pic), (_, _, nxt, _) in zip(parts, parts[1:]):
            width = overlays._tile_width(pic)
            self.assertEqual((pan + rep * 8) % width, nxt % width)

    def test_compile_does_not_cut(self):
        layout = _yard()
        layout.add_overlay("shadow", "yard", [(0, 6144), (2048, 6144), (2048, 8192), (0, 8192)],
                           floor_shade_offset=10)
        compiled = layout.compile()
        self.assertEqual(len(compiled.level.sectors), 2)


if __name__ == "__main__":
    unittest.main()
