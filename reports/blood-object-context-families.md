# Object-scale unsigned families: Phase 3

One new family in the existing pattern pipeline, not a new framework:
`object-context`, one sample per sector that holds objects, keyed by its
Phase 1 relation neighborhood. The three families already there measure a
sector's *shape* (`local-morphology`), its *route* (`route-exposure`) or its
*edges* (`vertical-transition`). This one measures what a sector is for at
object scale: what it holds, what holds those objects up, and how it sits
among its neighbours.

```text
python -m bloodmap pattern-mine --maps maps/blood --population blood-campaign \
  -o work/blood-pattern-unsigned-campaign.json
python -m bloodmap pattern-mine --maps maps/blood --population community \
  --tier S --limit 20 -o work/blood-pattern-unsigned-tierS.json
```

The signature is the relation context plus two scale bands. Because the
features are Phase 1 relations, it is frame-independent: two furnished
corners in different maps at different orientations key the same, which is
the only reason mining them together means anything.

## The bands are measured, not chosen

Quartiles of the 2837 sprite-carrying sectors in the first 15 campaign maps:
area p25/p50/p75 = 3.7/14.2/56.7 player areas, clear height 1.57/1.93/3.50
player heights. The first version guessed round numbers (1.0/2.0/4.0 on
height) and put nearly every campaign sector in one bucket, which would have
made the facet decorative. Calibrated, the four bands hold 25/24/27/24% and
25/33/20/22% of the sample.

## Candidate stability and cross-map coverage

| population | samples | `object-context` candidates | occurrences | in >=3 maps | share of occurrences |
| --- | ---: | ---: | ---: | ---: | ---: |
| `blood-campaign` | 27925 | 1328 | 6599 | 460 | 80% |
| `blood-bloodbath` | 2295 | 242 | 546 | 28 | 38% |
| `community tier S` | 16064 | 894 | 2997 | 217 | 63% |

**80% of campaign object-context occurrences fall in a candidate that recurs
across three or more maps.** Half the candidates are singletons, but they
hold only 10% of the occurrences: the tail is long and thin, and the mass is
in recurring structure.

For comparison, in the same run `route-exposure` puts 50% of its occurrences
in candidates spanning three or more maps, and 0% in BloodBath. The new
family is more stable than one of the families already in the pipeline.

### The vocabulary transfers between populations

```text
campaign signatures                      1328
also seen in BloodBath                   204 = 89% of BloodBath occurrences
also seen in community tier S (20 maps)  579 = 84% of tier-S occurrences
```

Populations stay separate as evidence -- this is a *coverage* statement, not
a claim that community maps follow campaign convention. What it says is that
the signature vocabulary is not campaign-specific: nine tenths of BloodBath's
object-scale contexts are contexts the campaign also builds.

## Clusters nobody programmed

The exit criterion. None of these is a named concept anywhere in the code --
they are discrete signatures that recurred.

- **256 occurrences across 41 maps** (BloodBath x23; tier S x69)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:some|run:no|size:hall|clear:lofty`
- **101 occurrences across 32 maps** (BloodBath x17; tier S x39)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:some|run:no|size:hall|clear:standing`
- **91 occurrences across 32 maps** (tier S x68)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:some|run:no|size:hall|clear:open`
- **63 occurrences across 31 maps** (BloodBath x12; tier S x11)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:none|run:no|size:hall|clear:lofty`
- **72 occurrences across 30 maps** (BloodBath x5; tier S x22)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:some|run:no|size:room|clear:standing`
- **77 occurrences across 28 maps** (BloodBath x7; tier S x35)
  `portals:2|enclosed:no|stacked:none|coplanar:yes|objects:1|seated:none|wallbound:all|run:no|size:tiny|clear:tight`

### The pair worth looking at

Two candidates identical in every facet but one:

```text
 77 occ / 28 maps   seated:none   the object hangs on the wall
 72 occ / 24 maps   seated:all    the object stands on the floor

shared: a tiny, tight, two-portal sector holding exactly one object,
        against a wall, sharing a floor plane with a neighbour
```

A niche in a passage with one fixture in it, and the same niche with the
fixture on the floor instead of the wall. Both recur in over twenty
campaign maps and in both other populations. That is `03_...md`'s
contrastive mining -- "nearly identical structures with one systematic
relational difference" -- arrived at without searching for it.

Automatic contrast search over candidates spanning eight or more maps finds
pairs differing in exactly one facet; `clear` and `size` dominate (the same
furnished hall at four ceiling heights), and the informative ones are the
`seated`/`wallbound` pairs above.

## The Phase 2 prediction, tested

Phase 2 ended with a prediction: object anchors would cluster tightly and
material anchors would not. The campaign mine keys every sprite-carrying
sector to a signature, so testing it is a join, not new mining. For each
anchor role: what share of its campaign carrying sectors fall in its single
commonest object-context signature?

```text
anchor                 Ph2 enrichment   sectors   concentration
chair                          11.58        22           0.500
outlet                          9.38        13           0.154
hanging_clothes                 6.97        27           0.333
sewer_grate                     5.77        44           0.136
machinery                       3.14        62           0.129
crate_surface                   2.77      1067           0.157
shelf_wall                      2.56        25           0.360
sewer_light                     2.22        51           0.059
wood_casework                   1.40       486           0.068
pipe_walls                      1.15       384           0.133
drawer_surface                  0.83        50           0.220
shaft_metal                     0.75       132           0.152
sewer_door                      0.53        33           0.242

Pearson r = 0.541  (n = 13)
```

**Directionally supported, not established.** The extremes behave: `chair`
(11.6x, 0.50) and `hanging_clothes` (7.0x, 0.33) are high on both; 
`sewer_light` (2.2x, 0.059) and `wood_casework` (1.4x, 0.068) are low on
both. But r = 0.54 at n = 13 is weak, and there are two clear
counterexamples: `outlet` has the third-highest enrichment and near-lowest
concentration (11 distinct signatures over 13 sectors), and `sewer_door` is
anti-associated by enrichment (0.53) yet more concentrated than several
enriched anchors.

The two numbers are also measured on different corpora -- enrichment on the
reference view's densest maps, concentration on the campaign -- so part of
the scatter is corpus mismatch rather than signal. The prediction survives
as a hypothesis with a measured effect size; it is not a finding.

## Limitations

- Only sectors holding at least one sprite are sampled. An empty sector has
  no object-scale content, and including 600 per map would bury the
  families that do.
- The tier-S run is **20 maps of 294**, taken in enumeration order so a
  rerun mines the same ones. It is a bounded sample and the report says so.
- `E6M7.MAP` produces no samples in any family: its sector 144 has invalid
  wall ownership and `analyze_spatial` validates the whole map before any
  selection. Reported in `observe_errors`, not silently dropped.
- Every candidate is `unsigned`. No occurrence here has been interpreted,
  and the signature describes a sector's role among its neighbours, not its
  shape -- two differently shaped rooms can key alike.
- Community and tier-S occurrences are precedent, never campaign convention.

