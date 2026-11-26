# Gravesend

A Blood city for single play: streets and a square with a fair, six keyed places
(church, arcade, theatre, market, foundry, station), sewers, a ghost railway and
a storm chamber. One of llmapper's level projects, and its largest: 1,802
sectors at the time of writing. Version 0.1 was given out on 2026-11-25
(`release/`).

Read [reports/STATUS.md](reports/STATUS.md) first: the build's size, every named
place with its study and its last critique, and what is open. The build writes
it; it is never edited.

## Working on it

```bash
python projects/blood-city/level/build_skeleton.py     # two to three minutes; prints every pass
python projects/blood-city/level/status.py --place station   # one place and what is open on it
python projects/blood-city/level/status.py --kind refused    # one kind of open item
python projects/blood-city/level/status.py --wires           # the level's wiring (named in level/wires.py)
python projects/blood-city/level/status.py --stages          # the build's stages and their lines
python -m tools.look blood-city --set <poses> -o <dir>       # frames; the sets are level/poses.py (--list)
python -m tools.sprite_fit projects/blood-city/level/blood-city-current.MAP
python -m tools.critique --project blood-city prepare <slug> --poses <set> --kind <kind>
python -m tools.suite --project blood-city                   # its regression tests (tests/)
python projects/blood-city/level/citytree.py zoom <place> --depth 2   # stand anywhere in its tree
python projects/blood-city/level/package.py                  # only when a version is given out
```

The build is deterministic and writes `level/blood-city-current.MAP`, which
every tool reads, and `level/gravesend.MAP` (`release.py`: the same level with
what is under the city moved out from under it), which the owner plays. What it
measured is in `reports/build-manifest.json`, and it ends by rewriting the
status. After recording a critique round, run `status.py` again.

A place is named on `level/character.py` with the study it was built from.
A new kind of place is studied first (`python -m tools.study`), built, looked
at, then read blind.

## What is where

```
project.json    what the shared tools need: the map, the poses, the ground floor
level/          the build (build_skeleton.py), a module a place, wires.py, lights.py, poses.py, gameplay.py
tests/          regression tests of this level: places, walks, the owner's rulings on it
reports/        written by the build and the tools: STATUS.md, build-manifest.json, critique/, showcase/
references/     design notes of its places
release/        what was given out: GRAVESEND.MAP and README.TXT, by level/package.py
experiments/    records of design experiments (history)
```

Its build is older than `bloodmap.finish` and runs the same passes itself, with
dozens of its own between them: read `build_skeleton.py`'s stages
(`status.py --stages`) before adding one.

## What is the game's and not this level's

What was learned here about Blood, the engine and how to build is on the shared
shelves: `python -m tools.findings find <words>`. Many of this level's modules
are worked examples that the findings point at (`level/ghost_stair.py` for a
flight under a sloped roof, `level/sewer_rooms.py` for refitting a room in
place). A technique another level needs is moved into `bloodmap/` when it is
needed there, not copied.
