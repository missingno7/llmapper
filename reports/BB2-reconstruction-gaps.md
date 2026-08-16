# BB2 semantic reconstruction — information loss

Central question: for each mismatch, was the builder wrong, or did the
understanding document fail to preserve a source relationship?

Classification keys:

- `BUILDER REASONING FAILURE` — prose had it; construction used it poorly
- `UNDERSTANDING INFORMATION LOSS` — source had it; prose did not carry it
- `MISSING SENSOR` — analyzer could not observe it
- `MATERIAL KNOWLEDGE GAP` — visual role could not be retrieved reliably
- `RUNTIME GAP` — mechanism feel needs NBlood stepping
- `DELIBERATE BOTTLENECK LOSS` — exact geometry/IDs omitted on purpose

---

### 1. Outdoor spawns are alcoves, not hunting grounds

**Failure.** Source southern outdoor start sits in ~455 player-areas with
max 2D sight ~73 widths and is one half of the only clear spawn pair.
Candidate outdoor starts are small ring/alcove cells facing walls.

**Why.** The prose stated both “mutually concealed except across the open
ground” *and* outdoor footprints 110–455 with long sight. The builder
optimized the pairwise sight matrix to 0/28 and carved sheds/sight-bars
until alcoves were blind, shrinking spawn neighborhoods.

**Class.** `BUILDER REASONING FAILURE` (numbers were in the spec) plus a
`MISSING SENSOR` for **spawn-neighborhood exposure** (local footprint +
max sight + whether the start sees the main field). Pairwise spawn sight
alone does not encode “peek the courtyard without seeing other starts.”

**Smallest next sensor.** Bounded visibility / openness sampled **from
each start in a 8–16 width radius**, plus spawn-cell footprint vs the
main outdoor component — not only the 28-pair matrix.

---

### 2. Covered sectors should outnumber sky sectors

**Failure.** Source 116 covered vs 63 sky (one-third footprint, more
cells). Candidate 34 covered vs 78 sky.

**Why.** Prose said this explicitly. The builder treated “outdoor
dominant” as sky-*sector* majority on a coarse grid.

**Class.** `BUILDER REASONING FAILURE`

**Lesson.** Footprint fraction and sector cardinality are different
constraints; both were written; only one was built.

---

### 3. Outdoor ground is not a single plane

**Failure.** Source outdoor Z spans related elevations and includes a
~6-height floor-drop lift. Candidate outdoor Z is 0 everywhere.

**Why.** Prose mentioned elevation bands and a sky-exposed lift under
mechanisms. It gave no constructable terrace map. The builder skipped
the lift as “soft toybox.”

**Class.** `UNDERSTANDING INFORMATION LOSS` (no elevation layout) with
`BUILDER REASONING FAILURE` (the lift was described well enough to place
*a* outdoor Z-motion).

---

### 4. Mover toybox thinned to three Z-doors

**Failure.** Source: 13 Z-motion, 4 slide-marked, 6 rotators, 10 gibs.
Candidate: 3 Z-doors, 1 gib.

**Why.** Instructions said preserve gameplay purpose, not native tags.
Prose called it a toybox wrapping item rooms. Hard contract items were
only the three gated prizes.

**Class.** `DELIBERATE BOTTLENECK LOSS` for tag-for-tag identity;
`UNDERSTANDING INFORMATION LOSS` for “how dense local doors should feel
along a route” (no door-per-circulation-length metric).

**Smallest next sensor.** Mechanism density along traversable routes
(movers encountered per player-width of a loop), without requiring type
identity.

---

### 5. Outdoor floor tile 270 vs source 2448

**Failure.** Functional outdoor floor exists; the source’s actual
dominant sky floor is 2448. The candidate used 2448 *indoors* and 270
outside (ontology “organic earth”).

**Why.** Prose described outdoor as gray mottled / ontology organic
earth and forbade copying unannotated bricks. It did not name 2448 as
the outdoor floor. JSON would have.

**Class.** `UNDERSTANDING INFORMATION LOSS` (facet instead of the
annotated campaign floor actually used) and `MATERIAL KNOWLEDGE GAP`
(no “BB2 outdoor ground” family; 270 is the campaign earth prototype).
Not scored as texture-ID failure.

Optional second pass with JSON would likely flip this without leaking
wall coordinates.

---

### 6. Water does not look like water

**Failure.** Tesla is underwater with marker pairs; NBlood surface reads
as shaded floor, not liquid.

**Why.** Prose correctly said there is no liquid animation family on the
surface. Ontology tile 90 is mixed_use / unknown visual material.

**Class.** `MATERIAL KNOWLEDGE GAP` (already disclosed in the
understanding doc). `RUNTIME GAP` for swim feel.

---

### 7. Interior architecture is an orthogonal grid

**Failure.** Source masonry is irregular, multi-loop, visually
building-like. Candidate is a Cartesian grid with a square pavilion.

**Why.** Exact footprints were **deliberately omitted**. Prose said
“cluster of masonry interiors punched into” the field but gave no
shape grammar (L-plans, courtyards inside buildings, fence lines).

**Class.** `DELIBERATE BOTTLENECK LOSS` for coordinates;
`UNDERSTANDING INFORMATION LOSS` for qualitative plan language
(how masses meet the field); `MISSING SENSOR` for a compact
**building-mass sketch** (convex blocks + mouths) that is not a wall dump.

**Smallest next sensor.** Coarse occupied-vs-sky bitmap or convex
building hulls at ~4–8 player-width cells — enough to punch irregular
masses, not enough to trace BB2.

---

### 8. Lighting / shade landmarks

**Failure.** Neither reconstruction nor the first-person shots have a
authored lighting mood. Source shade fields exist but were never a
sensor.

**Class.** `MISSING SENSOR` (stated in the understanding uncertainties).

---

### 9. Ammo abundance

**Failure.** 18 ammo piles vs 47.

**Why.** Prose said ammo-rich and gave counts as fact, then said exact
counts are not required for reconstruction. The builder placed a
representative mix.

**Class.** Soft miss; `BUILDER REASONING FAILURE` if “47” was meant as
scale, otherwise acceptable approximation.

---

### 10. Route-level exposure

**Failure.** Candidate can circulate the ring but first-person field
presence is weaker than “shared hunting ground.” Spawn-pair sight passed
while the *experience* of leaving cover into long sight did not fully.

**Why.** Prose described that transition (sight ~12→50+) as
interior→exterior, not as a sampled route.

**Class.** `MISSING SENSOR`: visibility samples along representative
loops (already hypothesized in the experiment brief).

---

## Sensors / representations that would most improve the next roundtrip

1. **Spawn neighborhood profile** (footprint, local max sight, sees-main-field
   boolean) — fixes the concealment-vs-hunting-ground collapse.
2. **Coarse building-mass sketch** at a few player-widths — fixes grid-yard
   vs punched-masonry without leaking polygons.
3. **Route exposure samples** along the main loop — fixes “pairs are blind
   but the field never feels open.”

Do **not** add a combat simulator, Experience Atlas, or universal room
ontology on this evidence. The pairwise sight sensor worked; it was the
wrong *only* visibility target.

## What not to change

- Do not put BB2 wall coordinates into the prose spec.
- Do not treat exact picnum match as reconstruction success.
- Keep the isolation bottleneck; it did its job.
