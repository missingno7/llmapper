# Implementation Roadmap

This roadmap is ordered to minimize speculative framework work. Each phase now
records three things against the repository as of 2026-08:

- **Already in the repository** — do not rebuild this.
- **Gap** — what is genuinely missing.
- **Agent task** — a self-contained work item with deliverables and exit
  criteria, sized for one focused agent run.

Each task ends with evidence, regression tests
(`python -m unittest discover -s tests`), and a stated next question.
Generated maps are never evidence. The NBlood submodule is off-limits for
these tasks (it hosts the playtest bot; never stage its pointer).

---

# Phase 0a — Corpus integration (DONE, 2026-08-31)

**Status: complete.** The registry is in `bloodmap/patterns.py`
(`list_corpus_maps`, `resolve_corpus_map`, `unadmitted_corpus_maps`,
`build_corpus_manifest`, `observed_mode`); the CLI gained `corpus-manifest`,
`corpus-health`, and `--recursive` / `--population` / `--view` on `corpus` and
`roundtrip-all`. Manifest: `maps/blood/corpus.json`. Health:
`reports/blood-corpus-health.md` plus four per-population JSON reports.
Tests: `tests/test_corpus_registry.py`. Measured counts and the community gate
result are in `07_...md`; the campaign is **43** `E*M*.MAP` files, not 44 — the
old figure counted `DNE3L1.MAP` (a conversion) in a flat inventory.

Two findings for the owner, not fixed here:

- `maps/blood/campaign/ASAVE1.map` (an editor autosave) appeared in the
  campaign directory mid-run. It is quarantined by the name cross-check and
  reported in `corpus.json` under `unadmitted`, never mined as campaign
  convention. Move or delete it.
- `tests/test_rules.RoomOverRoomTests.test_the_two_rooms_meet_at_one_plane`
  now runs (it was hidden behind a corpus-dependent class skip) and **fails**:
  `room_over_room` treats the stack's own upper region as a plan-overlapping
  neighbour, so `lower.ceiling_z` is clamped to the upper region's ceiling
  instead of its floor (`bloodmap/roomoverroom.py:135`). Pre-existing, and
  outside Phase 0a.

## Why first

The corpus moved into subdirectories (`maps/blood/{campaign,curated,
conversions,community,tiered,mechanism}` with `multiplayer/` mode subdirs —
final layout in `07_...md`, physically done by the owner 2026-08-31) and
grew by ~1500 community maps, but `bloodmap.patterns.list_original_maps`
iterates one flat directory and classifies population purely from
filenames. Every corpus command (`corpus`, `roundtrip-all`, `pattern-mine`,
`spatial-corpus`, …) currently sees zero or partial maps. Until this is
fixed, no other phase can cite corpus evidence honestly.

Additionally, existing code and docs carry a **provenance error corrected by
the owner (2026-08-31)**: `DWE*` (Death Wish) and `TEDE*` are hand-picked
community source maps, and `DNE*` are the owner's own Duke3D→Blood
conversions — yet `classify_map_population` and the population table in
`docs/design-pattern-discovery.md` label all three prefixes `conversion`.

## Already in the repository

- fail-closed filename classifier `classify_map_population` (patterns.py) —
  needs the correction above,
- native losslessness gate and `roundtrip-all` (docs/corpus.md),
- tier metadata in `maps/blood/tiered/{manifest,research,summary}.json`
  (heuristic classifier from the `selection` branch; absolute paths stale).

## Agent task

1. The physical reorganization is already done by the owner — verify
   against the layout in `07_...md` rather than moving files. Record it in
   a corpus manifest (`maps/blood/corpus.json` + short README, replacing
   the stale flat-corpus `campaign/README.md`) including the named view
   `reference = campaign + curated`, the mode axis (`mode=sp|multiplayer`
   from the `multiplayer/` subdirectories, cross-checked against player
   starts), and the owner-provenance notes.
2. Introduce a corpus registry that resolves populations from the directory
   layout (directory provenance authoritative, filename prefixes only a
   sanity cross-check); fix `classify_map_population` and the population
   table in `docs/design-pattern-discovery.md` accordingly; keep the
   `BLOODMAP_CORPUS` override.
3. Make corpus enumeration recursive and population-aware; `community` and
   `tiered` must resolve to one population with tier as metadata, never two.
4. Run the parse gate over the community corpus fail-closed: emit a
   machine-readable report (per map: parses / roundtrips / version /
   failure reason) under `reports/`; do not normalize failures.
5. Update `docs/corpus.md` and `docs/design-pattern-discovery.md` command
   examples to the new layout.
6. Tests: population resolution for each directory, tier metadata attach,
   the `reference` view membership, fail-closed behavior on an unsupported
   fixture.

## Exit criteria

`python -m bloodmap corpus`-level commands enumerate the new layout;
`pattern-mine --population blood-campaign` finds exactly the original
`E*M*.MAP` set and nothing hand-picked or converted; `blood-bloodbath`
resolves to `campaign/multiplayer/` (BB1–BB9 only); DWE/TEDE resolve to
`community-curated` and DNE to `own-conversion`; a community-corpus health
report exists and states how many maps pass the gate.

---

# Phase 0 — Stabilize current foundations (DONE, 2026-08-31)

**Status: complete.** `docs/architecture.md` gained a "Where a new fact
belongs" section: a table mapping thirteen kinds of fact to the module that
owns each, the two-direction observe/promote rule pointing at
`knowledge/blood/design/README.md`, and the `context_signature` module move as
the worked example — it was written in `anchors.py`, the pattern pipeline
needed the same key, and the import would have closed a
`patterns → anchors → patterns` cycle. The section also states the two rules
that keep costing more than they look: *a label is not a filter*, and *compute
a whole-map fact once per map*.

Pinning tests in `tests/test_architecture.py` (15), only where a boundary was
load-bearing and untested: the layering arrows that the cycle would violate
(checked by parsing module-level imports, since `relations.py` reaches the
corpus registry inside a function body on purpose), that `context_signature`
is re-exported rather than copied, that `blood_types.py` stays a leaf, that
`reachability.py` never depends on its consumers, that visibility is decided
in one place and needs both of its signals, and that a generated map can never
be cited as a population. No new abstractions.

## Already in the repository

Ownership boundaries exist and are documented in module docstrings and
`docs/architecture.md`:

- `Assembly` = mechanism membership + relations (`bloodmap/assembly.py`),
- `doors.py` = specialized dynamic interpretation,
- `spatial.py` = independent derived spatial views,
- `knowledge/blood/design/` = evidence-backed retrieval surface with an
  explicit promotion rule (README),
- generated maps never become evidence (`docs/design-pattern-discovery.md`).

## Gap

No single note states these boundaries for a newcomer agent; a few behaviors
lack pinning tests.

## Agent task

Write a short architecture note (or extend `docs/architecture.md`) mapping
"where does a new fact of kind X belong"; add pinning tests only where a
boundary is load-bearing and untested. No new abstractions.

## Exit criteria

An agent can explain where a new mechanism fact belongs without inventing a
parallel framework.

---

# Phase 1 — General relation extraction (DONE, 2026-08-31)

**Status: complete.** `bloodmap/relations.py` extracts ten object-scale
relation kinds over a `BuildIR` neighborhood (`extract_relations`,
`neighborhood`, `sprite_dense_seeds`, `mine_relations`); CLI `relation-dump`
and `relation-mine`; report `reports/blood-object-relations-pilot.{json,md}`;
tests `tests/test_relations.py`.

Frame independence is pinned, not asserted: the same neighborhood of a
translated or quarter-turn-rotated map yields an identical document, checked on
a synthetic map and on three campaign maps. The first run of that check failed
(`repeats_along` ordered its members by position, so a half turn reversed the
row) and the fix is in.

Measured on 5 campaign maps' sprite-densest neighborhoods, 2432 relations:
268/310 `rests_on` sit exactly on the floor plane, 261/297 `faces_wall` are
exactly square to the wall's inward normal, and `against_wall` distance is
bimodal -- but that second mode is one map's repeated furnishing, not a
convention. Evenly spaced identical sprite rows are **rare** (1 run in the
sample), which is a negative result about Blood: the detector does find them
where they exist, recovering E6M1's three-mannequin display row from geometry
alone.

**Known defect (owner-flagged 2026-08-31, measured):** `sprite_dense_seeds`
ignores `bloodmap/reachability.py`, and a logic closet is the sprite-densest
place on a map — 3 of the pilot's 15 seeds are off-map (E1M2 sector 19, the
map's densest, is its switch closet; E1M3 291; E1M5 231), so the pilot
distributions include switch-closet relations. Phase 3 inherits it: 81/6803
campaign object-context samples (1.2%) sit in off-map sectors. Fix by
*labeling*, not dropping: tag every seed/sample with the reachability kind
(`reachable` / `logic_closet` / `signature` / bare off-map) — closets are
wiring evidence for Phases 8–9, they just must not pose as furniture.

**Fixed 2026-08-31 (labelled, not dropped).** `reachability.sector_kinds`
answers "what is this sector, and why" for every sector, computed once per map
and passed in; `sprite_dense_seeds` takes it and ranks reachable sectors by
*visible* objects, while `excluded_dense_seeds` reports what the two filters
held back and why. Every relation document now carries `sector_kinds` and each
`in_sector` relation a `visibility` label; absent a reachability map, sectors
are `unknown` rather than assumed reachable.

Measured on the regenerated pilot: **0 of 15 seeds off-map** (was 3), and seven
sectors held back in all — the three switch closets plus four reachable but
wiring-dominated ones (E1M4 sector 321 holds 72 sprites of which 56 are wiring;
E1M3 sector 284, 40 of 59). The headline statistic moved: `rests_on` exactly on
the floor plane fell from **86.5% (268/310) to 63.5% (106/167)** once sound
markers stopped counting, because markers sit exactly on the plane 41 times out
of 42. `faces_wall` exactly square was unaffected (87.9% → 88.5%), which is what
a fact about drawn things should do. See
`reports/blood-object-relations-pilot.md`.

## Already in the repository

- `design.py` / `spatial.py`: adjacency, portals, polygon loops, derived
  spatial views;
- `structures.py`: object-scale candidates with evidence and residuals;
- `prefab.py`: small-sector kinds; `reachability.py`: playable vs support
  geometry; `assembly.py`: relational facts inside mechanisms.

## Gap

No unified, inspectable **object-scale relation dump** using the vocabulary
of `03_...md` (against_wall, faces, aligned_with, repeats_along, supports,
…), with provenance, usable as input for anchor and unsigned mining.

## Agent task

Build a relation extractor over `BuildIR` for a *local neighborhood*
(sector cluster + sprites + walls), reusing existing sensors, emitting
normalized JSON with provenance per relation. Pilot on 3–5 campaign maps.
Do not add relations no consumer needs yet.

## Exit criteria

The system can describe a local object-scale neighborhood without semantic
names, and the dump is stable under translation/rotation of the input.

---

# Phase 2 — Semantic-anchor mining (DONE, 2026-08-31)

**Status: complete.** `bloodmap/anchors.py` is the general form of the two
hand-written miners (`AnchorSpec`, `anchor_from_tiles` / `anchor_from_material`
/ `anchor_from_regions`, `find_occurrences`, `context_signature`, `mine_anchor`,
`mine_kit`, `load_kit`); CLI `anchor-mine` (with `--kit`, which reads a
`role_assets` table -- including from a reference report's own); reports
`reports/anchor-queries.md` plus `anchor-{e6m1-shop,sewer-kit}.json`; tests
`tests/test_anchors.py`.

Both reference reports reproduce through the general path: e6m1-shop's 11
`asset_counts` exactly, sewer-kit's 5 densest maps exactly (map, uses, and
`affected_sectors`). `maps_with_use` differs by one for two sewer roles, and
the new number is the right one -- the extra map in the old path is
`campaign/ASAVE1.map`, the autosave Phase 0a quarantines. First statistic the
quarantine has changed.

Beyond tile lookup: each anchor gets a clustered context signature, its
counterexamples, its anchor-free analogues, and an **enrichment** figure -- how
much more often the anchor's sectors carry the dominant context than sectors
with none of its tiles. Object anchors are strongly enriched (mannequin 30.4x,
chair 11.6x, outlet 9.4x); bulk surface anchors are not (pipe walls 1.15x,
sewer door 0.53x), which is the tool reporting that its own dominant cluster is
meaningless for a material. That split is the phase's main finding.

## Already in the repository

`tools/mine_e6m1_shop.py` and `tools/mine_sewer_kit.py` are working
single-anchor miners (owner-identified assets, carrying sectors, one-hop
neighborhoods, no cross-map tile inference). CLI has `sprite-context-mine`,
`door-mine`, `materials-mine`. A ready-made anchor input exists:
`knowledge/blood/design/owner-anchors-v1.json` — ~37 owner hand-tagged
picnums (shelves, crates, drawer/bookcase fronts, grates, pipes, machinery,
clocks, …) including intact/broken state pairs and known dual roles.

## Gap

Each anchor is a hand-written script. There is no reusable anchor query that
takes labels (tiles / materials / example regions) and runs the Phase 1
neighborhood extraction across a chosen population.

## Agent task

Generalize the two mining scripts into one anchor-query tool
(`python -m bloodmap anchor-mine …` or `tools/`): input = anchor spec,
population; output = occurrences, multi-scale neighborhoods, clustered
recurring relations, anchor-free analogue search, counterexamples. Validate
by reproducing the e6m1-shop and sewer-kit reports through the new path.

## Exit criteria

One anchor produces useful knowledge beyond tile lookup, and the two
existing reference reports are reproducible outputs, not one-offs.

---

# Phase 3 — Unsigned structural candidate discovery (DONE, 2026-08-31)

**Status: complete.** One family added to the existing pipeline, not a new
framework: `patterns.observe_object_context` + `_object_context_signature`,
registered in `_SIGNATURES` and wired into `observe_map`, with features from
Phase 1 relations. `pattern-mine` gained `--tier` and `--limit`. Report:
`reports/blood-object-context-families.md`. Tests: `tests/test_patterns.py`.

Scale bands are corpus quartiles, not round numbers -- the first guess put
nearly every campaign sector in one height bucket and made the facet
decorative.

Measured: 1328 campaign candidates over 6599 occurrences, **80% of them in
candidates recurring across three or more maps** (`route-exposure`, already in
the pipeline, manages 50%). 89% of BloodBath and 84% of tier-S object-context
occurrences use a signature the campaign also uses. The clearest unprogrammed
find is a contrast pair: a tiny, tight, two-portal sector holding exactly one
wall-bound object, `seated:none` (77 occ / 28 maps) versus `seated:all` (72 occ
/ 24 maps) -- a wall fixture in a passage niche against the same niche with the
fixture on the floor.

The Phase 2 prediction (object anchors cluster tightly, material anchors do
not) was tested and is **directionally supported but not established**:
r = 0.541 at n = 13, with `outlet` and `sewer_door` as clear counterexamples,
and the two measures taken on different corpora.

## Already in the repository

`patterns.py` mines unsigned candidates over discrete signatures (spawn
neighborhoods, route exposure, morphology, vertical transitions) with strict
population separation; `structures.py` yields unsigned geometry candidates.

## Gap

No object-scale unsigned families: tiny-sector clusters, repeated shallow
wall structures, sprite+wall furniture-like assemblies. No cross-map
coverage stats over the enlarged corpus.

## Agent task

Add one or two object-scale signature families to the existing pattern
pipeline (not a new framework), using Phase 1 relations as features. Run on
campaign (SP + multiplayer), then sample `tiered/S`. Report candidate stability
and cross-map coverage.

## Exit criteria

At least several visually/semantically meaningful clusters found that were
not explicitly programmed as named concepts.

---

# Phase 4 — Contrastive concepts and counterexamples (DONE, 2026-08-31)

**Status: complete.** Contrast machinery extends `bloodmap/anchors.py`
(`CONTRAST_FEATURES`, `carrier_features`, `_separation`, `_map_transfer`,
`contrast_anchor_sets`, `contrast_signature_classes`); CLI `anchor-contrast`;
reports `reports/blood-contrast-{shelf-vs-crate,bookcase-vs-crate,niche-pair}`;
tests `tests/test_contrast.py`. Nineteen relational features, none of which
reads which tile a surface wears.

**Pilot 1, shelf vs crate pile: rejected, and the rejection is the finding.**
16 shelf-carrying sectors in 3 maps against 1047 crate-carrying in 59. Every
discriminator `03_...md` predicts for this pair scores below the 0.65 floor:
`stackable_identical_units` 0.53, `solid_closed_volume` 0.52,
`requires_access_clearance` 0.52, and `repeated_horizontal_support_surfaces`
separates the wrong way (98% of crate sectors share a plane against 62% of
shelf). The best feature, `portals < 1.5` at 0.729, is a **map artifact**: it
matches 89% of SSMALL's positives and 0% of E6M1's, and leave-one-map-out
transfers to neither. Diagnosis: neither anchor delimits a class. `2026`/`2635`
sit on shelf recesses in SSMALL and on retail-floor walls in E6M1; the crate
tiles are bulk wall material spanning every plan size (16% of their sectors are
halls, only 29% stand proud of every neighbour). A companion contrast on the
owner's bookcase-front tiles (157 sectors, 31 maps) gives real n and still
tops out at 0.663 while wrongly matching 574 crate sectors.

The hypothesis was **re-encoded before it was rejected**: the first feature set
mapped `stackable_identical_units` onto `above`, which means a volume stacked
over a volume, not a platform raised over a floor. Two features were added to
carry the platform reading and the contrast re-run; the answer did not change.

**Pilot 2, the niche pair: one concept with two mounting variants.** Chosen
over storefront-vs-window because the classes were already found relationally
by Phase 3 rather than hand-assembled, and pilot 1 shows what hand-picked tiles
are worth as class definitions. 77 vs 72 sectors across 28 and 24 maps. **No
free feature reaches the floor** (best 0.634), and the defining relation is
real rather than a threshold artifact: the raised variant sits at a median
0.377 player heights (modal 6400 Build units, 22/64 across 12 maps), with only
6 of 77 near the 0.15 `rests_on` cut, while 78% of the floor variant sits
exactly on the plane. Decisively **not texture**: picnum 2520 is 83% of *both*
classes -- the same object, mounted two ways.

**Post-phase identification (2026-08-31): picnum 2520 is `kSoundSector`'s
editor icon** — 1247/1250 campaign sprites wearing it are sprite type 709,
invisible in game. The structural finding stands; the design reading
reframes from "fixture niche" to "where mappers drop the sector-sound marker
for a small ambient space" (addendum in
`reports/blood-contrast-niche-pair.md`). Second instance of the same defect
shape as the reachability one: wiring posing as furniture. Object-scale
mining must separate non-visible wiring sprites (sound 709–711, markers,
generators) from visible decoration — folded into the queued cleanup task.

**Fixed 2026-08-31 (labelled, not dropped).** `blood_types.sprite_visibility`
decides in one place, from the catalog's own categories (`sound`, `marker`,
`start`, `generator`) *and* Build's invisible cstat bit — two independent
signals, both needed: `start` sprites never carry the bit and are still
invisible, while 730 campaign `thing` sprites carry it. No picnum list: the
same tile 2520 is a sound marker 1247 times and a switch 3 times.

The Phase 4 contrast was re-run on visible objects only
(`reports/blood-contrast-niche-pair-visible-only.json`, re-run section appended
to the MD). **The family dissolved: 77 → 13 and 72 → 10 sectors, 85% of members
gone**, and picnum 2520 appears on neither side. What survives is genuinely
furnished and still separated cleanly by the defining relation (raised median
0.483 player heights, none on the plane; floor median 0.0, 6 of 10 on it), but
its one feature above the discriminator floor has a map-transfer spread of 1.00
across 10 maps — a map artifact, as in pilot 1. **A preserved counterexample got
explained**: the 10 raised objects sitting *below* their sector's floor were all
wiring, exactly as the addendum guessed.

Phase 3 was regenerated too: 1962 of 6599 object-context occurrences (30%) left
the default statistics — 1889 wiring-only sectors, 79 off-map (50 logic_closet,
29 sealed) — and are clustered under `excluded_candidates` rather than dropped.
Cross-map stability held at 78% (was 80%), so the recurring structure was never
the wiring; the membership of individual families was.

Counterexamples preserved: 10 of 77 raised objects sit *below* their sector's
floor plane, unexplained; 26 distinct raised heights appear, so 6400 units is a
preference, not a rule. Review-queue item: picnum 2520 is unlabelled in
`owner-anchors-v1.json` and naming it would label 124 of 149 occurrences here.

## Already in the repository

Anchors for both sides of several contrasts exist (`furniture.py` named
props, `item_display.py`, crate/shelf tiles in the e6m1-shop reference).

## Gap

No contrast reports; discriminating relations are not measured.

## Agent task

Pick two pilots (shelf vs crate pile; storefront vs generic window). For
each: positive set, comparison set, measured discriminating relations,
ambiguous cases, rejected hypotheses. Statistics must be actually measured,
in the `10_...md` reporting style.

## Exit criteria

A hypothesis explains both positive and negative evidence relationally, not
by texture or bounding box alone.

---

# Phase 5 — Object assemblies and negative space (DONE, 2026-08-31)

**Status: complete.** Grouping in `bloodmap/anchors.py` (`Bundle`,
`find_bundles`, `scatter_verdict`, `compare_placements`); clearance in
`bloodmap/player_space.py` (`Clearance`, `bundle_clearance`,
`check_clearance`); report `reports/blood-assembly-counters.{json,md}`; tests
`tests/test_assembly_bundles.py` (26).

**The bundle: a raised island.** One outer neighbour (the host), everything
else inset in its own footprint (the caps), floor raised over the host by more
than the 4096-unit step limit, in the waist band, elongated, carrying a cap or
a visible prop. Proximity is not one of the signals. Given nothing but that
rule it recovers E6M1's cashwrap exactly as the owner's shop reference
describes it -- core S32, host S61, caps {S33, S34}, three props, rise 6144.
**146 campaign bundles in 31 maps**, 238 curated as precedent; the waist band
itself is measured, since of 958 campaign blocking islands 38.3% fall in
4096-8192 units and a second mass (33.2%) above 1.45 player heights is wall
stubs rather than furniture.

**The clearance measurement overturned the obvious model.** `04_...md` suggests
a clearance prism around an object. Measured: only **23%** of campaign counters
keep half a player width on every side, **73% are flush against their host on
at least one**, and **95% are asymmetric**. A clearance-all-round rule would
reject 77% of the campaign's own counters. So `Clearance` represents an
*access front* -- the widest free side, `hard: false`, owned by the assembly,
narrow sides recorded rather than required. Every campaign bundle keeps at
least 1.333 player widths on that side (median 9.33), which is the check;
10 of 238 curated bundles fall below it and are preserved as counterexamples.

**The scatter detector uses support, never sprite count.** An authored prop
sits on something; a scattered one sits on the floor it landed on. Validated on
a synthetic pair -- one host, one island, three props on it against the same
three on the floor: support share 1.00 against 0.00, and doubling the scattered
props does not move it. `compare_placements` answers the A/B question the exit
criterion states. Run on E6M1's own selling floor it reports `mixed` at 0.16
(three props on the counter, sixteen deliberately on the floor), so the verdict
names what was measured rather than judging a room's author.

Table + chairs was the stated fallback and was not needed: 146 campaign
instances in 31 maps is not thin evidence.

## Already in the repository

`player_space.py` (openings, clearance, enclosure vs player profiles),
`placement.py`, `furniture.py` mounting semantics, `assembly.py` grouping
discipline for mechanisms.

## Gap

Assembly grouping for *static* furniture bundles; explicit negative-space
representation (access fronts, pull-out volumes); random-scatter detector.

## Agent task

Implement grouping rules for one bundle type (counter + workspace, or table
+ chairs) mined from campaign maps; add a minimal clearance representation
and check; build the scatter detector and validate it on synthetic
authored-vs-scattered scenes (validation only, never evidence).

## Exit criteria

The system distinguishes an authored assembly from the same props randomly
distributed nearby.

---

# Phase 6 — Functional regions (DONE, 2026-08-31)

**Status: complete.** `spatial.zone_partition` is the derived view (connected
sectors sharing a floor plane and floor tile) and knows nothing about bundles;
`anchors.region_candidates` composes it with Phase 5 bundles into hierarchical
containment — complex → zone → {sectors, bundles → core/caps/props}. Report
`reports/blood-assembly-regions.{json,md}`; tests in
`tests/test_assembly_bundles.py` (37 total).

**E6M1 first, as the phase asks.** Two hops from the cashwrap's host gives a
20-sector complex and 11 zones. The largest is the public shop floor — the
apparel bay, display window, selling floor and their connectors, 8 sectors,
746 player areas, 36 props, one plane and one tile — recovered as a single
place, with the counter its own zone, each register cap another, and the
sunken back office another. Corpus-wide: **every one of the 146 campaign
counter complexes holds ≥2 zones (median 7), and in all 146 the counter is in
a different zone from its host**; 92% are alone in theirs. Not a tautology —
a counter at its host's plane and tile merges, and a test pins that.

**Two namings were tested and both rejected**, which is the phase's real
result. `04_...md` offers `customer_front` / `employee_workspace` either side
of a counter boundary, and Phase 5's 95%-asymmetric figure looked like exactly
that. (1) *The wide side is the customer front because that is where the ways
out are*: 84.1% of a host's exits are on the wide side — but that side also
carries 83.2% of the host's wall, a lift of **+0.024**, with only 43% of
bundles beating their own wall share. The wide side has the exits because it
has the wall. (2) *Merchandise stands on the customer side*: props on the wide
side 0.651 against a floor share of 0.730, a lift of **−0.080** — the opposite
of the guess. So the asymmetry is a shape fact, not a zoning fact, and
`region_candidates` emits zones with **no names** and carries the rejections
in `REJECTED_ZONE_NAMINGS`.

**Stated ceiling.** The owner's shop reference names apparel bay, display
window and selling floor as three zones; they share one plane and one tile and
differ only in what they hold, so this view cannot separate them. That is
anchor evidence, not geometric evidence, and the report says so rather than
inventing a split.

## Already in the repository

`reachability.py` already assigns *roles* to non-playable geometry
(logic_closet, letterforms) — the precedent for role assignment from
relations. The e6m1-shop reference records counter / retail floor / display
clusters for one real shop.

## Gap

In-room functional zoning (shop floor, counter boundary, storage, office
corner) as mined candidates.

## Agent task

Using Phase 5 bundles + circulation from `spatial.py`, mine functional
region candidates in the maps where anchors already exist (E6M1 shop first),
then search analogues corpus-wide. Hierarchical containment in the output.

## Exit criteria

The system can explain that one room contains multiple functional zones,
with evidence.

---

# Phase 7 — Facade grammar (DONE, 2026-08-31)

**Status: complete.** `anchors.find_facades` mines facade candidates as
maximal **collinear** runs of a sky-lit reachable sector's wall loop, at least
two 1024-unit bays long, interrupted by at least one opening — where an
opening is a two-sided wall with a **header**, per `06_...md`: the facade owns
the openings. Signage is a member of the hierarchy (building → facade → bay →
opening → signage), not decoration, per owner steering.
`anchors.interior_components` and `anchors.party_wall_gaps` answer the
building-extent question the first pass left open. Reports
`reports/blood-facade-grammar.{json,md}` and
`reports/blood-party-walls.{json,md}`, frames under
`reports/blood-facade-views/`, tests in `tests/test_facade.py` (43) and
`tests/test_party_walls.py` (19) and `tests/test_lintel.py` (22), with 36 of 36
non-equivalent mutants caught. The facade JSON is abridged — every candidate in
full is 32 MB — and says so.

**Two defects, both found by the synthetic fixture rather than the corpus.**
The numbers below are from the corrected extractor; none of the first draft's
survive, and the reports carry both corrections rather than quietly restating.

1. *The corner rule.* The first collinearity predicate measured the candidate
   wall's **near** end, which in a closed loop is the previous wall's end and
   lies on the run's line by construction. It collapsed to
   `|dx_run| · |dy| / L` — correct for an east–west run, identically zero for
   a north–south one, so every north–south street ran through its own corners.
   The tell was in the draft as a limitation: median sign-to-plane distance
   429 units, now **4**, and no letter more than 5 units off its plane.
2. *The lintel rule.* The first extractor counted every two-sided wall as an
   opening. **3187 of 4331 were not openings**: 2559 kerbs and 628 seams —
   two sky-lit street sectors meeting at a step in the pavement, no hole and
   no wall above. Requiring a header drops all 3187 and loses 4 genuine indoor
   neighbours. Campaign candidates fall 3570 → 890, multi-opening runs
   450 → 131, signed facades 27 → 11 — and the 11 are all real shopfronts
   (LOADING, FEINMAN MEATS, STORAGE, EVERYTHING, BURGERS, SCREAMS, WATER, ICE,
   BAIT) where the 27 included stray letters standing on pavement.

**The exit criterion, answered with numbers.** 890 campaign candidates in 37
maps; 131 have more than one opening, which is where "belonging together"
means anything. What keeps them coherent: **one wall tile across the whole run
(98%), then a header datum (79%) and a sill datum (77%) together, then a thin
helper sector (71%)** — and *not* the bay grid, which 31% of their openings
land on. Header and sill are within two points on 131 runs and are
deliberately not ranked against one another.

**A shipped constant partly contradicted.** `facade_pass.py`'s
16-world-units-per-tile-pixel scale is confirmed corpus-wide (3869/5275, 73%)
and is what makes `BAY = 1024` real. Its other two claims do not generalize:
world-phased `x_panning` is 20% campaign-wide (E6M3 80%, E6M1 72%) and header
cstat bit 4 is 28% (E3M1 38%). Both are local habits, and blood-city should
not adopt them as rules. E6M3, not E3M1, is the campaign's most disciplined
street: 81% of its openings a whole number of bays wide against 26%
campaign-wide.

**Signage.** 86 letter sprites on 11 facades (3 campaign in 2 maps, 8 curated
— the statistics lean on Death Wish and say so). 100% flat on the wall, none a
perpendicular flag; median 2.54 player heights up; 77% in the middle half of
their run; 84% within one bay of an opening, 96% in the campaign. And the
placement rule the lintel fix made visible: **every campaign sign letter
(26/26) sits above the header of the opening it belongs to**, 85% corpus-wide.
The two-tier reading from the E3M2 frame is confirmed but rests on 2 facades
of 11 — real, not a convention.

**Building extent: the objection was measured and withdrawn.** The first pass
refused `facade_run()` because a candidate is a plane, not a building.
`party_wall_gaps` tests that against the interior — two openings are in one
building when their interiors connect without going back outside — and finds
that **a run serving any interior serves exactly one building 98% of the time**
(732/749), never below four bays, 2% at four to eight, 12% at eight to
sixteen, 20% above. The city-block edge is real and is a long-run problem.
Most of what looked like a run crossing a boundary was a stretch of pavement.

**What marks a boundary, when there is one: almost nothing.** Over 241 judged
pairs `gap_bays ≥ 0.1875` scores 0.877, but only because 177 of the 222
one-building pairs have no pier at all — they are two halves of one hole. On
the 63 pairs a pier genuinely separates, **only `header_changes` clears the
0.65 floor (0.711)**, and it transfers across nine maps at 0.75–1.00.
**Material is not a weak signal but the absence of one**: tile change fires on
zero pairs of either class, which follows from the 98% one-tile figure. Pier
width falls to 0.617 — Blood puts two- and three-bay piers *inside* one
shopfront (E1M3 median 2.5 bays, E3M6 3.0).

**The lintel band: recoverable, and not what places a sign.** The last stated
blocker, measured. Blood paints its cornices and plinths into the wall art, so
the band lives at a fixed texture row: `art.course_rows` finds it and
`texture_align.course_z` puts it in the world. Every tile carrying campaign or
curated signage has courses, and tile 80's bottom course, hung from the E3M2
loading bay's head, lands 3 texture pixels below the LOADING letters — the band
the rendered frame shows, computed from the art.

**But Blood does not use it.** Letters sit within 3 texture rows of a painted
course 22% of the time against a **27% null** for random rows on the same
tiles — no closer than chance, marginally further. Nor is anything else tight:
the best of four candidate datums is height above the street floor at a
coefficient of variation of 0.33 (1.69 to 5.13 player heights), and measuring
from the opening's head is *worse* (cv 0.79) even though every campaign letter
is above it. The head is a constraint, not a datum.

**Constructor promotion: unblocked, not yet done.** The blocker dissolves the
opposite way round from expected — not because the missing datum was found, but
because **there is no datum to miss**. "A constructor cannot place the band" is
therefore not a reason to refuse `facade_run()`: placing a sign at ~2.5 player
heights above the street and above its opening's head is as right as Blood is,
and can carry the spread instead of implying a precision the corpus lacks.
What promotion still needs is a generated facade that survives the validators
and the engine — reading is not building — and opening positions taken rather
than invented, since 53 repeating runs in 890 is not enough recurrence to give
rhythm a default. Report `reports/blood-lintel-band.{json,md}`, tests in
`tests/test_lintel.py` (22, 8 of 8 mutants caught).

**A third defect, found on the way.** A wall texture's vertical span had two
definitions in the codebase, reciprocal in `y_repeat` and agreeing only at
`y_repeat` 16. `texture_align.repeat_span` is right — under it 48% of the
campaign's 51571 one-sided walls with known art are exactly one repeat tall,
against a mode of four repeats under the other — and `aperture.tile_span_z`
now delegates to it. The dimensional check agrees: Blood's z is 16 times finer
than x and y, so 2048/`y_repeat` is 256 z per texture pixel at `y_repeat` 8,
which is 16 world units — the same 16 units per pixel the facade scale runs at
horizontally. At the pairing Blood pins, a wall texture is square.
`snap_leaf`'s docstring arithmetic was scaled by that error: tile 22 at
`y_repeat` 8 spans 32768 z, which is the campaign's median aperture leaf
outright — one repeat, not four — and over the 540 campaign walls carrying it
the tile draws a median of 1.00 times up its wall. `at_least` drops from 2 to 1,
which against the corrected span would otherwise have doubled every leaf.

**Built, 2026-08-31: `aperture.facade_run`.** The phase's reading was crossed
into authoring. One street frontage emitted from the measured defaults and
nothing else, at two widths, in `projects/facade-pilot/`. Verified with "it
compiled" excluded: `validate`, `roundtrip` (byte-exact) and
`validate-authored` all clean at both widths, geometry-audit native 0 /
authored 0, and an NBlood load/spawn smoke reaching map_initialization and the
game loop. Width invariance holds -- at 6 and 10 bays the bay, the reveal, both
datums, both materials and the sign seat are identical, which is Phase 13's
exit shape piloted early. Report `reports/blood-facade-build.md`, tests
`tests/test_facade_run.py` (26, 11 of 11 mutants caught).

**Building corrected the reading twice, and both corrections are in the
phase's numbers now.**

1. *The datums were annotations.* Recording `header_z` beside the opening left
   the mouth open floor-to-ceiling; the placement validator caught it as sign
   letters hanging over a hole. The header **is** the neighbour's ceiling, so
   it shapes the opening rather than describing it.
2. *A facade wall has thickness, and the piers are void.* Giving the interior
   the whole frontage and declaring the spans solid is a wall sandwich, which
   the authored-geometry gate rejects. Asked directly, the corpus is
   unanimous: of **780 campaign facade solid walls, 0 have a reversed
   coincident partner and 780 stand alone**. So the interior is set back and
   each opening is a passage cut through the wall -- the reveal -- whose depth
   is measured too: 256 and 512 are the commonest of the 1140 sectors behind a
   campaign facade opening, and 41% are at or under 512.

`facade_run` is a **composable helper, not a `vocabulary.py` constructor**.
That module admits a concept only when a compact parameter set reproduces
held-out examples, which has never been run; the blockers are returned on every
build rather than left in a comment.

## Already in the repository

`aperture.py` (an opening is a leaf plus mediation; reveal dressing rules),
`texture_align.py`, `lettering.py`, run-rhythm and wall-thickness knowledge
files, rendered street views under `projects/blood-city/references/
e6m1-shop-views/`.

## Gap

Facade/bay hierarchy as a mined object: main plane, bays, datums (sill /
header / cornice), rhythm, style inheritance.

## Agent task

Facade candidate extractor over street-facing campaign maps (E6M1 and the
city episodes are natural pilots): identify facade extent, plane, openings,
thin helper sectors, measure repeated datums; render street views for
validation; search cross-map analogues; keep counterexamples.

## Exit criteria

The system can explain why several openings belong to one facade and what
keeps it coherent. Only then may `facade_run()`-style constructors be
promoted into `vocabulary.py`.

---

# Phase 8 — Neutral dynamic-state observations  **[DONE — Z-motion and swept; the polygon sweep is open]**

**Owner steering (2026-08-31), the phase's program in one example.** The
turnstile is where several planes meet — a kind of mechanism, a kind of
space, a kind of style — and mechanics must be learned *generally*, factored
along exactly those planes:

1. **Physical primitive** — "a sector rotates about an axis": sector type,
   the origin marker with its position *and angle*, busy_time as
   speed/direction. Engine fact, no semantics.
2. **Carried parts** — the sprites riding the motion (the turnstile's blade
   grates) and their *relations* to the axis — `assembly.py`'s domain.
3. **Embedding** — where it sits. This is where meaning is born, and it is
   already measured: 88 instances of the same auto-rotating primitive, only
   6 are doors; the rest are a carnival ride, station rotors, fans. Same
   machine, different design object, decided by space, never by fields.
4. **Style/readability** — the blades being see-through grates, the
   counter-rotating pair, the ambient sound riding along.

The same primitive family serves other purposes across the corpus, so this
phase delivers a neutral state-change vocabulary plus the rule that the
*name* is assigned from embedding — never a catalog of named prefabs. The
`turnstile` constructor in `mechanism.py` is one worked example of the
decomposition, not the deliverable's shape.

**Owner-attested E1M1 mechanism reading (2026-09-01; sector ids
owner-supplied, start/links verified against the map).** The campaign's
opening is a showcase of themed realizations of the slide/rotate/ROR
primitives — many *design objects* on the same machinery:

- **the casket** — CORRECTED (owner, 2026-09-01; every field verified): a
  FOUR-sector construct, two pairs. Hole sides: s28 (upper) + s30 (lower,
  the player start), both kSectorSlideMarked, ROR-linked (link 10, sprites
  47/46). Cover sides: s27 + s29, plain sectors. Each slide sector moves
  exactly ONE flagged wall (cstat 16384) — s28's wall 221 against s27,
  s30's wall 229 against s29 — and that wall is the hole/cover BOUNDARY:
  its travel re-partitions plan area between the two, sliding the lid
  open. The same travel vector runs on both sides of the ROR plane
  (markers 42→43 Δx −1916, 44→45 Δx −1912; the "to" markers stand inside
  the cover sectors), synced on rx 102, so the revealed holes meet through
  the link. Owner's category: a **sliding ceiling/floor door** — planar
  motion gating a VERTICAL crossing. Three concepts our stack lacks:
  boundary-wall area re-partition, ROR links CONDITIONED by cover position
  (conditional.py treats links as always-on — a Phase 9 gap), and the
  paired-travel-across-a-link pattern as a recognizable design object.
  *Narrative* — the primitive dressed as waking from a coffin.
  **Owner-authored oracle: `maps/blood/mechanism/casket.map` (2026-09-01)**
  — a minimal 7-sector demonstration of the same principle (floor sliding
  doors uncovering a walkable ROR stack), and it teaches two dialects
  E1M1 does not: the MOTOR may sit on either side of the boundary (here
  the 614 sectors are the LIDS s2/s5 and the link-bearing holes s3/s6 are
  plain — role assignment is free, only the flagged boundary matters),
  and BOTH sides of the boundary wall pair may carry the flag (walls
  18+22, 36+40) where E1M1 flags one. Also attested: lid thickness as a
  1024 step between tray and hole; travel = full cover with the tray
  sized to receive (the invariant the zoo build violated); one channel
  (rx 100) syncing both planes; link markers 2332/2331 at exactly the
  meeting planes, data_1-paired, statnum 0. **Answered, and then answered
  better (2026-09-01): INTENT, not an editor leftover.** `trInit` translates
  a moving sector by -65536 of the marker delta and records that as the base
  (`triggers.cpp:2224-2245`), so the geometry saved in a map is the pose at
  busy 65536 — state ON — always. A sector declaring `state=1` therefore
  starts exactly where it was drawn, which is what s2 does and what its
  author meant. The earlier "leftover" reading came from our own from/to
  marker model and did not survive the loader. Both planes are DRAWN in the
  same
  physical pose — boundary at the on-marker — but `trInit` treats the
  drawn geometry as the pose at busy 1, so a state-0 sector displaces
  itself by the whole marker separation the instant the level loads.
  Measured with `motion_sim`: s2 rests where it was drawn (displacement
  0) and s5 jumps 1920. Two lids on ONE channel, out of step from the
  first frame. `tests/test_attested_constructs.py` pins both numbers. This map is the primary fixture for the
  planar-door constructor and the swept-state validation gate, and
  reading it field-by-field corrected the MOTION MODEL itself:
  `TranslateSector` drags a flagged wall's own vertex **and its
  `point2`'s** unless that next wall is flagged too
  (`triggers.cpp:897-909`), which is how flagging ONE wall translates a
  whole EDGE. `motion_sim` moved only the flagged vertex, so it sheared
  every Marked slide instead of sliding it — the oracle's lid came back
  as a 2228224-unit trapezoid where the engine gives a 2048x128 strip.
  Every swept measurement taken before that fix was of the wrong shape. s30's z rise (floor
  −20480 → −26624) is NOT part of the lid mechanism — it lifts the player
  so they can jump out. A new category: **ergonomic-assist motion**,
  present for the body, not for topology; a reading that counts it as part
  of the door's gating misreads the construct. And the z endpoints are
  NOT a type-600 privilege: the two z states are available on other
  sector types too, so rotation or translation composes freely with z
  travel — the casket's s30 (614 + z) is the attested proof.

**The owner's constitution for this whole track (2026-09-01): Blood has a
LANGUAGE of mechanisms — more sophisticated than Duke3D's — and the goal
is to understand the language, never to slavishly copy examples.** The
grammar as currently understood:

```text
verbs        sector type selects the XY motion (slide/rotate/path/...);
             the XSECTOR z endpoints are an ORTHOGONAL z verb available
             regardless of type — verbs compose on one sector
payload      wall cstat flags (16384/32768) and sprite flags select what
             moves; 616/617 drag every wall, 614/615 only flagged ones;
             a payload can be sprites alone (E1M1 s65's gate)
parameters   MARKERS ARE STATE-ANCHORED, NOT JOURNEY-ANCHORED (settled
             2026-09-01 against DOOR-CURTAINS.map, three exemplars to
             the coordinate): type 3 = the position FOR STATE OFF,
             type 4 = the position FOR STATE ON, axis+angle = type 5.
             The mapper DRAWS the geometry at the ON pose (every
             tutorial curtain's fabric hem is saved exactly at its
             type-4 marker), and the XSECTOR `state` field decides where
             it snaps at load. "Rest" is not a marker concept — it is
             whatever `state` says. Our earlier from/to model was wrong
             both ways and is why the zoo curtains ran backwards; it
             also resolves the oracle map's s2 state=1 "mystery" — drawn
             at ON, meant to start there. Bonus from the same map: the
             tutorial curtain's fabric is an internal FIN with its own
             vertices (the seam built into the sector's own outline),
             which is why tutorial curtains never deform their rooms.
             maps/blood/mechanism/ (Vanilla/ + Modern/) is a goldmine of
             such single-mechanism tutorials — fixture them as they are
             consulted. And the owner's state-preview idea: the XMapEdit
             observer can render a mechanism's OFF and ON poses for a
             visual state check — the components already exist.
control bus  TX/RX channels + COMMAND VERBS (off/on/toggle/lock/unlock/
             ...) — a lever TXing Lock locks a door, it does not open it;
             reading every TX->RX as "operates" loses the verb. System
             channels (level_start...); tense/aspect = trigger_once /
             retrigger / interruptable / busy waves; chaining (s50→s51)
             and fan-out are sentences
interaction  three routes, orthogonal to everything else: XSECTOR Push/
             Wallpush; remote RX; and XWALL triggers ON THE PAYLOAD WALLS
             themselves TXing to their own sector's RX (E1M1 s4, verified:
             both leaves' walls carry tx 100 / Toggle / trigger_push while
             the sector has no push at all — the walls are the buttons,
             the sector is the motor). doors.py reads only portal XWALLs,
             so this third route is currently MISREAD as remote-only — a
             known model defect to fix.
payload dirs editor colors: cstat 16384 = BLUE = travels the marker
             vector; 32768 = GREEN = travels exactly opposite — one
             sector, two opposite-flagged leaves = a double door
state+verb   (owner, 2026-09-01) a command must fit the receiver's STATE:
             a mechanism saved at state ON receiving command ON is a
             no-op — the zoo casket shipped exactly that (state 1, switch
             sending only 1) and "did not work". Authoring rule: wire
             TOGGLE unless the intent needs a directed verb; reading
             rule: a trigger whose command cannot change the receiver's
             state is a detectable defect.
see-through  a walkable ROR stack is SEEN THROUGH only with floor picnum
             504 or floorstat & 0x180 (mirrors.cpp IsRorSector; already
             used in blood-city, forgotten in the zoo) — the view is a
             separate property from the warp, one more independent axis.
influence    (owner, 2026-09-01) A MECHANISM'S SENTENCE INCLUDES ITS
             EFFECT NETWORK — what it connects to and influences (the
             curtain whose room brightens via command-5 Link, the door
             that TXs onward). And the network competes for FINITE
             single-slot resources: a sector carries ONE XSECTOR — one
             rx, one tx, one state machine, one shade wave, one marker
             pair, one type; a wall one XWALL; a sprite one XSPRITE.
             Compositions therefore COLLIDE, and the answer is never
             "the door is impossible because the neighbour cannot take
             the light change" — it is a DECISION, made and reported:
             (a) SPLIT a sector to mint a new resource carrier (the
             lightpools pattern blood-city already uses), (b) insert a
             RELAY (a wired sprite carrying the extra channel hop),
             (c) REROUTE channels, or (d) DEGRADE the secondary effect
             under an intent hierarchy — mechanism function outranks
             mediation, mediation outranks presentation; the primary
             never blocks on the secondary. Every such decision is a
             reported finding per the authoring-loop law, and conflict
             DETECTION (two claims on one resource slot) is a gate-level
             check like ownership conflicts.
ownership    (owner hypothesis, 2026-09-01, confirmed by the accumulated
             cases) WALL OWNERSHIP IS TWOFOLD. Storage ownership is
             fixed by Build (each wall in exactly one sector's array; a
             boundary exists twice as a red-wall twin pair). FUNCTIONAL
             ownership — whose wall it is for a mechanism's purposes —
             is NOT fixed: it depends on the mechanism type and intent.
             Evidence: E1M1's curtain stretches walls stored in s125 AND
             their twins stored in the room; the casket's boundary wall
             functionally belongs to the four-sector construct; s65's
             functional payload is sprites; the tutorial's fabric fin is
             storage deliberately RESHAPED to match intended functional
             ownership (own vertices for the fabric). Our code assumed
             single ownership (spatial._owners, regions owning their
             walls) — a root cause of the zoo's integration defects.
             Consequences: a construct is a SUBGRAPH over sectors, walls,
             vertices and sprites that may cross storage boundaries;
             MechanismDecl members claim walls/vertices by ROLE across
             sectors; the motion-set closure is the computed functional
             ownership and the declared claims must match it; two
             constructs claiming one vertex with different motions is a
             detectable conflict; and constructors build storage topology
             (fins, seams, splits) TO SERVE declared functional
             ownership — never the other way round.
vertex drag  (owner, 2026-09-01, the deepest payload rule) motion moves
             VERTICES, not walls: a flagged wall carries its two points,
             and EVERY wall incident on a moved point drags with it (one
             end stays, one end moves). The true payload is the closure
             over shared vertices, not the flag set. Consequence:
             mechanisms need MOTION APERTURES — deliberate wall splits
             that bound the deformation, exactly as a doorway's jamb
             isolates the door's texture AND its motion. E1M1's curtain
             works because the room wall is SPLIT so the fabric's end
             vertices are its own; the zoo's curtain lacks that seam and
             deforms the whole room (its markers are also reversed, so
             rest reads open — two distinct defects). Detection law: for
             every mechanism, compute the ACTUAL motion set (flags +
             vertex closure) and diff it against the sentence's DECLARED
             payload — any extra member is an integration defect even
             when the geometry stays valid. This check belongs beside
             the swept-state gate and must run without an owner walk.
presentation shade/amplitude waves synced to state — the mechanism's
             visual voice, not decoration
composition  ROR links couple constructs across layers (casket); links
             can be CONDITIONED by cover position; ROR carries a global
             visibility budget authors design around
access       keys/locks gate the control bus, not the geometry; "Player
             only" (dude_lockout) excludes enemies — why E1M1's secret
             arc s26 carries it
voice        a SOUND QUARTET per mechanism: Off→On + its stopping,
             On→Off + its stopping — the mechanism's audio feedback for
             each direction and interruption; half its readability
bus timing   "send at ON/OFF" chooses WHEN in the transition the TX
             fires — chains can wait for arrival or fire immediately
hazards      Crush, DamageType, Depth/Underwater (medium) — a lift that
             crushes is one checkbox away from one that carries
ambient      CONTINUOUS MOTION (bob floor/ceiling, rotate, Theta, always)
             — perpetual motion WITHOUT the bus, a different class from
             rx-7 self-retriggering rotors; plus MOTION FX texture
             panning (conveyors, currents), wind, drag
light color  color lights / pal2 per surface
ergonomics   small motions exist for the player's body (the casket
             lift-out), not for topology — a separate reading category

The XMapEdit sector dialog IS the documented property surface (owner
screenshots, 2026-09-01): the property-model deliverable should be
structured panel-by-panel against it, each field source-cited and its
campaign usage measured — an axis the campaign never touches is still
part of the language.
```

**MEDIATION ELEMENTS (owner, 2026-09-01) — a first-class concept that
unifies threads the plan has been nibbling at separately** (the aperture
grammar's "leaf plus mediation", the motion apertures, chapter 04's
negative space, the kerb): a mediation is anything that JOINS an element
to its surroundings while SEPARATING them correctly. The taxonomy, each
kind with checkable functions:

```text
FRAME      guides motion and isolates it: the door jamb (195+200) that
           makes a leaf slide where intended; the casket tray's edges
SEAT       sets an object into a surface and bounds materials: the
           flowerpot for the flower, the plinth for the statue
HOLDER     the surrounding sectors that hold a pane: the shopfront's
           glass carried by its own reveal sectors
JUNCTION   joins two zone materials with a readable edge: the kerb
           between sidewalk and roadway
SEAM       bounds deformation: the wall splits that keep a curtain's
           motion out of the room (the motion aperture)
CLEARANCE  reserved volume with a function: a revolving door must have
           room to swing and must NOT collide with neighbouring
           geometry; a drawer's pull-out; a counter's workspace
```

**PREFAB SLOTS (owner, 2026-09-01 — a principle offered loosely, NOT to
be forced everywhere yet):** mediation composes with a slot mechanism. A
host element exposes a bounded sequence of SLOTS whose capacity derives
from its own dimensions — a corridor's length yields so many lamp/wall
slots, a facade's width yields bays (the 1024 bay grid IS this), a shelf
yields goods positions — and prefabs fill slots. A slot-filling prefab
may itself be a mediation hosting further slots: the planter (SEAT
toward the corridor) carries a row of flower slots. The reading side
already measures the counterpart (repeats_along, run-rhythm, lamp
service intervals, the E6M1 display row), so declared slots would be
checkable against mined rhythm. Per the smallest-useful-abstraction
guardrail: adopt it where a real case demands (corridor dressing, facade
bays, shelf stocking), not as a universal scheme.

Representation rule: every constructor OWNS its mediations — they are
part of the construct, never the caller's afterthought — and every
mediation's function is checkable: FRAME/SEAM by the motion-set gate,
CLEARANCE by a swept-volume-vs-surroundings check (the swept-state gate
validates the construct's own geometry; clearance extends it to what the
sweep must not touch), SEAT/HOLDER/JUNCTION by the usage-kind and
readability critics. In MechanismDecl (Phase 13), mediations are typed
members alongside lid/hole/switch, so a sentence declares not only what
moves but what seats, bounds and receives it.

A construct (casket, furnace, turnstile pair) is a *sentence* in this
language: several sectors conjugating different verbs on a shared bus.
Understanding means parsing sentences into the grammar; copying means
memorizing one sentence. Every mechanism deliverable is judged against
this.

**Properties are independent axes (owner, 2026-09-01; verified against
NBlood db.h).** A sector/wall/sprite's TYPE is only one property among
many, and the rest are orthogonal: XSPRITE carries identity-independent
trigger capabilities (Push/Vector/Impact/Pickup/Touch/Sight/Proximity —
any sprite with an XSPRITE can transmit; a switch's picnum toggle is its
type's behavior, its triggering is separate wiring), the bus
(txID/rxID/command/on/off), timing (busyTime/waitTime/restState/
Interruptable/wave), once-ness (triggerOnce/Decoupled), access
(key/locked/lockMsg), launch filters (skill and game-mode bits!), and
data1-4. XSECTOR likewise: two z states, markers, payload flags, shade
wave — all independent, all combinable.

**Mandate: ground the property model in the sources and documentation,
not in mined examples alone.** NBlood source (db.h structs, triggers.cpp
dispatch — read-only, the submodule is never touched) and the XMapEdit
manual (maps/blood/mechanism/xmapedit.pdf; reference/blood/xmpdocs/ for
art/qav/seq) are the authorities. Mining then measures which corner of
the language the campaign actually speaks — it never defines the
language. The precedent is established: blood_types.py cites
common_game.h, motion_sim transcribes TranslateSector, the payload rule
came from triggers.cpp. The missing deliverable is the systematic
PROPERTY MODEL: every XSECTOR/XWALL/XSPRITE axis, source-cited, with the
campaign's usage measured against it.
- **the crypt arc** — sector 26, kSectorRotate with a 20-wall arc,
  trigger_wall_push, dude_lockout: a curved wall revealing a *secret*.
- **the double sliding door out of the crypt** — sector 4 (one
  kSectorSlideMarked carrying both leaves). NOT the ROR pair.
- **the double rotating door** — sectors 50 + 51, two kSectorRotate leaves
  chained by channel (50 rx 105 → tx 106 → 51 rx 106).
- **sectors 65 + 90 are an ROR portal, not a door** — they connect the
  building's second storey. Sector 65 is *additionally* slide-marked so it
  can drive wall sprites 37/38, a small sliding gate at its entrance.
  Owner explanation: **multiple ROR sectors must not be visible at once or
  the view glitches**, so the level uses one giant ROR sector and hangs
  the gate's motion on it — an engine-constraint-driven authoring
  workaround, and a slide mechanism whose moved subject is *sprites*, not
  its own walls.
- **sector 99** — slides away and rats run out: an *ambush/flavor reveal*.
- **the curtain — full anatomy (owner 2026-09-01, wall ids verified
  exactly):** motor = s125 (slide-marked, markers 291/292); moving walls
  1200 (BLUE) and 1210 (GREEN) travel TOWARD each other; unflagged
  curtain walls 1201/1209/1183 STRETCH as the flagged endpoints migrate —
  the squash/stretch of texture 146 IS the animation. No sprites, no z.
  Interaction: XWALLs on the fabric walls (tx 125 → own rx, Toggle,
  trigger_push) — push the curtain anywhere. And s125 TXs 126 with
  command 5 (Link) to s124's shade amplitude: **the room's light follows
  the curtain's busy value continuously** — a three-layer sentence
  (motion → bus → presentation). General rule this teaches: door vs
  curtain is the SAME verb with different PAYLOAD TOPOLOGY — flag the
  whole leaf group and it translates rigidly (s4); flag only the leading
  edges and the neighbours deform elastically. Rigid vs elastic is a
  flagging pattern, not a mechanism type.
- **sector 63** — a plain standalone sliding door.
- **sector 70** — a shelf that is a *secret entrance*, sliding aside.
- **the furnace** — sector 88 is only the interior; the whole crematorium
  furnace composes a conveyor (sector 79) with sectors 81 and 89, embedded
  in the wall — an *assembly spanning mechanisms and static parts* that is
  deliberately hard to separate.
- **sectors 86 + 139** — a sink with dirty water (fixture, not a door).

Any swept-area/slide reading must describe all of these with ONE
vocabulary and let embedding name them: narrative, secret, progression,
ambush, furnishing, fixture, workaround. Two structural lessons: ROR links
participate in mechanism composition (the casket) *and* impose global
visibility constraints that reshape authoring (the 65/90 workaround); and
a slide sector's moved subject may be carried sprites rather than its own
geometry.

**Before mining the excluded remainder, split it (2026-08-31).** The hygiene
fix moved 30% of campaign object-context occurrences out of the default
statistics and called them "wiring". Opening that bin
(`reports/blood-wiring-placement.md`) shows three unrelated things, and only
one is material for this phase:

```text
sound              1765   ambience; no state, no reachability effect
marker              990   link/warp wiring, already consumed by reachability.py
start               144
hidden-thing        156   hidden-switch        85    >  triggers and spawners: THIS is Phase 8/9 input
generator            75   /
hidden-decoration    32
```

**Queued experiment: visible against hidden switches.** 85 campaign switch
sprites carry Build's invisible cstat bit while their type category is
`switch` -- a mapper deliberately concealing a trigger. `assembly.py` already
records the TX/RX side, so the contrast is runnable with existing machinery:
positives = hidden switches, comparison = visible ones, features = channel role
and what the switch commands, **not** geometry. The question is whether a
concealed trigger commands a different *kind* of thing than an exposed one. Use
`anchors.contrast_anchor_sets`' discipline: balanced accuracy, a map-transfer
check, counterexamples preserved. Not run yet; recorded so it is not lost.

Roughly two thirds is ambience and navigation. `excluded_candidates` are now
keyed on the wiring they hold (`wiring_signature`, `wiring_categories`) rather
than on the visible objects they lack, so the three parts are separable without
re-mining. The 316 hidden-mechanism occurrences plus the `logic_closet` sectors
are the trigger evidence; the rest should not be read as mechanisms.

Measured while checking: all 1247 campaign `kSoundSector` markers sit in
**reachable** geometry and 84% of their sectors hold no visible object at all,
so ambience pockets and switch closets are not even the same kind of sector.
Marker z is placed at an absolute height, not a fraction of the room (top-three
concentration 55% against 32%; only 3% at the sector midpoint), with 0 units
(27%) and 6400 units (19%) the two preferences out of 204 distinct values --
a preference, not a rule, and predicted but not determined by whether the
sector has headroom. 116 markers (9%) sit below their own floor, which closes
the Phase 4 contrast's last open counterexample.

**Turnstile template promoted, 2026-08-31 -- partly.** The
kSectorRotateMarked door subfamily (88 instances in 14 maps; the door/scenery
split is spatial, not a field) is now a template mined by name from E1M4
151/314 and DWE1M9 61/64, and a constructor: `mechanism.turnstile` and
`turnstile_pair`, beside `sliding_gate`. Report
`reports/blood-turnstile-build.md`, template
`projects/facade-pilot/reports/turnstile-template.json`, tests
`tests/test_turnstile.py` (23, 13 of 13 mutants caught).

Its **state-change reading is this phase's material**: the rotor takes the
`level_start` broadcast once on `rx_id` 7 and cycles for ever because both
waves retrigger, which is a state machine with one input and no rest pose --
a shape neither `doors.py` nor the Z-motion vocabulary covers.

Two corrections to `auto-rotators.md` came out of building it. The ambient
sound sprite is **not** a family trait -- E1M4 has one in both rotors and
DWE1M9 in neither -- so it is off by default. And direction is **not** the
marker's sign: both E1M4 rotors carry the same marker angle and mirrored busy
fields, so what counter-rotates a pair is which busy field carries the period.

**A silent defect found by the motion replay.** `construction.add_sprite`
masked every sprite angle to `& 2047`. For a kMarkerAxis the angle is not a
facing but the *travel* -- Blood interpolates `0 -> ang` -- and E1M4's -8192 is
four whole turns, which masks to exactly **0**: a rotor that does not move,
written silently with every validator green. The mask now applies to facings
only.

**Not proven, and the phase is not DONE on it:** that a player can pass through
at the mined spin rates. The available oracles are a load/spawn smoke and an
action oracle that presses Use once; neither walks a body through a moving
aperture. The map loads, spawns and survives. Relatedly, `motion_sim` agrees
with the original and cannot check this mechanism: a 615 sweeps only walls
flagged `cstat & 16384/32768`, every E1M4 rotor wall is `cstat 0`, and what
turns is the carried grates, which `blood_sweep` does not model.

## Already in the repository

Most of this phase: `assembly.py` (travel, pivot, carried parts),
`doors.py` (rest/open geometry, interaction, condition, feedback,
signifier), `mechanism.py` (template-driven construction), `motion_sim.py`
(engine-exact motion), `state_model.py`, `mechanisms.py` (cross-game
semantic layer).

## Gap

A single minimal physical-effect vocabulary (`move_z_floor`, `translate_xy`,
`change_blocking`, `destroy`, …) shared by these modules, and the
three-way experiment from `05_...md` (door vs lift vs third Z-motion
mechanism described without naming them incorrectly).

## Agent task

Extract the neutral effect vocabulary from what `assembly.py`/`doors.py`
already record — as a *reading*, not a rewrite. Run the door/lift/other
experiment on campaign maps and report LOW LEVEL / SPATIAL EFFECT /
SEMANTICS per `05_...md`.

## Exit criteria

The same low-level motion representation describes all three mechanisms;
semantic distinction comes from spatial context, and the report shows it.

## Status, 2026-08-31 — DONE for Z-motion, and for the switch question

**The vocabulary exists as a reading.** `bloodmap/effects.py`, over what
`doors.py` and `assembly.py` already record: `move_floor_z`,
`move_ceiling_z`, `translate_xy`, `rotate_about_axis`, factored along the
owner's four planes. `design_object` takes the embedding and **cannot be
handed a sector type** — there is no parameter for one.

**The three-way experiment is run and the exit criterion is met, for
Z-motion.** 2027 moving sectors in 43 campaign maps
(`reports/blood-effects-motion.md`):

```text
                      changes what fits   carries between   both   neither   undecidable
z_ceiling   646              540                 –            –      102          4
z_floor     541              122               168           95      152          4
z_split     180               56                39           47       32          6
slide       396                4                 –            –        5        387
rotate      263                2                 –            –        1        260
```

**Naming from the surface that moves gets 40% of them wrong** — 471 of 1179.
The third mechanism, described without its name, is a motion that changes
neither: 292 of them, of which 46 open to more than a crouching body and less
than a standing one. The reading returns `not decidable from z alone` for the
662 that only slide or turn, because both embedding questions are about a
vertical opening; filing those under "neither" was the first thing the
experiment did wrong.

**The queued hidden-vs-visible switch contrast is run, and the answer is
no.** 115 hidden switches in 18 maps against 1281 visible
(`reports/blood-effects-switches.md`). Not one feature of channel role or of
what is commanded reaches the 0.65 discriminator floor; the best is
`commands_nothing_in_this_map` at 0.614, and that one is the least
trustworthy of them. Two absolutes worth a targeted test rather than a
promotion: no hidden campaign switch ends the level (0/115 against 56/1281),
and none is keyed (0/115 against 17/1281). Concealment is not a property of
what a trigger does — which makes the placement question Phase 9's.

The count is 115 here against the 85 recorded above; the two selections
differ and are unreconciled.

**NOT done, and the phase is not DONE on it.** Slide and rotate have no
spatial effect test: `changes_what_fits` is z-only, and
`motion_sim.blood_sweep` cannot supply the swept-area one for the rotor
family. 650 mechanisms are returned undecided rather than guessed at.

**Still not proven: that a body passes a turnstile.** A passage oracle now
exists, is headless, and is calibrated in both directions — a body driven
across an open corridor is recorded crossing, the same corridor walled is
recorded staying put. It cannot answer for a rotor: the only available driver
refuses to enter a `kSectorRotateMarked` sector at all, at every period from
32 to 400, deriving `walk=0 why=no_stance` on the entry relation while the
exit relation is `walk=1`. `reports/blood-passage-oracle.md`. The turnstile's
promotion blocker stands and the Aldermack forecourt mouth is not sealed.

## Handoff to Phase 9

1. **Where hidden switches sit.** The contrast above is forbidden to look at
   geometry and came back empty, so what distinguishes a concealed trigger is
   its placement. That is the conditional view's question, and it is now a
   sharp one rather than a fishing expedition.
2. **The 292-sector residue is Phase 9 material.** A motion that changes
   neither passability nor elevation still changes *something* — 118 shut to
   nothing, 46 open only to a crouch. Conditional topology is where a
   crouch-only way and a closing gap stop being the same thing.
3. **`design_object` is the naming rule to build the conditional view on.**
   It reads embedding and nothing else, and Phase 9 should extend the
   embedding rather than reach back for fields.
4. **Slide and rotate need a swept-area effect test** before either can be
   named. Until then any conditional view over them is over undecided input.

---

# Phase 9 — Conditional topology and causal meaning  **[DONE — swept blocking states are open]**

## Already in the repository

`reachability.py` (at-rest reachability), `progression.py`,
`sp_understand.py` (physical walkability kept separate from allowed
progress), channel graphs in `fragment.py`/`assembly.py`.

## Gap

A derived `conditional_traversability` view: edges annotated with the
mechanism state that enables them, and the trigger → mechanism →
reachability chain.

## Agent task

Add the conditional view to `spatial.py`-style derived views, fed by Phase 8
effects. Pilots: one lift, one breakable barrier, one keyed door, on
campaign maps. Answer "what becomes reachable after this action" with
causal provenance.

## Exit criteria

The question above is answered mechanically and the explanation cites
native evidence (channels, XSECTOR fields), not prose.

## Status, 2026-08-31 — DONE for Z-motion

**The view exists.** `bloodmap/conditional.py`, a reading over
`reachability.py`'s graph and `effects.py`'s embedding, plus
`llmapper conditional`. Crossings are **directed** (climbing is capped at the
engine's step-up 6656, falling is not) and collapse into **routes**, which is
what a reader means by "the door": one mechanism, the two rooms it joins.

**The question is answered mechanically, and the explanation is fields.**
`llmapper conditional MAP --action destroy --target 373` returns the newly
reachable set and, per crossing, trigger → channel → mechanism → topology
delta → crossing. On E1M4's crack that reads: `sprite 373, type 408, shot,
irreversible` → `channel 119` → `sector 276, enabling state on` → `opening
0 → 28672` → `276 → 245`.

**The campaign, measured** (43 maps, `reports/blood-conditional-topology.md`):

```text
Z-motion mechanisms 1365   wired 1235   inert (nothing can reach them) 130
rotate and slide, scoped out                                          657
conditional crossings 4160  -> 1069 routes    never passable        1085
routes needing a key    87        routes that cannot be undone        156

routes by reading            triggers
door-like       665  62.2%   switch 514   push 264   shot 176
lift-like       182  17.0%   unknown 170  touch 70
both            134  12.5%
neither          88   8.2%
```

Not one of the 113 distinct gating channels is below 100: the reserved band
carries level start, exit and secrets and **never gates a door**.

**Three pilots, each checked against the raw XSECTOR and the editor
renderer**, not against the view's own graph. A lift (E1M3 s241: floor
18432 → -16384, exactly its two neighbours' floors, gains 33). A breakable
barrier (E1M4 sprite 373 → sectors 276/277, flush at rest, `trigger_once`,
gains 14 — and the renderer independently **refused** sector 276 for want of
standing clearance). A keyed door (E1M4 s295, `key=6`, gains 46 — and the
render from s294 shows a moon lock plate on the wall).

**The hidden-switch placement question is answered, and it is a null.**
`reports/blood-hidden-switch-placement.md`: no spatial feature reaches the
0.65 floor in either scope; the best is `distance_to_target` at 0.640. The
weak signals agree in direction — hidden switches sit further from what they
open, less often adjacent, less often in sight — but 0.64 on 22 positives is
a tendency, not a distinction. The reframing finding is that **57% of hidden
and 59% of visible switch sprites sit in a logic closet**, so the invisible
cstat bit is largely a construction detail of closet wiring rather than a
decision to hide a trigger. Both contrasts have been comparing two
populations that are mostly the same thing.

**115 against 85, reconciled and computed:** 115 = 85 hidden-switch
occurrences inside `mine_object_contexts`' excluded scope + 30 whose sector
is reachable *and* holds something visible. Both numbers are right; they
count sprites and occurrences-in-a-bin respectively.

**Slide and rotate unparked, 2026-09-01.** They are no longer excluded:
`effects.py` reads the engine's own instruction (two markers for a slide, one
for a rotate), **what the motion drags**, and how wide a gap the leaf
vacates. 659 swept sectors described, 538 of them opening a body's width.
`reports/blood-swept-mechanisms.md`.

Owner-attested E1M1 reading (sector ids owner-supplied) is the specification
and the evidence: one slide/rotate/ROR machinery, many design objects.

Three engine facts now encoded rather than rediscovered.
`TranslateSector`'s `bAllWalls` is `type == kSectorSlide/kSectorRotate`, so
the unmarked types 616/617 drag every wall and the **Marked** 614/615 drag
only walls flagged `cstat & 16384`/`& 32768` -- while **sprites are dragged
on their own 8192/16384 whatever the walls do**. 35 campaign mechanisms move
*only* sprites, E1M1's sector 65 among them: 49 walls, none flagged, two wall
sprites doing the whole job of a gate. Room-over-room participates in
mechanism composition (the casket is slide-marked *and* stack-linked) and is
a **budget** -- two ROR volumes must not be in view at once, so 11 of 43 maps
have none and most of the rest have a handful, and E1M1 reuses one big ROR
volume as a slide carrier rather than spending another. And
**kChannelLevelStart fires before the player moves**: E1M1's casket is opened
by a switch on rx 7 that no body can reach, and treating that as a player
action reported the level as 2 reachable sectors of 155.

**NOT done, and it is now the only gap.** *Which state of a swept mechanism
blocks* is answered for **5 of 628**. The cheap test -- does a leaf segment
cross the line between two portal midpoints -- is correct where it fires and
almost never fires, because a door's two portals are adjacent as often as
opposite (E1M1 s63's are 512 apart on the same side). Assuming the rest state
is the shut one is far worse and was measured as such: it cut E1M2 from 226
reachable sectors to 26. **The polygon sweep is what remains.**

The owner's eight design-object names are **not all recoverable from
embedding**, and the measurements say where it stops: E1M1's rat trap and its
curtain have identical topological signatures, and its plain sliding door is
more load-bearing than the double rotating door built as the way on. What is
assigned is narrative, technical workaround, fixture, and required against
side passage; `secret_within_reach` and `dudes_immediately_beyond` are
recorded and never named from.

The turnstile family sits inside the remaining gap and is parked by owner
decision; its passage blocker stands.

## Base graph resolved, 2026-09-01

**Three bases, one default, each saying what it assumes** (`conditional.BASES`):

```text
optimistic       reachability.portal_graph: every two-sided wall is a way.
                 Reaches behind shut doors.
blocking_aware   the default. portal_graph minus crossings whose wall carries
                 the blocking cstat, plus the blocking walls a kWallGib
                 mechanism reopens.
strict           spatial.walkable_at_rest: blocking flag, width under 512 and
                 opening under 4096 are all hard stops, none reopened.
```

**Only one wall mechanism reopens a blocked wall.** `triggers.cpp`
`SetupGibWallState` clears `cstat & 65` and the masked bit on both sides when
a kWallGib (type 511) XWALL's `state` is 1. Nothing else in the engine
changes a wall's blocking bit — a Z-motion sector moves floors and ceilings,
never cstat — so a blocking wall that is not a gib wall is shut for ever.

Campaign, 43 maps: 60839 two-sided walls, 2272 blocking (3.7%). Of those,
**205 are kWallGib, every one built shut and every one wired** — no
exceptions to open by hand. The rest are permanently solid: 1183 plain, 850
on a motion sector (the door's own jamb walls), 34 other XWALL types.

Two rules the measurement forced. A **wall pair** is shut when *either* side
carries the bit, because the engine sets it on one side and clears it on the
other. A **sector pair** is shut only when *every* wall pair between the two
blocks — reading it the other way made this base stricter than the strict
base, and E1M1 fell to 28 sectors against strict's 34, which is how the
mistake surfaced.

```text
map    sectors design |  optimistic | blocking-aware |   strict | sp_understand
E1M1       155    146 |  125 > 131  |     97 > 120   |  34 > 38 |     2 > 2
E1M2       313    293 |  231 > 238  |    226 > 233   | 218 > 225|   242 > 248
E1M3       329    320 |  227 > 269  |    211 > 243   | 208 > 240|   243 > 271
E1M4       398    387 |  260 > 362  |    253 > 357   | 231 > 308|   263 > 278
E2M2       290    260 |  221 > 255  |    201 > 230   | 195 > 222|   204 > 221
```

Final-reachable agreement with `sp_understand` is still **exact 0 of 5** on
every base; gaps on the blocking-aware base are 118, 15, 28, 79, 9. E1M1
remains the outlier for the reason above, which is a defect in
`analyze_progression`'s input rather than in any base.

**The three Phase 9 pilots return identical answers on all three bases** —
joins, reading, key and trigger kind unchanged. None of their crossings
carries a blocking flag, so no base can move them; the test asserts it.

**The 170 unknown-trigger routes are classified**, and they were never
unknown triggers. The classifier was measuring the absence of a
player-facing flag: `trigger_on` / `trigger_off` are *response* flags, not
causes. Adding `relay` (listens on one channel, retransmits on another),
`pickup`, `kill`, `generator` and `leave` (Blood's `trigger_exit`) takes the
residue from **170 routes to 9 causes**, all one type: kTrapExploder sprites
that transmit with no trigger flag and no `rx_id`, so nothing in the map says
what fires them.

## Handoff to Phase 10

1. ~~**Neither base graph is right, and they are wrong in opposite
   directions.**~~ **RESOLVED 2026-09-01, and the diagnosis above was
   wrong.** E1M1's two blocking-flagged start portals carry no XWALL, so
   nothing in the engine can ever open them — `analyze_spatial` is right to
   treat them as hard stops. The real cause is that the player start is a
   four-sector box whose way out is a **paired stack link** to sector 28:
   `analyze_spatial` files it under `known_non_portal_transitions` and
   `analyze_progression` never reads that list. The blocking-aware base is
   built and is now the default; see the Phase 9 status note below.
2. The multi-view bundle should carry the conditional view beside the spatial
   one, and carry which base it ran on.
3. 170 routes have a cause whose trigger kind is `unknown` — something
   transmits and nothing explains how it fires.
4. The switch question that survives is about **XWALLs**, not sprites: the
   face a player actually pushes. Nothing has measured those.

---

# Phase 10 — Multi-view understanding bundle  **[DONE — one map]**

## Already in the repository

`understanding.py` and `sp_understand.py` already bundle sensors;
`level_profile.py` gives the corpus-comparison view; `visual.py` the
rendered view.

## Gap

One map, all views, cross-view contradictions made explicit.

## Agent task

For one selected original map, produce one machine-readable bundle + one
human-readable report combining geometry, assemblies, functional regions,
mechanisms, conditional topology, progression, visual/readability — with a
section listing disagreements between views.

## Exit criteria

No single view pretends to be canonical; cross-view relations are explicit.

## Status, 2026-09-01 — DONE for one map

`bloodmap/bundle.py`, `reports/E1M4-bundle.json` (370 KiB) and
`reports/E1M4-bundle.md`. **All eight views gathered, none missing.** Every
view names the module that produced it and what that module assumes; nothing
is merged.

**E1M4 chosen over E3M2 and E6M1.** E3M2 exercises the conditional view
harder (65 routes and 29 lifts against 26 and 4); E1M4 carries the most
facades of any candidate (41) *and* three mechanisms already verified
against the raw XSECTOR and the editor renderer independently of any code
here. Checkability beat volume. The trade-off given up is lift variety.

```text
geometry            398 sectors, 3651 walls, 995 portals; 387 reachable
assemblies          56, in 30 distinct shapes
functional regions  257 candidates over 191 sectors (164 overlooks)
facades             41: 37 single, 2 repeating, 2 centered
effects             56 mechanisms; 29 not decidable from z alone
conditional         26 routes; 16 blocking crossings, 4 reopened, 14 shut
progression         253 at rest -> 357 after 5 rounds
visual              8 frames; 1 sector refused for want of clearance
```

**Five disagreements, none reconciled.** Reachability 357 against
`sp_understand`'s 278; 29 mechanisms both views refuse for the same reason
but count differently; 4 sectors that are both frontage and structure; 30
sectors the geometry calls player space that the traversal cannot enter; and
the renderer refusing sector 276 — which is really an *agreement*, two
readings with no shared code independently saying a body cannot stand there
until the crack is shot.

**NOT done.** One map only, and on that map 29 of 56 mechanisms are
undecidable, so the bundle describes about half of E1M4's machinery. The
rotate and slide swept-area reading is still the gap, and the turnstile
inside it stays parked.

---

# Realign — plumbing, 2026-09-01  **[Phase 11's prerequisite]**

Not a phase. An audit found the pipeline healthy and three structural
defects, all of them plumbing, and Phase 11 cannot be built on them.

**1. Owner knowledge was not consumed.** `owner-anchors-v1.json` -- 97 tiles
the owner named by hand -- was read by people and not by code, so every
module that needed a tile's meaning typed its own list. `bloodmap/
owner_anchors.py` is the typed, schema-validated access: by picnum, kind,
binding, the wiring set, the state pairs. A malformed entry now fails a test
instead of a mining run. `anchors.anchor_from_owner` and `owner_anchor_kit`
make a class out of the owner's readings (`anchor-mine --owner-anchor`,
`--owner-kit`), and `effects.payload` names what a mechanism's moving parts
are made of in the owner's words.

**The binding rule is executable.** The owner's principle -- a visually
singular tile binds its meaning, a generic surface is material -- becomes:
**strong-binding tiles may contribute naming evidence, weak and untested
ones never may.** Each use stamps provenance (`anchor 361, binding strong`)
so a wrong name is traceable to the tile it rested on. The rule bites
immediately: see the dressing plane below.

**2. Mechanism naming read only topology.** `design_role` v2 proposes across
four planes -- **position** (spawn, ROR pairing), **dressing** (strong-binding
owner tiles on the moving faces), **contents** (secrets and dudes beyond),
**topology** (the counterfactual) -- and reports which plane decided and
which others disagreed. On the owner's thirteen attested E1M1 cases it
recovers **7 of 13**, against 5 for the topology-only version: position 3,
contents 5, topology 5. `reports/blood-role-v2.md`.

The six misses are each traceable, and two are the most useful output of the
run. s4/s50/s51 are unplaceable because the swept blocking state is unknown
-- the parked polygon sweep. **s125's curtain is misnamed an ambush because
its tile (146) has no owner binding**, so the plane that would have called it
a furnishing is silent by the rule rather than guessing. A binding for 146
would fix it; that is a request, not a tuning knob. Features were **not**
tuned to hit thirteen labels.

The owner has attested one map, so there is no held-out test and **the
cross-cut frequency is uncharacterised**.

**3. The retrieval surface predated most of the knowledge.**
`bloodmap/knowledge_index.py` indexes the owner anchors, the pattern catalog,
every versioned knowledge file, every report (JSON *and* prose-only -- the
rotating-door census has no JSON and was unreachable), the bundle's
per-sector readings, and the promoted constructors. 334 entries, every one
naming the file it came from and its grade: **OWNER**, **DERIVED**,
**INTERPRETED**. `llmapper knowledge "332"` / `"swinging doors"` /
`"E1M4 sector 26"` all answer with sources from one entry point; a query
nothing knows about relaxes and says so rather than answering no.
`design-index` indexes maps by fingerprint and is a different axis; neither
subsumes the other.

---

# Pattern Zoo — standing infrastructure, 2026-09-01

The playable half of the batched review queue. `projects/pattern-zoo/` is a
generated gallery in which every pattern, mechanism and constructor the
pipeline has learned stands as one labelled exhibit, so the owner can walk
it, try everything, and send corrections **per exhibit label**.

Generated from a registry, never hand-placed. A conformance test fails when a
public constructor has no exhibit and no explicit skip reason, which is what
keeps the zoo current: **future constructor promotions must add an exhibit.**

Labels are unique and stable, because owner feedback arrives by label name.
Tour sheet: `reports/pattern-zoo-tour.md`.

## What v1 taught, 2026-09-01

The owner walked v1 and it failed **conceptually**. Not one door worked. Every
exhibit had hand-assembled its own `sector_behavior` dict and never set the
sector *type*, so the map contained **zero type-600 sectors** and the XSECTOR
data sat on type-0 sectors, which the engine ignores entirely. Alongside that:
mannequins floated (a floor sprite's z is its *centre*), the shelf run was a
sprite thrown at a wall (a shelf is a wall texture on shallow sectors), crates
were sprites (a crate is a sector volume wearing crate textures), and every
stall was 1.5 player heights against a campaign median of 1.96, so the facades
had no room to be facades.

v1 passed structural validation, byte-exact round trip, an NBlood load smoke
and twenty-four renders. **Every gate it passed was a gate about depiction.**

Two rules came out of it, and both are now enforced by the suite:

1. **A showcase is assembled from the constructors that own each concept**, or
   it is an honest EMPTY stall with the gap lettered on the wall. Re-deriving a
   mechanism from parts inside an exhibit is how the type came to be missing.
2. **It is verified by the understanding stack reading it back.**
   `projects/pattern-zoo/selfread.py` reads the built map with
   `bloodmap.effects` and `bloodmap.conditional` -- the same code that reads the
   campaign -- and checks every registry claim against what that reading finds:
   the sector type, the design object, the trigger, the channel, the key. A
   dead map fails the build. Two further checks catch what the owner found by
   walking: nothing the builder seated on a floor may hang off it, and no stall
   may be unreachable from the start.

The one-line version, for anything else the pipeline ever ships to a player:
**depictions pass renders and fail players.**

## What v3 taught, 2026-09-01: the knowledge was already here

The owner's verdict on v3 was that the knowledge existed in this repo -- in
the campaign corpus, in blood-city, in owner-anchors -- and the build neither
consumed nor enforced it. The corpus audit bears that out precisely. Every
tile error the zoo shipped was already answerable from a table nobody had
compiled: 400 is a facade backdrop the owner had labelled, 2026 is a shelf the
campaign only ever hangs on walls, 502 is a grate that appears 27 times as an
over_picnum and never on a floor.

So the fix is not more knowledge, it is **plumbing**: the usage-kind table is
mined once, stored in knowledge, read by a validator, and run by the zoo's own
gate. A build can no longer pass a gate the rest of the pipeline would fail it
on -- which is exactly how v3 shipped eighteen transparency violations inside
the exhibit that teaches the transparency law.

A third rule arrived with the rebuild and is enforced by review rather than by
test: a stall is a **habitat**, not a box. Its size, material and dressing are
derived from that mechanism's own mined evidence and constitute a claim about
correct usage. Where a habitat needs a technique no constructor owns, the
honest-empty rule applies to the *dressing* too: the mechanism is built in a
plainer room and the gap is recorded in the registry's `hand_composed` field,
which the tour sheet prints as a promotion candidate.

## What v2 taught, 2026-09-01: sections

The owner walked v2 and rejected its **shape**. The mechanisms worked, and it
was still wrong: a corridor of one-exhibit cells is not a gallery, and a
mechanism shown in a generic box says nothing about how it is used. The
habitat rule had been applied one room at a time, which is too small a unit
for it to mean anything.

v3 is therefore built out of **sections**. A section is one environment --
a shop, a street, a sewer, a park -- holding the several exhibits that belong
together in it, and the section is the habitat claim. The SHOP section is
E6M1's shop re-expressed through our own constructors, which is also what
functional zoning (Phase 6) looks like when it is built rather than read.

Two structural facts fell out of building it, and both are general:

**A label cannot go on the wall of the thing it names.** An exhibit is
entitled to open all of its own wall -- a doorway, a park, a frontage -- and
letters hung across an opening are refused, correctly. So every bay is
preceded by a **pier** of solid wall, sized from the word it has to carry and
one unit wider so the label can be justified hard against the bay it names.
Centred on a tight pier, a label reads as belonging to either neighbour.

**The representation taxonomy is checkable, and worth checking.** A concept
realized at the wrong level is a build failure, not a style choice: a shelf is
wall texture on shallow sectors, a crate is a sector volume, a mannequin is a
sprite, a grate is a maskwall panel. `selfread.py` now asserts, per exhibit,
that a tile claimed as wall texture is on that exhibit's own walls and is not
thrown anywhere as a sprite. It also enforces the owner's **transparency law**
-- no mask-carrying tile on any floor or ceiling, 0 of 28158 campaign non-sky
surface slots -- and that check caught two violations in this very build: the
tile museum wearing sprite tiles on its panel floors, and the sewer grate laid
underfoot.

## Engine usage laws, 2026-09-01

Four laws about **where a tile may go**, each sourced in the engine, measured
on the campaign, and registered in `bloodmap.rules_blood` so authored-map
validation and the zoo's self-reading gate both enforce them. Grades are in
`knowledge/blood/design/rules-v1.json`; the table they read is
`knowledge/blood/design/usage-kinds-v1.json`.

```text
mask-tile-off-plain-surfaces     0 / 78805   engine.cpp:2902 ceilscan,
  a mask-coloured tile never goes on a floor, a ceiling, or a one-sided
  wall's picnum. Those have nothing behind them, so the engine draws the
  frame buffer through the holes. 0 of 26383 non-parallax surface slots and
  0 of 52422 one-sided wall slots. TWO tiles break it on two-sided walls
  across 23 of 60839 slots -- 142 and 2464 -- which is where the owner's
  suspected door-leaf exception lives and is too few to name a family, so
  the rule leaves two-sided walls alone.

parallax-wears-a-sky-tile        0 / 1775    usage-kinds sky_family
  a parallaxed surface wears a tile from the sky family, which is DERIVED
  and turns out to be exactly three: 2500, 3491, 3678. They are backdrops
  rather than skies -- 3678 is a dark rock face used as a cavern roof 363
  times -- and all three are 64x400.

sky-tile-is-parallaxed           5 / 1780    tiles.cpp:281 tileUpdatePicSiz
  and the mirror: a sky tile on a surface carries the bit. Without it the
  strip is sampled through picsiz as 64x256. The campaign slips 5 times.

tile-sits-in-an-attested-slot    tautological, and useful anyway
  a tile goes in a slot the campaign is attested to use it in. Its grade is
  0 BY CONSTRUCTION, because the table is mined from the corpus it is graded
  against -- so the number means nothing and the rule is a WARNING tier. Its
  value is entirely on authored maps, where it caught shelf goods laid on a
  floor, crate tiles on a ceiling, and six sprite cut-outs painted on walls.
```

**The aspect law already existed and was already enforced.** The owner's list
had it as a fourth violation; `flat-tile-power-of-two` has been in
`rules_blood` and in `PlanarLayout._validate_flat_tiles` all along, and the
zoo -- which builds through PlanarLayout -- never broke it. The finding is
that it INTERLOCKS with parallax: all three sky tiles are 64x400, so a sky
tile on an ordinary ceiling is wrong twice, and the aspect law's exemption
for parallax surfaces is not a loophole but the other half of the same fact.

**Slot correctness is not the whole of usage.** `usage_kinds.overused`
compares a map's share of each wall tile against the campaign's. Tile 400 is
a multi-storey facade backdrop with 48 wall slots in 43 maps; the zoo made it
the default gallery wall and used it 162 times in one level -- 786x the
campaign rate, every use in an attested slot, every one passing the
usage-kind check. That is the crudest possible instrument and it found the
largest error in the build.

## Two payload shapes the model could not name

`effects.payload_shape` reads what the ARRANGEMENT of flagged walls means,
where before the model could only list which walls moved. Measured over the
campaign's 659 swept sectors:

```text
340  nothing moves                sprite payload, or an unmarked type
154  part of the sector travels   E1M1 s63, the plain slide door
104  the sector resizes itself    OPPOSITE flags: one end advances while the
                                  other retreats, so the sector's own extent
                                  changes and the texture between deforms.
                                  E1M1 s125 is the curtain; s4 is a two-leaf
                                  door built the same way
 44  boundary re-partition        ONE flagged wall, and it is the portal to a
                                  neighbour: its travel moves the line
                                  between two sectors, so plan area passes
                                  from one to the other. E1M1 s28 and s30 are
                                  the casket
 17  the whole sector travels
```

Both named shapes are now constructors: `mechanism.curtain` and
`mechanism.planar_door`, each built from E1M1's own fields rather than from
memory. `PlanarLayout.carry_wall` is what made them possible -- until it
existed there was no way to say which walls a Marked slide drags, and two
whole classes of Blood mechanism could not be authored at all.

## Promotion queue, 2026-09-01

Promoted in this run, each with a zoo exhibit the conformance test holds it
to: the four usage laws above; `PlanarLayout.carry_wall` and `paint_wall`;
`mechanism.curtain` (CURTAIN); `mechanism.planar_door` (CASKET);
`mechanism.shade_wave` (CASKET, on the cover); `aperture.maskwall_panel`
(SEWER AND TECH, which had its grate lettered as a gap until this existed);
`effects.payload_shape`; `furniture.place` and `furniture.mounting_for`.

Queued, ranked by recurrence x cost. Recurrence is how many
`projects/blood-city/level/*.py` modules reach for the technique by hand.

```text
rank  technique                     recurrence  why it is not done here
1     ROR links CONDITIONED by      --          DONE 2026-09-01, and one
      cover position                            expectation it disproved;
                                                see below
2     a lift constructor            --          DONE 2026-09-01:
      (floor-travelling z-motion)               mechanism.lift, built to
                                                Vanilla/MACHINERY-LIFT.map;
                                                it needs no markers, because
                                                the z pair IS the state pair
3     porch                         10          street anatomy, with kerb
4     grate/grille placement        9           HALF DONE: maskwall_panel is
                                                the wall case; a free-standing
                                                grille sprite is not
5     jamb dressing 195 + 200       5           the reveal is built by hand in
                                                every door exhibit
6     kerb                          5           needs street anatomy first
7     a service run                 --          four pipe sectors chained by
                                                hand in the zoo
8     shop fittings on PlanarLayout --          templates.py owns them on the
                                                levelprog stack and cannot be
                                                called from a PlanarLayout
9     free-standing volumes         --          PlanarLayout refuses a region
                                                wholly inside another, so a
                                                crate cannot stand in the
                                                middle of a floor
10    wall-level interaction route  --

Added 2026-09-01 from the owner-requested sweep of PROJECT MAPS (sources
beyond blood-city; several are MechanismDecl-shaped sentences and should
land as its first citizens):

```text
rank  technique                     source & why
11    WATER LINK pair               reasoned-authoring-v1 candidate_v6 — the
      (kMarkerUp/LowWater, data1-   repo's reference artifact for links (ROR
      paired, congruent underwater  debugging diffed against it); a link-
      volume ELSEWHERE, Underwater  primitive dialect (medium change), and
      flag; + ripple helper)        the harbor/bay wishlist needs it
12    PROSCENIUM / stage            l3_theatre — measured law already ("a
                                    stage under a LOWER ceiling than the
                                    house; one-max-step rise; 20k arch"),
                                    owner-approved on the Theatre Row walk;
                                    the curtain's natural habitat
13    BREAKABLE GLASS pane          l3_theatre — two-sided gib wall with a
                                    shop behind; conditional already READS
                                    kWallGib, nothing writes it; storefronts
                                    for the city overhaul
14    STAGED EXPLOSION chain        l3_foundry dock (channel 30) + the
                                    crack->exploder vocabulary from DNE3L6 —
                                    an irreversible-spectacle sentence
15    HATCH link + join-by-faces    vertical-fragment — _hatch_link and the
      (against/side_of idiom)       against()/side_of() face-joining helpers
                                    that levelprog's faces should absorb
16    AMBIENT SOUND placement       setpieces.sound_gizmo + the measured
                                    blood-wiring-placement heights (0 and
                                    6400 as the two practices) — promote
                                    with mined defaults
17    the VOLUME-ON-FLOOR family    setpieces raised_solid/stepped_solid/
      (counter, altar, basin,       inset/canopy/stall — blocked on rank 9
      stall, canopy...)             (free-standing volumes); when rank 9
                                    lands, this whole family moves into
                                    bloodmap with it
```

Synergy note: reports/E2M2-mechanism-patterns.json (fan-out TX/RX, single
motion gates) has been waiting for "a mechanism view in the catalog" —
MechanismDecl IS that view; when it lands, the E2M2 compositions become
sentence templates rather than a stranded report.          doors.py models the sector
      in doors.py                               route; the XWALL one is unread
11    command-verb reading on the   --          command 5 on E1M1's curtain is
      bus                                       unread by the whole stack
```

**Not promoted on purpose.** `aperture.facade_run` stays a helper rather than
a `vocabulary` constructor, for the reasons its own report gives: the second
half of the admission rule -- a compact parameter set reproducing held-out
examples -- has never been run.

## Rank 1, done 2026-09-01 -- and one thing it disproved

`PlanarLayout.stack_link` builds a room-over-room pair: two marker sprites,
types 11 and 12, matched on their XSPRITE `data_1`, on **statnum 0** because
statnum 10 is culled at load and a link built there is a link that does not
exist. Making a link declares the plan overlap it necessarily has, which is
otherwise refused. `reachability.link_pairs` finds the result.

`conditional.conditioned_links` and `repartition_edges` close the two model
gaps together. A stack link one of whose sectors is a boundary re-partition
mover is no longer treated as always open: it becomes a conditional edge
gated on that mechanism's channel, with its cause chain. That is what makes a
planar door a topology change at all -- it has no portal that opens or shuts,
so every route through one had been invisible, and the zoo's casket could
claim no trigger.

**And the framing it disproved.** The expected picture was that at rest the
cover lies ACROSS the link and no body passes, and that opening the lid
uncovers it. E1M1's own casket does not do that: on BOTH halves the link
marker sits deep inside the hole, well clear of the band the boundary wall
sweeps. So `covered_at_rest` is measured and REPORTED, and the edge is gated
on the structural fact instead -- that one side of the link is a
re-partitioning mover, so the plan area the link plane sits in changes hands.
The intuitive story is not what those fields say, and the code records the
measurement rather than forcing the story onto it.


## DOOR-CURTAINS, and what a curtain actually is, 2026-09-01

`maps/blood/mechanism/Vanilla/` is a second tutorial folder -- one
single-mechanism map per file, DOOR-SLIDING, DOOR-SWINGING, DOOR-ROTATING,
DOOR-PORTCULLIS and the rest -- and DOOR-CURTAINS.map alone carries
twenty-five curtain exemplars. It settles two things this project had wrong.

**Markers are state-anchored, and that is now the primitive.** Type 3 is the
position FOR STATE OFF, type 4 the position FOR STATE ON; the mapper draws
the geometry at the ON pose and `state` decides which one it snaps to at
load. There is no from/to journey and no rest marker. Verified to the
coordinate on s3, s6 and s8, and `motion.drawn_pose` confirms every moving
sector in the map -- and both planes of the oracle casket -- is saved at its
ON pose. Consequences:

* a state-0 sector displacing itself by the whole marker separation at load
  is the NORMAL case, not a smell. It is how a curtain drawn open comes up
  closed, and the swept gate now says so only when the displacement and the
  separation DISAGREE;
* the oracle's s2 state=1 is not a mystery and not a leftover: drawn at ON,
  meant to start there;
* our from/to model was wrong in both directions, which is why the zoo's
  curtains ran backwards.

**A curtain is an internal FIN.** s3 is eight walls: the four sides of the
doorway, then the outline runs back along the anchored edge and out into a
narrow tab -- 64 wide of a 256 opening, centred -- whose free END is the one
flagged wall. Drawing it across stretches the tab's two sides. Because every
moved vertex is interior to the sector's own outline, the isolation seam is
PART OF THE SECTOR and nothing outside can deform: `motion_set` returns
exactly `[s]` for s3, s24 and s53. Not a thin separate sector, and not the
pair of opposed caps we built from E1M1 s125 -- that is a different, double
arrangement, and the basic form is one fin.

Also demonstrated there, one sector each and all fixtured: s6 self-closing on
`wait_time`, s8 keyed, s24 the same law drawing along x instead of y, and s21
driving a light on **command 5** -- kCmdLink, which `SetSpriteState` excludes
from its evSend guards precisely because it couples state continuously
instead of firing an edge.

**The rule that follows: consult maps/blood/mechanism FIRST for any mechanism
question, and fixture what you consult.**

## The curtain family, and the rendering law, 2026-09-01

Supervisor assignment P1. The wave-1b curtain deviation was right to refuse;
re-reading the engine around it found that the constructor knew ONE of four
attested dialects, and that the deviation had a second half nobody could see.

### The census, re-run

43 campaign maps, **39** type-614 sectors wearing 146/147: **26 one flagged
wall, 12 two, 1 three** (E2M1 s95, not a dialect anything builds). 27 void
slots, 12 not.

A first pass gave 40 and 13 two-leaf. The extra was
`maps/blood/campaign/ASAVE1.map` -- a SECOND editor autosave still sitting in
the campaign directory after the first was pulled, different content, whose
s125 duplicates E1M1's curtain exactly. Moved to the holding pen. The corpus
is 43 campaign maps again and the census matches.

### Four dialects, not one

| source | leaves | slot | what it teaches |
| --- | --- | --- | --- |
| DOOR-CURTAINS s3 | 1 | void | the tutorial; fabric one-sided, XWALL push |
| DOOR-CURTAINSD s2 | 2 | void | tips carry OPPOSITE flags, so leaves converge |
| DOOR-CURTAINSD s4 | 2 | **pocket** | slot is a real sector; pocket-side wall MASKED with over 1060 |
| E1M1 s125 | 2 | void | a PELMET on a stepped two-sided wall, and a command-5 Link to s124 |

`curtain_spec` takes `leaves` and `slot`; `curtain_dialect` names which one a
built sector is.

### The rendering law, which the project had never asked

`engine.cpp:4938-4940`: a wall's middle band is drawn from `picnum` only when
the wall is ONE-SIDED, and from `overpicnum` only when it is two-sided AND
one-way; otherwise a two-sided wall reaches its middle band only through the
masked path. **So fabric on a two-sided unmasked wall shows on the step bands
and nowhere a body walks.**

The city's curtain was exactly that. It had a ceiling step, so its tile drew
as a valance above head height -- accidentally the E1M1 pelmet -- and nothing
in the walkable band. "Not built as a curtain" also meant "not visible".

### Why carving the fin was wrong twice over

The tree idiom carved the fin's own outline out of the auditorium, so hole and
room were the SAME polygon: all eight walls coincided and all eight paired as
portals. That made the motion drag the house (`DragPoint` walks `nextwall`,
triggers.cpp:817-854; a flagged wall also drags its `point2` when unflagged,
:897-910) AND made the fabric two-sided, hence invisible.

DOOR-CURTAINS s3 does it the other way: the slot is a NOTCH and the space
inside belongs to nobody. So the house gives up the DOORWAY RECT, the fin
stands inside it, and the notch stays solid void. City s37 now reads
`motion_set [37]`, `fabric_visible 3/3`, `closed_texel_scale [2.0, 2.0, 2.0]`.

### Two templates that would have rejected the tutorial

Worth recording because both were nearly shipped.

**"every fabric wall must be visible"** fails DOOR-CURTAINSD s4, which has six
fabric walls and two visible -- the masked pocket pair. The rule is at least
one PER LEAF.

**"closed texel scale 2.0 +/- 0.35"** fails s2 (1.33) and E1M1 (2.83, 4.0).
Measured over 355 fabric walls in the originals: 2.0 is the mode by a
distance (171 of 355) and the attested envelope runs 1.0 to 8.0. The
constructor authors the mode; the gate flags the envelope. The defect it was
written for measured 96.

### The closure, walked the engine's way

`motion.drag_closure` follows `nextwall` as `DragPoint` does, rather than
matching coordinates. On the four originals and the rebuilt city the two
**agree** -- a negative result worth keeping, since the coordinate reading can
over-report and never under-reports.

### The 256 was a mechanism running backwards

Reported first as an imprecision: the two-leaf repeat derived from `span/2`
= 1536 while the swept closed length measured 1280, leaving the pair at texel
1.67 instead of the 2.0 mode. Inside the attested envelope, so every gate
passed it.

It was not an imprecision. **Both leaves were travelling OUTWARD.** Each tip
began 128 inside the doorway and ended 1280 past its own jamb: the pair
rested OPEN and "closing" retracted it out of the opening. The 256 was the
two retractions.

Which leaf carries which flag is not free. DOOR-CURTAINSD s2: span y -3072
(low) to -1024 (high), marker delta +960 toward high, LOW-end tip `0x8000`
AGAINST and HIGH-end tip `0x4000` WITH. Ours had them swapped. Corrected,
both tips close to exactly midspan, `closed_len` is span/2 as the derivation
always assumed, and the texel scale is 2.0 on all six fabric walls.

The lesson is about the gates, not the flags: a number sitting comfortably
inside a tolerance was the only visible trace of a mechanism that worked
backwards. `tests/test_attested_constructs` now asserts the two tips MEET,
and meet at midspan rather than at a jamb.

### The city's state preview

Filed as missing in wave 1b and built: `work/_city_state_preview.py` snaps the
map to each pose and renders the house. OFF shows the fabric drawn across the
proscenium at natural scale; ON shows it gathered. It also states both ends of
the light the Link drives -- stage s24, rx 341, amplitude -24, shade 32 -> 8 --
because `sectorfx.cpp:161-166` scales that by busy at runtime and a static
render cannot show it moving.

## The rendering law, made a reader, 2026-09-01

Supervisor assignment P2, after a first attempt died mid-run (its work was
committed untested as `f8f45fa` and is merged here). P1 had already read
`engine.cpp:4938-4940` correctly and put the conclusion inside
`conformance.fabric_is_visible`. This finishes the job: **one reader owns
the law**, `bloodmap/render_slots.py`, and conformance calls it.

### What the engine draws, transcribed and cited

`classicDrawBunches` (`engine.cpp:4498-...`) and the deferred
`renderDrawMaskedWall` (`:7189`). Vanilla; nothing here is under
NOONE_EXTENSIONS or gModernMap.

| band | tile | condition | lines |
| --- | --- | --- | --- |
| one-sided middle | `picnum` | `nextsector < 0`, ceiling to floor | 4938-4940 |
| two-sided upper | `picnum` | neighbour's ceiling lower at either end; skipped when both ceilings parallaxed | 4688, 4690, 4720 |
| two-sided lower | `picnum`, or the PARTNER's under `cstat&2` | neighbour's floor higher at either end; skipped when both floors parallaxed | 4799, 4801, 4832-4833 |
| masked middle | `over_picnum` | `(cstat&48) == 16` -- masked AND NOT one-way; between `max(ceilings)` and `min(floors)` | 4685-4686, 7217-7218, 7231 |
| one-way middle | `over_picnum` | `cstat&32`, through the white-wall branch, opaque | 4938-4940 |

Blocking (`cstat&1`) and hitscan (`cstat&64`) draw nothing: neither bit is
read in the wall pass, they are clip masks (`clip.cpp:1491`, `build.h:225`,
`:226`). Sky is a SURFACE bit: it removes the two step bands when both
sectors carry it and does nothing to a white or one-way wall. The mirror is
a LOAD-TIME edit -- `mirrors.cpp:466-469` forces `CSTAT_WALL_1WAY` on and
copies 504 into `overpicnum` before anything is drawn -- so the file and the
running level disagree about the flags, and `render_slots.mirror_pass`
applies it. The campaign has 8 mirror walls, and the one red one draws a
`oneway_middle` that reading the file's cstat would miss.

### Two things this reader says that the project had written down wrongly

**E1M1's pelmet is tile 109, not 146.** Walls 1203-1207 (s125, ceiling
-10240) face s122 whose ceiling is -75776. The neighbour's ceiling is
*higher*, so on the curtain's side no upper step exists at all (`:4690`).
The step is on s122's side and its walls 1102-1106 draw their own `picnum`
109; their `over_picnum` 146 is behind cstat 0x6 and never read. **Tile 146
on those five walls is drawn nowhere** -- the "attested valance" is an editor
leftover, and the city curtain's excuse ("accidentally the E1M1 pelmet") was
an excuse for reproducing the same invisibility. Fixtured.

**DOOR-CURTAINSD s4's pocket dialect shows 1060, not 146.** Walls 28, 32, 37
and 41 (cstat 0x51) draw `masked_middle 1060` at the full 24576 opening; the
146 on their `picnum`, and on the flush pocket walls, is never on screen.

### The gate, and the rate that grades it

Three formulations of "a tile authored on a wall is drawn somewhere",
measured over the 43 campaign maps:

```text
per wall            28539 / 107785   26.5%   note      wall-draws-its-own-tile
per sector x tile    4515 /  27104   16.7%   (not registered)
per map x tile         97 /   1979    4.9%   warning   wall-tile-is-drawn-somewhere  <- THE GATE
```

Per wall it is the editor's habit -- Build copies the previous wall's picnum
on insert and nobody clears it -- so a rule there can only ever be a note.
Per map it separates a leftover (drawn elsewhere in the same map) from a lost
material (drawn nowhere): E1M1 loses none, E3M4 loses one.

**Fail first, on a real map.** `blood-city-current.MAP` as committed at
**8c42701**, before P1's rebuild: 6 of 32 authored wall tiles lost, tile 146
on walls 276-278 among them. The test pulls that blob with `git cat-file` so
the anchor outlives the fix. After the rebuild: 146 is gone from the list and
**five tiles remain** -- 68, 93, 203, 1011 (the parlor, church, theatre and
crypt `Material.opening` fields) and 194 (`sewerkit.MOUTH_TILE`), all on
flush unmasked doorway thresholds. The curtain's defect, in four more
districts. Owner queue item 9. The zoo loses zero and now runs the gate as a
LAW rule.

### usage-kinds by rendered slot

`knowledge/blood/design/usage-kinds-v2.json` sits beside v1 with a diff in
`reports/blood-usage-kinds-rendered.{json,md}`; `tools/mine_usage_kinds.py`
is the mine. Tile 146, the test case: v1 said `wall_two_sided 129`; rendered
that is **71 lower steps, 3 upper steps, 55 drawn nowhere, 0 masked
middles** (173 + 71 + 3 + 55 = 302 = v1's 173 + 129, exactly). The mask law
restated by band names the same two tiles the owner already ruled on -- 142
and 2464 -- out of 79982 opaque band draws. 14 tiles v1 called "attested on
walls" have no rendered wall slot at all.

`usage_kinds.unattested_uses` judges walls by band when v2 is present, which
is how the city's 12 tile-202 lower steps became visible to the attested-slot
warning; surfaces and sprites are unchanged.

### What is still unproven

* Occlusion, room-over-room and the `yax` paths are not modelled: a band that
  draws is a band the engine would rasterise if nothing stood in front of it.
* Heights are read in the SAVED pose. A door saved closed whose material only
  draws when open is reported as it is saved.
* Slope endpoints use an exact integer square root where the engine uses its
  `nsqrtasm` table, so a sloped z can differ by a unit; no step decision in
  any campaign map turned on that unit, but that is a check, not a proof.
* Polymost (`polymost.cpp:6528`) branches on the same
  `(nextsectnum < 0) || (wal->cstat&32)`; it was not transcribed line by line.

## The walk fixes, 2026-09-01

The owner walked the rebuilt zoo. Casket works, lift works, curtains open the
right way. Three mechanisms were still wrong and one was merely ugly, and all
four were diagnosed against the ISOLATED tutorials rather than embedded
campaign cases -- the owner's rule, and it paid: a tutorial shows one
mechanism with nothing else in the way.

**A crack is a THING, not a switch.** `#SPR408.MAP` spr0 is the record: type
408, tile 1127, cstat 722, on the THING statnum 4, transmitting on Impact --
damage landing -- and not on Vector, which is a hitscan crossing. The zoo had
given it a switch's wiring, so it never fired. It had also omitted the part
that makes a breach read as one: a CASCADE of three type-459 exploders (tile
908, statnum 11) on the crack's own channel, staggered 2/1/1, plus the
type-600 sectors that collapse on the same channel. Without them a wall does
not blow, it silently stops existing. `motion.crack_thing`, `thing_transmitter`
and `exploder` build the whole record, and `thing_faults` makes a type-408
without the thing statnum or without impact triggering a constructor-level
error.

ENVIRONMENT-EXPLODEWALL is the second oracle and it DIFFERS in four fields:
cstat 464 rather than 722, no Once on the crack, exploders with no
`trigger_on` and a wider 0/3/6 stagger. The owner's queue also cites E1M4
sprite 373 at cstat 209. Three sources, three cstats -- the isolated single is
preferred, and the difference is fixtured so it stays a known fact.

**A key pickup must wear the key it grants.** Mined over the 43 campaign maps:
95 key pickups, six item types, and every one wears `2452 + type`. No map ever
dresses a key as another key. The zoo granted the moon key (type 105) and
placed the SKULL key's tile (2552): the lock opened and the thing on the floor
was the wrong key. `keys.world_picnum` and `keys.pickup` derive art and type
together so they cannot drift, and `keys.pickup_art_faults` is the
readability check.

**A secret is credited with a NUMBER.** `OTHERSECTORSFX-SECRETS.map`:
`kChannelSecretFound` is 2 and `kCmdNumberic` is 64, so command 64 means
secret 0 and 65 means secret 1. The zoo sent command 1 -- kCmdOn, a verb --
and nothing declared the level total on channel 1, which every campaign map
checked does. `motion.secret_credit`, `secret_total` and `secret_faults`.

**A curtain is calibrated for its CLOSED span.** Measured across the whole
DOOR-* family, natural texel scale is `length / x_repeat == 2 * tile_width`
-- 3440 walls sit exactly there. DOOR-CURTAINS s3 and s53 carry x_repeat 16
over a 1024 CLOSED span on tile 146 (32 wide), which is natural to the unit;
s24 is the one exemplar at twice that. Because the geometry is saved at the
ON pose, sizing the fabric to what the file shows is sizing it to the gathered
bundle: ours came out at texel scale 96, forty-eight times natural. Now the
repeat is computed from the OFF span, so the drape is natural shut and
squashes to 0.08 open, which is what cloth does. Also: only the three FABRIC
walls wear the fabric now -- the tutorial's s3 is eight walls and exactly
three carry tile 146, and we had put curtain on the door frame.

### Two bugs the texture work turned up

**`off_pose` was translating the whole sector.** It subtracted the marker
delta from every point instead of moving only the motion set, which is right
only when the whole sector travels. A fin moved bodily instead of stretching,
so its closed span measured the same as its drawn one and the fabric could
not be calibrated at all. It delegates to the sweep now.

**A sweep starts at the REST pose, not at busy 0.** `blood_sweep` runs from
where the sector rests outwards, so `frames[0]` is busy 65536 for a state-1
sector. Everything reading `frames[0]` as "OFF" printed such a mechanism
backwards, and the zoo's two casket lids are exactly that. `motion_sim.
blood_poses` returns (OFF, ON) whatever it rests at, and the state preview and
state check now use it.

### The mask law's scope has a reason now

The owner ruled on both tiles. 142 is a skull-shaped FIREPLACE maskwall --
not curtain family despite the 140s run -- and its two-sided uses are the
legitimate see-through mouth, which is exactly the masked-overlay case the law
permits. 2464 is an ejected shell casing and its two slots are accidents. The
implementation does not change; the reasoning does, from "23 slots is too few
to name a family" to a ruling. The rule text, the usage-kinds docstring and
`tests/test_usage_laws.py` carry it.

That ruling immediately broke something else, which is the useful part: the
new strong anchors put 142 into the tile museum's strong-binding set, and the
museum paints niche walls without distinguishing one-sided from two-sided --
so the exhibit that teaches the transparency law shipped three violations of
it. A tile attested only on two-sided walls now goes on the niche's OPENING as
a `maskwall_panel`, which is the only two-sided wall a niche has.

## The curriculum, mined, 2026-09-01

`maps/blood/mechanism/` is a taught course, and it ships with its own
981-page manual (`xmapedit.pdf`, XMAPEDIT 3rd ed. 2025). 136 maps mined,
1291 constructs read, **17 laws** with detectors. `Modern/` is deliberately
unmined: it is the NBlood-extension dialect and mining it as vanilla would
put extension behaviour into base-engine laws. It is a queued phase.

**Six of the seventeen laws CORRECT this project** rather than extend it, and
three of those correct work from the run immediately before.

Deliverables, so the retrieval surface is findable:

```text
knowledge/blood/design/mechanism-curriculum-v1.json  facts + laws + evidence
reports/blood-mechanism-curriculum.md                what it found, readably
reports/zoo-state-check.json                         every mechanism measured
                                                     in BOTH states
reports/owner-prescreen.html                         the phone state sheet
bloodmap/curriculum.py, curriculum_laws.py           the mine and the laws
bloodmap/construct.py                                functional ownership
bloodmap/arbiter.py                                  single-slot arbitration
tests/test_curriculum.py                             tier-1 fixtures, incl.
                                                     BADROR as a NEGATIVE
tests/test_ownership_and_arbitration.py              ownership + the arbiter
```

**The pose is not a convention, it is what the loader does.** `trInit`
translates a moving sector by -65536 of the marker delta, records THAT as the
base with `setBaseWallSect`, and only then applies the sector's own busy
(triggers.cpp:2224-2245). So the outline saved in a map is the pose at busy
65536 -- state ON -- always, whatever the author believed they were drawing,
and the OFF pose is the drawn outline minus the delta. Confirmed to the unit
on DOOR-CURTAINS s3. `motion.off_pose` computes it and `motion.drawn_pose` is
deprecated to a constant.

**A slide reads only the difference between its markers.** `TranslateSector`
moves each base point by `interpolate(m1, m2, busy) - m1`, so the pair's
absolute position on the grid is free -- 196 of the curriculum's mechanisms
place the pair at the two poses and 52 park it elsewhere, and both drive the
sector identically. The old `drawn_pose` compared a moved vertex against the
markers' absolute coordinates and called the answer a pose; for the 52 it was
measuring noise. It is now `marker_convention`, which reports which
convention is in use and claims nothing more. A ROTATE is different and must
not be read the same way: its single marker is the PIVOT, absolute position
mattering, and its `ang` is the ON angle interpolated from 0.

**The button is the surface you touch.** The tutorials do not wire a shove
with the sector's `trigger_wall_push`. They put an XWALL on each face you are
meant to push -- type 0 Decoration, tx on the mechanism's channel, Toggle,
Trigger On Push -- and the sector merely RECEIVES (manual p.239;
DOOR-CURTAINS s3 walls 38/39/40, whose sector's entire XSECTOR is rx 100, two
busy times and the marker pair). A commit of mine claimed s3 carries
`trigger_wall_push`. It does not. `motion.wall_button` and
`PlanarLayout.wire_wall` build it the tutorial's way, and the payoff is
twofold: the button is the cloth rather than the whole doorway, and the
mechanism's one `tx` slot stays free for its downstream effects.

**The edge rule binds switches, not senders.** `SetSpriteState` gates
`evSend` on triggerOn/triggerOff, so a toggle, one-way or padlock switch with
neither flag sends nothing -- but a kSwitchCombo sends from its own arm of
`OperateSprite`, `if (command == kCmdLink && txID > 0)`, outside those guards,
and kGenTrigger relays and sector-sound sprites transmit by other paths
entirely. `motion.transmitter` refused all of them, which would have refused
the tutorial's own relay. The curriculum's six edgeless switches are all
combination switches on command 5, exactly as the source predicts.

**Motion crossing a storage boundary is the NORM.** 94 of the curriculum's
swept mechanisms deform more than their own sector, because `dragpoint` moves
a vertex for every wall incident on it. We treated that as pathology to be
engineered away. The isolation FIN -- every moved vertex interior to the
sector's own outline -- is a deliberate construction for when a room must not
be disturbed, and the same map slides other curtains straight into their
neighbours where it does not matter. What matters is not whether a motion
crosses a boundary but whether the construct DECLARED it, which is what
`construct.check_declared_motion` now asks.

Two more worth keeping. A **path sector fails silently**: `InitPath` prints a
system message and returns when no marker matches its `data`, leaving a
typed, wired, motionless sector. And **z motion is state-anchored in exactly
the same shape as the horizontal** -- `off_floor_z`/`on_floor_z` and the
ceiling's own pair, chosen by the same `state` -- which is why
`mechanism.lift` needs no markers at all.

### What a broken ROR looks like

STACKS3DSPACES-BADROR is shipped as a negative example and a reading that
passes it is wrong. The manual's rules (p.364-365) are congruent halves, 504
on both facing planes, markers pegged to those planes and not floating,
`data_1` pairing the links, never two links visible at once, and no
over-complicated link sector. BADROR passes the first four. What separates it
is the last: its two link sectors are the only CONCAVE ones among the working
examples, ten-wall outer loops with the alcoves cut into the boundary, where
ROR1 and ROR2 keep four- and six-wall convex outer loops and put their
complexity in inner loops.

That check is a RISK, not a rule, and it is reported as one: `STACKS3DSPACES`
itself has two concave link sectors and ships as a working example. The
honest statement is that concavity separates BADROR from the two maps built
to demonstrate correctness, and not from everything.

### A gate that could not fail, removed

`swept_state` used to report a mechanism sitting away from its drawn outline
at load. Under the engine law that is not measurable: the base is DERIVED
from the markers, so a state-0 sector displaces by the marker separation by
construction and the two can never disagree. The test that was meant to catch
a disagreement had to move a marker to provoke one, which moved the
separation with it. It is replaced by a **clearance** check that does fail:
at every step of the travel, does the moving outline properly cross a wall
belonging to a sector OUTSIDE the motion set? That is a mechanism sweeping
through standing geometry, the fault the rotors were always suspected of and
nothing ever checked.

## The swept gate learned the closure, 2026-09-01

Supervisor assignment P3. The gate swept the mover's own polygon and treated
every neighbour as static. The engine does neither, and the curriculum's own
law says so.

### What the engine does

`triggers.cpp:817-854` `DragPoint` sets a vertex for every wall that shares it,
found by walking `nextwall`: forward through each partner's `point2`, and --
this is the half both of our readers were missing -- when that walk meets a
one-sided wall it restarts at the argument and goes the other way through
`lastwall().nextwall` (`engine.cpp:13227`). `:897-910` a 16384 wall drags its
`point2`'s vertex too when that wall carries no flag; `:912-926` the same in
reverse for 32768. The `gModernMap` split in `TranslateSector` (`:874-878`) is
about reverse-flagged SPRITES, so the wall path is the vanilla path.

### One closure, not two

`motion.drag_closure` and a second walk inside `motion_sim` were both live
after the merge, and they were not the same function: the short one walked the
ring forward only, so it under-reported precisely the fin-beside-a-void-slot
case this project builds most. `motion_sim` owns the walk (it needs the
per-driver sign and the loops the chains land in, for the sweep);
`motion.drag_closure` delegates and keeps its published shape.
`motion_sim` also stops re-declaring `MOVES_WITH` / `MOVES_AGAINST` /
`MOVES_EVERY_WALL` / `wall_owners` and imports them from `motion`.

### The gate

`blood_sweep(..., by_loop=True)` returns frames for every loop the closure
touches, keyed `(sector, loop)`; `sweep_health` takes that mapping and
`closure_health` is the fuller check -- inversion against the DRAWN winding
(not against frame 0, which would call the drawn pose the inverted one),
self-intersection, and crossing a wall the motion does not move. The
fail-first fixture is a `PlanarLayout` slide-marked strip whose flagged wall is
shared with a thin sector that is inside out at busy 0: the mover's own polygon
is healthy at every pose, and the previous gate passed it. That is kept as a
test, not a claim (`test_the_mover_only_sweep_is_blind_to_the_neighbour`).

Wired into `projects/pattern-zoo/sweep.py` (a conformance row) and
`projects/blood-city/level/build_skeleton.py` (refuses to write the map).

### Two corrections the census forced

**An assembly cannot be judged one mechanism at a time.** The first run called
10 campaign neighbours inverted and 72 self-crossing. Most were rotor rings and
boats -- E1M4 s321-s329 around the hub s352, E3M2's fifteen sectors around s16
-- where several mechanisms drag the same loop and it is whole only when all of
them have travelled. `co_driven_walls` finds those per WALL; such loops are a
note, never a problem. 215 campaign and 132 curriculum loops.

**A graze is not a fold.** A 617 rotor hinges on a vertex OF the room it turns
in, so its leaf tip crosses that room's wall a hair past the corner at small
angles. `crossing_depth` measures how far two crossing segments reach into each
other; the campaign's 27 folding neighbour loops split at 13.69 vs 19.98 units,
and `SWEEP_GRAZE = 16.0` sits in the gap -- also the right order for the
model's own rounded marker angle (~1.6 units at a 1024 radius).

The two-leaf finding landed while this was being written and it is the right
warning: a number inside a widened envelope was the only trace of a mechanism
running backwards. So this tolerance accounts for itself. Every loop carries
`grazing_steps`, every crossing its `depth` and a `graze` flag,
`closure_health` returns `graze_tolerance` / `grazing_loops` /
`grazing_crossings`, and the census prints them beside the findings (2
loop-poses and 38 crossings in the course, 90 and 449 in the campaign). Set it
to 0 and every graze becomes a fold; a test asserts that flip still happens.

### Numbers

429 swept mechanisms in the vanilla course (138 maps), 648 in the campaign (43).
Isolated -- the fin technique -- 109 and 200: one in four. Deform a neighbour
199 and 412. After both corrections: **zero** inverting or self-crossing
neighbours in the whole taught course, against 1 and 18 in the campaign, and 2
crossings against 89. The tutorials are built to a precision the shipped levels
are not.

The one campaign inversion is `E4M2 s201` (615) dragging `s200`, inside out at
11 of 17 poses including the pose the level loads in. It is the only instance
of the supervisor's inside-out case (b), and it is a candidate, not a verdict
-- nobody has seen it in the engine. Queued for the owner.

Full census: `reports/blood-mechanism-drag-closure.json` (215 KB: summaries and
the mechanisms that have something to say; the 803 clean ones are counted, not
listed) and a section in `reports/blood-mechanism-curriculum.md`.

### Still unproven

- Whether the 18 folding campaign neighbours are visible in the engine. The
  model rounds the marker angle where the engine rounds coordinates.
- `cuts standing geometry` fires on 89 of 648 campaign mechanisms and 2 of 429
  curriculum ones. At a 14% campaign rate it is not a build-blocking rule on
  its own; a 617 leaf swinging through the room it opens into is the dominant
  shape and may be legitimate.
- The 69 `coincident but not chained` vertices are read as unwelded map
  defects on the engine's own logic, but none has been observed tearing.

## Round-trip closure moved to the constructor, 2026-09-01

Supervisor assignment P7. Phase 11 item 3 -- *every constructor's test builds,
reads back through effects/conditional, and asserts the parse equals the
grammar sentence the constructor claims* -- was true of the pattern zoo only,
because the gates lived in `projects/pattern-zoo/sweep.py` and `selfread.py`.
The city built a curtain that failed conformance and nothing in its build said
so until P1 added a call by hand.

### One function, and a sentence that is a documented dict

`bloodmap/readback.py`. `read_back(disk, sentences)` takes a built map and the
sentences it was built from and returns structural equality or typed
`Difference` records -- facet, wanted, found, and WHICH READER found it, so a
diff can be re-run rather than believed. Seven readers behind one call:
`effects.read_mechanism` and `payload`, `conditional.route_edges`,
`motion_sim.drag_closure` and `closure_health`, `conformance.measure_*`,
`render_slots`, and the state-pair measurement.

`sentence()` REFUSES an unknown key. A misspelled claim that is silently
dropped is a gate that measures nothing, which is the failure this module
exists for; and a claim the source never made is never a difference, or the
gate starts inventing intent. Facets no reader could measure go in
`unmeasured` and are printed, never swallowed.

The typed `MechanismDecl` (Phase 13) is deliberately NOT built. The dict's keys
are what the comparison actually needed, which is the right shape to grow the
typed layer from.

**The state pair, in memory.** `readback.state_pair` is the measurement behind
`reports/zoo-state-check.json`, whose generator (`work/_state_check.py`, commit
929cdc1) wrote out two whole snapped maps and read them both. It needs no
files: `motion_sim.blood_poses` already transcribes `TranslateSector` and knows
which frame is OFF for a sector that rests open, and the z pair is in the
XSECTOR. Four measures -- plan area, headroom, turn, marker travel -- and
`changes` False is the generator's "NOTHING MEASURABLE CHANGED", with the
whole-circle rotator exempt because ending where it began IS the mechanism.

### The declared side is DERIVED, not written twice

`sentences_from_layout(compiled, layout=)` reads the sentences off the source
that built the map: each region's sector type, the XSECTOR its constructor
asked for, and the payload it declared through `declare_motion`. A second
hand-written manifest drifts from the source it describes, and then the gate
compares two stale things.

A curtain is identified by WHAT IT WEARS, not by its region id -- the lesson
the zoo's sweep paid for, when routing the curtain check on a payload SHAPE
stopped running the moment the constructor was corrected and the zoo reported
13/13 conforming because the curtain was never asked.

Worth running on the FINAL disk even though `compile` preflights the motion
set: the city's facade, lintel and wall-sprite passes edit the compiled level
AFTER `compile` returns, and the gate inside it saw the geometry before all of
that.

### The gate fails first, on the real defect

`git show 8c42701:projects/blood-city/level/blood-city-current.MAP` -- the city
as committed before P1's rebuild -- read back against the sentence its
constructor claimed:

```text
PRE-P1   members: wanted [37], found [23, 37]
             wall 209 of sector 23 shares the moved vertex (25472, 7072)
             wall 210 of sector 23 shares the moved vertex (25472, 7008)
         visibility.146.drawn: wanted 3, found 0
         visibility.146.walkable_band: wanted 1, found 0
         conformance: fabric is visible -- 0 of 1 per leaf
CURRENT  all agree; motion_set [37], 146 authored 3 / drawn 3 / walkable 3
```

Both halves of the defect, and the second is the one nobody could see. Two more
fail-first fixtures are mis-wired copies of current constructs: a Link receiver
with `shade_always` set, which `sectorfx.cpp:161-166` makes deaf to busy, and a
door with an rx that nothing transmits on.

### Coverage, and the rule that keeps it

`tests/test_readback.py`: 35 tests. Ten public constructors build in a minimal
`PlanarLayout`, read back and assert equality; the two blood-city places from
the TREE (`turnstiles.pair`/`populate`, `curtains.hang`/`furnish`) do the same
in a minimal levelprog program, because the level is authored in two dialects
and a flat-side test proves nothing about the tree side.

`ReadBackRegistry` fails for any public constructor of `mechanism`, `doors`,
`glass`, `aperture` or `street` with neither a read-back test nor a written
reason -- the shape of `tests/test_pattern_zoo.ConformanceTest`. 45 public
callables: 10 covered, 35 skipped with a reason that says what the function
does INSTEAD of building. Three of those skips are PENDING rather than
excused -- `aperture.framed_door`, `frame_z_doors` and `facade_run` all need
ART tile extents to choose a reveal, and this suite has no corpus-free source
for them. Named so the gap is countable.

Both build scripts now call `read_back` over `sentences_from_layout` and refuse
the build on a difference: `projects/pattern-zoo/build_zoo.py` after `glaze`
edits compiled walls, `projects/blood-city/level/build_skeleton.py` after the
swept gate and after every post-compile pass.

### Two defects the gate found in existing readers

**`motion.rotate_marker` read the wrong sprite for a sector with no marker.**
`marker_0` is -1 for "no marker" and the guard checked only the top end, so
Python indexed from the END: a lift -- a z motion, which carries no marker --
read the map's LAST sprite, and would have reported a pivot and a turn if that
sprite happened to be a kMarkerAxis. With no sprites at all it raised. Found by
`state_pair` measuring a lift.

**The interaction reading told a player to find a switch that does not exist.**
`observe_motion_sector` collected XWALLs from PORTAL walls only, and Blood's
canonical doors put the push on the sector's own leaf, which is routinely
one-sided -- `#SLDOOR`, `#SWDOOR`, E1M1 s4, and this project's own
`mechanism.curtain`. Reproduced on a map built here with no corpus: our curtain
read `remote_rx`, its three push XWALLs sitting on `next -1` walls.

The engine: `player.cpp:1637-1641` reads the hit wall's own XWALL and operates
it when `triggerPush` is set, without consulting `nextsector` -- the
`nextsector >= 0` branch under it is the FALLBACK to the neighbour's
`Wallpush`. `trTriggerWall` (`triggers.cpp:1865-1884`) then reaches
`OperateWall` (`:692`), whose default branch calls `SetWallState`
(`:112-128`), which sends the wall's own `txID` on the state edge.

`observe_motion_sector` now reports `own_xwalls` and routes on it. Over the 43
campaign maps, 2027 mechanisms, **171 readings change**: 168 `remote_rx` ->
`wall_push`, and 3 lose a `+remote` suffix that was never a second route --
that channel is how a wall reaches a sector at all. Owner queue item 12; the
mined door precedents under `knowledge/` are stale by 8.4% and were not
re-mined here.

### The three acceptance fixtures

**The wall-level interaction route: PASSES.** `expectedFailure` removed, the
assertion unchanged. A second fixture asserts the reading it needed -- the push
XWALLs are on walls s4 owns and transmit on the channel it receives.

**The light link as a facet: still fails, and the missing reader is named.**
Every field is legible one at a time -- s125 `tx_id 126, command 5`; s124
`rx_id 126, amplitude -8, shade_always 0, shade_floor 1, shade_walls 1`.
Nothing in the stack reads a SECTOR's `command` as a verb at all, so
`read_mechanism` returns eight keys and none is a transmitter-side facet. That
is prompt P8's deliverable and was left to it rather than half-built here.

**The stack-linked casket: still fails, and it is blocked on a LAYER.**
`reachability.link_pairs` already reports `{link 10, sectors [28, 30], sprites
[47, 46]}`; `motion.stack_pairs` reports nothing, because it looks for the
floor-picnum-504 see-through marking this pair does not carry. What is missing
is composition: nothing joins a per-sector record to the mechanism across its
ROR plane, and four sectors in two planes cannot be said by a per-sector record
at all. Adding a `stack_partner` key to make one test pass would put the
composition in the wrong place; it belongs in MechanismDecl.

### The twelve rendering errors, restated as what they are

`readback.lost_tiles_as_differences` turns the `wall-tile-is-drawn-somewhere`
violations into `Difference` records, and the city build prints them as
`READ-BACK DIFF (non-blocking, owner-queue item 9)` rather than as `LOST` lines
inside a rule count. They are not a style warning: the map claims a material
and the engine draws something else, which is exactly the diff the constructors
should own. Left non-blocking only because five flush doorway thresholds are
still with the owner; the moment that is decided the list belongs above the
build's `return 1`, and the comment there says so.

### What is unproven

* **Neither build was run end to end.** `reference/blood` holds no ART in this
  environment and `PlanarLayout` refuses a seated placement without a tile
  extent, so `build_zoo.py` and `build_skeleton.py` both stop before they
  reach the new gate. The gate itself is exercised: 35 tests build and read
  back through the same call, both tree placers included, and the two SHIPPED
  maps were read back against the claims every mover makes by construction --
  20 mechanisms in `pattern-zoo.MAP` and 14 in `blood-city-current.MAP`, all
  agreeing. What is unproven is the wiring inside the two scripts.
* The `members` claim is only as good as `declare_motion`. A constructor that
  declares nothing gets no members check, and several do not declare.
* `state_pair` reads the z pair the XSECTOR states rather than simulating the
  travel, so a door whose endpoints are right and whose busy times are zero
  measures as changing. `trProcessBusy` is not modelled here.
* The conformance template routing is by construct NAME, and the name comes
  from the sector type plus the fabric tile. A curtain that wears something
  else is measured as a plain marked slide.

## The Link, read as a verb, 2026-09-02

Supervisor assignment P8. The reader could not say "the room light follows the
curtain" although three attested pairs and the city's own are wired for it.
P7 had measured exactly why and left it: every field is legible one at a time
-- E1M1 s125 `tx_id 126, command 5`; s124 `rx_id 126, amplitude -8,
shade_always 0` -- and **nothing in the stack read a sector's `command` as a
verb at all**.

### What changed

`effects.transmission(disk, sector_id)` is the reader, and `read_mechanism`
carries it as a fifth plane beside primitive / carried / embedding / style.
The four planes describe one sector. This one cannot: what a mechanism drives
is not a property of the mechanism or of the thing it drives, it is a property
of the pair, and the only field holding it is `command`.

It lives in `effects.py` rather than `conditional.py` because `conditional`
imports `effects` and that arrow points one way; `receiver_index` -- the
mirror of `conditional.transmitters` -- lives there for the same reason.

The record carries two keys deliberately. `drives` is the flat list of driven
sector ids, which is what a caller comparing two readings wants;
`transmission` beside it is the whole facet -- channel, verb, every listener
by kind, and per listener what the sender's `busy` does to it.

### Evidence

Engine, all vanilla and each line read before it was cited:

* The send is from the **busy proc**, once per game tick for the whole
  travel, carrying the sender's `busy`: `VSpriteBusy :1247`, `VDoorBusy
  :1346`, `HDoorBusy :1374`, `RDoorBusy :1401`, `StepRotateBusy :1434`,
  `GenSectorBusy :1454`. The seventh copy, `VCrushBusy :1198`, is
  **unreachable in vanilla** -- `BUSYID_0` is referenced from
  `nnexts.cpp:4222` alone, under `NOONE_EXTENSIONS`. The supervisor brief
  listed six; there are seven, and one of them does not count.
* `SetSectorState` sends no edge for such a sector: `:140` and `:152` both
  open with `command != kCmdLink`.
* `LinkSector` (`:1776-1801`) decides by the RECEIVER's type. Six types are
  handed to their own busy proc (`:1781-1794`) and mirror the travel;
  everything else takes the default (`:1795-1799`), which copies the busy and
  calls `SetSectorState` only at a whole state.
* `LinkSprite` (`:1803-1831`) and `LinkWall` (`:1833-1839`) do the same for
  the other two kinds; `kSwitchCombo` is the one sprite that reads a Link as
  DATA, copying the sender's `data1` (`:1806-1821`).
* `sectorfx.cpp:162` is the lighting gate (`shadeAlways || busy`), `:166-168`
  scales the amplitude by busy, `:171` evaluates the wave with
  `phase*8 + freq*totalclock`, `:171-199` applies the result to the faces the
  three `shade_*` flags select.
* **`InitSectorFX:363`** is the fact the brief did not have: a sector enters
  `shadeList` only `if (pXSector->amplitude)`. With amplitude 0 the sector is
  never visited and every other shade field on it is inert. That is a harder
  test than "no wave", and it is the correct one.
* `trMessageSector:1916` / `trMessageWall:1937` / `trMessageSprite:1962` drop
  every command but the two lock verbs on a `locked` receiver.

Campaign, 43 maps, 2023 mechanisms, 752 transmitting sectors
(`reports/blood-link-census.json`, section in
`reports/blood-conditional-topology.md`):

* **146 send a Link (19.4% of transmitters)**, reaching 269 receivers --
  1.84 each.
* **268 sectors (99.6%), one sprite (0.4%), no walls.**
* **175 dim (65.1%), 93 mirror (34.6%), 1 flips only at a whole state.** The
  Link is a lighting verb about twice as often as a coupling verb.
* Senders: 600 (65), 617 (44), 614 (28), 615 (5), 616 (4). No 602, 613 or 612
  -- which is where the engine stops being symmetric.
* **152 of the 175 dimmers (86.9%) carry `shade_wave` 0**, which is not a
  missing field: `GetWaveValue` case 0 returns the amplitude unchanged
  (`:80-81`), so the shade IS the scaled amplitude and tracks the travel
  linearly. This is the campaign's canonical dimmer.

### Counterexamples

* **The asymmetry the model had to grow to hold.** 613 SENDS a Link
  (`StepRotateBusy:1434`) and is absent from `LinkSector`'s switch: a stepped
  rotator can drive a mirror and cannot be one. 612 is the reverse -- `PathBusy`
  (`:1465-1494`) is the one busy proc with no Link clause, so a `command 5`
  path sector never sends. 604 runs no busy proc at all.
* **A `command 5` sector with both busy times zero transmits NOTHING.**
  `OperateSector:1717-1737` reaches `GenSectorBusy` only when there is a busy
  time; otherwise it calls `SetSectorState`, whose sends `:140/:152` refuse
  for a Link. No campaign map does this; the fixture is a mutated copy.
* **One campaign receiver of 269 cannot answer: E4M2 s33 -> s200**,
  `shade_always 1` with `shade_wave 7`. Its three fellow listeners on channel
  103 all respond. Recorded as an observation, not a bug: a light meant to
  flicker regardless is a legitimate thing to want and this reading cannot
  tell that from a slip.
* **Eight Link senders (5.5%) reach nobody** -- E1M3 s307, E1M4 s218, E1M5
  s197, E1M8 s109, E2M5 s80, E2M5 s673, E3M2 s45, E3M6 s35 -- checked against
  sectors, walls and sprites alike.
* **126 of 146 (86.3%) carry edge flags the engine cannot consult.** Harmless.
  Recorded so no reader reports an edge these mechanisms never report.

### The gate, and what it failed on first

`test_a_receiver_with_shade_always_cannot_follow` takes DOOR-CURTAINS s21 ->
s20 and sets one bit on the receiver. With the `shade_always` clause removed
from `_sector_receiver` the reading still says `follows [20]` and the test
fails on `[20] != []`; with it, `cannot_respond` names s20 and quotes
`sectorfx.cpp:166`. Every field on both sectors stays individually valid, so
nothing else in the stack can tell. Four more mutated fixtures cover amplitude
0, a locked receiver, an empty channel and the zero-busy-time sender.

The acceptance fixture, `test_the_light_link_is_read_as_a_facet_of_the_
mechanism`, passes with **its assertion unchanged**; `expectedFailure`
removed.

**And the suite log found a second copy of it.** The same gap had been
recorded twice -- once on E1M1 in `test_attested_constructs` and once on the
tutorial map as `test_door_curtains.WiringExemplarTest.test_the_light_link_is_
read_as_a_facet` -- and the first full run came back `FAILED (unexpected
successes=1)` with no ERROR or FAIL line anywhere in it. Closing one closed
both, which nobody knew, because nothing in the repo had ever asked how many
fixtures were waiting on the same missing reader. That is the supervisor's
"never pipe the suite through tail" rule earning its keep for the second time
in two days: the only trace was one line above the `Ran` line.

### Regression tests

`tests/test_attested_constructs.TheLinkIsAVerbTest`, 10 tests, plus the two
that close the tutorial twin in `tests/test_door_curtains`: the two
tutorial pairs (DOOR-CURTAINS s21 -> s20, DOOR-CURTAINSD s18 -> s17), E1M1's
carnival rotator s50 driving four receivers of two kinds on one channel
(s51 mirrors, s44/s45/s55 dim), the five fail-first mutations, the 613
asymmetry and wave 0. Plus two new assertions on `CurtainTest` for the E1M1
pair's shade numbers and its dead edge flags.

### The city

`projects/blood-city/level/build_skeleton.py` ran end to end -- P7 could not
run it, because `reference/blood` held no ART; it does now, and the build is
**byte-identical** to the committed map, 259 sectors / 1694 walls / 430
sprites, `read-back: 44 sentence(s), all agree`. That closes P7's first
unproven item as well as this one.

s37 -> s24 reads `follow me`, `continuous`, sending from `HDoorBusy
(triggers.cpp:1374)`, `follows [24]`, no faults. The stage light at each end
of the curtain's travel:

```text
OFF (busy 0)      floor 32   ceiling 34   walls 32
ON  (busy 65536)  floor  8   ceiling 10   walls  8      delta -24, wave 0
```

### What remains unknown

* **The clock is not simulated.** `GetWaveValue`'s phase advances with
  `freq*totalclock` (`:170-171`), so a receiver with a non-zero
  `shade_frequency` has a shade RANGE, not a value. `wave_value` transcribes
  waves 0-4 exactly; 5 and 11 need Build's `Sin`/`Cos` tables and 6-10 index
  the four flicker tables and the strobe table, none transcribed here. **23 of
  269 receivers (8.6%) report `unmeasurable` with the reason** rather than a
  number nobody checked.
* `trProcessBusy` is still not modelled (P7 said the same of `state_pair`), so
  "at busy 65536" is the end of travel and not a time.
* The facet reads a SECTOR's transmission. A wall or sprite that transmits is
  a receiver here and never a sender; `conditional.transmitters` still owns
  that side.
* Nothing yet declares `drives` as a read-back claim, so a constructor cannot
  yet be held to the light it says it drives. That is the natural next step
  and it needs a `sentence()` key.

### Next highest-value experiment

Give `readback.sentence()` a `drives` key so `curtains.link_stage_light`'s
claim is checked against the built map rather than trusted -- the arbiter
already decides the tx slot and nothing verifies the decision survived. After
that, the receiver-side twin of P7's 171 changed interaction readings: how
many campaign mechanisms have a `drives` facet that the design-role reading
should be consulting and is not.

## Texture frames: where a material is, 2026-09-02

Supervisor assignment P11, from the owner walk. Adjacent walls wearing the
same tile did not continue the texture -- at vertices, on facades, in the
arcades, across doorway and window cuts. The supervisor had measured why: the
representation decides texture fields PER WALL, so nothing in it can state
"this material is projected onto this run from this origin at this scale".

### The law, read from the editor rather than re-derived

`AlignWalls` (`xmapedit/src_blood/xmpmaped.cpp:3024-3050`) is the whole wall
half in four lines: a wall consumes exactly `x_repeat * 8` texels, panning is
a texel offset modulo the tile width, `y_repeat` is carried along a run, and
`y_panning` shifts by `((z1-z0) * y_repeat) / (tilesizy*8)`. `GetWallZPeg`
(`:2991-3022`) says where a wall hangs from -- and its two-sided branch is two
`if`s rather than an if/else, so a wall with a top step AND a bottom step ends
up pegged to the bottom one. `ED32_AutoAlignWalls` (`:3070-3145`) is the
traversal, and the traversal is why a run is not a sector loop: at
`:3142-3143` it steps `wall[wall[w1].nextwall].point2`, around the vertex into
the neighbouring sector. That is how a facade continues past a doorway.

**Three corrections to the brief, all from reading the lines.**

* **The `>` key is not the recursive one.** `maproc.cpp:1146-1151` sets flag
  `0x01` when shift is NOT held, so plain `.` aligns a whole run and `>`
  (shift+period) aligns exactly one neighbour. `,` adds `0x10` (walk
  `lastwall`), ctrl adds `0x04` (carry the scale), and `0x20` is automatic
  when the cursor sits on a bottom-swapped band. `AutoAlignWalls`
  (`:3205-3216`) then runs the recursion **twice** with a fresh visited list,
  so a correct map is a fixed point of two passes.
* **Lengths are `approxDist`** (`common_game.h:1004-1012`), Build's octagonal
  approximation, not the Euclidean length. Every diagonal wall in the map is
  measured with the wrong number otherwise.
* **A floor texel is sixteen world units**, and the expanded bit
  (`floorstat 8`) makes it eight, not thirty-two: `globalxshift = 8 - log2
  tilesizx` (`engine.cpp:2797`), `globalxpanning <<= globalxshift + 6`
  (`:2880`), and the bit *increments* the shift (`:2799`). So a 64-wide tile
  covers 1024 world units, which is why a 1024 crate on the 1024 grid wears a
  whole tile and one anywhere else wears a cut one.

### What changed

`bloodmap/texture_frame.py`. A `WallRunFrame` is `(tile, texels per unit,
u-origin, v-origin as a world z, y_repeat, flip)` attached to a RUN; a
`SurfaceFrame` is `(tile, anchor, expanded, flips)` for a floor or ceiling.
`resolve_run` derives all six wall fields from the frame and the wall's own
world geometry, and `resolve_surface` derives `floor_stat` and the two
pannings -- so a portal cut changes nothing and the wall-list order is not an
input.

The one running quantity is the texel cursor, and it is a prefix sum of
`x_repeat * 8` **because the engine's accumulator is** (`:3036`). Using the
true world distance would drift from the editor by the accumulated rounding of
every wall before it, and the invariance test below would fail. That is the
sense in which this is closed form: closed in the wall list, not in the run.

`frame_map` replaces `texture_align.align_wall_runs` and the floor-anchored
`align_wall_textures` pass **together**, which is the fix -- those two fought
each other. The run pass carried x inside a sector loop and refused every
portal-to-portal join but one opted-in concourse; the anchor pass then set y
from each wall's own sector height, breaking the vertical phase at every kerb,
sill and lintel.

### The gate, and the threshold that had to be measured twice

`texture-continues-across-a-join` in `rules_blood.py`, over nine classes
(collinear/bend/reflex x solid-solid/solid-portal/portal-portal) in two axes.

The first version used the campaign aggregate minus fifteen points, as the
brief specifies, **and it flagged E1M1 and E3M1**. The reason is that the
aggregate is not a standard: `bend solid-solid` x runs from **28% to 95%
across the campaign's own maps**. A rule fifteen points under the 68%
aggregate is a rule about being below average, and a third of Blood is.

The threshold is now each class's campaign **floor** -- the lowest any single
campaign map with 30+ joins reaches, rounded DOWN to the per cent. A violation
then says something falsifiable: *no campaign map is ever this bad in this
class*. Rounding the floor to the NEAREST per cent instead flagged five maps
with their own minimum, which is how that detail was found.

Deliberate restarts are excluded **by axis**, not by class. The campaign
restarts x at outside corners (19-25%) and between step bands (30%) and
continues y in those very same joins 62-91% of the time, so dropping the whole
class would stop looking at the half that is broken.

### The acceptance test: the editor has nothing left to say

`auto_align_walls` is a port of `ED32_AutoAlignWalls`, second pass included.
Resolve a frame onto a run, then run it: **0 of 788 framed walls in 158 runs
moved**, on pattern-zoo, blood-city and E1M1. `tests/test_texture_frame` holds
it on E1M1 and E3M1 -- original geometry with diagonals, steps, portals and
bottom-swapped walls, not a rectangle chosen to pass -- and a companion test
nudges one wall by 7 to prove the check can fail.

That test found a real transcription bug. `AlignWalls`'s y term has a negative
numerator at every lintel, sill and kerb return; **C truncates toward zero and
Python floors**, so `-1 // 8` is `-1` where C gives `0`, and `-1` becomes
`y_panning` 255. Thirty-six walls of the pattern zoo read as misaligned by
exactly that one step until `c_div` existed.

### The class table, before and after

```text
                            campaign      pattern-zoo        blood-city
                            n      x   y    before  after     before  after
bend solid-solid          20021  68  99    x 41 -> 93       x 73 ->  95
bend solid-portal         13366  34  61    x 60 -> 73       x 91 ->  83
                                           y 78 -> 93       y 31 ->  97
collinear solid-portal     4442  80  88    x 42 -> 71       x 94 ->  98
                                           y 49 -> 100      y 58 ->  97
bend portal-portal        28216  30  91         --          x 55 ->  93
collinear portal-portal    3588  57  89         --          x 37 ->  87
reflex solid-portal        2836  25  62         --          x  0 ->  58
                                                            y  0 ->  12
```

Gate: **3 findings before, 0 after; 0 of 43 campaign maps flagged.** One class
went down -- blood-city `bend solid-portal` x, 91% to 83% -- because
`world_align_facades` had been phasing those walls from world position and now
mostly stands aside (`walls_phased` 128 -> 1); at 83% it is still two and a
half times the campaign rate, and the two passes wanting the same walls is
worth a decision rather than a silent winner.

### Crate tops

The campaign's raised crate tops (floor tiles 95/298/375/452/456/462, above
every neighbour): **110 of them, 62% expanded, 71% landing the tile grid on
the crate's own corner, 59% panned, 6% first-wall-relative.** The city's
eleven and the zoo's three used **none of it** -- no expanded bit, no panning,
nothing on the grid. `frame_raised_solids` gives each an object-anchored
`SurfaceFrame`: **11 of 11 and 3 of 3 now wear an uncut top**, up from 0. The
expanded bit is left as authored, because halving the world size of a tile is
a look and landing the grid on the corner is correctness.

### The moving-wall law, which the zoo's read-back taught

`frame_map`'s first run turned the zoo's curtain texel scale from 2.0 into
0.02 and the read-back gate refused the build. A moving sector's walls have no
projectable length: `TranslateSector` moves the flagged end every tick while
`x_repeat` stays put, and a curtain's fabric repeat is authored for the span
the cloth hangs ACROSS while the file is saved at the gathered pose. So
`MOVING_SECTOR_TYPES` are skipped and counted (`walls_left_to_their_mechanism`
92 in the zoo, 60 in the city). The authoring-loop law caught a representation
mistake that no texture measurement would have.

### The shopfront, measured -- and not yet applied

E6M1's four glazed walls do not lie between the street and the shop. `s4` and
`s64` are 4096 x **512** four-wall display recesses; against the shop `s52`
that is a **sill 8192 up and a head 77824 down**, and the pane is the recess's
INNER face, so the facade material crosses the mouth as a lintel band and the
street never meets the glass. `glass.recess_spec` reproduces those two z values
exactly from the shop's own, `recess_faults` tells a display box from a room
(E6M1 s4/s64 clean, s52 flagged), and `panes_without_a_recess` is the
map-level reader.

**The census qualifies the brief: of the 356 glazed walls in the 43 campaign
maps, 139 (39%) sit in a shallow pocket and 217 are on a room face.** The
recess is a strong minority idiom for shopfronts, not a law about glass, which
is why the constructor offers it rather than forcing it.

Re-glazing blood-city's six spans through it is **not done** -- see below.

### What remains unproven, and what was left out

* **The city's six shopfronts are not re-glazed.** Eight of its thirteen
  glass-bearing sectors are rooms, and the fix is a geometry change in the
  levelprog tree -- carve a 512 recess, re-hang the pane on its inner face,
  continue the facade run across the mouth -- which needs its own build pass
  and its own read-back claim. The reader, the spec and the fixtures are in
  place so that pass can be gated; doing it inside this run would have been an
  unread-back geometry edit to a map that currently builds clean.
* **Sloped walls are not modelled.** `GetWallZPeg` is transcribed as written,
  which reads flat `floor_z`/`ceiling_z`; a sloped sector's peg varies along
  the wall and this pass does not know it.
* **Bottom-swapped walls are ported but not fixtured.**
  `ED32_AutoAlignWalls_GetWall` (`:3058-3061`) and flag `0x20` are
  transcribed; no test drives them, because no map to hand has a
  `kWallSwap` run to drive them with.
* **`world_align_facades` and `frame_map` overlap.** Both want the facade
  walls, and the frames are winning by default. Owner queue item 16.
* Wall x/y flips are carried from the run head as the editor does
  (`cstat0`, `:3095`), but nothing chooses them: no frame in either build
  sets a flip deliberately.

### Regression tests

`tests/test_texture_frame`, 15 tests: the engine arithmetic (approxDist, C
division, the sixteen-unit texel, the 1024 grid line), the z peg against every
one-sided wall of E1M1, the invariance pair plus its can-it-fail companion,
the run crossing a sector boundary, the partition covering each wall once, the
moving-wall skip on DOOR-CURTAINS, and the calibration (0 of 43 flagged, plus a
fail-first on an E1M1 with every panning zeroed). `tests/test_glass` gains five
for the recess.

### Next highest-value experiment

Carry the recess through: give `levelprog` a shopfront node that emits the
recess, the pane and the facade run as one thing, and make
`panes_without_a_recess` a build-blocking claim in `readback.sentence()`. Then
decide the `world_align_facades` overlap, which is the last place two passes
still want the same field.

## The demonstration maps, and two things they said plainly

`maps/blood/mechanism/` holds thirty-odd official XMapEdit tutorial maps, one
mechanism each -- #SLDOOR, #SWDOOR, #STACK, #TYPE600/602/613/616/617,
#REVDOOR, #ELEVATR, #PATHSEC and the rest -- beside the owner's own
casket.map. This project had never read one of them, and both defects the
owner then found by walking are stated outright in the first two opened.

**A transmitter sends because it reports an EDGE, not because it has a
channel.** `SetSpriteState` calls `evSend` only inside

```c
    triggers.cpp:100  if (pXSprite->txID) {
                          if (command != kCmdLink && pXSprite->triggerOn
                              && pXSprite->state)  evSend(...);
                          if (command != kCmdLink && pXSprite->triggerOff
                              && !pXSprite->state) evSend(...);
```

so a switch with a valid `tx_id`, a valid `command` and a valid
`trigger_push` but neither edge flag flips its own state and sends NOTHING.
The pattern zoo shipped five of them. Every field is individually valid, no
static reading of the finished map can tell, and the owner found them by
pushing each one. `#TYPE600.MAP`'s canonical switch is type 21 on picnum
1046 with `trigger_on` and a 30-tenth `wait_time` so it springs back.
Registered as `transmitter-reports-an-edge`: 13 of 2234 campaign
transmitters, an error-tier rule.

**And the canonical doors have no switch at all.** #SLDOOR and #SWDOOR carry
`trigger_wall_push` on the moving SECTOR and no rx_id: you push the door
itself. The route is orthogonal to the channel, which is what the grammar
said and what the constructors did not offer.

**A stack is marked on BOTH halves.** #STACK.MAP puts floor picnum 504 on
the upper sector and ceiling picnum 504 on the lower, and the oracle does the
same on s3 and s6. Marking only the upper -- which is what the zoo did --
leaves the view from below looking at a solid ceiling.

**A casket is FOUR sectors in TWO planes.** s2|s3 is a lid in the upper
room's floor and s5|s6 its mirror in the lower room's ceiling, both on rx 100
with the same travel, so the ceiling below opens as the floor above does.
Building only the upper plane leaves a hole in the floor with an unbroken
ceiling under it, which is what the owner saw.

## The motion machinery, factored, 2026-09-01

`bloodmap/motion.py` holds the four primitives every Blood motion mechanism
is composed from, each separately readable, separately buildable and
separately fixtured. `mechanism.planar_door` and `mechanism.curtain` are thin
compositions that add only composition facts. The point is not tidiness: a
grammar factored this way can read and build combinations nobody has named.

```text
1 MARKED-WALL MOTION  flags -> moved POINTS -> the vertex closure.
                      `motion_set` is the closure and it spans sectors,
                      because dragpoint (engine.cpp:13071) walks every wall
                      around a moved vertex. payload_shape names the three
                      arrangements: re-partition, self-resize, rigid
2 MOTION MARKERS      the from/to pair; `owner` is the sector CONTROLLED,
                      not the one it stands in; `state` says which pose the
                      map is drawn in and a state-0 sector jumps at load
3 CONTROL WIRING      route (push / wall-push / wall-button / remote /
                      level_start / keyed) orthogonal to the verb, and the
                      VERB IS CHECKED against the receiver's state
4 ROR STACK           link pair 2332/2331 on statnum 0, data_1-paired, a
                      TRANSLATION AT A PLANE -- and see-through as its own
                      property, floor picnum 504 (mirrors.cpp IsRorSector)
```

**What the factoring corrected.** The isolation discipline is NOT universal,
and measuring it said so. E1M1's curtain is isolated -- its motion reaches
only itself and the alcove behind -- because the deformation runs along a
face the player looks at, and the fabric is a RECESSED BULGE in a strip whose
unmoved shoulders carry the room-facing wall. E1M1's casket is NOT isolated:
s28 drags one wall each of sectors 1 and 2, s30 one each of 67 and 68,
because a floor boundary sliding across a room meets that room's walls at its
ends and nobody sees it. So the gate checks a construct against what it
DECLARED rather than against a blanket rule, and `declare_motion` is how a
constructor says what it means to touch.

## The two gates that were missing

Both were written first, watched fail on the zoo as it stood, and only then
satisfied.

**Swept-state** steps every mechanism's full travel through `motion_sim` and
checks for inversion, collapse and wall crossings at each step. It caught the
casket's cover sweeping 2304 units past its own far wall.

**Motion-set conformance** computes the actual motion set and diffs it
against the declared payload, naming the wall and the shared vertex it drags
through. It caught the curtain deforming the section room: the fabric's
moving vertices were the ROOM's corners.

Both run in `PlanarLayout.compile` and in the zoo's own gate, alongside a
whole-map sweep for wirings whose command cannot change their receiver.

## The paid-for build gotchas

Each of these cost a failed build at least once. They are properties of
`PlanarLayout` and the Blood constructors, not of the zoo.

```text
sub-rooms go in a BACK BOX      a region wholly inside another is a
                                containment the layout refuses, and rightly:
                                neither side of that boundary can be a portal
a feature narrower than the     leaves the rest of the shared stretch
wall needs a NECK               coincident and unpaired; the corridor makes
                                the same move onto every room
a room may not be wider than    its near wall then meets the wall either side
its own doorway                 over stretches that are neither portal nor
                                solid
a gate sector must be WIDER     the leaves retract past the ends of the
than its threshold              opening into the jambs
a rotor's clear height is a     a blade spans its rotor exactly, top on the
whole number of blade tiles     ceiling and bottom on the floor; a height that
                                is not is refused rather than filled
a sprite may not span an        wall sprites are checked against the z range
opening                         each wall is open over, so a sign goes above
                                a header, never across a mouth
a floor sprite's z is its       seating goes through `furniture.place`, which
CENTRE                          dispatches on the tile's own mounting
placement ids must be unique    `placement_sprites` is a dict; three gates
across the whole map            named `<x>:gate` all produced `gate_leaf_west`
                                and two of them became unfindable
a marker's OWNER is the sector  E1M1's casket puts its "to" marker inside the
it controls, not the one it     cover, which has no XSECTOR at all; the loader
stands in                       deletes any marker whose owner names none
half of four axis frames are    a reflection reverses a loop's winding AND the
REFLECTIONS, not rotations      side a wall sprite offsets to; transport the
                                local normal rather than reasoning about signs
a branch's back boxes reach     so the gap between two branches on the same
out of BOTH its long walls      side is the two facing runs' depths, not a
                                constant
```

---

# Phase 11 — Automatic discovery frontier + batched review

**Status, 2026-09-01: the self-correction half is DONE and proven; the
novelty frontier is OPEN.** What exists and holds: attested-construct
fixtures, the conformance and swept-state gates, the motion-set check, the
zoo reading itself back, the contradiction queue, and the batched review page
(`reports/owner-review-queue.md`). What does not exist: anything that goes
LOOKING for a pattern nobody has named — every finding so far came from a
question someone asked. That asymmetry is the phase's remaining work, and it
is not started.


**The authoring-loop law (owner, 2026-09-01):** whenever the AI builds a
mechanism in a level, it must immediately verify that the built thing
does what was INTENDED — read it back through the understanding stack
and compare against the declared sentence (self-read: it exists and
fires; swept-state: valid through the whole travel; motion-set: only the
declared payload moves; intent: the function claim holds in the
embedding). A mismatch is always a finding: either a bug in the level or
a bug in this project's constructors, readers, or grammar — and both
kinds are wins. Building without this read-back is not finished work.
This is why intent must be declarable (MechanismDecl, Phase 13): a
comparison needs both sides in one language.

**Owner steering (2026-09-01): the mining system must be built to
self-correct and expose its own errors.** The working example is the
curtain verification of the same day: an owner claim (sector id, wall
ids, motion story) was checked field-by-field against the map, one id
discrepancy surfaced honestly (motor is s125, s124 is the lit room), and
a new rule fell out (rigid vs elastic payload topology). Generalize that
loop into standing machinery:

1. **Attested-construct fixtures** — every owner-attested construct
   (casket s27-s30, curtain s124/125, door s4, the s65/s90 workaround,
   the turnstiles) is a permanent test: the reading stack must parse the
   real map into the expected grammar sentence, and any model change
   that breaks a parse fails the suite. Owner knowledge becomes
   regression armor, not prose.
2. **Contradiction mining** — cross-layer consistency checks over the
   knowledge index: owner anchors vs the corpus usage-kind table vs
   constructor claims vs bundle views. Disagreements are ranked into the
   review queue as first-class frontier items — a contradiction is a
   discovery.
3. **Round-trip closure** — every constructor's test builds, reads back
   through effects/conditional, and asserts the parse equals the grammar
   sentence the constructor claims (the zoo's self-reading gate,
   generalized to unit scale).
4. **Owner claims as probes** — when an owner statement disagrees with
   the data, the system reports the discrepancy with evidence and lets
   the review decide; it never silently accepts either side.

## DONE, 2026-09-01: the self-correction half

Owner-steered and proven. **PARTIALLY done overall** — the discovery
frontier is untouched and said so below.

**Template conformance** (`bloodmap/conformance.py`,
`projects/pattern-zoo/sweep.py`). Every constructor promoted from a mined
template gets a check that rebuilds it, measures it with the same relational
miners that produced the template, and diffs. Relations, not absolutes:
angular spacing about an axis, radial stand-off, span as a fraction of clear
height — so a legitimate rescale passes and a rotation that forgot the angles
does not.

It was written to fail first, and it did. The owner walked v3 and found the
turnstile's four blades in a SQUARE instead of a cross; the check reproduced
that from the built map, and the campaign's own rotors (E1M4 151/314) passed
it, which is what calibrated it. Then the sweep found the rest:

```text
what the sweep caught, before the fix        10 deviations, 10 constructs
  6 rotors        blades in a square         the owner's report
  4 sliding gates leaves edge-on to their    NOT owner-reported: found by
                  own travel                 the machinery
one root cause    frame.Framed rotated sprite POSITIONS and not their ANGLES
```

Four gates had shipped leaves that slid edge-on and stopped nothing. That is
the "many similar oddities" the owner suspected, found automatically, and it
is the argument for the whole mechanism: every one of those passed structural
validation, the usage laws, the self-reading gate, byte-exact round trip, an
NBlood load smoke and thirty-one renders.

**Attested-construct fixtures** (`tests/test_attested_constructs.py`). Twenty-
one assertions parsing the ORIGINAL campaign maps, turning owner knowledge
into regression armor: the casket's four sectors, its boundary re-partitions
and ergonomic z-assist and voice; the curtain's elastic payload, its
push-the-fabric wall route and its command-5 light link to s124; s4's rigid
double slide worked from its own leaf walls; s65/s90's synced ROR pair with a
sprite-only payload; E1M4's counter-rotating turnstiles. Three facets the
model still cannot produce are `expectedFailure` with their blueprint
reference, so the gap is countable rather than absent — and an
expectedFailure that starts passing reports as an unexpected success.

**Contradiction mining, minimum viable** (`bloodmap/contradictions.py`,
`llmapper contradictions`). One command comparing the four places this
project keeps the same facts — owner anchors, the usage-kind table,
constructor claims, a built map — ranked conflict / drift / open, each item
named for confirm or reject. It independently surfaced the tile-502 drift a
human found by hand last run, and it carries the two questions measurement
could not settle.

## STILL OPEN: the discovery frontier

Ranking candidates by novelty, coverage and uncertainty over community
mining, and batched review actions that PROPAGATE (confirm / reject / split /
show counterexamples changing downstream state). None of that is built. The
queue here is a comparison of what is already written down, not a search for
what is not. The exit criterion — the user no longer needs to enumerate most
concepts manually — is NOT met.

## Two items awaiting the owner, not the machine

Both are in the contradiction queue by name, and both are the owner's call by
construction:

* **`mask-law-two-sided-exception`** — tiles 142 and 2464 break the mask law
  on two-sided walls in 23 of 60839 slots, against a clean zero everywhere
  else. Family or accident decides whether the law gains a door-leaf clause
  or a rate.
* **`gallery-topology-exemption`** — the zoo measures mean_degree 2.09
  against a campaign median of 2.74, and dead-ends 0.344 against 0.159.
  Thirty-one exhibits are terminal by construction; the only way to hit the
  norm is loops that go nowhere. The proposal is a documented exemption for
  gallery-shaped artifacts rather than gaming the number.

---

# Phase 12 — Recursive knowledge growth

Use learned concepts as new atoms (drawer unit → desk assembly → office
region; storefront → facade → street frontage). Provenance must survive
through abstraction layers.

## Exit criteria

The system discovers patterns not expressible in raw sector/wall/sprite
terms.

---

# Phase 13 — Design intent + synthesis

**PREREQUISITE (systemic review, 2026-09-01): ONE source language.** The
level is currently authored in TWO dialects — the levelprog tree
(blood-city, vertical-fragment, e2m3-decompiled) and flat PlanarLayout
(pattern-zoo, facade-pilot, reasoned-authoring) — and the constructors
are split BY dialect: mechanism.py and the facade builders speak flat,
templates/setpieces speak tree. Measured symptoms: promotion-queue ranks
8 and 9, blood-city's turnstiles.py hand-adapting a spec because the
builder targets the other stack, and the zoo being written in the
dialect without locality, style provenance, or an intent tree. Fix
before MechanismDecl (or it gets implemented twice): the TREE is the
only source language; PlanarLayout is demoted to compiler IR — output of
the tree, never hand-authored; constructors re-homed to tree nodes; the
zoo and facade-pilot rewritten as the proving migration. Alongside: the
source layer should speak DERIVED units (player heights, steps, bays)
with the compiler doing Build conversion — the 16:1 z anisotropy has
burned this project repeatedly and raw numbers in source are where it
hides.

**Owner-steered entry point (2026-09-01), from the representation review:
the missing layer is a shared CONSTRUCT/SENTENCE schema.** The review
found: BuildIR/native needs no rework (byte-exact contract stays); the
reading stack parses mechanisms into grammar sentences well; the level
program tree understands architecture (locality, style provenance) but
mechanisms are NOT citizens of the tree — they are imperative calls into
flat PlanarLayout with sector_behavior dicts, and intent exists only as
~15 free-text `intent={"purpose"}` strings. Reading and writing never
meet in one schema; self-reading bridges them post-hoc. The rework:

- **MechanismDecl**, a typed node used by BOTH sides: members+roles
  (lid/hole/link/switch/blade...), primitives with parameters (the
  four-primitive factoring), wiring (interaction route, channel, command
  verb), and a TYPED function field — the E1M1 taxonomy (narrative /
  secret / progression / ambush / furnishing / fixture /
  ergonomic-assist / workaround) — with evidence for the claim
  (INTERPRETED discipline: function is asserted from embedding, contents
  and dressing, never free).
- Level programs DECLARE mechanisms as tree nodes, compiled down to
  PlanarLayout behaviors; readers (effects/conditional/assembly) EMIT
  the same schema from original maps; fixtures, conformance and the zoo
  self-read become structural equality between the declared and the
  parsed sentence — the self-correction loop gains one common language,
  and reading↔writing become symmetric.
- Scope: a new declaration layer + adapters — NOT an IR rewrite.

Fundamental understanding of mechanisms is what makes intent legible
(the owner's thesis); this layer is where that intent lives and is
checked.

Generate from semantic/function/architecture intent, not coordinate soup.
This must land in the existing source representation: level programs and
`vocabulary.py` constructors, per the project's representation-first
priority. Deliverables: design-intent IR, deterministic compilation,
hard/soft/style constraints.

## Exit criteria

A prompt such as "small street-facing shop, two-bay facade, recessed
storefront, counter, rear storage" produces a structure whose relationships
survive changes of width, orientation, or art set.

---

# Phase 14 — Independent critics and scoped repair

## Already in the repository

Independent critics exist (geometry validate/audit, level_profile, NBlood
oracle, visual observer, overlap validator) and feed `authoring_loop.py`.

## Gap

Structured diagnoses with repair scope; semantic-delta validation after
repair. Standing warning: critic rules have historically measured the wrong
thing — every critic must name its oracle and a failure it provably
detects.

## Exit criteria

A facade readability failure can be repaired without changing progression
or rebuilding unrelated rooms, and the semantic delta proves it.

---

# Phase 15 — Quality diversity

Late-stage. Once understanding and critics are reliable, maintain diverse
valid solutions along axes (verticality, loopiness, openness, clutter,
facade rhythm, encounter density, mechanism complexity). Do not use
quality-diversity to hide weak semantic understanding.
