"""The reader half of "one record, one frame": surfaces recovered from a MAP.

`surface.Surface` and `texture_frame.WallRunFrame` are the writer. This is the
inverse. Given an original level, group its wall records into SURFACES -- the
maximal sets of records that one material, projected once from one origin at
one scale, would have produced -- and fit that frame to each. What the frame
reproduces exactly is understood; what it does not is residue, per record,
with the field that disagrees.

The grouping law, stated so it can be argued with
=================================================

Two records belong to one surface when all four hold:

1. they meet at a shared vertex, in the editor's own traversal
   (`ED32_AutoAlignWalls`, `xmpmaped.cpp:3096-3144`, which is
   `texture_frame._next_on_run`) -- so the relation is the engine's, not a
   geometric guess of ours;
2. they wear the same `picnum`;
3. they carry the same SCALE, in texels per world unit: `x_repeat * 8 /
   length` (`AlignWalls`, `:3036`, where `xrepeat<<3` is the texel count a
   wall consumes);
4. the second record's `x_panning` is where the first record's projection
   arrives: `(x_panning + x_repeat * 8) mod tile_width` -- which is
   `texture_frame.join_continues`'s x clause, and is exactly "continuity of
   world u across the shared vertex".

Clause 3 is the one that is a judgement. Blood's `x_repeat` is a byte and
`AlignWalls` rounds, so two records of one surface can differ by a repeat of 1
on a short wall and still be the same projection. The tolerance is therefore
stated in REPEATS (`scale_tolerance`, default 0: exact) rather than in a float
epsilon, and the census reports how many records join only because of it.

What is deliberately not done here
==================================

No record is repaired, no field is written back to the level, and a run is
never extended across a break "because it obviously continues". A surface that
covers one record is a surface of one record, and the ledger says how many
there are -- a reader that tidies its own input measures its own tidying.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Sequence

from .texture_frame import (
    FrameError, PANNING_PERIOD, WallRunFrame, WALL_FLIP_MASK, _fields,
    _next_on_run, c_div, resolve_run, sector_index, wall_length, wall_visible,
    wall_z_peg, world_u,
)

#: Where the ART lives when nobody says otherwise. A reader that silently
#: measures nothing because the ART is absent is worse than one that stops,
#: so `read_surfaces` refuses an empty size table rather than returning zero
#: surfaces and calling the map understood.
DEFAULT_ART = "reference/blood"


class SurfaceReadError(ValueError):
    """The map cannot be read as surfaces with the evidence available."""


@dataclass
class RecoveredSurface:
    """One material, projected once, and the records it accounts for."""

    surface_id: str
    tile: int
    records: list[int]
    frame: WallRunFrame
    #: Records the frame reproduces field for field.
    exact: list[int] = field(default_factory=list)
    #: `record -> {field: (in the map, from the frame)}` for the rest.
    mismatches: dict[int, dict[str, tuple[int, int]]] = field(default_factory=dict)
    #: Does the surface's u-origin agree with its own world coordinate?
    world_phased: bool = False
    joined_by_tolerance: int = 0

    @property
    def understood(self) -> bool:
        return len(self.exact) == len(self.records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "tile": int(self.tile),
            "records": list(self.records),
            "frame": {
                "tile": int(self.frame.tile),
                "texels_per_unit": float(self.frame.texels_per_unit),
                "u0": int(self.frame.u0),
                "v0": None if self.frame.v0 is None else int(self.frame.v0),
                "y_repeat": int(self.frame.y_repeat),
                "flip": int(self.frame.flip),
            },
            "exact": len(self.exact),
            "mismatched": sorted(self.mismatches),
            "mismatch_fields": {
                str(record): {key: [int(a), int(b)] for key, (a, b) in row.items()}
                for record, row in sorted(self.mismatches.items())
            },
            "world_phased": bool(self.world_phased),
            "joined_by_tolerance": int(self.joined_by_tolerance),
        }


def implied_scale(level: Any, index: int) -> float | None:
    """This record's own texels per world unit, or None for a zero-length wall.

    `AlignWalls` (`:3036`) accumulates `xrepeat<<3` texels across a wall, so
    the scale a record states is `x_repeat * 8 / length`.
    """
    length = wall_length(level, index)
    if length <= 0:
        return None
    return int(_fields(level.walls[index])["x_repeat"]) * 8.0 / length


def _repeat_for(level: Any, index: int, scale: float) -> int:
    """`resolve_run`'s own rounding, so the two never disagree."""
    return max(1, min(255, int(round(wall_length(level, index) * scale / 8.0))))


def continues(level: Any, this: int, nxt: int, width: int) -> bool:
    """Does the projection arrive where the next record starts it?

    `texture_frame.join_continues`'s x clause, lifted out because the surface
    partition needs it on pairs that are not `point2` neighbours inside one
    loop -- the editor's traversal hops through `next_wall` too.
    """
    face = _fields(level.walls[this])
    other = _fields(level.walls[nxt])
    want = (int(face["x_panning"]) + (int(face["x_repeat"]) << 3)) % int(width)
    return int(other["x_panning"]) == want


def surface_partition(level: Any, *, art_sizes: dict[int, tuple[int, int]],
                      owners: Sequence[int] | None = None,
                      scale_tolerance: int = 0,
                      ) -> tuple[list[list[int]], dict[str, Any]]:
    """Every wall record, cut into surfaces, deterministically.

    Returns the runs and a census of why records did NOT join: the reasons are
    the interesting half, because each one names a place where the map does
    something a single projection cannot express.
    """
    owners = list(owners) if owners is not None else sector_index(level)
    successor: dict[int, int] = {}
    tolerated: set[int] = set()
    broke = Counter()
    #: `record -> (the same-material neighbour it did not join, why)`. This is
    #: the residue's evidence: a break is only interesting where a neighbour
    #: of the same material existed to break from.
    breaks: dict[int, tuple[int, str]] = {}
    unmeasurable: list[int] = []
    for index in range(len(level.walls)):
        face = _fields(level.walls[index])
        tile = int(face["picnum"])
        size = art_sizes.get(tile)
        if not size or not size[0]:
            unmeasurable.append(index)
            continue
        nxt = _next_on_run(level, index, tile, owners, {index}, 100.0)
        if nxt is None:
            broke["no successor of this material"] += 1
            continue

        def stop(reason: str) -> None:
            broke[reason] += 1
            breaks[index] = (int(nxt), reason)

        here, there = implied_scale(level, index), implied_scale(level, nxt)
        if here is None or there is None:
            stop("a record of zero length")
            continue
        want = _repeat_for(level, nxt, here)
        got = int(_fields(level.walls[nxt])["x_repeat"])
        if abs(want - got) > int(scale_tolerance):
            stop("a different scale")
            continue
        if want != got:
            tolerated.add(nxt)
        if not continues(level, index, nxt, size[0]):
            stop("u does not continue across the vertex")
            continue
        if (int(face["cstat"]) & WALL_FLIP_MASK) != (
                int(_fields(level.walls[nxt])["cstat"]) & WALL_FLIP_MASK):
            stop("a different flip")
            continue
        if int(face["y_repeat"]) != int(_fields(level.walls[nxt])["y_repeat"]):
            stop("a different vertical scale")
            continue
        successor[index] = nxt

    has_predecessor = set(successor.values())
    blind = set(unmeasurable)
    runs: list[list[int]] = []
    covered: set[int] = set()

    def follow(start: int) -> list[int]:
        run, seen, current = [start], {start}, start
        while True:
            nxt = successor.get(current)
            if nxt is None or nxt in seen or nxt in covered:
                break
            run.append(nxt)
            seen.add(nxt)
            current = nxt
        return run

    for index in range(len(level.walls)):
        if index in covered or index in has_predecessor or index in blind:
            continue
        run = follow(index)
        covered.update(run)
        runs.append(run)
    #: What is left is a closed loop of one material with no start anywhere in
    #: it -- a round pillar, a circular shaft. Seeded in index order so the
    #: choice of where to break it is at least stable.
    for index in range(len(level.walls)):
        if index in covered or index in blind or index not in successor:
            continue
        run = follow(index)
        covered.update(run)
        runs.append(run)
    #: and what is left after that is a record with no successor and no
    #: predecessor: a surface of one record, which is a real answer.
    for index in range(len(level.walls)):
        if index not in covered and index not in blind:
            covered.add(index)
            runs.append([index])
    census = {
        "records": len(level.walls),
        "unmeasurable": sorted(unmeasurable),
        "breaks": dict(broke),
        "break_records": {int(k): [int(v[0]), v[1]] for k, v in sorted(breaks.items())},
        "joined_by_tolerance": sorted(tolerated),
    }
    return runs, census


def fit_v0(level: Any, run: Sequence[int], y_repeat: int, height: int,
           owners: Sequence[int]) -> int:
    """The world z the material hangs from, solved rather than assumed.

    `resolve_run` derives every record's `y_panning` from one `v0`
    (`AlignWalls`, `:3044`: the vertical phase is affine in the peg height),
    so a frame that takes `v0` as the first record's own peg forces that
    record's `y_panning` to zero -- and the map's is usually not zero. The
    correct reading is the inverse: each record STATES a `v0` through its own
    `y_panning`, and the surface's `v0` is the one the most records state.

    Solving `y_panning = c_div((peg - v0) * y_repeat, height << 3) mod 256`
    for `v0` gives `v0 = peg - y_panning * (height << 3) / y_repeat` up to the
    modulus, so the candidates are exactly one per record and the fit is a
    vote, not a search.
    """
    if not y_repeat or not height:
        return wall_z_peg(level, run[0], owners)
    span = (int(height) << 3)
    pegs = [wall_z_peg(level, index, owners) for index in run]
    wanted = [int(_fields(level.walls[index])["y_panning"]) for index in run]

    def predicts(v0: int, position: int) -> bool:
        return (c_div((pegs[position] - v0) * int(y_repeat), span)
                % PANNING_PERIOD) == wanted[position]

    #: One candidate per record, then a short exact walk around it: the
    #: inverse of a TRUNCATING division is an interval, not a point, and
    #: taking its midpoint lands one texel out about a third of the time.
    candidates: list[int] = []
    for position, peg in enumerate(pegs):
        seed = peg - (wanted[position] * span) // int(y_repeat)
        step = max(1, span // int(y_repeat))
        for delta in range(-2, 3):
            guess = seed + delta * step
            if predicts(guess, position):
                candidates.append(guess)
                break
        else:
            candidates.append(seed)
    best, score = candidates[0], -1
    for guess in dict.fromkeys(candidates):
        agree = sum(1 for position in range(len(run)) if predicts(guess, position))
        if agree > score:
            best, score = guess, agree
    return int(best)


def fit_frame(level: Any, run: Sequence[int], owners: Sequence[int], *,
              art_sizes: dict[int, tuple[int, int]] | None = None
              ) -> WallRunFrame:
    """The one frame that best explains this run.

    The scale is the run's MODAL implied scale rather than its first record's:
    a run whose first wall is short carries the most rounding, and taking it
    as the truth would make every other record of the surface a mismatch.
    """
    face = _fields(level.walls[run[0]])
    scales = [implied_scale(level, index) for index in run]
    real = [value for value in scales if value]
    modal = Counter(round(value, 6) for value in real).most_common(1)
    tile = int(face["picnum"])
    height = (art_sizes or {}).get(tile, (0, 0))[1]
    y_repeat = int(face["y_repeat"])
    return WallRunFrame(
        tile=tile,
        texels_per_unit=float(modal[0][0]) if modal else 1.0 / 16.0,
        u0=int(face["x_panning"]),
        v0=fit_v0(level, run, y_repeat, int(height), owners),
        y_repeat=y_repeat,
        flip=int(face["cstat"]) & WALL_FLIP_MASK,
    )


_CHECKED = ("picnum", "x_repeat", "x_panning", "y_repeat", "y_panning")


class _Scratch:
    """The level with only this run's records copied.

    `resolve_run` is the writer and it must stay the writer -- a reader that
    reimplements the projection would drift from it silently. So the replay
    calls the real function, and the only trick is that it is handed a level
    whose OTHER records are the originals: `resolve_run` writes to the run's
    faces and reads everything else, so copying `len(run)` walls is enough and
    a whole-level `deepcopy` per surface is not (2481 of them took minutes).
    """

    __slots__ = ("walls", "sectors", "sprites")

    def __init__(self, level: Any, run: Sequence[int]) -> None:
        self.walls = list(level.walls)
        self.sectors = level.sectors
        self.sprites = getattr(level, "sprites", [])
        for index in run:
            self.walls[index] = deepcopy(level.walls[index])


def _replay(level: Any, run: Sequence[int], frame: WallRunFrame,
            art_sizes: dict[int, tuple[int, int]], owners: Sequence[int]):
    """Write the frame onto a COPY and say, per record, what disagreed.

    One difference is not a disagreement: E3M1 stores `x_panning` values at or
    above the tile width (tile 108 is 64 wide and the map writes 96), and the
    engine indexes the texel modulo the width, so 96 and 32 are the same
    projection. `resolve_run` writes the reduced form. Counting that as a
    mismatch would say the frame failed where the only difference is which of
    two spellings of one number the file holds -- so it is counted apart, as
    `normalised`, and the structure diff treats them as equal.
    """
    before = [dict(_fields(level.walls[index])) for index in run]
    copy = _Scratch(level, run)
    resolve_run(copy, list(run), frame, art_sizes, owners)
    width = int((art_sizes.get(int(frame.tile)) or (0, 0))[0])
    exact, wrong, normalised = [], {}, []
    for position, index in enumerate(run):
        after = _fields(copy.walls[index])
        row = {key: (int(before[position][key]), int(after[key]))
               for key in _CHECKED
               if int(before[position][key]) != int(after[key])}
        if "x_panning" in row and width:
            was, now = row["x_panning"]
            if was % width == now % width:
                row.pop("x_panning")
                normalised.append(index)
        if row:
            wrong[index] = row
        else:
            exact.append(index)
    return exact, wrong, normalised


def read_surfaces(level: Any, *, art_sizes: dict[int, tuple[int, int]] | None = None,
                  art_dir: str = DEFAULT_ART, scale_tolerance: int = 0,
                  ) -> dict[str, Any]:
    """Recover the surfaces, and say which records no surface explains.

    The residue is what the experiment asks for -- a record whose u-origin
    fits no neighbour's frame -- split into the two things that sentence can
    mean, because they measure different failures:

    * **broken**: the record HAS a same-material neighbour across a shared
      vertex and does not continue its projection. This is the residue that
      says the map does something one frame cannot: a restarted run, a second
      scale, a mirrored band.
    * **solitary**: the record has no same-material neighbour at all. Its
      frame is itself, so it reproduces exactly and explains nothing. Counted
      as residue and reported apart, because calling it understood would be
      calling every isolated tile an insight.

    A record is EXPLAINED only when it sits in a surface of two or more
    records that one frame reproduces field for field. That is the whole
    asymmetry of the gate: a frame fitted to a single record always comes back
    identical, and identity that cost nothing is not evidence.
    """
    if art_sizes is None:
        from .texture_align import wall_art_sizes

        art_sizes = wall_art_sizes(art_dir)
    if not art_sizes:
        raise SurfaceReadError(
            f"no ART sizes under {art_dir!r}: a surface reader without tile "
            f"widths measures nothing and would report the map as understood")
    owners = sector_index(level)
    runs, census = surface_partition(
        level, art_sizes=art_sizes, owners=owners,
        scale_tolerance=scale_tolerance)
    tolerated = set(census["joined_by_tolerance"])
    #: The independent check on the whole grouping: `continuity_rows` measures
    #: the same x continuity over same-tile `point2` joins by join class and
    #: was written long before this module. If the two disagree wildly, one of
    #: them is wrong -- and it is cheap enough to always ask.
    from .texture_frame import continuity_rows

    census["continuity_by_join_class"] = continuity_rows(level, art_sizes)

    surfaces: list[RecoveredSurface] = []
    all_normalised: list[int] = []
    for number, run in enumerate(sorted(runs, key=lambda item: item[0])):
        frame = fit_frame(level, run, owners, art_sizes=art_sizes)
        try:
            exact, wrong, normalised = _replay(
                level, run, frame, art_sizes, owners)
        except FrameError as error:            # a tile with no ART height
            exact, wrong, normalised = [], {index: {"art": (0, 0)} for index in run}, []
            census.setdefault("refused", []).append(str(error))
        all_normalised.extend(normalised)
        size = art_sizes.get(int(frame.tile)) or (0, 0)
        phased = bool(size[0]) and (
            int(frame.u0) % int(size[0])
            == world_u(level, run[0], texels_per_unit=frame.texels_per_unit)
            % int(size[0]))
        surfaces.append(RecoveredSurface(
            surface_id=f"surface:{number:04d}", tile=int(frame.tile),
            records=list(run), frame=frame, exact=exact, mismatches=wrong,
            world_phased=phased,
            joined_by_tolerance=len(set(run) & tolerated)))

    singles = [item for item in surfaces if len(item.records) == 1]
    covered = {index for item in surfaces for index in item.records}
    #: A record is touched by a break if its own projection stopped at a
    #: neighbour, or if a neighbour's projection stopped at it.
    broke_from = {int(key) for key in census["break_records"]}
    broke_into = {int(value[0]) for value in census["break_records"].values()}
    alone = {item.records[0] for item in singles}
    broken = sorted(alone & (broke_from | broke_into))
    solitary = sorted(alone - set(broken))
    explained = sorted(index for item in surfaces if len(item.records) > 1
                       for index in item.exact)
    mismatched = sorted(index for item in surfaces for index in item.mismatches)
    visible = [index for index in broken + solitary
               if wall_visible(level, index, owners)]
    return {
        "surfaces": surfaces,
        "census": census,
        "records": len(level.walls),
        "records_covered": len(covered),
        "records_unmeasurable": census["unmeasurable"],
        "surfaces_understood": sum(1 for item in surfaces if item.understood),
        "records_explained": explained,
        "records_exact": sum(len(item.exact) for item in surfaces),
        "records_mismatched": mismatched,
        "residue_broken": broken,
        "residue_solitary": solitary,
        "residue_records": sorted(set(broken) | set(solitary) | set(mismatched)),
        "residue_records_visible": visible,
        "multi_record_surfaces": len(surfaces) - len(singles),
        "world_phased_surfaces": sum(1 for item in surfaces if item.world_phased),
        "records_normalised": sorted(all_normalised),
    }


def summary(result: dict[str, Any]) -> dict[str, Any]:
    """The ledger row for this layer."""
    records = int(result["records"])
    residue = len(result["residue_records"])
    return {
        "records": records,
        "surfaces": len(result["surfaces"]),
        "surfaces_of_more_than_one_record": int(result["multi_record_surfaces"]),
        "records_explained": len(result["records_explained"]),
        "records_mismatched": len(result["records_mismatched"]),
        "records_unmeasurable": len(result["records_unmeasurable"]),
        "records_normalised": len(result["records_normalised"]),
        "residue_broken": len(result["residue_broken"]),
        "residue_solitary": len(result["residue_solitary"]),
        "residue_records": residue,
        "residue_percent": round(100.0 * residue / records, 2) if records else 0.0,
        "breaks": dict(result["census"]["breaks"]),
    }
