# Church and cemetery patterns — the mandatory landmark complex

Owner directive, 2026-08-27. Precedents chosen and mined by this project:
**E1M1** (Cradle to Grave — cemetery, mausoleum galleries, and a crypt
stack) and **E1M5** (Hallowed Grounds — the campaign's church interior at
full scale), via `tools/mine_room_grammar.py`
([room-grammar.json](room-grammar.json)); church *interior* prior art is the
monastery chapel in `projects/reasoned-authoring-v1` (its aperture and
chancel lessons transfer directly — the leaf-plus-mediation opening
grammar, the raised chancel over the nave, the door-face rule).

## Cemetery (E1M1)

- **Outdoor fabric, exactly as the directive expects**: the cemetery is
  walled ground with gates; tombstones are sprites (E1M1 carries 148 wall
  sprites — the highest wall-sprite count of the six maps mined — plus 364
  face sprites over 155 sectors), monuments and mausoleums are small
  masses. Cheap articulation per wall spent.
- **The mausoleum gallery module**: 4 congruent halls of ~2097k area at
  aspect 8 (sectors 33/34/46...) — long narrow tomb galleries in a row
  against the grounds' edge, each a few crypt slots deep. Twin grave-slot
  modules repeat besides (5× 262k aspect 4).
- **The crypt is a paired-sector stack**: E1M1 has 2 stack pairs, one
  overlapping in plan — the below-ground layer under the grounds is built
  exactly with the mechanism Old Crossing's roof route uses. Precedent
  confirmed for a **crypt stack under the cemetery**.
- **Spawn language**: kDudeZombieAxeBuried ×9 — the cemetery's population
  rises out of its own ground (L3 note; no other map mined uses buried
  spawns at this rate).
- Light: shade median +30, 50 animated sectors — lantern flicker among the
  stones.

## Church (E1M5, scaled by the monastery prior art)

- E1M5 at full scale: 429 sectors / 3627 walls, one 182-sector main space,
  **191 animated-shade sectors** (candle light as the dominant interior
  language), 556 face + 116 wall sprites, 68 user channels. A whole map —
  not importable, but its ratios are: the church interior is the *most*
  flicker-dense and sprite-dressed interior register in the corpus.
- The buildable church at city scale is the monastery chapel pattern:
  nave + aisles + raised chancel + apse, apertures with named leaves,
  door faces on the portals. City dose: **nave 3–4 texture-repeats tall,
  60–90 sectors, 400–600 walls, 2–4 channels** (door, bell sound, one
  secret), bell tower as the Phase 2 silhouette element.

## Placement decision (recorded as a judgment call in the review queue)

The complex anchors **Old Crossing** — the pre-boom quarter the city grew
around is where the parish church stands, and the district currently spends
its identity only on the roof route. The oc_block_b footprint (fronting the
avenue) becomes: church mass at the avenue side (its tower the west
counterpart to the Aldermack silhouette on the same vista), walled cemetery
ground behind it with a lychgate on the west street and a gate by the
church, and a **mausoleum row attached to the cemetery's north wall**
(attached, not free-standing, so the street-loop count holds at the CN 2
ceiling). The crypt stack sits under the mausoleum row — the cemetery earns
the stack on E1M1's evidence, *in addition to* Old Crossing's roof route
(stacks are two sectors and two markers; the budget cost is negligible).

## Contract for the Gravesend complex

- Cemetery ground: walled, 2 gates (lychgate + church-side), tombstone wall
  sprites at E1M1-like density, 2 mausoleum masses on the north wall, floor
  shade ≈ +30 with lantern flicker pools.
- Church: fronts the avenue; the monastery chapel grammar; interior in the
  landmark-complex register (multi-door, braided rooms) at 400–600 walls.
- Crypt: one stack pair under the mausoleum row (Phase 4 with Old
  Crossing's district turn), E1M1 congruence rules.
- Circuit: the avenue vista leg passes the church front; the cemetery is a
  side-pocket off the west street, not a required leg (the sewer already
  holds the required mid-route beat).
