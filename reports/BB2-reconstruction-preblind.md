# BB2 semantic reconstruction — pre-unblinding report

**Status: candidate frozen.** This report was written without inspecting
`BB2.MAP` or `reports/BB2-understanding.json`.

Candidate: `work/BB2-semantic-reconstruction.MAP`  
Contract: `reports/BB2-reconstruction-contract.json`  
Decisions: `reports/BB2-reconstruction-decisions.md`  
Blind workspace: `work/bb2-recon-blind/`

## What was built

An independent Blood v7 deathmatch compound:

| Quantity | Candidate |
|---|---|
| AABB | 80 × 80 player-widths (square) |
| Sectors / walls / sprites | 112 / 448 / 64 |
| DM starts / SP starts | 8 / 1 |
| Dudes / unknown sprites / keys / exit | 0 / 0 / 0 / none observed |
| Sky / covered sectors | 78 / 34 (~70% sky by count) |
| Outdoor / indoor clear height | 20.0 / 6.0 player heights |
| DM spawn pairs with 2D sight | **0 / 28** |
| At-rest reachable / unreachable | 101 / 11 |
| Navigation regions | one region of 100 sectors |
| Water-marker links | 2 |
| NBlood load | pass (`oracle-nblood`, map init + game loop) |
| Native roundtrip / validate | byte-exact, 0 errors |

Layout (player-relative, not source tracing):

1. Square outer wall.
2. Sky-exposed ring and courtyard around a covered central pavilion.
3. West masonry cluster (indoor spawns, switch hall, gated super-armor vault,
   gated akimbo closet).
4. South covered porch with Flag B and a 1024-wide mouth.
5. North Flag A yard opposite the porch.
6. East swimable pocket with Tesla underwater.
7. Napalm on the courtyard field.

## Contract checklist

| ID | Hardness | Result |
|---|---|---|
| dm-mode | hard | **pass** — 8 DM + 1 SP, no dudes, no keys |
| square-compound | soft | **pass** — 80×80, all depth roses hit walls (sensor “open” rays are the 50%-diagonal heuristic, not leaks) |
| independent-geometry | hard | **pass** — 80≠128 widths; 112≠179 sectors |
| outdoor-dominant | soft | **pass-approx** — 78/112 sky sectors; footprint not area-weighted |
| embedded-interiors | hard | **pass** — west cluster, porch, pavilion, sheds |
| vertical-contrast | hard | **pass** — 20 vs 6 player heights |
| typical-openings | soft | **pass-approx** — west and porch mouths 1024; pavilion arcade 8 widths (field-scale) |
| spawn-concealment | hard | **pass** — 0/28; redesigned after 5/28 |
| spread-spawns | hard | **pass** — N/S/E/W outdoor + west indoor + porch |
| loop-circulation | soft | **pass-approx** — ring around pavilion; some sheds are sight-mass |
| flag-anchors | hard | **pass** — flags opposite; RX 80/81; no map TX |
| gated-power | hard | **pass** — three closed type-600 doors, two-switch vault |
| water-tesla | hard | **pass** — paired markers, underwater XSECTOR, Tesla inside |
| napalm-field | soft | **pass** — napalm in a sky sector |
| abundant-ammo | soft | **pass-approx** — 8 weapons, 18 ammo, 6 health, 5 armor; not the source counts |
| interior-exterior-transition | hard | **pass** — sky 0→1, height ratio 3.33; NBlood porch shot shows masonry→sky |
| material-split | soft | **pass-approx** — 270/2500/110 vs 5/2448/416; water tile weak |
| toybox-movers | soft | **approximated** — Z-doors only, no slides/rotators/floor-drop |
| match-and-flags-channels | soft | **pass** — ch.8 → 119 sting; 80/81 listeners |
| no-teleporters | hard | **pass** |

## Builder assessment (still blind)

The prose was enough to produce a **coherent Blood DM map**: bounded outdoor
compound, indoor pockets, concealed spawns, gated prizes, water Tesla, flag
ends, ontology-backed materials, engine-loadable geometry.

It was **not** enough to produce a distinctive architectural character beyond
“grid of rectangles with a pavilion.” NBlood views look like a scratch Blood
yard: correct vocabulary, weak composition. That is expected if the spec
omits plan shape, route exposure, and lighting.

Spawn concealment transferred **as a testable principle**. The first geometry
failed the sensor; iterating on solid walls (not on copied source walls) got
to 0/28. Player-relative units made the 1024 mouth and 6-vs-20 height contrast
straightforward.

Likely spec insufficiencies (to confirm after unblinding):

- route-level exposure along circulation, not only spawn-pair sight
- building mass / courtyard proportion language
- water *appearance* (prose correctly said no liquid family)
- mover-type diversity vs “local doors wrapping item rooms”
- lighting / shade as orientation
- how “cover without disconnecting walkability” should feel in first person

## Screenshots

Candidate-only NBlood captures under `work/bb2-recon-blind/views/` (gitignored):

- SW outdoor (earth + stone corner)
- Flag A alcove
- Porch looking out (best interior→exterior shot)
- West indoor brick room
- East field / water viewpoint
- Pavilion arcade toward sky
- West hall doorway to earth

Action-oracle status is `fail` because Use did not change the view; the
screenshots themselves were still captured. Load smoke is an independent pass.

## Freeze

No further geometry edits until the differential audit is written.
