"""The outdoor light of maps, against the campaign's town maps: spread, facing, ground.

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
    by = row["by_facing"]
    return (f"{name:28s} walls {row['walls']:5d}  wall sd {row['wall_sd']:5.1f}  "
            f"by facing N/E/S/W {by['N']}/{by['E']}/{by['S']}/{by['W']}  "
            f"step {row['facing_step']}  ground {row['ground_median']} (sd {row['ground_sd']})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("maps", nargs="*")
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)
    out = {}
    for name in TOWNS:
        out[name] = profile(name)
        print(line(name, out[name]))
    sds = [out[n]["wall_sd"] for n in TOWNS]
    steps = [out[n]["facing_step"] for n in TOWNS]
    print(f"{'campaign towns':28s} wall sd {min(sds)}..{max(sds)}, facing step {min(steps)}..{max(steps)}")
    for name in args.maps:
        out[name] = profile(name)
        print(line(pathlib.Path(name).name, out[name]))
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(out, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
