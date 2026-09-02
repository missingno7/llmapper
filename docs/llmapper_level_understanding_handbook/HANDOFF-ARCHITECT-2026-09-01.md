# Architect handoff — 2026-09-01

Written for a fresh architect model. It separates evidence from belief; the
current plan is one proposal among possible ones, and your job is to
independently reassess. Where evidence surprised us or contradicted us, it is
kept and marked.

---

## 1. ORIGINAL OBJECTIVE

Move `llmapper` from "an AI that constructs valid Blood maps" toward a system
that can understand, decompile, explain, verify and eventually synthesize
authored level design. Standing priority predating this effort: the primary
artifact is a **hierarchical, editable source representation** of a level
(level programs); visual critique is secondary. `projects/blood-city`
(Gravesend) is the demonstration piece and acceptance test. The owner reviews
in batches, never as a blocking gate. The working roadmap is
`docs/llmapper_level_understanding_handbook/` (14 docs; `09_...md` is the
live single source of truth and has absorbed all owner steering).

Secondary owner goals, stated 2026-08-31: city facades with signs/lettering,
a park, a harbor that reads as a harbor (with a boat), street anatomy
(roadway/sidewalk/kerb), urban greenery; and a maintainable "pattern zoo"
map exhibiting everything the system can build.

---

## 2. HARD OBSERVATIONS / ORACLE EVIDENCE

Engine-sourced (NBlood source is in-repo as a read-only submodule) or
measured on the corpus. The surprising and contradictory ones are flagged ⚡.

**Corpus** (registry: `bloodmap/patterns.py`; manifest `maps/blood/corpus.json`)
- Campaign = **43** `E*M*.MAP` (an old "44/44" count included a conversion).
- Community gate: 1462/1500 pass; every failure is a hard structural error in
  an otherwise byte-exact file; all failures inside `questionable`/
  `multiplayer`/untiered tiers. Two files were Duke3D maps.
- ⚡ Heuristic tier churn: changing the reference view by 2 maps moved 6% of
  tiers; reference (102) vs original (52) views moved **14.6%**. Tiers are
  not stable to their reference.
- ⚡ The old tier tree had flattened paths: 120 duplicate filenames silently
  overwrote each other; 128 maps had lost tiers. The Phase 0a hash-join had
  refused to guess exactly those.

**Engine laws** (each has a detector + citation; `mechanism-curriculum-v1.json`, 17 laws, 0 unsupported)
- ⚡ `trInit` (triggers.cpp:2224-2245): the geometry SAVED in a map is the
  **ON pose**; the loader derives the OFF base by subtracting the marker
  delta. This is loader behavior, not convention — it holds even when the
  author drew the other pose by mistake.
- Markers are **state-anchored**: sprite type 3 = position for state OFF,
  type 4 = position for state ON; XSECTOR `state` decides the load snap.
  (Our earlier "from/to journey" model was wrong; zoo curtains ran backwards
  because of it.)
- ⚡ For slides, the marker pair contributes **only its vector difference**;
  absolute marker positions are free.
- Payload: types 616/617 drag every wall; 614/615 drag only cstat-16384
  (editor blue, travels the marker vector) / 32768 (green, travels opposite)
  walls; sprites ride on their own flags regardless (35 campaign mechanisms
  move only sprites). Motion moves **vertices**: every wall incident on a
  moved point drags (one end fixed, one moves) — the true payload is the
  closure over shared vertices, not the flag set.
- Mask color (palette index 255): 3590 ART tiles carry it; **0 of 28,158**
  campaign non-sky floor/ceiling slots use one. A law with zero exceptions.
  Two-sided-wall breaches: only tiles 142 and 2464, 23/60,839 slots — owner
  ruled 142 = skull-fireplace maskwall (legitimate see-through), 2464 =
  shotgun shell casing (accidents). ⚡ The machine's recommended default
  ("142 is curtain family") was wrong.
- Parallax sky family is exactly {2500, 3491, 3678}; ⚡ 5/1780 campaign
  ceilings wear a sky tile unparallaxed (unexplained residue).
- ROR: statnum-10 markers are deleted at load (`PropagateMarkerReferences`);
  campaign stack markers are statnum 0, picnum 2332 (upper)/2331 (lower),
  data1-paired. See-through requires floor picnum 504 or floorstat&0x180
  (mirrors.cpp). Owner: multiple ROR volumes visible at once glitch — E1M1
  reuses one giant ROR sector (s65/s90) as a slide carrier for gate sprites
  37/38 as a workaround.
- XSPRITE (db.h:51): trigger capabilities (Push/Vector/Impact/Pickup/Touch/
  Sight/Proximity), bus (tx/rx/command), timing, once-ness, key/lock, launch
  filters (skill AND game-mode bits), data1-4 are independent axes on ANY
  sprite — a "switch" is an appearance, not a wiring category.
- A command must fit the receiver's state: state-ON receiving command ON is a
  no-op (a zoo casket shipped exactly this and "did not work").
- Crack construct (`#SPR408.MAP`): type-408 sprite is a THING — statnum 4,
  cstat 722, trigger_impact, transmits on death — plus a staggered cascade of
  type-459 exploders (pic 908) and type-600 sectors on one channel.

**Mechanism semantics (measured)**
- ⚡ 88 campaign instances of the self-cycling rotor signature (rx=7
  level_start, retrigger both); only 6 are doors — the rest carnival ride,
  station rotors, fans. Same fields, different design objects; embedding
  decides, fields cannot.
- Naming from the moving surface gets 471/1179 wrong (122 floor-movers behave
  as doors; 102 ceiling-movers as neither).
- ⚡ Hidden switches: TWO independent contrasts (channel role; spatial
  placement) both null (best 0.614/0.640 vs 0.65 floor). 57% of hidden and
  59% of visible switch sprites sit in logic closets — the invisible bit is
  closet-wiring construction, not concealment.
- ⚡ Sound markers: picnum 2520 is sprite type 709 (kSoundSector, invisible)
  in 1247/1250 campaign uses; a Phase-4 "furniture niche" concept was 85%
  sound pockets and dissolved on re-run. Phase 1's headline statistic
  (`rests_on` exactly on plane) fell 86.5%→63.5% after visibility hygiene.
- E1M1 owner-attested constructs (ids verified to the field): casket = FOUR
  sectors (hole pair s28/s30, slide-marked + ROR link 10; cover pair
  s27/s29), boundary walls 221/229, same travel both sides (~-1916/-1912),
  s30's floor rise is an *ergonomic assist* (player lift-out), not gating;
  curtain = s125 motor with a fabric FIN (own vertices; walls 1200/1210
  opposite flags converge; 1201/1209/1183 stretch), pushed by its cloth
  (XWALLs tx→own rx), and TX 126 command 5 (Link) drives s124's shade —
  **the room light follows the curtain's busy value**; double slide door s4
  = one sector, both leaves, walls-as-buttons (leaf XWALLs tx 100 → own rx),
  no push on the sector itself.
- Owner oracle `maps/blood/mechanism/casket.map`: the planar-door principle
  with the MOTOR ON THE COVER side and both boundary sides flagged — two
  dialects exist; role assignment is free.
- Street kerb (E3M1, all 22 shared walls): **2048**, zero variance. ⚡ The
  project's earlier "kerb = 1024" was a different object (drain-grate ring).
  Roadway=352, sidewalk=4 (by area E3M1: 352 37%, 4 34%, 379 29%).
- Usage-kind proportion check: tile 400 used at **786×** its campaign rate
  in the zoo while per-slot checking passed every use — slot attestation
  alone cannot catch overuse.

**Verification failure modes actually observed**
- Historical: validators passed a map that segfaulted; "72 stairs to
  nowhere" passed every automated gate.
- Zoo v1: static renders + NBlood load smoke passed a map with **zero
  working mechanisms** (XSECTOR data written, sector `type` never set).
- Zoo casket: boundary travel −3080 into a 768-deep cover (cover inverts in
  motion) while `validate_map` reported **0 errors** — it validates the rest
  pose only.
- ⚡ Passage oracle: the only available driver (`-bot`) refuses to enter any
  kSectorRotateMarked sector at every period 32–400 (`walk=0 no_stance`), so
  six rotor probes produced **no data** — including two negatives that
  "agreed" by accident. Turnstile passage remains unproven.
- Base-graph disagreement: at-rest reachability vs progression differed by
  a fifth of E1M4 (357 vs 278) until a blocking-aware graph (gate on wall
  blocking cstat, reopen via the driving mechanism) was added; both older
  graphs were wrong in opposite directions.
- ⚡ An agent staged a file by name without diffing and swept unrelated
  owner edits into a commit (caught, rewritten). Stage-by-name alone is
  insufficient; diff first.
- Owner visual-guess error rate on tiles: ~12 corrections out of ~60 AI
  guesses (~25% (silently wrong if unreviewed)).
- Wave 1: Gravesend's district seams run down street centrelines — 8 street
  runs refused; roads impossible in 2 of 4 districts under current plan
  (4 attempted workarounds recorded in `bloodmap/street.py`). A bounding-box
  slot lattice dropped 11/20 park plants (the green contains a church).
  Also caught: the level's secret count was never declared (tx 1, command
  66, no trigger_on — every field individually legal).

---

## 3. CURRENT IMPLEMENTATION STATE

Branch `blood-city-arcade`, everything pushed; suite ~1552 tests green
(1 skip, 7 expected failures). Handbook phases (scoped statuses in
`09_...md` headers):

- 0a corpus registry, 0 architecture note, 1 relations, 2 anchors,
  3 unsigned candidates, 4 contrasts, 5 assemblies, 6 functional regions,
  7 facade grammar, 8 dynamic effects (Z-motion + swept; **polygon sweep
  open** — swept blocking state decidable for only 5/628 before it),
  9 conditional topology (blocking-aware base; swept family scoped),
  10 multi-view bundle (one map: E1M4, five disagreements preserved),
  11 self-correction half DONE (attested-construct fixtures over original
  maps; template conformance; contradiction mining queue; gates), novelty
  frontier over community OPEN. 12–15 not started.
- Gates in force: self-read (mechanism exists as claimed), swept-state
  (motion_sim steps full travel, geometry valid at each step), motion-set
  (actual vertex-closure payload = declared payload), state-preview (OFF/ON
  rendered pairs), usage-kind + mask/parallax/aspect laws, template
  conformance, resource-conflict detection.
- Constructors (with self-declared blockers): facade_run (missing held-out
  reproduction), turnstile/turnstile_pair (**passage unproven** — blocker
  stands), curtain (fin topology; closed-span repeat law pending in the
  walk-fix), planar_door (both dialects), lift, street (roadway+sidewalk+
  kerb-2048), shade_wave, maskwall_panel, sliding_gate, carry_wall/
  paint_wall, furniture.place/mounting_for.
- Knowledge: `owner-anchors-v1.json` (104 owner-named tiles, `binding`
  grades, wiring/state-pair/dual-role fields), `usage-kinds-v1.json` (4159
  tiles × attested slots), `mechanism-curriculum-v1.json` (136 tutorial maps
  mined; Modern/ dialect EXCLUDED), knowledge_index (~334 entries, graded
  OWNER/DERIVED/INTERPRETED), plus ~25 older versioned files (see the
  README table).
- Pattern zoo: registry-generated gallery (`projects/pattern-zoo/`),
  maintenance-only; conformance test forces an exhibit per public
  constructor. Owner walk results: casket ✓, lift ✓, curtains ✓ (texture
  stretch fix specified), keyed door ✓ (world key art ≠ granted key —
  law specified), crack ✗ (thing wired as a switch — fix specified per
  `#SPR408.MAP`), shelf-secret unintelligible (rebuild specified).
- Blood-city: wave 1 PARTIAL — streets built where seams allow + park green
  (9/20 planted); Parts B (signage), D (glass), E (venue chains) not
  started; wave-1b autonomous prompt exists (Parts 0/A–E incl. a seam
  decision brief). City: 257 sectors / 1672 walls (cap 7000).
- Two authoring dialects exist: levelprog TREE (blood-city,
  vertical-fragment, e2m3-decompiled) vs flat PlanarLayout (zoo,
  facade-pilot, reasoned-authoring); constructors are split by dialect.
- Owner review queue (`reports/owner-review-queue.md`): items 2 (zoo
  topology exemption draft), 3 (crate/shelf sector labels), 4 (maps/review
  trio), 6 (six tile-kind drifts) awaiting the owner; item 1 answered
  (142/2464); the seam decision pending.

---

## 4. CONSTRAINTS / INVARIANTS

- Original maps are the only evidence; generated maps may be scored, never
  mined. Populations never mix; community = precedent, never campaign
  convention; tiers are navigation metadata, never evidence weights.
- Corpus is local-only, never committed; provenance comes from directories
  (`maps/blood/{campaign,curated,conversions,community,tiered,mechanism}`,
  `multiplayer/` mode subdirs); enumerate via the registry, never by glob.
- The native byte-exact contract (parse/write/roundtrip gates) must not
  weaken. BuildIR stays Build-only.
- NBlood submodule is off-limits (hosts the playtest bot; never stage its
  pointer); xmapedit submodule likewise. Never `git add -A`; diff each file
  before staging by name.
- Never launch NBlood from an authoring session; verification is the
  XMapEdit observer + static/graph checks + motion_sim; play is owner-side.
  Bot runs are crash-smoke only, never navigation evidence.
- Owner review is batched, never blocking; owner anchors are OWNER
  provenance and are never overwritten by mining (campaign usage may be
  recorded beside them).
- The authoring-loop law (owner): build → read back through the
  understanding stack → compare to intent; a mismatch is a finding about
  the level or the tooling; unread-back building is unfinished work.
- Gates must be able to fail (each new gate is written to fail on a known
  defect first). A detector that measures nothing is reported unsupported.
- City wall budget 7000. Blood-city norms comparisons are rates-not-counts;
  norms are observed ranges, never targets; no single quality scalar.
- Suite (`python -m unittest discover -s tests`) green before push;
  corpus-gated tests skip cleanly without local maps.

---

## 5. HYPOTHESES (explicitly hypotheses)

- **Functional wall ownership** (owner): which construct a wall/vertex
  belongs to depends on mechanism type and intent, not storage; a construct
  is a subgraph crossing sector boundaries. Consistent with all observed
  cases; encoded; not adversarially tested.
- **Binding strength** (owner): how strongly a tile's look binds its meaning
  predicts the rule/exception ratio. Correlates with anchor enrichment
  r = 0.541 at n = 13 with clear counterexamples — *directionally supported,
  not established*.
- **The E1M1 naming cross-cut** (8/13 owner mechanism names not recoverable
  from topological embedding) may be that map's showcase density, or the
  general case — one attested map; frequency uncharacterised. A second
  owner-attested map would decide.
- **Mediation taxonomy** (frame/seat/holder/junction/seam/clearance) and
  **prefab slots** (host-derived bounded positions) are owner-proposed
  design-language concepts; partially corroborated by mining (jamb tiles
  195+200 span 32 maps; bay grid; lamp intervals); not yet systematically
  validated.
- **Intent must be declarable** (a shared MechanismDecl sentence schema for
  reading AND writing, typed function taxonomy) for the authoring loop to
  close — architectural hypothesis; nothing built yet.
- **One source language** (tree only; PlanarLayout demoted to compiler IR)
  would remove the constructor split — inferred from measured symptoms
  (queue ranks 8/9, hand adaptations); the migration itself is untested.

---

## 6. APPROACHES TRIED AND OBSERVED RESULTS

- Filename-based population classification → failed on arbitrary community
  names and mislabeled DWE/TEDE as conversions → replaced by directory
  provenance.
- Tile-anchored contrast classes (shelf vs crate) → REJECTED by measurement:
  every predicted discriminator under the 0.65 floor; best rule
  (portals<1.5, 0.729) was a map artifact transferring to neither map.
  ⚡ Contradiction preserved: the owner later reviewed rendered positives
  and ruled **all 16 shelf hits are true shelves** (two structural
  realizations) — the anchor was good; the tile-defined *comparison class*
  was the failure.
- "Fixture niche" unsigned concept → dissolved (85% sound-marker pockets)
  after sprite-visibility hygiene; survivors (23) too few to claim.
- Passage oracle via the game's own bot driver → produces no data for
  rotating sectors (driver refuses entry); negatives meaningless; blocker
  honestly kept rather than shipped around.
- Hand-assembled `sector_behavior` dicts for mechanisms → dead map (types
  never set); replaced by owning constructors; then depiction-style exhibits
  → rejected by owner walk; replaced by habitat rule + owning constructors.
- from/to marker model → wrong (state-anchored; loader law); one-sided
  boundary flags assumed → both dialects legal (owner oracle).
- Rest-pose-only validation → missed an inverting cover → swept-state gate;
  flag-set payload model → missed room-dragging vertices → motion-set gate;
  render/load-smoke acceptance → missed dead mechanisms → self-read gate;
  each gate was written to fail on its motivating defect first.
- Invented confidence scalar in tiering → removed (violates no-invented-
  numbers); replaced by rule traces.
- Bounding-box slot lattice → dropped 11/20 plants in a notched green →
  notched-outline lattice queued.
- Zoo topology forced toward campaign norms → structurally impossible for a
  gallery (mean_degree 2.09 vs 2.74); exemption drafted for owner instead of
  gaming loops.
- Street constructor across centreline seams → 8 refusals, 4 recorded failed
  workarounds → escalated as a plan decision (not machine-solvable).

---

## 7. CURRENT PROPOSED PLAN (non-authoritative)

The standing proposal — reassess freely:

1. Wave 1b (autonomous; prompt exists): zoo walk-fix four → city signage,
   storefront glass promotion, Aldermack curtains + light Link, green/lamp
   follow-ups, seam decision brief (analysis only).
2. Owner decides the seam question (paired half-roads / move seams / streets
   as first-class tree parts — the brief quantifies them); unblocked streets
   follow.
3. Wave 2: harbor (requires water-link promotion, queue rank 11).
4. One-language unification (tree as the only authoring source; zoo and
   facade-pilot migrated as the proof).
5. MechanismDecl (shared sentence schema for readers and writers; typed
   function taxonomy: narrative/secret/progression/ambush/furnishing/
   fixture/ergonomic-assist/workaround; mediations and slots as members;
   E2M2 composition patterns become its templates).
6. Phases 12–15 (recursive abstraction, design-intent synthesis, critics +
   scoped repair, quality diversity). Promotion queue ranks 4–17 as demand
   arises.

---

## 8. UNRESOLVED QUESTIONS

- The seam decision (a/b/c) — owner pending; blocks roads in 2 of 4
  districts.
- Owner-review queue items 2, 3, 4, 6 (see the queue file) — pending.
- Turnstile passage: no driver can walk a body through a rotating aperture;
  owner playtest of `projects/facade-pilot/level/turnstile.MAP` would settle
  it in seconds.
- The polygon sweep for swept-mechanism blocking states (5/628 decidable
  without it); the Modern/ tutorial dialect entirely unmined.
- 5/1780 unparallaxed sky ceilings in the campaign — unexplained.
- Whether the community novelty frontier (Phase 11's open half) is worth
  running before or after the city work.
- `mechanism.BLADE_PICNUM` (332) graded untested; `FENCE_PICNUM` (1044) has
  no anchor.
- Whether the tree language can express everything the flat projects need
  (unification risk untested).
- MechanismDecl's function taxonomy: is embedding+contents+dressing enough
  to assign it mechanically? (The E1M1 cross-cut says topology alone is not.)

---

## 9. RELEVANT FILES / COMMITS / COMMANDS / TESTS

**Single source of truth**:
`docs/llmapper_level_understanding_handbook/09_IMPLEMENTATION_ROADMAP.md`
(phase statuses, the mechanism-language grammar with all axes, owner
steering, E1M1 blueprints, promotion queue). Companions: `00`–`12` docs,
`AGENT_START_HERE.md`, `10_AGENT_EXECUTION_PROTOCOL.md` (conventions +
completion format).

**Knowledge**: `knowledge/blood/design/README.md` (table of all files),
`owner-anchors-v1.json`, `usage-kinds-v1.json`, `mechanism-curriculum-v1.json`,
`norms-v1.json`, `keys-v1.json`, `catalog-v1.json`.

**Key bloodmap modules**: `patterns.py` (corpus registry + unsigned mining),
`relations.py`, `anchors.py` (+contrasts), `effects.py` (4-plane mechanism
reading), `conditional.py` (blocking-aware conditional topology),
`mechanism.py` (constructors), `street.py`, `doors.py`, `aperture.py`,
`assembly.py`, `motion_sim.py`, `oracle.py`, `owner_anchors.py`,
`knowledge_index.py`, `tiering.py`, `reachability.py`, `levelprog.py` (tree),
`planar_layout.py` (flat), `lettering.py` (A–Z = 3808–3833).

**Projects**: `projects/blood-city/` (tree language; `reports/wave1-review.md`),
`projects/pattern-zoo/` (`registry.py`, `stalls.py`, `selfread.py`,
`sweep.py`), `projects/facade-pilot/`.

**Maps**: corpus layout under `maps/blood/` (local-only);
`maps/blood/mechanism/` = the tutorial curriculum (Vanilla/ = classic,
`#TYPE6xx`/`#SPR408` singles = per-primitive primers,
`STACKS3DSPACES-BADROR.map` = negative fixture, `xmapedit.pdf` = 981-page
manual); `maps/blood/mechanism/casket.map` = owner-authored planar-door
oracle; `maps/review/` = owner holding pen.

**Reports worth reading first**: `reports/owner-review-queue.md`,
`reports/blood-mechanism-curriculum.md`, `reports/E1M4-bundle.md`,
`reports/blood-corpus-health.md`, `reports/pattern-zoo-tour.md` +
`reports/owner-prescreen.html`, `projects/blood-city/reports/wave1-review.md`.

**Commands**:
`python -m unittest discover -s tests` (suite; corpus tests skip without
maps) · `python -m bloodmap corpus-manifest -o maps/blood/corpus.json` ·
`llmapper knowledge "<query>"` (retrieval) · `llmapper conditional …` ·
`python -m bloodmap corpus-tier …` · `python -m tools.render_precedent
<map> --sectors … -o <dir>` (observer renders; never launch NBlood).

**Commit trail by theme** (branch `blood-city-arcade`): `b3f2c9f` phases
0a–3 · `7193f9d` phase 4 + visibility hygiene · `1cc9689`/`c1b0f10`/`25a8196`
tiering landed + rerun · `00266a5` blocking-aware base + E1M4 bundle ·
`f10b430` bundle disagreements · `5e24c4d`…`a4da385` mechanism rework series
(curriculum `7503a83`, subgraph+arbitration `d007b49`, fixtures `eb3a687`,
state-anchored markers `a4da385`) · `ddfa3c1` the mossy-rock crate fix ·
`1d594a3` wave 1 (streets + green).
