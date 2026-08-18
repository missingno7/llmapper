# NBlood autonomous playtest bot

The first bot lives inside the real `NBlood` runtime. Normal play is
unchanged when bot mode is disabled.

Build NBlood using its normal build target, then run from the directory that
contains the Blood data files:

```text
nblood.exe -bot -bot_timeout 1800 -bot_stall 45
```

The bot selects the original campaign E1M1 unless `-map` supplies a user map.
It uses the normal `GINPUT` → network FIFO → `ProcessFrame()` path, so the
same input is also eligible for NBlood's normal demo recorder. Bot mode runs
headless and advances simulation time without waiting for rendering.

Outputs default to:

```text
llmapper-bot.ndjson
llmapper-bot.trajectory.ndjson
llmapper-bot.dem
```

The event file is newline-delimited JSON with run, discovery, goal, key,
failure, completion, and summary records. The trajectory file contains
`game_time`, `x`, `y`, `z`, and `sector` samples. The demo is NBlood's normal
demo format and can be replayed in a visible run.

Useful switches are `-bot_telemetry`, `-bot_trajectory`, `-bot_demo`,
`-bot_timeout`, `-bot_stall`, and `-bot_realtime`.

The playtest knowledge model is observation-bounded: it records only the
current sector, geometrically visible portal openings and objects passing
NBlood's `cansee()` test. Navigation uses the discovered traversable graph;
the full loaded MAP is not used as a solution graph. Locked doors retain their
key requirement for later revisit after a key is acquired.

This initial vertical slice intentionally reports bounded failures rather than
claiming E1M1 completion before a real runtime run demonstrates it. The next
iteration should use the emitted demo and trajectory to improve generic
movement, mechanism interaction, and combat behavior exposed by that run.

## First supplied-data runtime check

On 2026-08-18, the modified executable was built and launched against the
workspace Blood data plus `maps/blood/E1M1.MAP` with a 10-second timeout and a
5-second stall watchdog. The run completed cleanly and reported `STALLED` after
5 simulated seconds, with two observed sectors and 13 trajectory samples. It
therefore validates the in-process launch, real map loading, GINPUT/FIFO frame
path, telemetry, trajectory, and demo output; it does not yet demonstrate map
completion.
