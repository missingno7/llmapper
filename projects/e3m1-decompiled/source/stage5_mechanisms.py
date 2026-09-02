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


def _review(world, result) -> dict:
    tree = Tree(len(world.sectors), "E3M1 -- mechanisms as sentences")
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
    off_course = [row for row in result["sentences"]
                  if "but not this combination"
                  in row["against_the_course"].get("verdict", "")]
    chains = sorted((row for row in result["sentences"]
                     if row["kind"] == "tx -> rx chain"),
                    key=lambda row: -row.get("receivers", 0))
    questions = [
        {"node": (off_course[0]["id"] if off_course
                  else result["sentences"][0]["id"]),
         "question": (f"{len(off_course)} of {len(result['sentences'])} "
                      f"sentences use a (type, shape, slot) combination the "
                      f"taught course never shows -- s41's type 615 with "
                      f"'part of the sector travels' and a shade wave, for "
                      f"one. Is a combination the course does not teach a "
                      f"finding or a reader artefact?"),
         "recommended_default": ("a finding, and the interesting one: the "
                                 "course teaches each slot alone and the "
                                 "campaign combines them. It belongs in the "
                                 "curriculum's own gaps list, not in ours"),
         "evidence": "references/mechanisms.json: sentences[].against_the_course"},
        {"node": (chains[0]["id"] if chains else "level"),
         "question": (f"E3M1's biggest chain is one channel telling "
                      f"{chains[0].get('receivers') if chains else 0} records "
                      f"at once. Our writer has no construct that fans out "
                      f"like that. Should a chain be one sentence, or one "
                      f"sentence per receiver?"),
         "recommended_default": ("one sentence: the channel IS the mechanism "
                                 "and its fan-out is a parameter. Splitting "
                                 "it would make the collapsing house 159 "
                                 "mechanisms that happen to share a number"),
         "evidence": "references/mechanisms.json: links"},
        {"node": "kind:room_over_room",
         "question": ("All three of E3M1's stacks carry the same fault: the "
                      "floor marker sits 256 units below the plane it links. "
                      "Three of three is a convention, not a mistake. Is the "
                      "marker meant to float?"),
         "recommended_default": ("yes -- and the fault text should say "
                                 "'256 below, as all three of E3M1's do' "
                                 "rather than 'floats'. A convention the "
                                 "campaign keeps three times out of three is "
                                 "not a defect our checker gets to name"),
         "evidence": "references/mechanisms.json: stacks"},
    ]
    return write_pack(5, tree, "E3M1 layer 5: mechanisms as sentences",
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

    print(f"E3M1 mechanisms: {stats['sentences']} sentences {stats['by_kind']}")
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
