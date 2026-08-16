# BB2 semantic roundtrip

Independent descriptions compared in **design space**, not polygon space.

```text
BB2.MAP → Understanding A (reports/BB2-understanding.md)
                ↓
     blind reconstruction
                ↓
candidate.MAP → Understanding B (reports/BB2-reconstruction-understanding.md)
                ↓
          A ≈ B  ?
```

Understanding B was frozen before this file was written. It did not read
Understanding A. Geometry of BB2.MAP is used here only to *explain* claim
mismatches after both prose documents existed.

No single similarity score is computed.

---

## 1. Level identity

| claim | A (BB2) | B (candidate) | delta |
| --- | --- | --- | --- |
| Game | Blood v7 DM compound, no campaign progression | Blood v7 DM compound, no campaign progression | PRESERVED |
| Purpose | FFA with flag bases as opposite-end anchors | DM / CTF compound with flag bases | APPROXIMATELY PRESERVED |
| Spatial character | square walled outdoor-majority killing field with masonry interiors punched in | square enclosed outdoor-majority yard with west strip, porch, pavilion, east water | APPROXIMATELY PRESERVED |
| Bounded vs open | compound, not wilderness (lateral enclosure ~0.87 with sky) | compound, not wilderness (lateral enclosure ~0.88 with sky) | PRESERVED |
| Outdoor / interior | sky ~2/3 footprint, covered ~1/3; covered *sectors* more numerous | sky ~3/4 footprint, covered ~1/4; sky *sectors* more numerous | APPROXIMATELY PRESERVED (footprint) / INVERTED (sector majority) |

**Would both descriptions make a designer imagine the same broad kind of level?**
Yes: a square Blood deathmatch compound, tall sky field, lower interiors, flags,
gated prizes, water Tesla. They would not imagine the same *grain* of
architecture or the same spawn yards.

**Profile:** strong match.

---

## 2. Spatial scale

| | A | B | delta |
| --- | --- | --- | --- |
| AABB | 128 × 128 widths | 80 × 80 widths | APPROXIMATELY PRESERVED (same shape, smaller) |
| Sky footprint | ~4589 player-areas | ~4885 | APPROXIMATELY PRESERVED |
| Covered footprint | ~2513 | ~1658 | APPROXIMATELY PRESERVED (same order, thinner interiors) |
| Outdoor height | typically 17–23 PH (sky median ~15.6 including zero-height movers) | uniformly 20 PH | APPROXIMATELY PRESERVED / EXAGGERATED uniformity |
| Indoor height | ~5–11 PH (median ~5.1) | ~6 PH (doors 0 at rest) | APPROXIMATELY PRESERVED |
| Height contrast | ~3× indoor→outdoor | 3.33× | PRESERVED |
| Typical opening | median 2.67 widths (corpus-typical); max ~21 | median 8 widths; min 2.67; max 24 | EXAGGERATED typical width |
| Outdoor Z | several related elevations; outdoor floor-drop lift | single plane Z = 0 | LOST |

B is a smaller, simpler, flatter, wider-ported version of the same height
contrast. Open-space *area* is similar; covered *area* shrank; connector
scale jumped from Blood-typical 2.67 to a coarse 8-width grid.

**Profile:** strong match on height/enclosure contrast; partial match on
footprint; weak match on connector grain and outdoor Z.

---

## 3. Spatial organization

| | A | B | delta |
| --- | --- | --- | --- |
| Major open component | one traversal component; outdoor *sight* broken by buildings; largest connected sky region ~2789 areas / 19 sectors | almost all sky is one connected region (~4679 / 72) | LOST (sky fragmentation) |
| Embedded structures | many masonry interiors punched into the field | west strip, south porch, center pavilion, north sheds | APPROXIMATELY PRESERVED as roles, LOST as irregular mass |
| Covered pockets | more covered sectors than sky; porches/sheds/buildings | fewer covered sectors; a handful of rectangles | INVERTED sector mix |
| Loops | loop around and through buildings | ring around a pavilion | APPROXIMATELY PRESERVED |
| Bottlenecks | building mouths and movers | grid portals and three Z-doors | APPROXIMATELY PRESERVED role / LOST density |
| Alternate routes | optional indoor shortcuts | west indoor plus ring | APPROXIMATELY PRESERVED |
| Nav regions | 2 (151 + 3) | 1 (100) | APPROXIMATELY PRESERVED (still one dominant) |

Both descriptions say: outdoor connector, interiors as loot/cover, water on
one side, flags at opposite ends, west indoor cluster. B’s outdoor is a
**single rectangular courtyard system**; A’s outdoor is a **continuous walk
with fragmented sky and broken sight**.

**Profile:** strong match on program; weak match on how open space is cut.

---

## 4. Architectural morphology

New general sensor. Not in the original prose as numbers; recovered from both
MAPs after B was frozen.

| | A (BB2.MAP) | B (candidate) |
| --- | --- | --- |
| Orthogonal length | 0.73 | 1.00 |
| Diagonal length | 0.06 | 0.00 |
| Orientation diversity (5° bins / 36) | **0.94** (34 bins) | **0.06** (2 bins) |
| Rectangular sector fraction | 0.30 | 1.00 |
| Convex sector fraction | 0.69 | 1.00 |
| Outer vertices median / max | 5 / 40 | 4 / 4 |
| AABB fill mean | 0.78 | 1.00 |
| Chamfer fraction | 0.036 | 0.00 |
| Segmented-arc chains | 29 | 0 |

A’s prose said “masonry interiors punched into” a compound and never stated
orientation diversity. B’s independent reading says the architecture is an
orthogonal rectangular grid. That is an accurate description of B, and it is
**not** a description of A.

**Delta: LOST.** This is the rectangular reconstruction failure, now
measurable.

Cause: `UNDERSTANDING INFORMATION LOSS` (prose had spatial roles, not
geometric language) plus `BUILDER REASONING FAILURE` (the construction API
already accepts arbitrary polygons; the builder chose a Cartesian grid).

**Profile:** weak match.

---

## 5. Spawn experience

Pairwise 2D spawn LOS: A **1/28** clear (two outdoor starts); B **0/28**.
Concealment is PRESERVED and slightly EXAGGERATED.

Neighborhood sensor (the distinction pairwise LOS cannot make):

| | A | B |
| --- | --- | --- |
| Outdoor / indoor DM starts | 5 / 3 | 5 / 3 |
| Spawn sector areas | 28–455 (several 300+) | 32–162 (none in the 300–455 band) |
| Local 16-width area | 249–896 | 176–653 (high values are *indoor* west cluster) |
| Portal choices | 2–8 (outdoor often 5–8) | 1–3 |
| Hops to largest sky region | 0–13, mixed | outdoor mostly 0; indoor 1–5 |
| Sky-ray fraction into that region | two starts 1.0; others ~0 | four outdoor 1.0; indoor/porch/NW 0.16–0.31 |
| Median 2D sight at spawn | ~2–14 widths | ~6.5–8.7 widths |
| Max 2D sight | outdoor ~50–73; enclosed indoor ~12 | outdoor 18–80; indoor 16–33 |

A: several starts sit in **large sky neighborhoods** with many exits and long
max sight, still mostly unable to see other starts because **building mass
fragments the field**. B: starts sit in **small grid cells** with 1–3 exits;
concealment is **local enclosure**. West indoor local area is large in B only
because the west block is one connected rectangle cluster, not because the
spawn occupies a hunting ground.

**Spawn concealment:** PRESERVED  
**Spawn neighborhood openness:** LOST  
**Spawn → main circulation:** PARTIAL (indoor still duck into a strip; outdoor
B starts are already in the one courtyard but in a closet-scale cell)  
**Spawn → resources:** APPROXIMATELY PRESERVED (flags adjacent to N/S starts;
several starts share a cell with a weapon)

The sensor **does** distinguish hunting-ground starts from enclosed closets:
A’s southern outdoor start is 455 areas, 8 portals, hops 0, sky-ray 1.0, max
sight 73. B’s smallest start is 32 areas, 3 portals, hops 1, sky-ray 0.25.
Pairwise LOS is ~0 in both.

**Profile:** strong match on concealment; weak match on neighborhood character.

---

## 6. Route experience

| | A | B |
| --- | --- | --- |
| Outdoor route sky fraction | 0.75–1.0 | 0.93–1.0 |
| Indoor route sky fraction | 0.27–0.44 | 0.64–0.88 |
| Cover↔sky transitions | 0–3 | 0–2 (indoor typically 1) |
| Mean max sight along route | ~36–58 widths | ~46–60 widths |

A’s indoor routes spend most samples under cover and cross sky/cover more
than once. B’s indoor routes take **one** transition onto a long-sight ring.
A’s outdoor routes still clip buildings (sky fraction sometimes 0.75). B’s
outdoor routes are almost pure sky.

Hunting ground / covered movement / short refuge / open re-entry: A has all
four in the route samples. B has hunting ground and a short indoor strip;
refuge is the spawn cell; re-entry is a single portal onto the ring.

**Delta:** APPROXIMATELY PRESERVED outdoor exposure; LOST covered-travel
share and multi-transition routes.

Route exposure **does** explain what pairwise LOS could not: both maps hide
spawns from each other; A then dumps the player into a wide, building-broken
field, while B dumps them into a grid ring after a closet or a short hall.

**Profile:** partial / weak match.

---

## 7. Resources and multiplayer incentives

| | A | B | delta |
| --- | --- | --- | --- |
| Flags opposite ends | N outdoor / S covered | N outdoor / S covered | PRESERVED |
| Super armor gated | yes (two switches, ceiling) | yes (two switches, Z-door) | PRESERVED |
| Cloak gated | yes | yes | PRESERVED |
| Akimbo gated | yes | yes | PRESERVED |
| Tesla underwater | yes | yes | PRESERVED |
| Napalm as field prize | outdoor, nearer middle | outdoor, beside pavilion | PRESERVED |
| Weapon set | shotgun, tommy, flare×2, tesla, napalm | same types (counts differ) | APPROXIMATELY PRESERVED |
| Ammo | 47 piles | 18 piles | LOST density |
| Health / armor counts | 7 / 7 | 6 / 5 | APPROXIMATELY PRESERVED |
| Ammo as constant fire | explicit in A | sparse in B | LOST |

Roles survive. Density and “generous ammo” collapse.

**Profile:** strong match on high-value roles; weak match on ammo density.

---

## 8. Mechanisms

| | A | B | delta |
| --- | --- | --- | --- |
| Z-motion | 13 (doors, hatches, outdoor lift, squeezes) | 3 (item Z-doors only) | LOST diversity |
| Slide-marked | 4 | 0 | LOST |
| Rotators | 6 | 0 | LOST |
| Gib walls | 10 | 1 | LOST density |
| Water links | 2 pairs, 3 underwater | 2 pairs, 2 underwater | APPROXIMATELY PRESERVED |
| Match-start sting | channel 8 → 119 → SFX | same pattern | PRESERVED |
| Ambient 710 | 37 | 3 | LOST density |
| Outdoor lift | ~6 PH floor drop | none | LOST |

Same *design roles* for gated prizes, water, and match sting. A has a richer
mechanism vocabulary that changes local circulation, sight (masked gibs), and
outdoor Z. B implements the contract items as three identical Z-doors.

**Delta:** PRESERVED gated-item role; LOST toybox diversity.

**Profile:** partial match.

---

## 9. Materials / visual grammar

| | A | B | delta |
| --- | --- | --- | --- |
| Sky sheet 2500 | yes | yes | PRESERVED |
| Outdoor floor | 2448 organic earth (gray mottled) | 270 organic earth (brown dirt) | APPROXIMATELY PRESERVED class / LOST identity |
| Outdoor walls | 2455 red brick, 2492 masonry, 91 stone, 5 brick | 110 stone only | LOST mix |
| Indoor walls | brick/stone mix including unannotated 2455 | 5 brick | APPROXIMATELY PRESERVED “brick interiors” |
| Indoor floor | 110 stone used horizontally | 2448 earth | INVERTED vs A’s indoor stone floor |
| Indoor ceiling | 385 (vertical brick used as ceiling) | 416 (true indoor ceiling fill) | B more role-correct; A’s identity lost |
| Water surface | distinct from outdoor gray ground | tile 90 mixed-use unknown | APPROXIMATELY PRESERVED as “not the dirt” / weak readability |
| Masked / gibs | 18 masked, several overpics | 1 masked fence 330 | LOST |
| Lighting | not in A’s sensors; B measured as flat shade 16/8/0 | flat | UNMEASURABLE in A / NEW observation in B |
| Visibility 800 / sky type 2 | yes | yes | PRESERVED |

Exact picnum identity was never the primary metric. Outdoor earth-vs-sky vs
indoor brick is shared. A’s distinctive gray 2448 field and mixed masonry
skins do not survive. B accidentally used A’s *indoor* floor tile (2448) as
*outdoor* ground? No: A outdoor is 2448, B outdoor is 270, B indoor is 2448.
So B swapped the campaign earth tiles relative to A.

**Profile:** partial match.

---

## 10. Landmarks and orientation

Both descriptions: sky vs ceiling, opposite flags, water/Tesla on one side,
west indoor cluster, square compound wall, height contrast. Neither claims a
unique monument.

A adds: super-armor two-switch room as memorable; masked breakable screens;
irregular building silhouettes (now measurable). B’s landmarks are the same
*program* on a grid — flags, water, west brick, pavilion — with little unique
mass.

**Would a player orient with similar kinds of cues?** Yes for mode objects and
enclosure; no for architectural silhouette.

**Profile:** strong match on cue *kinds*; weak match on unique mass.

---

## 11. Important transitions

| transition | A | B | delta |
| --- | --- | --- | --- |
| Interior → exterior | sky 0→1, height ~5→~18, sight ~12→~50+ | sky 0→1, height 6→20, route sight ~7→~50 | PRESERVED |
| Tight → open | building mouth; median portal still 2.67 | spawn cell → 8-width ring | APPROXIMATELY PRESERVED |
| Covered → exposed | multiple along indoor routes | typically one | APPROXIMATELY PRESERVED / simplified |
| Route → water Tesla | edge pocket, unique floor, swim | east bay, tile 90, swim | PRESERVED |
| Ordinary → gated prize | switch/mover rooms, some slides/rotators | three identical Z-doors | APPROXIMATELY PRESERVED role |

**Profile:** strong match on the interior↔exterior jump; partial on how often
it happens along a route.

---

## Semantic delta (important differences)

| property | class | reason | likely cause |
| --- | --- | --- | --- |
| DM mode / 8 starts / square compound | PRESERVED | both readings | — |
| Outdoor-majority footprint | APPROXIMATELY PRESERVED | 2/3 vs 3/4 | builder coarsened interiors |
| Covered-sector majority | INVERTED | A 116 vs 63 sky; B 34 vs 78 sky | BUILDER REASONING FAILURE (prose had both footprint and sector count) |
| Height contrast ~3× | PRESERVED | 17–23 vs 5–11 vs B 20 vs 6 | — |
| Outdoor Z variation | LOST | A related elevations + lift; B plane | UNDERSTANDING INFORMATION LOSS + BUILDER |
| Spawn-pair concealment | PRESERVED (EXAGGERATED 0/28 vs 1/28) | both near-zero | builder optimized the 28-pair matrix |
| Spawn neighborhood openness | LOST | A 110–455 / 5–8 exits; B 32–162 / 1–3 exits | MISSING SENSOR in A (now added) + BUILDER optimizing LOS |
| Route covered-travel | LOST / weakened | A indoor sky-fraction ~0.3; B ~0.7 | same |
| Sky fragmentation | LOST | A largest sky 2789/4589; B 4679/4885 | UNDERSTANDING INFORMATION LOSS (one “exterior”) |
| Architectural morphology | LOST | diversity 0.94 vs 0.06; rectangular 0.30 vs 1.00 | UNDERSTANDING INFORMATION LOSS (no geometric language) |
| Gated prizes + flags + Tesla | PRESERVED | same roles | — |
| Ammo density | LOST | 47 vs 18 | BUILDER (prose said abundant) |
| Mechanism toybox | LOST | 13Z+4 slide+6 rot+10 gib vs 3Z+1 gib | DELIBERATE BOTTLENECK + INFORMATION LOSS |
| Outdoor floor identity 2448 | LOST | B used 270 | MATERIAL / builder kit |
| Lighting | UNMEASURABLE in A | B flat; A unmeasured | MISSING SENSOR |

---

## Self-consistency of the two documents

If we ignored the source MAPs and judged only the two independent readings:

```text
mode / purpose                   strong match
macro spatial organization      strong match
height/enclosure                 strong match
spawn concealment               strong match
spawn neighborhood character    weak match
resource roles                  strong match
ammo density                    weak match
mechanism diversity             partial match
architectural morphology        weak match
materials                       partial match
route exposure                  weak match
outdoor Z / terraces            weak match
landmarks (cue kinds)           strong match
landmarks (silhouette)          weak match
```

The roundtrip **closes** on: what kind of level this is, height contrast,
flags, gated power, water Tesla, spawn-pair blindness, interior↔exterior.

It **breaks** on: geometric language of mass, spawn-yard scale vs closet
scale, how the outdoor field is fragmented, mechanism vocabulary, ammo
generosity, outdoor floor identity.

That is evidence that the first prose preserved **program** and lost
**morphology and neighborhood exposure**. Those are now sensors, not hunches.

---

## Semantic Level Roundtrip (benchmark concept)

Definition:

```text
Map A
  → independent understanding
  → (optional design contract)
  → blind construction of Map B
  → independent understanding of Map B
  → multidimensional semantic comparison
```

Invariant under test: `Understand(A) ≈ Understand(B)` in design claims,
**not** `geometry(A) ≈ geometry(B)`.

Reusable command (sensor freeze, not a scorer):

```text
python -m bloodmap understand MAP --multiplayer-only -o work/foo-understand.json
python -m bloodmap spawn-neighborhood MAP --multiplayer-only
python -m bloodmap route-exposure MAP --multiplayer-only
python -m bloodmap morphology MAP
```

Prose remains an agent-written bottleneck. Do not maximize lexical similarity
between Markdown files. Do not emit a single `semantic_similarity` number.

This BB2 pass is the first recorded instance of the benchmark.
