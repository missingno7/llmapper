# Church interior: gaps against the study

Prioritised. Each change keeps the outer walls closed (no opening, no niche
cut through them: l3_church.py PORTALS) and keeps rooms of one layer from
overlapping in plan -- everything below is either a hole carved inside a
room, a sector inside the church mass that no room owns, or a sprite.
Units: 1,060 = 1.8 m = one body high (16,960 z).

1. **Light hierarchy: bright floor, dark roof, brightest chancel.**
   Today every church surface is shade 32 (nave s79, chancel s103, aisle
   s84, measured in blood-city-current.MAP). Recipe: nave floor 20, nave
   ceiling 44, aisle floor 28 / ceiling 40, chancel and apse floor 14 /
   ceiling 36, walls follow their floor +6; lancets and the great window's
   reveal -6. From E3M4 s286 (floor 9-11 under ceiling 45) and DWE1M4 s288
   (chancel floor 24 vs nave 36, rose -6). Frame test: in `nave_north` the
   chancel end is visibly the brightest band and the roof the darkest; a
   luminance profile down the frame's centre column falls from floor to
   ceiling.

2. **Pews with a profile, in wood.** Replace `chapel_furnishing`'s grey
   kerbs (512 deep, rise 5,120, pitch 1,024, 406/110). Recipe per pew:
   seat 512 deep rising 6,144 (0.36 body), top 34 (owner: wood for
   counter/cabinet sides), faces 88 (owner: wooden pilaster -- repeats
   three times on a 1,536 face, reads as panelled pew ends); back strip 256
   deep behind the seat rising 12,288 (0.72 body), same tiles. Pitch 1,536,
   three rows (E3M4 has three) with their seat fronts at y 25,600, 27,136
   and 28,672, below the steps of gap 3; 1,536 long (x 28,672..30,208), 512
   side aisles as now; 1,536 of clear floor left at the south end. From E3M4 s280-s285 (seat, tiles, pitch) and DWE1M4 s229/s230
   (back + seat pair: there the back is 14,336, 0.85 body, and the seat
   5,120; the 0.72 back is our own recipe). Frame test: in `nave_north` each pew shows a lit top
   and a taller dark back, and the rows read as separate (floor visible
   between them), not as one stepped mass.

3. **A raised chancel with steps and a rail.** Today a single 2,048 rise
   (0.12 body). Recipe: raise the chancel 8,192 (0.48 body) over three
   rises: two steps 512 deep carved as raised solids across the nave's
   north end (y 24,064..24,576 at 2,048 and y 24,576..25,088 at 5,120,
   full nave width, inside the nave so nothing overlaps), and the last
   3,072 at the nave/chancel line itself; chancel floor 15 (owner: planks)
   or keep 307; then four 1056 sprites across the top step: wall-aligned (cstat 16|64,
   as DWE1M4's 413), x_repeat 32, y_repeat 16 (1,024 wide x 8,192 z), 4,096
   over the step, 1,024 apart, leaving the centre 1,024 open. From DWE1M4
   s216-s226 and sprites 234-238; height from E3M4 s295. Frame test:
   `nave_north` shows a stair and an iron rail with bars against the lit
   chancel floor; the altar stands above the rail line.

4. **The altar: a cloth-draped table with candles, between candle boxes.**
   Today a two-tier grey block 1,280 x 1,024. Recipe: mensa 1,536 x 640
   rising 13,312 (0.78 body) over the chancel, top 253 (owner: dressed
   stone -- altars), faces 146 (owner: curtain texture -- E3M4's lectern
   wears it as cloth), shade 10; on it six 938 candles in a line 192 apart
   (cstat 384, rep 64x64, shade -8, type 32 as E3M4 sprites 528-536); in
   the chancel's two north corners (x 28,160..28,672 and 30,208..30,720,
   clear of a mensa at x 28,672..30,208) a 512-square candle box rising
   8,192, top 355, with three 938 in a diagonal 128 apart (E3M4 s292/s294
   at half size: theirs are 1,024 with five); a 580
   candelabrum (rep 64x64, shade -6, cstat 385) at each south corner of
   the chancel (DWE1M4 sprites 314/315); a 1013 vase (rep 64x64, type 416)
   each side of the mensa (DWE1M4 sprite 387). Frame test: `apse` shows a
   draped table with a row of flames on it, not a stacked block.

5. **One great window and a cross behind the altar, not three equal slits.**
   Today three 569 sprites at 512 pitch in the apse. Recipe: on the apse's
   north (solid, outer) wall hang ONE 265 sprite (a haloed figure; 0%
   see-through, so legal on a solid wall) wall-aligned, x_repeat 96,
   y_repeat 128 (1,536 x 2 bodies), sill 0.8 body, shade -6; flank it with
   two 569 lancets of x_repeat 32, y_repeat 128 (512 wide, 1.5 bodies) at
   sill 1.0, 128 clear of it. In front, on the altar's axis 512 north of
   the mensa: a cross -- a 256 x 256 post carved into the apse rising 2.6
   bodies, faces 20 (wood); arm of tile-68 wall sprites (rep 64x64, two per
   face, front and back 256 apart, plus flats top and bottom, end caps rep
   16x64) 1,792 long with its centre at 1.75 bodies -- two thirds up, NOT
   DWE1M4's lower-third (inverted) arm. From DWE1M4 s192 (one picture
   window, bright, on axis) and s200 + sprites 237-247 (the cross); 265
   from E3M2 s312-s314. Frame test: `apse` and `nave_north` show a single
   bright picture with a dark cross over it; the reviewer's "stamped" must
   not apply to the east end.

6. **An arcade between nave and aisle.** Today the aisle is open along the
   nave's whole west face and reads as a ledge under a coffered band.
   Recipe: two free columns carved inside the nave's 512 west side aisle
   (x 28,160..28,672, inside the nave, not the aisle room), centred between
   the pew rows of gap 2 at y 26,624 and 28,160 (pitch 1,536 -- half
   E1M5's and E3M4's 3,072, for a nave a quarter of E1M5's width): each a
   512-square solid hole whose faces wear 479 (owner: stone column
   texture; 32 px = 512, one repeat per face, x_repeat 4) -- or, to
   transcribe E1M5's s306 at two-thirds scale, a 512-square sector with
   floor raised 6,656 (plinth) and ceiling dropped 4,608 (capital), both
   faced 366, holding a 16-gon solid shaft 384 across in 93. Add a respond
   (a 256-deep half pier, same tile) at each end of the nave's west face. Raise the aisle
   ceiling from 32,768 to 40,960 (2.4 bodies, 0.63 of the nave as E3M4's
   0.58 and DWE1M4's 0.63) if the low roof's eaves allow (BODY_HEIGHT
   65,536 says they do). Frame test: `nave_west` shows two columns rising
   from floor to roof with the aisle seen between them, and the aisle
   ceiling as a lower plane behind the columns.

7. **Break the blank east wall into bays.** The east wall over the vestry,
   antechamber and narthex is 406 from floor to roof. Recipe: split the
   nave's east face into segments at the clerestory stations and give the
   piers between them 408 (grey stone panel with meander border, E1M5's
   partner to 406) at x_repeat 8 per 1,024, the stretches 406; run a 409
   meander band (owner: grey stone wall with meander ornament) as the
   upper texture where the aisle and side rooms' ceilings meet the nave
   wall (E1M5 s306 w2430, E3M4's 123 band at the aisle step). Engaged
   half-columns like E3M4 s278 (eight 200-unit walls of 245, shade 39 at
   the crown to 47 at the edge) would need 512 of depth the plan does not
   give on this face; use them only on the west aisle's outer wall if its
   1,024 width allows a 512 bulge. Frame test: `nave_east` shows vertical
   bays and a horizontal band at the aisle-ceiling line; no stretch of
   unbroken 406 wider than 1,536.

8. **Group and vary the clerestory glass.** Today twelve identical 569
   sprites, one per station. Recipe: per bay, pairs of 569 lancets 384
   wide (x_repeat 48) with a 128 mullion between, alternating y_repeat 176
   and 144 bay by bay; over the chancel step, both walls, one taller light
   (y_repeat 208). Keep the outside stations (`glaze`) where they are; only
   the inside counterparts move. From E3M2 s312-s314 (one subject in
   three lights of differing repeat/panning and head shape) and DWE1M4
   (glass as an event, not a wallpaper). Frame test: `nave_east` and
   `nave_west` show lights in pairs at two heights; a blind reviewer no
   longer writes "evenly spaced" or "identical".

9. **Candlelight down the aisle, a chandelier in the crossing.** Today four
   wall braziers for the whole church. Recipe: a 580 candelabrum at the
   aisle end of every other pew (cstat 385, rep 64x64, shade -6, floor
   standing, 128 clear of the pew), and one 628 chandelier (rep 64x64,
   shade -12, cstat 385) hung under the nave ridge 512 south of the
   chancel step, its bottom 1.4 bodies below the ceiling. From DWE1M4
   sprites 306-313 (pitch 2,048) and spr373 (628, 78,080 over the floor in
   s278). Frame test: `nave_north` shows a rhythm of flames converging on
   the chancel and a hanging ring of candles against the dark roof.

10. **Stoups at the way in.** Today the font is a 4,096-high block in the
    narthex. Recipe: keep the block, and stand a 1063 sprite (basin on a
    gilt pedestal) either side of the narthex-to-nave opening, 768 inside
    the nave, face sprite rep 48x48, cstat 385, shade 8, type 416 -- or put
    one 1063 on the font block in place of its plain top. From E3M4
    sprites 280/281. Frame test: `narthex` shows a basin on a pedestal at
    waist height.

Not on this list, and why: widening the nave (the vestry, antechamber and
narthex own the east, the mass edge the west -- gap 6 is the way to make
the 3,584 read as one space); 264 and the fire room (cult); 633/637
(funeral and cult emblems).
