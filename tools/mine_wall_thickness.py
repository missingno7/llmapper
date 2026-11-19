"""How thin a wall Blood is willing to build between two rooms.

The fault this measures against: squeezing a new part into a layout by hand
leaves whatever space is left over between it and its neighbour, and what is
left over is often four units of stone. The engine draws it happily; a player
reads it as two rooms sharing a sheet of paper.

Method
------

For every *solid* wall of a playable sector, step outward along the wall's own
normal and find the first playable sector on the other side. The distance at
which that happens is the thickness of the mass separating them, measured where
a player would actually see it -- at the wall, not between centroids.

Two things this deliberately does not count:

* **Two-sided walls.** Those are openings, not masses; their thickness is zero
  by construction and including them buries the distribution at 0.
* **The same sector coming back round.** A concave room's normal can re-enter
  the room it started in. That is one space, not two, so it is skipped.
* **Volumes that do not coexist.** A first pass put 16.8% of probes at 16 units
  and made every map's thinnest wall 16, which is not a finding about masonry --
  it is room-over-room. A stack's two halves share a footprint, so a probe out of
  the upper room's wall lands in the lower room immediately. Nothing separates
  them horizontally because nothing is meant to. Two sectors are only separated
  by a *wall* if their floor-to-ceiling ranges overlap, so that a player standing
  in one is at heights the other also occupies.

The probe walks outward in `PROBE_STEP` units to `PROBE_REACH`
(`bloodmap.layout`); anything thicker than that is not a thin-wall problem and is recorded only as "thicker than".

.. code-block:: bash

    python -m tools.mine_wall_thickness -o knowledge/blood/design/wall-thickness-v1.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import Counter
from typing import Any

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.layout import (
    PLAYER_WIDTH, PROBE_REACH, PROBE_STEP, observe_wall_thickness,
)

SCHEMA = "llmapper.blood-wall-thickness"
SCHEMA_VERSION = 1


def band(values: list[float], digits: int = 2) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}

    def at(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))]

    return {
        "min": round(ordered[0], digits),
        "p01": round(at(0.01), digits),
        "p05": round(at(0.05), digits),
        "q1": round(at(0.25), digits),
        "median": round(statistics.median(ordered), digits),
        "q3": round(at(0.75), digits),
        "max": round(ordered[-1], digits),
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    thick = [r["thickness"] for r in rows]
    histogram = Counter(min(r["thickness"], 512) // 32 * 32 for r in rows)
    # The thinnest each map is willing to go, which is the number the grammar
    # wants: one outlier in one map should not set the floor for every level.
    per_map: dict[str, int] = {}
    for row in rows:
        key = row["map"]
        if key not in per_map or row["thickness"] < per_map[key]:
            per_map[key] = row["thickness"]
    return {
        "probes": len(rows),
        "thickness": band(thick, 0),
        "thickness_player_widths": band([r["thickness_player_widths"] for r in rows]),
        "thinnest_per_map": band([float(v) for v in per_map.values()], 0),
        "histogram_to_512": {str(k): histogram[k] for k in sorted(histogram)},
        "share_under": {
            str(cut): round(sum(1 for t in thick if t < cut) / max(1, len(thick)), 5)
            for cut in (64, 128, 192, 256, 384, 512)
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", help="corpus root or a directory of maps (default: the local corpus)")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    seen = 0
    for path in campaign_maps(args.maps, required=True):
        name = path.stem.upper()
        try:
            rows.extend(observe_wall_thickness(name, read_map(path)))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
            continue
        seen += 1
        print("  %s: %d probes" % (name, len(rows)), end="\r")

    summary = summarise(rows)
    document = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "maps": seen,
        "summary": summary,
        "method": (
            "step outward from every solid wall of a playable sector along its "
            "own normal, in %d-unit steps to %d, and record the distance at "
            "which another playable sector begins. Two-sided walls are openings "
            "and are excluded; a normal that re-enters its own sector is one "
            "space and is excluded." % (PROBE_STEP, PROBE_REACH)
        ),
        "reading_guide": [
            "thickness is in Build units; one body width is %d" % PLAYER_WIDTH,
            "thinnest_per_map is the floor each map allowed itself, which is the "
            "number a minimum should be derived from -- a single outlier in one "
            "map is not a licence for every level",
            "a band is what the campaign did, never what a level must do",
        ],
    }

    s = summary
    print("%d maps, %d probes                       " % (seen, s["probes"]))
    print()
    print("wall thickness, Build units : %s" % s["thickness"])
    print("            in body widths  : %s" % s["thickness_player_widths"])
    print("thinnest wall in each map   : %s" % s["thinnest_per_map"])
    print()
    print("share of walls thinner than:")
    for cut, share in s["share_under"].items():
        print("  %4s units (%.2f body widths): %6.3f%%"
              % (cut, int(cut) / PLAYER_WIDTH, 100 * share))
    print()
    print("histogram to 512 units, in 32s:")
    for key, count in s["histogram_to_512"].items():
        print("  %4s %s %d" % (key, "#" * min(60, count // 40), count))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
        print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
