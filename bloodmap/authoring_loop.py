"""One authored candidate, compiled and then independently explained.

This module is the integration seam of the reasoned authoring loop:

    LLM-authored source -> compile -> hard gates -> independent decompilation
    -> probes -> ART evidence -> declared views -> evidence packet -> revision

It owns no new analysis of its own.  Compilation is :mod:`bloodmap.planar_layout`,
structural truth is :mod:`bloodmap.analysis` and :mod:`bloodmap.geometry_audit`,
the independent critic is :func:`bloodmap.decompiler.decompile_level`, questions
are :mod:`bloodmap.probes`, and views are :mod:`bloodmap.viewpoints`.

Two rules hold everywhere below:

* An authored label is intent, never evidence.  ``role="courtyard"`` is recorded
  in the intent section and is never allowed to answer a question in the
  observation sections.
* Nothing is reduced to one quality number.  Structure, space, progression,
  material, and uncertainty stay separate and individually addressable.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .analysis import validate_map
from .build_ir import BuildIR
from .decompiler import decompile_level
from .format import encode_map, write_map
from .geometry_audit import authored_geometry_report, validate_authored_level
from .placement import validate_attachments, validate_use_poses
from .planar_layout import CompiledLayout, PlanarLayout
from .morphology import SHAPE_KEYS, shape_signature
from .player_space import player_profile
from . import probes as _probes  # noqa: F401 - import registers the probe implementations
from .probe_schema import DesignProbe, ProbeResult, run_probe
from .progression import analyze_progression
from .state_model import PlayerState, WorldState
from .viewpoints import (
    ViewpointSpec,
    prepare_viewpoints,
    viewpoint_manifest,
)

SCHEMA = "llmapper.authoring-iteration"
SCHEMA_VERSION = 1

EVIDENCE_NAMESPACES = (
    "gate", "decompiled", "probe", "view", "authored", "intent",
    "source", "art", "discrepancy", "transition", "scale", "shape", "sprite-scale",
    "structure",
)


class AuthoringLoopError(ValueError):
    """A candidate, its declared intent, or an evidence reference is malformed."""


# ---------------------------------------------------------------------------
# Authored intent (declaration only; never treated as observation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuthoredAssembly:
    """A major authored grouping of regions with one intended spatial identity."""

    assembly_id: str
    name: str
    role: str
    intent: str
    regions: tuple[str, ...]
    parent_assembly: str | None = None
    optional: bool = False
    mandatory: bool = True
    material_vocabulary: dict[str, Any] = field(default_factory=dict)
    landmarks: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "assembly_id": self.assembly_id, "name": self.name, "role": self.role,
            "intent": self.intent, "regions": list(self.regions),
            "parent_assembly": self.parent_assembly, "optional": self.optional,
            "mandatory": self.mandatory,
            "material_vocabulary": deepcopy(self.material_vocabulary),
            "landmarks": list(self.landmarks),
            "status": "authored declaration; not evidence about the compiled result",
        }


@dataclass(frozen=True)
class AuthoredTransition:
    """An authored moment of change between two regions and what it should do."""

    transition_id: str
    name: str
    from_region: str
    to_region: str
    kind: str
    intent: str
    connection_id: str | None = None
    expectation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id, "name": self.name,
            "from_region": self.from_region, "to_region": self.to_region,
            "kind": self.kind, "intent": self.intent,
            "connection_id": self.connection_id,
            "expectation": deepcopy(self.expectation),
            "status": "authored declaration; not evidence about the compiled result",
        }


@dataclass(frozen=True)
class AuthoredIntent:
    """Everything the author claims the level is supposed to be."""

    brief: str
    start_region: str
    exit_region: str
    assemblies: tuple[AuthoredAssembly, ...]
    transitions: tuple[AuthoredTransition, ...] = ()
    progression: tuple[dict[str, Any], ...] = ()
    landmarks: tuple[dict[str, Any], ...] = ()
    optional_regions: tuple[str, ...] = ()
    loops: tuple[dict[str, Any], ...] = ()
    material_vocabulary: dict[str, Any] = field(default_factory=dict)

    def assembly(self, assembly_id: str) -> AuthoredAssembly:
        for item in self.assemblies:
            if item.assembly_id == assembly_id:
                return item
        raise AuthoringLoopError(f"unknown authored assembly {assembly_id!r}")

    def region_owner(self, region_id: str) -> str | None:
        for item in self.assemblies:
            if region_id in item.regions:
                return item.assembly_id
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief": self.brief,
            "start_region": self.start_region,
            "exit_region": self.exit_region,
            "assemblies": [item.to_dict() for item in self.assemblies],
            "transitions": [item.to_dict() for item in self.transitions],
            "progression": [deepcopy(item) for item in self.progression],
            "landmarks": [deepcopy(item) for item in self.landmarks],
            "optional_regions": list(self.optional_regions),
            "loops": [deepcopy(item) for item in self.loops],
            "material_vocabulary": deepcopy(self.material_vocabulary),
            "authority": (
                "intent only. Every field here is what the author meant, and is "
                "deliberately excluded from the observation sections."
            ),
        }


@dataclass(frozen=True)
class ProbeRequest:
    """A brief-relevant question, declared against authored region IDs."""

    probe_id: str
    probe_type: str
    question: str
    relevance: str
    start_region: str | None = None
    target_region: str | None = None
    source_region: str | None = None
    destination_region: str | None = None
    opened_connections: tuple[str, ...] = ()
    alt_opened_connections: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Candidate:
    """One iteration of authored source plus everything needed to evaluate it."""

    iteration_id: str
    module: str
    factory: Callable[[], PlanarLayout]
    intent: AuthoredIntent
    probes: tuple[ProbeRequest, ...] = ()
    viewpoints: tuple[ViewpointSpec, ...] = ()
    parent: str | None = None
    declared_changes: tuple[str, ...] = ()
    mandatory_regions: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Compilation identity
# ---------------------------------------------------------------------------

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compile_candidate(candidate: Candidate) -> tuple[CompiledLayout, bytes, bool]:
    """Compile twice from a fresh factory and report byte determinism honestly."""
    compiled = candidate.factory().compile()
    first = encode_map(compiled.level.to_disk_map())
    second = encode_map(candidate.factory().compile().level.to_disk_map())
    return compiled, first, first == second


def _allocations(compiled: CompiledLayout) -> dict[str, int]:
    return {key: value.sector_id for key, value in compiled.allocations.items()}


def _sectors_for(compiled: CompiledLayout, regions: Iterable[str]) -> list[int]:
    allocations = _allocations(compiled)
    result: list[int] = []
    for region_id in regions:
        if region_id not in allocations:
            raise AuthoringLoopError(f"authored intent names unknown region {region_id!r}")
        result.append(allocations[region_id])
    return sorted(set(result))


def _gated_sectors(compiled: CompiledLayout) -> set[int]:
    return {
        compiled.allocations[key].sector_id
        for key, region in compiled.layout.regions.items()
        if region.type in {600, 602} or region.role in {"doorway", "gated_pocket"}
    }


def _zero_exit_sectors(compiled: CompiledLayout) -> set[int]:
    return {
        compiled.allocations[key].sector_id
        for key, region in compiled.layout.regions.items()
        if region.declared_zero_exit
    }


def connection_portals(compiled: CompiledLayout) -> dict[str, dict[str, Any]]:
    """Map each authored connection ID to the walls and portal ID it became."""
    result: dict[str, dict[str, Any]] = {}
    level = compiled.level
    for item in compiled.connection_report:
        if item["status"] != "realized":
            continue
        walls = sorted(
            compiled.wall_from_atomic[atomic]
            for atomic in item.get("atomic_ids", [])
            if atomic in compiled.wall_from_atomic
        )
        portals = []
        for wall_id in walls:
            other = int(level.walls[wall_id]["fields"]["next_wall"])
            portals.append(f"portal:{min(wall_id, other) if other >= 0 else wall_id}")
        entry = result.setdefault(item["connection_id"], {
            "connection_id": item["connection_id"],
            "region_a": item["region_a"], "region_b": item["region_b"],
            "role": item["role"], "walls": [], "portals": [], "widths": [],
        })
        entry["walls"].extend(walls)
        entry["portals"].extend(portals)
        entry["widths"].append(item["width"])
    for entry in result.values():
        entry["walls"] = sorted(set(entry["walls"]))
        entry["portals"] = sorted(set(entry["portals"]))
    return result


# ---------------------------------------------------------------------------
# Hard gates
# ---------------------------------------------------------------------------

def _gate(gate_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    if status not in {"pass", "fail", "skipped"}:
        raise AuthoringLoopError(f"invalid gate status {status!r}")
    return {"gate_id": gate_id, "status": status, "detail": detail, **extra}


_OVERLAP_CODES = {
    "footprint_partial_area_overlap",
    "footprint_full_containment_a_in_b",
    "footprint_full_containment_b_in_a",
}
_CONTACT_CODES = {"t_junction", "partial_collinear_overlap", "proper_crossing"}
_ADJACENCY_CODES = {
    "intended_adjacency_missing", "unresolved_intended_connection", "unintended_portal",
}


def _codes_gate(gate_id: str, diagnostics: list[dict[str, Any]], codes: set[str], detail: str) -> dict[str, Any]:
    hits = [item for item in diagnostics if item["severity"] == "error" and item["code"] in codes]
    return _gate(
        gate_id, "pass" if not hits else "fail",
        detail if not hits else f"{len(hits)} error(s): {hits[0]['code']} — {hits[0]['message']}",
        failures=[{"code": item["code"], "location": item["location"], "message": item["message"]} for item in hits[:8]],
    )


def run_hard_gates(
    candidate: Candidate,
    compiled: CompiledLayout,
    payload: bytes,
    deterministic: bool,
) -> list[dict[str, Any]]:
    """Every structural precondition, reported one by one and never merged."""
    level = compiled.level
    disk = level.to_disk_map()
    gates: list[dict[str, Any]] = []

    native_errors = [item for item in validate_map(disk) if item.severity == "error"]
    gates.append(_gate(
        "native_structure_valid", "pass" if not native_errors else "fail",
        "native Blood validation reports no errors" if not native_errors
        else f"{len(native_errors)} native error(s): {native_errors[0].code} at {native_errors[0].location}",
    ))

    diagnostics = validate_authored_level(
        level,
        intended_adjacency=[(item.region_a, item.region_b) for item in compiled.layout.connections.values()],
        gated_sectors=_gated_sectors(compiled),
        declared_zero_exit=_zero_exit_sectors(compiled),
        declared_specials=compiled.declared_specials,
        allocations=_allocations(compiled),
        connection_report=compiled.connection_report,
    )
    authored = authored_geometry_report(diagnostics)
    records = authored["diagnostics"]
    gates.append(_gate(
        "authored_geometry_valid", "pass" if authored["errors"] == 0 else "fail",
        f"{authored['errors']} authored error(s), {authored['warnings']} warning(s)",
        errors=authored["errors"], warnings=authored["warnings"],
    ))
    gates.append(_codes_gate("no_unintended_overlaps", records, _OVERLAP_CODES, "no unintended XY footprint overlap"))
    gates.append(_codes_gate("no_unresolved_boundary_contacts", records, _CONTACT_CODES,
                             "no T-junctions, partial collinear overlaps, or proper crossings"))
    gates.append(_codes_gate("intended_adjacency_realized", records, _ADJACENCY_CODES,
                             "every intended adjacency became a portal and no portal is unintended"))

    conservation = compiled.conservation.to_dict()
    gates.append(_gate(
        "geometry_conservation", "pass" if conservation["conserved"] else "fail",
        f"{conservation['source_directed_edges']} source edges -> "
        f"{conservation['emitted_directed_edges']} emitted; split {conservation['split_count']}",
        conservation=conservation,
    ))

    portals = connection_portals(compiled)
    unrealized = [
        item["connection_id"] for item in compiled.connection_report
        if item["status"] != "realized"
    ]
    narrow = [
        item["connection_id"] for item in compiled.connection_report
        if item["status"] == "realized" and not item["wide_enough"]
    ]
    gates.append(_gate(
        "portals_realized", "pass" if not unrealized and not narrow else "fail",
        f"{len(portals)} authored connections realized"
        if not unrealized and not narrow
        else f"unrealized={unrealized} narrower_than_declared={narrow}",
        unrealized=unrealized, narrower_than_declared=narrow,
    ))

    start = level.player_start
    start_sector = int(start["sector"])
    start_ok = 0 <= start_sector < len(level.sectors)
    gates.append(_gate(
        "player_start_valid", "pass" if start_ok else "fail",
        f"start sector:{start_sector} of {len(level.sectors)}",
        player_start=dict(start),
    ))

    profile = player_profile("blood")
    if start_ok:
        fields = level.sectors[start_sector]["fields"]
        clear = int(fields["floor_z"]) - int(fields["ceiling_z"])
        heights = round(clear / profile.standing_height, 3)
        gates.append(_gate(
            "player_relative_clearance", "pass" if clear >= profile.standing_height else "fail",
            f"start clear height {clear} = {heights} player heights",
            player_heights=heights,
        ))
    else:
        gates.append(_gate("player_relative_clearance", "skipped", "no valid player start to measure"))

    build = disk.to_build_ir()
    reachability = _required_reachability(candidate, compiled, build)
    gates.append(reachability)

    progression = analyze_progression(disk)
    gates.append(_gate(
        "exit_reachable", "pass" if progression["exit_reachable"] else "fail",
        "an exit is reachable under the declared progression"
        if progression["exit_reachable"]
        else "no exit was reached by the static progression witness",
        witness=progression.get("witness"),
        reachable_at_rest=progression["physical_reachable_at_rest"],
        final_reachable=progression["final_reachable"],
    ))

    attachments = validate_attachments(disk)
    poses = validate_use_poses(disk)
    gates.append(_gate(
        "object_attachment_valid", "pass" if attachments["ok"] and poses["ok"] else "fail",
        "sprite attachments and use poses are consistent"
        if attachments["ok"] and poses["ok"]
        else f"attachment violations={len(attachments['violations'])} pose violations={len(poses['violations'])}",
        attachment_violations=attachments["violations"][:8],
        use_pose_violations=poses["violations"][:8],
    ))

    gates.append(_gate(
        "deterministic_emission", "pass" if deterministic else "fail",
        f"two independent compiles produced {'identical' if deterministic else 'different'} bytes",
        map_sha256=_sha256(payload), bytes=len(payload),
    ))
    return gates


def _required_reachability(
    candidate: Candidate, compiled: CompiledLayout, build: BuildIR,
) -> dict[str, Any]:
    """Reach every declared-mandatory region with all authored gates opened."""
    mandatory = list(candidate.mandatory_regions)
    if not mandatory:
        mandatory = sorted({
            region
            for assembly in candidate.intent.assemblies
            if assembly.mandatory and not assembly.optional
            for region in assembly.regions
        })
    if not mandatory:
        return _gate("required_reachability", "skipped", "no mandatory regions were declared")
    allocations = _allocations(compiled)
    portals = connection_portals(compiled)
    opened = frozenset(
        portal for entry in portals.values() for portal in entry["portals"]
    )
    world = WorldState(opened_portals=opened, notes="every authored connection declared open")
    start_sector = int(compiled.level.player_start["sector"])
    unreachable: list[str] = []
    for region_id in mandatory:
        probe = DesignProbe(
            probe_type="access",
            question=f"is {region_id} reachable with all authored connections open?",
            player_state=PlayerState(sector=start_sector),
            world_state=world,
            parameters={"target_sector": allocations[region_id]},
        )
        if run_probe(probe, build).status != "pass":
            unreachable.append(region_id)
    return _gate(
        "required_reachability", "pass" if not unreachable else "fail",
        f"{len(mandatory) - len(unreachable)}/{len(mandatory)} mandatory regions reachable",
        mandatory_regions=mandatory, unreachable_regions=unreachable,
    )


def blocking_failures(gates: list[dict[str, Any]]) -> list[str]:
    return [item["gate_id"] for item in gates if item["status"] == "fail"]


# ---------------------------------------------------------------------------
# Independent hierarchy comparison
# ---------------------------------------------------------------------------

def _node_index(source) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in source.hierarchy["nodes"]}


def summarize_derived_hierarchy(source) -> dict[str, Any]:
    """Concise reading of what decompile_level independently derived."""
    nodes = source.hierarchy["nodes"]
    assemblies = [item for item in nodes if item["kind"] == "assembly"]
    spaces = [item for item in nodes if item["kind"] == "space"]
    details = [item for item in nodes if item["kind"] == "detail_group"]
    singletons = [item for item in spaces if len(item["sources"]["sectors"]) == 1]
    relations = source.hierarchy["relations"]
    connects = [item for item in relations if item["kind"] == "connects"]
    overlaps = [item for item in relations if item["kind"] in {"overlaps", "embedded_in"}]
    candidates = source.hierarchy["alternative_candidates"]
    structures = [item for item in nodes if item["kind"] == "structure"]
    # An overlook or a pit is a relation rather than a drawn object, so the
    # decompiler files it as one; the packet reports the count and the extremes
    # instead of a hundred near-identical entries.
    relational = [item for item in relations if item["kind"] in {"overlook", "pit"}]
    return {
        "derived_structures": [{
            "id": item["id"],
            "kind": item["structure"]["kind"],
            "parent": item["parent"],
            "sectors": item["sources"]["sectors"],
            "parameters": item["structure"]["parameters"],
            "residual": item["structure"]["residual"],
            "attaches_to_spaces": item["structure"]["attaches_to_spaces"],
        } for item in structures],
        "structure_relations": {
            "counts": {
                kind: sum(1 for item in relational if item["kind"] == kind)
                for kind in ("overlook", "pit")
            },
            "largest_drops": sorted(
                ({
                    "id": item["from"], "kind": item["kind"], "spaces": item["to"],
                    "toward": item["toward"],
                    "measure": item["evidence"].get("drop") or item["evidence"].get("depth"),
                } for item in relational),
                key=lambda row: -(row["measure"] or 0),
            )[:8],
        },
        "structure_recovery": source.hierarchy["structure_recovery"],
        "derived_assemblies": [{
            "id": item["id"], "sectors": len(item["sources"]["sectors"]),
            "geometry": item["geometry"],
        } for item in assemblies],
        "derived_spaces": [{
            "id": item["id"], "parent": item["parent"],
            "sectors": item["sources"]["sectors"],
            "sprites": len(item["sources"]["sprites"]),
            "player_relative": item["geometry"]["player_relative"],
            "floor_z_range": item["geometry"]["floor_z_range"],
            "spatial_candidate": item["provenance"]["spatial_candidate"],
        } for item in spaces],
        "counts": {
            "assemblies": len(assemblies), "spaces": len(spaces),
            "singleton_spaces": len(singletons), "detail_groups": len(details),
            "cross_space_connections": len(connects),
            "vertical_overlap_relations": len(overlaps),
            "structures": len(structures),
        },
        "singleton_space_ids": [item["id"] for item in singletons],
        "major_connections": [{
            "from": item["from"], "to": item["to"], "portal": item["source"],
            "width": item["evidence"].get("width"),
            "at_rest_opening": item["evidence"].get("at_rest_opening"),
            "floor_delta": item["evidence"].get("floor_delta"),
        } for item in connects],
        "vertical_overlaps": [{
            "candidate": item["from"], "spaces": item["to"], "relation": item["kind"],
            "evidence": item["evidence"],
        } for item in overlaps],
        "material_continuity_candidates": [
            {"id": item["id"], "sectors": item["sector_ids"], "evidence": item["evidence"]}
            for item in candidates if item["kind"] == "material_region"
        ],
        "detail_group_distribution": [
            {"id": item["id"], "parent": item["parent"], "sprites": len(item["sources"]["sprites"])}
            for item in details
        ],
        "basis": "bloodmap.decompiler.decompile_level over the compiled candidate only",
        "limitations": list(source.hierarchy["limitations"]),
    }


def _sector_areas(level) -> dict[int, float]:
    """Absolute polygon area per sector, rebuilt from point2 wall loops."""
    from .planar_geom import area2
    from .viewpoints import _sector_loops

    result: dict[int, float] = {}
    for sector_id in range(len(level.sectors)):
        loops = _sector_loops(level, sector_id)
        # The first loop is the outer boundary; later loops are holes and carry
        # the opposite winding, so the signed sum already subtracts them.
        result[sector_id] = abs(sum(area2(tuple(loop)) for loop in loops)) / 2.0
    return result


def _discrepancy(
    identifier: str, kind: str, description: str, rule: str, evidence: list[str], **extra: Any,
) -> dict[str, Any]:
    return {
        "id": identifier, "kind": kind, "description": description,
        "rule": rule, "evidence": evidence,
        "status": "derived observation; not a verdict on design quality",
        **extra,
    }


def compare_hierarchies(
    candidate: Candidate, compiled: CompiledLayout, source,
) -> dict[str, Any]:
    """Set authored grouping beside independently derived grouping."""
    allocations = _allocations(compiled)
    sector_to_region = {value: key for key, value in allocations.items()}
    nodes = _node_index(source)
    spaces = [item for item in source.hierarchy["nodes"] if item["kind"] == "space"]
    space_of: dict[int, str] = {}
    for item in spaces:
        for sector_id in item["sources"]["sectors"]:
            space_of[sector_id] = item["id"]
    assembly_of: dict[int, str] = {}
    for item in source.hierarchy["nodes"]:
        if item["kind"] == "assembly":
            for sector_id in item["sources"]["sectors"]:
                assembly_of[sector_id] = item["id"]

    transition_regions = {
        key for key, region in compiled.layout.regions.items()
        if region.role in {"doorway", "stair", "gated_pocket", "gateway", "threshold"}
    }

    areas = _sector_areas(compiled.level)
    rows: list[dict[str, Any]] = []
    discrepancies: list[dict[str, Any]] = []
    space_owners: dict[str, set[str]] = {}

    for assembly in candidate.intent.assemblies:
        sectors = _sectors_for(compiled, assembly.regions)
        derived_assemblies = sorted({assembly_of[value] for value in sectors})
        counts: dict[str, int] = {}
        for value in sectors:
            counts[space_of[value]] = counts.get(space_of[value], 0) + 1
        covered_spaces = sorted(counts)
        for space_id in covered_spaces:
            space_owners.setdefault(space_id, set()).add(assembly.assembly_id)
        singletons = [
            space_id for space_id in covered_spaces
            if len(nodes[space_id]["sources"]["sectors"]) == 1
        ]
        # A closed Z-door has no at-rest opening, so it can never be grouped with
        # anything and is always its own space.  Counting those as fragmentation
        # would flag every gated room in every Blood map.  Only rooms that ended
        # up alone say something about how the assembly reads.
        room_singletons = [
            space_id for space_id in singletons
            if sector_to_region.get(nodes[space_id]["sources"]["sectors"][0]) not in transition_regions
        ]
        # Share is measured by floor area, not sector count: a 392 player-area
        # room flanked by two 16 player-area arches is one place with two
        # thresholds, even though it is one sector out of three.
        area_by_space: dict[str, float] = {}
        for value in sectors:
            area_by_space[space_of[value]] = area_by_space.get(space_of[value], 0.0) + areas.get(value, 0.0)
        assembly_area = sum(area_by_space.values())
        dominant = max(area_by_space.items(), key=lambda item: (item[1], item[0])) if area_by_space else None
        share = round(dominant[1] / assembly_area, 4) if dominant and assembly_area else 0.0
        sector_share = round(max(counts.values()) / len(sectors), 4) if counts else 0.0
        rows.append({
            "assembly_id": assembly.assembly_id,
            "authored_name": assembly.name,
            "authored_role": assembly.role,
            "authored_regions": list(assembly.regions),
            "sectors": sectors,
            "derived_assemblies": derived_assemblies,
            "derived_spaces": [{
                "id": space_id,
                "shared_sectors": counts[space_id],
                "space_sector_count": len(nodes[space_id]["sources"]["sectors"]),
            } for space_id in covered_spaces],
            "derived_space_count": len(covered_spaces),
            "singleton_space_ids": singletons,
            "room_singleton_space_ids": room_singletons,
            "dominant_space": None if dominant is None else dominant[0],
            "dominant_space_share": share,
            "dominant_space_share_basis": "floor area",
            "dominant_space_sector_share": sector_share,
        })

        base_evidence = [f"intent:{assembly.assembly_id}"] + [
            f"decompiled:{space_id}" for space_id in covered_spaces
        ]
        if len(derived_assemblies) > 1:
            discrepancies.append(_discrepancy(
                f"discrepancy:{assembly.assembly_id}:split",
                "assembly_split_across_navigation_components",
                f"authored assembly {assembly.name!r} spans {len(derived_assemblies)} independent "
                "navigation components, so parts of it are not connected to each other",
                "derived assembly count for one authored assembly > 1",
                [f"intent:{assembly.assembly_id}"] + [f"decompiled:{value}" for value in derived_assemblies],
                derived_assemblies=derived_assemblies,
            ))
        if len(sectors) > 1 and share < 0.4:
            discrepancies.append(_discrepancy(
                f"discrepancy:{assembly.assembly_id}:fragmented",
                "assembly_lacks_dominant_perceptual_space",
                f"authored assembly {assembly.name!r} is split over {len(covered_spaces)} derived "
                f"perceptual spaces and its largest one holds only {round(share * 100)}% of its floor area",
                "largest derived space share of an authored assembly's floor area < 0.40",
                base_evidence, dominant_space_share=share,
            ))
        if len(room_singletons) >= 2:
            discrepancies.append(_discrepancy(
                f"discrepancy:{assembly.assembly_id}:singletons",
                "assembly_contains_perceptual_singletons",
                f"{len(room_singletons)} non-circulation sector(s) of {assembly.name!r} were grouped "
                "with nothing else, so they read as separate incidental spaces rather than one place",
                "authored assembly contains >= 2 single-sector derived spaces that are not doorways, "
                "gateways, or stairs",
                [f"intent:{assembly.assembly_id}"] + [f"decompiled:{value}" for value in room_singletons],
                room_singleton_space_ids=room_singletons,
                all_singleton_space_ids=singletons,
            ))

    for space_id, owners in sorted(space_owners.items()):
        if len(owners) > 1:
            discrepancies.append(_discrepancy(
                f"discrepancy:{space_id.replace('/', '.')}:collapsed",
                "authored_assemblies_share_one_perceptual_space",
                f"authored assemblies {sorted(owners)} were grouped into the single derived space "
                f"{space_id}, so their intended identities are not perceptually separated",
                "one derived space contains sectors from more than one authored assembly",
                [f"decompiled:{space_id}"] + [f"intent:{value}" for value in sorted(owners)],
                authored_assemblies=sorted(owners),
            ))

    areas = _sector_areas(compiled.level)
    for space in spaces:
        members = space["sources"]["sectors"]
        if len(members) < 2:
            continue
        transitional = [
            value for value in members
            if sector_to_region.get(value) in transition_regions
        ]
        # A space made only of stair steps is a stair, not a finding.  The
        # interesting case is a space that is supposed to be somewhere and is
        # swamped by circulation.  Sector count answers this badly -- one large
        # room beside six tiny steps is six-of-seven sectors and 4% of the floor
        # -- so the discrepancy fires on floor area and reports both.
        if not transitional or len(transitional) == len(members):
            continue
        total_area = sum(areas.get(value, 0.0) for value in members)
        transition_area = sum(areas.get(value, 0.0) for value in transitional)
        area_share = round(transition_area / total_area, 4) if total_area else 0.0
        if area_share <= 0.5:
            continue
        discrepancies.append(_discrepancy(
            f"discrepancy:{space['id'].replace('/', '.')}:transition-dominated",
            "transition_regions_dominate_space",
            f"derived space {space['id']} is mostly authored doorway/stair floor area "
            f"({round(area_share * 100)}%, {len(transitional)} of {len(members)} sectors), "
            "so the space reads as circulation rather than as a destination",
            "authored doorway/stair regions hold more than half of a mixed derived space's floor area",
            [f"decompiled:{space['id']}"] + [
                f"authored:{sector_to_region[value]}" for value in transitional
                if value in sector_to_region
            ],
            transition_area_share=area_share,
            transition_sector_share=round(len(transitional) / len(members), 4),
        ))

    for assembly in candidate.intent.assemblies:
        if not assembly.parent_assembly:
            continue
        child_spaces = {space_of[value] for value in _sectors_for(compiled, assembly.regions)}
        parent = candidate.intent.assembly(assembly.parent_assembly)
        parent_spaces = {space_of[value] for value in _sectors_for(compiled, parent.regions)}
        shared = sorted(child_spaces & parent_spaces)
        if shared:
            discrepancies.append(_discrepancy(
                f"discrepancy:{assembly.assembly_id}:containment",
                "embedded_structure_merged_into_host",
                f"authored embedded structure {assembly.name!r} shares derived space(s) {shared} "
                f"with its host {parent.name!r}, so it does not read as a distinct interior",
                "an authored child assembly shares a derived perceptual space with its parent",
                [f"intent:{assembly.assembly_id}", f"intent:{parent.assembly_id}"]
                + [f"decompiled:{value}" for value in shared],
            ))

    return {
        "model": (
            "authored grouping is a declaration; derived grouping comes only from "
            "decompile_level over the compiled MAP"
        ),
        "assemblies": rows,
        "discrepancies": discrepancies,
        "unmatched_regions": sorted(
            set(allocations) - {
                region for assembly in candidate.intent.assemblies for region in assembly.regions
            }
        ),
    }


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def run_requested_probes(
    candidate: Candidate, compiled: CompiledLayout, build: BuildIR,
) -> list[dict[str, Any]]:
    allocations = _allocations(compiled)
    portals = connection_portals(compiled)

    def portal_ids(names: Iterable[str]) -> frozenset[str]:
        result: set[str] = set()
        for name in names:
            if name not in portals:
                raise AuthoringLoopError(f"probe names unrealized connection {name!r}")
            result.update(portals[name]["portals"])
        return frozenset(result)

    def sector_of(region_id: str | None) -> int | None:
        if region_id is None:
            return None
        if region_id not in allocations:
            raise AuthoringLoopError(f"probe names unknown region {region_id!r}")
        return allocations[region_id]

    results: list[dict[str, Any]] = []
    for request in candidate.probes:
        parameters = dict(request.parameters)
        target = sector_of(request.target_region)
        if target is not None:
            parameters["target_sector"] = target
        source_sector = sector_of(request.source_region)
        if source_sector is not None:
            parameters["source_sector"] = source_sector
        destination = sector_of(request.destination_region)
        if destination is not None:
            parameters["destination_sector"] = destination
        if request.alt_opened_connections:
            parameters["alt_world_state"] = WorldState(
                opened_portals=portal_ids(request.alt_opened_connections),
            ).to_dict()
        start = sector_of(request.start_region)
        probe = DesignProbe(
            probe_type=request.probe_type,
            question=request.question,
            player_state=PlayerState(
                sector=int(compiled.level.player_start["sector"]) if start is None else start,
            ),
            world_state=WorldState(
                opened_portals=portal_ids(request.opened_connections),
                notes="portals declared open by the authored probe request",
            ),
            parameters=parameters,
        )
        result: ProbeResult = run_probe(probe, build)
        results.append({
            "probe_id": request.probe_id,
            "relevance": request.relevance,
            "declared": {
                "probe_type": request.probe_type,
                "start_region": request.start_region,
                "target_region": request.target_region,
                "source_region": request.source_region,
                "destination_region": request.destination_region,
                "opened_connections": list(request.opened_connections),
                "alt_opened_connections": list(request.alt_opened_connections),
            },
            "probe": probe.to_dict(),
            "result": result.to_dict(),
        })
    return results


# ---------------------------------------------------------------------------
# ART and visual-composition evidence
# ---------------------------------------------------------------------------

def sprite_scale_evidence(
    compiled: CompiledLayout, *, art_directory: str | Path | None = None,
) -> dict[str, Any]:
    """Measure every sprite against the room it stands in.

    A decoration is the wrong size when it is large relative to its own space,
    not when its repeats differ from the corpus mode: the same censer is right in
    a twelve player-height gallery and absurd in a low side chapel.  Needs the
    local ART set for tile dimensions and reports honestly when it is absent.
    """
    level = compiled.level
    profile = player_profile("blood")
    if art_directory is None or not Path(art_directory).is_dir():
        return {
            "status": "unavailable",
            "note": "no local ART directory was supplied, so sprite world size cannot be measured",
            "sprites": [], "findings": [],
        }
    from .art import read_art_directory

    try:
        tiles = read_art_directory(art_directory)
    except Exception as exc:  # noqa: BLE001 - a missing or odd ART set must not fail the packet
        return {
            "status": "unavailable",
            "note": f"could not read the ART directory: {type(exc).__name__}: {exc}",
            "sprites": [], "findings": [],
        }

    areas = _sector_areas(level)
    allocations = _allocations(compiled)
    sector_to_region = {value: key for key, value in allocations.items()}
    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for index, sprite in enumerate(level.sprites):
        fields = sprite["fields"]
        tile = tiles.get(int(fields["picnum"]))
        if tile is None or not tile.height:
            continue
        sector_id = int(fields["sector"])
        if not 0 <= sector_id < len(level.sectors):
            continue
        sector = level.sectors[sector_id]["fields"]
        clear = int(sector["floor_z"]) - int(sector["ceiling_z"])
        # Build renders a sprite at tile size times repeat times four world units.
        world_height = tile.height * int(fields["y_repeat"]) * 4
        world_width = tile.width * int(fields["x_repeat"]) * 4
        share = round(world_height / clear, 4) if clear > 0 else None
        row = {
            "sprite": f"sprite:{index}",
            "picnum": int(fields["picnum"]),
            "region": sector_to_region.get(sector_id),
            "height_player_heights": round(world_height / profile.standing_height, 2),
            "width_player_widths": round(world_width / profile.body_width, 2),
            "sector_clear_player_heights": round(clear / profile.standing_height, 2),
            "height_share_of_sector_clearance": share,
            "footprint_share_of_sector": (
                round((world_width ** 2) / areas[sector_id], 4)
                if areas.get(sector_id) else None
            ),
        }
        rows.append(row)
        if share is not None and share > 0.75 and int(fields["type"]) == 0:
            findings.append({
                "id": f"sprite-scale:{index}",
                "kind": "decoration_large_relative_to_its_space",
                "description": (
                    f"sprite:{index} (tile {int(fields['picnum'])}) in "
                    f"{sector_to_region.get(sector_id)} is {row['height_player_heights']} player "
                    f"heights tall in a space {row['sector_clear_player_heights']} player heights "
                    f"clear, filling {round(share * 100)}% of the available height"
                ),
                "rule": "a type-0 decoration taller than 75% of its sector's clear height",
                "evidence": [f"source:sprite:{index}", f"art:blood:tile:{int(fields['picnum'])}"],
                "status": "derived observation; some decorations are meant to span floor to ceiling",
            })
    return {
        "status": "measured",
        "art_directory": str(art_directory),
        "sprites": rows,
        "findings": findings,
        "limitations": [
            "world size is tile size times repeat times four; slopes and pitch are ignored",
            "chains and vines are often intended to span a whole wall, so a finding here is a "
            "question about intent rather than a defect",
        ],
    }


def _load_catalog(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.is_file():
        return None
    return json.loads(candidate.read_text(encoding="utf-8"))


def _asset_note(catalog: dict[str, Any] | None, tile_id: int) -> dict[str, Any]:
    """Separate verified corpus usage from interpreted meaning; never invent either."""
    key = f"blood:tile:{tile_id}"
    if catalog is None or key not in catalog.get("assets", {}):
        return {
            "asset": key, "knowledge": "unknown",
            "note": "no mined material knowledge was supplied for this tile",
        }
    asset = catalog["assets"][key]
    usage = asset.get("usage", {})
    annotation = (catalog.get("annotations") or {}).get(key)
    record: dict[str, Any] = {
        "asset": key,
        "knowledge": "verified_usage_only" if annotation is None else "verified_usage_plus_interpreted_role",
        "verified_usage": {
            "total": usage.get("total", 0), "wall": usage.get("wall", 0),
            "floor": usage.get("floor", 0), "ceiling": usage.get("ceiling", 0),
            "sprite": usage.get("sprite", 0), "maps": usage.get("maps", 0),
        },
        "verified_shade_median": (asset.get("distributions", {}).get("shade") or {}).get("median"),
    }
    if annotation is None:
        record["interpreted_role"] = None
        record["uncertainty"] = "no reviewed annotation exists for this tile"
    else:
        values = annotation.get("values") or {}
        record["interpreted_role"] = {
            facet: values[facet]["value"] for facet in sorted(values)
        }
        record["interpretation_provenance"] = annotation.get("provenance")
        record["interpretation_basis"] = annotation.get("basis")
    return record


def _dominant(counts: dict[str, int], limit: int = 3) -> list[dict[str, Any]]:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], int(item[0])))
    return [{"tile": int(tile), "count": count} for tile, count in ordered[:limit]]


def _shade_range(level, sector_ids: list[int]) -> dict[str, int]:
    values: list[int] = []
    for sector_id in sector_ids:
        fields = level.sectors[sector_id]["fields"]
        values.extend([int(fields["floor_shade"]), int(fields["ceiling_shade"])])
    return {"min": min(values), "max": max(values)} if values else {"min": 0, "max": 0}


def _palette(usage: dict[str, dict[str, int]]) -> frozenset[str]:
    return frozenset(
        f"{role}:{tile}" for role in ("floor", "ceiling", "wall")
        for tile in usage.get(role, {})
    )


def art_evidence(
    candidate: Candidate,
    compiled: CompiledLayout,
    source,
    comparison: dict[str, Any],
    *,
    catalog_path: str | Path | None = None,
    surface_corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Material and decoration evidence per derived node, with honest unknowns."""
    catalog = _load_catalog(catalog_path)
    level = compiled.level
    nodes = _node_index(source)
    interesting = [
        item for item in source.hierarchy["nodes"] if item["kind"] in {"assembly", "space"}
    ]
    tiles_seen: set[int] = set()
    records: list[dict[str, Any]] = []
    for node in interesting:
        usage = node["material_usage"]
        sectors = node["sources"]["sectors"]
        dominant = {
            role: _dominant(usage.get(role, {}))
            for role in ("floor", "ceiling", "wall", "wall_overlay", "sprite")
        }
        for role_values in dominant.values():
            tiles_seen.update(item["tile"] for item in role_values)
        distinct = {role: len(usage.get(role, {})) for role in ("floor", "ceiling", "wall")}
        records.append({
            "node": node["id"],
            "kind": node["kind"],
            "sectors": len(sectors),
            "dominant": dominant,
            "distinct_tile_counts": distinct,
            "sprite_count": len(node["sources"]["sprites"]),
            "shade_range": _shade_range(level, sectors),
            "repetition": {
                role: round(
                    max(usage.get(role, {}).values(), default=0) / max(1, sum(usage.get(role, {}).values())), 4,
                )
                for role in ("floor", "ceiling", "wall")
            },
        })

    empty_spaces = [
        item["node"] for item in records
        if item["kind"] == "space" and item["sprite_count"] == 0 and item["sectors"] >= 1
    ]
    sprite_totals = {
        item["node"]: item["sprite_count"] for item in records if item["kind"] == "space"
    }
    total_sprites = sum(sprite_totals.values())
    concentration = (
        round(max(sprite_totals.values()) / total_sprites, 4) if total_sprites else 0.0
    )

    palettes = {
        item["id"]: _palette(item["material_usage"])
        for item in source.hierarchy["nodes"] if item["kind"] == "space"
    }
    assembly_rows = {row["assembly_id"]: row for row in comparison["assemblies"]}
    near_identical: list[dict[str, Any]] = []
    declared = list(candidate.intent.assemblies)
    for index, left in enumerate(declared):
        for right in declared[index + 1:]:
            left_spaces = [item["id"] for item in assembly_rows[left.assembly_id]["derived_spaces"]]
            right_spaces = [item["id"] for item in assembly_rows[right.assembly_id]["derived_spaces"]]
            left_palette = frozenset().union(*(palettes[value] for value in left_spaces)) if left_spaces else frozenset()
            right_palette = frozenset().union(*(palettes[value] for value in right_spaces)) if right_spaces else frozenset()
            union = left_palette | right_palette
            if not union:
                continue
            overlap = round(len(left_palette & right_palette) / len(union), 4)
            if overlap >= 0.6:
                near_identical.append({
                    "assemblies": [left.assembly_id, right.assembly_id],
                    "surface_vocabulary_overlap": overlap,
                    "evidence": [f"intent:{left.assembly_id}", f"intent:{right.assembly_id}"],
                    "rule": "shared floor/ceiling/wall tile vocabulary >= 0.60 of the union",
                })

    # Whole-assembly vocabulary overlap is diluted by stair and doorway sectors,
    # which every assembly shares.  Compare the room sectors' dominant surface
    # triple as well, so two rooms finished identically are named even when their
    # circulation differs.
    allocations = _allocations(compiled)
    room_roles_excluded = {"doorway", "stair", "gated_pocket"}
    dominant_surfaces: dict[str, dict[str, int] | None] = {}
    for assembly in candidate.intent.assemblies:
        rooms = [
            allocations[region] for region in assembly.regions
            if compiled.layout.regions[region].role not in room_roles_excluded
        ]
        if not rooms:
            dominant_surfaces[assembly.assembly_id] = None
            continue
        counters: dict[str, Counter[int]] = {"floor": Counter(), "ceiling": Counter(), "wall": Counter()}
        for sector_id in rooms:
            fields = level.sectors[sector_id]["fields"]
            counters["floor"][int(fields["floor_picnum"])] += 1
            counters["ceiling"][int(fields["ceiling_picnum"])] += 1
            first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
            for wall_id in range(first, first + count):
                counters["wall"][int(level.walls[wall_id]["fields"]["picnum"])] += 1
        dominant_surfaces[assembly.assembly_id] = {
            role: min(values.items(), key=lambda item: (-item[1], item[0]))[0]
            for role, values in counters.items() if values
        }
    identical_rooms: list[dict[str, Any]] = []
    for index, left in enumerate(declared):
        for right in declared[index + 1:]:
            left_surfaces = dominant_surfaces.get(left.assembly_id)
            right_surfaces = dominant_surfaces.get(right.assembly_id)
            if left_surfaces and left_surfaces == right_surfaces:
                identical_rooms.append({
                    "assemblies": [left.assembly_id, right.assembly_id],
                    "dominant_surfaces": dict(left_surfaces),
                    "evidence": [f"intent:{left.assembly_id}", f"intent:{right.assembly_id}"],
                    "rule": "room sectors of both assemblies share the same dominant floor, ceiling, and wall tile",
                })

    transitions: list[dict[str, Any]] = []
    for transition in candidate.intent.transitions:
        left, right = allocations.get(transition.from_region), allocations.get(transition.to_region)
        if left is None or right is None:
            continue
        left_fields = level.sectors[left]["fields"]
        right_fields = level.sectors[right]["fields"]
        changed = {
            "floor_tile_changed": int(left_fields["floor_picnum"]) != int(right_fields["floor_picnum"]),
            "ceiling_tile_changed": int(left_fields["ceiling_picnum"]) != int(right_fields["ceiling_picnum"]),
            "floor_shade_delta": int(right_fields["floor_shade"]) - int(left_fields["floor_shade"]),
            "clear_height_delta": (
                (int(right_fields["floor_z"]) - int(right_fields["ceiling_z"]))
                - (int(left_fields["floor_z"]) - int(left_fields["ceiling_z"]))
            ),
        }
        transitions.append({
            "transition_id": transition.transition_id,
            "from": f"sector:{left}", "to": f"sector:{right}",
            "material_change": changed,
            "any_surface_change": changed["floor_tile_changed"] or changed["ceiling_tile_changed"]
            or changed["floor_shade_delta"] != 0,
            "evidence": [f"transition:{transition.transition_id}", f"source:sector:{left}", f"source:sector:{right}"],
        })

    # A sector finished with one tile on floor, ceiling and walls loses its own
    # edges in the renderer.  Originals do it, sparingly; the useful measure is
    # the fraction of the level built that way, against the corpus.
    from .materials import single_surface_sectors

    single = single_surface_sectors(level)
    fraction = round(len(single) / max(1, len(level.sectors)), 4)
    samples = list((surface_corpus or {}).get("fraction_samples") or [])
    surface_treatment = {
        "single_surface_sectors": single,
        "fraction": fraction,
        "corpus_percentile": _percentile(fraction, samples),
        "corpus": (surface_corpus or {}).get("summary"),
        "corpus_maps": (surface_corpus or {}).get("maps"),
        "reading": _band(_percentile(fraction, samples)) if samples else "no corpus",
        "rule": "floor tile, ceiling tile and dominant wall tile are all the same",
    }

    known = [_asset_note(catalog, tile) for tile in sorted(tiles_seen)]
    unknown = [item["asset"] for item in known if item["knowledge"] == "unknown"]
    return {
        "surface_treatment": surface_treatment,
        "catalog": None if catalog is None else str(catalog_path),
        "catalog_status": "absent" if catalog is None else "loaded",
        "nodes": records,
        "assets": known,
        "unresolved_assets": unknown,
        "visually_empty_spaces": empty_spaces,
        "decorative_distribution": {
            "total_space_sprites": total_sprites,
            "largest_share_in_one_space": concentration,
            "per_space": sprite_totals,
        },
        "near_identical_treatments": near_identical,
        "identical_room_treatments": identical_rooms,
        "assembly_dominant_surfaces": {
            key: value for key, value in sorted(dominant_surfaces.items())
        },
        "transition_material_evidence": transitions,
        "limitations": [
            "tile identity is exact; tile meaning is either mined-and-interpreted or unknown",
            "surface vocabulary overlap is a raw tile-set measure, not a perceived-similarity model",
            "no claim is made here about how a surface actually looks in the renderer",
        ],
    }


# ---------------------------------------------------------------------------
# Corpus-relative scale and shape
# ---------------------------------------------------------------------------

def _percentile(value: float | None, samples: Sequence[float]) -> float | None:
    if value is None or not samples:
        return None
    ordered = sorted(float(item) for item in samples)
    below = sum(1 for item in ordered if item <= float(value))
    return round(100.0 * below / len(ordered), 1)


def _band(percentile: float | None) -> str:
    if percentile is None:
        return "no corpus"
    if percentile <= 10:
        return "below the corpus tenth percentile"
    if percentile >= 90:
        return "above the corpus ninetieth percentile"
    return "inside the corpus central mass"


def corpus_scale_evidence(
    compiled: CompiledLayout,
    source,
    *,
    spatial_corpus: dict[str, Any] | None = None,
    shape_corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Place the candidate's scale and shape against original-map distributions.

    Player-relative numbers on their own do not say whether a space is right.
    "Four player heights" only means something next to what original maps of the
    same footprint actually do, so every height here is reported as a percentile
    against corpus sectors of comparable size, not against the whole corpus.
    """
    level = compiled.level
    profile = player_profile("blood")
    areas = _sector_areas(level)
    allocations = _allocations(compiled)
    sector_to_region = {value: key for key, value in allocations.items()}

    paired: list[tuple[float, float]] = []
    all_heights: list[float] = []
    all_areas: list[float] = []
    # Sky-lit sectors are their own population: the corpus median clear height
    # is 11.6 player heights under a sky and 5.8 over the whole corpus, so a
    # courtyard measured against every sector of its footprint is mostly being
    # measured against interiors.
    sky_heights: list[float] = []
    if spatial_corpus:
        all_areas = [float(v) for v in spatial_corpus.get("footprint_player_areas", [])]
        all_heights = [float(v) for v in spatial_corpus.get("clear_height_player_heights", [])]
        sky_heights = [float(v) for v in spatial_corpus.get("sky_clear_height_player_heights", [])]
        if len(all_areas) == len(all_heights):
            paired = list(zip(all_areas, all_heights))

    def size_matched(area: float) -> list[float]:
        """Corpus heights for sectors within half to double this footprint."""
        if not paired or area <= 0:
            return []
        low, high = area / 2.0, area * 2.0
        matched = [height for other, height in paired if low <= other <= high]
        return matched if len(matched) >= 30 else []

    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for node in source.hierarchy["nodes"]:
        if node["kind"] != "space":
            continue
        members = node["sources"]["sectors"]
        footprint = sum(areas.get(value, 0.0) for value in members) / (profile.body_width ** 2)
        heights = [
            (int(level.sectors[value]["fields"]["floor_z"])
             - int(level.sectors[value]["fields"]["ceiling_z"])) / profile.standing_height
            for value in members
        ]
        # Weight by floor area, not by sector: a courtyard with six tiny stair
        # steps in it is as tall as the courtyard, and its median sector is a step.
        weights = [areas.get(value, 0.0) for value in members]
        total_weight = sum(weights)
        median_height = (
            sum(h * w for h, w in zip(heights, weights)) / total_weight
            if total_weight else (sorted(heights)[len(heights) // 2] if heights else None)
        )
        plain_median = sorted(heights)[len(heights) // 2] if heights else None
        matched = size_matched(footprint)
        matched_percentile = _percentile(median_height, matched)
        sky_members = [
            value for value in members
            if int(level.sectors[value]["fields"]["ceiling_stat"]) & 1
        ]
        row = {
            "node": node["id"],
            "regions": [sector_to_region.get(value) for value in members],
            "footprint_player_areas": round(footprint, 2),
            "clear_height_player_heights_area_weighted": None if median_height is None else round(median_height, 2),
            "clear_height_player_heights_sector_median": None if plain_median is None else round(plain_median, 2),
            "footprint_corpus_percentile": _percentile(footprint, all_areas),
            "height_corpus_percentile": _percentile(median_height, all_heights),
            "height_percentile_vs_same_size_corpus_sectors": matched_percentile,
            "size_matched_sample_count": len(matched),
            "reading": _band(matched_percentile),
            "sky_lit_sectors": len(sky_members),
            "height_percentile_vs_corpus_sky_sectors": (
                _percentile(median_height, sky_heights) if sky_members and sky_heights else None
            ),
        }
        rows.append(row)
        if matched_percentile is not None and matched_percentile <= 10 and footprint >= 20:
            findings.append({
                "id": f"scale:{node['id'].replace('/', '.')}:low-ceiling",
                "kind": "space_much_lower_than_corpus_for_its_size",
                "description": (
                    f"derived space {node['id']} covers {round(footprint)} player areas but is only "
                    f"{round(median_height, 2)} player heights clear (area-weighted), at the "
                    f"{matched_percentile} percentile of the {len(matched)} corpus sectors of "
                    "comparable footprint"
                ),
                "rule": "area-weighted clear height below the 10th percentile of corpus sectors within "
                        "half to double the same footprint, for spaces of at least 20 player areas",
                "evidence": [f"decompiled:{node['id']}"],
                "status": "derived observation against this corpus; not a universal constant",
            })

    shape: dict[str, Any] = {"status": "no shape corpus supplied", "signature": None}
    if shape_corpus:
        signature = shape_signature(level.to_disk_map().to_build_ir())
        samples = shape_corpus.get("samples", {})
        metrics = []
        for key in SHAPE_KEYS:
            percentile = _percentile(signature.get(key), samples.get(key, []))
            metrics.append({
                "metric": key,
                "candidate": round(signature[key], 4),
                "corpus_percentile": percentile,
                "corpus": shape_corpus.get("summaries", {}).get(key),
                "reading": _band(percentile),
            })
            if percentile is None:
                continue
            unusual_high = key in {"orthogonal_length_fraction", "rectangular_sector_fraction"}
            unusual_low = key in {
                "diagonal_length_fraction", "orientation_5deg_bins_occupied",
                "orientation_diversity", "chamfer_fraction", "segmented_arc_chain_count",
            }
            if (unusual_high and percentile >= 90) or (unusual_low and percentile <= 10):
                findings.append({
                    "id": f"shape:{key.replace('_', '-')}",
                    "kind": "shape_outside_corpus_mass",
                    "description": (
                        f"{key} is {round(signature[key], 4)}, at the {percentile} percentile of "
                        f"{len(shape_corpus.get('maps', []))} original maps"
                    ),
                    "rule": "orthogonality and rectangularity above the corpus 90th percentile, or "
                            "diagonal, orientation, chamfer, and arc measures below its 10th",
                    "evidence": ["gate:authored_geometry_valid"],
                    "status": "derived observation against this corpus; not a universal constant",
                })
        shape = {
            "status": "compared",
            "corpus_maps": len(shape_corpus.get("maps", [])),
            "signature": {key: round(value, 4) for key, value in signature.items()},
            "metrics": metrics,
        }

    return {
        "profile": profile.id,
        "spatial_corpus": None if not spatial_corpus else {
            "game": spatial_corpus.get("game"),
            "maps": spatial_corpus.get("maps"),
            "summaries": spatial_corpus.get("summaries"),
        },
        "spaces": rows,
        "shape": shape,
        "findings": findings,
        "limitations": [
            "a percentile says how unusual a number is for this corpus, never whether it is good",
            "size matching uses footprint alone; it does not know what a corpus sector was for",
            "shape is measured for the whole level, so one deliberately plain wing moves it",
        ],
    }


# ---------------------------------------------------------------------------
# Iteration packet
# ---------------------------------------------------------------------------

@dataclass
class AuthoringIteration:
    """Versioned, machine-readable evidence about one authored candidate."""

    identity: dict[str, Any]
    authored_intent: dict[str, Any]
    hard_gates: list[dict[str, Any]]
    independent_hierarchy: dict[str, Any]
    hierarchy_comparison: dict[str, Any]
    design_probes: list[dict[str, Any]]
    art_evidence: dict[str, Any]
    corpus_scale: dict[str, Any]
    render: dict[str, Any]
    review: dict[str, Any] | None = None
    schema: str = SCHEMA
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": self.schema,
            "schema_version": self.schema_version,
            "identity": deepcopy(self.identity),
            "authored_intent": deepcopy(self.authored_intent),
            "hard_gates": deepcopy(self.hard_gates),
            "independent_hierarchy": deepcopy(self.independent_hierarchy),
            "hierarchy_comparison": deepcopy(self.hierarchy_comparison),
            "design_probes": deepcopy(self.design_probes),
            "art_evidence": deepcopy(self.art_evidence),
            "corpus_scale": deepcopy(self.corpus_scale),
            "render": deepcopy(self.render),
            "review": deepcopy(self.review),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AuthoringIteration":
        if value.get("$schema") != SCHEMA or int(value.get("schema_version", -1)) != SCHEMA_VERSION:
            raise AuthoringLoopError(f"unsupported authoring-iteration document {value.get('$schema')!r}")
        return cls(
            identity=deepcopy(value["identity"]),
            authored_intent=deepcopy(value["authored_intent"]),
            hard_gates=deepcopy(value["hard_gates"]),
            independent_hierarchy=deepcopy(value["independent_hierarchy"]),
            hierarchy_comparison=deepcopy(value["hierarchy_comparison"]),
            design_probes=deepcopy(value["design_probes"]),
            art_evidence=deepcopy(value["art_evidence"]),
            corpus_scale=deepcopy(value.get("corpus_scale") or {}),
            render=deepcopy(value["render"]),
            review=deepcopy(value.get("review")),
        )

    @property
    def promotable(self) -> bool:
        return not blocking_failures(self.hard_gates)


def evaluate_candidate(
    candidate: Candidate,
    *,
    map_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
    art_directory: str | Path | None = None,
    spatial_corpus_path: str | Path | None = None,
    shape_corpus_path: str | Path | None = None,
    surface_corpus_path: str | Path | None = None,
    engine: dict[str, Any] | None = None,
    view_dir: str | Path | None = None,
    work_dir: str | Path | None = None,
) -> AuthoringIteration:
    """Compile one candidate and assemble its complete evidence packet.

    ``engine`` may carry ``nblood`` / ``game_dir`` paths.  Engine work is skipped,
    and honestly reported as skipped, whenever the environment is unavailable or
    the candidate already failed a cheap structural gate.
    """
    compiled, payload, deterministic = compile_candidate(candidate)
    level = compiled.level
    map_sha = _sha256(payload)
    if map_path is not None:
        Path(map_path).parent.mkdir(parents=True, exist_ok=True)
        write_map(level.to_disk_map(), map_path)

    identity = {
        "iteration_id": candidate.iteration_id,
        "module": candidate.module,
        "parent_iteration": candidate.parent,
        "declared_changes": list(candidate.declared_changes),
        "map_path": None if map_path is None else str(map_path),
        "map_sha256": map_sha,
        "map_bytes": len(payload),
        "counts": {
            "sectors": len(level.sectors), "walls": len(level.walls),
            "sprites": len(level.sprites), "regions": len(compiled.layout.regions),
            "connections": len(compiled.layout.connections),
        },
        "deterministic_compile": deterministic,
        "counting_note": "object counts describe size, never quality",
    }

    gates = run_hard_gates(candidate, compiled, payload, deterministic)
    failures = blocking_failures(gates)

    source = decompile_level(level, source_name=f"{candidate.iteration_id}.MAP")
    derived = summarize_derived_hierarchy(source)
    comparison = compare_hierarchies(candidate, compiled, source)

    build = level.to_disk_map().to_build_ir()
    probes = run_requested_probes(candidate, compiled, build)
    art = art_evidence(
        candidate, compiled, source, comparison, catalog_path=catalog_path,
        surface_corpus=_load_catalog(surface_corpus_path),
    )
    art["sprite_scale"] = sprite_scale_evidence(compiled, art_directory=art_directory)
    scale = corpus_scale_evidence(
        compiled, source,
        spatial_corpus=_load_catalog(spatial_corpus_path),
        shape_corpus=_load_catalog(shape_corpus_path),
    )

    render = _render_section(
        candidate, compiled, map_sha,
        engine=engine, view_dir=view_dir, work_dir=work_dir, blocked_by=failures,
    )
    if render.get("nblood_load"):
        gates.append(render["nblood_load"])

    return AuthoringIteration(
        identity=identity,
        authored_intent=candidate.intent.to_dict(),
        hard_gates=gates,
        independent_hierarchy=derived,
        hierarchy_comparison=comparison,
        design_probes=probes,
        art_evidence=art,
        corpus_scale=scale,
        render=render,
    )


def _render_section(
    candidate: Candidate,
    compiled: CompiledLayout,
    map_sha: str,
    *,
    engine: dict[str, Any] | None,
    view_dir: str | Path | None,
    work_dir: str | Path | None,
    blocked_by: list[str],
) -> dict[str, Any]:
    level = compiled.level
    allocations = _allocations(compiled)
    manifest = viewpoint_manifest(
        level, candidate.viewpoints, allocations=allocations, map_sha256=map_sha,
    ) if candidate.viewpoints else {
        "$schema": "llmapper.viewpoint-manifest", "schema_version": 1,
        "candidate_map_sha256": map_sha, "viewpoints": [],
        "limitations": ["no viewpoints were declared for this iteration"],
    }
    section: dict[str, Any] = {"manifest": manifest, "captures": None, "nblood_load": None}

    if blocked_by:
        section["capture_status"] = "skipped"
        section["capture_note"] = (
            "expensive engine evaluation was not run for a candidate that failed "
            f"structural gates: {blocked_by}"
        )
        section["nblood_load"] = _gate(
            "nblood_load_smoke", "skipped",
            f"not run; structural gates failed first: {blocked_by}",
        )
        return section
    if not engine:
        section["capture_status"] = "unavailable"
        section["capture_note"] = "no local NBlood environment was supplied to this run"
        section["nblood_load"] = _gate(
            "nblood_load_smoke", "skipped", "no local NBlood environment was supplied",
        )
        return section

    from .oracle import OracleError, run_nblood_oracle, run_nblood_viewpoint_capture

    nblood, game_dir = Path(engine["nblood"]), Path(engine["game_dir"])
    root = Path(work_dir) if work_dir is not None else Path("work") / f"authoring-{candidate.iteration_id}"
    root.mkdir(parents=True, exist_ok=True)
    candidate_map = root / f"{candidate.iteration_id}.MAP"
    write_map(level.to_disk_map(), candidate_map)
    try:
        load = run_nblood_oracle(
            candidate_map, nblood=nblood, game_dir=game_dir,
            grace_seconds=float(engine.get("grace_seconds", 5.0)),
            work_dir=root / "load",
        )
        section["nblood_load"] = _gate(
            "nblood_load_smoke", "pass" if load["status"] == "pass" else "fail",
            f"NBlood load smoke {load['status']}; revisions={load['engine_revisions']}",
            report=load,
        )
    except OracleError as exc:
        section["nblood_load"] = _gate("nblood_load_smoke", "skipped", f"engine unavailable: {exc}")
        section["capture_status"] = "unavailable"
        section["capture_note"] = str(exc)
        return section

    if section["nblood_load"]["status"] != "pass" or not candidate.viewpoints:
        section["capture_status"] = "skipped"
        section["capture_note"] = (
            "no viewpoints declared" if not candidate.viewpoints
            else "NBlood load smoke did not pass; views would not be trustworthy evidence"
        )
        return section

    prepared = prepare_viewpoints(level, candidate.viewpoints, allocations=allocations)
    variant_dir = root / "variants"
    variant_dir.mkdir(parents=True, exist_ok=True)
    requests: list[dict[str, Any]] = []
    for item in prepared:
        identifier = item["resolved"]["viewpoint_id"]
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in identifier)
        variant_path = variant_dir / f"{safe}.MAP"
        write_map(item["level"].to_disk_map(), variant_path)
        requests.append({
            "viewpoint_id": identifier, "map": str(variant_path), "resolved": item["resolved"],
            "variant_diff": item["diff"],
            "pitch_taps": int(item["resolved"].get("pitch") or 0),
        })
    images = Path(view_dir) if view_dir is not None else root / "views"
    try:
        captures = run_nblood_viewpoint_capture(
            requests, nblood=nblood, game_dir=game_dir, image_dir=images,
            work_dir=root / "capture",
            startup_timeout=float(engine.get("startup_timeout", 20.0)),
            settle_seconds=float(engine.get("settle_seconds", 2.5)),
        )
        section["captures"] = captures
        section["capture_status"] = captures["status"]
    except OracleError as exc:
        section["capture_status"] = "unavailable"
        section["capture_note"] = str(exc)
    section["variants"] = [
        {"viewpoint_id": item["viewpoint_id"], "map": item["map"], "diff": item["variant_diff"]}
        for item in requests
    ]
    return section


# ---------------------------------------------------------------------------
# Evidence references
# ---------------------------------------------------------------------------

def resolve_evidence(packet: AuthoringIteration, ref: str) -> dict[str, Any]:
    """Resolve one evidence reference to the exact object it names."""
    namespace, _, rest = str(ref).partition(":")
    if not rest or namespace not in EVIDENCE_NAMESPACES:
        raise AuthoringLoopError(f"evidence reference {ref!r} does not name a known namespace")
    document = packet.to_dict()

    def names(value: str) -> bool:
        """IDs are written either bare or already carrying their namespace prefix."""
        return value == rest or value == ref

    if namespace == "gate":
        for item in document["hard_gates"]:
            if names(item["gate_id"]):
                return {"ref": ref, "kind": "hard_gate", "object": item}
    elif namespace == "decompiled":
        for item in document["independent_hierarchy"]["derived_spaces"]:
            if names(item["id"]):
                return {"ref": ref, "kind": "derived_space", "object": item}
        for item in document["independent_hierarchy"]["derived_assemblies"]:
            if names(item["id"]):
                return {"ref": ref, "kind": "derived_assembly", "object": item}
        for item in document["independent_hierarchy"]["detail_group_distribution"]:
            if names(item["id"]):
                return {"ref": ref, "kind": "derived_detail_group", "object": item}
    elif namespace == "structure":
        for item in document["independent_hierarchy"]["derived_structures"]:
            if names(item["id"]):
                return {"ref": ref, "kind": "derived_structure", "object": item}
    elif namespace == "probe":
        for item in document["design_probes"]:
            if names(item["probe_id"]):
                return {"ref": ref, "kind": "design_probe", "object": item}
    elif namespace == "view":
        captures = (document["render"].get("captures") or {}).get("views", [])
        for item in captures:
            if names(item["viewpoint_id"]):
                return {"ref": ref, "kind": "rendered_view", "object": item}
        for item in document["render"]["manifest"]["viewpoints"]:
            if names(item["viewpoint_id"]):
                return {"ref": ref, "kind": "declared_viewpoint", "object": item}
    elif namespace == "intent":
        for item in document["authored_intent"]["assemblies"]:
            if names(item["assembly_id"]):
                return {"ref": ref, "kind": "authored_assembly", "object": item}
    elif namespace == "transition":
        for item in document["authored_intent"]["transitions"]:
            if names(item["transition_id"]):
                return {"ref": ref, "kind": "authored_transition", "object": item}
    elif namespace == "authored":
        for row in document["hierarchy_comparison"]["assemblies"]:
            if rest in row["authored_regions"]:
                return {"ref": ref, "kind": "authored_region", "object": {
                    "region_id": rest, "assembly_id": row["assembly_id"],
                }}
        if rest in document["hierarchy_comparison"]["unmatched_regions"]:
            return {"ref": ref, "kind": "authored_region", "object": {
                "region_id": rest, "assembly_id": None,
            }}
    elif namespace == "sprite-scale":
        for item in (document["art_evidence"].get("sprite_scale") or {}).get("findings", []):
            if item["id"] == ref:
                return {"ref": ref, "kind": "sprite_scale_finding", "object": item}
    elif namespace == "art":
        for item in document["art_evidence"]["nodes"]:
            if item["node"] == rest:
                return {"ref": ref, "kind": "art_node", "object": item}
        for item in document["art_evidence"]["assets"]:
            if item["asset"] == rest or rest == item["asset"].rpartition(":")[2]:
                return {"ref": ref, "kind": "art_asset", "object": item}
    elif namespace in {"scale", "shape"}:
        for item in document["corpus_scale"].get("findings", []):
            if item["id"] == ref:
                return {"ref": ref, "kind": "corpus_scale_finding", "object": item}
        for item in document["corpus_scale"].get("spaces", []):
            if names(item["node"]):
                return {"ref": ref, "kind": "corpus_scale_space", "object": item}
        # Shape metric names are written with underscores, but findings key them with
        # hyphens, so a reference may legitimately use either spelling.
        wanted = rest.replace("-", "_")
        for item in (document["corpus_scale"].get("shape") or {}).get("metrics", []):
            if names(item["metric"]) or item["metric"] == wanted:
                return {"ref": ref, "kind": "corpus_shape_metric", "object": item}
    elif namespace == "discrepancy":
        for item in document["hierarchy_comparison"]["discrepancies"]:
            if item["id"] == ref:
                return {"ref": ref, "kind": "hierarchy_discrepancy", "object": item}
    elif namespace == "source":
        if rest == "module":
            return {"ref": ref, "kind": "authored_module", "object": {
                "module": packet.identity["module"],
                "iteration_id": packet.identity["iteration_id"],
                "map_sha256": packet.identity["map_sha256"],
            }}
        kind, _, number = rest.partition(":")
        if kind in {"sector", "wall", "sprite"} and number.isdigit():
            limit = int(packet.identity["counts"][f"{kind}s"])
            if 0 <= int(number) < limit:
                return {"ref": ref, "kind": f"source_{kind}", "object": {
                    "ref": f"{kind}:{number}", "map_sha256": packet.identity["map_sha256"],
                }}
    raise AuthoringLoopError(f"evidence reference {ref!r} does not resolve in this iteration")


def validate_evidence(packet: AuthoringIteration, refs: Iterable[str]) -> list[dict[str, Any]]:
    return [resolve_evidence(packet, ref) for ref in refs]


def packet_evidence_refs(packet: AuthoringIteration) -> list[str]:
    """Every reference the packet itself emits, for a self-consistency check."""
    refs: set[str] = set()
    document = packet.to_dict()
    for item in document["hierarchy_comparison"]["discrepancies"]:
        refs.update(item["evidence"])
    for item in document["art_evidence"]["near_identical_treatments"]:
        refs.update(item["evidence"])
    for item in document["art_evidence"]["transition_material_evidence"]:
        refs.update(item["evidence"])
    for item in document["corpus_scale"].get("findings", []):
        refs.update(item["evidence"])
    for item in (document["art_evidence"].get("sprite_scale") or {}).get("findings", []):
        refs.update(item["evidence"])
    return sorted(refs)


# ---------------------------------------------------------------------------
# Reasoning-review seam
# ---------------------------------------------------------------------------

CLAIM_STATUS = {"supported", "contradicted", "uncertain"}


@dataclass(frozen=True)
class ReviewClaim:
    claim: str
    status: str
    evidence: tuple[str, ...]
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim, "status": self.status,
            "evidence": list(self.evidence), "reasoning": self.reasoning,
        }


@dataclass(frozen=True)
class NextAction:
    action: str
    expected_effect: str
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action, "expected_effect": self.expected_effect,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class ReasoningReview:
    """An auditable engineering/design decision record written by an external agent."""

    reviewer: str
    iteration_id: str
    claims: tuple[ReviewClaim, ...] = ()
    accepted_strengths: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()
    next_actions: tuple[NextAction, ...] = ()
    uncertainties: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": "llmapper.authoring-review",
            "schema_version": 1,
            "reviewer": self.reviewer,
            "iteration_id": self.iteration_id,
            "claims": [item.to_dict() for item in self.claims],
            "accepted_strengths": list(self.accepted_strengths),
            "problems": list(self.problems),
            "next_actions": [item.to_dict() for item in self.next_actions],
            "uncertainties": list(self.uncertainties),
            "status": (
                "external reviewer conclusions; the deterministic package neither "
                "produced nor validated the reasoning, only the evidence references"
            ),
        }


def review_from_dict(value: dict[str, Any]) -> ReasoningReview:
    """Rebuild a review written as data by an external reviewing agent."""
    return ReasoningReview(
        reviewer=str(value["reviewer"]),
        iteration_id=str(value["iteration_id"]),
        claims=tuple(
            ReviewClaim(
                claim=str(item["claim"]), status=str(item["status"]),
                evidence=tuple(str(ref) for ref in item.get("evidence", ())),
                reasoning=str(item.get("reasoning", "")),
            )
            for item in value.get("claims", ())
        ),
        accepted_strengths=tuple(str(item) for item in value.get("accepted_strengths", ())),
        problems=tuple(str(item) for item in value.get("problems", ())),
        next_actions=tuple(
            NextAction(
                action=str(item["action"]), expected_effect=str(item["expected_effect"]),
                evidence=tuple(str(ref) for ref in item.get("evidence", ())),
            )
            for item in value.get("next_actions", ())
        ),
        uncertainties=tuple(str(item) for item in value.get("uncertainties", ())),
    )


def attach_review(packet: AuthoringIteration, review: ReasoningReview) -> AuthoringIteration:
    """Embed a review after proving every reference resolves inside this packet."""
    if review.iteration_id != packet.identity["iteration_id"]:
        raise AuthoringLoopError(
            f"review targets {review.iteration_id!r} but packet is {packet.identity['iteration_id']!r}"
        )
    for claim in review.claims:
        if claim.status not in CLAIM_STATUS:
            raise AuthoringLoopError(f"unknown claim status {claim.status!r}")
        if not claim.evidence:
            raise AuthoringLoopError(f"claim {claim.claim!r} cites no evidence")
        validate_evidence(packet, claim.evidence)
    for action in review.next_actions:
        validate_evidence(packet, action.evidence)
    packet.review = review.to_dict()
    return packet


def record_review(root: str | Path, packet: AuthoringIteration, review: ReasoningReview) -> dict[str, Any]:
    """Append the review to the existing workspace decision and episode ledgers."""
    from .workspace import append_decision, append_episode

    written: dict[str, Any] = {"decisions": [], "episodes": []}
    for action in review.next_actions:
        written["decisions"].append(append_decision(
            root,
            intent=f"{packet.identity['iteration_id']}: {review.reviewer}",
            decision=action.action,
            expected=action.expected_effect,
            evidence=list(action.evidence),
            status="proposed",
        ))
    observed = {
        "iteration_id": packet.identity["iteration_id"],
        "map_sha256": packet.identity["map_sha256"],
        "failed_gates": blocking_failures(packet.hard_gates),
        "discrepancies": [
            item["kind"] for item in packet.hierarchy_comparison["discrepancies"]
        ],
        "claims": [item.to_dict() for item in review.claims],
    }
    written["episodes"].append(append_episode(
        root,
        intent=packet.authored_intent["brief"],
        expected="; ".join(packet.identity["declared_changes"]) or "initial blockout",
        observed=observed,
        correction="; ".join(item.action for item in review.next_actions) or None,
    ))
    return written


# ---------------------------------------------------------------------------
# Cross-iteration comparison
# ---------------------------------------------------------------------------

def _gate_map(packet: AuthoringIteration) -> dict[str, str]:
    return {item["gate_id"]: item["status"] for item in packet.hard_gates}


def compare_iterations(packets: Sequence[AuthoringIteration]) -> dict[str, Any]:
    """Per-dimension cross-iteration comparison; deliberately not one score."""
    if not packets:
        raise AuthoringLoopError("comparison requires at least one iteration")
    rows: list[dict[str, Any]] = []
    for packet in packets:
        document = packet.to_dict()
        probes = document["design_probes"]
        art = document["art_evidence"]
        captures = (document["render"].get("captures") or {}).get("views", [])
        rows.append({
            "iteration_id": packet.identity["iteration_id"],
            "parent": packet.identity["parent_iteration"],
            "declared_changes": packet.identity["declared_changes"],
            "map_sha256": packet.identity["map_sha256"],
            "counts": packet.identity["counts"],
            "hard_validation": {
                "failed": blocking_failures(packet.hard_gates),
                "skipped": [item["gate_id"] for item in packet.hard_gates if item["status"] == "skipped"],
                "by_gate": _gate_map(packet),
            },
            "authored_vs_observed_hierarchy": {
                "discrepancies": [
                    {"id": item["id"], "kind": item["kind"]}
                    for item in document["hierarchy_comparison"]["discrepancies"]
                ],
                "per_assembly": [
                    {
                        "assembly_id": row["assembly_id"],
                        "derived_space_count": row["derived_space_count"],
                        "dominant_space_share": row["dominant_space_share"],
                        "singletons": len(row["singleton_space_ids"]),
                    }
                    for row in document["hierarchy_comparison"]["assemblies"]
                ],
            },
            "singleton_spaces": {
                "count": document["independent_hierarchy"]["counts"]["singleton_spaces"],
                "ids": document["independent_hierarchy"]["singleton_space_ids"],
            },
            "derived_space_count": document["independent_hierarchy"]["counts"]["spaces"],
            "route_structure": {
                item["probe_id"]: {
                    "status": item["result"]["status"],
                    "measurements": item["result"].get("measurements", {}),
                    "route_length": len(item["result"].get("route", [])),
                }
                for item in probes
            },
            "mandatory_reachability": next(
                (item for item in packet.hard_gates if item["gate_id"] == "required_reachability"), None,
            ),
            "transition_evidence": art["transition_material_evidence"],
            "major_space_scale": [
                {
                    "id": item["id"],
                    "footprint_player_areas": item["player_relative"]["footprint_player_areas"],
                    "median_clear_height_player_heights": item["player_relative"]["median_clear_height_player_heights"],
                }
                for item in sorted(
                    document["independent_hierarchy"]["derived_spaces"],
                    key=lambda value: -value["player_relative"]["footprint_player_areas"],
                )[:5]
            ],
            "art_differentiation": {
                "near_identical_pairs": art["near_identical_treatments"],
                "unresolved_assets": len(art["unresolved_assets"]),
            },
            "decorative_distribution": art["decorative_distribution"],
            "oversized_decorations": [
                item["id"] for item in (art.get("sprite_scale") or {}).get("findings", [])
            ],
            "corpus_scale": {
                "findings": [
                    {"id": item["id"], "kind": item["kind"]}
                    for item in document.get("corpus_scale", {}).get("findings", [])
                ],
                "spaces_below_corpus_for_their_size": [
                    item["node"] for item in document.get("corpus_scale", {}).get("spaces", [])
                    if (item.get("height_percentile_vs_same_size_corpus_sectors") or 100) <= 10
                ],
                "shape_signature": (document.get("corpus_scale", {}).get("shape") or {}).get("signature"),
            },
            "visually_empty_spaces": art["visually_empty_spaces"],
            "nblood_load": next(
                (item["status"] for item in packet.hard_gates if item["gate_id"] == "nblood_load_smoke"),
                "not_attempted",
            ),
            "views_captured": [
                {"viewpoint_id": item["viewpoint_id"], "status": item["status"],
                 "image": item["image"], "image_sha256": item["image_sha256"]}
                for item in captures
            ],
            "review": document.get("review"),
        })
    return {
        "$schema": "llmapper.authoring-comparison",
        "schema_version": 1,
        "iterations": rows,
        "reading_guide": [
            "no dimension here is a quality score and none of them may be summed",
            "a lower singleton count or a higher sprite count is not automatically better",
            "a skipped gate is not a passing gate",
        ],
    }
