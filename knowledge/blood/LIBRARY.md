# The library

One place to look anything up before building it. Started 2026-11-18 on
the owner's instruction: "that catalog needs to be coherent and usable ...
rather than tons of texts, it needs to be a real library you can use."

## What is on the shelves

| Shelf | What an entry is | Id | Where |
|---|---|---|---|
| Tiles | what a tile shows (class, layout, a name, themes), the owner's name for it, every way Blood uses it | the tile number | `design/tile-looks/`, `design/owner-anchors-v1.json`, `design/tile-usage-v1.json` |
| Places | one room of the campaign or curated maps: size, lettering, distinctive tiles, what stands in it, and its kind once somebody has looked | `MAP:sector` | `design/places-v1.json`, `design/place-labels/` |
| Studies | how Blood built one KIND of place, looked at and written up, with a ranked recipe | a slug (`crypt`) | `studies/<slug>/` |
| Ideas | one reusable idea seen on a tour, with a recipe | a card id | `ideas/cards/` |
| Mechanisms | what the engine does: every sector, wall and sprite type the campaign uses, every sector effect, every reserved channel and every tutorial lesson, each with maps that show it | `sector:614`, `effect:conveyor`, `channel:4`, `lesson:DOOR-SLIDING` | `design/mechanism-examples-v1.json` |

The owner's names outrank the mapper's readings wherever both exist.

## One vocabulary

Every tile reading and place label is written in the words of
`design/catalog-vocabulary.json`: 17 tile classes, 4 layouts, the theme
list, the place kinds. The tools refuse any other word. Add a word on
purpose (`python -m tools.catalog vocab add --list themes --word X`), so
one thing keeps one name and a search for it finds all of it.

## Using it

```bash
python -m tools.catalog find rail          # every shelf at once
python -m tools.catalog find conveyor      # ...a mechanic is found the same way
python -m tools.catalog show conveyor      # what it is, how often, where to look
python -m tools.catalog show sector:614    # a type: name, readings, examples, lessons
python -m tools.catalog record E3M5 sector 20   # only the fields that are set on it
python -m tools.catalog show 1129          # a tile: name, reading, uses, places
python -m tools.catalog show E1M2:271      # a place: kind, signs, distinctive tiles
python -m tools.tile_usage 1129            # the tile's picture and every context
python -m tools.study station --seed E1M2:271!   # look at a place, start a study
python -m tools.ideas list --grep curtain  # idea cards
python -m tools.catalog status             # how much is catalogued
```

## The loop

1. **Want** something ("a railway station").
2. **Find**: `catalog find rail train ticket` gives tiles, then the places
   that wear them. No guessing at map names.
3. **Look**: `study` renders those places as the game shows them.
4. **Write**: the study's notes and recipe.
5. **File** whatever was learned on the way: `catalog look` for a tile
   read, `catalog label` for a place identified, `ideas add` for an idea.
   Every search leaves the library better than it found it.
6. **Build**, and name the study on the place (`character.py`).

## Scales and confidence

A label says what something IS at one of four scales -- a `map`, a
`venue` in it, a `place` (one room), a `thing` in the room (a bed, a pew,
a train car) -- and how it is known: `seen` (somebody looked at a frame),
`inferred` (read from fields or lettering), or `guessed`.

`python -m tools.catalog guess` files the library's own hypotheses: a kind
for every place whose rare tiles agree on a theme, with the tiles as
evidence. A guess is somewhere to LOOK. A label a reader records always
outranks it.

## Mechanisms

Three questions, in the order an agent has them.

**What is it, and where can I see one?** `find` a word, then `show` the key
it gives. An entry is a dozen lines: the engine's name, how many the
campaign has and in how many maps, eight instances spread across the
campaign, what the mechanism reader made of the moving ones, the tutorial
lessons that teach it, and the three commands to run next.

```bash
python -m tools.catalog find lift           # lessons, types, effects, channels
python -m tools.catalog show kSwitchToggle  # by key, by engine name, or by word
python -m tools.catalog show lesson:MACHINERY-LIFT
```

**How is that one set up?** `record` prints one object as the fields that
are set on it and nothing else -- the values to copy.

```bash
python -m tools.catalog record E3M5 sector 20
#   extension: state=1, busy=65536, pan_floor=1, drag=1, pan_velocity=64, pan_angle=1024
```

**What is it wired to?**

```bash
python -m tools.catalog mechanisms E2M4            # every chain a player can set off
python -m tools.catalog mechanisms E2M4 --place E2M4:613
```

A chain starts at something a player causes (push, shot, enter, pickup,
or the level starting) and is followed through every channel and relay to
what finally moves, with the type of each receiver named. The deepest
chains are printed first: they are the ones worth a study.

An effect is defined by which XSECTOR fields are set (`bloodmap.examples.EFFECTS`)
and by nothing else; a type's name is the engine's own; a lesson is a file. None
of it says what a thing does when it runs -- follow an example for that. Rebuild
after the corpus, the curriculum or a constructor's docstring changes:
`python -m tools.catalog build-mechanisms` (three seconds; a test fails while it
is stale).

## Adding to it

```bash
python -m tools.catalog sheets                       # tile pages to read
python -m tools.catalog look 1129 --class material --layout band \
    --depicts "railway track with sleepers" --themes rail,floor --part NAME
python -m tools.catalog look-batch FILE.json --part NAME    # many at once
python -m tools.catalog label E1M2:271 --kind station --note "waiting hall" --part NAME
python -m tools.catalog build-places                 # after the corpus changes
```

`--part` is who looked: each reader writes its own part file, so a fleet
of agents can fill the shelves at once without collisions.
