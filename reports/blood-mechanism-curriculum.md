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
laws                16  (6 from the engine, 3 from the manual, 7 measured)
laws unsupported    0
corrections to us   5
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
| `a-rotate-marker-is-the-pivot-and-carries-the-angle` | engine | engine-cited, nothing to count |
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
