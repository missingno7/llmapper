# Study: washroom

Written 2026-11-26 from the study the E4L1 remake made of its workers'
washhouse (`projects/duke-e4l1-remake`, place `washhouse`), moved to the
shelf so the next level finds it. What that level built and why is in the
project's `notes/washhouse.md`; this page is only what Blood does.

## What I want to build

A washroom or workers' toilets in a working building: stalls, toilets,
wall urinals and a basin, dim and used, that reads as what it is from its
fittings rather than from a sign.

## Where Blood built it

- **E2M4, room 487** (seed `E2M4:487!`): a private bathroom, 6.5 by 7.7 m,
  5.4 m high: a tiled bath on a raised step, a mirror over a washbasin,
  towels on a rail, and a stone toilet in sectors 467-469. It is the
  campaign's one clear toilet built of sectors.
- Blood has no urinal and no row of stalls that we have found; a workers'
  washroom is a transcription of E2M4's fittings, not a copy of a room.

## What makes it read as that

1. **The toilet is sectors, not a sprite.** Stone 43 makes a raised bowl
   (sector 468, 448 square, 0.24 body) and a separate rear cistern
   (sector 467, 512 by 256, 0.48 body); the liquid is a lower sector
   (469, 192 by 288) floored in sewage 997, below the rim.
2. **It flushes.** Sprite 845 in sector 469 is an invisible kSwitchToggle
   (type 20, cstat 33152) with `trigger_push` and sound 369 ("Toilet
   Flushing", `catalog show sound:369`) in both `data_1` and `data_2`: Use
   plays the flush on either change. No wire, no channel.
3. **Tiles where water is.** Tile 297 (owner: "tiles") on the wet walls,
   with grey plaster 1012 above; the floor is a grey tile 299.
4. **Things of use stand in it**: the basin under a mirror, towels, a bath
   step. The fittings carry the room; there is no lettering.

## Sizes

- The toilet as a whole is about 512 by 700: cistern 512 by 256 behind a
  448 bowl. The bowl's top is a quarter of a body over the floor.
- The room is 11 M of floor (`area_M`), ceiling 5.4 m: a domestic room
  made tall, not a cubicle.

## What I will transcribe

- Toilets as stone 43 sectors (bowl, cistern, a lower liquid sector), or,
  where sectors cannot be added, as sprites of the same proportions.
- The local flush: an invisible Push toggle with sound 369 on both edges,
  standing in the bowl. It needs no declared wire.
- Tile 297 where it is wet, plaster above it, a plain tiled floor.

## What I will not do, and why

- Copy E2M4's bath, towels or mirror into a workers' room: they say home.
- Use tile 843 (a small wooden pedestal basin) for an industrial basin: it
  is domestic furniture.
- Put a sign on the door to say what it is.

## What I still do not know

- Whether Blood has a urinal anywhere (a community map may; the campaign
  does not, as far as `catalog find toilet` and the tile names show).
- Whether a toilet of sprites reads as one to a blind reader: the E4L1
  remake built one and no reader has seen it yet.
