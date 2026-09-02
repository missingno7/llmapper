"""The three censuses of decisions section 30, over the 43 campaign maps.

    PYTHONPATH=".;projects/campaign-census/source" \
        python projects/campaign-census/source/three_censuses.py

28b end-wall tiles by join pair, 28d u-continuity by bend class, 28e
interior|interior pairs by floor and ceiling kind. Plus the shade-step
envelope of item 29a, under BOTH network definitions, because the answer
moves with the definition and the writer's gate has to name which it means.

Nothing is added to `joins.ROWS`. The indoor rows are PROPOSED, with the share
and the number of maps behind each, and P14b decides.
"""

from __future__ import annotations

import json
from collections import Counter

from _common import PROJECT, art_sizes, campaign, levels, write

from bloodmap.read_census import census, proposed_indoor_rows
from bloodmap.read_light import NETWORKS, shade_step_envelope
from bloodmap.read_store import FactStore


def main() -> int:
    sizes = art_sizes()
    names, worlds = [], []
    for name, level in levels():
        names.append(name)
        worlds.append(level)
    print(f"campaign: {len(worlds)} maps")

    summary = census(worlds, names=names, art_sizes=sizes)
    rows = proposed_indoor_rows(summary)
    envelopes = {which: shade_step_envelope(worlds, network=which, names=names)
                 for which in NETWORKS}

    write("three-censuses.json", {
        "population": "blood-campaign",
        "maps": summary["maps"],
        "end_wall_tiles": summary["end_wall_tiles"],
        "u_continuity": summary["u_continuity"],
        "interior_pairs": summary["interior_pairs"],
        "proposed_indoor_rows": rows,
        "per_map": summary["per_map"],
    })
    write("shade-step-envelope.json", envelopes)

    store = FactStore()
    _facts(store, summary, rows, envelopes)
    written = store.write(PROJECT / "facts")
    print(f"facts: {sum(written.values())} rows in {len(written)} predicates")

    _print(summary, rows, envelopes)
    return 0


def _facts(store, summary, rows, envelopes) -> None:
    """The census as facts, in the reader's frozen row shape.

    New predicates, each declared with a description in `read_store`: the row
    shape is untouched, which is the constraint this slice runs under while
    P14b re-shapes the compiler's store onto it.
    """
    for pair, tiles in summary["end_wall_tiles"]["tiles"].items():
        store.add("census_band", f"end_wall:{pair}",
                  {"pair": pair, "tiles": tiles,
                   "blocking": summary["end_wall_tiles"]["blocking"].get(pair, {}),
                   "step_by_blocking":
                       summary["end_wall_tiles"]["step_by_blocking"].get(pair, {}),
                   "maps": summary["end_wall_tiles"]["maps_with_the_pair"].get(pair, 0),
                   "population": "blood-campaign"},
                  reader="bloodmap.read_census.end_wall_tiles")
    for name, row in summary["u_continuity"].items():
        store.add("census_continuity", f"bend:{name.replace(' ', '_')}",
                  {"join_class": name, **row, "population": "blood-campaign"},
                  reader="bloodmap.read_census.u_continuity")
    classes = summary["interior_pairs"]["classes"]
    maps = summary["interior_pairs"]["maps_with_the_class"]
    for key, count in classes.items():
        store.add("census_pair", f"interior:{key.replace(' ', '_')}",
                  {"pair_class": key, "records": count,
                   "maps": maps.get(key, 0),
                   "draws": summary["interior_pairs"]["draws"].get(key, {}),
                   "population": "blood-campaign"},
                  reader="bloodmap.read_census.interior_pairs")
    for row in rows:
        store.add("proposed_row", f"indoor:{row['proposed_row'].replace(' ', '_')}",
                  {**row, "state": "PROPOSED, never added to joins.ROWS"},
                  reader="bloodmap.read_census.proposed_indoor_rows")
    for which, row in envelopes.items():
        store.add("census_envelope", f"shade_step:{which}",
                  {"network": which, "envelope": row["envelope"],
                   "maps": row["maps"],
                   "maps_with_a_boundary": row["maps_with_a_boundary"],
                   "current_gate": row["current_gate"],
                   "population": "blood-campaign"},
                  reader="bloodmap.read_light.shade_step_envelope")


def _print(summary, rows, envelopes) -> None:
    print("\n28b -- what a termination's band wears, by join pair")
    for pair, tiles in summary["end_wall_tiles"]["tiles"].items():
        total = sum(tiles.values())
        top = list(tiles.items())[:6]
        print(f"  {pair:22s} {total:5d} records over "
              f"{summary['end_wall_tiles']['maps_with_the_pair'][pair]} maps; "
              f"top tiles {top}")
        print(f"  {'':22s} blocking "
              f"{summary['end_wall_tiles']['blocking'][pair]}")
        step = summary["end_wall_tiles"]["step_by_blocking"].get(pair, {})
        for state, spread in step.items():
            if spread.get("n"):
                print(f"  {'':22s} {state:14s} step median "
                      f"{spread['median']:8d}  q1 {spread['q1']:8d}  q3 "
                      f"{spread['q3']:8d}  (n={spread['n']})")
    print(f"  the writer's class: facade stone = "
          f"{summary['end_wall_tiles']['the_writers_class']['facade stone']}")

    print("\n28d -- where a material stops, by bend class")
    for name, row in summary["u_continuity"].items():
        print(f"  {name:26s} {row['u_continues']:6d}/{row['n']:6d} "
              f"{row['percent']:5.1f}%   over {row['maps']} maps")

    print("\n28e -- interior meeting interior, by what the surfaces do")
    total = sum(summary["interior_pairs"]["classes"].values())
    for key, count in list(summary["interior_pairs"]["classes"].items())[:12]:
        share = 100.0 * count / total
        print(f"  {key:44s} {count:6d} {share:5.1f}%  "
              f"{summary['interior_pairs']['maps_with_the_class'][key]} maps")
    print(f"  {len(summary['interior_pairs']['classes'])} classes over "
          f"{total} records; {len(rows)} would earn a proposed row")

    print("\n29a -- the shade step, by network definition")
    for which, row in envelopes.items():
        env = row["envelope"]
        gate = row["current_gate"]
        print(f"  {which:28s} n={env.get('n', 0):5d} over "
              f"{row['maps_with_a_boundary']} maps  "
              f"median {env.get('median')}  q1 {env.get('q1')} q3 "
              f"{env.get('q3')}  mean {env.get('mean')}")
        print(f"  {'':28s} the gate's {gate['interval']} holds "
              f"{gate['boundaries_inside']} of {env.get('n', 0)} "
              f"({gate['percent_inside']}%)")


if __name__ == "__main__":
    raise SystemExit(main())
