# Saloon and canteen: what to change

From the saloon study (`notes.md`, same folder), 2026-11-18. Compared
against our frames of `blood-city-current.MAP`. Our saloon: s3 (main), s4
(counter island x 5120..9216, y 9216..9984, rise 8,192), s5/s6 (table
platforms, rise 5,088, top 390), s7 (back room). Our canteen: s145 (main),
s147 (counter 1,024 x 1,536, rise 4,096 = 0.24 b), s148 (512 square, rise
2,048), s146 (back, bare). All floors are at z 8192 and all ceilings at
-24576 (1.93 bodies); every floor shade is 32 or 36.

Priority is by how much the frame changes. Z values below assume our floor
at 8192 (z grows downward).

## 1. Put the saloon counter against the north wall, with an aisle behind it

- **Change**: remove the island s4. Build the counter as a strip along the
  north side: counter x 4608..8960, y 9216..9728 (4,352 x 512 = 7.4 x
  0.87 m), floor z -2048 (rise 10,240, 0.60 b). Behind it an aisle x
  4096..9984, y 8192..9216 (1,024 deep), floor z 6144 (raised 2,048), floor
  tile 304 (owner: carpet). Leave the counter's east end open: the aisle
  meets the room at x 8960..9984 (1,024 wide) with the 2,048 step, as E1M2's
  aisle meets its room at w1571. The back room door, on y 8192, then opens
  into the aisle -- the bartender's way to the store.
- **Tiles**: counter top 34 (owner: wood for counter/cabinet sides), shade 5;
  room-side face 84 (owner: wooden panelling / wainscot), x repeat 1 per 128
  of length, y repeat 8, shade 26; ends 34.
- **Exemplar**: E1M2 s210 (counter) and s211 (aisle); DWE3M1 s134/s136 and
  E6M2 s122/s209 confirm the counter-plus-aisle in all three bars.
- **Frame test**: from the room's south-east corner the counter is a single
  long panelled run across the far side of the room with floor visible
  behind it, not a box in the middle of the floor.

## 2. Raise the main room and hang a soffit over the bar

- **Change**: main room s3 ceiling from -24576 to -36864 (45,056 high, 2.66
  b, 4.8 m, as E1M2 s278). Counter and aisle sectors keep ceiling -24576
  (32,768 over the room floor, 1.93 b): that is the soffit, 0.72 b deep.
  Back room s7 stays at -24576.
- **Tiles**: soffit ceiling 379 (owner: stone wall), shade 50; the soffit's
  front face (the upper wall where s3 meets the counter sector) 84 or 28,
  shade 40. One post: a 128 x 128 hole in the counter sector at its middle,
  walls 20 (owner: wood).
- **Exemplar**: E1M2 s210 (ceiling -53248 over room floor -20480; room
  ceiling -65536), post walls 1555-1558.
- **Frame test**: in the across-the-room frame the counter sits under a dark
  band roofing it; the room's ceiling is visibly higher than the bar's.

## 3. A back bar of bottles and hanging glasses

- **Change**: in the aisle's north wall, east of the back room (x
  7168..10240 is outside the back room's footprint), cut a niche x
  7424..9984 (2,560 long), 256 deep (y 7936..8192), sill floor z -4096
  (10,240 above the aisle floor), niche ceiling z -20480 (an opening of
  16,384, 0.97 b: DWE3M1's 22,528 would not fit under our 32,768 soffit).
  If the plot north of y 8192 is not ours, fall back to E6M2: wall tile 64
  (owner: barrel wall) on the aisle's north wall, repeats 16 x 8, shade 38.
- **Tiles**: niche back 105 (owner: coffered wood panelling), floor and
  cheeks 34, framing posts 20; niche floor shade 11.
- **Sprites** (all type 416, z on the sill, cstat 385 unless said):
  a run of eight 759 at rep 16x16, 64 apart (DWE3M1 496-501); then 759 rep
  48 pal 12, 605 rep 40x48, 606 rep 40, 712 (owner: clay jug) rep 48, 616 rep
  64, spaced 256; and eight 574 (owner: drinking glass) rep 40, cstat 16781
  (y-flipped), z 14,000 above the sill, 256 apart (DWE3M1 516-527).
- **Exemplar**: DWE3M1 s132 and its sprites; E1M2 s213 for the 105 back.
- **Frame test**: looking over the counter, a lit wooden shelf full of
  small bottles reads behind it, with glasses hanging upside down along its
  top.

## 4. Stools along the counter face

- **Change**: six stools in front of the counter: x 4992, 5760, 6528, 7296,
  8064, 8832 (768 apart), y 9984 (256 out from the face at y 9728).
- **Sprite**: tile 284, type 416, cstat 385, rep 32x24, z 8192 - 2,880 =
  5312, shade 0.
- **Exemplar**: DWE3M1 sprites 539-547.
- **Frame test**: a row of chrome stools with red seats stands in front of
  the counter at even spacing, their seats just below the counter top.

## 5. A light pool on the bar; a dark room

- **Change**: counter top shade 5, aisle floor 11, niche floor 11, soffit
  ceiling 50, room floor s3 30, room ceiling 38, room walls 30-40 (vary by
  wall, darker in corners). Hang two lanterns over the table area.
- **Sprite**: 641 (owner: lamp hanging on a chain; needs a real ceiling --
  this one has one), type 0, cstat 128, rep 64x64, z just under the raised
  ceiling (-36864 + 1,024), at (6144, 11776) and (8192, 11776).
- **Exemplar**: E1M2 s210/s211/s213/s278 shades; DWE3M1 sprites 554/555.
- **Frame test**: in the across-the-room frame the counter top is the
  brightest horizontal surface; the floor in front of it is darker.

## 6. Tables you stand at in the saloon; cloth tables in the canteen

- **Saloon**: remove the platforms s5 and s6 (they read as raised floor, not
  tables) and stand four pedestal tables 649 at (5632, 11264), (7168,
  11264), (6400, 12800), (8704, 12800) -- a 1,536 x 1,536 stagger.
  Sprite: type 417, cstat 385, rep 64x64, z 8192 (on the floor), shade -8.
  Keep the two chairs 758 out, or set them at a table as DWE3M1 does.
- **Canteen**: two table sectors 1,024 x 1,024 rising 6,144 (0.36 b), top
  and sides 1008 (owner: tablecloth, carpet), two chairs 758 each (rep 40,
  type 416, cstat 385, z 8,960 above floor), tables 2,048 apart.
- **Exemplar**: E1M2 sprites 162-164/197 (saloon); DWE3M1 s149-152 and
  chairs 538/548/550-553 (canteen).
- **Frame test**: the saloon floor shows four round-topped pedestal tables
  at standing height; the canteen shows two covered tables with chairs.

## 7. The pub sign on the soffit and a jukebox

- **Sign**: move the WHISKEY letters' role to 741 ("Cask of Amontillado Pub
  & Grille", not owner-named) on the soffit front, centred on the counter,
  wall-aligned cstat 208, rep 64x64, type 417, on the soffit's front face
  (which spans z -24576 to -36864 once item 2 is done), centred at z -29696:
  37,888 above the floor (2.23 b), as E6M2 sprite 70. (goods.py hangs 741
  at rep 80 beside the door outside; inside, 64 as E6M2.)
- **Jukebox** on the west wall, x 4096..4544, y 11520..12544: two side
  columns 448 x 256 and a middle 448 x 512, all rising 8,192, tops 2476
  (owner: cash register top / machinery) on the columns and 2291 in the
  middle; column faces 569 (owner: stained glass -- here the coloured
  tubes), middle face 105; a 64 x 1,024 strip behind them rising 14,336
  with top 68. Flat sprite 2546 on the middle top: type 416, cstat 485, rep
  32x28.
- **Exemplar**: E6M2 sprite 70; E1M2 s40-43 and sprite 543.
- **Frame test**: the sign is read over the bar from the door; the west
  wall shows a box with orange, red, blue and green tubes either side.

## 8. The canteen counter at serving height, with a hatch and a menu

- **Change**: s147 rise from 4,096 (0.24 b) to 7,168 (0.42 b, floor z
  1024), 768 deep, along the wall shared with the back room s146; over it a
  serving hatch into the kitchen (an opening in that wall above the counter
  top, 1,536 wide, its lintel at 1.9 b). Remove s148.
- **Tiles**: top 34, face 28 (owner: wooden wall).
- **Sprites**: four tankards 604 on the top, rep 40x40, type 416, cstat 385,
  256-450 apart (E2M4 377-380); chalkboard 2318 ("Today's special") beside
  the hatch, wall-aligned cstat 208, rep 64x64, 19,456 above the floor
  (1.15 b), type 417 (E6M2 sprite 190).
- **Exemplar**: E2M4 s409 under its louvred hatch into s434; E6M2 sprite
  190.
- **Frame test**: the counter top is at hip height with mugs on it, the
  kitchen is visible through the hatch behind, the chalkboard is legible.

## 9. Make the canteen's back room a kitchen

- **Change**: floor of s146 to 365 (grey tiles), walls 503 (owner: metal
  wall), shade 17-35. Along its north wall two stove bays, each 1,280 x 512
  rising 8,192 (z 0), top 487, room-side face 490, the bay ceiling 20,480
  above the stove top (z -20480), hood ceiling 503 at shade 45 (E2M4 uses
  376, whose picture I have not looked at), the bays separated
  by a 512 metal pillar. Along the east wall a prep counter 2,560 x 512
  rising 6,144, top 266 (owner: glass or metal sheet), its ceiling tile 501
  (owner: technical light) at shade 0.
- **Sprites** over each stove (type 417, cstat 385, rep 64x64): 2304 at
  15,872 and 2305 at 16,384 above the top; steam 672 (owner: smoke/steam
  plume) type 0, cstat 128, rep 40, 160 above; pot 961 rep 64 at 1,792;
  meat 1269 rep 64 at 1,280 on the prep counter. Tools on the wall above
  the prep counter: 1709, 1715, 2140, cstat 464, rep 56-64, 13,312-15,360
  above its top, type 417.
- **Exemplar**: E2M4 s399, s400, s419 and sprites 621-623, 626, 332-333,
  636, 693, 385-388, 624-625.
- **Frame test**: through the hatch the back room shows grey tile, steel
  walls, two dark recessed stoves with pans hung over them and steam rising.

## 10. Wall bands in the saloon

- **Change**: the main room's walls are 28 floor to ceiling. Replace with
  150 (unnamed; brown stained plaster over a dark marbled dado) on the long
  walls, y repeat 8, shade 26-43, as E1M2 s278's 69% wall share; keep 28 on
  the counter and in the back room.
- **Exemplar**: E1M2 s278 walls.
- **Frame test**: the room walls show a dark lower band and a brown upper
  band; the wood is left to the counter, which then stands out against them.
  Ask the owner to name 150 first.
