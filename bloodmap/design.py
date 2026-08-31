"""Deterministic Design Understanding measurements.

The functions here are sensors, not a level-design rules engine.  They preserve
exact object references, expose measured geometry separately from heuristics, and
work on the game-neutral BuildIR so Blood and Duke3D can be compared without
pretending their native tags are interchangeable.
"""

from __future__ import annotations

from collections import Counter, deque
from math import hypot
from typing import Any, Iterable

from .build_ir import BuildIR


class DesignUnderstandingError(ValueError):
    pass


def _ref(kind: str, identifier: int) -> str:
    return f"{kind}:{identifier}"


def _metric(value: Any, *, basis: str = "derived", confidence: str = "measured") -> dict[str, Any]:
    return {"value": value, "basis": basis, "confidence": confidence}


def _polygon(build: BuildIR, sector_id: int) -> list[tuple[int, int]]:
    """Return all loop points flattened for legacy callers.

    Area-aware consumers must use :func:`_polygon_loops`: a Build sector can
    contain an outer loop and one or more inner loops.
    """
    return [point for loop in _polygon_loops(build, sector_id) for point in loop]


def _polygon_loops(build: BuildIR, sector_id: int) -> list[list[tuple[int, int]]]:
    fields = build.sectors[sector_id]["fields"]
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    if first < 0 or count < 3 or first + count > len(build.walls):
        raise DesignUnderstandingError(f"sector:{sector_id} has invalid wall ownership")
    allowed, remaining = set(range(first, first + count)), set(range(first, first + count))
    loops: list[list[tuple[int, int]]] = []
    while remaining:
        root, current, visited = min(remaining), min(remaining), set()
        points: list[tuple[int, int]] = []
        while current not in visited:
            if current not in allowed:
                raise DesignUnderstandingError(f"sector:{sector_id} wall loop leaves owning range")
            visited.add(current)
            remaining.discard(current)
            wall = build.walls[current]["fields"]
            points.append((int(wall["x"]), int(wall["y"])))
            current = int(wall["point2"])
        if current != root or len(points) < 3:
            raise DesignUnderstandingError(f"sector:{sector_id} has an invalid wall loop")
        loops.append(points)
    return loops


def _area(points: list[tuple[int, int]]) -> float:
    return abs(sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )) / 2.0


def _signed_area(points: list[tuple[int, int]]) -> float:
    return sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    ) / 2.0


def _components(graph: dict[int, set[int]]) -> list[set[int]]:
    remaining = set(graph)
    result: list[set[int]] = []
    while remaining:
        root = min(remaining)
        component = {root}
        pending = [root]
        remaining.remove(root)
        while pending:
            current = pending.pop()
            for neighbor in graph[current] & remaining:
                remaining.remove(neighbor)
                component.add(neighbor)
                pending.append(neighbor)
        result.append(component)
    return result


def _graph_distances(graph: dict[int, set[int]]) -> list[int]:
    distances: list[int] = []
    for root in graph:
        seen = {root: 0}
        pending = deque([root])
        while pending:
            current = pending.popleft()
            for neighbor in graph[current]:
                if neighbor not in seen:
                    seen[neighbor] = seen[current] + 1
                    pending.append(neighbor)
        distances.extend(value for node, value in seen.items() if node != root)
    return distances


def _source_mechanisms(build: BuildIR, selected: set[int]) -> dict[str, Any]:
    """Return source-aware counts while keeping native semantics opaque here."""
    if build.source_game == "duke3d":
        from .duke_semantics import analyze_duke_mechanisms

        inventory = analyze_duke_mechanisms(build.to_native_disk_map())
        effectors = [item for item in inventory["effectors"] if item["source_sector"] in selected]
        cracks = [item for item in inventory["destructible_walls"] if item["source_sector"] in selected]
        return {
            "controllers": len(effectors),
            "destructible_or_damageable": len(cracks),
            "kinds": dict(sorted(Counter(item["kind"] for item in effectors).items())),
            "evidence": [_ref("sprite", item["source_sprite"]) for item in effectors[:64]],
        }
    extras = []
    native_document = build.native.get("document") if build.native.get("adapter") == "blood-level-ir-v1" else None
    native_objects = {
        "sector": native_document.get("sectors", []) if native_document else [],
        "wall": native_document.get("walls", []) if native_document else [],
        "sprite": native_document.get("sprites", []) if native_document else [],
    }
    for kind, objects in (("sector", build.sectors), ("wall", build.walls), ("sprite", build.sprites)):
        for identifier, item in enumerate(objects):
            if kind == "sprite" and int(item["fields"]["sector"]) not in selected:
                continue
            native_item = native_objects[kind][identifier] if identifier < len(native_objects[kind]) else None
            if native_item and native_item.get("blood") is not None:
                extras.append((kind, identifier, native_item["blood"]["kind"]))
    controller_extras = [item for item in extras if item[2] in {"XSECTOR", "XWALL"}]
    return {
        "controllers": len(controller_extras),
        "destructible_or_damageable": sum(
            (object_kind == "wall" and int(build.walls[identifier]["fields"]["lotag"]) == 511)
            or (object_kind == "sprite" and int(build.sprites[identifier]["fields"]["lotag"]) == 408)
            for object_kind, identifier, _extra_kind in extras
        ),
        "kinds": dict(sorted(Counter(kind for _object_kind, _identifier, kind in extras).items())),
        "evidence": [_ref(kind, identifier) for kind, identifier, _ in extras[:64]],
    }


def design_fingerprint(build: BuildIR, sector_ids: Iterable[int] | None = None) -> dict[str, Any]:
    """Measure a level or selected connected region for LLM retrieval.

    Values are intentionally compact and JSON-native.  ``metrics`` are derived
    measurements; ``interpretations`` are explicitly heuristic text; ``evidence``
    points back to exact BuildIR objects.
    """
    selected = set(range(len(build.sectors))) if sector_ids is None else {int(value) for value in sector_ids}
    if not selected:
        raise DesignUnderstandingError("sector selection is empty")
    invalid = sorted(value for value in selected if not 0 <= value < len(build.sectors))
    if invalid:
        raise DesignUnderstandingError(f"sector IDs are out of range: {invalid}")
    ignored_degenerate = sorted(
        value for value in selected
        if int(build.sectors[value]["fields"]["wall_count"]) < 3
    )
    selected -= set(ignored_degenerate)
    if not selected:
        raise DesignUnderstandingError("sector selection contains no geometrically valid sectors")

    areas: dict[int, float] = {}
    heights: dict[int, int] = {}
    elevations: list[int] = []
    shape_signatures: Counter[tuple[int, int, int]] = Counter()
    selected_walls: set[int] = set()
    centroids: dict[int, tuple[float, float]] = {}
    graph = {sector_id: set() for sector_id in selected}
    connector_widths: list[float] = []
    connector_refs: list[str] = []
    for sector_id in sorted(selected):
        loops = _polygon_loops(build, sector_id)
        points = [point for loop in loops for point in loop]
        area = abs(sum(_signed_area(loop) for loop in loops))
        fields = build.sectors[sector_id]["fields"]
        areas[sector_id] = area
        ceiling_z, floor_z = int(fields["ceiling_z"]), int(fields["floor_z"])
        heights[sector_id] = floor_z - ceiling_z
        elevations.extend((ceiling_z, floor_z))
        selected_walls.update(range(int(fields["wall_ptr"]), int(fields["wall_ptr"]) + int(fields["wall_count"])))
        min_x, max_x = min(point[0] for point in points), max(point[0] for point in points)
        min_y, max_y = min(point[1] for point in points), max(point[1] for point in points)
        centroids[sector_id] = ((min_x + max_x) / 2, (min_y + max_y) / 2)
        shape_signatures[(len(points), len(loops), round((max_x - min_x) / max(1.0, max_y - min_y), 2), round(area / 1_000_000))] += 1
        for wall_id in range(int(fields["wall_ptr"]), int(fields["wall_ptr"]) + int(fields["wall_count"])):
            wall = build.walls[wall_id]["fields"]
            next_sector = int(wall["next_sector"])
            point2 = int(wall["point2"])
            end = build.walls[point2]["fields"]
            length = hypot(int(end["x"]) - int(wall["x"]), int(end["y"]) - int(wall["y"]))
            if next_sector in selected:
                graph[sector_id].add(next_sector)
            # A connector is a portal leaving the selected region.  Do not
            # count every one-sided wall in a whole-level fingerprint: those
            # are boundaries, not traversable room-to-room connections.
            elif next_sector >= 0:
                connector_widths.append(round(length, 3))
                connector_refs.append(_ref("wall", wall_id))

    edges = sum(len(neighbors) for neighbors in graph.values()) // 2
    degrees = [len(graph[node]) for node in graph]
    components = _components(graph)
    distances = _graph_distances(graph)
    total_area = sum(areas.values())
    total_volume = sum(areas[node] * heights[node] for node in selected)
    unique_materials = {
        int(build.sectors[node]["fields"][name])
        for node in selected for name in ("ceiling_picnum", "floor_picnum")
    }
    unique_materials.update(int(build.walls[wall]["fields"]["picnum"]) for wall in selected_walls)
    sprite_ids = [
        identifier for identifier, item in enumerate(build.sprites)
        if int(item["fields"]["sector"]) in selected
    ]
    source_mechanisms = _source_mechanisms(build, selected)
    source_enemy_types = {"blood": set(range(200, 300)), "duke3d": {1680, 2120, 2121, 2150, 1820, 1880, 1960, 2000, 2001, 2045, 2165, 2370, 2631}}[build.source_game]
    sprite_kind_field = "lotag" if build.source_game == "blood" else "picnum"
    enemy_ids = [identifier for identifier in sprite_ids if int(build.sprites[identifier]["fields"][sprite_kind_field]) in source_enemy_types]
    occupied_enemy_sectors = {int(build.sprites[identifier]["fields"]["sector"]) for identifier in enemy_ids}
    key_types = {100, 101} if build.source_game == "blood" else {60}
    key_ids = [identifier for identifier in sprite_ids if int(build.sprites[identifier]["fields"][sprite_kind_field]) in key_types]
    repeated_shape_ratio = max(shape_signatures.values()) / len(selected)
    metrics = {
        "topology": {
            "sector_count": _metric(len(selected), basis="verified selection"),
            "portal_edge_count": _metric(edges),
            "component_count": _metric(len(components)),
            "average_degree": _metric(round(sum(degrees) / max(1, len(degrees)), 4)),
            "branching_ratio": _metric(round(sum(value >= 3 for value in degrees) / max(1, len(degrees)), 4)),
            "dead_end_ratio": _metric(round(sum(value <= 1 for value in degrees) / max(1, len(degrees)), 4)),
            "loopiness": _metric(round(max(0, edges - len(selected) + len(components)) / max(1, len(selected)), 4)),
            "linearity": _metric(round((max(distances) if distances else 0) / max(1, len(selected) - 1), 4)),
        },
        "space": {
            "area": _metric(round(total_area, 3)),
            "volume_proxy": _metric(round(total_volume, 3)),
            "mean_sector_area": _metric(round(total_area / len(selected), 3)),
            "min_sector_area": _metric(round(min(areas.values()), 3)),
            "max_sector_area": _metric(round(max(areas.values()), 3)),
            "mean_clear_height": _metric(round(sum(heights.values()) / len(heights), 3)),
            "vertical_range": _metric(max(elevations) - min(elevations)),
            "connector_width_mean": _metric(round(sum(connector_widths) / len(connector_widths), 3) if connector_widths else None),
        },
        "architecture": {
            "distinct_elevation_pairs": _metric(len({(int(build.sectors[node]["fields"]["ceiling_z"]), int(build.sectors[node]["fields"]["floor_z"])) for node in selected})),
            "shape_signature_count": _metric(len(shape_signatures)),
            "repeated_shape_ratio": _metric(round(repeated_shape_ratio, 4)),
            "irregularity_proxy": _metric(round(1.0 - repeated_shape_ratio, 4)),
            "material_diversity": _metric(len(unique_materials)),
        },
        "visual": {
            "shade_mean": _metric(round(sum(int(build.sectors[node]["fields"]["floor_shade"]) + int(build.sectors[node]["fields"]["ceiling_shade"]) for node in selected) / (2 * len(selected)), 3)),
            "shade_range": _metric(round(max(
                [int(build.sectors[node]["fields"][name]) for node in selected for name in ("floor_shade", "ceiling_shade")]
            ) - min(
                [int(build.sectors[node]["fields"][name]) for node in selected for name in ("floor_shade", "ceiling_shade")]
            ), 3)),
            "material_family_consistency": _metric(None, basis="not inferred from tile IDs", confidence="unknown"),
        },
        "gameplay": {
            "sprite_count": _metric(len(sprite_ids), basis="verified selection"),
            "enemy_count": _metric(len(enemy_ids)),
            "enemy_sector_ratio": _metric(round(len(occupied_enemy_sectors) / max(1, len(selected)), 4)),
            "key_count": _metric(len(key_ids)),
            "mechanism_density": _metric(round(source_mechanisms["controllers"] / max(1, len(selected)), 4)),
            "destructible_or_damageable_count": _metric(source_mechanisms["destructible_or_damageable"]),
        },
    }
    interpretations: list[dict[str, Any]] = []
    topology = metrics["topology"]
    space = metrics["space"]
    if topology["branching_ratio"]["value"] >= 0.34:
        interpretations.append({"text": "The selected space branches into multiple routes.", "basis": "branching_ratio", "confidence": "heuristic"})
    if topology["dead_end_ratio"]["value"] >= 0.5:
        interpretations.append({"text": "Many selected sectors behave as terminal or near-terminal spaces.", "basis": "dead_end_ratio", "confidence": "heuristic"})
    if topology["loopiness"]["value"] > 0:
        interpretations.append({"text": "The selected topology contains a loop or alternate return path.", "basis": "loopiness", "confidence": "heuristic"})
    if space["vertical_range"]["value"] > max(4096, space["mean_clear_height"]["value"] * 0.5):
        interpretations.append({"text": "The region has meaningful vertical contrast.", "basis": "vertical_range", "confidence": "heuristic"})
    if space["connector_width_mean"]["value"] is not None and space["connector_width_mean"]["value"] < 2048:
        interpretations.append({"text": "Connections are relatively compressed compared with Build units.", "basis": "connector_width_mean", "confidence": "heuristic"})
    if metrics["architecture"]["repeated_shape_ratio"]["value"] >= 0.5:
        interpretations.append({"text": "Repeated sector proportions suggest a structural rhythm.", "basis": "repeated_shape_ratio", "confidence": "heuristic"})
    return {
        "$schema": "bloodmap.design-fingerprint",
        "schema_version": 1,
        "source_game": build.source_game,
        "scope": "level" if sector_ids is None else "selection",
        "sector_ids": sorted(selected),
        "ignored_degenerate_sector_ids": ignored_degenerate,
        "metrics": metrics,
        "interpretations": interpretations,
        "source_mechanisms": source_mechanisms,
        "evidence": {
            "sectors": [_ref("sector", value) for value in sorted(selected)],
            "walls": [_ref("wall", value) for value in sorted(selected_walls)[:128]],
            "connectors": connector_refs[:128],
            "sprites": [_ref("sprite", value) for value in sprite_ids[:128]],
            "enemy_sprites": [_ref("sprite", value) for value in enemy_ids[:128]],
            "key_sprites": [_ref("sprite", value) for value in key_ids[:128]],
        },
        "provenance": {
            "verified_facts": ["object references and native source game", "sector topology and dimensions", "entity and extended-record counts"],
            "derived_metrics": ["topology ratios", "area/volume proxies", "repetition and material counts", "enemy and mechanism density"],
            "heuristic_interpretations": [item["text"] for item in interpretations],
            "not_inferred": ["material family names", "visual focal-point strength", "player intent", "atmosphere"],
        },
    }
