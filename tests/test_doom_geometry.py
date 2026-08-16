"""Characterization and regression tests for Doom → Build boundary lowering.

These tests encode required conservation and determinism. Known defects in the
current tracer are marked expectedFailure until the geometry workstream lands.
"""

from __future__ import annotations

import itertools
import unittest
from collections import Counter

from bloodmap.construction import new_level
from bloodmap.doom import DoomThing
from bloodmap.doom_convert import DoomConversionError, convert_doom_to_blood
from bloodmap.doom_fixtures import _sector, assemble_doom
from bloodmap.doom_geometry import DoomGeometryError, canonical_topology, extract_sector_loops, lower_doom_geometry
from bloodmap.model import LevelIR


def _square(origin: tuple[int, int], size: int = 64) -> list[tuple[int, int]]:
    x, y = origin
    return [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]


def _clockwise_square_lines(vertex_base: int, sector: int, *, back=None, special: int = 0, tag: int = 0):
    """Interior-on-right outer loop: (0,3), (3,2), (2,1), (1,0) relative to base."""
    a, b, c, d = vertex_base, vertex_base + 1, vertex_base + 2, vertex_base + 3
    return [
        (a, d, sector, back, special, tag),
        (d, c, sector, back, special, tag),
        (c, b, sector, back, special, tag),
        (b, a, sector, back, special, tag),
    ]


def _disconnected_two_squares() -> object:
    vertices = _square((0, 0)) + _square((128, 0))
    lines = _clockwise_square_lines(0, 0) + _clockwise_square_lines(4, 0)
    return assemble_doom(
        "MAP01",
        vertices,
        lines,
        [_sector()],
        [DoomThing(32, 32, 0, 1, 7)],
    )


def _touching_two_squares(line_order: str = "ab") -> object:
    """Two outer squares that share exactly one vertex at (64, 64)."""
    vertices = _square((0, 0)) + _square((64, 64))
    lines_a = _clockwise_square_lines(0, 0)
    lines_b = _clockwise_square_lines(4, 0)
    if line_order == "ab":
        lines = lines_a + lines_b
    elif line_order == "ba":
        lines = lines_b + lines_a
    elif line_order == "interleaved":
        lines = list(itertools.chain.from_iterable(zip(lines_a, lines_b)))
    else:
        raise ValueError(line_order)
    return assemble_doom(
        "MAP01",
        vertices,
        lines,
        [_sector()],
        [DoomThing(32, 32, 0, 1, 7)],
    )


def _nested_hole() -> object:
    outer = _square((0, 0), 192)
    inner = _square((64, 64), 64)
    vertices = outer + inner
    outer_lines = _clockwise_square_lines(0, 0)
    a, b, c, d = 4, 5, 6, 7
    hole_lines = [
        (a, b, 0, None),
        (b, c, 0, None),
        (c, d, 0, None),
        (d, a, 0, None),
    ]
    return assemble_doom(
        "MAP01",
        vertices,
        outer_lines + hole_lines,
        [_sector()],
        [DoomThing(32, 32, 0, 1, 7)],
    )


def _source_directed_edges(level, sector_id: int) -> list[tuple[int, int, int, int, int, int]]:
    from bloodmap.doom import NO_SIDE

    edges = []
    for line_id, line in enumerate(level.linedefs):
        for side, reverse in ((0, False), (1, True)):
            side_id = line.side_front if side == 0 else line.side_back
            if side_id == NO_SIDE or not 0 <= side_id < len(level.sidedefs):
                continue
            if int(level.sidedefs[side_id].sector) != sector_id:
                continue
            a, b = level.vertices[line.v1], level.vertices[line.v2]
            if reverse:
                edges.append((b.x, b.y, a.x, a.y, line_id, side))
            else:
                edges.append((a.x, a.y, b.x, b.y, line_id, side))
    return edges


def _emitted_edges(loops) -> list[tuple[int, int, int, int, int, int]]:
    edges = list(loops.outer)
    for hole in loops.holes:
        edges.extend(hole)
    extra = getattr(loops, "extra_outers", None) or []
    for loop in extra:
        edges.extend(loop)
    if hasattr(loops, "components"):
        edges = [edge for component in loops.components for edge in component.all_edges()]
    return [(edge.x1, edge.y1, edge.x2, edge.y2, edge.linedef, edge.side) for edge in edges]


def _rotate_min(seq: tuple) -> tuple:
    if not seq:
        return seq
    start = min(range(len(seq)), key=lambda index: seq[index])
    return seq[start:] + seq[:start]


def _canonical_loops_from_extract(loops) -> dict:
    all_loops = []
    if hasattr(loops, "components"):
        for component in loops.components:
            all_loops.append(component.outer.edges)
            all_loops.extend(hole.edges for hole in component.holes)
    else:
        all_loops = [loops.outer, *loops.holes]
    components = []
    for loop in all_loops:
        directed = tuple((edge.x1, edge.y1, edge.x2, edge.y2, edge.linedef, edge.side) for edge in loop)
        components.append(_rotate_min(directed))
    components.sort()
    return {
        "directed_edge_multiset": Counter(
            (edge.x1, edge.y1, edge.x2, edge.y2, edge.linedef, edge.side)
            for loop in all_loops
            for edge in loop
        ),
        "boundary_components": tuple(components),
    }


def _canonical_from_ir(ir: LevelIR) -> dict:
    components = []
    ownership = []
    directed = []
    for sector_id, sector in enumerate(ir.sectors):
        first = int(sector["fields"]["wall_ptr"])
        count = int(sector["fields"]["wall_count"])
        used = [False] * count
        loops = []
        for offset in range(count):
            if used[offset]:
                continue
            loop = []
            current = offset
            for _ in range(count + 1):
                if used[current]:
                    break
                used[current] = True
                wall_id = first + current
                wall = ir.walls[wall_id]["fields"]
                nxt = int(wall["point2"])
                end = ir.walls[nxt]["fields"]
                loop.append((int(wall["x"]), int(wall["y"]), int(end["x"]), int(end["y"])))
                current = nxt - first
            loops.append(_rotate_min(tuple(loop)))
        loops.sort()
        components.append((sector_id, tuple(loops)))
        ownership.append((sector_id, count))
        directed.extend(item for _sid, loops_for_sector in [(sector_id, loops)] for item in loops_for_sector)
    portals = []
    for wall_id, wall in enumerate(ir.walls):
        nxt = int(wall["fields"]["next_wall"])
        nsec = int(wall["fields"]["next_sector"])
        if nxt >= 0:
            pair = tuple(sorted((wall_id, nxt)))
            portals.append((pair, tuple(sorted((
                int(ir.walls[wall_id]["fields"]["next_sector"]),
                nsec,
            )))))
    return {
        "directed_edge_multiset": Counter(edge for _sid, loops in components for loop in loops for edge in loop),
        "boundary_components": tuple(components),
        "portal_pairings": tuple(sorted(set(portals))),
        "sector_ownership": tuple(ownership),
        "wall_count": len(ir.walls),
    }


def _assert_conserved_or_typed_failure(test: unittest.TestCase, level, sector_id: int = 0) -> None:
    source = _source_directed_edges(level, sector_id)
    try:
        loops = extract_sector_loops(level, sector_id)
    except DoomGeometryError as exc:
        message = str(exc)
        test.assertIn(f"sector:{sector_id}", message)
        test.assertTrue(any(f"linedef:{line_id}" in message or str(line_id) in message for _, _, _, _, line_id, _ in source))
        return
    emitted = _emitted_edges(loops)
    dropped = [edge for edge in source if edge not in emitted]
    extra = [edge for edge in emitted if edge not in source]
    test.assertEqual(
        dropped, [],
        msg=f"lossy success is not allowed; dropped {dropped} warnings={loops.warnings}",
    )
    test.assertEqual(extra, [], msg=f"duplicated or invented edges {extra}")
    test.assertEqual(len(emitted), len(source))
    test.assertFalse(
        any("disconnected extra outer" in item for item in loops.warnings),
        msg="a warning plus successful lossy output is not acceptable",
    )


class DisconnectedComponentTests(unittest.TestCase):
    def test_two_disconnected_squares_preserve_all_eight_edges_or_fail_closed(self):
        level = _disconnected_two_squares()
        source = _source_directed_edges(level, 0)
        self.assertEqual(len(source), 8)
        _assert_conserved_or_typed_failure(self, level, 0)
        try:
            ir = new_level()
            report = lower_doom_geometry(level, ir=ir)
        except DoomGeometryError as exc:
            self.assertIn("sector:0", str(exc))
            return
        lossy_warnings = [
            item for item in report.get("warnings", [])
            if "disconnected extra outer" in str(item.get("message", item))
        ]
        self.assertFalse(lossy_warnings, msg=f"lossy warnings on success: {lossy_warnings}")
        self.assertEqual(len(ir.walls), 8)
        self.assertEqual(ir.sectors[0]["fields"]["wall_count"], 8)

    def test_conversion_cannot_succeed_with_four_walls_from_eight_edges(self):
        level = _disconnected_two_squares()
        try:
            blood, report = convert_doom_to_blood(level)
        except (DoomGeometryError, DoomConversionError) as exc:
            self.assertIn("sector:0", str(exc))
            return
        self.assertEqual(len(blood.walls), 8)
        self.assertNotEqual(len(blood.walls), 4)


class LinedefPermutationTests(unittest.TestCase):
    def test_touching_loop_permutations_share_canonical_topology(self):
        signatures = []
        outcomes = []
        for order in ("ab", "ba", "interleaved"):
            level = _touching_two_squares(order)
            source = _source_directed_edges(level, 0)
            self.assertEqual(len(source), 8)
            try:
                ir = new_level()
                report = lower_doom_geometry(level, ir=ir)
                loops = extract_sector_loops(level, 0)
            except DoomGeometryError:
                outcomes.append("error")
                signatures.append(None)
                continue
            outcomes.append("ok")
            conservation = {
                "source": Counter(source),
                "emitted": Counter(_emitted_edges(loops)),
            }
            self.assertEqual(conservation["source"], conservation["emitted"], msg=order)
            signatures.append({
                "extract": {
                    "directed_edge_multiset": Counter(
                        (x1, y1, x2, y2) for x1, y1, x2, y2, _linedef, _side in
                        _canonical_loops_from_extract(loops)["directed_edge_multiset"].elements()
                    ),
                    "boundary_components": tuple(
                        tuple((x1, y1, x2, y2) for x1, y1, x2, y2, _linedef, _side in component)
                        for component in _canonical_loops_from_extract(loops)["boundary_components"]
                    ),
                },
                "ir": _canonical_from_ir(ir),
                "topology": canonical_topology(ir),
                "portals": report.get("portals"),
                "sector_map": report.get("sector_map"),
                "conservation": (
                    loops.conservation.to_dict() if getattr(loops, "conservation", None) else None
                ),
            })
        self.assertEqual(len(set(outcomes)), 1, msg=f"permutation outcomes diverged: {outcomes}")
        if outcomes[0] == "ok":
            first = signatures[0]
            for other in signatures[1:]:
                self.assertEqual(other["extract"]["directed_edge_multiset"], first["extract"]["directed_edge_multiset"])
                self.assertEqual(other["extract"]["boundary_components"], first["extract"]["boundary_components"])
                self.assertEqual(other["topology"]["directed_edge_multiset"], first["topology"]["directed_edge_multiset"])
                self.assertEqual(other["topology"]["boundary_components"], first["topology"]["boundary_components"])
                self.assertEqual(other["topology"]["portal_pairings"], first["topology"]["portal_pairings"])
                self.assertEqual(other["topology"]["sector_ownership"], first["topology"]["sector_ownership"])
                self.assertEqual(other["conservation"], first["conservation"])


class GeometryEdgeCaseTests(unittest.TestCase):
    def test_nested_outer_and_hole_keeps_eight_edges(self):
        level = _nested_hole()
        source = _source_directed_edges(level, 0)
        self.assertEqual(len(source), 8)
        loops = extract_sector_loops(level, 0)
        emitted = _emitted_edges(loops)
        self.assertEqual(len(emitted), 8)
        self.assertEqual(len(loops.holes), 1)
        self.assertEqual(len(loops.outer), 4)
        self.assertEqual(len(loops.holes[0]), 4)

    def test_multiple_disconnected_components_are_not_silently_lossy(self):
        vertices = _square((0, 0)) + _square((128, 0)) + _square((256, 0))
        lines = (
            _clockwise_square_lines(0, 0)
            + _clockwise_square_lines(4, 0)
            + _clockwise_square_lines(8, 0)
        )
        level = assemble_doom("MAP01", vertices, lines, [_sector()], [DoomThing(32, 32, 0, 1, 7)])
        _assert_conserved_or_typed_failure(self, level, 0)

    def test_touching_components_are_conserved(self):
        _assert_conserved_or_typed_failure(self, _touching_two_squares("ab"), 0)

    def test_ambiguous_vertex_is_reported_or_resolved_geometrically(self):
        level = _touching_two_squares("ab")
        try:
            loops = extract_sector_loops(level, 0)
        except DoomGeometryError as exc:
            self.assertIn("sector:0", str(exc))
            return
        messages = " ".join(loops.warnings)
        if "multiple unused outgoing" in messages or "ambiguous" in messages.lower():
            self.assertEqual(len(_emitted_edges(loops)), 8)
            return
        self.assertEqual(len(_emitted_edges(loops)), 8)

    def test_self_referencing_linedef_is_not_silently_dropped(self):
        vertices = _square((0, 0), 192) + [(64, 64), (128, 64)]
        lines = _clockwise_square_lines(0, 0) + [(4, 5, 0, 0)]
        level = assemble_doom("MAP01", vertices, lines, [_sector()], [DoomThing(32, 32, 0, 1, 7)])
        source = _source_directed_edges(level, 0)
        self.assertEqual(len(source), 6)
        try:
            loops = extract_sector_loops(level, 0)
        except DoomGeometryError as exc:
            self.assertIn("sector:0", str(exc))
            self.assertTrue("linedef:4" in str(exc) or "self-referenc" in str(exc).lower())
            return
        emitted = _emitted_edges(loops)
        self.assertEqual(len(emitted), 6)

    def test_open_chain_fails_closed(self):
        vertices = [(0, 0), (64, 0), (64, 64), (0, 64)]
        lines = [(0, 1, 0, None), (1, 2, 0, None), (2, 3, 0, None)]
        level = assemble_doom("MAP01", vertices, lines, [_sector()], [DoomThing(16, 16, 0, 1, 7)])
        with self.assertRaises(DoomGeometryError) as raised:
            extract_sector_loops(level, 0)
        self.assertIn("sector:0", str(raised.exception))
        self.assertTrue(any(token in str(raised.exception) for token in ("linedef:0", "linedef:1", "linedef:2")))

    def test_reversed_sidedef_ownership_still_owns_the_named_sector(self):
        vertices = _square((0, 0), 128) + _square((128, 0), 128)
        lines = [
            (0, 3, 0, None), (3, 2, 0, None), (2, 1, 0, 1), (1, 0, 0, None),
            (4, 1, 1, None), (2, 5, 1, None), (5, 4, 1, None),
        ]
        level = assemble_doom(
            "MAP01", vertices, lines, [_sector(), _sector()], [DoomThing(32, 32, 0, 1, 7)],
        )
        shared = level.linedefs[2]
        shared.side_front, shared.side_back = shared.side_back, shared.side_front
        source_0 = _source_directed_edges(level, 0)
        source_1 = _source_directed_edges(level, 1)
        self.assertGreaterEqual(len(source_0), 3)
        self.assertGreaterEqual(len(source_1), 3)
        try:
            loops_0 = extract_sector_loops(level, 0)
            loops_1 = extract_sector_loops(level, 1)
        except DoomGeometryError:
            return
        self.assertEqual(len(_emitted_edges(loops_0)), len(source_0))
        self.assertEqual(len(_emitted_edges(loops_1)), len(source_1))

    def test_zero_length_edge_fails_closed(self):
        vertices = [(0, 0), (64, 0), (64, 64), (0, 64), (32, 32)]
        lines = _clockwise_square_lines(0, 0) + [(4, 4, 0, None)]
        level = assemble_doom("MAP01", vertices, lines, [_sector()], [DoomThing(16, 16, 0, 1, 7)])
        with self.assertRaises(DoomGeometryError) as raised:
            extract_sector_loops(level, 0)
        self.assertIn("sector:0", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
