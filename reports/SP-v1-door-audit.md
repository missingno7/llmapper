# SP-progression-v1 door / gate audit

Authored-map forensic report. Original campaign maps are evidence, not this file.

## Why the mandatory keyed door cannot be opened from a normal standing position

The archive gate (`region:keyed_door`) is a type-600 closed Z-ceiling slab
(`rest opening 0`). The player stands in `region:start`, not inside the slab.

NBlood `ActionScan` (Use, range **64** Build units):

- XWALL `trigger_push` → wall trigger
- portal hit whose **next** sector has XSECTOR `trigger_wall_push` → that sector
- XSECTOR `trigger_push` only if the player is already in the sector, or the
  hitscan strikes its floor/ceiling

SP-v1 set **`trigger_push=1` only**. There is no `trigger_wall_push` and no
XWALL on the portal. Use hits the hallway portal wall and nothing fires.

The same map's gallery/exit/secret doors are RX-only, which *is* the native
remote-switch pattern. Their failure is visual, not interaction.

## Visual failure

Closed portals have zero opening, so the player never sees the door sector's
floor/ceiling (tile 104). They see the **approach-side portal wall**, which
inherited the neighboring room fill (180 masonry, 5, 184, …). Tile 104 is not a
campaign door face (ontology: 2 placements). The 8 player-width openings are
entire walls moving, not door leaves in a frame.

There is no skull-key emblem. Campaign maps repeatedly place wall-aligned
sprite **2540** next to skull-key locks.

## Player-facing checklist

| gate | identify visually | Use from hallway | requires key | opens enough | progression |
|---|---|---|---|---|---|
| keyed_door | no | **no** (missing Wallpush) | key=1 authored | yes (on-state) | unique cut |
| gallery_door | no | n/a (RX 100) | no | yes | unique cut TX 100 |
| exit_door | no | n/a (RX 101) | no | yes | unique cut TX 101 |
| secret_door | no (acceptable if hidden) | n/a (RX 102) | no | yes | optional |

Runtime: NBlood **load** of v1 passed. An action oracle at the default spawn
would Use toward the closed **exit** door, not the keyed door. Gate tests need
posed starts (see v2 fixtures).

ActionScan Use range: 64 Build units.

NBlood ActionScan: XWALL.trigger_push; portal hit whose next XSECTOR has trigger_wall_push; XSECTOR.trigger_push only if already inside or floor/ceiling hit

## region:keyed_door

- classification: `UNKNOWN`
- intent: `{}`
- native: type 600 z_ceiling family `t600|z_ceiling|sector_push|norx|key|closed`
- triggers: ['trigger_push'] rx=0 key=1
- interaction: sector_push
- closed rest opening: 0 open-state: 28160
- region tiles wall/floor/ceil: 104/104/104
- visually distinct approach face: False
  - portal wall 20: approach picnum 5 vs neighbor fill 5 width 8.0 pw opening 0
  - portal wall 22: approach picnum 180 vs neighbor fill 180 width 8.0 pw opening 0
- player-facing failures:
  - closed Z-door used from the hallway requires XSECTOR.trigger_wall_push; trigger_push alone does not fire ActionScan on the portal wall
  - approach portal picnum matches neighboring fill; closed gate is not visually a door
  - keyed gate has no nearby non-key sprite and no distinct face tile

## region:gallery_door

- classification: `UNKNOWN`
- intent: `{}`
- native: type 600 z_ceiling family `t600|z_ceiling|remote_rx|rx|nokey|closed`
- triggers: [] rx=100 key=0
- interaction: remote_rx
- closed rest opening: 0 open-state: 39424
- region tiles wall/floor/ceil: 104/104/104
- visually distinct approach face: False
  - portal wall 48: approach picnum 184 vs neighbor fill 184 width 8.0 pw opening 0
  - portal wall 50: approach picnum 5 vs neighbor fill 5 width 8.0 pw opening 0
- player-facing failures:
  - approach portal picnum matches neighboring fill; closed gate is not visually a door

## region:secret_door

- classification: `UNKNOWN`
- intent: `{}`
- native: type 600 z_ceiling family `t600|z_ceiling|remote_rx|rx|nokey|closed`
- triggers: [] rx=102 key=0
- interaction: remote_rx
- closed rest opening: 0 open-state: 33792
- region tiles wall/floor/ceil: 104/104/104
- visually distinct approach face: False
  - portal wall 61: approach picnum 110 vs neighbor fill 110 width 6.0 pw opening 0
  - portal wall 63: approach picnum 184 vs neighbor fill 184 width 6.0 pw opening 0
- player-facing failures:
  - approach portal picnum matches neighboring fill; closed gate is not visually a door

## region:exit_door

- classification: `UNKNOWN`
- intent: `{}`
- native: type 600 z_ceiling family `t600|z_ceiling|remote_rx|rx|nokey|closed`
- triggers: [] rx=101 key=0
- interaction: remote_rx
- closed rest opening: 0 open-state: 33792
- region tiles wall/floor/ceil: 104/104/104
- visually distinct approach face: False
  - portal wall 70: approach picnum 180 vs neighbor fill 180 width 8.0 pw opening 0
  - portal wall 72: approach picnum 181 vs neighbor fill 181 width 8.0 pw opening 0
- player-facing failures:
  - approach portal picnum matches neighboring fill; closed gate is not visually a door

