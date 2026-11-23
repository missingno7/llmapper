# The Aldermack, rebuilt

The owner, 2026-11-23: "Later I would do a major overhaul of the whole
aldermack to make it look better", then "Yes, start it". Studies:
`knowledge/blood/studies/theatre` (sizes, exemplars) and
`knowledge/blood/studies/aldermack-rebuild`. Coordinates are plan units
(1 = 1,024); heights are z over GRADE (8192), up positive; a body is 16,960.

## The exemplars

The owner, 2026-11-23: "I think we can find better examples in existing
levels". They are in `knowledge/blood/studies/aldermack-rebuild/notes.md`,
with the records; build from these and cite them:

| Part | Exemplar |
| --- | --- |
| the house and its first look, seats, aisle, the seated dead, the beam | THESLUMS.MAP s508, s509-s549 |
| the performer, the spotlight and its shadows | HUNT.MAP s672-s675 |
| proscenium, drape legs, apron | SCHOOL_.MAP s177-s182 (study `theatre`); AFTSHOCK.MAP is Duke E1L1 converted: an idea (dark frame, bright legs), never its room |
| footlights, stage face, tied-back drapes | EU11_.MAP s346, s349 |
| boxes, circle, the star's room: drapes, candelabra, chandeliers | REALM4.MAP s181; NUTHOUSE.MAP s263 for boxes over the seats |
| the name in lights over the street | THESLUMS.MAP s484 |

## What was wrong

One wallpapered box, 7 x 7, with a slab for a stage, three carpet stripes for
seats, a curtain that did not read, one window, and a plain street door. The
campaign never built a theatre, so the marks to hit are the study's: a curtain
that is the far WALL of the room, a framed proscenium, small identical seats
in a grid, a floor that falls to the stage, a room far taller than any other,
and darkness.

## The story

The Aldermack's last night. The Cabal took the house during a performance and
never let it end: the audience is still in its seats, the player is still on
the rope. Drawing the curtain is what the player does here, and it is a
mistake they will enjoy. Twisted and theatrical, not a museum. (The owner of
the Rat King's shrine: "looks twisted and I love it".)

## The plan

The block is x 17 to 26, y 3 to 15 (its south-east corner is chamfered from
25.5), with the foyer wing x 26 to 30, y 6.5 to 10.5. The house is turned to
run north-south over the plot's whole depth; today it stops at y 11 and
y 11 to 15 is solid void.

| Part | Rect (x0, y0, x1, y1) | Floor | Clear | Owner |
| --- | --- | --- | --- | --- |
| stage (fly tower over it) | 19.25, 3.5, 25.75, 6.75 | +11520 | to +115712 | house |
| proscenium strip, 256 deep | opening 20.25 to 24.75, y 6.75 to 7.0; side bays 0.5 wide at 3.0 bodies, the middle 3.6 | +11520 | 51200 / 61056 | house |
| apron | 20.1, 7.0, 24.9, 7.5 | +11520 | house's | house |
| steps up to the apron | 20.1 to 20.9 and 24.1 to 24.9, y 7.5 to 8.5 | 0 to +11520 | | house |
| orchestra pit | 20.9, 7.5, 24.1, 8.5 | -8192, steps out at one end | | house |
| front floor and cross aisle | 20, 8.5, 25, 10 | 0 | +96256, a dome over it | house |
| stalls | 20, 10, 25, 12.9 | rows rising 1,024 each | | house |
| dress circle (solid below, its front is a parapet over the stalls' back wall) | 20, 13, 25, 14.6 | +24576, two tiers | | house |
| west boxes (solid below) | 19.125 to 20: y 10.125 to 11.25 and 11.375 to 12.75 | +24576 | 20480 | house |
| stage box, west | 19.125 to 20: y 7.6 to 8.4 | +24576 | | house |
| east: false boxes | 0.1 deep, curtained shut, matching the west ones | | | house |
| pass-door passage, west | 19, 8.5, 20, 10 (the stage doors' frame meets it at x 19) | 0 | 24576 | house |
| vomitory, east | 25, 8.5, 26, 10 (meets the foyer's west wall at x 26) | 0 | 24576 | house |
| circle stair, east | 25.125, 10, 25.875, about 14, climbing south from the vomitory to the circle | 0 to +24576 | | house |
| foyer | 26, 6.5, 30, 10.5 (as now) | 0 | 40960 | front |
| avenue lobby | 30, 7.5, 31.5, 9.5 (as now) | 0 | | front |
| front on the forecourt | y 10.5 to 11, x 26 to 30, faces south | | | front |
| backstage corridor and stage doors' bay | 17, 4, 18.875, 11 (as now) | 0 | 32768 | backstage |
| dressing room | 17, 11, 19, 14 (as now) | 0 | 24576 | backstage |
| way onto the stage | 18.875, 4.75, 19.25, 5.75, steps from 0 to +11520 | | | house |

The circle's west end opens on the second west box at the same floor. A
player can drop from either to the stalls.

Joins that cross owners, and must keep their place:
`backstage corridor east wall (x 18.875, y 4.75 to 5.75)`; the stage doors'
frame `(x 19, y 8.5 to 10)`; the foyer's west wall `(x 26, y 8.5 to 10)`;
the parlor passage `(x 17, y 7 to 8)`; the avenue lobby `(x 30)`; the forecourt
door `(y 11)`.

Free: the sewer's layers start at z 28672, so the pit may sink; no other
room lies under x 17 to 26.

## Rules that outlast this build

- A moving sector never leaves its parent; its parent is never cut by light
  (`swept_state.escape`, `swept_state.hosts`).
- A masked wall never shares its record with a step band.
- Dark house, light on purpose: chandelier, sconces, the stage once drawn.
- The owner's name for a tile outranks any reading; study a tile's uses
  (`tools.tile_usage`) before wearing it.
- Wall and ceiling sprites are seated by the drawn box; chains run up into
  ceilings.
