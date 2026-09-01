# Pattern Zoo -- the tour sheet

Every pattern, mechanism and constructor the pipeline has learned, one
labelled exhibit each, in the order you walk them. Pre-screen here, then
play the map and send corrections **by label** -- the labels are stable
identities and a rename loses the thread of corrections attached to one.

**v2.** You walked v1 and found that nothing worked: every door was a
hand-written XSECTOR dict on a type-0 sector, which the engine ignores
entirely. Every gate v1 passed was a gate about *depiction*. So v2 is
assembled only by the constructors that own each concept, and the
acceptance gate is that **the zoo reads itself**: the map is read back
with `bloodmap.effects` and `bloodmap.conditional` -- the same code that
reads the campaign -- and every claim below is checked against what that
reading finds. A dead map fails the build.

Each stall is also a **habitat**: its size, material and dressing are
chosen to demonstrate how that mechanism sits where the campaign uses it.
The habitat is itself a claim, and is meant to be judged as one.

```text
map            projects/pattern-zoo/level/pattern-zoo.MAP
built from     projects/pattern-zoo/registry.py (generated, never hand-placed)
size           99 sectors, 538 walls, 307 sprites
exhibits       21, of which 2 are honest EMPTY stalls
live sectors   7 x type 600, 3 x type 614, 4 x type 615
```

## Verification

```text
the zoo reads itself    12 claims checked, 0 unsupported
structural validation   0 errors, 0 warnings
round trip              byte-exact
geometry audit          9 zero_exit_gameplay_sector, every one a shut door
                        leaf or the room it hides -- declared in the source
                        and the point of the exhibit
NBlood load/spawn       **pass** -- the map loads and the player spawns
observer                21 stalls rendered, 0 refused
```

## What to try first

1. **PUSH DOOR** -- open it. In v1 this did nothing at all; it is the
   single most important thing to confirm, and if it works the other six
   type-600 sectors are built the same way.
2. **LIFT** -- ride it, then look at what is up there. The habitat rule
   says a lift needs a destination; judge whether that upper room is one.
3. **TURNSTILE PAIR** -- walk into it. Passage through a rotating door is
   the pipeline's longest-standing unproven claim; ten seconds of you
   walking settles it.
4. **COUNTER** -- try to reach the working side from the front. The
   clearance is the campaign's own mined rule, not a guess.
5. **CRATE STACK** -- check these are crates. A build once shipped tile
   459, a moss-grown rock, as a crate.

## The exhibits

### 1. PUSH DOOR

a z-motion door opened by pushing its own wall.

- **try:** press use on the door face; it should rise
- **from:** doors.z_motion_door(interaction='direct'), which sets the busy times a bare endpoints dict leaves at zero
- **read back as:** 1 sector(s) of type 600, read as a changes what fits through, worked by a push
- **covers:** bloodmap.doors.z_motion_door, bloodmap.doors.xsector_direct_use
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 2

![PUSH DOOR](projects/pattern-zoo/reports/tour/observation/frames/push_door.png)

### 2. SWITCHED DOOR

the same motion, worked from a switch across the room.

- **try:** press the switch on the side wall, not the door
- **from:** doors.z_motion_door(interaction='remote'); reports/blood-effects-switches.md
- **read back as:** 1 sector(s) of type 600, read as a changes what fits through, worked by a switch, listening on channel 300
- **covers:** bloodmap.doors.xsector_remote_rx
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 7

![SWITCHED DOOR](projects/pattern-zoo/reports/tour/observation/frames/switched_door.png)

### 3. KEYED DOOR

a door that wants the moon key, which lies in the room.

- **try:** try the door, then take the key and try again
- **from:** doors.z_motion_door(key=6); E1M4 sector 295 wears the moon emblem; knowledge/blood/design/keys-v1.json
- **read back as:** 1 sector(s) of type 600, read as a changes what fits through, requiring key 6
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 12

![KEYED DOOR](projects/pattern-zoo/reports/tour/observation/frames/keyed_door.png)

### 4. LIFT

a floor that carries a body between two standing levels.

- **try:** ride it up, step off, and look back down
- **from:** reports/blood-effects-motion.md; E1M3 sector 241, whose floor endpoints are exactly its neighbours'
- **read back as:** 1 sector(s) of type 600, read as a carries a body between levels
- **hand-composed dressing:** the mechanism itself: a floor-travelling z-motion, because doors.z_motion_door writes ceiling endpoints only; the upper room that makes the ride worth taking: material, light and two props placed by hand -- promotion candidate
- **room:** 66560 clear (3.92 player heights), 5120 x 7168
- **sector:** 17

![LIFT](projects/pattern-zoo/reports/tour/observation/frames/lift.png)

### 5. CRACK BARRIER

a wall that opens once, when shot, and never closes again.

- **try:** shoot the crack; what it opens stays open
- **from:** reports/blood-conditional-topology.md; E1M4 sprite 373 on channel 119, listeners flush at rest
- **read back as:** 1 sector(s) of type 600, worked by a shot, listening on channel 301, one-way
- **hand-composed dressing:** the load-bearing wall the breach interrupts is plain masonry; no constructor owns a damaged-wall habitat -- promotion candidate
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 21

![CRACK BARRIER](projects/pattern-zoo/reports/tour/observation/frames/crack_barrier.png)

### 6. TURNSTILE PAIR

two counter-rotating four-vane rotors at E1M4's spin rate.

- **try:** WALK THROUGH IT. this settles the parked passage question
- **from:** mechanism.turnstile_pair; reports/blood-rotating-doors.md; passage unproven -- reports/blood-passage-oracle.md
- **read back as:** 2 sector(s) of type 615, listening on channel 7
- **hand-composed dressing:** a public forecourt for the pair to flank, as E1M4's carnival entry does -- promotion candidate
- **covers:** bloodmap.mechanism.turnstile_pair
- **room:** 33280 clear (1.96 player heights), 7168 x 6144
- **sector:** 25

![TURNSTILE PAIR](projects/pattern-zoo/reports/tour/observation/frames/turnstile_pair.png)

### 7. TURNSTILE SAME WAY

the DNE3L6 variant: both rotors turning the same way.

- **try:** walk through and compare with the pair next door
- **from:** mechanism.turnstile_pair(counter_rotating=False); DNE3L6 sectors 3 and 11
- **read back as:** 2 sector(s) of type 615, listening on channel 7
- **covers:** bloodmap.mechanism.turnstile
- **room:** 33280 clear (1.96 player heights), 7168 x 6144
- **sector:** 32

![TURNSTILE SAME WAY](projects/pattern-zoo/reports/tour/observation/frames/turnstile_same_way.png)

### 8. SLIDING GATE

two leaves that part along their own line into the jambs.

- **try:** press it and watch where the leaves go
- **from:** mechanism.sliding_gate, built to the campaign template
- **read back as:** 1 sector(s) of type 614
- **hand-composed dressing:** the yard the gate closes off: a plain stone room, not a courtyard with anything in it -- promotion candidate
- **covers:** bloodmap.mechanism.sliding_gate
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 39

![SLIDING GATE](projects/pattern-zoo/reports/tour/observation/frames/sliding_gate.png)

### 9. CASKET

the player start as a mechanism: a lid that lifts.

- **try:** look up, then walk out; E1M1 opens inside one of these
- **from:** owner-attested E1M1 reading, sectors 30 and 28. The full casket is slide, stack link and z at once; this is its z half, which is as far as one constructor goes
- **read back as:** 1 sector(s) of type 600
- **room-over-room:** placed clear of the other ROR exhibit, so no two ROR volumes are in view at once
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 42

![CASKET](projects/pattern-zoo/reports/tour/observation/frames/casket.png)

### 10. CURTAIN

a slide used as furnishing, not as a way through.

- **try:** open it; nothing behind it was ever closed off
- **from:** owner-attested E1M1 reading, sector 125. Its tile has no owner binding, which is why the dressing plane cannot name it -- reports/blood-role-v2.md
- **read back as:** 1 sector(s) of type 614
- **hand-composed dressing:** a proscenium for the curtain to hang in; hand-composed as a framed opening -- promotion candidate
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 45

![CURTAIN](projects/pattern-zoo/reports/tour/observation/frames/curtain.png)

### 11. SHELF SECRET

a shelf that slides aside and is the way into a secret.

- **try:** find what opens it, then step behind the shelf
- **from:** owner-attested E1M1 reading, sector 70; the secret sector transmits on channel 2, kChannelSecretFound
- **read back as:** 1 sector(s) of type 614, listening on channel 304
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 50

![SHELF SECRET](projects/pattern-zoo/reports/tour/observation/frames/shelf_secret.png)

### 12. FACADE

a street frontage with its bays, reveal and lettered sign.

- **try:** stand back across the street and read the sign
- **from:** aperture.facade_run; reports/blood-facade-build.md
- **covers:** bloodmap.aperture.facade_run
- **room:** 49920 clear (2.94 player heights), 9216 x 8192
- **sector:** 54

![FACADE](projects/pattern-zoo/reports/tour/observation/frames/facade.png)

### 13. DRESSED DOORWAY

an opening wearing its jamb rail and threshold.

- **try:** look down at the threshold and up along the jambs
- **from:** aperture.framed_door; owner anchors 195 (metal rail) and 200 (riveted threshold)
- **read back as:** 1 sector(s) of type 600, worked by a push
- **covers:** bloodmap.aperture.framed_door
- **room:** 33280 clear (1.96 player heights), 5120 x 6144
- **sector:** 58

![DRESSED DOORWAY](projects/pattern-zoo/reports/tour/observation/frames/dressed_doorway.png)

### 14. CRATE STACK

crates as what they are: sector volumes wearing crate art.

- **try:** walk round them and climb one; they are geometry
- **from:** templates.SMALL_CRATE and LARGE_CRATE -- 452 at a 1024 module, 95 at 2048. v1 made these sprites. 459 is a moss-grown rock, not a crate
- **hand-composed dressing:** a stockroom around the crates -- promotion candidate
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 64

![CRATE STACK](projects/pattern-zoo/reports/tour/observation/frames/crate_stack.png)

### 15. SHELF RUN

a shelf as a shallow sector wearing the shelf texture.

- **try:** look along it; the depth is geometry, not a sprite
- **from:** owner anchor 2026 (wall shelf, strong binding); the E6M1 shop kit. v1 hung this on a wall as one sprite
- **hand-composed dressing:** a shop room around the shelf run -- promotion candidate
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 70

![SHELF RUN](projects/pattern-zoo/reports/tour/observation/frames/shelf_run.png)

### 16. PARK CORNER

grass and dirt with trees standing on the ground.

- **try:** check the trees meet the grass and do not float
- **from:** furniture.furnish, which knows each tile's campaign height; owner anchors 361 (grass, strong) and 270
- **hand-composed dressing:** outdoor ground cover beyond one grass and one dirt sector -- promotion candidate
- **room:** 66560 clear (3.92 player heights), 6144 x 6144
- **sector:** 73

![PARK CORNER](projects/pattern-zoo/reports/tour/observation/frames/park_corner.png)

### 17. COUNTER

a shop counter, to the campaign's own five-clause rule.

- **try:** try to reach the working side from the front; the clearance is measured, not decorative
- **from:** reports/blood-assembly-counters.json, 384 mined bundles: waist-band rise 4096-8192, aspect >= 2, props on top, one host neighbour, asymmetric access. E1M1 sector 80 is the worked example
- **hand-composed dressing:** the shop around the counter: shelf-tiled walls and three props, assembled here rather than by a constructor that owns shops -- promotion candidate
- **room:** 33280 clear (1.96 player heights), 5120 x 6144
- **sector:** 77

![COUNTER](projects/pattern-zoo/reports/tour/observation/frames/counter.png)

### 18. SEWER WALL

the sewer kit as a wet service passage you duck along.

- **try:** follow the pipe run and find the seam where the technical door face starts it
- **from:** reports/anchor-sewer-kit.json, mined by role: pipe walls 496-499, door 500, light 501, grate 502
- **hand-composed dressing:** the passage itself: four pipe sectors chained by hand, because no constructor owns a service run -- promotion candidate
- **room:** 33280 clear (1.96 player heights), 5120 x 8192
- **sector:** 81

![SEWER WALL](projects/pattern-zoo/reports/tour/observation/frames/sewer_wall.png)

### 19. TILE MUSEUM

the owner's strong-binding tiles, each on its own panel.

- **try:** read the panels and correct any tile that is wrong
- **from:** knowledge/blood/design/owner-anchors-v1.json, the 15 tiles graded strong
- **hand-composed dressing:** panel bays with their own lighting -- promotion candidate
- **room:** 33280 clear (1.96 player heights), 7168 x 4096
- **sector:** 88

![TILE MUSEUM](projects/pattern-zoo/reports/tour/observation/frames/tile_museum.png)

### 20. SPRITE BRIDGE  *(EMPTY)*

composing solid flat sprites into a walkable volume.

- **try:** nothing yet; this stall is the gap itself
- **from:** owner-named gap, 2026-09-01: the sprite-bridge technique has no constructor in the repository
- **blocked by:** NO CONSTRUCTOR OWNS THIS YET
- **room:** 33280 clear (1.96 player heights), 5120 x 5120
- **sector:** 96

![SPRITE BRIDGE](projects/pattern-zoo/reports/tour/observation/frames/sprite_bridge.png)

### 21. STACK LINK  *(EMPTY)*

room over room: two floors standing in one place.

- **try:** nothing yet; see the casket for the other ROR exhibit
- **from:** reachability.link_pairs; the owner's ROR visibility budget -- two volumes must not be in view at once
- **blocked by:** NEEDS A SECOND ROR VOLUME
- **room-over-room:** placed clear of the other ROR exhibit, so no two ROR volumes are in view at once
- **room:** 33280 clear (1.96 player heights), 6144 x 5120
- **sector:** 98

![STACK LINK](projects/pattern-zoo/reports/tour/observation/frames/stack_link.png)

## Limitations

- The map is generated evidence of nothing. It shows what the
  constructors build; it is never mined and never scored against the
  corpus.
- **CASKET** shows the z half of E1M1's casket. The full one is slide,
  stack link and z at once, and no single constructor reaches that.
- **SPRITE BRIDGE** and **STACK LINK** are EMPTY stalls with their gaps
  lettered on the wall. An honest gap is an exhibit too.
- The self-read checks that each claimed mechanism *exists and is wired*
  as claimed. It cannot check that a body fits through one; only you
  walking it can, which is what the tour is for.
- The frames are what the *editor* renderer paints with local game data,
  not what the game looks like in motion. Mechanisms are shown at rest.
