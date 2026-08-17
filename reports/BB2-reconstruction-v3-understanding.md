# Independent understanding: `work/BB2-semantic-reconstruction-v3.MAP`

Frozen from `reports/BB2-reconstruction-v3-understanding.json` before comparison
with the BB2 target prose.

## What this map is

A Blood v7 deathmatch compound on an 88 × 62 player-width board. Eight DM
starts, flag bases, gated super armor / cloak / akimbo, underwater Tesla, an
outdoor Z-lift, and a 20 vs 6 player-height sky/cover contrast.

It **is one walkable circuit** at rest for every deathmatch start. Static
progression from the single-player start reaches 11 sectors; 6 are unreachable
because they are rest-closed Z-doors and their prize pockets. Fourteen
at-rest portals exist. Water is a paired 9/10 link, not a portal.

## Exact contents

17 sectors, 126 walls, 36 sprites. 5 parallax ceilings, 12 covered. Native
validation 0 errors. Pickups: 5 weapons, 8 ammo, 3 health, 2 armor, 2
powerups, 2 flags. One underwater XSECTOR.

## Scale

- Sky footprint **2640** player-areas, height 20 PH, 5 sectors
- Covered footprint **800** player-areas, median height 6 PH, 12 sectors
- Covered *sectors* outnumber sky; sky still has the larger footprint
- Outdoor floor is one plane except the lift’s on-Z (6 PH up)

## Morphology

| metric | value |
| --- | --- |
| orthogonal length | 0.79 |
| diagonal length | 0.05 |
| orientation diversity | 0.22 (8 of 36 bins) |
| rectangular sector fraction | 0.35 |
| convex fraction | 1.00 |
| outer vertices | median 6, max 14 |
| chamfer fraction | 0.13 |
| segmented-arc chains | 0 |

Mostly orthogonal with chamfered courtyard, irregular yards, and rectangular
interiors. Not a pure grid. Orientation language is still sparse versus a map
that occupies almost every 5° bin.

## Spawn neighborhoods

| start | sky | sector area | portals | hops to main sky | max sight |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | yes | 628 | 2 | 0 | 60 |
| 2 | yes | 540 | 1 | 0 | 65 |
| 3 | no | 320 | 1 | 1 | 69 |
| 4 | yes | **1360** | 6 | 0 | 52 |
| 5 | yes | **1360** | 6 | 0 | 40 |
| 6 | no | 160 | 1 | 2 | 15 |
| 7 | no | 40 | 1 | 2 | 46 |
| 8 | yes | 628 | 2 | 0 | 66 |

Two outdoor starts sit in a **large hunting-ground cell** (1360 areas, 6
exits, already in the sky component). Indoor starts are small rooms with a
mouth into the field, not sealed closets. Pairwise 2D spawn sight is **10/28**
clear — more peeking than a 1/28 map.

## Routes

All eight starts have a shortest path to the largest sky sector. Outdoor
routes are all-sky; indoor routes take 1–2 hops with a cover→sky transition.
Route exposure here reports hunting-ground vs porch, not disconnection.

## Resources and mechanisms

Flags sit opposite: A under sky in the south yard, B in the north interior.
Super armor, cloak, and akimbo sit behind rest-closed Z-doors with push
switches. Tesla is underwater on paired water markers. A type-602 outdoor
lift sits on the south yard. Ammo is on the open circuit.

## Materials

Outdoor: earth 270, stone 110, sky 2500. Indoor: floor 2448, brick 5, ceiling
416. Water uses tile 90. Lighting still flat.

## Interpretation

v3 is a Blood DM compound **program** with **irregular outdoor masses**, at
least one true hunting-ground spawn, **and a coherent at-rest circulation
graph**. Buildings are punched into the field as shells with thickness, not
as overlays. Gated prizes remain gated. Isolation is no longer the source of
concealment.

Limitations: 2D sight; closed doors blocked in the static model; no NBlood
step in this packet.
