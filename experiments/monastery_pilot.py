"""Drive the reasoned authoring loop over the cliffside monastery pilot.

Each candidate lives as standalone authored Python under
``projects/reasoned-authoring-v1/level/``.  This runner only loads one, hands it
to :func:`bloodmap.authoring_loop.evaluate_candidate`, and preserves the MAP,
the packet, and any captured views.  It makes no design decisions.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from bloodmap.authoring_loop import (
    AuthoringIteration,
    Candidate,
    attach_review,
    compare_iterations,
    evaluate_candidate,
    record_review,
    review_from_dict,
)

PROJECT = Path("projects/reasoned-authoring-v1")
LEVEL_DIR = PROJECT / "level"
REPORT_DIR = PROJECT / "reports"
DEFAULT_CATALOG = Path("work/blood.material-knowledge-v2.json")
DEFAULT_SPATIAL_CORPUS = Path("work/blood.spatial-corpus.json")
DEFAULT_SHAPE_CORPUS = Path("work/blood.shape-corpus.json")
DEFAULT_ART = Path("reference/blood")
ITERATIONS = ("v0", "v1", "v2", "v3")


def load_candidate(iteration: str) -> Candidate:
    path = LEVEL_DIR / f"candidate_{iteration}.py"
    if not path.is_file():
        raise SystemExit(f"no authored source for iteration {iteration}: {path}")
    spec = importlib.util.spec_from_file_location(f"monastery_{iteration}", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.candidate()


def engine_config(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.nblood or not args.game_dir:
        return None
    if not Path(args.nblood).is_file() or not Path(args.game_dir).is_dir():
        return None
    return {
        "nblood": args.nblood, "game_dir": args.game_dir,
        "grace_seconds": args.grace_seconds,
        "startup_timeout": args.startup_timeout,
        "settle_seconds": args.settle_seconds,
    }


def run_iteration(iteration: str, args: argparse.Namespace) -> AuthoringIteration:
    candidate = load_candidate(iteration)
    out = REPORT_DIR / iteration
    out.mkdir(parents=True, exist_ok=True)
    catalog = Path(args.catalog) if args.catalog else DEFAULT_CATALOG
    spatial = Path(args.spatial_corpus) if args.spatial_corpus else DEFAULT_SPATIAL_CORPUS
    shape = Path(args.shape_corpus) if args.shape_corpus else DEFAULT_SHAPE_CORPUS
    art_dir = Path(args.art_dir) if args.art_dir else DEFAULT_ART
    packet = evaluate_candidate(
        candidate,
        map_path=LEVEL_DIR / f"candidate-{iteration}.MAP",
        catalog_path=catalog if catalog.is_file() else None,
        art_directory=art_dir if art_dir.is_dir() else None,
        spatial_corpus_path=spatial if spatial.is_file() else None,
        shape_corpus_path=shape if shape.is_file() else None,
        engine=engine_config(args),
        view_dir=out / "views",
        work_dir=Path("work") / f"monastery-{iteration}",
    )
    review_path = PROJECT / "design" / "reviews" / f"{iteration}.json"
    if review_path.is_file():
        review = review_from_dict(json.loads(review_path.read_text(encoding="utf-8")))
        attach_review(packet, review)
        record_review(PROJECT, packet, review)
    (out / "iteration.json").write_text(
        json.dumps(packet.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    (out / "summary.md").write_text(summarize(packet), encoding="utf-8", newline="\n")
    return packet


def summarize(packet: AuthoringIteration) -> str:
    document = packet.to_dict()
    lines = [
        f"# Iteration {packet.identity['iteration_id']}", "",
        f"- source: `{packet.identity['module']}`",
        f"- MAP sha256: `{packet.identity['map_sha256']}`",
        f"- counts: {packet.identity['counts']}",
        f"- deterministic compile: {packet.identity['deterministic_compile']}",
        "", "## Hard gates", "",
    ]
    for gate in document["hard_gates"]:
        mark = {"pass": "PASS", "fail": "FAIL", "skipped": "SKIP"}[gate["status"]]
        lines.append(f"- **{mark}** `{gate['gate_id']}` — {gate['detail']}")
    counts = document["independent_hierarchy"]["counts"]
    lines += ["", "## Independently derived hierarchy", "",
              f"- assemblies {counts['assemblies']}, spaces {counts['spaces']}, "
              f"singletons {counts['singleton_spaces']}, detail groups {counts['detail_groups']}",
              f"- cross-space connections {counts['cross_space_connections']}, "
              f"vertical overlap relations {counts['vertical_overlap_relations']}",
              "", "### Authored assembly vs derived spaces", "",
              "| authored | sectors | derived spaces | dominant share | singletons |",
              "| --- | --- | --- | --- | --- |"]
    for row in document["hierarchy_comparison"]["assemblies"]:
        lines.append(
            f"| {row['authored_name']} | {len(row['sectors'])} | {row['derived_space_count']} "
            f"| {row['dominant_space_share']} | {len(row['singleton_space_ids'])} |"
        )
    lines += ["", "### Discrepancies", ""]
    if not document["hierarchy_comparison"]["discrepancies"]:
        lines.append("- none raised by the current rules")
    for item in document["hierarchy_comparison"]["discrepancies"]:
        lines.append(f"- `{item['kind']}` — {item['description']}")
        lines.append(f"  - rule: {item['rule']}")
        lines.append(f"  - evidence: {', '.join(item['evidence'])}")
    lines += ["", "## Probes", ""]
    for item in document["design_probes"]:
        measurements = item["result"].get("measurements", {})
        lines.append(
            f"- `{item['probe_id']}` ({item['declared']['probe_type']}) -> "
            f"**{item['result']['status']}** — {item['result'].get('answer', '')}"
        )
        if measurements:
            lines.append(f"  - {json.dumps(measurements, sort_keys=True)}")
    art = document["art_evidence"]
    lines += ["", "## ART and visual composition", "",
              f"- catalog: {art['catalog_status']}",
              f"- unresolved assets: {len(art['unresolved_assets'])}",
              f"- visually empty derived spaces: {len(art['visually_empty_spaces'])}",
              f"- decorative distribution: {json.dumps(art['decorative_distribution']['largest_share_in_one_space'])} "
              f"of {art['decorative_distribution']['total_space_sprites']} space sprites in one space"]
    if art["near_identical_treatments"]:
        lines.append("- near-identical surface vocabularies:")
        for item in art["near_identical_treatments"]:
            lines.append(f"  - {item['assemblies']} overlap {item['surface_vocabulary_overlap']}")
    if art.get("identical_room_treatments"):
        lines.append("- identical dominant room surfaces:")
        for item in art["identical_room_treatments"]:
            lines.append(f"  - {item['assemblies']} -> {item['dominant_surfaces']}")
    scale = document.get("corpus_scale") or {}
    if scale.get("spaces"):
        lines += ["", "## Corpus-relative scale and shape", "",
                  "| derived space | player areas | clear player heights | height pct vs same-size corpus |",
                  "| --- | --- | --- | --- |"]
        for item in sorted(scale["spaces"], key=lambda v: -v["footprint_player_areas"])[:10]:
            lines.append(
                f"| {item['node']} | {item['footprint_player_areas']} "
                f"| {item['clear_height_player_heights_area_weighted']} "
                f"| {item['height_percentile_vs_same_size_corpus_sectors']} |"
            )
        signature = (scale.get("shape") or {}).get("metrics") or []
        if signature:
            lines += ["", "| shape metric | candidate | corpus percentile |", "| --- | --- | --- |"]
            for item in signature:
                lines.append(f"| {item['metric']} | {item['candidate']} | {item['corpus_percentile']} |")
        sprite_scale = art.get("sprite_scale") or {}
        lines += ["", f"- sprite scale: {sprite_scale.get('status')}, "
                      f"{len(sprite_scale.get('findings', []))} oversized decoration(s)"]
        for item in sprite_scale.get("findings", []):
            lines.append(f"  - {item['description']}")
        lines += ["", "### Scale and shape findings", ""]
        if not scale.get("findings"):
            lines.append("- none raised by the current rules")
        for item in scale.get("findings", []):
            lines.append(f"- `{item['kind']}` — {item['description']}")
    lines += ["", "## Render", "",
              f"- capture status: {document['render'].get('capture_status')}"]
    if document["render"].get("capture_note"):
        lines.append(f"- note: {document['render']['capture_note']}")
    captures = (document["render"].get("captures") or {}).get("views", [])
    for item in captures:
        lines.append(f"- `{item['viewpoint_id']}` {item['status']} -> `{item['image']}`")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iterations", nargs="*", default=None,
                        help="iteration ids to run; default is every authored candidate")
    parser.add_argument("--nblood", help="path to NBlood executable for load smoke and views")
    parser.add_argument("--game-dir", help="path to local Blood game data")
    parser.add_argument("--catalog", help="mined material knowledge JSON")
    parser.add_argument("--spatial-corpus", help="mined player-relative spatial corpus JSON")
    parser.add_argument("--shape-corpus", help="mined shape corpus JSON")
    parser.add_argument("--art-dir", help="local Blood ART directory, for sprite world size")
    parser.add_argument("--grace-seconds", type=float, default=5.0)
    parser.add_argument("--startup-timeout", type=float, default=25.0)
    parser.add_argument("--settle-seconds", type=float, default=3.0)
    parser.add_argument("--comparison", action="store_true",
                        help="write reports/comparison.json across the run")
    args = parser.parse_args(argv)

    wanted = args.iterations or [
        name for name in ITERATIONS if (LEVEL_DIR / f"candidate_{name}.py").is_file()
    ]
    packets: list[AuthoringIteration] = []
    for iteration in wanted:
        packet = run_iteration(iteration, args)
        packets.append(packet)
        failures = [g["gate_id"] for g in packet.hard_gates if g["status"] == "fail"]
        print(
            f"{iteration}: sectors={packet.identity['counts']['sectors']} "
            f"walls={packet.identity['counts']['walls']} "
            f"sprites={packet.identity['counts']['sprites']} "
            f"failed_gates={failures or 'none'} "
            f"derived_spaces={packet.independent_hierarchy['counts']['spaces']} "
            f"discrepancies={len(packet.hierarchy_comparison['discrepancies'])}"
        )
    if args.comparison and packets:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        (REPORT_DIR / "comparison.json").write_text(
            json.dumps(compare_iterations(packets), indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"wrote {REPORT_DIR / 'comparison.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
