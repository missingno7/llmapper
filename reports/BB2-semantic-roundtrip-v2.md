# BB2 semantic roundtrip — revision 2

v2 understanding was frozen from `work/BB2-semantic-reconstruction-v2.MAP`
before this comparison.

Question: did the design-space error signal shrink without seeing BB2.MAP?

---

## What moved toward Understanding A

| dimension | v1 B | v2 | A | note |
| --- | --- | --- | --- | --- |
| Rectangular fraction | 1.00 | **0.30** | 0.30 | closed |
| Orientation diversity | 0.06 | **0.22** | 0.94 | moved, not closed |
| Orthogonal length | 1.00 | **0.83** | 0.73 | moved |
| Diagonal length | 0.00 | **0.03** | 0.06 | moved |
| Chamfer fraction | 0.00 | 0.13 | 0.036 | present (slightly EXAGGERATED) |
| Outer vertices median | 4 | **5** | 5 | closed |
| Covered sector majority | inverted (34 vs 78) | **17 vs 10** | 116 vs 63 | direction restored |
| One hunting-ground spawn | max outdoor cell 144, 1–3 exits | **720 areas, max sight 62, 3 exits** | 110–455, 5–8 exits | area/sight closed for one start; exit count still low |
| Ammo piles | 18 | **26** | 47 | moved |
| Z-motion roles | 3 item doors | **3 doors + outdoor lift** | 13 mixed | one missing role restored |
| Indoor→outdoor area ratio | 1.98 | **4.34** | 5.90 | moved |

Morphology is no longer “an orthogonal grid of rectangles.” That was the
clearest v1 semantic break, and v2 moved it using only the delta.

---

## What did not shrink, or got worse

| dimension | v1 | v2 | class |
| --- | --- | --- | --- |
| Walkable circuit / loop | one nav region, 126 walkable edges | **1 reachable sector from SP; 13 walkable edges; 5/8 starts isolated** | INVERTED / NEW failure |
| Spawn-pair LOS | 0/28 | 2/28 | still near A’s 1/28 for the connected pair; isolation is not concealment-by-design |
| Portal choices on hunting starts | 1–3 | 0–3 (zeros are sealed yards) | not closed |
| Indoor route cover share | measurable 0.64–0.88 | mostly unmeasurable (unreachable) | UNMEASURABLE |
| Orientation diversity vs 0.94 | 0.06 | 0.22 | still weak |
| Mechanism toybox | 3 Z | 4 Z | still lost slides/rotators |
| AABB 128 | 80 | 80 | unchanged (out of scope) |
| Outdoor floor 2448 | 270 | 270 | unchanged |

The builder enlarged spawn yards and broke rectangles, then **lost coincident
portals**. Large outdoor masses became sealed rooms. That is not the hunting
ground + occlusion pattern. It is a construction-topology failure.

---

## Profile after v2

```text
mode / purpose                   strong match (still)
macro spatial organization      weak match (disconnected)
height/enclosure                 strong match
spawn concealment               partial (2/28, but isolation dominates)
spawn neighborhood character    partial (one true hunting ground; several sealed yards)
resource roles                  strong match
ammo density                    partial
mechanism diversity             partial (lift restored)
architectural morphology        partial (rectangularity closed; diversity still low)
materials                       partial (unchanged kit)
route exposure                  weak / unmeasurable
```

Did the independently measured description move closer to the target?
**On morphology and one spawn yard, yes. On circulation and route experience,
no — it receded.**

---

## What the delta forced into the understanding representation

Compact measurements now in the target prose (without wall coordinates):

- spawn-sector area, local 16-width area, portal choices, hops, sky-ray fraction
- orthogonal/diagonal fractions, orientation diversity, rectangularity,
  vertex counts, chamfers, segmented-arc chains

Those were sufficient for the builder to *attempt* irregular mass and larger
yards. They were not sufficient to keep a walkable loop, because the missing
information was a **construction** primitive (portal two colinear overlapping
edges), not more BB2 vertices.

---

## Construction API audit (Phase 8)

`add_sector` already accepts arbitrary polygons. v2 used that. The block was
**connecting** those polygons: portals require exact reversed coincident
endpoints. Overlapping colinear walls of different length do not portal.

Do not add `make_blood_style_building()`. The missing primitive is closer to:

```text
split colinear overlap → connect the shared segment
```

That is CAD, not a Blood style pack. It was not implemented in this pass;
v2 ships with unmatched intended portals as evidence of the block.
