# bloodmap

`bloodmap` is a dependency-free Python toolkit for inspecting and editing Monolith
Blood MAP files through a verified lossless representation. It was built from the
actual XMAPEDIT and NBlood load/save paths and regression-tested against every MAP
under `maps/`.

The architecture deliberately has two layers:

1. `DiskMap` preserves every decoded disk field, packed extended field, reserved
   header region, original index, and the genuinely opaque four-byte XSPRITE tail.
2. `LevelIR` is a stable, editable JSON representation with explicit object IDs,
   relationships, player start, geometry, and named Blood properties.

The writer always rebuilds the file from these fields. It never retains or returns
the original complete file blob.

## Quick start

Python 3.10 or newer is sufficient; there are no runtime dependencies.

```text
python -m bloodmap corpus maps -o reports/corpus_inventory.json
python -m bloodmap roundtrip-all maps
python -m bloodmap validate maps/E1M1.MAP
python -m bloodmap inspect maps/E1M1.MAP --sector 42
python -m bloodmap channels maps/E1M1.MAP --channel 104
python -m bloodmap dump maps/E1M1.MAP -o work/E1M1.json
python -m bloodmap build work/E1M1.json -o work/E1M1_rebuilt.MAP
python -m bloodmap render maps/E1M1.MAP -o reports/E1M1.svg
python -m bloodmap stats maps -o reports/corpus_statistics.json
python -m bloodmap extract maps/E1M1.MAP --sectors 12,13,20-24 -o work/fragment.json
python -m bloodmap apply-fragment maps/E1M1.MAP work/fragment.json -o work/restored.MAP
python -m bloodmap compose maps/E1M2.MAP work/fragment.json --x 8192 --channel-policy remap --report work/composition.json -o work/composed.MAP
python -m bloodmap connect work/composed.MAP --wall-a 120 --wall-b 845 -o work/connected.MAP
python -m bloodmap oracle-nblood work/composed.MAP --baseline maps/E1M2.MAP --nblood reference/blood/nblood.exe --game-dir reference/blood -o work/oracle.json
```

Safe whole-map transformations operate through `LevelIR`, then write, reparse,
and validate their output:

```text
python -m bloodmap transform maps/E1M1.MAP -o work/moved.MAP translate --x 4096 --y -2048
python -m bloodmap transform maps/E1M1.MAP -o work/turned.MAP rotate --turns 1 --pivot-x 0 --pivot-y 0
```

Sector extraction uses `LevelFragment` with explicit index maps and classified
external dependencies. Same-source application restores detached relationships
exactly; cross-map composition allocates object, extra-record, and user-channel
identities deterministically and leaves external dependencies explicit.

Run the test suite with:

```text
python -m unittest discover -s tests -v
```

See [docs/format.md](docs/format.md) for the evidence-backed disk specification
and [reports/verification.md](reports/verification.md) for the latest corpus result.
The optional NBlood load-smoke workflow is documented in
[docs/reference-oracles.md](docs/reference-oracles.md).

## Project documentation

- [Architecture and invariants](docs/architecture.md)
- [Local corpus setup and policy](docs/corpus.md)
- [Sector fragments and remapping](docs/fragments.md)
- [Deterministic composition](docs/composition.md)
- [Local reference oracles](docs/reference-oracles.md)
- [Long-term roadmap](docs/roadmap.md)
- [Contributing and verification gates](CONTRIBUTING.md)

The original Blood maps are intentionally not distributed by this repository.
Place a legally obtained local corpus under `maps/` or point `BLOODMAP_CORPUS` at
one before running corpus and mutation tests. See `maps/README.md` for details.
