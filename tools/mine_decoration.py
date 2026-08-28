"""How Blood dresses a room: which decorations, how big, where, how many.

`bloodmap.vocabulary.sprite_repeats` asks an author how tall a decoration should
be in player heights and derives the repeat from the tile's pixels.  That is the
right calculation and the wrong question.  The campaign says a decoration is
almost always drawn at its **natural size** -- 60% of visible decorations use
``y_repeat`` 64 exactly, 73% use a power of two, and the whole campaign uses only
53 distinct values.  The height is a consequence of picking the tile, not an
input the designer supplies.

So this mines three things an author actually needs and cannot currently get:

* the canonical size of each decoration tile, and how tightly it is held;
* which few tiles genuinely scale with the room they are in;
* how thickly rooms are dressed, and where the sprites sit.

.. code-block:: bash

    python -m tools.mine_decoration --maps maps/blood --art reference/blood \\
        -o knowledge/blood/design/decoration-v1.json

A "decoration" here is a sprite with no gameplay type that is not marked
invisible, in a sector the player can reach.  Markers, traps, dudes and pickups
all carry a type and are excluded: they are placement questions, not dressing.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.art import read_art_directory
from bloodmap.format import read_map
from bloodmap.reachability import design_sectors

SCHEMA = "llmapper.decoration-evidence"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

from bloodmap.player_space import PLAYER_PROFILES

#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height
PLAYER_WIDTH = 384

CSTAT_INVISIBLE = 32768
CSTAT_WALL_ALIGNED = 16
CSTAT_FLOOR_ALIGNED = 32

#: The cstat bits that say how a sprite is *mounted* -- blocking, alignment,
#: one-sidedness, centring, hitscan. The flip bits (4, 8) and the translucency
#: bits vary from placement to placement and are not a property of the tile, so
#: they are masked out before asking what a tile's usual mounting is.
CSTAT_STRUCTURAL = 1 | 16 | 32 | 64 | 128 | 256

#: Below this the tile is drawn at one size wherever it appears, and an author
#: should simply use that size rather than choosing one.
FIXED_SIZE_RATIO = 1.35

#: A correlation this strong between drawn size and room height means the tile
#: is one of the few that is genuinely scaled to its space.
SCALES_WITH_ROOM = 0.45


def _alignment(cstat: int) -> str:
    if cstat & CSTAT_FLOOR_ALIGNED:
        return "floor"
    if cstat & CSTAT_WALL_ALIGNED:
        return "wall"
    return "face"


def observe(path: pathlib.Path, art: dict[int, Any]) -> list[dict[str, Any]]:
    disk = read_map(path)
    playable = set(design_sectors(disk))
    rows: list[dict[str, Any]] = []
    for sprite in disk.sprites:
        fields = sprite.fields
        if int(fields["type"]) != 0:
            continue
        cstat = int(fields["cstat"])
        if cstat & CSTAT_INVISIBLE:
            continue
        sector_id = int(fields["sector"])
        if sector_id not in playable:
            continue
        tile = art.get(int(fields["picnum"]))
        if tile is None or not tile.height:
            continue
        sector = disk.sectors[sector_id].fields
        floor_z, ceiling_z = int(sector["floor_z"]), int(sector["ceiling_z"])
        room_height = abs(floor_z - ceiling_z) / PLAYER_HEIGHT
        rows.append({
            "map": path.stem.upper(),
            "sector": sector_id,
            "picnum": int(fields["picnum"]),
            "y_repeat": int(fields["y_repeat"]),
            "x_repeat": int(fields["x_repeat"]),
            "drawn_height": ((int(fields["y_repeat"]) * tile.height) << 2) / PLAYER_HEIGHT,
            "room_height": room_height,
            "above_floor": (floor_z - int(fields["z"])) / PLAYER_HEIGHT,
            "alignment": _alignment(cstat),
            "cstat": cstat,
            "shade": int(fields["shade"]),
        })
    return rows


def _correlation(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 12:
        return None
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    numerator = sum((a - mx) * (b - my) for a, b in pairs)
    denominator = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return numerator / denominator if denominator else None


def build(rows: list[dict[str, Any]], *, min_uses: int) -> dict[str, Any]:
    by_tile: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_tile[row["picnum"]].append(row)

    repeats = Counter(row["y_repeat"] for row in rows)
    total = sum(repeats.values())

    tiles = []
    for picnum, group in sorted(by_tile.items(), key=lambda item: -len(item[1])):
        if len(group) < min_uses:
            continue
        drawn = sorted(row["drawn_height"] for row in group)
        low = drawn[int(0.1 * (len(drawn) - 1))]
        high = drawn[int(0.9 * (len(drawn) - 1))]
        ratio = (high / low) if low else 0.0
        repeat_counts = Counter(row["y_repeat"] for row in group)
        canonical, canonical_n = repeat_counts.most_common(1)[0]
        correlation = _correlation([(row["room_height"], row["drawn_height"]) for row in group])
        alignments = Counter(row["alignment"] for row in group)
        above = sorted(row["above_floor"] for row in group)
        cstats = Counter(row["cstat"] & CSTAT_STRUCTURAL for row in group)
        shades = Counter(row["shade"] for row in group)
        x_repeats = Counter(row["x_repeat"] for row in group)
        tiles.append({
            "picnum": picnum,
            "uses": len(group),
            "maps": len({row["map"] for row in group}),
            "canonical_y_repeat": canonical,
            "canonical_share": round(canonical_n / len(group), 3),
            "drawn_height_player_heights": {
                # p10/p90 describe where the campaign usually draws this tile;
                # min/max are what it ever draws. Six per cent of the campaign's
                # own decorations sit outside their tile's p10..p90, so a
                # percentile band cannot be used as a limit -- it would reject
                # Blood. Tile 1044 is the worked example: p10 is 5.09 player
                # heights and the smallest one in the game is 3.64.
                "min": round(drawn[0], 2),
                "p10": round(low, 2),
                "median": round(statistics.median(drawn), 2),
                "p90": round(high, 2),
                "max": round(drawn[-1], 2),
            },
            "size_ratio_p90_over_p10": round(ratio, 2),
            "fixed_size": bool(ratio and ratio < FIXED_SIZE_RATIO),
            "scales_with_room": bool(correlation is not None and abs(correlation) >= SCALES_WITH_ROOM),
            "room_height_correlation": None if correlation is None else round(correlation, 2),
            "alignment": {name: round(count / len(group), 3) for name, count in alignments.most_common()},
            "above_floor_median": round(statistics.median(above), 2),
            # The modal cstat carries the alignment, the one-sidedness and the
            # centring together, which is what a placement actually needs; the
            # alignment share above is only how confident that mode is.
            "canonical_cstat": cstats.most_common(1)[0][0],
            "canonical_cstat_share": round(cstats.most_common(1)[0][1] / len(group), 3),
            "canonical_x_repeat": x_repeats.most_common(1)[0][0],
            "canonical_shade": shades.most_common(1)[0][0],
        })

    per_sector = Counter()
    for row in rows:
        per_sector[(row["map"], row["sector"])] += 1
    counts = list(per_sector.values())

    correlations = [t["room_height_correlation"] for t in tiles if t["room_height_correlation"] is not None]
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "definition": (
            "a sprite with no gameplay type, not marked invisible, in a sector the "
            "player can reach"
        ),
        "decorations": len(rows),
        "distinct_tiles": len(by_tile),
        "sizing": {
            "y_repeat_histogram": {str(value): count for value, count in repeats.most_common(12)},
            "natural_size_share": round(repeats.get(64, 0) / total, 3) if total else 0.0,
            "power_of_two_share": round(
                sum(n for v, n in repeats.items() if v and not (v & (v - 1))) / total, 3
            ) if total else 0.0,
            "distinct_repeats": len(repeats),
            "tiles_drawn_at_one_size": sum(1 for t in tiles if t["fixed_size"]),
            "tiles_that_scale_with_the_room": sum(1 for t in tiles if t["scales_with_room"]),
            "median_room_height_correlation": (
                round(statistics.median([abs(c) for c in correlations]), 2) if correlations else None
            ),
        },
        "density": {
            "decorated_sectors": len(per_sector),
            "decorations_per_decorated_sector": {
                "median": statistics.median(counts) if counts else 0,
                "p90": sorted(counts)[int(0.9 * (len(counts) - 1))] if counts else 0,
                "max": max(counts) if counts else 0,
            },
        },
        "tiles": tiles,
        "reading_guide": [
            "canonical_cstat is the structural mounting only, with the flip and "
            "translucency bits masked off; its share says how much of a habit it is, "
            "and a tile below about half genuinely varies and needs a decision",
            "canonical_y_repeat is what to use; the drawn height is a consequence "
            "of the tile, not a number the designer chose",
            "fixed_size means the campaign never varies this tile's size, so "
            "asking an author for one is asking them to get it wrong",
            "scales_with_room names the few tiles that genuinely follow the space",
            "a share is what the campaign did, never what a level must do",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--art", default="reference/blood")
    parser.add_argument("--min-uses", type=int, default=20)
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    art = read_art_directory(args.art)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if name in seen or not CAMPAIGN.match(name):
            continue
        seen.add(name)
        try:
            rows.extend(observe(pathlib.Path(path), art))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")

    document = build(rows, min_uses=args.min_uses)
    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "maps": len(seen),
        "decorations": document["decorations"],
        "tiles_profiled": len(document["tiles"]),
        "sizing": document["sizing"],
        "output": args.output,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
