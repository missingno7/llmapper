# Blood MAP v7 disk notes

## Sources and scope

The implementation follows and cross-checks these authoritative paths:

- XMAPEDIT: `src_blood/db.cpp`, `src_blood/db.h`, `include/build.h`, and the
  least-significant-bit-first `BitReader`/`BitWriter` in `src_blood/common_game.h`.
- NBlood: `source/blood/src/db.cpp`, `source/blood/src/db.h`, and the Build record
  definitions reachable from `source/blood/src/common_game.h`.

All 43 supplied maps are version `0x0700`, so v7 is the fully verified target.
The parser has conservative v6 reading/writing scaffolding, but historical v6 is
not claimed as corpus-verified.

## File order

All integers are little-endian. A v7 file is:

```text
BLM\x1a signature (4)
version (uint16)
encrypted main header (37)
encrypted extra header (128)
encrypted sky offsets (2 * 2^skyBits)
sector record (40), followed immediately by XSECTOR when sector.extra > 0
wall record (32), followed immediately by XWALL when wall.extra > 0
sprite record (44), followed immediately by XSPRITE when sprite.extra > 0
CRC-32 (uint32) over every preceding byte
```

The corpus extended sizes from the extra header are XSECTOR 60, XWALL 24, and
XSPRITE 56 bytes.

## Obfuscation

`dbCrypt` XORs byte `i` with the low eight bits of `key + i`. Applying it twice
restores the input. Keys are:

- main header: `0x7474614d` (`ttaM` in little-endian bytes),
- extra header: wall count,
- sky: sky byte length,
- sectors: `revision * 40`,
- walls: `(revision * 40) | 0x7474614d`,
- sprites: `(revision * 44) | 0x7474614d`.

The extended records themselves are not encrypted.

## Packed records

Extended fields are decoded explicitly in the exact source order. Bit zero of the
first byte is read first; each field occupies the next stated number of bits. No
compiler bitfield layout is used. `bloodmap/format.py` contains the field schemas,
widths, signedness, masks, range checks, and inverse writer.

XSECTOR consumes all 480 bits. XWALL consumes all 192 bits. The known XSPRITE
fields consume 416 of 448 bits. NBlood explicitly skips the final 32 bits (the old
runtime AI-state pointer slot), so `DiskMap` preserves exactly those four bytes as
the smallest opaque unit. The rest of every extended record is decoded.

## Non-obvious corpus evidence

- The packed extended `reference` is redundant. Both loaders bind an extended
  record through inline order and the owning Build record's `extra` index, then
  overwrite `reference` with the current owner. Some originals contain stale
  values after sprite deletion; they are preserved but are not structural errors.
- Sprite `angle` is physically a signed 16-bit field. Original maps contain
  negative and greater-than-2047 values; Build angle consumers use modulo-2048
  semantics. Parsing does not normalize these values.
- E3M5 contains a non-reciprocal portal association and E6M7 contains a two-wall
  degenerate sector. Build accepts both. The validator reports semantic warnings,
  while invalid ranges and out-of-bounds relationships remain hard errors.
- Reserved extra-header regions are retained as two bounded fields (64 and 37
  bytes), not as a whole-map blob. Known XMAPEDIT header extensions are decoded.

## Losslessness

Untouched `parse -> encode` and `parse -> LevelIR -> DiskMap -> encode` are both
byte-exact for all supplied originals. CRC is recomputed from rebuilt bytes. Tests
also mutate fields at every major layer and prove that the emitted bytes reparse to
the new values rather than being an input passthrough.
