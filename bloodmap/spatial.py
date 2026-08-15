"""Independent, derived spatial views for Build-engine maps.

This module deliberately does *not* define a canonical room graph.  It exposes
several partial views over the same sectors and emits overlapping hypotheses
whose evidence can be inspected or rejected by an LLM.
"""

from __future__ import annotations

from collections import defaultdict, deque
from math import hypot
from typing import Any, Iterable

from .build_ir import BuildIR
from .design import DesignUnderstandingError, _polygon_loops, _ref, _signed_area


class SpatialAnalysisError(DesignUnderstandingError):
    """The derived spatial sensor cannot safely analyze this source shape."""


def _selected(build: BuildIR, sector_ids: Iterable[int] | None) -> set[int]:
    values = set(range(len(build.sectors))) if sector_ids is None else {int(value) for value in sector_ids}
    if not values:
        raise SpatialAnalysisError("sector selection is empty")
    invalid = sorted(value for value in values if not 0 <= value < len(build.sectors))
    if invalid:
        raise SpatialAnalysisError(f"sector IDs are out of range: {invalid}")
    return values


def _owners(build: BuildIR) -> list[int]:
    owners = [-1] * len(build.walls)
    for sector_id, sector in enumerate(build.sectors):
        fields = sector["fields"]
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        if first < 0 or count < 3 or first + count > len(build.walls):
            raise SpatialAnalysisError(f"sector:{sector_id} has invalid wall ownership")
        for wall_id in range(first, first + count):
            if owners[wall_id] != -1:
                raise SpatialAnalysisError(f"wall:{wall_id} has multiple sector owners")
            owners[wall_id] = sector_id
    if -1 in owners:
        raise SpatialAnalysisError(f"wall:{owners.index(-1)} has no sector owner")
    return owners


def _bounds(points: list[tuple[int, int]]) -> dict[str, int]:
    return {
        "min_x": min(point[0] for point in points), "min_y": min(point[1] for point in points),
        "max_x": max(point[0] for point in points), "max_y": max(point[1] for point in points),
    }


def _overlaps(left: dict[str, int], right: dict[str, int]) -> bool:
    return not (
        left["max_x"] < right["min_x"] or right["max_x"] < left["min_x"]
        or left["max_y"] < right["min_y"] or right["max_y"] < left["min_y"]
    )


def _jaccard(left: set[int], right: set[int]) -> float:
    if not left and not right:
        return 1.0
    return round(len(left & right) / len(left | right), 4)


def _components(nodes: set[int], edges: Iterable[tuple[int, int]]) -> list[list[int]]:
    graph = {node: set() for node in nodes}
    for left, right in edges:
        if left in graph and right in graph:
            graph[left].add(right)
            graph[right].add(left)
    result: list[list[int]] = []
    unseen = set(nodes)
    while unseen:
        root = min(unseen)
        unseen.remove(root)
        component = {root}
        pending = [root]
        while pending:
            current = pending.pop()
            for neighbor in graph[current] & unseen:
                unseen.remove(neighbor)
                component.add(neighbor)
                pending.append(neighbor)
        result.append(sorted(component))
    return result


def _native_blood(build: BuildIR, kind: str, identifier: int) -> dict[str, Any] | None:
    if build.source_game != "blood" or build.native.get("adapter") != "blood-level-ir-v1":
        return None
    objects = build.native.get("document", {}).get(f"{kind}s", [])
    if not 0 <= identifier < len(objects):
        return None
    return objects[identifier].get("blood")


def _sector_materials(build: BuildIR, sector_id: int) -> set[int]:
    fields = build.sectors[sector_id]["fields"]
    values = {int(fields["floor_picnum"]), int(fields["ceiling_picnum"])}
    for wall_id in range(int(fields["wall_ptr"]), int(fields["wall_ptr"]) + int(fields["wall_count"])):
        values.add(int(build.walls[wall_id]["fields"]["picnum"]))
    return values


def _blood_mechanisms(build: BuildIR, selected: set[int], owners: list[int]) -> list[dict[str, Any]]:
    groups: dict[int, dict[str, Any]] = {}
    for kind, objects in (("sector", build.sectors), ("wall", build.walls), ("sprite", build.sprites)):
        for identifier, item in enumerate(objects):
            sector_id = identifier if kind == "sector" else (
                owners[identifier] if kind == "wall" else int(item["fields"]["sector"])
            )
            if sector_id not in selected:
                continue
            blood = _native_blood(build, kind, identifier)
            if blood is None:
                continue
            fields = blood["fields"]
            for direction, field in (("transmitter", "tx_id"), ("receiver", "rx_id")):
                channel = int(fields.get(field, 0))
                if not channel:
                    continue
                group = groups.setdefault(channel, {
                    "id": f"channel:{channel}", "kind": "blood_channel", "channel": channel,
                    "members": [], "sectors": set(), "evidence": {"transmitters": [], "receivers": []},
                })
                ref = _ref(kind, identifier)
                group["members"].append({"ref": ref, "role": direction, "sector": _ref("sector", sector_id)})
                group["sectors"].add(sector_id)
                group["evidence"][f"{direction}s"].append(ref)
    result = []
    for group in groups.values():
        group["members"].sort(key=lambda item: (item["role"], item["ref"]))
        group["sectors"] = [_ref("sector", value) for value in sorted(group["sectors"])]
        result.append(group)
    return sorted(result, key=lambda item: item["channel"])


def _duke_mechanisms(build: BuildIR, selected: set[int]) -> list[dict[str, Any]]:
    from .duke_semantics import analyze_duke_mechanisms

    inventory = analyze_duke_mechanisms(build.to_native_disk_map())
    by_tag: dict[int, list[dict[str, Any]]] = defaultdict(list)
    ungrouped: list[dict[str, Any]] = []
    for record in inventory["effectors"]:
        if record["source_sector"] in selected:
            if int(record["hitag"]):
                by_tag[int(record["hitag"])].append(record)
            else:
                ungrouped.append(record)
    result = []
    for tag, records in sorted(by_tag.items()):
        sectors = sorted({int(record["source_sector"]) for record in records})
        result.append({
            "id": f"duke-tag:{tag}",
            "kind": "duke_effector_group",
            "tag": tag,
            "sectors": [_ref("sector", value) for value in sectors],
            "members": [
                {"ref": _ref("sprite", int(record["source_sprite"])), "role": record["kind"],
                 "sector": _ref("sector", int(record["source_sector"])),
                 "classification": record["classification"]}
                for record in records
            ],
            "evidence": {"effectors": [_ref("sprite", int(record["source_sprite"])) for record in records]},
        })
    for record in ungrouped:
        result.append({
            "id": f"duke-effector:{record['source_sprite']}", "kind": "duke_effector",
            "tag": 0, "sectors": [_ref("sector", int(record["source_sector"]))],
            "members": [{
                "ref": _ref("sprite", int(record["source_sprite"])), "role": record["kind"],
                "sector": _ref("sector", int(record["source_sector"])),
                "classification": record["classification"],
            }],
            "evidence": {"effectors": [_ref("sprite", int(record["source_sprite"]))]},
        })
    return result


def _known_non_portal_transitions(build: BuildIR, selected: set[int]) -> list[dict[str, Any]]:
    """Return only source-backed transition forms with explicit limitations."""
    transitions: list[dict[str, Any]] = []
    if build.source_game == "duke3d":
        from .duke_semantics import analyze_duke_mechanisms

        inventory = analyze_duke_mechanisms(build.to_native_disk_map())
        groups: dict[int, set[int]] = defaultdict(set)
        for record in inventory["effectors"]:
            if record["kind"] == "teleport_or_water_link" and int(record["hitag"]):
                groups[int(record["hitag"])].add(int(record["source_sector"]))
        for tag, sectors in sorted(groups.items()):
            if len(sectors) == 2 and sectors <= selected:
                transitions.append({
                    "id": f"duke-link:{tag}", "kind": "teleport_or_water_link",
                    "sectors": [_ref("sector", value) for value in sorted(sectors)],
                    "evidence": [f"Duke Sector Effector hitag {tag}"],
                    "state": "runtime conditions are not simulated",
                })
        return transitions

    water: dict[int, set[int]] = defaultdict(set)
    for sprite_id, sprite in enumerate(build.sprites):
        sector_id = int(sprite["fields"]["sector"])
        if sector_id not in selected or int(sprite["fields"]["lotag"]) not in {9, 10}:
            continue
        blood = _native_blood(build, "sprite", sprite_id)
        if blood is not None and int(blood["fields"].get("data_1", 0)):
            water[int(blood["fields"]["data_1"])].add(sector_id)
    for link, sectors in sorted(water.items()):
        if len(sectors) == 2:
            transitions.append({
                "id": f"blood-water:{link}", "kind": "paired_water_link",
                "sectors": [_ref("sector", value) for value in sorted(sectors)],
                "evidence": [f"Blood water XSPRITE data_1 {link}"],
                "state": "water-entry rules are not simulated",
            })
    for sector_id in sorted(selected):
        if int(build.sectors[sector_id]["fields"]["lotag"]) != 604:
            continue
        blood = _native_blood(build, "sector", sector_id)
        marker = int(blood["fields"].get("marker_0", -1)) if blood is not None else -1
        if 0 <= marker < len(build.sprites):
            destination = int(build.sprites[marker]["fields"]["sector"])
            if destination in selected:
                transitions.append({
                    "id": f"blood-teleport:{sector_id}:{marker}", "kind": "teleport_marker",
                    "sectors": [_ref("sector", sector_id), _ref("sector", destination)],
                    "evidence": [_ref("sector", sector_id), _ref("sprite", marker)],
                    "state": "teleport activation conditions are not simulated",
                })
    return transitions


def analyze_spatial(build: BuildIR, sector_ids: Iterable[int] | None = None) -> dict[str, Any]:
    """Return independent structural views and overlapping region hypotheses.

    Geometry is exact for well-formed wall ownership. Traversability and
    visibility are intentionally limited static approximations and say so in
    their models; no output here modifies BuildIR or native map data.
    """
    selected = _selected(build, sector_ids)
    owners = _owners(build)
    sector_data: dict[int, dict[str, Any]] = {}
    for sector_id in sorted(selected):
        loops = _polygon_loops(build, sector_id)
        points = [point for loop in loops for point in loop]
        fields = build.sectors[sector_id]["fields"]
        bounds = _bounds(points)
        sector_data[sector_id] = {
            "area": round(abs(sum(_signed_area(loop) for loop in loops)), 3), "bounds": bounds,
            "floor_z": int(fields["floor_z"]), "ceiling_z": int(fields["ceiling_z"]),
            "clear_height": int(fields["floor_z"]) - int(fields["ceiling_z"]),
            "shade": round((int(fields["floor_shade"]) + int(fields["ceiling_shade"])) / 2, 3),
            "materials": _sector_materials(build, sector_id),
            "wall_loop_count": len(loops),
        }

    geometry_edges: list[dict[str, Any]] = []
    seen_portals: set[tuple[int, int]] = set()
    for wall_id, wall in enumerate(build.walls):
        left = owners[wall_id]
        fields = wall["fields"]
        right, other = int(fields["next_sector"]), int(fields["next_wall"])
        if left not in selected or right not in selected or right < 0:
            continue
        signature = tuple(sorted((wall_id, other))) if other >= 0 else (wall_id, wall_id)
        if signature in seen_portals:
            continue
        seen_portals.add(signature)
        point2 = int(fields["point2"])
        if not 0 <= point2 < len(build.walls):
            raise SpatialAnalysisError(f"wall:{wall_id} has invalid point2 {point2}")
        end = build.walls[point2]["fields"]
        width = round(hypot(int(end["x"]) - int(fields["x"]), int(end["y"]) - int(fields["y"])), 3)
        opening = min(sector_data[left]["floor_z"], sector_data[right]["floor_z"]) - max(
            sector_data[left]["ceiling_z"], sector_data[right]["ceiling_z"]
        )
        wall_refs = [_ref("wall", wall_id)]
        if other >= 0:
            wall_refs.append(_ref("wall", other))
        geometry_edges.append({
            "id": f"portal:{min(wall_id, other) if other >= 0 else wall_id}",
            "sectors": [_ref("sector", left), _ref("sector", right)], "walls": wall_refs,
            "width": width, "at_rest_opening": opening,
            "blocking_flag": bool(int(fields["cstat"]) & 1),
            "floor_delta": abs(sector_data[left]["floor_z"] - sector_data[right]["floor_z"]),
        })

    traversable: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for edge in geometry_edges:
        reasons = []
        if edge["blocking_flag"]:
            reasons.append("wall cstat blocking flag")
        if edge["width"] < 512:
            reasons.append("portal width below 512 Build units")
        if edge["at_rest_opening"] < 4096:
            reasons.append("at-rest vertical opening below 4096 Build units")
        record = {**edge, "step_or_jump_may_be_required": edge["floor_delta"] > 4096}
        if reasons:
            record["reasons"] = reasons
            blocked.append(record)
        else:
            traversable.append(record)

    visibility = [
        {**edge, "visibility": "direct-portal-candidate", "basis": "shared portal plus at-rest opening"}
        for edge in geometry_edges if edge["at_rest_opening"] > 0 and edge["width"] >= 64
    ]

    vertical: list[dict[str, Any]] = []
    for position, left in enumerate(sorted(selected)):
        for right in sorted(selected)[position + 1:]:
            if not _overlaps(sector_data[left]["bounds"], sector_data[right]["bounds"]):
                continue
            left_floor, right_floor = sector_data[left]["floor_z"], sector_data[right]["floor_z"]
            left_ceiling, right_ceiling = sector_data[left]["ceiling_z"], sector_data[right]["ceiling_z"]
            if left_floor < right_ceiling:
                relation = "above"
            elif right_floor < left_ceiling:
                relation = "below"
            else:
                relation = "overlapping_vertical_intervals"
            vertical.append({
                "sectors": [_ref("sector", left), _ref("sector", right)], "relation": relation,
                "floor_delta": abs(left_floor - right_floor),
                "xy_overlap": "bounding-box", "basis": "sector XY bounds and flat surface Z ranges",
            })

    material_edges = []
    for edge in geometry_edges:
        left, right = (int(value.split(":", 1)[1]) for value in edge["sectors"])
        continuity = _jaccard(sector_data[left]["materials"], sector_data[right]["materials"])
        material_edges.append({
            "sectors": edge["sectors"], "portal": edge["id"], "shared_tile_ratio": continuity,
            "shade_delta": abs(sector_data[left]["shade"] - sector_data[right]["shade"]),
            "basis": "raw floor/ceiling/wall tile IDs and sector shade; material families are not inferred",
        })

    mechanisms = _blood_mechanisms(build, selected, owners) if build.source_game == "blood" else _duke_mechanisms(build, selected)
    non_portal_transitions = _known_non_portal_transitions(build, selected)
    traversable_pairs = [
        tuple(int(value.split(":", 1)[1]) for value in edge["sectors"]) for edge in traversable
    ]
    start = int(build.player_start["sector"])
    reachable: set[int] = set()
    if start in selected:
        adjacency: dict[int, set[int]] = defaultdict(set)
        for left, right in traversable_pairs:
            adjacency[left].add(right)
            adjacency[right].add(left)
        for transition in non_portal_transitions:
            left, right = (int(value.split(":", 1)[1]) for value in transition["sectors"])
            adjacency[left].add(right)
            adjacency[right].add(left)
        reachable = {start}
        pending = deque([start])
        while pending:
            current = pending.popleft()
            for neighbor in adjacency[current] - reachable:
                reachable.add(neighbor)
                pending.append(neighbor)

    hypotheses: list[dict[str, Any]] = []
    def add_hypotheses(kind: str, components: list[list[int]], evidence: Any, *, minimum: int = 2) -> None:
        for number, component in enumerate(components):
            if len(component) < minimum:
                continue
            hypotheses.append({
                "id": f"{kind}:{number}", "kind": kind,
                "sectors": [_ref("sector", value) for value in component],
                "evidence": evidence(component),
                "status": "derived hypothesis; not an authoritative room partition",
            })

    perceptual_pairs = []
    for edge in visibility:
        left, right = (int(value.split(":", 1)[1]) for value in edge["sectors"])
        material = next(item for item in material_edges if item["portal"] == edge["id"])
        if edge["floor_delta"] <= 4096 and material["shade_delta"] <= 12:
            perceptual_pairs.append((left, right))
    add_hypotheses("perceptual_space", _components(selected, perceptual_pairs), lambda sectors: {
        "portal_continuity": "direct portal candidates with floor delta <= 4096",
        "visual_continuity": "shared portal opening and shade delta <= 12",
        "sectors_considered": len(sectors),
    })
    add_hypotheses("navigation_region", _components(selected, traversable_pairs), lambda sectors: {
        "traversability": "static at-rest portal approximation", "sectors_considered": len(sectors),
    })
    material_pairs = []
    for edge in material_edges:
        left, right = (int(value.split(":", 1)[1]) for value in edge["sectors"])
        if edge["shared_tile_ratio"] >= 0.25 and edge["shade_delta"] <= 8:
            material_pairs.append((left, right))
    add_hypotheses("material_region", _components(selected, material_pairs), lambda sectors: {
        "material_continuity": "shared raw tile ratio >= 0.25 and shade delta <= 8",
        "sectors_considered": len(sectors),
    })
    for number, mechanism in enumerate(mechanisms):
        members = sorted({int(value.split(":", 1)[1]) for value in mechanism["sectors"]})
        if members:
            hypotheses.append({
                "id": f"mechanism_region:{number}", "kind": "mechanism_region",
                "sectors": [_ref("sector", value) for value in members],
                "evidence": {"mechanism": mechanism["id"], "members": mechanism["members"]},
                "status": "derived behavior membership; may be spatially discontinuous",
            })
    for number, relation in enumerate(vertical):
        if relation["relation"] in {"above", "below"}:
            hypotheses.append({
                "id": f"vertical_layer:{number}", "kind": "vertical_layer",
                "sectors": relation["sectors"], "evidence": relation,
                "status": "derived XY-overlap relationship; not a rendering proof",
            })

    return {
        "$schema": "bloodmap.spatial-analysis", "schema_version": 1,
        "source_game": build.source_game, "scope": "level" if sector_ids is None else "selection",
        "sector_ids": [_ref("sector", value) for value in sorted(selected)],
        "views": {
            "geometry": {
                "model": "raw Build sector adjacency through portal references",
                "sectors": [{"ref": _ref("sector", value), **{
                    key: sector_data[value][key] for key in ("area", "bounds", "floor_z", "ceiling_z", "clear_height", "wall_loop_count")
                }} for value in sorted(selected)],
                "portals": geometry_edges,
            },
            "traversability": {
                "model": "static approximation: portal width/opening and wall blocking flag; source-backed water/teleport links are listed separately and runtime conditions are not simulated",
                "walkable_at_rest": traversable, "blocked_or_state_dependent": blocked,
                "known_non_portal_transitions": non_portal_transitions,
            },
            "visibility": {
                "model": "heuristic direct-portal candidates only; no renderer, occlusion, slopes, or multi-portal rays",
                "candidates": visibility,
            },
            "vertical": {
                "model": "flat floor/ceiling Z intervals plus XY bounding-box overlap",
                "relationships": vertical,
            },
            "mechanism": {
                "model": "Blood TX/RX extended-record groups or Duke source-backed Sector Effector tag groups",
                "groups": mechanisms,
            },
            "progression": {
                "model": "static traversal from player start plus known water/teleport links; blocked portals and mechanism groups are state-change candidates, not solved progression",
                "start_sector": _ref("sector", start) if start in selected else None,
                "reachable_sectors": [_ref("sector", value) for value in sorted(reachable)],
                "unreachable_sectors": [_ref("sector", value) for value in sorted(selected - reachable)] if start in selected else [],
                "state_change_candidates": [{"portal": edge["id"], "reasons": edge["reasons"]} for edge in blocked],
                "mechanism_state_candidates": [
                    {
                        "mechanism": group["id"], "sectors": group["sectors"],
                        "crosses_current_reachability": bool(reachable) and any(
                            int(ref.split(":", 1)[1]) in reachable for ref in group["sectors"]
                        ) and any(
                            int(ref.split(":", 1)[1]) not in reachable for ref in group["sectors"]
                        ),
                    }
                    for group in mechanisms
                ],
            },
            "material": {
                "model": "raw tile-ID and shade continuity; no material-family or aesthetic inference",
                "portal_continuity": material_edges,
            },
        },
        "hypotheses": hypotheses,
        "provenance": {
            "verified_facts": ["sector/wall/sprite references", "portal references", "raw tile and shade values", "native mechanism fields"],
            "derived_metrics": ["portal opening/width", "static traversal candidates", "XY/Z relationship candidates", "tile-ID continuity"],
            "heuristic_hypotheses": ["perceptual_space", "navigation_region", "material_region", "vertical_layer"],
            "not_inferred": ["canonical rooms", "line of sight through renderer", "mechanism state over time", "player intent", "encounter boundaries"],
        },
    }


def spatial_selection_context(build: BuildIR, sector_ids: Iterable[int]) -> dict[str, Any]:
    """Return compact selection context, retaining neighboring contrast evidence."""
    selected = _selected(build, sector_ids)
    analysis = analyze_spatial(build)
    geometry = analysis["views"]["geometry"]
    by_sector = {item["ref"]: item for item in geometry["sectors"]}
    inside = {_ref("sector", value) for value in selected}
    external = [
        edge for edge in geometry["portals"]
        if bool(set(edge["sectors"]) & inside) and not set(edge["sectors"]) <= inside
    ]
    contrast = []
    for edge in external:
        left, right = edge["sectors"]
        source, neighbor = (left, right) if left in inside else (right, left)
        source_data, neighbor_data = by_sector[source], by_sector[neighbor]
        contrast.append({
            "from": source, "to": neighbor, "portal": edge["id"],
            "area_delta_ratio": round(neighbor_data["area"] / max(1.0, source_data["area"]), 4),
            "clear_height_delta": neighbor_data["clear_height"] - source_data["clear_height"],
            "floor_delta": neighbor_data["floor_z"] - source_data["floor_z"],
            "basis": "adjacent sector geometry; a reveal/release interpretation is heuristic",
        })
    touching_vertical = [
        relation for relation in analysis["views"]["vertical"]["relationships"]
        if set(relation["sectors"]) & inside
    ]
    mechanisms = [
        group for group in analysis["views"]["mechanism"]["groups"]
        if set(group["sectors"]) & inside
    ]
    hypotheses = [
        item for item in analysis["hypotheses"] if set(item["sectors"]) & inside
    ]

    def compact_hypothesis(item: dict[str, Any]) -> dict[str, Any]:
        sectors = item["sectors"]
        return {
            "id": item["id"], "kind": item["kind"], "sector_count": len(sectors),
            "selected_members": sorted(set(sectors) & inside), "sector_sample": sectors[:32],
            "truncated": len(sectors) > 32, "evidence": item["evidence"], "status": item["status"],
        }

    def compact_mechanism(item: dict[str, Any]) -> dict[str, Any]:
        members = item["members"]
        return {
            "id": item["id"], "kind": item["kind"], "sector_count": len(item["sectors"]),
            "selected_members": sorted(set(item["sectors"]) & inside), "sector_sample": item["sectors"][:32],
            "member_sample": members[:32], "truncated": len(item["sectors"]) > 32 or len(members) > 32,
            "evidence": item["evidence"],
        }
    return {
        "$schema": "bloodmap.spatial-selection-context", "schema_version": 1,
        "selected_sectors": sorted(inside), "external_connectors": external,
        "adjacent_space_contrast": contrast, "vertical_context": touching_vertical[:64],
        "vertical_context_truncated": len(touching_vertical) > 64,
        "mechanism_relationships": [compact_mechanism(item) for item in mechanisms],
        "overlapping_hypotheses": [compact_hypothesis(item) for item in hypotheses],
        "limitations": ["contrast does not prove a dramatic reveal", "hypotheses overlap and do not partition sectors"],
    }
