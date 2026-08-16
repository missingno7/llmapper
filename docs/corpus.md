# Corpus policy and verification

## Local-only data

The regression corpora consist of proprietary Blood and Duke3D maps. They are
excluded from Git and must be obtained lawfully by each developer. The package has
no runtime dependency on them.

Default layout:

```text
maps/blood/*.MAP
maps/duke3d/*.MAP
```

Set `BLOODMAP_CORPUS` or `DUKEMAP_CORPUS` to override a location. Tests skip the
corresponding corpus gate cleanly when no maps are available.

## Native losslessness gate

Every supported map must satisfy:

1. version is a supported Blood major (6 or 7) or Duke v7; campaign `E*.MAP`
   files are Blood v7 (`0x0700`); sizes and record counts are recognized;
2. parsing consumes the defined file while deliberately preserving allowed tails;
3. native disk parse/write is byte-identical;
4. `BuildIR` native reconstruction is byte-identical;
5. `BuildIR` JSON serialization and restoration are byte-identical;
6. genuine mutations reach new output and reparse correctly;
7. structural validation has zero hard errors;
8. original-map warnings are investigated and documented.

Blood additionally requires byte-exact reconstruction through `LevelIR`, including
encryption, CRC, and all extended records.

```text
python -m bloodmap roundtrip-all maps/blood
python -m bloodmap roundtrip-all maps/duke3d
python -m unittest discover -s tests -v
```

The current local result is 44/44 Blood maps and 41/41 Duke3D maps.
Derived, non-proprietary inventories are tracked in
`reports/corpus_inventory.json` and `reports/duke3d_corpus_inventory.json`;
`reports/corpus_statistics.json` retains the richer Blood semantic statistics.

## Cross-game evidence gate

`maps/duke3d/E3L1.MAP` and `maps/blood/DNE3L1.MAP` form an independently authored
conversion pair. `compare-e3l1` derives scale, exact geometry correspondences,
topology agreement, Z residuals, shade regressions, material candidates, and
mechanism inventories without assuming equal object indices.

`maps/duke3d/E3L3.MAP` and `maps/blood/DNE3L3.map` are a second pair. DNE3L3 is a
Blood-native reimagination of E3L3, not an index-matched conversion: the
differential still selects 3:2 from shared wall-vector lengths, but unique sector
shapes do not correspond. Use it as Blood mechanism vocabulary (water markers,
type-600 Z-motion, type-617 swinging doors), not as a geometry oracle.

`maps/duke3d/E2L1.MAP` and `maps/blood/DWE2M3.MAP` are a visual-style pair: both
are space-station maps, unique sector correspondences are zero, and DWE2M3 is
much larger. Conversion keeps Duke E2L1 topology at the measured 3:2 profile and
uses DWE2M3 as Blood indoor material, palette, shade, visibility, and sky
vocabulary. Do not treat wall-vector overlap at 2:1 as an authoring scale; that
ratio is coincidental on this unrelated pair.

`maps/duke3d/E3L11.MAP` and `maps/blood/DNE3L11.map` are a partial 3:2 conversion:
wall-vector overlap strongly selects 3:2, sector indices are mostly preserved,
but unique sector shapes do not match after edits (250 vs 253 sectors). The Blood
map is a water-layout pass: 15 water-marker pairs, one stack pair, and
XSECTOR.Underwater on every Duke ST2 index, with no type-600 doors or cracks yet.
Use it as stacked-flag evidence, not as a finished mechanism oracle.

`maps/duke3d/E3L6.MAP` and `maps/blood/DNE3L6.map` are a partial-geometry
reimagination (72 unique sector matches at 3:2). DNE3L6 supplies Blood vocabulary
for type-408 cracks TX-ing type-459 exploders, Push+Wallpush type-600 doors, and
XWALL switches. It also uses path/rotate-marked/damage sectors (612/615/618) on
rebuilt geometry; those are not copied onto unmatched Duke tags.

`maps/duke3d/BE1L1.map` … `BE1L4.map` and `BE1L7.map` are reverse (Blood→Duke)
conversions of E1M1–E1M4 and E1M7. They are heavily rebuilt; vector overlap
prefers 4:3 rather than 2:3. They confirm Duke ST1/ST2 as the water lowering and
CRACK sprites as the crack lowering, but they leak Blood sector types (600, 618)
into Duke lotags and are not a geometry oracle.

`maps/blood/TEDE1M9.MAP` is a Blood-native recreation of Doom E1M1: close in
layout, not a 1:1 sector conversion (105 Blood sectors vs 88 Doom sectors).
Wall-vector overlap against Doom E1M1 peaks at XY ×16 with Y-flip, and
floor/ceiling values match Doom heights ×256. That agrees with NBlood
`source/tools/src/wad2map.cpp` (`<<4` XY, `-(z<<8)` Z). Use TEDE1M9 as a
Doom→Blood scale/height oracle, not as a sector-index oracle.

Derived mappings are enabled only when their classification and support threshold
are explicit. Context-dependent candidates remain evidence, not conversion rules.

```text
python -m bloodmap compare-e3l1 --duke maps/duke3d/E3L1.MAP \
  --blood maps/blood/DNE3L1.MAP -o work/e3l1-differential.json
python -m bloodmap compare-e3l1 --duke maps/duke3d/E3L3.MAP \
  --blood maps/blood/DNE3L3.map -o work/e3l3-differential.json
python -m bloodmap compare-e3l1 --duke maps/duke3d/E2L1.MAP \
  --blood maps/blood/DWE2M3.MAP -o work/e2l1-dwe2m3-differential.json
```

## Adding a format or variant

Do not generalize from a header byte alone. Add a legally usable fixture or local
corpus, trace a primary engine/editor load and save path, encode the exact field
layout, add mutation tests, and run every existing gate. Unsupported variants must
fail clearly instead of being guessed or normalized.
