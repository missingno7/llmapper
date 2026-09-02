# E3M1, decompiled

`maps/blood/campaign/E3M1.MAP` — the map whose street language Blood City is
written in — read back the way our own levels are written: the plan, the
surfaces, the joins, the overlays, the mechanisms, the edges and the intent,
each with the records and fields it cannot explain.

**Authority.** `E3M1.MAP` is the truth (CRC `a6465024`; 382 sectors, 2481
walls, 807 sprites, 133 XSECTORs, 41 XWALLs, 716 XSPRITEs). Everything here is
derived. The exact `LevelIR` is not committed — it is 5.5 MB and reproducible:

```bash
python -m bloodmap decompile maps/blood/campaign/E3M1.MAP -o work/E3M1.level-source.json
```

## The decompilation is a fact store

`facts/` holds one JSONL per predicate
(`RESEARCH-OVERLAPPING-LAYERS-2026-09-02.md` section 2). Base facts are the
records as the map stores them; every derived fact carries the facts it came
from (`_from`) and the reader that made it (`_reader`, `_layer`). The store
only grows within a run: a selection pass may CHOOSE among candidates, and
nothing deletes.

```text
base        sector wall sprite xsector xwall xsprite connects
space       part_of
surfaces    surface frame attachment stepped_run
joins       surface_kind join unknown_join
overlays    island kerb sun shade_edge shade_depth light_source
edges       edge_segment offmap
plan        corridor plan_edge block
mechanisms  sentence realises link key stack condition
the ledger  claims candidate selection conflict residue
```

Relations are records, in the IFC sense: a join, a link, a stack, an
attachment is a predicate with attributes and evidence, never a field hung on
a wall. The space tree is `part_of` facts, so two hierarchies can coexist
without either being *the* tree. Ambiguity is kept as `candidate` rows and
resolved by a `selection` pass that states its criterion — including where it
chooses nothing, because a tie is a result.

**Understanding is the share of CLAIMED FIELDS.** A `claims` row says: this
layer's model determines this field of this record, and replaying the model
reproduces it. Anything weaker is not a claim — the space tree claims nothing,
because a partition is not a value. Two exclusive claims on one field with
different values is a `conflict`, recorded with both owners; agreeing is
corroboration; `shade` is additive, so a sun and a lamp both writing it is
normal.

**No percentage in any report here is typed.** `source/query.py` computes
every one of them from `facts/` and writes `residue-ledger.json`.

## Running it

Absolute paths in a worktree, never a junction:

```bash
BLOODMAP_CORPUS=D:/Games/DOS/llmapper/maps/blood BLOODMAP_ART=D:/Games/DOS/llmapper/reference/blood PYTHONPATH=".;projects/e3m1-decompiled/source" python projects/e3m1-decompiled/source/run_all.py
```

`run_all.py` builds the store, queries it, then rebuilds every stage's
evidence and review pack, in that order.

| stage | layer | reader | evidence |
| --- | --- | --- | --- |
| `stage1_space_tree.py` | the space tree | `bloodmap.decompiler` (reused) | `references/space-tree.json` |
| `stage2_surfaces.py` | surfaces, frames, stairs | `read_surfaces`, `read_stairs` | `references/surfaces.json` |
| `stage3_joins.py` | joins | `read_joins` | `references/join-census.json` |
| `stage4_overlays.py` | islands, the light field, lamps | `read_islands`, `read_light` | `references/overlays.json` |
| `stage6_edges.py` | the edge chain | `read_edges` | `references/edge-chain.json` |
| `stage7_plan.py` | the plan | `read_plan` | `references/plan.json` |
| `stage5_mechanisms.py` | mechanisms as sentences | `read_mechanisms` | `references/mechanisms.json` |
| `stage8_intent.py` | intent | `read_intent` | `references/intent.json` |

Every reader is a pure function in `bloodmap`; `bloodmap/read_facts.py` turns
each one's result into facts. The project orchestrates and stores, and that is
all it does.

## Review packs

One per layer, in `review/layer<N>.html`, from `tools/review_pack.py`: the
reader's decisions as a tree, E3M1 on the right in XMapEdit's orientation
(+Y down), one aspect at a time. **A sector no node owns is that layer's
residue**, shown rather than claimed. Clicking a sector fills a fact panel
with every claim on its fields — layer, owner, value, reason — then the
candidates still open on it, then every field of the sector record nothing
claims. "mark a claim" records the record, the field and the note.

Owner questions live beside the pack in `review/questions-layer<N>.json`, at
most ten a layer, each naming a node id with a recommended default. They are
never nodes: the pack's deepest-owner rule would let a question own the
sectors it asks about and colour the map by our doubts. Marks come back as
`review/answers-layer<N>.json`, and each is fixed or refuted by a measurement
in the next report.

## What is here

| Path | What it is |
| --- | --- |
| `facts/` | **the decompilation**: one JSONL per predicate, with provenance |
| `residue-ledger.json` | the query over it: understanding, residue, conflicts |
| `claims.json`, `candidates.json` | the panels the review packs read |
| `provenance.json` | CRC, counts, and the commands that regenerate everything |
| `hierarchy.json`, `structures.json`, `assets.json`, `nodes.jsonl` | the layer-1 reading view |
| `references/` | one human-readable evidence file per layer |
| `review/` | one pack, one hierarchy and one question set per layer |
| `source/` | the orchestration: `build_facts.py`, `query.py`, one stage per layer |

## The rule the ledger keeps

A frame fitted to one record reproduces that record exactly. So does a join
rule written from the one pair it was written from. Identity that cost nothing
is not evidence, and the ledger counts it as residue rather than as
understanding — which is why these numbers are far smaller than a coverage
report of the same map would be.

Links — tx/rx, markers, stacks, keys, conditions — are a relation set over
records, never tree nodes. A link is not a place, and putting one in the
hierarchy would give it sectors it does not own.
