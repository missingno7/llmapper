"""Observe an original map, so claims about the corpus have evidence.

The authoring loop can look at a generated candidate.  It had no way to look at
an original, which meant every comparison with the corpus was being made from
memory.  This closes that.

    python -m tools.render_precedent maps/blood/E2M3.MAP \\
        --sectors 105,41,37,44 --resource-dir reference/blood \\
        -o work/precedent-views/E2M3

This used to drive NBlood: launch the game, focus its window, inject keys, hope
a screenshot landed.  The frames it produced were contaminated by the thing
producing them -- a pain flash, a cultist walking into shot, the automap left
toggled on -- and none of it was reproducible.  It now goes through the
XMapEdit observer instead, which takes a pose as a number and answers with what
the renderer painted.  JSON is the product; a frame is written only for the
poses asked for with ``--screenshot``.

What comes back is evidence about how the editor renderer draws that map with
the local game data.  It is not evidence about design intent, and an image hash
of it proves stability and nothing else.
"""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
from typing import Any

from bloodmap.format import read_map, write_map
from bloodmap.blood_types import classify
from bloodmap.viewplan import angle_toward, eye_z, interior_point
from bloodmap.visual import (
    ObservationRequest,
    SourceMap,
    Viewpoint,
    compact_summary,
    join_view,
    run_observation,
)
from bloodmap.viewpoints import _sector_loops


def _pose(level, sector_id: int, angle: int | None) -> Viewpoint | None:
    """A point that is really inside the sector, at eye level above its floor."""
    point = interior_point(level, sector_id)
    if point is None:
        return None
    z = eye_z(level, sector_id)
    if z is None:
        return None
    if angle is None:
        # Face the farthest vertex of the sector, which is the longest thing
        # there is to look at inside it.
        outer = _sector_loops(level, sector_id)[0]
        far = max(outer, key=lambda p: (p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2)
        angle = angle_toward(point, far)
    return Viewpoint(
        view_id="sector_%d" % sector_id, x=point[0], y=point[1], z=z,
        angle=int(angle) & 2047, sector=sector_id,
        node="sector:%d" % sector_id, purpose="precedent",
        note="original %s sector %d" % ("", sector_id),
    )


def _architecture_only_map(map_path: pathlib.Path, out: pathlib.Path) -> tuple[pathlib.Path, int]:
    """Write a renderer-only copy with non-player actor sprites hidden.

    The observer loads a MAP, so a view cannot merely ask it to omit a sprite
    after it has already drawn and occluded geometry.  Keep every record and
    index intact, but give classified ``dude`` sprites no drawn size.  This
    leaves portals, triggers and all non-actor decoration untouched while
    making a reference frame about the level's architecture rather than its
    encounter population.
    """
    disk = copy.deepcopy(read_map(map_path))
    hidden = 0
    for sprite in disk.sprites:
        fields = sprite.fields
        type_id = int(fields.get("type", 0))
        # Player starts are useful orientation evidence and do not clutter a
        # scene; all other classified actors are encounter population.
        if classify("sprite", type_id).get("category") != "dude" or 231 <= type_id <= 238:
            continue
        fields["x_repeat"] = 0
        fields["y_repeat"] = 0
        hidden += 1
    filtered = out / "architecture-only.MAP"
    write_map(disk, filtered)
    return filtered, hidden


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--sectors", required=True,
                        help="comma-separated sector ids to stand in")
    parser.add_argument("--angle", type=int, default=None,
                        help="a fixed Build angle for every pose; omitted means face "
                             "the farthest corner of each sector")
    parser.add_argument("--horiz", type=int, default=100,
                        help="Build horizon: 100 is level, above looks up")
    parser.add_argument("--resource-dir", default="reference/blood")
    parser.add_argument("--binary", default=None)
    parser.add_argument("--screenshot", action="append", default=[],
                        help="sector ids to write a frame for; repeatable")
    parser.add_argument("--brightness", type=int, default=0)
    parser.add_argument("--hide-dudes", action="store_true",
                        help="render a temporary architecture-only copy without non-player actors")
    parser.add_argument("-o", "--out", required=True)
    args = parser.parse_args(argv)

    map_path = pathlib.Path(args.map)
    level = read_map(map_path).to_level_ir()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    observed_map = map_path
    hidden_dudes = 0
    if args.hide_dudes:
        observed_map, hidden_dudes = _architecture_only_map(map_path, out)

    wanted = [int(item) for item in args.sectors.split(",") if item.strip()]
    views: list[Viewpoint] = []
    refused: list[dict[str, Any]] = []
    for sector_id in wanted:
        if not 0 <= sector_id < len(level.sectors):
            refused.append({"sector": sector_id, "reason": "no such sector in this map"})
            continue
        pose = _pose(level, sector_id, args.angle)
        if pose is None:
            refused.append({"sector": sector_id,
                            "reason": "no interior point with standing clearance"})
            continue
        views.append(pose if args.horiz == 100 else
                     Viewpoint(**{**pose.__dict__, "horiz": args.horiz}))
    if not views:
        parser.error("no usable pose among the requested sectors")

    shots = {"sector_%s" % item for item in args.screenshot}
    request = ObservationRequest(
        map_path=str(observed_map), output_dir=str(out / "observation"),
        resource_dir=args.resource_dir, viewpoints=tuple(views),
        brightness=args.brightness,
    )
    if shots:
        request = request.with_screenshots(shots)
    manifest = run_observation(request, binary=args.binary)

    # An original has no authored source, so a sector is its own node.  The
    # names stay native on purpose: inventing one here would be interpretation
    # presented as measurement.
    from bloodmap.visual import NodeAllocation

    source_map = SourceMap([
        NodeAllocation("sector:%d" % int(sector["id"]), ("sector:%d" % int(sector["id"]),),
                       "space", frozenset({int(sector["id"])}))
        for sector in level.sectors
    ])

    records: list[dict[str, Any]] = []
    summaries: list[str] = []
    plan = {view.view_id: view for view in views}
    for view in manifest.views:
        join = join_view(view, source_map, level=level)
        records.append({
            "view_id": view.get("id"), "status": view.get("status"),
            "reason": view.get("reason", ""), "camera": view.get("camera", {}),
            "frame": view.get("frame", {}), "screenshot": view.get("screenshot"),
            "visible": join.get("visible", []),
        })
        summaries.append(compact_summary(view, join, viewpoint=plan.get(view.get("id", ""))))

    document = {
        "$schema": "llmapper.precedent-observation",
        "schema_version": 1,
        "of": map_path.name,
        "rendered_map": observed_map.name,
        "hidden_dudes": hidden_dudes,
        "source_crc32": "%08x" % read_map(map_path).source_crc32,
        "renderer": manifest.data.get("renderer", {}),
        "timing_ms": manifest.timing,
        "requested_sectors": wanted,
        "refused": refused,
        "views": records,
        "limitations": manifest.limitations + [
            "a sector is its own node here; an original has no authored source to join to",
        ],
    }
    (out / "precedent-observation.json").write_text(
        json.dumps(document, indent=1) + "\n", encoding="utf-8")
    (out / "summary.txt").write_text("\n\n".join(summaries) + "\n", encoding="utf-8")
    print(json.dumps({
        "views": len(records),
        "refused": refused,
        "frames": [r["screenshot"] for r in records if r["screenshot"]],
        "out": str(out),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
