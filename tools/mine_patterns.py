"""Compositional patterns, counted -- the things that make a room look built.

This is the follow-on from `mine_texture_fit` and the E3M8 comparison. Those
answered "how much detail"; this asks "what shape is the detail". Each pattern
here was first seen in a rendered frame from a verified pose, then defined so it
could be counted, so that "E6M6 has parapets" becomes a number the candidate can
be held to.

The patterns
------------

``overlook``   a walkable neighbour whose floor stands half a body to three
               bodies above a large space. The parapet a cultist shoots at you
               from, and the single cheapest way to make a courtyard feel built
               rather than fenced.
``ledge``      a small sector hugging a wall, its floor a little above the room.
               Plinths, benches, altar steps, the base course of a column.
``arch``       a doorway sector with more than four corners: the head is shaped
               rather than square. Gothic openings are built this way because
               Build cannot curve a wall top -- the shape is in the plan.
``pit``        a walkable neighbour *below* a large space, deep enough to be a
               feature and shallow enough to climb out of.
``silhouette`` distinct roofline heights around one open-air sector. A courtyard
               whose enclosing walls all stop at the same height reads as a box;
               Blood's read as buildings.

Every one is measured only over playable sectors, in standing humans.

.. code-block:: bash

    python -m tools.mine_patterns --maps maps/blood --against MAP
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import pathlib
import statistics
from collections import Counter
from typing import Any

from bloodmap.format import read_map
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.reachability import design_sectors, portal_graph

SCHEMA = "llmapper.blood-patterns"
SCHEMA_VERSION = 1

PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height
#: The same height expressed horizontally, because Build's z is 16x the plan
#: unit and comparing the two without it makes a slot look square.
HUMAN_PLAN = PLAYER_HEIGHT / 16.0

#: A space big enough that what surrounds it is composition rather than fit.
BIG_AREA = 5.0

#: A step you can see over but not walk up: the parapet band.
OVERLOOK_LOW, OVERLOOK_HIGH = 0.5, 3.0

#: A plinth is small in plan and shallow in rise.
LEDGE_AREA = 0.6
LEDGE_LOW, LEDGE_HIGH = 0.08, 0.6

#: Deep enough to read as a pit, shallow enough not to be a different storey.
PIT_LOW, PIT_HIGH = 0.5, 4.0


def area_of(disk: Any, sector: int) -> float:
    fields = disk.sectors[sector].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    total = 0
    for wall in range(start, start + count):
        here = disk.walls[wall].fields
        there = disk.walls[int(here["point2"])].fields
        total += int(here["x"]) * int(there["y"]) - int(there["x"]) * int(here["y"])
    return abs(total) / 2.0 / (HUMAN_PLAN * HUMAN_PLAN)


def clear_height(disk: Any, sector: int) -> float:
    fields = disk.sectors[sector].fields
    return (int(fields["floor_z"]) - int(fields["ceiling_z"])) / PLAYER_HEIGHT


def solid_walls(disk: Any, sector: int) -> int:
    fields = disk.sectors[sector].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    return sum(1 for w in range(start, start + count)
               if int(disk.walls[w].fields["next_sector"]) < 0)


def observe(name: str, disk: Any) -> dict[str, Any]:
    play = design_sectors(disk)
    if not play:
        return {}
    graph = portal_graph(disk)
    areas = {s: area_of(disk, s) for s in play}
    floors = {s: int(disk.sectors[s].fields["floor_z"]) for s in play}
    heights = {s: clear_height(disk, s) for s in play}

    big = [s for s in play if areas[s] >= BIG_AREA]
    overlooked = 0
    overlooks = 0
    pits = 0
    pitted = 0
    for sector in big:
        found = above = below = 0
        for other in graph.get(sector, ()):
            if other not in play:
                continue
            rise = (floors[sector] - floors[other]) / PLAYER_HEIGHT
            if OVERLOOK_LOW <= rise <= OVERLOOK_HIGH and heights[other] >= 1.0:
                above += 1
            if PIT_LOW <= -rise <= PIT_HIGH and heights[other] >= 1.0:
                below += 1
        overlooks += above
        pits += below
        overlooked += 1 if above else 0
        pitted += 1 if below else 0

    ledges = 0
    for sector in play:
        if areas[sector] > LEDGE_AREA or solid_walls(disk, sector) == 0:
            continue
        for other in graph.get(sector, ()):
            if other not in play or areas[other] < BIG_AREA:
                continue
            rise = (floors[other] - floors[sector]) / PLAYER_HEIGHT
            if LEDGE_LOW <= rise <= LEDGE_HIGH:
                ledges += 1
                break

    arches = 0
    doorways = 0
    for sector in play:
        neighbours = [x for x in graph.get(sector, ()) if x in play]
        if len(neighbours) != 2 or areas[sector] >= BIG_AREA:
            continue
        doorways += 1
        if int(disk.sectors[sector].fields["wall_count"]) > 4:
            arches += 1

    # Rooflines around open-air space: how many distinct ceiling heights the
    # sectors bounding one outdoor sector stop at.
    silhouettes = []
    for sector in play:
        if not int(disk.sectors[sector].fields["ceiling_stat"]) & 1:
            continue
        tops = set()
        for other in graph.get(sector, ()):
            if other in play:
                tops.add(int(disk.sectors[other].fields["ceiling_z"]) // 2048)
        if tops:
            silhouettes.append(len(tops))

    return {
        "map": name,
        "playable": len(play),
        "big_spaces": len(big),
        "overlook": {
            "spaces_with_one": overlooked,
            "share_of_big_spaces": round(overlooked / max(1, len(big)), 3),
            "per_big_space": round(overlooks / max(1, len(big)), 2),
        },
        "pit": {
            "spaces_with_one": pitted,
            "share_of_big_spaces": round(pitted / max(1, len(big)), 3),
        },
        "ledge": {
            "count": ledges,
            "per_100_playable": round(100 * ledges / len(play), 1),
        },
        "arch": {
            "doorways": doorways,
            "shaped_heads": arches,
            "share": round(arches / max(1, doorways), 3),
        },
        "silhouette": {
            "open_sectors": len(silhouettes),
            "median_distinct_rooflines": (round(statistics.median(silhouettes), 1)
                                          if silhouettes else 0.0),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--only", nargs="*", help="map stems to include")
    parser.add_argument("--against", help="an extra map to profile alongside")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    paths: dict[str, str] = {}
    for pattern in ("*.MAP", "*.map"):
        for path in glob.glob(str(pathlib.Path(args.maps) / pattern)):
            paths.setdefault(pathlib.Path(path).stem.upper(), path)
    if args.only:
        wanted = {name.upper() for name in args.only}
        paths = {k: v for k, v in paths.items() if k in wanted}
    if args.against:
        paths["CANDIDATE"] = args.against

    rows = []
    for name in sorted(paths):
        try:
            row = observe(name, read_map(paths[name]))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
            continue
        if row:
            rows.append(row)

    print("%-11s %6s %6s  %-18s %-10s %-12s %-10s"
          % ("map", "play", "big", "overlooked big spaces", "ledges", "shaped heads",
             "rooflines"))
    for row in rows:
        print("%-11s %6d %6d  %5.0f%% (%.2f each)   %5.1f/100  %5.0f%% of %-4d %6.1f"
              % (row["map"], row["playable"], row["big_spaces"],
                 100 * row["overlook"]["share_of_big_spaces"],
                 row["overlook"]["per_big_space"],
                 row["ledge"]["per_100_playable"],
                 100 * row["arch"]["share"], row["arch"]["doorways"],
                 row["silhouette"]["median_distinct_rooflines"]))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "unit": "standing humans (%d z); plan distances divided by %d"
                    % (PLAYER_HEIGHT, int(HUMAN_PLAN)),
            "definitions": {
                "overlook": "walkable neighbour %.1f-%.1f humans above a space of "
                            "at least %.0f square humans" % (OVERLOOK_LOW, OVERLOOK_HIGH, BIG_AREA),
                "ledge": "sector under %.1f square humans, touching a solid wall, "
                         "%.2f-%.2f humans above a big neighbour" % (LEDGE_AREA, LEDGE_LOW, LEDGE_HIGH),
                "arch": "a two-neighbour doorway sector with more than four corners",
                "pit": "walkable neighbour %.1f-%.1f humans below a big space" % (PIT_LOW, PIT_HIGH),
                "silhouette": "distinct ceiling heights, to the nearest 2048 z, "
                              "among the sectors bounding one open-air sector",
            },
            "maps": rows,
        }, indent=1) + "\n", encoding="utf-8")
        print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
