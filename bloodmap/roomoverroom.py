"""One room over another, built from one declaration.

Blood has no portal. `warpInit` (warp.cpp:43) collects at most one *upper* and
one *lower* link marker per sector and pairs them by the link id in their
XSprite's ``data_1``; `CheckLink` (warp.cpp:183) then moves anything that
crosses the threshold plane into the partner's sector, translating it by

    x += lower.x - upper.x
    y += lower.y - upper.y

That is the whole boundary: a translation at a plane. The playtest bot's
room-over-room model in the NBlood submodule arrived at the same description
from the other end, and navigates E1M1 with it.

What the corpus says
--------------------

Mining all 43 campaign maps -- 251 paired links, in
``knowledge/blood/design/stacks-v1.json`` -- separates two things that are
usually spoken of as one::

    family   pairs   maps   congruent   overlaps in plan   median offset
    water      191     24         77%                 7%         81.3 pw
    stack       38     20         61%                66%          0.8 pw
    link        22     12         68%                32%         60.0 pw

A **water** link is a congruent copy of the room parked far away in free map
space, dived into. A **stack** is the same footprint in the same place, one room
directly above another. They are opposite geometries and only the second is
room-over-room in the sense people mean.

Four things are unanimous across all 38 stack pairs -- and across all 502 link
markers of every family -- and are therefore built in here rather than offered as
options:

* every marker sits on **statnum 0**, the decoration list. This one is fatal
  rather than stylistic: `PropagateMarkerReferences` (db.cpp:681, called from
  `dbLoadMap` at db.cpp:1325) walks `kStatMarker` -- statnum 10 -- and deletes
  every sprite on it that is not an Off, On, Axis or WarpDest marker. A link
  marker put there is destroyed before `warpInit` (blood.cpp:750) can pair it,
  and the result is a stack with its mirror tiles and no link at all: the floor
  stays solid and the room below is never drawn. This module shipped statnum 10
  until the first map that actually used it was walked in the engine.
* the upper sector's **floor** picnum and the lower sector's **ceiling** picnum
  are both **504**, `kMirrorTile`. This is what `IsRorSector` looks at, and it
  is the only reason the other side is drawn at all -- without it the link still
  moves the player and they cross it blind.
* both markers carry an **XSprite**; `warpInit` does not collect a marker
  without one.
* the two markers share a **link id**, and it must be unique in the map --
  `warpInit` matches on ``data_1`` alone, across families, so a stack and a pool
  sharing an id will pair with each other.

Congruence is *not* unanimous -- 15 of the 38 pairs have differently shaped
sectors -- so it is checked and warned about rather than required. What the
boundary needs is that the part you can walk over lines up, not that the whole
outline does.
"""

from __future__ import annotations

from typing import Any

#: mirrors.cpp:37. The tile that makes a surface see-through.
MIRROR_TILE = 504

#: warp.cpp:110. Upper markers, by what they do at the threshold.
MARKER_UP_LINK, MARKER_LOW_LINK = 7, 6
MARKER_UP_WATER, MARKER_LOW_WATER = 9, 10
MARKER_UP_STACK, MARKER_LOW_STACK = 11, 12
MARKER_UP_GOO, MARKER_LOW_GOO = 13, 14

#: Markers live on the **decoration** list, statnum 0, and this is load-bearing.
#:
#: `PropagateMarkerReferences` (db.cpp:681) walks every sprite on `kStatMarker`
#: -- statnum 10 -- and `DeleteSprite`s any whose type is not one of kMarkerOff,
#: kMarkerAxis, kMarkerWarpDest or kMarkerOn. Link markers are none of those, so
#: a stack marker parked on statnum 10 is destroyed during `dbLoadMap`, at
#: db.cpp:1325, before `warpInit` runs at blood.cpp:750 and can pair it.
#:
#: The symptom is a room-over-room pair that has its mirror tiles and no link:
#: the floor stays solid, the other side is never drawn, and nothing in the map
#: file looks wrong. This module carried statnum 10 for as long as it had never
#: built a map.
#:
#: All 502 link markers in the campaign are on statnum 0, across all four
#: families, without exception.
MARKER_STATNUM = 0

#: 486 of the campaign's 502 link markers carry exactly this; `warpInit` then
#: ors in 32768 and clears 257 itself (warp.cpp:113).
MARKER_CSTAT = 128

#: The editor's own marker tiles, unanimous across all four families and all
#: 502 markers: the upper of a pair is 2332 and the lower is 2331.
MARKER_TILE_UPPER = 2332
MARKER_TILE_LOWER = 2331


class StackError(ValueError):
    """A room-over-room pair the engine would not build."""


def align_lower_mouth(layout: Any, upper_region: str, lower_region: str,
                      *, recess: int = 2048) -> tuple[int, int]:
    """Fit a lower ROR mouth to the air around it.

    A mirror floor is a threshold, not a second low ceiling: the lower mouth's
    roof may be raised to its neighbouring sector roof, but never left below
    it.  Its floor is kept at least ``recess`` units below neighbouring floors,
    which makes a drop read as a shallow landing (and leaves room for water or
    a damage volume) instead of a lip above the tunnel.  With no overlapping
    lower-layer neighbour the historical upper-floor plane is retained.
    """
    upper = layout.regions[upper_region]
    lower = layout.regions[lower_region]

    def bbox(region: Any) -> tuple[int, int, int, int]:
        xs = [int(point[0]) for point in region.outer]
        ys = [int(point[1]) for point in region.outer]
        return min(xs), min(ys), max(xs), max(ys)

    lx0, ly0, lx1, ly1 = bbox(lower)
    neighbours = []
    for region_id, region in layout.regions.items():
        # The stack partner overlaps the lower region by construction; it is
        # the plane being met, not a co-planar neighbour to stay clear of.
        if region_id in (lower_region, upper_region):
            continue
        if getattr(region, "layer", None) != getattr(lower, "layer", None):
            continue
        x0, y0, x1, y1 = bbox(region)
        if max(lx0, x0) < min(lx1, x1) and max(ly0, y0) < min(ly1, y1):
            neighbours.append(region)

    ceiling = int(upper.floor_z)
    floor = int(lower.floor_z)
    if neighbours:
        ceiling = min(ceiling, min(int(region.ceiling_z) for region in neighbours))
        floor = max(floor, max(int(region.floor_z) for region in neighbours) + int(recess))
        if floor <= ceiling:
            floor = ceiling + max(1, int(recess))
    lower.ceiling_z = ceiling
    lower.floor_z = floor
    return ceiling, floor


FAMILIES = {
    "stack": (MARKER_UP_STACK, MARKER_LOW_STACK),
    "water": (MARKER_UP_WATER, MARKER_LOW_WATER),
    "goo": (MARKER_UP_GOO, MARKER_LOW_GOO),
    "link": (MARKER_UP_LINK, MARKER_LOW_LINK),
}


def room_over_room(layout: Any, stack_id: str, upper_region: str,
                   lower_region: str, *, link_id: int, at: tuple[int, int],
                   family: str = "stack") -> dict[str, Any]:
    """Stack `lower_region` under `upper_region` and open the floor between them.

    `at` is where both markers stand. Putting them at the same point makes the
    translation zero, which is what an in-place stack wants: the player steps
    through the hole and comes out directly below. A non-zero offset is legal
    and is how the water links are built, but for a stack it means the room
    below is not where the room above says it is.

    Returns what it built, so a caller can wire more to the same pair.
    """
    if family not in FAMILIES:
        raise StackError(
            f"{stack_id}: unknown family {family!r}; "
            f"known: {', '.join(sorted(FAMILIES))}")
    upper_type, lower_type = FAMILIES[family]

    for region_id in (upper_region, lower_region):
        if region_id not in layout.regions:
            raise StackError(f"{stack_id}: unknown region {region_id!r}")
    upper = layout.regions[upper_region]
    lower = layout.regions[lower_region]

    # The two rooms meet at one plane. Across the campaign's 38 stack pairs the
    # median of `lower ceiling - upper floor` is exactly **0**: the lower room's
    # ceiling *is* the upper room's floor, so `CheckLink`'s z translation comes
    # out zero and the player crosses without a step. Setting it here rather than
    # checking it removes the whole class of error where the two are a few
    # thousand apart and the crossing jolts.
    if int(lower.floor_z) <= int(upper.floor_z):
        raise StackError(
            f"{stack_id}: {lower_region} has its floor at {lower.floor_z}, which "
            f"is not below {upper_region}'s floor at {upper.floor_z}. Blood's z "
            "points down, so the room underneath needs the larger number")
    align_lower_mouth(layout, upper_region, lower_region)

    # The two surfaces the stack looks through. Unanimous across the corpus.
    upper.floor_picnum = MIRROR_TILE
    lower.ceiling_picnum = MIRROR_TILE

    # The overlap is the point, so it has to be declared or the layout audit
    # refuses two regions standing on the same ground.
    # The kind is the family name, which is what the geometry audit looks for
    # when it decides that two sectors sharing an exact reversed boundary are a
    # stack rather than an infinitely thin partition.
    layout.declare_special(upper_region, lower_region, family)

    markers = {}
    for tag, region_id, marker_type, tile, z in (
        ("upper", upper_region, upper_type, MARKER_TILE_UPPER, int(upper.floor_z)),
        ("lower", lower_region, lower_type, MARKER_TILE_LOWER, int(lower.ceiling_z)),
    ):
        placement_id = f"{stack_id}_{tag}"
        layout.add_sprite(
            placement_id, region_id, x=int(at[0]), y=int(at[1]), z=z,
            type=int(marker_type), status=MARKER_STATNUM, picnum=int(tile),
            cstat=MARKER_CSTAT, x_repeat=64, y_repeat=64, angle=0,
            # warpInit reads the link id out of the XSprite and skips any marker
            # that has not got one.
            behavior={"data_1": int(link_id)},
        )
        markers[tag] = placement_id

    return {
        "stack": stack_id,
        "family": family,
        "upper": upper_region,
        "lower": lower_region,
        "link_id": int(link_id),
        "markers": markers,
        "translation": [0, 0],
        "basis": (
            "all 38 campaign stack pairs put tile 504 on both surfaces; "
            "warp.cpp:43 warpInit pairs by XSprite data_1"
        ),
    }


def congruence(layout: Any, upper_region: str, lower_region: str,
               tolerance: int = 16) -> bool:
    """Are the two outlines the same shape in the same place?

    Not required -- 15 of the campaign's 38 stack pairs are not congruent -- but
    worth knowing, because where they differ the player can walk over a hole
    that has no room under it.
    """
    top = list(layout.regions[upper_region].outer)
    bottom = list(layout.regions[lower_region].outer)
    if len(top) != len(bottom):
        return False
    for rotation in range(len(bottom)):
        turned = bottom[rotation:] + bottom[:rotation]
        if all(abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance
               for a, b in zip(top, turned)):
            return True
    return False
