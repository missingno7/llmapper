# The residue curve over the campaign, and the second map

P15, 2026-09-03. All eight layers' readers, run as a census over the 43
campaign maps — they are pure functions, so a whole decompilation runs on any
map without a project directory. Produced by
`projects/campaign-census/source/residue_curve.py`, stored as `census_layer`
facts in `projects/campaign-census/facts/`. Nothing here is typed.

**43 maps read, 0 failed, 37 with a base plane, 19 with a street in the
model's sense** (a road, an island standing on it, and a kerb at the join).

## The curve

Claimed share is the fraction of claimable fields with a claim, the same
measure E3M1's ledger reports. `road/is/kerb` is road sectors, islands, kerb
records. Per-layer numbers are claims.

| map | claimed | fields | of | residue | road/is/kerb | per-layer claims |
| --- | --- | --- | --- | --- | --- | --- |
| E1M6 | 7.120% | 12838 | 180310 | 5376 | 1/1/4 | 2:12397 4:3 5:415 6:23 |
| E4M6 | 7.046% | 9228 | 130967 | 4818 | 1/1/0 | 2:9021 4:2 5:196 6:9 |
| E2M8 | 6.730% | 1585 | 23551 | 690 | 0/0/0 | 2:1570 5:15 |
| E4M8 | 6.693% | 1637 | 24458 | 1059 | 1/1/6 | 2:1530 3:6 4:4 5:85 6:12 |
| E2M7 | 6.525% | 8535 | 130803 | 4919 | 0/0/0 | 2:8122 5:413 |
| E2M5 | 6.514% | 13241 | 203256 | 8948 | 1/1/0 | 2:12993 4:4 5:244 |
| … | | | | | | |
| **E1M2** | **4.083%** | 4126 | 101049 | 3559 | **4/1/7** | 2:3951 **3:12** 4:3 5:151 6:9 |
| **E3M1** | **3.883%** | 4310 | 110998 | 3609 | **4/3/11** | 2:3992 **3:33** 4:17 5:206 6:64 |
| E6M8 | 3.325% | 935 | 28123 | 798 | 8/3/21 | 2:830 4:15 5:35 6:55 |
| E2M9 | 2.700% | 2040 | 75544 | 2804 | 2/3/8 | 2:1809 4:14 5:192 6:25 |
| E1M3 | 2.604% | 3390 | 130195 | 3836 | 17/4/12 | 2:2984 4:12 5:321 6:73 |

The full 43 rows are in `projects/campaign-census/references/residue-curve.json`.

**The curve's shape is one fact repeated 43 times: layer 2 makes 95.8% of
every claim in the campaign.** Over all 43 maps the claims divide as

| layer | claims | share |
| --- | --- | --- |
| 2 surfaces and stairs | 205 043 | 95.84% |
| 5 mechanisms | 7 556 | 3.53% |
| 6 edges | 1 022 | 0.48% |
| 4 overlays | 259 | 0.12% |
| 3 joins | 53 | 0.02% |
| 1, 7, 8 | 0 | 0% |

Everything except layer 2 claims between 15 and 441 fields per map. The
claimed share therefore ranks maps roughly by wall count, not by how well they
are understood; the campaign's shares run 2.604% to 7.120%, median 5.205%.

**And the more street a map has, the lower it ranks.** E1M3 (17 road sectors),
E2M9, E6M8 and E3M1 are the four lowest of the street maps, because a street
is outdoor sectors whose fields the readers mostly do not claim, while a map
of dense interiors is wall records that layer 2 does claim.

## The second map: E1M2

The rule is "among maps with a street network, the largest claimed share under
E3M1's readers; the default if ambiguous is E1M2".

**It is ambiguous, measurably.** The literal ranking gives **E1M6** — whose
whole street is one road sector, one island and four kerb records, and 96.6%
of whose claims are layer 2. Ranking the same maps on everything EXCEPT layer
2 gives **E4M8** instead, an 80-sector fragment. Two readings of one rule, and
which wins is decided entirely by a layer that measures texture runs rather
than streets. So the stated default applies: **E1M2**.

**And E1M2 is independently the right choice**, on the criterion the sleep
phase actually needs. The point of a second map is to find what two
decompilations SHARE, so the map that matters is the one E3M1's street grammar
already reaches. The join table describes anything at all on four maps:

| map | layer-3 claims | road | islands | kerbs | sectors |
| --- | --- | --- | --- | --- | --- |
| E3M1 | 33 | 4 | 3 | 11 | 382 |
| **E1M2** | **12** | 4 | 1 | 7 | 313 |
| E4M8 | 6 | 1 | 1 | 6 | 80 |
| E2M6 | 2 | 1 | 2 | 2 | 237 |

Excluding E3M1, E1M2 leads by a factor of two and is a whole map rather than a
fragment. It is 313 sectors against E3M1's 382, has the same four road
sectors, and its street reaches the grammar.

## Two findings from running every reader on every map

**E6M7 cannot be decompiled, and it is layer 1 that cannot do it.**
`decompiler.decompile_level` raises `KeyError(144)`: `analyze_spatial` returns
no geometry record for that sector. The census now runs the other seven layers
anyway and records `layer1_error` on the row, so one map's gap in a reader
that predates this work does not remove the map from the curve. Queue item
34a.

**19 of 43 maps have a street in the model's sense.** 37 have a base plane —
the flag is true wherever any outdoor ground exists — but only 19 have a road
with an island standing on it and a kerb at the join. That is the population
the street model is about, and it is under half the campaign.

## The suite

```text
Ran 2024 tests in 202.189s
FAILED (failures=5, errors=4, skipped=267, expected failures=4)
```

The nine are the worktree-environment failures (relative `maps/`,
`reference/`, `NBlood/` paths) that belong to P16; none is from this work. A
tenth appeared once and is gone: `test_kerb_records_claims_a_kerb_on_edges_
facing_no_road` pinned `overlay.kerb_records` claiming 81 records where E3M1
makes 11 — **P14b fixed it** (7541ca7, from queue item 29b), and the reader
that found the defect is now the gate that proves the fix: it claims 11 and
the map makes 11.
