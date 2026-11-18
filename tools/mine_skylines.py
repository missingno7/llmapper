"""How the campaign makes a building look tall: the two techniques, counted.

    python -m tools.mine_skylines -o work/skylines.json

For every original map, over its sectors open to the sky:

* `sky_steps`        portals between two open sectors whose ceilings differ by
                     a body or more -- the stepped sky `bloodmap.skyline` uses
* `raised_floors`    one-sided-wall heights that differ because the FLOOR
                     differs under one sky -- the roof-sector technique
* `wall_heights`     the heights one-sided walls are drawn to, in bodies
* `sloped_sky`       open sectors whose parallax ceiling carries a slope

DERIVED, all of it: read from sector and wall fields.  Which technique a
mapper "meant" is an interpretation and is not made here.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap.format import read_map
from bloodmap.patterns import list_original_maps

BODY = 16960


def measure(disk) -> dict:
    sectors = [s.fields for s in disk.sectors]
    walls = [w.fields for w in disk.walls]
    sky = [i for i, s in enumerate(sectors) if int(s["ceiling_stat"]) & 1]
    steps, heights = [], Counter()
    ceilings, floors = set(), set()
    sloped = 0
    for index in sky:
        s = sectors[index]
        ceiling, floor = int(s["ceiling_z"]), int(s["floor_z"])
        if int(s["ceiling_stat"]) & 2 and int(s["ceiling_heinum"]):
            sloped += 1
        solid = 0
        for wall_id in range(int(s["wall_ptr"]),
                             int(s["wall_ptr"]) + int(s["wall_count"])):
            other = int(walls[wall_id]["next_sector"])
            if other < 0:
                solid += 1
            elif (0 <= other < len(sectors) and index < other
                  and int(sectors[other]["ceiling_stat"]) & 1):
                gap = abs(int(sectors[other]["ceiling_z"]) - ceiling)
                if gap >= BODY:
                    steps.append(round(gap / BODY, 1))
        if solid:
            heights[round((floor - ceiling) / BODY)] += solid
            ceilings.add(ceiling)
            floors.add(floor)
    steps.sort()
    return {
        "sky_sectors": len(sky),
        "sky_steps": len(steps),
        "sky_step_median_bodies": steps[len(steps) // 2] if steps else None,
        "sky_step_max_bodies": steps[-1] if steps else None,
        "distinct_sky_ceilings_over_walls": len(ceilings),
        "distinct_floors_under_walls": len(floors),
        "distinct_wall_heights_bodies": len(heights),
        "wall_heights_bodies": {str(k): v for k, v in sorted(heights.items())},
        "sloped_sky": sloped,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out", default=None)
    parser.add_argument("--population", default="blood-campaign")
    args = parser.parse_args(argv)
    per_map = {}
    for path in list_original_maps(population=args.population):
        try:
            per_map[path.stem.upper()] = measure(read_map(path))
        except Exception as error:      # a map that will not read is reported
            per_map[path.stem.upper()] = {"error": str(error)}
    good = {k: v for k, v in per_map.items() if "error" not in v
            and v["sky_sectors"]}
    summary = {
        "maps": len(per_map), "maps_with_open_sky": len(good),
        "maps_with_a_stepped_sky": sum(1 for v in good.values() if v["sky_steps"]),
        "sky_steps": sum(v["sky_steps"] for v in good.values()),
        "maps_with_three_or_more_wall_heights":
            sum(1 for v in good.values() if v["distinct_wall_heights_bodies"] >= 3),
        "maps_with_one_wall_height":
            sum(1 for v in good.values() if v["distinct_wall_heights_bodies"] == 1),
        "maps_with_a_sloped_sky": sum(1 for v in good.values() if v["sloped_sky"]),
        "sloped_sky_sectors": sum(v["sloped_sky"] for v in good.values()),
    }
    out = {"$schema": "llmapper.skyline-mine", "schema_version": 1,
           "population": args.population,
           "summary": summary, "per_map": per_map}
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(out, indent=1) + "\n", "utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
