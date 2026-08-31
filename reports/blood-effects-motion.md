# One motion, three design objects

The roadmap's first experiment for this phase: find a door, a lift, and a
third Z-motion mechanism, **ignore their names**, and report what is the same
about them and what is not. If the distinction can be explained from map
context, the abstraction boundary is in the right place.

It can. Across 43 campaign maps, 2027 moving sectors, the low-level
representation is the same for all of them and the fields do not tell you what
any of them is.

```text
bloodmap/effects.py            the reading: four planes, one vocabulary
reports/blood-effects-motion.json
work/_effects_mine.py          the miner
tests/test_effects.py          21 tests
tests/test_switch_contrast.py  15 tests
                               19 of 19 mutants caught across both
```

## The vocabulary

A reading over what `doors.py` and `assembly.py` already record — no new
geometry, no parallel framework. Four planes, kept apart on purpose:

```text
primitive   move_floor_z  move_ceiling_z  translate_xy  rotate_about_axis
carried     what rides the motion, and in what numbers  (assembly.py)
embedding   what the motion does to occupancy and reachability
style       a face unlike its surround, a signifier beside it, keyed or not
```

`design_object` takes the **embedding and nothing else**. There is no way to
pass it a sector type, because a sector type is the thing it must not consult.

## The embedding asks two questions

Both spatial, neither a field.

**Does the motion change whether a body fits through?** Asked symmetrically. A
leaf that rests open and shuts changes what fits exactly as much as one that
rests shut and opens, and deciding which is "the" direction is a reading
dressed as a measurement. The first version of this asked only "does it open",
and filed every rest-open mechanism under *neither*.

**Does it carry a body between two standing levels?** The floor has to travel
further than a body can step (6656, NBlood's ClipMove limit) and arrive at two
different neighbours' floors.

## What the fields say against what the space says

```text
fields say   n      changes what fits   carries between   both   neither   undecidable
z_ceiling   646            540                  –           –      102          4
z_floor     541            122                168          95      152          4
z_split     180             56                 39          47       32          6
slide       396              4                  –           –        5        387
rotate      263              2                  –           –        1        260
```

**Naming a mechanism from the surface that moves gets 40% of them wrong** —
471 of 1179. Not a rounding error and not a tail: 122 sectors whose *floor*
moves change what fits through a portal, and 102 whose *ceiling* moves change
nothing at all.

This is the same result one family over. 88 instances of the auto-rotating
primitive and only 6 are doors; the rest are a carnival ride, station rotors
and fans (`projects/blood-city/references/auto-rotators.md`). Same machine,
different design object, decided by space.

## The three, described without their names

Typical instances, chosen at each class's median travel rather than its
extremes — the first cut of this picked the largest in each class and produced
four freak shafts.

**A thing whose ceiling rises 26624 and whose gap goes from nothing to
26624.** Two neighbours, worked from a channel. At rest a body cannot pass; in
the other state it can. E1M3 s312, E1M8 s397, E2M2 s227 and s229 are all this,
to the unit.

**A thing whose floor travels 32768 between two neighbours' standing levels,
with a gap that admits a body throughout.** Nothing about it opens or closes;
what changes is which floor a body standing on it is level with. E2M2 s276,
E2M3 s18, E2M5 s769, E2M6 s0 — and note the last is worked by walking into it,
the one before by pushing its wall.

**A thing that moves and never changes either.** E1M3 s108 and s109 open to
14336 and stop. That is above a crouching body (13376) and below a standing
one (16960): a way through that a body has to duck for, and one that the
"does it admit a body" question answers *no* about in both states. 46 of the
292 in this class are that shape.

The first two are what a player calls a door and a lift. The third is not a
degenerate case of either, and calling it one is what a name-first reading
would do.

## The reading declines where it should

662 sectors come back `not decidable from z alone`. Both embedding questions
are about a vertical opening, so a sector that only slides or only turns has
not been tested — and "untested" and "neither" are not the same claim.

Filing those 662 under *neither* is the first thing this experiment did, and
it made the residue look like the largest class in Blood. It is now an
explicit outcome, which means the reading can decline, which is the only
reason to believe it when it does not.

## The residue

292 sectors move in z and neither open a way nor carry a body:

```text
open throughout            169    the motion never restricts anything
shuts to nothing           118    the gap closes to under 512
reaches one neighbour      141    it touches one space, so there is nothing to join
opens only to a crouch      46    a way through, for a body on its knees
```

(The rows overlap; a sector can be several of these.)

## Exit criteria

> The same low-level motion representation describes all three mechanisms;
> semantic distinction comes from spatial context, and the report shows it.

Met, for Z-motion. One vocabulary describes 1367 z-moving sectors; the split
into three design objects comes entirely from two spatial questions; and
naming from the fields instead would be wrong 40% of the time.

Not met for slide and rotate, and the reading says so rather than guessing:
647 of the 659 sliding and turning sectors come back undecided, and the dozen
that do not are ones whose z endpoints move as well.

## Limitations

- `changes_what_fits` and `carries_between_levels` are z-only. A sliding or
  turning sector needs a swept-area test, and `motion_sim.blood_sweep` cannot
  supply one for the rotor family — a 615 sweeps only walls flagged
  `cstat & 16384/32768`, every E1M4 rotor wall is `cstat 0`, and what turns is
  the carried grates.
- The two states are the sector's `off` and `on` endpoints. A mechanism with
  more than two rest poses is read as its extremes.
- `doors.py` supplies two readings of the same motion that can disagree:
  `motion` is computed from the raw extra fields, while the endpoints are
  normalized against the sector's own floor and ceiling when a field is
  absent. Where they differ, the effects list is the one that reflects the
  normalized endpoints, and it is the one to trust.
- Campaign only. Community maps are precedent, never convention, and this
  measures convention.
- `levels_served` counts neighbours whose floor a body could step onto. A lift
  serving a landing more than one step above its top counts as serving one
  level, which is why four of E2M7's big shafts land in the residue.
