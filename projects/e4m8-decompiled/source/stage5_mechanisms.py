"""Stage 5 -- mechanisms as sentences, each checked against its lesson.

`bloodmap.read_mechanisms` writes one sentence per triggered sector, per
`kWallGib` wall, per stack and per tx -> rx chain, and looks each one up in
the taught course under `maps/blood/mechanism/Vanilla` before writing it down.
A wired record no sentence realises is named residue.

The denominator is the supervisor's inventory and the reader reproduces it:
133 XSECTORs, 41 XWALLs, 716 XSPRITEs; sector types 600 x34, 614 x6, 615 x4,
616 x1, 617 x6, 618 x1; 18 walls of type 511; 26 sectors with a tx, 54 with an
rx, 4 key-locked; 61 with a light wave, 45 with shade_always.

    PYTHONPATH=. python projects/e3m1-decompiled/source/stage5_mechanisms.py
"""

from __future__ import annotations

from collections import Counter

from _common import MAP_NAME, level, write
from _review import Tree, answers, write_pack

from bloodmap.curriculum import mine_map
from bloodmap.format import read_map
from bloodmap.patterns import corpus_map_path
from bloodmap.read_mechanisms import read_mechanisms, summary

import build_facts


def _example(off_course) -> str:
    """Name one off-course sentence, from this map, or say nothing."""
    if not off_course:
        return ""
    row = off_course[0]
    verdict = row["against_the_course"].get("verdict", "")
    return f" -- {row['id'].split('sentence:')[1]}, {verdict}, for one"


def _review(world, result) -> dict:
    tree = Tree(len(world.sectors), f"{MAP_NAME} -- mechanisms as sentences")
    by_kind: dict[str, list[str]] = {}
    for row in result["sentences"]:
        by_kind.setdefault(row["kind"], []).append(row["id"])

    def sectors_of(ids) -> list[int]:
        out = []
        for name in ids:
            for record in result["realises"].get(name, ()):
                kind, index = record.split(":", 1)
                if kind == "sector":
                    out.append(int(index))
                elif kind == "sprite":
                    out.append(int(world.sprites[int(index)]["fields"]["sector"]))
        return out

    for kind, ids in sorted(by_kind.items()):
        node = f"kind:{kind.replace(' ', '_')}"
        tree.add(node, "mechanism_kind", f"{kind} ({len(ids)})",
                 tree.root.id, sectors_of(ids))
        for name in ids[:40]:
            tree.add(name, "sentence", name.split("sentence:")[1],
                     node, sectors_of([name]))
    def ensure(node_id: str) -> str:
        """A question must name a node the owner can click.

        The tree shows the first 40 sentences of each kind, and the sentence a
        question is about is not always among them -- E1M2's biggest chain is
        not in its first 40 channels. So the referenced node is added on
        demand, under its kind, rather than the question being retargeted.
        """
        if node_id in tree.nodes or node_id == tree.root.id:
            return node_id
        row = next((one for one in result["sentences"]
                    if one["id"] == node_id), None)
        if row is None:
            return tree.root.id
        parent = f"kind:{row['kind'].replace(' ', '_')}"
        tree.add(node_id, "sentence", node_id.split("sentence:")[1],
                 parent if parent in tree.nodes else tree.root.id,
                 sectors_of([node_id]))
        return node_id

    off_course = [row for row in result["sentences"]
                  if "but not this combination"
                  in row["against_the_course"].get("verdict", "")]
    chains = sorted((row for row in result["sentences"]
                     if row["kind"] == "tx -> rx chain"),
                    key=lambda row: -row.get("receivers", 0))
    questions = [
        {"node": ensure(off_course[0]["id"] if off_course
                        else result["sentences"][0]["id"]),
         "question": (f"{len(off_course)} of {len(result['sentences'])} "
                      f"sentences use a (type, shape, slot) combination the "
                      f"taught course never shows"
                      f"{_example(off_course)}. Is a combination the course "
                      f"does not teach a "
                      f"finding or a reader artefact?"),
         "recommended_default": ("a finding, and the interesting one: the "
                                 "course teaches each slot alone and the "
                                 "campaign combines them. It belongs in the "
                                 "curriculum's own gaps list, not in ours"),
         "evidence": "references/mechanisms.json: sentences[].against_the_course"},
        {"node": ensure(chains[0]["id"]) if chains else tree.root.id,
         "question": (f"the biggest chain here is one channel telling "
                      f"{chains[0].get('receivers') if chains else 0} records "
                      f"at once. Our writer has no construct that fans out "
                      f"like that. Should a chain be one sentence, or one "
                      f"sentence per receiver?"),
         "recommended_default": ("one sentence: the channel IS the mechanism "
                                 "and its fan-out is a parameter. Splitting "
                                 "it would make the collapsing house 159 "
                                 "mechanisms that happen to share a number"),
         "evidence": "references/mechanisms.json: links"},
    ]
    #: Only where there is a stack to ask about. The 256-below convention was
    #: read off E3M1's three and is now the checker's (queue item 30e); a map
    #: with stacks of its own is asked whether it keeps the same convention.
    if result["stacks"] and "kind:room_over_room" in tree.nodes:
        faults = [fault for stack in result["stacks"]
                  for fault in stack.get("faults", ())]
        questions.append({
            "node": "kind:room_over_room",
            "question": (f"this map has {len(result['stacks'])} stacks and "
                         f"the checker reports {len(faults)} faults on them. "
                         f"E3M1's three all sat 256 units below the plane "
                         f"they link, which `curriculum.stack_faults` now "
                         f"treats as a convention. Do this map's stacks keep "
                         f"it?"),
            "recommended_default": ("yes where no fault is reported: silence "
                                    "IS the answer, because the checker only "
                                    "excuses that exact offset and flags "
                                    "every other one"),
            "evidence": "references/mechanisms.json: stacks"})
    questions = questions[:10]
    return write_pack(5, tree, f"{MAP_NAME} layer 5: mechanisms as sentences",
                      questions)


def main() -> int:
    world = level()
    path = corpus_map_path(MAP_NAME)
    disk = read_map(path)
    result = read_mechanisms(world, disk, lessons=build_facts.lessons_dir(),
                             reading=mine_map(path))
    stats = summary(result)

    payload = {
        "reader": "bloodmap.read_mechanisms (new; reuses curriculum.mine_map "
                  "for the sentence and conditional.* for the wiring)",
        "summary": stats,
        "sentences": result["sentences"],
        "realises": result["realises"],
        "links": result["links"],
        "keys": result["keys"],
        "stacks": result["stacks"],
        "conditions": result["conditions"],
        "conditional_census": result["conditional_census"],
        "curriculum": result["curriculum"],
        "wall_buttons": result["wall_buttons"],
        "wiring": result["wiring"],
        "residue": result["residue"],
        "ledger": {
            "reader": "bloodmap.read_mechanisms (new)",
            "gate": ("every record carrying an XSECTOR, XWALL or XSPRITE "
                     "either realised by a sentence or named as residue; each "
                     "sentence checked against the lessons of its type"),
            "population": f"{result['wired_records']} wired records "
                          f"(133 XSECTOR, 41 XWALL, 716 XSPRITE)",
            "explained": result["records_a_sentence_realises"],
            "residue": len(result["residue"]),
            "residue_percent": stats["residue_percent"],
            "residue_is": "wired records no sentence realises",
            "disagreements": [],
        },
    }
    payload["review"] = _review(world, result)
    payload["owner_marks_read_back"] = answers(5)
    write("mechanisms.json", payload)

    print(f"{MAP_NAME} mechanisms: {stats['sentences']} sentences {stats['by_kind']}")
    print(f"  inventory          : {stats['inventory']['xsector']} XSECTOR, "
          f"{stats['inventory']['xwall']} XWALL, "
          f"{stats['inventory']['xsprite']} XSPRITE; sector types "
          f"{stats['inventory']['sector_types']}; wall types "
          f"{stats['inventory']['wall_types']}")
    print(f"  wiring             : {stats['links']} channels, "
          f"{stats['keys']} keyed, {stats['stacks']} stacks, "
          f"{stats['conditions']} conditional crossings")
    print(f"  tx / rx / key      : sectors "
          f"{stats['inventory']['records_with_tx']['sector']} / "
          f"{stats['inventory']['records_with_rx']['sector']} / "
          f"{stats['inventory']['records_with_a_key']['sector']}")
    print(f"  against the course : "
          f"{sum(1 for row in result['sentences'] if 'but not this combination' in row['against_the_course'].get('verdict', ''))}"
          f" sentences use a combination the course never shows")
    print(f"  RESIDUE            : {len(result['residue'])} of "
          f"{result['wired_records']} wired records "
          f"({stats['residue_percent']}%)")
    print(f"    by reason        : "
          f"{Counter(row['why'][:38] for row in result['residue']).most_common(4)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
