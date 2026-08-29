"""Detail at volume: the small sectors a Blood level is mostly made of.

A room is not what makes a level. **68% of E1M1's sectors are under 20 player
widths squared and 40 of them are under 4** -- it is roughly 46 real spaces and
roughly 100 small ones, and the small ones are what the player actually walks
past. Mined across the campaign, those small sectors sort into seven kinds with
a stable population per map:

===========  =============  ===========================================
kind          per map (med)  what it is
===========  =============  ===========================================
junction               47    three or more ways meet, and a cycle closes
link                   45    a short run between two spaces
alcove                 39    a dead end cut into one wall
arch                   18    a lowered ceiling between two spaces
bay                    12    a niche opening onto two spaces that touch
tread                  11    a step
branch                 10    three or more ways meet, no cycle
===========  =============  ===========================================

`vocabulary.recess` already builds one alcove. Building thirty-nine of them one
call at a time is why this level had five. These constructors take a wall and
put a *run* of detail along it, so the unit of authoring is the wall rather than
the niche -- which is how the density gets to be campaign-like without thirty
hand-written regions per room.

The bands come from `tools/mine_prefabs.py` and are stated where they are used.
"""

from __future__ import annotations

from math import atan2, ceil, hypot, pi
from typing import Any, Iterable

from .planar_layout import PlanarLayout
from .vocabulary import Anchor, VocabularyError, recess

PLAYER_WIDTH = 384


class PrefabError(ValueError):
    """A prefab cannot be placed without making invalid authored geometry."""

#: Alcove footprint, from 1,793 campaign instances: area q1 0.88, median 2.67,
#: q3 7.11 player widths squared. A niche a bit over a player wide and about as
#: deep lands on the median.
ALCOVE_WIDTH = 2 * PLAYER_WIDTH
ALCOVE_DEPTH = PLAYER_WIDTH

#: How far apart to space them along a wall. Wide enough that the piers between
#: read as piers rather than as gaps.
ALCOVE_PITCH = 4 * PLAYER_WIDTH

#: A third of campaign alcoves lower their ceiling; two thirds keep the host's
#: floor. `recess` already defaults to a flush floor, so only the drop is named.
ALCOVE_CEILING_DROP = 2048

#: How often a niche gets its back corners cut. 42% of the campaign's 1,793
#: alcoves carry at least one diagonal wall, and this level's carried none --
#: which is most of why its share of non-axis-aligned walls sat at 0.22 against
#: a campaign q1 of 0.27. A chamfer costs no extra wall (the outline is still
#: four points) and is the difference between a niche and a dent.
CHAMFER_SHARE = 0.42

#: How far in the back corners are cut, as a fraction of the mouth.
CHAMFER_FRACTION = 0.3


def wall_in_winding_order(layout: PlanarLayout, region_id: str,
                          a: tuple[int, int], b: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return the two points in the host's own outline order.

    Which way a niche is cut depends on the anchor's direction, because the
    offset follows the inward normal -- so the same two points build a niche in
    the wall or a niche in the middle of the room depending on the order they
    are given in. That is not a decision an author should be making; the region's
    outline already says which way round its walls go.

    A wall that is not a segment of the region's outer loop -- because it is a
    portal, or because the points are not both on it -- is returned unchanged and
    left to the compiler to reject, which it does clearly.
    """
    region = layout.regions.get(region_id)
    if region is None:
        raise VocabularyError(f"unknown region {region_id!r}")
    outer = list(region.outer)
    for index, point in enumerate(outer):
        nxt = outer[(index + 1) % len(outer)]
        if (tuple(point), tuple(nxt)) == (tuple(a), tuple(b)):
            return a, b
        if (tuple(point), tuple(nxt)) == (tuple(b), tuple(a)):
            return b, a
    # Not a whole outline edge: fall back to whichever endpoint comes first
    # along the loop, which is right for a sub-segment of a longer wall.
    for index, point in enumerate(outer):
        nxt = outer[(index + 1) % len(outer)]
        if _on_segment(point, nxt, a) and _on_segment(point, nxt, b):
            first = _along(point, nxt, a)
            second = _along(point, nxt, b)
            return (a, b) if first <= second else (b, a)
    return a, b


def _along(p: tuple[int, int], q: tuple[int, int], x: tuple[int, int]) -> float:
    dx, dy = q[0] - p[0], q[1] - p[1]
    length = dx * dx + dy * dy
    if not length:
        return 0.0
    return ((x[0] - p[0]) * dx + (x[1] - p[1]) * dy) / length


def _on_segment(p: tuple[int, int], q: tuple[int, int], x: tuple[int, int],
                *, tolerance: int = 2) -> bool:
    cross = (q[0] - p[0]) * (x[1] - p[1]) - (q[1] - p[1]) * (x[0] - p[0])
    span = hypot(q[0] - p[0], q[1] - p[1]) or 1.0
    if abs(cross) / span > tolerance:
        return False
    t = _along(p, q, x)
    return -0.001 <= t <= 1.001


def _lerp(a: tuple[int, int], b: tuple[int, int], t: float) -> tuple[int, int]:
    return (int(round(a[0] + (b[0] - a[0]) * t)),
            int(round(a[1] + (b[1] - a[1]) * t)))


def alcove_run(
    layout: PlanarLayout,
    structure_id: str,
    *,
    region_id: str,
    a: tuple[int, int],
    b: tuple[int, int],
    count: int | None = None,
    width: int = ALCOVE_WIDTH,
    depth: int = ALCOVE_DEPTH,
    pitch: int = ALCOVE_PITCH,
    ceiling_drop: int = ALCOVE_CEILING_DROP,
    margin: float = 0.5,
    **surface: Any,
) -> list[str]:
    """Cut a row of niches into one wall of a region.

    `a` and `b` are the wall, in the host's winding order, so the niches face
    into the room. `count` defaults to as many as fit at `pitch`, keeping
    `margin` pitches clear at each end so the run does not collide with whatever
    is at the corners.

    Returns the structure ids built, which may be fewer than asked for if the
    wall is short -- a wall that fits none is not an error, it is a short wall.
    """
    a, b = wall_in_winding_order(layout, region_id, a, b)
    span = hypot(b[0] - a[0], b[1] - a[1])
    if span <= 0:
        raise VocabularyError(f"{structure_id}: the wall has no length")
    usable = span - 2 * margin * pitch
    fits = int(usable // pitch) + 1 if usable >= 0 else 0
    wanted = fits if count is None else min(count, fits)
    if wanted <= 0:
        return []

    # Skip a niche that would land in something already there. These walls are
    # rarely blank: a doorway, a stair, or the next room along is behind part of
    # most of them, and an author who has to know which parts is back to placing
    # niches one at a time. The compiler would reject the collision anyway --
    # this just declines to make it.
    occupied = [
        list(other.outer) for name, other in layout.regions.items()
        if name != region_id
    ]
    # And do not cut a niche behind something already hung on this wall. A
    # recess moves the wall face back by its depth, so a torch or a sconce that
    # was against it is left floating in front of the opening -- which is what
    # happened to six of this level's decorations the first time these runs were
    # added. The mounted sprite has priority: it was placed deliberately, and
    # the niche is one of a row.
    mounted = _wall_mounted_points(layout, region_id)
    # And do not cut a niche across a span the room already opens through. A
    # doorway is not a region that overlaps the niche -- it is a *connection*
    # sharing the same stretch of wall -- so the footprint test above cannot see
    # it, and the compiler reports the result as an unpaired portal rather than
    # as an overlap.
    # Projected onto the run's own axis, so a doorway that only partly overlaps a
    # niche is still caught. Testing whether the mouth lies inside the doorway
    # missed exactly that case.
    spoken_for: list[tuple[float, float]] = []
    for conn in layout.connections.values():
        if not (conn.a1 and conn.a2):
            continue
        if region_id not in (conn.region_a, conn.region_b):
            continue
        if not (_on_segment(a, b, tuple(conn.a1), tolerance=8)
                and _on_segment(a, b, tuple(conn.a2), tolerance=8)):
            continue
        lo = _along(a, b, tuple(conn.a1))
        hi = _along(a, b, tuple(conn.a2))
        spoken_for.append((min(lo, hi), max(lo, hi)))

    built: list[str] = []
    skipped = 0
    # Centre the run on the wall rather than starting at one end, so a wall that
    # fits three niches puts them symmetrically instead of crowding one corner.
    used = (wanted - 1) * pitch
    start = (span - used) / 2.0
    for index in range(wanted):
        centre = (start + index * pitch) / span
        half = (width / 2.0) / span
        low, high = centre - half, centre + half
        if low <= 0.0 or high >= 1.0:
            continue
        mouth_a, mouth_b = _lerp(a, b, low), _lerp(a, b, high)
        if _would_collide(layout, region_id, mouth_a, mouth_b, depth, occupied):
            skipped += 1
            continue
        if _carries_a_sprite(mouth_a, mouth_b, mounted):
            skipped += 1
            continue
        if any(low < hi and high > lo for lo, hi in spoken_for):
            skipped += 1
            continue
        tag = f"{structure_id}_{index:02d}"
        # Deterministic rather than random: the same layout must compile to the
        # same bytes, and a chamfer chosen by index is as unpatterned as one
        # chosen by chance over a run of three or four.
        if ((index * 7 + 3) % 10) / 10.0 < CHAMFER_SHARE:
            _chamfered_niche(layout, tag, region_id, mouth_a, mouth_b,
                             depth=depth, ceiling_drop=ceiling_drop, **surface)
            built.append(tag)
            continue
        recess(
            layout, tag,
            anchor=Anchor(region_id, _lerp(a, b, low), _lerp(a, b, high)),
            depth=depth, ceiling_drop=ceiling_drop, role="detail",
            intent={"purpose": f"niche in {region_id}", "classification": "OPTIONAL"},
            **surface,
        )
        built.append(tag)
    return built


def _chamfered_niche(layout: PlanarLayout, tag: str, region_id: str,
                     mouth_a: tuple[int, int], mouth_b: tuple[int, int], *,
                     depth: int, ceiling_drop: int,
                     chamfer: float = CHAMFER_FRACTION, **surface: Any) -> None:
    """A niche whose back corners are cut, so two of its walls run diagonally."""
    from .planar_geom import area2

    host = layout.regions[region_id]
    far = Anchor(region_id, mouth_a, mouth_b).offset(depth)
    span = hypot(mouth_b[0] - mouth_a[0], mouth_b[1] - mouth_a[1]) or 1.0
    ux = (mouth_b[0] - mouth_a[0]) / span
    uy = (mouth_b[1] - mouth_a[1]) / span
    cut = span * chamfer
    far_a = (int(round(far.a[0] + ux * cut)), int(round(far.a[1] + uy * cut)))
    far_b = (int(round(far.b[0] - ux * cut)), int(round(far.b[1] - uy * cut)))
    outline = [mouth_a, far_a, far_b, mouth_b]
    if area2(tuple(outline)) < 0:
        outline = [mouth_b, far_b, far_a, mouth_a]
    layout.add_region(
        f"region:{tag}", outline, role="detail",
        floor_z=host.floor_z, ceiling_z=host.ceiling_z + ceiling_drop,
        intent={"purpose": f"chamfered niche in {region_id}",
                "classification": "OPTIONAL"},
        **surface)
    layout.add_connection(
        f"connection:{tag}:mouth", region_id, f"region:{tag}",
        a1=mouth_a, a2=mouth_b, min_width=max(512, int(span)))


def _wall_mounted_points(layout: PlanarLayout, region_id: str) -> list[tuple[float, float]]:
    """Where this region's wall-mounted placements sit, before compilation.

    A wall placement is stored as its anchor and a fraction along it, so the
    point can be worked out without compiling -- which matters, because the
    niches have to be decided while the layout is still being built.
    """
    points: list[tuple[float, float]] = []
    for placement in layout.placements:
        if placement.region_id != region_id:
            continue
        anchor = placement.anchor or {}
        if anchor.get("kind") != "wall":
            continue
        a1 = anchor.get("a1")
        a2 = anchor.get("a2")
        if not a1 or not a2:
            continue
        t = float(anchor.get("t") or 0.5)
        points.append((a1[0] + (a2[0] - a1[0]) * t, a1[1] + (a2[1] - a1[1]) * t))
    return points


def _carries_a_sprite(mouth_a: tuple[int, int], mouth_b: tuple[int, int],
                      mounted: list[tuple[float, float]],
                      *, margin: int = PLAYER_WIDTH // 2) -> bool:
    """Whether a mounted sprite sits within this mouth, or just beside it."""
    for x, y in mounted:
        along = _along(mouth_a, mouth_b, (int(x), int(y)))
        span = hypot(mouth_b[0] - mouth_a[0], mouth_b[1] - mouth_a[1]) or 1.0
        slack = margin / span
        if -slack <= along <= 1.0 + slack and _on_segment(
                mouth_a, mouth_b, (int(x), int(y)), tolerance=margin):
            return True
    return False


def _would_collide(layout: PlanarLayout, region_id: str,
                   mouth_a: tuple[int, int], mouth_b: tuple[int, int],
                   depth: int, occupied: list[list[tuple[int, int]]]) -> bool:
    """Whether the niche this anchor would cut overlaps an existing region.

    Point probes alone are not enough. Two rectangles can overlap in a corner
    with neither's sampled interior points falling inside the other, and that is
    exactly what slipped past the first version -- a niche clipping the corner of
    an existing one. Containment *and* edge crossing are both needed: the first
    catches one shape inside another, the second catches them merely meeting.
    """
    from .exposure import _point_in_loop
    from .planar_geom import proper_crossing

    far = Anchor(region_id, mouth_a, mouth_b).offset(depth)
    corners = [mouth_a, far.a, far.b, mouth_b]
    centre = (sum(p[0] for p in corners) // 4, sum(p[1] for p in corners) // 4)
    probes = [centre] + [
        ((p[0] + centre[0]) // 2, (p[1] + centre[1]) // 2) for p in corners
    ]
    edges = [(corners[i], corners[(i + 1) % 4]) for i in range(4)]
    for loop in occupied:
        if any(_point_in_loop(probe[0], probe[1], loop) for probe in probes):
            return True
        for index, point in enumerate(loop):
            nxt = loop[(index + 1) % len(loop)]
            if any(proper_crossing(p, q, point, nxt) for p, q in edges):
                return True
            # a loop vertex sitting inside the niche is an overlap the crossing
            # test misses when one shape is wholly inside the other
            if _point_in_loop(point[0], point[1], corners):
                return True
    return False


def alcove_capacity(a: tuple[int, int], b: tuple[int, int], *,
                    pitch: int = ALCOVE_PITCH, margin: float = 0.5) -> int:
    """How many niches this wall would take, without building any."""
    span = hypot(b[0] - a[0], b[1] - a[1])
    usable = span - 2 * margin * pitch
    return max(0, int(usable // pitch) + 1) if usable >= 0 else 0


#: Blood's breakable props, and the single biggest gap between this level and a
#: real one: E1M1 carries **183** of them against this level's 3, and the
#: campaign runs a median of 33 per 100 playable sectors. They are what a room
#: is full of -- the thing you shoot for the ammo behind it.
#:
#: 416 is `kThingObjectGib`, which breaks apart; 417 is `kThingObjectExplode`,
#: which does not. Both sit on statnum 4, kStatThing, and both need `data_1`:
#: it names the gib or explosion, and a prop without one breaks into nothing.
#: The forms below are the campaign's modal ones for their tile, from 80, 78 and
#: 63 instances respectively.
BREAKABLES = {
    "urn": dict(type=416, picnum=759, status=4, cstat=385,
                x_repeat=48, y_repeat=48, behavior={"data_1": 1, "data_4": 301}),
    "crate": dict(type=416, picnum=574, status=4, cstat=385,
                  x_repeat=40, y_repeat=40, behavior={"data_1": 1, "data_4": 301}),
    "barrel": dict(type=417, picnum=1167, status=4, cstat=224,
                   x_repeat=64, y_repeat=64, behavior={"data_1": 21}),
}

#: Things per 100 playable sectors: campaign median 33, q1 15, q3 56.
THINGS_PER_100_SECTORS = 33


def breakable(kind: str, *, shade: int = -8) -> dict[str, Any]:
    """One breakable prop, in the campaign's modal form for its tile."""
    try:
        spec = dict(BREAKABLES[kind])
    except KeyError:
        raise VocabularyError(
            f"unknown breakable {kind!r}; have {sorted(BREAKABLES)}") from None
    spec["behavior"] = dict(spec["behavior"])
    spec["shade"] = shade
    return spec


# ---------------------------------------------------------------------------
# Sprite bridges
# ---------------------------------------------------------------------------
#
# A floor-aligned sprite with the blocking bit set is a floor. Build's clipping
# treats it as a surface at its own z, so a run of them is a walkway with nothing
# underneath -- which is how Death Wish crosses a chasm without building one.
#
# DWE1M1 has the clearest example: sector 431 carries nineteen slabs of tile 256
# at cstat 417, over a floor **83 player heights** below them. The numbers that
# matter are not obvious from looking at it:
#
# * **cstat 417** -- blocking (1), floor-aligned (32), centred (128) and
#   hitscan-blocking (256). Drop the 1 and it is scenery you fall through.
# * **repeat 48/48** on a 128-pixel tile, so each slab is drawn 1536 square,
#   four player widths.
# * each panel reaches exactly to the next one.  They meet at an edge, but must
#   never cover the same area: coincident floor sprites shimmer and can give
#   Build's renderer ambiguous draw order.
# * each slab shaded separately -- DWE1M1's run spans shade 14 to 27 -- so the
#   bridge has length to it rather than reading as one flat plane.

#: The campaign's own slab: a 128x128 stone panel.
BRIDGE_TILE = 256

#: Blocking, floor-aligned, centred, hitscan-blocking.
BRIDGE_CSTAT = 1 | 32 | 128 | 256

#: A floor-aligned sprite's footprint is ``repeat * tile_pixels / 4``.  The
#: plane has the same XY scale as a wall sprite; confusing it with texture
#: coverage (/8) halves the calculated square, making adjacent bridge panels
#: overlap by half their real width.  At repeat 48 on a 128-pixel tile the
#: footprint is 1536 units.
FLOOR_SPRITE_DIVISOR = 4.0

#: Bridge panels touch edge-to-edge.  A fractional pitch used to make them
#: overlap, which is not valid for floor-aligned sprites.  Kept as an explicit
#: argument so old call sites fail loudly rather than silently recreating the
#: bad geometry.
BRIDGE_OVERLAP = 1.0
STEPPING_STONE_PITCH = 1.88


def _bridge_footprint(cx: float, cy: float, ux: float, uy: float,
                      width: float) -> tuple[tuple[int, int], ...]:
    """Return the four Build-grid corners of a square floor sprite."""
    half = width / 2.0
    px, py = -uy, ux
    return tuple(
        (int(round(cx + sx * ux * half + sy * px * half)),
         int(round(cy + sx * uy * half + sy * py * half)))
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
    )


def _bridge_is_inside_host(layout: PlanarLayout, region_id: str,
                           footprint: tuple[tuple[int, int], ...]) -> bool:
    """Whether a sprite square is strictly clear of the host walls and holes."""
    from .planar_geom import classify_segment_pair, point_in_loops

    host = layout.regions[region_id]
    loops = (host.outer, *host.holes)
    if any(point_in_loops(point, loops) != 1 for point in footprint):
        return False
    edges = tuple(zip(footprint, footprint[1:] + footprint[:1]))
    for loop in loops:
        host_edges = tuple(zip(loop, loop[1:] + loop[:1]))
        for a, b in edges:
            for c, d in host_edges:
                if classify_segment_pair(a, b, c, d) is not None:
                    return False
    return True


def _bridge_slabs_overlap(left: dict[str, float], right: dict[str, float],
                          ux: float, uy: float) -> bool:
    """True only for a positive-area overlap; a common edge is allowed."""
    dx, dy = right["x"] - left["x"], right["y"] - left["y"]
    along = abs(dx * ux + dy * uy)
    across = abs(-dx * uy + dy * ux)
    return (along < (left["width"] + right["width"]) / 2.0 - 1e-6
            and across < (left["width"] + right["width"]) / 2.0 - 1e-6)


def sprite_bridge(layout, bridge_id, region_id, *, start, end, z,
                  tile=BRIDGE_TILE, repeat=48, tile_width=128,
                  overlap=BRIDGE_OVERLAP, shade_from=14, shade_to=27,
                  angle=None, quarter_turn=False):
    """Lay a walkway of blocking floor-aligned sprites from `start` to `end`.

    The angle comes from the run unless one is given. A floor-aligned sprite's
    angle turns it in the floor plane, so a slab laid at 0 on a bridge running
    north is a quarter turn out -- which is what the first version of this did,
    and it is obvious from standing on it and invisible from the map file.
    `quarter_turn` adds 90 degrees, for a tile whose planking wants to lie
    across the walkway rather than along it.

    ``start`` and ``end`` are the outside edges of the complete deck, not its
    first and last sprite centres.  Every panel is preflighted against the host
    region, including its holes, and panels may share an edge but never area.

    Returns the placement ids. The caller is responsible for there being
    somewhere to fall: a bridge over a floor is just a rug.
    """
    (ax, ay), (bx, by) = start, end
    dx, dy = bx - ax, by - ay
    span = hypot(dx, dy)
    if span <= 0:
        raise PrefabError(f"{bridge_id}: bridge has no length")
    if region_id not in layout.regions:
        raise PrefabError(f"{bridge_id}: unknown host region {region_id!r}")
    if int(repeat) != repeat or int(repeat) <= 0:
        raise PrefabError(f"{bridge_id}: repeat must be a positive integer")
    repeat = int(repeat)
    if int(tile_width) != tile_width or int(tile_width) <= 0:
        raise PrefabError(f"{bridge_id}: tile_width must be a positive integer")
    tile_width = int(tile_width)
    if abs(overlap - BRIDGE_OVERLAP) > 1e-9:
        raise PrefabError(
            f"{bridge_id}: overlapping floor sprites are forbidden; use a "
            "separate stepping-stone prefab for gaps")
    if angle is None:
        # Build angles: 0 is +x, 512 is +y, 1024 is -x, 1536 is -y.
        angle = int(round(atan2(by - ay, bx - ax) * 1024.0 / pi)) % 2048
    if quarter_turn:
        angle = (angle + 512) % 2048
    unit = tile_width / FLOOR_SPRITE_DIVISOR
    total_repeats = int(round(span / unit))
    if total_repeats <= 0 or abs(span - total_repeats * unit) > 1e-6:
        raise PrefabError(
            f"{bridge_id}: span {span:g} cannot be tiled exactly by "
            f"{unit:g}-unit floor-sprite texels")
    # Distribute integer repeats across the panels.  This makes the complete
    # deck terminate exactly on start/end, leaving neither a seam nor a
    # coincident strip at a join.
    count = max(1, ceil(total_repeats / repeat))
    base_repeat, extra = divmod(total_repeats, count)
    ux, uy = dx / span, dy / span
    panels: list[dict[str, float]] = []
    cursor = 0.0
    for index in range(count):
        panel_repeat = base_repeat + (1 if index < extra else 0)
        width = panel_repeat * unit
        distance = cursor + width / 2.0
        panels.append({
            "repeat": float(panel_repeat), "width": width,
            "x": ax + ux * distance, "y": ay + uy * distance,
            "t": distance / span,
        })
        cursor += width
    if abs(cursor - span) > 1e-6:
        raise PrefabError(f"{bridge_id}: panel layout did not cover its span")
    for index, panel in enumerate(panels):
        footprint = _bridge_footprint(panel["x"], panel["y"], ux, uy,
                                      panel["width"])
        if len(set(footprint)) != 4 or not _bridge_is_inside_host(
                layout, region_id, footprint):
            raise PrefabError(
                f"{bridge_id}: panel {index} intersects a host wall or hole")
        if index and _bridge_slabs_overlap(panels[index - 1], panel, ux, uy):
            raise PrefabError(f"{bridge_id}: panels {index - 1} and {index} overlap")
    out = []
    for index, panel in enumerate(panels):
        shade = int(round(shade_from + (shade_to - shade_from) * panel["t"]))
        placement_id = f"{bridge_id}_{index:02d}"
        layout.add_sprite(
            placement_id, region_id,
            x=int(round(panel["x"])), y=int(round(panel["y"])),
            z=int(z), type=0, status=0, picnum=int(tile), cstat=BRIDGE_CSTAT,
            x_repeat=int(panel["repeat"]), y_repeat=int(panel["repeat"]), shade=shade,
            angle=int(angle),
        )
        out.append(placement_id)
    return out


# ---------------------------------------------------------------------------
# Parapets: the thing you get shot from
# ---------------------------------------------------------------------------

#: The recipe, from 309 overlooks across the eight Blood maps closest to the
#: monastery by palette (`knowledge/blood/design/overlooks-v1.json`). An
#: overlook there is a walkable sector standing 0.5 to 3.0 standing humans above
#: a space of at least five square humans.
#:
#:     rise            median 1.93 humans   q1 0.97   q3 1.93   p95 2.66
#:     head clearance  median 2.17          q1 1.75   q3 3.80
#:     depth           median 1.33 body widths          q3 3.00
#:     edge length     median 4.67 body widths          q3 8.00
#:     share of the space's perimeter    median 5%      q3 10.5%
#:
#: 1.93 humans is 32768 z, which is also the campaign's median aperture leaf and
#: four repeats of a door tile. The same number keeps arriving from different
#: directions because it is the body-scale unit Blood is built on.
PARAPET_RISE = 32768
PARAPET_DEPTH = 512
PARAPET_HEAD = 36864

#: Two habits worth building in rather than offering.
#:
#: **The lip does not block.** Only 5% of the corpus's overlooks have a blocking
#: wall along the edge they overlook. A parapet you cannot step off is a
#: balcony, and Blood mostly builds the other thing -- a walk you can drop from,
#: which is what makes it read as continuous with the space rather than as a
#: box attached to it.
#:
#: **It goes somewhere.** 89% have another way off besides the drop. An overlook
#: with one entrance is a shooting position; with two it is part of the route,
#: and the corpus overwhelmingly builds the second.
PARAPET_LIP_BLOCKS = False
PARAPET_WANTS_ANOTHER_WAY_OFF = 0.89


def parapet(
    layout: PlanarLayout,
    structure_id: str,
    *,
    anchor: Anchor,
    rise: int = PARAPET_RISE,
    depth: int = PARAPET_DEPTH,
    head: int | None = PARAPET_HEAD,
    role: str = "gameplay",
    intent: dict | None = None,
    **surface: Any,
) -> Any:
    """A raised walk along one face of a space, looking down into it.

    Built outward from `anchor`, into the mass beyond the wall, so the host
    space keeps its own footprint -- which is also how the corpus builds them,
    in the thickness of the surrounding building rather than by eating the
    courtyard.

    Returns the `Structure`, whose `far` anchor is where a stair or a door
    should attach: see `PARAPET_WANTS_ANOTHER_WAY_OFF`.
    """
    host = layout.regions.get(anchor.region_id)
    if host is None:
        raise VocabularyError(f"{structure_id}: unknown host {anchor.region_id!r}")
    if rise <= 0:
        raise VocabularyError(
            f"{structure_id}: a parapet stands above the space it overlooks; "
            f"rise must be positive")
    marks = dict(intent or {})
    marks.setdefault("purpose",
                     "raised walk overlooking %s" % anchor.region_id)
    marks.setdefault("classification", "OPTIONAL")
    # A walk over an open courtyard is usually open itself -- 38% of the
    # corpus's overlooks are -- and roofing one is not merely a style choice: a
    # roofed sector standing higher than its open neighbour puts that sector's
    # sky *below* a roof, which the engine draws as a hole in the world.
    # `head=None` gives the walk its host's ceiling, whatever that is.
    built = recess(
        layout, structure_id, anchor=anchor, depth=int(depth),
        # z points down, so standing above the host is a smaller number.
        floor_delta=-int(rise),
        clear_height=(None if head is None else int(head)),
        role=role, intent=marks,
        # The drop is the point. Leaving the mouth unblocked is what the corpus
        # does 95% of the time.
        connection={"min_width": max(512, int(anchor.width))},
        **surface,
    )
    return built
