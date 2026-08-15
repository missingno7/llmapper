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

## Playable E3L11 vertical slice

`convert-e3l11` is the first source-specific gameplay profile layered above the
conservative generic policies. It proves a complete lowering path without treating
unrelated Duke and Blood tag numbers as equivalent.

The converter preserves E3L11's 253-sector/1,600-wall topology at the measured 3:2
scale and creates native Blood behavior records for:

- four ceiling doors, one elevator, three ceiling and two floor rise/fall sectors;
- one two-marker sliding door and five axis-marker rotating bridges;
- twenty upper/lower water pairs and two bidirectional teleporter pairs;
- nine floor-panning conveyors and six enter-trigger touchplates;
- keyed and ordinary switches on allocated user channels, plus a normal exit on
  Blood's reserved channel 4.

Weapons, ammo, health, inventory, keys, and enemies use explicit role
substitutions. Each one is classified in the report: a Duke RPG becomes a Blood
napalm launcher, while a Battlelord becoming Cerberus is recorded as a balance
approximation.

Materials are selected only from tiles already used as surfaces in the local Blood
corpus. The matcher compares ART dimensions, palette colour moments, luminance
histograms, and a small spatial thumbnail; the five exact differential mappings
still take precedence. Water interfaces use a corpus-backed Blood water-surface
tile. This is a coherent first pass, not final art direction.

Conversion fails if water endpoints are unpaired, structural validation fails, or
the exit is absent from a static reachability graph containing configured-open
portals, water links, and teleporters. Unsupported lighting, explosions, quake
debris, and demo-camera effectors remain listed rather than silently discarded.
Local game data and generated maps stay ignored and are never redistributed.

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

The E3L11 playable output also initializes, enters the game loop, and remains
healthy for the bounded NBlood oracle run. This is a load/startup proof;
interactive completion and balance remain separate playtest gates.
