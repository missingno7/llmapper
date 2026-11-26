# Three censuses over the campaign, and the shade-step envelope

P15, 2026-09-03. Decisions section 30 assigns items 28b, 28d, 28e and 29a to
the readers before the writer changes anything. Every number below is produced
by `projects/campaign-census/source/three_censuses.py` over the 43 campaign
maps and stored in `projects/campaign-census/facts/`; none is typed.

Readers: `bloodmap/read_census.py` (new) and
`bloodmap.read_light.shade_step_envelope` (P14b's, adopted — see 29a).
**Nothing was added to `joins.ROWS`.** The indoor rows below are proposals with their evidence, and
P14b decides.

## 28b — what a termination's band wears

The band is read on the GROUND's record, the side a body sees from the street.
**Re-run after item 32c**, which split `facade` off `end_wall`: 179 records
before and 179 after, 31 of them under a new name. The split is exact and
nothing left the census.

| pair | records | maps | top tiles |
| --- | --- | --- | --- |
| `road\|end_wall` | 116 | 16 | 2490 (28), 449 (17), 28 (16), 5 (8), 91 (8), 95 (7) |
| `road\|facade` | 27 | 4 | 91 (15), 2490 (9), 177 (2), 414 (1) |
| `pavement\|end_wall` | 32 | 5 | 120 (12), 68 (10), 414 (4), 270 (3), 95 (1) |
| `pavement\|facade` | 4 | 1 | 414 (2), 417 (2) |

**`TILE_CLASSES["facade stone"] = 400` is worn by NONE of the 179 records.**
That was true before the split and is true of every one of the four rows
after it. E3M1's 414 accounts for 9. The class has 17 distinct members on the
road side alone, led by 2490 (24%) and 91 (21%) — and the split says something
about those two: **91 leads the buildings (15 of 27) and 2490 leads the plain
terminations (28 of 116)**, which is the first evidence that the campaign
dresses a facade differently from a wall.

**The row's `cstat=1` is the campaign's exception, not its rule.** 104 of 116
`road|end_wall` band records do NOT block (89.7%); 28 of 32
`pavement|end_wall` do not (87.5%); 26 of 27 `road|facade` do not (96.3%).
The one row that blocks throughout is `pavement|facade` — 4 of 4 — and all
four are E3M1's single building.

It is not a height rule. On `road|end_wall`, blocking records stand a median
88 064 above the road (5.2 player heights) and non-blocking ones a median
65 536, with quartiles 24 576 and 393 216 — the non-blocking set holds both
the lowest masses and the highest.

> **These numbers moved twice when the reader's kind moved, and that is the
> point.** Before item 28c the same census gave 285 road-side records over 21
> maps, 2 of them wearing 400, with 449 leading at 75; naming a raised mass
> that carries a sector type a MECHANISM AT REST rather than a termination
> removed 136 of them and every 400 with them. Item 32c then split the
> buildings out of what remained. A census is conditioned on the kind that
> defines its population (section 22a), and both earlier figures are kept here
> so the conditioning is visible rather than silently overwritten.

> **Read the reader's kind before reading the number.** `end_wall` is now "an
> outdoor mass, carrying no sector type, holding no room, that no body can
> step onto". Its step quartiles are 24 576 and 393 216, so a quarter of these
> masses still stand under two player heights and are ledges rather than
> terminations. A narrower kind is a further reader change and would want the
> owner's word — queue item 37a.

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

**The census is `read_light.shade_step_envelope`, which landed on main from
this queue item while this report was being written — and its measurement is
better than the one this section first carried.** It counts one entry per
BOUNDARY; mine counted one per record, so a two-sided wall was weighed twice
and a sector pair sharing several walls weighed more than once. Theirs is what
the writer's gate calls, so it is what the census reports, and my duplicate
implementation is gone.

| network | boundaries | maps | median | quartiles | the gate's [8, 16] holds |
| --- | --- | --- | --- | --- | --- |
| `largest_outdoor_component` | 192 | 36 | **13.0** | [9.0, 18.75] | 50.5% |
| `all_outdoor` | 365 | 37 | **12** | [8.0, 16.0] | 52.3% |

Section 30 names `largest_outdoor_component` — "a city's street". Under it the
median is 13 and the quartile envelope is **[9, 18.75]**, and the interval the
gate carries today holds half its boundaries.

The two implementations also differed on what "the largest outdoor component"
IS, and the difference is worth stating: theirs takes every parallax sector,
mine took only walkable ones and picked the largest by area rather than by
count. Theirs finds a component on 36 maps, mine on 21. Neither is wrong; the
gate uses theirs, and the reason to say so is that the same name meant two
populations for a day.

E3M1's own 24–26 is the precedent's value and is outside both envelopes; that
is recorded, not repaired.

## What this leaves for the writer

- **28b:** `facade stone` is not 400 in the campaign — it is worn by none of
  the 179 end-wall band records — and the row's blocking clause holds on 21 of
  them (11.7%), 13 of the 143 road-side (9.1%). Both are P14b's to change or
  keep, with the numbers now available.
- **28d:** no change. The writer already matches the campaign.
- **28e:** eleven proposed rows, and an argument that they are one law.
- **29a:** the envelope is a reader call, not a constant, and the call
  is P14b's `shade_step_envelope` — one census, not two.
