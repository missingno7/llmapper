# Single-player understanding

Deathmatch sensors (spawn neighborhoods, start-to-sky routes, hunting-cell
morphology) do not represent Blood campaign progression. Physical walkability
and allowed progress are different graphs.

## Populations

Keep them explicit:

| corpus | use |
| --- | --- |
| `E*.MAP` campaign | SP progression, mechanisms, pacing, materials |
| `BB*.MAP` BloodBath | multiplayer only |
| `BB3.MAP` | compact **vertical** morphology, not SP gating |
| generated reconstructions | never design evidence |

## Physical vs progress

`analyze-space` rest-walkability is the physical traversal graph: portal width,
vertical opening ≥ 4096, no blocking flag.

`python -m bloodmap progression MAP` adds keys (sprite types 100–106),
RX-gated type 600/602 motion, push-gated motion (not while locked without the
key), and exit channels 4/5. It is not a player simulator. Destruction,
one-shot walls, and undocumented types stay unknown.

```text
python -m bloodmap progression maps/blood/E2M2.MAP -o reports/E2M2-progression.json
```

A completion witness is a greedy grounded trace: spawn → collect reachable
keys → unlock adjacent keyed motion → push adjacent unlocked motion → activate
TX in reached sectors. Counterfactual classification re-solves with each
activated channel or collected key dropped.

On a large campaign map the at-rest component can already contain the exit
sprite, so **no single channel is a cut**. That is a reported limitation, not
a claim that the level has no gating in play. Authored scratch maps can still
prove unique cuts (key, then switch A, then switch B).

## Mechanism compositions

Unsigned signatures look like `tx1|rx8|motion1|exit0|sprite`. Fan-out
(one transmitter, many receivers) and single-motion gates recur across the
43-map campaign. E2M2 observations are promoted only after that search.

## Vertical morphology

BB3 is a clean height reference: many walkable floor deltas cluster at
**0.73 player-heights** (4096 Build units, Blood's max step), connecting a
low court to a high platform several player-heights up. Campaign maps
(E1M1–E1M6, …) contain the same delta band. Do not import BB3's deathmatch
logic into SP design; import the step size and the low/high split.

## Authoring order

1. Design program (phases, not polygons).
2. Machine-readable state graph with Blood-native transitions.
3. PlanarLayout blockout with gated type-600 doors and wall-anchored controls.
4. Witness: exit unreachable at rest; reachable after intended actions;
   optional branches remain optional; no unexplained floating switches.
5. Independent `Understand(generated)` without the E2M2 target in the prompt.

```text
python -m bloodmap design-sp-v1 \
  -o work/SP-progression-v1.MAP \
  --report reports/SP-progression-v1-build.json
```

See [object-placement.md](object-placement.md) for anchors.
See [E2M2 understanding](../reports/E2M2-understanding.md) for the first
campaign microscope.
