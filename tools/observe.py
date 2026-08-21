"""Plan viewpoints, run the XMapEdit observer, and write a source-linked packet.

Two ways in, one packet out:

.. code-block:: bash

    python -m tools.observe program experiments.nested_authoring -o work/obs-nested
    python -m tools.observe decompiled maps/blood/E2M3.MAP \
        --hierarchy projects/e2m3-decompiled/hierarchy.json -o work/obs-e2m3

``program`` takes a module with ``build_level() -> LevelProgram``, compiles it,
and uses the compiler's own allocations for the join.  ``decompiled`` takes an
original MAP and a recovered hierarchy and uses that instead.  From there the
two paths are identical, which is the point: an original and a generated level
are read the same way.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any, Sequence

from bloodmap.format import read_map, write_map
from bloodmap.model import LevelIR
from bloodmap.viewplan import (
    plan_connection_views,
    plan_level_views,
    plan_node_views,
    plan_structure_views,
)
from bloodmap.visual import (
    ObservationRequest,
    SourceMap,
    Viewpoint,
    compact_summary,
    covisibility,
    join_view,
    run_observation,
)

PACKET_SCHEMA = "llmapper.visual-observation-packet"
PACKET_SCHEMA_VERSION = 1


def replay_viewpoints(packet_path: Path) -> list[Viewpoint]:
    """Re-use an earlier packet's exact cameras.

    A plan is derived from geometry, so an edit that moves geometry moves the
    camera too, and a before/after read of a planned view can be comparing two
    different questions.  Replaying pins the pose so the only thing that
    changed is the level.
    """
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    views: list[Viewpoint] = []
    for view in packet.get("views", []):
        camera = view.get("camera", {})
        if view.get("status") != "ok":
            continue
        views.append(Viewpoint(
            view_id=str(view["id"]),
            x=int(camera["x"]), y=int(camera["y"]), z=int(camera["z"]),
            angle=int(camera.get("angle", 0)), horiz=int(camera.get("horiz", 100)),
            sector=int(camera["sector"]) if camera.get("sector") is not None else None,
            node=str(view.get("node", "")), purpose=str(view.get("purpose", "")),
            note="replayed from " + str(packet_path).replace("\\", "/"),
        ))
    return views


def _children_by_parent(source_map: SourceMap) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for record in source_map.allocations.values():
        if "/" not in record.node:
            continue
        parent = record.node.rsplit("/", 1)[0]
        if parent in source_map.allocations:
            result.setdefault(parent, []).append(record.node)
    return {key: sorted(value) for key, value in result.items()}


def plan_for(level: LevelIR, source_map: SourceMap, *, nodes: Sequence[str] | None,
             per_node: Sequence[str], structures: bool, limit: int | None) -> list[Viewpoint]:
    children = _children_by_parent(source_map)
    room_kinds = {"room", "space"}
    chosen = list(nodes) if nodes else sorted(
        record.node for record in source_map.allocations.values()
        if record.kind in room_kinds
    )
    views = plan_level_views(
        level, source_map, nodes=chosen, include=per_node,
        children_of=children, limit=limit,
    )
    if structures:
        for record in sorted(source_map.allocations.values(), key=lambda r: r.node):
            if record.kind in {"staircase", "stepped_run"}:
                views.extend(plan_structure_views(level, source_map, record.node))
    seen: set[str] = set()
    unique: list[Viewpoint] = []
    for view in views:
        if view.view_id in seen:
            continue
        seen.add(view.view_id)
        unique.append(view)
    return unique


def observe(level: LevelIR, source_map: SourceMap, map_path: Path, out_dir: Path, *,
            viewpoints: Sequence[Viewpoint], resource_dir: str, screenshots: Sequence[str],
            binary: str | None, width: int, height: int, brightness: int) -> dict[str, Any]:
    request = ObservationRequest(
        map_path=str(map_path), output_dir=str(out_dir / "observation"),
        resource_dir=resource_dir, viewpoints=tuple(viewpoints),
        width=width, height=height, brightness=brightness,
    )
    if screenshots:
        request = request.with_screenshots(screenshots)
    manifest = run_observation(request, binary=binary)

    plan = {view.view_id: view for view in viewpoints}
    views: list[dict[str, Any]] = []
    summaries: list[str] = []
    for view in manifest.views:
        join = join_view(view, source_map, level=level)
        viewpoint = plan.get(view.get("id", ""))
        views.append({
            "id": view.get("id"),
            "node": viewpoint.node if viewpoint else "",
            "purpose": viewpoint.purpose if viewpoint else "",
            "note": viewpoint.note if viewpoint else "",
            "camera": view.get("camera", {}),
            "status": view.get("status"),
            "reason": view.get("reason", ""),
            "frame": view.get("frame", {}),
            "screenshot": view.get("screenshot"),
            "join": join,
            "native": {
                "surfaces": len(view.get("surfaces", [])),
                "occluded": len(view.get("occluded", [])),
            },
        })
        summaries.append(compact_summary(view, join, viewpoint=viewpoint))

    packet = {
        "$schema": PACKET_SCHEMA,
        "schema_version": PACKET_SCHEMA_VERSION,
        "map": str(map_path).replace("\\", "/"),
        "renderer": manifest.data.get("renderer", {}),
        "timing_ms": manifest.timing,
        "view_count": len(views),
        "invalid_poses": [
            {"id": view["id"], "reason": view["reason"]}
            for view in views if view["status"] != "ok"
        ],
        "views": views,
        "covisibility": covisibility(manifest, source_map),
        "limitations": manifest.limitations + [
            "poses come from a deterministic plan, so a place is observed from a "
            "handful of positions rather than from everywhere in it",
            "a hole's walls belong to the host sector in Build, so an embedded "
            "building's exterior faces are attributed to the space around it",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "packet.json").write_text(json.dumps(packet, indent=1) + "\n", encoding="utf-8")
    (out_dir / "summary.txt").write_text("\n\n".join(summaries) + "\n", encoding="utf-8")
    (out_dir / "allocation.json").write_text(
        json.dumps(source_map.to_dict(), indent=1) + "\n", encoding="utf-8")
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("program", "decompiled"))
    parser.add_argument("target", help="a module with build_level(), or a MAP path")
    parser.add_argument("-o", "--out", required=True)
    parser.add_argument("--hierarchy", help="decompiled mode: the recovered hierarchy JSON")
    parser.add_argument("--resource-dir", default="reference/blood")
    parser.add_argument("--binary", default=None)
    parser.add_argument("--map-out", default=None,
                        help="program mode: where to write the compiled MAP")
    parser.add_argument("--node", action="append", default=[],
                        help="restrict the plan to these nodes; repeatable")
    parser.add_argument("--purpose", action="append", default=[],
                        help="which per-node purposes to plan; repeatable")
    parser.add_argument("--structures", action="store_true",
                        help="also plan foot and head views for vertical runs")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--replay", default=None,
                        help="reuse the exact cameras from an earlier packet.json")
    parser.add_argument("--screenshot", action="append", default=[],
                        help="view ids to render a frame for; repeatable")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--brightness", type=int, default=0)
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "program":
        module = importlib.import_module(args.target)
        program = module.build_level()
        compiled = program.compile().compile()
        level = compiled.level
        map_path = Path(args.map_out or (out_dir / "level.MAP"))
        map_path.parent.mkdir(parents=True, exist_ok=True)
        write_map(level.to_disk_map(), map_path)
        source_map = SourceMap.from_level_program(program, compiled)
    else:
        map_path = Path(args.target)
        level = read_map(map_path).to_level_ir()
        if not args.hierarchy:
            parser.error("decompiled mode needs --hierarchy")
        hierarchy = json.loads(Path(args.hierarchy).read_text(encoding="utf-8"))
        source_map = SourceMap.from_hierarchy(hierarchy, level)

    if args.replay:
        viewpoints = replay_viewpoints(Path(args.replay))
    else:
        purposes = tuple(args.purpose) or ("room_center", "room_entry", "toward_child")
        viewpoints = plan_for(
            level, source_map, nodes=args.node or None, per_node=purposes,
            structures=args.structures, limit=args.limit,
        )
    if not viewpoints:
        parser.error("the plan produced no valid poses")

    packet = observe(
        level, source_map, map_path, out_dir, viewpoints=viewpoints,
        resource_dir=args.resource_dir, screenshots=args.screenshot,
        binary=args.binary, width=args.width, height=args.height,
        brightness=args.brightness,
    )
    print(json.dumps({
        "views": packet["view_count"],
        "invalid_poses": len(packet["invalid_poses"]),
        "timing_ms": packet["timing_ms"],
        "out": str(out_dir),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
