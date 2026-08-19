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
`-bot_timeout`, `-bot_stall`, `-bot_realtime`, and `-bot_visible`.

For a human-debugging run, add `-bot_visible` to watch the bot in the normal
NBlood window. This automatically uses realtime pacing; the accelerated,
headless behavior remains the default for `-bot`.
The initial coffin escape can take several realtime seconds, so repeated jump
attempts during that opening sequence are expected.

To inspect a recorded run, start NBlood from the Blood data directory and pass
the demo file to the normal playback path:

```text
nblood.exe -usecwd -nosetup -playback llmapper-bot.dem
nblood.exe -usecwd -nosetup -playback llmapper-bot.dem -playback_speed 4
```

`-playback_speed` accepts values from 1 through 8. The default is normal
speed; higher values process more recorded frames per display tick. Playback
uses the ordinary visible NBlood renderer, and Escape can be used to stop it.
Bot demos containing an external map path register that map automatically
during playback.

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

## Exploration model

The bot follows one branch into new territory and remembers what it passes.
All unresolved work lives in a single ledger of *opportunities*: frontiers
into unentered space, locked continuations, known mechanisms, pickups, and
local space that has been entered but not yet observed. Selection is one
ranked choice per committed mission, not a per-tick re-evaluation of every
affordance, and each choice carries a reason that appears in telemetry:

```text
CONTINUE_FORWARD              keep pushing the branch the bot is on
RETURN_FOR_KEY_DOOR           a held key just made a known door actionable
RETURN_TO_UNEXPLORED_BRANCH   this branch ended; go back to unresolved work
SOLVE_BLOCKING_OBSTACLE       the way forward is blocked; work the obstacle
REOPEN_ROUTE_TO_OBJECTIVE     the route to that work passes a shut connection
CONSUME_OPENED_ROUTE          go through what was just deliberately opened
EXPOSE_UNSEEN_LOCAL_SPACE     look at reachable space never observed
COLLECT_ON_THE_WAY            pick up something underfoot
RETRY_DORMANT_OPPORTUNITY     nothing is live; re-arm the oldest dormant work
```

Ordering is depth-first: a deeper pending frontier continues the branch
already being followed, and popping to the next-deepest is a natural
backtrack rather than a random hop. Nothing is ever permanently retired.
Work that fails goes *dormant* with a growing cooldown and is re-armed
later; a key acquisition clears the dormancy of every door that wanted it.

Entering a sector is not the same as having explored it. A Build sector can
be large and concave, and a door or switch can sit around a corner inside a
room the bot has already stood in, so the bot tracks which standable cells it
has actually seen and treats unseen reachable space as real unresolved work.

## Dynamic topology

"Blocked right now" is not "there is no route here". Blood builds doors out
of moving sector and wall geometry, so a closed door can be geometrically
indistinguishable from a wall. The bot separates three things:

* **structural knowledge** — a boundary exists here, and what mechanism, if
  any, is attached to it. This survives the mechanism opening and closing.
* **current state** — whether the player can pass *now*. Navigation uses
  only this.
* **affordance** — whether a legitimate action could change that state, read
  from Blood's own records (`XWALL.triggerPush`, `XSECTOR.Push`/`Wallpush`,
  `XSPRITE.Push`, key locks). `ActionScanPreview` remains the authority on
  whether the current pose can actually operate it.

A boundary that is blocked *and* has no known affordance from this side is
recorded once as `boundary_inert` and left alone. A boundary that is blocked
but has a mechanism is progression work. Reachability follows shut
connections the bot knows how to reopen, at extra cost, so work behind an
auto-closing door does not vanish from the ledger the moment it shuts; when a
route is gated that way the mission becomes reopening the gate.

## Navigation mesh

Sectors are discretised into a uniform grid rather than triangulated. Build
sectors routinely contain inner wall loops, and per-loop ear clipping
silently fragments exactly those rooms — an early run produced seven
disconnected walk areas across ten physically connected sectors. Grid
adjacency is also an O(1) lookup instead of an O(cells^2) edge search.

Cells sit at the grid centre where the player can stand there. A sector whose
walkable band is narrower than the grid — a 512-unit corridor leaves barely
more than the player's own clip diameter — is rebuilt with the most open
point sampled inside each square, reported as
`nav_sector_too_tight_for_grid`. Links are confirmed with the engine's own
ray test, because a wall lying exactly between two cell centres puts the
midpoint on the wall, where `inside()` is ambiguous.

Wall coordinates are part of the topology signature: a mesh that ignores
where the walls are cannot notice that a passage appeared when a mechanism
slid them apart.

### Player width

A cell exists only where the player's whole clip radius clears the sector's
walls. Demanding less lets the bot plan routes between bars it can never fit
past, which is a failure mode that looks like a stuck bot rather than a bad
plan. The relaxed passes below that exist to keep a *visited* sector
represented at all, so they say nothing about whether a body fits; a sector
is judged to admit the player only from the margin-respecting passes, plus a
fine sweep for sectors the 256-unit grid is simply too coarse for.

Width is structural, headroom is not. A sector too narrow for the body is
scenery — a wall with a seam in it — and a frontier into one is reported as
`boundary_too_narrow` and never pursued. A sector that is merely *short* is a
shut door, and belongs to current state, not to structure.

A sector too thin to hold a standable square but wide enough for the body — a
step, a ledge, a door track — gets a transit cell at each of its doorways so
routes can pass through, reported as `nav_sector_transit_only`.

## Moving geometry

`XSECTOR.state` does not say which way a sector is travelling. `SetSectorState`
runs only when the travel *finishes*, so throughout the motion `state` still
names where the sector came from. Read the direction from the sign of the
sector's live entry in `gBusy` instead — the same value the engine steps.
Getting this backwards inverts every verdict about moving geometry: opening
doors look like closing ones and are waited out instead of walked through,
and closing doors look safe to enter.

Travel time comes from the same records: `12 * busyTime` ticks to cross, and
`12 * waitTime` ticks of hold before an auto-closing door reverses.

## What the bot is allowed to conclude

An executor failure must not become world knowledge unless the world caused
it. Most of the bot's worst behaviour has come from breaking that rule: it
would fail to move for a reason that had nothing to do with the level --
combat holding the camera, a mechanism mid-travel, a controller deliberately
standing still, a crossing filed against the wrong wall -- and then remember
the route as impossible. Later runs showed it walking through boundaries it
had already written off.

So the layers are kept apart:

* **who is driving.** Navigation owns yaw and locomotion during ordinary
  travel. Combat says whether it is worth stopping for: an immediate threat,
  a melee engagement or critical health takes the controls, anything else is
  opportunistic and fires only when the route already points near the target.
  Ownership is resolved once, where the input is composed.
* **not moving is not failing.** Every decision records whether it commanded
  translation. A stall with no such request, or one while any controller
  other than navigation holds the camera, is a `stationary_hold`, and the
  objective is left alone.
* **one owner per fact.** Activation state lives in the interaction ledger.
  A second copy in the door record, never written on the path that resolves
  a Use, reported accepted activations as `INTERACTION_VALID_BUT_NO_RESPONSE`.
* **one activation, one transaction.** A world delta is emitted per
  activation, not per observation, so a burst of shots at one wall cannot
  keep refreshing the semantic-progress clock over a real stall.
* **an answered mechanism is done.** A reversible mechanism is not pressed
  again on the evidence that its own boundary is still shut -- one whose
  effect is elsewhere never makes its own wall passable, and re-pressing it
  closes the way it just opened.
* **dormant means dormant.** Suppressed work records what the bot knew when
  it gave up, and comes back early only when that has changed. Running out
  of other ideas is not new evidence.
* **crossings name the boundary crossed.** Derived from the two sectors, not
  from what the route was aiming at.
* **height is not traversal**, and progress is measured in distance rather
  than in squares of distance.

Sprites get the same treatment. Whether the player can operate one is read
off its XSPRITE rather than guessed from its status list and type number, so
a decoration a mapper wired to a channel is a mechanism; a wall-aligned
sprite is clipped as the line the engine clips it as, not as a post at its
centre; a floor-aligned one is a surface rather than a barrier; and a
doorway a solid sprite stands in reports as blocked, and as blocked *and
actionable* when that sprite can be pushed.

`tools/bot_invariants.py` checks these against a run's telemetry and runs as
part of `botcorpus.sh`. It is not a quality measure: a run may fail its
objective and satisfy every invariant. A violation means the bot has
corrupted its own model of the level, whatever the outcome says.

```text
python tools/bot_invariants.py work/botlab/mytag/telemetry.ndjson        --map reference/blood/AGTST4.map
```

## Regression maps

`reference/blood/AGTST1.map` and `AGTST2.map` are the fast exploration gate
and should be run before the campaign corpus. They isolate, in order: a
concave starting sector whose door is around a corner, a distraction alcove
of tiny sectors, a crouch-height door that closes behind the player, a key,
a keyed door requiring a deliberate return across the level, and a vertically
awkward exit switch. Both complete deterministically.

`AGTST5.map` adds a breakable wall in front of a key and a row of columns
whose gaps are too narrow to walk between. `AGTST4.map` is a shorter,
enemy-free E1M1 with four keys, only one of which is needed; it exercises a
rotating arc door that seals a room until it is operated, and completes by
opening that door once, collecting the key it reveals, returning, unlocking
the door that key opens and throwing the lever behind it. `AGTST7.map` bars
its only doorway with a pushable sprite panel: the bot must recognise a
sprite as an obstacle and as a mechanism at the same time. All five
complete.

`AGTST6.map` is not yet passed. It needs the bot to walk a bridge made of
floor-aligned sprites across a damaging pit, which means treating a sprite
surface as a floor in the navigation mesh -- the mesh currently reads the
sector floor, which is far below. The bot reaches 25 of its 35 sectors and
then falls in.

```text
bash tools/botcorpus.sh
bash tools/botrun.sh reference/blood/AGTST2.map mytag -bot_timeout 180
python tools/bot_scorecard.py work/botlab/mytag/telemetry.ndjson \
                              work/botlab/mytag/trajectory.ndjson
python tools/bot_narrative.py work/botlab/mytag/telemetry.ndjson --collapse
python tools/bot_map_render.py reference/blood/AGTST2.map \
       work/botlab/mytag/trajectory.ndjson --output run.svg --zoom
```

Production behaviour contains no map, sector or wall identities. The IDs in
these notes are evidence from runs, not inputs to the bot.

## Watching a run

`-bot_visible` draws a short status readout in the top-left corner:

```text
T 1:23  sect 48  depth 12  seen 27      clock, where it is, how deep, how much seen
RETURN_TO_UNEXPLORED_BRANCH             what it is doing and why
obj t4 id446 ->s47 d1830 6s             objective: type, id, destination, distance, age
todo 4  asleep 9  keys 2  hp 100        unresolved work, dormant work, keys, health
no progress 7s                          only when nothing has advanced for a while
```

The clock is simulated seconds and is the same value as `game_time` in the
telemetry, so a moment seen on screen can be looked up directly:

```text
python tools/bot_narrative.py work/botlab/<tag>/telemetry.ndjson        --from-time 5 --to-time 8 --all
```

`--all` shows every event in the window rather than just the decision story,
which is usually what is wanted when a specific few seconds looked wrong.
The objective `type` values are 1 pickup, 2 key, 3 interaction, 4 frontier,
5 investigate, 6 expose.
