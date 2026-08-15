# llmapper

`llmapper` is a dependency-free Python toolkit for lossless Build-engine MAP
inspection, transformation, and evidence-driven conversion. It currently supports
Blood v7 (`0x0700`) and classic Duke Nukem 3D v7 maps.

The project separates three concerns:

1. `DiskMap` and `DukeDiskMap` preserve each game's native file exactly.
2. `BuildIR` exposes common sectors, walls, sprites, topology, slopes, lighting,
   and player start through one JSON contract while retaining a lossless native
   extension.
3. `LevelIR` remains the richer Blood authoring layer for triggers, channels,
   fragments, room attachment, corridors, stairs, and scratch construction.

Neither writer caches the original file blob. The 44-map Blood corpus and 41-map
Duke3D corpus both pass byte-exact native and `BuildIR` roundtrips.

## Quick start

Python 3.10 or newer is sufficient; there are no runtime dependencies.

```text
python -m bloodmap roundtrip-all maps/blood
python -m bloodmap roundtrip-all maps/duke3d
python -m bloodmap validate maps/duke3d/E3L1.MAP
python -m bloodmap dump-build maps/duke3d/E3L1.MAP -o work/E3L1.build.json
python -m bloodmap build-build work/E3L1.build.json -o work/E3L1.rebuilt.MAP
python -m bloodmap transform maps/duke3d/E1L1.MAP -o work/turned.MAP rotate --turns 1
python -m bloodmap compare-e3l1 --duke maps/duke3d/E3L1.MAP \
  --blood maps/blood/DNE3L1.MAP -o work/e3l1-differential.json
python -m bloodmap design-fingerprint maps/blood/E1M1.MAP --sectors 12,13 \
  -o work/E1M1.design.json
python -m bloodmap design-index maps/blood -o work/blood.design-index.json
python -m bloodmap design-search work/blood.design-index.json \
  --motif repeated-bays --limit 5
python -m bloodmap analyze-space maps/blood/E1M1.MAP --sectors 12,13 \
  -o work/E1M1.spatial.json
python -m bloodmap design-index maps/duke3d --include-spatial \
  -o work/duke.spatial-index.json
python -m bloodmap design-search work/duke.spatial-index.json \
  --region-kind mechanism_region --limit 5
python -m bloodmap probe-route maps/blood/E1M1.MAP \
  --from-sector 22 --to-sector 0 -o work/E1M1-route.json
python -m bloodmap project-init projects/crypt --name "Monastery crypt"
```

Cross-game conversion requires an explicit fidelity policy:

```text
python -m bloodmap convert maps/duke3d/E3L1.MAP --to blood \
  --policy geometry-only --report work/E3L1-to-blood.json \
  -o work/E3L1-geometry-blood.MAP
python -m bloodmap convert maps/blood/DNE3L1.MAP --to duke3d \
  --policy semantic --report work/DNE3L1-to-duke.json \
  -o work/DNE3L1-semantic-duke.MAP
```

`geometry-only` preserves normalized geometry, topology, slopes, player start,
and the supported lighting model; it intentionally removes sprites, native tags,
controllers, and triggers. `semantic` additionally enables only the few mappings
whose evidence and classification are explicit in the report. `strict` refuses a
cross-game export while any asset or gameplay mechanism is unresolved.

E3L11 is the principal regression board for the playable Duke-to-Blood conversion
profile. It uses the local Duke and Blood ART sets for role-aware surface matching,
translates the gameplay population by role, and lowers supported Duke mechanisms
to native Blood records:

```text
python -m bloodmap convert-e3l11 maps/duke3d/E3L11.MAP \
  --duke-art reference/duke3d --blood-art reference/blood \
  --blood-maps maps/blood --report work/E3L11-BLOOD.report.json \
  -o work/E3L11-BLOOD.MAP
```

The profile converts doors, lifts, rotating/sliding sectors, paired water links,
teleporters, conveyors, touchplates, keyed switches, switchable/ambient lights,
CRACK/SE13 breakable-wall explosion chains, weapons, inventory, enemies, and the
normal exit. Unsupported choreography remains explicit in the report. This is a
playable approximation, not a claim of exact game equivalence.

Blood-specific authoring remains available through `LevelIR`:

```text
python -m bloodmap observe maps/blood/E1M1.MAP --sectors 12,13 -o work/room.json
python -m bloodmap extract-closed maps/blood/E1M1.MAP --sectors 12,13 -o work/fragment.json
python -m bloodmap attach maps/blood/E1M2.MAP work/fragment.json \
  --destination-wall 120 --fragment-wall 3 -o work/attached.MAP
python -m bloodmap design-first-room --report work/first-room.json \
  -o work/first-puzzle-room.MAP
```

Independent local engine load checks are optional:

```text
python -m bloodmap oracle-eduke32 work/DNE3L1-geometry-duke.MAP \
  --baseline maps/duke3d/E3L1.MAP --eduke32 reference/duke3d/eduke32.exe \
  --game-dir reference/duke3d -o work/eduke-report.json
python -m bloodmap oracle-nblood work/E3L1-geometry-blood.MAP \
  --baseline maps/blood/DNE3L1.MAP --nblood reference/blood/nblood.exe \
  --game-dir reference/blood -o work/nblood-report.json
```

Run all tests with:

```text
python -m unittest discover -s tests -v
```

## Documentation

- [Architecture and invariants](docs/architecture.md)
- [Design Understanding and grounded retrieval](docs/architecture.md#design-understanding)
- [Multi-view spatial understanding](docs/spatial-understanding.md)
- [Experience Atlas and persistent level projects](docs/experience-atlas.md)
- [Shared BuildIR contract](docs/build-ir.md)
- [Duke3D v7 format support](docs/duke3d.md)
- [Cross-game normalization and conversion](docs/conversion.md)
- [LevelIR authoring](docs/level-ir.md)
- [Corpus policy](docs/corpus.md)
- [Local reference oracles](docs/reference-oracles.md)
- [Long-term roadmap](docs/roadmap.md)
- [Current verification](reports/verification.md)
- [E3L11 playable conversion summary](reports/e3l11_playable_summary.json)

Commercial game data, maps, executables, ART files, and upstream reference
checkouts are intentionally ignored. See [maps/README.md](maps/README.md) and
[docs/reference-oracles.md](docs/reference-oracles.md) for the expected local
layout.
