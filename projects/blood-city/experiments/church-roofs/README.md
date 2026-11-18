# Experiment: a low sky is a lid

2026-11-17, the afternoon. Follows `../church-skyline`, and supersedes its
method. Before/after pairs: [`before-after.png`](before-after.png).

## What the owner said

Walking the morning's build in NBlood:

> when you put parallax sky low it is covering view like a normal ceiling.
> For example that exterior wall around church yard could be a normal red
> sector with some floor height instead of lowering sky.

## What that looked like

`before/` is the morning's result, from seven new cameras that look *past*
something low at something tall (`look.py --set over`):

- `yard_to_tower`: from the churchyard the church has no tower. It stands
  17.4 bodies tall forty units away and paints 0 pixels.
- `yard_out_south`, `yard_out_east_up`: nothing beyond the yard wall exists.
- `avenue_over_wall`: the west street's blocks do not show over the wall.

The morning's own record called the hidden nave "a limit of the technique".
It was a limit of the choice. A low parallax ceiling is still a ceiling: the
renderer paints it from the top of the far wall upward over every column the
sector covers.

## What was done

Nothing is short because its sky is low any more.

| thing | this morning | now |
|---|---|---|
| churchyard wall, mausoleum row | apron on two streets, 11.6 bodies on the other two; yard sky lowered to 3.9 | raised-floor sectors 3.1 bodies tall on all four sides; yard under the city's sky |
| church's low range | apron, sky 3.9 | roof sector, floor at 3.9, in its own layer over the rooms |
| nave | invisible | two pitched roof sectors, eaves 5.8, ridge 7.0: a gable at each end |
| tower | three street faces under a raised sky | the same, plus its west face rising out of the roof |
| way in | portal in the avenue face, door in the cemetery face | **one door, in the tower's foot, and a second inside it** |

`bloodmap.skyline` gained `roof`, `dress_steps`, `lowered_skies` and
`leaks_under_roofs`. Skies held a body or more under the city's: 5 this
morning, 0 now. (`lowered_skies` also lists three street sectors a quarter
of a body low; they were there before any of this and hide nothing.)

## The thing nobody predicted

Round 2 had the roofs and still had the avenue portal. A blind reviewer
reported "a thin dark pole" in the sky in five frames. It was the porch's
ceiling, painted from the top of the screen down beside the door.

Cause, isolated by editing copies of the map (the pole survives flattening
the door bay's sky, raising it to the street's, and raising it above the
street's; it goes when the porch itself is opened to the sky): Build keeps
**one open span per screen column**. Once a wall is low enough to see over,
the columns above it stay open, and any sector the renderer reaches in the
meantime paints into them. The porch lay under the roof.

With the portal standing open it is not a pole:

| frame | ceiling pixels in the sky, door open |
|---|---|
| avenue_front_up | 23,262 |
| avenue_south_up | 18,939 |
| tower_foot | 18,074 |

This is the engine's sector-over-sector rule, and `bloodmap/layers.py`
already states it ("the space you enter the ground floor from must not also
open into the storey above it through the same facade"). Its checker did not
fire, because a roof is not a storey you enter. `skyline.leaks_under_roofs`
now does, on the source layout, and the build refuses a map that has one.

So the doors moved. The tower is the one part of the church nothing is seen
over: its walls are one-sided to their own raised sky and close every column
they cover, and the belfry lies wholly inside its plan.

| doors | leak, standard cameras |
|---|---|
| both shut | 0 |
| outer open | 0 |
| both open | 808 to 14,475 px in six frames |

The last row is why both leaves close themselves after three seconds
(`doors.z_motion_door(close_after=30)`: 202 campaign doors do this and 30 is
their commonest wait; `SetSectorState` needs `reTriggerA` set as well as the
wait, triggers.cpp:147). A player cannot open the second, get back outside
and look in three seconds. It is a mitigation, not a proof.

## The predictions, scored

Written in `hypothesis.json` before the first edit.

| | prediction | result |
|---|---|---|
| R1 | the tower paints 2000+ px in `yard_to_tower` (was 0) | held: 4,247 (and 6,284 in `yard_out_east_up`) |
| R2 | sky share falls 0.10 in `yard_out_south` and `avenue_over_wall` | **failed**: +0.042 and -0.029. The blocks do appear, but the wall is also lower than the lid was, which adds sky. The measure was wrong for the claim |
| R3 | sky share falls 0.03 in `avenue_over_church`, `row_over_church` | held: -0.046, -0.058 |
| R4 | nave, chancel, aisle, narthex frames pixel-identical | **failed as written**: 3,082 to 131,822 px changed. Removing two doors and adding a third changed the rooms' bounced light. Round 1, before the doors moved, was 0 to 2 px |
| R5 | lowered skies fall to at most 3 | held: 0 of a body or more (3 pre-existing, a quarter body) |
| R6 | no new rule error; layers accept the stack; deterministic | held; rule report is 13 errors, 5 warnings (one fewer than baseline) |
| R7 | avenue sky share within 0.10 of the morning's | held: 0.350 to 0.302 |

Not predicted at all: the leak; two headstones the auto-dresser stood on the
roof (it took the roof for a room); and every interior camera rendering the
rooftop, because `look.sector_at` returned the first sector in plan. All
three are fixed at their source.

## What a stranger saw

| | this morning's result | roofs, portal still in the face | now |
|---|---|---|---|
| the church | church (likely) | church (likely) | church nave plus bell tower (likely) |
| the cemetery | cemetery wall (guess) | graveyard (certain) | cemetery (certain) |
| the spire, far | church steeple (certain) | spire (certain) | best frame; church (likely) |
| one building? | "steeple does not match the tower up close" | "two or three separate things" | "does not read as one coherent building" |
| render faults named | none | a pole in five frames | none |
| the way in | church door (likely) | "nothing marks a main entrance" | "a closet door, not a church portal" |

The gain is the yard and the absence of faults. The cost is the entrance:
moving it into the tower's foot made the church correct and its door meaner.
The reviewer also reads the roof as "a flat box" from the avenue (it is the
nave's long side, where a pitched roof shows only its eaves) and a gable from
the ends, and takes that for inconsistency.

## Does it run

`python -m bloodmap oracle-nblood`: **pass** (loads, reaches the game loop,
stays healthy). That is a load test, not play. `route/static-route.json`:
the map holds a chain from the spawn to every church room through the two
tower doors; `a_player_was_moved: false`. The owner has it as
`reference/blood/GRAVESEND.MAP`.

Unknown: whether NBlood's GL renderer shows the two-doors-open leak the way
the observer's software renderer does. The observer is JFBuild's classic
renderer; NBlood's default is not.

## Not done

- The church has no front. A portal that is grand and legal needs a west
  front that is itself not seen over: a full-height gabled frontispiece block
  with the door in it, the way the tower carries this one.
- The tower from its own foot is still a plain shaft.
- The loop through the church into the yard is gone with the cemetery door.
  A side porch that is its own small tall block would restore it.
- The lancets are sprites on a wall that is now a step; nothing checks they
  stay under the eaves if the eaves move.
- Every other block in the city, which `skyline.roof` now fits better than
  the apron did: a tenement has no door problem if its roof is not seen over.
