# Map understanding sensors

These sensors exist because reading one real Blood deathmatch map (`BB2.MAP`)
required names, inventories, and geometric sight that `analyze-space` did not
provide. They are general. Nothing here is hardcoded to BB2.

## Type catalog

`bloodmap.blood_types.classify(kind, type_id)` maps Blood sector/wall/sprite
types, commands, and reserved channels to NBlood names.

Unknown IDs stay `known: false`. Type 710 is **Ambient SFX**: it is in the
Blood map editor list and is processed by `asound.cpp` on `kStatAmbience`, but
it is not a named constant in `common_game.h` (the gap between 709 and 711).

```text
python -m bloodmap contents maps/blood/BB2.MAP --mechanisms --multiplayer
```

## Geometric sight

`analyze-space` visibility remains **direct-portal candidates**. That is not
line of sight.

`bloodmap.sight` casts 2D XY rays against occluding walls:

- one-sided walls occlude
- unmasked blocking / hitscan walls occlude
- masked walls and open portals do not
- height, slopes, sprites, and lighting are ignored

```text
python -m bloodmap sightline maps/blood/BB2.MAP --spawns --multiplayer-only
python -m bloodmap sightline maps/blood/BB2.MAP --from-x 0 --from-y 0 --to-x 1024 --to-y 0
```

## Contents / multiplayer layout

`inventory_map` classifies starts, pickups, movers, sounds, and unknown types.
`explain_mechanisms` lists every XSECTOR/XWALL/special sprite with trigger
flags and Z off/on deltas. It does not tick NBlood.
`multiplayer_layout` adds spawn-to-spawn 2D sight and nearest-resource
distances in player-widths, without claiming competitive balance.

## Spawn-neighborhood exposure

Pairwise spawn sight cannot tell a hunting-ground alcove from a closet.
`spawn_neighborhood_report` measures, for each start, spawn-sector area,
reachable area within 16 player-widths, immediate portal choices, hops into
the largest connected sky-parallax component, max/median 2D sight, and the
fraction of rays that sample that component. It does not assign closet/field
labels.

```text
python -m bloodmap spawn-neighborhood MAP --multiplayer-only
```

## Route exposure

`route_exposure_report` samples 2D sight and sky/cover along the shortest
at-rest path from each start to the largest sky sector. It is not a player
simulator. The point is to see whether leaving a spawn immediately occupies a
broad field or travels enclosed corridors first.

```text
python -m bloodmap route-exposure MAP --multiplayer-only
```

## Architectural morphology

`analyze_morphology` measures wall-orientation bins, orthogonal/diagonal
length fractions, rectangularity, convexity, vertex counts, chamfer-like
corners, straight-run lengths, and segmented-arc chain candidates. It is not
a room detector and it does not claim Blood maps must use diagonals.

```text
python -m bloodmap morphology MAP
```

## Bundled understanding packet

```text
python -m bloodmap understand MAP --multiplayer-only -o work/foo-understand.json
```

Freezes the sensors above (plus contents, player-space sky/covered, spatial
summary) into one packet. Prose interpretation stays outside the packet.

```text
python -m bloodmap understand MAP --multiplayer-only \
  --patterns knowledge/blood/design/catalog-v1.json -o work/foo-understand.json
```

`--patterns` attaches overlapping catalog hypotheses. It does not name rooms.
See [design-pattern-discovery.md](design-pattern-discovery.md).

## Single-player progression

`analyze-space` rest-walkability is not allowed progress. Keys, RX Z-motion,
push motion, and exit channels 4/5 are a separate graph:

```text
python -m bloodmap progression maps/blood/E2M2.MAP -o reports/E2M2-progression.json
```

Object-to-wall attachment is mined separately (`placement-mine`). See
[single-player-understanding.md](single-player-understanding.md) and
[object-placement.md](object-placement.md).

## Semantic Level Roundtrip

A reusable benchmark, not a scorer:

```text
Map A
  → independent understanding (prose + understand packet)
  → blind construction of Map B
  → independent understanding of Map B
  → multidimensional comparison of claims
```

The invariant is `Understand(A) ≈ Understand(B)` in design meaning, not
geometric identity. Do not emit a single similarity number. Comparison
classes: PRESERVED, APPROXIMATELY PRESERVED, LOST, EXAGGERATED, INVERTED,
NEW, UNMEASURABLE.

The first instance is BB2:

- [BB2 understanding](../reports/BB2-understanding.md)
- [reconstruction understanding](../reports/BB2-reconstruction-understanding.md)
- [semantic roundtrip](../reports/BB2-semantic-roundtrip.md)
- [revision plan](../reports/BB2-semantic-revision-plan.md)
- [v2 candidate understanding](../reports/BB2-reconstruction-v2-understanding.md)
- [v2 comparison](../reports/BB2-semantic-roundtrip-v2.md)
- [v2 geometry audit](../reports/BB2-v2-geometry-audit.md)
- [v3 candidate understanding](../reports/BB2-reconstruction-v3-understanding.md)
- [v3 comparison](../reports/BB2-semantic-roundtrip-v3.md)
- [BB6 pattern-aware understanding](../reports/BB6-understanding.md)
- [BB6 semantic roundtrip](../reports/BB6-semantic-roundtrip.md)

Order is mandatory: freeze the candidate reading **before** opening the
target description.

## BB2 experiment outputs

- [BB2 understanding (prose)](../reports/BB2-understanding.md)
- [BB2 understanding (structured)](../reports/BB2-understanding.json)
- Semantic roundtrip:
  [v1 candidate understanding](../reports/BB2-reconstruction-understanding.md),
  [v1 comparison](../reports/BB2-semantic-roundtrip.md),
  [v2 candidate understanding](../reports/BB2-reconstruction-v2-understanding.md),
  [v2 comparison](../reports/BB2-semantic-roundtrip-v2.md),
  [v2 geometry audit](../reports/BB2-v2-geometry-audit.md),
  [v3 candidate understanding](../reports/BB2-reconstruction-v3-understanding.md),
  [v3 comparison](../reports/BB2-semantic-roundtrip-v3.md),
  [revision plan](../reports/BB2-semantic-revision-plan.md),
  first reconstruction notes:
  [pre-unblinding](../reports/BB2-reconstruction-preblind.md),
  [comparison](../reports/BB2-reconstruction-comparison.md),
  [information loss](../reports/BB2-reconstruction-gaps.md)

The prose is the reconstruction bottleneck. It must not smuggle the MAP.

### Reconstruction lesson

A source-blind builder can produce a coherent Blood DM compound from the
prose (mode, height contrast, flags, gated prizes, water Tesla, spawn
concealment). Pairwise 2D spawn sight is an insufficient *only* visibility
target: optimizing it carved alcoves and hid the hunting-ground spawns the
same document also described. Spawn-neighborhood exposure, route exposure, and
architectural morphology are the sensors that gap justified. See the Semantic
Level Roundtrip section above.
