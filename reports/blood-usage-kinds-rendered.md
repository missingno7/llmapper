# The rendering law: what the engine draws on a wall, and the usage table re-mined by it

Date 2026-09-01. Machine-readable twin: `blood-usage-kinds-rendered.json`;
knowledge: `knowledge/blood/design/usage-kinds-v2.json` beside the v1 table.
Reader: `bloodmap/render_slots.py`. Gate: `wall-tile-is-drawn-somewhere` in
`bloodmap/rules_blood.py`. Population: the 43 campaign maps through the corpus
registry; the city and zoo builds are scored, never mined.

## 1. The law, read from the classic renderer

`NBlood/source/build/src/engine.cpp`, `classicDrawBunches` and
`renderDrawMaskedWall`. Every line was read before it was cited; none of this
sits under NOONE_EXTENSIONS or gModernMap. For a wall seen from its own
sector:

| band | tile drawn | condition | lines |
| --- | --- | --- | --- |
| one-sided middle | `picnum` | `nextsector < 0`; ceiling to floor | 4938-4940 `setup_globals_wall1(wal, (nextsectnum < 0) ? wal->picnum : wal->overpicnum)` |
| two-sided upper step | `picnum` | neighbour's ceiling LOWER at either end; skipped when `(cz[2] <= cz[0]) && (cz[3] <= cz[1])`; skipped when both ceilings parallaxed | 4688, 4690, 4720 |
| two-sided lower step | `picnum`, or the PARTNER's picnum under `cstat&2` | neighbour's floor HIGHER at either end; skipped when `(fz[2] >= fz[0]) && (fz[3] >= fz[1])`; skipped when both floors parallaxed | 4799, 4801, 4832-4833 `twal = (wal->cstat&2) ? &wall[wal->nextwall] : wal` |
| masked middle | `over_picnum` | `(cstat&48) == 16` -- masked AND NOT one-way; deferred, then drawn between the lower ceiling and the higher floor: `z1 = max(nsec->ceilingz, sec->ceilingz); z2 = min(nsec->floorz, sec->floorz)` | 4685-4686, 7217-7218, 7231 |
| one-way middle | `over_picnum` | `cstat&32`, through the white-wall branch, opaque; `wallscan` runs `uplc`..`dplc` (this sector's own ceiling and floor) but the two steps have already pushed `umost`/`dmost` in (:4728-4740 and :4847-4853), so what survives is the middle | 4938-4940 |

**Blocking (cstat&1) and hitscan (cstat&64) draw nothing.** Neither bit is
read in the wall pass; they are clip masks -- `clip.cpp:1491 dawalclipmask =
(cliptype & 65535)` with `build.h:225 CLIPMASK0 = (1<<16)+1` (movement) and
`build.h:226 CLIPMASK1 = (256<<16)+64` (hitscan). A blocked, hitscan,
unmasked red wall is an invisible fence.

**The sky bypass.** When both sectors' ceilings carry the parallax bit the
upper step is not evaluated at all (4688) and `parascan` (4187) paints the
sky over those columns; the parascan wall loop at 4294 skips a column whose
neighbour is itself parallaxed, leaving it to the neighbour's own bunch. The
sky family is `{2500, 3491, 3678}` (derived, `usage-kinds` `sky_family`).

**The mirror bypass.** `NBlood/source/blood/src/mirrors.cpp:37
kMirrorTile 504`; `:466-469` a wall whose picnum is 504 gets `cstat |=
CSTAT_WALL_1WAY` and `overpicnum = kMirrorTile` at level start, so the game
turns it into a one-way wall and draws the reflection through it; `:442-451`
a wall whose over_picnum is 504 on a `kWallStack` XWALL gets the same bit and
is a room-over-room link. `render_slots.mirror_pass` applies the first
transform, because it changes the band: the campaign stores 504 on 8 walls,
7 white and 1 red, and that red one draws a `oneway_middle` that a reading of
the file's cstat alone would miss. The stack case needs the XWALL type and is
left to `bloodmap.layers`.

**Slopes.** Endpoint heights come from `getzsofslopeptr`
(`engine.cpp:14333-14354`): `z += scale(heinum, j, i)` with `j` the
perpendicular distance from the sector's first wall and `i` that wall's
length, only when stat bit 2 is set. Blood runs
`enginecompatibilitymode = ENGINE_19960925` (`blood.cpp:1890`) so the EDUKE32
shift is 0. The reader uses an exact integer square root where the engine's
`nsqrtasm` is a table, so a sloped endpoint can differ by one z unit; the
step decisions (`<=`, `>=` at both ends) are what the reader needs and the
unit does not move them in any campaign case checked.

Polymost (`polymost.cpp:6528`) branches on the same
`(nextsectnum < 0) || (wal->cstat&32)`; it was not transcribed line by line.

## 2. What the campaign does with the invisible band

Census over 113261 campaign walls (`render_slots.undrawn_walls`, exempting
sky, mirror and tile 0). Re-measured 2026-09-01 with the ART present:

```text
walls                                          113261
  one-sided                                     52422
    ... drawing their picnum                    51560
    ... drawing nothing (zero-height sector)      862
  two-sided                                     60839
walls whose picnum draws nowhere on the pair, by VALUE
  (its own bands, or the partner drawing the same tile)     28539   of 107785 non-exempt, 26.5%
    two-sided                                               27678
      partner wears a different tile                        16100
        ... and the pair draws SOMETHING (a step in the other tile)  12560
        ... and the pair draws nothing at all (flush, unmasked)       3540
      partner wears the same tile                           11578
    one-sided in a zero-height sector                         861
two-sided walls carrying an over_picnum the engine never reads  2626
```

So an authored picnum on an invisible band is the editor's habit, not a
defect: Build copies the previous wall's picnum when a point is inserted and
nobody clears it. Tile 110 leads with 1657 undrawn walls, 5 has 1406, 80 has
1080, 449 has 1016.

Three formulations of "a tile authored on a wall is drawn somewhere", rated:

```text
per wall            28539 / 107785   26.5%   note      (registered: wall-draws-its-own-tile)
per sector x tile    4515 /  27104   16.7%   note      (not registered)
per map x tile         97 /   1979    4.9%   warning   (registered: wall-tile-is-drawn-somewhere -- THE GATE)
```

The per-map form is the statement taken literally -- the tile is on screen
*somewhere* -- and it separates a leftover (drawn elsewhere in the same map)
from a lost material (drawn nowhere). E1M1 has 0 lost tiles; E3M4 has 1
(tile 80, weathered stone, on invisible walls only).

## 3. Fail first: the city before the curtain rebuild, then after, then the zoo

The fail-first fixture is a REAL map, not a reduction: the city as committed
at **8c42701**, before P1 rebuilt the proscenium. `tests/test_rendering_law.py`
reads it back out of the object store with `git cat-file` so the anchor
outlives the fix.

```text
wall-tile-is-drawn-somewhere    6 of 32 authored wall tiles lost
  tile 146   walls 276, 277, 278        the stage curtain's fabric  <- the defect the reader was written for
  tile 68    walls 124, 127, 134, 170, 172
  tile 93    9 walls (503, 506, 510, 511, 521, 535 ...)
  tile 194   walls 1266, 1318
  tile 203   walls 240, 245, 259
  tile 1011  walls 512, 514, 515
wall-draws-its-own-tile         341 of 1696 walls (20%), 276-278 among them
```

And the SAME map after P1's rebuild (`blood-city-current.MAP` at e0cb075):

```text
wall-tile-is-drawn-somewhere    5 of 32 authored wall tiles lost
  tile 146   GONE -- the fin is one-sided now and draws a one_sided_middle
  tile 68    walls 124, 127, 134, 170, 172
  tile 93    9 walls (501, 504, 508, 509, 519, 533 ...)
  tile 194   walls 1264, 1316
  tile 203   walls 238, 243, 257
  tile 1011  walls 510, 512, 513
wall-draws-its-own-tile         338 of 1694 walls (20%)
```

**The five survivors are one defect, not five.** 68, 93, 203 and 1011 are the
`opening` field of `materials.py`'s parlor, church, theatre and crypt
Materials, and 194 is `sewerkit.MOUTH_TILE`. Every one sits on a flush,
unmasked two-sided threshold -- wall 124 for instance is s14 -> s15 with both
ceilings at -20480 and both floors at 8192, cstat 0, partner also wearing 68.
The city paints a doorway lining on the portal wall of a doorway that has no
step, so the lining is never on screen; the curtain was the same mistake with
a more visible material. Recorded in `reports/owner-review-queue.md`.

Sector 37 itself: walls 276-278 wear 146, two-sided into sector 23, cstat 0
(277 carries the 0x4000 move flag), sector 37 ceiling -16384 against sector
23's -40960 with flush floors at 8192. From the curtain's side neither step
exists; the auditorium's partner walls 204-211 draw THEIR picnum 119 on a
27908-unit upper step. The fabric is on screen nowhere in the level.

`projects/pattern-zoo/level/pattern-zoo.MAP`: 0 of 22 tiles lost; 103 of
528 walls carry an undrawn picnum (the habit, at the campaign's rate). The
zoo's self-read gate now runs `wall-tile-is-drawn-somewhere` as a LAW rule
and passes with zero.

## 4. Tile 146, the test case

v1 stored it as `wall_one_sided 173, wall_two_sided 129, floor 4,
sprite_wall 5`. Rendered:

```text
one_sided_middle   173     the leaves and fins (DOOR-CURTAINS s3 idiom)
two_sided_lower     71     drawn on a FLOOR step -- fabric hanging over a raised stage edge
two_sided_upper      3     drawn on a ceiling step
wall_undrawn        55     walls wearing 146 that show it nowhere: E1M1 1203-1207 among them
masked_middle        0     the campaign never masks 146
over_unread         10     over_picnum 146 on walls that never read it (E1M1 1102-1106, cstat 0x6)
```

173 + 71 + 3 + 55 = 302 = v1's `wall_one_sided 173 + wall_two_sided 129`, so
the redistribution is exact and nothing is double counted.

So of the 129 two-sided uses, 74 are step bands and 55 draw nothing; none is
a masked middle. Two corrections to the brief's reading of the fixtures:

* **E1M1 s125's pelmet is tile 109, not 146.** Walls 1203-1207 (s125,
  ceiling -10240) face s122 whose ceiling is -75776: from the curtain's side
  nothing steps, so their 146 is invisible -- the same storage the city
  reproduced. The 65536-unit pelmet is drawn by the partners 1102-1106 with
  their own picnum 109 (s122's wall stone); their over_picnum 146 sits
  behind cstat 0x6 (swap + align, no mask) and is never read. The visible
  fabric in E1M1 is the one-sided leaves 1200/1201/1209/1210.
* **DOOR-CURTAINSD s4's pocket dialect shows tile 1060, not 146.** Verified
  wall by wall: 28 and 32 (s4 side) and 37 and 41 (the pockets' side) carry
  cstat 0x51 and draw `masked_middle 1060` at the full opening height
  24576; their picnum 146, and the 146 on the flush pocket walls
  26/27/33/34/36/39/42/43, is never on screen. So the pocket dialect's
  visible cloth is 1060 and its 146 is storage. The curriculum, not the
  campaign, so it is precedent for the reader, not a campaign count.

## 5. The mask law, restated by band

With the ART read (`reference/blood`, 3585 tiles carrying more than 5%
mask): only **11** of them are drawn on any wall band in the campaign at
all, and on the OPAQUE bands (one_sided_middle, two_sided_upper,
two_sided_lower) exactly two -- 142 (4 upper, 8 lower) and 2464 (5 upper) --
the same two the owner has already ruled on. The other nine (58, 104, 330,
331, 463, 465, 466, 502, 1066) are in masked or one-way middles, which is
where a see-through tile belongs. 79982 opaque band draws, 12 of them a
mask tile: 0.015%. The band formulation is the one the engine implements;
v1's "two-sided" clause conflated the step (opaque) with the mask
(see-through).

## 6. What the rendered vocabulary changes downstream

* `usage_kinds.unattested_uses` judges walls by the bands they draw when the
  v2 table is present (`rendered_wall_uses`); surfaces and sprites are
  unchanged. Its campaign grade stays 0 by construction. On the city it
  finds the 12 tile-202 lower steps that the storage vocabulary could not.
* 14 tiles the campaign stores on walls are drawn on NO band anywhere in the
  campaign: 45, 151, 283, 307, 308, 310, 443, 445, 1006, 2468, 2532, 2534,
  2536, 2537. Under v1 they were "attested on walls"; under v2 they have no
  rendered wall slot, so an authored map using them on a visible wall now
  gets the attested-slot warning it should always have had.
* The storage vocabulary never looked at `over_picnum` on a wall at all --
  it checked `picnum` and the slot was "one-sided or two-sided". The band
  vocabulary checks the overlay wherever the engine reads it, and the first
  thing that found is in `projects/reasoned-authoring-v1`: candidate-v7
  walls 577, 579, 593, 595 are a masked pair (cstat 0x51) between sectors 76
  and 77 whose `over_picnum` is **110**, the bulk wall stone. The campaign
  draws 110 as a white wall 2513 times, on an upper step 574 and a lower one
  513, and **never once** as a masked middle: its masked panes are doors,
  grates and glass (266 x232, 330, 463, 502). Waived by name in
  `tests/test_rules.py` -- another project's shipped artifact is reported,
  not patched.
* Opacity is NOT what separates a masked middle: 326 of the campaign's 519
  masked-middle draws wear a fully opaque tile (266 alone is 232 of them).
  The finding above is about tile 110 specifically, not about see-through.

## 7. Limits

* Flat and sloped heights are read; sector effects that move heights at run
  time (lifts, Z-motion doors) are read in the SAVED pose only. A door saved
  closed whose fabric draws only when open is reported as it is saved.
* The reader does not model occlusion, room-over-room, or the
  `yax` paths; a band that draws is a band the engine would rasterise if
  nothing stood in front of it.
* The per-wall habit rule produces 338 notes on the current city; it is
  registered for diagnosis, and its severity says it is not a law.
* The load-time mirror transform is modelled for `picnum == 504`
  (`mirrors.cpp:466-469`) but NOT for the stack form at `:442-451`, which
  needs the wall's XWALL type. A room-over-room link wall therefore reads as
  whatever its file cstat says.
* Polymost's own wall pass (`polymost.cpp:6528`) branches on the same
  `(nextsectnum < 0) || (wal->cstat&32)` and was spot-checked, not
  transcribed. If the two renderers disagree anywhere, this reader follows
  classic.
