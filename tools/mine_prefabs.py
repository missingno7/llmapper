"""What a Blood level is made of, below the size of a room.

`mine_assemblies` mines machinery. This mines architecture, and it exists
because of one measurement: **E1M1 is not 155 rooms.** 68% of its sectors are
under 20 player widths squared and 40 are under 4. It is about 46 real spaces
and about 100 small ones, and the small ones are the level.

They are also not decoration. **A third of the campaign's 9,494 small sectors
close a triangle** -- their neighbours already touch each other, so the small
sector is an alternative way round rather than a pocket hanging off a room. The
campaign median is 60 such sectors per map. This project's level had 5 of 38,
which is why its loop count and its sector count were short by the same factor:
they were the same shortfall counted twice.

.. code-block:: bash

    python -m tools.mine_prefabs -o knowledge/blood/design/prefabs-v1.json
    python -m tools.mine_prefabs --against projects/.../candidate-v5.MAP

Each small sector is classified by what it does -- which is a question about its
neighbours, not about its shape -- and each class is then measured, so a
constructor can be parameterised from evidence instead of taste.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.format import read_map
from bloodmap.reachability import analyze_reachability, design_sectors

SCHEMA = "llmapper.blood-prefab-shapes"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

PLAYER_WIDTH = 384.0

from bloodmap.player_space import PLAYER_PROFILES

#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

#: Above this a sector is a room and is somebody's destination. Below it, the
#: sector is something the player passes through, stands in briefly, or looks
#: at -- and that is the population this mines.
SMALL_AREA = 20.0

#: A height difference smaller than this is a build tolerance, not a step.
STEP_TOLERANCE = 256


def area_of(disk: Any, index: int) -> float:
    fields = disk.sectors[index].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    total = 0
    for wall in range(start, start + count):
        x1, y1 = int(disk.walls[wall].fields["x"]), int(disk.walls[wall].fields["y"])
        nxt = int(disk.walls[wall].fields["point2"])
        x2, y2 = int(disk.walls[nxt].fields["x"]), int(disk.walls[nxt].fields["y"])
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0 / (PLAYER_WIDTH * PLAYER_WIDTH)


def classify(disk: Any, index: int, graph: dict[int, set[int]],
             playable: set[int]) -> str | None:
    """What this small sector is for, from how it meets its neighbours."""
    neighbours = [n for n in graph.get(index, ()) if n in playable]
    if not neighbours:
        return None
    fields = disk.sectors[index].fields
    floor_z, ceiling_z = int(fields["floor_z"]), int(fields["ceiling_z"])
    floor_steps = [floor_z - int(disk.sectors[n].fields["floor_z"]) for n in neighbours]
    ceiling_steps = [ceiling_z - int(disk.sectors[n].fields["ceiling_z"]) for n in neighbours]
    floor_differs = any(abs(v) > STEP_TOLERANCE for v in floor_steps)
    ceiling_differs = any(abs(v) > STEP_TOLERANCE for v in ceiling_steps)

    # Does it close a cycle? That is the property that makes a small sector part
    # of the level's routing rather than an ornament on it.
    closes = any(
        b in graph.get(a, ())
        for i, a in enumerate(neighbours) for b in neighbours[i + 1:]
    )

    if len(neighbours) == 1:
        return "alcove"
    if closes:
        return "bay" if len(neighbours) == 2 else "junction"
    if len(neighbours) == 2 and floor_differs and not ceiling_differs:
        return "tread"
    if len(neighbours) == 2 and ceiling_differs and not floor_differs:
        return "arch"
    if len(neighbours) == 2:
        return "link"
    return "branch"


def observe(path: str) -> list[dict[str, Any]]:
    disk = read_map(path)
    playable = set(design_sectors(disk))
    graph = analyze_reachability(disk).graph
    rows: list[dict[str, Any]] = []
    for index in sorted(playable):
        size = area_of(disk, index)
        if size >= SMALL_AREA:
            continue
        kind = classify(disk, index, graph, playable)
        if kind is None:
            continue
        fields = disk.sectors[index].fields
        neighbours = [n for n in graph.get(index, ()) if n in playable]
        floor_z, ceiling_z = int(fields["floor_z"]), int(fields["ceiling_z"])
        rows.append({
            "kind": kind,
            "area": round(size, 2),
            "walls": int(fields["wall_count"]),
            "degree": len(neighbours),
            "height": round(abs(floor_z - ceiling_z) / PLAYER_HEIGHT, 2),
            "floor_step": round(max(
                (abs(floor_z - int(disk.sectors[n].fields["floor_z"])) for n in neighbours),
                default=0) / PLAYER_HEIGHT, 2),
            "ceiling_step": round(max(
                (abs(ceiling_z - int(disk.sectors[n].fields["ceiling_z"])) for n in neighbours),
                default=0) / PLAYER_HEIGHT, 2),
        })
    return rows


def _band(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}
    return {
        "q1": round(ordered[len(ordered) // 4], 2),
        "median": round(statistics.median(ordered), 2),
        "q3": round(ordered[3 * len(ordered) // 4], 2),
    }


def build(per_map: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    everything = [row for rows in per_map.values() for row in rows]
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in everything:
        by_kind[row["kind"]].append(row)

    counts_per_map: dict[str, list[int]] = defaultdict(list)
    for rows in per_map.values():
        seen = Counter(row["kind"] for row in rows)
        for kind in by_kind:
            counts_per_map[kind].append(seen.get(kind, 0))

    kinds = {}
    for kind, rows in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
        kinds[kind] = {
            "instances": len(rows),
            "share_of_small": round(len(rows) / len(everything), 3),
            "per_map": _band([float(v) for v in counts_per_map[kind]]),
            "area": _band([r["area"] for r in rows]),
            "walls": _band([float(r["walls"]) for r in rows]),
            "height": _band([r["height"] for r in rows]),
            "floor_step": _band([r["floor_step"] for r in rows]),
            "ceiling_step": _band([r["ceiling_step"] for r in rows]),
        }
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "maps": len(per_map),
        "small_sectors": len(everything),
        "small_area_threshold": SMALL_AREA,
        "kinds": kinds,
        "reading_guide": [
            "a kind is what the sector does for its neighbours, not what shape "
            "it is; the same rectangle is an alcove, a bay or a tread depending "
            "on what it opens onto",
            "'bay' and 'junction' are the ones that close a cycle -- together a "
            "third of every small sector in the campaign",
            "a band is what the campaign did, never what a level must do",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--against")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    per_map: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name) or name in per_map:
            continue
        try:
            per_map[name] = observe(path)
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
    if not per_map:
        print("no campaign maps")
        return 1
    document = build(per_map)

    print("%d small sectors across %d maps" % (
        document["small_sectors"], document["maps"]))
    print("%-10s %7s %7s  %-22s %-22s" % (
        "kind", "count", "share", "per map (q1/med/q3)", "area (q1/med/q3)"))
    for kind, spec in document["kinds"].items():
        pm, ar = spec["per_map"], spec["area"]
        print("%-10s %7d %6.0f%%  %6s %6s %6s      %6s %6s %6s" % (
            kind, spec["instances"], 100 * spec["share_of_small"],
            pm["q1"], pm["median"], pm["q3"], ar["q1"], ar["median"], ar["q3"]))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")

    if args.against:
        mine = Counter(row["kind"] for row in observe(args.against))
        print()
        print("%-10s %8s %10s   %s" % ("kind", "level", "campaign", ""))
        for kind, spec in document["kinds"].items():
            pm = spec["per_map"]
            got = mine.get(kind, 0)
            inside = pm["q1"] <= got <= pm["q3"]
            print("%-10s %8d %10s   %s" % (
                kind, got, "%g..%g" % (pm["q1"], pm["q3"]), "in" if inside else "SHORT"
                if got < pm["q1"] else "over"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
