"""State-dependent single-player progression over Blood native mechanisms.

Physical walkability (spatial.walkable_at_rest) is not the same as allowed
progress. This module adds keys, RX-gated Z-motion, push-gated motion, and
exit channels. It does not tick NBlood interpolation.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from .analysis import channel_graph
from .blood_types import classify
from .build_ir import BuildIR
from .contents import explain_mechanisms, inventory_map
from .format import read_map
from .model import DiskMap
from .spatial import analyze_spatial


SCHEMA = "llmapper.sp-progression"
SCHEMA_VERSION = 1
EXIT_CHANNELS = {4, 5}
KEY_TYPES = {100: 1, 101: 2, 102: 3, 103: 4, 104: 5, 105: 6, 106: 7}
SWITCH_TYPES = {20, 21, 22, 23}
MOTION_TYPES = {600, 602}


class ProgressionError(ValueError):
    pass


def _sid(ref: str) -> int:
    return int(str(ref).split(":", 1)[1])


def _start_sector(disk: DiskMap, inventory: dict[str, Any]) -> int:
    starts = inventory["starts"]["single_player"]
    if starts:
        return int(starts[0]["sector"])
    return int(disk.header["start_sector"])


def _portal_map(spatial: dict[str, Any]) -> tuple[dict[int, set[int]], dict[int, set[int]], dict[tuple[int, int], dict[str, Any]]]:
    rest: dict[int, set[int]] = defaultdict(set)
    gated: dict[int, set[int]] = defaultdict(set)
    edges: dict[tuple[int, int], dict[str, Any]] = {}
    trav = spatial["views"]["traversability"]
    for edge in trav["walkable_at_rest"]:
        a, b = _sid(edge["sectors"][0]), _sid(edge["sectors"][1])
        rest[a].add(b)
        rest[b].add(a)
        edges[(a, b)] = edge
        edges[(b, a)] = edge
    for edge in trav["blocked_or_state_dependent"]:
        a, b = _sid(edge["sectors"][0]), _sid(edge["sectors"][1])
        gated[a].add(b)
        gated[b].add(a)
        edges[(a, b)] = edge
        edges[(b, a)] = edge
    return rest, gated, edges


def _motion_receivers(disk: DiskMap) -> dict[int, list[int]]:
    by_rx: dict[int, list[int]] = defaultdict(list)
    for index, sector in enumerate(disk.sectors):
        extra = sector.extra.fields if sector.extra is not None else None
        type_id = int(sector.fields["type"])
        if extra is None:
            continue
        rx = int(extra.get("rx_id") or 0)
        if rx and type_id in MOTION_TYPES:
            by_rx[rx].append(index)
        elif rx and int(extra.get("off_ceiling_z") or 0) != int(extra.get("on_ceiling_z") or 0):
            by_rx[rx].append(index)
        elif rx and int(extra.get("off_floor_z") or 0) != int(extra.get("on_floor_z") or 0):
            by_rx[rx].append(index)
    return by_rx


def _push_sectors(disk: DiskMap) -> set[int]:
    found = set()
    for index, sector in enumerate(disk.sectors):
        extra = sector.extra.fields if sector.extra is not None else None
        if extra is None:
            continue
        if extra.get("trigger_push") or extra.get("trigger_wall_push"):
            if int(sector.fields["type"]) in MOTION_TYPES or extra.get("rx_id") == 0:
                found.add(index)
    return found


def _locked_sectors(disk: DiskMap) -> dict[int, int]:
    locked = {}
    for index, sector in enumerate(disk.sectors):
        extra = sector.extra.fields if sector.extra is not None else None
        if extra is None:
            continue
        key = int(extra.get("key") or 0)
        if key:
            locked[index] = key
    for index, wall in enumerate(disk.walls):
        extra = wall.extra.fields if wall.extra is not None else None
        if extra is None:
            continue
        key = int(extra.get("key") or 0)
        if not key:
            continue
        owner = int(wall.fields.get("sector", -1) or -1)
        nxt = int(wall.fields["next_sector"])
        if nxt >= 0:
            locked[nxt] = key
        if 0 <= owner:
            locked[owner] = key
    return locked


def _transmitters(disk: DiskMap) -> list[dict[str, Any]]:
    items = []
    for kind, objects in (("sprite", disk.sprites), ("wall", disk.walls), ("sector", disk.sectors)):
        for index, obj in enumerate(objects):
            extra = obj.extra.fields if obj.extra is not None else None
            if extra is None:
                continue
            tx = int(extra.get("tx_id") or 0)
            if not tx:
                continue
            sector = int(obj.fields["sector"]) if kind == "sprite" else (
                int(obj.fields.get("sector", 0) or 0) if kind == "wall" else index
            )
            if kind == "wall":
                # owner recovered from next/point; use first matching sector later
                sector = -1
            typed = classify(kind, int(obj.fields.get("type") or 0))
            items.append({
                "kind": kind,
                "id": index,
                "ref": f"{kind}:{index}",
                "tx_id": tx,
                "command": int(extra.get("command") or 0),
                "sector": sector,
                "type_id": int(obj.fields.get("type") or 0),
                "type_name": typed.get("name"),
                "triggers": [name for name, value in extra.items() if str(name).startswith("trigger_") and value],
                "is_switch": kind == "sprite" and int(obj.fields.get("type") or 0) in SWITCH_TYPES,
                "is_exit": tx in EXIT_CHANNELS,
            })
    return items


def _assign_wall_sectors(disk: DiskMap, transmitters: list[dict[str, Any]]) -> None:
    owners = [-1] * len(disk.walls)
    for sector_id, sector in enumerate(disk.sectors):
        first = int(sector.fields["wall_ptr"])
        count = int(sector.fields["wall_count"])
        for wall_id in range(first, first + count):
            owners[wall_id] = sector_id
    for item in transmitters:
        if item["kind"] == "wall" and 0 <= item["id"] < len(owners):
            item["sector"] = owners[item["id"]]


def _keys(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in inventory["pickups"] if item["category"] == "key"]


def _flood(start: set[int], rest: dict[int, set[int]], extra: dict[int, set[int]]) -> set[int]:
    seen = set(start)
    pending = deque(start)
    while pending:
        current = pending.popleft()
        for neighbor in rest[current] | extra[current]:
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return seen


def analyze_progression(
    disk: DiskMap,
    *,
    skip_tx_ids: set[int] | None = None,
    skip_key_ids: set[int] | None = None,
    include_pacing: bool = True,
) -> dict[str, Any]:
    """Derive a grounded SP progression graph. Ungrounded tricks stay unknown.

    ``include_pacing=False`` keeps the reachability witness and progression
    measurements while omitting the expensive player-space snapshots intended
    for interactive reports. Corpus indexing uses this mode because it needs
    measurements for every map, not a full route presentation for each one.
    """
    skip_tx_ids = set(skip_tx_ids or ())
    skip_key_ids = set(skip_key_ids or ())
    build = disk.to_build_ir()
    spatial = analyze_spatial(build)
    inventory = inventory_map(disk)
    mechanisms = explain_mechanisms(disk)
    rest, gated, _edges = _portal_map(spatial)
    receivers = _motion_receivers(disk)
    push = _push_sectors(disk)
    locked = _locked_sectors(disk)
    transmitters = _transmitters(disk)
    _assign_wall_sectors(disk, transmitters)
    keys = _keys(inventory)
    start = _start_sector(disk, inventory)
    from .player_space import inspect_space
    from .understanding import _compact_scale

    extra_open: dict[int, set[int]] = defaultdict(set)

    def open_sector(sector_id: int) -> None:
        for neighbor in gated[sector_id]:
            extra_open[sector_id].add(neighbor)
            extra_open[neighbor].add(sector_id)

    def snapshot(label: str, event: dict[str, Any] | None = None) -> dict[str, Any]:
        space = inspect_space(build, reached) if reached else None
        return {
            "label": label,
            "event": None if event is None else {
                key: event.get(key) for key in ("kind", "ref", "tx_id", "key", "is_exit", "newly_reachable", "sector")
                if event.get(key) is not None
            },
            "reachable_count": len(reached),
            "space": None if space is None else _compact_scale(space),
        }

    activated: set[int] = set()
    have_keys: set[int] = set()
    reached = _flood({start}, rest, extra_open)
    events: list[dict[str, Any]] = [{"kind": "spawn", "sector": start, "reachable": len(reached)}]
    steps = []
    pacing = [snapshot("spawn")] if include_pacing and not skip_tx_ids and not skip_key_ids else []
    changed = True
    safety = 0
    while changed and safety < 64:
        safety += 1
        changed = False
        # pick up keys
        for key in keys:
            kid = KEY_TYPES.get(int(key["type_id"]))
            if kid and kid in skip_key_ids:
                continue
            if kid and key["sector"] in reached and kid not in have_keys:
                have_keys.add(kid)
                events.append({"kind": "take-key", "type_id": key["type_id"], "sector": key["sector"], "key": kid, "reachable": len(reached)})
                if pacing:
                    pacing.append(snapshot("take-key", events[-1]))
                changed = True
        # key-gated motion
        for sector_id, key_id in locked.items():
            adjacent = sector_id in reached or any(
                sector_id in gated[item] or sector_id in rest[item] for item in reached
            )
            if key_id in have_keys and adjacent:
                before = len(reached)
                open_sector(sector_id)
                reached = _flood(reached, rest, extra_open)
                if len(reached) > before:
                    events.append({"kind": "unlock", "sector": sector_id, "key": key_id, "reachable": len(reached)})
                    if pacing:
                        pacing.append(snapshot("unlock", events[-1]))
                    changed = True
        # adjacent push motion
        for sector_id in push:
            if sector_id in locked and locked[sector_id] not in have_keys:
                continue
            adjacent = sector_id in reached or any(sector_id in gated[item] and item in reached for item in reached)
            if adjacent:
                before = len(reached)
                open_sector(sector_id)
                reached = _flood(reached, rest, extra_open)
                if len(reached) > before:
                    events.append({"kind": "push-motion", "sector": sector_id, "reachable": len(reached)})
                    if pacing:
                        pacing.append(snapshot("push-motion", events[-1]))
                    changed = True
        # switches / TX in reached sectors
        for tx in transmitters:
            if tx["tx_id"] in activated or tx["tx_id"] in skip_tx_ids:
                continue
            if tx["sector"] not in reached:
                continue
            if not (tx["is_switch"] or tx["kind"] in {"wall", "sector"} or "trigger_push" in tx["triggers"] or "trigger_enter" in tx["triggers"]):
                continue
            activated.add(tx["tx_id"])
            before = len(reached)
            for sector_id in receivers.get(tx["tx_id"], []):
                open_sector(sector_id)
            reached = _flood(reached, rest, extra_open)
            events.append({
                "kind": "activate",
                "ref": tx["ref"],
                "tx_id": tx["tx_id"],
                "is_exit": tx["is_exit"],
                "newly_reachable": len(reached) - before,
                "reachable": len(reached),
            })
            steps.append({
                "action": tx["ref"],
                "tx_id": tx["tx_id"],
                "reachable_count": len(reached),
            })
            if pacing and (tx["is_exit"] or len(reached) > before):
                pacing.append(snapshot("activate", events[-1]))
            changed = True
            break

    exit_ready = any(item["is_exit"] and item["tx_id"] in activated for item in transmitters)
    if not exit_ready:
        exit_ready = any(item["is_exit"] and item["sector"] in reached for item in transmitters)

    chains = []
    graph = channel_graph(disk)
    for channel in graph["channels"]:
        ch = channel["channel"]
        if not channel["transmitters"] or not channel["receivers"]:
            continue
        chains.append({
            "channel": ch,
            "transmitters": channel["transmitters"],
            "receivers": channel["receivers"],
            "exit": ch in EXIT_CHANNELS,
            "motion_receivers": receivers.get(ch, []),
        })

    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "model": "keys + RX Z-motion + push motion + TX in reached sectors; not a player simulator",
        "start_sector": start,
        "physical_reachable_at_rest": len(_flood({start}, rest, defaultdict(set))),
        "final_reachable": len(reached),
        "sector_count": len(disk.sectors),
        "keys_collected": sorted(have_keys),
        "channels_activated": sorted(activated),
        "exit_reachable": bool(exit_ready),
        "witness": events,
        "steps": steps,
        "pacing": pacing,
        "chains": chains,
        "transmitters": transmitters,
        "transmitter_count": len(transmitters),
        "motion_receivers": {str(k): v for k, v in receivers.items()},
        "push_sectors": sorted(push),
        "locked_sectors": {str(k): v for k, v in locked.items()},
        "limitations": [
            "destruction, one-shot walls, and undocumented types are not simulated",
            "opening a motion sector makes all its gated portals walkable",
            "secret exits (channel 5) are recorded but not required for completion",
        ],
    }


def classify_mechanisms(report: dict[str, Any], disk: DiskMap | None = None) -> dict[str, Any]:
    """Counterfactual when a DiskMap is supplied; otherwise witness-only roles."""
    if disk is not None:
        return classify_mechanisms_counterfactual(disk, report)
    required = []
    optional = []
    decorative = []
    exit_index = None
    for index, event in enumerate(report["witness"]):
        if event.get("kind") == "activate" and event.get("is_exit"):
            exit_index = index
            required.append({"ref": event.get("ref"), "role": "exit", "tx_id": event.get("tx_id")})
    for event in report["witness"]:
        if event.get("kind") != "activate" or event.get("is_exit"):
            continue
        record = {"ref": event.get("ref"), "tx_id": event.get("tx_id"), "newly_reachable": event.get("newly_reachable")}
        if event.get("newly_reachable", 0) > 0:
            required.append({**record, "role": "opens_space"})
        else:
            optional.append({**record, "role": "no_new_space_on_witness"})
    for tx in report["transmitters"]:
        used = any(event.get("ref") == tx["ref"] for event in report["witness"] if event.get("kind") == "activate")
        if not used and not tx["is_exit"]:
            decorative.append({"ref": tx["ref"], "tx_id": tx["tx_id"], "role": "never_on_witness"})
    return {
        "required": required,
        "optional": optional,
        "decorative_or_unreached": decorative,
        "exit_event_index": exit_index,
        "notes": [
            "required means the witness used it to grow reachability or to fire the exit",
            "optional/decorative is not a proof the player cannot use it",
            "pass disk= to re-solve with each activated channel dropped",
        ],
    }


def classify_mechanisms_counterfactual(disk: DiskMap, report: dict[str, Any]) -> dict[str, Any]:
    """Drop each activated channel (and each collected key) and re-solve exit reachability."""
    required = []
    optional = []
    decorative = []
    for tx_id in report["channels_activated"]:
        alt = analyze_progression(disk, skip_tx_ids={tx_id})
        record = {
            "tx_id": tx_id,
            "exit_without": alt["exit_reachable"],
            "final_without": alt["final_reachable"],
            "final_with": report["final_reachable"],
        }
        if report["exit_reachable"] and not alt["exit_reachable"]:
            required.append({**record, "role": "required_for_exit"})
        elif alt["final_reachable"] < report["final_reachable"]:
            optional.append({**record, "role": "optional_space"})
        else:
            decorative.append({**record, "role": "no_progression_effect"})
    for key_id in report["keys_collected"]:
        alt = analyze_progression(disk, skip_key_ids={key_id})
        record = {
            "key": key_id,
            "exit_without": alt["exit_reachable"],
            "final_without": alt["final_reachable"],
        }
        if report["exit_reachable"] and not alt["exit_reachable"]:
            required.append({**record, "role": "required_key"})
        elif alt["final_reachable"] < report["final_reachable"]:
            optional.append({**record, "role": "optional_key"})
        else:
            decorative.append({**record, "role": "unused_key"})
    unused = [
        {"ref": tx["ref"], "tx_id": tx["tx_id"], "role": "never_on_witness"}
        for tx in report["transmitters"]
        if tx["tx_id"] not in report["channels_activated"] and not tx["is_exit"]
    ]
    return {
        "required": required,
        "optional": optional,
        "decorative_or_unreached": unused[:40],
        "decorative_or_unreached_count": len(unused) + sum(1 for item in decorative if item.get("role") == "no_progression_effect"),
        "no_progression_effect": decorative,
        "method": "re-solve with each activated channel or collected key dropped",
        "notes": [
            "required_for_exit means dropping that channel/key makes the exit unreachable in this model",
            "optional_space still reaches the exit but with fewer sectors",
            "destruction and undocumented types remain unmodeled",
        ],
    }


def completion_witness(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "coherent": bool(report["exit_reachable"]),
        "start_sector": report["start_sector"],
        "events": report["witness"],
        "keys_collected": report["keys_collected"],
        "channels_activated": report["channels_activated"],
        "final_reachable": report["final_reachable"],
        "physical_reachable_at_rest": report["physical_reachable_at_rest"],
    }


def _chain_kind(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("kind") or "unknown")
    text = str(item)
    return text.split(":", 1)[0] if ":" in text else text


def _chain_signature(chain: dict[str, Any]) -> str:
    n_tx = len(chain.get("transmitters") or [])
    n_rx = len(chain.get("receivers") or [])
    motion = 1 if chain.get("motion_receivers") else 0
    exit_flag = 1 if chain.get("exit") else 0
    kinds = sorted({_chain_kind(item) for item in (chain.get("transmitters") or [])})
    return f"tx{n_tx}|rx{n_rx}|motion{motion}|exit{exit_flag}|{'+'.join(kinds) or 'none'}"


def compact_progression_report(report: dict[str, Any]) -> dict[str, Any]:
    """Drop bulky native listings while keeping the witness and roles."""
    payload = dict(report)
    payload.pop("transmitters", None)
    chains = []
    for chain in payload.get("chains") or []:
        chains.append({
            "channel": chain["channel"],
            "exit": chain.get("exit"),
            "transmitter_count": len(chain.get("transmitters") or []),
            "receiver_count": len(chain.get("receivers") or []),
            "motion_receivers": chain.get("motion_receivers") or [],
            "transmitter_kinds": sorted({_chain_kind(item) for item in (chain.get("transmitters") or [])}),
            "signature": _chain_signature(chain),
        })
    payload["chains"] = chains
    roles = payload.get("roles")
    if isinstance(roles, dict) and "decorative_or_unreached" in roles:
        items = roles["decorative_or_unreached"]
        roles = dict(roles)
        roles["decorative_or_unreached_count"] = roles.get("decorative_or_unreached_count", len(items))
        roles["decorative_or_unreached"] = items[:12]
        payload["roles"] = roles
    return payload


def pacing_along_witness(disk: DiskMap, report: dict[str, Any]) -> list[dict[str, Any]]:
    if report.get("pacing"):
        return list(report["pacing"])
    return analyze_progression(disk)["pacing"]
