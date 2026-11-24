# The library

One place to look anything up before building it. Started 2026-11-18 on
the owner's instruction: "that catalog needs to be coherent and usable ...
rather than tons of texts, it needs to be a real library you can use."

## What is on the shelves

| Shelf | What an entry is | Id | Where |
|---|---|---|---|
| Tiles | what a tile shows (class, layout, a name, themes), the owner's name for it, every way Blood uses it | the tile number | `design/tile-looks/`, `design/owner-anchors-v1.json`, `design/tile-usage-v1.json` |
| Tile contexts | what a tile is used as, in which slot and kind of place, and whose evidence says so: the owner's word, then counts over the campaign, the owner's own maps, the curated, multiplayer and community maps, then agents' readings; agents add readings as they learn | the tile number, or a slot and a place | `tile-contexts/` (`python -m tools.tile_contexts`) |
| Places | one room of the campaign or curated maps: size, lettering, distinctive tiles, its member sectors, what works and stands in it (by the Mechanisms keys), and its kind once somebody has looked | `MAP:sector` | `design/places-v1.json`, `design/place-labels/` |
| Compositions | sprite rings and squares, rings of pillars, concentric floors, round rooms, common facings and groups that share a centre | `MAP:sector` | `design/compositions-v1.json`, `design/compositions-community-v1.json` (`python -m tools.mine_compositions`) |
| Studies | how Blood built one KIND of place, looked at and written up, with a ranked recipe | a slug (`crypt`) | `studies/<slug>/` |
| Ideas | one reusable idea seen on a tour, with a recipe | a card id | `ideas/cards/` |
| Parts | what a mechanism is made of: every sector, wall and sprite type the campaign uses, every sector effect, every engine channel and every tutorial lesson, each with maps that show it, what sets it off and what it drives | `sector:614`, `effect:conveyor`, `channel:4`, `lesson:DOOR-SLIDING` | `design/mechanism-examples-v1.json` (`entries`) |
| What players wrote | each campaign level's Blood Wiki page as facts: designer, song, enemies per difficulty, secrets and their rewards, keys in the walkthrough's order, the words its walkthrough, secrets and trivia use; the prose itself is cached locally, not committed | the map (`E3M3`) | `wiki/levels.json` (`python -m tools.wiki_levels fetch`, `mine`, `show E3M3`; shown in `catalog map`, searched by `catalog find`) |
| Sounds | numbered SFX entries, sample lengths and loops, sourced descriptions, Whisper transcripts, and configured campaign uses with examples | `sound:3001` | `sounds.json` (`python -m tools.sound_catalog`) |
| Wiring | the mechanisms themselves: every shape of chain the campaign has, an act on a sender and what answers, with how often, how many are keyed, and where | words (`catalog wiring switch door`) | `design/mechanism-examples-v1.json` (`wiring`) |

The owner's names outrank the mapper's readings wherever both exist.

**A mechanism is not a part.** Blood has no door and no lift: it has sectors,
walls and sprites, and a layer of wiring over them in which an act makes one
object send and others answer. `kSectorZMotion` is 671 times something that
changes what fits through, 186 times something that carries a body between
levels, and four times in five it is moved by something else. So ask for a
mechanism by what happens (`catalog wiring switch lift`, `find door key`) and
read a part's entry for what it is set off by. Never pick a sector type and
call it the mechanism.

The wiring is a language, and the campaign writes it in phrases: a switch
that is shot instead of pushed (a breakable clock face), an act that ends at
the engine's secret counter, a cascade relayed through a room no player
reaches, something destroyed that drops a floor. `catalog idioms` lists each
phrase with how many of the campaign's 2,775 chains are written in it and the
commonest shape; `catalog wiring <phrase> <words>` finds them. A level of ours
says its own wiring the same way, on a `bloodmap.wiring.Circuit`: each wire
states what it is for, the circuit numbers the channel, and the build reads
the finished map back against it.

Places and Parts are joined both ways. A part's entry names the rooms
holding the most of it and each of its examples says which room it is in; a
place row lists what it holds under the part keys. So `find lift crypt`
answers with crypts that have a lift, `show conveyor` ends with the room to
go and stand in, and `record` says which room an object is in.

## One vocabulary

Every tile reading and place label is written in the words of
`design/catalog-vocabulary.json`: 17 tile classes, 4 layouts, the theme
list, the place kinds. The tools refuse any other word. Add a word on
purpose (`python -m tools.catalog vocab add --list themes --word X`), so
one thing keeps one name and a search for it finds all of it.

## Using it

```bash
python -m tools.catalog find rail          # every shelf at once
python -m tools.catalog map E1M1           # one whole map: rooms, how it ends, wiring, materials
python -m tools.catalog find conveyor      # ...a part is found the same way
python -m tools.catalog find door creaking open
python -m tools.catalog show sound:3001
python -m tools.catalog show conveyor      # what it is, how often, where to look
python -m tools.catalog show sector:614    # a type: readings, what sets it off, examples
python -m tools.catalog wiring switch door # mechanisms: an act, a sender, what answers
python -m tools.catalog idioms             # the phrases: shot switch, secret, cascade, closet relay ...
python -m tools.catalog wiring locked door # a phrase and a word together
python -m tools.catalog mechanisms E1M5 --place E1M5:160   # one room's chains in full
python -m tools.catalog record E3M5 sector 20   # only the fields that are set on it
python -m tools.catalog show 1129          # a tile: name, reading, uses, places
python -m tools.catalog show E1M2:271      # a place: kind, signs, tiles, what works in it
python -m tools.catalog find lift crypt    # words from two shelves: rooms that are both
python -m tools.mine_compositions find ring candle --min-count 5
python -m tools.mine_compositions find nest object
python -m tools.mine_compositions show E1M7:29
python -m tools.tile_usage 1129            # the tile's picture and every context
python -m tools.tile_contexts show 364     # a tile's contexts: slot, place, whose evidence
python -m tools.tile_contexts where two_sided_lower --place church   # what Blood puts there
python -m tools.tile_contexts discover <MAP>   # what a map does that nobody has shown
python -m tools.tile_contexts record 364 --slot two_sided_lower --is "..." --evidence "..."
python -m tools.study station --seed E1M2:271!   # look at a place, start a study
python -m tools.ideas list --grep curtain  # idea cards
python -m tools.catalog status             # how much is catalogued
```

## Compositions

The reader uses single-player load visibility, skips off-map control closets
and groups a room's local portals with its enclosed floor bands. A nest follows complete portal rims.
Sectors split by radial walls count as one band when their union closes the
rim at a common floor elevation. Levels run from outside in. A positive z
step measures a rise, a negative step a fall. Flat nests change floor tile
or shade. A ring records how many angular slots are empty. Four corners
with equal sides read as a square.
The miner gets five- and eight-view sprite directions from the local ART
metadata. [NBlood's sprite view pass](https://github.com/nukeykt/NBlood/blob/master/source/blood/src/view.cpp#L2598-L2651)

Groups compare each layer with the smallest ring or shape in the group.
The sorting score is the number of agreeing layers, plus up to 0.8 for
regularity and 0.19 for member count. Two readings of the same sprites
contribute one layer. Search words can come from different layers, the centre
object, or the room label. Use `object` to require a visible centre sprite.

`python -m tools.mine_compositions mine --serial` refreshes the named shelf.
The `campaign` source is the single-player campaign. The `curated` source
covers the remaining named maps, with their corpus provenance on each row.
Add `--community` to mine the bulk archive with the process pool, or add
`--serial` where pools are unavailable. The community shelf skips known
Duke conversions and keeps groups with at least two layers and rings with
at least five sprites. Its 3 MB budget retains the highest scores.

The [campaign audit](design/compositions-audit.md) records the native geometry
checked for the first shelf.

## Sounds

Search by the words in the recording or the description. A sound entry
shows both when they disagree. Ronald Allen's 1997 list is credited on each
entry it describes. Archive-name readings and engine use are credited
separately. Whisper confidence is the geometric mean token probability,
with the model's no-speech probability alongside it.
The shelf keeps the decoded wording when a name, engine call, or published
caption supports a correction. Cabal spellings cite the vocabulary used
to interpret those sounds. Entries marked unresolved have speech evidence
but conflicting or unintelligible decodes.

The shelf covers the numbered SFX namespace in `SOUNDS.RFF`. MIDI and
standalone WAV resources use separate namespaces. Duration is one pass at
the header's format rate, with nominal pitched 3D duration also shown if
different. Campaign counts are sound slots, including indirect glass sounds
from XWALL gib types. Sector movement sounds live on sprites in the sector.

Regenerate with `python -m tools.sound_catalog --transcribe` and the cached
Whisper medium.en weights. The miner takes Allen's supplied list from
`work/briefs/sector_ambient_sfx.json` (override with `--published`). It
writes WAVs and decoding scores to `work/sound-catalog/`. An existing
shelf supplies the published descriptions when the brief is absent.
With cached decodes, run `python -m tools.sound_catalog` to rebuild the
shelf. Use
`--verify ID ...` for a second decode with full context and timestamps.

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
python -m tools.catalog build-places                 # after the corpus changes (ten seconds)
python -m tools.catalog build-mechanisms             # then this: it reads the rooms from the places
```

`--part` is who looked: each reader writes its own part file, so a fleet
of agents can fill the shelves at once without collisions.
