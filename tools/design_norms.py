"""Measure the Blood campaign, then measure a candidate level against it.

.. code-block:: bash

    python -m tools.design_norms --corpus maps/blood -o knowledge/blood/design/norms-v1.json
    python -m tools.design_norms --against projects/.../candidate-v5.MAP \
        --norms knowledge/blood/design/norms-v1.json

The norms are the *observed range* of each measurement across the 43 campaign
maps, not a target.  Blood levels differ enormously -- E1M1 and E4M8 agree on
almost nothing -- so a candidate sitting outside the median is uninteresting.
What is interesting is a candidate outside the range that **every** campaign map
occupies, because that is an axis the designers never varied.

The report therefore ranks findings by how far outside the observed range a
candidate sits, and says which way. It does not produce a score: the whole point
is to hand back a list of specific, separable things to look at.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
from typing import Any

from bloodmap.format import read_map
from bloodmap.level_profile import flatten, level_profile

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

#: Metrics where being *below* the campaign range is the interesting direction
#: and being above is not a defect (a level may legitimately be huge).
LOWER_IS_SUSPECT = {
    "topology.loops_per_100_sectors",
    "topology.mean_degree",
    "shape.area_iqr_ratio",
    "shape.height_iqr_ratio",
    "shape.distinct_floor_levels",
    "materials.wall_tiles",
    "materials.floor_tiles",
    "population.dudes",
    "population.distinct_dude_types",
    "population.pickups",
    "mechanisms.moving_sectors",
    "mechanisms.distinct_moving_types",
    "progression.keys_placed",
}


#: Metrics that count things rather than measure proportions. The campaign holds
#: them in a narrow band only because its 43 maps are all roughly one size, so
#: they rank as consensus axes and then read as failures on any level built to a
#: different scale -- which is a statement about the level's size and nothing
#: else. The monastery sits at 26.0 pickups and 16.0 weapons per 100 sectors,
#: both inside the campaign's own rates, while failing `population.pickups` by a
#: factor of five purely for being a sixth as large.
#:
#: They stay in `metrics`, because the count is a real fact about the campaign.
#: They are kept out of `consensus`, because consensus is the list a level is
#: judged against and a raw count cannot judge one.
SIZE_DEPENDENT = {
    "scale.sectors",
    "scale.walls",
    "scale.sprites",
    "scale.playable_sectors",
    "population.dudes",
    "population.pickups",
    "population.items",
    "population.weapons_and_ammo",
    "materials.wall_tiles",
    "materials.floor_tiles",
    "mechanisms.moving_sectors",
    "water.underwater_sectors",
    "water.pool_pairs",
}


def corpus_profiles(directory: pathlib.Path, *, pattern: re.Pattern[str]) -> list[dict[str, Any]]:
    profiles = []
    seen: set[str] = set()
    for path in sorted(glob.glob(str(directory / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if name in seen or not pattern.match(name):
            continue
        seen.add(name)
        try:
            profiles.append(level_profile(read_map(path), name=name))
        except Exception as error:  # a map we cannot read is not a norm
            print(f"skipped {name}: {type(error).__name__}: {error}")
    return profiles


def build_norms(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    flats = [flatten(p) for p in profiles]
    keys = sorted({k for f in flats for k in f})
    norms: dict[str, Any] = {}
    for key in keys:
        values = sorted(f[key] for f in flats if key in f)
        if not values:
            continue
        norms[key] = {
            "n": len(values),
            "min": values[0],
            "max": values[-1],
            "median": statistics.median(values),
            "q1": values[len(values) // 4],
            "q3": values[3 * len(values) // 4],
        }
    # Which axes the designers actually agreed on. A metric the campaign holds
    # within a narrow band across 43 levels of wildly different themes is a
    # convention; one that ranges over an order of magnitude is a free choice.
    # Only the first kind makes "outside the range" mean anything, so the
    # ranking is part of the artifact rather than something a reader has to
    # rederive.
    consensus = []
    for key, norm in norms.items():
        median = norm["median"]
        if not median or key in SIZE_DEPENDENT:
            continue
        consensus.append({
            "metric": key,
            "q1": norm["q1"],
            "median": median,
            "q3": norm["q3"],
            "iqr_over_median": round((norm["q3"] - norm["q1"]) / abs(median), 2),
        })
    consensus.sort(key=lambda item: item["iqr_over_median"])

    return {
        "$schema": "llmapper.blood-design-norms",
        "schema_version": 1,
        "maps": [p["name"] for p in profiles],
        "map_count": len(profiles),
        "consensus": consensus,
        "metrics": norms,
        "limitations": [
            "the range is what the campaign happens to contain, not a rule",
            "a candidate inside every range can still be a bad level; these are "
            "necessary conditions at best",
            "off-map geometry is excluded, so switch closets and author "
            "signatures do not move any statistic",
        ],
    }


def compare(profile: dict[str, Any], norms: dict[str, Any]) -> dict[str, Any]:
    flat = flatten(profile)
    findings = []
    for key, value in sorted(flat.items()):
        norm = norms["metrics"].get(key)
        if not norm:
            continue
        low, high = norm["min"], norm["max"]
        if low <= value <= high:
            continue
        below = value < low
        # Distance outside the range, scaled by the range's own width, so a
        # metric that the campaign varies a lot has to miss by a lot to rank.
        width = high - low
        if width > 0:
            severity = (low - value) / width if below else (value - high) / width
        else:
            severity = 1.0
        findings.append({
            "metric": key,
            "value": value,
            "campaign_min": low,
            "campaign_max": high,
            "campaign_median": norm["median"],
            "direction": "below" if below else "above",
            "severity": round(severity, 2),
            "suspect": below and key in LOWER_IS_SUSPECT,
        })
    findings.sort(key=lambda f: (not f["suspect"], -f["severity"]))
    return {
        "$schema": "llmapper.blood-design-comparison",
        "schema_version": 1,
        "name": profile.get("name", ""),
        "compared_against": norms.get("map_count", 0),
        "metrics_checked": len([k for k in flat if k in norms["metrics"]]),
        "outside_campaign_range": len(findings),
        "findings": findings,
        "profile": profile,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", help="directory of Blood MAPs to build norms from")
    parser.add_argument("--pattern", default=CAMPAIGN.pattern,
                        help="regex a map stem must match to count as corpus")
    parser.add_argument("--against", help="a candidate MAP to compare")
    parser.add_argument("--norms", help="an existing norms document to compare against")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    norms = None
    if args.corpus:
        profiles = corpus_profiles(pathlib.Path(args.corpus), pattern=re.compile(args.pattern))
        if not profiles:
            parser.error("no maps matched")
        norms = build_norms(profiles)
    elif args.norms:
        norms = json.loads(pathlib.Path(args.norms).read_text(encoding="utf-8"))

    if args.against:
        if norms is None:
            parser.error("comparing needs --corpus or --norms")
        candidate = level_profile(read_map(args.against), name=pathlib.Path(args.against).stem)
        result = compare(candidate, norms)
        summary = {
            "name": result["name"],
            "compared_against": result["compared_against"],
            "metrics_checked": result["metrics_checked"],
            "outside_campaign_range": result["outside_campaign_range"],
            "top": [
                {k: f[k] for k in ("metric", "value", "campaign_min", "campaign_median", "direction")}
                for f in result["findings"][:10]
            ],
        }
    else:
        if norms is None:
            parser.error("give --corpus, or --norms with --against")
        result = norms
        summary = {"maps": norms["map_count"], "metrics": len(norms["metrics"])}

    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        summary["output"] = str(out)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
