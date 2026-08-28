"""Mine architectural structures from the Blood campaign and test abstractions.

This is the evidence step between "a shape occurs in E2M3" and "a constructor
belongs in the authoring vocabulary".  It never promotes anything by itself; it
produces the numbers a promotion decision has to survive.

    python -m tools.mine_structures --maps maps/blood \\
        -o projects/e2m3-decompiled/references/abstraction-candidates.json

The split is by episode, not by random sample: fitting on episodes 1-3 and
testing on 4 and 6 asks whether an abstraction transfers to *different maps by
the same team*, which is the question that matters for authoring.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import Counter, defaultdict
from math import hypot
from typing import Any

from bloodmap.design import _polygon_loops, _signed_area
from bloodmap.format import read_map
from bloodmap.morphology import _turn_deg
from bloodmap.structures import detect_structures

SCHEMA = "llmapper.abstraction-candidates"
SCHEMA_VERSION = 1

FIT_EPISODES = ("E1", "E2", "E3")
HELD_OUT_EPISODES = ("E4", "E6")

PLAYER_WIDTH = 384

from bloodmap.player_space import PLAYER_PROFILES

#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

#: Matches bloodmap.morphology._curved_chain_count so the mined parameters
#: describe the same chains the shape corpus counts.
ARC_MIN_SEGMENTS = 4
ARC_SHALLOW_LOW = 8.0
ARC_SHALLOW_HIGH = 50.0
ARC_AXIS_TOLERANCE = 2.0


def _percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "p10": round(ordered[len(ordered) // 10], 4),
        "median": round(statistics.median(ordered), 4),
        "p90": round(ordered[len(ordered) * 9 // 10], 4),
        "min": round(ordered[0], 4),
        "max": round(ordered[-1], 4),
    }


def _arc_chains(points: list[tuple[int, int]]) -> list[dict[str, Any]]:
    """Segmented-arc chains in one loop, with the parameters a constructor needs."""
    count = len(points)
    signed = [
        _turn_deg(*points[index], *points[(index + 1) % count], *points[(index + 2) % count])
        for index in range(count)
    ]
    chains: list[list[tuple[int, float]]] = []
    run: list[tuple[int, float]] = []
    previous = 0
    for index, turn in enumerate(signed):
        if turn is None:
            sign, shallow = 0, False
        else:
            sign = 1 if turn > ARC_AXIS_TOLERANCE else (-1 if turn < -ARC_AXIS_TOLERANCE else 0)
            shallow = ARC_SHALLOW_LOW < abs(turn) < ARC_SHALLOW_HIGH
        if sign and shallow and (previous == 0 or sign == previous):
            run.append((index, turn))
            previous = sign
        else:
            if len(run) >= ARC_MIN_SEGMENTS:
                chains.append(run)
            run = [(index, turn)] if (sign and shallow) else []
            previous = sign if run else 0
    if len(run) >= ARC_MIN_SEGMENTS:
        chains.append(run)

    result: list[dict[str, Any]] = []
    for chain in chains:
        turns = [abs(turn) for _index, turn in chain]
        lengths = [
            hypot(
                points[(index + 2) % count][0] - points[(index + 1) % count][0],
                points[(index + 2) % count][1] - points[(index + 1) % count][1],
            )
            for index, _turn in chain
        ]
        mean_turn = statistics.mean(turns)
        mean_length = statistics.mean(lengths)
        result.append({
            "segments": len(chain) + 1,
            "turn_mean_deg": round(mean_turn, 3),
            "turn_relative_stdev": round(
                (statistics.pstdev(turns) / mean_turn) if (len(turns) > 1 and mean_turn) else 0.0, 4
            ),
            "segment_length": round(mean_length, 1),
            "segment_length_player_widths": round(mean_length / PLAYER_WIDTH, 3),
            "sweep_deg": round(sum(turns), 1),
        })
    return result


def observe_map(path: pathlib.Path) -> dict[str, Any]:
    disk = read_map(path)
    level = disk.to_level_ir()
    document = detect_structures(level)
    build = disk.to_build_ir()
    arcs: list[dict[str, Any]] = []
    for sector_id in range(len(build.sectors)):
        try:
            loops = _polygon_loops(build, sector_id)
        except Exception:  # a malformed loop is not this tool's problem
            continue
        outer = max(loops, key=lambda loop: abs(_signed_area(loop)))
        arcs.extend(_arc_chains(outer))
    return {
        "map": path.stem,
        "sectors": len(level.sectors),
        "structures": document["structures"],
        "coverage": document["coverage"],
        "arc_chains": arcs,
    }


def _episode(name: str) -> str:
    return name[:2].upper()


def _stepped_run_candidate(fit: list[dict], held: list[dict]) -> dict[str, Any]:
    vocabulary_counts: Counter[int] = Counter()
    for item in fit:
        for value in item["evidence"]["rise_sequence"]:
            vocabulary_counts[abs(int(value))] += 1
    fitted = sorted(value for value, count in vocabulary_counts.items() if count >= 10)
    covered = sum(count for value, count in vocabulary_counts.items() if value in fitted)

    def score(rows: list[dict]) -> dict[str, Any]:
        exact = mixed = 0
        residual: list[dict[str, Any]] = []
        for item in rows:
            sequence = [abs(int(value)) for value in item["evidence"]["rise_sequence"]]
            if len(set(sequence)) == 1 and sequence[0] in fitted:
                exact += 1
            elif set(sequence) <= set(fitted):
                mixed += 1
            else:
                residual.append({"map": item["map"], "rise_sequence": sequence})
        total = max(1, len(rows))
        return {
            "examples": len(rows),
            "exact_constant_rise": exact,
            "exact_fraction": round(exact / total, 4),
            "mixed_but_in_vocabulary": mixed,
            "residual": residual,
        }

    everything = fit + held
    return {
        "candidate": "staircase",
        "derived_from": "structures.stepped_run",
        "occurrences": len(everything),
        "maps_with_at_least_one": len({item["map"] for item in everything}),
        "fitted_step_rise_vocabulary": fitted,
        "fit_rise_coverage": round(covered / max(1, sum(vocabulary_counts.values())), 4),
        "parameters": {
            "essential": {
                "rises": _percentiles([float(item["parameters"]["rises"]) for item in everything]),
                "total_rise": _percentiles(
                    [abs(float(item["parameters"]["total_rise"])) for item in everything]
                ),
                "width_player_widths": _percentiles(
                    [float(item["parameters"]["width"]) / PLAYER_WIDTH for item in everything]
                ),
            },
            "expressive": {
                "step_rise_histogram": dict(sorted(vocabulary_counts.items())),
            },
            "residual_not_exposed": {
                "relative_width_stdev": _percentiles([
                    item["residual"]["portal_width"]["stdev"] / item["residual"]["portal_width"]["mean"]
                    for item in everything if item["residual"]["portal_width"]["mean"]
                ]),
                "uniform_rise_fraction": round(
                    sum(1 for item in everything if item["residual"]["uniform_rise"])
                    / max(1, len(everything)), 4
                ),
            },
        },
        "fit": score(fit),
        "held_out": score(held),
    }


def _recess_candidate(fit: list[dict], held: list[dict]) -> dict[str, Any]:
    def profile(rows: list[dict]) -> dict[str, Any]:
        total = max(1, len(rows))
        return {
            "examples": len(rows),
            "floor_flush_fraction": round(
                sum(1 for item in rows if item["parameters"]["floor_delta"] == 0) / total, 4
            ),
            "lower_ceiling_fraction": round(
                sum(1 for item in rows if item["parameters"]["ceiling_delta"] > 0) / total, 4
            ),
            "area_fraction_of_host": _percentiles(
                [float(item["parameters"]["depth_ratio"]) for item in rows]
            ),
            "opening_width_player_widths": _percentiles(
                [float(item["parameters"]["opening_width"]) / PLAYER_WIDTH for item in rows]
            ),
            "footprint_player_areas": _percentiles(
                [float(item["parameters"]["area"]) / (PLAYER_WIDTH ** 2) for item in rows]
            ),
        }

    everything = fit + held
    return {
        "candidate": "recess",
        "derived_from": "structures.recess",
        "occurrences": len(everything),
        "maps_with_at_least_one": len({item["map"] for item in everything}),
        "fit": profile(fit),
        "held_out": profile(held),
    }


def _shell_candidate(fit: list[dict], held: list[dict]) -> dict[str, Any]:
    def profile(rows: list[dict]) -> dict[str, Any]:
        total = max(1, len(rows))
        return {
            "examples": len(rows),
            "rectangular_fraction": round(
                sum(1 for item in rows if item["evidence"]["vertices"] == 4) / total, 4
            ),
            "occupies_host": _percentiles(
                [float(item["parameters"]["occupies_host"]) for item in rows]
            ),
            "contained_sectors": _percentiles(
                [float(item["parameters"]["contained_sectors"]) for item in rows]
            ),
            "hole_vertices": _percentiles([float(item["evidence"]["vertices"]) for item in rows]),
        }

    everything = fit + held
    return {
        "candidate": "embedded_shell",
        "derived_from": "structures.embedded_shell",
        "occurrences": len(everything),
        "maps_with_at_least_one": len({item["map"] for item in everything}),
        "fit": profile(fit),
        "held_out": profile(held),
    }


def _landing_candidate(rows: list[dict]) -> dict[str, Any]:
    small = [
        item for item in rows
        if float(item["parameters"]["area"]) / (PLAYER_WIDTH ** 2) < 10.0
    ]
    return {
        "candidate": "landing",
        "derived_from": "structures.landing",
        "occurrences": len(rows),
        "maps_with_at_least_one": len({item["map"] for item in rows}),
        "stair_sized": {
            "definition": "under 10 player areas of floor",
            "count": len(small),
            "maps": sorted({item["map"] for item in small}),
            "examples": [
                {
                    "map": item["map"],
                    "player_areas": round(float(item["parameters"]["area"]) / (PLAYER_WIDTH ** 2), 2),
                    "open_portals": item["parameters"]["open_portals"],
                }
                for item in small
            ],
        },
        "room_sized": len(rows) - len(small),
    }


def _relation_candidate(name: str, fit: list[dict], held: list[dict], key: str,
                        extra: tuple[str, ...] = ()) -> dict[str, Any]:
    """Overlooks and pits, with the same fit/held-out split the others get.

    These two used to report one pooled distribution, which is enough to say a
    shape is common and not enough to promote it: the reading guide asks for a
    held-out figure that matches the fitted one, and a pooled number cannot
    produce that. The extra keys are the parameters a *constructor* would take,
    because a distribution over something the vocabulary cannot express is not
    evidence for adding it.
    """
    def profile(rows: list[dict]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "examples": len(rows),
            "measure_player_heights": _percentiles(
                [float(item["parameters"][key]) / PLAYER_HEIGHT for item in rows]
            ),
        }
        for field in extra:
            values = [
                float(item["parameters"][field])
                for item in rows if field in item["parameters"]
            ]
            if values:
                result[field] = _percentiles(values)
        return result

    everything = fit + held
    return {
        "candidate": name,
        "derived_from": f"structures.{name}",
        "occurrences": len(everything),
        "maps_with_at_least_one": len({item["map"] for item in everything}),
        "measure_player_heights": _percentiles(
            [float(item["parameters"][key]) / PLAYER_HEIGHT for item in everything]
        ),
        "fit": profile(fit),
        "held_out": profile(held),
    }


def _arc_candidate(fit: list[dict], held: list[dict], per_map: dict[str, int]) -> dict[str, Any]:
    def profile(rows: list[dict]) -> dict[str, Any]:
        return {
            "examples": len(rows),
            "segments_per_chain": _percentiles([float(item["segments"]) for item in rows]),
            "turn_per_segment_deg": _percentiles([float(item["turn_mean_deg"]) for item in rows]),
            "segment_length_player_widths": _percentiles(
                [float(item["segment_length_player_widths"]) for item in rows]
            ),
            "sweep_deg": _percentiles([float(item["sweep_deg"]) for item in rows]),
            "turn_relative_stdev": _percentiles(
                [float(item["turn_relative_stdev"]) for item in rows]
            ),
        }

    everything = fit + held
    return {
        "candidate": "arc",
        "derived_from": "morphology segmented-arc chains",
        "occurrences": len(everything),
        "maps_with_at_least_one": sum(1 for value in per_map.values() if value),
        "chains_per_map": _percentiles([float(value) for value in per_map.values()]),
        "fit": profile(fit),
        "held_out": profile(held),
    }


def mine(directory: pathlib.Path, pattern: str = "E?M*.MAP") -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for path in sorted(directory.glob(pattern)):
        try:
            observations.append(observe_map(path))
        except Exception as exc:  # a corpus map this analysis cannot read
            skipped.append({"map": path.stem, "reason": str(exc)})

    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    arcs_by_map: dict[str, int] = {}
    arcs: list[dict[str, Any]] = []
    for item in observations:
        for structure in item["structures"]:
            record = dict(structure)
            record["map"] = item["map"]
            by_kind[structure["kind"]].append(record)
        arcs_by_map[item["map"]] = len(item["arc_chains"])
        for chain in item["arc_chains"]:
            record = dict(chain)
            record["map"] = item["map"]
            arcs.append(record)

    def split(rows: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
        return (
            [item for item in rows if _episode(item["map"]) in FIT_EPISODES],
            [item for item in rows if _episode(item["map"]) in HELD_OUT_EPISODES],
        )

    run_fit, run_held = split(by_kind["stepped_run"])
    rec_fit, rec_held = split(by_kind["recess"])
    shell_fit, shell_held = split(by_kind["embedded_shell"])
    overlook_fit, overlook_held = split(by_kind["overlook"])
    pit_fit, pit_held = split(by_kind["pit"])
    arc_fit, arc_held = split(arcs)

    candidates = [
        _stepped_run_candidate(run_fit, run_held),
        _recess_candidate(rec_fit, rec_held),
        _arc_candidate(arc_fit, arc_held, arcs_by_map),
        _shell_candidate(shell_fit, shell_held),
        _landing_candidate(by_kind["landing"]),
        _relation_candidate("overlook", overlook_fit, overlook_held, "drop",
                            ("opening_width", "upper_area", "lower_area")),
        _relation_candidate("pit", pit_fit, pit_held, "depth",
                            ("area", "exits", "clear_height")),
    ]
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "corpus": {
            "directory": str(directory),
            "pattern": pattern,
            "maps_analysed": len(observations),
            "maps_skipped": skipped,
            "fit_episodes": list(FIT_EPISODES),
            "held_out_episodes": list(HELD_OUT_EPISODES),
        },
        "per_map": [
            {"map": item["map"], "sectors": item["sectors"], **item["coverage"]["by_kind"],
             "arc_chains": arcs_by_map[item["map"]]}
            for item in observations
        ],
        "candidates": candidates,
        "reading_guide": [
            "occurrence counts describe how often a shape appears, never how good it is",
            "a held-out figure that matches its fit figure is the only reason to promote",
            "residual entries record what the abstraction does not reproduce; that is the point",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--pattern", default="E?M*.MAP")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    document = mine(pathlib.Path(args.maps), args.pattern)
    text = json.dumps(document, indent=1, sort_keys=False)
    if args.output:
        path = pathlib.Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path} ({len(text)} bytes)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
