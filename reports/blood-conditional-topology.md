# Conditional topology: which ways are gated, and what opens them

`reachability.py` says so in its own limitations: *gating is ignored, a closed
door is still a portal*. That is the right answer to its question — is this
geometry part of the level — and the wrong answer to this one. This is the
derived view that puts the gates back, and answers **"what becomes reachable
after this action?"** with the chain that explains it.

```text
bloodmap/conditional.py        the view
bloodmap/cli.py                llmapper conditional
reports/blood-conditional-topology.json
tests/test_conditional.py      46 tests, 25 of 25 mutants caught
work/_cond_report.py  work/_pilot_verify.py  work/_progression_diff.py
```

## Three bases, one default

Updated 2026-09-01. The base graph is no longer a single permissive answer.

```text
optimistic       reachability.portal_graph: every two-sided wall is a way,
                 gating ignored. Reaches behind shut doors.
blocking_aware   THE DEFAULT. portal_graph minus crossings whose wall carries
                 the blocking cstat, plus the blocking walls a kWallGib
                 mechanism reopens -- as conditional crossings with their
                 cause chain, not as walls.
strict           spatial.walkable_at_rest: the blocking flag, a portal under
                 512 wide and an opening under 4096 are all hard stops, and
                 nothing reopens any of them.
```

All three stay callable and every report says which it ran on, because they
disagree by a lot and the disagreement is a finding rather than a setting.

**Only one mechanism in the engine reopens a blocked wall.**
`triggers.cpp:SetupGibWallState` clears `cstat & 65` and the masked bit on
both sides when a kWallGib (type 511) XWALL's `state` is 1, and sets them
again when it is 0. Nothing else changes a wall's blocking bit — a Z-motion
sector moves floors and ceilings, never cstat — so a blocking wall that is
not a gib wall is **shut for ever**.

```text
60839 two-sided campaign walls    2272 blocking (3.7%)
  kWallGib (511)            205    every one built shut, every one wired
  plain and solid for ever 1183
  plain, on a motion sector 850    the door's own jamb walls
  other XWALL                34
```

Two rules the measurement forced, in opposite directions. A **wall pair** is
shut when *either* side carries the bit, because the engine sets it on one
side and clears it on the other. A **sector pair** is shut only when *every*
wall pair between the two blocks — reading that the other way made this base
stricter than the strict base, and E1M1 fell to 28 sectors against strict's
34, which is how the mistake surfaced.

## What it reads

Three kinds of crossing, over the chosen base and `effects.py`'s embedding —
no second opinion about what a portal is:

* **at rest** — passable with nobody doing anything; left in the base.
* **conditional** — passable in exactly one of a mechanism's two states,
  carrying that state and the chain that reaches it.
* **never** — passable in neither, which is a finding rather than an edge.

A crossing is **directed**, because climbing is capped at the engine's
step-up (6656) and falling is not. A lift is exactly the mechanism that
exploits the difference. Treating the two directions alike called 21 of
E1M2's crossings impassable when a body can simply drop down them.

A **route** collapses a mechanism's crossings into the connection a reader
means by "the door": one sector with a portal on each side is one route, four
directed edges.

## The campaign, measured

43 maps.

```text
Z-motion mechanisms                1365      blocking crossings      1392
  wired                            1235        reopened by a gib wall  214
  inert -- nothing can reach them    130        shut for ever          1190
rotate and slide, scoped out        657
conditional crossings              4378   -> 1178 routes
never passable in either state     1085
routes needing a key                 87
routes that cannot be undone         268
```

```text
routes by what gates them           routes by trigger kind
a moving sector    1069             push 276   shot 303   switch 498
a breakable wall    109             relay 123  touch 70   pickup 12
                                    unknown 9  leave 3    kill 1   generator 1

routes by what the mechanism reads as
changes what fits through   774        both        134
carries a body between lvl  182        neither      88
```

**Restated 2026-09-01: a switch worked by pushing is a switch.** The trigger
classifier put player-facing flags before what the thing *is*, so 212 routes
fired by pressing a switch sprite were reported as `push` -- indistinguishable
from a pushable wall, which is the one thing the label had to separate them
from. The rule now reads: a `SWITCH_TYPES` sprite whose push flag would have
decided it reports `switch`. It stays below `trigger_vector`, so a shootable
switch still reports `shot`, and it is scoped to the push flags alone, so a
proximity or exit switch still reports how it actually fires. The split above
is the re-measured one; the earlier `push 488 / switch 285` counted the same
routes under the less specific name.

**Not one gating channel is a system channel.** Of the 113 distinct channels
that cause a conditional crossing, every one is ≥ 100; the reserved band
(`fragment.SYSTEM_CHANNELS`, 1–97) carries level start, exit and secrets and
never gates a door. The vocabulary is still the right one to name a channel
with — it just never fires as a cause here.

## An inert mechanism gates nothing

130 Z-motion mechanisms have no way to change state: no channel reaches them,
no wall of theirs is pushable, walking in does nothing. Almost all are type 0
carrying stale XSECTOR z endpoints, which `doors._is_motion` accepts on the
endpoints alone — right for "does this sector describe a motion", wrong for
"can this motion ever happen".

Before that clause existed, E1M3's eight of them produced **60 conditional
crossings opened by nobody**. They are now counted as inert and excluded.

## Three pilots, each checked twice

Every number below is read off the raw XSECTOR by `work/_pilot_verify.py`,
which imports nothing from the view, and then looked at in the editor
renderer. Agreement here is two independent readings agreeing, not one
reading agreeing with itself.

### A lift — E1M3 sector 241

```text
type 600   floor 18432 -> -16384   ceiling -6144 -> -40960
trigger_push + trigger_wall_push, no channel
neighbours 240 (floor 18432) and 242 (floor -16384)
```

The floor's two endpoints are **exactly** its two neighbours' floors. The
opening stays 24576 in both states, so nothing about it opens or closes —
what changes is which floor a body standing on it is level with. Operating it
gains 33 sectors.

This is the case that proves the crossing test needs both clauses: a reading
that asks only "does the gap admit a body" calls this unconditional.

### A breakable barrier — E1M4 sprite 373

```text
sprite 373  type 408 kThingWallCrack  tx_id 119  command 1   in sector 245
sector 276  rx_id 119  trigger_once  ceiling 38912 -> 10240   floor 38912
sector 277  rx_id 119  trigger_once  ceiling 38912 -> 12800   floor 38912
```

Both listeners are **flush** at rest — ceiling equal to floor, opening 0 —
and open to 28672 and 26112. `trigger_once`, and a crack does not come back,
so the route is irreversible. Reached at round 2 of the frontier, it gains 14
sectors.

The editor renderer confirms it without being asked: it **refused to place a
viewpoint in sector 276**, reporting *"no interior point with standing
clearance"*. A renderer that knows nothing about this view agrees the sector
is shut.

### A keyed door — E1M4 sector 295

```text
type 600   key 6 (moon)   trigger_wall_push
ceiling 40960 -> 10240, so the opening goes 0 -> 30720
neighbours 294 and 296, both at floor 40960
exactly one moon-key sprite in the map (1088); exactly one sector keyed to 6
```

Picking up the moon key gains 46 sectors. The render from sector 294 shows a
**moon lock plate on the door wall** — the XSECTOR says `key=6`, the renderer
paints a crescent, and neither was told about the other.

## The question, answered

```bash
llmapper conditional maps/blood/campaign/E1M4.MAP --action destroy --target 373
```

returns the newly reachable set and, for each crossing opened, the chain:
trigger (`sprite 373, type 408, shot, irreversible`) → channel (`119`) →
mechanism (`sector 276, enabling state on`) → topology delta (`opening
0 → 28672, floor 38912, neighbour floor 40960`) → crossing (`276 → 245`).
Every link is a field in the map.

`--frontier` emits the whole progression instead; `--holding-key` and
`--fired-channel` set the state to ask from, which a keyed door needs.

## The trigger kinds, and what "unknown" was really measuring

170 routes used to carry a cause reading `unknown`. They were never unknown
triggers: the classifier was measuring the **absence of a player-facing
flag**, and `trigger_on` / `trigger_off` are *response* flags — what a thing
does when its channel fires — not causes.

Five kinds were missing. **`relay`** (154 of the 204 unclassified causes): a
thing that listens on one channel and retransmits on another, a link in a
chain rather than its head; 99 of them are kSectorZMotion sectors that
transmit when they move. **`pickup`**: 18 were key sprites, and picking up a
key is the commonest progression step in the game. **`leave`**: Blood's
`trigger_exit`, fired by walking *out*. **`kill`**: a dude that transmits on
death. **`generator`**: kGenTrigger and its family.

That takes the residue from 170 routes to **9 causes, all kTrapExploder**.

## Against `sp_understand`, and neither of us is right

Five campaign maps, at-rest and final reachable sector counts. `loose` is
this view on `reachability.py`'s base, `strict` is the same view on
`spatial.py`'s walkable-at-rest base, `sp` is `analyze_progression`.

```text
map    sectors design |  optimistic | blocking-aware |    strict | sp_understand
E1M1       155    146 |  125 > 131  |     97 > 120   |  34 > 38  |     2 > 2
E1M2       313    293 |  231 > 238  |    226 > 233   | 218 > 225 |   242 > 248
E1M3       329    320 |  227 > 269  |    211 > 243   | 208 > 240 |   243 > 271
E1M4       398    387 |  260 > 362  |    253 > 357   | 231 > 308 |   263 > 278
E2M2       290    260 |  221 > 255  |    201 > 230   | 195 > 222 |   204 > 221
```

**Final-reachable agreement is exact 0 of 5 on every base.** Gaps on the
default base are 118, 15, 28, 79 and 9. The size of the disagreement is the
finding, not the count — E2M2 differs by 9 and E1M1 by 118.

**And the earlier diagnosis of E1M1 was wrong.** Its two blocking-flagged
start portals carry **no XWALL**, so nothing in the engine can ever open
them; `analyze_spatial` is right to treat them as hard stops. The player
start is a four-sector box, and the way out is a **paired stack link** to
sector 28 — which `analyze_spatial` records under
`known_non_portal_transitions` and `analyze_progression` never reads. That
is why it reaches 2 of 146 design sectors on a map players finish, and it is
a defect in its input rather than in any base graph.

The blocking-aware base keeps links and teleports whatever else it refuses,
for exactly this reason.

## Limitations

- Only Z-motion is gated. The 657 rotate and slide mechanisms have no
  swept-area spatial-effect reading, so their crossings stay in the base as
  `reachability.py` had them — **excluded, not answered**. The turnstile
  family is inside that gap and is parked.
- The base graph is somebody else's answer, so a static height difference
  between two ordinary sectors is not gated. Only a mechanism's own crossings
  are.
- The blocking-aware base gates on the blocking cstat and nothing else. It
  does **not** adopt `spatial.walkable_at_rest`'s width and opening
  thresholds, so a portal 300 units wide is still a way in the default base.
- 9 causes still read `unknown`, and they are all one type: kTrapExploder
  sprites that transmit with no trigger flag and no `rx_id`, so nothing in
  the map says what fires them. (This was 170 routes before the classifier
  learned about relays — see below.)
- Firing a channel is modelled as making every listener's enabling state
  available. A channel that toggles listeners into different states, or a
  `command` that turns one off, is not distinguished.
- Whether a body **survives** a crossing is not asked. A long fall is a way
  down.
- The frontier's rounds are ordered; the actions within a round are not. It
  is not a play order and not a route.
