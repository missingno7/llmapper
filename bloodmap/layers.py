"""Space stacked over space, and the conditions that make it safe.

A Build sector is a 2D polygon with one floor and one ceiling. Everything a
level does to get a second storey is a way around that, and this module governs
the most dangerous of them: two sectors that share ground in plan.

`PlanarLayout` already forbids that outright -- `_validate_regions` raises on any
undeclared footprint overlap -- and the only escape was `declare_special`, which
switches every check off at once. That is the right answer for a room-over-room
pair and the wrong answer for a street with a cellar under it, so levels built
with this toolkit are flat.

A **layer** is the missing middle: a named planar arrangement with its own height
band. Overlap *within* a layer stays forbidden. Overlap *between* layers is
allowed, and is exactly where the conditions below are checked.

Why these conditions
--------------------

Blood runs the engine in ``ENGINE_19960925`` (blood/src/blood.cpp:1890), and that
one line decides all of it.

**Movement never looks at z.** Every ``clipmove`` ends in ``clipmove_compat``
(build/src/clip.cpp:1823 dispatching to :1112), which resolves the mover's sector
by walking ``clipsectorlist`` and taking the first entry containing the point *in
plan alone* (clip.cpp:1114-1119). That list is a portal-graph breadth-first
search seeded at the mover's own sector (clip.cpp:1508), grown across two-sided
walls (clip.cpp:1688), bounded by a *box* about the mover (clip.cpp:1500) that no
wall outside it is even looked at through (clip.cpp:1574). Only when nothing in
the list contains the point does it fall through to a reverse linear scan that
*does* compare ceiling and floor against the mover's z (clip.cpp:1122-1157).

Two consequences, and both of them contradict the way this is usually stated.

**Portal separation is the primary protection**, because the z-blind path is the
one that runs on every single move. Z separation is the backstop that saves the
cold lookup.

**But the separation that matters is not a hop count.** The list is seeded with
the mover's own sector and scanned in order, so index 0 wins whenever it still
contains the point; a mover is only misplaced just after leaving a sector, when
the right answer is a portal neighbour. A wrong sector has to arrive no later
than that to win -- two hops, not five -- *and* the walk between them has to stay
inside a box about 2,264 units across. Two rooms one above the other are zero
apart in plan and still perfectly safe if the only way between them goes out to a
stairwell and back, which is how a building is built.

Measured that way by ``tools.mine_layers``, over all 43 campaign maps and 2,614
genuinely overlapping sector pairs:

* 16.4% of overlap pairs have intersecting z bands -- a habit, not a law.
* 0.19% are close enough to be transposed at all.
* **0.038%** -- one pair, in one map -- are both. That conjunction is the law,
  and it is what :data:`OVERLAP_RULE` states. The single case is E1M1's sectors
  45 and 55, where 55's wall loop revisits one vertex three times and carries
  zero-width spurs, so it is a degenerate outline rather than a second storey.

The hop *distribution* is reported alongside because it is what the campaign
looks like from a distance -- q1 9, median 12, q3 15, with 594 pairs not
portal-joined at all -- but it is a statement about Blood's levels being large,
not about what is safe.

The declared-owner condition is not an engine behaviour but a toolchain one.
Blood reads a player start's sector straight off the marker sprite
(warp.cpp:62-70), teleports to the destination marker's recorded sector
(triggers.cpp:1577), and `dbLoadMap` trusts every sprite's stored ``sectnum``
without recomputing it (db.cpp:1195). Whatever *we* write is what the engine
believes forever -- and we resolve a placement's owner in plan.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable

from .planar_geom import (
    Point,
    classify_segment_pair,
    loops_equivalent,
    same_ground,
    point_in_loops,
    polygon_relation,
    z_interval,
    z_relation,
)
from . import drawsort
from .planar_layout import PlanarLayoutError

#: One standing Blood human, in Build z units. See `bloodmap.player_space`.
STANDING_HEIGHT = 16960

#: The vertical acceleration MoveDude adds per game frame (blood/src/actor.h:186).
DUDE_GRAVITY = 58254

#: Impact damage MoveDude forgives on landing (blood/src/actor.h:187), in the
#: engine's x16 health scale, so this is 100 hit points.
FALL_DAMAGE_FLOOR = 100 << 4

#: The shortest portal-graph separation the campaign is willing to put between
#: two sectors that share ground. Below this it essentially stops: 21 of 2,614
#: overlap pairs, and only 4 of those also clash in z.
#:
#: Reported as evidence, not enforced. Hops are a *proxy* for the thing that
#: actually decides whether two sectors can be confused, and a poor one: a small
#: building cannot put five portals between its ground floor and the loft over
#: it, and does not need to.
MIN_PORTAL_SEPARATION = 5

#: How close in the portal graph two overlapping sectors have to be before the
#: engine can actually transpose them.
#:
#: `clipsectorlist` is seeded with the mover's *own* sector (clip.cpp:1508) and
#: `clipmove_compat` scans it in order (clip.cpp:1114), so index 0 wins whenever
#: it still contains the point. A mover is only ever misplaced when they have
#: just left their sector, and then the right answer is a portal neighbour --
#: depth 1 in the walk. For a wrong sector to be taken instead it has to reach
#: the list no later, which means it is a neighbour of the same sector, or of
#: the mover's destination itself. Two hops, not five.
#:
#: Five is what the campaign's *median* separation looks like from a distance,
#: and it is mostly a statement that Blood's levels are big. Measured at the
#: floor instead, the campaign puts 5 of its 2,614 overlap pairs within two hops
#: -- 0.19% -- and exactly one of those also clashes in z.
CONFUSABLE_HOPS = 2

#: What actually bounds the clip list, in Build units.
#:
#: `clipmove` fixes a box of `rad` about the mover (build/src/clip.cpp:1500) and
#: refuses to even look at a wall lying wholly outside it (clip.cpp:1574), so a
#: sector only enters `clipsectorlist` if the portal walk reaches it *and* stays
#: inside that box. The radius is a distance, not a hop count:
#:
#:     rad = move + MAXCLIPDIST + walldist + 8
#:
#: `MAXCLIPDIST` is 1024 (build/src/engine_priv.h:19). A player's `walldist` is
#: their clipdist shifted twice -- 0x30 in `gPlayerTemplate` (blood/src/dude.cpp:1581)
#: -- plus the 16 `MoveDude` adds for a player (blood/src/actor.cpp:4593). The
#: move term is one tick of running, and a generous 1024 is used so the bound
#: errs toward calling things dangerous.
MAX_CLIP_DIST = 1024
PLAYER_WALLDIST = (0x30 << 2) + 16
TICK_MOVE = 1024
CLIP_RADIUS = MAX_CLIP_DIST + PLAYER_WALLDIST + 8 + TICK_MOVE

#: The three footprint relations that mean two regions genuinely share ground.
#: The same predicate `PlanarLayout._validate_regions` refuses on, so the
#: measurement and the enforcement are one test.
OVERLAPPING_KINDS = frozenset({
    "partial_area_overlap",
    "full_containment_a_in_b",
    "full_containment_b_in_a",
    "identical_footprint",
})

#: Relationships that are their own contract and are not layer overlaps.
#: A room-over-room stack overlaps in plan on purpose and is resolved by
#: `CheckLink`, not by `clipmove`.
DECLARED_KINDS = frozenset({"stack", "water", "goo", "link", "helper"})

OVERLAP_RULE = (
    "two regions that share ground must be resolved by disjoint height bands, or "
    "by being far enough apart that one mover's clip box cannot hold a portal "
    f"walk between them within {CONFUSABLE_HOPS} hops"
)

#: Movement and draw order are different faults. The sentence above is
#: `clipmove_compat`. This one is `wallfront`. Passing either says nothing
#: about the other.
DRAW_ORDER_RULE = (
    "whether two sectors can be drawn together is decided by wallfront "
    "(build/src/engine.cpp:2227), which takes the two walls' x/y and the "
    "viewer's x/y and has no z in it; the bunch sort answers a negative with "
    "continue (engine.cpp:9736). Disjoint bands and portal-walk separation "
    "are clipmove conditions. They do not rank bunches."
)


class LayerError(PlanarLayoutError):
    """A stack of space the engine would not keep straight."""


@dataclass(frozen=True)
class Layer:
    """One planar arrangement, and the slice of z it is allowed to occupy.

    Blood's z points down, so `ceiling_z` is the smaller number. A band is
    stated as the pair the regions themselves use, in the same sense, so that a
    region's own two numbers can be compared against it without translation.
    """

    layer_id: str
    ceiling_z: int
    floor_z: int
    note: str = ""

    def __post_init__(self) -> None:
        if int(self.ceiling_z) >= int(self.floor_z):
            raise LayerError(
                f"layer {self.layer_id!r} has its ceiling at {self.ceiling_z} and its "
                f"floor at {self.floor_z}; in Blood z points down, so a band needs the "
                "ceiling to be the smaller number"
            )

    @property
    def band(self) -> tuple[int, int]:
        return (int(self.ceiling_z), int(self.floor_z))

    @property
    def height(self) -> int:
        return int(self.floor_z) - int(self.ceiling_z)

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer_id, "ceiling_z": int(self.ceiling_z),
            "floor_z": int(self.floor_z), "height": self.height,
            "height_bodies": round(self.height / STANDING_HEIGHT, 2),
            "note": self.note,
        }


@dataclass(frozen=True)
class Overlap:
    """Two regions sharing ground, and what keeps the engine from confusing them."""

    left: str
    right: str
    left_layer: str
    right_layer: str
    kind: str
    z: str
    hops: int | None
    #: Whether a portal walk from one to the other stays inside a mover's clip
    #: box the whole way. This is the condition the engine actually applies; the
    #: hop count beside it is the campaign-comparable statistic.
    one_clip_list: bool = False
    declared: str | None = None

    @property
    def bands_disjoint(self) -> bool:
        return self.z != "overlapping_vertical_volumes"

    @property
    def separated(self) -> bool:
        """Can the engine still tell these two apart by where they are?

        Both halves have to fail before a pair is confusable: the two sectors
        must be close enough in the portal walk to be transposed at all, *and*
        near enough in plan for one clip box to hold the walk between them.
        """
        if self.hops is None or self.hops > CONFUSABLE_HOPS:
            return True
        return not self.one_clip_list

    @property
    def movement_resolved_by(self) -> tuple[str, ...]:
        """What keeps the *engine* from putting the player in the wrong one.

        Both entries are about `clipmove_compat` and `updatesectorz_compat`.
        Neither says anything about what gets drawn: `wallfront`
        (build/src/engine.cpp:2227) takes two walls' x/y and the viewer's x/y and
        has no z in it at all, so disjoint bands cannot help it order anything,
        and the renderer's flood is gated by `testvisiblemost` on per-column
        occlusion (polymost.cpp:6601), which has never heard of a clip box.
        
        This was called `resolved_by` and read as though either entry settled the
        pair. It settles half of it. The other half is co-visibility, and it is
        reported separately because it is a separate question.
        """
        out = []
        if self.bands_disjoint:
            out.append("bands")
        if self.separated:
            out.append("separation")
        return tuple(out)

    @property
    def safe_to_move_through(self) -> bool:
        return bool(self.declared) or bool(self.movement_resolved_by)

    @property
    def safe(self) -> bool:
        """Movement only. Rendering is `layer-overlap-in-one-view`."""
        return self.safe_to_move_through

    def to_dict(self) -> dict[str, Any]:
        return {
            "regions": [self.left, self.right],
            "layers": [self.left_layer, self.right_layer],
            "kind": self.kind, "z": self.z, "hops": self.hops,
            "one_clip_list": self.one_clip_list,
            "declared": self.declared,
            "movement_resolved_by": list(self.movement_resolved_by),
            "safe_to_move_through": self.safe_to_move_through,
        }


@dataclass(frozen=True)
class LayerFinding:
    """One thing wrong with how this level stacks, said precisely enough to fix."""

    severity: str
    code: str
    message: str
    location: str

    def to_dict(self) -> dict[str, Any]:
        return {"severity": self.severity, "code": self.code,
                "message": self.message, "location": self.location}


@dataclass
class Slab:
    """One region met by a vertical line, and the air under the one above it."""

    region_id: str
    layer: str
    ceiling_z: int
    floor_z: int
    air_above: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "region": self.region_id, "layer": self.layer,
            "ceiling_z": self.ceiling_z, "floor_z": self.floor_z,
            "clear_height": self.floor_z - self.ceiling_z,
            "clear_bodies": round((self.floor_z - self.ceiling_z) / STANDING_HEIGHT, 2),
            "air_above": self.air_above,
        }


@dataclass
class Drop:
    """A fall from one region's floor to another's, priced in Blood's own arithmetic."""

    from_region: str
    to_region: str
    distance: int
    damage_hp: float
    ticks: int

    @property
    def bodies(self) -> float:
        return self.distance / STANDING_HEIGHT

    @property
    def painless(self) -> bool:
        return self.damage_hp <= 0.0

    @property
    def lethal_from_full_health(self) -> bool:
        return self.damage_hp >= 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_region, "to": self.to_region,
            "distance": self.distance, "bodies": round(self.bodies, 2),
            "damage_hp": round(self.damage_hp, 1), "ticks": self.ticks,
            "painless": self.painless, "lethal": self.lethal_from_full_health,
        }


# ---------------------------------------------------------------------------
# declaring layers
# ---------------------------------------------------------------------------

def layers_of(layout: Any) -> dict[str, Layer]:
    """The layers declared on a layout. Empty until one is declared."""
    return getattr(layout, "layers", {})


def declare_layer(layout: Any, layer_id: str, *, ceiling_z: int, floor_z: int,
                  note: str = "") -> Layer:
    """Name a height band that a set of regions is allowed to occupy.

    Declaring layers is what turns `RegionSpec.layer` from a label into a
    constraint. A layout with no declared layers behaves exactly as before.
    """
    registry = getattr(layout, "layers", None)
    if registry is None:
        registry = {}
        layout.layers = registry
    if layer_id in registry:
        raise LayerError(f"duplicate layer id {layer_id!r}")
    layer = Layer(layer_id, int(ceiling_z), int(floor_z), note)
    registry[layer_id] = layer
    return layer


def layer_bands_overlap(left: Layer, right: Layer) -> bool:
    return z_relation(left.band, right.band) == "overlapping_vertical_volumes"


def permitted_band(layout: Any, region_id: str,
                   registry: dict[str, Layer] | None = None) -> tuple[int, int]:
    """How much z this region is allowed, given what it is joined to.

    A region normally has to fit inside its own layer's band -- that is what
    stops layers from bleeding into each other. But the thing that *joins* two
    layers necessarily occupies both: a stair down from the street stands on the
    cellar floor and is open to the street ceiling, and there is no honest layer
    to assign it to.

    So a region declared-joined to another layer may reach across into that
    layer's band, and only into that one. The connectors widen; everything else
    stays where it was put.
    """
    known = layers_of(layout) if registry is None else registry
    region = layout.regions[region_id]
    band = known.get(region.layer)
    if band is None:
        return (-2 ** 31, 2 ** 31)
    ceiling, floor = band.band
    for reached in _layers_reached(layout, region_id, known):
        ceiling = min(ceiling, reached.ceiling_z)
        floor = max(floor, reached.floor_z)
    if getattr(region, "parallax_ceiling", False):
        # A yard is not roofed by the layer above it. The sky belongs to no
        # layer -- it is the absence of one -- and an open sector's ceiling is
        # the sky plane, which necessarily stands above every storey around it.
        # Only its *floor* says which layer it is part of.
        #
        # This is not a hole in the conditions. The open volume is still its
        # real interval everywhere else, so a gallery built out over the yard is
        # still a z-clash with it and is still caught. What is permitted here is
        # only the yard being as tall as the buildings round it, which is what
        # an outdoor space is.
        ceiling = -2 ** 31
    return (ceiling, floor)


#: Roles whose whole job is to be between two places. A run of these is one
#: connector even though it is many sectors -- a ten-step stair down from a loft
#: to a yard is a single thing that spans two bands, and each step in the middle
#: of it belongs to neither.
CONNECTOR_ROLES = frozenset({"stair", "doorway", "gateway", "lift", "ramp"})


def _layers_reached(layout: Any, region_id: str,
                    known: dict[str, Layer]) -> list[Layer]:
    """The bands a region may borrow, by being or touching a connector.

    An ordinary room reaches the layers it is directly joined to -- a landing
    that opens onto a stairhead. A *connector* also reaches through other
    connectors, because a stair is one object however many sectors it is cut
    into, and the middle steps are joined to nothing but their neighbours.

    Reaching stops at the first non-connector, so a stair widens to the rooms at
    its two ends and no further. A layer full of ordinary rooms joined to each
    other never widens at all, which is the whole point.
    """
    joins = layout.declared_joins()
    neighbours: dict[str, set[str]] = {}
    for pair in joins:
        members = tuple(pair)
        if len(members) != 2:
            continue
        left, right = members
        neighbours.setdefault(left, set()).add(right)
        neighbours.setdefault(right, set()).add(left)
    # Room-over-room pairs are vertical connectors, not portal edges.  They
    # still join the two height bands for the purpose of a stair's permitted
    # extent: otherwise a real stair ending at a stack mouth is incorrectly
    # told it may only occupy its street band.
    for left, right, _kind in getattr(layout, "special_pairs", ()):
        neighbours.setdefault(left, set()).add(right)
        neighbours.setdefault(right, set()).add(left)

    home = layout.regions[region_id].layer
    seen = {region_id}
    frontier = deque([region_id])
    out: dict[str, Layer] = {}
    while frontier:
        current = frontier.popleft()
        for other_id in neighbours.get(current, ()):
            if other_id in seen:
                continue
            seen.add(other_id)
            other = layout.regions.get(other_id)
            if other is None:
                continue
            if other.layer != home and other.layer in known:
                out[other.layer] = known[other.layer]
            if str(getattr(other, "role", "")) in CONNECTOR_ROLES:
                frontier.append(other_id)
    if str(getattr(layout.regions[region_id], "role", "")) not in CONNECTOR_ROLES:
        # An ordinary room only borrows from what it directly touches, so drop
        # anything that was reached by walking on through a connector.
        direct = {
            layout.regions[other].layer
            for other in neighbours.get(region_id, ())
            if other in layout.regions
        }
        out = {name: band for name, band in out.items() if name in direct}
    return list(out.values())


# ---------------------------------------------------------------------------
# the three spatial queries
# ---------------------------------------------------------------------------

def column_at(layout: Any, x: int, y: int) -> list[Slab]:
    """What is above and below this point, and how much air is between.

    Top first, in Blood's sense: the smallest `ceiling_z` comes first. `air_above`
    on each slab is the gap between the top of that region and the floor of the
    one over it, or None for the topmost.

    Called by the band conditions, and by the fragment's acceptance where it has
    to show that the player looks down onto a space they have walked.
    """
    found: list[Slab] = []
    for region in layout.regions.values():
        loops = [list(region.outer)] + [list(hole) for hole in region.holes]
        if point_in_loops((int(x), int(y)), loops) == 0:
            continue
        found.append(Slab(region.region_id, region.layer,
                          int(region.ceiling_z), int(region.floor_z)))
    found.sort(key=lambda slab: slab.ceiling_z)
    for index in range(1, len(found)):
        found[index].air_above = found[index].ceiling_z - found[index - 1].floor_z
    return found


def can_see(layout: Any, region_a: str, region_b: str,
            *, occluders: list[tuple[Point, Point]] | None = None) -> bool:
    """Is there a clear 2D line between the two regions' interior samples?

    Deliberately 2D and deliberately layer-blind: it answers the renderer's
    question, which is whether a flood could hold both, not the player's, which
    would need eye height and a frustum. Where it says no, no viewpoint can hold
    both; where it says yes, one might.

    Called by the shared-sight condition.
    """
    if region_a == region_b:
        return True
    left = interior_sample(layout, region_a)
    right = interior_sample(layout, region_b)
    if left is None or right is None:
        return False
    walls = solid_edges(layout) if occluders is None else occluders
    for start, end in walls:
        relation = classify_segment_pair(left, right, start, end)
        if relation is not None and str(relation["kind"]) == "proper_crossing":
            return False
    return True


def drop_between(layout: Any, from_region: str, to_region: str) -> Drop:
    """How far is this drop, and what does Blood charge for it?

    Not a guess. `MoveDude` integrates a falling dude as ``z += zvel>>8`` and then
    ``z += (kDudeGravity*2)>>8; zvel += kDudeGravity`` each tick
    (blood/src/actor.cpp:4595, 4628-4631), and charges
    ``mulscale30(vax, vax) - kFallDamageFloor`` on landing (actor.cpp:4835-4846),
    where `vax` is the impact z-velocity exactly -- `actFloorBounceVector` with
    ``elastic = 0`` over a flat floor returns its input (actor.cpp:2691-2699).
    This replays that integration rather than approximating it.

    Called by the fragment where it authors a descent, and by its acceptance.
    """
    upper = layout.regions[from_region]
    lower = layout.regions[to_region]
    distance = int(lower.floor_z) - int(upper.floor_z)
    if distance < 0:
        raise LayerError(
            f"{to_region} is above {from_region}, so this is not a drop; Blood's z "
            "points down, so the floor below has the larger number"
        )
    damage, ticks = fall_cost(distance)
    return Drop(from_region, to_region, distance, damage, ticks)


def fall_cost(distance: int) -> tuple[float, int]:
    """Damage in hit points, and the tick the landing happens on, for a free fall.

    Returns 0.0 damage for anything the engine forgives. Blood's own thresholds
    fall out of this: the last painless drop is 62,564 z (3.69 bodies), the first
    that hurts is 68,025 (4.01), and 127,411 (7.51) kills from full health.
    """
    if distance <= 0:
        return (0.0, 0)
    z, zvel, tick = 0, 0, 0
    while z < distance and tick < 4096:
        tick += 1
        if zvel:
            z += zvel >> 8
        z += (DUDE_GRAVITY * 4 // 2) >> 8
        zvel += DUDE_GRAVITY
    raw = ((zvel * zvel) >> 30) - FALL_DAMAGE_FLOOR
    return (max(0.0, raw / 16.0), tick)


# ---------------------------------------------------------------------------
# the geometry the queries and conditions share
# ---------------------------------------------------------------------------

def interior_sample(layout: Any, region_id: str) -> Point | None:
    """A point inside the region, used as its stand-in for sight tests."""
    region = layout.regions[region_id]
    loops = [list(region.outer)] + [list(hole) for hole in region.holes]
    points = list(region.outer)
    count = len(points)
    for index in range(count):
        a, b, c = points[index], points[(index + 1) % count], points[(index + 2) % count]
        candidate = ((a[0] + b[0] + c[0]) // 3, (a[1] + b[1] + c[1]) // 3)
        if point_in_loops(candidate, loops) == 1:
            return candidate
    centroid = (sum(p[0] for p in points) // count, sum(p[1] for p in points) // count)
    return centroid if point_in_loops(centroid, loops) == 1 else None


def solid_edges(layout: Any) -> list[tuple[Point, Point]]:
    """The stretches of region boundary that actually stop a sightline.

    Two things cancel an edge, and the earlier version knew only one of them:

    * a same-layer neighbour running along it -- two rooms side by side share a
      boundary and it is a portal, not a wall; and
    * **a declared join, whatever layers the two regions are in.** This is the
      one that was missing. Edges were grouped by layer and only same-layer
      neighbours could cancel, so a cross-layer connection -- a yard opening onto
      the roof above it, which is the whole subject of this module -- had the
      lower region's edge cancelled by its same-layer neighbour and the upper
      region's edge left standing as if it were masonry. `can_see` then treated a
      real opening as an occluder from one side and not the other, and the
      sightline conditions under-reported in exactly the direction that matters.

    Cancellation is now by interval rather than wholesale. An edge part-covered
    by a join keeps the part that is not covered; the old code dropped the whole
    edge on any overlap, which cancelled masonry that was never a portal.
    """
    joins = _declared_join_segments(layout)

    by_layer: dict[str, list[tuple[str, Point, Point]]] = {}
    for region in layout.regions.values():
        loops = [list(region.outer)] + [list(hole) for hole in region.holes]
        for loop in loops:
            for index, start in enumerate(loop):
                end = loop[(index + 1) % len(loop)]
                by_layer.setdefault(region.layer, []).append(
                    (region.region_id, start, end))

    out: list[tuple[Point, Point]] = []
    for edges in by_layer.values():
        for owner, start, end in edges:
            covered: list[tuple[float, float]] = []
            for other, other_start, other_end in edges:
                if other == owner:
                    continue
                span = _covered_span(start, end, other_start, other_end)
                if span is not None:
                    covered.append(span)
            for join_a, join_b in joins.get(owner, ()):
                span = (_covered_span(start, end, join_a, join_b)
                        or _covered_span(start, end, join_b, join_a))
                if span is not None:
                    covered.append(span)
            out.extend(_remaining_segments(start, end, covered))
    return out


def _declared_join_segments(layout: Any) -> dict[str, list[tuple[Point, Point]]]:
    """Each region's declared openings, as segments, indexed by region.

    A connection that names its own `a1`/`a2` is taken at its word. One that does
    not is resolved to the stretch its two regions actually share, which is what
    the compiler will pair anyway.
    """
    out: dict[str, list[tuple[Point, Point]]] = {}
    for connection in getattr(layout, "connections", {}).values():
        a, b = connection.region_a, connection.region_b
        if connection.a1 and connection.a2:
            segment = (tuple(connection.a1), tuple(connection.a2))
            out.setdefault(a, []).append(segment)
            out.setdefault(b, []).append(segment)
            continue
        left = layout.regions.get(a)
        right = layout.regions.get(b)
        if left is None or right is None:
            continue
        for a_start, a_end in _outline_edges(left):
            for b_start, b_end in _outline_edges(right):
                relation = classify_segment_pair(a_start, a_end, b_start, b_end)
                if relation is None:
                    continue
                if str(relation["kind"]) not in _COINCIDENT_KINDS:
                    continue
                overlap = relation.get("overlap")
                segment = ((tuple(overlap[0]), tuple(overlap[1]))
                           if overlap and len(overlap) == 2 else (a_start, a_end))
                out.setdefault(a, []).append(segment)
                out.setdefault(b, []).append(segment)
    return out


#: The three ways `classify_segment_pair` says "these two lie along each other".
_COINCIDENT_KINDS = {
    "exact_reversed_coincident", "exact_same_direction_coincident",
    "partial_collinear_overlap",
}


def _covered_span(start: Point, end: Point, other_start: Point,
                  other_end: Point) -> tuple[float, float] | None:
    """Where `other` lies along `start->end`, as a `[0, 1]` interval, or None."""
    relation = classify_segment_pair(start, end, other_start, other_end)
    if relation is None or str(relation["kind"]) not in _COINCIDENT_KINDS:
        return None
    overlap = relation.get("overlap")
    if not overlap or len(overlap) != 2:
        return (0.0, 1.0)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = dx * dx + dy * dy
    if length == 0:
        return (0.0, 1.0)
    ts = sorted(((p[0] - start[0]) * dx + (p[1] - start[1]) * dy) / length
                for p in overlap)
    lo, hi = max(0.0, ts[0]), min(1.0, ts[1])
    return (lo, hi) if hi > lo else None


def _remaining_segments(start: Point, end: Point,
                        covered: list[tuple[float, float]]
                        ) -> list[tuple[Point, Point]]:
    """The parts of an edge nothing cancels, rounded back to Build units."""
    if not covered:
        return [(start, end)]
    dx, dy = end[0] - start[0], end[1] - start[1]
    out: list[tuple[Point, Point]] = []
    cursor = 0.0
    for lo, hi in sorted(covered):
        if lo > cursor:
            out.append(((round(start[0] + cursor * dx), round(start[1] + cursor * dy)),
                        (round(start[0] + lo * dx), round(start[1] + lo * dy))))
        cursor = max(cursor, hi)
    if cursor < 1.0:
        out.append(((round(start[0] + cursor * dx), round(start[1] + cursor * dy)),
                    end))
    return [(a, b) for a, b in out if a != b]


def portal_graph(layout: Any) -> dict[str, set[str]]:
    """Regions joined by something the player can actually walk through.

    Only the declared joins, which is exactly what the compiler turns into a
    two-sided wall. An earlier version counted any two regions whose boundaries
    ran along each other, on the grounds that being conservative is safe -- and
    that made a loft look one hop from the room beneath it, because they have the
    same outline. Being wrong in the safe direction is still being wrong when it
    fires on every stacked building in the level.
    """
    graph: dict[str, set[str]] = {region_id: set() for region_id in layout.regions}
    for pair in layout.declared_joins():
        members = tuple(pair)
        if len(members) != 2:
            continue
        left, right = members
        if left in graph and right in graph:
            graph[left].add(right)
            graph[right].add(left)
    return graph


def in_one_clip_list(layout: Any, left_id: str, right_id: str,
                     portals: dict[str, set[str]] | None = None) -> bool:
    """Could a mover standing over the overlap hold both of these at once?

    This is the condition `clipmove_compat` actually applies. `clipmove` fixes a
    box of `CLIP_RADIUS` about the mover and will not so much as look at a wall
    lying wholly outside it (build/src/clip.cpp:1574), so the portal walk that
    builds `clipsectorlist` cannot leave that box. Two sectors are confusable
    only if a walk from one to the other stays inside it the whole way.

    A hop count cannot express that. Two rooms one above the other are zero
    apart in plan and may still be unreachable within the box, because the only
    way between them goes out to a stairwell and back -- which is exactly how a
    building is built, and why the campaign's five-hop habit is a consequence of
    its levels being large rather than a rule about safety.
    """
    graph = portal_graph(layout) if portals is None else portals
    centre = _overlap_centre(layout, left_id, right_id)
    if centre is None:
        return False
    frontier = deque([left_id])
    seen = {left_id}
    while frontier:
        current = frontier.popleft()
        for other in graph.get(current, ()):
            if other in seen:
                continue
            if not _within_clip_box(layout, other, centre):
                continue
            if other == right_id:
                return True
            seen.add(other)
            frontier.append(other)
    return right_id in seen


def _overlap_centre(layout: Any, left_id: str, right_id: str) -> Point | None:
    """A point in the ground the two share, where a mover would stand."""
    left = _bbox(layout.regions[left_id])
    right = _bbox(layout.regions[right_id])
    low_x, high_x = max(left[0], right[0]), min(left[2], right[2])
    low_y, high_y = max(left[1], right[1]), min(left[3], right[3])
    if low_x > high_x or low_y > high_y:
        return None
    return ((low_x + high_x) // 2, (low_y + high_y) // 2)


def _within_clip_box(layout: Any, region_id: str, centre: Point) -> bool:
    """Does any of this region's boundary fall inside the clip box about `centre`?"""
    box = _bbox(layout.regions[region_id])
    return not (box[0] > centre[0] + CLIP_RADIUS or box[2] < centre[0] - CLIP_RADIUS
                or box[1] > centre[1] + CLIP_RADIUS or box[3] < centre[1] - CLIP_RADIUS)


def hops_between(graph: dict[str, set[str]], start: str, goal: str,
                 limit: int = 24) -> int | None:
    """Shortest portal-graph distance, or None if unjoined or beyond `limit`.

    None is the safest separation there is, not a missing measurement.
    """
    if start == goal:
        return 0
    frontier = deque([(start, 0)])
    seen = {start}
    while frontier:
        node, distance = frontier.popleft()
        if distance >= limit:
            continue
        for next_node in graph.get(node, ()):
            if next_node == goal:
                return distance + 1
            if next_node not in seen:
                seen.add(next_node)
                frontier.append((next_node, distance + 1))
    return None


# ---------------------------------------------------------------------------
# the conditions
# ---------------------------------------------------------------------------

def find_overlaps(layout: Any) -> list[Overlap]:
    """Every pair of regions that genuinely shares ground, and how it is resolved."""
    declared: dict[frozenset[str], str] = {}
    for left, right, kind in getattr(layout, "special_pairs", []):
        declared[frozenset((left, right))] = kind

    ids = list(layout.regions)
    portals = portal_graph(layout)
    boxes = {region_id: _bbox(layout.regions[region_id]) for region_id in ids}
    # A city can put one undercroft room beneath dozens of street sectors.  The
    # earlier pair loop launched the same breadth-first portal search once per
    # overlap, so adding the first real under-city made validation quadratic in
    # overlaps *and* graph size.  Reachability has no dependency on the pair's
    # overlap centre, therefore cache the complete limited search per source.
    hop_cache: dict[str, dict[str, int]] = {}

    def hops_from(source: str) -> dict[str, int]:
        cached = hop_cache.get(source)
        if cached is not None:
            return cached
        distances = {source: 0}
        frontier = deque([source])
        while frontier:
            current = frontier.popleft()
            distance = distances[current]
            if distance >= 24:
                continue
            for other in portals.get(current, ()):
                if other not in distances:
                    distances[other] = distance + 1
                    frontier.append(other)
        hop_cache[source] = distances
        return distances

    out: list[Overlap] = []
    for index, left_id in enumerate(ids):
        for right_id in ids[index + 1:]:
            if not _boxes_overlap(boxes[left_id], boxes[right_id]):
                continue
            left = layout.regions[left_id]
            right = layout.regions[right_id]
            loops_l = [list(left.outer)] + [list(h) for h in left.holes]
            loops_r = [list(right.outer)] + [list(h) for h in right.holes]
            if (loops_equivalent(left.outer, right.outer)
                    or same_ground(left.outer, right.outer)):
                # The commonest overlap of all -- a loft directly over the room
                # it belongs to -- and the one `polygon_relation` does not call
                # an overlap: two identical outlines have no vertex strictly
                # inside the other, so it reports a shared boundary. Two rooms
                # with one footprint share all of their ground, not none of it.
                kind = "identical_footprint"
            else:
                kind = str(polygon_relation(loops_l, loops_r)["kind"])
                if kind not in OVERLAPPING_KINDS:
                    continue
            out.append(Overlap(
                left=left_id, right=right_id,
                left_layer=left.layer, right_layer=right.layer,
                kind=kind,
                z=z_relation(z_interval(int(left.ceiling_z), int(left.floor_z)),
                             z_interval(int(right.ceiling_z), int(right.floor_z))),
                hops=hops_from(left_id).get(right_id),
                one_clip_list=in_one_clip_list(layout, left_id, right_id,
                                               portals),
                declared=declared.get(frozenset((left_id, right_id))),
            ))
    return out


def check(layout: Any, *, overlaps: Iterable[Overlap] | None = None,
          tally: dict[str, list[int]] | None = None) -> list[LayerFinding]:
    """Run every layer condition over a layout, hardest first.

    Returns findings rather than raising, so a caller can print all of them.
    `enforce` is the one that stops a build.
    """
    registry = layers_of(layout)
    found = list(find_overlaps(layout)) if overlaps is None else list(overlaps)
    out: list[LayerFinding] = []

    # Layers have to mean something before they can excuse anything.
    for region in layout.regions.values():
        if not registry:
            break
        if region.layer not in registry:
            out.append(LayerFinding(
                "error", "layer-undeclared",
                f"region sits in layer {region.layer!r}, which is not declared; "
                f"declared layers are {', '.join(sorted(registry)) or 'none'}",
                region.region_id))
            continue
        ceiling, floor = permitted_band(layout, region.region_id, registry)
        if int(region.ceiling_z) < ceiling or int(region.floor_z) > floor:
            band = registry[region.layer]
            reach = ("" if (ceiling, floor) == band.band else
                     f" (widened to {ceiling}..{floor} by what it is joined to)")
            out.append(LayerFinding(
                "error", "layer-band-escape",
                f"region occupies {region.ceiling_z}..{region.floor_z} but layer "
                f"{region.layer!r} is {band.ceiling_z}..{band.floor_z}{reach}; a layer "
                "whose regions leave its band cannot separate anything",
                region.region_id))

    for overlap in found:
        where = f"{overlap.left} / {overlap.right}"
        if overlap.declared:
            continue
        if overlap.left_layer == overlap.right_layer:
            out.append(LayerFinding(
                "error", "layer-overlap-within",
                f"two regions of layer {overlap.left_layer!r} share ground "
                f"({overlap.kind}); overlap is what layers are for, so it belongs "
                "between them, not inside one",
                where))
            continue
        left_band = registry.get(overlap.left_layer)
        right_band = registry.get(overlap.right_layer)
        if left_band and right_band and layer_bands_overlap(left_band, right_band):
            # Two layers whose bands intersect are not two layers. They are one
            # plan drawn twice, and nothing downstream can tell them apart:
            # the clip list reads plan only and the linear fallback reads a z
            # that lands in both. This is stricter than the per-pair law below
            # on purpose -- the law says what the engine survives, and this says
            # what a layer means.
            out.append(LayerFinding(
                "error", "layer-bands-intersect",
                f"layers {overlap.left_layer!r} ({left_band.ceiling_z}..{left_band.floor_z}) "
                f"and {overlap.right_layer!r} ({right_band.ceiling_z}..{right_band.floor_z}) "
                "occupy the same height and their plans share ground; separate the "
                "bands or stop the plans overlapping",
                where))
            continue
        if not overlap.movement_resolved_by:
            out.append(LayerFinding(
                "error", "layer-overlap-unresolved",
                f"{OVERLAP_RULE}; this pair has neither -- z is {overlap.z} and they "
                f"are {overlap.hops} portal hops apart. clipmove_compat "
                "(build/src/clip.cpp:1114) resolves a mover's sector from the clip "
                "list in plan alone, so the engine has nothing left to tell them apart",
                where))
        elif not overlap.separated:
            out.append(LayerFinding(
                "note", "layer-overlap-close",
                f"{overlap.hops} portal hops apart and inside one clip box, so a mover "
                "crossing between them can reach both at the same depth of the walk; "
                "the disjoint height bands are the only thing resolving this pair, and "
                "clipmove_compat (build/src/clip.cpp:1114) does not read them",
                where))

    if tally is not None:
        undeclared = [o for o in found if not o.declared]
        tally.setdefault("layer-overlap-unresolved", [len(undeclared), 0])[1] = len(
            [f for f in out if f.code == "layer-overlap-unresolved"])
        tally.setdefault("layer-overlap-close", [len(undeclared), 0])[1] = len(
            [f for f in out if f.code == "layer-overlap-close"])
    out.extend(_stacked_and_seen_findings(layout, found, tally))
    out.extend(_unorderable_wall_findings(layout, found, tally))
    out.extend(_coincident_wall_findings(layout, found, tally))
    out.extend(_shared_sight_findings(layout, found, tally))
    out.extend(_declared_owner_findings(layout, found, tally))
    return out


def _coincident_wall_findings(layout: Any, found: list[Overlap],
                              tally: dict[str, list[int]] | None = None) -> list[LayerFinding]:
    """Two sectors whose walls run along each other, with no portal between them.

    This is a *renderer* fault, and it is independent of everything above --
    movement and drawing are two hazards with two conditions, and collapsing
    them into one is how the first version of this module came to pass a level
    whose upper storey glitched.

    `wallfront` (build/src/engine.cpp:2227) decides which of two wall bunches is
    in front using x, y and the viewer's x, y. There is no z in it. For two walls
    lying on the same line it finds `t1 == 0 && t2 == 0` and returns **-1**, and
    the bunch sort at engine.cpp:9739 answers a -1 with `continue` -- so the two
    are never ordered against each other and whichever the loop happens to be
    holding is drawn first. The source says so itself, at engine.cpp:9738:
    ``closest = 0;  //Almost works, but not quite :(``

    The campaign leaves **22** such pairs in 113,912 walls across 44 maps. Six
    maps have any at all and the worst has six, so this is a habit strong enough
    to build on but not an absolute: it is reported, not enforced.

    A declared room-over-room pair is exempt. Its two halves are congruent on
    purpose, the engine draws the far side through the mirror tile rather than
    through the wall, and the campaign's own stacks are built this way.
    """
    declared = {frozenset((o.left, o.right)) for o in found if o.declared}
    for left, right, _kind in getattr(layout, "special_pairs", []):
        declared.add(frozenset((left, right)))

    out: list[LayerFinding] = []
    ids = list(layout.regions)
    seen: set[frozenset[str]] = set()
    walls = solid_edges(layout)
    examined = 0
    for index, left_id in enumerate(ids):
        left = layout.regions[left_id]
        for right_id in ids[index + 1:]:
            pair = frozenset((left_id, right_id))
            if pair in declared or pair in seen:
                continue
            right = layout.regions[right_id]
            if left.layer == right.layer:
                continue
            if not layout.separate_arrangements(left_id, right_id):
                continue
            shared = _shared_boundary_length(left, right)
            if shared <= 0:
                continue
            examined += 1
            # Coincident walls are only a fault when one flood can hold both.
            # The store roof and a step of the cellar stair share a boundary and
            # are eighty thousand units apart in z with no sightline between
            # them; saying so would be the hop count's mistake made again.
            vantage = covisible(layout, left_id, right_id)
            if vantage is None:
                continue  # proved: no point holds both, so nothing to order
            seen.add(pair)
            out.append(LayerFinding(
                "note", "layer-walls-coincide",
                f"{shared} units of boundary run along each other with no portal "
                "between them; wallfront (build/src/engine.cpp:2227) is a 2D test "
                "and returns -1 for walls on one line, which the bunch sort skips "
                "rather than resolves, so which of the two is drawn first is not "
                "something the map decides. The campaign leaves 22 such pairs in "
                f"113,912 walls. `covisible` could not rule out a sightline "
                f"holding both, from {vantage}. Separate the two footprints so "
                "there is nothing to order, or close the opening that lets one "
                "vantage reach both",
                f"{left_id} / {right_id}"))
    if tally is not None:
        tally["layer-walls-coincide"] = [examined, len(out)]
    return out


#: How many portals deep a sightline is followed before the search gives up and
#: reports "possible" rather than proving anything. Every extra hop costs, and a
#: view that has already crossed six apertures has almost nothing left of its
#: cone. Raising this can only turn a "possible" into a "proved impossible".
SIGHT_DEPTH = 6


def view_cuts(layout: Any) -> set[tuple[str, str]]:
    """The `(from, into)` pairs whose flood the author has cut, one way.

    A one-way wall carries `CSTAT_WALL_1WAY` on one of the two coincident walls,
    and `scansector` tests it on the wall belonging to the sector it is standing
    in -- `if ((!(wal->cstat&32)) && ...) scansector(nextsectnum)`, engine.c:3134.
    So the cut is ordered rather than mutual: inside `from`, `into` is never
    collected, and the wall is drawn solid from `over_picnum` instead
    (engine.c:3157); inside `into`, `from` is still reached normally.

    That is the one thing in this module that can turn `layer-overlap-in-one-view`
    from a warning into a proof, because it is the only flag in the format that
    stops the flood. Distance cannot, bands cannot, and hop counts cannot.
    """
    out: set[tuple[str, str]] = set()
    for connection in getattr(layout, "connections", {}).values():
        side = getattr(connection, "view_cut_from", None)
        if side is None:
            continue
        a, b = connection.region_a, connection.region_b
        near = a if str(side) in ("left", "a", a) else b
        out.add((near, b if near == a else a))
    return out


def openings_into(layout: Any, region_id: str) -> list[tuple[str, tuple[Point, Point]]]:
    """The apertures a sightline has to come through to reach this region.

    One per declared join, as the segment the two regions share. A region with
    no openings cannot be seen into at all.
    """
    out: list[tuple[str, tuple[Point, Point]]] = []
    region = layout.regions[region_id]
    cuts = view_cuts(layout)
    for pair in layout.declared_joins():
        if region_id not in pair:
            continue
        other_id = next(iter(pair - {region_id}), None)
        other = layout.regions.get(other_id) if other_id else None
        if other is None:
            continue
        # Standing here, the renderer never collects the other side.
        if (region_id, other_id) in cuts:
            continue
        for a_start, a_end in _outline_edges(region):
            for b_start, b_end in _outline_edges(other):
                relation = classify_segment_pair(a_start, a_end, b_start, b_end)
                if relation is None:
                    continue
                if str(relation["kind"]) not in {
                    "exact_reversed_coincident", "exact_same_direction_coincident",
                    "partial_collinear_overlap",
                }:
                    continue
                overlap = relation.get("overlap")
                if overlap and len(overlap) == 2:
                    out.append((other_id, (tuple(overlap[0]), tuple(overlap[1]))))
                else:
                    out.append((other_id, (a_start, a_end)))
    return out


def sight_reach(layout: Any, region_id: str,
                depth: int = SIGHT_DEPTH) -> dict[str, tuple[Point, Point]]:
    """Every region a sightline could reach from inside this one, and through what.

    A conservative portal walk. It prunes only where it can *prove* an aperture
    is unreachable -- when the candidate opening lies wholly behind the plane of
    the one already crossed, so that no ray through the first can meet it -- and
    keeps everything else. Being wrong in this direction is safe: the answer is a
    superset of what is really visible, so where two of these sets are disjoint,
    the two regions are genuinely never seen together.
    """
    reached: dict[str, tuple[Point, Point]] = {}
    frontier: deque = deque()
    home = _band_of(layout, region_id)
    for other_id, aperture in openings_into(layout, region_id):
        band = _band_through(home, _band_of(layout, other_id))
        if band is None:
            continue
        if other_id not in reached:
            reached[other_id] = aperture
            frontier.append((other_id, aperture, band, region_id, 1))
    while frontier:
        current, aperture, band, came_from, hops = frontier.popleft()
        if hops >= depth:
            continue
        behind = interior_sample(layout, came_from)
        for other_id, next_aperture in openings_into(layout, current):
            if other_id in (region_id, came_from) or other_id in reached:
                continue
            if behind is not None and _wholly_behind(aperture, next_aperture, behind):
                continue
            # An opening passes only the height the two rooms have in common,
            # and a sightline cannot get back what an earlier one took away.
            # This is what `umost`/`dmost` do per column, and without it the
            # walk cannot tell a roof from the cellar under the store.
            narrowed = _band_through(band, _band_of(layout, other_id))
            if narrowed is None:
                continue
            reached[other_id] = next_aperture
            frontier.append((other_id, next_aperture, narrowed, current, hops + 1))
    return reached


def _band_of(layout: Any, region_id: str) -> tuple[int, int]:
    region = layout.regions[region_id]
    return (int(region.ceiling_z), int(region.floor_z))


def _band_through(carried: tuple[int, int],
                  room: tuple[int, int]) -> tuple[int, int] | None:
    """What is left of a sightline's height after one more opening.

    An aperture between two rooms passes only the z the two share, so a walk
    that crosses several of them keeps the running intersection. Empty means the
    view is closed -- there is no height at which anything could be seen through
    that chain -- and that is a proof, not a guess.
    """
    low = max(carried[0], room[0])
    high = min(carried[1], room[1])
    return None if low >= high else (low, high)


def _side_of(line: tuple[Point, Point], point: Point) -> int:
    (ax, ay), (bx, by) = line
    return (point[0] - ax) * (by - ay) - (point[1] - ay) * (bx - ax)


def _wholly_behind(aperture: tuple[Point, Point], candidate: tuple[Point, Point],
                   behind: Point) -> bool:
    """Is every point of `candidate` on the side the ray came *from*?

    A segment on its own has no front, which is what the first version of this
    got wrong: it pruned by an arbitrary winding and threw away the forward
    direction, so the walk stopped at one hop and the prover cheerfully declared
    two rooms it had never looked at impossible to see together. The direction of
    travel has to be carried, and `behind` is a point in the region the ray just
    left.

    This is the only pruning the walk does, and it is exact. Nothing on the near
    side of an aperture is reachable through it, whatever the rest of the level
    looks like.
    """
    reference = _side_of(aperture, behind)
    if reference == 0:
        return False
    sides = [_side_of(aperture, point) for point in candidate]
    if reference > 0:
        return all(side > 0 for side in sides)
    return all(side < 0 for side in sides)


def covisible(layout: Any, left_id: str, right_id: str,
              depth: int = SIGHT_DEPTH) -> str | None:
    """A region that could see into both, or None when that is impossible.

    This is the question the renderer actually asks. Two sectors whose walls lie
    on one line cannot be ordered by `wallfront` -- it is a 2D test that returns
    -1 for them -- so the map is only safe if **no point ever holds both at
    once**. Sampling poses cannot establish that; a walk that only prunes what it
    can prove unreachable can.

    Returns the name of a region from which both are possibly visible, so the
    answer can be taken to the observer and rendered. `None` is the proof.
    """
    # The reach map is a property of this layout's portals and height bands,
    # not of the particular pair being asked about.  Layer validation asks the
    # same question for every plan-overlap pair; recomputing every source walk
    # for each pair turned a whole-city undercroft into minutes of duplicate
    # work.  A layout is assembled before `compile`, so its region and
    # connection counts are a sufficient invalidation key here.
    key = (len(layout.regions), len(layout.connections), int(depth))
    cached = getattr(layout, "_layer_sight_reach", None)
    if not cached or cached.get("key") != key:
        reach = {
            region_id: set(sight_reach(layout, region_id, depth))
            for region_id in layout.regions
        }
        layout._layer_sight_reach = {"key": key, "reach": reach}
    else:
        reach = cached["reach"]
    for region_id, seen in reach.items():
        if left_id in seen and right_id in seen:
            return region_id
    if left_id in reach.get(right_id, ()) or right_id in reach.get(left_id, ()):
        return left_id if right_id in reach.get(left_id, ()) else right_id
    return None


def _common_vantage(layout: Any, left_id: str, right_id: str,
                    walls: list[tuple[Point, Point]]) -> str | None:
    """A region with a clear plan sightline to both, or None.

    Stands in for the renderer's own flood, which is bounded by screen-space
    occlusion rather than by anything this side can compute exactly. Where this
    says no, no viewpoint holds both; where it says yes, one might.
    """
    for region_id in layout.regions:
        if region_id in (left_id, right_id):
            continue
        if (can_see(layout, region_id, left_id, occluders=walls)
                and can_see(layout, region_id, right_id, occluders=walls)):
            return region_id
    return None


def _shared_boundary_length(left: Any, right: Any) -> int:
    """How much of these two outlines lies on the same line, in Build units."""
    total = 0.0
    for a_start, a_end in _outline_edges(left):
        for b_start, b_end in _outline_edges(right):
            relation = classify_segment_pair(a_start, a_end, b_start, b_end)
            if relation is None:
                continue
            if str(relation["kind"]) not in {
                "exact_reversed_coincident", "exact_same_direction_coincident",
                "partial_collinear_overlap",
            }:
                continue
            overlap = relation.get("overlap")
            if overlap and len(overlap) == 2:
                (x1, y1), (x2, y2) = overlap
                total += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            else:
                total += ((a_end[0] - a_start[0]) ** 2
                          + (a_end[1] - a_start[1]) ** 2) ** 0.5
    return int(round(total))


def _outline_edges(region: Any) -> list[tuple[Point, Point]]:
    out: list[tuple[Point, Point]] = []
    for loop in [list(region.outer)] + [list(hole) for hole in region.holes]:
        for index, start in enumerate(loop):
            out.append((start, loop[(index + 1) % len(loop)]))
    return out


#: How many portals from a common space is "the same place" for this purpose.
#: Two hops is a yard with a door into the room and a door into the storey over
#: it, which is the shape that tore this project's fragment -- but only when
#: those two doors lie on one wall line, so one look holds both halves stacked.
VANTAGE_HOPS = 2


def _apertures_toward(layout: Any, vantage_id: str, target_id: str,
                      hops: int = VANTAGE_HOPS) -> list[tuple[Point, Point]]:
    """The vantage's own openings that lead to `target` within `hops`.

    The aperture recorded is the one in the vantage's wall, not the inner door:
    that is the facade the viewer looks through. Two such apertures on one line
    are one vertical sightline.
    """
    out: list[tuple[Point, Point]] = []
    for neighbor, aperture in openings_into(layout, vantage_id):
        if neighbor == target_id:
            out.append(aperture)
            continue
        if hops < 2:
            continue
        for further, _inner in openings_into(layout, neighbor):
            if further == target_id:
                out.append(aperture)
                break
    return out


def _same_facade_into_both(layout: Any, vantage_id: str,
                           left_id: str, right_id: str) -> bool:
    """Does this vantage open into both storeys along one wall line?

    That is the engine failure, not merely "can see both". Perpendicular
    openings -- a street door on the north and a porch on the east -- are how
    BB4 stacks three floors on one space without a tear: you cannot look into
    two of them along the same line. `wallfront` returning `COLLINEAR` is the
    engine's own test for that line.
    """
    toward_left = _apertures_toward(layout, vantage_id, left_id)
    toward_right = _apertures_toward(layout, vantage_id, right_id)
    for left_ap in toward_left:
        for right_ap in toward_right:
            if drawsort.wallfront(left_ap, right_ap) == drawsort.COLLINEAR:
                return True
    return False


def _region_polygon(region: Any) -> list[tuple[Point, Point]]:
    return _outline_edges(region)


def _point_inside(polygon: list[tuple[Point, Point]], point: tuple[float, float]) -> bool:
    x, y = point
    inside = False
    for (ax, ay), (bx, by) in polygon:
        if (ay > y) != (by > y):
            if x < ax + (y - ay) * (bx - ax) / float(by - ay):
                inside = not inside
    return inside


def _solid_edges_of(layout: Any, region_id: str) -> list[tuple[Point, Point]]:
    """This region's own boundary, less whatever a declared join opens."""
    region = layout.regions[region_id]
    joins = _declared_join_segments(layout).get(region_id, ())
    out: list[tuple[Point, Point]] = []
    for start, end in _outline_edges(region):
        covered = []
        for join_a, join_b in joins:
            span = _covered_span(start, end, join_a, join_b)
            if span is not None:
                covered.append(span)
        out.extend(_remaining_segments(start, end, covered))
    return out


def wall_standing_inside(layout: Any, owner_id: str, other_id: str,
                         offset: float = 24.0, samples: int = 5
                         ) -> tuple[Point, Point] | None:
    """A solid wall of `owner` standing **strictly inside** `other`'s plan.

    Strictly: points a little to either side of it are both inside the other
    region. A wall that merely runs along the other's boundary does not count,
    and that distinction is the whole rule -- two storeys built on one outline
    are flush and safe, two storeys where one is set in are not.

    Why it matters is entirely 2D. Build's sort ranks wall bunches with
    `wallfront`, which has no z in it, and a one-sided wall retires its screen
    columns whole once drawn -- `umost[x]=1; dmost[x]=0` (engine.c:3216) --
    however few rows it painted. `scansector` then refuses to recurse past a
    retired column (engine.c:3156). So a solid wall standing inside another
    sector's footprint blots out whatever is behind it *in plan*, even when the
    two are tens of thousands of units apart in z and neither could ever be seen
    through the other. Height does not save it. Nothing does, except not doing it.
    """
    other = layout.regions.get(other_id)
    if other is None:
        return None
    polygon = _region_polygon(other)
    for start, end in _solid_edges_of(layout, owner_id):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            continue
        nx, ny = -dy / length * offset, dx / length * offset
        for step in range(1, samples + 1):
            fraction = step / (samples + 1.0)
            px, py = start[0] + dx * fraction, start[1] + dy * fraction
            if (_point_inside(polygon, (px + nx, py + ny))
                    and _point_inside(polygon, (px - nx, py - ny))):
                return (start, end)
    return None


#: Ways of joining two regions that the renderer's flood does not follow.
#: A room-over-room link is a pair of marker sprites, not a two-sided wall:
#: `scansector` never crosses it, and Blood draws the far half in its own pass
#: with its own occlusion. Walking through one is not seeing through one.
UNFLOODED_FAMILIES = {"stack", "water", "link"}


def render_graph(layout: Any) -> dict[str, set[str]]:
    """`portal_graph` less the joins the renderer's flood does not cross."""
    graph = {region_id: set(neighbours)
             for region_id, neighbours in portal_graph(layout).items()}
    for region_a, region_b, kind in getattr(layout, "special_pairs", ()):
        if kind not in UNFLOODED_FAMILIES:
            continue
        graph.get(region_a, set()).discard(region_b)
        graph.get(region_b, set()).discard(region_a)
    return graph


def common_vantage_hops(layout: Any, left_id: str, right_id: str,
                        cap: int = VANTAGE_HOPS) -> int | None:
    """The fewest portals from one third region that reaches both, or None.

    On `render_graph`, not `portal_graph`: the question is what one flood can
    hold, and a room-over-room link is not something a flood crosses.
    """
    graph = render_graph(layout)

    def reach(source: str) -> dict[str, int]:
        seen = {source: 0}
        frontier = [source]
        for step in range(1, cap + 1):
            nxt = []
            for node in frontier:
                for other in graph.get(node, ()):
                    if other not in seen:
                        seen[other] = step
                        nxt.append(other)
            frontier = nxt
        return seen

    from_left, from_right = reach(left_id), reach(right_id)
    shared = [max(from_left[r], from_right[r])
              for r in set(from_left) & set(from_right)
              if r not in (left_id, right_id)]
    return min(shared) if shared else None


def _stacked_and_seen_findings(layout: Any, found: list[Overlap],
                               tally: dict[str, list[int]] | None = None
                               ) -> list[LayerFinding]:
    """A real second storey that one view can hold. This is the fault.

    Not co-visibility on its own: Blood draws both halves of an overlapping pair
    in 59% to 80% of views on BB4, E1M1, E3M1 and E4M2, and is fine. Not shared
    wall lines on their own: 91% of the campaign's overlapping pairs have them.
    **A storey.**

    Measured, on those four maps: same-footprint pairs are co-drawn in 658 views
    and the sort fails to order them in **none** of the 658. It never has to,
    because every same-footprint pair Blood ships is one of two things -- two
    near-coplanar rooms whose outlines happen to match (floors 0 to 5,120 apart,
    which is a step, not a storey), or a room-over-room link, which the engine
    draws in its own pass with its own occlusion. There is no third case. Blood
    does not build a plain second storey on one footprint and let you look into
    both halves.

    The reason is that for a building envelope there is no geometry that avoids
    it. The upper storey's outer walls are either *on* the lower storey's --
    coincident, so `wallfront` returns -1 (engine.cpp:2227), the sort answers
    with `continue` (engine.cpp:9736) and draw order falls out of enumeration
    order -- or *inside* them, and then a one-sided wall stands in the middle of
    the other's plan, retires its screen columns whole once drawn
    (engine.c:3216) and stops `scansector` recursing past them (engine.c:3156).
    Inset and flush are the only two options and both fail. Height does not
    help; the sort has no z in it.

    So the constraint is on what can see what, and it is architectural: **the
    space you enter the ground floor from must not also open into the storey
    above it through the same facade.** Two openings on one wall line are one
    vertical sightline -- that is what tore this project's fragment, looking
    north through a street door and a loading door stacked on it. BB4 puts three
    floors on one space and stays clean because you cannot look into two of them
    along the same line; a porch around the side is that pattern. Rooms that go
    different ways before they overlap satisfy it for free.
    """
    out: list[LayerFinding] = []
    examined = 0
    for overlap in found:
        if overlap.declared:
            continue          # a stack or a link is its own contract
        left = layout.regions.get(overlap.left)
        right = layout.regions.get(overlap.right)
        if left is None or right is None:
            continue
        examined += 1
        if overlap.kind != "identical_footprint":
            # Deliberately narrow as a *failure*. Containment pairs are examined
            # so the tally is the overlap inventory, not a silent subset: a
            # cellar strictly inside the street has walls that are parallel but
            # not on each other, `wallfront` ranks them, and Blood builds that
            # everywhere. `layer-overlap-in-one-view` is the condition that
            # speaks to those.
            continue
        gap = abs(int(left.floor_z) - int(right.floor_z))
        if gap <= STANDING_HEIGHT:
            continue          # a step between two rooms, not a storey
        vantage = covisible(layout, overlap.left, overlap.right)
        if vantage is None:
            continue
        if not _same_facade_into_both(layout, vantage, overlap.left, overlap.right):
            continue
        wall = (wall_standing_inside(layout, overlap.left, overlap.right)
                or wall_standing_inside(layout, overlap.right, overlap.left))
        how = ("one storey's wall stands inside the other's plan"
               if wall else "the two storeys' walls lie on each other")
        out.append(LayerFinding(
            "error", "layer-stacked-and-seen-together",
            f"{overlap.left} and {overlap.right} share ground and are {gap} apart "
            f"in z -- {gap / STANDING_HEIGHT:.1f} standing bodies, a storey -- and "
            f"{vantage} opens into both along one wall line. {how.capitalize()}, "
            "and the draw-order sort is 2D either way: coincident walls it "
            "refuses to rank (engine.cpp:2227, and the sort skips a refusal at "
            "engine.cpp:9736), and a wall standing inside the other's plan "
            "retires that column whole once drawn (engine.c:3216) so "
            "`scansector` never reaches what is behind it (engine.c:3156). "
            "Across BB4, E1M1, E3M1 and E4M2 the sort ordered same-footprint "
            "pairs in all 658 views that held one, because every such pair in "
            "the campaign is either near-coplanar or a room-over-room link, "
            "and none of them lets one vantage look into both halves along "
            "the same facade. Give the two storeys openings on different walls, "
            "or make the pair a declared room-over-room stack",
            f"{overlap.left} / {overlap.right}"))
    if tally is not None:
        tally["layer-stacked-and-seen-together"] = [examined, len(out)]
    return out


def _unorderable_wall_findings(layout: Any, found: list[Overlap],
                               tally: dict[str, list[int]] | None = None
                               ) -> list[LayerFinding]:
    """Wall pairs the draw-order sort cannot rank, by the engine's own predicate.

    `bloodmap.drawsort.wallfront` is a transcription of engine.cpp:2227, not a
    model of it. It returns -1 for two segments on one line and -2 for two that
    cross, and `bunchfront` passes both straight to a sort that answers them with
    `continue` (engine.cpp:9736). Neither answer depends on where the viewer is,
    so the whole map can be asked at once, exactly, without sampling a pose.

    **This is graded a note, and the corpus is why.** Of the campaign's 7,533
    overlapping sector pairs, 91.1% have at least one wall pair that is collinear
    with overlapping spans, or crossing. Blood builds stacked space by putting
    one sector directly over another with the same outline, so every wall of the
    one lies on a wall of the other; that is the technique, not a defect in it.
    A rule that fired on 91% of the corpus would be measuring the corpus's own
    grammar. What keeps those safe is that the two are almost never in one flood,
    which is what `overlap_visibility` and `layer-overlap-in-one-view` ask.

    So this reports rather than refuses, and it is worth reading next to those
    two: a pair that is both unorderable *and* co-visible is the one to move.
    """
    out: list[LayerFinding] = []
    examined = 0
    for overlap in found:
        if overlap.declared:
            continue
        left = layout.regions.get(overlap.left)
        right = layout.regions.get(overlap.right)
        if left is None or right is None:
            continue
        examined += 1
        hits = drawsort.segments_unorderable(_outline_edges(left),
                                             _outline_edges(right))
        if not hits:
            continue
        crossing = sum(1 for _i, _j, v in hits if v == drawsort.CROSSING)
        out.append(LayerFinding(
            "note", "layer-unorderable-walls",
            f"{len(hits)} wall pair(s) that `wallfront` (engine.cpp:2227) cannot "
            f"rank -- {len(hits) - crossing} on one line, {crossing} crossing. The "
            "sort at engine.cpp:9736 answers a negative with `continue`, so which "
            "of the two draws first falls out of enumeration order. The campaign "
            "does this in 91.1% of its overlapping pairs and is fine, because the "
            "two halves are almost never reached by one flood; read this together "
            "with layer-overlap-in-one-view, and move the geometry where both fire",
            f"{overlap.left} / {overlap.right}"))
    if tally is not None:
        tally["layer-unorderable-walls"] = [examined, len(out)]
    return out


def _shared_sight_findings(layout: Any, found: list[Overlap],
                           tally: dict[str, list[int]] | None = None) -> list[LayerFinding]:
    """No viewpoint may hold both halves of an overlap the engine cannot rank.

    **Every undeclared overlap is asked.** The only thing that may skip one is a
    proof that no single flood can hold both -- `covisible` returning None. Not
    distance, not height bands, not a hop count.

    The first version gated this on `Overlap.separated` and thereby never ran:
    MALTX has sixty-nine overlapping pairs and no z-clash at all, so every one of
    them was "separated" and condition C examined exactly zero. The premise was
    that a pair the portal graph had separated could not be reached by one flood,
    and it is false. `separated` is built from `clipmove_compat`'s clip box --
    where the *player* can be put. The renderer's flood is gated by
    `testvisiblemost` (build/src/polymost.cpp:6601) on per-column occlusion and
    consults neither the clip box nor z, and `wallfront` (engine.cpp:2227) is a
    2D test that returns -1 for walls on one line and is skipped by the sort.
    Disjoint bands stop the engine confusing which sector the player is in. They
    do nothing about it drawing both.
    """
    out: list[LayerFinding] = []
    close = [o for o in found if not o.declared]
    if tally is not None:
        tally.setdefault("layer-overlap-in-one-view", [0, 0])[0] = len(close)
    if not close:
        return out
    walls = solid_edges(layout)
    # A one-way wall is a solid wall to anyone standing on the flagged side --
    # engine.c:3157 draws it from `over_picnum` and engine.c:3134 never collects
    # what is behind it -- so for that one vantage it occludes like masonry. It
    # is not added to the shared set, because from the other side it is a portal
    # like any other and the view through it is real.
    cut_edges = _cut_edges(layout)
    for overlap in close:
        for region_id in layout.regions:
            if region_id in (overlap.left, overlap.right):
                continue
            occluders = walls + cut_edges.get(region_id, [])
            if not (can_see(layout, region_id, overlap.left, occluders=occluders)
                    and can_see(layout, region_id, overlap.right,
                                occluders=occluders)):
                continue
            vantage = region_id
            if tally is not None:
                tally["layer-overlap-in-one-view"][1] += 1
            out.append(LayerFinding(
                "warning", "layer-overlap-in-one-view",
                f"{vantage} has a clear plan sightline to both {overlap.left} and "
                f"{overlap.right}, which "
                "share ground; a renderer flood that holds both draws them in "
                "an order the map does not control. Build collects a neighbour "
                "sector through a portal and then lets all of its walls compete "
                "for screen columns -- the opening does not clip them -- so a "
                "storey above the eye can win the columns of the room behind it "
                "and leave them unwritten. The campaign's measured answer is "
                "architectural: openings on facades that are not the same line "
                "(BB4's stacked-entrance median is 98 degrees), and a plan that "
                "does not hand wallfront collinear neighbours. A one-way wall "
                "(engine.c:3134) cuts the flood from one side only and cannot "
                "resolve a symmetric co-visibility problem; a masked wall "
                "(cstat&48 == 16, engine.c:2920) changes what is painted, not "
                "what the sort can order. Neither flag is a substitute for "
                "moving the openings",
                f"{overlap.left} / {overlap.right}"))
            break
    return out


def _cut_edges(layout: Any) -> dict[str, list[tuple[Point, Point]]]:
    """The declared cuts as occluding segments, indexed by who cannot see past them."""
    out: dict[str, list[tuple[Point, Point]]] = {}
    for connection in getattr(layout, "connections", {}).values():
        side = getattr(connection, "view_cut_from", None)
        if side is None or not (connection.a1 and connection.a2):
            continue
        a, b = connection.region_a, connection.region_b
        near = a if str(side) in ("left", "a", a) else b
        out.setdefault(near, []).append((tuple(connection.a1), tuple(connection.a2)))
    return out


def _declared_owner_findings(layout: Any, found: list[Overlap],
                             tally: dict[str, list[int]] | None = None) -> list[LayerFinding]:
    """Nothing whose sector the engine reads off the map may stand over an overlap.

    Blood takes a player start's sector from the marker sprite (warp.cpp:69), a
    teleport destination's from the destination marker (triggers.cpp:1577), and
    `dbLoadMap` never recomputes either (db.cpp:1195). We resolve a placement's
    owning region in plan, so over an overlap the answer is decided by whichever
    region the compiler tested first, and the engine then believes it forever.
    """
    out: list[LayerFinding] = []
    if not found:
        if tally is not None:
            tally["layer-owner-over-overlap"] = [0, 0]
        return out
    sites: list[tuple[str, str, int, int]] = []
    start = getattr(layout, "player_start", None)
    if start is not None:
        sites.append(("player start", getattr(start, "region_id", "?"),
                      int(start.x), int(start.y)))
    for placement in getattr(layout, "placements", []):
        fields = getattr(placement, "fields", {}) or {}
        kind = int(fields.get("type", 0) or 0)
        if int(fields.get("status", 0) or 0) != 10 and kind == 0:
            continue
        sites.append((f"marker {placement.placement_id}", placement.region_id,
                      int(placement.x), int(placement.y)))

    overlapping = {frozenset((o.left, o.right)) for o in found if not o.declared}
    for label, region_id, x, y in sites:
        stack = [slab.region_id for slab in column_at(layout, x, y)]
        for index, left in enumerate(stack):
            for right in stack[index + 1:]:
                if frozenset((left, right)) in overlapping:
                    out.append(LayerFinding(
                        "error", "layer-owner-over-overlap",
                        f"{label} stands at ({x}, {y}), which is inside both {left} and "
                        f"{right}; the engine reads this sprite's sector off the map and "
                        "never checks it, so the compiler's plan-order guess becomes law",
                        region_id))
    if tally is not None:
        tally["layer-owner-over-overlap"] = [len(sites), len(out)]
    return out


def enforce(layout: Any) -> list[Overlap]:
    """Check the layers and raise on anything that would break the level.

    Returns the overlap inventory, so a build can record what it stacked and why
    the engine can tell the halves apart.
    """
    found = find_overlaps(layout)
    findings = check(layout, overlaps=found)
    fatal = [f for f in findings if f.severity == "error"]
    if fatal:
        lines = "\n".join(f"  {f.code} at {f.location}: {f.message}" for f in fatal)
        raise LayerError(f"{len(fatal)} layer condition(s) failed:\n{lines}")
    return found


def report(layout: Any) -> dict[str, Any]:
    """Everything this layout stacks, for the build manifest.

    Each condition reports how many pairs it *examined* as well as how many it
    failed. A condition that looked at nothing is as loud as one that failed --
    which is how the sight condition sat inert over sixty-nine overlapping pairs
    without anybody noticing.
    """
    found = find_overlaps(layout)
    tally: dict[str, list[int]] = {}
    findings = check(layout, overlaps=found, tally=tally)
    registry = layers_of(layout)
    populations: dict[str, int] = {}
    for region in layout.regions.values():
        populations[region.layer] = populations.get(region.layer, 0) + 1
    return {
        "$schema": "llmapper.layer-report",
        "rule": OVERLAP_RULE,
        "draw_order_rule": DRAW_ORDER_RULE,
        "min_portal_separation": MIN_PORTAL_SEPARATION,
        "layers": [
            dict(layer.to_dict(), regions=populations.get(layer_id, 0))
            for layer_id, layer in sorted(registry.items(),
                                          key=lambda item: item[1].ceiling_z)
        ],
        "overlaps": [o.to_dict() for o in found],
        "conditions": {
            code: {"examined": counts[0], "failed": counts[1],
                   "inert": counts[0] == 0}
            for code, counts in sorted(tally.items())
        },
        "findings": [f.to_dict() for f in findings],
    }


def _bbox(region: Any) -> tuple[int, int, int, int]:
    points = list(region.outer)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
