# Contrast pilot 2: the niche pair, wall fixture against floor object

Phase 3 found two unsigned candidates identical in every facet but one, each
recurring across more than twenty campaign maps. This pilot asks the
question that decides whether they are one concept or two: **does anything
else differ?**

It was chosen over storefront-vs-window because the evidence already exists
and was found *relationally* rather than assembled by hand. Storefront has no
anchor set in `owner-anchors-v1.json`; defining one would mean hand-picking
the positives, and pilot 1 is a demonstration of what hand-picked tiles are
worth as class definitions.

```text
wall_fixture_niche  seated:none   77 sectors in 28 maps
floor_object_niche  seated:all    72 sectors in 24 maps

shared context: a tiny, tight, two-portal sector holding exactly one object,
                against a wall, sharing a floor plane with a neighbour
```

## What was excluded, and why

The classes are defined by a signature, so most features are fixed by
construction. Scoring them would report the class definition back as a
discovery. Excluded:

```text
area_player_areas              bound by facet 'size'
clear_height_player_heights    bound by facet 'clear'
in_a_repeating_run             bound by facet 'run'
inside_another_sector          bound by facet 'enclosed'
objects_against_wall           bound by facet 'wallbound'
objects_held                   bound by facet 'objects'
objects_resting                bound by facet 'seated'
portals                        bound by facet 'portals'
shares_a_plane                 bound by facet 'coplanar'
stands_above_a_neighbour       bound by facet 'stacked'
stands_under_a_neighbour       bound by facet 'stacked'
```

Left free and actually measured: `enterable`, `solid_closed_volume`, `max_step_player_heights`, `min_opening_player_heights`, `raised_above_all_neighbours`, `rise_over_neighbours_player_heights`, `twin_neighbours`, `solid_wall_share`.

## Result: nothing else separates them

No free feature reaches the 0.65 floor.

| balanced acc. | feature | positive | comparison |
| ---: | --- | --- | --- |
| 0.634 | `min_opening_player_heights` | median 0.966 | median 0.0 |
| 0.607 | `rise_over_neighbours_player_heights` | median 0.0 | median 0.0 |
| 0.585 | `enterable` | 35% | 18% |
| 0.585 | `solid_closed_volume` | 65% | 82% |
| 0.582 | `max_step_player_heights` | median 0.0 | median 0.0604 |
| 0.577 | `twin_neighbours` | median 0.0 | median 0.0 |
| 0.530 | `raised_above_all_neighbours` | 5% | 11% |
| 0.514 | `solid_wall_share` | median 0.5 | median 0.5 |

The strongest, `min_opening_player_heights` at 0.634, is below the floor and
is downstream of the mounting height anyway: a sector whose object hangs
clear of the floor tends to have a taller at-rest opening recorded.

`raised_above_all_neighbours` is deliberately *not* excluded: the `stacked`
facet comes from the `above` relation, which compares a floor with a
*ceiling*, while standing proud of a neighbour's **floor** is a different
measurement the signature does not fix. Measured, it scores 0.53 -- the
verdict survives having that mislabelling corrected.

## But the defining relation is real, not a threshold artifact

`rests_on` fires within 0.15 player heights of a plane. If the two classes
were the same thing split by that cut, the raised class would cluster just
above 0.15. Measured height of the object above the floor plane:

```text
                    min      p10     p25   median     p75      max   on the plane
wall_fixture      -3.396   -0.317   0.377   0.377   0.528    5.615     0 / 77
floor_object      -0.106    0.000   0.000   0.000   0.000    1.449    56 / 72  (78%)

wall_fixture rows inside the grey zone 0.15-0.30 : 6 of 77
```

The raised class sits at a median 0.377 player heights -- 6400 Build units,
about waist height -- not at the edge of the band. Six of seventy-seven are
near the cut. **The split is a design decision, not a threshold effect.**

## And it is not texture

```text
wall_fixture_niche  8 distinct picnums, commonest 2520 x64
floor_object_niche  12 distinct picnums, commonest 2520 x60

picnum 2520 is 83% of BOTH classes
```

The same object. Mounted on the wall in one variant and stood on the floor in
the other. A texture-identity separator would have shown up here as two
disjoint picnum sets; instead the dominant tile is shared, in the same
proportion, on both sides.

## Verdict

**One structural concept with two mounting variants**, and the variant is
carried by a relation. Stated so it can be falsified:

```text
A tiny, tight sector with two portals, holding exactly one object against
its wall and sharing a floor plane with a neighbour, is a fixture niche.
It has two variants, distinguished only by where the object sits:
  floor variant  rests_on(object, sector, floor)      78% exactly on the plane
  raised variant no rests_on; object 0.38 player heights up, modal 6400 units
Both variants carry the same object 83% of the time.
Nothing else measured separates them.
```

This meets the phase's exit criterion. Both the positive and the negative
evidence are explained by one relation (`rests_on`, and the height it
thresholds on), and explicitly not by texture -- the picnum is shared -- nor
by bounding box, since plan size and clear height are signature-bound and
equal on both sides.

## Counterexamples, preserved

```text
10 of 77 raised-variant objects sit BELOW their sector's floor plane
   (negative height, min -3.396 player heights)
 1 of 72 floor-variant objects likewise (-0.106)
16 of 72 floor-variant objects are not exactly on the plane, only within the band
26 distinct raised heights appear; 6400 units is 22 of 64 (34%) across 12 maps
```

The sub-floor cases are real and unexplained. A sprite below its sector's
floor is either room-over-room geometry, where the object belongs to the
space below, or a mapper error. Neither is decided here.

6400 units being only a third of the raised instances means the mounting
height is a **preference, not a rule** -- worth stating before anyone
promotes it to a constructor default.

## For the review queue

Picnum 2520 dominates both variants and is not in
`knowledge/blood/design/owner-anchors-v1.json`. Naming it would label 124 of
the 149 occurrences in this contrast at once, which is the kind of decision
`07_...md` says is worth a human's attention.

## Addendum (2026-08-31): picnum 2520 identified — the concept reframes

Measured across the campaign: 1247 of 1250 sprites wearing picnum 2520 are
sprite **type 709 `kSoundSector`** (the editor's speaker icon; invisible in
game). The "fixture" in the niche is a sector-sound marker, not a visible
object.

What survives: the *structural* finding is intact — the niche sector family
is real, the two placement variants are real, and the split is still carried
by one relation. What changes: the design reading. This is not furniture
with two mountings; it is **where mappers drop the sound marker for a small
ambient space**, and the marker's Z is unlikely to be a player-facing design
decision. The sub-floor counterexamples stop being mysterious: invisible
markers have no reason to respect the floor.

The general lesson joins the reachability one already queued: object-scale
mining must separate **non-visible wiring sprites** (sound types 709–711,
markers, generators) from visible decoration before counting "objects held".
Both defects have the same shape — wiring posing as furniture.

## Re-run (2026-08-31): visible objects only

The addendum above predicted the consequence; this is the measurement. The
contrast was re-run with the mining-hygiene fix in place -- object counts
cover only sprites the engine draws, and off-map sectors are excluded from
the default scope. Everything above is left as it was recorded.

```text
reports/blood-contrast-niche-pair-visible-only.json
```

### The family does not survive

```text
                      before   after (visible objects only)
wall_fixture_niche     77 / 28 maps       13 / 10 maps
floor_object_niche     72 / 24 maps       10 /  7 maps
```

**126 of 149 members (85%) were sectors whose
only object was a sound marker.** With wiring no longer counted, they hold
zero visible objects and stop matching the `objects:1` facet that defined
the class. Picnum 2520 -- 83% of *both* classes before -- does not appear on
either side now.

The `03_...md` outcome for this is *dissolve*: the pair was mostly one
phenomenon, and that phenomenon was **where mappers drop the sector-sound
marker for a small ambient space**, exactly as the addendum read it.

### What survives is real but too small to claim

The remaining 13 and 10 sectors are genuinely furnished niches, and the
relation that defined the variants still separates them cleanly:

```text
object height above the floor plane, in player heights, visible objects only

raised  n=13   0.204 0.204 0.242 0.362 0.377 0.483 0.483 0.483 0.496
               0.604 0.604 0.604 0.664       median 0.483, none on the plane
floor   n=10   0.0 x6, 0.083, 0.106, 0.574, 1.449   median 0.0, 6 on the plane
```

No overlap at the bottom of the raised range. The two floor-class outliers
at 0.574 and 1.449 are within the band of their *ceiling* rather than their
floor -- `rests_on` fires for either surface.

One feature now clears the 0.65 discriminator floor, and the built-in
map-transfer check immediately disposes of it:

```text
twin_neighbours   balanced accuracy 0.8077
rule: twin_neighbours >= 0.5

E2M2.MAP       100% of 4 positives match
E2M3.MAP       100% of 1 positives match
E2M6.MAP       0% of 1 positives match
E3M2.MAP       100% of 1 positives match
E3M4.MAP       100% of 1 positives match
E3M6.MAP       0% of 1 positives match
E4M3.MAP       100% of 1 positives match
E4M6.MAP       0% of 1 positives match
E6M3.MAP       0% of 1 positives match
E6M4.MAP       0% of 1 positives match
spread 1.00 over 10 maps
```

It holds completely in five maps and not at all in five. Same shape as the
shelf-vs-crate pilot's winning rule: separating maps, not concepts. With 13
positives across 10 maps there is not enough evidence here for any claim,
and inventing one would repeat the mistake this re-run exists to correct.

### A preserved counterexample gets explained

The original run recorded 10 of 77 raised objects sitting *below* their
sector's floor plane, "real and unexplained". Among visible objects the
minimum height is **0.204 player heights and no member is below the floor at
all**. Every sub-floor case was a wiring sprite. The addendum guessed this --
"invisible markers have no reason to respect the floor" -- and the
measurement confirms it.

### What still stands from the original run

- The *structural* niche family: a tiny, tight, two-portal sector holding one
  object against a wall, sharing a floor plane with a neighbour. It is real,
  it recurs, and Phase 3 found it without being told.
- The method: nothing separated the two variants but the defining relation,
  and that is still true at n=23.
- The refusal to separate by texture. Before the fix the shared picnum was
  the argument; after it, the two sides share no dominant picnum at all
  (7x144 against 10 distinct tiles), which is a weaker but honest position.

### The general lesson, now measured twice

Wiring posing as furniture cost this contrast 85% of its members and cost the
Phase 1 pilot its headline statistic (`rests_on` exactly on the plane fell
from 86.5% to 63.5% once sound markers stopped counting). Object-scale mining
labels both axes now -- `reachability.sector_kinds` and
`blood_types.sprite_visibility` -- and defaults its statistics to reachable
geometry and visible objects, with the remainder reported rather than
dropped.
