"""Where a floor-aligned sprite really lies: the engine's own arithmetic.

The owner, 2026-11-19, in the game, of the carriage roof built from twenty
floor sprites: "sprite roof on carriage doesn't align, I think there might
be general bug in whatever you are using to put the sprites there, center
and size estimations might be off, check what is the root cause and fix
it."

The root cause was not in a tool. There WAS no tool: nothing in this
project said where a flat sprite's rectangle lies. The roof was written
as `x_repeat` 64 (meant: 1,024 along the car) by `y_repeat` 48 (meant: 768
across it) at angle 0, on the assumption that a tile's x is the map's x.
It is not. `get_floorspr_points` (NBlood/source/build/src/engine_priv.h)
lays the tile's WIDTH along (-sin a, cos a) and its HEIGHT along
(-cos a, -sin a): a quarter turn from the sprite's angle. At angle 0 the
width runs along the map's +y and the height along -x, so every piece
lay 768 by 1,024, with a 256 gap to the next and 128 hanging over each
wall. The lint that should have seen it (`sprite_fit.flat_overlaps`)
ignored rotation by its own admission.

So this module is the one place that knows:

``footprint``  the four corners of a flat sprite, transcribed from the
               engine line for line, tile offsets and flips included.
``cover``      the sprites that tile a map rectangle EXACTLY: angle
               1536, at which a tile's width is the map's +x and its
               height the map's +y, and whole repeats only.
``faults``     what a set of flat sprites fails to cover of a rectangle,
               and what it covers outside it.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

#: at this angle a tile's width lies along the map's +x, its height along +y
MAP_ALIGNED = 1536
#: one repeat of one texel is a quarter of a map unit
TEXEL = 4
#: the texel scale Blood draws most things at
USUAL_REPEAT = 64


class FlatSpriteError(ValueError):
    """A rectangle that whole repeats of this tile cannot cover exactly."""


def _sin(angle: int) -> int:
    """`sintable[angle & 2047]`: 16,384 times the sine."""
    return int(round(16384 * math.sin((int(angle) & 2047) * math.pi / 1024)))


def footprint(fields: Any, tile_size: Sequence[int],
              tile_offset: Sequence[int] = (0, 0)) -> list[tuple[int, int]]:
    """The four corners, in the engine's order. `get_floorspr_points`."""
    angle = int(fields["angle"])
    cos, sin = _sin(angle + 512), _sin(angle)
    span_x, span_y = int(tile_size[0]), int(tile_size[1])
    rep_x, rep_y = int(fields["x_repeat"]), int(fields["y_repeat"])
    off_x = int(tile_offset[0]) + int(fields.get("x_offset", 0) or 0)
    off_y = int(tile_offset[1]) + int(fields.get("y_offset", 0) or 0)
    cstat = int(fields["cstat"])
    if cstat & 4:
        off_x = -off_x
    if cstat & 8:
        off_y = -off_y
    centre_x = ((span_x >> 1) + off_x) * rep_x
    centre_y = ((span_y >> 1) + off_y) * rep_y
    wide, deep = span_x * rep_x, span_y * rep_y
    x1 = int(fields["x"]) + ((sin * centre_x + cos * centre_y) >> 16)
    y1 = int(fields["y"]) + ((sin * centre_y - cos * centre_x) >> 16)
    x2 = x1 - ((sin * wide) >> 16)
    y2 = y1 + ((cos * wide) >> 16)
    ofs_x, ofs_y = -((cos * deep) >> 16), -((sin * deep) >> 16)
    return [(x1, y1), (x2, y2), (x2 + ofs_x, y2 + ofs_y),
            (x1 + ofs_x, y1 + ofs_y)]


def box(fields: Any, tile_size: Sequence[int],
        tile_offset: Sequence[int] = (0, 0)) -> tuple[int, int, int, int]:
    """The footprint's bounding box: exact for a map-aligned sprite."""
    points = footprint(fields, tile_size, tile_offset)
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _pieces(length: int, texels: int) -> tuple[int, int]:
    """(how many, at what repeat) so that whole repeats span `length`."""
    best = None
    for count in range(1, 65):
        if (length * TEXEL) % (count * texels):
            continue
        repeat = length * TEXEL // (count * texels)
        if not 1 <= repeat <= 255:
            continue
        score = abs(repeat - USUAL_REPEAT)
        if best is None or score < best[0]:
            best = (score, count, repeat)
    if best is None:
        raise FlatSpriteError(
            f"{length} map units cannot be laid in whole repeats of a "
            f"{texels}-texel tile")
    return best[1], best[2]


def cover(rect: Sequence[int], tile_size: Sequence[int]) -> list[dict[str, int]]:
    """Sprites whose footprints tile `rect` (x0, y0, x1, y1) exactly.

    Each is {"x", "y", "angle", "x_repeat", "y_repeat"}: its centre, the
    map-aligned angle, and repeats near the usual 64 that divide the
    rectangle with nothing left over.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    across, x_repeat = _pieces(x1 - x0, int(tile_size[0]))
    down, y_repeat = _pieces(y1 - y0, int(tile_size[1]))
    wide = int(tile_size[0]) * x_repeat // TEXEL
    deep = int(tile_size[1]) * y_repeat // TEXEL
    return [{"x": x0 + i * wide + wide // 2, "y": y0 + j * deep + deep // 2,
             "angle": MAP_ALIGNED, "x_repeat": x_repeat, "y_repeat": y_repeat}
            for j in range(down) for i in range(across)]


def faults(rect: Sequence[int], boxes: Iterable[Sequence[int]],
           cell: int = 64) -> dict[str, int]:
    """What `boxes` leave bare of `rect`, lay over twice, and spill past it.

    In map units squared, counted on a grid of `cell`: enough to tell a
    256-wide gap from a seam, which is what the first roof had ten of.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    boxes = [tuple(int(v) for v in b) for b in boxes]
    bare = doubled = 0
    for cx in range(x0, x1, cell):
        for cy in range(y0, y1, cell):
            px, py = cx + cell // 2, cy + cell // 2
            hits = sum(1 for bx0, by0, bx1, by1 in boxes
                       if bx0 <= px < bx1 and by0 <= py < by1)
            bare += hits == 0
            doubled += hits > 1
    spill = 0
    for bx0, by0, bx1, by1 in boxes:
        whole = (bx1 - bx0) * (by1 - by0)
        inside = (max(0, min(bx1, x1) - max(bx0, x0))
                  * max(0, min(by1, y1) - max(by0, y0)))
        spill += whole - inside
    return {"bare": bare * cell * cell, "doubled": doubled * cell * cell,
            "spill": spill}
