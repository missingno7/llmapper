# BB2 v2 geometry and connectivity audit

Source: `work/BB2-semantic-reconstruction-v2.MAP`  
Machine packet: `reports/BB2-v2-geometry-audit.json`  
Overlay: `reports/BB2-v2-geometry-audit.svg` (local; `reports/*.svg` is gitignored)

`validate_map()` reports **0 native errors**. The authored audit reports **151 errors**.
The map is structurally serializable and topologically broken.

## Traversal

- 15 at-rest components; largest has 10 of 27 sectors
- walkable-at-rest edges: 14
- DM starts in the main network: **3 / 8**
- Unreachable DM starts: sprites 63, 65, 66, 67, 69 in sectors 6, 8, 5, 15, 17
- Zero-exit sectors: 3, 5, 6, 8, 14, 18, 19, 20, 21, 22, 23, 26

Sealed “hunting yards” are not concealed alcoves. They are outdoor polygons
with no reciprocal portal into the courtyard.

## What sealed every isolated space

`LevelBuilder.connect()` requires exact reversed coincident endpoints.
v2 placed irregular outdoor masses so that intended mouths were:

- partial collinear overlaps of different length (20 findings), or
- T-junctions where a yard corner sits on a longer courtyard wall (38 findings),

and never became portals. Ordinary validation does not care.

Those walls remain one-sided. In the editor they look like infinitely thin
solid partitions because they are ordinary Build walls that happen to lie on
another sector’s boundary without `next_wall` pairing.

## Boundary conflicts (exact classes)

| class | count | meaning |
| --- | ---: | --- |
| proper crossings | 13 | unrelated edges cross; e.g. walls 3×128 at integer (19968, 6144) |
| T-junctions | 38 | endpoint-on-segment, longer wall not split |
| partial collinear overlaps | 20 | shared interval, not exact reversed match; not portaled |
| exact reversed coincident unpaired | 2 | same undirected segment, opposite directions, no portal |
| exact same-direction coincident | 5 | duplicate directed ownership |
| sub-body wall fragments | 43 | wall midpoint strictly inside another sector |

None of these are engine-legal “thin fences” with XWALL roles. They are
construction leftovers.

## Sector footprint intersections

Actual polygon tests, not AABBs. Fail-closed unless a water/stack marker pair
is present.

Accidental same-layer overlaps with overlapping Z (not legitimate stacks):

- 0∩23, 2∩16, 2∩17, 3∩4, 3∩14, 3∩23, 5∩14, 5∩23, 7∩17, 8∩19

`3⊃4` is full containment at the same outdoor Z interval `[-112640, 0]`: a
smaller outdoor mass sitting inside a larger one with no hole carved.

XY overlap with only touching Z, still undeclared (ambiguous point-in-sector):

- 0∩22 (`[-112640,0]` vs `[0,0]` door slab), 3∩26, 5∩22

Legitimate Blood water/stack (markers present; accepted):

- 3⊃25, 4⊃26, 25⊃26 — underwater continuation, vertically touching or stacked

No overlap was a declared hole: v2 never represented buildings as host loops
with holes. It overlaid independent polygons on the courtyard.

## Missing primitives (not wall-ID patches)

1. **Collinear split-and-stitch** — partial reversed overlap and T-junctions
   must become atomic reversed coincidences before `connect`.
2. **Hole-aware / building-shell construction** — outer footprint carved from
   the host, inner footprint inset, doorway sectors through the thickness.
   Overlaying a building polygon on a field is not a wall.
3. **Authored-geometry validator** — `validate_map()` cannot be the feasibility
   gate for scratch maps.

## Overlay legend

cyan reciprocal portals · orange unpaired coincident · magenta partial
collinear · yellow T-junctions · red crossings / overlapping fills · gray
isolated sectors
