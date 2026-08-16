# BB2 semantic reconstruction — design-level comparison

Post-freeze audit. The candidate was **not** edited during this comparison.

Source: `maps/blood/BB2.MAP` + `reports/BB2-understanding.json`  
Candidate: `work/BB2-semantic-reconstruction.MAP`  
Blind inputs: `reports/BB2-understanding.md` only

There is **no global similarity score**. Each section is a separate dimension.

## 1. Topology / circulation

| Signal | Source | Candidate |
|---|---|---|
| Dominant navigation region | 151 + 3 sectors | 100 sectors (one region) |
| SP-at-rest reachable | 154 / 25 unreachable | 101 / 11 unreachable |
| Walkable portals | 291 | 126 |
| Blocked / state-dependent | 119 | 6 |
| Non-portal transitions | 2 water links | 2 water links |
| Teleporters | none | none |

Both are one outdoor-connected compound with optional closed pockets. The
candidate has the same *kind* of graph (one big walkable component plus
gated rooms) and far less interior fragmentation.

Source interiors are many small sectors punched into a large exterior
(116 covered vs 63 sky). The candidate inverts that count (34 covered vs
78 sky) even though **sky footprint fraction is close** (0.75 vs 0.65).

Loops exist around a central pavilion rather than through an irregular
building cluster. Bottlenecks are 1024 mouths plus three Z-doors, not a
dense toybox of movers.

## 2. Player-relative scale

| Signal | Source | Candidate |
|---|---|---|
| AABB | 128 × 128 widths | 80 × 80 widths (independent, as required) |
| Sky footprint fraction | 0.646 | 0.747 |
| Outdoor median clear height | 15.6 (spawns 17–23) | 20.0 (uniform) |
| Covered median clear height | 5.1 (spawns 5–11) | 6.0 (uniform) |
| Median portal | 2.67 widths | 1024 mouths = 2.67; many full-cell edges wider |
| Outdoor spawn footprints | 110–455 player-areas | small grid cells / alcoves |
| Indoor spawn footprints | 28–173 | west rooms + porch, smaller than source large indoor |

Height contrast transferred. Plan scale is smaller by design. Outdoor
**elevation variation** (source: not a single plane) did not transfer —
the candidate outdoor floor is one Z.

Enclosure metrics survived surprisingly well despite different geometry:

| Enclosure (sky / covered) | Source | Candidate |
|---|---|---|
| Openness | 0.56 / 0.25 | 0.56 / 0.32 |
| Lateral enclosure | 0.87 / 0.92 | 0.88 / 0.85 |
| Vertical enclosure (covered) | 0.59 | 0.50 |

## 3. Spawn design

| Signal | Source | Candidate |
|---|---|---|
| DM / SP | 8 / 1 | 8 / 1 |
| Outdoor / indoor DM | 5 / 3 | 5 / 3 |
| Clear 2D spawn pairs | 1 / 28 (two outdoor) | 0 / 28 |
| Mix around the square | yes | yes |
| Large outdoor spawn field | southern ground ~455 areas, long sight | SW/SE/NW/NE are pockets |

Concealment **overshot** the source. The principle “most pairs are blind”
survived; the source’s one outdoor peek and the **large hunting-ground
spawns** did not. Indoor starts are hidden in both.

## 4. Resources

| Category | Source | Candidate |
|---|---|---|
| Weapons | 8 (shotgun, Tommy, flare×2, Tesla, napalm) | 8 (same set, shotgun/Tommy/flare×2) |
| Ammo | 47 | 18 |
| Health | 7 | 6 |
| Armor | 7 | 5 |
| Powerups | cloak + akimbo | cloak + akimbo |
| Flags | A/B bases | A/B bases |
| Tesla | underwater | underwater |
| Napalm | sky field | sky field |
| Super armor | gated Z-ceiling, two switches | gated Z-ceiling, two switches |

Weapon *identity* transferred. Ammo richness is weaker (18 vs 47). Exact
counts were not required. Gated/high-risk placement transferred.

## 5. Mechanisms

| Role | Source | Candidate |
|---|---|---|
| Match-start sting | ch.8 → player SFX | same pattern |
| Flag capture listeners | 80/81, no map TX | same |
| Super armor | two switches, Z ceiling, link companion | two switches, Z ceiling, no companion |
| Cloak / akimbo | switch / closed mover | Z-doors ch.102 / 101 |
| Water | 2 pairs, 3 underwater XSECTORs | 2 pairs, 2 underwater XSECTORs |
| Z-motion | 13 | 3 |
| Slide-marked | 4 | 0 |
| Rotators | 6 | 0 |
| Gib windows | 10 | 1 |
| Ambient 710 | 37 | 3 |

Gameplay *purpose* of gated prizes, water Tesla, and reserved channels
transferred. Native toybox diversity did not. That matches the builder
instruction to preserve effects, not tags — and it is still a real
experiential thinning.

## 6. Enclosure / visibility

Sky vs covered contrast transferred (parallax, height, openness).

Source outdoor starts have max 2D sight ~50–73 widths once in the field.
Candidate outdoor starts live in alcoves; the courtyard *exists* but is
not the spawn neighborhood. Spawn-pair sight is stricter than source.
Route-level exposure along the ring was never specified in prose and was
not measured as a first-class target.

## 7. Materials

| Role | Source dominant | Candidate | Appropriate? |
|---|---|---|---|
| Outdoor floor | 2448 (campaign floor) | 270 (ontology organic earth) | role yes; tile no |
| Sky | 2500 | 2500 | yes |
| Outdoor / compound walls | mix; 110 in ontology | 110 stone | yes |
| Interior walls | 91, plus unannotated 2455/2492 | 5 brick | masonry yes; not source bricks |
| Interior floor | stone used horizontally | 2448 | we used the source *outdoor* floor indoors |
| Interior ceiling | brick-as-ceiling pitfall | 416 (annotated ceiling) | ontology-correct, not source |
| Water surface | distinct from gray ground | 90 + pal 1 | distinct, does not read as water |
| Switches | 1070 family | 1070 | yes |

Exact texture identity is **not** a success metric. Outdoor/indoor split
is visible in NBlood. Water appearance is a known ontology hole. Using
2448 indoors and 270 outdoors is a facet-following choice that happens
to invert source assignment.

## 8. Design experience (interpreted)

| Relationship | Survived? |
|---|---|
| Open ↔ covered circulation | Partially — the spaces exist; first-person spawn views often face walls |
| Interior → exterior expansion | Yes (height 6→20, sky 0→1; porch screenshot) |
| Spawn concealment | Yes, even stricter |
| Orientation (flags, water, sky) | Flags and sky yes; water weak visually; no unique skyline (prose said none proven) |
| Resource control / gated prizes | Yes |
| Risk/reward side pocket | Yes (east water Tesla) |
| Large outdoor meeting ground | Weak — courtyard is there, spawns are not *in* it |
| Irregular masonry cluster | No — orthogonal grid |

---

## What survived completely different geometry

- Deathmatch mode inventory (8 DM, 1 SP, no dudes/keys/exit)
- Square walled compound, outdoor-majority *footprint*
- 5 outdoor / 3 indoor DM starts
- Sky/covered openness and lateral enclosure numbers nearly matching
- 6-vs-20 height contrast
- Flag ends, water Tesla, napalm on the field, gated super/cloak/akimbo
- Channel 8 / 80 / 81 wiring pattern
- Typical 1024 building mouth

## What was lost

- 128-width footprint and 179-sector fragmentation (**deliberate**)
- Large outdoor spawn neighborhoods and the 1 outdoor peek pair
- Covered-sectors-more-numerous than sky sectors
- Outdoor Z variation / lifts
- Slide and rotate toybox
- Ammo density
- Source masonry IDs and outdoor floor 2448
- Ambient beds, gib windows, lighting mood
