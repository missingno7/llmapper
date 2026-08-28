# Venue patterns — the anatomy of an enterable venue

Supplement to [city-norms.md](city-norms.md). Measured by
`tools/mine_venues.py` from E1M4 (Dark Carnival's attractions), E3M1 (Ghost
Town's saloon/hotel complex and shops), and DWE3M1's town interiors; full
records with sector ids in [venue-mining.json](venue-mining.json). A venue is
an interior component entered from sky-ceiling public space; anatomy is
measured, venue *names* are **interpreted** readings of the anatomy and are
marked so. This is "lightly inspired": the anatomy and staging transfer, the
carnival theme does not.

Baselines: night-street floor shade means E1M4 **+21**, E3M1 **+25** (positive
= darker); street decoration density 0.26–0.33 sprites/1M area (DWE3M1's
streets are barren at 0.08, so its density ratios read high).

## The threshold law

- Venue interiors are **as dark as or darker than the night street** on
  average (shade step street→venue: +1.7 to +33; only open-front booths go
  brighter, at −2.7 to −3.9). What sells a lit venue is not a bright room but
  **high internal contrast**: venue shade spans of 30–50+ points (E3M1 saloon
  wing: −8 to +44) against the street's near-uniform band.
- **The marquee is animated shade, not geometry**: threshold sectors carry
  xsector `amplitude`/`shade_wave` on the mouth. Every E1M4 attraction mouth
  has it (comp 60: 9 animated sectors; comps 10, 13, 14: 1–3), and E3M1's
  saloon and its neighbor carry one each. This is the cheapest signature we
  can steal — it costs zero walls.
- Signage clusters *at the doorway, on the public side*: face sprites within
  2048 units of the mouth (E3M1 complex: 39 public-side face sprites across 7
  doorways; E1M4 comp 14: 9). Wall-sprite signs are secondary (1–8).

## Venue types

### 1. Open-front booth / shop (interpreted: ticket booth, general store)

Exemplars: E1M4 comps 10, 14 (midway booths); E3M1 comp 9 (**interpreted**
store: 22 merchandise face sprites in 6 sectors at 11× street density).

- **Budget: 3–9 sectors, 21–81 walls, 9–39 sprites, 0–1 channels.**
- The front is open: doorway total width 1024–7181 (up to the whole face);
  no door sectors; interior often *brighter* than street (step −2.7).
- Counter is geometry: one platform at rise 3072–4096 z, ~0.2–0.5M area.
- Decoration is face-sprite merchandise at 3–11× street density — the
  densest sprite spend per area of any venue type.

### 2. Show tent / stage attraction (interpreted: the big top)

Exemplar: E1M4 comp 60 — the octagonal ring, 9 sectors, 56 walls, 72 sprites.

- One ring room (main-room share 0.70), fully open frontage (8 doorways,
  31k total width) closed by **rotating gate leaves: one channel fanning out
  to 9 door_rotate receivers** — the whole venue opens on one cue.
- Marquee: 9 animated-shade sectors, the heaviest on any mouth.
- Interior 17 points darker than the midway; decoration is face + floor
  sprites (49 + 23— seating, props, ring dressing), zero wall sprites.
- **Budget: ~9 sectors, ~56 walls, ~72 sprites, 1 channel (+9 receivers).**

### 3. Walk-through attraction (interpreted: funhouse / dark ride)

Exemplars: E1M4 comp 0 (25 sectors, 281 walls, 12 channels), comp 13
(destruction-staged: 6 exploder receivers), comp 28, comp 36 (booth-cluster
games hall).

- **Deep plan behind a narrow mouth**: frontage 2048–3072 against interiors
  of 14–60M — main-room-area-per-frontage 2465–29088, an order of magnitude
  deeper than the open types (1509–3434). The mouth undersells the inside.
- Room-chain staging spends channels: 4–12 per attraction, receivers split
  doors (door_z sequencing 1–4) / destruction (2–6) / sound (0–1); many
  small platforms (rise 1024–8192) as the ride's set dressing.
- Decoration 3.6–4.4× street density, face-sprite dominant.
- **Budget: 12–25 sectors, 100–281 walls, 33–72 sprites, 4–12 channels.**

### 4. Bar / saloon room (interpreted from E3M1's saloon wing, comp 5)

- 55 sectors / 278 walls / 77 sprites / 17 channels for the wing; the bar
  room proper: main room 0.18 share with **counter as geometry** (platforms
  at rise 4096, ~0.5M area) and **tables as geometry**: four identical
  1.18M-area platforms at rise 8192 z (table height ≈ 0.48 standing) — the
  card tables are sectors, not sprites. Stools/bottles/patrons are face
  sprites (73 of 77 sprites are face-aligned).
- Swing/slide door at 2–4k width, marquee sector on the mouth, shade step
  ≈ +2 with internal span 12..61.
- Channel spend leans destruction: 23 exploder/thing receivers — the bar is
  wired to break. ([[blood-city-project]] contract: venues carry the city's
  destruction set-piece reserve.)
- **Budget (bar room alone, interpreted share): ~15–20 sectors, ~90–120
  walls, ~30–40 sprites, 3–5 channels; the full wing 55/278/77/17.**

### 5. Landmark complex (interpreted: saloon-hotel; DW's mansion)

Exemplars: E3M1 comp 2 (113 sectors, 677 walls, 183 sprites, 16 channels,
7 doorways, upstairs connected); DWE3M1 comp 9 (168 / 1320 / 332 / 29).

- Not a big shop but a **braid of venue rooms sharing one shell**: main-room
  share collapses to 0.12–0.21 because no single room dominates; 6–15
  furniture-height platforms; multiple door types (z + slide + rotate all
  present); receiver mix touches everything (doors 13, destruction 15,
  spawn/sound in DW's).
- Frontage 9.6–22.6k with doorways on several faces — the complex fronts
  more than one street, which is what makes it a landmark.
- **Budget: 110–170 sectors, 680–1320 walls, 180–330 sprites, 16–29
  channels.** One per city is E3M1's dose; DWE3M1 confirms it scales ~2×
  before it eats a DWE3M1-sized wall budget.

## City contract from this supplement

- Entertainment district venue set: 1 landmark complex (the bar anchors it),
  2–3 walk-through attractions or a show room, 2–4 open-front shops/booths —
  total ≈ **180–280 sectors, 1100–1900 walls** if taken at the exemplar
  sizes, which exceeds the district norm; scale to ~60%: complex at the low
  end (≈110 sectors/680 walls) and the rest small.
- Every venue mouth gets: animated-shade marquee sector(s), public-side face
  signage within 2048 of the door, and a doorway whose width states the type
  (narrow 2048 = walk-through; open face = booth/tent).
- Counters, stages, and tables are **geometry** (rise 3072–4096 counters,
  8192 tables); everything on or around them is face sprites at 3–11× street
  density.
- Venue channel spend at city scale: complexes 16+, attractions 4–12, shops
  0–1 — consistent with the ≈50–70 city channel budget when there is one
  complex and a handful of small venues.

---

# Supplement (owner directive, 2026-08-27): shop, retail row, hospital elements

Measured by `tools/mine_room_grammar.py` from E6M1, E4M9, E3M4 (records with
sector ids in [room-grammar.json](room-grammar.json)); readings marked
interpreted as before.

## 6. Shop (E6M1 + E3M1's store, comp 9)

E6M1's retail interior (walkable space S1: 30 sectors, 300 walls, 224
sprites; sectors listed in room-grammar.json) refines the open-front type
into a full `shop`:

- **Display is geometry at two heights**: repeated 512x512 pedestal sectors
  raised 2048 above the room floor, one merchandise face sprite each (E6M1
  sectors 33/34/58: ten of one class), plus the counter at rise 3072-4096
  from the E3M1/E1M4 pattern. Tall 256-square pillar modules (rise 28672,
  sectors 51/74/76) frame the room.
- **Merchandise face sprites dominate**: 150 face vs 44 wall vs 30 floor in
  the shop space; the top prop tile (2290, x65 map-wide) repeats like stock
  on shelves. E3M1's store corroborates at 11x street sprite density.
- **Light**: interior shade median +32 with 19 animated-shade sectors in the
  shop space alone -- flicker inside, not only at the marquee.
- **Wiring warning (interpreted)**: E6M1 spends 79 user channels on 123
  sectors, mostly traps (16 dude, 9 destruction, 11 sound receivers touch
  the shop). That is ambush-house wiring, not shop wiring; take the fixture
  grammar, not the channel budget.
- **Budget (city-scaled): 12-20 sectors, 90-150 walls, 40-70 sprites,
  1-3 channels**, display pedestals x4-8.

## 7. Retail row / multi-unit grammar (E4M9, interiors only)

E4M9's mall: one concourse space (45 sectors, 1809M area) serving repeated
unit modules (11 of one 786k-area aspect-3 class; 7 more of two smaller
classes -- room-grammar.json `repeated_chamber_classes`).

- **Storefront rhythm**: 39 openings off the concourse; width median 1536
  (p90 4096), nearest-neighbour spacing median 1840 -- a mouth roughly every
  two mouth-widths. This rhythm applies to ordinary street frontage too:
  openings cluster, they do not spread evenly.
- **Units repeat and differentiate**: one plan class, different dressing --
  the unit module is ~1536x2304-3072 (aspect 3) behind a 1536-2048 mouth.
- **Vertical**: 6 stack pairs (3 true stacks) -- the mall runs a second
  storey over parts of the concourse; scaled down this is a mezzanine, not a
  floor.
- **Budget for a 2-3 unit retail row: 25-40 sectors, 180-260 walls,
  60-100 sprites, 2-4 channels.**

## 8. Hospital elements (E3M4) -- elements, not a venue

E3M4 is one large institution (434 sectors, 96 user channels -- the most
wired map measured in this project) and does not scale down whole. Judgment,
stated: **no hospital venue in Gravesend**; these named elements fold into
existing types:

- **The bed bay module**: 24 congruent 1024x1152 chambers, one sprite each,
  with 23 companion 384x1024 divider strips (sectors 42/63/65...; 41/64/66).
  A ward is a *row of geometry bays*, not a big room with sprite beds.
  Reusable in any dormitory, bunkhouse, or cell-row interior.
- ~~Signage tile 3997~~ **Correction (2026-08-27)**: tile 3997 is Blood's
  invisible marker/control tile (roomoverroom.MARKER_TILE), so its x91 count
  reads as *heavy wiring*, consistent with the 96 channels -- not signage.
- **Light**: 80 animated-shade sectors; corridors at 512-1024 clear width --
  tighter than city streets by an order of magnitude, which is why the
  register reads institutional.
- **Whole-map-scale only**: the multi-wing circulation (74 corridor
  sectors), the 96-channel wiring, the reception-to-theatre progression.

## Decision (C): shopping venue over hospital

Grounds, recorded also in the review queue: the mall grammar reduces cleanly
(a 2-3 unit retail row fits the market hall slot at ~200 walls); Gravesend's
identity already has Market Slip to receive it, while no district hook wants
a hospital; the mandatory church complex supplies the institutional register
this iteration; and E3M4 measured as elements-not-venue. The market_hall
slot upgrades to type `retail_row`; hospital bed-bay and signage elements
stay available to any interior that wants them.
