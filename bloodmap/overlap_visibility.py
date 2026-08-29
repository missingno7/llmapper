"""Overlapping sectors, and the cut that makes each one safe.

Two sectors on the same ground are only safe if the renderer can never hold both
at once. This module does **not** try to work out whether it can. It checks
something exact instead: that every route between them passes through a cut the
author declared.

Why not simulate visibility
---------------------------

The obvious approach -- replay `scansector` and see what it reaches -- does not
work, and reading the engine says why.

`polymost_scansector` (build/src/polymost.cpp:6632) does not flood the visible
set on its own. The only place it appends to its own queue is the proximity
clause::

    if (d*d < (p1.x*p1.x + p1.y*p1.y) * 256.f)
        sectorborder[sectorbordercnt++] = nextsectnum;

`d` is the cross product of the wall's two endpoints taken relative to the
viewer, so ``|d| / |wall|`` is the perpendicular distance to the wall's line and
the test is **distance < 16 Build units**. It pulls in a neighbour the viewer is
practically standing in, whatever way they face. Everything else in that loop
builds bunches of wall spans.

Recursion into distant sectors happens in the *drawing* code
(build/src/polymost.cpp:6601, and build/src/engine.cpp:4914 for classic)::

    if (nextsectnum >= 0)
        if (!bitmap_test(gotsector, nextsectnum) && testvisiblemost(x0,x1))
            polymost_scansector(nextsectnum);

`testvisiblemost` (polymost.cpp:5100) walks the `vsp` span list and answers
whether any screen column in ``x0..x1`` still has unoccluded vertical extent.
Occlusion is resolved per screen column. Reproducing that faithfully means
writing a software renderer, which is not what a validator should be.

Attempting it anyway is not merely expensive, it is uninformative. A flood with
the occlusion gate removed reaches nearly everything in a connected map: run over
the campaign it calls 89% of overlapping pairs co-renderable, which by this
project's own grading convention derives to a `note` -- the rule would measure
the approximation rather than Blood.

The asymmetry that makes the cheap answer the right one
-------------------------------------------------------

A validator must never call something safe when it is not. Calling something
unsafe when it would have been fine is acceptable: it only forces a design
change. So the check asks for a *proof*, and the proof is a graph query.

The traversal condition, in both renderers, is
``nextsector >= 0 && !(wal->cstat & 32)``. Two things therefore cut the flood
outright, and nothing else does:

* **Disconnection** -- no path exists. Free to verify, and E2M3 relies on it.
* **A one-way wall** -- `CSTAT_WALL_1WAY = 1u<<5u`
  (build/include/buildtypes.h:154) stops *scansector* traversal dead
  (engine.c:3134). A body still walks through **if bit 0 is clear**: clipmove
  tests `wal->cstat & dawalclipmask` (clip.cpp:1626, :1913) and CLIPMASK0 is
  bits 0 and 16 (build.h:225), which does not include bit 5. Setting bit 0 as
  well is what stops movement, and it is a different flag for a different job.

One correction that fell out of building the fixture, and it matters: **a one-way
wall flagged on one side only is not a cut.** The flag lives on a wall, not on
the pair, so the partner wall is still open and a viewer on the far side floods
back out and reaches both halves anyway. The graph here is therefore directed,
and the question is whether any sector is a common *ancestor*.

Door state
----------

The cut has to hold with every moving sector open. It does, and by construction
rather than by luck: Blood's moving sectors are translated and rotated by
`TranslateSector` (blood/src/triggers.cpp), which moves wall *coordinates* and
never `nextsector` or `cstat`. The portal graph and every flag in it are
identical whether a door is open or shut, so this check is door-state
independent.

The one thing that is *not* invariant is the overlap set itself: a sliding sector
can slide over something it did not overlap at rest. Overlaps here are computed
at rest, and that is a stated limit rather than a claim.

Room-over-room
--------------

A linked pair is exempt, and not by special pleading: `mirrors.cpp` draws the far
side of a link in its own pass, not through `scansector` at all. Its two halves
are meant to be seen together -- that is what the mirror tile is for.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from .planar_geom import same_ground, loops_equivalent, polygon_relation

#: build/include/buildtypes.h:154. The only flag that cuts the flood.
CSTAT_WALL_1WAY = 1 << 5

#: build/src/polymost.cpp:6698. `d*d < |wall|^2 * 256` is a perpendicular
#: distance of 16 Build units: inside that a neighbour is collected whatever way
#: the viewer faces. Recorded because it is why no facing direction is ever
#: assumed here, not because it is used as a threshold.
NEAR_PLANE_UNITS = 16

#: The footprint relations that mean two sectors genuinely share ground.
OVERLAPPING_KINDS = frozenset({
    "partial_area_overlap",
    "full_containment_a_in_b",
    "full_containment_b_in_a",
    "identical_footprint",
})

#: warp.cpp:110. Marker types that make a pair a room-over-room link.
LINK_MARKER_TYPES = frozenset({6, 7, 9, 10, 11, 12, 13, 14})

#: What can make an overlap safe. `uncut` is the refusal.
#:
#: `band_separated` is not a cut and is listed last of the safe ones on purpose:
#: it does not stop the renderer reaching both, it stops the *engine confusing*
#: them. `updatesectorz_compat` (build/src/engine.cpp:13454) disambiguates a cold
#: lookup by z through `inside_z_p` (build/include/build.h:1733), and a portal
#: passes only the height its two sectors share, so two sectors whose bands do
#: not meet cannot be taken for each other and cannot be drawn through one
#: another vertically.
#:
#: It has to be here because it is what Blood actually does. Cuts account for
#: 10.8% of the campaign's overlapping pairs and one of the two kinds is a single
#: map's idiom; everything else is bands and distance. A checker that called the
#: other 89% unsafe would be measuring its own strictness.
CUTS = ("disconnection", "one_way", "link", "band_separated", "uncut")

#: The cuts that are proofs about **drawing**. Bands are not among them.
#:
#: This distinction was missing and it cost this project a great deal. Asked
#: about MALTX, `audit` called all 73 of its overlapping pairs safe, 72 of them
#: `band_separated` -- while two of those pairs were tearing the frame. Disjoint
#: z bands stop `updatesectorz_compat` confusing which sector the player is in.
#: They do nothing whatever about draw order, because the sort that decides it
#: (`wallfront`, engine.cpp:2227) has no z in it at all.
#:
#: Use `RENDER_PROOFS` when the question is what can be drawn together, and the
#: full `CUTS` when the question is where the player can be.
RENDER_PROOFS = frozenset({"disconnection", "one_way", "link"})


@dataclass(frozen=True)
class Verdict:
    """One overlapping pair, and the cut that severs it."""

    sectors: tuple[int, int]
    kind: str
    cut: str
    #: For a band-separated pair, the masonry between them in Build units.
    slab: int | None = None
    #: How many one-way walls the cut rests on. 0 is disconnection; 1 means a
    #: single wall's flag is holding it, which is worth saying out loud.
    depends_on_walls: int | None = None
    #: For a refused pair, a sector whose flood reaches both.
    witness: int | None = None

    @property
    def safe(self) -> bool:
        """Safe for *movement*: the engine cannot put the player in the wrong one."""
        return self.cut != "uncut"

    @property
    def safe_to_draw(self) -> bool:
        """Proved never drawable together. Bands do not count; only a real cut.

        A pair that is `safe` but not `safe_to_draw` is one the player cannot be
        confused about and the renderer can still hold both of.
        """
        return self.cut in RENDER_PROOFS

    def to_dict(self) -> dict[str, Any]:
        return {
            "sectors": list(self.sectors), "kind": self.kind, "cut": self.cut,
            "slab": self.slab, "depends_on_walls": self.depends_on_walls,
            "witness": self.witness, "safe": self.safe,
            "safe_to_draw": self.safe_to_draw,
        }


# ---------------------------------------------------------------------------
# the graph
# ---------------------------------------------------------------------------

def sector_loops(disk: Any, sector_id: int) -> list[list[tuple[int, int]]]:
    """One sector's wall run split into closed loops, following `point2`.

    Inner loops come out separately, which is what stops a carved hole from
    reading as an overlap with whatever fills it.
    """
    fields = disk.sectors[sector_id].fields
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    last = min(first + count, len(disk.walls))
    loops: list[list[tuple[int, int]]] = []
    seen: set[int] = set()
    cursor = first
    while cursor < last:
        if cursor in seen:
            cursor += 1
            continue
        loop: list[tuple[int, int]] = []
        walk = cursor
        while walk not in seen and first <= walk < last:
            seen.add(walk)
            wall = disk.walls[walk].fields
            loop.append((int(wall["x"]), int(wall["y"])))
            walk = int(wall["point2"])
        if len(loop) >= 3:
            loops.append(loop)
        cursor += 1
    return loops


def flood_graph(disk: Any) -> tuple[list[set[int]], list[set[int]]]:
    """The directed graph the renderer's traversal condition allows, and its reverse.

    An edge A -> B where A owns a two-sided wall into B that is not one-way.
    Directed, because `cstat & 32` is a property of one wall: A into B can be cut
    while B into A stays open.
    """
    count = len(disk.sectors)
    forward: list[set[int]] = [set() for _ in range(count)]
    backward: list[set[int]] = [set() for _ in range(count)]
    for index in range(count):
        fields = disk.sectors[index].fields
        first = int(fields["wall_ptr"])
        walls = int(fields["wall_count"])
        for wall_id in range(first, min(first + walls, len(disk.walls))):
            wall = disk.walls[wall_id].fields
            neighbour = int(wall["next_sector"])
            if not (0 <= neighbour < count) or neighbour == index:
                continue
            if int(wall["cstat"]) & CSTAT_WALL_1WAY:
                continue          # polymost.cpp:6601 -- the flood stops here
            forward[index].add(neighbour)
            backward[neighbour].add(index)
    return forward, backward


def raw_components(disk: Any) -> list[int]:
    """Component per sector over every two-sided wall, ignoring `cstat`.

    Disconnection is about geometry that is not joined at all, so the one-way
    flag is deliberately not consulted here -- otherwise a one-way cut would be
    reported as disconnection and the two proofs would stop being distinct.
    """
    count = len(disk.sectors)
    neighbours: list[set[int]] = [set() for _ in range(count)]
    for index in range(count):
        fields = disk.sectors[index].fields
        first = int(fields["wall_ptr"])
        walls = int(fields["wall_count"])
        for wall_id in range(first, min(first + walls, len(disk.walls))):
            neighbour = int(disk.walls[wall_id].fields["next_sector"])
            if 0 <= neighbour < count and neighbour != index:
                neighbours[index].add(neighbour)
                neighbours[neighbour].add(index)
    component = [-1] * count
    label = 0
    for start in range(count):
        if component[start] != -1:
            continue
        frontier = deque([start])
        component[start] = label
        while frontier:
            node = frontier.popleft()
            for other in neighbours[node]:
                if component[other] == -1:
                    component[other] = label
                    frontier.append(other)
        label += 1
    return component


def _reach(graph: list[set[int]], start: int) -> set[int]:
    out = {start}
    frontier = deque([start])
    while frontier:
        node = frontier.popleft()
        for other in graph[node]:
            if other not in out:
                out.add(other)
                frontier.append(other)
    return out


def one_way_depth(disk: Any, sources: set[int], targets: set[int]) -> int:
    """Fewest one-way walls on any route from `sources` to `targets`.

    A 0-1 breadth-first search over the *undirected* portal graph: an ordinary
    portal costs nothing, a one-way wall costs one. The answer is how many flags
    the separation actually rests on, so a 1 says one wall is holding it up.
    """
    count = len(disk.sectors)
    edges: list[list[tuple[int, int]]] = [[] for _ in range(count)]
    for index in range(count):
        fields = disk.sectors[index].fields
        first = int(fields["wall_ptr"])
        walls = int(fields["wall_count"])
        for wall_id in range(first, min(first + walls, len(disk.walls))):
            wall = disk.walls[wall_id].fields
            neighbour = int(wall["next_sector"])
            if not (0 <= neighbour < count) or neighbour == index:
                continue
            cost = 1 if int(wall["cstat"]) & CSTAT_WALL_1WAY else 0
            edges[index].append((neighbour, cost))
            edges[neighbour].append((index, cost))

    best = {int(s): 0 for s in sources}
    frontier = deque(sorted(sources))
    while frontier:
        node = frontier.popleft()
        if node in targets:
            return best[node]
        for other, cost in edges[node]:
            candidate = best[node] + cost
            if other not in best or candidate < best[other]:
                best[other] = candidate
                (frontier.append if cost else frontier.appendleft)(other)
    return max(best.values(), default=0)


# ---------------------------------------------------------------------------
# the overlaps
# ---------------------------------------------------------------------------

def linked_sectors(disk: Any) -> set[frozenset[int]]:
    """Room-over-room pairs, which `mirrors.cpp` draws together on purpose."""
    by_link: dict[int, list[int]] = {}
    for sprite in disk.sprites:
        fields = sprite.fields
        if int(fields["type"]) not in LINK_MARKER_TYPES:
            continue
        extra = sprite.extra
        if extra is None or not hasattr(extra, "fields"):
            continue
        by_link.setdefault(int(extra.fields.get("data_1") or 0), []).append(
            int(fields["sector"]))
    out: set[frozenset[int]] = set()
    for sectors in by_link.values():
        for index, left in enumerate(sectors):
            for right in sectors[index + 1:]:
                if left != right:
                    out.add(frozenset((left, right)))
    return out


def overlapping_pairs(disk: Any) -> list[tuple[int, int, str]]:
    """Every pair of sectors sharing ground: bbox prefilter, then real polygons."""
    count = len(disk.sectors)
    loops = [sector_loops(disk, i) for i in range(count)]
    boxes: list[tuple[int, int, int, int] | None] = []
    for shape in loops:
        if not shape:
            boxes.append(None)
            continue
        xs = [p[0] for loop in shape for p in loop]
        ys = [p[1] for loop in shape for p in loop]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))

    out: list[tuple[int, int, str]] = []
    for left in range(count):
        if boxes[left] is None:
            continue
        for right in range(left + 1, count):
            if boxes[right] is None:
                continue
            a, b = boxes[left], boxes[right]
            if a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]:
                continue
            # Same ground, corner for corner, however the two are subdivided.
            # `loops_equivalent` demands matching vertex lists, and a storey and
            # the storey over it never have those -- each has its own doorways
            # splitting its own walls. `polygon_relation` then calls the pair
            # `exactly_shared_boundary`, which is not in OVERLAPPING_KINDS, so
            # Blood's normal way of stacking space was invisible to every check
            # built on this function. `same_ground` is the corner-wise test, and
            # it is deliberately narrower than `exactly_shared_boundary`: a
            # sector filling a *hole* in another satisfies that and shares no
            # ground at all.
            if (loops_equivalent(loops[left][0], loops[right][0])
                    or same_ground(loops[left][0], loops[right][0])):
                out.append((left, right, "identical_footprint"))
                continue
            kind = str(polygon_relation(loops[left], loops[right])["kind"])
            if kind in OVERLAPPING_KINDS:
                out.append((left, right, kind))
    return out


# ---------------------------------------------------------------------------
# the check
# ---------------------------------------------------------------------------

def audit(disk: Any, pairs: list[tuple[int, int, str]] | None = None) -> list[Verdict]:
    """Name the cut that severs each overlapping pair, or refuse it."""
    found = overlapping_pairs(disk) if pairs is None else pairs
    if not found:
        return []
    _forward, backward = flood_graph(disk)
    component = raw_components(disk)
    linked = linked_sectors(disk)

    ancestors: dict[int, set[int]] = {}
    for left, right, _kind in found:
        for sector in (left, right):
            if sector not in ancestors:
                ancestors[sector] = _reach(backward, sector)

    out: list[Verdict] = []
    for left, right, kind in found:
        if frozenset((left, right)) in linked:
            out.append(Verdict((left, right), kind, "link"))
            continue
        shared = ancestors[left] & ancestors[right]
        if shared:
            slab = _band_gap(disk, left, right)
            if slab is not None and slab > 0:
                out.append(Verdict((left, right), kind, "band_separated",
                                   slab=slab, witness=min(shared)))
            else:
                out.append(Verdict((left, right), kind, "uncut",
                                   witness=min(shared)))
        elif component[left] != component[right]:
            out.append(Verdict((left, right), kind, "disconnection",
                               depends_on_walls=0))
        else:
            depth = one_way_depth(disk, ancestors[left], ancestors[right])
            out.append(Verdict((left, right), kind, "one_way",
                               depends_on_walls=depth))
    return out


def _band_gap(disk: Any, left: int, right: int) -> int | None:
    """Masonry between two sectors' height bands, or None if they interpenetrate.

    A sloped surface is not measured against: `ceilingz`/`floorz` are only its
    hinge and the real band varies across the sector, so the honest answer there
    is "cannot say" rather than a number that happens to be positive.
    """
    for sector in (left, right):
        fields = disk.sectors[sector].fields
        if int(fields.get("ceiling_heinum") or 0) or int(fields.get("floor_heinum") or 0):
            return None
    a = disk.sectors[left].fields
    b = disk.sectors[right].fields
    low = (int(a["ceiling_z"]), int(a["floor_z"]))
    high = (int(b["ceiling_z"]), int(b["floor_z"]))
    if low[0] > high[0]:
        low, high = high, low
    return high[0] - low[1]


def refused(disk: Any) -> list[Verdict]:
    """Overlapping pairs with no cut on some route between them."""
    return [item for item in audit(disk) if not item.safe]


def report(disk: Any) -> dict[str, Any]:
    verdicts = audit(disk)
    by_cut: dict[str, int] = {}
    for item in verdicts:
        by_cut[item.cut] = by_cut.get(item.cut, 0) + 1
    return {
        "$schema": "llmapper.overlap-visibility",
        "overlapping_pairs": len(verdicts),
        "by_cut": by_cut,
        "resting_on_one_wall": [
            v.to_dict() for v in verdicts
            if v.cut == "one_way" and v.depends_on_walls == 1],
        "thinnest_slab": min(
            [v.slab for v in verdicts if v.slab is not None], default=None),
        "uncut": [v.to_dict() for v in verdicts if not v.safe],
    }
