# Pattern Zoo — the tour sheet

Every pattern, mechanism and constructor the pipeline has learned, one
labelled exhibit each, in the order you walk them. Pre-screen here, then
play the map and send corrections **by label** — the labels are stable
identities and a rename loses the thread of corrections attached to one.

```text
map            projects/pattern-zoo/level/pattern-zoo.MAP
built from     projects/pattern-zoo/registry.py (generated, never hand-placed)
size           79 sectors, 424 walls, 255 sprites
exhibits       24, of which 1 are honest EMPTY stalls
```

## Verification

```text
structural validation   0 errors, 0 warnings
round trip              byte-exact
geometry audit          9 zero_exit_gameplay_sector, every one a shut door
                        leaf or the room it hides -- declared in the source
                        and the point of the exhibit
NBlood load/spawn       **pass** — no fatal indicators; the map loads and the player spawns
observer                24 stalls rendered, 0 refused
```

## What to try first

1. **TURNSTILE PAIR** — walk into it. Passage through a rotating door is
   the pipeline's longest-standing unproven claim; ten seconds of you
   walking settles it.
2. **CRATE STACK** — check these are crates. A build once shipped tile
   459, a moss-grown rock, as a crate.
3. **TILE MUSEUM** — read the names on the owner-anchor tiles and correct
   any that are wrong.

## The exhibits

### 1. PUSH DOOR

a z-motion door opened by pushing its own wall.

- **try:** walk up to it and press use on the door face
- **from:** doors.z_motion_door; reports/blood-door-families.md
- **covers:** bloodmap.doors.z_motion_door, bloodmap.doors.xsector_direct_use
- **sector:** 2

![PUSH DOOR](projects/pattern-zoo/reports/tour/observation/frames/sector_2.png)

### 2. SWITCHED DOOR

the same door, worked from a switch across the stall.

- **try:** press the switch on the side wall, not the door
- **from:** doors.xsector_remote_rx; reports/blood-effects-switches.md
- **covers:** bloodmap.doors.xsector_remote_rx
- **sector:** 6

![SWITCHED DOOR](projects/pattern-zoo/reports/tour/observation/frames/sector_6.png)

### 3. KEYED DOOR

a door with a key emblem; the key lies in the stall.

- **try:** try the door first, then take the key and try again
- **from:** doors.KEY_TYPES + knowledge/blood/design/keys-v1.json; E1M4 sector 295 wears the moon emblem
- **covers:** bloodmap.doors.z_motion_endpoints
- **sector:** 10

![KEYED DOOR](projects/pattern-zoo/reports/tour/observation/frames/sector_10.png)

### 4. LIFT

a floor that carries a body between two standing levels.

- **try:** ride it up, then step off and look down
- **from:** reports/blood-effects-motion.md; E1M3 sector 241
- **sector:** 14

![LIFT](projects/pattern-zoo/reports/tour/observation/frames/sector_14.png)

### 5. CRACK BARRIER

a wall that opens once, when shot, and never closes.

- **try:** shoot the crack; the way behind it stays open
- **from:** reports/blood-conditional-topology.md; E1M4 sprite 373 on channel 119
- **sector:** 18

![CRACK BARRIER](projects/pattern-zoo/reports/tour/observation/frames/sector_18.png)

### 6. TURNSTILE PAIR

two counter-rotating four-vane rotors, E1M4's spin rate.

- **try:** WALK THROUGH IT. this settles the parked passage question
- **from:** mechanism.turnstile_pair; reports/blood-rotating-doors.md; passage unproven -- reports/blood-passage-oracle.md
- **covers:** bloodmap.mechanism.turnstile_pair
- **sector:** 22

![TURNSTILE PAIR](projects/pattern-zoo/reports/tour/observation/frames/sector_22.png)

### 7. TURNSTILE SAME WAY

the DNE3L6 variant: both rotors turning the same way.

- **try:** walk through and compare with the pair next door
- **from:** reports/blood-rotating-doors.md; DNE3L6 sectors 3 and 11
- **covers:** bloodmap.mechanism.turnstile
- **sector:** 26

![TURNSTILE SAME WAY](projects/pattern-zoo/reports/tour/observation/frames/sector_26.png)

### 8. SLIDING GATE

a gate that slides rather than turning.

- **try:** watch which way it goes and try to follow it
- **from:** mechanism.sliding_gate
- **covers:** bloodmap.mechanism.sliding_gate
- **sector:** 30

![SLIDING GATE](projects/pattern-zoo/reports/tour/observation/frames/sector_30.png)

### 9. CASKET

the player start as a mechanism: slide, stack link and z at once.

- **try:** look up, then walk out; this is E1M1's opening shot
- **from:** owner-attested E1M1 reading, sectors 30 and 28, stack link 10; roadmap Phase 8 note
- **room-over-room:** placed clear of the other ROR exhibit, so no two ROR volumes are in view at once
- **sector:** 33

![CASKET](projects/pattern-zoo/reports/tour/observation/frames/sector_33.png)

### 10. DOUBLE SLIDE DOOR

one sector carrying both leaves, parting in opposite directions.

- **try:** stand in the middle and watch both halves go
- **from:** owner-attested E1M1 reading, sector 4
- **sector:** 36

![DOUBLE SLIDE DOOR](projects/pattern-zoo/reports/tour/observation/frames/sector_36.png)

### 11. DOUBLE ROTATE DOOR

two rotating leaves chained by channel, one firing the next.

- **try:** press once and watch the second leaf follow
- **from:** owner-attested E1M1 reading, sectors 50 and 51 (rx 105 -> tx 106 -> rx 106)
- **sector:** 39

![DOUBLE ROTATE DOOR](projects/pattern-zoo/reports/tour/observation/frames/sector_39.png)

### 12. CURTAIN

a slide used as furnishing rather than as a way through.

- **try:** open it; nothing beyond it was closed off
- **from:** owner-attested E1M1 reading, sector 125. Its tile has no owner binding, which is why the dressing plane cannot name it -- reports/blood-role-v2.md
- **sector:** 43

![CURTAIN](projects/pattern-zoo/reports/tour/observation/frames/sector_43.png)

### 13. SHELF SECRET

a shelf that slides aside and is a secret entrance.

- **try:** find what opens it, then look behind the shelf
- **from:** owner-attested E1M1 reading, sector 70
- **sector:** 46

![SHELF SECRET](projects/pattern-zoo/reports/tour/observation/frames/sector_46.png)

### 14. STACK LINK  *(EMPTY)*

room over room: two floors in one place.

- **try:** walk the lower floor, then the upper, and look down
- **from:** reachability.link_pairs; owner note on the ROR visibility budget -- two volumes must not be in view at once
- **blocked by:** NEEDS A SECOND ROR VOLUME OUT OF SIGHT OF THE CASKET
- **room-over-room:** placed clear of the other ROR exhibit, so no two ROR volumes are in view at once
- **sector:** 50

![STACK LINK](projects/pattern-zoo/reports/tour/observation/frames/sector_50.png)

### 15. FACADE NARROW

a street frontage at its narrow width, with its lettered sign.

- **try:** stand back in the corridor and read the sign
- **from:** aperture.facade_run; reports/blood-facade-build.md
- **covers:** bloodmap.aperture.facade_run
- **sector:** 52

![FACADE NARROW](projects/pattern-zoo/reports/tour/observation/frames/sector_52.png)

### 16. FACADE WIDE

the same grammar at the wide width.

- **try:** compare the bay rhythm with the narrow one
- **from:** aperture.facade_run; reports/blood-facade-grammar.md
- **sector:** 55

![FACADE WIDE](projects/pattern-zoo/reports/tour/observation/frames/sector_55.png)

### 17. DRESSED DOORWAY

a doorway wearing jamb rail and threshold.

- **try:** look down at the threshold and along the jambs
- **from:** owner anchors 195 (metal rail) and 200 (threshold); reports/blood-facade-grammar.md
- **sector:** 58

![DRESSED DOORWAY](projects/pattern-zoo/reports/tour/observation/frames/sector_58.png)

### 18. COUNTER

a counter with the working clearance behind it.

- **try:** try to stand behind the counter; the gap is measured
- **from:** reports/blood-assembly-counters.json
- **sector:** 61

![COUNTER](projects/pattern-zoo/reports/tour/observation/frames/sector_61.png)

### 19. CRATE STACK

crates built from the owner's tiles: intact, broken, large.

- **try:** check these are crates and not mossy rocks
- **from:** owner anchors 452 / 462 / 95; a build once shipped tile 459, a moss-grown rock, as a crate
- **sector:** 65

![CRATE STACK](projects/pattern-zoo/reports/tour/observation/frames/sector_65.png)

### 20. SHELF RUN

a run of wall shelves, the owner's strong-binding tile.

- **try:** look along the run; the tile is 2026
- **from:** owner anchor 2026 (wall shelf, strong binding)
- **sector:** 67

![SHELF RUN](projects/pattern-zoo/reports/tour/observation/frames/sector_67.png)

### 21. MANNEQUIN ROW

three mannequins in a display row.

- **try:** the tile binds its meaning almost always -- does it here
- **from:** owner anchor 2377 (mannequin, strong binding); reports/blood-contrast-shelf-vs-crate.json
- **sector:** 69

![MANNEQUIN ROW](projects/pattern-zoo/reports/tour/observation/frames/sector_69.png)

### 22. PARK CORNER

grass and dirt with trees.

- **try:** walk the grass and look at where it meets the dirt
- **from:** owner anchors 361 (grass, strong) and 270 (dirt); furniture.py park vocabulary
- **sector:** 71

![PARK CORNER](projects/pattern-zoo/reports/tour/observation/frames/sector_71.png)

### 23. SEWER WALL

the sewer kit: pipe walls and a technical door.

- **try:** look for the seam between the pipe run and the door
- **from:** reports/anchor-sewer-kit.json; owner anchors 496-502
- **sector:** 75

![SEWER WALL](projects/pattern-zoo/reports/tour/observation/frames/sector_75.png)

### 24. TILE MUSEUM

the owner's strong-binding tiles, each with its name.

- **try:** read the names and correct any that are wrong
- **from:** knowledge/blood/design/owner-anchors-v1.json, binding strong
- **sector:** 78

![TILE MUSEUM](projects/pattern-zoo/reports/tour/observation/frames/sector_78.png)

## Limitations

- The map is generated evidence of nothing. It shows what the
  constructors build; it is never mined and never scored against the
  corpus.
- **CASKET** shows the z half of E1M1's casket. The full one is slide,
  stack link and z at once, and no single constructor reaches that.
- **STACK LINK** is an EMPTY stall: a second room-over-room volume has
  to sit out of sight of the casket, and placing it is v2 work.
- Three aperture constructors (`pierce`, `framed_door`, `frame_z_doors`)
  and two vocabulary ones (`staircase`, `recess`) are skipped with
  PENDING reasons and deserve stalls in v2.
- The frames are what the *editor* renderer paints with local game data,
  not what the game looks like in motion. Mechanisms are shown at rest.
