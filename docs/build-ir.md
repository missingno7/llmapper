# BuildIR: the shared authoring contract

`BuildIR` is the game-neutral, JSON-serializable view used when an operation should
work on both Blood and Duke3D. Its schema identifier is `llmapper.build-ir` and its
current schema version is 1.

## Document shape

```json
{
  "$schema": "llmapper.build-ir",
  "schema_version": 1,
  "source_game": "duke3d",
  "map_version": 7,
  "player_start": {"x": 0, "y": 0, "z": 0, "angle": 0, "sector": 0},
  "sectors": [{"id": 0, "fields": {}}],
  "walls": [{"id": 0, "fields": {}}],
  "sprites": [{"id": 0, "fields": {}}],
  "native": {"adapter": "duke-v7"},
  "semantic": {}
}
```

Sector fields include wall ownership, ceiling/floor Z, stat bits, tiles, slopes,
shade, palette, panning, visibility/fog, tags, and native extra index. Wall fields
include endpoints through `point2`, reciprocal portal references, stat bits,
tiles, shade/palette, repetition, panning, tags, and extra index. Sprite fields
include position, visual fields, sector/status/angle/owner, velocity components,
tags, and extra index.

Names follow common Build concepts: `lotag`, `hitag`, `x_velocity`, `fog_pal`, and
`blend`. Blood's differently named disk fields are projected into these neutral
slots without claiming that their numeric gameplay meanings match Duke's.

## Native extension

The `native` object is part of the lossless adapter contract, not an invitation to
edit opaque fields casually. It retains every source-game value required to
reconstruct an unchanged map exactly. On native export, common fields are overlaid
onto the preserved source records. Cross-game conversion does not copy this
extension to the other game.

## LLM workflow

```text
python -m bloodmap dump-build maps/duke3d/E1L1.MAP -o work/E1L1.build.json
# inspect or edit common fields in work/E1L1.build.json
python -m bloodmap build-build work/E1L1.build.json -o work/E1L1-edited.MAP
python -m bloodmap validate work/E1L1-edited.MAP
```

Prefer the high-level `translate` and `rotate` APIs over manually editing every
coordinate. For Blood room copying, trigger-aware dependency closure, connection,
and scratch construction, use `LevelIR`; those semantics have not yet been lifted
into the common layer.

## Invariants

- object IDs correspond to stable array indices within the document;
- sector wall ranges and `point2` loops must remain valid;
- reciprocal portals use both `next_wall` and `next_sector`;
- player and sprite sector references must be in range;
- native export requires object counts to agree with the native extension;
- a cross-game export always goes through an explicit conversion policy and emits
  a fidelity report.
