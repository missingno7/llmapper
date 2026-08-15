# Duke3D v7 support

## Scope

`bloodmap.duke` implements classic little-endian Duke3D MAP version 7. The parser
accepts version 7 only and fails clearly on truncated or unsupported input.

The disk layout used is:

| Part | Size |
|---|---:|
| version + player X/Y/Z + angle + sector | 20 bytes |
| sector count | 2 bytes |
| sector record | 40 bytes |
| wall count | 2 bytes |
| wall record | 32 bytes |
| sprite count | 2 bytes |
| sprite record | 44 bytes |

Signedness and field order follow EDuke32's v7 structs and load/save code. Unknown
trailing bytes are preserved rather than discarded.

## Evidence

The local EDuke32 checkout at commit
`ec5824db81817866f70da326d3811bb0f52b3517` was used as the primary source:

- `source/build/include/buildtypes.h` defines `sectortypev7`, `walltypev7`, and
  `spritetypev7`;
- `source/build/src/engine.cpp` implements v7 `loadboard` and `saveboard` paths;
- `source/duke3d/src/player.h` defines `PHEIGHT` as `38 << 8`.

The complete local 41-map Duke3D corpus is additional behavioral evidence. Every
map is byte-identical through:

```text
bytes -> DukeDiskMap -> bytes
bytes -> DukeDiskMap -> BuildIR -> DukeDiskMap -> bytes
BuildIR -> JSON -> BuildIR -> DukeDiskMap -> bytes
```

Mutation tests separately change the start position and a wall shade, rebuild the
file, reparse it, and observe those new values.

## Commands

```text
python -m bloodmap validate maps/duke3d/E1L1.MAP
python -m bloodmap roundtrip maps/duke3d/E1L1.MAP
python -m bloodmap roundtrip-all maps/duke3d
python -m bloodmap dump-build maps/duke3d/E1L1.MAP -o work/E1L1.json
python -m bloodmap build-build work/E1L1.json -o work/E1L1-rebuilt.MAP
python -m bloodmap transform maps/duke3d/E1L1.MAP -o work/moved.MAP \
  translate --x 1024 --y -2048 --z 4096
```

Blood-specific commands such as `dump`, `build`, `observe`, `channels`, fragment
composition, and construction still require Blood `LevelIR`.

## Structural edge case

Original E2L6 contains a portal whose referenced wall owner does not match the
declared next sector. EDuke32 loads it, so shared validation reports a warning and
preserves the data instead of normalizing it.
