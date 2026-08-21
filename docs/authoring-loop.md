# Reasoned authoring loop

`bloodmap.authoring_loop` is the integration seam that turns a one-shot generator
into an iterative one. It does not add analysis; it arranges existing analysis
into one bounded evidence packet an external reasoning agent can act on.

```text
LLM writes Python / PlanarLayout source
    -> compile candidate MAP                 (bloodmap.planar_layout)
    -> hard structural gates                 (analysis, geometry_audit, placement, progression)
    -> independent decompilation             (bloodmap.decompiler.decompile_level)
    -> design probes                         (bloodmap.probes)
    -> ART and corpus-relative evidence      (materials, player_space, morphology)
    -> optional NBlood viewpoint capture     (bloodmap.oracle, bloodmap.viewpoints)
    -> concise evidence packet               (llmapper.authoring-iteration)
    -> external agent compares with intent   (llmapper.authoring-review)
    -> source-level revision
```

Two rules hold throughout:

* **An authored label is intent, never evidence.** `role="courtyard"` is recorded
  in the intent section and is excluded from every observation section. What the
  space *is* comes only from the compiled MAP.
* **Nothing is reduced to one quality number.** Structure, space, progression,
  material, scale, shape, and uncertainty stay separate and individually
  addressable. There is deliberately no `quality` field to optimize.

## The packet

`evaluate_candidate(candidate)` returns an `AuthoringIteration`
(`llmapper.authoring-iteration`, version 1) with these sections:

| Section | Contents |
| --- | --- |
| `identity` | source module, iteration and parent ID, declared changes, MAP hash and size, object counts, deterministic-compile result |
| `authored_intent` | declared assemblies, transitions, progression, landmarks, optional regions, loops, material vocabulary |
| `hard_gates` | each precondition reported individually as `pass` / `fail` / `skipped` |
| `independent_hierarchy` | `decompile_level` over the compiled candidate: derived assemblies, spaces, singletons, connections, vertical overlaps, detail groups |
| `hierarchy_comparison` | authored grouping beside derived grouping, plus discrepancies with the rule that produced each |
| `design_probes` | brief-relevant probes, declared against region IDs and resolved to sectors after compiling |
| `art_evidence` | dominant surfaces, repetition, shade ranges, empty spaces, decorative distribution, transition material change, sprite world scale |
| `corpus_scale` | player-relative footprint and clear height as percentiles against original maps of comparable size, plus whole-level shape against a mined shape corpus |
| `render` | viewpoint manifest, pose-only variant diffs, and captured PNGs when the engine is available |
| `review` | the external agent's conclusions, attached only after every reference resolves |

`identity.counts` carries a `counting_note`: object counts describe size, never
quality. A candidate with more sectors is not a better candidate.

## Hard gates

Every gate is reported separately and no failure is hidden:

`native_structure_valid`, `authored_geometry_valid`, `no_unintended_overlaps`,
`no_unresolved_boundary_contacts`, `intended_adjacency_realized`,
`geometry_conservation`, `portals_realized`, `player_start_valid`,
`player_relative_clearance`, `required_reachability`, `exit_reachable`,
`object_attachment_valid`, `deterministic_emission`, `nblood_load_smoke`.

A gate is `skipped` when its evaluator could not run — no engine, no player
start to measure. **A skipped gate is never a passing gate.** Engine work is not
attempted at all for a candidate that already failed a cheap structural gate, and
the skip records which gates blocked it.

## Independent hierarchy as a critic

The comparison maps each authored assembly onto the derived spaces its sectors
landed in, and raises discrepancies such as:

* `assembly_split_across_navigation_components` — parts of one authored assembly
  are not connected to each other;
* `assembly_lacks_dominant_perceptual_space` — its largest derived space holds
  under 40% of its floor area;
* `authored_assemblies_share_one_perceptual_space` — two intended identities
  were grouped into one place;
* `transition_regions_dominate_space` — a mixed space is mostly doorway and
  stair floor area, so it reads as circulation;
* `assembly_contains_perceptual_singletons` — two or more non-circulation
  sectors were grouped with nothing else;
* `embedded_structure_merged_into_host` — a declared child shares a derived
  space with its parent.

Each discrepancy carries the `rule` that produced it and resolves to exact
authored region IDs and derived node IDs. Every one is labelled a derived
observation, not a verdict.

**These rules measure floor area, not sector count.** An early version counted
sectors and called a 1008 player-area courtyard "circulation" because six tiny
stair steps outnumbered it, and called every gated room "fragmented" because a
closed Z-door has no at-rest opening and can never group with anything. Both were
corrected after the rule disagreed with a rendered frame.

## Corpus-relative scale and shape

Player-relative numbers alone do not say whether a space is right. "Four player
heights" only means something next to what original maps of the same footprint
do. `corpus_scale` therefore reports each derived space's area-weighted clear
height as a percentile against corpus sectors within half to double its
footprint, and the whole level's shape signature against a mined shape corpus:

```text
python -m bloodmap ...                       # mine the corpora first
bloodmap.player_space.mine_build_spatial_corpus(maps)   -> llmapper.spatial-corpus
bloodmap.morphology.mine_shape_corpus(maps)             -> llmapper.shape-corpus
```

`mine_shape_corpus` is the shape counterpart of the spatial corpus: orthogonal
and diagonal wall-length fractions, occupied orientation bins, orientation
diversity, chamfer fraction, segmented-arc chains, and rectangular and convex
sector fractions, per map.

A percentile says a number is unusual for that corpus. It never says the number
is wrong, and the packet says so in its own `limitations`. Deliberate exceptions
are expected to be argued in the review, not silently tuned away.

Both sections degrade honestly: with no corpus supplied, player-relative numbers
are still reported and every percentile is `null`.

## Viewpoints and rendered views

`bloodmap.viewpoints` is pure and dependency-free so declaration, validation, and
manifest generation stay testable without a game executable. A viewpoint names a
pose inside an authored region; `resolve_viewpoint` refuses a pose outside its
sector or outside the sector's Z range.

A variant MAP may change **only** the player-start pose: the header start fields
and every native `kMarkerPlayerStart` sprite (Blood spawns from the sprite, not
the header). `viewpoint_variant_diff` enumerates every difference and
`prepare_viewpoints` refuses any variant that changed anything else, so a
captured frame is evidence about the candidate and not about a different map.

`bloodmap.oracle.run_nblood_viewpoint_capture` launches NBlood once per pose in
an isolated work directory, waits for MAP initialization, and preserves one PNG
per pose alongside its sector, XYZ, angle, engine revision, MAP hash, and image
hash. **Image hashes establish stability, never visual quality** — the images are
kept so they can be looked at.

## The reasoning-review seam

The deterministic package contains no LLM dependency. An external agent writes a
`llmapper.authoring-review` record:

```json
{
  "reviewer": "...", "iteration_id": "v2",
  "claims": [{"claim": "...", "status": "supported|contradicted|uncertain",
              "evidence": ["decompiled:assembly:001/space:004", "view:courtyard_center"],
              "reasoning": "..."}],
  "accepted_strengths": [], "problems": [],
  "next_actions": [{"action": "...", "expected_effect": "...", "evidence": []}],
  "uncertainties": []
}
```

`attach_review` refuses the record unless **every** evidence reference resolves
inside that packet. References use these namespaces:

`gate:` `decompiled:` `probe:` `view:` `intent:` `transition:` `authored:`
`art:` `scale:` `shape:` `sprite-scale:` `discrepancy:` `source:`

`record_review` appends the review to the existing workspace ledgers
(`design/decisions.jsonl`, `memory/episodes.jsonl`) rather than inventing a
parallel log. This is an auditable engineering record — intent, observed
evidence, conclusion, proposed change, expected result — not private reasoning.

## Cross-iteration comparison

`compare_iterations(packets)` emits `llmapper.authoring-comparison`, one row per
iteration across separate dimensions: hard validation, authored-versus-observed
hierarchy, singleton spaces, route structure, transition evidence, major-space
scale, ART differentiation, decorative distribution, oversized decorations,
corpus scale and shape, NBlood load, captured views, and the review. Its
`reading_guide` states that no dimension may be summed and that a lower singleton
count or a higher sprite count is not automatically better.

## Worked pilot

`projects/reasoned-authoring-v1/` is the first full use of the loop: four
preserved iterations of a cliffside monastery, each with its authored Python, its
MAP, its evidence packet, its rendered views, and its review. See
[the pilot report](../projects/reasoned-authoring-v1/reports/comparison.md).

```text
python -m experiments.monastery_pilot v0 v1 v2 v3 --comparison \
  --nblood reference/blood/nblood.exe --game-dir reference/blood
```

## Limits

* Perceptual grouping is the decompiler's static approximation (floor delta and
  shade delta across a portal). It is not a renderer and not a person, so every
  change it motivates should be cross-checked against a rendered frame.
* Shape metrics are whole-level aggregates. They locate a problem; they do not
  locate where it is.
* The sprite-scale rule fires above 75% of a space's clear height, which catches
  egregious cases and not merely poor ones.
* Nothing here measures combat, pacing, enemy placement, sound, or how a level
  plays.
