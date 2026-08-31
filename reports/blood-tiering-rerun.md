# Re-running the tier classifier through the corpus registry

PR #2 is the generator of `maps/blood/tiered/`. Until now only its output
lived here, carrying absolute paths from another checkout. This is the
re-run after the refactor, against the assignment Phase 0a recovered from
that output by content hash.

```text
python -m bloodmap corpus-tier --maps maps/blood --population community \
  --view reference --health-report reports/blood-community-corpus-health.json \
  --output-directory work/tier-rerun/tiered \
  --manifest maps/blood/tiered/manifest-v2.json \
  --summary  maps/blood/tiered/summary-v2.json --workers 4
```

The tier metadata itself is local-only and not committed; only this
comparison is. The regenerated manifest was written alongside the existing
one as `manifest-v2.json` rather than over it -- the old tree is the owner's
data and the comparison below depends on being able to read both.

## What the run covered

```text
community population                     1498
skipped by the native losslessness gate    37
tiered                                   1461
```

Every map is accounted for. The health report was generated when the
population was 1500; two maps have left the directory since, one of them a
gate failure (`community/chronicles1/ZQUEST.MAP`), which is why 38 recorded
failures produce 37 skips. Skipping is fail-closed: a heuristic that scores
a file the parser could not round-trip is scoring its own parse errors.

## Against the Phase 0a hash-based attach

```text
community maps in both views   1461
  same tier                    1220  84%
  moved                          85  6%
  previously untiered           156  11%
```

**84% agree.** The disagreements are worth reading separately, because they
have two different causes and only one of them is a change of opinion.

### The moves are adjacent-tier churn

```text
A->S                                  30
S->A                                  28
B->A                                  13
A->B                                   9
S->B                                   3
```

Almost all of it is S against A in both directions, plus a little A/B. No
map moves more than one tier. That is what a boundary looks like when the
reference population shifts slightly: the old run scored against a
`maps/canonical` directory of 100 maps, this one against the `reference`
view of 102 (campaign + curated), and maps sitting on the S/A line move.
The tiers are not stable to that, which is a fact about tiers rather than a
defect -- and the reason `07_...md` says a tier is navigation metadata and
never an evidence weight.

### The 156 previously untiered are the interesting number

```text
S                   78
A                   41
B                   25
multiplayer          6
C                    2
mechanism            2
questionable         2
```

Phase 0a could not read a tier for these out of the old tree, and it
declined to guess. The cause is now clear, and it was a defect in the
generator rather than in the join:

```text
filenames the old flat tier tree put in more than one tier directory   120
community maps carrying one of those names                            128
of those, left untiered by the Phase 0a hash join                      128  (100%)
all of them now carry a tier                                          yes
```

The old tier tree flattened every map to `tiered/<TIER>/<FILENAME>`. Two
community maps that share a name -- `community/CRYPT.MAP` and
`community/chronicles1/CRYPT.MAP` are one of 120 such pairs -- overwrote
each other, so one file ended up standing for two maps and its hash
appeared under two tiers. A hash join has to refuse that, and Phase 0a did.

The refactor keeps the source's shape below its population directory, so
`community/chronicles1/CRYPT.MAP` now lands at `S/chronicles1/CRYPT.MAP`
and nothing overwrites anything. **Two maps that share a name are two
maps.** The remaining 28 newly-tiered maps were simply not present in the
old tree at all.

## Counts, old against new

| classification | old | new | delta |
| --- | ---: | ---: | ---: |
| `A` | 170 | 182 | +12 |
| `B` | 174 | 172 | -2 |
| `C` | 81 | 52 | -29 |
| `S` | 332 | 373 | +41 |
| `mechanism` | 12 | 12 | +0 |
| `multiplayer` | 539 | 538 | -1 |
| `questionable` | 153 | 132 | -21 |

`C` falls by 29 and `questionable` by 21, and both are largely the
degenerate-sector fix from the first commit of this series: a map whose
sensors used to stop at the first two-walled sector was measured as partial
evidence and tiered down. `bloodbath` and `mechanism` are unchanged to
within one map, which is the expected behaviour of rules that key on
player starts and mechanism counts rather than on the reference
distribution.

## What the refactor removed

```text
records carrying an absolute path      0     (of 1461, checked for ':' and a leading '/')
records carrying a confidence scalar   0
records carrying a rule trace          874
```

874 rather than 1461 because the bloodbath, mechanism and sensor-failure
branches return before the dimension rules run; those records carry their
evidence as reasons instead. The confidence formula
(`0.58 + min(0.25, |strong − weak| × 0.035) + 0.08`) is gone: it read as a
probability and measured nothing.

## Limitations

- A tier is navigation and sampling metadata. It is not an evidence weight,
  and the 6% of maps that moved on a small change of reference population
  are the demonstration of why.
- The reference view is campaign + curated. Curated is the owner's
  hand-picked precedent, so the yardstick is part authoritative and part
  vetted precedent, and the manifest records which.
- `quality_score` remains a declared rubric with its components exposed. It
  is not a measured quantity either, and unlike the confidence scalar it
  says so; a later pass should decide whether it earns its place.
- The regenerated tier *tree* was written to `work/tier-rerun/tiered` rather
  than over `maps/blood/tiered/`, to avoid destroying the owner's copy. One
  command rebuilds it wherever it is wanted.

