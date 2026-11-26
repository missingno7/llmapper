# The Cold Store

A level project of llmapper. This page is the project's own: what the level is
meant to be, and how it is worked on. What the game is like, and how a thing is
built, is not kept here: it is on the shared shelves, where the next level will
find it.

## What it is

Write the brief here: who the player is, what the place was, what the player
does in it, how it ends. Keep it short, and keep it true as the level changes.

## Working on it

```bash
python projects/cold-store/level/build.py            # build; a rule error, a broken sweep, a read-back or wiring difference writes no map
python -m tools.project status cold-store            # reports/STATUS.md: every open item and what to do
python -m tools.look cold-store --set start -o work/cold-store   # frames, as the game shows it
python -m tools.suite --project cold-store           # this level's own tests
python -m tools.critique --project cold-store prepare <slug> --poses <set> --kind <kind>   # blind readers
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
