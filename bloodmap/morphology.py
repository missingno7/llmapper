"""Architectural morphology over Build wall chains.

This is a geometric sensor, not a style rule. It reports how orthogonal,
diagonal, and irregular a map's walls and sector loops are. It does not
claim Blood maps must use diagonals.
"""

from __future__ import annotations

from collections import Counter
from math import atan2, degrees, hypot
from typing import Any

from .build_ir import BuildIR
from .design import _polygon_loops, _signed_area


SCHEMA = "llmapper.morphology"
SCHEMA_VERSION = 1
AXIS_TOLERANCE_DEG = 2.0
DIAGONAL_TOLERANCE_DEG = 8.0
RIGHT_ANGLE_TOLERANCE_DEG = 8.0


class MorphologyError(ValueError):
    pass


def _fold_deg(angle: float) -> float:
    value = angle % 180.0
    if value < 0:
        value += 180.0
    return value


def _axis_deviation(angle: float) -> float:
    folded = _fold_deg(angle) % 90.0
    return min(folded, 90.0 - folded)


def _is_orthogonal(angle: float) -> bool:
    return _axis_deviation(angle) <= AXIS_TOLERANCE_DEG


def _is_diagonal(angle: float) -> bool:
    folded = _fold_deg(angle) % 90.0
    return abs(folded - 45.0) <= DIAGONAL_TOLERANCE_DEG


def _turn_deg(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float | None:
    ux, uy = bx - ax, by - ay
    vx, vy = cx - bx, cy - by
    lu, lv = hypot(ux, uy), hypot(vx, vy)
    if lu < 1.0 or lv < 1.0:
        return None
    cross = ux * vy - uy * vx
    dot = ux * vx + uy * vy
    return degrees(atan2(cross, dot))


def _summary(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    ordered = sorted(values)
    return {
        "min": round(ordered[0], 4),
        "median": round(ordered[len(ordered) // 2], 4),
        "max": round(ordered[-1], 4),
        "mean": round(sum(ordered) / len(ordered), 4),
        "count": len(ordered),
    }


def _straight_runs(points: list[tuple[int, int]]) -> list[float]:
    n = len(points)
    if n < 2:
        return []
    runs: list[float] = []
    current = 0.0
    for index in range(n):
        ax, ay = points[index]
        bx, by = points[(index + 1) % n]
        current += hypot(bx - ax, by - ay)
        cx, cy = points[(index + 2) % n]
        turn = _turn_deg(ax, ay, bx, by, cx, cy)
        if turn is None or abs(turn) > AXIS_TOLERANCE_DEG:
            runs.append(current)
            current = 0.0
    if current > 0:
        if runs:
            runs[0] += current
        else:
            runs.append(current)
    return [value for value in runs if value >= 1.0]


def _curved_chain_count(turns: list[float]) -> int:
    """Count runs of at least four similar-signed shallow turns (segmented arcs)."""
    if len(turns) < 4:
        return 0
    chains = 0
    run = 0
    prev_sign = 0
    for turn in turns:
        sign = 1 if turn > AXIS_TOLERANCE_DEG else (-1 if turn < -AXIS_TOLERANCE_DEG else 0)
        shallow = 8.0 < abs(turn) < 50.0
        if sign and shallow and (prev_sign == 0 or sign == prev_sign):
            run += 1
            prev_sign = sign
        else:
            if run >= 4:
                chains += 1
            run = 1 if sign and shallow else 0
            prev_sign = sign if run else 0
    if run >= 4:
        chains += 1
    return chains


def _loop_metrics(points: list[tuple[int, int]]) -> dict[str, Any]:
    n = len(points)
    lengths = []
    turns = []
    orthogonal_corners = 0
    for index in range(n):
        ax, ay = points[index]
        bx, by = points[(index + 1) % n]
        lengths.append(hypot(bx - ax, by - ay))
        cx, cy = points[(index + 2) % n]
        turn = _turn_deg(ax, ay, bx, by, cx, cy)
        if turn is None:
            continue
        turns.append(abs(turn))
        if abs(abs(turn) - 90.0) <= RIGHT_ANGLE_TOLERANCE_DEG:
            orthogonal_corners += 1
    area = abs(_signed_area(points))
    aabb = (max(p[0] for p in points) - min(p[0] for p in points)) * (
        max(p[1] for p in points) - min(p[1] for p in points)
    )
    signed = [_turn_deg(*points[i], *points[(i + 1) % n], *points[(i + 2) % n]) for i in range(n)]
    defined = [value for value in signed if value is not None]
    left = sum(1 for value in defined if value > RIGHT_ANGLE_TOLERANCE_DEG)
    right = sum(1 for value in defined if value < -RIGHT_ANGLE_TOLERANCE_DEG)
    convex = bool(defined) and not (left and right)
    rectangular = (
        n == 4
        and orthogonal_corners == 4
        and all(_is_orthogonal(degrees(atan2(points[(i + 1) % n][1] - points[i][1], points[(i + 1) % n][0] - points[i][0]))) for i in range(n))
    )
    chamfer_corners = sum(1 for turn in turns if abs(abs(turn) - 45.0) <= DIAGONAL_TOLERANCE_DEG)
    return {
        "vertices": n,
        "lengths": lengths,
        "turns": turns,
        "orthogonal_corners": orthogonal_corners,
        "chamfer_corners": chamfer_corners,
        "rectangular": rectangular,
        "convex": convex,
        "aabb_fill": None if aabb <= 0 else round(area / aabb, 4),
        "straight_runs": _straight_runs(points),
        "curved_chains": _curved_chain_count(
            [value for value in signed if value is not None]
        ),
    }


def analyze_morphology(build: BuildIR, sector_ids: set[int] | None = None) -> dict[str, Any]:
    """Measure wall orientation, corner, and loop-shape variation."""
    if not build.walls:
        raise MorphologyError("map has no walls")
    selected = set(range(len(build.sectors))) if sector_ids is None else {int(value) for value in sector_ids}
    invalid = sorted(value for value in selected if not 0 <= value < len(build.sectors))
    if invalid:
        raise MorphologyError(f"sector IDs are out of range: {invalid}")
    ignored_degenerate = sorted(
        value for value in selected
        if int(build.sectors[value]["fields"]["wall_count"]) < 3
    )
    selected -= set(ignored_degenerate)
    if not selected:
        raise MorphologyError("sector selection contains no geometrically valid sectors")
    lengths_all: list[float] = []
    orthogonal_length = 0.0
    diagonal_length = 0.0
    orientation_bins: Counter[int] = Counter()
    wall_count = 0
    for wall in build.walls:
        fields = wall["fields"]
        point2 = int(fields["point2"])
        if not 0 <= point2 < len(build.walls):
            continue
        end = build.walls[point2]["fields"]
        dx = int(end["x"]) - int(fields["x"])
        dy = int(end["y"]) - int(fields["y"])
        length = hypot(dx, dy)
        if length < 1.0:
            continue
        wall_count += 1
        lengths_all.append(length)
        angle = _fold_deg(degrees(atan2(dy, dx)))
        orientation_bins[int(round(angle / 5.0) * 5) % 180] += 1
        if _is_orthogonal(angle):
            orthogonal_length += length
        if _is_diagonal(angle):
            diagonal_length += length
    occupied_bins = [bin_deg for bin_deg, count in orientation_bins.items() if count >= 2]
    loops = []
    rectangular_sectors = 0
    convex_sectors = 0
    vertex_counts: list[int] = []
    all_turns: list[float] = []
    all_runs: list[float] = []
    chamfer_corners = 0
    corner_count = 0
    curved_chains = 0
    fill_values: list[float] = []
    for sector_id in sorted(selected):
        sector_loops = _polygon_loops(build, sector_id)
        outer = max(sector_loops, key=lambda loop: abs(_signed_area(loop)))
        metrics = _loop_metrics(outer)
        vertex_counts.append(metrics["vertices"])
        all_turns.extend(metrics["turns"])
        all_runs.extend(metrics["straight_runs"])
        chamfer_corners += metrics["chamfer_corners"]
        corner_count += len(metrics["turns"])
        curved_chains += metrics["curved_chains"]
        if metrics["aabb_fill"] is not None:
            fill_values.append(metrics["aabb_fill"])
        if metrics["rectangular"]:
            rectangular_sectors += 1
        if metrics["convex"]:
            convex_sectors += 1
        loops.append({
            "sector": sector_id,
            "vertices": metrics["vertices"],
            "rectangular": metrics["rectangular"],
            "convex": metrics["convex"],
            "aabb_fill": metrics["aabb_fill"],
            "orthogonal_corner_fraction": None if not metrics["turns"] else round(
                metrics["orthogonal_corners"] / len(metrics["turns"]), 4
            ),
            "chamfer_corners": metrics["chamfer_corners"],
            "curved_chains": metrics["curved_chains"],
        })
    total_length = sum(lengths_all) or 1.0
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "model": "wall-chain and outer-loop morphology; not a room detector",
        "walls": {
            "counted": wall_count,
            "orthogonal_length_fraction": round(orthogonal_length / total_length, 4),
            "diagonal_length_fraction": round(diagonal_length / total_length, 4),
            "length_player_widths": _summary([value / 384.0 for value in lengths_all]),
            "orientation_5deg_bins_occupied": len(occupied_bins),
            "orientation_diversity": round(len(occupied_bins) / 36.0, 4),
            "orientation_bins": sorted(occupied_bins),
            "straight_run_player_widths": _summary([value / 384.0 for value in all_runs]),
        },
        "corners": {
            "count": corner_count,
            "angle_deg": _summary(all_turns),
            "orthogonal_fraction": None if not corner_count else round(
                sum(1 for turn in all_turns if abs(abs(turn) - 90.0) <= RIGHT_ANGLE_TOLERANCE_DEG) / corner_count, 4
            ),
            "chamfer_fraction": None if not corner_count else round(chamfer_corners / corner_count, 4),
            "segmented_arc_chain_count": curved_chains,
        },
        "sectors": {
            "count": len(selected),
            "rectangular_fraction": round(rectangular_sectors / max(1, len(selected)), 4),
            "convex_fraction": round(convex_sectors / max(1, len(selected)), 4),
            "outer_vertex_counts": _summary([float(value) for value in vertex_counts]),
            "aabb_fill": _summary(fill_values),
        },
        "loops": loops,
        "ignored_degenerate_sector_ids": ignored_degenerate,
        "limitations": [
            "inner loops are ignored for rectangularity",
            "slopes and sprites are ignored",
            "2 degree axis tolerance; 8 degree diagonal/right-angle tolerance",
            "segmented-arc chains are consecutive shallow same-sign turns, not true curves",
        ],
    }


SHAPE_KEYS = (
    "orthogonal_length_fraction",
    "diagonal_length_fraction",
    "orientation_5deg_bins_occupied",
    "orientation_diversity",
    "chamfer_fraction",
    "segmented_arc_chain_count",
    "rectangular_sector_fraction",
    "convex_sector_fraction",
    "median_outer_vertex_count",
)


def shape_signature(build: BuildIR) -> dict[str, float]:
    """One comparable shape vector per map, drawn from analyze_morphology."""
    report = analyze_morphology(build)
    walls, corners, sectors = report["walls"], report["corners"], report["sectors"]
    vertices = sectors.get("outer_vertex_counts") or {}
    return {
        "orthogonal_length_fraction": float(walls["orthogonal_length_fraction"]),
        "diagonal_length_fraction": float(walls["diagonal_length_fraction"]),
        "orientation_5deg_bins_occupied": float(walls["orientation_5deg_bins_occupied"]),
        "orientation_diversity": float(walls["orientation_diversity"]),
        "chamfer_fraction": float(corners.get("chamfer_fraction") or 0.0),
        "segmented_arc_chain_count": float(corners["segmented_arc_chain_count"]),
        "rectangular_sector_fraction": float(sectors["rectangular_fraction"]),
        "convex_sector_fraction": float(sectors["convex_fraction"]),
        "median_outer_vertex_count": float(vertices.get("median") or 0.0),
    }


def mine_shape_corpus(maps: list[tuple[str, BuildIR]]) -> dict[str, Any]:
    """Distribution of whole-map shape signatures, for corpus-relative comparison.

    This is the shape counterpart of ``player_space.mine_build_spatial_corpus``:
    it says what proportion of a real map's wall length is axis-aligned, how many
    orientations it uses, and how often its sectors are plain rectangles.  It
    assigns no labels and sets no targets; a candidate outside the corpus mass is
    unusual for this corpus, which is a question, not a verdict.
    """
    if not maps:
        raise MorphologyError("shape corpus is empty")
    samples: dict[str, list[float]] = {key: [] for key in SHAPE_KEYS}
    used: list[str] = []
    skipped: list[dict[str, str]] = []
    for name, build in maps:
        try:
            signature = shape_signature(build)
        except (MorphologyError, ValueError, KeyError) as exc:
            skipped.append({"map": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        used.append(name)
        for key in SHAPE_KEYS:
            samples[key].append(signature[key])
    if not used:
        raise MorphologyError("shape corpus has no maps the morphology sensor can analyze")
    return {
        "$schema": "llmapper.shape-corpus",
        "schema_version": SCHEMA_VERSION,
        "maps": used,
        "skipped": skipped,
        "samples": {key: values for key, values in samples.items()},
        "summaries": {key: _summary(values) for key, values in samples.items()},
        "notes": [
            "Percentiles are computed against these maps, not universal constants.",
            "Being outside the corpus mass is a question about the candidate, not a defect.",
            "Shape here is wall orientation and loop rectangularity only; it says nothing "
            "about whether a shape is good.",
        ],
    }
