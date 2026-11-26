# llmapper

`llmapper` is a system in which AI agents author levels for Build-engine games
(Blood first), and get better at it with every level. It has four parts, and
keeping them apart is the point:

| Part | Where | What it holds |
| --- | --- | --- |
| the library | `bloodmap/` | lossless formats, geometry, sensors that read a map, constructors that write one, the passes every level's map goes through (`bloodmap.finish`), the gates that refuse a bad one |
| the tools | `tools/` | the library run over the corpus or a level: look something up, study a kind of place, look at a level, lint it, hand it to blind readers |
| what is known | `knowledge/blood/` | the catalog of tiles, parts and wiring, studies of how Blood built a kind of place, tile contexts, and the findings: what building taught us, each saying how it is known |
| the levels | `projects/<name>/` | one directory a level: its brief, its own modules, poses, tests, reports and critique rounds. `python -m tools.project list` |

A level uses everything above it and owns only its own design. What it learns
about the game goes back onto the shared shelves, so the next level starts with
it (`AGENTS.md`, "Give back what you learn"). Gravesend
(`projects/blood-city`), a city of 1,800 sectors, is the largest level so far;
`projects/cold-store` is a small one begun from the starter.

```text
python -m tools.project new my-level --title "My Level"   # a level that builds as it stands
python projects/my-level/level/build.py                   # compile, align, gates (four of them refuse the map), light, write
python -m tools.project status my-level                   # every open item and what to do
python -m tools.look my-level --set start -o work/look    # frames, as the game shows it
python -m tools.catalog find <words>                      # look anything up before building it
python -m tools.suite                                     # the tests: tests/ (library) and projects/*/tests
```

Under all of it is a binary-first foundation: Blood v7 (`0x0700`), classic Duke
Nukem 3D v7 and classic Doom / Doom II maps are read and written exactly.

1. `DiskMap`, `DukeDiskMap`, and `DoomDiskMap` preserve each game's native file
   exactly. Doom does **not** live inside `BuildIR`.
2. `BuildIR` exposes common Build sectors, walls, sprites, topology, slopes,
   lighting, and player start through one JSON contract while retaining a
   lossless native extension.
3. `SemanticLevel` / `SemanticMechanism` sit above native encodings so a keyed
   door can be recognized in Doom, reasoned about without linedef numbers, and
   lowered into Blood XSECTOR motion.
4. `LevelIR` is the Blood authoring layer the level programs compile to.

Neither writer caches the original file blob. The local corpora pass byte-exact
native and `BuildIR` roundtrips: the 102 named Blood maps (campaign, BloodBath,
curated, conversions) and 46 Duke3D maps, as of 2026-11-19. The commercial maps
and art are not distributed (`maps/README.md`).

## Where to start

| You are about to... | Read |
| --- | --- |
| start a session as an agent | [AGENTS.md](AGENTS.md) -- the lookups, the rules, the loop, what not to do |
| start a level | `python -m tools.project new <name> --title "..."`, then the project's own `README.md` |
| build or change a map | [what is in the toolkit](docs/toolkit-index.md) -- one page, "reach for X, not Y" |
| look something up about Blood before building it | [the library](knowledge/blood/LIBRARY.md) -- tiles, places, studies, ideas |
| add a module, a sensor or a tool | [architecture](docs/architecture.md) -- which module owns which kind of fact |
| find out whether something already exists | [the module map](docs/module-map.md) -- every library module and tool, by layer |
| change parsing, conversion or a gate that judges a level | [CONTRIBUTING](CONTRIBUTING.md) -- the gates each kind of change must pass |

The corpus is never globbed. `bloodmap.corpus` knows where every map lives:
`campaign_maps()` for the original campaign, `named_maps()` for everything a
bare filename names, `corpus_map_path("E3M1")` for one map.

## Quick start: formats, conversion and analysis

Python 3.10 or newer is sufficient; there are no runtime dependencies.

```text
python -m bloodmap roundtrip-all maps/blood        # the named maps; --recursive adds the bulk community set
python -m bloodmap roundtrip-all maps/duke3d
python -m bloodmap validate maps/duke3d/E3L1.MAP
python -m bloodmap dump-build maps/duke3d/E3L1.MAP -o work/E3L1.build.json
python -m bloodmap build-build work/E3L1.build.json -o work/E3L1.rebuilt.MAP
python -m bloodmap transform maps/duke3d/E1L1.MAP -o work/turned.MAP rotate --turns 1
python -m bloodmap compare-e3l1 --duke maps/duke3d/E3L1.MAP \
  --blood maps/blood/conversions/DNE3L1.MAP -o work/e3l1-differential.json
python -m bloodmap design-fingerprint maps/blood/campaign/E1M1.MAP --sectors 12,13 \
  -o work/E1M1.design.json
python -m bloodmap design-index maps/blood -o work/blood.design-index.json
python -m bloodmap design-search work/blood.design-index.json \
  --motif repeated-bays --limit 5
python -m bloodmap analyze-space maps/blood/campaign/E1M1.MAP --sectors 12,13 \
  -o work/E1M1.spatial.json
python -m bloodmap decompile maps/blood/campaign/E1M1.MAP \
  -o work/E1M1.level-source.json --python work/E1M1.level-source.py
python -m bloodmap compile-source work/E1M1.level-source.json \
  -o work/E1M1.rebuilt.MAP
python -m bloodmap inspect-space maps/blood/campaign/E1M1.MAP --sectors 12 \
  --corpus work/blood.spatial-corpus.json
python -m bloodmap compare-space maps/blood/campaign/E1M1.MAP --from 12 --to 18
python -m bloodmap design-index maps/duke3d --include-spatial \
  -o work/duke.spatial-index.json
python -m bloodmap design-search work/duke.spatial-index.json \
  --region-kind mechanism_region --limit 5
python -m bloodmap probe-route maps/blood/campaign/E1M1.MAP \
  --from-sector 22 --to-sector 0 -o work/E1M1-route.json
python -m bloodmap project-init projects/crypt --name "Monastery crypt"
```

The August authoring loop (an authored candidate compiled, gated, decompiled
and probed as one evidence packet) is retired; its record is
[docs/history/authoring-loop.md](docs/history/authoring-loop.md) and the six-iteration
[cliffside monastery pilot](projects/reasoned-authoring-v1/reports/comparison.md).

A level can also be written and read as a tree of named parts, each owning its
own geometry in its own coordinates, its own surfaces, its structures and its
details:

```text
python -m experiments.nested_authoring --tree
python -m experiments.nested_authoring --room lobby
python -m tools.emit_level_program maps/blood/campaign/E2M3.MAP --art-dir reference/blood     --names projects/e2m3-decompiled/references/names.json -o work/E2M3.py
```

See [level programs](docs/level-programs.md) and
[E2M3 decompiled](projects/e2m3-decompiled/README.md).

Three campaign maps are read further, layer by layer, into a fact store where
every derived fact names the reader and the facts it came from. One stage
program serves all of them:

```text
python -m tools.decompile_stages.run_all projects/e3m1-decompiled
python -m tools.decompile_stages.query projects/e3m1-decompiled
```

See [E3M1 decompiled](projects/e3m1-decompiled/README.md).

A source node can ask what it actually looks like. The XMapEdit fork builds a
small headless observer that renders a pose and reports what the renderer
painted, joined back to the node that owns it:

```text
mingw32-make -C xmapedit/src_blood/observe
python -m tools.observe program experiments.nested_authoring -o work/obs --structures
python -m tools.observe decompiled maps/blood/campaign/E2M3.MAP \
  --hierarchy projects/e2m3-decompiled/hierarchy.json -o work/obs-e2m3
```

The product is JSON; a frame is written only where one is asked for. NBlood
stays the runtime oracle -- does it load, does the switch fire, is it playable --
and is no longer driven with injected keys to photograph a room. See
[structured visual observation](docs/visual-observation.md).


Cross-game conversion requires an explicit fidelity policy:

```text
python -m bloodmap convert maps/duke3d/E3L1.MAP --to blood \
  --policy geometry-only --report work/E3L1-to-blood.json \
  -o work/E3L1-geometry-blood.MAP
python -m bloodmap convert maps/blood/conversions/DNE3L1.MAP --to duke3d \
  --policy semantic --report work/DNE3L1-to-duke.json \
  -o work/DNE3L1-semantic-duke.MAP
python -m bloodmap doom-corpus maps/doom/doom.wad -o work/doom-corpus.json
python -m bloodmap convert-doom maps/doom/doom.wad --map E1M1 \
  --report work/E1M1-BLOOD.report.json -o work/E1M1-BLOOD.MAP
```

`geometry-only` preserves normalized geometry, topology, slopes, player start,
and the supported lighting model; it intentionally removes sprites, native tags,
controllers, and triggers. `semantic` additionally enables only the few mappings
whose evidence and classification are explicit in the report. `strict` refuses a
cross-game export while any asset or gameplay mechanism is unresolved.

E3L11 and E3L3 are the regression boards for the playable Duke-to-Blood conversion
profile. DNE3L3 is a Blood reimagination of E3L3 used as mechanism vocabulary, not
as a geometry oracle. DWE2M3 is a Blood space-station style reference for E2L1:
same mood, not the same geometry. The profile uses local ART sets for role-aware
surface matching, optionally constrained to one Blood style map, translates the
gameplay population by role, and lowers supported Duke mechanisms to native Blood
records:

```text
python -m bloodmap convert-playable maps/duke3d/E3L11.MAP \
  --duke-art reference/duke3d --blood-art reference/blood \
  --blood-maps maps/blood --report work/E3L11-BLOOD.report.json \
  -o work/E3L11-BLOOD.MAP
python -m bloodmap convert-playable maps/duke3d/E3L3.MAP \
  --duke-art reference/duke3d --blood-art reference/blood \
  --blood-maps maps/blood --report work/E3L3-BLOOD.report.json \
  -o work/E3L3-BLOOD.MAP
python -m bloodmap convert-playable maps/duke3d/E2L1.MAP \
  --duke-art reference/duke3d --blood-art reference/blood \
  --blood-maps maps/blood --style-map maps/blood/curated/DWE2M3.MAP \
  --report work/E2L1-BLOOD.report.json \
  -o work/E2L1-BLOOD.MAP
python -m bloodmap compare-e3l1 --duke maps/duke3d/E3L3.MAP \
  --blood maps/blood/conversions/DNE3L3.map -o work/e3l3-differential.json
```

The profile converts doors, lifts, rotating/sliding/swinging sectors, paired water
links, teleporters, hatches, conveyors, touchplates, keyed switches, switchable/ambient
lights, CRACK/SE13 destruction chains, weapons, inventory, enemies, and the
normal exit. Unsupported choreography remains explicit in the report. This is a
playable approximation, not a claim of exact game equivalence.

Blood-specific authoring remains available through `LevelIR`:

```text
python -m bloodmap observe maps/blood/campaign/E1M1.MAP --sectors 12,13 -o work/room.json
python -m bloodmap extract-closed maps/blood/campaign/E1M1.MAP --sectors 12,13 -o work/fragment.json
python -m bloodmap attach maps/blood/campaign/E1M2.MAP work/fragment.json \
  --destination-wall 120 --fragment-wall 3 -o work/attached.MAP
python -m experiments.bb2_reconstruction_v3 --report reports/BB2-v3-build-report.json \
  -o work/BB2-semantic-reconstruction-v3.MAP
python -m bloodmap geometry-audit work/BB2-semantic-reconstruction-v2.MAP \
  --markdown work/BB2-v2-geometry-audit.md
python -m bloodmap pattern-mine --maps maps/blood --population blood-bloodbath \
  -o work/blood-pattern-unsigned-bloodbath.json
python -m bloodmap understand maps/blood/campaign/multiplayer/BB6.MAP --multiplayer-only \
  --patterns knowledge/blood/design/catalog-v1.json \
  -o work/BB6-understanding.json
```

See [authored-geometry.md](docs/authored-geometry.md) for the planar compiler and
strict authored-geometry gate. `geometry-audit` on a frozen MAP is fail-closed
without blueprint declarations; compile-time validation passes the declared
water/partition/gated specials. Quality-diversity search is a second-order layer
and may only archive candidates that pass that gate.

Independent local engine load checks are optional:

```text
python -m bloodmap oracle-eduke32 work/DNE3L1-geometry-duke.MAP \
  --baseline maps/duke3d/E3L1.MAP --eduke32 reference/duke3d/eduke32.exe \
  --game-dir reference/duke3d -o work/eduke-report.json
python -m bloodmap oracle-nblood work/E3L1-geometry-blood.MAP \
  --baseline maps/blood/conversions/DNE3L1.MAP --nblood reference/blood/nblood.exe \
  --game-dir reference/blood -o work/nblood-report.json
```

Run all tests with:

```text
python -m tools.suite              # every test module, a process each: about a minute
```

## Documentation

- [Architecture and invariants](docs/architecture.md)
- [The module map: every module and tool, one line each](docs/module-map.md)
- [What is in the toolkit, and when to reach for it](docs/toolkit-index.md)
- [The library of Blood: tiles, places, studies, ideas](knowledge/blood/LIBRARY.md)
- [Level programs: hierarchical, editable level source](docs/level-programs.md)
- [Structured visual observation through XMapEdit](docs/visual-observation.md)
- [Cliffside monastery authoring pilot](projects/reasoned-authoring-v1/reports/comparison.md)
- [Design Understanding and grounded retrieval](docs/architecture.md#design-understanding)
- [Multi-view spatial understanding](docs/spatial-understanding.md)
- [Experience Atlas and persistent level projects](docs/experience-atlas.md)
- [Shared BuildIR contract](docs/build-ir.md)
- [Classic Doom maps and engine-neutral mechanisms](docs/doom.md)
- [Player-relative spatial presentation](docs/player-space.md)
- [Material evidence and discovered annotation](docs/materials.md)
- [Map understanding sensors (types, contents, sight, exposure, morphology)](docs/map-understanding.md)
- [Design-pattern discovery](docs/design-pattern-discovery.md)
- [Authored planar geometry](docs/authored-geometry.md)
- [Scratch construction](docs/construction.md)
- [Object placement and spatial anchors](docs/object-placement.md)
- [Single-player understanding](docs/single-player-understanding.md)
- [Door affordances](docs/door-affordances.md)
- [BB2 deathmatch understanding experiment (archived)](reports/archive/BB2-understanding.md)
- [BB2 semantic roundtrip (archived)](reports/archive/BB2-semantic-roundtrip.md)
- [BB6 pattern-aware understanding (archived)](reports/archive/BB6-understanding.md)
- [BB6 semantic roundtrip (archived)](reports/archive/BB6-semantic-roundtrip.md)
- [E2M2 single-player understanding (archived)](reports/archive/E2M2-understanding.md)
- [SP-progression-v1 independent understanding (archived)](reports/archive/SP-progression-v1-understanding.md)
- [Duke3D v7 format support](docs/duke3d.md)
- [Cross-game normalization and conversion](docs/conversion.md)
- [LevelIR authoring](docs/level-ir.md)
- [Corpus policy](docs/corpus.md)
- [Blood v7 MAP format](docs/format.md)
- [Room fragments](docs/fragments.md) and [fragment composition](docs/composition.md)
- [Level decompiler](docs/level-decompiler.md)
- [Duke mechanisms lowered to Blood](docs/duke-blood-mechanisms.md) and [Duke's moving sectors](docs/duke-moving-sectors.md)
- [The NBlood playtest bot](docs/nblood-autonomous-playtest-bot.md)
- [Local reference oracles](docs/reference-oracles.md)
- [History: the old roadmap, handbook and audits](docs/history/README.md) (nothing there describes the present)
- [Verification as of September (archived)](reports/archive/verification.md)
- [E3L11 playable conversion summary](reports/e3l11_playable_summary.json)

Commercial game data, maps, executables, ART files, and upstream reference
checkouts are intentionally ignored. See [maps/README.md](maps/README.md) and
[docs/reference-oracles.md](docs/reference-oracles.md) for the expected local
layout.
