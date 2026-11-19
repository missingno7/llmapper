"""Drive the reasoned authoring loop over the cliffside monastery pilot.

Each candidate lives as standalone authored Python under
``projects/reasoned-authoring-v1/level/``.  This runner only loads one, hands it
to :func:`bloodmap.authoring_loop.evaluate_candidate`, and preserves the MAP,
the packet, and any captured views.  It makes no design decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from bloodmap.authoring_loop import (
    AuthoringIteration,
    Candidate,
    compare_iterations,
    evaluate_candidate,
)

PROJECT = Path("projects/reasoned-authoring-v1")
LEVEL_DIR = PROJECT / "level"
DEFAULT_CATALOG = Path("work/blood.material-knowledge-v2.json")
DEFAULT_SPATIAL_CORPUS = Path("work/blood.spatial-corpus.json")
DEFAULT_SHAPE_CORPUS = Path("work/blood.shape-corpus.json")
DEFAULT_SURFACE_CORPUS = Path("work/blood.surface-corpus.json")
DEFAULT_ART = Path("reference/blood")
ITERATIONS = ("v0", "v1", "v2", "v3", "v4", "v5")


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
    out = args.run_dir / iteration
    out.mkdir(parents=True, exist_ok=False)
    catalog = Path(args.catalog) if args.catalog else DEFAULT_CATALOG
    spatial = Path(args.spatial_corpus) if args.spatial_corpus else DEFAULT_SPATIAL_CORPUS
    shape = Path(args.shape_corpus) if args.shape_corpus else DEFAULT_SHAPE_CORPUS
    surface = Path(args.surface_corpus) if args.surface_corpus else DEFAULT_SURFACE_CORPUS
    art_dir = Path(args.art_dir) if args.art_dir else DEFAULT_ART
    packet = evaluate_candidate(
        candidate,
        map_path=out / "candidate.MAP",
        catalog_path=catalog if catalog.is_file() else None,
        art_directory=art_dir if art_dir.is_dir() else None,
        spatial_corpus_path=spatial if spatial.is_file() else None,
        shape_corpus_path=shape if shape.is_file() else None,
        surface_corpus_path=surface if surface.is_file() else None,
        engine=engine_config(args),
        view_dir=out / "views",
        work_dir=out / "engine-work",
    )
    # A historical review describes the historical MAP, not a recompilation
    # with today's compiler/defaults. New runs start without a review.
    (out / "iteration.json").write_text(
        json.dumps(packet.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    (out / "summary.md").write_text(summarize(packet), encoding="utf-8", newline="\n")
    return packet


def prepare_run(output_root: Path, run_id: str, iterations: list[str]) -> Path:
    """Reserve a new run and preserve the Python that will produce its maps."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id):
        raise ValueError("run-id must contain only letters, digits, '-' and '_'")
    if not iterations:
        raise ValueError("a run must contain at least one iteration")
    if len(set(iterations)) != len(iterations):
        raise ValueError("each iteration may occur only once in a run")
    for iteration in iterations:
        if not re.fullmatch(r"v[0-9]+", iteration) or not (LEVEL_DIR / f"candidate_{iteration}.py").is_file():
            raise ValueError(f"unknown iteration: {iteration!r}")
    run_dir = output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    sources = sorted(Path("bloodmap").rglob("*.py")) + sorted(LEVEL_DIR.glob("*.py"))
    sources.append(Path(__file__).resolve().relative_to(Path.cwd().resolve()))
    files = []
    for path in sources:
        target = run_dir / "source" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        files.append({"path": path.as_posix(), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    try:
        revision = subprocess.run(
            ["git", "-c", f"safe.directory={Path.cwd().as_posix()}", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        )
        commit = revision.stdout.strip() if revision.returncode == 0 else None
    except OSError:
        commit = None
    (run_dir / "run.json").write_text(json.dumps({
        "run_id": run_id, "iterations": iterations,
        "git_revision": commit,
        "python": sys.version, "source_files": files,
        "status": "started", "kind": "current-source reevaluation",
        "limitations": ["No historical review is inherited.",
                        "Game assets and runtime binaries are external inputs.",
                        "A completed evaluation does not establish map quality."],
    }, indent=2) + "\n", encoding="utf-8")
    return run_dir


def record_inputs(args: argparse.Namespace) -> None:
    """Identify external evidence inputs without copying commercial game data."""
    paths = [Path(args.catalog or DEFAULT_CATALOG),
             Path(args.spatial_corpus or DEFAULT_SPATIAL_CORPUS),
             Path(args.shape_corpus or DEFAULT_SHAPE_CORPUS),
             Path(args.surface_corpus or DEFAULT_SURFACE_CORPUS)]
    art = Path(args.art_dir or DEFAULT_ART)
    paths.extend(p for p in art.glob("*") if p.suffix.lower() in {".art", ".rff"})
    if args.game_dir and Path(args.game_dir).resolve() != art.resolve():
        paths.extend(p for p in Path(args.game_dir).glob("*") if p.suffix.lower() in {".art", ".rff"})
    if args.nblood:
        paths.append(Path(args.nblood))
    from bloodmap.visual import default_binary
    paths.append(default_binary())
    path = args.run_dir / "run.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["inputs"] = [
        {"path": str(p.resolve()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None}
        for p in sorted(set(paths))
    ]
    manifest["arguments"] = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


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
    parser.add_argument("--surface-corpus", help="mined single-surface treatment corpus JSON")
    parser.add_argument("--art-dir", help="local Blood ART directory, for sprite world size")
    parser.add_argument("--grace-seconds", type=float, default=5.0)
    parser.add_argument("--startup-timeout", type=float, default=25.0)
    parser.add_argument("--settle-seconds", type=float, default=3.0)
    parser.add_argument("--comparison", action="store_true",
                        help="write comparison.json inside the new run")
    parser.add_argument("--run-id", required=True,
                        help="new immutable run label; an existing label is refused")
    parser.add_argument("--output-root", type=Path, default=Path("work/authoring-runs"))
    args = parser.parse_args(argv)

    wanted = args.iterations or [
        name for name in ITERATIONS if (LEVEL_DIR / f"candidate_{name}.py").is_file()
    ]
    try:
        args.run_dir = prepare_run(args.output_root, args.run_id, wanted)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    record_inputs(args)
    packets: list[AuthoringIteration] = []
    for iteration in wanted:
        try:
            packet = run_iteration(iteration, args)
        except Exception as error:
            (args.run_dir / "failure.json").write_text(json.dumps({
                "iteration": iteration, "error_type": type(error).__name__,
                "error": str(error), "status": "failed",
            }, indent=2) + "\n", encoding="utf-8")
            manifest_path = args.run_dir / "run.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "failed"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            raise
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
        (args.run_dir / "comparison.json").write_text(
            json.dumps(compare_iterations(packets), indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"wrote {args.run_dir / 'comparison.json'}")
    failures = any(g["status"] == "fail" for p in packets for g in p.hard_gates)
    manifest_path = args.run_dir / "run.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed = [row["path"] for row in manifest["source_files"]
               if not Path(row["path"]).is_file() or hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() != row["sha256"]]
    if changed:
        manifest["changed_during_run"] = changed
        failures = True
    manifest["status"] = "source_changed" if changed else ("failed_gates" if failures else "evaluated")
    manifest["artifacts"] = [
        {"iteration": p.identity["iteration_id"], "map_sha256": p.identity["map_sha256"],
         "packet_sha256": hashlib.sha256((args.run_dir / p.identity["iteration_id"] / "iteration.json").read_bytes()).hexdigest(),
         "gates": {g["gate_id"]: g["status"] for g in p.hard_gates}}
        for p in packets
    ]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
