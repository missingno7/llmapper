# Experiment: a shop has a surround, a name and a light, and which of them matters

2026-11-18. Follows `../shopfronts-streets` and the DukCity transfer
(`../../references/dukcity-transfer.md`). Pairs:
[`before-after.png`](before-after.png). The what-if strip:
[`what-if.png`](what-if.png). `hypothesis.json` was written before the first
build.

## What the owner asked

> Lit room and named fascias - be creative. ... you can try to check how it
> looks without something, maybe have different views, something that can
> give you good feedback from critically, like what if we add this or remove
> this, what it will change

Two things, then: build it, and find a way to know which part of it works.

## What was built

Three measured gaps, all from standing in DukCity and checking Blood's own
E3M1 beside it:

- rooms behind glass were at the street's shade (32 and 32; E3M1 32 and 24,
  DukCity3 37 and 24);
- the pawnbroker and the rest were named on their own **inside** walls; one
  sign in the city faced a street;
- a facade was one tile from pavement to sky.

None of it needed a new sector. Each window already had a reveal between
the street and its sash pockets. Give that reveal the street's floor and a
ceiling a fascia's height (0.72 body) over the window's head, and:

- the band under each pane and the band over it are step bands of the
  reveal-to-sash wall, drawn from the **reveal's** record: the stall riser
  and the fascia, in the shop's own material;
- the solid wall between two sashes is the reveal's back wall: a pilaster;
- the street's record over the mouth starts above the fascia and is still
  the facade's; the pane still hangs between two volumes at one height.

`glass.surround` does it for all three venues. Materials are the owner's:
wainscot (84) and pilaster (88) for the pawnbroker, pressed metal (215) for
the market hall, coffered panelling (105) for the arcade. The name is
lettered on the fascia (`glass.write_names`): PAWNBROKER, PROVISIONS,
MARKET HALL, and after the review DRAPER and CLOCKS. A chain lamp (owner
tile 641) hangs in each display over a declared light source.

## The what-if tool

`tools/whatif.py` takes a **built** map and a list of edits and writes a
variant: these sectors' shades set, these walls repainted, these sprites
dropped. A variant costs a second where a build costs three minutes, and it
says of itself that it is not a build. The build now writes
`blood-city-current.tags.json` beside the map (which sectors are shop
displays, surrounds, carriageways, end walls ...) so an edit can say "the
shop displays" instead of a list of sector numbers.

Three variants of the full build, each with one thing taken away
(`whatif.json` has every edit and how many records it touched):

| variant | what was removed |
|---|---|
| unlit | 10 lit sectors and their 127 walls returned to the shades the same rooms had before; 6 lamps dropped |
| unnamed | 30 fascia letters dropped |
| unfronted | 34 surround walls repainted in the wall they stand in |

## What a stranger made of five unlabelled sets

One fresh reviewer, nine views, five folders named P to T (`critic.md`). It
was told only that some sets "may differ from each other in only one
respect".

**It reconstructed the design.** Unprompted, it listed three things that
vary, drew the table of which set has which, and named the three pairs that
differ in exactly one respect. All correct.

| | what it is, with the evidence it cited |
|---|---|
| before | "a clothing shop (guess)"; the market hall "a storeroom (guess)" |
| unnamed | "a clothing or dress boutique (likely)"; "a storeroom or warehouse, possibly a shop (guess) ... nothing says it is a shop" |
| full | "a pawnbroker (certain)"; "a grocery or general store (certain)" |

And how much each feature matters, in its words:

- **the sign: decisive.** "It turns the pawn from a dress shop into a
  pawnbroker and the super from a storeroom into a grocer."
- **the surround: helps.** "Without it the window reads as a hole in a
  residential or tech facade, and the sign has nothing to sit on."
- **the light: its absence "hurts, mildly".** It read the unlit rooms as
  "dark, tinted, reflective glass" that "hides the goods, which are what
  identifies a shop".

Ranking, full build first in every view but two ties: full, unlit,
unfronted, unnamed, before.

## The predictions, scored

| | prediction | result |
|---|---|---|
| F1 | rooms behind glass 8 or more shade steps brighter than the street | **failed at first, twice.** Six lamps at an indoor bracket's strength moved the rooms 2 steps: a room that states its own floor shade is protected from LightBomb. Marked as generated surfaces and given stronger sources, displays and shops reached medians 21 and 20 against the street's 32. See the last section for the final build |
| F2 | the reviewer names what each street shop is from the full build and cannot from the before | held: "certain" against "guess" |
| F3 | of the three ablations, the name is missed most | held: unnamed ranked lowest of the three in the pawnbroker's and the market hall's front views |
| F4 | unlit ranks below full looking through glass, and makes no difference at a rake | **half**: below full through glass, and in the arcade well below ("the glass mostly shows a reflection"); but it also ranked below full at a rake |
| F5 | unfronted ranks below full | held; it also produced every texture fault the reviewer listed ("brick-window texture squashed onto the narrow pier faces") |
| F6 | no glazed record gains a step band; rules; determinism; oracle; suite | held; see below |
| C1 | street-end and church frames change by fewer than 500 px | held: 0 |

Could-be-wrong, as written: pressed metal on the market hall did **not**
read as a shutter ("a framed panel with the sign"); the letters **are** too
small from across the street ("barely legible" in `super_north_far`); the
lamp **did** hang wrong ("mid-doorway at eye level", "dropping almost to the
floor").

## What the reviewer still found wrong, and what was done

1. "The mall units sell nothing ... no sign, no goods, no counter." The two
   glazed units are now lettered DRAPER and CLOCKS. Still no goods.
2. The market hall's sign was "dim blue on black" and its lamp hung at eye
   level. The sign is now in the pawnbroker's lettering; every lamp's chain
   is cut to the upper third of its display.
3. "The pawn's goods say 'boutique', not 'pawn'": mannequins in dresses.
   **Not done.** It is the next thing: what a shop sells is in its window.

These three changes were made after the review. **The final build has not
been reviewed blind.**

## Does it run

325 sectors / 2,074 walls / 517 sprites. Rules 12 errors, 7 warnings, as
before. The reviewed build: deterministic, suite 2,268 OK. The final build:
`measurements.txt`.

## What this says about the process

- A before/after pair would have said "better". The what-if strip said
  **why**: the name carries the meaning, the surround gives it somewhere to
  sit, and the light lets the goods be seen. That ordering is now a reason
  to name every venue before fitting it out.
- The reviewer's reconstruction of the design is a check on the reviewer as
  much as on the build: a reader who can tell which sets differ in one
  respect is reading the frames, not guessing.
- Variants are cheap enough to make before deciding what to build, not only
  after.
