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

**The deliverable is `residue-ledger.json`.** Understanding is 100% minus
residue, per layer, in that layer's own population. A layer that is not read
says "not yet read"; it never says zero.

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

`source/ledger.py` composes every stage's evidence into `residue-ledger.json`.

## Review packs

Every layer emits one, into `review/layer<N>.html`: the reader's decisions as
a tree on the left, E3M1 on the right in XMapEdit's orientation (+Y down),
click a node to light its sectors. **A sector no node owns is that layer's
residue**, shown rather than claimed, so the packs are built from a hierarchy
whose nodes are only what the layer decided.

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
| `residue-ledger.json` | **the deliverable**: per layer, what nothing explains |
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
understanding — which is why these numbers are larger than a coverage report
of the same map would be.
