"""Walls that carry nothing, taken out of a finished map: points on a straight run where nothing changes, and seams between pieces of one floor that came out alike.

A run is split wherever a pass needed an end on it: a light band, a neighbour
that has since gone, a texture's start. What is left when every pass has run is
often two walls with one look. `unsplit` joins them, both sides of an opening
at once, and renumbers; nothing drawn changes but a step of shade too small to
see (`SHADE_STEP`).

A point is kept where a third wall ends on it, where either wall is wired, where
the picture does not run on, and where it begins a sector whose floor or ceiling
hangs on its first wall.
"""

from __future__ import annotations

from collections import defaultdict
from math import hypot
from typing import Any, Mapping

from .model import record_extra, record_fields

#: two walls of one run whose shades differ by no more are drawn as one
SHADE_STEP = 3
#: a tile's picture may be off by so many texels across the joint
TEXELS = 1
#: no drawn wall is made longer than this: E3M1's longest
LONGEST = 8704
LOOK = ("picnum", "over_picnum", "pal", "cstat", "type", "y_repeat", "y_panning")


def _owners(disk: Any) -> list[int]:
    out = [-1] * len(disk.walls)
    for index, sector in enumerate(disk.sectors):
        f = record_fields(sector)
        for wall in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            out[wall] = index
    return out


def unsplit(disk: Any, art: Mapping[int, Any] | None = None, *, shade_step: int = SHADE_STEP) -> dict[str, int]:
    """Join the walls of a straight run that look alike; returns how many went. `art` is {tile: (width, height, ...)}."""
    walls = [record_fields(w) for w in disk.walls]
    sectors = [record_fields(s) for s in disk.sectors]
    owner = _owners(disk)
    before = {int(w["point2"]): i for i, w in enumerate(walls)}
    first = {int(s["wall_ptr"]) for s in sectors}
    ends: dict[tuple[int, int], set[int]] = defaultdict(set)
    for i, w in enumerate(walls):
        ends[int(w["x"]), int(w["y"])].add(i)
    gone: set[int] = set()
    hidden = [record_extra(s) is None and not (int(f["floor_stat"]) | int(f["ceiling_stat"])) & 2
              for s, f in zip(disk.sectors, sectors)]

    def unseen(i: int) -> bool:
        """An opening between two still sectors of one height: none of the wall is drawn."""
        w = walls[i]
        if int(w["next_sector"]) < 0 or int(w["cstat"]) & 48:
            return False
        a, b = owner[i], int(w["next_sector"])
        return (hidden[a] and hidden[b] and sectors[a]["floor_z"] == sectors[b]["floor_z"]
                and sectors[a]["ceiling_z"] == sectors[b]["ceiling_z"])

    def length(i: int) -> float:
        n = walls[int(walls[i]["point2"])]
        return hypot(int(n["x"]) - int(walls[i]["x"]), int(n["y"]) - int(walls[i]["y"]))

    def alike(p: int, q: int) -> bool:
        """Whether q's picture is p's, run on."""
        a, b = walls[p], walls[q]
        if int(a["x_repeat"]) + int(b["x_repeat"]) > 255:
            return False
        if unseen(p) and unseen(q):
            return int(a["cstat"]) == int(b["cstat"]) and int(a["type"]) == int(b["type"])
        if any(a[key] != b[key] for key in LOOK) or abs(int(a["shade"]) - int(b["shade"])) > shade_step:
            return False
        la, lb = length(p), length(q)
        if la + lb > LONGEST:
            return False
        if not la or not lb or abs(int(a["x_repeat"]) / la - int(b["x_repeat"]) / lb) > 0.06 * int(a["x_repeat"]) / la:
            return False
        tile = art.get(int(a["picnum"])) if art is not None else None
        if not tile or not tile[0]:
            return False
        wide = int(tile[0])
        off = (int(a["x_panning"]) + int(a["x_repeat"]) * 8 - int(b["x_panning"])) % wide
        return min(off, wide - off) <= TEXELS

    def straight(p: int, q: int) -> bool:
        a, b = walls[p], walls[q]
        c = walls[int(b["point2"])]
        ux, uy = int(b["x"]) - int(a["x"]), int(b["y"]) - int(a["y"])
        vx, vy = int(c["x"]) - int(b["x"]), int(c["y"]) - int(b["y"])
        return ux * vy == uy * vx and ux * vx + uy * vy > 0

    def join(p: int, q: int) -> None:
        """p takes q's length."""
        a, b = walls[p], walls[q]
        la, lb = length(p), length(q)
        a["shade"] = round((int(a["shade"]) * la + int(b["shade"]) * lb) / (la + lb))
        a["x_repeat"] = int(a["x_repeat"]) + int(b["x_repeat"])
        a["point2"] = b["point2"]
        before[int(b["point2"])] = p
        ends[int(b["x"]), int(b["y"])].discard(q)
        gone.add(q)

    for q in range(len(walls)):
        p = before.get(q)
        if q in gone or p is None or p in gone or q in first or p == q:
            continue
        a, b = walls[p], walls[q]
        if int(a["extra"]) > 0 or int(b["extra"]) > 0 or a["next_sector"] != b["next_sector"] or not straight(p, q):
            continue
        if int(b["point2"]) == p or owner[p] != owner[q]:
            continue
        here = ends[int(b["x"]), int(b["y"])]
        if int(a["next_sector"]) < 0:
            if len(here) == 1 and alike(p, q):
                join(p, q)
            continue
        # an opening: its other side runs the other way, and is joined with it or not at all
        over_p, over_q = int(a["next_wall"]), int(b["next_wall"])
        if (len(here) != 2 or over_p in gone or over_q in gone or int(walls[over_q]["point2"]) != over_p or over_p in first
                or int(walls[over_p]["extra"]) > 0 or int(walls[over_q]["extra"]) > 0):
            continue
        if alike(p, q) and alike(over_q, over_p):
            join(p, q)
            join(over_q, over_p)
            walls[p]["next_wall"], walls[over_q]["next_wall"] = over_q, p

    # the rest close up
    number, kept = {}, []
    for i in range(len(walls)):
        if i not in gone:
            number[i] = len(kept)
            kept.append(i)
    for s in sectors:
        start, count = int(s["wall_ptr"]), int(s["wall_count"])
        mine = [number[i] for i in range(start, start + count) if i not in gone]
        s["wall_ptr"], s["wall_count"] = mine[0], len(mine)
    for i in kept:
        w = walls[i]
        w["point2"] = number[int(w["point2"])]
        if int(w["next_wall"]) >= 0:
            w["next_wall"] = number[int(w["next_wall"])]
        extra = disk.walls[i].extra
        if extra is not None:
            extra.fields["reference"] = (number[i] + 8192) % 16384 - 8192      # 14 bits, signed; the engine writes its own
    disk.walls[:] = [disk.walls[i] for i in kept]
    return {"walls_before": len(walls), "walls": len(kept), "joined": len(gone)}


# --- pieces of one floor that came out alike --------------------------------------

#: two pieces of a floor whose shades differ by no more are one
PIECE_STEP = 4
SAME = ("floor_z", "ceiling_z", "floor_picnum", "ceiling_picnum", "floor_stat", "ceiling_stat", "floor_heinum", "ceiling_heinum",
        "floor_pal", "ceiling_pal", "floor_x_panning", "floor_y_panning", "ceiling_x_panning", "ceiling_y_panning", "type",
        "visibility")


def _loops(disk: Any) -> list[list[list[int]]]:
    """Each sector's walls, loop by loop."""
    out = []
    for sector in disk.sectors:
        f = record_fields(sector)
        left = list(range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])))
        seen: set[int] = set()
        loops = []
        for start in left:
            if start in seen:
                continue
            loop, wall = [], start
            while wall not in seen:
                seen.add(wall)
                loop.append(wall)
                wall = int(record_fields(disk.walls[wall])["point2"])
            loops.append(loop)
        out.append(loops)
    return out


def _chain(loop: list[int], shared: set[int]) -> list[int] | None:
    """The loop turned so that its shared walls come last, if they are one stretch of it: what is not shared."""
    flags = [w in shared for w in loop]
    if not any(flags):
        return None
    if all(flags):
        return []
    turns = [k for k in range(len(loop)) if flags[k - 1] and not flags[k]]
    if len(turns) != 1:
        return None
    k = turns[0]
    turned = loop[k:] + loop[:k]
    return [w for w in turned if w not in shared]


def merge_alike(disk: Any, first_piece: int, *, step: int = PIECE_STEP) -> dict[str, Any]:
    """Make one sector of neighbouring pieces that look the same.

    Only a sector from `first_piece` on is given up (the pieces the light stage
    added stand at the end, so every sector before them keeps its number), only
    where neither has an XSECTOR or a slope or hangs on its first wall, and only
    where the two meet along one stretch, so that the outline stays plain.
    Returns the new number of each old sector.
    """
    walls = [record_fields(w) for w in disk.walls]
    sectors = [record_fields(s) for s in disk.sectors]
    loops = _loops(disk)
    owner = [-1] * len(walls)
    for index, rings in enumerate(loops):
        for loop in rings:
            for wall in loop:
                owner[wall] = index
    into = list(range(len(sectors)))
    dead: set[int] = set()

    def plain(index: int) -> bool:
        f = sectors[index]
        return record_extra(disk.sectors[index]) is None and not (int(f["floor_stat"]) | int(f["ceiling_stat"])) & (2 | 64)

    def area(index: int) -> float:
        total = 0
        for loop in loops[index]:
            for a, b in zip(loop, loop[1:] + loop[:1]):
                total += int(walls[a]["x"]) * int(walls[b]["y"]) - int(walls[b]["x"]) * int(walls[a]["y"])
        return abs(total) / 2

    def alike(a: int, b: int) -> bool:
        fa, fb = sectors[a], sectors[b]
        if any(fa.get(key) != fb.get(key) for key in SAME):
            return False
        sky = int(fa["ceiling_stat"]) & 1
        return (abs(int(fa["floor_shade"]) - int(fb["floor_shade"])) <= step
                and (sky and fa["ceiling_shade"] == fb["ceiling_shade"]
                     or not sky and abs(int(fa["ceiling_shade"]) - int(fb["ceiling_shade"])) <= step))

    def absorb(a: int, b: int) -> bool:
        """a takes b's ground."""
        mine = {w for loop in loops[a] for w in loop if int(walls[w]["next_sector"]) == b}
        theirs = {int(walls[w]["next_wall"]) for w in mine}
        if not mine or any(int(walls[w]["extra"]) > 0 or int(walls[w]["cstat"]) & (1 | 16 | 32 | 64) for w in mine | theirs):
            return False
        ours = [k for k, loop in enumerate(loops[a]) if mine & set(loop)]
        its = [k for k, loop in enumerate(loops[b]) if theirs & set(loop)]
        if len(ours) != 1 or len(its) != 1:
            return False
        left, right = _chain(loops[a][ours[0]], mine), _chain(loops[b][its[0]], theirs)
        if left is None or right is None or (not left) != (not right) and left and right:
            return False
        wide, narrow = area(a), area(b)
        joined = left + right
        rest = [loop for k, loop in enumerate(loops[a]) if k != ours[0]] + [loop for k, loop in enumerate(loops[b]) if k != its[0]]
        rings = ([joined] if joined else []) + rest
        if not rings:
            return False
        for loop in rings:
            for w, n in zip(loop, loop[1:] + loop[:1]):
                walls[w]["point2"] = n
                owner[w] = a
        # whoever looked into b looks into a
        for loop in rings:
            for w in loop:
                over = int(walls[w]["next_wall"])
                if over >= 0:
                    walls[over]["next_sector"] = a
        for key in ("floor_shade", "ceiling_shade"):
            sectors[a][key] = round((int(sectors[a][key]) * wide + int(sectors[b][key]) * narrow) / max(1.0, wide + narrow))
        loops[a], loops[b] = rings, []
        into[b] = a
        dead.add(b)
        return True

    changed = True
    while changed:
        changed = False
        for b in range(first_piece, len(sectors)):
            if b in dead or not plain(b):
                continue
            beside = sorted({int(walls[w]["next_sector"]) for loop in loops[b] for w in loop} - {-1, b})
            for a in beside:
                if a not in dead and plain(a) and alike(a, b) and absorb(a, b):
                    changed = True
                    break

    # the rest close up, sectors and walls
    def home(index: int) -> int:
        while into[index] != index:
            index = into[index]
        return index

    number = {old: new for new, old in enumerate(i for i in range(len(sectors)) if i not in dead)}
    final = {i: number[home(i)] for i in range(len(sectors))}
    order: list[int] = []
    at: dict[int, int] = {}
    for index in range(len(sectors)):
        if index in dead:
            continue
        start = len(order)
        for loop in loops[index]:
            for wall in loop:
                at[wall] = len(order)
                order.append(wall)
        sectors[index]["wall_ptr"], sectors[index]["wall_count"] = start, len(order) - start
    for wall in order:
        w = walls[wall]
        w["point2"] = at[int(w["point2"])]
        if int(w["next_wall"]) >= 0:
            w["next_wall"], w["next_sector"] = at[int(w["next_wall"])], final[int(w["next_sector"])]
        extra = disk.walls[wall].extra
        if extra is not None:
            extra.fields["reference"] = (at[wall] + 8192) % 16384 - 8192
    count = len(walls)
    disk.walls[:] = [disk.walls[wall] for wall in order]
    disk.sectors[:] = [s for i, s in enumerate(disk.sectors) if i not in dead]
    for i, sector in enumerate(disk.sectors):
        if sector.extra is not None:
            sector.extra.fields["reference"] = i
    for sprite in disk.sprites:
        f = record_fields(sprite)
        if 0 <= int(f["sector"]) < len(final):
            f["sector"] = final[int(f["sector"])]
    disk.header["start_sector"] = final[int(disk.header["start_sector"])]
    return {"sectors_merged": len(dead), "walls_before": count, "walls": len(order), "into": final}
