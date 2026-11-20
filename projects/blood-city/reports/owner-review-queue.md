# Owner review queue

Questions that are the owner's to answer, each with a recommended
default already in the build, so nothing is blocked on a reply. An A/B
question carries the fixture that shows both options passing every gate,
because "no invariant separates them" is shown and never asserted.

---

## 1. Should Gravesend have street lamps at all? (from slice 2i, still open)

**Recommended default, and what is built:** yes, fourteen of them, as
**wall-mounted sconces** (tile 510) on the pavement islands, at Blood's
own indoor lamp density.

**What the corpus says.** Blood does not light its streets. Across the
43 campaign maps and 51,277,134,846 square units of outdoor ground there
are **zero visible outdoor lamps**. E3M1's 45 bright outdoor sprites are
sound generators wearing an editor icon -- cstat 32896, whose `0x8000`
bit is INVISIBLE, statnum 12, types 708 and 710. Its streets are lit by
the sun and the shadow field and by nothing else.

**Why it is built anyway.** `city_plan.AREAS` asks for lamps at three
places by name, and the supervisor's slice-3 brief says lamps stay,
recorded as a CHOICE claim. So they are: Blood's indoor density (a
per-map median of one lamp per 187,624,103 square units), Blood's own
sconce, Blood's own mounting, and a shade delta of -6 that is OURS and
is written as ours -- half the measured field step, so a lamp lifts half
a shadow level rather than cancelling one.

**If the answer is "no":** delete `LAMP_*` from the emitter and the
`lamp_delta` facts go with them; nothing else changes, and the sun does
all the work as it does in E3M1.

---

## 2. Do the shells' doors open, and onto what? (A/B, with the fixture)

Nine street doors exist, each a sector of its own carrying sector type
614, each filling an opening in its facade. **Nothing opens them.** Every
`link` fact says `realised: false` with the reason -- the door carries
the rx and no switch, generator or key pickup carries the matching tx --
and five of them additionally carry a `key` fact for the citywide
circuit's five key gates, also unrealised.

* **A, they are doors.** Wire each to a switch on the facade beside it,
  and the five gated ones to keys placed on the circuit.
* **B, they are thresholds.** Drop the sector type; the mouth stays open
  and the shell reads as a shopfront rather than a house.

**The fixture that separates them:** `tests/test_rule_two.py`. Both
options pass every geometry gate, every join gate and the frames gate,
because neither changes a wall. They differ on exactly one reading: with
the type, the light domain reports **9 eligible** and Rule 2 has a
population; without it, **0 eligible**, and the manifest goes back to
saying UNTESTED. That is the invariant, and it is why A is what is
built.

---

## 3. The plan's circuit is in a grid the solve does not use

`city_plan.CIRCUIT` has 16 legs and their coordinates are in the 58x56
plan grid; the envelope solve produces 72x60. So the circuit's legs
**are not checked against the built map**, and the build says so rather
than checking something else and calling it the circuit.

**Recommended default:** re-express `CIRCUIT` in the solved grid, as a
sequence of surface ids rather than plan-unit coordinates -- a leg is
"the avenue between Theatre Row and Market Street", which survives a
re-solve, and a coordinate does not. That is a change to the plan and so
it is the owner's, not mine.

---

## 4. What is behind the nine doors

Each shell has one room, one storey, no contents. The L3 interiors the
brief names -- church, foundry, mall, market, theatre, shed, sewer --
are **not re-parented**; the rooms are empty boxes at the right size and
in the right place, entered through a real opening.

**Recommended default:** re-parent them one at a time, each under the
island whose shell it belongs to, and each with its own read-back
sentence, so a failure names one building rather than the city.

---

## The owner's walk of 2026-11-20 (Foundry Ward and the underpass)

Recorded by the agent that was told these things, the same night. "Done"
means built and looked at in a frame by that agent; nobody has walked the
result.

**Done**

- "Passageway looks ok, but simple, these bars are just bars, you can't
  really tell what it is." The bore behind the bars is lit and wears the
  board ARRIVALS DEPARTURES (431) on its back wall; TICKETS (943) hangs
  beside the bars and EXIT (761) toward each stair
  (`build_skeleton.dress_underpass`).
- "These low doors ... something what is not finished properly" (standing
  at X 51969 Y 17417, ANG 1553). They are the works canteen's two doors,
  which were 16,384 high: lower than a body and lower than 87% of the
  campaign's ceiling doors. They are 31,744 now, like every other venue's.
- "That walk-in bay looks like just a random cutoff in the building. You can
  put there bars ... bloody stuff behind bars." It is a cage: bars across a
  reveal in its mouth, three corpses on chains (690, 698) over a pool of
  blood (956, 730), the two barrels kept.
- "When you look at that canteen facade it is cutting off middle of windows,
  we should align it properly." Two faults in `texture_frame.frame_map`,
  both city-wide. A run took its scale from its FIRST wall, and on the works
  block that was a 724-unit corner chamfer whose repeat rounds 5.66 to 6, so
  the whole facade was drawn 6% fine (windows every 910 units). And a
  district run took its world-grid phase once and carried it round every
  chamfer (45.25 texels each), so every face after the first stood off the
  grid. The scale is now the run's total, snapped to the natural one on a
  district run, and each straight leg of a district run is phased to the
  world grid. The canteen's face is 64 texels a bay at panning 0: a door or
  a hatch takes a whole window and the piers keep theirs. The torch beside
  the door hung across a window and is moved to the jamb.
- "Canteen should look more like a canteen ... give it some unique style,
  like rat dogs (similar to E1M4)." It is RAT DOGS: studied first
  (`knowledge/blood/studies/ratdogs-stand/notes.md`), then rebuilt. Its west
  door is a serving hatch at half a body with E1M4's grill on the sill (a
  burning damage sector with a flickering glow, rats and steam on it, fans
  over it); the word RAT DOGS is over it in E1M4's own lettering; inside it
  wears E1M4's kitchen (rusted metal, diamond-plate floor, a fluorescent
  tube), the counter is grill iron with rats on it, and a wooden table
  stands where the display pedestal was. Frames: `look.py --set canteen`.
  Not walked, and no blind reader has seen it.
- "Interior is bit empty, I would add dine in and maybe freezer to the
  back." Studied in `knowledge/blood/studies/canteen-freezer-dining/`
  (E1M3's freezer, E3M2's meat rooms, E1M2's station buffet). The main
  room is E1M2's buffet: marble chequer, clay over a dark stone base, three
  round stand-up tables (the campaign seats nobody at a table), and the
  kitchen's wall over the counter (pans, EMPLOYEES MUST WASH HANDS, a fire
  extinguisher). The back room is a walk-in freezer behind a metal push
  door: E1M3's riveted floor and frosted walls, four carcasses on hooks
  dripping blood, pools under them, the butcher's saw, tongs and axe on
  the wall, and a butcher (E3M2's fat zombie) in place of the axe zombie.
  Not walked.
- "You can even change shape of the building." The dine-in took the old
  back room's floor (now 4,096 by 4,608, 19 M against a destination's
  14 M; five tables) and the freezer moved north into the place of the
  rail-yard backdrop box, so it has no window onto the sky. The facades and
  the yard are unchanged. Not walked.

- "Back to RAT DOGS" (after the showcase). The showcase's blind reader said
  of the old iron island, in rounds 1 and 2, "the low grill reads as a
  box ... no clear place to order or eat", and of the yard "add a small Rat
  Dogs outdoor seating area". The counter is Blood's half-body wooden bar
  (`fixtures.BAR`) running south from a pass, on the door's left, with
  stools along its face and the cleaver and rats on it; the kitchen behind
  it has a griddle range under the pans (iron 376, fans over it); two
  stand-up tables stand out in the yard. Round 3 (counter only): "rat-meat
  diner", but blind "bar interior"; round 4 (griddle added): "rat-infested
  diner", blind "diner counter", recognised. Still said: the griddle reads
  as a grey prep island, not a flat-top grill, and the yard's hatch is easy
  to miss ("a brightly lit awning"). Not walked.

- The market hall (owner: "focus on something else in the city ... free
  hand"). Picked because the showcase's blind reader did not recognise it
  (round 2: "tiled room with central counter"). Two faults of naming, not
  of taste: its grocer's windows held tile 2937 as "a roast" (the owner's
  "dead cultist"), and its east shelf bank wore 202 (the owner's "worn
  wall/facade texture"), which is the "barrier" the reader saw. The middle
  bank is a half-body market stall now, stocked from both aisles, with E3M2's
  carcasses hanging over it and two chain lamps (641), on a lit floor pool;
  the aisles are a step darker. Rounds 5-8: "indoor meat market", blind
  "butcher's stall", sure 5, four rounds running. Next said: a timber-framed
  stall front. `tests/test_goods_names.py` now holds every goods name to the
  owner's word, and `templates.tile_is` refuses a shelf that is not one.

- Gravesend Station has a front on the avenue. The north-lane door was
  "a brick building entrance" to the blind reader: a 2,048 slot in a long
  wall on a lane where no view shows a front. The avenue, the city's long
  axis, ended in a blank end wall a few units south of the platform's east
  end, so the station now closes the avenue's vista
  (`l3_station.avenue_front`): an ashlar front (427) with twin doors under
  iron canopies (floor-aligned 438, as the carriage roof), GRAVESEND over
  one and STATION over the other, a clock tower on the seam between the
  districts, lamp posts before it; behind, a hall, a stair up 1.21 bodies,
  and a concourse that walks out onto the platform beside the engine. The
  north-lane door still works. Rounds 9-12: with the letters, "Gravesend
  Station forecourt"; with signs hidden, still "lamp-lit cobblestone
  courtyard". Open: a portal with real architectural presence (an arched
  opening or a train-shed roof seen over the front), and a lit interior
  seen through the doors. The street lamps in item 1 are not tile 510
  (the owner's "metal plate"): that was slice 2's choice and is retired;
  the city's posts are 640.

- "Train station facade looks bad, there are building textures with
  windows and they are even cutoff ... maybe you can even do some arcs."
  The windows were the bands over the two doors: a roofed doorway onto an
  open street draws the wall over it to the STREET'S sky, in the street's
  facade tile. The station has a forecourt now whose sky is the front's
  top, and the front is its far wall: ashlar (427) with two pointed arches
  (E1M2 s207's form: two half-sectors pitched from spring to apex), the pier
  between them in meander stone (409) under the clock, GRAVESEND and
  STATION over the arches, lamp posts, lit floor before each arch. Blind,
  rounds 15-17: "train station entrance", three running.
- "Rework that welcome to Gravesend ... bigger memorial with water", then,
  of the first try (a block of falling water): "there should be that
  combination of stone and water, to give it some shape", pointing at the
  owner's street memorial in RABIDN09 (read for ideas, not copied): a rim
  of light stone (253) round a pool, a dark backdrop with the ram skull
  (1348) and WELCOME TO GRAVESEND, a dark box with one narrow moving fall
  (1005, E3M6's panning) and foam (1037), two drums of meander stone (409)
  in the water with crouching statues (536). 8 by 7.5 plan units; the old
  fountain is gone into it. Blind, round 17: "stone fountain in a
  courtyard". Open, said: the square around it lacks a destination.
- "Haven't you spot that these statues are floating mid air?" No. Tiles
  drawn to be centred (art y-offset half their height: statue 536, steam
  754, smoke 672, the eye key 2553) were written without cstat 128 and the
  renderer lifted them. All five are centred now, as the campaign writes
  every one of them, and `tools.sprite_fit` reports `lifted` sprites (a
  standing thing in the air where the campaign stands that tile on its
  floor); it had declared the threshold and never used it.

**Open, said in the same walk and not done**

- The avenue mouth of the underpass cut the facade's painted windows. After
  the facade fix below its wall (850) is two whole bays at panning 0, so by
  measurement it takes two whole windows; not looked at in a frame.
- The breach that is to be the foundry's staged moment is not built; the
  wire `foundry:staged-moment` is in the plan with no ends.
