# Six mechanisms for Gravesend

Start with the Foundry Ward loading shutter and the Settling Hall lift. Both have clear player-facing jobs, readable endpoints, and references that can be checked in a small test room. Follow with the station turnstile and the Aldermack fire doors. Develop the Ghost Station puzzle as an optional secret. Fit the sampling trolley when the stockyard drain is laid out.

The [current city status](../reports/STATUS.md) identifies missing motion in the foundry underpass and at Gravesend Station, and missing machinery at the Aldermack. The [sewer design](sewer-design.md) already gives the Settling Hall two elevations, places the proposed Ghost Station behind a pump-station hatch, and leaves the stockyard drain to be built. The existing tunnel roll-up gate, press belt, and stage curtain establish how players already operate machinery. Tutorial record numbers below are zero-based. [Tutorial catalogue and posed views](../../../knowledge/blood/studies/doors-and-mechanisms/notes.md).

## 1. Foundry Ward double sliding shutter

Put a freight shutter in a short, roofed service recess off the foundry underpass. Build enough depth for a lit loading alcove with a supply pickup. Two leaves with a center seam and recessed tracks make it read as a door for crates. A player should be able to use either leaf and see both retreat. Give the opening fixed jambs that conceal the parked leaves. The existing bloody loading cage serves a different bay nearby.

**Tutorial.** `DOOR-SLIDINGD` sector 3, wall 14 and marker sprites 343/344. One type-614 sector drives both marked vertex sets in opposite directions. Wall Push sends Toggle. [Rest and fired comparison](../../../work/mech/double-slide/pair.json).

**Build.** Draw the open geometry, add the OFF/ON markers and both vertex groups, and declare one circuit with Push on the accessible leaves from both sides. Make the travel just large enough to hide the panels in their pockets. Frame the opening and check the shared loops throughout the sweep. Verify the shut seam, open clearance and repeat operation from a player's approach.

## 2. Settling Hall service lift

Put a small lift at the west quay where the dry edge of the tanks comes closest to the gallery. It looks like equipment for hauling filters and tools between the lower hall and the gallery, and it gives the player a second way back up after descending. Give it a shaft, a work light at each landing and a call control within sight of the deck. Keep the stair available as a walkable route.

**Tutorial.** `MACHINERY-LIFT` sectors 2 and 14, sprite 9 for the remote control. Type 600 changes the floor level under a fixed shaft ceiling. [Rest and fired comparison](../../../work/mech/lift/pair.json).

**Build.** Use `mechanism.lift` with the gallery and quay elevations. The sewer design documents a 45,056-unit gallery drop, so measure the proposed dry landing heights in the built layout before setting endpoints. Place the shaft beside the tanks and away from the channel, manhole landing and Cabal circle. Fit call controls that explicitly recall to their own stop and a rider control, and shield the shaft edges. Verify boarding, headroom at the upper stop and recall from either landing.

## 3. Gravesend Station fare turnstile

Use one of the concourse's iron-fenced bays, between the ticket hall and the platform. A slow-moving four-vane gate makes the connection to the ticket office legible and puts motion where players can watch it before stepping in. Keep the open bay alongside for ordinary circulation and the exit route.

**Tutorial.** `DOOR-ROTATING` sector 4 and axis sprite 4. Type 615 `kSectorRotateMarked`, a central pivot, four carried blades, linear movement and level-start cycling. The city already has turnstile helper code and no rotor in the saved map.

**Build.** Carve a stationary surround and use `mechanism.turnstile_spec` for the moving blades. Use the rail hall's existing grille vocabulary and size the rotor, roof and vanes together. Start it through the named level-start wire. Check a few distinct intermediate angles for wall contact, and check player passage at the chosen speed before expecting anyone to use it.

## 4. Aldermack backstage fire doors

Put paired solid fire doors at the auditorium-to-backstage opening, where a wide threshold makes sense for scenery and stage crews. Use both leaves to signal a working theatre service access. A push from either approach opens them into clear pockets off the travel line. Their opening should reveal the backstage corridor and its work lighting.

**Tutorial.** `DOOR-SWINGINGD` sectors 12 and 30, wall 435 and pivot sprites 206 and 213. Two type-617 solids on one RX, with opposite quarter-turns. [Hall view shut](../../../work/mech/double-swing/near/rest/frames/hall.png) and [hall view open](../../../work/mech/double-swing/near/posed/frames/hall.png).

**Build.** Reserve swing pockets in the backstage layout, author both pivot/leaf assemblies, and wire the accessible faces on both approaches to one Toggle circuit. Set the door to stay open until operated again so crews and the player can pass freely. Verify swing clearance, approach from both rooms, and an open aperture that meets the existing route's width and headroom. Leave the paired curtain-and-light cue to the stage itself.

## 5. Pump-station combination for the Ghost Station hatch

Put three labelled dials on a maintenance panel near the lower pump-station landing, off the conveyor and press route. An old inspection plate nearby records the three settings in the same order as the panel. A correct match gives a local latch sound and exposes the concealed access to the tiled Ghost Station platform. Put the secret count on arrival inside the platform, beyond the hatch.

**Tutorial.** `#SPR22` sprites 0, 3 and 4 → hidden combo sprite 1 → sound sprite 2. Take the match logic and cue from that circuit, then use the side-sliding whole panel in `DOOR-CLOSET` sector 17 as the hatch's motor reference. `#COMREST` sprite 8 is a reference if a staffed reset control is wanted later. [Closet panel comparison](../../../work/mech/closet/pair.json).

**Build.** Start with three non-matching dials and a zero tally. Wire the match/mismatch transitions as in the tutorial, and have the success output send ON once to the hatch and its sound cue. Provide a return path from the secret. Prototype the raw type-22 records with named circuits and test overshooting a match, reaching the answer in any order, and revisiting after success. The existing pose tool cannot prove this logic.

## 6. Stockyard drain sampling trolley

When the stockyard drain is built, put a small hand-operated sampling trolley on a straight rail along a wider chamber at the end of the market spur. Ride it across the channel to an inspection alcove. This gives the stockyard branch a different way to use its water and a reason for rails to cross it. Give both ends a dry boarding ledge and leave the maintenance walk continuous.

**Tutorial.** `#2WAYCAR` sector 1, marker sprites 0 and 1. The type-616 sector translates with `drag`, allowing the moving floor to carry occupants. Use explicit end controls in Gravesend so players have time to board before departure.

**Build.** Reserve one straight swept envelope during branch layout. Build a rigid slide-sector deck and keep its wheels and railings aligned to its travel. Use explicit On and Off commands for destination stops, with a call control on each ledge and a departure control on the deck. Keep the highest water and adjacent geometry clear of the deck and player. Check docking, calling from either end, crossing on the deck and falling safely into the channel. Save the multi-leg type-612 train patterns for a location with a genuine reason to turn.

## Acceptance for the first prototypes

Use the ordinary city aperture and circuit passes, then read back the built records and the moving walls, sprite edges and floor heights. Check swept geometry and obtain matched viewpoints from the side a player uses. For the lift, trolley, turnstile and combination, exercise the intermediate states in a runtime check or the owner's walk. The current static reader's completed route is the baseline for the station and backstage changes.
