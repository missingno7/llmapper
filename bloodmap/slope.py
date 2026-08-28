"""Sloped floors and ceilings, which this project had never built.

Every one of the 43 campaign maps slopes sectors -- the thinnest does 5, the
median 59, and the biggest 238. The monastery had none in 112 sectors, which is
a whole axis of Blood architecture the level was not using: every roof flat,
every vault flat, every ramp a staircase.

The campaign slopes ceilings about twice as often as floors (2,392 sectors
against 1,576), and that ratio is the shape of the feature. A sloped floor is a
ramp and has to stay walkable; a sloped ceiling is a pitched roof, a vault, a
cave mouth, and costs nothing but headroom.

How Build does it
-----------------

``getflorzofslope`` reads::

    wal  = &wall[sector->wallptr];  wal2 = &wall[wal->point2];
    dx = wal2->x - wal->x;  dy = wal2->y - wal->y;
    i = nsqrtasm(dx*dx + dy*dy) << 5;
    j = dmulscale3(dx, y - wal->y, -dy, x - wal->x);
    return sector->floorz + scale(sector->floorheinum, j, i);

``dmulscale3`` is the cross product shifted right by 3 and ``i`` is the wall
length shifted left by 5, so the whole thing reduces to

    z(p) = floor_z + heinum * perpendicular_distance(p, hinge) / 256

with the distance signed to the left of the hinge wall's direction. Two things
follow, and both are constraints on the caller rather than details:

* **The hinge is the sector's first wall.** Not a wall you pick -- ``wallptr``.
  A region that wants a slope has to be emitted with the hinge edge first, which
  is why `PlanarLayout` rotates the wall loop instead of offering a parameter.
* **The floor and the ceiling share that hinge.** One sector cannot pitch its
  roof about one edge and ramp its floor about another. A slope that needs its
  own axis needs its own sector -- which is also how a real pitched roof is
  built: two sectors meeting along the ridge.

Build's z axis is 16 units to one horizontal unit, so heinum 4096 is 45 degrees.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

Point = tuple[int, int]

#: heinum for 45 degrees. Build's z axis is 16 units per horizontal unit and
#: ``scale(heinum, j, i)`` divides by 256 = 16 * 16.
HEINUM_45 = 4096

#: Divisor in ``z = heinum * perpendicular / SLOPE_DIVISOR``.
SLOPE_DIVISOR = 256.0

#: What the campaign's slopes measure, over 1,077 sloped floors and 1,538 sloped
#: ceilings with a non-zero heinum::
#:
#:     surface     q1  median    q3   p95
#:     floor     1024    1536  2304  4352
#:     ceiling   1280    2304  4096  5120
#:
#: 1536 is 20.6 degrees and 2304 is 29.4, so a campaign floor slope is a ramp you
#: walk up and a campaign ceiling slope is a roof pitch. The p95 is the limit
#: used here: past it a slope is a special case -- a chute, a shaft -- and should
#: be asked for by heinum rather than arrived at by accident.
CAMPAIGN_HEINUM = {
    "floor": {"q1": 1024, "median": 1536, "q3": 2304, "p95": 4352},
    "ceiling": {"q1": 1280, "median": 2304, "q3": 4096, "p95": 5120},
}

#: How far a campaign slope travels, top to bottom, in player heights: q1 0.73,
#: median 1.29, q3 2.18, p95 5.45. A slope is a storey, not a lip.
CAMPAIGN_RISE_PLAYER_HEIGHTS = {"q1": 0.73, "median": 1.29, "q3": 2.18, "p95": 5.45}

from .player_space import PLAYER_PROFILES

#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height


class SlopeError(ValueError):
    """A slope that cannot be built, or that the engine would read differently."""


@dataclass(frozen=True)
class SlopeSpec:
    """A slope on one surface of one region.

    ``hinge`` names the edge the surface pivots about, as the two points of an
    edge of the region's outer ring; the surface keeps the region's declared z
    along that edge and departs from it going inward.

    ``rise_player_heights`` is what the author is actually thinking about -- how
    much taller the room gets at the far side -- and is converted to a heinum
    against the region's own depth. Blood's z points down, so a *negative* rise
    on a ceiling lifts it and a negative rise on a floor raises the walking
    surface; `PlanarLayout` takes the sign as given rather than guessing which
    the author meant.

    Give ``heinum`` instead when the number matters more than the effect.
    """

    hinge: tuple[Point, Point]
    rise_z: float | None = None
    heinum: int | None = None

    def __post_init__(self) -> None:
        if (self.rise_z is None) == (self.heinum is None):
            raise SlopeError("a slope needs exactly one of rise_z or heinum")


def _edge_vector(hinge: tuple[Point, Point]) -> tuple[float, float, float]:
    (ax, ay), (bx, by) = hinge
    dx, dy = float(bx - ax), float(by - ay)
    length = math.hypot(dx, dy)
    if length <= 0:
        raise SlopeError("a slope hinge with no length")
    return dx, dy, length


def signed_distance(point: Point, hinge: tuple[Point, Point]) -> float:
    """Distance from the hinge line, signed the way Build signs it.

    Build's ``j`` is ``dx*(y-ay) - dy*(x-ax)``; this is that cross product over
    the hinge length, so it carries the same sign in map units.
    """
    dx, dy, length = _edge_vector(hinge)
    (ax, ay), _ = hinge
    return (dx * (point[1] - ay) - dy * (point[0] - ax)) / length


def depth(outline: Sequence[Point], hinge: tuple[Point, Point]) -> float:
    """How far the region reaches from its hinge, in map units."""
    return max((abs(signed_distance(p, hinge)) for p in outline), default=0.0)


def rise_at(heinum: int, distance: float) -> float:
    """Displacement of the surface, in z units, at a perpendicular distance."""
    return heinum * distance / SLOPE_DIVISOR


def _inward_sign(outline: Sequence[Point], hinge: tuple[Point, Point]) -> int:
    """Which side of the hinge line the body of the region lies on."""
    reach = 0.0
    for point in outline:
        distance = signed_distance(point, hinge)
        if abs(distance) > abs(reach):
            reach = distance
    return 1 if reach >= 0 else -1


def heinum_for_rise(outline: Sequence[Point], hinge: tuple[Point, Point],
                    rise_z: float) -> int:
    """The heinum that displaces the far edge of this region by ``rise_z``.

    Which side of the hinge line the region lies on is a property of the region,
    not of the request, so the sign is worked out here rather than asked for.
    """
    span = depth(outline, hinge)
    if span <= 0:
        raise SlopeError("a slope on a region with no depth from its hinge")
    value = int(round(rise_z * SLOPE_DIVISOR / span)) * _inward_sign(outline, hinge)
    if not -32768 <= value <= 32767:
        raise SlopeError(f"slope heinum {value} does not fit the map format")
    return value


def hinge_index(loop: Sequence[tuple[Point, Point]],
                hinge: tuple[Point, Point]) -> int:
    """Where in an emitted wall loop the hinge edge sits.

    Matched on the pair of endpoints in either order: a caller naming an edge of
    a region does not know which way round the compiler wound it.
    """
    want = {tuple(hinge[0]), tuple(hinge[1])}
    for index, (a, b) in enumerate(loop):
        if {tuple(a), tuple(b)} == want:
            return index
    raise SlopeError(f"hinge edge {hinge} is not an edge of the region")


def surface_bounds(outline: Sequence[Point], hinge: tuple[Point, Point],
                   base_z: int, heinum: int) -> tuple[float, float]:
    """The lowest and highest z the sloped surface reaches over the region.

    A plane is extreme at a vertex, so the corners are the whole answer.
    """
    values = [base_z + rise_at(heinum, signed_distance(p, hinge)) for p in outline]
    return (min(values), max(values)) if values else (float(base_z), float(base_z))


def headroom(outline: Sequence[Point], hinge: tuple[Point, Point], *,
             floor_z: int, ceiling_z: int,
             floor_heinum: int = 0, ceiling_heinum: int = 0) -> float:
    """The tightest gap between the two surfaces anywhere in the region.

    Blood's z points down, so the gap is ``floor - ceiling``. Both surfaces
    share the hinge, so their difference is itself a plane, and is again extreme
    at a corner.
    """
    worst: float | None = None
    for point in outline:
        distance = signed_distance(point, hinge)
        gap = ((floor_z + rise_at(floor_heinum, distance))
               - (ceiling_z + rise_at(ceiling_heinum, distance)))
        worst = gap if worst is None else min(worst, gap)
    return float(worst if worst is not None else floor_z - ceiling_z)


def steeper_than_campaign(heinum: int, surface: str) -> str | None:
    """A note when a slope leaves the range the campaign built in."""
    band = CAMPAIGN_HEINUM.get(surface)
    if band is None or heinum == 0:
        return None
    steepness = abs(heinum)
    if steepness > band["p95"]:
        degrees = math.degrees(math.atan(band["p95"] / HEINUM_45))
        return (f"{surface} heinum {steepness} is steeper than 95% of the "
                f"campaign's ({band['p95']}, {degrees:.0f} deg)")
    return None
