# Study: station

Written 2026-11-18. Seeds run through `tools.study`: `E1M2:271!` (the
waiting hall), `E1M2:34!` (the track cutting and its wagon),
`E1M3:6!` (a carriage interior on the Phantom Express) and
`maps/blood/community/STATION.MAP:125!` (a platform beside a standing train;
community map STATION, tier S). Every frame was rendered through
`look.as_played`; the automatic corner frames were supplemented by custom
poses (scratch folder `study_station/render.py`, montages `r_e1m2`,
`r_e1m3`, `r_station`, `r_misk`). Also measured but not seeded: community
MISKSTAT ("Miskatonic Station", tier S; its frames came out almost black at
brightness 0), DWE2M10 (a second moving train), TRAIN__, FCZug (letters
"METRO", "ZUG").

## What I want to build

A railway station on the outer edge of Gravesend, in the free space behind
one of the edge facades that are now empty shells. The player comes off a
city street through a doorway in the facade, crosses a booking hall, steps
out onto one platform beside a track, and finds a train standing there.
The line runs out of the station into a tunnel or into the dark, where it
cannot be followed. In the first second a player should read "station":
rails at the foot of a platform edge, a long straight perspective, a
nameboard over the edge, and a train.

## Where Blood built it

Found by sweeping the campaign, the curated maps and the 1,500 community
maps (`bloodmap.patterns.list_corpus_maps`) for floor tile 1129 (owner:
"railway track with sleepers, floor texture"), panning floors with
pan_velocity >= 64, and letter sprites 3808-3833 spelled into words.

- **E1M2 "Wrong Side of the Tracks"** -- the campaign's station. A track
  cutting s34 (kSectorSlideMarked 614, 3,584 wide by 61,952 long, floor
  1129, open sky 3678) between grey-brick walls (421); a platform s272
  (1,024 wide by 12,288, floor 281) with a plank canopy (ceiling 67); a
  waiting hall s271 (5,120 by 12,288, floor 281, ceiling 67) behind a row
  of iron gates; a stair s105 (2,048 by 4,096, sloped heinum -1,280) up
  from a passage s104/s103 (3,328 wide in two 614 halves, ceiling 120
  "clay tiles") off the street s207. An open wagon (s7, s8, s9, s10, all
  kSectorSlide 616 on markers 294/295 and 300/301) stands on the track and
  slides away (busy 120 = 12 s) when channel 111 fires; the track ends in
  a dark covered run s264/s267/s291 and a kill sector s286 (618,
  damage_type 3).
- **E1M3 "Phantom Express"** -- the campaign's moving train. Five cars
  stand still on track sectors 82-93 and 230-239 while the ground s96/s98
  and the ballast s289 scroll past. Seeded the lounge/bar car around s6.
  (Recorded already as idea card E1M3-96; I re-measured it.)
- **STATION (community, tier S)** -- a two-track station yard (s122, s123,
  s127 floor 1129, at the SAME level as its platforms s124/s125/s126,
  floor 276), with a standing car "662 Phantom" built as a solid block
  s128 (4,096 by 12,800) faced in the livery tile 1665, a rear balcony
  with balusters, a ticket-less hall s104/s105 (ceiling 253) and the line
  leaving north through a tunnel s131-s140 that darkens and ends in a
  chasm s139 with a wrecked car s141.
- **MISKSTAT (community, tier S)** -- "Miskatonic Station": a hall s99
  (22,016 by 6,144, 3.14 bodies, floor 294, ceiling 105) with a wall clock
  (sprite 143, tile 1165) high on its platform wall; platform s2 (2,048
  wide, floor 7,168, top tile 195) over a track bed s1 (5,120 wide, floor
  25,600, tile 1129); a train that arrives and leaves as two kSectorSlide
  blocks s90/s74 (rx 109, busy 25) whose sides are 1665/1666.
- **DWE2M10** -- a second moving train: embankments s74/s75 (tile 449 pal
  9, sloped heinum -1,536) panning at 200 and the track s76-s93 (448) at
  100, drag 1, no wind, damage_type 1 and 3.

Not found anywhere: a ticket office with a counter grille, a timetable
board, benches on a platform, luggage, a signal box, a buffer stop. The
lettering sweep found TRACK A (E1M2, letters hidden below the map), METRO
and ZUG (FCZug), TRAIN (GHOSTTWN) -- never TICKETS, PLATFORM or DEPOT.

## What makes it read as that

**The rails, seen down a long straight.** In every frame that reads
"railway" the camera looks along the track: two rails converge to a dark
end. E1M2 does it with one floor tile: 1129 in floor_stat 4 (swap x/y) on
a 3,584-wide sector, floor y_panning 176 to centre it. The tile is 32 by
256 texels; swapped, its long axis lies across the track, so one repeat is
4,096 across and 512 along: one sleeper (a plank about 150 wide) every 512,
and two rails (10 texels = 160 wide) whose centres are 124 texels = 1,984
apart. E1M3 builds the track from sectors instead: rails are strips 256
wide of tile 195 (owner: "metal rail/track -- primarily the inside faces of
jambs") raised 1,024 z over the bed, 2,048 apart (centres 2,304), with
tile 170 (owner: "wooden boarding") between them and 110 ("cobblestone")
outside; the ballast beyond is 362 (green-grey grit). Both read at once as
track; E1M3's raised rails catch light and cast a lip.

**The platform edge and what hangs over it.** E1M2's platform s272 is a
strip 1,024 wide, 14,336 z (0.85 body) over the rail bed, its face to the
track tile 174 pal 11 (bottom-swapped, cst 2). Square columns 512 by 512
(notches in the platform's outline, faced 115, a riveted pilaster strip)
stand every 2,560, and between them hang iron gates: wall sprites tile 1044
(owner: "grate"), cstat 8413, repeats 64 by 96, shade 32, five of them
(sprites 473-477). Over the edge hangs a nameboard: a sector s214 only 128
wide and 4,224 long inside the platform, its ceiling 8,192 z (0.48 body)
below the canopy, so its two long walls draw as a board 2.48 bodies above
the platform: tile 646 (a painted board reading MISKATONIC STATION) facing
the track, 68 (a dark plank) on the back. On the far wall of the cutting,
facing the waiting passenger, two enamel plaques: sprites 593 and 611, tile
420 (NORTHBOUND EXPRESS), type 417, cstat 464, repeats 96 by 96, shade 19,
2.11 bodies over the rail bed.

**The waiting hall is a room of posters behind gates.** s271 is lit
(floor shade 9) under a dark plank ceiling (67, shade 26), walls of 90
("worn large bricks with moss"), 49 and 414, and its long wall carries
posters as wall sprites: 440 (TONIGHT MONKEY WRESTLING), 453 (POSSUM
GALLO), 981 (owner: "poster 'JOJO the idiot circus boy'") at 1.54-1.57
bodies, repeats 88-104, type 417 (they burst when shot); 823 (NO ADMITTANCE)
over the door to the back room. Kicking pails (3540, type 415) and gibs on
the floor. The frames: a hall opening on one long side through a row of
gates to light and sky.

**The train.** Every train in the corpus wears the same livery: tile 1665
(and 1666), a wall strip 32 texels wide of grey roof, a green band, grey
panels and a ribbed grey skirt; E1M3 also uses 1556/1557 (dark wood lower
panels). The word "Phantom" (tile 1667, a mask) and "666" (tile 1407) are
wall sprites on the cars' sides (E1M2 s7/s8: repeats 78 by 59, pal 9, 2.05
bodies over the wagon floor; STATION sprite 299: 1667 repeats 80 by 96,
pal 10). STATION shows a standing car as one solid sector s128, 4,096 by
12,800, its floor raised to the yard's sky ceiling so its faces are one
lower wall in 1665 (cst 4, repeats 88 by 8); a balustraded rear platform
and a dark wooden balcony end it. E1M3's cars are entered: outer hull 8,704
wide by 19,456 long between gangways, car floor 20,480 z (1.21 bodies) over
the ground, interior 32,768 z (1.93 bodies) high, ceiling 455 (owner:
"moss-green surface material"), floors of carpet 300/308. Windows are
openings in the hull 1,024-2,048 long, sill 0.48 body and head 1.69 bodies
over the car floor (s164/s165: floor 0, ceiling -20,480 against the car's
8,192), filled with glass 266 as a masked wall (cstat 213, translucent).
Inside the lounge car: a central carpet runner 2,048 wide (s6, tile 308),
counters 512 wide raised 0.48 body (s218/s220, floor 43) either side,
tables as raised blocks, and side compartments (s22: 2,560 by 4,096) with
benches s4/s11 (2,816 by 1,024, raised 6,144 z = 0.36 body, top tile 34,
owner: "wood ... for counter/cabinet sides") and backs s2/s3 (3,072 by
512, raised 3,072 and 8,192 z, carpet 300).

**How a moving train is done (E1M3).** Nothing moves but the floors. The
ground beside the train, s96 and s98 (11,264 by 147,456, floor 373, floor
z 28,672, i.e. 1.21 bodies below the car floor), has XSECTOR pan_floor 1,
pan_always 1, pan_velocity 128, pan_angle 512, drag 1, wind_velocity 255,
wind_angle 512, wind_always 1, under a parallax sky 3678 (cstat 67). The
ballast s289 and every rail and bed strip pan at 255 -- faster than the
far ground, which gives a parallax of speed. Every sector under and beside
the train is a damage sector (618: damage_type 3 on rails and ballast, 1
on the beds), and the four ends s0, s1, s94, s99 are zero-height 618
sectors (damage_type 3, explode) with pan_velocity 255: step off and you
are dragged backwards to your death. DWE2M10 does the same with sloped
embankments (heinum -1,536) and no wind.

**How the line leaves.** E1M2: the cutting runs on under a plank roof
(s264/s267, ceiling 67, shade 50-56) into darkness and ends in a kill
sector s286 (618, damage_type 3, shade 63). STATION: a tunnel 4,096 wide
and 3.92 bodies high, dressed-stone ceiling 253 (owner: "dressed/worked
stone"), walls 80, whose shade steps 45 (s131) -> 56 (s135) -> 63 (s137);
beyond, the track drops into a chasm s139 (floor 15.4 bodies down) beside a
wrecked car s141. Neither has a buffer stop.

**The first second.** From the platform, looking along the track: rails
converging under sky, a long brick wall with blue enamel plaques on the
far side, the platform's column-and-gate rhythm on the near side, the
nameboard overhead, and at the end the train's dark end or a black tunnel.

## Sizes

(1,024 units = 1.7 m; a body is 16,960 z, 1,060 units tall, 384 wide.)
- Track gauge: E1M2 tile 1129 rails 1,984 apart (3.4 m, 1.9 bodies wide);
  E1M3 sector rails 2,304 centres, 2,048 inside (3.5-3.9 m). Real gauge is
  1.4 m: Blood's is 2.4-2.8 times real, scaled to the player.
- Rail strip (E1M3): 256 wide (0.4 m), 1,024 z (0.06 body) high.
- Sleepers (1129): about 150 wide, one every 512 (0.9 m).
- Track bed: E1M2 s34 3,584 wide (6.1 m); E1M3 total under one track
  6,656 (11.3 m); MISKSTAT s1 5,120 (8.7 m).
- Platform over rail bed: E1M2 14,336 z (0.85 body, 1.4 m); MISKSTAT
  18,432 z (1.09 bodies); STATION 0 (platforms at track level).
- Platform width: E1M2 1,024 (1.7 m) plus the 5,120 hall open to it
  through gates; MISKSTAT 2,048 (3.5 m). Length: E1M2 12,288 (21 m),
  MISKSTAT 18,432 (31 m).
- Canopy over the platform (E1M2): 50,176 z = 2.96 bodies, planks 67.
- Columns: 512 square (0.9 m), pitch 2,560 (4.4 m). Gates between them:
  1044, repeats 64 by 96.
- Nameboard: 128 thick, 4,224 long (7.2 m), 8,192 z (0.48 body) tall, its
  underside 2.48 bodies over the platform.
- Waiting hall (E1M2 s271): 5,120 by 12,288 (8.7 by 21 m), 2.96 bodies
  high. MISKSTAT hall s99: 22,016 by 6,144 (37 by 10 m), 3.14 bodies.
- Stair from the street up to the hall (E1M2 s105): 2,048 wide, 4,096
  long, rising 20,480 z (1.21 bodies). Entrance passage 3,328 wide (5.7
  m), 3.86 bodies high.
- Car (E1M3): 8,704 wide by about 19,456 long including gangways (14.8 by
  33 m), floor 1.21 bodies over the ground, inside 1.93 bodies. STATION's
  standing car: 4,096 by 12,800 (7.0 by 21.8 m). E1M2 wagon: 3,072 by
  5,632, deck 0.97 body over the bed.
- Windows (E1M3): 1,024-2,048 long, sill 0.48 body, head 1.69 bodies.
- Wall clock (MISKSTAT sprite 143): repeats 55 by 55, 2.6 bodies over the
  hall floor.
- Posters: repeats 64-104, centres 1.5-1.75 bodies over the floor.
- Shades: E1M2 hall floor 9, ceiling 26, walls 24-49; track 26, its walls
  32-42; the dark run beyond 50-63. STATION tunnel 45 -> 56 -> 63.

## What I will transcribe

- The track as E1M2's s34: one sector 3,584 wide, floor 1129, floor_stat
  4, floor_y_panning 176, shade 26, open sky; walls 421 grey brick. For
  close-up track ends (by the platform) E1M3's sector rails: 195 strips 256
  wide raised 1,024, 170 between, 110 outside.
- The platform as E1M2's s272: 0.85 body over the bed, edge face 174, a
  plank canopy 67 at 2.96 bodies, columns 512 square at 2,560 faced 115,
  grate sprites 1044 between columns (cstat 8413, repeats 64 by 96).
- The nameboard as E1M2's s214: a 128-thick sector with its ceiling 0.48
  body lower, board face toward the track, plank 68 on the back.
- Plaques 420 on the far wall at 2.11 bodies (E1M2 sprites 593/611), and
  posters 440/453/981/823 in the hall (E1M2 s271).
- The street-to-hall rise as E1M2's s105: a stair up 1.21 bodies.
- The standing train: STATION's s128 block for the cars the player
  cannot enter, faced in 1665/1666; one enterable car after E1M3 at a
  width we can afford, floor 1.21 bodies over the bed (so 0.36 body, 6,144
  z, over a 0.85-body platform: under the ~6,659 z step allowance), windows
  of 266 glass at sill 0.48 / head 1.69 bodies, compartments with benches
  s4/s11 and backs s2/s3.
- The wall clock 1165 as MISKSTAT sprite 143 (wall-aligned, cstat 209,
  repeats 55 by 55, shade -8) high on the hall's platform wall.
- The line leaving through STATION's tunnel: ceiling 253, walls 80, shade
  steps 45 -> 56 -> 63 into black.

## What I will not do, and why

- **Not the MISKATONIC STATION board (646) as our name.** It names another
  town's station (Blood's own Lovecraft joke). Gravesend's board should be
  spelled in the letter sprites 3808-3833 (wooden letters; E1M2 sprites
  86-91 are TRACK A at repeats 104 by 104, cstat 208, pal 5), or the owner
  may allow 646 as a stand-in. Ask him.
- **Not "Phantom" (1667) or "666" (1407) on our train.** That is the
  Phantom Express; ours needs its own name or none (the harbour study
  refused 1667 for the same reason).
- **Not a moving ground set piece.** E1M3's recipe kills a player who steps
  off and needs a train you ride; a station has a train that stands. If a
  train is ever to pass, MISKSTAT's slide blocks s90/s74 (kSectorSlide 616,
  markers 101/135, busy 25) are the pattern, not E1M3's.
- **Not E1M3's car width.** 8,704 (8.2 bodies wide) is a dining hall, not a
  carriage; STATION's 4,096 is the right width for a car on a 3,584 bed.
- **Not E1M2's sinking platform.** s272 is a kSectorZMotionSprite 602 whose
  floor drops 49,152 z when the wagon has gone (rx 106); it is a trap, and
  ours must stay walkable.
- **Not kill sectors at the line's end.** E1M2's s286 and E1M3's 618 ends
  explode the player; ours closes the line by darkness and a sealed bend,
  never by death the player cannot see coming.
- **Not track at platform level** (STATION): with no edge, nothing says
  "platform".

## What I still do not know

- No ticket office, ticket window, counter grille, timetable board,
  platform bench, luggage, signal box or buffer stop anywhere in the
  campaign, the curated maps or the community lettering sweep. Each in the
  recipe is my invention and must be marked so.
- Whether E1M2's passage halves s103/s104 (614, rx 161, busy 5) are a
  sliding double gate; I read them so but did not trace the switch.
- What the 1665 car side looks like over a 3.9-body lower wall (STATION
  s128): in frames it reads about 2 bodies tall, then sky; I did not check
  whether the upper repeat is drawn or hidden by the parallax ceiling.
- Whether a 6,144 z step from a 0.85-body platform into a car floored 1.21
  bodies over the bed is climbable in the engine (it is under the measured
  ~6,659 allowance on paper; not walked).
- How MISKSTAT is lit: at brightness 0 its frames were black, so I measured
  it from data only.
- Whether the owner will accept 1129's 3.4 m gauge next to our city's
  scale, and whether he wants the name board spelled in letters or 646.
