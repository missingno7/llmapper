# The lintel band: recoverable, and not what places a sign

`reports/blood-facade-grammar.md` refused a `facade_run()` constructor on
one remaining ground. Every campaign sign letter sits above the header of
its opening; the band it appears to sit *on* is painted into the wall
texture rather than built out of sectors; so a constructor could place the
opening and not the band above it.

Half of that is now wrong. The band is recoverable. It is simply not what
places the sign -- and neither is anything else, tightly.

```text
bloodmap/art.py             course_rows, row_luminance
bloodmap/texture_align.py   course_z
tests/test_lintel.py
reports/blood-lintel-band.json
```

## The band is in the tile, and the tile can be placed

Blood paints its cornices and plinths into the wall art. `art.course_rows`
finds them -- rows where the tile's mean brightness jumps more than two
standard deviations -- and `texture_align.course_z` puts one in the world,
given the wall's `y_repeat`, `y_panning`, and the edge its texture hangs
from. Every tile that carries campaign or curated signage has courses:

```text
  tile  1004   29 letters   32x64   course rows [2, 8, 10, 62]
  tile    89   16 letters  128x128  course rows [3, 12, 19, 110, 111, 114, 115, 116]
  tile    15   15 letters   64x64   course rows [9, 10, 21, 22, 49, 63]
  tile    90   12 letters   64x64   course rows [16, 48]
  tile   474    7 letters   64x64   course rows [28, 42, 56]
  tile    80    7 letters  128x128  course rows [6, 8, 115, 119, 126, 127]
```

Tile 80 is the E3M2 loading bay: a heavy course of blocks across the top of
the tile and another across the bottom. Its bottom course at row 115, hung
from that bay's head at z -29696, lands at **z -33024**. The LOADING letters
sit at **z -33792** -- three texture pixels above it. That is the band the
rendered frame shows, found from the art and placed in the world.

So the datum exists and a constructor can compute it. The question is
whether Blood uses it.

## It does not

```text
letters within 3 texture rows of a painted course   22%   (median 10.0 rows away)
a random row on the same tiles                27%   (median 7.45 rows away)
```

Blood's sign letters are **no closer to a painted course than chance**, and
marginally further. The tiles that carry signage have six to eight courses
each, so a random row is often near one; that is what makes the null 27% and
it is why the comparison is against the null rather than against zero.

The E3M2 case is real and is one case. It is what the frame shows, it is
what suggested the hypothesis, and 86 letters say it does not generalize.

## Then what does place a sign? Nothing, tightly

Four candidate datums, ranked by coefficient of variation -- how much a
constructor using each as its rule would be guessing:

```text
blood-campaign
  cv  0.37  height above the street floor, player heights      n= 26  median   2.536  [2.053, 5.132]
  cv  0.48  height above its opening's head, letter heights    n= 24  median   1.766  [1.455, 4.052]
  cv  0.86  height above its opening's head, player heights    n= 24  median   0.725  [0.242, 2.355]
  cv  0.96  distance to the nearest painted course, texture rows n= 26  median  12.000  [0.0, 35.0]

campaign + curated
  cv  0.33  height above the street floor, player heights      n= 86  median   2.536  [1.691, 5.132]
  cv  0.53  height above its opening's head, letter heights    n= 55  median   1.455  [0.808, 4.052]
  cv  0.79  height above its opening's head, player heights    n= 55  median   0.664  [0.242, 2.355]
  cv  0.92  distance to the nearest painted course, texture rows n= 86  median  10.000  [0.0, 44.0]
```

The best of them is height above the street floor at a coefficient of
variation of 0.333, ranging from 1.691 to 5.132 player heights. That is
not a datum a rule hangs from; it is a habit with a wide spread. Measuring
from the opening's head instead is **worse**, not better
(cv 0.788), even though every campaign letter is above its head --
the constraint is real and the offset is not.

Normalizing by the sign's own letter height helps a little
(cv 0.529, median 1.455 letter heights above the head) and is the
only candidate that ties the sign's position to the sign's own size. It is
still not tight enough to call a rule.

## What this does to the constructor

The blocker dissolves, but not the way the last report expected. It is not
that the missing datum was found. It is that **there is no datum to miss**:
Blood does not place its shopfront signs against a line, painted or built.
It puts them above the opening, roughly two and a half player heights up,
and varies by a factor of three.

So "a constructor cannot place the band" is not a reason to refuse
`facade_run()`. A constructor placing a sign at 2.5 player heights above the
street, above its opening's head, is as right as Blood is -- and can say so,
with the spread attached, instead of implying a precision the corpus does
not have.

What promotion still needs, and this report does not provide:

- **A generated facade that survives the validators and the engine.** The
  measurements here are about reading. `06_...md`'s own warning applies: a
  constructor that returns without raising is not evidence.
- **A decision about rhythm.** 53 repeating runs in 890 campaign candidates
  is not enough recurrence to give a rhythm parameter a default, so a
  constructor should take opening positions rather than invent them.

## Two corrections this experiment forced

Neither was the thing being looked for; both were in the way of it.

1. **A wall texture's vertical span had two definitions in the codebase**,
   reciprocal in `y_repeat` and agreeing only at `y_repeat` 16.
   `texture_align.repeat_span` is right -- 48% of the campaign's 51571
   one-sided walls with known art are exactly one repeat tall under it --
   and `aperture.tile_span_z` now delegates to it. Blood's z is 16 times
   finer than x and y, so at `y_repeat` 8 one texture pixel is 256 z, which
   is 16 world units: the same 16 units per pixel the facade scale runs at
   horizontally. At the pairing Blood pins, a wall texture is square.
2. **`snap_leaf`'s arithmetic** was scaled by that error. Tile 22 at
   `y_repeat` 8 spans 32768 z, which is the campaign's median aperture leaf
   outright -- one repeat, not four -- and over the 540 campaign walls
   carrying that tile it draws a median of 1.00 times up its wall.

## Limitations

- 26 campaign letters on 3 facades in 2 maps, 86 in all. Every
  number here should be read at that size, and the curated share means the
  spread leans on Death Wish.
- A course is a brightness edge, not a cornice. `art.course_rows` cannot
  tell a painted band from the top of a brick course, which is why tile 90 --
  plain masonry -- reports two courses and tile 80 reports its cornice and
  its plinth alongside four rows of block detail.
- The anchor model is Build's two choices for the top step of a two-sided
  wall: the head of the opening, or the sector ceiling when
  `ALIGN_TO_CEILING` is set. Walls that are neither -- a one-sided wall
  behind a sign -- are anchored at the sector ceiling here, and 31 of the 86
  letters stand on one.

