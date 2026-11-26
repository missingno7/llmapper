# BB2 semantic roundtrip — revision 3

v3 understanding was frozen from `work/BB2-semantic-reconstruction-v3.MAP`
before this comparison.

Question: did the map become a coherent playable circulation graph while
retaining v2’s morphology improvements?

Compiled from `experiments/bb2_reconstruction_v3.py` through `PlanarLayout`.
No BB2 vertices were copied. Two compiles are byte-identical
(`reports/BB2-v3-build-report.json`).

## Feasibility gates (before aesthetics)

| gate | v2 | v3 |
| --- | --- | --- |
| native validation errors | 0 | **0** |
| strict authored-geometry errors (with declared specials) | 151 | **0** |
| compile-time audit error conflicts | n/a | **0** |
| unresolved intended connections | many | **0** |
| proper crossings | 13 | **0** |
| unresolved T-junctions | 38 | **0** |
| partial collinear overlaps | 20 | **0** (stitched) |
| accidental footprint overlaps | 10+ | **0** |
| isolated DM starts | 5 | **0** |
| DM starts reaching main network | 3/8 | **8/8** |
| required open-circuit resources reachable | no | **yes** |
| gated prizes at rest | closed | **closed** (warnings only) |
| water Tesla | present | **present**, linked |
| NBlood load-smoke | n/a | **pass** (map init + game loop, 5s) |

Allowed specials listed in `reports/BB2-v3-build-report.json`: pool ↔ underwater (`water`, markers 9/10, data_1=7); armor/cloak outer masonry partitions against the host hole; rest-closed Z-doors and prize pockets (sectors 7–10, 12–13) plus the outdoor lift envelope.

MAP-only `geometry-audit` without those declarations still flags the water duplicate loop and the declared solid partitions. That is fail-closed reading of a frozen MAP, not a compile failure.

## Circulation vs v2

v2 inverted the walkable circuit: 1 reachable sector from SP, 5/8 starts
isolated, sealed sky yards. v3 restores one navigation region of 11 sectors
and 14 at-rest portals. Every spawn→sky route exists.

That was the P0/P1 requirement. It is met.

## Morphology vs v2 and A

| metric | v1 | v2 | v3 | A |
| --- | --- | --- | --- | --- |
| rectangular fraction | 1.00 | 0.30 | **0.35** | 0.30 |
| orientation diversity | 0.06 | 0.22 | **0.22** | 0.94 |
| orthogonal length | 1.00 | 0.83 | **0.79** | 0.73 |
| diagonal length | 0.00 | 0.03 | **0.05** | 0.06 |
| chamfer fraction | 0.00 | 0.13 | **0.13** | 0.036 |
| outer vertices median | 4 | 5 | **6** | 5 |

Morphology stayed in the v2 band. Rectangularity did not snap back to a grid.
Diversity is still far from A’s 0.94; that remains a later QD axis, not a
reason to break connectivity.

## Spawn / route experience

v2 had one true hunting ground and several sealed yards. v3 has two 1360-area
outdoor starts with 6 portal choices and hops=0, plus 540–628 area yards on
the same graph. Indoor starts are 40–320 areas with mouths, not isolation.

Pairwise LOS 10/28 is **more peeking than A’s 1/28** (EXAGGERATED vis-à-vis
concealment). Concealment is no longer purchased with disconnectedness.

## Profile after v3

```text
mode / purpose                   strong match
macro spatial organization       strong match (circuit restored)
height/enclosure                 strong match
spawn concealment                partial (10/28 vs 1/28)
spawn neighborhood character     strong/partial (hunting grounds real and connected)
resource roles                   strong match
ammo density                     partial
mechanism diversity              partial (Z-doors + lift + water)
architectural morphology         partial (v2 gains kept; diversity still low)
materials                        partial (same kit)
route exposure                   measurable; all eight routes exist
```

Did independently measured description move closer to the target?
**On circulation, reachability, and embedded buildings, yes. On morphology,
v2’s gains held. On spawn-peeking, it receded slightly versus A.**

## What remains before a larger QD run can be trusted

A 64-candidate local slice (`experiments/bb2_qd_slice.py`) compiled every
variant through `PlanarLayout` and archived **64/64**. Invalid geometry never
entered the archive. Morphology scores (spawn area, chamfer, orientation) moved
only after that gate.

That slice only perturbs courtyard chamfer and yard spans. It is not MAP-Elites
over free polygons. A larger search is safe only if every candidate still
compiles through the same planar compiler and hard feasibility gate. Candidates
must not skip `PlanarLayout.compile()`, and disconnected geometry must never
receive a favorable morphology score.
