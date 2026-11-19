# Study: saloon

Written 2026-11-18, after the saloon and the works canteen of Gravesend were
already built from fixture templates. Scale throughout: 589 plan units to a
metre (1,024 = 1.74 m), 16,960 z to a body (1.8 m), so 1 m = 9,422 z.
Frames are as played (control sprites hidden); enemies stay in them.

## What I want to build

The drinking and eating houses of Gravesend: a **saloon** (main bar room
x 4096..10240, y 8192..13312, back room x 4096..7168, y 6144..8192) and a
**works canteen** (main x 49152..53248, y 12288..14848, back x 49664..52736,
y 10240..12288) in `blood-city-current.MAP`. Each must read as a place to
drink or to eat before anyone is in it: a counter you stand at, something
behind it, somewhere to sit or lean, and -- for the canteen -- a kitchen.

## Where Blood built it

Found by a corpus scan for bottle/glass/tankard/stool/table sprites per
sector and for raised sectors topped with 2476 (cash register), then looked at.

- **E1M2 sector 278** (seed `E1M2:278!`), the station bar of *Wrong Side of
  the Tracks*. 8,704 x 4,096 (14.8 x 7.0 m), 2.66 bodies high, chequer floor
  290. An angled wooden counter (s210) under a dark soffit, a bartender's
  floor behind it (s211), a bottle niche in the back wall (s213), a light
  panel over the bartender (s212), stools, pedestal tables, a **jukebox**
  on the west wall (s40-43) and a lit food case with a pot in it (s120).
  The best bar in the campaign.
- **DWE3M1 sector 238** (seed `DWE3M1:238!`), the "Cask of Amontillado Pub &
  Grille" of a Death Wish town map. 8,704 x 7,680 (14.8 x 13 m), 2.11 bodies,
  plank floor 15, grey brick 414 walls. An L-shaped counter (s134) with a
  walk-through gap (s135), a bartender aisle (s136) with doors at both ends,
  a long framed bottle niche (s132), nine stools, four table sectors
  (s149-152) with voxel chairs, lanterns, the cash register on its own
  stand (s139-144). The aisle's end walls wear a painted door (29).
- **E6M2 sector 82** (measured and rendered; dropped as a seed for the
  kitchen). The campaign's own "Cask of Amontillado" pub: a straight
  counter (s122), a raised aisle (s209), barrel wall 64 behind, a canopy
  over the counter with the pub sign on its fascia, a "Today's special:
  chum chowder" chalkboard (2318), pedestal tables in s64, s69, s121.
- **E2M4 sector 407** (seed `E2M4:407!`), the café of the *Overlooked
  Hotel*: pedestal tables, a short wooden counter (s409) with tankards,
  directly under a louvred wooden hatch that opens into the kitchen.
- **E2M4 sector 434** (seed `E2M4:434!`), that kitchen: 5,376 square
  (9.1 m), grey tile floor 365, metal cabinetry 503/1011, two stove bays
  (s399, s400), a prep counter (s419), pans, steam, meat, tools on the wall.
- **E3M1 sectors 170/171/168**, the *Ghost Town* bar: 1.93 bodies high,
  drop-ceiling 40, floor 390, red walls 100, counter tops s158 and s167. This
  is what our saloon was evidently copied from (same 390 floor, 40 ceiling,
  1.93-body height). Small and low; the least barlike of the six.
- Kitchen corroboration: **E3M2 s90** (pans 2304/2305 hung from a rack at
  1.3-1.4 bodies), **E1M2 s217** (a pan and skillet hung on a wall).

## What makes it read as that

1. **The counter is against something, with a person's space behind it.**
   In every bar the counter divides the room from a bartender aisle 1,024 to
   1,792 deep, and the aisle has the back bar on its far wall. Ours is an
   island in the middle of the floor with nothing behind it; looking at our
   frame it reads as a row of crates.
2. **Something hangs over the counter.** E1M2 drops a dark soffit (ceiling
   379, shade 50) 0.72 bodies below the room ceiling over the counter, held by
   a wooden post, with five drinking glasses (574) hanging upside down
   beneath it. E6M2 builds a canopy 1.15 bodies deep and hangs the pub sign
   741 on its front. That roof-within-the-room is the strongest single cue
   in the frames.
3. **The back bar is lit and full.** E1M2: a niche of coffered panelling
   105 at counter height with bottles standing in it. DWE3M1: a 3,328-long
   framed niche with ~20 bottles, jugs, a tin and 12 glasses hanging upside
   down along its top. E6M2: no niche at all -- the barrel wall 64 painted
   behind the counter.
4. **Stools in a row, tables that you stand at.** Tile 284 (chrome stool,
   red seat; not owner-named) lined along the counter face. The tables in
   E1M2, E6M2 and E2M4 are pedestal sprites 649 with NO chairs; only DWE3M1
   seats people, at table sectors with voxel chairs 758.
5. **The counter is the brightest thing.** E1M2: counter top shade 5, the
   aisle floor 11, the niche floor 11, against a room floor of 30 and walls
   26-44. Our saloon is a flat 32 everywhere.
6. **One thing that says "entertainment"**: the jukebox in E1M2 (coloured
   tubes of 569 either side, the record-player panel 2546 on top), the
   "Tonight!! Monkey wrestling" bill 440 and the chalkboard 2318 in E6M2, the
   Jo-Jo bill 981 by DWE3M1's register.
7. **A diner/kitchen differs by surfaces, not furniture**: grey tile floor
   365, steel walls 503, stoves as recessed bays with a hood, pans hung over
   them, steam rising, a steel prep top; the café side has a lower counter
   (0.42 bodies) with tankards 604 under a serving hatch, and a chalkboard
   menu. No bottles, no stools.

## Sizes

| thing | exemplar | units / z | metres | bodies |
|---|---|---|---|---|
| bar room | E1M2 s278 | 8,704 x 4,096, h 45,056 | 14.8 x 7.0, h 4.8 | h 2.66 |
| bar room | DWE3M1 s238 | 8,704 x 7,680, h 35,840 | 14.8 x 13.0, h 3.8 | h 2.11 |
| bar room | E6M2 s82 | 6,400 x 8,192, h 47,104 | 10.9 x 13.9, h 5.0 | h 2.78 |
| café | E2M4 s407 | 4,352 x 6,912, h 46,080 | 7.4 x 11.7, h 4.9 | h 2.72 |
| kitchen | E2M4 s434 | 5,376 x 5,376, h 40,960 | 9.1 x 9.1, h 4.3 | h 2.42 |
| E3M1 bar | s170 | 3,456 x 3,584, h 32,768 | 5.9 x 6.1, h 3.5 | h 1.93 |
| **ours** saloon | s3 | 6,144 x 5,120, h 32,768 | 10.4 x 8.7, h 3.5 | h 1.93 |
| **ours** canteen | s145 | 4,096 x 2,560, h 32,768 | 7.0 x 4.3, h 3.5 | h 1.93 |

Counters:
- **E1M2 s210**: rise 10,240 (1.09 m, 0.60 b) over the room floor, 512 deep
  (0.87 m), runs 1,792 + a 1,810 diagonal + 512 (about 4,100 = 7 m). Top 34
  (owner: wood for counter sides) at shade 5; room-side face 84 (owner:
  wooden panelling / wainscot) -- drawn through walls of tile 83 with cstat 2
  (bottom swapped), repeats 4..14 x 8, shade 26-41. Aisle s211 raised 2,048
  (0.22 m) above the room, carpet 304. The aisle opens straight onto the room
  at its north end (w1571, 1,024 wide): the way behind is past the end of the
  counter. Soffit: s210's ceiling 32,768 above the room floor (1.93 b), tile
  379, shade 50; post a 128 x 128 hole walled in 20.
- **DWE3M1 s134**: rise 9,216 (0.98 m, 0.54 b), only **256 deep**
  (0.43 m), 5,120 long plus a 2,048 return arm. Top 34, face 28 (owner:
  wooden wall) rep 40x8. **Gap s135**: 768 wide (1.3 m) at floor level,
  with a plank sprite 68 lying flat across it at counter height (sprite 477,
  cstat 417, rep 48x64) -- a lift-flap. Aisle s136 1,792 deep, flat; at its
  two ends a solid wall wears tile 29 (a painted plank door with a metal
  jamb), so the doors off the aisle are pictures, not openings.
- **E6M2 s122**: rise 8,192 (0.87 m, 0.48 b), 512 deep, 4,096 long (7 m),
  top 34, face 28 (w594), ends 473. Aisle s209 1,024 deep, raised 2,048.
  Canopy: s122's ceiling at 27,648 above the room floor (1.63 b) under a
  room ceiling of 2.78 b.
- **E2M4 s409** (café): rise 7,168 (0.76 m, 0.42 b), 768 x 2,048, top 34.
- No counter in the six has a **foot rail**, a kick plate or a step.

Back bars:
- **E1M2 s213**: niche 1,448 long, 362 deep, sill 8,192 above the aisle
  (10,240 above the room), opening 12,288 (0.72 b) tall; back 105 (owner:
  coffered wood panelling), cheeks 34, floor and ceiling 34 at shade 11/36.
  Five bottles: 759 rep 48-56 (pal 3, 4, 12), 605 rep 64 pal 4, 606 rep 64;
  all type 416, cstat 385, z on the niche floor.
- **DWE3M1 s132**: niche 3,328 long (5.6 m), 256 deep, sill 10,240 above the
  aisle, opening 22,528 tall; framed by posts of 20; back 28. Bottles 759 at
  rep 16 set 64 apart in a run (sprites 496-501), 759 rep 48, 606 rep 40,
  802, 712 (owner: clay jug) rep 48, 616 rep 80, 517, 604; all type 416,
  cstat 8577. Twelve 574 glasses (owner: drinking glass) rep 40, cstat 16781
  (y-flipped: hanging upside down), z 18,528 above the sill, 128-384 apart.
- **E6M2**: wall tile 64 (owner: barrel wall) behind the aisle, no sprites.

Hanging glasses under a soffit: E1M2 sprites 198-202, tile 574 rep 64, type
416, cstat 907 (y-flipped, translucent), z 16,128 above the counter top,
256 apart.

Stools (284, a 35 x 59 mask): E1M2 sprites 664-666 rep 40x32, z 3,840 above
floor, type 417; DWE3M1 539-547 rep 32x24, z 2,880 above floor, type 416,
cstat 385, **768 apart, 256 out from the counter face**; E6M2 40-44 rep
40x24, z 2,880 (around its tables, not a counter).

Tables: pedestal 649 (720 wide, 0.48 b), rep 64x64, type 417, cstat 385,
z on the floor. E1M2 s278 sprites 162-164, 197 in a staggered grid 1,024
across by 1,536 deep; E6M2 s64 sprites 124-128 in a row 1,792 apart.
DWE3M1 tables are sectors 1,024 x 1,024 rising 6,144 (0.36 b), with two
voxel chairs 758 (rep 32-40, type 416, cstat 385, z 7,168-8,960 above floor)
each, the four tables on a 2,560 x 2,048 grid.

Lighting: E1M2 floor 30 / ceiling 38 / walls 26-44 / counter 5 / soffit 50;
E6M2 floor 20, counter 20; E2M4 café floor 6, kitchen floor 7, stove tops
17, the prep counter's ceiling 501 (owner: technical light) at shade 0;
DWE3M1 shade 0 throughout with lanterns 641 (owner: lamp hanging on a chain)
rep 64x64 (sprites 554, 555). Ours: 32 on every floor and 27-34 on ceilings.

Kitchen (E2M4 s434): stove bays s399/s400 1,280 x 512 rising 8,192, top 487,
room-side face 490 (cstat 264), hood ceiling 20,480 above the top (1.21 b),
ceiling 376 at shade 45. Pans 2304 and 2305 rep 64, type 417, 15,872-16,384
above the stove top; steam 672 (owner: smoke/steam plume) rep 40, type 0,
cstat 128, 160 above; meat 1269 rep 64 at 1,280; pot 961 rep 64 at 1,792.
Prep counter s419 3,584 x 512 rising 6,144, top 266 (owner: glass or metal
sheet), with tools hung on the wall above it: 1709, 1714, 1715, 2140, cstat
464, rep 56-64, 13,312-15,360 above the top.

## What I will transcribe

- **The counter against a wall, with an aisle.** E1M2 s210/s211 dimensions:
  512 deep, 8,192-10,240 rise, top 34, face 84 (or 28 as DWE3M1/E6M2), an
  aisle 1,024 deep raised 2,048, entered past one end or through a 768 gap
  with a flat 68 plank across it (DWE3M1 s135, sprite 477).
- **The soffit** over counter and aisle: ceiling 1.93 b above the room floor
  in a room of about 2.66 b, tile 379, shade 50, one post; glasses 574
  hanging under it as E1M2 198-202.
- **A back-bar niche**: DWE3M1 s132's long niche (sill 10,240, 256 deep)
  with its run of bottles and hanging glasses, field for field; back 105 as
  E1M2 s213.
- **Stools** 284 as DWE3M1 539-547: 768 apart, 256 out, rep 32x24, z +2,880.
- **Pedestal tables** 649 as E1M2 162-164: rep 64, on the floor, a 1,024 x
  1,536 stagger, no chairs.
- **The light pool**: counter top 5, aisle 11, room floor 30, soffit 50.
- **The pub sign** 741 on the soffit's front, as E6M2 sprite 70 (cstat 208).
- **The jukebox** of E1M2 s40-43 on one saloon wall.
- For the canteen: E2M4's café counter (0.42 b, tankards 604), E6M2's
  chalkboard 2318, and E2M4 s434's stove bays, hood, pans, steam and prep
  counter in the back room.

## What I will not do, and why

- **No foot rail.** None of the six bars has one; it would be my
  invention.
- **No mirror behind the bar, no piano, no stage.** I found none of them in
  any bar or café of the corpus scan; the "entertainment" Blood puts in a
  bar is a jukebox and posted bills.
- **Not E3M1's 1.93-body drop ceiling (40) for the main bar room.** It is
  the only low bar of the six, and our frame shows why it reads as an
  office: the ceiling panels fill a third of the view. It may stay in the
  back room.
- **Not the curtain texture 146 on tables**, though DWE3M1 uses it: the
  owner's note on 146 says a curtain is a thin moving sector. 1008 (owner:
  tablecloth, carpet) is used as a table top in 4 maps; that one.
- **Not E2M4's body parts** (680 head, 682 arm) on the canteen's counters.
  That kitchen is a cannibal butcher's set piece; a works canteen is not.
  Raw meat 1269 is enough.
- **Not DWE3M1's flat shade 0 with fog.** That is a Death Wish lighting
  habit; the campaign's bars are dark rooms with a lit counter.
- **Not 504** anywhere, and no mask tile on a solid wall.

## What I still do not know

- What lies north of the saloon at x 7168..10240, y < 8192: the back-bar
  niche needs 256 of depth there. If it is another building, the back bar
  has to be E6M2's painted barrel wall 64 instead.
- Whether DWE3M1's flap sprite (cstat 417: blocking, floor-aligned at 0.54
  b) actually lets the player through the gap; the aisle's painted doors
  are not a way in, so if the flap blocks, the aisle is shut.
- How E6M2's raised aisle s209 is entered -- I did not trace it.
- Whether the city builder can give one room a 2.66-body ceiling while its
  back room stays at 1.93 (it is a building-wide constant in our map now).
- Tile 284 (the stool), 649 (pedestal table), 150 (brown plaster over a dark
  dado, E1M2's bar wall), 2546 (record-player panel) and 2318 (chalkboard)
  have no owner name; my readings of them are for him to confirm.
- None of it has been walked in the game.
