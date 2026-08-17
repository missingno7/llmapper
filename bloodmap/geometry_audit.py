"""Forensic geometry/connectivity audit and strict authored-level validation.

`validate_map()` remains the native structural checker for original maps.
This module answers a different question: would this geometry be a legal
scratch-authored Blood level?

Every diagnostic is collected; the first conflict does not stop the scan.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from math import hypot
from typing import Any, Iterable

from .analysis import Diagnostic, validate_map
from .blood_types import classify
from .model import DiskMap, LevelIR
from .planar_geom import (
    Point,
    Segment,
    area2,
    classify_segment_pair,
    on_segment_strict,
    point_in_loops,
    polygon_relation,
    undirected_key,
    validate_loop,
    z_interval,
    z_relation,
)

SCHEMA = "llmapper.geometry-audit"
SCHEMA_VERSION = 1

WALKABLE_WIDTH = 512
WALKABLE_OPENING = 4096


class AuthoredGeometryError(ValueError):
    pass


@dataclass
class GeometryConflict:
    kind: str
    severity: str
    why: str
    walls: list[int] = field(default_factory=list)
    sectors: list[int] = field(default_factory=list)
    endpoints: list[list[int]] = field(default_factory=list)
    overlap_interval: list[list[int]] | None = None
    z_intervals: list[list[int]] = field(default_factory=list)
    portal_state: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "kind": self.kind,
            "severity": self.severity,
            "why": self.why,
            "walls": self.walls,
            "sectors": self.sectors,
            "endpoints": self.endpoints,
            "z_intervals": self.z_intervals,
            "portal_state": self.portal_state,
            "context": self.context,
        }
        if self.overlap_interval is not None:
            payload["overlap_interval"] = self.overlap_interval
        return payload


def _as_level(source: DiskMap | LevelIR) -> LevelIR:
    if isinstance(source, LevelIR):
        return source
    return source.to_level_ir()


def _wall_owners(level: LevelIR) -> list[int]:
    owners = [-1] * len(level.walls)
    for sector_id, sector in enumerate(level.sectors):
        first = int(sector["fields"]["wall_ptr"])
        count = int(sector["fields"]["wall_count"])
        for wall_id in range(first, first + count):
            if 0 <= wall_id < len(owners):
                owners[wall_id] = sector_id
    return owners


def _segment(level: LevelIR, wall_id: int) -> Segment:
    wall = level.walls[wall_id]["fields"]
    end = level.walls[int(wall["point2"])]["fields"]
    return (int(wall["x"]), int(wall["y"])), (int(end["x"]), int(end["y"]))


def _sector_loops(level: LevelIR, sector_id: int) -> list[list[Point]]:
    fields = level.sectors[sector_id]["fields"]
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    remaining = set(range(first, first + count))
    loops: list[list[Point]] = []
    while remaining:
        root = min(remaining)
        current = root
        visited: set[int] = set()
        points: list[Point] = []
        while current not in visited and current in remaining:
            visited.add(current)
            remaining.discard(current)
            wall = level.walls[current]["fields"]
            points.append((int(wall["x"]), int(wall["y"])))
            current = int(wall["point2"])
        if points:
            loops.append(points)
    loops.sort(key=lambda item: abs(area2(item)), reverse=True)
    return loops


def _z_of(level: LevelIR, sector_id: int) -> tuple[int, int]:
    fields = level.sectors[sector_id]["fields"]
    return z_interval(int(fields["ceiling_z"]), int(fields["floor_z"]))


def _portal_state(level: LevelIR, wall_id: int) -> dict[str, Any]:
    fields = level.walls[wall_id]["fields"]
    return {
        "next_wall": int(fields["next_wall"]),
        "next_sector": int(fields["next_sector"]),
        "cstat": int(fields.get("cstat") or 0),
        "has_xwall": level.walls[wall_id].get("blood") is not None,
    }


def _sprite_context(level: LevelIR, sector_id: int) -> list[dict[str, Any]]:
    out = []
    for index, sprite in enumerate(level.sprites):
        fields = sprite["fields"]
        if int(fields["sector"]) != sector_id:
            continue
        typed = classify("sprite", int(fields["type"]))
        out.append({
            "sprite": index,
            "type_id": int(fields["type"]),
            "type_name": typed["name"],
            "category": typed["category"],
        })
    return out


def _mechanism_context(level: LevelIR, sector_id: int) -> dict[str, Any]:
    sector = level.sectors[sector_id]
    blood = sector.get("blood")
    fields = sector["fields"]
    return {
        "type": int(fields.get("type") or 0),
        "underwater": bool(blood and blood["fields"].get("underwater")),
        "rx_id": None if blood is None else blood["fields"].get("rx_id"),
        "tx_id": None if blood is None else blood["fields"].get("tx_id"),
        "parallax_ceiling": bool(int(fields.get("ceiling_stat") or 0) & 1),
    }


def _special_xy_overlap_reason(
    level: LevelIR, left: int, right: int, relation: dict[str, Any],
) -> str | None:
    """Return a supported special-construction label, or None to fail closed."""
    mech_l, mech_r = _mechanism_context(level, left), _mechanism_context(level, right)
    if mech_l["underwater"] or mech_r["underwater"]:
        markers = [
            item for item in _sprite_context(level, left) + _sprite_context(level, right)
            if item["type_id"] in {9, 10, 11, 12}
        ]
        if markers:
            return "paired_water_or_stack_markers"
        if mech_l["underwater"] != mech_r["underwater"]:
            return "underwater_flag_without_markers"
    if relation.get("hole_relationship"):
        return "explicit_hole_relationship"
    types = {mech_l["type"], mech_r["type"]}
    if types & {600, 602}:
        return "moving_sector_envelope_candidate"
    return None


def audit_geometry(
    source: DiskMap | LevelIR,
    *,
    fail_closed_specials: bool = True,
    declared_specials: Iterable[tuple[int, int, str]] | None = None,
    gated_sectors: Iterable[int] | None = None,
    declared_zero_exit: Iterable[int] | None = None,
) -> dict[str, Any]:
    """Return every suspicious geometric and connectivity relationship."""
    level = _as_level(source)
    owners = _wall_owners(level)
    declared = {
        frozenset((int(a), int(b))): str(kind)
        for a, b, kind in (declared_specials or [])
    }
    conflicts: list[GeometryConflict] = []
    summaries: dict[str, list[dict[str, Any]]] = defaultdict(list)

    segments = [_segment(level, wall_id) for wall_id in range(len(level.walls))]
    loops = [_sector_loops(level, sector_id) for sector_id in range(len(level.sectors))]

    for wall_id, (start, end) in enumerate(segments):
        if start == end:
            conflict = GeometryConflict(
                kind="zero_length_wall",
                severity="error",
                why="wall has identical endpoints; Build serializes this but authored geometry must not",
                walls=[wall_id],
                sectors=[owners[wall_id]],
                endpoints=[[start[0], start[1]], [end[0], end[1]]],
                z_intervals=[list(_z_of(level, owners[wall_id]))] if owners[wall_id] >= 0 else [],
                portal_state=_portal_state(level, wall_id),
            )
            conflicts.append(conflict)
            summaries["zero_length_walls"].append(conflict.to_dict())

    for left in range(len(level.walls)):
        for right in range(left + 1, len(level.walls)):
            if owners[left] < 0 or owners[right] < 0:
                continue
            if owners[left] == owners[right]:
                continue
            if frozenset((owners[left], owners[right])) in {
                frozenset((int(a), int(b))) for a, b, _kind in (declared_specials or [])
            }:
                continue
            relation = classify_segment_pair(*segments[left], *segments[right])
            if relation is None:
                continue
            kind = str(relation["kind"])
            portal_l = _portal_state(level, left)
            portal_r = _portal_state(level, right)
            paired = (
                portal_l["next_wall"] == right and portal_r["next_wall"] == left
            )
            z_l, z_r = _z_of(level, owners[left]), _z_of(level, owners[right])
            endpoints = [
                [segments[left][0][0], segments[left][0][1], segments[left][1][0], segments[left][1][1]],
                [segments[right][0][0], segments[right][0][1], segments[right][1][0], segments[right][1][1]],
            ]
            overlap = relation.get("overlap")
            overlap_interval = None if overlap is None else [
                [overlap[0][0], overlap[0][1]],
                [overlap[1][0], overlap[1][1]],
            ]
            why = {
                "proper_crossing": "unrelated boundaries cross; this is not a T-junction and was not split into a planar junction",
                "t_junction": "an endpoint lies in the interior of another wall; the longer wall was not split",
                "partial_collinear_overlap": "collinear walls share a proper sub-interval but are not exact reversed coincidences, so LevelBuilder.connect cannot portal them",
                "exact_reversed_coincident": "walls occupy the same undirected segment in opposite directions",
                "exact_same_direction_coincident": "two sectors own the same directed boundary; duplicate ownership",
                "zero_length": "degenerate wall",
            }.get(kind, kind)
            if kind == "exact_reversed_coincident":
                if paired:
                    summaries["reciprocal_portals"].append({
                        "walls": [left, right],
                        "sectors": [owners[left], owners[right]],
                        "endpoints": endpoints,
                    })
                    continue
                stacked_sectors = {
                    int(a) for a, b, kind in (declared_specials or []) if kind in {"water", "stack"}
                } | {
                    int(b) for a, b, kind in (declared_specials or []) if kind in {"water", "stack"}
                }
                if owners[left] in stacked_sectors or owners[right] in stacked_sectors:
                    continue
                severity = "error"
                why = (
                    "exact reversed coincident walls are not reciprocal portals; "
                    "this is an unintended one-sided shared boundary / infinitely thin partition"
                )
                summaries["unpaired_coincident_walls"].append({
                    "walls": [left, right], "sectors": [owners[left], owners[right]],
                })
            elif kind == "exact_same_direction_coincident":
                severity = "error"
            elif kind == "partial_collinear_overlap":
                severity = "error"
                summaries["partial_collinear_overlaps"].append({
                    "walls": [left, right],
                    "sectors": [owners[left], owners[right]],
                    "overlap": overlap_interval,
                    "portaled": paired,
                })
            elif kind == "t_junction":
                severity = "error"
                summaries["t_junctions"].append({
                    "walls": [left, right],
                    "point": list(relation["point"]),
                    "sectors": [owners[left], owners[right]],
                })
            elif kind == "proper_crossing":
                severity = "error"
                summaries["proper_crossings"].append({
                    "walls": [left, right],
                    "sectors": [owners[left], owners[right]],
                    "integer_intersection": relation.get("integer_intersection"),
                })
            else:
                severity = "warning"
            conflict = GeometryConflict(
                kind=kind,
                severity=severity,
                why=why,
                walls=[left, right],
                sectors=[owners[left], owners[right]],
                endpoints=endpoints,
                overlap_interval=overlap_interval,
                z_intervals=[list(z_l), list(z_r)],
                portal_state={"left": portal_l, "right": portal_r, "reciprocal": paired},
                context={
                    "mechanisms": [
                        _mechanism_context(level, owners[left]),
                        _mechanism_context(level, owners[right]),
                    ],
                },
            )
            conflicts.append(conflict)

    for wall_id, (start, end) in enumerate(segments):
        if start == end:
            continue
        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        # Prefer a point strictly on the segment when the midpoint is a lattice point.
        probe = (int(mid[0]), int(mid[1]))
        if not on_segment_strict(start, end, probe):
            continue
        owner = owners[wall_id]
        for sector_id, sector_loops in enumerate(loops):
            if sector_id == owner:
                continue
            if point_in_loops(probe, sector_loops) == 1:
                conflict = GeometryConflict(
                    kind="sub_body_wall_fragment",
                    severity="error",
                    why="wall midpoint lies strictly inside another sector footprint; the wall is an unintended internal partition or overlap artifact",
                    walls=[wall_id],
                    sectors=[owner, sector_id],
                    endpoints=[[start[0], start[1]], [end[0], end[1]]],
                    z_intervals=[list(_z_of(level, owner)), list(_z_of(level, sector_id))],
                    portal_state=_portal_state(level, wall_id),
                    context={"probe": list(probe)},
                )
                conflicts.append(conflict)
                summaries["sub_body_wall_fragments"].append(conflict.to_dict())
                break

    footprint: list[dict[str, Any]] = []
    for left in range(len(level.sectors)):
        for right in range(left + 1, len(level.sectors)):
            relation = polygon_relation(loops[left], loops[right])
            kind = str(relation["kind"])
            if kind == "disjoint":
                continue
            z_kind = z_relation(_z_of(level, left), _z_of(level, right))
            special = declared.get(frozenset((left, right)))
            inferred = _special_xy_overlap_reason(level, left, right, relation)
            allowed = special or inferred
            if fail_closed_specials and inferred in {
                "underwater_flag_without_markers", "moving_sector_envelope_candidate",
            }:
                allowed = None if fail_closed_specials and special is None else inferred
                if fail_closed_specials and special is None and inferred != "paired_water_or_stack_markers":
                    allowed = None
            if kind in {"partial_area_overlap", "full_containment_a_in_b", "full_containment_b_in_a"}:
                if allowed in {"explicit_hole_relationship", "paired_water_or_stack_markers"} and kind == "hole_containment":
                    severity = "info"
                elif allowed == "paired_water_or_stack_markers" and z_kind != "overlapping_vertical_volumes":
                    severity = "info"
                elif z_kind == "overlapping_vertical_volumes" and allowed is None:
                    severity = "error"
                    why = (
                        f"XY {kind} with overlapping Z intervals; this is accidental volume overlap, "
                        "not a declared stack/water/hole construction"
                    )
                elif z_kind != "overlapping_vertical_volumes" and allowed is None:
                    severity = "error"
                    why = (
                        f"XY {kind} with {z_kind}; point-to-sector resolution is ambiguous unless "
                        "an explicit stacked/water relationship is declared"
                    )
                else:
                    severity = "info"
                    why = f"XY {kind} accepted as {allowed}"
            elif kind == "hole_containment":
                severity = "info" if allowed else "error"
                why = (
                    "inner footprint matches a hole loop"
                    if allowed else
                    "nested footprint looks like a hole but was not declared; fail closed"
                )
            elif kind in {"exactly_shared_boundary", "boundary_touching"}:
                severity = "info"
                why = f"sectors {kind.replace('_', ' ')}"
            else:
                severity = "warning"
                why = kind
            record = {
                "sectors": [left, right],
                "xy": kind,
                "z": z_kind,
                "z_intervals": [list(_z_of(level, left)), list(_z_of(level, right))],
                "special": allowed,
                "hole_relationship": bool(relation.get("hole_relationship")),
                "severity": severity,
                "why": why,
            }
            footprint.append(record)
            if kind in {"partial_area_overlap", "full_containment_a_in_b", "full_containment_b_in_a", "hole_containment"}:
                summaries["sector_footprint_intersections"].append(record)
            if kind.startswith("full_containment") or kind == "hole_containment":
                summaries["sector_containment"].append(record)
            if kind in {"boundary_touching", "exactly_shared_boundary"}:
                summaries["sector_boundary_touching"].append(record)
            if z_kind == "overlapping_vertical_volumes":
                summaries["xy_overlap_overlapping_z"].append(record)
            elif z_kind in {"vertically_disjoint", "vertically_touching"}:
                summaries["xy_overlap_disjoint_or_touching_z"].append(record)
            if severity == "error":
                conflicts.append(GeometryConflict(
                    kind=f"footprint_{kind}",
                    severity=severity,
                    why=why,
                    sectors=[left, right],
                    z_intervals=[list(_z_of(level, left)), list(_z_of(level, right))],
                    context={"special": allowed, "z": z_kind, "xy": kind},
                ))

    undirected_owners: dict[tuple[Point, Point], list[int]] = defaultdict(list)
    for wall_id, (start, end) in enumerate(segments):
        if start == end:
            continue
        undirected_owners[undirected_key(start, end)].append(wall_id)
    for key, wall_ids in undirected_owners.items():
        if len(wall_ids) <= 2:
            continue
        owner_set = {owners[item] for item in wall_ids}
        stacked = set()
        for a, b, kind in (declared_specials or []):
            stacked.add(int(a))
            stacked.add(int(b))
        if owner_set & stacked and len(owner_set - stacked) <= 1:
            continue
        conflicts.append(GeometryConflict(
            kind="more_than_two_boundary_owners",
            severity="error",
            why="more than two walls occupy the same undirected segment",
            walls=list(wall_ids),
            sectors=sorted({owners[item] for item in wall_ids}),
            endpoints=[[key[0][0], key[0][1]], [key[1][0], key[1][1]]],
        ))
        summaries["duplicate_directed_boundaries"].append({
            "segment": [list(key[0]), list(key[1])],
            "walls": wall_ids,
        })

    traversal = _traversal_audit(
        level, owners, segments,
        gated_sectors=gated_sectors,
        declared_zero_exit=declared_zero_exit,
    )
    summaries.update(traversal["summaries"])
    conflicts.extend(traversal["conflicts"])

    native = [item for item in validate_map(level.to_disk_map()) if item.severity == "error"]
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "native_validation_errors": len(native),
        "counts": {
            "sectors": len(level.sectors),
            "walls": len(level.walls),
            "sprites": len(level.sprites),
            "conflicts": len(conflicts),
            "error_conflicts": sum(1 for item in conflicts if item.severity == "error"),
        },
        "summaries": {key: value for key, value in summaries.items()},
        "conflicts": [item.to_dict() for item in conflicts],
        "traversal": traversal["report"],
        "limitations": [
            "2D XY tests ignore slopes except via sampled Z intervals at sector constants",
            "fail-closed specials require explicit water/stack markers or declared pairs",
            "intended portal candidates without coincident geometry cannot be recovered from the MAP alone",
        ],
    }


def _traversal_audit(
    level: LevelIR, owners: list[int], segments: list[Segment],
    *,
    gated_sectors: Iterable[int] | None = None,
    declared_zero_exit: Iterable[int] | None = None,
) -> dict[str, Any]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    zero_exit: list[int] = []
    exits: dict[int, int] = defaultdict(int)
    for wall_id, wall in enumerate(level.walls):
        fields = wall["fields"]
        other = int(fields["next_wall"])
        next_sector = int(fields["next_sector"])
        owner = owners[wall_id]
        if next_sector < 0 or other < 0 or owner < 0:
            continue
        start, end = segments[wall_id]
        width = hypot(end[0] - start[0], end[1] - start[1])
        left_z, right_z = _z_of(level, owner), _z_of(level, next_sector)
        opening = min(left_z[1], right_z[1]) - max(left_z[0], right_z[0])
        blocking = bool(int(fields.get("cstat") or 0) & 1)
        if width >= WALKABLE_WIDTH and opening >= WALKABLE_OPENING and not blocking:
            adjacency[owner].add(next_sector)
            exits[owner] += 1
    # Water/stack markers are real Blood transitions even without portals.
    by_key: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, sprite in enumerate(level.sprites):
        fields = sprite["fields"]
        type_id = int(fields["type"])
        if type_id not in {9, 10, 11, 12}:
            continue
        blood = sprite.get("blood") or {}
        data1 = int((blood.get("fields") or {}).get("data_1") or 0)
        by_key[(type_id, data1)].append(int(fields["sector"]))
    for data1 in {key[1] for key in by_key}:
        ups = by_key.get((9, data1), []) + by_key.get((11, data1), [])
        downs = by_key.get((10, data1), []) + by_key.get((12, data1), [])
        for left in ups:
            for right in downs:
                adjacency[left].add(right)
                adjacency[right].add(left)
                exits[left] += 1
                exits[right] += 1

    for sector_id in range(len(level.sectors)):
        adjacency.setdefault(sector_id, set())
        if exits[sector_id] == 0:
            zero_exit.append(sector_id)

    components: list[list[int]] = []
    unseen = set(range(len(level.sectors)))
    while unseen:
        root = min(unseen)
        unseen.remove(root)
        component = {root}
        pending = deque([root])
        while pending:
            current = pending.popleft()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
        components.append(sorted(component))
    components.sort(key=len, reverse=True)
    main = set(components[0]) if components else set()

    starts = []
    pickups = []
    for index, sprite in enumerate(level.sprites):
        fields = sprite["fields"]
        typed = classify("sprite", int(fields["type"]))
        record = {
            "sprite": index,
            "type_id": int(fields["type"]),
            "type_name": typed["name"],
            "category": typed["category"],
            "sector": int(fields["sector"]),
        }
        if typed["category"] == "start":
            starts.append(record)
        if typed["category"] in {"weapon", "ammo", "health", "armor", "powerup", "flag"}:
            pickups.append(record)

    unreachable_starts = [
        item for item in starts
        if item["type_id"] == 2 and item["sector"] not in main
    ]
    unreachable_pickups = [item for item in pickups if item["sector"] not in main]
    isolated = [component for component in components if len(component) == 1]
    allowed_zero = set(int(item) for item in (gated_sectors or [])) | set(
        int(item) for item in (declared_zero_exit or [])
    )
    conflicts = []
    for sector_id in zero_exit:
        declared = sector_id in allowed_zero
        conflicts.append(GeometryConflict(
            kind="zero_exit_gameplay_sector",
            severity="info" if declared else "error",
            why=(
                "declared gated/helper sector has no walkable-at-rest portal"
                if declared else
                "sector has no walkable-at-rest reciprocal portal"
            ),
            sectors=[sector_id],
            z_intervals=[list(_z_of(level, sector_id))],
            context=_mechanism_context(level, sector_id),
        ))
    for item in unreachable_starts:
        conflicts.append(GeometryConflict(
            kind="unreachable_start",
            severity="error",
            why="deathmatch start is not in the largest at-rest circulation component",
            sectors=[item["sector"]],
            context=item,
        ))
    for item in unreachable_pickups:
        conflicts.append(GeometryConflict(
            kind="unreachable_pickup",
            severity="warning",
            why="pickup sector is outside the largest at-rest circulation component (may be gated)",
            sectors=[item["sector"]],
            context=item,
        ))
    return {
        "conflicts": conflicts,
        "summaries": {
            "isolated_traversal_components": isolated,
            "zero_exit_gameplay_sectors": zero_exit,
            "unreachable_starts": unreachable_starts,
            "unreachable_pickups": unreachable_pickups,
        },
        "report": {
            "component_count": len(components),
            "components": components,
            "main_network": sorted(main),
            "main_size": len(main),
            "dm_starts_in_main": sum(1 for item in starts if item["type_id"] == 2 and item["sector"] in main),
            "dm_starts_total": sum(1 for item in starts if item["type_id"] == 2),
            "walkable_edges": sum(len(neighbors) for neighbors in adjacency.values()) // 2,
        },
    }


def validate_authored_geometry(
    source: DiskMap | LevelIR,
    *,
    declared_specials: Iterable[tuple[int, int, str]] | None = None,
    gated_sectors: Iterable[int] | None = None,
    declared_zero_exit: Iterable[int] | None = None,
) -> list[Diagnostic]:
    """Strict authored-geometry gate. Returns every diagnostic."""
    audit = audit_geometry(
        source,
        fail_closed_specials=True,
        declared_specials=declared_specials,
        gated_sectors=gated_sectors,
        declared_zero_exit=declared_zero_exit,
    )
    out: list[Diagnostic] = []
    for item in audit["conflicts"]:
        if item["severity"] == "info":
            continue
        location = ",".join(
            [*(f"sector[{sid}]" for sid in item.get("sectors") or []),
             *(f"wall[{wid}]" for wid in item.get("walls") or [])]
        ) or "level"
        out.append(Diagnostic(item["severity"], item["kind"], item["why"], location))
    level = _as_level(source)
    for sector_id in range(len(level.sectors)):
        loops = _sector_loops(level, sector_id)
        if not loops:
            out.append(Diagnostic("error", "open_loop", "sector has no closed wall loop", f"sector[{sector_id}]"))
            continue
        for index, loop in enumerate(loops):
            role = "outer" if index == 0 else "hole"
            for message in validate_loop(loop, role=role):
                out.append(Diagnostic("error", "invalid_loop", message, f"sector[{sector_id}].{role}"))
    return out


def validate_authored_level(
    source: DiskMap | LevelIR,
    *,
    intended_adjacency: Iterable[tuple[str | int, str | int]] | None = None,
    gated_sectors: Iterable[int] | None = None,
    declared_zero_exit: Iterable[int] | None = None,
    declared_specials: Iterable[tuple[int, int, str]] | None = None,
    required_resources: Iterable[int] | None = None,
    allocations: dict[str, int] | None = None,
    connection_report: list[dict[str, Any]] | None = None,
) -> list[Diagnostic]:
    """Geometry plus deathmatch circulation / intended-adjacency gates."""
    gated = set(int(item) for item in (gated_sectors or []))
    allowed_zero = set(int(item) for item in (declared_zero_exit or []))
    out = list(validate_authored_geometry(
        source,
        declared_specials=declared_specials,
        gated_sectors=gated,
        declared_zero_exit=allowed_zero,
    ))
    level = _as_level(source)
    audit = audit_geometry(
        source,
        declared_specials=declared_specials,
        gated_sectors=gated,
        declared_zero_exit=allowed_zero,
    )
    traversal = audit["traversal"]
    main = set(traversal["main_network"])
    names = allocations or {}

    def _sector_id(value: str | int) -> int:
        if isinstance(value, int):
            return value
        if value in names:
            return int(names[value])
        raise AuthoredGeometryError(f"unknown region id {value!r}")

    for sector_id in audit["summaries"].get("zero_exit_gameplay_sectors") or []:
        if sector_id in allowed_zero or sector_id in gated:
            out = [item for item in out if not (
                item.code == "zero_exit_gameplay_sector" and f"sector[{sector_id}]" in item.location
            )]
            continue
        if not any(item.code == "zero_exit_gameplay_sector" and f"sector[{sector_id}]" in item.location for item in out):
            out.append(Diagnostic(
                "error", "zero_exit_gameplay_sector",
                "large gameplay sector has zero exits and is not declared gated/helper",
                f"sector[{sector_id}]",
            ))

    dm_total = traversal["dm_starts_total"]
    dm_main = traversal["dm_starts_in_main"]
    if dm_total:
        if dm_main != dm_total:
            out.append(Diagnostic(
                "error", "all_dm_starts_reach_main_network",
                f"{dm_main}/{dm_total} DM starts reach the main circulation component",
                "starts",
            ))
        for item in audit["summaries"].get("unreachable_starts") or []:
            out.append(Diagnostic(
                "error", "isolated_dm_start",
                f"sprite {item['sprite']} ({item['type_name']}) is outside the main network",
                f"sprite[{item['sprite']}]",
            ))

    if required_resources is not None:
        reachable = set(main)
        # Gated resources may sit outside at-rest main; caller must name them.
        for sector_id in required_resources:
            if int(sector_id) not in reachable and int(sector_id) not in gated:
                out.append(Diagnostic(
                    "error", "required_resource_unreachable",
                    "required resource sector is outside the main network and not marked gated",
                    f"sector[{sector_id}]",
                ))

    owners = _wall_owners(level)
    portal_pairs: set[frozenset[int]] = set()
    for wall_id, wall in enumerate(level.walls):
        nxt = int(wall["fields"]["next_sector"])
        if nxt >= 0 and owners[wall_id] >= 0:
            portal_pairs.add(frozenset((owners[wall_id], nxt)))
    if intended_adjacency:
        for left, right in intended_adjacency:
            pair = frozenset((_sector_id(left), _sector_id(right)))
            if pair not in portal_pairs:
                out.append(Diagnostic(
                    "error", "intended_adjacency_missing",
                    f"intended connection {left!r} ↔ {right!r} was not realized as a reciprocal portal",
                    "adjacency",
                ))

    if connection_report:
        by_connection: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in connection_report:
            by_connection[str(item.get("connection_id") or "connection")].append(item)
            if item.get("status") != "realized":
                out.append(Diagnostic(
                    "error", "unresolved_intended_connection",
                    item.get("why") or "intended connection was not compiled",
                    item.get("connection_id") or "connection",
                ))
            if item.get("unintended"):
                out.append(Diagnostic(
                    "error", "unintended_portal",
                    "a portal exists that was not declared",
                    item.get("connection_id") or "connection",
                ))
        for connection_id, items in by_connection.items():
            realized = [item for item in items if item.get("status") == "realized"]
            if (
                realized
                and any(item.get("role") == "doorway" for item in realized)
                and not any(item.get("wide_enough", True) for item in realized)
            ):
                out.append(Diagnostic(
                    "error", "doorway_too_narrow",
                    "intended connection has no atomic portal meeting the required width",
                    connection_id,
                ))
    return out


def construction_preflight(diagnostics: list[Diagnostic]) -> None:
    errors = [item for item in diagnostics if item.severity == "error"]
    if errors:
        first = errors[0]
        raise AuthoredGeometryError(
            f"{len(errors)} authored-geometry error(s); first: {first.code} at {first.location}: {first.message}"
        )


def authored_geometry_report(diagnostics: list[Diagnostic]) -> dict[str, Any]:
    return {
        "errors": sum(1 for item in diagnostics if item.severity == "error"),
        "warnings": sum(1 for item in diagnostics if item.severity == "warning"),
        "diagnostics": [
            {"severity": item.severity, "code": item.code, "message": item.message, "location": item.location}
            for item in diagnostics
        ],
    }


def audit_markdown(audit: dict[str, Any], *, title: str = "Geometry audit") -> str:
    lines = [
        f"# {title}",
        "",
        f"Native `validate_map()` errors: **{audit['native_validation_errors']}**.",
        f"Authored conflicts: **{audit['counts']['error_conflicts']}** errors "
        f"of {audit['counts']['conflicts']} total findings.",
        "",
        f"Sectors {audit['counts']['sectors']}, walls {audit['counts']['walls']}, "
        f"sprites {audit['counts']['sprites']}.",
        "",
        "## Traversal",
        "",
        f"- components: {audit['traversal']['component_count']}",
        f"- main network size: {audit['traversal']['main_size']}",
        f"- DM starts in main: {audit['traversal']['dm_starts_in_main']} / {audit['traversal']['dm_starts_total']}",
        f"- walkable-at-rest edges: {audit['traversal']['walkable_edges']}",
        "",
    ]
    for heading, key in (
        ("Proper crossings", "proper_crossings"),
        ("T-junctions", "t_junctions"),
        ("Partial collinear overlaps", "partial_collinear_overlaps"),
        ("Unpaired coincident walls", "unpaired_coincident_walls"),
        ("Reciprocal portals", "reciprocal_portals"),
        ("Footprint intersections", "sector_footprint_intersections"),
        ("Zero-exit sectors", "zero_exit_gameplay_sectors"),
        ("Unreachable starts", "unreachable_starts"),
        ("Unreachable pickups", "unreachable_pickups"),
        ("Isolated components", "isolated_traversal_components"),
    ):
        values = audit["summaries"].get(key) or []
        lines.append(f"## {heading}")
        lines.append("")
        if not values:
            lines.append("None.")
            lines.append("")
            continue
        lines.append(f"{len(values)} finding(s).")
        lines.append("")
        for item in values[:80]:
            lines.append(f"- {_compact_finding(item)}")
        if len(values) > 80:
            lines.append(f"- … {len(values) - 80} more")
        lines.append("")
    lines.append("## Conflicts")
    lines.append("")
    for item in audit["conflicts"]:
        if item["severity"] == "info":
            continue
        lines.append(
            f"- **{item['severity']}** `{item['kind']}` walls={item.get('walls')} "
            f"sectors={item.get('sectors')}: {item['why']}"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def audit_svg(source: DiskMap | LevelIR, audit: dict[str, Any]) -> str:
    level = _as_level(source)
    if not level.walls:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"/>'
    xs = [int(wall["fields"]["x"]) for wall in level.walls]
    ys = [int(wall["fields"]["y"]) for wall in level.walls]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    width, height, margin = 1600, 1200, 40
    scale = min((width - 2 * margin) / max(1, max_x - min_x), (height - 2 * margin) / max(1, max_y - min_y))

    def xy(x: int, y: int) -> tuple[float, float]:
        return margin + (x - min_x) * scale, margin + (y - min_y) * scale

    owners = _wall_owners(level)
    portal_walls = set()
    unpaired = set()
    overlaps = set()
    junctions = []
    crossings = []
    for item in audit["summaries"].get("reciprocal_portals") or []:
        portal_walls.update(item["walls"])
    for item in audit["summaries"].get("unpaired_coincident_walls") or []:
        unpaired.update(item["walls"])
    for item in audit["summaries"].get("partial_collinear_overlaps") or []:
        overlaps.update(item["walls"])
    for item in audit["summaries"].get("t_junctions") or []:
        junctions.append(item["point"])
    for item in audit["summaries"].get("proper_crossings") or []:
        crossings.append(item["walls"])
    isolated = {sector for component in audit["summaries"].get("isolated_traversal_components") or [] for sector in component}
    overlap_sectors = set()
    for item in audit["summaries"].get("sector_footprint_intersections") or []:
        if item.get("severity") == "error":
            overlap_sectors.update(item["sectors"])

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#111318"/>',
        '<g fill-opacity="0.18">',
    ]
    for sector_id in range(len(level.sectors)):
        loops = _sector_loops(level, sector_id)
        if not loops:
            continue
        d = " ".join(
            "M " + " L ".join(f"{xy(*point)[0]:.1f},{xy(*point)[1]:.1f}" for point in loop) + " Z"
            for loop in loops
        )
        fill = "#c0392b" if sector_id in overlap_sectors else "#7f8c8d" if sector_id in isolated else "#2ecc71"
        parts.append(f'<path d="{d}" fill="{fill}" stroke="none"/>')
    parts.append("</g><g fill=\"none\" stroke-linecap=\"round\">")
    for wall_id, wall in enumerate(level.walls):
        start, end = _segment(level, wall_id)
        x1, y1 = xy(*start)
        x2, y2 = xy(*end)
        if wall_id in portal_walls:
            color, stroke = "#43a4db", 2.4
        elif wall_id in unpaired:
            color, stroke = "#e67e22", 2.2
        elif wall_id in overlaps:
            color, stroke = "#9b59b6", 2.4
        else:
            color, stroke = "#d8dde6", 0.7
        parts.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="{stroke}"/>'
        )
    parts.append("</g>")
    parts.append('<g>')
    for point in junctions:
        x, y = xy(int(point[0]), int(point[1]))
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#f1c40f"/>')
    for walls in crossings:
        start, end = _segment(level, walls[0])
        x, y = xy((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#e74c3c"/>')
    parts.append("</g>")
    parts.append(
        '<g font-family="monospace" font-size="12" fill="#ecf0f1">'
        '<text x="20" y="24">cyan=reciprocal portal  orange=unpaired coincident  '
        "magenta=partial collinear  yellow=T-junction  red=crossing/overlap  gray=isolated</text></g>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _compact_finding(item: Any) -> str:
    if isinstance(item, dict):
        walls = item.get("walls")
        sectors = item.get("sectors")
        kind = item.get("kind") or item.get("xy") or item.get("special")
        parts = []
        if kind:
            parts.append(str(kind))
        if sectors is not None:
            parts.append(f"sectors={sectors}")
        if walls is not None:
            parts.append(f"walls={walls}")
        if item.get("why"):
            parts.append(str(item["why"]))
        if item.get("point"):
            parts.append(f"point={item['point']}")
        return " ".join(parts) if parts else str(item)
    return str(item)
