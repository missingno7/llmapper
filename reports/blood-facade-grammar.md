# Facade grammar: what makes several openings one facade

`06_...md`: the facade owns the openings, the opening does not own the
facade. So this does not look for windows. It looks for a coherent run of
street-facing wall and treats the openings as what interrupts it.

```text
bloodmap/anchors.py   Facade, find_facades
tests/test_facade.py
reports/blood-facade-grammar.json
reports/blood-facade-views/   rendered validation frames
```

The JSON is abridged on purpose. Writing every candidate in full comes to
32 MB, twenty times the largest report in the repository, most of it the
same three-string `basis` repeated 18870 times. What it carries instead:
a full record for every campaign multi-opening candidate and for every
signed candidate in either population, a compact row for every campaign
candidate so the distributions below can be recomputed, and per-population
aggregates in `summary`. Curated runs that carry no signage are precedent
and appear only in the aggregates.

A facade candidate is a maximal **collinear** run of one sky-lit reachable
sector's wall loop, at least two bays long, carrying at least one opening.
Collinear because a run that turned a corner would have no plane to measure
datums against, and a facade that turns a corner is a different facade of
the same building.

## The corner rule is load-bearing, and the first version of it was wrong

The first collinearity predicate measured the perpendicular offset of each
candidate wall's **near** end from the run's line. In a closed loop that end
is the previous wall's end, which lies on the line by construction, so it
could never detect a corner. Algebraically it collapsed to
`|dx_run| * |dy| / L`: exactly right for an east-west run, identically zero
for a north-south one. Every north-south street ran straight through its own
corners.

It is fixed to use the far end, and the giveaway is a number that sat in the
draft of this report as a limitation:

```text
median distance from a sign to its facade's chord
  measuring the near end (wrong)    429 units
  measuring the far end (fixed)       4 units
```

Four units is a quarter of one tile pixel. Letters sit *on* the plane, and
what looked like a wandering chord was runs wrapped around corners.

## An opening in a facade has a lintel, and the first version forgot that

The second and larger correction. The first extractor counted every
two-sided wall on a run as an opening. Of the 4331 it found on campaign
runs, **3187 were not openings at all**:

```text
outdoor neighbour, same sky ceiling, a step in the floor   2559   a kerb
outdoor neighbour, same sky ceiling, same floor             628   a seam
indoor or gated neighbour, with a header                   1140   an opening
indoor neighbour with neither                                 4
```

A street is many sectors, and where two of them meet at a step in the
pavement Build puts a two-sided wall. There is no hole and no wall above it:
it is ground. **An opening in a facade has a header** -- the neighbour's
ceiling is below the host's -- and requiring one drops all 3187 while losing
4 genuine indoor neighbours.

Campaign candidates fall from 3570 to 890, multi-opening runs from 450 to
131, and signed facades from 27 to 11. That last one is the tell that this
is a gain and not a loss: the 27 included stray single letters sitting on
stretches of pavement, and the 11 are shopfronts -- LOADING, FEINMAN MEATS,
STORAGE, EVERYTHING, BURGERS, SCREAMS, WATER, ICE, BAIT.

Every number below is from both fixes. None of the first draft's survive.

## The two measured constants, re-confirmed and partly contradicted

`projects/blood-city/level/facade_pass.py` measured three things off E3M1
and TEDE1M2. Checked over 5275 street-facing walls in 34 campaign maps:

| claim | its own sample, remeasured | campaign-wide | verdict |
| --- | --- | --- | --- |
| street walls run at 16 world units per tile pixel | 111/122 E3M1 (91%) | **3869/5275 (73%)** | confirmed |
| `x_panning` phased to world position | 59/111 E3M1 (53%) | **770/3869 (20%)** | **local habit, not convention** |
| header walls take cstat bit 4 | 23/60 E3M1 (38%) | **628/2215 (28%)** | **local habit, not convention** |

These three count street-facing *walls* and the headers over real openings,
so the lintel fix does not move them; only the opening-width figures below
changed.

The scale constant holds, and it is what makes the bay grid real: a
64-pixel facade tile at 16 units per pixel spans 1024 units, so `BAY =
1024`. The other two do not generalize. World-phasing is an E6M3 (80%),
E6M1 (72%) and E1M3 (33%) habit; most campaign street walls are phased from
their own start vertex. A generator that applies either corpus-wide is
copying three maps, not the campaign -- worth knowing before blood-city
adopts them as rules.

E6M3, not E3M1, is the campaign's most disciplined street: 95% of its
street walls at facade scale, 80% world-phased, and 81% of its street
openings (29 of 36) a whole number of bays wide, against 26% campaign-wide.

## What keeps a facade coherent

The exit criterion. Measured over the campaign facades that have more than
one opening -- the ones where "belonging together" means anything:

```text
campaign facade candidates            890  in 37 maps
with two or more openings             131/890  (15%)

one wall tile across the whole run    128/131  (98%)
openings share a header datum         104/131  (79%)
openings share a sill datum           101/131  (77%)
carrying a thin helper sector         93/131  (71%)
openings on a whole number of bays    117/381  (31%)
```

So the answer: **one material first and by a long way, then a header line
and a sill line together, then a thin helper sector.** Header and sill are
within two points of each other and should not be ranked against one
another on 131 runs.

Not the bay grid. Fewer than a third of campaign openings on these runs land
on whole bays, and a rule that demanded it would reject most of the
campaign's own facades. The thin helper sectors sit surprisingly high --
71% -- and the rendered E3M2 frames show what they are: the kerb strip along
the pavement, and the stone frame around the loading bay. They reach a
facade through a seam as often as through an opening, which is why they are
counted over every two-sided neighbour rather than only the openings.

Curated maps are precedent, never convention, and are kept separate
throughout. They agree on the ordering and are slightly tidier about it --
one tile 97%, header 88%, sill 86%, helper 58%,
over 283 multi-opening runs in 38 maps.

## Rhythm

```text
single                    759    85%
repeating                  53     6%
centered                   35     4%
irregular                  33     4%
intentionally_broken        6     1%
alternating                 4     0%
```

Most street runs carry one opening, so most have no rhythm to measure, and
once seams stop counting as openings that gets more pronounced, not less: a
Blood street is mostly single openings in long plain walls, with the
repeating window bank as the exception. `intentionally_broken` -- even
spacing but for one outlier -- is kept as its own class rather than rounded
into `repeating`, because `06_...md` asks not to regularize authored
irregularity away. At 6 campaign runs it is a category held open
for evidence, not an established pattern.

## Signage, as a member of the hierarchy

The owner's steer: treat signage as first-class, not decoration. Blood has
no text primitive -- `lettering.py` records the alphabet at tiles 3808-3833
-- so a sign is a row of letter sprites, and each is assigned to the facade
plane it is nearest to, so a shopfront is never counted twice.

```text
facades carrying signage        11   (3 campaign, 8 curated)
letter sprites placed           86
wall-aligned                    86/86  (100%)
```

```text
height above the street, player heights
  min 1.691   p25 2.254   median 2.536   p75 3.442   max 5.132
  between 1.5 and 3.5           74/86  (86%)

position along the run, as a fraction of its length
  p25 0.35   median 0.5   p75 0.698
  in the middle half of the run 66/86  (77%)

  within one bay of an opening  72/86  (84%)   campaign 25/26  (96%)
  distance from the plane, units: median 4.0   p75 4.0
```

**Where a sign belongs, from the evidence:** flat on the wall (100% of 86,
none of them a perpendicular flag), *on* the plane -- no letter is more than
5 units off it -- in the middle half of its facade rather than at an end
(77%), about two and a half player heights up (median 2.54), and beside an
opening (84% within one bay, 96% in the campaign alone).

### The two-tier reading, confirmed

The rendered E3M2 frame shows LOADING immediately over its loading bay and
FEINMAN MEATS on the band above -- which reads as two tiers, a bay sign and
a building sign. Measured against real openings:

```text
sits above its nearest opening's header
  campaign            26/26   (100%)
  campaign + curated  73/86    (85%)

distance to that opening, bays        campaign median 0.375, p75 0.562
more than a player height above it    22 letters on 2 facades
  E3M2.MAP sector:301   12   FEINMAN MEATS   median 3.985 heights up
  DWE1M9.MAP sector:98  10   EVERYTHING
  the other 64                          median 2.254 heights up
```

**Every campaign sign letter sits above the header of the opening it
belongs to.** That is the placement rule, and it was invisible before the
lintel fix because most letters were being matched to kerbs. The draft of
this report scored the same question at 22% and blamed the datum.

The upper tier is real and separates cleanly, but on two facades out of 11
-- enough to say the frame was read correctly, not enough to call it a
convention.

The cornice remains a genuine datum gap: a street sector's ceiling is the
sky, so the top of a facade is painted rather than built, and
`datums.cornice` is reported as `null` with that reason rather than guessed.
The visible lintel band a sign sits on has the same problem -- the header
measured here is the neighbour sector's `ceiling_z`, not the painted band.

## Rendered validation

```text
reports/blood-facade-views/E3M2-signage/observation/frames/sector_301.png
reports/blood-facade-views/E3M2-signage/observation/frames/sector_179.png
reports/blood-facade-views/E6M3-bays/observation/frames/sector_142.png
reports/blood-facade-views/E6M3-bays/observation/frames/sector_32.png
```

The E3M2 pair is the signage evidence in a picture: a window bank down one
side, a kerb strip as a thin helper sector, a loading bay with its frame and
sill, and both tiers of sign.

The E6M3 pair is the corner rule in a picture, which is why it is here at
all. `sector_32` looks into the angle where a grey brick frontage with a
single doorway meets a boarded wooden one; they share nothing but the
corner, and the first collinearity predicate reported them as one facade.
`sector_142` is the wooden frontage itself, one material the whole way with
piers dividing it into bays, and a hazard-striped door frame on a different
plane behind. Neither run has a repeating rhythm: E6M3 is disciplined about
the bay grid, not about repetition.

The frames come from the XMapEdit observer, so they are evidence about how
the renderer paints that map with the local game data -- not about design
intent.

## Counterexamples, preserved

```text
facade runs longer than 30 bays              17
longest campaign run                         144.0 bays
openings leading to more outdoor space       150/1140  (13%)   a gate or an arch
facades carrying at least one seam           4 of the 140 written out in full

retracted from the first draft, which measured them on kerbs:
  letters below the street floor             0    (was 1; the lowest is now 1.691)
  signed facades with fewer than 3 letters   0    (was 5, all of them stray)
```

The very long runs were called the largest gap in this extractor. Measured,
they are the only place the gap is real: of the runs that serve an interior,
none under four bays crosses a building boundary and 20% of those over
sixteen do. `reports/blood-party-walls.md` has the rest.

Run-order spelling is a useful tell rather than a defect: E3M2's sector:301
reads `FEIMNEMAATNS`, which is FEINMAN over MEATS interleaved, because run
order is one-dimensional and a two-line sign is not. Anything that wants the
text has to group by height first.

## Constructor promotion: the blocker moved

`09_...md` allows a `facade_run()` constructor into `vocabulary.py` only
once recurrence is established. This report first refused on the ground that
a candidate is a plane, not a building. `reports/blood-party-walls.md`
measured that against the interior -- two openings are in one building when
their interiors connect without going back outside -- and **withdrew it**: a
run serving any interior serves exactly one building in 98% of the campaign,
never below four bays, and the exceptions are long runs.

What still blocks promotion:

- **The visible lintel.** Sill and header datums exist, but the band a sign
  sits on does not, and every campaign sign sits on it. A constructor could
  place the opening and not the band above it.
- **Rhythm is rare.** 53 repeating runs in 890 campaign candidates
  is not enough recurrence to promote a rhythm parameter with a default.

What *is* established and can be used now, with the numbers above behind it:
one material across a run, a header line and a sill line shared by its
openings, a bay of 1024 units at the 16-units-per-pixel scale, a thin helper
sector at the kerb or around the opening, and signage flat on the plane at
about 2.5 player heights, beside an opening and above its header.

## Limitations

- A candidate is a plane in a sky-lit sector. An indoor shopfront onto a
  covered arcade is not found at all.
- A run is straight to within 64 units, so a curved street is chopped into
  short chords rather than recognized as one frontage.
- Curated facades are precedent. 8 of the 11 signed facades are
  curated, so the signage statistics lean on Death Wish and are labelled as
  such. The campaign on its own has 3 signed facades in 2 maps carrying 26
  letters, and every signage claim above should be read at that size.
- A gate or an arch into an outdoor courtyard has a header and so counts as
  an opening, which is right, but it means 13% of the openings found lead to
  more outdoor space rather than into a building.
- `owner-anchors-v1.json` marks tile 202 weak-binding -- material, never
  facade identity -- and nothing here reads a tile as evidence of a facade.

