"""Grime: decoration at the campaign's own rate, chosen by association.

This pass has been wrong three times, each time for a measurable reason,
and the corrections are worth keeping because they are all the same
mistake: reasoning from a marginal statistic instead of a joint one.

**It was far too dense.**  The first version compared "sprites per sector"
against a campaign figure of 1.60-4.06 and concluded Gravesend was
under-populated by a factor of three.  That figure counted every sprite --
actors, pickups, markers, triggers, effects -- over every sector.  Counting
what this pass actually places (decoration: statnum 0, type 0) over what it
actually dresses (rooms of at least a plan unit square and over 1.2 player
heights) gives a very different picture:

    campaign rooms      6745
      carrying grime     790  (12%)   median 2, p75 3, p90 5, max 45
      carrying a LIGHT   177  ( 3%)
    Gravesend rooms      105
      carrying grime     105  (100%)  median 2

Blood dresses **selectively and heavily**: most rooms are bare, and the
ones that are dressed get a cluster.  We dressed uniformly and lightly,
which is the opposite distribution at the same average -- and it is what
"hit and miss" looks like from inside the level.

**It drew from a third of the vocabulary.**  Of the 263 props the campaign
uses more than rarely, 142 are wall-aligned.  The old pass excluded them
because it had no wall anchor, so rooms got blood and crates where the
campaign would hang a painting, a window, a poster or a sign.

**It chose by a ceiling-tile lookup.**  Now it asks `props.props_for`,
which reads the mined joint distribution: what the campaign actually keeps
in a room made of these surfaces, gated on indoor/outdoor context.
"""

from __future__ import annotations

import hashlib

import props

PLAYER_HEIGHT = 16960

#: Rooms too small or too shallow to hold anything.
MIN_AREA = 400_000
MIN_CLEAR = 8192

#: Which face a wall-aligned prop hangs on, cycled per placement so a room
#: does not put all four paintings on one wall.
FACES = ("north", "east", "south", "west")


def _roll(seed: str, n: int) -> int:
    """A stable pseudo-random index: the same map every build."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % n


def _inside(polygon, x: float, y: float) -> bool:
    """Ray cast: is (x, y) inside this loop?"""
    hit = False
    count = len(polygon)
    for index in range(count):
        ax, ay = polygon[index]
        bx, by = polygon[(index + 1) % count]
        if (ay > y) != (by > y):
            cross = ax + (y - ay) * (bx - ax) / (by - ay)
            if cross > x:
                hit = not hit
    return hit


def _free_point(region, u: float, v: float):
    """The world point a local (u, v) names, if it is really in the room.

    `place_on_floor` resolves a local against the region's bounding box and
    does not know about its holes, so a local that lands on a bar counter or
    a stage is accepted here and fails at compile time, several thousand
    sprites later.  This does the containment test the anchor cannot.
    """
    outer = list(region.outer)
    xs = [p[0] for p in outer]
    ys = [p[1] for p in outer]
    x = min(xs) + u * (max(xs) - min(xs))
    y = min(ys) + v * (max(ys) - min(ys))
    if not _inside(outer, x, y):
        return None
    for hole in region.holes:
        if _inside(list(hole), x, y):
            return None
    return x, y


def _palette_for(region) -> str | None:
    ceiling = int(getattr(region, "ceiling_picnum", 0) or 0)
    if ceiling in BY_CEILING:
        return BY_CEILING[ceiling]
    if getattr(region, "parallax_ceiling", False):
        return "street"
    return "interior"


def dress(layout, regions=None) -> dict:
    """Dress the campaign's share of rooms, each as a coherent set."""
    report = {"dressed": 0, "bare": 0, "placed": 0, "no_association": 0,
              "wall_hung": 0, "skipped_no_room": 0, "tiles": {}}
    items = (regions if regions is not None else layout.regions).items()

    # Two passes.  A room the campaign has nothing to put in is not a
    # failed roll -- it is a room that stays bare, and it must not consume
    # the quota either.  So gather the rooms that CAN be dressed first,
    # then dress the campaign's share of all rooms out of that pool.
    dressable = []
    for region_id, region in sorted(items):
        clear = abs(int(getattr(region, "floor_z", 0))
                    - int(getattr(region, "ceiling_z", 0)))
        if clear < MIN_CLEAR:
            continue                      # doorways, and anything crawlable
        surfaces = _surfaces_of(region)
        if surfaces is None:
            continue
        # A porch is 256 units deep.  Nothing hangs in it, and a wall
        # anchor inset from both ends of a face that short is degenerate.
        rect = props.room_rect(region)
        if min(rect[2] - rect[0], rect[3] - rect[1]) < 1024:
            continue
        wall, floor, ceiling, sky = surfaces
        report["rooms"] = report.get("rooms", 0) + 1
        candidates = props.props_for(wall, floor, ceiling, sky=sky)
        if not candidates:
            report["no_association"] += 1
            report["bare"] += 1
            continue
        faces = props.solid_faces(layout, region_id, rect)
        dressable.append((region_id, region, candidates, faces,
                          props.place_id(region)))

    quota = max(1, round(props.GRIME_ROOM_SHARE * report.get("rooms", 0)))
    # Seeded from the room's PLACE, not from its region id.  A region id is
    # `"region:" + path()`, so it changes whenever the level program is
    # reorganised -- and this pass, which both sorts and rolls on it, would
    # then reshuffle every grime sprite in the city.  A restructure that
    # moves no geometry has to be provably distinguishable from a redesign,
    # and it cannot be if the sprite passes are seeded from tree position.
    # `props.place_id` is the world outline and the floor: invariant under
    # reparenting, and different the moment the room actually moves.
    dressable.sort(key=lambda row: _roll(f"{row[4]}:dress", 1_000_000))
    report["bare"] += max(0, len(dressable) - quota)

    for region_id, region, candidates, faces, place in dressable[:quota]:
        count = props.GRIME_COUNTS[
            _roll(f"{place}:count", len(props.GRIME_COUNTS))]
        put = 0
        for index in range(count):
            seed = f"{place}:{index}"
            tile = candidates[_roll(seed + ":tile", len(candidates))]
            kind = props.kind_of(tile)
            if kind in ("wall_aligned", "bracket"):
                if not faces:
                    continue        # every wall of this room is a portal
                face = faces[_roll(seed + ":face", len(faces))]
                try:
                    props.mount_on_wall(
                        layout, f"grime:{region_id}:{index}", region,
                        face, tile,
                        t=0.25 + 0.5 * (_roll(seed + ":t", 100) / 99))
                except Exception:
                    continue          # no rectangular face to hang it on
                report["wall_hung"] += 1
            else:
                local = None
                for attempt in range(8):
                    u = 0.15 + 0.7 * (_roll(f"{seed}:u{attempt}", 100) / 99)
                    v = 0.15 + 0.7 * (_roll(f"{seed}:v{attempt}", 100) / 99)
                    if _free_point(region, u, v) is not None:
                        local = (u, v)
                        break
                if local is None:
                    report["skipped_no_room"] += 1
                    continue
                props.stand_on_floor(layout, f"grime:{region_id}:{index}",
                                     region_id, local=local, tile=tile)
            put += 1
            report["tiles"][tile] = report["tiles"].get(tile, 0) + 1
        if put:
            report["dressed"] += 1
            report["placed"] += put
        else:
            report["bare"] += 1
    return report


def _surfaces_of(region):
    """This room's (wall, floor, ceiling, is_sky), or None if unreadable."""
    wall = getattr(region, "wall_picnum", None)
    floor = getattr(region, "floor_picnum", None)
    ceiling = getattr(region, "ceiling_picnum", None)
    if wall is None or floor is None or ceiling is None:
        return None
    sky = bool(getattr(region, "parallax_ceiling", False))
    return int(wall), int(floor), int(ceiling), sky
