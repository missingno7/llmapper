"""Stage 2 -- hierarchy: the level as a small number of named places.

Stage 1 is 340 sectors.  This stage is the twenty places those sectors group
into, each with the evidence that grouped them and a local name that is an
*interpretation* and is labelled as one.

The point of the stage is context cost.  To answer "what is next to the space
the player starts in" from stage 1 you read 340 sectors and 2808 walls.  Here
you read one dict.

Naming rule used throughout: a name may only cite things that were measured --
footprint, clear height, sky, dominant tiles, sprite count, recovered
structures, connectivity.  Where the measurements do not distinguish two
readings, the name stays vague and ``confidence`` says so.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

HIERARCHY = pathlib.Path("projects/e2m3-decompiled/hierarchy.json")

#: Local, interpreted names.  ``basis`` lists only measured facts.  Nothing here
#: is evidence for anything: it is a reading that a later reader may overturn.
READING: dict[str, dict[str, Any]] = {
    "assembly:001/space:011": {
        "name": "arrival_yard",
        "confidence": "high",
        "basis": "holds the only player start; 478 player areas; every sector sky-lit; "
                 "42 sprites; the outdoor tile set (wall 2499, floor 2448, ceiling 2500)",
    },
    "assembly:001/space:028": {
        "name": "main_open_ground",
        "confidence": "high",
        "basis": "largest space at 873 player areas; 9 of 15 sectors sky-lit; outdoor tile "
                 "set; the only space touching both a second exterior and the big interior",
    },
    "assembly:001/space:063": {
        "name": "far_open_ground",
        "confidence": "medium",
        "basis": "820 player areas, 16 of 16 sectors sky-lit, outdoor tile set, but "
                 "connected only to two small spaces -- a separate outdoor lobe",
    },
    "assembly:001/space:037": {
        "name": "large_interior",
        "confidence": "high",
        "basis": "475 player areas with no sky at all; its own tile set (wall 153/181, "
                 "floor 253/21, ceiling 20/67); 27 sectors, 54 sprites -- the densest "
                 "space in the map; contains a stepped run, a recess and three shells",
    },
    "assembly:001/space:027": {
        "name": "shell_court",
        "confidence": "medium",
        "basis": "430 player areas, 4 sky sectors, three embedded shells and one recess; "
                 "a third tile set again (wall 309/355, floor 2490/355)",
    },
    "assembly:001/space:033": {
        "name": "second_interior",
        "confidence": "medium",
        "basis": "258 player areas, no sky, 7.3 player heights, wall 309/5 over floor 365/6",
    },
    "assembly:001/space:050": {
        "name": "outdoor_junction",
        "confidence": "high",
        "basis": "248 player areas, 11 of 11 sectors sky-lit, and the only space adjacent "
                 "to three other major spaces",
    },
    "assembly:001/space:044": {
        "name": "sprite_dense_interior",
        "confidence": "low",
        "basis": "233 player areas, no sky, 40 sprites, and a tile set (365/372) it shares "
                 "with nothing else; what it is for is not measured here",
    },
}

#: Deliberately not named.  Each of these is a real space the measurements do
#: not separate from its neighbours in any way worth a word.
UNNAMED_NOTE = (
    "128 further spaces are left with their derived ids. 92 of them are single "
    "sectors: door volumes, treads, ledges and detail pockets. Naming them would "
    "invent distinctions the evidence does not carry."
)


def hierarchy() -> dict[str, Any]:
    return json.loads(HIERARCHY.read_text(encoding="utf-8"))


def nodes_by_id(document: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    document = document or hierarchy()
    return {node["id"]: node for node in document["nodes"]}


def place(name: str) -> dict[str, Any]:
    """One named place, its reading, and the measurements behind the reading."""
    for node_id, reading in READING.items():
        if reading["name"] == name:
            node = nodes_by_id()[node_id]
            return {
                "id": node_id,
                "interpreted": reading,
                "measured": {
                    "sectors": len(node["sectors"]),
                    "sprites": node["sprite_count"],
                    "player_relative": node["player_relative"],
                    "dominant_assets": node["dominant_assets"],
                },
            }
    raise KeyError(name)


def structures_of(node_id: str) -> list[dict[str, Any]]:
    """The architectural structures the decompiler placed inside one space."""
    document = hierarchy()
    index = nodes_by_id(document)
    return [
        index[relation["from"]]["structure"]
        for relation in document["relations"]
        if relation["kind"] == "part_of" and relation["to"] == node_id
    ]


def tour() -> list[dict[str, Any]]:
    """Named places in descending footprint, with their named neighbours."""
    document = hierarchy()
    adjacency: dict[str, set[str]] = {}
    for relation in document["relations"]:
        if relation["kind"] != "connects":
            continue
        adjacency.setdefault(relation["from"], set()).add(relation["to"])
        adjacency.setdefault(relation["to"], set()).add(relation["from"])
    index = nodes_by_id(document)
    result = []
    for node_id, reading in READING.items():
        node = index[node_id]
        result.append({
            "name": reading["name"],
            "id": node_id,
            "player_areas": node["player_relative"]["footprint_player_areas"],
            "neighbours": sorted(
                READING[other]["name"]
                for other in adjacency.get(node_id, set()) if other in READING
            ),
            "structures": sorted({item["kind"] for item in structures_of(node_id)}),
        })
    return sorted(result, key=lambda item: -item["player_areas"])


def main() -> None:
    for row in tour():
        print(
            f"{row['name']:24s} {row['player_areas']:8.0f} player areas  "
            f"structures={row['structures'] or '-'}  next to {row['neighbours'] or '-'}"
        )
    print()
    print(UNNAMED_NOTE)


if __name__ == "__main__":
    main()
