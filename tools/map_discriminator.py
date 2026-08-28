"""Could you tell this level from a Blood level, on the evidence available?

"Inside q1..q3 on most metrics" is a weak claim. A level can sit inside every
band one at a time and still be obviously synthetic, because what gives it away
is the *combination* -- rooms of campaign size joined in a way no campaign map
joins them, campaign lighting on a floor plan nothing in the game has.

So this asks the question the way it should be asked. Every map, campaign and
candidate alike, becomes one feature vector. Each is then scored against *the
others* -- leave-one-out, so a campaign map is never judged against itself -- and
the scores are ranked together. If the candidate's score sits inside the range
the campaign maps produce for each other, then on this evidence it is not
separable from them. If it sits outside, the features that put it there are
named, and those are the things to fix.

.. code-block:: bash

    python -m tools.map_discriminator --against projects/.../candidate-v5.MAP

The score is a robust one: per feature, the distance from the others' median in
units of their interquartile range, aggregated by taking a high percentile
rather than a mean. A level is given away by its worst few features, not by its
average one, so averaging is the wrong summary -- it lets a map with one absurd
property hide behind fifty ordinary ones.

What this cannot say: that a *player* could not tell. These are the properties
the project knows how to measure, and a level can match all of them and still
be dull to walk through. Passing is necessary and nowhere near sufficient.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
import tempfile
from typing import Any

from bloodmap.format import read_map
from bloodmap.level_profile import flatten, level_profile

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

#: Features that measure size rather than character. A level built to a
#: different scale is not thereby a fake one, and including these would score
#: every small map as synthetic no matter how it was made.
#: Anything that counts objects rather than describing their arrangement. A
#: rate, a share or a ratio belongs in the comparison; a total does not.
#:
#: Getting this list wrong is the easy way to make the whole exercise
#: meaningless. The first run of this tool put `topology.sectors` (50 against a
#: campaign median of 302), `topology.portals` and `topology.independent_loops`
#: among the candidate's worst deviations -- three of its top thirteen -- and
#: all three were saying the same uninteresting thing, that the level is
#: smaller. A discriminator that scores small maps as fakes has learned to
#: detect size, not authorship.
SIZE_FEATURES = frozenset({
    "scale.sectors", "scale.walls", "scale.sprites", "scale.playable_sectors",
    "population.dudes", "population.pickups", "population.items",
    "population.weapons_and_ammo", "materials.wall_tiles", "materials.floor_tiles",
    "materials.ceiling_tiles",
    "mechanisms.moving_sectors", "water.underwater_sectors", "water.pool_pairs",
    "progression.keys_placed", "progression.locked_objects",
    "progression.distinct_keys", "mechanisms.distinct_moving_types",
    "shape.distinct_floor_levels", "population.distinct_dude_types",
    "topology.sectors", "topology.portals", "topology.independent_loops",
    "topology.max_degree", "geometry.blocking_two_sided_walls",
    "shape.median_area",
})

#: The percentile of per-feature deviations used as a map's score. A level is
#: given away by its worst few properties.
SCORE_PERCENTILE = 0.90


def structural_features(path: str) -> dict[str, float]:
    profile = flatten(level_profile(read_map(path)))
    return {
        name: float(value) for name, value in profile.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        and name not in SIZE_FEATURES
    }


def visual_features(path: str, *, sample: int, art: str) -> dict[str, float]:
    from tools.mine_visual_norms import KINDS, frame_metrics, viewpoints
    from bloodmap.visual import ObservationRequest, run_observation

    poses = viewpoints(read_map(path), sample=sample)
    if not poses:
        return {}
    with tempfile.TemporaryDirectory() as work:
        manifest = run_observation(ObservationRequest(
            map_path=path, output_dir=work, resource_dir=art,
            viewpoints=tuple(poses)))
        data = manifest.data
    rows = [
        metrics for view in data.get("views", [])
        if view.get("status") == "ok"
        for metrics in [frame_metrics(view)] if metrics is not None
    ]
    if not rows:
        return {}
    out = {
        f"visual.composition.{kind}": statistics.median(r["composition"][kind] for r in rows)
        for kind in KINDS
    }
    for name in ("tile_variety", "depth", "contrast", "shade_spread"):
        out[f"visual.{name}"] = float(statistics.median(r[name] for r in rows))
    return out


def features_for(path: str, *, sample: int, art: str, visual: bool) -> dict[str, float]:
    out = structural_features(path)
    if visual:
        out.update(visual_features(path, sample=sample, art=art))
    return out


def _iqr(values: list[float]) -> float:
    ordered = sorted(values)
    if len(ordered) < 4:
        return 0.0
    q1 = ordered[len(ordered) // 4]
    q3 = ordered[3 * len(ordered) // 4]
    return q3 - q1


def deviations(target: dict[str, float],
               others: list[dict[str, float]]) -> list[tuple[str, float, float, float]]:
    """Per feature: (name, value, others' median, distance in IQRs)."""
    rows = []
    for name, value in sorted(target.items()):
        column = [other[name] for other in others if name in other]
        if len(column) < 8:
            continue
        median = statistics.median(column)
        spread = _iqr(column)
        if spread <= 0:
            # A feature the corpus never varies: any difference at all is total,
            # but an identical value must not count as infinitely normal either.
            distance = 0.0 if value == median else 4.0
        else:
            distance = abs(value - median) / spread
        rows.append((name, value, median, distance))
    return rows


def score(target: dict[str, float], others: list[dict[str, float]]) -> float:
    rows = deviations(target, others)
    if not rows:
        return 0.0
    distances = sorted(row[3] for row in rows)
    index = min(len(distances) - 1, int(SCORE_PERCENTILE * (len(distances) - 1)))
    return distances[index]


#: How close to the corpus median a feature has to be to count as "typical".
BLAND_THRESHOLD = 0.25


def blandness(target: dict[str, float], others: list[dict[str, float]]) -> float:
    """Share of features sitting almost exactly on the corpus median.

    The outlier score is one-sided: it asks whether anything sticks out, and a
    level fitted to the corpus passes it easily. But being *more typical than any
    real map* is its own tell. Every campaign map has idiosyncrasies -- one is
    unusually vertical, another unusually dark -- because it was built to be a
    place rather than to match a distribution. A level with no idiosyncrasies at
    all is the shape a fitted thing has.

    So this is the second half of the question, and the two are read together: a
    candidate should be inside the corpus range on *both*, not merely low on the
    first.
    """
    rows = deviations(target, others)
    if not rows:
        return 0.0
    return sum(1 for row in rows if row[3] <= BLAND_THRESHOLD) / len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--art", default="reference/blood")
    parser.add_argument("--against", required=True)
    parser.add_argument("--sample", type=int, default=24)
    parser.add_argument("--no-visual", action="store_true")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    visual = not args.no_visual
    corpus: dict[str, dict[str, float]] = {}
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name) or name in corpus:
            continue
        try:
            corpus[name] = features_for(path, sample=args.sample, art=args.art, visual=visual)
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")
    if len(corpus) < 10:
        print("not enough campaign maps to compare against")
        return 1

    names = sorted(corpus)
    ranked = []
    for name in names:
        others = [corpus[other] for other in names if other != name]
        ranked.append((score(corpus[name], others), name))
    ranked.sort()

    mine = features_for(args.against, sample=args.sample, art=args.art, visual=visual)
    my_score = score(mine, [corpus[name] for name in names])

    worst = ranked[-1][0]
    inside = my_score <= worst
    below = sum(1 for value, _ in ranked if value < my_score)

    print("campaign maps scored against each other (leave-one-out):")
    print("  best  %.2f  (%s)" % (ranked[0][0], ranked[0][1]))
    print("  median %.2f" % statistics.median(value for value, _ in ranked))
    print("  worst %.2f  (%s)" % (ranked[-1][0], ranked[-1][1]))
    print()
    print("candidate: %.2f  -- %s" % (
        my_score,
        "inside the campaign's own range, at rank %d of %d"
        % (below + 1, len(ranked) + 1) if inside
        else "OUTSIDE the campaign's own range (worse than every campaign map)"))
    print()

    bland_scores = sorted(
        blandness(corpus[name], [corpus[other] for other in names if other != name])
        for name in names)
    my_bland = blandness(mine, [corpus[name] for name in names])
    blander_than = sum(1 for value in bland_scores if value < my_bland)
    print("blandness -- share of features within %.2f IQR of the corpus median:"
          % BLAND_THRESHOLD)
    print("  campaign: min %.2f  median %.2f  max %.2f"
          % (bland_scores[0], statistics.median(bland_scores), bland_scores[-1]))
    print("  candidate: %.2f  -- blander than %d of %d campaign maps%s"
          % (my_bland, blander_than, len(bland_scores),
             "" if my_bland <= bland_scores[-1]
             else "  (BLANDER THAN ANY REAL MAP)"))
    print()
    rows = sorted(deviations(mine, [corpus[name] for name in names]),
                  key=lambda row: -row[3])
    print("%-40s %10s %10s %8s" % ("feature", "level", "campaign", "IQRs"))
    for name, value, median, distance in rows[:args.top]:
        print("%-40s %10.3f %10.3f %8.2f" % (name, value, median, distance))

    if args.output:
        pathlib.Path(args.output).write_text(json.dumps({
            "candidate": args.against,
            "score": round(my_score, 3),
            "blandness": round(my_bland, 3),
            "campaign_scores": {name: round(value, 3) for value, name in ranked},
            "deviations": [
                {"feature": n, "level": round(v, 4), "campaign_median": round(m, 4),
                 "iqrs": round(d, 3)}
                for n, v, m, d in rows
            ],
        }, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
