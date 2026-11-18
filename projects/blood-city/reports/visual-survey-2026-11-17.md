# Gravesend from the ground — survey, 2026-11-17

What the city looks like at standing eye height, what is wrong with it in
order of how much it costs the player, and what is and is not known about
walking it. Written from 85 observer frames of
`level/blood-city-current.MAP` (baseline sha256 `5a1aac2e…`, rebuilt
byte-exact from source before anything was changed), three blind reviews,
and the static route reader. **No frame here is a play record and nobody has
walked this map.**

Kinds of statement are kept apart: **measured** (a tool counted it),
**seen** (in a named frame), **read** (an interpretation, with whose).

## What a player meets

**The spawn and the plaza** (`opening`, `market`). Seen: a lamp in the
foreground, the monument with its flame, tall brick blocks, a red sky. It is
the most finished outdoor frame in the city and the only one a blind reviewer
called that.

**The streets** (`fresh1`, `fresh3`, `wave1`, `skyline`). Measured: all 141
street walls under open sky were drawn to one height, 11.6 bodies; the
campaign has no map that does that (0 of 38) and 32 of 38 draw three or
more. Seen: every block is a slab of one repeated window tile from pavement
to sky, with no doors at street level for most of its length, and every long
view ends in black. Read (blind reviewers, twice): "the city reads as sets,
not as continuous space"; "machine-tiled".

**St Gallow's** (`skyline`, `church`). Seen, before: a blank pale slab the
height of its neighbours, a plank door under a strip of tenement brick; the
room called "tower", 5.8 bodies clear, inside a wall 11.6 tall. Inside it is
one of the better interiors: a stepped chancel with a meander frieze, a
pitched nave, a lettered wall. Outside and inside did not describe the same
building. **This is what was changed** — see
`experiments/church-skyline/README.md`.

**The Aldermack** (`theatre`). Seen: the strongest interior — damask, a
lettered foyer, a proscenium. The saloon reads as a panelled room of tables,
each with a fire on it; nothing in the frame says "bar". The pawn shop is a
grey box with a coat on the wall.

**The arcade** (`mall`). Seen: a coffered concourse and glazed fronts that
read as shops. One unit pose and the fountain pose resolved to no sector.

**Under the city** (`sewer`, `station`). Not surveyed: see the next finding.

## Findings, most costly first

1. **No building has a height.** *Measured.* Height was a property of the
   district's sky, not of anything in it. Cause: a mass is a hole, and a
   hole's face is the street sector's wall. Fixed for one building by
   `bloodmap.skyline`; the other 113 street walls are still 11.6 bodies.
   This is the largest single reason the city looks generated.

2. **Every vista ends in black.** *Seen* in `avenue_south`, `avenue_north`,
   `vista_far`; *read* as the top fault by two of three blind reviews. Likely
   cause: the far end of each street is a district-edge wall in deep shade
   with nothing lit on it. Not investigated further. A vista needs something
   at the end of it — the campaign puts a lit front, a sign or a turn there.

3. **The landmark could not be told from a tenement.** *Read* by the round-1
   blind review as "warehouse or fortress (guess)". Addressed; now "church
   (likely)". See the experiment.

4. **Facades are one tile, floor to sky.** *Seen* everywhere outdoors.
   The owner's own note on tiles 400/401 says they are backdrop-scale
   textures; the city wears them at arm's length. No ground storey, no
   doors, no cornice. Lowering heights will make this worse before it makes
   it better, because the eye will reach the top of each block.

5. **Doors are not announced.** *Read* by all three reviews: a door is found
   only because it is the one wooden rectangle on a wall. No step, no light,
   no recess depth, no surround.

6. **The pose library has rotted, and one fault in it is live.** *Measured*:
   of the `sewer` and `station` sets, `north_walk`, `pump_room` and
   `station_hall` now render a street wall or a blank face; `unit_in` and
   `plaza_fountain` resolve to no sector. Two causes. Poses are absolute
   plan coordinates and the plan has moved under them. And
   `look.sector_at` returns the first sector containing a point, so where
   the sewer runs under a street the pose lands in whichever comes first.
   `walk_static.sector_at_grade` fixes that for street-level places; the
   sewer poses need a layer named on them. Until then **the sewer has not
   been looked at in this survey.**

7. **The saloon's tables are each on fire.** *Seen* in `saloon_in`. A flame
   sprite per table reads as a row of braziers.

8. **The cemetery says nothing.** *Read*: "nothing here says cemetery".
   `cemetery_side` is a corner of plaster and the edge of a door. The
   headstones exist (seen in the route strip) but not from the church side.

9. **The sky tile paints spires.** *Read* by the round-2 reviewer; nobody had
   written it down. Tile 3491's horizon competes with any real tower.

10. **Two standing checks were already red.** *Measured* on the untouched
    baseline: `conformance.py` 12/13 (street component 29 measured against
    25 declared — the committed report said 25 and was stale),
    `tree_tests.py` fails on 13 `layer-band-escape` findings (stair flights
    below the street band), `plan_review.py` 15/16. None was caused or
    cured today; the first now reads 39 against 35, the same four over.

## Traversal

**What exists.** NBlood has a bot (`-bot`, with `-bot_trajectory` writing
one NDJSON line per tick: position, sector, angle, commanded input,
velocity, `on_ground`). There is a load-smoke oracle, a passage oracle and a
window-driven action oracle.

**What is permitted.** `handoff.md` says, under Standing disciplines:
"Never launch NBlood" and "Bot runs are crash-smoke only, never navigation
evidence". Those are this project's rules and they were followed: NBlood was
not started today, on this map or any other.

**What is reliable.** Not the bot, as a witness. It chooses its own goals;
there is no flag that feeds it a route. BloodForge wrapped it carefully and
its real runs returned "312,500 samples stuck in sector 0, or a single
sample". The passage oracle's own report disproves three of its readouts. A
bot that fails proves nothing, and one that succeeds proves only that *some*
path was found.

**What was done instead.** `level/walk_static.py` reads a route off the map
with `bloodmap.conditional` and renders a standing eye in each sector of it:

| to | at rest | after working mechanisms | gates on the path |
|---|---|---|---|
| the avenue at the church | yes | yes | none |
| the cemetery | yes | yes | none |
| belfry | no | yes | the tower door |
| tower room, chancel, nave, narthex | no | yes | the tower door, then the inner door |

(As of the afternoon build, `experiments/church-roofs/route`. The morning's
build went in through an avenue portal that no longer exists.)

So the map contains a chain of openings a standing body fits, from the spawn
through the tower's two doors to every room of the church. Its output carries `a_player_was_moved: false`,
`collision_was_tested: false`, `doors_were_operated: false`. It cannot see a
clip radius, a door that does not answer Use, or a monster in the way.

**The smallest path to the real thing.** In order of cost:

1. *A route-following input mode in the bot*: read a list of waypoints,
   steer toward each, press Use when blocked by a mechanism, write the
   existing trajectory NDJSON. Per-tick position, sector and
   commanded-against-actual velocity is already everything collision
   evidence needs. This is the right harness — small, deterministic, and it
   answers "can THIS route be walked" rather than "did a bot find a way".
   It needs an edit inside the NBlood submodule, which is off-limits to this
   project, and the owner's leave to launch NBlood headless on the city.
2. *A synthesised demo.* NBlood plays `.dem` input files. A planned route
   could be compiled to one without touching the submodule. Unverified:
   whether playback can run headless and emit a trajectory.
3. *Until either*, pair every "reachable" claim with `walk_static`'s
   `claims` block and call it what it is.

Both 1 and 2 need a decision that is the owner's, not an agent's.

## Afternoon addendum

The owner played the morning's build and found that its lowered skies hid
everything beyond them. Findings 1 and 3 above were re-done with raised
floors (`experiments/church-roofs`); the NBlood load oracle was run on the
result and passes. Nobody has yet walked it under measurement.

## What changed today, in one line

One building has a height, a silhouette and windows; a blind reviewer who
called it a warehouse now calls it a church; the tools that showed that are
reusable; and the rest of the city is exactly as it was.
