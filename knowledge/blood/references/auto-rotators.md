# Auto-rotating sectors — original-map evidence (turnstile family)

Occurrence evidence is in [auto-rotators.json](auto-rotators.json), mined
2026-08-31 from the reference view (campaign + curated, both modes) plus
conversions. Owner-suggested anchor: the automatic revolving turnstile doors
in E1M4 and DNE3L6.

## The native signature

One mechanism family, fully explained by native fields:

```text
sector type   615 kSectorRotateMarked (or 617/613 for scenery variants)
marker_0      kMarkerAxis sprite (type 5) inside the rotor — the pivot
rx_id         7 = system channel level_start
retrigger     both waves
busy_time     asymmetric a/b — the direction and speed of the endless spin
no key, no push, no wallpush
```

Reading: the rotor receives the level-start broadcast once and, because both
waves retrigger, cycles forever. **88 instances in 14 maps** match this
signature, so the mechanism is a corpus convention, not an E1M4 one-off.

## The family splits in two (same engine motion, different design object)

**Turnstile doors** — the rotor is an *aperture* the player passes through:

| where | pair | walls | portal walls | blade posts | spin |
|---|---|---|---|---|---|
| E1M4 (carnival entry) | 151 ↔ 314 | 8 | 2 | 4× picnum 332 | counter-rotating (255/0 vs 0/255) |
| DWE1M9 (Death Wish) | 61 ↔ 64 | 4 | 2 | 4× picnum 332 | counter-rotating (100/0 vs 0/100) |
| DNE3L6 (own conversion) | 3, 11 | 18 | — | 4× picnum 465 | same direction (both 0/100) |

Recurring traits of the door subfamily: **they come in pairs flanking one
entrance**, the pair usually counter-rotates (mirrored busy_time), exactly two
portal walls form the passage, four blade sprites ride the sector, and a
sound generator (type 710, picnum 2521) sits in or beside one rotor. The
blades are **grates** (owner-identified 2026-08-31: 332 and 465 are lattice
tiles, also usable as maskwall grates) — which is why the turnstile reads as
passable machinery rather than a solid drum. Death Wish reuses the
campaign's exact grate tile (332) — vocabulary transfer across populations.

**Rotating scenery** — the same signature with no aperture role: the E1M4
carnival ride (sectors 321–329, with shade waves and `drag`), E3M2/E4M2
rotors, DWE2M3's space-station rotor cluster (23 sectors, one shared spin
rate), SSMALL/SSFACE/SSHIVE machinery, fans on 624-posts. Distinguishing the
two is a *spatial* question (does the rotor sit in a doorway with portal
walls?), not a field question — the low-level mechanism is identical.

## Prefab reading for BloodCity

A turnstile entrance is one call taking the two things that differ between
instances: where the opening is, and the spin period. Everything else is the
template: RotateMarked sector + axis marker at the centroid + rx 7 +
retrigger both + asymmetric busy_time + four blade posts + one sound sprite.
Build them in counter-rotating pairs at a public entrance (the campaign and
Death Wish both do); the same-direction DNE3L6 variant is attested but rarer.

## Promotion status

Evidence recorded; **not yet a constructor**. Per the promotion rule
(`knowledge/blood/design/README.md`), the next step is an
`bloodmap.assembly` template mined from E1M4 151/314 + DWE1M9 61/64, a
`mechanism.py` constructor deriving every fact from that template, a
`motion_sim` replay check, and an NBlood oracle run proving the player can
actually pass through at the mined spin rates.
