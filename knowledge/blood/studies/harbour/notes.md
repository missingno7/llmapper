# Study: harbour

Written 2026-11-18, after the harbour of Gravesend had been reviewed blind
twice at 1/5 ("the rock is a featureless prism", "walls end flat against the
sky", "the still water tile read as grass", "a test yard, not a place").
Every frame below was rendered through `look.as_played` (control sprites
hidden); custom poses are in the scratch folder `study_harbour/render.py`.

## What I want to build

The harbour of Gravesend: a quay street with a boardwalk along the water, a
ship moored at a jetty, the sea running out to a sky horizon, and the two
ends of the quay where its buildings meet the water. It must read as a
working waterfront at the edge of a town -- something a player looks out
over from a raised edge -- not a flat yard with a green floor.

## Where Blood built it

Found by measurement: every sector over the campaign and the curated maps
with a parallax ceiling, a water XSECTOR (depth > 0 or a panning floor) and
an area over 4M. The harbours proper are all in the curated DWE maps; the
campaign gives the ship (E2M1) and the water form (E2M1, E2M9).

- **DWE3M4, seed `DWE3M4:548!`** -- the best whole harbour. A boardwalk
  promenade (s547/548, floor 28) runs north-south along the sea for ~40,000
  units, shops behind it (BAIT, GAMELAND), a moored steel ship "Phantom"
  (hull s625 and its parts s628-635, s683) reached by a level jetty (s549),
  a dirt beach run-out at sea level at the south end (s352), and a sea of
  four bands (s636, s528, s527, s856) inside a zero-height horizon ring
  (s648). Night sky 2500.
- **DWE2M6, seed `DWE2M6:627!`** -- a cove ringed by rock cliffs (s931-940,
  s612-617), a wooden town on a dirt bank (s598) edged with a plank rail, a
  jetty on piles (water s627 under it, piles s621-626) and a big ghost ship
  in palette 1 (hull s662, decks s642/s657/s660, masts as holes in s632 and
  s657, sails and flags 3558).
- **E2M1, seed `E2M1:247!`** -- the campaign's ship, frozen in ice: hull
  ~7,168 by ~40,000 (s116-s248), main deck s247/s234 of dark planks 21,
  raised decks of 120 fore and aft, crates, a black flag (3558), an anchor
  chain, a bowsprit beam over the bow, ice floes 2448 (pal 0) with ice
  cliffs 2490 (pal 0), and open water s125/s123 in 2448 palette 10.
- **DWE3M5, seed `DWE3M5:50!`** -- the rock lesson: a bay (s159, s131,
  s132) ringed by cliff facets s46-s60, and the same "Phantom" boat model
  (s65 and its parts s0-s32) moored in it.
- Also measured, not seeded: DWE3M10 s452 is a copy of DWE3M4's sea (same
  bbox); E1M6 s498 (2448 pal 0, pan 3) is a lake; E1M7 s45 is 2448 pal 5 (a
  red pool); E2M9 s49 is 2490 pal 10 shade 16 pan 5 -- the campaign's own
  instance of the DWE water form.

## What makes it read as that

**The water.** Every sea in these maps is the same recipe: floor tile 2490
(owner: "light marble") or 2448 (owner: "marble; also used as snow") drawn
in **palette 10** (blue), floor shade **28-44**, XSECTOR `pan_floor` 1 with
`pan_velocity` 10-20 (DWE3M4: 10 at angle 900; E2M1: 10 at 1024; DWE3M5:
20 at 1540), `depth` 0, `visibility` 0. Looked at, the picture is a grey
streaked stone; under palette 10 and at shade ~40 it is dark blue-violet
with long pale streaks -- ripples -- and it moves. The very same tiles in
palette 0 are E2M1's ice. DWE3M4 darkens the bands going out: 38 (s636,
nearest), 41 (s528), 44 (s527, s856).

**Why ours reads as grass.** Ours is tile **1120**, which the owner names
"green dirty water": a green mottled blob pattern, in palette 0, shade
26-32 (brighter than Blood's sea by 10-15 shades), not panning, XSECTOR
depth 7 (a wading pool), and -- the biggest thing -- only **2,048 z (0.12
body)** below the boardwalk (boardwalk s207 floor 8,192; water s208 floor
10,240). Seen from the quay it is a green textured plane at the level of
the walk, filling the frame to the horizon: a lawn. Blood's sea lies **1.75
bodies (29,696 z)** below DWE3M4's boardwalk, behind a kerb, so the eye
sees the quay's edge and a drop before the water.

**What stands at the quay's edge (DWE3M4).** Not bollards or crates -- I
found none on the promenade. Instead:
- a **kerb**: a strip 256 wide (s519, s406), raised 6,144 z (0.36 body)
  over the boardwalk, floor 21 (owner: "dark vertical planks"), faces 177
  ("wooden wall"), shade 31; on its sea side the wall drops 1.75 bodies to
  the water, seen from the sea as a dark plank bulkhead;
- **street lamps**: sprite 640 (a lamp post, mask), face-aligned, repeats
  64x64 (1.13 bodies), on the boardwalk floor 256 inside the kerb, at y
  41,728 / 46,336 / 54,016 / 58,624 -- every 4,600 to 7,700;
- **string lights**: sprite 624 (a round glow) in pairs, repeats 8x8 and
  4x4 at the same point, shade -30, palette cycling 0/7/8/10, one pair every
  256 units, their z dipping in a catenary between tall posts from 5.3 to
  2.2 bodies over the walk (sprites 285-318, 681-728);
- a **jetty** at quay level (s549, 10,240 by 4,096, floor 28) to the ship,
  its two long edges and its end the same 256 kerb (s518, s520, s429).
DWE2M6's dirt bank instead has a timber rail of two horizontal beams; its
jetty stands on piles with a lantern on each.

**How the buildings meet the water.** Never directly. In DWE3M4 the shops
stand behind the boardwalk (4,096 of planks between them and the kerb); at
the south end the boardwalk becomes a dirt beach at sea level (s352, tile
433 "dirt", shade 35, with shrub and debris sprites) under the quay's plank
bulkhead with an iron fence above it. In DWE2M6 the town sits on a dirt
bank and the cove is closed by a continuous ring of cliffs, so no end of
anything is seen against the sky. In DWE3M5 the bay is ringed by cliffs and
the town stands above them. The sea's far edge is a zero-height ring
(DWE3M4 s648: floor = ceiling = sea level 21,504, floor tile 2500 with
floor_stat 1, i.e. parallaxed): the water meets the sky in a straight dark
horizon.

**What makes a hull read as a ship.**
- DWE3M4 "Phantom" (s625): a long narrow hull 13,312 by 4,096 with a
  pointed bow (s628, sloped heinum 768), deck 2.4 bodies over the water and
  0.66 over the quay (floor -19,456 vs quay -8,192), deck tile 255 ("metal
  wall, lightly rusted") in palette 10, hull faces 381; a rusty blue gunwale
  strip (395) along the rim, a grey metal cabin (55) with a door, portholes
  and the ship's name as a wall sprite (1667, a mask of the word, palette 2,
  repeats 192x176 at 1.21 bodies) on both cabin sides, and string lights
  running up from the jetty to a post.
- E2M1: a hull 7,168 wide (12 m, 6.8 bodies) and ~40,000 long (68 m), main
  deck 1.27 bodies over the water, a bulwark round the deck (raised strips
  512 wide, 0.6 body over the deck), raised fore and aft decks, a cabin of
  49 (red-grey vertical planks with iron bands) with a door, crates as
  1,024 cube sectors faced in 452 ("smaller crate"), a round wooden mast
  stump with a torch, a black skull flag (3558, wall sprite, 64x64, shade 8,
  2.3 bodies over the deck: E2M1 sprites 156/157), an anchor chain, and a
  bowsprit beam leaning out over the water ahead of the bow.
- DWE2M6 masts: a 512 x 512 **hole** (an inner loop with no next sector,
  walls tile 20) inside the deck sector (s632 walls 4587-4590), so the
  column runs from the deck to the sky ceiling, 10.4 bodies tall; sails and
  flags are 3558 wall sprites stacked on the mast at 1.9 to 11 bodies
  (repeats 48x72 to 255x255, translucent cstat 146/154).
Ours: a plank box (67 hull, 15 rim) with a cabin box and a pole -- "a
wooden rectangle". None of the deck furniture.

**How rock is made not to look like a prism.** DWE3M5's cliffs are 8 or
more sectors (s46-s60), each an irregular polygon of 6-11 corners with no
right angles (s50: 8 corners, edges 4,000-12,000 long), each with its own
**sloped top** (heinum 512, 768, 1,024, -512, -1,280) and its own **shade**
(25, 29, 31, 32, 33, 34, 37), tops at different heights (3.3 to 9.7 bodies
over the water), floor 458 ("rock"), faces 458/433/386. In frames the
skyline over the bay is a jagged line and neighbouring faces differ in
brightness. DWE2M6's cove ring (s931-940) is the same: floor 273
("rock/cliff"), faces 458, 2.7-3.6 bodies over the water (s612: 6.5),
heinum -2,560 to 768. Ours: headlands s216/s218 are 3,584 by 6,656
rectangles with a flat top (2.6 bodies) and a smaller flat crest
(s217/s219, 4.2 bodies), one shade each (30, 26): two stacked boxes.

## Sizes

(1,024 units = 1.7 m; a body is 16,960 z, 1,060 units tall, 384 wide.)
- Boardwalk (DWE3M4 s548): 4,096 wide = 7.0 m; 33.4 m of it in one sector.
- Quay to water: 29,696 z = 1.75 bodies = 3.1 m (DWE3M4). Beach to water:
  0 (s352). DWE2M6 dirt bank to water: 4,096 z (0.24 body); ice to water in
  E2M1: 3,000-16,000 z (0.2-1.0 body). Ours: 2,048 z (0.12 body).
- Kerb: 256 wide (0.4 m), 6,144 z (0.36 body) high.
- Jetty: DWE3M4 10,240 by 4,096 (17 by 7 m), at quay level. DWE2M6 8,192 by
  4,096 (14 by 7 m), deck 1.69 bodies over the water, piles 512 square
  (0.9 m) at 2,560 (4.3 m) pitch on both long sides, 2.05 bodies over the
  water, i.e. 0.36 body over the deck.
- Ships: Phantom 13,312 by 4,096 (22.6 by 7.0 m), deck 2.4 bodies over the
  water. E2M1 7,168 by ~40,000 (12 by 68 m), deck 1.27 bodies over the
  water, bulwark 0.6 body. DWE2M6 ghost ship ~9,200 by ~27,600 (16 by 47
  m); masts 10.4 bodies.
- Lamps: 1.13 bodies tall, every 4,600-7,700 along the kerb.
- Cliffs: facets 4,000-12,000 on a side; tops 2.7-9.7 bodies over the sea.
- Sea: DWE3M4 roughly 97,000 by 177,000 inside its ring; bands' shades 38,
  41, 44.

## What I will transcribe

- The sea: 2490 in palette 10, floor_stat 4, shades 38/41/44 going out,
  `pan_floor` 1, `pan_velocity` 10, `pan_angle` 900, `depth` 0 (DWE3M4
  s636/s528/s527). Campaign precedent: E2M1 s125 (2448, pal 10, shade 34,
  pan 10/1024) and E2M9 s49 (2490, pal 10, shade 16).
- The drop: sea floor 1.75 bodies under the boardwalk, behind DWE3M4's 256
  x 0.36-body kerb (floor 21, faces 177), the bulkhead faced in dark planks.
- Lamps 640 along the kerb and string lights 624 in rep-8/rep-4 pairs,
  field for field from DWE3M4.
- A jetty on piles from DWE2M6 s621-627 (piles tile 20, lantern 693 on
  each, edge beams 68).
- A ship with deck furniture from E2M1 and DWE3M4: bow, bulwark, cabin with
  door, crates, a hole-mast to the sky, the black flag 3558.
- Rock as facets after DWE3M5 s46-s60, and a beach run-out at sea level
  after DWE3M4 s352 where the quay ends.

## What I will not do, and why

- **Not DWE3M4's night sky (2500).** The owner's rule is one sky per
  connected outdoor space, and Gravesend's is the red 3491; the sea must
  read blue under it, which is the palette-10 tile's job.
- **Not the name sprite 1667** ("Phantom") nor the "666" door sign: they are
  another map's ship. A name needs its own tile and the owner's say.
- **Not the DWE2M6 ghost ship's palette 1** (pale planks, grim reaper
  sprites 3075/3090): that is a ghost ship, ours is a moored one.
- **Not DWE3M4's underwater link** (kMarkerUpWater 2332 sprites under the
  sea): a swimmable sea needs a room-over-room pair; ours stays unswimmable
  (depth 0) and the kerb keeps the player out, with the beach as the way
  back if he jumps.
- **Not 1120 for the sea.** It is "green dirty water", E3M3's sewer/wading
  water; it may stay in the slip or a sewer, never for open sea.
- **Not a shape the eye can read as a box** for rock: no rectangle, no flat
  top, no single shade.

## What I still do not know

- How DWE3M4's string-light posts are built (I saw tall dark posts in the
  frames but did not find their sectors or sprites); and how a player gets
  from the jetty onto Phantom's deck 0.66 body up.
- Whether tile 2490 in palette 10 is acceptable to the owner as "water": his
  name for 2490 is "light marble". Its usage as sea is unambiguous in the
  corpus (and in E2M9), but this is a use to tell him about.
- Whether Blood ever put bollards, coiled rope, nets or a crane on a quay: I
  found none in these four places. Crates appear on E2M1's deck only.
- What the quay's bulkhead face is drawn with (s519's sea-side wall has
  picnum 0; the frame shows dark planks, so the face is probably drawn from
  the water sector's side).
- Whether a 1.75-body drop works with our city's quay grade without
  re-leveling the slip and the jetty; none of it has been walked in game.
