# Party walls: where does one building stop?

`reports/blood-facade-grammar.md` refused to promote a `facade_run()`
constructor on one ground: a facade candidate is a plane, not a building,
and nothing in the run says where one frontage stops and the next begins.
This measures that claim, and it turns out to be mostly wrong -- for a
reason that was itself a defect in the extractor.

```text
bloodmap/anchors.py   interior_components, party_wall_gaps
tests/test_facade.py
reports/blood-party-walls.json
```

## The oracle is the interior, not a label

Two openings on one frontage are in the same building when you can walk
from one interior to the other without stepping back outside. So: cut every
portal that passes through a sky-lit sector, label the connected components
of what remains, and read the verdict off the components the two openings
lead into. A pair where either side opens onto outdoor space -- a gate, an
arch into a courtyard -- carries no verdict and is excluded rather than
guessed.

This is not a proxy for a label; it is the thing itself. Its two failure
modes are stated up front: a building with a sky-lit internal courtyard is
split into two, and two shops joined by a back-room door are merged into
one. Both are real buildings in Blood and both are counted wrongly here.

## The answer: a run is a building frontage, under about eight bays

```text
campaign facade candidates                      890
serving at least one interior                   749
of those, serving exactly one building          732   (98%)
serving two or more                             17   (2%)

by run length:
  under 4 bays       2/426 cross a boundary   (0%)
  4 to 8 bays        5/246 cross a boundary   (2%)
  8 to 16 bays       8/ 67 cross a boundary   (12%)
  over 16 bays       2/ 10 cross a boundary   (20%)
```

**A collinear facade run that serves any interior serves exactly one
building 98% of the time**, and the exceptions sit in the long runs,
exactly where they were predicted to be: never under four
bays, 2% between four and eight, 12% between eight and sixteen, 20% above
that. The city-block edge is a real failure mode and it is a *long-run*
failure mode.

## Why the earlier report got this wrong

The first facade extractor counted every two-sided wall on a run as an
opening. 3187 of the 4331 it found were not openings at all: they were
seams and kerbs in the street's own ground -- two sky-lit sectors meeting at
a step in the pavement, with no lintel and no wall above. An opening in a
facade has a header; a two-sided wall that keeps the host's own sky ceiling
is ground, not wall.

Requiring a header drops all 3187 and only 4 genuine indoor neighbours. It
also cuts campaign candidates from 3570 to 890 and, because runs whose only
interruptions were kerbs no longer qualify, replaces a population of street
segments with a population of frontages. The `2%` above is measured on the
second population; on the first it was 12%, and most of what looked like a
run crossing a building boundary was a stretch of pavement.

## What marks the boundary, when there is one

241 campaign opening pairs carry a verdict: 19 different
buildings, 222 one building. Measured over all of them, the answer
looks strong, and is not:

```text
DISCRIMINATES  gap_bays                     0.877   gap_bays >= 0.1875
DISCRIMINATES  solid_walls_between          0.846   solid_walls_between >= 0.5
DISCRIMINATES  sill_changes                 0.668   0.5789 vs 0.2432
DISCRIMINATES  header_changes               0.666   0.5789 vs 0.2477
DISCRIMINATES  interior_depth_changes       0.651   interior_depth_changes >= 0.0935
rejected       gap_shade_differs_from_run   0.515   0.0526 vs 0.0225
rejected       flank_tiles_differ           0.504   0.0 vs 0.009
rejected       gap_tile_differs_from_run    0.500   0.0 vs 0.0
rejected       masked_wall_in_gap           0.500   0.0 vs 0.0
```

`gap_bays >= 0.1875` is just "is there a pier at all", and it scores 0.877
only because 177 of the 222 one-building pairs have **no pier**:
they are two halves of a single wide hole, split by Build into two walls.
The rule is detecting *two separate openings*, which is not the question.

Restricted to the pairs that a pier genuinely separates, the base rate rises
from 8% to 29% and almost everything collapses:

```text
pairs separated by a pier: 63  (18 different buildings, 45 one building)

DISCRIMINATES  header_changes               0.711   0.5556 vs 0.1333
DISCRIMINATES  interior_depth_changes       0.678   interior_depth_changes >= 0.0625
rejected       sill_changes                 0.633   0.5556 vs 0.2889
rejected       gap_bays                     0.617   gap_bays >= 3.5
rejected       solid_walls_between          0.589   solid_walls_between >= 1.5
rejected       gap_shade_differs_from_run   0.528   0.0556 vs 0.1111
rejected       gap_tile_differs_from_run    0.500   0.0 vs 0.0
rejected       flank_tiles_differ           0.500   0.0 vs 0.0
rejected       masked_wall_in_gap           0.500   0.0 vs 0.0
```

**A change in the header line is the only thing left**, and only just: 0.711
balanced accuracy, catching 56% of boundaries while firing on 13% of
non-boundaries. It does transfer -- across the nine maps with at least four
such pairs it scores between 0.75 and 1.00 -- but 63 pairs is a small thing
to build a rule on.

```text
  E1M3.MAP     0.80  n=10
  E1M4.MAP     0.75  n=4
  E2M5.MAP     0.80  n=5
  E3M1.MAP     0.75  n=4
  E3M6.MAP     1.00  n=4
  E4M3.MAP     0.75  n=4
  E4M6.MAP     0.80  n=5
  E6M2.MAP     0.75  n=4
  E6M5.MAP     1.00  n=4
```

## Rejected, and worth stating plainly

**Material never marks a party wall.** `gap_tile_differs_from_run` and
`flank_tiles_differ` fire on **zero** pairs of either class, and shade is at
chance. This is not a weak signal, it is the absence of one, and it follows
from the facade report's own headline: 98% of multi-opening campaign facades
use a single wall tile across the whole run. A generator that changes tile
at a property line would be inventing a convention Blood does not have.

**Pier width does not mark it either.** Once zero-gap pairs are removed,
`gap_bays` falls to 0.617 -- below the floor. Blood puts piers of two and
three bays *inside* one shopfront: E1M3's one-building pairs have a median
gap of 2.5 bays, E3M6's 3.0. A wide blank stretch of wall is how a window
bank is spaced, not how two owners are divided.

## Counterexamples, preserved

```text
  E3M1.MAP     sector:339    18.25 bays   2 openings  2 buildings
  E6M2.MAP     sector:263     18.0 bays   2 openings  2 buildings
  E2M3.MAP     sector:260   15.875 bays   6 openings  2 buildings
  E6M2.MAP     sector:59      12.0 bays   2 openings  2 buildings
  E6M3.MAP     sector:142     12.0 bays   2 openings  2 buildings
  E6M3.MAP     sector:145     12.0 bays   2 openings  2 buildings
  E1M4.MAP     sector:139   10.294 bays   3 openings  3 buildings
  E1M4.MAP     sector:382      9.5 bays   2 openings  2 buildings
```

One boundary has no pier at all -- two buildings whose openings are
adjacent walls with nothing between them. Any rule built on the pier misses
it by construction.

## Consequence for `facade_run()`

The building-extent objection is largely withdrawn. A run under eight bays
that serves an interior is a single building's frontage in 98% of the
campaign, and a constructor can be promoted on that domain with the failure
rate stated rather than hidden. Above sixteen bays it should not be, and a
header-line change is the only hint available for splitting one.

What still blocks promotion is unchanged and is *not* building extent: the
visible lintel band a sign sits on is not recoverable from sector geometry,
so a constructor can place an opening but cannot place the band above it.

