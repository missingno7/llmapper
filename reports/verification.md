# Verification report

Generated against the supplied `maps/` corpus.

| Gate | Result |
|---|---:|
| Maps discovered | 43 |
| Detected versions | 43 × Blood MAP `0x0700` |
| Parse success | 43/43 |
| Byte-exact DiskMap roundtrip | 43/43 |
| Byte-exact LevelIR roundtrip | 43/43 |
| Reparse success | 43/43 |
| Hard validation success | 43/43 |
| Unit/corpus/mutation tests | 14/14 |

Corpus totals: 14,079 sectors, 113,261 walls, and 24,730 sprites across
6,846,491 source bytes.

Implemented transformations:

- whole-map translation in X/Y/Z, including player, geometry, sprites, absolute
  sector motion Z values, and known XSPRITE target coordinates;
- safe quarter-turn rotation around an explicit pivot, including known world-space
  points and direction angles.

Both transformations write through `LevelIR -> DiskMap`, then reparse and validate
the produced MAP before reporting success.

Semantic corpus warnings (not hard errors):

- E3M5: two diagnostics for an original non-reciprocal portal association accepted
  by Build;
- E6M7: one diagnostic for an original two-wall degenerate sector accepted by Build.

Remaining scope boundaries:

- historical v6 files are not in the supplied corpus and are not claimed as
  regression-verified;
- the final four bytes of XSPRITE are preserved as an opaque per-record tail because
  NBlood explicitly skips the former runtime pointer slot;
- region extraction/cloning has an architectural path through explicit IDs and
  relationship fields, but automatic subgraph remapping/composition is intentionally
  deferred until it can be verified against a dedicated fixture corpus.
