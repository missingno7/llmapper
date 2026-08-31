# Corpus Expansion, Active Learning and the Discovery Frontier

## The corpus as it actually exists (2026-08)

The corpus is local-only and never committed (see `docs/corpus.md`). It was
reorganized from a flat `maps/blood/*.MAP` into subdirectories, and expanded
with a large community collection.

**Provenance corrections from the owner (2026-08-31), overriding older docs
and code:** `DWE*` (Death Wish) and `TEDE*` are *not* conversions — they are
high-quality community maps the owner hand-picked as good sources. `DNE*`
are the owner's own manual Duke3D→Blood conversions. The filename table in
`docs/design-pattern-discovery.md` and `classify_map_population` in
`bloodmap/patterns.py` both mislabel `DWE`/`TEDE` as `conversion` and must
be corrected in Phase 0a.

### Layout (as reorganized by the owner, 2026-08-31; directory = provenance)

```text
maps/blood/
  campaign/      E1M*..E6M*   original Monolith maps (43)
    multiplayer/ BB1..BB9     original BloodBath (9)
  curated/       DWE* (Death Wish), TEDE*, SS*  owner's hand-picked
                              community source maps, single-player (44)
    multiplayer/ DWBB1-3, DM1-3  owner's hand-picked BloodBath/DM (6)
  conversions/   DNE*         owner's manual Duke3D->Blood conversions (4)
                              (pairs with maps/duke3d, see docs/corpus.md)
  community/     1500 bulk unsorted community maps (arbitrary filenames),
                 plus subdirs chronicles1/ (37), chronicles2/ (40)
  tiered/        the same community maps, sorted by a heuristic classifier
                 (from the `selection` branch); tier is metadata on the
                 community population, never a second population
  mechanism/     curated mechanism tutorials/showcases (#*.MAP singles,
                 Modern/, Vanilla/, helix_stairs.map) + xmapedit.pdf (172 maps)
  corpus.json    generated manifest; README.md records the layout
```

**Counts measured on disk 2026-08-31 by `bloodmap corpus-manifest`** (Phase 0a),
correcting earlier estimates in this document. They are a snapshot: the owner
reorganizes in place (`SSFACE.MAP` moved between `curated/multiplayer/` and
`curated/` during the Phase 0a run), so regenerate `maps/blood/corpus.json`
rather than trusting a number written in prose:

```text
blood-campaign       43   (E1M1-8, E2M1-9, E3M1-8, E4M1-9, E6M1-9; there is no
                          E5 set locally. The old "44" was 43 campaign maps
                          plus DNE3L1.MAP, a conversion, in the flat inventory)
blood-bloodbath       9
community-curated    50   (44 sp + 6 multiplayer)
own-conversion        4
community          1500   (1470 distinct filenames; 1706 distinct sha256
                          across the whole corpus, 0 cross-population
                          duplicates)
mechanism-tutorial  172
reference view      102   = campaign + curated, both modes
```

Tier attach, by content hash (`community/` files, `tiered/` as the index),
after the regenerated tree replaced the flattened one:

```text
bloodbath 538   S 373   A 182   B 172   questionable 132   C 52
mechanism  12   untiered 37
```

The 37 untiered are exactly the maps the native losslessness gate rejected, so
they were never scored. The previous tree gave 157 untiered because it
flattened every map to `tiered/<TIER>/<FILENAME>` and same-named maps
overwrote each other; `reports/blood-tiering-rerun.md` has the accounting. The
old tree is kept locally as `tiered-v1-backup/`.

`untiered` is honest absence: the map is not under `tiered/`. It is never
guessed.

**Why those 120 exist (2026-08-31).** The tier tree's generator landed in this
branch as `bloodmap/tiering.py` (PR #2), and re-running it explained the
ambiguity: the old tree flattened every map to `tiered/<TIER>/<FILENAME>`, so
two community maps sharing a name overwrote each other and one file stood for
two maps. All 128 affected maps were among the 157 the hash join left untiered.
The refactored generator keeps the source's shape below its population
directory, and all 128 now carry a tier. The counts above still describe
`maps/blood/corpus.json`, which reads the *old* tree; the re-run's assignment
is in `maps/blood/tiered/manifest-v2.json` (local-only) and the two are
compared in `reports/blood-tiering-rerun.md` -- 84% agree, and the 6% that
move are all single-step S/A churn caused by the reference population changing
from a 100-map `maps/canonical` directory to the 102-map `reference` view.

The physical reorganization is **done**; there is no `canonical/` and no
top-level `bloodbath/` directory anymore. "Canonical" survives as a named
**view**, not a directory: the reference set the tier classifier scored
against is `campaign + curated`, recorded in the corpus manifest.

Phase 0a (done): the registry lives in `bloodmap/patterns.py`
(`list_corpus_maps`, `resolve_corpus_map`, `build_corpus_manifest`), the
manifest is `maps/blood/corpus.json`, and the flat-corpus README moved from
`campaign/README.md` to `maps/blood/README.md` with updated commands.

Facts an agent must respect:

- The tier labels (`S`..`C`, `questionable`) come from a **heuristic feature
  classifier**, not from human judgment. They are navigation and sampling
  aids, never evidence weights and never ground-truth quality. The `curated/`
  set, by contrast, *is* human judgment — the owner's selection.
- `tiered/manifest.json` records absolute paths from another checkout
  (`D:\prog\llmapper\...`). Treat the manifest's *relative identity*
  (sha256, filename) as meaningful and the absolute paths as stale.
- `community/` and `tiered/` contain the same population; do not mine both
  as if they were independent evidence.
- **Provenance comes from the directory a map lives in.** Filename prefixes
  remain only a sanity cross-check (a `DW*`-named file in `community/` is
  still `community`). Community maps have arbitrary filenames, so the
  filename-only classifier cannot cover them anyway.
- Community maps have *not* passed the native losslessness gate. Some will
  be unsupported Build versions or corrupt. The gate stays fail-closed:
  a map that fails parse/roundtrip is skipped **and reported**, never
  normalized or silently dropped.

Measured by the Phase 0a run (`reports/blood-corpus-health.md`): 1462/1500
community maps pass; the reference view passes 102/102. No community map fails
on parse or on either byte roundtrip — every skip is a hard structural
validation error in an otherwise byte-exact file. Two files in `community/`
(`POWER06.MAP`, `TWISTER.MAP`) are **Duke3D v7 maps, not Blood maps**. Failure
concentrates entirely in the tiers the classifier already distrusts: every
`S`/`A`/`B`/`C` map passes, and all 38 skips are `questionable` (20),
`multiplayer` (16) or untiered (2).

## Populations

Keep source populations separate. The population registry should become:

Game mode is a second, orthogonal axis, applied uniformly: provenance owns
the top-level directory; the multiplayer subset is always a `multiplayer/`
subdirectory (`campaign/multiplayer/`, `curated/multiplayer/`,
`tiered/multiplayer/`) and becomes metadata (`mode=sp|multiplayer`),
cross-checkable against player starts in the map.

```text
blood-campaign      campaign/ (mode=sp)      original Blood SP convention
                                             (authoritative)
blood-bloodbath     campaign/multiplayer/    original multiplayer convention
                                             (authoritative)
community-curated   curated/                 owner-vetted precedent + style
                                             vocabulary (mode=multiplayer for
                                             curated/multiplayer/)
own-conversion      conversions/             cross-game correspondence evidence
                                             only; never Blood design convention
                                             (layouts originate in Duke3D)
community           community/ or tiered/ (same maps; tier recorded as
                    metadata: tier=S|A|B|C|questionable|multiplayer|mechanism)
mechanism-tutorial  mechanism/               mechanism wiring examples, not
                                             design norms
generated           reconstructions and authored outputs — never evidence
```

The legacy population names `blood-campaign` / `blood-bloodbath` (used by
`bloodmap/patterns.py` and existing reports) stay valid: they are the
`original` provenance filtered by mode. Do not rename them in code; resolve
them from the directory layout.

Named views over populations:

```text
reference  = blood-campaign + community-curated
             (what the tier classifier scored against; the quality yardstick)
```

Authoritative statements about "what original Blood does" may only cite
`blood-campaign` and `blood-bloodbath`. `community-curated` supplies
**vetted precedent** ("hand-picked, demonstrated to work well in Blood");
bulk community maps supply wide precedent, clearly labeled as such.

## Two distinct questions

Keep separate:

```text
What did original Blood commonly do?
```

from:

```text
What has been demonstrated to work well in Blood/Build?
```

The second question may legitimately use the community corpus, preferring
higher tiers first as a sampling order.

## Coverage-driven corpus use

Do not mine 1500 maps because they exist. Evaluate what a candidate map or
tier adds:

```yaml
known_patterns_covered: 312
rare_patterns_covered: 27
new_unsigned_candidates: 14
new_mechanism_compositions: 7
new_texture_contexts: 38
new_topology_motifs: 4
```

Prefer maps that add design coverage, not duplicates. A practical order:
campaign (SP + multiplayer) + curated fully; then `tiered/S`; expand
downward only when a question needs more examples.

## Automatic candidate discovery

The miner (extending `bloodmap/patterns.py`, which already does unsigned
signature mining for spawn/route/morphology/vertical views) should search for:

### Repetition

Recurring relational subgraphs.

```text
same structural motif appears many times
```

### Contrast

Nearly identical structures with one systematic relational difference.

```text
shelf vs crate stack
window vs storefront
door vs lift despite similar Z-motion
```

### Anomaly

Rare but internally consistent structures.

These may be:

- new design patterns,
- mapper exceptions,
- broken hypotheses,
- unusual mechanisms.

## Discovery frontier report

After each corpus run produce a ranked work queue.

Example:

```text
#184
72 occurrences / 19 maps
stable geometry
strong facade association
unknown semantics

#291
31 occurrences / 8 maps
dynamic assembly
two stable states
strong topology effect
no current interpretation
```

Ranking signals may include: recurrence, cross-map diversity, structural
stability, semantic uncertainty, potential authoring usefulness, disagreement
between views, novelty, coverage gain — and cross-population status (campaign
convention vs community-only precedent).

## Human review is batched, never blocking

Project norm: no human gates inside agent loops. Automated acceptance runs to
completion; human decisions accumulate in a review queue and are applied in
batches.

Do not ask:

```text
What is sector 17?
What is sector 18?
```

Ask:

```text
Candidate 0187:
34 occurrences across 12 maps.

Hypothesis:
drawer unit

Why:
repeated shallow front-facing modules,
wooden frame,
27/34 use known drawer-front art.

Alternatives:
cabinet / shelf-like trim

[confirm] [reject] [split] [show counterexamples]
```

A single decision should propagate to many examples.

## Confirmation propagation

When a candidate is confirmed:

1. search structural neighbors,
2. find weaker instances,
3. find anchor-free variants,
4. find containing assemblies,
5. find correlated functional regions,
6. find contrastive concepts,
7. rerun higher-level candidate mining.

Human supervision should move upward from annotation to arbitration.

## Active-learning rule

Queue a question for the human when the answer is likely to change a large
part of the knowledge graph:

- two high-support hypotheses conflict,
- one label would classify hundreds of occurrences,
- a candidate is structurally stable but semantically ambiguous,
- a community pattern conflicts with original-campaign convention.

Avoid spending human attention on low-impact edge cases.
