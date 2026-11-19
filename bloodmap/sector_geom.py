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
from .planar_geom import area2, point_in_loop

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

    The outline and every hole come out separately, in wall order, which is
    what stops a carved hole from reading as part of the floor or as an
    overlap with whatever fills it. Wall order is NOT outline-first: ask
    `outline_and_holes` for which is which. A loop of fewer than three points
    is dropped.
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


def outline_and_holes(level: Any, sector_id: int) -> tuple[list[Point], list[list[Point]]]:
    """A sector's outline and the holes cut in it.

    The outline is the loop of greatest area, not the first one. Build does
    not promise that the outer loop owns the lowest wall index: BB4 sector 41
    traces a hole of 1,048,576 before an outline of 22,077,276, E1M2 has
    twenty-five such sectors, and a reader that takes `sector_loops(...)[0]`
    for the outline accepts points that stand in solid space.
    """
    loops = sorted(sector_loops(level, sector_id), key=lambda loop: abs(area2(loop)),
                   reverse=True)
    if not loops:
        return [], []
    return loops[0], loops[1:]


def sector_contains(level: Any, sector_id: int, x: int, y: int) -> bool:
    """Is this point in the sector: in or on its outline, and in no hole.

    A point on the edge of a hole counts as in the sector; a point inside one
    does not, which is what keeps a camera out of a carved lamp base.
    """
    outline, holes = outline_and_holes(level, sector_id)
    if not outline or point_in_loop((x, y), outline) == 0:
        return False
    return all(point_in_loop((x, y), hole) != 1 for hole in holes)


def sector_at(level: Any, x: int, y: int, *,
              floor_near: int | None = None) -> int | None:
    """The sector at a point in plan, or None.

    Space is stacked: a sewer runs under a street and a roof stands over a
    nave, so a point can lie in several sectors. `floor_near` picks the one
    whose floor is nearest that z -- the level a person there would be
    standing on. Without it the first sector in map order is returned, which
    is right only for a map that does not overlap itself: the day a church got
    a roof, every pose inside it rendered the rooftop.
    """
    hits = [sector_id for sector_id in range(len(level.sectors))
            if sector_contains(level, sector_id, x, y)]
    if not hits:
        return None
    if floor_near is None:
        return hits[0]
    return min(hits, key=lambda sector_id: abs(
        int(record_fields(level.sectors[sector_id])["floor_z"]) - floor_near))
