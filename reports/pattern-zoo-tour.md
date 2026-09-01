# Pattern Zoo -- the tour sheet

Every pattern, mechanism and constructor the pipeline has learned, one
labelled exhibit each, grouped into the environments they belong to.
Pre-screen here, then play the map and send corrections **by label** --
the labels are stable identities and a rename loses the thread of
corrections attached to one.

**v3.** Two rejections shaped this. v1 failed because *nothing worked*:
every door was a hand-written XSECTOR dict on a type-0 sector, which the
engine ignores, and it passed validation, round trip, load smoke and
twenty-four renders anyway. v2 fixed the mechanisms and failed on shape:
a corridor of one-exhibit cells is not a gallery, and a mechanism in a
generic box says nothing about how it is used.

So the zoo is now a spine that branches into **sections**, and a section
is one environment holding the exhibits that belong together in it. The
SHOP is E6M1's shop re-expressed through our own constructors. Inside a
section each exhibit has a **bay**, and a **pier** of solid wall beside
it carrying its name -- the label cannot go on the bay's own wall,
because an exhibit is entitled to open all of it.

The acceptance gate is that **the zoo reads itself**: the map is read
back with `bloodmap.effects` and `bloodmap.conditional` -- the same code
that reads the campaign -- and every claim below is checked against what
that reading finds. A dead map fails the build.

```text
map            projects/pattern-zoo/level/pattern-zoo.MAP
built from     projects/pattern-zoo/registry.py (generated, never hand-placed)
size           92 sectors, 504 walls, 557 sprites
sections       7
exhibits       31, of which 1 are honest EMPTY
live sectors   6 x type 600, 7 x type 614, 6 x type 615
```

## Verification

```text
the zoo reads itself    25 claims checked, 0 unsupported
  representation          tiles claimed as wall texture are on walls and
                          not thrown as sprites, and the reverse
  the transparency law    no mask-carrying tile on any floor or ceiling
  seating                 nothing the builder seated on a floor is off it
  lettering               every exhibit has its label sprites
  reachability            every section reachable from the start
structural validation   0 errors, 0 warnings
round trip              byte-exact
geometry audit          11 zero_exit_gameplay_sector, every one a shut
                        door leaf or the room it hides -- declared in
                        the source and the point of the exhibit
NBlood load/spawn       **pass** -- the map loads and the player spawns
observer                31 exhibits rendered, 0 refused
```

## What to try first

1. **PUSH DOOR** (doors and mechanisms) -- open it. In v1 this did
   nothing at all. If it rises, the other five type-600 sectors are
   built the same way and the whole v1 failure class is closed.
2. **CASKET** -- the owner's own correction, built: a slide and a z
   travel conjugated on ONE sector. Check the z motion reads as the
   ergonomic lift-out and not as part of the gating.
3. **TURNSTILE PAIR** (street) -- walk into it. Whether a body passes a
   turning rotor is the pipeline's longest-standing unproven claim.
4. **SHOP** as a whole -- the section is the claim. Does it read as a
   shop, or as four exhibits in a room?
5. **STRONG BINDING** (tile museum) -- read the owner's own names back
   off the panels and correct any that are wrong.

## DOORS AND MECHANISMS

the gallery: the z-motion door family, a lift, a shot-open breach, and the E1M1 blueprints the owner attested.

- **room:** 33280 clear (1.96 player heights)
- **hand-composed:** the gallery hall itself: a plain ashlar room, because no constructor owns a gallery

### PUSH DOOR

a z-motion door used from the room outside it.

- **try:** press use on the door face; it should rise
- **from:** doors.z_motion_door(interaction='direct'). It sets Push AND Wallpush together and says why: a shut z-door has zero height, so the player stands in the hall and Wallpush is what fires
- **read back as:** 1 sector(s) of type 600, read as a changes what fits through, worked by a push
- **covers:** bloodmap.doors.z_motion_door, bloodmap.doors.xsector_direct_use

![PUSH DOOR](projects/pattern-zoo/reports/tour/observation/frames/push_door.png)

### SWITCHED DOOR

the same motion, worked from a switch across the room.

- **try:** press the switch on the side wall, not the door
- **from:** doors.z_motion_door(interaction='remote') and xsector_remote_rx; reports/blood-effects-switches.md
- **read back as:** 1 sector(s) of type 600, read as a changes what fits through, worked by a switch, listening on channel 300
- **covers:** bloodmap.doors.xsector_remote_rx

![SWITCHED DOOR](projects/pattern-zoo/reports/tour/observation/frames/switched_door.png)

### KEYED DOOR

a door that wants the moon key, which lies in the room.

- **try:** try the door, then take the key and try again
- **from:** doors.z_motion_door(key=6); E1M4 sector 295 wears the moon emblem; knowledge/blood/design/keys-v1.json
- **read back as:** 1 sector(s) of type 600, read as a changes what fits through, requiring key 6

![KEYED DOOR](projects/pattern-zoo/reports/tour/observation/frames/keyed_door.png)

### LIFT

a floor that carries a body between two storeys, with a landing worth arriving at.

- **try:** ride it up, step off, and look back down
- **from:** reports/blood-effects-motion.md; E1M3 sector 241, whose floor endpoints are exactly its neighbours'
- **read back as:** 1 sector(s) of type 600, read as a carries a body between levels
- **hand-composed:** the mechanism itself: a floor-travelling z-motion. doors.z_motion_door writes CEILING endpoints only, so no constructor owns a lift; the upper room that makes the ride worth taking -- promotion candidate

![LIFT](projects/pattern-zoo/reports/tour/observation/frames/lift.png)

### CRACK BARRIER

a breach in a load-bearing wall, opened once by shooting it.

- **try:** shoot the crack; it opens once and stays open
- **from:** E1M4 sectors 276 and 277, flush at rest; kThingWallCrack transmits once
- **read back as:** 1 sector(s) of type 600, worked by a shot, listening on channel 301, one-way
- **hand-composed:** the load-bearing wall the breach interrupts is plain masonry; no constructor owns a damaged-wall habitat -- promotion candidate

![CRACK BARRIER](projects/pattern-zoo/reports/tour/observation/frames/crack.png)

### CASKET

a lid that slides aside by MOVING THE BOUNDARY between hole and cover, over a room-over-room link, breathing light as it goes.

- **try:** look up, then walk out; E1M1 opens inside one
- **from:** owner-attested E1M1 reading, sectors 28/30 (hole, slide-marked, ROR-linked) and 27/29 (cover). Each slide sector moves exactly ONE flagged wall, and that wall is the hole/cover boundary
- **read back as:** 1 sector(s) of type 614, listening on channel 309, whose payload is 'boundary re-partition', stack-linked across a room-over-room plane
- **hand-composed:** the SECOND pair: E1M1's casket is four sectors, and this is one pair plus its link. Building both, synced on one channel with the same travel on each side of the plane, is the next step -- promotion candidate
- **covers:** bloodmap.mechanism.planar_door, bloodmap.mechanism.shade_wave

![CASKET](projects/pattern-zoo/reports/tour/observation/frames/casket.png)

### DOUBLE SLIDE DOOR

one sector, two leaves parting along their own line.

- **try:** push it and watch where the leaves go
- **from:** owner-attested E1M1 sector 4; mechanism.sliding_gate built to the campaign template
- **read back as:** 1 sector(s) of type 614
- **covers:** bloodmap.mechanism.sliding_gate

![DOUBLE SLIDE DOOR](projects/pattern-zoo/reports/tour/observation/frames/double_slide.png)

### PLAIN SLIDE DOOR

a single leaf sliding aside, the load-bearing kind.

- **try:** open it and step through; nothing is dressed up
- **from:** owner-attested E1M1 sector 63. Its two portals are 512 apart on the SAME side, which is why the cheap blocking test almost never fires
- **read back as:** 1 sector(s) of type 614

![PLAIN SLIDE DOOR](projects/pattern-zoo/reports/tour/observation/frames/plain_slide.png)

### DOUBLE ROTATING DOOR

two rotating leaves chained on one channel.

- **try:** work one leaf; the other answers on the chain
- **from:** owner-attested E1M1 sectors 50 and 51: s50 transmits to s51, which is a sentence in the control-bus grammar, not two doors
- **read back as:** 2 sector(s) of type 615
- **covers:** bloodmap.mechanism.turnstile

![DOUBLE ROTATING DOOR](projects/pattern-zoo/reports/tour/observation/frames/rotating_door.png)

### SHELF SECRET

a shelf that slides aside and is the way into a secret.

- **try:** find what opens it, then step behind the shelf
- **from:** owner-attested E1M1 sector 70; the secret sector transmits on channel 2, kChannelSecretFound
- **read back as:** 1 sector(s) of type 614, listening on channel 304

![SHELF SECRET](projects/pattern-zoo/reports/tour/observation/frames/shelf_secret.png)

### CURTAIN

a thin sector whose own LENGTH changes -- the texture squashing IS the animation.

- **try:** open it and watch the fabric gather: the sector resizes, it does not slide aside
- **from:** owner anchor 146/147, binding strong, and the owner's note with them: a Blood curtain is a thin deforming sector, not a pair of leaves
- **read back as:** 1 sector(s) of type 614, listening on channel 303, whose payload is 'the sector resizes itself', tiles 146 worn as wall texture, not thrown as sprites
- **covers:** bloodmap.mechanism.curtain

![CURTAIN](projects/pattern-zoo/reports/tour/observation/frames/curtain.png)

## FURNITURE HALL

one hall of the furniture kinds the pipeline can place, each seated the way that thing is actually mounted.

- **room:** 40704 clear (2.40 player heights)
- **hand-composed:** the hall itself; and the table volumes, which are raised sectors assembled here because templates.py's table lives on the levelprog stack and cannot be called from a PlanarLayout

### LIGHT FITTINGS

the four light kinds, each on the surface it hangs from.

- **try:** look up: the chandelier and lantern hang, the torch and sconce are on the wall
- **from:** furniture.py, whose mounting field is mined from the campaign: a torch is drawn fullbright in 89% of its 150 uses because it is on fire
- **read back as:** tiles 506/510/641/1701 placed as sprites
- **covers:** bloodmap.furniture.furnish, bloodmap.furniture.place, bloodmap.furniture.mounting_for

![LIGHT FITTINGS](projects/pattern-zoo/reports/tour/observation/frames/lights.png)

### WALL FITTINGS

plaque, plank and ceiling plate: mounted things that are not lights.

- **try:** the ceiling plate is floor-aligned and lies flat; it cannot hang on a wall and furniture.py refuses to try
- **from:** furniture.py mounting rules; the alignment state is a property of the tile, not of the caller
- **read back as:** tiles 68/795/915 placed as sprites

![WALL FITTINGS](projects/pattern-zoo/reports/tour/observation/frames/wall_fittings.png)

### TABLES

tables as raised sector volumes at the campaign rise, not as sprites.

- **try:** walk up to one: it is geometry, and you can stand on it
- **from:** projects/blood-city/level/templates.py TABLE_RISE = 0.30 player heights, TABLE_SIDE 1024

![TABLES](projects/pattern-zoo/reports/tour/observation/frames/tables.png)

### GRAVEYARD

the headstone and tomb set, seated on their own campaign heights.

- **try:** check nothing floats and nothing is buried
- **from:** furniture.py graveyard entries; every height is the mined campaign median for that tile
- **read back as:** tiles 701/703/704/706 placed as sprites

![GRAVEYARD](projects/pattern-zoo/reports/tour/observation/frames/graveyard.png)

### SPRITE BRIDGE  *(EMPTY)*

composing flat sprites into a solid volume you can walk across.

- **try:** nothing yet: this is the technique we do not have, lettered where it would stand
- **from:** owner-named gap. Flat floor-aligned sprites composed into a walkable volume is a technique the pipeline cannot express
- **lettered on the wall:** NO CONSTRUCTOR OWNS THIS YET

![SPRITE BRIDGE](projects/pattern-zoo/reports/tour/observation/frames/sprite_bridge.png)

## SHOP

E6M1's shop re-expressed through our constructors: counter, shelf runs, crate stock and a display row.

- **room:** 33280 clear (1.96 player heights)
- **hand-composed:** the shop room itself: worn facade tile 202 on the walls, which is a material choice and not a constructor

### REGISTER

a counter with the working clearance behind it.

- **try:** try to reach the working side from the front; the clearance is measured, not decorative
- **from:** reports/blood-assembly-counters.json, 384 mined bundles: waist-band rise 4096-8192, aspect at least 2, props on top, asymmetric access. E1M1 sector 80 is the worked example

![REGISTER](projects/pattern-zoo/reports/tour/observation/frames/register.png)

### SHELF RUNS

shelves as WALL TEXTURE on shallow sectors, in the three shop tiles.

- **try:** a shelf is not a sprite: walk along and see them as geometry
- **from:** owner anchors 2026 and 2635, both strong binding, plus 202. E6M1's shop kit
- **read back as:** tiles 2026/2635 worn as wall texture, not thrown as sprites

![SHELF RUNS](projects/pattern-zoo/reports/tour/observation/frames/shelf_runs.png)

### CRATE STACK

crates as sector VOLUMES wearing the crate modules.

- **try:** check these are crates, and that you can climb the small ones
- **from:** projects/blood-city/level/templates.py SMALL_CRATE (452, 1024 side, 16384 rise) and LARGE_CRATE (95, 2048, 32768). 459 is a moss-grown rock and a build once shipped it as a crate
- **read back as:** tiles 452/95 worn as wall texture, not thrown as sprites
- **hand-composed:** the crate VOLUMES: the modules are imported from templates.py, but its _crate_block builds on the levelprog space stack, so the volumes themselves are assembled here on PlanarLayout; a free-standing crate in the middle of the floor is not expressible at all: PlanarLayout refuses a region wholly inside another, so these stand against a wall -- promotion candidate

![CRATE STACK](projects/pattern-zoo/reports/tour/observation/frames/crate.png)

### DISPLAY ROW

three mannequins, standing on the floor they are seated to.

- **try:** check they stand on the ground; in v1 they floated
- **from:** owner anchor 2377, binding strong. Its height is the one number here no campaign map backs: the tile has no mined median
- **read back as:** tiles 2377 placed as sprites

![DISPLAY ROW](projects/pattern-zoo/reports/tour/observation/frames/display.png)

## STREET

outdoor scale under sky: the frontage at two widths and the turnstiles that admit you to somewhere public.

- **room:** 67840 clear (4.00 player heights), open sky
- **hand-composed:** street anatomy: there is no kerb, no roadway and no gutter, because no constructor owns them and no owner anchor grades a road surface. The ground here is the gallery's own floor tile, which is the honest placeholder rather than a guess

### FACADE NARROW

a six-bay frontage with two openings and a sign.

- **try:** stand back and read it; then compare it with the wide one
- **from:** reports/blood-facade-build.md: one wall tile across the run in 98% of 131 campaign multi-opening facades; bay 1024; reveal 256
- **covers:** bloodmap.aperture.facade_run

![FACADE NARROW](projects/pattern-zoo/reports/tour/observation/frames/facade_narrow.png)

### FACADE WIDE

the same frontage at ten bays and three openings.

- **try:** every relationship should survive the width change; only the counts differ
- **from:** reports/blood-facade-build.md width invariance: header, sill, reveal and sign seat are shared datums across both widths

![FACADE WIDE](projects/pattern-zoo/reports/tour/observation/frames/facade_wide.png)

### TURNSTILE PAIR

two counter-rotating drums flanking a public way in.

- **try:** walk into it. Whether a body passes a turning rotor is the pipeline's longest unproven claim
- **from:** reports/blood-turnstile-build.md; E1M4's carnival entry at period 255, four blades on tile 332, each spanning its rotor exactly
- **read back as:** 2 sector(s) of type 615
- **covers:** bloodmap.mechanism.turnstile_pair

![TURNSTILE PAIR](projects/pattern-zoo/reports/tour/observation/frames/turnstile_pair.png)

### TURNSTILE SAME WAY

the same pair turning the same way, the DNE3L6 variant.

- **try:** compare the two: counter-rotating is E1M4's, same-way is the community precedent
- **from:** reports/blood-turnstile-build.md; the community variant is precedent, never convention
- **read back as:** 2 sector(s) of type 615

![TURNSTILE SAME WAY](projects/pattern-zoo/reports/tour/observation/frames/turnstile_same.png)

## SEWER AND TECH

a wet service passage: the sewer kit by the role each tile was mined under.

- **room:** 33280 clear (1.96 player heights)

### PIPE RUN

a passage you duck along, four pipe tiles down it.

- **try:** the clear height is deliberately below the campaign median; that is what a service run is
- **from:** reports/anchor-sewer-kit.json, role pipe_walls: tiles 496 to 499
- **read back as:** tiles 496/497/498/499 worn as wall texture, not thrown as sprites
- **hand-composed:** the passage: four pipe sectors chained by hand, because no constructor owns a service run -- promotion candidate
- **covers:** bloodmap.aperture.maskwall_panel

![PIPE RUN](projects/pattern-zoo/reports/tour/observation/frames/sewer.png)

### SEWER DOOR

the technical door face, on a working z-motion door.

- **try:** open it; the face is tile 500 and the mechanism is the same one the stone doors use
- **from:** reports/anchor-sewer-kit.json role sewer_door: tile 500. The mechanism is doors.z_motion_door
- **read back as:** 1 sector(s) of type 600, worked by a push

![SEWER DOOR](projects/pattern-zoo/reports/tour/observation/frames/sewer_door.png)

### SLIDING GATE

two leaves parting into the jambs, serving the passage.

- **try:** press it and watch where the leaves go; they rest shut and are drawn open
- **from:** mechanism.sliding_gate. A gate is authored in its OPEN pose and rests shut, which is what both campaign two-leaf gates do
- **read back as:** 1 sector(s) of type 614, listening on channel 302

![SLIDING GATE](projects/pattern-zoo/reports/tour/observation/frames/sliding_gate.png)

## PARK

outdoors under sky: the ground vocabulary and the things that grow in it.

- **room:** 67840 clear (4.00 player heights), open sky

### GROUND

grass and dirt, the two-tile ground vocabulary.

- **try:** the seam between them is where a path would go
- **from:** owner anchor 361 (grass, strong: dominant floor of E1M1's open-sky sectors, 35 of 66 uses under sky) with 270 dirt
- **read back as:** tiles 361/270 worn as wall texture, not thrown as sprites
- **hand-composed:** ground cover beyond two sectors: no constructor owns a path or a planted bed -- promotion candidate

![GROUND](projects/pattern-zoo/reports/tour/observation/frames/ground.png)

### TREES

the four tree kinds, each at its own campaign height.

- **try:** an oak is 2.82 player heights and a pine is not; check they differ
- **from:** furniture.py growing things; every height is the mined campaign median for that tile
- **read back as:** tiles 541/542/543/547 placed as sprites

![TREES](projects/pattern-zoo/reports/tour/observation/frames/trees.png)

### STRAW

a heap of straw, at the height the campaign draws it.

- **try:** 0.97 player heights: a heap you walk round, not a scatter underfoot
- **from:** tile 515, owner-named in the zoo specification. Campaign median height 0.97; the anchor file grades it untested, so the name here is the owner's and not ours
- **read back as:** tiles 515 placed as sprites

![STRAW](projects/pattern-zoo/reports/tour/observation/frames/straw.png)

## TILE MUSEUM

a gallery wall of the owner's anchor tiles, each lettered with the owner's own name for it.

- **room:** 33280 clear (1.96 player heights)
- **hand-composed:** the panel bays: shallow sectors wearing one tile each, with no lighting of their own

### STRONG BINDING

the tiles the owner graded strong: these may name what they depict.

- **try:** read the names and correct any that are wrong
- **from:** knowledge/blood/design/owner-anchors-v1.json, binding strong. Weak and untested tiles never name -- that rule is executable in owner_anchors.may_name
- **covers:** bloodmap.owner_anchors.load_owner_anchors, bloodmap.owner_anchors.owner_label

![STRONG BINDING](projects/pattern-zoo/reports/tour/observation/frames/museum.png)

## Limitations

- The map is generated evidence of nothing. It shows what the
  constructors build; it is never mined and never scored against the
  corpus.
- **There is no room-over-room anywhere in the zoo**, so the ROR
  visibility budget is not exercised. `PlanarLayout` has no stack link
  at all, which is why the CASKET is the slide-plus-z half of E1M1's
  and not the four-sector construct.
- The self-read checks that each claimed mechanism *exists and is wired*
  as claimed. It cannot check that a body fits through one; only you
  walking it can, which is what the tour is for.
- The frames are what the *editor* renderer paints with local game data,
  not what the game looks like in motion. Mechanisms are shown at rest.
