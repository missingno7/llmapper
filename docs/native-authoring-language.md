# Native Blood authoring language

llmapper can emit a valid MAP. That is not the same as authoring the way a
Blood mapper does: a locked crypt door is a moving boundary, a Use/wall-push
trigger, a key condition, a recognizable face, a frame of neighboring fill,
often an emblem, and an opening that fits the room.

The LLM remains the mapper. This layer supplies **grounded knowledge and
verified operations**. It does not choose the door.

## Research loop

```text
decide what to build
    → query current knowledge
    → if insufficient: original maps → source/runtime → promote → retry
    → construct the pieces deliberately
```

Do not annotate every tile first. Do not turn families into
`if locked: texture=123`. Query precedents, then place.

## Populations

Campaign `E*.MAP` is SP evidence. BloodBath `BB*.MAP` is multiplayer.
Generated reconstructions are never design evidence.

## Operations that are allowed to be thin

These fill native fields only:

- `xsector_direct_use` / `xsector_remote_rx` — ActionScan vs RX split
- `PlanarLayout` `face_picnum` on a connection — paint both portal walls
- `place_on_wall` / `place_on_floor` — resolved anchors
- region `intent` — authored classification (`MANDATORY`, `OPTIONAL`,
  `STATE_DEPENDENT`, `INTENTIONALLY_UNREACHABLE`, `HELPER`)

They are not `make_door()` or `decorate_room()`.

## Intent vs reachability

On **authored** maps, unreachable is not automatically broken.

| class | meaning |
|---|---|
| MANDATORY | required for the intended exit |
| STATE_DEPENDENT | reachable after a named action |
| OPTIONAL | secret / side |
| INTENTIONALLY_UNREACHABLE | scenery, helper, staging |
| HELPER | mechanism envelope |
| UNKNOWN | not declared |

Do not apply this taxonomy as truth for original maps. Originals get
measured candidates (adjacent-unreachable sectors, rest vs final graphs).

Intended progression, physical reachability, and observed skips stay separate.
A jump skip is classified by the mapper, not auto-sealed.

## Query

```text
python -m bloodmap door-query reports/blood-door-families.json --direct-use 1 --keyed 1
python -m bloodmap door-query reports/blood-door-families.json --remote 1 --motion z_ceiling
```

Sprite context (wall-mounted, near keyed motion, interactive, …) is
`reports/blood-sprite-context.json` after `assets.mine_sprite_context`.

## Persistent test level

`experiments/sp_progression_v1.py` → v2 → … one map, incremental literacy.

v1 proved progression wiring. v2 proved hallway Use, distinct faces, and a
skull-key emblem, plus one scenic unreachable courtyard.

See [door-affordances.md](door-affordances.md).
