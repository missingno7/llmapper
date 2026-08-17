# Door affordances

A Blood door is not one native type. Original campaign maps implement
passage-gating with several **behavior / interaction / condition** combinations.
llmapper records those combinations as mined families. It does not collapse them
into `make_door()`.

## ActionScan (Use)

NBlood `player.cpp` `ActionScan` is a hitscan of **64 Build units**.

| hit | fires |
|---|---|
| XWALL `trigger_push` | that wall |
| portal whose **next** XSECTOR has `trigger_wall_push` | that sector |
| XSECTOR `trigger_push` | only if the player is already in the sector, or the hitscan strikes its floor/ceiling |

A closed Z-door has `ceiling_z ≈ floor_z`. The player stands in the hallway and
Use hits the **portal wall**. `trigger_push` alone does not open it.
`trigger_wall_push` does.

Remote switch doors are the opposite: XSECTOR `rx_id` set, **no** Push, **no**
Wallpush. The switch sprite is the interaction.

Verified field fragments (not complete doors):

```text
bloodmap.doors.xsector_direct_use(key=None|1..7)
bloodmap.doors.xsector_remote_rx(rx_id)
```

## Five facets

Keep them independent:

- **Behavior** — Z-ceiling, Z-floor, Z-split, slide (614/616), rotate (617/615)
- **Interaction** — wall_push, sector_push, touch, remote_rx, or dual
- **Condition** — XSECTOR `key` 1–7 (skull…moon), or none
- **Feedback** — locked response / motion (runtime; static maps only store `key`/`locked`)
- **Signifier** — approach portal picnum vs neighboring fill; optional emblem sprite

## Campaign families (43 E*.MAP, 2027 motion sectors)

Dominant, not exclusive:

| family (signature) | roughly | interaction |
|---|---|---|
| `t600\|z_ceiling\|remote_rx` | rising slab, switch-operated | remote |
| `t600\|z_floor\|remote_rx` | lift / floor motion | remote |
| `t614\|slide\|remote_rx` | sliding sector | remote |
| `t600\|z_ceiling\|wall_push` | hallway-use ceiling door | direct |
| `t617\|rotate\|wall_push` | swinging door | direct |
| `t600\|z_ceiling\|wall_push` + `key` | keyed hallway door | direct + key |

Closed rest opening is a heuristic (`<= 512`), not a native “is_door” flag.

Approach **face** is the paired portal wall the player looks at from the neighbor.
Tile 104 (old scratch default) is almost unused in the campaign and is not a
door family.

Common closed wall-push faces include 22, 495, 9, 25, 26, 28. Remote closed
faces include 200, 345, 449. These are retrieval hints, not placement policy.

Typical direct-use width clusters near **1024** units (~2.7 player-widths), not
a full room wall.

## Key emblems

Wall-aligned type-0 sprites 2540–2545 co-occur with keyed motion far above the
unkeyed baseline, split by key id:

| picnum | dominant key | maps |
|---|---|---|
| 2540 | skull (1) | 15 |
| 2541 | eye (2) | 9 |
| 2542 | fire (3) | 9 |
| 2543 | dagger (4) | 5 |
| 2545 | moon (6) | 9 |

They also appear without locks (2540 has unkeyed uses). Treat as **strong
corpus association**, not a guaranteed emblem ontology. Modal sit: wall-flush,
cstat 464, repeat 32×32, origin ~2.55 player-heights.

## Affordance gate

`door_affordance_report` on an authored PlanarLayout compile. Mandatory doors
must not be mechanically unusable or visually identical to neighboring fill,
unless intent sets `hidden` (secrets) or `INTENTIONALLY_UNREACHABLE`.

```text
python -m bloodmap door-audit --blueprint sp-v2 --json reports/SP-v2-door-affordance.json
python -m bloodmap door-mine --maps maps/blood -o reports/blood-door-families.json \
  --signifiers reports/blood-key-signifiers.json
python -m bloodmap door-query reports/blood-door-families.json --direct-use 1 --keyed 1 --limit 8
```
