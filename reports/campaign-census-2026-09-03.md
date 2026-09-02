# Three censuses over the campaign, and the shade-step envelope

P15, 2026-09-03. Decisions section 30 assigns items 28b, 28d, 28e and 29a to
the readers before the writer changes anything. Every number below is produced
by `projects/campaign-census/source/three_censuses.py` over the 43 campaign
maps and stored in `projects/campaign-census/facts/`; none is typed.

Readers: `bloodmap/read_census.py` (new) and
`bloodmap.read_light.shade_step_envelope` (new). **Nothing was added to
`joins.ROWS`.** The indoor rows below are proposals with their evidence, and
P14b decides.

## 28b — what a termination's band wears

The band is read on the GROUND's record, the side a body sees from the street.

| pair | records | maps | top tiles |
| --- | --- | --- | --- |
| `road\|end_wall` | 149 | 17 | 2490 (36), 91 (31), 449 (17), 28 (16), 5 (8), 95 (7) |
| `pavement\|end_wall` | 42 | 6 | 120 (12), 68 (10), 414 (6), 2490 (5), 270 (3) |

**`TILE_CLASSES["facade stone"] = 400` is worn by NONE of the 191 records.**
E3M1's 414 accounts for 9 of them. The class has 17 distinct members on the
road side alone, led by 2490 (24%) and 91 (21%).

**The row's `cstat=1` is the campaign's exception, not its rule.** 136 of 149
`road|end_wall` band records do NOT block (91.3%); 34 of 42 `pavement|end_wall`
do not (81.0%). E3M1's three blocking records are the minority behaviour.

It is not a height rule. Blocking records stand a median 88 064 above the road
(5.2 player heights) and non-blocking ones a median 66 560, with quartiles
32 768 and 393 216 — the non-blocking set holds both the lowest masses and the
highest.

> **These numbers moved when the reader's kind moved, and that is the point.**
> Run before item 28c, the same census gave 285 road-side records over 21
> maps, 2 of them wearing 400, with 449 leading at 75. Naming a raised mass
> that carries a sector type as a MECHANISM AT REST rather than a termination
> removed 136 records — nearly half — and every one of the 400s with them. A
> census is conditioned on the kind that defines its population (section 22a),
> and the first figures are kept here so the conditioning is visible rather
> than silently overwritten.

> **Read the reader's kind before reading the number.** `end_wall` is now "an
> outdoor mass, carrying no sector type, that no body can step onto". Its step
> quartiles are 32 768 and 393 216, so a quarter of these masses still stand
> under two player heights and are ledges rather than terminations. A narrower
> kind is a further reader change and would want the owner's word — queue item
> 32a.

## 28d — where a material stops, by bend class

| join class | u continues | of | rate | maps |
| --- | --- | --- | --- | --- |
| collinear solid-solid | 6336 | 6760 | **93.7%** | 42 |
| collinear solid-portal | 3551 | 4442 | 79.9% | 43 |
| bend solid-solid | 13591 | 20021 | **67.9%** | 43 |
| collinear portal-portal | 2043 | 3588 | 56.9% | 43 |
| bend solid-portal | 4498 | 13366 | 33.7% | 43 |
| bend portal-portal | 8341 | 28216 | 29.6% | 43 |
| reflex solid-portal | 699 | 2836 | 24.6% | 43 |
| reflex portal-portal | 401 | 1910 | 21.0% | 43 |
| reflex solid-solid | 166 | 871 | **19.1%** | 39 |

**This corrects my own E3M1 reading.** Report 28d said "E3M1 restarts its
materials at corners… a surface here is a FLAT FACE", from E3M1's 50.6% on
bend solid-solid. The campaign's rate is **67.9%** — Blood does carry a run
through an ordinary bend, and it is E3M1 that is the outlier at 50.6%. The
writer's `RUN_BREAK_DEGREES = 100` — carry through a bend, stop at a reflex
corner — is what the campaign does: 68% against 19%. **No change is proposed
to the writer.**

## 28e — interior meeting interior

49 821 records over 25 classes, keyed on what the two floors and the two
ceilings do. The classes come in mirrored pairs, because both records of a
join are counted and each sees the other's relation reversed.

| class | records | share | maps | draws |
| --- | --- | --- | --- | --- |
| floor level \| ceiling level | 13852 | 27.8% | 43 | 132 of 13852 |
| floor far above \| ceiling level | 5382 | 10.8% | 41 | 5382 of 5382 |
| floor far below \| ceiling level | 5382 | 10.8% | 41 | 22 of 5382 |
| floor level \| ceiling far below | 3326 | 6.7% | 43 | 3326 of 3326 |
| floor level \| ceiling far above | 3326 | 6.7% | 43 | 5 of 3326 |
| floor a step up \| ceiling level | 3147 | 6.3% | 42 | 3147 of 3147 |
| floor a step down \| ceiling level | 3147 | 6.3% | 42 | 5 of 3147 |
| floor level \| ceiling a step down | 1801 | 3.6% | 39 | 1801 of 1801 |
| floor level \| ceiling a step up | 1801 | 3.6% | 39 | 5 of 1801 |
| floor far above \| ceiling far below | 1611 | 3.2% | 42 | 1611 of 1611 |
| floor far below \| ceiling far above | 1611 | 3.2% | 42 | 54 of 1611 |

Eleven classes clear the proposal floor (2% of records and more than one map).

**The `draws` column is the engine, not the campaign, and saying so is the
point.** It is `wallVisible`: a two-sided record draws where a step exposes it
on its own side. So the mirrored pairs above are not two rules but one — *the
band is on the side that stands above* — which is the same law the kerb states
outdoors, now measured on 49 821 indoor records. An indoor grammar does not
need eleven rows; it needs that one law plus a tile class per context.

**The residual is the evidence about authorship.** 132 `level | level`
records draw where the geometry exposes nothing, and **every one of them is
overridden by hand: 126 masked, 6 one-way.** Those 132 are what an indoor
grammar would have to describe as a decision rather than derive.

## 29a — the shade step, by network definition

The gate must name its network, because the answer moves with it.

| network | boundaries | maps | median | q1 | q3 | mean | the gate's [8, 16] holds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `largest_outdoor_component` | 362 | 21 | **15** | 8 | 18 | 14.15 | 164 (45.3%) |
| `all_parallax` | 1362 | 29 | **12** | 8 | 16 | 14.91 | 766 (56.2%) |

Section 30 names `largest_outdoor_component` — "a city's street". Under it the
median is 15 and the quartile envelope is **[8, 18]**, and the interval the
gate carries today holds under half its boundaries.

`shade_step_envelope(network=...)` is in `read_light` for P14b's gate to call.
E3M1's own 24–26 is the precedent's value and is outside both envelopes; that
is recorded, not repaired.

## What this leaves for the writer

- **28b:** `facade stone` is not 400 in the campaign — it is worn by none of
  the 191 end-wall band records — and the row's blocking clause holds on 8.7%
  of the road-side ones. Both are P14b's to change or keep, with the numbers
  now available.
- **28d:** no change. The writer already matches the campaign.
- **28e:** eleven proposed rows, and an argument that they are one law.
- **29a:** the envelope is a reader call, not a constant.
