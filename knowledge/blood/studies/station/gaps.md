# Station: a build recipe for Gravesend's first station

We have no station yet, so this is a recipe, not a gap list. It is one
building plus one platform, behind one of the empty edge facades, laid out
from `notes.md`. Every item names its exemplar as **[MAP s/spr id]**; my own
inventions are marked **[INVENTION]** and are the first things to check in
frames and with the owner. Units: 1,024 = 1.7 m; a body is 16,960 z.
Heights are given over the floor they stand on. "Bed" is the rail bed.

Levels (z grows downward; G = street floor):
- street G; booking hall G - 20,480 (1.21 bodies up) **[E1M2 s207 -> s105
  -> s271: -78,848 -> -99,328]**;
- platform = hall floor (they are one level, as E1M2 s271/s272);
- rail bed = platform + 14,336 (0.85 body down) **[E1M2 s272 over s34]**,
  i.e. the bed is G - 6,144: the track lies 0.36 body above the street.
- car floor = bed - 20,480 (1.21 bodies over the bed) **[E1M3 car floor
  8,192 over ground 28,672]** = platform - 6,144 (0.36 body up from the
  platform: under the ~6,659 z step allowance, not yet walked).

## Rooms, in the order the player meets them

1. **Doorway through the edge facade.** 2,048 wide (3.5 m), head 1.93
   bodies (32,768 z). Leaf: none (an open arch) or the facade's existing
   door style. **[INVENTION: width/height; E1M2's street entrance is a
   3,328-wide passage of two kSectorSlideMarked halves s103/s104, rx 161]**

2. **Entrance passage.** 3,328 wide by 4,096 deep (5.7 by 7.0 m), ceiling
   3.86 bodies, ceiling tile 120 ("clay tiles"), floor 281 ("irregular grey
   stone masonry"), walls 414 (unnamed: grey plaster over red brick),
   shade 39-51 (dim after the street). **[E1M2 s103/s104, minus their
   motion: we do not slide it]**

3. **Stair up to the hall.** 2,048 wide by 4,096 long, one sloped sector
   rising 20,480 z (1.21 bodies): floor heinum -1,280, floor_stat 66,
   floor 281, shade 12, walls 414 shade 15-39. **[E1M2 s105]** Axis aimed
   at the platform gates so the street door already shows them
   **[INVENTION: alignment]**.

4. **Booking hall.** 6,144 by 10,240 (10.4 by 17.4 m), 2.96 bodies high
   (50,176 z). Floor 281 shade 9, ceiling 67 ("dark horizontal planks")
   shade 26, walls 90 ("worn large bricks with moss") shade 36-39 and 49
   (unnamed: vertical planks with iron bands) on the back wall, 414 round
   the stair head. Long side toward the platform is the column-and-gate
   line (room 5). **[E1M2 s271: 5,120 by 12,288, same tiles; I widen it by
   1,024 to hold a counter]**
   - **Ticket counter** on the short wall away from the stair: a sector 512
     deep by 4,096 long raised 8,192 z (0.48 body), top 34 ("wood, usable
     e.g. for counter/cabinet sides"), face 34. **[counter form from E1M3
     s218/s220 (512 wide, 0.48 body); the ticket office itself is
     INVENTION -- no ticket office exists in the corpus]**
   - **Booth and grille** behind it: a room 1,536 deep, same floor, ceiling
     at 1.45 bodies so the opening over the counter is 0.48 -> 1.45 bodies;
     the counter's front edge carries a masked wall of 58 ("iron bars
     (jail)"), blocking, across that opening. **[INVENTION; 58's own mask
     use is 0.73 body tall, blocks 1]**
   - **TICKETS** over the booth in letter sprites: T 3827, I 3816, C 3810,
     K 3818, E 3812, T 3827, S 3826; wall sprites cstat 208, repeats 104 by
     104 (each 208 wide, 0.27 body tall), pal 5, spaced 384, centred 2.3
     bodies over the floor. **[letter form from E1M2 sprites 86-91 "TRACK
     A": cstat 208, repeats 104, pal 5, spacing 384; the word is INVENTION]**
   - **Clock**: tile 1165 ("wall clock"), wall sprite on the hall's platform
     wall over the widest gate bay: cstat 209, repeats 55 by 55, pal 0,
     shade -8, 2.6 bodies over the floor. **[MISKSTAT spr 143]**
   - **Posters** on the long wall opposite the gates: 440, 453, 981 (owner:
     "poster 'JOJO the idiot circus boy'"), wall sprites type 417, cstat
     464, repeats 88-104, shade 0-9, centres 1.55 bodies over the floor,
     one every 2,560; 823 (NO ADMITTANCE) over the booth door at 1.75
     bodies, repeats 64. **[E1M2 spr 484/485/486, 224]**
   - **Benches** (two, along the poster wall): seat 2,816 by 1,024 raised
     6,144 z (0.36 body), top 34; back 3,072 by 256 behind it raised 8,192
     z (0.48 body), top 300 ("carpet"). **[E1M3 s4/s11 seat, s3/s15 back --
     those are carriage benches; benches in a hall are INVENTION]**
   - **Luggage: none.** No luggage tile or use was found; I have looked at
     no tile that could carry it, so none is recommended.

5. **Platform.** 2,048 wide by 16,384 long (3.5 by 28 m), at the hall's
   floor, 0.85 body over the bed. Floor 281 shade 9. Edge face (the lower
   wall seen from the track) 174 (unnamed: brown vertical planks), pal 11,
   cstat 2, shade 38. **[E1M2 s272/w381; width from MISKSTAT s2 (2,048)
   because E1M2's 1,024 is one body-and-a-half]**
   - **Canopy** over the 10,240 that front the hall: ceiling 67 at 2.96
     bodies, shade 26. The remaining 6,144 of platform open to the city's
     sky. **[E1M2 s272 ceiling; the open part is INVENTION]**
   - **Columns** on the hall/platform line: 512 square, every 2,560, faced
     115 (unnamed: riveted pilaster strip), shade 24-49. **[E1M2 s272
     notches w2070-w2088]**
   - **Gates** between columns: wall sprites tile 1044 ("grate"), cstat
     8413, repeats 64 by 96, shade 32, angle along the line. Leave two
     bays without a gate as the way through. **[E1M2 spr 473-477; the open
     bays are an adaptation -- E1M2 gates every bay]**
   - **Nameboard** over the platform, 128 from the edge: a sector 128 by
     4,224 whose ceiling is 8,192 z (0.48 body) below the canopy, i.e. its
     underside 2.48 bodies over the platform; its track-facing wall 68
     with GRAVESEND in letter sprites (G 3814, R 3825, A 3808, V 3829, E
     3812, S 3826, E 3812, N 3821, D 3811; cstat 208, repeats 104 by 104,
     spacing 384 -> 3,456 long), back wall 68. **[board: E1M2 s214 (646
     face, 68 back, 128 by 4,224 = exactly one repeat of 646); lettering
     instead of 646 "MISKATONIC STATION" is our change -- ask the owner
     whether 646 may stand in]**
   - **Platform end** away from the hall: three steps down to the bed, each
     4,779 z (0.28 body) and 512 deep, 2,048 wide, faced 174, so a player
     who drops onto the track can climb back. **[INVENTION; a 14,336 z
     edge is over twice the step allowance]**

6. **Track cutting.** Bed 3,584 wide (6.1 m) by 16,384 + 8,192 (the run
   past the platform end), floor 1129 ("railway track with sleepers, floor
   texture"), floor_stat 4, floor_y_panning 176, shade 26, open to the
   city's sky (Gravesend's 3491, not E1M2's 3678 -- one sky per outdoor
   space). Far wall 421 ("wall of grey bricks") shade 32-42, rising 3.9
   bodies over the bed. **[E1M2 s34]**
   - **Enamel plaques** on the far wall facing the platform: tile 420
     (NORTHBOUND EXPRESS), type 417, cstat 464, repeats 96 by 96, shade 19,
     2.11 bodies over the bed, two, 6,000 apart. **[E1M2 spr 593/611]**
   - **Terminus end** under the hall's end: a buffer block across the bed,
     1,024 deep, raised 8,192 z (0.48 body), faced 470 ("riveted metal
     plating"). **[INVENTION: no buffer stop exists in the corpus]**

7. **The line leaving.** At the far end the cutting becomes a tunnel: three
   sectors, each 3,584 wide and 8,192 long, ceiling 253 ("dressed/worked
   stone") at 3.92 bodies over the bed, walls 80 ("weathered vertical stone
   wall with hints of moss"), floor 1129 continuing, shades 45, 56, 63
   (floor, ceiling and walls alike). **[STATION s131 (45), s135 (56), s137
   (63)]** The last sector bends 30 degrees and ends in a wall at shade 63,
   so no end wall is seen face-on. No kill sector. **[the bend and the
   sealed end are INVENTION; STATION ends in a chasm s139, E1M2 in a 618
   kill sector s286 -- we refuse both]**

8. **The train: two cars standing at the platform.** Car side flush with
   the platform edge line, the pair together 25,600 long (more than the
   platform, so the train's rear end stands in the tunnel mouth's shadow).
   - **Car A (cannot be entered):** one sector 4,096 by 12,800, floor raised
     to the car roof (bed - 20,480 - 32,768 - 4,096: 3.4 bodies over the
     bed), roof tile 438 ("embossed metal floor"); every face a lower wall
     of 1665 (unnamed: train livery -- grey roof, green band, grey panels,
     ribbed skirt), cstat 4, repeats 88 by 8 on the long sides, shade 20.
     **[STATION s128/w(125->128)]**
   - **Car B (entered):** outer 4,096 by 12,288, hull walls 256 thick. Floor
     1.21 bodies over the bed, interior 1.93 bodies high (32,768 z), ceiling
     455 ("moss-green surface material") shade 14, aisle floor 308
     (unnamed: rug) shade 20, bay floors 300 ("carpet") shade 16, inside
     walls 109 ("plaster wall with top beam and carved base") shade 12-24.
     **[E1M3 s6 (308, ceiling 455 at 1.93 bodies), s2/s3 (300), s22 walls
     109; E1M3's compartment floor is 305, which I have not looked at, so
     300 stands in; width from STATION s128]** Outside faces 1665 / 1666.
     - **Windows:** one per seating bay on both sides, 2,048 long, sill 0.48
       body, head 1.69 bodies over the car floor; the hull wall over the
       opening a masked wall 266 ("glass or metal sheet (mask)"), cstat 213,
       blocking. **[E1M3 s164/s165 and walls 289 -> 54..57: over 266, cstat
       213]**
     - **Door:** a 1,024 opening in the platform-side hull at the car's
       third point, no leaf, sill = car floor (0.36 body above the
       platform). **[INVENTION: E1M3's doors s164/s165 are 614 slides; we
       leave it open]**
     - **Seating bays** (four, 2,560 long, either side of a 1,024 aisle):
       seat 1,280 by 1,024 raised 6,144 z (0.36 body), top 34; back 1,280 by
       256 raised 8,192 z (0.48 body), top 300. **[E1M3 s4/s11 and s3/s15,
       scaled to the narrower car]**
     - Name on the car: none for now. **[Not 1667 "Phantom" / 1407 "666":
       another train's name -- see notes]**

## The mechanism: nothing moves

The train stands; no XSECTOR on any of its sectors. Should the owner later
want a train that arrives or leaves, the exemplar is MISKSTAT s90/s74:
kSectorSlide (616) blocks shaped as the car, rx 109, busy_time_a 25 (2.5
s), markers sprites 101 (kMarkerOff, in s90) / 102 (kMarkerOn, at the
track's far end), sides 1665/1666 -- and the platform must then be kept
clear of the slide path. E1M3's moving-ground recipe (s96: pan_floor 1,
pan_always 1, pan_velocity 128, pan_angle 512, drag 1, wind 255 at 512,
wind_always; ends s0/s1/s94/s99 type 618 damage_type 3) is for a ride, not
a station, and is NOT used here.

## Lighting (shade per room)

| room | floor | ceiling | walls | exemplar |
|---|---|---|---|---|
| entrance passage | 51 | 51 | 39-51 | E1M2 s103/s104 |
| stair | 12 | 26 | 15-39 | E1M2 s105 |
| booking hall | 9 | 26 | 24-39 | E1M2 s271 |
| booth behind the grille | 20 | 20 | 24 | INVENTION (a step darker) |
| platform under canopy | 9 | 26 | 24-49 | E1M2 s272 |
| platform open part | 9 | sky | -- | INVENTION |
| track bed | 26 | sky | 32-42 | E1M2 s34 |
| tunnel 1 / 2 / 3 | 45 / 56 / 63 | same | same | STATION s131 / s135 / s137 |
| car B inside | 20 | 14 | 12-26 | E1M3 s6, s22 |
| car A / B outside | -- | -- | 20 | STATION s125 -> s128 |

## What each view must show

- **From the street door:** up the stair, the lit hall, and straight ahead
  through an open gate bay the bright cutting with the green livery band of
  car B filling the bay; the clock above that bay. If the door frame shows
  only the hall's back wall, the axis is wrong. **[E1M2 frame "room_w":
  columns, gates, sky and a plaque through the gates]**
- **From the concourse (hall middle):** the rhythm of columns and gates
  along one whole long wall, the train's side behind them, the counter with
  its grille and TICKETS to one side, posters and benches behind. **[E1M2
  s271 study frames]**
- **From the platform:** looking along the track toward the tunnel -- rails
  (1129) converging under the sky into a black mouth, the train's side to
  one hand, the nameboard overhead, the brick far wall with two blue
  plaques; looking back -- the buffer block under the canopy and the hall
  behind the gates. **[E1M2 frames "track_n"/"tracks_s"; STATION frame
  "tunnel"]**

## To check in frames once built

1. The 0.36-body step from platform into car B is climbable in the engine
   (walk it; the paper allowance is ~6,659 z).
2. 1665 on car A's 3.4-body face: does the livery read about 2 bodies tall
   with the rest dark, as STATION's does under its sky?
3. GRAVESEND letters legible at repeats 104 on a 0.48-body board seen from
   the platform's far end.
4. Owner: lettering vs 646, and every [INVENTION] above.
