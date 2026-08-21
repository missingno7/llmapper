# Cliffside monastery: six evidence-driven iterations

The machine-readable version is `comparison.json`. Each iteration's full packet
is `v*/iteration.json`, its readable digest `v*/summary.md`, its rendered frames
`v*/views/`, and the reasoning that drove the next one
`../design/reviews/v*.json`.

Every number below was produced by `bloodmap.authoring_loop` from the compiled
MAP. None of it comes from the authored labels.

## Dimensions, not a score

| | v0 | v1 | v2 | v3 | v4 | v5 |
| --- | --- | --- | --- | --- | --- | --- |
| **hard validation** | 0 failed | 0 failed | 0 failed | 0 failed | 0 failed | 0 failed |
| NBlood load smoke | pass | pass | pass | pass | pass | pass |
| views captured / passing | 8 / 8 | 11 / 11 | 11 / 11 | 12 / 12 | 14 / 14 | 18 / 18 |
| views that look up | 0 | 0 | 0 | 0 | 0 | **4** |
| **authored vs observed hierarchy** | 1 discrepancy | 0 | 0 | 0 | 0 | 0 |
| derived spaces | 9 | 14 | 14 | 14 | 16 | 16 |
| derived structures | 8 | 9 | 9 | 11 | 14 | 15 |
| **vertical relationships** (overlooks) | 0 | 0 | 0 | 0 | **3** | 3 |
| **material** | | | | | | |
| identical room-treatment pairs | 4 | 2 | 1 | 1 | 1 | **0** |
| single-surface sectors | 0.433 (p97.7) | 0.387 | 0.387 | 0.387 | 0.368 | **0.079 (p41.9)** |
| oversized decorations | 0 | 0 | **18** | 0 | 0 | 0 |
| visually empty derived spaces | 5 | 10 | 6 | 5 | 6 | 6 |
| sprites | 5 | 5 | 56 | 60 | 60 | 60 |
| **shape vs 42 campaign maps** | | | | | | |
| orientation bins occupied | 2 (p0) | 2 | 2 | 6 (p0) | 5 (p0) | **17 (p4.8)** |
| segmented-arc chains | 0 | 0 | 0 | 9 | 9 | **15 (p31)** |
| chamfer fraction | 0.000 | 0.000 | 0.000 | 0.305 (p100) | 0.263 | **0.185 (p97.6)** |
| diagonal wall length | 0.000 | 0.000 | 0.000 | 0.117 | 0.107 | 0.090 |
| rectangular sector fraction | 0.767 (p100) | 0.742 | 0.742 | 0.548 | 0.632 | 0.632 (p100) |
| **progression** | | | | | | |
| mandatory regions reachable | 28/28 | 29/29 | 29/29 | 29/29 | 36/36 | 36/36 |
| route steps, start to exit | 10 | 10 | 10 | 10 | 10 | 10 |
| gallery first adjacent along route | — | 88% | 88% | 88% | 88% | 88% |
| **major-space scale** (percentile among corpus sectors of its footprint) | | | | | | |
| courtyard | 59 | 59 | 59 | 59 | 59.3 | 59.4 |
| gallery | 19 | 19 | 19 | **57** | 56.5 | 56.3 |
| chapel | 11.5 | 11.5 | 11.5 | **35.5** | 35.5 | 35.4 |
| exit hall | 4.5 | 4.5 | 4.5 | **41** | 39.7 | 39.7 |
| crypt hall | 2.5 | 2.5 | 2.5 | **8.5** | 8.2 | 8.6 |

Sector counts went 30, 31, 31, 31, 38, 38 and wall counts 157, 167, 167, 208,
250, 295.
Object count is not on this table as a quality signal; it is here so the shape
and scale rows can be read against the size that produced them.

Mandatory reachability rises from 29/29 to 36/36 at v4 because v4 declares seven
more mandatory regions, not because anything became reachable that was not. The
crypt-hall scale percentile stays near 8 on purpose: a crypt as tall as a nave is
not a crypt, and that exception is argued in `../design/reviews/v3.json`.

Every cell comes from its own iteration's packet, and all six were re-run
together under the current rules after the sky fix, so the rows are comparable.

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

**v3 -> v4 (structure, driven by the recovered structure layer).** The
decompiler gained an architectural-structure layer after E2M3 was taken apart,
and the first thing it said about v3 was that the level contained no overlook
and no pit anywhere, across three storeys. Every height change in it was a stair
you walk up; nothing was ever seen from another height, and all 42 campaign maps
have overlooks. v4 raised the planter and the chancel out of step range and put a
tomb block in the crypt hall: 0 -> 3. All four stairs became
`vocabulary.staircase` calls, and the ascent rise moved from 3840 -- a value the
corpus never uses -- to 4096, which it uses for 771 of its 1283 stair rises. The
level's own courtyard was then flagged as a "landing" by the detector, at 1053
player areas, reproducing on purpose-built geometry the same false positive that
made 14 of the corpus's 19 landings ordinary rooms.

**v4 -> v5 (curvature and surface, plus one compiler bug).** Three findings from
v4's frames. The crypt used tile 1097 on floor, walls and ceiling in eleven
sectors and was unreadable; the corpus does use that tile that way, but at a
median of 8 player areas against our hall's 174, so it is a cell finish stretched
over a hall. Segmented arcs at the mined parameters replaced eight chamfers,
taking orientation bins from 5 to 17 -- above the corpus minimum of 15, and the
metric v3 stopped on. And the black sky, an unexplained unknown since v2, turned
out not to be the level at all: `new_level` hardcoded a one-panel sky where all
38 campaign maps with a parallax sector declare sixteen, so 360 degrees of
horizon were being mapped onto a single dark 64-pixel column of the sky tile.
That fix applies to every level this project generates.

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
