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
tests/test_conditional.py      27 tests, 16 of 16 mutants caught
work/_cond_report.py  work/_pilot_verify.py  work/_progression_diff.py
```

## What it reads

Three kinds of crossing, over `reachability.py`'s graph and `effects.py`'s
embedding — no second opinion about what a portal is:

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
Z-motion mechanisms                1365
  wired                            1235
  inert -- nothing can reach them    130
rotate and slide, scoped out        657
conditional crossings              4160   -> 1069 routes
never passable in either state     1085
routes needing a key                 87
routes that cannot be undone         156
```

```text
routes by what the mechanism reads as        routes by trigger kind
changes what fits through   665  62.2%       switch    514
carries a body between lvl  182  17.0%       push      264
both                        134  12.5%       shot      176
neither                      88   8.2%       unknown   170
                                             touch      70
```

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

## Against `sp_understand`, and neither of us is right

Five campaign maps, at-rest and final reachable sector counts. `loose` is
this view on `reachability.py`'s base, `strict` is the same view on
`spatial.py`'s walkable-at-rest base, `sp` is `analyze_progression`.

```text
map    sectors  design | loose  final | strict  final |  sp  final  exit
E1M1       155     146 |   125    130 |     34     38 |   2      2  False
E1M2       313     293 |   231    233 |    218    220 | 242    248  True
E1M3       329     320 |   227    269 |    208    240 | 243    271  True
E1M4       398     387 |   260    362 |    231    306 | 263    278  False
E2M2       290     260 |   221    255 |    195    222 | 204    221  True
```

**Final-reachable agreement: 0 of 5.** But the size of the disagreement is
the finding, not the count:

* **E1M3 agrees to within 2 sectors** (269 against 271) and E2M2 within 34.
* **E1M1 disagrees catastrophically**: 2 against 130, on a map with 146
  design sectors that players finish. Diagnosed: the player start (sector 30)
  has three portals — one to sector 29, and two 1920-wide ones to 67 and 68
  that carry the **wall cstat blocking flag**. `analyze_spatial` files
  blocking-flagged walls under `blocked_or_state_dependent`, and
  `analyze_progression` only floods walkable-at-rest plus channel-opened
  extras, so the flood halts at two sectors.

Neither base is right, and they are wrong in opposite directions.
`reachability.portal_graph` ignores blocking flags entirely, so "at rest 125"
on E1M1 counts sectors behind shut doors. `spatial.walkable_at_rest` refuses
a blocking flag even where a door opens it. The view runs on either, and says
which it used.

## Limitations

- Only Z-motion is gated. The 657 rotate and slide mechanisms have no
  swept-area spatial-effect reading, so their crossings stay in the base as
  `reachability.py` had them — **excluded, not answered**. The turnstile
  family is inside that gap and is parked.
- The base graph is somebody else's answer, so a static height difference
  between two ordinary sectors is not gated. Only a mechanism's own crossings
  are.
- 170 routes have a cause whose trigger kind reads `unknown`: something
  transmits on the channel but neither a switch type, a destructible, nor a
  recognisable trigger flag explains how it fires.
- Firing a channel is modelled as making every listener's enabling state
  available. A channel that toggles listeners into different states, or a
  `command` that turns one off, is not distinguished.
- Whether a body **survives** a crossing is not asked. A long fall is a way
  down.
- The frontier's rounds are ordered; the actions within a round are not. It
  is not a play order and not a route.
