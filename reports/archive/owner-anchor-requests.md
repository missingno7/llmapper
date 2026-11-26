# Owner anchor requests, from Gravesend

`bloodmap.owner_anchors` names 224 tiles. These are the ones this city needs and that file does not have, and the ones whose anchor gives them a role the city uses them against.

## Tiles with no anchor

| tile | the city uses it as | records | where it came from |
| --- | --- | --- | --- |
| 536 | sprite | 1 | `furniture.FURNITURE['statue']` |
| 537 | sprite | 1 | `furniture.FURNITURE['urn']` |
| 1070 | sprite | 9 | the campaign's commonest wall-aligned switch: 104 as kSwitchToggle and 78 as kSwitchOneWay |
| 2552 | sprite | 1 | Blood's key 1: sprite type 100 |
| 2553 | sprite | 1 | Blood's key 2: sprite type 101 |
| 2554 | sprite | 1 | Blood's key 3: sprite type 102 |
| 2555 | sprite | 1 | Blood's key 4: sprite type 103 |
| 2556 | sprite | 1 | Blood's key 5: sprite type 104 |

## Tiles the city uses against their anchor

Each is a question, not a licence: the owner's word for the tile and the campaign's use of it disagree.

**379 as a floor** -- the owner names it a wall, 'stone wall' (untested binding); 3 record(s).

E3M1 puts 379 on the tops of s0, s339 and s343 -- its three end walls -- and `street.END_WALL_FLOOR_TILE` was measured from them. The owner names 379 a wall, 'stone wall'. Which is right for the top of a stone mass is the owner's to say

**2490 as a floor** -- the owner names it a wall, 'light marble' (untested binding); 23 record(s).

DWE3M10's sea is 2490 under palette 10 with pan_floor, pan_always and drag -- 25 of its 34 campaign sectors carry the palette and pan -- and the whole waterfront grammar is built on it. The owner names 2490 a wall, 'light marble', which is what the other 8 are
