# Cross-game normalization and conversion

## Evidence from E3L1 and DNE3L1

The hand-converted pair supplies the first measured profile rather than relying on
memory or tag-number guesses. Exact geometry signatures are independent of sector
and wall array order.

| Observation | Result |
|---|---:|
| Selected Duke-to-Blood XY/Z scale | 3:2 |
| Matching directed wall vectors at 3:2 | 1,831 |
| Next-best vector match | 984 at 3:4 |
| Unique exact sector correspondences | 232 / 345 (67.25%) |
| Unique exact wall correspondences | 1,665 / 2,334 (71.34%) |
| Matched sectors with equal portal degree | 227 / 232 |
| Exact scaled ceiling/floor Z samples | 433 / 464 |

The 3:2 ratio is therefore an empirical authoring-scale profile. Player eye
heights—Duke `38 << 8`, Blood standing posture `0x1600`—are retained as separate
gameplay evidence and are not used to override the geometry measurement.

For ordinary matched wall shades, 1,387 of 1,621 samples satisfy
`Blood shade = 2 * Duke shade` (85.56%). Least-squares fit gives slope 1.9876,
intercept 1.48, and mean absolute error 2.81. The initial conversion model doubles
Duke shade, halves it in the reverse direction, clamps signed-byte output, and
defaults Duke sentinel-like values at or below -100 when targeting Blood.

Five nonzero material mappings are globally enabled because every observation for
the Duke tile selected the same Blood tile with at least five samples:

| Duke tile | Blood tile | Support |
|---:|---:|---:|
| 89 | 2500 | 35 / 35 |
| 793 | 1353 | 13 / 13 |
| 698 | 471 | 10 / 10 |
| 893 | 458 | 10 / 10 |
| 216 | 492 | 7 / 7 |

Other candidates remain report-only because their use is contextual or ambiguous.
Only three sprites have unique exact XY correspondence in the pair, so proximity
is explicitly rejected as an entity-mapping method.

## Policies and fidelity

`geometry-only` scales X/Y/Z by 3:2 or 2:3, preserves wall/sector indices,
portals, slope coefficients, safe common cstat bits, panning, repetition, and
player start. It removes all sprites, game-native tags, controllers, extended
records, and triggers. Unknown textures use an explicit safe target default.

`semantic` starts from the same geometry and additionally enables:

- shotgun pickup: Duke tile 28 <-> Blood type 41 / tile 559, classified
  `semantic-equivalent`;
- ranged humanoid: Duke LIZTROOP tile 1680 <-> Blood cultist-with-Tommy type 201 /
  tile 2820, classified `approximation`.

Everything else is omitted and itemized. These are a deliberately small initial
registry, not a claim that the two games' actor systems are interchangeable.
EDuke32 `names.h` identifies tiles 28 and 1680 as `SHOTGUNSPRITE` and `LIZTROOP`.
NBlood/XMAPEDIT identify Blood types 41 and 201 as the sawed-off pickup and Tommy
cultist; all 122 type-41 and all 550 type-201 sprites in the local Blood corpus use
tiles 559 and 2820 respectively.

`strict` currently fails cross-game conversion because complete texture, palette,
entity, sound, weapon, controller, trigger, secret, and progression equivalence is
not established.

Every successful conversion report states structural validity and separately
classifies geometry, visual, and gameplay fidelity. A structurally valid converted
map is not described as gameplay-equivalent.

Reproducible sample fidelity reports are tracked as
`reports/e3l1_to_blood_geometry.json` and
`reports/dne3l1_to_duke_geometry.json`; their source and target MAPs remain
ignored. `reports/e3l1_cross_game_summary.json` records the compact differential
evidence without embedding proprietary geometry.

## Runtime result

The E3L1 geometry-only Blood output initializes and remains healthy in NBlood
`r14378-fbc5e1186`. The DNE3L1 geometry-only Duke output does the same in EDuke32
`r10669-ec5824db8`. Both were tested beside untouched baselines in isolated
directories. See [verification.md](../reports/verification.md).
