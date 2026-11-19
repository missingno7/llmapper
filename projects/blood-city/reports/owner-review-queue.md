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

**Open, said in the same walk and not done**

- "When you look at that canteen facade it is cutting off middle of windows,
  we should align it properly." Measured, not fixed: the yard's north face
  (walls 838-841, y 15,360, x 50,176..53,760) wears tile 393 at `x_repeat`
  9 on its 1,024-long walls, which is 72 texels a wall where the tile is 64
  wide. So its painted windows stand every 910 units and the doors, which
  are on the 1,024 grid, cut them. `texture_frame.frame_map` sets the
  natural scale (64 texels a wall, `x_repeat` 8) for these walls; something
  after it, or the face's length of 3.5 bays (one corner is chamfered), is
  squeezing four tiles into it. Find which pass writes the 9. The raised
  doors also end partway up the window row, and the torch between them
  hangs across a window.
- "Canteen should look more like a canteen." Not started. It has no study;
  by this project's rule it gets one before it is rebuilt.
- The avenue mouth of the underpass cuts the facade's painted windows too.
- The breach that is to be the foundry's staged moment is not built; the
  wire `foundry:staged-moment` is in the plan with no ends.
