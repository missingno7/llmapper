# Sewer patterns — what lives under a DukCity street

Supplement to [city-norms.md](city-norms.md). Structure measured by
`tools/mine_sewers.py` from DukCity1–4 (full records with sector ids in
[sewer-mining.json](sewer-mining.json)); dressing for Blood City's sewer
comes from the Blood-side water/underground norms already in
`knowledge/blood/design/` (stacks-v1, surface-palettes-v1), not from Duke
tiles. Role readings are **interpreted** from keycard/secret/effector
evidence as labeled; everything else is derived geometry.

## The finding that reframes the question

**DukCity "sewers" are displaced boxes, not under-street networks.**
Under-street area share is 0.00 for every below-grade network in all four
maps: Duke has no room-over-room, so the underground is built elsewhere in
map space and reached through point transports. The network's *shape* is
therefore free — it never has to mirror the street grid, and measured, it
doesn't: internal cycle ranks of 7–52 against street-level loop counts of
7–11, a denser, self-owned topology.

Blood has real stacks (E3M1 uses 3), so Blood City gets to do what Duke
faked: the sewer *can* lie truly under its district. The contract below keeps
Duke's quantities and roles, and upgrades the connection form to ROR.

## Measured anatomy

| map | network | sectors | area | depth (standing) med/max | wet share | cycle rank | entries (form) | evidence → role |
|---|---|---|---|---|---|---|---|---|
| DukCity1 | pocket | 17 | 54M | 1.05 / 1.05 | 0.00 | 16 | 0 seen¹ | dead-end pocket |
| DukCity2 | main | 89 | 525M | 2.63 / 3.37 | 0.01 | 52 | 1 (drop) | keycard → **required passage** |
| DukCity2 | side | 8 | 33M | 4.63 / 4.74 | 0.00 | 0 | 1 (elevator) | secret tag → **secret** |
| DukCity3 | transit | 69 | 835M | 2.84 / 3.79 | 0.00 | 24 | 2 (elevator) | SE6/SE14 → **subway ring** (holds a keycard: the station is on the route) |
| DukCity3 | pocket | 27 | 14M | 5.16 / 5.26 | 0.00 | 20 | 0 seen¹ | dead-end pocket |
| DukCity3 | vault | 13 | 11M | 3.47 / 3.47 | 0.00 | 0 | 1 (elevator) | keycard → **required passage** |
| DukCity4 | main | 64 | 97M | 4.11 / 5.47 | 0.02 | 7 | 1 (elevator) | secret tag → **secret** |

¹ Reached by riding moving sectors (train/vehicle) or through routes the
walkable-adjacency model cannot traverse; the zero is a model limit, noted,
not a claim the pocket is sealed.

- **Entries are rare and pointlike**: 1–2 per network, 0.02–0.04 per 10240
  units of street frontage — one underground entrance per ~250–500k of
  frontage. The sewer is not a second street grid with many manholes; it is
  a **destination dungeon with one or two doors**.
- **Entry forms**: elevator shaft (5 of 7 observed), floor drop (1), water
  dive via SE7 pairs (present in DukCity2's water linking). Walk-down stairs
  from the street essentially do not occur.
- **Depth**: medians 2.6–5.2 standing heights below grade (≈44k–88k z);
  shallow transit at ~1–2.8, deep vaults at 3.5–5.5.
- **Dry, not wet**: wet area share 0.00–0.02. The "sewer" is corridors and
  chambers; water is an accent puddle or a single channel, not the medium.
- **Roles across the corpus**: required passage ×3 (keycard placed inside),
  secret ×2, transit ring ×1, ambient pocket ×2. Both story roles occur
  about equally; no map makes the sewer a casual shortcut loop.

## Design contract for Blood City's sewer district

- One sewer network under the designated district: **50–90 sectors**,
  footprint 100–500M sq units, **depth 2.5–4 standing heights** below street
  grade, internal cycle rank ≥ 7 (its own loops, denser than the street's).
- **True ROR placement** (Blood stacks, per `stacks-v1` congruence rules):
  the network lies under its district's actual streets — the upgrade Duke
  could not build. Under-street share target ≥ 0.5, against Duke's 0.0,
  marked as a deliberate deviation from precedent.
- **Two entries, forms translated to Blood**: one drop entry (manhole/grate
  ROR hole in a street or alley floor, with return route), one z-motion
  platform or stair from inside a building (the "elevator" translation).
  A third, secret, water-dive entry is optional and follows the water-stack
  norms.
- **Role: required passage once, shortcut never** — the main circuit routes
  through the sewer for exactly one leg (key or objective inside, per
  DukCity2/3 precedent), and one secret stash lives in a dead-end branch.
- Wet share ≤ 0.2: dry corridors with one water channel; underwater only in
  the optional secret branch.
- Budget guide (from the 64–89-sector mains at DukCity wall density ≈8/sector):
  **≈400–700 walls**, charged to the sewer district's chunk budget.

---

# Supplement: E3M3, the Blood-side sewer precedent (owner directive, 2026-08-27)

`tools/mine_room_grammar.py` on E3M3 (Blood's own sewers map; 309 sectors,
2227 walls, 519 sprites, records in
[room-grammar.json](room-grammar.json)). Where it disagrees with the
Duke-derived contract above, **Blood wins on dressing outright**, and each
structural disagreement is shown with both numbers.

## What E3M3 measures

- **Wet, not dry -- a structural disagreement.** DukCity wet share:
  0.00-0.02. E3M3: **90 underwater sectors (29% of the map)** plus 26
  shallow-depth sectors, and 37 link pairs of which the overwhelming
  majority are water dives (36 water/1 stack). Blood's sewer medium *is*
  water; Duke's dry corridors were an engine limitation as much as a
  choice (no true diving under a walkway without ROR).
- **The cross-section is a ledge over a channel**: 62 ledge-over-channel
  pairs (elongated low sector beside a walkway with a modest step); the
  walk-step census has median 4096 z -- one max-step from walkway to
  channel. The standard corridor module repeats 30 times as a ~2048x512
  segment class (sectors 42/46/50...): narrow channels, wider walks.
- **Light is animated everywhere**: 175 of 309 sectors carry animated
  shade (57%) -- the densest flicker of any map measured in this project.
  Shade median +34.
- **Lightly wired**: 23 user channels (vs 47 campaign median) -- sewers
  spend on atmosphere, not mechanism.
- **What lives there**: bone eels x17, rats x9, gill beasts x7, butchers
  x13, axe zombies -- water dwellers and scavengers, no cultist garrison.

## Reconciled contract for Gravesend's sewer

Replaces the corresponding rows of the design contract above; urban
integration findings (point entries, one required passage, entry forms and
rates) stand -- E3M3 is a whole-map sewer and does not measure urban
integration.

- **Wet share 0.2-0.4** (was <=0.2): one continuous water channel through
  the ring with ledge walkways at step 4096, and the Phase 4 buildout adds
  one water-dive link (water stack) into a flooded branch -- the Blood move
  Duke could not make. Structural disagreement resolved toward Blood:
  DukCity 0.00-0.02 / E3M3 0.29 / Gravesend target 0.2-0.4.
- **Cross-section**: walkway >= 1024 beside a 512-2048 channel; corridor
  clear height stays 1.2 standing.
- **Light**: ~half the sewer's sectors animated-shade, median around +34
  -- darker and more restless than the streets above.
- **Population register** (L3): rats/eels/gill beasts, no garrison.
- **Channels**: the sewer stays lightly wired (<=4 of the district
  allocation), spending on sound/ambience not mechanisms.
