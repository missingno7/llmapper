# Hierarchical level decompiler

`bloodmap.decompiler` is the first single-level source-reconstruction pilot. It
joins existing exact and derived layers rather than replacing them:

```text
Blood MAP -> LevelIR (authoritative)
          -> BuildIR / spatial evidence (derived)
          -> LevelSource primary hierarchy (reviewable)
          -> JSON and executable Python
```

## Current-component audit

| Need | Reused component | Pilot responsibility |
| --- | --- | --- |
| Exact native truth | `DiskMap` and `LevelIR` | Embed the complete `LevelIR`; compile only this field |
| Geometry/topology evidence | `BuildIR` and `analyze_spatial` | Cite portal components and perceptual candidates |
| Player-relative scale | `player_space` profile | Summarize footprint, bounds, and clearance per node |
| Materials/ART identity | native `picnum` usage and `materials` separation rules | Expose role-specific tile use; leave aliases/meaning unreviewed |
| Local composition | `LevelIR` fragments and `composition` | Preserve source refs so a reviewed node can later become a slice/fragment |
| Searchable precedent memory | `design-index` and workspace `LevelSlice` | Emit inspectable nodes; cross-map node indexing remains next work |
| Authored validation | geometry audit and native validation | Validate the exact rebuild; generic-plus-residual experiments remain next work |
| Engine testing | NBlood oracle/bot infrastructure | Deliberately not invoked or modified by this geometry-first pilot |

## Knowledge boundaries

A `llmapper.level-source` document has four important parts:

- `exact_level_ir` is the only compilation authority. Hierarchy edits cannot
  silently rewrite native sectors, walls, sprites, extended records, or channels.
- `hierarchy.nodes` is the primary readable tree. Assemblies use persistent
  portal topology; spaces use perceptual-continuity candidates within those
  assemblies. Ungrouped sectors remain explicit reviewable singleton spaces.
- `hierarchy.relations` retains internal and cross-space portals and overlapping
  vertical relationships with exact wall/sector evidence.
- `hierarchy.alternative_candidates` preserves all spatial hypotheses, including
  navigation, material, mechanism, and vertical views. They are not forced into
  the primary tree.

Every primary node records exact sector/wall/sprite IDs. Level nodes cover every
native object, and primary spaces partition every sector exactly once. Validation
rejects missing, duplicate, out-of-range, or cyclic provenance.

Neutral names such as `space_001_004` are intentional. They make the Python
source navigable without claiming that a portal-continuity cluster is a lobby,
crypt, staircase, or garden. An LLM or human review can fill `interpretation`
with a semantic name, description, and confidence while retaining the evidence.

## Pilot commands

Decompile one original Blood level to the canonical document and a Python view:

```text
python -m bloodmap decompile maps/blood/E1M1.MAP \
  -o work/E1M1.level-source.json \
  --python work/E1M1.level-source.py
```

The Python file contains local build functions for the level, assemblies,
spaces, and sprite-detail groups. It also exposes `level_source()` so tooling can
recover the complete typed document.

Rebuild authoritative source truth:

```text
python -m bloodmap compile-source work/E1M1.level-source.json \
  -o work/E1M1.rebuilt.MAP
```

For unchanged source, this rebuild is byte-exact. Semantic hierarchy edits are
therefore safe annotations until a future explicit lowering step translates a
reviewed authoring operation into `LevelIR` geometry.

## What this proves and does not prove

The pilot proves that one complex native level can live in a versioned document
that is simultaneously lossless, hierarchical, evidence-backed, player-scaled,
asset-aware, and readable as Python. It creates the seam where an LLM can revise
decomposition without corrupting source truth.

It does not yet claim good semantic naming, a reusable staircase/alcove/shell
vocabulary, generic-plus-residual reconstruction, held-out abstraction quality,
or a cross-map node atlas. The next useful test is to have a reviewing agent name
and reorganize one level, then measure whether an authoring agent actually opens
and reuses those nodes instead of dropping back to raw sector emission.
