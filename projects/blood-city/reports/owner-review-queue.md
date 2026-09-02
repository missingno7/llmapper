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
