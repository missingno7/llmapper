# Blood design-pattern examples

Derived from original `BB*.MAP` and `E*.MAP` mines. Labels are INTERPRETED.
Retrieval should return several precedents, not one winner.

## Spawn neighborhoods (original BloodBath)

**Open hunting cell** (`pattern:spawn:open-hunting-cell`) — 26 starts on 6 maps.

A deathmatch start already occupies a sky cell with many exits, high local
sight, and high sky-field fraction. BB6 has four of these in two large yards.
BB8 and BB9 share the same relation with slightly different area bins.

**Sky porch into field** (`pattern:spawn:sky-porch-into-field`) — 2 starts, BB6.

A tiny sky pad with one exit whose reachable neighborhood is still the large
adjacent field. This is not a closet.

**Covered hops to sky** (`pattern:spawn:covered-hops-to-sky`) — 10 starts on 5 maps.

Indoor BloodBath starts that still reach the main sky component in two or more
portal hops (BB1, BB2, BB7–BB9). Distinct from indoor-only maps (BB3–BB5)
where hops-to-sky is `none`.

## Route exposure

**All-sky shortest path** (`pattern:route:all-sky-shortest-path`) — 29 routes on 6 BB maps.

From the start to the largest sky sector, every sample is sky. BB6 is entirely
this family. That does **not** mean the map has no interiors.

**Cover then open** (`pattern:route:cover-then-open` / campaign twin) — common on
BB2/BB7–BB9 and **dominant** on original campaign maps (169 CS routes on 27
E-maps). Single-player starts typically approach outdoor space from cover.
BloodBath BB6 is the opposite.

**Open-cover-open** (`pattern:route:open-cover-open`) — 5 routes on BB1 and BB2.

Outdoor circulation interrupted by a covered mass, then sky again.

## Architectural morphology

**Irregular covered footprint** — 153 BloodBath samples on all 9 BB maps; 1431
campaign samples on 42 E-maps. Non-rectangular 9+ vertex loops with loose AABB
fill. This is closer to Blood's indoor grain than any named room type.

**Chamfered irregular** and **segmented curve chains** recur on most original
maps in both populations.

**Sky host with holes** — 11 BloodBath samples on 5 maps, including BB6. An
outdoor loop with carved masses. The useful relation is the hole, not an
octagon.

**Rectangular covered 4-vertex cell** — 202 BB + 3495 campaign samples. See
counterexamples: this is construction default, not a gameplay role.

## Vertical transitions

**Open into cover / cover into open** — leaving or entering a covered mass.
Present on BB1, BB6, BB7 and elsewhere. Often a descent on BB6.

**Storey into a larger same-cover cell** — the most common vertical signature
in both populations. Too frequent to mean "overlook" by itself.
