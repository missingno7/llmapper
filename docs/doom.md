# Classic Doom support

Supporting Doom does **not** mean `BuildIR` is a universal engine IR.

```text
Doom native (WAD / VERTEXES / LINEDEFS / SIDEDEFS / SECTORS / THINGS)
        ↓
verified Doom runtime semantics (GZDoom xlat + maploader)
        ↓
game-neutral SemanticLevel / SemanticMechanism
        ↓
Blood LevelIR construction
```

Blood and Duke still share Build, so a shared `BuildIR` cannot prove that
higher abstractions are engine-independent. Doom is the experiment that can.

## Format scope

The first implementation reads original Doom / Doom II **classic binary maps**.

Authoritative sources:

- GZDoom `src/doomdata.h` record layouts
- GZDoom `src/common/filesystem/source/file_wad.cpp` WAD directory
- GZDoom `src/maploader/maploader.cpp` `LoadVertexes` / `LoadLineDefs` /
  `LoadSectors` / `LoadThings`
- GZDoom `wadsrc/static/xlat/base.txt` and `xlat/doom.txt` special translation
- GZDoom `wadsrc/static/mapinfo/doomitems.txt` thing editor numbers
- NBlood `source/tools/src/wad2map.cpp` Doom→Build scale and sector chaining
- `maps/blood/TEDE1M9.MAP` Blood-native recreation of Doom E1M1 (scale/height oracle)

Explicitly **out of scope**: Hexen-format (`BEHAVIOR`), UDMF (`TEXTMAP`), Boom
generalized linedefs, ACS, 3D floors, and arbitrary ZDoom extensions. Those
maps are classified and rejected rather than decoded.

## Native representation

`bloodmap.doom.WadFile` / `DoomDiskMap` reconstruct THINGS, LINEDEFS, SIDEDEFS,
VERTEXES, and SECTORS from decoded fields. SEGS, SSECTORS, NODES, REJECT,
BLOCKMAP, and non-map lumps stay opaque. Mutation tests change a decoded field
and require the rebuilt lump bytes to change.

Whole-WAD roundtrip of unmodified IWADs patches reconstructed lumps into the
original layout when sizes match, so commercial WAD bytes can roundtrip without
keeping those lump bytes as a hidden encoder shortcut.

```text
python -m bloodmap doom-corpus maps/doom/doom.wad -o work/doom-corpus.json
python -m bloodmap doom-mechanisms maps/doom/doom.wad --map E1M1
python -m bloodmap convert-doom maps/doom/doom.wad --map E1M1 \
  -o work/E1M1-BLOOD.MAP --report work/E1M1-BLOOD.report.json
```

## Geometry: Doom sectors are not Build sectors

A Doom sector is the set of sidedefs that name it. A Build sector owns a
contiguous wall loop (outer, then holes) with reciprocal `next_wall` /
`next_sector` portals.

The converter traces directed sidedef edges, Y-flips into Build screen space,
reverses winding so outer loops are clockwise, and pairs two-sided linedefs as
portals. This is a **geometric translation**, not an identity:

```text
Doom linedef ≠ Build wall
```

except at that translation step. Disconnected extra outer loops, self-referencing
sectors, and unclosed chains are reported; they are not silently repaired.

## Scale

XY and Z follow Ken Silverman's `wad2map.cpp` in NBlood
(`reference/NBlood/source/tools/src/wad2map.cpp`), confirmed against
`maps/blood/TEDE1M9.MAP` (a Blood-native recreation of Doom E1M1):

| Axis | Ratio | Evidence |
|---|---|---|
| XY | 16 | `wad2map`: `((vertex - centroid) << 4)`; TEDE1M9 wall-vector overlap peaks at ×16 with Y-flip |
| Z | 256 | `wad2map`: `sector.z = -(doom_z << 8)`; TEDE1M9 floor/ceiling hits peak at ×256 |
| Angle | `2048 - deg*2048/360` | Y-flip mirrors yaw |
| Light | `28 - (light >> 3)` | `wad2map` shade |

`wad2map` also subtracts the map centroid. This converter does **not**: converted
coordinates are a pure function of Doom vertices so reports stay comparable.

Typical Doom door 64 becomes Build 1024. That is narrower than Blood's
construction `min_width` 2048; the construction limit is a Blood authoring
constraint, not the Doom→Build scale.

Doom XY and Z share a unit. Build Z is a separate axis (positive down).

## Sector composition

`wad2map` and this converter both keep **one Build sector per Doom sector**.
Each Doom sector's sidedefs are collected as directed edges and chained into
wall loops with reciprocal portals.

`TEDE1M9` has more sectors than Doom E1M1 (105 vs 88). It is a Blood-native
recreation with extra splits and detailing, not a mechanical 1:1 conversion.
Use it as a scale/height/style oracle, not as a sector-index oracle.

## Semantic mechanisms

`bloodmap.mechanisms` is the engine-neutral layer. A keyed door is:

```text
Doom linedef special 26 + tag 0 (back sector)
    ↓ runtime: USE Door_LockedRaise, blue card or skull, VDOORWAIT
    ↓ semantic: key_gate(activation=use, key=blue, local door sector)
    ↓ Blood: type-600 XSECTOR, key=1, Push+Wallpush
```

Representability is asymmetric on purpose:

| Direction | Example | Class |
|---|---|---|
| Doom → Blood | normal / keyed door, teleport, exit | `semantic` |
| Doom → Blood | walkover trigger, secret tally | `approximate` |
| Blood → Doom | rotating sector, sliding door | `requires_redesign` |
| Build → Doom | stacked overlapping sectors | `unsupported` |

## Materials and entities

Textures are classified by role (wall, door, trim, floor, ceiling, hazard, sky,
switch) and mapped onto Blood construction tiles. Reports say `role-matched` or
`defaulted`, never "this Doom name is that Blood tile".

Things use GZDoom editor numbers and Blood gameplay types: shotgun → sawed-off,
Imp/Zombieman → cultist (approximation), blue card → Skull key.

## Progression

`solve_progression` walks `SemanticLevel` connections and keys. The same solver
is used for a Doom compilation and an authored Blood fixture. It does not know
linedef specials or XSECTOR fields.

## Runtime oracles

GZDoom under `reference/doom/` is an optional behavior oracle, not a package
dependency. NBlood remains the Blood load/behavior oracle. Semantic outcomes
(door blocked → trigger → route open) matter more than frame-perfect rendering.

## What this experiment proves

1. Native lossless parsing can exist for a non-Build engine without widening
   `BuildIR`.
2. A small mechanism vocabulary (door, lift, key_gate, teleport, exit) can sit
   above two encodings.
3. Doom → Blood is a lowering into a richer target; the reverse often requires
   redesign, and the representability enum can say so.
4. Progression reasoning can be shared when both games compile to `SemanticLevel`.
5. Scale is an empirical claim: Ken's `wad2map` and TEDE1M9 agree on XY×16 and
   Z×256. Blood construction `min_width` is not a Doom world scale.

The same `solve_progression` reaches the exit on authored Blood fixtures, Doom
compilations, and converted Blood maps for the five synthetic scenarios. E1M1,
E1M3, E2M1, and Doom II MAP01 convert to structurally valid Blood maps with
1:1 Doom→Build sector composition.
