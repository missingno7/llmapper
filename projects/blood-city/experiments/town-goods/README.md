# Experiment: the town is dressed with what Blood's towns are dressed with

2026-11-18. Pairs: [`before-after.png`](before-after.png).
`hypothesis.json` was written before the first build.

## What the owner said

> I think you should try to using more variety of assets, check other blood
> city maps like DWE3M1, E3M1, etc. what they are using for decorations.
> Looks like you have quite limited set now

## Counted

`tools/mine_city_assets.py` (new), distinct decoration tiles per map:

| Gravesend | E6M1 | E3M1 | E3M2 | DWE3M10 | E1M4 | E1M2 | DWE3M1 |
|---|---|---|---|---|---|---|---|
| **38** | 32 | 61 | 87 | 91 | 104 | 109 | 142 |

Seven of Blood's town maps hold 335 decoration tiles between them. 119 are
used by two or more of them and by Gravesend not at all.

The existing catalogue (`mine_prop_catalogue.py`) covers the whole campaign
with a frequency floor, which is why a bottle that stands on forty bars was
in it and a pub sign that hangs on two was not. The new miner asks a named
handful of town maps and keeps everything, with the fields each tile is set
down with: repeats, cstat, shade, palette, type, status and height over the
floor. `references/city-assets.json`; pictures in `city-assets.png`.

## What was done

`level/goods.py`: a plan by place. Every tile is used by at least two of
those maps and set down with their fields.

- **The saloon:** bottles, glasses and a jug on the bar and the card tables;
  a still life and a portrait; a potted plant; "Cask of Amontillado Pub &
  Grille" beside its street door.
- **The pawnbroker:** an urn, a jug, a skull goblet and a statue in the
  window among the dresses; a pitcher and a candle behind the bars.
- **PROVISIONS:** a roast, jars, tins, bottles and jugs in the three windows.
- **The arcade:** flasks and a jar on the apothecary's counter; a bucket, an
  anvil, a shovel and pliers at the ironmonger's; a statue and a candle;
  jars and tins at the tobacconist's; "Pickman's Rare Books and Maps".
- **The Aldermack:** TICKETS and a show bill in the foyer, MANAGER and a
  fire extinguisher backstage, plants in the foyer and the lobby; three
  bills on the street.
- **St Gallow's:** candles on the altar, a banner, a statue, a tapestry.
- **The churchyard:** three dead trees and two dry bushes.
- **The street:** notices, newspapers and a warning plate on four facades.

88 of 93 planned things were set down in the reviewed build; the five that
were not are each named with their reason in the build's output and in the
manifest.

## What a stranger made of four unlabelled sets

One fresh reviewer, ten views (`critic.md`). Sets: before, full, the full
build without its new signs, bills and notices, and the full build without
its new objects (`whatif.json`).

| view | bare | dressed |
|---|---|---|
| the saloon's counter | "could be a sauna, a forge or a crypt. Guess." | "bar or saloon, likely. Evidence: objects (wine glasses, a bottle, a painting)" |
| the saloon | "shrine or crematorium" (guess) | "tavern, likely" |
| the apothecary | likely, from its lettering | "certain": "a red potion and a jar on the counters" |
| the nave | "church or crypt, likely" | "church nave, certain ... altar candles, a banner, a statue" |
| the pawnbroker's window | certain, from lettering | "more pawn-shop clutter, so slightly stronger" |

- "Props on counters and tables: **decisive**. They are the only thing that
  makes the two saloon views read as a bar."
- "Altar dressing: **decisive** for church versus crypt."
- "Wall art: helps." "Shop goods behind glass: helps. The lettering already
  carries those views."
- The new printed matter: "**barely**". In these ten views almost none of it
  is in frame; the test did not look at it.

## The predictions, scored

| | prediction | result |
|---|---|---|
| A1 | distinct decoration tiles from 38 to 75 or more | held: 86 in the reviewed build, 85 in the final |
| A2 | 85% of placements set down, every refusal named | held: 88 of 93, then 83 of 88 |
| A3 | the reviewer names five places from objects in the full build and cannot for three of them before | **partly**: the saloon (twice), the nave and the apothecary moved on objects; the pawnbroker and PROVISIONS were already "certain" from the lettering put up yesterday |
| A4 | no more than two frames with an object out of place | **failed**: it listed nine. Four were mine |
| A5 | rules, determinism, load oracle, suite | see below |
| C1 | street-end frames change by fewer than 500 px | **half**: `avenue_north_mid` 0; `row_west_near` 2,915, because a bill on a frontage is in that frame, which the control should have expected |

## What it caught

**Mine.**
- Tile 505, which I read off its picture as a waste bin and stood by three
  shop doors. In place it is a bucket of gore: "says 'danger', not 'hall'
  ... the most obvious repeat". **Removed.** A tile's picture is not a
  reading of the thing in a street, and this is the case for the owner's
  sheet in one line.
- The statue in the pawn window "crammed behind a mannequin". Moved.
- A banner hung where a torch "looks as if it is burning the cloth". Moved.
- The grocer's goods are "tiny lumps scattered on the floor rather than on
  shelves". **Not fixed**: the display's floor is the only surface there.
- The first build's show bills took the Aldermack's own board off its foyer
  wall. I caught that one; the goods pass now runs after the venues' detail.

**Older, and now fixed.** "Open fires burn on top of the tables ... burning
bar tables are absurd." The bar was dressed with a flame on every module;
the survey had called them braziers two days ago. With bottles on the bar
they are gone.

**"It is a small kit."** "Interiors get 1 to 3 props each. The streets get
only gore." Fair. 85 tiles spread over a city is two or three to a room.

## What the reviewer wants next

1. "No bar counter, shelves or barrels in the saloon." A back bar with
   bottle shelves.
2. "Shops have no fixtures": shelves and racks with stock on them.
3. "Facades without lettering or a hanging sign are anonymous": the saloon's
   door and the market hall's.

## Does it run

327 sectors / 2,086 walls. Rules 12 errors, 7 warnings, unchanged. Details:
`measurements.txt`. The final build has not been reviewed blind.

## Not done

- 46 of the tiles used have no owner anchor. They are listed, with what I
  read each as, in `references/goods-unnamed-tiles.md`. Tile 505 says why
  that list matters.
- Wall, floor and ceiling textures: still 37, 23 and 11 against E3M1's 67,
  29 and 22. This experiment changed sprites only.
- Fixtures: the things goods stand ON.
- Nothing was added to the sewer, the station or the works.
