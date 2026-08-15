# Contributing

## Development setup

Use Python 3.10 or newer. The package has no runtime dependencies.

```text
python -m unittest discover -s tests -v
python -m bloodmap --help
```

Original Blood and Duke3D maps are not distributed. See `maps/README.md` and
`docs/corpus.md` for optional local corpus setup.

Game-neutral editing APIs must operate on `BuildIR`. Blood-specific authoring APIs
operate on `LevelIR` or a documented derivative such as `LevelFragment`.
`DiskMap` and `DukeDiskMap` are lossless import/export representations, not
authoring APIs. New LLM-facing observations must use stable semantic references
and label unknown numeric semantics instead of inventing names.

## Change gates

Changes to binary parsing, packing, models, or conversion logic must include:

1. evidence from XMAPEDIT, NBlood, EDuke32, or an isolated reproducible fixture;
2. a focused unit or mutation test;
3. a full available-corpus direct and IR roundtrip run;
4. a validator run with every new warning investigated;
5. a short update to `docs/format.md` or `docs/duke3d.md` for non-obvious format knowledge.

Changes to fragment composition, map writing, or structural limits should also run
the optional baseline/candidate NBlood load smoke when local game data is available:

```text
python -m bloodmap oracle-nblood work/candidate.MAP \
  --baseline maps/blood/E1M2.MAP \
  --nblood reference/blood/nblood.exe \
  --game-dir reference/blood \
  -o work/oracle.json
```

This gate proves that both files reach NBlood's initialized game loop and remain
healthy for the configured grace period. It does not by itself prove gameplay
equivalence.

Duke writer and cross-game geometry changes should run the corresponding EDuke32
baseline/candidate smoke. Cross-game changes must also update or reproduce the
fidelity report and must never equate native tags solely because their numbers
match.

Room-attachment changes must additionally cover automatic rotation, repeated room
copies, channel remapping, blocked-wall policy, and slope-aware endpoint clearance.
When the original-map corpus is present, reproduce the attachment fixture in
`docs/reference-oracles.md` and run its NBlood load smoke.

Changes to fragment allocation, channel remapping, or extended-record ownership
should also run the Windows behavior oracle when local NBlood game data is
available. It briefly foregrounds the NBlood window to send raw keyboard input:

```text
python -m bloodmap oracle-nblood-behavior \
  --nblood reference/blood/nblood.exe \
  --game-dir reference/blood \
  -o work/behavior-oracle.json
```

This gate covers the synthetic wall-trigger/channel/Z-motion scenario documented
in `docs/reference-oracles.md`; it is not evidence for untested gameplay systems.

Do not normalize values in lossless paths, rely on compiler bitfield layout, retain
the complete input blob, or silently discard references.

## Commit hygiene

- Keep proprietary maps and original-map SVG renderings out of commits.
- Keep generated scratch output under ignored `work/`.
- Make commits focused and describe the verified behavior they add.
- Do not mix semantic guesses into binary-format changes.

## Adding operations

An editing operation must document its preconditions, exact fields touched,
reference-remapping behavior, expected diagnostics, and reparse/validation checks.
Unknown fields remain unchanged unless their meaning has been verified.
