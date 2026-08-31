# Agent Start Here

You are working on `llmapper`, especially the Blood level-understanding and
authoring pipeline.

Your task is **not** to implement the entire handbook in one pass.

Read in this order:

1. `00_README.md` — including "Existing foundations": most early phases are
   partially implemented already; do not rebuild them,
2. `01_PRINCIPLES_AND_GUARDRAILS.md`,
3. `09_IMPLEMENTATION_ROADMAP.md` — pick ONE task; each phase lists what
   already exists, the gap, and the agent task,
4. `10_AGENT_EXECUTION_PROTOCOL.md` — repository conventions and reporting
   format,
5. the numbered document for your chosen phase.

**Phase 0a (corpus integration) is done (2026-08-31).** The corpus registry
resolves populations from the directory layout
(`maps/blood/{campaign,curated,conversions,community,tiered,mechanism}` with
`multiplayer/` mode subdirectories); see `bloodmap/patterns.py`,
`maps/blood/README.md`, and the measured counts in `07_...md`. Enumerate with
`list_corpus_maps` / `list_original_maps`, never by globbing a directory.
**Phase 1 (general relation extraction) is done (2026-08-31).**
`bloodmap/relations.py` emits object-scale relations over a neighborhood,
frame-independently; see `reports/blood-object-relations-pilot.md`.

**Phase 2 (semantic-anchor mining) is done (2026-08-31).** `bloodmap/anchors.py`
replaces the two hand-written anchor miners with one query (`anchor-mine`), and
reports each anchor's context enrichment; see `reports/anchor-queries.md`.

**Phase 3 (object-scale unsigned families) is done (2026-08-31).** The
`object-context` family lives in `patterns.py` alongside the three that were
there; see `reports/blood-object-context-families.md`. The next runnable task
is Phase 0 (the architecture note) or Phase 4.

## Working rule

At every step ask:

```text
What new level-design fact can the system learn from original maps after this
change that it could not learn before?
```

If the answer is unclear, do not add the abstraction.

## Current architectural bias

Prefer extending existing concepts:

- `bloodmap/assembly.py` for mechanism membership and relational closure,
- `bloodmap/doors.py` as the reference dynamic interpretation,
- `bloodmap/spatial.py` for derived independent spatial views,
- `bloodmap/patterns.py` for unsigned candidates, populations, provenance,
- `bloodmap/structures.py` / `prefab.py` for object-scale geometry recovery,
- `bloodmap/vocabulary.py` for constructor promotion (with corpus support),
- `knowledge/blood/design/` for versioned interpreted knowledge,
- `tools/mine_e6m1_shop.py` / `tools/mine_sewer_kit.py` as the anchor-mining
  precedent to generalize.

Avoid parallel frameworks.

## Main roadmap

```text
corpus integration (new layout, populations, tier metadata)
-> relations
-> semantic anchors
-> unsigned subgraph discovery
-> contrastive concepts
-> negative space + assemblies
-> functional regions
-> facade grammar
-> generic state-change observations   (mostly exists: assembly/doors/motion_sim)
-> conditional topology
-> multi-view understanding
-> discovery frontier + batched review queue
-> recursive abstraction
-> design intent (lands in level programs + vocabulary constructors)
-> synthesis + critics + scoped repair
```

## Deliver one task at a time

For each task:

1. inspect current code and evidence,
2. choose a narrow pilot,
3. produce an evidence-backed result,
4. preserve counterexamples,
5. write meaningful tests (`python -m unittest discover -s tests`),
6. update docs/knowledge,
7. state the next experiment.

Never treat generated maps as evidence. Never block on human review — queue
it. Never touch the NBlood submodule pointer.
