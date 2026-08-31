# llmapper — Level Understanding & Synthesis Handbook

## Purpose

This document set is a long-term implementation roadmap for moving `llmapper` from
"an AI that can construct valid Blood maps" toward a system that can **understand,
decompile, explain, verify and eventually synthesize authored level design**.

The central idea is:

> Do not teach the AI what Blood levels look like. Teach it how Blood levels are
> composed: from primitive geometry, surfaces, sprites and mechanisms into
> objects, assemblies, functional regions, architecture, gameplay structures,
> progression and visual communication.

The target is not one canonical representation of a level. A level has multiple
partially independent views:

- physical geometry,
- semantic objects and architecture,
- functional use,
- mechanisms and state changes,
- topology and progression,
- gameplay,
- aesthetics,
- readability and visual communication.

These views should be mined independently from existing maps and later reconciled
into higher-level design understanding.

This handbook complements, and must not contradict, the project's standing
priority: **the primary artifact is a hierarchical, editable source
representation of a level** (level programs and the authoring vocabulary).
Mined understanding is valuable exactly insofar as it improves what can be
expressed and verified in that source representation.

## Existing foundations in the repository

The roadmap extends existing architecture instead of replacing it. Much more
exists than a greenfield reading would suggest. Before starting any phase,
check this list — several roadmap phases are already partially or largely
implemented.

**Relations and structure recovery**

- `bloodmap/design.py`, `bloodmap/spatial.py` — deterministic sensors and
  independent derived spatial views; deliberately no canonical room graph.
- `bloodmap/structures.py` — recovers the layer between a space and its
  details (stair treads, alcoves, door volumes, shells), each candidate with
  evidence, essential parameters, and residual.
- `bloodmap/prefab.py` — the seven mined kinds of small sectors (junction,
  link, alcove, …) with stable per-map populations.
- `bloodmap/reachability.py` — playable space vs `logic_closet` vs letterforms
  vs off-map machinery; what non-playable geometry is *for*.

**Mechanisms and dynamics**

- `bloodmap/assembly.py` — a mechanism is several objects plus relations;
  closure over containment, references and channels; relational facts (travel,
  pivot, carried parts, operator commands).
- `bloodmap/doors.py` — five independent facets per door (Behavior,
  Interaction, Condition, Feedback, Signifier), mined from the campaign; the
  reference for interpreting a physical state change as one semantic mechanism.
- `bloodmap/mechanism.py` — constructs mechanisms *from* mined templates
  (the authoring half of the loop).
- `bloodmap/motion_sim.py` — engine-transcribed motion replay; the oracle for
  "is this the same motion".
- `bloodmap/state_model.py` — PlayerState / WorldState / PlayerKnowledge
  layers for design probes.
- `bloodmap/mechanisms.py` — game-neutral semantic mechanisms above Blood /
  Duke / Doom native encodings.

**Patterns and knowledge**

- `bloodmap/patterns.py` — unsigned candidate mining over discrete signatures
  (spawn neighborhoods, route exposure, morphology, vertical transitions),
  population separation, retrieval. See `docs/design-pattern-discovery.md`.
- `knowledge/blood/design/` — versioned (`*-v1.json`) evidence-backed
  hypotheses; a retrieval surface, not a second authoring language. Its
  README states the promotion rule: repeated needs go into `bloodmap`
  constructors with regression tests.
- `bloodmap/vocabulary.py` — the constructor promotion discipline
  (constructor / compositional / relation), with corpus support recorded per
  entry.
- `tools/mine_e6m1_shop.py`, `tools/mine_sewer_kit.py` — the current
  precedent for **semantic-anchor mining**: owner-identified assets, complete
  carrying sectors, one-hop neighborhoods, no cross-map tile inference.

**Critics and oracles**

- `bloodmap/analysis.py` (validate), `bloodmap/geometry_audit.py` — geometry.
- `bloodmap/level_profile.py` + `tools/design_norms` — corpus comparison as a
  vector of independent measurements, never one score.
- `bloodmap/oracle.py` — NBlood as runtime oracle (does it load, spawn, move).
- `bloodmap/visual.py` + XMapEdit observer — rendered-view evidence.
- `bloodmap/authoring_loop.py` — the existing authoring loop these critics
  feed. Known standing issue: critic rules have repeatedly measured the wrong
  thing; every new critic must state its oracle and its failure to detect.

## Target architecture

```text
ORIGINAL / CURATED MAP CORPUS
            |
            v
      EXACT MAP FACTS
            |
            v
        GROUNDED VIEWS
            |
  +---------+---------+------------------+
  |         |         |                  |
geometry  surfaces  mechanisms      rendered/play views
  |         |         |                  |
  +---------+---------+------------------+
            |
            v
      RELATION EXTRACTION
            |
            v
   AUTOMATIC PATTERN DISCOVERY
            |
   +--------+---------+
   |                  |
unsigned candidates   semantic anchors
   |                  |
   +--------+---------+
            |
            v
     hypotheses + counterexamples
            |
            v
   BATCHED HUMAN REVIEW QUEUE
            |
            v
       KNOWLEDGE GRAPH
            |
            v
   HIGHER-LEVEL DISCOVERY
            |
            +--------------------+
            |                    |
            v                    |
       DESIGN INTENT             |
            |                    |
            v                    |
     AUTHORING PRIMITIVES        |
            |                    |
            v                    |
           MAP                   |
            |                    |
            v                    |
   INDEPENDENT CRITICS ----------+
            |
            v
       SCOPED REPAIR
```

Human review is **batched, never blocking**: agent loops run to completion
against automated acceptance, and human decisions are collected in a review
queue that propagates to many candidates at once. No phase may introduce a
human gate inside an agent loop.

The loop is recursive: every newly learned semantic concept becomes a
higher-level feature that can be used to discover larger structures.

Example:

```text
walls + sectors + texture
    -> drawer unit
    -> desk assembly
    -> office region
    -> office / service-space design pattern
```

## The corpus

The map corpus was reorganized (2026-08) into subdirectories of `maps/blood/`
and expanded by ~1500 community maps. See
`07_CORPUS_EXPANSION_ACTIVE_LEARNING_AND_DISCOVERY_FRONTIER.md` for the
authoritative layout and the required loader work — **existing corpus commands
do not yet see the new layout**, which is the first implementation task.

## How to use this handbook

Do **not** implement everything at once.

Read:

1. `01_PRINCIPLES_AND_GUARDRAILS.md`
2. `02_MULTI_VIEW_LEVEL_MODEL.md`
3. `09_IMPLEMENTATION_ROADMAP.md` — each phase now states what already exists
   in the repository and what the remaining agent task is
4. then execute one task at a time.

Each implementation task must:

- start from original-map evidence,
- state what is observation vs interpretation,
- produce inspectable artifacts,
- include counterexamples,
- include regression tests (`python -m unittest discover -s tests`),
- avoid introducing a universal abstraction until at least several real cases
  justify it.

The highest-risk failure mode is not missing features. It is creating an
impressive framework that has no oracle and therefore silently teaches the AI
fiction.
