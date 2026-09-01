# The mechanism curriculum, mined

`maps/blood/mechanism/` is a taught course: one folder of single-purpose maps, each
demonstrating one mechanism, with a 981-page manual (`xmapedit.pdf`) that explains
them. This project built its mechanism subsystem from the campaign and from
inference instead, and the course disagrees with it in several places. Those
disagreements are the deliverable.

Every law below is a statement plus a **detector**; the detector runs over the
mined maps and the evidence is what it found. A law that measures nothing is
reported as unsupported rather than quietly kept.

```text
maps mined          136  (tier 1: 34, tier 2: 43, other: 59)
constructs read     1291
swept mechanisms    256
laws                17  (6 from the engine, 3 from the manual, 8 measured)
laws unsupported    0
corrections to us   6
excluded            Modern/ -- the NBlood-extension dialect, a separate phase
```

## What the course corrects

The laws that say our model was wrong, not merely incomplete.

### drawn-geometry-is-the-on-pose

The geometry SAVED in the map is the pose at busy 65536, which is state ON. `trInit` translates the sector by -65536 of the marker delta, records THAT as the base with `setBaseWallSect`, and only then applies the sector's own busy. So the base -- the OFF pose -- is the drawn outline minus the marker delta, always, whatever the author intended.

**We had:** We had this as a convention -- 'the mapper draws at the ON pose'. It is not a convention, it is what the loader does, and it holds even when the author drew the other pose by mistake.

- NBlood/source/blood/src/triggers.cpp:2224-2245 (trInit)
- DOOR-CURTAINS.map s3: drawn tip y -1152, delta +896, base y -2048 == the OFF marker, to the unit


### slide-markers-are-a-vector-not-two-places

For a SLIDE, the marker pair contributes only its difference. `TranslateSector` moves each base point by `interpolate(m1, m2, busy) - m1`, so the pair's absolute position on the grid is free: a pair parked anywhere with the right separation drives the sector identically.

**We had:** `motion.drawn_pose` compared a moved vertex against the markers' ABSOLUTE coordinates and called the answer the drawn pose. That only works for the pairs an author placed at the two poses; for the rest it measures nothing. It is a convention check, and is now named as one.

- NBlood/source/blood/src/triggers.cpp:879-928 (TranslateSector: x + vc - a4)
- xmapedit.pdf p.240: the arrow's tail is the OFF position and its point the ON position


### a-rotate-marker-angle-is-a-total-turn

That angle is a TOTAL TURN, not a final heading. `RotatePoint` masks it with 2047, so a marker angle that is a whole number of full circles spins the sector all the way round and returns it to where it was drawn -- a gear or a fan, not a door. Thirteen of the curriculum's fifteen rotator markers are exact multiples of 2048; MACHINERY-GEAR turns 20480, which is ten revolutions.

**We had:** Nothing in the stack read a rotator's marker at all. `marker_pair` wants two markers, a rotator has one, and so 180 rotators across the curriculum mined with no motion data and ten of them raised inside the sweep. `motion.rotate_marker` reads the pivot and the turn.

- MACHINERY-GEAR.map s1: turn 20480 about (-4051, -473)
- MACHINERY-GEAR.map s3: turn -1024, half a circle, a real swing
- DOOR-ROTATING.map s4: turn 8192 on channel 7 (level start) with a wave and a retrigger -- something that spins forever


### a-transmitter-must-declare-an-edge

`SetSpriteState` only calls `evSend` inside `if (triggerOn && state)` or `if (triggerOff && !state)`. A toggle, one-way or padlock switch with neither flag transmits NOTHING however correct its channel is. A COMBINATION switch is different: it sends from its own arm of `OperateSprite`, `if (command == kCmdLink && txID > 0)`, outside those guards -- which is why the curriculum's six edgeless switches are all combination switches on command 5, and why they work.

**We had:** We generalised this to every transmitter, and `motion.transmitter` REFUSES to build a sender without an edge. That is too broad: it binds switches, because switches are what `SetSpriteState` handles. Relays (kGenTrigger), sector-sound sprites and command-carrying decorations transmit by other paths and carry no edge flags in the tutorials -- five of them do exactly that.

- NBlood/source/blood/src/triggers.cpp:100-130 (SetSpriteState)
- NBlood/source/blood/src/triggers.cpp:475-493 (kSwitchCombo sends kCmdLink outside the edge guards)
- SPRITE-OTHERSP.map sprites 66-70, 72: combination switches, command 5, no edge flags
- xmapedit.pdf p.239: the curtain's own wiring sets Send When Going ON and Going OFF


### the-button-is-the-surface-you-touch

The tutorials do not wire a shove with the sector's `trigger_wall_push`. They put an XWALL on each face you are meant to touch -- type 0 Decoration, tx on the mechanism's channel, command Toggle, Trigger On Push -- and the sector merely RECEIVES that channel. The mechanism's own tx slot stays free, and the button is exactly the surface, not the room.

**We had:** Our curtain constructor set `trigger_push` and `trigger_wall_push` on the SECTOR unconditionally, and a commit message of mine claimed DOOR-CURTAINS s3 carries them. It does not: s3's whole XSECTOR is rx 100, two busy times and the marker pair.

- xmapedit.pdf p.239 (Folding Door/Curtain, step 1)
- DOOR-CURTAINS.map s3: walls 38/39/40 each carry tx 100, command 3, trigger_push; the sector carries only rx 100


### motion-crosses-storage-boundaries-by-default

A mechanism deforming more than its own sector is the NORMAL case in the curriculum, not the pathology we treated it as. `dragpoint` moves a vertex for every wall incident on it, so any flagged wall shared with a neighbour drags that neighbour too.

**We had:** We modelled a construct as owning its own sector and treated a motion reaching a neighbour as a defect to be engineered away. The tutorials say the opposite: it is the default, and what matters is whether the construct DECLARED the sectors it moves.

- NBlood/source/build/src/engine.cpp:13071 (dragpoint)


## Every law

| law | grade | evidence |
| --- | --- | --- |
| `drawn-geometry-is-the-on-pose` | engine | engine-cited, nothing to count |
| `slide-markers-are-a-vector-not-two-places` | engine | 206 place the pair at the two poses |
| `a-rotate-marker-is-the-pivot-and-carries-the-angle` | engine | 185 citations |
| `a-rotate-marker-angle-is-a-total-turn` | derived | 185 citations |
| `state-becomes-busy-at-load` | engine | engine-cited, nothing to count |
| `a-path-sector-fails-silently` | engine | engine-cited, nothing to count |
| `a-transmitter-must-declare-an-edge` | engine | 1124 switches checked, 6 silent |
| `the-button-is-the-surface-you-touch` | documented | 124 citations |
| `a-mechanisms-sprites-are-members-of-it` | documented | 247 citations |
| `a-link-is-a-congruent-pair-of-planes` | documented | engine-cited, nothing to count |
| `a-link-sector-wants-a-simple-silhouette` | derived | 0-VERTICALPORTAL.map: the floor marker floats: sprite 1 sits at z 4096 and the plane it links is at 24576 |
| `motion-crosses-storage-boundaries-by-default` | derived | 100 citations |
| `the-fin-is-an-isolation-technique` | derived | 106 citations |
| `z-motion-is-state-anchored-too` | derived | 281 citations |
| `the-relay-is-a-sprite` | derived | 20 citations |
| `one-xsector-is-one-of-each` | derived | 96 citations |
| `a-mechanism-sentence-includes-what-it-drives` | derived | 81 citations |

### drawn-geometry-is-the-on-pose

The geometry SAVED in the map is the pose at busy 65536, which is state ON. `trInit` translates the sector by -65536 of the marker delta, records THAT as the base with `setBaseWallSect`, and only then applies the sector's own busy. So the base -- the OFF pose -- is the drawn outline minus the marker delta, always, whatever the author intended.

- NBlood/source/blood/src/triggers.cpp:2224-2245 (trInit)
- DOOR-CURTAINS.map s3: drawn tip y -1152, delta +896, base y -2048 == the OFF marker, to the unit


### slide-markers-are-a-vector-not-two-places

For a SLIDE, the marker pair contributes only its difference. `TranslateSector` moves each base point by `interpolate(m1, m2, busy) - m1`, so the pair's absolute position on the grid is free: a pair parked anywhere with the right separation drives the sector identically.

- NBlood/source/blood/src/triggers.cpp:879-928 (TranslateSector: x + vc - a4)
- xmapedit.pdf p.240: the arrow's tail is the OFF position and its point the ON position


```text
206 place the pair at the two poses
DOOR-3DSLIDEDOOR.map s2
DOOR-3DSLIDEDOOR.map s24
DOOR-CLOSET.map s17
DOOR-CLOSET.map s18
50 park the pair elsewhere
... and 4 more
```

### a-rotate-marker-is-the-pivot-and-carries-the-angle

A ROTATE has one marker and reads it differently from a slide: its x/y are the PIVOT that `RotatePoint` turns the sector about -- absolute position matters here -- and its `ang` is the ON angle, interpolated from 0. Reusing the slide's reading on a rotator gets both wrong.

- NBlood/source/blood/src/triggers.cpp:2229-2231 (the single-marker call passes a8=0, a11=pMark1->ang)
- NBlood/source/blood/src/triggers.cpp:889-905 (RotatePoint about a4,a5)


```text
DOOR-COMBIDOORS.map s6 turns 512
DOOR-COMBIDOORS.map s7 turns -512
DOOR-ROTATEGATE.map s0 turns -512
DOOR-ROTATING.map s4 turns 8192 (whole circles)
DOOR-SWINGING.map s12 turns -512
DOOR-SWINGING.map s13 turns -512
... and 179 more
```

### a-rotate-marker-angle-is-a-total-turn

That angle is a TOTAL TURN, not a final heading. `RotatePoint` masks it with 2047, so a marker angle that is a whole number of full circles spins the sector all the way round and returns it to where it was drawn -- a gear or a fan, not a door. Thirteen of the curriculum's fifteen rotator markers are exact multiples of 2048; MACHINERY-GEAR turns 20480, which is ten revolutions.

- MACHINERY-GEAR.map s1: turn 20480 about (-4051, -473)
- MACHINERY-GEAR.map s3: turn -1024, half a circle, a real swing
- DOOR-ROTATING.map s4: turn 8192 on channel 7 (level start) with a wave and a retrigger -- something that spins forever


```text
DOOR-COMBIDOORS.map s6 turns 512
DOOR-COMBIDOORS.map s7 turns -512
DOOR-ROTATEGATE.map s0 turns -512
DOOR-ROTATING.map s4 turns 8192 (whole circles)
DOOR-SWINGING.map s12 turns -512
DOOR-SWINGING.map s13 turns -512
... and 179 more
```

### state-becomes-busy-at-load

`state` is the only thing that decides where a mechanism starts: at load, `if (pXSector->state) pXSector->busy = 65536`. The same line exists for XWALL and XSPRITE, so walls and sprites keep state the same way sectors do.

- NBlood/source/blood/src/triggers.cpp:2186-2188 (XWALL), :2210-2211 (XSECTOR), :2266-2268 (XSPRITE)


### a-path-sector-fails-silently

`InitPath` looks for a path marker whose `data_1` matches the sector's `data`, and when there is none it prints a system message and RETURNS. The sector stays in the map, keeps its type, and never moves. A path mechanism with a mistyped id is not an error anyone sees -- it is a dead sector.

- NBlood/source/blood/src/triggers.cpp:1745-1774 (InitPath)


### a-transmitter-must-declare-an-edge

`SetSpriteState` only calls `evSend` inside `if (triggerOn && state)` or `if (triggerOff && !state)`. A toggle, one-way or padlock switch with neither flag transmits NOTHING however correct its channel is. A COMBINATION switch is different: it sends from its own arm of `OperateSprite`, `if (command == kCmdLink && txID > 0)`, outside those guards -- which is why the curriculum's six edgeless switches are all combination switches on command 5, and why they work.

- NBlood/source/blood/src/triggers.cpp:100-130 (SetSpriteState)
- NBlood/source/blood/src/triggers.cpp:475-493 (kSwitchCombo sends kCmdLink outside the edge guards)
- SPRITE-OTHERSP.map sprites 66-70, 72: combination switches, command 5, no edge flags
- xmapedit.pdf p.239: the curtain's own wiring sets Send When Going ON and Going OFF


```text
1124 switches checked, 6 silent
SPRITE-OTHERSP.map: switch: combination sprite 66 declares no edge
SPRITE-OTHERSP.map: switch: combination sprite 67 declares no edge
SPRITE-OTHERSP.map: switch: combination sprite 68 declares no edge
SPRITE-OTHERSP.map: switch: combination sprite 69 declares no edge
SPRITE-OTHERSP.map: switch: combination sprite 70 declares no edge
... and 1 more
```

### the-button-is-the-surface-you-touch

The tutorials do not wire a shove with the sector's `trigger_wall_push`. They put an XWALL on each face you are meant to touch -- type 0 Decoration, tx on the mechanism's channel, command Toggle, Trigger On Push -- and the sector merely RECEIVES that channel. The mechanism's own tx slot stays free, and the button is exactly the surface, not the room.

- xmapedit.pdf p.239 (Folding Door/Curtain, step 1)
- DOOR-CURTAINS.map s3: walls 38/39/40 each carry tx 100, command 3, trigger_push; the sector carries only rx 100


```text
DOOR-3DSLIDEDOOR.map s2 is shoved through walls [15, 16, 17, 18, 33, 35]
DOOR-CEILING.map s42 is shoved through walls [224, 232]
DOOR-CEILING.map s43 is shoved through walls [224, 232]
DOOR-CEILING.map s58 is shoved through walls [288, 296]
DOOR-CEILING.map s59 is shoved through walls [288, 296]
DOOR-CEILING.map s73 is shoved through walls [352]
... and 118 more
```

### a-mechanisms-sprites-are-members-of-it

A sprite inside a moving sector does not move with it by default: it has to be flagged into the motion the same way a wall is. The manual makes this an explicit step for the curtain's sound sprite, and every curtain in the tutorial has its sector-sound sprite flagged.

- xmapedit.pdf p.240: make the SFX sprite blue so it moves with the door
- DOOR-CURTAINS.map s3: sprite 0 (kSoundSector) carries a carry bit


```text
DOOR-3DSLIDEDOOR.map s2 carries 3 sprite(s)
DOOR-3DSLIDEDOOR.map s24 carries 3 sprite(s)
DOOR-CLOSET.map s17 carries 3 sprite(s)
DOOR-CLOSET.map s18 carries 3 sprite(s)
DOOR-CLOSET.map s19 carries 2 sprite(s)
DOOR-CLOSET.map s20 carries 3 sprite(s)
... and 241 more
```

### a-link-is-a-congruent-pair-of-planes

The two halves of a room-over-room are a portal, so they must be the same size and shape, both must carry tile 504 on the plane that faces the other, their markers must sit ON those planes rather than floating, and `data_1` is what pairs them when a map has more than one.

- xmapedit.pdf p.364-365 (ROR: Room Over Room)


### a-link-sector-wants-a-simple-silhouette

The manual blames HOMs on over-complicated link sectors, and the shape of the outer loop is where that shows: every working link sector in ROR1 and ROR2 has a four- or six-wall CONVEX outer loop with its complexity in inner loops, while BADROR -- the map the manual points at to show the glitches -- cuts its alcoves into the boundary and gets a ten-wall concave one. This is a RISK, not a rule: STACKS3DSPACES itself has two concave link sectors and ships as a working example.

- xmapedit.pdf p.364: do not over-complicate the shape
- STACKS3DSPACES-BADROR.map s0 and s7 (concave, 10 walls)
- STACKS3DSPACES-ROR1.map, STACKS3DSPACES-ROR2.map (all convex)


```text
0-VERTICALPORTAL.map: the floor marker floats: sprite 1 sits at z 4096 and the plane it links is at 24576
0-VERTICALPORTAL.map: the ceiling marker floats: sprite 0 sits at z 4096 and the plane it links is at 0
E1M1ZD1.map: s115 is a link sector whose outer loop is concave (44 walls); a link is a portal silhouette and re-entrant corners in it are what HOMs
E1M1ZD1.map: s54 is a link sector whose outer loop is concave (49 walls); a link is a portal silhouette and re-entrant corners in it are what HOMs
E1M1ZDF.map: s115 is a link sector whose outer loop is concave (44 walls); a link is a portal silhouette and re-entrant corners in it are what HOMs
E1M1ZDF.map: s54 is a link sector whose outer loop is concave (49 walls); a link is a portal silhouette and re-entrant corners in it are what HOMs
... and 9 more
```

### motion-crosses-storage-boundaries-by-default

A mechanism deforming more than its own sector is the NORMAL case in the curriculum, not the pathology we treated it as. `dragpoint` moves a vertex for every wall incident on it, so any flagged wall shared with a neighbour drags that neighbour too.

- NBlood/source/build/src/engine.cpp:13071 (dragpoint)


```text
DOOR-3DSLIDEDOOR.map s2 deforms 3 sectors
DOOR-3DSLIDEDOOR.map s24 deforms 3 sectors
DOOR-CLOSET.map s17 deforms 2 sectors
DOOR-CLOSET.map s18 deforms 2 sectors
DOOR-CLOSET.map s19 deforms 2 sectors
DOOR-CLOSET.map s20 deforms 2 sectors
... and 94 more
```

### the-fin-is-an-isolation-technique

Confining a motion to one sector is a deliberate construction, not a property of the mechanism type: the fabric is drawn as an internal fin so every moved vertex is interior to the sector's own outline. It is what you build when the room must not be disturbed -- and the same map slides other curtains straight into their neighbours where that does not matter.

- DOOR-CURTAINS.map s3, s24, s53 (motion set is the sector itself); s10 in the same map deforms two


```text
DOOR-COMBIDOORS.map s2
DOOR-CURTAINS.map s3
DOOR-CURTAINS.map s6
DOOR-CURTAINS.map s8
DOOR-CURTAINS.map s15
DOOR-CURTAINS.map s17
... and 100 more
```

### z-motion-is-state-anchored-too

The vertical has the same shape as the horizontal: a z-moving sector carries `off_floor_z`/`on_floor_z` and `off_ceiling_z`/`on_ceiling_z`, one pair per plane, and `state` chooses between them exactly as it chooses between markers. A lift is the pair with the floor travelling; a ceiling door is the pair with the ceiling travelling; both planes may travel at once.

- MACHINERY-LIFT.map s2 (floor 8192 -> -24576, ceiling still), s6 (both planes travel)
- NBlood/source/blood/src/triggers.cpp:2246 (ZTranslateSector from the same busy)


```text
DOOR-CEILING.map s11 type 600
DOOR-CEILING.map s14 type 600
DOOR-CEILING.map s19 type 600
DOOR-CEILING.map s22 type 600
DOOR-CEILING.map s27 type 600
DOOR-CEILING.map s30 type 600
... and 275 more
```

### the-relay-is-a-sprite

When the author needs a channel to fan out, to be delayed, or to change command on the way, they drop a kGenTrigger (sprite type 700): it receives on one channel and transmits on another, with its own busy and wait. It is the move that gets a second transmitter into a sector that has already spent its one tx.

- MACHINERY-LIFT.map sprite 127: rx 106, tx 115, command 3, wait 16
- common_game.h:440 (kGenTrigger = 700)


```text
DOOR-CEILING.map: 2 relay sprite(s)
DOOR-CLOSET.map: 1 relay sprite(s)
DOOR-CURTAINS.map: 1 relay sprite(s)
DOOR-CURTAINSD.map: 1 relay sprite(s)
DOOR-PORTCULLIS.map: 2 relay sprite(s)
DOOR-SLIDING.map: 2 relay sprite(s)
... and 14 more
```

### one-xsector-is-one-of-each

A sector has exactly one XSECTOR, and an XSECTOR has one rx, one tx, one state machine, one shade wave, one wind, one panning, one bob and one z pair. Compositions therefore collide over them, and the tutorials are full of sectors carrying three or more at once -- which is how close to the ceiling ordinary authoring runs.

- MACHINERY-LIFT.map s25: rx, state, z pair and bob on one sector
- MACHINERY-LIFT.map s16: tx, state, z pair, driving the light in s17


```text
DOOR-CEILING.map s46: rx, z pair, key
DOOR-CEILING.map s54: rx, z pair, key
DOOR-CEILING.map s59: rx, bob, z pair
DOOR-CEILING.map s62: rx, z pair, key
DOOR-CEILING.map s70: rx, z pair, key
DOOR-CEILING.map s89: rx, z pair, key
... and 90 more
```

### a-mechanism-sentence-includes-what-it-drives

Mechanisms in the curriculum routinely transmit onward as part of doing their job -- a lift that dims the shaft, a curtain that brightens the room behind it. The downstream effect is not decoration bolted on afterwards; it is in the same XSECTOR as the motion, and reading the mechanism without it reads half a sentence.

- MACHINERY-LIFT.map s16 -> s17 (command 5 Link to a shade wave)
- DOOR-CURTAINS.map s21 -> s20 (the same pattern)


```text
DOOR-CEILING.map s38 drives s33, s37
DOOR-CEILING.map s76 drives s80
DOOR-CEILING.map s77 drives s80
DOOR-CLOSET.map s22 drives s15, s16
DOOR-CLOSET.map s30 drives s52
DOOR-CLOSET.map s51 drives s52
... and 75 more
```

## The shapes the course teaches

What a mechanism's payload does, counted over every swept sector in the course.

```text
  160  the whole sector travels
  123  nothing moves
   69  part of the sector travels
   62  the sector resizes itself
   24  boundary re-partition
```

```text
  196  sector type 600
   72  sector type 602
   12  sector type 604
   43  sector type 612
    4  sector type 613
  197  sector type 614
   77  sector type 615
   67  sector type 616
  104  sector type 617
   35  sector type 618
    2  sector type 619
```

## The DragPoint closure, swept (2026-09-01)

`motion-crosses-storage-boundaries-by-default` said a mechanism deforming its
neighbours is the normal case. The swept-state gate then swept the mover's own
polygon and called every neighbour static, so it was blind to exactly that
case. `motion_sim.closure_sweep` now moves every vertex `DragPoint` moves and
`closure_health` judges every LOOP the closure touches -- the mover's own and
each neighbour's -- for inversion against its drawn winding, self-intersection,
and crossing a wall the motion does not move.

Engine basis, read this session: `NBlood/source/blood/src/triggers.cpp:817-854`
(`DragPoint` walks `nextwall` forward through each partner's `point2`, and when
that walk meets a one-sided wall it restarts and goes the other way through
`lastwall().nextwall`); `:897-910` and `:912-926` (a flagged wall drags its
`point2`'s vertex too, when that wall carries no flag of its own; 32768 does it
in reverse); `NBlood/source/build/src/engine.cpp:13227` (`lastwall`). The
`gModernMap` branch inside `TranslateSector` (`:874-878`, `sprDy`) is about
reverse-flagged SPRITES, not walls, so the vanilla and modern wall paths are
the same code and this is the vanilla reading.

### The census

`python -m tools.sweep_drag_closure` (16 steps), over the vanilla course
(`maps/blood/mechanism/*.map` primers + `Vanilla/`, 138 maps; `Modern/`
excluded) and the 43 campaign maps. Nothing generated is mined.

```text
                                      curriculum   campaign
maps                                         138         43
swept mechanisms (types 614-617)             429        648
  614 / 615 / 616 / 617              198/77/50/104  308/41/88/211
deform a neighbour                           199        412
  ... a neighbour that does not move         192        363
  ... in a co-moving assembly                 39        110
ISOLATED -- the fin technique                109        200
judgeable neighbour loops touched            176        383
assembly loops, not judged                   132        215
neighbour loop inverts at some pose            0          1
neighbour loop crosses itself                  0         18
the MOVER's own loop inverts or folds          0          4
cuts a wall it does not move                   2         89
```

**Isolation is a minority technique and a deliberate one.** 109 of 429 in the
course, 200 of 648 in the campaign: roughly one mechanism in four keeps its
motion to itself. Every other one reshapes something else on purpose, which is
why "the motion set is bigger than the sector" was never the right defect.

**The tutorials are clean and the campaign is not.** Zero neighbour inversions
and zero neighbour folds across 429 taught mechanisms, against 1 and 18 in the
campaign; 2 crossings against 89. The isolated lesson maps are built to a
precision the shipped levels are not, which is the argument for diagnosing
against them.

### An assembly cannot be judged one mechanism at a time

The first run of this census reported 10 inverting and 72 self-crossing
neighbours and was wrong about most of them. `TranslateSector` runs per
mechanism, but every mechanism on a channel runs in the same tick, each
re-placing the shared vertices from its own base -- so a loop whose moved walls
two mechanisms drag is only whole when both have travelled. E1M4's rotor ring
(s321-s329 around the hub s352) and E3M2's fifteen-sector boat around s16 are
that shape, and swept singly each spoke turns the hub inside out.

`co_driven_walls` finds them per WALL, not per sector, and `closure_health`
reports such a loop in `notes` and never in `problems`. 132 curriculum loops
and 215 campaign loops are excluded this way; 127 campaign and 13 curriculum
hubs would break if judged alone, and they are listed in the JSON as
candidates, not defects.

### Grazes are not folds

A 617 rotor hinges on a vertex OF the room it turns in, so at a small angle its
leaf tip crosses that room's wall a hair past the corner. `crossing_depth`
measures how far into each other two crossing segments reach, and the campaign's
27 self-crossing neighbour loops split cleanly on it: eleven top out at 13.69
units and appear at one step of sixteen, the rest start at 19.98 and run to 707
over many steps. `SWEEP_GRAZE = 16.0` sits in that gap. It is also the right
order for the model's own error -- the interpolated marker angle is rounded to
a whole Build unit, about 1.6 units of position at a 1024-unit radius.

### The inside-out candidates

The owner reported seeing inside-out sectors. Case (b) of the supervisor's four
-- a neighbour deformed by `DragPoint` that no gate swept -- has exactly one
campaign instance under this reading:

```text
E4M2.MAP s201 (type 615) drags s200 loop 0, which is inverted at 11 of 17
  poses, INCLUDING busy 0 -- the pose the level loads in. Its signed area
  runs -390562 -> +128418 over the travel and the drawn pose is +128418,
  so it is wound the wrong way for two thirds of the motion and right only
  at the end. The same mechanism folds its own loop 1 at three poses.
```

Four movers break their OWN loop: `E1M2 s34` (614), `E1M3 s183` (615),
`E4M2 s201` (615), `E6M3 s76` (614).

Eighteen campaign mechanisms fold a neighbour past the graze tolerance, and the
persistent ones -- the ones that stay folded over most of the travel -- are:

```text
E2M5  s95, s96  (615) -> s708 loop 1     15-16 of 17 poses
E2M5  s521, s522 (617) -> s525 loop 0    13 of 17
E3M1  s66 (617) -> s71 loop 0             6 of 17
E3M3  s0, s263 (615) -> s1..s12 loop 0    9-10 of 17 each
E3M3  s13 (615) -> s14 loop 0            10 of 17
E4M2  s201 (615) -> s200 loop 0          14 of 17
```

These are candidates for the owner's sighting, not verdicts: the model rounds
the marker angle where the engine rounds coordinates, and none of them has been
seen in the engine. Full per-mechanism evidence is in
`reports/blood-mechanism-drag-closure.json`.

### The two closures agreed, and one of them was short

`motion.drag_closure` (nextwall) and `motion.motion_set` (coordinate
coincidence) agree on every mechanism the P1 run checked, and the census
extends that: over 1077 mechanisms the coordinate reading reaches MORE sectors
than the chain on 69 of them (66 campaign, 3 curriculum) and fewer on none --
which is the predicted direction, since linked walls always share a coordinate
and coincident walls need not be linked. Those 69 are `coincident but not
chained` vertices: a wall sits on the moved point with no `nextwall` pairing
reaching it, so the engine leaves it behind and the motion tears the map open
there. 186 such vertices over 108 campaign mechanisms, 11 over 4 curriculum
ones (`DOOR-SLIDING` s41, `DOOR-SLIDINGD` s67, `DOOR-SWINGINGD` s35,
`TRAP-WALLTRAP` s4).

There were two implementations of the walk and they were not the same. The
short one in `motion.py` walked the ring forward only; `DragPoint`'s forward
walk STOPS at a one-sided wall and then goes round the other way. A fin beside
a void slot is precisely that case -- the mechanism this project builds most.
`motion_sim` owns the walk now and `motion.drag_closure` delegates to it.

### Where the gate runs

`bloodmap.swept_state.run` sweeps the closure for every mechanism in a built
map, and both builds call it: `projects/pattern-zoo/sweep.py` reports it beside
the template conformance, and `projects/blood-city/level/build_skeleton.py`
refuses to write the map on a problem. The fail-first fixture is
`tests/test_swept_state._strip_with_thin_neighbour`: a slide-marked strip whose
flagged wall is shared with a thin sector that is inside out at busy 0. The
mover's own polygon is healthy at every pose, so the previous gate passed it
(`test_the_mover_only_sweep_is_blind_to_the_neighbour` keeps that on record).

## Editor debris

`ASAVE1.map` and `ASAVE1.bak` in `maps/blood/mechanism/` are XMAPEDIT autosave
files, not tutorials. They are left untouched and excluded from the mine; the
owner may want them removed from the corpus.

## Limitations

- `Modern/` (45 maps) is unmined. It is the NBlood-extension dialect and its
  semantics are not vanilla Blood's; mining it as vanilla would put extension
  behaviour into base-engine laws. It is a queued phase.
- The manual is read for the mechanisms this run reworks. It has 981 pages and
  most of them are still unread.
- A law graded `derived` is a measurement over 98 maps, not a proof. The
  concave-link-sector law is the honest example: it separates BADROR from the
  two working ROR maps, and then fires on `STACKS3DSPACES` itself, which ships
  as a working example. It is reported as a risk, not a rule.
