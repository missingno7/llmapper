# Scratch LevelIR construction

`LevelBuilder` is the deterministic starting point for maps that do not inherit an
original MAP. It creates and edits only `LevelIR`; binary encoding remains the same
verified final boundary used by every other workflow.

```python
from bloodmap import LevelBuilder

builder = LevelBuilder()
room = builder.add_sector(
    [(0, 0), (8192, 0), (8192, 8192), (0, 8192)],
    ceiling_z=-24576,
    floor_z=8192,
)
builder.set_player_start(sector=room.sector_id, x=4096, y=4096, z=0, angle=0)
level = builder.build()
```

## Construction invariants

- sector loops require at least three unique points, clockwise Build screen-space
  winding, nonzero area, and no self-intersection;
- wall and sector IDs are dense and allocated deterministically;
- portals require exact coincident reversed wall endpoints in different sectors;
- sprite and player positions are checked against sector geometry and vertical
  bounds;
- XSECTOR, XWALL, and XSPRITE records receive independent lowest-free positive
  IDs and source-compatible defaults;
- `build()` runs the ordinary MAP structural validator before returning a level.

`set_behavior(kind, id, **fields)` exposes named LevelIR fields instead of packed
bits. Unknown field names fail immediately. This keeps construction readable while
preserving the engine's exact serialized contract.

## Walkability profiles

`portal_profiles(level)` reports doorway width, current vertical opening, and the
maximum opening configured by type-600/type-602 vertical-motion sectors. The
default walkability threshold is 2048 horizontal units and 8192 vertical units.
This deliberately rejects visually connected but impractically narrow routes.

Closed doors correctly report `walkable_at_rest: false` and
`walkable_when_open: true` when their configured motion provides enough space.

## First puzzle room

```text
python -m bloodmap design-first-room \
  --report work/first-puzzle-room-report.json \
  -o work/first-puzzle-room.MAP
```

The design is authored in `bloodmap/designs.py`. Switch A sends command `On` over
channel 100 to the east vertical door. The revealed alcove contains Switch B,
which sends `On` over channel 101 to the north reward door. A sawed-off shotgun is
the current completion reward. See `reports/first_puzzle_room.md` for the exact
layout and validation evidence.

The generic action oracle can verify an intended interaction positioned at the
player start:

```text
python -m bloodmap oracle-nblood-action work/first-puzzle-room.MAP \
  --nblood reference/blood/nblood.exe --game-dir reference/blood \
  --work-dir work/first-puzzle-room-action \
  -o work/first-puzzle-room-action.json
```
