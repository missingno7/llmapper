"""How often the campaign places detail along a run.

A run is a long thin space -- a tunnel, a corridor, a quay, a fence line --
and the question a run generator has to answer is *how often*: a pipe every
how many plan units, a bracket every how many, where repetition stops.

`decoration-v1` answered the sizing question well (15 of 36 tiles are never
resized, only 5 truly scale with the room).  This asks the rhythm question
the same way: find long thin sectors, project everything attached to them
onto the long axis, and measure the gaps between consecutive items.

Derived: the spacings, the counts, the runs they came from.  Interpreted:
nothing here -- the classes a caller builds on top are its own business.

    python tools/mine_run_rhythm.py -o knowledge/blood/design/run-rhythm-v1.json
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bloodmap.format import read_map
from bloodmap.patterns import CORPUS_VIEWS, list_corpus_maps

PLAN = 1024
PLAYER = 16960
#: A run is at least this long and this much longer than it is wide.
MIN_LENGTH = 4 * PLAN
MIN_ASPECT = 2.5


def sector_box(m, index):
    s = m.sectors[index]
    pts = [(m.walls[w].x, m.walls[w].y)
           for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--view", default="reference",
                    choices=sorted(CORPUS_VIEWS),
                    help="corpus view to mine (default: reference)")
    args = ap.parse_args(argv)

    gaps = []
    per_run = []
    tiles_on_runs = collections.Counter()
    # This used to glob a flat maps/blood, which after the corpus became
    # provenance directories matched nothing at all. The population it
    # was really reading is the `reference` view -- campaign, BloodBath
    # and the curated community sets -- and that is what the committed
    # knowledge file was mined from, so it stays the default rather than
    # silently moving numbers nobody asked to move. Note that the prose
    # above says "the campaign" and the evidence is wider than that;
    # `--view original` is the honest campaign-only run.
    for path in sorted(str(item.path) for item in
                       list_corpus_maps(view=args.view)):
        name = pathlib.Path(path).stem
        try:
            m = read_map(path)
        except Exception:
            continue
        by_sector = collections.defaultdict(list)
        for sp in m.sprites:
            if sp.status == 0 and sp.type == 0 and sp.picnum > 0:
                by_sector[sp.sector].append(sp)
        for index in range(len(m.sectors)):
            if m.sectors[index].wall_count < 4:
                continue
            x0, y0, x1, y1 = sector_box(m, index)
            width, depth = x1 - x0, y1 - y0
            length, across = max(width, depth), max(1, min(width, depth))
            if length < MIN_LENGTH or length / across < MIN_ASPECT:
                continue
            horizontal = width >= depth
            items = sorted((sp.x if horizontal else sp.y)
                           for sp in by_sector.get(index, []))
            for sp in by_sector.get(index, []):
                tiles_on_runs[sp.picnum] += 1
            if len(items) >= 2:
                run_gaps = [(b - a) / PLAN for a, b in zip(items, items[1:])
                            if b > a]
                gaps += run_gaps
                per_run.append({"map": name, "sector": index,
                                "length_plan": round(length / PLAN, 2),
                                "items": len(items),
                                "per_plan_unit": round(len(items) / (length / PLAN), 3)})
    gaps.sort()

    def q(v, p):
        return round(v[min(len(v) - 1, int(len(v) * p))], 2)

    density = sorted(r["per_plan_unit"] for r in per_run)
    report = {
        "$schema": "llmapper.run-rhythm",
        "schema_version": 1,
        "note": ("Derived. A run is a sector at least 4 plan units long and "
                 "2.5x longer than wide; gaps are between consecutive items "
                 "projected on the long axis."),
        "runs_examined": len(per_run),
        "gaps_measured": len(gaps),
        "gap_plan_units": {"p10": q(gaps, .1), "q1": q(gaps, .25),
                           "median": round(statistics.median(gaps), 2),
                           "q3": q(gaps, .75), "p90": q(gaps, .9)},
        "items_per_plan_unit": {"p10": q(density, .1),
                                "median": round(statistics.median(density), 3),
                                "q3": q(density, .75), "p90": q(density, .9)},
        "tiles_seen_on_runs": tiles_on_runs.most_common(30),
        "longest_runs": sorted(per_run, key=lambda r: -r["length_plan"])[:15],
    }
    pathlib.Path(args.output).write_text(json.dumps(report, indent=1),
                                         encoding="utf-8")
    print(f"wrote {args.output}: {len(per_run)} runs, {len(gaps)} gaps")
    print(f"  gap between items (plan units): {report['gap_plan_units']}")
    print(f"  items per plan unit: {report['items_per_plan_unit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
