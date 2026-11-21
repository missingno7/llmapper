"""The outdoor light of maps, against the campaign's town maps: corners, facing within a building, tone, ground.

`bloodmap.sunlight.measure` over a set of maps, one line each, with the
campaign's own range printed first so a number is read against something.

.. code-block:: bash

    python -m tools.light_profile projects/blood-city/level/blood-city-current.MAP
    python -m tools.light_profile E3M1 E1M1 --json work/light.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: the campaign maps whose streets are towns, the reference for the range
TOWNS = ("E3M1", "E3M2", "E1M1", "E1M2", "E1M4", "E2M1", "E6M1")


def profile(name: str) -> dict:
    from bloodmap.corpus import corpus_map_path
    from bloodmap.format import read_map
    from bloodmap.sunlight import measure

    path = pathlib.Path(name)
    disk = read_map(path if path.suffix.lower() == ".map" else corpus_map_path(name))
    return measure(disk)


def line(name: str, row: dict) -> str:
    wb, cd = row["within_building"], row["corner_darker"]
    return (f"{name:24s} faces {row['walls']:4d}  sd {row['wall_sd']:4.1f}  "
            f"corners equal {row['corner_equal']} step {row['corner_step']}  "
            f"darker at a corner N/E/S/W {cd['N']}/{cd['E']}/{cd['S']}/{cd['W']}  "
            f"in a building N/E/S/W {wb['N']}/{wb['E']}/{wb['S']}/{wb['W']}  "
            f"one tile sd {row['tile_sd']}  walls {row['wall_median']} on ground {row['ground_median']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("maps", nargs="*")
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)
    out = {}
    for name in TOWNS:
        out[name] = profile(name)
        print(line(name, out[name]))
    for name in args.maps:
        out[name] = profile(name)
        print(line(pathlib.Path(name).name, out[name]))
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(out, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
