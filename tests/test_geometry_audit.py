"""Geometry audit and authored-validator regressions."""

from __future__ import annotations

import unittest

from bloodmap.construction import LevelBuilder
from bloodmap.geometry_audit import (
    audit_geometry,
    validate_authored_geometry,
    validate_authored_level,
)
from bloodmap.planar_geom import classify_segment_pair, polygon_relation, validate_loop


class PlanarGeomTests(unittest.TestCase):
    def test_classifies_reversed_partial_and_crossing(self):
        reversed_exact = classify_segment_pair((0, 0), (100, 0), (100, 0), (0, 0))
        self.assertEqual(reversed_exact["kind"], "exact_reversed_coincident")
        partial = classify_segment_pair((0, 0), (100, 0), (80, 0), (20, 0))
        self.assertEqual(partial["kind"], "partial_collinear_overlap")
        self.assertFalse(partial["same_direction"])
        same = classify_segment_pair((0, 0), (100, 0), (0, 0), (100, 0))
        self.assertEqual(same["kind"], "exact_same_direction_coincident")
        tee = classify_segment_pair((0, 0), (100, 0), (40, 0), (40, 50))
        self.assertEqual(tee["kind"], "t_junction")
        cross = classify_segment_pair((0, 0), (100, 100), (0, 100), (100, 0))
        self.assertEqual(cross["kind"], "proper_crossing")

    def test_loop_validation_and_containment(self):
        self.assertTrue(validate_loop([(0, 0), (0, 10), (10, 10), (10, 0)]))  # CCW → winding error
        self.assertFalse(validate_loop([(0, 0), (10, 0), (10, 10), (0, 10)]))
        outer = [[(0, 0), (100, 0), (100, 100), (0, 100)]]
        inner = [[(20, 20), (80, 20), (80, 80), (20, 80)]]
        relation = polygon_relation(inner, outer)
        self.assertIn(relation["kind"], {"full_containment_a_in_b", "hole_containment"})


class GeometryAuditTests(unittest.TestCase):
    def test_disconnected_rooms_are_flagged_even_when_native_validation_passes(self):
        builder = LevelBuilder()
        a = builder.add_sector([(0, 0), (4096, 0), (4096, 4096), (0, 4096)])
        builder.add_sector([(8192, 0), (12288, 0), (12288, 4096), (8192, 4096)])
        builder.set_player_start(sector=a.sector_id, x=2048, y=2048, z=0, angle=0)
        level = builder.build()
        self.assertFalse([item for item in __import__("bloodmap.analysis", fromlist=["validate_map"]).validate_map(level.to_disk_map()) if item.severity == "error"])
        authored = validate_authored_geometry(level)
        codes = {item.code for item in authored}
        self.assertTrue({"zero_exit_gameplay_sector"} & codes or any("zero_exit" in item.code for item in authored))

    def test_overlapping_footprints_are_authored_errors(self):
        builder = LevelBuilder()
        a = builder.add_sector([(0, 0), (8000, 0), (8000, 8000), (0, 8000)])
        builder.add_sector([(2000, 2000), (6000, 2000), (6000, 6000), (2000, 6000)])
        builder.set_player_start(sector=a.sector_id, x=500, y=500, z=0, angle=0)
        level = builder.build()
        audit = audit_geometry(level)
        self.assertEqual(audit["native_validation_errors"], 0)
        self.assertTrue(audit["summaries"]["sector_footprint_intersections"])
        errors = [item for item in validate_authored_geometry(level) if item.severity == "error"]
        self.assertTrue(errors)

    def test_unpaired_coincident_walls_are_errors(self):
        builder = LevelBuilder()
        a = builder.add_sector([(0, 0), (4096, 0), (4096, 4096), (0, 4096)])
        builder.add_sector([(4096, 0), (8192, 0), (8192, 4096), (4096, 4096)])
        builder.set_player_start(sector=a.sector_id, x=2048, y=2048, z=0, angle=0)
        level = builder.build()
        audit = audit_geometry(level)
        self.assertTrue(audit["summaries"]["unpaired_coincident_walls"])
        self.assertFalse(audit["summaries"].get("reciprocal_portals") or [])

    def test_dm_start_isolation_gate(self):
        builder = LevelBuilder()
        a = builder.add_sector([(0, 0), (8192, 0), (8192, 8192), (0, 8192)])
        b = builder.add_sector([(20000, 0), (24000, 0), (24000, 4096), (20000, 4096)])
        builder.set_player_start(sector=a.sector_id, x=4096, y=4096, z=0, angle=0)
        builder.add_sprite(sector=a.sector_id, x=4096, y=4096, z=0, type=2, picnum=0)
        builder.add_sprite(sector=b.sector_id, x=22000, y=2048, z=0, type=2, picnum=0)
        level = builder.build()
        diagnostics = validate_authored_level(level)
        codes = {item.code for item in diagnostics}
        self.assertIn("all_dm_starts_reach_main_network", codes)

    def test_integer_intersection_is_lattice_or_none(self):
        from bloodmap.planar_geom import integer_intersection
        self.assertEqual(integer_intersection((0, 0), (100, 100), (0, 100), (100, 0)), (50, 50))
        self.assertIsNone(integer_intersection((0, 0), (5, 2), (0, 2), (5, 0)))

    def test_same_winding_nested_loop_is_invalid_hole(self):
        from bloodmap.planar_geom import validate_loop
        outer = [(0, 0), (100, 0), (100, 100), (0, 100)]
        hole_same_winding = [(20, 20), (80, 20), (80, 80), (20, 80)]
        self.assertFalse(validate_loop(outer, role="outer"))
        self.assertTrue(validate_loop(hole_same_winding, role="hole"))
        hole_ccw = [(20, 20), (20, 80), (80, 80), (80, 20)]
        self.assertFalse(validate_loop(hole_ccw, role="hole"))

    def test_gated_pocket_is_allowed_only_when_declared(self):
        builder = LevelBuilder()
        yard = builder.add_sector([(0, 0), (8192, 0), (8192, 8192), (0, 8192)])
        hall = builder.add_sector([(8192, 0), (12288, 0), (12288, 8192), (8192, 8192)])
        pocket = builder.add_sector([(20000, 0), (22000, 0), (22000, 2000), (20000, 2000)])
        builder.connect(yard.wall_ids[1], hall.wall_ids[3])
        builder.set_player_start(sector=yard.sector_id, x=4096, y=4096, z=0, angle=0)
        builder.add_sprite(sector=yard.sector_id, x=4096, y=4096, z=0, type=2, picnum=0)
        builder.add_sprite(sector=pocket.sector_id, x=21000, y=1000, z=0, type=144, picnum=0, status=3)
        level = builder.build()
        undeclared = [item for item in validate_authored_level(level) if item.severity == "error"]
        declared = [
            item for item in validate_authored_level(level, gated_sectors={pocket.sector_id})
            if item.severity == "error"
        ]
        self.assertTrue(any(item.code == "zero_exit_gameplay_sector" for item in undeclared))
        self.assertFalse([item for item in declared if item.code == "zero_exit_gameplay_sector"])


if __name__ == "__main__":
    unittest.main()
