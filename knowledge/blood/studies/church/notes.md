# Study: church

Written 2026-11-18 after a blind reviewer scored St Gallow's interior 3/5
("identical, evenly spaced glass slits look stamped", "the altar is a plain
stacked block", "big blank stone wall"). Frames were rendered through
`look.as_played` (control sprites hidden); the exemplar frames below were
taken at brightness 8 to read structure and re-taken at brightness 0 (as
played) for DWE1M4. Scale: a body is 16,960 z = 1,060 units = 1.8 m; 589
units to the metre.

## What I want to build

The inside of St Gallow's, Gravesend's parish church: a nave a player walks
up between rows of pews toward a raised, brighter chancel where an altar
stands against a great window and a cross; a low west aisle that reads as
part of the nave through an arcade, not as a ledge beside it; glass that is
grouped and varied, not one slit stamped down each wall. All glass hung
inside (sprites, or pictures on interior solid walls) -- the outer walls
take no opening (l3_church.py PORTALS: the see-over roof).

## Where Blood built it

Seeds: `DWE1M4:276`, `E3M4:286`, `E1M5:104`. (A first run also seeded
`E1M5:362`, which is an outdoor yard, and `E1M5:394`, a cult hall with
square brick piers and a curtained stage; neither is a church, the folders
are left as evidence of the miss.)

- **E3M4 s286/s287 (campaign, "Sick Ward"): the funeral chapel.** The only
  campaign room found with true pews. Nave 7,168 x 4,096 under a pitched
  ceiling (432, two halves at heinum 4096 meeting on the centre line y=1024),
  ridge 98,304 z. Outer aisles s278/s279, 1,024 deep at 57,344 z, with
  engaged half-columns. Chancel s295 at the west end, lectern s293, candle
  boxes s292/s294 in the chancel's cut corners, gargoyle niches s392-397 in
  the east corners, an emblem sprite 637 high in the east gable.
- **DWE1M4 s276/s275/s277/s280/s284 (Death Wish, curated): a cathedral.**
  The richest church in the corpus. Nave 17,408 x 11,264 at 92,160 z; eight
  pew blocks (s229-s252) either side of a carpeted central aisle (s277,
  tile 251); chancel s288 raised by four steps (s204-s209, s216-s226) behind
  an altar rail of sprites; a cross (post s200 + arm sprites 237-247) in
  front of a rose window 264 (s192/s180) backlit by a fire room (s413).
  The map mirrors the whole church at x -18,000..-2,800 (s615-s649).
- **E1M5 s102/s103/s104 (campaign, "Hallowed Grounds"): the cult temple.**
  Not Christian, but Blood's own colonnade: two rows of three columns
  (s306-s311), a tall central strip s104 with a green runner (422), side
  bays s102/s103 under sloped ceilings, raised side galleries s99/s101 with a
  balustrade strip s98/s100, meander frieze 409 and panels 408 on 406 walls.
- **E3M2 s312-s314: a triptych of figure glass (265)** on solid walls at the
  back of three 1,024-wide, 256-deep niches, sill 18,432 z over the gallery
  floor s322. Measured only; I could not get a pose that sees it.
- **DWE1M4 s822-s835**: a 10,240-wide rose of 264 spread across seven niche
  walls by x-panning; shaped by sloped niche floors/ceilings. In an
  unearthly 60-body hall; looked at, not useful at our scale.
- Searched and NOT churches: E1M1 s123 (a corridor with one candelabrum),
  E1M5 s362 (yard with 569 windows on its building), E2M5 s299-307
  (stepped stair), E1M6 s303 (temple hall). A pew detector over all
  campaign and curated maps (rows of >=3 equal raised strips with a gap)
  found pews only in DWE1M4, DWE1M5, DWE1M9, E3M4 and E2M7 (E2M7's are
  sloped benches in water).

## What makes it read as that

1. **Rows of pews are the word "church".** Every frame of E3M4 and DWE1M4
   that shows pews reads as a church before anything else does. Both build
   them as raised sectors, not sprites, at a pitch that leaves a body's
   legroom (1,024) between them. DWE1M4's have a BACK: a tall strip behind a
   low seat, and a blue cushion (251) on the seat top -- the profile is what
   makes a block a pew.
2. **A bright, raised east end with a picture in it.** DWE1M4: the rose is
   shade -6 against walls at 37, the chancel floor 24 against the nave's 36,
   chandelier 628 hung under the crossing at 4.6 bodies, an iron rail (1056)
   across the top step, a vase (1013) and candelabrum (580) each side. The
   eye goes straight to it from the doors.
3. **Height is read from a low thing beside a tall thing.** None of the
   three has a flat ceiling over a uniform room: E3M4 drops its aisles to
   3.4 bodies beside a 5.8-body pitched nave; DWE1M4 rims its 5.4-body
   ceiling with a 3.4-body band (s281/s282) and coves the step with 512-wide
   sloped strips (s283, s285-s287, tile 273); E1M5 runs a 5.6-body slot
   (s104) between 3.7-body bays. Columns stand where the two heights meet.
4. **Walls are punctuated at a rhythm.** E3M4: engaged half-columns 1,024
   across at 3,072 pitch, made of eight 200-unit walls of tile 245 (twisted
   column), shade baked from 39 at the crown to 47 at the edges so the column
   looks round. E1M5: 408 panels and 409 meander bands on 406. Our nave has
   none of this: 406 at shade 32 from floor to roof.
5. **Light falls on the floor; the roof is dark.** E3M4 floor 9-11 under a
   ceiling at 45; E1M5 floor 7 under 45; DWE1M4 36 under 43-46 but chancel
   24. Ours is 32 on floor, ceiling, walls, nave and chancel alike -- no
   hierarchy at all (measured in blood-city-current.MAP: nave s79 floor 32
   ceiling 27; chancel s103 floor 32 ceiling 33; aisle s84 32/34).
6. **Glass is a subject, not a pattern.** DWE1M4 has ONE great window, a
   picture (264) 4,096 wide by 3.86 bodies, framed by a bright reveal (185
   and 253 at shade -6) and backed by fire (2342 mask in s180, flame sprites
   908 in s413). E3M2 makes three lights of one picture (265) differ by
   x_repeat (3 vs 2) and x_panning (24), and points the two outer heads by a
   sloped niche ceiling (heinum 4864) over a flat-headed centre. Ours is
   twelve identical 569 clerestory sprites (x_repeat 48, y_repeat 176,
   shade 8, sill 2.45 bodies), one per LANCETS_AVENUE station on both nave
   walls, plus three more of the same in the apse at 512 pitch.

## Sizes

| | DWE1M4 nave | E3M4 chapel | E1M5 temple | ours |
|---|---|---|---|---|
| nave width | 11,264 (19.1 m) | 4,096 (7.0 m); 6,144 (10.4 m) with aisles | 14,848 (25.2 m) | 2,560 (4.3 m); 3,584 (6.1 m) with aisle |
| length | 17,408 (29.6 m) | 7,168 (12.2 m) + chancel 2,048 | 10,240 (17.4 m) | 6,656 (11.3 m) + chancel 1,536 |
| height | 92,160 z: 5.43 bodies, 9.8 m | ridge 98,304: 5.8 bodies, 10.4 m | slot 95,232: 5.6; bays 62,464: 3.7 | 65,536: 3.86 bodies, 7.0 m, + pitch 1.29 |
| low side | rim 58,368: 3.4 bodies | aisles 57,344: 3.4 bodies | 3.7 | aisle 32,768: 1.93 bodies |

- **Pews.** DWE1M4 (s229-s252): back 512 deep rising 14,336 (0.85 body,
  1.5 m), floor 253; seat 512 deep rising 5,120 (0.30 body, 0.54 m), floor
  251 (blue cushion); row pitch 2,048 (3.5 m); block 2,048 long (3.5 m);
  four rows a block, two blocks a side; central aisle 2,560 (4.3 m, tile
  251 runner on 67 planks). E3M4 (s280-s285): one block 512 deep rising
  6,144 (0.36 body, 0.65 m), 3,072 long (two 1,536 halves meeting on the
  centre line, no central aisle), pitch 1,536 (2.6 m), three rows; top 34
  (wood), faces 88 (owner: "wooden column/pilaster with base and capital",
  which on a 1,536 face repeats three times and reads as panelled pew ends).
  Ours: 512 deep x 1,536 long, rise 5,120, pitch 1,024, tiles 406/110 --
  a grey stone kerb.
- **Chancel.** DWE1M4 s288: 4,096 x 7,168, raised 10,240 (0.60 body) over
  four steps 512 deep (2,048, 2,048, 3,072, 3,072). E3M4 s295: 2,048 x 6,144
  raised 8,192 (0.48 body), floor 15 (planks) at shade 16. Ours: raised
  2,048 (0.12 body), one step.
- **Altar / lectern.** E3M4 s293: 384 x 768 (0.65 x 1.3 m), a further 8,192
  over the chancel (0.97 body above the nave), top 34, faces 146 (owner:
  curtain texture) -- a cloth-draped stand. Candle boxes s292/s294: 1,024
  square in the chancel's cut corners, raised 8,192, top 355, five single
  candles 938 on each in a diagonal line (sprites 528-536: 128 apart in x
  and y, cstat 384, rep 64x64, shade -8, type 32). DWE1M4 has no altar
  table; the rail (sprites 234-238: tile 1056, wall-aligned, cstat 413, rep
  32x16 = 1,024 wide x 8,192 z, 4,096 over the floor, 1,024 apart along
  x=-28,800, angle 1024) and the cross stand in its place.
- **Cross (DWE1M4).** Post: s200, 256 x 256, its floor 53,248 over the
  chancel (3.14 bodies, 5.6 m); the faces you see are s288's inner loop in
  tile 20 (wood). Arm: tile 68 (wood plank, 64x16 px) sprites 237-247 --
  four wall sprites rep 64x64 (1,024 x 4,096 z) in front/back pairs 256
  apart, flats rep 64x64 above and below, end caps rep 16x64 -- 2,304 long,
  its centre 18,432 over the floor, i.e. at the post's lower third: an
  INVERTED cross (a cult church). Shades: front 12/14, back -16.
- **Rose (DWE1M4 s192 wall 1997 / s180 wall 1936).** Tile 264, masked wall
  cstat 209/217, rep 16x4 (one picture across 4,096 by 65,536 z), shade -6;
  its sill 10,240 over the chancel (0.6 body). Reveal s193-s199: 256 deep,
  floors/ceilings sloped (heinum +/-7,680, +/-4,096, +/-2,560 toward the
  ends) so the opening is an octagon; faces 185 and 253 at shade -6. Behind
  it a 64-deep sector s180 with fire mask 2342 (owner: "fire (mask wall)")
  at rep 8x2, then s413 with thirteen flame sprites 908.
- **Columns.** E1M5 s306-s311: a 1,024-square sector whose floor rises
  13,312 (plinth, 0.78 body) and ceiling drops 9,216 (capital, 0.54 body),
  both faced in 366 from the bay (copper-framed marble panels); inside it a
  solid 16-gon shaft 768 across in tile 93, shade 24. Pitch 3,072; rows
  9,728 apart. E3M4: engaged half-columns 1,024 across at pitch 3,072 in 245.
- **Light fittings.** DWE1M4: candelabra 580 at every pew row end along
  the central aisle (sprites 306-313: x pitch 2,048, both kerbs, floor
  standing, cstat 385, rep 64x64, shade -6), two more at the chancel corners
  (314/315); chandelier 628 (spr373, rep 64x64, shade -12) 78,080 over the
  floor in the crossing. E3M4: no candelabra; ten candles 938 on two boxes.
- **Font / stoup.** E3M4 sprites 280/281: tile 1063 (a basin of water on a
  gilt pedestal), face sprite rep 48x48 (about 624 wide, 0.69 body tall),
  cstat 385, shade 8, type 416, one either side of the centre line 768 in
  from the door wall. Ours is a raised block (FONT_RISE 4,096) in the
  narthex.

## What I will transcribe

- E3M4's pew at our scale: pitch 1,536, rise 6,144, top 34, faces 88;
  DWE1M4's back strip behind the seat (256 deep, rising 12,288).
- The chancel as DWE1M4/E3M4 raise it: 0.5-0.6 body by steps 512 deep,
  not one 2,048 kerb; a 1056 rail across the top step.
- E3M4's candle boxes in the chancel corners with 938 candles in a line;
  DWE1M4's 580 candelabra at pew-row ends and chancel corners, shade -6.
- A cross on the altar's axis built like DWE1M4's (post sector in tile 20,
  arm of tile-68 sprites), with the arm at two thirds of the post, not one.
- One great picture window over the altar: tile 265 (a haloed, robed
  figure with a sword) on the apse's solid north wall, bright reveal,
  flanked by 569 lancets of a different height.
- E3M4's engaged-column rhythm (245 or 479) and E1M5's 408/409 bands on
  the blank east wall; E1M5's plinth-and-capital column for the arcade.
- Light: floor bright (16-20) in the nave's centre and chancel, ceiling
  dark (44), aisle 30; glass and reveal at -6.
- E3M4's paired 1063 stoups at the way in.

## What I will not do, and why

- **No opening in an outer wall**, not even a niche cut into one: the
  see-over roof law (l3_church.py PORTALS) and the one-layer plan rule.
  Window niches only where the plan inside the mass allows (the apse's own
  depth), otherwise pictures as wall sprites.
- **Not 264.** It is a goat-headed Tchernobog rose: right for DWE1M4's cult
  cathedral, wrong for a parish church unless the owner wants St Gallow's
  desecrated. Not the fire room behind the glass either, for the same
  reason and because it needs depth we do not have.
- **Not DWE1M4's inverted cross**, nor its scale: its nave is 4.4 times
  ours in width; its proportions (pitch 2,048, 2,560 aisle) do not fit a
  2,560-wide nave. E3M4 is the size to copy.
- **Not 633 or 637.** 633 is a "REST IN PIECES" funeral wreath and 637 a
  cult emblem; both belong to E3M4's funeral parlour, not to a parish.
- **Not E1M5's raised side galleries** -- our aisle is 1,024 wide; a 1,536
  gallery would not fit.
- **No sprite-palette variation of 569** (E1M5 wall 29 wears pal 9) until I
  have looked at what pal 9 does to that tile; I have not.

## What I still do not know

- What E3M2's triptych looks like in the game: I measured s312-s314 but
  every pose from the gallery s322 looked under the frieze, not at it.
- Whether 265 at sprite scale (x_repeat 96, y_repeat 128) reads as glass
  or as a painting; it is 0% see-through and Blood uses it on walls, never
  as a large sprite (one sprite, DM1 sprite 65, rep 19x14).
- Whether a 3,584-wide nave+aisle with an arcade will satisfy the scale
  check (q1 6,144 for the floor area); the nave cannot widen east (vestry,
  antechamber and narthex stand there) or west (the mass edge is 26,624).
- The heinum-to-rise conversion for E3M4's pitched ceiling (where its
  eaves land); I read the ridge from ceiling_z, not the eaves.
- Whether wood pews (34/88) sit right in a 406 stone church: E3M4 is clay
  and wood throughout; DWE1M4's stone pews (253) with 251 cushions are the
  stone alternative.
- None of this has been walked in NBlood.
