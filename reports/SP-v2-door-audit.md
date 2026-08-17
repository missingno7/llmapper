# SP-progression-v2 door / gate audit

Authored-map forensic report. Original campaign maps are evidence, not this file.

ActionScan Use range: 64 Build units.

NBlood ActionScan: XWALL.trigger_push; portal hit whose next XSECTOR has trigger_wall_push; XSECTOR.trigger_push only if already inside or floor/ceiling hit

## region:crypt_door

- classification: `MANDATORY`
- intent: `{'purpose': 'crypt mouth', 'classification': 'MANDATORY', 'interaction': 'direct_use', 'realization': 'campaign wall_push Z-ceiling, face 22'}`
- native: type 600 z_ceiling family `t600|z_ceiling|wall_push|norx|nokey|closed`
- triggers: ['trigger_push', 'trigger_wall_push'] rx=0 key=0
- interaction: wall_push
- closed rest opening: 0 open-state: 19712
- region tiles wall/floor/ceil: 22/22/22
- visually distinct approach face: True
  - portal wall 17: approach picnum 22 vs neighbor fill 110 width 2.0 pw opening 0
  - portal wall 19: approach picnum 22 vs neighbor fill 110 width 2.0 pw opening 0
- player-facing failures: none recorded

## region:keyed_door

- classification: `MANDATORY`
- intent: `{'purpose': 'skull-keyed archive gate', 'classification': 'MANDATORY', 'interaction': 'direct_use', 'realization': 'E3M3-style wall_push Z-ceiling, face 495, emblem 2540'}`
- native: type 600 z_ceiling family `t600|z_ceiling|wall_push|norx|key|closed`
- triggers: ['trigger_push', 'trigger_wall_push'] rx=0 key=1
- interaction: wall_push
- closed rest opening: 0 open-state: 28160
- region tiles wall/floor/ceil: 495/495/495
- visually distinct approach face: True
  - portal wall 32: approach picnum 495 vs neighbor fill 5 width 2.0 pw opening 0
  - portal wall 34: approach picnum 495 vs neighbor fill 180 width 2.0 pw opening 0
- player-facing failures: none recorded

## region:gallery_door

- classification: `MANDATORY`
- intent: `{'purpose': 'remote stair-to-gallery door', 'classification': 'MANDATORY', 'interaction': 'remote_switch', 'realization': 'RX 100, no Push/Wallpush, face 200'}`
- native: type 600 z_ceiling family `t600|z_ceiling|remote_rx|rx|nokey|closed`
- triggers: [] rx=100 key=0
- interaction: remote_rx
- closed rest opening: 0 open-state: 39424
- region tiles wall/floor/ceil: 200/200/200
- visually distinct approach face: True
  - portal wall 62: approach picnum 200 vs neighbor fill 184 width 2.0 pw opening 0
  - portal wall 64: approach picnum 200 vs neighbor fill 5 width 2.0 pw opening 0
- player-facing failures: none recorded

## region:secret_door

- classification: `OPTIONAL`
- intent: `{'purpose': 'hidden secret panel', 'classification': 'OPTIONAL', 'hidden': True, 'interaction': 'remote_switch', 'realization': 'same face as gallery fill; not a visible door'}`
- native: type 600 z_ceiling family `t600|z_ceiling|remote_rx|rx|nokey|closed`
- triggers: [] rx=102 key=0
- interaction: remote_rx
- closed rest opening: 0 open-state: 33792
- region tiles wall/floor/ceil: 184/184/184
- visually distinct approach face: False
  - portal wall 75: approach picnum 110 vs neighbor fill 110 width 6.0 pw opening 0
  - portal wall 77: approach picnum 184 vs neighbor fill 184 width 6.0 pw opening 0
- player-facing failures: none recorded

## region:exit_door

- classification: `MANDATORY`
- intent: `{'purpose': 'remote exit door', 'classification': 'MANDATORY', 'interaction': 'remote_switch', 'realization': 'RX 101, face 345'}`
- native: type 600 z_ceiling family `t600|z_ceiling|remote_rx|rx|nokey|closed`
- triggers: [] rx=101 key=0
- interaction: remote_rx
- closed rest opening: 0 open-state: 33792
- region tiles wall/floor/ceil: 345/345/345
- visually distinct approach face: True
  - portal wall 84: approach picnum 345 vs neighbor fill 180 width 2.0 pw opening 0
  - portal wall 86: approach picnum 345 vs neighbor fill 181 width 2.0 pw opening 0
- player-facing failures: none recorded

