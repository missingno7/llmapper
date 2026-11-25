# The sewers outside the city: can it be done

The owner, 2026-11-25: "sounds from sewers are leaking into overgournd, but I am affraid
that only way to handle it would be to move the whole sewers layer outside of the city."
Measured on the build of that day. Nothing of this is built.

## What is true now

- **The engine hears through floors.** `Calc3DValues` (NBlood `sfx.cpp`) takes x and y over 16 and z over 256 and
  nothing else; `ambProcess` (`asound.cpp`) the same. A sewer floor is 53,248 z under the street: 208 of those units,
  or 3.25 plan units. A sound straight below is at full volume; one 64 units away is at 5%.
- **62 of the 97 ambient emitters are in the deep layer**, with reaches of 600 to 1,100 of those units. At street level
  at least one of them is heard over 39% of the city's plan.
- **903 of the deep layer's 1,449 square units lie under something**, so the automap draws both, one over the other.
- **Only two portals join it to the rest**, as the owner thought: the crypt's slab (its shaft is 1 by 1, at 30.5..31.5,
  25.25..26.25, and opens on the crypt at the bottom) and the last tread of the pump station's cellar flight (46.5..47,
  4..5). 753 sectors are on the far side of them: sewers, crypt, settling hall, stockyard, den, railway.
- The four manholes are stacks already, and the drowned places are linked 60 units away from their surfaces: a link is a
  translation, so distance is nothing to it.
- The deep layer is 70 by 90 units (0.5..70.5 by -19..70.5). A stack takes two mirror slots of NBlood's 128 (`mirrors.h`);
  four stacks and one mirror wall are used.

## What it would be

1. **The crypt's slab, as E4M4 s159 and s154.** There the car is the LOWER sector, type 600, its ceiling 504 at -24,576; it
   stops at -20,480, which is 4,096 under the plane; above it is one sector of the same plan with a floor of 504. Ours: the
   shaft's top stop goes from 8,192 to 12,288 and it gets a ceiling at 8,192; a 1 by 1 sector in the church's floor is its upper
   half. One steps 4,096 down onto it and 4,096 up off it, and looks down the shaft after it when it has gone. The skull switch
   the slab carries cannot be seen across the plane; the switches at the two stops call it.
2. **The pump station, as E2M1 s2 and s20.** The upper half is one flat sector, 1,024 by 2,560, floor 504, entered over one
   edge. The lower is one sector of the same plan, ceiling 504, whose floor slopes the whole length (heinum 2,752: 27,520 z
   over 2,560), from 896 under the plane to 28,416 under it. A body sinks through a linked floor onto what is linked under it, and
   `CheckLink` (`warp.cpp`) carries it over as its middle passes the plane, both ways: it is walked down and walked up. Ours
   takes the place of the eight treads at 46.5..50.5: the mouth is 2.5 of those four units, and the ramp's foot is
   4,352 over the cellar's floor, one step. Each half is one sector and must stay one (no light cut), with no other 504 in view of it.
3. **The shift.** The last thing the build does to the finished map: every wall and sprite of the deep layer moves by (-128,
   -16) units, after the light stage, so nothing about how it is drawn changes (16 units is a multiple of every power-of-two floor
   tile's period). It lands at x -127.5..-57.5, y -35..54.5: inside Build's +-131,072 (DWE3M4 and DWE3M5 reach 127 units),
   clear of the drowned places (x -45..-14) and of the sea (y 63 on). The nearest of it is 57 units from the nearest street: 3,648
   of the engine's units, three times the longest ambience's reach, and a shot there is at 6%.
4. **Who reads it by coordinate.** 33 test modules open the built map and name a deep place; `look.py`, `playthrough.py` and
   `gameplay.py` too. They would go on speaking in the plan's own coordinates: the build records the shift and one reader moves
   the layer back in memory.

## What could go wrong

- The ramp is 34 degrees. E2M1's is the same number, but nobody has walked ours.
- A body on the slab as it crosses the plane with another; E4M4 has the same.
- Not looked into: whether an explosion's damage crosses a stack, and how the headless bot takes a sloped one.
- It will not touch a glitch that is inside one layer.

## Recommendation

Do it, and in this order: the two stacks first, where everything still stands (a commit each, so each can be walked), then
the shift, which is mechanical. The stacks are what can feel wrong; the shift is what cannot be seen.
