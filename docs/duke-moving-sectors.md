# Duke's hardcoded moving sectors, and Blood's flexible ones

Duke3D does not let a mapper say how far a door travels. Every moving sector in
the classic game runs a hardcoded routine whose extent, speed and direction come
out of fields that do not look like motion fields: the sector's `extra`, the
effector's `ang`, its `pal`, and in one case a constant in `actors.cpp`.

Blood is the opposite. `kSectorSlide` and `kSectorRotate` read the whole motion
out of marker sprites, so any distance and any angle -- including more than one
full turn -- is expressible.

Converting one to the other needs Duke's constants written down rather than
guessed. `bloodmap.duke_motion` is that transcription; every number in it cites
the EDuke32 function it came from.

## The one thing the two engines agree on exactly

`A_MoveSector` (EDuke32 `actors.cpp`) places **every** wall of the sector at

```text
effector.xy + rotatevec(origin[w], T3)
```

where `origin[w]` was captured at spawn as `wall[w].xy - effector.xy`.

Blood's `TranslateSector` (NBlood `triggers.cpp`) with `bAllWalls` set does the
same thing. `bAllWalls` is true for exactly `kSectorSlide` (616) and
`kSectorRotate` (617). That agreement is what makes a faithful conversion
possible, and it is also what disqualifies 616 for SE20 -- see below.

The two rotations are the same rotation. Build's `rotatevec` uses
`cos = sintable[(a+2560)&2047]` and `sin = sintable[(a+2048)&2047]`; Blood's
`RotatePoint` uses `Cos(a)`/`Sin(a)` with the same signs.

## Where the numbers come from

`game.cpp` copies `sector.extra` into the effector as `sprite.yvel` at spawn, and
the movement code reads it back through `SP(i)`. `premap.cpp` initialises every
sector's `extra` to **256**; a GPSPEED sprite in the sector overrides it. Every
SE0, SE11, SE15 and SE20 in the 52-map corpus has `y_velocity == 0` on disk, so
the map file never carries this value.

| Mechanism | Motion | Extent | Speed | Direction from |
| --- | --- | --- | --- | --- |
| SE11 / ST23 swinging door | rotation about the effector | **512, always** | `(extra>>3) * 2` per tick | `ang > 1024 ? + : -` |
| SE15 / ST25 sliding door | translation along `ang` | `16 * (extra>>3)` | 16 per tick | `ang`, +1024 on each operation |
| SE0 in ST30 rotate bridge | rotation about the SE1 pivot, **plus floor Z** | `2 * extra` | `extra>>5` per tick, always 64 ticks | `pal` |
| SE0 elsewhere | continuous rotation about the pivot | unbounded | `extra>>3` per tick | the *pivot's* `ang` |
| SE20 / ST27 stretch bridge | two walls only | `extra` | 8 per tick | `ang` |

The swing bound is a constant and the bridge turn is not, which is why one
hardcoded angle cannot serve both. E3L11 alone carries a 45-degree bridge
(`extra` 128, from a GPSPEED) and a 90-degree one (`extra` 256).

Duke effectors run at 30 Hz and Blood's `busyTime` is in tenths of a second, so
a motion of *n* ticks wants `busyTime = n / 3`.

## SE20 is not a rigid body

SE20 never calls `A_MoveSector`. `game.cpp` records the two walls of the sector
nearest the effector -- picked with `FindDistance2D`, which is Ken's octagonal
approximation and not the Euclidean distance -- and `actors.cpp` drags only
those two. The rest of the sector stays put, so the bridge *extends*.

Blood splits on exactly that distinction: `TranslateSector` with `bAllWalls`
clear moves only walls flagged `cstat & 16384`. So SE20 lowers to
**`kSectorSlideMarked` (614)** with those two walls marked. Lowering it to 616
slides the whole bridge away instead of extending it.

## Two Blood details that look like nothing and are not

**A marker angle is a signed sweep, not a facing direction.** Blood interpolates
the turn linearly from 0 to `marker0.ang`, so the sign is the direction and a
magnitude past 2048 is more than one turn. The campaign authors `-512` ninety
times and `-4096` -- two turns backwards -- nine times, and `db.cpp` only
byte-swaps the field. Reducing `-256` to `1792` keeps the final pose and sweeps
315 degrees the other way, dragging the sector through everything beside it.

**A slide's markers must both be angle 0.** `TranslateSector` computes the
rotation as `interpolate(marker0.ang, marker1.ang, busy)`, and
`interpolate(a, a, t)` is `a` for every `t`. Two markers carrying the same
non-zero angle therefore rotate the sector by that angle for the entire travel,
at rest included, and never reach zero. 1,021 of the 1,054 slide sectors in the
Blood corpus author both markers at 0 and carry the direction in marker1's
position alone.

## Checking it, rather than asserting it

Structural validation says a map is well formed and the NBlood oracle says it
loads. Neither says a door opens the right distance or stays out of the wall
next to it. `bloodmap.motion_sim` replays the travel in both engines and
`tools/verify_motion` compares them:

```bash
python -m tools.verify_motion maps/duke3d/E3L11.MAP -o work/motion-e3l11.json
python -m tools.verify_motion --corpus maps/duke3d -o work/motion-corpus.json
```

Four independent measurements per moving sector:

* **deviation** -- how far the Blood walls drift from the 3:2-scaled Duke walls
  across the whole sweep, with both re-expressed relative to their own first
  frame so a constant placement offset does not count;
* **rest displacement** -- how far the sector sits from its authored outline
  before anything triggers it, which is the half the relative comparison cannot
  see by construction;
* **folding** -- whether the outline crosses itself at any sampled step;
* **intrusion** -- whether it ends up overlapping a sector it does not share a
  wall with.

The last two are only reported when **Duke does not do the same thing**. Overlap
and folding are not defects on their own: E3L11 parks bridge leaves above each
other at different floor heights, E3L8's sector 5 is self-intersecting as
authored, and E1L3's swing doors are slivers that fold in Duke too. A difference
from the source is the bug; a shared behaviour was authored.

## Result

Across the 26 classic boards that convert, **258 of 258 modelled moving sectors
follow their Duke original**, worst deviation 1.58 Blood units over travels up to
3,000 -- which is 3:2 rounding. Before this pass the same check reported
sliding doors opening to 14% of their travel, bridges turning half as far as
they should or 315 degrees the wrong way, and stretch bridges carrying
themselves off their abutments.

## Still not modelled

* SE6/SE14 subways, SE30 two-way trains, SE16 reactors and SE25 pistons.
* SE0 outside ST30 is a *continuous* rotation with no extent, so a bounded Blood
  rotation cannot express it; only the ST30 case is lowered.
* The intrusion pass compares plan-view outlines and ignores Z, so it relies on
  the Duke comparison to suppress the many legitimate overlaps between sectors
  at different heights.
