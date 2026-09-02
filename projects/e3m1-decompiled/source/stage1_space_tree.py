"""Stage 1 -- the space tree, and the sectors no area claims.

The reader is `bloodmap.decompiler.decompile_level`, reused unchanged: E2M3's
hierarchy applied to E3M1. What is new here is the residue. The hierarchy
PARTITIONS every sector by construction -- `LevelSource.validate` refuses one
that does not -- so "every sector is in a space" is a property of the schema,
not a measurement, and quoting it as coverage would be measuring our own
bookkeeping.

The measurement is which spaces are evidence and which are bookkeeping. A
space carries its basis; either it is

    "perceptual-space intersection with its navigation assembly"

-- several sectors a sensor grouped -- or it is

    "sector not grouped by current perceptual-space evidence; retained as a
     reviewable singleton"

-- one sector nothing grouped, kept so the partition closes. The second kind
is the residue of this layer: the sector is in the tree and the tree says
nothing about it.

    PYTHONPATH=. python projects/e3m1-decompiled/source/stage1_space_tree.py
"""

from __future__ import annotations

import json
from collections import Counter

from _common import PROJECT, level, write
from _review import Tree, answers, write_pack

SINGLETON = "retained as a reviewable singleton"


def read_space_tree() -> dict:
    hierarchy = json.loads((PROJECT / "hierarchy.json").read_text(encoding="utf-8"))
    nodes = hierarchy["nodes"]
    spaces = [node for node in nodes if node["kind"] == "space"]
    assemblies = [node for node in nodes if node["kind"] == "assembly"]
    grouped, singles = [], []
    for space in spaces:
        (singles if any(SINGLETON in basis for basis in space.get("basis", []))
         else grouped).append(space)
    residue = sorted(sector for space in singles for sector in space["sectors"])
    claimed = sorted(sector for space in grouped for sector in space["sectors"])
    lone_assemblies = [item["id"] for item in assemblies if len(item["sectors"]) == 1]
    return {
        "reader": "bloodmap.decompiler.decompile_level (reused, unchanged)",
        "sectors": len(claimed) + len(residue),
        "assemblies": len(assemblies),
        "assemblies_of_one_sector": lone_assemblies,
        "spaces": len(spaces),
        "spaces_with_grouping_evidence": len(grouped),
        "spaces_retained_as_singletons": len(singles),
        "structures": sum(1 for node in nodes if node["kind"] == "structure"),
        "structure_kinds": dict(Counter(
            node["structure"]["kind"] for node in nodes
            if node["kind"] == "structure" and "structure" in node)),
        "sectors_claimed_by_a_grouped_space": claimed,
        "residue_sectors": residue,
    }


def _review(payload: dict) -> dict:
    """The pack: the spaces a sensor grouped, and nothing else.

    The singleton spaces are deliberately NOT nodes. They exist in
    `hierarchy.json` only so the partition closes, and putting them in the
    pack would colour every one of them as an answer -- the map must show
    the 108 sectors nothing grouped as residue, because that is what they are.
    """
    hierarchy = json.loads((PROJECT / "hierarchy.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in hierarchy["nodes"]}
    sectors = len(nodes[hierarchy["primary_root"]]["sectors"])
    tree = Tree(sectors, "E3M1 -- spaces a sensor grouped")
    for node in hierarchy["nodes"]:
        if node["kind"] != "assembly":
            continue
        grouped = [nodes[child] for child in node["children"]
                   if nodes[child]["kind"] == "space"
                   and not any(SINGLETON in basis
                               for basis in nodes[child].get("basis", []))]
        if not grouped:
            continue
        #: An assembly holds only what its GROUPED spaces hold. Giving it its
        #: whole sector list would colour the 108 ungrouped sectors as an
        #: answer, and the pack's residue is exactly what must not be hidden.
        tree.add(node["id"], "assembly", node["name"], tree.root.id,
                 [value for child in grouped for value in child["sectors"]])
        for child in grouped:
            tree.add(child["id"], "space", child["name"], node["id"],
                     child["sectors"])
    questions = [{
        "node": "assembly:001",
        "question": ("36 spaces group 274 sectors and 108 sectors are grouped "
                     "by nothing. Is a singleton space a reading worth keeping "
                     "in the tree, or should the space tree admit that a "
                     "sector may belong to no space?"),
        "recommended_default": ("keep the singletons in hierarchy.json (the "
                               "partition is what validates) and keep them out "
                               "of the review pack and out of the explained "
                               "count, which is what this layer does"),
        "evidence": "references/space-tree.json: residue_sectors",
    }]
    return write_pack(1, tree, "E3M1 layer 1: the space tree", questions)


def main() -> int:
    payload = read_space_tree()
    claimed = len(payload["sectors_claimed_by_a_grouped_space"])
    residue = len(payload["residue_sectors"])
    total = claimed + residue
    payload["residue_percent"] = round(100.0 * residue / total, 2)
    payload["ledger"] = {
        "reader": payload["reader"],
        "gate": ("the hierarchy's own validator: primary spaces partition "
                 "every sector exactly once and every node's sources agree "
                 "with sector ownership (`LevelSource.validate`)"),
        "population": f"{total} sectors",
        "explained": claimed,
        "residue": residue,
        "residue_percent": payload["residue_percent"],
        "residue_is": ("sectors held only by a singleton space nothing "
                       "grouped: in the tree, and the tree says nothing "
                       "about them"),
        "disagreements": [],
    }
    payload["review"] = _review(payload)
    payload["owner_marks_read_back"] = answers(1)
    write("space-tree.json", payload)
    print(f"E3M1 space tree: {payload['assemblies']} assemblies, "
          f"{payload['spaces']} spaces, {payload['structures']} structures")
    print(f"  grouped by evidence : {len(payload['sectors_claimed_by_a_grouped_space'])} sectors "
          f"in {payload['spaces_with_grouping_evidence']} spaces")
    print(f"  RESIDUE             : {len(payload['residue_sectors'])} sectors "
          f"({payload['residue_percent']}%) in singleton spaces nothing grouped")
    print(f"  structures          : {payload['structure_kinds']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
