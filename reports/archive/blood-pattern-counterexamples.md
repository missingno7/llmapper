# Blood design-pattern counterexamples

Failed interpretations. These are as important as the clusters.

## Outdoor spawn is concealed

**Rejected.** `sky + hops 0 + hunting-cell` does not imply spawn-to-spawn
concealment.

BB6's four large-yard starts match the hunting-cell signature and have
pairwise 2D sight **28/28 clear**. The same map's roses still hit occluders
in every direction: the world is bounded, but the starts see each other in
2D. BB2 is closer to the concealed-hunting-ground story the BB2 roundtrip
cared about. Treating "outdoor" as "hidden" overfits BB2.

`pattern:spawn:pairwise-2d-exposed` is kept as **disputed**: high 2D peek is
real, and it is not 3D concealment. Floor delta is ignored by the sight
sensor. BB6 lower-Z starts may be vertically offset from yard starts.

## One exit is a closet

**Rejected.** BB6 has 1-exit sky pads whose local reachable area is still the
large field (`pattern:spawn:sky-porch-into-field`). Exit count without local
area and hops is not a room type.

## All-sky shortest path means no interiors

**Rejected.** Every BB6 start-to-largest-sky route is cover-sequence `S`.
BB6 still has 151 covered sectors, 11 holed outdoor loops, and 39 sectors
unreachable at rest (gated / state-dependent). The route sensor only walks
start → largest sky.

## Cover → open is a reveal

**Not established.** CS routes recur, especially in the campaign. Some are
storey-scale with shade change; some are flat in Z and shade. Geometry
sequence alone does not distinguish a staged reveal from a mundane doorway.
Needs visibility, material, landmark, or resource context before the
interpretation is supported.

## A rectangle is a room

**Rejected.** Axis-aligned 4-vertex covered cells are the modal footprint in
both original populations (202 BloodBath, 3495 campaign). The same signature
is storage, stairs, porches, and generic interiors. Status: **disputed** as a
design pattern; useful as a construction-default warning.

## A storey delta is an overlook

**Rejected as a default reading.** Storey-scale same-cover transitions into a
larger cell are the most common vertical signature on all 9 BloodBath maps
and 40 campaign maps. Most are ordinary stairs. Overlook / high-path
relationships need visibility and route context that this signature does not
carry.

## Blood maps generally spawn into outdoor hunting space

**Population-specific, not universal.** Original campaign routes are mostly
cover-then-open from an indoor start. Original BloodBath BB6 is all-sky
shortest paths from outdoor starts. Mixing E* and BB* would invent a false
global spawn style.
