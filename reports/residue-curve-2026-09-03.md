# The residue curve over the campaign, and the second map

P15, 2026-09-03. All eight layers' readers, run as a census over the 43
campaign maps — they are pure functions, so a whole decompilation runs on any
map without a project directory. Produced by
`projects/campaign-census/source/residue_curve.py`, stored as `census_layer`
facts in `projects/campaign-census/facts/`. Nothing here is typed.

**This report was re-run after the step-2 reader corrections landed, and six
of the 43 rows moved. The second-map choice moved with them.** What the first
version of this report said, and what is now true, is in "The curve moved"
below; the numbers here are the current ones.

**43 maps read, 0 failed, 36 with an outdoor network, 16 with a street in the
model's sense** (a road, an island standing on it, and a kerb at the join).

## The curve

Claimed share is the fraction of claimable fields with a claim, the same
measure E3M1's ledger reports. `road/is/kerb` is road sectors, islands, kerb
records. Per-layer numbers are claims.

| map | claimed | fields | of | residue | road/is/kerb | per-layer claims |
| --- | --- | --- | --- | --- | --- | --- |
| E1M6 | 7.107% | 12814 | 180310 | 3699 | 0/0/0 | 2:12397 4:2 5:415 |
| E4M6 | 7.038% | 9218 | 130967 | 3058 | 0/0/0 | 2:9021 4:1 5:196 |
| E2M8 | 6.730% | 1585 | 23551 | 530 | 0/0/0 | 2:1570 5:15 |
| **E4M8** | **6.669%** | 1631 | 24458 | 693 | **1/1/6** | 2:1530 4:4 5:85 6:12 |
| E2M7 | 6.525% | 8535 | 130803 | 3221 | 0/0/0 | 2:8122 5:413 |
| E2M5 | 6.514% | 13241 | 203256 | 5628 | 1/0/0 | 2:12993 4:4 5:244 |
| … | | | | | | |
| **E1M2** | **4.071%** | 4114 | 101049 | 2457 | **4/1/7** | 2:3951 4:3 5:151 6:9 |
| **E3M1** | **3.872%** | 4298 | 110998 | 2485 | **4/3/11** | 2:3992 **3:21** 4:17 5:206 6:64 |
| E6M8 | 3.325% | 935 | 28123 | 586 | 8/3/21 | 2:830 4:15 5:35 6:55 |
| E2M9 | 2.675% | 2021 | 75544 | 2523 | 3/0/0 | 2:1809 4:10 5:192 6:10 |
| E1M3 | 2.558% | 3331 | 130195 | 3014 | 4/0/0 | 2:2984 4:6 5:321 6:20 |

**Re-run 2026-09-03 after two changes to layer 3.** P14b's indoor law (item
37e) and P15's `facade` and `opening` (item 32c). Campaign residue falls from
**155 676 to 105 843 facts, a third of it gone in one row**; claimed share
falls by hundredths, because the indoor row describes a record by claiming a
`cstat` rather than a frame.

The full 43 rows are in `projects/campaign-census/references/residue-curve.json`.

**The curve's shape is one fact repeated 43 times: layer 2 makes 96% of every
claim in the campaign.** Over 43 maps the claims divide as layer 2 205 043,
layer 5 7556, layer 6 811, layer 4 247, layer 3 **21**, and layers 1, 7 and 8
nothing. Everything except layer 2 claims between 15 and 441 fields per map.

**Layer-3 CLAIMS have stopped being a measure of anything.** Before the indoor
law, four maps had layer-3 claims and the count ranked them; now the row that
describes most of the campaign's joins claims a `cstat` rather than a field,
so only E3M1 has any layer-3 claim at all and the "maps the join table
reaches" list has one entry. The measure to use from here is
`join_census.records_described`, which counts what the grammar can SAY rather
than what it happens to claim a field for. Queue item 38g. The claimed share therefore ranks maps roughly by wall count,
not by how well they are understood; the campaign's shares run 2.558% to
7.107%.

**And the more street a map has, the lower it ranks.** E1M3, E2M9, E6M8 and
E3M1 sit at the bottom, because a street is outdoor sectors whose fields the
readers mostly do not claim, while a map of dense interiors is wall records
that layer 2 does claim. The measure rewards the maps the street model has
least to say about.

## The curve moved, and so did the choice

The first run of this census predated three of my own step-2 reader
corrections. Re-running it under the corrected readers moved six rows:

| map | claimed share | road sectors | islands | kerb records |
| --- | --- | --- | --- | --- |
| E1M3 | 2.604 → 2.558 | 17 → 4 | 4 → 0 | 12 → 0 |
| E1M6 | 7.120 → 7.107 | 1 → 0 | 1 → 0 | 4 → 0 |
| E1M7 | 6.060 → 6.017 | 4 → 2 | — | — |
| E2M1 | 5.608 → 5.486 | 0 → 1 | — | — |
| E2M9 | 2.700 → 2.675 | 2 → 3 | 3 → 0 | 8 → 0 |
| E4M6 | 7.046 → 7.038 | 1 → 0 | 1 → 0 | — |

The cause is item 28c: **a raised outdoor mass carrying a sector type is a
mechanism at rest, not an island.** E1M3's "17 road sectors and 4 islands"
were partly a lift and a moving platform read as street furniture. Under the
corrected reader those maps have no island standing on their road, so they
have no street in the model's sense, and the street population falls from 19
to 16.

**The rule now has an unambiguous answer, and it is not the one I acted on.**
"Among maps with a street network, the largest claimed share" gives **E4M8**
(6.693%) both literally and with layer 2 excluded; the ambiguity that
triggered the stated E1M2 default is gone.

I had already decompiled E1M2 under the earlier curve. Rather than discard
either, **both are decompiled**: E4M8 because the rule names it, E1M2 because
it is the map the join grammar actually reaches — 12 layer-3 claims over 313
sectors against E4M8's 6 over 80. The maps the join table reaches at all are
still only four:

| map | layer-3 claims | road | islands | kerbs | sectors |
| --- | --- | --- | --- | --- | --- |
| E3M1 | 33 | 4 | 3 | 11 | 382 |
| E1M2 | 12 | 4 | 1 | 7 | 313 |
| E4M8 | 6 | 1 | 1 | 6 | 80 |
| E2M6 | 2 | 1 | 2 | 2 | 237 |

Three decompilations rather than two also makes the sleep phase's rule bite
harder: a macro must lower residue on two of three, not on both of two. Every
candidate survives it, which is the sleep phase's own result — see
[the sleep-phase report](sleep-phase-2026-09-03.md). None of the five moved
when the indoor law landed, either, which is the classification working: a row
gap and a construct gap are different things.

## Findings from running every reader on every map

**Nothing failed this time.** The `KeyError(144)` that stopped E6M7's layer 1
is still there in `decompiler.decompile_level`; the census runs the other
seven layers around it and records `layer1_error` on the row, which is why the
failure count is 0 and E6M7 still has a curve. Queue item 34a stands.

**16 of 43 maps have a street in the model's sense.** 36 have an outdoor
network — the flag is true wherever any outdoor ground exists — but only 16
have a road with an island standing on it and a kerb at the join. That is the
population the street model is about, and it is under half the campaign, and
it shrank by three when a reader stopped mistaking mechanisms for islands.

## The suite

Quoted in [the sleep-phase report](sleep-phase-2026-09-03.md), which was run
last.
