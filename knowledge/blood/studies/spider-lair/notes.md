# Study: spider-lair

## What I want to build

A spider lair under Gravesend's old quarter (the owner, 2026-11-22: "We can also add spider lair somewhere, similar to E2M8 - but there might be better examples in other levels, you don't have to look only at canonical levels"). The cellars of the old tannery under the saloon row, which the spiders took. You reach it from Graves Brook through a passage, with a web across its mouth that has to be broken.

## Where Blood built it

I mined every single-player map in the corpus, 1,587 of them, for rooms dense in spiders (types 213-216), webs (thing 410), cocoons (tile 1061) and cobweb decals (`work/spider/lairs.py`, `lairs.json`):

- **E2M8:52** is the campaign's spider queen lair. A cobblestone (411) and rubble (110) room with an earth floor (270) and a rock ceiling (253). Shallow alcoves in its walls are lined with silk (wall 1057), and each holds one egg cocoon (1061). Silk torn at the alcove edges (1058) hangs at mid-height. Victims wrapped in silk (1059, type 416, a gib object) hang from the ceiling. Two mothers (216) cling to the ceiling, upside down.
- **CHORROR:414** (community, tier S) is the clearest lair in the corpus. It is a cobblestone cellar. Its lair opens through a mouth fringed with hanging web (1067/1068 along the lintel, at the ceiling). Inside are a wall of cocoons, a breakable web (410 on 1069) across one opening, and 31 small brown spiders (213 at repeat 16) on the ceiling, upside down. There are hanging victims (1059), dead innocents, and the mother on the floor at the back. A carved spider panel (643) hangs over the mouth.
- The other seeds were not lairs. DARKWOOD's room was a lava cave with a web curtain; FOULKEEP, HNTDGRVY and DEDRIVER were the wrong rooms. Other dense rooms in the mining are left for later: GHOSTTWN, CLICK3, castle13 and JOJO (20 web things).

## What makes it read as that

- **Silk where a wall should be.** Alcoves walled in 1057, each with one cocoon, read as "nest" from across the room.
- **Things hanging from the ceiling.** Wrapped bodies (1059) and fringes of web (1068) at the ceiling line.
- **Spiders on the ceiling, upside down.** Records with cstat 8 (y-flip), 1,344 under the ceiling. They drop on you.
- **A web across the way in.** A breakable 410 has to be shot through.
- **Earth underfoot, rough stone round, dark.** Floor shade about 31, lit only by what reaches it.

## Sizes

- E2M8:52's room is 9 sectors, 32,768 to 40,960 high (1.9 to 2.4 bodies).
- CHORROR's lair is 20 sectors and 40,960 high at the median.
- A cocoon stands with its centre 1.1 to 1.3 bodies up.
- Wrapped victims hang from 224 to 256 above the ceiling line.
- Mid-height silk (1058) has its centre at 16,384 to 18,432.

## What I will transcribe

Every sprite comes from E2M8's own record (`l3_foundry._attested("E2M8", type, picnum=)`):

- the cocoon 0/1061 and the torn silk 0/1058;
- the hanging victim 416/1059, without E2M8's wiring;
- the mother 216/1930 on the ceiling;
- brown spiders 213/1920 on the ceiling (cstat 392);
- the fringe 0/1068;
- the web 410/1069 across the passage.

For surfaces:

- wall 411 with 110;
- floor 270;
- ceiling 253;
- 1057 on the alcoves' walls.

## What I will not do, and why

- **No end-of-level wiring on the mother.** E2M8's mothers end the level when killed; this lair is a side place.
- **No dead innocents (type 245).** CHORROR's are live dudes, not decoration.
- **No carved spider panel (643) yet.** There is no wall to hang it on that says "the cult did this".
- **No lava or torches.** The sewer is dark; the lair takes the sewer's dark and the brook's lamps through its mouth.

**Since 2026-11-25** the pillar is a pit and the roof goes up over it; two torches are one and a shaft of light on the key
(`references/sewer-design.md`, "The third pass"). What the corpus gave: E2M8:52's mothers hang free of any wall, and a flipped spider
is weightless until it wakes (NBlood `ai.cpp` 1649, `cstat & 8` sets flags 9), so she may hang on a thread and not on the stone.

## What I still do not know

- Whether ceiling spiders placed by the layout pass `sprite_fit` without reading as "through". The lint is the arbiter.
- How dark is too dark here. The owner will judge it walking.
- What E2M8's victims' wiring did (tx 105/107 relay out of what the catalog follows).
