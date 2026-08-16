# Architecture and invariants

## Purpose

`llmapper` is a binary-first, game-neutral foundation for Build-engine level
tooling. Every supported native map must remain explainable, editable,
reconstructable, and independently testable before higher-level conversion or
generation is trusted.

```text
Blood bytes -> DiskMap -----\
                           BuildIR -> shared Build transforms / conversion
Duke bytes  -> DukeDiskMap-/

Doom WAD   -> DoomDiskMap -> SemanticLevel / SemanticMechanism
Blood/Duke natives also compile into that semantic layer when justified.

BuildIR -> Design Understanding sensors -> fingerprints / corpus retrieval
        -> multi-view spatial analysis -> overlapping hypotheses / context

Blood DiskMap <-> LevelIR -> fragments / composition / construction
Doom DiskMap  -> Blood LevelIR (one-way lowering)
```

`BuildIR` remains a Build-engine contract. Supporting Doom does not make it a
universal map IR. See [doom.md](doom.md).

Derived geometry, trigger graphs, differential evidence, statistics, renderings,
semantic annotations, and Design Understanding observations are never
authoritative serialized state.

## Design Understanding

`bloodmap.design` is a deterministic sensor layer over `BuildIR`. It measures
topology, space, architecture, visual proxies, and gameplay inventories for a
whole map or an explicitly selected set of sectors. Every fingerprint keeps
three kinds of knowledge separate:

- verified facts: exact object references, source game, and native counts;
- derived metrics: reproducible measurements such as portal degree, area,
  vertical range, repetition proxies, and enemy density;
- heuristic interpretations: soft statements such as branching, compression,
  vertical contrast, or structural rhythm.

Heuristics never mutate LevelIR or native disk data. They include their basis
and confidence, while `provenance.not_inferred` records questions the sensor
does not answer (for example material-family meaning or player intent).
`design-index` stores these grounded fingerprints for original Blood and Duke3D
maps, and `design-search` retrieves multi-dimensional similarities or explicitly
named soft motifs. Search results retain the fingerprint's sector, wall, sprite,
and mechanism evidence so an LLM can inspect the source rather than trust a
label. This is a sensory and retrieval layer, not a finite room taxonomy or a
procedural replacement for design judgment.

The next sensor layer, `bloodmap.spatial`, keeps geometry, static
traversability, portal-visibility candidates, vertical relationships, mechanism
memberships, progression candidates, and raw material continuity as separate
views. It does not create `level.rooms`. Instead it returns explicitly derived,
overlapping region hypotheses and selection context. See
[spatial-understanding.md](spatial-understanding.md).

`bloodmap.experience` adds bounded Level-0 probes over those views. It models a
declared `WorldState` separately from `PlayerKnowledge`, reports routes,
transitions, direct-portal visibility candidates, and static progression, and
never claims renderer-accurate perception. `bloodmap.workspace` persists the
brief, decisions, evidence claims, LevelSlice precedents, and observed design
episodes needed to reproduce an agent's work. See
[experience-atlas.md](experience-atlas.md).

`bloodmap.materials` measures ART appearance and original-map usage before any
semantic texture vocabulary exists. Clusters and co-occurrence relations stay
unlabeled until an offline review imports an INTERPRETED facet schema.
Blood now has a versioned review under `knowledge/blood/` (v1 → contradiction
pass → v2). Native IDs are never material semantics. See
[materials.md](materials.md) and [materials-discovery.md](materials-discovery.md).

`bloodmap.player_space` is a derived presentation over exact geometry. It
normalizes openings, clearances, footprints, and steps against a source-backed
player body, original-map percentiles, and neighbor ratios. It does not invent
rooms, replace native units, or make meters the primary abstraction. See
[player-space.md](player-space.md).

## Native disk models

`DiskMap` mirrors Blood v7, including encryption, CRC, packed extended records,
reserved header data, stale redundant values, and the opaque XSPRITE tail.
`DukeDiskMap` mirrors classic Duke v7's 20-byte header and fixed 40/32/44-byte
sector/wall/sprite records, plus any trailing bytes.

Neither object retains the complete source blob. Each writer reconstructs bytes
from decoded fields. Genuine mutation tests prove changed values reach the output.

## Shared BuildIR

`BuildIR` schema version 1 is the common contract. It gives the same names and
shape to player start, sectors, walls, sprites, portals, slopes, shade, palettes,
panning, repetition, and common Build tags. `source_game` and `map_version` make
the native context explicit.

The `native` extension is an opaque lossless adapter envelope. It preserves the
complete Blood `LevelIR` document or Duke-native fields needed for exact unchanged
reconstruction. Common-field edits are overlaid on that envelope when exporting
back to the source game. This deliberately favors proven preservation over an
early attempt to assign cross-game meanings to native tags.

Shared translation and quarter-turn rotation operate on `BuildIR`, so both games
use one geometry operation path. Blood-only absolute XSPRITE target coordinates
and XSECTOR motion destinations are kept coherent through the native adapter.

Schema rules:

1. Never silently reinterpret an existing field.
2. Keep uncertain semantics neutral or native.
3. Increment the schema version for incompatible changes.
4. Require explicit migrations for renamed or removed serialized fields.
5. Do not use native numeric tags as cross-game semantic equivalence.

## Blood LevelIR

`LevelIR` remains the stable, JSON-serializable Blood authoring contract. It owns
the mature Blood semantics: extended records, TX/RX channels, dependency closure,
room fragments, allocation, portal attachment, pathways, stairs, and scratch
construction. Existing Blood workflows therefore retain their stronger domain
model while neutral operations move to `BuildIR`.

## Validation boundaries

Shared validation checks engine-level topology and references without interpreting
game tags: object limits, sector wall ranges, wall loops, portal pairs, sprite
sectors, player start, and Build angles. Game-native validation then adds Blood or
Duke-specific requirements.

Validation distinguishes engine-breaking structure from accepted original-map
oddities. For example, Duke E2L6's portal-owner mismatch and Blood E3M5's
non-reciprocal portal are warnings rather than automatic repairs.

## Conversion boundary

Cross-game export is a new authored map, never a native roundtrip. It always emits
a fidelity report covering geometry, lighting, materials, entities, mechanisms,
validation, and known gameplay differences. Unsupported data is removed or
defaulted explicitly; it is never smuggled across by matching tag numbers.

The three policies are:

- `strict`: fail unless every required cross-game feature is verified;
- `semantic`: use the small evidence-backed mapping registry and report omissions;
- `geometry-only`: preserve neutral structure and remove gameplay semantics.

See [conversion.md](conversion.md) for measured normalization and current limits.

## Runtime oracles

The package has no engine dependency. Optional bounded harnesses load generated
maps in local NBlood and EDuke32 installations. They compare a known-good baseline
and candidate in isolated directories, require engine-specific initialization
markers and a healthy grace period, and report revisions, identities, and fatal
indicators. These are load/startup checks, not gameplay-equivalence proofs.
