# Building a turnstile: a mechanism promoted from four rotors

`projects/blood-city/references/auto-rotators.md` recorded the family and
refused to promote it, listing what promotion would need. This does that, and
the interesting part is again what building found.

```text
bloodmap/mechanism.py          turnstile, turnstile_pair, TURNSTILE_TEMPLATE
bloodmap/construction.py       _sprite_angle
projects/facade-pilot/level/build_turnstile.py
projects/facade-pilot/level/turnstile.MAP
work/_turnstile_template.py    re-mines the template
tests/test_turnstile.py
```

## The template, and where every line came from

Mined from the door subfamily by name -- the split between a turnstile *door*
and rotating *scenery* is spatial (does the rotor sit in a doorway?) and not a
field, so the root type alone would have mixed 88 instances of two design
objects.

```text
E1M4   151 <-> 314   blood-campaign        busy 255/0 against 0/255
DWE1M9  61 <->  64   community-curated     busy 100/0 against 0/100
DNE3L6   3,     11   own-conversion        both 0/100, the same-direction variant
```

All four agree on: sector type 615, `rx_id` 7 (the `level_start` broadcast),
both busy waves 1, both retriggers 1, `interruptable` 0, exactly one
kMarkerAxis at the pivot on statnum 10, and exactly four blade sprites on tile
332. The blades being **grates** is what makes a turnstile read as passable
machinery rather than a drum, and Death Wish reuses the campaign's exact tile.

Two things the four do *not* agree on, so both are arguments:

- **the spin period** -- E1M4 255, Death Wish 100;
- **how far it turns** -- E1M4 −8192, DWE1M9 2047, DNE3L6 2032.

## Two corrections to the reference

**The sound sprite is not a trait of the family.** `auto-rotators.md` says "a
sound generator (type 710, picnum 2521) sits in or beside one rotor".
Measured, E1M4 has one in **both** its rotors and DWE1M9 in **neither**. It is
a map's habit, so the constructor has it off by default.

**Direction is not the marker's sign.** Both E1M4 rotors carry the same marker
angle (−8192) and mirrored busy fields, so what counter-rotates a pair is
*which busy field carries the period*, not the angle. That is why `clockwise`
is a boolean rather than an angle.

## What building found

**The travel is the axis marker's angle, and it was being destroyed.**
`construction.add_sprite` masked every angle to `& 2047`. That is right for a
facing, which wraps at a full turn, and wrong for a kMarkerAxis: Blood
interpolates `0 -> ang` to sweep the sector, so the magnitude is *how far it
turns*. E1M4's −8192 is four whole turns, and `-8192 & 2047` is exactly **0** --
a rotor that does not move, written silently, with every validator green. The
mask now applies to facings only.

This is the reason the motion replay was worth running: nothing else in the
pipeline would have noticed.

## Verification, and one thing that is not verified

```text
validate                0 errors, 0 warnings
roundtrip               byte-exact, 1695 bytes
validate-authored       0 errors, 0 warnings
NBlood load/spawn       pass -- autoexec, map_initialization and game_loop
                        reached, stayed alive, no fatal indicators
                        engine r14433-f88c4f189
```

Field-for-field, the built map carries the template: two type-615 sectors,
`rx_id` 7, busy 255/0 against 0/255, waves 1/1, retriggers 1/1,
`interruptable` 0, two kMarkerAxis sprites on statnum 10 each owning its own
sector, `marker_0` resolving to the axis, and eight blades on tile 332.

**Motion replay agrees with the original and cannot prove the motion.**
`motion_sim.blood_sweep` reports zero wall travel for the built rotors -- and
for E1M4 151/314 and DWE1M9 61/64 as well. That is correct, not a failure: a
type 615 sector sweeps only walls flagged `cstat & 16384/32768`, and every one
of E1M4's rotor walls is `cstat 0`. A turnstile turns its **carried sprites**,
and `motion_sim` models wall sweeps. So the replay establishes that the built
rotor moves its geometry exactly as much as the campaign's does -- none -- and
says nothing about the blades.

**Passage is not proven.** The reference asked for "an NBlood oracle run
proving the player can actually pass through at the mined spin rates". The
oracles available here are a load/spawn smoke and an action oracle that presses
Use once and diffs screenshots. Neither walks a player through a moving
aperture. The map loads, spawns and survives; whether a body fits between
turning grates at period 255 is untested, and the honest status is that this
half of the promotion criterion is **not met**.

## Rendered

```text
work/turnstile-frames/built/frames/built_turnstile.png
work/turnstile-frames/campaign-E1M4/frames/E1M4_151.png
```

Both from the same observer at the same settings; not committed, per the
render-dump policy. The built frame shows the two rotors either side of a
central pier with the grate blades legible in both mouths. The E1M4 frame is
taken from inside its own rotor, looking out past a blade into the carnival.

The arrangement differs and the report should say so: E1M4's pair flanks one
central entrance, while the built pair makes each rotor its own passage with a
pier between them. Both satisfy the measured trait -- exactly two portal walls
per rotor -- but the composition is not the campaign's, and nothing in the
mined fields would have told me which to choose.

## Promotion status

`turnstile` and `turnstile_pair` live in `bloodmap/mechanism.py` beside
`sliding_gate`, which is where template-driven construction belongs. They are
**not** `vocabulary.py` entries: that module is for spatial vocabulary, and its
rule wants a compact parameter set to reproduce held-out examples, which here
would mean rebuilding DWE1M9's pair from the template and comparing. That has
not been run.

Of the four things `auto-rotators.md` said promotion needed, three are done --
the assembly template, the constructor deriving every fact from it, and the
motion replay -- and the fourth, an oracle proving passage, is not.

## A near-miss worth recording

The mutation sweep for this file reported two survivors that were not
survivors, and one full-suite run failed two tests that pass. Both had the same
cause: the harness writes a mutant, a subprocess imports it and caches the
bytecode, and the restore lands inside the same second -- so the `.pyc`'s
recorded source mtime matches the restored file and Python keeps running the
**mutant**. `BLADE_PICNUM` read 332 in the source and 400 in the imported
module.

The source was right the whole time and the cache was lying. Both sweeps were
re-run with `__pycache__` cleared around every mutation, and the results here
(11 of 11 and 13 of 13) are from that harness. A mutation result taken without
that guard is not evidence, which is worth knowing before the next one.

## Limitations

- One pair, one period, one arrangement. Nothing tests a rotor in a real
  street, a pair at Death Wish's period 100, or the same-direction variant in
  a built map rather than in the constructor's arguments.
- The blades are placed at four quarter-turn angles around the pivot. That is
  a reading of "four blade posts", not a measurement of their angles in the
  original, which was not taken.
- The built map is an artifact and never evidence.
