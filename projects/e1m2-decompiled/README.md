# E1M2, decompiled

`maps/blood/campaign/E1M2.MAP` — the town at the foot of the mountain — read
back through the same eight layers as [E3M1](../e3m1-decompiled/README.md),
with **byte-identical stage code**. That is the point of it: a second map is
what proves a program reads maps rather than one map.

**Authority.** `E1M2.MAP` is the truth (CRC `ba5db227`; 313 sectors, 2469
walls, 698 sprites). Everything here is derived and reproducible:

```bash
python -m bloodmap decompile maps/blood/campaign/E1M2.MAP -o work/E1M2.level-source.json
```

## Why this map

The residue curve over all 43 campaign maps
([reports/residue-curve-2026-09-03.md](../../reports/residue-curve-2026-09-03.md))
says the join grammar reaches only four maps at all, and outside E3M1 this is
by far the strongest: **12 layer-3 claims over 313 sectors**, four road
sectors, one island, seven kerb records. It was chosen as the second map under
the stated E1M2 default; the curve later moved and named E4M8 instead, so
[E4M8 is decompiled too](../e4m8-decompiled/README.md) and this one is kept
for the reason it was picked.

## What it cost the program to read a second map

Five crashes, each a place where E3M1's program had assumed E3M1:

* no `sign` dict at all — E1M2 has **no oblique shade boundary**, so the sun
  is never read. Fixed in `read_light` by returning the same keys either way;
* no `casters` census behind it, for the same reason and the same fix;
* the biggest `tx -> rx` chain outside the first 40 of its kind, so the owner
  question named a node the tree had truncated;
* `kind:room_over_room` as a question node on a map with one stack;
* a naming question about the first named mechanism, on E4M8, which names
  none.

Two of the five were fixed in the reader rather than the caller, under the
rule already applied to `sun_axis`: **return the same keys whether or not
anything was found.**

## The numbers

4126 of 101049 claimable fields have a claim (**4.083%**); 3559 residue facts.
Per layer, and against the other two maps, in
[reports/sleep-phase-2026-09-03.md](../../reports/sleep-phase-2026-09-03.md).

Its own measurements, where they differ from E3M1's: measured island rise
**1024** (E3M1's is 2048), base plane z 17408, kerb tile **281** on 7 of 7
`road|pavement` records with none blocking, and 22 join pairs with no row —
including the only water in the three maps, which leaves 56 residue facts of
its own.

## Layout

Identical to E3M1's, and produced by the same `source/`. `facts/` is one JSONL
per predicate, `references/` the per-layer evidence, `review/` the eight owner
packs, `residue-ledger.json` the deliverable.

```bash
BLOODMAP_CORPUS=<absolute path to maps/blood> \
PYTHONPATH=".;projects/e1m2-decompiled/source" \
python projects/e1m2-decompiled/source/run_all.py
```
