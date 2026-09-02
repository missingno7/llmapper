"""Intent: a name only where a measurement distinguishes, a refusal elsewhere.

E2M3 named 8 of its 340 sectors and refused the other 332, and that refusal is
the part worth copying. Two naming rules here, and both are measurements:

**A mechanism is named by the course that teaches its type.** The lesson files
under `maps/blood/mechanism/Vanilla` are the campaign's own name for a thing:
`DOOR-SWINGING.map` teaching sector type 617 with the shape "the whole sector
travels" is Blood telling us what a 617 of that shape is. So the function name
is the modal PREFIX of the lesson names that teach this (type, shape), and it
is taken only when one prefix holds a clear majority. That is not our
vocabulary put into the map's mouth; it is the curriculum's, counted.

**A place is named only by what was measured about it.** Holding the player
start, being wholly outdoors on the street network, containing a recovered
structure, carrying a stack link: each is a fact from another layer. A space
that fires no rule is refused by name, and a space that fires two is a
`candidate` for the selection pass rather than a name chosen by rule order.

Nothing here is evidence for anything. A name is an interpretation and it
carries the facts it was read from, so a later reader can overturn it.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Sequence

#: How much of the teaching one prefix must hold before it names the thing.
MAJORITY = 0.6


def _prefix(lesson: str) -> str:
    stem = lesson.rsplit(".", 1)[0]
    return stem.split("-", 1)[0].lower()


def name_mechanisms(sentences: Sequence[dict[str, Any]],
                    index: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """A function name per sentence, from the course, or a refusal."""
    named: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for row in sentences:
        type_id = row.get("type")
        if type_id is None:
            refused.append({"sentence": row["id"],
                            "why": "not a sector type: the course teaches it "
                                   "somewhere other than by type"})
            continue
        taught = index.get(int(type_id))
        if not taught:
            refused.append({"sentence": row["id"],
                            "why": f"the course teaches no lesson of type "
                                   f"{type_id}"})
            continue
        shape = row.get("shape") or "(no shape)"
        lessons = taught.get("lessons_by_shape", {}).get(shape)
        if not lessons:
            refused.append({"sentence": row["id"],
                            "why": f"the course teaches type {type_id} but "
                                   f"never with the shape {shape!r}"})
            continue
        votes: Counter = Counter()
        for lesson, count in lessons.items():
            votes[_prefix(lesson)] += count
        total = sum(votes.values())
        top, held = votes.most_common(1)[0]
        share = held / total if total else 0.0
        row_out = {"sentence": row["id"], "type": int(type_id), "shape": shape,
                   "name": top, "share": round(share, 3),
                   "lessons": sorted(lessons),
                   "basis": (f"{held} of {total} lesson constructs teaching "
                             f"type {type_id} with this shape come from "
                             f"lessons named {top.upper()}-*")}
        if share >= MAJORITY:
            named.append(row_out)
        else:
            candidates.append({**row_out,
                               "readings": [name for name, _ in votes.most_common()],
                               "why": (f"no prefix holds {MAJORITY:.0%} of the "
                                       f"teaching: {dict(votes)}")})
    return {"named": named, "candidates": candidates, "refused": refused,
            "rule": (f"the modal prefix of the lesson names teaching this "
                     f"(type, shape), taken when it holds at least "
                     f"{MAJORITY:.0%} of the teaching")}


def name_places(level: Any, spaces: Sequence[dict[str, Any]], *,
                street: Sequence[int] = (), start_sector: int | None = None,
                structures: dict[str, Sequence[int]] | None = None,
                stacks: Sequence[dict[str, Any]] = ()) -> dict[str, Any]:
    """A name per space, only where one measured rule fires."""
    structures = dict(structures or {})
    street = set(street)
    stacked: dict[int, str] = {}
    for stack in stacks:
        stacked[int(stack["lower"])] = f"stack {stack['link_id']}"
        stacked[int(stack["upper"])] = f"stack {stack['link_id']}"

    named, candidates, refused = [], [], []
    for space in spaces:
        sectors = set(space["sectors"])
        hits: list[dict[str, str]] = []
        if start_sector is not None and start_sector in sectors:
            hits.append({"name": "arrival",
                         "basis": f"holds the player start, sector {start_sector}"})
        if sectors and sectors <= street:
            hits.append({"name": "street",
                         "basis": f"all {len(sectors)} of its sectors are on "
                                  f"the outdoor street network"})
        for structure, members in structures.items():
            if sectors & set(members):
                hits.append({"name": structure.split(":")[1]
                             if ":" in structure else structure,
                             "basis": f"contains {structure}"})
        touched = sorted(sectors & set(stacked))
        if touched:
            hits.append({"name": "stacked_space",
                         "basis": f"carries a room-over-room link at "
                                  f"{', '.join(stacked[s] for s in touched)}"})
        if not hits:
            refused.append({"space": space["id"],
                            "why": "no measurement distinguishes it: it is "
                                   "an interior of this map like many others"})
        elif len(hits) == 1:
            named.append({"space": space["id"], **hits[0],
                          "sectors": sorted(sectors)})
        else:
            candidates.append({"space": space["id"],
                               "sectors": sorted(sectors),
                               "readings": [hit["name"] for hit in hits],
                               "bases": [hit["basis"] for hit in hits],
                               "why": "more than one measured rule fires, and "
                                      "rule order is not evidence"})
    return {"named": named, "candidates": candidates, "refused": refused,
            "rule": ("a name only where exactly one measured rule fires; two "
                     "rules is a candidate, none is a refusal")}


def summary(mechanisms: dict[str, Any], places: dict[str, Any]) -> dict[str, Any]:
    total_m = (len(mechanisms["named"]) + len(mechanisms["candidates"])
               + len(mechanisms["refused"]))
    total_p = (len(places["named"]) + len(places["candidates"])
               + len(places["refused"]))
    return {
        "mechanisms": {"named": len(mechanisms["named"]),
                       "candidates": len(mechanisms["candidates"]),
                       "refused": len(mechanisms["refused"]),
                       "population": total_m,
                       "named_percent": round(100.0 * len(mechanisms["named"]) / total_m, 2)
                       if total_m else 0.0},
        "places": {"named": len(places["named"]),
                   "candidates": len(places["candidates"]),
                   "refused": len(places["refused"]),
                   "population": total_p,
                   "named_percent": round(100.0 * len(places["named"]) / total_p, 2)
                   if total_p else 0.0},
        "names_by_kind": dict(Counter(row["name"] for row in mechanisms["named"])),
        "places_by_name": dict(Counter(row["name"] for row in places["named"])),
    }
