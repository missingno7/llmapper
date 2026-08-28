"""A wall is a vertical 2D surface, and a sprite on it is a rectangle.

Owner: "when you are putting wall sprites they should not occupy same
physical space, they can be next to each other or on the top of each other,
but not on the same place.  Some sprites are wider, taller, etc, so this
should be handled."  And: "you can have multiple lines of text on same wall
as long as they are in different heights"; "text can even be written
vertically... you can have a painting and description under it... text can
have different sizes"; "the whole text doesn't even need to be one colour."

What the project had instead was `props.MIN_WALL_PROP_SPACING = 384`: a
single constant reserving a fixed run of the supporting **line** around
every anchor.  One dimension, no knowledge of the size of the thing being
hung, and no knowledge of z at all -- so two signs stacked at different
heights read as a conflict while a 2,048-wide hanging dropped straight over
a word read as fine.  `tools/mine_wall_sprites.py` measures the result:

| | clashing pairs per 100 wall sprites | fully hidden |
|---|---|---|
| Gravesend, before | **18.86** | **26** |
| E1M1 / E3M2 / DWE3M1 / DWE3M10 | 6.7 - 8.0 | 0 - 4 |
| E2M1 / E6M1 / E4M9 / E3M1 | 0.0 - 3.3 | 0 - 1 |

St Gallow's nave was the worst of it: every letter of its sign sat behind
tile 847, a 2,048 x 32,768 hanging, at 100% coverage.

This module is the surface those decisions need.

**A rectangle, from the tile.**  Along the wall a sprite runs from
``-(w/2 + xofs) * x_repeat / 4`` to ``+(w - w/2 - xofs) * x_repeat / 4``;
up and down it runs by `bloodmap.placement.sprite_extent`.  Both come from
the ART, so a decal reserves a decal's worth and a window reserves a
window's.

**A plane, not a wall id.**  Two sprites collide when they lie on the same
supporting line -- including back to back, which still fights for the same
pixels -- and their rectangles intersect in *both* axes.  Stacking is
legal, which is the whole point: a caption under a painting is two
rectangles on one plane that do not overlap.

**Two different things put letters above each other**, and telling them
apart is most of the measurement.  A word written DOWNWARD -- 11 of them in
the corpus, ABALCO and CABALO and FINANCE and HOTEL and FRIES, all of them
hanging shop signs in the Death Wish maps -- sets its letters nearly
touching, at a median **1.095** drawn heights.  A sign of several LINES --
117 of those -- leaves **1.455** between them.  Counting both together, as
the first version of this did, reports 132 columns where there are 11 and a
pitch that belongs to neither.  `VERTICAL_PITCH` and `LINE_PITCH` are the
two numbers, and `knowledge/blood/design/wall-sprites-v1.json` is where they
come from.

**A text style is a parametric prefab**, the same shape as
`fixtures.Family`: `TextStyle` pins the size, the palette and the shade and
frees the words, carries its provenance, and steps down its own size ladder
when the wall is short rather than failing. `STYLES` is the corpus's own
table of them.

**Per-letter palette and size.**  `text()` takes a scalar or a sequence for
`palette`, `size` and `shade`.  A sequence **pads with its last value**, so
``size=(112, 72)`` is a drop capital and ``palette=("warning", "sign")`` is a
coloured initial; wrap it in `cycle()` for a repeating pattern.
"""

from __future__ import annotations

import hashlib
import math
import pathlib
from dataclasses import dataclass, field

from bloodmap.art import read_art_directory
from bloodmap.lettering import (
    LETTER_CSTAT, LETTER_HEIGHT, LETTER_SHADE, LETTER_WIDTH, PALETTES, PITCH,
    SIZES, tile_for,
)
from bloodmap.placement import (
    PLAYER_HEIGHT, PLAYER_WIDTH, inward_normal, sprite_extent,
)

ALIGN_MASK = 0x30
ALIGN_WALL = 0x10
XFLIP = 0x04

#: How far apart two supporting lines may be and still be one wall.  Props
#: are mounted a tenth of a body width off the surface and signs a little
#: more, so coplanar things differ by a few units; a genuine second wall is
#: hundreds away.  Matches `tools/mine_wall_sprites.py`.
PLANE_TOLERANCE = 24.0

#: Centre-to-centre spacing for letters written DOWNWARD, as a multiple of a
#: letter's drawn height: median **1.095**, q1 1.004, q3 1.198, over 45 gaps
#: in the corpus's 11 genuine columns (ABALCO, CABALO, FINANCE, HOTEL,
#: FRIES).  Letters in a column nearly touch, which is why the first version
#: of this number -- 1.25 -- was wrong: it was measured over letters that
#: shared a point, and most of those are not columns at all but the second
#: and third LINES of ordinary horizontal signs.  That population is
#: `LINE_PITCH`, and it is a different number for a different thing.
VERTICAL_PITCH = 1.095

#: The share of a rectangle that may be covered before a placement is
#: refused.  Not zero: a couple of units of touching edge is not the fault
#: being fixed, and refusing it would make every dense composition fail.
OVERLAP_FLOOR = 0.02

#: What the campaign leaves between two stacked lines of one sign, as a
#: multiple of a letter's drawn height: median **1.455**, q1 1.247, q3
#: 1.662, over 163 gaps in 117 multi-line signs.  The gap BELOW a line is
#: therefore about 0.455 of its own height -- which is what `LINE_GAP`
#: approximates in player heights for a 64-repeat letter (2,816 z units).
LINE_PITCH = 1.455
LINE_GAP = round((LINE_PITCH - 1.0) * (64 * 4 * 11) / 16960, 3)

#: How the search moves when the asked-for spot is taken.  Along the wall
#: first -- a sign at eye level should stay at eye level -- then up and
#: down, because stacking is legal and often what the author wanted.
SLIDE_STEPS = 24
STACK_STEPS = 12
#: The vertical range a stacked search will use, in player heights above
#: the floor.  Below 0.25 a sprite is on the skirting; above 2.6 it is out
#: of sight in most of this city's rooms.
STACK_LOW, STACK_HIGH = 0.25, 2.60
#: How close to the floor or the ceiling a reserved rectangle may come.
#: `resolve_anchor` clamps a wall sprite to 256 units inside the room, and a
#: reservation that ignored that would be honoured by moving the sprite.
ROOM_MARGIN = 256


class WallPlaneError(ValueError):
    """A wall composition that will not fit, naming what was in the way."""


# ---------------------------------------------------------------------------
# the art
# ---------------------------------------------------------------------------

_ART: dict[int, tuple[int, int, int, int]] | None = None


def art(reference: str = "reference/blood") -> dict:
    """tile -> (width, height, x offset, y offset), loaded once."""
    global _ART
    if _ART is None:
        _ART = {tile: (item.width, item.height,
                       item.animation["xofs"], item.animation["yofs"])
                for tile, item in read_art_directory(reference).items()}
    return _ART


def extents(tile: int, x_repeat: int, y_repeat: int, cstat: int):
    """(left, right, above, below) in map units, about the sprite's own point."""
    size = art().get(int(tile))
    if size is None:
        return None
    width, height, xofs, yofs = size
    if width <= 0 or height <= 0:
        return None
    centre = width // 2 + int(xofs)
    if int(cstat) & XFLIP:
        centre = width - centre
    left = (int(x_repeat) * centre) // 4
    right = (int(x_repeat) * (width - centre)) // 4
    above, below = sprite_extent(height, int(y_repeat), int(cstat),
                                 y_offset=int(yofs))
    return left, right, above, below


# ---------------------------------------------------------------------------
# the plane
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Rect:
    """A footprint on one plane: along the wall, and down the wall."""
    along0: float
    along1: float
    z0: int
    z1: int

    @property
    def area(self) -> float:
        return max(0.0, self.along1 - self.along0) * max(0, self.z1 - self.z0)

    def overlaps(self, other: "Rect") -> float:
        wide = min(self.along1, other.along1) - max(self.along0, other.along0)
        tall = min(self.z1, other.z1) - max(self.z0, other.z0)
        if wide <= 0 or tall <= 0:
            return 0.0
        return float(wide) * float(tall)


@dataclass
class Plane:
    """One vertical surface and everything already hanging on it."""
    key: tuple
    unit: tuple
    taken: list = field(default_factory=list)

    def free(self, rect: Rect) -> bool:
        if rect.area <= 0:
            return False
        for other in self.taken:
            shared = rect.overlaps(other)
            if shared and shared / min(rect.area, other.area) >= OVERLAP_FLOOR:
                return False
        return True

    def blocker(self, rect: Rect):
        for other in self.taken:
            if rect.overlaps(other):
                return other
        return None


def _unit_and_offset(a1, a2):
    dx, dy = float(a2[0] - a1[0]), float(a2[1] - a1[1])
    length = math.hypot(dx, dy)
    if length <= 0:
        raise WallPlaneError("a wall segment with no length carries nothing")
    ux, uy = dx / length, dy / length
    if (ux, uy) < (0.0, 0.0):
        ux, uy = -ux, -uy
    return (ux, uy), length


def _plane_key(point, unit) -> tuple:
    ux, uy = unit
    offset = -point[0] * uy + point[1] * ux
    return (round(ux, 3), round(uy, 3), round(offset / PLANE_TOLERANCE))


def anchor_point(a1, a2, t: float, offset_player_widths: float):
    """Where the compiler will put a wall sprite anchored like this.

    Copied from `placement.resolve_anchor`'s wall branch rather than
    guessed: an occupancy model that predicts a different point from the one
    the compiler uses is worse than none.
    """
    mx = a1[0] + (a2[0] - a1[0]) * t
    my = a1[1] + (a2[1] - a1[1]) * t
    nx, ny = inward_normal(a1[0], a1[1], a2[0], a2[1])
    push = offset_player_widths * PLAYER_WIDTH
    return (mx + nx * push, my + ny * push)


def anchor_z(region, height_player_heights: float, above: int, below: int) -> int:
    """The z the compiler will settle on, including its two clamps."""
    floor_z = int(region.floor_z)
    ceiling_z = int(region.ceiling_z)
    z = int(round(floor_z - height_player_heights * PLAYER_HEIGHT))
    z = max(ceiling_z + 256, min(floor_z - 256, z))
    if above + below <= abs(floor_z - ceiling_z):
        z = max(ceiling_z + above, min(floor_z - below, z))
    return z


def occupancy(layout) -> dict:
    """Every wall sprite already declared, as rectangles on their planes.

    Recomputed on each call.  The layout is the single source of truth for
    what has been placed, and a cache that disagreed with it would put a
    sprite through a sprite while reporting success.
    """
    planes: dict[tuple, Plane] = {}
    for placement in layout.placements:
        anchor = placement.anchor or {}
        if anchor.get("kind") != "wall":
            continue
        if int(placement.cstat) & ALIGN_MASK != ALIGN_WALL:
            continue
        size = extents(placement.picnum, placement.x_repeat,
                       placement.y_repeat, placement.cstat)
        if size is None:
            continue
        left, right, above, below = size
        a1, a2 = tuple(anchor["a1"]), tuple(anchor["a2"])
        try:
            unit, _length = _unit_and_offset(a1, a2)
        except WallPlaneError:
            continue
        point = anchor_point(a1, a2, float(anchor.get("t", 0.5)),
                             float(anchor.get("offset_player_widths") or 0.08))
        region = layout.regions.get(placement.region_id)
        if region is None:
            continue
        z = anchor_z(region, float(anchor.get("height_player_heights") or 0.0),
                     above, below)
        key = _plane_key(point, unit)
        plane = planes.setdefault(key, Plane(key, unit))
        along = point[0] * unit[0] + point[1] * unit[1]
        plane.taken.append(Rect(along - left, along + right,
                                z - above, z + below))
    return planes


# ---------------------------------------------------------------------------
# asking the wall for room
# ---------------------------------------------------------------------------

def portal_spans(layout, region_id: str, a1, a2) -> list:
    """The stretches of this wall an OPENING owns, in `along` coordinates.

    A wall sprite hung over a doorway has nothing behind it, and the
    compiler refuses it -- correctly.  The occupancy model knew about other
    sprites and not about portals, so a run sliding along a wall to find
    room could slide straight onto the annex mouth.  A connection's anchor
    lies on the wall line itself and the sprite plane is parallel to it, so
    the two project onto the same axis and can be compared directly.
    """
    unit, _length = _unit_and_offset(a1, a2)
    line_a = a1[0] * unit[0] + a1[1] * unit[1]
    line_b = a2[0] * unit[0] + a2[1] * unit[1]
    lo_line, hi_line = min(line_a, line_b), max(line_a, line_b)
    normal = (-unit[1], unit[0])
    offset = a1[0] * normal[0] + a1[1] * normal[1]
    out = []
    for connection in getattr(layout, "connections", {}).values():
        if region_id not in (connection.region_a, connection.region_b):
            continue
        if connection.a1 is None or connection.a2 is None:
            continue
        here = connection.a1[0] * normal[0] + connection.a1[1] * normal[1]
        there = connection.a2[0] * normal[0] + connection.a2[1] * normal[1]
        if abs(here - offset) > 2 or abs(there - offset) > 2:
            continue                     # a different wall of this room
        first = connection.a1[0] * unit[0] + connection.a1[1] * unit[1]
        second = connection.a2[0] * unit[0] + connection.a2[1] * unit[1]
        low, high = min(first, second), max(first, second)
        if high < lo_line or low > hi_line:
            continue
        out.append((low, high))
    return out


def find_slot(layout, region_id: str, a1, a2, *, width: float, above: int,
              below: int, t: float = 0.5, height_player_heights: float = 0.65,
              offset_player_widths: float = 0.10,
              slide: bool = True, stack: bool = True):
    """A free (t, height) for a rectangle this size, or None.

    Tries the asked-for spot, then slides along the wall keeping the height,
    then walks up and down.  Returns the pair to place at.
    """
    region = layout.regions.get(region_id)
    if region is None:
        return None
    unit, length = _unit_and_offset(a1, a2)
    if width > length:
        return None
    planes = occupancy(layout)
    blocked = portal_spans(layout, region_id, a1, a2)
    half = width / 2.0

    clear = abs(int(region.floor_z) - int(region.ceiling_z))
    if above + below > clear - 2 * ROOM_MARGIN:
        return None                 # the room is not tall enough to hold it

    def fits(candidate_t, candidate_h):
        point = anchor_point(a1, a2, candidate_t, offset_player_widths)
        plane = planes.get(_plane_key(point, unit))
        z = anchor_z(region, candidate_h, above, below)
        # A height the room clamps is not the height that was asked for, and
        # reserving one rectangle while the sprites land at another is how
        # four letters of a vertical word ended up stacked at one z against
        # the ceiling.  Only an honest height counts as a fit.
        raw = int(round(int(region.floor_z) - candidate_h * PLAYER_HEIGHT))
        if z != raw:
            return None
        along = point[0] * unit[0] + point[1] * unit[1]
        if any(along - half < high and low < along + half
               for low, high in blocked):
            return None                  # nothing behind it
        if plane is None:
            return z
        rect = Rect(along - half, along + half, z - above, z + below)
        return z if plane.free(rect) else None

    margin = half / length
    low, high = margin, 1.0 - margin
    if low > high:
        return None
    want_t = min(high, max(low, float(t)))
    if fits(want_t, height_player_heights) is not None:
        return (want_t, height_player_heights)

    heights = [height_player_heights]
    if stack:
        # Outward from the asked-for height, so a caption displaced by a
        # painting lands just under it rather than at the far end of the room.
        step = (STACK_HIGH - STACK_LOW) / STACK_STEPS
        for index in range(1, STACK_STEPS + 1):
            for sign in (-1, 1):
                value = height_player_heights + sign * index * step
                if STACK_LOW <= value <= STACK_HIGH:
                    heights.append(value)

    slots = [want_t]
    if slide:
        for index in range(1, SLIDE_STEPS + 1):
            for sign in (-1, 1):
                value = want_t + sign * index * (high - low) / SLIDE_STEPS
                if low <= value <= high:
                    slots.append(value)

    for candidate_h in heights:
        for candidate_t in slots:
            if fits(candidate_t, candidate_h) is not None:
                return (candidate_t, candidate_h)
    return None


def sprite(layout, placement_id: str, region_id: str, a1, a2, *, tile: int,
           x_repeat: int, y_repeat: int, cstat: int, t: float = 0.5,
           height_player_heights: float = 0.65,
           offset_player_widths: float = 0.10, required: bool = False,
           **fields):
    """Hang one wall sprite where it does not cover anything already there.

    Returns the placement id, or None if the wall had no room -- which is a
    legitimate answer for decoration.  `required=True` raises instead, for
    the things that must appear (a key placard, a lever).
    """
    size = extents(tile, x_repeat, y_repeat, cstat)
    if size is None:
        raise WallPlaneError(f"{placement_id}: tile {tile} is not in the ART")
    left, right, above, below = size
    slot = find_slot(layout, region_id, a1, a2, width=left + right,
                     above=above, below=below, t=t,
                     height_player_heights=height_player_heights,
                     offset_player_widths=offset_player_widths)
    if slot is None:
        if required:
            raise WallPlaneError(
                f"{placement_id}: no free {left + right} x {above + below} "
                f"rectangle on this wall for tile {tile}")
        return None
    got_t, got_h = slot
    return layout.place_on_wall(
        placement_id, region_id, a1=a1, a2=a2, t=got_t,
        height_player_heights=got_h,
        offset_player_widths=offset_player_widths,
        type=0, picnum=int(tile), cstat=int(cstat),
        x_repeat=int(x_repeat), y_repeat=int(y_repeat), **fields)


# ---------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------

class Cycle(tuple):
    """A per-letter sequence that repeats: ``Cycle(("sign", "rust"))``.

    A plain sequence **pads with its last value**, because that is what a
    drop capital is -- ``size=(112, 72)`` means one big letter and the rest
    small.  Cycling was the first rule here and it turned THE ALDERMACK into
    a 112/72/72/112/72/72 sawtooth.  Alternation is the rarer intent, so it
    is the one that has to say so.
    """


def cycle(values) -> Cycle:
    return Cycle(values)


class PerWord(tuple):
    """A palette per WORD rather than per letter: ``PerWord((4, 0, 11))``.

    The other thing the campaign does with colour, and the one that reads as
    meaning rather than as decoration: DWE2M2 paints ACTIVE, REMOVED and
    OPEN in three palettes with each word uniform, and LAUNCH LAUNCH in two.
    Two of the corpus's nine mixed signs are this form.
    """


def per_word(values) -> PerWord:
    return PerWord(values)


def _roll(seed: str, n: int) -> int:
    """A stable index, the same contract as `runs` and `fixtures`."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % max(1, n)


def _word_index(words: str) -> list:
    """Which whitespace-separated word each character belongs to."""
    out, index, started = [], 0, False
    for character in words:
        if character.isspace():
            if started:
                index += 1
                started = False
            out.append(index)
            continue
        started = True
        out.append(index)
    return out


def _per_letter(value, index, default, words: str | None = None):
    if value is None:
        return default
    if isinstance(value, PerWord):
        if words is None:
            return value[0]
        return value[_word_index(words)[index] % len(value)]
    if isinstance(value, Cycle):
        return value[index % len(value)]
    if isinstance(value, (list, tuple)):
        return value[min(index, len(value) - 1)]
    return value


def _palette(value) -> int:
    if isinstance(value, str):
        if value not in PALETTES:
            raise WallPlaneError(
                f"no palette named {value!r}; known: {', '.join(sorted(PALETTES))}")
        return PALETTES[value]
    return int(value)


def letter_size(size: int) -> tuple[float, int]:
    """One letter's drawn (width, height) at this repeat."""
    return (size * LETTER_WIDTH / 4.0, (int(size) << 2) * LETTER_HEIGHT)


def _advances(words: str, size, *, vertical: bool, tracking: float | None = None):
    """Per-letter (drawn size, advance to the next letter).

    Pitch is centre to centre, so a word's own extent is the advances of all
    but the last letter plus the last letter's drawn size -- not the sum of
    every advance, which over-reserves by nearly half a letter and is what
    made ST GALLOW'S crypt sign report "no room" on a wall it fitted.
    """
    pitch = (VERTICAL_PITCH if vertical else PITCH) if tracking is None \
        else float(tracking)
    out = []
    for index in range(len(words)):
        width, height = letter_size(_per_letter(size, index, 64))
        drawn = height if vertical else width
        out.append((drawn, drawn * pitch))
    return out


def text_box(words: str, size, *, vertical: bool = False,
             tracking: float | None = None, jitter: float = 0.0):
    """(along, above, below) for a word, from the letter tiles themselves.

    A letter is not centred on its own z: the alphabet carries an ART y
    offset, so `sprite_extent` puts more of it below the anchor than above.
    Reserving a symmetric box around the centre therefore under-reserves the
    bottom by that offset, which is exactly the 144 units by which the
    arcade's sign and its caption came to touch.
    """
    above = below = 0
    for index, character in enumerate(words):
        tile = tile_for(character)
        if tile is None:
            continue
        this = _per_letter(size, index, 64)
        got = extents(tile, this, this, LETTER_CSTAT)
        if got is None:
            continue
        above = max(above, got[2])
        below = max(below, got[3])
    run, across = text_extent(words, size, vertical=vertical,
                              tracking=tracking)
    if jitter:
        # A jittered sign occupies the band its letters wander over, not the
        # band one letter occupies.
        swing = int(round(jitter * max(1, across if vertical else across)))
        above += swing // 2
        below += swing - swing // 2
    if not vertical:
        return float(run), above, below
    # A vertical stack's extent ALREADY runs from the top of the first letter
    # to the bottom of the last, so adding a whole letter's above and below
    # to it reserves one letter too many -- which is what refused a five
    # letter word on a wall with room for it.  Only the ART offset's
    # asymmetry is left to add.
    first, last = _end_letters(words, size)
    top = across // 2 + (first[0] - first[2] // 2 if first else 0)
    bottom = across - across // 2 + (last[1] - last[2] // 2 if last else 0)
    return float(run), max(0, top), max(0, bottom)


def _end_letters(words: str, size):
    """(above, below, drawn) for the first and last real letters of a word."""
    found = []
    for index, character in enumerate(words):
        tile = tile_for(character)
        if tile is None:
            continue
        this = _per_letter(size, index, 64)
        got = extents(tile, this, this, LETTER_CSTAT)
        if got is not None:
            found.append((got[2], got[3], got[2] + got[3]))
    if not found:
        return None, None
    return found[0], found[-1]


def text_extent(words: str, size, *, vertical: bool = False,
                tracking: float | None = None) -> tuple[float, int]:
    """The (along, down) box a word occupies, before it is placed."""
    steps = _advances(words, size, vertical=vertical, tracking=tracking)
    if not steps:
        return (0.0, 0)
    run = sum(advance for _drawn, advance in steps[:-1]) + steps[-1][0]
    across = max(letter_size(_per_letter(size, index, 64))[0 if vertical else 1]
                 for index in range(len(words)))
    if vertical:
        return float(across), int(run)
    return float(run), int(across)


def text(layout, sign_id: str, region_id: str, a1, a2, *, words: str,
         style=None, size=64, palette="default", shade=LETTER_SHADE,
         t: float = 0.5, height_player_heights: float = 1.2,
         offset_player_widths: float = 0.12, vertical: bool = False,
         required: bool = False):
    """Write a word on a wall, in the space the wall actually has free.

    `size`, `palette` and `shade` each take a scalar or a sequence: a
    sequence is applied letter by letter and repeats, so
    ``palette=("default", "green")`` alternates and ``size=(96, 64, 64)``
    sets a large initial.

    `vertical=True` stacks the letters downward at one point along the wall,
    at the campaign's measured 1.25 drawn heights of pitch.

    Unlike `lettering.write_on_wall`, which centres blindly at `t` and at a
    given height, this reserves the whole word as one rectangle and moves it
    -- along the wall, then up or down -- until it covers nothing.  A word
    that will not fit anywhere returns None rather than being written over
    something.
    """
    if not words.strip():
        raise WallPlaneError(f"{sign_id}: nothing to write")
    _u, span = _unit_and_offset(a1, a2)

    # A style walks its OWN size ladder against the real wall, not against
    # the wall's length alone.  Length is only one of the two constraints:
    # a column is limited by the room's height and by what is already
    # hanging there, and neither is visible to `TextStyle.fit`.  Trying the
    # ladder here is what lets LOANS step from 136 down to a size the pawn
    # shop's 1.45 player heights of clear wall will take.
    tracking, jitter = None, 0.0
    if style is not None:
        chosen = STYLE_TABLE(style)
        attempts = [chosen.at(step) for step in chosen.steps()]
    else:
        attempts = [None]

    slot = tried = None
    for trial in attempts:
        if trial is not None:
            size, palette = trial.sizes(), trial.palettes()
            shade, vertical = trial.shade, trial.vertical
            tracking, jitter = trial.tracking, trial.jitter
        wide, tall = text_extent(words, size, vertical=vertical,
                                 tracking=tracking)
        if not vertical and wide > span:
            continue
        _run, above, below = text_box(words, size, vertical=vertical,
                                      tracking=tracking, jitter=jitter)
        slot = find_slot(layout, region_id, a1, a2, width=wide,
                         above=above, below=below, t=t,
                         height_player_heights=height_player_heights,
                         offset_player_widths=offset_player_widths)
        tried = trial
        if slot is not None:
            break
    if slot is None:
        if required:
            raise WallPlaneError(
                f"{sign_id}: no free rectangle on {span:.0f} units of wall "
                f"for {words!r}"
                + (f" at any step of the {chosen.name} style {chosen.steps()}"
                   if style is not None else ""))
        return None
    if tried is not None:
        size, palette = tried.sizes(), tried.palettes()
        shade, vertical = tried.shade, tried.vertical
        tracking, jitter = tried.tracking, tried.jitter
        wide, tall = text_extent(words, size, vertical=vertical,
                                 tracking=tracking)
    got_t, got_h = slot

    _unit, length = _unit_and_offset(a1, a2)
    out = []
    steps = _advances(words, size, vertical=vertical, tracking=tracking)
    if vertical:
        # Top of the word, then down: the first letter is highest, which is
        # how every campaign stack reads.  The cursor tracks each letter's
        # own centre, so mixed sizes stay on one column.
        cursor = got_h + (tall / 2.0) / PLAYER_HEIGHT
        for index, character in enumerate(words):
            this_size = _per_letter(size, index, 64)
            drawn, advance = steps[index]
            cursor -= (drawn / 2.0) / PLAYER_HEIGHT
            picnum = tile_for(character)
            if picnum is None:
                continue
            placement_id = f"{sign_id}_{index:02d}"
            layout.place_on_wall(
                placement_id, region_id, a1=a1, a2=a2, t=got_t,
                height_player_heights=cursor,
                offset_player_widths=offset_player_widths,
                type=0, picnum=picnum, cstat=LETTER_CSTAT,
                shade=int(_per_letter(shade, index, LETTER_SHADE, words)),
                pal=_palette(_per_letter(palette, index, "default", words)),
                x_repeat=int(this_size), y_repeat=int(this_size))
            out.append(placement_id)
            cursor -= (advance - drawn / 2.0) / PLAYER_HEIGHT
        return out

    cursor = -wide / 2.0
    for index, character in enumerate(words):
        this_size = _per_letter(size, index, 64)
        drawn, advance = steps[index]
        centre = cursor + drawn / 2.0
        cursor += advance
        picnum = tile_for(character)
        if picnum is None:
            continue
        placement_id = f"{sign_id}_{index:02d}"
        # Jitter is deterministic in the sign's own identity, like every
        # other choice in this project: the same sign rebuilds identically
        # and two signs wander differently.
        wobble = 0.0
        if jitter:
            _w, letter_h = letter_size(this_size)
            swing = jitter * letter_h
            wobble = (_roll(f"{sign_id}:jitter:{index}", 201) - 100) / 100.0
            wobble = wobble * swing / 2.0 / PLAYER_HEIGHT
        layout.place_on_wall(
            placement_id, region_id, a1=a1, a2=a2,
            t=got_t + centre / length,
            height_player_heights=got_h + wobble,
            offset_player_widths=offset_player_widths,
            type=0, picnum=picnum, cstat=LETTER_CSTAT,
            shade=int(_per_letter(shade, index, LETTER_SHADE, words)),
            pal=_palette(_per_letter(palette, index, "default", words)),
            x_repeat=int(this_size), y_repeat=int(this_size))
        out.append(placement_id)
    return out


# ---------------------------------------------------------------------------
# text styles: the same parametric prefab shape as a fixture family
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TextStyle:
    """A look that is pinned, and words that are free.

    Exactly `fixtures.Family`, one layer up: a family pins a fixture's rise,
    tile and depth and varies its length; a style pins a word's size,
    palette and shade and varies the word.  Both carry their provenance, and
    both clamp rather than fail when what they are handed is out of range.

    `ladder` is the one interpreted part.  A style's own size is measured;
    the sizes it may step down through when a wall is short are
    `lettering.SIZES` below it -- the campaign's own size ladder -- on the
    reasoning that keeping a look and losing a size is better than losing
    the sign.  Say `ladder=()` to refuse instead.
    """
    name: str
    size: int
    palette: object = "default"
    shade: int = 0
    vertical: bool = False
    #: (size, palette) for the first letter: a drop capital, a coloured
    #: initial, or both.  `None` writes the word uniformly.
    initial: tuple | None = None
    source: str = ""
    ladder: tuple = ()
    #: Centre-to-centre letter spacing in drawn widths.  `None` takes
    #: `lettering.PITCH` (1.45).  The corpus's uniform signs sit at a median
    #: 1.333 and its mixed ones at 1.004, and E1M4 tracks ROTTEN CANDY at
    #: 2.0 -- wide tracking is part of what makes a carnival sign one.
    tracking: float | None = None
    #: How far a letter may wander in z from the line, in drawn heights,
    #: chosen deterministically per letter.  0 for every ordinary sign: the
    #: corpus's uniform signs have a q3 of exactly 0.0.  E1M4's ROTTEN CANDY
    #: spreads 0.73 across its eleven letters.
    jitter: float = 0.0

    def steps(self) -> tuple:
        """The sizes this style will accept, its own first.

        `lettering.SIZES` is the campaign's ladder and does not contain
        every size the campaign writes at -- `label` is 32 and `fascia` is
        120, neither of which is in it -- so a style's own measured size
        leads, and the ladder is what it may fall back to.
        """
        if self.ladder:
            return tuple(sorted(set(self.ladder), reverse=True))
        below = [size for size in SIZES if size < self.size]
        return tuple(sorted({self.size, *below}, reverse=True))

    def at(self, size: int) -> "TextStyle":
        return TextStyle(self.name, int(size), self.palette, self.shade,
                         self.vertical, self.initial, self.source, self.ladder,
                         self.tracking, self.jitter)

    def sizes(self):
        """The per-letter size sequence, with the initial applied."""
        if self.initial is None:
            return self.size
        head = self.initial[0]
        # A multiplier under 8 scales the style's size; anything larger is a
        # size.  255 is the largest repeat Build stores in a byte.
        scaled = int(round(self.size * head)) if head < 8 else int(head)
        return (max(1, min(255, scaled)), self.size)

    def palettes(self):
        if self.initial is None or len(self.initial) < 2:
            return self.palette
        return (self.initial[1], self.palette)

    def cost(self, words: str) -> dict:
        """Declared before anything is written, like a fixture run's."""
        return {"style": self.name,
                "sprites": sum(1 for c in words if tile_for(c) is not None),
                "source": self.source}

    def fit(self, words: str, span: float) -> "TextStyle | None":
        """The largest step of this style that fits in `span` units of wall.

        A vertical style is not limited by the wall's length, so it fits at
        its own size or not at all -- the room's height decides, and
        `find_slot` is what knows that.
        """
        if self.vertical:
            return self
        for size in self.steps():
            trial = self.at(size)
            wide, _tall = text_extent(words, trial.sizes(),
                                      vertical=trial.vertical,
                                      tracking=trial.tracking)
            if wide <= span:
                return trial
        return None


#: **The campaign's own text styles**, from `tools/mine_wall_sprites.py
#: --corpus` over 393 words in the corpus.  Derived: every size, palette,
#: shade and count.  Interpreted: the names, and the ladders.
#:
#: Grouping needed two fixes before these numbers meant anything.  Letters
#: above each other are two different things -- a word written downward, and
#: the second line of an ordinary sign -- and counting them together said
#: there were 132 columns when there are 11.  And a long sign crosses
#: whatever sector boundaries its wall crosses, so keying on the sector (as
#: `lettering.read_sign` does) returns LIQUO, LOERS and WTID where DWE3M10
#: has words.
STYLES = {
    "plain": TextStyle(
        "plain", 64, "default", 0,
        source="84 words, the corpus's commonest look: MEN, WOMEN"),
    "notice": TextStyle(
        "notice", 64, "default", -8,
        source="12 words: LOADING, TRANSITION"),
    "label": TextStyle(
        "label", 32, "default", -8,
        source="8 words, the small one: BOAT, HOTEL, CONTROL, GATE"),
    "fascia": TextStyle(
        "fascia", 120, "sign", 0,
        source="10 words at 120/pal 4: WELCOME"),
    "announce": TextStyle(
        "announce", 120, 10, 0,
        source="8 words at 120/pal 10: PLEASE PROCEED"),
    "banner": TextStyle(
        "banner", 184, "rust", -50,
        source="32 words, Death Wish's big lettering"),
    "department": TextStyle(
        "department", 48, "cold", -128,
        source="6 words at 48/pal 11 lit: MEDLAB, ARSENAL, OPERATIONS"),
    "works": TextStyle(
        "works", 80, "cold", -128,
        source="7 words at 80/pal 11 lit: POWER PLANT"),
    "breach": TextStyle(
        "breach", 56, "cold", -70,
        source="6 words at 56/pal 11: WALL BREACH, CONTROL ROOM"),
    # **The mixed forms.**  Only 9 of the corpus's 160 signs mix palettes at
    # all -- 5.6% -- and they are concentrated where the identity carries
    # them: E1M4 (Dark Carnival), DWE1M9 (SPOOKY WORLD), DWE3M4 and DWE3M10
    # (ICE), DWE2M2, TEDE1M4.  A church does not get one.
    "carnival": TextStyle(
        "carnival", 64, cycle((4, 11, 0, 13)), -8, tracking=2.0, jitter=0.73,
        source=("E1M4 ROTTEN CANDY: 11 letters, palettes 4/11/0/13, tracked "
                "2.0 drawn widths and jittered 0.73 heights")),
    "fortune": TextStyle(
        "fortune", 64, cycle((4, 3, 12, 11)), -8, tracking=1.5,
        source=("E1M4 FORTUNES: the corpus's ONE regular cycle, period 4 "
                "over 8 letters")),
    "spooky": TextStyle(
        "spooky", 64, (4, 8, 5, 2, 11, 4), -8, tracking=1.0,
        source="DWE1M9 SPOOKY and WORLD: irregular, five palettes, no cycle"),
    # The two vertical looks, from all 11 columns in the corpus.
    "column": TextStyle(
        "column", 255, 2, 0, vertical=True, ladder=(255, 184, 136),
        source="ABALCO, CABALO, HOTEL -- hanging shop signs at repeat 255"),
    "column_small": TextStyle(
        "column_small", 136, "sign", -30, vertical=True, ladder=(136, 96, 64),
        source="FRIES in DWE3M4 and DWE3M10, twice each"),
}


def STYLE_TABLE(name_or_style) -> TextStyle:
    """A `TextStyle`, from one or from the name of one."""
    if isinstance(name_or_style, TextStyle):
        return name_or_style
    if name_or_style not in STYLES:
        raise WallPlaneError(
            f"no text style named {name_or_style!r}; known: "
            f"{', '.join(sorted(STYLES))}")
    return STYLES[name_or_style]


def style(name_or_style, **overrides) -> TextStyle:
    """A named style, optionally varied.

    ``style("banner", initial=(1.6, "warning"))`` is the banner look with a
    drop capital half again as big in a different colour -- the parametric
    part.  A style is frozen, so this returns a new one.
    """
    base = STYLE_TABLE(name_or_style)
    if not overrides:
        return base
    fields = {"name": base.name, "size": base.size, "palette": base.palette,
              "shade": base.shade, "vertical": base.vertical,
              "initial": base.initial, "source": base.source,
              "ladder": base.ladder, "tracking": base.tracking,
              "jitter": base.jitter}
    fields.update(overrides)
    return TextStyle(**fields)


# ---------------------------------------------------------------------------
# compositions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Block:
    """One row of a composition: a sprite, or a line of text.

    `kind` is "sprite" or "text".  A composition stacks its blocks downward
    in the order given, centred on one point along the wall, and reserves
    them one at a time -- so the whole group lands together or not at all.
    """
    kind: str
    tile: int | None = None
    words: str = ""
    size: object = 64
    palette: object = "default"
    shade: object = None
    x_repeat: int = 64
    y_repeat: int = 64
    cstat: int = 16
    gap: float = LINE_GAP      # player heights left under this block
    vertical: bool = False
    #: A named `TextStyle`, carried through so `text` can walk its own size
    #: ladder against the real wall.  Resolving it here instead -- which the
    #: first version did -- throws the ladder away and a caption that needed
    #: one step down is simply dropped.
    style: object = None


def painting(tile: int, *, x_repeat: int = 64, y_repeat: int = 64,
             cstat: int = 16, shade: int = -8, gap: float = 0.10) -> Block:
    return Block("sprite", tile=tile, x_repeat=x_repeat, y_repeat=y_repeat,
                 cstat=cstat, shade=shade, gap=gap)


def caption(words: str, *, style=None, size=48, palette="default",
            shade=LETTER_SHADE, gap: float = LINE_GAP,
            vertical: bool = False) -> Block:
    """One line of a composition.  `style` supersedes the loose parameters."""
    if style is not None:
        chosen = STYLE_TABLE(style)
        size, palette = chosen.sizes(), chosen.palettes()
        shade, vertical = chosen.shade, chosen.vertical
    return Block("text", words=words, size=size, palette=palette,
                 shade=shade, gap=gap, vertical=vertical, style=style)


def composition(layout, group_id: str, region_id: str, a1, a2, *,
                blocks, t: float = 0.5, top_player_heights: float = 1.9,
                offset_player_widths: float = 0.11) -> dict:
    """A painting with a description under it, and anything of that shape.

    Blocks are laid out downward from `top_player_heights`, each centred on
    the same point along the wall.  Every block is placed through the same
    occupancy as everything else, so a composition cannot cover the sign
    next to it and the next thing hung cannot cover the composition.
    """
    report = {"group": group_id, "placed": [], "skipped": []}
    cursor = float(top_player_heights)
    for index, block in enumerate(blocks):
        if block.kind == "sprite":
            size = extents(block.tile, block.x_repeat, block.y_repeat,
                           block.cstat)
            if size is None:
                report["skipped"].append(f"{index}: tile {block.tile} not in ART")
                continue
            _l, _r, above, below = size
            centre = cursor - (above / PLAYER_HEIGHT)
            got = sprite(layout, f"{group_id}_{index}", region_id, a1, a2,
                         tile=block.tile, x_repeat=block.x_repeat,
                         y_repeat=block.y_repeat, cstat=block.cstat,
                         t=t, height_player_heights=centre,
                         offset_player_widths=offset_player_widths,
                         shade=block.shade if block.shade is not None else -8)
            if got is None:
                report["skipped"].append(f"{index}: tile {block.tile} did not fit")
                continue
            report["placed"].append(got)
            cursor = centre - (below / PLAYER_HEIGHT) - block.gap
        else:
            _wide, above, below = text_box(block.words, block.size,
                                           vertical=block.vertical)
            centre = cursor - above / PLAYER_HEIGHT
            got = text(layout, f"{group_id}_{index}", region_id, a1, a2,
                       words=block.words, style=block.style,
                       size=block.size, palette=block.palette,
                       shade=block.shade if block.shade is not None
                       else LETTER_SHADE,
                       t=t, height_player_heights=centre,
                       offset_player_widths=offset_player_widths,
                       vertical=block.vertical)
            if not got:
                report["skipped"].append(f"{index}: {block.words!r} did not fit")
                continue
            report["placed"].extend(got)
            cursor = centre - below / PLAYER_HEIGHT - block.gap
    return report
