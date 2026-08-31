# The passage oracle, and what it says about the turnstile

The turnstile's last promotion blocker was never geometric. The template is
mined, the constructor builds it, the map loads and survives — and nothing in
the repository could answer the only question that matters about a door:
**does a body get through it?** The load smoke proves a map starts; the action
oracle presses Use once. Neither walks anybody anywhere.

This run built the oracle that does, calibrated it against controls in both
directions, and then found that it cannot yet answer the question it was built
for. Both halves are the result.

```text
bloodmap/oracle.py            run_nblood_passage_oracle, passage_verdict
bloodmap/cli.py               oracle-nblood-passage
tests/test_passage_oracle.py  16 tests, 13 of 13 mutants caught
reports/blood-passage-oracle.json
work/_passage_probe.py        the probes and their controls
work/_passage_run.py          the runner
```

## How it reads a run

Headless, and that is not a nicety. `-bot` draws no frame at all
(`blood.cpp:2066`) and runs accelerated (`:2008`), the process is started with
`CREATE_NO_WINDOW`, and `-bot_trajectory` writes x/y/z/**sector** every tick
(`bot_debug.cpp:159`). The sector sequence is exactly the thing being asked
about, so the oracle reads it rather than inferring it.

The verdict has two clauses, and the second is what makes the first mean
anything:

1. some tick puts the body in a far sector;
2. the **first** tick does not, because a probe that spawns the body beyond
   the aperture answers yes without anything having been traversed.

## Three readouts that do not work

Recorded because each looked convincing while it was wrong, and the second and
third were each disproven only by a control.

**Hashing the screenshot.** `_capture_hashes` can only ever report
"different": a rotor turns continuously, so no two frames of the same room are
identical. Hashing the compressed PNG bytes instead is worse than useless —
deflate output is near-uniform whatever the picture, so a pitch-black frame
scored the same distance from a lit one as two identical frames did.

**Frame-to-frame change of any kind.** A rotor changes the picture whether or
not anyone gets past it. A coarse colour signature *can* be made to
discriminate — comparing the settled view against a twin map with the body
spawned beyond the aperture separated an open corridor (distance 0) from a
walled one (36), with the tolerance at 8 — but it needs a keyboard driver, and
that means focusing the game window and taking the desktop away from whoever
is using the machine. Abandoned for that reason, not because it failed.

**The level exit.** `kChannelLevelExitNormal` is channel 4, so a far room with
`tx_id` 4 and `trigger_enter` should end the level on arrival, and level-end
should be observable. It is not. An open corridor and a walled one produced
byte-comparable logs, neither process exited, and nothing was written. Tested
twice, once with the body spawned directly in the exit sector.

## What the controls say

```text
probe             ticks  visited  verdict     expected
open-corridor       675  [0, 1]   pass        pass      arrived at game_time 1
walled-corridor      83  [0]      fail        fail
single-255            0  []       no data     pass
single-100            0  []       no data     pass
pair-255              0  []       no data     pass
pair-255-same         0  []       no data     pass
solid-blades          0  []       no data     fail
sealed-rotor          0  []       no data     fail
```

**The readout is calibrated.** A body driven across an open corridor is
recorded crossing into the far sector; the same corridor walled is recorded
staying put for 83 ticks. Positive and negative both land, so the oracle can
fail, which is the only reason to trust it when it passes.

**Every rotor probe is empty.** Not a failure — no data. The run ends at
`game_time` 0 with `NO_KNOWN_ACTION` and writes no trajectory at all. The two
negatives that appear to "agree" agree by accident: they were never tested
either.

## Why the rotor probes are empty

The driver models the rotor correctly and then refuses to enter it. From
`single-255`'s telemetry:

```text
region=2 mover=0 corners=4 holes=4 blood_sectors=[2]     the rotor, four blades
relation=0 from=0 to=2  walk=0  why=no_stance  stances=12   near -> rotor
relation=1 from=2 to=0  walk=1  why=none       stances=41   rotor -> near
relation=2 from=1 to=2  walk=0  why=no_stance  stances=12   far  -> rotor
relation=3 from=2 to=1  walk=1  why=none       stances=41   rotor -> far
```

Getting **out** of the rotor is walkable from either side; getting **in** is
not, from either side. Twelve candidate stances are offered at each entry
mouth and none is accepted, while the exit relations accept 41. With no way
in, the model offers nothing to do and the run ends before a tick is
simulated.

That is a statement about the driver, which is unfinished and experimental,
not about the aperture. The blades punch four holes in the rotor's walkable
area and the entry stances are evaluated against one pose of a sector that
never stops moving.

**It is not the spin rate.** Measured, not reasoned: a sweep at periods 32,
64, 100, 160, 255 and 400 produced 0 ticks at every one. The refusal happens
while the world is being mapped, before any motion — so the roadmap's
suggestion to "measure at which period passage becomes reliable" has no
answer to give here.

## Consequences

**Passage through a rotating door remains unproven, at every period.** The
Aldermack forecourt mouth is therefore **not sealed** and the turnstile's
promotion blocker stands. Sealing it would have staked a level's only route on
a claim nothing checks — which is the same shape as the 72 stairs to nowhere
that passed every automated gate.

Three ways forward, in the order I would take them:

1. Split the engine flags so `-bot_trajectory` records without `-bot` driving.
   The recorder and the driver are the same switch today
   (`bot.cpp:1686` sets `m_enabled` from either), and separating them would
   let a scripted hold-forward driver produce the same sector sequence, with
   negatives that mean what they claim.
2. Failing that, the entry-stance derivation is where a rotor is refused, and
   it is refused for both directions symmetrically — a narrow, testable thing.
3. A human walking through the built `turnstile.MAP` settles it in ten
   seconds, and is worth more than either.

## Limitations

- A pass and a fail are not symmetric. A crossing is evidence about the
  aperture whatever drove the body, because the engine recorded the sector
  changing. A non-crossing is ambiguous between an aperture that blocks and a
  driver that never tried, and must be read beside a positive control sharing
  the driver.
- Windows only, and it needs NBlood plus Blood's game data. The corpus-free
  half — trajectory parsing and the verdict — is what the tests cover.
- The probes are generated maps. They are instruments, and are scored, never
  mined.
- The far side is named by sector index, taken from the build rather than
  guessed from region order. On a map not built here that index has to come
  from somewhere, and nothing yet derives it.
