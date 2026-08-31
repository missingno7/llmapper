# Local MAP corpora

Commercial maps are not distributed with this repository. Put legally obtained
files in these ignored directories:

```text
maps/
  blood/    the Blood corpus, organized by provenance. The directory a map
            lives in is its population; see maps/blood/README.md (written
            alongside the corpus, local-only) and docs/corpus.md.
    campaign/      original Monolith maps; campaign/multiplayer/ = BB1-BB9
    curated/       owner hand-picked community source maps (DWE*, TEDE*, SS*)
    conversions/   the owner's manual Duke3D->Blood conversions (DNE*)
    community/     bulk community maps; tiered/ is the same set re-sorted by
                   a heuristic classifier, with tier kept as metadata
    mechanism/     mechanism tutorials and showcases
  duke3d/   classic Duke3D v7 maps, including E3L1.MAP, E3L3.MAP, and E2L1.MAP when available
  doom/     original Doom / Doom II IWADs (`doom.wad`, `DOOM2.WAD`) when available
```

Tests use these locations by default. Override them with `BLOODMAP_CORPUS` and
`DUKEMAP_CORPUS`; a flat override directory still works. Corpus-dependent tests
skip when their local data is absent.

```text
python -m bloodmap corpus-manifest maps/blood -o maps/blood/corpus.json
python -m bloodmap roundtrip-all maps/blood/campaign
python -m bloodmap corpus-health --maps maps/blood --population community \
  -o reports/blood-community-corpus-health.json
python -m bloodmap roundtrip-all maps/duke3d
python -m bloodmap doom-corpus maps/doom/doom.wad
```
