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
Blood has a versioned review, `knowledge/blood/ontology-v2.json` (the second
pass, after a contradiction pass over the first). Native IDs are never material
semantics. See [materials.md](materials.md).

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
| a record's base fields or its Blood extension, whichever shape holds it (`DiskObject` or a `LevelIR` dict) | `model.record_fields`, `model.record_extra` | `getattr(item, "extra", None)`, which is None for every decompiled level |
| which sector owns a wall, a sector's loops, a wall's two ends | `sector_geom.py` | a loop over `wall_ptr`/`wall_count` in the module that needed it |
| area, containment, intersection of point lists | `planar_geom.py` | a shoelace sum beside the caller |
| how tall and wide the player is, and what it can step | `player_space.PLAYER_PROFILES` | the literal 16960, 384 or 4096 |
| how big a map may be | `build_ir.BUILD_LIMITS` (the ports: an error past it), `build_ir.VANILLA_LIMITS` (the DOS game: a warning), `analysis.BLOOD_X_LIMITS` | the literal 1024, 8192 or 4096 |
| whether the player can get to a sector, and what off-map geometry is for | `reachability.py` | a fresh flood fill |
| what a mechanism is made of and how its parts relate | `assembly.py` | a second grouping pass |
| how one dynamic family works in detail (doors, lifts) | `doors.py`, `mechanism.py` | `assembly.py`, which owns membership, not behaviour |
| a derived spatial view over sectors (adjacency, portals, loops) | `spatial.py` | recomputing from walls |
| an object-scale relation between a sprite, a wall and a sector | `relations.py` | `patterns.py` |
| a reduction of relations to a comparable key | `relations.py` (`context_signature`) | its consumers |
| where a corpus map came from, which population it is, and how to list "the campaign" | `corpus.py` (`campaign_maps`, `named_maps`, `corpus_map_path`) | globbing a directory, or a regex over filenames |
| a recurring unsigned signature family | `patterns.py` (`observe_*` + `_SIGNATURES`) | a new pipeline |
| what surrounds a labelled anchor, and whether that context means anything | `anchors.py` | `patterns.py` |
| an architectural structure candidate with parameters and residual (stairs, recesses) | `structures.py` | `relations.py` |
| what an opening in a wall is: leaf, lintel, step, and which are apertures | `aperture.observe_openings` | the miner that runs it over the corpus |
| how much solid mass stands between two rooms | `layout.observe_wall_thickness` | the miner that runs it over the corpus |
| where the campaign has an instance of a type, a sector effect or a reserved channel, and which lesson teaches it | `examples.py` (asked through `python -m tools.catalog find` / `show`) | a census written for the occasion |
| what an act sets off: the chain from a cause through a sender to everything that answers, and that chain's shape | `wiring.py` (`chains`, `shape`; indexed by `examples.py`, asked through `catalog find` / `wiring` / `mechanisms`) | another walk over `tx_id`/`rx_id`; naming a mechanism by a sector's type |
| whether our readers can finish a map known to be finishable, and where they stop | `completion.py` (`read`, `missed`; the campaign's score is `tools/reading_check.py`) | judging a reader by whether it returns; a scoreboard labelled by hand |
| a level's own wiring: what each wire is for, which channel it is on, and whether the built map agrees | `wiring.py` (`Circuit`, `Wire`; `read_back`) | a channel number typed into a module; an object given two `tx_id`s |
| whether an object with a channel can send at all | `wiring.py` (`can_send`, `silent_senders`; `motion.silent_transmitters` and the rule `transmitter-reports-an-edge` call it) | a check that looks at sprites only |
| which tile the renderer shows on which band of a wall (steps, mask, one-way) | `render_slots.py` | a `next_sector < 0` test in the consumer |
| a measured, versioned, citable design number | `knowledge/blood/design/*-vN.json` | a constant in the module that needed it |
| something a level taught us that fits no other shelf: what the engine does with a construction, how a thing is built, a renderer limit, a trap a check cannot see, a ruling of the owner's | a finding, saying how it is known: `python -m tools.findings add` (`bloodmap/findings.py`) | the docstring of the level module that met it; an agent's memory |
| where a level's map, poses, reports and critique rounds are | its `project.json`, read through `bloodmap.project` | a path typed into a tool |
| the order a level's map goes through from layout to file | `bloodmap/finish.py` | the last seven hundred lines of one level's build |
| what one level decided for itself: its plan, its places, its rows | `projects/<name>/level/` | `bloodmap/`, where every other level would inherit it |
| something an author should be able to *write* | a `vocabulary.py` / `prefab.py` constructor | the knowledge store |

A sensor lives in the library; a tool is its run over a corpus. `tools/mine_*.py`
enumerate maps through `corpus.py`, call a library sensor, summarise, and write
a knowledge file. The library never imports from `tools/` or `experiments/`
(`tests/test_architecture.py` holds that), because a rule that reads a built map
through a script's function stops working the day the package is installed
without the scripts beside it. The full list of what exists, one line per
module and tool, is [the module map](module-map.md).

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
sectors, player start, and Build angles. The limits are the target ports': NBlood and
EDuke32 compile with 4096 sectors, 16384 walls and 16384 sprites, and a map past
those is an error. A map past the original DOS game's 1024/8192/4096 is a warning:
it loads in the ports, and how large a map may be is its author's decision. Game-native validation then adds Blood or
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

## Known debts

What the consolidation of 2026-11-26 left undone, so that it is not found again by
surprise. Each is paid when a second level needs the thing, by moving it with a test that
needs no level and proving that Gravesend's map does not change by a byte.

- **Gravesend's build does not call `bloodmap.finish.finish`.** It runs the same library
  passes itself with dozens of its own between them (`projects/blood-city/level/build_skeleton.py`,
  one function of two thousand lines sharing a `ctx`). The order is written once, in
  `finish.py`; the two can drift. Paying it means giving `finish` hooks at every point where
  Gravesend interleaves.
- **Techniques still written against Gravesend's layout**, each a worked example the findings
  point at: the arrangement-place kit (`_q`, `_rect`, `_ring`, `keep` in eight modules; the
  general form is `settling_hall.put_back` over `bloodmap.surface.RecordOwner`), `props`,
  `setpieces`, `fixtures`, `templates`, `facade_pass`, `facade_bays`, `windows`, `glass.shopfront`,
  `wing_doors`, `doorswitch`, `curtains`, `motion_sounds`, `solidity`, `apertures`, `dressing`,
  `runs`, `ambience`, `sewerkit`, `difficulty`, `players`, `first_sight`, `playthrough`,
  `release.shift`, the flight of `ghost_stair`.
- **Gravesend's choices encoded in the library as if general:** `joins.TILE_CLASSES` (and the
  readers `read_joins`, `read_facts` that score a band by that one tile), `read_plan.WIDTH_CLASSES`,
  the weights of `view_score.score` (fitted on Gravesend's showcase rounds only), and the
  city-shaped modules `city`, `street`, `street_model`.
- **Three ways to author a level that no level uses** (August 2026): `construction.LevelBuilder`
  with `designs`; fragment composition with `recipe` and `recipes/*.json`; the authoring loop
  and probes (`authoring_loop`, `probes`, `probe_schema`, `state_model`, `design_contract`,
  `counterfactual`). They are tested and reachable from the CLI; whether to remove them is the
  owner's decision. A level is authored with `levelprog` and finished with `finish`.
- **Capabilities tested only on Gravesend's map** (their tests are in `projects/blood-city/tests`):
  `tidy.merge_alike`, `sprite_fit.unbacked`, `texture_frame.split_bands_unpegged`,
  `catalog.directional_floor_faults`, the clock rules of `breakables`, the overlay
  rounding-drift regressions (they import `resolution.SUN_BEARING`).
- **A project status of two kinds.** `tools.project status` is every level's; Gravesend's
  `level/status.py` and the E4L1 remake's `status.py` know their own places. The place table
  (`character.PLACES`, `places.json`) is the part worth making common.
- **The findings are checked, and a few will still be wrong.** The shelf was filled in a day
  from notes and comments. A first audit (81 of 322 corrected) left a false statement in a
  quarter or more of it. The second, on 2026-11-26, opened every citation: 233 of 327 were
  corrected and each finding now carries a mark saying what was opened and what was read there
  (`checked`; `python -m tools.findings unchecked` lists what has none, or has been rewritten
  since). Two independent verifiers then re-opened 48: 36 held entirely, 9 had a slip that
  misleads nobody, 3 still said something false (all twelve since corrected). So expect about
  one marked finding in sixteen to be wrong somewhere, and correct it when you meet it
  (`tools.findings amend`).
- **Values the audit showed to rest on a wrong figure, left as they are because changing them
  changes Gravesend's map** (each says so where it stands): `l3_church.PITCH` 21878 (the
  campaign's median slope rise in the retired 0x1600 unit; in bodies it is about 7,290),
  `fixtures.GOODS_SHARE` 0.14 (the five maps pooled give 0.12), `scale.HOLE_MEDIAN` /
  `HOLE_LARGE` (from a sweep that was not kept; the 96 kept holes give 1,664 / 1.57 and
  2,208 / 1.95), `lettering.PITCH` 1.45 (the campaign's letter pitch is 1.333; 1.45 is its line
  pitch). Whether Gravesend should move to the true figures is a design decision.
- **Small things the audit met and did not settle.** `tools/mine_city_assets.py` and
  `tools/mine_stands.py` name their maps by path (`TOWN_MAPS`) instead of through
  `bloodmap.corpus`. `bloodmap/conditional.py` gives E1M2's reachability cut as from 231
  sectors and `reports/blood-swept-mechanisms.md` as from 226; neither run was kept.
  `blood_types.sprite_visibility` calls every generator "wiring", though the campaign draws
  112 of them. `HIDDEN_TYPES` still holds markers 8 and 15-19 on belief: the engine's hiding
  of those was not read.
