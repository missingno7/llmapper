# Study: sewagefall

## What I want to build

Carry the ring's dirty water across the Settling Hall gallery through a low mouth and down the wall into the first settling tank.

## Where Blood built it

- E3M3 sectors 173–174 are a close match. The pool frames show a dark green stripe joining the green pool. Pool wall 1319 (metal 510, cstat 6) uses bottom swap to draw the lower band from mouth wall 1307.
- E1M8:243 is a large walk-over-sewage room. Wall 1309 uses 1120, repeats (16, 8), panning (0, 218), and always-on XWALL velocity (0, −85). Nearby E1M8 walls 1361 and 1386 use translucent masked middles with overpic 1120, cstat 656, repeats (16, 8), and phases (0, 218)/(0, 41). Their vertical velocities are −85 and −128.
- The community scan found 449 vertically panned 1120 wall records in 36 bulk maps and zero in the curated set. FULLMOON sector 116 wall 716 uses a lower band with type 0, cstat 4, repeats (3, 8), panning (32, 251), and always-on XWALL velocity (0, −20). BIOSYN walls 333 and 345 use translucent masks with cstat 656, repeats (4, 8), phases (0, 236)/(0, 74), and XWALL velocity (0, −50).

## What makes it read as that

Tile 1120 is 64×64 green dirty water. Its ART entry advances forward through six additional frames (1121–1126) at speed 4. A feed floor and receiving pool in the same material give the vertical animation a clear source and destination. The E3M3 upper band stays metal because bottom swap gives the falling sheet its own texture record. The wall is type 0 and XWALL panning provides the directional motion.

## Sizes

E3M3 mouth 173 is 1024 by 1024 Build units and 14336 z units high (0.85 standing bodies). The pool is 40960 z units (2.42 bodies) below its lip. The gallery water in Gravesend stands 43008 z units (2.54 bodies) above the first tank. The adjoining dry ledge is 45056 z units (2.66 bodies) above it.

## What I will transcribe

Use E3M3 wall 1307's tile 1120, repeats (8, 8), x/y panning (0, 242), type 0 and always-on XWALL velocity (0, −20) with x/y fractions (0, 128). Carry wall 1319's bottom-swap and peg flags on the tank side. The mouth uses sector 173's clear height and XSECTOR panning speed 8, turned south for the gallery plan. The original floor's stored panning is (100, 0), its floor stat is 20, and its XSECTOR panning angle is 0.

Copy the ambient water sprite from E3M3 sprite 393. It is invisible tile 2521, type 710, status 12, cstat 32896, repeats (64, 64), data fields (150, 350, 56, 50), state 1, and busy 65536. It is 6400 z units above the pool surface. The other sprite in the receiving pool is stack marker 96. E1M8 has separate blood drips under its hanging bodies. Its nearby 1120 masks use ambient sound and stack markers. Both campaign examples use zero visible splash sprites at the foot.

## What I will not do, and why

The lower band follows E3M3's solid-backed sheet, leaving the opening above it clear. The E1M8 and BIOSYN masks serve falls across pass-through openings. The Settling Hall uses the campaign's ambient water sound for the impact.

## What I still do not know

The observer provides still frames. The live timing of the tile cycle, XWALL scroll and ambient sound remain to be checked in a playthrough.
