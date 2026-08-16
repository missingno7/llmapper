from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bloodmap.cli import main
from bloodmap.construction import LevelBuilder
from bloodmap.exposure import route_exposure_report, spawn_neighborhood_report
from bloodmap.format import write_map
from bloodmap.morphology import analyze_morphology
from tests.helpers import synthetic_map


def _sky(builder, alloc):
    fields = builder.level.sectors[alloc.sector_id]["fields"]
    fields["ceiling_stat"] = int(fields["ceiling_stat"]) | 1
    fields["ceiling_z"] = -20 * 5632
    fields["floor_z"] = 0


def _start(builder, sector, x, y):
    sid = builder.add_sprite(sector=sector, x=x, y=y, z=0, type=2, picnum=2522, status=0)
    builder.set_behavior("sprite", sid, launch_bloodbath=1)
    return sid


def field_and_closet_map():
    """Large sky field with a 1024-wide closet on the east edge."""
    builder = LevelBuilder()
    field = builder.add_sector([
        (0, 0), (20480, 0), (20480, 9728), (20480, 10752), (20480, 20480), (0, 20480),
    ])
    closet = builder.add_sector([
        (20480, 9728), (21504, 9728), (21504, 10752), (20480, 10752),
    ])
    builder.connect(field.wall_ids[2], closet.wall_ids[3])
    _sky(builder, field)
    _start(builder, field.sector_id, 10240, 10240)
    _start(builder, closet.sector_id, 20992, 10240)
    builder.set_player_start(sector=field.sector_id, x=10240, y=10240, z=0, angle=0)
    return builder.build().to_disk_map()


def octagon_map():
    builder = LevelBuilder()
    s = 4096
    o = 1024
    builder.add_sector([
        (o, 0), (s - o, 0), (s, o), (s, s - o),
        (s - o, s), (o, s), (0, s - o), (0, o),
    ])
    builder.set_player_start(sector=0, x=s // 2, y=s // 2, z=0, angle=0)
    return builder.build().to_disk_map()


class MorphologyTests(unittest.TestCase):
    def test_rectangle_is_orthogonal_and_octagon_has_diagonals(self):
        rectangle = analyze_morphology(synthetic_map().to_build_ir())
        octagon = analyze_morphology(octagon_map().to_build_ir())
        self.assertGreaterEqual(rectangle["walls"]["orthogonal_length_fraction"], 0.99)
        self.assertEqual(rectangle["sectors"]["rectangular_fraction"], 1.0)
        self.assertGreater(octagon["walls"]["diagonal_length_fraction"], 0.3)
        self.assertLess(octagon["sectors"]["rectangular_fraction"], 1.0)
        self.assertGreaterEqual(octagon["sectors"]["outer_vertex_counts"]["max"], 8)
        self.assertGreater(octagon["corners"]["chamfer_fraction"] or 0.0, 0.5)
        self.assertGreater(octagon["walls"]["orientation_diversity"], rectangle["walls"]["orientation_diversity"])
        self.assertEqual(rectangle["corners"]["segmented_arc_chain_count"], 0)


class ExposureTests(unittest.TestCase):
    def test_closet_spawn_has_smaller_local_area_and_more_hops_than_field_spawn(self):
        build = field_and_closet_map().to_build_ir()
        report = spawn_neighborhood_report(build)
        by_sector = {item["sector"]: item for item in report["neighborhoods"]}
        field = by_sector["sector:0"]
        closet = by_sector["sector:1"]
        self.assertTrue(field["sky_ceiling"])
        self.assertFalse(closet["sky_ceiling"])
        self.assertEqual(field["hops_to_largest_sky_region"], 0)
        self.assertEqual(closet["hops_to_largest_sky_region"], 1)
        self.assertGreater(field["spawn_sector_area_player_areas"], closet["spawn_sector_area_player_areas"] * 10)
        self.assertGreater(field["local_reachable_area_player_areas"], closet["spawn_sector_area_player_areas"])
        self.assertGreater(field["sky_region_ray_fraction"], closet["sky_region_ray_fraction"])

        routes = route_exposure_report(build)
        field_route = next(item for item in routes["routes"] if item["origin"].endswith(":0") or "sprite:0" in item["origin"])
        closet_route = next(item for item in routes["routes"] if item["origin"] != field_route["origin"])
        self.assertTrue(field_route["reachable"] and closet_route["reachable"])
        self.assertGreaterEqual(field_route["sky_sample_fraction"], closet_route["sky_sample_fraction"])
        self.assertEqual(closet_route["hops"], 1)
        self.assertEqual(field_route["hops"], 0)

    def test_cli_writes_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "field.MAP"
            write_map(field_and_closet_map(), path)
            morph = Path(directory) / "morph.json"
            neigh = Path(directory) / "neigh.json"
            route = Path(directory) / "route.json"
            understand = Path(directory) / "understand.json"
            self.assertEqual(main(["morphology", str(path), "-o", str(morph)]), 0)
            self.assertEqual(main(["spawn-neighborhood", str(path), "-o", str(neigh)]), 0)
            self.assertEqual(main(["route-exposure", str(path), "-o", str(route)]), 0)
            self.assertEqual(main(["understand", str(path), "--multiplayer-only", "-o", str(understand)]), 0)
            packet = json.loads(understand.read_text(encoding="utf-8"))
            self.assertEqual(len(packet["neighborhoods"]["neighborhoods"]), 2)
            self.assertIn("morphology", packet)


if __name__ == "__main__":
    unittest.main()
