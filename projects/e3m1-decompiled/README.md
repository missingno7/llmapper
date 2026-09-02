# E3M1, decompiled

`maps/blood/campaign/E3M1.MAP` — the map whose street language Blood City is
written in — read back the way our own levels are written: not a geometric
tree only, but the plan, the surfaces, the joins, the overlays, the
mechanisms, the edges and the intent, each with the records and sectors it
cannot explain.

**Authority.** `E3M1.MAP` is the truth (CRC `a6465024`; 382 sectors, 2481
walls, 807 sprites). Everything here is derived, and `provenance.json` says
by what. The exact `LevelIR` is not committed — it is 5.5 MB and reproducible:

```bash
python -m bloodmap decompile maps/blood/campaign/E3M1.MAP -o work/E3M1.level-source.json
```

**The deliverable is `residue-ledger.json`.** It is one shared
`(record, field) -> [claims]` ledger -- the writer's own `RecordOwner` /
`RegionLedger` shape at field granularity -- and every layer writes into it.
Understanding is the share of CLAIMED FIELDS, and a sector is understood in
proportion to its own claimed fields. A layer that is not read says "not yet
read"; it never says zero.

A **claim** means: this layer's model determines this field's value, and
replaying the model reproduces it. Anything weaker is not a claim. The space
tree therefore claims nothing -- it partitions sectors, and a partition is not
a value -- which is the truest thing that can be said about a geometric
hierarchy. Two layers claiming one exclusive field with different values is a
conflict, reported by name; agreeing is corroboration; `shade` is additive, so
a sun and a lamp both writing it is the normal case.

## Running it

Every stage is runnable on its own and writes its evidence to
`references/`. In a worktree, absolute paths, never a junction:

```bash
BLOODMAP_CORPUS=D:/Games/DOS/llmapper/maps/blood BLOODMAP_ART=D:/Games/DOS/llmapper/reference/blood PYTHONPATH=".;projects/e3m1-decompiled/source" python projects/e3m1-decompiled/source/stage1_space_tree.py
```

| stage | layer | reader | evidence |
| --- | --- | --- | --- |
| `stage1_space_tree.py` | the space tree | `bloodmap.decompiler` (reused) | `references/space-tree.json` |
| `stage2_surfaces.py` | surfaces and frames | `bloodmap.read_surfaces` (new) | `references/surfaces.json` |
| `stage3_joins.py` | joins | `bloodmap.read_joins` (new) | `references/join-census.json` |
| `stage4_overlays.py` | islands, the light field, lamps | `bloodmap.read_islands`, `bloodmap.read_light` (new) | `references/overlays.json` |
| `stage6_edges.py` | the edge chain | `bloodmap.read_edges` (new) | `references/edge-chain.json` |

`source/run_all.py` runs every stage, merges the ledger, and runs them again --
a stage's review pack shows the SHARED ledger's fact panel, so the packs are
rebuilt once every layer's claims are in.

`source/ledger.py` composes every stage's evidence into `residue-ledger.json`.

## Review packs

Every layer emits one, into `review/layer<N>.html`: the reader's decisions as
a tree on the left, E3M1 on the right in XMapEdit's orientation (+Y down),
click a node to light its sectors. **A sector no node owns is that layer's
residue**, shown rather than claimed, so the packs are built from a hierarchy
whose nodes are only what the layer decided.

Each pack shows **one aspect at a time** (the select at the top of the side
panel dims everything outside one top-level branch), and clicking a sector
fills a fact panel with every claim on its fields -- the layer, the owner, the
value and the reason -- followed by every field of the sector record nothing
claims. "mark a claim" records the record, the field and the note.

Owner questions are beside the pack in `review/questions-layer<N>.json`, at
most ten a layer, each naming a node id with a recommended default -- never
nodes themselves, because `review_pack`'s deepest-owner rule would then let a
question own the sectors it asks about and colour the map by our doubts. The
owner's marks come back as `review/answers-layer<N>.json`; each is fixed or
refuted by a measurement in the next report.

## What is here

| Path | What it is |
| --- | --- |
| `provenance.json` | CRC, counts, and the commands that regenerate everything |
| `residue-ledger.json` | **the deliverable**: the shared claim ledger, per layer and per record |
| `claims.json` | the raw `(record, field) -> [claims]` map, for the packs |
| `hierarchy.json` | the derived space tree as a reading view |
| `structures.json` | recovered architectural structures with residuals |
| `assets.json` | this level's dominant tiles with local role aliases |
| `nodes.jsonl` | one grep-able line per searchable node |
| `references/` | one evidence file per layer, machine-readable |
| `source/` | one runnable stage per layer |

## The rule the ledger keeps

A frame fitted to one record reproduces that record exactly. So does a join
rule written from the one pair it was written from. Identity that cost nothing
is not evidence, and the ledger counts it as residue rather than as
understanding — which is why these numbers are far smaller than a coverage
report of the same map would be.

Links — tx/rx, markers, stacks, keys, conditions — are a **relation set over
records**, never tree nodes. A link is not a place, and putting one in the
hierarchy would give it sectors it does not own.
