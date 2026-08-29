"""Build's own draw-order predicate, transcribed rather than modelled.

The renderer sorts wall bunches front to back, and the whole sort rests on one
function. `wallfront` (build/src/engine.cpp:2227) takes two walls and the
viewer's position and answers which is in front -- except that it has two
answers that are not answers:

* ``-1`` when the two wall segments lie on one infinite line, and
* ``-2`` when they properly cross.

`bunchfront` (engine.cpp:2325) passes those straight through, and the sort does
this with them (engine.cpp:9736, and the comment is Build's author's own)::

    closest = 0;              //Almost works, but not quite :(
    for (i=1; i<numbunches; i++)
        if ((j = bunchfront(i,closest)) < 0) continue;

An unorderable pair is skipped, not resolved. Draw order then falls out of
enumeration order, so the far bunch can be drawn first; and drawing it retires
its screen columns -- `umost[x] > dmost[x]` marks a column finished
(engine.cpp:4699, engine.cpp:4740) -- so the near geometry is never given them.
The columns stay at whatever the frame was cleared to. That is the black
rectangle, and it is why no amount of z separation, hop distance or flood
cutting addresses it: **the predicate that fails never looks at any of them.**

Two consequences shape this module.

The first is that ``-1`` and ``-2`` do not depend on the viewer. Only the two
segments decide them. So they can be found statically, for a whole map, without
sampling a single pose -- and that answer is not an approximation of the
renderer's behaviour, it is the renderer's own condition evaluated ahead of
time.

The second is architectural. Two rooms stacked on one footprint have collinear
walls by construction. Offsetting them, jogging the plan, or turning one
relative to the other removes the condition at the source; nothing applied
afterwards can. Rooms that go different ways before they overlap satisfy it for
free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

Point = tuple[int, int]

#: What `wallfront` returns when it cannot answer.
COLLINEAR = -1
CROSSING = -2

VERDICT_NAMES = {
    COLLINEAR: "walls lie on one line",
    CROSSING: "walls properly cross",
}


def _i32(value: int) -> int:
    """Truncate to a signed 32-bit int, the way the engine's arithmetic does."""
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def dmulscale2(a: int, b: int, c: int, d: int) -> int:
    """`(a*b + c*d) >> 2`, in 32-bit, exactly as Build computes it.

    The shift is not cosmetic. It floors, so a cross product of 1, 2 or 3 comes
    back as **0** and reads as "this endpoint is on the line" when it is not
    quite. Emulating the shift rather than using the raw cross product is the
    difference between reproducing the engine and approximating it.
    """
    return _i32((_i32(a * b) + _i32(c * d)) >> 2)


def wallfront(l1: tuple[Point, Point], l2: tuple[Point, Point],
              viewer: Point | None = None) -> int:
    """Transcription of engine.cpp:2227.

    Returns **0 when `l1` is in front** and 1 when `l2` is -- the caller's own
    convention, from the sort at engine.cpp:9736: `if (j == 0) closest = i`,
    where `i` was passed as `l1`. `COLLINEAR` or `CROSSING` when the engine
    gives up.

    With no `viewer` the two orderable cases cannot be told apart and both come
    back as 1. That costs nothing here: the two failures are properties of the
    two segments alone, and they are the whole subject of this module.
    """
    (l1x, l1y), (l1px, l1py) = l1
    (l2x, l2y), (l2px, l2py) = l2
    dx, dy = l1px - l1x, l1py - l1y

    t1 = dmulscale2(l2x - l1x, dy, -dx, l2y - l1y)
    t2 = dmulscale2(l2px - l1x, dy, -dx, l2py - l1y)
    if t1 == 0:
        if t2 == 0:
            return COLLINEAR
        t1 = t2
    if t2 == 0:
        t2 = t1
    if (t1 ^ t2) >= 0:
        if viewer is None:
            return 1
        return int((dmulscale2(viewer[0] - l1x, dy, -dx, viewer[1] - l1y) ^ t1) >= 0)

    dx, dy = l2px - l2x, l2py - l2y
    t1 = dmulscale2(l1x - l2x, dy, -dx, l1y - l2y)
    t2 = dmulscale2(l1px - l2x, dy, -dx, l1py - l2y)
    if t1 == 0:
        if t2 == 0:
            return COLLINEAR
        t1 = t2
    if t2 == 0:
        t2 = t1
    if (t1 ^ t2) >= 0:
        if viewer is None:
            return 1
        return int((dmulscale2(viewer[0] - l2x, dy, -dx, viewer[1] - l2y) ^ t1) < 0)

    return CROSSING


@dataclass(frozen=True)
class Unorderable:
    """One pair of walls the sort cannot rank, and which two things own them."""

    left: str
    right: str
    left_wall: int
    right_wall: int
    verdict: int
    segment_a: tuple[Point, Point]
    segment_b: tuple[Point, Point]

    @property
    def why(self) -> str:
        return VERDICT_NAMES[self.verdict]


def segments_unorderable(a: Sequence[tuple[Point, Point]],
                         b: Sequence[tuple[Point, Point]]) -> list[tuple[int, int, int]]:
    """Every `(index in a, index in b, verdict)` the engine could not rank."""
    out: list[tuple[int, int, int]] = []
    for i, left in enumerate(a):
        for j, right in enumerate(b):
            verdict = wallfront(left, right)
            if verdict < 0:
                out.append((i, j, verdict))
    return out


def sector_walls(disk: Any, sector_id: int) -> list[tuple[int, tuple[Point, Point]]]:
    """A sector's walls as `(wall index, (start, end))`, following `point2`."""
    sector = disk.sectors[sector_id]
    first = int(sector.fields["wall_ptr"])
    count = int(sector.fields["wall_count"])
    out = []
    for index in range(first, first + count):
        wall = disk.walls[index]
        nxt = disk.walls[int(wall.fields["point2"])]
        out.append((index, ((int(wall.fields["x"]), int(wall.fields["y"])),
                            (int(nxt.fields["x"]), int(nxt.fields["y"])))))
    return out


def unorderable_between(disk: Any, left: int, right: int) -> list[Unorderable]:
    """Every wall pair across two sectors that `wallfront` refuses to rank."""
    a = sector_walls(disk, left)
    b = sector_walls(disk, right)
    out: list[Unorderable] = []
    for left_wall, seg_a in a:
        for right_wall, seg_b in b:
            verdict = wallfront(seg_a, seg_b)
            if verdict < 0:
                out.append(Unorderable(str(left), str(right), left_wall,
                                       right_wall, verdict, seg_a, seg_b))
    return out


def audit(disk: Any, pairs: Iterable[tuple[int, int]]) -> list[Unorderable]:
    """Run the predicate over the sector pairs given, usually the overlaps."""
    out: list[Unorderable] = []
    for left, right in pairs:
        out.extend(unorderable_between(disk, left, right))
    return out


__all__ = ["COLLINEAR", "CROSSING", "Unorderable", "audit", "dmulscale2",
           "sector_walls", "segments_unorderable", "unorderable_between",
           "wallfront"]
