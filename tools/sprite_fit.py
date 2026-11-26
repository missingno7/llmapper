"""Print where a map's sprites do not fit as the engine draws them: sunk, through a ceiling, squeezed, overlapping, hung on air.

    python -m tools.sprite_fit projects/blood-city/level/blood-city-current.MAP
    python -m tools.sprite_fit --rates maps...      # one line per map
    python -m tools.sprite_fit <MAP> --json out.json

The sensor, its thresholds and why each is where the campaign stops are
`bloodmap.sprite_fit`; this is its command line.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bloodmap.sprite_fit import *  # noqa: E402,F401,F403
from bloodmap.sprite_fit import (  # noqa: E402,F401
    art, audit, drawn_extent, drawn_lift, faults, flat_overlaps, hung_tiles, lifted, lint, on_travelling_floor, overlaps,
    rates, stood_on_floor, sunk_actors, unbacked,
)


def main(argv=None) -> int:
    from bloodmap.format import read_map

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("maps", nargs="+")
    parser.add_argument("--rates", action="store_true")
    parser.add_argument("--json")
    args = parser.parse_args(argv)
    out = {}
    for text in args.maps:
        path = pathlib.Path(text)
        if not path.is_absolute() and not path.exists():
            path = ROOT / text
        disk = read_map(path)
        rows = audit(disk)
        covering = overlaps(disk)
        lying = flat_overlaps(disk)
        buried = sunk_actors(disk)
        out[path.stem] = {"rates": rates(rows), "faults": faults(rows),
                          "overlaps": covering, "flat_overlaps": lying,
                          "sunk_actors": buried}
        print(path.stem, rates(rows), "overlapping wall sprite pairs:",
              len(covering), "flat pairs:", len(lying), "sunk actors:",
              len(buried))
        if args.rates:
            continue
        for pair in lying:
            print(f"  flat      sprites {pair['a']} and {pair['b']} tiles "
                  f"{pair['tiles']} sector {pair['sector']} at "
                  f"({pair['x']}, {pair['y']}): {pair['covered']:.0%} of the "
                  "smaller is covered")
        for r in buried:
            print(f"  actor     sprite {r['sprite']:4d} tile {r['tile']:5d} "
                  f"type {r['type']} sector {r['sector']}: {r['sunk']:.0%} "
                  "of it is under its floor")
        for pair in covering:
            print(f"  overlap   sprites {pair['a']} and {pair['b']} tiles "
                  f"{pair['tiles']} sector {pair['sector']} at "
                  f"({pair['x']}, {pair['y']}): {pair['covered']:.0%} of the "
                  "smaller is covered")
        for kind, found in faults(rows).items():
            for r in sorted(found, key=lambda r: (r["tile"], r["sprite"])):
                detail = (f"room {r.get('room')} for half width "
                          f"{r.get('half_width')}" if kind == "squeezed"
                          else f"{r[kind]:.0%} of its height")
                print(f"  {kind:9s} sprite {r['sprite']:4d} tile {r['tile']:5d} "
                      f"{r['align']:5s} type {r['type']:3d} sector "
                      f"{r['sector']:4d} at ({r['x']}, {r['y']}): {detail}")
        for r in lifted(rows):
            print(f"  lifted    sprite {r['sprite']:4d} tile {r['tile']:5d} sector "
                  f"{r['sector']:4d}: {r['over_floor']} bodies over its floor "
                  f"(the campaign stands it at {r['campaign']})")
        out[path.stem]["lifted"] = lifted(rows)
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(out, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
