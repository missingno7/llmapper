# Blast chains: how Blood times many explosions

Asked by the owner, 2026-11-24: "The explosion can be a chain going upwards or
something, check explosion chains in DW levels, they can be sometimes quite
complex, but just don't make everything to explode because it would be killing
player."

Read by `bloodmap.blasts`, mined by `python -m tools.mine_blasts`
(`knowledge/blood/design/blast-chains.json`: 128 chains of four moments or more
in 54 of the named maps); one in full: `python -m tools.mine_blasts show DWE3M5 155`.

## The grammar

* **One wire, many waits.** Every exploder (459) of a chain is on ONE channel
  and holds its own `wait_time` in tenths. Nothing passes from blast to blast.
  A wait of 0 becomes 1 (actInit). Statnum 11, invisible.
* **Two tenths between moments** (the median; DWE3M7's runs and DWE3M5's 127 go
  at one), about 1.5 s in all, 13 blasts. DWE2M3's 157 is 833 blasts over 49 s.
* **A run goes somewhere.** A path over the plan, steps of about 1,000 units or
  a body of height (DWE3M5's 155: fifteen blasts, two tenths apart, eleven
  bodies down a shaft; E3M1's 116 up; nine chains climb two bodies or more).
  A room going up is several at once, a pause, several more, then a run
  (DWE1M6's 110: six at 4.5 s, six at 5.0, then one or two at a time).
* **Beside it on the wire**: an earthquake (19) in 25 of the 128, a voice (711)
  in 23, and one-way relays (21/20) whose wait is the chain's length and which
  send the next thing on. Spawns at the end (DWE1M6's six 205s).
* **Things burst with no blast**: gib objects (416/417) on the wire at once:
  rock (data_1 20), wood (4, 15), fire sparks (6), fire puffs (26), with a sound
  in data_4 (313 stone, 314 metal, 305 the large explosion). A gib object takes
  the wire at once and has no wait of its own: give it a relay. `locked` keeps
  another blast from breaking it first (E4M6's). It hurts nobody.

## What a blast does to the player (`blasts.hurts`)

Radius 2,400 over the plan and 38,400 (2.26 bodies) up and down, if it sees
them. 20 to 30 health at once, then 900 * 0x40000 / (0x40000 + d*d) sixteenths of one
for each of some fifteen frames: by the formula 432 health in all at 500 units,
175 at 1,000, 88 at 1,500, 52 at 2,000 (before armour, and if he is not thrown
clear). So blasts for show stand more than 2.3 bodies
over the floor, or 2,400 from where anyone can be, or behind something; what
bursts at eye level is a gib object. `blasts.harmless` checks it.

## Used

The Cabal's chamber (`cabal_rite._blasts`): the statue bursts (gib), fire climbs
(gib puffs to 2.2 bodies, then five exploders up the hanged one's chain), a ring
of five round the crown a tenth apart, stone falls, Caleb speaks, and the emptied
well's bottom goes up.
