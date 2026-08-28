# Refinement loop — Gravesend

Owner verdict opening the loop: *"very raw overall, textures don't fit."*
One line per fault. Frames under `reports/looks/<tag>/frames/`.

## Iteration 1 — the surface system (textures)

Looked: pilot set + fresh1 (11 poses, incl. the player's first frame on the
quay and a look-up the avenue). Reference frames captured under identical
settings: E3M1 sectors 3/6/12/17, E3M3 sectors 42/23.

**Found**
- F1 *systemic*: surfaces were named per district and inherited by every
  region in it, so interiors and the sewer wore street facades (arched
  windows underground, visible through the grate) — worst fault.
- F2: Market Slip's facade tile 414 is **wood boarding**, not a facade —
  a contact sheet rendered from Blood's ART settled it; hence the black
  slabs in the player's first frame.
- F3: the avenue's floor changed material down its centerline (district
  seams run along street centres, and floors were per district).
- F4: every building on a street wears one identical tile (no per-building
  variation within a district's set).
- F5: `flicker_lit_sectors` reports 0 animated sectors (campaign: 20.7%) —
  its default tile set does not include our lamp tile 641.
- F6: roadway is E3M1's flagstone (4); E3M1's roadway is cobble with
  flagstone as the *walk*.
- Checked, **not** a fault: our sky (3491) against E3M1 sector 6 — same red
  night cloud. Recorded so it is not re-litigated.

**Fixed**
- F1: `level/materials.py` — surfaces named by role (facade per district,
  interior, service, sewer, masonry, backdrop), each carrying its own
  opening/jamb tile applied through `portal_wall_picnum` (the campaign's
  74% rule). Every id measured: a role-separated census of E3M1/DWE3M1/
  TEDE1M2/E3M3 plus a rendered contact sheet.
- F2: facades are now 400 / 384 / 380 / 393 — four distinct window facades
  from E3M1's own facade census; 414 retired to `HOARDING`.
- F3: one roadway for the whole city; district identity lives in facades.

**Verified** (before/after, same poses): `i1-before` → `i1-after`,
`i1-after2`. Quay: black slabs → multi-storey window facades. Grate: sewer
with arched windows → E3M3's stone-and-rust register. Canteen: facade brick
→ papered walls, coffered ceiling, patterned floor (matches E3M1 sector 12).

**Deferred**: F4, F5, F6 → iteration 2. Sidewalk geometry (E3M1 splits
roadway from walk) — needs new sectors along every facade, costed later.

**Owner note folded in**: tile sheet approved for exteriors and sewers.

## Iteration 2 — facade variety, light pools, props (textures → lighting)

Looked: fresh2 + fresh4 (10 new poses: west lane, cemetery gate, dock,
plaza, forecourt, wet sewer trunk).

**Found**
- F4 (carried): one tile per district — measured against E3M1, which runs
  **13 distinct facade tiles over its street network, none above 22%**.
- F7: the plaza monument wore a storeyed window facade and read as a tower.
- F8: lighting is flat citywide — one sector per district means shade
  cannot vary along a street (E3M1 splits its streets into 20 sectors).
- F9: `flicker_lit_sectors` animated 0% against a campaign 20.7%.
- F10: the pool prop rendered as a floating sliver.
- Checked, **not** faults: distance blackness (visibility 800 = E3M1's own
  and the campaign median); wall shade (ours median 17 vs E3M1's 28 — we
  are *brighter*, so black distance is fog, not shade).

**Fixed**
- F4: `level/facade_pass.py`, a post-compile pipeline stage — each carved
  mass is a building, each gets a facade from its district's tile-set.
  City now runs **6 facade tiles + masonry**, spread like E3M1's.
- F7: masses under 3 pu across take masonry, not a facade (a rule).
- F8: `level/lightpools.py` — Blood's own technique: 9 small sectors cut
  into street floors at mouths, gates, junctions, 18 shade points brighter,
  animating. +9 sectors, +72 walls.
- F9/F10: prop chosen by measurement, not by name — tile 908 is E3M1's
  street "fire" but a type census shows all 235 are kTrapExploder *traps*;
  tile 641 is a hall torch mounted 57k–64k above the floor; **tile 506** is
  the campaign's floor-standing flame (150 instances, median height 18.8k).
  Flicker now **22.2%** against the campaign's 20.7%.
- Bonus F11: the avenue's floor changed material down the centerline
  because district seams follow street centres — one roadway citywide now.

**Verified**: `i2-after` → `i2-torch` → `i2-flame`. Forecourt: grey slab
wall → ashlar facade with arched windows, masonry kiosk, a burning flame.
Sewer trunk: mossy water floor, rusted stone, rat — E3M3's register.

## Integration pass (iteration 3 boundary)

- plan contracts **16/16**; conformance **7/7** (it caught the light pools
  joining the street network — now declared in `reports/build-manifest.json`
  so declaration and geometry stay tied).
- budget: **45 sectors / 327 walls / 26 sprites** — 95% wall reserve.
- discriminator: **2.09, inside the campaign's own range** (0.59–4.29),
  rank 39/44.
- Worst features, with honest readings:
  - `sky_fraction` 0.378 vs E3M1's own 0.118 — **not a texture fault**: our
    buildings have almost no interiors yet, so sky sectors dominate. Falls
    as districts are built out; recorded rather than silenced.
  - `height_iqr_ratio` 9.6 vs 2.0 and `median_height` 20.5k vs 33.3k — same
    cause plus interiors built one texture-repeat short.
  - `pickups_per_dude` 0.0 vs 0.9 and `declared_secrets` 0 vs 5 — real
    content gaps, iteration 3.
  - `dead_end_fraction` 0.333 vs 0.159 — real; the sewer ring is not closed
    and the canteen has one door.
  - `coincident_solid_pairs` 2 vs 0 — the two stack mouths, by design.

## Iteration 3 — dressing density and the content gaps

Looked: fresh3 (Theatre Row, forecourt, north lane, market street, quay up).

**Found**
- F12: no pickups anywhere (campaign 0.9 per dude).
- F13: interiors one texture-repeat short (20,480 against the campaign's
  33,280 median room).
- F14: dead-end fraction 0.33 against the campaign's 0.16 — the canteen had
  one door.
- F15 *tooling*: the observer silently drops a frame for very long sight
  lines (four poses aimed 8-16 pu down a street produced no image; the same
  poses aimed 3-6 pu render). Recorded as a limitation of the looking
  tool, not a fault of the map; loop poses now keep sight lines short.
- F16: a `secret=True` region emits the campaign's per-sector wiring, but
  the *count* is a separate sprite (E3M1 carries one transmitting command
  73 on channel 1 — nine secrets). Ours declared none, so a player would
  never be told they found one.

**Fixed**
- F12: six pickups, types and fields transcribed from E3M1's own
  placements — ratio now 1.00 against the campaign's 0.9.
- F13: canteen raised to 32,768 (counter and pedestal with it).
- F14: a second z-motion door on the canteen's west end.
- F16: the declaring sprite, command 64+1.
- Also: a secret stash off the sewer trunk (`secret=True`), which is the
  SP contract's secret branch arriving early.

**Measured, and NOT fixed — a disagreement recorded rather than silenced**
- `shape.height_iqr_ratio` 9.6 vs campaign 2.0 is the discriminator's worst
  feature, and the tempting fix is to lower the streets. E3M1's own street
  sectors measure **196,608 tall — exactly ours**. The spread comes from
  having sky streets and almost no interiors yet: E3M1 carries 337 non-sky
  sectors against our 30. Lowering the streets to satisfy the statistic
  would break a measured norm. It falls as districts are built out.
  `median_height` and `mean_degree` have the same cause.
- `coincident_solid_pairs` 2 vs 0: the two sewer stack mouths, required to
  be congruent by the stack contract.

## Iteration 4 — fresh eyes, no new fault above minor

Looked: fresh5 (cemetery, lychgate, the stash, the canteen's second door,
the well square). Frames show the flame pools reading in Old Crossing, the
stash with its pickup, facades differing between neighbours. Nothing found
above minor: one close-range sprite clips a corner (normal), and the
stash's stone reads a little clean for a sewer branch.

**Exit condition met**: two consecutive iterations with no new fault above
minor from fresh poses. Wall reserve 95% (338 of 7,000), far above the 10%
floor.

## Final state

- plan contracts 16/16 · conformance 7/7 · budget 47 sectors / 338 walls /
  33 sprites · discriminator **1.79, inside the campaign's range** (opened
  at 2.09) · flicker 22.2% against the campaign's 20.7%.

## Iteration 5 — Market Slip built out (the district the player starts in)

The loop's pipeline stages carried straight over; this district only needed
what is particular to it, from its own L1 `furnish` slots.

**Built**
- The **fountain**: a sunken basin at DWE3M1's own basin depth (4096),
  which is also exactly one max step — so it stays inside the street's
  walkable component and costs no walk-around loop (the census is at its
  contract ceiling of 9).
- A **stall run** of three platforms at +3072 (TEDE1M2's market module).
- The **quay's boards**: floor 352, held back in materials.py for the thing
  it actually is rather than a district's roadway. This also delivers the
  roadway/walk split that E3M1 has and we had deferred.
- The **river** beyond it with a moored lighter, per DWE3M10: water built
  as real sectors with boats as geometry, not a painted edge.
- The **market hall**: E4M9's retail grammar — a concourse with two units
  behind mouth-sized storefront necks.

**Found and fixed while building**
- F17 *water*: tile 404 (DWE3M1 basins) and 433 (DWE3M10) both rendered as
  dirt — DWE3M10's wet sectors are `underwater` volumes needing a water-link
  pair. E3M3's **shallow** water is the right precedent: tile 1120 at
  xsector `depth` 7, in 16 sectors. River and basin now read as water.
- F18 *aperture step-wall ownership*, the worst find of this iteration and
  the directive's own lever: a door opening straight onto a six-storey
  facade makes Build draw **the whole wall above it from the door's tile** —
  a brown wooden slab six storeys tall, visible in the stall frame. The fix
  is mediation, not retiling: a porch with a door-height ceiling gives the
  facade back the wall above the opening. Applied to the market hall and
  to **both canteen doors in the pilot district**, which had the same fault.
- F19: the hall's jamb wore the interior's papered tile where the plaza
  could see it floor-to-sky. A doorway's jambs belong to the room that
  looks at them; they take the facade's opening tile.
- F20: two rooms sharing only *part* of an edge leave the remainder
  coincident and unpaired. Storefronts now meet the concourse through a
  neck whose whole face is the mouth — which is what a storefront reveal
  is anyway.
- F21: the wall lamps still used tile 641 at head height and rendered as a
  checkered sliver; the campaign mounts that torch 57k-64k above the floor
  (73 instances). Now at 3.38 player heights.

**State**: 63 sectors / 440 walls / 33 sprites (94% wall reserve).
Contracts 16/16, conformance 7/7 (it caught the market furniture joining
the street network, then the hall interiors being wrongly counted as
street-joined — both now declared separately in the build manifest).
Discriminator **1.64**, blandness 0.25 — inside the campaign's own
distribution for the first time (blander than 7 of 43, from 0 of 43).

**Deferred**: `dead_end_fraction` rose to 0.381 because retail units are
dead ends by nature; the honest fix is circulation loops (the sewer ring's
dive link, the roof route), not shop plans.

## Iteration 6 — texture alignment at entrances (owner report)

Owner: *"when there is entrances the building textures aren't correctly
aligned."*  Two distinct faults, both at openings, both now pipeline fixes.

**F22 — horizontal: the run restarts at every split.**  Blood advances a
wall's texture by `x_repeat * 8` along its length, so a run continues only
if the next wall's panning picks up where the last left off.  Ours all
started at zero, so the pattern restarted at every vertex — including the
vertices that are not corners at all, the ones where a long facade was
split to hang an entrance off it (which is `align_wall_runs`' own
description of the fault).  Wired `align_wall_runs` + `align_wall_textures`
after the facade pass, since they depend on its picnums: **176 walls
repanned across 44 runs; 67 walls floor-anchored.**

**F23 — vertical: the header is anchored to the wrong edge.**  This was the
one the frames showed worst.  Build anchors a *one-sided* wall's texture to
its sector's ceiling, but a *two-sided* wall's upper step to the bottom of
that step — the head of the opening.  Our headers are 180,224 tall against a
32,768 tile repeat: **5.5 repeats, so the two anchors sit exactly half a
tile apart**, and every cornice band broke as it crossed an entrance.
Measured the campaign before choosing: E3M1 sets the align-to-ceiling flag
on 21 of its 35 street headers; DWE3M1 (9 of 105) and TEDE1M2 (0 of 85)
mostly leave it clear — and their street facades are plainer tiles where
the phase does not show.  Ours are banded, so we follow E3M1.
`facade_pass.align_headers` now sets it on every street opening: 5 headers,
heights 174,080 / 176,128 / 180,224.

**Verified**: `align-before` → `align-header`, same poses.  At the market
hall the window row and both cornice bands now run unbroken across the
entrance; at the canteen the works' arched window row runs continuously
across both doors, where before the wall above them was blank and
out of phase.

Contracts 16/16, conformance 7/7, 63 sectors / 440 walls unchanged — the
fix is panning and one cstat bit, not geometry.

## Iteration 7 — entrances land between the painted windows

Owner: *"texture is correctly aligned but the entrance is visually wrong,
it should copy the windows on texture, not cut them in half."*

Alignment was fixed last iteration; this is the geometry of the hole.

**Measured first.**  Both E3M1 and TEDE1M2 draw street walls at **16 world
units per tile pixel** (133 of 152 and 216 of 260 walls), so a 64-pixel
facade tile is a **1024-unit bay** — one painted window and its pier.  Two
more measurements decided the rule:
- E3M1's modal street opening is **exactly one bay (1024)**, and whole-bay
  openings are its largest class (17 of 34); ours were 1536 and 1.5 bays.
- E3M1 phases **43 of its 61 street-facing walls to world position** rather
  than to each wall's own start vertex.  That is what makes a bay grid
  exist across a whole district instead of per wall.

**Fixed**
- `facade_pass.world_align_facades`: every street wall's `x_panning` is
  derived from its world coordinate along its own axis (with the sign of
  its direction, so a wall running backwards still lands its tile
  boundaries on world multiples of 1024).  132 walls phased.
- `facade_pass.snap_opening`: openings snap to whole bays on that grid.
- Applied to all five street openings: the canteen's two doors (1 bay
  each, with a pier between), the market hall (2 bays), the works stair
  mouth (2 bays), the loading dock (2 bays), the lychgate (2 bays).
- The canteen itself sat at `yard_x0 - 512`, half a bay off the grid, so
  every opening in its face cut windows no matter their width; it now
  starts on the grid.

**Verified**: numerically — all five openings report whole-bay widths with
both edges on 1024 multiples — and by eye at three entrances: the arched
window row runs unbroken across the works facade with the doors set between
bays, and the market hall's windows and cornices are whole either side of a
two-bay opening.

Contracts 16/16, conformance 7/7, 63 sectors / 438 walls.

## Iteration 8 — the sewer network, and why it wasn't connected

Owner: *"more tunnels in sewers, more places to visit"*, then *"sewers
aren't correctly connected to the city, I just see the flying torches"*.

**Built** (`level/l3_sewer.py`): a ring of ten segments -- corner, leg,
corner, leg all the way round -- with the north and south legs split
lengthwise into a **walk and a channel**, which is E3M3's cross-section
(62 ledge-over-channel pairs, the walk one max step above the water) rather
than decoration.  Four places to go hang off it: the pumping chamber, a
silt trap, an eastern annex, and a flooded branch.  Three necks tie the
ring into the trunk, the junction and the cistern.

Against the contract: **35 sectors, internal cycle rank 7** (SP asks 7+),
**wet share 0.22** (0.2-0.4), depth 3.14 standing, animated shade tuned
from 79% down toward E3M3's 57% by lighting the water and the chambers
rather than every plain leg.  Population from E3M3's own census (rats, a
gill beast, a bone eel -- no cultist garrison), four finds so a branch is
worth taking, and the flooded branch is a second declared secret (the
count sprite now transmits 64+2).

**F24 — the sewer was not connected, and it was one wrong constant.**
The campaign's walkable room-over-room floors are the **stack** family
(`kMarkerUpStack` 11 / `kMarkerLowStack` 12): every paired link in E1M1 and
E3M1 reads as "stack".  My hand-built links used **7/6, the "link"
family** -- a different mechanism.  `warpInit` therefore never paired them,
so the floor stayed solid (no way down) while the mirror tile still made
the renderer draw the far side's *sprites* without its geometry: flying
torches over the grate.  Diagnosed by dumping a working E1M1/E3M1 pair and
comparing field by field, which is also how the missing XSector on our
lower halves showed up (100% of campaign pairs carry one; ours now do).

**F25 — the flames floated.**  A face sprite's z is its *centre*, so a
506 flame (11,008 tall) placed one player height up hangs with its base
11k above the ground and its top through a tunnel ceiling.  Floor-standing
props now sit at half their own height, computed from the tile.

**F26 — the loading dock was unreachable**: raised 6144, above the 4096
max step.  street-furniture measured cart platforms at +6144, but those are
scenery; a dock the player steps onto belongs at exactly one max step.
Found by the reachability check, not by eye -- recorded as a deliberate
deviation from the mined value, with the reason.

**F27 — the conformance check was reading the old marker ids** and so
passed nothing at all once the links moved to the stack family.  It now
reads pairs through the project's own stack miner, and asserts the family
as well as the shared translation.

**Verified**: all **35 sewer sectors reachable from the spawn** through the
stack links; 79 of 80 sectors reachable overall, the one exception being
the backdrop scene, which is unreachable by design.  Contracts 16/16,
conformance 7/7.  80 sectors / 528 walls / 52 sprites, 92% wall reserve.

## Iteration 9 — why the sewer really wasn't connected (source, not inference)

Owner: *"This is not connection of sectors, it is just some torch sprite.
Check how it should correctly work, no guessing."*  Correct on both counts:
my previous answer was inference validated by my own tool agreeing with my
own construction.  Read NBlood instead.

**How Blood room-over-room actually works** (source-verified):
- `warp.cpp warpInit()` scans sprites, and for `kMarkerUpStack`(11) /
  `kMarkerLowStack`(12) records `gUpperLink[sectnum]` / `gLowerLink[sectnum]`,
  snaps the marker z to the sector floor/ceiling, then pairs an upper with
  the lower carrying the same `XSPRITE.data1`, writing each into the
  other's `owner`.
- Falling through is not a hole in the floor: `gameutil.cpp GetZRange()`
  sees `gUpperLink[nSector] >= 0`, re-runs `getzrange` inside the *linked*
  sector at the marker offset, and returns that as the floor.  The floor of
  the pit simply stops existing, the player drops, and
  `warp.cpp CheckLink()` moves them by `lower - upper`.
- Seeing through is separate: `mirrors.cpp` requires
  `IsRorSector(upper, OBJ_FLOOR) > 0` -- floor picnum `kMirrorTile` (504)
  or floorstat & 0x180 -- *plus* the paired link.  It then forces the lower
  sector's ceiling to 504 itself.

**F28 — the real bug: the markers were deleted at map load.**
`db.cpp PropagateMarkerReferences()` walks every sprite on statnum 10
(`kStatMarker`) and `DeleteSprite()`s any whose type is not
kMarkerOff/Axis/WarpDest/On.  Types 9-14 -- water, **stack**, goo -- all
fall through to the delete.  It runs at the end of `dbLoadMap`
(db.cpp:1325); `warpInit` runs later at level start (blood.cpp:750).  So
every marker was gone before a single link was registered: no
`gUpperLink`, no floor extension, solid ground, no way down.  All six stack
markers in E3M1 sit on statnum **0** with cstat 128 -- which is why the
campaign's work and mine did not.

Our markers now match the campaign field for field: type 11/12, statnum 0,
cstat 128, XSprite present, paired `data1`.

**F29 — the same bug is in the shared grammar.**
`bloodmap/roomoverroom.py` hardcodes `MARKER_STATNUM = 10`, so every link
`room_over_room()` has ever built is deleted at load.  Filed as
grammar-requests.md #8 (high priority); not patched here, since that tree
belongs to the parallel workstream.

**New standing check**: conformance now fails the build if any link marker
sits on statnum 10 or lacks an XSprite, citing the two source sites.  8/8
rows pass.

**Correction to iteration 8**: the "wrong marker family" I reported there
was not the whole story -- `warpInit` registers 6/7 as links too; the
families differ in z-snapping (11/12 snap to floor/ceiling) and in what the
campaign uses for walkable ROR floors.  The statnum is what actually broke
it.  Switching to 11/12 was right, but it was not the fix.

## Iteration 10 — the marker tile, and the numbers behind "must not die"

Owner: *"I still see that ROR connections is not done correctly... In
xmapedit I just see normal sector and torch sprite instead of these special
linking sprites"*, pointing at `reasoned-authoring-v1`, whose underwater
links work.

Comparing our markers against that working example was decisive, and it is
the comparison I should have made first.

**F30 — the marker tile was wrong.**  Censused across the whole campaign,
273 link markers of every family use **picnum 2332 on the upper half and
2331 on the lower**, 100% of instances; the monastery's working water links
use exactly those.  Ours used `roomoverroom.MARKER_TILE = 3997`, which
XMapEdit draws as a **torch** -- so the editor showed a torch where the
link marker should be, which is precisely what was reported.  Filed as
grammar-requests #8b.

Our markers now match the working example field for field: type 11/12,
statnum 0, picnum 2332/2331, cstat 128, XSprite present, paired `data1`.

**The two safety questions, answered from source rather than by feel:**
- `kDudeGravity` 58254/tic and `kFallDamageFloor` 100<<4 (forgiven) give a
  **damage-free fall of 62,793 units = 3.70 player heights**.  The grate
  drop is 53,248 (3.14) -> impact 1,281,588 against a 1,310,720 threshold:
  **zero damage**, with margin.  The cellar pit is 10,240: zero.
- The standing human's `normalJumpZ` (0xbaaaa) gives a **jump rise of
  21,113 = 1.24 player heights**.  The cellar pit's climb-back is 10,240
  (0.60) -> **jumpable**, so the works stair is a genuine two-way exit and
  the sewer is not a trap.  The grate's 3.14 heights is one-way by design.

**Three new standing checks** (conformance now 11/11): marker tiles match
the campaign; no link drop injures the player; at least one link is
climbable back out.  Each cites its source site so the next person does not
have to re-derive it.

**Deferred, with the reason**: the grate still wants a kerb ring to read as
a manhole, and the owner's suggested technical building with stairs is the
better entrance.  A first attempt at the kerb collided with the works stair
and the loading dock -- the yard is only 4 plan units wide with a gatehouse
taking 2.25 of them -- so both belong with a small building placed on the
rail spur, where there is room, rather than forced into the yard.

## Iteration 11 — the pumping station: a road-level way in, and out

Owner: the entrances *"need to be more obvious, not just some random
square"*, with a real sense of descending, no fall deaths, and a way back;
the suggestion being a road-level entrance with stairs from a small
technical building, as Blood does it.

**Built** (`level/l3_shed.py`): the pumping station on the rail spur -- a
door on the street with its bay-aligned porch reveal, a hall, and a
**ten-step flight** descending 40,960 into the works void to a cellar.
The cellar holds a pit that stack-links into a new **shaft-foot chamber**
in the sewer, off the ring's north walk.  So the sewer now has a proper
front door: street, door, stairs, cellar, shaft, network -- and the same
way back.

**Why it sits inside the works mass rather than standing free.**  Two
attempts failed first, both instructive: a free-standing hut on the spur
adds a tenth walk-around loop and the census is at its contract ceiling of
nine; a lean-to bumped out of the works' face makes `carve` cut a *second*
hole that shares an edge with the works hole, which is not a legal
boundary.  Inside the mass, the rooms occupy void that already exists and
the door still reads as a small building on the street.

**The two safety numbers, now built into the geometry:**
- the station drop is **12,288 = 0.72 player heights**, under the 1.24
  jump rise, so the player hops back up through the plane and walks out;
- three links now: the grate at 3.14 heights (one-way, and under the 3.70
  damage-free limit), the works pit at 0.60 and the station pit at 0.72,
  both climbable.  Conformance asserts all of it.

**F31 — the station interiors rendered almost black.**  The service
material's shade (36-38) suits a sewer, not a room someone works in; hall,
stair and cellar came back as near-solid black.  Shade lifted to 22 and a
measured floor flame placed in the hall and the cellar.

**Deferred, honestly**: the grate still has no kerb.  It wants one, but the
yard is 4 plan units wide with a gatehouse taking 2.25, and a ring around
it collided with the works stair and the loading dock; it belongs with a
small rearrangement of the yard rather than forced in beside them.

**State**: 97 sectors / 613 walls / 56 sprites, 91% wall reserve.  Plan
16/16, conformance 11/11, 96 of 97 sectors reachable from the spawn (the
one exception is the backdrop scene, unreachable by design), all 45 sewer
sectors reachable.

## Iteration 12 — the grate gets its kerb

The piece I owed from last iteration: the drop entry was "just a random
square" in the paving.

**Moved before framed.**  A ring around the grate where it stood collided
with the loading dock to the west and the gatehouse to the east -- the yard
is four plan units wide and the gatehouse takes 2.25 of them.  The L1 entry
therefore shifts half a unit east, to (50.5, 21.5), which leaves half a
plan unit of clearance on both sides; the plan layer is where that
decision belongs, and the sewer's trunk followed it automatically because
the trunk's east end is derived from the entry position.

**Built**: a 2048 kerb ring -- one sector with the shaft as its hole --
raised 1024 above the paving, which is a quarter of the 4096 max step, so
it is stepped over rather than climbed.  Through the opening you now see
the sewer's planking and a flame burning below.

Two things fell out of it, both caught by checks rather than by eye:
- the staged charges ended up inside the new kerb footprint and had to move
  into the strip between the dock mouth and the ring;
- the kerb joined the street's walkable component, so conformance failed
  until the manifest declared it -- the declaration-versus-geometry check
  doing its job for the third time.

**A dead end removed on the way**: with the grate moved, the trunk reaches
the shaft foot directly and the shaft also opens onto the ring's east leg,
so the drop lands on a junction with two ways on rather than in a pocket.

**State**: 97 sectors / 617 walls / 56 sprites, 91% wall reserve.  Plan
16/16, conformance 11/11, 96 of 97 sectors reachable (the backdrop scene is
the exception, by design), all 44 sewer sectors reachable.  Discriminator
**1.31**, its best yet -- 2.09 when the loop opened -- and blandness 0.21,
now inside the campaign's own spread rather than outside it.

## Iteration 13 — Theatre Row's venues, and four faults they exposed

The Aldermack complex, the saloon, the shooting parlor and the pawn shop,
built into the superblock's void: 38 sectors and 241 walls of venue.  The
build was the easy half.  Rendering it found four faults, three of them
systemic and none of them about Theatre Row.

**Every venue was the same room.**  The first frames showed a bar, a
shooting gallery and the city's landmark theatre as the same brown box:
`INTERIORS` had one interior palette ("common") and every venue inherited
it, the exact shape of the fault the district-facade work fixed one layer
up.  A per-building census says what a town actually does -- E3M1 puts 20
interior palettes across its 337 interior sectors, TEDE1M2 35 across 613,
E3M2 29 across 473.  A building's palette is how you know which building
you are in.  So `INTERIORS` now carries one entry per venue role, each one
a single campaign building's own triple taken whole and then looked at on a
contact sheet: saloon 28/390/40 (E3M1 building 3, plank walls over a wood
floor), parlor 100/294/20 (E3M1 building 4, rust plaster over chequered
tile), theatre 119/300/422 (E3M2 building 4: red-and-gold tapestry with a
carved base course, patterned carpet, medallion ceiling), shop 2294/290/40
(E6M1's shop, brick over wainscot).  Height differentiates too, and it is
free: the auditorium is 49,152 -- the tallest interior in the city -- the
pawn shop 24,576.

**The theatre was a hall with a step in it.**  A stage is not a raised
platform, it is a raised platform under a *lower ceiling*: give the stage
its own clear height and the wall between it and the house becomes a
proscenium arch, 20,480 units of it, facing the audience.  Three raked rows
at 1024 / 2048 / 3072 and a pair of flames flanking the stage front finish
it.  Each row is an island with clear floor around it, because two
adjacent platforms would share an edge no portal declares.

**The way out of a room was the darkest thing in it.**  The pawn shop's
door rendered as a black rectangle.  Two causes, measured rather than
guessed:

* `shade_walls_directionally` shades walls by the cosine between their
  normal and the room's light, and the campaign does not do that to doors.
  Across E3M1, E3M2, E1M1, E6M1 and E4M9 -- 720 walls facing a z-motion
  door -- the shade delta against the owning room's median is exactly
  **+0.0** (p10 -5, p90 +7).  Ours was **+15**.  `lightpools.settle_door_shading`
  now pulls every door-facing wall back to its room's median, which moved
  17 walls by up to 11 shades.
* `room_amplitude` sizes a room by its **wall count**, and our furniture is
  geometry: the pawn shop is 3.5 x 2.5 plan units with four display
  pedestals in it, so it has 22 walls and was shaded like a hall.  Banding
  the campaign's spread by floor *area* instead (1,393 rooms) gives
  medians 7 / 12 / 19 / 21 and p75s 15 / 22 / 32 / 32 for tiny / small /
  medium / large.  `lightpools.settle_room_spread` caps each room at its
  band's p75.  Filed as grammar request #9 -- the sizing belongs in
  bloodmap, this is a corrective pass over its output.

  *A wrong turn worth recording*: the cap was first set at the band
  **median**, which compressed 102 of 135 rooms and dropped measured
  contrast from 49.5 to 32 -- precisely the failure `bloodmap.lighting`
  already documents ("applying an average everywhere produces a level with
  no light in it").  p75 removes the extreme without removing the tail:
  16 rooms compressed, contrast back to 34.

**The city was paved in the wrong tile.**  Rendering E3M1 sector 6 through
the same observer for a side-by-side made this unmissable: the reference
frame is more than a third warm red cobble and ours was grey wall to wall.
E3M1's street runs three surfaces in near-equal thirds by area -- 352
(37%), 4 (34%), 379 (29%) -- and the contact sheet says 352 is the
**cobblestone roadway** and 4 is the flagstone **pavement**.  We had
`ROADWAY = 4`, so the whole city was paved in E3M1's sidewalk; and 352 was
meanwhile called `BOARDWALK` on the strength of its name, which is the tile
414 mistake made a second time.  Corrected: `ROADWAY = 352`, `WALK = 4`,
and the real boardwalk is **28** -- DWE3M10's pier promenade is 64% of it
by area.  One line of materials, and the city's whole colour balance moves
onto Blood's.

**One geometry fault the campaign never has.**  The discriminator's worst
feature this round was `coincident_solid_pairs` at 2.000 against a campaign
**0.000 in all 43 maps**: the parked pit landing declared only its north
and south rims, so its east and west edges coincided with the junction's
hole and were solid on both sides.  All four rims now declared; the count
is 0.

**Not a fault, checked and recorded**: distant facades render nearly black
in our street frames.  The E3M1 reference frame renders the same way, and
our street facades are in fact *brighter* than the campaign's (median shade
17 against E3M1's 28, nothing at all above 48).  It is Blood at 3am, not a
bug -- recorded so it is not re-litigated.

**State**: 135 sectors / 858 walls / 81 sprites, 88% wall reserve.  Plan
16/16, conformance 11/11.  Discriminator **1.37**, inside the campaign's
range (0.67-4.00) at rank 33 of 44, blandness 0.25.

**Still open, ranked**: `visual.composition.ceiling` 0.134 against 0.025
(3.11 IQRs) is now the worst single feature and is untouched by this round;
`dead_end_fraction` 0.333 against 0.159 wants circulation loops, not shop
plans; `contrast` 34 against 49.5 says our dark end is not dark enough --
every room of ours has a flame in it, and the campaign leaves rooms unlit.
The sidewalk/roadway *split* is still geometry we have not built; only the
materials are now right.

## Iteration 14 — the city was empty, and the reason it was empty

Three faults, one of which turns out to be the same fault the last two
iterations kept meeting from different sides.

**The city was under-dressed by a factor of three.**  Sprites per sector,
measured:

| map | sprites/sector | per 100 walls |
|-----|----------------|---------------|
| E6M1 | 4.06 | 57.0 |
| E3M1 | 2.11 | 32.5 |
| E4M9 | 1.78 | 26.0 |
| E3M2 | 1.60 | 21.2 |
| **Gravesend (before)** | **0.60** | **9.4** |

Every venue had a cultist and a flame in it and nothing else.  What Blood
puts in a room is not furniture -- the furniture is geometry, which this
project already builds -- it is **grime**: censusing `decoration-v1.json`
across eight campaign maps, the tiles that come up are blood spatter and
pools, slime and water drips, cobwebs, crates and floor grates.
`level/dressing.py` now places those by space (sewer / service / interior /
street), each sprite carrying the reference's own canonical `x_repeat`,
`y_repeat`, `cstat` and `shade`, at the campaign's own density -- median 1
per decorated sector, p90 5, drawn from an eleven-slot distribution rather
than from its average.  246 placed; **2.42 sprites/sector, 38.0 per 100
walls**, inside the campaign band on both.

*The bug it shipped with, and the rule behind it*: the first pass stood
every sprite up at half its drawn height, and the saloon came back with
2.91 player heights of blood spatter hanging in mid-air over the card
tables.  How high a sprite sits is decided by its **alignment**, which
lives in the cstat and nowhere else: a face sprite (0x30 == 0) stands at
half its own height because its z is its centre, a floor-aligned sprite
(0x30 == 0x20) is a flat decal and lies at zero, and a wall-aligned one
(0x10) cannot be placed by a floor anchor at all -- tile 915 was dropped
from the palettes for that reason rather than hung in the air.

**The sewer was one height everywhere.**  `visual.composition.ceiling` was
the worst feature on the board at 0.134 against a campaign 0.025, and the
worst frames in the level were all sewer: 20,480 of flat ceiling over every
run and chamber, filling 35-40% of the frame.  E3M3, Blood's own sewer,
runs a median sector height of **28,672** with q1 16,384 and q3 32,768 --
higher than ours, and varying by a factor of two where ours was a single
constant.  Runs are now 24,576 and chambers 32,768.

**Four venues off one street are four dead-end trees.**  Two corridors
through the void the venues left between them -- saloon back room to the
parlor's range, and the range through to the Aldermack's backstage -- close
the block into a circuit.

**The diagnosis under all three, stated plainly**: our rooms are far larger
and far fewer than the campaign's.  Roofed sector area, Mu^2:

| map | q1 | median | q3 | share over 10M |
|-----|----|--------|----|----------------|
| E3M1 | 0.26 | 0.39 | 1.13 | 2% |
| E3M2 | 0.38 | 0.79 | 2.59 | 9% |
| E3M3 | 1.05 | 2.10 | 4.33 | 8% |
| **Gravesend** | 0.52 | 2.10 | **8.39** | **23%** |

A campaign interior is a warren; ours are halls.  That single fact drives
`composition.ceiling` (a big flat ceiling over a long sight line),
`dead_end_fraction` 0.321 against 0.159, `mean_degree` 2.20 against 2.74
and `loops_per_100_sectors` 9.6 against 37.7 -- and the dead ends confirm
it: of 49 sectors with degree 1, 18 are light pools and 11 are furniture
islands, details that can only ever touch one room.  We have the campaign's
details and a quarter of its rooms.  **The remedy is more rooms, not fewer
details**, which makes it Old Crossing's work (church, cemetery crypt,
tenement interiors) rather than a topology patch here.  Recorded rather
than papered over.

**State**: 137 sectors / 874 walls / 332 sprites, 88% wall reserve.  Plan
16/16, conformance 11/11.  Discriminator **1.34** (from 1.44 at the start
of iteration 13), rank 32 of 44.  `composition.ceiling` 0.134 -> 0.081-0.112
(the visual features are sampled from 40 random poses and move a few
hundredths between runs; the direction is solid, the third digit is not).
`contrast` 34 -> 37-38.5.  Blandness 0.25-0.28.

## Iteration 16 — the decoration overhaul, doors, and shop glass

Owner report: "weird usage of decoration sprites, these flying torches
(506) maybe suppose to be lamps? Also 754 smoke, 660 underwater plant, 668
underwater bubbling. Building entrances are not recognisable as a door and
they are short like for midgets. I would do bigger shop windows with
breakable transparent glass — have a look at E6M1."

Every item was a real fault, and each was settled by measurement rather
than by argument.

**1. Props had no mounting model.** This project placed every decoration
with `place_on_floor` in the middle of a region at a height derived from
the tile's own drawn size — as though mounting were a property of the
placement code. It is a property of the thing. Censusing all 40 campaign
maps for each tile's height above its sector floor and its distance to the
nearest *solid* wall separates them cleanly:

| tile | n | centre height | within 512u of a solid wall | what it is |
|---|---|---|---|---|
| 506 | 194 | +1.03 | **92%** | a brazier bracketed to a wall |
| 641 | 447 | +3.44 | 53% | a hall torch, mounted high |
| 640 | 593 | +0.00 | 58% | a lamp fixture standing on the ground |
| 754 | 192 | +0.00 | 58% | smoke, on the ground, cstat 130 |
| 660 | 733 | +0.00 | 9% | a frond, out in open water |
| 668 | 111 | +0.00 | 45% | rising bubbles |
| 795 | 1327 | +1.99 | 42% | a grate, up on a wall |

So 506 is a wall bracket, and we floated it mid-room at a third of a player
height: "flying torches" is an exact description. `props.py` now carries the
measured catalogue and `props.mount_on_wall` brackets against a named face.

**Shade was the other half.** Tile 506 is shade **−128 in 148 of its 194**
campaign instances — a flame is self-illuminated. Ours carried no shade,
inherited the room's +26, and rendered as *dark* torches; worse,
`lights_by_sector` drops anything above its shade threshold, so the flicker
pass had stopped seeing them (0.6% of sectors animating against a campaign
20.7%). With measured shades it is back to **0.199**.

**2. 660 / 664 / 668 are water dressing.** Blood does use them in E3M3 —
but E3M3's sewer has water in it. Ours ran them down dry brick tunnels.
They are now placed only in the wet channels and the flooded branch (6
sprites, by hand in `l3_sewer`), and are gone from the generic pass. 795 is
gone from the street palette: at +1.99 heights it is a wall grate, not a
floor plate.

**3. The doors were measured, and the owner is right.** Across 1,269
campaign z-motion doors the open height runs **median 31,744 = 1.87 player
heights**, p10 17,408. Ours were 16,384 — **0.97 of a player height**,
below the campaign's tenth percentile. All four modules now use 31,744.

A correction worth recording: I first went looking for a "door texture" and
listed 2490/449/200 as door faces. They are jambs. The owner's point —
*"there is no such a thing as door"* — is the actual grammar: in Blood a
door is a moving sector wearing ordinary wall material (E3M1's own door
leaves are 379 and 449, plain stone). An opening therefore reads as a door
through **proportion and reveal**, which is why the height was the whole fix.

**4. Shop glass, from E6M1's own four walls.** Reading them gives the
recipe exactly: `over_picnum 266`, `cstat 0x00d5` (blocking | align |
masked | hitscan | translucent), `x_repeat 32`, `y_repeat 8`, and an XWALL
with `trigger_vector = 1`. NBlood confirms the behaviour rather than us
inferring it: `actor.cpp` case 4 fires `trTriggerWall(..., kCmdWallImpact)`
on a masked wall whose XWALL sets triggerVector, and `triggers.cpp` then
clears cstat bits 1, 64 and 16 on **both** sides — the glass stops
blocking, stops catching hitscans, and stops being drawn.

The construction that makes this possible is a **display box**: a shallow
room between shop and street, floor raised 2048 as a plinth, glazed on its
street edge. Glass needs a two-sided wall, so it needs something to be
transparent *to*. The pawn shop's long frontage is its north face on
Theatre Row (not the avenue end where its door is), so the window gets two
full bays there. Verified in the emitted map: 4 panes, each with
`trigger_vector=1`.

Also fixed on the way: `props.face_segment` first inset *perpendicular* to
the face as well as along it, putting the anchor segment inside the room;
brackets then resolved onto whatever wall the engine found, including
portals, which the compiler rightly rejected.

Build: 156 sectors / 992 walls / 387 sprites. 11/11 conformance, 16/16
contract rows. Frames in `reports/looks/i28`.

**Still open, and visible in `street_lamp.png`:** every mass rises to the
same sky, so the city has no skyline — the church tower, which
church-patterns.md asks for as the vista silhouette, cannot be seen from
the street at all. E3M1's differentiator is precisely its stepped
roofscape. That is the next structural piece, and it is a massing-layer
change, not a dressing one.

## Iteration 17 — style as a joint distribution, not a set of marginals

Owner: "that style, decorations and sprites selection is still hit and miss
— get better understanding of style combination and what it suppose to
mean and be used for."

The diagnosis is that every earlier pass mined **marginals** — how high tile
506 sits, which facade tile is commonest — and never the **joint**
distribution. So `materials.py` chose surfaces by role and `dressing.py`
chose props by a ceiling-tile lookup, and the two never met. Two new tools
mine the joint distribution instead.

**`tools/mine_style_combinations.py`** — 19,504 campaign rooms (sectors of
at least a plan unit square and over 1.2 player heights, doors excluded),
6,316 distinct (wall, floor, ceiling) styles, and for each prop the
surfaces it keeps company with, by PMI over a support floor. That is what a
prop *means*:

    580  candelabra       wall:100 (n=23), wall:119 (n=8)
    269  framed painting  ceiling:40
    965  window view      ceiling:454
    1701 chandelier       floor:110
    54 / 694 / 692        floor:568, ceiling:255   (drips, grating, chains)

**`tools/mine_prop_catalogue.py`** — all 263 props the campaign uses more
than rarely, classified by their own cstat alignment bits: **142 are
wall-aligned**, 77 stand on the floor, 40 are decals, 4 are brackets. The
old pass excluded wall-aligned tiles outright because it had no wall
anchor, so **more than half of Blood's decoration vocabulary was
unreachable** and rooms got blood and crates where the campaign hangs a
painting, a window, a tapestry or a sign.

### The density was wrong, and my earlier "fix" made it wrong

An earlier iteration compared *sprites per sector* against a campaign
figure of 1.60–4.06 and concluded Gravesend was under-dressed threefold.
That figure counted every sprite — actors, pickups, markers, triggers,
effects — over every sector. Counting what the pass actually places
(decoration: statnum 0, type 0) over what it actually dresses (rooms):

| | campaign | Gravesend before | after |
|---|---|---|---|
| rooms carrying grime | **12%** (median 2, p75 3, p90 5) | 100% | **10%** |
| rooms carrying a light prop | **3%** | ~100% | 19% |

Blood dresses **selectively and heavily**; we dressed **uniformly and
lightly** — the opposite distribution at the same average, which is what
"hit and miss" looks like from inside the level. And Blood lights a room
with *sector shade*, not with lamp sprites: 3% of its rooms contain a
light-emitting prop at all.

### Three gates, because association is not meaning

Co-occurrence alone put a dead tree in the saloon. Each gate is recorded
for what it is:

1. **Context** (measured): the catalogue records each prop's `sky_share`.
   540 is a tree at 0.61 — outdoors; 269 is a painting at 0.00 — never.
2. **Surface tiles** (measured): a tile used 200+ times as a
   wall/floor/ceiling picnum is a *surface*, occasionally pressed into
   service as a sprite. Tile 68 has 5,197 such uses, 568 has 10,151, and
   both were standing free in our rooms. Using one as a prop is an authored
   trick, not something a dressing pass should reach for.
3. **Terrain** (a judgement, and written down as one): rocks genuinely
   co-occur with plank walls — they share rustic and cave spaces — so
   association put a boulder on the saloon's bar. No statistic in the
   corpus separates "rock" from "furniture"; `props.TERRAIN` is an
   authored exclusion and is labelled as such in the source.

Resulting vocabularies, all derived rather than chosen:

    saloon   269 painting, 965 window, 1050 panel
    theatre  580 candelabra, 791, 793, 431
    shop     965 window, 269 painting, 610 tapestry, 2541/2542 medallions
    church   617 portrait, 167 medallion, 683 skull, 753, 847
    sewer    54 drips, 694 grating, 692 chains, 668 bubbles, 776 blood

### Deviations recorded, not silenced

Light props sit at 19% against the campaign's 3%. Two blocks account for
15 of the 20: the nine **street light pools**, which exist precisely because
our streets are district-sized single sectors where the campaign has many
small ones, and the six **sewer corner lights** on a dark ring of four
identical turns. The remaining five are one per venue. This is a real
disagreement with a measured norm and is left standing on stated grounds.

Build: 156 sectors / 992 walls / **107 sprites** (was 387). 11/11
conformance, 16/16 contract rows. Frames in `reports/looks/i30`, `i30b`.

## Iteration 18 — sprite glyph text, and the set-piece capability

Two owner directives: give the city writing, and build the object-scale
version of the authoring loop.

### Writing

`bloodmap.lettering` already existed, built for the monastery project off
the 36 words the campaign spells out. Blood has no text primitive — it has
an alphabet at tiles 3808-3833 and lays one sprite per letter, wall-aligned
at cstat 208, pitched at 1.45 times a letter's drawn width, coloured by
palette lookup. `level/signage.py` is the city's copy of that: ten signs,
73 letters, each palette chosen for what it means (`sign` for commerce,
`warning` for hazard, `stencil` for utility, `rust` for what has been there
too long). Verified by round-trip: `read_sign` on the built map returns
ALDERMACK, WHISKEY, SHOOTING, PAWN, STAGE DOOR, ST GALLOWS, CRYPT, PUMP
HOUSE, OUTFALL, NO EXIT — in that order, not reversed, which is this
module's documented failure mode.

**And a bug it exposed.** The prop-association miner had been treating the
alphabet as decoration, so the dressing pass was scattering single random
letters through the sewer as grime. `props.ALPHABET` now excludes them.

### Set-pieces

`tools/mine_set_pieces.py` detects furniture-like sectors — small, adjacent
to a bigger host room, standing at a different level or wearing different
flats — groups them into pieces and clusters them by signature: **7,014
pieces, 312 classes with four or more occurrences**, in
`knowledge/blood/design/set-pieces-v1.json`.

Tested against the seed the directive named: E1M1's piano comes out as
sectors **[43, 126, 127]**, tiers 0.54 / 0.60 / 0.72, flats 34 and 620,
walls 109/90/84, one `kGenSound` (type 708), sprite 584. That is the
signature exactly. Getting there needed one fix worth recording: a second
tier touches only the tier below it, so the first pass — which required a
host neighbour — produced a two-sector piano missing half its keyboard.

**The proportion that mattered.** Every raised-block class agrees on its
height: 363 pieces across 38 maps, rise **median 0.48 player heights =
8,140 units**. Gravesend's counters were 4,096 — half a Blood counter, and
the reason the saloon bar and card tables read as low platforms. Retrofitted.

`level/setpieces.py` carries the vocabulary (raised_solid, stepped_solid,
basin, inset, canopy) and the class constructors. The plaza fountain, the
venue counters and the church altar are now built through them.

`level/object_loop.py` is the per-object loop: approach poses at standing
eye height, the campaign's own instance of the same class rendered from the
same binary at the same size in the same session, measured checks against
the class's mined ranges, and a packet in `reports/objects/`.

### What this cost, and what is still wrong

Standing the fountain proud of the plaza — which is what the basin class
does — added a tenth walk-around loop and broke conformance. Resolved by
this project's own screening rule: a free-standing mass with no doorway
onto it is landscape, not urbanism. `conformance.MONUMENTS` names it,
counts it, and sets it aside before applying the CN 2 block band. 11/11.

Honest limits:

- **The furnace seed is not reproduced as one piece.** E1M1's 80/81/88/89
  chain through a connecting room (79, 3.15M), so the detector either
  splits them or over-grows. It finds the fire chamber (sector 80, flat
  266) as its own piece. Not tuned away.
- **A class is a geometry, not a meaning.** The basin class's campaign
  instances include stepped pits as well as fountains, so the reference
  frame is a fair comparison of *construction* and not of *subject*.
- Three pieces are under the loop. Market stalls and the stove are declared
  in the vocabulary and not yet wired.
- Two loop bugs found and fixed by looking at the frames: the reference
  selector picked a class containing a sunk example rather than a sunk
  example (rendering a corridor), and approach poses were unconstrained
  (rendering a blank wall). A viewpoint with no line of sight is not a weak
  comparison — it is not a comparison.

Build: 159 sectors / 1,016 walls / 187 sprites. 11/11 conformance, 16/16
contract rows.

## Iteration 19 — Duke's fonts, door levers, and how rectangular we are

### Reading Duke's signage

`tools/read_duke_signs.py` decodes Duke's letter sprites. `DEFS.CON` names
the fonts but does not describe them correctly:

    2822..2915  full ASCII, 2822 draws `!`   (STARTALPHANUM — as documented)
    2940..2965  capitals, 2940 draws **A**   (BIGALPHANUM — NOT `!`)
    2966..2991  capitals again, a second style — undocumented

Decoded from `!`, the sign that reads SHOPPING CENTER comes out as
`3(/00).'#%.4%2`, every character shifted by the ASCII gap between `!` and
`A`. And the block above BIGALPHANUM is not its lowercase: read as a second
A-Z it spells SWISS BANKS, SBS CLUB, BANK, PUB, INFO.

**125 signs across DukCity1-4** (`references/dukcity-signs.txt`), and they
answer the "buildings are still empty" question directly. DukCity names its
uses on the wall: HILTON, HARD ROCK CAFE, BURGER QUEEN, SHOPPING CENTER,
PHARMACY, SECURITY, X-FILES, LAUNDROMAT, PIZZA, TENNIS CENTER, FRENCH
RESTAURANT, BOWLING, HOSPITAL, EMERGENCY, INNER POOL, PRISON, TRIBUNAL,
LAPD, PARKING, VIDEOS, BOOKS, CD LISTENING, MONITORS, CPU, ART, MARKT,
ESSO, TOYS US, SWISS BANKS, NEWS, MEAT, FISH, OPENING SOON, WANTED... —
roughly ten named uses per map. Gravesend has five venues and a church.
That is the gap, stated as a count.

### Door levers

Owner: doors look like solid walls. They do, and this project had already
established why — Blood has no door texture, so a closed door in a masonry
facade *is* masonry. Height and a reveal got part of the way; a lever
finishes it, because it is the only thing on a Blood facade that says
"this opens".

Measured, not chosen: **tile 1070** is the lever (356 instances, more than
twice the next switch tile), wall-aligned at cstat 464, repeats 40x40,
shade -8, mounted at **0.48 player heights** — hand height. **351 of its
356 instances carry a tx_id**, modal command **1 = kCmdOn**, initial state 0.

`level/doorswitch.py` places one beside each street door and wires it:
doors gained `xsector_remote_rx(channel)` while keeping
`xsector_direct_use`, so the door opens if you push it *or* pull the lever.
Five levers on channels 200-204, verified paired in the emitted map.

One bug worth keeping: the first lobby lever landed *inside* the building.
A lever segment has to be wound so the street lies on the side
`place_on_wall` resolves against, and the winding differs per face.

### How rectangular we are

| | 4-wall axis rectangles | diagonal walls |
|---|---|---|
| E1M1 | 30% | 33% |
| E3M1 | 35% | 35% |
| TEDE1M2 | 41% | 32% |
| DukCity1-4 | 46-59% | 23-34% |
| **Gravesend (before)** | **72%** | **7%** |
| **Gravesend (after)** | 72% | **11%** |

Three to five times more rectangular than any reference. `mass_outline`
now chamfers convex corners (512 units, one wall per corner), which is
where a Build city's diagonals actually come from, and the canted corners
read on the avenue.

**It only moved 7% to 11%, and the reason is structural.** Every interior
room this project builds is an axis-aligned rectangle, because
`Assembly.room` joins rooms on named compass faces and a face is a side of
a rectangle — and `props.face_segment`, `setpieces`, `signage` and
`doorswitch` all inherit that assumption. Closing the rest is a grammar
change, filed as request #10, not something to fake here.

Build: 159 sectors / 1,062 walls / 192 sprites. 11/11 conformance, 16/16
contract rows.

## Iteration 20 — understanding Duke, and the gap it exposed

Owner: understand Duke better, fill the missing gaps; it would improve our
conversions too.

### Two knowledge files where there were none

`knowledge/` held Blood only. Now:

**`knowledge/duke3d/semantics-v1.json`** — Duke's own names, transcribed
from Duke's own files rather than inferred: 740 tile names from
`reference/duke3d/DEFS.CON`, 582 of which have art; the 21 `ST_*` sector
tags and 41 `SE_*` sector effectors from EDuke32's `game.h`.

One trap worth recording: DEFS.CON is *sectioned*, and only the first
section is tiles. After the "Defines weapon" comment it is weapon ids,
actor motion values, player actions and sound ids — all colliding
numerically with tiles. Read whole, tile 4 comes back as ACTIVATORLOCKED
*and* RPG_WEAPON *and* getv *and* EJECT_CLIP. Split at the file's own
section break, and cross-checked against the shipped ART, it is clean:
740 tile names, 450 non-tile constants kept separately.

**`knowledge/duke3d/mechanisms-v1.json`** — what Duke maps actually *do*,
across all 56 Duke maps in the corpus: sector lotags, SECTOREFFECTOR
lotags, and the control sprites (ACTIVATOR, TOUCHPLATE, MASTERSWITCH,
CYCLER, MUSICANDSFX, RESPAWN, LOCATORS, GPSPEED) that wire them by hitag.

### What DukCity does

    DukCity1  63 SE  22 demo cam, 16 teleport, 13 swinging door, 6 light switch
    DukCity2  60 SE  14 conveyor, 9 explosive, 7 random lights, 6 teleport
    DukCity3 133 SE  56 light switch, 34 swinging door, 20 teleport, 8 warp elevator
    DukCity4  48 SE  11 sliding door, 9 swinging door, 6 demo cam, 6 teleport

Its doors **swing** (ST 23 + SE 11) rather than rising, which is a large
part of why a Duke door reads as a door. And it carries **22 to 52
MUSICANDSFX emitters per map**.

### The gap that finding opened

Counting the same thing on the Blood side: the campaign runs a **median of
78 ambient sound sprites per map, 23.6 per hundred sectors**. Gravesend
had **one**. It is the largest single dimension the city was missing, and
no rendered frame would ever have shown it.

`level/ambience.py` reads the mechanism out of
`NBlood/source/blood/src/asound.cpp`: type 710 on **statnum 12**, invisible
at cstat 32896, shade -128, tile 2521 (all 1,778 campaign instances). The
**sound id is `XSPRITE.data_3`** — not `owner`, which is the runtime
channel and is -1 in every campaign instance — with `data_1`/`data_2` the
near and far radius and `data_4` the volume (50 in 1,177 of 1,778).
`ambInit` **skips any emitter where data_1 >= data_2**, so getting the
radii backwards produces silence with no error.

Sound ids are attested per context from the map that *is* that context:
E3M3's sewer runs 30 (21 of its 41), E3M1's town runs 8 (22 of 35), E1M5's
church runs 50 and 32.

Gravesend now carries **38 emitters, 23.9 per hundred sectors** against the
campaign's 23.6, every one verified playable (statnum 12, data_1 < data_2,
sound set, state on).

### Conversion coverage, measured

Across the 56-map Duke corpus there are **5,968 sector effectors**, and
`bloodmap`'s Duke support converts **26%** of them — the teleport, door,
bridge and rotation families. The rest, by weight and by how many maps
they appear in:

    757  random lights                (39 maps)
    574  light switch                 (23 maps)
    474  conveyor                     (30 maps)
    427  explosive                    (42 maps)
    403  ceiling rise fall            (35 maps)
    333  floor rise fall              (40 maps)
    326  up open door lights          (27 maps)
    315  door auto close              (45 maps)
    222  random lights after shot out (17 maps)
    196  demo cam                     (38 maps)

That is a conversion roadmap ordered by what maps actually use, and it is
now a file rather than an impression. Note the shape of it: the unhandled
majority is **lighting and destruction**, not motion — the motion families
are the ones already done.

Build: 159 sectors / 1,062 walls / 230 sprites. 11/11 conformance, 16/16
contract rows.

## Iteration 21 — keys used correctly, and the Gravesend Arcade

### The key signs were wrong, exactly as reported

`knowledge/blood/design/keys-v1.json`, mined by the authoring-loop agent
across 43 maps, says what tiles 2540-2545 are: **placards**, hung beside a
door that needs that key. The campaign has 265 keyed things and **213 carry
one** — 80%. "The emblem is the message; the frame is the same on all six."

Gravesend was placing the **eye (2541) and the flame (2542) as wall
ornaments**, in a city with **zero keyed doors** — a sign promising a lock
that does not exist. The association miner had no way to know; it saw two
wall-aligned tiles that co-occur with shop surfaces. `props.KEY_EMBLEMS`
now excludes the whole range, as `props.ALPHABET` already did for letters.

`level/keysign.py` is the correct use, and it emits a placard only together
with the door it describes. A working keyed door is three things, all
measured: the door sector carries `XSECTOR.key = N`; the placard is tile
**2539 + N**, wall-aligned at **0.845 player heights** (campaign q1 0.785,
q3 0.966), repeats 32x32; and the key item is sprite type **99 + N** with
tile **2551 + N**, placed somewhere reachable — a lock with no key is a wall.

Verified in the emitted map: keyed sector with `key = 2`, one placard tile
2541, one key item type 101 / tile 2553. Emblem, door and key all agree.

### The levers were at the wrong height

`switches-v1.json` splits switches by *how they are operated*, which a raw
per-tile median cannot. Tile 1070 spans q1 0.18 / median 0.48 / q3 0.78
across all instances, but the **pushed** population — the ones a player
walks up to and uses — sits at median **0.79**, just under the campaign's
0.832 eye height. Our door levers were at 0.48, the all-instances figure.
Raised.

### The Gravesend Arcade

E4M9 measured rather than remembered: its concourse sectors run **3.86 to
4.35 player heights** where its retail units run 1.8 to 2.9. **The height
difference is the mall.** Units open at the concourse's own floor level
(step +0), a few raised half a player.

Built on `market_block_c`, the biggest unbuilt block in the city (14x10 plan
units): a 11x3 concourse at 65,536 tall, six retail units at 28,672, each
reaching the concourse through its own neck so the frontage beside it is
free for glass. Two units get E6M1 shopfronts — a display box with a raised
plinth, glazed with the masked translucent wall and XWALL from `glass.py`.
Counters at the mined set-piece height. E4M9's own ambient sound 65.

And a locked service corridor, which is where the key work lands: the door
carries key 2, the eye placard hangs beside it, and the eye key is in unit F.

Two construction notes worth keeping. **Units must stand back from the
concourse by one neck depth** — letting them touch it directly means a
shared edge that is only partly a portal, which leaves unpaired coincident
walls. And **a locked room legitimately has no walkable-at-rest exit**: the
geometry audit flags that, correctly, unless the region declares
`declared_zero_exit`. Declaring it is the honest fix; weakening the lock
would not have been.

### Naming the uses

Reading Duke's signage established the gap: DukCity names roughly ten uses
per map on its walls, where Gravesend had five venues in the whole city.
The arcade's units are named — APOTHECARY, IRONMONGER, BOOKS, TOBACCO,
STAFF ONLY — and THE ARCADE goes on the street facade beside the entrance,
because the concourse has an opening on every face, which is what makes it
a concourse. Sixteen signs, 123 letters, all placed.

Build: 182 sectors / 1,210 walls / 297 sprites. 11/11 conformance, 16/16
contract rows.

### Where to take it next

Ordered by measured gap rather than by taste:

1. **Named uses.** Still roughly nine against DukCity's ten per map, but
   most of the city's blocks are solid. `oc_block_a` (12x14) and
   `market_block_a` are the next interiors.
2. **Rectangularity.** 11% diagonal walls against 23-35%; the ceiling is
   structural until rooms can be non-rectangular (grammar request #10).
3. **No skyline.** Every mass still rises to the same sky, so the church
   tower cannot be seen from the street. A massing-layer change.
4. **Light props at 19%** against the campaign's 3% — two reasoned
   deviations cover 15 of the 20, but the interiors could lean further on
   shade.
5. **Duke conversion**: 26% of sector effectors handled, and the unhandled
   majority is lighting and destruction, not motion.

## Iteration 22 — the tool-adoption audit, and a pitched roof

Owner: the Blood grammar should be a general thing usable across projects —
check whether we are really using the tools available.

We were not. Of 31 authoring-relevant `bloodmap` modules the city used
**13**, and four of the unused ones had been **reimplemented here**:

* `doorswitch.py` against `bloodmap.switches` — and the reimplementation
  omitted `trigger_push` and `trigger_on`, which 230 and 316 of the
  campaign's 356 tile-1070 levers respectively set. **Our five door levers
  could not be pushed.** It had also rediscovered the 0.79 mount height
  from `switches-v1.json` that `pressed_switch` already returns.
* `keysign.py` against `bloodmap.keys`, whose `sign_the_locks` finds every
  keyed region *and its approach wall* automatically and reports what it
  could not sign; this project hand-specified a literal wall segment.
* `props.py`'s wet gating against `bloodmap.furniture.wet_only()` — the
  hand-listed set missed tile 546.
* `materials.py` against `bloodmap.surfaces`.

Knowledge was worse: of the 20 files in `knowledge/blood/design/`, the city
loaded **one**. `keys-v1` and `switches-v1` were read by hand and
transcribed, when the modules that consume them already existed.

`bloodmap.switches` and `bloodmap.furniture` are adopted; the levers now
carry `trigger_push`, `trigger_on` and `kCmdToggle` and are pressable.

**And a gap the audit surfaced:** `bloodmap.slope` was sitting unused while
Gravesend had **0 sloped surfaces in 182 sectors against a campaign median
of 21.7%**. The module's own guidance is that a sloped ceiling "costs
nothing but headroom", which is exactly what a nave has spare — so St
Gallow's has a pitched roof now, at the campaign's median rise of 1.29
player heights. One sloped sector is not 21.7%, but it proves the path.

The rule this suggests, written into the handoff: before writing a helper
in `projects/blood-city/level/`, grep `bloodmap/` for the noun. Four of
this project's modules would not exist under that rule.

`reports/handoff.md` written: state, disciplines, recurring traps, and the
eight next steps ordered by measured gap.

Build: 182 sectors / 1,210 walls / 297 sprites. 11/11 conformance, 16/16
contract rows.
