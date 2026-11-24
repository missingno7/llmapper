# Working in llmapper

You are an agent building or analysing Build-engine maps (Blood first). This
page is what every session needs; everything else is looked up when the task
calls for it. Commands are run from the repository root.

## Look it up before you build it

| You need to know | Run |
| --- | --- |
| what a tile is, a part is, how a thing is wired, or where Blood has one | `python -m tools.catalog find <words>` |
| one whole map: what it says of itself, its rooms, how it is finished, its wiring, how far our readers get | `python -m tools.catalog map E1M1` |
| one tile: the owner's name, what it shows, every way Blood uses it | `python -m tools.catalog show 1129` |
| what a tile is used as in a slot and kind of place, on whose evidence; what to put in a slot; what a map does that nobody has shown; recording what you learn | `python -m tools.tile_contexts show 364`, `where <slot> --place <kind>`, `discover <MAP>`, `record` |
| one part: engine name, how many, what sets it off, examples, lessons | `python -m tools.catalog show conveyor` (also `sector:614`, `kSwitchToggle`, `channel:4`, `lesson:DOOR-SLIDING`) |
| a mechanism: an act, the object it is done to, what answers | `python -m tools.catalog wiring switch door` (a sector type is a part; "door" and "lift" are readings of where it sits) |
| whether a mechanism visibly works: the same view at rest and fired | `python -m tools.mechanism_look MAP --root "sprite 51" -o work/mech/<name>`, then `python -m tools.critique change work/mech/<name>/pair.json` for blind readers |
| the phrases Blood's wiring is written in, each counted | `python -m tools.catalog idioms` (shot switch, secret, cascade, closet relay, breach ...) |
| what players wrote about a campaign level: its walkthrough, keys in order, secrets and rewards | `python -m tools.wiki_levels show E3M3` (facts in `knowledge/blood/wiki/levels.json`; `fetch` caches the pages) |
| how one object in a campaign map is set up | `python -m tools.catalog record E3M5 sector 20` (only the fields that are set, and the room it is in) |
| which rooms have a mechanic, and what one room has | `python -m tools.catalog find lift crypt`, then `python -m tools.catalog show E1M8:243` |
| what is arranged around a centre, and where to see it | `python -m tools.mine_compositions find ring candle`, then `show MAP:sector` |
| what a thing is wired to | `python -m tools.catalog mechanisms E2M4 --place E2M4:613` |
| whether the library already has a function for this | [docs/module-map.md](docs/module-map.md): every module and tool, one line each |
| which module owns a kind of fact | [docs/architecture.md](docs/architecture.md) |
| what to reach for when authoring | [docs/toolkit-index.md](docs/toolkit-index.md) |
| how Blood built a kind of place | `python -m tools.study <slug> --want "..." --seed MAP:sector!` then read its frames |
| which view shows a city place best, and what each place lacks (blind) | `python -m tools.showcase run`, `judge`, `report`; read `projects/blood-city/reports/showcase/round-N/showcase.md` |

The shelves behind `catalog` are described in
[knowledge/blood/LIBRARY.md](knowledge/blood/LIBRARY.md). The owner's name for a
tile outranks any reading of it; never choose a tile by a statistic.

## Rules of the codebase

The suite enforces the ones it can: the corpus, the import direction, the
module map and the limits fail a test when broken.

- **Maps come from `bloodmap.corpus`.** `campaign_maps()`, `named_maps()`,
  `corpus_map_path("E3M1")`. Never glob `maps/` or match filenames: the corpus
  is provenance directories and a glob finds nothing.
- **The library imports nothing from `tools/`, `experiments/` or `projects/`.**
  A sensor lives in `bloodmap/`; a tool is its run over a corpus.
- **A new module is placed in `tools/module_map.py`** and opens with a
  one-sentence docstring; then `python -m tools.module_map`.
- **Read records through `model.record_fields` / `record_extra`** and sectors
  through `sector_geom`. A sector's outline is its LARGEST loop
  (`outline_and_holes`), not its first: 514 of the campaign's 867 sectors with
  holes trace a hole first.
- **A wire is declared on a `wiring.Circuit`**, with a sentence saying what
  it is for; the circuit numbers the channel. Never type a channel number:
  below 100 is the engine's. An object has one `tx_id` and one `rx_id`, and a
  sender that reports neither its ON nor its OFF change sends nothing.
- **Units come from `player_space.PLAYER_PROFILES["blood"]`.** A standing
  player is 16960 high and 384 wide. `0x1600` is an eye offset, not a height.
- **Limits are NBlood's**: 4096 sectors, 16384 walls, 16384 sprites. Past the
  original game's 1024/8192/4096 is a warning, not an error.

## Verifying

```bash
python -m unittest discover -s tests > work/suite.log 2>&1; grep -E "^(Ran|OK|FAILED)" work/suite.log
```

About five minutes; read the `Ran` and `OK` lines from the log, because a pipe
hides the exit code. A single module is `python -m unittest tests.test_<name>`.

When a change moves a sensor or a helper, run the miner that uses it before
and after and compare the files byte for byte. When it touches the city, the
build must write the same map unless you meant to change it.

A reader is marked against the campaign, which needs no labels: every shipped
map can be finished. `python -m tools.reading_check` says in how many our
readers reach the exit, the keys and the rooms; a change to a reader is
checked there.

A function that returns without raising is not evidence that it built what it
says. Read the result back: `python -m tools.sprite_fit <MAP>`, the build's own
read-back and rule lines, or a frame.

## The city (`projects/blood-city`)

Read [projects/blood-city/reports/STATUS.md](projects/blood-city/reports/STATUS.md)
first: the build's size, every named place with its study and its last
critique, and what is open. The build writes it; it is never edited.

```bash
python projects/blood-city/level/status.py --place station   # one place and what is open on it
python projects/blood-city/level/status.py --kind refused    # one kind of open item
python projects/blood-city/level/status.py --wires           # the level's wiring (named in level/wires.py)
python projects/blood-city/level/build_skeleton.py     # about a minute; prints every pass
python projects/blood-city/level/look.py --set <poses> -o <dir>   # frames, as the game shows it
python -m tools.sprite_fit projects/blood-city/level/blood-city-current.MAP
python -m tools.critique prepare <slug> --poses <set> --kind <kind>
```

The build is deterministic and writes `level/blood-city-current.MAP`; what it
measured is in `reports/build-manifest.json`, and it ends by rewriting the
status. After recording a critique round, run `status.py` again. A new kind of place is studied
first (`tools.study`), named on the place in `level/character.py`, built, then
looked at. Your own reading of your own frames does not pass a place:
`tools.critique` hands them to blind readers, and the owner walking the map
outranks all of it.

## Things you must not do

- **Never start `nblood` or `eduke32` with a window, and never inject keys.**
  Looking is done by the XMapEdit observer from a pose
  (`bloodmap.visual.run_observation`, `look.py`). Playing is the owner's.
- **Never commit or delete anything under `maps/` or `reference/`.** They hold
  commercial game data, supplied locally. Renders of commercial maps and
  copies of them are gitignored for the same reason; do not force-add them.
- **Do not stage the `NBlood` or `xmapedit` submodule pointers** from this
  repository, and never run `git add -A` inside them.
- **Do not stash, reset or discard uncommitted work you did not make.** Copy a
  baseline aside instead.
- **Do not repair an original map to make it compile**, and do not normalise
  values on a lossless path. An original's oddity is evidence.

## When you finish

Say what you verified and how, and what you did not. If something a later
agent needs is only in your head -- a place's state, an open fault, a number
you measured -- put it in the repository where the next one will read it,
generated by a tool where possible. A page that can go stale will.
