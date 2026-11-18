# Does every sprite fit where it was put?

The owner walked the fixtures build and said: sprites partly under ground or
in space they do not fit, statues in weird places, lamps placed weirdly,
letters overlapping other sprites; and asked for a lint.

## The lint

`python -m tools.sprite_fit MAP` -- per sprite, as the ENGINE DRAWS it:

- **sunk** / **through**: the drawn bottom under the floor, the drawn top
  over a real ceiling
- **squeezed**: a face sprite with less room to the nearest wall or step
  than half its half width
- **overlap**: two wall sprites on one plane whose rectangles intersect

`--rates` prints the same numbers for any map, and the thresholds are where
seven of Blood's town maps stop, because Blood buries and overlaps a few
things on purpose. The build prints it and `tests/test_sprite_fit.py` holds
the city to the town maps' worst.

## What it found, and why each was there

1. **Sunk.** Sprites were seated by Blood's PHYSICS box
   (`GetSpriteExtents`: half above z, half below, whatever the cstat). The
   renderer's box is different (`engine.cpp`, `setup_globals_sprite1`): bit
   128 centres a sprite on its z, the tile's y offset moves it. `goods.py`
   set z to the floor: right for a bottle, whose art is offset to stand on
   its z, and half a height wrong for an urn, a plant, a pitcher. The town
   maps seat by the drawn box: their median height over the floor equals
   its bottom to within 8 units. `bloodmap.placement.drawn_extent`.
2. **Through a shelf.** A statue 17,600 tall in a shelf 12,288 clear.
   Nothing asked whether a thing was shorter than its place.
3. **Statues.** Blood stands tile 536 on a floor by a wall (E3M1, twice) or
   raised with a body of air over it (E1M2). I had six: on counters, in
   shop shelves, in a window.
4. **Hanging things standing.** A pan stands nowhere in the town maps: it
   hangs, a body up. The census had the height and the plan ignored it.
5. **Letters through pictures.** `wallplane` keyed a wall plane by a rounded
   offset; a letter 8 units nearer the room than a painting could fall the
   other side of a bucket edge and never be compared with it.
6. **Lamps.** 1.1 bodies tall (DWE3M1: 2.1), in pairs facing each other,
   half a pavement in from the kerb (DWE3M1: 512), one in front of a door;
   two chain lamps hanging from the sky.

## Trade stock (agreed the turn before)

- BOOKS: the shelf's back is the owner's "bookcase front" (32). Books are a
  wall in Blood, not a sprite.
- CLOCKS: the owner's "wall clock" (1165) on the walls. In the town maps
  every one of them is a switch wearing a clock face.
- DRAPER: the owner's "hanging clothes" (73) on the walls.
- The saloon: a chair at each table.

## What happened

`measurements.txt`, `critic.md`, `before-after.png`. Sunk 5.2% to 0;
overlapping pairs 16 to 1. A blind reviewer: "M is clearly better."

## Not done, not known

- Nobody has walked this build. The lint reads the map, not the game.
- E3M1, the campaign's city, has NO standing street lamps. The lamp rule is
  DWE3M1's (a community map); if the owner wants the campaign's street,
  the answer is fewer still.
- The lint does not know what a thing IS, so "a statue in a shop" is a rule
  in `goods.py` (`FLOOR_ONLY`), not a lint finding.
- An enemy's picture in the map is not what the game shows; the reviewer's
  "torso sunk in the floor" is that, and unverified.
- Light-pool lamps stand where a pool is, not at a kerb.
- The final build was not reviewed blind.
