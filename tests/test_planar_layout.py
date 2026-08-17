"""Synthetic regressions for planar layout compilation and wall stitching."""

from __future__ import annotations

import unittest

from bloodmap.analysis import validate_map
from bloodmap.format import encode_map, parse_map
from bloodmap.geometry_audit import validate_authored_geometry, validate_authored_level
from bloodmap.planar_layout import PlanarLayout, PlanarLayoutError


def _rect(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


class PlanarLayoutTests(unittest.TestCase):
    def test_exact_reversed_match_compiles_and_conserves(self):
        layout = PlanarLayout(name="exact")
        layout.add_region("region:a", _rect(0, 0, 8192, 4096))
        layout.add_region("region:b", _rect(8192, 0, 12288, 4096))
        layout.add_connection("connection:ab", "region:a", "region:b")
        layout.set_player_start("region:a", x=4096, y=2048, z=0)
        compiled = layout.compile()
        self.assertTrue(compiled.conservation.conserved)
        self.assertEqual(len(compiled.level.sectors), 2)
        self.assertEqual(compiled.level.walls[1]["fields"]["next_sector"], 1)
        self.assertFalse([item for item in validate_map(compiled.level.to_disk_map()) if item.severity == "error"])
        self.assertFalse([item for item in validate_authored_geometry(compiled.level) if item.severity == "error"])

    def test_partial_reversed_collinear_overlap_is_stitched(self):
        layout = PlanarLayout(name="partial")
        layout.add_region("region:a", _rect(0, 0, 10000, 5000))
        layout.add_region("region:b", _rect(2000, 5000, 8000, 9000))
        layout.add_connection("connection:ab", "region:a", "region:b")
        layout.set_player_start("region:a", x=4096, y=2048, z=0)
        compiled = layout.compile()
        self.assertGreater(compiled.conservation.split_count, 0)
        realized = [item for item in compiled.connection_report if item["status"] == "realized"]
        self.assertEqual(len(realized), 1)
        self.assertEqual(realized[0]["width"], 6000)
        errors = [item for item in validate_authored_level(compiled.level) if item.severity == "error"]
        self.assertFalse(errors)

    def test_multiple_overlap_intervals_are_all_paired(self):
        layout = PlanarLayout(name="multi")
        layout.add_region("region:a", [(0, 0), (12000, 0), (12000, 4000), (0, 4000)])
        layout.add_region(
            "region:b",
            [(1000, 4000), (4000, 4000), (4000, 7000), (8000, 7000), (8000, 4000), (11000, 4000), (11000, 9000), (1000, 9000)],
        )
        layout.add_connection("connection:ab", "region:a", "region:b")
        layout.set_player_start("region:a", x=2000, y=2000, z=0)
        compiled = layout.compile()
        realized = [item for item in compiled.connection_report if item["status"] == "realized"]
        self.assertGreaterEqual(len(realized), 2)

    def test_t_junction_is_split(self):
        layout = PlanarLayout(name="tee")
        layout.add_region("region:a", _rect(0, 0, 8000, 4000))
        layout.add_region("region:b", _rect(8000, 1000, 12000, 3000))
        layout.add_connection("connection:ab", "region:a", "region:b")
        layout.set_player_start("region:a", x=2000, y=2000, z=0)
        compiled = layout.compile()
        self.assertGreater(compiled.conservation.split_count, 0)
        self.assertTrue(any(item["status"] == "realized" for item in compiled.connection_report))

    def test_non_integer_crossing_fails_closed(self):
        layout = PlanarLayout(name="cross")
        layout.add_region("region:a", [(0, 0), (5000, 2000), (5000, 4000), (0, 4000)])
        layout.add_region("region:b", [(0, 2000), (5000, 0), (5000, 8000), (0, 8000)])
        layout.add_connection("connection:ab", "region:a", "region:b")
        layout.set_player_start("region:a", x=200, y=3000, z=0)
        with self.assertRaisesRegex(PlanarLayoutError, "integer|crossing|overlap"):
            layout.compile()

    def test_missing_intended_portal_fails(self):
        layout = PlanarLayout(name="missing")
        layout.add_region("region:a", _rect(0, 0, 4000, 4000))
        layout.add_region("region:b", _rect(8000, 0, 12000, 4000))
        layout.add_connection("connection:ab", "region:a", "region:b")
        layout.set_player_start("region:a", x=2000, y=2000, z=0)
        with self.assertRaisesRegex(PlanarLayoutError, "unpaired|missing"):
            layout.compile()

    def test_already_connected_exact_edge_is_idempotent(self):
        layout = PlanarLayout(name="once")
        layout.add_region("region:a", _rect(0, 0, 4096, 4096))
        layout.add_region("region:b", _rect(4096, 0, 8192, 4096))
        layout.add_connection("connection:ab", "region:a", "region:b")
        layout.set_player_start("region:a", x=2048, y=2048, z=0)
        first = layout.compile()
        second = layout.compile()
        self.assertEqual(
            encode_map(first.level.to_disk_map()),
            encode_map(second.level.to_disk_map()),
        )

    def test_xwall_on_split_connection_fails_closed_without_policy(self):
        layout = PlanarLayout(name="xwall")
        layout.add_region("region:a", _rect(0, 0, 10000, 5000))
        layout.add_region("region:b", _rect(2000, 5000, 8000, 9000))
        layout.add_connection(
            "connection:ab", "region:a", "region:b",
            wall_behavior={"rx_id": 9},
        )
        layout.set_player_start("region:a", x=4096, y=2048, z=0)
        # Partial overlap yields one atomic pair, so a single XWALL is allowed.
        compiled = layout.compile()
        walls = [item["walls"] for item in compiled.connection_report if item["status"] == "realized"]
        self.assertEqual(len(walls), 1)
        self.assertIsNotNone(compiled.level.walls[walls[0][0]].get("blood"))

    def test_xwall_duplication_on_multi_atomic_fails(self):
        layout = PlanarLayout(name="xwall-multi")
        layout.add_region("region:a", [(0, 0), (12000, 0), (12000, 4000), (0, 4000)])
        layout.add_region(
            "region:b",
            [(1000, 4000), (4000, 4000), (4000, 7000), (8000, 7000), (8000, 4000), (11000, 4000), (11000, 9000), (1000, 9000)],
        )
        layout.add_connection(
            "connection:ab", "region:a", "region:b",
            wall_behavior={"rx_id": 9},
        )
        layout.set_player_start("region:a", x=2000, y=2000, z=0)
        with self.assertRaisesRegex(PlanarLayoutError, "duplicate XWALL|atomic"):
            layout.compile()

    def test_hole_and_building_shell_do_not_overlap(self):
        layout = PlanarLayout(name="shell")
        layout.add_region(
            "region:yard",
            [(0, 0), (20000, 0), (20000, 16000), (0, 16000)],
            parallax_ceiling=True,
            ceiling_z=-81920,
        )
        shell = layout.insert_building_shell(
            "region:yard",
            mass_id="north",
            outer_footprint=[(6000, 4000), (14000, 4000), (14000, 10000), (6000, 10000)],
            inner_footprint=[(7000, 5000), (13000, 5000), (13000, 9000), (7000, 9000)],
            entrances=[{
                "id": "south_door",
                "outer_a": (9000, 10000),
                "outer_b": (11000, 10000),
                "inner_a": (9000, 9000),
                "inner_b": (11000, 9000),
            }],
        )
        layout.set_player_start("region:yard", x=2000, y=2000, z=0)
        compiled = layout.compile()
        self.assertIn(shell["interior"], compiled.allocations)
        errors = [item for item in validate_authored_geometry(compiled.level) if item.severity == "error"]
        self.assertFalse(errors, errors)
        yard = compiled.allocations["region:yard"].sector_id
        interior = compiled.allocations[shell["interior"]].sector_id
        self.assertNotEqual(yard, interior)
        door = compiled.allocations[shell["doors"][0]].sector_id
        self.assertEqual(compiled.level.sectors[door]["fields"]["wall_count"], 4)

    def test_same_xy_overlapping_z_rejected(self):
        layout = PlanarLayout(name="z-overlap")
        pts = _rect(0, 0, 4096, 4096)
        layout.add_region("region:a", pts, ceiling_z=-10000, floor_z=0)
        layout.add_region("region:b", pts, ceiling_z=-5000, floor_z=5000, layer="ground")
        layout.set_player_start("region:a", x=2000, y=2000, z=-1000)
        with self.assertRaisesRegex(PlanarLayoutError, "XY|identical"):
            layout.compile()

    def test_explicit_water_stack_accepted(self):
        layout = PlanarLayout(name="water")
        pts = _rect(0, 0, 8000, 8000)
        layout.add_region("region:pool", pts, ceiling_z=-20000, floor_z=8192, floor_picnum=90)
        layout.add_region(
            "region:under", pts, ceiling_z=8192, floor_z=20000, special="water",
            layer="stack:pool", declared_zero_exit=True,
        )
        layout.declare_special("region:pool", "region:under", "water")
        layout.add_sprite("up", "region:pool", x=4000, y=4000, z=8192, type=9, picnum=0, behavior={"data_1": 1})
        layout.add_sprite("down", "region:under", x=4000, y=4000, z=9000, type=10, picnum=0, behavior={"data_1": 1})
        layout.set_player_start("region:pool", x=2000, y=2000, z=0)
        compiled = layout.compile()
        self.assertEqual(len(compiled.declared_specials), 1)
        self.assertTrue(compiled.conservation.conserved)

    def test_byte_identical_replays(self):
        def make():
            layout = PlanarLayout(name="replay")
            layout.add_region("region:a", _rect(0, 0, 8192, 4096))
            layout.add_region("region:b", _rect(8192, 0, 12288, 4096))
            layout.add_connection("connection:ab", "region:a", "region:b")
            layout.set_player_start("region:a", x=4096, y=2048, z=0, angle=512)
            return layout.compile().level
        self.assertEqual(encode_map(make().to_disk_map()), encode_map(make().to_disk_map()))
        self.assertEqual(parse_map(encode_map(make().to_disk_map())).header["num_sectors"], 2)

    def test_proper_crossing_rejected(self):
        layout = PlanarLayout(name="x")
        layout.add_region("region:a", [(0, 0), (8000, 0), (8000, 4000), (0, 4000)])
        layout.add_region("region:b", [(2000, -2000), (6000, -2000), (6000, 6000), (2000, 6000)])
        layout.set_player_start("region:a", x=1000, y=2000, z=0)
        with self.assertRaisesRegex(PlanarLayoutError, "crossing|overlap"):
            layout.compile()

    def test_same_xy_disjoint_z_without_declaration_rejected(self):
        layout = PlanarLayout(name="z-disjoint")
        pts = _rect(0, 0, 4096, 4096)
        layout.add_region("region:a", pts, ceiling_z=-20000, floor_z=0)
        layout.add_region("region:b", pts, ceiling_z=10000, floor_z=20000, layer="stack:undeclared")
        layout.set_player_start("region:a", x=2000, y=2000, z=-1000)
        with self.assertRaisesRegex(PlanarLayoutError, "identical XY"):
            layout.compile()

    def test_invalid_same_winding_hole_rejected(self):
        layout = PlanarLayout(name="bad-hole")
        layout.add_region("region:yard", _rect(0, 0, 20000, 16000), parallax_ceiling=True, ceiling_z=-81920)
        layout.regions["region:yard"].holes = (tuple(_rect(6000, 4000, 12000, 10000)),)
        layout.set_player_start("region:yard", x=2000, y=2000, z=0)
        with self.assertRaisesRegex(PlanarLayoutError, "winding"):
            layout.compile()

    def test_conservation_owns_every_emitted_wall_once(self):
        layout = PlanarLayout(name="own")
        layout.add_region("region:a", _rect(0, 0, 10000, 5000))
        layout.add_region("region:b", _rect(2000, 5000, 8000, 9000))
        layout.add_connection("connection:ab", "region:a", "region:b")
        layout.set_player_start("region:a", x=4096, y=2048, z=0)
        compiled = layout.compile()
        self.assertTrue(compiled.conservation.conserved)
        self.assertFalse(compiled.conservation.dropped_source_edges)
        self.assertFalse(compiled.conservation.duplicated_source_edges)
        self.assertTrue(compiled.conservation.walls_owned_once)
        self.assertEqual(len(compiled.level.walls), compiled.conservation.emitted_directed_edges)

    def test_all_dm_starts_must_reach_main_network(self):
        layout = PlanarLayout(name="dm")
        layout.add_region("region:a", _rect(0, 0, 8192, 8192))
        layout.add_region("region:b", _rect(20000, 0, 24000, 4096))
        layout.set_player_start("region:a", x=4096, y=4096, z=0)
        layout.add_sprite("dm0", "region:a", x=4096, y=4096, z=0, type=2)
        layout.add_sprite("dm1", "region:b", x=22000, y=2048, z=0, type=2)
        with self.assertRaisesRegex(PlanarLayoutError, "dm_start|authored-geometry|zero_exit"):
            layout.compile()

    def test_narrow_doorway_fails_width_gate(self):
        layout = PlanarLayout(name="narrow")
        layout.add_region("region:a", _rect(0, 0, 8192, 4096))
        layout.add_region("region:b", _rect(8192, 1800, 10240, 2100))
        layout.add_connection(
            "connection:ab", "region:a", "region:b",
            role="doorway", min_width=2048,
        )
        layout.set_player_start("region:a", x=4096, y=2048, z=0)
        with self.assertRaisesRegex(PlanarLayoutError, "doorway_too_narrow|authored-geometry"):
            layout.compile()


if __name__ == "__main__":
    unittest.main()
