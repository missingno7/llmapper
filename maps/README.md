# Local Blood MAP corpus

Place legally obtained Blood `.MAP` files in this directory for regression testing.
The original game maps are proprietary and are deliberately ignored by Git; this
repository does not distribute them.

The canonical development corpus used for the initial verification contained 43
version `0x0700` maps named from `E1M1.MAP` through the supplied episode set. A
different directory can be selected for tests with `BLOODMAP_CORPUS`:

```powershell
$env:BLOODMAP_CORPUS = 'D:\path\to\blood-maps'
python -m unittest discover -s tests -v
```

Useful corpus commands:

```text
python -m bloodmap corpus maps -o reports/corpus_inventory.json
python -m bloodmap roundtrip-all maps
python -m bloodmap stats maps -o reports/corpus_statistics.json
```

Never edit the source corpus in place. Write rebuilt or transformed maps to a
separate ignored `work/` directory.
