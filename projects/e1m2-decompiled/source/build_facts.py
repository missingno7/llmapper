"""Run every reader and store what it emits. The project orchestrates; that is all.

    PYTHONPATH=. python projects/e3m1-decompiled/source/build_facts.py

Writes one JSONL per predicate under `projects/e3m1-decompiled/facts/`, with
the base facts (the records as the map stores them) and every derived fact
carrying the facts it came from and the reader that made it.

No number is computed here. `query.py` answers every question the reports ask,
by reading these files.
"""

from __future__ import annotations

import json

from _common import MAP_NAME, PROJECT, art_dir, art_sizes, level

import os

from bloodmap import read_facts, read_intent
from bloodmap.anchors import find_bundles
from bloodmap.curriculum import mine_map
from bloodmap.format import read_map
from bloodmap.patterns import corpus_map_path
from bloodmap.read_mechanisms import curriculum_index, read_mechanisms
from bloodmap.read_store import FactStore, base_facts
from bloodmap.read_edges import read_edges
from bloodmap.read_islands import read_islands
from bloodmap.read_joins import adjacency, surface_kinds
from bloodmap.read_light import read_light
from bloodmap.read_joins import join_census
from bloodmap.read_plan import read_plan
from bloodmap.read_stairs import read_stairs
from bloodmap.read_surfaces import read_surfaces
from bloodmap.texture_frame import sector_index


def lessons_dir() -> str:
    """The taught course. `BLOODMAP_LESSONS` wins, then the corpus's own."""
    return os.environ.get(
        "BLOODMAP_LESSONS",
        str(corpus_map_path("E1M1").parent.parent / "mechanism" / "Vanilla"))


def main() -> int:
    world = level()
    owners = sector_index(world)
    store = FactStore()
    store.extend(base_facts(world))

    #: `connects` is a base relation, not a reading: two sectors share a
    #: two-sided record, and the map says so.
    graph = adjacency(world, owners)
    for here in sorted(graph):
        for there in sorted(graph[here]):
            if there > here:
                store.add("connects", f"sector:{here}-sector:{there}",
                          {"a": f"sector:{here}", "b": f"sector:{there}"},
                          sources=(f"sector:{here}", f"sector:{there}"),
                          reader="map")

    hierarchy = json.loads((PROJECT / "hierarchy.json").read_text(encoding="utf-8"))
    store.extend(read_facts.layer1(world, hierarchy))

    sizes = art_sizes()
    surfaces = read_surfaces(world, art_sizes=sizes)
    stairs = read_stairs(world)
    store.extend(read_facts.layer2(world, surfaces, stairs))

    kinds = surface_kinds(world, owners=owners)
    census = join_census(world, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer3(world, {"kinds": kinds, "census": census}))

    islands = read_islands(world, kinds["kinds"], owners=owners)
    light = read_light(world, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer4(world, islands, light))

    edges = read_edges(world, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer6(world, edges))

    plan = read_plan(world, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer7(world, plan))

    disk = read_map(corpus_map_path(MAP_NAME))
    reading = mine_map(corpus_map_path(MAP_NAME))
    mechanisms = read_mechanisms(world, disk, lessons=lessons_dir(),
                                 reading=reading)
    store.extend(read_facts.layer5(world, mechanisms))

    spaces = [node for node in hierarchy["nodes"]
              if node["kind"] == "space" and not any(
                  "reviewable singleton" in basis
                  for basis in node.get("basis", []))]
    structures = {run["id"]: run["sectors"] for run in stairs["runs"]}
    names = read_intent.name_mechanisms(
        mechanisms["sentences"], curriculum_index(lessons_dir()))
    places = read_intent.name_places(
        world, spaces,
        street=[index for index, kind in kinds["kinds"].items()
                if kind in ("road", "pavement", "outdoor_ground", "end_wall")],
        start_sector=int(disk.header["start_sector"]),
        structures=structures, stacks=mechanisms["stacks"],
        props=read_intent.named_props(world),
        bundles=[row.to_dict() for row in find_bundles(disk.to_build_ir())])
    store.extend(read_facts.layer8(names, places))

    #: The selection passes run LAST, over every candidate any reader left.
    store.extend(read_facts.selections(store))

    written = store.write(PROJECT / "facts")
    print(f"{MAP_NAME} fact store: {sum(written.values())} rows in "
          f"{len(written)} predicates")
    for predicate, count in sorted(written.items(), key=lambda row: -row[1]):
        print(f"    {predicate:16s} {count:6d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
