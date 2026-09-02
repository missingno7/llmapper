"""The grid, solved from the inside out instead of taken from a norm.

Gravesend's L1 fixes its block columns and rows from `city-norms.md` -- "CN 2
mid mode", 12 and 14 plan units -- and the rooms are then carved into whatever
that leaves. The arcade is what that costs: its concourse came out at the size
the block allowed rather than the size E4M9 says a concourse is.

The owner's order of decision (street-model-decisions section 9) inverts it.
Three things with different stiffness negotiate:

===============  ==========  =====================================
element          stiffness   what fixes its size
===============  ==========  =====================================
landmark          RIGID      the venue pattern: measured room sizes
corridor         SEMI-RIGID  a class MINIMUM; may grow, never shrink
filler building    SOFT      one room plus walls; takes the rest
plaza, yard,      SLACK      absorbs the residue, on purpose
cemetery, alley
===============  ==========  =====================================

So a cell is as wide as the widest ENVELOPE standing in it -- interior, plus
its walls, plus the facade depth an insert needs (P13's 512 recess) -- and a
gutter is its class minimum and no less. Everything left over goes to the
slack elements. That is a one-dimensional solve per axis, which is all a grid
of running sums ever needed.

And the composition rule (section 10): **roads are spacers, islands are the
designed things.** The quarters are laid out as pavement islands with their
buildings on them, and a road is inserted between two islands to push them
apart by its class width. Where no road runs, islands abut with a
pavement-only path -- E3M1's s10/s11, 512 wide. So this solver never asks
"where is there room for a street"; it asks how wide each island must be and
then spaces them.

Units are Build units here, not plan units: the solve is where L1's schematic
becomes a size, and `resolution.WIDTH_UNITS` is the dictionary that does it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

#: The facade depth an insert needs behind the face: P13's recess, measured on
#: E6M1 (s4/s64 are 4096 x 512 against the shop s52). A building whose
#: envelope does not carry it has nowhere to put a shopfront and its panes end
#: up flush on the facade line, which is the defect P13 counted.
FACADE_DEPTH = 512

#: One room plus its two walls: the least a filler building can be and still
#: be enterable. Below this a frontage is a yard or an alley, not a building.
MIN_BUILDING_DEPTH = 3072

#: E3M1's pavement bands, measured: 512 x2, 1024 x1, 2048 x6, 2560 x1 on its
#: 14 pavement sectors. 2048 is the mode and the band this city uses; 512 is
#: what E3M1 leaves between houses where no road runs, which is the
#: pavement-only path of the composition rule.
BAND = 2048
PATH_BAND = 512
BAND_ENVELOPE = (512, 2560)


class SolveError(ValueError):
    """The plan asks for a city that does not fit its own constraints."""


@dataclass(frozen=True)
class Envelope:
    """What a venue needs, derived UP from its interior.

    `interior` is the measured room extent from the venue's own pattern or
    from the `l3_*` module that builds it -- never a number taken from a
    block. `walls` is the masonry each side.
    """

    venue_id: str
    interior: tuple[int, int]
    walls: int = 512
    facade_depth: int = FACADE_DEPTH
    #: Which faces carry inserts, and therefore need the recess depth. A
    #: building fronting one street pays for it once, not four times.
    faced: tuple[str, ...] = ("south",)

    def demand(self, axis: str) -> int:
        """How much of one axis this envelope claims."""
        size = self.interior[0] if axis == "x" else self.interior[1]
        low, high = (("west", "east") if axis == "x" else ("north", "south"))
        faces = sum(1 for name in (low, high) if name in self.faced)
        return int(size) + 2 * int(self.walls) + faces * int(self.facade_depth)


@dataclass(frozen=True)
class Cell:
    """A column or row of the grid: an island with envelopes standing on it."""

    cell_id: str
    envelopes: tuple[Envelope, ...] = ()
    #: A cell nobody builds on -- a plaza, the cemetery, the yard -- takes the
    #: residue instead of setting a demand.
    slack: bool = False
    band: int = BAND

    def demand(self, axis: str) -> int:
        if self.slack or not self.envelopes:
            return 0
        return max(env.demand(axis) for env in self.envelopes)

    def island(self, axis: str) -> int:
        """The island is the built demand grown by its pavement band."""
        return self.demand(axis) + 2 * int(self.band)


@dataclass(frozen=True)
class Gutter:
    """A road inserted between two islands, or a path where none runs."""

    gutter_id: str
    width_class: str
    #: `None` means a pavement-only path: the islands abut and the gap between
    #: their bands is the whole of it (E3M1 s10/s11, 512).
    minimum: int | None = None

    def width(self, widths: dict[str, int]) -> int:
        if self.width_class == "path":
            return PATH_BAND
        if self.width_class not in widths:
            raise SolveError(f"{self.gutter_id}: unknown width class "
                             f"{self.width_class!r}")
        return int(self.minimum if self.minimum is not None
                   else widths[self.width_class])


@dataclass
class AxisSolution:
    """Where every cell and gutter starts and ends, and what it cost."""

    axis: str
    spans: list[tuple[str, int, int]] = field(default_factory=list)
    total: int = 0
    slack_given: dict[str, int] = field(default_factory=dict)
    demanded: dict[str, int] = field(default_factory=dict)

    def span(self, name: str) -> tuple[int, int]:
        for found, lo, hi in self.spans:
            if found == name:
                return lo, hi
        raise SolveError(f"{name} is not on the {self.axis} axis")


def solve_axis(axis: str, order: Sequence[Cell | Gutter],
               widths: dict[str, int], *, target: int | None = None
               ) -> AxisSolution:
    """One axis, in one pass: islands take what they need, roads their class.

    `target` is the city size to hit. The residue goes to the SLACK cells and
    to nothing else -- never to an interior, never to a corridor below its
    class minimum. If there is no slack cell to take it, the solve reports the
    total it reached rather than quietly stretching something rigid.
    """
    out = AxisSolution(axis=axis)
    sizes: dict[str, int] = {}
    for item in order:
        if isinstance(item, Gutter):
            sizes[item.gutter_id] = item.width(widths)
        else:
            sizes[item.cell_id] = item.island(axis)
            out.demanded[item.cell_id] = item.demand(axis)

    fixed = sum(sizes.values())
    slack_cells = [item for item in order
                   if isinstance(item, Cell) and item.slack]
    if target is not None and slack_cells:
        residue = int(target) - fixed
        share, extra = divmod(residue, len(slack_cells))
        for position, cell in enumerate(slack_cells):
            give = share + (extra if position == len(slack_cells) - 1 else 0)
            grown = sizes[cell.cell_id] + give
            if grown < 2 * cell.band:
                raise SolveError(
                    f"{cell.cell_id}: absorbing {give} would leave "
                    f"{grown}, less than its own pavement band -- the rigid "
                    f"parts of this axis already exceed the target")
            sizes[cell.cell_id] = grown
            out.slack_given[cell.cell_id] = give

    cursor = 0
    for item in order:
        name = item.gutter_id if isinstance(item, Gutter) else item.cell_id
        size = sizes[name]
        out.spans.append((name, cursor, cursor + size))
        cursor += size
    out.total = cursor
    return out


def compare(solution: AxisSolution, old: Sequence[tuple[str, int, int]],
            *, plan_unit: int = 1024) -> dict[str, object]:
    """The solved grid beside the one it replaces, as rates.

    Counts would say nothing: the two grids do not have the same elements.
    What is comparable is the SHAPE -- how much of the axis is corridor, how
    much is built, how much is slack -- and that is what E3M1's block pitch
    can be held against.
    """
    built = sum(hi - lo for name, lo, hi in solution.spans
                if name in solution.demanded)
    corridor = solution.total - built
    old_total = max((hi for _n, _l, hi in old), default=0) * plan_unit
    return {
        "total": solution.total,
        "old_total": old_total,
        "built_share": round(built / solution.total, 3) if solution.total else 0,
        "corridor_share": (round(corridor / solution.total, 3)
                           if solution.total else 0),
        "slack_given": dict(solution.slack_given),
    }
