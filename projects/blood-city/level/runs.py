"""Runs: a rhythm of detail along a span, as executable craft.

The unit here is the **run**, not the object. A sewer tunnel, a corridor, a
quay, a fence: something long, whose length decides how much detail it
carries and whose context decides where that detail may not go. The
declaration is one line; the emission is large. That locality is the point.

This generalises a pattern that already works in this repository three
times -- `prefab.alcove_run`, `sprite_bridge` and `parapet` all take a span
plus its context and emit a rhythm. It does not invent it.

**Rhythm is corpus-calibrated.** `tools/mine_run_rhythm.py` projects
everything attached to a long thin sector onto its long axis and measures
the gaps: 702 runs, 4,755 gaps, **median gap 0.5 plan units** and **0.485
items per plan unit** -- about one thing every two plan units, q3 1.25,
p90 2.99. `EVERY_PLAN` below is that median density, not a guess.

**Variation is deterministic.** Verification in this project rests on
before/after frame comparison, so a prefab that varies randomly destroys
the method. Every choice is seeded from the run's stable identity and the
beat index: two runs differ, the same run rebuilds byte-identically.

**Cost is declared before emission.** `estimate` returns the walls a run
will add so a planner can budget against the 7,000 cap before generating.
A wall-mounted element costs nothing; a carved element costs eight.

**The parameter range is the unit of test**, not one instance. `beats`
places at ``(i + 0.5) / count`` rather than at ``i * every``: the latter is
what opened a gap between every pair of planks in `sprite_bridge`, because
the spacing rounded down and the remainder went to one end.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Sequence

PLAN = 1024

#: The campaign's own density: 0.485 items per plan unit is one every 2.06.
EVERY_PLAN = 2.06
#: Its q1 and p90, which bound what a caller may ask for without saying why.
EVERY_MIN, EVERY_MAX = 0.8, 3.0


@dataclass(frozen=True)
class Element:
    """One thing a run can place, and what it costs to place it.

    `kind` is not declared here -- it is read from the measured prop
    catalogue, because a tile's alignment is a property of the tile and
    declaring it by hand gets it wrong. Tile 795 was declared "wall" in the
    first version of this table and the compiler rejected it correctly: it
    carries floor alignment (cstat 160), and a floor sprite on a wall hangs
    in the air.
    """
    tile: int
    walls: int = 0            # emitted walls; sprites are free
    note: str = ""

    @property
    def kind(self) -> str:
        import props
        spec = props.CATALOGUE.get(self.tile)
        if spec is None:
            raise RunError(f"tile {self.tile} is not in the prop catalogue, "
                           f"so its mounting is unknown")
        return spec["kind"]


#: The sewer's own run vocabulary, every tile attested on campaign runs by
#: `mine_run_rhythm` and identified by looking at it:
#:
#:   694  a pipe with an elbow      692  a hanging chain
#:   795  a round wall grate         54  drips
#:  1060  an X-braced truss         104  a railing
#: Only the wall-aligned ones run along a wall; 694 and 692 hang high
#: (+2.88 and +3.44 player heights) and 795 is floor-aligned, so they are
#: not wall elements however much a pipe sounds like one.
SEWER_ELEMENTS = (
    Element(54, note="drips"),
    Element(1060, note="an X-braced truss"),
    Element(104, note="a railing"),
    Element(743, note="a plaque"),
)

#: How many beats in a row may carry the same element before the run has to
#: vary. Mass repetition is the fastest route to content that reads as
#: generated, and the discriminator's blandness already measures it.
MAX_REPEAT = 2

#: How far a run keeps clear of its own two ends, as a fraction of the span.
#: A bracket at the very corner reads badly, and it is also where the next
#: room along joins: the first sewer runs put their last beat exactly on the
#: corner join and seven sprites ended up hanging over the opening.
END_INSET = 0.08


class RunError(ValueError):
    """A run the layer will not emit, naming the fix."""


@dataclass(frozen=True)
class Run:
    """A span, its identity, and what may not be built on it.

    `occupied` are (start, end) fractions of the span that something else
    already owns -- a doorway, a neck, a mounted light. A run declines to
    build there rather than colliding: the compiler would reject it anyway,
    and an author who has to know which stretches are free is back to
    placing detail one at a time.
    """
    name: str
    room: Any
    face: str
    length_plan: float
    every_plan: float = EVERY_PLAN
    elements: Sequence[Element] = SEWER_ELEMENTS
    occupied: Sequence[tuple[float, float]] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name:
            raise RunError("a run needs a stable name: it seeds its variation")
        if self.length_plan <= 0:
            raise RunError(f"{self.name}: length {self.length_plan} is not a span")
        if not (EVERY_MIN <= self.every_plan <= EVERY_MAX):
            raise RunError(
                f"{self.name}: {self.every_plan} plan units between items is "
                f"outside the campaign's q1..p90 of {EVERY_MIN}..{EVERY_MAX}; "
                f"pass it deliberately or use EVERY_PLAN ({EVERY_PLAN})")
        if not self.elements:
            raise RunError(f"{self.name}: no elements to place")


def occupied_from_layout(layout, room, face: str) -> tuple:
    """The stretches of this face a connection already owns, as fractions.

    `alcove_run` learned this the hard way: a doorway is not a region that
    overlaps the niche, it is a *connection* sharing the same stretch of
    wall, so a footprint test cannot see it and the compiler reports the
    result as an unpaired portal instead. Asking the layout is the only
    reliable way -- and hand-listing the spans, which the first version of
    the sewer table did, left twelve sprites hanging over openings.
    """
    import props

    x0, y0, x1, y1 = props.room_rect(room)
    horizontal = face in ("north", "south")
    lo, hi = (x0, x1) if horizontal else (y0, y1)
    span = max(1, hi - lo)
    axis = 1 if horizontal else 0          # the constant coordinate
    line = {"north": y0, "south": y1, "west": x0, "east": x1}[face]
    region_id = getattr(room, "region_id", None)
    out = []
    for connection in layout.connections.values():
        if region_id not in (connection.region_a, connection.region_b):
            continue
        a1, a2 = connection.a1, connection.a2
        if a1 is None or a2 is None:
            continue
        if abs(a1[axis] - line) > 1 or abs(a2[axis] - line) > 1:
            continue                        # not on this face
        along = 0 if horizontal else 1
        t0 = (min(a1[along], a2[along]) - lo) / span
        t1 = (max(a1[along], a2[along]) - lo) / span
        # A little margin: a sprite mounted right at a portal's edge still
        # reads as hanging in the opening.
        out.append((t0 - 0.03, t1 + 0.03))
    return tuple(out)


def _roll(seed: str, n: int) -> int:
    """A stable index. The same run rebuilds identically, always."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % max(1, n)


def beats(run: Run) -> list[tuple[int, float]]:
    """(index, t) for every beat of this run, free ones only.

    Placed at ``(i + 0.5) / count``: evenly spaced *inside* the span, so
    neither end is jammed into a corner and no remainder collects at one
    end. Placing at ``i * every`` is what left a gap between every pair of
    `sprite_bridge`'s planks.
    """
    count = max(1, round(run.length_plan / run.every_plan))
    usable = 1.0 - 2 * END_INSET
    out = []
    for index in range(count):
        t = END_INSET + usable * (index + 0.5) / count
        if any(lo <= t <= hi for lo, hi in run.occupied):
            continue
        out.append((index, t))
    return out


def choose(run: Run, index: int) -> Element:
    """Which element this beat carries, deterministically and with variety.

    Seeded from the run's name and the beat index, then forced to change
    after `MAX_REPEAT` identical beats -- repetition is the failure mode
    this layer is most likely to produce.
    """
    picked = run.elements[_roll(f"{run.name}:{index}", len(run.elements))]
    if index >= MAX_REPEAT and len(run.elements) > 1:
        window = {run.elements[_roll(f"{run.name}:{i}", len(run.elements))]
                  for i in range(index - MAX_REPEAT, index)}
        if len(window) == 1 and picked in window:
            others = [e for e in run.elements if e != picked]
            picked = others[_roll(f"{run.name}:{index}:vary", len(others))]
    return picked


def estimate(run: Run) -> dict:
    """What this run will cost, before anything is emitted."""
    placed = beats(run)
    walls = sum(choose(run, index).walls for index, _t in placed)
    return {"beats": len(placed), "walls": walls,
            "walls_per_plan_unit": round(walls / run.length_plan, 3)}


def emit(layout, run: Run) -> dict:
    """Place the run. Returns what it did, including its realised cost."""
    import props

    report = {"run": run.name, "placed": 0, "walls": 0, "skipped": 0,
              "tiles": {}}
    rect = props.room_rect(run.room)
    for index, t in beats(run):
        element = choose(run, index)
        try:
            if element.kind in ("wall_aligned", "bracket"):
                props.mount_on_wall(layout, f"run:{run.name}:{index}",
                                    run.room, run.face, element.tile, t=t)
            else:
                props.stand_on_floor(layout, f"run:{run.name}:{index}",
                                     run.room.region_id, local=(t, 0.5),
                                     tile=element.tile)
        except Exception:
            report["skipped"] += 1
            continue
        report["placed"] += 1
        report["walls"] += element.walls
        report["tiles"][element.tile] = report["tiles"].get(element.tile, 0) + 1
    return report


def emit_all(layout, runs: Sequence[Run]) -> dict:
    """Every run, with the budget declared before the first is placed."""
    planned = [estimate(run) for run in runs]
    total = {"runs": len(runs), "planned_beats": sum(p["beats"] for p in planned),
             "planned_walls": sum(p["walls"] for p in planned),
             "placed": 0, "walls": 0, "skipped": 0, "tiles": {}}
    for run in runs:
        got = emit(layout, run)
        total["placed"] += got["placed"]
        total["walls"] += got["walls"]
        total["skipped"] += got["skipped"]
        for tile, n in got["tiles"].items():
            total["tiles"][tile] = total["tiles"].get(tile, 0) + n
    return total
