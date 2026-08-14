# Local reference oracles

The project can use a local `reference/` tree for source cross-checks, format
probes, and independent runtime verification. The entire tree is ignored by Git
because it may contain commercial Blood data and nested upstream repositories.

The expected local layout is:

```text
reference/
  blood/       legally obtained game data and local executables
  xmapedit/    https://github.com/NoOneBlood/xmapedit.git
  NBlood/      https://github.com/NBlood/NBlood.git
```

Clone the open-source references locally when needed:

```text
git clone https://github.com/NoOneBlood/xmapedit.git reference/xmapedit
git clone https://github.com/NBlood/NBlood.git reference/NBlood
```

These inputs are evidence, not runtime dependencies. The Python package must keep
working without `reference/`, and ordinary tests use synthetic fixtures or the
separately ignored `maps/` corpus. When a verification claim depends on an
upstream checkout, record its commit in `reports/verification.md` so the result is
reproducible.

Never copy game resources, generated screenshots, executables, or nested Git
metadata into tracked paths. Only derived facts, focused tests, and documentation
belong in the repository.

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
  --baseline maps/E1M2.MAP \
  --nblood reference/blood/nblood.exe \
  --game-dir reference/blood \
  --seconds 6 \
  --work-dir work/oracle-harness \
  -o reports/nblood_oracle.json
```

The current composition fixture is reproducible from the ignored corpus:

```text
python -m bloodmap extract maps/E1M1.MAP --sectors 0 \
  -o work/oracle/fragment.json
python -m bloodmap compose maps/E1M2.MAP work/oracle/fragment.json \
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
