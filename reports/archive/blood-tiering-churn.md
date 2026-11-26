# How much of a tier is the reference population?

The re-run that landed the tier classifier moved 6% of maps when the
reference changed by two maps. That looked like a boundary effect worth
bounding, so this is the deliberate version: tier the same 1461 community
maps twice, against two reference views that differ by half.

```text
python -m bloodmap corpus-tier --population community --view reference  ...
python -m bloodmap corpus-tier --population community --view original   ...
python -m bloodmap corpus-tier --compare <reference> <original> -o cmp.json
```

```text
reference   campaign + curated, both modes    102 maps
original    campaign only, both modes           52 maps
```

## Result

```text
community maps tiered by both   1461
  same tier                      1248   85.4%
  moved                           213   14.6%
  moved more than one step         12
```

**Halving the reference population moves 14.6% of the corpus.** That is
the number this experiment existed to get, and it is large enough to change
how a tier may be used.

## Which decisions are reference-sensitive, and which are not

```text
S              -> A                102
A              -> S                 35
A              -> B                 33
B              -> A                 31
S              -> B                 11
B              -> S                  1
```

Every move is inside {A, B, S}. **C, bloodbath, mechanism, questionable never move.**

That split is the useful part. The quality tiers are a comparison against a
distribution, so they move when the distribution moves. `bloodbath`,
`mechanism` and `questionable` are decided on absolute evidence -- player
starts, mechanism counts, sensor status -- and `C` is capped by an absolute
sector count. Those four are stable under a reference that changed by half.

Direction: the wider `reference` view produces **more** S (373 against 296)
and fewer A (182 against 247). Adding Death Wish and the other curated maps
widens the reference distribution, so a community map's percentiles look
less unusual and it clears the strong-dimension bar more often. A stricter,
campaign-only yardstick is not a *higher* bar in the direction one would
guess; it is a *narrower* one.

## The consequence, implemented

A tier is a comparison, so two tiers are comparable only if they were
compared against the same thing. Manifests now record a
`reference_fingerprint` -- one digest over the reference population's
content hashes -- next to the view name, because `reference` means whatever
`campaign + curated` held on the day and the corpus is edited in place.

```text
reference   reference  102 maps   2cbfabc4812d5348
original    original    52 maps   e6c260f332adbb61
```

`corpus-tier --compare` refuses across them:

```text
refusing to compare tier manifests scored against different reference
populations: reference (102 maps, 2cbfabc4812d) against original (52 maps,
e6c260f332ad). Measured churn between the reference and original views is
14.6%, so the difference would be the reference and not the maps.
```

The same manifest against itself reports 1461/1461 and 0 moved, so the
refusal is about the reference and not about refusing everything.

## What this licenses

- A tier orders a sampling queue. `07_...md` already said tiers are
  navigation metadata and never evidence weights; this puts a number on it.
  One in seven maps would carry a different letter under a defensible
  alternative yardstick.
- Any statement of the form "tier S maps do X" has to name the reference
  the tier was scored against, or it is a statement about the reference.
- `bloodbath`, `mechanism`, `questionable` and `C` may be relied on more
  heavily than S/A/B, because they did not move at all.

## Limitations

- Two reference views, not a sweep. This bounds the sensitivity; it does not
  characterise it.
- The two views nest (`original` is a subset of `reference`), so this is the
  effect of *adding curated precedent*, not of an arbitrary reference.
- Churn is measured on classification labels. A map that keeps its letter
  may still have moved a long way inside its percentile table.

