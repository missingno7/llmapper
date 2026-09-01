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
| masked middle | `over_picnum` | `(cstat&48) == 16`; deferred, then drawn between the lower ceiling and the higher floor: `z1 = max(nsec->ceilingz, sec->ceilingz); z2 = min(nsec->floorz, sec->floorz)` | 4685, 7214-7215, 7231 |
| one-way middle | `over_picnum` | `cstat&32`, through the white-wall branch, opaque, after the steps | 4938-4940 |

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
turns it into a one-way wall and draws the reflection through it; `:442-455`
a wall whose over_picnum is 504 with a stack type is a room-over-room link.

**Slopes.** Endpoint heights come from `getzsofslopeptr`
(`engine.cpp:14333-14352`): `z += scale(heinum, j, i)` with `j` the
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
sky, mirror and tile 0):

```text
walls                                          113261
  one-sided                                     52415   every one draws its picnum
  two-sided                                     60838
red walls whose picnum draws nowhere on the pair, by VALUE
  (its own bands, or the partner drawing the same tile)     28539   47% of red walls, 25% of all
    partner wears a different tile                          16100
      ... and the pair draws SOMETHING (a step in the other tile)   12560
      ... and the pair draws nothing at all (flush, unmasked)        3540
    partner wears the same tile                             11578
    no partner (nextwall -1 on a red wall)                    861
red walls carrying an over_picnum the engine never reads      2626
```

So an authored picnum on an invisible band is the editor's habit, not a
defect: Build copies the previous wall's picnum when a point is inserted and
nobody clears it. Tile 110 leads with 1657 undrawn walls, 5 has 1406, 80 has
1080, 449 has 1016.

Three formulations of "a tile authored on a wall is drawn somewhere", rated:

```text
per wall            28539 / 113253   25.2%   note      (registered: wall-draws-its-own-tile)
per sector x tile    4317 /  27104   15.9%   note      (not registered)
per map x tile         97 /   1979    4.9%   warning   (registered: wall-tile-is-drawn-somewhere -- THE GATE)
```

The per-map form is the statement taken literally -- the tile is on screen
*somewhere* -- and it separates a leftover (drawn elsewhere in the same map)
from a lost material (drawn nowhere). E1M1 has 0 lost tiles; E3M4 has 1
(tile 80, weathered stone, on invisible walls only).

## 3. Fail first: the city, then the zoo

`projects/blood-city/level/blood-city-current.MAP` as committed at 8c42701:

```text
wall-tile-is-drawn-somewhere    6 of 32 authored wall tiles lost
  tile 146   walls 276, 277, 278        the stage curtain's fabric  <- the defect the reader was written for
  tile 68    walls 124, 127, 134, 170, 172
  tile 93    9 walls (503, 506, 510, 511, 521, 535 ...)
  tile 194   walls 1266, 1318
  tile 203   walls 240, 245, 259
  tile 1011  walls 512, 514, 515
wall-draws-its-own-tile         341 of 1696 walls (20%), 276-278 among them
tile-sits-in-an-attested-slot   12 new warnings under the rendered vocabulary:
  tile 202 on two_sided_lower x12 (walls 300-307, 1106-1109); the campaign
  shows 202 on one_sided_middle only
```

Sector 37 itself: walls 276-278 wear 146, two-sided into sector 23, cstat 0
(277 carries the 0x4000 move flag), sector 37 ceiling -16384 against sector
23's -40960 with flush floors at 8192. From the curtain's side neither step
exists; the auditorium's partner walls 204-211 draw THEIR picnum 119 on a
27908-unit upper step. The fabric is on screen nowhere in the level.

`projects/pattern-zoo/level/pattern-zoo.MAP`: 0 of 22 tiles lost; 101 of
510 walls carry an undrawn picnum (the habit, at the campaign's rate); 0
rendered-slot warnings. The zoo's self-read gate now runs
`wall-tile-is-drawn-somewhere` as a LAW rule and passes.

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

So of the 129 two-sided uses, 74 are step bands and 55 draw nothing; none is
a masked middle. Two corrections to the brief's reading of the fixtures:

* **E1M1 s125's pelmet is tile 109, not 146.** Walls 1203-1207 (s125,
  ceiling -10240) face s122 whose ceiling is -75776: from the curtain's side
  nothing steps, so their 146 is invisible -- the same storage the city
  reproduced. The 65536-unit pelmet is drawn by the partners 1102-1106 with
  their own picnum 109 (s122's wall stone); their over_picnum 146 sits
  behind cstat 0x6 (swap + align, no mask) and is never read. The visible
  fabric in E1M1 is the one-sided leaves 1200/1201/1209/1210.
* **DOOR-CURTAINSD s4's pocket dialect shows tile 1060, not 146.** The
  pocket-side walls 28/32/37/41 (cstat 0x51) draw `masked_middle 1060` at
  full opening height (24576); their picnum 146, and the 146 on the flush
  pocket walls 26/27/33/34, is never on screen. The curriculum, not the
  campaign, so it is precedent for the reader, not a campaign count.

## 5. The mask law, restated by band

With the ART read (`reference/blood`): 78 of 3590 mask-carrying tiles appear
on some wall band; on the OPAQUE bands (one_sided_middle, two_sided_upper,
two_sided_lower) exactly two -- 142 (4 upper, 8 lower) and 2464 (5 upper) --
the same two the owner has already ruled on. Every other mask tile on a wall
is in a masked middle (58, 104, 330, 331, 463, 465, 466, 502, 1066) or a
one-way middle. The band formulation is the one the engine implements; v1's
"two-sided" clause conflated the step (opaque) with the mask (see-through).

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

## 7. Limits

* Flat and sloped heights are read; sector effects that move heights at run
  time (lifts, Z-motion doors) are read in the SAVED pose only. A door saved
  closed whose fabric draws only when open is reported as it is saved.
* The reader does not model occlusion, room-over-room, or the
  `yax` paths; a band that draws is a band the engine would rasterise if
  nothing stood in front of it.
* The per-wall habit rule produces 341 notes on the city; it is registered
  for diagnosis, and its severity says it is not a law.
