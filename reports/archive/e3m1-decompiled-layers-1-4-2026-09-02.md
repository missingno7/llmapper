# E3M1 decompiled: layers 1-4, the stop-and-report

P15, 2026-09-02, branch `e3m1-decompiled` from `blood-city-arcade`
(2267716, 8bf4819, 56a1dd5, 3a0e8e2). Project
`projects/e3m1-decompiled`. Every number below is read off
`maps/blood/campaign/E3M1.MAP` (CRC `a6465024`, 382 sectors, 2481 walls,
807 sprites) by a reader in `bloodmap/`; none is typed in. No writer
module was edited.

## The ledger, in the shape the supervisor fixed

One shared `(record, field) -> [claims]` ledger for all layers
(`bloodmap.read_ledger.ClaimLedger`), in `surface.RecordOwner` /
`channels.RegionLedger` form at field granularity. A CLAIM means: this layer's
model determines this field's value and replaying the model reproduces it.
Fields the FORMAT owns (`wall_ptr`, `wall_count`, `point2`, `next_wall`,
`filler`, `extra`, `reference`) are not claimable and are excluded by name --
12 282 of them.

```text
E3M1: 4040 of 110998 claimable fields have a claim -- 3.64%

  layer 1  space tree                     0 fields   0.0%    {}
  layer 2  surfaces, frames, structures  3992        3.596%  frame 3895, floor_z 97
  layer 3  joins                            33       0.03%   frame 33
  layer 4  overlays                         17       0.015%  floor_z 9, shade 8

  conflicts on exclusive channels : 0
  corroborated exclusive fields   : 2
  sector : 271 of 382 with no claimed field, median 0%, best 10.5%
  wall   : 1682 of 2481 with no claimed field, median 0%, best 42.9%
  sprite : 807 of 807 with no claimed field
```

**Layer 1 claims nothing, and that is the finding rather than an omission.**
The space tree partitions sectors; a partition is not a value. A geometric
hierarchy tells you where you are and nothing about what anything is, and the
ledger now says so in arithmetic instead of prose.

## Per layer: residue in records and sectors, and as a percentage

| layer | population | explained | residue | % |
| --- | --- | --- | --- | --- |
| 1 space tree | 382 sectors | 274 | **108 sectors** | 28.27 |
| 2 surfaces + structures | 2481 wall records | 779 | **1702 records** | 68.60 |
| 3 joins | 1386 two-sided records | 74 | **1312 records** | 94.66 |
| 4 overlays | 24 sectors + 26 steps + 16 oblique edges = 66 items | 33 | **32 items** | 48.48 |

Layer 2's residue splits into 574 records broken off a same-material
neighbour, 1075 with no same-material neighbour at all, and 53 a fitted frame
does not reproduce. Layer 3's is 31 surface pairs the table has no row for, of
which 1122 records are `interior|interior`. Layer 4's is 15 sectors whose
shade is not `base + k*12`, 15 floor steps that are not the island rise, and 2
oblique shade edges not at the sun's bearing.

## Every disagreement with the measured facts I was handed

**Confirmed, recovered rather than assumed.**

- roads are tile 352 at z 10240: the reader finds the base plane at z 10240
  and the road as `{3, 7, 8, 45}` **without looking at a tile** -- it is the
  level the islands stand on;
- pavements at 8192, +2048: the rise is measured as **2048 on 11 of 11
  steps** inside the street network;
- the kerb is tile 6 on the road-side record, 11 of 11: **exactly so**, and
  none of the 11 blocks;
- sky 3491 on the street ceilings: 45 parallax-ceiling sectors, all 3491;
- 379 is the roof and wall-top tile: every one of the 10 wall-top masses the
  reader finds by the autostep criterion wears 379 except the two at 2915
  and 255 (s236, s237);
- the T of the main street ends in three end walls, s0, s339, s343: **exactly
  those three are met by a ROAD record** (s7->s0, s3->s339, s45->s343);
- SUN_BEARING 478: the reader recovers **479 build units**, 0.18 degrees
  apart, with the axis from the oblique boundaries and the sign from the
  perpendicular ones.

**Disagreements, with their numbers.**

1. **"44 shade boundaries over 68 street sectors"** -- the reader finds **22
   shade-boundary records over 24 street sectors**. No definition of the
   network reproduces 44/68: all parallax-ceiling sectors gives 22 over 45;
   parallax plus one ring of neighbours gives 22 same-z (66 any-z) over 76.
   22 is exactly half of 44, which suggests the earlier count was over a
   wider network or counted differently; I cannot reproduce it either way.
2. **"20 oblique shade edges at ~84 degrees"** -- the reader finds **16
   oblique shade-boundary records**, 14 of them within 8 degrees of the
   median (spread 82.87-86.42), and 2 at 71.08 (walls 643 and 857, the
   s118|s165 boundary) that are residue. The BEARING is confirmed; the count
   is not.
3. **"the light field quantises to base + k*12"** -- E3M1's own deltas are
   **12 x2, 24 x6, 26 x14**, median 26. `base + k*12` reproduces only shades 8
   and 32; the map also uses 14, 24, 34 and 46, and 15 of its 24 street
   sectors fit no level. **20 of its 22 boundary records lie outside the
   gate's envelope [8, 16]** -- the map the street language was read from
   fails the light gate the writer enforces. The base (8) and the level count
   (3, inside 2-4) do hold.
4. **`joins.py`'s pavement|pavement row cites "E3M1 s10/s11: a pavement-only
   path"** -- both sectors have `floor_z == ceiling_z == 8192`. They are
   solid masses; Build draws nothing inside one and no body stands in it. The
   row is still attested (14 pavement|pavement records, between the
   shadow-cut bands); only its citation is wrong.
5. **`TILE_CLASSES["facade stone"] = 400`** -- E3M1's 3 road|end_wall records
   all wear **414**; its 13 pavement|end_wall records wear
   `{414: 6, 181: 2, 384: 2, 417: 2, 488: 1}`. 400 is Gravesend's choice.
6. **road|end wall is "blocking"** -- 11 of 16 band records block. The 5 that
   do not: 4 face sectors 172 and 174, which carry **sector type 600** and
   move; 1 faces the raised ledge s237.
7. **`overlay.kerb_records` says which records carry the kerb** -- replayed
   over the three recovered islands it claims **81** records where E3M1 makes
   **11**. It iterates the island's outline and never reads its
   `ground_outline` argument, so it asks for a kerb on the 56 edges facing the
   void, the 18 facing an interior and the 13 facing an end wall.
8. **`joins.is_water`'s panning clause never runs on a `LevelIR`** -- it reads
   `getattr(sector, "extra", None)`, which is `None` there (the extra is under
   the key `"blood"`), so only its palette clause fires. On DWE3M10, the map
   the shore and sea rows were mined from, that loses 4 of its 22 panning
   sectors (393-396, palette 0).
9. **"`reachability.classify_offmap` raises `TypeError` on every map"**
   (section 14) -- it does not. On E3M1 it returns 374 sectors reached, 8
   off-map, 2 logic closets and 6 bare. The only reader that could find an
   enclosure's backdrop masses works.

## Every pair, edge or step the readers could not classify

- **surface pairs with no row (31 keys, 1312 records)**, folded to unordered
  pairs: `interior|interior` 1122, `interior|solid` 66, `interior|pavement`
  36, `end_wall|solid` 26, `end_wall|end_wall` 20, `pavement|solid` 14,
  `end_wall|interior` 12, `outdoor_ground|pavement` 8, `solid|solid` 6,
  `interior|outdoor_ground` 2.
- **oblique shade edges not at the bearing (2)**: walls 643 and 857, axis
  71.08 degrees, the s118|s165 boundary.
- **floor steps that are not the island rise (15)**: 21504, 33792, 65536 x3,
  67584, 98304 x6, 99328, 100352 x2 -- every one of them a wall top rather
  than a step.
- **the stair residual (1)**: sector 347, in a run of 19 whose rise is not
  constant.
- **records a fitted frame does not reproduce (53)**, in `x_repeat` (rounding
  against the run's modal scale), `x_panning` and `y_panning`.

## The join census

```text
described, 74 records over 8 rows:
  pavement|pavement equal    14      end_wall|pavement b_below  13
  pavement|end_wall b_above  13      pavement|road b_below      11
  road|pavement b_above      11      road|road equal             6
  end_wall|road b_below       3      road|end_wall b_above       3

what the band records wear, and whether they block:
  road|pavement b_above      {6: 11}                              11/11 the
                                                                  table's tile,
                                                                  blocking {0: 11}
  road|end_wall b_above      {414: 3}                             0/3, blocking {1: 3}
  pavement|end_wall b_above  {181:2, 384:2, 414:6, 417:2, 488:1}  0/13,
                                                                  blocking {0:5, 1:8}

undescribed, 1312 records over 31 pairs -- the table describes the street and
nothing inside the buildings.
```

## What the writer assumes that E3M1 does not do

- **that a material runs across corners.** `RUN_BREAK_DEGREES` is 100, so a
  run carries through every bend. E3M1 continues u on 88% of collinear
  solid-solid joins but only 51% of solid-solid bends, 28% of solid-portal
  bends, 15% of solid-portal reflex corners. 514 of 1537 same-tile joins
  continue (33.4%); a surface here is a FLAT FACE.
- **that a shadow step is 8-16.** E3M1's is 24-26.
- **that a kerb belongs on every island edge.** It belongs on the edges facing
  the road: 11 of 81.
- **that "facade stone" is 400.** Here it is 414.
- **that s10 and s11 are a pavement path.** They are solid masses.
- **that an end wall stays put.** Two of the ten wall-top masses carry sector
  type 600.
- **that water can be read off a `LevelIR` by `is_water`.** Its panning clause
  cannot see the extra.

## Which reader I wrote from scratch and which I reused

| reader | new or reused |
| --- | --- |
| `decompiler.decompile_level`, `tools/decompile_project` | **reused unchanged** (layer 1) |
| `texture_frame.resolve_run`, `_next_on_run`, `wall_z_peg`, `world_u`, `continuity_rows` | **reused** as the replay and the cross-check |
| `structures.detect_structures` | **reused** (the stepped runs) |
| `joins.ROWS`, `joins.rule`, `TILE_CLASSES` | **reused**; no row added |
| `overlay.HeightIsland`, `overlay.kerb_records` | **reused** as the writer being replayed |
| `light_field.STEP`, `STEP_ENVELOPE`, `MAX_LEVELS`, `LEVEL_FLOOR` | **reused** as the numbers being tested |
| `channels.CHANNELS`, `surface.RecordOwner` | **reused** as the ledger's shape |
| `reachability.classify_offmap` | **reused** (and found to work) |
| `viewplan.sector_area` | reused |
| `bloodmap/read_surfaces.py` | **new** |
| `bloodmap/read_joins.py` (surface kinds + census) | **new** |
| `bloodmap/read_islands.py` | **new** |
| `bloodmap/read_light.py` | **new** |
| `bloodmap/read_stairs.py` | **new** |
| `bloodmap/read_ledger.py` | **new** |
| `bloodmap/read_edges.py` | **new** (layer 6, written, not yet staged) |
| `tools/review_pack.py` | copied in from the main checkout, where it is untracked; extended additively with `--claims` |

## Review packs

`projects/e3m1-decompiled/review/layer{1,2,3,4}.html`, one per layer, from
`tools/review_pack.py`. Nodes are what that layer's reader decided; a sector
no node owns is that layer's residue, drawn rather than claimed. Orientation
(+Y down, XMapEdit's) and the explicit colours are untouched.

| pack | nodes | sectors unowned | questions |
| --- | --- | --- | --- |
| layer 1 | 37 | 108 | 1 |
| layer 2 | 208 | 100 | 2 |
| layer 3 | 11 | 361 | 3 |
| layer 4 | 8 | 10 (plus an explicit out-of-scope node for the 358 indoors) | 3 |

With `--claims`, each pack shows one aspect at a time and a clicked sector's
fact panel lists every claim on its fields -- layer, owner, value, reason --
then every field of the sector record nothing claims. Questions are beside the
pack in `questions-layer<N>.json`, never nodes: `review_pack`'s deepest-owner
rule would let a question own the sectors it asks about and colour the map by
our doubts. No `answers-layer<N>.json` has arrived yet; every mark that does
will be fixed or refuted by a measurement in the next report.

## The suite

Worktree run, to `work/suite-layer4.log`:

```text
Ran 1915 tests in 179.360s
FAILED (failures=5, errors=4, skipped=267, expected failures=4)
```

All nine failures are worktree-environment, not regressions: they spell
relative `maps/blood/...`, `reference/blood` and `NBlood/source/...` paths,
which a worktree does not have and which the rules forbid junctioning in
(`test_attested_constructs` x2, `test_curriculum` x3, `test_rules` x2,
`test_assembly`, `test_pattern_zoo`). Running those same five modules in the
main checkout, which has both directories, gives
`Ran 125 tests`, `OK (skipped=1, expected failures=1)`.

## What layers 6, 7, 5 and 8 must answer first

- **6, the edge chain** (written, measured, not yet committed): E3M1's ground
  is 14 sectors and its boundary is **100 records in 69 segments** --
  building_back 58, interior_doorway 19, end_wall 16, backing 7, and **0
  unclassified**. Defining the boundary as the outdoor NETWORK's outline
  swallowed every end wall (the first run found none on a map whose T ends in
  three); the boundary is the GROUND's outline, and end walls are what it
  meets.
- **7, the plan**: the acid test. The solver's inverse has to recover a street
  graph with width classes, islands with bands and blocks with envelopes, in
  `city_plan.py`'s language, with no picnums and no z.
- **5, the mechanisms**: the denominator is the supervisor's inventory -- 133
  XSECTORs, 41 XWALLs, 716 XSPRITEs; sector types 600 x34, 614 x6, 615 x4,
  616 x1, 617 x6, 618 x1; 18 walls of type 511; 26 tx and 54 rx; 4 key-locked
  -- and every one becomes a sentence compared against the curriculum lesson
  of its kind under `maps/blood/mechanism`, or a named residue.
- **8, intent**: names only where a measurement distinguishes, with an
  explicit refusal elsewhere.
