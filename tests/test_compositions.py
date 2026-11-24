"""Synthetic geometry and map-read anchors for the composition sensor and shelf."""

from __future__ import annotations

import json
from math import atan2, cos, sin, tau
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from bloodmap.compositions import observe_compositions
from bloodmap.corpus import CorpusError, corpus_map_path
from bloodmap.format import SECTOR_FIELDS, SPRITE_FIELDS, WALL_FIELDS, read_map
from bloodmap.model import DiskMap, DiskObject, PackedExtra
from bloodmap.sector_geom import outline_and_holes


def polygon(radius, count=8, centre=(0, 0)):
    return [(round(centre[0] + radius * cos(tau * i / count)),
             round(centre[1] + radius * sin(tau * i / count))) for i in range(count)]


def disk_map():
    return DiskMap(0x700, {"start_sector": 0}, None, [], [], [], [], 0, 0)


def obj(schema, **fields):
    return DiskObject(dict.fromkeys((name for name, _codec in schema), 0) | fields)


def add_sector(disk, loops, *, z=0, tile=120, shade=0):
    sector = len(disk.sectors)
    first = len(disk.walls)
    for points in loops:
        start = len(disk.walls)
        disk.walls.extend(obj(WALL_FIELDS, x=x, y=y, point2=start + (i + 1) % len(points),
                              next_wall=-1, next_sector=-1) for i, (x, y) in enumerate(points))
    disk.sectors.append(obj(SECTOR_FIELDS, wall_ptr=first, wall_count=len(disk.walls) - first,
                            floor_z=z, ceiling_z=-64000, floor_picnum=tile, floor_shade=shade))
    return sector


def pair_portals(disk):
    edges = {}
    for sector, record in enumerate(disk.sectors):
        start = record.fields["wall_ptr"]
        for i in range(start, start + record.fields["wall_count"]):
            wall = disk.walls[i].fields
            end = disk.walls[wall["point2"]].fields
            a, b = (wall["x"], wall["y"]), (end["x"], end["y"])
            if (b, a) in edges:
                j, other = edges.pop((b, a))
                wall.update(next_wall=j, next_sector=other)
                disk.walls[j].fields.update(next_wall=i, next_sector=sector)
            else:
                edges[a, b] = i, sector


def add_sprite(disk, xy, *, sector=0, z=0, tile=938, kind=0, angle=0,
               cstat=0, status=0, **extra):
    sprite = obj(SPRITE_FIELDS, x=xy[0], y=xy[1], z=z, sector=sector, picnum=tile,
                 type=kind, angle=angle, cstat=cstat, status=status, x_repeat=32, y_repeat=32)
    if extra:
        sprite.extra = PackedExtra("sprite", extra)
    disk.sprites.append(sprite)


def rings(disk, **kwargs):
    return [r for r in observe_compositions(disk, **kwargs) if r["kind"] in ("ring", "square")]


class SpriteCompositionsTests(unittest.TestCase):
    def setUp(self):
        self.disk = disk_map()
        add_sector(self.disk, [[(-8000, -8000), (8000, -8000), (8000, 8000), (-8000, 8000)]])

    def test_ring_of_six_and_its_visible_wired_centre(self):
        for p in polygon(1500, 6, (100, -200)):
            add_sprite(self.disk, p)
        add_sprite(self.disk, (100, -200), tile=187, tx_id=142, rx_id=27)
        for kind, status, cstat, extra in ((1, 0, 0, {}), (709, 0, 0, {}), (0, 10, 0, {}),
                                           (0, 0, 0x8000, {}), (0, 0, 0, {"launch_single": 1})):
            add_sprite(self.disk, (100, -200), tile=500, kind=kind, status=status, cstat=cstat, **extra)
        row, = rings(self.disk)
        self.assertEqual((row["kind"], row["centre"], row["count"], row["missing"]),
                         ("ring", [100.0, -200.0], 6, 0))
        self.assertEqual(row["family"]["picnums"], [938])
        self.assertAlmostEqual(row["radius_m"], 2.55)
        self.assertEqual([s["picnum"] for s in row["centre_contents"]], [187])
        self.assertEqual(row["wiring"], [{"kind": "sprite", "id": 6, "tx_id": 142, "rx_id": 27}])
        original = observe_compositions(self.disk)
        self.assertEqual(original, observe_compositions(self.disk))
        self.assertEqual(original, json.loads(json.dumps(original)))

    def test_one_or_two_empty_slots(self):
        for count in (5, 4):
            with self.subTest(count=count):
                self.disk.sprites.clear()
                for p in polygon(1200, 6)[:count]:
                    add_sprite(self.disk, p)
                row, = rings(self.disk)
                self.assertEqual((row["kind"], row["missing"], row["expected_count"]),
                                 ("ring", 6 - count, 6))

    def test_concentric_rings_of_the_same_tile(self):
        for radius in (1000, 1800):
            for p in polygon(radius, 6):
                add_sprite(self.disk, p)
        rows = observe_compositions(self.disk)
        self.assertEqual([(r["count"], round(r["radius"])) for r in rows if r["kind"] == "ring"],
                         [(6, 1000), (6, 1800)])
        group, = [r for r in rows if r["kind"] == "group"]
        self.assertEqual(group["count"], 2)
        self.assertGreater(group["score"], max(r["score"] for r in rows if r["kind"] == "ring"))

    def test_dude_type_can_unite_different_frames(self):
        for i, p in enumerate(polygon(900, 6)):
            add_sprite(self.disk, p, kind=201, tile=2820 + i)
        row, = rings(self.disk)
        self.assertEqual(row["family"]["by"], "dude_type")
        self.assertEqual(row["family"]["types"], [201])

    def test_four_fit_needs_a_clean_annulus(self):
        for p in [*polygon(1200, 6)[:4], (600, -150)]:
            add_sprite(self.disk, p)
        self.assertEqual(rings(self.disk), [])

    def test_grid_rectangle_row_and_square(self):
        for layout, want in (
            ([(400 * i, 400 * j) for i in range(4) for j in range(5)], []),
            ([(500 * i, 300 * j) for i in range(4) for j in range(5)], []),
            ([(800 * i, 450 * j) for i in range(2) for j in range(2)], []),
            ([(400 * i, 0) for i in range(12)], []),
            ([(800 * i, 800 * j) for i in range(2) for j in range(2)], ["square"]),
        ):
            with self.subTest(layout=layout):
                self.disk.sprites.clear()
                for p in layout:
                    add_sprite(self.disk, p)
                self.assertEqual([r["kind"] for r in rings(self.disk)], want)

    def test_jittered_square_and_rectangular_grids(self):
        for width, depth in ((400, 400), (500, 300)):
            for seed in (0, 2, 4, 7, 13):
                with self.subTest(width=width, depth=depth, seed=seed):
                    self.disk.sprites.clear()
                    random = Random(seed)
                    for x in range(4):
                        for y in range(5):
                            add_sprite(self.disk, (width * x + random.randrange(-12, 13),
                                                   depth * y + random.randrange(-12, 13)))
                    self.assertEqual(rings(self.disk), [])

    def test_focus_of_a_congregation_and_directional_art(self):
        for i, p in enumerate([(-800, -900), (-300, -950), (300, -1000), (800, -1000)]):
            angle = round(atan2(-p[1], -p[0]) * 2048 / tau) % 2048
            add_sprite(self.disk, p, angle=angle, kind=201 if i < 2 else 0,
                       cstat=16 if i == 2 else 0, tile=938 + i)
        add_sprite(self.disk, (0, 0), tile=187)
        self.assertFalse(any(r["kind"] == "focus" for r in observe_compositions(self.disk)))
        row, = [r for r in observe_compositions(self.disk, directional_tiles={941})
                if r["kind"] == "focus"]
        self.assertEqual(row["count"], 4)
        self.assertLess(max(map(abs, row["centre"])), 3)
        self.assertEqual([s["picnum"] for s in row["centre_contents"]], [187])


class SectorCompositionsTests(unittest.TestCase):
    def make_nest(self, heights, *, radial=False):
        disk = disk_map()
        loops = [polygon(3600 - 750 * i) for i in range(len(heights))]
        for i, (z, outer) in enumerate(zip(heights, loops)):
            if i == len(loops) - 1:
                add_sector(disk, [outer], z=z, shade=i)
                break
            inner = loops[i + 1]
            if radial and i == 1:
                for j, k in zip(range(8), [1, 2, 3, 4, 5, 6, 7, 0]):
                    add_sector(disk, [[outer[j], outer[k], inner[k], inner[j]]],
                               z=z, shade=10 + j % 2)
            else:
                # Hole comes first on disk, so this also checks outline ownership.
                add_sector(disk, [inner[::-1], outer], z=z, shade=i)
        pair_portals(disk)
        return disk

    def test_three_rises_and_round_room(self):
        disk = self.make_nest([0, -2048, -4096, -6144])
        rows = observe_compositions(disk)
        nest, = [r for r in rows if r["kind"] == "nest"]
        self.assertEqual(nest["form"], "dais")
        self.assertEqual(nest["centre_sector"], 3)
        self.assertEqual(nest["host_sector"], 0)
        self.assertEqual(nest["centre_floor"]["floor_step"], 6144)
        self.assertEqual(nest["light_contrast"], 3)
        self.assertEqual([level["floor_step"] for level in nest["levels"]], [0, 2048, 2048, 2048])
        self.assertEqual([level["sides"] for level in nest["levels"]], [8, 8, 8, 8])
        room, = [r for r in rows if r["kind"] == "round"]
        self.assertEqual((room["host_sector"], room["sides"]), (0, 8))
        self.assertTrue(any(r["kind"] == "group" for r in rows))

    def test_pit_and_mixed_floor_steps(self):
        for heights, form in (([0, 2048, 4096], "pit"), ([0, -2048, 4096], "mixed")):
            with self.subTest(form=form):
                row, = [r for r in observe_compositions(self.make_nest(heights))
                        if r["kind"] == "nest"]
                self.assertEqual(row["form"], form)
                self.assertEqual(row["centre_floor"]["floor_step"], -4096)

    def test_radial_split_band_and_shade_only_nest(self):
        disk = self.make_nest([0, 0, 0, 0], radial=True)
        row, = [r for r in observe_compositions(disk) if r["kind"] == "nest"]
        self.assertEqual(row["form"], "flat")
        self.assertEqual(row["levels"][1]["sectors"], list(range(1, 9)))
        self.assertEqual(row["levels"][1]["sides"], 8)
        self.assertEqual(len(row["levels"][1]["surface_variants"]), 4)

    def test_pillars_as_solid_voids_and_raised_islands(self):
        for raised in (False, True):
            with self.subTest(raised=raised):
                disk = disk_map()
                islands = [polygon(190, 4, p) for p in polygon(2200, 6)]
                add_sector(disk, [*(loop[::-1] for loop in islands), polygon(5000)])
                if raised:
                    for loop in islands:
                        add_sector(disk, [loop], z=-3000)
                    pair_portals(disk)
                row, = [r for r in observe_compositions(disk) if r["kind"] == "pillars"]
                self.assertEqual(row["count"], 6)
                self.assertEqual({m["kind"] for m in row["members"]},
                                 {"sector" if raised else "wall"})


class CampaignCompositionsTests(unittest.TestCase):
    def read(self, name):
        try:
            path = corpus_map_path(name)
        except CorpusError:
            self.skipTest(f"{name} absent from the campaign corpus")
        disk = read_map(path)
        return disk, observe_compositions(disk)

    def test_altar_of_stone_has_a_split_dais_and_eight_pillars(self):
        disk, rows = self.read("E1M7")
        altar, = [r for r in rows if r["kind"] == "nest" and r["centre_sector"] == 42]
        self.assertEqual(altar["centre"], [6656.0, 23040.0])
        self.assertEqual([level["sectors"] for level in altar["levels"]],
                         [[29], [2], [0, 1, 40, 41], [42]])
        self.assertEqual(len(outline_and_holes(disk, 12)[1]), 8)
        self.assertTrue(any(r["kind"] == "pillars" and r["host_sector"] == 12 and r["count"] == 8
                            for r in rows))
        self.assertTrue(any(r["kind"] == "round" and r["host_sector"] == 29 for r in rows))

    def test_great_temple_rotundas_and_floor_drawing(self):
        disk, rows = self.read("E1M6")
        self.assertEqual(len(outline_and_holes(disk, 385)[0]), 24)
        self.assertTrue(any(r["kind"] == "round" and r["host_sector"] == 385 and r["sides"] == 24
                            for r in rows))
        row, = [r for r in rows if r["kind"] == "nest" and r["centre_sector"] == 456]
        self.assertEqual(row["form"], "flat")
        self.assertEqual(row["levels"][1]["sectors"], [457, 458, 459, 460, 461, 462])

    def test_eight_cultists_around_the_bonfire_share_one_group_layer(self):
        _disk, rows = self.read("E2M9")
        ring, = [r for r in rows if r["kind"] == "ring" and r["centre_sector"] == 164]
        self.assertEqual((ring["count"], ring["missing"]), (8, 0))
        self.assertIn(3566, {s["picnum"] for s in ring["centre_contents"]})
        group, = [r for r in rows if r["kind"] == "group" and r["centre_sector"] == 164]
        self.assertEqual(group["count"], 3)
        self.assertEqual({layer["kind"] for layer in group["layers"]},
                         {"nest", "round", "ring", "focus"})


class ShelfTests(unittest.TestCase):
    def test_search_room_join_numeric_tiles_and_community_roundtrip(self):
        from tools import mine_compositions as mine

        disk = disk_map()
        add_sector(disk, [polygon(5000)])
        for p in polygon(1600, 6):
            add_sprite(disk, p, tile=938)
        add_sprite(disk, (0, 0), tile=187)
        rows = observe_compositions(disk)
        for row in rows:
            row.update(map="EXAMPLE", place="EXAMPLE:0", source="curated",
                       provenance="community-curated", room_kind="crypt")
        with TemporaryDirectory() as folder:
            named = Path(folder) / "named.json"
            community = Path(folder) / "community.json"
            mine._write(named, rows, 1, 0, community=False)
            community_rows = [dict(row, map="OTHER", source="community", place=None,
                                   provenance="community", path="community/Other.map")
                              for row in rows]
            mine._write(community, community_rows, 1, 0, community=True)
            with patch.multiple(mine, NAMED=named, COMMUNITY=community):
                self.assertEqual(len(mine.find(["rings", "938", "187", "crypt"],
                                               kind="ring", min_count=5, source="curated")), 1)
                self.assertEqual(len(mine.at_place("EXAMPLE:0")), len(rows))
                self.assertEqual({r["kind"] for r in mine.at_place("community/Other.map:0")},
                                 {"group", "ring"})
                self.assertTrue(all("members" not in r for r in mine.find([], source="community")))


if __name__ == "__main__":
    unittest.main()
