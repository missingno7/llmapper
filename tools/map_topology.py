#!/usr/bin/env python3
"""Ground-truth sector topology for a Blood map, for bot run analysis only.

This is an offline analysis aid.  The bot itself never reads it; it exists so
a run can be compared against what the level actually offers.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bloodmap.format import read_map  # noqa: E402


def build(path):
    disk = read_map(path)
    walls = disk.walls
    sectors = disk.sectors
    neighbours = collections.defaultdict(set)
    for index, sector in enumerate(sectors):
        first = sector.fields["wall_ptr"]
        for offset in range(sector.fields["wall_count"]):
            wall = walls[first + offset]
            nxt = wall.fields["next_sector"]
            if nxt >= 0:
                neighbours[index].add(nxt)
    return disk, neighbours


def reachable_from(neighbours, start, count):
    seen, queue, depth = {start: 0}, collections.deque([start]), 0
    while queue:
        current = queue.popleft()
        for nxt in neighbours.get(current, ()):
            if nxt not in seen:
                seen[nxt] = seen[current] + 1
                queue.append(nxt)
    return seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("map")
    parser.add_argument("--from-sector", type=int, default=None)
    parser.add_argument("--visited", default="", help="comma separated visited sector ids")
    args = parser.parse_args()
    disk, neighbours = build(args.map)
    count = len(disk.sectors)
    visited = {int(v) for v in args.visited.split(",") if v.strip()}
    out = {"sectors": count, "walls": len(disk.walls)}
    if args.from_sector is not None:
        seen = reachable_from(neighbours, args.from_sector, count)
        out["geometrically_connected"] = len(seen)
        out["max_hop_depth"] = max(seen.values()) if seen else 0
    if visited:
        fringe = collections.Counter()
        for sector in visited:
            for nxt in neighbours.get(sector, ()):
                if nxt not in visited:
                    fringe[sector] += 1
        out["visited"] = len(visited)
        out["frontier_sectors_adjacent_to_visited"] = sum(fringe.values())
        out["visited_with_open_neighbours"] = dict(fringe)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
