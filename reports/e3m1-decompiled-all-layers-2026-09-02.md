# E3M1 decompiled: all eight layers, and the fact store

P15, 2026-09-02, branch `e3m1-decompiled` from `blood-city-arcade`. The
layers-1-4 stop-and-report is
[`e3m1-decompiled-layers-1-4-2026-09-02.md`](e3m1-decompiled-layers-1-4-2026-09-02.md);
this continues it through layers 6, 7, 5 and 8 and records the two shape
changes the supervisor made in flight.

**Every number below is a query over `projects/e3m1-decompiled/facts/`,
computed by `source/query.py`. None is typed.** Where a number here disagrees
with the layers-1-4 report, this one is right: the ledger was re-shaped and
re-run afterwards.

## The output is a fact store

`RESEARCH-OVERLAPPING-LAYERS-2026-09-02.md` section 2, applied. One JSONL per
predicate; base facts are the records as the map stores them; every derived
fact carries what it came from and the reader that made it. **18 297 rows in
35 predicates.** Readers are pure functions in `bloodmap`
(`facts.py`, `read_facts.py`) and the project only orchestrates and stores.

* **relations are records** — `join`, `link`, `key`, `stack`, `attachment`,
  `realises`, `part_of`. The space tree is one relation among many, which is
  why two hierarchies can coexist without either being *the* tree.
* **ambiguity survives** — 42 `candidate` rows, resolved by 24 `selection`
  rows that each state a criterion, including the one that chooses NOTHING.
* **inconsistency is recorded** — `conflict` and `residue` are predicates with
  owners.

## Understanding, per layer

```text
4310 of 110998 claimable fields have a claim -- 3.883%
(12 282 structural fields the FORMAT owns are excluded by name)

layer                                    facts   fields  share    residue
1 space tree                              1300        0   0.0%        108
2 surfaces, frames and structures         6812     3992   3.596%     1650
3 joins                                   3113       33   0.03%      1312
4 overlays: islands, light, lamps           85       17   0.015%       24
5 mechanisms as sentences                 1627      206   0.186%      397
6 the edge chain                           141       64   0.058%        0
7 the plan                                  32        0   0.0%          1
8 intent                                   172        0   0.0%        110

conflicts on exclusive channels : 0
corroborated exclusive fields   : 2
residue by aspect : surface 1649, join 1312, mechanism 397, intent 110,
                    space 108, light 17, island 7, structure 1, plan 1
sector : 382 records, 217 with no claimed field, median 0%, best 10.5%
wall   : 2481 records, 1654 with no claimed field, median 0%, best 42.9%
sprite : 807 records, 807 with no claimed field
```

**Layers 1, 7 and 8 claim no field, and that is the finding.** A space tree
partitions sectors and a partition is not a value. A plan is schematic by
contract — it holds no picnum, no z and no Build unit, so there is nothing of
a record for it to reproduce. A name is an interpretation. Each of the three
is real work with a real residue; none of them determines a number in the
file, and the ledger now says so in arithmetic instead of prose.

## Layers 6, 7, 5 and 8

**6, the edge chain.** 100 boundary records over 14 ground sectors, in 69
segments, 0 unclassified: building_back 58, interior_doorway 19, end_wall 16,
backing 7. A residue of zero here is easy — `building_back` catches every
one-sided record — so the number that measures the FAMILY is its own share:
**16 of 100 records are a termination**, 65 are the void behind a building and
19 are a way in. The first version of this reader found NO end wall on a map
whose main street ends in three, because it bounded the outdoor NETWORK, which
contains them; the chain bounds the GROUND.

**7, the plan** — decisions section 20's acid test. Two edges, two junctions,
three islands, 23 blocks, 1 sector of residue, in plan units with one stated
conversion. Recovered, not assumed: bands of **1.0, 2.0 and 2.5 pu**, which
is section 1's 1024 / 2048 / 2560; a main street of 7.28 pu of carriageway
(AVENUE, residual 0.28) and 10.78 with its pavements; an east arm of 4.00 pu
(LANE, residual 1.00) and **6.00 with its pavement (ROW, residual exactly 0)**.

**5, the mechanisms.** 136 sentences — 52 sector mechanisms, 18 `kWallGib`
walls, 3 stacks, 63 tx→rx chains — each checked against the lessons of its
type under `maps/blood/mechanism/Vanilla` *before* being written down. The
reader reproduces the supervisor's inventory exactly, every figure of it.
Residue 397 of 890 wired records (44.61%), 330 of them XSPRITEs carrying no
wiring this reader reads.

*The chain had to be a sentence.* Without it every record that only listens
reads as residue and E3M1's biggest mechanism — channel 116, two switches
telling **159 records at once** — has no sentence at all. Writing the chains
took the residue from 86.07% to 44.61%.

**8, intent.** A mechanism is named by the modal PREFIX of the lesson FILES
teaching its (type, shape) — Blood's own vocabulary, counted — at a 60%
majority: **16 named `door`, 36 candidates, 84 refused**. A place is named
where exactly one measured rule fires: 4 `stepped_run`, 2 `street`, 4
candidates, **26 refused**. E2M3 named 8 of 340; the refusal is the part
copied.

## Every disagreement with the measured facts, final list

Confirmed by the readers, recovered rather than assumed: road tile 352 at
z 10240 (found as the base plane, without a tile); pavements +2048 (the rise
measured as 2048 on 11 of 11 steps); the kerb tile 6 on 11 of 11 road-side
records, none blocking; sky 3491 on all 45 parallax ceilings; 379 on 8 of the
10 wall-top masses; the T's three end walls s0, s339, s343, exactly the three
a ROAD record meets; SUN_BEARING 478 recovered as **479** build units, 0.18
degrees apart.

Disagreements, with numbers: E3M1 has **22** shade-boundary records over 24
street sectors, not 44 over 68, under any definition of the network; **16**
oblique shade edges, 14 in the cluster 82.87-86.42, not 20; its shadow deltas
are **12 x2, 24 x6, 26 x14**, median 26, with 20 of 22 outside the gate's
[8, 16]; `joins.py`'s pavement|pavement row cites s10/s11, which are solid
masses (`floor_z == ceiling_z == 8192`); `TILE_CLASSES["facade stone"]` is 400
and E3M1's is 414; 5 of 16 end-wall band records do not block and 4 of those
face sectors carrying type 600; `overlay.kerb_records` claims 81 records where
the map makes 11; `joins.is_water`'s panning clause never runs on a `LevelIR`
(4 of DWE3M10's 22 panning sectors lost); and
`reachability.classify_offmap` does NOT raise `TypeError` — decisions
section 14 is out of date.

All of them, with recommended defaults, are queue items 28a-28e, 29a-29e and
30a-30h.

## What the writer assumes that E3M1 does not do

A material runs across corners (E3M1 continues u on 88% of collinear
solid-solid joins and 15-51% of bends); a shadow step is 8-16 (E3M1's is
24-26); a kerb belongs on every island edge (11 of 81); "facade stone" is 400
(414); s10 and s11 are a pavement path (they are masses); an end wall stays
put (2 of 10 carry type 600); a chain has one receiver (one has 159); water is
readable from a `LevelIR` by `is_water` (its panning clause cannot see the
extra).

## Readers: reused, and new

Reused unchanged: `decompiler.decompile_level`, `tools/decompile_project`,
`texture_frame` (`resolve_run`, `_next_on_run`, `wall_z_peg`, `world_u`,
`continuity_rows`), `structures.detect_structures`, `joins.ROWS` (no row
added), `overlay.HeightIsland` and `kerb_records` (as the writer being
replayed), `light_field`'s constants (as the numbers being tested),
`channels` and `surface.RecordOwner` (as the ledger's shape),
`reachability.classify_offmap`, `curriculum.mine_map` and `mine_folder`,
`conditional.transmitters` / `conditional_edges` / `key_sprites`,
`viewplan.sector_area`.

New: `bloodmap/read_surfaces.py`, `read_joins.py`, `read_islands.py`,
`read_light.py`, `read_stairs.py`, `read_edges.py`, `read_plan.py`,
`read_mechanisms.py`, `read_intent.py`, `read_ledger.py`, `facts.py`,
`read_facts.py`. `tools/review_pack.py` was copied in from the main checkout
(where it is untracked) and extended additively with `--claims` and
`--candidates`; its orientation and colours are untouched.

## Review packs

All eight, in `projects/e3m1-decompiled/review/`, with 22 owner questions
across them, each naming a node with a recommended default. No
`answers-layer<N>.json` has arrived; when one does, every mark is fixed or
refuted by a measurement in the next report.

| pack | nodes | sectors unowned | questions |
| --- | --- | --- | --- |
| layer 1 | 37 | 108 | 1 |
| layer 2 | 208 | 100 | 2 |
| layer 3 | 11 | 361 | 3 |
| layer 4 | 8 | 10 | 3 |
| layer 5 | 105 | 258 | 3 |
| layer 6 | 6 | 329 | 3 |
| layer 7 | 22 | 11 | 3 |
| layer 8 | 7 | 313 | 2 |

## What the next map has to answer

The sleep phase of the research document: decompile a second map, refactor the
two programs, and promote what both needed to a macro — a macro that does not
lower residue on at least two maps is not adopted. E3M1's tail names three
candidates already: a surface that stops at a flat face rather than at a run;
a chain construct that fans out; and a block cut at its street frontages.
