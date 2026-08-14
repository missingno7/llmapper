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
| Unit/corpus/mutation/fragment/composition tests | 34/34 |

Corpus totals: 14,079 sectors, 113,261 walls, and 24,730 sprites across
6,846,491 source bytes.

Implemented transformations:

- whole-map translation in X/Y/Z, including player, geometry, sprites, absolute
  sector motion Z values, and known XSPRITE target coordinates;
- safe quarter-turn rotation around an explicit pivot, including known world-space
  points and direction angles.

Both transformations write through `LevelIR -> DiskMap`, then reparse and validate
the produced MAP before reporting success.

Fragment verification:

- synthetic fixtures cover portal boundaries, cross-boundary triggers, markers,
  sprite ownership/targets, stale redundant references, and multiple wall loops;
- all 43 corpus maps exactly reproduce their original bytes after extracting and
  reinserting representative first, middle, and last sectors;
- fragment JSON carries compact maps for sector, wall, sprite, XSECTOR, XWALL, and
  XSPRITE indices plus a canonical source-IR SHA-256.

Composition verification:

- synthetic fixtures cover deterministic object and extended-record allocation,
  user-channel collision failure/remapping, reserved and system channel policy,
  repeated insertion, placement transforms, and explicit portal connection;
- composed fixtures encode, reparse, and pass structural validation;
- allocation and unresolved-dependency reports are JSON-serializable and stable.

Source cross-checks used the local upstream checkouts at XMAPEDIT `ea89fb1a9875`
and NBlood `fbc5e11861a7`. They remain untracked development oracles; see
`docs/reference-oracles.md`.

Semantic corpus warnings (not hard errors):

- E3M5: two diagnostics for an original non-reciprocal portal association accepted
  by Build;
- E6M7: one diagnostic for an original two-wall degenerate sector accepted by Build.

Remaining scope boundaries:

- historical v6 files are not in the supplied corpus and are not claimed as
  regression-verified;
- the final four bytes of XSPRITE are preserved as an opaque per-record tail because
  NBlood explicitly skips the former runtime pointer slot;
- structurally valid composition is implemented, but independent engine-oracle
  gameplay verification is still required before arbitrary production use is
  claimed.
