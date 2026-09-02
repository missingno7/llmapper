"""Light as a field, and the shadow as one of its iso-lines.

A shadow is not an overlay of its own. Sources sum -- the sun is a directional
source occluded by the masses, a lamp is a point source with a range -- the
field is quantised to a few levels, and the cut set is where the level
changes. A lamp inside a shadow then resolves itself, shadow plus lamp, with
no pairwise rule for anybody to write.

The quantisation, and what the corpus actually says
==================================================

The decision is `base + k * STEP`, with `base` the network's own lit shade,
`k` the number of overlapping shadows, and no penumbra level. Re-measured
over the 38 campaign maps that have outdoor ground, on the 402 same-z outdoor
boundaries where the shade changes:

* **the step is 12** -- but as the MEDIAN, not the mode. The distribution is
  flat: 16 appears 40 times, 10 thirty-four, 12 thirty-three, 8 thirty, and
  the commonest value takes only 9% of the boundaries. Calling any of them
  "the modal shadow step" overstates it. The median is exactly 12.0, the mean
  14.1, the quartiles 8 and 18, and **half of all boundaries lie in [8, 16]**
  -- which is the interval the gate uses, and it is an interval precisely
  because the corpus does not have a mode.
* **four levels is the right cap.** Counting a level as one carrying at least
  a tenth of a map's outdoor sectors, the median map uses 3 and **81% use 4
  or fewer**. (At a twentieth the count runs to 17, which is noise being
  counted as design; the tenth is the floor that makes the statistic mean
  something.)
* **the lit base varies more than the decision says.** The per-map modal
  outdoor shade runs -128 to 37, with 0 commonest on 12 maps. The stated
  0..30 covers nearly all of it; -128 is one map and is a fullbright, not a
  base.

So the decided form stands and one of its reasons does not, which is worth
the sentence: a number that is right for the wrong stated reason survives
until somebody re-derives it from the reason.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .overlay import (
    MIN_PIECE_AREA, Cut, OverlayError, cut_by_convex, region_area,
    signed_area)

#: The median shade delta across the campaign's same-z outdoor boundaries.
STEP = 12
#: Half of them lie here. The gate is the interval, not the number, because
#: the distribution has no mode worth the name.
STEP_ENVELOPE = (8, 16)
#: A network may reach base and three shadow levels. 81% of campaign maps use
#: four significant outdoor levels or fewer; the median uses three.
MAX_LEVELS = 4
#: Where a level has to sit to be one: a tenth of the surface.
LEVEL_FLOOR = 0.10


class FieldError(ValueError):
    """A light field that cannot be built as asked."""


@dataclass(frozen=True)
class Mass:
    """Something that occludes the sun."""

    mass_id: str
    outline: tuple[tuple[int, int], ...]
    height: int


@dataclass
class Piece:
    """One region of constant light: its rings, and how many shadows deep."""

    rings: list[list[tuple[int, int]]]
    depth: int = 0
    sources: list[str] = field(default_factory=list)

    @property
    def area(self) -> float:
        return region_area(self.rings)


def sun_vector(height: int, bearing_units: int, per_height: float = 1.0
               ) -> tuple[int, int]:
    """How far and which way a mass of this height throws its shadow."""
    length = int(height * per_height)
    radians = math.radians(bearing_units * 360.0 / 2048.0)
    return (int(round(length * math.cos(radians))),
            int(round(length * math.sin(radians))))


def shadow_of(mass: Mass, bearing_units: int, per_height: float = 1.0
              ) -> list[tuple[int, int]]:
    """A mass's shadow: its outline swept along the sun vector, hulled."""
    dx, dy = sun_vector(mass.height, bearing_units, per_height)
    points = sorted(set(list(mass.outline)
                        + [(x + dx, y + dy) for x, y in mass.outline]))
    if len(points) < 3:
        raise FieldError(f"{mass.mass_id} has no footprint to cast")

    def half(seq):
        out = []
        for point in seq:
            while len(out) >= 2:
                ax, ay = out[-2]
                bx, by = out[-1]
                if (bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax) > 0:
                    break
                out.pop()
            out.append(point)
        return out

    return half(points)[:-1] + half(list(reversed(points)))[:-1]


def build_field(rings: Sequence[Sequence[tuple[int, int]]],
                masses: Sequence[Mass], *, bearing_units: int,
                per_height: float = 1.0, max_levels: int = MAX_LEVELS,
                min_area: int = MIN_PIECE_AREA) -> dict[str, Any]:
    """Cut one surface by the sun field of every mass that reaches it.

    ONE field per plane, cut once. Each mass's shadow is a convex polygon and
    is applied with `cut_by_convex` to the pieces it actually overlaps, never
    to the whole plane -- cutting the plane with every shadow edge's line
    would run each line to the map's edge and the sector count would explode.

    Depth is additive: a piece under two shadows is two levels down, which is
    what makes a lamp inside a shadow resolve itself later without a pairwise
    rule. It is capped at `max_levels - 1` because the corpus stops at four.
    """
    pieces = [Piece(rings=[list(ring) for ring in rings], depth=0)]
    absorbed: list[dict[str, Any]] = []
    refused: list[str] = []
    for mass in masses:
        try:
            shadow = shadow_of(mass, bearing_units, per_height)
        except FieldError as error:
            refused.append(str(error))
            continue
        grown: list[Piece] = []
        for piece in pieces:
            inside, outside, notes = cut_by_convex(
                piece.rings, shadow, min_area=min_area)
            absorbed.extend({**note, "mass": mass.mass_id} for note in notes)
            if not inside:
                grown.append(piece)
                continue
            deeper = min(piece.depth + 1, max_levels - 1)
            for region in inside:
                grown.append(Piece(rings=region, depth=deeper,
                                   sources=piece.sources + [mass.mass_id]))
            for region in outside:
                grown.append(Piece(rings=region, depth=piece.depth,
                                   sources=list(piece.sources)))
        pieces = grown
    return {"pieces": pieces, "absorbed": absorbed, "refused": refused,
            "levels": sorted({piece.depth for piece in pieces})}


def shade_for(base: int, depth: int, step: int = STEP) -> int:
    """`base + k * step`, and Blood's shade grows darker upward."""
    return int(base) + int(depth) * int(step)


def field_faults(pieces: Sequence[Piece], *, base: int, step: int = STEP,
                 max_levels: int = MAX_LEVELS) -> list[str]:
    """Is this field one the campaign would recognise?

    Three absolute checks, each against a measured number rather than against
    the field's own consistency -- a field uniformly wrong passes every
    relative test, which is the lesson owner-queue item 17 paid for.
    """
    out = []
    levels = sorted({piece.depth for piece in pieces})
    if len(levels) > max_levels:
        out.append(f"{len(levels)} light levels; 81% of campaign maps use "
                   f"{max_levels} or fewer and the median uses 3")
    if len(levels) < 2 and len(pieces) > 1:
        out.append("the field has one level: nothing is in shadow, so the "
                   "cut set is empty and the sun is doing no work")
    low, high = STEP_ENVELOPE
    if not (low <= step <= high):
        out.append(f"a step of {step} is outside the campaign's [{low}, "
                   f"{high}], where half its outdoor shade boundaries lie")
    total = sum(piece.area for piece in pieces)
    if total <= 0:
        out.append("the field covers no area")
    return out


def edges_of(pieces: Sequence[Piece]) -> list[tuple]:
    """Every boundary between two pieces of different depth.

    The iso-lines: what the cut set actually is, recovered from the pieces so
    a gate can ask their bearing without trusting the builder's own list.
    """
    out = []
    for index, piece in enumerate(pieces):
        for other in pieces[index + 1:]:
            if piece.depth == other.depth:
                continue
            shared = _shared_segment(piece.rings[0], other.rings[0])
            if shared is not None:
                out.append(shared)
    return out


def _shared_segment(a: Sequence[tuple[int, int]],
                    b: Sequence[tuple[int, int]]):
    for index, start in enumerate(a):
        end = a[(index + 1) % len(a)]
        for other, b_start in enumerate(b):
            b_end = b[(other + 1) % len(b)]
            if {tuple(start), tuple(end)} == {tuple(b_start), tuple(b_end)}:
                return (tuple(start), tuple(end))
    return None
