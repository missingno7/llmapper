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

## BB2 experiment outputs

- [BB2 understanding (prose)](../reports/BB2-understanding.md)
- [BB2 understanding (structured)](../reports/BB2-understanding.json)
- Semantic roundtrip (prose → independent MAP):
  [pre-unblinding](../reports/BB2-reconstruction-preblind.md),
  [comparison](../reports/BB2-reconstruction-comparison.md),
  [information loss](../reports/BB2-reconstruction-gaps.md)

The prose is the reconstruction bottleneck. It must not smuggle the MAP.

### Reconstruction lesson

A source-blind builder can produce a coherent Blood DM compound from the
prose (mode, height contrast, flags, gated prizes, water Tesla, spawn
concealment). Pairwise 2D spawn sight is an insufficient *only* visibility
target: optimizing it carved alcoves and hid the hunting-ground spawns the
same document also described. The next cheap sensors are spawn-neighborhood
exposure, a coarse building-mass sketch, and route-level sight samples —
not a combat simulator.
