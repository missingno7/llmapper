# Study: ratdogs-stand

Written 2026-11-20, for the owner's ruling on Foundry Ward's works canteen:
"canteen should look more like a canteen" and "I would give it some unique
style, like rat dogs (similar to E1M4)". Seeds `E1M4:171!`, `E1M4:167!` and
`E1M4:170!` are the stand's sign strip, grill and kitchen. They are too small
for `tools.study`'s automatic cameras (no standing point a body and a half
clear), so the frames were taken by hand from the midway, s320, at
(24180, 39200) and (24180, 40400) looking north. I looked at them myself; no
blind reader has.

## What I want to build

A works canteen that is a rat-dog stand. In its first second a player should
read "they sell food here, and the food is rats", from the yard, before going
in.

## Where Blood built it

E1M4 (Dark Carnival), on the midway s320. The stand is three sectors set
into a striped booth front:

- **s171, the sign strip**: 0.3 m deep, in front of the hatch. It carries
  the word RATDOGS in seven letter sprites (3825 3808 3827 3811 3822 3814
  3826), at repeat 72, palette 12, shade 48, pitched 1.44 drawn widths
  apart, about two bodies above the midway. Each letter is a kThingObjectGib
  (416): the sign can be shot to pieces.
- **s167, the grill**: 2,048 by 512, its floor 8,192 above the midway and
  16,384 under its ceiling. Floor 376 (rusty ribbed iron), ceiling 255 at
  shade 63, walls 255. It is a **kSectorDamage (618)** with damage_type 1
  (burn), data 30, and a shade wave (amplitude -3, frequency 5, wave 6,
  shade_always, on floor, ceiling and walls): a grill that glows and burns.
  On it: rats 1743/1744 at repeat 24, three steam columns 754, and four
  framed fans 2548 laid flat on its ceiling (cstat 161).
- **s170, the kitchen** behind it: 3.5 m square and 3.5 m high, floor 438
  (embossed metal), ceiling 568, walls 255 with 2453 (riveted cladding) on
  the face over the grill; a fluorescent tube 796 flat on the ceiling, two
  life-essence hearts (type 109, tile 2169) on the floor and a tommy
  cultist (201) as the cook.

## What makes it read as that

From the frames, in the order a player meets them:

- **The word.** RATDOGS in dark brown letters over the hatch: the joke is
  carried by the sign.
- **The hatch frames the food.** A wooden-framed window at half a body,
  and on its sill the grill with rats lying on it and steam rising off
  them. The food is the only lit, moving thing in the frame.
- **The kitchen is dark metal**, seen behind the grill: it says "back of
  the stand", not "room".

## Sizes

- The hatch: 2,048 wide (3.5 m), sill 8,192 (half a body), opening 16,384
  (one body).
- The kitchen: 2,048 by 2,048, 32,768 high.
- The sign: seven letters over 1,241 units, two bodies above the floor.

## What I will transcribe

- The word, in its own look: `wallplane.STYLES["ratdogs"]` (72, palette 12,
  shade 48), over the hatch on the works face.
- The grill: s167's floor, ceiling, walls, its 618 type with its damage and
  its shade wave; rats, steam and fans on and over it.
- The kitchen's materials for the whole canteen (`materials.INTERIORS
  ["ratdogs"]`: 255 / 438 / 568, jambs in wood 20), its tube over the
  counter, and 2453 on the counter's sides.

## What I will not do, and why

- No striped booth front. The canteen is a room in the works block, and its
  face is the block's facade; a carnival stripe on it would be a booth
  pasted on a building.
- The hatch replaces a whole painted window and rises to the door's head,
  not E1M4's 16,384: a shorter hatch left the window's arch standing over it.
- The letters are plain sprites, not breakable 416s: the city's signs are
  written by `signage.py`, which does not make them breakable.
- No cultist cook. The canteen keeps the population it had.

## What I still do not know

- Whether a canteen reads as a canteen with one table. A dining room with
  benches would say it more plainly; Blood has no table tile, so tables are
  raised sectors, and one is built.
- Whether the grill's damage is reachable: the sill is 8,192, twice a step,
  so a player must jump onto it. Nobody has tried.
- What blind readers make of it: not run.

## What was built (2026-11-20)

`l3_foundry.dress`: the canteen's west door is the hatch (`hatch`, 618, at
`HATCH_SILL` 8,192 and up to the door's head); the counter is the grill's
iron with rats and steam on it; the display pedestal is a wooden table
(rise 7,168); the room wears the kitchen's materials at E1M4's shades. The
sign is `signage.STREET_SIGNS`' RAT DOGS. Frames: `look.py --set canteen`.
