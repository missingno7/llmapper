"""One review pack per layer, in the shape `tools/review_pack.py` already reads.

The pack's `load_nodes` wants `{nodes: [{id, kind, name, parent, children,
sectors}]}` and computes the residue itself as the sectors no node owns. So
nothing in the tool is adapted: each layer emits a tree in that shape whose
nodes are **what that layer's reader decided**, and a sector the layer does
not explain is simply in no node, which is what makes the map show the residue
rather than a claim about it.

Orientation and colours belong to the tool and are not touched here.

Owner questions are NOT nodes. Putting them in the tree would make each one
own the sectors it asks about, and `review_pack`'s deepest-owner rule (the
node with the fewest sectors wins) would hand a question the sectors of the
answer -- the map would then be coloured by our doubts. They go beside the
pack in `questions-layer<N>.json`, each naming a node id that IS in the tree.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any, Iterable

PROJECT = pathlib.Path(__file__).resolve().parent.parent
REVIEW = PROJECT / "review"
REPO = PROJECT.parent.parent

MAX_QUESTIONS = 10


class Node:
    __slots__ = ("id", "kind", "name", "parent", "children", "sectors")

    def __init__(self, node_id: str, kind: str, name: str,
                 parent: str | None, sectors: Iterable[int] = ()) -> None:
        self.id = node_id
        self.kind = kind
        self.name = name
        self.parent = parent
        self.children: list[str] = []
        self.sectors = sorted(set(int(value) for value in sectors))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "name": self.name,
                "parent": self.parent, "children": list(self.children),
                "sectors": list(self.sectors)}


class Tree:
    """A layer's decisions as a tree, with the root owning every sector."""

    def __init__(self, sector_count: int, name: str) -> None:
        self.count = int(sector_count)
        self.nodes: dict[str, Node] = {}
        self.root = self.add("level", "level", name, None,
                             range(self.count))

    def add(self, node_id: str, kind: str, name: str, parent: str | None,
            sectors: Iterable[int] = ()) -> Node:
        node = Node(node_id, kind, name, parent, sectors)
        if node_id in self.nodes:
            raise ValueError(f"duplicate review node {node_id!r}")
        self.nodes[node_id] = node
        if parent is not None:
            self.nodes[parent].children.append(node_id)
        return node

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": [self.nodes[key].to_dict() for key in self.nodes]}

    def unowned(self) -> list[int]:
        """What the pack will show as residue: sectors no non-root node holds."""
        owned = {value for key, node in self.nodes.items()
                 if key != self.root.id for value in node.sectors}
        return [index for index in range(self.count) if index not in owned]


def write_pack(layer: int, tree: Tree, title: str,
               questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Write the layer's hierarchy, run the pack, and write its questions."""
    from _common import MAP_NAME

    from bloodmap.patterns import corpus_map_path

    if len(questions) > MAX_QUESTIONS:
        raise SystemExit(f"layer {layer} asks {len(questions)} questions; the "
                         f"owner's limit is {MAX_QUESTIONS} per layer")
    known = set(tree.nodes)
    for item in questions:
        if item["node"] not in known:
            raise SystemExit(f"question names {item['node']!r}, which is not a "
                             f"node of layer {layer}'s tree; a question the "
                             f"owner cannot click is not reviewable")
        if not item.get("recommended_default"):
            raise SystemExit(f"question on {item['node']!r} has no recommended "
                             f"default")
    REVIEW.mkdir(parents=True, exist_ok=True)
    hierarchy = REVIEW / f"layer{layer}-hierarchy.json"
    hierarchy.write_text(json.dumps(tree.to_dict(), indent=1), encoding="utf-8")
    (REVIEW / f"questions-layer{layer}.json").write_text(
        json.dumps({"layer": layer, "questions": questions}, indent=1),
        encoding="utf-8")
    out = REVIEW / f"layer{layer}.html"
    subprocess.run(
        [sys.executable, str(REPO / "tools" / "review_pack.py"),
         str(corpus_map_path(MAP_NAME)), str(hierarchy), "-o", str(out),
         "--title", title],
        check=True, cwd=str(REPO))
    residue = tree.unowned()
    print(f"  review pack   : {out.relative_to(REPO)} "
          f"({len(tree.nodes) - 1} nodes, {len(residue)} sectors unowned, "
          f"{len(questions)} owner questions)")
    return {"pack": str(out.relative_to(REPO)),
            "hierarchy": str(hierarchy.relative_to(REPO)),
            "questions": str((REVIEW / f'questions-layer{layer}.json').relative_to(REPO)),
            "sectors_unowned": residue}


def answers(layer: int) -> list[dict[str, Any]]:
    """The owner's marks for this layer, or an empty list if none arrived.

    Every mark must be fixed or refuted by a measurement in the next report.
    A missing file is "the owner has not reviewed this layer", never "the
    owner agreed".
    """
    path = REVIEW / f"answers-layer{layer}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("marks", []))
