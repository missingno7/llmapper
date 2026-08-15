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
| ST20 / ST18 tagged-sector Z motion | `MovingSector(z)` | XSECTOR + sector type 600 endpoints | faithful where endpoints can be inferred from adjacent sectors |
| SE31 / SE32 endpoint controller | `MovingSector(floor/ceiling)` | type 600 off/on surface values | faithful |
| SE15 horizontal controller | `MovingSector(translation)` | type 616 with off/on markers | faithful for supported two-marker geometry |
| ST30 + SE0/SE1 + MasterSwitch group | `MovingSector(rotation)` | type 617 with an axis marker and recovered MasterSwitch RX channel | faithful for recovered groups |
| SE7 pair in ST1/ST2 sectors | `WaterLink` | Blood upper/lower-water markers | faithful |
| Other paired SE7 endpoints | `TeleportLink` | type 604 plus warp destination marker | faithful |

## Damage and effects

EDuke32 treats CRACK1--CRACK4 as damageable standable sprites. Qualifying impact
signals same-hitag SE13 controllers, which alter architecture and can create
explosion/debris effects. This is modeled as a behavior graph, not a crack decal:

```text
Duke impact -> CRACK(hitag) -> SE13 group
Blood impact -> kWallGib -> TX channel -> hidden exploder
```

The converter projects a crack to a unique wall in its containing sector (within
eight Duke units). That wall becomes type 511 `kWallGib`, with vector impact
enabled and initially blocking. NBlood's `OperateWall` clears movement/hitscan
blocking on impact, emits the TX command, and its hidden type-459 exploder handles
the linked blast. An ambiguous crack is reported as unsupported rather than bound
to a nearby arbitrary wall.

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
