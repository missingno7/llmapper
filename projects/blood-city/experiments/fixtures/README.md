# Fixtures: what the goods stand on

The owner, 2026-11-17: "Yes, fixtures."

A blind reviewer of the dressed town had said "shops have no fixtures ...
shelves and racks with stock on them" and called the saloon's bar
"bench-like blocks".

## What was measured first

`tools/mine_stands.py` reads, for every standing thing indoors in seven of
Blood's town maps, what is under it: the room's floor, an island, a ledge
against a wall, a niche let into one. It is geometry, not a reading of a
picture. `references/town-fixtures.json`, and thirteen of the fixtures seen
from the room beside them in `references/town-fixtures.png`.

- A fixture that carries things stands a median **0.48 body** over the floor
  beside it, and is topped with tile 34. Gravesend's stood 0.18.
- A stocked shelf is a **niche**: floor at that height, its own lowered
  head, a quarter to half a player width deep, a thing every third of a
  player width (E1M2 sector 213, E3M2 82 and 87, E1M4 298).
- A sprite's z is not its foot. Read raw, half the chairs in these maps hung
  in the air; the tool takes the foot from the tile's height and offset.

## What was built

- `fixtures.BAR`: one continuous piece 8,192 high, top 34, face 28 (both the
  owner's wood). The saloon's bar and the six arcade counters.
- `fixtures.shelf_niche`: a recess in a wall with void behind it. One in the
  saloon's east wall under WHISKEY; one in each unit's back wall under its
  name, in place of the pedestal run.
- `goods.ROWS`: a row along each shelf by what the place sells.
- `wallplane.portal_spans` now carries how high each opening is, so a name
  can stand over a shelf; `props.solid_faces(over_shelves=True)`.

## What happened

`measurements.txt`, `critic.md`, `before-after.png`. All five predictions
held. The reviewer, unprompted: "a long wooden counter with a slatted shelf
unit behind it"; stock on the shelf "decisive"; an empty shelf "a dark
slatted hole".

Two things were not predicted and both are the same mistake as before
(piercing or raising something changes what was placed by an older rule):
the shelves moved five names to side walls, and the counters shut the
arcade's key behind them. The second was found by the reviewer, not by me
or by any check.

## Not done

- The final build was not reviewed blind.
- The bookseller has no books and the clockmaker no clocks: none of the
  town-map tiles I can name is either.
- The six units are one shell; the pawn shop and the market hall got
  nothing (no void behind their walls).
- No chairs, stools or legs; the saloon's tables are boxes.
- Nobody has walked it. Whether a player fits round a counter's end is
  derived from a 1,024 gap, not observed.
