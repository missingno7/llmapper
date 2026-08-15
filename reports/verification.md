# Verification report

Verified locally on 2026-08-16 against ignored commercial corpora and independent
engine installations.

## Automated gates

| Gate | Result |
|---|---:|
| Blood v7 maps | 44 / 44 pass |
| Duke3D v7 maps | 41 / 41 pass |
| Blood native DiskMap roundtrip | 44 / 44 byte-exact |
| Blood LevelIR roundtrip | 44 / 44 byte-exact |
| Blood BuildIR roundtrip | 44 / 44 byte-exact |
| Duke native DiskMap roundtrip | 41 / 41 byte-exact |
| Duke BuildIR roundtrip | 41 / 41 byte-exact |
| Structural hard errors | 0 across both corpora |
| Unit/corpus/mutation/composition/conversion tests | 73 / 73 pass |
| E3L1 -> Blood geometry conversion in NBlood | pass |
| DNE3L1 -> Duke geometry conversion in EDuke32 | pass |
| E3L11 -> Blood playable-profile conversion in NBlood | pass |

Corpus totals:

| Game | Sectors | Walls | Sprites | Bytes |
|---|---:|---:|---:|---:|
| Blood | 14,425 | 115,585 | 25,109 | 6,975,270 |
| Duke3D | 14,680 | 98,503 | 28,224 | 4,982,218 |

The full test command was:

```text
python -m unittest discover -s tests -v
```

## Shared BuildIR

Both native models project player start, sectors, walls, sprites, topology, slopes,
shade, palette, panning, repetition, and common tags into schema-versioned
`llmapper.build-ir` JSON. Unchanged maps reconstruct exactly from that shared form.
Translation and quarter-turn rotation write back through the same path for both
games. Game-native data remains in a lossless adapter extension and is never
treated as a cross-game semantic mapping by numeric coincidence.

## E3L1/DNE3L1 differential

The measured Duke-to-Blood scale is 3:2, selected by 1,831 matching directed edge
vectors versus 984 for the next candidate. At that scale the matcher finds 232
unique exact sector correspondences, 1,665 exact wall correspondences, equal portal
degree in 227 of the matched sectors, and 433 exact Z surfaces among 464 samples.

Ordinary matched wall shading follows `Blood = 2 * Duke` in 1,387 of 1,621 samples
(85.56%); the fitted slope is 1.9876 with mean absolute error 2.81. Five globally
unambiguous nonzero material mappings currently meet the minimum support rule. No
entity map is inferred from proximity: the pair has only three unique exact-XY
sprite matches.

## Cross-game outputs

Geometry-only conversion preserves sector/wall counts, index topology, portals,
slopes, normalized coordinates and Z, player start, and supported common visual
fields. It deliberately emits zero sprites and strips native mechanisms. Unknown
assets use explicit target defaults. Reports classify geometry as normalized,
lighting as approximate, and gameplay fidelity as unsupported.

- Duke E3L1 -> Blood: 345 sectors, 2,334 walls, 0 sprites; reparses and validates.
  Candidate and untouched DNE3L1 baseline both initialized and stayed healthy in
  NBlood `r14378-fbc5e1186` with all markers and no fatal indicators.
- Blood DNE3L1 -> Duke: 346 sectors, 2,324 walls, 0 sprites; reparses and validates.
  Candidate and untouched E3L1 baseline both initialized and stayed healthy in
  EDuke32 `r10669-ec5824db8` with all markers and no fatal indicators.

These are load/startup proofs, not claims that triggers, combat, secrets, sounds,
or progression were translated.

The source-specific E3L11 profile produces 253 sectors, 1,600 walls, and 219
sprites. Structural validation reports zero errors and zero warnings. The result
contains ten Z-motion sectors, five rotating sectors, one sliding sector, four
teleporter sectors, twenty paired water links, keys and switches, weapons,
inventory, enemies, and an exit on channel 4. A configured-open static graph
reaches the exit from the player start. Candidate and DNE3L1 baseline both entered
the NBlood game loop and remained healthy for five seconds under
`r14378-fbc5e1186`.

This proves initialization and basic structural progression only. Manual
completion, combat balance, material curation, and action-level checks for every
converted mechanism remain release gates.

## Existing Blood authoring gates

The prior Blood-specific gates remain green: behavior-closed extraction,
same-source exact reinsertion, deterministic allocation and channel remapping,
room copying/rotation/attachment, routed corridors, bounded stairs, recipe-driven
mashups, the E1M2 room-order remix, and the scratch two-switch puzzle room.
Independent NBlood load checks pass for the attachment, mashup, remix, and scratch
room. The deterministic wall-trigger/channel/Z-motion behavior oracle and both
scratch-room switch action probes also pass.

## Source provenance

- EDuke32 `ec5824db81817866f70da326d3811bb0f52b3517`
- NBlood `fbc5e11861a74f4ec4fbf2b80cc3b06bb17696f3`
- XMAPEDIT `ea89fb1a9875cd2764bd1eb8ab12b17de4f9916d`

The source checkouts, game data, engines, maps, generated binaries, logs, and
screenshots stay under ignored local directories.

## Known boundaries

- Duke support is classic MAP version 7; old v5/v6 and newer map-text/VX variants
  are not claimed.
- Blood historical v6 files are not corpus-verified.
- Generic geometry conversion does not preserve native gameplay mechanisms; the
  E3L11 source-specific profile covers a documented subset.
- Sound, secrets, spawn conditions, complex lights/destruction, and exact combat
  balance need more evidence and abstractions.
- Original accepted oddities remain warnings: Duke E2L6 portal ownership, Blood
  E3M5 non-reciprocal portal association, and Blood E6M7's two-wall sector.
