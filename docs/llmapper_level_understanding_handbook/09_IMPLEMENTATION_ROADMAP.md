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

# Phase 8 — Neutral dynamic-state observations

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

- **the casket** — the player start (sector 30, kMarkerSPStart) IS a
  kSectorSlideMarked sector, ROR-paired via stack link_id 10 with sector 28
  (also slide, rx 102, shade wave); the opening lid is slide + link + z
  change, and sector 30 TXs 103 onward. *Narrative* — the primitive dressed
  as waking from a coffin.
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
- **sector 125** — a *curtain* that opens (slide as soft furnishing).
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

# Phase 9 — Conditional topology and causal meaning

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

**NOT done, stated as the known gap.** The 657 rotate and slide mechanisms
have no swept-area spatial-effect reading and are **excluded, not answered**.
The turnstile family is inside that gap and is parked by owner decision; its
passage blocker stands.

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

# Phase 10 — Multi-view understanding bundle

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

# Phase 11 — Automatic discovery frontier + batched review

## Gap (new work)

Ranked candidate queue with novelty/coverage/uncertainty, and batched
review actions (confirm / reject / split / show counterexamples) that
propagate. Review is a queue, never a blocking gate (project norm).

## Exit criteria

The user no longer needs to manually enumerate most concepts to
investigate.

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
