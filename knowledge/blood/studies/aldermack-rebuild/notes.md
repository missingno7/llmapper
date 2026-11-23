# Study: aldermack-rebuild

## What I want to build

The Aldermack rebuilt: a landmark playhouse read at once from its door. Raked
plush stalls with the dead still in them, a framed and curtained stage with
one performer in the light, boxes and a dress circle, a front in lights.
The plan is `projects/blood-city/references/aldermack-design.md`.

## Where Blood built it

The older `theatre` study searched the campaign and curated maps by evidence,
and the 1,500 community maps only by file name; it found three. The owner,
2026-11-23: "I think we can find better examples in existing levels". This
scan (`experiments/room_scan/scan_rooms.py`, ranked by `rank.py`, rendered by `pose_sectors.py`) read all 1,693 maps for parallel seat strips,
sprite grids, wide curtains in tall rooms, lettered words and theatre
posters. About forty rooms were rendered; `posed/` has the sheets, rendered locally and not committed.

- **THESLUMS.MAP (community), the cinema: the exemplar for the house.** From
  its door (s549 looking at s543; `posed/pose-5.png`): a chevron-carpet aisle
  (s508) runs between two blocks of benches (s509-s540) down to a lit, framed
  screen in black. Bloodied dead sit on the benches.
- **HUNT.MAP, s672-s675: the exemplar for the performance.** A small stage
  with a drape wall; a mime stands in the light and his black SHADOW is on
  the drape behind him; a trick table, a balloon and a sack each throw
  theirs. Fourteen robed figures stand watching.
- **AFTSHOCK.MAP, s269 with s223-s238: Duke's, not Blood's.** The owner,
  2026-11-23: "AFTSHOCK is actually conversion of E1L1 map from Duke3D".
  Measured, so are melte1m1 (its copy) and FORDTHEA
  (`knowledge/blood/duke-conversions.json`: 73, 72 and 141 distinctive
  sectors of E1L1's 325), so the three are ONE source, a well-known cinema
  that is not to be rebuilt. The proscenium's exemplar is SCHOOL_'s
  (study `theatre`). What is taken from AFTSHOCK is an idea, at our own
  sizes: a dark frame with bright drape legs, which the converter drew.
- **EU11_.MAP, s346/s349: the exemplar for footlights.** Ten flames 1,024
  apart along the stage's front edge; a stage face of upright panels (149);
  drapes 28,672 long behind; tied-back drapes (146, masked) at the entrance.
- **NUTHOUSE.MAP, s263 and its neighbours:** rows facing a screen, with
  curtained openings high on the side walls (`posed/pose-3.png`): the only
  boxes I found.
- **REALM4.MAP, s181:** a red boudoir: drape walls floor to ceiling, hanging
  chandeliers, standing candelabra, framed paintings, a round dais. For
  the boxes, the circle and the star's dressing room.
- **CULTHQ.MAP, s27/s8:** many rows with a red runner between.
- **TIMS61.MAP, s54:** a red-panelled split-level hall with drape walls.
- **THESLUMS.MAP, s484:** the street front: CINEMA in lit discs, read
  downward, hung over the street; beside it a framed picture on a pole.

Looked at and dropped: BLUDTOWN s445 (a church), DWE3M5 s382-s423 (a hall of
armour behind a draped railing), TEDE1M7 s272 (a void), TEDE1M5 s28 (a
corridor of posters, good for framed posters in glass), c1t5 s255 (a drape
room of sofas), hallfame (a museum), DACOM1, OMEGAMAN, FOULKEEP, CAFEDRAL.

## What makes it read as that

1. **The whole composition is one look down an aisle.** THESLUMS: near-black
   walls and ceiling, rows as silhouettes either side, the carpet a bright
   path, the frame the only strong light, at the end and above eye level.
2. **The dead are the audience.** Tile 2330 (a bloodied man sitting) on the
   bench tops, a few and not in every seat, one collapsed at the front.
3. **Light has a source you can see.** A run of flares (2446, then six 624s
   growing and dimming: shade -73, -23, -19, -10, +5, +12) down the aisle
   ceiling IS the projector's beam.
4. **The performer's shadow.** HUNT's silhouettes make a spotlight with no
   light at all: the same tile again, black, flat on the cloth.
5. **A proscenium is a dark frame with bright legs.** AFTSHOCK (Duke's): the opening
   is the darkest thing in the wall and the drape legs the brightest.
6. **Seats are plush, not slabs:** damask cushions (260), a lighter back.

## Sizes

| Thing | Exemplar | Record |
| --- | --- | --- |
| bench pair | THESLUMS s515/s516 | 2,304 long; seat 384 deep, floor and front 260 at shade 42/37; back 128 deep, 4,096 over the seat, faces 409, top 260 at 47 |
| pitch, rake | THESLUMS s509-s523 | 1,024; 2,048 a row; 7 rows; block floor s524 2,816 wide, 8,192 long |
| aisle | THESLUMS s508 | 1,536 wide, carpet 471 at shade 38, ceiling 364 at 54 |
| house height | THESLUMS / AFTSHOCK | 61,440 / 106,496 |
| front floor | THESLUMS s543 | 7,168 x 1,280 before the screen, carpet 390, walls 159 at 54-57 |
| seated dead | THESLUMS sprites 771, 773, 775 | 2330, type 416, data_1 8, data_2 16, data_4 318, cstat 384/388, repeat 40, shade -6 |
| blood and fallen | THESLUMS 769-772 | 3791 and 2334 (416), blood pool 1417 flat (cstat 674, pal 2) |
| beam | THESLUMS 736-751 | 2446 cstat 210 repeat 56 shade -73 pal 5; 624 cstat 210, repeat 42 to 64 |
| stage | HUNT s674 | 4,352 x 1,536; floor 21 at 0; 10,240 over the hall; back wall 146 at shade 0, sides 20 at 20; hall at 45 |
| performer, shadow | HUNT 1665, 1669 | 2400 cstat 129 repeat 48 shade -8; its shadow 2400 cstat 208 shade 63, repeat 56 x 64, 4 units off the cloth, 1,019 behind and 627 to one side |
| proscenium | AFTSHOCK s224-s238 | opening 5,056 wide, 45,312 high; legs 512 wide each side (146, masked 917/925); floor 20; frame 2453 |
| stage depth | AFTSHOCK s223-s225 | 1,088 over all, 8,192 over the house floor |
| footlights | EU11_ 519-528 | 3566 (the owner's "large flame / bonfire"), cstat 128, repeat 16 x 48, 1,024 apart, one row along the front edge |
| stage face | EU11_ s346 | 149, 2,048 high |

## What I will transcribe

THESLUMS's bench pair, pitch, rake, aisle carpet, seated dead (with its gib
record) and beam of flares; HUNT's performer and shadows; SCHOOL_'s
three-bay frame and drape legs (study `theatre`); EU11_'s footlight row and
panelled stage face; REALM4's drape walls and candelabra in the boxes; the
CINEMA sign's lit discs for ALDERMACK over the street.

## What I will not do, and why

- Not copy a room: our plan, sizes and story are our own; these are records of parts and how they are arranged.
- Not a screen: a playhouse has a curtain. THESLUMS's frame becomes the lit, framed opening.
- Not THESLUMS's absolute dark: the owner's city is seen in daylight and a player must find the doors; dark, with sources.
- Not fourteen live cultists on the floor: the watchers are the dead, and a few wake.

## What I still do not know

- How NUTHOUSE's side boxes are reached (its house sector s352 is too dark to read in a frame).
- Whether the owner reads 2330 as a seated patron from across the house: he has not named it.
- AFTSHOCK s238's curtain in motion: not simulated here.
