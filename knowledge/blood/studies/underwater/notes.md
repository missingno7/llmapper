# Study: underwater

Written 2026-11-25. Frames by the observer (`python -m tools.look --ref`), numbers read from
the 43 campaign maps' records (191 water pairs, 618 sectors with `underwater`
in 24 maps), behaviour from NBlood (`warp.cpp`, `actor.cpp`, `player.cpp`).

## What I want to build

Three drowned places in Gravesend, one idea each: the pumps' sump under the
settling basin, a flooded sewer branch reached only by diving, and the water
under the Demeter's keel. Each with a way back up that strands nobody.

## Where Blood built it

- **E3M3:176 / 174** (tile 1120). A round tank of rusted plate (510): surface
  2.4 bodies under its rim, 3.9 bodies of water, and half way down its wall two
  octagonal pipes (255, sloped floor and ceiling strips) lead off. From the
  tank's floor nothing else is seen. The best sump in the game.
- **E3M3:63 / 34 and 51-59**. A flooded corridor, 1.93 bodies of water under
  492 walls, and then NINE pairs in a row (63, 65-73), each 1,024 long and
  0.24 of a body shallower than the last: the stair goes on down under the
  water and every step of it is its own pair. That is how E3M3 lets a wader
  become a swimmer.
- **E6M4:287 / 281** (2915). A boat seen from below: the hull is a ring of
  sectors whose ceilings (67) slope down from the waterline to a flat bottom,
  dark over a grey bed (358), `visibility` 16 so that everything 8,000 away is
  black. The brightest thing is the surface. 3.3 bodies.
- **E1M4:248 / 254**. The carnival lake: 3.4 bodies over an earth bed (270),
  rock walls (449), the pier's posts (28) standing on it, weed, eleven eels.
- **E2M1** (2448 in palette 10), **E2M9** (2490): the sea and the cave lakes,
  the pal-10 pairs (11 of 191): the palette is on both surfaces.

## What makes it read as that

- **The underside of the surface** is the same tile on the ceiling, and it is
  the light: floor shade 22 (9 to 29), ceiling 26 (14 to 30), walls 28. Nothing
  is lit under water but what shines itself; nobody hangs a lamp there.
- **Weed and bubbles and nothing else**: 660 and 664 ("underwater grass"), both
  face sprites at 64 x 64, in clumps, and in three maps the weed IS the bubble
  generator (E1M4 sprite 339: type 706, tile 660, `busy_time` 50, `data_1` 10).
  E3M3 stands 22 columns of 668 (an animated thread of bubbles, shade 0 to 8),
  one by every pipe mouth. Both tiles are only ever under water (the rule
  `aquatic-sprite-is-under-water`).
- **Holes in the wall at half height**: an octagonal pipe end, black inside.
- The screen goes blue by itself (`view.cpp:4032`: palette 1 in water), the
  splash in and out is sound 720 / 721. The observer draws neither.
- **Sound**: the swimmer's own breath, sound 37 ("Scuba Diving"), 75-300 at 80
  on E1M8; 40 (water at a wall), 75-150 at 50, is on 53 surfaces and in
  29 drowned sectors.
- From above nothing marks water that can be dived into: the same tile lies on
  ankle-deep floors. What tells is a rim, and the missing `depth` (180 of 191
  surfaces have none).

## Sizes

| | campaign (191 pairs) | ours |
| --- | --- | --- |
| water, floor to surface | 0.24 to 5.8 bodies; quartiles 1.7, 2.9, 4.1 | sump 4.5, well 2.4, tank 2.3, hall 2.5, slip 3.4 |
| rim over the surface, lowest | 2,048 (40), 4,096 (24), 3,072 (11), 1,024 (5); many have a neighbour at 0 | 2,048, kerbs 3,072, a ramp 1,024 |
| a drowned passage, height | 0.24 to 1.9 bodies; 0.85 common (E6M4) | 1.2 to 1.4 |
| the two planes' z | not the same in 141 | junction, cistern, branch, slip the same; the sump 34,816 lower |
| overlap in plan | 7% | none: `OFFSET` -60 plan units for all |
| farthest point from a surface | 4 to 24 plan units, E2M1 40 | 4.5 |

- **Air**: `underwaterTime` is 1,200 tics of 120, ten seconds; then `chokeEffect`
  grows 4 a frame and a chance of `chokeEffect`/65,536 a frame costs 3 health:
  five seconds over costs two health in the mean. Nobody drowns suddenly.
- **Speed**: front acceleration 0x1200 times 1,024 (walk) or 2,048 (run) over
  256, against a drag of 5,376/65,536: 1.6 plan units a second walking, 3.2
  running; up and down 0x5b05 a frame: two bodies a second.
- **Climbing out**: whoever crosses the surface with jump held is thrown at
  `-0x6aaaa` (`actor.cpp:4680`). With gravity 58,254 and the buoyancy of the
  half that is still wet he peaks 6,904 over the surface, and a wall is passed
  when his centre is its height plus a quarter of him (2,120) over the water:
  2,048 has ten frames to do it in, 4,096 five, and 4,784 is the most. 6,144 is
  a trap.
- **What a link does not do**: `CheckLink` runs after the sector-enter trigger,
  so surfacing INTO a sector does not enter it. A secret counted by entering
  has to be a sector that is walked into from the one that is surfaced in.
- A bone eel (218) that surfaces dies; a gill beast (217) walks on. An axe
  zombie swims. Eels come in shoals of 3 to 22 (`launch_skill` on half), beasts
  one to five; both face by their angle.

## What I will transcribe

- `roomoverroom.water_link`: markers 9 and 10 (tiles 2332 and 2331, cstat 128,
  status 0) at one offset, one tile on both surfaces, `underwater` on the lower
  sector, and the outline moved exactly: whoever dives keeps his place in plan.
- E3M3's tank of 510 and its octagonal pipe (three strips: a flat middle, two
  with floor and ceiling sloped); its shimmer (`shade_wave` 7, amplitude -4,
  frequency 4) on both sides of a pair; 1120, 492, 568, 255.
- E6M4's hull: 67, flat bottom, sloped bilges; its bed 358, `visibility` 16.
- E1M4's bubbling weed.

## What I will not do, and why

- No lamps under water. Each place has at most one light and a reason for it: the
  pumps' wheel, a lantern in a sunk boat.
- No underwater doors or switches: nothing to read while the air runs out.
- The pal-9 and pal-5 lower ceilings (three pairs) are somebody's mistake.
- No drowned stair of nine pairs (E3M3:65-73): 100 walls for a wade.

## What I still do not know

- How the blue of the game's palette treats the wheel's orange: the observer
  has no underwater palette.
- Whether a player finds a tank in a dark cistern without being told. The
  campaign does not tell him either.
