# Local MAP corpora

Commercial maps are not distributed with this repository. Put legally obtained
files in these ignored directories:

```text
maps/
  blood/    Blood v7 maps, including DNE3L1.MAP when available
  duke3d/   classic Duke3D v7 maps, including E3L1.MAP when available
```

Tests use these locations by default. Override them with `BLOODMAP_CORPUS` and
`DUKEMAP_CORPUS`. Corpus-dependent tests skip when their local data is absent.

```text
python -m bloodmap roundtrip-all maps/blood
python -m bloodmap roundtrip-all maps/duke3d
```
