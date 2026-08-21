# Cliffside monastery: four evidence-driven iterations

The machine-readable version is `comparison.json`. Each iteration's full packet
is `v*/iteration.json`, its readable digest `v*/summary.md`, its rendered frames
`v*/views/`, and the reasoning that drove the next one
`../design/reviews/v*.json`.

Every number below was produced by `bloodmap.authoring_loop` from the compiled
MAP. None of it comes from the authored labels.

## Dimensions, not a score

| | v0 | v1 | v2 | v3 |
| --- | --- | --- | --- | --- |
| **hard validation** | 0 failed | 0 failed | 0 failed | 0 failed |
| NBlood load smoke | pass | pass | pass | pass |
| views captured / passing | 8 / 8 | 11 / 11 | 11 / 11 | 12 / 12 |
| **authored vs observed hierarchy** | 1 discrepancy | 0 | 0 | 0 |
| derived spaces | 9 | 14 | 14 | 14 |
| arrival dominant space share | shared blob | 1.00 | 1.00 | 1.00 |
| courtyard dominant space share | shared blob | 1.00 | 1.00 | 1.00 |
| gallery dominant space share | 1.00 *into the shared blob* | 0.925 own | 0.925 own | 0.932 own |
| **mandatory reachability** | 28/28 | 29/29 | 29/29 | 29/29 |
| **route structure** | 10 steps start→exit | 10 | 10 | 10 |
| courtyard onward choices | 6 | 6 | 6 | 6 |
| chapel onward choices | 1 † | 4 | 4 | 4 |
| crypt onward choices | 2 † | 3 | 3 | 3 |
| gallery first adjacent along route | — | 88% | 88% | 88% |
| **transition evidence** | reveal 63.5× area, +14 PH | 42.3×, +13 PH | 42.3×, +13 PH | 35.9×, +11 PH |
| **major-space scale** (corpus percentile for its footprint) | | | | |
| courtyard | 59 | 59 | 59 | 59 |
| gallery | 19 | 19 | 19 | **57** |
| chapel | 11.5 | 11.5 | 11.5 | **35.5** |
| exit hall | 4.5 | 4.5 | 4.5 | **41** |
| crypt hall | 2.5 | 2.5 | 2.5 | **8.4** |
| low-ceiling findings | 5 | 5 | 5 | **3 (argued)** |
| **shape vs 42 campaign maps** | | | | |
| orthogonal wall length | 1.00 (p100) | 1.00 | 1.00 | **0.838 (p88)** |
| diagonal wall length | 0.00 (p0) | 0.00 | 0.00 | **0.117 (p71)** |
| rectangular sector fraction | 0.767 (p100) | 0.742 | 0.742 | **0.548 (p100)** |
| orientation bins occupied | 2 (p0) | 2 | 2 | **6 (p0)** |
| **ART / material differentiation** | 3 identical room pairs | 0 | 0 | 0 |
| **decorative distribution** | 5 sprites, 0.40 in one space | 5, 0.40 | 56, 0.21 | 60, 0.22 |
| visually empty derived spaces | 5 | 10 | 6 | 5 |
| oversized decorations | 0 | 0 | **18** | **0** |
| **remaining unknowns** | see each review | | | |

Sector counts went 30 → 31 → 31 → 31 and wall counts 157 → 167 → 167 → 208.
Object count is not on this table as a quality signal; it is here so the shape
and scale rows can be read against the size that produced them.

† v0 declared no chapel or crypt escape probe; those two cells were measured
retrospectively by running the v1 probe declarations against the preserved v0
source, and are not in `v0/iteration.json`. Every other cell comes from its own
iteration's packet.

The v3 reveal ratio drops from 42.3× to 35.9× because the gatehouse itself grew
when it was splayed and its ceiling raised — the constrained side got larger, so
the ratio fell while the transition stayed the strongest in the level.

## Which source change caused which observed change

**v0 → v1 (spatial revision, driven by independent hierarchy evidence).**
v0's only discrepancy was that the arrival, the courtyard, and all eleven
gallery-assembly sectors landed in a single derived perceptual space. The
gallery rose 15360 units and still did not exist as a place, because the
grouping breaks on floor delta above 4096 across a portal or shade delta above
12, and a 3072-unit step at uniform shade delivers neither. The fix was
architectural: a covered gatehouse between the tunnel and the courtyard, and a
low dark arch at each of the gallery's two openings, each darker than its
neighbours by more than the tolerance. Derived spaces went 9 → 14 and the
discrepancy cleared. The same iteration cut stair sectors 16 → 10, raised room
sectors 10 → 15, gave the chapel two aisles and a raised apse (onward choices
1 → 4), and gave the crypt a reliquary and a cistern (2 → 3; the gate switch now
opens 8 sectors instead of 1).

It also revised the *intent*: v0 claimed the open exterior stairs for the
gallery, the evidence said they read as courtyard, and on reflection the evidence
was right. That is recorded as an accepted correction, not hidden.

**v1 → v2 (material revision, driven by ART evidence and rendered frames).**
Geometry and shading were held constant on purpose, so any hierarchy movement
would have proved the critic was reading something other than what changed.
Derived spaces stayed at 14 and discrepancies at 0, exactly as predicted. What
changed: each assembly got its own dominant floor/ceiling/wall triple (identical
room pairs 3 → 0, with only the intended crypt/ossuary pair left), ceilings were
chosen for what they look like after v1's frames showed every one rendering as a
black void, the courtyard wall moved from smooth marble to coursed rubble because
tile 2490 at 16 player heights gave the eye nothing to measure by, and 51
decorations were attached to architectural roles at densities anchored to the
precedent packet.

**v2 → v3 (scale and shape, driven by corpus evidence).** The project owner
observed that the map was still mostly rectangular and its ceilings too low.
Adding the two missing measurements proved both exactly, and v3 answered them:
ceilings set from what original maps do at each footprint rather than from round
multiples of player height; chamfers and shallower non-45-degree facets on nine
outlines; a splayed gatehouse, a radial chancel, an octagonal planter; and sprite
repeats derived from each tile's pixel size and a target height in player heights
instead of copied from the campaign mode, which took oversized decorations from
18 to 0.

## What the critic got wrong, and how

Three of the hierarchy rules were corrected during the pilot, each time because
the rule disagreed with a rendered frame or with plain sector composition:

1. `transition_regions_dominate_space` counted **sectors**, so it called a 1008
   player-area courtyard "circulation" because six tiny stair steps outnumbered
   it. Now weighs floor area and ignores spaces made entirely of circulation.
2. `assembly_contains_perceptual_singletons` counted closed Z-doors, which have
   no at-rest opening and so can never group with anything, making every gated
   room in any Blood map look fragmented. Now counts only non-circulation
   singletons.
3. `assembly_lacks_dominant_perceptual_space` counted sectors, so it called the
   gallery fragmented for being one 392 player-area room between two 16
   player-area arches. Now weighs floor area.

Two dimensions were **missing entirely** until the project owner named the
symptom: corpus-relative scale and shape. Three iterations had passed every gate
with zero discrepancies while the level was a pure axis-aligned grid with rooms
in the bottom decile of the corpus for height. The packet was not wrong about
what it measured; it had no way to measure those things. A third gap — sprite
world size against the room it stands in — was found the same way and closed.

All four iterations are reported under the corrected rules, so their rows are
comparable. The pre-correction output is not preserved and must not be compared
against them.

## What is verified, derived, interpreted, and unknown

**Verified.** Every MAP parses, validates natively and against the strict
authored-geometry gate, conserves its source edges, realizes every declared
portal, compiles byte-identically twice, and reaches NBlood revision
`rlocal-agtst10`'s initialized game loop. Sector, wall, sprite, tile, shade, and
coordinate values are exact. All 42 viewpoint captures produced a preserved PNG
from a variant that differed from its candidate only in the player-start pose.

**Derived.** Perceptual spaces, assemblies, connections, and every discrepancy
come from static approximations documented in the decompiler's own limitations.
Corpus percentiles are relative to 42 campaign maps, not universal constants.
Material roles are mined from corpus usage.

**Interpreted by the LLM.** Every claim, priority, and design decision in
`design/reviews/*.json`, including the judgement that three low crypt spaces
should stay low, that the exterior stairs belong to the courtyard, and that the
remaining rectangularity is not worth further chamfering.

**Unknown.** Why the parallax sky renders as dark as it does. Whether the
shade-step thresholds are experienced as thresholds by a player. Whether tile
449's mined `stone_masonry` role or its root-like rendered appearance is right.
Anything about combat, pacing, enemy placement, sound, or how the level plays —
nothing in this pilot measures any of it.

## The next bottleneck

Orientation variety. The level occupies 6 of 36 orientation bins against a corpus
minimum of 15, and its chamfer fraction is now *above* the corpus maximum because
every cut corner is a chamfer. Chamfering reaches four orientations; adding
shallow facets reached six. Original maps reach thirty-six because they contain
genuinely curved, segmented-arc geometry built from many small angle steps.
`PlanarLayout` can express that today, but nothing in the loop helps an author
compose it, and no precedent in the packet describes how originals build one.
Further chamfering would push one metric past the corpus while leaving another at
the floor — fitting the measurement rather than the brief.
