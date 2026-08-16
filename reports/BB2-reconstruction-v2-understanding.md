# Independent understanding: `work/BB2-semantic-reconstruction-v2.MAP`

Same sensors as the v1 candidate reading. This file was written from the v2
MAP and the understanding packet only.

---

## What this map is

A Blood v7 deathmatch compound on an 80 × 80 player-width square. Eight DM
starts, flag bases, gated super armor / cloak / akimbo, underwater Tesla, and
a 20 vs 6 player-height sky/cover contrast.

It is **not one walkable circuit**. Static progression from the single-player
start reaches **1 sector**; 26 are unreachable at rest. Thirteen at-rest
portals exist. Several authored outdoor masses never received a coincident
portal, so they are large sky rooms with **zero exits**.

---

## Exact contents

27 sectors, 151 walls, 72 sprites. 10 parallax ceilings, 17 covered. Validation
0 errors. 6 XSECTORs (three Z-doors, one outdoor Z-lift, two underwater). 1
gib wall. Pickup mix: 2 flags, 8 weapons, 26 ammo, 5 health, 5 armor, 2
powerups.

---

## Scale

- Sky footprint **4731** player-areas, height 20 PH, 10 sectors
- Covered footprint **2570** player-areas, median height 6 PH, 17 sectors
- Covered *sectors* outnumber sky; sky still has the larger footprint
- Indoor-start → outdoor-start height ratio 3.33; sky exposure 0 → 1
- Outdoor floor is still a single plane except the lift’s on-Z (6 PH down)
- Openings are coarser than campaign medians (wall lengths median ~9 widths)

---

## Morphology

| metric | value |
| --- | --- |
| orthogonal length | 0.83 |
| diagonal length | 0.03 |
| orientation diversity | 0.22 (8 of 36 bins) |
| rectangular sector fraction | 0.30 |
| convex fraction | 1.00 |
| outer vertices | median 5, max 9 |
| chamfer fraction | 0.13 |
| segmented-arc chains | 1 |
| AABB fill mean | 0.94 |

The architecture is **mostly orthogonal but not a pure grid**. Octagons,
trapezoids, and chamfered loops exist. Orientation language is still sparse
compared with a map that occupies almost every 5° bin.

---

## Spawn neighborhoods

| start | sky | sector area | local 16w | portals | hops to main sky | max sight | sky-ray |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 62 | yes | **720** | 974 | 3 | 0 | 62 | 1.00 |
| 63 | yes | 552 | 552 | **0** | none | 13 | 0.13 |
| 64 | yes | 160 | 160 | 2 | 0 | 29 | 1.00 |
| 65 | yes | 370 | 370 | **0** | none | 10 | 0.00 |
| 66 | yes | 549 | 549 | **0** | none | 14 | 0.00 |
| 67 | no | 64 | 424 | 1 | none | 41 | 0.13 |
| 68 | no | 190 | 910 | 1 | 1 | 50 | 0.41 |
| 69 | no | 288 | 288 | 1 | none | 10 | 1.00 |

One outdoor start occupies a **large hunting-ground cell** (720 areas, long
max sight, already in the main sky component). Several other outdoor starts
sit in **large but sealed** sky polygons. Pairwise 2D spawn sight is **2/28**
clear. Median sight at sealed starts is short; the connected south start has
median ~18 widths.

---

## Routes

Only three of eight starts have a shortest path to the largest sky sector.
Those routes are mostly sky (fraction 0.8–1.0) with 0–1 cover transitions.
The other five are not on the at-rest graph. Route exposure here mostly
reports **disconnection**, not hunting-ground vs corridor.

---

## Resources and mechanisms

Flags sit opposite: A under sky, B under a covered porch. Super armor, cloak,
and akimbo are behind rest-closed Z-doors. Tesla is underwater on paired water
markers. An extra Z-motion **floor lift** exists beside a south mouth. Ammo is
present on many sectors (26 piles) but some of those sectors are unreachable.

---

## Materials

Outdoor: earth 270, stone 110, sky 2500. Indoor: floor 2448, brick 5, ceiling
416. Water uses tile 90. Same kit as v1; lighting still flat.

---

## Interpretation

v2 is a Blood DM compound **program** (flags, gates, Tesla, height contrast)
with **irregular masses** and at least one true hunting-ground spawn, sitting
on a **broken circulation graph**. The design meaning of “loop the compound
and duck into buildings” is not currently playable for most starts.

Limitations: 2D sight; closed doors blocked; no NBlood step; several intended
portals never matched because irregular edges were not coincident.
