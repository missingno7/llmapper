# Corpus policy and verification

## Why the corpus is local

The primary regression corpus consists of original Blood game maps. Those assets
are useful evidence but remain proprietary. They are excluded from Git and must be
obtained lawfully by each developer. The tooling has no runtime dependency on them.

By default tests look in the repository's `maps/` directory. Set
`BLOODMAP_CORPUS` to use another directory. Corpus-dependent tests skip cleanly
when no `.MAP` files are available; low-level format tests continue to run.

## Corpus gate

A supported corpus is acceptable only when every map satisfies all of these:

1. Signature, version, sizes, and CRC are recognized.
2. Parsing consumes the complete file without hidden trailing content.
3. `parse -> encode` is byte-identical.
4. `parse -> LevelIR -> DiskMap -> encode` is byte-identical.
5. Rebuilt bytes parse to a deeply equal DiskMap.
6. Structural validation has zero hard errors.
7. Any semantic warnings are investigated and documented.

Run the gate with:

```text
python -m bloodmap roundtrip-all maps
python -m unittest discover -s tests -v
```

## Generated evidence

- `reports/corpus_inventory.json` records filename, size, SHA-256, version, counts,
  and CRC without containing map bytes.
- `reports/corpus_statistics.json` records aggregate structural/gameplay facts.
- `reports/verification.md` summarizes the verified baseline and known warnings.

SVG renderings of original map geometry are treated as local diagnostic artifacts
and ignored by Git.

## Adding a supported variant

Do not generalize from a header byte alone. Add a legally usable fixture/corpus,
trace the relevant XMAPEDIT and NBlood load/save paths, encode new knowledge in
explicit parsing and packing code, add focused primitive tests, and then run every
existing corpus gate. Unsupported variants must fail clearly rather than being
guessed or normalized.
