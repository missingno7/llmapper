# City norms — what the precedents actually build

Phase 0 reference for Blood City. Every number below is measured by
`tools/mine_city_norms.py` from the six sources and stored with full detail in
[city-norms.json](city-norms.json); the plots under [plots/](plots/) show what
the classifier decided so its mistakes stay visible. Structure norms use all
six maps; art norms use the Blood two only — tile identity does not transfer
between games.

Sources: `maps/blood/E3M1.MAP` (Ghost Town), `maps/blood/DWE3M1.MAP`
(Death Wish), `maps/duke3d/DukCity1–4.map`.

Method in one paragraph (full version in the JSON `scope.method`): the street
is the sky-ceiling walkable component with the most doorways into interiors —
largest-by-area picks the landscape *around* the town in DWE3M1. Widths are
ray-cast across a 128-unit raster of that region; blocks are its enclosed
holes; vertical z compares to plan xy at the engine's 16:1. Thresholds are
echoed in `scope.thresholds`. "Derived" numbers are pure geometry;
anything resting on a threshold or a reading is marked **interpreted**.

## 1. Street widths and canyon ratios

| map | width p10 | median | p90 | canyon p10 | median | p90 | samples |
|---|---|---|---|---|---|---|---|
| E3M1 | 2048 | 7168 | 27776 | 0.20 | 1.68 | 6.0 | 701 |
| DWE3M1 | 1536 | 7552 | 20608 | 0.13 | 0.32 | 2.28 | 1011 |
| DukCity1 | 2048 | 5248 | 23680 | 0.39 | 2.07 | 5.31 | 2567 |
| DukCity2 | 1024 | 5120 | 8192 | 1.31 | 2.12 | 10.62 | 2818 |
| DukCity3 | 1152 | 5120 | 16128 | 0.43 | 2.12 | 9.44 | 2398 |
| DukCity4 | 1024 | 5120 | 14336 | 0.30 | 2.12 | 10.62 | 2013 |

- The DukCity street is astonishingly stable: **median 5120–5248 units**
  (≈16 player widths) across all four maps, with alleys at ~1024 and plazas
  at 8k–24k. The Blood towns run wider: median 7168–7552 (≈19 player widths)
  — frontier-town streets, not Manhattan canyons.
- Canyon ratio (facade face height ÷ street width, dimensionless):
  **DukCity holds median ≈2.1** — the facade wall stands about twice the
  street's width — with p90 spikes of 5–10 where towers front narrow streets.
  E3M1 sits at 1.68. DWE3M1's 0.32 median says its town is *low*; take its
  scale and density, not its skyline (and not its fog).
- **Interpreted**: E3M1's sky-bounded samples include canyon rim walls, which
  fatten its p90; the median is street-dominated (see plot).

**Design contract**: main streets 5120–7168 wide, alleys ~1024–2048, one plaza
per district at 8k+; facades on main streets aim for canyon ratio 1.7–2.1
(street 6144 wide → facade face ≈ 10.5k–13k xy-equivalent ≈ 168k–208k z).

## 2. Blocks and street loops

| map | walk-around blocks | loop count | block extent median | max | sub-block obstacles |
|---|---|---|---|---|---|
| E3M1 | 1 | 1 | 14848 | 14848 | 0 |
| DWE3M1 | 8 | 8 | 2816 | 11264 | 5 |
| DukCity1 | 11 | 11 | 2304 | 36864 | 5 |
| DukCity2 | 7 | 7 | 23552 | 37120 | 0 |
| DukCity3 | 9 | 9 | 7680 | 36864 | 0 |
| DukCity4 | 7 | 7 | 2432 | 37120 | 0 |

- A DukCity map loops its streets around **7–11 blocks**, and block size is
  bimodal: small free-standing masses at 768–2432 units (kiosks, monuments,
  single buildings) and **superblocks at 24k–37k units** holding many
  buildings behind one continuous frontage.
- E3M1 is one loop around one 14848-unit block; its other buildings are
  frontage masses at the street edge with no walk-around (visible in
  [plots/e3m1-city-plan.png](plots/e3m1-city-plan.png)). DWE3M1 likewise
  fronts most buildings. **Blood towns wrap buildings less than Duke cities
  do** — the loop count is where DukCity's urban feel lives.

**Design contract**: 6–9 street loops; 2–3 superblocks (24k–32k) plus a
scatter of small free-standing masses; the rest as edge frontage.

## 3. Enterable share and interior sizing

| map | walk-around blocks enterable | doorways /10240 frontage | substantial interiors /10240 | interior area median (max) |
|---|---|---|---|---|
| E3M1 | 1/1 | 1.17 | 0.37 | 77M (212M) |
| DWE3M1 | 1/8 | 0.96 | 0.13 | 115M (4573M¹) |
| DukCity1 | 5/11 (0.455) | 0.31 | 0.18 | 26M (336M) |
| DukCity2 | 4/7 (0.571) | 0.23 | 0.14 | 82M (546M) |
| DukCity3 | 5/9 (0.556) | 0.50 | 0.19 | 14M (299M) |
| DukCity4 | 3/7 (0.429) | 0.40 | 0.18 | 56M (114M) |

¹ DWE3M1's max "interior" chains through the whole below-town cave system —
component merging, not a shop.

- **About half of walk-around blocks are enterable** in every DukCity map
  (0.43–0.57 — four maps agreeing within ±0.07). This is the contract number.
- Substantial-interior rate is even tighter: **0.13–0.19 per 10240 units of
  frontage** for five of six maps — one real interior per ~55k–75k units of
  street wall. E3M1 doubles that (0.37): a small dense town where the
  saloon/hotel complex dominates.
- Interior components run 14M–115M sq units (a 4k–10k square equivalent) —
  **interiors are pocket-sized relative to their massing**: a 24k superblock
  fronts interiors 4–8k deep. The facade promises far more building than
  exists, everywhere, in every source.

**Design contract**: ~half the blocks enterable; ≈1 substantial interior per
60k frontage (≈8–12 interiors at our scale); interiors 3k–8k deep behind the
facade, never footprint-filling.

## 4. Facade articulation — geometry vs. texture vs. sprites

Per 1024 units of street frontage:

| map | wall vertices | masked-glass windows | red-wall openings | wall sprites | face sprites in street (count) |
|---|---|---|---|---|---|
| E3M1 | 0.53 | 0.011 | 0.091 | 0.032 | 257 |
| DWE3M1 | 0.73 | 0.003 | 0.101 | 0.258 | 152 |
| DukCity1 | 0.46 | 0.001 | 0.038 | 0.057 | 124 |
| DukCity2 | 0.28 | 0.000 | 0.023 | 0.098 | 101 |
| DukCity3 | 0.38 | 0.000 | 0.057 | 0.132 | 133 |
| DukCity4 | 0.49 | 0.002 | 0.047 | 0.173 | 95 |

- **Windows are texture, not geometry.** Masked-glass walls on street
  frontage are nearly absent everywhere (≤0.011/1024 ≈ one per 93k units).
  The window-dense look of these cities is painted on facade tiles.
- Geometry articulation is coarse: **one vertex per 1.4k–3.7k units** of
  frontage. Nobody models window reveals; corners, setbacks and doorway
  reveals are what walls buy.
- Sprite dressing carries signage and fixtures: 0.03–0.26 wall sprites/1024,
  and Death Wish is the heaviest sprite-dresser of the six — that is the
  budget-cheap articulation channel.

**Design contract** (this is what keeps Phase 3 inside the wall cap): facades
spend walls on silhouette (setbacks, corners, doorway reveals) at ≈0.4–0.5
vertices/1024; window rhythm comes from tile choice; signage and fixtures
from wall sprites at ≈0.1–0.2/1024.

## 5. Verticality

| map | skyline wmedian (xy) | tallest (standing heights) | rooftop share of street area | perched outdoor | below-grade sectors (area) | stacks |
|---|---|---|---|---|---|---|
| E3M1 | 4096 | 8.5 | 0.528 | 2 | 0 | 3 stack + 1 water |
| DWE3M1 | 2368 | 2.8 | 0.072 | 33 | 20 (2705M) | 2 water, 1 goo, 1 stack |
| DukCity1 | 1280 | 6.5 | 0.001 | 6 | 17 (54M) | — |
| DukCity2 | 896 | 10.1 | 0.014 | 7 | 99 (562M) | — |
| DukCity3 | 2496 | 6.0 | 0.004 | 3 | 125 (871M) | — |
| DukCity4 | 1856 | 6.0 | 0.020 | 8 | 75 (173M) | — |

- **E3M1's signature is the walkable roofscape**: sky sectors above grade
  cover 52.8% of the street area — the town has a second storey of routes,
  built with 3 paired-sector stacks (plus one water stack). That is the Blood
  move Duke cannot make, and the strongest differentiator available to us.
- **DukCity's signature is the sewer**: 75–125 below-grade sectors per map
  (up to 871M sq units in DukCity3) against zero in E3M1. Duke roofs are
  scenery (share ≤ 0.02) — skylines of 6–10 standing heights that you look
  at, not walk on.
- DWE3M1 perches 33 small outdoor sectors above grade — balconies and ledges
  as dressing.
- **Interpreted**: skyline is roof-sector floors within 2048 units of the
  street; stack rules (congruent loops, plan overlap) are in the JSON
  `verticality.stack_pairs` and follow the norms already mined in
  `knowledge/blood/design/stacks-v1.json`.

**Design contract**: one district carries an E3M1-style stacked roof route;
one carries a DukCity-style sewer beneath 10–20% of its street; skyline
area-weighted median ≈2–4k xy with a landmark at 6–8 standing heights.

## 6. Districts and seams (art: Blood sources only)

- **E3M1** resolves into 4 street zones: a boardwalk zone (floor 352) and
  three ground zones (floor 4) that differentiate by **facade texture set**,
  not floor — zone facade tops are {400, 414, 181, 417, 418}, {380, 381,
  393}, {384, 393, 181}. Floor shade sits at +32/+34 (a dark night town) with
  near-zero spread. Seams fall at street junctions, not mid-street.
- **DWE3M1** fragments: every street sector its own material (floors 255,
  404, 374 under pal 1 — the fog palette we are not reproducing). Its
  district reading is per-building variety, not zoned palettes.
- So in Blood-town practice, **a district is a facade tile-set plus a floor
  material, under uniform night shading** — light variation comes from
  sources (see `knowledge/blood/design/visual-norms-v1.json`), not from
  zone-wide shade bands.

## 7. Budget spend

Totals (sectors / walls / sprites): E3M1 **382 / 2481 / 807** · DWE3M1
**606 / 6032 / 1690** · DukCity1 634/5464/1201 · DukCity2 496/4211/1275 ·
DukCity3 **994 / 8185 / 1526** (walls 99.9% of the 8192 engine limit) ·
DukCity4 715/5420/1376.

Per district-sized chunk (street-zone attribution, `budget_per_chunk`):

- E3M1 spends **79–1007 walls per chunk** across 4 chunks (147+150 sectors in
  the two big ones) — a Blood-town district is a 300–1000-wall object.
- DukCity3's city core is one 6406-wall / 796-sector chunk; its subway and
  racetrack hold the other ~1800 walls. DukCity is one-district urbanism at
  maximum density; Blood City should be E3M1's zoning at DukCity's density.
- Walls per sector: E3M1 6.5, DukCity1 8.6, DukCity3 8.2, DWE3M1 10.0.
  At the target 400–650 sectors, DukCity-like density predicts
  **3300–5300 walls** — the 7000 cap holds ~1700+ of facade/iteration
  headroom, and per-district caps of ≈700–1100 walls match the E3M1 chunk
  norm.

## 8. What E3M1 spends its mechanism channels on

69 user channels (DWE3M1: 58). Shapes: 21 one-to-one, 31 fan-out, 10 fan-in,
7 mesh. Receivers by resolved type (names from `bloodmap.blood_types`,
NBlood common_game.h):

- **Doors and motion, 29 receivers**: z-motion 21, slide (614/616) 6,
  rotate 2 — the door stock of a town.
- **Destruction set-pieces, 18**: kTrapExploder 459 ×13, kThingObjectExplode
  417 ×5 — Ghost Town's collapsing/exploding moments are its second-largest
  channel spend.
- **Switches 13** (types 20–23) as transmitters into the above.
- **Scripted sound and spawns, 15**: kGenSound ×6, kSoundPlayer ×4, Ambient
  SFX ×2, kMarkerDudeSpawn ×3 — fan-outs that stage an event (sound + spawn +
  motion on one channel).
- DWE3M1 shifts the mix toward narration: kSoundPlayer ×22, switches ×16.

**Design contract**: ≈50–70 user channels; door wiring mostly 1:1 and
fan-out from switches; at least a handful of channels reserved for
destruction set-pieces and staged sound+spawn events — a city that only
spends channels on doors is under-wired by these norms.

## Known limits of the measurement

- The street component is walkable-at-grade sky; streets joined only through
  indoor arcades would fragment it (none of the six sources needed the
  merge).
- Slopes are read at their flat z (the sources keep streets flat).
- The block census undercounts "buildings" in frontage towns (E3M1, DWE3M1);
  that is what the frontage rates are for.
- E3M1 canyon p90 and skyline include canyon-rim geology; medians are
  street-dominated.
