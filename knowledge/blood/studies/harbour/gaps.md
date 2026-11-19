# Harbour: what to change in ours, in order

From the study in `notes.md`. Ordered by how far each moves a blind
reviewer's "is this a harbour?" read. Ours: quay boardwalk s207 (floor
8,192), sea s208/s209/s212 (floor 10,240), horizon ring s210/s213/s215,
headlands s216-s219, jetty s220-s228, ship s229-s233; code in
`projects/blood-city/level/l3_market.py`.

1. **Make the sea water, not grass.**
   Recipe: every sea band floor tile 2490, `floor_pal` 10, `floor_stat` 4,
   shades 38 / 41 / 44 from the quay outwards (replace `SEA_BANDS` shades
   26/29/32); XSECTOR `pan_floor` 1, `pan_velocity` 10, `pan_angle` 900,
   `depth` 0 (not 7), `visibility` 0. Keep 1120 ("green dirty water") out
   of the open sea entirely.
   Exemplar: DWE3M4 s636 (sh 38), s528 (41), s527/s856 (44); campaign
   E2M1 s125 (2448, pal 10, sh 34, pan 10/1024), E2M9 s49.
   Tell in a frame: `horizon_south` shows a dark blue-violet surface with
   long pale streaks, no green, darker than the boardwalk; two frames a
   moment apart differ (panning). Tell the owner 2490 is used as water.

2. **Drop the sea 1.75 bodies below the quay, behind a kerb.**
   Recipe: sea floor = boardwalk floor + 29,696 z (8,192 -> 37,888); along
   the boardwalk's seaward edge a strip 256 wide raised 6,144 z (0.36
   body) over the boardwalk, floor 21 (dark vertical planks), faces 177
   (wooden wall), shade 31; the bulkhead face from kerb top to water in
   dark planks (20), shade 31. Horizon ring floor = ceiling = the new sea
   floor. The slip/wading idea (SLIP_DROP 2,048) does not apply to the sea.
   Exemplar: DWE3M4 s519, s406 (kerb), s548 (boardwalk -8,192) over s636
   (sea 21,504).
   Tell: from the boardwalk the water is seen below an edge, its far line
   meeting the sky lower in the frame; from `quay_from_sea` a dark plank
   wall a body and three quarters tall stands between water and town.

3. **Rebuild the rock as facets, not two boxes.**
   Recipe: each headland 6-10 sectors, each an irregular polygon of 6-8
   corners with no right angles and edges 4,000-10,000 long; each its own
   sloped floor (heinum from -1,280 to +1,280, mixed signs) and its own
   floor shade between 25 and 37 (neighbours differ by at least 3); tops
   2.7 to 6 bodies over the sea, highest at the land and falling toward the
   water; floor 458 (rock) or 273 (rock/cliff), faces 458. Same for the
   skerry (3-4 facets).
   Exemplar: DWE3M5 s46-s60 (e.g. s50: 8 corners, heinum -512, shade 37;
   s47: heinum 1,024, shade 29); DWE2M6 s931-s940.
   Tell: in `east_end` / `west_end` the rock's top edge is a broken line
   against the sky and adjacent faces read in different greys.

4. **Close the quay's ends: no wall end against open sky.**
   Recipe: at each end the rock of gap 3 wraps round the flank building's
   corner and runs on behind it and outwards along the sea's side as a ring
   of 3-5 more facets reaching the horizon ring (DWE2M6's ring is
   continuous round its cove); the building's flank stops INSIDE the rock,
   never at its edge. Alternatively at one end a beach run-out: the
   boardwalk stops, a dirt slope (433 "dirt", shade 35) descends to sea
   level over ~4,000 and meets the water flush, with a few small debris
   sprites, under the bulkhead.
   Exemplar: DWE2M6 s931-s940 (ring), DWE3M4 s352 (beach, dirt at sea
   level, 54 sprites).
   Tell: no frame along the quay shows a flat building end or a flat rock
   end with sky on both sides of it.

5. **Give the ship a ship's deck.**
   Recipe (after DWE3M4 s625 and E2M1): hull about 13,000 by 4,096 with a
   pointed bow of 2-3 sloped sectors; deck 2.4 bodies over the (new) water,
   0.5-0.7 body over the jetty; a bulwark 512 wide all round, 0.6 body over
   the deck; a cabin of tile 49 (red-grey planks with iron bands) with a
   door on the jetty side; two or three crates as 1,024 cube sectors faced
   452 ("smaller crate"); a mast as a 512 x 512 hole in the deck sector,
   walls tile 20, rising to the sky ceiling; the black flag 3558 as a wall
   sprite on the mast (repeats 64x64, shade 8, about 2.3 bodies over the
   deck, cstat wall-aligned); a bowsprit beam leaning out over the water
   ahead of the bow.
   Exemplar: DWE3M4 s625/s628; E2M1 s247, s234, sprites 156/157 (flag);
   DWE2M6 s632 walls 4587-4590 (hole mast).
   Tell: `ship_from_quay` shows a pointed hull standing out of the water
   with things on its deck, a mast to the top of the frame and a flag;
   no reviewer says "wooden rectangle".

6. **A jetty on piles, open underneath.**
   Recipe: the jetty deck at quay level over the sea (so water shows
   below it from the side); square piles 512 x 512, walls tile 20, at 2,560
   pitch down both long sides just outside the deck, rising 0.36 body over
   the deck; a lantern sprite 693 (face, repeats 40x40, shade -20) on top
   of each pile; edge beams as wall sprites 68 (repeats 128x64, cstat 465)
   along both sides at deck height. Remove the upright planks that now read
   as a fence.
   Exemplar: DWE2M6 s627, piles s621-s626, sprites 776-800.
   Tell: `piles` and `jetty_end` show posts in the water with lights on
   them and dark water between them under the deck.

7. **Lamps along the kerb.**
   Recipe: sprite 640 (lamp post), face-aligned, repeats 64x64, on the
   boardwalk floor 256 inside the kerb, every 4,600-7,700 units along the
   quay; each with a light source if the city's lighting needs one.
   Exemplar: DWE3M4 sprites 611, 1250, 1254, 1255 (x -21,760).
   Tell: `horizon_east` shows a row of lamp posts receding along the edge.

8. **String lights between tall posts over the boardwalk.**
   Recipe: pairs of sprite 624 at one point, repeats 8x8 and 4x4, shade
   -30, palettes cycling 0 / 7 / 8 / 10, one pair every 256 along the line,
   z following a sag from about 5 bodies at the posts to 2.2 at mid-span.
   Posts: tall dark timber (how DWE3M4 builds them is still open; a 512 x
   512 hole column like the mast is the safe form).
   Exemplar: DWE3M4 sprites 285-318, 681-728.
   Tell: a sagging line of coloured dots across the sky over the walk in
   `ship_from_quay` and `horizon_east`.

9. **Make the sea darker than the quay, and the quay than the town.**
   Recipe: boardwalk shade 21-31 (DWE3M4 s548: 21, s547: 31), sea 38-44
   (gap 1), rock 25-37 (gap 3), so the brightness falls from town to sea.
   Exemplar: DWE3M4 s547/s548/s636.
   Tell: in `quay_from_sea` the town is the brightest band, the water the
   darkest.

10. **Something at sea besides the skerry (optional).**
    Recipe: a second, smaller moored hull or a row of 3-4 free-standing
    piles (gap 6's pile, no deck) in the near band, out of reach.
    Exemplar: DWE2M6 s621-s626 (piles alone), DWE3M5 s65 (a boat moored
    out in the bay).
    Tell: `horizon_south` has a middle-distance object between the quay
    and the horizon.
