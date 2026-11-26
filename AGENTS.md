# Working in llmapper

You are an agent building or analysing Build-engine maps (Blood first). llmapper is
the product: a library (`bloodmap/`), its tools (`tools/`) and what is known about
the game (`knowledge/`). A level is a project under `projects/`; it uses all of
that and owns only its own design. Commands are run from the repository root.

## Look it up before you build it

| You need to know | Run |
| --- | --- |
| anything, on every shelf at once: findings, tiles, parts, wiring, Blood's rooms, studies, ideas | `python -m tools.catalog find <words>` |
| what building levels has taught us: engine behaviour, techniques, traps, the owner's rulings, each by how it is known | `python -m tools.findings find <words>`, `show <id>` |
| one whole map: what it says of itself, its rooms, how it is finished, its wiring, how far our readers get | `python -m tools.catalog map E1M1` |
| one tile: the owner's name, what it shows, every way Blood uses it | `python -m tools.catalog show 1129` |
| what a tile is used as in a slot and kind of place, on whose evidence; what to put in a slot | `python -m tools.tile_contexts show 364`, `where <slot> --place <kind>`, `discover <MAP>` |
| one part: engine name, how many, what sets it off, examples, lessons | `python -m tools.catalog show conveyor` (also `sector:614`, `kSwitchToggle`, `channel:4`, `lesson:DOOR-SLIDING`) |
| a mechanism: an act, the object it is done to, what answers | `python -m tools.catalog wiring switch door`, `idioms` (a sector type is a part; "door" and "lift" are readings of where it sits) |
| whether a mechanism visibly works: the same view at rest and fired | `python -m tools.mechanism_look MAP --root "sprite 51" -o work/mech/<name>`, then `python -m tools.critique change work/mech/<name>/pair.json` |
| what players wrote about a campaign level: walkthrough, keys in order, secrets | `python -m tools.wiki_levels show E3M3` |
| how one object in a campaign map is set up; what a room has; what a thing is wired to | `python -m tools.catalog record E3M5 sector 20`, `show E1M8:243`, `mechanisms E2M4 --place E2M4:613` |
| what is arranged around a centre, and where to see it | `python -m tools.mine_compositions find ring candle` |
| how Blood built a kind of place | `python -m tools.study <slug> --want "..." --seed MAP:sector!`, then read its frames |
| whether the library already has a function for this | [docs/module-map.md](docs/module-map.md) (every module and tool, one line each), [docs/toolkit-index.md](docs/toolkit-index.md) (what to reach for), [docs/architecture.md](docs/architecture.md) (which module owns a kind of fact) |

The shelves are described in [knowledge/blood/LIBRARY.md](knowledge/blood/LIBRARY.md).
The owner's name for a tile outranks any reading of it; never choose a tile by a statistic.

## Give back what you learn

What one level learns, the next must find. Before you finish, put each thing
where it is looked for, and say how it is known:

| learned | goes to |
| --- | --- |
| what the engine does, a way of building a thing, a renderer limit, a trap a check cannot see, a ruling of the owner's | `python -m tools.findings add ...`: `engine` (cite file:line or the run), `precedent` (MAP and sector), `tendency` (the count), `ruling` (the day), `practice` (it worked for us: binds nobody), `hypothesis`, `refuted` |
| a tile used as something, in a slot and kind of place | `python -m tools.tile_contexts record` (`--misfit` when it did not read) |
| how Blood built a kind of place; an idea seen on a tour | `tools.study` and its `notes.md`; `python -m tools.ideas add` |
| a function a second level would write again | `bloodmap/`, with a test that needs no level |

A thing that worked in one level is `practice`, not a rule of Blood. Cite what another
agent can open (never `work/`). A finding shown as `unchecked` has not been held against
its citation: open it, then `tools.findings checked` or `amend`. A project keeps only its own.

## Rules of the codebase

The suite enforces the ones it can.

- **Maps come from `bloodmap.corpus`.** `campaign_maps()`, `named_maps()`,
  `corpus_map_path("E3M1")`. Never glob `maps/` or match filenames.
- **The library imports nothing from `tools/` or `projects/`**, and
  no shared tool or test in `tests/` names a live level: a tool takes
  `--project <name>` (or `LLMAPPER_PROJECT`) and reads `projects/<name>/project.json`
  (`bloodmap.project`). A sensor lives in `bloodmap/`; a tool is its run.
- **A new module is placed in `tools/module_map.py`** and opens with a
  one-sentence docstring; then `python -m tools.module_map`.
- **Read records through `model.record_fields` / `record_extra`** and sectors
  through `sector_geom`. A sector's outline is its LARGEST loop (`outline_and_holes`).
- **A wire is declared on a `wiring.Circuit`**, with a sentence saying what it is
  for; the circuit numbers the channel. Never type a channel number: below 100
  is the engine's. A sender that reports neither its ON nor its OFF change sends nothing.
- **Units come from `player_space.PLAYER_PROFILES["blood"]`.** A standing
  player is 16960 high and 384 wide. `0x1600` is an eye offset, not a height.
- **Limits are NBlood's**: 4096 sectors, 16384 walls, 16384 sprites. Past the
  original game's 1024/8192/4096 is a warning, not an error.

## A level

```bash
python -m tools.project list                          # every project and what kind it is
python -m tools.project new <name> --title "..."      # a level that builds as it stands; read its README.md
python projects/<name>/level/build.py                 # its build (Gravesend's: level/build_skeleton.py, two minutes)
python -m tools.project status <name>                 # reports/STATUS.md: every open item and what to do
python -m tools.look <name> --set <poses> -o <dir>    # frames from its named poses, as the game shows it
python -m tools.sprite_fit <MAP>                      # every sprite as the engine draws it
python -m tools.critique --project <name> prepare <slug> --poses <set> --kind <kind>   # blind readers
python -m tools.showcase --project <name> run         # which view shows each place best, and what it lacks
```

A build declares rooms as a program (`bloodmap.levelprog`), then
`bloodmap.finish` takes the layout to a map: compile, align, gates, light, tidy,
write (`finish`, or `Finish` with your own passes between its stages). A rule error, a mechanism that breaks what it drags, a
read-back difference or wiring that differs writes no map; the rest is measured
and listed in the status for you to answer. Read a project's own page
first: [projects/blood-city/README.md](projects/blood-city/README.md) for
Gravesend, whose state is the generated
[reports/STATUS.md](projects/blood-city/reports/STATUS.md). A new kind of place
is studied first (`tools.study`), built, then looked at. Your own reading of your
own frames does not pass a place: `tools.critique` hands them to blind readers,
and the owner walking the map outranks all of it.

## Verifying

Run what can tell you something about the change you made, and no more:

| after | run | about |
| --- | --- | --- |
| an edit | `python -m tools.suite <words>` (modules by name), or `--changed` | seconds |
| a library change | `python -m tools.suite --library`: `tests/`, which needs no level | 40 seconds |
| a change to a level | several edits to ONE build, then frames and `python -m tools.suite --project <name>` | minutes |
| before a commit | `python -m tools.suite`: every module, a process each | a minute |
| a change to a reader | `python -m tools.reading_check` | minutes |

`work/suite.log` holds what failed. When a change moves a sensor or a helper, run
the miner that uses it before and after and compare the files byte for byte.
When it touches a level, the build must write the same map unless you meant to
change it. A function that returns without raising is not evidence that it built
what it says: read the result back (the build's gates, `tools.sprite_fit`, a frame).

## Things you must not do

- **Never start `nblood` or `eduke32` with a window, and never inject keys.**
  Looking is done by the XMapEdit observer from a pose
  (`bloodmap.visual.run_observation`, `tools.look`). Playing is the owner's.
- **Never commit or delete anything under `maps/` or `reference/`.** They hold
  commercial game data, supplied locally. Renders and copies of commercial maps
  are gitignored for the same reason; do not force-add them.
- **Do not stage the `NBlood` or `xmapedit` submodule pointers** from this
  repository, and never run `git add -A` inside them.
- **Do not stash, reset or discard uncommitted work you did not make.** Copy a
  baseline aside instead.
- **Do not repair an original map to make it compile**, and do not normalise
  values on a lossless path. An original's oddity is evidence.

## When you finish

Say what you verified and how, and what you did not. What a later agent needs
goes into the repository where it will be looked for: about the game, onto a
shelf (above); about a level, into what its tools generate. A page that can go
stale will.
