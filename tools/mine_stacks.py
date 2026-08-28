"""Room over room, as Blood actually builds it.

Blood has no portal primitive. What it has is `CheckLink` (warp.cpp:183): a
sector may carry an *upper* link marker and/or a *lower* one, and when a sprite's
z crosses the threshold the engine moves it to the partner marker's sector and
translates it by exactly

    x += lower.x - upper.x
    y += lower.y - upper.y
    z += z2 - z1

So the boundary between the two rooms is **a translation at a plane**, and
nothing else. That is the same model the playtest bot arrived at from the other
direction, which is worth noting: it navigates E1M1 with it.

Six marker types make four kinds of link, and the difference between them is
only what the threshold plane *is* and what happens to the player when it is
crossed::

    kMarkerLowLink   6 / kMarkerUpLink    7   threshold is the marker's own z
    kMarkerUpWater   9 / kMarkerLowWater 10   threshold is the sector floor/ceiling
    kMarkerUpStack  11 / kMarkerLowStack 12   likewise; the other side is drawn
    kMarkerUpGoo    13 / kMarkerLowGoo   14   likewise, sludge instead of water

`kMarkerUpStack` is the one that is room-over-room in the sense people mean: on
crossing, the engine flags the sector's ceiling picnum for drawing, so you see
through the boundary rather than merely passing it.

.. code-block:: bash

    python -m tools.mine_stacks -o knowledge/blood/design/stacks-v1.json

What this measures, per pair: which maps use it, the offset between the paired
markers, whether the two sectors' footprints are congruent, whether they overlap
in plan (parked apart, or genuinely stacked), and how far apart they sit.
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

from bloodmap.format import read_map

SCHEMA = "llmapper.blood-stacks"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")
DEATHWISH = re.compile(r"^DWE1M\d+$")

PLAYER_WIDTH = 384.0

#: type -> (name, partner type, "upper" or "lower")
MARKERS = {
    6: ("low-link", 7, "lower"),
    7: ("up-link", 6, "upper"),
    9: ("up-water", 10, "upper"),
    10: ("low-water", 9, "lower"),
    11: ("up-stack", 12, "upper"),
    12: ("low-stack", 11, "lower"),
    13: ("up-goo", 14, "upper"),
    14: ("low-goo", 13, "lower"),
}

#: The pair a link belongs to, named by its upper half.
FAMILY = {6: "link", 7: "link", 9: "water", 10: "water",
          11: "stack", 12: "stack", 13: "goo", 14: "goo"}


def loop_of(disk: Any, sector: int) -> list[tuple[int, int]]:
    fields = disk.sectors[sector].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    out, wall = [], start
    while True:
        here = disk.walls[wall].fields
        out.append((int(here["x"]), int(here["y"])))
        wall = int(here["point2"])
        if wall == start or len(out) > count:
            break
    return out


def congruent(a: list[tuple[int, int]], b: list[tuple[int, int]],
              offset: tuple[int, int], tolerance: int = 16) -> bool:
    """Is loop `b` loop `a` moved by `offset`?"""
    if len(a) != len(b):
        return False
    wanted = [(x + offset[0], y + offset[1]) for x, y in a]
    for rotation in range(len(b)):
        turned = b[rotation:] + b[:rotation]
        if all(abs(p[0] - q[0]) <= tolerance and abs(p[1] - q[1]) <= tolerance
               for p, q in zip(wanted, turned)):
            return True
    return False


def bounds(loop: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    xs = [p[0] for p in loop]
    ys = [p[1] for p in loop]
    return min(xs), min(ys), max(xs), max(ys)


def overlaps(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> bool:
    ax0, ay0, ax1, ay1 = bounds(a)
    bx0, by0, bx1, by1 = bounds(b)
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def observe(name: str, disk: Any) -> list[dict[str, Any]]:
    """Every link pair in one map."""
    # The pairing is by XSPRITE.data1, not by `owner`. `warpInit` walks every
    # upper link, reads its data1, and searches every lower link for one with the
    # same value -- filling `owner` in at load. The stored map has no owner to
    # read, which is why the first version of this pass found 251 pairs and
    # matched none of them.
    uppers: dict[int, tuple[Any, int]] = {}
    lowers: dict[int, list[tuple[Any, int]]] = defaultdict(list)
    for index, sprite in enumerate(disk.sprites):
        kind = int(sprite.fields["type"])
        if kind not in MARKERS:
            continue
        extra = sprite.extra
        if extra is None:
            continue                       # warpInit skips a marker with no XSprite
        # `data_1`, with the underscore. `.get("data1", 0)` returned 0 for every
        # marker in the corpus and made the whole sweep report 251 pairs and
        # match none of them -- a default swallowing a typo, which is the one
        # failure mode of `.get` worth being afraid of.
        if "data_1" not in extra.fields:
            raise KeyError("XSPRITE has no data_1 field; the schema has moved")
        link = int(extra.fields["data_1"] or 0)
        if MARKERS[kind][2] == "upper":
            uppers[index] = (sprite.fields, link)
        else:
            lowers[link].append((sprite.fields, index))

    out = []
    for index, (fields, link) in uppers.items():
        kind = int(fields["type"])
        candidates = lowers.get(link, [])
        if not candidates:
            out.append({"map": name, "family": FAMILY[kind], "upper_type": kind,
                        "paired": False, "link_id": link,
                        "note": "no lower marker carries this link id"})
            continue
        other, partner = candidates[0]
        upper_sector = int(fields["sector"])
        lower_sector = int(other["sector"])
        if not (0 <= upper_sector < len(disk.sectors)
                and 0 <= lower_sector < len(disk.sectors)):
            continue
        offset = (int(other["x"]) - int(fields["x"]),
                  int(other["y"]) - int(fields["y"]))
        top = loop_of(disk, upper_sector)
        bottom = loop_of(disk, lower_sector)
        upper_fields = disk.sectors[upper_sector].fields
        lower_fields = disk.sectors[lower_sector].fields
        out.append({
            "map": name,
            "family": FAMILY[kind],
            "upper_type": kind,
            "paired": True,
            "link_id": link,
            "lower_candidates": len(candidates),
            "upper_sector": upper_sector,
            "lower_sector": lower_sector,
            "offset": list(offset),
            "distance_player_widths": round(math.hypot(*offset) / PLAYER_WIDTH, 1),
            "same_wall_count": len(top) == len(bottom),
            "congruent": congruent(top, bottom, offset),
            "overlaps_in_plan": overlaps(top, bottom),
            "upper_walls": len(top),
            "lower_walls": len(bottom),
            "upper_floor_z": int(upper_fields["floor_z"]),
            "lower_ceiling_z": int(lower_fields["ceiling_z"]),
            "upper_floor_stat": int(upper_fields["floor_stat"]),
            "lower_ceiling_stat": int(lower_fields["ceiling_stat"]),
            "upper_underwater": bool(disk.sectors[upper_sector].extra and int(
                disk.sectors[upper_sector].extra.fields.get("underwater", 0) or 0)),
            "lower_underwater": bool(disk.sectors[lower_sector].extra and int(
                disk.sectors[lower_sector].extra.fields.get("underwater", 0) or 0)),
        })
    return out


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)
    families = {}
    for family, items in sorted(by_family.items()):
        paired = [r for r in items if r.get("paired")]
        maps = sorted({r["map"] for r in items})
        distances = sorted(r["distance_player_widths"] for r in paired)
        families[family] = {
            "pairs": len(items),
            "paired": len(paired),
            "maps": len(maps),
            "map_names": maps,
            "congruent": sum(1 for r in paired if r["congruent"]),
            "same_wall_count": sum(1 for r in paired if r["same_wall_count"]),
            "overlaps_in_plan": sum(1 for r in paired if r["overlaps_in_plan"]),
            "distance_player_widths": {
                "min": distances[0] if distances else None,
                "median": round(statistics.median(distances), 1) if distances else None,
                "max": distances[-1] if distances else None,
            },
            "underwater_upper": sum(1 for r in paired if r["upper_underwater"]),
            "underwater_lower": sum(1 for r in paired if r["lower_underwater"]),
        }
    return families


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--include-deathwish", action="store_true")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    seen = 0
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        ours = CAMPAIGN.match(name) or (args.include_deathwish and DEATHWISH.match(name))
        if not ours:
            continue
        try:
            rows.extend(observe(name, read_map(path)))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
            continue
        seen += 1

    families = summarise(rows)
    document = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "maps": seen,
        "pairs": len(rows),
        "families": families,
        "pairs_detail": rows,
        "engine": {
            "translation": "warp.cpp:183 CheckLink -- x += lower.x-upper.x, "
                           "y += lower.y-upper.y, z += z2-z1",
            "pairing": "the upper marker's `owner` field names the lower marker's "
                       "sprite index",
            "threshold": "the marker's own z for link (6/7); the sector floor or "
                         "ceiling for water (9/10), stack (11/12) and goo (13/14)",
            "drawn_through": "actor.cpp:4668 -- crossing a stack marker flags the "
                             "sector's floor or ceiling picnum for drawing, which "
                             "is what makes a stack see-through and a link not",
        },
        "reading_guide": [
            "a pair is reported from its upper marker; `paired` is false when the "
            "owner field names no marker",
            "congruent means the lower sector's outline is the upper's moved by "
            "the marker offset -- the two rooms are the same shape",
            "overlaps_in_plan means the two sectors share ground on the map, "
            "which is what a stack cannot do and a link need not avoid",
        ],
    }

    print("%d maps, %d link pairs" % (seen, len(rows)))
    print("%-8s %6s %6s %6s %10s %10s %12s %s" % (
        "family", "pairs", "maps", "congr", "same walls", "overlap", "dist (pw)", "maps"))
    for family, spec in families.items():
        d = spec["distance_player_widths"]
        print("%-8s %6d %6d %6d %10d %10d %12s %s" % (
            family, spec["pairs"], spec["maps"], spec["congruent"],
            spec["same_wall_count"], spec["overlaps_in_plan"],
            "%s..%s" % (d["min"], d["max"]),
            ",".join(spec["map_names"][:6]) + ("..." if len(spec["map_names"]) > 6 else "")))

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
        print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
