"""Capture rendered frames from an original map, so visual claims have evidence.

The authoring loop can already look at a generated candidate.  It had no way to
look at an original, which meant every visual comparison with the corpus was
being made from memory.  This tool closes that: it places the camera inside
named sectors of an original MAP and preserves one PNG per pose, using the same
pose-only variant rule the candidate captures use.

    python -m tools.render_precedent maps/blood/E2M3.MAP \\
        --sectors 105,41,37,44 --nblood reference/blood/nblood.exe \\
        --game-dir reference/blood -o work/precedent-views/E2M3

A captured frame is evidence about how the engine draws that map with the local
game data.  It is not evidence about design intent, and an image hash of it
proves stability and nothing else.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any

from bloodmap.format import encode_map, read_map, write_map
from bloodmap.oracle import run_nblood_viewpoint_capture
from bloodmap.viewpoints import ViewpointSpec, prepare_viewpoints, viewpoint_manifest
from bloodmap.viewpoints import _sector_loops


def _pose(level, sector_id: int) -> tuple[int, int, int]:
    """A point inside the sector, at eye level above its floor."""
    loops = _sector_loops(level, sector_id)
    outer = loops[0]
    x = sum(point[0] for point in outer) / len(outer)
    y = sum(point[1] for point in outer) / len(outer)
    from bloodmap.viewpoints import _contains

    candidate = (int(round(x)), int(round(y)))
    if not _contains(level, sector_id, *candidate):
        # A concave or holed sector may not contain its own vertex average; fall
        # back to a point just inside the first edge.
        ax, ay = outer[0]
        bx, by = outer[1 % len(outer)]
        candidate = (int(round((ax + bx) / 2 + (by - ay) * 0.02)),
                     int(round((ay + by) / 2 - (bx - ax) * 0.02)))
        if not _contains(level, sector_id, *candidate):
            raise SystemExit(f"cannot find an interior pose for sector:{sector_id}")
    fields = level.sectors[sector_id]["fields"]
    floor_z, ceiling_z = int(fields["floor_z"]), int(fields["ceiling_z"])
    z = max(ceiling_z, floor_z - 0x1600)
    return (candidate[0], candidate[1], z)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--sectors", required=True, help="comma-separated sector ids")
    parser.add_argument("--angles", default="0", help="comma-separated build angles, cycled")
    parser.add_argument("--pitch", type=int, default=0,
                        help="Aim_Up taps before the shot; negative aims down")
    parser.add_argument("--nblood", required=True)
    parser.add_argument("--game-dir", required=True)
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--grace-seconds", type=float, default=14.0)
    parser.add_argument("--startup-timeout", type=float, default=45.0)
    parser.add_argument("--settle-seconds", type=float, default=3.0)
    args = parser.parse_args(argv)

    path = pathlib.Path(args.map)
    level = read_map(path).to_level_ir()
    sector_ids = [int(value) for value in args.sectors.split(",") if value.strip()]
    angles = [int(value) for value in args.angles.split(",") if value.strip()] or [0]

    specs: list[ViewpointSpec] = []
    allocations: dict[str, int] = {}
    for index, sector_id in enumerate(sector_ids):
        x, y, z = _pose(level, sector_id)
        region = f"sector:{sector_id}"
        allocations[region] = sector_id
        specs.append(ViewpointSpec(
            viewpoint_id=f"view:{path.stem.lower()}_sector_{sector_id}",
            purpose="assembly_center", region_id=region,
            x=x, y=y, z=z, angle=angles[index % len(angles)],
            note=f"original {path.stem} sector {sector_id}",
        ))

    payload = encode_map(level.to_disk_map())
    manifest = viewpoint_manifest(
        level, specs, allocations=allocations,
        map_sha256=hashlib.sha256(payload).hexdigest(),
    )
    out_dir = pathlib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    variant_dir = out_dir / "variants"
    variant_dir.mkdir(parents=True, exist_ok=True)
    requests = []
    for item in prepare_viewpoints(level, specs, allocations=allocations):
        identifier = item["resolved"]["viewpoint_id"]
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in identifier)
        variant_path = variant_dir / f"{safe}.MAP"
        write_map(item["level"].to_disk_map(), variant_path)
        requests.append({
            "viewpoint_id": identifier, "map": str(variant_path),
            "resolved": item["resolved"], "variant_diff": item["diff"],
            "pitch_taps": args.pitch,
        })
    captures = run_nblood_viewpoint_capture(
        requests, nblood=args.nblood, game_dir=args.game_dir,
        image_dir=out_dir, startup_timeout=args.startup_timeout,
        settle_seconds=args.settle_seconds,
    )
    document: dict[str, Any] = {
        "$schema": "llmapper.precedent-views",
        "of": path.name,
        "source_crc32": level.metadata.get("source_crc32"),
        "manifest": manifest,
        "captures": captures,
        "limitations": [
            "a frame shows how this engine and this game data draw the map, not intent",
            "image hashes prove stability, never visual quality",
        ],
    }
    (out_dir / "precedent-views.json").write_text(json.dumps(document, indent=1, default=str), encoding="utf-8")
    print(json.dumps({
        "status": captures.get("status"),
        "views": len(captures.get("views") or []),
        "image_dir": str(out_dir),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
