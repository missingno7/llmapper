# Station, round 5: the passenger and player read

## 1. Passenger walk
- **Find it (view_09).** The doorway (DOOR, 3.4 m) is a dark slot with no frame, canopy or lamp you can see. STATION is lettered on the neighbouring facade, over that building's windows, so it reads as a shop or hotel called "Station". The clock is on the building to the west.
- **Ticket (view_08).** This works. A barred window 1.7 m wide with a 0.85 m sill, a TICKETS board and a clerk behind the bars. The side door is open.
- **Wait (view_04).** The hall is 17 x 10 m with a 5.2 m ceiling. It has columns, iron gates and benches facing the platform. The benches are solid brown blocks with no legs and read as crates. There is a clock and an arrivals board, but no departures board and no timetable.
- **Platform and train (view_01, view_04).** The platform is 3.4 m deep. The carriage beside it reads as a wall with a stripe: a 17.8 m grey slab with a green band, only two windows a side, one door, and no roofline, ends or wheels visible from platform height. Behind the glass you still see brown panelling (the window sectors wear PANELLING 105). The engine (view_07) now does read as one: wheels, horned smokebox, chimney and smoke.
- **Board.** Only after the lever. Inside (view_05) is the best room in the station: carpet, curtains, chairs, a table, an axe zombie.
- **Where does it go?** Only "TO THE QUAY" in small letters on the track wall, cut off in view_07. The tunnel is a black void behind bars (view_03).

## 2. Four things that would do most, in order
1. A coach that reads as a coach: compartment doors and windows every 2 m or so, a roof edge, buffers and a gap where it couples to the engine.
2. A frontage of its own: a framed doorway with a canopy, and GRAVESEND STATION over that doorway, not on the neighbour.
3. A station nameboard on the platform and a departures board ("Boat train to the Quay", up trains), so the line has places to go.
4. Harbour traffic on the platform: a porter's barrow, fish boxes and nets, a water column for the engine.

## 3. Sizes
- The platform is 1.5 m above the rail (real: about 0.9 m).
- The carriage door is 1.7 m wide (a real door is about 0.7 m), and its windows are 2.55 m wide but only two a side on 17.8 m.
- The track bed is 13.6 m for two tracks (about 8 m would do), so it is an empty trench.
- The chimney top is 5.1 m above the rail (real: about 4 m).
- The benches are 0.64 m deep with solid fronts.
- The hall, the office (3 x 5.1 m) and the car's inside (2.55 m wide, 2.55 m clear) are right.

## 4. Player
The chain is: pull the lever on the column, the door rises and stays open, fight the guard and the porter, take the prize at the east end.
- **No search.** The lever is beside the door, so there is nothing to look for. The clerk and the office have no part in the chain. The module docstring still says the lever is in the office, which the code no longer does.
- **No end.** The carriage is a cul-de-sac, and the prize sits beside the guard. The ramp down to the track leads only to bars. You cannot enter the engine, and nothing moves but the door.
- **Cheap improvement A.** Put the lever inside the office at the barred window. A line from the window (8192, -12544) to the carriage door (about 15360, -14720) passes through open bays 2 and 3. So you fight the clerk, pull the lever, and watch the door rise through the bars.
- **Cheap improvement B.** Make the prize a key the level needs, or a switch in the engine's cab that raises the tunnel bars. Then the visit has an outcome, and the "TO THE QUAY" sign means something.

## 5. This town or generic
Mostly generic: Build brick, a red sky, E1M2's gates and E1M3's lounge car. The harbour shows only as one illegible sign, sacks and barrels, and the Pandemonium bill. There is nothing of the sea.

## 6. Score
3 out of 5. The office and the car's inside are memorable, and the engine is now legible. The coach's outside and the street door are not.

## 7. Blocking defects
- From the platform and the hall the carriage reads as a striped wall, not a train: one slab, two windows a side, one door, and no roof, ends or wheels in view (view_01, view_04).
- The carriage windows still show brown panelling behind the glass, because the window sectors wear PANELLING 105. This is the round-4 defect and it persists.
- STATION is lettered on the neighbouring building, and the doorway is an unmarked, unframed slot (view_09).
