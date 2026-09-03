"""Stage 8 -- intent: a name only where a measurement distinguishes.

Two naming rules, both measurements. A mechanism is named by the PREFIX of the
lesson files that teach its (type, shape) -- `DOOR-SWINGING.map` teaching type
617 is Blood's own name for a 617, counted rather than chosen. A place is named
only where exactly one measured rule fires; two rules is a candidate for the
selection pass and none is a refusal.

E2M3 named 8 of its 340 sectors. The refusal is the part being copied.

    PYTHONPATH=. python projects/e3m1-decompiled/source/stage8_intent.py
"""

from __future__ import annotations

import json
from collections import Counter

from _common import MAP_NAME, PROJECT, level, write
from _review import Tree, answers, write_pack

from bloodmap.curriculum import mine_map
from bloodmap.format import read_map
from bloodmap.patterns import corpus_map_path
from bloodmap.anchors import find_bundles
from bloodmap.read_intent import (
    PROP_MAJORITY,
    name_mechanisms, name_places, named_props, summary)
from bloodmap.read_joins import surface_kinds
from bloodmap.read_mechanisms import curriculum_index, read_mechanisms
from bloodmap.read_stairs import read_stairs
from bloodmap.texture_frame import sector_index

import build_facts

SINGLETON = "retained as a reviewable singleton"


def _review(world, places, names) -> dict:
    tree = Tree(len(world.sectors), f"{MAP_NAME} -- names, and the refusals")
    named = places["named"]
    if named:
        tree.add("places", "intent", f"places one measurement names "
                 f"({len(named)})", tree.root.id,
                 [index for row in named for index in row["sectors"]])
        for row in named:
            tree.add(f"named:{row['space']}", "name",
                     f"{row['name']} <- {row['basis'][:60]}", "places",
                     row["sectors"])
    questions = [
        {"node": "level",
         "question": (f"{len(places['refused'])} of "
                      f"{len(places['named']) + len(places['candidates']) + len(places['refused'])} "
                      f"grouped spaces are refused a name: no measurement "
                      f"distinguishes them. E2M3 named 8 of 340 for the same "
                      f"reason. Is a refusal rate this high the honest answer, "
                      f"or a missing measurement?"),
         "recommended_default": ("the honest answer, and the missing "
                                 "measurement is named rather than guessed: "
                                 "what distinguishes a Blood interior is its "
                                 "furniture, and the prop reader is not "
                                 "wired into this layer yet"),
         "evidence": "references/intent.json: places.refused"},
    ]
    #: Asked only where a mechanism was named. E4M8's 45 sentences are all
    #: doors and channels the course teaches without a file prefix that holds
    #: a majority, so the reader names none of them -- and a question about
    #: naming, on a map with no name, is not a question about that map.
    if names["named"]:
        first = names["named"][0]
        questions.append({
            "node": f"named:{named[0]['space']}" if named else tree.root.id,
            "question": (f"A mechanism is named by the prefix of the lesson "
                         f"files teaching its type and shape -- "
                         f"{first['name'].upper()}-* for {first['sentence']}, "
                         f"on {first['basis']}. Is the curriculum's own file "
                         f"naming a fair source of function names?"),
            "recommended_default": ("yes, with the share reported: it is the "
                                    "campaign's vocabulary rather than ours, "
                                    "and where no prefix holds 60% the reader "
                                    "refuses instead of picking"),
            "evidence": "references/intent.json: mechanisms.named"})
    else:
        questions.append({
            "node": tree.root.id,
            "question": (f"No mechanism on this map is named: all "
                         f"{len(names['refused'])} refusals. The rule is that "
                         f"a lesson-file prefix must hold "
                         f"{int(PROP_MAJORITY * 100)}% of the lessons "
                         f"teaching that (type, shape). Is a map with no "
                         f"named mechanism a reading or a gap?"),
            "recommended_default": ("a reading. Every sentence here is a door "
                                    "or a channel, and the course teaches "
                                    "those under file names too varied for a "
                                    "majority. The refusal is the honest "
                                    "answer and the rate is the measurement"),
            "evidence": "references/intent.json: mechanisms.refused"})
    questions = questions[:10]
    return write_pack(8, tree, f"{MAP_NAME} layer 8: intent", questions)


def main() -> int:
    world = level()
    owners = sector_index(world)
    path = corpus_map_path(MAP_NAME)
    disk = read_map(path)
    kinds = surface_kinds(world, owners=owners)["kinds"]
    lessons = build_facts.lessons_dir()
    mechanisms = read_mechanisms(world, disk, lessons=lessons,
                                 reading=mine_map(path))
    stairs = read_stairs(world)
    hierarchy = json.loads((PROJECT / "hierarchy.json").read_text(encoding="utf-8"))
    spaces = [node for node in hierarchy["nodes"]
              if node["kind"] == "space"
              and not any(SINGLETON in basis for basis in node.get("basis", []))]

    names = name_mechanisms(mechanisms["sentences"], curriculum_index(lessons))
    places = name_places(
        world, spaces,
        street=[index for index, kind in kinds.items()
                if kind in ("road", "pavement", "outdoor_ground", "end_wall")],
        start_sector=int(disk.header["start_sector"]),
        structures={run["id"]: run["sectors"] for run in stairs["runs"]},
        stacks=mechanisms["stacks"],
        props=named_props(world),
        bundles=[row.to_dict() for row in find_bundles(disk.to_build_ir())])
    stats = summary(names, places)

    payload = {
        "reader": "bloodmap.read_intent (new)",
        "summary": stats,
        "mechanisms": names,
        "places": places,
        "ledger": {
            "reader": "bloodmap.read_intent (new)",
            "gate": ("a name only where a measurement distinguishes: the "
                     "modal lesson-name prefix for a mechanism, exactly one "
                     "firing rule for a place. Everything else is refused by "
                     "name"),
            "population": (f"{stats['mechanisms']['population']} sentences and "
                           f"{stats['places']['population']} grouped spaces"),
            "explained": (stats["mechanisms"]["named"] + stats["places"]["named"]),
            "residue": (len(names["refused"]) + len(places["refused"])),
            "residue_percent": round(
                100.0 * (len(names["refused"]) + len(places["refused"]))
                / max(1, stats["mechanisms"]["population"]
                      + stats["places"]["population"]), 2),
            "residue_is": "sentences and spaces no measurement names",
            "disagreements": [],
        },
    }
    payload["review"] = _review(world, places, names)
    payload["owner_marks_read_back"] = answers(8)
    write("intent.json", payload)

    print(f"{MAP_NAME} intent")
    print(f"  mechanisms         : {stats['mechanisms']['named']} named, "
          f"{stats['mechanisms']['candidates']} candidates, "
          f"{stats['mechanisms']['refused']} refused of "
          f"{stats['mechanisms']['population']}")
    print(f"    names            : {stats['names_by_kind']}")
    print(f"  places             : {stats['places']['named']} named, "
          f"{stats['places']['candidates']} candidates, "
          f"{stats['places']['refused']} refused of "
          f"{stats['places']['population']}")
    print(f"    names            : {stats['places_by_name']}")
    for row in places["named"]:
        print(f"      {row['space']:28s} {row['name']:16s} {row['basis'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
