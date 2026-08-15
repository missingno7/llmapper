# Long-term roadmap

This roadmap preserves the project's central rule: evidence and roundtrip gates
come before abstraction or generation. Milestones are capability gates, not dates.

## Baseline — verified binary foundation

Status: complete for the supplied Blood v7 and Duke3D v7 corpora.

- explicit native parsers/writers, including Blood encryption, packed extras, and CRC;
- lossless `DiskMap`, `DukeDiskMap`, `LevelIR`, and shared `BuildIR`;
- byte-exact direct, native-IR, and shared-IR corpus roundtrips;
- mutation tests and structural validation;
- geometry/channel observations, statistics, SVG inspection;
- safe translation and quarter-turn rotation.

No later milestone may weaken these gates.

## Cross-game foundation — normalized BuildIR and measured conversion

Status: initial foundation complete.

- shared game-neutral geometry, topology, slope, lighting, and player-start model;
- native-lossless Blood and Duke adapters;
- shared translation and quarter-turn rotation;
- E3L1/DNE3L1 differential inference independent of object indices;
- explicit geometry-only, conservative semantic, and fail-closed strict policies;
- bidirectional outputs that reparse, validate, and initialize in NBlood/EDuke32;
- machine-readable fidelity reports with unsupported mechanisms called out.
- E3L11-regressed semantic lowering for doors, lifts, rotating/sliding sectors,
  water, teleporters, conveyors, switches, keys, exit, population, lighting, and
  CRACK/SE13 destruction chains;
- ART-driven material matching constrained to role-equivalent Blood map surfaces;
- source-backed Duke mechanism inventories and a corpus query command, rather than
  hardcoded E3L11 controller indices.

Next gates:

- broaden hand-converted-map evidence beyond one pair;
- broaden role-aware ART similarity into material-family and neighborhood profiles;
- add palette, translucency, and sprite-size normalization;
- model common concepts such as doors, lifts, switches, keys, exits, secrets, and
  spawn conditions above each game's native controller graph;
- add deterministic behavior oracles for mapped mechanisms in both games;
- introduce game-neutral room fragments only after semantic dependency closure is
  as explicit as Blood `LevelFragment` closure.

## Milestone 1 — extraction and reference remapping

Goal: select sectors and obtain a self-describing fragment without corrupting
relationships.

Status: implemented for extraction, dependency classification, compact index maps,
and exact same-source reinsertion. Cross-map allocation remains Milestone 2.

Deliverables:

- `LevelFragment` containing selected sectors, owned walls, contained sprites, and
  extended records;
- reusable sector/wall/sprite/extra index maps;
- explicit classification of every reference as internal geometry, external
  geometry, external trigger, marker/owner, or system/global;
- policies for closing or retaining boundary portals;
- fixtures covering holes, multiple loops, portals, markers, and stale redundant
  owner fields;
- extraction reports that list unresolved external dependencies.

Gate: extraction followed by reinsertion at the same location can reproduce the
source structures exactly, and no reference is silently dropped.

## Milestone 2 — deterministic fragment composition

Goal: place multiple verified fragments in one level without raw concatenation.

Status: deterministic insertion, behavior-closed extraction, object/extra
allocation, user-channel collision handling, placement transforms,
unresolved-dependency reports, and explicit portal connection are implemented.
Equal-length room walls can be automatically attached; arbitrary separated and
unequal-width walls can be joined by collision-checked routed corridors/stairs.
Allocation-aware composition recipes replay multi-map assemblies. Reproducible
baseline/candidate NBlood load smoke and a deterministic wall-trigger/channel/Z-motion
behavior scenario pass. Broader layout and behavior coverage remains before
composition is considered production-complete.

Deliverables:

- collision-free object and extra-index allocation;
- channel inventory and collision detection;
- source-derived handling of reserved/special Blood channels;
- translation/rotation during insertion through the existing transform machinery;
- explicit connector API for selected boundary walls;
- automatic exact-wall room attachment with deterministic placement reports;
- generated tapered corridors and bounded-height stair connections;
- new-vs-existing and pathway self-overlap rejection;
- gameplay-dependency closure and replayable composition recipes;
- transform-relative player-start placement with geometric validation;
- validation of portal reciprocity, marker ownership, and trigger reachability.

Gate: composed fixtures write, reparse, validate, load into NBlood, and preserve
each fragment's internal behavior under oracle-backed integration tests. The first
behavior scenario proves exact before/after visual equivalence for a composed
wall-push trigger driving sector Z motion; marker-, sprite-, and progression-driven
scenarios remain.

The E1M2 remix recipe now demonstrates controlled room reordering at LevelIR level:
four behavior-closed rooms are rotated/repositioned into a new opening sequence,
joined by bounded stairs, assigned a transformed local player start, and returned
to the preserved base progression. Static reachability and NBlood load gates pass.

## Milestone 3 — semantic pattern library

Goal: answer questions such as “show original keyed-door implementations” from
derived evidence rather than hardcoded map lore.

Status: implemented foundation. The LevelIR-native observation contract indexes
sectors, geometry, contents, connectors, type/tile inventories, channel
endpoints, active trigger modes, selection dependencies, and a grounded Design
Understanding fingerprint. Blood and Duke3D map directories can be indexed and
searched by multi-dimensional similarity, source mechanism, or explicitly
labeled soft motifs. Source-backed pattern naming and finer region extraction
remain.

Deliverables:

- indexed corpus observations for object types, channels, commands, keys, and
  trigger combinations;
- structural subgraph fingerprints;
- explainable queries that cite source map/object IDs;
- verified/derived/heuristic provenance on region and level observations;
- design fingerprints covering topology, space, architecture, visual proxies,
  gameplay inventories, and source mechanism evidence;
- pattern extraction for doors, switches, lifts, traps, secrets, spawn systems,
  and progression gates only after their semantics are source-verified.

Gate: every named pattern links back to concrete IR fields and original examples;
heuristics are labeled and never overwrite disk truth.

## Milestone 4 — constrained editing operations

Goal: support encounter and progression edits with predictable invariants.

Candidates include sprite replacement, difficulty/mode filters, key/channel
rewiring, texture substitutions, sector height edits, and connector placement.

Gate: each operation declares preconditions, touched fields, expected diagnostics,
and mutation/property tests. Operations fail closed when semantics are uncertain.

## Milestone 5 — constructive level assembly

Goal: create complete maps from validated authored fragments and explicit design
constraints, without introducing an LLM dependency into the core library.

Status: started. The deterministic `LevelBuilder` creates empty v7 levels,
clockwise polygon sectors, exact portals, sprites, extended behavior records, and
validated player starts. Portal profiles reject narrow connections and distinguish
closed-at-rest moving doors from their configured-open clearance. The first
scratch-authored two-switch puzzle room writes, reparses, loads, and responds to
controlled Use-key interaction in NBlood. Multi-room progression and richer
construction recipes remain.

Deliverables:

- new-level allocator and deterministic defaults derived from references;
- explicit polygon/portal/sprite/behavior allocation with construction-time guards;
- minimum-width and dynamic-opening portal profiles;
- topology and progression constraint model;
- spawn/start/exit and reachability checks;
- channel namespace planning;
- gameplay-oriented linting distinct from structural validation;
- export reports explaining every constructed relationship.

Gate: generated maps pass writer/reparse/structural validation and load in an
independent Blood implementation used only as a development oracle.

## Milestone 6 — LLM client layer

Goal: let an LLM inspect and request operations through small, deterministic tool
contracts.

The LLM remains a client. It receives concise observations, proposes operations,
and gets validation/diff results. It never edits binary blobs, invents raw packed
fields, or bypasses gates.

Gate: the same workflows remain fully usable without an LLM, and every agent action
can be replayed from a machine-readable operation log.

## Cross-cutting work

- Expand historical-version support only with evidence and fixtures.
- Maintain schema migrations and compatibility policy.
- Add independent XMAPEDIT/NBlood differential probes for disputed semantics.
- Fuzz parsers and validators with bounded synthetic corruptions.
- Keep the dependency footprint minimal and the core deterministic.
- Document newly understood fields in code, focused tests, and technical notes.

## Explicit non-goals

- No raw map-fragment concatenation.
- No automatic “repair” during lossless parsing.
- No 3D game renderer in this project.
- No map generation before composition and validation gates are proven.
- No LLM dependency in the parser, writer, IR, or validator.
