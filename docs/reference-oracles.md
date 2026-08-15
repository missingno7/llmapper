# Local reference oracles

The project can use a local `reference/` tree for source cross-checks, format
probes, and independent runtime verification. The entire tree is ignored by Git
because it may contain commercial game data, executables, and nested upstream
repositories.

The expected local layout is:

```text
reference/
  blood/       legally obtained game data and local executables
  duke3d/      legally obtained Duke3D data and a local EDuke32 executable
  eduke32/     https://github.com/EDuke32/eduke32.git
  xmapedit/    https://github.com/NoOneBlood/xmapedit.git
  NBlood/      https://github.com/NBlood/NBlood.git
```

Clone the open-source references locally when needed:

```text
git clone https://github.com/NoOneBlood/xmapedit.git reference/xmapedit
git clone https://github.com/NBlood/NBlood.git reference/NBlood
git clone https://github.com/EDuke32/eduke32.git reference/eduke32
```

These inputs are evidence, not runtime dependencies. The Python package must keep
working without `reference/`, and ordinary tests use synthetic fixtures or the
separately ignored `maps/` corpus. When a verification claim depends on an
upstream checkout, record its commit in `reports/verification.md` so the result is
reproducible.

Never copy game resources, ART files, generated screenshots, executables, or nested Git
metadata into tracked paths. Only derived facts, focused tests, and documentation
belong in the repository.

## Bounded EDuke32 load smoke

`oracle-eduke32` validates a Duke v7 candidate structurally, copies it into an
isolated working directory, supplies a controlled config and autoexec, and launches
it through EDuke32's normal `-map` path. It requires the autoexec marker, Duke3D
game-data marker, user-map initialization marker, no fatal indicator, and a healthy
grace period. A baseline can be tested in the same environment.

```text
python -m bloodmap oracle-eduke32 work/DNE3L1-geometry-duke.MAP \
  --baseline maps/duke3d/E3L1.MAP \
  --eduke32 reference/duke3d/eduke32.exe \
  --game-dir reference/duke3d --seconds 3 \
  -o work/eduke-oracle.json
```

The harness deliberately names its engine configuration `llmapper.cfg`; EDuke32
reserves a config matching the MAP basename for map-local console commands.

## Bounded NBlood load smoke

`oracle-nblood` launches a candidate MAP and, preferably, an untouched baseline in
separate temporary working directories. It supplies a low-resolution local config,
disables autoloads, starts the MAP through NBlood's normal command-line path, and
requires three startup observations:

- the controlled autoexec reached the registered OSD environment;
- NBlood entered its normal game loop;
- MAP initialization processed the loaded level.

Each process must remain healthy for the requested grace period. The harness then
terminates that exact process and reports hashes, object counts, engine revision,
markers, and fatal indicators as JSON. On Windows the child is created hidden.

```text
python -m bloodmap oracle-nblood work/oracle_composed.MAP \
  --baseline maps/blood/E1M2.MAP \
  --nblood reference/blood/nblood.exe \
  --game-dir reference/blood \
  --seconds 6 \
  --work-dir work/oracle-harness \
  -o reports/nblood_oracle.json
```

The current composition fixture is reproducible from the ignored corpus:

```text
python -m bloodmap extract maps/blood/E1M1.MAP --sectors 0 \
  -o work/oracle/fragment.json
python -m bloodmap compose maps/blood/E1M2.MAP work/oracle/fragment.json \
  --x 1000000 --y 1000000 --channel-policy remap \
  --report work/oracle/composition.json \
  -o work/oracle/oracle_composed.MAP
```

The smoke is deliberately narrower than gameplay equivalence: it detects loader,
initialization, startup-crash, and early-exit failures, but it does not assert that
triggers, motion, combat, or progression behave identically.

## Deterministic trigger and motion oracle

`oracle-nblood-behavior` constructs a small source-backed scenario in two forms:
an authored baseline, and the same mechanism extracted as a `LevelFragment` then
inserted into a separate destination. In both maps, the player pushes a decoupled
XWALL, command `On` travels over user channel 100, and a type-600 XSECTOR moves its
ceiling from the off Z position to the on Z position.

The Windows-only harness launches each map independently, briefly foregrounds the
NBlood SDL window, supplies hardware scan-code input, and captures repeated views
before and after the action. It passes only when:

- every capture phase has exactly one unique image hash;
- the initial view remains unchanged for a no-input control interval;
- each map visibly changes after the controlled action;
- baseline and composed initial views are byte-identical; and
- baseline and composed final views are byte-identical.

Generated MAPs, screenshots, configs, and logs stay under the ignored work tree.
The tracked JSON report contains only derived identities, hashes, observations,
and the deterministic allocation report.

```text
python -m bloodmap oracle-nblood-behavior \
  --nblood reference/blood/nblood.exe \
  --game-dir reference/blood \
  --work-dir work/behavior-oracle \
  -o reports/nblood_behavior_oracle.json
```

This is a focused integration scenario, not a universal gameplay proof. It covers
the composition-sensitive wall trigger, channel dispatch, and sector Z-motion
path. Doors, lifts with markers, sprite-driven systems, combat, secrets, and level
progression need additional deterministic scenarios before broader claims.

## Single-map action oracle

`oracle-nblood-action` applies the same idle/action capture gate to an existing
MAP. It is useful for confirming that a scratch-authored switch is reachable from
the declared player start and produces a stable engine-visible response:

```text
python -m bloodmap oracle-nblood-action work/first-puzzle-room.MAP \
  --nblood reference/blood/nblood.exe \
  --game-dir reference/blood \
  --work-dir work/first-puzzle-room-action \
  -o reports/nblood_first_puzzle_room_action.json
```

The oracle proves a controlled Use input changed the rendered game state while
the process remained healthy. The LevelIR channel graph and portal profiles supply
the complementary evidence about the exact transmitter, receiver, and configured
door clearance; a screenshot difference by itself is not treated as proof of an
entire progression path.

## Real-map room attachment smoke

The attachment gate is reproducible with the ignored commercial corpus. It extracts
E1M1 sector 1, attaches its fragment wall 0 to E1M2 wall 138, automatically selects
three quarter-turns, aligns floors with a Z offset, and verifies the result against
the untouched E1M2 baseline:

```text
python -m bloodmap extract maps/blood/E1M1.MAP --sectors 1 \
  -o work/attachment-room.json
python -m bloodmap attach maps/blood/E1M2.MAP work/attachment-room.json \
  --destination-wall 138 --fragment-wall 0 --z -36864 \
  --channel-policy remap --report reports/attachment_fixture.json \
  -o work/real-attachment.MAP
python -m bloodmap oracle-nblood work/real-attachment.MAP \
  --baseline maps/blood/E1M2.MAP --nblood reference/blood/nblood.exe \
  --game-dir reference/blood --seconds 6 \
  -o reports/nblood_attachment_oracle.json
```

Only derived reports are tracked. The source maps and generated mashup remain in
ignored local paths.
