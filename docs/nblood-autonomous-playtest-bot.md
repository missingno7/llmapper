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

The bot now treats a mechanism as actionable only after it has aligned its
view and reached the approach envelope; Use is held there and Blood's own
`ActionScan` decides whether the wall or button is in range. Successful
push-door crossings mark the whole observed sector-to-sector route as opened,
so the reverse side is not immediately selected as a new frontier. Jump
recovery is generic: a stuck target gets bounded jump attempts followed by a
camera reorientation, and item observation accepts ordinary item sprites
without assuming an XSPRITE record.

## First supplied-data runtime check

On 2026-08-18, the modified executable was built and launched against the
workspace Blood data plus `maps/blood/E1M1.MAP` with a 10-second timeout and a
5-second stall watchdog. The run completed cleanly and reported `STALLED` after
5 simulated seconds, with two observed sectors and 13 trajectory samples. It
therefore validates the in-process launch, real map loading, GINPUT/FIFO frame
path, telemetry, trajectory, and demo output; it does not yet demonstrate map
completion.

## Door-interaction runtime check

On 2026-08-18, the current executable was run against the same supplied data
for 240 simulated seconds (`-bot_stall 45`). The strongest trace reached seven
visited sectors in the sequence `30 → 29 → 28 → 2 → 150 → 0 → 9`, with nine
observed sectors. It emitted `door_use_attempt` records while facing wall 1420
from sector 150, then recorded `door_traversed` at simulated second 31 for
`150 → 0`. This confirms the close-enough, camera-aligned interaction path in
the real engine. The run later returned through the small sector-9 dead end and
ended with the bounded failure `TIMEOUT` at 240 seconds; no level completion
was claimed.

The artifacts are `reference/blood/llmapper-bot-iter27.ndjson` (65,210 bytes),
`reference/blood/llmapper-bot-iter27.trajectory.ndjson` (51,873 bytes), and
`reference/blood/llmapper-bot-iter27.dem` (33,782 bytes). The normal NBlood
demo playback path was also launched successfully with the generated demo.
The next blocker is movement/frontier selection around the vertical lift and
its small dead-end branches, not the first door-use alignment.
