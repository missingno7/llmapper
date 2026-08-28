## 0b. Market Slip built out — owner-play-pending (newest)

The district the player spawns in is now dressed, on the pipeline the pilot
proved.  `level/blood-city-current.MAP` rebuilt: 63 sectors / 440 walls,
94% wall reserve, contracts 16/16, conformance 7/7, discriminator **1.64**
(2.09 when the loop opened) with blandness inside the campaign's own
distribution for the first time.

New in the plaza and on the water: a sunken **fountain** at DWE3M1's basin
depth, a **stall run** of three platforms, the quay's **boards** (which
also delivers the roadway/walk split E3M1 has), the **river** with a moored
lighter built as sectors per DWE3M10, and the **market hall** — E4M9's
retail grammar as a concourse with two units behind storefront necks.

**The find worth knowing about**: a door opening straight onto a six-storey
facade makes Build draw the entire wall above it from the *door's* tile — a
brown wooden slab six storeys tall.  It was in the pilot's canteen doors too
and nobody would have seen it from the pilot's pose set; a Market Slip pose
caught it.  The fix is the project's own aperture grammar (a leaf plus its
mediation): a porch with a door-height ceiling gives the facade back the
wall above the opening.  Both districts now build doors that way.

**What I want your eyes on here**
- The opening view from the spawn: monument, brazier, plaza, block facades.
- Whether the fountain and stalls make the plaza a *market* or just objects
  on flagstones — the stalls have no goods on them yet (sprites, next pass).
- The river: it is wadeable (one max step down) and the lighter is
  walkable.  Is that right, or should the water be a look-only edge?
- The market hall's two units are identical in plan and differ only in
  dressing, per E4M9 — does that read as a row of shops or as one room
  split in half?

## 0. CLOSING SUMMARY — refinement loop (owner-play-pending)

The owner's verdict opening this loop was *"very raw overall, textures
don't fit."*  Four iterations later, `level/blood-city-current.MAP` is
rebuilt and ready to play.  Full log: [refinement-log.md](refinement-log.md).

**What improved — strongest before/after pairs** (same pose, same settings):

1. *The player's first frame*, `looks/i1-before/frames/quay_start.png` →
   `looks/i2-lit/frames/quay_start.png`: featureless black slabs → a
   multi-storey stone facade with lattice windows and cornices.  Cause was
   not shade: tile 414, used as Market Slip's facade, is **wood boarding**
   — settled by rendering Blood's own ART to a contact sheet.
2. *Through the grate*, `i1-before/frames/grate_stand.png` →
   `i1-after/frames/grate_stand.png`: a sewer wearing arched street windows
   → E3M3's stone-and-rust register.  Same fix, one rule: surfaces are
   named by role (facade / interior / service / sewer / masonry), never
   inherited from the district by everything in it.
3. *The canteen*, `i1-before` → `i3-after/frames/canteen_in.png`: brick
   facade indoors → papered walls, coffered ceiling, patterned floor, at
   full campaign room height — E3M1's own interior register.
4. *The forecourt*, `i2-fix` → `i2-flame/frames/pool_forecourt.png`: flat
   grey → the Aldermack's ashlar under a burning flame, with the kiosk in
   masonry instead of wearing a tower's worth of windows.
5. *A street that was never dressed at all*,
   `i3-fresh3b/frames/north_lane.png`: the works' brick corner with lit and
   unlit faces, flagstone lane, red sky.

Three of those are pipeline stages, so every future district inherits them:
`materials.py` (role-named surfaces with the campaign's jamb rule),
`facade_pass.py` (per-building facade variety — the city now spends 6
facade tiles like E3M1 spends 13, instead of one per district), and
`lightpools.py` (Blood's own way of lighting a street: small brighter
sectors, now 22.2% animated against the campaign's 20.7%).

**What I want the owner's eyes on, in game**
- Whether the four district facades read as four *places* or merely four
  textures — the frames say distinct, but that is a judgment.
- The flame pools: nine of them, at mouths and gates.  Too sparse? Too
  regular?
- The see-through grate: standing over it and dropping through.
- The canteen: does the venue register (papered walls, coffered ceiling)
  read as a works canteen, or too genteel for Foundry Ward?

**Deferred, with reasons**
- Sidewalks: E3M1 splits roadway from walk; ours is one material because a
  walk needs a sector along every facade.  Costed later.
- Only 1 declared secret against a campaign median of 5 — more arrive with
  the other districts.
- `height_iqr_ratio`, `median_height`, `sky_fraction`: all consequences of
  three districts still being bare massing, and E3M1's own street height is
  identical to ours.  Fixing the statistic would break the measured norm;
  recorded as a disagreement, not silenced.
- The observer drops frames for sight lines over ~6 plan units — a looking
  tool limitation, worked around by aiming poses shorter.

# Review queue — accumulated human-judgment work

Standing artifact per the no-blocking-gates directive. Automation has
verified everything it can on each item; what remains is taste. Ordered by
how expensive later rework would be. Feedback lands as normal iteration work
at whatever layer it names.

## 1. L1 plan approval (highest rework leverage)

The schematic plan passed all 16 contract rows
([plan-contract-check.md](plan-contract-check.md)) and Phase 1c proceeded
automatically. Judgment calls a human might veto, in the plan's own words
([../level/city_plan.py](../level/city_plan.py), plot:
[gravesend-l1-plan.png](../references/plots/gravesend-l1-plan.png)):

- **District geography**: Market Slip south (river gate + start), Theatre
  Row north with the Aldermack fronting the avenue vista, Old Crossing west
  (roof route), Foundry Ward east rows 1–2 (sewer below). The avenue is the
  city's one full north-south vista.
- **Two superblocks, not three**: the Aldermack (29k) and the works (32k);
  the third mode is covered by three small free-standing masses (kiosk,
  monument, gatehouse). CN 2 allows 2–3.
- **Venue distribution**: four of nine venues cluster on the Aldermack
  superblock (the entertainment-district reading of VP); Old Crossing gets
  only the hidden workshop bar — its identity spend is the roof route
  instead.
- **Circuit shape**: a single big loop with the sewer leg mid-route
  (required passage per SP), returning along market street rather than
  backtracking the north lane. The objective is the Aldermack forecourt,
  entered at the end of the vista the player has seen since leg 3.
- **The quay is the city's south wall**: no playable riverfront beyond it in
  this iteration.

Judgment calls from the 2026-08-27 owner-requirements directive (church,
cemetery, shop-vs-hospital; references:
[church-patterns.md](../references/church-patterns.md), venue/sewer pattern
supplements):

- **Church + cemetery anchor Old Crossing**, on the old block B footprint:
  church mass fronting the avenue (its tower the west counterpart to the
  Aldermack on the same vista), walled cemetery behind with a lychgate on
  the west street, mausoleum row on the church's west face, crypt stack
  beneath it (E1M1 precedent) — *in addition to* the roof route.
  Alternative rejected: anchoring Market Slip (the plaza already anchors
  it; Old Crossing had only the roof route).
- **Decision C: shopping venue over hospital.** The E4M9 mall grammar
  reduces cleanly to a 2–3 unit retail row and Market Slip's market hall
  was already there to receive it; E3M4 measured as one large institution
  (434 sectors, 96 channels) whose scalable pieces — the geometry bed-bay
  module, the institutional signage/lighting language — fold into other
  interiors as named elements. The church supplies the solemn register a
  hospital would have added.
- **The mausoleum row attaches to the church, not the cemetery wall** — a
  wall-attached row would add two street loops and break the CN 2 ceiling;
  the merged solid keeps the count at 9. (Contract tension, resolved inside
  the plan.)
- **Sewer contract re-based on E3M3**: wet share target 0.2–0.4 against
  Duke's 0.00–0.02 — the one structural point where the Blood precedent
  overruled the Duke-derived numbers (both shown in sewer-patterns.md).

## 2. Fun-unvalidated patterns (flagged prominently)

Nothing here has been played by a human yet. **Every pattern below is
fun-unvalidated**; replication will prefer owner-played patterns once any
exist:

- The manhole-drop → sewer ring → works-stair loop as the circuit's
  mid-game beat (SP precedent says required-passage sewers work in DukCity;
  ours is a translation).
- The Aldermack forecourt as both venue mouth and final objective.
- The dead-end alleys as texture-without-loops.

## 3. Skeleton walk (available now)

`level/blood-city-current.MAP` is the compiled L2 skeleton — engine-tested
(no crash, clean run). Walkability is verified statically (street component
joined, conformance clean); a bot run also crossed three sectors without
crashing, but per the owner's note the bot is crash-smoke only, not a
navigation metric — it stops when idle and can miss reachable places. It is
bare massing under a night sky:
streets, masses, the cemetery ring, the yard, the manhole drop and the works
stair down to the sewer trunk. Worth a two-minute walk to veto the *feel* of
the street widths and the vista before facades spend walls on them.
Evidence: [plan-conformance.md](plan-conformance.md),
[skeleton-city-plan.png](skeleton-city-plan.png) vs the precedent plots.

One deviation to know about: **the sewer runs under the works superblock,
not under the streets** — the geometry audit refuses declared
partial-overlap stacks (grammar-requests.md #6), so the SP "true ROR
under-street" row is grammar-blocked, stated in the conformance report, and
will be revisited when the parallel grammar workstream lands the exemption.

## 4. Urban-source screening fold-in (2026-08-27, verified sources)

Done and green; the judgment items:

- **Re-detected networks for owner check**:
  [tede1m2-city-plan.png](../references/plots/tede1m2-city-plan.png) now
  reads square + west + south streets (58 sectors, 39 doorways); the
  northeast quarter still reads as interiors — if those lanes are streets
  in the owner's reading, they are covered arcades beyond the 3-hop merge
  limit, and the limit needs raising for that map only.
  [e3m2-city-plan.png](../references/plots/e3m2-city-plan.png) reads the
  town at the owner's numbers (77 doorways, 2.04/10240).
- **Art admissibility call**: TEDE1M2 (95% campaign tiles) and DWE3M10
  (97%) admitted to the art set — DWE3M1, already admitted, sits at 94%;
  their few foreign tile ids are excluded. Veto here removes them from
  ART_SOURCE_NAMES only.
- **Contract stance**: no L1 change from v2
  ([city-norms-v2-diff.md](city-norms-v2-diff.md)) — the loop floor's
  softness and the Duke-derived canyon target are *recorded, not acted on*;
  the lane class (3072) is now attested vocabulary for Old Crossing.
- **New pattern applications proposed** (all fun-unvalidated): backdrop
  windows in Phase 3 (Aldermack upper windows, works east wall, quay far
  shore), the Aldermack interior court weave in Phase 4, the rail spur
  continuing as a cutting (E3M2 seam precedent) as a Phase 2 option.

## 5. Urban-semantics pass (2026-08-27, owner-requested deeper look)

New per-sector classifier ([urban-semantics.md](../references/urban-semantics.md),
labeled plots in references/plots/semantics/). Judgment items:

- **Proposed L1 contract change**: adopt the per-building enterable share
  band **0.13–0.40** (cross-game, from ground-floor walkable building
  units) alongside the frontage rates. Gravesend's plan sits at ~0.2–0.25;
  no geometry changes, one new contract row in plan_review. Approve/veto —
  cheap either way.
- **E3M2 correction accepted into the record**: its corpus-max doorway rate
  was gate mouths; it is rampart urbanism (buildings entered from the wall
  circulation above). Gravesend keeps only its rail-seam lesson.
- **Storey-mix targets for Phase 2** (from the storey segmentation): ~half
  of Old Crossing/Theatre Row buildings multi-storey (E3M1 at 47% is the
  model), a quarter elsewhere. Will be encoded as massing-phase checks.
- **TEDE1M2 northeast quarter**: the strict arcade tests keep 5 covered-lane
  sectors; the rest reads as building interior by geometry. Still the open
  owner-check from the screening item above.

## 6. Owner-play-pending: Foundry Ward pilot, iteration 1 (FIRST PLAYABLE)

`level/blood-city-current.MAP` — spawn on the quay, walk the avenue or cut
east to the rail spur; the pilot district is dressed, the rest is skeleton
massing (deliberately visible raw city, per the milestone directive). What
to look at: **the works yard** (dock, lamps, cultists), **the canteen**
(counter/pedestal geometry, the z-motion door, the backdrop window in the
back room), **the yard grate** (see-through stack — look down before you
drop), **the staged moment** (step on the grate), **the sewer leg** (drop,
trunk, junction, rats, out via the cellar pit jump + works stair). Packet
with acceptance, renders, and three judgment calls flagged fun-unvalidated:
[pilot-foundry-packet.md](pilot-foundry-packet.md). Everything here is
unplayed; the second district will prefer whatever this play session
approves.

## 7. Owner-play-pending: Theatre Row's venues (iteration 13) — **fun-unvalidated**

`level/blood-city-current.MAP`, walk north up the avenue or west along
Theatre Row.  Four venues opened, none of them play-tested:

- **the Aldermack** — foyer off the forecourt, a second lobby on the
  avenue, auditorium with a proscenium stage, backstage and dressing rooms.
  The taste call: the house is the tallest interior in the city (49,152,
  2.9 player heights) and the stage sits under a much lower ceiling.  It
  should read as grand; it may just read as empty, because there is nothing
  on the stage and the raked rows are platforms rather than seats.
- **the saloon** — counter and two card tables as geometry, per E3M1.
- **the shooting parlor** — a one-bay mouth into a gallery, with a firing
  line and three targets in the range behind.  The *type's* whole trick is
  that the mouth undersells the inside; whether ours does is a judgement
  no check I have makes.
- **the pawn shop** — open front on the avenue, four display modules.

**What changed under the whole city at the same time, and wants an eye**:
the roadway tile.  Every street in Gravesend is now red cobble (352) rather
than grey flagstone (4) — the evidence for it is strong (E3M1's street is
37% cobble by area and we were paved in its sidewalk tile) but it changes
the look of every outdoor frame in the level at once, so it is the single
biggest visual change since the loop began.

**Also unvalidated**: each venue now has its own wall/floor/ceiling palette
and its own ceiling height.  The measurements say a campaign town does
exactly this; whether *these four* palettes sit together on one street is
taste.

## Object loop — three set-pieces, frames to compare (fun-unvalidated)

Each of these passes its measured checks. What remains is taste, and it
reaches you as a pair of frames rather than as a question.

- **plaza_fountain** — ours `reports/looks/objects-plaza_fountain/frames/`
  against E4M1 sectors 46/47/48/171-174 in
  `reports/looks/objects-plaza_fountain-ref/frames/`. Built from the mined
  basin class (concentric tiers descending in even steps inside a raised
  rim). Note the campaign's instance of this class is a stepped pit, not a
  fountain — the class is a *geometry*, and its occurrences are not all the
  same object. Judge ours on whether it reads as a fountain, not on how
  closely it matches that frame.
- **saloon_counter** — ours `reports/looks/objects-saloon_counter/frames/`.
  Rebuilt at the mined 0.48 player heights, up from 0.24. The question is
  whether the bar now reads as a bar.
- **church_altar** — `reports/looks/objects-church_altar/frames/`, seen from
  the nave, which is where an altar is meant to be seen from.



## The opening view (iteration 30)

The monument is built and reads correctly at the steps and from five plan
units. Two judgements that are the owner's, not the automation's:

1. **The name does not carry to the spawn**, and cannot on a free-standing
   mass -- the measurement is in iteration 30 of the refinement log.
   Recommendation: put WELCOME TO GRAVESEND on the **market hall's frontage**
   facing the plaza at size 120 or larger, and let the monument be the lit
   landmark standing in front of it. A building frontage has no CN 2 band
   ceiling.
2. **The spawn frame is dark and a street lamp stands in the middle of it.**
   `reports/looks/monument2/frames/spawn.png`. The monument, the plaza, the
   market hall's frontage and the avenue vista are all in shot and none of
   them is the subject. The opening view wants its own pass -- lamp
   placement, plaza shade, and where the player is actually put down.
