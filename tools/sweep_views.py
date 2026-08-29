"""Stand everywhere in a map, look every way, and record what was drawn.

.. code-block:: bash

    python -m tools.sweep_views maps/blood/BB4.MAP -o work/sweep/bb4

The overlap-visibility validator can *prove* two sectors are never co-rendered,
but where it cannot prove it the answer is not "unsafe" -- it is "not proved".
Telling those apart needs the renderer's own answer, and the XMapEdit observer
gives it: every surface it drew, the sector it belongs to, and its screen box.

So this stands on a grid in every sector a body could stand in, turns all the
way round at each point, and writes one manifest. `tools.render_conflicts` then
asks which of those frames actually holds two sectors the renderer cannot order.

No facing direction is privileged, because none can be: `scansector` collects a
neighbour regardless of view direction whenever the viewer is within 16 units of
its wall's plane (engine.cpp:1863).
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bloodmap.format import read_map
from bloodmap.viewplan import eye_z, interior_point
from bloodmap.viewpoints import _contains, _sector_loops
from bloodmap.visual import ObservationRequest, Viewpoint, run_observation


def sweep_poses(level, *, step: int = 1024, angles: int = 8,
                limit: int = 4000) -> list[Viewpoint]:
    out: list[Viewpoint] = []
    for sector_id in range(len(level.sectors)):
        z = eye_z(level, sector_id)
        if z is None:
            continue
        loops = _sector_loops(level, sector_id)
        if not loops:
            continue
        xs = [p[0] for p in loops[0]]
        ys = [p[1] for p in loops[0]]
        points = [(x, y)
                  for x in range(min(xs) + step // 2, max(xs), step)
                  for y in range(min(ys) + step // 2, max(ys), step)
                  if _contains(level, sector_id, x, y)]
        if not points:
            point = interior_point(level, sector_id)
            if point is None:
                continue
            points = [point]
        for px, py in points:
            for turn in range(angles):
                out.append(Viewpoint(
                    view_id=f"s{sector_id}_{px}_{py}_a{turn}",
                    x=px, y=py, z=z, angle=(turn * 2048) // angles,
                    horiz=100, sector=sector_id, node=f"sweep:{sector_id}",
                    purpose="sweep", screenshot=False,
                    note=f"sector {sector_id} at ({px}, {py})"))
                if len(out) >= limit:
                    return out
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("-o", "--out", required=True)
    parser.add_argument("--step", type=int, default=1024)
    parser.add_argument("--angles", type=int, default=8)
    parser.add_argument("--limit", type=int, default=4000)
    parser.add_argument("--timeout", type=float, default=7200,
                        help="seconds the observer may take for the whole batch")
    args = parser.parse_args(argv)

    root = pathlib.Path(__file__).resolve().parent.parent
    level = read_map(args.map).to_level_ir()
    views = sweep_poses(level, step=args.step, angles=args.angles,
                        limit=args.limit)
    if not views:
        print("no standing points resolved")
        return 1
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_observation(ObservationRequest(
        map_path=args.map, output_dir=str(out_dir),
        resource_dir=str(root / "reference" / "blood"), viewpoints=tuple(views),
        width=640, height=480, screenshots=False, brightness=0, rff=None),
        timeout=args.timeout)
    print(f"{len(views)} views -> {out_dir}")
    print(f"now: python -m tools.render_conflicts {args.map} "
          f"{out_dir / 'observation.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
