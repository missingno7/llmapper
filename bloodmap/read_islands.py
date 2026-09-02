"""The reader half of `overlay.HeightIsland`: islands recovered from steps.

The writer declares a pavement as an island on a ground plane, with a rise and
a kerb tile, and `overlay.kerb_records` says which records carry the band.
This is the inverse: find the islands in an original map, recover each one's
outline and rise from the geometry, and then run the WRITER's `kerb_records`
over the recovered island to see which of its claims the map actually makes.

An island, read
===============

A maximal connected group of ground sectors standing one measured rise above
the base plane. The rise is `read_joins.measured_rise` -- counted off the map,
not taken from `HeightIsland.rise`'s default -- and the group is closed under
"same level, sharing a record", so a pavement band cut in three by shadow
boundaries is ONE island, which is the whole point of the model.

The outline is the group's own boundary: every record whose other side is not
in the group, chained into loops. Nothing is smoothed and no collinear pair is
merged, so the outline has exactly the vertices the map has.

The residue
===========

Two kinds, and they measure different things:

* **steps that are not islands** -- a floor step inside the network whose size
  is not the rise. Each is a place the island model does not reach.
* **island edges with no kerb** -- edges of a recovered island that carry no
  kerb band on the other side. This is where the writer over-claims:
  `kerb_records` emits one entry per edge of the island and never consults
  `ground_outline`, so it asks for a kerb on the side facing a building too.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Sequence

from .overlay import HeightIsland, kerb_records
from .read_joins import AUTOSTEP, adjacency, measured_rise, street_network
from .texture_frame import sector_index

Point = tuple[int, int]


def _face(item: Any) -> Any:
    return item["fields"] if isinstance(item, dict) else item.fields


def boundary_loops(level: Any, group: set[int], owners: Sequence[int]
                   ) -> list[list[Point]]:
    """The group's own outline: its records that face out, chained.

    Uses each record's `point2` successor restricted to the boundary, which is
    Build's own winding, so the loops come back in the order the map states
    rather than in one this function invents.
    """
    edges: dict[Point, Point] = {}
    for sector_id in sorted(group):
        fields = _face(level.sectors[sector_id])
        start = int(fields["wall_ptr"])
        for wall_id in range(start, start + int(fields["wall_count"])):
            face = _face(level.walls[wall_id])
            other = int(face["next_sector"])
            if other >= 0 and other in group:
                continue
            nxt = _face(level.walls[int(face["point2"])])
            edges[(int(face["x"]), int(face["y"]))] = (int(nxt["x"]), int(nxt["y"]))
    loops: list[list[Point]] = []
    seen: set[Point] = set()
    for start in sorted(edges):
        if start in seen:
            continue
        loop, current = [], start
        while current in edges and current not in seen:
            seen.add(current)
            loop.append(current)
            current = edges[current]
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def read_islands(level: Any, kinds: dict[int, str] | None = None, *,
                 owners: Sequence[int] | None = None) -> dict[str, Any]:
    """Every height island on the street network, and what nothing explains."""
    owners = list(owners) if owners is not None else sector_index(level)
    graph = adjacency(level, owners)
    network, _ = street_network(level, graph)
    rise, steps = measured_rise(level, network, graph)
    if kinds is None:
        from .read_joins import surface_kinds

        kinds = surface_kinds(level, owners=owners)["kinds"]

    def floor(index: int) -> int:
        return int(_face(level.sectors[index])["floor_z"])

    base_candidates = [floor(index) for index in network
                       if kinds.get(index) == "road"]
    base_z = max(base_candidates) if base_candidates else None
    on_island = sorted(index for index in network
                       if base_z is not None and floor(index) == base_z - rise)

    #: One island per connected group at the island level.
    groups: list[list[int]] = []
    left = set(on_island)
    while left:
        seed = min(left)
        found, queue = {seed}, [seed]
        while queue:
            current = queue.pop()
            for other in graph.get(current, ()):
                if other in left and other not in found:
                    found.add(other)
                    queue.append(other)
        left -= found
        groups.append(sorted(found))

    islands: list[dict[str, Any]] = []
    kerb_tiles: Counter = Counter()
    claimed = matched = 0
    unkerbed: list[dict[str, Any]] = []
    for number, group in enumerate(groups):
        loops = boundary_loops(level, set(group), owners)
        outline = max(loops, key=len) if loops else []
        #: What the MAP puts on the records of this island's boundary, by the
        #: kind of surface on the other side.
        band: dict[str, Counter] = defaultdict(Counter)
        facing: Counter = Counter()
        for sector_id in group:
            fields = _face(level.sectors[sector_id])
            start = int(fields["wall_ptr"])
            for wall_id in range(start, start + int(fields["wall_count"])):
                face = _face(level.walls[wall_id])
                other = int(face["next_sector"])
                if other >= 0 and other in group:
                    continue
                kind = kinds.get(other, "void") if other >= 0 else "void"
                facing[kind] += 1
                if other >= 0:
                    band[kind][int(_face(level.walls[int(face['next_wall'])])
                                   ["picnum"])] += 1
        #: The kerb is on the ROAD's record, so it is read from the road side.
        road_side = band.get("road", Counter())
        kerb_tiles.update(road_side)
        island = HeightIsland(island_id=f"island:{number:03d}",
                              outline=tuple(outline), rise=int(rise),
                              kerb_tile=int(road_side.most_common(1)[0][0])
                              if road_side else 0,
                              floor_picnum=int(_face(level.sectors[group[0]])
                                               ["floor_picnum"]))
        #: THE WRITER, RUN OVER THE RECOVERED ISLAND. `kerb_records` claims a
        #: kerb on every edge of the outline; the map puts one only where the
        #: other side is the road.
        wanted = kerb_records(island, "ground", outline)
        claimed += len(wanted)
        matched += sum(road_side.values())
        if len(wanted) > sum(road_side.values()):
            unkerbed.append({
                "island": island.island_id,
                "outline_edges": len(wanted),
                "records_the_map_kerbs": sum(road_side.values()),
                "what_the_other_side_is": dict(facing),
            })
        islands.append({
            "island_id": island.island_id,
            "sectors": group,
            "rise": int(rise),
            "floor_picnum": int(island.floor_picnum),
            "kerb_tile": int(island.kerb_tile),
            "outline_vertices": len(outline),
            "loops": len(loops),
            "boundary_faces": dict(facing),
            "road_side_tiles": dict(road_side),
        })

    not_islands = {int(size): int(count) for size, count in steps.items()
                   if int(size) != int(rise)}
    return {
        "rise": int(rise),
        "base_plane_z": base_z,
        "islands": islands,
        "island_sectors": on_island,
        "kerb_tiles_seen": dict(kerb_tiles),
        "kerb_records_the_writer_claims": claimed,
        "kerb_records_the_map_makes": matched,
        "islands_the_writer_over_claims": unkerbed,
        "steps_that_are_not_islands": not_islands,
        "steps_that_are_not_islands_count": sum(not_islands.values()),
        "walkable_steps_that_are_not_islands": {
            size: count for size, count in not_islands.items()
            if size <= AUTOSTEP},
    }


def summary(result: dict[str, Any]) -> dict[str, Any]:
    steps = int(result["steps_that_are_not_islands_count"])
    islands = len(result["islands"])
    total = steps + int(result["kerb_records_the_map_makes"])
    return {
        "islands": islands,
        "island_sectors": len(result["island_sectors"]),
        "rise": int(result["rise"]),
        "kerb_records_the_map_makes": int(result["kerb_records_the_map_makes"]),
        "kerb_records_the_writer_claims": int(result["kerb_records_the_writer_claims"]),
        "kerb_tiles_seen": result["kerb_tiles_seen"],
        "steps_that_are_not_islands": steps,
        "residue_percent": round(100.0 * steps / total, 2) if total else 0.0,
    }
