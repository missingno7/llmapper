# Blood mechanics, and what the campaign actually does with them

Two questions, answered against two different authorities. What the engine
*does* comes from NBlood's source, cited by file and function. What the
designers *did* comes from the 43 campaign maps, counted.

Neither is allowed to stand in for the other. A mechanic NBlood implements that
no campaign map uses is still a mechanic; a convention 40 maps follow is still
only a convention.

## Type coverage

Every type id, sector type, wall type and command in the 43 campaign maps now
resolves to a named entry or to an explicit anomaly. Before this pass, **5,855
occurrences did not**:

| Gap | Occurrences | What it was |
| --- | --- | --- |
| sprite 201–253 | 4,400 | every enemy in the game; the catalog had no `kDude` at all |
| sprite 459 | 1,085 in 31 maps | `kTrapExploder`, the most common typed sprite in the corpus |
| sprite 413, 418–432, 452–456 | ~90 | the rest of the thing and trap ranges |
| command 64–81 | 325 in all 43 maps | `kCmdNumberic`: a number, not an instruction |
| sector 607 | 3 | no case anywhere in NBlood |
| sprite 136, 455, 457, 458 | 14 | gaps in the item and trap ranges, no engine case |

The last two rows are recorded as `category: "anomaly"` with the reason. They are
in the data and the engine does nothing with them, and saying so is the answer.

### `kCmdNumberic` is the one that matters

A command of 64 or more is not an instruction. It carries the number
`command - 64`, and **what the number means is decided by the channel it travels
on** (`eventq.cpp:377-398`):

| tx channel | call | means |
| --- | --- | --- |
| 1 `kChannelSetTotalSecrets` | `levelSetupSecret(n)` | the level has n secrets |
| 2 `kChannelSecretFound` | `levelTriggerSecret(n)` | secret n has been found |
| 3 `kChannelTextOver` | `trTextOver(n)` | show level message n |
| 6 `kChannelModernEndLevelCustom` | `levelEndLevelCustom(n)` | end to level n (gModernMap) |

A command table on its own cannot read a Blood map. `NUMERIC_COMMAND_MEANING`
carries the pairing.

## Where the player actually is

Three facts, each of which llmapper had wrong, and each of which breaks
everything downstream when it is wrong.

**The spawn is a marker, not the header.** `warpInit` overrides
`gStartZone[data1]` from a `kMarkerSPStart` whose `XSPRITE.data1` is 0, then
deletes the sprite (`warp.cpp`). The map header's start is only the fallback
(`blood.cpp:724`). All 43 campaign maps carry the marker, and **the header
disagrees with it on 37 of them**. Taking the first `kMarkerSPStart` by sprite
index instead is wrong on E3M7, E4M3 and E6M7 — the others are coop slots.

**Sectors are joined by markers as well as by walls.** An up-family marker
(`kMarkerUpLink`/`UpWater`/`UpStack`/`UpGoo`) pairs with the low-family marker
whose `XSPRITE.data1` matches. A `kSectorTeleport` reaches the sector its
`XSECTOR.marker0` destination sits in (`triggers.cpp` `OperateTeleport`).

**Gating is not reachability.** A closed door is still a portal. Whether the
geometry is part of the level and when the player gets through it are different
questions.

Crossing walls alone leaves a median **8.5%** of each campaign map unreachable
and, on E6M5, 97% of it. Crossing links and teleports as well leaves **2.8%**,
median, and never more than 13.8%.

## What the remaining 2.8% is

Not level design, and not noise either. Three distinct things, and reading them
as rooms is how a shape corpus ends up measuring letterforms.

### Logic closets — 52 of them, in 39 of 43 maps

A **single sector**, always, packed with switches and generators, wired to the
level by channel rather than by geometry. Every one of the 52 is one sector.

| map | switches | generators |
| --- | --- | --- |
| E1M6 | 67 | 7 |
| E3M4 | 44 | 3 |
| E6M1 | 44 | 1 |
| E2M7 | 42 | 0 |
| E1M2 | 41 | 1 |

Median 11 switches. 26 maps have exactly one closet, 13 have two, 4 have none.
This is the level's control panel. Reading it as a room is wrong; reading it as
the trigger wiring is right.

### Signatures — 153 sectors, in 15 of 43 maps

Nine sectors of 10 to 19 vertices each, all at the same floor and ceiling,
carrying nothing, laid out in a row 21 by 3 player widths. They are letters. The
stamp reads **"croweater"** and is the same seven distinct outlines every time —
two letters repeat — copied whole into E1M2, E1M5, E2M1, E2M3, E2M4, E3M2, E3M4,
E3M7, E3M8, E4M2, E4M7, E4M8, E4M9 and twice into E2M2 and E4M3, plus BB3 and
BB5.

E2M3 has it. Before this pass, its emitted level program built those nine
letters as nine ordinary rooms.

The outlines are stored in `knowledge/blood/offmap-signature-glyphs.json` as
data rather than as a rule: a map without them is not penalised, and a handle
this has never seen falls through to `bare` rather than being guessed at.

### Helpers, bare and sealed

The rest: link and warp destinations, sectors carrying nothing at all (144
components, median one sector and 2.6 player areas), and unreachable geometry
that does carry content. `bare` is deliberately not a verdict — it holds
unrecognised signatures, scenery and things nobody finished, and this does not
pretend to tell them apart.

## How secrets are declared

Verified end to end, and a genuine authoring convention:

* a sprite transmitting on **channel 1** with command `64 + n` declares that the
  level has *n* secrets — 42 of 43 maps do this;
* an object transmitting on **channel 2** with command `64 + n` *is* secret *n*
  — 40 of 43 maps, and it is usually a **sector** you walk into (153 sectors
  against 74 sprites);
* `levelSetupSecret` calls `SetCount`, not an add, so two objects declaring
  different totals means the last one processed wins.

Declared totals run from 2 (E2M2) to 17 (E2M4).

## What this changes

| Consumer | Before | After |
| --- | --- | --- |
| `tools/propose_areas` | grouped closets and letters with rooms | excludes them, and records what it left out |
| `tools/observe` | planned camera poses inside letters | 156 views on E2M3 instead of 163 |
| `tools/emit_level_program` | nine letters as nine rooms | `build_offmap_signature_007()` with a docstring saying what it is |
| `bloodmap.blood_types` | 5,855 unknown occurrences | zero |

`design_sectors(disk)` is the one call a statistic about level design should go
through. It returns what the player can reach, and takes `keep=` for the rare
case where an off-map kind is the thing being measured.

## Still not modelled

* **When** a gated sector opens. `analyze_progression` models key and switch
  order; this module deliberately does not.
* Reachability that needs a jump, a lift ride or a broken wall. Those are
  counted through their portal, never by simulating a player.
* `kSectorPath`, rotating and sliding sectors move geometry, and a sector that
  moves may open a route this treats as always open.
* Blood's modern (`gModernMap`) types. The campaign does not use them.
