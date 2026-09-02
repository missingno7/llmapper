"""Facades with holes, inserts with holders, and one owner per record.

A Build wall record has exactly **one** set of texture fields. `picnum` and
`over_picnum` -- the step bands and the masked middle -- share `x_repeat`,
`x_panning`, `y_repeat`, `y_panning` and the flip bits. So a material that
needs its own scale and phase cannot live on a record that also carries a
facade run: whichever writer runs last wins, and the other material is wrong.

That is not a hypothetical. In blood-city, `glass.glaze` set `x_repeat` 32 on
each of 24 panes and `texture_frame.frame_map` then re-derived the facade's
run over the same records: **fifteen kept the pane's number and nine got the
facade's**, and which nine was decided by the order the two passes happen to
run in. Nobody chose it and nothing reported it.

The owner's model, and the fix:

    A building's FACADE provides holes and has its own aligned texture.
    Shopfronts, windows and doors are put INTO the holes.

* A :class:`Surface` is a planar face of a construct -- the street face of a
  building, the inner wall of a room. It has one material, one
  :class:`~bloodmap.texture_frame.WallRunFrame`, and a list of
  :class:`Opening`.
* An :class:`Opening` is a hole in a surface: a rectangle in the facade
  plane. It is a sub-surface, not a construct.
* An :class:`Insert` is the construct bound to one opening -- a shopfront
  (recess plus pane), a window (reveal plus glass or grille), a door (reveal
  sectors plus leaf plus jambs). It **owns its sectors and its frames**.

The only way to give an insert its own record is a sector boundary: a HOLDER
whose return walls end the facade run at the jambs and whose own wall carries
the insert. The facade's continuity across the opening is then a property of
the facade's FRAME -- world-anchored, so it does not care where the cuts are
-- and not of the records the opening happens to cut.

:class:`RecordOwner` is the ledger that makes this checkable rather than
intended. Every pass that writes texture fields claims the records it writes,
a second claim on the same record raises, and the build prints what was
claimed by whom. A gate that depends on nobody forgetting is not a gate; this
one refuses at the point of the write.

Cited: the law is `xmapedit/src_blood/xmpmaped.cpp:3024-3050 AlignWalls`
(which fields a wall has and what they mean) and `GetWallZPeg` (`:2991-3022`,
which band pegs where); the audit behind it is the supervisor brief 6d and the
architect review section 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .texture_frame import WallRunFrame

#: What an insert is. Named rather than free-text so a build cannot invent a
#: fifth kind without saying so here.
SHOPFRONT = "shopfront"
WINDOW = "window"
DOOR = "door"
INSERT_KINDS = frozenset({SHOPFRONT, WINDOW, DOOR})


class SurfaceError(ValueError):
    """A surface, opening or insert was described in a way Build cannot hold."""


class OwnershipError(SurfaceError):
    """Two owners claimed the same record. One of them would have been wrong."""


@dataclass(frozen=True)
class Opening:
    """A hole in a surface: a rectangle in the surface's own plane.

    Not a construct. It is the *absence* the facade provides, and the insert
    bound to it is the thing that owns geometry.
    """

    opening_id: str
    span: tuple[int, int, int, int]
    kind: str = WINDOW

    def __post_init__(self) -> None:
        if self.kind not in INSERT_KINDS:
            raise SurfaceError(f"unknown opening kind {self.kind!r}")
        x0, y0, x1, y1 = self.span
        if x0 == x1 and y0 == y1:
            raise SurfaceError(f"{self.opening_id}: an opening with no extent")

    def contains(self, x: float, y: float) -> bool:
        x0, y0, x1, y1 = self.span
        return (min(x0, x1) <= x <= max(x0, x1)
                and min(y0, y1) <= y <= max(y0, y1))


@dataclass(frozen=True)
class Surface:
    """A planar face of a construct: one material, one frame, some holes.

    The frame is the whole point. Because it is anchored in world space, the
    surface's texture does not know where its openings are -- cutting a new
    door into a facade changes which records exist and changes no pixel on the
    ones that remain. The per-wall representation could not say that.
    """

    surface_id: str
    owner: str
    frame: WallRunFrame
    openings: tuple[Opening, ...] = ()

    def opening_at(self, x: float, y: float) -> Opening | None:
        for opening in self.openings:
            if opening.contains(x, y):
                return opening
        return None


@dataclass(frozen=True)
class Insert:
    """A construct bound to one opening, owning its holder and its frame.

    `holder_regions` is what makes it lawful: an insert with no holder has
    nowhere of its own to put a material, so it would have to borrow the
    facade's record -- which is the defect this module exists to stop.
    """

    insert_id: str
    opening_id: str
    kind: str
    holder_regions: tuple[str, ...] = ()
    frame: WallRunFrame | None = None

    def __post_init__(self) -> None:
        if self.kind not in INSERT_KINDS:
            raise SurfaceError(f"unknown insert kind {self.kind!r}")

    @property
    def lawful(self) -> bool:
        """Does this insert have a record of its own to write on?"""
        return bool(self.holder_regions)


@dataclass
class RecordOwner:
    """Which construct owns each wall record's texture fields.

    The ledger. `claim` is called by every pass that writes `x_repeat`,
    `x_panning`, `y_repeat`, `y_panning` or the flip bits, and a second claim
    on the same record raises :class:`OwnershipError` -- because a second
    claim means two materials wanted the same four fields and one of them was
    about to be silently wrong.

    `concede` is the escape hatch with a name: a pass that knowingly stands
    aside for another owner records that it did so, so the build can print how
    many records a surface gave up to inserts rather than leaving it to
    whoever reads the diff.
    """

    owners: dict[int, str] = field(default_factory=dict)
    conceded: dict[int, str] = field(default_factory=dict)

    def claim(self, record: int, owner: str) -> None:
        record = int(record)
        held = self.owners.get(record)
        if held is not None and held != owner:
            raise OwnershipError(
                f"record {record} is owned by {held!r} and {owner!r} also "
                f"claimed it: a Build wall has one set of texture fields, so "
                f"one of those two materials would be drawn wrong")
        self.owners[record] = owner

    def claim_all(self, records: Iterable[int], owner: str) -> int:
        count = 0
        for record in records:
            self.claim(record, owner)
            count += 1
        return count

    def concede(self, record: int, to: str) -> None:
        """Stand aside for another owner, and say so."""
        self.conceded[int(record)] = to

    def owner_of(self, record: int) -> str | None:
        return self.owners.get(int(record))

    def owns(self, record: int, owner: str) -> bool:
        return self.owners.get(int(record)) == owner

    def may_write(self, record: int, owner: str) -> bool:
        """May `owner` write texture fields on this record?

        Unclaimed records are writable -- a build that has not adopted the
        ledger everywhere still works, and the report says how much of it is
        unclaimed rather than pretending the question was asked.
        """
        held = self.owners.get(int(record))
        return held is None or held == owner

    def report(self) -> dict[str, Any]:
        by_owner: dict[str, int] = {}
        for owner in self.owners.values():
            by_owner[owner] = by_owner.get(owner, 0) + 1
        return {"records_owned": len(self.owners),
                "owners": dict(sorted(by_owner.items())),
                "records_conceded": len(self.conceded)}


def insert_faults(inserts: Sequence[Insert]) -> list[str]:
    """Inserts with nowhere of their own to put a material.

    The source-side half of the `no-record-carries-two-frames` gate: an
    insert without a holder region will end up writing on whatever record the
    surface already owns, and no amount of pass ordering makes that lawful.
    """
    return [f"{insert.insert_id}: a {insert.kind} with no holder region, so "
            f"its material would have to share the surface's record"
            for insert in inserts if not insert.lawful]
