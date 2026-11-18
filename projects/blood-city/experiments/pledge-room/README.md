# Experiment: a pledge room, and what "more complex" turned out to mean

2026-11-18. The what-if strip: [`what-if.png`](what-if.png).
`hypothesis.json` was written before the first build.

## What the owner asked

> I also would like to have more complex interiors.

## What "complex" measures as

`tools/city_profile.py --interiors` (new): one row per map, medians per
interior, an interior being a connected group of roofed sectors of 20 square
bodies or more.

| | E3M1 | E1M4 | DukCity3 | Gravesend |
|---|---|---|---|---|
| floor heights per interior | 15.5 | 3 | 7 | 7.5 |
| floor range, bodies | 2.96 | 0.54 | 1.13 | 1.45 |
| ceiling heights per interior | 10.5 | 3 | 5.5 | 5.5 |
| wall tiles per interior | 14.5 | 5 | 9.5 | 7.5 |
| floor shade spread | 37 | 18 | 30 | 7.5 |
| sloped sectors, share | 0.095 | 0.226 | 0.07 | 0.027 |

Against Blood's own city, Gravesend's interiors are short of **levels** (half
the range), of **materials**, and above all of **light and dark**: 7.5 shade
steps between an interior's darkest and brightest floor where E3M1 holds 37.
Against E1M4 they are not short of anything. So the target is E3M1, and the
largest gap is light.

## What was built

One room. Behind the pawn shop, in the dead pocket between it and the
Aldermack's lobby: a recess a quarter of a body up, a strongroom behind it
under a ceiling half a body lower than the shop's, walled in the owner's
pressed metal (215), lit, two pledged coats on its back wall, a chain lamp,
and a blocking grille (the owner's mask 463) across the recess. The bars
hang between two volumes at one height: the same record law as a pane
(`bloodmap.glass.grille` refuses to pretend otherwise).

## The what-if variants

From the built map, `tools/whatif.py` (`whatif.json`): **nobars** (the mask
and the blocking removed from 2 walls), **unlit** (the room and its 4 walls
at the street's shade, its lamp out), **empty** (the 3 sprites removed).

## What a stranger made of five unlabelled sets

One fresh reviewer, four views inside the shop (`critic.md`).

| | what is in the back wall |
|---|---|
| before | "There is nothing in the back wall." |
| empty | "an empty barred niche ... empty, it reads more like a jail cell (guess)" |
| full | "likely a locked cage of pledged or high-value goods behind a barred counter" |
| unlit | "identical ... but the inside of the cage is darker. Likely a secure cage of pledged goods" |
| nobars | "an open recessed display closet ... it reads as a clothing boutique, and the pawn or security read is gone" |

- **The goods: decisive.** "It turns a jail cell into a shop's secure stock."
- **The bars** carry the meaning and cost the view: without them the niche
  "helps depth and legibility, and hurts the pawn-cage identity", and it was
  ranked first in two of four views for "a real lit space with a floor".
- **The light: "barely".** It preferred the unlit cage overall: "dimmer
  interior adds dark-behind-bars depth".

## The predictions, scored

| | prediction | result |
|---|---|---|
| P1 | the pawn shop's interior reaches 4 or more floor heights and its shade spread rises by 6 or more | **failed.** Floor heights 5 before and 5 after (the room's floor is at the display sill's height, which the shop already had); range unchanged at 0.48 body; shade spread 17 to 18. What moved: ceiling heights 3 to 4, wall tiles 10 to 13 |
| P2 | the reviewer names a barred or caged room and what it is for | held, at "likely" |
| P3 | without the bars it reads as a back room or store | held: "a display alcove or wardrobe" |
| P4 | unlit, the reviewer does not mention it or calls it a dark doorway | **failed**: it read it the same and liked it better |
| P5 | the grille's record has no step band; rules; determinism; oracle; suite | held; see below |
| C1 | street shopfront frames change by fewer than 500 px | **failed as written** for `pawn_front` (21,461 px): the window looks straight through the shop at the wall the bars are in. The market hall and the arcade: 0 |

## What it found that I had not

**A regression.** Moving the shop's shirts off the new opening pushed the
LOANS column out of every view, and the reviewer saw it at once: "Shop
identity and the cage are never seen together. Only [the before] has the
LOANS sign." LOANS now hangs on the back wall beside the bars. That change
has not been reviewed.

**"The room is ONE flat box."** "A single uniformly lit ceiling, flat even
light everywhere, no level change, no shadowed corner, no light source and
no pool of light. The only depth is the 1 m niche."

**"The barred niche is unreachable and has no purpose."** No counter meets
it; "it reads as wall decoration, not a service window or lockup a player
could open".

## What this says

The stranger and the table agree, and they agree against me. A room behind
bars is a detail. It gave the shop a second reading and moved none of the
numbers that separate Gravesend's interiors from E3M1's, and the reviewer's
last word on the shop is the table's first row: one flat box, evenly lit.

"More complex interiors" is therefore not more rooms. In the order the
measurements put them:

1. **Light and dark inside one room.** 7.5 against 37. A shop lit by one
   lamp over its counter and dark in its corners, not a shade per sector.
2. **Levels.** 1.45 bodies against 2.96: a stair to a gallery, a cellar, a
   raised back shop. The venue's programme has to ask for it.
3. **Materials.** 7.5 wall tiles against 14.5.

And from the what-if: put the **goods** in first. They were decisive here as
the name was on the shopfronts.

## Does it run

327 sectors / 2,086 walls / 520 sprites. Rules 12 errors, 7 warnings. The
reviewed build is deterministic. Final build: `measurements.txt`.

## Not done

- Everything in "What this says". This experiment found the target; it did
  not hit it.
- The cage cannot be opened and nothing meets it.
- The pledges are two coats, because coats are the only goods this shop's
  code knows how to hang.
