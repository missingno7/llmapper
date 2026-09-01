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
                         \-> LevelSource exact truth + reviewable hierarchy / Python
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
views. It does not create `level.rooms`. Geometric line of sight is a separate
probe in `bloodmap.sight` (2D XY rays vs occluding walls). Blood object types,
starts, pickups, and static mechanisms are named by `bloodmap.blood_types` and
`bloodmap.contents`. See [spatial-understanding.md](spatial-understanding.md)
and [map-understanding.md](map-understanding.md).

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

## Where a new fact belongs

Read this before adding a module. Every row is a module that already owns a
kind of fact; the question is which kind you have, not which module is
convenient.

| A fact about... | Belongs in | Not in |
| --- | --- | --- |
| what a native type *means* (`type 709 is kSoundSector`, and that it is never drawn) | `blood_types.py` | wherever you noticed it |
| whether the player can get to a sector, and what off-map geometry is for | `reachability.py` | a fresh flood fill |
| what a mechanism is made of and how its parts relate | `assembly.py` | a second grouping pass |
| how one dynamic family works in detail (doors, lifts) | `doors.py`, `mechanism.py` | `assembly.py`, which owns membership, not behaviour |
| a derived spatial view over sectors (adjacency, portals, loops) | `spatial.py` | recomputing from walls |
| an object-scale relation between a sprite, a wall and a sector | `relations.py` | `patterns.py` |
| a reduction of relations to a comparable key | `relations.py` (`context_signature`) | its consumers |
| where a corpus map came from, and which population it is | `patterns.py` (the corpus registry) | globbing a directory |
| a recurring unsigned signature family | `patterns.py` (`observe_*` + `_SIGNATURES`) | a new pipeline |
| what surrounds a labelled anchor, and whether that context means anything | `anchors.py` | `patterns.py` |
| an architectural structure candidate with parameters and residual (stairs, recesses) | `structures.py` | `relations.py` |
| which tile the renderer shows on which band of a wall (steps, mask, one-way) | `render_slots.py` | a `next_sector < 0` test in the consumer |
| a measured, versioned, citable design number | `knowledge/blood/design/*-vN.json` | a constant in the module that needed it |
| something an author should be able to *write* | a `vocabulary.py` / `prefab.py` constructor | the knowledge store |

Two directions, and they are not symmetric. A fact is **observed** into a
sensor module and, once it recurs and is understood, **promoted** into a
constructor. The promotion rule is in
[`knowledge/blood/design/README.md`](../knowledge/blood/design/README.md) and
requires recurrence, a known invariant, counterexamples, and a regression test
that can fail. Nothing goes the other way: an authoring constructor is never
evidence for anything, and generated maps are never evidence at all.

### The motivating example

`context_signature` reduces a relation document to a discrete key. It was
written inside `anchors.py`, because the anchor query was the first thing that
needed it. When the unsigned pattern pipeline needed exactly the same key, the
import would have been `patterns.py` -> `anchors.py` -> `patterns.py`, a
cycle -- and the alternative on offer was a second copy that would drift.

The question that resolved it is the one this table asks: *what kind of fact is
it?* A signature is a reduction of relations, so it belongs with the relations,
and both consumers import it from there. The cycle was a symptom; the missing
answer was the cause.

### Two rules that keep costing more than they look

**A label is not a filter.** When a sensor learns that some of its input is a
different kind of thing -- off-map geometry, a sprite the engine never draws --
the fix is to tag it and default the statistics to the part that answers the
question, not to drop it. `reachability.sector_kinds` and
`blood_types.sprite_visibility` are both consumed this way: object-scale mining
labels every sample with both and reports the excluded remainder under its own
heading, because a switch closet is evidence about wiring even when it is not
evidence about furniture.

**Compute a whole-map fact once per map.** `analyze_reachability` floods the
whole map; calling it per sample cost more than every relation extraction in
the Phase 1 pilot put together. Sensors that need it take a precomputed
mapping as a parameter and say so in the docstring.

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

`bloodmap.decompiler` embeds that complete contract in a `LevelSource` and adds a
separate, reviewable geometry-first hierarchy. The hierarchy cites existing
spatial/player/material evidence and never becomes compilation authority. See
[level-decompiler.md](level-decompiler.md).

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
