# Design layers — what lives where, and what may touch what

The project's structure for Blood City. Each layer states what it contains,
what it must not contain, its review artifact, and its conformance check.
The locality rule between layers: an L3 edit never touches L1; an L1 change
regenerates the L2 skeleton and L3 attachments survive by name. Where the
grammar cannot yet support that survival, the gap goes to
[../reports/grammar-requests.md](../reports/grammar-requests.md) — it is
never a reason to author geometry globally.

Process rule (owner directive, 2026-08-27): **no blocking human gates.**
Each layer's checks are automated; passing them advances the work. Human
judgment accumulates in [../reports/review-queue.md](../reports/review-queue.md),
ordered by rework cost, and batch feedback lands as normal iteration work at
whatever layer it names. From the first walkable skeleton on, every iteration
ends with an engine-loadable MAP at `level/blood-city-current.MAP`. Anything
fun-critical that automation cannot judge is flagged **fun-unvalidated** in
the queue, and replication prefers owner-played patterns over unplayed ones.

## L0 — Identity

- **Is**: prose. The city's name, hour, reason to exist, landmark, district
  identities. [city-identity.md](city-identity.md).
- **Must not contain**: numbers that belong to contracts (those live in the
  mined references), geometry, materials by id.
- **Review artifact**: the page itself.
- **Conformance check**: every lower-layer choice must be defensible from
  it; a choice that is not is an L0 amendment or a bug.

## L1 — Schematic plan

- **Is**: the city as data — [../level/city_plan.py](../level/city_plan.py).
  Districts; the street network as a graph whose edges carry a **width
  class**, not units; blocks with a **role** (superblock / free-standing /
  frontage); venue slots typed from [venue-patterns.md](venue-patterns.md)
  and placed on named frontages; the sewer subgraph with its entries; the
  roof-route stack positions; the main circuit; the channel budget per
  district. Schematic coordinates (1 pu, plotted at 1024 Build units for
  side-by-side comparability) exist only for the plotter.
- **Must not contain**: Build units beyond the plotting convention, picnums,
  z values, sector-level geometry.
- **Review artifact**: the L1 plot (`plots/gravesend-l1-plan.png`) rendered
  side-by-side comparable with the precedent plans, plus the measured
  contract table (`../reports/plan-contract-check.md`).
- **Conformance check**: every Phase 0 contract row computes green from the
  data itself; a row that cannot pass is a plan bug. Green advances to L2
  automatically; the plot, table, and judgment calls go to the review queue.

## L2 — Massing geometry

- **Is**: PlanarLayout regions derived from L1 by
  [../level/build_skeleton.py](../level/build_skeleton.py) — district
  assemblies with inherited style, streets as the flexible elements
  (width classes resolved to units from the city-norms bands), blocks
  carved as holes (the E2M6 precedent), stacks declared, the sewer at
  depth. **Derived, never authored freehand**: a hand edit to L2 output is
  a bug by definition.
- **Must not contain**: facades, interiors, decoration, population.
- **Review artifact**: compiled MAP + the same classifier plot the
  precedents got.
- **Conformance check**: `tools/mine_city_norms.py` runs on the compiled
  skeleton and its reading (street component, loops, blocks, widths) is
  diffed against what L1 declares — `../reports/plan-conformance.md`. The
  diff is a standing per-iteration check; drift is a finding, never silent.
  Bot navigation smoke on the main circuit as soon as it is walkable.

## L3 — Architecture and dressing

- **Is**: facades, Apertures (leaf + mediation), interiors, materials,
  lighting, population — attached to L2 **by names and anchors** (region
  ids derive from L1 element names, faces are named, prefabs stamp into
  frames).
- **Must not contain**: street-network or massing decisions; those are L1/L2
  edits that regenerate downward.
- **Review artifact**: per-district iteration packets — pose-set renders at
  standing eye height, budget report, norms comparison (rates, never
  counts).
- **Conformance check**: registry rules at their derived enforcement
  levels; discriminator and blandness inside campaign bands; per-district
  wall caps (≈700–1100 norm); the L2 conformance diff stays clean.

## Phasing under the layers

Phase 1a authors L1; 1b plots and proves it (green table advances
automatically); 1c derives the L2 skeleton and closes the conformance loop.
Phase 2 builds **one pilot district end-to-end** through L3 — chosen for
most patterns exercised per wall — and proceeds to replication when full
automated acceptance passes, with the district marked owner-play-pending in
the review queue. Replication across the remaining districts is then L1 plan
plus proven per-district pattern. Iteration packets are per-district;
whole-city integration packets run at phase boundaries only.
