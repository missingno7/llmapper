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
| Unit/corpus/mutation/fragment/composition/oracle tests | 38/38 |
| NBlood baseline load smoke | pass (6 seconds) |
| NBlood composed-map load smoke | pass (6 seconds) |
| NBlood baseline trigger/Z-motion behavior | pass |
| NBlood composed trigger/Z-motion behavior | pass |

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

Independent load-oracle verification:

- untouched E1M2 and a deterministic E1M2 plus E1M1-sector-0 composition both
  reached NBlood's initialized game loop and remained healthy for six seconds;
- both probes ran in isolated directories with autoloads disabled and were
  terminated by the bounded harness after their grace periods;
- engine revision, hashes, counts, required markers, and fatal indicators are in
  `reports/nblood_oracle.json`;
- this proves load/startup compatibility, not trigger or progression equivalence.

Independent behavior-oracle verification:

- a synthetic decoupled wall-push XWALL sends command `On` over channel 100 to a
  type-600 XSECTOR, moving its ceiling from -8192 to -4096;
- the candidate extracts that mechanism and inserts it into a separate destination
  through the public deterministic composition path;
- both baseline and candidate retained one stable image hash across an idle control
  interval and produced a different stable image hash only after input;
- baseline and candidate hashes matched exactly in both states under NBlood
  `r14378-fbc5e1186`;
- map identities, allocations, action metadata, and derived view hashes are in
  `reports/nblood_behavior_oracle.json`.

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
- composition now passes an independent engine load smoke and one deterministic
  wall-trigger/channel/Z-motion scenario, but broader gameplay scenarios are still
  required before arbitrary production use is claimed.
