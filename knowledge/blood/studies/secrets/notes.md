# Secrets: how Blood hides a place and gives it away

Data: `secrets.json` here, written by `python -m tools.mine_secrets` (two
minutes); `show MAP` reads one map, `record MAP s:N w:N p:N ch:N` prints every
set field of a record or channel, `buttons` and `bars` list those two idioms
over every admitted map. Supplies in secrets are in
[../supplies/notes.md](../supplies/notes.md); this is about the hiding.

## What I want to build

Ten secrets in Gravesend, no two hidden alike, each with something a careful
player can read, none holding a required item. The owner: some are "too visible
and easy to access like that voodoo doll"; he asked for bars opened by a wheel
(tile 982), and for the button with bloody hands that "goes back a little when
pressed".

## Where Blood built it

Campaign 236 secrets in 43 maps; Death Wish 171. The way read is the walk's
shortest from the secret back to ordinary ground. Campaign first, DW in brackets.

### The gate

| what stands before it | campaign | DW |
| --- | --- | --- |
| nothing: out of the way, round a corner | 55 | 58 |
| nothing: a jump, leap or climb | 22 | 16 |
| nothing: a crawl | 9 | 8 |
| nothing: under water, a water link, a teleporter | 6 | 19 |
| a wall that rises (600; includes ordinary doors the reader cannot tell apart) | 55 | 27 |
| a block that sinks (600) | 24 | 14 |
| a lift or moving floor | 20 | 6 |
| a panel that slides (614/616) | 14 | 4 |
| a panel that turns (613/615/617) | 10 | 0 |
| a crack, blown (1127) | 10 | 3 |
| a pane or wall that breaks | 1 | 5 |
| nothing we read moves; a ceiling; a path | 10 | 11 |

### What opens it

| | campaign | DW |
| --- | --- | --- |
| nothing | 92 | 101 |
| the panel itself, pushed | 72 | 21 |
| a switch sprite elsewhere (1046 x5, 1070 x4, 1074 x3; tile 0 unseen on a drawn thing x7 with the props below) | 19 | 16 |
| a prop pushed: handsaw 1714, hand print 904, warning sign 744, poster 930, gravestone 706, wall trim 68 | 9 | - |
| a step somewhere | 9 | 2 |
| a blast (crack or barrel) | 13 | 3 |
| a shot: extinguisher 658, hanged man 1727, eye banner 637, button 1046, mask 226 | 7 | 3 |
| a pickup | 2 | 3 |
| the rest credit themselves when pushed or shot | 13 | - |

**Away and in sight.** Of 57 campaign triggers that are not on the gate, the
distance to it is 608 / **2,944** / 5,780 (quartiles) and the gate is in sight
of the trigger for 32. A mapper lets you see what you did a little more than
half the time.

### The face: the rule of the tell

| the panel against the wall beside it | it is its own button (70) | worked from elsewhere (54) |
| --- | --- | --- |
| another tile | **32** | 15 |
| same tile, another palette / shade / broken pattern | 9 | 5 |
| same tile, in its own bay | 21 | 9 |
| identical | 7 | **25** |

A wall you push shows you that it is the one; a wall worked from elsewhere is
invisible and its BUTTON is the tell. DW keeps the first half harder: 13 of 18
own-button panels wear another tile, 1 another colour, none is identical. The quietest tell is the palette: E1M1 s6
(329), E1M5 s185 (366), E3M3 s290 (499), E3M8 s437 (80), E4M4 s244 (22), E6M9
s98 (110) are the wall's own tile in another `pal`.

### The window

108 of 212 secrets with something in them can be seen from ordinary ground, but
of the 123 behind a moving gate only 33. Seen THROUGH something and
not reachable is rare: 5 campaign, 6 DW. The best is **E3M8 sector 490**.

## What makes it read as that

Frames in `work/secrets/look/` (commercial renders, not committed).

* **The wheel, E3M3 sprites 107 and 108** (`shots1.png`): two red wheels on
  bright round plates (shade -8 in a room at 28), red and silver against grey
  iron. The second, turned THREE times (counter sprite 111, data_2 3), opens a
  closet across the water behind you for six seconds (s299, wait 60). Wall and
  closet wear tile 492, identical; the wiki's hint is "keep looking behind you".
* **The hands, E1M2 sector 261** (`E1M2-209/pairs.png`, `shots1.png`): a pale
  slab (2453) in the dark iron wall (379) of a freezer, two red hands (904) on
  it, zombies standing in front. Pushed, it goes in 64 with a click and comes
  back; a wine rack slides 1,920 in another room (828 away, not in sight).
* **The bars you see a prize through, E3M8 walls 265/272** (`shots3.png`): a
  window of bars (58) with monks and a napalm launcher behind. The way in is a
  panel under a missing painting (s484), open four seconds, its switch (258,
  1074) behind a blown crack 2,944 away.
* **The cell, DWE2M4 sectors 877/876** (`shots1.png`): an arch, fixed bars (331)
  each side and a barred gate (332) between, hay and zombies and gasoline
  behind. The switch is a gargoyle's face (634) high on a wall 4,257 away.
* **The hanged man, E1M4 sprite 311** (`shots4.png`): behind bent bars, shot, he
  opens the brick wall at your back (s374, 181 beside 181: identical).
* **The saw, E1M1 sprite 136** (`shots3.png`): one of three tools on a wall, the
  only one that is not a breakable; it dips and the whole shelf slides.
* **The scratched crate, E1M4 wall 1281**: 462 among 452s. **The painting**,
  E3M1 s181 (716), s216 (614). **The bed**, E3M3 s264. **The bookcase**, E2M5
  s769 (31 beside 32), E1M2 s15/s18 by the cash register. **The gravestone**,
  E1M8 sprite 74. **The warning sign**, E1M4 sprite 941.

## Sizes

Travel of a pressed slab: 64 (E1M2) and 192 (TEDE1M1), in 0.2 s and 1.0 s, back
after 2 s. Slab 192 x 512 and 9,216 high, its middle at the eye. Wheel 24 x 24
repeats = 384 wide, its middle 14,336 over the floor (0.85 of a body). Bars sprite 1044 is 128 x 128 texels: 64 x 64 repeats is 2,048 wide and
32,768 high. Lift of the bars 22,528 (E3M3), 28,672 (E4M6), 2 s and 1 s.

## What I will transcribe

Every field not listed is zero.

**The wheel, E3M3 sprite 108.** type 20, tile 982, cstat 464, shade -8,
repeats 24/24, clipdist 32, 4 units off its wall. XSPRITE: tx, command 1,
trigger_on 1, trigger_off 1, trigger_push 1, dude_lockout 1, data_1 209,
data_2 209 (the turning sound, both ways). Both edges send ON, so every push is
an ON. The picture is not swapped by hand: a type-20 sprite whose state is 1 is
drawn as the next tile (view.cpp:2735), and 983 is the same wheel turned half a
spoke. It does not spin; it clicks over. `data_2 N` on a type-22 sprite
(rx the wheel, tx the gate, command 1, trigger_on 1) makes it take N turns.
Six more working wheels are in DW (DWE1M5 1, DWE1M9 1285, DWE2M1 117 and 587,
DWE2M5 339), mostly pal 6 and cstat 8592; none opens bars. Bars on a wheel is
our combination; its halves are both E3M3's.

**Bars that rise, E3M3 sector 254.** Sector type 602; XSECTOR rx,
busy_time_a 20, busy_time_b 20, off/on_ceiling_z both the ceiling's, off_floor_z
the floor's, on_floor_z the floor's less 22,528 (nothing of the sector moves:
the difference is how far the sprite goes). Sprite 198: tile 1044, type 0,
cstat 8337 (8192 goes with the floor, 128 centred, 16 on a wall, 1 blocks),
shade -8, repeats 64/64, in the middle of the sector. Sprite 126: type 709,
tile 2520, cstat 32896, shade -128, data 105, 150, 105, 150 (its sounds).
Levers 199 (other side, multiplayer) and 201: type 20, tile 1070, cstat 464, 48/48, shade
-8, command 3, both edges, push, data_1 and data_2 203. Cstat 8593 (E4M6 196/197, E3M2 545/546) also
stops shots. E4M6 317: two sprites of 56/64, 10 tenths, a skull switch (1048) beside it.

**Bars that slide, DWE2M4 sector 877.** Type 614, rx, trigger_on, trigger_off,
trigger_once, busy 10/10, markers 3 and 4 751 apart, NO wall flagged: only
sprite 1006 moves (tile 332, cstat 8593, 48/46). The fixed bars are its portal
walls, cstat 81 (64 stops shots, 16 masked, 1 blocks), over 331, both sides.

**The bloody-hands button, E1M2 sector 261.** Type 614; floor -30,720, ceiling
-39,936 (room floor about -21,500); both planes 379, shades 46 and 48, ceiling
stat 64, floor stat 12. XSECTOR: rx 160, busy_wave_a 1, busy_wave_b 1,
busy_time_a 2, busy_time_b 2, wait_time_a 20, retrigger_a 1, marker_0 359,
marker_1 360. Six walls: 1961 (-6528,25024) 379; 1962 (-6336,25024) 2453 and
1963 (-6464,25024) 2453 and 1964 (-6464,25536) 2453, all three cstat 16384; 1965
(-6336,25536) 379; 1966 (-6528,25536) the portal to the room, 2453. 1963 is the
face: shade 6, repeats 4/9, x_panning 24, y_panning 81; the rest shade 38,
repeats 1/9. Markers: 359 type 3 at (-6528,25280) in the ROOM's sector, 360 type
4 at (-6464,25280) in its own; both tile 3997, cstat 32896, status 10, owner
261. It is saved pressed and stands flush at rest. Hands 209 at (-6468,25147,
-35141) cstat 8660 (mirrored) and 312 at (-6468,25392,-33792) cstat 8656: tile
904, shade -23, 64/64, angle 1024, type 0, XSPRITE tx 160, command 1,
trigger_on, trigger_off, trigger_push, dude_lockout. **Its tx is its own
sector's rx and the gate's**: one channel moves both. Sound sprite 339: type
709, tile 2520, data 108, 200, 108, 203. The gate, s259: type 614, rx 160, busy
15, wait_time_a 40, interruptable, retrigger_a (it shuts after 4 s).

**The same with the push on the face, TEDE1M1 sector 157.** Six walls in one
tile (253), travel 192, busy 10/10, wait 20, retrigger_a. The pushed thing is
the moved wall 1140 itself (cstat 16384, XWALL tx 201, command 3, both edges,
push, dude_lockout); the hand 247 is only drawn (cstat 8400). Sound data 106, 203.

**A lever of a whole block, E6M7 sector 323** and E3M6 sector 398: 616, a
128 or 64 square, `trigger_wall_push` on the sector, its own tx, goes 512.

**A prop that dips, E1M1 sector 85**: type 602 room, off/on_floor 2,048 apart,
busy 5, wait_time_a 10, retrigger_a, rx 113 / tx 112; sprite 136 (tile 1714,
cstat 8656) tx 113. Nothing else in the room has bit 8192, so only the saw moves.

**Bars that break**: E1M4 1043/1044 (type 417, tile 465, cstat 401, 64/56,
status 4, data_1 5, data_4 314, rx), E1M8 632-634 (the same, type 416, no
wire). Bars are never a kWallGib in the campaign: it is always the sprite.

## What I will not do, and why

* No wall that is its own button and identical to its neighbours. Blood does it
  7 times in 70 and the wiki needed a walkthrough for those.
* No key, weapon of the way or exit behind one; no button without an answer in
  sight, or else a sound and a gate on ground the player passes again.
* Not two of one kind: the city has six others at a corner now.

### Our ten

| secret (sector) | hidden by now | gives | how easy | do this | from |
| --- | --- | --- | --- | --- | --- |
| stash (399) | nothing: the trunk's open end, full 2,048 mouth | voodoo doll, TNT box | in plain view | a 602 sector 256 deep in the mouth, one 1044 sprite 64/48 cstat 8593, lift 22,528; a live 982 wheel; wall 3012 keeps its width | E3M3 s254 + p108 |
| flooded room (454) | nothing; a 6,144 edge | napalm launcher, gasoline | in plain view | a sump: gun and can in a drowned pocket under its far corner | E2M7 s252, E4M2 s262 |
| Molly's nest (474) | a crawl, Molly in view | doctor's bag | easy, honest | keep the crawl; hang the ivy or wrack over its mouth | E6M6 walkthrough (vines), E3M1 s230/s250 crawls |
| Rat King's shrine (486) | nothing: a lit pipe 768 wide | death mask | in plain view | plug the pipe with its wall's own tile (600, identical); a hanged carcass on the drain, shot, lifts it | E1M4 p311 -> s374 |
| booking hall (504) | nothing: a hall one walks through | nothing | not a secret | move the credit into the booking window: bars (58) with the prize on the clerk's desk, a door behind open 4 s, a lever across the hall | E3M8 p258 -> s484, walls 265/272 |
| Demeter's locker (349) | a panel of other planks, pushed | dynamite, doctor's bag | easy | the hands button in a pale board in the hold's hull, the panel then wearing the partition's own planks; try the roof: the walk drops in from the deckhouse wall (342) | E1M2 s261 -> s259 |
| plague pit (475) | a crack | life seed | right | keep | E1M2 p675 -> s195 |
| arcade cache (307) | an extinguisher, shot | body armor, TNT | right | keep | E1M2 p489 -> s241 |
| Toshers' cache (773) | the bed that stands too high | life seed, tesla | right | keep | E3M3 s264 |
| the Cabal's heart (886) | the boss; an eye, shot | guns akimbo, super armor | earned, but credited for walking in | credit on taking the akimbo (pickup, 48 of 236), so that it is the shot eye that counts | E3M3 p324's XSPRITE |

The wheel: the sewer already hangs 982 as decoration in two niches (sprites
1318 at 37.0,5.5 and 1323 at 48.0,34.5, shade -8, type 0). Those teach that a
wheel does nothing. Dull them (shade 20, or pal 6) and give the live one shade
-8 on a bright plate, on the west wall of the junction (sector 394, x 39.25, y
10-13: 8,000 to 11,000 north of the bars, E3M3's own is 6,672; its riser,
sector 397, starts beside the stash's mouth): the player meets bars, riser, wheel,
and comes back. Cheapest: make 1323 live. One turn; sound 209 at the wheel and 105/150 at
the bars.

## What I still do not know

* Ordinary doors on a secret's way are counted as walls that rise.
* Which of two ways a player takes: the walk's shortest is read.
* Sight reads flat floors and no stacked rooms; a portal under a masked wall is
  see-through if its tile is.
* E1M8's gravestone, E1M4's crate at close range and the DW gargoyle were not
  seen clearly (the cameras stood behind walls).
* Nothing here was played. The wheel over bars, and bars under a 24,576 roof,
  want the owner's walk.
