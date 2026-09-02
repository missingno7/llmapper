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
`-bot_timeout`, `-bot_stall`, `-bot_realtime`, `-bot_visible`, and
`-bot_debug`.

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

## Architecture

Four separate authorities, one question each, with dependencies pointing one
way. The split is not cosmetic: the direction is what keeps engine detail out
of the decisions.

```text
NBlood / Build engine
        v
llmapper/bot/blood/       what physically exists, read out of Blood
llmapper/bot/terrain/     that geometry turned into Regions by its shape
        v
llmapper/bot/semantic/    the 3D world: Regions, SpatialRelations, Affordances
        v
llmapper/bot/traversal/   world + Caleb's current physics -> typed transitions
        v
llmapper/bot/planner/     of what can be executed, what to do
        v
llmapper/bot/exec/        carrying one chosen action out
```

`llmapper/bot/debug/` reads both sides so a log line can name the Blood
objects behind a semantic id. It feeds nothing back; deleting it would not
change a tick. `bot.cpp` runs the layers in order and owns none of their jobs.

### One continuous space is one Region

A Region is one physically continuous piece of standable space: an outline,
the holes of whatever solid things stand in it, any wall it wraps around, the
surface holding a body up over it and the free volume above that surface. It
is not convex, it is not small, and it is not cut up to make walking across
it easier.

Regions are built from geometry in this order:

1. read every support surface -- sector floors, and floor-aligned solid
   sprites, which are surfaces in their own right;
2. dissolve every seam that carries no physical meaning. A seam is
   meaningless when the support plane, the clearance class, the hazard and
   the dynamic owner are the same on both sides and the world does not close
   it;
3. reconstruct the continuous outline of what is left by cancelling every
   internal edge, whatever subdivision it came from, and drop the vertices
   that subdivision left lying on straight lines;
4. that outline is the Region. Solid objects standing in it are holes; a wall
   that divides part of it without cutting it in two is kept as a wall
   inside it.

A Region boundary therefore exists only where a player-relevant property
changes: a different thing holding the body up, a different support or
ceiling plane, a different clearance class, a hazard, something that can
move, or genuinely disconnected space. Not because a sector changed, not
because a polygon needed another piece, and never because there is a pickup
or a button there.

Measured on `AGTST6`: 42 support faces, 12 continuous spaces, **12 Regions**
and 42 relations. Thirty Build sectors dissolve into one Region with six
holes; the whole outdoor area -- which the previous convex model cut into
thirty-four pieces -- is one 25-corner Region with one wall inside it.

Region identity is derived from shape, so it survives observer movement,
re-tessellation and re-authoring. No sampling constant -- ray count, ray
range, connection radius, grid size -- exists above the mapper at all, and
there is no convex decomposition anywhere in the semantic layers.

### Region is planning, pose is execution

A SpatialRelation says two Regions are next to each other and carries the
Gateway: the interval of boundary they share, the vertical step across it and
the clearance. It is not a traversal. Gateways come from real seams between
distinct spaces, merged where an author split one opening into several walls
and kept apart where there are genuinely two ways through.

Getting across a Region is a real navigation problem, and it is solved in
`llmapper/bot/nav/` -- below the planner, at the moment a leg is needed, in
the actor's own configuration space:

* the region's solid boundary is its outline and holes minus its openings,
  plus any wall inside it;
* Build does not clip a wall as a line alone -- it puts an axis-aligned
  square of the body's width at each end -- so the end of a wall is a square
  obstacle and the model uses the same shape;
* corners are stood off at the distance that clears both of their faces,
  which for a sharp corner is further and for a blunt one is nearer, and is
  the body's own width divided by the sine of the corner's half angle;
* a visibility graph over those corners gives the shortest polyline that
  never comes within the body's width of anything.

Nothing this produces is stored, and the planner never sees any of it. The
acute wall spur in `AGTST6` at `(4096,-4096)` -- which the convex model
turned into a chain of gateways through its tip -- is now an ordinary corner
inside one Region, rounded by two steering points 209 units clear of it.

### Affordances do not partition anything

A pickup, a switch and a pushable wall are all one thing: an `Affordance`
with an `ActionKind` and an execution domain. The domain is the set of poses
the engine itself accepts the action from, grouped by the Region each pose
falls in -- a door can be pushed from either side, and that is two options in
two Regions and one affordance. Which option is used is chosen by the planner
from what it can reach.

Pickups use Blood's own `CheckPickUp` bounds; interactions use Blood's own
`ActionScan`. Neither adds a Region, a node or a waypoint.

### Physics decides what can be traversed

`blood/caleb_physics.*` is the authority on what the actor can currently do.
Given a relation it asks the engine, by walking the live hull with `ClipMove`
and settling the way `MoveDude` settles it. Nothing compares a height
difference to a number. Picking up Jumping Boots changes what this object
says and nothing about the world -- an invariant the spatial tests check
directly.

`WALK` and `DROP` are derived; `CROUCH`, `JUMP` and `RIDE` have no
engine-backed query written yet. What the actor can physically do and what
this bot has an executor for are separate facts: a drop into a pit is
reported as physically real and never selected.

### Checking it

`tools/bot_layering.sh` is the gate. It greps for engine vocabulary above the
mapper, checks planning cannot reach provenance, and then compiles the
semantic, terrain, traversal, local-path, planner and executor modules with
no engine include path at all and runs the spatial invariants: tessellation
(same footprints and gateways from one, four and eight sectors), authoring
direction, one concave space staying one Region, a room with three crates
staying one Region with three holes, a wall spur staying an obstacle, two
doorways staying two ways, an internal wall surviving as a wall, meaningful
steps, clearance classes, stacked supports, crossed supports, affordances not
partitioning terrain, the Jumping Boots invariant and the capability split.

```text
bash tools/bot_layering.sh
```

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

Regions are large, so having entered one is not the same as having explored
from it, and `observed` is never taken to mean "finished with". The frontier
is a way out, not a place:

1. a gateway the actor can drive, has never gone through, and which leads
   somewhere it has never stood;
2. otherwise an affordance that has never been tried;
3. otherwise a gateway that is known, has never been gone through and cannot
   be -- a shut door is a fact about the world with something on the other
   side of it, and standing at it is how the actor finds out what would open
   it. Each is walked to once and then recorded as looked at;
4. otherwise an affordance whose last attempt widened the world.

There is a finite number of gateways and a finite number of affordances, so
this terminates. There are no observation points anywhere in it.

The world's geometry is read whole rather than discovered by looking at it,
and what can be done in it is read the same way: a model that knew the floor
of a room but not the switch on its wall would be inconsistent with itself.
Whether a thing has actually been seen is recorded separately, which is what
`observed` means.

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

## What Caleb can do

Every physical capability the bot plans against is asked of the engine, in
`llmapper/bot/player_capability.h`, and nothing there is fitted to a
recording or rounded to a convenient number. The body comes from
`GetSpriteExtents` and `clipdist`, the same values MoveDude feeds to
`ClipMove`; the jump apex, the flight time and the harmless drop height are
Blood's own impulse, gravity and landing-damage arithmetic replayed forward;
the pitchfork's reach is `gVectorData[kVectorTine].maxDist`; the pitch limits
and the full-throttle input are the constants `ProcessInput` and
`ctrlGetInput` actually clamp to. Anything that is bot *policy* -- how much
margin to leave, how much damage is acceptable, how close to stand -- lives
in `bot.cpp` and is written as a margin on top of one of those facts.

The same header carries a one-frame simulator of the player's motion:
`ProcessInput`'s acceleration, then `actProcessSprites`' air drag, then
`MoveDude`'s move, gravity, landing and ground drag, in that order and with
the engine's own constants. It leaves out only clipping.

The claim that it is exact is checked rather than asserted. Every frame the
bot steps the simulator from the state it saw last frame with the input it
actually sent, and compares against what the engine did; a run ends with a
`motion_model_audit` line saying how it went. Frames the model does not claim
-- the engine clipped, `pushmove_old` shoved the body out of geometry, the
sprite's extents changed mid-animation, the player is in water -- are counted
separately, so `diverged` means the arithmetic is wrong and nothing else. It
is zero on all seven regression maps. That check is what found the air drag:
`actAirDrag(pSprite, 128)` runs on every dude every frame, takes a
five-hundredth of all three velocity components, and leaving it out made
every predicted arc land long.

## Jumping a gap

A hole with something across it is a crossing. The bot looks from a ledge it
will not step off for a lip standing clear of the pit, square-on to both
edges, with the line between them over the hole; the landing may be higher by
less than the jump reaches or lower by less than a jump would climb back,
because one pillar in a row is rarely the height of the next.

Blood scales input authority and drag by height off the floor, and both only
cut out well above where a jump reaches -- about three quarters of the ground
control is still there at the apex. A jump is therefore steerable after it is
taken, and the question at the lip is not whether full throttle lands right,
but whether *any* input does: over a pillar a thousand units deep, full
throttle sails clean over. The bot runs the simulator across the range of
forward inputs and keeps the one landing nearest the middle of the ledge.
The launch, the mid-air trim, and the decision to carry a landing's momentum
straight into the next jump all ask that same question, so there is one
answer to it and no separate rule for chaining.

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
python tools/bot_invariants.py work/botlab/mytag/telemetry.ndjson        --map reference/blood/AGTST18.map
```

## Regression maps

Five maps, and only these five. `tools/botcorpus.sh` runs them all without
monsters -- this phase has no combat, so an enemy is not a test of anything
the bot does; it only decides how long the run lasts.

`AGTST1`, `AGTST6` and `AGTST7` are the behavioural gate. They need ordinary
walking, exploration, a generic `Use` and a generic `Collect` and nothing
else, which is exactly the abstraction being proved, and all three complete
deterministically. Any other result on them is a regression.

* `AGTST1` -- a concave starting room whose way on is a wall that has to be
  pushed, with the switch reachable from either side of the door it opens.
* `AGTST6` -- a bridge of floor-aligned sprites across a damaging pit, an
  acute wall spur in the middle of one continuous outdoor space, and thirty
  Build sectors that are one corridor.
* `AGTST7` -- a doorway barred by a pushable sprite panel, which the model
  has to hold as an obstacle and a mechanism at the same time.

`AGTST17` and `AGTST18` are the harder ones the model is pushed against.
They are not there to pass; they are there to say which problem is next, and
what matters about a run on them is which problem it exposes.

```text
AGTST1   COMPLETED         30s | 6 sectors -> 3 regions
AGTST6   COMPLETED         61s | 35 sectors, 42 faces -> 12 regions
AGTST7   COMPLETED         48s | 5 sectors -> 5 regions
AGTST17  COMPLETED         79s | 8 sectors -> 5 regions
AGTST18  NO_KNOWN_ACTION   28s | 155 sectors, 173 faces -> 133 regions,
                                 121 places, 11 of them split by body width
```

`AGTST18` is the size at which the model stops being able to hide anything:
698 relations, 208 of them walkable, and eleven Regions that one continuous
piece of space for the world is several pieces of space for a body 384 units
wide. Reading a run on it starts with the `why=` on each `relation_mapped`
line and the `pieces=` on each `region_mapped` line.

```text
bash tools/botcorpus.sh
bash tools/botrun.sh reference/blood/AGTST18.map mytag -bot_timeout 300 -nodudes
python tools/bot_scorecard.py work/botlab/mytag/telemetry.ndjson                               work/botlab/mytag/trajectory.ndjson
python tools/bot_narrative.py work/botlab/mytag/telemetry.ndjson --collapse
python tools/bot_map_render.py reference/blood/AGTST18.map        work/botlab/mytag/trajectory.ndjson --output run.svg --zoom
```

Production behaviour contains no map, sector or wall identities. The IDs in
these notes are evidence from runs, not inputs to the bot.

## Seeing the world the bot sees

`-bot_debug` draws the semantic world over the normal game view. It does not
need `-bot`: with the flag on and the bot off, the mapper runs while a person
plays the level, so the model can be walked through and looked at.

```bash
nblood.exe -usecwd -nosetup -map AGTST6.map -bot_debug
```

What is painted:

```text
translucent floor      one Region, coloured by id. Two Regions that ought to
                       abut but actually overlap show up as one shape
                       bleeding through another.
outline  white         the Region the actor is standing in
         violet        a Region that has been observed
         amber         a Region that exists but has not been seen
line across an opening
         green         the model says the body can walk it
         amber         physically possible, but this bot has no executor
                       for it -- a drop, for instance
         red           the model says no
cross + "use N"        an affordance and its spatial target; green when the
                       world currently accepts it, red when it does not, and
                       a trailing * once it has been tried
number                 the Region id, so a screenshot can be matched against
                       the `region_mapped` telemetry
```

The two things worth looking for are a red line across a doorway that can
plainly be walked through, and floor with no Region painted on it at all.
Both mean the mapper is wrong, and both are much easier to see than to infer
from a run that stalled.

## Watching a run

`-bot_visible` draws a short status readout in the top-left corner:

```text
BOT 1:23 r7/32 go_to       clock, which region it is in, how many are known,
                            and what it is doing with the one it chose
```

The clock is simulated seconds and is the same value as `game_time` in the
telemetry, so a moment seen on screen can be looked up directly:

```text
python tools/bot_narrative.py work/botlab/<tag>/telemetry.ndjson        --from-time 5 --to-time 8 --all
```

`--all` shows every event in the window rather than just the decision story,
which is usually what is wanted when a specific few seconds looked wrong.
The decision events are `goal_chosen`, `waypoint`, `goal_finished`,
`action_delivered`, `action_settled` and `no_known_action`. `world_mapped`,
`region_mapped`, `relation_mapped` and `affordance_mapped` record what the
mapper made of the world each time it was rebuilt, which is the trace to read
when a run goes wrong: engine, mapper, Regions, relations, traversal, planner,
executor, in that order. Each carries the Blood objects behind the semantic id
it names, for reading only.

## Loss notice, 2026-09-02

The AGTST test maps (`reference/blood/AGTST1.map` … `AGTST18.map`),
`overlap1.map` and the `llmapper-bot-iter27.*` artifacts were deleted on
2026-09-01 by a worktree cleanup that followed a directory junction, and no
copy exists anywhere on this machine or in the NBlood fork's history. The
hard correctness gate in `tools/botcorpus.sh` therefore has no maps to run
until they are re-authored. Recovery record: `reports/corpus-recovery-
2026-09-01.md`. The rule that follows is in
`docs/llmapper_level_understanding_handbook/10_AGENT_EXECUTION_PROTOCOL.md`,
"Irreplaceable local data".
