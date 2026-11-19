"""Lit windows: recesses in the city's edge buildings, as E3M1 cuts them.

The owner, 2026-11-18: "We should have more windows in buildings around
the city." Gravesend's facades already wore window TILES on 95% of their
street length (E3M1: 54%); what they had none of was a window that is a
place -- E3M1 cuts twelve shallow recesses into its fronts (0.43 per
10,000 of street wall): 1,024 wide to match one column of the facade
tile, 224 to 288 deep, the sill 2.42 to 4.35 bodies up, 1.15 to 1.57
tall, five of the twelve brighter than the wall they are in.

Here they go in the BACKS along the city's edge, where the far side of
the wall is certainly nothing: one to a building (`facade_pass.split_backs`
makes the buildings), a whole number of tile columns from the building's
corner so the facade's painted windows are not cut down the middle, and
every other one lit. The recess wears its building's own tile, brighter
or darker than the wall: the first build gave it tile 144, the owner's
"wooden lattice, used e.g. as windows", which is a MASK -- see-through
pixels on a solid wall, magenta in the first frame I looked at.

`cut` adds the recesses before compile; `paint` runs after the facade
pass, which gives each wall RECORD its own tile and so would dress the
piece of wall over a window as a different building.
"""

from __future__ import annotations

from typing import Any

BODY = 16960
WIDTH, DEPTH = 1024, 256
SILL, HEIGHT = 41040, 24576            # 2.42 bodies up, 1.45 tall
LATTICE = 144
LIT, DARK = -14, 42
#: filled by `cut`: region id, the street region, the two ends, lit
NICHES: list[dict] = []


def _f(item: Any) -> dict:
    return item.get("fields", item) if isinstance(item, dict) else item.fields


def _bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def cut(layout, districts, edge, *, grade: int) -> dict:
    """One recess to a building back on the west, north and east edges."""
    NICHES.clear()
    taken = [_bbox(region.outer) for region_id, region in
             layout.regions.items() if region_id not in districts]
    report = {"cut": 0, "lit": 0, "blocked": 0}
    for district in districts:
        region = layout.regions.get(district)
        if region is None:
            continue
        points = [(int(x), int(y)) for x, y in region.outer]
        for i, (x0, y0) in enumerate(points):
            x1, y1 = points[(i + 1) % len(points)]
            length = abs(x1 - x0) + abs(y1 - y0)
            if length < 4 * WIDTH:
                continue
            if x0 == x1 and x0 == edge[0]:
                out = (-1, 0)
            elif x0 == x1 and x0 == edge[2]:
                out = (1, 0)
            elif y0 == y1 and y0 == edge[1]:
                out = (0, -1)
            else:
                continue                      # the south edge is the sea
            sx = (x1 > x0) - (x1 < x0)
            sy = (y1 > y0) - (y1 < y0)
            #: whole tile columns from the building's own corner
            start = (length // (2 * WIDTH)) * WIDTH
            a = (x0 + sx * start, y0 + sy * start)
            b = (a[0] + sx * WIDTH, a[1] + sy * WIDTH)
            c = (b[0] + out[0] * DEPTH, b[1] + out[1] * DEPTH)
            d = (a[0] + out[0] * DEPTH, a[1] + out[1] * DEPTH)
            box = _bbox((a, b, c, d))
            if any(box[0] < t[2] and t[0] < box[2] and box[1] < t[3]
                   and t[1] < box[3] for t in taken):
                report["blocked"] += 1
                continue
            lit = (len(NICHES) % 2) == 0
            region_id = f"{district}/window_{len(NICHES)}"
            layout.add_region(
                region_id, [a, d, c, b], floor_z=grade - SILL,
                ceiling_z=grade - SILL - HEIGHT, wall_picnum=LATTICE,
                floor_picnum=int(region.wall_picnum),
                ceiling_picnum=int(region.wall_picnum),
                wall_shade=LIT if lit else DARK,
                floor_shade=LIT + 8 if lit else DARK,
                ceiling_shade=LIT + 8 if lit else DARK,
                role="detail", layer=getattr(region, "layer", "street"),
                declared_zero_exit=True, intent={"kind": "window_niche"})
            layout.add_connection(f"connection:window_{len(NICHES)}",
                                  region_id, district, a1=a, a2=b)
            taken.append(box)
            NICHES.append({"region_id": region_id, "street": district,
                           "a": a, "b": b, "lit": lit})
            report["cut"] += 1
            report["lit"] += int(lit)
    return report


#: Real windows. The owner, the same day, on seeing the recesses: "Windows
#: should really be windows where you can look from inside outside, you
#: can put bars there or glass, check how they are done in other levels,
#: for example E1M4". Measured over E1M4, E1M1, E1M2, E3M1 and E3M2 (74
#: of them): a four-walled sill sector THROUGH the wall between a room and
#: the street, 768 to 1,024 wide and as deep as the wall (128 to 256), the
#: sill 0.5 to 0.6 of a body up (E1M4, E1M1, E1M2 medians 0.6, 0.54, 0.6)
#: and the opening 1.0 to 1.5 tall. Most are open; the rest are glazed
#: with breakable glass (266 or 263, type 511). Bars are the owner's own
#: suggestion: 463, his "grate", a mask.
THROUGH_SILL, THROUGH_HEIGHT = 9216, 19456       # 0.54 up, 1.15 tall
#: Gravesend's walls are 512 and 1,024 thick: a window through the
#: thicker ones is a deep reveal (E6M1's are 768)
THROUGH_MAX_WALL = 1024
BARS = 463
#: filled by `cut_through`: also read by `paint` and by `glaze`
THROUGH: list[dict] = []


def _rect(region):
    points = [(int(x), int(y)) for x, y in region.outer]
    if len(points) != 4:
        return None
    box = _bbox(points)
    if {(box[0], box[1]), (box[2], box[1]), (box[2], box[3]),
            (box[0], box[3])} != set(points):
        return None
    return box


def cut_through(layout, districts, *, grade: int, limit: int = 16) -> dict:
    """A window from each street-side room to the street it stands on."""
    THROUGH.clear()
    report = {"cut": 0, "glass": 0, "bars": 0, "rooms": []}
    boxes = {region_id: _bbox(region.outer)
             for region_id, region in layout.regions.items()}
    placed: dict = {}
    items = getattr(layout, "placements", {})
    for q in (items.values() if isinstance(items, dict) else items):
        placed.setdefault(q.region_id, []).append(q)
    rooms = []
    for region_id, region in layout.regions.items():
        if getattr(region, "role", "") != "interior":
            continue
        if getattr(region, "layer", "street") != "street":
            continue                  # nothing under a see-over roof
        box = _rect(region)
        clear = int(region.floor_z) - int(region.ceiling_z)
        if (box is None or int(region.floor_z) != grade
                or clear < THROUGH_SILL + THROUGH_HEIGHT + 2048
                or min(box[2] - box[0], box[3] - box[1]) < 2048):
            continue
        rooms.append((region_id, region, box))
    import os
    if os.environ.get("WINDOW_DEBUG"):
        roles = {}
        for region_id, region in layout.regions.items():
            key = (getattr(region, "role", ""), getattr(region, "layer", ""))
            roles[key] = roles.get(key, 0) + 1
        print("WINDOW_DEBUG roles", roles)
        for region_id, _region, box in rooms:
            best = None
            for district in districts:
                street = layout.regions.get(district)
                for hole in (street.holes if street else ()):
                    pts = [(int(x), int(y)) for x, y in hole]
                    for i, (x0, y0) in enumerate(pts):
                        x1, y1 = pts[(i + 1) % len(pts)]
                        if x0 == x1:
                            ov = min(max(y0, y1), box[3]) - max(min(y0, y1), box[1])
                            gaps = (abs(x0 - box[0]), abs(x0 - box[2]))
                        elif y0 == y1:
                            ov = min(max(x0, x1), box[2]) - max(min(x0, x1), box[0])
                            gaps = (abs(y0 - box[1]), abs(y0 - box[3]))
                        else:
                            continue
                        if ov >= 1024:
                            g = min(gaps)
                            if best is None or g < best[0]:
                                best = (g, ov)
            print("WINDOW_DEBUG", region_id.split("/")[-2:], box, best)
    for district in districts:
        street = layout.regions.get(district)
        if street is None:
            continue
        for hole in street.holes:
            points = [(int(x), int(y)) for x, y in hole]
            for i, (x0, y0) in enumerate(points):
                x1, y1 = points[(i + 1) % len(points)]
                if x0 != x1 and y0 != y1:
                    continue
                vertical = x0 == x1
                line = x0 if vertical else y0
                lo, hi = sorted((y0, y1) if vertical else (x0, x1))
                for region_id, region, box in rooms:
                    if report["cut"] >= limit:
                        break
                    if any(w["room"] == region_id and w["line"] == line
                           for w in THROUGH):
                        continue             # one to a wall of a room
                    faces = ((box[0], box[2]) if vertical
                             else (box[1], box[3]))
                    rlo, rhi = ((box[1], box[3]) if vertical
                                else (box[0], box[2]))
                    for face in faces:
                        gap = abs(face - line)
                        if not 128 <= gap <= THROUGH_MAX_WALL:
                            continue
                        #: the room must lie beyond the wall from the street
                        inside = (faces[0] + faces[1]) / 2
                        if abs(inside - line) < abs(inside - face):
                            continue
                        a, b = max(lo, rlo) + 512, min(hi, rhi) - 512
                        if b - a < WIDTH:
                            continue
                        #: clear of whatever already hangs on that wall of
                        #: the room: try the middle, then step aside
                        hung = []
                        for q in placed.get(region_id, ()):
                            anchor = getattr(q, "anchor", None) or {}
                            if anchor.get("kind") != "wall":
                                continue
                            (px, py), (qx, qy) = anchor["a1"], anchor["a2"]
                            k = float(anchor["t"])
                            wx, wy = px + (qx - px) * k, py + (qy - py) * k
                            if abs((wx if vertical else wy) - face) <= 128:
                                hung.append(wy if vertical else wx)
                        centre = ((a + b) // 2 // 256) * 256
                        mid = None
                        for step in (0, 1536, -1536, 3072, -3072, 4608,
                                     -4608):
                            c = centre + step
                            if c - WIDTH // 2 < a or c + WIDTH // 2 > b:
                                continue
                            if all(abs(h - c) > WIDTH // 2 + 640
                                   for h in hung):
                                mid = c
                                break
                        if mid is None:
                            continue
                        s0, s1 = mid - WIDTH // 2, mid + WIDTH // 2
                        n0, n1 = sorted((line, face))
                        rect = ((n0, s0, n1, s1) if vertical
                                else (s0, n0, s1, n1))
                        #: clear of every door, reveal, shelf and shopfront:
                        #: nothing else may stand within 384 along the wall
                        grown = ((rect[0], rect[1] - 384, rect[2],
                                  rect[3] + 384) if vertical else
                                 (rect[0] - 384, rect[1], rect[2] + 384,
                                  rect[3]))
                        if any(other not in (district, region_id)
                               and grown[0] < t[2] and t[0] < grown[2]
                               and grown[1] < t[3] and t[1] < grown[3]
                               for other, t in boxes.items()):
                            continue
                        name = f"{region_id}/window_{len(THROUGH)}"
                        barred = len(THROUGH) % 2 == 1
                        #: TWO volumes at one floor and one ceiling, the
                        #: pane between them. The owner, 2026-11-17: "The
                        #: glass should sit in an aperture/frame so glass
                        #: texture scaling won't be colliding with facade
                        #: texture." A pane on the street's own wall shares
                        #: that record with the facade's bands over and
                        #: under the window; five standing tests said so
                        #: when the first version did exactly that.
                        half = (n0 + n1) // 2
                        street_first = line == n0
                        outer_n = (n0, half) if street_first else (half, n1)
                        inner_n = (half, n1) if street_first else (n0, half)

                        def box_of(nn):
                            return ((nn[0], s0, nn[1], s1) if vertical
                                    else (s0, nn[0], s1, nn[1]))

                        for part, nn in (("reveal", outer_n),
                                         ("pocket", inner_n)):
                            r = box_of(nn)
                            layout.add_region(
                                f"{name}/{part}",
                                [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]),
                                 (r[0], r[3])],
                                floor_z=grade - THROUGH_SILL,
                                ceiling_z=grade - THROUGH_SILL - THROUGH_HEIGHT,
                                wall_picnum=int(region.wall_picnum),
                                floor_picnum=int(region.wall_picnum),
                                ceiling_picnum=int(region.wall_picnum),
                                role="detail", layer="street",
                                declared_zero_exit=True,
                                intent={"kind": "window"})
                        if vertical:
                            street_seg = ((line, s0), (line, s1))
                            room_seg = ((face, s0), (face, s1))
                            pane_seg = ((half, s0), (half, s1))
                        else:
                            street_seg = ((s0, line), (s1, line))
                            room_seg = ((s0, face), (s1, face))
                            pane_seg = ((s0, half), (s1, half))
                        layout.add_connection(
                            f"connection:window_out_{len(THROUGH)}",
                            f"{name}/reveal", district,
                            a1=street_seg[0], a2=street_seg[1])
                        layout.add_connection(
                            f"connection:window_pane_{len(THROUGH)}",
                            f"{name}/reveal", f"{name}/pocket",
                            a1=pane_seg[0], a2=pane_seg[1])
                        layout.add_connection(
                            f"connection:window_in_{len(THROUGH)}",
                            f"{name}/pocket", region_id,
                            a1=room_seg[0], a2=room_seg[1])
                        boxes[name] = rect
                        THROUGH.append({
                            "region_id": f"{name}/reveal", "room": region_id,
                            "pane_seg": pane_seg,
                            "street": district, "a": street_seg[0],
                            "b": street_seg[1], "lit": True,
                            "barred": barred, "street_seg": street_seg,
                            "line": line})
                        NICHES.append(THROUGH[-1])
                        report["cut"] += 1
                        report["bars" if barred else "glass"] += 1
                        report["rooms"].append(region_id.split("/")[-1])
                        break
    return report


def glaze(level) -> dict:
    """Glass in one window and bars in the next, in the wall's middle."""
    from bloodmap import glass

    def span(window):
        (x0, y0), (x1, y1) = window["pane_seg"]
        return (min(x0, x1) - 16, min(y0, y1) - 16,
                max(x0, x1) + 16, max(y0, y1) + 16)

    panes = glass.glaze(level, [span(w) for w in THROUGH if not w["barred"]],
                        fit=True)
    bars = glass.grille(level, [span(w) for w in THROUGH if w["barred"]],
                        tile=BARS)
    return {"panes": panes["panes"], "barred": len(bars["barred"]),
            "refused": bars["refused"]}


def paint(level, compiled) -> dict:
    """The wall a window is cut in is ONE building: dress it as one."""
    report = {"niches": 0, "records": 0}
    for niche in NICHES:
        allocation = compiled.allocations.get(niche["region_id"])
        if allocation is None:
            continue
        sector_id = allocation.sector_id
        report["niches"] += 1
        (ax, ay), (bx, by) = niche["a"], niche["b"]
        vertical = ax == bx
        line = ax if vertical else ay
        lo, hi = sorted((ay, by) if vertical else (ax, bx))
        own, flank = [], []
        for wall in level.walls:
            f = _f(wall)
            n = _f(level.walls[int(f["point2"])])
            x0, y0, x1, y1 = int(f["x"]), int(f["y"]), int(n["x"]), int(n["y"])
            if vertical and not (x0 == x1 == line):
                continue
            if not vertical and not (y0 == y1 == line):
                continue
            p, q = sorted((y0, y1) if vertical else (x0, x1))
            if int(f["next_sector"]) == sector_id:
                own.append(f)
            elif int(f["next_sector"]) < 0 and (q == lo or p == hi):
                flank.append(f)
        if not own or not flank:
            continue
        #: The longer flank is the building. Its tile goes on the other
        #: flank and on the wall the window is cut in; the flanks keep the
        #: scale and origin the facade pass gave them, and the cut wall
        #: CONTINUES the flank that runs into it -- one column on, and
        #: hung from the street's own sky as a solid wall is (bit 4 on a
        #: two-sided wall), so the painted storeys run straight across.
        def length_of(f):
            n = _f(level.walls[int(f["point2"])])
            return (abs(int(n["x"]) - int(f["x"]))
                    + abs(int(n["y"]) - int(f["y"])))

        building = max(flank, key=length_of)
        tile = int(building["picnum"])
        for f in flank:
            f["picnum"] = tile
        for f in own:
            before = [g for g in flank
                      if _f(level.walls[int(g["point2"])]) is f]
            lead = before[0] if before else building
            f["picnum"] = tile
            f["x_repeat"], f["y_repeat"] = WIDTH // 128, int(lead["y_repeat"])
            f["x_panning"] = ((int(lead["x_panning"])
                               + int(lead["x_repeat"]) * 8) % 64
                              if before else 0)
            f["y_panning"] = int(lead["y_panning"])
            f["cstat"] = int(f["cstat"]) | 4
            f["shade"] = int(lead["shade"])
            report["records"] += 1
        if "room" in niche:
            continue                  # a real window keeps its room jambs
        #: the recess itself wears the building, lit or dark
        sector = _f(level.sectors[sector_id])
        for w in range(int(sector["wall_ptr"]),
                       int(sector["wall_ptr"]) + int(sector["wall_count"])):
            g = _f(level.walls[w])
            if int(g["next_sector"]) < 0:
                g["picnum"] = tile
                g["shade"] = LIT if niche["lit"] else DARK
                g["x_panning"] = g["y_panning"] = 0
                g["cstat"] = int(g["cstat"]) | 4
    return report
