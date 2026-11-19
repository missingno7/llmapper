"""How big a hole in a wall is, and what Blood puts around it.

An opening is not an absence. Build draws a two-sided wall as three bands: an
*upper* section from the higher ceiling down to the lower one, a *lower* section
from the higher floor down to the lower one, and the gap between them -- and the
gap is the only part the player walks through. So an opening has:

    leaf     min(floor) - max(ceiling)     the hole itself
    lintel   the upper section             wall above the hole
    step     the lower section             wall below it

and each of those is a decision somebody made. This measures all three across
the campaign so the aperture grammar has defaults rather than guesses.

Two things it also measures, because the level program has been getting them
wrong from opposite directions:

* **who owns the lintel.** Build takes the upper section's tile from the wall's
  own ``picnum`` -- not the neighbour's -- so the band above an opening belongs
  to the *facade it is seen from*. Whether that continues the room's own wall is
  measurable, and a break there is the texture jump above a corridor mouth.
* **how tall an opening gets before it stops being a door.** Full-height
  openings exist -- a cathedral portal is real -- so the question is not whether
  the campaign does it but how often and how big.

A note on the unit
------------------

Heights here are in standing humans, and a standing human is 16960 z, not the
0x1600 this project used until 2026-08-27. 0x1600 is ``POSTURE.eyeAboveZ``, an
offset from the player sprite's *centre*; calling it a body height denominated
every measurement in the project in a unit three times too small. The first run
of this miner reported a median doorway of 5.82 "player heights", which should
have been the tell. It is 1.93 standing humans. See ``bloodmap/player_space.py``
for the correction and its evidence.

.. code-block:: bash

    python -m tools.mine_apertures -o knowledge/blood/design/apertures-v1.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import Counter
from typing import Any

from bloodmap.aperture import (
    PLAYER_HEIGHT, PLAYER_WIDTH, dominant_wall_tile, observe_openings,
)
from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map

SCHEMA = "llmapper.blood-apertures"
SCHEMA_VERSION = 1


def band(values: list[float], digits: int = 2) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}

    def at(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))]

    return {
        "min": round(ordered[0], digits),
        "q1": round(at(0.25), digits),
        "median": round(statistics.median(ordered), digits),
        "q3": round(at(0.75), digits),
        "p95": round(at(0.95), digits),
        "max": round(ordered[-1], digits),
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    kinds = Counter(r["kind"] for r in rows)
    apertures = [r for r in rows if r["aperture"]]
    with_lintel = [r for r in apertures if r["lintel_player_heights"] > 0]
    leaves = [r["leaf_player_heights"] for r in apertures]
    full = [r for r in apertures if r["full_height"]]

    def share_over(cut: float) -> float:
        return round(sum(1 for x in leaves if x > cut) / max(1, len(leaves)), 4)

    return {
        "two_sided_walkable_walls": len(rows),
        "kinds": {k: {"count": v, "share": round(v / max(1, len(rows)), 4)}
                  for k, v in kinds.most_common()},
        "apertures": len(apertures),
        "leaf_player_heights": band(leaves),
        "leaf_width_player_widths": band([r["width_player_widths"] for r in apertures]),
        "facade_player_heights": band([r["facade_player_heights"] for r in apertures]),
        "lintel": {
            "openings_with_one": len(with_lintel),
            "share": round(len(with_lintel) / max(1, len(apertures)), 3),
            "player_heights": band([r["lintel_player_heights"] for r in with_lintel]),
            "continues_the_facade": round(
                sum(1 for r in with_lintel if r["lintel_continues_facade"])
                / max(1, len(with_lintel)), 3),
        },
        "step": {
            "openings_with_one": sum(1 for r in apertures if r["step_player_heights"] > 0),
            "player_heights": band([r["step_player_heights"] for r in apertures
                                    if r["step_player_heights"] > 0]),
        },
        "full_height": {
            "openings": len(full),
            "share": round(len(full) / max(1, len(apertures)), 4),
            "leaf_player_heights": band([r["leaf_player_heights"] for r in full]),
            "in_door_sectors": sum(1 for r in full if r["sector_type"] == 600),
        },
        "leaf_taller_than": {str(c): share_over(c)
                             for c in (1.5, 2.0, 2.5, 3.0, 4.0, 6.0)},
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
            rows.extend(observe_openings(name, read_map(path)))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
            continue
        seen += 1

    summary = summarise(rows)
    document = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "maps": seen,
        "unit": "standing humans (%d z) and player widths (%d)"
                % (PLAYER_HEIGHT, PLAYER_WIDTH),
        "summary": summary,
        "engine": {
            "bands": "a two-sided wall draws an upper section from the lower of "
                     "the two ceilings up to its own, a lower section from the "
                     "higher of the two floors down to its own, and leaves the "
                     "gap between",
            "lintel_owner": "the upper section takes this wall's own picnum, not "
                            "the neighbour's, so the band above an opening "
                            "belongs to the facade it is seen from",
        },
        "reading_guide": [
            "leaf is the hole the player walks through, in standing humans",
            "lintel is the facade above it and step the facade below, both "
            "measured on the viewing side",
            "a seam is not an aperture: two sectors of one continuous space "
            "meeting, with no wall there to carry a lintel",
            "full_height means the opening runs the whole facade -- no lintel and "
            "no step -- which the campaign does, rarely, and on purpose",
            "a band is what the campaign did, never what a level must do",
        ],
    }

    s = summary
    print("%d maps, %d walkable two-sided walls" % (seen, s["two_sided_walkable_walls"]))
    print()
    for kind, stat in s["kinds"].items():
        print("  %-12s %6d  %5.1f%%" % (kind, stat["count"], 100 * stat["share"]))
    print()
    print("APERTURES: %d" % s["apertures"])
    print("  leaf height, standing humans : %s" % s["leaf_player_heights"])
    print("  leaf width, player widths    : %s" % s["leaf_width_player_widths"])
    print("  facade height                : %s" % s["facade_player_heights"])
    print()
    print("  lintel: %d have one (%.0f%%), %s"
          % (s["lintel"]["openings_with_one"], 100 * s["lintel"]["share"],
             s["lintel"]["player_heights"]))
    print("          continues the facade material in %.0f%%"
          % (100 * s["lintel"]["continues_the_facade"]))
    print("  step  : %d have one, %s"
          % (s["step"]["openings_with_one"], s["step"]["player_heights"]))
    print()
    print("  full height: %d (%.1f%% of apertures), %s"
          % (s["full_height"]["openings"], 100 * s["full_height"]["share"],
             s["full_height"]["leaf_player_heights"]))
    print()
    for cut, share in s["leaf_taller_than"].items():
        print("  leaf taller than %-4s humans: %5.1f%% of apertures" % (cut, 100 * share))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
        print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
