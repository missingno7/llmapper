"""Geometry-first, lossless level source reconstruction.

The decompiler deliberately keeps two unlike things apart:

* ``exact_level_ir`` is authoritative Blood source truth and can be compiled;
* ``hierarchy`` is a derived, reviewable authoring view over that truth.

The first hierarchy is intentionally conservative.  It turns existing spatial
sensor evidence into a readable primary tree while retaining every overlapping
hypothesis for later LLM review instead of pretending that rooms are native MAP
objects.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pprint import pformat
from typing import Any, Iterable

from .model import LevelIR
from .player_space import player_profile
from .spatial import analyze_spatial
from .structures import detect_structures


SCHEMA = "llmapper.level-source"
SCHEMA_VERSION = 1


class DecompilerError(ValueError):
    """The level-source document is inconsistent with its exact LevelIR."""


def _ids(refs: Iterable[str]) -> list[int]:
    return sorted(int(ref.split(":", 1)[1]) for ref in refs)


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
        component = {root}
        pending = [root]
        unseen.remove(root)
        while pending:
            current = pending.pop()
            for neighbor in sorted(graph[current] & unseen):
                unseen.remove(neighbor)
                component.add(neighbor)
                pending.append(neighbor)
        result.append(sorted(component))
    return sorted(result, key=lambda values: (values[0], len(values)))


def _owned_refs(level: LevelIR, sector_ids: Iterable[int]) -> dict[str, list[int]]:
    selected = set(sector_ids)
    walls: list[int] = []
    for sector_id in sorted(selected):
        fields = level.sectors[sector_id]["fields"]
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        walls.extend(range(first, first + count))
    sprites = [
        sprite_id for sprite_id, sprite in enumerate(level.sprites)
        if int(sprite["fields"]["sector"]) in selected
    ]
    return {"sectors": sorted(selected), "walls": walls, "sprites": sprites}


def _geometry_summary(
    sector_ids: Iterable[int], geometry: dict[int, dict[str, Any]], *, body_width: int,
    standing_height: int,
) -> dict[str, Any]:
    records = [geometry[value] for value in sector_ids]
    bounds = {
        "min_x": min(item["bounds"]["min_x"] for item in records),
        "min_y": min(item["bounds"]["min_y"] for item in records),
        "max_x": max(item["bounds"]["max_x"] for item in records),
        "max_y": max(item["bounds"]["max_y"] for item in records),
    }
    heights = sorted(int(item["clear_height"]) for item in records)
    median_height = heights[len(heights) // 2]
    area = round(sum(float(item["area"]) for item in records), 4)
    width = bounds["max_x"] - bounds["min_x"]
    depth = bounds["max_y"] - bounds["min_y"]
    return {
        "bounds": bounds,
        "area_native_squared": area,
        "aabb_native": {"width": width, "depth": depth},
        "player_relative": {
            "footprint_player_areas": round(area / (body_width * body_width), 4),
            "aabb_player_widths": [round(width / body_width, 4), round(depth / body_width, 4)],
            "median_clear_height_player_heights": round(median_height / standing_height, 4),
        },
        "floor_z_range": [min(int(item["floor_z"]) for item in records), max(int(item["floor_z"]) for item in records)],
        "ceiling_z_range": [min(int(item["ceiling_z"]) for item in records), max(int(item["ceiling_z"]) for item in records)],
        "wall_loop_count": sum(int(item["wall_loop_count"]) for item in records),
    }


def _asset_counts(level: LevelIR, refs: dict[str, list[int]]) -> dict[str, dict[str, int]]:
    roles: dict[str, Counter[int]] = {
        "floor": Counter(), "ceiling": Counter(), "wall": Counter(), "wall_overlay": Counter(),
        "sprite": Counter(),
    }
    for sector_id in refs["sectors"]:
        fields = level.sectors[sector_id]["fields"]
        roles["floor"][int(fields["floor_picnum"])] += 1
        roles["ceiling"][int(fields["ceiling_picnum"])] += 1
    for wall_id in refs["walls"]:
        fields = level.walls[wall_id]["fields"]
        roles["wall"][int(fields["picnum"])] += 1
        overlay = int(fields["over_picnum"])
        if overlay >= 0:
            roles["wall_overlay"][overlay] += 1
    for sprite_id in refs["sprites"]:
        roles["sprite"][int(level.sprites[sprite_id]["fields"]["picnum"])] += 1
    return {
        role: {str(tile_id): count for tile_id, count in sorted(counts.items())}
        for role, counts in roles.items() if counts
    }


def _compact_candidate(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"], "kind": item["kind"], "sector_ids": _ids(item["sectors"]),
        "evidence": deepcopy(item["evidence"]), "status": item["status"],
    }


def _node(
    identifier: str, kind: str, name: str, parent: str | None, refs: dict[str, list[int]],
    geometry: dict[str, Any] | None, materials: dict[str, dict[str, int]],
    *, basis: list[str], candidate: str | None = None,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "kind": kind,
        "name": name,
        "parent": parent,
        "children": [],
        "sources": refs,
        "geometry": geometry,
        "material_usage": materials,
        "interpretation": {
            "status": "unreviewed",
            "semantic_name": None,
            "description": None,
            "confidence": None,
        },
        "provenance": {
            "status": "derived hierarchy proposal; exact sources remain authoritative",
            "basis": basis,
            "spatial_candidate": candidate,
        },
    }


@dataclass
class LevelSource:
    """Versioned exact source plus a non-authoritative semantic scene graph."""

    source: dict[str, Any]
    exact_level_ir: dict[str, Any]
    hierarchy: dict[str, Any]
    assets: list[dict[str, Any]]
    schema: str = SCHEMA
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": self.schema,
            "schema_version": self.schema_version,
            "source": deepcopy(self.source),
            "exact_level_ir": deepcopy(self.exact_level_ir),
            "hierarchy": deepcopy(self.hierarchy),
            "assets": deepcopy(self.assets),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LevelSource":
        result = cls(
            schema=str(value["$schema"]), schema_version=int(value["schema_version"]),
            source=deepcopy(value["source"]), exact_level_ir=deepcopy(value["exact_level_ir"]),
            hierarchy=deepcopy(value["hierarchy"]), assets=deepcopy(value["assets"]),
        )
        result.validate()
        return result

    def to_level_ir(self) -> LevelIR:
        """Compile only authoritative source truth; interpretations never rewrite it."""
        self.validate()
        return LevelIR.from_dict(deepcopy(self.exact_level_ir))

    def node(self, identifier: str) -> dict[str, Any]:
        for item in self.hierarchy["nodes"]:
            if item["id"] == identifier:
                return deepcopy(item)
        raise DecompilerError(f"unknown hierarchy node {identifier!r}")

    def validate(self) -> None:
        if self.schema != SCHEMA or self.schema_version != SCHEMA_VERSION:
            raise DecompilerError(f"unsupported level-source schema {self.schema!r} version {self.schema_version}")
        level = LevelIR.from_dict(self.exact_level_ir)
        limits = {"sectors": len(level.sectors), "walls": len(level.walls), "sprites": len(level.sprites)}
        nodes = self.hierarchy.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            raise DecompilerError("hierarchy requires nodes")
        by_id = {str(item.get("id")): item for item in nodes}
        if len(by_id) != len(nodes):
            raise DecompilerError("hierarchy node IDs must be unique")
        root_id = self.hierarchy.get("primary_root")
        if root_id not in by_id or by_id[root_id].get("kind") != "level":
            raise DecompilerError("primary_root must identify a level node")
        for node_id, item in by_id.items():
            parent = item.get("parent")
            if parent is not None and parent not in by_id:
                raise DecompilerError(f"{node_id} has unknown parent {parent!r}")
            for kind, maximum in limits.items():
                refs = item.get("sources", {}).get(kind, [])
                if refs != sorted(set(refs)) or any(not isinstance(value, int) or not 0 <= value < maximum for value in refs):
                    raise DecompilerError(f"{node_id} has invalid {kind} source references")
            expected_children = sorted(other_id for other_id, other in by_id.items() if other.get("parent") == node_id)
            if sorted(item.get("children", [])) != expected_children:
                raise DecompilerError(f"{node_id} children disagree with parent links")
        root_refs = by_id[root_id]["sources"]
        for kind, maximum in limits.items():
            if root_refs[kind] != list(range(maximum)):
                raise DecompilerError(f"root does not preserve every exact {kind} reference")
        primary_assemblies = [item for item in nodes if item["kind"] == "assembly"]
        assembly_sectors = [value for item in primary_assemblies for value in item["sources"]["sectors"]]
        if sorted(assembly_sectors) != list(range(limits["sectors"])):
            raise DecompilerError("primary assemblies must partition every sector exactly once")
        primary_spaces = [item for item in nodes if item["kind"] == "space"]
        seen = [value for item in primary_spaces for value in item["sources"]["sectors"]]
        if sorted(seen) != list(range(limits["sectors"])):
            raise DecompilerError("primary spaces must partition every sector exactly once")
        for item in primary_assemblies + primary_spaces:
            expected = _owned_refs(level, item["sources"]["sectors"])
            if item["sources"] != expected:
                raise DecompilerError(f"{item['id']} source objects disagree with sector ownership")
            if item["kind"] == "space":
                parent = by_id[item["parent"]]
                if not set(item["sources"]["sectors"]) <= set(parent["sources"]["sectors"]):
                    raise DecompilerError(f"{item['id']} is not contained by its assembly")
        for item in nodes:
            if item["kind"] != "detail_group":
                continue
            if item["sources"]["sectors"] or item["sources"]["walls"]:
                raise DecompilerError(f"{item['id']} detail group may own only sprite references")
            parent = by_id[item["parent"]]
            if not set(item["sources"]["sprites"]) <= set(parent["sources"]["sprites"]):
                raise DecompilerError(f"{item['id']} contains sprites outside its parent space")
        for node_id in by_id:
            visited: set[str] = set()
            current: str | None = node_id
            while current is not None:
                if current in visited:
                    raise DecompilerError(f"hierarchy contains a parent cycle at {current}")
                visited.add(current)
                current = by_id[current].get("parent")


def decompile_level(level: LevelIR, *, source_name: str | None = None) -> LevelSource:
    """Create the first conservative hierarchy proposal for one Blood level."""
    build = level.to_disk_map().to_build_ir()
    spatial = analyze_spatial(build)
    geometry = {int(item["ref"].split(":", 1)[1]): item for item in spatial["views"]["geometry"]["sectors"]}
    portals = spatial["views"]["geometry"]["portals"]
    profile = player_profile("blood")
    all_sectors = set(range(len(level.sectors)))

    # Major assemblies follow persistent source topology.  Doors and lifts must
    # not shatter a building into dozens of fake assemblies merely because the
    # at-rest traversal approximation calls their portals blocked.
    navigation_edges: list[tuple[int, int]] = [tuple(_ids(edge["sectors"])) for edge in portals]
    for transition in spatial["views"]["traversability"]["known_non_portal_transitions"]:
        members = _ids(transition["sectors"])
        if len(members) == 2:
            navigation_edges.append((members[0], members[1]))
    assemblies = _components(all_sectors, navigation_edges)

    perceptual = [item for item in spatial["hypotheses"] if item["kind"] == "perceptual_space"]
    perceptual_sets = [(item, set(_ids(item["sectors"]))) for item in perceptual]
    nodes: list[dict[str, Any]] = []
    root_refs = _owned_refs(level, all_sectors)
    root = _node(
        "level", "level", "level", None, root_refs,
        _geometry_summary(all_sectors, geometry, body_width=profile.body_width, standing_height=profile.standing_height),
        _asset_counts(level, root_refs), basis=["exact LevelIR object inventory", "whole-level spatial geometry"],
    )
    nodes.append(root)

    sector_to_space: dict[int, str] = {}
    for assembly_number, assembly_values in enumerate(assemblies, 1):
        assembly_id = f"assembly:{assembly_number:03d}"
        assembly_set = set(assembly_values)
        refs = _owned_refs(level, assembly_values)
        assembly_node = _node(
            assembly_id, "assembly", f"assembly_{assembly_number:03d}", "level", refs,
            _geometry_summary(assembly_values, geometry, body_width=profile.body_width, standing_height=profile.standing_height),
            _asset_counts(level, refs),
            basis=["connected component of native portals and explicit native links; transient gating ignored"],
        )
        nodes.append(assembly_node)

        pieces: list[tuple[list[int], str | None]] = []
        covered: set[int] = set()
        for candidate, candidate_set in perceptual_sets:
            intersection = sorted(candidate_set & assembly_set)
            if not intersection:
                continue
            pieces.append((intersection, candidate["id"]))
            covered.update(intersection)
        for sector_id in sorted(assembly_set - covered):
            pieces.append(([sector_id], None))
        pieces.sort(key=lambda value: (value[0][0], len(value[0]), value[1] or ""))
        for local_number, (space_values, candidate_id) in enumerate(pieces, 1):
            space_id = f"{assembly_id}/space:{local_number:03d}"
            refs = _owned_refs(level, space_values)
            basis = ["perceptual-space intersection with its navigation assembly"] if candidate_id else [
                "sector not grouped by current perceptual-space evidence; retained as a reviewable singleton"
            ]
            nodes.append(_node(
                space_id, "space", f"space_{assembly_number:03d}_{local_number:03d}", assembly_id, refs,
                _geometry_summary(space_values, geometry, body_width=profile.body_width, standing_height=profile.standing_height),
                _asset_counts(level, refs), basis=basis, candidate=candidate_id,
            ))
            for sector_id in space_values:
                if sector_id in sector_to_space:
                    raise DecompilerError(f"perceptual hierarchy assigned sector {sector_id} twice")
                sector_to_space[sector_id] = space_id
            if refs["sprites"]:
                detail_id = f"{space_id}/details"
                detail_refs = {"sectors": [], "walls": [], "sprites": refs["sprites"]}
                nodes.append(_node(
                    detail_id, "detail_group", f"details_{assembly_number:03d}_{local_number:03d}", space_id,
                    detail_refs, None, _asset_counts(level, detail_refs),
                    basis=["native sprite placement inside the parent space; semantics remain unreviewed"],
                ))

    by_id = {item["id"]: item for item in nodes}
    for item in nodes:
        parent = item["parent"]
        if parent is not None:
            by_id[parent]["children"].append(item["id"])

    relations: list[dict[str, Any]] = []
    seen_connections: set[tuple[str, str, str]] = set()
    for portal in portals:
        left_sector, right_sector = _ids(portal["sectors"])
        left, right = sector_to_space[left_sector], sector_to_space[right_sector]
        if left == right:
            relations.append({
                "kind": "internal_connection", "within": left, "source": portal["id"],
                "wall_refs": _ids(portal["walls"]),
                "evidence": {
                    key: deepcopy(portal[key]) for key in (
                        "width", "at_rest_opening", "floor_delta", "blocking_flag"
                    ) if key in portal
                },
            })
            continue
        key = (min(left, right), max(left, right), portal["id"])
        if key in seen_connections:
            continue
        seen_connections.add(key)
        relations.append({
            "kind": "connects", "from": left, "to": right, "source": portal["id"],
            "wall_refs": _ids(portal["walls"]),
            "evidence": {
                key: deepcopy(portal[key]) for key in (
                    "width", "at_rest_opening", "floor_delta", "blocking_flag"
                ) if key in portal
            },
        })

    # Architectural structures: the layer between a perceptual space and one
    # sector.  Only the kinds that survived cross-corpus testing as things an
    # author draws become nodes.  Overlooks and pits are consequences of two
    # height decisions rather than drawn objects, so they stay relations; a node
    # per overlook would add a hundred entries to a campaign map and answer
    # nothing.
    structure_document = detect_structures(level, spatial=spatial)
    sector_to_assembly = {
        value: f"assembly:{number:03d}"
        for number, values in enumerate(assemblies, 1) for value in values
    }
    structure_nodes = {"stepped_run", "landing", "recess", "embedded_shell"}
    for item in structure_document["structures"]:
        owners = sorted({sector_to_assembly[value] for value in item["sectors"]})
        spaces = sorted({sector_to_space[value] for value in item["sectors"]})
        if item["kind"] not in structure_nodes:
            relations.append({
                "kind": item["kind"], "from": item["id"],
                "to": sorted({sector_to_space[value] for value in item["sectors"]}),
                "toward": sorted({sector_to_space[value] for value in item["attaches_to"]}),
                "source": item["id"], "evidence": deepcopy(item["parameters"]),
            })
            continue
        refs = _owned_refs(level, item["sectors"])
        nodes.append(_node(
            item["id"], "structure", item["id"].split(":", 2)[-1], owners[0], refs,
            _geometry_summary(
                item["sectors"], geometry,
                body_width=profile.body_width, standing_height=profile.standing_height,
            ),
            _asset_counts(level, refs),
            basis=[item["evidence"]["basis"]] + (
                [] if len(owners) == 1 else [f"spans navigation assemblies {owners}"]
            ),
        ))
        nodes[-1]["structure"] = {
            "kind": item["kind"],
            "parameters": deepcopy(item["parameters"]),
            "residual": deepcopy(item["residual"]),
            "attaches_to_spaces": sorted({
                sector_to_space[value] for value in item["attaches_to"]
            }),
        }
        for space_id in spaces:
            relations.append({
                "kind": "part_of", "from": item["id"], "to": space_id,
                "source": item["id"],
                "evidence": {"kind": item["kind"], "sectors": list(item["sectors"])},
            })
        by_id[owners[0]]["children"].append(item["id"])

    alternatives = [_compact_candidate(item) for item in spatial["hypotheses"]]
    for item in alternatives:
        if item["kind"] == "vertical_layer":
            owners = sorted({sector_to_space[value] for value in item["sector_ids"]})
            relations.append({
                "kind": "overlaps" if len(owners) > 1 else "embedded_in",
                "from": item["id"], "to": owners, "source": item["id"],
                "evidence": deepcopy(item["evidence"]),
            })

    aggregate: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for role, counts in _asset_counts(level, root_refs).items():
        for tile_id, count in counts.items():
            aggregate[int(tile_id)][role] += count
    assets = [{
        "id": f"blood:tile:{tile_id}",
        "native": {"game": "blood", "tile_id": tile_id},
        "local_alias": None,
        "verified_usage": dict(sorted(roles.items())),
        "interpreted_meaning": None,
        "interpretation_status": "unreviewed",
    } for tile_id, roles in sorted(aggregate.items())]

    result = LevelSource(
        source={
            "name": source_name,
            "game": "blood",
            "format": level.metadata.get("format", "Blood MAP"),
            "source_crc32": level.metadata.get("source_crc32"),
            "authority": "exact_level_ir",
        },
        exact_level_ir=level.to_dict(),
        hierarchy={
            "model": "reviewable primary hierarchy plus overlapping alternatives; never native truth",
            "primary_root": "level",
            "nodes": nodes,
            "relations": relations,
            "alternative_candidates": alternatives,
            "structure_recovery": {
                "model": structure_document["model"],
                "coverage": structure_document["coverage"],
                "limitations": structure_document["limitations"],
            },
            "limitations": [
                "names are neutral until semantic review",
                "navigation connectivity is a static at-rest approximation",
                "perceptual grouping uses portal/material continuity rather than renderer visibility",
                "mechanism and experience decomposition are intentionally out of scope",
                "structures are derived from geometry and overlap the spaces they belong to",
            ],
        },
        assets=assets,
    )
    result.validate()
    return result


def emit_python_source(source: LevelSource) -> str:
    """Emit executable, readable Python with one function per primary hierarchy node."""
    source.validate()
    document = pformat(source.to_dict(), width=100, sort_dicts=False)
    nodes = {item["id"]: item for item in source.hierarchy["nodes"]}
    function_names: dict[str, str] = {}
    used: set[str] = {"build_level", "level_source"}
    for item in source.hierarchy["nodes"]:
        base = "build_" + "".join(character if character.isalnum() else "_" for character in item["name"]).strip("_")
        name = base
        suffix = 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1
        used.add(name)
        function_names[item["id"]] = name

    lines = [
        '"""Generated by llmapper; edit interpretations, never exact source casually."""',
        "", "from bloodmap.decompiler import LevelSource", "",
        f"_DOCUMENT = {document}", "",
        "_SOURCE = LevelSource.from_dict(_DOCUMENT)", "",
    ]
    ordered = sorted(
        source.hierarchy["nodes"],
        key=lambda item: (item["kind"] == "level", item["kind"] == "assembly", item["id"]),
    )
    for item in ordered:
        function = function_names[item["id"]]
        calls = ", ".join(f"{function_names[child]}()" for child in item["children"])
        lines.extend([
            f"def {function}():",
            f"    node = _SOURCE.node({item['id']!r})",
            f"    node['compiled_children'] = [{calls}]" if calls else "    node['compiled_children'] = []",
            "    return node",
            "",
        ])
    root_function = function_names[source.hierarchy["primary_root"]]
    lines.extend([
        "def build_level():",
        f"    return {root_function}()",
        "",
        "def level_source():",
        "    return LevelSource.from_dict(_DOCUMENT)",
        "",
    ])
    return "\n".join(lines)
