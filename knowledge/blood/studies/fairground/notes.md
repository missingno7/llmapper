# Study: fairground

Written 2026-11-25 for Gravesend's fair (`projects/blood-city/level/fair.py`). Read from the
records of E1M4 and looked at in its frames; no blind reader has.

## What I want to build

A small travelling fair on a town square: a carousel that turns and stalls that each do something, solid enough to hide the square from its side streets.

## Where Blood built it

- The carousel: E1M4 s321 to s329, nine sectors of type 617, one axis (sprite 771 and its copies at one point), `rx` 128, `busy_time_a` 255,
  `busy_time_b` 0, `retrigger` at both ends, `drag`; its poles (213) and beasts (1475) are sprites with cstat 8192.
- The shooting gallery: E1M4 s26 to s43. Stepped tiers 256 deep; in them slabs of 64 by 64, type 616, `retrigger` at both ends, waits of a
  few tenths, 10 to 20 tenths for 2,240 units; on each a duck (852, data 8 / 2203) or a smiling face (853, data 1 / 301), type 416, cstat
  8577. One face (sprite 47) sends 110: a bell (sound 270, sprite 1038) and s64, a well whose floor brings the prize up. A lever (1074) starts it.
- The bottles: s297/s298. Three lots of three big bottles (759, palettes 4, 11, 12, 14); the front one of each sends 124 to a switch of type 22
  that wants 3 (sprite 202), which sends 106: the bell and s174, the well in the counter.
- The glasses and jugs: s66 to s70 (574, 712), all on 103.
- A bullseye: 967, type 416, cstat 400 (sprite 999). 966 is its grey face (E2M5 455 to 460).
- The booth: 943 TICKETS, 905 prices, 752 admission; balloons 1115 in palettes 4, 11, 12.

## What makes it read as that

Red bulbs on a rail (77), the striped cloth (1004), balloons, and things that move by themselves.

## Sizes

E1M4's carousel is 8.7 m across the platform, its gallery 4.3 by 7.2 m with a counter half a body high. Ours: 5.2 units (8.8 m) and 2.5 by 2.8 units.

## What I will transcribe

The drives (617 and 616), the targets' records, the tally and the bell, the well.

## What I will not do, and why

Its room, its Happy-Go-Pukey, its beasts: ours stands in the open with a roof of flat sprites, and carries iron hounds and rats, so that nothing alive is taken for them. Tile 836 (a decoy) is no target: the owner, 2026-11-25.

## What I still do not know

Whether a rider is carried smoothly by three sectors at once; nobody has ridden ours.
