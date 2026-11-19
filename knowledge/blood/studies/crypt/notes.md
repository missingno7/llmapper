# Study: crypt

Written 2026-11-18, AFTER the first two crypts were built without one. The
owner on the second: "The crypt doesn't really look like a crypt, check
E1M1 for reference". This is what looking found.

## What I want to build

A crypt under St Gallow's, the parish church of Gravesend: one burial
vault a player goes DOWN into from the church, that reads as a place of
the dead before anything in it moves, and that has a second way out (the
sewer runs under the avenue beside it).

## Where Blood built it

- **E1M1, sector 150** (seed `E1M1:150!`): the mausoleum the campaign
  opens in. An L of two arms, 17 m by 18 m over all, 4.1 m high. The
  sarcophagus stands in the short arm, in an alcove of its own width.
- **E3M8, sector 456** is NOT a crypt, though its palette matched: it is
  a graveyard at night -- brick paving, round mausoleum drums carved with
  a cross, iron-ringed doors. Useful for a cemetery, not for this.
- **E3M8, sectors 249 and 445**: a closed sarcophagus top -- tile 128, the
  carved figure, as the floor of a chest 1,024 by 2,048 over earth.
- **E1M1, sectors 0 and 9**: tombs 2,048 by 1,024 flanking the mausoleum,
  0.4 body high, topped with tile 346 (the owner's "gravestone").

## What makes it read as that

Looked at in frames with the control sprites hidden:

1. **Rubble, not brick.** The walls are rough fieldstone (110). Neat grey
   brick (421) appears only on the made things -- the chest's sides.
2. **Earth underfoot** (270), dark red-brown, and a dark worked-stone
   vault (253) close overhead.
3. **One sarcophagus is what the room is for.** It has a profile: sides
   standing a third of a body, a bevelled shoulder (three sloped sectors,
   256 wide, rising 2,048), then the top a lip above that.
4. **The dead are named on the walls**: gold plaques of a carved figure
   (128 in palette 8) at 1.2 bodies, one to a stretch of wall.
5. **Nobody has been here**: cobwebs hang from the vault in open air
   (1067/1068, translucent), not on the walls.
6. **It is dim and nearly bare.** Floor shade 34; two wall sprites of
   blood; no furniture besides the tombs.

## Sizes

- E1M1's arms are 4,096 to 6,144 wide (7 to 10 m); the ceiling is 2.3
  bodies. Ours: 4,096 by 3,840, 2.4 bodies -- one arm of E1M1's.
- Sarcophagus: lid 1,920 by 1,024 (E1M1) or 2,048 by 1,024 (E3M8, E1M1's
  flanking tombs): the size of the tile, 64 by 128 pixels, laid once.
- A body's aisle (1,024) on every side of it.

## What I will transcribe

- Walls 110, floor 270, ceiling 253, floor shade 34.
- The sarcophagus profile: sides 6,144, sloped shoulders 256 wide rising
  2,048, lid a lip of 2,048 above; chest faces 421; shoulders 273.
- The lid CLOSED, 1,024 by 2,048, in tile 346 with the texture begun at
  the lid's own corner (`floor_stat` 64), as E1M1 lays it on s0 and s9.
  The owner chose 346 over 128; the lookup confirms both are used so.
- Plaques: E1M1 sprites 185-189, field for field (type 417, so the powder
  barrels will break them).
- Cobwebs: E1M1 sprites 150-154, field for field, hung under the vault.

## What I will not do, and why

- **Not E1M1's wooden top (504).** It is the surface the player climbs
  out through; the owner's name for 504 is "mirror / room-over-room
  surface ... never a material choice". I put it on the lid before
  looking the tile up, and the owner caught it.
- **Not E1M1's rotating drum door**: our way in is the slab lift, and a
  second mechanism at the same door would be noise.
- **Not a row of four tombs.** The first version had four plain boxes;
  E1M1 has one sarcophagus that is the subject and two low tombs aside.

## What I still do not know

- Whether one arm is enough: E1M1's crypt is an L, and the turn is part
  of why it does not read as a box. Ours is one rectangle.
- Whether the plaques want E1M1's spacing (about one per 4,000 of wall)
  -- ours are four on two walls.
- None of it has been walked in the game.
