"""Hierarchy-aware viewpoint planning.

The renderer draws whatever pose it is handed.  Deciding which poses are worth
rendering needs the hierarchy, the geometry and the player profile, all of
which live here, so the planning lives here too.

A plan is deterministic: the same level and the same node produce the same
poses, so two observations of the same place are comparable and a source edit
shows up as a change in what is visible rather than as a change in where the
camera stood.

Poses that geometry already rules out are dropped here with a reason.  The
observer checks again and refuses rather than nudging a camera; both ends
declining is deliberate, because a silently moved camera answers a question
nobody asked.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .model import LevelIR
from .planar_geom import point_in_loop
from .player_space import player_profile
from .viewpoints import ViewpointError, _contains, _sector_loops
from .visual import SourceMap, Viewpoint

#: What a planned pose is for.  Deliberately small: every purpose here answers
#: a question an author actually asks about a part of a level.
PURPOSES = (
    "room_center",        # what is this place
    "room_entry",         # what do I see arriving
    "room_reverse",       # what do I see leaving
    "toward_child",       # how does the thing inside sit in its host
    "connection_before",  # what does the opening promise
    "connection_after",   # what does it deliver
    "structure_foot",     # from the bottom of a rise
    "structure_head",     # from the top of a rise
    "area_overview",      # the widest read of a group
)


class ViewPlanError(ValueError):
    pass


@dataclass(frozen=True)
class Pose:
    x: int
    y: int
    z: int
    angle: int
    sector: int


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _area_and_centroid(loop: Sequence[tuple[int, int]]) -> tuple[float, tuple[float, float]]:
    twice = 0.0
    cx = 0.0
    cy = 0.0
    for index, (x1, y1) in enumerate(loop):
        x2, y2 = loop[(index + 1) % len(loop)]
        cross = x1 * y2 - x2 * y1
        twice += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if twice == 0:
        xs = [p[0] for p in loop]
        ys = [p[1] for p in loop]
        return 0.0, (sum(xs) / len(xs), sum(ys) / len(ys))
    return abs(twice) / 2.0, (cx / (3 * twice), cy / (3 * twice))


def sector_area(level: LevelIR, sector_id: int) -> float:
    try:
        loops = _sector_loops(level, sector_id)
    except ViewpointError:
        return 0.0
    outer, holes = loops[0], loops[1:]
    area, _ = _area_and_centroid(outer)
    for hole in holes:
        hole_area, _ = _area_and_centroid(hole)
        area -= hole_area
    return max(area, 0.0)


def interior_point(level: LevelIR, sector_id: int) -> tuple[int, int] | None:
    """A point that really is inside, centroid first and a sampled grid after.

    A centroid is outside its own sector often enough -- L-shapes, courtyards
    with a building in the middle -- that trusting it produces poses the
    renderer then refuses.
    """
    try:
        loops = _sector_loops(level, sector_id)
    except ViewpointError:
        return None
    outer = loops[0]
    _, (cx, cy) = _area_and_centroid(outer)
    candidate = (int(round(cx)), int(round(cy)))
    if _contains(level, sector_id, *candidate):
        return candidate

    xs = [p[0] for p in outer]
    ys = [p[1] for p in outer]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    best: tuple[float, tuple[int, int]] | None = None
    steps = 9
    for i in range(1, steps):
        for j in range(1, steps):
            x = int(round(lo_x + (hi_x - lo_x) * i / steps))
            y = int(round(lo_y + (hi_y - lo_y) * j / steps))
            if not _contains(level, sector_id, x, y):
                continue
            clearance = min(
                _distance_to_loop((x, y), loop) for loop in loops
            )
            if best is None or clearance > best[0]:
                best = (clearance, (x, y))
    return best[1] if best else None


def _distance_to_loop(point: tuple[int, int], loop: Sequence[tuple[int, int]]) -> float:
    px, py = point
    best = math.inf
    for index, (x1, y1) in enumerate(loop):
        x2, y2 = loop[(index + 1) % len(loop)]
        dx, dy = x2 - x1, y2 - y1
        span = dx * dx + dy * dy
        if span == 0:
            best = min(best, math.hypot(px - x1, py - y1))
            continue
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / span))
        best = min(best, math.hypot(px - (x1 + t * dx), py - (y1 + t * dy)))
    return best


def eye_z(level: LevelIR, sector_id: int, *, profile: str = "blood") -> int | None:
    """Standing eye height, or None where the player could not stand at all."""
    fields = level.sectors[sector_id]["fields"]
    floor_z, ceiling_z = int(fields["floor_z"]), int(fields["ceiling_z"])
    clear = floor_z - ceiling_z
    if clear <= 512:
        return None
    stand = player_profile(profile).standing_height
    eye = min(int(stand * 0.9), clear // 2)
    return floor_z - max(eye, 256)


def angle_toward(origin: tuple[float, float], target: tuple[float, float]) -> int:
    """Build angle units: 0 is +x, 512 is +y, and screen y grows downward."""
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    if dx == 0 and dy == 0:
        return 0
    return int(round(math.atan2(dy, dx) * 1024.0 / math.pi)) & 2047


def portals_of(level: LevelIR, sector_id: int) -> list[dict[str, Any]]:
    """Two-sided walls out of a sector, widest first."""
    fields = level.sectors[sector_id]["fields"]
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    result: list[dict[str, Any]] = []
    for index in range(start, min(start + count, len(level.walls))):
        wall = level.walls[index]["fields"]
        neighbour = int(wall["next_sector"])
        if neighbour < 0:
            continue
        a = (int(wall["x"]), int(wall["y"]))
        point2 = int(wall["point2"])
        if not 0 <= point2 < len(level.walls):
            continue
        b_fields = level.walls[point2]["fields"]
        b = (int(b_fields["x"]), int(b_fields["y"]))
        result.append({
            "wall": index,
            "neighbour": neighbour,
            "a": a,
            "b": b,
            "midpoint": ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0),
            "width": math.hypot(b[0] - a[0], b[1] - a[1]),
        })
    result.sort(key=lambda item: -item["width"])
    return result


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def _representative_sector(level: LevelIR, sectors: Iterable[int]) -> int | None:
    ranked = sorted(((sector_area(level, s), s) for s in sectors), reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] > 0 else None


def _pose(level: LevelIR, sector_id: int, at: tuple[int, int], facing: tuple[float, float],
          *, profile: str) -> Pose | None:
    z = eye_z(level, sector_id, profile=profile)
    if z is None:
        return None
    if not _contains(level, sector_id, at[0], at[1]):
        return None
    return Pose(at[0], at[1], z, angle_toward((at[0], at[1]), facing), sector_id)


def _step_inside(point: tuple[float, float], toward: tuple[float, float], step: float) -> tuple[int, int]:
    dx = toward[0] - point[0]
    dy = toward[1] - point[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return (int(round(point[0])), int(round(point[1])))
    return (int(round(point[0] + dx / length * step)),
            int(round(point[1] + dy / length * step)))


def plan_node_views(level: LevelIR, source_map: SourceMap, node: str, *,
                    profile: str = "blood", include: Sequence[str] = PURPOSES,
                    child_nodes: Sequence[str] = ()) -> list[Viewpoint]:
    """Poses that answer: what is this place, how is it entered, what is inside it."""
    allocation = source_map.allocations.get(node)
    if allocation is None:
        raise ViewPlanError(f"{node!r} owns no native geometry in this source map")
    sectors = sorted(allocation.sectors)
    home = _representative_sector(level, sectors)
    if home is None:
        return []
    centre = interior_point(level, home)
    if centre is None:
        return []
    unit = player_profile(profile).body_width

    views: list[Viewpoint] = []
    portals = [p for p in portals_of(level, home) if p["neighbour"] not in allocation.sectors]
    biggest = portals[0] if portals else None

    if "room_center" in include:
        facing = biggest["midpoint"] if biggest else _far_corner(level, home, centre)
        pose = _pose(level, home, centre, facing, profile=profile)
        if pose:
            views.append(_viewpoint(f"{_slug(node)}__center", pose, node, "room_center",
                                    note="centre of the largest sector, facing its widest opening"))

    if "room_entry" in include and biggest is not None:
        inside = _step_inside(biggest["midpoint"], centre, unit * 1.2)
        pose = _pose(level, home, inside, centre, profile=profile)
        if pose:
            views.append(_viewpoint(f"{_slug(node)}__entry", pose, node, "room_entry",
                                    note="one and a bit player widths inside the widest opening"))

    if "room_reverse" in include and biggest is not None:
        pose = _pose(level, home, centre, biggest["midpoint"], profile=profile)
        if pose and not any(v.purpose == "room_center" and v.angle == pose.angle for v in views):
            views.append(_viewpoint(f"{_slug(node)}__toward_entry", pose, node, "room_reverse",
                                    note="from the centre back toward the widest opening"))

    if "toward_child" in include:
        for child in child_nodes:
            child_alloc = source_map.allocations.get(child)
            if child_alloc is None:
                continue
            target = _representative_sector(level, child_alloc.sectors)
            if target is None:
                continue
            aim = interior_point(level, target)
            if aim is None:
                continue
            pose = _pose(level, home, centre, aim, profile=profile)
            if pose:
                views.append(_viewpoint(
                    f"{_slug(node)}__toward__{_slug(child)}", pose, node, "toward_child",
                    note=f"from {node} toward {child}",
                ))
    return views


def _far_corner(level: LevelIR, sector_id: int, origin: tuple[int, int]) -> tuple[float, float]:
    loops = _sector_loops(level, sector_id)
    best = max(loops[0], key=lambda p: math.hypot(p[0] - origin[0], p[1] - origin[1]))
    return (float(best[0]), float(best[1]))


def plan_connection_views(level: LevelIR, source_map: SourceMap, *,
                          wall: int, profile: str = "blood",
                          label: str | None = None) -> list[Viewpoint]:
    """Approach, and what the crossing delivers, for one two-sided wall."""
    if not 0 <= wall < len(level.walls):
        raise ViewPlanError(f"wall {wall} is not in this level")
    fields = level.walls[wall]["fields"]
    far = int(fields["next_sector"])
    if far < 0:
        raise ViewPlanError(f"wall {wall} is not a portal")
    near = _sector_of_wall(level, wall)
    if near is None:
        return []
    a = (int(fields["x"]), int(fields["y"]))
    b_fields = level.walls[int(fields["point2"])]["fields"]
    b = (int(b_fields["x"]), int(b_fields["y"]))
    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)

    unit = player_profile(profile).body_width
    near_in = interior_point(level, near)
    far_in = interior_point(level, far)
    name = label or f"wall{wall}"
    views: list[Viewpoint] = []

    if near_in is not None:
        at = _step_inside(mid, near_in, unit * 2.0)
        pose = _pose(level, near, at, mid, profile=profile)
        if pose:
            views.append(_viewpoint(f"{_slug(name)}__before", pose,
                                    source_map.sector_owner.get(near, ""),
                                    "connection_before",
                                    note="two player widths back on the near side"))
    if far_in is not None:
        at = _step_inside(mid, far_in, unit * 1.2)
        pose = _pose(level, far, at, far_in, profile=profile)
        if pose:
            views.append(_viewpoint(f"{_slug(name)}__after", pose,
                                    source_map.sector_owner.get(far, ""),
                                    "connection_after",
                                    note="just across, facing on"))
    return views


def _sector_of_wall(level: LevelIR, wall: int) -> int | None:
    for sector in level.sectors:
        fields = sector["fields"]
        start = int(fields["wall_ptr"])
        if start <= wall < start + int(fields["wall_count"]):
            return int(sector["id"])
    return None


def plan_structure_views(level: LevelIR, source_map: SourceMap, node: str, *,
                         profile: str = "blood") -> list[Viewpoint]:
    """Foot and head of a vertical run, which is where a stair reads or does not."""
    allocation = source_map.allocations.get(node)
    if allocation is None or not allocation.sectors:
        return []
    ranked = sorted(
        allocation.sectors,
        key=lambda s: int(level.sectors[s]["fields"]["floor_z"]),
    )
    low, high = ranked[-1], ranked[0]    # floor_z grows downward in Build
    if low == high:
        return []
    low_at = interior_point(level, low)
    high_at = interior_point(level, high)
    if low_at is None or high_at is None:
        return []
    views: list[Viewpoint] = []
    pose = _pose(level, low, low_at, high_at, profile=profile)
    if pose:
        views.append(_viewpoint(f"{_slug(node)}__foot", pose, node, "structure_foot",
                                note="from the bottom of the run, looking up it"))
    pose = _pose(level, high, high_at, low_at, profile=profile)
    if pose:
        views.append(_viewpoint(f"{_slug(node)}__head", pose, node, "structure_head",
                                note="from the top of the run, looking back down"))
    return views


def plan_level_views(level: LevelIR, source_map: SourceMap, *,
                     nodes: Sequence[str] | None = None,
                     profile: str = "blood",
                     include: Sequence[str] = ("room_center", "room_entry"),
                     children_of: Mapping[str, Sequence[str]] | None = None,
                     limit: int | None = None) -> list[Viewpoint]:
    """A bounded plan over a set of nodes, in a stable order."""
    chosen = list(nodes) if nodes is not None else sorted(source_map.allocations)
    children_of = children_of or {}
    planned: list[Viewpoint] = []
    for node in chosen:
        try:
            planned.extend(plan_node_views(
                level, source_map, node, profile=profile, include=include,
                child_nodes=children_of.get(node, ()),
            ))
        except ViewPlanError:
            continue
        if limit is not None and len(planned) >= limit:
            return planned[:limit]
    return planned


def _viewpoint(view_id: str, pose: Pose, node: str, purpose: str, *, note: str = "") -> Viewpoint:
    return Viewpoint(
        view_id=view_id, x=pose.x, y=pose.y, z=pose.z, angle=pose.angle,
        sector=pose.sector, node=node, purpose=purpose, note=note,
    )


def _slug(text: str) -> str:
    out = []
    for ch in text:
        out.append(ch if ch.isalnum() else "_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "view"


__all__ = [
    "PURPOSES", "ViewPlanError", "Pose",
    "sector_area", "interior_point", "eye_z", "angle_toward", "portals_of",
    "plan_node_views", "plan_connection_views", "plan_structure_views", "plan_level_views",
]
