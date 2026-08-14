# Architecture and invariants

## Purpose

`bloodmap` is a binary-first foundation for future Blood level tooling. Its core
job is not generation: it is to make every byte of a supported map explainable,
editable, reconstructable, and testable before higher-level composition is trusted.

```text
Blood MAP bytes
    -> explicit parser
    -> DiskMap (lossless disk truth)
    -> LevelIR (canonical authoring form)
    -> DiskMap
    -> explicit writer + CRC
    -> Blood MAP bytes
```

Derived geometry, trigger graphs, statistics, renderings, and future semantic
analysis observe the IR. They are never authoritative serialized state.

## Layer 1: DiskMap

`DiskMap` mirrors the supported file organization without relying on native C/C++
layout. It retains:

- signature and exact format version;
- all main- and extra-header fields;
- bounded reserved header regions;
- sky offsets and revision metadata;
- every Build sector, wall, and sprite field;
- every known packed XSECTOR, XWALL, and XSPRITE field;
- original indices and redundant/stale disk values;
- the four-byte XSPRITE tail that NBlood explicitly skips;
- source CRC and size as provenance metadata.

The complete source blob is never stored. `encode_map` reconstructs all content and
computes a new CRC from the result. Mutation tests prove that changed model values
reach the written file.

## Layer 2: LevelIR

`LevelIR` is the stable, JSON-serializable authoring contract. Schema version 1
preserves all DiskMap information while exposing IDs, player start, geometry,
visual fields, and named Blood trigger properties. Conversion in both directions
must remain lossless for unchanged data.

Schema evolution rules:

1. Never silently reinterpret an existing field.
2. Add neutral names when semantics are uncertain.
3. Increment the schema version for incompatible shape or meaning changes.
4. Provide an explicit migration before removing or renaming serialized fields.
5. Keep disk-only preservation data structurally local to the owning object.

## Validation boundary

Validation distinguishes engine-breaking structure from unusual but accepted map
techniques.

Hard errors include invalid ranges, open loops, out-of-range indices, inconsistent
extra ownership, invalid starts, and impossible portal references. Semantic warnings
include corpus-proven constructs that Build accepts, such as the original E3M5
non-reciprocal portal and E6M7 two-wall sector.

The parser does not normalize or repair data. In particular, signed sprite angles
and stale redundant extended-record owner fields are preserved exactly.

## Derived services

- Geometry view: sector bounds, centroid, adjacency, portals, heights, and sprites.
- Channel graph: TX objects, commands, trigger edges, and RX objects by channel.
- Statistics: dimensions, object/type/tile/channel/key/command usage and trigger
  combinations.
- SVG renderer: deterministic diagnostic geometry, portals, IDs, sprites, player
  start, and selection highlighting.

These services can be recomputed at any time and must not be needed for roundtrip.

## Transform contract

Transformations operate on `LevelIR`, convert back to `DiskMap`, write, reparse,
and validate. They may change only fields whose semantics are verified. Translation
and quarter-turn rotation are the first operations because their expected results
are objectively testable.

Future extraction and composition must use explicit index/channel remapping. Raw
array concatenation is forbidden.
