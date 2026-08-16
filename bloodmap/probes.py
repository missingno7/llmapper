"""Design Probe implementations.

Each probe is a replayable, bounded, deterministic question about a level.
Probes use the state model (PlayerState, WorldState, PlayerKnowledge) and
the BuildIR to answer specific design questions.

Fidelity levels:
  L0 — graph/state reasoning (this implementation)
  L1 — spatial traversal with player dimensions (partially implemented)
  L2 — perceptual traversal (visibility, landmarks) (partially implemented)
  L3 — abstract gameplay reasoning (architectural only, not implemented)

Evidence classification:
  Every probe result includes evidence with source classification:
    - static_exact: derived from exact map structure
    - static_approximate: derived from approximate static analysis
    - semantic_simulation: derived from semantic mechanism model
    - real_engine: derived from real engine runtime oracle
"""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any

from .build_ir import BuildIR
from .probe_schema import (
    EVIDENCE_SEMANTIC_SIMULATION,
    EVIDENCE_STATIC_APPROXIMATE,
    EVIDENCE_STATIC_EXACT,
    Evidence,
    ProbeError,
    ProbeResult,
    register_probe,
)
from .state_model import PlayerKnowledge, PlayerState, WorldState


# ---------------------------------------------------------------------------
# Traversal graph construction
# ---------------------------------------------------------------------------

def _sector_ref(sector_id: int) -> str:
    return f"sector:{sector_id}"


def _parse_ref(ref: str | int) -> int:
    if isinstance(ref, int):
        return ref
    prefix, value = ref.split(":", 1)
    if prefix != "sector":
        raise ProbeError(f"expected sector reference, got {ref!r}")
    return int(value)


def _build_traversal_graph(
    build: BuildIR,
    world_state: WorldState,
) -> tuple[dict[int, set[int]], dict[frozenset[int], dict[str, Any]]]:
    """Build a traversal graph from BuildIR geometry and world state.

    Returns:
        graph: adjacency list of sector_id -> set of reachable sector_ids
        edges: map of frozenset({left, right}) -> edge metadata
    """
    from .spatial import analyze_spatial

    analysis = analyze_spatial(build)
    views = analysis["views"]

    graph: dict[int, set[int]] = defaultdict(set)
    edges: dict[frozenset[int], dict[str, Any]] = {}

    # Walkable at-rest edges
    for edge in views["traversability"]["walkable_at_rest"]:
        left, right = (_parse_ref(s) for s in edge["sectors"])
        graph[left].add(right)
        graph[right].add(left)
        edges[frozenset((left, right))] = {"kind": "portal", **edge}

    # Known non-portal transitions (water links, teleporters)
    for edge in views["traversability"]["known_non_portal_transitions"]:
        left, right = (_parse_ref(s) for s in edge["sectors"])
        graph[left].add(right)
        graph[right].add(left)
        edges[frozenset((left, right))] = {"kind": "known_non_portal_transition", **edge}

    # Opened portals (from world state)
    for edge in views["traversability"]["blocked_or_state_dependent"]:
        if edge["id"] not in world_state.opened_portals:
            continue
        left, right = (_parse_ref(s) for s in edge["sectors"])
        graph[left].add(right)
        graph[right].add(left)
        edges[frozenset((left, right))] = {
            "kind": "world_state_override",
            "assumption": "caller declared this portal opened",
            **edge,
        }

    # Enabled routes (from world state)
    for route_id in world_state.enabled_routes:
        # Route IDs can reference specific connections
        # For now, we treat them as additional opened portals
        pass

    return graph, edges


def _shortest_path(
    graph: dict[int, set[int]],
    start: int,
    target: int,
) -> list[int] | None:
    """BFS shortest path from start to target."""
    if start == target:
        return [start]
    pending = deque([start])
    parent: dict[int, int | None] = {start: None}
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


def _bfs_reachable(graph: dict[int, set[int]], start: int) -> set[int]:
    """BFS to find all reachable sectors from start."""
    reached = {start}
    pending = deque([start])
    while pending:
        current = pending.popleft()
        for neighbor in sorted(graph[current] - reached):
            reached.add(neighbor)
            pending.append(neighbor)
    return reached


def _get_sector_geometry(build: BuildIR, sector_id: int) -> dict[str, Any]:
    """Get geometry metrics for a sector."""
    from .design import _polygon_loops, _signed_area

    loops = _polygon_loops(build, sector_id)
    points = [point for loop in loops for point in loop]
    fields = build.sectors[sector_id]["fields"]
    return {
        "area": round(abs(sum(_signed_area(loop) for loop in loops)), 3),
        "floor_z": int(fields["floor_z"]),
        "ceiling_z": int(fields["ceiling_z"]),
        "clear_height": int(fields["floor_z"]) - int(fields["ceiling_z"]),
        "wall_loop_count": len(loops),
        "bounds": {
            "min_x": min(p[0] for p in points),
            "min_y": min(p[1] for p in points),
            "max_x": max(p[0] for p in points),
            "max_y": max(p[1] for p in points),
        },
    }


# ---------------------------------------------------------------------------
# Probe: access
# ---------------------------------------------------------------------------

@register_probe("access")
def probe_access(probe, build: BuildIR) -> ProbeResult:
    """Can the player reach X under world state Y?

    Returns:
        reachable: bool
        blocking reasons: list of strings
        required keys: list of key IDs needed
        required mechanisms: list of mechanism IDs that need to be activated
        candidate route: compressed sector path
    """
    params = probe.parameters
    target_sector = _parse_ref(params.get("target_sector", params.get("target", 0)))
    start_sector = int(probe.player_state.sector)

    graph, edges = _build_traversal_graph(build, probe.world_state)
    path = _shortest_path(graph, start_sector, target_sector)

    result = ProbeResult(
        probe_type="access",
        status="inconclusive",
        question=probe.question or f"Can the player reach sector:{target_sector}?",
        fidelity_level="L0",
        limitations=[
            "L0 graph reasoning only; does not simulate player movement, slopes, or combat",
            "Does not infer key ownership, switch order, or dynamic mechanism behavior",
        ],
    )

    if path is not None:
        result.status = "pass"
        result.answer = f"sector:{target_sector} is reachable from sector:{start_sector}"
        result.route = path
        result.evidence.append(Evidence(
            claim=f"Path found with {len(path) - 1} steps from sector:{start_sector} to sector:{target_sector}",
            source=EVIDENCE_STATIC_EXACT,
            confidence="high",
        ))
    else:
        result.status = "fail"
        result.answer = f"sector:{target_sector} is not reachable from sector:{start_sector} under the declared world state"
        result.blocking_reasons.append(f"No path from sector:{start_sector} to sector:{target_sector}")
        result.evidence.append(Evidence(
            claim=f"No path found from sector:{start_sector} to sector:{target_sector}",
            source=EVIDENCE_STATIC_EXACT,
            confidence="high",
        ))

    return result


# ---------------------------------------------------------------------------
# Probe: route
# ---------------------------------------------------------------------------

@register_probe("route")
def probe_route(probe, build: BuildIR) -> ProbeResult:
    """What is a plausible traversable route from A to B?

    Returns a compressed route, not thousands of micro-steps.
    """
    params = probe.parameters
    start_sector = int(probe.player_state.sector)
    target_sector = _parse_ref(params.get("target_sector", params.get("target", 0)))

    graph, edges = _build_traversal_graph(build, probe.world_state)
    path = _shortest_path(graph, start_sector, target_sector)

    result = ProbeResult(
        probe_type="route",
        status="inconclusive",
        question=probe.question or f"Route from sector:{start_sector} to sector:{target_sector}",
        fidelity_level="L0",
        limitations=[
            "Route is a static graph shortest path, not a player movement recording",
            "Does not simulate slopes, step height, or vertical clearance",
        ],
    )

    if path is not None:
        result.status = "pass"
        result.answer = f"Route found with {len(path) - 1} steps"
        result.route = path

        # Collect mechanisms required along the route
        for i in range(len(path) - 1):
            edge_key = frozenset((path[i], path[i + 1]))
            if edge_key in edges:
                edge = edges[edge_key]
                if edge.get("kind") == "world_state_override":
                    result.required_mechanisms.append(edge["id"])
                    result.state_changes.append({
                        "type": "portal_opened",
                        "portal": edge["id"],
                        "sectors": edge.get("sectors", []),
                    })

        result.evidence.append(Evidence(
            claim=f"Route has {len(path)} sectors, {len(result.required_mechanisms)} required mechanisms",
            source=EVIDENCE_STATIC_EXACT,
            confidence="high",
        ))
    else:
        result.status = "fail"
        result.answer = f"No route from sector:{start_sector} to sector:{target_sector}"
        result.blocking_reasons.append("No path found in traversal graph")
        result.evidence.append(Evidence(
            claim="No path found in traversal graph",
            source=EVIDENCE_STATIC_EXACT,
            confidence="high",
        ))

    return result


# ---------------------------------------------------------------------------
# Probe: progression
# ---------------------------------------------------------------------------

@register_probe("progression")
def probe_progression(probe, build: BuildIR) -> ProbeResult:
    """Analyze known progression dependencies.

    Returns:
        initial reachable region
        locked objectives
        key/switch dependencies
        state transitions
        exit reachability
        potential sequence breaks
    """
    start_sector = int(probe.player_state.sector)

    graph, edges = _build_traversal_graph(build, probe.world_state)
    reachable = _bfs_reachable(graph, start_sector)

    all_sectors = set(range(len(build.sectors)))
    unreachable = all_sectors - reachable

    result = ProbeResult(
        probe_type="progression",
        status="pass",
        question=probe.question or "What is the progression structure?",
        fidelity_level="L0",
        limitations=[
            "Does not infer key ownership, switch order, or dynamic mechanism behavior",
            "State transitions are identified but not simulated",
        ],
    )

    result.measurements = {
        "initial_reachable_count": len(reachable),
        "unreachable_count": len(unreachable),
        "total_sectors": len(all_sectors),
        "reachable_sectors": [_sector_ref(s) for s in sorted(reachable)],
        "unreachable_sectors": [_sector_ref(s) for s in sorted(unreachable)],
    }

    result.evidence.append(Evidence(
        claim=f"{len(reachable)} sectors reachable initially, {len(unreachable)} unreachable",
        source=EVIDENCE_STATIC_EXACT,
        confidence="high",
    ))

    return result


# ---------------------------------------------------------------------------
# Probe: transition
# ---------------------------------------------------------------------------

@register_probe("transition")
def probe_transition(probe, build: BuildIR) -> ProbeResult:
    """Compare two sides of a traversal transition.

    Measures differences such as:
        - area ratio
        - clear height delta
        - navigation choices delta
        - opening width
        - material family
        - shade/brightness
        - vertical range
    """
    params = probe.parameters
    source_sector = _parse_ref(params.get("source_sector", params.get("source", 0)))
    dest_sector = _parse_ref(params.get("destination_sector", params.get("destination", 0)))

    source_geom = _get_sector_geometry(build, source_sector)
    dest_geom = _get_sector_geometry(build, dest_sector)

    area_ratio = round(dest_geom["area"] / max(1.0, source_geom["area"]), 4)
    height_delta = dest_geom["clear_height"] - source_geom["clear_height"]
    floor_delta = dest_geom["floor_z"] - source_geom["floor_z"]

    result = ProbeResult(
        probe_type="transition",
        status="pass",
        question=probe.question or f"Transition from sector:{source_sector} to sector:{dest_sector}",
        fidelity_level="L1",
        limitations=[
            "Measurements are based on sector geometry, not renderer views",
            "Area ratio uses polygon area, not perceived spatial extent",
        ],
    )

    result.measurements = {
        "area_ratio": area_ratio,
        "clear_height_delta": height_delta,
        "floor_delta": floor_delta,
        "source_area": source_geom["area"],
        "dest_area": dest_geom["area"],
        "source_clear_height": source_geom["clear_height"],
        "dest_clear_height": dest_geom["clear_height"],
    }

    # Identify transition type
    if area_ratio >= 2.0 or height_delta >= 4096:
        result.state_changes.append({
            "type": "spatial_expansion",
            "area_ratio": area_ratio,
            "height_delta": height_delta,
        })
        result.evidence.append(Evidence(
            claim=f"Strong spatial expansion: area ratio {area_ratio}, height delta {height_delta}",
            source=EVIDENCE_STATIC_EXACT,
            confidence="high",
        ))
    elif area_ratio <= 0.5 or height_delta <= -4096:
        result.state_changes.append({
            "type": "spatial_contraction",
            "area_ratio": area_ratio,
            "height_delta": height_delta,
        })
        result.evidence.append(Evidence(
            claim=f"Strong spatial contraction: area ratio {area_ratio}, height delta {height_delta}",
            source=EVIDENCE_STATIC_EXACT,
            confidence="high",
        ))

    return result


# ---------------------------------------------------------------------------
# Probe: visibility
# ---------------------------------------------------------------------------

@register_probe("visibility")
def probe_visibility(probe, build: BuildIR) -> ProbeResult:
    """Is target T visible from this route or from these approach positions?

    Initially uses conservative geometry-derived approximations plus
    optional real-engine samples.

    Returns evidence such as:
        - first observed at X% of route
        - visible from N/M sampled decision points
        - lost from view after transition X
    """
    params = probe.parameters
    start_sector = int(probe.player_state.sector)
    target_sector = _parse_ref(params.get("target_sector", params.get("target", 0)))

    graph, edges = _build_traversal_graph(build, probe.world_state)
    path = _shortest_path(graph, start_sector, target_sector)

    result = ProbeResult(
        probe_type="visibility",
        status="inconclusive",
        question=probe.question or f"Is sector:{target_sector} visible from sector:{start_sector}?",
        fidelity_level="L2",
        limitations=[
            "Visibility is approximated using direct portal adjacency",
            "No renderer, occlusion, view angle, or landmark recognition",
            "Does not pretend to solve human perception exactly",
        ],
    )

    if path is None:
        result.status = "fail"
        result.answer = f"sector:{target_sector} is not reachable from sector:{start_sector}"
        result.blocking_reasons.append("Target is not reachable")
        return result

    # Check direct portal visibility along the route
    visible_at: list[int] = []
    for i, sector_id in enumerate(path):
        if sector_id == target_sector:
            visible_at.append(i)
            continue
        # Check if target is a direct portal neighbor
        neighbors = graph.get(sector_id, set())
        if target_sector in neighbors:
            visible_at.append(i)

    if visible_at:
        first = min(visible_at)
        result.status = "pass"
        result.answer = f"sector:{target_sector} is visible at {first} steps ({round(first / max(1, len(path) - 1) * 100)}% of route)"
        result.route = path
        result.measurements = {
            "first_visible_step": first,
            "route_fraction": round(first / max(1, len(path) - 1), 4),
            "visible_at_steps": visible_at,
            "total_steps": len(path) - 1,
        }
        result.evidence.append(Evidence(
            claim=f"Target first visible at step {first} ({round(first / max(1, len(path) - 1) * 100)}% of route)",
            source=EVIDENCE_STATIC_APPROXIMATE,
            confidence="medium",
        ))
    else:
        result.status = "fail"
        result.answer = f"sector:{target_sector} is not visible along the route"
        result.blocking_reasons.append("No direct portal visibility found")

    return result


# ---------------------------------------------------------------------------
# Probe: revisit
# ---------------------------------------------------------------------------

@register_probe("revisit")
def probe_revisit(probe, build: BuildIR) -> ProbeResult:
    """Compare the same area in different world/knowledge states.

    Example:
        before key acquisition
        after key acquisition

    Useful output:
        - new paths
        - changed mechanisms
        - new visibility
        - changed route choices
        - known-vs-new landmarks
    """
    params = probe.parameters
    start_sector = int(probe.player_state.sector)
    target_sector = _parse_ref(params.get("target_sector", params.get("target", 0)))

    # Build graph for current world state
    graph_before, edges_before = _build_traversal_graph(build, probe.world_state)
    reachable_before = _bfs_reachable(graph_before, start_sector)

    # Build graph for alternate world state (if provided)
    alt_world_state = WorldState.from_dict(params.get("alt_world_state", {}))
    graph_after, edges_after = _build_traversal_graph(build, alt_world_state)
    reachable_after = _bfs_reachable(graph_after, start_sector)

    newly_reachable = reachable_after - reachable_before
    still_unreachable = (set(range(len(build.sectors))) - reachable_after) - reachable_before

    result = ProbeResult(
        probe_type="revisit",
        status="pass",
        question=probe.question or f"Revisit comparison for sector:{target_sector}",
        fidelity_level="L0",
        limitations=[
            "Comparison is based on graph reachability, not player movement",
            "Does not simulate dynamic mechanism state changes",
        ],
    )

    result.measurements = {
        "reachable_before_count": len(reachable_before),
        "reachable_after_count": len(reachable_after),
        "newly_reachable_count": len(newly_reachable),
        "newly_reachable_sectors": [_sector_ref(s) for s in sorted(newly_reachable)],
        "still_unreachable_count": len(still_unreachable),
    }

    if newly_reachable:
        result.state_changes.append({
            "type": "new_paths_opened",
            "count": len(newly_reachable),
            "sectors": [_sector_ref(s) for s in sorted(newly_reachable)],
        })
        result.evidence.append(Evidence(
            claim=f"{len(newly_reachable)} new sectors became reachable",
            source=EVIDENCE_STATIC_EXACT,
            confidence="high",
        ))

    return result


# ---------------------------------------------------------------------------
# Probe: escape
# ---------------------------------------------------------------------------

@register_probe("escape")
def probe_escape(probe, build: BuildIR) -> ProbeResult:
    """Given a position/region and world state, determine available traversal options.

    Returns things such as:
        - number of viable exits
        - blocked exits
        - dead-end depth
        - routes requiring passing through same bottleneck

    Does not simulate combat.
    """
    params = probe.parameters
    start_sector = int(probe.player_state.sector)

    graph, edges = _build_traversal_graph(build, probe.world_state)

    # Find all exits from the current sector
    neighbors = sorted(graph.get(start_sector, set()))
    viable_exits = []
    blocked_exits = []

    for neighbor in neighbors:
        edge_key = frozenset((start_sector, neighbor))
        edge = edges.get(edge_key, {})
        if edge.get("kind") == "world_state_override":
            # This exit was opened by world state
            viable_exits.append({
                "sector": _sector_ref(neighbor),
                "edge": edge.get("id", ""),
                "status": "open_via_world_state",
            })
        elif edge.get("kind") == "known_non_portal_transition":
            viable_exits.append({
                "sector": _sector_ref(neighbor),
                "edge": edge.get("id", ""),
                "status": "transition",
            })
        else:
            viable_exits.append({
                "sector": _sector_ref(neighbor),
                "edge": edge.get("id", ""),
                "status": "open",
            })

    # Check for dead-end depth (how deep can you go from start without branching)
    dead_end_depth = 0
    current = start_sector
    visited = {start_sector}
    while True:
        next_neighbors = sorted(graph.get(current, set()) - visited)
        if len(next_neighbors) != 1:
            break
        current = next_neighbors[0]
        visited.add(current)
        dead_end_depth += 1

    result = ProbeResult(
        probe_type="escape",
        status="pass",
        question=probe.question or f"Escape options from sector:{start_sector}",
        fidelity_level="L0",
        limitations=[
            "Does not simulate combat, enemy positions, or resource pressure",
            "Dead-end depth is based on graph topology, not actual player movement",
        ],
    )

    result.measurements = {
        "viable_exit_count": len(viable_exits),
        "viable_exits": viable_exits,
        "blocked_exit_count": len(blocked_exits),
        "blocked_exits": blocked_exits,
        "dead_end_depth": dead_end_depth,
    }

    result.evidence.append(Evidence(
        claim=f"{len(viable_exits)} viable exits, dead-end depth {dead_end_depth}",
        source=EVIDENCE_STATIC_EXACT,
        confidence="high",
    ))

    return result
