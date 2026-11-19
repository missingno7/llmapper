"""Completion: whether our readers can finish a map that is known to be finishable, and where they stop.

A shipped campaign map is evidence of four things nobody has to label. It can
be finished. Every key in it can be picked up. The space a player can stand
in can be stood in. And it says how many secrets it has, on the engine's own
channel. So a reader of maps can be marked against the campaign with no human
in the loop: read the map, and see whether the reading reaches the exit, the
keys and the rooms, and counts the secrets the map counts.

This is that mark for one map. It runs the traversal reader
(`bloodmap.conditional.frontier`, through `bloodmap.bundle`) and the wiring
reader (`bloodmap.wiring.chains`) and compares them with the map's own
records. Where a reading falls short the map is not wrong; the reader is, or
is silent about something, and `unreached` and `missed` say where to look.
`tools/reading_check.py` runs it over the campaign and keeps the score.

Engine facts used, from the source and not assumed:

* an exit is a chain that ends on channel 4 or 5 (`kChannelLevelExitNormal`,
  `kChannelLevelExitSecret`);
* a secret is credited on channel 2 with a numeric command, and the number is
  a TYPE, not an index: 0 is a normal secret, anything more a super secret
  (`CSecretMgr::Found`, endgame.cpp:240). The level's total is sent on
  channel 1 as `64 + n` (eventq.cpp:393) and counts the normal ones.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from . import bundle, reachability, wiring
from .blood_types import classify
from .doors import KEY_NAMES
from .model import record_extra, record_fields

EXIT_CHANNELS = (4, 5)
SECRET_TOTAL_CHANNEL, SECRET_FOUND_CHANNEL = 1, 2
NUMERIC = 64


def reached_sectors(progression: dict[str, Any]) -> set[int]:
    """Every sector the traversal reader ends up standing in.

    The reader's own list when it gives one. A round's `newly_reachable` is
    cut at 64, so adding the rounds up undercounts a big map, and the first
    scorecard was read that way.
    """
    if "reached_sectors" in progression:
        return set(progression["reached_sectors"])
    reached: set[int] = set()
    for step in progression.get("rounds", ()):
        reached.update(step.get("newly_reachable", ()))
        for action in step.get("actions", ()):
            reached.update(action.get("newly_reachable", ()))
    return reached


def player_space(disk: Any, kinds: dict[int, str] | None = None) -> set[int]:
    """Sectors a body could ever stand in: not behind a wall nothing opens.

    `reachability.sector_kinds` calls a sector reachable when portals join it
    to the start, and a horizon, a sky backing and a vault seen through bars
    are all joined by portals. A blocking wall that no gib wall reopens and
    no travelling leaf carries away is shut for ever (`conditional.KWALLGIB`),
    so what lies only behind one is scenery. Counted as player space, the
    city's sea and street ends were 25 sectors "never reached".
    """
    from . import conditional

    kinds = reachability.sector_kinds(disk) if kinds is None else kinds
    graph = conditional.build_graph(disk)
    shut = set(conditional.blocking_crossings(disk))
    shut -= {edge.sectors for edge in graph.edges if edge.mechanism_kind == "wall"}
    shut -= set(graph.swept_blocked)
    seen, pending = {graph.start}, [graph.start]
    links = conditional._non_portal_pairs(graph.reach)
    step = {}
    for left, right in links:
        step.setdefault(left, set()).add(right)
    while pending:
        here = pending.pop()
        for there in set(graph.reach.graph.get(here, ())) | step.get(here, set()):
            if there in seen or ((here, there) in shut and (here, there) not in links):
                continue
            seen.add(there)
            pending.append(there)
    return {sector for sector in seen if kinds.get(sector) == "reachable"}


def read(disk: Any, name: str = "") -> dict[str, Any]:
    """One map's mark: what a finished map must have, and what the readers found."""
    views = bundle.build_bundle(disk, map_name=name)["views"]
    progression = views.get("progression") or {}
    reached = reached_sectors(progression)
    kinds = reachability.sector_kinds(disk)
    space = sorted(player_space(disk, kinds))
    every = wiring.nodes(disk)
    by_id = {node["id"]: node for node in every}
    found = wiring.chains(disk, reach=kinds)

    exits = []
    for chain in found:
        ends = [step for step in chain["steps"]
                if step["to"] == "engine" and step["channel"] in EXIT_CHANNELS]
        if ends and not chain["silent"]:
            exits.append({"root": chain["root"], "cause": "/".join(chain["cause"]),
                          "sector": chain["sector"], "to": ends[0]["to_type"],
                          "reached": chain["sector"] in reached})

    keys = []
    for index, sprite in enumerate(disk.sprites):
        fields = record_fields(sprite)
        named = classify("sprite", int(fields["type"]))
        if named.get("category") == "key":
            keys.append({"sprite": index, "name": named.get("name"),
                         "sector": int(fields["sector"]),
                         "reached": int(fields["sector"]) in reached})
        elif named.get("category") == "dude":
            # a key a dude drops when killed (actor.cpp:3053)
            carried = int((record_extra(sprite) or {}).get("key", 0) or 0)
            if carried:
                keys.append({"sprite": index,
                             "name": f"{KEY_NAMES.get(carried, carried)} key, "
                                     f"dropped by {named.get('name')}",
                             "sector": int(fields["sector"]),
                             "reached": int(fields["sector"]) in reached})
    #: what wants a key, and what it works when it has one
    locked: dict[tuple[int, int], dict[str, Any]] = {}
    roots = {chain["root"]: chain for chain in found}
    for node in every:
        if not node["key"]:
            continue
        chain = roots.get(node["id"])
        answers = sorted({step["to"] for step in chain["steps"]}) if chain else []
        row = locked.setdefault((node["key"], node["tx"]), {
            "key": node["key"], "key_name": KEY_NAMES.get(node["key"]),
            "senders": [], "sector": node["sector"], "answers": answers})
        row["senders"].append(node["id"])

    # A lock is not always on a wire: a door pushed by hand that wants a key
    # sends and hears nothing, so the wiring never lists it. The city's one
    # key works exactly such a door, and it was read as a key for nothing.
    wired = {node["id"] for node in every}
    owners = None
    for kind, group in (("sector", disk.sectors), ("wall", disk.walls),
                        ("sprite", disk.sprites)):
        for index, item in enumerate(group):
            wants = int((record_extra(item) or {}).get("key", 0) or 0)
            if not wants or f"{kind} {index}" in wired:
                continue
            fields = record_fields(item)
            if kind == "sprite":
                if classify("sprite", int(fields["type"])).get("category") == "dude":
                    continue                      # a key it drops, not a lock
                sector = int(fields["sector"])
            elif kind == "sector":
                sector = index
            else:
                if owners is None:
                    from .sector_geom import wall_owners
                    owners = wall_owners(disk)
                sector = owners.get(index, -1)
            row = locked.setdefault((wants, -index - 1 if kind == "sector" else 0), {
                "key": wants, "key_name": KEY_NAMES.get(wants), "senders": [],
                "sector": sector,
                "answers": [f"{kind} {index}"] if kind == "sector" else []})
            row["senders"].append(f"{kind} {index}")
            row["by_hand"] = True

    declared = None
    credited = Counter()
    for node in every:
        if node["tx"] == SECRET_TOTAL_CHANNEL and node["command"] >= NUMERIC:
            declared = node["command"] - NUMERIC
        if node["tx"] == SECRET_FOUND_CHANNEL and node["command"] >= NUMERIC:
            credited["normal" if node["command"] == NUMERIC else "super"] += 1

    old = progression.get("sp_understand") or {}
    return {
        "map": name,
        "start_sector": progression.get("start_sector"),
        "space": len(space),
        "reached": sum(1 for sector in space if sector in reached),
        "unreached": [sector for sector in space if sector not in reached],
        "exits": exits,
        "exit_reached": any(row["reached"] for row in exits),
        #: the map as it is played: what is open from the start, and what
        #: each act opens (`bloodmap.conditional.frontier`)
        "gated_areas": [{"round": area["round"], "opened_by": area["opened_by"],
                         "sectors": len(area["sectors"]),
                         "first_sector": area["sectors"][0]}
                        for area in progression.get("gated_areas", ())],
        "keys": keys,
        "locked": sorted(locked.values(), key=lambda row: (row["key"], row["sector"])),
        "secrets": {"declared": declared, "credited_normal": credited["normal"],
                    "credited_super": credited["super"]},
        #: the older progression reader's answer, kept beside the newer one
        #: so the two can be seen to disagree
        "older_reader": {"final_reachable": old.get("final_reachable"),
                         "exit_reachable": old.get("exit_reachable")},
        "by_node": {"exists": len(by_id)},
    }


def missed(mark: dict[str, Any]) -> list[str]:
    """What the readers failed to find that a shipped map certainly has."""
    out = []
    if not mark["exits"]:
        out.append("no chain ends at the level's exit")
    elif not mark["exit_reached"]:
        out.append("the exit is never reached")
    wanted = {row["key"] for row in mark.get("locked", ())}
    names = {name: number for number, name in KEY_NAMES.items()}
    for row in mark["keys"]:
        said = row["name"].lower()
        number = next((names[name] for name in names if name in said), None)
        if number is not None and number not in wanted:
            out.append(f"{row['name']} opens nothing: no lock wants it")
            break
    lost = [row["name"] for row in mark["keys"] if not row["reached"]]
    if lost:
        out.append(f"{len(lost)} key(s) never reached: {', '.join(sorted(lost))}")
    if mark["unreached"]:
        out.append(f"{len(mark['unreached'])} of {mark['space']} player-space "
                   f"sectors never reached")
    secrets = mark["secrets"]
    if secrets["declared"] is None:
        if secrets["credited_normal"]:
            out.append("secrets are credited and the level declares no total")
    elif secrets["declared"] != secrets["credited_normal"]:
        out.append(f"the level declares {secrets['declared']} secrets and "
                   f"{secrets['credited_normal']} senders credit one")
    return out
