"""Wiring: what a player's act sets off, followed from sender to listener across sectors, walls and sprites.

There is no such thing in Blood as a door or a lift. There are sectors, walls
and sprites, and laid over them a second layer: this one sends on a channel
when something is done to it, those listen on that channel and do what their
own fields say. A "door" is a sector that changes what fits through it, plus
whatever was wired to set it off, and the same sector type on the end of a
different wire is a crusher, a secret or a trap. So a mechanism is not a
record. It is a CHAIN: a cause, the object it happens to, the channel that
object sends on, everything that listens, and on through any listener that
sends in turn.

`chains` reads that layer off a map. A chain starts where the engine itself
starts one:

* a trigger flag on the object (pushed, shot, entered, picked up, ...);
* a dude that is killed or a thing that is destroyed, which fire their own
  trigger with no flag at all (`actKillDude`, actor.cpp:3029; the thing
  branch of `actDamageSprite`, actor.cpp:3513);
* one of the engine's channels the object listens on (the level starting).

and it ends at its listeners, or at one of the engine's own channels (a
secret found, the level's exit), which is a listener no record holds.

`shape` reduces a chain to what a mapper asks for -- "a pushed switch that
moves a floor" -- so the same wiring can be counted and found across a
campaign. `bloodmap.examples` indexes the shapes; `tools/catalog.py
mechanisms MAP` prints one map's chains. The per-channel bus views
(`analysis.channel_graph`, `curriculum.wiring_graph`) answer a different
question, who is on a channel; this answers what happens.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from .blood_types import RESERVED_CHANNELS, SECTOR_TYPES, SPRITE_TYPES, WALL_TYPES
from .model import record_extra, record_fields
from .sector_geom import wall_owners

#: A trigger flag, and what a player (or anything else) does to raise it.
CAUSES: tuple[str, ...] = ("push", "vector", "impact", "pickup", "touch", "sight",
                           "proximity", "enter", "exit", "wall_push")

#: Channels from here up are a level's own; below are the engine's, and zero
#: is no channel at all (`if (pXSprite->txID)`, triggers.cpp).
USER_CHANNELS_FROM = 100

#: How far a chain is followed through listeners that send in turn.
MAX_DEPTH = 8

#: `bloodmap.effects`' reading of a moving sector, as the clause a shape says.
#: Its other readings ("neither", "not decidable from z alone") say nothing a
#: mapper can use, so a sector read that way keeps its type's name alone.
DOES = {
    "changes what fits through": "changes what fits through",
    "carries a body between levels": "carries a body between levels",
    "both": "changes what fits through and carries a body between levels",
}


def _engine_channel(channel: int) -> str | None:
    """The engine's name for a channel it owns, or None for a level's own or none."""
    if 0 < channel < USER_CHANNELS_FROM and channel in RESERVED_CHANNELS:
        return str(RESERVED_CHANNELS[channel]["name"])
    return None


def nodes(disk: Any) -> list[dict[str, Any]]:
    """Every sector, wall and sprite that sends or listens, with why it would fire."""
    owners = wall_owners(disk)
    out = []
    for kind, group, table in (("sprite", disk.sprites, SPRITE_TYPES),
                               ("sector", disk.sectors, SECTOR_TYPES),
                               ("wall", disk.walls, WALL_TYPES)):
        for index, item in enumerate(group):
            extra = record_extra(item) or {}
            tx, rx = int(extra.get("tx_id", 0) or 0), int(extra.get("rx_id", 0) or 0)
            if not tx and not rx:
                continue
            fields = record_fields(item)
            type_id = int(fields.get("type", 0))
            named = table.get(type_id) or {}
            causes = [cause for cause in CAUSES
                      if int(extra.get(f"trigger_{cause}", 0) or 0)]
            if not causes and tx and kind == "sprite":
                # No flag, and it still fires: the engine triggers a dude on
                # its death and a thing on its destruction.
                if named.get("category") == "dude":
                    causes = ["killed"]
                elif named.get("category") == "thing":
                    causes = ["destroyed"]
            sector = (int(fields["sector"]) if kind == "sprite"
                      else index if kind == "sector" else owners.get(index, -1))
            out.append({
                "id": f"{kind} {index}", "kind": kind, "index": index,
                "type": type_id, "type_name": named.get("name", str(type_id)),
                "tile": int(fields.get("picnum", fields.get("floor_picnum", 0))),
                "tx": tx, "rx": rx, "command": int(extra.get("command", 0) or 0),
                "causes": causes, "sector": sector,
                "once": bool(int(extra.get("trigger_once", 0) or 0)),
                "wait": int(extra.get("wait_time", extra.get("wait_time_a", 0)) or 0),
                "key": int(extra.get("key", 0) or 0)})
    return out


def chains(disk: Any, only: Iterable[int] | None = None) -> list[dict[str, Any]]:
    """Every chain of one map, deepest first: a cause, a sender, and all that answers.

    `only` keeps the chains whose first object is in one of those sectors. A
    step whose `to` is ``engine`` ends on a channel the engine owns; its
    `to_type` is that channel's name.
    """
    every = nodes(disk)
    keep = None if only is None else set(only)
    listeners: dict[int, list[dict[str, Any]]] = {}
    for node in every:
        if node["rx"]:
            listeners.setdefault(node["rx"], []).append(node)
    found = []
    for node in every:
        if not node["tx"]:
            continue
        started_by = _engine_channel(node["rx"])
        if node["causes"]:
            cause = list(node["causes"])
        elif started_by:
            cause = [f"channel {node['rx']} {started_by}"]
        elif not node["rx"]:
            # It sends, nothing is flagged and it listens to nothing: what
            # fires it is its own type's business (a generator's timer).
            cause = ["itself"]
        else:
            continue                      # a relay: it is some other chain's step
        if keep is not None and node["sector"] not in keep:
            continue
        steps, seen, frontier, depth = [], {node["id"]}, [node], 0
        while frontier and depth < MAX_DEPTH:
            following = []
            for sender in frontier:
                engine = _engine_channel(sender["tx"])
                if engine:
                    steps.append({"from": sender["id"], "channel": sender["tx"],
                                  "command": sender["command"], "to": "engine",
                                  "to_kind": "engine", "to_type_id": sender["tx"],
                                  "to_type": engine, "wait": 0})
                for receiver in listeners.get(sender["tx"], ()):
                    steps.append({"from": sender["id"], "channel": sender["tx"],
                                  "command": sender["command"],
                                  "to": receiver["id"], "to_kind": receiver["kind"],
                                  "to_type_id": receiver["type"],
                                  "to_type": receiver["type_name"],
                                  "wait": receiver["wait"]})
                    if receiver["id"] not in seen and receiver["tx"]:
                        seen.add(receiver["id"])
                        following.append(receiver)
            frontier, depth = following, depth + 1
        found.append({
            "root": node["id"], "root_kind": node["kind"], "root_type_id": node["type"],
            "root_type": node["type_name"], "tile": node["tile"],
            "sector": node["sector"], "cause": cause,
            "key": node["key"], "once": node["once"],
            "steps": steps, "depth": depth,
            "receivers": dict(Counter(step["to_type"] for step in steps))})
    found.sort(key=lambda chain: (-chain["depth"], -len(chain["steps"])))
    return found


def _part(kind: str, type_id: int, type_name: str) -> str:
    """A part in a mapper's words: its type's name, or what it plainly is."""
    if kind == "engine":
        return f"the engine ({type_name})"
    if not type_id:
        return f"a plain {kind}"
    return type_name


def shape(chain: Mapping[str, Any],
          readings: Mapping[int, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """What a chain is, with its numbers taken out: cause, sender, what answers.

    Two chains of one shape are the same wiring in two places. `readings` is
    sector to `bloodmap.effects`' reading of it; with it a moving sector on
    the end of the wire is named by what it does to the space around it
    ("changes what fits through"), which is the only honest sense in which a
    sector is a door.
    """
    answers = set()
    for step in chain["steps"]:
        said = _part(step["to_kind"], step["to_type_id"], step["to_type"])
        if step["to_kind"] == "sector" and readings is not None:
            reading = readings.get(int(step["to"].split()[1]))
            if reading and reading["is"] in DOES:
                said += f" that {DOES[reading['is']]}"
        answers.add(said)
    return {"cause": "/".join(chain["cause"]),
            "sender": _part(chain["root_kind"], chain["root_type_id"], chain["root_type"]),
            "answers": sorted(answers)}
