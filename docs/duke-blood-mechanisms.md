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
| SE15 horizontal controller | `MovingSector(translation)` | type 616 with off/on markers along the SE angle; GPSPEED becomes `busy_time` | faithful for supported two-marker geometry |
| ST30 + SE0/SE1 + MasterSwitch group | `MovingSector(rotation)` | type 617 with an axis marker and recovered MasterSwitch RX channel; GPSPEED becomes `busy_time` | faithful for recovered groups |
| SE11 / ST23 swinging door | `MovingSector(rotation)` | type 617 with axis at the effector; T4 sign from SE angle | faithful |
| SE20 / ST27 stretch bridge | `MovingSector(translation)` | type 616 two-marker slide along the SE angle | semantically approximated (DNE3L3 used marked-slide 614 on rebuilt geometry) |
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
