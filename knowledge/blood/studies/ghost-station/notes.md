# Study of the Phantom Terminus

The carriage, the light and the drowned end were rebuilt after the owner's
ride; what they are made of now is in the study `moving-bodies`, in
`level/carriage.py` and in the design's "As rebuilt". What is said below of a
single 616 slab, painted pools, green floor cuts and 1717 is history.

## What I want to build

The boarded-up end of Gravesend's old line. The booking hall frames a lighted
car full of dead passengers. Taking the reward or pushing RUN starts its last run, past the staff who
sealed it in and on to the brick end of the line.

## Where Blood built it

The generated [measurements](study.json) cover Death Wish, the campaign and
four community maps. DWE3M2 s481 and s194 supply the tiled hall and gate
rhythm. S246 is its rusted edge and lamp run. S351 and s362 supply the dark
ceiling ribs and strips of light. SSR3 s5 and s46 looking at s45 give the
close carriage window and the drowned approach. GHOSTTWN s767/s709 give
the stone bore and ties. EU13 s281 gives the barred lantern niche, and
666UNDER s252 gives the watchers spaced along the track. These maps were
checked against `knowledge/blood/duke-conversions.json`.

## What makes it read as that

The pale banded wall sets off rust, iron and dark timber. A train is visible
through a gate before the player reaches its platform. Inside the car, the
windows light individual seats. In the bore, the rails and the occasional
wall niche are the things the eye can follow. At the drowned end one light
in the nose catches the surface of the water.

## Sizes

DWE3M2 s481 measures 5.4 by 25.4 m at 3.7 m clear. Its s246 edge is 1.7
by 19.3 m. The s351 and s362 runs are 11.7 and 12.2 m long. SSR3 s5 is
6.5 by 7.8 m at 3.5 m clear. The Gravesend platform keeps its floor at
118784 with 32768 clear. The carriage is 8192 by 3072 Build units. A
768-unit lane on either side leaves twice a standing player's width, and
the low vault shares the carriage's ceiling.

## What I will transcribe

- DWE3M2 s481 floor 374 and wall 3068's banded 369, s246 wall 1516's
  rusted 386, sprite 188's flat round 795 and sprite 258's folding gate
  1060. Its s481 sprites 196/197 pair the old bills.
- DWE3M2 sprite 208 triggers on pickup and sets the sequence in motion.
  Its s247/wall 1540 move marked walls, type 614. Gravesend needs the
  whole loop to move with grounded riders. Its Stockyard trolley supplies
  type 616, Drag, relative flooring, and the carrying flag for fittings.
- DWE3M2 s351 wall 2175 supplies repeated rib faces. E1M2 s272 supplies
  the platform-to-track relationship. Gravesend Station supplies the shared rail finish and split carriage skin.
  E1M3 wall 1829 and sprites 409/418 supply green livery 1665, sign 1667
  and the wheels. E1M2 sprite 65 carries the 666 fleet numeral. The
  destination over the boarding door is lettered on the carried steel
  fascia. The fixed station nameboards use the campaign's 1667 art.
- E1M3 sprite 409 supplies the green Phantom sign. E1M3 sprite 962
  supplies Caleb's line at the brick end. E1M3 sprite 966 supplies the
  spawn record schema, with the Phantasm as its dude type. E1M7 sprite
  216 and DWE3M2 sprite 172 supply the quake record schema. E1M2 sprites
  154 and 556 supply the whistle and rolling motor. DWE3M2 sprite 237
  supplies the finishing sound. E3M3 s13 has the abrupt shade flicker.
- E1M4 s210 supplies the surface of the drowned siding. The original
  Tommy gun starts the ride and the shadow cloak waits at the brick stop.

## Platform and coach finish

- DWE3M2 sprite 196 hangs the repeated bill, sprite 182 supplies the torn
  one, and wall 1396 gives the step its warning stripe. The stone chips
  beside the gang follow DWE2M4 sprite 404. The little shrine uses E1M5
  sprite 1's candle. DWE3M2 wall 3068's dado remains the pale wall finish,
  with separately shaded wall panels by the ticket grille and clock.
  The waiting-room luggage uses DWE1M7 sprites 420/423's chest art,
  with the paper from E1M2 sprite 137. The broken clock uses DWE3M1
  sprite 989. Its beam has the hanging corpse from E3M1 sprite 25,
  beside a loose lamp from E1M4 sprite 24.
- E1M2 s3 sprites 95, 98 and 101 supply the seated and slumped passengers.
  THESLUMS sprite 771 uses the seated pose on a smaller scale.
  Keep every drawn body and the prize at the carried seat-top height.
  E1M2 sprite 212 supplies the gore on the insides of two panes. SSR3 s5
  gives the low sill, with a clear opening above. TEDE1M5 sprite 694
  supplies the broken framed glass art, used here as an equilevel mask.
- Compare all 15 Blood PLUs on the finished interior. PLU 4 gives green
  enamel and mould. Keep the passengers on palette 0. The fixed pool
  centers start at shade 2, the rings at 12, and the hall and platform
  between them at 50–52. The booking gate and four windows have green
  floor cuts at shade 4. The track's four green patches are flat sprites
  so the travelling loop remains its only hole. Departure removes them
  with native type 405. Far-berth cuts use the car's own OFF stop and
  close when it reaches ON again.
- The carried RUN lever uses type 20 and the 1070 art from E1M2 sprite 22.
  A refusal to pick up a full weapon leaves the handle available. The
  platform's gate throat sends the distant 708 whistle and kills the edge
  lamp on first entry. The decoupled coach Enter sends its state to the boarding
  latch. A two-tenth-second pulse cuts the four carried lamps using
  E6M4 sprite 156's type 456 visibility operation. The first departure
  still sets the blackout and Phantasm latch, and the OFF stop supplies
  the Caleb line.
- SSR3 s46 toward s45 frames the distant cab. E1M4 s100 wall 705 gives
  the boiler its riveted cladding and E1M2 sprite 20 gives the cab its
  round dead portholes. The flood's lit cut uses its panned water texture.
- The station drone and flooded end use the campaign envelopes from
  [ambient sounds](../ambient-sounds/notes.md). Check TEDE1M5, DWE2M4
  SSR3 and THESLUMS against the conversion ledger along with the original
  seeds. None of these exemplars is in its conversion list.

## What I will not do, and why

The car has a permanent side opening and a continuous walk beside its
whole 11264-unit travel. The gallery steps climb 3072 units to the old
platform. A fixed call button at each end brings the car to the platform.
The warning stripe, crown and candle shrine keep the platform legible
as the light leaves. The pump hatch and seventh secret trigger use the
original maintenance route. The ticket pool leaves 512 open plan units
of the trigger's booking floor at the stair mouth.

## What I still do not know

The swept check measures the moving geometry, and static player space
measures the exit. The native lamp pulse and the sound balance need the
owner's play session. The carried benches have sprite tops and aprons
so they travel with the car. The drowned engine has a boxy chimney and
the approach has the proportions of a short flooded siding.
