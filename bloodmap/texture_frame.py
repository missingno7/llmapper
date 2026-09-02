"""Where a material sits in the world, so Build's fields can be derived from it.

The fields on a Blood wall -- `x_repeat`, `x_panning`, `y_repeat`, `y_panning`
and two flip bits -- do not say where a texture is. They say where it is
*relative to that one wall*, which is why a generator that fills them in per
wall produces a map whose textures restart at every vertex. Splitting a facade
to hang a doorway off it moves no stone in the world and should change no
pixel; in the per-wall representation it changes eight fields on two walls and
nobody can say what they should now be.

XMapEdit solves this **sequentially**. Its `.` key walks from the wall under
the cursor through `point2` and `nextwall`, carrying panning from each wall to
the next; the campaign's mappers drew first and pressed it afterwards. That is
a fix for a global fact applied one step at a time, and it works because the
step relation is affine: the accumulated offset after n walls does not depend
on when you pressed the key.

So this module says the global fact directly. A :class:`WallRunFrame` is a
material projected onto a RUN of walls from an origin at a scale; a
:class:`SurfaceFrame` is the same for a floor or ceiling. Resolving a frame
fills the Build fields in closed form from world coordinates, in one pass, in
an order nobody has to think about -- and the editor's own routine, ported
below as :func:`auto_align_walls`, then has nothing left to change. That
equality is the test this module is built to pass.

The law, read from the editor rather than re-derived
====================================================

**`AlignWalls`** (`xmapedit/src_blood/xmpmaped.cpp:3024-3050`), the whole of
the wall half in four lines:

.. code-block:: c

    t = (wall[w0_pan].xpanning + (wall[w0_rep].xrepeat<<3)) % tilesizx[nTile];
    wall[w1_pan].xpanning = t;
    wall[w1_rep].yrepeat  = wall[w0_rep].yrepeat;
    wall[w1_pan].ypanning = ((z1-z0) * first_yRepeat) / (tilesizy[nTile]<<3)
                            + wall[w0_pan].ypanning;

So a wall consumes exactly ``x_repeat * 8`` texels of its material, panning is
a texel offset modulo the tile width, the vertical scale is carried unchanged
along a run, and the vertical phase shifts by the peg-height difference scaled
into panning units. Both pannings are `uint8_t` and wrap.

**`GetWallZPeg`** (`:2991-3022`) is where the texture hangs from:

* one-sided: the sector's ceiling, or its floor under `kWallOrgBottom`
  (cstat 4, `common_game.h:345`);
* two-sided: the sector's ceiling under `kWallOrgOutside` (cstat 4 again --
  the same bit means "outside" on a two-sided wall), otherwise the top step's
  ceiling and then, if there is also a bottom step, the bottom step's floor.
  The second `if` is not an `else`: a wall with both steps pegs to the bottom
  one.

**`ED32_AutoAlignWalls`** (`:3070-3145`) is the traversal, and the traversal is
the reason a run is not a sector loop. From `w0` it takes `w1 = point2(w0)`;
having aligned `w1` it recurses, and when it runs out it continues with
``w1 = wall[wall[w1].nextwall].point2`` -- i.e. it steps *around the vertex
into the neighbouring sector*. That is how a facade continues past a doorway,
and it is exactly what a per-sector pass cannot do. It stops at a wall already
visited, at the back of the starting wall, at a one-sided wall with no
neighbour, and at any wall whose `picnum` differs or which `wallVisible`
(`:1500-1525`) says is not drawn.

**The flags, from the key binding** (`maproc.cpp:1146-1151`):

.. code-block:: c

    if (searchwall != searchwall2)  flags |= 0x20;   // cursor on a swapped band
    if (key == KEY_COMMA)           flags |= 0x10;   // ',' walks lastwall
    if (!shift)                     flags |= 0x01;   // recurse
    if (ctrl)                       flags |= 0x04;   // carry the scale

Which settles a thing the brief had the other way round: **0x01 is set when
shift is NOT held**, so the recursive whole-run align is plain ``.`` and
``>`` (shift+period) aligns exactly one neighbour. `AutoAlignWalls`
(`:3205-3216`) then runs the recursion **twice** with a fresh visited-list,
so a correct map must be a fixed point of two passes, not one.

**`fixxrepeat` / `getlenbyrep`** (`xmpmaped.h:279-290`) carry the scale:
``lenrepquot = (len0 << 12) / xrepeat0`` and then ``xrepeat = (len<<12 +
2048) / lenrepquot``, which is "the same texels per world unit, rounded to
the nearest". Lengths are `approxDist` (`common_game.h:1004-1012`), Build's
octagonal approximation, **not** the Euclidean length -- a detail that
matters for every diagonal wall.

Floors and ceilings
===================

`setup_globals_cf1` (`NBlood/source/build/src/engine.cpp:2802-2882`) with
`calc_globalshifts` (`:2795-2800`). For a tile of width ``2**k``:

* `globalxpanning = globalposx << 14` (`:2834`), then
  ``<<= (globalxshift + 6)`` (`:2880`) with ``globalxshift = 8 - k``
  (`:2797`) -- so the world coordinate reaches the texture lookup shifted by
  ``28 - k``, and the texel index is the top `k` bits: ``posx >> 4``.
  **Sixteen world units per texel**, whatever the tile size.
* `globalorientation & 8` increments both shifts (`:2799`), giving
  ``posx >> 3``: **eight world units per texel**. That is the "expanded" bit,
  and it makes the tile cover half as much world, not twice as much.
* `globalxpanning += xpanning << 24` (`:2881`), so one panning step is
  ``tilesizx/256`` texels -- 256 steps span exactly one tile whatever its
  size, which in world units is ``16 * tilesizx / 256 = tilesizx / 16``.
* `globalypanning = -(globalposy << 14)` (`:2835`): the v axis runs against
  world y.
* Bit 4 swaps the two axes (`:2856-2861`), bit 16 negates u (`:2862`), bit 32
  negates v (`:2863`), and bit 64 puts the origin on `wall[sec->wallptr]` with
  u along that wall (`:2843-2849`).

A 64-wide tile therefore covers 1024 world units unexpanded and 512 expanded,
which is why a 1024 crate whose corner sits on the 1024 grid wears a whole
tile and one that does not wears a cut one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

#: `common_game.h:344-353`. The two "origin" names are the same bit: on a
#: one-sided wall cstat 4 means "hang from the floor", on a two-sided wall it
#: means "hang from this sector's ceiling rather than from the step".
WALL_SWAP = 0x0002
WALL_ORG_BOTTOM = 0x0004
WALL_ORG_OUTSIDE = 0x0004
WALL_FLIP_X = 0x0008
WALL_FLIP_Y = 0x0100
WALL_FLIP_MASK = 0x0108
WALL_MASKED = 0x0010
WALL_ONE_WAY = 0x0020

#: `engine.cpp:2797` + `:2880`: the world coordinate arrives at the texture
#: lookup shifted so that a texel is sixteen world units wide.
FLOOR_UNITS_PER_TEXEL = 16
#: `engine.cpp:2799`: the expanded bit halves it.
FLOOR_EXPANDED = 0x08
FLOOR_SWAP_AXES = 0x04
FLOOR_FLIP_X = 0x10
FLOOR_FLIP_Y = 0x20
FLOOR_RELATIVE = 0x40

#: `AlignWalls` works modulo 256 in both pannings: they are `uint8_t`.
PANNING_PERIOD = 256

#: Where the campaign stops carrying a run. Not a guess: over the 43 campaign
#: maps a reflex join continues the texture a quarter of the time against
#: three quarters for a bend, and the editor's traversal has no angle test at
#: all -- it is the mappers who stop at an outside corner.
RUN_BREAK_DEGREES = 100.0


class FrameError(ValueError):
    """A frame was asked for something the geometry cannot answer."""


# ---------------------------------------------------------------------------
# the engine's own arithmetic, transcribed
# ---------------------------------------------------------------------------

def approx_dist(dx: int, dy: int) -> int:
    """`common_game.h:1004-1012`, Build's octagonal distance.

    The editor measures every wall with this, so a frame that uses the
    Euclidean length disagrees with `fixxrepeat` on every diagonal.
    """
    dx, dy = abs(int(dx)), abs(int(dy))
    if dx > dy:
        dy = (3 * dy) >> 3
    else:
        dx = (3 * dx) >> 3
    return dx + dy


def c_div(numerator: int, denominator: int) -> int:
    """C integer division: truncates toward zero, where Python floors.

    Not a detail. `AlignWalls`'s y term (`:3043`) is
    ``((z1-z0) * yrepeat) / (tilesizy<<3)`` and the numerator is negative
    whenever the next wall pegs higher than this one -- which is every lintel,
    every sill and every kerb return. Python's `//` gives -1 where C gives 0,
    and -1 becomes `ypanning` 255. Thirty-six walls of the pattern zoo read as
    misaligned by exactly that one step until this function existed.
    """
    quotient = abs(int(numerator)) // abs(int(denominator))
    return -quotient if (numerator < 0) != (denominator < 0) else quotient


def _fields(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def wall_length(level: Any, index: int) -> int:
    """`gameutil.cpp:899-903 getWallLength`."""
    a = _fields(level.walls[index])
    b = _fields(level.walls[int(a["point2"])])
    return approx_dist(int(b["x"]) - int(a["x"]), int(b["y"]) - int(a["y"]))


def sector_of_wall(level: Any, index: int) -> int:
    for sector_id, sector in enumerate(level.sectors):
        fields = _fields(sector)
        start = int(fields["wall_ptr"])
        if start <= index < start + int(fields["wall_count"]):
            return sector_id
    raise FrameError(f"wall {index} belongs to no sector")


def sector_index(level: Any) -> list[int]:
    """Wall -> sector, once, because `sector_of_wall` is a linear scan."""
    out = [-1] * len(level.walls)
    for sector_id, sector in enumerate(level.sectors):
        fields = _fields(sector)
        start = int(fields["wall_ptr"])
        for index in range(start, start + int(fields["wall_count"])):
            if 0 <= index < len(out):
                out[index] = sector_id
    return out


def wall_z_peg(level: Any, index: int, owners: Sequence[int] | None = None) -> int:
    """`xmpmaped.cpp:2991-3022 GetWallZPeg`, transcribed clause for clause.

    Note the two `if`s in the two-sided branch are not an if/else: a wall with
    a top step AND a bottom step ends up pegged to the bottom one, because the
    second assignment overwrites the first. Reproduced deliberately -- this is
    the law, not a tidy version of it.
    """
    fields = _fields(level.walls[index])
    sector_id = (owners[index] if owners is not None
                 else sector_of_wall(level, index))
    here = _fields(level.sectors[sector_id])
    nxt = int(fields["next_sector"])
    if nxt < 0:
        if int(fields["cstat"]) & WALL_ORG_BOTTOM:
            return int(here["floor_z"])
        return int(here["ceiling_z"])
    there = _fields(level.sectors[nxt])
    if int(fields["cstat"]) & WALL_ORG_OUTSIDE:
        return int(here["ceiling_z"])
    z = int(here["ceiling_z"])
    if int(there["ceiling_z"]) > int(here["ceiling_z"]):
        z = int(there["ceiling_z"])
    if int(there["floor_z"]) < int(here["floor_z"]):
        z = int(there["floor_z"])
    return z


def wall_visible(level: Any, index: int,
                 owners: Sequence[int] | None = None) -> bool:
    """`xmpmaped.cpp:1500-1525 wallVisible`.

    The same law `render_slots` states for the middle band, in the shape the
    aligner uses it: a two-sided wall that is neither masked nor one-way is
    drawn only where a step exposes it, and a wall in a zero-height sector is
    not drawn at all.
    """
    fields = _fields(level.walls[index])
    sector_id = (owners[index] if owners is not None
                 else sector_of_wall(level, index))
    here = _fields(level.sectors[sector_id])
    nxt = int(fields["next_sector"])
    cstat = int(fields["cstat"])
    if nxt >= 0 and not (cstat & WALL_MASKED) and not (cstat & WALL_ONE_WAY):
        there = _fields(level.sectors[nxt])
        return (int(here["ceiling_z"]) < int(there["ceiling_z"])
                or int(here["floor_z"]) > int(there["floor_z"]))
    return abs(int(here["floor_z"]) - int(here["ceiling_z"])) > 0


def align_pair(tile_size: tuple[int, int], z0: int, z1: int,
               w0_pan: dict, w0_rep: dict, w1_pan: dict, w1_rep: dict,
               *, do_xpan: bool = True) -> bool:
    """`AlignWalls` (`xmpmaped.cpp:3024-3050`), fields in, fields out.

    Mutates the `w1_*` dicts and returns whether anything changed, exactly as
    the editor's `char` return does. The four separate wall arguments are not
    redundancy: on a bottom-swapped join the panning is read from one wall and
    the repeat from another (`ED32_AutoAlignWalls_GetWall`, `:3058-3061`).
    """
    width, height = int(tile_size[0]), int(tile_size[1])
    if width == 0 or height == 0:
        return False
    changed = False
    if do_xpan:
        t = (int(w0_pan["x_panning"]) + (int(w0_rep["x_repeat"]) << 3)) % width
        if t != int(w1_pan["x_panning"]):
            w1_pan["x_panning"] = t
            changed = True
    first_y_pan = int(w0_pan["y_panning"])
    first_y_repeat = int(w0_rep["y_repeat"])
    offset = c_div((int(z1) - int(z0)) * first_y_repeat, height << 3)
    second_y_pan = (offset + first_y_pan) % PANNING_PERIOD
    if first_y_repeat != int(w1_rep["y_repeat"]):
        w1_rep["y_repeat"] = first_y_repeat
        changed = True
    if second_y_pan != int(w1_pan["y_panning"]):
        w1_pan["y_panning"] = second_y_pan
        changed = True
    return changed


def _swapped(level: Any, bot: bool, index: int) -> int:
    """`ED32_AutoAlignWalls_GetWall` (`xmpmaped.cpp:3058-3061`)."""
    fields = _fields(level.walls[index])
    if bot and (int(fields["cstat"]) & WALL_SWAP) and int(fields["next_wall"]) >= 0:
        return int(fields["next_wall"])
    return index


def _last_wall(level: Any, index: int, owners: Sequence[int]) -> int:
    """Build's `lastwall`: the wall whose `point2` is this one, in its loop."""
    sector_id = owners[index]
    fields = _fields(level.sectors[sector_id])
    start = int(fields["wall_ptr"])
    for other in range(start, start + int(fields["wall_count"])):
        if int(_fields(level.walls[other])["point2"]) == index:
            return other
    return index


def auto_align_walls(level: Any, start_wall: int, *, flags: int = 0x01,
                     art_sizes: dict[int, tuple[int, int]] | None = None,
                     owners: Sequence[int] | None = None) -> int:
    """`AutoAlignWalls` (`xmpmaped.cpp:3205-3216`) including its second pass.

    Returns the number of walls whose fields it changed. **On a map whose
    frames are resolved this must return 0**, which is what
    `tests/test_texture_frame` asserts: the editor's sequential fix has
    nothing left to do once the global fact has been stated directly.
    """
    owners = list(owners) if owners is not None else sector_index(level)
    sizes = art_sizes if art_sizes is not None else {}
    count = _recurse(level, start_wall, flags, sizes, owners, set(), 0, [None])
    _recurse(level, start_wall, flags, sizes, owners, set(), 0, [None])
    return count


def _recurse(level: Any, w0: int, flags: int, sizes: dict, owners: Sequence[int],
             done: set[int], depth: int, carry: list) -> int:
    """`ED32_AutoAlignWalls` (`xmpmaped.cpp:3070-3145`).

    `carry` holds the static locals the C keeps between recursions:
    `[lenrepquot, wall0, cstat0, numaligned]`.
    """
    reverse = bool(flags & 0x10)
    bot = bool(flags & 0x20)

    def face(index: int) -> Any:
        return _fields(level.walls[index])

    def step(index: int) -> int:
        return (_last_wall(level, index, owners) if reverse
                else int(face(index)["point2"]))

    w1 = step(w0)
    w0b = _swapped(level, bot, w0)
    tile = int(face(w0b)["picnum"])

    if depth == 0:
        repeat = int(face(w0)["x_repeat"])
        length = wall_length(level, w0)
        carry[:] = [((length << 12) // repeat) if repeat > 0 else (length << 12),
                    w0, int(face(w0b)["cstat"]) & WALL_FLIP_MASK, 0]
        done.add(w0)

    while True:
        w1b = _swapped(level, bot, w1)
        if w1 in done:
            break
        done.add(w1)
        if int(face(w1)["next_wall"]) == w0:
            break
        if int(face(w1b)["picnum"]) == tile and wall_visible(level, w1b, owners):
            if (flags & 0x04) and w1 != carry[1] and carry[0]:
                #: `fixxrepeat`, xmpmaped.h:285-289.
                value = ((wall_length(level, w1) << 12) + (1 << 11)) // carry[0]
                face(w1)["x_repeat"] = max(1, min(255, value))
            size = sizes.get(tile)
            if size and align_pair(size, wall_z_peg(level, w0, owners),
                                   wall_z_peg(level, w1, owners),
                                   face(w0b), face(w0), face(w1b), face(w1)):
                carry[3] += 1
            cstat = int(face(w1b)["cstat"])
            face(w1b)["cstat"] = (cstat & ~WALL_FLIP_MASK) | carry[2]
            if not (flags & 0x01):
                return carry[3]
            if int(face(w1)["next_wall"]) < 0:
                w0 = w1
                w0b = _swapped(level, bot, w0)
                w1 = step(w0)
                continue
            _recurse(level, w1, flags, sizes, owners, done, depth + 1, carry)
        if int(face(w1)["next_wall"]) < 0:
            break
        neighbour = int(face(w1)["next_wall"])
        w1 = (_last_wall(level, neighbour, owners) if reverse
              else int(face(neighbour)["point2"]))
    return carry[3]


# ---------------------------------------------------------------------------
# the same law, read as a question instead of as an assignment
# ---------------------------------------------------------------------------

#: Under five degrees a join is the same straight face, split for some other
#: reason -- a doorway hung off it, a shade change, a sector boundary.
COLLINEAR_DEGREES = 5.0


def join_turn(level: Any, this: int, nxt: int) -> float:
    """The turn in degrees from one wall onto the next, 0 for collinear."""
    a, b = _fields(level.walls[this]), _fields(level.walls[nxt])
    c = _fields(level.walls[int(b["point2"])])
    ux, uy = int(b["x"]) - int(a["x"]), int(b["y"]) - int(a["y"])
    vx, vy = int(c["x"]) - int(b["x"]), int(c["y"]) - int(b["y"])
    if (ux or uy) and (vx or vy):
        return abs(math.degrees(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)))
    return 0.0


def join_class(level: Any, this: int, nxt: int) -> str:
    """`"<collinear|bend|reflex> <solid-solid|solid-portal|portal-portal>"`."""
    turn = join_turn(level, this, nxt)
    angle = ("collinear" if turn < COLLINEAR_DEGREES
             else "reflex" if turn > RUN_BREAK_DEGREES else "bend")
    a, b = _fields(level.walls[this]), _fields(level.walls[nxt])
    left, right = int(a["next_sector"]) >= 0, int(b["next_sector"]) >= 0
    kind = ("portal-portal" if left and right
            else "solid-portal" if left or right else "solid-solid")
    return f"{angle} {kind}"


def join_continues(level: Any, this: int, nxt: int,
                   tile_size: tuple[int, int],
                   owners: Sequence[int] | None = None) -> tuple[bool, bool]:
    """Does the material continue across this join, in x and in y?

    `AlignWalls` read as a predicate. The two axes are separate because they
    fail for different reasons: x breaks when a run is restarted at a vertex,
    y when each wall is anchored to its own sector's height rather than to the
    run it belongs to.
    """
    a, b = _fields(level.walls[this]), _fields(level.walls[nxt])
    width, height = int(tile_size[0]), int(tile_size[1])
    if not width or not height:
        raise FrameError(f"tile {int(a['picnum'])} has no size")
    want_x = (int(a["x_panning"]) + (int(a["x_repeat"]) << 3)) % width
    repeat = int(a["y_repeat"])
    z0 = wall_z_peg(level, this, owners)
    z1 = wall_z_peg(level, nxt, owners)
    want_y = (c_div((z1 - z0) * repeat, height << 3)
              + int(a["y_panning"])) % PANNING_PERIOD
    return (int(b["x_panning"]) == want_x,
            int(b["y_repeat"]) == repeat and int(b["y_panning"]) == want_y)


def continuity_rows(level: Any,
                    art_sizes: dict[int, tuple[int, int]] | None = None
                    ) -> dict[str, dict[str, int]]:
    """Every same-tile join in one map, classified and tested.

    A join is a wall and its `point2` inside the same sector loop -- the pairs
    a person sees as one continuous face. Joins whose tile has no ART entry are
    not counted: an unmeasurable join is not a passing one.
    """
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes()
    owners = sector_index(level)
    out: dict[str, dict[str, int]] = {}
    for sector in level.sectors:
        fields = _fields(sector)
        start = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        for index in range(start, start + count):
            a = _fields(level.walls[index])
            nxt = int(a["point2"])
            if not (start <= nxt < start + count) or nxt == index:
                continue
            tile = int(a["picnum"])
            if tile != int(_fields(level.walls[nxt])["picnum"]):
                continue
            size = art_sizes.get(tile)
            if not size or not size[0] or not size[1]:
                continue
            x_ok, y_ok = join_continues(level, index, nxt, size, owners)
            row = out.setdefault(join_class(level, index, nxt),
                                 {"n": 0, "x": 0, "y": 0})
            row["n"] += 1
            row["x"] += int(x_ok)
            row["y"] += int(y_ok)
    return out


# ---------------------------------------------------------------------------
# the frames: what the source says, instead of what the fields say
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WallRunFrame:
    """A material projected onto a RUN of walls from an origin, at a scale.

    This is the object the per-wall fields could not be. `x_panning` says
    where a texture starts *on one wall*; a frame says where it starts on the
    world, and every wall of the run derives its four fields from that. Cut the
    run in half to hang a doorway off it and nothing here changes, which is the
    whole point -- the doorway is not a fact about the stone.

    `texels_per_unit` is the scale the editor carries with `lenrepquot`
    (`xmpmaped.h:279-289`); the field is texels per world unit, so a wall of
    length L takes ``L * texels_per_unit / 8`` as its `x_repeat`.

    `v0` is a world z, not a wall: the vertical phase is affine in the peg
    height (`AlignWalls`, `:3044`), so stating the height the material hangs
    from fixes every wall of the run at once, whatever each one's own sector
    does. Left None it is taken from the run's first wall, which reproduces the
    editor exactly.
    """

    tile: int
    #: Texels per world unit. 1/8 is one tile every 8*tilesizx units, which is
    #: what this repo has always called the natural scale.
    texels_per_unit: float = 1.0 / 8.0
    #: Texel offset at the run's first wall start. Non-zero only when a run is
    #: deliberately continued from somewhere else.
    u0: int = 0
    v0: int | None = None
    y_repeat: int = 8
    flip: int = 0

    def __post_init__(self) -> None:
        if self.texels_per_unit <= 0:
            raise FrameError("a material projected at zero scale is not a frame")
        if self.flip & ~WALL_FLIP_MASK:
            raise FrameError(f"flip {self.flip:#x} is not in kWallFlipMask")


@dataclass(frozen=True)
class SurfaceFrame:
    """A material on a floor or ceiling, anchored somewhere in particular.

    `anchor` is the whole question for a raised solid. The campaign fits the
    tile to the crate -- 90 of its 247 crate tops put their first corner on the
    tile grid and 11 use `floorstat 64` to make the grid start at the first
    wall -- and a generator that leaves the default fits the crate to nothing,
    so a 1024 box that is not on a 1024 world boundary wears a cut tile.

    * ``"world"``: Build's default. The grid starts at world (0, 0).
    * ``"corner"``: panning derived so the grid starts at `anchor_point`.
    * ``"first_wall"``: `floorstat 64`, the engine's own relative mode
      (`engine.cpp:2843-2849`), which also turns u along the first wall.
    """

    tile: int
    anchor: str = "world"
    anchor_point: tuple[int, int] | None = None
    expanded: bool = False
    swap_axes: bool = False
    flip_x: bool = False
    flip_y: bool = False

    def __post_init__(self) -> None:
        if self.anchor not in ("world", "corner", "first_wall"):
            raise FrameError(f"unknown anchor {self.anchor!r}")
        if self.anchor == "corner" and self.anchor_point is None:
            raise FrameError("a corner anchor needs the corner")


def units_per_texel(expanded: bool = False) -> int:
    """`engine.cpp:2797-2799` with `:2880`: 16 world units a texel, 8 expanded."""
    return FLOOR_UNITS_PER_TEXEL // 2 if expanded else FLOOR_UNITS_PER_TEXEL


def surface_panning(point: tuple[int, int], tile_size: tuple[int, int], *,
                    expanded: bool = False) -> tuple[int, int]:
    """The floor panning that puts the tile grid origin at `point`.

    From `engine.cpp:2834-2835` and `:2881`: the texel index is
    ``(posx >> shift) + xpanning * tilesizx / 256`` and the v axis is negated
    (`globalypanning = -(globalposy<<14)`), so solving each for "index 0 at
    this world point" gives the pair below. Exact whenever the tile side
    divides 256, which every Blood flat tile does -- `flat-tile-power-of-two`
    is the rule that guarantees it.
    """
    width, height = int(tile_size[0]), int(tile_size[1])
    if width <= 0 or height <= 0:
        raise FrameError("a tile with no size cannot be anchored")
    shift = 3 if expanded else 4
    u = (-(int(point[0]) >> shift) * 256 // width) % PANNING_PERIOD
    v = ((int(point[1]) >> shift) * 256 // height) % PANNING_PERIOD
    return u, v


def surface_is_whole(point: tuple[int, int], tile_size: tuple[int, int], *,
                     panning: tuple[int, int] = (0, 0),
                     expanded: bool = False) -> bool:
    """Does the tile grid have a corner exactly at `point`?

    The question behind "the crate tops wear cut tiles": with the default
    panning a 64-wide tile has a grid line every 1024 world units unexpanded
    and every 512 expanded, and a crate corner anywhere else is mid-tile.
    """
    want = surface_panning(point, tile_size, expanded=expanded)
    return (int(panning[0]) % PANNING_PERIOD == want[0]
            and int(panning[1]) % PANNING_PERIOD == want[1])


def sector_corner(level: Any, sector_id: int) -> tuple[int, int]:
    """The corner a raised solid's material should start from.

    Lowest x, then lowest y, of the sector's own walls: a choice that does not
    depend on which wall the list happens to begin with, so re-emitting the
    same solid twice anchors it in the same place.
    """
    fields = _fields(level.sectors[sector_id])
    start = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    points = [(int(_fields(level.walls[i])["x"]), int(_fields(level.walls[i])["y"]))
              for i in range(start, start + count)]
    if not points:
        raise FrameError(f"sector {sector_id} has no walls")
    return min(points)


def resolve_surface(level: Any, sector_id: int, frame: SurfaceFrame,
                    surface: str = "floor",
                    art_sizes: dict[int, tuple[int, int]] | None = None
                    ) -> dict[str, int]:
    """The `*_picnum`, `*_stat` and `*_panning` fields this frame implies."""
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes()
    size = art_sizes.get(int(frame.tile))
    fields = _fields(level.sectors[sector_id])
    stat = int(fields[f"{surface}_stat"])
    for bit, on in ((FLOOR_EXPANDED, frame.expanded),
                    (FLOOR_SWAP_AXES, frame.swap_axes),
                    (FLOOR_FLIP_X, frame.flip_x),
                    (FLOOR_FLIP_Y, frame.flip_y),
                    (FLOOR_RELATIVE, frame.anchor == "first_wall")):
        stat = (stat | bit) if on else (stat & ~bit)
    out = {f"{surface}_picnum": int(frame.tile), f"{surface}_stat": stat,
           f"{surface}_x_panning": 0, f"{surface}_y_panning": 0}
    point = frame.anchor_point
    if frame.anchor == "corner" and size:
        if point is None:
            point = sector_corner(level, sector_id)
        u, v = surface_panning(point, size, expanded=frame.expanded)
        out[f"{surface}_x_panning"] = u
        out[f"{surface}_y_panning"] = v
    return out


def apply_surface(level: Any, sector_id: int, frame: SurfaceFrame,
                  surface: str = "floor",
                  art_sizes: dict[int, tuple[int, int]] | None = None) -> int:
    """Write `resolve_surface`'s answer onto the sector. Fields changed."""
    fields = _fields(level.sectors[sector_id])
    changed = 0
    for key, value in resolve_surface(level, sector_id, frame, surface,
                                      art_sizes).items():
        if int(fields[key]) != value:
            fields[key] = value
            changed += 1
    return changed


# ---------------------------------------------------------------------------
# runs, and resolving a frame onto one
# ---------------------------------------------------------------------------

def run_from(level: Any, start: int, *,
             art_sizes: dict[int, tuple[int, int]] | None = None,
             owners: Sequence[int] | None = None,
             break_degrees: float = RUN_BREAK_DEGREES) -> list[int]:
    """The walls a material runs across, starting here.

    `ED32_AutoAlignWalls`'s traversal (`:3096-3144`) with one addition: the
    editor has no angle test and will carry a texture round an outside corner
    if you let it, because a person is watching. The campaign's mappers stop
    there -- 19% of reflex solid-solid joins continue against 68% of bends --
    so a generated run stops there too, and `break_degrees` is the one knob.

    Portal walls are INCLUDED, which is the difference from
    `texture_align.align_wall_runs`: the visible band of a portal wall is the
    same material continuing, and refusing to carry it is exactly what puts a
    seam at every doorway of a facade.
    """
    owners = list(owners) if owners is not None else sector_index(level)
    tile = int(_fields(level.walls[start])["picnum"])
    out = [start]
    seen = {start}
    current = start
    while True:
        nxt = _next_on_run(level, current, tile, owners, seen, break_degrees)
        if nxt is None:
            break
        out.append(nxt)
        seen.add(nxt)
        current = nxt
    return out


def _next_on_run(level: Any, current: int, tile: int, owners: Sequence[int],
                 seen: set[int], break_degrees: float) -> int | None:
    """One step of the editor's traversal, with the campaign's angle break.

    Around the shared vertex: `point2` first, then, while that wall is not the
    material, across its `next_wall` into the neighbouring sector -- which is
    `w1 = wall[wall[w1].nextwall].point2` at `:3142-3143`.
    """
    candidate = int(_fields(level.walls[current])["point2"])
    guard = 0
    while candidate not in seen and guard < 16:
        guard += 1
        face = _fields(level.walls[candidate])
        if int(face["picnum"]) == tile and wall_visible(level, candidate, owners):
            if join_turn(level, current, candidate) > break_degrees:
                return None
            return candidate
        neighbour = int(face["next_wall"])
        if neighbour < 0:
            return None
        candidate = int(_fields(level.walls[neighbour])["point2"])
    return None


def resolve_run(level: Any, run: Sequence[int], frame: WallRunFrame,
                art_sizes: dict[int, tuple[int, int]] | None = None,
                owners: Sequence[int] | None = None) -> int:
    """Write the frame onto the run's walls. Returns how many fields changed.

    Closed form in the sense that matters: each wall's fields come from the
    frame and from that wall's own world geometry, never from whatever a
    previous pass happened to leave on its neighbour, so the result does not
    depend on the order walls appear in the file and a portal cut changes
    nothing.

    The one running total is the texel cursor, and it is a prefix sum of
    ``x_repeat * 8`` **because the engine's own accumulator is** (`AlignWalls`,
    `:3036`). Using the true world distance instead would drift from the editor
    by the accumulated rounding of every wall before it, and
    :func:`auto_align_walls` would have something to change -- which is the
    test this has to pass.
    """
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes()
    owners = list(owners) if owners is not None else sector_index(level)
    size = art_sizes.get(int(frame.tile))
    if not size or not size[0] or not size[1]:
        raise FrameError(f"tile {frame.tile} has no ART size to project")
    width, height = int(size[0]), int(size[1])
    v0 = (frame.v0 if frame.v0 is not None
          else wall_z_peg(level, run[0], owners))
    cursor = int(frame.u0)
    changed = 0
    for index in run:
        face = _fields(level.walls[index])
        length = wall_length(level, index)
        repeat = max(1, min(255, int(round(length * frame.texels_per_unit))))
        y_panning = c_div((wall_z_peg(level, index, owners) - v0)
                          * int(frame.y_repeat), height << 3) % PANNING_PERIOD
        wanted = {
            "picnum": int(frame.tile),
            "x_repeat": repeat,
            "x_panning": cursor % width,
            "y_repeat": int(frame.y_repeat),
            "y_panning": y_panning,
            "cstat": (int(face["cstat"]) & ~WALL_FLIP_MASK) | int(frame.flip),
        }
        for key, value in wanted.items():
            if int(face[key]) != value:
                face[key] = value
                changed += 1
        cursor += repeat << 3
    return changed


def wall_u_origin(level: Any, index: int,
                  art_sizes: dict[int, tuple[int, int]] | None = None) -> int:
    """Where this wall's material starts, as a texel offset at its start point.

    The reader half: with this a run can be RECOVERED from an original map --
    two walls belong to the same projection when their u-origins agree once
    the texels between them are taken out, which is what `join_continues`
    tests pairwise. Kept as its own function because it is the quantity a
    person means by "where the texture starts", and nothing in the file states
    it.
    """
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes()
    face = _fields(level.walls[index])
    size = art_sizes.get(int(face["picnum"]))
    if not size or not size[0]:
        raise FrameError(f"tile {int(face['picnum'])} has no ART size")
    return int(face["x_panning"]) % int(size[0])


def frame_runs(level: Any, frames: dict[int, "WallRunFrame"], *,
               art_sizes: dict[int, tuple[int, int]] | None = None,
               owners: Sequence[int] | None = None) -> dict[str, Any]:
    """Resolve one frame per starting wall, and say what was left over.

    The leftovers are the point of the return value. A wall no frame covers is
    a wall still relying on the per-wall guess, and counting them is the only
    honest way to keep the old passes as a fallback: an uncounted fallback is
    indistinguishable from the frames not working.
    """
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes()
    owners = list(owners) if owners is not None else sector_index(level)
    covered: set[int] = set()
    runs = 0
    changed = 0
    for start in sorted(frames):
        if start in covered:
            continue
        run = [w for w in run_from(level, start, art_sizes=art_sizes,
                                   owners=owners) if w not in covered]
        if not run:
            continue
        changed += resolve_run(level, run, frames[start], art_sizes, owners)
        covered.update(run)
        runs += 1
    return {"runs": runs, "walls_framed": len(covered),
            "fields_changed": changed,
            "walls_unframed": len(level.walls) - len(covered)}


def run_partition(level: Any, *,
                  art_sizes: dict[int, tuple[int, int]] | None = None,
                  owners: Sequence[int] | None = None,
                  break_degrees: float = RUN_BREAK_DEGREES) -> list[list[int]]:
    """Every wall of the map, cut into runs, deterministically.

    Seeded from the walls that have no predecessor rather than from wall 0,
    because a run entered halfway is a different run: its frame would come
    from a wall in the middle of a facade and the half behind would be a
    separate projection. Finding the true starts first is what makes the
    partition independent of the order walls happen to sit in the file --
    which is the property the whole module exists for.
    """
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes()
    owners = list(owners) if owners is not None else sector_index(level)
    successor: dict[int, int] = {}
    for index in range(len(level.walls)):
        tile = int(_fields(level.walls[index])["picnum"])
        size = art_sizes.get(tile)
        if not size or not size[0]:
            continue
        nxt = _next_on_run(level, index, tile, owners, {index}, break_degrees)
        if nxt is not None:
            successor[index] = nxt
    has_predecessor = set(successor.values())

    out: list[list[int]] = []
    covered: set[int] = set()

    def follow(start: int) -> list[int]:
        run = [start]
        seen = {start}
        current = start
        while True:
            nxt = successor.get(current)
            if nxt is None or nxt in seen or nxt in covered:
                break
            run.append(nxt)
            seen.add(nxt)
            current = nxt
        return run

    for index in range(len(level.walls)):
        if index in covered or index in has_predecessor:
            continue
        run = follow(index)
        covered.update(run)
        out.append(run)
    #: What is left is a closed loop of one material -- a round pillar, a
    #: circular shaft -- with no start anywhere in it. Seeded in index order so
    #: the choice is at least stable.
    for index in range(len(level.walls)):
        if index in covered or index not in successor:
            continue
        run = follow(index)
        covered.update(run)
        out.append(run)
    return out


def frame_map(level: Any, *,
              art_sizes: dict[int, tuple[int, int]] | None = None,
              carry_scale: bool = True,
              break_degrees: float = RUN_BREAK_DEGREES,
              skip: set[int] | None = None,
              skip_moving: bool = True) -> dict[str, Any]:
    """Project every material onto the run it belongs to, in one pass.

    The replacement for `texture_align.align_wall_runs` and the floor-anchored
    y pass together, and it differs from them in three ways that are the whole
    of the owner's complaint:

    * a run is **not confined to a sector loop**. The editor's traversal steps
      across `next_wall` into the neighbour (`:3142-3143`), which is how a
      facade continues past a doorway; a per-sector pass cannot, so it puts a
      seam at every opening.
    * portal walls are **in** the run. Their visible band is the same material
      continuing, and the old pass refused every portal-to-portal join except
      one opted-in sector.
    * **y comes from the run**, not from each wall's own sector. Anchoring
      each wall to its own height is what broke the phase at every kerb, sill
      and lintel -- `bend solid-portal` y 31% in the city against the
      campaign's 61%.

    `carry_scale` takes the texels-per-unit from each run's first wall, which
    is the editor's ctrl-flag (`fixxrepeat`, `xmpmaped.h:285-289`): the scale
    a person chose is kept and merely made uniform along the run.

    **A moving sector's walls are not projectable and are skipped.** Their
    length is not a fact about the world: `TranslateSector` moves the flagged
    ends every tick while `x_repeat` stays where it was, so the material
    stretches as the mechanism runs. A curtain's fabric repeat is authored for
    the span the cloth hangs ACROSS and the file is saved at the gathered pose,
    so deriving a scale from the drawn length -- which is what a run frame does
    -- silently replaces a designed number with a meaningless one. The zoo's
    read-back caught exactly that the first time this pass ran: texel 2.0
    became 0.02.
    """
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes()
    owners = sector_index(level)
    skip = set(skip or ())
    moving = 0
    if skip_moving:
        for sector_id, sector in enumerate(level.sectors):
            if int(_fields(sector)["type"]) not in MOVING_SECTOR_TYPES:
                continue
            fields = _fields(sector)
            start = int(fields["wall_ptr"])
            for wall in range(start, start + int(fields["wall_count"])):
                skip.add(wall)
                moving += 1
    runs = run_partition(level, art_sizes=art_sizes, owners=owners,
                         break_degrees=break_degrees)
    framed = changed = singles = 0
    for run in runs:
        run = [w for w in run if w not in skip]
        if not run:
            continue
        head = _fields(level.walls[run[0]])
        tile = int(head["picnum"])
        length = wall_length(level, run[0]) or 1
        scale = (int(head["x_repeat"]) * 8.0 / length if carry_scale
                 else 1.0 / 8.0)
        frame = WallRunFrame(
            tile=tile,
            texels_per_unit=max(scale, 1e-6),
            u0=int(head["x_panning"]),
            v0=wall_z_peg(level, run[0], owners),
            y_repeat=int(head["y_repeat"]) or 8,
            flip=int(head["cstat"]) & WALL_FLIP_MASK,
        )
        changed += resolve_run(level, run, frame, art_sizes, owners)
        framed += len(run)
        singles += int(len(run) == 1)
    return {"runs": len(runs), "walls_framed": framed,
            "single_wall_runs": singles, "fields_changed": changed,
            "walls_unframed": len(level.walls) - framed,
            "walls_left_to_their_mechanism": moving,
            "basis": ("one WallRunFrame per run, resolved in closed form; "
                      "the editor's AutoAlignWalls has nothing left to change")}


#: The campaign's crate class: the six floor tiles the owner walk named, and
#: the measured practice on the 110 raised tops that wear them -- 62% use the
#: expanded bit, 71% land the tile grid on the crate's own corner, 59% carry a
#: panning, 6% use first-wall-relative alignment. The city's eleven use none of
#: it, which is why a 1024 box that is not on a 1024 world boundary wears a cut
#: tile: the campaign fits the tile to the crate and the city fits the crate to
#: nothing.
CRATE_FLOOR_TILES = frozenset({95, 298, 375, 452, 456, 462})

#: The sector types whose geometry moves. A wall of one of these has no
#: projectable length: `TranslateSector` moves its flagged end while
#: `x_repeat` stays put, so what the file records is one frame of a stretch.
MOVING_SECTOR_TYPES = frozenset({600, 602, 612, 613, 614, 615, 616, 617})


def raised_solids(level: Any, tiles: Iterable[int] | None = None) -> list[int]:
    """Sectors whose floor stands above every neighbour's: crates, plinths."""
    wanted = set(tiles) if tiles is not None else set(CRATE_FLOOR_TILES)
    out = []
    for sector_id, sector in enumerate(level.sectors):
        fields = _fields(sector)
        if wanted and int(fields["floor_picnum"]) not in wanted:
            continue
        start = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        neighbours = [int(_fields(level.walls[w])["next_sector"])
                      for w in range(start, start + count)]
        neighbours = [n for n in neighbours if n >= 0]
        if not neighbours:
            continue
        if all(int(fields["floor_z"])
               < int(_fields(level.sectors[n])["floor_z"]) for n in neighbours):
            out.append(sector_id)
    return out


def frame_raised_solids(level: Any, tiles: Iterable[int] | None = None, *,
                        art_sizes: dict[int, tuple[int, int]] | None = None,
                        expanded: bool | None = None) -> dict[str, Any]:
    """Give every raised solid a top that starts at its own corner.

    An object-anchored :class:`SurfaceFrame` per crate. `expanded` left None
    keeps whatever the sector already declares rather than imposing the
    campaign's 62%: the bit halves the world size of the tile
    (`engine.cpp:2799`) and choosing it is a look, while landing the grid on
    the corner is correctness.
    """
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes()
    solids = raised_solids(level, tiles)
    whole_before = whole_after = 0
    changed = 0
    for sector_id in solids:
        fields = _fields(level.sectors[sector_id])
        size = art_sizes.get(int(fields["floor_picnum"]))
        if not size or not size[0]:
            continue
        corner = sector_corner(level, sector_id)
        is_expanded = (bool(int(fields["floor_stat"]) & FLOOR_EXPANDED)
                       if expanded is None else bool(expanded))
        whole_before += int(surface_is_whole(
            corner, size, expanded=is_expanded,
            panning=(int(fields["floor_x_panning"]),
                     int(fields["floor_y_panning"]))))
        changed += apply_surface(
            level, sector_id,
            SurfaceFrame(tile=int(fields["floor_picnum"]), anchor="corner",
                         anchor_point=corner, expanded=is_expanded),
            "floor", art_sizes)
        whole_after += int(surface_is_whole(
            corner, size, expanded=is_expanded,
            panning=(int(fields["floor_x_panning"]),
                     int(fields["floor_y_panning"]))))
    return {"solids": len(solids), "fields_changed": changed,
            "uncut_before": whole_before, "uncut_after": whole_after,
            "basis": ("71% of the campaign's 110 raised crate tops land the "
                      "tile grid on the crate's own corner")}
