# Study: ritual-place

## What I want to build

The place where the Cabal does its summoning, under Gravesend: something the
chamber is arranged round, a congregation, a victim, and a thing that answers.
(`projects/blood-city/references/cabal-rite-design.md`.)

## Where Blood built it

Looked at in `tools.gallery` sheets of fifty places: the campaign's, Death
Wish's and the community's, found by their furniture (candles, bodies, gore,
cultists and demon faces within six metres of each other) and not by their
names. The frames are not committed; make them again with
`python -m tools.gallery E1M7:41 E6M6:213 DWE2M4:206 SSR3:230 ... -o work/gallery/ritual`.

| place | what it is |
|---|---|
| **E6M6:192/213** | THE ritual room (the wiki calls it that): a long six-sided pool, its stone rim 8,192 high (half a body) and two bodies wide, tile 43 on top and 409 round it; six candles (938, type 32) stand on the rim; the water is 4,096 under the rim, floor 280 in pal 2 with four translucent 1036 sheets over it; ten cultists down both long sides, facing it; at the end a horned-skull tapestry (267, breakable, type 417) over drapes (159) and two standing candelabra; a torchlit loft looks down along it; two ambients (4 and the undead praying, 220) at the rim |
| **E1M7:41** | the altar of stone: a three-step hexagonal dais on grass, a slab two bodies high with a body crucified on it (370) and blood run down it (915) onto the dais (732); eight cultists in a ring; a stair runs round the whole arena, so it is seen from above on the way in |
| **E2M9:118** | the campaign's own circle, found by the composition reader: eight cultists 2,000 to 2,200 from a bonfire, 45 degrees apart, every one facing it; the fire in its own small sector in a sixteen-sided patch of earth |
| **DWE3M9:117** | a round stone rim full of white fire in a red room, a ring of small red lights on the floor round it, a book open on the rim |
| **E2M4:503** | five cultists round the hotel ballroom's key, facing it, under a balcony |
| **SSR3:230** (community) | the same thing in an engine room, the nearest to ours: an octagonal hall of riveted steel (194) 5.6 bodies high; an octagonal pool of blood with bones (243, slowly panned) inside a rim 3,072 up; a key hung over the pool under a chained winged carcass; candles on the rim, on two crates and on the floor, every one a different size (repeats 64 to 96 by 40 to 88); thirty-two splashes (904) up the walls; gargoyle on a bracket; heartbeat (60) at the pool, machinery (8) round it |
| **DWE2M4:205-207** | a drum of brick 26,624 high in a sixteen-sided moat; a giant stone hand on it (2348) inside a ring of twelve candles; shooting the hand (type 416, `tx` 155) lets four phantasms out of it (four kMarkerDudeSpawn, data1 210) |
| **DWE3M6:840** | a mouth: a bay window ringed with stone teeth above and below; the pit behind it is red and something two-headed sits in it. Teeth are triangular sectors, floor slope -5,376 over 512, tile 273 |
| **DWE2M6:170-184** | a mouth to walk out of: the nave's door is a pair of jaws, the lower teeth triangles 256 x 384 sloped -5,120, the upper hung with ceiling slope 5,120, a red ramp for its tongue; rows of candelabra (580) lead to it |
| **DWE1M4:642** | a congregation of painted cultists (2870, type 0) in pews before a round window lit red with a black figure standing against it; two at the front break when shot |
| **DWE1M9:198**, theatre stalls | people who do not move, until some of them do |
| **E4M8:20** | a round pit of light under an oculus, a statue facing it across the room |
| **E2M4:564** | a secret chapel: one long altar table against the wall with the goods of it: book, three candles, skull, red candles, bottle |
| **E6M8:84** | four guards die and the room's centre column lifts its skirt (kSwitchCombo counting deaths) |
| **E1M5** super secret | an altar whose skull switches stop the chant heard all over the level (ambients 59 on rx 159) |
| HALL:135, ratme1m7:254 (community) | a niche of candles on three terraces, dozens of them: one thing made of many |
| oldmanor:335 (community) | a bath ringed with candles and a body in it |
| HIDDTEMP_:185 (community) | the goat rose (264) as a disc on the wall; a glow drawn round each candle with a translucent sprite |
| CULT:458 (community) | a carved slab with a body, a candelabrum and a priest behind it, a flayed torso in a frame (611) above |

## What makes it read as that

1. The thing in the middle is made of SECTORS: a rim, a dais, a drum, a moat.
   Our circle had none, and no arrangement of sprites on a flat floor read.
2. The candles stand on that thing and not round it on the floor, and no two
   are the same size.
3. Somebody is FACING it. Bodies arranged round a point say what the point is
   for before the point does.
4. There is one wall the room is turned to, with a face on it: tapestry, lit
   window, idol, mouth.
5. It is dark, the light is the fires' own, and the red is the pool's.
6. The place is seen whole before it is entered, from a loft or a stair.
7. Something is done there, and something answers.

## Sizes

E6M6's room 11 x 21 m and 8 m high, its pool 2 x 4 m; E1M7's arena 31 x 40 m;
SSR3's hall 12.5 m across and 5.6 bodies high; DWE2M4's moat 8 m across, its
drum 3.5 m. Rims are 3,072 (a step) to 8,192 (half a body). Teeth: 256 to 512 at
the base, as long again, sloped so the point stands 10,000 to 12,000 over it.

## What I will transcribe

* the rim, the blood and the candles of SSR3 and E6M6; 1130 for the blood
  itself (a red liquid tile, pal 0, where E6M6 tints 280);
* E1M7's and E6M6's people: backs to the way in, round the thing;
* the teeth of DWE3M6 and DWE2M6, round the well and at the mouth;
* DWE1M4's black figure against a lit round window, with the goat rose 264;
* E6M6's beast-priest wiring (E6M8) and E1M5's chant that stops;
* torches on a wire (CASTLE23), put out where it lights them.

## What I will not do, and why

* A pentagram as a sprite (825): it is the size of a plate. The sign is cut in
  the floor so it can be read from the gallery.
* A thin sign. From a body over the floor it is seen at a grazing angle: lines of
  176 at the stone's own shade read as a dark V. At 384, over the whole floor and
  forty shades brighter than its dead state, it is read from the door.
* Lava: the place is water's end.
* A key or a gate on the way in: it is a place to find.

## What I still do not know

* How the beast-priest's fight plays in a ring this size.
* Whether a player who falls into the well before the priest dies is confused
  by a floor of blood that holds them.

## Engine facts found on the way

* `kDecorationTorch` (30) draws its picnum + 1 while `state` is 1 and smoke when
  it is 0; `kDecorationCandle` (32) glows at 1 and is dull at 0, but its art (938)
  keeps its flame: a candle "out" still looks lit, a torch does not
  (view.cpp:2922-2938). Both take a wire by the default branch of
  `OperateSprite`. In 1,598 maps 70 torches in 19 maps and 25 candles in 5 are
  on one; CASTLE23's fourteen come alight two at a time down a hall, each pair
  on its own wire from a one-way switch that waits a little longer than the last.
* `kTrapZapSwitchable` (456) does nothing in the engine but show and hide its
  sprite (and block while shown): triggers.cpp:393-409. Two uses in all the
  maps, both in TUTORIUM with art 1156. It is how a sprite of any art appears
  and disappears by wire without the modern extensions.
* A sprite lower than its sector's floor is cut by it, so a figure may stand
  half out of a pool; cstat 8192 takes it along when the floor moves.
