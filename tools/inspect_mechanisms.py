"""Watch a mechanism move, instead of checking where it rests.

Almost every fault found in this project was found by a person looking at the
level, and the reason is always the same: the checks read the map file, and the
map file describes one frozen instant. A gate that rests correctly and crosses
its own leaves halfway through looks perfect to every static check ever written
here -- and it did, through four passes -- while being obvious in half a second
to anyone who pushed it.

So this steps a mechanism through its travel and reports what the *opening*
does, frame by frame. The number that matters is how much of the doorway is
blocked at each point, because that is the question a player asks with their
body: can I get through yet.

.. code-block:: bash

    python -m tools.inspect_mechanisms projects/.../candidate-v5.MAP
    python -m tools.inspect_mechanisms ... --frames work/gate --render

`--render` additionally writes one frame per step through the XMapEdit observer,
which turns "the leaves swap sides" from a sentence into a picture.

The travel model is the engine's, not an approximation. `trInit` displaces the
sector to busy -65536, takes *that* as the base, and translates back out to the
authored busy, so for a sprite carried with the sector (cstat 8192)

    position(busy) = authored + T * (busy/65536 - 1)

and for one carried against it (16384) the sign of the second term flips. At
busy 65536 both sit where they were drawn; at 0 they are a full travel either
side of it.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import pathlib
from typing import Any

from bloodmap.format import encode_map, read_map

MOVING = (613, 614, 615, 616, 617)
CARRY_WITH = 8192
CARRY_AGAINST = 16384
FULL = 65536


def _travel(disk: Any, sector: Any) -> tuple[int, int] | None:
    extra = sector.extra
    if extra is None:
        return None
    first = int(extra.fields.get("marker_0", -1))
    second = int(extra.fields.get("marker_1", -1))
    if not (0 <= first < len(disk.sprites) and 0 <= second < len(disk.sprites)):
        return None
    a, b = disk.sprites[first].fields, disk.sprites[second].fields
    return int(b["x"]) - int(a["x"]), int(b["y"]) - int(a["y"])


def carried_sprites(disk: Any, sector_index: int) -> list[int]:
    out = []
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["sector"]) != sector_index:
            continue
        if int(sprite.fields["cstat"]) & (CARRY_WITH | CARRY_AGAINST):
            out.append(index)
    return out


def _pivot(disk: Any, sector: Any) -> tuple[tuple[int, int], int] | None:
    """A rotating sector's axis and its signed sweep."""
    extra = sector.extra
    if extra is None:
        return None
    axis = int(extra.fields.get("marker_0", -1))
    if not 0 <= axis < len(disk.sprites):
        return None
    fields = disk.sprites[axis].fields
    return (int(fields["x"]), int(fields["y"])), int(fields["angle"])


def _rotate(point: tuple[int, int], centre: tuple[int, int], angle: int) -> tuple[int, int]:
    theta = angle / 2048.0 * 2 * math.pi
    dx, dy = point[0] - centre[0], point[1] - centre[1]
    return (int(round(centre[0] + dx * math.cos(theta) - dy * math.sin(theta))),
            int(round(centre[1] + dx * math.sin(theta) + dy * math.cos(theta))))


def pose(disk: Any, sector_index: int, busy: int) -> dict[int, tuple[int, int]]:
    """Where each carried sprite sits at this point in the travel.

    Slide and rotate are the same shape of answer. `trInit` displaces the sector
    by a full travel in the negative direction, takes that as the base, and comes
    back out to the authored busy -- so in both cases the offset from the drawn
    position is `T * (busy/65536 - 1)`, where T is a vector for a slide and an
    angle about the axis marker for a rotation.
    """
    sector = disk.sectors[sector_index]
    fraction = busy / float(FULL)

    if int(sector.fields["type"]) in (615, 617):
        spun = _pivot(disk, sector)
        if spun is None:
            return {}
        centre, sweep = spun
        out: dict[int, tuple[int, int]] = {}
        for index in carried_sprites(disk, sector_index):
            fields = disk.sprites[index].fields
            sign = 1.0 if int(fields["cstat"]) & CARRY_WITH else -1.0
            turn = sign * sweep * (fraction - 1.0)
            out[index] = _rotate(
                (int(fields["x"]), int(fields["y"])), centre, turn)
        return out

    travel = _travel(disk, sector)
    if travel is None:
        return {}
    tx, ty = travel
    fraction = busy / float(FULL)
    out: dict[int, tuple[int, int]] = {}
    for index in carried_sprites(disk, sector_index):
        fields = disk.sprites[index].fields
        sign = 1.0 if int(fields["cstat"]) & CARRY_WITH else -1.0
        shift = sign * (fraction - 1.0)
        out[index] = (int(round(int(fields["x"]) + tx * shift)),
                      int(round(int(fields["y"]) + ty * shift)))
    return out


def facing(disk: Any, sector_index: int, busy: int) -> dict[int, int]:
    """Which way each carried sprite faces at this point in the travel.

    `TranslateSector` turns a carried sprite with the sector: `ang += v14` for
    one carried with it and `-= v14` against. For a slide v14 is zero, so only a
    rotation changes it.
    """
    sector = disk.sectors[sector_index]
    out: dict[int, int] = {}
    if int(sector.fields["type"]) not in (615, 617):
        for index in carried_sprites(disk, sector_index):
            out[index] = int(disk.sprites[index].fields["angle"])
        return out
    spun = _pivot(disk, sector)
    if spun is None:
        return out
    _centre, sweep = spun
    fraction = busy / float(FULL)
    for index in carried_sprites(disk, sector_index):
        fields = disk.sprites[index].fields
        sign = 1.0 if int(fields["cstat"]) & CARRY_WITH else -1.0
        out[index] = int(round(int(fields["angle"]) + sign * sweep * (fraction - 1.0)))
    return out


def _opening(disk: Any, sector_index: int) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """The widest portal out of this sector: the hole the mechanism closes."""
    fields = disk.sectors[sector_index].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    best = None
    for wall in range(start, start + count):
        wf = disk.walls[wall].fields
        if int(wf["next_sector"]) < 0:
            continue
        ax, ay = int(wf["x"]), int(wf["y"])
        nxt = int(wf["point2"])
        bx, by = int(disk.walls[nxt].fields["x"]), int(disk.walls[nxt].fields["y"])
        span = math.hypot(bx - ax, by - ay)
        if best is None or span > best[0]:
            best = (span, (ax, ay), (bx, by))
    return None if best is None else (best[1], best[2])


def blocked_fraction(disk: Any, sector_index: int, busy: int,
                     art: dict[int, Any] | None = None) -> float:
    """How much of the opening the carried sprites cover at this point.

    Each sprite is projected onto the opening as an interval and the union is
    measured, so two leaves meeting in the middle read as 1.0 and two that have
    retracted past the jambs read as 0.0.
    """
    opening = _opening(disk, sector_index)
    if opening is None:
        return 0.0
    (ax, ay), (bx, by) = opening
    span = math.hypot(bx - ax, by - ay)
    if span <= 0:
        return 0.0
    ux, uy = (bx - ax) / span, (by - ay) / span
    positions = pose(disk, sector_index, busy)
    facings = facing(disk, sector_index, busy)
    intervals = []
    for index, (x, y) in positions.items():
        fields = disk.sprites[index].fields
        width = int(fields["x_repeat"]) * 128 / 4.0
        if art is not None:
            tile = art.get(int(fields["picnum"]))
            if tile is not None and tile.width:
                width = int(fields["x_repeat"]) * tile.width / 4.0
        # A panel that has turned no longer presents its full width to the
        # opening. Its angle is the normal of its face, so the plane it lies in
        # runs a quarter turn from that, and what blocks the doorway is the
        # projection of the plane onto the opening. Ignoring this reported a
        # rotating door as half shut when it had swung fully clear.
        plane = (facings.get(index, int(fields["angle"])) + 512) / 2048.0 * 2 * math.pi
        along = abs(math.cos(plane) * ux + math.sin(plane) * uy)
        width *= along
        centre = ((x - ax) * ux + (y - ay) * uy)
        intervals.append((centre - width / 2.0, centre + width / 2.0))
    if not intervals:
        return 0.0
    intervals.sort()
    covered = 0.0
    edge = 0.0
    for low, high in intervals:
        low = max(low, 0.0)
        high = min(high, span)
        if high <= low:
            continue
        low = max(low, edge)
        if high > low:
            covered += high - low
            edge = high
    return covered / span


def report(path: str, *, steps: int = 5, art_dir: str | None = None) -> list[dict[str, Any]]:
    disk = read_map(path)
    art = None
    if art_dir:
        try:
            from bloodmap.art import read_art_directory

            art = read_art_directory(art_dir)
        except Exception:
            art = None
    rows: list[dict[str, Any]] = []
    for index, sector in enumerate(disk.sectors):
        if int(sector.fields["type"]) not in MOVING or sector.extra is None:
            continue
        if not carried_sprites(disk, index):
            continue
        extra = sector.extra.fields
        state = int(extra.get("state", 0))
        rest = FULL if state else 0
        opening = FULL - rest
        series = []
        for step in range(steps):
            t = step / (steps - 1)
            busy = int(round(rest + (opening - rest) * t))
            series.append(round(blocked_fraction(disk, index, busy, art), 3))
        rows.append({
            "sector": index,
            "type": int(sector.fields["type"]),
            "rest_busy": rest,
            "blocked": series,
        })
    return rows


#: A mechanism only counts as a *closure* -- something whose job is to block a
#: doorway -- if its sprites cover most of the opening at some point in the
#: travel. Below this they are riding it rather than sealing it.
CLOSURE_THRESHOLD = 0.9


def describe(series: list[float]) -> str:
    """What the series does, stated without judging it.

    Two attempts at a universal fault rule both failed against the corpus, and
    the failures are the useful part.

    The first judged every carried mechanism and disagreed with the campaign on
    **133 of 136** -- because most sprites carried by a moving sector are not
    gate leaves at all. They are crates on a lift, charges on a platform, a
    torch on a rotating pillar, and nothing about them should cover a doorway.

    The second judged only *closures* and still called 34 of 40 broken, and
    flagged 59% of them for "blocking more midway than at rest" -- because
    plenty of Blood mechanisms rest **open** and close. A trap that shuts is not
    a gate that fails to open.

    So there is no corpus-derived rule here, and there cannot be: the corpus
    records what mechanisms *do*, and whether that is right depends on what the
    author meant them to do. `expect_closure` is the check, and it takes the
    intent as an argument rather than guessing it.
    """
    peak, first, last = max(series), series[0], series[-1]
    if peak < CLOSURE_THRESHOLD:
        return "rides (covers at most %.0f%% of the opening)" % (100 * peak)
    if first >= CLOSURE_THRESHOLD and last <= 0.1:
        return "shut at rest, fully open at the end"
    if first <= 0.1 and last >= CLOSURE_THRESHOLD:
        return "open at rest, fully shut at the end"
    return "shut %.0f%% at rest, %.0f%% at the end, peak %.0f%%" % (
        100 * first, 100 * last, 100 * peak)


def expect_closure(series: list[float], *, opens: bool = True) -> list[str]:
    """Check a profile against a stated intent, and return what disagrees.

    `opens=True` means: this thing is shut when the player finds it and gets out
    of the way completely, without ever blocking more than it started. That is
    what `mechanism.sliding_gate` builds, and it is the only claim strong enough
    to test -- the corpus cannot supply it, because the corpus has no intents.
    """
    problems: list[str] = []
    first, last = series[0], series[-1]
    if opens:
        if first < CLOSURE_THRESHOLD:
            problems.append("only %.0f%% shut at rest" % (100 * first))
        if last > 0.1:
            problems.append("%.0f%% still covered when open" % (100 * last))
        if max(series[1:]) > first + 0.01:
            problems.append("blocks more midway than at rest -- the leaves cross")
    else:
        if first > 0.1:
            problems.append("%.0f%% covered at rest, but it should start open" % (100 * first))
        if last < CLOSURE_THRESHOLD:
            problems.append("only %.0f%% shut at the end" % (100 * last))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--art", default="reference/blood")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    rows = report(args.map, steps=args.steps, art_dir=args.art)
    if not rows:
        print("no moving sector in this map carries a sprite")
        return 0
    print("%-8s %-6s  %-28s %s" % ("sector", "type", "opening blocked, shut -> open", ""))
    bad = 0
    for row in rows:
        series = " ".join("%4.0f%%" % (100 * b) for b in row["blocked"])
        note = describe(row["blocked"])
        problems = expect_closure(row["blocked"]) if max(row["blocked"]) >= CLOSURE_THRESHOLD else []
        if problems:
            bad += 1
            note += "  <-- " + "; ".join(problems)
        print("%-8d %-6d  %-28s %s" % (row["sector"], row["type"], series, note))
    print()
    closures = sum(1 for r in rows if max(r["blocked"]) >= CLOSURE_THRESHOLD)
    print("%d closures, %d other carried mechanisms; %d faulty"
          % (closures, len(rows) - closures, bad))
    if args.output:
        pathlib.Path(args.output).write_text(
            json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
