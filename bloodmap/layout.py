"""Sizing along an axis, so that inserting a part does not require arithmetic.

The fault
---------

Thin walls are a *sizing* fault wearing positioning clothes. A layout written as
global coordinates has no owner for the space between its parts: extend a
corridor by 512 and the room beyond it does not move, so the mass separating
them silently loses 512 units. Nothing complains, because nothing was ever told
that the mass was a thing. The path of least resistance -- nudge the number that
is easiest to reach -- produces walls four units thick, and Build draws them.

The fix is to say which part absorbs change. A run along an axis is a sequence
of parts, each either **fixed** (a door leaf, an alcove, a stair, a wall: things
with intrinsic size) or **flexible** (a corridor, a court: things whose job is to
be however long the rest leaves them). Inserting a fixed part shrinks the
flexible one. Shrinking it past its minimum is a compile error that names what no
longer fits.

This is one-directional propagation along one axis, and deliberately nothing
more. A general constraint solver fails unreadably when over- or
under-constrained, which is the opposite of what this is for: the whole value is
that the error message says *"the cloister walk cannot go below 3 body widths;
the chapel you just inserted needs 1536 and there are only 900 spare"*.

What the campaign says about walls
----------------------------------

``knowledge/blood/design/wall-thickness-v1.json``, from all 43 campaign maps:
51,521 probes stepping outward from every solid wall of a playable sector to the
next playable sector that shares its height range.

===================  =========
thinner than          share
===================  =========
64 units (0.17 bw)      1.38%
128 units (0.33 bw)     2.84%
192 units (0.50 bw)     6.37%
256 units (0.67 bw)     8.59%
===================  =========

The histogram is modal on multiples of 128 -- 128, 256, 384, and a large tail at
512 and beyond -- which is the grid Blood's masonry is actually built on.
`MIN_WALL` is 128 because that is where the campaign's own distribution begins;
below it a wall has to be *named*, the same move the aperture grammar makes for a
monumental leaf, so that the exception is visible in the source instead of being
whatever the arithmetic left over.

A note on what was excluded, because it changed the answer: a first pass put
16.8% of probes at 16 units and every map's thinnest wall at 16. Those were
room-over-room stacks -- two sectors sharing a footprint at different heights,
which nothing separates horizontally because nothing is meant to. Only volumes
whose floor-to-ceiling ranges overlap by a standing body are separated by a wall.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .planar_geom import point_in_loop
from .player_space import PLAYER_PROFILES
from .reachability import design_sectors
from .sector_geom import outline_and_holes

PLAYER_WIDTH = PLAYER_PROFILES["blood"].body_width

#: The thinnest mass this compiler will put between two rooms without being told
#: to. Derived from the campaign: 2.84% of Blood's own walls are thinner, and its
#: histogram's first mode sits here.
MIN_WALL = 128

#: What a wall thinner than `MIN_WALL` has to be called. Blood builds all of
#: these; what it does not do is arrive at one by accident.
THIN_WALL_NAMES = ("fake_wall", "hidden_door", "screen", "grate")


class LayoutError(ValueError):
    """A run that cannot be resolved, always naming what does not fit."""


@dataclass(frozen=True)
class Part:
    """One element of a run. Use `Fixed`, `Flex` or `Wall`."""

    name: str

    @property
    def minimum(self) -> int:
        raise NotImplementedError

    @property
    def flexible(self) -> bool:
        return False


@dataclass(frozen=True)
class Fixed(Part):
    """A part with intrinsic size: a door leaf, an alcove, a stair.

    Its extent is a property of what it *is*, so the run may not change it. If
    the run is too short, something else gives or the run is too short -- the one
    thing that must not happen is this quietly becoming smaller than the thing it
    represents.
    """

    extent: int = 0

    def __post_init__(self) -> None:
        if self.extent <= 0:
            raise LayoutError(
                "%s: a fixed part needs a positive extent; got %d"
                % (self.name, self.extent))

    @property
    def minimum(self) -> int:
        return self.extent


@dataclass(frozen=True)
class Wall(Fixed):
    """The mass between two parts, which is a part in its own right.

    This is the whole point of the module. A wall that is not represented is a
    wall that absorbs every rounding error in the layout, and the campaign says
    Blood's own masonry is 128 units thick at the thin end.
    """

    #: Set to one of `THIN_WALL_NAMES` to build below `MIN_WALL` on purpose.
    thin_because: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.extent >= MIN_WALL:
            return
        if self.thin_because is None:
            raise LayoutError(
                "%s: a wall %d units thick (%.2f body widths) is thinner than "
                "anything this compiler builds unasked. Blood goes below %d "
                "units on 2.84%% of its walls, and always because it means "
                "something.\n"
                "  If this one is meant to be thin, say why: "
                "thin_because='fake_wall' (or %s).\n"
                "  If it is not, it is the residue of a squeeze -- give the run "
                "a Flex part to absorb the change instead."
                % (self.name, self.extent, self.extent / PLAYER_WIDTH, MIN_WALL,
                   ", ".join(repr(n) for n in THIN_WALL_NAMES[1:])))
        if self.thin_because not in THIN_WALL_NAMES:
            raise LayoutError(
                "%s: %r is not a reason a wall is thin. Use one of: %s"
                % (self.name, self.thin_because, ", ".join(THIN_WALL_NAMES)))


@dataclass(frozen=True)
class Flex(Part):
    """A part whose job is to be whatever the rest of the run leaves it.

    `low` is the point below which it stops being itself: a cloister walk narrower
    than a body and a half is not a walk. `weight` shares the residual when a run
    has more than one flexible part.
    """

    low: int = PLAYER_WIDTH
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.low <= 0:
            raise LayoutError(
                "%s: a flexible part needs a positive minimum -- otherwise it "
                "absorbs a squeeze all the way to nothing and the error the "
                "minimum exists to raise never fires." % self.name)
        if self.weight <= 0:
            raise LayoutError("%s: weight must be positive" % self.name)

    @property
    def minimum(self) -> int:
        return self.low

    @property
    def flexible(self) -> bool:
        return True


@dataclass(frozen=True)
class Placed:
    """Where a part ended up along the run."""

    name: str
    offset: int
    extent: int
    flexible: bool

    @property
    def end(self) -> int:
        return self.offset + self.extent


@dataclass(frozen=True)
class Run:
    """A sequence of parts sharing one axis, resolved to offsets and extents.

    `total` is the span the run has to fill. Fixed parts keep their extents;
    flexible parts divide what is left, by weight, and never go below their own
    minimum.
    """

    id: str
    parts: tuple[Part, ...]
    total: int

    def __post_init__(self) -> None:
        if not self.parts:
            raise LayoutError("%s: a run needs at least one part" % self.id)
        seen: set[str] = set()
        for part in self.parts:
            if part.name in seen:
                raise LayoutError(
                    "%s: two parts are both called %r; a run's parts are "
                    "addressed by name" % (self.id, part.name))
            seen.add(part.name)

    def resolve(self) -> list[Placed]:
        fixed = sum(p.extent for p in self.parts if isinstance(p, Fixed))
        flexes = [p for p in self.parts if p.flexible]
        floor = sum(p.minimum for p in flexes)

        if not flexes:
            if fixed != self.total:
                raise LayoutError(
                    "%s: the parts add up to %d but the run is %d. With no "
                    "flexible part there is nothing to absorb the difference -- "
                    "mark one of %s as Flex, or change the run's total."
                    % (self.id, fixed, self.total,
                       ", ".join(repr(p.name) for p in self.parts)))
            spare = 0
        else:
            spare = self.total - fixed - floor
            if spare < 0:
                short = -spare
                raise LayoutError(
                    "%s: %d units short.\n"
                    "  the run is %d units long\n"
                    "  fixed parts need %d: %s\n"
                    "  flexible parts cannot go below %d: %s\n"
                    "  Either lengthen the run by %d, or take %d out of the "
                    "fixed parts. Shrinking the flexible parts further is what "
                    "this error exists to prevent."
                    % (self.id, short, self.total, fixed,
                       ", ".join("%s=%d" % (p.name, p.extent)
                                 for p in self.parts if isinstance(p, Fixed)) or "none",
                       floor,
                       ", ".join("%s>=%d" % (p.name, p.minimum) for p in flexes),
                       short, short))

        # Hand out the residual by weight, giving the remainder to the last
        # flexible part so the run's total is exact rather than nearly right.
        share: dict[str, int] = {}
        if flexes:
            weight = sum(p.weight for p in flexes)
            running = 0
            for part in flexes[:-1]:
                take = int(spare * part.weight / weight)
                share[part.name] = part.minimum + take
                running += take
            share[flexes[-1].name] = flexes[-1].minimum + (spare - running)

        placed = []
        offset = 0
        for part in self.parts:
            extent = share[part.name] if part.flexible else part.extent
            placed.append(Placed(part.name, offset, extent, part.flexible))
            offset += extent
        return placed

    def at(self, name: str) -> Placed:
        for placed in self.resolve():
            if placed.name == name:
                return placed
        raise LayoutError(
            "%s has no part called %r; it has %s"
            % (self.id, name, ", ".join(repr(p.name) for p in self.parts)))


def run(run_id: str, *parts: Part, total: int) -> Run:
    """Build a run. Reads as a sentence: fixed, flex, fixed."""
    return Run(run_id, tuple(parts), int(total))


def wall_between(name: str, extent: int, *, thin_because: str | None = None) -> Wall:
    return Wall(name=name, extent=int(extent), thin_because=thin_because)


def check_thickness(extent: int, *, what: str = "wall") -> None:
    """Raise unless `extent` is a thickness this compiler will build unasked.

    For callers that are not building a `Run` but still want the grammar's floor
    -- the planar compiler's own squeeze check, for instance.
    """
    Wall(name=what, extent=int(extent))


# ---------------------------------------------------------------------------
# Reading wall thickness back off a map
# ---------------------------------------------------------------------------
#
# The sensor `MIN_WALL` was measured with, and the one the thin-wall rule in
# `rules_blood.py` reads a built map through. It lived in
# `tools/mine_wall_thickness.py`, which is now its corpus run.

#: How far out to look, and how finely. 2048 is five and a bit body widths --
#: past that a mass is not a wall you might accidentally make thin.
PROBE_REACH = 2048
PROBE_STEP = 16

#: Sample the wall at these fractions of its length. A wall is thin where it is
#: thin, and only sampling the midpoint misses a wedge.
PROBE_SAMPLES = (0.25, 0.5, 0.75)

#: Walls shorter than this are chamfers and joins, not surfaces a player reads.
PROBE_MIN_WALL_LENGTH = 128

#: How much vertical overlap makes two sectors neighbours rather than stacked.
#: A standing body: if a player in one could stand at heights the other also
#: spans, the mass between them is a wall they can both see.
COEXIST_HEIGHT = PLAYER_PROFILES["blood"].standing_height

_CELL = 1024


def _index_sectors(disk: Any, playable: frozenset[int]) -> tuple[dict, dict]:
    """Bucket playable sectors by grid cell, and keep their loops.

    Outline first, then the holes. The wall run does not come that way: 514
    of the campaign's 867 sectors with holes trace a hole before the outline,
    and until 2026-11-19 this kept the run's order, so `_sector_at` tested
    those sectors against a hole and never found them.
    """
    loops = {}
    for s in playable:
        outline, holes = outline_and_holes(disk, s)
        loops[s] = [outline, *holes] if outline else []
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for sector, sector_loop in loops.items():
        if not sector_loop:
            continue
        xs = [p[0] for loop in sector_loop for p in loop]
        ys = [p[1] for loop in sector_loop for p in loop]
        for cx in range(min(xs) // _CELL, max(xs) // _CELL + 1):
            for cy in range(min(ys) // _CELL, max(ys) // _CELL + 1):
                grid[(cx, cy)].append(sector)
    return loops, grid


#: the boxes of loops already asked about, by the loop's own identity (a loop lives as long as its index)
_BOXES: dict[int, tuple[Any, tuple[int, int, int, int]]] = {}


def _box(loop: list) -> tuple[int, int, int, int]:
    kept = _BOXES.get(id(loop))
    if kept is None or kept[0] is not loop:
        if len(_BOXES) > 100_000:
            _BOXES.clear()
        kept = (loop, (min(p[0] for p in loop), min(p[1] for p in loop), max(p[0] for p in loop), max(p[1] for p in loop)))
        _BOXES[id(loop)] = kept
    return kept[1]


def _sector_at(point: tuple[int, int], loops: dict, grid: dict) -> int | None:
    """The smallest playable sector holding this point, or None."""
    found = []
    px, py = point
    for sector in grid.get((px // _CELL, py // _CELL), ()):
        sector_loop = loops[sector]
        if not sector_loop:
            continue
        x0, y0, x1, y1 = _box(sector_loop[0])
        if not (x0 < px < x1 and y0 < py < y1):          # strictly: on the edge is not inside
            continue
        if point_in_loop(point, sector_loop[0]) <= 0:
            continue
        # A point inside a hole is not inside the sector.
        if any(point_in_loop(point, hole) > 0 for hole in sector_loop[1:]):
            continue
        area = abs(sum(
            sector_loop[0][i][0] * sector_loop[0][(i + 1) % len(sector_loop[0])][1]
            - sector_loop[0][(i + 1) % len(sector_loop[0])][0] * sector_loop[0][i][1]
            for i in range(len(sector_loop[0]))))
        found.append((area, sector))
    if not found:
        return None
    return min(found)[1]


def _sectors_at(points: list[tuple[int, int]], loops: dict) -> list[int | None]:
    """`_sector_at` for many points: each sector asked about all the points in its box at once, in the same integers."""
    import numpy as np
    if not points:
        return []
    at = np.array(points, dtype=np.int64)
    order = np.argsort(at[:, 0], kind="stable")
    xs, ys = at[order, 0], at[order, 1]
    best = [None] * len(points)
    best_area: list[int | None] = [None] * len(points)

    def state(px, py, loop):
        """1 inside, 0 outside, -1 on the edge (`point_in_loop`)."""
        inside, edge = np.zeros(len(px), bool), np.zeros(len(px), bool)
        for (x1, y1), (x2, y2) in zip(loop, loop[1:] + loop[:1]):
            dx, dy, rx, ry = x2 - x1, y2 - y1, px - x1, py - y1
            cross = ry * dx - rx * dy
            edge |= ((cross == 0) & (px >= min(x1, x2)) & (px <= max(x1, x2)) & (py >= min(y1, y2)) & (py <= max(y1, y2)))
            if dy:
                over = (y1 > py) != (y2 > py)
                inside ^= over & ((cross > 0) if dy > 0 else (cross < 0))
        return np.where(edge, -1, inside.astype(np.int8))

    for sector, sector_loops in loops.items():
        if not sector_loops:
            continue
        outline = [tuple(p) for p in sector_loops[0]]
        x0, y0, x1, y1 = _box(sector_loops[0])
        lo, hi = np.searchsorted(xs, x0, "right"), np.searchsorted(xs, x1, "left")
        near = np.flatnonzero((ys[lo:hi] > y0) & (ys[lo:hi] < y1)) + lo
        if not len(near):
            continue
        near = near[state(xs[near], ys[near], outline) == 1]
        for hole in sector_loops[1:]:
            if len(near):
                near = near[state(xs[near], ys[near], [tuple(p) for p in hole]) != 1]
        if not len(near):
            continue
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, outline[1:] + outline[:1])))
        for k in order[near].tolist():
            if best_area[k] is None or (area, sector) < (best_area[k], best[k]):
                best_area[k], best[k] = area, sector
    return best


def observe_wall_thickness(name: str, disk: Any) -> list[dict[str, Any]]:
    playable = design_sectors(disk)
    if not playable:
        return []
    loops, _grid = _index_sectors(disk, playable)

    owner: dict[int, int] = {}
    for sector in playable:
        fields = disk.sectors[sector].fields
        start = int(fields["wall_ptr"])
        for wall in range(start, start + int(fields["wall_count"])):
            owner[wall] = sector

    span = {}
    for sector in playable:
        fields = disk.sectors[sector].fields
        span[sector] = (int(fields["ceiling_z"]), int(fields["floor_z"]))

    def coexist(a: int, b: int) -> bool:
        top = max(span[a][0], span[b][0])
        bottom = min(span[a][1], span[b][1])
        return bottom - top >= COEXIST_HEIGHT

    out = []
    # every point that may be asked about, in two goes: which side of each wall is its own, then the rays the other way
    solid, probes = [], []
    for wall_id, wall in enumerate(disk.walls):
        fields = wall.fields
        if int(fields["next_sector"]) >= 0:
            continue                       # an opening, not a mass
        mine = owner.get(wall_id)
        if mine is None:
            continue
        nxt = disk.walls[int(fields["point2"])].fields
        ax, ay = int(fields["x"]), int(fields["y"])
        bx, by = int(nxt["x"]), int(nxt["y"])
        length = math.hypot(bx - ax, by - ay)
        if length < PROBE_MIN_WALL_LENGTH:
            continue
        # Outward normal. Build's winding puts the interior on one side; find
        # which by probing a single step and seeing which one leaves the sector.
        nx, ny = (by - ay) / length, -(bx - ax) / length
        midx, midy = (ax + bx) / 2.0, (ay + by) / 2.0
        probe = (int(round(midx + nx * PROBE_STEP)), int(round(midy + ny * PROBE_STEP)))
        solid.append((wall_id, mine, ax, ay, bx, by, nx, ny))
        probes.append(probe)
    rays = []
    for (wall_id, mine, ax, ay, bx, by, nx, ny), found in zip(solid, _sectors_at(probes, loops)):
        if found == mine:
            nx, ny = -nx, -ny
        for fraction in PROBE_SAMPLES:
            px = ax + (bx - ax) * fraction
            py = ay + (by - ay) * fraction
            rays.append((wall_id, mine, [(int(round(px + nx * distance)), int(round(py + ny * distance)))
                                         for distance in range(PROBE_STEP, PROBE_REACH + 1, PROBE_STEP)]))
    answers = iter(_sectors_at([point for _w, _m, points in rays for point in points], loops))
    for wall_id, mine, points in rays:
        hit = None
        for distance, found in zip(range(PROBE_STEP, PROBE_REACH + 1, PROBE_STEP), [next(answers) for _ in points]):
            if found is not None and found != mine and coexist(mine, found):
                hit = (distance, found)
                break
        if hit is None:
            continue
        out.append({
            "map": name,
            "wall": wall_id,
            "sector": mine,
            "other": hit[1],
            "thickness": hit[0],
            "thickness_player_widths": round(hit[0] / PLAYER_WIDTH, 3),
        })
    return out
