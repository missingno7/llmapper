# Local MAP corpora

Commercial maps are not distributed with this repository. Put legally obtained
files in these ignored directories:

```text
maps/
  blood/    Blood v7 maps, including DNE3L1.MAP, DNE3L3.map, DWE2M3.MAP,
            and TEDE1M1.MAP–TEDE1M9.MAP when available. TEDE1M9 is a Blood-native
            recreation of Doom E1M1 (close, not 1:1) used as a Doom→Blood
            scale/height oracle.
  duke3d/   classic Duke3D v7 maps, including E3L1.MAP, E3L3.MAP, and E2L1.MAP when available
  doom/     original Doom / Doom II IWADs (`doom.wad`, `DOOM2.WAD`) when available
```

Tests use these locations by default. Override them with `BLOODMAP_CORPUS` and
`DUKEMAP_CORPUS`. Corpus-dependent tests skip when their local data is absent.

```text
python -m bloodmap roundtrip-all maps/blood
python -m bloodmap roundtrip-all maps/duke3d
python -m bloodmap doom-corpus maps/doom/doom.wad
```
