# BloodForge and llmapper: what to take, what to leave

2026-11-17. Read from source in both trees (`D:\Games\DOS\bloodforge\src\bloodforge`,
about 7,000 lines and 26 test files; llmapper's `bloodmap/`, `tools/`,
`projects/blood-city/`), not from either README.

## What each is

**BloodForge** is a small evidence pipeline. Every claim about a map is tied
to file hashes and stated as an explicit true/false flag. It has no renderer
of its own (it shells out to llmapper's `xmapedit-observe.exe`), no
construction vocabulary beyond stairs, rectangular areas, landings and
connections, and no runtime beyond "the engine stayed alive for five
seconds". Slopes, room-over-room, Blood's extended records, mechanisms and
collision are all unsupported. Zero recipes have reached `verified`.

**llmapper** is a large authoring system: an editable level tree, a planar
compiler, layers, apertures, doors, lighting, a rule engine, a headless
observer that reports post-occlusion painted pixels per native object, corpus
mining, and a city of 270 sectors built with it. Its weakness, by its own
handoff, is the opposite one: a great deal can be built and little is held to
account. Blood City's refinement log is a long run of "found / fixed"
entries, and none of them states beforehand what the fix was expected to
change.

## Where BloodForge is actually better

| BloodForge does | In the code | llmapper before today |
|---|---|---|
| Hashes every input and output of a tool run | `observe.observe_map` hashes the MAP, the executable and the asset tree before and after | `look.py` wrote frames beside a path the next build overwrites; a frame could not be tied to the map it showed |
| Freezes predictions before running | `tools/spatial_demo.py:81-110` writes `predictions-before-edits.json`, then judges per key | never; "a fix you did not re-render did not happen" is the nearest rule |
| States what a result does NOT show | a `claims` dict of booleans on every report | prose caveats, restated per manifest |
| Edits with preconditions and an audit | `spatial_edits.intervene`: `expect`, an allowed-field list, invariants | `fingerprint.py` covers the restructure case; nothing for an intended change |
| Keeps a control | the shade-only case that must change appearance and nothing else | never |
| Holds out evidence | `learning.split_groups`, frozen denominator | corpus statistics are mined and applied on the same maps |

## What was taken, and where it landed

Four of these, each because the church experiment needed it, none as a new
subsystem:

1. **A run keeps the map it looked at.** `look.py` now copies the MAP into
   the run directory as `observed.MAP`. Found the hard way: the first judge
   run compared "before" against a path that had already been rebuilt.
2. **Predictions written first, then scored.**
   `projects/blood-city/experiments/church-skyline/hypothesis.json` was
   written before the first source edit; `tools/judge_experiment.py` hashes
   it into `result.json` beside every map and frame hash. Two of seven
   predictions failed and are recorded as failures.
3. **Controls.** The cemetery frame and five interior frames were predicted
   pixel-identical and were (0 changed pixels), which is what makes the
   claim "nothing else moved" a measurement.
4. **A `claims` block.** `walk_static.py` writes
   `a_player_was_moved: false, the_engine_was_run: false,
   collision_was_tested: false` at the top of its output.

And one from the other direction: the **status ladder with supersession**.
BloodForge declares `superseded / verified / rejected` and never writes any
of them. `knowledge/blood/design/visual-construction-atlas-v1.json` uses a
shorter ladder (`hypothesis, observed_once, transferred, refuted`) and
actually has records at three of the four rungs.

## What was not taken, and why

- **The SQLite stores and content-addressed artifact tree**
  (`store.py`, a 1.25 GB `knowledge.db`). llmapper's knowledge is versioned
  JSON in git with provenance per file; hashes inside an experiment's
  `result.json` give the same guarantee at the scale this work has.
- **The scene/revision model** (`scene.SceneChange`,
  `workspace.apply_scene_changes`). llmapper's `LevelProgram` tree is the
  editable source and is far richer; optimistic concurrency solves a problem
  a single-author build script does not have.
- **`runtime.test_load` and `bot_diagnostic.py`.** The first is llmapper's
  own `oracle-nblood` with an asset copy added. The second is 361 lines of
  careful wrapping round a bot whose real runs produced "312,500 samples
  stuck in sector 0, or a single sample". Neither moves a player under
  control. BloodForge's own ledger lists a deterministic movement harness as
  open.
- **The held-out split.** Valuable, and not needed by anything done here.
  It becomes needed the day a construction rule is *learned* from the corpus
  and then scored on it. The atlas says so on the records it would apply to.
- **`spatial.analyze_space`.** llmapper's `player_space`, `sight`, `layers`
  and the observer's own occlusion already answer these.

## What neither has

Trustworthy traversal. See
`projects/blood-city/reports/visual-survey-2026-11-17.md`, "Traversal".
