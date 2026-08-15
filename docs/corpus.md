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

1. version, sizes, and record counts are recognized;
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

Derived mappings are enabled only when their classification and support threshold
are explicit. Context-dependent candidates remain evidence, not conversion rules.

```text
python -m bloodmap compare-e3l1 --duke maps/duke3d/E3L1.MAP \
  --blood maps/blood/DNE3L1.MAP -o work/e3l1-differential.json
```

## Adding a format or variant

Do not generalize from a header byte alone. Add a legally usable fixture or local
corpus, trace a primary engine/editor load and save path, encode the exact field
layout, add mutation tests, and run every existing gate. Unsupported variants must
fail clearly instead of being guessed or normalized.
