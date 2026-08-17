# Independent understanding: `SP-progression-v1.MAP`

Frozen from `reports/SP-progression-v1-understanding.json`. This packet was
not given E2M2 as a target. Original campaign vertices are not present.

## What this map is

A Blood v7 scratch single-player map. 15 sectors, 80 walls, 11 sprites.
Native validation 0 errors. No sky-parallax field. Four wall-mounted push
switches, one skull key, one optional health cache, two floor-supported
cultists (type 201).

It is a **gated indoor sequence**, not a deathmatch yard: 3 sectors
rest-walkable from the start, 15 after intended actions, 8
blocked-or-state-dependent portals.

## Progression

Independent counterfactual re-solve:

| dropped | exit still reachable? | reachable sectors |
| --- | --- | --- |
| nothing | yes | 15 |
| skull key | no | 3 |
| channel 100 (archive switch) | no | 9 |
| channel 101 (gallery switch) | no | 13 |
| channel 102 (secret switch) | yes | (secret omitted) |

Required: key 1, TX 100, TX 101. Optional: TX 102. Exit channel 4 fires only
after the exit chamber is reached.

Witness: spawn in the covered start (exit door closed ahead) → crypt branch
for the skull key → keyed door into the archive → wall switch opens the
stair gate → taller upper gallery → gallery switch opens the start-side exit
→ exit switch. The secret remains optional.

## Spatial phases (measured)

Start set is small (3 sectors). Unlock grows into the archive and stair
(9). Archive switch adds the gallery (11). Gallery switch adds the exit
(13). Secret switch fills the last two. Clear height and shade change with
those sets: the gallery uses a higher floor (2 player-heights up, 0.5 PH
steps) and a lighter palette (wall 184, floor 278, shade 4–8) than the crypt
(lower floor, wall 110, shade 24–28). The start uses masonry 180 / floor 292.

## Object attachment

All four switches are `wall_flush`, median height **2.18 player-heights**,
facing into their sectors. Use-pose gate passed. No unexplained floating
controls. Pickups and cultists are floor-anchored.

## Enemies

Two type-201 actors, floor-supported, ~3.6 player-widths from walls. Visible
as room occupants, not combat-balanced.

## What this prose is for

A later builder should preserve **gated multi-stage progress**, wall-mounted
usable controls, a lower key branch, a higher return gallery, and an optional
side cache — not these exact rectangles.
