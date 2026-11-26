# Study: locomotive

## What I want to build

A steam locomotive standing at Gravesend's platform, seen from outside and close up. The owner, 2026-11-18, of my fourth attempt: "Locomotive is made from one texture and there is grave on it. You should study more textures, decals combinations and locomotives in other levels."

## Where Blood built it

Found through the wheel tiles (2320, 2322, 2323: three coupled wheels and a rod in ONE picture) with `tools.catalog find locomotive`, then walked round with `tools.look_at` (frames and `recipe.json` in `round_E1M4`, `round_TEDE1M7`, `round_TEDE1M8`). E1M4 near sector 110 is the campaign's engine seen from outside; E1M3's is only ever seen from inside the train. TEDE1M7 and TEDE1M8 (Death Wish) have named wagons and an engine front.

## What makes it read as that

It is never one surface. E1M4's engine is three tiles and three sprites:

- body: 255, dark rusted plate
- where it is round (the front, the pillars): 2453, a riveted barrel
- every top: 438, diamond plate (a FLOOR, which is what the owner named it)
- a wood-framed opening in the cab
- a flame (3566) and two smokes over the chimney (754 thin, 672 plume)

The riveted underframe plate, 470, is TEDE1M7's engine's, not E1M4's.

The Death Wish trains add a barred vent (794) in the side, a horned face (634) on the front, a lamp, the train's NAME lettered along the wagon, and roofs arched with slopes. E1M3 hangs a bill (356) on its carriage's livery.

## Sizes

Wheel sprite at repeat 88 x 104, its centre 0.61 body over the rail. E1M4's body stands about two bodies over the wheels. Smoke at repeat 56 x 40 and 48 x 80.

## What I will transcribe

The four surfaces by role (underframe, barrel, cab panel, top), one wheel sprite, the vent, the horned face, both smokes, the bill on the carriage.

## What I will not do, and why

No flame: my cab is solid and has no firebox to put it in. No sloped roofs yet. No name lettered on the engine: the letters need a lit, flat run of wall and the boiler's side is the barrel tile.

## What I still do not know

Whether the smoke reads in play (in my frames it is a faint wisp). How E1M4 makes the cab's wood-framed opening (a masked wall or a sprite). None of these tiles has an owner name for use on a train; 438 on a top is his, the rest are my readings.
