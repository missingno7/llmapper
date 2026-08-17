# E2M2 vs SP-progression-v1 (design space, not geometry)

Independent packets:

- `reports/E2M2-understanding.json` / `.md`
- `reports/SP-progression-v1-understanding.json` / `.md`

E2M2 was not supplied while reading the generated map.

| dimension | E2M2 | SP-v1 | class |
| --- | --- | --- | --- |
| Progression complexity | Huge rest component (204/290); wings add 17 sectors; no unique exit cut in this model | 3 → 15 with three unique cuts (key, TX 100, TX 101) | APPROXIMATELY PRESERVED as *multi-stage gating*; LOST as *open exploration board* |
| State changes | Fire key, two push-motions, many TX; moon key unused | Key + two required switches + optional secret | PRESERVED in kind; SMALLER in count |
| Spatial pacing | Wide start volume, wings grow the same board | Small start → archive → tall gallery → exit | NEW (compressed indoor sequence) |
| Route branching | Large optional space; moon-key rooms unreached | One required crypt branch; one optional secret | APPROXIMATELY PRESERVED |
| Vertical rhythm | Covered ~5.8 PH vs sky ~13 PH; many storeys | Crypt 1 PH down; gallery 2 PH up in 0.5 PH steps (BB3-like) | PRESERVED as *meaningful height change*; LOST as *sky contrast* |
| Mechanism diversity | 42 chains; campaign-supported fan-out motion | One keyed door, two RX doors, one optional RX door, exit TX | LOST fan-out; PRESERVED switch→remote door |
| Materials / shade | Sky 2500, earth 2448, dark median shade 30 | Phase palettes (180/292 start, 110/270 crypt, 184/278 gallery) | APPROXIMATELY PRESERVED as *phase difference*; LOST as *E2M2 families* |
| Lighting | Dark whole-map median | Darker crypt, lighter gallery | APPROXIMATELY PRESERVED |
| Resource logic | 10 weapons, 12 health, 2 keys | Shotgun + skull key + optional health | SMALLER |
| Enemy character | 63 mixed dudes, mostly free-space floor | 2 cultists, floor-supported | PRESERVED as *floor actors*; LOST density |
| Revisit | Exit on the large circuit (model) | Return through start to the opened exit door | PRESERVED as *return through changed start* |

## What failed to survive

- E2M2’s **scale and optional density**. SP-v1 is a 10–20 minute indoor
  program, not a 290-sector campaign board.
- **Fan-out motion** (one switch, many receivers). SP-v1 uses 1:1 switch→door.
- **Sky / outdoor contrast**. Indoor-only; route-exposure correctly reports
  no field target.
- **Unique exit cut on E2M2 itself.** The understanding layer still cannot
  prove E2M2’s exit is behind a specific door. The generated map *can* prove
  its own cuts. That gap is in reading the original, not in authoring gates.

## Gap audit (this experiment)

| failure | class |
| --- | --- |
| E2M2 exit not a unique modeled cut | UNDERSTANDING GAP (rest opening / destruction / one-shots) |
| Fan-out not used in SP-v1 | BUILDER REASONING FAILURE (available, unused) |
| No sky phase in SP-v1 | BUILDER REASONING FAILURE (optional) |
| Dude sprites crashed NBlood without XSPRITE | CONSTRUCTION GAP (fixed: extras on actors/items) |
| Switch on a portal edge looks free-floating | PLACEMENT/ANCHOR GAP (fixed: solid-wall edges only) |
| Locked door also `trigger_push` opened without the key | MECHANISM GAP (fixed: push skipped while locked) |
| Indoor maps raised `route_exposure` | UNDERSTANDING GAP (fixed: empty routes if no sky) |
| Mixed-switch median 0.73 treated as wall height | PATTERN-KNOWLEDGE GAP (split wall vs floor pad; wall origin 2.18 PH) |

## Runtime

NBlood r14378 load smoke on `work/SP-progression-v1.MAP`: **pass**
(`work/nblood-sp-v1-report.json`). Map initialization and game loop markers
present. Action-oracle at spawn would Use the closed exit door, not a
switch; control usability is the deterministic Use pose gate (4/4 wall
switches).
