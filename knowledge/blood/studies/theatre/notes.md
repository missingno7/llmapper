# Study: theatre

Written 2026-11-18, AFTER the Aldermack was built without one. Scale used
throughout: a body is 16,960 z (1.8 m) and 1,060 plan units; 1,024 units is
1.7 m (`projects/blood-city/level/scale.py`).

## What I want to build

The Aldermack, the landmark theatre of Gravesend on Theatre Row: a house of
seats that a player stands in and reads at once as an audience's room,
facing a raised stage behind a proscenium curtain that slides open, with the
stage's own back-of-house (backstage, dressing room) behind it, and a foyer
with a ticket window and posters on the forecourt.

## Where Blood built it

**The campaign never built a theatre, a cinema or an opera house.** I
looked for them by evidence, not by name, over the campaign (43 maps) and the
curated set (46 maps):

- seat rows: 5 or more same-size raised boxes off one parent, and chair or
  sprite grids (`scratch rows.py`, `grid.py`, `sprrows.py`);
- raked rows: chains of 4 or more strip sectors rising 768 to 8,192 per step
  (`rake.py`);
- wide curtains: curtain tiles 146/147/159 running 4,096 or more on one side
  of a sector (`widecurtain.py`);
- letter-sprite signs (font 3808 = A): no THEATRE, CINEMA, STAGE or TICKETS
  anywhere; the words found are carnival and hotel words (E1M4's
  SEEING IS BELIEVING, DWE1M9's HOUSE OF HORRORS).

The leads did not hold up when I looked: E1M4 s219 is a carnival booth (a
160-deep slide curtain, s218, before a 1,536 by 2,400 stall); E2M4 s489-s495
are four curtained monster closets; DWE2M3 s584's "seat row" is a strip of
fluorescent floor lights (2288); DWE1M9 s632 is a carnival ride; DWE3M4 an
arcade; DWE2M10 a dining car; TEDE1M6 a railway carriage; DWE3M5's curtained
"rows" are a draped staircase. So the exemplars come from the community set,
where three map files are named for the thing, plus two campaign pieces:

- **SCHOOL_.MAP (community, tier S) -- the theatre.** Seeds `SCHOOL_.map:154!`
  (the house) and `SCHOOL_.map:244!` (the stage). A school auditorium with a
  raked floor of 48 seats, an orchestra pit, an apron, a three-bay proscenium
  hung with a static curtain (159), and a deep stage with risers behind.
- **FORDTHEA.MAP (community, untiered) -- a cinema.** Seed `FORDTHEA.MAP:252`.
  House s252 with three sector benches facing a screen that is tile 2047
  ("COMING SOON to a theater near you -- BLOOD THE MOVIE"); a lobby (s119,
  s239) with a panelled ticket/concession window.
- **DARKTHEA.map (community, tier B) -- a dark theatre, studied by my own
  renders** (the study tool and `look.sector_at` stop on its malformed sector
  336, so I wrapped `_contains` in a scratch runner): a stepped house of 7
  rows either side of a centre aisle, s374-s387, facing a stage platform s350
  with a curved apron. No curtain and no proscenium.
- **E1M1 s122 (campaign), seed `E1M1:122!`** -- the funeral chapel: two
  sector pews (s46/s47, s49/s48) and, on the east wall, the owner's attested
  curtain s125 (slide-marked, 128 deep, 4,352 long) closing alcove s124.
- **E1M5 s180-s182 and s191-s192 (campaign)**: gold curtained alcoves in the
  cathedral: slide-marked s182, 1,536 by 512, busy 10, wait 30, in front of a
  2,560 by 1,536 alcove whose every wall is 146.

## What makes it read as that

Looked at in frames rendered as played (control sprites hidden):

1. **The curtain is a WALL, floor to a high header, edge to edge.** SCHOOL_'s
   frame from the back of the house is dominated by a wall of festooned
   drapes (159) under a stone header; from the apron it fills the frame. It is
   not a strip on a low stage -- it is the far wall of the room.
2. **The proscenium is three bays**: a tall centre (s181, 5,376 wide) between
   two lower side bays (s179, s182, 2,304 each), all on one 128-deep strip,
   and the wall above them is a different material (tile 70, a grey framed
   stone panel) from the house's walls. The step in the header is what makes
   it a frame rather than a curtained wall.
3. **Seats are many small identical things in a grid with an aisle.** SCHOOL_
   has 48 sprites (649, a pedestal) in six rows of eight, one aisle; FORDTHEA
   and E1M1 build seat and back as two strips each, and the back is what
   reads -- a row of boxes with a taller lip behind. Three full-width slabs
   (ours) read as carpet stripes.
4. **The house floor falls toward the stage** (SCHOOL_ s154 is sloped, heinum
   256, its seats' z drops 1,024 per 1,024 toward the front; DARKTHEA steps
   4,096 per 2,048-deep row), so from the back you look DOWN over the seats.
5. **The room is far taller than any other room**: 5.7-6.8 bodies over the
   seats in all three exemplars, against a campaign room median of 1.93.
6. **The stage stands proud, with a pit or a lip in front.** SCHOOL_'s stage
   is about 0.68 body above the front of the house, over a pit 0.72 body deep
   whose stage-side face is hung in curtain 146 (wall 1213) -- a skirt.
7. **A cinema is read by its screen and a ticket window**: FORDTHEA's end wall
   is one copy of 2047 stretched over the whole 6,400 by 89,856 above a 1.2
   body sill; its lobby has a wood-panelled (179) front with two windows split
   by a post over a 0.36-body counter, and someone and goods behind it.
8. **Dark, not lit.** No exemplar lights the stage: SCHOOL_'s stage (floor
   shade 54) is darker than its house (42/47); DARKTHEA is 35-50 throughout;
   FORDTHEA 15 flat. The only painted light I saw is E1M1 s124's alcove
   behind the curtain: its walls split into 256-unit pieces whose shade runs
   24, 28, 32 ... 48 away from the curtain -- a falloff done by hand.

## Sizes

All in units (plan), z, bodies (b) and metres.

| thing | exemplar | size |
|---|---|---|
| house | SCHOOL_ s154 | 12,160 x 11,520 (20.6 x 19.6 m) |
| house | FORDTHEA s252 | 6,400 x 7,040 (10.9 x 12.0 m), flat |
| house | DARKTHEA s374-s387 | 2 blocks 11,520 + centre aisle 2,048, 7 rows x 2,048 deep (39 x 24 m over all) |
| house height | SCHOOL_ / FORDTHEA / E1M1 | 115,712 z (6.8 b, 12.3 m) / 106,496 (6.3 b, 11.3 m) / 98,304 (5.8 b, 10.4 m) |
| rake | SCHOOL_ | slope 1,024 z per 1,024 units; 11,520 z (0.68 b) over the house |
| rake | DARKTHEA | 4,096 z (0.24 b) per 2,048-deep row; 28,672 z (1.7 b) over 7 rows |
| seats (sprites) | SCHOOL_ spr 619-666 | tile 649, x/y_repeat 64, cstat 129, angle 1536 (facing the stage); 1,024 apart across; rows in pairs 1,024 apart, pairs 3,072 apart (a 2,048 cross aisle); one 2,048 gap for the aisle; 8 a row |
| pew (sectors) | E1M1 s46/s47 | 4,096 long (7.0 m); seat 512 deep at +4,096 (0.24 b), top 300; back 256 deep at +10,240 (0.60 b), top 20; faces: front 300, ends 84, rear 20; 2,304 between pews |
| bench (sectors) | FORDTHEA s90/s89 | 3,072 long (5.2 m); seat 256 deep at +4,096 (0.24 b); back 128 deep at +7,168 (0.42 b); top 179; pitch 1,280 (2.2 m); side aisles 1,792 and 1,536 |
| carriage seat | TEDE1M6 s35/s34 | 1,536 long; cushion 512 at +4,096; back 256 at +11,264 (0.66 b) |
| aisles | SCHOOL_ / DARKTHEA | 1,024-2,048 centre; DARKTHEA side aisles 1,536 |
| apron | SCHOOL_ s177 | 12,032 x 2,816 (20.4 x 4.8 m), ceiling 97,280 z clear (5.7 b) |
| stage height | SCHOOL_ | about 11,520 z (0.68 b, 1.2 m) over the front of the house (from the front seats' z) |
| stage height | DARKTHEA s350 | 14,336 z (0.85 b) over the front row |
| pit | SCHOOL_ s165 | 7,552 x 1,536 (12.8 x 2.6 m), 12,288 z (0.72 b) below the stage, side steps s161-s164 of 3,072 |
| proscenium | SCHOOL_ s179/s181/s182 | curtain line 9,984 wide (17.0 m), 128 deep; centre opening 5,376 (9.1 m) x 60,416 z (3.6 b, 6.4 m); side bays 2,304 (3.9 m) x 51,200 (3.0 b); header above the centre 36,864 z (2.2 b) of tile 70 |
| stage | SCHOOL_ s244 | 12,384 x 6,784 (21.0 x 11.5 m) behind the curtain line, 60,416 clear; floor 15 (planks); risers s189 (+4,096) and s183 (+12,288) at the back; door s190 |
| stage | DARKTHEA s350 | 25,088 x 4,096, curved apron (s381/s382) |
| screen | FORDTHEA s250, wall 1408 | 6,400 wide, from a 20,736 z (1.2 b) sill to the ceiling: 89,856 z (5.3 b, 9.5 m); tile 2047 at x_repeat 16, y_repeat 3 (one copy) |
| ticket window | FORDTHEA s239/s119 | counter 5,824 x 512 at +6,144 z (0.36 b); two windows in a 179 wall split by a post |
| curtain (moving) | E1M1 s125 | 128 x 4,352, type 614, every wall 146, x_repeat 24/16, rx 125 tx 126 command 5 busy 40 wave 1; markers type 3 and 4 at its two ends |
| curtain (moving) | E1M5 s182 | 1,536 x 512, type 614, rx 109 busy 10 wait 30, walls 146 |

**Ours**, measured from `blood-city-current.MAP` (s20-s34) and looked at in
six frames: house s20 7,168 x 7,168 (12.2 x 12.2 m), ceiling 49,152 z (2.9 b)
at the stage end, sloping up 8,192; stage s21 5,120 x 2,048 (8.7 x 3.5 m),
rise 4,096 (0.24 b), clear 24,576 (1.45 b, 2.6 m) under a soffit; curtain s34
(type 614, rx 340 tx 341 command 5, busy 15) 5,120 x 256, standing 256 IN
FRONT of the stage edge; rows s22-s24, three 5,120 x 512 slabs at +1,024,
+2,048, +3,072, pitch 1,024, no aisle; every wall tile 119, floor 300,
ceiling 422, every floor shade 32. Backstage s25 2,048 x 7,168, 1.93 b high,
a corridor beside the house (not behind the stage). Foyer s27 4,096 x 4,096
with a free-standing box-office counter s28 at +8,140 (0.48 b).

In the frames ours reads as a hotel corridor: from the back of the house the
"stage" is a thin line under a band of wallpaper; the curtain is not visible
at all (the file holds it gathered); the rows are carpet stripes.

## What I will transcribe

- **The proscenium of SCHOOL_**: a 128-deep curtain strip across the full
  house width, three bays (tall centre at 3.6 b, side bays at 3.0 b), header
  wall above in tile 70 (unnamed by the owner; looked at: grey framed stone
  panel, solid, fine on a solid wall).
- **The moving curtain of E1M1 s125**: a thin type-614 sector, walls 146, as
  the owner binds ("a thin sector that changes width"), linked by command 5
  to what lies behind it. Ours already is this; it must hang in the
  proscenium and be CLOSED as the level loads.
- **Static flanking drapes** in 159 (owner: "crumpled curtain"), as a masked,
  blocking over-picture on the side bays (cstat 17), as SCHOOL_ walls 1346 and
  1360 -- the dressing that frames the moving 146 leaf.
- **A stage skirt in 146** on the stage's front face (SCHOOL_ wall 1213).
- **Sector seats** on E1M1's pew profile (seat 512 at 0.24 b topped 300,
  back 256 at 0.60 b topped 20, ends 84), cut into rows with a centre aisle,
  on a house floor that rises toward the back by 1,024 z per row.
- **A house 5.5-6.8 bodies tall**, dark (floor shade about 40, ceiling about
  47, SCHOOL_), and a stage floor of planks (15, owner: "planks") so the stage
  is a different surface from the carpeted house.
- **Foyer posters**: 2047 (the BLOOD THE MOVIE "coming soon to a theater near
  you" poster; looked at; unnamed by the owner -- something to tell him) and
  981 (owner: poster "JOJO the idiot circus boy"), and a ticket WINDOW in a
  wood-panelled (179, owner: "wooden panel") wall, FORDTHEA-style.
- E1M1 s124's shade falloff (walls split into 256 pieces, shade stepping 4)
  for the stage behind the curtain.

## What I will not do, and why

- **Not seat sprites of 649.** I looked at it: it is a pedestal table, not a
  chair; SCHOOL_ uses it as seats but from the back of the house it reads as
  a hall of café tables. The owner's chair is 758 ("voxel chair", a mask
  sprite) -- 48 of them would be a forest of voxels; sectors are what Blood's
  own campaign (E1M1) uses for seating.
- **Not 759** for anything seat-like: it is a bottle.
- **Not DARKTHEA's room.** It has rows and a stage but no curtain and no
  frame, and in the frames it reads as an empty dark hall: the negative
  example of what a theatre without a proscenium is. (Its walls are 119, the
  same as ours.)
- **Not FORDTHEA's screen as our stage.** The Aldermack is a playhouse with a
  curtain; 2047 belongs in the foyer as a poster.
- **Not a lit stage as a rule.** No exemplar lights it; our light-follows-the-
  curtain link (s21 rx 341, amplitude -24) is our own idea, kept, but it can
  only read against a dark house.
- **Not the pit stairs at 3,072** without checking the player's step height:
  SCHOOL_ steps the pit 3,072 at a time; whether a player climbs that I did not
  verify here.

## What I still do not know

- Whether Blood (the campaign) has a balcony or a theatre box anywhere.
  FORDTHEA s150 is a 2,560 x 2,944 room 43,008 z (2.5 b) above the cinema
  floor that may be one; my render from it failed and I have not seen it.
- Footlights: no exemplar has any (no light sprites along a stage edge, no
  shaded strip). I do not know Blood's idiom for them.
- What palette 10 does to 159 on SCHOOL_'s curtain (it rendered dark red from
  the house and grey-blue up close); I have not compared pal 0 and pal 10.
- How a 5,120-wide 146 leaf looks in motion at our busy 15 -- none of this was
  walked in the game, and the file stores ours gathered.
- How much of a real theatre fits our 7,168 x 7,168 block: SCHOOL_'s house
  plus stage is 12,160 by 21,000; ours is a third of that.
- Whether a ticket booth was ever built in Blood as a free-standing kiosk;
  the only one I found (FORDTHEA) is a window in a wall.
