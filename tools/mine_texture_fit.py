"""How many times Blood lets a wall texture repeat up a wall.

The general form of a fault first noticed on one door: a chapel door showing
eleven stacked copies of the same 64x128 door tile, because the tile was put on
a wall as tall as the courtyard instead of on a wall as tall as a door.

Build's arithmetic for a wall's vertical texture span, in z units, is

    tilesizy * y_repeat * 8

so the number of times the tile repeats over a visible band of height ``H`` is
``H / (tilesizy * y_repeat * 8)``. A mapper choosing ``y_repeat`` is choosing
that number, and mostly chooses it to come out near one.

Three bands are measured separately because they are three different decisions:

``solid``   a one-sided wall: the whole floor-to-ceiling face
``upper``   the band above an opening, drawn from this wall's own picnum
``lower``   the band below one

The interesting statistic is not the mean but the tail: how often does the
campaign let a tile repeat more than twice, and what does it put there when it
does. A repeating brick or rubble tile is invisible at any count; a *door*, a
sign, a window, or anything with a single feature in the middle of it announces
every repeat.

.. code-block:: bash

    python -m tools.mine_texture_fit -o knowledge/blood/design/texture-fit-v1.json
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.format import read_map
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.reachability import design_sectors
from bloodmap.rules import art_sizes

SCHEMA = "llmapper.blood-texture-fit"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

#: Below this a band is a kerb or a step riser, not a surface anybody reads.
MIN_BAND = 2048


def wall_owners(disk: Any) -> dict[int, int]:
    owner: dict[int, int] = {}
    for index, sector in enumerate(disk.sectors):
        start = int(sector.fields["wall_ptr"])
        for wall in range(start, start + int(sector.fields["wall_count"])):
            owner[wall] = index
    return owner


def observe(name: str, disk: Any, sizes: dict[int, tuple[int, int]]) -> list[dict[str, Any]]:
    owner = wall_owners(disk)
    playable = design_sectors(disk)
    out = []
    for index, wall in enumerate(disk.walls):
        fields = wall.fields
        mine = owner.get(index)
        if mine is None or mine not in playable:
            continue
        here = disk.sectors[mine].fields
        my_ceiling, my_floor = int(here["ceiling_z"]), int(here["floor_z"])
        picnum = int(fields["picnum"])
        y_repeat = int(fields["y_repeat"])
        size = sizes.get(picnum)
        if not size or y_repeat <= 0:
            continue
        span = size[1] * y_repeat * 8          # the tile's vertical extent, in z
        if span <= 0:
            continue

        other = int(fields["next_sector"])
        bands: list[tuple[str, int]] = []
        if other < 0:
            bands.append(("solid", my_floor - my_ceiling))
        elif 0 <= other < len(disk.sectors):
            there = disk.sectors[other].fields
            bands.append(("upper", max(my_ceiling, int(there["ceiling_z"])) - my_ceiling))
            bands.append(("lower", my_floor - min(my_floor, int(there["floor_z"]))))

        for band_name, height in bands:
            if height < MIN_BAND:
                continue
            out.append({
                "map": name,
                "wall": index,
                "sector": mine,
                "band": band_name,
                "picnum": picnum,
                "y_repeat": y_repeat,
                "height": height,
                "height_player_heights": round(height / PLAYER_HEIGHT, 3),
                "repeats": round(height / span, 3),
            })
    return out


def band_stats(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}

    def at(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))]

    return {
        "min": round(ordered[0], 2),
        "q1": round(at(0.25), 2),
        "median": round(statistics.median(ordered), 2),
        "q3": round(at(0.75), 2),
        "p95": round(at(0.95), 2),
        "p99": round(at(0.99), 2),
        "max": round(ordered[-1], 2),
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_band: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_band[row["band"]].append(row["repeats"])
    everything = [row["repeats"] for row in rows]

    # Which tiles the campaign is willing to stack. A tile that repeats happily
    # is a field material; one that never does has a feature in it.
    per_tile: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        per_tile[row["picnum"]].append(row["repeats"])
    stackable = {
        str(picnum): {"n": len(values), "median": round(statistics.median(values), 2),
                      "p95": round(sorted(values)[min(len(values) - 1,
                                                      int(0.95 * (len(values) - 1)))], 2)}
        for picnum, values in per_tile.items() if len(values) >= 40
    }
    return {
        "bands_measured": len(rows),
        "repeats": band_stats(everything),
        "by_band": {name: {"n": len(values), **band_stats(values)}
                    for name, values in sorted(by_band.items())},
        "share_over": {
            str(cut): round(sum(1 for value in everything if value > cut)
                            / max(1, len(everything)), 5)
            for cut in (1.5, 2.0, 3.0, 4.0, 6.0)
        },
        "per_tile": stackable,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    sizes = art_sizes()
    if not sizes:
        print("no Blood ART available")
        return 1

    rows: list[dict[str, Any]] = []
    seen = 0
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name):
            continue
        try:
            rows.extend(observe(name, read_map(path), sizes))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
            continue
        seen += 1

    summary = summarise(rows)
    document = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "maps": seen,
        "summary": summary,
        "engine": {
            "span": "a wall texture's vertical extent in z is tilesizy * y_repeat * 8, "
                    "so repeats = band height / that",
            "upper_band_owner": "the band above an opening is drawn from that "
                                "wall's own picnum, not the neighbour's",
        },
        "reading_guide": [
            "repeats near 1.00 means the mapper sized the tile to the wall",
            "a field material stacks invisibly; a tile with one feature in the "
            "middle -- a door, a sign, a window -- announces every repeat",
            "a band is what the campaign did, never what a level must do",
        ],
    }

    s = summary
    print("%d maps, %d visible wall bands" % (seen, s["bands_measured"]))
    print()
    print("vertical texture repeats: %s" % s["repeats"])
    for name, stat in s["by_band"].items():
        print("  %-6s n=%-7d q1 %.2f  median %.2f  q3 %.2f  p95 %.2f  p99 %.2f"
              % (name, stat["n"], stat["q1"], stat["median"], stat["q3"],
                 stat["p95"], stat["p99"]))
    print()
    for cut, share in s["share_over"].items():
        print("  repeats more than %-4s : %6.2f%%" % (cut, 100 * share))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
        print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
