# Under Gravesend — the sewer as a place with a past

The owner, 2026-11-21: "overhaul of the sewers to basically make them more
interesting ... each part will look like slightly different, and there will
be like interesting things in it"; "come up with your own idea of the
sewers that will fit into ... the story around the city ... secret rooms from
like some urban legends"; "manholes like around the city, which you can blow
up to get into the sewers, basically to fall there"; "a bigger room with like
the wastewater".

What is there now (the build of 2026-11-21): a brick ring about 21 by 28 plan
units under Foundry Ward (35 by 48 m), every floor at one depth (61440), one
material (`materials.SEWER`: wall 492, floor 568, ceiling 255, water 1120),
a ledge beside a channel on the long legs, five side rooms (the pump room, the
silt trap, the east annex, the flooded branch, the station spiral's foot), the
church crypt's breach on the west, and one entry by the works. Every stretch
is the same stretch. The measured contract it was built to
(`sewer-patterns.md`) stands; this page adds what it lacks: a history, parts
that differ, things to find, and ways in from the streets.

**Room.** The owner, 2026-11-21: "You can make sewers larger even going
outside of the city area." The sewer is not bound to the city's footprint:
the Settling Hall and the brook may run out under the river front and past
the city's edge, where nothing above constrains them.

**Built so far** (all of it in `l3_sewer.py`; `l3_sewer.plan()` lists every
room with its rectangle and kind).

* **The layout follows the streets** (agreed with the owner, 2026-11-21:
  "Looks reasonable", and "We can also extend sewers towards west part of
  the city"). The ring under Foundry Ward; GRAVES BROOK, the old culvert,
  west under the row street past the church to the city's west edge; the
  OUTFALL south from the ring into the SETTLING BASIN under the plaza by the
  memorial; a south-east branch under the market road's north pavement.
  Map: `work/sewer-study/sewer-built.png`.
* **One way in per quarter of the city**: the pump station's spiral (north
  east, kept), and three manholes at the far ends of the branches -- the
  brook's west end, the plaza by the memorial, the corner where the market
  road meets the east street. The east and church manholes, the works cellar,
  its service stair and its pit into the junction are gone (the owner: "You
  are always putting these sewers enterances so close to each other"). The
  crypt breach stays a secret from the church's crypt. Every cover lies
  level with its street (8,192, checked); the market road itself is sunk
  2,048, so its manhole is on the pavement corner, not in the road.
* **A manhole** is a 768-unit shaft, a recess of 4,096 to a see-through link,
  and its cover: E4M3 sprite 130's record (type 417, debris 5, sound 314) on
  the owner's drain tile 219 at repeat 72, flat and blocking at street level.
  It lands in water, an island in the branch's channel (or the basin) at the
  water's level; the fall is 51,200 units and `conformance.py` reads 0
  damage on all three links. The blown state is not seen in a frame: the
  observer draws a link floor as planks.
* **Every corridor is E3M3's** (the owner: "I would like to do sewers more
  like in E3M3, there is that flowing water in the middle and sewers has
  that sloped ceiling"; measured off E3M3 sectors 136|120|117 by
  `work/sewer-study/e3m3_section.py`): 2,048 wide, a 512 walk each side of a
  1,024 channel that runs 2,048 lower; the walks' ceilings slope 8,192 down
  to the wall (heinum 4,096), the channel's is flat, 28,672 over the walks.
  The corners are pools at the water's level. Where a branch's channel
  enters a corridor from the side (the brook into the west leg, the
  south-east spur into its drain), the walk on that side is a FORD at the
  water's level, which the water runs through and the player wades.
  The brook is the same section in rubble (110) and dark stone (253).
* **The water flows** (`l3_sewer.FLOW`): the north channel east, the east leg
  south, the south channel west, the west leg south, out of the south-west
  corner down the outfall, into the basin and west toward the river; the
  brook east into the ring; the south-east branch north into the ring. E3M3's
  shimmer on every water sector.
* **Light cuts respect the vault.** The cutter cuts a sloped sector only
  ACROSS its slope (`overlays.cut_sectors(slopes_across=True)`: every new
  edge perpendicular to the hinge, every piece keeping a stretch of the hinge
  as its first wall, so each piece is the same plane -- the owner: "be
  careful about slopes, I think we still can split it perpendicularly"); the
  light stage traces each sloped walk along its hinge and cuts it where its
  light changes (`light_stage.band_slopes`): 13 walks into 58 pieces, every
  shared point checked level. A current and a water depth count as surface
  effects (`overlays.SHADE_ANIMATION`), so the channels beside the walks are
  cut by light too.
* **Cutouts with something in them** (the owner: "add some decorative
  elements and cutouts with something"; `l3_sewer.NICHES`, `NICHE_DRESS`):
  twelve niches a unit long and half deep in the walks' outer walls, their
  ceilings under the vault's low edge so a lintel shows -- a valve wheel on
  the owner's technical wall (499), barrels (925, the toxic 201) that break,
  a skeleton on a chain (689) over bones, twin pipes (211). Every sprite is
  a campaign record; the barrels are lifted by half their drawn height and
  the skeleton drawn at 40, or the lint reads them sunk.
* **Chains may run into the ceiling** (the owner: "lanterns on chain, you
  can simply let it sink into ceiling and it looks good"): the light stage
  lifts a chain lamp that is longer than the room allows until its foot
  clears the floor, keeping the lamp itself under the ceiling, so Graves
  Brook hangs its chain lamps (641) where it used to fall back to flat ones;
  `sprite_fit` reads their chains as 19% through the vault, which is the
  point. A sewer corridor's walks, fords and channel are lit as one room
  (`lights.room_key`), or its strips are each too narrow to hold a light.
  The bones niches are tall inside (30,720) and their skeletons (E1M2's 689
  at 60) hang whole; a sprite may not stand above its sector's ceiling.
* **The Settling Hall** (`l3_sewer.HALL`, its own layer `settling_hall`
  under the plaza by the memorial): the outfall runs into the GALLERY, an
  E3M3 corridor along the hall's north wall at the sewer's level (its water
  west; the memorial manhole lands in its channel). Off the gallery's south
  walk the hall drops 2.4 bodies to three settling tanks (water at 106,496,
  barely moving) with walks between and a quay down the west side, and the
  CIRCLE QUAY along the south where the Cabal keeps its circle: six of the
  owner's standing candelabra (580) round a pool of blood, two of E3M3's
  cultists. A stair of ten steps climbs from the circle quay to the gallery
  in a column of its own. The hall is lit as one room: six chain lamps over
  the tanks, their chains in the roof. The drop from the gallery does no
  harm (45,056); there is no way back up but the stair.
* **Two secret rooms off Graves Brook** (`l3_sewer.SECRET_ROOMS`, its own
  assembly `secrets`), both counted (the level's total is now 5):
  OLD MOLLY'S NEST, through a crawl-height arch (14,336; crouching clears
  13,376) in the brook's south wall at x 5, a low lair of rubble and bones
  with a gill beast and a doctor's bag; and THE PLAGUE PIT under the
  churchyard, behind a cracked stretch of the brook's south wall at x 25: a
  wall crack (408 on 1127, only a blast breaks it) sends wire
  `sewer:plague-pit` (channel 109), which opens the hole and fires three
  charges inside; the pit is half a step down, two skeletons on chains over
  bones, a life seed. THE HOLE IS RAGGED (the owner, 2026-11-22: "Blown out
  holes are usually using sloped floor and ceiling and usually aren't
  regular, our look too blocky"; `bloodmap.breach`, from the campaign's 185
  crack-opened sectors): four Z-motion pieces with slanted seams, each
  sloping its floor and ceiling about a slanted edge, the middle two a body
  tall and the end two low rubble shoulders falling away from them; its
  faces are the wall's own stone. Every piece is solid shut (ceiling slope
  at least the floor's), and the hole's top sits under the walk's vault
  (`work/sewer-study/hole_check.py` reads it back). The pieces are typed
  after the door pass (`l3_sewer.LATE_TYPES`), like the crypt breach:
  framed as a door the seal stood a head two bodies tall; and the sewer's
  mouth lining leaves a moving sector alone (it had lined the hole in
  tunnel tile 194). The crypt breach into the west leg and the arcade's
  cache are built the same way now (`breach.lay`; `l3_church.breach_pieces`,
  `l3_mall.secret_pieces`); frames of both, shut and blown,
  `work/sewer-study/holes/holes-sheet.png`. Both rooms are unlit (`lights`
  rule `sewer/secrets/`: nobody keeps a lamp there), dark between the
  brook's lamps and the shade's flicker. Two faults found on the way, both
  fixed in general: an exploder wears the flame tile and the light model
  counted it as a lamp (`light_kinds.sprite_lights` now skips what the game
  never draws, `visual.HIDDEN_TYPES`); and the church's face pass painted
  every solid wall on the church's outline at any depth, the west leg's walk
  and the pit included (`facade_pass.face_landmark(deepest=)`).
  Frames: `work/sewer-study/secrets/secrets-sheet.png` and `hole-sheet.png`
  (`work/sewer-study/secrets_look.py`).
* **The Weaver's Cellars, a spider lair** (`l3_sewer.LAIR_*`, `spider_lair`,
  `dress_lair`; study `knowledge/blood/studies/spider-lair`, mined from all
  1,587 single-player maps by `work/spider/lairs.py`; the owner, 2026-11-22:
  "We can also add spider lair somewhere, similar to E2M8"): the old
  tannery's cellars under the saloon row, off Graves Brook's north walk at x
  11.75. A passage with E2M8's web (410 on 1069) across its mouth, which a
  shot breaks; a cobblestone hall (411, earth 270) with its corners knocked
  off; three brood alcoves walled in silk (1057), each with E2M8's cocoon at
  its own scale (so the alcoves are E2M8's size, 1,024 deep); wrapped
  victims (416 on 1059, unwired) and web fringe (1068) from the ceiling; six
  brown spiders and their mother on the ceiling upside down (E2M8's records,
  cstat 8); E1M2's bones; a bundle of TNT in the east alcove, for the plague
  pit's crack. It is not a counted secret. Measured layers 3 (campaign
  p25 2, p50 5).
  **Blind critique** (`python -m tools.critique verdict spider-lair`; four
  readers a round, pose set `lair` in `look.py`): every round's
  recognition reader named it a spider nest without words. Rounds 1-3
  did not pass, each on concrete faults, now built in:
  - **Nests:** single eggs in shallow silk boxes read as carvings or
    ghosts. Every alcove is now a deep, low nest with clustered eggs of
    several sizes and cobwebs on its lintel; the north one has E1M5's
    carved spider (314) over it.
  - **Victims:** E2M8's wrapped victim (1059) read as a post, a column, a
    palm tree or a light fitting at every length tried. One stays, short;
    two are E1M2's chained skeletons.
  - **Torn silk:** the 1058 sheets on jambs and the pillar read as plaster
    panels, so they are gone.
  - **Spiders:** the ceiling spiders and their mother are seated by their
    drawn top against the ceiling.
  - **Pillar and light:** a rough pillar breaks up the view, and two wall
    torches (E2M1's) give pools of light, with the lair's lamps at 0.55.
  - **Floor:** E2M1's skull piles stand, where E1M2's flat bones vanished
    into the earth.
  - **TNT and passage:** a TNT box on the hall floor at the east nest's
    mouth, and the passage in the hall's stone.
  Round 4 (still no pass, all four readers at 3 of 5) found two more:
  - a shovel stood in the east nest, hung there by the city's generic
    dressing (`dressing.dress`). The lair's rooms are now
    `intent={"kind": "furnished"}`, as the station's are.
  - the passage web "lies flat on the floor". The owner: "Check web in
    other levels what are we doing wrong". All 693 webs in the corpus
    (`work/spider/webs.py`): the commonest is opaque (cstat 401; only 181
    are translucent, E2M8's 915 among them), and hung ON the opening's
    line at its full width with its foot on the floor. Ours was E2M8's
    translucent one, 256 inside the passage: the floor showed through it.
    It is now hung the corpus's way and reads as a sheet across the mouth
    (`work/spider/webside_final/sheet.png`). NBlood seats a wall sprite as
    `drawn_extent` does (`engine.cpp:5393`).
  Round 5 (recognition 4 of 5, the others 3; only blocking: a floating
  silk sack and even light): eggs now stand at the pillar's foot; all
  three hanging dead are chained skeletons; and the lair's torches are
  back at full strength, so the light stage cuts pools into the hall's
  floor (shade 0-11 at the torches, 26-33 between; at 0.35 the hall was
  one sector at 33).
  Round 6 (sense 4 of 5 with nothing blocking; the rest 3): webs flat on
  the two corner walls without torches, strands cascading inside each
  nest, a find at each nest's back (life essence, shells, gasoline), finds
  seated by their drawn foot. Its one shared blocker was the nests' silk
  walls ("museum vitrines", "cardboard boxes"), so the nests are now the
  hall's rough stone and earth. Not yet read by a seventh round. Still
  wanted: a less flat ceiling, a larger spider panel, web mats in the
  corners, darker walls.
  Two frame faults the rounds found, fixed in general:
  - the observer drew a lit torch as the bare sconce (`visual.light_torches`,
    `view.cpp:2930`);
  - the critique packet numbers views alphabetically by pose name, so a
    brief must give that order.
  Frames: `work/spider/look9/lair-sheet.png` (`work/spider/lair_look.py`).
* **Open:** the gallery's step face over the tanks is one tall bare wall
  (a sewagefall there wants the wall below the outfall's mouth in 1120,
  panned, and a per-edge texture the layout does not give); the walks carry only floor debris: anything hung on their walls
  (E3M3's drips at 1.21 bodies, its moss, the vault grates) lands in the
  sloped ceiling, because the detail runs read a flat ceiling's height; and
  E3M3's X-brace pilasters (487) are wall textures in E3M3, a wall split we
  have not made. Not built: the stockyard drain, and the later legends
  (the Ghost Station through the pump station's hatch, the Toshers' Cache,
  the Rat King's shrine, which wants the stockyard drain). The blown seal
  is seen in a frame only with its sector opened by hand; nobody has blown
  it in the game.

## The history, oldest first

Gravesend's sewer was not built; it accreted, and each age left its own
masonry. That is what makes one stretch unlike the next: a player walking
from the ring into the brook should feel he has gone back fifty years.

1. **Graves Brook** (before the town). The stream the town is named for ran
   past the old burial ground at Old Crossing and down to the river: the
   graves' end. It was culverted when the town grew over it -- rough rubble,
   low, wet, the oldest stone in the city. It still runs under Old Crossing to
   the river, and it passes the church: the crypt's breach opens onto it.
2. **The Foundry Main** (the boom). The brick ring the works paid for:
   engineered, ledge and channel, iron grates, gas pipes along the walls.
   What the city has now.
3. **The Pumping Station** (the boom). Below the works' pump machine hall:
   the machines that lift the low sewer to the river outfall, their valves
   and sluices. The pump room exists; it is the station's floor.
4. **The Stockyard Drain** (the boom). The slaughterhouses on the river
   front wash down into the Main through their own outfall: a channel that
   has run red for forty years.
5. **The Metro that never was** (the last good year). Under the foundry
   underpass a passage ends at the barred mouth of a metro tunnel that was
   started and abandoned (`character.PLACES["foundry underpass"]`). The
   service hatch from it into the sewer is the way into its one finished
   platform.
6. **Now** (three weeks of quarantine). The Cabal works below the city too.
   What was carried out of the Aldermack went down through the works into the
   settling tanks; the summoning is done where all the city's water meets.
   The sewer workers (toshers, who lived off what washed down) left in a
   hurry.

## The parts

Each part has its own material, height, water and light, so no two parts a
player walks between look alike. Exemplars are filled from the campaign study
(`work/sewer-study/`); a part is studied (`tools.study`) and named on the
place (`level/character.py`) before it is built.

| part | what it is | how it reads | water | light |
|---|---|---|---|---|
| **The Settling Hall** | the big wastewater room the owner asked for: where the Main, the brook and the stockyard drain meet, three long settling tanks between walks, outfall pipes pouring in high on the walls, a tall vaulted roof (the city's "cathedral" of a storm chamber) | the tallest room underground; walkways and bridges over open sewage; the Cabal's circle on the central platform | sewage, deep in the tanks, a current along them | dim, red from the circle, grey pools under the few panels; restless shade |
| **The Foundry Main** | the ring, kept, made legible: each corner its own landmark | engineered brick, ledge over channel | a channel | panels in their rows (as built), dark between |
| **The Pumping Station** | the pump room grown into a machine floor: pumps, a valve gallery whose two wheels drain the flooded branch | machinery tiles, rails, gauges; lit by technical panels | drained by the valves | bright, steady (the only steady light below) |
| **Graves Brook** | the old culvert from the crypt's breach west and south toward the river | rubble walls (the crypt's 110), lower, rougher, curved by sloped ceilings | waist-deep, flowing | almost none: candles left at a shrine, a grate of street light |
| **The Stockyard Drain** | the slaughterhouse outfall into the Main | tiled channel, hooks and carcasses at its mouth | blood, panning, drags the player | red |
| **The Toshers' Den** | where the sewer workers lived: straw beds, a stove, lanterns, their finds | timber props, a doorway in the brick | dry | one lantern |

### What the campaign gives each part (the study, 2026-11-21)

Read with the scratch notes and frames in `work/sewer-study/campaign/`.
Heights in bodies (16960 z, about 1.7 m).

* **Settling Hall.** Blood's big wastewater halls get their height from
  TIERS, not one tall ceiling: E3M3:15 (25 x 27 x 14 m) stacks a pool, a
  main walk 5.3 bodies up, catwalks at 3.4 more and a top gallery, with
  trusses (487) and X-braced hatch floors (191) overhead and lifts between;
  E1M8:243 (45 x 63 x 7 m) is plank walks over a sea of sewage (1120).
  Walks stand half a body over the water. The inflow is E3M3:173/174's
  **sewagefall**: a low pipe slot (0.85 body) with a panned floor spilling
  down a wall of 1120 panned in y (-20) into a pool 2.4 bodies lower, the
  way on under the fall. The ambush is E3M3:210's: walking in wakes axe
  zombies lying in the sludge (`kDudeZombieAxeLaying`).
* **Foundry Main.** E3M3:271's shimmering ledge: the walk 0.48 body over a
  1120 channel panned at 8, water sectors with a shade wave (7, amplitude -4,
  frequency 4), X-brace pilasters (487) every few metres, headroom 1.7 to
  2.4 bodies; E3M3:43's stair descending into the sewage in eight steps.
* **Pumping Station.** E3M3's valve pair (sprites 107/108, sectors 97/99):
  two shade-0 niches with a cart-wheel (982) as a toggle switch, joined by a
  combo that slides the gate; a second combo opens a secret behind the
  player 60 ticks later. Its machinery room E3M3:263 (2462/2463/2477
  machines, DANGER plates 933/942) and its rotor key (button 328 turning
  `kSectorRotate` sectors).
* **Graves Brook.** E6M6:128: a brick channel opening into a 6.6-body shaft
  with a balcony four bodies up; E3M3:101's swim tubes (1.4 bodies, bubbles
  668, weed 660/664).
* **Stockyard Drain.** E1M8:389's River Ride: a sector-wide panning floor
  that carries the player (speeds 60 to 255, drag on), with E1M8's blood
  pipes (977) and hanging corpses.
* **Toshers' Den.** E3M3:16 and E3M3:265: straw (515), bodies (2333/2334),
  rats, drip generators; the sliding bed is E3M3:265's.

Secrets in the campaign's sewers are signposted three ways: a slightly wrong
colour (E3M3's off-colour support), one damaged copy of a thing that
otherwise repeats (E3M3:133's broken cable box, a 1127 crack that a blast
opens), or a reward the player can see. Each legend room below takes one.

### The ways in from the street: manholes you blow open

The owner: manholes "around the city, which you can blow up to get into the
sewers, basically to fall there", and then, exactly: "a floor aligned sprite
over hole as a cover that is destructible by explosion, not wall crack. Like
a normal manhole on the street you can drop into". So no wiring at all:

* a **hole** in the street the size of a manhole, open all the way down: a
  shaft to a sewer stretch under that street, landing on a walk (not in a
  channel), with a way to climb back or a route on;
* a **cover** over it: a FLOOR-ALIGNED sprite of a destructible thing,
  lying at grade on the hole's rim, blocking so it can be walked over, wearing
  a manhole cover tile (the owner's 191, a metal hatch with an X brace, or a
  round one), a little larger than the hole so no edge of the hole shows;
* an explosion destroys the cover and the player drops in. Nothing else
  changes: the hole was always there.

From the engine (NBlood `actor.cpp` `thingInfo`, damage multipliers in the
order fall, burn, bullet, explosion, drown, spirit, tesla): the **explode
object, type 417** (`kThingObjectExplode`) takes `0, 0, 0, 256, 0, 0, 128` --
nothing from bullets, falls or fire, full from explosions, half from tesla.
The crate face (405) and the wall crack (408) take explosions only, but the
first is a wall thing and the second the breach trigger; the gib object (416)
breaks to bullets too. Destroyed, a 417 sends OFF and throws the gibs its
data fields name (`triggers.cpp`, `actActivateGibObject`). Build's floor-height
check counts a floor-aligned sprite with the blocking bit as ground
(`clip.cpp`, `getzrange`, the floor-sprite case), so the cover is walked over
until it is blown. Still to settle: the drop a player takes without harm,
and whether the campaign lays a 417 flat anywhere (the study is asked).

The hole under it is a room-over-room mouth into the sewer
(`build_skeleton.mouth_pair`, see-through) or a shaft, round enough (an
octagon) to read as a manhole once the cover is gone: the yard grate was a
bare square hole until 2026-11-19 and the owner found it "weird".

Four or five of them, each over a different part, so blowing one is a choice
of where to arrive. The campaign never lays a breakable grate flat (its five metal
grates, type 411, all stand on walls), so the flat cover is ours; its
nearest relatives are E1M4:368 (an invisible explode object in a floor that
drops 11.6 bodies when blown) and E4M4:92, a small floor hole into sewage
1.7 bodies down with a water link below -- the campaign's own manhole, in an
outhouse. Foundry Ward (into the Main), Old Crossing (into the
brook), Market Slip (into the stockyard drain), the theatre's back street
(into the settling hall's gallery, the way the Cabal's carts went). The yard
grate (`l3_foundry`) stays a grate you cannot open: the owner did not want two
entries side by side.

## Secret rooms, after the city's legends

Every city has stories about what is under it. Gravesend's, each a secret
the campaign's own ways of hiding would allow (the study lists how E3M3 hides
its five: a support of a slightly different colour, a wall that opens while
you turn a valve, a broken-looking box, a bed that slides, a button behind a
plant):

* **Old Molly's Nest** -- "a thing lives in the brook, the size of a man,
  that took the dogs". A dead-end of the brook choked with bones, dog collars,
  a nest of rags; a gill beast that is not just any gill beast. Found by
  swimming under a low arch where the water is darker.
* **The Ghost Station** -- "there is a finished platform down there with the
  lights still on". Through the metro hatch: one tiled platform, a lettered
  station name, benches, an unfinished tunnel mouth bricked up, the lights
  burning for nobody. The reward is on the platform; the way in is a hatch in
  the pump station that looks like every other panel.
* **The Plague Pit** -- "when they dug the brook they found the old burials
  and bricked them in". Behind a cracked stretch of the brook's wall near the
  crypt breach: a low vault of bones, older than the church. Blown open, like
  the breach it neighbours.
* **The Toshers' Cache** -- the den's bed slides back on what the workers
  kept from what washed down (E3M3's sliding bed, said by players to be one of
  its best).
* **The Rat King** -- "a knot of rats tied by their tails, under the
  stockyards". A small shrine in a pipe niche of the stockyard drain, candles
  round a knot of rats; the cult left an offering on it.

## Order of work

1. The study (running): the campaign's sewer spaces, set pieces, secrets,
   breaches and largest wastewater halls; the community maps' ideas.
2. The Settling Hall -- the hero room the owner asked for, and the place every
   part leads to.
3. The manholes: one first, proven by a frame at rest and blown
   (`tools.mechanism_look`), then the rest.
4. The brook, the pumping station's valves, the stockyard drain.
5. The secret rooms, each with the campaign's own secret wiring
   (`catalog wiring secret`).

Each part is studied, named on the place, built, looked at, and put to blind
readers (`tools.critique`) before the next.
