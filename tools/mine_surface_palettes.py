"""Which tiles Blood uses on which kind of space.

The material knowledge base already records what a tile looks like and which
other tiles it is seen beside -- 16,798 tile-to-tile relations.  None of that
answers the question an author actually asks, which is not "what goes with tile
180" but **"I am making a large sky-lit courtyard at ground level; what does
Blood put on it?"**

That is a conditional, and the difference matters: a marginal distribution over
tiles can only score a choice already made, while a distribution conditioned on
properties the author knows *before* choosing can make the choice.

So the context signature is built only from things a designer has decided by the
time they pick a texture:

* how big the space is, in player areas;
* how tall it is, in player heights;
* whether it is open to the sky;
* how many ways out it has;
* where it sits in the level's vertical range.

Nothing in the signature is a tile, a shade or a material.  If it were, the
result would be a tautology.

.. code-block:: bash

    python -m tools.mine_surface_palettes --maps maps/blood \\
        -o knowledge/blood/design/surface-palettes-v1.json

Following the promotion discipline used for structures, episodes 1-3 are fitted
and 4 and 6 are held out, so the report can say whether a conditional transfers
to maps the fit never saw rather than only that it exists.
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
from bloodmap.reachability import design_sectors, portal_graph

SCHEMA = "llmapper.surface-palettes"
SCHEMA_VERSION = 1

PLAYER_WIDTH = 384
PLAYER_AREA = float(PLAYER_WIDTH * PLAYER_WIDTH)

from bloodmap.player_space import PLAYER_PROFILES

#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

CAMPAIGN = re.compile(r"^(E[1-46])M([1-9])$")
FIT_EPISODES = ("E1", "E2", "E3")

#: Bands are chosen so each holds a usable share of the corpus rather than to
#: look tidy; a band nothing lands in teaches nothing.
AREA_BANDS = ((4.0, "tiny"), (16.0, "small"), (64.0, "medium"), (256.0, "large"), (math.inf, "vast"))
HEIGHT_BANDS = ((1.5, "crawl"), (3.0, "low"), (6.0, "tall"), (math.inf, "cavernous"))
EXIT_BANDS = ((1, "dead_end"), (2, "through"), (4, "junction"), (math.inf, "hub"))


def _band(value: float, bands) -> str:
    for limit, name in bands:
        if value <= limit:
            return name
    return bands[-1][1]


def _sector_area(disk: Any, sector_id: int) -> float:
    fields = disk.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    total = 0.0
    for index in range(start, start + int(fields["wall_count"])):
        wall = disk.walls[index].fields
        nxt = disk.walls[int(wall["point2"])].fields
        total += int(wall["x"]) * int(nxt["y"]) - int(nxt["x"]) * int(wall["y"])
    return abs(total) / 2.0


def observe_map(path: pathlib.Path) -> list[dict[str, Any]]:
    """One record per playable sector: its context, and what is painted on it."""
    disk = read_map(path)
    playable = set(design_sectors(disk))
    if not playable:
        return []
    graph = portal_graph(disk)
    floors = [int(disk.sectors[i].fields["floor_z"]) for i in playable]
    low, high = min(floors), max(floors)
    span = (high - low) or 1

    surfaces = {
        sector_id: {
            "floor": int(disk.sectors[sector_id].fields["floor_picnum"]),
            "ceiling": int(disk.sectors[sector_id].fields["ceiling_picnum"]),
            "wall": _dominant_wall(disk, sector_id),
        }
        for sector_id in playable
    }

    rows = []
    for sector_id in sorted(playable):
        fields = disk.sectors[sector_id].fields
        area = _sector_area(disk, sector_id) / PLAYER_AREA
        floor_z = int(fields["floor_z"])
        height = abs(floor_z - int(fields["ceiling_z"])) / PLAYER_HEIGHT
        exits = len({n for n in graph.get(sector_id, ()) if n in playable})
        # Build's z grows downward, so the smallest floor_z is the highest floor.
        elevation = (high - floor_z) / span
        rows.append({
            "map": path.stem.upper(),
            "sector": sector_id,
            "context": {
                "area": _band(area, AREA_BANDS),
                "height": _band(height, HEIGHT_BANDS),
                "sky": bool(int(fields["ceiling_stat"]) & 1),
                "exits": _band(exits, EXIT_BANDS),
                "elevation": "upper" if elevation > 0.66 else ("lower" if elevation < 0.33 else "middle"),
            },
            "surfaces": surfaces[sector_id],
            "neighbours": sorted(n for n in graph.get(sector_id, ()) if n in playable),
        })
    return rows


def compare_predictors(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Four ways to guess a surface, scored against what the campaign painted.

    This is the part that decides *how* to use the tables below, and it is worth
    more than the tables. Conditioning on the space beats guessing the map's
    favourite tile, but neither comes close to simply looking at what the
    sector's neighbours are wearing.

    That is what a person does. They paint a region and change the finish where
    the space changes, so a tile is mostly inherited and occasionally decided.
    A generator that picks each sector's tile independently from a per-context
    table cannot produce that, however good the table is -- which is also why
    the per-context tile lists transfer so badly between episodes.
    """
    by_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_map[row["map"]].append(row)

    scores: dict[str, dict[str, list[float]]] = {
        name: defaultdict(list)
        for name in ("map_favourite", "context", "neighbours", "neighbours_in_context")
    }
    for _name, group in by_map.items():
        if len(group) < 40:
            continue
        surfaces = {row["sector"]: row["surfaces"] for row in group}
        context = {row["sector"]: _signature(row["context"], ("area", "height", "sky"))
                   for row in group}
        for role in ("wall", "floor", "ceiling"):
            marginal = Counter(row["surfaces"][role] for row in group)
            favourite = marginal.most_common(1)[0][0]
            per_context: dict[str, Counter] = defaultdict(Counter)
            for row in group:
                per_context[context[row["sector"]]][row["surfaces"][role]] += 1

            hits = {key: 0 for key in scores}
            for row in group:
                sector = row["sector"]
                actual = row["surfaces"][role]
                if actual == favourite:
                    hits["map_favourite"] += 1
                if per_context[context[sector]].most_common(1)[0][0] == actual:
                    hits["context"] += 1
                near = [surfaces[n][role] for n in row["neighbours"] if n in surfaces]
                if near and Counter(near).most_common(1)[0][0] == actual:
                    hits["neighbours"] += 1
                same = [surfaces[n][role] for n in row["neighbours"]
                        if n in surfaces and context.get(n) == context[sector]]
                if not same:
                    same = near
                if same and Counter(same).most_common(1)[0][0] == actual:
                    hits["neighbours_in_context"] += 1
            for key, value in hits.items():
                scores[key][role].append(value / len(group))

    return {
        "basis": "median over campaign maps of at least 40 playable sectors",
        "accuracy": {
            name: {role: round(statistics.median(values), 3)
                   for role, values in per_role.items()}
            for name, per_role in scores.items()
        },
        "reading": (
            "a surface is mostly inherited from what adjoins it and only "
            "occasionally decided; the space context modulates the decision "
            "rather than making it"
        ),
    }


def _dominant_wall(disk: Any, sector_id: int) -> int:
    fields = disk.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    tiles = Counter(
        int(disk.walls[index].fields["picnum"])
        for index in range(start, start + int(fields["wall_count"]))
    )
    return tiles.most_common(1)[0][0] if tiles else 0


def _signature(context: dict[str, Any], keys: tuple[str, ...]) -> str:
    return "|".join(f"{key}:{context[key]}" for key in keys)


def _entropy(counter: Counter) -> float:
    total = sum(counter.values())
    if not total:
        return 0.0
    return -sum((n / total) * math.log2(n / total) for n in counter.values() if n)


def _top(counter: Counter, limit: int) -> list[dict[str, Any]]:
    total = sum(counter.values())
    return [
        {"tile": tile, "count": count, "share": round(count / total, 3)}
        for tile, count in counter.most_common(limit)
    ]


def build(rows: list[dict[str, Any]], keys: tuple[str, ...], *, limit: int,
          min_examples: int) -> dict[str, Any]:
    fit = [r for r in rows if CAMPAIGN.match(r["map"]) and CAMPAIGN.match(r["map"]).group(1) in FIT_EPISODES]
    held = [r for r in rows if r not in fit]

    def group(source: list[dict[str, Any]]) -> dict[str, dict[str, Counter]]:
        out: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
        for row in source:
            key = _signature(row["context"], keys)
            for role, tile in row["surfaces"].items():
                out[key][role][tile] += 1
        return out

    fitted, held_out = group(fit), group(held)
    marginal: dict[str, Counter] = defaultdict(Counter)
    for row in fit:
        for role, tile in row["surfaces"].items():
            marginal[role][tile] += 1

    contexts = []
    for key in sorted(fitted, key=lambda k: -sum(fitted[k]["floor"].values())):
        examples = sum(fitted[key]["floor"].values())
        if examples < min_examples:
            continue
        record: dict[str, Any] = {"context": key, "fit_examples": examples,
                                  "held_out_examples": sum(held_out.get(key, {}).get("floor", Counter()).values())}
        for role in ("wall", "floor", "ceiling"):
            counter = fitted[key][role]
            record[role] = {
                "top": _top(counter, limit),
                # How much narrower the choice becomes once the context is known.
                # A context that does not reduce the entropy is not worth having.
                "bits_saved": round(_entropy(marginal[role]) - _entropy(counter), 2),
            }
            other = held_out.get(key, {}).get(role)
            if other:
                fitted_top = {item["tile"] for item in record[role]["top"]}
                agree = sum(n for tile, n in other.items() if tile in fitted_top)
                record[role]["held_out_top_share"] = round(agree / sum(other.values()), 3)
        contexts.append(record)

    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "conditioned_on": list(keys),
        "bands": {
            "area_player_areas": [name for _limit, name in AREA_BANDS],
            "height_player_heights": [name for _limit, name in HEIGHT_BANDS],
            "exits": [name for _limit, name in EXIT_BANDS],
        },
        "fit_episodes": list(FIT_EPISODES),
        "fit_sectors": len(fit),
        "held_out_sectors": len(held),
        "contexts": contexts,
        "marginal": {role: _top(counter, limit) for role, counter in marginal.items()},
        "predictors": compare_predictors(rows),
        "reading_guide": [
            "read `predictors` before the tables: it says how much of a surface "
            "choice each kind of evidence actually explains",
            "the per-context tile lists are within-map guidance; tile identity is "
            "episode-specific, so held_out_top_share is low by nature and is not a "
            "defect of the conditioning",
            "bits_saved is how much the context narrows the choice against the "
            "whole-corpus distribution; a context near zero is not worth asking about",
            "held_out_top_share is the fraction of episode 4 and 6 sectors in the "
            "same context painted with a tile the fitted top list already named",
            "a share is what the campaign did, never what a level must do",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--keys", default="area,height,sky",
                        help="comma-separated context keys to condition on")
    parser.add_argument("--limit", type=int, default=6, help="tiles listed per role")
    parser.add_argument("--min-examples", type=int, default=12)
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if name in seen or not CAMPAIGN.match(name):
            continue
        seen.add(name)
        try:
            rows.extend(observe_map(pathlib.Path(path)))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")

    keys = tuple(k.strip() for k in args.keys.split(",") if k.strip())
    document = build(rows, keys, limit=args.limit, min_examples=args.min_examples)
    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "maps": len(seen),
        "sectors": len(rows),
        "conditioned_on": list(keys),
        "contexts": len(document["contexts"]),
        "output": args.output,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
