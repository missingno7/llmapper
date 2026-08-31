# Building a facade: the first crossing from reading to authoring

Three reports measured what a Blood facade is. This builds one, and the
interesting part is what building found that reading had not.

```text
bloodmap/aperture.py                       facade_run, FacadeOpening
projects/facade-pilot/level/build_facade.py
projects/facade-pilot/level/facade-{narrow,wide}.MAP
projects/facade-pilot/reports/facade-pilot.json
tests/test_facade_run.py
```

## What it is given, and what it is told

Nothing dimensional is invented. Every number below was measured by
`reports/blood-facade-grammar.md`, `blood-lintel-band.md` or
`blood-party-walls.md`:

```text
one wall tile across the run       98% of 131 campaign multi-opening facades
a shared header datum              79%
a shared sill datum                77%
a thin helper sector (the kerb)    71%
openings on whole bays             31%
bay                                1024 units, from 16 units per tile pixel
wall thickness (the reveal)        256, the commonest depth behind an opening
sign height                        2.5 player heights, cv 0.33 over 86 letters
```

The openings are an **argument**, never invented: 53 repeating runs in 890
campaign candidates is not enough recurrence to give a rhythm a default. The
bay grid is offered and never enforced, because only 31% of campaign openings
land on one and a builder that snapped them would be reporting its own grid.

The sign height is stated as an authoring **preference** with its spread
attached, because the corpus has no rule there -- 1.69 to 5.13 player heights,
coefficient of variation 0.33. What *is* enforced is that the sign clears its
opening's header, which all 26 campaign letters do.

## Two things reading had got wrong

Neither was visible until something had to stand up.

**The datums were annotations, not geometry.** The first build recorded
`header_z` beside the opening and let the mouth run floor-to-ceiling. The
placement validator caught it the only way it could: five sign letters
"hang over an opening and have nothing behind them". The header *is* the
neighbour's ceiling -- that is what the facade study measured and what makes
several openings read as one facade -- so it has to shape the hole, not
describe it.

**A facade wall has thickness, and the piers are void.** The first build gave
the interior the whole frontage edge and declared the spans between the
openings solid, which is a wall sandwich: two coincident one-sided walls.
`validate-authored` rejected it as an infinitely thin partition, so the corpus
was asked directly:

```text
campaign facade solid walls                                     780
  with a reversed coincident partner (a wall sandwich)            0   (0.0%)
  standing alone, void behind them (real thickness)             780   (100%)
```

Not one. A Blood facade wall occupies plan space, the interior is set back
behind it, and each opening is a passage cut through -- which is exactly the
**reveal** this module already names. Its depth was measured rather than
picked: over the 1140 sectors behind a campaign facade opening, 256 and 512
are the two commonest (202 and 196 occurrences) and 41% are at or under 512.

A third, smaller one showed up only in a render: the band above the mouth was
wearing the jamb tile, painting a stripe of metal across the frontage above
every window. The lintel is drawn from the street-side wall record, so it must
carry the facade's own material. Dress the reveal, never the band above the
mouth.

## Verification

"It compiled" is not on this list.

```text
                        narrow (6 bays)   wide (10 bays)
validate                0 errors 0 warn   0 errors 0 warn
roundtrip               byte-exact        byte-exact
validate-authored       0 errors 0 warn   0 errors 0 warn
geometry-audit          native 0 authored 0, DM 0/0 in main
NBlood load/spawn       pass              pass
  autoexec / map_initialization / game_loop reached, stayed alive, no fatal
```

The authored-geometry gate is the one that matters here: it is the gate that
rejected the wall sandwich, and it is clean only because the geometry was
changed to match the corpus rather than the gate relaxed.

## Width invariance

The same facade at two widths. This is Phase 13's exit shape, piloted early:
change the width and the relationships have to survive.

```text
                              narrow      wide
run, bays                        6.0      10.0
bay, units                      1024      1024
reveal, units                    256       256
openings                           2         3
header_z (shared datum)       -40960    -40960
sill_z (shared datum)          -1024     -1024
wall tile                        400       400
jamb tile                        195       195
sign seat z                   -42400    -42400
sign clears its header by       1440      1440

openings at bays   narrow [(1,1), (3,1)]      wide [(1,1), (3,1), (6,2)]
piers at bays      narrow [(0,1), (2,1), (4,2)]  wide [(0,1), (2,1), (4,2), (8,2)]
```

Everything that is a relationship holds; only the count of bays and openings
changes, which is what was asked to change.

## Rendered

```text
work/facade-frames/built-narrow/frames/narrow_front.png
work/facade-frames/built-wide/frames/wide_front.png
work/facade-frames/campaign-E3M2/frames/campaign_E3M2_179.png
```

All three come from the same observer at the same settings, which is the only
way a side-by-side means anything. The frames are not committed: render dumps
under a project are ignored by policy, and the campaign frame is a render of a
commercial map.

**What the built frame shows:** one grey ashlar material across the frontage,
two openings on the bay grid with a shared header line and a shared sill, metal
jambs in the reveals, a kerb strip along the pavement, and MEATS lettered on
the band above the left opening's head.

**Against E3M2 sector 179**, honestly: the campaign frontage has the same
grammar -- one material, a header line, a sill, a sign above the head, a kerb --
and three things the built one has not. It is dressed (an awning, goods in the
bay, crates on the pavement); its sign is two-tier, a bay sign under a building
sign; and its openings are not on a strict grid, because the corpus only puts
31% of them there and a human put the rest where the building wanted them. The
built facade is more regular than any campaign facade, and that regularity is
the caller's input showing through, not a fact about Blood.

## Constructor promotion: not yet, and precisely why

`facade_run` is a **composable helper in `aperture.py`**, not a
`vocabulary.py` constructor. That module's rule is that a concept is admitted
when it occurs across most original maps *and a compact parameter set
reproduces held-out examples*. The first half is met -- 890 candidates in 37
maps. The second has never been run, and the blockers ride on every build
rather than living in a comment:

- **No held-out reproduction test.** Rebuilding facades the parameters were
  not derived from is the missing evidence, and it is the whole of the rule's
  second clause.
- **Rhythm is not a parameter.** 53 repeating runs in 890 is not recurrence.
- **Building extent is settled only below eight bays.** A run serving an
  interior serves exactly one building 732 times out of 749, but 20% of runs
  over sixteen bays cross a boundary.

## Limitations

- One frontage on one straight run. A corner, a curve, and a frontage that
  turns into another building are all untested.
- The kerb is composed by the caller, not built by the helper, because it lies
  on the street side of the frontage and a helper that silently reshapes its
  host is worse than one that leaves a documented job.
- The NBlood check is load and spawn. Nothing here proves the facade reads
  well in motion, and no bot has walked past it.
- The built maps are artifacts, never evidence: they may be scored against the
  corpus and must never be mined into it.
