# The Phantom Terminus (the Ghost Station, rebuilt)

The owner, 2026-11-24: "That ghost station looks quite plain, I would make it
more creepy and instead of just saying GHOST STATION maybe it should be
something like phantom something. Check some themes from existing levels like
DW."

## The story

The last train of the old line came in one night with everyone aboard already
dead. The doors stayed shut. The company bricked the line up behind it and
struck it off the map; the men who did the bricking are still on the platform.
The train is still waiting to leave. Caleb, who was on the Phantom Express
himself (E1M2, E1M3), says "End of the line" here.

The Phantasm is the place's own ghost: what it sounds when it sees you is
`sound:1600`, a train whistle and a shriek.

## The exemplars

| Part | Exemplar |
| --- | --- |
| the platform hall: pale tiled walls with a dark band, rusted square columns on a rusted edge, folding gates, torn bills, round lamps in the ceiling, stairs to a shut gate, gore on the wall | DWE3M2 s481, s246, s194 (Death Wish) |
| a train that moves when the prize aboard is taken, with an earthquake, dudes and the lights switched | DWE3M2 s247 (type 614, rx 105), sprites 208, 3000, 389, 172, 244-246, 3002 |
| the dark beyond: ribbed roof, light in bars across the ground | DWE3M2 s351, s362 |
| a car's inside, its windows, its end door; a train's lit front seen down a drowned tunnel | SSR3.MAP s5, s46 looking at s45 (community) |
| a stone-vaulted running tunnel with timber ties, buffers at its end | GHOSTTWN.MAP s767, s709 (community); EU13.MAP s281 for a portal with a lantern and a body behind bars |
| robed figures along an endless line with small lights | 666UNDER.map s252 (community) |
| the name | tile 1667, Blood's green gothic "Phantom" (E1M2, E1M3, DWE2M6, DWE2M10), as it is hung there |
| the Gravesend Station above, so the line is one line | `l3_station.py`, study `station` (its carriage, its livery 1665, its platform edge) |

## The plan

The hatch, its three dials, the inspection plate and the 28-step stair stay as
they are (wires `ghost:*`, tests). The platform keeps its place and its floor
(z 118,784), its secret (the level's seventh) and its reward.

1. **The stair's foot: a shut booking hall.** Before the platform: a small
   ticket hall with folding gates, a booking window with its clerk, a clock, a
   line map with the stations struck out, and a lamp that fails. The first
   sight through the gates is the train's lit windows.
2. **The platform**, broken into bays by the columns: waiting benches with
   those who waited, trunks and a pram's worth of luggage, the sweepers' barrow
   and bricks beside the bricked-up end, gore on the tile, bills. Levels: the
   platform, its rusted edge a step down, the track bed, an overbridge or a
   raised signal cabin if the height allows (GHOST_CLEAR is 32,768).
3. **The train**: a car alongside, as long as the platform allows, its windows
   lit a sick green, its dead still sitting in them. One door stands open.
   The prize is inside.
4. **The ride**: taking the prize shuts the station down: the lamps go out, the
   whistle sounds, the ground shakes, and the car moves off with the player
   aboard into the tunnel, past figures standing in the niches, and stops at
   the bricked end beside a door. Phantasms come for the car while it runs.
   From the stop a service passage climbs back to the platform (and the way
   out), and the car can be sent back.
5. **The drowned end**: the line's other end falls under black water, with the
   front of a second train, one lamp lit, under it.

Nobody may be locked in: at every moment there is a way to the stair, and a
player who never boards can leave.

**Name:** `Phantom` in 1667 and TERMINUS lettered beneath, on the platform's
wall and over the booking hall. Nothing says GHOST STATION any more.

## Rules

Everything in `aldermack-design.md` ("Rules that outlast this build") holds.
The car is a moving sector: its whole travel stays inside one host (the track),
which nothing else cuts; what rides in it carries `CARRY_WITH`; its floor has
relative alignment; it has the sound of a train (115, 277; motion_sounds).
