# Urban semantics — the deeper read the street classifier couldn't give

Owner request (2026-08-27): the street classifier isn't accurate enough, and
the inaccuracy extends into building interiors. This pass
(`tools/mine_urban_semantics.py`, records in
[urban-semantics.json](urban-semantics.json), labeled plots in
[plots/semantics/](plots/semantics/)) labels **every sector** and groups
interiors into **buildings**:

`street · arcade (covered passage) · courtyard · roof · interior_ground ·
interior_upper · underground · scene` — with buildings defined as
**ground-floor walkable interior components** (party walls no longer merge
rowhouses; shared upstairs no longer merges E3M1's saloon into its hotel),
upper storeys attached to the building they walk down into, and doorways
counted from the full circulation network (street ∪ arcades).

## Rules the corpus forced while building it (each bought by a misread)

1. **Storeys are local, not global**: ground-floor means within one standing
   of the *nearest street's* floor, propagated outward — a hilltop town read
   as one giant upper storey under a city-median grade.
2. **Scene labeling is sky-only**: the optimistic reachability model
   under-reaches through unmodeled gating; calling a locked ward a "scene"
   would repeat the bot mistake in static form (owner's caution, applied to
   the static model too).
3. **An arcade is corridor-narrow, per sector, on a mouth-to-mouth path**:
   without the narrowness test E3M2's roofed halls read as arcades; without
   path-pruning its entry vestibules were absorbed into the passage.

## What the deeper read found

| map | buildings (ground units) | entered from network | share | multi-storey share | arcades |
|---|---|---|---|---|---|
| E3M1 | 15 | 6 | **0.40** | 7/15 | 0 |
| TEDE1M2 | 25 (+1 solid) | 10 | **0.385** | 4/25 | 5 covered-lane sectors |
| DukCity3 | 34 (+1) | 13 | **0.37** | 6/34 | 3 |
| DukCity1 | 58 (+2) | 12 | 0.20 | 7/58 | 3 |
| DukCity2 | 48 (+2) | 10 | 0.20 | 8/48 | 4 |
| DWE3M10 | 52 | 7 | 0.135 | 2/52 | pier shacks, single-storey |
| DukCity4 | 66 (+2) | 9 | 0.13 | 4/66 | 0 |
| E3M2 | 8 (+3) | 0 direct | see below | 5/8 | 15 gate passages |

- **Per-building enterable share: 0.13–0.40 across both games** — a
  tighter, better-grounded enterability contract than the walk-around block
  share (which could not see frontage buildings at all). Gravesend's
  venue plan (10 venues over ~40–50 plan buildings ≈ 0.2–0.25) sits
  mid-band. Candidate L1 contract row; queued.
- **Storey mix**: E3M1 is the corpus's most vertical town (47% of buildings
  multi-storey); DukCity runs 10–17%, the pier 4%. Phase 2 massing note:
  roughly **half of Old Crossing/Theatre buildings should carry an upper
  storey**, a quarter elsewhere — E3M1 is the town Gravesend answers to.
- **E3M2 is rampart urbanism, and its v2 number needs an asterisk**: its
  15 "doorway targets" are narrow **gate passages through the town wall**
  (street at both mouths — correctly arcades), so the v2 "2.04/10240
  doorways, corpus max" mostly counts gate mouths, not building doors. Its
  buildings hang off **vertical circulation** — the roof/upper network
  (49 roof↔upper adjacencies): you enter from the walls above, not the
  street. A different urbanism; Gravesend takes the *rail-seam* lesson from
  E3M2, not its enterability numbers. Correction noted in
  [../reports/city-norms-v2-diff.md](../reports/city-norms-v2-diff.md).
- **TEDE1M2's covered lanes**: the arcade detector recovered the narrow
  roofed passages (5 sectors survive the strict tests; the rest of the
  northeast quarter reads as genuine building interior by geometry). The
  owner's check on that quarter stands as the open item.
- **E1M4 is not street urbanism** (street component = 1 sector, share
  0.08): the carnival is court-and-venue fabric; its numbers stay in
  venue-patterns, not the city corpus.

## Where this feeds Gravesend

- **Enterability contract (proposed L1 change, queued)**: adopt the
  per-building share band 0.13–0.40 alongside the frontage rates; the plan
  currently satisfies both.
- **Phase 2 massing**: storey mix targets per district (above); upper
  storeys attach to ground buildings by stair, which the building
  segmentation can verify per iteration.
- **Phase 3**: arcade grammar (corridor-narrow, mouth-to-mouth, ≤3 deep)
  is now a measurable element — Old Crossing's dead-end alley could become
  a true covered lane within contract.
- **Conformance**: the semantics pass runs per iteration next to the
  street classifier; drift in label counts (a venue's interior reading as
  scene, a courtyard reading as street) is a finding.
