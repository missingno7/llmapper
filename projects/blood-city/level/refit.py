"""Refit a finished room in place: cut it into cells without touching what is joined to it, wired to it or put in it.

A room of the tree is a rectangle that doors, dive links, wires, signs, sounds and supplies
name by its region. `refit` takes cells laid over that rectangle (`bloodmap.arrangement`):
one of them keeps the region, and with it every name, sign and wire; the others are regions
of their own under its path; and every opening is given to whichever cells now stand at it.
What the passes after it put down by the room's old rectangle is moved to the cell it landed
in, and to that cell's floor, by `settle`, right before the layout is compiled.
"""

from __future__ import annotations

import math
from dataclasses import replace

from bloodmap import arrangement as A
from bloodmap.planar_geom import point_in_loop

#: host -> {cell: region}, for `settle`, and the rectangle the room was
DONE: dict[str, dict[str, str]] = {}
WAS: dict[str, tuple[int, int, int, int]] = {}


def begin() -> None:
    DONE.clear()
    WAS.clear()


def _along(a, b, p, q):
    """The stretch of the segment a-b that p-q covers, on a's and b's own line, as a's walk goes; or None."""
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    for x, y in (p, q):
        if (x - ax) * dy != (y - ay) * dx:
            return None
    size = dx * dx + dy * dy
    t = sorted(((x - ax) * dx + (y - ay) * dy) for x, y in (p, q))
    lo, hi = max(0, t[0]), min(size, t[1])
    if lo >= hi:
        return None

    def at(v):
        return round(ax + dx * v / size), round(ay + dy * v / size)
    return at(lo), at(hi)


def refit(layout, host: str, cells, keep: str, surface, face=lambda *_: {}, joint=lambda *_: {}) -> dict[str, str]:
    """Cut `host` into `cells`. `surface(cell, outer)` is what `add_region` is given; `keep` is the cell that stays `host`."""
    room = layout.regions[host]
    if room.holes:
        raise ValueError(f"{host} is already cut: refit it before anything is carved in it")
    xs, ys = [p[0] for p in room.outer], [p[1] for p in room.outer]
    WAS[host] = (min(xs), min(ys), max(xs), max(ys))
    regions = {}
    for cell in cells:
        fields = {"layer": room.layer, "declared_zero_exit": True, "intent": {"kind": "furnished"}, "role": "interior",
                  **surface(cell.name, list(cell.outer))}
        if cell.name == keep:
            room.outer, room.holes = tuple(cell.outer), tuple(cell.holes)
            for key, value in fields.items():
                if key not in ("role", "declared_zero_exit", "intent", "layer"):
                    setattr(room, key, value)
            regions[cell.name] = host
        else:
            regions[cell.name] = layout.add_region(f"{host}:{cell.name}", cell.outer, holes=cell.holes, **fields)
    edges = A.rim(cells)
    for key, c in list(layout.connections.items()):
        if host not in (c.region_a, c.region_b):
            continue
        shares = [(cell, part) for cell, p, q in edges if (part := _along(c.a1, c.a2, p, q))]
        if not shares:
            raise ValueError(f"{host}: nothing of the new cells stands at {key} ({c.a1} to {c.a2})")
        del layout.connections[key]
        for n, (cell, (a, b)) in enumerate(shares):
            own = regions[cell]
            layout.connections[key if n == 0 else f"{key}:{n}"] = replace(
                c, connection_id=key if n == 0 else f"{key}:{n}", region_a=own if c.region_a == host else c.region_a,
                region_b=own if c.region_b == host else c.region_b, a1=a, a2=b, min_width=1 if len(shares) > 1 else c.min_width, min_opening=0)
    for n, j in enumerate(sorted(A.joints(cells), key=lambda j: (j.left, j.right, j.a))):
        layout.add_connection(f"{host}|{n}", regions[j.left], regions[j.right], a1=j.a, a2=j.b,
                              **{"min_width": 1, "min_opening": 0, **joint(j.left, j.right, j.a, j.b)})
        for seen, beyond in ((j.left, j.right), (j.right, j.left)):
            paint = face(seen, beyond, j.a, j.b)
            if paint:
                layout.paint_wall(regions[seen], j.a, j.b, fixed_frame="x_repeat" in paint, **paint)
    shared = {frozenset((c.a1, c.a2)) for c in layout.connections.values()}
    for name, a, b in edges:
        paint = face(name, None, a, b)
        if paint and frozenset((a, b)) not in shared:
            layout.paint_wall(regions[name], a, b, fixed_frame="x_repeat" in paint, **paint)
    DONE[host] = regions
    return regions


def _holds(layout, region: str, x: float, y: float) -> bool:
    r = layout.regions[region]
    return point_in_loop((round(x), round(y)), r.outer) == 1 and all(point_in_loop((round(x), round(y)), h) == 0 for h in r.holes)


def _bounds(layout, region: str):
    outer = layout.regions[region].outer
    return (min(p[0] for p in outer), min(p[1] for p in outer), max(p[0] for p in outer), max(p[1] for p in outer))


def _stand(layout, regions, x, y):
    """The cell that holds a point with room for a body round it, the nearest such point if it has none."""
    for reach in range(0, 2400, 120):
        for k in range(16 if reach else 1):
            px, py = x + reach * math.cos(k * math.pi / 8), y + reach * math.sin(k * math.pi / 8)
            for region in regions:
                if _holds(layout, region, px, py) and all(
                        _holds(layout, region, px + 96 * dx, py + 96 * dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    return region, px, py
    return None


def settle(layout) -> dict:
    """Give what stands in a refitted room to the cell it stands in, at that cell's floor (or under its roof)."""
    moved, lost = 0, []
    for host, regions in DONE.items():
        mine = list(dict.fromkeys(regions.values()))
        x0, y0, x1, y1 = WAS[host]
        for p in layout.placements:
            if p.region_id not in mine:
                continue
            anchor = p.anchor or {}
            if anchor.get("kind") in ("floor", "ceiling") and p.region_id == host:
                u, v = anchor["local"]
                found = _stand(layout, [r for r in mine if layout.regions[r].floor_slope is None], x0 + u * (x1 - x0), y0 + v * (y1 - y0))
                if found is None:
                    lost.append(p.placement_id)
                    continue
                p.region_id, px, py = found
                bx0, by0, bx1, by1 = _bounds(layout, p.region_id)
                anchor["local"] = [(px - bx0) / (bx1 - bx0), (py - by0) / (by1 - by0)]
                moved += 1
            elif anchor or _holds(layout, p.region_id, p.x, p.y):
                continue
            else:
                room = layout.regions[p.region_id]
                near = [r for r in (*mine, *layout.regions) if layout.regions[r].layer == room.layer and r != p.region_id and _holds(layout, r, p.x, p.y)]
                if not near:
                    lost.append(p.placement_id)
                    continue
                there = layout.regions[near[0]]
                p.z += (there.ceiling_z - room.ceiling_z) if abs(p.z - room.ceiling_z) < 1024 else (there.floor_z - room.floor_z)
                p.region_id = near[0]
                moved += 1
    return {"moved": moved, "lost": lost}
