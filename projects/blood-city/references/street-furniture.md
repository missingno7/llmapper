# Street furniture — the open-space vocabulary

Time-boxed pass (owner directive, 2026-08-27): DWE3M1 first, then E3M1,
TEDE1M2, DWE3M10, swept via the urban-semantics labels (open space = street
∪ courtyard; geometry islands = small sectors offset ≥1024 z from a much
larger open neighbour). One pass, done when it covers what the four sources
show. Tile ids reported as data; identity resolves at L3 against Blood art.

## Elements, with construction and budget

- **Fountain / basin** (DWE3M1 sectors 40/41 — twin basins): sunken sector
  at **−4096 z**, ~1.3–1.7M area (~1200 on a side), water-class floor
  (pic 404 there), optionally a raised rim at +1024. Bigger ponds run
  −8192..−35840 (sectors 26, 20). *Placement: centred in a plaza or
  terminating a walk.* **Budget ≈ 2 sectors / 8–16 walls / 0–2 sprites.**
- **Green / park terrace** (DWE3M1 sector 49: +2048, 10.5M, soft floor
  pic 374; big terraces 14/15/17): a raised soft-floor region with
  planting as face sprites (DWE3M1 carries 110× tile 2621 + 75× tile 599
  in its open space — its planting library). **A green differs from a
  plaza** in exactly the mined ways: raised 2048, soft floor material,
  planting density an order above the paving, and edging (the rise is the
  enclosure). The typed classifier gains a `green` area kind. **Budget ≈
  1–3 sectors / 6–20 walls / planting ~1 sprite per 1M area.**
- **Well** (DWE3M1 553/554, TEDE1M2 572): small shaft ~0.5M area
  (700–800 square), floor **−5120..−12288**, rim as the sector's own walls.
  *Placement: square centre (TEDE1M2) or court edge.* **Budget ≈ 1–2
  sectors / 4–8 walls.**
- **Market stall** (TEDE1M2 453–455 stepped platforms +3072..+9216,
  sector 300 +4096 2.6M; DWE3M10 148/149 +4096 pair): platform at
  **+3072–4096**, 1–2.6M area, goods as face sprites on top, canvas/awning
  as wall sprites (TEDE1M2's 79 wall sprites in open space: tiles 389,
  659). *Placement: edging a plaza or square, in runs of 2–3.* **Budget ≈
  1 sector / 4–6 walls / 3–6 sprites each.**
- **Bench / trough** (DWE3M10 145/146: +2048, ~1.2M twins): low platform
  pairs along a walk edge. **1 sector / 4 walls each.**
- **Cart / cargo** (DWE3M10 151–153: +6144 platforms; barrel-class sprite
  clusters, tile 505 ×16): either a +6144 platform with goods sprites or a
  pure sprite cluster. *Placement: quaysides, yards.* Industrial spaces
  (the works yard) take carts/cargo, not fountains.
- **Lamps** (tiles 2519/2520/2521 across every source): face sprites at
  thresholds and along walks; E3M1's town runs 45 light props over its
  ~192k frontage ≈ **one lamp per 4–5k units of frontage**, denser at
  mouths (venue-patterns' marquee rule).
- **Monument / plinth**: the free-standing mass (already in the plan) over
  a +2048 plinth island.

Open-space sprite density, measured with the caveat that landscape dilutes
it: town cores 4.0–4.2 sprites/10M of open area (E3M1, TEDE1M2); the
number to hold when furnishing a plaza.

## L1 furnishing slots (added to city_plan AREAS)

- `market_plaza`: fountain centred (the monument keeps its loop, the
  fountain sits off-axis toward the market hall), stall run of 3 on the
  west edge, lamps at the four mouths. The plaza keeps hard paving — it is
  a plaza, not a green.
- `well_square`: the well centred (TEDE1M2 precedent), one bench pair,
  lamps.
- `theatre_forecourt`: the kiosk stands (existing mass); lamps per the
  marquee rule dominate here — no basin (gaslight, not water, is Theatre
  Row's identity).
- `works_yard`: cart platform + cargo sprites (industrial vocabulary),
  lamps at the stair mouth and gatehouse; explicitly **no fountain** —
  the sources put water features in civic space only.
- `cemetery` (church-patterns.md already carries its own vocabulary:
  tombstones as wall/face sprites, lanterns).
