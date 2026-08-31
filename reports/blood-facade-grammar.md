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
what looked like a wandering chord was runs wrapped around corners. Every
number below is from the fixed predicate; none of the draft's survive.

## The two measured constants, re-confirmed and partly contradicted

`projects/blood-city/level/facade_pass.py` measured three things off E3M1
and TEDE1M2. Checked over 5275 street-facing walls in 34 campaign maps:

| claim | its own sample, remeasured | campaign-wide | verdict |
| --- | --- | --- | --- |
| street walls run at 16 world units per tile pixel | 111/122 E3M1 (91%) | **3869/5275 (73%)** | confirmed |
| `x_panning` phased to world position | 59/111 E3M1 (53%) | **770/3869 (20%)** | **local habit, not convention** |
| header walls take cstat bit 4 | 23/60 E3M1 (38%) | **628/2215 (28%)** | **local habit, not convention** |

The scale constant holds, and it is what makes the bay grid real: a
64-pixel facade tile at 16 units per pixel spans 1024 units, so `BAY =
1024`. The other two do not generalize. World-phasing is an E6M3 (80%),
E6M1 (72%) and E1M3 (33%) habit; most campaign street walls are phased from
their own start vertex. A generator that applies either corpus-wide is
copying three maps, not the campaign -- worth knowing before blood-city
adopts them as rules.

E6M3, not E3M1, is the campaign's most disciplined street: 95% of its
street walls at facade scale, 80% world-phased, and 85% of its street
openings a whole number of bays wide.

## What keeps a facade coherent

The exit criterion. Measured over the campaign facades that have more than
one opening -- the ones where "belonging together" means anything:

```text
campaign facade candidates            3570  in 37 maps
with two or more openings             450/3570  (13%)

one wall tile across the whole run    441/450  (98%)
openings share a header datum         406/450  (90%)
openings share a sill datum           286/450  (64%)
carrying a thin helper sector         196/450  (44%)
openings on a whole number of bays    376/1211  (31%)
```

So the answer, in order of strength: **one material, then a shared header
line, then a shared sill line.** Not the bay grid -- fewer than a third of
campaign street openings land on whole bays, and a rule that demanded it
would reject most of the campaign's own facades.

The thin helper sectors are the surprise: 44% of multi-opening facades carry
one, which puts them ahead of the bay grid as a facade signal. The rendered
E3M2 frames show what they are -- the kerb strip along the pavement, and the
stone frame around the loading bay.

Curated maps are precedent, never convention, and are kept separate
throughout. They agree on the ordering and are slightly tidier about it --
one tile 99%, header 95%, sill 71%, helper 42%,
over 1517 multi-opening runs in 38 maps.

## Rhythm

```text
single                   3120    87%
centered                  165     5%
irregular                 159     4%
repeating                 112     3%
intentionally_broken        9     0%
alternating                 5     0%
```

Most street runs carry one opening, so most have no rhythm to measure. Once
runs stop at corners this gets more pronounced, not less: a Blood street is
mostly single openings in long plain walls, with the repeating window bank
as the exception. `intentionally_broken` -- even spacing but for one
outlier -- is kept as its own class rather than rounded into `repeating`,
because `06_...md` asks not to regularize authored irregularity away. It is
rare enough (9 campaign runs) that it is a category held open for
evidence, not an established pattern.

## Signage, as a member of the hierarchy

The owner's steer: treat signage as first-class, not decoration. Blood has
no text primitive -- `lettering.py` records the alphabet at tiles 3808-3833
-- so a sign is a row of letter sprites, and each is assigned to the facade
plane it is nearest to, so a shopfront is never counted twice.

```text
facades carrying signage        27   (7 campaign, 20 curated)
letter sprites placed           165
wall-aligned                    165/165  (100%)
```

```text
height above the street, player heights
  min -10.566   p25 1.691   median 2.254   p75 3.26   max 6.581
  between 1.5 and 3.5           121/165  (73%)

position along the run, as a fraction of its length
  p25 0.344   median 0.571   p75 0.714
  in the middle half of the run 109/165  (66%)

  within one bay of an opening  123/165  (75%)
  distance from the plane, units: median 4.0   p75 192.0
```

**Where a sign belongs, from the evidence:** flat on the wall (100% of 165,
none of them a perpendicular flag), on the plane rather than near it, in the
middle half of its facade rather than at an end (66%), a little over two
player heights up (median 2.25), and beside an opening (75% within one bay).

### The two-tier reading survives, on two facades

The rendered E3M2 frame shows LOADING immediately over its loading bay and
FEINMAN MEATS on the band above -- which reads as two tiers, a bay sign and
a building sign. Against the fixed planes, that separates:

```text
letters more than a player height above their nearest opening's header
  E3M2.MAP sector:301   12   FEINMAN MEATS
  DWE1M9.MAP sector:98  10   EVERYTHING
  every other signed facade   0

median height above the street
  the high tier   3.985 player heights
  the low tier    2.254 player heights
```

So the tiers are real and separate cleanly -- on **two facades out of 27**,
one campaign and one curated. That is enough to say the frame was read
correctly and not enough to call it a convention: a building sign above a
bay sign is a thing Blood does, not a thing Blood does routinely. The draft
of this report scored the same question at 22% and blamed the datum; the
real cause was the corner bug matching letters to openings on other planes.

The cornice is a genuine datum gap, and it stays one: a street sector's
ceiling is the sky, so the top of a facade is painted rather than built, and
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
letters below the street floor            1   (min -10.566 player heights, E1M2 sector:34)
facade runs longer than 30 bays           47
longest campaign run                      144.0 bays
signed facades carrying fewer than 3 letters   10
```

The very long runs are city-block edges rather than buildings: a straight
run of a street sector's loop does not know where one building stops and the
next begins, and nothing in the geometry says. That is the largest honest
gap in this extractor, and the corner fix did not close it -- it stopped runs
crossing corners, not runs passing party walls.

The two-letter facades are the same gap seen from the other end: a word
split across a corner leaves one or two letters on each plane. `LO` / `E` /
`SR` on DWE3M10 sector:431 is one sign on a kiosk, reported as three.

Run-order spelling is a useful tell rather than a defect: E3M2's sector:301
reads `FEIMNEMAATNS`, which is FEINMAN over MEATS interleaved, because run
order is one-dimensional and a two-line sign is not. Anything that wants the
text has to group by height first.

## Constructor promotion: not yet

`09_...md` allows a `facade_run()` constructor into `vocabulary.py` only
once recurrence is established. It is not, and here is what is missing:

- **Building extent.** A facade candidate is a plane, not a building. Until
  something separates one building's frontage from its neighbour's, a
  constructor would be building city blocks, not shops.
- **The visible lintel.** Sill and header datums exist, but the band a sign
  sits on does not, and it is the line the eye reads.
- **Rhythm is rare.** 112 repeating runs in 3570 campaign candidates
  is not enough recurrence to promote a rhythm parameter with a default.

What *is* established and can be used now, with the numbers above behind it:
one material across a run, a shared header line, a bay of 1024 units at the
16-units-per-pixel scale, a thin helper sector at the kerb or around the
opening, and signage flat on the plane at about 2.25 player heights beside
an opening.

## Limitations

- A candidate is a plane in a sky-lit sector. An indoor shopfront onto a
  covered arcade is not found at all.
- A run is straight to within 64 units, so a curved street is chopped into
  short chords rather than recognized as one frontage.
- Curated facades are precedent. 20 of the 27 signed facades are
  curated, so the signage statistics lean on Death Wish and are labelled as
  such. The campaign on its own has 7 signed facades in 4 maps, and every
  signage claim above should be read at that sample size.
- `owner-anchors-v1.json` marks tile 202 weak-binding -- material, never
  facade identity -- and nothing here reads a tile as evidence of a facade.

