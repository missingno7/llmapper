"""Architectural structure recovery: the layer between a space and its details.

``bloodmap.decompiler`` recovers two levels of grouping -- navigation assemblies
and perceptual spaces -- and then stops.  On a real campaign map that leaves a
long tail of one-sector "spaces" that are not places at all: stair treads,
alcoves, door volumes, ledges, the inner shell of a building.  They are the
*parts* rooms are built from, and they are exactly what an author writes as one
call rather than six.

This module recovers that missing layer from geometry alone.  Every candidate
carries the evidence that produced it, an essential parameter set that would
reconstruct something of the same shape, and the residual by which the original
differs from that reconstruction.  Nothing here reads an authored label, and
nothing here is a verdict: a structure candidate is a derived observation.

Deliberate non-goals: naming rooms, classifying mechanisms, and scoring quality.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import hypot
from statistics import mean, pstdev
from typing import Any, Sequence

from .model import LevelIR
from .planar_geom import Point, area2, point_in_loop
from .player_space import player_profile
from .spatial import analyze_spatial
from .viewpoints import _sector_loops

SCHEMA = "llmapper.level-structures"
SCHEMA_VERSION = 1

#: Kinds this module is willing to propose.  Each is defined by measurement in
#: the detector of the same name; none of them is a semantic claim about what a
#: designer meant.
KINDS = (
    "stepped_run",
    "landing",
    "recess",
    "overlook",
    "embedded_shell",
    "pit",
)


class StructureError(ValueError):
    """A structure recovery request cannot be satisfied."""


def _ref_id(ref: str) -> int:
    return int(ref.split(":", 1)[1])


@dataclass
class StructureCandidate:
    """One derived architectural structure and the evidence behind it."""

    structure_id: str
    kind: str
    sectors: tuple[int, ...]
    parameters: dict[str, Any]
    residual: dict[str, Any]
    evidence: dict[str, Any]
    attaches_to: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.structure_id,
            "kind": self.kind,
            "sectors": list(self.sectors),
            "attaches_to": list(self.attaches_to),
            "parameters": dict(self.parameters),
            "residual": dict(self.residual),
            "evidence": dict(self.evidence),
        }


@dataclass
class _Geometry:
    area: float
    floor_z: int
    ceiling_z: int
    clear_height: int
    centroid: tuple[float, float]
    loop_count: int
    sector_type: int


def _centroid(level: LevelIR, sector_id: int, fallback: dict[str, int]) -> tuple[float, float]:
    try:
        loops = _sector_loops(level, sector_id)
    except Exception:  # a malformed wall loop is not this module's problem
        return (
            (fallback["min_x"] + fallback["max_x"]) / 2.0,
            (fallback["min_y"] + fallback["max_y"]) / 2.0,
        )
    outer = loops[0]
    doubled = area2(tuple(outer))
    if doubled == 0:
        xs = [point[0] for point in outer]
        ys = [point[1] for point in outer]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    cx = cy = 0.0
    for index, (x0, y0) in enumerate(outer):
        x1, y1 = outer[(index + 1) % len(outer)]
        cross = x0 * y1 - x1 * y0
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    return (cx / (3.0 * doubled), cy / (3.0 * doubled))


def _geometry(level: LevelIR, spatial: dict[str, Any]) -> dict[int, _Geometry]:
    result: dict[int, _Geometry] = {}
    for record in spatial["views"]["geometry"]["sectors"]:
        sector_id = _ref_id(record["ref"])
        result[sector_id] = _Geometry(
            area=float(record["area"]),
            floor_z=int(record["floor_z"]),
            ceiling_z=int(record["ceiling_z"]),
            clear_height=int(record["clear_height"]),
            centroid=_centroid(level, sector_id, record["bounds"]),
            loop_count=int(record["wall_loop_count"]),
            sector_type=int(level.sectors[sector_id]["fields"]["type"]),
        )
    return result


def _portal_graph(
    spatial: dict[str, Any],
) -> tuple[dict[int, set[int]], dict[tuple[int, int], dict[str, Any]]]:
    """Adjacency over portals that are open at rest, plus the widest portal record."""
    graph: dict[int, set[int]] = defaultdict(set)
    portals: dict[tuple[int, int], dict[str, Any]] = {}
    for record in spatial["views"]["geometry"]["portals"]:
        left, right = sorted(_ref_id(ref) for ref in record["sectors"])
        existing = portals.get((left, right))
        if existing is None or float(record["width"]) > float(existing["width"]):
            portals[(left, right)] = record
        if record["blocking_flag"] or int(record["at_rest_opening"]) <= 0:
            continue
        graph[left].add(right)
        graph[right].add(left)
    return graph, portals


def _portal(
    portals: dict[tuple[int, int], dict[str, Any]], a: int, b: int,
) -> dict[str, Any] | None:
    return portals.get((min(a, b), max(a, b)))


def _spread(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "stdev": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": round(mean(values), 2),
        "stdev": round(pstdev(values), 2) if len(values) > 1 else 0.0,
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }


def _rise_graph(
    geometry: dict[int, _Geometry], graph: dict[int, set[int]], *, step_limit: int,
) -> tuple[dict[int, set[int]], dict[int, set[int]]]:
    """Neighbours reachable by a nonzero floor change the player can step over."""
    up: dict[int, set[int]] = defaultdict(set)
    down: dict[int, set[int]] = defaultdict(set)
    for sector_id in sorted(graph):
        for other in sorted(graph[sector_id]):
            delta = geometry[other].floor_z - geometry[sector_id].floor_z
            if delta == 0 or abs(delta) > step_limit:
                continue
            if delta > 0:
                up[sector_id].add(other)
            else:
                down[sector_id].add(other)
    return up, down


def _detect_stepped_runs(
    geometry: dict[int, _Geometry],
    graph: dict[int, set[int]], portals: dict[tuple[int, int], dict[str, Any]],
    *, step_limit: int, minimum_rises: int = 3, terminal_area_ratio: float = 4.0,
) -> list[StructureCandidate]:
    """Maximal monotone climbs in the sub-step rise graph.

    An earlier version required every tread to have exactly two open portals.
    That is how a stair in a corridor is built and not how a stair against an
    open room is built, and on E2M3 it saw 17 of the map's 72 sub-step rises.
    The rise graph ignores lateral portals entirely: a tread is a sector with
    exactly one neighbour a short step above it and one a short step below.
    """
    up, down = _rise_graph(geometry, graph, step_limit=step_limit)
    nodes = set(up) | set(down)
    paths: list[list[int]] = []
    used: set[int] = set()
    for start in sorted(nodes):
        # Walk upward from the bottom of a run only.
        if len(up[start]) != 1 or len(down[start]) == 1:
            continue
        path = [start]
        current = start
        while True:
            nxt = next(iter(up[current]))
            if nxt in path or len(down[nxt]) != 1:
                break
            path.append(nxt)
            if len(up[nxt]) != 1:
                break
            current = nxt
        if len(path) - 1 >= minimum_rises and not (set(path) & used):
            used.update(path)
            paths.append(path)

    result: list[StructureCandidate] = []
    for number, path in enumerate(paths, 1):
        areas = sorted(geometry[value].area for value in path)
        median_area = areas[len(areas) // 2]
        body = list(path)
        trimmed: list[int] = []
        for index in (0, -1):
            if len(body) <= minimum_rises:
                break
            terminal = body[index]
            if median_area > 0 and geometry[terminal].area > median_area * terminal_area_ratio:
                trimmed.append(terminal)
                body.pop(index)
        if len(body) < 2:
            continue
        attaches = sorted(
            {value for terminal in (body[0], body[-1]) for value in graph[terminal]} - set(body)
        )
        rises = [
            geometry[path[index + 1]].floor_z - geometry[path[index]].floor_z
            for index in range(len(path) - 1)
        ]
        widths = [
            float(_portal(portals, path[index], path[index + 1])["width"])
            for index in range(len(path) - 1)
        ]
        runs_xy = [
            hypot(
                geometry[path[index + 1]].centroid[0] - geometry[path[index]].centroid[0],
                geometry[path[index + 1]].centroid[1] - geometry[path[index]].centroid[1],
            )
            for index in range(len(path) - 1)
        ]
        total_rise = geometry[path[-1]].floor_z - geometry[path[0]].floor_z
        total_run = hypot(
            geometry[path[-1]].centroid[0] - geometry[path[0]].centroid[0],
            geometry[path[-1]].centroid[1] - geometry[path[0]].centroid[1],
        )
        rise_spread = _spread(rises)
        width_spread = _spread(widths)
        run_spread = _spread(runs_xy)
        heights = [geometry[value].clear_height for value in body]
        result.append(StructureCandidate(
            structure_id=f"structure:stepped_run:{number:03d}",
            kind="stepped_run",
            sectors=tuple(body),
            attaches_to=tuple(attaches),
            parameters={
                "rises": len(rises),
                "treads": len(body),
                "total_rise": int(total_rise),
                "total_run": round(total_run, 1),
                "width": round(width_spread["mean"], 1),
                "clear_height": int(min(heights)),
            },
            residual={
                "step_rise": rise_spread,
                "step_run": run_spread,
                "portal_width": width_spread,
                "uniform_rise": rise_spread["stdev"] == 0.0,
                "uniform_width": width_spread["stdev"] == 0.0,
                "trimmed_terminals": sorted(trimmed),
            },
            evidence={
                "rise_sequence": [int(value) for value in rises],
                "step_limit": step_limit,
                "basis": (
                    "monotone path in the sub-step rise graph; each tread has exactly one "
                    "neighbour a short step above and one a short step below"
                ),
                "terminal_area_ratio": terminal_area_ratio,
            },
        ))
    return result


def _detect_landings(
    geometry: dict[int, _Geometry], graph: dict[int, set[int]],
    runs: Sequence[StructureCandidate],
) -> list[StructureCandidate]:
    """A sector that two separate stepped runs both attach to.

    This is the compositional half of the "staircase with an intermediate
    landing" hypothesis.  It is reported separately from the runs so that a
    negative result stays visible: if no original map builds its stairs this
    way, the vocabulary must not offer a ``landing=`` parameter.
    """
    by_end: dict[int, list[StructureCandidate]] = defaultdict(list)
    members = {value for run in runs for value in run.sectors}
    for run in runs:
        for sector_id in run.attaches_to:
            by_end[sector_id].append(run)
    result: list[StructureCandidate] = []
    number = 0
    for sector_id, attached in sorted(by_end.items()):
        if len(attached) < 2 or sector_id in members:
            continue
        number += 1
        result.append(StructureCandidate(
            structure_id=f"structure:landing:{number:03d}",
            kind="landing",
            sectors=(sector_id,),
            attaches_to=tuple(sorted(run.sectors[0] for run in attached)),
            parameters={
                "area": round(geometry[sector_id].area, 1),
                "clear_height": int(geometry[sector_id].clear_height),
                "joins_runs": sorted(run.structure_id for run in attached),
                "open_portals": len(graph[sector_id]),
            },
            residual={},
            evidence={
                "basis": "a sector two distinct stepped runs both attach to",
                "run_rises": sorted(run.parameters["rises"] for run in attached),
            },
        ))
    return result


def _detect_recesses(
    geometry: dict[int, _Geometry], graph: dict[int, set[int]],
    portals: dict[tuple[int, int], dict[str, Any]], *, step_limit: int, ratio: float,
) -> list[StructureCandidate]:
    """A small dead-end opening off exactly one larger neighbour, floor-flush."""
    result: list[StructureCandidate] = []
    number = 0
    for sector_id in sorted(graph):
        neighbours = sorted(graph[sector_id])
        if len(neighbours) != 1:
            continue
        host = neighbours[0]
        here, there = geometry[sector_id], geometry[host]
        if here.area <= 0 or there.area <= 0:
            continue
        if here.area > there.area * ratio:
            continue
        if abs(here.floor_z - there.floor_z) > step_limit:
            continue
        record = _portal(portals, sector_id, host)
        if record is None:
            continue
        number += 1
        result.append(StructureCandidate(
            structure_id=f"structure:recess:{number:03d}",
            kind="recess",
            sectors=(sector_id,),
            attaches_to=(host,),
            parameters={
                "area": round(here.area, 1),
                "depth_ratio": round(here.area / there.area, 4),
                "opening_width": round(float(record["width"]), 1),
                "floor_delta": int(here.floor_z - there.floor_z),
                "ceiling_delta": int(here.ceiling_z - there.ceiling_z),
                "clear_height": int(here.clear_height),
            },
            residual={},
            evidence={
                "basis": "single open portal, area at or below the host ratio, floor within one step",
                "host_area": round(there.area, 1),
                "ratio_threshold": ratio,
                "sector_type": here.sector_type,
            },
        ))
    return result


def _detect_overlooks(
    geometry: dict[int, _Geometry], portals: dict[tuple[int, int], dict[str, Any]],
    *, step_limit: int, standing_height: int,
) -> list[StructureCandidate]:
    """A one-way vertical relationship: open enough to look through, too tall to climb."""
    result: list[StructureCandidate] = []
    number = 0
    for (left, right), record in sorted(portals.items()):
        if record["blocking_flag"]:
            continue
        if int(record["at_rest_opening"]) < standing_height:
            continue
        delta = geometry[right].floor_z - geometry[left].floor_z
        if abs(delta) <= step_limit:
            continue
        upper, lower = (left, right) if delta > 0 else (right, left)
        number += 1
        result.append(StructureCandidate(
            structure_id=f"structure:overlook:{number:03d}",
            kind="overlook",
            sectors=(upper,),
            attaches_to=(lower,),
            parameters={
                "drop": int(abs(delta)),
                "opening_width": round(float(record["width"]), 1),
                "upper_area": round(geometry[upper].area, 1),
                "lower_area": round(geometry[lower].area, 1),
            },
            residual={},
            evidence={
                "basis": "open portal whose floor delta exceeds one player step",
                "at_rest_opening": int(record["at_rest_opening"]),
                "step_limit": step_limit,
            },
        ))
    return result


def _detect_embedded_shells(
    level: LevelIR, geometry: dict[int, _Geometry],
) -> list[StructureCandidate]:
    """A sector with an inner wall loop that other sectors sit inside."""
    loops: dict[int, list[list[Point]]] = {}
    for sector_id in range(len(level.sectors)):
        try:
            loops[sector_id] = _sector_loops(level, sector_id)
        except Exception:  # a malformed loop is not this detector's problem
            loops[sector_id] = []
    result: list[StructureCandidate] = []
    number = 0
    for host in sorted(loops):
        host_loops = loops[host]
        if len(host_loops) < 2:
            continue
        for hole_index, hole in enumerate(host_loops[1:], 1):
            # Test the centroid rather than a vertex: a sector that exactly fills
            # the hole shares every vertex with it, and a point on the boundary
            # is not inside it.
            contained = [
                other for other in sorted(loops)
                if other != host and loops[other]
                and point_in_loop(
                    (int(round(geometry[other].centroid[0])),
                     int(round(geometry[other].centroid[1]))),
                    tuple(hole),
                ) == 1
            ]
            if not contained:
                continue
            number += 1
            inner_area = abs(area2(tuple(hole))) / 2.0
            result.append(StructureCandidate(
                structure_id=f"structure:embedded_shell:{number:03d}",
                kind="embedded_shell",
                sectors=tuple(contained),
                attaches_to=(host,),
                parameters={
                    "footprint": round(inner_area, 1),
                    "contained_sectors": len(contained),
                    "host_area": round(geometry[host].area, 1),
                    "occupies_host": round(inner_area / (inner_area + geometry[host].area), 4),
                },
                residual={},
                evidence={
                    "basis": "host wall loop encloses the outer loop of other sectors",
                    "host_loop_index": hole_index,
                    "vertices": len(hole),
                },
            ))
    return result


def _detect_pits(
    geometry: dict[int, _Geometry], graph: dict[int, set[int]], *, step_limit: int,
) -> list[StructureCandidate]:
    """A sector every open neighbour of which stands more than one step above it."""
    result: list[StructureCandidate] = []
    number = 0
    for sector_id in sorted(graph):
        neighbours = sorted(graph[sector_id])
        if not neighbours:
            continue
        drops = [geometry[value].floor_z - geometry[sector_id].floor_z for value in neighbours]
        if any(value >= -step_limit for value in drops):
            continue
        number += 1
        result.append(StructureCandidate(
            structure_id=f"structure:pit:{number:03d}",
            kind="pit",
            sectors=(sector_id,),
            attaches_to=tuple(neighbours),
            parameters={
                "area": round(geometry[sector_id].area, 1),
                "depth": int(min(abs(value) for value in drops)),
                "exits": len(neighbours),
                "clear_height": int(geometry[sector_id].clear_height),
            },
            residual={},
            evidence={
                "basis": "every open neighbour's floor is more than one step above this one",
                "step_limit": step_limit,
            },
        ))
    return result


def detect_structures(
    level: LevelIR, *, spatial: dict[str, Any] | None = None,
    recess_ratio: float = 0.25, profile: str = "blood",
) -> dict[str, Any]:
    """Recover architectural structure candidates from one level's geometry."""
    if spatial is None:
        spatial = analyze_spatial(level.to_disk_map().to_build_ir())
    player = player_profile(profile)
    geometry = _geometry(level, spatial)
    graph, portals = _portal_graph(spatial)
    runs = _detect_stepped_runs(geometry, graph, portals, step_limit=player.max_step)
    candidates: list[StructureCandidate] = list(runs)
    candidates.extend(_detect_landings(geometry, graph, runs))
    candidates.extend(_detect_recesses(
        geometry, graph, portals, step_limit=player.max_step, ratio=recess_ratio,
    ))
    candidates.extend(_detect_overlooks(
        geometry, portals, step_limit=player.max_step, standing_height=player.standing_height,
    ))
    candidates.extend(_detect_embedded_shells(level, geometry))
    candidates.extend(_detect_pits(geometry, graph, step_limit=player.max_step))

    covered: dict[str, set[int]] = defaultdict(set)
    for item in candidates:
        covered[item.kind].update(item.sectors)
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "model": (
            "derived architectural structures between the perceptual space and the "
            "individual sector; geometry only, never authored labels"
        ),
        "player_profile": {
            "name": profile,
            "body_width": player.body_width,
            "standing_height": player.standing_height,
            "max_step": player.max_step,
        },
        "structures": [item.to_dict() for item in candidates],
        "coverage": {
            "sectors": len(level.sectors),
            "sectors_in_a_structure": len({
                value for item in candidates for value in item.sectors
            }),
            "by_kind": {kind: len(covered[kind]) for kind in KINDS},
        },
        "limitations": [
            "detection is static: transient door and lift motion is ignored",
            "a stepped run is a measured climb, not a claim that the designer drew a staircase",
            "a recess is a small dead end; whether it reads as an alcove is not measured here",
            "residual records how far the original is from its own parameters, not whether that matters",
        ],
    }


def structure_index(document: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    """Map each sector to the structures that claim it."""
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in document["structures"]:
        for sector_id in item["sectors"]:
            result[sector_id].append(item)
    return dict(result)
