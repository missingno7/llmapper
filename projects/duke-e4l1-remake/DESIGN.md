# Quarry pumping works: design and first editing pass

## Accepted direction and evidence limits

The owner chose a quarry/pumping works secretly used by the Cabal. The
original Duke environment is a Mission Impossible facility **at night in
a lightning storm**. Preserve infiltration, silhouettes, practical work
lights, exposed rock and the sense of a large guarded installation.

The working Blood MAP is the live project. Broad geometry and encounter
opportunities are useful starting material. Each room gets a reason to
exist, a material hierarchy and a gameplay role before it is dressed.

Static Duke reference views preserve authored geometry, art and palette,
but do not run weather, lighting, cameras or mechanisms. They also show
multiplayer player-start sprites that the single-player game hides.
Our available Duke ART lacks floor tiles 5065/5068, so their black rendered
appearance is not evidence that the original ground was black. The Blood
gravel choice follows the approved quarry fiction and Blood precedent.
Do not copy apparent guards or darkness from these limitations.

## Blood references inspected

All references were resolved through `bloodmap.corpus` and looked at with
the XMapEdit observer. What they show of Blood is on the shelf:
`knowledge/blood/studies/works-yard/notes.md`.

| Reference | What was observed | What this project takes from it |
| --- | --- | --- |
| E1M5:392, Hallowed Grounds | Dark cloud sky, dark ground and heavy wall silhouettes; triggered outdoor shade waves. Sector 392 has amplitude -17, wave 8, frequency 5, a 2-second active interval and a return. | A dark resting exterior, a coordinated brief lightning response and enough silhouette contrast to navigate. |
| E1M5 sprites 86, 88 and the matching sound generators | Type 700 repeats with a random timing range; the same channel reaches the lighting and type-708 generators using sound 255. | Native weather clock, outdoor lighting and distant lightning strike sound, with declared wiring. |
| E1M4:114, Dark Carnival industrial yard | Rough stone, earth, aged metal, fixtures and strong local light contrasts. | A restrained outdoor palette and practical industrial cues. Fire and carnival decoration are specific to that place and were not copied. |
| E1M4:331, exterior railway/factory edge | Architecture, work structures and supports make the yard read as used space. | Preserve worksite circulation and give fittings a physical purpose; avoid dressing a yard with unrelated props. |
| E3M5:2, Spare Parts | Riveted metal construction and a clearly framed industrial door; slab floor distinct from the door and overhead frame. | Separate the service gate, frame, facade and ground by role. |

Owner tile names outrank our image interpretations. Catalog and context
queries were made before selecting the first-pass materials and fixtures.
The reference notes above are observations and transcribed native fields;
the proposed pumping-works uses below are design interpretations.

## Area-by-area work order

`areas.json` covers every native sector. Fixed quarry and support groups
were selected explicitly. Remaining sectors are provisionally attached to
reviewed anchor rooms using portal distance. These groups include doors,
small fittings and support cells, so their sector counts are not room
counts. Refine boundaries at each new editing pass.

| Area and anchor sectors | Original reading | Current Blood problem | Blood interpretation and next work |
| --- | --- | --- | --- |
| Quarry, 453 and its ledges | Stormy rock approach and facility entrance | Marble paving, dressed-stone geology, missing weather and weak entrance cues | First pass applied: quarry geology, gravel, weathered masonry, metal service gate, work lamps, loose rock and native storm circuit. Owner review pending. |
| Administration, 482 / 486 | Carpeted facility corridors and reception | Leaf-pattern floor, ornate tomb-like columns, conflicting ceiling grids | Intake desk and foreman's offices; work records, boards, plain industrial wall construction and clear doors. Next visual area. |
| Security, 496 / 464 / 468 | Elevated office/control rooms with access readers and switches | Switch functions are unclear and the room has no clear operational purpose | Pump scheduling, secured records and Cabal administration. Trace each button before dressing its panel. |
| Washhouse, 152 with stalls 58/59 | Source toilet 569 and wall-urinal 571 sprites establish the actual bathroom | Fixtures omitted; room incorrectly made into a rotor | Workers' facilities with grimy tile, metal partitions and stone plumbing fixtures. Room 389's earlier bathroom label was wrong. |
| Process/control hall, 31 / 543 / 6 | Large hall with equipment islands and doors | Decorative floor pattern and empty islands | Pump controls, valves and instrument benches; preserve the islands' cover and circulation value. |
| Inner service reception, 528 | Wide service entrance/guard room | Blue decorative paving and abrupt stone/metal changes | Maintenance intake and stores desk with tool storage and work lights. |
| Pump lifts, 344 / 89 | Lift lobbies and raised service circulation | Repeated occult button textures, missing functional rails and ambiguous lifts | Maintenance lifts and inspection catwalks. Check stops, riding objects and approach controls. |
| Treatment/machinery, 336 / 256 | Industrial utilities, vents and hazardous barrels | Red louvres stand in for almost everything mechanical | Settling/sluice machinery with stained iron, wet masonry and distinct hazard boundaries. |
| Adit, 252 | Rock passage and narrow crossing with combat/rewards | Brick cave end and unrelated arch materials | Excavated service adit above a wet channel, with plausible shoring and a supported crossing. |
| Deep works, 293 / 316 / 311 | Deep facility and explosive end sequence | The route to the converted exit is unproven | Trace the original sequence before choosing a Blood shutdown/escape equivalent. Gameplay priority. |
| Fissure/cache, 270 | Hidden burning rock space with supplies | Its focal fire was lost | A hot fissure or illicit cult cache; soot, heat source and a purposeful reward. |

## Camera sets and mirror support

The owner identified the weather-forecast set as camera-only and disposable.
Source camera sprite 1034 in sector 536 uses lotag 9019; viewscreen sprite
1059 in sector 545 uses hitag 9019. The disconnected component contains
sectors **536-542**, including WOMAN (4874) and WEATHERWARN-family scenery
in 541. Sector **535** is a separate camera/joke set with a camera using
9014. These eight sectors are excluded from playable-room classification.
The internal SE7/SE23 pair 9017 remains inside that component; no exterior
SE7 targets it. Physical removal is queued as a separate, reviewed pass
because deletion renumbers sectors, walls, sprites and marker references.
Nothing has been secretly connected to it or made into a gameplay room.

The huge room **57** is mirror support. Source walls **277 / 570** connect
it with sector **117** and use Duke mirror over-tile 560. The converted
mask needs a later Blood-native repair or deliberate replacement. Retain
the support geometry until that decision is made. Its empty view is not
evidence of an unfinished playable hall.

## First area: rationale and actual changes

The quarry's interesting features are the rock enclosure, elevated ledges,
central outcrop, narrow entrance and side approach. They support an exposed
infiltration opening and remain geometrically intact.

The first reviewed patch changed the connected 19-sector exposed quarry
and its threshold. Gravel replaced the chequered ground. Cliff and outcrop
faces became streaked grey rock; raised rough surfaces use coarse stone.
The facility facade uses weathered masonry, with a metal-lined entrance.
Two recessed work lamps locate the entrance; two small loose-rock sprites
sit at outcrop edges and do not block the route.

Looking at that result exposed two further problems. Blood sky tile 3678
is a **16-panel panorama**, not a single texture: its first tile alone
produced broken bands. A second patch adopted E1M5's sky bits/offsets and
used the same cloud panorama on playable exterior sky surfaces. The
initial plain metal gate still read as a flat wall. A third patch gave its
visible leaves owner-named metal-door tile 495 at the native texture scale.
The closed and open geometry, Push/Wallpush controls and return timing
were preserved.

Evidence:

- `evidence/pass-01/before/frames`: the untouched baseline, five fixed poses.
- `evidence/pass-03/after/frames`: the current resting exterior, same poses.
- `evidence/pass-03/flash/frames`: current exterior posed at lightning peak.
- `evidence/pass-03/with-actors/frames`: current saved scene with population.
- `evidence/service-gate-open/frames`: a posed open gate from its approach.
- `evidence/comparison.png`: baseline, current rest and current flash together.

These are observer frames, not a playthrough. Sound, event timing, weather
randomness and actual Use activation still require the owner's in-game
check. No independent blind visual pass is claimed.

## Reusable, context-dependent correspondences

| Source situation | Blood choice in this project | Why / limits |
| --- | --- | --- |
| Cliff and a rock outcrop presented by source tiles 1169 / 782 | Tile 273, owner-named rock/cliff; coarse-stone ledge tops | Keep the same geology across the enclosure and outcrop. A rock wall's replacement is not dressed block masonry merely because the colors match. |
| Exterior approach ground (5068, missing in available Duke ART) | Tile 275 rough coarse stone | Approved quarry interpretation, supported by Blood outdoor/factory usage. This is not an assertion about the unavailable source artwork. |
| Raised rough ground and ledges | Tile 274 rough coarse stone, almost cobblestone | Makes raised rough surfaces distinct from the finer approach gravel. The choice depends on topography and room role. |
| Dark banded facility facade, source 368 | Tile 80 weathered stone, with metal at the entrance | A civil pumping works interpretation. Do not apply this choice to every original banded/metal wall. |
| Practical worksite lamp | Tile 2183 recessed lit metal wall lamp | Used on walls in Blood factories and interiors. Mount against an actual facade, face into the yard and choose its height using drawn extents. |
| Small debris at a geological edge | Tile 806 loose grey rocks | Adds erosion and a reason for scattered debris; use sparingly away from the route. ART offsets matter when seating it. |
| Mechanical door leaf (source 355 / 180-associated faces) | Tile 495 metal door; plain metal jambs | The function needs to read before the player presses Use. Repeated key-emblem tiles such as converted 2534 communicate the wrong function. |
| SE28 / NATURALLIGHTNING weather | Type 700 clock, plain-sector shade waves and type 708 sound 255 | E1M5 provides a native precedent. The original timing and bolt sprites are not reproduced exactly. New wire declared through Circuit; source channel numbers are not copied. |
| WATERDRIP 660 around the original exterior | Potential Blood drip/rain generators, still pending | It is weather/water behavior, not an arbitrary decoration. No bulk replacement of its 53 instances was attempted. |
| Camera / viewscreen | Remove the inaccessible forecast set later; reinterpret useful monitor positions as static plans, gauges or windows | The owner does not want a camera-dependent Blood design. Determine a monitor's gameplay purpose before choosing a substitute. |
| Duke mirror | Blood mirror or deliberate architectural replacement, still pending | Source support room is not a normal room. Inspect Blood's native mirror conventions before changing its geometry. |

## Mechanical status and next work

The storm clock starts from the engine's level-start broadcast. Circuit
allocated a free user channel around existing native wires. The clock's
repeat interval is 80 +/- 20 tenths of a second, about 6-10 seconds; a
repeat sends On to the 19 exposed sectors and a type-708 distant-lightning
sound generator. Each lighting receiver uses wave 8 / amplitude -17 and
returns after two seconds. The sound receiver returns after 1.5 seconds.
Wind ambience uses native ambient sound 16 at a restrained volume. Other
exterior courtyards need their own weather coverage when edited. Rain
particles and an explicit visible bolt have not been added.

`reports/storm-wire-readback.json` confirms the declared sender and every
listener, with no wire faults. The opened service gate has 30720 vertical
clearance against the player profile's 16960 standing height. The posed
open-state frame shows the route into the interior. That verifies encoded
state and presentation, not actual runtime Use behavior.

Open priorities, with no automatic repair invented:

1. **Actor seating:** the current fit reader finds 72 existing actors partly
   below floors. All original actors were retained unchanged in this pass.
   Correct them with ART-aware extents and the host floor, including slopes
   and moving sectors, for faithful saved-map presentation. Blood seats actors
   at spawn; this diagnostic alone does not establish a runtime combat fault.
2. **Exit:** trace the end sequence and the route to sector 311. The inherited
   static progression report does not prove access. Do not add an arbitrary
   exit or connect the deep works just to satisfy a reader.
3. **Administration:** replace the carpet/ornate-column mismatch in 482/486,
   establish desk/storage functions and inspect the first interior gates.
4. **Camera/mirror:** remove forecast-only components with explicit index
   remapping; separately resolve the mirror with native Blood evidence.
5. **Progression controls:** preserve and trace the skull/eye keys and the
   readers in 344/496; review switching, spawns, cracks and explosives area
   by area against the original intent.
6. **Presentation:** refine gravel scale, lamp falloff, seams and worksite
   detail after owner review. The first area is a deliberate initial pass,
   with further dressing and critique still owed.

## Verified scope

`reports/first-pass-readback.json` is tied to the first exterior pass's MAP SHA-256. It
checks geometry, topology, start, all original sprite records and all
pre-existing extended mechanism records against the immutable baseline.
There are zero structural errors, seven added sprites and no new fit
faults on the visible additions. The eight patch-tool tests check backups,
idempotence, manual-edit preservation, conflicts, report recovery, immutable
baseline protection and the sky panorama update. Existing structural
warnings are retained. The full environment's optional Pillow/Shapely
dependencies are unavailable; visual evidence was made with the native
observer and image composition through System.Drawing. No game window or
key injection was used, and Blood City was not edited by this project work.

## Continuation: using City's inspection workflow

`WORKFLOW.md` records the reusable City practices and local commands. The
live map remains authoritative. `places.json` gives the quarry and intake
explicit boundaries; `status.py` measures the current native MAP and marks
evidence by source and pose hashes. Places are looked at with `tools.look` and
handed to blind readers with `tools.critique` (see README.md).

Passes 04/05 are an initial intake material and fitting pass. See
`notes/intake.md`, the shelf study `knowledge/blood/studies/front-office/` and
`experiments/intake-01/` for references, the
pre-change prediction and same-pose evidence. Sectors 148 and the explosive
workbench 390/403/404/405 were deliberately left alone after checking native
geometry and mechanisms. Other adjoining interiors are still unfinished.

The current generated status supersedes the historical first-pass counts.
There are still 546 sectors and 3488 walls, now 345 sprites. Three original
cultist Z values were seated correctly; all their other fields and existing
mechanism extensions were preserved. Saved-map sunk-actor diagnostics fell
from 72 to 69. No new fitting fit faults or structural errors were found.

## Continuation: the briefing tape player

The owner identified the apparent workbench as the original self-destructible
tape player. `notes/briefing.md` records its source trace and native
adaptation. The converted map retained the explosion/collapse receivers but
omitted the tagged door-art Use face and its sending path. Pass 06 adds that
control extension and two hidden native delay relays through Circuit,
preserving receiver channels, trap fuses, geometry and endpoints. Pass 07 fits
the radio-cabinet recording-device art to the retained face.

The current map has 348 sprites. Stationary desk 404 receives a ledger; moving
parts receive materials only. Source and baseline hashes remain unchanged.
Three synthetic mechanism regression tests and native read-back verify the
encoded wires, return-edge delays and retained endpoints. Same-pose rest and
collapsed views are in `evidence/briefing-mechanism/`. Actual Use, timers,
damage and audio still need owner play; the original speech has not been
replaced by an unrelated Blood voice. Generated status lists this explicitly.


## Continuation: converter motion repair and manual boundary

One neighbouring-room fault was reproduced: SE11 door 50 used the spawn direction
instead of the direction reversed by ST23 on activation. Its shared vertices
folded sector 389 loop 3 during opening. Pass 08 fixes that and the other motor
parameters identified by the source audit, without changing saved geometry,
materials, added props or the declared weather/briefing wires. Marker angles
and XSECTOR motor fields are intentional changes; earlier preservation claims
refer to their recorded historical passes.

The owner accepts manual rework when Duke behavior cannot translate cleanly.
The generated `reports/converter-mechanism-audit.md` separates repaired bugs
from explicit manual tasks and approximations. It is not a claim that every
mechanism works: compound door 329, pistons, linked leaves, locks, independent
lights and control/audio choreography still need deliberate decisions.

## Continuation: actual washhouse, passes 09–10

Source fixtures identify sectors 58/59 as toilet stalls, 119 as the urinal
alcove and 152 as their main room. Sector 389 was misidentified in the early
survey; its genuine door-50 repair remains useful, but it is a separate place.
The source also contains SE11 sprite 487 in plain sector 152, hitag 409.
EDuke32 sector.cpp ST23 only arms same-hitag SE11s through an ST23 operator;
none exists for 409. The converter had invented a room-wide Push rotation,
and the room's touchplate then activated it on entry. Pass 09 retires that
generated rotation, preserves the entry signal and keeps real stall door 61
(hitag 408). The same general correction also applies to E1L2 sector 262.

Pass 10 keeps every sector and wall coordinate. It adds a first washhouse
finish: grimy-tile floor 296, tiled walls 297, riveted partitions 2453,
pressed-metal ceiling 215, vent grilles and two practical lights. Missing
Duke fixtures become two stone commodes and two wall urinals built from
native wall/floor sprites. E2M4's toilet sectors 467–469 and room 487 provide
the stone 43, bowl/rim/cistern construction and invisible flush-switch
precedent. Water 2915 replaces its sewage surface. This is an interpretation,
not a geometry transplant; rounded porcelain would require further modeling.

See `notes/washhouse.md` (Blood's precedent: `knowledge/blood/studies/washroom/`), the guarded pass and read-back report.
No actor, pickup, live motor or existing wire is moved by pass 10. Source
mirror support 57 remains excluded; its native mirror repair is still open.
Independent visual review, fixture collision and live flushing/door Use
checks remain pending. Saved observer frames cannot establish those results.
