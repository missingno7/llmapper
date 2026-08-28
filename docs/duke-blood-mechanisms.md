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
| SE31 / SE32 endpoint controller | `MovingSector(floor/ceiling)` | type 600 off/on surface values; speed follows effector shade, not GPSPEED; same Push/Wallpush vs RX split | faithful |
| SE15 horizontal controller | `MovingSector(translation)` | type 616, markers at angle 0, travel `16 * (sector.extra >> 3)` | faithful |
| ST30 + SE0/SE1 + MasterSwitch group | `MovingSector(rotation + z)` | type 617, marker angle `2 * sector.extra` signed by `pal`, plus the floor endpoint | faithful for recovered groups |
| SE11 / ST23 swinging door | `MovingSector(rotation)` | type 617, axis at the effector, marker angle a signed 512 -- `ang > 1024` turns positive | faithful |
| SE20 / ST27 stretch bridge | `StretchSector` | type **614**, marked slide: only the two walls nearest the effector carry `cstat & 16384` | faithful |
| SE10 autoclose timer | `DoorAutoclose` | XSECTOR `wait_time_a` plus `retrigger_a` on the host door (DNE3L1); `wait_time_b` stays 0 | semantically approximated |
| SE7 pair in ST1/ST2 sectors | `WaterLink` | Blood upper/lower-water markers | faithful |
| Paired SE7, both ONFLOORZ, not water | `TeleportLink` | type 604 plus warp destination marker; `dudeLockout` so only the player fires enter | faithful |
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

- On the floor, with sector lotag 0: the player must be grounded; flash teleport
  to the destination SE xyz. Blood type 604 plus warp dest (type 8).
- Off the floor: silent relative XY teleport when `|SE.z - player.z| < 6144`.
  Used for hatches and manholes. Blood type 604 fires on sector enter, so this
  path becomes stack markers (types 11/12) when the two sectors are congruent
  copies, otherwise physical room-link markers (types 7/6). Pairing is XSPRITE
  `data_1`, matching water markers.
- ST1+ST2 pairs remain Blood water markers 9/10.

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
