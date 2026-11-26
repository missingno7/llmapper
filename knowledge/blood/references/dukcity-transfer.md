# What DukCity can teach a Blood city, and what it cannot

2026-11-17. Sources: `maps/duke3d/DukCity1-4.map` (DukCity5 is an interior
and is left out), against `E3M1`, `E6M1` and Gravesend as built tonight.
Frames: [`dukcity-walk/dukcity-walk.png`](dukcity-walk/dukcity-walk.png).
Numbers: [`dukcity-walk/profile-table.md`](dukcity-walk/profile-table.md),
`profile.json`.

The earlier DukCity work (`city-norms.md`, `urban-semantics.md`) measured the
**plan**: street widths, block sizes, the venue mix. Nobody had stood in it.

## How a Duke map is made to answer a Blood question

Three things do not cross between the games, and one does.

| | crosses? | why |
|---|---|---|
| tile numbers | **no** | different ART; a number means nothing in the other game |
| raw coordinates | **no** | Blood is built at 3:2 of Duke (the hand-converted E3L1 pair) |
| raw shade | **no** | Blood's table has twice the steps |
| **structure, in bodies** | **yes** | a kerb is a tenth of a body in either game |

So the transfer has two instruments and one rule.

1. **`tools/city_profile.py`** asks one fixed list of structural questions of
   any Build map and answers in counts, shares, and lengths divided by the
   game's own standing height. A Duke map, a Blood campaign map and our city
   become columns of one table.
2. **`tools/duke_view.py`** lets the Blood observer stand in a Duke map:
   a viewing copy in Blood's file format (geometry and tile numbers
   untouched, nothing scaled), Duke's own ART, and Duke's own palette, shade
   table and palette swaps packed into the one archive format the observer
   reads a palette from. Colour and light as authored are Duke's; skies are
   not drawn. (The first version remapped Duke's art into Blood's palette;
   the owner's verdict was "Duke palette is off", and it was.)
3. **The rule: a Duke pattern is adopted only if Blood's own campaign also
   does it, or does nothing that contradicts it.** Each row below carries
   the Blood precedent beside the Duke one. Where they disagree, Blood wins
   and the row says so. Duke is where to find an idea; Blood is where to
   check it.

Statements are marked **measured** (the profile), **seen** (a named frame,
my reading), or **inferred**.

## Take

| pattern | DukCity | Blood precedent | Gravesend | verdict |
|---|---|---|---|---|
| **Glass is never on a street's wall** (measured) | 386 glass walls in four maps; 4 on a street record (0 to 2%) | E3M1 25% on a street record, E6M1 100% | 0% since tonight | **Take, and it is done.** Duke is the stronger precedent for the owner's rule than Blood is |
| **A pane is about one body wide** (measured) | median 0.91 to 1.09 bodies wide, 1.2 to 1.45 tall; 70% between 0.5 and 1.5 | E6M1's two are 3.9 wide | 1.0 to 2.0 wide, 1.7 tall | **Take**: bays of about a body. Ours were divided tonight at 2560 (2.4 bodies); a body is the Duke number |
| **Facades are articulated in plan** (measured) | median street-wall segment 0.41 to 0.56 bodies | E3M1 1.2, E6M1 2.2 | 1.45 | **Take, toward E3M1's 1.2 first.** Duke's facades are pilasters, returns and window pockets as geometry; ours are straight runs wearing a picture of windows. This is the largest structural gap in the table |
| **A shop is named on a band over its glass** (seen: `glass_1242`, `glass_422`; measured: letters) | 38 to 73 letter sprites outdoors per map | E1M4 33; E3M1 0 | 27 | **Take.** The fascia is a band of a second material at ground-storey height with the name on it; the pane and the stall riser sit in it. It answers survey finding 4 ("facades are one tile, floor to sky") without a new tile: a band is geometry |
| **On a dark street the rooms behind glass are lit** (measured) | DukCity3 (night): street floor shade 37, rooms behind glass 24 | E3M1: street 32, behind glass 24 | 32 and 32 | **Take.** The same 8 to 13 steps in both games, and none here. A window that is as dark as the street it faces is a grey rectangle |
| **Pavement nearly everywhere** (measured) | kerb length 63 to 109 per 100 of street wall | E3M1 40, E6M1 10 | 60 | **Hold at 60.** We are between Blood and Duke already |
| **Things on the pavement belong to the shop behind them** (seen: `glass_422_rake` tables, `glass_1242` bin) | bins 17 in four maps, poles 21, cones 14 | E3M1 6 sprites outdoors in all | lamps only | **Take sparingly**, as an attribute of a venue's frontage, not as scatter. Needs owner-anchored Blood tiles first |
| **Low things made of sectors** (measured) | 15 to 116 walls stepping 0.3 to 1 body outdoors | E3M1 1, E6M1 7 | 16 | **Take a little.** Planters, stoops, ledges, a bench-height wall: geometry at sitting height. Blood's own maps barely do it, so few |

## Do not take

| pattern | DukCity | Blood | why not |
|---|---|---|---|
| **One height for every street wall** (measured) | 88 to 96% of street-wall length at one height, 15.5 bodies | E3M1 38% at its commonest height, seven heights | This is exactly what Gravesend had this morning and the owner's first complaint. Duke's city is a canyon; Blood's is a town. The skyline comes from E3M1 |
| **Streets that end at the canyon wall** (measured) | no sky backing in any DukCity map | E3M1 six, E6M1 two | Duke never shows sky at a street's end. Blood does, and we now do |
| **Daylight** (measured) | DukCity1, 2, 4: street floor shade 0 to 16 | E3M1 32 to 34 | Blood is a dark game. Gravesend's ground (32) already matches E3M1 |
| **Kerb height** (measured) | 0.091 body | 0.121 body, 22 of 22 walls in E3M1 | Take Blood's |
| **Pavement width** (measured) | 1.09 bodies | 1.93 (E3M1, E6M1) | Take Blood's; ours is 1.93 |
| **Painted lane marks, parked vehicles, palm trees** (seen: `sector_600`, `sector_625`) | floor sprites 3 to 37 per map | E3M1 0 | 1996 Los Angeles. A cobbled town has no lane marks. The *idea* that a road carries something along its length may return as tram rails (owner tile 1129 is a floor) |

## A correction this produced

Earlier tonight I told the owner the city is lit much darker than the
campaign. `city_profile` weighs every open-sky surface instead of the three
records I had rendered: E3M1's road is at 32 and its pavement at 34, the
same as ours. The difference that exists is contrast (lit facade faces, lit
rooms behind glass), which is two rows of the table above.

## What the instruments cannot tell

- `duke_view` shows no parallax sky, no sector-effector lighting and
  nothing that moves. A frame is evidence of shape, colour and brightness as
  authored, not of how the level looks while Duke is running it.
- `city_profile`'s thresholds (a kerb is up to 0.30 body; a pocket up to 1.5
  bodies across) are stated in the file and are arguable. Its sprite count
  drops Duke's ten marker tiles and Blood's typed sprites and nothing else:
  the Duke figure still includes monsters and pickups, so "sprites outdoors"
  is an upper bound for decoration there.
- "Seen" rows are one reader's reading of a handful of frames.
- DukCity is four maps by one author. It is a style, not a population.

## Ranked for Gravesend

1. **Lit rooms behind glass.** Measured in both games, absent here, and
   cheap: a shade on six rooms.
2. **A named fascia band over each shopfront.** Seen in Duke, lettering
   precedent in E1M4, and it is the first real answer to "one tile from
   pavement to sky".
3. **Articulate the facades in plan**: returns and pilasters at the bay
   grid, toward E3M1's 1.2-body segment. The largest gap and the largest
   job.
4. Pane bays of about a body.
5. A frontage's own furniture, once the owner has named the tiles.
