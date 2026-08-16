"""Counterfactual candidate evaluation.

Allows an agent to evaluate candidate edits without committing them to the main
authored state. This is the level-design equivalent of trying alternative
implementations and running tests.

Example:
    Current:
        church entrance width = 3072
    Candidate A:
        1536
    Candidate B:
        4096

    Run the same probe suite against each candidate.
    Return comparable results.

This is implemented through deterministic snapshots/clones/temporary IR variants,
not destructive edits.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .build_ir import BuildIR
from .probe_schema import DesignProbe, ProbeResult, run_probe


class CounterfactualError(ValueError):
    """A counterfactual evaluation constraint was violated."""


def evaluate_candidates(
    build: BuildIR,
    probes: list[DesignProbe],
    candidates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate candidate edits against a set of probes.

    Args:
        build: The original BuildIR instance.
        probes: List of DesignProbe instances to run against each candidate.
        candidates: Map of candidate_name -> edit operations.
            Each edit operation is a dict with:
                - "type": "set_field", "translate", "rotate", etc.
                - Additional parameters specific to the edit type.

    Returns:
        A dict with results for the original and each candidate:
        {
            "original": {probe_results...},
            "candidates": {
                "candidate_a": {probe_results...},
                "candidate_b": {probe_results...},
            },
            "comparison": {comparison_table...},
        }
    """
    results: dict[str, Any] = {
        "original": _run_probe_suite(build, probes),
        "candidates": {},
        "comparison": {},
    }

    for candidate_name, edits in candidates.items():
        candidate_build = _apply_edits(build, edits)
        results["candidates"][candidate_name] = _run_probe_suite(candidate_build, probes)

    # Build comparison table
    comparison: dict[str, dict[str, Any]] = {}
    for i, probe in enumerate(probes):
        probe_key = f"probe_{i}_{probe.probe_type}"
        comparison[probe_key] = {
            "question": probe.question,
            "probe_type": probe.probe_type,
            "original": _extract_key_metrics(results["original"][i]),
        }
        for candidate_name in candidates:
            comparison[probe_key][candidate_name] = _extract_key_metrics(
                results["candidates"][candidate_name][i]
            )

    results["comparison"] = comparison
    return results


def _run_probe_suite(
    build: BuildIR,
    probes: list[DesignProbe],
) -> list[ProbeResult]:
    """Run a suite of probes against a BuildIR instance."""
    results = []
    for probe in probes:
        try:
            result = run_probe(probe, build)
            results.append(result)
        except Exception as exc:
            results.append(ProbeResult(
                probe_type=probe.probe_type,
                status="error",
                question=probe.question,
                answer=f"Probe execution failed: {exc}",
                limitations=["Probe execution failed"],
            ))
    return results


def _apply_edits(
    build: BuildIR,
    edits: dict[str, Any],
) -> BuildIR:
    """Apply edit operations to a copy of the BuildIR.

    Supported edit types:
        - "set_field": Set a field on a sector/wall/sprite
        - "translate": Translate the entire build by dx, dy, dz
        - "rotate": Rotate the entire build by quarter turns
        - "set_wall_xy": Set a wall's x, y coordinates
        - "set_sector_z": Set a sector's floor_z and/or ceiling_z

    Returns a new BuildIR instance with the edits applied.
    """
    new_build = deepcopy(build)

    edit_type = edits.get("type", "")
    if edit_type == "set_field":
        obj_type = edits.get("object_type", "sector")
        obj_id = int(edits.get("object_id", 0))
        field_name = edits.get("field_name", "")
        field_value = int(edits.get("field_value", 0))

        if obj_type == "sector":
            new_build.sectors[obj_id]["fields"][field_name] = field_value
        elif obj_type == "wall":
            new_build.walls[obj_id]["fields"][field_name] = field_value
        elif obj_type == "sprite":
            new_build.sprites[obj_id]["fields"][field_name] = field_value
        else:
            raise CounterfactualError(f"unsupported object type: {obj_type}")

    elif edit_type == "translate":
        dx = int(edits.get("dx", 0))
        dy = int(edits.get("dy", 0))
        dz = int(edits.get("dz", 0))
        new_build.translate(dx, dy, dz)

    elif edit_type == "rotate":
        turns = int(edits.get("turns", 0))
        pivot_x = int(edits.get("pivot_x", 0))
        pivot_y = int(edits.get("pivot_y", 0))
        new_build.rotate_quarter_turns(turns, pivot_x, pivot_y)

    elif edit_type == "set_wall_xy":
        wall_id = int(edits.get("wall_id", 0))
        x = int(edits.get("x", 0))
        y = int(edits.get("y", 0))
        new_build.walls[wall_id]["fields"]["x"] = x
        new_build.walls[wall_id]["fields"]["y"] = y

    elif edit_type == "set_sector_z":
        sector_id = int(edits.get("sector_id", 0))
        if "floor_z" in edits:
            new_build.sectors[sector_id]["fields"]["floor_z"] = int(edits["floor_z"])
        if "ceiling_z" in edits:
            new_build.sectors[sector_id]["fields"]["ceiling_z"] = int(edits["ceiling_z"])

    else:
        raise CounterfactualError(f"unsupported edit type: {edit_type}")

    return new_build


def _extract_key_metrics(result: ProbeResult) -> dict[str, Any]:
    """Extract key metrics from a probe result for comparison."""
    metrics: dict[str, Any] = {
        "status": result.status,
        "answer": result.answer,
    }
    if result.measurements:
        metrics["measurements"] = result.measurements
    if result.route:
        metrics["route_length"] = len(result.route)
    if result.blocking_reasons:
        metrics["blocking_reasons"] = result.blocking_reasons
    if result.required_mechanisms:
        metrics["required_mechanisms"] = result.required_mechanisms
    return metrics
