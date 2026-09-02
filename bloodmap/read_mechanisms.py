"""Mechanisms as sentences, each checked against the curriculum lesson of its kind.

`curriculum.mine_map` already writes the sentence -- the Phase 8 grammar, one
line of English per construct -- and `conditional` already reads the wiring.
What is new here is the two things the experiment asks for:

1. **the comparison.** Before a sentence is written down, the same TYPE is
   looked up in the taught course under `maps/blood/mechanism/Vanilla`, and
   the sentence carries how many lessons teach that type and whether any of
   them shows this shape and this set of XSECTOR slots. A construct whose
   shape the course never shows is not wrong -- it is the interesting one, and
   it is flagged rather than smoothed.
2. **the denominator.** Every record that carries an XSECTOR, XWALL or XSPRITE
   is in the population, and a record no sentence realises is named residue.
   Counting only the sectors that already have a sentence would measure the
   reader.

A stair is not a mechanism (it is layer 2's structure) and a light wave is not
one either -- an XSECTOR with `amplitude` and nothing else is a sector lighting
itself, and it gets a sentence of that kind rather than being counted as a
mover that fails to move.
"""

from __future__ import annotations

import pathlib
from collections import Counter, defaultdict
from typing import Any, Sequence

#: `kWallGib`: the wall that breaks. 18 of E3M1's walls carry it and none of
#: them is a sector mechanism, so a reader that only walks sector types loses
#: every crack in the map.
WALL_GIB = 511

DEFAULT_LESSONS = "maps/blood/mechanism/Vanilla"


def _fields(item: Any) -> dict[str, Any]:
    return dict(item["fields"] if isinstance(item, dict) else item.fields)


def _extra(item: Any) -> dict[str, Any] | None:
    extra = item["blood"] if isinstance(item, dict) else getattr(item, "extra", None)
    if extra is None:
        return None
    return dict(extra["fields"] if isinstance(extra, dict) else extra.fields)


def curriculum_index(folder: str | pathlib.Path = DEFAULT_LESSONS
                     ) -> dict[int, dict[str, Any]]:
    """What the taught course shows, per sector type.

    Returns an empty index when the course is absent rather than raising: the
    sentences still get written, and every one of them then says the course
    was not consulted, which is the honest state and not a silent pass.
    """
    from .curriculum import mine_folder

    out: dict[int, dict[str, Any]] = {}
    try:
        readings = mine_folder(folder)
    except Exception as error:
        return {"error": repr(error)}          # type: ignore[return-value]
    for reading in readings:
        for construct in reading.constructs:
            if not construct.type_id:
                continue
            row = out.setdefault(int(construct.type_id), {
                "lessons": set(), "constructs": 0,
                "shapes": Counter(), "slots": Counter(),
                "lessons_by_shape": defaultdict(Counter)})
            row["lessons"].add(reading.name)
            row["constructs"] += 1
            row["shapes"][construct.shape or "(no shape)"] += 1
            row["slots"][",".join(sorted(construct.slots)) or "(none)"] += 1
            #: The lesson's FILE NAME is the course's own name for the thing.
            #: `DOOR-SWINGING.map` teaching type 617 is the campaign telling
            #: us what a 617 is, which is a measurement rather than our
            #: vocabulary -- and it is what layer 8 names a mechanism from.
            row["lessons_by_shape"][construct.shape or "(no shape)"][
                reading.name] += 1
    for row in out.values():
        row["lessons"] = sorted(row["lessons"])
        row["shapes"] = dict(row["shapes"])
        row["slots"] = dict(row["slots"])
        row["lessons_by_shape"] = {shape: dict(names) for shape, names
                                   in row["lessons_by_shape"].items()}
    return out


def _against_the_course(construct: Any, index: dict[int, dict[str, Any]]
                        ) -> dict[str, Any]:
    if "error" in index:
        return {"consulted": False, "why": index["error"]}
    row = index.get(int(construct.type_id))
    if row is None:
        return {"consulted": True, "lessons": 0,
                "verdict": "the course teaches no lesson of this type"}
    shape = construct.shape or "(no shape)"
    slots = ",".join(sorted(construct.slots)) or "(none)"
    return {
        "consulted": True,
        "lessons": len(row["lessons"]),
        "constructs_taught": row["constructs"],
        "shape_taught": int(row["shapes"].get(shape, 0)),
        "slots_taught": int(row["slots"].get(slots, 0)),
        "verdict": ("the course shows this shape and this slot set"
                    if row["shapes"].get(shape) and row["slots"].get(slots)
                    else "the course teaches this type but not this "
                         f"combination (shape {shape!r}, slots {slots!r})"),
        "example_lessons": row["lessons"][:3],
    }


def read_mechanisms(level: Any, disk: Any, *,
                    lessons: str | pathlib.Path = DEFAULT_LESSONS,
                    reading: Any = None) -> dict[str, Any]:
    """Every triggered record as a sentence, or as a named residue."""
    from .conditional import conditional_edges, key_sprites, transmitters
    from .curriculum import mine_map

    index = curriculum_index(lessons)
    if reading is None:
        reading = mine_map(disk if isinstance(disk, (str, pathlib.Path))
                           else getattr(disk, "path", None) or disk)
    mined = reading.as_json()

    #: THE DENOMINATOR: every record the map wired, not every record a
    #: reader happens to reach.
    wired: dict[str, list[int]] = {"sector": [], "wall": [], "sprite": []}
    for kind, items in (("sector", level.sectors), ("wall", level.walls),
                        ("sprite", level.sprites)):
        for index_, item in enumerate(items):
            if _extra(item) is not None:
                wired[kind].append(index_)

    sentences: list[dict[str, Any]] = []
    realises: dict[str, list[str]] = {}

    for construct in reading.constructs:
        if not construct.type_id:
            continue
        name = f"sentence:sector:{construct.sector}"
        sentences.append({
            "id": name, "kind": "sector mechanism",
            "type": int(construct.type_id),
            "sentence": construct.sentence,
            "shape": construct.shape,
            "slots": list(construct.slots),
            "z_pair": construct.z_pair,
            "against_the_course": _against_the_course(construct, index),
        })
        members = [f"sector:{construct.sector}"]
        members += [f"sector:{s}" for s in construct.motion_sectors
                    if s != construct.sector]
        members += [f"sprite:{s}" for s in construct.carried_sprites]
        members += [f"wall:{w}" for w in construct.buttons]
        realises[name] = members

    #: The crack. A `kWallGib` wall is a mechanism with no sector type, and
    #: its sentence is the wall plus whatever its XWALL transmits to.
    for index_, wall in enumerate(level.walls):
        fields = _fields(wall)
        if int(fields["type"]) != WALL_GIB:
            continue
        extra = _extra(wall) or {}
        name = f"sentence:wall:{index_}"
        sentences.append({
            "id": name, "kind": "breakable wall",
            "type": WALL_GIB,
            "sentence": (f"w{index_} type {WALL_GIB} (kWallGib): the wall "
                         f"breaks"
                         + (f", telling channel {int(extra['tx_id'])}"
                            if int(extra.get("tx_id", 0)) else "")
                         + (f", answered by channel {int(extra['rx_id'])}"
                            if int(extra.get("rx_id", 0)) else "")),
            "shape": "a wall that breaks",
            "slots": [key for key in ("tx_id", "rx_id", "key")
                      if int(extra.get(key, 0))],
            "against_the_course": {
                "consulted": True,
                "verdict": "kWallGib is a wall type; the course teaches it in "
                           "its wall lessons rather than as a sector type"},
        })
        realises[name] = [f"wall:{index_}"]

    for stack in mined["stacks"]:
        name = f"sentence:stack:{stack['link_id']}"
        sentences.append({
            "id": name, "kind": "room over room",
            "type": None,
            "sentence": (f"sectors {stack['lower']} and {stack['upper']} are "
                         f"one space stacked, linked by sprites "
                         f"{stack['sprites']}, offset {stack['offset']}"
                         + (f"; faults: {'; '.join(stack['faults'])}"
                            if stack.get("faults") else "")),
            "shape": "a stack",
            "slots": [],
            "against_the_course": {
                "consulted": True,
                "verdict": "the course teaches stacks as link markers; the "
                           "faults are read against that"},
            "faults": stack.get("faults", []),
        })
        realises[name] = ([f"sector:{stack['lower']}", f"sector:{stack['upper']}"]
                          + [f"sprite:{s}" for s in stack["sprites"]])

    wires = transmitters(disk)
    links = []
    for channel, sources in sorted(wires.items()):
        receivers = _receivers(level, int(channel))
        from_ = [f"{source.kind}:{source.index}" for source in sources]
        triggers = sorted({source.trigger for source in sources})
        links.append({"channel": int(channel), "from": from_,
                      "triggers": triggers, "to": receivers})
        if not receivers:
            continue
        #: THE CHAIN IS A SENTENCE. A record that only listens is not
        #: unexplained: it is the far end of a tx -> rx link, and the link is
        #: what E3M1's collapsing house IS -- one shot wall telling fourteen
        #: sectors to move. Without this the whole chain reads as residue and
        #: the map's biggest mechanism has no sentence at all.
        name = f"sentence:channel:{int(channel)}"
        sentences.append({
            "id": name, "kind": "tx -> rx chain",
            "type": None,
            "sentence": (f"channel {int(channel)}: "
                         f"{', '.join(from_)} ({'/'.join(triggers)}) tells "
                         f"{len(receivers)} record(s)"),
            "shape": "a chain",
            "slots": ["tx", "rx"],
            "against_the_course": {
                "consulted": True,
                "verdict": "the course teaches the channel as the one way a "
                           "trigger reaches an effect; the chain's LENGTH is "
                           "this map's own"},
            "receivers": len(receivers),
        })
        realises[name] = from_ + receivers
    keys = [{"channel": int(channel), "sprites": [f"sprite:{s}" for s in items]}
            for channel, items in sorted(key_sprites(disk).items())]
    edges, edge_census = conditional_edges(disk)
    conditions = [{
        "sectors": list(edge.sectors), "mechanism": edge.mechanism,
        "enabling_state": edge.enabling_state, "verdict": edge.verdict,
        "requires_key": edge.requires_key,
        "irreversible": bool(edge.irreversible),
        "causes": [f"{source.kind}:{source.index}" for source in edge.causes],
    } for edge in edges]

    claimed = {record for members in realises.values() for record in members}
    residue: list[dict[str, Any]] = []
    for kind, indexes in wired.items():
        for index_ in indexes:
            record = f"{kind}:{index_}"
            if record in claimed:
                continue
            extra = _extra((level.sectors, level.walls,
                            level.sprites)[("sector", "wall", "sprite").index(kind)][index_]) or {}
            residue.append({
                "record": record,
                "why": _why_unexplained(kind, extra),
            })
    return {
        "sentences": sentences,
        "realises": realises,
        "links": links,
        "keys": keys,
        "stacks": mined["stacks"],
        "conditions": conditions,
        "conditional_census": edge_census,
        "wall_buttons": mined["wall_buttons"],
        "wiring": mined["wiring"],
        "inventory": {
            "xsector": len(wired["sector"]),
            "xwall": len(wired["wall"]),
            "xsprite": len(wired["sprite"]),
            "sector_types": dict(Counter(
                int(_fields(item)["type"]) for item in level.sectors
                if int(_fields(item)["type"]))),
            "wall_types": dict(Counter(
                int(_fields(item)["type"]) for item in level.walls
                if int(_fields(item)["type"]))),
            "records_with_tx": _with(level, "tx_id"),
            "records_with_rx": _with(level, "rx_id"),
            "records_with_a_key": _with(level, "key"),
            "sectors_with_a_light_wave": sum(
                1 for item in level.sectors
                if (_extra(item) or {}).get("amplitude")),
            "sectors_with_shade_always": sum(
                1 for item in level.sectors
                if (_extra(item) or {}).get("shade_always")),
        },
        "curriculum": {str(key): {"lessons": len(value["lessons"]),
                                  "constructs": value["constructs"]}
                       for key, value in index.items()
                       if isinstance(value, dict) and "lessons" in value},
        "wired_records": sum(len(value) for value in wired.values()),
        "records_a_sentence_realises": len(claimed),
        "residue": residue,
    }


def _with(level: Any, name: str) -> dict[str, int]:
    out = {}
    for kind, items in (("sector", level.sectors), ("wall", level.walls),
                        ("sprite", level.sprites)):
        out[kind] = sum(1 for item in items
                        if int((_extra(item) or {}).get(name, 0)))
    out["total"] = sum(out.values())
    return out


def _receivers(level: Any, channel: int) -> list[str]:
    out = []
    for kind, items in (("sector", level.sectors), ("wall", level.walls),
                        ("sprite", level.sprites)):
        for index, item in enumerate(items):
            if int((_extra(item) or {}).get("rx_id", 0)) == channel:
                out.append(f"{kind}:{index}")
    return out


def _why_unexplained(kind: str, extra: dict[str, Any]) -> str:
    if int(extra.get("amplitude", 0)) or int(extra.get("shade_always", 0)):
        return ("carries a light wave and nothing else: a sector lighting "
                "itself, which is a sentence this reader does not yet write")
    if int(extra.get("rx_id", 0)):
        return (f"listens on channel {int(extra['rx_id'])} but no sentence "
                f"names it: an effect nothing in the model produces")
    if int(extra.get("tx_id", 0)):
        return (f"transmits on channel {int(extra['tx_id'])} but no sentence "
                f"names it")
    if kind == "sprite":
        return ("an XSPRITE with no wiring this reader reads: a pickup, a "
                "dude or a decoration carrying its own state")
    return "wired, and no sentence realises it"


def summary(result: dict[str, Any]) -> dict[str, Any]:
    wired = int(result["wired_records"])
    residue = len(result["residue"])
    return {
        "sentences": len(result["sentences"]),
        "by_kind": dict(Counter(row["kind"] for row in result["sentences"])),
        "links": len(result["links"]),
        "keys": len(result["keys"]),
        "stacks": len(result["stacks"]),
        "conditions": len(result["conditions"]),
        "wired_records": wired,
        "records_a_sentence_realises": int(result["records_a_sentence_realises"]),
        "residue_records": residue,
        "residue_percent": round(100.0 * residue / wired, 2) if wired else 0.0,
        "inventory": result["inventory"],
    }
