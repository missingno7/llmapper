# LevelIR authoring and semantic observations

`LevelIR` is the canonical authoring model. Binary MAP structures are an import and
export concern only:

```text
MAP bytes -> DiskMap -> LevelIR -> authoring operations -> LevelIR -> DiskMap -> MAP bytes
```

An LLM client should never calculate encrypted offsets, patch packed records, or
concatenate sector/wall arrays. It observes stable semantic references and requests
bounded LevelIR operations.

## First-class operations

```python
level = read_map("maps/E1M2.MAP").to_level_ir()
room = read_map("maps/E1M1.MAP").to_level_ir().extract([12, 13])
closed_room = read_map("maps/E1M1.MAP").to_level_ir().extract_closed([12, 13])

observation = level.observe([14])
attached = level.attach(
    room,
    destination_wall=138,
    fragment_wall=0,
    channel_policy="remap",
).level
connected = attached.connect_portals(200, 900)
stairs = connected.connect_pathway(240, 910, max_step_height=2048).level
```

`extract`, `extract_closed`, `insert`, `attach`, `connect_portals`,
`connect_pathway`, `translate`, and `rotate_quarter_turns` all operate at this
layer. Allocation reports map local room
references to final LevelIR references so later operations do not infer array
offsets.

## Observation contract

`LevelIR.observe()` returns `bloodmap.level-observation` schema version 1. With no
selection it provides:

- map counts, bounds, player start, type inventory, and tile inventory;
- a compact sector index with bounds, neighbors, contents, and channel presence;
- the complete TX/RX graph with stable references and verified system-channel
  names.

With selected sectors it instead focuses the response:

```text
python -m bloodmap observe maps/E1M2.MAP --sectors 14 \
  -o work/E1M2-sector-14.json
```

The focused `selection` includes:

- sector geometry, surfaces, slope values, neighbors, and contained sprites;
- one-sided attachment walls and portals leaving the selection;
- concise XSECTOR/XWALL/XSPRITE behavior fields and active trigger modes;
- channels touching the selection, including their remote endpoints;
- classified external geometry, trigger, marker, and ownership dependencies.

References use strings such as `sector:14`, `wall:138`, and `sprite:39`. Numeric
Blood type, command, and tile IDs remain neutral until their names are established
from source or corpus evidence. Observation is derived and can always be rebuilt;
it is not serialized back into the MAP.

## Composition recipes

`bloodmap.composition-recipe` schema version 1 records `attach`, `insert`,
`pathway`, and `set_player_start` operations. Later operations reference allocated walls by operation ID
and fragment-local wall ID, so an LLM never predicts destination array offsets.
Every donor selection uses behavior closure; unresolved gameplay dependencies and
inserted-layout collisions fail the build. Player starts reference an allocated
fragment sector and donor-local position, so the same placement transform controls
the room and start together. `recipes/e1m2-crossroads.json` is a working multi-map
example; `recipes/e1m2-remix.json` creates a four-room reordered E1M2 prologue.

Construction remains above `LevelIR`: recipes choose semantic rooms and request
bounded operations, while the binary writer stays the deterministic final backend.
