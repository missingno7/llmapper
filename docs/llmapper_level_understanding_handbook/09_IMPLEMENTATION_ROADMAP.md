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

# Phase 5 — Object assemblies and negative space

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

# Phase 6 — Functional regions

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

# Phase 7 — Facade grammar

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
