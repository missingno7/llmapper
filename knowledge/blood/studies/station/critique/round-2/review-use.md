# Station, round 2: reader "use"

Units: 1,024 xy = 1.7 m; 16,960 z = one body = 1.76 m.

## 1. Passenger
- **Find it (v9).** The door is a 3.4 m x 3.3 m hole (DOOR, 2 PU, 32,768 z) in a theatre-row facade, with no frame, leaf, canopy or clock. The green STATION letters sit 2.2 bodies up and are cropped at the top of the frame. They read like a shop sign. Nothing says "station" at eye level.
- **Approach.** PASSAGE (5.1 x 6.8 m) and RAMP (3.4 x 6.8 m) are 13.6 m of bare corridor.
- **Buy (v5, v8).** This is the best thing in the level: a barred window under a TICKETS board, a clerk behind it, 0.85 m sill. But OFFICE_DOOR stands open beside it (1.3 m), so the bars guard nothing.
- **Wait (v4, v5).** A 17 x 10 m HALL holds only two benches. Each is 3.4 x 1.06 m, seat 0.64 m, back 1.17 m, and reads as a crate. There is no waiting room and no stove.
- **Find the platform.** There is one platform, unnamed. The GRAVESEND board hangs in the hall and is illegible from the track (v3). The arrivals board (431) names nowhere.
- **Board (v1, v4).** Yes, through the bay at 14,848-15,872.
- **Where does it go?** Nowhere. "TO THE QUAY" is on the far wall, and the tunnel is barred.

## 2. Missing, in order
1. A frontage of its own: arched entrance, canopy, clock, the name on a fascia.
2. A platform nameboard and destinations: "Platform 1, for the Quay", a timetable.
3. Luggage and parcels: trolley, trunks, fish crates and mailbags from the harbour, a guard's van.
4. Railway kit at the engine end: a signal post, a water crane, coal.

## 3. Sizes
- **Carriage** (CAR). 17.9 m long, 5.1 m wide outside, 4.25 m inside, 3.4 m clear. A real one is about 2.8 m wide and 2.3 m clear. Its door is 1.7 m wide and 3.0 m high (real: 0.7 x 1.9). Two windows a side, 2.55 m each, on an 18 m body. It has no bogies, so it reads as a green building (v2).
- **Locomotive.** BOILER is 6 m x 4.25 m x 4.25 m. CAB is 2.55 m long and **5.5 m tall**, 1.2 m above the boiler. The engine is 8.6 m long, half its carriage. It has no chimney, smokebox, dome or tender, and v7 shows another striped box.
- **Platform.** It stands 1.5 m above the rail (PLATFORM_DROP; real ~0.9 m). It is a 3.4 m corridor pinched between columns and car (v1).
- **Empty space.** The far track is 13.6 m of bed with an empty rail. The 47 m of track holds only a buffer. The carriage has two tables in 18 m.

## 4. Player
The intended run is street → hall (cultist) → office (axe-zombie clerk, lever, loot) → carriage (guard, porter, prize) → walk back. It has a beginning and no end: the platform ramp leads onto the track, which ends at a buffer and a barred tunnel.

What breaks it:
- The lever is about 22 m and two turns from the door it opens, and nothing visible happens when you pull it.
- If open_time 8 means seconds or less, the door may shut before the player arrives. I could not verify this.
- The open office door makes the "behind bars" idea pointless.

Two cheap improvements:
- **(a)** Put the grille at TUNNEL[0] on channel 264 too, or behind a second lever in the cab. The line then leads to the quay, and the station becomes a passage rather than a cul-de-sac.
- **(b)** Lock OFFICE_DOOR and put a visible cue by the lever: a signal arm on the platform, or the carriage door seen through the booking window. Make open_time long, or make the door stay open.

## 5. Town
It is generic. The ties to Gravesend are one Pandemonium Show bill (225) and the unseen "TO THE QUAY". To tie it to the town, show the harbour: fish boxes, nets and a steamer-company poster. Make it a boat-train line, and use the city's own facade brick and fog.

## 6. Score: 2/5
The ticket window is memorable. The train is two boxes.

## 7. Blocking
- The locomotive does not read as one: a box in carriage livery, a 5.5 m cab, no chimney or tender.
- The carriage is 5.1 m wide with a 1.7 m x 3.0 m door and no bogies, so it reads as a green building.
- The street entrance is an unframed slot in the theatre facade, with STATION above eye line.
- There is no end: the tunnel is barred and the player retraces the whole route.
- The lever gives no visible result 22 m from its door, and open_time 8 may shut the door first.
