"""How Blood builds the thing you get shot from.

Counting overlooks said the candidate has one where comparable maps have dozens.
This measures the *recipe*, so one can be built rather than admired: how high
the walk stands, how deep it is, how much of the room's edge it takes, whether
its lip stops you walking off, what stands on it, and how you get up there.

An overlook here is a walkable sector whose floor stands between half a body and
three bodies above a space of at least five square humans, sharing a boundary
with it. That band is not arbitrary -- across E6M6 every raised neighbour of a
big space falls inside it, and none is more than eight humans up.

.. code-block:: bash

    python -m tools.mine_overlooks --only E6M6 E6M5 E6M7 E3M8 E1M1 BB2
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

SCHEMA = "llmapper.blood-overlooks"
SCHEMA_VERSION = 1

PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height
PLAYER_WIDTH = PLAYER_PROFILES["blood"].body_width
HUMAN_PLAN = PLAYER_HEIGHT / 16.0

BIG_AREA = 5.0
RISE_LOW, RISE_HIGH = 0.5, 3.0

CSTAT_BLOCK = 1


def area_of(disk: Any, sector: int) -> float:
    fields = disk.sectors[sector].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    total = 0
    for wall in range(start, start + count):
        here = disk.walls[wall].fields
        there = disk.walls[int(here["point2"])].fields
        total += int(here["x"]) * int(there["y"]) - int(there["x"]) * int(here["y"])
    return abs(total) / 2.0 / (HUMAN_PLAN * HUMAN_PLAN)


def perimeter(disk: Any, sector: int) -> float:
    fields = disk.sectors[sector].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    total = 0.0
    for wall in range(start, start + count):
        here = disk.walls[wall].fields
        there = disk.walls[int(here["point2"])].fields
        total += math.hypot(int(there["x"]) - int(here["x"]),
                            int(there["y"]) - int(here["y"]))
    return total


def shared_edge(disk: Any, sector: int, other: int) -> tuple[float, int, int]:
    """Length of the boundary, how much of it blocks, and how many walls it is."""
    fields = disk.sectors[sector].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    length = 0.0
    blocked = 0.0
    walls = 0
    for wall in range(start, start + count):
        here = disk.walls[wall].fields
        if int(here["next_sector"]) != other:
            continue
        there = disk.walls[int(here["point2"])].fields
        run = math.hypot(int(there["x"]) - int(here["x"]),
                         int(there["y"]) - int(here["y"]))
        length += run
        walls += 1
        if int(here["cstat"]) & CSTAT_BLOCK:
            blocked += run
    return length, (1 if blocked > length * 0.5 else 0), walls


def observe(name: str, disk: Any) -> list[dict[str, Any]]:
    play = design_sectors(disk)
    if not play:
        return []
    graph = portal_graph(disk)
    areas = {s: area_of(disk, s) for s in play}
    sprites: Counter = Counter()
    dudes: Counter = Counter()
    for sprite in disk.sprites:
        if int(sprite.fields["cstat"]) & 0x8000:
            continue
        sector = int(sprite.fields["sector"])
        sprites[sector] += 1
        if 200 <= int(sprite.fields["type"]) <= 260:
            dudes[sector] += 1

    out = []
    for space in play:
        if areas[space] < BIG_AREA:
            continue
        base = int(disk.sectors[space].fields["floor_z"])
        for walk in graph.get(space, ()):
            if walk not in play:
                continue
            walk_fields = disk.sectors[walk].fields
            rise = (base - int(walk_fields["floor_z"])) / PLAYER_HEIGHT
            if not RISE_LOW <= rise <= RISE_HIGH:
                continue
            head = (int(walk_fields["floor_z"])
                    - int(walk_fields["ceiling_z"])) / PLAYER_HEIGHT
            if head < 1.0:
                continue                      # not somewhere a body stands
            edge, blocked, edge_walls = shared_edge(disk, walk, space)
            if edge <= 0:
                continue
            # A walk's depth: its area over the edge it presents. Crude, and
            # right for the long thin sectors these actually are.
            depth = (areas[walk] * HUMAN_PLAN * HUMAN_PLAN) / edge
            ways = [x for x in graph.get(walk, ()) if x in play and x != space]
            out.append({
                "map": name,
                "space": space,
                "walk": walk,
                "rise_humans": round(rise, 2),
                "head_humans": round(head, 2),
                "walk_area_sq_human": round(areas[walk], 2),
                "edge_body_widths": round(edge / PLAYER_WIDTH, 2),
                "edge_share_of_space_perimeter": round(
                    edge / max(1.0, perimeter(disk, space)), 3),
                "depth_body_widths": round(depth / PLAYER_WIDTH, 2),
                "lip_blocks": bool(blocked),
                "edge_walls": edge_walls,
                "other_ways_off": len(ways),
                "sprites_on_it": sprites.get(walk, 0),
                "dudes_on_it": dudes.get(walk, 0),
                "open_to_sky": bool(int(walk_fields["ceiling_stat"]) & 1),
            })
    return out


def band(values: list[float], digits: int = 2) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}

    def at(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))]

    return {"min": round(ordered[0], digits), "q1": round(at(0.25), digits),
            "median": round(statistics.median(ordered), digits),
            "q3": round(at(0.75), digits), "p95": round(at(0.95), digits),
            "max": round(ordered[-1], digits)}


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return {
        "overlooks": len(rows),
        "rise_humans": band([r["rise_humans"] for r in rows]),
        "head_humans": band([r["head_humans"] for r in rows]),
        "depth_body_widths": band([r["depth_body_widths"] for r in rows]),
        "edge_body_widths": band([r["edge_body_widths"] for r in rows]),
        "edge_share_of_space_perimeter": band(
            [r["edge_share_of_space_perimeter"] for r in rows], 3),
        "lip_blocks": round(sum(1 for r in rows if r["lip_blocks"]) / len(rows), 3),
        "open_to_sky": round(sum(1 for r in rows if r["open_to_sky"]) / len(rows), 3),
        "has_another_way_off": round(
            sum(1 for r in rows if r["other_ways_off"]) / len(rows), 3),
        "carries_a_dude": round(
            sum(1 for r in rows if r["dudes_on_it"]) / len(rows), 3),
        "sprites_per_overlook": round(
            sum(r["sprites_on_it"] for r in rows) / len(rows), 2),
        "edge_walls": band([float(r["edge_walls"]) for r in rows], 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--against")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    paths: dict[str, str] = {}
    for pattern in ("*.MAP", "*.map"):
        for path in glob.glob(str(pathlib.Path(args.maps) / pattern)):
            paths.setdefault(pathlib.Path(path).stem.upper(), path)
    if args.only:
        wanted = {n.upper() for n in args.only}
        paths = {k: v for k, v in paths.items() if k in wanted}
    if args.against:
        paths["CANDIDATE"] = args.against

    rows: list[dict[str, Any]] = []
    per_map: dict[str, list] = {}
    for name in sorted(paths):
        try:
            found = observe(name, read_map(paths[name]))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
            continue
        per_map[name] = found
        if name != "CANDIDATE":
            rows.extend(found)

    reference = summarise(rows)
    print("reference: %d overlooks over %d maps"
          % (reference.get("overlooks", 0), len(per_map) - (1 if args.against else 0)))
    print()
    for key in ("rise_humans", "head_humans", "depth_body_widths",
                "edge_body_widths", "edge_share_of_space_perimeter"):
        print("  %-30s %s" % (key, reference.get(key)))
    print()
    for key in ("lip_blocks", "open_to_sky", "has_another_way_off",
                "carries_a_dude"):
        print("  %-30s %.0f%%" % (key, 100 * reference.get(key, 0)))
    print("  %-30s %.2f" % ("sprites_per_overlook",
                            reference.get("sprites_per_overlook", 0)))
    print()
    print("%-11s %s" % ("map", "overlooks"))
    for name in sorted(per_map):
        print("  %-9s %d" % (name, len(per_map[name])))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "unit": "standing humans (%d z), body widths (%d)"
                    % (PLAYER_HEIGHT, PLAYER_WIDTH),
            "definition": "a walkable sector whose floor stands %.1f-%.1f humans "
                          "above a space of at least %.0f square humans, sharing "
                          "a boundary with it" % (RISE_LOW, RISE_HIGH, BIG_AREA),
            "reference": reference,
            "per_map": {k: len(v) for k, v in per_map.items()},
            "rows": rows,
        }, indent=1) + "\n", encoding="utf-8")
        print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
