"""How thin a wall Blood is willing to build between two rooms.

The fault this measures against: squeezing a new part into a layout by hand
leaves whatever space is left over between it and its neighbour, and what is
left over is often four units of stone. The engine draws it happily; a player
reads it as two rooms sharing a sheet of paper.

Method
------

For every *solid* wall of a playable sector, step outward along the wall's own
normal and find the first playable sector on the other side. The distance at
which that happens is the thickness of the mass separating them, measured where
a player would actually see it -- at the wall, not between centroids.

Two things this deliberately does not count:

* **Two-sided walls.** Those are openings, not masses; their thickness is zero
  by construction and including them buries the distribution at 0.
* **The same sector coming back round.** A concave room's normal can re-enter
  the room it started in. That is one space, not two, so it is skipped.
* **Volumes that do not coexist.** A first pass put 16.8% of probes at 16 units
  and made every map's thinnest wall 16, which is not a finding about masonry --
  it is room-over-room. A stack's two halves share a footprint, so a probe out of
  the upper room's wall lands in the lower room immediately. Nothing separates
  them horizontally because nothing is meant to. Two sectors are only separated
  by a *wall* if their floor-to-ceiling ranges overlap, so that a player standing
  in one is at heights the other also occupies.

The probe walks outward in `STEP` units to `REACH`; anything thicker than
`REACH` is not a thin-wall problem and is recorded only as "thicker than".

.. code-block:: bash

    python -m tools.mine_wall_thickness -o knowledge/blood/design/wall-thickness-v1.json
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.format import read_map
from bloodmap.planar_geom import point_in_loop
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.reachability import design_sectors

SCHEMA = "llmapper.blood-wall-thickness"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

PLAYER_WIDTH = PLAYER_PROFILES["blood"].body_width

#: How far out to look, and how finely. 2048 is five and a bit body widths --
#: past that a mass is not a wall you might accidentally make thin.
REACH = 2048
STEP = 16

#: Sample the wall at these fractions of its length. A wall is thin where it is
#: thin, and only sampling the midpoint misses a wedge.
SAMPLES = (0.25, 0.5, 0.75)

#: Walls shorter than this are chamfers and joins, not surfaces a player reads.
MIN_WALL_LENGTH = 128

#: How much vertical overlap makes two sectors neighbours rather than stacked.
#: A standing body: if a player in one could stand at heights the other also
#: spans, the mass between them is a wall they can both see.
COEXIST = PLAYER_PROFILES["blood"].standing_height

CELL = 1024


def sector_loops(disk: Any, sector: int) -> list[list[tuple[int, int]]]:
    """Every closed loop of a sector's boundary, outer first."""
    fields = disk.sectors[sector].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    seen: set[int] = set()
    loops = []
    for first in range(start, start + count):
        if first in seen:
            continue
        loop = []
        wall = first
        while wall not in seen:
            seen.add(wall)
            here = disk.walls[wall].fields
            loop.append((int(here["x"]), int(here["y"])))
            wall = int(here["point2"])
            if not start <= wall < start + count:
                break
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def index_sectors(disk: Any, playable: frozenset[int]) -> tuple[dict, dict]:
    """Bucket playable sectors by grid cell, and keep their loops."""
    loops = {s: sector_loops(disk, s) for s in playable}
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for sector, sector_loop in loops.items():
        if not sector_loop:
            continue
        xs = [p[0] for loop in sector_loop for p in loop]
        ys = [p[1] for loop in sector_loop for p in loop]
        for cx in range(min(xs) // CELL, max(xs) // CELL + 1):
            for cy in range(min(ys) // CELL, max(ys) // CELL + 1):
                grid[(cx, cy)].append(sector)
    return loops, grid


def sector_at(point: tuple[int, int], loops: dict, grid: dict) -> int | None:
    """The smallest playable sector holding this point, or None."""
    found = []
    for sector in grid.get((point[0] // CELL, point[1] // CELL), ()):
        sector_loop = loops[sector]
        if not sector_loop:
            continue
        if point_in_loop(point, sector_loop[0]) <= 0:
            continue
        # A point inside a hole is not inside the sector.
        if any(point_in_loop(point, hole) > 0 for hole in sector_loop[1:]):
            continue
        area = abs(sum(
            sector_loop[0][i][0] * sector_loop[0][(i + 1) % len(sector_loop[0])][1]
            - sector_loop[0][(i + 1) % len(sector_loop[0])][0] * sector_loop[0][i][1]
            for i in range(len(sector_loop[0]))))
        found.append((area, sector))
    if not found:
        return None
    return min(found)[1]


def observe(name: str, disk: Any) -> list[dict[str, Any]]:
    playable = design_sectors(disk)
    if not playable:
        return []
    loops, grid = index_sectors(disk, playable)

    owner: dict[int, int] = {}
    for sector in playable:
        fields = disk.sectors[sector].fields
        start = int(fields["wall_ptr"])
        for wall in range(start, start + int(fields["wall_count"])):
            owner[wall] = sector

    span = {}
    for sector in playable:
        fields = disk.sectors[sector].fields
        span[sector] = (int(fields["ceiling_z"]), int(fields["floor_z"]))

    def coexist(a: int, b: int) -> bool:
        top = max(span[a][0], span[b][0])
        bottom = min(span[a][1], span[b][1])
        return bottom - top >= COEXIST

    out = []
    for wall_id, wall in enumerate(disk.walls):
        fields = wall.fields
        if int(fields["next_sector"]) >= 0:
            continue                       # an opening, not a mass
        mine = owner.get(wall_id)
        if mine is None:
            continue
        nxt = disk.walls[int(fields["point2"])].fields
        ax, ay = int(fields["x"]), int(fields["y"])
        bx, by = int(nxt["x"]), int(nxt["y"])
        length = math.hypot(bx - ax, by - ay)
        if length < MIN_WALL_LENGTH:
            continue
        # Outward normal. Build's winding puts the interior on one side; find
        # which by probing a single step and seeing which one leaves the sector.
        nx, ny = (by - ay) / length, -(bx - ax) / length
        midx, midy = (ax + bx) / 2.0, (ay + by) / 2.0
        probe = (int(round(midx + nx * STEP)), int(round(midy + ny * STEP)))
        if sector_at(probe, loops, grid) == mine:
            nx, ny = -nx, -ny

        for fraction in SAMPLES:
            px = ax + (bx - ax) * fraction
            py = ay + (by - ay) * fraction
            hit = None
            for distance in range(STEP, REACH + 1, STEP):
                point = (int(round(px + nx * distance)), int(round(py + ny * distance)))
                found = sector_at(point, loops, grid)
                if found is not None and found != mine and coexist(mine, found):
                    hit = (distance, found)
                    break
            if hit is None:
                continue
            out.append({
                "map": name,
                "wall": wall_id,
                "sector": mine,
                "other": hit[1],
                "thickness": hit[0],
                "thickness_player_widths": round(hit[0] / PLAYER_WIDTH, 3),
            })
    return out


def band(values: list[float], digits: int = 2) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}

    def at(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))]

    return {
        "min": round(ordered[0], digits),
        "p01": round(at(0.01), digits),
        "p05": round(at(0.05), digits),
        "q1": round(at(0.25), digits),
        "median": round(statistics.median(ordered), digits),
        "q3": round(at(0.75), digits),
        "max": round(ordered[-1], digits),
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    thick = [r["thickness"] for r in rows]
    histogram = Counter(min(r["thickness"], 512) // 32 * 32 for r in rows)
    # The thinnest each map is willing to go, which is the number the grammar
    # wants: one outlier in one map should not set the floor for every level.
    per_map: dict[str, int] = {}
    for row in rows:
        key = row["map"]
        if key not in per_map or row["thickness"] < per_map[key]:
            per_map[key] = row["thickness"]
    return {
        "probes": len(rows),
        "thickness": band(thick, 0),
        "thickness_player_widths": band([r["thickness_player_widths"] for r in rows]),
        "thinnest_per_map": band([float(v) for v in per_map.values()], 0),
        "histogram_to_512": {str(k): histogram[k] for k in sorted(histogram)},
        "share_under": {
            str(cut): round(sum(1 for t in thick if t < cut) / max(1, len(thick)), 5)
            for cut in (64, 128, 192, 256, 384, 512)
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    seen = 0
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name):
            continue
        try:
            rows.extend(observe(name, read_map(path)))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
            continue
        seen += 1
        print("  %s: %d probes" % (name, len(rows)), end="\r")

    summary = summarise(rows)
    document = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "maps": seen,
        "summary": summary,
        "method": (
            "step outward from every solid wall of a playable sector along its "
            "own normal, in %d-unit steps to %d, and record the distance at "
            "which another playable sector begins. Two-sided walls are openings "
            "and are excluded; a normal that re-enters its own sector is one "
            "space and is excluded." % (STEP, REACH)
        ),
        "reading_guide": [
            "thickness is in Build units; one body width is %d" % PLAYER_WIDTH,
            "thinnest_per_map is the floor each map allowed itself, which is the "
            "number a minimum should be derived from -- a single outlier in one "
            "map is not a licence for every level",
            "a band is what the campaign did, never what a level must do",
        ],
    }

    s = summary
    print("%d maps, %d probes                       " % (seen, s["probes"]))
    print()
    print("wall thickness, Build units : %s" % s["thickness"])
    print("            in body widths  : %s" % s["thickness_player_widths"])
    print("thinnest wall in each map   : %s" % s["thinnest_per_map"])
    print()
    print("share of walls thinner than:")
    for cut, share in s["share_under"].items():
        print("  %4s units (%.2f body widths): %6.3f%%"
              % (cut, int(cut) / PLAYER_WIDTH, 100 * share))
    print()
    print("histogram to 512 units, in 32s:")
    for key, count in s["histogram_to_512"].items():
        print("  %4s %s %d" % (key, "#" * min(60, count // 40), count))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
        print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
