"""A painted facade is whole windows: no corner, doorway or cut window slices one, and a window one can look through is cut where one is painted.

The owner, 2026-11-25: "I would like to fix textures misalignments across the city
windows", and "I would try to align the windows cutouts with texture of the building
that has windows on it".

The facades were phased from the world's own 1,024 grid (`texture_frame.frame_map`), so
a window lay whole between any two openings on the grid -- and every building's corner is
cut back half a bay, so the last window before each corner was drawn in half: 43 of the
236 windowed walls ended inside a window. Windows one can look through were 1,024 wide
and 0.54 of a body up wherever there was room, across whatever was painted there.

`apply` runs last over the finished faces. A straight front is taken in stretches, each
from a corner or an opening to the next; a stretch carries whole windows at the natural
scale, the plaster between them taking up what is over (the art leaves 17 texels either
side of 380's window), and only where that will not go is it drawn a few per cent wider
or narrower. A stretch too short for a window wears the front's windowless twin. A
window that is really cut holds the painted one's place in the stretch exactly.

`windows_on` says where the painted windows of a stretch will stand, for whoever cuts one.
"""

from __future__ import annotations

import math
from typing import Any

#: units to a texel of a facade at its natural scale, and z to one
UNIT, Z = 16, 256
#: tile -> the columns its painted window lies between (frame and all), of 64
PAINTED = {380: (17, 47), 384: (17, 48), 393: (13, 53), 397: (9, 55), 400: (10, 54), 401: (10, 54)}
#: tile -> the opening that takes a painted window's place: columns, rows from the top, the tile's rows. Eight columns to a
#: step of `x_repeat`, so a cut window's record can be drawn at the scale of its neighbours. 400 and 401: the ground storey's.
OPENING = {380: (16, 48, 24, 88, 128), 384: (16, 48, 25, 70, 128), 393: (16, 48, 31, 63, 128), 397: (8, 56, 31, 72, 128),
           400: (8, 56, 188, 236, 256), 401: (8, 56, 157, 193, 256)}


def rises(tile: int) -> tuple[int, int]:
    """A cut window's sill and head over the ground the facade stands on."""
    _lo, _hi, top, bottom, rows = OPENING[tile]
    return (rows - bottom) * Z, (rows - top) * Z


def _cuts(tile: int, u: float) -> bool:
    lo, hi = PAINTED[tile]
    return lo < u % 64 < hi


def fit(length: float, tile: int, *, start: int | None = None, end: int | None = None) -> tuple[int, int, float]:
    """(first column, repeats, cost) of the best whole-window drawing of a stretch; `start` and `end` pin a column of 64."""
    lo, hi = PAINTED[tile]
    natural = length / UNIT / 8
    best = None
    for repeats in range(max(1, math.floor(natural) - 3), math.ceil(natural) + 4):
        stretch = abs(math.log(repeats / natural))
        firsts = [start] if start is not None else [(end - repeats * 8) % 64] if end is not None else range(64)
        for u0 in firsts:
            u1 = u0 + repeats * 8
            if start is not None and end is not None and (u1 - end) % 64:
                continue
            cost = 12 * stretch
            cost += 4 * ((start is None and _cuts(tile, u0)) + (end is None and _cuts(tile, u1)))
            if start is None and end is None:
                ends = (lo - u0) % 64, (u1 - hi) % 64
                cost += abs(ends[0] - ends[1]) / 64                      # as much wall at one end as at the other
                cost += 0.3 * max(0, 8 - min(ends)) / 8                  # and a pier, not a frame, at the corner
            if best is None or cost < best[2] - 1e-9:
                best = (int(u0) % 64, repeats, cost)
    return best or (start or 0, max(1, round(natural)), 99.0)


def windows_on(length: float, tile: int) -> list[tuple[int, int]]:
    """Where the openings of a whole stretch stand: (from, to) in units from its left end as one faces it."""
    lo, hi, *_ = OPENING[tile]
    u0, repeats, _cost = fit(length, tile)
    per = length / (repeats * 8)
    out = []
    for k in range(-1, repeats // 8 + 2):
        a, b = (k * 64 + lo - u0) * per, (k * 64 + hi - u0) * per
        if a >= 0 and b <= length:
            middle = (a + b) / 2
            half = (hi - lo) * UNIT / 2
            out.append((round(middle - half), round(middle + half)))
    return out


def _f(item: Any) -> dict:
    return item.get("fields", item) if isinstance(item, dict) else item.fields


def _pieces(level, skip) -> dict:
    """(tile, direction, line) -> the walls that show that tile to the sky along it, in order along the direction."""
    out: dict = {}
    for sector in level.sectors:
        s = _f(sector)
        if not int(s["ceiling_stat"]) & 1:
            continue
        first = int(s["wall_ptr"])
        for w in range(first, first + int(s["wall_count"])):
            f = _f(level.walls[w])
            tile = int(f["picnum"])
            if tile not in PAINTED or w in skip or int(f["cstat"]) & (16 | 32):
                continue
            n = _f(level.walls[int(f["point2"])])
            ax, ay, bx, by = int(f["x"]), int(f["y"]), int(n["x"]), int(n["y"])
            length = math.hypot(bx - ax, by - ay)
            if length < 1:
                continue
            kind = "wall"
            if int(f["next_sector"]) >= 0:
                t = _f(level.sectors[int(f["next_sector"])])
                above = not int(t["ceiling_stat"]) & 1 and int(t["ceiling_z"]) > int(s["ceiling_z"]) + 256
                below = int(t["floor_z"]) < int(s["floor_z"]) - 2048
                if above and below:
                    kind = "window"
                elif above:
                    kind = "door"
                elif not below:
                    continue
            dx, dy = (bx - ax) / length, (by - ay) / length
            key = (tile, round(dx, 2), round(dy, 2), round((ax * dy - ay * dx) / 4))
            out.setdefault(key, []).append((ax * dx + ay * dy, length, kind, w))
    for rows in out.values():
        rows.sort()
    return out


def _fronts(level, skip):
    """Straight fronts of one tile with no break in them: lists of (along, length, kind, wall)."""
    for key, rows in sorted(_pieces(level, skip).items(), key=lambda item: str(item[0])):
        front: list = []
        for row in rows:
            if front and abs(front[-1][0] - row[0]) < 2:
                continue                                     # one line seen on two storeys
            if front and abs(front[-1][0] + front[-1][1] - row[0]) > 8:
                yield key, front
                front = []
            front.append(row)
        if front:
            yield key, front


def _stretches(front):
    """The front cut at its doorways: (kind, pieces). What is between two doorways and no wider than a post goes with them."""
    out: list = []
    for piece in front:
        kind = "door" if piece[2] == "door" else "wall"
        if out and out[-1][0] == kind:
            out[-1][1].append(piece)
        else:
            out.append([kind, [piece]])
    k = 1
    while k < len(out) - 1:
        if out[k][0] == "wall" and sum(p[1] for p in out[k][1]) < 448:
            out[k - 1][1] += out[k][1] + out[k + 1][1]
            del out[k:k + 2]
        else:
            k += 1
    return out


def _draw(level, pieces, u0: int, repeats: int) -> None:
    """Lay `repeats` steps of eight columns over the pieces from column `u0`, every join on a whole step."""
    total = sum(p[1] for p in pieces)
    done, at, left = 0.0, 0, len(pieces)
    for _along, length, _kind, w in pieces:
        done += length
        left -= 1
        end = repeats if not left else min(repeats - left, max(at + 1, round(repeats * done / total)))
        f = _f(level.walls[w])
        f["x_repeat"], f["x_panning"] = max(1, min(255, end - at)), (u0 + at * 8) % 64
        at = max(at + 1, end)


def apply(level, *, skip=frozenset()) -> dict:
    """Draw every windowed front under the sky as whole windows."""
    from facade_pass import BLANK_OF
    report = {"fronts": 0, "stretches": 0, "blank": 0, "cut_windows": 0, "still_cut": []}
    for key, front in list(_fronts(level, skip)):
        tile = key[0]
        lo, hi, *_ = OPENING[tile]
        report["fronts"] += 1
        for kind, pieces in _stretches(front):
            report["stretches"] += 1
            length = sum(p[1] for p in pieces)
            cuts = [p for p in pieces if p[2] == "window" and abs(p[1] - (hi - lo) * UNIT) <= 24]
            painted = (PAINTED[tile][1] - PAINTED[tile][0]) * UNIT
            if not cuts and length < painted * 0.8:
                repeats = max(1, len(pieces), round(length / UNIT / 8))
                if tile in BLANK_OF:
                    blank = BLANK_OF[tile]
                    for p in pieces:
                        f = _f(level.walls[p[3]])
                        f["picnum"] = blank
                        if blank == 385:                     # half the height of the tile it stands for
                            f["y_panning"] = int(f["y_panning"]) * 2 % 256
                    report["blank"] += 1
                    _draw(level, pieces, (PAINTED[tile][1] + 1) % 64, repeats)
                else:
                    # the plaster between two windows, and as much of it as there is room for
                    _draw(level, pieces, round((sum(PAINTED[tile]) + 64) / 2 - repeats * 4) % 64, repeats)
                continue
            if not cuts:
                u0, repeats, _cost = fit(length, tile)
                if len(pieces) > repeats:
                    continue
                _draw(level, pieces, u0, repeats)
                if _cuts(tile, u0) or _cuts(tile, u0 + repeats * 8):
                    report["still_cut"].append((tile, round(length), kind, pieces[0][3]))
                continue
            # between the windows that are cut, each stretch meets them at their own columns
            groups: list = []
            run: list = []
            for p in pieces:
                if p in cuts:
                    groups += [run, p]
                    run = []
                else:
                    run.append(p)
            groups.append(run)
            for k, group in enumerate(groups):
                if isinstance(group, tuple):
                    _draw(level, [group], lo, (hi - lo) // 8)
                    f = _f(level.walls[group[3]])
                    f["cstat"] = int(f["cstat"]) | 4
                    report["cut_windows"] += 1
                elif group:
                    u0, repeats, _cost = fit(sum(p[1] for p in group), tile, start=hi % 64 if k else None,
                                             end=lo if k < len(groups) - 1 else None)
                    _draw(level, group, u0, max(repeats, len(group)))
    return report
