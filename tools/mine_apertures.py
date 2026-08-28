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
import glob
import json
import pathlib
import re
import statistics
from collections import Counter
from typing import Any

from bloodmap.format import read_map
from bloodmap.player_space import PLAYER_PROFILES

SCHEMA = "llmapper.blood-apertures"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

#: One standing human, from the player profile. Never hardcode this.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height
PLAYER_WIDTH = float(PLAYER_PROFILES["blood"].body_width)

#: Below this an opening is not a way through -- it is a window, a grate, or a
#: gap under a door.
WALKABLE_OPENING = 4096

#: Below this share of the smaller room's outline, a connection is a hole cut in
#: a wall rather than the seam where two halves of one space meet.
PINCH = 0.25


def wall_owners(disk: Any) -> dict[int, int]:
    owner: dict[int, int] = {}
    for index, sector in enumerate(disk.sectors):
        start = int(sector.fields["wall_ptr"])
        for wall in range(start, start + int(sector.fields["wall_count"])):
            owner[wall] = index
    return owner


def dominant_wall_tile(disk: Any, sector: int) -> int:
    fields = disk.sectors[sector].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    tally = Counter(int(disk.walls[w].fields["picnum"]) for w in range(start, start + count))
    return tally.most_common(1)[0][0]


def perimeter(disk: Any, sector: int) -> float:
    fields = disk.sectors[sector].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    total = 0.0
    for wall in range(start, start + count):
        here = disk.walls[wall].fields
        there = disk.walls[int(here["point2"])].fields
        total += ((int(there["x"]) - int(here["x"])) ** 2
                  + (int(there["y"]) - int(here["y"])) ** 2) ** 0.5
    return total


def observe(name: str, disk: Any) -> list[dict[str, Any]]:
    """Every walkable two-sided wall, classified.

    The classification matters more than the measurements. A first pass over the
    campaign called 60.86% of openings "full height", which would have made
    cathedral portals the Blood norm. They are not: most two-sided walls are
    *seams* inside one continuous space -- a hall split into three sectors so the
    middle one can be darker, a room divided to carry a slope -- and a seam has
    no lintel and no step because there is no wall there to have one.

    An aperture is a narrowing. Something about it is smaller than the room:

    door_sector   one side is a Z-motion door (600/602); a door by fiat
    lintel        the facade continues above the hole
    pinch         the connection is a small share of the room's outline
    step_only     a sill but no header -- a window ledge, a pool edge
    seam          none of the above; two sectors of one space meeting
    """
    owner = wall_owners(disk)
    shared: Counter = Counter()
    for index, wall in enumerate(disk.walls):
        other = int(wall.fields["next_sector"])
        mine = owner.get(index)
        if other < 0 or mine is None:
            continue
        nxt = disk.walls[int(wall.fields["point2"])].fields
        shared[(mine, other)] += (
            (int(nxt["x"]) - int(wall.fields["x"])) ** 2
            + (int(nxt["y"]) - int(wall.fields["y"])) ** 2) ** 0.5

    dominant: dict[int, int] = {}
    around: dict[int, float] = {}
    out = []
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        other = int(fields["next_sector"])
        if other < 0:
            continue
        mine = owner.get(index)
        if mine is None or not 0 <= other < len(disk.sectors):
            continue
        here = disk.sectors[mine].fields
        there = disk.sectors[other].fields
        my_ceiling, my_floor = int(here["ceiling_z"]), int(here["floor_z"])
        their_ceiling, their_floor = int(there["ceiling_z"]), int(there["floor_z"])

        top = max(my_ceiling, their_ceiling)        # the lower of the two ceilings
        bottom = min(my_floor, their_floor)         # the higher of the two floors
        leaf = bottom - top
        if leaf < WALKABLE_OPENING:
            continue                                # not a way through
        lintel = top - my_ceiling                   # facade above the hole
        step = my_floor - bottom                    # facade below it
        facade = my_floor - my_ceiling

        for sector in (mine, other):
            if sector not in dominant:
                dominant[sector] = dominant_wall_tile(disk, sector)
                around[sector] = perimeter(disk, sector)

        nxt = disk.walls[int(fields["point2"])].fields
        length = ((int(nxt["x"]) - int(fields["x"])) ** 2
                  + (int(nxt["y"]) - int(fields["y"])) ** 2) ** 0.5
        openness = shared[(mine, other)] / max(1.0, min(around[mine], around[other]))

        if int(here["type"]) in (600, 602) or int(there["type"]) in (600, 602):
            kind = "door_sector"
        elif lintel > 0:
            kind = "lintel"
        elif openness < PINCH:
            kind = "pinch"
        elif step > 0:
            kind = "step_only"
        else:
            kind = "seam"

        out.append({
            "map": name,
            "wall": index,
            "sector": mine,
            "next_sector": other,
            "kind": kind,
            "aperture": kind in ("door_sector", "lintel", "pinch"),
            "leaf_player_heights": round(leaf / PLAYER_HEIGHT, 3),
            "facade_player_heights": round(facade / PLAYER_HEIGHT, 3),
            "lintel_player_heights": round(lintel / PLAYER_HEIGHT, 3),
            "step_player_heights": round(step / PLAYER_HEIGHT, 3),
            "width_player_widths": round(length / PLAYER_WIDTH, 2),
            "openness": round(openness, 3),
            "full_height": lintel <= 0 and step <= 0,
            # Build takes the upper section from this wall's own picnum, so the
            # band above the hole is the viewing room's to paint.
            "lintel_continues_facade": int(fields["picnum"]) == dominant[mine],
            "wall_picnum": int(fields["picnum"]),
            "facade_picnum": dominant[mine],
            "sector_type": int(here["type"]),
            "masked": bool(int(fields["cstat"]) & 16),
        })
    return out


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
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    seen = 0
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name):
            continue
        try:
            rows.extend(observe(name, read_map(path)))
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
