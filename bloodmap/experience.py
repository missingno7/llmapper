"""Bounded, replayable Level-0 experience probes.

This is intentionally not a replacement engine.  It turns the derived spatial
views into concise route, access, transition, visibility, and progression probes
that expose assumptions and preserve world state separately from player knowledge.
"""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any, Iterable

from .build_ir import BuildIR
from .spatial import SpatialAnalysisError, analyze_spatial


class ExperienceProbeError(SpatialAnalysisError):
    """A bounded experience probe could not be formed safely."""


def _ref(sector_id: int) -> str:
    return f"sector:{sector_id}"


def _id(ref: str | int) -> int:
    if isinstance(ref, int):
        return ref
    try:
        prefix, value = ref.split(":", 1)
    except ValueError as exc:
        raise ExperienceProbeError(f"invalid sector reference {ref!r}") from exc
    if prefix != "sector":
        raise ExperienceProbeError(f"expected sector reference, got {ref!r}")
    return int(value)


def _world_state(value: dict[str, Any] | None) -> dict[str, Any]:
    value = value or {}
    opened = sorted({str(item) for item in value.get("opened_portals", [])})
    active = sorted({str(item) for item in value.get("activated_mechanisms", [])})
    unknown = sorted(set(value) - {"opened_portals", "activated_mechanisms", "notes"})
    if unknown:
        raise ExperienceProbeError(f"unsupported Level-0 world-state fields: {unknown}")
    result = {"opened_portals": opened, "activated_mechanisms": active}
    if "notes" in value:
        result["notes"] = str(value["notes"])
    return result


def _knowledge(value: dict[str, Any] | None) -> dict[str, Any]:
    value = value or {}
    allowed = {"seen_sectors", "known_landmarks", "known_locked_routes", "notes"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ExperienceProbeError(f"unsupported player-knowledge fields: {unknown}")
    result = {
        "seen_sectors": sorted({_id(item) for item in value.get("seen_sectors", [])}),
        "known_landmarks": sorted({str(item) for item in value.get("known_landmarks", [])}),
        "known_locked_routes": sorted({str(item) for item in value.get("known_locked_routes", [])}),
    }
    if "notes" in value:
        result["notes"] = str(value["notes"])
    return result


def _views(build: BuildIR) -> tuple[dict[str, Any], dict[str, Any]]:
    analysis = analyze_spatial(build)
    return analysis, analysis["views"]


def _edge_pairs(edges: Iterable[dict[str, Any]]) -> dict[frozenset[int], dict[str, Any]]:
    result = {}
    for edge in edges:
        sectors = [_id(item) for item in edge["sectors"]]
        if len(sectors) == 2:
            result[frozenset(sectors)] = edge
    return result


def _traversal_graph(views: dict[str, Any], state: dict[str, Any]) -> tuple[dict[int, set[int]], dict[frozenset[int], dict[str, Any]]]:
    graph: dict[int, set[int]] = defaultdict(set)
    edges: dict[frozenset[int], dict[str, Any]] = {}
    for edge in views["traversability"]["walkable_at_rest"]:
        left, right = (_id(item) for item in edge["sectors"])
        graph[left].add(right); graph[right].add(left)
        edges[frozenset((left, right))] = {"kind": "portal", **edge}
    for edge in views["traversability"]["known_non_portal_transitions"]:
        left, right = (_id(item) for item in edge["sectors"])
        graph[left].add(right); graph[right].add(left)
        edges[frozenset((left, right))] = {"kind": "known_non_portal_transition", **edge}
    opened = set(state["opened_portals"])
    for edge in views["traversability"]["blocked_or_state_dependent"]:
        if edge["id"] not in opened:
            continue
        left, right = (_id(item) for item in edge["sectors"])
        graph[left].add(right); graph[right].add(left)
        edges[frozenset((left, right))] = {
            "kind": "world_state_override", "assumption": "caller declared this portal opened", **edge,
        }
    return graph, edges


def _shortest_path(graph: dict[int, set[int]], start: int, target: int) -> list[int] | None:
    if start == target:
        return [start]
    pending = deque([start])
    parent = {start: None}
    while pending:
        current = pending.popleft()
        for neighbor in sorted(graph[current]):
            if neighbor in parent:
                continue
            parent[neighbor] = current
            if neighbor == target:
                result = [target]
                while parent[result[-1]] is not None:
                    result.append(parent[result[-1]])
                return list(reversed(result))
            pending.append(neighbor)
    return None


def _sector_nodes(build: BuildIR, views: dict[str, Any]) -> dict[int, dict[str, Any]]:
    geometry = {_id(item["ref"]): item for item in views["geometry"]["sectors"]}
    sprites: dict[int, list[str]] = defaultdict(list)
    for sprite_id, sprite in enumerate(build.sprites):
        sprites[int(sprite["fields"]["sector"])].append(f"sprite:{sprite_id}")
    material_edges = _edge_pairs(views["material"]["portal_continuity"])
    visibility_edges = _edge_pairs(views["visibility"]["candidates"])
    portal_edges = _edge_pairs(views["geometry"]["portals"])
    result = {}
    for sector_id, item in geometry.items():
        bounds = item["bounds"]
        result[sector_id] = {
            "sector": _ref(sector_id),
            "pose": {
                "x": round((bounds["min_x"] + bounds["max_x"]) / 2, 3),
                "y": round((bounds["min_y"] + bounds["max_y"]) / 2, 3),
                "z": item["floor_z"], "basis": "sector XY bounding-box center and floor Z",
            },
            "space": {
                key: item[key] for key in ("area", "clear_height", "floor_z", "ceiling_z", "wall_loop_count")
            },
            "entity_refs": sprites.get(sector_id, [])[:32],
            "entity_refs_truncated": len(sprites.get(sector_id, [])) > 32,
            "direct_portal_neighbors": [], "direct_visibility_candidates": [],
            "material_continuity": [],
        }
    for pair, edge in portal_edges.items():
        left, right = sorted(pair)
        result[left]["direct_portal_neighbors"].append({"sector": _ref(right), "portal": edge["id"]})
        result[right]["direct_portal_neighbors"].append({"sector": _ref(left), "portal": edge["id"]})
    for pair, edge in visibility_edges.items():
        left, right = sorted(pair)
        result[left]["direct_visibility_candidates"].append({"sector": _ref(right), "portal": edge["id"]})
        result[right]["direct_visibility_candidates"].append({"sector": _ref(left), "portal": edge["id"]})
    for pair, edge in material_edges.items():
        left, right = sorted(pair)
        result[left]["material_continuity"].append({"sector": _ref(right), **edge})
        result[right]["material_continuity"].append({"sector": _ref(left), **edge})
    for node in result.values():
        for name in ("direct_portal_neighbors", "direct_visibility_candidates", "material_continuity"):
            node[name].sort(key=lambda item: item["sector"])
    return result


def _node(node: dict[str, Any], graph: dict[int, set[int]], sector_id: int) -> dict[str, Any]:
    value = deepcopy(node[sector_id])
    value["navigation_choices"] = len(graph[sector_id])
    return value


def probe_route(
    build: BuildIR, start: int | str, target: int | str, *,
    world_state: dict[str, Any] | None = None, player_knowledge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Probe a shortest Level-0 traversal route under explicit state assumptions."""
    start_id, target_id = _id(start), _id(target)
    analysis, views = _views(build)
    if start_id not in {_id(value) for value in analysis["sector_ids"]} or target_id not in {_id(value) for value in analysis["sector_ids"]}:
        raise ExperienceProbeError("route sector is out of range")
    state, knowledge = _world_state(world_state), _knowledge(player_knowledge)
    graph, edge_map = _traversal_graph(views, state)
    path = _shortest_path(graph, start_id, target_id)
    nodes = _sector_nodes(build, views)
    blocked = [edge for edge in views["traversability"]["blocked_or_state_dependent"] if start_id in {_id(value) for value in edge["sectors"]}]
    if path is None:
        return {
            "$schema": "bloodmap.experience-probe", "schema_version": 1, "probe": "route",
            "status": "unreachable_under_declared_state", "from": _ref(start_id), "to": _ref(target_id),
            "world_state": state, "player_knowledge": knowledge,
            "local_state_change_candidates": [{"portal": edge["id"], "reasons": edge["reasons"]} for edge in blocked],
            "limitations": ["Level-0 does not simulate switches, locks, doors, lifts, slopes, or combat"],
        }
    transitions = []
    for left, right in zip(path, path[1:]):
        transitions.append({
            "from": _ref(left), "to": _ref(right),
            "edge": edge_map[frozenset((left, right))],
        })
    after = deepcopy(knowledge)
    after["seen_sectors"] = sorted(set(after["seen_sectors"]) | set(path))
    return {
        "$schema": "bloodmap.experience-probe", "schema_version": 1, "probe": "route", "status": "reachable",
        "from": _ref(start_id), "to": _ref(target_id), "world_state": state,
        "player_knowledge_before": knowledge, "player_knowledge_after": after,
        "path": [_ref(value) for value in path], "step_count": len(path) - 1,
        "experience_nodes": [_node(nodes, graph, value) for value in path], "transitions": transitions,
        "state_change_candidates_encountered": [
            {"portal": edge["id"], "sectors": edge["sectors"], "reasons": edge["reasons"]}
            for edge in views["traversability"]["blocked_or_state_dependent"]
            if any(_id(ref) in path for ref in edge["sectors"])
        ],
        "limitations": ["route is a static graph shortest path, not a player movement recording"],
    }


def probe_transition(
    build: BuildIR, source: int | str, destination: int | str, *, world_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare two adjacent experience nodes without naming a canonical room."""
    route = probe_route(build, source, destination, world_state=world_state)
    if route["status"] != "reachable" or route["step_count"] != 1:
        raise ExperienceProbeError("transition probe requires an adjacent reachable pair under the declared state")
    before, after = route["experience_nodes"]
    area_ratio = round(after["space"]["area"] / max(1.0, before["space"]["area"]), 4)
    height_delta = after["space"]["clear_height"] - before["space"]["clear_height"]
    choices_delta = after["navigation_choices"] - before["navigation_choices"]
    candidates = []
    if area_ratio >= 2 or height_delta >= max(4096, before["space"]["clear_height"] * 0.5):
        candidates.append({
            "kind": "spatial_expansion_candidate", "basis": {
                "area_ratio": area_ratio, "clear_height_delta": height_delta,
            }, "status": "heuristic; renderer and trajectory evidence required",
        })
    if choices_delta >= 2:
        candidates.append({
            "kind": "route_choice_expansion_candidate", "basis": {"navigation_choices_delta": choices_delta},
            "status": "heuristic; choices may not all be meaningful to a player",
        })
    return {
        "$schema": "bloodmap.experience-probe", "schema_version": 1, "probe": "transition", "status": "observed",
        "from": route["from"], "to": route["to"], "world_state": route["world_state"],
        "before": before, "after": after,
        "measured_change": {
            "area_ratio": area_ratio, "clear_height_delta": height_delta,
            "navigation_choices_delta": choices_delta,
        },
        "perceptual_change_candidates": candidates,
        "limitations": ["Level-0 has no render, turn direction, occlusion, landmark, or threat perception"],
    }


def probe_visibility(
    build: BuildIR, source: int | str, target: int | str, *, world_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Probe direct-portal visibility along a bounded static route to a target sector."""
    route = probe_route(build, source, target, world_state=world_state)
    if route["status"] != "reachable":
        return {**route, "probe": "visibility", "visibility": "unavailable because target is unreachable"}
    target_ref = route["to"]
    visible_at = [
        index for index, node in enumerate(route["experience_nodes"])
        if any(item["sector"] == target_ref for item in node["direct_visibility_candidates"])
    ]
    first = min(visible_at) if visible_at else None
    return {
        "$schema": "bloodmap.experience-probe", "schema_version": 1, "probe": "visibility", "status": "observed",
        "from": route["from"], "target": target_ref, "world_state": route["world_state"],
        "route": route["path"], "first_direct_portal_candidate_step": first,
        "route_fraction": round(first / max(1, route["step_count"]), 4) if first is not None else None,
        "evidence": "direct shared portal with nonzero static opening only",
        "limitations": ["not renderer visibility; no rays, occlusion, view angle, or landmark recognition"],
    }


def probe_progression(build: BuildIR, *, world_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a concise static accessibility/state-change report from player start."""
    analysis, views = _views(build)
    state = _world_state(world_state)
    start = int(build.player_start["sector"])
    graph, _edges = _traversal_graph(views, state)
    reached = {start}
    pending = deque([start])
    while pending:
        current = pending.popleft()
        for neighbor in sorted(graph[current] - reached):
            reached.add(neighbor); pending.append(neighbor)
    all_sectors = {_id(value) for value in analysis["sector_ids"]}
    return {
        "$schema": "bloodmap.experience-probe", "schema_version": 1, "probe": "progression", "status": "observed",
        "world_state": state, "start_sector": _ref(start),
        "reachable_sectors": [_ref(value) for value in sorted(reached)],
        "unreachable_sectors": [_ref(value) for value in sorted(all_sectors - reached)],
        "state_change_candidates": [
            {"portal": edge["id"], "sectors": edge["sectors"], "reasons": edge["reasons"]}
            for edge in views["traversability"]["blocked_or_state_dependent"]
        ],
        "mechanism_candidates": views["progression"]["mechanism_state_candidates"],
        "limitations": ["does not infer key ownership, switch order, or dynamic mechanism behavior"],
    }
