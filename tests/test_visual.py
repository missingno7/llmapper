"""The observation bridge: request, join, plan, summary.

Everything here runs without commercial Blood data and without the observer
binary.  The parts that need either are in ``test_visual_integration.py`` and
skip themselves.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from bloodmap.levelprog import LevelProgram, Style
from bloodmap.viewplan import (
    ViewPlanError,
    angle_toward,
    eye_z,
    interior_point,
    plan_node_views,
    plan_structure_views,
    portals_of,
    sector_area,
)
from bloodmap.visual import (
    SCHEMA,
    NodeAllocation,
    ObservationError,
    ObservationManifest,
    ObservationRequest,
    SourceMap,
    Viewpoint,
    compact_summary,
    covisibility,
    join_view,
)

U = 384
PH = 0x1600


def two_room_program() -> LevelProgram:
    program = LevelProgram(
        "fixture", name="fixture",
        style=Style(wall_picnum=100, floor_picnum=200, ceiling_picnum=300,
                    floor_z=0, clear_height=6 * PH),
    )
    house = program.assembly("house")
    hall = house.rect_room("hall", size=(10 * U, 8 * U))
    side = house.rect_room("side", size=(6 * U, 6 * U))
    side.place_against("west", hall.face("east", at=0.5, width=6 * U))
    program.connect(hall.face("east", at=0.5, width=6 * U),
                    side.face("west", at=0.5, width=6 * U),
                    connection_id="connection:hall_side")
    program.set_start(hall)
    return program


def compiled_fixture():
    program = two_room_program()
    compiled = program.compile().compile()
    return program, compiled


class RequestTests(unittest.TestCase):
    def test_request_is_deterministic(self):
        views = (Viewpoint("a", 1, 2, 3, angle=512, sector=0),
                 Viewpoint("b", 4, 5, 6, purpose="room_center"))
        left = ObservationRequest("m.MAP", "out", viewpoints=views)
        right = ObservationRequest("m.MAP", "out", viewpoints=views)
        self.assertEqual(json.dumps(left.to_dict()), json.dumps(right.to_dict()))

    def test_the_renderer_never_sees_llmapper_bookkeeping(self):
        view = Viewpoint("a", 1, 2, 3, node="house/hall", purpose="room_center",
                         note="a note")
        wire = view.to_request()
        self.assertNotIn("node", wire)
        self.assertNotIn("purpose", wire)
        self.assertIn("node", view.to_dict())

    def test_a_batch_carries_every_view(self):
        views = tuple(Viewpoint(f"v{i}", i, i, i) for i in range(12))
        request = ObservationRequest("m.MAP", "out", viewpoints=views)
        self.assertEqual(len(request.to_dict()["views"]), 12)
        self.assertEqual([v["id"] for v in request.to_dict()["views"]],
                         [f"v{i}" for i in range(12)])

    def test_screenshots_are_opt_in_per_view(self):
        views = (Viewpoint("a", 0, 0, 0), Viewpoint("b", 0, 0, 0))
        request = ObservationRequest("m.MAP", "out", viewpoints=views)
        self.assertFalse(request.to_dict()["screenshots"])
        self.assertFalse(any(v["screenshot"] for v in request.to_dict()["views"]))
        chosen = request.with_screenshots(["b"])
        self.assertTrue(chosen.to_dict()["screenshots"])
        self.assertEqual([v["screenshot"] for v in chosen.to_dict()["views"]], [False, True])

    def test_a_pose_is_data_not_input(self):
        """No key, no window, no timing: the wire form is only numbers."""
        wire = Viewpoint("a", 10, 20, 30, angle=900, horiz=140, sector=4).to_request()
        self.assertEqual(set(wire) - {"id", "screenshot"}, {"x", "y", "z", "angle", "horiz", "sector"})
        self.assertTrue(all(isinstance(wire[key], int)
                            for key in ("x", "y", "z", "angle", "horiz", "sector")))

    def test_request_writes_and_reads_back(self):
        import tempfile

        request = ObservationRequest("m.MAP", "out", viewpoints=(Viewpoint("a", 1, 1, 1),))
        with tempfile.TemporaryDirectory() as tmp:
            path = request.write(Path(tmp) / "r.json")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), request.to_dict())


class ManifestTests(unittest.TestCase):
    def _manifest(self, views):
        return ObservationManifest(data={
            "$schema": SCHEMA, "schema_version": 1, "views": views,
            "limitations": ["static world state"], "timing_ms": {"view_count": len(views)},
        })

    def test_each_view_id_resolves_exactly_once(self):
        manifest = self._manifest([
            {"id": "a", "status": "ok"}, {"id": "b", "status": "ok"},
        ])
        self.assertEqual(manifest.view_ids, ["a", "b"])
        self.assertEqual(manifest.view("a")["id"], "a")

    def test_a_repeated_view_id_is_refused(self):
        with self.assertRaises(ObservationError):
            self._manifest([{"id": "a", "status": "ok"}, {"id": "a", "status": "ok"}])

    def test_an_invalid_pose_is_reported_not_hidden(self):
        manifest = self._manifest([
            {"id": "a", "status": "ok"},
            {"id": "b", "status": "invalid_pose", "reason": "no sector contains (0, 0)"},
        ])
        self.assertEqual([v["id"] for v in manifest.invalid()], ["b"])

    def test_a_foreign_document_is_refused(self):
        with self.assertRaises(ObservationError):
            ObservationManifest(data={"$schema": "something.else"})


class SourceMapTests(unittest.TestCase):
    def test_every_compiled_sector_has_an_owner(self):
        program, compiled = compiled_fixture()
        source_map = SourceMap.from_level_program(program, compiled)
        self.assertEqual(len(source_map.sector_owner), len(compiled.level.sectors))

    def test_a_node_owns_the_walls_the_compiler_gave_it(self):
        program, compiled = compiled_fixture()
        source_map = SourceMap.from_level_program(program, compiled)
        hall = source_map.allocations["fixture/house/hall"]
        allocation = compiled.allocations["region:fixture/house/hall"]
        self.assertEqual(hall.sectors, frozenset({allocation.sector_id}))
        self.assertEqual(hall.walls, frozenset(allocation.wall_ids))

    def test_a_wall_answers_before_its_sector(self):
        """Two sectors share a portal; the wall id is the specific answer."""
        program, compiled = compiled_fixture()
        source_map = SourceMap.from_level_program(program, compiled)
        side = source_map.allocations["fixture/house/side"]
        wall = min(side.walls)
        self.assertEqual(source_map.owner(sector=0, wall=wall), "fixture/house/side")

    def test_overlay_kinds_do_not_claim_sectors(self):
        records = [
            NodeAllocation("a/space", ("a", "space"), "space", frozenset({1, 2})),
            NodeAllocation("a/stair", ("a", "stair"), "structure", frozenset({1})),
        ]
        source_map = SourceMap(records, owner_kinds=("space",))
        self.assertEqual(source_map.sector_owner[1], "a/space")
        self.assertIn("a/stair", source_map.allocations)

    def test_hierarchy_nodes_with_children_still_own_their_sectors(self):
        """A space with a detail group hanging off it is still a place."""
        from bloodmap.model import LevelIR

        level = LevelIR(
            metadata={}, player_start={}, sky={},
            sectors=[{"id": 0, "fields": {"wall_ptr": 0, "wall_count": 3}, "blood": None}],
            walls=[{"id": i, "fields": {"x": 0, "y": 0, "point2": (i + 1) % 3,
                                        "next_sector": -1, "picnum": 0}, "blood": None}
                   for i in range(3)],
            sprites=[],
        )
        hierarchy = {"nodes": [
            {"id": "a", "kind": "assembly", "parent": None, "children": ["a/s"], "sectors": [0]},
            {"id": "a/s", "kind": "space", "parent": "a", "children": ["a/s/d"], "sectors": [0]},
            {"id": "a/s/d", "kind": "detail_group", "parent": "a/s", "children": [], "sectors": []},
        ]}
        source_map = SourceMap.from_hierarchy(hierarchy, level)
        self.assertEqual(source_map.sector_owner[0], "a/s")
        self.assertEqual(source_map.path_of("a/s"), ("a", "a/s"))


class JoinTests(unittest.TestCase):
    def setUp(self):
        self.source_map = SourceMap([
            NodeAllocation("level/lobby", ("level", "lobby"), "room",
                           frozenset({0}), frozenset({0, 1, 2, 3})),
            NodeAllocation("level/gallery", ("level", "gallery"), "room",
                           frozenset({1}), frozenset({4, 5, 6, 7})),
        ])
        self.view = {
            "id": "v", "status": "ok",
            "camera": {"x": 0, "y": 0, "z": 0, "angle": 0, "horiz": 100, "sector": 0},
            "frame": {"pixels": 1000, "painted": 1000, "sky_pixels": 100},
            "surfaces": [
                {"kind": "wall", "sector": 0, "wall": 1, "picnum": 90, "shade": 0,
                 "pal": 0, "pixels": 700, "columns": 100, "bbox": [0, 0, 99, 99]},
                {"kind": "floor", "sector": 1, "picnum": 44, "shade": 0, "pal": 0,
                 "pixels": 200, "columns": 40, "bbox": [30, 50, 69, 99]},
                {"kind": "sprite", "sector": 0, "sprite": 3, "picnum": 700, "shade": 0,
                 "pal": 0, "pixels": 20, "columns": 10, "bbox": [10, 10, 19, 12]},
            ],
            "occluded": [{"kind": "wall", "sector": 1, "wall": 5, "picnum": 91}],
        }

    def test_native_ids_resolve_to_source_nodes(self):
        join = join_view(self.view, self.source_map)
        self.assertEqual([r["node"] for r in join["visible"]],
                         ["level/lobby", "level/gallery"])

    def test_prominence_is_the_renderers_own_measure(self):
        join = join_view(self.view, self.source_map)
        lobby = join["visible"][0]
        self.assertEqual(lobby["pixels"], 720)
        self.assertAlmostEqual(lobby["frame_fraction"], 0.72)
        self.assertAlmostEqual(lobby["structural_fraction"], 0.70)

    def test_a_node_already_visible_is_not_also_reported_occluded(self):
        join = join_view(self.view, self.source_map)
        self.assertEqual(join["occluded"], [])

    def test_a_node_only_occluded_is_kept(self):
        view = dict(self.view, surfaces=self.view["surfaces"][:1])
        join = join_view(view, self.source_map)
        self.assertEqual([r["node"] for r in join["occluded"]], ["level/gallery"])

    def test_a_refused_pose_joins_to_nothing_and_says_why(self):
        view = {"id": "v", "status": "invalid_pose", "reason": "eye z is below the floor"}
        join = join_view(view, self.source_map)
        self.assertEqual(join["visible"], [])
        self.assertIn("below the floor", join["reason"])

    def test_summary_is_bounded_and_carries_no_buffers(self):
        join = join_view(self.view, self.source_map)
        text = compact_summary(self.view, join)
        self.assertLess(len(text), 1200)
        self.assertIn("level/lobby", text)
        self.assertNotIn("bbox", text)
        self.assertNotIn("columns", text)

    def test_summary_states_no_verdict(self):
        join = join_view(self.view, self.source_map)
        text = compact_summary(self.view, join).lower()
        for word in ("good", "bad", "beautiful", "boring", "score", "quality"):
            self.assertNotIn(word, text)


class CovisibilityTests(unittest.TestCase):
    def test_mutual_visibility_is_distinguished_from_one_way(self):
        source_map = SourceMap([
            NodeAllocation("a", ("a",), "room", frozenset({0})),
            NodeAllocation("b", ("b",), "room", frozenset({1})),
        ])
        def view(view_id, sector, others):
            return {
                "id": view_id, "status": "ok",
                "camera": {"x": 0, "y": 0, "z": 0, "sector": sector},
                "frame": {"pixels": 100, "painted": 100, "sky_pixels": 0},
                "surfaces": [{"kind": "wall", "sector": s, "picnum": 1, "pixels": p,
                              "columns": 1, "bbox": [0, 0, 1, 1]}
                             for s, p in others],
                "occluded": [],
            }
        manifest = ObservationManifest(data={
            "$schema": SCHEMA, "schema_version": 1,
            "views": [view("va", 0, [(0, 60), (1, 40)]), view("vb", 1, [(1, 100)])],
        })
        result = covisibility(manifest, source_map)
        self.assertEqual(len(result["pairs"]), 1)
        pair = result["pairs"][0]
        self.assertEqual(pair["nodes"], ["a", "b"])
        self.assertFalse(pair["mutual"])


class ViewPlanTests(unittest.TestCase):
    def setUp(self):
        self.program, self.compiled = compiled_fixture()
        self.level = self.compiled.level
        self.source_map = SourceMap.from_level_program(self.program, self.compiled)

    def test_a_plan_is_deterministic(self):
        first = plan_node_views(self.level, self.source_map, "fixture/house/hall")
        second = plan_node_views(self.level, self.source_map, "fixture/house/hall")
        self.assertEqual([v.to_dict() for v in first], [v.to_dict() for v in second])

    def test_planned_poses_are_inside_their_sector(self):
        from bloodmap.viewpoints import _contains

        for view in plan_node_views(self.level, self.source_map, "fixture/house/hall"):
            self.assertTrue(_contains(self.level, view.sector, view.x, view.y))

    def test_planned_eye_height_is_between_floor_and_ceiling(self):
        for view in plan_node_views(self.level, self.source_map, "fixture/house/hall"):
            fields = self.level.sectors[view.sector]["fields"]
            self.assertLess(int(fields["ceiling_z"]), view.z)
            self.assertGreater(int(fields["floor_z"]), view.z)

    def test_an_unknown_node_is_an_error_not_an_empty_plan(self):
        with self.assertRaises(ViewPlanError):
            plan_node_views(self.level, self.source_map, "fixture/house/attic")

    def test_a_view_toward_a_child_faces_the_child(self):
        views = plan_node_views(
            self.level, self.source_map, "fixture/house/hall",
            include=("toward_child",), child_nodes=("fixture/house/side",),
        )
        self.assertEqual(len(views), 1)
        centre = interior_point(self.level, views[0].sector)
        target = interior_point(self.level, min(
            self.source_map.allocations["fixture/house/side"].sectors))
        self.assertEqual(views[0].angle, angle_toward(centre, target))

    def test_angles_follow_build_conventions(self):
        self.assertEqual(angle_toward((0, 0), (100, 0)), 0)
        self.assertEqual(angle_toward((0, 0), (0, 100)), 512)
        self.assertEqual(angle_toward((0, 0), (-100, 0)), 1024)
        self.assertEqual(angle_toward((0, 0), (0, -100)), 1536)

    def test_a_sector_reports_its_portals_widest_first(self):
        hall = min(self.source_map.allocations["fixture/house/hall"].sectors)
        portals = portals_of(self.level, hall)
        self.assertTrue(portals)
        self.assertEqual([p["width"] for p in portals],
                         sorted((p["width"] for p in portals), reverse=True))

    def test_interior_point_of_a_carved_room_is_not_in_its_hole(self):
        program = LevelProgram(
            "carved", name="carved",
            style=Style(wall_picnum=1, floor_picnum=2, ceiling_picnum=3,
                        floor_z=0, clear_height=6 * PH),
        )
        yard = program.assembly("out").rect_room(
            "yard", size=(30 * U, 30 * U),
            region_kwargs={"declared_zero_exit": True})
        yard.carve([(10 * U, 10 * U), (20 * U, 10 * U), (20 * U, 20 * U), (10 * U, 20 * U)])
        program.set_start(yard, local=(0.05, 0.05))
        compiled = program.compile().compile()
        source_map = SourceMap.from_level_program(program, compiled)
        sector = min(source_map.allocations["carved/out/yard"].sectors)
        point = interior_point(compiled.level, sector)
        self.assertIsNotNone(point)
        from bloodmap.viewpoints import _contains
        self.assertTrue(_contains(compiled.level, sector, *point))

    def test_a_flat_node_plans_no_vertical_views(self):
        self.assertEqual(
            plan_structure_views(self.level, self.source_map, "fixture/house/hall"), [])

    def test_sector_area_subtracts_holes(self):
        program = LevelProgram(
            "carved", name="carved",
            style=Style(wall_picnum=1, floor_picnum=2, ceiling_picnum=3,
                        floor_z=0, clear_height=6 * PH),
        )
        yard = program.assembly("out").rect_room(
            "yard", size=(30 * U, 30 * U),
            region_kwargs={"declared_zero_exit": True})
        yard.carve([(10 * U, 10 * U), (20 * U, 10 * U), (20 * U, 20 * U), (10 * U, 20 * U)])
        program.set_start(yard, local=(0.05, 0.05))
        compiled = program.compile().compile()
        sector = compiled.allocations["region:carved/out/yard"].sector_id
        self.assertAlmostEqual(sector_area(compiled.level, sector),
                               (30 * U) ** 2 - (10 * U) ** 2, delta=1.0)

    def test_no_clearance_means_no_pose(self):
        from bloodmap.model import LevelIR

        level = LevelIR(
            metadata={}, player_start={}, sky={},
            sectors=[{"id": 0, "fields": {"wall_ptr": 0, "wall_count": 3,
                                          "floor_z": 0, "ceiling_z": -100}, "blood": None}],
            walls=[], sprites=[],
        )
        self.assertIsNone(eye_z(level, 0))


if __name__ == "__main__":
    unittest.main()
