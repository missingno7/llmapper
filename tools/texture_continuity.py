"""Does a texture continue across a vertex, class by class, by the editor's law.

The question is not "are the textures aligned" -- that has no answer -- but
"of the joins where a material meets itself, which ones continue, and does a
built map continue the same classes the campaign does". The test for one join
is `AlignWalls` (`xmapedit/src_blood/xmpmaped.cpp:3024-3050`) read as a
predicate rather than as an assignment:

    x continues  iff  x_panning[b] == (x_panning[a] + x_repeat[a]*8) % tilesizx
    y continues  iff  y_repeat[b] == y_repeat[a]
                 and  y_panning[b] == (y_panning[a]
                                       + (zpeg[b]-zpeg[a])*y_repeat[a]
                                         / (tilesizy*8)) % 256

Both halves are counted separately because they fail for different reasons:
x breaks when a run is restarted at a vertex, y when each wall is anchored to
its own sector's height instead of to the run.

The classes matter because the campaign does not continue everything. A reflex
corner is an outside edge and the mappers stop there a quarter of the time; a
join between two portal walls is two step bands whose extents depend on the
neighbours. Those are deliberate restarts and a gate that "fixes" them would be
making built maps *less* like the campaign, which is why the rule this feeds
only fires when a built map falls well below the campaign in a class the
campaign itself continues.

.. code-block:: bash

    python -m tools.texture_continuity
    python -m tools.texture_continuity --map projects/pattern-zoo/level/pattern-zoo.MAP
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bloodmap.format import read_map                             # noqa: E402
from bloodmap.patterns import list_corpus_maps                   # noqa: E402
from bloodmap.texture_align import wall_art_sizes                # noqa: E402
from bloodmap.texture_frame import continuity_rows               # noqa: E402


def merge(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in rows:
        for key, value in row.items():
            slot = out.setdefault(key, {"n": 0, "x": 0, "y": 0})
            for field in ("n", "x", "y"):
                slot[field] += value[field]
    return out


def table(name: str, rows: dict[str, Any]) -> str:
    lines = [f"{name}"]
    for key in sorted(rows, key=lambda k: -rows[k]["n"]):
        row = rows[key]
        n, x, y = row["n"], row["x"], row["y"]
        lines.append(f"  {key:26} n={n:<6} x {100*x//n:3}%  y {100*y//n:3}%")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", default="blood-campaign")
    parser.add_argument("--map", action="append", default=[],
                        help="a built map to measure beside the campaign")
    parser.add_argument("--json", default="reports/texture-continuity.json")
    args = parser.parse_args(argv)

    sizes = wall_art_sizes()
    if not sizes:
        print("no ART in reference/blood; nothing can be measured")
        return 1

    entries = sorted(list_corpus_maps(population=args.population),
                     key=lambda entry: entry.path.stem)
    per_map = {}
    for entry in entries:
        per_map[entry.path.stem.upper()] = continuity_rows(read_map(entry.path), sizes)
    campaign = merge(list(per_map.values()))
    print(table(f"{args.population} ({len(entries)} maps)", campaign))

    built = {}
    for path in args.map or ("projects/blood-city/level/blood-city-current.MAP",
                             "projects/pattern-zoo/level/pattern-zoo.MAP"):
        target = pathlib.Path(path)
        if not target.exists():
            print(f"\n{path}: absent")
            continue
        rows = continuity_rows(read_map(target), sizes)
        built[target.name] = rows
        print()
        print(table(target.name, rows))

    payload = {"population": args.population, "maps": len(entries),
               "campaign": campaign, "per_map": per_map, "built": built}
    out = pathlib.Path(args.json)
    out.write_text(json.dumps(payload, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print("\nwrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
