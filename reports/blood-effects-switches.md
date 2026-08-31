# Hidden switches command the same things as visible ones

A switch sprite carrying Build's invisible bit is in the map, is pressable,
and is not drawn. The roadmap queued the question: **does a concealed trigger
command a different kind of thing than an exposed one?**

Measured. It does not.

```text
bloodmap/switches.py           switch_role, contrast_hidden_switches
reports/blood-effects-switches.json
work/_switch_contrast.py
tests/test_switch_contrast.py  15 tests, 19 of 19 mutants caught with
                               tests/test_effects.py
```

## The rule of the experiment

Features are **channel role** and **what the switch commands**. Nothing
geometric, nothing about the tile, nothing about height. That narrowness is
the experiment: a feature reading position would answer a different question
and look like an answer to this one.

Scored: `transmits`, `listens`, `relays`, `ends_the_level`,
`reserved_channel`, `sectors_commanded`, `commands_nothing_in_this_map`,
`commands_motion`, `commands_z_motion`, `commands_more_than_one_kind`,
`one_way`, `keyed`, `once_only`.

Discipline borrowed intact from `anchors.contrast_anchor_sets`: balanced
accuracy rather than accuracy, because the split is 115 against 1281 and a
rule that never fires scores 92% on the raw rate; a per-map transfer check;
counterexamples preserved.

## The population

```text
hidden      115 switches in 18 maps      types 20 (68), 21 (43), 22 (4)
visible    1281 switches in 43 maps
```

The roadmap recorded 85 hidden switches; this count is 115 over the 43
campaign maps, taking every sprite `switches.is_switch` accepts. The two
numbers come from different selections and I have not reconciled them; the
rows behind this one are in the JSON.

E1M2 alone holds 26 of the 115, E3M2 fifteen more.

## The result: nothing separates them

**Not one feature reaches the 0.65 discriminator floor.** The best two:

```text
feature                       balanced   hidden    visible
sectors_commanded < 0.5         0.614      68%       45%
commands_nothing_in_this_map    0.614      64%       42%
commands_motion                 0.594      24%       43%
relays                          0.588      85%       68%
```

A hidden switch is somewhat more likely to command nothing that any *sector*
listens to, and somewhat less likely to drive a moving sector. Both are
tendencies at around 0.61 balanced accuracy, which is not a distinction — it
is the shape of "much the same, slightly noisier".

And the leading tendency is the least trustworthy of them: a channel with no
listening sector may be commanding *sprites*, which this feature set does not
look at. `commands_nothing_in_this_map` is a fact about what was measured, not
about the switch.

## Two things no hidden switch does

Low balanced accuracy, because the visible base rates are small, but both are
absolute in a population of 115:

```text
ends_the_level     0 of 115 hidden      56 of 1281 visible  (4.4%)
keyed              0 of 115 hidden      17 of 1281 visible  (1.3%)
```

**No concealed switch in the campaign ends the level, and none is keyed.**
Neither would be found by a discriminator search, and neither is a rule the
contrast can promote — 4.4% and 1.3% are rare enough that 115 draws could miss
them by chance. Recorded because they are the kind of thing worth a targeted
test rather than a fishing expedition, not because they are established.

## What this says about the phase

The steering for this phase is that meaning comes from embedding rather than
from fields. This experiment is the same claim from the other side and it
lands the same way: **concealment is not a property of what a trigger does.**
A hidden switch is an ordinary switch that the mapper chose not to draw, and
whatever that choice means is in where it sits — which is exactly the half
this experiment is forbidden to look at.

So the question the result raises is the geometric one, and it is now the
sharper question: hidden and visible switches command the same things, so what
differs is where they are put. That belongs to Phase 9's conditional view.

## Limitations

- Every feature is channel role or what is commanded. By construction this
  cannot say whether hidden switches sit somewhere different, and that is now
  the open question rather than an oversight.
- Thresholds are fitted on the rows they are scored on. These are separations
  observed, not a validated classifier.
- `commands_*` resolves a channel to *sectors* that listen on it. Sprites that
  listen are not followed.
- Campaign only, 43 maps. Community maps are precedent, never convention.
- The 115/85 discrepancy against the roadmap's figure is unreconciled.
