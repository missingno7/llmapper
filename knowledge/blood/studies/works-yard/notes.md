# Study: works-yard

Written 2026-11-26 from the references the E4L1 remake looked at for its
storm quarry (`projects/duke-e4l1-remake`, place `quarry`; its design and
choices are in the project's DESIGN.md), moved to the shelf so the next level
finds them.

## What I want to build

The yard of a works at night: rough ground and rock, a facility front with
a framed service door, practical lamps, and lightning over it.

## Where Blood built it

- **E1M5, sector 392** (seed `E1M5:392!`), Hallowed Grounds: a dark open
  court, 20 by 31 m, under parallax sky 3678 (the owner names the tile "dark rock / scorched ground"; as a parallax ceiling it draws the clouded night of the frames), walls of brick 90 and dark
  stone 512, floor 278. It flashes: see below.
- **E1M4, sector 114** (seed `E1M4:114!`), Dark Carnival: an industrial
  yard of rock face 449, earth 270 and rusted metal 255 with riveted metal
  thresholds 200, under the same sky.
- **E1M4, sector 331** (seed `E1M4:331!`): a yard edge by the railway, of
  crates 95/452 and riveted cladding 2453 on plank floor 67.
- **E3M5, sector 2** (seed `E3M5:2!`), Spare Parts: not a yard but the
  works door seen from inside: a framed metal door 495, cladding 489, a
  hazard-striped frame and slab plating 491, floor and frame distinct.

## What makes it read as that

1. **Dark at rest, lit by moments.** E1M5's sector 392 is a shade wave:
   `shade_wave` 8, `amplitude` -17, `shade_frequency` 5, floor, ceiling and
   walls, `wait_time_a` 20 and a return, listening on channel 108. Sprite
   86 is a kGenTrigger (type 700, `busy_time` 45, `data_1` 20, tx 108); the
   same channel reaches kGenSound sprite 88 (type 708, `data_2` 255, the
   distant thunder; `catalog show sound:255`). That is Blood's lightning:
   a generator, shade waves and a sound on one channel.
2. **Rock and earth against metal.** In E1M4 the ground and cliff are
   rough (449, 270), the made things are rusted metal (255) and riveted
   thresholds (200): geology and works never share a material.
3. **The door is framed.** E3M5's door 495 sits in a frame of its own
   material, on a floor that differs from both.

## Sizes

- E1M5's court: 184 M of floor, the sky 12.9 m up. E1M4's yard: 50 M,
  7 m. A yard is several rooms' floor under one sky.

## What I will transcribe

- Lightning as E1M5 wires it: a type 700 generator, shade-wave receivers
  on the exposed sectors (wave 8, amplitude about -17, with a return), and
  a type 708 sound 255, all on one declared wire.
- Rough stone or rock for ground and cliffs, rusted or riveted metal for
  the works, a framed metal door at the entrance.

## What I will not do, and why

- E1M4's fires and carnival boards: they belong to the carnival.
- Light a night yard evenly: E1M5's resting shade is dark, and the flash
  is what shows the yard.

## What I still do not know

- How `busy_time` and `data_1` of a kGenTrigger set the interval and its
  spread in seconds; read NBlood's generator before timing a storm by them.
- How Blood draws rain or a visible bolt; neither seed has one.
- Parallax sky 3678 is drawn in 16 panels: a map that wears it needs E1M5's
  sky bits and offsets, or its first panel alone draws as broken bands.
