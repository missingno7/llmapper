# Study: canteen-freezer-dining

Written 2026-11-20, for the owner's second word on RAT DOGS: "Interior is
bit empty, I would add dine in and maybe freezer to the back. Freezers were
in E1M3 for example and some meat processing was in E3M2, check the visual
themes you can get inspired by." Seeds through `tools.study`: `E1M3:305!`
(a freezer), `E3M2:258!` and `E3M2:306!` (meat rooms), `E3M2:450!` (a
restaurant kitchen), `E2M4:613!` (a bar), `E1M2:257!`, `E1M2:185!` and
`E1M2:268!` (a station buffet: kitchen, dining room, locker). I looked at
every frame sheet myself; no blind reader has.

## What I want to build

Behind RAT DOGS' hatch and counter: a room to eat in, and a cold store for
the meat at the back. A player should read "canteen" from the door, and
"meat store" with the freezer door open.

## Where Blood built it

**E1M2 is the whole of it: a station buffet.** Its dining room s185 (4.3 by
9.1 m) has a black and grey marble chequer (290), walls of clay over a dark
stone base (150), and three round pedestal tables (649) to stand at: no
chairs. A sliding door (614, s149) leads to its kitchen s257: grimy tiles
296, metal cladding 489, a wooden counter with a cleaver (2139) and a rat on
it, two hanging pans (2304/2305), EMPLOYEES MUST WASH HANDS (1719), a fire
extinguisher (658), a NOTICE and a pin-up. Its grill s150 is the same as
E1M4's RATDOGS grill: a kSectorDamage (618) on ribbed iron 376, steam and a
pot on it. Beside the kitchen, s268: a locker of pipes (497) and stone
(379), dark at shade 46, corpses on chains (690, 689) from its ceiling.

**E1M3 s305 is the freezer**: 4.8 by 6.1 m, 2.7 m high. Riveted metal floor
315, rusted metal ceiling 255, grey walls with grime at the foot (345).
Carcasses on hooks (1351 three times, a plucked one 1350) hung near the
ceiling as breakable objects (416), each with a hidden blood-drip
generator (702) under it; large and small blood pools (1417, 1413, 732).

**E3M2 is meat processing**: s258 and s306, tall dark rooms of metal panels
(494, 492, 491, 497) under dark planks 174, carcasses by the half-dozen,
the butcher (the fat zombie, type 204, tile 1370), and the tools hung on a
plank board: handsaw 1714, ice tongs 1715, long axe 1709, pliers 1708.
E3M2's kitchen s450 has stoves, an extractor hood, pans and a fluorescent
panel over a green chequer (294).

**There is almost no seated dining in the campaign.** Of 649's 80 uses,
one (E6M7 s441) has chairs (758) at it; Blood's eating places are stand-up
tables and bar counters (E2M4's bar has stools at its counter).

## What makes it read as that

- **The dining room is the floor and the tables.** The chequer says
  "public room", the round tables say "eat here".
- **The kitchen is the wall over the counter**: pans, a sign about washing
  hands, an extinguisher. Each is small, and together they say "kitchen"
  more than any surface does.
- **The freezer is the carcasses, and the blood under them.** The walls are
  plain; the meat hangs at head height so the player walks into it.

## Sizes

- E1M2's dining room: 4.3 by 9.1 m, 7.8 m high, three tables in it.
- E1M3's freezer: 4.8 by 6.1 m, 2.7 m high, five carcasses.
- E1M2's locker: 1.6 by 3.0 m.

## What I will transcribe

- E1M2 s185 for the main room: floor 290, walls 150, ceiling 140 (its
  kitchen's), three tables 649.
- E1M2 s257's kitchen wall over the counter: pans 2304/2305, 1719, 658.
- E1M3 s305 for the back room: 315 / 255 / 345, four carcasses with their
  drip generators, three blood pools.
- E3M2 s258's tools on the freezer wall (1714, 1715, 1709) and its butcher
  in place of the back room's zombie.
- A metal door (495, E3M2's) on the freezer: a push door like the canteen's.

## What I will not do, and why

- No chairs. The campaign seats nobody at a table; a canteen of stand-up
  tables is E1M2's.
- No stoves or hood from E3M2's kitchen: the grill is the canteen's stove,
  and the room has no space for a second one.
- E1M3 wires its drips to a channel. These are built running (state 1) and
  are on no channel: nothing needs to start them.

## What I still do not know

- What blind readers make of it: not run.

## The canteen grew (2026-11-20, later)

First built, the dine-in was 11.2 M where a destination wants 14.0 M, and
the freezer kept the old back room's high window onto the rail yard. The
owner then allowed the building to change shape. The dine-in took the back
room's floor (4,096 by 4,608, five tables, a second tube over them, the
kitchen wall moved to the west wall beside the counter), and the freezer
moved north into the place of the rail-yard backdrop box, 4,096 by 1,792,
with no window. The build no longer calls the place cramped.

## What was built (2026-11-20)

`l3_foundry.dress` restyles `main` and `back` and adds `freezer_door`;
`l3_foundry.dress_canteen` places the tables, the kitchen wall and the
freezer's meat, drips, blood and tools. Frames: `look.py --set canteen`
(`canteen_dine`, `freezer_door`, `freezer_in`).
