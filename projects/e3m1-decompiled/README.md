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

`source/ledger.py` composes every stage's evidence into `residue-ledger.json`.

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
