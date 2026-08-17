# SP-progression-v2 understanding

Persistent test level continued from v1. Geometry is still invented. Door
*realizations* were chosen from campaign precedents after the v1 forensic audit.

## Acceptance

| gate | result |
|---|---|
| authored geometry errors | 0 (2 unreachable-pickup warnings: shotgun/key sit outside the *largest* at-rest component, which is the closed archive/stair island) |
| native validation | pass |
| progression unique cuts | skull key, TX 100, TX 101 required; TX 102 optional |
| DoorAffordance | **pass** |
| NBlood load of posed fixtures | map_initialization markers true |
| NBlood Use screenshots | **inconclusive** this session (window focus failed) |

## Door choices (not one template)

| region | behavior | interaction | condition | signifier |
|---|---|---|---|---|
| crypt_door | Z-ceiling type 600 | Wallpush + Push | none | approach face **22** (2 pw) |
| keyed_door | Z-ceiling type 600 | Wallpush + Push | skull key=1 | face **495** + wall sprite **2540** |
| gallery_door | Z-ceiling type 600 | remote RX 100 | none | face **200** |
| exit_door | Z-ceiling type 600 | remote RX 101 | none | face **345** |
| secret_door | Z-ceiling type 600 | remote RX 102 | none | **hidden**: gallery fill 184 |
| crypt_view | static | blocking window | n/a | INTENTIONALLY_UNREACHABLE courtyard |

## What v1 was missing

The keyed door was `trigger_push` only. ActionScan from the hallway never
fired. Faces were neighboring fill; tile 104 is not a campaign door.

## Scenic note

`crypt_view` is a blocking portal into a lower courtyard. Original campaign
maps have many adjacent-unreachable sectors (E1M1: 26 next to the rest
component, 24 without gameplay sprites). Those are candidates, not automatic
scenery labels.

See [door-affordances.md](../docs/door-affordances.md) and the gate dump below.

---
