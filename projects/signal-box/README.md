# The Signal Box

A level project of llmapper. This page is the project's own: what the level is
meant to be, and how it is worked on. What the game is like, and how a thing is
built, is not kept here: it is on the shared shelves, where the next level will
find it.

## What it is

A railway signal box by a level crossing, at night. The player comes up a brick
lane to a crossing whose wooden gate is shut across the road. The signal box
stands beside the line: a brick plinth with a timber upper storey. Inside, the
locking room; a stair up to the lever room, whose windows look onto the track and
whose frame of levers has one that works: pulling it lifts the crossing gate. The
road beyond ends at the exit switch. Four enemies, a sawed-off, shells, a pouch.

Not yet: windows on the lane front, a hipped roof, a nameboard, floor-standing
levers, ballast and a signal post on the track; never read by a blind critic.

## Working on it

```bash
python projects/signal-box/level/build.py            # build; refuses to write a map a gate fails
python -m tools.project status signal-box            # reports/STATUS.md: every open item and what to do
python -m tools.look signal-box --set start -o work/signal-box   # frames, as the game shows it
python -m tools.suite --project signal-box           # this level's own tests
python -m tools.critique --project signal-box prepare <slug> --poses <set> --kind <kind>   # blind readers
```

The cycle for a place: **look it up** (`python -m tools.catalog find <words>`:
findings, tiles, mechanisms, Blood's own rooms of the kind), **study** a kind of
place nobody has studied (`python -m tools.study <slug> --want "..."`), **build**
it in `level/`, **look** at it from named poses (`level/poses.py`), have it
**read blind** (`tools.critique`), and **give back** what was learned.

## Giving back

Anything learned here that another level would want goes on a shared shelf, not
into this directory:

| learned | goes to |
| --- | --- |
| what the engine does, a way of building a thing, a trap a check cannot see, the owner's ruling | `python -m tools.findings add ...` (say how it is known) |
| a tile used as something, in a slot and a kind of place | `python -m tools.tile_contexts record ...` |
| how Blood built a kind of place | `python -m tools.study <slug>` and its `notes.md` |
| an idea seen in a map nobody asked about | `python -m tools.ideas add ...` |
| a function another level would write again | `bloodmap/`, with a test that does not need this level |

What stays here: the brief, the level's own modules and creative decisions, its
poses, its tests, its reports and its critique rounds.

## Layout

```
project.json     what the tools need to know: the map, the build, the ground floor
level/build.py   the build; level/poses.py: where it is looked at from
tests/           regression tests of this level (run by `tools.suite`)
reports/         written by the build and the tools; STATUS.md is never edited
```
