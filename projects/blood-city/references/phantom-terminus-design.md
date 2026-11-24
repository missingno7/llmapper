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

## As rebuilt (2026-11-24, after the owner's ride)

The owner rode it: "train rides correctly", and then: 1717 is morgue drawers
and no floor; the train is one sector dressed in sprites, make it of sectors
that share a motion, and its ceiling must move with it; 51 and 52 are wall
decals and no objects; there are lit sectors with no light, and a light that
blinks must take its neighbours with it; the drowned end is a piece of wall,
give it space; the reapers' niches want flickering light.

- **The train is a body of sectors** (`level/carriage.py`,
  `bloodmap.mechanism.rigid_body`, study `moving-bodies`): zero-height hull
  solids, windows in two half bays with the pane between, benches, arms, a
  raised roof, a cab with a desk and a window, a running board all round.
  Every member is type 616 with one travel and one wire; floors and ceilings
  are aligned to the sector (bit 64). The track is a type 614 with the same
  motion and no wall of its own flagged, only so that the wheels hung in its
  space ride too (E1M2 s34).
- **The rails lie 6,144 under the platform.** Two steps at the platform's west
  end bring back whoever falls in; the bore widens past the platform's end so
  nothing scrapes a rider off the running board; the gap at the door is 64.
- **The same carriage, drowned**, stands askew in a flooded cavern with water
  all round and a fallen slab along its roof. One builder makes both: `Axes`
  puts the plan on any integer lattice ((63, 16), (-16, 63) is 14 degrees).
- **Light is traced, not painted.** The station left `lights.OWN_LIGHT`; it is
  lit by the lamps that hang in it, with a shade bias for how dark it is.
  `phantom_terminus.light_groups` names the lamps that blink, go out or
  travel; `light_stage.switch_lamps` traces the map without them and gives
  every sector that changes the same wave and wire. The light that falls from
  the coach's windows follows the coach by a Link.
- **A receiver that also sends is never given a light's wire**: the booking
  hall credits the secret, and would have credited it when the lamps went out.
- **Frames show a wave at its lit instant** (`visual.shade_waves_lit`); a lamp
  authored dark that flickers on used to be drawn as a lamp that is out.
- **Green is palette 4** on 109, 304, 454, 146 and 1665. On 300 and 301 it is
  camouflage; as the colour of a floor's light it reads as moss. Both were
  tried and taken out.
- Round 5 of the blind readers: recognition 4, comparison 4, use 4 with
  nothing blocking (3 in every round before), sense 3, its faults all marked
  uncertain. It does not pass by the rule on sense and on the flooded view's
  short car ("reads as a kiosk").
- **Ridden headless** (`experiments/moving_bodies/ride.py`): the engine carries a
  rider at the car's own speed across the body's sectors, with nothing fatal.
- **Owed to the owner's walk:** standing on the running board during the run,
  being under the train, the flicker's pace, the reapers' lights.

## As first built (2026-11-24; the car, the light and the drowned end are superseded above)

`level/phantom_terminus.py`; tests/test_phantom_terminus.py; pose set
`phantom`. Built by one Sol worker in two rounds and finished by the
integrator.

- **The ride works on paper, unridden.** A type 616 car, its whole sweep inside
  the track, a lane on both flanks and both ends; the prize (Tommy gun) and the
  driver's handle (carried, works with full bullets, unlabelled: the word RUN drew readers off the gun) start one show; RECALL
  at the signal cabin and at the brick stop brings the car home. The walk from
  either berth to the stair is read back in the tests at both poses.
- **Green is palette 4 on tiles that hold colour.** It leaves greys grey: 374
  under palette 4 stays white, 1717 goes green.
- **The drowned end is the train's second car**, in the running car's own
  window, livery and seated dead, standing in the water to its sills. A
  boiler built of raised blocks never read as a locomotive in two tries.
- **The sewer's mouth pass (tile 194) skips the station**: it had repainted 65
  of its walls, the brick barrier among them.
- A failing lamp is authored LIT with a positive amplitude, so it is drawn lit
  at rest and drops out; authored dark it reads as a ring of light round a hole.
- A raised block's outer faces belong to the room round it: paint them there
  (`paint_wall(host, ...)`), or they wear the dark room's shade.
- **Owed to the owner's walk:** jumping during the ride, the Phantasms' timing,
  the mix of the whistle and Caleb's line at the stop.
