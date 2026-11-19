"""A sector's walls, read off any map: who owns a wall, its loops, its segment.

Three things every sensor needs before it can measure anything. Each was
written once per module that needed it -- `wall_owners` thirteen times across
the library and the tools, the loop tracer six -- and the copies had begun to
differ in what they did with a malformed run. They are here once.

Everything takes a map with `sectors` and `walls` and works on a `DiskMap`
and a `LevelIR` alike (`model.record_fields`). Nothing here validates: a wall
range that runs off the end of the wall list is clamped, and a wall two
sectors both claim goes to the later one. Whether a map is well formed is
`analysis.validate_map`'s question, and `composition._wall_owners` and
`semantics._wall_owners` are the strict readers that raise.

One copy is kept on purpose: `render_slots.wall_owners`. That module is a
transcription of the engine's wall pass and imports nothing from the package,
so it stays citable on a hand-built map (`tests/test_architecture.py`).

Pure point-list geometry -- area, containment, intersection -- is
`planar_geom`; a derived view over many sectors (adjacency, portals) is
`spatial` for a `BuildIR` and `reachability` for a `DiskMap`.
"""

from __future__ import annotations

from math import hypot
from typing import Any

from .model import record_fields

Point = tuple[int, int]


def sector_walls(level: Any, sector_id: int) -> range:
    """The wall indices of one sector's run, clamped to the walls that exist."""
    fields = record_fields(level.sectors[sector_id])
    first = int(fields["wall_ptr"])
    return range(first, min(first + int(fields["wall_count"]), len(level.walls)))


def wall_owners(level: Any) -> dict[int, int]:
    """Wall index -> the sector whose run it belongs to."""
    owners: dict[int, int] = {}
    for sector_id in range(len(level.sectors)):
        for wall_id in sector_walls(level, sector_id):
            owners[wall_id] = sector_id
    return owners


def sector_loops(level: Any, sector_id: int) -> list[list[Point]]:
    """One sector's wall run split into closed loops, following `point2`.

    The outer loop and every inner one come out separately, in wall order,
    which is what stops a carved hole from reading as part of the floor or as
    an overlap with whatever fills it. A loop of fewer than three points is
    dropped.
    """
    run = sector_walls(level, sector_id)
    loops: list[list[Point]] = []
    seen: set[int] = set()
    for start in run:
        if start in seen:
            continue
        loop: list[Point] = []
        walk = start
        while walk not in seen and walk in run:
            seen.add(walk)
            wall = record_fields(level.walls[walk])
            loop.append((int(wall["x"]), int(wall["y"])))
            walk = int(wall["point2"])
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def wall_segment(level: Any, wall_id: int) -> tuple[Point, Point]:
    """A wall's two ends: its own point, and the point of the wall it leads to."""
    wall = record_fields(level.walls[wall_id])
    following = record_fields(level.walls[int(wall["point2"])])
    return ((int(wall["x"]), int(wall["y"])),
            (int(following["x"]), int(following["y"])))


def wall_length(level: Any, wall_id: int) -> float:
    (ax, ay), (bx, by) = wall_segment(level, wall_id)
    return hypot(bx - ax, by - ay)
