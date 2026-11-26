"""How many are met on each difficulty: fewer on the two easier, more on the two harder, as the campaign has it.

Over the campaign's 43 maps, against the middle difficulty: 0.75, 0.81, 1, 1.19, 1.28 (by a
map's median 0.76, 0.79, 1, 1.22, 1.29). The city stood at 0.88, 0.90, 1, 1.01, 1.01. The
middle one is what the owner has walked and stays as it is: `thin` keeps some of those who
are there from the easier, `add` sets others beside them for the harder.

`launch_skill` is a set of LOCKOUT bits (`blood.cpp:699`): 1 is not on the first, 3 not on
the first two, 7 on the last two only, 15 on the last only -- the campaign's four commonest
masks (1,872 of its 1,949 masked sprites; 28, 24 and ten others also occur).
"""

from __future__ import annotations

import math
from dataclasses import replace

#: what may be fewer or more: cultists, zombies, butchers, hounds, gill beasts; nobody who is part of something
KINDS = (201, 202, 203, 204, 211, 217, 248)
#: what share of the middle difficulty's foes each difficulty is to have
SHARES = (0.75, 0.80, 1.0, 1.20, 1.28)
EASY, EASIER, HARD, HARDEST = 1, 3, 7, 15
#: nobody is thinned out who has no one within this of them, and nobody is added nearer the start than `QUIET`
COMPANY, QUIET = 8 * 1024, 9 * 1024
#: and nobody on a height: the gallows' terrace sees the whole square, the start with it
OVERLOOKS = -24576
#: how far beside the one it is of, and the floor it wants
BESIDE, ROOM = (900, 1200, 1500, 2000, 700), 320


def _foe(p) -> bool:
    return 201 <= p.type <= 250 or p.type == 18


def count(placements) -> list[int]:
    """How many are met (placed, or waiting on a wire) on each difficulty."""
    return [sum(1 for p in placements if _foe(p) and not int(p.behavior.get("launch_skill") or 0) >> k & 1) for k in range(5)]


def _wired() -> set[str]:
    import wires
    return {end["ref"][1] for wire in wires.circuit().wires for end in (*wire.senders, *wire.answers)}


def _spread(rows, many: int) -> list:
    """`many` of them, each the farthest from those already taken: the whole city, not one street."""
    rows = list(rows)
    taken = rows[:1] if many > 0 else []
    rows = rows[1:]
    while rows and len(taken) < many:
        best = max(rows, key=lambda p: (min(math.hypot(p.x - q.x, p.y - q.y) + abs(p.z - q.z) / 8 for q in taken), p.placement_id))
        taken.append(best)
        rows.remove(best)
    return taken


def _free(layout) -> list:
    """Those who stand where they are for no reason but to be met there."""
    wired = _wired()
    plain = {"drop_item", "dude_deaf"}
    return [p for p in layout.placements if p.type in KINDS and p.placement_id not in wired and p.x > 0       # (the drowned are x < 0)
            and not {k for k, v in p.behavior.items() if v} - plain]


def thin(layout) -> int:
    """Some of the free are not there on the first two difficulties."""
    now = count(layout.placements)
    both, first = now[1] - round(now[2] * SHARES[1]), round(now[2] * SHARES[1]) - round(now[2] * SHARES[0])
    free = _free(layout)
    rows = [p for p in free if any(q is not p and math.hypot(p.x - q.x, p.y - q.y) < COMPANY and abs(p.z - q.z) < 20000 for q in free)]
    taken = _spread(rows, both + first)
    for k, p in enumerate(taken):
        p.behavior = {**p.behavior, "launch_skill": EASIER if k < both else EASY}
    return len(taken)


def add(layout, start, beside) -> int:
    """Others beside those, in the same sector and not by the start, for the last two difficulties."""
    import gameplay
    from shapely import Polygon
    now = count(layout.placements)
    hard, hardest = round(now[2] * SHARES[3]) - now[3], round(now[2] * SHARES[4]) - round(now[2] * SHARES[3])
    made = 0
    for p in _spread(beside, 400) * 2:                                          # (one beside each before two beside any)
        if made == hard + hardest:
            break
        if math.hypot(p.x - start[0], p.y - start[1]) < QUIET:
            continue
        region = layout.regions[p.region_id]
        if region.floor_slope is not None or region.floor_z < OVERLOOKS:
            continue
        shape = Polygon(region.outer, region.holes)
        from shapely import Point
        where = next(((x, y) for far in BESIDE for k in range(8)
                      for x, y in [(round(p.x + far * math.cos(k * math.pi / 4)), round(p.y + far * math.sin(k * math.pi / 4)))]
                      if shape.contains(Point(x, y)) and gameplay._clear(layout, shape, x, y, region.floor_z, ROOM)), None)
        if where is None:
            continue
        layout.placements.append(replace(
            p, placement_id=f"difficulty:more_{made}", x=where[0], y=where[1],
            behavior={"launch_skill": HARD if made < hard else HARDEST}))
        made += 1
    return made


def apply(layout, start) -> dict:
    """Both; what was there before, and what is now."""
    before = count(layout.placements)
    free = _free(layout)
    report = {"thinned": thin(layout), "added": add(layout, start, free), "before": before, "free": len(free)}
    return {**report, "now": count(layout.placements)}
