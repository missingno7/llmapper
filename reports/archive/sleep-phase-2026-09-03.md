# The sleep phase: three decompilations, and five macros

P15, 2026-09-03. Research section 2.5: after a second map, refactor the
programs, name what both needed, promote it to a macro, and measure the
residue each would lower per map per layer. Three maps are decompiled rather
than two — **E3M1**, **E1M2** and **E4M8** — for the reason in
[the residue curve](residue-curve-2026-09-03.md): the curve moved under my own
step-2 reader corrections and the second-map rule stopped naming E1M2.

Every number below is a query over the fact stores, run by
`projects/campaign-census/source/sleep_phase.py`, stored in
`projects/campaign-census/references/sleep-phase.json`. Nothing is typed.

**I have added no constructor to bloodmap.** The macro list is a proposal for
P14b, who owns `bloodmap/city.py`.

## The first result is that there is nothing to refactor

The three decompilations run **byte-identical stage code**:

```text
diff -rq --exclude=__pycache__ projects/e3m1-decompiled/source projects/e1m2-decompiled/source
diff -rq --exclude=__pycache__ projects/e3m1-decompiled/source projects/e4m8-decompiled/source
```

Both are silent. A second map is what forced that: E3M1's program had its own
name and its own findings written into it, and running it on another map
produced sentences that were true of Gravesend over another map's numbers.
Separating the two took four kinds of change, and all four were the same
mistake:

| what E3M1's program did | what it does now |
| --- | --- |
| titled its trees and packs `"E3M1 -- …"` | `f"{MAP_NAME} -- …"`, derived from the project directory and cross-checked against `provenance.json` |
| asserted E3M1's measurements as the model's ("400 is the facade tile", "the step is 24-26") | states the campaign census, and says "E3M1's precedent" where the number is E3M1's |
| asked owner questions whose answers were already in E3M1's numbers | asks them only where the map still disagrees |
| named review nodes that exist on E3M1 (`sentence:channel:189`, `kind:room_over_room`) | derives the node, and adds it to the tree if the question needs one the tree truncated |

The fourth of those was not cosmetic: on E1M2 and E4M8 the old code **crashed**
five times — a missing `sign` dict where a map has no oblique shade edge, a
missing `casters` census behind it, a chain outside the first 40 of its kind,
a `kind:room_over_room` node on a map with no stack, a named mechanism on a
map that names none. Each was a place where a program had quietly assumed a
map, and only a second map could find them. Two of the five were fixed in the
reader instead of the caller, both by the same rule already applied to
`sun_axis`: **return the same keys whether or not anything was found.**

## Per map, per layer

Residue is facts, not fields; the ledgers are in each project's
`residue-ledger.json`.

| layer | E3M1 claims | E3M1 residue | E1M2 claims | E1M2 residue | E4M8 claims | E4M8 residue |
| --- | --- | --- | --- | --- | --- | --- |
| 1 space tree | 0 | 108 | 0 | 110 | 0 | 24 |
| 2 surfaces, frames, structures | 3992 | 1650 | 3951 | 1626 | 1530 | 539 |
| 3 joins | 21 | 196 | 0 | 122 | 0 | 16 |
| 4 overlays | 17 | 24 | 3 | 7 | 4 | 1 |
| 5 mechanisms | 206 | 397 | 151 | 460 | 85 | 81 |
| 6 edge chain | 64 | 0 | 9 | 0 | 12 | 0 |
| 7 plan | 0 | 1 | 0 | 0 | 0 | 0 |
| 8 intent | 0 | 109 | 0 | 132 | 0 | 32 |
| **total** | **4298 of 110998 (3.872%)** | **2485** | **4114 of 101049 (4.071%)** | **2457** | **1631 of 24458 (6.669%)** | **693** |

**Re-measured 2026-09-03, after two changes landed on layer 3 within a day.**
The first reading of this table gave 3.883% / 4.083% / 6.693% with 3609 / 3559
/ 1059 residue facts. Then P14b landed the indoor law of item 37e — ONE row
keyed on the height relation — and P15 landed `facade` and `opening` (item
32c). Between them, **layer 3's residue falls from 2926 to 334 across the
three maps**, and the claimed share falls slightly, because the indoor row
claims a `cstat` rather than a frame and so describes a record without
claiming a field. That trade is worth stating plainly: 2592 residue facts
gone for 30 claims, on the item this report called the cheapest large win.

E3M1 re-ran unchanged at 3.883% under every reader I touched. One thing did
move in its layer 4, and it moved the right way: **`overlay.kerb_records` used
to claim 81 kerb records where E3M1 makes 11.** P14b fixed it (7541ca7, from
queue item 29b); the re-run claims 11 and the map makes 11, the disagreement
is gone from `references/overlays.json`, and the owner question about it is no
longer asked because the code now answers it.

## The residue of three maps is one residue

The residue reasons that hold on two or more maps, largest first:

| facts | maps | reason |
| --- | --- | --- |
| 2178 | 3 | surface: no same-material neighbour at all |
| 1636 | 3 | surface: broken off a same-material neighbour |
| 773 | 3 | mechanism: an XSPRITE with no wiring this reader reads |
| 242 | 3 | space: no perceptual-space evidence groups this sector |
| 178 | 3 | intent: not a sector type |
| 67 | 3 | intent: no measurement distinguishes it |
| 61 | 3 | mechanism: wired, and no sentence realises it |
| 47 | 3 | join: no row for `interior\|solid\|b_above` |
| 47 | 3 | join: no row for `solid\|interior\|b_below` |

The three `interior|interior` rows that led this table on the first reading —
1266, 662 and 662 facts — are **gone**, and nothing replaced them at the top.
That is what a row does when it is the right row.

Three maps from three episodes — a whole city street, a whole town, an
80-sector fragment — leave residue in the same proportions for the same
reasons. **The residue is not the maps'. It is the model's.**

## The three kinds of gap

A macro proposal turns on the residue's cause, not its size, and there are
three causes:

* a **construct** gap — the map authors something our language cannot say. A
  macro fixes it.
* a **row** gap — the join grammar has no row for a pair the campaign makes.
  A row fixes it; a macro does not.
* a **reader** gap — our reader cannot attest what the map did. Neither fixes
  it; a better measurement does.

Sorting the residue that way is the point of the exercise, because the two
largest buckets are not macro work at all:

| bucket | facts | cause | owner |
| --- | --- | --- | --- |
| a surface's own projection (2178 + 1636) | 3814 | reader | the Surface/Frame representation item — layer 2 cannot attest a frame on a wall with no same-material neighbour, or on one whose neighbour breaks the projection. **This is now 68% of all the residue on all three maps, and the only macro that reaches into it is `stair`, for 321 of the 3814.** |
| ~~`interior\|interior` rows~~ | ~~2590~~ → 0 | row | **Done.** Item 37e landed as ONE row keyed on the height relation rather than the eleven this report proposed, and it took the whole bucket. |
| spaces nothing groups | 242 | reader | `decompiler.decompile_level` — a sector in the tree only so the partition closes. A constructor cannot supply evidence. |

## The macros

The rule is that a macro lowering residue on fewer than two maps is not
proposed. **All five clear it**, four of them on all three maps — which is
itself the finding: with three maps this different, nothing I could measure
turned out to be one map's peculiarity.

| macro | lowers | E3M1 | E1M2 | E4M8 | maps |
| --- | --- | --- | --- | --- | --- |
| `dressing(anchor, [prop…], *, spread=, facing=)` | **773** | 330 | 371 | 72 | 3 |
| `stair(from_, to, *, treads=, width=, clear_height=)` | **321** | 219 | 102 | 0 | 2 |
| `channel(number, tx=[…], rx=[…], *, on=, wave=)` | **121** | 41 | 72 | 8 | 3 |
| `self_lit(space, amplitude=, phase=, wave=)` | **44** | 26 | 17 | 1 | 3 |
| `breakable(surface, *, on=, reveals=)` | **24** | 18 | 6 | 0 | 2 |

**`dressing`** — a bundle of unwired sprites placed against an anchor: a table
with its bottles, a shelf with its books. This is the largest construct gap on
every map, and the reader for it already exists: `read_intent.named_props`
names them and `anchors.find_bundles` groups them; nothing authors them. Our
language can place a sprite only by absolute coordinate, so every one of the
773 is residue.

**`stair`** — a stepped run as one construct owning every tread *and the
projection across them*. Measured by walls: the 12 stepped runs in E3M1 and 5
in E1M2 hold 219 and 102 of layer 2's surface residue between them, because a
tread is its own sector and its side walls have no same-material neighbour to
continue onto. E4M8 has no stepped run, so this is the one macro on two maps
rather than three. Note that it lowers residue in **layer 2**, not layer 1 —
the construct is a surface owner, not a space.

**`channel`** — one channel with all its transmitters and all its receivers.
The campaign fans a channel out as wide as it likes; our writer wires one
pair, which is exactly what leaves 121 records transmitting or listening on a
channel no sentence reaches.

**`self_lit`** — a sector carrying a light wave and no motion, no key and no
channel. The reader reads it perfectly and files it as residue only because it
is not a mechanism. It is a lighting construct with no home in the language.

**`breakable`** — a wall of type 511 (kWallGib) with the channel it fires and
what it opens onto. Layer 8 refuses to name these on both maps that have them,
because **the taught course has no lesson of type 511 at all**: the campaign
uses a mechanism its own curriculum omits.

**The macro total and the bucket total overlap by exactly `stair`'s 321.**
Those facts are surface residue on tread walls and are counted in both rows;
every other macro's residue is disjoint from both buckets. **5635** residue
facts across three maps now: 3814 in the surface bucket, 242 in spaces, 1283
the five macros would lower, 321 in both, and 617 elsewhere.

**Not one of the five macro numbers moved when the row landed**, which is the
classification earning its keep: a row gap and a construct gap are different
things, and clearing 2592 of the first left all 1283 of the second exactly
where it was.

## What I did not propose

`kerbed_island` and `water_body` were measured and not proposed, for opposite
reasons. The island residue on all three maps is `not the measured island
rise` — a reader refusing a step, not a construct missing; and E1M2's water
leaves 56 residue facts that are all join rows, which is row work.

## The suite

```text
Ran 2034 tests in 213.753s
FAILED (failures=5, errors=4, skipped=267, expected failures=4)
```

The nine are P16's worktree-environment failures (relative `maps/`,
`reference/`, `NBlood/` paths); none is from this work. The four new tests in
`tests/test_read_overlays.py` pin the no-sun shape — that `read_light` returns
its `sign` and `casters` keys on a map with no oblique shade boundary, and
that E3M1 still recovers a bearing of 479, so the shape is not a blanket.

## Owner questions

In `reports/owner-review-queue.md` as items 36a–36e, each with a recommended
default and a node id in a review pack.
