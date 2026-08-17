# Pattern-aware understanding: `BB6.MAP`

Frozen from `reports/BB6-understanding.json` using catalog
`knowledge/blood/design/catalog-v1.json`. Original geometry is not repeated
here. Labels in *italics* are INTERPRETED pattern hypotheses.

BB6 is the first non-BB2 validation of the pattern layer.

## What this map is

A Blood v7 BloodBath map on a ~117 × 195 player-width board. Eight
multiplayer starts, all under sky. Two flags, 15 weapons, 14 armor, 8 health,
heavy ammo. 170 sectors, 19 parallax ceilings. Native validation 0 errors.
105 XSECTORs; 39 sectors unreachable at rest — gated or state-dependent
circulation, not a broken graph. No underwater sectors.

It is a **team fortress** layout in the sense of two opposing covered masses
carved out of shared outdoor space, not in the sense of two disconnected
bases.

## What old whole-map averages miss

Covered *sectors* dominate (151 vs 19; sky-sector fraction 0.11). Sky
*footprint* is larger (5143 vs 4518 player-areas; sky-area fraction 0.53).
Reading sector counts as "mostly indoor" inverts the playable field.

Sky clear height is ~17 player-heights; covered median height is ~5. Outdoor
floors occupy several Z bands, including a depression below the main yards.

Morphology is not a grid: orthogonal length 0.69, diagonal 0.08, orientation
diversity 0.94 (34 of 36 bins), rectangular sector fraction 0.34. Indoor
loops include irregular 9+ vertex footprints, chamfers, and segmented curves.

## Spawn neighborhoods

All eight starts are already in the largest sky component (hops 0). They are
not a single spawn type.

- Four starts sit in *open hunting cells*: huge sky area, 14–16 immediate
  exits, max 2D sight 80–100 player-widths, field fraction 1.0. These are two
  pairs in two large yards.
- Two starts are *sky porches into that field*: tiny sector area, one exit,
  but local reachable area still matches the yards.
- One start is a *sky-constrained alcove*: sky ceiling, small local
  reachable area.
- One remaining small sky pad still opens into the large local field.

Pairwise 2D spawn sight is **28/28 clear**. That is *not* evidence that
starts are unconcealed in play: the sight sensor ignores height, and every
spawn rose still hits occluders (open-ray count 0). The disputed hypothesis
"outdoor BloodBath start = hidden from other starts" fails on this map.

## Routes

Every shortest path from a start to the largest sky sector is all-sky
(cover-sequence S, sky fraction 1.0, zero cover/sky transitions). Several
routes still change height and shade while remaining under sky — they walk
into the depression, not into interiors.

This *all-sky shortest path* pattern does not mean interiors are absent.
Interiors are off the start-to-main-sky geodesic. Entering a fortress is
`open → cover`, which the vertical layer sees (9 open-into-cover, 7
cover-into-open samples) even though the spawn-route sensor never samples
it.

## Architecture and vertical rhythm

Outdoor hosts with holes (`sky-host-with-holes`) are the footprint relation
behind the two fortresses. Covered interiors mix rectangular cells
(construction default; not a room type) with irregular, chamfered, and
curved loops.

Storey-scale same-cover height changes into larger cells are common and
should not be read as overlooks. The more specific relation is outdoor
circulation stepping down into a darker central depression, then back up
into the opposite yard.

## Gameplay anchors (still under-patterned)

Flags exist (2). Weapons and armor concentrate with the covered masses and
gated pockets (39 rest-unreachable sectors). The catalog does not yet encode
"control center locks storage / opens flag room" or the hidden Life Leech
cache; those need mechanism-scale mining. Unknown sprite types remain on
this map (including authored specials the type catalog does not name).

Materials: indoor floors/ceilings modal tile 255, indoor walls 194; outdoor
floors 274, sky ceilings 3491, outdoor walls 568. Shade is darker in the
depression and on the small sky pads than in the main yards.

## Pattern matches used for this prose

189 catalog hits, overlapping by design. Heaviest: storey height-change
hypothesis, irregular and rectangular covered footprints, segmented curves,
all-sky routes, pairwise 2D-exposed starts, open hunting cells, open/cover
vertical transitions, two sky porches, two holed sky hosts, one constrained
sky alcove.

## What this prose is for

A builder should reconstruct **relations**:

- two opposing covered masses interrupting shared outdoor hunting space
- mixed spawn neighborhoods: hunting-cell, porch-into-field, constrained
  alcove, lower depression
- start-to-field paths that stay under sky
- interiors that exist but are not on that geodesic
- gated prize / flag rooms off the at-rest circuit
- vertical step into a darker central depression
- irregular indoor grain, not a rectangle grid

and must not copy BB6 vertices.
