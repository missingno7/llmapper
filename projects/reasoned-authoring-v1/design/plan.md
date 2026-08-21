# Design plan and what actually happened

Replay everything:

```text
python -m experiments.monastery_pilot v0 v1 v2 v3 --comparison \
  --nblood reference/blood/nblood.exe --game-dir reference/blood \
  --grace-seconds 14 --startup-timeout 45
```

Without local game data the same command still runs; engine gates report
`skipped` and corpus percentiles report `null`.

## Iterations

- [x] **Precedents** — six bounded consultations of original maps frozen in
      `references/precedent-packet.json`, plus three candidates rejected on
      inspection (two degenerate sectors that a detector ranked first, and one
      mined tile role that disagrees with the rendered tile).
- [x] **v0 blockout** — hierarchy, containment, connectivity, scale, spine.
      Two coarse material sets, five sprites. All gates pass.
      *Finding:* arrival, courtyard and gallery collapse into one derived
      perceptual space; the crypt is one room at the end of a six-sector stair;
      the chapel is an empty box.
- [x] **v1 spatial revision** — gatehouse and two gallery arches as real
      thresholds; stairs 16 → 10 and rooms 10 → 15; chapel aisles and apse; crypt
      reliquary and cistern. Derived spaces 9 → 14, discrepancies 1 → 0.
      *Finding:* every ceiling renders as a black void; three assemblies are
      finished identically; the level is undecorated.
- [x] **v2 material revision** — one dominant surface triple per assembly,
      ceilings chosen by appearance as well as corpus count, coursed courtyard
      masonry, 51 decorations attached to architectural roles. Geometry and
      shading held constant, and the hierarchy evidence did not move.
      *Finding, from the project owner:* still mostly rectangular, ceilings too
      low. Adding corpus-relative scale and shape to the packet proved both.
- [x] **v3 scale and shape** — ceilings set from corpus percentiles per
      footprint; chamfers and non-45-degree facets on nine outlines; splayed
      gatehouse, radial chancel, octagonal planter; sprite repeats derived from
      tile pixels and a target height. Oversized decorations 18 → 0.
      *Remaining:* orientation variety.

## Stopping condition

Stopped at v5. v3 stopped because segmented-arc authoring had no constructor;
mining 1473 arc chains from 41 campaign maps produced one, and v5 spent it,
which took the metric v3 named as its bottleneck from the 0th percentile to
above the corpus minimum.

What is left on the shape axis is a limit of the measurement rather than of the
level: rectangular sector fraction stays at the corpus maximum because it counts
sectors, and a level whose large rooms are curved and whose stair treads and door
volumes are boxes scores the same as a grid. Moving it would mean curving stair
treads. The bottleneck is no longer visual.

See [`../reports/comparison.md`](../reports/comparison.md) for the full
cross-iteration evidence and the accounting of what is verified, derived,
interpreted, and unknown.
