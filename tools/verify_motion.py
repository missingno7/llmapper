"""Check every converted moving sector against its Duke3D original.

Structural validation says a map is well formed.  The NBlood oracle says it
loads.  Neither says a door opens the right distance, turns the right way, or
stays out of the wall next to it.  This does:

.. code-block:: bash

    python -m tools.verify_motion maps/duke3d/E3L11.MAP -o work/motion-e3l11.json
    python -m tools.verify_motion --corpus maps/duke3d -o work/motion-corpus.json

For each moving sector it converts the map, replays the travel in both engines
(``bloodmap.motion_sim``), and reports three independent things:

*deviation* -- how far the Blood walls drift from the 3:2-scaled Duke walls
across the whole sweep.  Rounding the level into Blood coordinates costs a unit
or so; anything above ``--tolerance`` means the motion itself differs.

*folding* -- whether the moving sector's own outline crosses itself at any point
in its travel.  Build's renderer and clipper both assume a simple loop, so a
sector that folds is broken even though the map file validates.

*intrusion* -- whether the mover ends up overlapping a sector it does not share
a wall with.  Neighbours are excluded because they legitimately deform: the
engine's ``DragPoint`` moves shared vertices, so a door and its frame are
*supposed* to stay joined.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
from typing import Any

from bloodmap.duke import read_duke_map
from bloodmap.e3l11 import convert_playable_duke_to_blood
from bloodmap.format import encode_map, parse_map
from bloodmap.motion_sim import (
    blood_sector_walls,
    duke_sector_walls,
    blood_sweep,
    compare_sweeps,
    duke_sweep,
    polygons_overlap,
    rest_displacement,
    self_intersections,
)

MOVING_KINDS = {"sliding-door", "rotate-bridge", "swinging-door", "stretch-bridge"}


def _neighbors(level: Any, sector_id: int) -> set[int]:
    fields = level.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    result = set()
    for wall in range(start, start + int(fields["wall_count"])):
        nxt = int(level.walls[wall].fields["next_sector"])
        if nxt >= 0:
            result.add(nxt)
    return result


def verify_map(duke_path: pathlib.Path, *, steps: int, tolerance: float,
               check_intrusion: bool) -> dict[str, Any]:
    duke = read_duke_map(duke_path)
    disk, report = convert_playable_duke_to_blood(duke)
    level = parse_map(encode_map(disk))

    # Every sector that moves, and where it ends up. A rotating assembly is
    # several sectors turning about one pivot in formation, so checking a moved
    # leaf against another leaf's *authored* outline reports an overlap that
    # never happens: the second leaf has swung out of the way too.
    final_outline: dict[int, list[tuple[float, float]]] = {}
    duke_final_outline: dict[int, list[tuple[float, float]]] = {}
    for record in report["mechanisms"]["records"]:
        if record.get("kind") not in MOVING_KINDS:
            continue
        moving_id = int(record["source_sector"])
        try:
            final_outline[moving_id] = blood_sweep(level, moving_id, steps=steps)[-1]
            duke_final_outline[moving_id] = duke_sweep(
                duke, int(record["source_effector"]), steps=steps)[-1]
        except (ValueError, IndexError, KeyError):
            continue

    findings: list[dict[str, Any]] = []
    for record in report["mechanisms"]["records"]:
        if record.get("kind") not in MOVING_KINDS:
            continue
        sector_id = int(record["source_sector"])
        entry: dict[str, Any] = {
            "kind": record["kind"],
            "sector": sector_id,
            "blood_type": record.get("blood_type"),
        }
        try:
            duke_frames = duke_sweep(duke, int(record["source_effector"]), steps=steps)
            blood_frames = blood_sweep(level, sector_id, steps=steps)
            comparison = compare_sweeps(duke_frames, blood_frames)
        except (ValueError, IndexError, KeyError) as error:
            entry.update(status="unmodelled", reason=str(error))
            findings.append(entry)
            continue

        entry.update(comparison)
        # A mechanism that is displaced before anything triggers it is broken in
        # a way the relative comparison cannot see, because that measures each
        # sweep against its own first frame.
        entry["rest_displacement"] = round(rest_displacement(level, sector_id, blood_frames), 2)
        # Folding gets the same treatment as overlap: a swinging door built from
        # a sliver sector folds in Duke too, and E3L8's sector 5 is already
        # self-intersecting as authored, before anything moves. What matters is
        # whether the conversion introduced a fold the original does not have.
        folds = [step for step, frame in enumerate(blood_frames) if self_intersections(frame)]
        duke_folds = [step for step, frame in enumerate(duke_frames) if self_intersections(frame)]
        entry["folds_at_steps"] = folds
        entry["duke_folds_at_steps"] = duke_folds
        entry["fold_inherited"] = bool(folds and duke_folds)
        introduced_fold = bool(folds) and not duke_folds

        # Overlap on its own is not a defect. Duke levels park bridge leaves on
        # top of each other at different floor heights, and a plan-view test
        # cannot tell that from a door grinding through a wall. So the question
        # is not "does the Blood sector overlap something" but "does it overlap
        # something its Duke original does not" -- a difference from the source
        # is the bug; a shared behaviour was authored.
        blood_hits: list[int] = []
        duke_hits: list[int] = []
        if check_intrusion:
            skip = _neighbors(level, sector_id) | {sector_id}
            candidates = [other for other in range(len(level.sectors)) if other not in skip]
            blood_final = blood_frames[-1]
            duke_final = duke_frames[-1]
            for other in candidates:
                blood_other = final_outline.get(other) or blood_sector_walls(level, other)
                if polygons_overlap(blood_final, blood_other):
                    blood_hits.append(other)
                duke_other = duke_final_outline.get(other) or duke_sector_walls(duke, other)
                if polygons_overlap(duke_final, duke_other):
                    duke_hits.append(other)
        intrusions = sorted(set(blood_hits) - set(duke_hits))
        entry["intrudes_into"] = intrusions
        entry["overlaps_in_both"] = sorted(set(blood_hits) & set(duke_hits))
        entry["duke_only_overlaps"] = sorted(set(duke_hits) - set(blood_hits))

        problems = []
        if comparison["max_deviation"] > tolerance:
            problems.append("deviation")
        if entry["rest_displacement"] > tolerance:
            problems.append("displaced_at_rest")
        if introduced_fold:
            problems.append("folds")
        if intrusions:
            problems.append("intrusion")
        entry["status"] = "ok" if not problems else "problem"
        entry["problems"] = problems
        findings.append(entry)

    modelled = [f for f in findings if f["status"] != "unmodelled"]
    return {
        "map": duke_path.stem.upper(),
        "moving_sectors": len(findings),
        "modelled": len(modelled),
        "ok": sum(1 for f in modelled if f["status"] == "ok"),
        "problems": sum(1 for f in modelled if f["status"] == "problem"),
        "worst_deviation": max((f["max_deviation"] for f in modelled), default=0.0),
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", nargs="?", help="a Duke3D MAP")
    parser.add_argument("--corpus", help="verify every MAP in this directory instead")
    parser.add_argument("-o", "--output")
    parser.add_argument("--steps", type=int, default=16,
                        help="samples across the travel; more finds narrower folds")
    parser.add_argument("--tolerance", type=float, default=8.0,
                        help="Blood units of drift attributable to 3:2 rounding")
    parser.add_argument("--no-intrusion", action="store_true",
                        help="skip the sector-overlap pass, which is the slow one")
    args = parser.parse_args(argv)

    if not args.map and not args.corpus:
        parser.error("give a MAP or --corpus")

    paths = (
        [pathlib.Path(p) for p in sorted(glob.glob(str(pathlib.Path(args.corpus) / "*.MAP")))]
        if args.corpus else [pathlib.Path(args.map)]
    )
    results, failures = [], []
    seen: set[str] = set()
    for path in paths:
        if path.stem.upper() in seen:
            continue
        seen.add(path.stem.upper())
        try:
            results.append(verify_map(
                path, steps=args.steps, tolerance=args.tolerance,
                check_intrusion=not args.no_intrusion,
            ))
        except Exception as error:  # a map that will not convert is its own finding
            failures.append({"map": path.stem.upper(), "error": f"{type(error).__name__}: {error}"})

    summary = {
        "$schema": "llmapper.motion-verification",
        "schema_version": 1,
        "tolerance": args.tolerance,
        "steps": args.steps,
        "maps": len(results),
        "conversion_failures": failures,
        "moving_sectors": sum(r["moving_sectors"] for r in results),
        "modelled": sum(r["modelled"] for r in results),
        "ok": sum(r["ok"] for r in results),
        "problems": sum(r["problems"] for r in results),
        "worst_deviation": max((r["worst_deviation"] for r in results), default=0.0),
        "results": results,
    }
    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
