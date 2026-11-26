# Duke3D to Blood mechanism correspondences

This document records only source-backed semantic rules. It is deliberately not a
table that equates numeric tags between games.

## Evidence trail

- EDuke32 `source/duke3d/src/game.h` names Sector Effector and tagged-sector
  families; `actors.cpp` executes their runtime behavior; `sector.cpp` resolves
  activators and MasterSwitches.
- NBlood `source/blood/src/common_game.h` names Blood sector, wall, marker, and
  trap types; `triggers.cpp` operates them; `sectorfx.cpp` applies XSECTOR
  lighting.
- `bloodmap.duke_semantics.analyze_duke_mechanisms` turns those relationships into
  a reusable per-map inventory. `llmapper duke-mechanisms maps/duke3d` writes the
  corpus evidence used to find configurations across the original maps.

## Motion and activation

| Duke runtime meaning | Semantic mechanism | Blood lowering | Fidelity |
|---|---|---|---|
| ST20 / ST18 tagged-sector Z motion | `MovingSector(z)` | type 600; unbuttoned doors get XSECTOR `Push` **and** `Wallpush` (NBlood `ActionScan` uses Wallpush when the Use hitscan hits the portal wall from the adjacent room); buttoned doors are RX-only | faithful where endpoints can be inferred from adjacent sectors |
| SE31 / SE32 endpoint controller | `MovingSector(floor/ceiling)` | type 600 off/on surface values; speed follows sector extra copied into effector yvel; same Push/Wallpush vs RX split | faithful |
| SE15 horizontal controller | `MovingSector(translation)` | type 616, markers at angle 0, travel `16 * (sector.extra >> 3)` | faithful |
| ST30 + SE0/SE1 + MasterSwitch group | `MovingSector(rotation + z)` | type 617, marker angle `2 * sector.extra` signed by `pal`, plus the floor endpoint | faithful for recovered groups |
| SE11 / ST23 swinging door | `MovingSector(rotation)` | type 617, axis at the effector, first operation reverses spawn T4; angles above 1024 swing negative | faithful |
| SE20 / ST27 stretch bridge | `StretchSector` | type **614**, marked slide: only the two nearest vertices move; only their connecting edge carries `cstat & 16384` | faithful |
| SE10 autoclose timer | `DoorAutoclose` | XSECTOR return on the open end (A or B) of the host door | semantically approximated |
| SE7 pair in ST1/ST2 sectors | `WaterLink` | Blood upper/lower-water markers | faithful |
| SE7 ONFLOORZ in an untagged sector, targeting SE7 or SE23 | `TeleportLink` | directed type 604 plus warp destination marker; SE23 never generates a return route; `dudeLockout` so only the player fires enter | faithful transport direction; player-enter approximation |
| Paired SE7 off the floor (hatch/manhole) | `AirHatch` | congruent copies → stack markers 11/12; otherwise room-link 7/6 | faithful for stack, approximated for physical-only link |
| SE17 / ST15 warp elevator | `TeleportLink` | type 604 plus warp destination marker between cabins; `dudeLockout` | semantically approximated (cabin Z-motion is not reproduced) |
| ST16 platform down | `MovingSector(z)` | type 600 floor endpoint from the nearest neighbor floor | faithful where a neighbor floor exists |
| ST22 splitting door | `MovingSector(z)` | type 600 moving both surfaces; closed state is the midpoint | faithful |
| SE6 subway | `Subway` | listed, not lowered | unsupported |

NBlood `player.cpp` `ActionScan` is the Use/Open hitscan (range 64). A hit on an
XWALL `triggerPush` fires a wall trigger. A hit on a portal whose **next**
sector has XSECTOR `Wallpush` fires that sector. `Push` only fires if the player
is already in the sector or the hitscan strikes its floor/ceiling. Closed Duke
OPEN doors are used from the hallway, so Wallpush is required. DNE3L1 authors
both bits on unbuttoned type-600 doors and RX-only (no Push, no Wallpush) on
switch-operated ones.

Type 604 `data` is an unsigned 16-bit TeleFrag source sprite. NBlood writes `-1`
there when a non-player enters, which becomes 65535 and asserts in
`actDamageSprite`. Converted teleporters set `dudeLockout` so only the player
fires enter.

## Damage and effects

EDuke32 treats CRACK1--CRACK4 as damageable standable sprites. Qualifying impact
signals same-hitag SE13 controllers. At spawn, SE13 stores the authored ceiling
and floor Z, then snaps the sector to the effector Z (both surfaces, or one
surface when `ang == 512`). Detonation expands those surfaces back. The hole is
that Z-motion, not a wall becoming passable.

```text
Duke impact -> CRACK(hitag) -> SE13 group expands collapsed sector + explosion
Blood impact -> kThingWallCrack TX -> type 600 expand + hidden kTrapExploder
```

The crack sprite becomes Blood type 408 (`kThingWallCrack`, tile 1127, stat 4)
with TX command On, `trigger_on`/`trigger_off`, **Vector**, and **Impact**.

It rests at **state 0**, which 154 of the corpus's 155 cracks do and which the
conversion previously got wrong: `SetSpriteState` returns early when the state
already equals the one asked for, so a crack authored at state 1 and then
switched on never reaches its `evSend` and never opens its hole. Its cstat is
Blood's `1|16|64|128` plus the hitscan-block bit and its repeat is 64x64;
carrying the Duke sprite's cstat and repeat across kept translucency bits Blood
never uses, dropped the y-centering, and made a Blood-sized tile half scale.
The hitscan bit is the one deliberate departure from Blood's own 208/209:
Blood cracks are opened with explosives, Duke cracks are shot, and NBlood's
VectorScan only reaches a sprite that blocks hitscan.
NBlood `actFireVector` only issues `kCmdSpriteImpact` when XSPRITE.Vector is set;
`thingInfo` for type 408 has 0 bullet damage, so a hitscan without Vector never
reaches `trTriggerSprite`. Impact covers nearby TNT (Duke SEENINE). Matching SE13
sectors become type 600 starting at the collapsed OFF Z. A type-459 exploder is
placed on `kStatTraps` (stat 11) with `waitTime >= 1`; NBlood's `actInit` only
arms exploders on that stat. `kWallGib` (wall type 511) is a different Blood
machine (E1M1 uses it with wall Vector) and is not the SE13 hole chain.

Blood XSECTOR flags stack on one extra record. DNE3L11 marks every Duke ST2
sector underwater, including the SE13 holes in sectors 140/141. DWE1M1 authors a
type-600 door that is also underwater and still has Push+Wallpush. Converted
maps copy that combination: ST2 always gets `Underwater`; a type-600/616/617/604
sector that neighbors ST2 gets it as well, so a submerged door keeps swim
physics instead of dropping back to air in the doorway.

## SE7 teleport vs hatch

EDuke32 sets `ONFLOORZ` from `sprite.z == sector.floorz` at SE7 spawn.

Transport destinations are **not** inferred by counting SE7s. At EDuke32 commit
`ec5824db81817866f70da326d3811bb0f52b3517`, `A_Spawn` in
`reference/eduke32/source/duke3d/src/game.cpp:2916` scans ascending sprite indices
for the first other live SE7 **or SE23** with the same full signed hitag. There
is no preference for SE23 when both kinds match. More than two endpoints is a
valid directed graph. SE23 owns itself; `G_MoveTransports` in `actors.cpp:3908`
skips self-owned sprites, so SE23 is destination-only. The same initialization
leaves a genuinely unmatched SE7 self-owned and inactive.

The reported hitag 9017 is E4L1's SE7 sprite 1036 (sector 537) targeting SE23
sprite 1039 (sector 538). It is a valid one-way floor teleporter. The converter
now creates one type-604 source and a destination marker owned by sector 537,
with the SE23's scaled xyz and facing. Sector 538 gets no return teleporter.
The destination need not be on its floor. Coordinates outside the destination
volume are preserved and diagnosed, rather than clamped to an invented pad.

- On the floor, with sector lotag 0: the player must be grounded; flash teleport
  to the destination SE xyz. Blood type 604 plus warp dest (type 8).
- Off the floor: silent relative XY teleport when `|SE.z - player.z| < 6144`.
  Used for hatches and manholes. Blood type 604 fires on sector enter, so this
  path becomes stack markers (types 11/12) when the two sectors are congruent
  copies, otherwise physical room-link markers (types 7/6). Pairing is XSPRITE
  `data_1`, matching water markers.
- ST1+ST2 pairs remain Blood water markers 9/10.

Only reciprocal off-floor SE7 pairs become hatches. A mixed floor/off-floor
pair has different activation semantics in each direction: its floor route
can be lowered independently and its silent route is reported unsupported.
One-way water/silent routes and nonreciprocal water/hatch graphs are also
reported unsupported: paired Blood markers would invent reverse transport.
Multiple competing source transports in one sector, or transport combined
with sector motion, are diagnosed before any existing behavior is overwritten.

The conversion report's `diagnostics` list identifies unsupported routes by
hitag, source/destination sprite and sector, and includes every endpoint's
SE lotag, xyz, angle, sector lotag and ONFLOORZ state, with a reason and the
action taken. Source mechanisms also remain in `semantic_inventory`.

Other corpus compatibility checks found three additional development-board
assumptions:

- SE17 groups with other than two stops were silently skipped. They now have
  explicit unsupported diagnostics; EDuke32 selects stops using sector hitags
  and travel direction, so arbitrarily pairing them is unsafe.
- Failure of the static progression reader is a report warning, including
  absent exits and unproven dynamic progression. It no longer aborts conversion,
  and `guaranteed_exit_channel` is null when the reader cannot prove access.
  No replacement exits are generated.
- New-level sprite containment rules rejected outside motion markers, original
  header starts beyond a floor, and hidden timers in closed/crushing sectors.
  The converter retains these sector-assigned records and reports their
  coordinates. NBlood `db.cpp::PropagateMarkerReferences` binds motion/warp
  markers by `owner`, independent of containment. General `LevelBuilder`
  authoring rules are unchanged. Structural errors and real Blood record/channel
  limits still abort; the user-channel allocator rejects exhaustion at 1023.

`python -m unittest tests.test_duke_transport` checks synthetic directed graphs,
unsupported configurations, report writing, source preservation and every map
enumerated by `bloodmap.corpus.list_corpus_maps` in `DUKEMAP_CORPUS` (default
`maps/duke3d`). The corpus run is recorded in
`reports/duke_playable_compatibility.json`. It proves conversion/read-back and
structural validity, not that every level can be completed in Blood.

In the 46-map local run, the old converter completed 22 maps and aborted on 24;
all 46 now encode, reparse and validate. Nineteen of the previously successful
outputs remain byte-identical. Three intentionally change: E2L8 hitag 188 is
a mixed floor/silent pair, while E1L7 and E4L9 combine floor transport with
SE31/SE32 motion. The previous output overwrote those moving-sector behaviors
with teleports; the report now exposes the Blood representation conflict.

XMAPEDIT/NBlood's ROR helper makes the same split: congruent floor/ceiling copies
are stack, otherwise link.

SE12 light switches are converted to XSECTOR animated light pulses on the same
recovered tag channel; XSECTOR affects floor, ceiling, and wall shades together.
This preserves switch wiring and a perceptible light response, but not Duke's
exact permanent bright/dark state, so it is a semantic approximation. SE3/SE4
random lights become continuous XSECTOR flicker and remain visual-only
approximations.

## Explicit non-equivalence

SE2 earthquakes, SE8/SE9 door-linked lights, SE27 demo cameras, and SE33 quake
debris are not gameplay-lowered yet. The report retains them with their semantic
classifications. A map loading successfully must not be read as proof that those
effects are equivalent.


## Moving sectors have their own document

The extents, speeds and directions above are hardcoded in Duke and expressed as
marker sprites in Blood, and getting that translation wrong produces doors that
load, validate and still open a quarter of the way or swing 315 degrees the
wrong direction. [Duke's hardcoded moving sectors](duke-moving-sectors.md)
records each constant with the EDuke32 function it comes from, and
`tools/verify_motion` replays every converted mechanism in both engines and
compares the swept wall positions.

## Switches, difficulty, and other Blood conventions

**Switch art.** Tile 318 is Blood's *level-exit* lever: 59 of its 66 appearances
in the corpus transmit on channel 4. Using it for every converted switch tells
the player that every switch ends the level. Converted switches now draw from
what Blood actually authors -- 1070 for key readers (which carry keys 1-6 in 26
of the corpus's locked switches), 624 for light switches, 1046 for tech
switches, and `kSwitchCombo` with tile 1161 for Duke's multi-position
dipswitches -- and only the Duke NUKEBUTTON keeps 318.

**Difficulty.** EDuke32 deletes a spawned actor when
`sprite.lotag > ud.player_skill`, so an actor's lotag is the lowest difficulty it
appears on. Blood inverts the question: `blood.cpp` deletes a sprite when
`lSkill & (1 << difficulty)`, so a set bit means *absent*. A Duke threshold of
*n* is therefore `(1 << n) - 1`, and Blood's own maps author exactly that ladder
-- the non-zero masks on its 8,656 typed dudes are dominated by 7, 15, 3 and 1.
E3L11 gates 49 of its 88 enemies this way; before this pass all 88 spawned on
every difficulty.

Only actors carry a skill threshold in their lotag. On everything else the lotag
means something else entirely -- a switch's lotag is its channel -- so reading it
as difficulty there would delete working machinery on the easier settings.

**Sprites over a collapsed sector.** An SE13 sector starts collapsed, so its
floor is not where the Duke mapper placed the things standing on it. Duke gets
away with it because its items fall; a Blood pickup keeps its authored z, so
anything left at the old floor height ends up inside the new one. Conversion
re-seats what the collapse moved, and only that.

**The player start.** Blood decides the spawn from a `kMarkerSPStart` whose
`XSPRITE.data1` is 0, which `warpInit` reads and then deletes; the map header is
only the fallback. All 43 campaign maps carry the marker, so a converted map
without one relies on a path no authored Blood level uses.

## Chained explosives, and why they are not barrels

A Duke SEENINE is not scenery. `game.cpp` zeroes its size and marks it invisible
whenever its `xrepeat` is 8 or less, and **all 61 of E3L11's are authored at 4**,
so the whole thing is hidden machinery. Converting them as visible TNT barrels
puts 61 barrels through a level that Duke never shows one in.

The mechanism is a timed chain. Damaging one SEENINE sets shade -32 on every
SEENINE sharing its **hitag**, and each then counts its own **lotag** down by 3
per 30 Hz tick before detonating (`actors.cpp`). So the hitag is the chain and
the lotag is a fuse. E3L11 authors ten cascades with fuses from 0 to 220, which
is nearly three seconds of staggered explosions.

`kTrapExploder` is the same machine. `trInit` clamps its `waitTime` to at least
1; `SetSpriteState` posts `kCmdOff` after `waitTime` tenths of a second when the
trap is switched on, and `OperateSprite` explodes it on anything that is not
`kCmdOn`. One RX channel plus a per-sprite `waitTime` of `lotag / 9` reproduces
the cascade exactly, and NBlood's `actInit` only arms exploders on `kStatTraps`.

Duke's tag numbering wires it for free: the touchplate that starts the sequence,
the MasterSwitch relaying it and the SEENINE group all carry the same number.
A hitag of 0 is *not* a group -- Duke chains on equal hitags, so a lone explosive
left at 0 belongs to nothing and is only ever set off by another blast reaching
it, which Blood's radius damage does too.

Duke RESPAWN (tile 9) has an exact Blood counterpart in `kMarkerDudeSpawn`: both
listen on a channel and spawn the actor named by a field when it fires.

## Two Blood objects that look wired and are not

**`kSwitchCombo` is a combination lock, not a toggle.** `OperateSprite` counts
`data1` up, wraps it at `data3`, and fires only when `data1 == data2`. A combo
switch left with all three at 0 steps to 1, can never match 0 again, and is dead
for the rest of the level. Duke's DIPSWITCH2 is a toggle the player flips, so it
lowers to `kSwitchToggle`. `data1` and `data2` on a toggle are its on and off
**sound ids**, not data; Blood authors 200 for both.

**A sprite is only pressable if `Push` is set**, because `trInit` derives the
hitscan bit from it -- `if (pXSprite->Push) sprite[i].cstat |= 4096` -- and
`ActionScan` scans with a sprite clip mask of exactly 4096. None of the 887
pushable switch sprites in the Blood corpus carries that bit on disk; the engine
adds it. Setting `Vector` does the same for `CSTAT_SPRITE_BLOCK_HITSCAN`.

## Where a moving sector rests

`trInit` does not treat the authored geometry as the resting pose. For a slide or
rotate sector it calls `TranslateSector` once at `busy = -65536` -- a full travel
*backwards* -- calls `setBaseWallSect` to make that the reference, and only then
moves to the sector's real `busy`. The coordinates in the MAP are therefore the
pose at `busy == 1`, and **a sector left at state 0 displaces itself by the whole
marker separation the moment the level loads**.

That is why a door converted closed with `state = 0` slides itself open on level
start and its switch then closes it. Converted movers rest at state 1, which puts
them back on their authored coordinates, and their markers point the other way so
the actuated pose is still the correct end of the travel.

## Touchplates, and why a converted one can do nothing at all

A Duke touchplate fires when a player is in **its sector** and on the ground
(`actors.cpp`), calling `G_OperateMasterSwitches(lotag)` and
`G_OperateActivators(lotag)`. Its **hitag is a use count**, not a flag: it counts
down on each activation and the plate is spent when it reaches zero, so a hitag
of 1 is one-shot and 0 is unlimited.

The Blood side has a trap in it. `trTriggerSector` sends the channel directly
only when `decoupled` is set, and 865 of the corpus's 885 Enter-plus-TX sectors
do **not** set it. They go through `OperateSector`, which for an untyped sector
falls to `SetSectorState(state ^ 1)`, and *that* only reaches its `evSend` when
`triggerOn && state` (or `triggerOff` and not state). A converted plate with
neither bit flips its own state and tells nobody: it looks completely wired in
the map file and does nothing in the game. 878 of the 885 set `triggerOn`, 751
of them in exactly the `(on=1, off=0, state=0)` shape.

Two further interactions matter:

* `busyTimeA`/`busyTimeB` send `OperateSector` down `OperateDoor` instead, so a
  plate sharing its sector with an SE12 light pulse transmits at the end of the
  busy rather than on the step. A delay, not a failure -- E3L11's sector 196.
* A plate can share its sector with a *moving* sector -- E1L3 puts one inside
  two of its rotate bridges. Movers rest at state 1 so their authored geometry
  is their resting pose, so the plate must not write `state`, and transmitting
  on both transitions makes it work from whichever state its sector rests in.

## What actually arms a chain, and what actually receives a channel

**A MasterSwitch is a receiver too.** When its channel fires it counts its hitag
down and then calls `G_OperateSectors` on *its own sector* -- exactly what an
ACTIVATOR does, with a delay. 168 MasterSwitches in the corpus sit in an operable
sector with no ACTIVATOR beside them, so treating only ACTIVATOR and
ACTIVATORLOCKED as receivers leaves those sectors deaf.

The hitag countdown is a delay line at 30 Hz, and Blood sends a channel
immediately with no per-link delay, so the wait is lost. It is recorded as
`masterswitch-delay` rather than dropped silently: E3L11's fifth bridge is meant
to swing 3.3 seconds after the other four.

**An explosive group is armed on the MasterSwitch's channel, not its hitag.**
The MasterSwitch sets shade -31 on the explosives in its own sector, and that one
chain-arms everything sharing its hitag. E3L11's group 50 is armed by the
MasterSwitch on 49 that also turns the bridges, so keying it to 50 left ten
explosives listening to a channel nobody sends. Groups with no MasterSwitch keep
their hitag, which is what their CRACK transmits on.

## Where an ST30 bridge actually turns

The ST30 branch of the movement code never touches the effector's position: it
leaves `xvel` at 0 and never assigns `sprite->x` from the pivot, unlike the
orbiting branch. So the sector turns about **the effector**, and spawn moves the
effector onto the SE1 pivot only when its angle is exactly 512. An SE0 authored
at any other angle turns about itself, and using the pivot for it swings the
sector through an arc it never travels -- E3L11's fifth bridge is authored at
1536 and is the one that does this.


## Motion audit and the boundary of automatic conversion (2026-11-24)

E4L1 exposed defects that structural validity and normalized own-polygon
sweeps could not establish. ST23 negates the SE11 spawn direction before the
first movement; ST25 adds 1024 to SE15 before moving. Using the authored
rather than activated direction swung door 50 through its adjoining
sector 389. The corrected sweep has no introduced fold in that neighbour.

`duke_motion.tagged_z_motion` reads strict directional neighbour heights and
Duke load state for ST16-22. It derives duration from travel / (sector extra
* TICSPERFRAME), at 30 updates per second, then rounds to Blood tenths. It
supports ST17/19/21 as well as previously handled tags, and reports unusable
non-positive speeds without inventing replacements. Motion uses linear Blood
wave 1. SE31/32 inherit sector extra in sprite.yvel at spawn. SE10 hitag is a
30Hz counter; a rotation's opened state is OFF, so its return belongs on B.
The remaining timer is estimated after subtracting opening travel. Presence
holds, exact timer phase, and engine tick quantization remain approximations.

SE20 selects two vertices. Blood's marked-wall translation carries point2
implicitly: flag their connecting edge once, not both vertices. ST30 Z
endpoints must also respect the state-1 load convention. Its rotation is
64*(extra>>5), equal to 2*extra only for multiples of 32. Unequal simultaneous
Z/rotation durations are reported as an approximation. Independent SE12 light
controls cannot overwrite a mover's RX, duration or return settings. Independent
SE13/horizontal motion conflicts are diagnosed rather than changing a rotor
into a Z-only sector.

`tools.verify_motion` now records timing and native waves, source and target
hashes, and every neighbour loop reached by Duke/Blood DragPoint calls. Its
`--converted` option audits an existing editable Blood MAP without writing it.
`--corpus` enumerates through `bloodmap.corpus`. The 46-map audit is in
`reports/duke-motion-compatibility.json`: 379 modeled horizontal motions pass
sampled geometric comparison, including affected loops, within 2 Blood units.
This is model verification, not a runtime or finishability guarantee.

The conversion report's `mechanisms.coverage` and per-object warning diagnostics
separate actual lowering from theoretical family support. Tagged vertex/compound
doors, coupled local leaves, independent control conflicts, locks, secrets,
sounds and MasterSwitch choreography can require manual authoring. The user
explicitly accepts that boundary. Do not invent endpoints, force unrelated
mechanisms together or equate a successful conversion with full gameplay parity.
E4L1's itemized list and guarded native repair are recorded in
`projects/duke-e4l1-remake/reports/converter-mechanism-audit.md`.

SE11 does not imply an operable door by itself. In sector.cpp, ST23 finds its
local SE11 and arms the same-hitag group; actors.cpp runs movement only while
that group's counter is active. E4L1's plain room 152 contains SE11 sprite
487, hitag 409, with no same-hitag ST23 operator. E1L2 room 262 is another
case. These controllers stay intentionally inactive, with a source-specific
diagnostic, rather than becoming invented Push rotors. A plain-sector SE11
member of a group with an actual ST23 operator still gets its geometry
lowered, without an invented local Use action; shared activation needs the
linked-group treatment recorded in coverage. E4L1 room 152 retains its entry
signal; its independent SE12 light conflict is diagnosed separately.

The earlier room-389 bathroom label was incorrect. Actual E4L1 toilet and
urinal sprites identify rooms 58/59/119/152; valid stall door 61 uses SE11
hitag 408. The guarded local repair retires the generated room-152 marker
in place and preserves the real door and source geometry.
