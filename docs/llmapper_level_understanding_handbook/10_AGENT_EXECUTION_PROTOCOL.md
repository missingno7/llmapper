# Agent Execution Protocol

This file is intended to be pasted into or referenced by a coding/research agent.

## Mission

Raise `llmapper` from low-level map generation toward evidence-driven,
multi-view level understanding.

Work incrementally. Do not solve the entire roadmap in one change. Pick **one
phase task** from `09_IMPLEMENTATION_ROADMAP.md` (each states what already
exists — do not rebuild it).

## Repository conventions (non-negotiable)

- Python package: `bloodmap/`; CLI: `python -m bloodmap <command>`.
- Tests: `python -m unittest discover -s tests` (unittest, not pytest).
  Corpus-dependent tests must skip cleanly when maps are absent.
- Corpus: local-only under `maps/blood/` (layout in `07_...md`), never
  committed; population provenance is fail-closed.
- Knowledge: versioned files `knowledge/blood/design/*-vN.json`; it is a
  retrieval surface, not a second authoring language. Repeated needs are
  promoted to `bloodmap` constructors + regression tests (see that README).
- Reports: machine-readable JSON + human-readable MD under `reports/` or
  `projects/<name>/references/`, in the style of the existing
  `e6m1-shop.{json,md}` pair.
- The NBlood submodule hosts the playtest bot: never `git add -A` inside it,
  never stage the parent's submodule pointer.
- Human review is batched, never blocking: no interactive gates inside
  loops; emit review queues instead.
- Verify the thing, not the call: a constructor or miner that returns
  without raising is not evidence. Inspect the artifact (render it, replay
  it, diff it) before claiming success.
- When changing a unit or measurement, grep for its consumers; derived
  numbers move with it.

## Before coding

For the selected task:

1. inspect the modules the roadmap phase names as already existing,
2. inspect existing knowledge/reports/tests,
3. identify what is already solved,
4. write a short problem statement,
5. state the exact new evidence the implementation will expose,
6. state how the result can be falsified.

## Evidence discipline

For every learned rule:

- preserve source map and population,
- preserve primitive IDs where practical,
- separate exact fact (OBSERVATION) from interpretation,
- search counterexamples,
- report ambiguity,
- exclude generated maps from evidence,
- cite community maps only as *precedent*, never as campaign convention.

## Required research loop

```text
observe
-> measure
-> hypothesize
-> search corpus
-> find support
-> find counterexamples
-> revise
-> encode only supported knowledge
-> verify
```

## Do not prematurely promote to authoring code

A recurring observation becomes a `vocabulary.py`-tier constructor only when:

- recurrence is established,
- invariants are understood,
- the concept is useful for synthesis,
- counterexamples are known,
- a regression test can detect breakage.

## When a candidate is uncertain

Do not guess. Produce:

```text
candidate ID
supporting examples
counterexamples
possible interpretations
specific experiment/query that would distinguish them
```

If human input is genuinely high leverage, add it to the review queue and
continue with the next task; do not block on it.

## Prefer experiments over prose

Bad:

```text
I think shelves are usually near walls.
```

Good:

```text
Of 63 candidate shelf assemblies:
- 57 have a dominant back plane within X distance,
- 4 are freestanding,
- 2 are ambiguous.
Compared with crate piles, wall adjacency separates the classes poorly,
but privileged front access separates them strongly.
```

Only report statistics actually measured.

## Avoid framework disease

Do not introduce universal ontologies, giant scene-graph engines, generic
solvers, or plugin systems unless current evidence proves they reduce
repeated work. If a 100-line targeted miner answers the current research
question, prefer it to a 3000-line architecture. Extend `patterns.py`,
`assembly.py`, `spatial.py`, `structures.py` before creating parallel
modules.

## Keep discoveries inspectable

Every mining tool should emit:

- machine-readable JSON,
- representative examples,
- source provenance (map, population, primitive IDs),
- human-readable summary,
- known limitations.

## Completion format for each task

### What changed

Concrete implementation.

### Evidence

What original-map evidence supports it (population named).

### Counterexamples

What does not fit.

### What remains unknown

Explicit uncertainty.

### Regression tests

Tests that can fail meaningfully.

### Next highest-value experiment

One or two focused next steps.

Do not claim a broad semantic capability from a narrow pilot.
