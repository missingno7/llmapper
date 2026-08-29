"""What the campaign does when two pieces of space share the same ground.

.. code-block:: bash

    python -m tools.mine_layers --maps maps/blood -o knowledge/blood/design/layers-v1.json

Build's sector is a 2D polygon with one floor and one ceiling, so a level that
wants space above space has to work around the format. Three ways exist, and
this measures how often the campaign reaches for each and -- for the one that is
genuinely dangerous, plan overlap -- what it keeps true whenever it does.

The danger is not abstract. Blood runs the engine in ``ENGINE_19960925``
(blood/src/blood.cpp:1890), which routes every move through ``clipmove_compat``
(build/src/clip.cpp:1112). That function resolves the mover's sector by walking
``clipsectorlist`` -- the portal BFS the clip step gathered, seeded at the
mover's current sector (clip.cpp:1508) and grown across two-sided walls
(clip.cpp:1688) -- and taking the **first** sector in it that contains the point
*in plan alone*. Z is not consulted on that path at all. Only when nothing in
the clip list contains the point does it fall through to a reverse linear scan
over every sector, and only *that* scan compares the mover's z against each
sector's ceiling and floor.

So the two protections are not interchangeable, and they are not ranked the way
they are usually stated: portal separation is what keeps two overlapping sectors
out of the same clip list, and z separation is what saves the cold lookup once
they are. This file measures both.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import pathlib
import re
from collections import deque
from typing import Any

from bloodmap.format import read_map
from bloodmap.planar_geom import polygon_relation, z_interval, z_relation

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

#: cstat bits 4-5 select how a sprite is drawn; 32 is "floor-aligned".
CSTAT_ALIGNMENT = 48
CSTAT_FLOOR_ALIGNED = 32
CSTAT_BLOCKING = 1

#: See `bloodmap.layers`. Two overlapping sectors can only be transposed if the
#: portal walk can reach one from the other at the depth the mover is already at
#: -- two hops -- and if that walk stays inside the clip box, which is a
#: distance and not a hop count.
CONFUSABLE_HOPS = 2
CLIP_RADIUS = 1024 + (0x30 << 2) + 16 + 8 + 1024

#: The three relations that mean two footprints genuinely share ground.
OVERLAPPING = {
    "partial_area_overlap",
    "full_containment_a_in_b",
    "full_containment_b_in_a",
}


def sector_loops(disk: Any, sector_id: int) -> list[list[tuple[int, int]]]:
    """Split one sector's wall run into its closed loops.

    A Build sector owns a contiguous run of walls holding an outer loop and then
    one loop per hole; ``point2`` is what closes each of them.
    """
    fields = disk.sectors[sector_id].fields
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    last = min(first + count, len(disk.walls))
    loops: list[list[tuple[int, int]]] = []
    seen: set[int] = set()
    cursor = first
    while cursor < last:
        if cursor in seen:
            cursor += 1
            continue
        loop: list[tuple[int, int]] = []
        walk = cursor
        while walk not in seen and first <= walk < last:
            seen.add(walk)
            wall = disk.walls[walk].fields
            loop.append((int(wall["x"]), int(wall["y"])))
            walk = int(wall["point2"])
        if len(loop) >= 3:
            loops.append(loop)
        cursor += 1
    return loops


def bbox(loops: list[list[tuple[int, int]]]) -> tuple[int, int, int, int]:
    xs = [p[0] for loop in loops for p in loop]
    ys = [p[1] for loop in loops for p in loop]
    return (min(xs), min(ys), max(xs), max(ys))


def boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def portal_graph(disk: Any) -> dict[int, set[int]]:
    graph: dict[int, set[int]] = {i: set() for i in range(len(disk.sectors))}
    for index, sector in enumerate(disk.sectors):
        first = int(sector.fields["wall_ptr"])
        count = int(sector.fields["wall_count"])
        for walk in range(first, min(first + count, len(disk.walls))):
            neighbour = int(disk.walls[walk].fields["next_sector"])
            if 0 <= neighbour < len(disk.sectors) and neighbour != index:
                graph[index].add(neighbour)
                graph[neighbour].add(index)
    return graph


def hops(graph: dict[int, set[int]], start: int, goal: int,
         limit: int = 24) -> int | None:
    """Shortest portal-graph distance, or None if unjoined or further than `limit`."""
    if start == goal:
        return 0
    frontier = deque([(start, 0)])
    seen = {start}
    while frontier:
        node, distance = frontier.popleft()
        if distance >= limit:
            continue
        for next_node in graph[node]:
            if next_node == goal:
                return distance + 1
            if next_node not in seen:
                seen.add(next_node)
                frontier.append((next_node, distance + 1))
    return None


def boxes_of(disk: Any, loops: list) -> list:
    return [bbox(shape) if shape else None for shape in loops]


def within_clip_box(box, centre) -> bool:
    if box is None:
        return False
    return not (box[0] > centre[0] + CLIP_RADIUS or box[2] < centre[0] - CLIP_RADIUS
                or box[1] > centre[1] + CLIP_RADIUS or box[3] < centre[1] - CLIP_RADIUS)


def one_clip_list(graph: dict[int, set[int]], boxes: list,
                  left: int, right: int) -> bool:
    """Could one mover's clip box hold a portal walk from one to the other?

    `clipmove` will not look at a wall lying wholly outside the box it fixes
    about the mover (build/src/clip.cpp:1574), so the walk that fills
    `clipsectorlist` cannot leave it.
    """
    a, b = boxes[left], boxes[right]
    low_x, high_x = max(a[0], b[0]), min(a[2], b[2])
    low_y, high_y = max(a[1], b[1]), min(a[3], b[3])
    if low_x > high_x or low_y > high_y:
        return False
    centre = ((low_x + high_x) // 2, (low_y + high_y) // 2)
    frontier, seen = deque([left]), {left}
    while frontier:
        current = frontier.popleft()
        for other in graph.get(current, ()):
            if other in seen or not within_clip_box(boxes[other], centre):
                continue
            if other == right:
                return True
            seen.add(other)
            frontier.append(other)
    return False


def quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)

    def at(fraction: float) -> float:
        position = fraction * (len(ordered) - 1)
        low, high = math.floor(position), math.ceil(position)
        if low == high:
            return float(ordered[low])
        return float(ordered[low] + (ordered[high] - ordered[low]) * (position - low))

    return {"n": len(ordered), "min": float(ordered[0]), "q1": at(0.25),
            "median": at(0.5), "q3": at(0.75), "max": float(ordered[-1])}


def stack_of(disk: Any, left: int, right: int) -> dict[str, Any]:
    """Which of the two is on top, the bands they occupy, and the slab between.

    A negative slab means the two volumes interpenetrate rather than stack, and
    zero means they meet on one plane -- which is what a room-over-room pair does
    on purpose and what nothing else should.
    """
    def band(sector: int) -> list[int]:
        fields = disk.sectors[sector].fields
        return [int(fields["ceiling_z"]), int(fields["floor_z"])]

    upper, lower = ((left, right)
                    if int(disk.sectors[left].fields["floor_z"])
                    < int(disk.sectors[right].fields["floor_z"])
                    else (right, left))
    upper_band, lower_band = band(upper), band(lower)
    return {"upper_band": upper_band, "lower_band": lower_band,
            "slab": lower_band[0] - upper_band[1]}


def layer_bands(row: dict[str, Any], grain: int = 8192) -> list[dict[str, Any]]:
    """The distinct height bands this map's overlapping sectors occupy.

    Rounded to `grain` -- a Build level does not have layers as such, so what is
    recovered here is where its floors actually cluster.
    """
    counts: dict[tuple[int, int], int] = {}
    for pair in row["pairs"]:
        for key in ("upper_band", "lower_band"):
            ceiling, floor = pair[key]
            rounded = (int(round(ceiling / grain)) * grain,
                       int(round(floor / grain)) * grain)
            counts[rounded] = counts.get(rounded, 0) + 1
    return [
        {"ceiling_z": ceiling, "floor_z": floor, "height": floor - ceiling,
         "height_bodies": round((floor - ceiling) / 16960, 2),
         "floor_bodies": round(floor / 16960, 2), "appearances": count}
        for (ceiling, floor), count in sorted(counts.items())
    ]


def measure(name: str, disk: Any) -> dict[str, Any]:
    count = len(disk.sectors)
    loops = [sector_loops(disk, i) for i in range(count)]
    boxes = boxes_of(disk, loops)
    graph = portal_graph(disk)

    pairs: list[dict[str, Any]] = []
    for left in range(count):
        if not loops[left]:
            continue
        for right in range(left + 1, count):
            if not loops[right] or not boxes_overlap(boxes[left], boxes[right]):
                continue
            kind = str(polygon_relation(loops[left], loops[right])["kind"])
            if kind not in OVERLAPPING:
                continue
            left_z = z_interval(int(disk.sectors[left].fields["ceiling_z"]),
                                int(disk.sectors[left].fields["floor_z"]))
            right_z = z_interval(int(disk.sectors[right].fields["ceiling_z"]),
                                 int(disk.sectors[right].fields["floor_z"]))
            distance = hops(graph, left, right)
            clip = (distance is not None and distance <= CONFUSABLE_HOPS
                    and one_clip_list(graph, boxes, left, right))
            pairs.append(dict(
                stack_of(disk, left, right),
                sectors=[left, right],
                kind=kind,
                z=z_relation(left_z, right_z),
                hops=distance,
                confusable=clip,
            ))

    floor_sprites = 0
    blocking_floor_sprites = 0
    for sprite in disk.sprites:
        cstat = int(sprite.fields["cstat"])
        if (cstat & CSTAT_ALIGNMENT) == CSTAT_FLOOR_ALIGNED:
            floor_sprites += 1
            if cstat & CSTAT_BLOCKING:
                blocking_floor_sprites += 1

    clashing = [p for p in pairs if p["z"] == "overlapping_vertical_volumes"]
    return {
        "map": name,
        "sectors": count,
        "overlap_pairs": len(pairs),
        "z_clashing_pairs": len(clashing),
        "confusable_pairs": len([p for p in pairs if p["confusable"]]),
        "unresolved_pairs": len([p for p in pairs if p["confusable"]
                                 and p["z"] == "overlapping_vertical_volumes"]),
        "floor_aligned_sprites": floor_sprites,
        "blocking_floor_aligned_sprites": blocking_floor_sprites,
        "pairs": pairs,
    }


def summarise(rows: list[dict[str, Any]], selector: str) -> dict[str, Any]:
    total = len(rows) or 1
    with_overlap = [r for r in rows if r["overlap_pairs"]]
    with_clash = [r for r in rows if r["z_clashing_pairs"]]
    with_platform = [r for r in rows if r["blocking_floor_aligned_sprites"]]
    all_pairs = [p for r in rows for p in r["pairs"]]
    clashing = [p for p in all_pairs if p["z"] == "overlapping_vertical_volumes"]
    joined = [float(p["hops"]) for p in all_pairs if p["hops"] is not None]
    clash_hops = [float(p["hops"]) for p in clashing if p["hops"] is not None]
    return {
        "$schema": "llmapper.blood-layers",
        "schema_version": 1,
        "corpus": {"maps": len(rows), "selector": selector},
        "reading_guide": [
            "an overlap pair is two sectors whose plan polygons genuinely share area",
            "z is how their [ceiling, floor] bands relate; only the overlapping case is ambiguous",
            "hops is the shortest portal-graph distance, null if unjoined or beyond 24",
            "a null hop count is the safest separation there is, not a missing measurement",
        ],
        "technique_usage": {
            "plan_overlap": {"maps": len(with_overlap),
                             "share": round(len(with_overlap) / total, 4)},
            "blocking_floor_aligned_sprite": {
                "maps": len(with_platform),
                "share": round(len(with_platform) / total, 4)},
            "both": {"maps": len([r for r in rows if r["overlap_pairs"]
                                  and r["blocking_floor_aligned_sprites"]])},
        },
        "z_ambiguity": {
            "maps_with_a_z_clashing_overlap": len(with_clash),
            "share_of_maps": round(len(with_clash) / total, 4),
            "pairs": len(clashing),
            "share_of_overlap_pairs": (round(len(clashing) / len(all_pairs), 4)
                                       if all_pairs else 0),
        },
        "portal_separation": {
            "all_overlap_pairs": quantiles(joined),
            "unjoined_overlap_pairs": len([p for p in all_pairs if p["hops"] is None]),
            "z_clashing_pairs_only": quantiles(clash_hops),
            "unjoined_z_clashing_pairs": len([p for p in clashing if p["hops"] is None]),
        },
        "confusability": {
            "reading_guide": [
                "confusable means <=2 portal hops apart AND inside one clip box",
                "unresolved means confusable AND the height bands intersect too;"
                " that conjunction is the only thing an author must never do",
            ],
            "confusable_pairs": len([p for p in all_pairs if p["confusable"]]),
            "share_of_overlap_pairs": (
                round(len([p for p in all_pairs if p["confusable"]]) / len(all_pairs), 5)
                if all_pairs else 0),
            "unresolved_pairs": len([p for p in all_pairs if p["confusable"]
                                     and p["z"] == "overlapping_vertical_volumes"]),
            "unresolved_share": (
                round(len([p for p in all_pairs if p["confusable"]
                           and p["z"] == "overlapping_vertical_volumes"])
                      / len(all_pairs), 5) if all_pairs else 0),
            "maps_with_an_unresolved_pair": len([
                r for r in rows if any(p["confusable"]
                                       and p["z"] == "overlapping_vertical_volumes"
                                       for p in r["pairs"])]),
        },
        "slab_between_overlapping_pairs": quantiles(
            [float(p["slab"]) for p in all_pairs if p["slab"] is not None]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--reference", default="BB4",
                        help="comma-separated maps to measure separately as a "
                             "worked example of the technique")
    parser.add_argument("-o", "--out", default="knowledge/blood/design/layers-v1.json")
    args = parser.parse_args(argv)

    wanted = {name.strip().upper() for name in args.reference.split(",") if name.strip()}
    rows: list[dict[str, Any]] = []
    reference: list[dict[str, Any]] = []
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name) and name not in wanted:
            continue
        row = measure(name, read_map(path))
        (rows if CAMPAIGN.match(name) else reference).append(row)
        print("{:6s} sectors={:4d} overlaps={:4d} z-clash={:4d} confusable={:3d} "
              "unresolved={:2d} floor-sprites={:4d}".format(
                  name, row["sectors"], row["overlap_pairs"], row["z_clashing_pairs"],
                  row["confusable_pairs"], row["unresolved_pairs"],
                  row["blocking_floor_aligned_sprites"]))

    document = summarise(rows, "E[1-46]M[1-9] under " + args.maps)
    if reference:
        document["reference"] = {
            "why": (
                "a small dense map that already is what a vertical fragment wants to "
                "be, measured with the same predicate so the two are comparable"),
            "maps": [dict(summarise([row], row["map"]), map=row["map"],
                          sectors=row["sectors"], bands=layer_bands(row))
                     for row in reference],
        }
        document["reference_detail"] = reference
    document["maps"] = rows
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print("\nwrote " + str(out))
    print(json.dumps({k: v for k, v in document.items()
                      if k not in ("maps", "reference_detail")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
