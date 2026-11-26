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
up and down it runs by `bloodmap.placement.drawn_extent`.  Both come from
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

from .art import read_art_directory
from .lettering import (
    LETTER_CSTAT, LETTER_HEIGHT, LETTER_SHADE, LETTER_WIDTH, PALETTES, PITCH,
    SIZES, tile_for,
)
from .placement import (
    PLAYER_HEIGHT, drawn_extent, resolve_anchor,
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
    top, bottom = drawn_extent(height, yofs, y_repeat, cstat)
    return left, right, -top, bottom


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


def _wall_anchor(region, a1, a2, t, height, offset, *, extent=None):
    return resolve_anchor(
        kind="wall", a1=a1, a2=a2, t=t, height_player_heights=height,
        offset_player_widths=offset, floor_z=region.floor_z,
        ceiling_z=region.ceiling_z, surface_at=region.surface_z, wall_extent=extent,
    )


def _anchor_rect(layout, placement, a1, a2, size, unit):
    left, right, above, below = size
    anchor = placement.anchor
    region = layout.regions[placement.region_id]
    got = _wall_anchor(region, a1, a2, anchor["t"], anchor["height_player_heights"],
                       anchor["offset_player_widths"], extent=(above, below))
    point = got["x"], got["y"]
    along = point[0] * unit[0] + point[1] * unit[1]
    # The sprite's horizontal axis is opposite the wall's directed edge.
    if _forward(a1, a2, unit) == (anchor.get("facing") != "outward"):
        left, right = right, left
    return point, Rect(along - left, along + right, got["z"] - above, got["z"] + below)


def _forward(a1, a2, unit):
    return (a2[0] - a1[0]) * unit[0] + (a2[1] - a1[1]) * unit[1] > 0


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
        region = layout.regions.get(placement.region_id)
        if region is None:
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
        point, rect = _anchor_rect(layout, placement, a1, a2, size, unit)
        key = _plane_key(point, unit)
        # In its own bucket AND the two beside it. A key is a rounded
        # offset, so two sprites 8 units apart in depth -- a letter at 0.12
        # of a player width off the wall, a painting at 0.10 -- could fall
        # either side of a bucket edge and never be compared. Six signs were
        # written through pictures that way (`tools/sprite_fit.py` overlap;
        # the owner saw it first, 2026-11-18).
        for near in (-1, 0, 1):
            beside = (key[0], key[1], key[2] + near)
            planes.setdefault(beside, Plane(beside, unit)).taken.append(rect)
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
        # ... and only between the other side's ceiling and floor. A shelf
        # let into a wall is a portal a body high; the wall over its head is
        # solid, and a sign belongs there (experiments/fixtures).
        other = layout.regions.get(connection.region_b
                                   if connection.region_a == region_id
                                   else connection.region_a)
        if other is None or int(other.ceiling_z) >= int(other.floor_z):
            #: a door is a sector of no height until it opens: all of it
            out.append((low, high, None, None))
        else:
            out.append((low, high, int(other.ceiling_z), int(other.floor_z)))
    return out


def edge_spans(layout, region_id: str, a1, a2) -> list:
    """The stretches of the line a1-a2 that ARE an edge of this region.

    The owner, 2026-11-19, in the game: "there are places with posters
    which are hanging mid air." A notice was hung at 0.6 of a line along a
    street's side; the street's outline has a yard let into it there, and
    for 3,072 units the line is not a wall. Nothing asked. (This is for
    things HUNG ON walls, which is what this module places. A wall-aligned
    sprite that stands free -- a railing, a gate, a cobweb, a flag -- is
    not wrong for having air behind it, and does not come through here.)
    """
    if layout.regions.get(region_id) is None:
        return []
    unit, _length = _unit_and_offset(a1, a2)
    normal = (-unit[1], unit[0])
    offset = a1[0] * normal[0] + a1[1] * normal[1]
    spans = []
    #: ANY room's edge on this line counts: a wall is a wall whichever
    #: side's outline draws it (the church's apse lights hang on a line
    #: that is the neighbouring room's edge, and were refused when only
    #: the named room's own outline was asked)
    loops = [loop for region in layout.regions.values()
             for loop in (tuple(region.outer),) + tuple(region.holes)]
    for loop in loops:
        for index, p in enumerate(loop):
            q = loop[(index + 1) % len(loop)]
            if (abs(p[0] * normal[0] + p[1] * normal[1] - offset) > 2
                    or abs(q[0] * normal[0] + q[1] * normal[1] - offset) > 2):
                continue
            first = p[0] * unit[0] + p[1] * unit[1]
            second = q[0] * unit[0] + q[1] * unit[1]
            spans.append((min(first, second), max(first, second)))
    spans.sort()
    merged = []
    for low, high in spans:
        if merged and low <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return merged


def find_slot(layout, region_id: str, a1, a2, *, width: float, above: int,
              below: int, t: float = 0.5, height_player_heights: float = 0.65,
              offset_player_widths: float = 0.10,
              slide: bool = True, stack: bool = True,
              over_steps: bool = False, bounds=None, top_z_min=None):
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
    # A portal is only an OPENING where it is open at the sprite's height.
    # The wall around a raised island is a portal on every face and solid
    # from the outside up to the island's floor -- it is a step, and it is
    # exactly the surface a monument carries its name on.  The span table
    # carries no z, so the caller says which case this is.
    blocked = [] if over_steps else portal_spans(layout, region_id, a1, a2)
    walls = edge_spans(layout, region_id, a1, a2)
    before, after = bounds if bounds is not None else (width / 2.0, width / 2.0)
    left, right = (before, after) if _forward(a1, a2, unit) else (after, before)

    def fits(candidate_t, candidate_h):
        got = _wall_anchor(region, a1, a2, candidate_t, candidate_h,
                           offset_player_widths, extent=(above, below))
        point, z = (got["x"], got["y"]), got["z"]
        _, floor = region.surface_z(point)
        if z != round(floor - candidate_h * PLAYER_HEIGHT):
            return False  # the compiler would move the anchor
        along = point[0] * unit[0] + point[1] * unit[1]
        rect = Rect(along - left, along + right, z - above, z + below)
        if top_z_min is not None and rect.z0 < top_z_min:
            return False
        for side in (-left, right):
            ceiling, floor = region.surface_z(
                (point[0] + side * unit[0], point[1] + side * unit[1]))
            if rect.z0 < ceiling or rect.z1 > floor:
                return False

        # Some fitted lamps intentionally project across a corner.
        if walls:
            on_wall = sum(max(0.0, min(rect.along1, high) - max(rect.along0, low))
                          for low, high in walls)
            if on_wall < 0.6 * width:
                return False
        if any(rect.along0 < high and low < rect.along1
               and (top is None or (rect.z0 < bottom and top < rect.z1))
               for low, high, top, bottom in blocked):
            return False
        plane = planes.get(_plane_key(point, unit))
        return plane is None or plane.free(rect)

    low, high = before / length, 1.0 - after / length
    if low > high:
        return None
    want_t = min(high, max(low, float(t)))
    if fits(want_t, height_player_heights):
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
            if fits(candidate_t, candidate_h):
                return (candidate_t, candidate_h)
    return None


def sprite(layout, placement_id: str, region_id: str, a1, a2, *, tile: int,
           x_repeat: int, y_repeat: int, cstat: int, t: float = 0.5,
           height_player_heights: float = 0.65,
           offset_player_widths: float = 0.10, required: bool = False,
           over_steps: bool = False, top_z_min=None, **fields):
    """Hang one wall sprite where it does not cover anything already there.

    Returns the placement id, or None if the wall had no room -- which is a
    legitimate answer for decoration.  `required=True` raises instead, for
    the things that must appear (a key placard, a lever). `over_steps` hangs
    it on the face of a step (a raised block seen from below it), as
    `text` does: the memorial's emblem on its backdrop.
    """
    size = extents(tile, x_repeat, y_repeat, cstat)
    if size is None:
        raise WallPlaneError(f"{placement_id}: tile {tile} is not in the ART")
    left, right, above, below = size
    slot = find_slot(layout, region_id, a1, a2, width=left + right,
                     above=above, below=below, t=t,
                     height_player_heights=height_player_heights,
                     offset_player_widths=offset_player_widths,
                     over_steps=over_steps, bounds=(right, left),
                     top_z_min=top_z_min)
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


def _letters(words, size, *, vertical=False, tracking=None, jitter=0.0, sign_id=""):
    """Glyph anchors and their drawn boxes, relative to the word's anchor."""
    steps = _advances(words, size, vertical=vertical, tracking=tracking)
    if not steps:
        return []
    run = sum(advance for _, advance in steps[:-1]) + steps[-1][0]
    cursor = -run / 2
    letters = []
    for index, (character, (drawn, advance)) in enumerate(zip(words, steps)):
        centre = cursor + drawn / 2
        cursor += advance
        tile = tile_for(character)
        if tile is None:
            continue
        repeat = int(_per_letter(size, index, 64))
        box = extents(tile, repeat, repeat, LETTER_CSTAT)
        if box is None:
            continue
        along, dz = (0.0, centre) if vertical else (centre, 0.0)
        if jitter and not vertical:
            _, height = letter_size(repeat)
            dz -= (_roll(f"{sign_id}:jitter:{index}", 201) - 100) * jitter * height / 200
        letters.append((index, tile, repeat, along, round(dz), box))
    return letters


def _letter_bounds(letters):
    # The word advances along the directed segment. The glyph's horizontal
    # axis points back along that segment, so right extends toward its start.
    return (
        max(-along + box[1] for _, _, _, along, _, box in letters),
        max(along + box[0] for _, _, _, along, _, box in letters),
        max(box[2] - z for _, _, _, _, z, box in letters),
        max(z + box[3] for _, _, _, _, z, box in letters),
    )


def text_box(words: str, size, *, vertical: bool = False,
             tracking: float | None = None, jitter: float = 0.0, sign_id=""):
    """The width and vertical offsets of the renderer's envelope of the glyphs."""
    letters = _letters(words, size, vertical=vertical, tracking=tracking,
                       jitter=jitter, sign_id=sign_id)
    if not letters:
        return 0.0, 0, 0
    left, right, above, below = _letter_bounds(letters)
    return left + right, above, below


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
         required: bool = False, over_steps: bool = False, top_z=None,
         top_z_min=None):
    """Write a word on a wall, in the space the wall actually has free.

    `size`, `palette` and `shade` each take a scalar or a sequence: a
    sequence is applied letter by letter and repeats, so
    ``palette=("default", "green")`` alternates and ``size=(96, 64, 64)``
    sets a large initial.

    `vertical=True` stacks the letters downward at one point along the wall,
    at the campaign's measured 1.095 drawn heights of pitch (`VERTICAL_PITCH`).

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

    region = layout.regions.get(region_id)
    if region is None:
        return None
    slot = None
    for trial in attempts:
        if trial is not None:
            size, palette = trial.sizes(), trial.palettes()
            shade, vertical = trial.shade, trial.vertical
            tracking, jitter = trial.tracking, trial.jitter
        letters = _letters(words, size, vertical=vertical, tracking=tracking,
                           jitter=jitter, sign_id=sign_id)
        if not letters:
            continue
        left, right, above, below = _letter_bounds(letters)
        height = height_player_heights
        if top_z is not None:
            origin = _wall_anchor(region, a1, a2, t, 0, offset_player_widths)
            _, floor = region.surface_z((origin["x"], origin["y"]))
            height = (floor - top_z - above) / PLAYER_HEIGHT
        slot = find_slot(layout, region_id, a1, a2, width=left + right,
                         above=above, below=below, t=t,
                         height_player_heights=height,
                         offset_player_widths=offset_player_widths,
                         over_steps=over_steps, bounds=(left, right),
                         top_z_min=top_z_min)
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
    got_t, got_h = slot
    centre = _wall_anchor(region, a1, a2, got_t, got_h, offset_player_widths)
    _, floor = region.surface_z((centre["x"], centre["y"]))
    z = round(floor - got_h * PLAYER_HEIGHT)
    out = []
    for index, picnum, repeat, along, dz, _box in letters:
        glyph_t = got_t + along / span
        point = _wall_anchor(region, a1, a2, glyph_t, 0, offset_player_widths)
        _, glyph_floor = region.surface_z((point["x"], point["y"]))
        placement_id = f"{sign_id}_{index:02d}"
        layout.place_on_wall(
            placement_id, region_id, a1=a1, a2=a2, t=glyph_t,
            height_player_heights=(glyph_floor - z - dz) / PLAYER_HEIGHT,
            offset_player_widths=offset_player_widths,
            type=0, picnum=picnum, cstat=LETTER_CSTAT,
            shade=int(_per_letter(shade, index, LETTER_SHADE, words)),
            pal=_palette(_per_letter(palette, index, "default", words)),
            x_repeat=repeat, y_repeat=repeat)
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
    #: `lettering.PITCH` (1.45, near the LINE pitch 1.455 rather than the
    #: letter spacing; kept because changing it moves every sign in
    #: Gravesend).  The corpus's uniform signs sit at a median
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
    "ratdogs": TextStyle(
        "ratdogs", 72, "rust", 48,
        source=("E1M4 RATDOGS over its grill hatch: 7 letters at 72, palette "
                "12, shade 48, pitched 1.44 drawn widths, no jitter")),
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
    region = layout.regions[region_id]
    unit, _ = _unit_and_offset(a1, a2)
    origin = _wall_anchor(region, a1, a2, t, 0, offset_player_widths)
    _, floor = region.surface_z((origin["x"], origin["y"]))
    cursor = round(floor - top_player_heights * PLAYER_HEIGHT)
    minimum_top = None
    for index, block in enumerate(blocks):
        first = len(layout.placements)
        if block.kind == "sprite":
            size = extents(block.tile, block.x_repeat, block.y_repeat, block.cstat)
            if size is None:
                report["skipped"].append(f"{index}: tile {block.tile} not in ART")
                continue
            got = sprite(layout, f"{group_id}_{index}", region_id, a1, a2,
                         tile=block.tile, x_repeat=block.x_repeat,
                         y_repeat=block.y_repeat, cstat=block.cstat, t=t,
                         height_player_heights=(floor - cursor - size[2]) / PLAYER_HEIGHT,
                         offset_player_widths=offset_player_widths, top_z_min=minimum_top,
                         shade=block.shade if block.shade is not None else -8)
            if got is None:
                report["skipped"].append(f"{index}: tile {block.tile} did not fit")
                continue
            report["placed"].append(got)
            t = layout.placements[-1].anchor["t"]
            origin = _wall_anchor(region, a1, a2, t, 0, offset_player_widths)
            _, floor = region.surface_z((origin["x"], origin["y"]))
        else:
            got = text(layout, f"{group_id}_{index}", region_id, a1, a2,
                       words=block.words, style=block.style,
                       size=block.size, palette=block.palette,
                       shade=block.shade if block.shade is not None else LETTER_SHADE,
                       t=t, top_z=cursor, top_z_min=minimum_top,
                       offset_player_widths=offset_player_widths, vertical=block.vertical)
            if not got:
                report["skipped"].append(f"{index}: {block.words!r} did not fit")
                continue
            report["placed"].extend(got)
        bottoms = []
        for placement in layout.placements[first:]:
            box = extents(placement.picnum, placement.x_repeat,
                          placement.y_repeat, placement.cstat)
            _, rect = _anchor_rect(layout, placement, a1, a2, box, unit)
            bottoms.append(rect.z1)
        cursor = max(bottoms) + round(block.gap * PLAYER_HEIGHT)
        minimum_top = cursor
    return report
