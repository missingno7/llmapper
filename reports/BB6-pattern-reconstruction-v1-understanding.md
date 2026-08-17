# Independent understanding: `work/BB6-pattern-reconstruction-v1.MAP`

Frozen from `reports/BB6-pattern-reconstruction-v1-understanding.json`
**before** comparing to `reports/BB6-understanding.md`.

## What this map is

A small Blood v7 deathmatch compound: 13 sectors, 92 walls, 20 sprites. Two
chamfered outdoor yards, a lower central depression, two covered masses with
gated flag rooms, and eight DM starts. 5 parallax ceilings. Native
validation 0 errors. Conservation conserved. 8/8 DM starts on the main
at-rest circuit. Four sectors unreachable at rest (gated doors and flag
pockets).

## Scale and enclosure

Sky footprint 2272 player-areas vs covered 304. Sky-area fraction 0.88;
sky-sector fraction 0.38. Outdoor height 20 PH; covered 6 PH. Depression
floor is 1.5 player-heights below the yards.

## Spawn neighborhoods

All eight starts are sky, hops 0, field fraction 1.0.

- Four *open hunting-cell* starts in the two yards (area 848, 3 exits).
- Two *sky porch into field* starts (area 32, one exit, local 880).
- Two depression starts (area 512, 2 exits) — outdoor, lower Z, not a
  hunting-cell (too few exits for that signature).

Pairwise 2D sight is **11/28 clear**. The two masses occlude some spawn
pairs. Roses are bounded.

## Routes

All eight start-to-largest-sky paths are all-sky.

## Morphology

Orthogonal length 0.90, diagonal 0, orientation diversity 0.11 (4 bins),
rectangular fraction 0.54, convex 1.0. Two sky hosts with holes. Indoor
loops are boxes. No irregular 9+ footprints, chamfers-as-chains, or
segmented curves matched.

## Contents

2 flags behind rest-closed Z-doors with push switches. 4 weapons and 2
armor in the interiors. 1 health in the depression. 1 cloak in a gated
north pocket. No underwater. No unknown special weapons.
